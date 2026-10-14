#!/usr/bin/env python
"""Uji sinyal Hpoc (nilai puncak POC) vs magnitude perpindahan — CAS(ME)^2.

Latar: Rosiani et al. (2020, POC-ABS) memakai EMPAT fitur per blok:
X, Y, M, T — dan M-nya BUKAN sqrt(X^2+Y^2), melainkan NILAI PUNCAK korelasi
POC itu sendiri (Hpoc). Bukti: contoh mereka XB28=2, YB28=2 tapi MB28=0,46
(= nilai puncak 0,4687 yang ditampilkan), bukan 2,83. Kode kita
(features/vektor.py:37) menghitung val_max lalu MEMBUANGNYA.

Mengapa ini penting untuk data 30 fps: perpindahan per frame terkuantisasi ke
integer piksel (temuan magnitude-deepdive: 15 nilai diskrit, 57,8% blok statis,
bottleneck = SNR). Hpoc adalah ukuran kemiripan KONTINU di (0,1] — tidak
mengenal lantai kuantisasi 1 piksel, jadi berpotensi membawa sinyal sub-piksel
yang selama ini hilang.

Yang diuji (4 konfigurasi x 4 sinyal per ROI):
  konfigurasi: b9abs (block 9, acuan frame-0 = pipeline sekarang)
               b5abs (block 5 = ukuran terbaik paper, acuan frame-0)
               b9seq (block 9, acuan frame berurutan = acuan paper)
               b5seq (block 5 + frame berurutan = konfigurasi persis paper)
  sinyal     : mean_m        = mean |V| (baseline sekarang, dari posisi puncak)
               frac_mov      = fraksi blok bergerak (Pvector paper, Eq. 6)
               hpoc_drop_mean= mean(1 - Hpoc) semua blok (ketidakmiripan kontinu)
               hpoc_drop_mov = mean(1 - Hpoc) blok bergerak saja (fitur M paper,
                               blok tanpa gerak dikecualikan sesuai paper)

Fase build : hitung + cache sinyal ke npz per video.
Fase eval  : F1 gabungan + F1 ketat (IoU>=0,5) + validasi split subjek 2-fold,
             resep deteksi SAMA dengan audit_mag_agg_casme2.py.

Cara pakai:
    .venv/bin/python scripts/audit_hpoc_casme2.py build --limit 2   # uji cepat
    .venv/bin/python scripts/audit_hpoc_casme2.py build --workers 3
    .venv/bin/python scripts/audit_hpoc_casme2.py eval
"""

from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT, ROOT / 'pipeline' / 'stages'):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import eval_spotting_casme2 as bench  # noqa: E402
import stage_1_spotting as spot  # noqa: E402
from apex import ApexPhase, ApexSmoother  # noqa: E402
from features.poc import POC  # noqa: E402

DEFAULT_CACHE = ROOT / 'output/training/casme2_hpoc_signals'
CONFIGS = ('b9abs', 'b5abs', 'b9seq', 'b5seq')
SIGNALS = ('mean_m', 'frac_mov', 'hpoc_drop_mean', 'hpoc_drop_mov')
BLOCK_OF = {'b9abs': 9, 'b5abs': 5, 'b9seq': 9, 'b5seq': 5}
IS_SEQ = {'b9abs': False, 'b5abs': False, 'b9seq': True, 'b5seq': True}
CUTOFFS = (0.3, 0.5)
TOP_K = 5


def block_stats(poc_arr: np.ndarray, bs: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Dari array POC (bs, bs, n_blok): (magnitude, moving, hpoc_drop) per blok.

    Setara Vektor+Quadran untuk magnitude (offset integer puncak dari tengah,
    aturan ambiguitas sama: >1 posisi maksimum => dianggap diam), plus Hpoc
    yang selama ini dibuang.
    """
    center = bs // 2
    n = poc_arr.shape[2]
    mag = np.zeros(n)
    mov = np.zeros(n, dtype=bool)
    drop = np.zeros(n)
    for i in range(n):
        r = poc_arr[:, :, i]
        vmax = float(r.max())
        pos = np.argwhere(r == vmax)
        drop[i] = 1.0 - vmax
        if len(pos) > 1:
            continue  # ambigu -> dianggap tidak bergerak (aturan Vektor)
        py, px = int(pos[0][0]), int(pos[0][1])
        if px != center or py != center:
            mov[i] = True
            mag[i] = float(np.hypot(px - center, py - center))
    return mag, mov, drop


def roi_signals(poc_arr: np.ndarray, bs: int) -> dict[str, float]:
    mag, mov, drop = block_stats(poc_arr, bs)
    return {
        'mean_m': float(mag.mean()) if mag.size else np.nan,
        'frac_mov': float(mov.mean()) if mov.size else np.nan,
        'hpoc_drop_mean': float(drop.mean()) if drop.size else np.nan,
        'hpoc_drop_mov': float(drop[mov].mean()) if mov.any() else 0.0,
    }


def signals_for_video(video: str, configs: tuple[str, ...]) -> dict[str, list[float]]:
    """{cfg__roi__sinyal: nilai per frame} untuk satu video."""
    cap = cv2.VideoCapture(video)
    grays, lms = [], []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        grays.append(gray)
        lms.append(spot.detect_landmarks(gray, spot.WORKER_DETECTOR, spot.WORKER_PREDICTOR))
    cap.release()
    if len(grays) < 3 or lms[0] is None:
        return {}

    regions = spot.config.regions
    out: dict[str, list[float]] = {
        f'{c}__{r}__{s}': [] for c in configs for r in regions for s in SIGNALS}
    need_abs = any(not IS_SEQ[c] for c in configs)
    need_seq = any(IS_SEQ[c] for c in configs)

    # ROI acuan (frame-0) diekstrak sekali saja
    ref_roi: dict[str, np.ndarray] = {}
    if need_abs:
        for r, idx in regions.items():
            a = spot.extract_region(grays[0], lms[0], idx)
            if a.size:
                tw, th = spot.config.target_size[r]
                ref_roi[r] = cv2.resize(a, (tw, th))

    for i in range(1, len(grays)):
        cur_lm = lms[i]
        prev_lm = lms[i - 1]
        for r, idx in regions.items():
            vals: dict[str, dict[str, float] | None] = {c: None for c in configs}
            try:
                tw, th = spot.config.target_size[r]
                cur = prev = None
                if cur_lm is not None:
                    c = spot.extract_region(grays[i], cur_lm, idx)
                    if c.size:
                        cur = cv2.resize(c, (tw, th))
                if need_seq and prev_lm is not None:
                    p = spot.extract_region(grays[i - 1], prev_lm, idx)
                    if p.size:
                        prev = cv2.resize(p, (tw, th))
                if cur is not None:
                    for c in configs:
                        ref = prev if IS_SEQ[c] else ref_roi.get(r)
                        if ref is None:
                            continue
                        bs = BLOCK_OF[c]
                        poc_arr = POC(ref, cur, bs).getPOC()[0]
                        vals[c] = roi_signals(poc_arr, bs)
            except Exception:
                vals = {c: None for c in configs}
            for c in configs:
                for s in SIGNALS:
                    v = vals[c][s] if vals[c] else np.nan
                    out[f'{c}__{r}__{s}'].append(v)

    for k in out:
        out[k] = spot._interpolate_signal(out[k])
    return out


def cache_file(cache_dir: Path, video: str) -> Path:
    v = Path(video)
    return cache_dir / f'{v.parent.name}_{v.stem}.npz'


def load(path: Path) -> dict[str, np.ndarray] | None:
    if not path.exists():
        return None
    try:
        with np.load(path) as z:
            return {k: z[k].astype(float) for k in z.files}
    except (OSError, ValueError):
        return None


def save(path: Path, sig: dict[str, list[float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    with open(tmp, 'wb') as fh:
        np.savez_compressed(fh, **{k: np.asarray(v, dtype=float) for k, v in sig.items()})
    tmp.replace(path)


def worker(job: tuple[str, str, tuple[str, ...]]) -> tuple[str, bool, str]:
    video, cache_path, configs = job
    path = Path(cache_path)
    old = load(path)
    if old is not None:
        want = {f'{c}__{r}__{s}' for c in configs for r in spot.config.regions for s in SIGNALS}
        if want.issubset(set(old)):
            return video, True, 'cached'
    try:
        t0 = time.time()
        sig = signals_for_video(video, configs)
        dt = time.time() - t0
    except Exception as exc:
        return video, False, repr(exc)
    if not sig:
        return video, False, 'sinyal kosong'
    if old:
        old.update({k: np.asarray(v, dtype=float) for k, v in sig.items()})
        sig = old
    save(path, sig)
    n = len(next(iter(sig.values())))
    return video, True, f'{n} frame, {dt:.0f}s'


def cmd_build(args: argparse.Namespace) -> None:
    gt = bench.load_ground_truth(bench.DEFAULT_GT, bench.DEFAULT_VIDEOS)
    videos = sorted(gt['video'].unique())
    if args.limit:
        videos = videos[:args.limit]
    configs = tuple(args.configs.split(',')) if args.configs else CONFIGS
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    print(f'video: {len(videos)} | konfigurasi: {configs} | cache: {args.cache_dir}')

    jobs = [(v, str(cache_file(args.cache_dir, v)), configs) for v in videos]
    ok = fail = 0
    with ProcessPoolExecutor(max_workers=max(1, args.workers),
                             initializer=spot.init_worker,
                             initargs=(str(bench.PREDICTOR),)) as ex:
        futures = {ex.submit(worker, j): j[0] for j in jobs}
        for i, fut in enumerate(as_completed(futures), 1):
            video, success, info = fut.result()
            ok += success
            fail += (not success)
            print(f'  [{i}/{len(jobs)}] {"OK " if success else "GAGAL"} '
                  f'{Path(video).name}: {info}', flush=True)
    print(f'\nSelesai: {ok} ok, {fail} gagal')


# ---------------- eval ----------------

def global_signals(cache: dict[str, np.ndarray], configs: tuple[str, ...]) -> dict[str, list[float]]:
    """{cfg__sinyal: sinyal global (mean antar ROI)} dari satu cache video."""
    by: dict[str, list[np.ndarray]] = {}
    for key, sig in cache.items():
        parts = key.split('__')
        if len(parts) != 3 or parts[0] not in configs:
            continue
        by.setdefault(f'{parts[0]}__{parts[2]}', []).append(sig)
    out = {}
    for cand, rois in by.items():
        if not rois or any(len(s) == 0 for s in rois):
            continue
        n = min(len(s) for s in rois)
        out[cand] = [float(np.mean([s[i] for s in rois])) for i in range(n)]
    return out


def detect_with_cutoff(signal: list[float], cutoff_ratio: float) -> list[dict]:
    """Resep deteksi baku (sama persis dgn audit_mag_agg_casme2.py)."""
    smoothed = ApexSmoother.smooth(signal)
    arr = np.asarray(smoothed, dtype=float)
    height = float(arr.mean() + arr.std())
    spread = float(arr.max() - arr.min())
    detector = ApexPhase(
        distance_threshold=1,
        prominence_threshold=max(0.04 * spread, spot.config.prominence_threshold),
        cutoff_ratio=cutoff_ratio,
    )
    apex_indices = detector.find_top_k_apex(smoothed, k=TOP_K, height=height, ranking='prominence')
    phases = detector.find_phase(smoothed, apex_indices) if apex_indices else {}
    events = []
    for apex_idx in apex_indices:
        phase = phases[apex_idx]
        if int(phase['end'] - phase['start']) < spot.config.min_phase_duration:
            continue
        events.append({
            'onset': spot.signal_index_to_frame_index(int(phase['start'])),
            'apex': spot.signal_index_to_frame_index(int(apex_idx)),
            'offset': spot.signal_index_to_frame_index(int(phase['end'])),
        })
    return events


def iou(det: dict, gt: dict) -> float:
    inter = min(det['offset'], gt['offset']) - max(det['onset'], gt['onset'])
    if inter < 0:
        return 0.0
    union = max(det['offset'], gt['offset']) - min(det['onset'], gt['onset'])
    return inter / union if union > 0 else 0.0


def evaluate_subset(videos: list[str], cand_sigs: dict, gt_by_video: dict,
                    cand: str, cutoff: float) -> dict:
    tp = fp = fn = tp_strict = n_det = 0
    dur_list: list[int] = []
    for v in videos:
        sig = cand_sigs.get(v, {}).get(cand)
        if sig is None or len(sig) < 10:
            continue
        det = detect_with_cutoff(sig, cutoff)
        gt = gt_by_video[v]
        pairs, fps, fns = bench.match_events(gt, det, tol=0)
        tp += len(pairs)
        fp += len(fps)
        fn += len(fns)
        n_det += len(det)
        tp_strict += sum(1 for d, g in pairs if iou(d, g) >= 0.5)
        dur_list += [d['offset'] - d['onset'] for d in det]
    sc = bench.scores(tp, fp, fn)
    sc_strict = bench.scores(tp_strict, n_det - tp_strict, (tp + fn) - tp_strict)
    return {**sc, 'f1_strict': sc_strict['f1'], 'det': n_det,
            'dur_med': int(np.median(dur_list)) if dur_list else 0}


def cmd_eval(args: argparse.Namespace) -> None:
    gt_df = bench.load_ground_truth(bench.DEFAULT_GT, bench.DEFAULT_VIDEOS)
    gt_by_video: dict[str, list[dict]] = {}
    for _, r in gt_df.iterrows():
        gt_by_video.setdefault(r['video'], []).append(r.to_dict())
    videos_all = sorted(gt_by_video)
    configs = tuple(args.configs.split(',')) if args.configs else CONFIGS

    cand_sigs: dict[str, dict[str, list[float]]] = {}
    for v in videos_all:
        cache = load(cache_file(args.cache_dir, Path(v)))
        if cache is None:
            continue
        cand_sigs[v] = global_signals(cache, configs)
    videos = [v for v in videos_all if v in cand_sigs]
    subjects = sorted({Path(v).parent.name for v in videos})
    print(f'{len(videos)} video tercache (dari {len(videos_all)}), '
          f'{len(subjects)} subjek, {len(gt_df)} GT', flush=True)

    cands = sorted({c for sigs in cand_sigs.values() for c in sigs})
    cands = [c for c in cands if all(c in cand_sigs[v] for v in videos)]
    print(f'kandidat sinyal: {cands}', flush=True)

    rows = []
    for cand in cands:
        for cutoff in CUTOFFS:
            r = evaluate_subset(videos, cand_sigs, gt_by_video, cand, cutoff)
            rows.append({'cand': cand, 'cutoff': cutoff, **r})
            print(f"  {cand:22s} cutoff={cutoff} | P {r['precision']:.4f} R {r['recall']:.4f} "
                  f"F1 {r['f1']:.4f} | ketat {r['f1_strict']:.4f} | "
                  f"det/video {r['det'] / max(1, len(videos)):.1f} dur {r['dur_med']}", flush=True)

    print('\n=== validasi split subjek (pilih di train, ukur di test) ===')
    subj_parity = {s: i % 2 for i, s in enumerate(subjects)}
    folds = {
        'A->B': ([v for v in videos if subj_parity[Path(v).parent.name] == 0],
                 [v for v in videos if subj_parity[Path(v).parent.name] == 1]),
        'B->A': ([v for v in videos if subj_parity[Path(v).parent.name] == 1],
                 [v for v in videos if subj_parity[Path(v).parent.name] == 0]),
    }
    val_rows = []
    for fname, (train, test) in folds.items():
        pick = max(
            ((cand, cut) for cand in cands for cut in CUTOFFS),
            key=lambda cc: evaluate_subset(train, cand_sigs, gt_by_video, cc[0], cc[1])['f1'],
        )
        r_tr = evaluate_subset(train, cand_sigs, gt_by_video, *pick)
        r_te = evaluate_subset(test, cand_sigs, gt_by_video, *pick)
        val_rows.append({'fold': fname, 'cand': pick[0], 'cutoff': pick[1],
                         'train_f1': r_tr['f1'], 'test_f1': r_te['f1'],
                         'test_f1_strict': r_te['f1_strict']})
        print(f"  {fname}: terpilih {pick[0]}/cutoff {pick[1]} | "
              f"train F1 {r_tr['f1']:.4f} | test F1 {r_te['f1']:.4f} "
              f"(ketat {r_te['f1_strict']:.4f})", flush=True)

    args.out.mkdir(parents=True, exist_ok=True)
    lines = ['# Sinyal Hpoc vs magnitude perpindahan — CAS(ME)^2', '',
             f'{len(videos)} video tercache. Resep deteksi baku (sama dgn audit_mag_agg).',
             'mean_m = baseline pipeline sekarang.', '',
             '| sinyal | cutoff | P | R | F1 | F1 ketat | det/video | durasi median |',
             '|---|---|---|---|---|---|---|---|']
    for r in rows:
        lines.append(f"| {r['cand']} | {r['cutoff']} | {r['precision']:.4f} | {r['recall']:.4f} | "
                     f"**{r['f1']:.4f}** | {r['f1_strict']:.4f} | "
                     f"{r['det'] / max(1, len(videos)):.1f} | {r['dur_med']} |")
    lines += ['', '## Validasi split subjek 2-fold', '',
              '| fold | terpilih | train F1 | test F1 | test F1 ketat |',
              '|---|---|---|---|---|']
    for r in val_rows:
        lines.append(f"| {r['fold']} | {r['cand']}/cutoff {r['cutoff']} | {r['train_f1']:.4f} | "
                     f"**{r['test_f1']:.4f}** | {r['test_f1_strict']:.4f} |")
    (args.out / 'README.md').write_text('\n'.join(lines) + '\n')
    print(f'\nhasil -> {args.out / "README.md"}')


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name in ('build', 'eval'):
        p = sub.add_parser(name)
        p.add_argument('--cache-dir', type=Path, default=DEFAULT_CACHE)
        p.add_argument('--configs', type=str, default=None,
                       help='daftar dipisah koma, default semua (b9abs,b5abs,b9seq,b5seq)')
        if name == 'build':
            p.add_argument('--workers', type=int, default=3)
            p.add_argument('--limit', type=int, default=None)
        else:
            p.add_argument('--out', type=Path, default=ROOT / 'output/training/audit_hpoc_casme2')
    args = ap.parse_args()
    if args.cmd == 'build':
        cmd_build(args)
    else:
        cmd_eval(args)


if __name__ == '__main__':
    main()

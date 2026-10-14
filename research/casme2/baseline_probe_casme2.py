#!/usr/bin/env python
"""Uji ACUAN POC-ABS: apakah frame-0 salah untuk video panjang CAS(ME)^2?

Hipotesis: pipeline memakai frame-0 sebagai acuan. Video CAS(ME)^2 panjangnya
median 77 detik (2305 frame), jadi acuan frame-0 membuat sinyal mengukur
PERGESERAN KUMULATIF dari awal video, bukan gerakan lokal. Akibatnya puncak
ekspresi tenggelam di antara puncak akibat drift.

Yang diuji (semua memakai ROI yang sama, landmark dihitung SEKALI):
  abs    : acuan frame 0 (yang dipakai pipeline sekarang)
  seq    : acuan frame i-1 (gerakan antar frame)
  lag10  : acuan frame i-10
  lag30  : acuan frame i-30   (~1 detik pada 30 fps)
  lag60  : acuan frame i-60

Metrik utama = "precision@K untuk apex": ambil K puncak teratas per ROI menurut
nilai sinyal, lalu hitung berapa persen apex GT yang punya puncak dalam +/-10
frame. Ini mengukur langsung apakah puncak ekspresi bisa DIPERINGKAT cukup
tinggi, terlepas dari ambang.

Cara pakai:
    .venv/bin/python scripts/baseline_probe_casme2.py --workers 4
"""

from __future__ import annotations

import argparse
import sys
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
from features.poc import POC  # noqa: E402
from features.vektor import Vektor  # noqa: E402

MODES = ('abs', 'seq', 'lag10', 'lag30')
DEFAULT_CACHE = ROOT / 'output/training/casme2_baseline_signals'


def mode_ref_index(mode: str, i: int) -> int:
    if mode == 'abs':
        return 0
    if mode == 'seq':
        return i - 1
    return max(0, i - int(mode[3:]))


def _crop_rois(gray, lm) -> dict[str, np.ndarray | None]:
    """Crop + resize tiap ROI satu kali (kecil, aman disimpan)."""
    crops: dict[str, np.ndarray | None] = {}
    for r, idx in spot.config.regions.items():
        if lm is None:
            crops[r] = None
            continue
        try:
            roi = spot.extract_region(gray, lm, idx)
            if roi.size == 0:
                crops[r] = None
                continue
            tw, th = spot.config.target_size[r]
            crops[r] = cv2.resize(roi, (tw, th))
        except Exception:
            crops[r] = None
    return crops


def signals_for_video(video: str) -> dict[str, list[float]]:
    """{f'{mode}__{roi}': sinyal} untuk semua mode sekaligus (landmark sekali).

    Frame di-STRIM: hanya crop ROI (kecil) dari 61 frame terakhir yang disimpan,
    bukan seluruh frame grayscale. Versi lama menyimpan semua frame (~1,3 GB
    untuk video 4370 frame per worker) sehingga menembus RAM dan bikin swap.
    """
    regions = spot.config.regions
    out: dict[str, list[float]] = {f'{m}__{r}': [] for m in MODES for r in regions}
    hist: list[tuple[int, dict]] = []  # (frame_index, crops) dari frame terakhir
    frame0: dict | None = None
    n = 0

    cap = cv2.VideoCapture(video)
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            lm = spot.detect_landmarks(gray, spot.WORKER_DETECTOR, spot.WORKER_PREDICTOR)
            crops = _crop_rois(gray, lm)
            if n == 0:
                frame0 = crops
            else:
                hist.append((n, crops))
                for r in regions:
                    cur = crops[r]
                    for m in MODES:
                        ref_i = mode_ref_index(m, n)
                        ref = frame0[r] if ref_i == 0 else None
                        if ref is None and ref_i != 0:
                            for idx, c in hist:
                                if idx == ref_i:
                                    ref = c[r]
                                    break
                        if cur is None or ref is None:
                            out[f'{m}__{r}'].append(np.nan)
                            continue
                        try:
                            poc = POC(ref, cur, spot.config.block_size)
                            q = Vektor(poc.getPOC(), spot.config.block_size).getVektor()
                            mags = np.array([float(x[4]) for x in q], dtype=float)
                            out[f'{m}__{r}'].append(float(mags.mean()) if mags.size else np.nan)
                        except Exception:
                            out[f'{m}__{r}'].append(np.nan)
                # simpan hanya 61 frame terakhir
                if len(hist) > 61:
                    hist.pop(0)
            n += 1
    finally:
        cap.release()

    if n < 5 or frame0 is None or all(v is None for v in frame0.values()):
        return {}
    for k in out:
        out[k] = spot._interpolate_signal(out[k])
    return out


def cache_file(cache_dir: Path, video: str) -> Path:
    v = Path(video)
    return cache_dir / f'{v.parent.name}_{v.stem}.npz'


def load(path: Path):
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


def worker(job: tuple[str, str]) -> tuple[str, bool, str]:
    video, cache_path = job
    path = Path(cache_path)
    if load(path) is not None:
        return video, True, 'cached'
    try:
        sig = signals_for_video(video)
    except Exception as exc:
        return video, False, repr(exc)
    if not sig:
        return video, False, 'kosong'
    save(path, sig)
    return video, True, f'{len(next(iter(sig.values())))} frame'


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache-dir', type=Path, default=DEFAULT_CACHE)
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--out', type=Path, default=ROOT / 'output/training/baseline_probe_casme2')
    ap.add_argument('--tolerance', type=int, default=10, help='toleransi frame utk apex')
    args = ap.parse_args()

    gt = bench.load_ground_truth(bench.DEFAULT_GT, bench.DEFAULT_VIDEOS)
    gt_by_video = {v: g.to_dict('records') for v, g in gt.groupby('video')}
    videos = sorted(gt_by_video)
    args.cache_dir.mkdir(parents=True, exist_ok=True)

    jobs = [(v, str(cache_file(args.cache_dir, v))) for v in videos]
    ok = fail = 0
    with ProcessPoolExecutor(max_workers=max(1, args.workers),
                             initializer=spot.init_worker,
                             initargs=(str(bench.PREDICTOR),)) as ex:
        futures = {ex.submit(worker, j): j[0] for j in jobs}
        for i, fut in enumerate(as_completed(futures), 1):
            video, success, info = fut.result()
            ok += success; fail += (not success)
            if not success:
                print(f'  GAGAL {Path(video).name}: {info}', flush=True)
            elif i % 20 == 0:
                print(f'  [{i}/{len(jobs)}] ok={ok} gagal={fail}', flush=True)
    print(f'\nsinyal selesai: {ok} ok, {fail} gagal')

    # ---- Evaluasi: precision@K apex + peringkat puncak ekspresi ----
    from scipy.signal import find_peaks
    from apex import ApexSmoother

    results: dict[str, dict] = {}
    for m in MODES:
        per_k = {k: [] for k in (1, 2, 5, 10)}
        ranks = []
        n_gt = 0
        for v in videos:
            sig = load(cache_file(args.cache_dir, v))
            if sig is None:
                continue
            g = gt_by_video[v]
            n = len(next(iter(sig.values())))
            for roi in spot.config.regions:
                key = f'{m}__{roi}'
                if key not in sig:
                    continue
                sm = np.asarray(ApexSmoother.smooth(sig[key].tolist()), dtype=float)
                if len(sm) < 10:
                    continue
                pk, _ = find_peaks(sm, distance=1)
                if len(pk) == 0:
                    continue
                order = np.argsort(-sm[pk])
                ranked = pk[order]
                for x in g:
                    n_gt += 1
                    ap = x['apex']
                    dist = np.abs((ranked + 1) - ap)
                    first = int(np.argmax(dist <= args.tolerance)) if (dist <= args.tolerance).any() else -1
                    for k in per_k:
                        per_k[k].append(1 if (first >= 0 and first < k) else 0)
                    if first >= 0:
                        ranks.append(first / len(ranked))
        results[m] = {
            'n_gt': n_gt,
            **{f'apex_precision_at_{k}': float(np.mean(v)) if v else float('nan')
               for k, v in per_k.items()},
            'median_rank_pct': float(np.median(ranks)) if ranks else float('nan'),
            'n_ranked': len(ranks),
        }
        print(f"  {m:6s}: P@1={results[m]['apex_precision_at_1']:.4f} "
              f"P@2={results[m]['apex_precision_at_2']:.4f} "
              f"P@5={results[m]['apex_precision_at_5']:.4f} "
              f"P@10={results[m]['apex_precision_at_10']:.4f} "
              f"| median rank {results[m]['median_rank_pct']:.3f}", flush=True)

    args.out.mkdir(parents=True, exist_ok=True)
    lines = ['# Uji acuan POC-ABS pada CAS(ME)^2', '',
             f'- toleransi apex: +/-{args.tolerance} frame',
             f'- n GT: {results[MODES[0]]["n_gt"]}',
             '',
             '`P@K` = proporsi apex GT yang punya puncak (dari K puncak teratas ROI '
             'menurut nilai sinyal) dalam jarak toleransi. Acak ~ K/jumlah_puncak.',
             '',
             '| acuan | P@1 | P@2 | P@5 | P@10 | median peringkat |',
             '|---|---|---|---|---|---|']
    for m in MODES:
        r = results[m]
        lines.append(f'| {m} | {r["apex_precision_at_1"]:.4f} | {r["apex_precision_at_2"]:.4f} | '
                     f'{r["apex_precision_at_5"]:.4f} | {r["apex_precision_at_10"]:.4f} | '
                     f'{r["median_rank_pct"]:.3f} |')
    (args.out / 'summary.md').write_text('\n'.join(lines) + '\n')
    print(f'\nKeluaran: {args.out}/summary.md')


if __name__ == '__main__':
    main()

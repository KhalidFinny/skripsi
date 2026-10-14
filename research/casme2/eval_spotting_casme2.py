#!/usr/bin/env python
"""Benchmark spotting POC-ABS pada CAS(ME)^2 (ground truth onset/apex/offset).

Fokus A: memberi tahap spotting angka akurasi ber-ground-truth pertama. Sinyal
(POC-ABS per ROI vs frame-0) dan detektor (ApexPhase) yang diuji adalah yang
SAMA dengan `pipeline/stages/stage_1_spotting.py` -- diimpor, bukan disalin --
jadi hasilnya mengukur pipeline ini apa adanya.

Ground truth: CAS(ME)^2 `code_final.xlsx`, 356 ekspresi berlabel onset/apex/
offset dan tipe (299 macro / 57 micro). Micro-expression adalah kasus tersulit
dan paling relevan, jadi metriknya dipisah macro vs micro.

Cara pakai:
    .venv/bin/python scripts/eval_spotting_casme2.py
    .venv/bin/python scripts/eval_spotting_casme2.py --limit 3   # uji cepat
"""

from __future__ import annotations

import argparse
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT, ROOT / 'pipeline' / 'stages'):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import stage_1_spotting as spot  # aman diimpor: eksekusi ada di main()

DEFAULT_GT = Path(os.environ.get(
    'CASME2_GT', '/home/finny/datasets/casme2/annotations/casme2_code_final.xlsx'))
DEFAULT_VIDEOS = Path(os.environ.get('CASME2_VIDEOS', '/home/finny/datasets/casme2/rawvideo'))
DEFAULT_OUT = ROOT / 'output/training/spotting_casme2'
DEFAULT_SIGNAL_CACHE = ROOT / 'output/training/spotting_casme2_signals'
PREDICTOR = ROOT / 'models/shape_predictor_68_face_landmarks.dat'

# Ekspresi CAS(ME)^2 diberi nama "<emosi><n>_<urut>"; nama itu tidak sama dgn
# nama file video. Sheet "naming rule" memetakan keduanya.
GT_COL_PARTICIPANT = 0
GT_COL_EXPRESSION = 1
GT_COL_ONSET = 2
GT_COL_APEX = 3
GT_COL_OFFSET = 4
GT_COL_TYPE = 7


def load_ground_truth(gt_path: Path, videos_root: Path) -> pd.DataFrame:
    """Ground truth per ekspresi, sudah dipetakan ke file video.

    Baris tanpa anotasi lengkap (offset <= 0, dsb.) dibuang: itu ekspresi yang
    tidak diselesaikan anotatornya, bukan sinyal untuk diukur.
    """
    code = pd.read_excel(gt_path, sheet_name=0)
    naming = pd.read_excel(gt_path, sheet_name=1, header=None)
    emotion = pd.read_excel(gt_path, sheet_name=2, header=None)

    idx_to_subject = dict(zip(naming[2].astype(int), naming[1].astype(str)))
    clip_to_code = {str(row[1]).strip(): f'{int(row[0]):04d}' for _, row in emotion.iterrows()}

    rows = []
    for _, r in code.iterrows():
        onset, apex, offset = int(r.iloc[GT_COL_ONSET]), int(r.iloc[GT_COL_APEX]), int(r.iloc[GT_COL_OFFSET])
        if min(onset, apex, offset) <= 0 or not (onset <= apex <= offset):
            continue
        subject = idx_to_subject.get(int(r.iloc[GT_COL_PARTICIPANT]))
        clip = str(r.iloc[GT_COL_EXPRESSION]).rsplit('_', 1)[0]
        clip_code = clip_to_code.get(clip)
        if subject is None or clip_code is None:
            continue
        matches = sorted((videos_root / subject).glob(f'{subject[1:]}_{clip_code}*.avi'))
        if not matches:
            continue
        rows.append({
            'subject': subject,
            'expression': str(r.iloc[GT_COL_EXPRESSION]),
            'video': str(matches[0]),
            'onset': onset,
            'apex': apex,
            'offset': offset,
            'expr_type': 'micro' if 'micro' in str(r.iloc[GT_COL_TYPE]).lower() else 'macro',
        })
    return pd.DataFrame(rows)


def signals_for_video(video: Path) -> dict[str, list[float]]:
    """Sinyal POC-ABS per ROI untuk satu video (bagian yang MAHAL).

    Frame di-STRIM lewat `iter_video_frames`, bukan dimuat semua: video CAS(ME)^2
    bisa 4370 frame (~4 GB bila dijadikan list) dan itu yang membuat proses
    dibunuh OOM killer.
    """
    n_frames = spot.count_video_frames(video)
    if n_frames < 5:
        return {}
    roi_signals = spot.build_roi_signals(
        spot.iter_video_frames(video), spot.WORKER_DETECTOR, spot.WORKER_PREDICTOR,
        frame_count=n_frames,
    )
    if not roi_signals or any(len(v) == 0 for v in roi_signals.values()):
        return {}
    return roi_signals


def detect_from_signals(roi_signals: dict[str, list[float]],
                        params: spot.DetectParams) -> list[dict]:
    """Event (indeks FRAME video) dari sinyal yang SUDAH dihitung. Bagian ini murah,
    jadi beberapa kombinasi parameter cukup dijalankan di proses utama.

    Mengikuti `spot.SPOT_SIGNAL_MODE` supaya yang diukur benar-benar perilaku
    pipeline: 'global_mean' = satu sinyal mean antar-ROI, 'roi_signals' = per-ROI.
    """
    if not roi_signals:
        return []
    if spot.SPOT_SIGNAL_MODE == 'roi_signals':
        _smoothed, events, _meta = spot.detect_events_per_roi(roi_signals, params)
    else:
        _smoothed, events, _meta = spot.detect_events(spot.build_global_signal(roi_signals), params)
    return [{
        'onset': spot.signal_index_to_frame_index(e['onset_signal']),
        'apex': spot.signal_index_to_frame_index(e['apex_signal']),
        'offset': spot.signal_index_to_frame_index(e['offset_signal']),
        'region': e['region'],
    } for e in events]


def cache_path(cache_dir: Path | None, video: Path) -> Path | None:
    if cache_dir is None:
        return None
    # Nama video sudah memuat nomor subjek (mis. 15_0102eatingworms), tapi
    # direktorinya ikut dipakai supaya tidak ada tabrakan antar-subjek.
    return cache_dir / f'{video.parent.name}_{video.stem}.npz'


def load_cached_signals(path: Path) -> dict[str, list[float]] | None:
    if not path.exists():
        return None
    try:
        with np.load(path) as z:
            return {r: z[r].astype(float).tolist() for r in z.files}
    except (OSError, ValueError):
        return None


def save_cached_signals(path: Path, signals: dict[str, list[float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    arrays = {r: np.asarray(v, dtype=float) for r, v in signals.items()}
    # Ditulis lewat file object: kalau diberi NAMA file yang tidak berakhiran
    # `.npz`, numpy menambahkan `.npz` sendiri sehingga file tmp tidak ada di
    # path yang diharapkan saat rename.
    with open(tmp, 'wb') as fh:
        np.savez_compressed(fh, **arrays)
    tmp.replace(path)


def worker(job: tuple[str, list[dict], str | None]) -> tuple[str, dict, list[dict]]:
    video_path, gt_rows, cache_file = job
    path = Path(cache_file) if cache_file else None
    if path is not None:
        cached = load_cached_signals(path)
        if cached is not None:
            return video_path, cached, gt_rows
    try:
        signals = signals_for_video(Path(video_path))
    except Exception as exc:  # video rusak / wajah tak terdeteksi: catat, jangan hentikan run
        return video_path, {}, [{'error': repr(exc), **gt_rows[0]}]
    if path is not None and signals:
        save_cached_signals(path, signals)
    return video_path, signals, gt_rows


def match_events(gt: list[dict], det: list[dict], tol: int) -> tuple[list, list, list]:
    """Pasangkan deteksi ke ground truth secara satu-ke-satu.

    Dua event dianggap bersinggungan kalau intervalnya beririsan setelah GT
    dilebarkan `tol` frame di kedua sisi. Setiap GT diambil deteksi yang apexnya
    paling dekat, supaya pasangan yang dipilih adalah yang paling masuk akal,
    bukan yang kebetulan ditemukan lebih dulu.
    """
    gt_sorted = sorted(gt, key=lambda x: x['onset'])
    pairs, used_det, used_gt = [], set(), set()
    for gi, g in enumerate(gt_sorted):
        best, best_dist = None, None
        for di, d in enumerate(det):
            if di in used_det:
                continue
            if d['onset'] <= g['offset'] + tol and g['onset'] - tol <= d['offset']:
                dist = abs(d['apex'] - g['apex'])
                if best_dist is None or dist < best_dist:
                    best, best_dist = di, dist
        if best is not None:
            used_det.add(best)
            used_gt.add(gi)
            pairs.append((det[best], g))
    fp = [d for di, d in enumerate(det) if di not in used_det]
    fn = [g for gi, g in enumerate(gt_sorted) if gi not in used_gt]
    return pairs, fp, fn


def nearest_gt_type(fp: dict, gt: list[dict]) -> str:
    """Tipe GT terdekat dari sebuah deteksi salah (untuk memecah FP per tipe)."""
    if not gt:
        return 'macro'
    nearest = min(gt, key=lambda g: abs(fp['apex'] - g['apex']))
    return nearest['expr_type']


def scores(tp: int, fp: int, fn: int) -> dict:
    precision = tp / (tp + fp) if tp + fp else float('nan')
    recall = tp / (tp + fn) if tp + fn else float('nan')
    # F1 hanya tak terdefinisi kalau precision DAN recall dua-duanya tak ada
    # (tidak ada GT dan tidak ada deteksi). precision=0 harus memberi F1=0,
    # bukan NaN.
    if np.isnan(precision) and np.isnan(recall):
        f1 = float('nan')
    elif np.isnan(precision):
        f1 = 0.0
    elif np.isnan(recall):
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {'tp': tp, 'fp': fp, 'fn': fn, 'precision': precision, 'recall': recall, 'f1': f1}


def compute_signals(gt_df: pd.DataFrame, workers: int,
                    cache_dir: Path | None) -> tuple[dict[str, tuple[dict, list[dict]]], list[dict]]:
    """Hitung sinyal POC-ABS SEKALI per video -> {video: (sinyal, ground_truth)}.

    Sinyal TIDAK bergantung pada parameter deteksi, jadi dihitung sekali lalu
    dipakai ulang untuk semua kombinasi parameter. Bagian ini yang mahal
    (dlib + POC per frame), karena itu di-paralel dan di-cache ke disk.
    """
    by_video: dict[str, list[dict]] = {}
    for _, r in gt_df.iterrows():
        by_video.setdefault(r['video'], []).append(r.to_dict())

    jobs = [(v, gt, str(cache_path(cache_dir, Path(v))) if cache_dir else None)
            for v, gt in sorted(by_video.items())]
    out: dict[str, tuple[dict, list[dict]]] = {}
    errors: list[dict] = []
    with ProcessPoolExecutor(
        max_workers=workers,
        initializer=spot.init_worker,
        initargs=(str(PREDICTOR),),
    ) as executor:
        futures = {executor.submit(worker, job): job[0] for job in jobs}
        for i, future in enumerate(as_completed(futures), start=1):
            video_path, signals, gt = future.result()
            if gt and 'error' in gt[0]:
                errors.append(gt[0])
                print(f'[{i}/{len(jobs)}] GAGAL {Path(video_path).name}: {gt[0]["error"]}', flush=True)
                continue
            out[video_path] = (signals, gt)
            print(f'[{i}/{len(jobs)}] {Path(video_path).name}: gt={len(gt)} '
                  f'frames={len(next(iter(signals.values()))) if signals else 0}', flush=True)
    return out, errors


def evaluate(signals_map: dict, gt_df: pd.DataFrame, tol: int, n_errors: int,
             params: spot.DetectParams) -> tuple[dict, list, list]:
    """Deteksi dari sinyal yang sudah dihitung, lalu cocokkan dengan GT.

    Deteksi (find_peaks) jauh lebih murah daripada perhitungan sinyal, jadi
    beberapa kombinasi parameter cukup memanggil ulang fungsi ini.
    """
    all_pairs, all_fp, all_fn = [], [], []
    for video_path, (signals, gt) in signals_map.items():
        det = detect_from_signals(signals, params)
        pairs, fp, fn = match_events(gt, det, tol)
        all_pairs.extend((video_path, d, g) for d, g in pairs)
        all_fp.extend((video_path, d) for d in fp)
        all_fn.extend((video_path, g) for g in fn)

    overall = scores(len(all_pairs), len(all_fp), len(all_fn))
    per_type = {}
    gt_records = gt_df.to_dict('records')
    for t in ('macro', 'micro'):
        n_gt = int((gt_df['expr_type'] == t).sum())
        tp = sum(1 for _, _, g in all_pairs if g['expr_type'] == t)
        fn = sum(1 for _, g in all_fn if g['expr_type'] == t)
        fp = sum(1 for _, d in all_fp if nearest_gt_type(d, gt_records) == t)
        per_type[t] = {'n_gt': n_gt, **scores(tp, fp, fn)}

    apex_err = [abs(d['apex'] - g['apex']) for _, d, g in all_pairs]
    detail = {
        'tol': tol,
        'n_videos': len(signals_map),
        'n_gt': len(gt_df),
        'n_det': len(all_pairs) + len(all_fp),
        'apex_err_median': float(np.median(apex_err)) if apex_err else float('nan'),
        'apex_err_mean': float(np.mean(apex_err)) if apex_err else float('nan'),
        'n_errors': n_errors,
        **overall,
    }
    return {'overall': detail, 'per_type': per_type}, all_pairs, all_fp


def _fmt(v: float) -> str:
    return 'n/a' if v is None or (isinstance(v, float) and np.isnan(v)) else f'{v:.4f}'


def write_summary(out_dir: Path, grid: list[dict], best: dict, results: dict,
                  gt_df: pd.DataFrame, errors: int, tolerances: list[int],
                  primary_tol: int, default_params: spot.DetectParams) -> None:
    lines = ['# Benchmark spotting POC-ABS pada CAS(ME)^2', '',
             'Sinyal & detektor = yang dipakai `pipeline/stages/stage_1_spotting.py` '
             '(diimpor langsung).',
             'Ground truth onset/apex/offset dari `code_final.xlsx`.',
             '',
             f'- video: {grid[0]["o"]["n_videos"]}'
             f' | ekspresi GT: {len(gt_df)} | error video: {errors}',
             f'- micro {int((gt_df["expr_type"] == "micro").sum())}, '
             f'macro {int((gt_df["expr_type"] == "macro").sum())}',
             f'- default pipeline (pembanding): top_k={default_params.top_k}, '
             f'prom_rel={default_params.prom_rel}, thresh={default_params.thresh}',
             '',
             f'## Grid parameter (toleransi {primary_tol} frame)', '',
             'Baris = kombinasi parameter. Kolom detik = rata-rata deteksi per video '
             '(GT rata-rata '
             f'{len(gt_df) / max(1, grid[0]["o"]["n_videos"]):.1f}).', '',
             '| top_k | prom_rel | thresh | precision | recall | F1 | recall micro | recall macro | det/video |',
             '|---|---|---|---|---|---|---|---|---|']
    for g in grid:
        o, pt = g['o'], g['pt']
        dv = o['n_det'] / max(1, o['n_videos'])
        mark = ' **<- terbaik**' if g is best else ''
        lines.append(
            f'| {g["top_k"]} | {g["prom_rel"]} | {g["thresh"]} | {_fmt(o["precision"])} | '
            f'{_fmt(o["recall"])} | {_fmt(o["f1"])} | {_fmt(pt["micro"]["recall"])} | '
            f'{_fmt(pt["macro"]["recall"])} | {dv:.1f}{mark} |')
    lines.append('')

    lines += ['## Detail kombinasi terbaik', '',
              f'`top_k={best["top_k"]}, prom_rel={best["prom_rel"]}, thresh={best["thresh"]}` '
              f'(dipilih dari F1 tertinggi pada toleransi {primary_tol}).', '']
    for tol in tolerances:
        o, pt = results[tol]['overall'], results[tol]['per_type']
        lines += [f'### Toleransi {tol} frame', '',
                  '| metrik | nilai |', '|---|---|',
                  f'| precision | {_fmt(o["precision"])} |',
                  f'| recall | {_fmt(o["recall"])} |',
                  f'| F1 | {_fmt(o["f1"])} |',
                  f'| TP / FP / FN | {o["tp"]} / {o["fp"]} / {o["fn"]} |',
                  f'| deteksi per video | {o["n_det"] / max(1, o["n_videos"]):.1f} |',
                  f'| error apex (median frame) | {o["apex_err_median"]:.1f} |',
                  '',
                  '| tipe | n GT | precision | recall | F1 |', '|---|---|---|---|---|']
        for t in ('macro', 'micro'):
            m = pt[t]
            lines.append(f'| {t} | {m["n_gt"]} | {_fmt(m["precision"])} | '
                         f'{_fmt(m["recall"])} | {_fmt(m["f1"])} |')
        lines.append('')

    lines += ['Catatan:',
              '- FP tiap tipe dihitung dari deteksi salah yang GT terdekatnya bertipe itu, '
              'jadi precision per tipe adalah perkiraan.',
              '- Micro-expression hanya 57 dari 308 ekspresi ber-anotasi; recall micro '
              'adalah angka yang paling menentukan untuk klaim "bisa micro-expression".',
              '- Sinyal POC-ABS dihitung sekali lalu di-cache; grid parameter hanya '
              'mengulang tahap deteksi (murah), jadi angka antar baris sebanding.',
              '- Frame GT dianggap berada di ruang indeks frame yang sama dengan pembacaan '
              'OpenCV (selisih 1 frame bila konvensi aslinya 1-based; diabaikan karena '
              'jauh lebih kecil dari durasi ekspresi).']
    (out_dir / 'summary.md').write_text('\n'.join(lines) + '\n')


def main() -> None:
    parser = argparse.ArgumentParser(description='Benchmark spotting POC-ABS pada CAS(ME)^2.')
    parser.add_argument('--gt', type=Path, default=DEFAULT_GT)
    parser.add_argument('--videos', type=Path, default=DEFAULT_VIDEOS)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--tolerances', type=int, nargs='+', default=[0, 5])
    parser.add_argument('--limit', type=int, default=None, help='batasi jumlah video (uji cepat)')
    parser.add_argument('--workers', type=int, default=3,
                        help='jumlah proses paralel. Default 3: tiap worker menyimpan model '
                             'dlib + sinyal, dan video panjang pernah membuat 4 worker '
                             'menembus RAM sampai dibunuh OOM killer.')
    parser.add_argument('--top-k', type=int, nargs='+', default=None,
                        help='satu atau beberapa nilai top_k per ROI. Default = nilai pipeline '
                             'sekarang. Contoh grid: --top-k 1 2 3')
    parser.add_argument('--prom-rel', type=float, nargs='+', default=None,
                        help='satu atau beberapa nilai prominence relatif. Default = nilai '
                             'pipeline sekarang. Contoh: --prom-rel 0.04 0.10 0.20')
    parser.add_argument('--thresh', nargs='+', choices=['meanstd', 'mad'], default=None,
                        help='mode ambang tinggi puncak. meanstd = mean+std (pipeline sekarang); '
                             'mad = median + 2.5*1.4826*MAD (lebih tahan outlier).')
    parser.add_argument('--signal-cache', type=Path, default=DEFAULT_SIGNAL_CACHE,
                        help='folder cache sinyal POC-ABS (dipakai ulang antar-run).')
    parser.add_argument('--no-cache', action='store_true', help='jangan pakai cache sinyal.')
    args = parser.parse_args()

    for path, label in ((args.gt, 'ground truth'), (args.videos, 'folder video'), (PREDICTOR, 'predictor')):
        if not path.exists():
            raise SystemExit(f'{label} tidak ditemukan: {path}')

    default_params = spot.resolve_detect_params(None)
    top_ks = args.top_k or [default_params.top_k]
    prom_rels = args.prom_rel or [default_params.prom_rel]
    threshes = args.thresh or [default_params.thresh]

    gt_df = load_ground_truth(args.gt, args.videos)
    if args.limit:
        keep = sorted(gt_df['video'].unique())[:args.limit]
        gt_df = gt_df[gt_df['video'].isin(keep)]
    print(f'GT: {len(gt_df)} ekspresi pada {gt_df["video"].nunique()} video '
          f'(micro {int((gt_df["expr_type"] == "micro").sum())}, '
          f'macro {int((gt_df["expr_type"] == "macro").sum())})')
    print(f'Grid: top_k={top_ks} x prom_rel={prom_rels} x thresh={threshes} '
          f'({len(top_ks) * len(prom_rels) * len(threshes)} kombinasi) | default pipeline: '
          f'top_k={default_params.top_k}, prom_rel={default_params.prom_rel}, '
          f'thresh={default_params.thresh}')

    args.out.mkdir(parents=True, exist_ok=True)
    cache_dir = None if args.no_cache else args.signal_cache
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
    signals_map, errors = compute_signals(gt_df, max(1, args.workers), cache_dir)
    print(f'Sinyal selesai: {len(signals_map)} video, {len(errors)} gagal')

    primary_tol = args.tolerances[0]
    grid = []
    for top_k in top_ks:
        for prom_rel in prom_rels:
            for thresh in threshes:
                params = spot.DetectParams(top_k=top_k, prom_rel=prom_rel, thresh=thresh)
                res, pairs, fp = evaluate(signals_map, gt_df, primary_tol, len(errors), params)
                o = res['overall']
                grid.append({'top_k': top_k, 'prom_rel': prom_rel, 'thresh': thresh,
                             'o': o, 'pt': res['per_type'], 'pairs': pairs, 'fp': fp})
                print(f'  top_k={top_k} prom_rel={prom_rel} thresh={thresh}: '
                      f'P={o["precision"]:.4f} R={o["recall"]:.4f} F1={o["f1"]:.4f} '
                      f'(det/video {o["n_det"] / max(1, o["n_videos"]):.1f})', flush=True)

    best = max(grid, key=lambda g: (-1 if np.isnan(g['o']['f1']) else g['o']['f1']))
    best_params = spot.DetectParams(top_k=best['top_k'], prom_rel=best['prom_rel'],
                                    thresh=best['thresh'])
    results = {tol: evaluate(signals_map, gt_df, tol, len(errors), best_params)[0]
               for tol in args.tolerances}

    pd.DataFrame([{'video': Path(v).name, 'gt': g['expression'], 'gt_type': g['expr_type'],
                   'gt_onset': g['onset'], 'gt_apex': g['apex'], 'gt_offset': g['offset'],
                   'det_onset': d['onset'], 'det_apex': d['apex'], 'det_offset': d['offset'],
                   'det_region': d['region'], 'apex_err': abs(d['apex'] - g['apex'])}
                  for v, d, g in best['pairs']]).to_csv(args.out / 'matched.csv', index=False)
    pd.DataFrame([{'video': Path(v).name, 'det_onset': d['onset'], 'det_apex': d['apex'],
                   'det_offset': d['offset'], 'det_region': d['region'], 'kind': 'fp'}
                  for v, d in best['fp']]).to_csv(args.out / 'false_positives.csv', index=False)

    write_summary(args.out, grid, best, results, gt_df, len(errors),
                  args.tolerances, primary_tol, default_params)
    print(f'\nTerbaik: top_k={best["top_k"]}, prom_rel={best["prom_rel"]}, '
          f'thresh={best["thresh"]} -> F1 {best["o"]["f1"]:.4f}')
    print(f'Keluaran: {args.out}/summary.md')


if __name__ == '__main__':
    main()

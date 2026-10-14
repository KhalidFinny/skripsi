#!/usr/bin/env python
"""Hitung + cache sinyal POC-ABS KAYA per ROI untuk semua video CAS(ME)^2.

Sinyal yang dihitung per ROI (acuan frame-0, sama seperti pipeline):
  mean_m, max_m, motion_count, mean_x, mean_y, angle_R

Bedanya dari `spot.build_roi_signals` yang hanya menyimpan mean magnitudo:
di sini arah (mean_x/mean_y) dan koherensi sudut (angle_R) ikut disimpan,
karena itulah yang terbukti menaikkan AUC (Iterasi 4.47).

Hasil di-cache ke .npz per video supaya eksperimen klasifikasi bisa diulang
tanpa menghitung ulang POC (yang mahal).

Cara pakai:
    .venv/bin/python scripts/rich_signals_casme2.py
    .venv/bin/python scripts/rich_signals_casme2.py --workers 3
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
from features.quadran import Quadran  # noqa: E402
from features.vektor import Vektor  # noqa: E402

DEFAULT_CACHE = ROOT / 'output/training/casme2_rich_signals'
SIGNALS = ('mean_m', 'max_m', 'motion_count', 'mean_x', 'mean_y', 'angle_R')


def signals_for_video(video: str) -> dict[str, list[float]]:
    """{signal: nilai per frame} untuk SATU ROI ('global'), dipakai lintas ROI.

    Nama kunci = "<roi>__<signal>" supaya satu npz memuat semua ROI.
    """
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
    out: dict[str, list[float]] = {f'{r}__{s}': [] for r in regions for s in SIGNALS}
    for i in range(1, len(grays)):
        cur_lm = lms[i]
        for r, idx in regions.items():
            vals = None
            if cur_lm is not None:
                try:
                    a = spot.extract_region(grays[0], lms[0], idx)
                    c = spot.extract_region(grays[i], cur_lm, idx)
                    if a.size and c.size:
                        tw, th = spot.config.target_size[r]
                        poc = POC(cv2.resize(a, (tw, th)), cv2.resize(c, (tw, th)), spot.config.block_size)
                        q = Quadran(Vektor(poc.getPOC(), spot.config.block_size).getVektor()).getQuadran()
                        m = np.array([float(x[4]) for x in q], float)
                        xs = np.array([float(x[1]) for x in q], float)
                        ys = np.array([float(x[2]) for x in q], float)
                        moving = m > 0
                        if moving.any():
                            th_ = np.arctan2(ys[moving], xs[moving])
                            cos_m, sin_m = float(np.mean(np.cos(th_))), float(np.mean(np.sin(th_)))
                        else:
                            cos_m = sin_m = 0.0
                        vals = {
                            'mean_m': float(m.mean()) if m.size else np.nan,
                            'max_m': float(m.max()) if m.size else np.nan,
                            'motion_count': float(moving.mean()) if m.size else np.nan,
                            'mean_x': float(xs.mean()) if xs.size else np.nan,
                            'mean_y': float(ys.mean()) if ys.size else np.nan,
                            'angle_R': float(np.hypot(cos_m, sin_m)),
                        }
                except Exception:
                    vals = None
            for s in SIGNALS:
                out[f'{r}__{s}'].append(vals[s] if vals else np.nan)

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


def worker(job: tuple[str, str]) -> tuple[str, bool, str]:
    video, cache_path = job
    path = Path(cache_path)
    if load(path) is not None:
        return video, True, 'cached'
    try:
        sig = signals_for_video(video)
    except Exception as exc:  # video rusak: catat, jangan hentikan run
        return video, False, repr(exc)
    if not sig:
        return video, False, 'sinyal kosong'
    save(path, sig)
    return video, True, f'{len(next(iter(sig.values())))} frame'


def main() -> None:
    ap = argparse.ArgumentParser(description='Cache sinyal POC-ABS kaya (CAS(ME)^2).')
    ap.add_argument('--cache-dir', type=Path, default=DEFAULT_CACHE)
    ap.add_argument('--workers', type=int, default=3)
    ap.add_argument('--limit', type=int, default=None)
    args = ap.parse_args()

    gt = bench.load_ground_truth(bench.DEFAULT_GT, bench.DEFAULT_VIDEOS)
    videos = sorted(gt['video'].unique())
    if args.limit:
        videos = videos[:args.limit]
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    print(f'video: {len(videos)} | cache: {args.cache_dir}')

    jobs = [(v, str(cache_file(args.cache_dir, v))) for v in videos]
    ok = fail = 0
    with ProcessPoolExecutor(max_workers=max(1, args.workers),
                             initializer=spot.init_worker,
                             initargs=(str(bench.PREDICTOR),)) as ex:
        futures = {ex.submit(worker, j): j[0] for j in jobs}
        for i, fut in enumerate(as_completed(futures), 1):
            video, success, info = fut.result()
            ok += success
            fail += (not success)
            if not success:
                print(f'  [{i}/{len(jobs)}] GAGAL {Path(video).name}: {info}', flush=True)
            elif i % 10 == 0 or info == 'cached':
                print(f'  [{i}/{len(jobs)}] {Path(video).name}: {info}', flush=True)
    print(f'\nSelesai: {ok} ok, {fail} gagal')


if __name__ == '__main__':
    main()

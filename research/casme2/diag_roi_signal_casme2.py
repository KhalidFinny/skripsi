#!/usr/bin/env python
"""Diagnostik dasar: apakah crop ROI dan pengukuran sinyal saya benar?

Dua kecurigaan pada pengukuran SEBELUMNYA (bukan pada metode):
  1. "persentil sinyal di apex = 0,988" dihitung dari MAX dalam jendela +/-5
     frame, bukan nilai DI apex. Mengambil max lalu menanyakan persentilnya
     selalu tinggi secara artifisial.
  2. Crop ROI belum pernah diperiksa secara visual untuk CAS(ME)^2.

Skrip ini:
  - menyimpan montase crop 5 ROI (dengan kotak landmark) untuk dilihat
  - menghitung persentil sinyal DI frame apex (bukan max jendela)
  - menghitung korelasi silang sinyal vs penanda GT, untuk mencari geseran

Cara pakai:
    .venv/bin/python scripts/diag_roi_signal_casme2.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT, ROOT / 'pipeline' / 'stages'):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import eval_spotting_casme2 as bench  # noqa: E402
import stage_1_spotting as spot  # noqa: E402
import rich_signals_casme2 as rich  # noqa: E402
from apex import ApexSmoother  # noqa: E402


def save_roi_montage(video: Path, frame_idx: int, out_path: Path) -> None:
    cap = cv2.VideoCapture(str(video))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        print(f'  gagal baca frame {frame_idx}')
        return
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    lm = spot.detect_landmarks(gray, spot.WORKER_DETECTOR, spot.WORKER_PREDICTOR)
    if lm is None:
        print('  landmark tidak terdeteksi')
        return
    tiles = []
    full = frame.copy()
    for r, idx in spot.config.regions.items():
        pts = lm[idx].astype(int)
        cv2.polylines(full, [pts.reshape(-1, 1, 2)], True, (0, 255, 0), 1)
        x0, y0 = pts.min(axis=0) - [spot.config.padding_x, spot.config.padding_y]
        x1, y1 = pts.max(axis=0) + [spot.config.padding_x, spot.config.padding_y]
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(frame.shape[1], x1), min(frame.shape[0], y1)
        crop = frame[y0:y1, x0:x1]
        tw, th = spot.config.target_size[r]
        crop = cv2.resize(crop, (tw, th))
        crop = cv2.resize(crop, (tw * 4, th * 4), interpolation=cv2.INTER_NEAREST)
        cv2.putText(crop, r, (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        tiles.append(crop)
    h = max(t.shape[0] for t in tiles)
    tiles = [cv2.copyMakeBorder(t, 0, h - t.shape[0], 0, 6, cv2.BORDER_CONSTANT, value=(40, 40, 40)) for t in tiles]
    strip = np.hstack(tiles)
    full = cv2.resize(full, (strip.shape[1], int(full.shape[0] * strip.shape[1] / full.shape[1])))
    cv2.imwrite(str(out_path), np.vstack([full, strip]))
    print(f'  montase ROI: {out_path}')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--videos', type=int, default=3)
    ap.add_argument('--out', type=Path, default=ROOT / 'output/training/diag_roi_casme2')
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    gt = bench.load_ground_truth(bench.DEFAULT_GT, bench.DEFAULT_VIDEOS)
    gt_by_video = {v: g.to_dict('records') for v, g in gt.groupby('video')}
    spot.init_worker(str(bench.PREDICTOR))

    # ---- 1. montase ROI ----
    for v in sorted(gt_by_video)[:args.videos]:
        g = gt_by_video[v]
        apex = g[0]['apex'] if g else 300
        save_roi_montage(Path(v), int(apex), args.out / f'roi_{Path(v).stem}.png')

    # ---- 2. persentil sinyal DI apex (perbaikan pengukuran) ----
    print('\n=== persentil sinyal DI frame apex (bukan max jendela) ===')
    vals_at, vals_win = [], []
    for v in sorted(gt_by_video):
        sig = rich.load(rich.cache_file(rich.DEFAULT_CACHE, v))
        if sig is None:
            continue
        for x in gt_by_video[v]:
            fi = x['apex'] - 1
            if fi < 0:
                continue
            best_at = best_win = -1.0
            for roi in spot.config.regions:
                key = f'{roi}__mean_m'
                if key not in sig:
                    continue
                arr = np.asarray(sig[key], dtype=float)
                if fi >= len(arr):
                    continue
                sm = np.asarray(ApexSmoother.smooth(arr.tolist()), dtype=float)
                if fi >= len(sm):
                    continue
                best_at = max(best_at, float((sm <= sm[fi]).mean()))
                lo, hi = max(0, fi - 5), min(len(sm), fi + 6)
                best_win = max(best_win, float((sm <= sm[lo:hi].max()).mean()))
            if best_at >= 0:
                vals_at.append(best_at)
                vals_win.append(best_win)
    va, vw = np.array(vals_at), np.array(vals_win)
    print(f'  nilai DI apex   : median persentil = {np.median(va):.3f} '
          f'(proporsi >0,90 = {(va > 0.90).mean():.3f})')
    print(f'  max jendela +/-5: median persentil = {np.median(vw):.3f} '
          f'(proporsi >0,90 = {(vw > 0.90).mean():.3f})   <- pengukuran lama')
    print('  (kalau angka pertama jauh lebih rendah, "0,988" sebelumnya memang '
          'artefak pengukuran)')

    # ---- 3. korelasi silang: apakah ada geseran sistematis? ----
    print('\n=== korelasi silang sinyal vs penanda GT (cari geseran) ===')
    shifts = []
    for v in sorted(gt_by_video):
        sig = rich.load(rich.cache_file(rich.DEFAULT_CACHE, v))
        if sig is None:
            continue
        key = 'mulut__mean_m'
        if key not in sig:
            continue
        sm = np.asarray(ApexSmoother.smooth(np.asarray(sig[key], float).tolist()), dtype=float)
        sm = (sm - sm.mean()) / (sm.std() + 1e-9)
        marker = np.zeros(len(sm))
        for x in gt_by_video[v]:
            a, b = max(0, x['onset'] - 1), min(len(marker), x['offset'])
            if b > a:
                marker[a:b] = 1.0
        if marker.sum() < 2:
            continue
        marker = (marker - marker.mean()) / (marker.std() + 1e-9)
        corr = np.correlate(sm, marker, mode='full') / len(sm)
        lag = int(np.argmax(corr) - (len(marker) - 1))
        shifts.append(lag)
    sh = np.array(shifts)
    print(f'  n video: {len(sh)} | geseran optimum median = {np.median(sh):.0f} frame')
    print(f'  distribusi: {np.percentile(sh, [10, 25, 50, 75, 90]).round(0)}')
    print('  (kalau median jauh dari 0, ada geseran sistematis antar sumbu waktu)')


if __name__ == '__main__':
    main()

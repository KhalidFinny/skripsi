#!/usr/bin/env python
"""Probe sub-piksel POC + koreksi skala ROI + kegagalan landmark (CAS(ME)^2).

Plan 2026-10-13 isu 05. Temuan isu 01: magnitude terkuantisasi 15 nilai diskret
(puncak POC diambil pada lokasi integer). Skrip ini menguji tiga hal:

  int    : magnitude integer (perilaku pipeline sekarang)
  sub    : magnitude sub-piksel — koreksi parabolik 3 titik di sekitar puncak
           korelasi POC 9x9 (standar pada literatur phase correlation)
  sub+scl: sub-piksel dikoreksi skala ROI (piksel citra asli, bukan piksel
           hasil resize ke ukuran target)

Plus: fraksi frame gagal landmark dlib (penyebab interpolasi) dan posisinya
relatif terhadap rentang GT ekspresi.

Sanity check sintetis: patch digeser 0,5 px -> int harus 0, sub harus ~0,5.

Cara pakai:
    .venv/bin/python scripts/probe_spotting_mechanism_casme2.py --videos 10
"""

from __future__ import annotations

import argparse
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import cv2
import numpy as np
from scipy.signal import find_peaks, peak_prominences

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT, ROOT / 'pipeline' / 'stages'):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import eval_spotting_casme2 as bench  # noqa: E402
import stage_1_spotting as spot  # noqa: E402
from apex import ApexSmoother  # noqa: E402
from features.poc import POC  # noqa: E402


def subpixel_magnitudes(r: np.ndarray, block: int) -> tuple[np.ndarray, np.ndarray]:
    """Magnitude per blok: integer vs sub-piksel dari matriks POC r (bs,bs,n).

    Offset mengikuti konvensi Vektor: oX = puncak_x - tengah, oY = tengah - puncak_y.
    Koreksi parabolik: c = 0,5*(a-b)/(a-2m+b) pada tetangga kiri-kanan puncak.
    """
    n = r.shape[2]
    ctr = block // 2
    mag_int = np.zeros(n)
    mag_sub = np.zeros(n)
    for i in range(n):
        m = r[:, :, i]
        flat = int(np.argmax(m))
        py, px = divmod(flat, m.shape[1])
        # multi-puncak (korelasi datar, tidak ada tekstur) => 0, sama seperti Vektor
        if np.count_nonzero(m == m.max()) > 1:
            continue
        ox_i, oy_i = px - ctr, ctr - py
        mag_int[i] = float(np.hypot(ox_i, oy_i))
        # Sub-piksel JUGA diterapkan saat puncak == tengah: untuk geseran < 1 px
        # puncak integer tetap di tengah, tapi bentuk puncak korelasi miring ke
        # arah geseran — di sinilah informasi sub-piksel berada (diverifikasi
        # sintetis: 0,5 px -> 0,277; 1,0 px -> 0,987; 2,0 px -> 1,967).
        cx = cy = 0.0
        if 0 < px < m.shape[1] - 1:
            a, b, mid = m[py, px - 1], m[py, px + 1], m[py, px]
            d = a - 2 * mid + b
            if abs(d) > 1e-12:
                v = 0.5 * (a - b) / d
                cx = v if abs(v) <= 1.0 else 0.0
        if 0 < py < m.shape[0] - 1:
            a, b, mid = m[py - 1, px], m[py + 1, px], m[py, px]
            d = a - 2 * mid + b
            if abs(d) > 1e-12:
                v = 0.5 * (a - b) / d
                cy = v if abs(v) <= 1.0 else 0.0
        mag_sub[i] = float(np.hypot(ox_i + cx, oy_i - cy))
    return mag_int, mag_sub


def synthetic_check() -> None:
    """Patch digeser 0,5 px: integer harus 0, sub-piksel harus ~0,5."""
    rng = np.random.default_rng(7)
    base = rng.normal(128, 25, (9, 9)).astype(np.float32)
    m = np.float32([[1, 0, 0.5], [0, 1, 0]])
    moved = cv2.warpAffine(base, m, (9, 9), flags=cv2.INTER_LINEAR)
    poc = POC(moved, base, 9)
    r = poc.getPOC()[0]
    mi, ms = subpixel_magnitudes(r, 9)
    print(f'sanity sintetis (geser 0,5 px): int={mi[0]:.2f} sub={ms[0]:.2f} '
          f'(harapan int=0, sub≈0,3-0,5; aproksimasi parabolik meremehkan)', flush=True)


def analyze(video: str, gt_rows: list[dict]) -> dict:
    regions = spot.config.regions
    cap = cv2.VideoCapture(video)
    ok, first = cap.read()
    if not ok:
        cap.release()
        return {}
    ref_gray = cv2.cvtColor(first, cv2.COLOR_BGR2GRAY)
    ref_lm = spot.detect_landmarks(ref_gray, spot.WORKER_DETECTOR, spot.WORKER_PREDICTOR)

    per_roi: dict[str, dict[str, list[float]]] = {
        r: {'int': [], 'sub': [], 'scl': []} for r in regions}
    n_frames = 1
    fail_cur = 0
    fail_frames: list[int] = []
    if ref_lm is None:
        fail_frames.append(0)

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        idx = n_frames
        n_frames += 1
        cur_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        cur_lm = spot.detect_landmarks(cur_gray, spot.WORKER_DETECTOR, spot.WORKER_PREDICTOR)
        if ref_lm is None or cur_lm is None:
            fail_cur += 1
            fail_frames.append(idx)
            for r in regions:
                for k in per_roi[r]:
                    per_roi[r][k].append(np.nan)
            continue
        for region, lm_idx in regions.items():
            a = spot.extract_region(ref_gray, ref_lm, lm_idx)
            c = spot.extract_region(cur_gray, cur_lm, lm_idx)
            if a.size == 0 or c.size == 0:
                for k in per_roi[region]:
                    per_roi[region][k].append(np.nan)
                continue
            tw, th = spot.config.target_size[region]
            poc = POC(cv2.resize(a, (tw, th)), cv2.resize(c, (tw, th)),
                      spot.config.block_size)
            mi, ms = subpixel_magnitudes(poc.getPOC()[0], spot.config.block_size)
            scale = c.shape[1] / tw  # lebar_crop / lebar_target
            per_roi[region]['int'].append(float(mi.mean()))
            per_roi[region]['sub'].append(float(ms.mean()))
            per_roi[region]['scl'].append(float(ms.mean() * scale))
    cap.release()

    out = {'n_frames': n_frames, 'fail_cur': fail_cur, 'fail_frames': fail_frames}
    for k in ('int', 'sub', 'scl'):
        rois = {r: spot._interpolate_signal(per_roi[r][k]) for r in regions}
        if any(len(v) == 0 for v in rois.values()):
            continue
        n = len(next(iter(rois.values())))
        out[k] = [float(np.mean([rois[r][i] for r in rois])) for i in range(n)]
    return out


def rank_quality(signal: list[float], gt: list[dict]) -> float:
    sm = np.asarray(ApexSmoother.smooth(signal), dtype=float)
    if len(sm) < 10:
        return float('nan')
    pk, _ = find_peaks(sm, distance=1, height=sm.mean() + sm.std(),
                       prominence=max(0.04 * (sm.max() - sm.min()), 0.005))
    if len(pk) < 5:
        return float('nan')
    prom = peak_prominences(sm, pk)[0]
    order = np.argsort(-prom)
    rank_of = {int(pk[o]): k for k, o in enumerate(order)}
    rq = []
    for x in gt:
        cand = [int(i) for i in pk if i + 1 - 6 <= x['offset'] and x['onset'] <= i + 1 + 6]
        if cand:
            rq.append(min(rank_of[i] for i in cand) / len(pk))
    return float(np.median(rq)) if rq else float('nan')


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--videos', type=int, default=10)
    ap.add_argument('--workers', type=int, default=4)
    args = ap.parse_args()

    synthetic_check()

    gt = bench.load_ground_truth(bench.DEFAULT_GT, bench.DEFAULT_VIDEOS)
    vids_all = sorted(gt['video'].unique())
    step = max(1, len(vids_all) // args.videos)
    vids = vids_all[::step][:args.videos]

    results = {}
    with ProcessPoolExecutor(max_workers=args.workers,
                             initializer=spot.init_worker,
                             initargs=(str(bench.PREDICTOR),)) as ex:
        futs = {ex.submit(analyze, v, gt[gt.video == v].to_dict('records')): v
                for v in vids}
        for i, fut in enumerate(as_completed(futs), 1):
            v = futs[fut]
            d = fut.result()
            results[v] = d
            if d:
                gt_rows = gt[gt.video == v].to_dict('records')
                in_gt = sum(1 for x in gt_rows
                            for f in d['fail_frames']
                            if x['onset'] <= f <= x['offset'])
                d['fail_in_gt'] = in_gt
                print(f"  [{i}/{len(vids)}] {Path(v).name} gagal landmark: "
                      f"{d['fail_cur']}/{d['n_frames']} frame "
                      f"({d['fail_cur'] / max(1, d['n_frames']) * 100:.1f}%), "
                      f"{in_gt} di dalam GT", flush=True)

    ok = [d for d in results.values() if d and 'int' in d]
    print('\n=== peringkat puncak ekspresi (0=terbaik, 0,5=acak) ===')
    gt_by_video = {v: gt[gt.video == v].to_dict('records') for v in vids}
    for k, label in [('int', 'integer (sekarang)'),
                     ('sub', 'sub-piksel'),
                     ('scl', 'sub-piksel + skala')]:
        vals = [rank_quality(d[k], gt_by_video[v]) for v, d in results.items() if d and k in d]
        print(f'  {label:20s}: {np.nanmedian(vals):.3f}')


if __name__ == '__main__':
    main()

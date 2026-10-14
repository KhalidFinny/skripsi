#!/usr/bin/env python
"""DEEP DIVE magnitude POC-ABS: kuantisasi, saturasi, dilusi mean (CAS(ME)^2).

Pertanyaan yang dijawab (plan 2026-10-13, isu 01):
  1. Seberapa kasar kuantisasi magnitude per blok (block 9 -> oX/oY integer -4..4)
     dan berapa fraksi blok yang JENUH di batas pencarian (mode ABS, acuan frame-0)?
  2. Berapa fraksi blok yang bergerak saat GT ekspresi vs di luar ekspresi?
     (Kalau ekspresi hanya menggerakkan sedikit blok, MEAN menenggelamkan sinyal.)
  3. Definisi sinyal kandidat mana yang menempatkan puncak ekspresi paling atas:
     mean (sekarang) / max / mean top-25% / count blok bergerak /
     mean tertimbang puncak korelasi POC.

Metrik peringkat: seperti probe_signal_casme2, tapi urutan puncak memakai
PROMINENCE (resep deteksi baru), bukan nilai. 0 = terbaik, 0,5 = acak.

Cara pakai:
    .venv/bin/python scripts/diag_magnitude_casme2.py --videos 10
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
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
from features.quadran import Quadran  # noqa: E402
from features.vektor import Vektor  # noqa: E402

CANDIDATES = ('mean', 'max', 'top25', 'count', 'weighted')
# Sampel blok untuk histogram/saturasi dibatasi per video supaya RAM aman;
# populasi blok per video ~ n_frames x ~74 blok, lebih dari cukup untuk distribusi.
MAX_BLOCK_SAMPLES = 2_000_000


def per_block_data(video: Path) -> dict:
    """Magnitude + puncak korelasi + saturasi per blok, per frame (ABS frame-0).

    Mengembalikan agregat (histogram, counter saturasi, fraksi bergerak) dan
    sinyal kandidat per ROI; TIDAK menyimpan array per-blok mentah.
    """
    regions = spot.config.regions
    cap = cv2.VideoCapture(str(video))
    ok, first = cap.read()
    if not ok:
        cap.release()
        return {}
    ref_gray = cv2.cvtColor(first, cv2.COLOR_BGR2GRAY)
    ref_lm = spot.detect_landmarks(ref_gray, spot.WORKER_DETECTOR, spot.WORKER_PREDICTOR)

    hist = Counter()
    sat_x = sat_y = sat_both = n_blocks = 0
    roi_frames: dict[str, list[dict[str, float] | None]] = {r: [] for r in regions}

    frame_idx = 1  # sinyal ke-i mengukur frame video ke-(i+1)
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        cur_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        cur_lm = spot.detect_landmarks(cur_gray, spot.WORKER_DETECTOR, spot.WORKER_PREDICTOR)
        frame_idx += 1
        if ref_lm is None or cur_lm is None:
            for r in regions:
                roi_frames[r].append(None)
            continue
        for region, lm_idx in regions.items():
            a = spot.extract_region(ref_gray, ref_lm, lm_idx)
            c = spot.extract_region(cur_gray, cur_lm, lm_idx)
            if a.size == 0 or c.size == 0:
                roi_frames[region].append(None)
                continue
            tw, th = spot.config.target_size[region]
            poc = POC(cv2.resize(a, (tw, th)), cv2.resize(c, (tw, th)), spot.config.block_size)
            poc_out = poc.getPOC()
            q = Quadran(Vektor(poc_out, spot.config.block_size).getVektor()).getQuadran()
            mags = np.array([float(x[4]) for x in q], dtype=float)
            ox = np.array([int(x[1]) for x in q])
            oy = np.array([int(x[2]) for x in q])
            # val_max: tinggi puncak korelasi per blok (0..1) untuk bobot
            corr = poc_out[0]
            vmax = corr.max(axis=(0, 1)) if corr.ndim == 3 else np.array([float(corr.max())])
            if vmax.size != mags.size:
                vmax = np.resize(vmax, mags.size)
            lim = spot.config.block_size // 2  # 4 untuk block 9
            sx = np.abs(ox) == lim
            sy = np.abs(oy) == lim
            if n_blocks < MAX_BLOCK_SAMPLES:
                hist.update(np.round(mags, 3).tolist())
                sat_x += int(sx.sum())
                sat_y += int(sy.sum())
                sat_both += int((sx & sy).sum())
                n_blocks += mags.size
            wsum = float(vmax.sum())
            k = max(1, int(np.ceil(mags.size * 0.25)))
            roi_frames[region].append({
                'mean': float(mags.mean()),
                'max': float(mags.max()),
                'top25': float(np.sort(mags)[-k:].mean()),
                'count': float((mags > 0).mean()),
                'weighted': float((mags * vmax).sum() / wsum) if wsum > 1e-12 else 0.0,
                'moving': float((mags > 0).sum()),
                'n_blocks': float(mags.size),
            })
    cap.release()

    signals: dict[str, dict[str, list[float]]] = {}
    for cand in CANDIDATES:
        per_roi = {}
        for r in regions:
            vals = [f[cand] if f else np.nan for f in roi_frames[r]]
            per_roi[r] = spot._interpolate_signal(vals)
        if per_roi and all(len(v) for v in per_roi.values()):
            n = len(next(iter(per_roi.values())))
            per_roi = {r: v for r, v in per_roi.items()}
            signals[cand] = {
                'global': [float(np.mean([per_roi[r][i] for r in per_roi])) for i in range(n)],
            }
    moving = np.array([
        np.mean([f['moving'] / f['n_blocks'] for f in frames if f])
        if any(f for f in frames) else np.nan
        for frames in zip(*roi_frames.values())
    ])
    return {
        'hist': hist, 'sat_x': sat_x, 'sat_y': sat_y, 'sat_both': sat_both,
        'n_blocks': n_blocks, 'signals': signals, 'moving_frac': moving,
    }


def rank_quality(signal: list[float], gt: list[dict]) -> float:
    """Median peringkat relatif puncak ekspresi (urut PROMINENCE, resep baru)."""
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


def analyze(video: str, gt_rows: list[dict]) -> dict:
    d = per_block_data(Path(video))
    if not d:
        return {}
    gt_mask = np.zeros(len(d['moving_frac']), dtype=bool)
    for x in gt_rows:
        lo, hi = max(1, x['onset']) - 1, min(len(gt_mask), x['offset'])
        gt_mask[lo:hi] = True
    mv = d['moving_frac']
    d['moving_gt'] = float(np.nanmean(mv[gt_mask])) if gt_mask.any() else float('nan')
    d['moving_base'] = float(np.nanmean(mv[~gt_mask])) if (~gt_mask).any() else float('nan')
    d['ranks'] = {cand: rank_quality(sig['global'], gt_rows) for cand, sig in d['signals'].items()}
    return d


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--videos', type=int, default=10)
    ap.add_argument('--workers', type=int, default=4)
    args = ap.parse_args()

    gt = bench.load_ground_truth(bench.DEFAULT_GT, bench.DEFAULT_VIDEOS)
    vids_all = sorted(gt['video'].unique())
    step = max(1, len(vids_all) // args.videos)
    vids = vids_all[::step][:args.videos]
    n_micro = sum(1 for v in vids if (gt[(gt.video == v) & (gt.expr_type == 'micro')]).shape[0])
    print(f'{len(vids)} video (setiap ke-{step} dari {len(vids_all)}), '
          f'{sum(gt[gt.video.isin(vids)].shape[0] for _ in [0])} GT '
          f'({n_micro} micro)', flush=True)

    results = {}
    with ProcessPoolExecutor(max_workers=args.workers,
                             initializer=spot.init_worker,
                             initargs=(str(bench.PREDICTOR),)) as ex:
        futs = {ex.submit(analyze, v, gt[gt.video == v].to_dict('records')): v for v in vids}
        for i, fut in enumerate(as_completed(futs), 1):
            v = futs[fut]
            d = fut.result()
            results[v] = d
            if d:
                print(f'  [{i}/{len(vids)}] {Path(v).name} '
                      f'bergerak GT={d["moving_gt"]:.3f} baseline={d["moving_base"]:.3f}',
                      flush=True)

    ok = [d for d in results.values() if d]
    hist = Counter()
    for d in ok:
        hist.update(d['hist'])
    n_blocks = sum(d['n_blocks'] for d in ok)
    sat_x = sum(d['sat_x'] for d in ok)
    sat_y = sum(d['sat_y'] for d in ok)
    sat_both = sum(d['sat_both'] for d in ok)

    print('\n=== 1. Distribusi magnitude per blok (kuantisasi) ===')
    total = sum(hist.values())
    for val, cnt in sorted(hist.items()):
        print(f'  {val:6.3f} : {cnt / total * 100:5.2f}%')
    print(f'  nilai diskret: {len(hist)} | blok: {n_blocks:,}')
    print(f'  saturasi batas (|oX|=4): {sat_x / n_blocks * 100:.2f}% | '
          f'(|oY|=4): {sat_y / n_blocks * 100:.2f}% | keduanya: {sat_both / n_blocks * 100:.2f}%')

    print('\n=== 2. Fraksi blok bergerak (magnitude > 0) ===')
    mg = np.nanmean([d['moving_gt'] for d in ok])
    mb = np.nanmean([d['moving_base'] for d in ok])
    print(f'  saat GT ekspresi : {mg:.3f}')
    print(f'  di luar ekspresi : {mb:.3f}')
    print(f'  rasio            : {mg / mb:.2f}x')

    print('\n=== 3. Peringkat puncak ekspresi per definisi (0=terbaik, 0,5=acak) ===')
    rows = sorted(
        ((cand, np.nanmedian([d['ranks'][cand] for d in ok])) for cand in CANDIDATES),
        key=lambda kv: kv[1])
    for cand, rq in rows:
        print(f'  {cand:9s}: {rq:.3f}')
    print('\nBaseline sekarang = mean.')


if __name__ == '__main__':
    main()

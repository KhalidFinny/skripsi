#!/usr/bin/env python
"""Ulang uji acuan baseline POC (abs/lag10/lag30/seq) dengan resep deteksi baru.

Plan 2026-10-13 isu 07. Audit 2026-10-09 §4 menguji acuan dengan metrik P@k dan
resep LAMA. Diulang dengan F1 (toleransi 0) + resep baru (3% adaptif, prominence
ranking, height=mean+std, top_k=5, cutoff 0,3) pada cache baseline yang ada
(`output/training/casme2_baseline_signals`, subset video). Pembanding abs pada
subset yang sama dihitung dari cache kaya supaya apple-to-apple.

Cara pakai:
    .venv/bin/python scripts/audit_baseline_recheck_casme2.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT, ROOT / 'pipeline' / 'stages'):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import eval_spotting_casme2 as bench  # noqa: E402
import stage_1_spotting as spot  # noqa: E402
from apex import ApexPhase, ApexSmoother  # noqa: E402

BASELINE_DIR = ROOT / 'output/training/casme2_baseline_signals'
RICH_DIR = ROOT / 'output/training/casme2_rich_signals'


def detect(signal: list[float]) -> list[dict]:
    smoothed = ApexSmoother.smooth(signal)
    arr = np.asarray(smoothed, dtype=float)
    height = float(arr.mean() + arr.std())
    spread = float(arr.max() - arr.min())
    detector = ApexPhase(
        distance_threshold=1,
        prominence_threshold=max(0.04 * spread, 0.005),
        cutoff_ratio=0.3,
    )
    apex_indices = detector.find_top_k_apex(smoothed, k=5, height=height,
                                            ranking='prominence')
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


def evaluate(videos: list[str], signals: dict, gt_by_video: dict) -> dict:
    tp = fp = fn = 0
    for v in videos:
        sig = signals.get(v)
        if sig is None or len(sig) < 10:
            continue
        det = detect(sig)
        pairs, fps, fns = bench.match_events(gt_by_video[v], det, tol=0)
        tp += len(pairs)
        fp += len(fps)
        fn += len(fns)
    return bench.scores(tp, fp, fn)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.parse_args()

    gt_df = bench.load_ground_truth(bench.DEFAULT_GT, bench.DEFAULT_VIDEOS)
    gt_by_video: dict[str, list[dict]] = {}
    for _, r in gt_df.iterrows():
        gt_by_video.setdefault(r['video'], []).append(r.to_dict())

    modes = ('abs', 'lag10', 'lag30', 'seq')
    signals: dict[str, dict[str, list[float]]] = {m: {} for m in modes}
    videos = []
    for path in sorted(BASELINE_DIR.glob('*.npz')):
        cache = bench.load_cached_signals(path) or {}
        if not cache:
            continue
        # kunci: "<mode>__<roi>" (dibangun baseline_probe_casme2.py)
        by_mode: dict[str, list[list[float]]] = {m: [] for m in modes}
        for key, sig in cache.items():
            if '__' not in key:
                continue
            mode, _roi = key.split('__', 1)
            if mode in by_mode and len(sig):
                by_mode[mode].append(sig)
        # cocokkan ke video lewat nama file cache: <subdir>_<stem>.npz
        hit = [v for v in gt_by_video
               if f'{Path(v).parent.name}_{Path(v).stem}' == path.stem]
        if not hit:
            continue
        v = hit[0]
        videos.append(v)
        for m in modes:
            rois = by_mode[m]
            if rois:
                n = min(len(s) for s in rois)
                signals[m][v] = [float(np.mean([s[i] for s in rois])) for i in range(n)]

    # pembanding abs dari cache kaya (mean_m, 86 video) pada subset yang sama
    for v in videos:
        vp = Path(v)
        rich = bench.load_cached_signals(RICH_DIR / f'{vp.parent.name}_{vp.stem}.npz') or {}
        rois = [s for k, s in rich.items() if k.endswith('__mean_m') and len(s)]
        if rois:
            n = min(len(s) for s in rois)
            signals['abs'] = signals.get('abs', {})
            signals['abs'][v] = [float(np.mean([s[i] for s in rois])) for i in range(n)]

    print(f'{len(videos)} video dengan cache baseline', flush=True)
    for m in modes:
        have = [v for v in videos if v in signals.get(m, {})]
        sc = evaluate(have, signals[m], gt_by_video)
        print(f"  {m:5s}: P {sc['precision']:.4f} R {sc['recall']:.4f} "
              f"F1 {sc['f1']:.4f} ({len(have)} video)", flush=True)


if __name__ == '__main__':
    main()

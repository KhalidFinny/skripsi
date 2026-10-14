#!/usr/bin/env python
"""Sweep internals detektor spotting (merge, top_k, durasi, uptick, radius).

Plan 2026-10-13 isu 06. One-at-a-time sensitivity di sekitar resep baru
(3% adaptif, prominence ranking, height=mean+std, cutoff 0,3, global mean_m)
pada cache 86 video CAS(ME)^2. Kombinasi pemenang divalidasi split subjek A/B.

Cara pakai:
    .venv/bin/python scripts/audit_detector_internals_casme2.py
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

RICH_DIR = ROOT / 'output/training/casme2_rich_signals'

# titik sekarang (default pipeline)
BASE = dict(merge=10, top_k=5, min_dur=2, uptick=0.75, radius=100)
VARIATIONS = {
    'merge': (5, 10, 20),
    'top_k': (3, 4, 5, 6, 8),
    'min_dur': (1, 2, 4),
    'uptick': (0.5, 0.75, 0.9),
    'radius': (30, 60, 100, 200),
}


def detect(signal: list[float], p: dict) -> list[dict]:
    smoothed = ApexSmoother.smooth(signal)
    arr = np.asarray(smoothed, dtype=float)
    height = float(arr.mean() + arr.std())
    spread = float(arr.max() - arr.min())
    detector = ApexPhase(
        distance_threshold=1,
        merge_distance=p['merge'],
        prominence_threshold=max(0.04 * spread, 0.005),
        cutoff_ratio=0.3,
        valley_uptick_threshold=p['uptick'],
    )
    detector.MAX_SEARCH_RADIUS = p['radius']
    apex_indices = detector.find_top_k_apex(smoothed, k=p['top_k'], height=height,
                                            ranking='prominence')
    phases = detector.find_phase(smoothed, apex_indices) if apex_indices else {}
    events = []
    for apex_idx in apex_indices:
        phase = phases[apex_idx]
        if int(phase['end'] - phase['start']) < p['min_dur']:
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


def evaluate(videos: list[str], signals: dict, gt_by_video: dict, p: dict) -> dict:
    tp = fp = fn = tp_strict = 0
    dur: list[int] = []
    for v in videos:
        sig = signals.get(v)
        if sig is None or len(sig) < 10:
            continue
        det = detect(sig, p)
        gt = gt_by_video[v]
        pairs, fps, fns = bench.match_events(gt, det, tol=0)
        tp += len(pairs)
        fp += len(fps)
        fn += len(fns)
        tp_strict += sum(1 for d, g in pairs if iou(d, g) >= 0.5)
        dur += [d['offset'] - d['onset'] for d in det]
    sc = bench.scores(tp, fp, fn)
    n_det = tp + fp
    sc_strict = bench.scores(tp_strict, n_det - tp_strict, (tp + fn) - tp_strict)
    return {**sc, 'f1_strict': sc_strict['f1'],
            'det': n_det / max(1, len(videos)),
            'dur': int(np.median(dur)) if dur else 0}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path,
                    default=ROOT / 'output/training/audit_detector_internals_casme2')
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    gt_df = bench.load_ground_truth(bench.DEFAULT_GT, bench.DEFAULT_VIDEOS)
    gt_by_video: dict[str, list[dict]] = {}
    for _, r in gt_df.iterrows():
        gt_by_video.setdefault(r['video'], []).append(r.to_dict())
    videos = sorted(gt_by_video)
    subjects = sorted({Path(v).parent.name for v in videos})
    print(f'{len(videos)} video, {len(subjects)} subjek', flush=True)

    signals: dict[str, list[float]] = {}
    for v in videos:
        vp = Path(v)
        cache = bench.load_cached_signals(RICH_DIR / f'{vp.parent.name}_{vp.stem}.npz') or {}
        rois = [s for k, s in cache.items() if k.endswith('__mean_m') and len(s)]
        if rois:
            n = min(len(s) for s in rois)
            signals[v] = [float(np.mean([s[i] for s in rois])) for i in range(n)]

    rows = []
    r0 = evaluate(videos, signals, gt_by_video, BASE)
    rows.append(('BASE (default)', BASE.copy(), r0))
    print(f"BASE {BASE} -> F1 {r0['f1']:.4f} ketat {r0['f1_strict']:.4f} dur {r0['dur']}",
          flush=True)
    for param, values in VARIATIONS.items():
        for val in values:
            if val == BASE[param]:
                continue
            p = {**BASE, param: val}
            r = evaluate(videos, signals, gt_by_video, p)
            rows.append((f'{param}={val}', p, r))
            print(f"  {param}={val}: F1 {r['f1']:.4f} ketat {r['f1_strict']:.4f} "
                  f"det/vid {r['det']:.1f} dur {r['dur']}", flush=True)

    # kombinasi pemenang individual (diuji eksplisit; pemilihan otomatis dari
    # tabel one-at-a-time keliru karena nilai BASE ikut tertimpa run lain)
    combos = {
        'KOMBI': dict(merge=10, top_k=4, min_dur=4, uptick=0.9, radius=200),
        'K2': dict(merge=10, top_k=4, min_dur=2, uptick=0.9, radius=100),
        'K4': dict(merge=10, top_k=4, min_dur=2, uptick=0.75, radius=100),
    }
    print('\n=== kombinasi + validasi split subjek ===')
    subj_parity = {s: i % 2 for i, s in enumerate(subjects)}
    folds = {
        'A->B': ([v for v in videos if subj_parity[Path(v).parent.name] == 0],
                 [v for v in videos if subj_parity[Path(v).parent.name] == 1]),
        'B->A': ([v for v in videos if subj_parity[Path(v).parent.name] == 1],
                 [v for v in videos if subj_parity[Path(v).parent.name] == 0]),
    }
    for label, p in combos.items():
        r = evaluate(videos, signals, gt_by_video, p)
        print(f"{label} full: F1 {r['f1']:.4f} ketat {r['f1_strict']:.4f} dur {r['dur']}",
              flush=True)
        for fname, (train, test) in folds.items():
            rb_tr = evaluate(train, signals, gt_by_video, BASE)
            rb_te = evaluate(test, signals, gt_by_video, BASE)
            rk_tr = evaluate(train, signals, gt_by_video, p)
            rk_te = evaluate(test, signals, gt_by_video, p)
            print(f"  {fname}: BASE train {rb_tr['f1']:.4f} test {rb_te['f1']:.4f} | "
                  f"{label} train {rk_tr['f1']:.4f} test {rk_te['f1']:.4f}", flush=True)

    lines = ['# Sweep internals detektor — CAS(ME)^2', '',
             f'BASE = {BASE}. F1 toleransi 0 + F1 ketat (IoU>=0,5).', '',
             '| variasi | P | R | F1 | F1 ketat | det/video | durasi median |',
             '|---|---|---|---|---|---|---|']
    for name, _p, r in rows:
        lines.append(f"| {name} | {r['precision']:.4f} | {r['recall']:.4f} | "
                     f"**{r['f1']:.4f}** | {r['f1_strict']:.4f} | {r['det']:.1f} | {r['dur']} |")
    (args.out / 'README.md').write_text('\n'.join(lines) + '\n')
    print(f'\nhasil -> {args.out / "README.md"}')


if __name__ == '__main__':
    main()

#!/usr/bin/env python
"""Sweep agregasi sinyal x cutoff_ratio untuk spotting POC-ABS (CAS(ME)^2).

Plan 2026-10-13 isu 02. Resep deteksi DIPAKUIN ke konfigurasi terbaik hasil
audit 2026-10-09 (report/findings/audit-spotting-casme2.md):
  global_mean -> savgol 3% adaptif -> find_peaks(height=mean+std,
  prominence rel 0,04) -> ranking prominence -> top_k=5.
Yang di-sweep HANYA:
  agregasi : mean_m (sekarang) / max_m / motion_count / sinyal tambahan dari
             cache topk (top25_m, weighted_m) bila cache-nya sudah dibangun
  cutoff   : 0,3 (sekarang) / 0,5 (menang di F1 ketat pada audit sebelumnya)

Validasi split subjek 2-fold (pola audit_window_sweep_casme2.py): konfigurasi
dipilih di paruh A, diukur di paruh B, dan sebaliknya. Ini menutup jebakan
"memilih parameter di data uji".

Cara pakai:
    .venv/bin/python scripts/audit_mag_agg_casme2.py
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
TOPK_DIR = ROOT / 'output/training/casme2_topk_signals'
CUTOFFS = (0.3, 0.5)
TOP_K = 5


def load_candidate_signals(video: Path) -> dict[str, list[float]]:
    """{kandidat: sinyal global (mean antar ROI)} dari cache yang tersedia."""
    out: dict[str, list[float]] = {}
    rich_path = TOPK_DIR / f'{video.parent.name}_{video.stem}.npz'
    # cache kaya (86 video): roi__mean_m / roi__max_m / roi__motion_count / ...
    cache = bench.load_cached_signals(RICH_DIR / f'{video.parent.name}_{video.stem}.npz') or {}
    by_cand: dict[str, list[list[float]]] = {}
    for key, sig in cache.items():
        if '__' not in key:
            continue
        _roi, cand = key.split('__', 1)
        by_cand.setdefault(cand, []).append(sig)
    if rich_path.exists():
        cache2 = bench.load_cached_signals(rich_path) or {}
        for key, sig in cache2.items():
            if '__' not in key:
                continue
            _roi, cand = key.split('__', 1)
            by_cand.setdefault(cand, []).append(sig)
    for cand, rois in by_cand.items():
        if not rois or any(len(s) == 0 for s in rois):
            continue
        n = min(len(s) for s in rois)
        out[cand] = [float(np.mean([s[i] for s in rois])) for i in range(n)]
    return out


def detect_with_cutoff(signal: list[float], cutoff_ratio: float) -> list[dict]:
    """Resep deteksi baru, cutoff_ratio eksplisit (DetectParams tidak membawanya)."""
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
    """Pooled-micro P/R/F1 (toleransi 0) + F1 ketat (IoU>=0,5) + durasi median."""
    tp = fp = fn = tp_strict = 0
    n_det = durations = 0
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
        strict = sum(1 for d, g in pairs if iou(d, g) >= 0.5)
        tp_strict += strict
        dur_list += [d['offset'] - d['onset'] for d in det]
    sc = bench.scores(tp, fp, fn)
    sc_strict = bench.scores(tp_strict, n_det - tp_strict, (tp + fn) - tp_strict)
    durations = int(np.median(dur_list)) if dur_list else 0
    return {**sc, 'f1_strict': sc_strict['f1'], 'det': n_det, 'dur_med': durations}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, default=ROOT / 'output/training/audit_mag_agg_casme2')
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    gt_df = bench.load_ground_truth(bench.DEFAULT_GT, bench.DEFAULT_VIDEOS)
    gt_by_video: dict[str, list[dict]] = {}
    for _, r in gt_df.iterrows():
        gt_by_video.setdefault(r['video'], []).append(r.to_dict())
    videos = sorted(gt_by_video)
    subjects = sorted({Path(v).parent.name for v in videos})
    print(f'{len(videos)} video, {len(subjects)} subjek, {len(gt_df)} GT', flush=True)

    cand_sigs = {v: load_candidate_signals(Path(v)) for v in videos}
    cands = sorted({c for sigs in cand_sigs.values() for c in sigs})
    # Hanya kandidat yang tersedia di SEMUA video (apple-to-apple)
    cands = [c for c in cands if all(c in cand_sigs[v] for v in videos)]
    print(f'kandidat sinyal: {cands}', flush=True)

    rows = []
    for cand in cands:
        for cutoff in CUTOFFS:
            r = evaluate_subset(videos, cand_sigs, gt_by_video, cand, cutoff)
            rows.append({'cand': cand, 'cutoff': cutoff, **r})
            print(f"  {cand:14s} cutoff={cutoff} | P {r['precision']:.4f} R {r['recall']:.4f} "
                  f"F1 {r['f1']:.4f} | F1ketat {r['f1_strict']:.4f} | "
                  f"det/video {r['det'] / len(videos):.1f} dur {r['dur_med']}", flush=True)

    # ---- validasi split subjek 2-fold ----
    subj_parity = {s: i % 2 for i, s in enumerate(subjects)}
    folds = {
        'A->B': ([v for v in videos if subj_parity[Path(v).parent.name] == 0],
                 [v for v in videos if subj_parity[Path(v).parent.name] == 1]),
        'B->A': ([v for v in videos if subj_parity[Path(v).parent.name] == 1],
                 [v for v in videos if subj_parity[Path(v).parent.name] == 0]),
    }
    print('\n=== validasi split subjek (pilih di train, ukur di test) ===')
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
                         'test_f1_strict': r_te['f1_strict'],
                         'test_p': r_te['precision'], 'test_r': r_te['recall']})
        print(f"  {fname}: terpilih {pick[0]}/cutoff {pick[1]} | "
              f"train F1 {r_tr['f1']:.4f} | test F1 {r_te['f1']:.4f} "
              f"(ketat {r_te['f1_strict']:.4f})", flush=True)

    lines = ['# Sweep agregasi x cutoff_ratio — CAS(ME)^2', '',
             f'{len(videos)} video, {len(gt_df)} GT. Resep deteksi: 3% adaptif, '
             f'prominence ranking, height=mean+std, top_k={TOP_K}, global_mean.', '',
             '| agregasi | cutoff | P | R | F1 | F1 ketat (IoU>=0,5) | det/video | durasi median |',
             '|---|---|---|---|---|---|---|---|']
    for r in rows:
        lines.append(f"| {r['cand']} | {r['cutoff']} | {r['precision']:.4f} | {r['recall']:.4f} | "
                     f"**{r['f1']:.4f}** | {r['f1_strict']:.4f} | {r['det'] / len(videos):.1f} | "
                     f"{r['dur_med']} |")
    lines += ['', '## Validasi split subjek 2-fold', '',
              '| fold | terpilih | train F1 | test F1 | test F1 ketat | test P | test R |',
              '|---|---|---|---|---|---|---|']
    for r in val_rows:
        lines.append(f"| {r['fold']} | {r['cand']}/cutoff {r['cutoff']} | {r['train_f1']:.4f} | "
                     f"**{r['test_f1']:.4f}** | {r['test_f1_strict']:.4f} | "
                     f"{r['test_p']:.4f} | {r['test_r']:.4f} |")
    (args.out / 'README.md').write_text('\n'.join(lines) + '\n')
    print(f'\nhasil -> {args.out / "README.md"}')


if __name__ == '__main__':
    main()

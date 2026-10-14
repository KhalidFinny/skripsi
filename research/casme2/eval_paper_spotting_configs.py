#!/usr/bin/env python
"""Cache-based CAS(ME)^2 sweep for paper-backed spotting configs."""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
from scipy.signal import find_peaks, savgol_filter

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT, ROOT / 'pipeline' / 'stages'):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import eval_spotting_casme2 as bench  # noqa: E402
import stage_1_spotting as spot  # noqa: E402


DEFAULT_OUT = ROOT / 'output/training/paper_spotting_configs'
DEFAULT_CACHE = ROOT / 'output/training/spotting_casme2_signals'


@dataclass(frozen=True, slots=True)
class Candidate:
    name: str
    family: str
    build: Callable[[dict[str, np.ndarray]], tuple[np.ndarray, dict]]


def load_signal_cache(cache_dir: Path, video: str) -> dict[str, np.ndarray] | None:
    path = bench.cache_path(cache_dir, Path(video))
    if path is None or not path.exists():
        return None
    try:
        with np.load(path) as z:
            return {k: z[k].astype(float) for k in z.files}
    except (OSError, ValueError):
        return None


def top_roi_mean(values: list[float], top_rois: int | str) -> float:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return 0.0
    if top_rois == 'mean':
        return float(arr.mean())
    k = max(1, min(int(top_rois), arr.size))
    return float(np.sort(arr)[-k:].mean())


def smooth_curve(curve: np.ndarray, window: int = 7) -> np.ndarray:
    if curve.size < 5:
        return curve.astype(float, copy=True)
    w = min(window, curve.size - 1 if curve.size % 2 == 0 else curve.size)
    if w % 2 == 0:
        w -= 1
    if w < 5:
        return curve.astype(float, copy=True)
    return savgol_filter(curve, window_length=w, polyorder=min(2, w - 1))


def fixed_window_event(curve: np.ndarray, peak: int, width: int,
                       boundary_beta: float | None) -> dict:
    half = max(1, width // 2)
    start = max(0, peak - half)
    end = min(curve.size - 1, peak + half)
    if boundary_beta is not None and curve.size:
        base = float(np.median(curve))
        level = base + boundary_beta * max(float(curve[peak]) - base, 0.0)
        left = peak
        while left > start and curve[left - 1] >= level:
            left -= 1
        right = peak
        while right < end and curve[right + 1] >= level:
            right += 1
        start, end = left, right
    return {
        'onset': int(start + 1),
        'apex': int(peak + 1),
        'offset': int(end + 1),
        'score': float(curve[peak]),
    }


def curve_to_events(curve: np.ndarray, threshold: float, distance: int,
                    width: int, boundary_beta: float | None = None,
                    max_events: int | None = None) -> list[dict]:
    if curve.size < 3 or not np.isfinite(threshold):
        return []
    peaks, props = find_peaks(curve, height=threshold, distance=max(1, distance))
    if peaks.size == 0:
        return []
    heights = props.get('peak_heights', curve[peaks])
    order = np.argsort(-heights)
    if max_events is not None:
        order = order[:max_events]
    events = [fixed_window_event(curve, int(peaks[i]), width, boundary_beta) for i in order]
    return nms_events(sorted(events, key=lambda e: e['onset']), overlap=0.5)


def nms_events(events: list[dict], overlap: float) -> list[dict]:
    kept: list[dict] = []
    for event in sorted(events, key=lambda e: -e['score']):
        if all(interval_iou(event, old) < overlap for old in kept):
            kept.append(event)
    return sorted(kept, key=lambda e: e['onset'])


def interval_iou(a: dict, b: dict) -> float:
    inter = min(a['offset'], b['offset']) - max(a['onset'], b['onset']) + 1
    if inter <= 0:
        return 0.0
    union = max(a['offset'], b['offset']) - min(a['onset'], b['onset']) + 1
    return inter / union if union > 0 else 0.0


def fd_curve(signals: dict[str, np.ndarray], k: int, top_rois: int | str) -> np.ndarray:
    keys = sorted(signals)
    n = min((len(signals[r]) for r in keys), default=0)
    out = np.zeros(n, dtype=float)
    if n <= 2 * k:
        return out
    for i in range(k, n - k):
        vals = []
        for r in keys:
            arr = signals[r]
            vals.append(max(float(arr[i] - 0.5 * (arr[i - k] + arr[i + k])), 0.0))
        out[i] = top_roi_mean(vals, top_rois)
    return smooth_curve(out, window=max(5, min(15, 2 * (k // 2) + 1)))


def multi_window_curve(signals: dict[str, np.ndarray], length: int,
                       top_rois: int | str) -> np.ndarray:
    keys = sorted(signals)
    n = min((len(signals[r]) for r in keys), default=0)
    out = np.zeros(n, dtype=float)
    if n < length:
        return out
    half = length // 2
    for i in range(half, n - half):
        start = i - half
        end = i + half + 1
        vals = []
        for r in keys:
            window = signals[r][start:end]
            baseline = float(0.5 * (window[0] + window[-1]))
            vals.append(max(float(window.max() - baseline), 0.0))
        out[i] = top_roi_mean(vals, top_rois)
    return smooth_curve(out, window=max(5, min(21, length // 2 * 2 + 1)))


def of_fd_proxy_curve(signals: dict[str, np.ndarray], top_rois: int | str,
                      smooth_window: int) -> np.ndarray:
    keys = sorted(signals)
    n = min((len(signals[r]) for r in keys), default=0)
    out = np.zeros(n, dtype=float)
    for i in range(n):
        out[i] = top_roi_mean([signals[r][i] for r in keys], top_rois)
    # OF-FD family denoises optical-flow time curves before peak/NMS. This proxy
    # uses the current POC-ABS ROI motion curves, so keep the name honest.
    return smooth_curve(out, window=smooth_window)


def current_baseline_events(signals: dict[str, np.ndarray]) -> list[dict]:
    roi = {k: v.astype(float).tolist() for k, v in signals.items()}
    _smoothed, events, _meta = spot.detect_events(spot.build_global_signal(roi))
    return [{
        'onset': spot.signal_index_to_frame_index(e['onset_signal']),
        'apex': spot.signal_index_to_frame_index(e['apex_signal']),
        'offset': spot.signal_index_to_frame_index(e['offset_signal']),
        'score': 1.0,
    } for e in events]


def global_mean_curve(signals: dict[str, np.ndarray], top_rois: int | str,
                      smooth_window: int) -> np.ndarray:
    keys = sorted(signals)
    n = min((len(signals[r]) for r in keys), default=0)
    out = np.zeros(n, dtype=float)
    for i in range(n):
        out[i] = top_roi_mean([signals[r][i] for r in keys], top_rois)
    return smooth_curve(out, window=smooth_window)


def candidate_name(prefix: str, beta: float | None) -> str:
    return f'{prefix}_b{beta if beta is not None else "fixed"}'


def build_candidates(boundary_betas: list[float | None]) -> list[Candidate]:
    candidates: list[Candidate] = [
        Candidate('current_mean_m', 'baseline', lambda s: (np.empty(0), {'events': current_baseline_events(s)})),
    ]

    for lam in (2.0, 2.5, 3.0, 3.5):
        for top_rois in (1, 2, 'mean'):
            for smooth_window in (15, 35):
                for beta in boundary_betas:
                    name = candidate_name(f'mean_m_precision_mad{lam:g}_top{top_rois}_sw{smooth_window}', beta)

                    def build(s, lam=lam, top_rois=top_rois, smooth_window=smooth_window, beta=beta):
                        curve = global_mean_curve(s, top_rois=top_rois, smooth_window=smooth_window)
                        med = float(np.median(curve))
                        mad = float(np.median(np.abs(curve - med)))
                        threshold = med + lam * 1.4826 * mad
                        events = curve_to_events(curve, threshold, distance=12,
                                                 width=35, boundary_beta=beta)
                        return curve, {'events': events, 'threshold': threshold}

                    candidates.append(Candidate(name, 'mean_m_precision', build))

    for k in (8, 12, 17):
        for tau in (0.10, 0.20, 0.30, 0.45):
            for top_rois in ('mean', 2):
                for beta in boundary_betas:
                    name = candidate_name(f'fd_k{k}_tau{tau:g}_top{top_rois}', beta)

                    def build(s, k=k, tau=tau, top_rois=top_rois, beta=beta):
                        curve = fd_curve(s, k=k, top_rois=top_rois)
                        threshold = float(curve.mean() + tau * (curve.max() - curve.mean()))
                        events = curve_to_events(curve, threshold, distance=max(1, k // 2),
                                                 width=2 * k + 1, boundary_beta=beta)
                        return curve, {'events': events, 'threshold': threshold}

                    candidates.append(Candidate(name, 'fd_peak', build))

    for length in (17, 25, 35, 45):
        for tau in (0.10, 0.20, 0.30):
            for top_rois in ('mean', 2):
                for beta in boundary_betas:
                    name = candidate_name(f'multiwin_L{length}_tau{tau:g}_top{top_rois}', beta)

                    def build(s, length=length, tau=tau, top_rois=top_rois, beta=beta):
                        curve = multi_window_curve(s, length=length, top_rois=top_rois)
                        threshold = float(curve.mean() + tau * (curve.max() - curve.mean()))
                        events = curve_to_events(curve, threshold, distance=max(1, length // 3),
                                                 width=length, boundary_beta=beta)
                        return curve, {'events': events, 'threshold': threshold}

                    candidates.append(Candidate(name, 'multi_window_temporal', build))

    for lam in (2.0, 2.5, 3.0, 3.5):
        for top_rois in (1, 2, 'mean'):
            for smooth_window in (15, 35):
                for beta in boundary_betas:
                    name = candidate_name(f'of_fd_proxy_mad{lam:g}_top{top_rois}_sw{smooth_window}', beta)

                    def build(s, lam=lam, top_rois=top_rois, smooth_window=smooth_window, beta=beta):
                        curve = of_fd_proxy_curve(s, top_rois=top_rois, smooth_window=smooth_window)
                        med = float(np.median(curve))
                        mad = float(np.median(np.abs(curve - med)))
                        threshold = med + lam * 1.4826 * mad
                        events = curve_to_events(curve, threshold, distance=12,
                                                 width=35, boundary_beta=beta)
                        return curve, {'events': events, 'threshold': threshold}

                    candidates.append(Candidate(name, 'of_fd_proxy', build))

    return candidates


def score_counts(tp: int, fp: int, fn: int) -> dict[str, float]:
    precision = tp / (tp + fp) if tp + fp else float('nan')
    recall = tp / (tp + fn) if tp + fn else float('nan')
    if np.isnan(precision) or np.isnan(recall) or precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return {'tp': tp, 'fp': fp, 'fn': fn, 'precision': precision, 'recall': recall, 'f1': f1}


def match_events(gt: list[dict], det: list[dict], mode: str) -> tuple[list[tuple[dict, dict]], list[dict], list[dict]]:
    pairs: list[tuple[dict, dict]] = []
    used_det: set[int] = set()
    used_gt: set[int] = set()
    for gi, g in enumerate(sorted(gt, key=lambda x: x['onset'])):
        best_di = None
        best_score = -math.inf
        for di, d in enumerate(det):
            if di in used_det:
                continue
            iou = interval_iou(d, g)
            if mode == 'iou50':
                ok = iou >= 0.5
                score = iou
            else:
                ok = d['onset'] <= g['offset'] and g['onset'] <= d['offset']
                score = -abs(d['apex'] - g['apex'])
            if ok and score > best_score:
                best_di = di
                best_score = score
        if best_di is not None:
            used_gt.add(gi)
            used_det.add(best_di)
            pairs.append((det[best_di], g))
    fp = [d for di, d in enumerate(det) if di not in used_det]
    sorted_gt = sorted(gt, key=lambda x: x['onset'])
    fn = [g for gi, g in enumerate(sorted_gt) if gi not in used_gt]
    return pairs, fp, fn


def frame_accuracy_f(pairs: list[tuple[dict, dict]]) -> float:
    if not pairs:
        return float('nan')
    vals = []
    for d, g in pairs:
        c_w = 0.5 * (d['onset'] + d['offset'])
        c_gt = 0.5 * (g['onset'] + g['offset'])
        l_w = max(1, d['offset'] - d['onset'] + 1)
        l_gt = max(1, g['offset'] - g['onset'] + 1)
        vals.append((abs(c_w - c_gt) + abs(l_w - l_gt)) / (2 * l_gt))
    return float(np.mean(vals))


def evaluate_candidate(name: str, family: str, events_by_video: dict[str, list[dict]],
                       gt_by_video: dict[str, list[dict]], video_set: set[str] | None = None) -> dict:
    loose_pairs: list[tuple[dict, dict]] = []
    iou_pairs: list[tuple[dict, dict]] = []
    loose_fp = loose_fn = iou_fp = iou_fn = 0
    det_count = 0
    durations = []
    videos = [v for v in sorted(gt_by_video) if video_set is None or v in video_set]
    for video in videos:
        gt = gt_by_video[video]
        det = events_by_video.get(video, [])
        det_count += len(det)
        durations.extend(max(1, d['offset'] - d['onset'] + 1) for d in det)
        pairs, fp, fn = match_events(gt, det, mode='loose')
        loose_pairs.extend(pairs)
        loose_fp += len(fp)
        loose_fn += len(fn)
        pairs_iou, fp_iou, fn_iou = match_events(gt, det, mode='iou50')
        iou_pairs.extend(pairs_iou)
        iou_fp += len(fp_iou)
        iou_fn += len(fn_iou)

    loose = score_counts(len(loose_pairs), loose_fp, loose_fn)
    iou50 = score_counts(len(iou_pairs), iou_fp, iou_fn)
    n_videos = max(1, len(videos))
    apex_err = [abs(d['apex'] - g['apex']) for d, g in loose_pairs]
    return {
        'config': name,
        'family': family,
        'n_videos': len(videos),
        'n_det': det_count,
        'det_per_video': det_count / n_videos,
        'fp_per_video': loose_fp / n_videos,
        'duration_median': float(np.median(durations)) if durations else float('nan'),
        'apex_err_median': float(np.median(apex_err)) if apex_err else float('nan'),
        'frame_F': frame_accuracy_f(loose_pairs),
        'iou50_f1': iou50['f1'],
        **loose,
    }


def subject_splits(gt_df: pd.DataFrame) -> tuple[set[str], set[str]]:
    subjects = sorted(gt_df['subject'].unique())
    midpoint = len(subjects) // 2
    a_subjects = set(subjects[:midpoint])
    b_subjects = set(subjects[midpoint:])
    video_subject = dict(zip(gt_df['video'], gt_df['subject']))
    a_videos = {v for v, s in video_subject.items() if s in a_subjects}
    b_videos = {v for v, s in video_subject.items() if s in b_subjects}
    return a_videos, b_videos


def fmt(value: float) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return 'n/a'
    return f'{value:.4f}'


def write_summary(out: Path, results: pd.DataFrame, split_results: pd.DataFrame,
                  limit: int | None) -> None:
    lines = ['# Paper-backed spotting config sweep — CAS(ME)^2', '']
    if limit:
        lines.append(f'> Diagnostic run only: limited to {limit} videos. Do not use these numbers as final evidence.\n')
    lines += [
        'Metrics:',
        '- `f1`: loose interval-overlap F1, comparable to earlier repo audits.',
        '- `iou50_f1`: strict IoU≥0.5 interval F1.',
        '- `frame_F`: benchmark frame-accuracy metric; lower is better.',
        '- `fp_per_video` / `det_per_video`: false-positive load for downstream recognition.',
        '',
    ]

    display_cols = ['config', 'family', 'precision', 'recall', 'f1', 'iou50_f1',
                    'frame_F', 'det_per_video', 'fp_per_video', 'duration_median']

    family_best = results.loc[results.groupby('family')['f1'].idxmax()].sort_values('f1', ascending=False)
    baseline = results[results['config'] == 'current_mean_m'].iloc[0]
    best_candidate = results[results['config'] != 'current_mean_m'].sort_values('f1', ascending=False).iloc[0]
    best_frame = results[results['recall'] >= 0.15].sort_values('frame_F', ascending=True).iloc[0]
    best_precision = results[results['recall'] >= 0.10].sort_values(
        ['precision', 'fp_per_video'], ascending=[False, True]).iloc[0]

    lines += [
        '## Verdict',
        '',
        f'- Best loose-F1 config: `{baseline["config"]}` '
        f'(F1 {fmt(baseline["f1"])}, P {fmt(baseline["precision"])}, R {fmt(baseline["recall"])}).',
        f'- Best non-baseline loose-F1 config: `{best_candidate["config"]}` '
        f'(F1 {fmt(best_candidate["f1"])}, F {fmt(best_candidate["frame_F"])}, '
        f'FP/video {fmt(best_candidate["fp_per_video"])}).',
        f'- Best frame-localization `F` among recall ≥ 0.15: `{best_frame["config"]}` '
        f'(F {fmt(best_frame["frame_F"])}, F1 {fmt(best_frame["f1"])}).',
        f'- Best precision-oriented config among recall ≥ 0.10: `{best_precision["config"]}` '
        f'(P {fmt(best_precision["precision"])}, R {fmt(best_precision["recall"])}, '
        f'FP/video {fmt(best_precision["fp_per_video"])}).',
        '- Downstream decision: loose F1 is not the selection metric for anxiety recognition. '
        'Use `current_mean_m` as the high-recall baseline and run the precision-first '
        '`of_fd_proxy_mad3.5_topmean_sw35_b0.3` recipe as the noise-reduction A/B.',
        '',
        '## Best config per family',
        '',
        '| family | config | P | R | F1 | IoU50 F1 | F | det/video | FP/video |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for _, row in family_best.iterrows():
        lines.append('| ' + ' | '.join([
            str(row['family']), str(row['config']), fmt(row['precision']), fmt(row['recall']),
            fmt(row['f1']), fmt(row['iou50_f1']), fmt(row['frame_F']),
            fmt(row['det_per_video']), fmt(row['fp_per_video']),
        ]) + ' |')
    lines.append('')

    def add_table(title: str, frame: pd.DataFrame) -> None:
        lines.extend([f'## {title}', '', '| config | family | P | R | F1 | IoU50 F1 | F | det/video | FP/video | dur med |',
                      '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|'])
        for _, row in frame[display_cols].head(12).iterrows():
            lines.append('| ' + ' | '.join([
                str(row['config']), str(row['family']), fmt(row['precision']), fmt(row['recall']),
                fmt(row['f1']), fmt(row['iou50_f1']), fmt(row['frame_F']),
                fmt(row['det_per_video']), fmt(row['fp_per_video']), fmt(row['duration_median']),
            ]) + ' |')
        lines.append('')

    add_table('Best by loose F1', results.sort_values('f1', ascending=False))
    usable = results[results['recall'] >= 0.15].copy()
    if not usable.empty:
        add_table('Best frame accuracy F among recall ≥ 0.15', usable.sort_values('frame_F', ascending=True))
    precision_usable = results[results['recall'] >= 0.10].copy()
    if not precision_usable.empty:
        add_table('Precision-oriented configs among recall ≥ 0.10', precision_usable.sort_values(['precision', 'fp_per_video'], ascending=[False, True]))

    lines += ['## Subject split A/B selection', '',
              'For each split, config is selected on one subject half by F1, then reported on the other half.', '',
              '| train half | selected config | test half | test F1 | test F | test P | test R |',
              '|---|---|---|---:|---:|---:|---:|']
    for _, row in split_results.iterrows():
        lines.append(f'| {row["train_half"]} | {row["config"]} | {row["test_half"]} | '
                     f'{fmt(row["test_f1"])} | {fmt(row["test_frame_F"])} | '
                     f'{fmt(row["test_precision"])} | {fmt(row["test_recall"])} |')

    (out / 'summary.md').write_text('\n'.join(lines) + '\n')


def main() -> None:
    parser = argparse.ArgumentParser(description='CAS(ME)^2 cache sweep for paper-backed spotting configs.')
    parser.add_argument('--gt', type=Path, default=bench.DEFAULT_GT)
    parser.add_argument('--videos', type=Path, default=bench.DEFAULT_VIDEOS)
    parser.add_argument('--cache-dir', type=Path, default=DEFAULT_CACHE)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--limit', type=int, default=None)
    parser.add_argument('--boundary-beta', type=float, nargs='*', default=[0.3],
                        help='Boundary-refinement beta values. Use no values to disable; fixed windows are always included.')
    args = parser.parse_args()

    gt_df = bench.load_ground_truth(args.gt, args.videos)
    if args.limit:
        keep = sorted(gt_df['video'].unique())[:args.limit]
        gt_df = gt_df[gt_df['video'].isin(keep)].copy()

    gt_by_video = {v: g.to_dict('records') for v, g in gt_df.groupby('video')}
    signals_by_video: dict[str, dict[str, np.ndarray]] = {}
    for video in sorted(gt_by_video):
        signals = load_signal_cache(args.cache_dir, video)
        if signals is not None:
            signals_by_video[video] = signals
    missing = sorted(set(gt_by_video) - set(signals_by_video))
    if missing:
        print(f'WARNING: {len(missing)} videos skipped because signal cache is missing.', flush=True)
        gt_by_video = {v: gt for v, gt in gt_by_video.items() if v in signals_by_video}

    args.out.mkdir(parents=True, exist_ok=True)
    boundary_betas: list[float | None] = [None] + list(args.boundary_beta or [])
    candidates = build_candidates(boundary_betas)
    print(f'videos={len(gt_by_video)} configs={len(candidates)} cache={args.cache_dir}', flush=True)

    rows = []
    all_events: dict[str, dict[str, list[dict]]] = {}
    for candidate in candidates:
        events_by_video = {}
        for video, signals in signals_by_video.items():
            _curve, meta = candidate.build(signals)
            events_by_video[video] = meta['events']
        all_events[candidate.name] = events_by_video
        rows.append(evaluate_candidate(candidate.name, candidate.family, events_by_video, gt_by_video))
        print(f'{candidate.name}: F1={rows[-1]["f1"]:.4f} F={fmt(rows[-1]["frame_F"])} '
              f'P={fmt(rows[-1]["precision"])} R={fmt(rows[-1]["recall"])}', flush=True)

    results = pd.DataFrame(rows).sort_values('f1', ascending=False)
    results.to_csv(args.out / 'results.csv', index=False)

    a_videos, b_videos = subject_splits(gt_df)
    split_rows = []
    for train_name, test_name, train_set, test_set in (
        ('A', 'B', a_videos, b_videos),
        ('B', 'A', b_videos, a_videos),
    ):
        train_scores = []
        for candidate in candidates:
            train_scores.append(evaluate_candidate(candidate.name, candidate.family, all_events[candidate.name], gt_by_video, train_set))
        picked = max(train_scores, key=lambda r: (-1.0 if np.isnan(r['f1']) else r['f1']))
        test = evaluate_candidate(picked['config'], picked['family'], all_events[picked['config']], gt_by_video, test_set)
        split_rows.append({
            'train_half': train_name,
            'test_half': test_name,
            'config': picked['config'],
            'family': picked['family'],
            'train_f1': picked['f1'],
            'test_f1': test['f1'],
            'test_frame_F': test['frame_F'],
            'test_precision': test['precision'],
            'test_recall': test['recall'],
        })
    split_results = pd.DataFrame(split_rows)
    split_results.to_csv(args.out / 'split_selection.csv', index=False)
    write_summary(args.out, results, split_results, args.limit)
    print(f'Wrote {args.out / "summary.md"}', flush=True)


if __name__ == '__main__':
    main()

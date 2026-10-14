# 03 — Li/Moilanen training-free feature-difference peak spotter

**Severity:** high

**Status:** done — `fd_peak` configs are in the CAS(ME)² sweep; best FD (`fd_k17_tau0.45_topmean_bfixed`) reached F1 0.1900, below `current_mean_m` F1 0.3192.

## Current Problem

We need a training-free paper baseline to isolate spotting from classifier
overfitting. Current detector is peak picking on absolute POC-ABS magnitude, not
feature difference contrast. This is useful diagnostically, but it is not the
only or strongest comparator; OF-FD is the main modern training-free target.

## Target

Implement FD contrast on cached ROI signals:

- for center frame `i`, compare center against average of head/tail frames at
  ±k or within window length `N`
- per ROI/block-like signal: `diff = center - 0.5*(head + tail)`, clip negative
  to zero
- aggregate top ROI/signals or mean global
- threshold: `T = Cmean + tau*(Cmax-Cmean)`
- peak detection with minimum distance `k/2`
- sweep `k/window` and `tau`
- produce both recall-oriented and precision-oriented configs; downstream anxiety
  may prefer fewer cleaner clips over high-recall noisy clips

Source mapping:
- Li et al. / “Towards Reading Hidden Emotions”: FD contrast + peak detection,
  chi-square feature distance, threshold formula, min peak distance `k/2`.
- Benchmark implementation: LBP-χ² with 6×6 spatial blocks and HF/CF/TF.

## Required Design

- Name output configs as `fd_k{}` / `fd_tau{}`.
- Use subject split to pick tau/k.
- Note eye-blinks can cause FP; do not remove eye ROIs unless it is a separate
  labelled config.
- Report frame-based `F` and false positives/video alongside F1.

## Tests

Use common evaluator limit run, then full cache sweep if fast enough.

## Done Criteria

- [x] FD configs appear in `results.csv`.
- [x] Summary states whether FD beats current `mean_m` on CAS(ME)².

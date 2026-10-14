# 04 — Multi-window temporal feature

**Severity:** high

**Status:** done — `multi_window_temporal` configs are in the CAS(ME)² sweep; L=35 is included, but the best multi-window result came from L=45 and still lost to `current_mean_m`.

## Current Problem

The prior plan called this `SpotFormer-inspired SW-MRO`, but that is too loose.
SpotFormer's benefit comes from CSW-MRO features consumed by a trained temporal
attention/Transformer stack. Borrowing only window size 17 into a handcrafted
peak detector is not SpotFormer.

## Target

Implement a clearly named `multi_window_temporal` candidate:

- primary literature-grounded window: **L=35** from the micro-expression spotting
  benchmark (mean ME sample size ≈34, fixed window set to 35)
- sweep windows: 17, 25, 35, 45, optionally 9/11/15 as diagnostics
- for each center/window, build a temporal contrast curve from cached ROI signals:
  center/local peak vs head-tail/local baseline, with top-ROI aggregation
- convert peaks to intervals with shared evaluator and NMS
- report frame-based accuracy `F`, not just F1, because interval cleanliness matters
  for downstream recognition features

## Required Design

- Do not call this SpotFormer unless the trained architecture is used.
- Window 17 can be included because SpotFormer found it best inside its model, but
  the benchmark L=35 is the defensible training-free anchor.
- Keep output config names explicit: `multiwin_L35_tau...`, etc.

## Tests

Use common evaluator limit run, then full cache sweep if fast enough.

## Done Criteria

- [x] `multi_window_temporal` configs are compared with baseline.
- [x] L=35 is included and highlighted.
- [x] Summary states whether this improves F and downstream candidate quality.

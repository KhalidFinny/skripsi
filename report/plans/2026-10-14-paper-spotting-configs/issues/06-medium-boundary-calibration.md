# 06 — Boundary calibration post-refiner

**Severity:** medium

**Status:** done in the evaluator as optional `boundary_beta=0.3` plus fixed-window variants; no boundary-calibrated non-baseline config won automatic promotion.

## Current Problem

Some configs may find peaks near the right frames but produce bad onset/offset
boundaries. The 2024 boundary-calibration paper explicitly targets this, but exact
public thresholds/code were not found.

## Target

Add an optional post-refiner after candidate peak detection:

- from apex, search left/right to local minima or to `baseline + beta*(peak-baseline)`
- sweep `beta = 0.1, 0.2, 0.3, 0.5`
- cap durations at micro/macro plausible limits
- run NMS at IoU 0.3/0.5

## Required Design

- Label as paper-inspired boundary calibration.
- Report both loose overlap F1 and IoU≥0.5 F1.

## Tests

Evaluator summary before/after boundary calibration.

## Done Criteria

- [x] If used, boundaries improve IoU≥0.5 without destroying loose F1.

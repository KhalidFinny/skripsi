# 01 — Literature config map

**Severity:** critical

## Current Problem

We have candidate names from papers (`SW-MRO`, temporal state transition,
feature difference peak detection), but not all are equally portable. If we mix
paper results with partial ports, FINAL.pdf becomes weaker, not stronger.

## Target

Create/update `report/findings/spotting-feature-deepdive.md` with a concrete
matrix:

| method | source | exact config | train needed | portable now | expected use |

Minimum entries:
- SpotFormer / CSW-MRO: window 17, ROI optical flow, trained transformer.
- ME-TST: video-level regression + joint spotting/recognition, deep training.
- Li et al. FD: training-free, chi-square/feature difference, threshold formula.
- MDMD MEGC2020: 6×6 blocks, 4 dirs, k=12/39, p=0.01, duration filters.
- Boundary calibration: post-processing idea, no exact public thresholds found.

## Required Design

- Separate **reproduced** from **inspired**.
- Include links/citations and concrete parameters.
- State what can be implemented without new training.

## Tests

No tests. Verification is source-backed citations and exact config values.

## Done Criteria

- [ ] Findings document has the matrix.
- [ ] Non-portable methods are not presented as immediate configs.

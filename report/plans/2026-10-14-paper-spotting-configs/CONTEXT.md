# CONTEXT — Paper-backed spotting config search

## Problem

Supervisor target is >60% downstream anxiety classification, so stopping at a
negative write-up is not acceptable yet. Current automatic spotting variants
already tried in this repo (`mean_m`, `combo`, motion-comp + simple `mdmd`) do
not generalize on the fold-first anxiety protocol. FINAL.pdf also contains older
claims/configs (block 7, 3 ROI, external test accuracy 58%) that need a stronger,
defensible replacement path.

The next smallest correct path is not another blind TabR run. The bottleneck is
upstream spotting: if event clips are noisy, TabR only learns noise. We need a
paper-backed spotting sweep that isolates which detector configurations improve
CAS(ME)² spotting first, then only promote the best automatic spotter into the
fold-first anxiety pipeline.

## Fix

Build a compact, reproducible paper-backed spotter matrix:

1. **Training-free Feature Difference / Peak Detection (Li et al.)** on cached
   POC-ABS ROI signals: LBP-χ²/FD idea adapted as ROI feature-difference,
   threshold `Cmean + tau*(Cmax-Cmean)`, peak distance `k/2`.
2. **OF-FD / fixed-ROI optical-flow feature difference**: use the modern
   training-free optical-flow family (14 ROI / nose-aligned OF features + wave
   peak detection) as the credible comparator, because MDMD MEGC2020 is a weak
   floor rather than an informative target.
3. **Multi-window temporal feature**: no longer presented as a SpotFormer port.
   Use benchmark-grounded fixed windows (especially `L=35`, mean ME duration in
   the benchmark paper) plus a sweep. Window 17 can remain a diagnostic point,
   but not the anchor.
4. Optional **boundary calibration** post-refiner after candidates, clearly
   labelled paper-inspired when exact code is unavailable.
5. Optional **MDMD floor check** only if needed for thesis comparison; do not
   let it drive the implementation order.

Evaluate on CAS(ME)² first, with subject-split selection only. Then wire the
winning spotter as env-gated pipeline option for a full fold-first anxiety run.

## Architecture Now

```diagram
┌─────────────────────────────┐
│ CAS(ME)² annotated videos    │
└──────────────┬──────────────┘
               │ cached ROI signals / optional optical flow
               ▼
┌─────────────────────────────┐
│ paper-backed spotter matrix  │
│ FD peaks / SW-MRO / MDMD     │
└──────────────┬──────────────┘
               │ subject-split selection, no anxiety test tuning
               ▼
┌─────────────────────────────┐
│ best automatic spotter       │
│ env-gated in pipeline v3     │
└──────────────┬──────────────┘
               │ full fold-first run only after CAS(ME)² evidence
               ▼
┌─────────────────────────────┐
│ anxiety LOSO-44 + holdout-12 │
└─────────────────────────────┘
```

## Key Files

### Research / evidence
- `FINAL.pdf` / `.amp/in/final.txt` — current thesis claims to fix or supersede.
- `report/findings/spotting-feature-deepdive.md` — existing literature summary.
- `report/findings/audit-spotting-casme2.md` — current CAS(ME)² baseline and audit.
- `report/findings/magnitude-deepdive.md` — why `mean_m` stayed default so far.

### Spotting code
- `scripts/eval_spotting_casme2.py` — CAS(ME)² evaluator; extend or add a sibling
  evaluator for candidate curves.
- `scripts/process_spotting_pipeline.py` — production spotting; add only the
  winning env-gated option after CAS(ME)² evidence.
- `apex/apex_phase.py`, `apex/apex_smoother.py` — current peak/fase detector.
- `output/training/spotting_casme2_signals/*.npz` — cached POC-ABS ROI signals.

## Important Behavior Changes

- No default production change until a candidate wins CAS(ME)² subject-split
  validation.
- New spotters must be named by source and config, not generic labels.
- Any deep method (SpotFormer, ME-TST) is evidence for feature design unless we
  explicitly import/train the model; do not imply a no-training port reproduces
  paper SOTA.
- The CAS(ME)² evaluator must include frame-based accuracy `F`: lower is better,
  because it measures center and length deviation of true positive intervals and
  is closer to downstream feature cleanliness than loose F1 alone.

## Tests

Per user contract: do not run full tests/e2e unless asked. Allowed validation:
syntax/type/build checks and cache-based CAS(ME)² research scripts if needed.
Full anxiety pipeline remains user-run unless explicitly requested.

## Validation Done

- Read FINAL.pdf text enough to confirm current claims: POC-ABS block 7×7,
  right/left eye-eyebrow + mouth ROI, external accuracy 58%.
- Web/literature checked:
  - SpotFormer / CSW-MRO: window 17 best at 30 fps inside a trained transformer;
    CAS(ME)² overall F1 0.4841, ME F1 0.2817. This is not a drop-in config.
  - ME-TST: video-level regression + joint spotting/recognition; code exists but
    is deep training, not a direct drop-in config.
  - Li et al. feature-difference: training-free FD contrast + peak detection;
    threshold `Cmean + tau*(Cmax-Cmean)`, min peak distance `k/2`, eye blinks are
    a known FP source.
  - OF-FD/MSOF family: modern optical-flow fixed-ROI methods use 14/13 ROIs,
    face/nose alignment, optical-flow time curves, denoising, peak/NMS; this is
    the more credible training-free comparator than MDMD.
  - MDMD MEGC2020 repo: 6×6 blocks, 4 directions, CAS(ME)² k=12 micro / 39 macro,
    `p=0.01`, duration filters, IoU 0.5; reported MEGC2020 performance is too
    weak to be more than a floor check.

## Known Notes

- Devil's advocate: literature does not guarantee >60% honest holdout anxiety.
  SpotFormer improves CAS(ME)² spotting F1 but is supervised and still only ME F1
  0.2817 on CAS(ME)². Use it as evidence that windowed optical flow helps, not as
  a magic no-training switch.
- We can still pursue >60%, but every reported number must separate:
  CAS(ME)² spotting quality, anxiety train-pool LOSO, and anxiety holdout.

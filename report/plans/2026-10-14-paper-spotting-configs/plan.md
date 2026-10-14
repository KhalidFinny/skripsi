# Paper-backed spotting configs — plan

> **Status:** downstream A/B ready, 2026-10-14. The evaluator and all four requested candidate families ran on cached CAS(ME)² signals; `current_mean_m` is the high-recall baseline, and precision-first `of_fd_proxy` is wired for the next fold-first anxiety run.

- **Goal:** find a paper-backed automatic spotting configuration that improves event quality enough to make a subject-level fold-first anxiety result above 60% accuracy plausible, while keeping evaluation defensible for FINAL.pdf replacement.
- **Architecture:** annotated CAS(ME)² → candidate spotter curves → subject-split selection → env-gated pipeline spotter → fold-first anxiety run.
- **Tech Stack:** existing Python scripts, OpenCV/numpy/scipy/pandas, cached POC-ABS ROI signals; no new dependency unless unavoidable.

## Must Not Forget

- Supervisor wants >60%, so do not stop at “negative finding” yet.
- Do not fabricate >60%. If a method does not honestly improve holdout, say so and move to the next planned lever.
- Success target is explicit: downstream anxiety **subject-level accuracy ≥60%** on the fold-first holdout is the supervisor-facing target; balanced accuracy, MCC, AUC, and LOSO-44 stay as guards against majority-class or threshold artifacts.
- Spotting F1 is not the final success metric. For spotting, report F1 plus frame-based accuracy `F`, precision at fixed recall / recall at fixed precision, event duration, and false-positive load.
- Spotting configs are selected on CAS(ME)² or train folds only. Do not tune on anxiety holdout.
- Deep methods (SpotFormer, ME-TST) require training/pretrained models. If we only port their feature idea, label it as a different method; do not borrow their reported numbers.
- MDMD MEGC2020 is too weak to be a main candidate (micro F1 0.0082 / overall 0.0376 under that protocol). Keep it only as a sanity/floor check unless source-backed numbers under a comparable protocol justify otherwise.
- Keep `mean_m` production default until a candidate wins validation.
- Do not run full anxiety pipeline/test/e2e unless Khalid asks. Syntax/build/cache research checks are allowed.
- Update `PROGRESS.md` and `HANDOFF.md` with every completed sweep/result.

## Issue Index

### critical
- [01-critical-literature-config-map](issues/01-critical-literature-config-map.md) — lock exact paper configs and what is realistic to port.
- [02-critical-cache-evaluator](issues/02-critical-cache-evaluator.md) — build one evaluator that compares candidate scalar curves on CAS(ME)² fairly.

### high
- [03-high-fd-peak-spotter](issues/03-high-fd-peak-spotter.md) — implement Li et al. training-free feature-difference + peak detector on cached ROI signals.
- [04-high-multi-window-temporal-feature](issues/04-high-multi-window-temporal-feature.md) — implement a clearly named multi-window temporal feature, grounded in benchmark window length 35 and sweeps, not claimed as SpotFormer.
- [05-high-of-fd-spotter](issues/05-high-of-fd-spotter.md) — implement credible optical-flow feature-difference / fixed-ROI comparison before any MDMD floor check.

### medium
- [06-medium-boundary-calibration](issues/06-medium-boundary-calibration.md) — add paper-inspired boundary refinement/NMS if candidates produce good peaks but poor boundaries.
- [07-medium-promote-winner-pipeline](issues/07-medium-promote-winner-pipeline.md) — wire only the validated winner into `process_spotting_pipeline.py` / `run_pipeline_v3.sh` as env-gated option.
- [08-medium-final-pdf-coverage](issues/08-medium-final-pdf-coverage.md) — write the thesis correction/replacement notes for FINAL.pdf.

### low
- [09-low-mdmd-floor-check](issues/09-low-mdmd-floor-check.md) — optional MDMD floor check only, not a main decision lever.

## Target Architecture

```diagram
┌───────────────┐   cached signals   ┌──────────────────────┐
│ CAS(ME)² GT    ├───────────────────►│ paper config evaluator│
└───────────────┘                    └──────────┬───────────┘
                                                │ subject split winner
                                                ▼
                                      ┌──────────────────────┐
                                      │ env-gated v3 spotter  │
                                      └──────────┬───────────┘
                                                 │ user-run full pipeline
                                                 ▼
                                      ┌──────────────────────┐
                                      │ LOSO-44 + holdout-12 │
                                      └──────────────────────┘
```

## Priority Order

1. 01 — map configs and reject non-portable claims.
2. 02 — common evaluator so all configs use same matching metrics.
3. 03 and 05 — training-free FD plus credible OF-FD comparison.
4. 04 — multi-window temporal feature, using benchmark-grounded windows.
5. 06 — boundary refiner if peaks are good but intervals are bad.
6. 07 — production wiring only after CAS(ME)² winner.
7. 08 — FINAL.pdf coverage.
8. 09 — MDMD only if needed as a floor/sanity check.

## Validation Commands

```bash
# syntax checks after scripts are added/edited
.venv/bin/python -m py_compile scripts/<new_evaluator>.py scripts/process_spotting_pipeline.py
bash -n scripts/run_pipeline_v3.sh

# cache-based CAS(ME)² sweep, no full anxiety run
.venv/bin/python scripts/<new_evaluator>.py --out output/training/<candidate_sweep>
```

## Rollout Plan

- [x] Read FINAL.pdf claims and existing spotting findings.
- [x] Research SpotFormer/SW-MRO, ME-TST, Li FD peak detection, MDMD repo configs.
- [x] Revise plan after critique: OF-FD promoted, MDMD downgraded, frame `F` and downstream accuracy target added.
- [x] Implement cache-based evaluator.
- [x] Run CAS(ME)² candidate sweep.
- [x] Pick downstream A/B configs without anxiety holdout tuning: `current_mean_m` baseline and precision-first `of_fd_proxy_mad3.5_topmean_sw35_b0.3`.
- [x] Wire precision-first OF-FD proxy into pipeline behind env var.
- [x] Prepare exact full-run command for Khalid.
- [ ] Update FINAL.pdf correction notes.

## Done Criteria

- [x] A table exists comparing current POC-ABS baseline vs paper-backed candidates on CAS(ME)², including F1, frame-based `F`, precision-oriented metrics, and event load.
- [x] Winner is selected without using anxiety holdout labels.
- [x] Winner is env-gated in pipeline v3 or explicitly rejected with evidence.
- [x] Khalid has one exact command to run the full fold-first anxiety pipeline and the success criterion is stated as subject-level holdout accuracy ≥60% with BA/MCC/AUC guardrails.
- [ ] `PROGRESS.md` and `HANDOFF.md` record the result and FINAL.pdf impact.

# 02 — Common cache-based evaluator

**Severity:** critical

**Status:** done — `scripts/eval_paper_spotting_configs.py` runs on cached CAS(ME)² signals and writes `output/training/paper_spotting_configs/{results.csv,split_selection.csv,summary.md}`.

## Current Problem

Existing `eval_spotting_casme2.py` evaluates the production POC-ABS detector.
New candidate curves need identical matching, metrics, split selection, and output
format, otherwise numbers cannot be compared.

## Target

Add a small evaluator script, likely `scripts/eval_paper_spotting_configs.py`,
that:

- loads CAS(ME)² GT via `eval_spotting_casme2.load_ground_truth`
- loads cached POC-ABS ROI signals from `output/training/spotting_casme2_signals`
- turns each candidate curve into intervals using a shared peak/threshold/NMS path
- reports TP/FP/FN, precision, recall, F1, IoU≥0.5 F1, median duration, apex error
- reports frame-based accuracy `F` from the benchmark paper: lower is better,
  measuring center and length deviation for true positive intervals
- reports precision-oriented diagnostics: precision at fixed recall levels, recall
  at fixed precision levels, and detections/video / false positives/video
- supports subject split A/B selection to avoid picking configs on the test half

## Required Design

- Do not recalculate dlib/POC unless needed; use existing cache first.
- No anxiety data in this evaluator.
- Selection is not only max F1. Keep a decision table with: best F1, best `F`
  among usable recall, and best precision-oriented config for downstream anxiety.
- Write `summary.md` and `results.csv` under `output/training/...`.

## Tests

Allowed:
```bash
.venv/bin/python -m py_compile scripts/eval_paper_spotting_configs.py
.venv/bin/python scripts/eval_paper_spotting_configs.py --limit 3
```

## Done Criteria

- [x] Script runs on a small limit and writes a summary.
- [x] Current baseline can be reproduced enough to compare ranking.

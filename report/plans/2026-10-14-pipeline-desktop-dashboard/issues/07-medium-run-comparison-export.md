# 07 — Run comparison and thesis-ready export

- **Severity:** medium

## Current Problem

Comparing runs currently means reading multiple summaries and progress notes.
For thesis/report work, Khalid needs a clean table and explanation of what changed.

## Target

Add run comparison:

- select 2–5 runs
- table of preset/env/config/dataset/metrics
- highlight changed inputs
- highlight best metric per column without claiming significance
- export Markdown summary for `report/findings/` or thesis notes

## Required Design

- Do not claim improvement unless source metrics justify it.
- Include warnings for small n, CI overlap, selected-best inflation, or missing baseline.
- Every exported metric includes source run ID and raw report path.

## Tests

- Compare two existing parsed summaries.
- Export Markdown and verify source links.

## Done Criteria

- [ ] User can compare runs without manually opening multiple files.
- [ ] Export is thesis-note ready and honest about uncertainty.

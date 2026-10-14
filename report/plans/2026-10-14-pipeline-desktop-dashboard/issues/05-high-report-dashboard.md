# 05 — Report parser and dashboard models

- **Severity:** high

## Current Problem

Reports are hard to read because the key conclusions are scattered across
Markdown summaries, progress docs, logs, and output folders.

## Target

Parse known report files into `reports/summary.json` and render dashboard cards:

- run status and chosen preset
- LOSO metrics: accuracy, balanced accuracy, MCC, AUC, CI if available
- baseline comparison
- holdout metrics when present
- within-subject gate p-value / BA when present
- dataset/config names
- raw links to source files

## Required Design

- Parser must never invent missing metrics.
- Summary model should include `source_path` per metric group.
- Report UI should show unknown/missing clearly.
- Support Markdown first. Add CSV/XLSX only when a needed metric is not in Markdown.

## Tests

- Parse existing `output/training/*/summary.md` samples.
- Parse a missing/partial report and show unknown fields.
- Validate JSON schema for summary output.

## Done Criteria

- [ ] At least the current pipeline training summary can be parsed.
- [ ] Dashboard displays metrics with raw source links.
- [ ] Missing report files produce an actionable empty/error state.

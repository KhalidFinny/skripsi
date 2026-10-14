# 09 — MDMD floor check

**Severity:** low

## Current Problem

The previous plan gave MDMD too much priority. Source-backed MEGC2020 MDMD reports
very weak long-video performance (CAS(ME)² overall F1 0,0376; micro F1 0,0082),
so implementing it early is unlikely to guide the >60% anxiety goal.

## Target

Only if needed for thesis comparison, implement a small MDMD floor check:

- source config: 6×6 blocks, 4 directions, top 1/3 vectors/blocks, CAS(ME)²
  `k=12` micro and `k=39` macro
- threshold family: `T = Cmean + p*(Cmax-Cmean)`, `p` sweep 0.01..0.20
- interval grouping of adjacent positives
- duration filters / NMS

## Required Design

- Label this as a floor/sanity comparator.
- Do not spend full implementation time before FD, OF-FD, and multi-window configs.
- Do not rerun anxiety based on MDMD unless it unexpectedly wins CAS(ME)² and
  precision-oriented diagnostics.

## Tests

Common evaluator and syntax checks.

## Done Criteria

- [ ] Either MDMD is explicitly skipped as not informative, or reported as a floor.

# 08 — FINAL.pdf coverage notes

**Severity:** medium

## Current Problem

FINAL.pdf currently says POC-ABS block 7×7, three ROI groups, and 58% external
test accuracy. Local evidence has moved beyond that and needs a defendable story
if supervisor asks why the implementation changed.

## Target

Update `report/findings/koreksi-final-pdf.md` or add a focused appendix note:

- current issue with old external split / old configs
- new fold-first protocol
- why spotting was decomposed and validated on CAS(ME)²
- paper-backed configs tried and which one was selected
- final anxiety result once user runs it

## Required Design

- Cover Syahrul's thesis problems without attacking the thesis wording.
- Keep claims tied to observed metrics.

## Tests

No tests.

## Done Criteria

- [ ] FINAL.pdf correction note reflects the selected spotter/result.

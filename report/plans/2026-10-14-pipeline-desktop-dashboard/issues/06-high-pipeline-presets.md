# 06 — Presets for common experiment variants

- **Severity:** high

## Current Problem

Switching variants requires remembering env vars and config file paths, e.g.
`V3_PRESPLIT=1`, `V3_SPOT_SIGNAL=combo`, `V3_SPOT_MOTION_COMP=1`,
`V3_EXTRA_CONFIGS=...`.

## Target

Add named presets that set the exact env/config bundle:

- Default v3 mean_m
- Fold-first mean_m
- Fold-first combo
- Fold-first motion-comp + MDMD
- Cutoff 0.5 A/B
- ROI25 extra config comparison
- LOSO only from existing temporal features

## Required Design

- Preset shows its env diff before running.
- User can duplicate/edit a preset for one run without mutating the original.
- Preset stores why it exists and when it should be used.
- Unsafe/destructive options like `--fresh` need explicit confirmation in UI.

## Tests

- Preset expands to expected command/env.
- Missing config path is caught before run.
- `--fresh` cannot be triggered accidentally.

## Done Criteria

- [ ] Common variants no longer require typing env vars.
- [ ] Preset expansion is visible and stored in `run.json`.
- [ ] Invalid preset cannot start a run.

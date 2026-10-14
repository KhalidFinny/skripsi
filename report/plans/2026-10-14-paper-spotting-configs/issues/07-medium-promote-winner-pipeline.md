# 07 — Promote validated winner into pipeline v3

**Severity:** medium

## Current Problem

Research configs do not affect anxiety pipeline unless wired into
`process_spotting_pipeline.py` and `run_pipeline_v3.sh`.

## Target

After a CAS(ME)² winner exists:

- add env-gated spotter mode, e.g. `V3_SPOT_ALGO=fd|swmro|mdmd_proper`
- forward env through stage 1 and stage 8
- keep default unchanged
- dry-run prints the selected algo/config
- provide one exact command for fold-first 2-config full run

## Required Design

- No default change until evidence supports it.
- Same recipe must apply to train-pool and holdout spotting.

## Tests

Allowed:
```bash
.venv/bin/python -m py_compile scripts/process_spotting_pipeline.py
bash -n scripts/run_pipeline_v3.sh
./scripts/run_pipeline_v3.sh --dry-run
```

## Done Criteria

- [ ] Env-gated winner is wired to stage 1 and 8.
- [ ] Dry-run shows the config.
- [ ] Command is documented in HANDOFF/PROGRESS.

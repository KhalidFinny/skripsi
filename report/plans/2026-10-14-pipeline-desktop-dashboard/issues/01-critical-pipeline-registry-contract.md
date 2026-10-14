# 01 — Pipeline registry and run contract

> **Status:** done for MVP (2026-10-14).

- **Severity:** critical

## Current Problem

The app cannot safely run pipelines if each run is just a remembered shell
command. Today the contract lives inside `scripts/run_pipeline_v3.sh`, docs, and
Khalid's memory: stage names, env vars, outputs, and report files are not
machine-readable.

## Target

Create a small pipeline registry that describes what the app can run:

- pipeline ID and title
- stages and stage numbers
- command template
- allowed env/config fields
- output paths
- report files
- whether the pipeline supports dry-run, resume, force, fresh, and presplit

Start with these runnable entries:

1. `pipeline_v3` — existing main pipeline.
2. `pipeline_v3_presplit` — fold-first mode.
3. `loso_only` — training from an existing feature table.
4. `casme2_spotting_eval` — spotting benchmark when needed.

## Required Design

- Prefer a simple JSON/TOML/YAML file if it stays readable. Use Python-generated
  JSON only if dynamic fields are needed.
- Keep paths relative to repo root.
- Every field that appears in UI must have a source in the registry, not hardcoded
  inside view code.
- The registry should point to `pipeline/run.sh` after stage-refactor. Until then,
  it can point to `scripts/run_pipeline_v3.sh` with a clear TODO/compat adapter.

## Tests

- Load registry in Go and validate required fields.
- Validate every command path exists.
- Validate dry-run command can be built without executing the heavy pipeline.

## Done Criteria

- [x] Registry exists and lists stages 0–8 with user-facing names.
- [x] Env fields for the known variants are typed and documented.
- [x] Go loader rejects missing command paths and duplicate IDs.
- [x] App/controller code does not hardcode stage lists.

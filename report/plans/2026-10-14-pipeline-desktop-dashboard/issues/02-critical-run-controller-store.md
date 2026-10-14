# 02 — Go run controller and structured run store

> **Status:** MVP controller done, no full pipeline run executed (2026-10-14).

- **Severity:** critical

## Current Problem

Pipeline state is ephemeral terminal output plus scattered logs. The app needs a
single source of truth for what ran, what stage is active, what failed, and where
the artifacts are.

## Target

Build a Go controller that starts one pipeline run, captures stdout/stderr,
writes structured events, and stores run metadata under `.pipeline/runs/<run-id>/`.

Minimum run store:

```text
.pipeline/runs/<run-id>/
  run.json
  events.jsonl
  stages/
    <stage>.log
  reports/
    summary.json
```

`run.json` stores command, cwd, env, selected preset, config paths, dataset, git
branch/status summary, start/end time, status, and exit code.

`events.jsonl` stores app-readable events: run started, stage started, log line,
stage completed, stage failed, report parsed.

## Required Design

- One run at a time until outputs are isolated.
- Controller must stream logs while preserving raw text.
- App state must be updated from background work without blocking the MyGo main thread.
- Use fake command fixtures for controller validation. Do not run the real full pipeline unless asked.
- Stop must be deliberate: send interrupt/terminate, mark run stopped, keep logs.

## Tests

- Fake command emits stage-like lines and exits 0: run status becomes success.
- Fake command exits nonzero: run status becomes failed and stores tail.
- Metadata persists after controller restarts.
- `go build` and `go vet` pass.

## Done Criteria

- [x] Controller can run a command and write run metadata.
- [ ] Controller dry-run execution from the real app was not run because Khalid's contract forbids smoke/e2e unless asked.
- [x] Failed commands map to a failed run and failed stage where detectable.
- [x] Existing raw logs are never overwritten by the controller.

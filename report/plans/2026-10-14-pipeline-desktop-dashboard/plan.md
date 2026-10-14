# Plan — MyGo native desktop app for pipeline dashboard and reports

> **Status:** MVP implemented locally, not shipped (2026-10-14).

- **Goal:** replace command-memory pipeline operation with a native desktop app that can switch pipelines, run them, show stage progress, diagnose failures, and render readable reports.
- **Architecture:** MyGo native UI → Go run controller → existing Python/bash pipeline via a machine-readable registry → structured run store and normalized reports.
- **Tech Stack:** Go 1.27 + MyGo native UI, existing Python 3.12 pipeline, local JSON/JSONL run metadata, existing Markdown/CSV/XLSX outputs.

## Must Not Forget

- **Do not build a terminal skin.** The app must expose pipeline state, stages, metrics, and diagnostics as first-class UI, with terminal logs only as drill-down.
- **Do not rewrite the research pipeline in Go.** Python/bash remains the compute layer until there is a measured reason to move a piece.
- **Do not run full pipeline/e2e unless Khalid asks.** Use dry-run, fake commands, build/vet, and UI screenshots for verification.
- **Respect the existing stage-refactor plan.** Prefer `pipeline/run.sh` and numbered stages after `report/plans/2026-10-13-pipeline-stage-refactor/` is executed. If this app starts earlier, add a compatibility adapter for `scripts/run_pipeline_v3.sh`.
- **One run at a time by default.** The current pipeline writes shared outputs (`output/`, `experiments/features/apex/`, `logs/`), so concurrent runs risk corrupting each other unless the outputs are isolated first.
- **Every run must be reproducible.** Store command, cwd, env, git state, config paths, dataset name, start/end time, and selected preset.
- **Stage names stay human-readable and stable:** split, spotting/apex, extraction, cache, temporal, gate, training, collect, holdout.
- **Reports need source links.** Every dashboard metric links back to the raw summary/log/artifact that produced it.
- **UI direction is now set:** Aqua OS Dashboard, a Frutiger Aero MyGo native desktop style. Make it bright, clean, glossy, aqua/green, and nostalgic, but keep diagnostics and reports readable. Use sky/aqua depth, glossy white-blue panels, green glass status blocks, clear red failure states, spacious panels, and readable stage blocks. Do not turn it into illegible bubble wallpaper or fake terminal cosplay.
- **No fabricated metrics or claims.** If the parser cannot find a metric, show unknown with the raw file link, not a guessed value.

## Issue Index

### Critical
- [01 — Pipeline registry and run contract](issues/01-critical-pipeline-registry-contract.md)
- [02 — Go run controller and structured run store](issues/02-critical-run-controller-store.md)
- [03 — Native app shell and pipeline run screen](issues/03-critical-native-app-shell.md)

### High
- [04 — Stage diagnostics and log inspector](issues/04-high-stage-diagnostics-log-inspector.md)
- [05 — Report parser and dashboard models](issues/05-high-report-dashboard.md)
- [06 — Presets for common experiment variants](issues/06-high-pipeline-presets.md)

### Medium
- [07 — Run comparison and thesis-ready export](issues/07-medium-run-comparison-export.md)
- [08 — Safe stop, resume, and rerun controls](issues/08-medium-stop-resume-rerun.md)

### Low
- [09 — Packaging, app icon, and launch ergonomics](issues/09-low-packaging-launch.md)

## Target Architecture

```text
desktop/pipelinedesk/
  main.go                 MyGo entry point
  app.go                  app state, route/page state, selected run
  view.go                 shell, sidebar, main panes
  theme.go                chosen palette and metrics
  pipeline/
    registry.go           loads runnable pipeline definitions
    presets.go            known variants and env bundles
  controller/
    runner.go             starts/stops one run
    events.go             structured event model
    logs.go               log capture and tailing
    store.go              .pipeline/runs/<run-id>/ layout
  reports/
    parse.go              summary.md/log parsers
    models.go             metrics shown by dashboard
  diagnostics/
    rules.go              known failure patterns and hints

pipeline/
  registry.json           source of truth for app-visible pipelines
  run.sh                  app-preferred runner after stage refactor

.pipeline/runs/
  2026-10-14_153000_fold-first-combo/
    run.json
    events.jsonl
    stages/
      1_spotting.log
      6_train_loso.log
    reports/
      summary.json
```

Main app screens:

1. **Pipelines** — switch between pipeline v3 fold-first, CAS(ME)² spotting eval, LOSO only, baseline, and future variants.
2. **Run Setup** — choose dataset/config/preset without typing env vars.
3. **Live Run** — stage timeline with current stage, elapsed time, ETA when known, and last log lines.
4. **Diagnostics** — failed stage, likely cause, exact raw log lines, outputs present/missing, suggested next action.
5. **Reports** — accuracy/BA/MCC/AUC, baseline, CI, within-subject gate, holdout status, raw links.
6. **Compare Runs** — compare selected runs and explain what changed: signal, config, presplit, dataset, metrics.

## Priority Order

1. **01 → 02** — define pipeline contract and run store. Without this, UI becomes a fragile command wrapper.
2. **03** — minimal native app that can list pipelines and launch dry-run/full command with clear state.
3. **04 → 05** — diagnostics and report parser, the core value over terminal.
4. **06** — presets, so Khalid can switch variants without env var memory.
5. **07 → 08** — comparison/export and safe rerun controls.
6. **09** — package and polish after the workflow proves useful.

## Validation Commands

```bash
# Controller/app compile only, no full pipeline run
go build ./desktop/pipelinedesk/...
go vet ./desktop/pipelinedesk/...

# Runner contract proves stage plan without executing heavy work
./pipeline/run.sh --dry-run
V3_PRESPLIT=1 ./pipeline/run.sh --dry-run

# Temporary compatibility path if pipeline/ refactor is not done yet
./scripts/run_pipeline_v3.sh --dry-run
V3_PRESPLIT=1 ./scripts/run_pipeline_v3.sh --dry-run

# UI visual verification once app exists
go tool mygo dev ./desktop/pipelinedesk
# capture screenshot(s) of: setup, live run, failed stage, report dashboard
```

## Rollout Plan

- [x] Decide UI direction before build: Aqua OS Dashboard, Frutiger Aero native desktop, fun but readable.
- [x] 01 — add pipeline registry with stage names, commands, env fields, outputs, and report files.
- [x] 02 — add run controller and `.pipeline/runs/<run-id>/` store using a fake command first.
- [x] 02 — adapter for `pipeline/run.sh`; compatibility adapter for `scripts/run_pipeline_v3.sh` only if stage refactor is not yet executed.
- [x] 03 — create MyGo native app shell with sidebar, setup page, and live run timeline.
- [x] 04 — add log inspector and stage diagnostics from structured events + known error patterns.
- [x] 05 — parse existing training summaries and show report dashboard with raw source links.
- [x] 06 — add presets for the commands Khalid actually runs.
- [ ] 07 — add compare-runs table and export Markdown/PDF-ready summary.
- [ ] 08 — add stop/resume/rerun once run isolation is safe enough.
- [x] 09 — package app with MyGo and add a root shortcut command.

## Done Criteria

- [x] Khalid can open the desktop app and choose a pipeline without opening docs.
- [x] Khalid can run at least dry-run from the app and see the exact stage sequence.
- [x] A run writes `run.json`, `events.jsonl`, and stage logs. `reports/summary.json` remains future work.
- [x] The UI shows stage progress and makes the failing stage obvious.
- [x] The dashboard shows metrics placeholders or parsed metrics with links to raw report files.
- [x] Common variants are presets, not typed env var strings.
- [x] App build passes `go build` and `go vet`.
- [x] UI has inspected screenshots for setup, running, failure, and report states.

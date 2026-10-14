# CONTEXT — Native desktop app for running and diagnosing pipelines

## Problem

Khalid does not want to keep typing long command lines to run the research
pipeline. The current workflow is powerful, but it is operator-hostile:

- Pipeline entry points are shell/Python commands (`./run`, `scripts/run_pipeline_v3.sh`, individual `scripts/*.py`).
- Progress lives in terminal output and many `logs/stage*.log` files.
- Reports exist, but the important answer is scattered across Markdown, CSV, XLSX, PKL outputs, and training folders.
- Switching between variants (`V3_PRESPLIT`, `V3_SPOT_SIGNAL`, `V3_EXTRA_CONFIGS`, configs, datasets) requires remembering env vars and file paths.
- Diagnosing failure means tailing logs and knowing which stage owns the problem.
- The repo already has a separate plan to make pipeline stages easier to find: `report/plans/2026-10-13-pipeline-stage-refactor/`. That helps the code layout, but it does not solve the day-to-day running and diagnosis experience.

The app Khalid wants is a native desktop control room: choose a pipeline, run it,
watch each stage, diagnose failures, and read a clean report without opening a
terminal unless needed.

## Fix

Build a MyGo native UI app named **Pipeline Desk** (working name) inside this
repo, backed by a thin Go run controller around the existing Python/bash
pipeline.

The key decision: **do not make the app a pretty wrapper over arbitrary terminal
commands.** That would only hide the mess. First create a small machine-readable
pipeline contract, then the app runs that contract and renders its state.

Implementation shape:

1. Keep pipeline logic in Python/bash for now.
2. Add a pipeline registry/manifest that describes each pipeline, stages, inputs,
   env vars, outputs, and report files.
3. Add a stable run controller that starts one run, streams logs, writes
   structured events, records metadata, and supports stop/resume where the
   pipeline already supports it.
4. Build a MyGo native UI around that controller:
   pipeline switcher, run setup, stage timeline, log inspector, artifacts, and
   report viewer.
5. Promote the existing Markdown/CSV summaries into a normalized report JSON so
   the dashboard can compare runs and point to likely bottlenecks.

## Architecture Now

After the change, the flow is:

```text
┌───────────────────────────────────────────────────────────────────┐
│ MyGo native app: Pipeline Desk                                     │
│  ├─ pipeline switcher                                               │
│  ├─ run setup                                                       │
│  ├─ stage timeline                                                  │
│  ├─ log / artifact inspector                                        │
│  └─ report dashboard                                                │
└──────────────────────────────┬────────────────────────────────────┘
                               │ starts/stops/observes
┌──────────────────────────────▼────────────────────────────────────┐
│ Go run controller                                                  │
│  ├─ reads pipeline/registry.json or pipeline/registry.py output     │
│  ├─ spawns existing scripts with explicit env                       │
│  ├─ captures stdout/stderr                                          │
│  ├─ writes run metadata + structured events                         │
│  └─ parses known report files                                       │
└──────────────────────────────┬────────────────────────────────────┘
                               │ executes
┌──────────────────────────────▼────────────────────────────────────┐
│ Existing pipeline                                                   │
│  ├─ stage 0 presplit                                                │
│  ├─ stage 1 spotting / apex                                         │
│  ├─ stage 2 feature extraction                                      │
│  ├─ stage 3 cache                                                   │
│  ├─ stage 4 temporal features                                       │
│  ├─ stage 5 gate                                                    │
│  ├─ stage 6 LOSO training                                           │
│  ├─ stage 7 collect/baseline                                        │
│  └─ stage 8 holdout                                                 │
└──────────────────────────────┬────────────────────────────────────┘
                               │ writes
┌──────────────────────────────▼────────────────────────────────────┐
│ Run store                                                           │
│  .pipeline/runs/<run-id>/                                           │
│   ├─ run.json                                                       │
│   ├─ events.jsonl                                                   │
│   ├─ stages/<stage>.log                                             │
│   ├─ reports/summary.json                                           │
│   └─ links to output/, logs/, experiments/features/                  │
└───────────────────────────────────────────────────────────────────┘
```

## Key Files

**New app and controller:**

- `desktop/pipelinedesk/main.go` — MyGo app entry point.
- `desktop/pipelinedesk/app.go` — app state, selected pipeline, selected run.
- `desktop/pipelinedesk/view.go` — native UI shell.
- `desktop/pipelinedesk/theme.go` — visual tokens after Khalid picks direction.
- `desktop/pipelinedesk/controller/` — run controller, process spawning, event writer.
- `desktop/pipelinedesk/reports/` — report parsing and dashboard models.
- `desktop/pipelinedesk/mygo.json` or root app config if MyGo expects one app per module.

**Pipeline contract:**

- `pipeline/registry.*` — list of runnable pipelines and their stages.
- `pipeline/run.sh` — preferred entry point after the existing stage-refactor plan is executed.
- `scripts/run_pipeline_v3.sh` — temporary entry point if the app starts before the refactor lands.

**Run store:**

- `.pipeline/runs/<run-id>/run.json` — inputs, command, env, start/end, status.
- `.pipeline/runs/<run-id>/events.jsonl` — append-only structured events.
- `.pipeline/runs/<run-id>/stages/*.log` — captured stage logs.
- `.pipeline/runs/<run-id>/reports/summary.json` — normalized metrics for the dashboard.

**Existing outputs to parse:**

- `output/training/<dataset>/summary.md`
- `output/training/<dataset>_holdout/summary.md`
- `output/presplit/summary.md`
- `logs/pipeline_v3_*.log`
- `logs/stage*.log`
- `experiments/features/apex/*`

## Important Behavior Changes

- Running a pipeline becomes a selected app action, not a remembered command.
- Each run gets a stable run ID and a single folder that points to all relevant
  logs, reports, and artifacts.
- Env vars become typed UI fields or presets.
- Failures are shown at the stage that failed, with the last useful log lines,
  known likely causes, and the exact rerun/resume option.
- Reports become readable dashboard cards and comparisons, while raw Markdown
  and logs stay accessible.
- Terminal remains available as an escape hatch, not the primary interface.

## Tests

Khalid's rule: do not run full tests, smoke tests, or e2e unless asked.
Allowed validation during execution:

- `go build ./desktop/pipelinedesk/...`
- `go vet ./desktop/pipelinedesk/...`
- MyGo view snapshots or `just snapshots` equivalent once the UI exists.
- `./pipeline/run.sh --dry-run` or `./scripts/run_pipeline_v3.sh --dry-run` from the controller.
- A fake command adapter for controller logic, not the real long pipeline.
- Manual app launch and screenshot for UI verification.

Full real pipeline runs remain Khalid-triggered unless explicitly requested.

## Validation Done

Discovery for this plan:

- Current repo has `./run` shortcuts and `scripts/run_pipeline_v3.sh`, but no desktop app.
- `scripts/run_pipeline_v3.sh` already has a clear stage model, dry-run mode, per-stage banners, logs, fold-first mode, and multi-config support.
- Existing plan `report/plans/2026-10-13-pipeline-stage-refactor/` already proposes `pipeline/run.sh` and numbered stages. This app should build on that rather than fight it.
- MyGo supports native UI in Go, the same style of app used by Meiro and kupic.
- kupic proves the pattern Khalid likes: native MyGo app, Go controller, long work off the main thread, dark product-specific theme, screenshots for UI verification.
- Khalid changed the visual direction after exploring brutalism: **Aqua OS Dashboard**, the practical daily-use Frutiger Aero variant: bright, clean, aqua/green, glossy, nostalgic. Use that as the app identity unless changed again.

No implementation has been done yet.

## Known Notes

- The app should not start by replacing the pipeline internals. It should first
  observe and control the existing pipeline through a stable contract.
- The pipeline stage refactor is a strong prerequisite. If skipped, the desktop
  app needs a compatibility adapter for `scripts/run_pipeline_v3.sh` and will
  carry more path debt.
- UI direction is no longer open: Aqua OS Dashboard Frutiger Aero. The constraint
  is functional gloss, not illegible decoration. Reports, failure diagnosis, and
  long logs must stay readable.
- MyGo native UI is the right default because this is a local desktop tool with
  long-running processes, logs, files, and no need for a web server.

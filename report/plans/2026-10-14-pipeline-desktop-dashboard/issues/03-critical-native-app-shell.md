# 03 — Native app shell and pipeline run screen

> **Status:** done for MVP (2026-10-14).

- **Severity:** critical

## Current Problem

There is no desktop UI. The first app slice needs to prove the workflow: select
pipeline, choose preset/env, run dry-run or command, and see stage state.

## Target

Create a MyGo native UI app in `desktop/pipelinedesk/` with:

- top pipeline tabs: pipelines switch above the content, not in a sidebar
- run setup page: selected pipeline, preset, key options, start button
- live run page: stage timeline, current status, elapsed time, log tail
- current run panel: status, run store path, expanded command

## Required Design

- UI direction is confirmed by Khalid: Aqua OS Dashboard, the practical Frutiger
  Aero variant: bright, clean, glossy, aqua/green, nostalgic, and visibly
  different from Meiro/kupic.
- Use Frutiger Aero as functional grouping, not as noise: sky/aqua depth, glossy
  white-blue panels, soft highlights, fresh green status blocks, clear red
  failure states, readable typography, and spacious panels. Keep reports and
  diagnostics readable.
- Avoid fake terminal cosplay as the primary UI. Logs are a drill-down, not the
  whole design.
- Native UI only, matching Meiro/kupic pattern. No webview, no Bun frontend.
- Long work runs off the main thread and updates UI through the app's safe update path.
- Every interactive control must do something real or be hidden.
- Loading, empty, and error states are required.

## Tests

- `go build ./desktop/pipelinedesk/...`
- `go vet ./desktop/pipelinedesk/...`
- Launch with fake registry/store.
- Screenshot setup, running, failed, and report states.

## Done Criteria

- [x] App opens and lists registered pipelines.
- [x] Empty state explains no runs yet.
- [x] Start dry-run is wired to controller and timeline state. Real launch was not executed because smoke/e2e runs were not requested.
- [x] Failure state is visible and navigable.
- [x] Screenshots are captured and inspected before delivery.
- [x] Final Aero Ribbon screenshots re-inspected after the last overlap patch; the stage-timeline bleed behind `Stage details` is gone.
- [x] The rejected sidebar shell is removed from `view.go`; the app renders only the Aero Ribbon variant.
- [x] `./run desk` builds and the app stays running.

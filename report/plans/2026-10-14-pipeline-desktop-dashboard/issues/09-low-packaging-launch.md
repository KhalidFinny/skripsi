# 09 — Packaging, app icon, and launch ergonomics

- **Severity:** low

## Current Problem

Even after the app works, Khalid needs an easy way to open it, ideally not from a long Go/MyGo command.

## Target

Package and expose the app:

- root shortcut, e.g. `./run desk` or `./run app`
- MyGo dev/build commands documented
- Linux desktop build under `build/`
- app icon only after Khalid gives direction or approves a placeholder

## Required Design

- Do not generate a final logo/icon without explicit direction.
- Build artifacts remain ignored.
- Keep the shortcut simple and consistent with existing `./run` command style.

## Tests

- `./run desk` starts dev app or prints clear setup instructions.
- `go tool mygo build ./desktop/pipelinedesk` succeeds when packaging is ready.

## Done Criteria

- [ ] App can be launched from one memorable command.
- [ ] Build command is documented.
- [ ] No fake final icon is shipped.

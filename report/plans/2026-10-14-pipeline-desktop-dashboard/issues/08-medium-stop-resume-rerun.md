# 08 — Safe stop, resume, and rerun controls

- **Severity:** medium

## Current Problem

Long runs need operational controls, but stopping or rerunning can leave partial
outputs. Today resume/force/fresh behavior is in shell flags and file checks.

## Target

Add safe controls:

- stop current run
- rerun same preset
- resume from failed stage when supported
- rerun one stage when supported
- fresh run with explicit warning about outputs touched

## Required Design

- Stop preserves metadata and marks run as stopped.
- Fresh must list what it will delete or overwrite before confirmation.
- Resume uses existing pipeline flags, not custom file surgery.
- Stage rerun only appears for stages where the underlying runner supports it.

## Tests

- Fake long-running command can be stopped.
- Stopped run remains inspectable.
- Resume command generated correctly for known failed stage.

## Done Criteria

- [ ] Stop/rerun/resume controls are safe and explicit.
- [ ] No control silently deletes output.

# 04 — Stage diagnostics and log inspector

- **Severity:** high

## Current Problem

When a stage fails, Khalid has to inspect terminal output or find the right log
file manually. The difficult part is identifying which stage failed and why.

## Target

Add a diagnostics pane for each run:

- failed stage highlighted
- last 50 useful log lines
- full log viewer with search/filter
- known error hints: missing dataset mount, OOM, missing model file, config path
  mismatch, 0 folds done, missing feature table, command not found
- links to raw log files and output folders

## Required Design

- Hints must be rule-based and conservative. If no known pattern matches, show
  unknown and the raw log, not a fake diagnosis.
- Keep terminal log text copyable.
- Show output presence checks, e.g. expected metadata/report exists or missing.
- Preserve Indonesian stage labels where current logs use them.

## Tests

- Feed sample log snippets for each known pattern.
- Verify unknown logs stay unknown.
- Verify each diagnostic links to the stage log path.

## Done Criteria

- [ ] Failed runs show the failed stage first.
- [ ] Known failure patterns produce useful hints.
- [ ] Unknown failures remain honest.
- [ ] Full raw log is still accessible.

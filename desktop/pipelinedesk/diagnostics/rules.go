package diagnostics

import "strings"

type Finding struct {
	Title string
	Hint  string
	Level string
}

func Analyze(lines []string) Finding {
	joined := strings.ToLower(strings.Join(lines, "\n"))
	switch {
	case strings.Contains(joined, "no such file") || strings.Contains(joined, "not found"):
		return Finding{Title: "Missing file or command", Hint: "Check dataset mount, script path, config path, or model file path.", Level: "error"}
	case strings.Contains(joined, "killed") || strings.Contains(joined, "out of memory") || strings.Contains(joined, "oom"):
		return Finding{Title: "Memory pressure", Hint: "Reduce workers, close heavy apps, or resume from the failed stage.", Level: "error"}
	case strings.Contains(joined, "0 fold") || strings.Contains(joined, "0 folds"):
		return Finding{Title: "No folds completed", Hint: "Check dataset export and training config mismatch before rerunning.", Level: "error"}
	case strings.Contains(joined, "threshold") || strings.Contains(joined, "below"):
		return Finding{Title: "Validation gate failed", Hint: "The run finished far enough to diagnose signal quality. Open the gate log and report summary.", Level: "warning"}
	case len(lines) == 0:
		return Finding{Title: "No logs yet", Hint: "Start a dry-run or pipeline run to collect diagnostics.", Level: "info"}
	default:
		return Finding{Title: "No known pattern", Hint: "Open the raw log. No conservative diagnosis matched the current tail.", Level: "info"}
	}
}

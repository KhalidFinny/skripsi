package reports

import (
	"os"
	"regexp"
	"strings"
)

type Summary struct {
	Accuracy string
	BA       string
	MCC      string
	AUC      string
	Source   string
	Missing  bool
}

var metricPatterns = map[string]*regexp.Regexp{
	"accuracy": regexp.MustCompile(`(?im)(?:^|\|)\s*accuracy\s*\|\s*([\-+]?[0-9]+(?:[,.][0-9]+)?%?)`),
	"ba":       regexp.MustCompile(`(?im)(?:^|\|)\s*(?:BA|balanced accuracy)\s*\|\s*([\-+]?[0-9]+(?:[,.][0-9]+)?%?)`),
	"mcc":      regexp.MustCompile(`(?im)(?:^|\|)\s*MCC\s*\|\s*([\-+]?[0-9]+(?:[,.][0-9]+)?)`),
	"auc":      regexp.MustCompile(`(?im)(?:^|\|)\s*AUC(?:[^|]*)?\|\s*([\-+]?[0-9]+(?:[,.][0-9]+)?)`),
}

func ParseMarkdown(path string) Summary {
	summary := Summary{Source: path, Missing: true, Accuracy: "[from report]", BA: "[from report]", MCC: "[from report]", AUC: "[from report]"}
	data, err := os.ReadFile(path)
	if err != nil {
		return summary
	}
	summary.Missing = false
	text := strings.ReplaceAll(string(data), ",", ".")
	if value := find(metricPatterns["accuracy"], text); value != "" {
		summary.Accuracy = value
	}
	if value := find(metricPatterns["ba"], text); value != "" {
		summary.BA = value
	}
	if value := find(metricPatterns["mcc"], text); value != "" {
		summary.MCC = value
	}
	if value := find(metricPatterns["auc"], text); value != "" {
		summary.AUC = value
	}
	return summary
}

func find(re *regexp.Regexp, text string) string {
	match := re.FindStringSubmatch(text)
	if len(match) < 2 {
		return ""
	}
	return match[1]
}

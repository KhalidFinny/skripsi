package main

import (
	"strings"
	"time"

	"github.com/egoist/mygo/ui"

	"github.com/SyahrulBhudiF/Skripsi/desktop/pipelinedesk/controller"
	"github.com/SyahrulBhudiF/Skripsi/desktop/pipelinedesk/pipeline"
)

func (a *app) view(c *ui.Context) {
	a.viewVariant(c, variantRibbon)
}

func (a *app) focusStage() controller.StageStatus {
	definition, ok := a.selectedDefinition()
	if !ok {
		return controller.StageStatus{Stage: pipeline.Stage{Number: 6, Name: "GATE"}, Status: controller.StatusFailed}
	}
	for _, status := range a.stageStatuses(definition) {
		if status.Status == controller.StatusFailed {
			return status
		}
	}
	for _, status := range a.stageStatuses(definition) {
		if status.Status == controller.StatusRunning {
			return status
		}
	}
	for _, status := range a.stageStatuses(definition) {
		if status.Status == controller.StatusQueued {
			return status
		}
	}
	return controller.StageStatus{Stage: definition.Stages[0], Status: controller.StatusQueued}
}

func stageDetailState(status controller.Status) (label string, color ui.Color, symbol string) {
	switch status {
	case controller.StatusSuccess:
		return "Finished", aquaGreenLo, "✓"
	case controller.StatusRunning:
		return "Running", aquaBlue, "▶"
	case controller.StatusFailed:
		return "Failed", aquaRed, "×"
	case controller.StatusStopped:
		return "Stopped", aquaCoral, "■"
	default:
		return "Waiting", aquaMuted, "…"
	}
}

func detailRow(c *ui.Context, label, value string) {
	ui.Row(c).Gap(12).AlignItems(ui.Center).Children(func() {
		ui.Text(c, label).Width(88).FontSize(12).Bold().TextColor(aquaMuted)
		ui.Text(c, value).FontSize(12).TextColor(aquaInk).Grow(1).MaxLines(2)
	})
}

func artifactChip(c *ui.Context, label, path string) {
	ui.Row(c).Grow(1).Basis(0).Padding(9, 12).Gap(8).Radius(13).AlignItems(ui.Center).
		Background(ui.RGBA(246, 253, 255, 0.72)).Border(1, ui.RGBA(95, 168, 216, 0.45)).Children(func() {
		ui.Text(c, "▣").FontSize(13).TextColor(aquaBlue)
		ui.Column(c).Gap(1).Grow(1).MinWidth(0).Children(func() {
			ui.Text(c, label).FontSize(12).Bold().TextColor(aquaInk).SingleLine()
			if path != "" {
				ui.Text(c, path).FontSize(11).TextColor(aquaMuted).SingleLine()
			}
		})
	})
}

func reportPath(definition pipeline.Definition) string {
	if len(definition.Reports) == 0 {
		return ""
	}
	return definition.Reports[0].Path
}

func displayTime(t time.Time) string {
	if t.IsZero() {
		return "Not started"
	}
	return t.Format("2006-01-02 15:04:05")
}

func displayDuration(start, end time.Time) string {
	if start.IsZero() {
		return "Not started"
	}
	if end.IsZero() {
		elapsed := time.Since(start).Round(time.Second)
		if elapsed < 0 {
			return "Just started"
		}
		return elapsed.String()
	}
	duration := end.Sub(start).Round(time.Second)
	if duration < 0 {
		return "Just started"
	}
	return duration.String()
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			return value
		}
	}
	return "Unknown"
}

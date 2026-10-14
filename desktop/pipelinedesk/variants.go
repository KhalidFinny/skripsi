package main

import (
	"path/filepath"
	"strings"

	"github.com/egoist/mygo/ui"

	"github.com/SyahrulBhudiF/Skripsi/desktop/pipelinedesk/controller"
	"github.com/SyahrulBhudiF/Skripsi/desktop/pipelinedesk/pipeline"
)

type designVariant int

const (
	variantRibbon designVariant = iota
	variantControlPanel
	variantLabMonitor
)

type aeroPalette struct {
	bgTop    ui.Color
	bgBottom ui.Color
	panelTop ui.Color
	panelMid ui.Color
	panelLow ui.Color
	line     ui.Color
	lineSoft ui.Color
	ink      ui.Color
	muted    ui.Color
	blue     ui.Color
	blueSoft ui.Color
	green    ui.Color
	greenTop ui.Color
	red      ui.Color
	gold     ui.Color
	white    ui.Color
}

var win7 = aeroPalette{
	bgTop:    ui.Hex("#EAF8FF"),
	bgBottom: ui.Hex("#B9DDF1"),
	panelTop: ui.RGBA(255, 255, 255, 0.96),
	panelMid: ui.RGBA(244, 251, 255, 0.94),
	panelLow: ui.RGBA(220, 239, 249, 0.88),
	line:     ui.Hex("#7FAFD1"),
	lineSoft: ui.Hex("#C1DCEC"),
	ink:      ui.Hex("#173F68"),
	muted:    ui.Hex("#527A9B"),
	blue:     ui.Hex("#2F79BC"),
	blueSoft: ui.Hex("#D8EEF9"),
	green:    ui.Hex("#77C760"),
	greenTop: ui.Hex("#D8F8CB"),
	red:      ui.Hex("#D96666"),
	gold:     ui.Hex("#F2C761"),
	white:    ui.Hex("#FFFFFF"),
}

func (a *app) viewVariant(c *ui.Context, variant designVariant) {
	c.SetTheme(a.theme)
	c.Root().Background(win7.bgBottom).Draw(func(p *ui.Painter, r ui.Rect) {
		p.Image(frutigerAeroBackground(), r, ui.Cover)
	})
	switch variant {
	case variantControlPanel:
		a.controlPanelVariant(c)
	case variantLabMonitor:
		a.labMonitorVariant(c)
	default:
		a.ribbonVariant(c)
	}
}

func (a *app) variantHeader(c *ui.Context, compact bool) {
	bar := c.TitleBar()
	height := float32(66)
	if compact {
		height = 58
	}
	ui.Row(c).Height(max(float32(bar.Height), height)).Padding(0, float32(bar.Right+24), 0, float32(platformTitleInset())).
		Gap(14).AlignItems(ui.Center).DragWindow().Children(func() {
		ui.Text(c, "Pipeline Desk").FontSize(30).Bold().TextColor(win7.ink).SingleLine()
		ui.Text(c, "Windows 7 Aero study console").FontSize(12).TextColor(win7.muted).Padding(9, 0, 0).SingleLine()
		ui.Spacer(c)
		ui.Text(c, "Build").FontSize(12).TextColor(win7.muted)
		ui.Text(c, "Run").FontSize(12).TextColor(win7.muted)
		ui.Text(c, "Reports").FontSize(12).TextColor(win7.muted)
	})
}

func (a *app) pipelineTabs(c *ui.Context, centered bool) {
	if a.registry == nil {
		return
	}
	row := ui.Row(c).Height(52).Gap(8).AlignItems(ui.End).Padding(0, 18)
	if centered {
		row.Center()
	}
	row.Children(func() {
		for _, definition := range a.registry.Pipelines {
			a.pipelineTab(c, definition)
		}
	})
}

func (a *app) pipelineTab(c *ui.Context, definition pipeline.Definition) {
	selected := definition.ID == a.selectedPipeline
	tab := ui.Row(c).Height(38).MinWidth(138).Padding(8, 16).Radius(10).AlignItems(ui.Center).
		Border(1, win7.line).Label(definition.Name)
	if selected {
		tab.Gradient(win7.white, win7.blueSoft, 180).TextColor(win7.ink)
	} else {
		tab.Gradient(ui.RGBA(255, 255, 255, 0.72), ui.RGBA(220, 239, 249, 0.62), 180).TextColor(win7.muted)
	}
	tab.Children(func() {
		ui.Text(c, definition.Name).FontSize(13).Bold().SingleLine()
	})
	if tab.Clicked() {
		a.selectPipeline(definition.ID)
	}
}

func (a *app) ribbonVariant(c *ui.Context) {
	definition, ok := a.selectedDefinition()
	ui.Column(c).Fill().Children(func() {
		a.variantHeader(c, false)
		a.pipelineTabs(c, false)
		ui.Scroll(c).Grow(1).Padding(16, 22, 22).Gap(12).Children(func() {
			if !ok {
				a.variantPanel(c, "Registry", func() { ui.Text(c, a.loadErr).TextColor(win7.red).FontSize(13) })
				return
			}
			ui.Row(c).Height(190).Gap(14).Children(func() {
				ui.Box(c).Grow(1).Basis(0).MinWidth(0).Children(func() { a.variantRunSetup(c, definition) })
				ui.Box(c).Grow(1).Basis(0).MinWidth(0).Children(func() { a.currentRunPanel(c) })
			})
			a.variantStageTimeline(c, definition, false)
			ui.Row(c).Height(260).Gap(14).Children(func() {
				ui.Box(c).Grow(1).Basis(0).MinWidth(0).Children(func() { a.variantStageDetails(c) })
				ui.Box(c).Grow(1).Basis(0).MinWidth(0).Children(func() { a.variantReport(c, definition) })
			})
			a.variantArtifacts(c, definition)
		})
	})
}

func (a *app) controlPanelVariant(c *ui.Context) {
	definition, ok := a.selectedDefinition()
	ui.Column(c).Fill().Children(func() {
		a.variantHeader(c, true)
		a.pipelineTabs(c, false)
		ui.Scroll(c).Grow(1).Padding(24, 28, 26).Gap(18).Children(func() {
			if !ok {
				a.variantPanel(c, "Registry", func() { ui.Text(c, a.loadErr).TextColor(win7.red).FontSize(13) })
				return
			}
			a.variantRunSetup(c, definition)
			a.variantStageTimeline(c, definition, true)
			ui.Row(c).Height(252).Gap(18).Children(func() {
				ui.Box(c).Grow(1).Basis(0).MinWidth(0).Children(func() { a.variantStageDetails(c) })
				ui.Box(c).Grow(1).Basis(0).MinWidth(0).Children(func() { a.variantReport(c, definition) })
			})
			a.variantArtifacts(c, definition)
		})
	})
}

func (a *app) labMonitorVariant(c *ui.Context) {
	definition, ok := a.selectedDefinition()
	ui.Column(c).Fill().Children(func() {
		a.variantHeader(c, true)
		a.pipelineTabs(c, true)
		ui.Scroll(c).Grow(1).Padding(18, 22, 22).Gap(14).Children(func() {
			if !ok {
				a.variantPanel(c, "Registry", func() { ui.Text(c, a.loadErr).TextColor(win7.red).FontSize(13) })
				return
			}
			a.variantRunStrip(c, definition)
			a.variantStageTimeline(c, definition, true)
			ui.Row(c).Height(332).Gap(14).Children(func() {
				ui.Box(c).Grow(1).Basis(0).MinWidth(0).Children(func() { a.variantStageDetails(c) })
				ui.Column(c).Grow(1).Basis(0).Gap(14).Children(func() {
					a.variantReport(c, definition)
					a.variantArtifacts(c, definition)
				})
			})
		})
	})
}

func (a *app) variantPanel(c *ui.Context, title string, children func()) {
	ui.Column(c).FillWidth().MinWidth(0).Padding(13, 16).Gap(9).Radius(10).Border(1, win7.line).
		Gradient(win7.panelTop, win7.panelLow, 180).Children(func() {
		ui.Text(c, title).FontSize(16).Bold().TextColor(win7.ink).SingleLine()
		children()
	})
}

func (a *app) variantRunSetup(c *ui.Context, definition pipeline.Definition) {
	a.variantPanel(c, "Run setup", func() {
		presetOptions := make([]string, 0, len(definition.Presets))
		for _, preset := range definition.Presets {
			presetOptions = append(presetOptions, preset.ID)
		}
		variantField(c, "Preset", func() {
			if ui.Select(c.Key("variant-preset"), &a.selectedPreset, presetOptions).Grow(1).Changed() {
				a.selectPreset(a.selectedPreset)
			}
		})
		variantField(c, "Run name", func() { ui.TextInput(c.Key("variant-run-name"), &a.runName).Grow(1) })
		ui.Row(c).Gap(12).AlignItems(ui.Center).Children(func() {
			ui.Checkbox(c.Key("variant-dry-run"), &a.dryRun, "Dry-run first")
			ui.Spacer(c)
			a.variantStartButton(c)
		})
		if preset, ok := a.selectedPresetValue(); ok {
			ui.Text(c, preset.Description).FontSize(12).TextColor(win7.muted).MaxLines(2)
		}
	})
}

func (a *app) variantRunStrip(c *ui.Context, definition pipeline.Definition) {
	a.variantPanel(c, "Run controls", func() {
		ui.Row(c).Gap(14).AlignItems(ui.Center).Children(func() {
			ui.Text(c, "Preset").FontSize(12).Bold().TextColor(win7.muted)
			presetOptions := make([]string, 0, len(definition.Presets))
			for _, preset := range definition.Presets {
				presetOptions = append(presetOptions, preset.ID)
			}
			ui.Select(c.Key("strip-preset"), &a.selectedPreset, presetOptions).Width(240)
			ui.Checkbox(c.Key("strip-dry-run"), &a.dryRun, "Dry-run first")
			ui.Spacer(c)
			a.variantStartButton(c)
		})
	})
}

func (a *app) currentRunPanel(c *ui.Context) {
	a.variantPanel(c, "Current run", func() {
		status := "Waiting"
		if a.hasRun {
			status = strings.Title(string(a.current.Status))
		}
		detailRow(c, "Status", status)
		detailRow(c, "Store", filepath.Join(".pipeline", "runs", "<run-id>"))
		if definition, ok := a.selectedDefinition(); ok {
			preset, _ := a.selectedPresetValue()
			detailRow(c, "Command", strings.Join(definition.CommandFor(preset, a.dryRun), " "))
		}
	})
}

func (a *app) variantStartButton(c *ui.Context) {
	label := "Start run"
	if a.isRunning() {
		label = "Stop run"
	}
	button := ui.PrimaryButton(c.Key("variant-start-run"), label).Height(38).MinWidth(128).Radius(9).
		Gradient(win7.greenTop, win7.green, 180).TextColor(ui.Hex("#173B17"))
	if a.isRunning() {
		button.Gradient(ui.Hex("#FFE7E7"), win7.red, 180).TextColor(ui.Hex("#5B1717"))
	}
	if button.Clicked() {
		if a.isRunning() {
			a.stopRun()
		} else {
			a.startRun()
		}
	}
}

func (a *app) variantStageTimeline(c *ui.Context, definition pipeline.Definition, large bool) {
	height := float32(112)
	if large {
		height = 150
	}
	a.variantPanel(c, "Pipeline stages", func() {
		ui.Row(c).Height(height).Gap(10).Children(func() {
			for _, status := range a.stageStatuses(definition) {
				a.variantStageTile(c, status)
			}
		})
	})
}

func (a *app) variantStageTile(c *ui.Context, status controller.StageStatus) {
	bgTop, bgLow, text, symbol := win7.white, win7.panelLow, win7.ink, ""
	switch status.Status {
	case controller.StatusSuccess:
		bgTop, bgLow, symbol = win7.greenTop, win7.green, "✓"
	case controller.StatusRunning:
		bgTop, bgLow, symbol = win7.white, ui.Hex("#A7DDF8"), "▶"
	case controller.StatusFailed:
		bgTop, bgLow, text, symbol = ui.Hex("#FFEAEA"), win7.red, ui.Hex("#5B1717"), "×"
	default:
		symbol = ""
	}
	ui.Column(c).Grow(1).Basis(0).MinWidth(0).Padding(10, 8).Gap(4).Radius(9).Border(1, win7.lineSoft).
		Gradient(bgTop, bgLow, 180).Children(func() {
		ui.Row(c).Gap(6).AlignItems(ui.Center).Children(func() {
			ui.Textf(c, "%d", status.Stage.Number).FontSize(13).Bold().TextColor(text)
			if symbol != "" {
				ui.Text(c, symbol).FontSize(13).Bold().TextColor(text)
			}
		})
		ui.Text(c, status.Stage.Name).FontSize(12).Bold().TextColor(text).MaxLines(2)
	})
}

func (a *app) variantStageDetails(c *ui.Context) {
	a.variantPanel(c, "Stage details", func() {
		focused := a.focusStage()
		label, color, symbol := stageDetailState(focused.Status)
		ui.Row(c).Gap(12).Children(func() {
			ui.Box(c).Size(44, 44).Radius(10).Gradient(win7.white, color, 180).Center().Children(func() {
				ui.Text(c, symbol).FontSize(24).Bold().TextColor(win7.white)
			})
			ui.Column(c).Grow(1).Gap(3).Children(func() {
				ui.Textf(c, "Stage %d: %s", focused.Stage.Number, focused.Stage.Name).FontSize(17).Bold().TextColor(win7.ink)
				ui.Text(c, label).FontSize(14).Bold().TextColor(color)
			})
		})
		detailRow(c, "Started", displayTime(focused.Started))
		detailRow(c, "Duration", displayDuration(focused.Started, focused.Ended))
		detailRow(c, "Status", firstNonEmpty(focused.Message, a.finding.Hint))
		detailRow(c, "Log", firstNonEmpty(focused.Stage.LogPattern, "Not available yet"))
	})
}

func (a *app) variantReport(c *ui.Context, definition pipeline.Definition) {
	a.variantPanel(c, "Report summary", func() {
		if a.summary.Missing {
			ui.Text(c, "Report not found yet. Metrics stay as placeholders until summary.md exists.").FontSize(12).TextColor(win7.muted).MaxLines(2)
		}
		ui.Row(c).Gap(10).Children(func() {
			variantMetric(c, "Accuracy", a.summary.Accuracy)
			variantMetric(c, "BA", a.summary.BA)
			variantMetric(c, "MCC", a.summary.MCC)
			variantMetric(c, "AUC", a.summary.AUC)
		})
		detailRow(c, "Source", reportPath(definition))
	})
}

func (a *app) variantArtifacts(c *ui.Context, definition pipeline.Definition) {
	a.variantPanel(c, "Artifacts", func() {
		ui.Row(c).Gap(10).Children(func() {
			artifactChip(c, "summary.md", reportPath(definition))
			artifactChip(c, "stage log", "logs/stage*_*.log")
			artifactChip(c, "run.json", filepath.Join(".pipeline", "runs", "<run-id>", "run.json"))
		})
	})
}

func variantField(c *ui.Context, label string, children func()) {
	ui.Row(c).Gap(12).AlignItems(ui.Center).Children(func() {
		ui.Text(c, label).Width(92).FontSize(12).Bold().TextColor(win7.muted)
		children()
	})
}

func variantMetric(c *ui.Context, label, value string) {
	ui.Column(c).Grow(1).Basis(0).Height(72).Padding(10).Gap(6).Radius(8).Border(1, win7.lineSoft).
		Gradient(win7.white, ui.Hex("#ECF7FD"), 180).Children(func() {
		ui.Text(c, label).FontSize(12).Bold().TextColor(win7.ink)
		ui.Text(c, value).FontSize(12).TextColor(win7.muted).SingleLine()
	})
}

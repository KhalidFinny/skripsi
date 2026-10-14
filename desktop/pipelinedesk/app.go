package main

import (
	"context"
	"os"
	"path/filepath"
	"runtime"
	"time"

	"github.com/egoist/mygo"
	"github.com/egoist/mygo/ui"

	"github.com/SyahrulBhudiF/Skripsi/desktop/pipelinedesk/controller"
	"github.com/SyahrulBhudiF/Skripsi/desktop/pipelinedesk/diagnostics"
	"github.com/SyahrulBhudiF/Skripsi/desktop/pipelinedesk/pipeline"
	"github.com/SyahrulBhudiF/Skripsi/desktop/pipelinedesk/reports"
)

type app struct {
	win   *mygo.Window
	theme *ui.Theme
	root  string

	registry *pipeline.Registry
	loadErr  string

	selectedPipeline string
	selectedPreset   string
	runName          string
	dryRun           bool

	controller controller.Controller
	current    controller.RunState
	hasRun     bool
	runs       []controller.RunState
	summary    reports.Summary
	finding    diagnostics.Finding
}

func newApp() *app {
	root := repoRoot()
	registry, err := pipeline.Load(root)
	a := &app{
		theme:   aquaTheme(),
		root:    root,
		dryRun:  true,
		runName: "pipeline_" + time.Now().Format("2006-01-02_01"),
		summary: reports.Summary{
			Accuracy: "[from report]",
			BA:       "[from report]",
			MCC:      "[from report]",
			AUC:      "[from report]",
		},
	}
	if err != nil {
		a.loadErr = err.Error()
		return a
	}
	a.registry = registry
	if len(registry.Pipelines) > 0 {
		a.selectedPipeline = registry.Pipelines[0].ID
		preset := registry.Pipelines[0].DefaultPreset()
		a.selectedPreset = preset.ID
	}
	a.refreshSummary()
	a.finding = diagnostics.Analyze(nil)
	return a
}

func repoRoot() string {
	if env := os.Getenv("PIPELINE_DESK_ROOT"); env != "" {
		return env
	}
	cwd, err := os.Getwd()
	if err != nil {
		return "."
	}
	for dir := cwd; ; dir = filepath.Dir(dir) {
		if _, err := os.Stat(filepath.Join(dir, "pyproject.toml")); err == nil {
			return dir
		}
		if parent := filepath.Dir(dir); parent == dir {
			break
		}
	}
	return cwd
}

func (a *app) selectedDefinition() (pipeline.Definition, bool) {
	if a.registry == nil {
		return pipeline.Definition{}, false
	}
	return a.registry.Find(a.selectedPipeline)
}

func (a *app) selectedPresetValue() (pipeline.Preset, bool) {
	definition, ok := a.selectedDefinition()
	if !ok {
		return pipeline.Preset{}, false
	}
	preset, ok := definition.Preset(a.selectedPreset)
	if ok {
		return preset, true
	}
	return definition.DefaultPreset(), len(definition.Presets) > 0
}

func (a *app) selectPipeline(id string) {
	a.selectedPipeline = id
	if definition, ok := a.selectedDefinition(); ok {
		a.selectedPreset = definition.DefaultPreset().ID
	}
	a.refreshSummary()
}

func (a *app) selectPreset(id string) {
	a.selectedPreset = id
}

func (a *app) startRun() {
	definition, ok := a.selectedDefinition()
	if !ok {
		return
	}
	preset, ok := a.selectedPresetValue()
	if !ok {
		return
	}
	err := a.controller.Start(context.Background(), controller.Options{
		Root:     a.root,
		Pipeline: definition,
		Preset:   preset,
		DryRun:   a.dryRun,
		Update: func(state controller.RunState) {
			a.update(func() {
				a.acceptRunState(state)
			})
		},
	})
	if err != nil {
		a.finding = diagnostics.Finding{Title: "Could not start run", Hint: err.Error(), Level: "error"}
		return
	}
	if state, ok := a.controller.State(); ok {
		a.acceptRunState(state)
	}
}

func (a *app) stopRun() {
	a.controller.Stop()
	if state, ok := a.controller.State(); ok {
		a.acceptRunState(state)
	}
}

func (a *app) acceptRunState(state controller.RunState) {
	a.current = state
	a.hasRun = true
	a.finding = diagnostics.Analyze(state.LogTail)
	if state.Status == controller.StatusSuccess || state.Status == controller.StatusFailed || state.Status == controller.StatusStopped {
		a.addRun(state)
		a.refreshSummary()
	}
}

func (a *app) addRun(state controller.RunState) {
	for i, run := range a.runs {
		if run.ID == state.ID {
			a.runs[i] = state
			return
		}
	}
	a.runs = append([]controller.RunState{state}, a.runs...)
	if len(a.runs) > 8 {
		a.runs = a.runs[:8]
	}
}

func (a *app) refreshSummary() {
	definition, ok := a.selectedDefinition()
	if !ok || len(definition.Reports) == 0 {
		return
	}
	a.summary = reports.ParseMarkdown(filepath.Join(a.root, definition.Reports[0].Path))
}

func (a *app) update(fn func()) {
	if a.win == nil {
		fn()
		return
	}
	a.win.Update(fn)
}

func (a *app) isRunning() bool {
	return a.hasRun && a.current.Status == controller.StatusRunning
}

func (a *app) stageStatuses(definition pipeline.Definition) []controller.StageStatus {
	if a.hasRun && a.current.PipelineID == definition.ID && len(a.current.Stages) > 0 {
		return a.current.Stages
	}
	statuses := make([]controller.StageStatus, 0, len(definition.Stages))
	for _, stage := range definition.Stages {
		statuses = append(statuses, controller.StageStatus{Stage: stage, Status: controller.StatusQueued})
	}
	return statuses
}

func platformTitleInset() int {
	if runtime.GOOS == "darwin" {
		return 88
	}
	return 18
}

package main

import (
	"image/png"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/egoist/mygo/ui"

	"github.com/SyahrulBhudiF/Skripsi/desktop/pipelinedesk/controller"
	"github.com/SyahrulBhudiF/Skripsi/desktop/pipelinedesk/diagnostics"
	"github.com/SyahrulBhudiF/Skripsi/desktop/pipelinedesk/pipeline"
)

func TestSnapshots(t *testing.T) {
	dir := os.Getenv("PIPELINE_DESK_SNAPSHOTS")
	if dir == "" {
		t.Skip("set PIPELINE_DESK_SNAPSHOTS to a directory to write snapshots")
	}
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}

	a, tt := snapshotApp(t)
	saveSnapshot(t, tt, dir, "pipelinedesk-setup")

	a, tt = snapshotApp(t)
	seedRunningState(a)
	saveSnapshot(t, tt, dir, "pipelinedesk-running")

	a, tt = snapshotApp(t)
	seedFailedState(a)
	saveSnapshot(t, tt, dir, "pipelinedesk-failed-report")
}

func TestVariantSnapshots(t *testing.T) {
	dir := os.Getenv("PIPELINE_DESK_SNAPSHOTS")
	if dir == "" {
		t.Skip("set PIPELINE_DESK_SNAPSHOTS to a directory to write snapshots")
	}
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	for _, tc := range []struct {
		name    string
		variant designVariant
	}{
		{name: "variant-aero-ribbon", variant: variantRibbon},
		{name: "variant-control-panel", variant: variantControlPanel},
		{name: "variant-lab-monitor", variant: variantLabMonitor},
	} {
		a := newApp()
		if a.registry == nil || len(a.registry.Pipelines) == 0 {
			t.Fatalf("registry not loaded: %s", a.loadErr)
		}
		tt := ui.NewTester(func(c *ui.Context) { a.viewVariant(c, tc.variant) }, 1440, 900)
		tt.SetPreferences(ui.Preferences{ReduceMotion: true, TextScale: 1})
		saveSnapshot(t, tt, dir, tc.name)
	}
}

func TestViewInteractions(t *testing.T) {
	a, tt := snapshotApp(t)
	tt.Frame()
	if err := tt.Click("Fold-first v3"); err != nil {
		t.Fatal(err)
	}
	if a.selectedPipeline != "pipeline_v3_presplit" {
		t.Fatalf("selected pipeline = %q", a.selectedPipeline)
	}
	if !tt.HasText("SPLIT") || !tt.HasText("HOLDOUT") {
		t.Fatalf("fold-first stages are not visible: %v", tt.Texts())
	}

	if err := tt.Click("Dry-run first"); err != nil {
		t.Fatal(err)
	}
	if a.dryRun {
		t.Fatal("dry-run checkbox did not toggle")
	}
	if err := tt.Click("Dry-run first"); err != nil {
		t.Fatal(err)
	}
	if !a.dryRun {
		t.Fatal("dry-run checkbox did not toggle back")
	}
}

func snapshotApp(t *testing.T) (*app, *ui.Tester) {
	t.Helper()
	a := newApp()
	if a.registry == nil || len(a.registry.Pipelines) == 0 {
		t.Fatalf("registry not loaded: %s", a.loadErr)
	}
	tt := ui.NewTester(a.view, 1440, 900)
	tt.SetPreferences(ui.Preferences{ReduceMotion: true, TextScale: 1})
	return a, tt
}

func seedRunningState(a *app) {
	definition, _ := a.selectedDefinition()
	preset, _ := a.selectedPresetValue()
	started := time.Now().Add(-3 * time.Minute)
	a.current = controller.RunState{
		ID:           "snapshot-running",
		PipelineID:   definition.ID,
		PipelineName: definition.Name,
		PresetID:     preset.ID,
		PresetName:   preset.Name,
		Status:       controller.StatusRunning,
		Started:      started,
		ActiveStage:  4,
		Stages:       snapshotStages(definition, 4, 0, started),
		LogTail: []string{
			"STAGE 4 cache: building feature cache",
			"loaded fold metadata",
			"writing normalized features",
		},
	}
	a.hasRun = true
	a.finding = diagnostics.Analyze(a.current.LogTail)
}

func seedFailedState(a *app) {
	definition, _ := a.selectedDefinition()
	preset, _ := a.selectedPresetValue()
	started := time.Now().Add(-17 * time.Minute)
	a.current = controller.RunState{
		ID:             "snapshot-failed",
		PipelineID:     definition.ID,
		PipelineName:   definition.Name,
		PresetID:       preset.ID,
		PresetName:     preset.Name,
		Status:         controller.StatusFailed,
		Started:        started,
		Ended:          started.Add(12 * time.Minute),
		ActiveStage:    6,
		Stages:         snapshotStages(definition, 6, 6, started),
		FailureMessage: "Validation gate failed",
		LogTail: []string{
			"STAGE 6 gate: validation threshold below target",
			"balanced accuracy below configured gate",
			"see logs/stage6_loso_snapshot.log",
		},
	}
	a.hasRun = true
	a.finding = diagnostics.Analyze(a.current.LogTail)
	a.runs = []controller.RunState{a.current}
}

func snapshotStages(definition pipeline.Definition, running, failed int, started time.Time) []controller.StageStatus {
	stages := make([]controller.StageStatus, 0, len(definition.Stages))
	for _, stage := range definition.Stages {
		status := controller.StatusQueued
		stageStarted := time.Time{}
		stageEnded := time.Time{}
		message := ""
		switch {
		case failed > 0 && stage.Number < failed:
			status = controller.StatusSuccess
			stageStarted = started.Add(time.Duration(stage.Number) * time.Minute)
			stageEnded = stageStarted.Add(40 * time.Second)
		case failed > 0 && stage.Number == failed:
			status = controller.StatusFailed
			stageStarted = started.Add(time.Duration(stage.Number) * time.Minute)
			stageEnded = stageStarted.Add(40 * time.Second)
			message = "Validation gate failed"
		case running > 0 && stage.Number < running:
			status = controller.StatusSuccess
			stageStarted = started.Add(time.Duration(stage.Number) * time.Minute)
			stageEnded = stageStarted.Add(35 * time.Second)
		case running > 0 && stage.Number == running:
			status = controller.StatusRunning
			stageStarted = started.Add(time.Duration(stage.Number) * time.Minute)
		}
		stages = append(stages, controller.StageStatus{Stage: stage, Status: status, Started: stageStarted, Ended: stageEnded, Message: message})
	}
	return stages
}

func saveSnapshot(t *testing.T, tt *ui.Tester, dir, name string) {
	t.Helper()
	tt.Frame()
	file, err := os.Create(filepath.Join(dir, name+".png"))
	if err != nil {
		t.Fatal(err)
	}
	defer file.Close()
	if err := png.Encode(file, tt.Image()); err != nil {
		t.Fatal(err)
	}
}

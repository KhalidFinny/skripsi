package controller

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
	"time"

	"github.com/SyahrulBhudiF/Skripsi/desktop/pipelinedesk/pipeline"
)

type Status string

const (
	StatusQueued  Status = "queued"
	StatusRunning Status = "running"
	StatusSuccess Status = "success"
	StatusFailed  Status = "failed"
	StatusStopped Status = "stopped"
)

type StageStatus struct {
	Stage   pipeline.Stage `json:"stage"`
	Status  Status         `json:"status"`
	Started time.Time      `json:"started,omitempty"`
	Ended   time.Time      `json:"ended,omitempty"`
	Message string         `json:"message,omitempty"`
}

type RunState struct {
	ID             string            `json:"id"`
	PipelineID     string            `json:"pipeline_id"`
	PipelineName   string            `json:"pipeline_name"`
	PresetID       string            `json:"preset_id"`
	PresetName     string            `json:"preset_name"`
	Command        []string          `json:"command"`
	Env            map[string]string `json:"env"`
	Root           string            `json:"root"`
	Status         Status            `json:"status"`
	Started        time.Time         `json:"started"`
	Ended          time.Time         `json:"ended,omitempty"`
	ExitCode       int               `json:"exit_code,omitempty"`
	ActiveStage    int               `json:"active_stage"`
	Stages         []StageStatus     `json:"stages"`
	LogTail        []string          `json:"log_tail"`
	StoreDir       string            `json:"store_dir"`
	SummaryPath    string            `json:"summary_path,omitempty"`
	FailureMessage string            `json:"failure_message,omitempty"`
}

type Event struct {
	Time    time.Time `json:"time"`
	Type    string    `json:"type"`
	Stage   int       `json:"stage,omitempty"`
	Message string    `json:"message,omitempty"`
}

type Controller struct {
	mu     sync.Mutex
	state  *RunState
	cancel context.CancelFunc
}

type Options struct {
	Root     string
	Pipeline pipeline.Definition
	Preset   pipeline.Preset
	DryRun   bool
	Update   func(RunState)
}

var stageRE = regexp.MustCompile(`STAGE[[:space:]]+([0-9]+)`) // matches pipeline banners and failures.

func (c *Controller) State() (RunState, bool) {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.state == nil {
		return RunState{}, false
	}
	return cloneState(*c.state), true
}

func (c *Controller) Start(ctx context.Context, opts Options) error {
	c.mu.Lock()
	if c.state != nil && c.state.Status == StatusRunning {
		c.mu.Unlock()
		return fmt.Errorf("a run is already active")
	}
	runCtx, cancel := context.WithCancel(ctx)
	c.cancel = cancel
	state, err := newRunState(opts)
	if err != nil {
		c.mu.Unlock()
		return err
	}
	c.state = &state
	c.mu.Unlock()

	go c.run(runCtx, opts)
	return nil
}

func (c *Controller) Stop() {
	c.mu.Lock()
	cancel := c.cancel
	if c.state != nil && c.state.Status == StatusRunning {
		c.state.Status = StatusStopped
		c.state.Ended = time.Now()
	}
	state := c.state
	c.mu.Unlock()
	if cancel != nil {
		cancel()
	}
	if state != nil {
		_ = writeJSON(filepath.Join(state.StoreDir, "run.json"), state)
	}
}

func (c *Controller) run(ctx context.Context, opts Options) {
	state, _ := c.State()
	_ = os.MkdirAll(filepath.Join(state.StoreDir, "stages"), 0o755)
	_ = os.MkdirAll(filepath.Join(state.StoreDir, "reports"), 0o755)
	_ = writeJSON(filepath.Join(state.StoreDir, "run.json"), state)
	events, _ := os.OpenFile(filepath.Join(state.StoreDir, "events.jsonl"), os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o644)
	if events != nil {
		defer events.Close()
		writeEvent(events, Event{Time: time.Now(), Type: "run_started", Message: strings.Join(state.Command, " ")})
	}

	cmd := exec.CommandContext(ctx, state.Command[0], state.Command[1:]...)
	cmd.Dir = opts.Root
	cmd.Env = mergedEnv(opts.Preset.Env)
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		c.finishFailure(events, fmt.Sprintf("stdout pipe: %v", err), -1, opts.Update)
		return
	}
	stderr, err := cmd.StderrPipe()
	if err != nil {
		c.finishFailure(events, fmt.Sprintf("stderr pipe: %v", err), -1, opts.Update)
		return
	}
	if err := cmd.Start(); err != nil {
		c.finishFailure(events, fmt.Sprintf("start command: %v", err), -1, opts.Update)
		return
	}

	allLog, _ := os.Create(filepath.Join(state.StoreDir, "stages", "run.log"))
	if allLog != nil {
		defer allLog.Close()
	}
	var wg sync.WaitGroup
	wg.Add(2)
	go c.scanOutput(&wg, stdout, allLog, events, opts.Update)
	go c.scanOutput(&wg, stderr, allLog, events, opts.Update)
	wg.Wait()

	err = cmd.Wait()
	if ctx.Err() != nil {
		c.finishStopped(events, opts.Update)
		return
	}
	if err != nil {
		exitCode := -1
		if cmd.ProcessState != nil {
			exitCode = cmd.ProcessState.ExitCode()
		}
		c.finishFailure(events, err.Error(), exitCode, opts.Update)
		return
	}
	c.finishSuccess(events, opts.Update)
}

func (c *Controller) scanOutput(wg *sync.WaitGroup, reader io.Reader, copyTo io.Writer, events io.Writer, update func(RunState)) {
	defer wg.Done()
	scanner := bufio.NewScanner(reader)
	for scanner.Scan() {
		line := scanner.Text()
		if copyTo != nil {
			_, _ = fmt.Fprintln(copyTo, line)
		}
		c.recordLine(line, events, update)
	}
}

func (c *Controller) recordLine(line string, events io.Writer, update func(RunState)) {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.state == nil {
		return
	}
	if match := stageRE.FindStringSubmatch(line); len(match) == 2 {
		var stage int
		_, _ = fmt.Sscanf(match[1], "%d", &stage)
		if stage != 0 || strings.Contains(line, "STAGE 0") {
			c.state.ActiveStage = stage
			for i := range c.state.Stages {
				if c.state.Stages[i].Status == StatusRunning && c.state.Stages[i].Stage.Number != stage {
					c.state.Stages[i].Status = StatusSuccess
					c.state.Stages[i].Ended = time.Now()
				}
				if c.state.Stages[i].Stage.Number == stage && c.state.Stages[i].Status == StatusQueued {
					c.state.Stages[i].Status = StatusRunning
					c.state.Stages[i].Started = time.Now()
				}
			}
			writeEvent(events, Event{Time: time.Now(), Type: "stage_seen", Stage: stage, Message: line})
		}
	}
	c.state.LogTail = append(c.state.LogTail, line)
	if len(c.state.LogTail) > 80 {
		c.state.LogTail = c.state.LogTail[len(c.state.LogTail)-80:]
	}
	writeEvent(events, Event{Time: time.Now(), Type: "log", Stage: c.state.ActiveStage, Message: line})
	state := cloneState(*c.state)
	go updateState(update, state)
}

func (c *Controller) finishSuccess(events io.Writer, update func(RunState)) {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.state == nil {
		return
	}
	now := time.Now()
	c.state.Status = StatusSuccess
	c.state.Ended = now
	for i := range c.state.Stages {
		if c.state.Stages[i].Status == StatusRunning || c.state.Stages[i].Status == StatusQueued {
			c.state.Stages[i].Status = StatusSuccess
			c.state.Stages[i].Ended = now
		}
	}
	writeEvent(events, Event{Time: now, Type: "run_success"})
	_ = writeJSON(filepath.Join(c.state.StoreDir, "run.json"), c.state)
	updateState(update, cloneState(*c.state))
}

func (c *Controller) finishStopped(events io.Writer, update func(RunState)) {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.state == nil {
		return
	}
	now := time.Now()
	c.state.Status = StatusStopped
	c.state.Ended = now
	writeEvent(events, Event{Time: now, Type: "run_stopped"})
	_ = writeJSON(filepath.Join(c.state.StoreDir, "run.json"), c.state)
	updateState(update, cloneState(*c.state))
}

func (c *Controller) finishFailure(events io.Writer, message string, exitCode int, update func(RunState)) {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.state == nil {
		return
	}
	now := time.Now()
	c.state.Status = StatusFailed
	c.state.Ended = now
	c.state.ExitCode = exitCode
	c.state.FailureMessage = message
	for i := range c.state.Stages {
		if c.state.Stages[i].Stage.Number == c.state.ActiveStage {
			c.state.Stages[i].Status = StatusFailed
			c.state.Stages[i].Ended = now
			c.state.Stages[i].Message = message
		} else if c.state.Stages[i].Status == StatusRunning {
			c.state.Stages[i].Status = StatusFailed
			c.state.Stages[i].Ended = now
		}
	}
	writeEvent(events, Event{Time: now, Type: "run_failed", Stage: c.state.ActiveStage, Message: message})
	_ = writeJSON(filepath.Join(c.state.StoreDir, "run.json"), c.state)
	updateState(update, cloneState(*c.state))
}

func newRunState(opts Options) (RunState, error) {
	if opts.Root == "" {
		return RunState{}, fmt.Errorf("root is required")
	}
	if opts.Pipeline.ID == "" {
		return RunState{}, fmt.Errorf("pipeline is required")
	}
	preset := opts.Preset
	if preset.ID == "" {
		preset = opts.Pipeline.DefaultPreset()
	}
	cmd := opts.Pipeline.CommandFor(preset, opts.DryRun)
	if len(cmd) == 0 {
		return RunState{}, fmt.Errorf("empty command")
	}
	runID := time.Now().Format("2006-01-02_150405") + "_" + opts.Pipeline.ID + "_" + preset.ID
	state := RunState{
		ID:           runID,
		PipelineID:   opts.Pipeline.ID,
		PipelineName: opts.Pipeline.Name,
		PresetID:     preset.ID,
		PresetName:   preset.Name,
		Command:      cmd,
		Env:          preset.Env,
		Root:         opts.Root,
		Status:       StatusRunning,
		Started:      time.Now(),
		ActiveStage:  firstStage(opts.Pipeline),
		StoreDir:     filepath.Join(opts.Root, ".pipeline", "runs", runID),
	}
	for _, stage := range opts.Pipeline.Stages {
		state.Stages = append(state.Stages, StageStatus{Stage: stage, Status: StatusQueued})
	}
	return state, nil
}

func firstStage(def pipeline.Definition) int {
	if len(def.Stages) == 0 {
		return 0
	}
	return def.Stages[0].Number
}

func mergedEnv(extra map[string]string) []string {
	env := os.Environ()
	for key, value := range extra {
		env = append(env, key+"="+value)
	}
	return env
}

func writeEvent(w io.Writer, event Event) {
	if w == nil {
		return
	}
	data, err := json.Marshal(event)
	if err == nil {
		_, _ = fmt.Fprintln(w, string(data))
	}
}

func writeJSON(path string, value any) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	data, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, data, 0o644)
}

func cloneState(state RunState) RunState {
	state.Command = append([]string(nil), state.Command...)
	state.LogTail = append([]string(nil), state.LogTail...)
	state.Stages = append([]StageStatus(nil), state.Stages...)
	state.Env = map[string]string{}
	for key, value := range state.Env {
		state.Env[key] = value
	}
	return state
}

func updateState(update func(RunState), state RunState) {
	if update != nil {
		update(state)
	}
}

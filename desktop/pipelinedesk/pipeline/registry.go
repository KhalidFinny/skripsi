package pipeline

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"slices"
	"strings"
)

type Registry struct {
	Pipelines []Definition `json:"pipelines"`
}

type Definition struct {
	ID          string     `json:"id"`
	Name        string     `json:"name"`
	Description string     `json:"description"`
	Command     []string   `json:"command"`
	WorkingDir  string     `json:"working_dir"`
	Supports    Supports   `json:"supports"`
	Stages      []Stage    `json:"stages"`
	Fields      []Field    `json:"fields"`
	Presets     []Preset   `json:"presets"`
	Reports     []Artifact `json:"reports"`
	Artifacts   []Artifact `json:"artifacts"`
}

type Supports struct {
	DryRun   bool `json:"dry_run"`
	Force    bool `json:"force"`
	Fresh    bool `json:"fresh"`
	Resume   bool `json:"resume"`
	Presplit bool `json:"presplit"`
}

type Stage struct {
	Number      int    `json:"number"`
	ID          string `json:"id"`
	Name        string `json:"name"`
	Description string `json:"description"`
	LogPattern  string `json:"log_pattern"`
	Optional    bool   `json:"optional"`
}

type Field struct {
	Key         string   `json:"key"`
	Label       string   `json:"label"`
	Kind        string   `json:"kind"`
	Default     string   `json:"default"`
	Options     []string `json:"options"`
	Description string   `json:"description"`
}

type Preset struct {
	ID          string            `json:"id"`
	Name        string            `json:"name"`
	Description string            `json:"description"`
	Args        []string          `json:"args"`
	Env         map[string]string `json:"env"`
	Dangerous   bool              `json:"dangerous"`
}

type Artifact struct {
	Label string `json:"label"`
	Path  string `json:"path"`
	Kind  string `json:"kind"`
}

func Load(root string) (*Registry, error) {
	path := filepath.Join(root, "pipeline", "registry.json")
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var registry Registry
	if err := json.Unmarshal(data, &registry); err != nil {
		return nil, err
	}
	if err := registry.Validate(root); err != nil {
		return nil, err
	}
	return &registry, nil
}

func (r *Registry) Validate(root string) error {
	if r == nil || len(r.Pipelines) == 0 {
		return errors.New("pipeline registry is empty")
	}
	ids := map[string]bool{}
	for _, definition := range r.Pipelines {
		if strings.TrimSpace(definition.ID) == "" {
			return errors.New("pipeline id is required")
		}
		if ids[definition.ID] {
			return fmt.Errorf("duplicate pipeline id %q", definition.ID)
		}
		ids[definition.ID] = true
		if strings.TrimSpace(definition.Name) == "" {
			return fmt.Errorf("pipeline %q has no name", definition.ID)
		}
		if len(definition.Command) == 0 {
			return fmt.Errorf("pipeline %q has no command", definition.ID)
		}
		cmd := definition.Command[0]
		if !filepath.IsAbs(cmd) && strings.Contains(cmd, "/") {
			if _, err := os.Stat(filepath.Join(root, cmd)); err != nil {
				return fmt.Errorf("pipeline %q command %q: %w", definition.ID, cmd, err)
			}
		}
		if len(definition.Stages) == 0 {
			return fmt.Errorf("pipeline %q has no stages", definition.ID)
		}
		stageIDs := map[string]bool{}
		for _, stage := range definition.Stages {
			if strings.TrimSpace(stage.ID) == "" || strings.TrimSpace(stage.Name) == "" {
				return fmt.Errorf("pipeline %q has incomplete stage %d", definition.ID, stage.Number)
			}
			if stageIDs[stage.ID] {
				return fmt.Errorf("pipeline %q has duplicate stage id %q", definition.ID, stage.ID)
			}
			stageIDs[stage.ID] = true
		}
	}
	return nil
}

func (r *Registry) Find(id string) (Definition, bool) {
	if r == nil {
		return Definition{}, false
	}
	for _, pipeline := range r.Pipelines {
		if pipeline.ID == id {
			return pipeline, true
		}
	}
	return Definition{}, false
}

func (d Definition) Preset(id string) (Preset, bool) {
	for _, preset := range d.Presets {
		if preset.ID == id {
			return preset, true
		}
	}
	return Preset{}, false
}

func (d Definition) DefaultPreset() Preset {
	if len(d.Presets) == 0 {
		return Preset{}
	}
	return d.Presets[0]
}

func (d Definition) StageByNumber(number int) (Stage, bool) {
	for _, stage := range d.Stages {
		if stage.Number == number {
			return stage, true
		}
	}
	return Stage{}, false
}

func (d Definition) CommandFor(preset Preset, dryRun bool) []string {
	cmd := slices.Clone(d.Command)
	cmd = append(cmd, preset.Args...)
	if dryRun && d.Supports.DryRun && !slices.Contains(cmd, "--dry-run") {
		cmd = append(cmd, "--dry-run")
	}
	return cmd
}

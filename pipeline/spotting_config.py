"""Konfigurasi spotting.

Definisi ROI/target_size/block_size diambil dari `features/roi_config.py`
(satu-satunya sumber kebenaran) supaya sinyal yang dipakai spotting tidak
menyimpang dari ROI yang dipakai ekstraksi fitur.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from features.roi_config import BLOCK_SIZE, REGIONS, TARGET_SIZE


@dataclass(slots=True)
class SpottingConfig:
    dataset_root: Path
    output_root: Path
    predictor_path: Path
    video_extensions: set[str]
    overwrite: bool = False
    block_size: int = BLOCK_SIZE
    padding_x: int = 6
    padding_y: int = 8
    min_phase_duration: int = 2
    top_k_apex: int = 5
    regions: dict[str, list[int]] | None = None
    target_size: dict[str, tuple[int, int]] | None = None
    distance_threshold: int = 1
    prominence_threshold: float = 0.005
    cutoff_ratio: float = 0.3

    def __post_init__(self) -> None:
        if self.regions is None:
            self.regions = dict(REGIONS)
        if self.target_size is None:
            self.target_size = dict(TARGET_SIZE)

    @property
    def output_dataset_root(self) -> Path:
        return self.output_root / "dataset"

    @property
    def metadata_path(self) -> Path:
        return self.output_root / "metadata.xlsx"


def run_spotting(_config: SpottingConfig) -> pd.DataFrame:
    raise NotImplementedError("Run logic lives in pipeline/stages/stage_1_spotting.py")

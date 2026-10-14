"""Konfigurasi ekstraksi fitur perbandingan.

Definisi ROI/target_size/block_size TIDAK lagi didefinisikan di sini: satu-satunya
sumber kebenaran ada di `features/roi_config.py` supaya tidak menyimpang
dari yang dipakai spotting dan ekstraksi pipeline utama.
"""

from dataclasses import dataclass, field
from pathlib import Path

from features.roi_config import (
    BLOCK_SIZE,
    PADDING_X,
    PADDING_Y,
    REGIONS,
    TARGET_SIZE,
)


@dataclass(slots=True)
class ComparisonConfig:
    predictor_path: Path = Path("models/shape_predictor_68_face_landmarks.dat")
    output_root: Path = Path("comparasion/output_casme2")
    regions: dict[str, list[int]] = field(default_factory=lambda: dict(REGIONS))
    target_size: dict[str, tuple[int, int]] = field(default_factory=lambda: dict(TARGET_SIZE))
    padding_x: int = PADDING_X
    padding_y: int = PADDING_Y
    block_size: int = BLOCK_SIZE
    feature_method: str = "poc_abs"
    include_quadrant_counts: bool = True

    @property
    def roi_output_dir(self) -> Path:
        return self.output_root / "roi"

    @property
    def feature_output_dir(self) -> Path:
        return self.output_root / "features"

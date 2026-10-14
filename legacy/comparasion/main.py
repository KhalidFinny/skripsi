from pathlib import Path

from shared.config import ComparisonConfig
from legacy.comparasion.dataset import discover_clips
from legacy.comparasion.pipeline import run_dataset, run_dataset_parallel


def run_all(dataset_root: str | Path, n_proc: int | None = None) -> tuple[int, list[tuple[str, str]]]:
    config = ComparisonConfig()
    clips = discover_clips(dataset_root)
    if n_proc:
        return run_dataset_parallel(clips, config, n_proc=n_proc)
    return run_dataset(clips, config)

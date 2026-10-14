#!/usr/bin/env python
"""
switch_spotting_config.py - ganti konfigurasi spotting di notebook
process_all_datasets.ipynb tanpa edit manual.

Pemakaian:
  uv run python scripts/switch_spotting_config.py --mode datatest --abs 1
  uv run python scripts/switch_spotting_config.py --mode anxiety --abs 0
  uv run python scripts/switch_spotting_config.py --mode datatest --abs 1 --print-only

--mode   : datatest (default) | anxiety
--abs    : 1 = POC-ABS (frame-0 baseline), 0 = frame berurutan (asli)
--print-only : hanya cetak config yang akan dipakai, tanpa menulis file
"""
import argparse
import json
import re
import sys
from pathlib import Path

NOTEBOOK = Path("notebooks/process_all_datasets.ipynb")

MODE_CONFIG = {
    "datatest": {
        "dataset_root": "PROJECT_ROOT / 'dataset' / 'datatest' / 'labeled'",
        "output_root": "PROJECT_ROOT / 'output' / 'apex' / 'datatest'",
        "video_extensions": "{'.webm'}",
    },
    "anxiety": {
        "dataset_root": "PROJECT_ROOT / 'dataset' / 'anxiety_raw'",
        "output_root": "PROJECT_ROOT / 'output' / 'apex'",
        "video_extensions": "{'.avi'}",
    },
}


def patch_line(source: str, pattern: str, replacement: str) -> str:
    new_source, n = re.subn(pattern, replacement, source, count=1)
    if n != 1:
        raise SystemExit(f"GAGAL: pola tidak ditemukan di notebook: {pattern}")
    return new_source


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=list(MODE_CONFIG), default="datatest")
    parser.add_argument("--abs", type=int, choices=[0, 1], default=1)
    parser.add_argument("--print-only", action="store_true")
    args = parser.parse_args()

    cfg = MODE_CONFIG[args.mode]
    abs_line = f"USE_ABS_BASELINE = {bool(args.abs)}  # True = POC-ABS (frame-0 baseline); False = frame berurutan (asli)"

    print(f"Mode             : {args.mode}")
    print(f"dataset_root     : {cfg['dataset_root']}")
    print(f"output_root      : {cfg['output_root']}")
    print(f"video_extensions : {cfg['video_extensions']}")
    print(f"USE_ABS_BASELINE : {bool(args.abs)}")

    if args.print_only:
        return

    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    src = "".join(nb["cells"][2]["source"])

    src = patch_line(src, r"dataset_root=.*", f"dataset_root={cfg['dataset_root']},")
    src = patch_line(src, r"output_root=.*", f"output_root={cfg['output_root']},")
    src = patch_line(src, r"video_extensions=.*", f"video_extensions={cfg['video_extensions']},")
    if "USE_ABS_BASELINE" in src:
        src = patch_line(src, r"USE_ABS_BASELINE = (True|False).*", abs_line)
    else:
        anchor = "max_workers = min(4, os.cpu_count() or 1)"
        assert anchor in src, "anchor max_workers tidak ditemukan"
        src = src.replace(anchor, abs_line + "\n" + anchor, 1)

    nb["cells"][2]["source"] = src.splitlines(keepends=True)
    NOTEBOOK.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nConfig notebook diperbarui: {NOTEBOOK}")


if __name__ == "__main__":
    sys.exit(main())

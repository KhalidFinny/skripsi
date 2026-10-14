#!/usr/bin/env python
"""Simpan acuan netral per sample (neutral.png) dari video mentah.

Kenapa perlu:
  Baseline POC-ABS yang dipakai sejak awal adalah **frame onset klip event**.
  Klip event disimpan mulai onset (`save_event_clip_frames`), jadi "frame 1"
  klip = frame yang ototnya sudah mulai berkontraksi, bukan wajah netral.
  Literatur (SAMM/Adaptive Baseline Threshold; StressGAT Differential AU)
  memakai baseline netral per orang.

Kenapa script terpisah, bukan spotting ulang:
  Klip event + metadata sudah ada dan konsisten (22 Sep). Menjalankan ulang
  seluruh spotting hanya untuk mendapat neutral.png itu boros (560 video,
  jam-an) dan berisiko mengubah event set. Script ini hanya membaca 10 frame
  pertama tiap video mentah dan menulis satu PNG per sample.

Output: <dataset_root>/<phase>/<condition>/<participant>/<question>/<sample>/neutral.png
  (di sebelah direktori event_*/ , tempat extract_features_poc_abs.py
   mencarinya lewat --baseline neutral)

Contoh:
    .venv/bin/python scripts/save_neutral_references.py
    .venv/bin/python scripts/save_neutral_references.py --force --workers 4
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import cv2
import numpy as np
from tqdm import tqdm

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RAW_ROOT = Path('/mnt/FINNY/dataset/anxiety_raw')
DEFAULT_DATASET_ROOT = ROOT / 'output/apex/dataset'
VIDEO_EXTENSIONS = {'.avi', '.webm'}


def natural_sort_key(value: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', str(value))]


def find_raw_video(raw_root: Path, rel_sample: Path) -> Path | None:
    """Cari video mentah untuk satu sample.

    rel_sample = phase/cond/participant/question/<sample>; video mentahnya ada di
    <raw_root>/phase/cond/participant/question/<sample>.avi (nama file = nama sample).
    """
    sample_dir = raw_root / rel_sample.parent
    if not sample_dir.is_dir():
        return None
    stem = rel_sample.name
    candidates = sorted(
        [p for p in sample_dir.iterdir()
         if p.is_file() and p.stem == stem and p.suffix.lower() in VIDEO_EXTENSIONS],
        key=lambda p: natural_sort_key(p.name),
    )
    if not candidates:
        return None
    # Utamakan .avi (yang dipakai pipeline spotting), kalau tidak ada pakai yang pertama.
    avi = [p for p in candidates if p.suffix.lower() == '.avi']
    return (avi or candidates)[0]


def read_neutral(video_path: Path, n_frames: int) -> np.ndarray | None:
    cap = cv2.VideoCapture(str(video_path))
    frames = []
    try:
        for _ in range(n_frames):
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
    finally:
        cap.release()
    if not frames:
        return None
    return np.median(np.stack(frames).astype(np.float32), axis=0).astype(np.uint8)


def process_sample(rel_sample: str, raw_root: str, dataset_root: str, n_frames: int, force: bool) -> tuple[str, str]:
    rel = Path(rel_sample)
    out_path = Path(dataset_root) / rel / 'neutral.png'
    if out_path.exists() and not force:
        return rel_sample, 'skip'
    video = find_raw_video(Path(raw_root), rel)
    if video is None:
        return rel_sample, 'no-video'
    neutral = read_neutral(video, n_frames)
    if neutral is None:
        return rel_sample, 'no-frames'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(out_path), neutral):
        return rel_sample, 'write-failed'
    return rel_sample, 'ok'


def discover_samples(dataset_root: Path) -> list[str]:
    """Sample = direktori yang memuat minimal satu subdirektori event_*."""
    samples = []
    for event_dir in dataset_root.rglob('event_*'):
        if not event_dir.is_dir():
            continue
        rel = event_dir.parent.relative_to(dataset_root)
        samples.append(str(rel))
    return sorted(set(samples), key=natural_sort_key)


def main() -> None:
    parser = argparse.ArgumentParser(description='Simpan neutral.png per sample dari video mentah.')
    parser.add_argument('--raw-root', type=Path,
                        default=Path(os.environ.get('SPOT_DATASET_ROOT', str(DEFAULT_RAW_ROOT))),
                        help=f'root dataset mentah. Default: {DEFAULT_RAW_ROOT}')
    parser.add_argument('--dataset-root', type=Path, default=DEFAULT_DATASET_ROOT,
                        help=f'root klip event. Default: {DEFAULT_DATASET_ROOT}')
    parser.add_argument('--frames', type=int, default=10,
                        help='jumlah frame awal video yang di-median (default 10).')
    parser.add_argument('--workers', type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument('--force', action='store_true', help='tulis ulang walau neutral.png ada')
    args = parser.parse_args()

    if not args.raw_root.exists():
        raise SystemExit(f'Dataset mentah tidak ditemukan: {args.raw_root}')
    if not args.dataset_root.exists():
        raise SystemExit(f'Dataset klip tidak ditemukan: {args.dataset_root}')

    samples = discover_samples(args.dataset_root)
    print(f'Raw    : {args.raw_root}')
    print(f'Klip   : {args.dataset_root}')
    print(f'Sample : {len(samples)} | workers: {args.workers} | frames: {args.frames}')
    if not samples:
        raise SystemExit('Tidak ada sample (direktori event_*) ditemukan.')

    counts: dict[str, int] = {}
    missing: list[str] = []
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(process_sample, s, str(args.raw_root), str(args.dataset_root),
                            args.frames, args.force)
            for s in samples
        ]
        for future in tqdm(as_completed(futures), total=len(futures), desc='neutral', unit='sample'):
            rel, status = future.result()
            counts[status] = counts.get(status, 0) + 1
            if status in {'no-video', 'no-frames'}:
                missing.append(f'{rel} ({status})')

    print(f'Hasil: {counts}')
    if missing:
        print(f'PERINGATAN: {len(missing)} sample tanpa acuan netral (akan fallback ke onset):')
        for item in missing[:10]:
            print(f'  {item}')
        if len(missing) > 10:
            print(f'  ... dan {len(missing) - 10} lagi')
        Path(args.dataset_root.parent / 'neutral_missing.txt').write_text('\n'.join(missing) + '\n')
        print(f'Daftar lengkap: {args.dataset_root.parent / "neutral_missing.txt"}')


if __name__ == '__main__':
    main()

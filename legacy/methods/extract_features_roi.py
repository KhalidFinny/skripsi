#!/usr/bin/env python
# coding: utf-8

# # Export apex POC-ABS flatten ordered (datatest 15/17)
# 
# Dynamic recursive event export with memory-friendly multiprocessing.
# 

# In[1]:


import gc
import os
import re
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path

from tqdm import tqdm

import cv2
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

print(f'Project root: {ROOT}')


# In[2]:


from shared.config import ComparisonConfig
from shared.roi import ROIExtractor
from features.poc import POC
from features.quadran import Quadran
from features.roi_config import REGIONS, TARGET_SIZE
from features.vektor import Vektor


# In[3]:


DATASET_SPECS = [
    {'name': '15_04_2026', 'dataset_root': (ROOT / 'output/apex/datatest/dataset/15_04_2026').resolve()},
    {'name': '17_04_2026', 'dataset_root': (ROOT / 'output/apex/datatest/dataset/17_04_2026').resolve()},
]
FEATURE_ROOT = (ROOT / 'output/apex/datatest/features').resolve()
ANNOTATIONS_PATH = Path(os.environ.get('SPOT_ANNOTATIONS_PATH', '/mnt/FINNY/dataset/datatest/annotations.xlsx')).resolve()
TEMP_ROOT = FEATURE_ROOT / '_tmp_batches'

BASE_CONFIG = ComparisonConfig(
    predictor_path=ROOT / 'models/shape_predictor_68_face_landmarks.dat',
    output_root=ROOT / 'output/apex/tmp_compare',
    regions=REGIONS,
    target_size=TARGET_SIZE,
)

MAX_WORKERS = min(4, os.cpu_count() or 1)
FLUSH_ROWS = 50_000
OVERWRITE = True

print(f'Feature root: {FEATURE_ROOT}')
print(f'Annotations:  {ANNOTATIONS_PATH}')
print(f'Max workers:  {MAX_WORKERS}')
print(f'Regions:      {list(BASE_CONFIG.regions)}')



# In[4]:


for spec in DATASET_SPECS:
    if not spec['dataset_root'].exists():
        raise FileNotFoundError(f"Dataset root not found: {spec['dataset_root']}")
if not BASE_CONFIG.predictor_path.exists():
    raise FileNotFoundError(f'Predictor not found: {BASE_CONFIG.predictor_path}')
FEATURE_ROOT.mkdir(parents=True, exist_ok=True)
TEMP_ROOT.mkdir(parents=True, exist_ok=True)


# In[5]:


def normalize_subject_id(value: str) -> str:
    return re.sub(r'_+', '_', str(value).strip())


def load_annotation_lookup(path: Path) -> dict[str, dict]:
    if not path.exists():
        print(f'Annotation file not found, phase will be unknown: {path}')
        return {}
    lookup = {}
    sheets = pd.read_excel(path, sheet_name=None)
    for sheet_name, df in sheets.items():
        if 'subject_id' not in df.columns:
            continue
        for row in df.itertuples(index=False):
            subject_id = str(getattr(row, 'subject_id'))
            item = {
                'annotation_sheet': sheet_name,
                'stage': getattr(row, 'stage', None),
                'score': getattr(row, 'score', None),
                'annotation_label': getattr(row, 'label', None),
            }
            lookup[subject_id] = item
            lookup.setdefault(normalize_subject_id(subject_id), item)
    return lookup

annotation_lookup = load_annotation_lookup(ANNOTATIONS_PATH)
print(f'Annotation subjects: {len(annotation_lookup)}')


# In[6]:


@dataclass(slots=True)
class EventClip:
    date: str
    phase: str
    condition: str
    label: str
    participant_raw: str
    participant_key: str
    question: str
    question_no: int
    sample_name: str
    clip_name: str
    event_clip: str
    event_no: int
    event_dir: str
    clip_path: str
    score: float | None = None
    annotation_sheet: str | None = None

    @property
    def sample_id(self) -> str:
        return f'{self.date}__{self.label}__{self.participant_raw}__{self.question}__{self.sample_name}__event_{self.event_no:03d}'


def natural_sort_key(value: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', str(value))]


def parse_question_no(question: str) -> int:
    match = re.search(r'(\d+)', str(question))
    return int(match.group(1)) if match else 0


def normalize_participant_key(name: str) -> str:
    return normalize_subject_id(re.sub(r'_[0-9]+$', '', str(name)))


def map_label(value: str) -> str:
    mapping = {
        'anxiety': 'anxiety_tinggi',
        'tidak': 'anxiety_rendah',
        'anxiety_tinggi': 'anxiety_tinggi',
        'anxiety_rendah': 'anxiety_rendah',
    }
    return mapping.get(str(value), str(value))


def event_no_from_name(name: str) -> int:
    match = re.search(r'event_(\d+)', name)
    return int(match.group(1)) if match else 0


def relative_to_root(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def parse_event_dir(event_dir: Path, dataset_root: Path, dataset_name: str) -> EventClip:
    rel_parts = event_dir.relative_to(dataset_root).parts
    if len(rel_parts) < 4:
        raise ValueError(f'Path too short: {event_dir}')

    question_idx = next((i for i, part in enumerate(rel_parts) if re.fullmatch(r'q\d+', part.lower())), None)
    if question_idx is None or question_idx == 0 or question_idx + 1 >= len(rel_parts):
        raise ValueError(f'Cannot parse question/sample from: {event_dir}')

    question = rel_parts[question_idx]
    participant_raw = rel_parts[question_idx - 1]
    sample_name = rel_parts[question_idx + 1]
    event_clip = event_dir.name

    label_part = next((p for p in rel_parts[:question_idx] if map_label(p) in {'anxiety_rendah', 'anxiety_tinggi'}), None)
    if label_part is None:
        raise ValueError(f'Cannot parse label from: {event_dir}')
    label = map_label(label_part)

    ann = annotation_lookup.get(participant_raw) or annotation_lookup.get(normalize_subject_id(participant_raw)) or {}
    phase = str(ann.get('stage') or 'unknown')

    return EventClip(
        date=dataset_name,
        phase=phase,
        condition=label,
        label=label,
        participant_raw=participant_raw,
        participant_key=normalize_participant_key(participant_raw),
        question=question,
        question_no=parse_question_no(question),
        sample_name=sample_name,
        clip_name=sample_name,
        event_clip=event_clip,
        event_no=event_no_from_name(event_clip),
        event_dir=str(event_dir.resolve()),
        clip_path=relative_to_root(event_dir),
        score=ann.get('score'),
        annotation_sheet=ann.get('annotation_sheet'),
    )


def discover_event_clips(dataset_root: Path, dataset_name: str) -> tuple[list[EventClip], list[tuple[str, str]]]:
    clips, errors = [], []
    event_dirs = sorted([p for p in dataset_root.rglob('event_*') if p.is_dir()], key=lambda p: natural_sort_key(str(p)))
    for event_dir in event_dirs:
        try:
            clips.append(parse_event_dir(event_dir, dataset_root, dataset_name))
        except Exception as exc:
            errors.append((relative_to_root(event_dir), str(exc)))
    return sorted(clips, key=lambda c: (c.participant_key, c.label, c.question_no, c.phase, natural_sort_key(c.clip_name), c.event_no)), errors

for spec in DATASET_SPECS:
    clips, parse_errors = discover_event_clips(spec['dataset_root'], spec['name'])
    print(spec['name'], 'clips=', len(clips), 'parse_errors=', len(parse_errors))


# In[7]:


WORKER_EXTRACTOR = None
WORKER_CONFIG = None


def init_worker(config_dict: dict) -> None:
    global WORKER_EXTRACTOR, WORKER_CONFIG
    WORKER_CONFIG = ComparisonConfig(
        predictor_path=Path(config_dict['predictor_path']),
        output_root=Path(config_dict['output_root']),
        regions=config_dict['regions'],
        target_size={k: tuple(v) for k, v in config_dict['target_size'].items()},
        padding_x=config_dict['padding_x'],
        padding_y=config_dict['padding_y'],
        block_size=config_dict['block_size'],
    )
    WORKER_EXTRACTOR = ROIExtractor(WORKER_CONFIG)


def load_event_frame_paths(event_dir: Path) -> list[Path]:
    return sorted(
        [p for p in event_dir.iterdir() if p.is_file() and p.suffix.lower() in {'.jpg', '.jpeg', '.png'}],
        key=lambda p: natural_sort_key(p.name),
    )


def to_gray(image: np.ndarray) -> np.ndarray:
    return image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def extract_flatten_row(clip: EventClip, frame_no: int, rois: dict[str, np.ndarray], baseline_gray: dict[str, np.ndarray]) -> dict:
    row = {
        'date': clip.date,
        'phase': clip.phase,
        'condition': clip.condition,
        'label': clip.label,
        'participant': clip.participant_key,
        'participant_raw': clip.participant_raw,
        'question': clip.question,
        'question_no': clip.question_no,
        'sample': clip.sample_name,
        'clip': clip.clip_name,
        'event_clip': clip.event_clip,
        'event_no': clip.event_no,
        'clip_path': clip.clip_path,
        'frame': frame_no,
        'score': clip.score,
        'annotation_sheet': clip.annotation_sheet,
    }
    for comp in WORKER_CONFIG.regions:
        gray = to_gray(rois[comp])
        poc = POC(baseline_gray[comp], gray, WORKER_CONFIG.block_size)
        vec = Vektor(poc.getPOC(), WORKER_CONFIG.block_size)
        quad = Quadran(vec.getVektor()).getQuadran()
        for block_id, block in enumerate(quad, start=1):
            row[f'{comp}_x{block_id}'] = block[1]
            row[f'{comp}_y{block_id}'] = block[2]
            row[f'{comp}_t{block_id}'] = block[3]
            row[f'{comp}_m{block_id}'] = block[4]
    return row


def process_event_clip(clip_dict: dict) -> dict:
    clip = EventClip(**clip_dict)
    event_dir = Path(clip.event_dir)
    try:
        frame_paths = load_event_frame_paths(event_dir)
        if len(frame_paths) < 2:
            raise ValueError(f'Need >= 2 frames: {event_dir}')

        baseline = cv2.imread(str(frame_paths[0]))
        if baseline is None:
            raise FileNotFoundError(f'Failed to read image: {frame_paths[0]}')
        baseline_rois = WORKER_EXTRACTOR.extract_rois(baseline)
        baseline_gray = {name: to_gray(img) for name, img in baseline_rois.items()}

        rows = []
        for idx, frame_path in enumerate(frame_paths[1:], start=2):
            image = cv2.imread(str(frame_path))
            if image is None:
                continue
            try:
                rois = WORKER_EXTRACTOR.extract_rois(image)
            except ValueError:
                continue
            rows.append(extract_flatten_row(clip, idx, rois, baseline_gray))
        return {'ok': True, 'sample_id': clip.sample_id, 'rows': rows, 'error': None}
    except Exception as exc:
        return {'ok': False, 'sample_id': clip.sample_id, 'rows': [], 'error': str(exc)}

worker_config = {
    'predictor_path': str(BASE_CONFIG.predictor_path),
    'output_root': str(BASE_CONFIG.output_root),
    'regions': BASE_CONFIG.regions,
    'target_size': BASE_CONFIG.target_size,
    'padding_x': BASE_CONFIG.padding_x,
    'padding_y': BASE_CONFIG.padding_y,
    'block_size': BASE_CONFIG.block_size,
}


# In[8]:


def flush_rows(rows: list[dict], temp_dir: Path, batch_no: int) -> int:
    if not rows:
        return batch_no
    temp_dir.mkdir(parents=True, exist_ok=True)
    path = temp_dir / f'batch_{batch_no:04d}.csv'
    pd.DataFrame(rows).to_csv(path, index=False)
    print(f'  flushed {len(rows)} rows -> {path.name}')
    rows.clear()
    gc.collect()
    return batch_no + 1


def finalize_batches(temp_dir: Path, output_path: Path) -> pd.DataFrame:
    batch_paths = sorted(temp_dir.glob('batch_*.csv'))
    if not batch_paths:
        raise ValueError(f'No rows produced in {temp_dir}')
    dfs = [pd.read_csv(path) for path in batch_paths]
    df = pd.concat(dfs, ignore_index=True)
    df = df.sort_values(
        by=['date', 'participant', 'label', 'question_no', 'phase', 'clip', 'event_clip', 'event_no', 'frame'],
        key=lambda s: s.map({'before': 0, 'after': 1, 'unknown': 2}) if s.name == 'phase' else s,
        kind='stable',
    ).reset_index(drop=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(output_path, index=False)
    return df


def export_dataset_slice(spec: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    name = spec['name']
    dataset_root = spec['dataset_root']
    output_dir = FEATURE_ROOT / name
    output_path = output_dir / 'poc_abs_test.xlsx'
    errors_path = output_dir / 'errors.xlsx'
    temp_dir = TEMP_ROOT / name

    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    if output_path.exists() and not OVERWRITE:
        print(f'Skip {name}: exists {output_path}')
        return pd.read_excel(output_path), pd.DataFrame()

    clips, parse_errors = discover_event_clips(dataset_root, name)
    print(f'Export {name}: {len(clips)} clips, {len(parse_errors)} parse errors')

    rows_buffer, errors = [], list(parse_errors)
    batch_no = 0
    completed = 0

    with ProcessPoolExecutor(max_workers=MAX_WORKERS, initializer=init_worker, initargs=(worker_config,)) as executor:
        futures = [executor.submit(process_event_clip, asdict(clip)) for clip in clips]
        for future in tqdm(as_completed(futures), total=len(futures), desc=f'Export {name}', unit='clip'):
            result = future.result()
            if result['ok']:
                rows_buffer.extend(result['rows'])
            else:
                errors.append((result['sample_id'], result['error']))
            if len(rows_buffer) >= FLUSH_ROWS:
                batch_no = flush_rows(rows_buffer, temp_dir, batch_no)

    batch_no = flush_rows(rows_buffer, temp_dir, batch_no)
    df = finalize_batches(temp_dir, output_path)
    error_df = pd.DataFrame(errors, columns=['sample_id', 'error'])
    output_dir.mkdir(parents=True, exist_ok=True)
    error_df.to_excel(errors_path, index=False)
    print(f'Saved: {output_path} shape={df.shape}')
    print(f'Saved errors: {errors_path} rows={len(error_df)}')
    return df, error_df


# In[9]:


export_results = {}
for spec in DATASET_SPECS:
    df, error_df = export_dataset_slice(spec)
    export_results[spec['name']] = {'df': df, 'errors': error_df}

summary_rows = []
for name, result in export_results.items():
    df = result['df']
    summary_rows.append({
        'dataset': name,
        'rows': len(df),
        'participants': df['participant_raw'].nunique(),
        'events': df[['participant_raw', 'question', 'sample', 'event_clip', 'event_no']].drop_duplicates().shape[0],
        'errors': len(result['errors']),
        'output': str((FEATURE_ROOT / name / 'poc_abs_test.xlsx').relative_to(ROOT)),
    })
summary_df = pd.DataFrame(summary_rows)
summary_path = FEATURE_ROOT / 'export_summary.xlsx'
summary_df.to_excel(summary_path, index=False)
print(f'Saved summary: {summary_path}')
print(summary_df.to_string(index=False))


# In[10]:


for name, result in export_results.items():
    df = result['df']
    print(f'===== {name} =====')
    print(df[['date', 'participant', 'label', 'question', 'phase', 'event_clip', 'event_no', 'frame']].head(20).to_string(index=False))
    print('phase:', df['phase'].value_counts(dropna=False).to_dict())
    print('label:', df['label'].value_counts(dropna=False).to_dict())
    print()


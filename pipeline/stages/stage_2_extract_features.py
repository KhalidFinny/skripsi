#!/usr/bin/env python
# coding: utf-8

# # Export POC-ABS dari apex event clips ke satu XLSX
# 
# Pipeline:
# 1. Baca `output/apex/metadata.xlsx`
# 2. Ambil semua clip event dari `output/apex/dataset/.../event_*`
# 3. Per event clip: frame pertama = baseline, frame berikutnya = POC-ABS flatten
# 4. Gabung semua row jadi **satu XLSX**
# 5. Urutkan per partisipan / label / pertanyaan dari **before → after**
# 

# In[1]:


import argparse
import gc
import os
import re
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from tqdm import tqdm

import cv2
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

print(f'Project root: {ROOT}')


# In[2]:


from apex import ApexPhase, ApexSmoother
from shared.config import ComparisonConfig
from shared.roi import ROIExtractor
from features.poc import POC
from features import geometry
from features.quadran import Quadran
from features.roi_config import (
    BLOCK_SIZE,
    REGIONS as _CANON_REGIONS,
    REGIONS_TANPA_ALIS,
    TARGET_SIZE as _CANON_TARGET_SIZE,
)
from features.vektor import Vektor


# In[3]:


_parser = argparse.ArgumentParser(description='Export POC-ABS features (3 atau 5 region).')
_parser.add_argument('--brows', action='store_true', help='sertakan alis (608 fitur) -> poc_abs_flatten_ordered_608.xlsx')
_parser.add_argument('--roi-signals', action='store_true', help='mode agregat: 5 sinyal per ROI per frame (25 fitur) + apex per area')
_parser.add_argument(
    '--with-geometry', action='store_true',
    help='Tambah keluarga fitur geometri wajah + head pose (kolom geo_*): EAR, MAR, '
         'jarak alis-mata, lebar rahang, pitch/yaw/roll, plus kecepatannya. Semua fitur '
         'statis dinormalkan skala inter-okular lalu DIKURANGI baseline netral subjek '
         '(Differential AU, StressGAT). Menulis 3 tabel: POC-ABS saja (skema lama, tidak '
         'berubah), geometri saja, dan gabungan. Dasar riset: '
         'report/findings/geometri-headpose.md',
)
_parser.add_argument(
    '--baseline', choices=['onset', 'neutral'], default='onset',
    help="Acuan POC-ABS. 'onset' (default): frame pertama klip event = frame onset, "
         "otot sudah mulai berkontraksi (perilaku lama). 'neutral': neutral.png per "
         "sample yang disimpan spotting (SPOT_SAVE_NEUTRAL=1) -- baseline netral per "
         "orang. Kalau neutral.png tidak ada, jatuh ke 'onset' dengan peringatan.",
)
_parser.add_argument(
    '--output', type=Path, default=None,
    help="Path tabel keluaran (xlsx). Default mengikuti mode (mis. poc_abs_roi_signals.xlsx). "
         "Dipakai supaya run baseline berbeda tidak menimpa tabel lama.",
)
_parser.add_argument(
    '--limit', type=int, default=None,
    help='Proses hanya N klip pertama (untuk memeriksa perubahan kode dengan cepat '
         'sebelum menjalankan ekstraksi penuh ~33 menit). Default: semua klip.',
)
_ARGS = _parser.parse_args()
if _ARGS.roi_signals:
    _ARGS.brows = True

DATASET_ROOT = Path(os.environ.get('FEAT_DATASET_ROOT', str(ROOT / 'output/apex/dataset'))).resolve()
METADATA_PATH = Path(os.environ.get('FEAT_METADATA_PATH', str(ROOT / 'output/apex/metadata.xlsx'))).resolve()
OUTPUT_DIR = (ROOT / 'experiments/features/apex').resolve()
if _ARGS.roi_signals:
    OUTPUT_PATH = OUTPUT_DIR / 'poc_abs_roi_signals.xlsx'
    APEX_OUTPUT_PATH = OUTPUT_DIR / 'roi_apex.xlsx'
else:
    OUTPUT_PATH = OUTPUT_DIR / ('poc_abs_flatten_ordered_608.xlsx' if _ARGS.brows else 'poc_abs_flatten_ordered.xlsx')
    APEX_OUTPUT_PATH = None
if _ARGS.output is not None:
    # Dipakai supaya run dengan baseline berbeda tidak menimpa tabel lama.
    OUTPUT_PATH = _ARGS.output if _ARGS.output.is_absolute() else (ROOT / _ARGS.output)
    APEX_OUTPUT_PATH = OUTPUT_PATH.with_name(f'{OUTPUT_PATH.stem}_apex.xlsx') if _ARGS.roi_signals else None

# Dua tabel turunan --with-geometry. Nama diturunkan dari OUTPUT_PATH supaya run
# dengan --output berbeda tidak saling menimpa.
GEO_OUTPUT_PATH = OUTPUT_PATH.with_name(f'{OUTPUT_PATH.stem}_geo.xlsx')
FUSED_OUTPUT_PATH = OUTPUT_PATH.with_name(f'{OUTPUT_PATH.stem}_fused.xlsx')

# Kolom identitas baris. Sama persis di ketiga tabel supaya bisa di-join 1:1 dan
# dibaca run_loso.py/within_subject_test.py.
KEY_COLS = [
    'phase', 'condition', 'label', 'participant', 'participant_raw', 'question', 'question_no',
    'sample', 'clip', 'event_clip', 'event_no', 'clip_path', 'frame',
]
MAX_WORKERS = int(os.environ.get('FEAT_WORKERS', min(6, os.cpu_count() or 1)))  # 6: frame di-streaming per-klip, memori worker kecil

REGIONS = dict(_CANON_REGIONS) if _ARGS.brows else dict(REGIONS_TANPA_ALIS)
TARGET_SIZE = {k: v for k, v in _CANON_TARGET_SIZE.items() if k in REGIONS}

config = ComparisonConfig(
    output_root=Path('output/apex/tmp_compare'),
    regions=REGIONS,
    target_size=TARGET_SIZE,
)

print(f'Dataset root: {DATASET_ROOT}')
print(f'Metadata:     {METADATA_PATH}')
print(f'Output xlsx:  {OUTPUT_PATH}')
print(f'Max workers:  {MAX_WORKERS}')
print(f'Regions:      {list(config.regions.keys())}')
print(f'Target size:  {config.target_size}')
print(f'Block size:   {config.block_size}')


# In[4]:


if not DATASET_ROOT.exists():
    raise FileNotFoundError(f'Dataset root not found: {DATASET_ROOT}')
if not METADATA_PATH.exists():
    raise FileNotFoundError(f'Metadata not found: {METADATA_PATH}')
if not config.predictor_path.exists():
    raise FileNotFoundError(f'Predictor not found: {config.predictor_path}')

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
metadata = pd.read_excel(METADATA_PATH)
print(f'Metadata rows: {len(metadata)}')
metadata.head(2)


# In[5]:


@dataclass(slots=True)
class EventClip:
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
    event_dir: Path
    onset_frame: int
    apex_frame: int
    offset_frame: int

    @property
    def sample_id(self) -> str:
        return f'{self.phase}__{self.condition}__{self.participant_raw}__{self.question}__{self.sample_name}__event_{self.event_no:03d}'


def natural_sort_key(value: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', value)]


def parse_question_no(question: str) -> int:
    match = re.search(r'(\d+)', question)
    return int(match.group(1)) if match else 0


def normalize_participant_key(name: str) -> str:
    return re.sub(r'_[0-9]+$', '', name)


def map_label(condition: str) -> str:
    mapping = {
        'anxiety': 'anxiety_tinggi',
        'tidak': 'anxiety_rendah',
    }
    return mapping.get(condition, condition)


def parse_event_dir(clip_dir_value: str) -> Path:
    raw = Path(str(clip_dir_value).replace('\\', '/'))
    parts = raw.parts

    if raw.is_absolute():
        return raw.resolve()

    if parts[:3] == ('output', 'apex', 'dataset'):
        raw = Path(*parts[3:])
    elif parts and parts[0] == 'dataset':
        raw = Path(*parts[1:])

    return (DATASET_ROOT / raw).resolve()


def build_event_clips(df: pd.DataFrame) -> list[EventClip]:
    clips: list[EventClip] = []
    valid = df[df['clip_dir'].notna()].copy()

    for row in valid.itertuples(index=False):
        parts = Path(row.relative_sample).parts
        if len(parts) < 5:
            continue

        phase, condition, participant_raw, question, sample_name = parts[:5]
        event_dir = parse_event_dir(row.clip_dir)
        clips.append(EventClip(
            phase=phase,
            condition=condition,
            label=map_label(condition),
            participant_raw=participant_raw,
            participant_key=normalize_participant_key(participant_raw),
            question=question,
            question_no=parse_question_no(question),
            sample_name=sample_name,
            clip_name=sample_name,
            event_clip=event_dir.name,
            event_no=int(row.event_no),
            event_dir=event_dir,
            onset_frame=int(row.onset_frame),
            apex_frame=int(row.apex_frame),
            offset_frame=int(row.offset_frame),
        ))

    return sorted(
        clips,
        key=lambda c: (
            c.participant_key,
            c.label,
            c.question_no,
            0 if c.phase == 'before' else 1,
            natural_sort_key(c.clip_name),
            c.event_no,
            natural_sort_key(c.event_clip),
        ),
    )


event_clips = build_event_clips(metadata)
if _ARGS.limit is not None:
    event_clips = event_clips[:_ARGS.limit]
print(f'Event clips: {len(event_clips)}')
event_clips[:3]


# In[6]:


WORKER_EXTRACTOR = None
WORKER_CONFIG = None


def init_worker() -> None:
    global WORKER_EXTRACTOR, WORKER_CONFIG
    WORKER_CONFIG = ComparisonConfig(
        output_root=Path('output/apex/tmp_compare'),
        regions=REGIONS,
        target_size=TARGET_SIZE,
        padding_x=config.padding_x,
        padding_y=config.padding_y,
        block_size=config.block_size,
        predictor_path=config.predictor_path,
        feature_method=config.feature_method,
        include_quadrant_counts=config.include_quadrant_counts,
    )
    WORKER_EXTRACTOR = ROIExtractor(WORKER_CONFIG)


def to_gray(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def extract_flatten_row(clip: EventClip, frame_no: int, rois: dict[str, np.ndarray], baseline_gray: dict[str, np.ndarray], block_size: int) -> dict:
    row = {
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
        'clip_path': str(clip.event_dir.resolve().relative_to(ROOT.resolve())),
        'frame': frame_no,
    }

    for comp in WORKER_CONFIG.regions:
        gray = to_gray(rois[comp])
        poc = POC(baseline_gray[comp], gray, block_size)
        vec = Vektor(poc.getPOC(), block_size)
        quad = Quadran(vec.getVektor()).getQuadran()

        for block_id, block in enumerate(quad, start=1):
            row[f'{comp}_x{block_id}'] = block[1]
            row[f'{comp}_y{block_id}'] = block[2]
            row[f'{comp}_t{block_id}'] = block[3]
            row[f'{comp}_m{block_id}'] = block[4]

    return row


def per_block_data(rois: dict[str, np.ndarray], baseline_gray: dict[str, np.ndarray], block_size: int) -> dict[str, np.ndarray]:
    """Per ROI: array (n_blocks, 6) dari Quadran.getQuadran (id, x, y, t, m)."""
    out = {}
    for comp in WORKER_CONFIG.regions:
        gray = to_gray(rois[comp])
        poc = POC(baseline_gray[comp], gray, block_size)
        vec = Vektor(poc.getPOC(), block_size)
        out[comp] = Quadran(vec.getVektor()).getQuadran()
    return out


def extract_roi_signal_row(clip: EventClip, frame_no: int, quad: dict[str, np.ndarray]) -> dict:
    row = {
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
        'clip_path': str(clip.event_dir.resolve().relative_to(ROOT.resolve())),
        'frame': frame_no,
    }

    for comp, block_data in quad.items():
        mags = np.asarray([float(b[4]) for b in block_data], dtype=float)
        xs = np.asarray([float(b[1]) for b in block_data], dtype=float)
        ys = np.asarray([float(b[2]) for b in block_data], dtype=float)
        row[f'{comp}_mean_m'] = float(np.mean(mags)) if len(mags) else 0.0
        row[f'{comp}_max_m'] = float(np.max(mags)) if len(mags) else 0.0
        row[f'{comp}_mean_abs_x'] = float(np.mean(np.abs(xs))) if len(xs) else 0.0
        row[f'{comp}_mean_abs_y'] = float(np.mean(np.abs(ys))) if len(ys) else 0.0
        row[f'{comp}_motion_count'] = float(np.mean(mags > 0)) if len(mags) else 0.0
        # ARAH BERTANDA. Quadran menghitung X dan Y bertanda (oX/oY), tapi versi lama
        # hanya menyimpan mean(|X|) dan mean(|Y|) sehingga tanda arah hilang: mulut
        # naik dan mulut turun jadi fitur yang identik. Karena acuan POC-ABS adalah
        # wajah NETRAL (bukan onset), arah perpindahan konsisten sepanjang event,
        # jadi mean(X)/mean(Y) bertanda memang bermakna, bukan saling menghapus.
        row[f'{comp}_mean_x'] = float(np.mean(xs)) if len(xs) else 0.0
        row[f'{comp}_mean_y'] = float(np.mean(ys)) if len(ys) else 0.0

        # --- E3: arah hanya atas BLOK YANG BERGERAK + sudut yang tadinya dibuang ---
        # mean_x/mean_y di atas dirata-ratakan atas SEMUA blok, termasuk yang diam
        # (nilainya 0). Jadi keduanya mencampur dua hal berbeda: "berapa banyak blok
        # bergerak" (identitas) dan "ke arah mana" (kondisi). Empat fitur di bawah
        # memisahkan keduanya.
        mov = mags > 0
        if mov.any():
            xs_m, ys_m = xs[mov], ys[mov]
            row[f'{comp}_mean_x_mov'] = float(np.mean(xs_m))
            row[f'{comp}_mean_y_mov'] = float(np.mean(ys_m))
            # Sudut: Quadran sudah menghitung tetha lalu membuangnya. Dihitung ulang
            # dari X/Y supaya tidak bergantung pada pembulatan format_number_and_round.
            # Rata-rata sudut TIDAK boleh aritmetik (0 dan 359 derajat bukan 179,5);
            # dipakai rata-rata sirkular: vektor satuan (cos, sin) lalu dijumlahkan.
            th = np.arctan2(ys_m, xs_m)
            c, s = float(np.mean(np.cos(th))), float(np.mean(np.sin(th)))
            row[f'{comp}_angle_cos'] = c
            row[f'{comp}_angle_sin'] = s
            # Panjang resultan: 1 = semua blok bergerak searah, 0 = arah acak.
            # Mengukur KOHERENSI arah, bukan besarnya gerakan.
            row[f'{comp}_angle_R'] = float(np.hypot(c, s))
        else:
            for suffix in ('mean_x_mov', 'mean_y_mov', 'angle_cos', 'angle_sin', 'angle_R'):
                row[f'{comp}_{suffix}'] = 0.0

    return row


def attach_geometry(
    row: dict,
    static_geo: dict[str, float] | None,
    baseline_geo: dict[str, float] | None,
    prev_geo: dict[str, float] | None,
) -> dict[str, float] | None:
    """Tambah kolom geo_* ke `row`; kembalikan frame ini sebagai `prev_geo` berikutnya.

    Statis  = nilai frame dikurangi baseline netral subjek (Differential AU).
    Kecepatan = selisih terhadap frame terakhir yang terdeteksi. Frame tanpa wajah
    tidak masuk tabel, jadi `prev_geo` sengaja tidak direset: kecepatan dihitung
    terhadap frame terakhir yang benar-benar ada, bukan terhadap frame yang hilang.
    """
    if static_geo is None:
        return prev_geo
    row.update(geometry.differential(static_geo, baseline_geo))
    row.update(geometry.velocity(prev_geo, static_geo))
    return static_geo


def detect_roi_apex(clip: EventClip, region: str, signal: list[float]) -> dict | None:
    """Apex per area, parameter sama dengan spotting (distance 1, prominence 0.005, cutoff 0.3).

    CATATAN (belum diperbaiki, sengaja): `clip.onset_frame + indeks_sinyal` hanya
    benar kalau indeks sinyal == nomor frame clip-relatif. Itu berlaku pada mode
    `--baseline neutral` (dipakai pipeline: frame 1 menghasilkan baris DAN slot
    sinyal, jadi pemetaannya 1:1). Pada mode `--baseline onset`, frame 1 sengaja
    dibuang dari keduanya sehingga seluruh nomor frame bergeser satu. Tabel apex
    tidak dikonsumsi training, jadi ini tidak memengaruhi hasil; dicatat di sini
    supaya tidak hilang kalau mode onset dipakai lagi.

    Gagal/tidak ada puncak -> None (bukan exception): output apex hanya pelengkap,
    tidak boleh menggagalkan baris fitur event.
    """
    try:
        if len(signal) < 3:
            return None
        smoothed = ApexSmoother.smooth(signal)
        signal_arr = np.asarray(smoothed, dtype=float)
        height_threshold = float(signal_arr.mean() + signal_arr.std()) if len(signal_arr) else 0.0
        detector = ApexPhase(distance_threshold=1, prominence_threshold=0.005, cutoff_ratio=0.3)
        apex_indices = detector.find_top_k_apex(smoothed, k=1, height=height_threshold)
        if not apex_indices:
            return None
        apex_idx = apex_indices[0]
        phase = detector.find_phase(smoothed, [apex_idx]).get(apex_idx)
        if phase is None:
            return None
        if int(phase['end'] - phase['start']) < 2:
            return None

        return {
            'region': region,
            'onset_signal': int(phase['start']),
            'apex_signal': int(apex_idx),
            'offset_signal': int(phase['end']),
            'onset_frame': clip.onset_frame + int(phase['start']),
            'apex_frame': clip.onset_frame + int(apex_idx),
            'offset_frame': clip.onset_frame + int(phase['end']),
            'apex_value': float(smoothed[apex_idx]),
        }
    except Exception:
        return None


_WARNED_NO_NEUTRAL: set[str] = set()


def resolve_neutral_baseline(clip: EventClip) -> np.ndarray | None:
    """Baca neutral.png per sample bila --baseline neutral.

    None = pakai frame onset klip (perilaku lama / fallback). Peringatan hanya
    sekali per sample supaya log tidak banjir saat dataset lama (tanpa
    neutral.png) diekspor.
    """
    if _ARGS.baseline != 'neutral':
        return None
    path = clip.event_dir.parent / 'neutral.png'
    image = cv2.imread(str(path)) if path.exists() else None
    if image is None:
        sample_dir = str(clip.event_dir.parent)
        if sample_dir not in _WARNED_NO_NEUTRAL:
            _WARNED_NO_NEUTRAL.add(sample_dir)
            print(f'PERINGATAN: neutral.png tidak ada/tidak terbaca di {clip.event_dir.parent}; '
                  f'fallback ke frame onset klip', flush=True)
    return image


def process_event_clip(clip: EventClip) -> tuple[list[dict], list[dict] | None]:
    # Streaming per frame: hanya 1 frame di RAM per worker (bukan seluruh klip).
    # Acuan POC = frame onset klip (--baseline onset) atau neutral.png per sample
    # (--baseline neutral); frame berikutnya dibaca, diproses, langsung dibuang.
    frame_paths = sorted(
        [p for p in clip.event_dir.iterdir() if p.is_file() and p.suffix.lower() in {'.jpg', '.jpeg', '.png'}],
        key=lambda p: natural_sort_key(p.name),
    )
    if len(frame_paths) < 2:
        raise ValueError(f'Need >= 2 frames: {clip.event_dir}')

    baseline_image = resolve_neutral_baseline(clip)
    baseline_gray: dict[str, np.ndarray] | None = None
    baseline_geo: dict[str, float] | None = None
    prev_geo: dict[str, float] | None = None
    rows: list[dict] = []
    # Jangan diisi 0.0 palsu: elemen pertama harus benar-benar frame pertama. Kalau
    # tidak, sinyal yang dipakai detect_roi_apex punya puncak palsu di indeks 0 dan
    # semua nomor frame apex bergeser satu.
    roi_signals: dict[str, list[float]] = {comp: [] for comp in WORKER_CONFIG.regions}

    for idx, path in enumerate(frame_paths):
        image = cv2.imread(str(path))
        if image is None:
            raise FileNotFoundError(f'Failed to read image: {path}')
        frame_no = idx + 1

        if idx == 0:
            own_baseline = baseline_image is None
            reference = image if own_baseline else baseline_image
            ref_landmarks = WORKER_EXTRACTOR.extract_landmarks(reference) if _ARGS.with_geometry else None
            try:
                if ref_landmarks is not None:
                    baseline_rois = WORKER_EXTRACTOR.extract_rois_from_landmarks(reference, ref_landmarks)
                else:
                    baseline_rois = WORKER_EXTRACTOR.extract_rois(reference)
            except ValueError:
                baseline_rois = None
            if baseline_rois is None:
                raise ValueError(f'No face detected in baseline frame: {clip.event_dir}')
            if ref_landmarks is not None:
                # Baseline geometri = wajah netral orang ini (Differential AU, StressGAT).
                baseline_geo = geometry.extract_geometry(ref_landmarks, reference.shape)
            baseline_gray = {name: to_gray(img) for name, img in baseline_rois.items()}
            if own_baseline:
                # Acuan = frame onset itu sendiri -> POC(frame0, frame0) = 0, bukan baris data.
                del image, reference
                continue
            # Acuan netral (neutral.png): frame onset (frame 1) adalah baris data yang SAH,
            # jadi jangan dibuang. Versi lama membuangnya di KEDUA mode, sehingga tabel
            # fitur kehilangan frame onset pada semua event (kolom `frame` mulai dari 2).

        image_shape = image.shape
        landmarks = WORKER_EXTRACTOR.extract_landmarks(image) if _ARGS.with_geometry else None
        try:
            if landmarks is not None:
                rois = WORKER_EXTRACTOR.extract_rois_from_landmarks(image, landmarks)
            else:
                rois = WORKER_EXTRACTOR.extract_rois(image)
        except ValueError:
            rois = None
        static_geo = (
            geometry.extract_geometry(landmarks, image_shape)
            if (_ARGS.with_geometry and landmarks is not None)
            else None
        )
        del image

        if rois is None:
            if _ARGS.roi_signals:
                for comp in WORKER_CONFIG.regions:
                    roi_signals[comp].append(0.0)
            continue

        if _ARGS.roi_signals:
            quad = per_block_data(rois, baseline_gray, WORKER_CONFIG.block_size)
            row = extract_roi_signal_row(clip, frame_no, quad)
            prev_geo = attach_geometry(row, static_geo, baseline_geo, prev_geo)
            rows.append(row)
            for comp in WORKER_CONFIG.regions:
                mags = np.asarray([float(b[4]) for b in quad[comp]], dtype=float)
                roi_signals[comp].append(float(np.mean(mags)) if len(mags) else 0.0)
        else:
            row = extract_flatten_row(clip, frame_no, rois, baseline_gray, WORKER_CONFIG.block_size)
            prev_geo = attach_geometry(row, static_geo, baseline_geo, prev_geo)
            rows.append(row)

    apex_rows = None
    if _ARGS.roi_signals:
        apex_rows = []
        for comp in WORKER_CONFIG.regions:
            rec = detect_roi_apex(clip, comp, roi_signals[comp])
            if rec is not None:
                rec.update({
                    'phase': clip.phase, 'condition': clip.condition, 'label': clip.label,
                    'participant': clip.participant_key, 'participant_raw': clip.participant_raw,
                    'question': clip.question, 'question_no': clip.question_no,
                    'sample': clip.sample_name, 'clip': clip.clip_name,
                    'event_clip': clip.event_clip, 'event_no': clip.event_no,
                    'clip_path': str(clip.event_dir.resolve().relative_to(ROOT.resolve())),
                })
                apex_rows.append(rec)

    return rows, apex_rows


def worker_task(clip: EventClip) -> tuple[EventClip, list[dict] | None, list[dict] | None, str | None]:
    try:
        rows, apex_rows = process_event_clip(clip)
        return clip, rows, apex_rows, None
    except Exception as exc:
        return clip, None, None, str(exc)


def save_xlsx_streaming(df: pd.DataFrame, path: Path) -> None:
    """Tulis xlsx tanpa menahan semua sel di memori (openpyxl write_only).

    to_excel biasa mem-build seluruh workbook di RAM; untuk ~16 juta sel
    (2706 klip) itu bisa membuat proses di-OOM kill.
    """
    from openpyxl import Workbook

    wb = Workbook(write_only=True)
    ws = wb.create_sheet()
    ws.append(list(df.columns))
    for row in df.itertuples(index=False, name=None):
        ws.append(row)
    wb.save(path)


# In[7]:


all_apex = []
errors = []
chunk_dfs: list[pd.DataFrame] = []
pending_rows: list[dict] = []
CHUNK_CLIPS = 800  # baris di-flush ke DataFrame tiap ~800 klip -> RAM flat, tidak menumpuk list dict raksasa

def flush_pending() -> None:
    if pending_rows:
        chunk_dfs.append(pd.DataFrame(pending_rows))
        pending_rows.clear()

with ProcessPoolExecutor(max_workers=MAX_WORKERS, initializer=init_worker) as executor:
    futures = [executor.submit(worker_task, clip) for clip in event_clips]

    for future in tqdm(futures, total=len(futures), desc='Ekspor fitur', unit='clip'):
        clip, rows, apex_rows, error = future.result()
        if error is not None:
            errors.append((clip.sample_id, error))
            continue
        pending_rows.extend(rows)
        if len(pending_rows) >= CHUNK_CLIPS:
            flush_pending()
        if apex_rows:
            all_apex.extend(apex_rows)
flush_pending()
gc.collect()

print(f'Rows collected: {sum(len(c) for c in chunk_dfs)}', flush=True)
print(f'Errors: {len(errors)}', flush=True)


# In[8]:


if errors:
    error_df = pd.DataFrame(errors, columns=['sample_id', 'error'])
    print(error_df.head(20).to_string(index=False))
    error_df.head(20)


# In[9]:


df = pd.concat(chunk_dfs, ignore_index=True)
del chunk_dfs
gc.collect()  # lepaskan list chunk sebelum sort (anti-OOM pada 4.737 event / ~65k baris)

if df.empty:
    raise ValueError('No rows produced.')

df = df.sort_values(
    by=['participant', 'label', 'question_no', 'phase', 'clip', 'event_clip', 'event_no', 'frame'],
    key=lambda s: s.map({'before': 0, 'after': 1}) if s.name == 'phase' else s,
    kind='stable',
).reset_index(drop=True)

geo_cols = [c for c in df.columns if c.startswith(geometry.GEO_PREFIX)]
poc_cols = [c for c in df.columns if c not in geo_cols]

save_xlsx_streaming(df[poc_cols], OUTPUT_PATH)
print(f'Saved: {OUTPUT_PATH} (POC-ABS saja, {len(poc_cols)} kolom)', flush=True)

if _ARGS.with_geometry:
    missing_key = [c for c in KEY_COLS if c not in df.columns]
    if missing_key:
        raise ValueError(f'Kolom identitas hilang dari tabel fitur: {missing_key}')
    if not geo_cols:
        raise ValueError('--with-geometry tidak menghasilkan kolom geo_*; periksa ekstraksi geometri.')
    save_xlsx_streaming(df[KEY_COLS + geo_cols], GEO_OUTPUT_PATH)
    print(f'Saved: {GEO_OUTPUT_PATH} (geometri saja, {len(geo_cols)} kolom)', flush=True)
    save_xlsx_streaming(df, FUSED_OUTPUT_PATH)
    print(f'Saved: {FUSED_OUTPUT_PATH} (gabungan POC-ABS + geometri, {df.shape[1]} kolom)', flush=True)

print(f'Shape: {df.shape}', flush=True)
df.head()

if _ARGS.roi_signals and all_apex:
    apex_df = pd.DataFrame(all_apex)
    apex_df = apex_df.sort_values(
        by=['participant', 'label', 'question_no', 'phase', 'clip', 'event_clip', 'event_no', 'region'],
        key=lambda s: s.map({'before': 0, 'after': 1}) if s.name == 'phase' else s,
        kind='stable',
    ).reset_index(drop=True)
    save_xlsx_streaming(apex_df, APEX_OUTPUT_PATH)
    print(f'Saved apex per area: {APEX_OUTPUT_PATH}', flush=True)
    print(f'Apex rows: {len(apex_df)}', flush=True)
    print(apex_df.groupby('region').size().to_dict(), flush=True)


# In[11] (dihapus): re-save "phase-first ordering" duplikat — sort di atas sudah
# mengurutkan phase before->after lewat key; menulis xlsx dua kali memboroskan
# memori (penyebab OOM pada data penuh).


# In[10]:


print(df[['participant', 'label', 'question', 'phase', 'clip', 'event_clip', 'event_no', 'frame']].head(20).to_string(index=False))
print()
print(df['phase'].value_counts().to_dict())
print(df['label'].value_counts().to_dict())


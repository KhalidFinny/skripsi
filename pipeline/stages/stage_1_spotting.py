#!/usr/bin/env python
# coding: utf-8

# # Micro-Expression Spotting — Clip Output
# 
# Notebook utama untuk spotting.
# 
# Output:
# - `/output/apex/metadata.xlsx`
# - `/output/apex/dataset/...`
# 
# Struktur folder input dipertahankan pada `/output/apex/dataset`.
# 

# In[1]:


import gc
import os
import re
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from tqdm import tqdm

import cv2
import dlib
import numpy as np
import pandas as pd
from scipy.signal import find_peaks, savgol_filter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apex import ApexPhase, ApexSmoother, ApexPhaseVisualizer
from features.poc import POC
from features.quadran import Quadran
from features.vektor import Vektor
from pipeline.spotting_config import SpottingConfig


# In[2]:


config = SpottingConfig(
    dataset_root=Path(os.environ.get('SPOT_DATASET_ROOT', str(PROJECT_ROOT / 'dataset' / 'datatest' / 'labeled'))),
    output_root=Path(os.environ.get('SPOT_OUTPUT_ROOT', str(PROJECT_ROOT / 'output' / 'apex' / 'datatest'))),
    predictor_path=Path(os.environ.get('SPOT_PREDICTOR', str(PROJECT_ROOT / 'models/shape_predictor_68_face_landmarks.dat'))),
    video_extensions=set(os.environ.get('SPOT_VIDEO_EXT', '.webm').split(',')),
    overwrite=os.environ.get('SPOT_OVERWRITE', '0') == '1',
    # cutoff_ratio batas onset/offset: 0,3 default (menang F1 longgar CAS(ME)^2 di
    # kedua fold validasi subjek); 0,5 menang F1 ketat (IoU>=0,5) dan memperpendek
    # durasi 61->41 frame. Opsi env untuk uji A/B di sisi anxiety.
    # Lihat report/findings/audit-spotting-casme2.md bagian 10.
    cutoff_ratio=float(os.environ.get('SPOT_CUTOFF', '0.3')),
)

USE_ABS_BASELINE = os.environ.get('SPOT_ABS', '1') == '1'  # True = POC-ABS (frame-0 baseline); False = frame berurutan (asli)
# 3.2: 'global_mean' = sinyal lama (mean antar ROI, apex global); 'roi_signals' = sinyal per-ROI, apex per area (digabung)
# AUDIT 2026-10-09 (CAS(ME)^2, 86 video): mode per-ROI memecah plafon deteksi jadi
# 5 ROI x top_k (19,2 deteksi/video utk GT 3,6) dan F1-nya 0,1637; mode global
# (perilaku asli notebook) 5,0 deteksi/video dgn F1 0,2141. Default dikembalikan
# ke global. Lihat report/findings/audit-spotting-casme2.md.
SPOT_SIGNAL_MODE = os.environ.get('SPOT_SIGNAL_MODE', 'global_mean')
# 3.5: interpolasi nilai saat landmark gagal (bukan 0.0)
SPOT_INTERP = os.environ.get('SPOT_INTERP', '1') == '1'
# 3.4: 'meanstd' = height mean+std (per-ROI di mode roi_signals); 'mad' = median + 2.5*1.4826*MAD (tahan outlier)
SPOT_THRESH = os.environ.get('SPOT_THRESH', 'meanstd')
# Pemilihan K puncak teratas: 'value' (nilai sinyal, perilaku lama) atau
# 'prominence' (paling menonjol lokal). AUDIT 2026-10-09 pada 86 video CAS(ME)^2:
# prominence menaikkan F1 0,266 -> 0,314 (dan tervalidasi di split subjek).
# Ini juga desain notebook asli. Lihat report/findings/audit-spotting-casme2.md.
SPOT_RANKING = os.environ.get('SPOT_RANKING', 'prominence')
# 3.6: aktifkan filter distance & prominence (sebelumnya nyaris non-aktif:
#      distance=1 + prominence=0.005 => satu-satunya gerbang adalah height=mean+std).
#   SPOT_DISTANCE  : jarak minimum antar puncak (frame). 1 = non-aktif (perilaku lama).
#                    CATATAN: merge_distance=10 di ApexPhase tetap yang dominan.
#   SPOT_PROM_REL  : prominence minimum RELATIF terhadap rentang sinyal halus
#                    (0 = pakai config.prominence_threshold, perilaku lama).
#                    Memberi filter nyata utk membuang puncak noise low-SNR.
SPOT_DISTANCE = int(os.environ.get('SPOT_DISTANCE', '1'))
SPOT_PROM_REL = float(os.environ.get('SPOT_PROM_REL', '0.04'))
# Algoritma spotting level-event. Default `phase` = detektor ApexPhase lama pada
# sinyal global mean_m/hpoc/combo/mdmd. `of_fd_proxy` = kandidat precision-first
# dari sweep CAS(ME)^2 2026-10-14: kurva ROI POC-ABS diperlakukan seperti kurva
# optical-flow ROI, dihaluskan, threshold MAD, lalu fixed/beta boundary. Ini
# BUKAN reproduksi dense OF-FD paper; namanya tetap proxy.
SPOT_ALGO = os.environ.get('SPOT_ALGO', 'phase')
SPOT_OF_FD_MAD = float(os.environ.get('SPOT_OF_FD_MAD', '3.5'))
SPOT_OF_FD_TOP = os.environ.get('SPOT_OF_FD_TOP', 'mean')
SPOT_OF_FD_SMOOTH = int(os.environ.get('SPOT_OF_FD_SMOOTH', '35'))
SPOT_OF_FD_WIDTH = int(os.environ.get('SPOT_OF_FD_WIDTH', '35'))
SPOT_OF_FD_DISTANCE = int(os.environ.get('SPOT_OF_FD_DISTANCE', '12'))
SPOT_OF_FD_BOUNDARY_BETA = os.environ.get('SPOT_OF_FD_BOUNDARY_BETA', '0.3')
SPOT_OF_FD_BOUNDARY_BETA = None if SPOT_OF_FD_BOUNDARY_BETA == 'fixed' else float(SPOT_OF_FD_BOUNDARY_BETA)
# Definisi sinyal spotting per ROI:
#   'mean_m' (default, perilaku lama) : mean |V| perpindahan integer per blok.
#   'hpoc'  : mean(1 - nilai puncak POC) per blok — fitur M yang sebenarnya di
#             paper Rosiani et al. 2020 (kode lama menghitung val_max lalu
#             membuangnya). Kontinu, tidak terkuantisasi 1 piksel.
#   'combo' : z(mean_m global) + z(hpoc global) — pemenang audit 2026-10-13
#             (86 video CAS(ME)^2: F1 0,3343 vs 0,3192 baseline; terpilih di
#             kedua fold validasi subjek, test 0,3262/0,3198). Di mode
#             roi_signals, combo diterapkan per ROI (varian ini lebih lemah:
#             0,3113 — lihat report/findings/magnitude-deepdive.md bagian 7).
SPOT_SIGNAL = os.environ.get('SPOT_SIGNAL', 'mean_m')
# LEVER 1 (2026-10-13, deep dive): rigid/global motion compensation. Sebelum
# sinyal dihitung, kurangi komponen gerakan GLOBAL (median antar-blok dx, dy)
# per frame. Gerakan kepala/latar bersifat global — menggerakkan SEMUA blok
# serempak ke arah sama; menguranginya menghilangkan sumber noise terbesar
# tanpa menyentuh sinyal ekspresi LOKAL (perbedaan antar blok). '1' = aktif,
# '0' (default) = perilaku lama bit-identik.
SPOT_MOTION_COMP = os.environ.get('SPOT_MOTION_COMP', '0') == '1'
# LEVER 2 (2026-10-13, deep dive): sinyal SPOT_SIGNAL='mdmd'. Alih-alih
# magnitude mentah, pakai Main Directional Maximal Difference (Wang 2017):
# per frame, kurangi magnitude arah-utama SAAT INI dengan rata-rata frame
# TETANGGA (jendela ±SPOT_MDMD_K). Ekspresi berbalik arah cepat (onset->apex->
# offset) sehingga beda-terhadap-tetangga besar; gerakan kepala berubah lambat
# sehingga bedanya kecil. Diimplementasikan pada sinyal mean_m per ROI (sinyal
# yang sudah ada), lalu dikirim ke detektor puncak yang sama. Aktif juga bila
# SPOT_MDMD=1 (dipaksa mean_m lalu didifference).
SPOT_MDMD = os.environ.get('SPOT_MDMD', '0') == '1'
SPOT_MDMD_K = int(os.environ.get('SPOT_MDMD_K', '5'))
# Lewati penyimpanan event_signals (xlsx/plot per video) — tidak dipakai hilir, hemat waktu
SPOT_NO_EVENT_SIGNAL = os.environ.get('SPOT_NO_EVENT_SIGNAL', '0') == '1'
# Simpan acuan netral per sample (neutral.png) supaya ekstraksi fitur bisa memakai
# baseline netral per orang, bukan frame onset klip yang ototnya sudah berkontraksi.
SPOT_SAVE_NEUTRAL = os.environ.get('SPOT_SAVE_NEUTRAL', '0') == '1'
# Jumlah frame awal video yang di-median jadi acuan netral.
SPOT_NEUTRAL_FRAMES = int(os.environ.get('SPOT_NEUTRAL_FRAMES', '10'))
# Bangun ulang metadata.xlsx HANYA dari klip event yang sudah ada, lalu keluar.
# Dipakai untuk memulihkan metadata yang hilang/rusak tanpa video mentah dan
# tanpa menghitung ulang sinyal (driv raw tidak perlu ter-mount).
SPOT_REBUILD_METADATA_ONLY = os.environ.get('SPOT_REBUILD_METADATA_ONLY', '0') == '1'
# FOLD-FIRST (2026-10-13): path txt berisi daftar ORANG yang boleh diproses
# (satu per baris, hasil split_persons_presplit.py). Video milik orang lain
# TIDAK dibaca sama sekali — inilah jaminan struktural bahwa 12 orang holdout
# tidak terlihat pipeline sebelum evaluasi akhir. Kosong = semua (perilaku
# lama, bit-identik). Nama dinormalisasi dengan regex yang sama dengan
# extract_features_poc_abs.py (strip _[0-9]+$).
SPOT_INCLUDE_PERSONS = os.environ.get('SPOT_INCLUDE_PERSONS', '')


def load_include_persons() -> set[str] | None:
    if not SPOT_INCLUDE_PERSONS:
        return None
    path = Path(SPOT_INCLUDE_PERSONS)
    if not path.is_file():
        raise SystemExit(f'SPOT_INCLUDE_PERSONS tidak ditemukan: {path}')
    persons = set()
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            persons.add(re.sub(r'_[0-9]+$', '', line))
    if not persons:
        raise SystemExit(f'SPOT_INCLUDE_PERSONS kosong: {path}')
    return persons


INCLUDE_PERSONS = load_include_persons()
max_workers = min(4, os.cpu_count() or 1)

print(f'DATASET_ROOT = {config.dataset_root}')
print(f'OUTPUT_DATASET_ROOT = {config.output_dataset_root}')
print(f'METADATA_PATH = {config.metadata_path}')
print(f"EVENT_SIGNAL_ROOT = {config.output_root / 'event_signals'}")
print(f'MAX_WORKERS = {max_workers}')
print(f'SPOT_ALGO = {SPOT_ALGO}')



# In[3]:


@dataclass(slots=True)
class VideoSample:
    video_path: Path
    relative_parent: Path
    stem: str

    @property
    def relative_video_key(self) -> Path:
        return self.relative_parent / self.stem


WORKER_DETECTOR = None
WORKER_PREDICTOR = None


def init_worker(predictor_path: str) -> None:
    global WORKER_DETECTOR, WORKER_PREDICTOR
    WORKER_DETECTOR = dlib.get_frontal_face_detector()
    WORKER_PREDICTOR = dlib.shape_predictor(predictor_path)


def natural_sort_key(value: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', value)]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def discover_video_samples(dataset_root: Path, video_extensions: set[str]) -> list[VideoSample]:
    samples = []
    for video_path in sorted(dataset_root.rglob('*'), key=lambda p: natural_sort_key(str(p))):
        if not video_path.is_file():
            continue
        if video_path.suffix.lower() not in video_extensions:
            continue
        rel = video_path.relative_to(dataset_root)
        samples.append(VideoSample(video_path=video_path, relative_parent=rel.parent, stem=video_path.stem))
    if INCLUDE_PERSONS is not None:
        # Struktur anxiety_raw: <phase>/<condition>/<participant>_<ts>/q*/file.
        # parts[2] = participant_raw (sama dengan extract_features_poc_abs.py).
        # Struktur lain (CAS(ME)^2 dll) TIDAK difilter supaya benchmark tidak
        # berubah — sample dengan path dangkal dibiarkan lolos.
        kept, skipped = [], 0
        for s in samples:
            parts = s.relative_parent.parts
            if len(parts) >= 3 and re.sub(r'_[0-9]+$', '', parts[2]) not in INCLUDE_PERSONS:
                skipped += 1
                continue
            kept.append(s)
        print(f'INCLUDE_PERSONS: {len(kept)} video diproses, {skipped} dilewati '
              f'({len(INCLUDE_PERSONS)} orang dari {SPOT_INCLUDE_PERSONS})')
        samples = kept
    return samples


def extract_region(image: np.ndarray, landmarks, indices: list[int]) -> np.ndarray:
    pts = [(landmarks.part(i).x, landmarks.part(i).y) for i in indices]
    xs, ys = zip(*pts)
    left = max(0, min(xs) - config.padding_x)
    top = max(0, min(ys) - config.padding_y)
    right = min(image.shape[1], max(xs) + config.padding_x)
    bottom = min(image.shape[0], max(ys) + config.padding_y)
    return image[top:bottom, left:right]


def detect_landmarks(gray: np.ndarray, detector, predictor):
    faces = detector(gray)
    if len(faces) > 0:
        return predictor(gray, faces[0])
    return None


def _hpoc_drop_mean(poc_arr: np.ndarray) -> float:
    """mean(1 - nilai puncak POC) per blok — ukuran ketidakmiripan kontinu.

    Ini fitur M yang sebenarnya di paper Rosiani et al. 2020 (di sana M = Hpoc,
    bukan |V|). Tidak terkuantisasi 1 piksel seperti |V|, jadi membawa sinyal
    sub-piksel yang hilang pada data 30 fps.
    """
    drops = [1.0 - float(poc_arr[:, :, i].max()) for i in range(poc_arr.shape[2])]
    return float(np.mean(drops)) if drops else np.nan


def compute_roi_magnitudes(prev_gray, prev_lm, curr_gray, curr_lm,
                           want_hpoc: bool = False) -> dict:
    """Rata-rata magnitude per ROI (NaN bila ROI gagal — di-interpolasi nanti).

    want_hpoc=True: nilai kembali per ROI = (mean_m, hpoc_drop_mean).
    """
    out = {}
    for region_name, lm_indices in config.regions.items():
        try:
            roi_prev = extract_region(prev_gray, prev_lm, lm_indices)
            roi_curr = extract_region(curr_gray, curr_lm, lm_indices)
            if roi_prev.size == 0 or roi_curr.size == 0:
                out[region_name] = (np.nan, np.nan) if want_hpoc else np.nan
                continue
            target = config.target_size[region_name]
            roi_prev = cv2.resize(roi_prev, target)
            roi_curr = cv2.resize(roi_curr, target)
            poc = POC(roi_prev, roi_curr, config.block_size)
            poc_out = poc.getPOC()
            vec = Vektor(poc_out, config.block_size)
            quad_data = Quadran(vec.getVektor()).getQuadran()
            if SPOT_MOTION_COMP:
                # LEVER 1: kurangi median global (dx, dy) antar blok di ROI ini.
                # quad_data kolom 1 = oX, kolom 2 = oY, kolom 4 = magnitude.
                # Komponen gerakan yang SERENTAK di semua blok = gerakan global
                # (kepala/latar). Mengurangi median menghilangkannya; sisa =
                # deviasi lokal (ekspresi). Magnitude dihitung ulang dari deviasi.
                ox = np.array([float(b[1]) for b in quad_data], dtype=float)
                oy = np.array([float(b[2]) for b in quad_data], dtype=float)
                mdx, mdy = float(np.median(ox)), float(np.median(oy))
                dx = ox - mdx
                dy = oy - mdy
                dev_mag = np.sqrt(dx * dx + dy * dy)
                m = float(np.mean(dev_mag)) if dev_mag.size else np.nan
            else:
                magnitudes = [float(block[4]) for block in quad_data]
                m = float(np.mean(magnitudes)) if magnitudes else np.nan
            out[region_name] = (m, _hpoc_drop_mean(poc_out[0])) if want_hpoc else m
        except Exception:
            out[region_name] = (np.nan, np.nan) if want_hpoc else np.nan
    return out


def load_video_frames(video_path: Path) -> list[np.ndarray]:
    frames = []
    cap = cv2.VideoCapture(str(video_path))
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    cap.release()
    return frames


def iter_video_frames(video_path: Path):
    """Generator: baca frame satu per satu, JANGAN muat seluruh video ke RAM.

    Video CAS(ME)^2 panjangnya sampai 4370 frame 640x480; memuat semuanya
    sebagai list numpy butuh ~4 GB per video. Dengan beberapa worker, itu
    menembus RAM dan proses dibunuh OOM killer. Untuk sinyal saja, frame tidak
    perlu disimpan -- cukup frame acuan + frame saat ini.
    """
    cap = cv2.VideoCapture(str(video_path))
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            yield frame
    finally:
        cap.release()


def count_video_frames(video_path: Path) -> int:
    cap = cv2.VideoCapture(str(video_path))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return n


def _interpolate_signal(values: list[float]) -> list[float]:
    """3.5: interpolasi linier menggantikan nilai 0.0 palsu dari landmark gagal."""
    s = pd.Series(values, dtype=float)
    if s.isna().all():
        return []
    s = s.interpolate(method='linear', limit_direction='both')
    return s.fillna(0.0).tolist()


def _mdmd_difference(values: list[float], k: int) -> list[float]:
    """LEVER 2 (Wang 2017, MDMD): per frame i, sinyal' = sinyal[i] - rata-rata
    tetangga dalam jendela ±k (i-k .. i+k, selain i), di-clip >= 0.

    Intuisi anti-noise: ekspresi adalah puncak LOKAL TAJAM (onset->apex->offset
    cepat) sehingga nilainya jauh di atas tetangga; gerakan kepala/latar adalah
    TREN LAMBAT sehingga nilai frame ≈ rata-rata tetangganya dan selisihnya
    mendekati nol. Didifference menghilangkan tren lambat (gerakan global),
    menyisakan puncak tajam (ekspresi). Setara "maximal difference" MDMD yang
    membandingkan frame saat ini dengan frame head/tail di jendela 2k.
    """
    arr = np.asarray(values, dtype=float)
    n = arr.size
    if n == 0:
        return []
    csum = np.concatenate(([0.0], np.cumsum(arr)))
    out = np.empty(n, dtype=float)
    for i in range(n):
        lo = max(0, i - k)
        hi = min(n, i + k + 1)
        # jumlah tetangga = (hi-lo) frame dikurangi frame i sendiri
        total = csum[hi] - csum[lo] - arr[i]
        cnt = (hi - lo) - 1
        neigh = total / cnt if cnt > 0 else 0.0
        out[i] = arr[i] - neigh
    np.clip(out, 0.0, None, out=out)
    return out.tolist()


def _top_roi_mean(values: list[float], top_rois: int | str) -> float:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return 0.0
    if top_rois == 'mean':
        return float(arr.mean())
    k = max(1, min(int(top_rois), arr.size))
    return float(np.sort(arr)[-k:].mean())


def _smooth_spot_curve(curve: np.ndarray, window: int) -> np.ndarray:
    if curve.size < 5:
        return curve.astype(float, copy=True)
    w = min(window, curve.size - 1 if curve.size % 2 == 0 else curve.size)
    if w % 2 == 0:
        w -= 1
    if w < 5:
        return curve.astype(float, copy=True)
    return savgol_filter(curve, window_length=w, polyorder=min(2, w - 1))


def build_roi_signals(frames, detector, predictor, frame_count: int | None = None):
    """Sinyal magnitude per ROI (panjang N-1, POC-ABS atau frame berurutan).

    `frames` boleh list ATAU generator (lihat `iter_video_frames`). Untuk sinyal
    hanya perlu frame acuan + frame saat ini, jadi frame TIDAK disalin semua ke
    grayscale di awal: dulu `grays = [...]` menambah salinan penuh di samping
    list frame, dan pada video panjang itu sumber OOM. `frame_count` wajib diisi
    kalau `frames` generator (generator tidak punya len).

    SPOT_SIGNAL='mean_m' (default): dict ROI -> sinyal mean |V| (perilaku lama).
    SPOT_SIGNAL='hpoc': dict ROI -> sinyal mean(1-Hpoc).
    SPOT_SIGNAL='combo': tuple (signals_m, signals_h) — kombinasi z-score
        dilakukan di pemanggil (global: build_magnitude_signal; per-ROI:
        process_sample mode roi_signals).
    """
    n_frames = frame_count if frame_count is not None else len(frames)
    if n_frames < 3:
        return {}
    # LEVER 2: mdmd aktif bila SPOT_SIGNAL='mdmd' ATAU SPOT_MDMD=1. Keduanya
    # memakai sinyal dasar mean_m (bukan hpoc), jadi want_hpoc dimatikan.
    use_mdmd = SPOT_MDMD or SPOT_SIGNAL == 'mdmd'
    want_hpoc = SPOT_SIGNAL != 'mean_m' and not use_mdmd
    signals: dict[str, list[float]] = {r: [] for r in config.regions}
    signals_h: dict[str, list[float]] = {r: [] for r in config.regions}
    iterator = iter(frames)
    first = next(iterator)
    if USE_ABS_BASELINE:
        # POC-ABS: setiap frame dibandingkan dengan frame-0 (baseline tetap)
        ref_gray = cv2.cvtColor(first, cv2.COLOR_BGR2GRAY)
        ref_lm = detect_landmarks(ref_gray, detector, predictor)
        for frame in iterator:
            curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            curr_lm = detect_landmarks(curr_gray, detector, predictor)
            if ref_lm is not None and curr_lm is not None:
                roi_mags = compute_roi_magnitudes(ref_gray, ref_lm, curr_gray, curr_lm,
                                                  want_hpoc=want_hpoc)
                for r in config.regions:
                    if want_hpoc:
                        m, h = roi_mags.get(r, (np.nan, np.nan))
                        signals[r].append(float(m))
                        signals_h[r].append(float(h))
                    else:
                        signals[r].append(float(roi_mags.get(r, np.nan)))
            else:
                for r in config.regions:
                    signals[r].append(np.nan)
                    if want_hpoc:
                        signals_h[r].append(np.nan)
    else:
        # Kode asli: frame berurutan (frame N vs N-1)
        prev_gray = cv2.cvtColor(first, cv2.COLOR_BGR2GRAY)
        prev_lm = detect_landmarks(prev_gray, detector, predictor)
        for frame in iterator:
            curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            curr_lm = detect_landmarks(curr_gray, detector, predictor)
            if prev_lm is not None and curr_lm is not None:
                roi_mags = compute_roi_magnitudes(prev_gray, prev_lm, curr_gray, curr_lm,
                                                  want_hpoc=want_hpoc)
                for r in config.regions:
                    if want_hpoc:
                        m, h = roi_mags.get(r, (np.nan, np.nan))
                        signals[r].append(float(m))
                        signals_h[r].append(float(h))
                    else:
                        signals[r].append(float(roi_mags.get(r, np.nan)))
            else:
                for r in config.regions:
                    signals[r].append(np.nan)
                    if want_hpoc:
                        signals_h[r].append(np.nan)
            prev_gray = curr_gray
            prev_lm = curr_lm
    if SPOT_INTERP:
        signals = {r: _interpolate_signal(v) for r, v in signals.items()}
        if want_hpoc:
            signals_h = {r: _interpolate_signal(v) for r, v in signals_h.items()}
    else:
        signals = {r: [0.0 if np.isnan(x) else float(x) for x in v] for r, v in signals.items()}
        if want_hpoc:
            signals_h = {r: [0.0 if np.isnan(x) else float(x) for x in v] for r, v in signals_h.items()}
    if use_mdmd:
        signals = {r: _mdmd_difference(v, SPOT_MDMD_K) for r, v in signals.items()}
        return signals
    if SPOT_SIGNAL == 'hpoc':
        return signals_h
    if SPOT_SIGNAL == 'combo':
        return signals, signals_h
    return signals


def build_global_signal(roi_signals: dict[str, list[float]]) -> list[float]:
    """Sinyal global = mean antar ROI (mode lama)."""
    if not roi_signals or any(len(v) == 0 for v in roi_signals.values()):
        return []
    n = len(next(iter(roi_signals.values())))
    return [float(np.mean([roi_signals[r][i] for r in roi_signals])) for i in range(n)]


def _zscore(values: list[float]) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    sd = float(arr.std())
    return (arr - float(arr.mean())) / sd if sd > 0 else arr * 0.0


def build_magnitude_signal(frames: list[np.ndarray], detector, predictor) -> list[float]:
    roi_signals = build_roi_signals(frames, detector, predictor)
    if SPOT_SIGNAL == 'combo' and isinstance(roi_signals, tuple):
        # Tervalidasi di CAS(ME)^2 86 video (F1 0,3343 vs 0,3192): kombinasi di
        # level GLOBAL (z dari sinyal global), bukan per ROI.
        signals_m, signals_h = roi_signals
        global_m = build_global_signal(signals_m)
        global_h = build_global_signal(signals_h)
        if not global_m or not global_h:
            return []
        n = min(len(global_m), len(global_h))
        return list(_zscore(global_m[:n]) + _zscore(global_h[:n]))
    return build_global_signal(roi_signals)


@dataclass(frozen=True, slots=True)
class DetectParams:
    """Parameter pemilihan event. Field None = pakai nilai global yang sekarang.

    Dipakai agar parameter bisa diuji (mis. benchmark spotting) TANPA mengubah
    perilaku pipeline utama. Pemanggil lama yang tidak mengisi apa pun tetap
    mendapat perilaku yang persis sama.
    """
    top_k: int | None = None
    min_phase_duration: int | None = None
    prom_rel: float | None = None
    distance: int | None = None
    thresh: str | None = None
    ranking: str | None = None


def resolve_detect_params(params: DetectParams | None) -> DetectParams:
    """Isi field None dari konfigurasi/global yang berlaku sekarang."""
    p = params or DetectParams()
    return DetectParams(
        top_k=config.top_k_apex if p.top_k is None else p.top_k,
        min_phase_duration=config.min_phase_duration if p.min_phase_duration is None else p.min_phase_duration,
        prom_rel=SPOT_PROM_REL if p.prom_rel is None else p.prom_rel,
        distance=SPOT_DISTANCE if p.distance is None else p.distance,
        thresh=SPOT_THRESH if p.thresh is None else p.thresh,
        ranking=SPOT_RANKING if p.ranking is None else p.ranking,
    )


def _make_detector(signal_arr: np.ndarray, params: DetectParams) -> ApexPhase:
    """3.6: detector dgn prominence aktif (relatif thd rentang sinyal halus).

    Prominence di-find_peaks harus absolut; kita skala ke rentang sinyal
    supaya puncak noise low-SNR dibuang, bukan hanya sinyal di bawah
    height=mean+std. prom_rel <= 0 => perilaku lama (hampir non-aktif).
    """
    prom = config.prominence_threshold
    if params.prom_rel and params.prom_rel > 0 and len(signal_arr):
        arr = np.asarray(signal_arr, dtype=float)
        spread = float(arr.max() - arr.min())
        prom = max(params.prom_rel * spread, config.prominence_threshold)
    return ApexPhase(
        distance_threshold=params.distance,
        prominence_threshold=prom,
        cutoff_ratio=config.cutoff_ratio,
    )


def _height_threshold(signal_arr: np.ndarray, params: DetectParams) -> float:
    """3.4: 'meanstd' = mean+std; 'mad' = median + 2.5*1.4826*MAD (tahan outlier/noise)."""
    if params.thresh == 'mad':
        med = float(np.median(signal_arr))
        mad = float(np.median(np.abs(signal_arr - med)))
        return med + 2.5 * (1.4826 * mad)
    return float(signal_arr.mean() + signal_arr.std())


def detect_events(magnitudes: list[float], params: DetectParams | None = None) -> tuple[list[float], list[dict], dict]:
    p = resolve_detect_params(params)
    smoothed = ApexSmoother.smooth(magnitudes)
    signal_arr = np.asarray(smoothed, dtype=float)
    height_threshold = _height_threshold(signal_arr, p)
    detector = _make_detector(signal_arr, p)
    apex_indices = detector.find_top_k_apex(smoothed, k=p.top_k, height=height_threshold,
                                            ranking=p.ranking)
    phases = detector.find_phase(smoothed, apex_indices) if apex_indices else {}
    events = []
    for event_no, apex_idx in enumerate(apex_indices, start=1):
        phase = phases[apex_idx]
        duration = int(phase['end'] - phase['start'])
        if duration < p.min_phase_duration:
            continue
        events.append({
            'event_no': event_no,
            'onset_signal': int(phase['start']),
            'apex_signal': int(apex_idx),
            'offset_signal': int(phase['end']),
            'duration': duration,
            'region': 'global',
        })
    window_length = ApexSmoother.calculate_window_length(len(magnitudes))
    meta = {
        'window_length': window_length,
        'polyorder': ApexSmoother.calculate_polyorder(window_length),
        'height_threshold': height_threshold,
    }
    return smoothed, events, meta


def detect_events_per_roi(
    roi_signals: dict[str, list[float]],
    params: DetectParams | None = None,
) -> tuple[dict[str, list[float]], list[dict], dict]:
    """3.2+3.4: apex dideteksi per ROI dgn threshold per ROI; event overlap digabung
    (ambil apex_value tertinggi), lalu diurutkan onset.

    `params` mengizinkan pengujian parameter tanpa mengubah default pipeline;
    None = perilaku lama persis.
    """
    p = resolve_detect_params(params)
    candidates: list[dict] = []
    smoothed_map: dict[str, list[float]] = {}
    thresholds: list[float] = []
    n_signals = None
    for region, signal in roi_signals.items():
        n_signals = len(signal)
        smoothed_map[region] = []
        if len(signal) < 3:
            continue
        smoothed = ApexSmoother.smooth(signal)
        smoothed_map[region] = smoothed
        signal_arr = np.asarray(smoothed, dtype=float)
        height = _height_threshold(signal_arr, p)
        thresholds.append(height)
        detector = _make_detector(signal_arr, p)
        apex_indices = detector.find_top_k_apex(smoothed, k=p.top_k, height=height,
                                                ranking=p.ranking)
        if not apex_indices:
            continue
        # Skor dedup HARUS bebas skala ROI. Magnitudo mulut jauh lebih besar dari
        # alis/mata, jadi membandingkan `apex_value` MENTAH lintas ROI selalu
        # memenangkan mulut dan menenggelamkan micro-expression alis (AU1/AU2/AU4).
        # z-score di dalam sinyal ROI itu sendiri = "seberapa luar biasa puncak ini
        # menurut skala ROI-nya", sehingga antar ROI jadi sebanding.
        mu = float(signal_arr.mean())
        sd = float(signal_arr.std())
        phases = detector.find_phase(smoothed, apex_indices)
        for apex_idx in apex_indices:
            phase = phases.get(apex_idx)
            if phase is None:
                continue
            duration = int(phase['end'] - phase['start'])
            if duration < p.min_phase_duration:
                continue
            apex_value = float(smoothed[apex_idx])
            candidates.append({
                'region': region,
                'onset_signal': int(phase['start']),
                'apex_signal': int(apex_idx),
                'offset_signal': int(phase['end']),
                'duration': duration,
                'apex_value': apex_value,
                'apex_z': (apex_value - mu) / sd if sd > 0 else 0.0,
            })

    candidates.sort(key=lambda e: e['apex_z'], reverse=True)
    kept: list[dict] = []
    for cand in candidates:
        overlap = any(
            cand['onset_signal'] <= k['offset_signal'] and k['onset_signal'] <= cand['offset_signal']
            for k in kept
        )
        if not overlap:
            kept.append(cand)
    kept.sort(key=lambda e: e['onset_signal'])

    events = []
    for event_no, e in enumerate(kept, start=1):
        events.append({
            'event_no': event_no,
            'onset_signal': e['onset_signal'],
            'apex_signal': e['apex_signal'],
            'offset_signal': e['offset_signal'],
            'duration': e['duration'],
            # Region disimpan supaya asal-usul event bisa diaudit (dan supaya
            # dedup lintas-ROI yang baru bisa diverifikasi, bukan cuma dipercaya).
            'region': e['region'],
        })
    window_length = ApexSmoother.calculate_window_length(n_signals or 0)
    meta = {
        'window_length': window_length,
        'polyorder': ApexSmoother.calculate_polyorder(window_length),
        'height_threshold': float(np.mean(thresholds)) if thresholds else None,
    }
    return smoothed_map, events, meta


def _signal_index_to_event(signal_index: int, curve: np.ndarray, width: int,
                           boundary_beta: float | None) -> dict:
    half = max(1, width // 2)
    start = max(0, signal_index - half)
    end = min(curve.size - 1, signal_index + half)
    if boundary_beta is not None and curve.size:
        base = float(np.median(curve))
        level = base + boundary_beta * max(float(curve[signal_index]) - base, 0.0)
        left = signal_index
        while left > start and curve[left - 1] >= level:
            left -= 1
        right = signal_index
        while right < end and curve[right + 1] >= level:
            right += 1
        start, end = left, right
    return {
        'onset_signal': int(start),
        'apex_signal': int(signal_index),
        'offset_signal': int(end),
        'duration': int(end - start),
        'region': 'of_fd_proxy',
        'score': float(curve[signal_index]),
    }


def _event_iou(a: dict, b: dict) -> float:
    inter = min(a['offset_signal'], b['offset_signal']) - max(a['onset_signal'], b['onset_signal']) + 1
    if inter <= 0:
        return 0.0
    union = max(a['offset_signal'], b['offset_signal']) - min(a['onset_signal'], b['onset_signal']) + 1
    return inter / union if union > 0 else 0.0


def detect_events_of_fd_proxy(roi_signals: dict[str, list[float]]) -> tuple[list[float], list[dict], dict]:
    """Precision-first OF-FD proxy from the CAS(ME)^2 paper-config sweep.

    Uses existing POC-ABS ROI curves instead of dense optical flow; this is for
    downstream A/B only, not a claim to reproduce OF-FD literature numbers.
    """
    top_rois: int | str = SPOT_OF_FD_TOP if SPOT_OF_FD_TOP == 'mean' else int(SPOT_OF_FD_TOP)
    keys = sorted(roi_signals)
    n = min((len(roi_signals[r]) for r in keys), default=0)
    curve = np.zeros(n, dtype=float)
    for i in range(n):
        curve[i] = _top_roi_mean([roi_signals[r][i] for r in keys], top_rois)
    curve = _smooth_spot_curve(curve, SPOT_OF_FD_SMOOTH)
    med = float(np.median(curve)) if curve.size else 0.0
    mad = float(np.median(np.abs(curve - med))) if curve.size else 0.0
    threshold = med + SPOT_OF_FD_MAD * 1.4826 * mad
    peaks, props = find_peaks(curve, height=threshold, distance=max(1, SPOT_OF_FD_DISTANCE))
    heights = props.get('peak_heights', curve[peaks]) if peaks.size else np.empty(0)
    events = [_signal_index_to_event(int(peaks[i]), curve, SPOT_OF_FD_WIDTH, SPOT_OF_FD_BOUNDARY_BETA)
              for i in np.argsort(-heights)]
    kept: list[dict] = []
    for event in sorted(events, key=lambda e: -e['score']):
        if all(_event_iou(event, old) < 0.5 for old in kept):
            kept.append(event)
    kept.sort(key=lambda e: e['onset_signal'])
    for event_no, event in enumerate(kept, start=1):
        event['event_no'] = event_no
        event.pop('score', None)
    meta = {
        'window_length': SPOT_OF_FD_SMOOTH,
        'polyorder': 2,
        'height_threshold': threshold,
    }
    return curve.tolist(), kept, meta


def signal_index_to_frame_index(signal_index: int) -> int:
    return int(signal_index + 1)


def save_neutral_reference(frames: list[np.ndarray], sample_output_dir: Path) -> Path | None:
    """Simpan acuan netral per sample: median piksel SPOT_NEUTRAL_FRAMES frame pertama.

    Baseline POC-ABS sebelumnya = frame onset klip, dan klip disimpan mulai
    onset (`save_event_clip_frames`), jadi ototnya sudah mulai berkontraksi.
    Median beberapa frame awal video mendekati wajah netral per orang dan
    menekan noise sensor.
    """
    n = min(SPOT_NEUTRAL_FRAMES, len(frames))
    if n <= 0:
        return None
    neutral = np.median(np.stack(frames[:n]).astype(np.float32), axis=0).astype(np.uint8)
    ensure_dir(sample_output_dir)
    path = sample_output_dir / 'neutral.png'
    cv2.imwrite(str(path), neutral)
    return path


def save_event_clip_frames(frames: list[np.ndarray], sample_output_dir: Path, events: list[dict]) -> list[dict]:
    ensure_dir(sample_output_dir)
    rows = []
    for event in events:
        onset_frame = min(signal_index_to_frame_index(event['onset_signal']), len(frames) - 1)
        apex_frame = min(signal_index_to_frame_index(event['apex_signal']), len(frames) - 1)
        offset_frame = min(signal_index_to_frame_index(event['offset_signal']), len(frames) - 1)
        clip_dir = sample_output_dir / f"event_{onset_frame:05d}-{offset_frame:05d}_{event['region']}"
        ensure_dir(clip_dir)
        for write_idx, frame_idx in enumerate(range(onset_frame, offset_frame + 1)):
            if frame_idx == apex_frame:
                out_path = clip_dir / f'frame_{write_idx:05d}-apex.png'
            else:
                out_path = clip_dir / f'frame_{write_idx:05d}.jpg'
            cv2.imwrite(str(out_path), frames[frame_idx])
        rows.append({
            'relative_sample': str(sample_output_dir.relative_to(config.output_dataset_root)),
            'event_no': event['event_no'],
            'onset_signal': event['onset_signal'],
            'apex_signal': event['apex_signal'],
            'offset_signal': event['offset_signal'],
            'onset_frame': onset_frame,
            'apex_frame': apex_frame,
            'offset_frame': offset_frame,
            'duration': event['duration'],
            'saved_frames': offset_frame - onset_frame + 1,
            'region': event['region'],
            'clip_dir': str(clip_dir.relative_to(config.output_root)),
        })
    return rows


def rebuild_metadata_rows(sample_output_dir: Path, source_video: str) -> list[dict]:
    """Buat baris metadata dari klip event yang SUDAH tersimpan (kasus resume).

    Tanpa ini, sample yang di-skip (output sudah ada) tidak masuk metadata,
    sehingga metadata.xlsx hanya berisi sample yang diproses fresh pada run
    terakhir -> fitur/ekspor menjadi tidak lengkap.
    """
    rows = []
    event_dirs = sorted(
        [p for p in sample_output_dir.iterdir() if p.is_dir() and p.name.startswith('event_')],
        key=lambda p: natural_sort_key(p.name),
    )
    for event_no, event_dir in enumerate(event_dirs, start=1):
        # Region opsional di akhiran nama: `event_00015-00032_mulut`. Klip lama
        # (sebelum dedup lintas-ROI diperbaiki) tidak punya sufiks -> None.
        m = re.fullmatch(r'event_(\d+)-(\d+)(?:_(.+))?', event_dir.name)
        if m is None:
            continue
        onset_frame, offset_frame = int(m.group(1)), int(m.group(2))
        region = m.group(3)
        apex_files = [f for f in event_dir.iterdir() if f.name.endswith('-apex.png')]
        if not apex_files:
            continue  # klip tidak lengkap (mis. run terputus saat menulis)
        # nama file apex = indeks relatif-klip; metadata memakai frame absolut
        apex_rel = int(re.fullmatch(r'frame_(\d+)-apex\.png', apex_files[0].name).group(1))
        apex_frame = onset_frame + apex_rel
        rows.append({
            'relative_sample': str(sample_output_dir.relative_to(config.output_dataset_root)),
            'source_video': source_video,
            'event_no': event_no,
            'onset_signal': onset_frame - 1,
            'apex_signal': apex_frame - 1,
            'offset_signal': offset_frame - 1,
            'onset_frame': onset_frame,
            'apex_frame': apex_frame,
            'offset_frame': offset_frame,
            'duration': offset_frame - onset_frame + 1,
            'saved_frames': offset_frame - onset_frame + 1,
            'region': region,
            'window_length': None,
            'polyorder': None,
            'height_threshold': None,
            'clip_dir': str(event_dir.relative_to(config.output_root)),
        })
    return rows


def process_sample(sample: VideoSample) -> dict:
    detector = WORKER_DETECTOR
    predictor = WORKER_PREDICTOR
    relative_key = sample.relative_video_key
    sample_output_dir = config.output_dataset_root / relative_key

    if sample_output_dir.exists() and not config.overwrite:
        return {
            'status': 'skip',
            'relative_key': str(relative_key),
            'rows': rebuild_metadata_rows(sample_output_dir, str(sample.video_path)),
            'reason': 'exists',
        }

    if sample_output_dir.exists() and config.overwrite:
        shutil.rmtree(sample_output_dir)

    frames = load_video_frames(sample.video_path)
    if len(frames) < 3:
        return {
            'status': 'skip',
            'relative_key': str(relative_key),
            'rows': [],
            'reason': f'too few frames ({len(frames)})',
        }

    if SPOT_SAVE_NEUTRAL:
        save_neutral_reference(frames, sample_output_dir)

    if SPOT_ALGO == 'of_fd_proxy':
        roi_signals = build_roi_signals(frames, detector, predictor)
        if isinstance(roi_signals, tuple):
            roi_signals = roi_signals[0]
        if not roi_signals or any(len(v) < 5 for v in roi_signals.values()):
            return {
                'status': 'skip',
                'relative_key': str(relative_key),
                'rows': [],
                'reason': 'too few magnitudes',
            }
        try:
            _curve, events, meta = detect_events_of_fd_proxy(roi_signals)
        except ValueError as e:
            return {
                'status': 'skip',
                'relative_key': str(relative_key),
                'rows': [],
                'reason': str(e),
            }
    elif SPOT_SIGNAL_MODE == 'roi_signals':
        roi_signals = build_roi_signals(frames, detector, predictor)
        if SPOT_SIGNAL == 'combo' and isinstance(roi_signals, tuple):
            # Varian per-ROI (lebih lemah dari combo global — 0,3113 vs 0,3343
            # di CAS(ME)^2): z(mean_m) + z(hpoc) di dalam tiap ROI.
            signals_m, signals_h = roi_signals
            roi_signals = {r: list(_zscore(signals_m[r]) + _zscore(signals_h[r]))
                           for r in signals_m}
        if not roi_signals or any(len(v) < 5 for v in roi_signals.values()):
            return {
                'status': 'skip',
                'relative_key': str(relative_key),
                'rows': [],
                'reason': 'too few magnitudes',
            }
        try:
            _smoothed_map, events, meta = detect_events_per_roi(roi_signals)
        except ValueError as e:
            return {
                'status': 'skip',
                'relative_key': str(relative_key),
                'rows': [],
                'reason': str(e),
            }
    else:
        magnitudes = build_magnitude_signal(frames, detector, predictor)
        if len(magnitudes) < 5:
            return {
                'status': 'skip',
                'relative_key': str(relative_key),
                'rows': [],
                'reason': f'too few magnitudes ({len(magnitudes)})',
            }
        try:
            _smoothed, events, meta = detect_events(magnitudes)
        except ValueError as e:
            return {
                'status': 'skip',
                'relative_key': str(relative_key),
                'rows': [],
                'reason': str(e),
            }

    rows = save_event_clip_frames(frames, sample_output_dir, events)
    metadata_rows = []
    if not rows:
        metadata_rows.append({
            'relative_sample': str(relative_key),
            'source_video': str(sample.video_path),
            'event_no': None,
            'onset_signal': None,
            'apex_signal': None,
            'offset_signal': None,
            'onset_frame': None,
            'apex_frame': None,
            'offset_frame': None,
            'duration': None,
            'saved_frames': 0,
            'window_length': meta['window_length'],
            'polyorder': meta['polyorder'],
            'height_threshold': meta['height_threshold'],
            'clip_dir': None,
        })
    else:
        for row in rows:
            metadata_rows.append({
                'relative_sample': row['relative_sample'],
                'source_video': str(sample.video_path),
                'event_no': row['event_no'],
                'onset_signal': row['onset_signal'],
                'apex_signal': row['apex_signal'],
                'offset_signal': row['offset_signal'],
                'onset_frame': row['onset_frame'],
                'apex_frame': row['apex_frame'],
                'offset_frame': row['offset_frame'],
                'duration': row['duration'],
                'saved_frames': row['saved_frames'],
                'region': row.get('region'),
                'window_length': meta['window_length'],
                'polyorder': meta['polyorder'],
                'height_threshold': meta['height_threshold'],
                'clip_dir': row['clip_dir'],
            })

    del frames
    gc.collect()
    return {
        'status': 'processed',
        'relative_key': str(relative_key),
        'rows': metadata_rows,
        'reason': None,
    }


# In[4]:


def rebuild_metadata_from_clips(output_dataset_root: Path, raw_root: Path) -> pd.DataFrame:
    """Bangun ulang metadata HANYA dari klip event yang sudah tersimpan.

    Dipakai kalau metadata.xlsx hilang/rusak padahal klipnya masih ada. Tidak
    butuh video mentah dan tidak menghitung ulang sinyal: nama direktori klip
    sudah memuat onset/offset, dan nama berkas `*-apex.png` memuat apex.

    `raw_root` hanya dipakai untuk mengisi kolom `source_video` (informasional);
    kolom itu TIDAK dipakai hilir, jadi tidak masalah kalau drivnya sedang
    tidak ter-mount.
    """
    rows: list[dict] = []
    sample_dirs = sorted(p for p in output_dataset_root.glob('*/*/*/*/*') if p.is_dir())
    for sample_dir in sample_dirs:
        rel = sample_dir.relative_to(output_dataset_root)
        rows.extend(rebuild_metadata_rows(sample_dir, str(raw_root / f'{rel}.avi')))
    return pd.DataFrame(rows)


# In[5]:


# CATATAN: blok eksekusi spotting dulu berjalan di level MODUL, sehingga
# `import process_spotting_pipeline` langsung menulis metadata.xlsx/klip (pernah
# menghapus metadata saat diimpor tak sengaja). Sekarang dipindah ke main() di
# akhir file; import modul ini hanya mendefinisikan fungsi + config.


# In[6]:


def export_event_signals(samples) -> None:
    """Simpan sinyal per video (xlsx + plot). Dipakai untuk analisis/visual saja;
    dilewati bila SPOT_NO_EVENT_SIGNAL=1 (tidak dipakai hilir, hemat ~separuh waktu)."""
    if SPOT_NO_EVENT_SIGNAL:
        print('Event signals: SKIPPED (SPOT_NO_EVENT_SIGNAL=1)')
        return

    event_signal_root = config.output_root / 'event_signals'
    ensure_dir(event_signal_root)

    signal_rows = []
    visualizer = ApexPhaseVisualizer()

    for sample in tqdm(samples, desc='Event signals', unit='video'):
        relative_key = sample.relative_video_key
        signal_path = event_signal_root / relative_key.with_suffix('.xlsx')
        plot_path = event_signal_root / relative_key.with_suffix('.png')

        if signal_path.exists() and plot_path.exists() and not config.overwrite:
            print(f'skip {relative_key}: event signal exists')
            continue

        frames = load_video_frames(sample.video_path)
        if len(frames) < 3:
            print(f'skip {relative_key}: too few frames ({len(frames)})')
            continue

        detector = dlib.get_frontal_face_detector()
        predictor = dlib.shape_predictor(str(config.predictor_path))
        magnitudes = build_magnitude_signal(frames, detector, predictor)
        if len(magnitudes) < 5:
            print(f'skip {relative_key}: too few magnitudes ({len(magnitudes)})')
            continue

        try:
            smoothed, events, meta = detect_events(magnitudes)
        except ValueError as e:
            print(f'skip {relative_key}: {e}')
            continue

        event_by_apex = {event['apex_signal']: event for event in events}
        phases = {
            event['apex_signal']: {'start': event['onset_signal'], 'end': event['offset_signal']}
            for event in events
        }
        apex_indices = list(event_by_apex)

        rows = []
        for idx, (raw_value, smooth_value) in enumerate(zip(magnitudes, smoothed)):
            event = event_by_apex.get(idx)
            marker = ''
            event_no = None
            if event is not None:
                marker = 'apex'
                event_no = event['event_no']
            else:
                for candidate in events:
                    if idx == candidate['onset_signal']:
                        marker = 'onset'
                        event_no = candidate['event_no']
                        break
                    if idx == candidate['offset_signal']:
                        marker = 'offset'
                        event_no = candidate['event_no']
                        break
            rows.append({
                'relative_sample': str(relative_key),
                'source_video': str(sample.video_path),
                'signal_index': idx,
                'frame_index': signal_index_to_frame_index(idx),
                'raw_magnitude': raw_value,
                'smoothed_magnitude': smooth_value,
                'height_threshold': meta['height_threshold'],
                'event_marker': marker,
                'event_no': event_no,
            })

        signal_path.parent.mkdir(parents=True, exist_ok=True)
        plot_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_excel(signal_path, index=False)

        if apex_indices:
            visualizer.plot_phases(
                signal=smoothed,
                apex_indices=apex_indices,
                phases=phases,
                title=f'Micro-Expression Spotting: {relative_key}',
                save_path=str(plot_path),
            )

        signal_rows.append({
            'relative_sample': str(relative_key),
            'source_video': str(sample.video_path),
            'signal_excel': str(signal_path.relative_to(config.output_root)),
            'plot_path': str(plot_path.relative_to(config.output_root)) if apex_indices else None,
            'total_frames': len(frames),
            'total_magnitudes': len(magnitudes),
            'event_count': len(events),
            'window_length': meta['window_length'],
            'polyorder': meta['polyorder'],
            'height_threshold': meta['height_threshold'],
        })
        print(f'saved {relative_key}: {len(events)} events -> {signal_path}')

    signal_index_df = pd.DataFrame(signal_rows)
    signal_index_path = event_signal_root / 'index.xlsx'
    signal_index_df.to_excel(signal_index_path, index=False)
    print(f'Saved event signal index: {signal_index_path}')
    return signal_index_df


def main() -> None:
    """Spotting penuh: video mentah -> klip event + metadata.xlsx."""
    if SPOT_REBUILD_METADATA_ONLY:
        print('REBUILD METADATA SAJA: dari klip yang sudah ada, tanpa video mentah')
        ensure_dir(config.output_root)
        rebuilt = rebuild_metadata_from_clips(config.output_dataset_root, config.dataset_root)
        if rebuilt.empty:
            raise SystemExit(f'Tidak ada klip event di {config.output_dataset_root}')
        rebuilt.to_excel(config.metadata_path, index=False)
        print(f'Saved metadata: {config.metadata_path}')
        print(f'  baris: {len(rebuilt)} | sample: {rebuilt["relative_sample"].nunique()}')
        return

    if not config.dataset_root.exists():
        raise FileNotFoundError(f'Dataset root not found: {config.dataset_root}')
    if not config.predictor_path.exists():
        raise FileNotFoundError(f'Predictor not found: {config.predictor_path}')

    ensure_dir(config.output_root)
    ensure_dir(config.output_dataset_root)
    samples = discover_video_samples(config.dataset_root, config.video_extensions)
    print(f'Found {len(samples)} video files')

    metadata_rows = []
    predictor_path = str(config.predictor_path)
    with ProcessPoolExecutor(
        max_workers=max_workers,
        initializer=init_worker,
        initargs=(predictor_path,),
    ) as executor:
        futures = {executor.submit(process_sample, sample): sample for sample in samples}
        completed = 0
        for future in tqdm(as_completed(futures), total=len(samples), desc='Spotting', unit='video'):
            sample = futures[future]
            relative_key = sample.relative_video_key
            completed += 1
            try:
                result = future.result()
            except Exception as e:
                print(f'[{completed}/{len(samples)}] fail {relative_key}: {e}')
                continue

            if result['status'] == 'skip' and not result['rows']:
                continue

            metadata_rows.extend(result['rows'])

    metadata_df = pd.DataFrame(metadata_rows)
    metadata_df.to_excel(config.metadata_path, index=False)
    print(f'Saved metadata: {config.metadata_path}')
    print(metadata_df.head())
    export_event_signals(samples)


if __name__ == '__main__':
    main()

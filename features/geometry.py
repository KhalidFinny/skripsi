"""Deskriptor geometri wajah + head pose dari 68 landmark dlib.

SATU-SATUNYA sumber kebenaran untuk keluarga fitur geometri. Dipakai oleh
`pipeline/stages/stage_2_extract_features.py --with-geometry`.

Latar: fitur POC-ABS mengkodekan IDENTITAS lebih kuat daripada kondisi (varian
antar subjek > varian dalam subjek), sehingga LOSO jatuh ke level acak. Ini
keluarga fitur KEDUA yang dipilih dari literatur:

  - AnxietyFaceTrack, IEEE TAFFC 2026 (N=91, kamera ponsel): 3D landmark
    88-91%, head pose 85-89,7%, action unit 59-73%, gaze 53%. Kontributor
    utama: rotasi kepala sumbu-x, landmark tepi wajah, landmark mata.
  - StressGAT, arXiv:2607.20819 (58 peserta, LOSO 88,62%): mekanisme intinya
    "Differential Action Units" -- fitur dinormalkan terhadap baseline NETRAL
    tiap orang, supaya ciri anatomi permanen tidak tertukar dengan sinyal.
  - Giannakakis et al., Biomed. Signal Process. Control 2017 / IEEE BHI 2018:
    mobilitas dan kecepatan kepala naik saat stres.
  - Rumahorbo et al., Commun. Math. Biol. Neurosci. 2025 (BINUS): kelopak
    mata, jarak bibir atas-bawah, panjang/tinggi bibir = fitur yang relevan.
  - Ghimire et al. 2013 / arXiv:2506.17191: displacement dari netral lebih
    informatif daripada posisi absolut.

Karena itu semua fitur STATIS (STATIC_COLS) diskala oleh jarak inter-okular
lalu dikurangi nilai netral subjek (`differential`). Fitur KECEPATAN
(VELOCITY_COLS) tidak dikurangi karena sudah berupa selisih antar frame.

Konvensi indeks landmark mengikuti `features/roi_config.py`:
mata/alis "kiri" = sisi KIRI dari sudut pandang penonton (dlib 36-41 / 17-21),
"kanan" = 42-47 / 22-26.

Semua nilai selalu finite (tidak ada NaN): head pose jatuh ke proyeksi
geometris (`_head_pose_proxy`) kalau solvePnP gagal, sehingga tidak muncul
lonjakan palsu di fitur kecepatan.
"""

from __future__ import annotations

import math

import cv2
import numpy as np

# Prefiks semua kolom. Dipakai untuk memisahkan keluarga fitur ini dari POC-ABS,
# mis. `--drop-features "_max_m$|^geo_"` = POC-ABS saja (hasil lama).
GEO_PREFIX = 'geo_'

_EYE_OUTER_KIRI = 36
_EYE_OUTER_KANAN = 45
_CHIN = 8
_NOSE_TIP = 30
_INNER_BROW_KIRI = 21
_INNER_BROW_KANAN = 22

# 6 titik acuan head pose + model 3D generik (mm), urutan harus sama.
_POSE_IDX = [30, 8, 36, 45, 48, 54]
_POSE_MODEL_3D = np.array(
    [
        (0.0, 0.0, 0.0),        # 30 ujung hidung
        (0.0, -63.6, -12.5),    # 8 dagu
        (-43.3, 32.7, -26.0),   # 36 sudut luar mata kiri (penonton)
        (43.3, 32.7, -26.0),    # 45 sudut luar mata kanan
        (-28.9, -28.9, -24.1),  # 48 sudut mulut kiri
        (28.9, -28.9, -24.1),   # 54 sudut mulut kanan
    ],
    dtype=np.float64,
)

# Acuan frontal untuk sudut Euler: model memakai +Y ke atas, citra memakai +Y ke
# bawah, jadi rotasi wajah frontal adalah 180 derajat terhadap sumbu X. Sudut
# dinyatakan relatif terhadap acuan ini supaya kontinu (lihat _head_pose_pnp).
_FRONTAL_REFERENCE = np.diag([1.0, -1.0, -1.0])


def normalize_roll(roll_deg: float) -> float:
    """Lipat roll ke (-90, 90].

    solvePnP dengan model wajah yang hampir planar punya DUA solusi kembar untuk
    wajah hampir frontal: solusi benar dan solusi yang terbalik 180 derajat pada
    roll (pitch/yaw hampir sama). Ambiguitas ini nyata di data ini: 9 dari 10
    neutral.png subjek abdillah_agil_arbiansyah memberi roll ~0, satu sample
    memberi +179,66 -- orang yang sama, sesi yang sama, wajah yang sama.

    Kalau tidak dinormalkan, pengurangan diferensial (frame - baseline) berubah
    jadi lonjakan ~180-360 derajat dan merusak geo_roll, geo_d_roll, serta
    geo_head_motion. Terukur sebelum perbaikan: 1.472 baris (1,46%) dengan
    |roll| > 170, terkonsentrasi di 5 subjek (sampai 20% frame mereka), dan
    geo_head_motion mencapai 359,86 derajat/frame.

    Wajah manusia dalam wawancara tidak pernah terbalik, jadi melipat roll ke
    (-90, 90] adalah kendala yang sah, bukan tambalan.
    """
    if abs(roll_deg) > 90.0:
        return roll_deg - math.copysign(180.0, roll_deg)
    return roll_deg

STATIC_COLS = [
    'geo_ear_kiri',
    'geo_ear_kanan',
    'geo_ear_mean',
    'geo_mar',
    'geo_mouth_open',
    'geo_mouth_width',
    'geo_lip_corner_drop',
    'geo_brow_eye_kiri',
    'geo_brow_eye_kanan',
    'geo_brow_gap',
    'geo_jaw_width',
    'geo_pitch',
    'geo_yaw',
    'geo_roll',
    'geo_eye_line_roll',
]

VELOCITY_COLS = [
    'geo_d_ear_mean',
    'geo_d_mar',
    'geo_d_pitch',
    'geo_d_yaw',
    'geo_d_roll',
    'geo_head_motion',
]

ALL_COLS = STATIC_COLS + VELOCITY_COLS


def _eye_aspect_ratio(eye: np.ndarray) -> float:
    """EAR Soukupova & Cech: (|p1-p5| + |p2-p4|) / (2*|p0-p3|) pada 6 titik mata."""
    horizontal = float(np.linalg.norm(eye[0] - eye[3]))
    if horizontal <= 1e-6:
        return 0.0
    return float((np.linalg.norm(eye[1] - eye[5]) + np.linalg.norm(eye[2] - eye[4])) / (2.0 * horizontal))


def _head_pose_pnp(landmarks: np.ndarray, image_shape: tuple[int, ...]) -> dict[str, float] | None:
    """Pitch/yaw/roll (derajat) dari solvePnP. None kalau gagal.

    Model 3D memakai +Y KE ATAS sementara citra memakai +Y ke bawah, jadi rotasi
    yang cocok untuk wajah frontal adalah 180 derajat terhadap sumbu X. Kalau
    sudut diambil apa adanya, pitch duduk di +/-180 dan MENYEBABKAN LONJAKAN 360
    derajat begitu wajah melewati titik itu (fitur kecepatan jadi sampah).
    Karena itu rotasi dinyatakan relatif terhadap acuan frontal R_ref = rotasi
    180 derajat sumbu X: `R_ref @ R` bernilai ~0 untuk wajah frontal, sehingga
    sudutnya kontinu. Konvensi Euler: x=pitch, y=yaw, z=roll.
    """
    height, width = int(image_shape[0]), int(image_shape[1])
    image_points = np.asarray([landmarks[i] for i in _POSE_IDX], dtype=np.float64)
    camera = np.array(
        [
            [float(width), 0.0, width / 2.0],
            [0.0, float(width), height / 2.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    try:
        ok, rvec, _ = cv2.solvePnP(
            _POSE_MODEL_3D, image_points, camera, np.zeros((4, 1)), flags=cv2.SOLVEPNP_ITERATIVE
        )
        if not ok:
            return None
        rotation, _ = cv2.Rodrigues(rvec)
    except cv2.error:
        return None
    if not np.all(np.isfinite(rotation)):
        return None
    rotation = _FRONTAL_REFERENCE @ rotation
    sy = math.sqrt(rotation[0, 0] ** 2 + rotation[1, 0] ** 2)
    if sy < 1e-6:
        pitch = math.atan2(-rotation[1, 2], rotation[1, 1])
        yaw = math.atan2(-rotation[2, 0], sy)
        roll = 0.0
    else:
        pitch = math.atan2(rotation[2, 1], rotation[2, 2])
        yaw = math.atan2(-rotation[2, 0], sy)
        roll = math.atan2(rotation[1, 0], rotation[0, 0])
    return {
        'geo_pitch': math.degrees(pitch),
        'geo_yaw': math.degrees(yaw),
        'geo_roll': normalize_roll(math.degrees(roll)),
    }


def _head_pose_proxy(landmarks: np.ndarray, iod: float) -> dict[str, float]:
    """Cadangan geometris tanpa solvePnP: selalu terdefinisi, satuan DERAJAT.

    Satuannya sengaja dibuat sama dengan jalur solvePnP supaya frame yang jatuh
    ke cadangan tidak melompat skala.
    """
    eye_y = float(np.mean(landmarks[36:48, 1]))
    eye_x = float(np.mean(landmarks[[_EYE_OUTER_KIRI, _EYE_OUTER_KANAN], 0]))
    chin_y = float(landmarks[_CHIN, 1])
    nose_x, nose_y = float(landmarks[_NOSE_TIP, 0]), float(landmarks[_NOSE_TIP, 1])
    return {
        'geo_pitch': math.degrees(math.atan2(nose_y - eye_y, max(chin_y - eye_y, 1e-6))),
        'geo_yaw': math.degrees(math.atan2(nose_x - eye_x, iod)),
        'geo_roll': _eye_line_roll(landmarks),
    }


def _eye_line_roll(landmarks: np.ndarray) -> float:
    """Kemiringan garis mata (derajat) -- proksi roll yang tidak butuh solvePnP."""
    dy = float(landmarks[_EYE_OUTER_KANAN, 1] - landmarks[_EYE_OUTER_KIRI, 1])
    dx = float(landmarks[_EYE_OUTER_KANAN, 0] - landmarks[_EYE_OUTER_KIRI, 0])
    return normalize_roll(math.degrees(math.atan2(dy, dx)))


def extract_geometry(landmarks: np.ndarray, image_shape: tuple[int, ...]) -> dict[str, float]:
    """Fitur statis (STATIC_COLS) dari satu frame. Sudah bebas skala identitas."""
    landmarks = np.asarray(landmarks, dtype=np.float64)
    iod = float(np.linalg.norm(landmarks[_EYE_OUTER_KIRI] - landmarks[_EYE_OUTER_KANAN]))
    iod = max(iod, 1e-6)

    ear_kiri = _eye_aspect_ratio(landmarks[36:42])
    ear_kanan = _eye_aspect_ratio(landmarks[42:48])

    mouth_width = float(np.linalg.norm(landmarks[48] - landmarks[54])) / iod
    mouth_open = float(np.mean(landmarks[64:67, 1]) - np.mean(landmarks[61:64, 1])) / iod
    lip_center_y = float(np.mean([landmarks[51, 1], landmarks[57, 1]]))
    lip_corner_y = float(np.mean([landmarks[48, 1], landmarks[54, 1]]))

    pose = _head_pose_pnp(landmarks, image_shape) or _head_pose_proxy(landmarks, iod)

    return {
        'geo_ear_kiri': ear_kiri,
        'geo_ear_kanan': ear_kanan,
        'geo_ear_mean': (ear_kiri + ear_kanan) / 2.0,
        'geo_mar': mouth_open / mouth_width if mouth_width > 1e-6 else 0.0,
        'geo_mouth_open': mouth_open,
        'geo_mouth_width': mouth_width,
        'geo_lip_corner_drop': (lip_corner_y - lip_center_y) / iod,
        'geo_brow_eye_kiri': float(np.mean(landmarks[36:42, 1]) - np.mean(landmarks[17:22, 1])) / iod,
        'geo_brow_eye_kanan': float(np.mean(landmarks[42:48, 1]) - np.mean(landmarks[22:27, 1])) / iod,
        'geo_brow_gap': float(np.linalg.norm(landmarks[_INNER_BROW_KIRI] - landmarks[_INNER_BROW_KANAN])) / iod,
        'geo_jaw_width': float(np.linalg.norm(landmarks[0] - landmarks[16])) / iod,
        'geo_pitch': pose['geo_pitch'],
        'geo_yaw': pose['geo_yaw'],
        'geo_roll': pose['geo_roll'],
        'geo_eye_line_roll': _eye_line_roll(landmarks),
    }


def differential(static: dict[str, float], baseline: dict[str, float] | None) -> dict[str, float]:
    """Kurangi fitur statis dengan baseline netral subjek (StressGAT, Differential AU).

    baseline None -> nilai apa adanya (acuan onset/fallback).
    """
    if baseline is None:
        return dict(static)
    return {col: static[col] - baseline[col] for col in STATIC_COLS}


def velocity(previous: dict[str, float] | None, current: dict[str, float]) -> dict[str, float]:
    """Selisih antar frame (per frame). previous None -> tidak ada gerakan teramati."""
    if previous is None:
        return {col: 0.0 for col in VELOCITY_COLS}
    d_ear = current['geo_ear_mean'] - previous['geo_ear_mean']
    d_mar = current['geo_mar'] - previous['geo_mar']
    d_pitch = current['geo_pitch'] - previous['geo_pitch']
    d_yaw = current['geo_yaw'] - previous['geo_yaw']
    d_roll = current['geo_roll'] - previous['geo_roll']
    return {
        'geo_d_ear_mean': d_ear,
        'geo_d_mar': d_mar,
        'geo_d_pitch': d_pitch,
        'geo_d_yaw': d_yaw,
        'geo_d_roll': d_roll,
        'geo_head_motion': math.sqrt(d_pitch * d_pitch + d_yaw * d_yaw + d_roll * d_roll),
    }

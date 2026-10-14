"""Definisi kanonik ROI wajah, ukuran target, dan block_size POC.

SATU-SATUNYA sumber kebenaran. Sebelum ini definisi yang sama disalin di LIMA
tempat (comparasion/core/config.py, scripts/spotting.py,
pipeline/stages/stage_2_extract_features.py, legacy/methods/extract_features_roi.py, dan
comparasion/core/pipeline.py) dan sudah TERBUKTI menyimpang: spotting memakai
mata = kelopak saja, sedangkan ekstraksi memakai mata = alis + kelopak. Akibatnya
`mata_*` dan `alis_*` saling tumpang tindih (alis ⊂ mata) sehingga fiturnya
redundan, dan sinyal yang dipakai spotting berbeda dari yang dipakai fitur.

Landmark mengikuti model 68 titik dlib:
    17-21 alis kiri (dari sudut pandang penonton), 22-26 alis kanan
    36-41 mata kiri, 42-47 mata kanan
    48-67 mulut

ROI sengaja TIDAK tumpang tindih supaya tiap fitur punya arti sendiri:
gerakan alis (AU1/AU2/AU4) dan gerakan kelopak (AU5/AU7) adalah sinyal yang
berbeda secara diagnostik, jadi digabung justru menghilangkan informasi.

BLOCK_SIZE = 9 (bukan 7): saturasi POC terjadi saat perpindahan melebihi
(block_size-1)/2. Diukur pada 18 clip x 8 frame (lihat
report/findings/perbaikan-ekstraksi-v2.md):
    block_size 7 -> 4,6% blok mentok di batas
    block_size 9 -> 1,4%
    block_size 11 -> 1,2%   (tapi alis tinggal 2 baris blok)
    block_size 13 -> 0,85%  (alis tinggal 1 baris blok -> degenerate)
9 dipilih karena memangkas ~70% saturasi tanpa merusak resolusi spasial.
"""

from __future__ import annotations

REGIONS: dict[str, list[int]] = {
    'mulut': list(range(48, 68)),
    'mata_kiri': list(range(36, 42)),
    'mata_kanan': list(range(42, 48)),
    'alis_kiri': list(range(17, 22)),
    'alis_kanan': list(range(22, 27)),
}

# Mode lama 3 region (tanpa alis) untuk tabel poc_abs_flatten_ordered.xlsx.
REGIONS_TANPA_ALIS: dict[str, list[int]] = {
    k: v for k, v in REGIONS.items() if not k.startswith('alis_')
}

TARGET_SIZE: dict[str, tuple[int, int]] = {
    'mulut': (70, 35),
    'mata_kiri': (48, 32),
    'mata_kanan': (48, 32),
    'alis_kiri': (64, 24),
    'alis_kanan': (64, 24),
}

BLOCK_SIZE: int = 9
PADDING_X: int = 6
PADDING_Y: int = 8

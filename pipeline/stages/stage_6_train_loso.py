#!/usr/bin/env python
"""LOSO (Leave-One-Subject-Out) untuk TabR - subjek-disjoint murni.

Setiap fold: test = 1 subjek (belum pernah dilihat model),
val = 20% subjek tersisa (early stopping, subjek-disjoint dari test),
train = sisa subjek. Train clips diseimbangkan per label persis seperti
export utama (seed 72) supaya hasilnya apple-to-apple dgn protokol
GroupShuffleSplit 33/11/12 yang sudah ada.

Hyperparameter DIAMBIL dari run utama (bukan tuning per fold):
0-evaluation/{seed}.toml terbaik dari exp/tabr/convat_apex_anxiety
(config 392 fitur, dipilih lewat val_score).

Konteks evaluasi TabR:
- Numpy dataset per fold di-stage ke data/<dataset> (overwrite tiap fold,
  hemat disk; hasil tiap fold disimpan di exp/tabr/<dataset>/fold_XXX/).
- bin.evaluate.main dipanggil in-process per fold.

Contoh:
    uv run python pipeline/stages/stage_6_train_loso.py                     # semua fold, 3 seed
    uv run python pipeline/stages/stage_6_train_loso.py --seeds 1           # 1 seed per fold
    uv run python pipeline/stages/stage_6_train_loso.py --fold 0 --seeds 1  # smoke test fold 0
    uv run python pipeline/stages/stage_6_train_loso.py --force             # ulang walau ada DONE
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import hashlib
import json
import os
import random
import re
import shutil
import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_selection import VarianceThreshold
from sklearn.impute import SimpleImputer
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
TABR_ROOT = ROOT / 'third_party/tabular-dl-tabr-official'
FEATURES_XLSX = ROOT / 'experiments/features/apex/poc_abs_roi_signals.xlsx'
FEATURES_CSV = ROOT / 'experiments/features/apex/poc_abs_roi_signals_full.csv'
FEATURES_PKL = ROOT / 'experiments/features/apex/poc_abs_roi_signals_full.pkl'

RANDOM_SEED = 72
LABEL_MAP = {'anxiety_rendah': 0, 'anxiety_tinggi': 1}
META_COLS = [
    'phase', 'condition', 'label', 'participant', 'participant_raw', 'question', 'question_no',
    'sample', 'clip', 'event_clip', 'event_no', 'clip_path', 'frame', 'target', 'event_id',
]
# Config training default = kapasitas minimal (compact): satu-satunya yang
# overfitting-nya praktis nol (gap train-val -0,0055) dengan AUC setara config
# berkapasitas 4x lebih besar. Sama dengan default run_pipeline_v3.sh.
DEFAULT_CONFIG = ROOT / 'experiments/configs/tabr_loso_compact.toml'


def balance_train_clips_by_label(df_train: pd.DataFrame, seed: int = RANDOM_SEED):
    """Sama persis dgn export utama: seimbangkan JUMLAH CLIP per label di train."""
    rng = random.Random(seed)
    event_table_train = (
        df_train[['event_id', 'label', 'target', 'phase', 'participant', 'question', 'clip', 'event_clip']]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    grouped = {}
    for label_name, label_df in event_table_train.groupby('label', sort=True):
        clip_table = (
            label_df[['participant', 'question', 'clip', 'label']]
            .drop_duplicates()
            .sort_values(['participant', 'question', 'clip'], kind='stable')
            .reset_index(drop=True)
        )
        grouped[label_name] = clip_table
    min_clip_count = min(len(x) for x in grouped.values())
    selected_clip_keys = []
    for label_name, clip_table in grouped.items():
        clip_records = clip_table.to_dict('records')
        rng.shuffle(clip_records)
        chosen = clip_records[:min_clip_count]
        selected_clip_keys.extend([
            (row['participant'], row['question'], row['clip'], row['label'])
            for row in chosen
        ])
    selected_clip_keys = set(selected_clip_keys)
    return df_train[
        df_train.apply(lambda row: (row['participant'], row['question'], row['clip'], row['label']) in selected_clip_keys, axis=1)
    ].copy()


def balance_train_frames_by_label(df_train: pd.DataFrame, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Oversample baris (frame) kelas minoritas agar jumlah FRAME per label
    seimbang di train. Duplikat frame = oversampling klasik; tidak menyentuh
    protokol split (subjek-disjoint sudah dibentuk sebelumnya).

    Target: training jadi tidak condong ke kelas mayoritas, sehingga recall
    kelas minoritas (yang tadinya bisa jatuh ke ~0.17) lebih adil.
    """
    rng = np.random.RandomState(seed)
    idx_by_label = {0: df_train.index[df_train['target'] == 0], 1: df_train.index[df_train['target'] == 1]}
    counts = {lab: len(idx) for lab, idx in idx_by_label.items()}
    max_count = max(counts.values())
    chosen = []
    for label, idx in idx_by_label.items():
        needed = max_count - len(idx)
        if needed > 0:
            replace = needed <= len(idx)
            idx = np.append(idx, rng.choice(idx, size=needed, replace=replace))
        chosen.append(idx)
    return df_train.loc[np.concatenate(chosen)].reset_index(drop=True)


AGG_KEYS = {
    'clip': ['participant', 'question', 'clip', 'event_clip'],
    # SATU BARIS = SATU SESI (subjek x fase), BUKAN satu orang.
    # Label di dataset ini milik SESI, bukan orang: folder `before/anxiety` dan
    # `after/tidak` menghasilkan label berbeda untuk orang yang sama, dan 18 dari
    # 56 subjek memang berpindah label antar sesi. Dengan kunci `['participant']`
    # saja, kedua sesi digabung jadi SATU baris (mean+std atas ~1600 frame
    # campuran dua kondisi) dan labelnya diambil dari sesi yang terurut lebih
    # dulu (`after`) -- 18 baris (32%) jadi campuran dua kondisi berlawanan
    # dengan label yang hanya benar untuk separuh isinya. `phase` ikut kunci
    # supaya tiap baris = satu sesi utuh dengan label yang benar.
    'subject': ['participant', 'phase'],
}


def apply_feature_drop(feature_cols: list[str], pattern: str) -> tuple[list[str], list[str]]:
    """Buang kolom fitur yang cocok dengan regex. Mengembalikan (sisa, dibuang).

    Dipanggil DUA KALI: sebelum agregasi dan sesudahnya. Alasannya, nama kolom
    berubah setelah agregasi (`mulut_mean_m` -> `mulut_mean_m_mean`/`_std`):

      - `_max_m$`  cocok SEBELUM agregasi, tidak cocok sesudah (`..._max_m_mean`
        berakhiran `_mean`). Jadi ia harus jalan sebelum.
      - `_std$`    TIDAK cocok sebelum agregasi (belum ada sufiks itu), cocok
        sesudah. Jadi ia harus jalan sesudah.

    Bug yang diperbaiki: dulu regex hanya dijalankan SEBELUM agregasi, sehingga
    `--drop-features "_std$"` membuang 0 kolom tanpa peringatan (diam-diam tidak
    melakukan apa pun), DAN karena ia menggantikan default `_max_m$`, fitur
    tersensor `*_max_m` justru ikut kembali.
    """
    if not pattern:
        return feature_cols, []
    pat = re.compile(pattern)
    dropped = [c for c in feature_cols if pat.search(c)]
    return [c for c in feature_cols if not pat.search(c)], dropped


def aggregate_rows(df: pd.DataFrame, feature_cols: list[str], mode: str) -> tuple[pd.DataFrame, list[str]]:
    """Ringkas baris frame jadi 1 baris per clip / per sesi (fitur = mean + std).

    TabR dilatih per baris sementara label di data ini milik SESI (subjek x fase),
    jadi satu sesi menyumbang 500-1400 baris dan rata-rata probabilitas frame jadi
    tidak terkontrol. Mode ini memindahkan agregasi ke sisi fitur supaya 1 baris =
    1 unit label (clip atau sesi). Kunci agregasi HARUS sepadan dengan satuan
    label: menggabungkan dua sesi satu orang jadi satu baris mencampur dua kondisi
    yang justru berbeda.
    """
    keys = AGG_KEYS[mode]
    feats = df.groupby(keys, sort=True, dropna=False)[feature_cols].agg(['mean', 'std'])
    feats.columns = [f'{col}_{stat}' for col, stat in feats.columns]
    # Kolom yang sudah jadi bagian kunci tidak boleh di-agregasi lagi: setelah
    # `reset_index()` kunci itu muncul sebagai kolom, dan menambahkannya lagi
    # lewat agg() membuat reset_index gagal ("cannot insert phase, already
    # exists"). Nilainya identik, jadi cukup ambil sisanya.
    meta_cols = [c for c in ('label', 'target', 'phase', 'condition') if c not in keys]
    meta = df.groupby(keys, sort=True, dropna=False).agg(
        **{col: (col, 'first') for col in meta_cols}
    )
    out = feats.reset_index().merge(meta.reset_index(), on=keys, how='left')
    out['event_id'] = out[keys].astype(str).agg('||'.join, axis=1)
    return out, [c for c in out.columns if c not in META_COLS]


def subject_standardize(df: pd.DataFrame, feature_cols: list[str], subject_col: str = 'participant') -> pd.DataFrame:
    """Z-score tiap fitur memakai mean/std subjek itu sendiri.

    Menghapus pergeseran dan skala identitas (varian antar subjek di data ini
    lebih besar dari varian dalam subjek). Tanpa label: hanya distribusi fitur
    subjek tersebut, jadi tidak ada kebocoran label; subjek uji memakai
    statistiknya sendiri (Personal-Zscore pada literatur cross-subject).

    Subjek dengan std 0 (fitur konstan) dibiarkan apa adanya (std -> 1).
    """
    out = df.copy()
    grouped = out.groupby(subject_col, sort=False)[feature_cols]
    mean = grouped.transform('mean')
    std = grouped.transform('std').replace(0.0, 1.0).fillna(1.0)
    out[feature_cols] = (out[feature_cols] - mean) / std
    return out


def load_full_table(features_path: Path | None = None) -> tuple[pd.DataFrame, list[str]]:
    """Full feature table (semua subjek, SEMUA baris, tanpa balance).

    Cache diutamakan: pkl (bit-identik dgn xlsx, ~0.02s) > csv > xlsx (~30s,
    openpyxl). Cache pkl dibuat sekali oleh pipeline/stages/stage_3_cache.py; kalau tidak ada, xlsx
    tetap dipakai dan itu yang bikin stage 3 diam ~30 detik di awal.
    `features_path` = override opsional; default = roi25.
    """
    if features_path is None:
        for cand in (FEATURES_PKL, FEATURES_CSV, FEATURES_XLSX):
            if cand.exists():
                features_path = cand
                break
    if features_path.suffix.lower() == '.pkl':
        print(f'Baca tabel fitur (pkl cache): {features_path}')
        df = pd.read_pickle(features_path)
    elif features_path.suffix.lower() == '.csv':
        print(f'Baca tabel fitur (csv): {features_path}')
        df = pd.read_csv(features_path)
    else:
        print(f'Baca tabel fitur (xlsx, lambat ~30s): {features_path}', flush=True)
        df = pd.read_excel(features_path)
    df = df[df['label'].isin(LABEL_MAP)].copy()
    df['target'] = df['label'].map(LABEL_MAP)
    df['event_id'] = (
        df['phase'].astype(str) + '||' + df['participant'].astype(str) + '||' +
        df['question'].astype(str) + '||' + df['clip'].astype(str) + '||' + df['event_clip'].astype(str)
    )
    feature_cols = [c for c in df.columns if c not in META_COLS]
    return df, feature_cols


def has_both_labels(df: pd.DataFrame, subjects) -> bool:
    """True kalau subset subjek ini memuat kedua kelas (syarat val yang informatif)."""
    return set(df[df['participant'].isin(subjects)]['label']) == set(LABEL_MAP)


def epoch_trace_from_checkpoint(run_dir: Path) -> list[dict]:
    """Trace per-epoch dari `checkpoint.pt` milik satu run (fold, seed).

    Sumbernya `training_log`: tiap epoch menyimpan `metrics` val/test lengkap,
    termasuk `cross-entropy` (loss) yang TIDAK ada di `summary.json` maupun
    `report.json` (keduanya hanya menyimpan epoch terbaik). Train loss diambil
    dari tfevents `loss_train/` karena hanya itu yang menyimpannya.

    Kenapa loss penting, bukan cuma akurasi: dengan ~11 subjek val, akurasi val
    hanya bergerak dalam langkah 1/11 = 9,1% dan berupa fungsi tangga berisik,
    sehingga "epoch terbaik" menurut akurasi nyaris acak. Loss kontinu. Kalau
    train loss TURUN sementara val loss NAIK, model menghafal data latih sejak
    epoch itu -- dan itu tidak terlihat dari angka akurasi.

    Cara ini konsisten dengan `notebooks/tabr_feature_pruning_tuning.ipynb`
    (`collect_epoch_metrics`).
    """
    ckpt = run_dir / 'checkpoint.pt'
    if not ckpt.exists():
        return []
    try:
        import torch
        ck = torch.load(ckpt, map_location='cpu', weights_only=False)
    except Exception:  # checkpoint rusak/versi lain -> jangan gagalkan run
        return []
    rows = []
    for i, item in enumerate(ck.get('training_log') or []):
        m = item.get('metrics') or {}
        val = m.get('val') or {}
        test = m.get('test') or {}
        rows.append({
            'epoch': i,
            'val_acc': val.get('score'),
            'val_ce': val.get('cross-entropy'),
            'test_acc': test.get('score'),
            'train_ce': None,
        })
    # Train loss: hanya ada di tfevents loss_train/ (ditulis writer.add_scalars).
    try:
        from tensorboard.backend.event_processing import event_accumulator
        loss_dir = run_dir / 'loss_train'
        ev = next(loss_dir.glob('events.out.tfevents.*'), None) if loss_dir.is_dir() else None
        if ev is not None:
            acc = event_accumulator.EventAccumulator(str(ev))
            acc.Reload()
            for s in acc.Scalars('loss'):
                if 0 <= s.step < len(rows):
                    rows[s.step]['train_ce'] = float(s.value)
    except Exception:  # tensorboard tidak ada -> biarkan None
        pass
    return rows


def install_quiet_tqdm() -> None:
    """Ganti `tqdm` dengan no-op supaya log training tidak jadi ribuan baris progress.

    TabR memanggil tqdm di dalam loop epoch (bin/tabr.py, lib/neighbors.py); satu
    update per batch. Jumlahnya membengkak mengikuti batch per epoch: pada run
    frame-level (259 batch/epoch) 168 fold-seed menulis ratusan MB karakter
    carriage-return ke log. Diukur pada fold 0, 1 seed, --aggregate subject:
    log turun dari 460 baris/26.617 byte jadi 22 baris/1.631 byte.

    Modul asli disalin apa adanya kecuali `tqdm` supaya `import tqdm.auto` milik
    lib/dnnr/scaling.py tetap bisa dipakai.
    """
    import tqdm as real_tqdm

    class _QuietTqdm:
        def __init__(self, iterable=None, *args, **kwargs):
            self._iterable = [] if iterable is None else iterable

        def __iter__(self):
            return iter(self._iterable)

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def update(self, *args, **kwargs):
            return None

        def set_description(self, *args, **kwargs):
            return None

        def set_postfix(self, *args, **kwargs):
            return None

        def close(self):
            return None

        @staticmethod
        def write(*args, **kwargs):
            return None

    shim = types.ModuleType('tqdm')
    shim.__dict__.update(real_tqdm.__dict__)
    shim.tqdm = _QuietTqdm
    sys.modules['tqdm'] = shim


def run_fingerprint(path: Path, df: pd.DataFrame, run_key: str) -> str:
    """Sidik jari tabel fitur + opsi run, untuk memutuskan resume fold masih sah atau tidak.

    `DONE.json` lama hanya mencatat fold/subjek/seed, TIDAK mencatat tabel fitur
    maupun opsi yang mengubah DATANYA. Akibatnya resume melewati fold hasil
    training pada tabel/opsi lama walau keduanya sudah diganti, lalu collect
    melaporkan angka milik data lama seolah-olah milik data sekarang. Sidik jari
    ini menutup celah itu: fold di-skip hanya kalau tabel fitur DAN opsi run sama.

    `run_key` = ringkasan opsi yang mengubah isi baris training (label-unit,
    aggregate, subject-norm, drop-features, dataset, seeds). Tanpa ini, ganti
    `--label-unit person` -> `session` atau `--aggregate` tetap memakai fold lama
    dan hasilnya tampak "tidak berubah" walau datanya sudah berbeda.
    """
    try:
        st = path.stat()
        meta = f'{path.resolve()}|{st.st_size}|{st.st_mtime_ns}'
    except OSError:
        meta = f'{path}|?'
    cols = '|'.join(map(str, df.columns))
    return hashlib.sha1(f'{meta}|{len(df)}|{cols}|{run_key}'.encode()).hexdigest()[:16]


def main() -> None:
    parser = argparse.ArgumentParser(description='LOSO TabR (subjek-disjoint).')
    parser.add_argument(
        '--dataset', default='convat_apex_anxiety_loso_roi25_reg',
        help='nama dataset di third_party/.../data/. Default disamakan dengan '
             '`[data] path` di DEFAULT_CONFIG supaya tidak ada mismatch.',
    )
    parser.add_argument(
        '--features', type=Path, default=None,
        help='tabel fitur alternatif (csv/xlsx); default = roi25 '
             '(experiments/features/apex/poc_abs_roi_signals.xlsx, 25 fitur).',
    )
    parser.add_argument('--seeds', type=int, default=3)
    parser.add_argument('--fold', type=int, default=None, help='jalankan satu fold saja (indeks subjek terurut)')
    parser.add_argument(
        '--test-persons-file', type=Path, default=None,
        help='Mode EVALUASI HOLDOUT (fold-first): txt berisi daftar orang test '
             '(satu per baris, hasil split_persons_presplit.py). Menjalankan TEPAT '
             'SATU fold (fold_000): test = semua orang di file, train/val = sisanya '
             'via split subjek-disjoint biasa. Tujuan: 12 orang ini tidak pernah '
             'dibaca spotting/fitur/tuning sama sekali sebelum evaluasi ini. '
             'Tidak bisa digabung dengan --fold.',
    )
    parser.add_argument('--force', action='store_true', help='ulang walau fold sudah DONE')
    parser.add_argument(
        '--quiet', action='store_true',
        help='Ringkas log: progress bar TabR dimatikan dan keluaran tiap fold ditulis ke '
             'fold_XXX/train.log, bukan ke stdout. Satu baris per fold. Traceback tetap '
             'muncul di stdout dan di fold_XXX/FAILED.txt.',
    )
    parser.add_argument('--val-size', type=float, default=0.2)
    parser.add_argument(
        '--variance-threshold', type=float, default=1e-4,
        help='Hapus fitur yang HAMPIR KONSTAN di train (varianza <= nilai ini). '
             'Dihitung SETELAH StandardScaler dan hanya pada X_train fold (anti-bocor). '
             'Urutan scale-dulu-baru-variance itu penting: pada nilai mentah, ambang '
             'absolut seperti 1e-4 menjadi filter SKALA dan membuang fitur satuan-kecil '
             '(mis. geometri ternormalisasi) yang sebenarnya bergerak. '
             'Default 1e-4 (dinyalakan); 0 = mati.',
    )
    parser.add_argument(
        '--imbalance', choices=['clips', 'frames'], default='clips',
        help="Titik rebalance kelas di train: 'clips' = seimbangkan JUMLAH CLIP per label "
             "(protokol lama); 'frames' = oversample FRAME kelas minoritas (sesudah clip-balance).",
    )
    parser.add_argument(
        '--label-unit', choices=['person', 'session'], default='person',
        help="Satuan label. 'person' (default): pakai sesi 'after' saja -> tiap subjek "
             "punya TEPAT SATU label (baris 'before' dibuang; 'before' memuat 41/56 "
             "anxiety_tinggi (73%%) vs 'after' 25/56 (45%%), jadi labelnya sangat "
             "tercampur dengan fase before/after dan menambah confound fase). "
             "'session': semua baris, label = kondisi sesi (perilaku lama; 18 subjek punya 2 label).",
    )
    parser.add_argument(
        '--drop-features', default=r'_max_m$',
        help='Regex nama kolom fitur yang dibuang. Default membuang *_max_m yang '
             'tersensor: nilainya mentok di (block_size-1)/2*sqrt(2) = 5.657 untuk '
             'block_size 9. Pakai "" untuk mematikan.',
    )
    parser.add_argument(
        '--aggregate', choices=['none', 'clip', 'subject'], default='none',
        help="Satuan baris training. 'none' (default): 1 baris = 1 frame (protokol lama). "
             "'clip': 1 baris = 1 clip (fitur di-ringkas mean+std, train di-balance per clip). "
             "'subject': 1 baris = 1 SESI, yaitu subjek x fase (mean+std; tanpa balance karena "
             "tiap sesi harus tetap ikut). Label di data ini milik sesi, bukan orang -- 18 dari "
             "56 subjek berpindah label antar sesi before/after, jadi menggabung dua sesi jadi "
             "satu baris akan mencampur dua kondisi berlawanan. Agregasi pindah ke sisi fitur, "
             "jadi prediksi test tidak lagi bergantung pada berapa frame yang dimiliki satu sesi.",
    )
    parser.add_argument(
        '--subject-norm', choices=['none', 'subject'], default='none',
        help="Normalisasi fitur per subjek. 'none' (default): hanya StandardScaler "
             "global di train (protokol lama, hasil lama tetap bisa direproduksi). "
             "'subject': tiap fitur di-z-score memakai mean/std subjek ITU SENDIRI "
             "(train/val/test masing-masing), tanpa label. Ini membuang pergeseran & "
             "skala identitas -- varian antar subjek di data ini lebih besar dari "
             "varian dalam subjek, jadi fitur lebih kuat mengkodekan SIAPA orangnya "
             "daripada kondisi cemasnya. Tidak boleh dipakai bersama --aggregate subject.",
    )
    parser.add_argument(
        '--device', choices=['auto', 'cpu', 'cuda'], default='cpu',
        help="Perangkat training TabR. Default 'cpu' DISENGAJA: data ini 44 baris train "
             "x <=660 fitur, jadi GPU tidak memberi percepatan berarti, sementara tiap "
             "fold membuat konteks CUDA baru (56 fold x 3 seed = 168 konteks) dan itu "
             "membebani driver di GPU kecil -- dilaporkan membuat mesin crash/reboot. "
             "'cuda' memaksa GPU (butuh CUDA_VISIBLE_DEVICES), 'auto' mengikuti ketersediaan.",
    )
    parser.add_argument(
        '--epochs-log', action='store_true',
        help='Cetak satu baris ringkas per fold berisi jumlah epoch, epoch terbaik, dan '
             'skor train/val. Detail per epoch tetap ada di fold_*/train.log.',
    )
    parser.add_argument(
        '--epochs-trace', type=int, nargs='?', const=40, default=0, metavar='N',
        help='Cetak kurva per epoch (maks N angka per seed, default 40) untuk tiap fold: '
             'val_acc%%, train_loss, val_loss, epoch terbaik, dan peringatan overfit. '
             'Sumbernya checkpoint.pt (training_log) + tfevents loss_train/. Berguna untuk '
             'melihat apakah val loss naik sementara train loss turun (overfit).',
    )
    parser.add_argument(
        '--config', type=Path, default=DEFAULT_CONFIG,
        help=f'Config training TabR (toml). Default: {DEFAULT_CONFIG}',
    )
    args = parser.parse_args()

    if args.subject_norm == 'subject' and args.aggregate == 'subject':
        raise SystemExit(
            "--subject-norm subject tidak bisa dipakai bersama --aggregate subject: "
            "dengan 1 baris/subjek, std subjek = 0 untuk semua fitur sehingga "
            "semua baris jadi 0 dan tidak ada informasi tersisa."
        )

    dataset_name = args.dataset
    os.environ['PROJECT_DIR'] = str(TABR_ROOT)
    # Perangkat harus diputuskan SEBELUM torch diimpor (lib.util.get_device membaca
    # torch.cuda.is_available()). CUDA_VISIBLE_DEVICES="" menyembunyikan GPU dari
    # torch, jadi TabR otomatis jatuh ke CPU tanpa perlu mengubah kode pihak ketiga.
    if args.device == 'cpu':
        os.environ['CUDA_VISIBLE_DEVICES'] = ''
        print('Device  : cpu (CUDA disembunyikan dari torch)')
    elif args.device == 'cuda':
        os.environ.setdefault('CUDA_VISIBLE_DEVICES', '0')
        print(f"Device  : cuda (CUDA_VISIBLE_DEVICES={os.environ['CUDA_VISIBLE_DEVICES']})")
    else:
        print('Device  : auto (mengikuti ketersediaan CUDA)')
    sys.path.append(str(TABR_ROOT))

    if args.quiet:
        install_quiet_tqdm()

    import bin.evaluate  # noqa: E402  (butuh PROJECT_DIR dulu)
    import lib  # noqa: E402

    data_dir = TABR_ROOT / 'data' / dataset_name
    exp_root = TABR_ROOT / 'exp/tabr' / dataset_name
    exp_root.mkdir(parents=True, exist_ok=True)

    df, feature_cols = load_full_table(args.features)
    all_participants = sorted(df['participant'].unique().tolist())
    if args.label_unit == 'person':
        before_rows = len(df)
        df = df[df['phase'] == 'after'].copy()
        lost = sorted(set(all_participants) - set(df['participant']))
        print(f'label unit = person: {before_rows - len(df)} baris "before" dibuang, '
              f'sisa {len(df)} baris (sesi "after", 1 label per subjek)')
        if lost:
            print(f'  PERINGATAN: subjek tanpa sesi "after" ikut hilang: {lost}')
    if args.drop_features:
        feature_cols, dropped = apply_feature_drop(feature_cols, args.drop_features)
        print(f'drop fitur /{args.drop_features}/ (pra-agregasi): {len(dropped)} dibuang'
              + (f' -> {dropped}' if dropped else ' (tidak ada yang cocok di tahap ini)'))
    if args.aggregate != 'none':
        n_before = len(df)
        df, feature_cols = aggregate_rows(df, feature_cols, args.aggregate)
        print(f'agregasi {args.aggregate}: {n_before} baris frame -> {len(df)} baris, '
              f'{len(feature_cols)} fitur (mean+std)')
        # Regex dijalankan ULANG sesudah agregasi: sufiks `_mean`/`_std` baru ada
        # di sini, jadi pola seperti `_std$` hanya cocok pada tahap ini.
        if args.drop_features:
            feature_cols, dropped_post = apply_feature_drop(feature_cols, args.drop_features)
            print(f'drop fitur /{args.drop_features}/ (pasca-agregasi): '
                  f'{len(dropped_post)} dibuang' + (f' -> {dropped_post}' if dropped_post else ''))
            if not dropped and not dropped_post:
                raise SystemExit(
                    f'--drop-features "{args.drop_features}" tidak cocok dengan kolom mana pun. '
                    f'Periksa regex-nya (mis. "_std$" untuk membuang blok std, "_max_m$" untuk max_m).'
                )
    participants = sorted(df['participant'].unique().tolist())
    print(f'Total baris={len(df)} subjek={len(participants)} fitur={len(feature_cols)}')
    print(f'Kelas: {df["label"].value_counts().to_dict()}')
    n_folds = len(participants)

    if args.test_persons_file is not None and args.fold is not None:
        raise SystemExit('--test-persons-file tidak bisa digabung dengan --fold.')
    if args.test_persons_file is not None:
        # Mode evaluasi holdout: SATU fold, test = daftar orang dari file.
        holdout = [ln.strip() for ln in args.test_persons_file.read_text().splitlines()
                   if ln.strip() and not ln.strip().startswith('#')]
        missing = sorted(set(holdout) - set(participants))
        if missing:
            raise SystemExit(
                f'--test-persons-file: {len(missing)} orang tidak ada di tabel fitur: '
                f'{missing}. Pastikan fitur holdout sudah digabung (combine_feature_tables.py).'
            )
        fold_defs: list[tuple[int, list[str]]] = [(0, sorted(set(holdout)))]
        print(f'Mode HOLDOUT: 1 fold, test = {len(fold_defs[0][1])} orang dari '
              f'{args.test_persons_file}')
    else:
        fold_indices = [args.fold] if args.fold is not None else list(range(n_folds))
        fold_defs = [(i, [participants[i]]) for i in fold_indices]

    base_config = lib.load_config(args.config)
    print(f'Config  : {args.config}')
    print(f'Score   : {base_config["data"].get("score") or "accuracy (default TabR)"}'
          '  <- dipakai untuk early stopping (best_epoch)')

    # Config menyatakan dataset mana yang ia di-tuning untuk itu, tapi --dataset
    # selalu menimpanya (lihat `template['data']['path']` di loop fold). Kalau
    # keduanya tidak cocok, hyperparameter di config dipakai pada data yang
    # berbeda dari yang dimaksud penulisnya. Itu pernah membuat satu run jatuh
    # ke bawah acak tanpa error apa pun, jadi sekarang diperingatkan.
    cfg_path = base_config['data'].get('path')
    if cfg_path:
        cfg_dataset = str(cfg_path).split('/')[-1]
        if cfg_dataset != dataset_name:
            print(
                f'\n!! PERINGATAN: config menyatakan dataset `{cfg_dataset}`, '
                f'tapi --dataset = `{dataset_name}`.\n'
                f'   --dataset MENANG, jadi config ini dilatih pada data yang '
                f'bukan target tuning-nya.\n'
                f'   Kalau ini tidak disengaja, pakai --dataset {cfg_dataset} '
                f'atau jalankan lewat pipeline/run.sh (default-nya '
                f'sudah disamakan).\n'
            )

    print(f'Imbalance: {args.imbalance} | var-thresh: {args.variance_threshold} | '
          f'aggregate: {args.aggregate} | subject-norm: {args.subject_norm}')

    # Opsi yang mengubah ISI baris training, jadi harus ikut sidik jari resume.
    # Tanpa ini, resume melewati fold lama dan hasilnya tampak tidak berubah
    # padahal data training-nya sudah berbeda. Hyperparameter config ikut di-hash
    # ISI-nya (bukan cuma path-nya): config yang di-edit di tempat yang sama juga
    # harus memaksa latih ulang.
    cfg_hash = hashlib.sha1(
        json.dumps(base_config, sort_keys=True, default=str).encode()
    ).hexdigest()[:12]
    run_key = '|'.join([
        f'dataset={dataset_name}',
        f'label_unit={args.label_unit}',
        f'aggregate={args.aggregate}',
        f'subject_norm={args.subject_norm}',
        f'drop_features={args.drop_features}',
        f'imbalance={args.imbalance}',
        f'variance_threshold={args.variance_threshold}',
        f'seeds={args.seeds}',
        f'config={args.config}',
        f'config_sha1={cfg_hash}',
    ])
    feat_fp = run_fingerprint(args.features, df, run_key)
    print(f'Fitur   : {args.features} (sidik jari run {feat_fp})')

    for fold_idx, test_subjects in fold_defs:
        test_subject = (test_subjects[0] if len(test_subjects) == 1
                        else f'{len(test_subjects)} orang (holdout)')
        test_set = set(test_subjects)
        fold_dir = exp_root / f'fold_{fold_idx:03d}'
        eval_dir = fold_dir / '0-evaluation'
        done_file = fold_dir / 'DONE.json'
        if done_file.exists() and not args.force:
            try:
                prev_inputs = json.loads(done_file.read_text()).get('inputs', {})
            except (json.JSONDecodeError, OSError):
                prev_inputs = {}
            # `run_sha1` = tabel fitur + opsi run. DONE.json lama hanya punya
            # `features_sha1` (tabel saja) -> dianggap tidak cocok supaya fold
            # lama tidak dipakai ulang tanpa verifikasi.
            prev_fp = prev_inputs.get('run_sha1')
            if prev_fp == feat_fp:
                print(f'[{fold_idx}/{n_folds}] skip {test_subject} (DONE ada)')
                continue
            # Sidik jari berbeda -> latih ulang. Sebabnya bisa tabel fitur yang
            # berubah ATAU opsi run (label-unit/aggregate/subject-norm/seeds/...),
            # jadi pesannya tidak boleh mengklaim hanya tabel fitur.
            print(f'[{fold_idx}/{n_folds}] ulang {test_subject} '
                  f'(konfigurasi run berubah: {prev_fp or "tidak tercatat"} -> {feat_fp})')
        else:
            print(f'\n[{fold_idx + 1}/{n_folds}] fold: test subjek = {test_subject}', flush=True)

        # ── Split subjek-disjoint: test = 1 subjek (atau daftar holdout), val = 20% sisa, train = sisa ──
        rest = pd.Series([p for p in participants if p not in test_set])
        train_parts = val_parts = None
        for rs in range(RANDOM_SEED, RANDOM_SEED + 500):
            gss = GroupShuffleSplit(n_splits=1, test_size=args.val_size, random_state=rs)
            tr_idx, va_idx = next(gss.split(rest, groups=rest))
            cand_tr, cand_va = rest.iloc[tr_idx], rest.iloc[va_idx]
            if has_both_labels(df, cand_tr) and has_both_labels(df, cand_va):
                train_parts, val_parts = cand_tr, cand_va
                if rs != RANDOM_SEED:
                    print(f'      split random_state={rs} (seed {RANDOM_SEED}: val tidak '
                          f'memuat 2 kelas, early stopping jadi tidak informatif)', flush=True)
                break
        if train_parts is None:
            raise SystemExit(
                f'Fold {fold_idx}: tidak ada split subjek-disjoint dgn 2 kelas di train DAN val '
                f'(val_size={args.val_size}).'
            )
        df_tr = df[df['participant'].isin(train_parts)].copy()
        df_val = df[df['participant'].isin(val_parts)].copy()
        df_test = df[df['participant'].isin(test_set)].copy()

        if args.subject_norm == 'subject':
            df_tr = subject_standardize(df_tr, feature_cols)
            df_val = subject_standardize(df_val, feature_cols)
            df_test = subject_standardize(df_test, feature_cols)
            print('      subject-norm: fitur di-z-score per subjek (train/val/test)', flush=True)

        print(f'      subjek train={len(train_parts)} val={len(val_parts)} test={len(test_set)}', flush=True)
        if args.aggregate == 'subject':
            print(f'      baris train={len(df_tr)} (1 baris/subjek, tanpa balance) '
                  f'val={len(df_val)} test={len(df_test)}', flush=True)
        else:
            df_tr = balance_train_clips_by_label(df_tr, seed=RANDOM_SEED)
            print(f'      baris train={len(df_tr)} (setelah balance clips) val={len(df_val)} test={len(df_test)}',
                  flush=True)
            if args.imbalance == 'frames':
                df_tr = balance_train_frames_by_label(df_tr, seed=RANDOM_SEED)
                print(f'      baris train={len(df_tr)} (frames-oversampled, kelas seimbang)',
                      flush=True)

        # ── Impute + scaler + (opsional) prune fitur konstan (fit train saja, anti-bocor) ──
        # URUTAN PENTING: scale DULU, baru variance. Threshold variance pada nilai
        # MENTAH adalah filter SKALA, bukan filter "fitur statis": fitur dengan
        # satuan kecil (geometri ternormalisasi ~1e-4) jatuh di bawah ambang 1e-4
        # yang disetel untuk POC-ABS, sehingga fitur yang jelas bergerak ikut
        # terbuang. Terukur pada run 2026-10-06: 16 dari 42 kolom geometri
        # (mean+std) dibuang, termasuk geo_lip_corner_drop (p gerbang 0,0352,
        # fitur geometri terkuat). Setelah di-scale: 0 kolom terbuang.
        imputer = SimpleImputer(strategy='mean')
        scaler = StandardScaler()
        X_train_all = imputer.fit_transform(df_tr[feature_cols])
        X_val_all = imputer.transform(df_val[feature_cols])
        X_test_all = imputer.transform(df_test[feature_cols])
        scaler.fit(X_train_all)
        X_train_all = scaler.transform(X_train_all)
        X_val_all = scaler.transform(X_val_all)
        X_test_all = scaler.transform(X_test_all)
        used_cols = list(feature_cols)
        if args.variance_threshold > 0:
            selector = VarianceThreshold(threshold=args.variance_threshold)
            X_train_all = selector.fit_transform(X_train_all)
            mask = selector.get_support()
            used_cols = [c for c, keep in zip(used_cols, mask) if keep]
            X_val_all = selector.transform(X_val_all)
            X_test_all = selector.transform(X_test_all)
            print(f'      constant-feature prune: {len(feature_cols)} -> {len(used_cols)} fitur',
                  flush=True)
        X_train = X_train_all.astype(np.float32)
        X_val = X_val_all.astype(np.float32)
        X_test = X_test_all.astype(np.float32)
        y_train = df_tr['target'].to_numpy(dtype=np.int64)
        y_val = df_val['target'].to_numpy(dtype=np.int64)
        y_test = df_test['target'].to_numpy(dtype=np.int64)

        # ── Stage dataset fold (overwrite) ──
        if data_dir.exists():
            shutil.rmtree(data_dir)
        data_dir.mkdir(parents=True)
        for part, X, y in [('train', X_train, y_train), ('val', X_val, y_val), ('test', X_test, y_test)]:
            np.save(data_dir / f'X_num_{part}.npy', X)
            np.save(data_dir / f'Y_{part}.npy', y)
        (data_dir / 'info.json').write_text(json.dumps({'task_type': 'binclass', 'name': dataset_name, 'id': dataset_name}, indent=2))
        (data_dir / 'feature_cols.json').write_text(json.dumps(used_cols, indent=2))
        (data_dir / 'READY').write_text('')
        df_test.to_csv(data_dir / 'test_split.csv', index=False)
        # Disimpan juga supaya ambang keputusan bisa dipilih di val (bukan di test).
        # Tanpa ini, urutan baris val tidak bisa direkonstruksi dari artefak run.
        df_val.to_csv(data_dir / 'val_split.csv', index=False)

        # ── Config evaluasi fold (config project, ganti data path) ──
        template = copy.deepcopy(base_config)
        template['data']['path'] = f':data/{dataset_name}'
        template['data']['cache'] = False
        template.pop('seed', None)
        if eval_dir.exists():
            shutil.rmtree(fold_dir)
        eval_dir.mkdir(parents=True)
        lib.dump_config(template, eval_dir / '0.toml')

        print(f'      training: {eval_dir} seeds={args.seeds}', flush=True)
        try:
            if args.quiet:
                # Detail per fold ke file sendiri; log pipeline cukup 1 baris per fold.
                with open(fold_dir / 'train.log', 'w') as fold_log, \
                        contextlib.redirect_stdout(fold_log), contextlib.redirect_stderr(fold_log):
                    bin.evaluate.main(eval_dir, args.seeds, 'bin.tabr.main', force=True)
            else:
                bin.evaluate.main(eval_dir, args.seeds, 'bin.tabr.main', force=True)
        except Exception as exc:  # noqa: BLE001 - biar fold lain tetap jalan
            import traceback
            print(f'[{fold_idx}] GAGAL fold {test_subject}: {exc!r}', flush=True)
            (fold_dir / 'FAILED.txt').write_text(traceback.format_exc())
            continue

        # ── Simpan hasil fold ──
        seed_reports = []
        for seed in range(args.seeds):
            run_dir = eval_dir / str(seed)
            report_path = run_dir / 'report.json'
            if report_path.exists():
                report = json.loads(report_path.read_text())
                seed_reports.append({
                    'seed': seed,
                    'val_score': report.get('metrics', {}).get('val', {}).get('score'),
                    'train_score': report.get('metrics', {}).get('train', {}).get('score'),
                    'test_score': report.get('metrics', {}).get('test', {}).get('score'),
                    'best_epoch': report.get('best_epoch'),
                    'time': report.get('time'),
                })
        shutil.copy(data_dir / 'test_split.csv', fold_dir / 'test_split.csv')
        shutil.copy(data_dir / 'val_split.csv', fold_dir / 'val_split.csv')
        done = {
            'fold': fold_idx,
            'test_subject': test_subject,
            'test_subjects': sorted(test_set),
            'train_subjects': train_parts.tolist(),
            'val_subjects': val_parts.tolist(),
            'rows': {'train': int(len(df_tr)), 'val': int(len(df_val)), 'test': int(len(df_test))},
            'inputs': {
                'features': str(args.features),
                'run_sha1': feat_fp,
                'run_key': run_key,
                'config': str(args.config),
            },
            'seeds': seed_reports,
        }
        (fold_dir / 'DONE.json').write_text(json.dumps(done, indent=2))
        if args.epochs_log and seed_reports:
            # Satu baris per fold, per seed: epoch terbaik + skor train/val.
            # `tr` jauh di atas `va` = hafalan; `ep0` = val tidak pernah membaik
            # dari inisialisasi. Keduanya penting untuk dibaca di log pipeline.
            def _s(r: dict) -> str:
                def f(v, nd=2):
                    return 'n/a' if v is None else f'{v:.{nd}f}'
                return (f"s{r['seed']} ep{r.get('best_epoch')} "
                        f"tr{f(r.get('train_score'))} va{f(r.get('val_score'))}")
            print(f"[{fold_idx}] OK {test_subject} | " + ' | '.join(_s(r) for r in seed_reports),
                  flush=True)
        else:
            print(f'[{fold_idx}] OK {test_subject} seeds={seed_reports}', flush=True)

        if args.epochs_trace:
            for seed in range(args.seeds):
                rows = epoch_trace_from_checkpoint(eval_dir / str(seed))
                if not rows:
                    continue
                n = len(rows)
                shown = rows if n <= args.epochs_trace else rows[:args.epochs_trace]
                tail = '' if n <= len(shown) else f' ...(+{n - len(shown)} ep)'
                accs = ' '.join(f'{r["val_acc"] * 100:.0f}' if r['val_acc'] is not None else '--'
                                for r in shown)
                trs = ' '.join(f'{r["train_ce"]:.2f}' if r['train_ce'] is not None else '--'
                               for r in shown)
                vas = ' '.join(f'{r["val_ce"]:.2f}' if r['val_ce'] is not None else '--'
                               for r in shown)
                best = max(rows, key=lambda r: (r['val_acc'] is not None, r['val_acc']))
                print(f'      s{seed} val_acc%/epoch  : {accs}{tail}', flush=True)
                print(f'      s{seed} train_loss/epoch: {trs}{tail}', flush=True)
                print(f'      s{seed} val_loss/epoch  : {vas}{tail}', flush=True)
                print(f'      s{seed} -> best ep{best["epoch"]} = '
                      f'{best["val_acc"] * 100:.0f}% | {n} epoch total', flush=True)
                # Overfit terdeteksi kalau train loss turun tapi val loss naik.
                if rows[0]['train_ce'] is not None and rows[-1]['val_ce'] is not None:
                    d_tr = rows[-1]['train_ce'] - rows[0]['train_ce']
                    d_va = rows[-1]['val_ce'] - rows[0]['val_ce']
                    if d_tr < 0 and d_va > 0:
                        print(f'      s{seed} !! OVERFIT: train loss {d_tr:+.2f} '
                              f'(turun) tapi val loss {d_va:+.2f} (naik) -> model '
                              'menghafal, tidak menambah kemampuan generalisasi.',
                              flush=True)

    print('\nSelesai. Hasil: exp/tabr/%s/fold_*/' % dataset_name, flush=True)


if __name__ == '__main__':
    main()

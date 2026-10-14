# Perbaikan Pipeline v3 — Re-spotting + Re-ekstraksi

Sesi 2026-10-06 (lanjutan `perbaikan-ekstraksi-v2.md`).

v2 memperbaiki **ekstraksi** (tanda arah, frame onset, apex palsu). v3 memperbaiki
**spotting** dan menghapus akar penyimpangan konfigurasi. Karena `block_size`
dipakai spotting, perbaikan ini menuntut **re-spotting penuh** — bukan sekadar
re-ekstraksi.

Semua keluaran lama tetap utuh: pipeline baru menulis ke `output/apex_v2/` dan
`experiments/features/apex/*_v3*`.

---

## 0. Ringkasan perubahan

| # | Perubahan | Alasan | Dampak |
|---|---|---|---|
| 1 | `block_size` POC **7 → 9** | saturasi turun ~70% (diukur) | event & fitur berubah |
| 2 | Definisi ROI **disatukan** ke satu modul | ada 5 salinan, sudah terbukti menyimpang | hilangnya tumpang tindih |
| 3 | `mata` = **kelopak saja** (36-41 / 42-47) | sebelumnya `mata` ⊃ `alis` → fitur redundan | `mata_*` berubah arti |
| 4 | Typo di `vektor.py`: `len(temp_y) or len(temp_y)` → `len(temp_x) or len(temp_y)` | bug logika | puncak ambigu tertangani benar |
| 5 | `FEAT_DATASET_ROOT` / `FEAT_METADATA_PATH` (env) | bisa menunjuk keluaran baru tanpa menimpa lama | — |

---

## 1. Akar masalah: definisi yang disalin lima kali

Definisi ROI/target_size/block_size ada di **lima tempat**:

1. `comparasion/core/config.py`
2. `scripts/spotting.py`
3. `scripts/extract_features_poc_abs.py`
4. `scripts/extract_features_roi.py`
5. `comparasion/core/pipeline.py` (memakai `config.block_size`)

Dan sudah **terbukti menyimpang**:

| | spotting | ekstraksi (sebelum v3) |
|---|---|---|
| `mata_kiri` | `36-41` (kelopak) | `17-21 + 36-41` (alis + kelopak) |
| `mata_kanan` | `42-47` | `22-26 + 42-47` |
| `alis_kiri` target | `(48, 20)` | `(64, 24)` |

Akibat nyata: `alis_kiri` **himpunan bagian** dari `mata_kiri`, jadi kedua fitur
mengukur wilayah yang sama (redundan), dan sinyal yang dipakai spotting berbeda
dari ROI yang dipakai fitur.

### Perbaikan

Satu modul baru: **`features_extraction/roi_config.py`** — satu-satunya sumber
kebenaran. `comparasion/core/config.py`, `scripts/spotting.py`,
`scripts/extract_features_poc_abs.py`, dan `scripts/extract_features_roi.py`
sekarang meng-import dari situ. Sudah diverifikasi keempatnya menghasilkan
nilai identik.

ROI kanonik (tidak tumpang tindih, diverifikasi `irisan alis & mata = KOSONG`):

```python
REGIONS = {
    'mulut':      range(48, 68),   # 48-67
    'mata_kiri':  range(36, 42),   # kelopak/bola mata
    'mata_kanan': range(42, 48),
    'alis_kiri':  range(17, 22),   # alis saja
    'alis_kanan': range(22, 27),
}
TARGET_SIZE = {'mulut': (70,35), 'mata_*': (48,32), 'alis_*': (64,24)}
BLOCK_SIZE = 9
```

**Kenapa `mata` dipisah dari `alis`:** gerakan alis (AU1/AU2/AU4) dan gerakan
kelopak (AU5/AU7) adalah sinyal yang **berbeda secara diagnostik**. Menggabung
keduanya (seperti sebelumnya) menghapus perbedaan itu dan membuat dua fitur
saling menyalin.

---

## 2. `block_size`: 7 → 9, dari pengukuran bukan tebakan

Saturasi POC terjadi saat perpindahan melebihi `(block_size-1)/2`; puncak mentok
di tepi blok dan informasi gerakan hilang. Diukur pada 18 clip × 8 frame
(`.amp/in/measure_blocksize.py`), **fraksi BLOK** yang mentok:

| block_size | batas | mulut | mata_kiri / kanan | alis_kiri / kanan | blok/ROI (mulut/mata/alis) |
|---|---|---|---|---|---|
| **7** | ±3 | **4,62%** | 5,16% / 5,43% | 4,09% / 5,03% | 50 / 24 / 27 |
| **9** | ±4 | **1,37%** | 1,64% / 1,78% | 1,66% / 1,81% | 21 / 15 / 14 |
| 11 | ±5 | 1,21% | 0,44% / 1,94% | 0,49% / 0,56% | 18 / 8 / 10 |
| 13 | ±6 | 0,85% | 0,82% / 1,41% | 0,18% / 0,00% | 10 / 6 / **4** |

**9 dipilih** karena:
- memangkas saturasi ~70% (4,62% → 1,37%);
- masih menyisakan blok cukup banyak di semua ROI (21/15/14);
- `block_size = 13` menurunkan saturasi lebih jauh **tapi membuat ROI alis hanya
  1 baris blok** (4 blok total) — praktis degenerate, jadi ditolak.

**Koreksi atas klaim saya sebelumnya.** Dokumen v2 sempat menyebut saturasi
"mulut 14,92% baris mentok". Itu dari kolom `max_m` — statistik maksimum antar
~50 blok, yang **justru dibuang** dari fitur (`--drop-features "_max_m$"`). Yang
masuk model adalah rata-rata antar blok, jadi angka yang relevan adalah fraksi
**blok** (4,62%), bukan fraksi baris. Saturasinya nyata tapi tidak separah yang
saya tulis. Sudah dikoreksi di `perbaikan-ekstraksi-v2.md` §4.

Distribusi magnitudo juga menunjukkan **p50 = 0,000** di semua ROI — mayoritas
blok statis, hanya sebagian kecil bergerak. Itu wajar untuk ROI yang sebagian
besar adalah kulit.

---

## 3. Typo di `vektor.py`

```python
# sebelum (bug): temp_y diperiksa dua kali, temp_x tidak pernah diperiksa
if (len(temp_y) > 1 or len(temp_y) > 1):
# sesudah
if (len(temp_y) > 1 or len(temp_x) > 1):
```

Dua puncak POC dengan korelasi sama (ambiguitas) seharusnya dianggap "tidak ada
gerakan" (pakai titik tengah). Sebelum perbaikan, ambiguitas yang hanya muncul di
sumbu-x **lolos**, sehingga blok itu menghasilkan arah gerak acak alih-alih nol.
Efeknya kecil tapi ini bug logika yang jelas.

---

## 4. Yang TIDAK diubah (dan kenapa)

| Tidak diubah | Alasan |
|---|---|
| Definisi ROI di `spotting.py` untuk `mata` | spotting memang sudah kelopak-saja; menyatukan ke kanonik berarti sinyal spotting **tidak berubah** untuk `mata`, jadi perubahan event bisa diatribusikan ke `block_size` |
| `top_k_apex = 5`, `merge_distance = 10`, `cutoff_ratio = 0.3` | parameter apex; tidak ada bukti cacat, dan mengubahnya menambah variabel tanpa dasar |
| `SPOT_PROM_REL = 0.04`, `SPOT_DISTANCE = 1` | idem |
| `max_m` tetap dibuang | nilainya tersensor by construction; `mean_*` lebih baik |
| `--brows` (mode 3 region lama) | dipertahankan untuk reproduksi `poc_abs_flatten_ordered.xlsx`; kini sumbernya kanonik |

---

## 5. Perintah yang dijalankan

```bash
# 1. Re-spotting -> output/apex_v2 (output/apex lama tidak disentuh)
SPOT_DATASET_ROOT="/run/media/finny/New Volume/dataset/anxiety_raw" \
SPOT_OUTPUT_ROOT="$PWD/output/apex_v2" \
SPOT_VIDEO_EXT=".avi" SPOT_ABS=1 SPOT_OVERWRITE=0 \
SPOT_NO_EVENT_SIGNAL=1 SPOT_SAVE_NEUTRAL=1 \
.venv/bin/python scripts/process_spotting_pipeline.py

# 2. Re-ekstraksi dari dataset baru
FEAT_WORKERS=3 FEAT_DATASET_ROOT="$PWD/output/apex_v2/dataset" \
FEAT_METADATA_PATH="$PWD/output/apex_v2/metadata.xlsx" \
.venv/bin/python scripts/extract_features_poc_abs.py \
  --roi-signals --baseline neutral \
  --output experiments/features/apex/poc_abs_roi_signals_v3.xlsx

# 3. Cache + fitur temporal + gerbang within-subject
.venv/bin/python scripts/build_feature_cache.py \
  --xlsx .../poc_abs_roi_signals_v3.xlsx --pkl .../poc_abs_roi_signals_v3_full.pkl
.venv/bin/python scripts/build_temporal_features.py \
  --input .../poc_abs_roi_signals_v3_full.pkl \
  --output .../poc_abs_roi_signals_v3_temporal.pkl --no-xlsx
```

---

## 6. Hasil

### 6.1 Stages 1-5 (SELESAI)

| | v2 (block_size 7, ROI tumpang tindih) | v3 (block_size 9, ROI kanonik) |
|---|---|---|
| event di metadata | 6.878 | **6.972** |
| sample / neutral.png | 560 / 560 | **560 / 560** |
| baris fitur | 104.194 | **100.817** |
| fitur statis | 35 | 35 |
| fitur temporal | 185 | 185 |
| `frame` minimum | 1 | **1** |
| error ekstraksi | 0 | **0** |

Jumlah event berubah (6.878 → 6.972, +1,4%) karena `block_size` mengubah sinyal
yang dipakai spotting. Itu **memang diharapkan** — bukan tanda kerusakan.

### 6.2 Gerbang within-subject (wasit utama)

| set fitur | fitur | acc | null | p |
|---|---|---|---|---|
| onset lama | 25 | 0,5833 | 0,4921 | 0,2637 |
| neutral lama | 25 | 0,5278 | 0,4981 | 0,4726 |
| v2 statis | 35 | 0,4167 | 0,4969 | 0,7910 |
| v2 temporal | 185 | 0,6667 | 0,4940 | 0,0746 |
| **v3 statis** | 35 | **0,4444** | 0,4942 | 0,7761 |
| **v3 temporal** | 185 | **0,6111** | 0,5004 | 0,1990 |

Grup kontrol: 0/35 dan 0/185 signifikan (kecuali 1/185 di v3 temporal — wajar,
sesuai ekspektasi FDR 5%). Tidak ada efek sesi yang terbawa.

**Bacaan jujur:**
- **v3 TIDAK memperbaiki gerbang.** v3 temporal 0,6111 (p=0,199) justru lebih
  rendah dari v2 temporal 0,6667 (p=0,075). Dengan n = 36 baris, selisih itu
  **di dalam derau** — jadi jangan disimpulkan v3 merugikan, tapi juga **tidak
  boleh diklaim v3 membaik**.
- **Tidak ada set fitur yang mencapai p < 0,05.** Semua masih setara tebak acak
  secara statistik.
- Perbaikan v3 tetap sahih secara rekayasa (saturasi turun ~70%, ROI tidak lagi
  redundan, satu sumber kebenaran konfigurasi, tiga bug diperbaiki) — tapi
  **perbaikan itu tidak diterjemahkan jadi sinyal yang terukur**.

### 6.3 Training LOSO (GAGAL di percobaan pertama, lalu diperbaiki)

Percobaan pertama dengan `tabr_loso_roi25_reg_ce.toml` gagal di **56/56 fold**:
`KeyError('cross-entropy')`. Penyebab dan perbaikannya di
`report/documentation/changes-log.md` Iterasi 4.21 — ringkasnya: `lib/metrics.py`
hanya menulis `cross-entropy` kalau satu part punya >1 kelas, sedangkan di LOSO
test = 1 subjek = 1 kelas. Sudah diperbaiki dengan `labels` eksplisit.

Setelah perbaikan, angka training **belum ada** — belum dijalankan ulang.

### 6.4 Hasil training — KOREKSI (ada bug di collector saya)

**Koreksi penting.** Angka "pooled antar seed" dan kolom CI di versi pertama
bagian ini **salah**. Penyebabnya bug di `collect_loso_results.py`: `pooled['proba']`
diganti dengan rata-rata antar seed, **tapi `pred` tidak dihitung ulang**, dan
`drop_duplicates('subject')` menyisakan baris **seed 0**. Jadi yang dilaporkan
sebagai "pooled antar seed" sebenarnya **hanya seed 0**.

Bukti: v3 seed 0 accuracy = 0,4107 = angka "Pooling antar seed" di summary.md lama.
Sudah diperbaiki (hitung ulang `pred` dari proba rata-rata) dan ketiga run
dikumpulkan ulang. Semua angka di bawah sudah memakai versi benar.

**Angka yang benar — seed-ensemble (proba dirata-rata antar seed, lalu threshold):**

| run | fitur | config | accuracy | CI 95% | MCC | balAcc | sens | spec |
|---|---|---|---|---|---|---|---|---|
| reg | v2, 237 | akurasi | **0,6250** | 0,4941–0,7399 | **+0,2272** | 0,6032 | 0,400 | 0,807 |
| v3 | v3, 370 | cross-entropy | 0,6071 | 0,4763–0,7242 | +0,1910 | 0,5910 | 0,440 | 0,742 |
| v3acc | v3, 370 | akurasi | 0,5357 | 0,4070–0,6598 | +0,0464 | 0,5226 | 0,400 | 0,645 |
| — | — | baseline mayoritas | 0,5536 | — | — | — | — | — |

Rata-rata antar seed (bukan ensemble):

| run | accuracy | MCC |
|---|---|---|
| reg | 0,5952 ± 0,0734 | +0,1706 ± 0,1491 |
| v3 (CE) | 0,5238 ± 0,0803 | +0,0154 ± 0,1664 |
| v3acc | 0,5179 ± 0,0636 | +0,0054 ± 0,1287 |

**Bacaan yang benar:**
- **Ketiga CI 95% MEMUAT baseline mayoritas 0,5536.** Jadi tidak ada satu pun run
  yang terbukti lebih baik dari menebak kelas mayoritas. Termasuk `reg`.
- Klaim saya sebelumnya ("CI v3 0,2917–0,5412 seluruhnya di bawah baseline →
  lebih buruk dari mayoritas") **DICABUT** — itu CI seed 0, bukan CI pooled.
- Per-seed MCC saling tumpang tindih berat (reg −0,02…+0,34; v3acc −0,18…+0,11),
  jadi **selisih antar run tidak bisa dibedakan dari derau**.

### 6.5 Isolasi: yang merusak early stopping adalah FITUR, bukan cross-entropy

`reg` vs `v3acc` adalah isolasi bersih (config **sama**, hanya fitur berbeda).
Ternyata **kedua** run v3 berhenti di epoch sangat awal:

| run | config | best_epoch median | fold berhenti di epoch ≤ 1 |
|---|---|---|---|
| reg | akurasi | 5 (mean 12,2) | 34/168 |
| v3 | cross-entropy | 1 (mean 2,4) | **101/168** |
| v3acc | akurasi | 1 (mean 3,9) | **97/168** |

**Klaim saya sebelumnya ("cross-entropy yang merusak training") DICABUT.**
Kalau CE penyebabnya, `v3acc` (config akurasi) seharusnya berperilaku seperti
`reg`. Kenyataannya v3acc juga berhenti di 97/168 fold.

Penyebabnya **jumlah fitur**: 370 kolom untuk 44 baris train (d/n 8,4) vs 237
(d/n 5,4). Dengan fitur lebih banyak, akurasi val memuncak di epoch 0-1
(praktis acak) lalu turun — jadi early stopping memilih model yang belum
belajar. Ini persis masalah rezim *high-dimensional low-sample-size* yang sudah
didokumentasikan di `research-tabr-config-small-data.md`.

**Konsekuensi:** menambah fitur (v3) **memperburuk** masalah dimensi, dan itu
lebih besar dampaknya daripada perbaikan ekstraksi apa pun.

### 6.6 Yang terbukti berguna dan yang tidak

| Lever | Hasil |
|---|---|
| Ambang dari val | **BERGUNA** — bias prediksi −0,1190 → **+0,0238** |
| Fitur arah bertanda + frame onset + fix apex | Tidak terukur manfaatnya |
| `block_size` 9 (saturasi −70%) | Tidak terukur manfaatnya |
| ROI tidak tumpang tindih | Tidak terukur manfaatnya |
| Pemilihan epoch cross-entropy | **TIDAK BERGUNA** (bukan penyebab utama, tapi tetap tidak menolong) |
| Menambah fitur jadi 370 | **MERUGIKAN** (early stopping makin dini) |

Semua perbaikan v3 sahih secara rekayasa dan ketiga bug yang ditemukan memang bug
nyata — **tapi tidak satu pun menghasilkan sinyal yang bisa diukur.** Gerbang
within-subject juga tetap tidak signifikan (v3 temporal 0,6111, p = 0,199).

**Langkah berikutnya yang paling masuk akal: A/B reduksi dimensi** — bukan
menambah apa pun lagi. Semua tabel fitur sudah ada, tidak perlu re-ekstraksi:

```bash
# 370 -> ~185 fitur (buang std)
./run loso --dataset convat_apex_anxiety_loso_v3_d1 \
  --features experiments/features/apex/poc_abs_roi_signals_v3_temporal.pkl \
  --aggregate subject --drop-features "_std$" \
  --config experiments/configs/tabr_loso_roi25_reg.toml

# 370 -> ~90 fitur (sisakan inti)
./run loso --dataset convat_apex_anxiety_loso_v3_d2 \
  --features experiments/features/apex/poc_abs_roi_signals_v3_temporal.pkl \
  --aggregate subject --drop-features "_std$|_ttp_|_rise_|_fall_|_auc_" \
  --config experiments/configs/tabr_loso_roi25_reg.toml

# ROI25 murni -> ~70 fitur (d/n 1,6)
./run loso --dataset convat_apex_anxiety_loso_v3_d3 \
  --features experiments/features/apex/poc_abs_roi_signals_v3_full.pkl \
  --aggregate subject \
  --config experiments/configs/tabr_loso_roi25_reg.toml
```

Wasit: **MCC seed-ensemble** + apakah CI keluar dari baseline mayoritas 0,5536.


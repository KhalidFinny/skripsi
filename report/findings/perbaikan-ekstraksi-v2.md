# Perbaikan Ekstraksi Fitur v2 — Tiga Cacat yang Ditemukan

Sesi 2026-10-06. Audit `scripts/extract_features_poc_abs.py` menemukan **tiga
cacat nyata** pada tabel fitur yang selama ini dipakai. Semuanya diperbaiki dan
ekstraksi dijalankan ulang ke berkas **v2** (tabel lama TIDAK ditimpa).

Konteks strategi: `report/findings/strategi-bebas-bias-dan-overfitting.md`.
Bias yang sudah terukur: `report/findings/analisis-bias-loso.md`.

---

## 0. Ringkasan

| # | Cacat | Bukti | Dampak | Status |
|---|---|---|---|---|
| 1 | **Tanda arah dibuang** — hanya `mean(\|x\|)`, `mean(\|y\|)` yang disimpan; `theta` dan `quadranLabel` dihitung tapi tidak dipakai | `extract_features_poc_abs.py:347-348` vs `quadran.py` | mulut naik vs turun jadi fitur identik | **DIPERBAIKI** |
| 2 | **Frame onset hilang** — frame 1 dibuang di SEMUA event | kolom `frame` tabel lama min = **2**, 0 baris frame 1 | 6.878 baris (7,1%) hilang, termasuk frame onset | **DIPERBAIKI** |
| 3 | **Sinyal apex dipalsukan** — `roi_signals` di-seed `0.0` | `extract_features_poc_abs.py:427` (lama) | puncak palsu di indeks 0, nomor frame apex bergeser 1 | **DIPERBAIKI** |
| 4 | **Saturasi POC** — `max_m` mentok 4.243 | mulut: **14,92%** baris mentok, 59,8% > 3,0 | gerakan besar terpotong | **BELUM** (butuh re-spotting) |

---

## 1. Cacat #1 — Tanda arah dibuang (paling penting)

### Apa yang terjadi

`features_extraction/quadran.py` menghitung **enam** besaran per blok:

```
[block_id, X, Y, theta, magnitude, quadranLabel]
```

`X` dan `Y` **bertanda** (`oX`/`oY` dari `vektor.py`, rentang -3..+3). `theta`
(sudut 0-360°) dan `quadranLabel` (Q1-Q4) juga sudah dihitung.

Tapi `extract_roi_signal_row` hanya menyimpan:

```python
row[f'{comp}_mean_abs_x'] = float(np.mean(np.abs(xs)))   # <-- tanda dibuang
row[f'{comp}_mean_abs_y'] = float(np.mean(np.abs(ys)))   # <-- tanda dibuang
```

Akibatnya **`theta` dan `quadranLabel` terbuang seluruhnya**, dan tanda arah
hilang. Untuk ekspresi wajah ini fatal: sudut mulut **naik** (senyum/tegang) dan
**turun** (sedih/menahan) menghasilkan fitur yang **identik**.

### Perbaikan

Tambah dua fitur bertanda per ROI:

```python
row[f'{comp}_mean_x'] = float(np.mean(xs))
row[f'{comp}_mean_y'] = float(np.mean(ys))
```

**Kenapa ini sahih, bukan sekadar menambah fitur:** karena acuan POC-ABS adalah
wajah **NETRAL** (bukan onset), arah perpindahan konsisten sepanjang event. Kalau
acuannya frame onset, `mean(X)` akan saling menghapus (otot keluar lalu kembali)
dan fitur bertanda jadi tidak berguna. Jadi perbaikan ini **bergantung** pada
baseline netral yang sudah dipakai.

### Verifikasi

| Pemeriksaan | Hasil |
|---|---|
| Kolom fitur | 25 → **35** (5 ROI × 2 fitur baru) |
| `mean_x` punya dua tanda? | ya: **44,3% negatif**, 32,9% positif |
| Redundan dengan `mean_abs_x`? | **tidak** — korelasi \|mean_x\| vs mean_abs_x hanya **0,587** |
| Nilai nol (tidak ada gerak) | 23-45% per ROI (wajar) |

Korelasi 0,59 itu buktinya: fitur bertanda membawa informasi yang **tidak** ada
di fitur absolut, bukan duplikat.

---

## 2. Cacat #2 — Frame onset hilang dari semua event

### Apa yang terjadi

```python
if idx == 0:
    reference = baseline_image if baseline_image is not None else image
    ...
    continue          # <-- frame 0 dibuang SELALU
```

`continue` itu benar kalau acuannya **frame 0 sendiri** (POC(frame0, frame0) = 0,
tidak informatif). Tapi kalau acuannya **neutral.png**, frame 0 adalah frame
**onset** yang sah — perbandingannya bermakna. Versi lama membuangnya di kedua
mode.

### Bukti

```
kolom `frame` tabel lama: min = 2, max = 135
baris dengan frame == 1 : 0
```

Setiap 6.878 event kehilangan frame onset-nya → **6.878 baris (7,1%)** hilang,
dan yang hilang justru frame tempat ekspresi **mulai** — informasi onset yang
persis dibutuhkan oleh deskriptor temporal `_rise`.

### Perbaikan

Buang frame 0 hanya kalau acuannya frame 0 sendiri:

```python
own_baseline = baseline_image is None
...
if own_baseline:
    del image, reference
    continue
# acuan netral -> frame onset tetap diproses sebagai baris data
```

### Verifikasi

Tabel v2: `frame` min = **1**, dan ada **1 baris frame 1 per event**.

---

## 3. Cacat #3 — Sinyal apex dipalsukan

```python
roi_signals = {comp: [0.0] for comp in WORKER_CONFIG.regions}   # <-- 0.0 palsu
```

List dimulai dengan `0.0` yang **bukan frame apa pun**. `detect_roi_apex` lalu
mencari puncak di sinyal yang punya lembah palsu di indeks 0, dan karena indeks
list dipakai untuk memetakan nomor frame (`clip.onset_frame + phase['start']`),
**semua nomor frame apex bergeser satu**.

Perbaikan: seed dengan list kosong `[]`. Setelah itu pemetaan
`onset_frame + index` jadi benar (list indeks j = frame_no j+1).

**Dampak terbatas:** `roi_apex.xlsx` **tidak dipakai hilir** (hanya
`*_full.pkl` dan `*_temporal.pkl` yang masuk training). Jadi ini memperbaiki
berkas pelengkap, bukan tabel fitur utama.

---

## 4. Cacat #4 — Saturasi POC (DIPERBAIKI di v3, lihat `perbaikan-pipeline-v3.md`)

`block_size = 7` membuat perpindahan maksimum yang bisa diwakili hanya **±3
piksel**; `magnitude` mentok di `3*sqrt(2) = 4.243`.

**Angka yang benar (koreksi).** Dokumen ini awalnya menyebut "mulut 14,92% baris
MENTOK dan 59,8% baris > 3,0" dari kolom `max_m`. Itu **menyesatkan**, karena:

- `max_m` = maksimum antar ~50 blok dalam satu frame. Statistik itu memang sering
  mentok (14,92% baris), **tapi `max_m` justru dibuang** dari fitur
  (`--drop-features "_max_m$"`), jadi tidak pernah masuk model.
- Yang benar-benar dipakai adalah **rata-rata antar blok** (`mean_m`,
  `mean_abs_x/y`, `motion_count`). Untuk itu yang relevan adalah **fraksi BLOK
  yang mentok**, bukan fraksi baris.

**Pengukuran langsung per blok** (18 clip × 8 frame, `magnitude` dari Quadran):

| block_size | batas | fraksi BLOK mentok (mulut) | mata | alis |
|---|---|---|---|---|
| **7** | ±3 | **4,62%** | 5,16% / 5,43% | 4,09% / 5,03% |
| 9 | ±4 | 1,37% | 1,64% / 1,78% | 1,66% / 1,81% |
| 11 | ±5 | 1,21% | 0,44% / 1,94% | 0,49% / 0,56% |
| 13 | ±6 | 0,85% | 0,82% / 1,41% | 0,18% / 0,00% |

Jadi pada `block_size = 7` sekitar **2,3 dari 50 blok** per frame mulut mentok —
nyata tapi tidak separah yang tersirat dari angka `max_m`. Distribusi magnitudo
juga menunjukkan **p50 = 0,000** di semua ROI: mayoritas blok memang statis, dan
hanya sebagian kecil yang bergerak.

**Perbaikan (v3): `block_size = 9`** memangkas saturasi ~70% (4,62% → 1,37%)
tanpa merusak resolusi spasial. `block_size = 13` menurunkan saturasi lebih
banyak lagi tapi membuat ROI alis tinggal **1 baris blok** (degenerate), jadi
tidak dipakai. Detail keputusan ada di `perbaikan-pipeline-v3.md`.


---

## 5. Yang TIDAK diperbaiki (dan kenapa)

| Bukan cacat | Alasan |
|---|---|
| `max_m` tersensor lalu dibuang | Sudah ditangani benar oleh `--drop-features "_max_m$"`; akar masalahnya ada di #4 |
| Definisi ROI spotting vs ekstraksi berbeda | `spotting.py` memakai `mata_kiri` = kelopak saja (36-41); ekstraksi memakai 17-21 + 36-41 (alis + kelopak). Ini **tidak konsisten** tapi tidak salah: spotting butuh sinyal gerak, ekstraksi butuh kotak fitur. Dibiarkan, dicatat di sini supaya tidak jadi kejutan. |
| `mean_abs_x`/`mean_abs_y` dibuang | Sengaja **ditambah**, bukan diganti: absolut = intensitas, bertanda = arah. Keduanya dipakai. |

---

## 6. Berkas keluaran

Tabel lama **tidak ditimpa** (sesuai `Must Not Forget` di plan):

| Baru (v2) | Lama (tetap ada) |
|---|---|
| `experiments/features/apex/poc_abs_roi_signals_neutral_v2.xlsx` | `..._neutral.xlsx` |
| `experiments/features/apex/poc_abs_roi_signals_neutral_v2_full.pkl` | `..._neutral_full.pkl` |
| `experiments/features/apex/poc_abs_roi_signals_neutral_v2_temporal.pkl` | `..._neutral_temporal.pkl` |

Perubahan kode:
- `scripts/extract_features_poc_abs.py` — 3 perbaikan + flag `--limit` (untuk
  memeriksa perubahan tanpa menunggu ekstraksi penuh)
- `scripts/build_temporal_features.py` — regex sinyal dasar diperluas supaya
  `mean_x`/`mean_y` **ikut** diproses jadi fitur temporal (kalau tidak, fitur
  baru akan diam-diam dibuang oleh whitelist)

---

## 7. Hasil verifikasi setelah re-ekstraksi

### 7.1 Integritas tabel

| | lama | v2 |
|---|---|---|
| baris | 97.317 | **104.194** (+6.877, +7,1%) |
| fitur statis | 25 | **35** (+10 bertanda) |
| fitur temporal | 125 | **185** (+60) |
| `frame` minimum | 2 | **1** |
| fitur hilang | – | **tidak ada** |
| subjek / event | 56 / 6.878 | 56 / 6.878 |
| error ekstraksi | 0 | **0** |

`frame == 1` ada di 6.877 dari 6.878 event; satu event tidak punya baris frame 1
karena deteksi wajah gagal pada frame onset-nya (perilaku yang sama seperti frame
lain), bukan kegagalan.

### 7.2 Gerbang within-subject (wasit utama)

| set fitur | fitur | acc within-subject | null | p |
|---|---|---|---|---|
| onset lama | 25 | 0.5833 | 0.4921 | 0.2637 |
| neutral lama | 25 | 0.5278 | 0.4981 | 0.4726 |
| **neutral v2 statis** | 35 | 0.4167 | 0.4969 | 0.7910 |
| **neutral v2 temporal** | 185 | **0.6667** | 0.4940 | **0.0746** |

Grup **kontrol bersih di semua set** (0/35 dan 0/185 signifikan) — jadi tidak ada
efek sesi yang ikut terbawa, tidak seperti baseline onset lama (20/25 "berubah"
vs 25/25 kontrol).

**Bacaan jujur:**
- Yang bergerak adalah set **temporal**: 0.5278 (p=0,47) → **0.6667 (p=0,075)**.
  Ini hasil gerbang terbaik sejauh ini, dan arahnya benar.
- **Tapi p=0,075 belum signifikan di ambang 5%.** Jangan diperlakukan sebagai
  bukti.
- Set **statis v2 justru turun** (0.4167, p=0,79). Dengan n = 36 baris, selisih
  0,42 vs 0,67 itu **di dalam derau** — jangan disimpulkan bahwa fitur bertanda
  merugikan; 10 fitur baru di antara 185 tidak akan menjelaskan selisih sebesar itu.
- Artinya: perbaikan ekstraksi **memindahkan gerbang dari jelas-null ke marginal**,
  belum ke signifikan. Satu-satunya cara memutuskan adalah A/B LOSO penuh.

### 7.3 Batas harapan (jujur)

Perbaikan ini **menambah informasi yang sebelumnya dibuang** dan
**mengembalikan 7,1% baris yang hilang**. Itu perbaikan representasi yang nyata.

Yang **tidak** dijanjikan: akurasi 70%, dan belum terbukti bahwa fitur bertanda
adalah penyebab kenaikan gerbang — yang naik adalah kombinasi fitur bertanda +
frame onset yang kembali + 150 deskriptor temporal.

Wasit yang benar untuk menilai: **MCC** di protokol LOSO penuh, dibandingkan
terhadap run `reg` (MCC +0,1706), bukan accuracy dan bukan gerbang ini.


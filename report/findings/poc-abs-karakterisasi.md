# Karakterisasi POC-ABS: apa yang sebenarnya diukur, dan apakah bisa membawa sinyal

Tanggal: 2026-10-08
Data: `poc_abs_roi_signals_v3_full.pkl` (97.808 baris frame, 35 sinyal dasar),
`poc_abs_roi_signals_v3_poc_temporal.pkl` (185 sinyal + deskriptor dinamika).
Protokol uji: LOSO 56 subjek, satuan label = sesi (peserta x fase) = 112 unit.

---

## 1. Rantai pengukuran (apa yang sebenarnya dihitung)

```
frame netral (median 10 frame pertama video)
        |
        v
crop ROI dari 68 landmark dlib  ->  resize ke ukuran TETAP
        |
        v
POC per blok 9x9 (fft2 -> R = F_ref*conj(F_cur)/|...| -> ifft2 -> fftshift)
        |
        v
Vektor: cari puncak POC; puncak != tengah => ada gerakan
        oX = arah-x bertanda (-4..4), oY = arah-y bertanda (-4..4)
        |
        v
Quadran: hitung sudut tetha + magnitude = sqrt(oX^2 + oY^2)
        |
        v
Agregasi antar-blok per frame  ->  7 sinyal per ROI
        |
        v
Agregasi antar-frame per event ->  mean + std  (mode --aggregate subject)
```

**Yang diukur:** besar pergeseran lokal wajah **relatif terhadap frame netral sesi itu**,
di dalam tiap ROI. Bukan ekspresi absolut, melainkan simpangan dari wajah netral orang tersebut.

### 7 sinyal per ROI (35 total, 5 ROI)

| sinyal | arti | dominasi identitas |
|---|---|---|
| `mean_m` | rata-rata magnitude gerakan | 0,73 |
| `max_m` | magnitude gerakan terbesar | 0,82 |
| `mean_abs_x` | rata-rata **besar** gerak horizontal | 0,75 |
| `mean_abs_y` | rata-rata **besar** gerak vertikal | 0,72 |
| `motion_count` | fraksi blok yang bergerak | 0,74 |
| `mean_x` | rata-rata **arah** horizontal (bertanda) | 0,70 |
| `mean_y` | rata-rata **arah** vertikal (bertanda) | 0,60 |

"Dominasi identitas" = proporsi varians yang dijelaskan perbedaan antar-orang.
> 0,5 berarti fitur lebih menyerupai "sidik jari orang" daripada kondisi.
**Median 0,79** — fitur 79% identitas.

---

## 2. Temuan struktural

### 2.1 Grid blok membuang 21-31% piksel ROI

ROI di-resize ke ukuran tetap, lalu dipotong jadi blok 9x9. Sisa pembagian **dibuang**:

| ROI | ukuran | blok | piksel terpakai | terbuang |
|---|---|---|---|---|
| mulut | 70x35 | 3x7 = 21 | 69% | **31%** |
| mata_kiri/kanan | 48x32 | 3x5 = 15 | 79% | 21% |
| alis_kiri/kanan | 64x24 | 2x7 = 14 | 74% | 26% |

Konsekuensi: resolusi spasial sangat kasar (14-21 blok per ROI), dan sebagian tepi ROI
(mis. 8 dari 35 baris mulut) tidak pernah dilihat.

### 2.2 Sudut/kuadran dihitung lalu DIBUANG

`Quadran.getQuadran()` menghitung `tetha` (sudut 0-360) dan label kuadran (Q1-Q4).
`extract_roi_signal_row()` hanya memakai kolom magnitude (b[4]), X (b[1]), Y (b[2]).
**`tetha` dan label kuadran tidak pernah jadi fitur.** Informasi arah yang paling
terkode (sudut) hilang; yang tersisa hanya proyeksi x/y mentah.

### 2.3 Hanning window adalah NO-OP (bukan bug yang merugikan)

`POC.hannCalc()`:
```python
window = np.hanning(self.blockSize)     # shape (9,)  -> vektor 1D
window = np.dot(window.T, window)       # -> SKALAR 3.0, bukan matriks 2D
```
`np.dot` dua vektor 1D menghasilkan skalar (inner product), bukan outer product.
Yang benar untuk jendela 2D adalah `np.outer(hann, hann)`.

Karena phase correlation menormalkan `R1/|R1|`, pengali skalar **hilang sepenuhnya**.
Terbukti: hasil POC dengan window skalar **identik bit-per-bit** dengan tanpa window.

**Tetapi jangan diperbaiki.** Diuji pada 400 patch sintetis dengan pergeseran diketahui:

| window | estimasi pergeseran tepat |
|---|---|
| skalar (sekarang) | **100,0%** |
| 2D hann (yang "benar") | 69,8% |
| tanpa window | 100,0% |

Jendela 2D justru **merusak** akurasi pada blok 9x9: tepi di-nol-kan, informasi hilang,
puncak bergeser. Jadi kode ini dead code yang kebetulan tidak merugikan. **Dibiarkan apa adanya.**

### 2.4 Referensi netral = median 10 frame pertama

`neutral.png` = `np.median` dari 10 frame pertama video. Kalau perekaman dimulai sebelum
subjek tenang, referensinya tidak netral. Ini berlaku sama untuk semua subjek, tapi
kualitas referensi bisa berbeda sistematis antara sesi *before* dan *after*.

### 2.5 `mean_x`/`mean_y` terencerkan blok diam

`mean_x = np.mean(xs)` dihitung atas **semua** blok, termasuk yang tidak bergerak (nilainya 0).
Jadi `mean_x` mencampur dua hal: berapa banyak blok bergerak, dan ke arah mana.
Ukuran yang lebih bersih (rata-rata atas blok bergerak saja) belum pernah diuji.

---

## 3. Uji apakah ada sinyal

### 3.1 Sinyal dasar (35), uji berpasangan 18 subjek yang labelnya berubah

- Signifikan p<0,05: **1/35** — harapan acak 1,75. **Tidak ada lebih dari kebetulan.**
- FDR-BH q<0,05: **0/35**. Bonferroni: **0/35**.
- AUC 1-fitur > 0,60: **0/35**.

### 3.2 Deskriptor dinamika (185), uji yang sama

- Signifikan p<0,05: **20/185** — harapan acak 9,2 (2,2x pengayaan)
- **Tetapi** FDR-BH q<0,05: **0/185**. Bonferroni: **0/185**.
- Uji permutasi (acak tanda selisih per subjek, 3000 kali):
  observasi 21 vs null 8,8 ± 11,0 → **p = 0,109. Tidak signifikan.**
- AUC 1-fitur tertinggi 0,6464 (`alis_kiri_mean_abs_x_rise`), tapi null max AUC
  = 0,6431 ± 0,0249 → **p = 0,40**. Itu murni efek seleksi 185 fitur.

**Kesimpulan: tidak ada satu pun fitur yang lolos koreksi multiple-comparison.**

### 3.3 Apakah sinyal ada di distribusi, bukan rata-rata?

Dominasi identitas per statistik sesi: `mean` 0,68 | `std` 0,79 | `iqr` 0,78 |
`p90` 0,77 | `skew` 0,62. Tidak ada yang lolos dari dominasi identitas.

---

## 4. Dua eksperimen: mengubah APA yang diukur

Bukan menambah/mengurangi jumlah fitur, tapi memilih **komponen keluaran POC-ABS**
yang dipakai. Keduanya tetap POC-ABS murni.

### E1 — arah bertanda saja
`experiments/features/apex/poc_signed_full.pkl` → **20 fitur**
Hanya `mean_x` + `mean_y` (arah), membuang semua magnitudo (`mean_m`, `mean_abs_x/y`, `motion_count`).
Hipotesis: magnitudo = "seberapa banyak orang ini bergerak" (identitas, dominasi 0,87);
arah = "ke mana wajahnya bergerak" (lebih dekat ke kondisi, dominasi 0,60).

### E2 — dinamika saja
`experiments/features/apex/poc_dynamics_full.pkl` → **180 fitur**
Hanya deskriptor lintasan onset→apex→offset (`rise`, `fall`, `ttp`), membuang level
(`peak`, `auc`). Hipotesis: kecemasan adalah fenomena **temporal**; cara gerakan
naik dan turun lebih informatif daripada besarnya.

### Cara menjalankan

```bash
cd /home/finny/projects/Skripsi
TRAIN_FEATURES=$PWD/experiments/features/apex/poc_signed_full.pkl \
  ./scripts/run_pipeline_v3.sh --from 6

TRAIN_FEATURES=$PWD/experiments/features/apex/poc_dynamics_full.pkl \
  ./scripts/run_pipeline_v3.sh --from 6
```

### Ekspektasi jujur

Berdasarkan §3, **keduanya kemungkinan besar tetap di level acak.** Yang sudah diuji dan nol:
POC+geometri (0,4723), POC semua sinyal 360 fitur (0,4852), POC 20 sinyal (0,4589),
tabel lama 240 fitur (0,5385). Semua di dalam derau antar-seed (0,09-0,18).

E1/E2 tetap layak dijalankan karena keduanya **belum pernah dicoba** dan menyasar
komponen yang berbeda secara prinsip — bukan sekadar variasi jumlah fitur.

---

## 5. Catatan untuk arah live video

Pipeline ini **training dari rekaman**, dan itu benar. Kebutuhan real-time
(ring buffer per frame, referensi netral bergerak) adalah urusan tahap **inference**
yang terpisah, di luar lingkup repo ini. Tidak ada yang perlu diubah di sini.

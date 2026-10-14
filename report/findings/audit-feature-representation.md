# Representasi Fitur POC-ABS: apa yang sebenarnya membawa sinyal

> **PENTING — baca §10 dulu.** Angka di §3-§8 diukur pada tabel fitur dari run
> yang **pernah terputus** (sesi `before` tidak lengkap: 35.019 baris, seharusnya
> 35.477). Run ulang BERSIH ada di §10 dan angkanya menggantikan: gerbang `rise`
> adalah **BA 0,7500 (p 0,0100)**, bukan 0,8333. Arah kesimpulannya tidak berubah,
> tapi angka yang dipakai di tesis harus dari §10.

Tanggal: 2026-10-10
Konteks: setelah spotting diperbaiki (Iterasi 4.49) dan pipeline kecemasan
diregenerasi (4.50), klasifikasi LOSO masih di bawah acak. Sesi ini menyerang
**representasi fitur**.

Data: `poc_abs_roi_signals_v3fixed_poc_temporal.pkl` — 62.955 baris frame,
2.647 event, 335 fitur (60 sinyal dasar + 275 deskriptor temporal), 56 subjek,
2 sesi/subjek (before/after).

---

## 1. Struktur label yang menentukan segalanya

Label **per-sesi**, bukan per-orang:

| | anxiety_tinggi | anxiety_rendah |
|---|---|---|
| before | 41 | 15 |
| after | 25 | 31 |

- **18 dari 56 subjek labelnya BERUBAH** antar sesi (17 naik→turun, 1 turun→naik).
- 38 subjek labelnya sama di kedua sesi.

Konsekuensi: ada **dua pertanyaan berbeda** yang sering tertukar.

| pertanyaan | uji | n |
|---|---|---|
| **STATE**: apakah wajah orang yang sama berubah antara sesi cemas dan tenang? | berpasangan dalam-subjek | 18 subjek |
| **TRAIT**: bisakah kita menebak tingkat kecemasan seseorang yang belum pernah dilihat? | LOSO lintas-subjek | 56 subjek |

Pipeline sekarang memakai `--label-unit person` = hanya sesi `after` → pertanyaan
TRAIT, dan membuang separuh data (35.019 baris `before`).

---

## 2. Ceiling lintas-subjek: tidak ada fitur yang lolos derau seleksi

`scripts/audit_feature_representation.py`, sesi `after`, 56 subjek, 670 fitur
(mean+std):

| ukuran | nilai |
|---|---|
| max \|AUC−0,5\| observasi | 0,2432 |
| null 200 acak (label diacak) | 0,2379 ± 0,0251 |
| **p-value** | **0,385** |

AUC terbaik (0,73) persis sebesar yang didapat dari 670 fitur acak. **Tidak ada
satu pun fitur yang membawa sinyal trait lintas-subjek.**

---

## 3. Ablasi keluarga: sinyalnya ada di `rise`, bukan magnitude

Fitur dipisah menurut jenis sinyal dasar × ROI, diuji pada **gerbang
within-subject** (uji paling bersih: orang sama, wajah sama, label beda).
`scripts/audit_feature_family_casme2.py`:

| keluarga | n | BA (berubah, label) | BA (kontrol, sesi) |
|---|---|---|---|
| **`desc:rise`** | **55** | **0,8333** | **0,4605** |
| `arah` (mean_x/y, _mov, angle_*) | 120 | 0,6667 | 0,4605 |
| koherensi (angle_R dll) | 90 | 0,6389 | 0,5263 |
| SEMUA | 335 | 0,6389 | 0,4737 |
| magnitude (mean_m, max_m, abs, count) | 125 | 0,6111 | 0,5000 |
| `desc:peak` | 55 | 0,6111 | 0,5658 |
| `desc:auc` | 55 | 0,6111 | 0,5526 |
| `desc:ttp` | 55 | 0,5000 | – |
| `desc:fall` | 55 | 0,4444 | – |

`rise` = kemiringan naik dari awal event ke apex: `(peak - first) / idx_peak`.
Jadi yang informatif adalah **kecepatan onset micro-expression**, bukan besarnya
gerakan. Ini masuk akal: kecemasan tampak sebagai micro-expression yang lebih
mendadak, bukan gerakan yang lebih besar.

**Menambah fitur lain justru mengencerkan:**

| kombinasi | n | BA (berubah) | BA (kontrol) |
|---|---|---|---|
| rise | 55 | **0,8333** | 0,4605 |
| rise + arah | 175 | 0,7500 | 0,5526 |
| rise (hanya sinyal arah) | 35 | 0,6944 | 0,4737 |
| rise + sinyal dasar | 115 | 0,6944 | 0,4868 |
| SEMUA | 335 | 0,6389 | 0,4737 |
| sinyal dasar saja | 60 | 0,6111 | 0,5395 |

---

## 4. Uji kontrol: bukan artefak sesi

Penjelasan saingan yang harus dibunuh: `before` dan `after` direkam pada waktu
berbeda, jadi fitur bisa mendeteksi "sesi", bukan "kecemasan".

`scripts/audit_rise_control.py`:

| grup | target | BA `rise` |
|---|---|---|
| 18 subjek label BERUBAH | label sesi | **0,8333** |
| 38 subjek label SAMA (kontrol) | sesi (before/after) | **0,4605** |

Untuk 38 subjek yang kecemasannya **tidak** berubah menurut pakar, fitur `rise`
**tidak** bisa membedakan before dari after (0,46 = di bawah acak). Jadi `rise`
mendeteksi sesuatu yang **spesifik pada subjek yang kecemasannya berubah**, bukan
artefak waktu perekaman.

---

## 5. Validasi bersarang: pemilihan keluarga tidak overfit

Kekhawatiran: `rise` dipilih setelah melihat 10 keluarga → bisa jadi seleksi
post-hoc. Diuji dengan LOSO bersarang: untuk tiap subjek uji, keluarga dipilih
**hanya dari 17 subjek latih**, lalu subjek uji diprediksi.

| | nilai |
|---|---|
| balanced accuracy (18 subjek, di luar sampel) | **0,7778** |
| keluarga terpilih | `desc:rise` di **16/18** fold, `arah` di 2 |

Jadi pemilihannya stabil dan tidak bergantung pada subjek uji.

---

## 6. Diterapkan: representasi `rise`

`scripts/build_temporal_features.py` ditambah:

- `--descriptors rise` — batasi deskriptor yang dihitung.
- `--only-descriptors` — buang sinyal dasar per-frame (tetap 1 baris/frame
  supaya agregasi mean+std hilir tidak berubah).

Tabel: `experiments/features/apex/poc_abs_rise_v3fixed.pkl` — **55 fitur**
(5 ROI × 11 sinyal × 1 deskriptor), 62.955 baris.

### Gerbang within-subject (uji resmi repo, 500 permutasi)

| representasi | fitur | BA | p |
|---|---|---|---|
| SEMUA (per-frame + semua deskriptor) | 335 | 0,6389 | 0,1045 |
| **`rise` saja** | **55** | **0,8333** | **0,0020** |

**Naik dan sekarang SIGNIFIKAN.** Ini hasil pertama di proyek ini yang lolos
p < 0,05 pada uji kecemasan dengan protokol bersih.

---

## 7. Tapi TRAIT masih tidak bekerja

LOSO TabR, protokol sama (56 fold × 3 seed, `after`, agregasi subject):

| representasi | accuracy | bal. acc | MCC | AUC | baseline |
|---|---|---|---|---|---|
| SEMUA (335) | 0,4821 | 0,4716 | −0,0622 | 0,4606 | 0,5536 |
| **`rise` (55)** | **0,4762** | **0,4533** | **−0,1037** | **0,3978** | 0,5536 |

Perbandingan per keluarga pada tugas trait (logistic LOSO, sesi `after`):

| fitur | AUC | bal. acc |
|---|---|---|
| `desc:rise` | 0,5265 | 0,4942 |
| magnitude | 0,5277 | 0,4819 |
| SEMUA | 0,4142 | 0,4981 |
| koherensi | 0,4697 | 0,4819 |
| `arah` | 0,3252 | 0,4097 |

**Semua di sekitar acak.** Representasi `rise` memperbaiki STATE, bukan TRAIT.

### 7.1 Dikonfirmasi lewat pipeline resmi

Setelah `run_pipeline_v3.sh` diperbaiki (stage 4 & 6 memakai `rise` sebagai
default, lihat changes-log Iterasi 4.52), pipeline penuh dijalankan ulang:

| tahap | hasil |
|---|---|
| gerbang, tabel `rise` (55 fitur) | BA **0,8333**, p **0,0050** |
| gerbang, tabel per-frame (60 fitur) | BA 0,6111, p 0,1244 |
| LOSO TabR, `rise` | acc 0,4762, MCC −0,1037, AUC 0,3978 (baseline 0,5536) |
| baseline logistic pada `rise` | acc 0,5357, p 0,4179 |
| baseline GBDT pada `rise` | acc 0,4464, p 0,8557 |

Baseline model sederhana pun tidak signifikan. Jadi kegagalan TRAIT bukan
kekhususan TabR.

---

## 8. Kesimpulan

1. **Representasi yang benar untuk status kecemasan adalah dinamika onset
   (`rise`), bukan besaran gerakan.** Ini terukur, tervalidasi bersarang, dan
   bukan artefak sesi.
2. Efeknya **STATE**: pada orang yang kecemasannya berubah, wajahnya berubah, dan
   `rise` bisa membedakan sesi cemas dari sesi tenang dengan BA 0,833 (p 0,002).
3. **TRAIT lintas-subjek tetap tidak terdeteksi** dengan representasi apa pun
   yang diuji (semua AUC 0,32–0,53). Ini batas data/metode pada N=56, bukan
   sekadar masalah representasi.
4. Angka lama "fitur mengodekan identitas (0,79)" **tidak terverifikasi** dan
   tidak bisa direproduksi (eta-kuadrat 0,030–0,047; lihat
   `audit-spotting-casme2.md` §11). Jadi klaim itu tidak bisa dipakai untuk
   menjelaskan kegagalan trait.

### Implikasi untuk tesis

Framing yang didukung data: **"POC-ABS mendeteksi perubahan status kecemasan
(before vs after ujian) pada orang yang sama"** — bukan "mengklasifikasi tingkat
kecemasan orang". Framing kedua tetap di bawah baseline mayoritas.

## 9. TEMUAN BESAR: model OVERFIT sejak epoch 0 (diagnosis TRAIT)

`--epochs-trace` baru di `run_loso.py` menampilkan kurva per-epoch dari
`checkpoint.pt` (`training_log`) + train loss dari tfevents. Untuk fold 1, seed 0
pada tabel `rise`:

| epoch | 0 | 4 | 7 | 12 | 18 | 24 |
|---|---|---|---|---|---|---|
| train loss | 0.70 | 0.58 | 0.48 | 0.33 | 0.19 | **0.11** |
| val loss | 0.68 | 0.69 | 0.71 | 0.75 | 0.90 | **1.10** |
| val acc | 45% | 64% | **73%** | 45% | 45% | 45% |

**Train loss turun 0.70 → 0.11 sementara val loss NAIK 0.68 → 1.10.** Itu
overfitting sejak epoch pertama. Model menghafal 44 subjek latih dan tidak pernah
menambah kemampuan generalisasi. Val acc 73% di epoch 7 hanyalah derau di atas
model yang makin buruk.

Ini menjelaskan dua hal yang sebelumnya terlihat aneh:

1. **48,8% fold-seed "berhenti di epoch 0"** — bukan bug early stopping, memang
   tidak ada yang membaik. Val loss naik terus sejak awal.
2. **Akurasi val berupa tangga 9,1%** — hanya ~11 subjek val, jadi val acc
   bergerak dalam langkah 1/11 dan "epoch terbaik" menurut akurasi nyaris acak.
   Karena itu pemilihan epoch lewat akurasi val tidak bisa dipercaya di sini.

**Konsekuensi:** angka LOSO (~48%, di bawah baseline mayoritas 55%) adalah hasil
jujur dari model yang tidak bisa generalisasi, BUKAN bukti bahwa fitur tidak
membawa sinyal. Untuk memisahkan keduanya perlu perbaikan rezim training
(regularisasi/konfigurasi/epoch-selection lewat val loss), bukan sekadar
menambah fitur. Catatan: gerbang within-subject tetap signifikan pada fitur yang
sama, jadi sinyal STATE nyata; yang gagal adalah transfer antar-subjek. Angka
gerbang yang benar (setelah run ulang bersih) ada di §10: **0,7500, p 0,0100**.

## 10. Run ulang BERSIH dari nol (2026-10-11) — angka otoritatif

Pipeline penuh stage 1-7 dijalankan dari nol (`output/apex_run2`, 560 sample,
selesai 21:51). Ini menggantikan angka §7.1 yang sebagian berasal dari run yang
pernah terputus.

### 10.1 PENTING: run sebelumnya TIDAK lengkap

| | run lama (`apex_fixed`) | **run bersih (`apex_run2`)** |
|---|---|---|
| event total | 2.647 | **2.667** |
| baris `before` | 35.019 | **35.477** (+458) |
| baris `after` | 27.936 | **27.936** (sama) |
| sample | (terputus di tengah) | **560/560** |

Run lama pernah dimatikan di tengah lalu di-resume; logika resume melewati sample
yang direktori output-nya sudah ada, sehingga sample yang tertulis separuh
(di paruh `before`) ikut terlewat. **Semua selisih 458 baris ada di `before`**;
baris `after` identik. Karena LOSO hanya memakai sesi `after`, angka LOSO tidak
berubah. Tapi **gerbang within-subject memakai KEDUA sesi**, jadi angkanya berubah
dan yang lama terlalu tinggi:

| gerbang (55 fitur `rise`) | run lama | **run bersih** |
|---|---|---|
| balanced accuracy | 0,8333 | **0,7500** |
| p-value | 0,0050 | **0,0100** |

Yang benar adalah **0,7500 (p 0,0100)**. Tetap signifikan, tapi 0,8333 tidak boleh
dipakai lagi.

### 10.2 Hasil otoritatif

**Gerbang within-subject** (18 subjek × 2 sesi = 36 baris):

| fitur | n | balanced accuracy | p |
|---|---|---|---|
| `rise` (55) | 55 | **0,7500** | **0,0100** |
| per-frame (60) | 60 | 0,6389 | 0,0647 |
| vektor selisih (`after − before`) | – | 0,5000 | 0,6119 / 0,7612 |

**LOSO TabR** (56 fold × 3 seed, sesi `after`, 27.936 baris → 56 baris subjek):

| metrik | nilai | pembanding |
|---|---|---|
| train acc | 72,06% | – |
| val acc | 49,89% | – |
| **test acc** | **47,62%** | baseline mayoritas **55,36%** |
| balanced accuracy | 0,4533 | – |
| MCC | −0,1037 | 0 = acak |
| AUC (level subjek) | 0,3978 | 0,5 = acak |

**Baseline model sederhana** pada fitur `rise`:

| model | accuracy | p (permutasi 200×) |
|---|---|---|
| logistic | 53,57% | 0,4179 |
| GBDT | 44,64% | 0,8557 |

### 10.3 Overfitting bersifat UNIVERSAL

Dari trace epoch (`--epochs-trace`): **168 dari 168 fold-seed** memicu peringatan
OVERFIT (train loss turun sementara val loss naik). Contoh fold 1 seed 0:

| epoch | 0 | 7 | 12 | 18 | 24 |
|---|---|---|---|---|---|
| train loss | 0.70 | 0.48 | 0.33 | 0.19 | **0.11** |
| val loss | 0.68 | 0.71 | 0.75 | 0.90 | **1.10** |

Bukan kasus sebagian fold — semuanya. Jadi angka LOSO ~48% mengukur model yang
tidak bisa generalisasi, dan itu konsisten di seluruh 56 subjek. Sinyal STATE
tetap nyata (gerbang 0,75, p 0,01) pada fitur yang sama.

**Langkah berikutnya yang paling masuk akal:** perbaiki rezim training sebelum
menyimpulkan apa pun tentang fitur pada tugas TRAIT — turunkan `lr` (config kita
1e-3, notebook lama 3e-4), pilih epoch lewat **val loss** bukan val accuracy
(val accuracy hanya bergerak dalam langkah 9,1%), dan naikkan regularisasi.

---

## Lampiran — skrip

| skrip | isi |
|---|---|
| `audit_feature_representation.py` | ceiling AUC lintas-subjek + null permutasi |
| `audit_feature_family_casme2.py` | ablasi keluarga fitur pada gerbang |
| `audit_rise_control.py` | uji kontrol artefak sesi |
| `build_temporal_features.py` | + `--descriptors`, `--only-descriptors` |

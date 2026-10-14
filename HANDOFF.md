# HANDOFF — Validasi Tahap Spotting dengan CAS(ME)² (Fokus A)

> **STRUKTUR BERUBAH (2026-10-13).** Pipeline kini di `pipeline/`:
> titik masuk `./pipeline/run.sh`, stage di `pipeline/stages/stage_0..8_*.py`.
> Peta stage + perintah: **`pipeline/README.md`**.
> `scripts/` sudah tidak ada. Perintah lama di catatan bertanggal di bawah
> (`./scripts/run_pipeline_v3.sh`) sekarang `./pipeline/run.sh`.
> Kode lama ada di `legacy/`, eksperimen di `research/`.

Diperbarui: 2026-10-14.

## Keadaan 2026-10-14 — paper-backed spotting sweep selesai + Hanning fixed

User meminta "do all 4 and fix hanning window". Selesai:
- `features_extraction/poc.py`: Hanning window diperbaiki dari skalar/no-op
  menjadi window 2D (`np.outer`) dan diaplikasikan element-wise sebelum FFT.
- `scripts/eval_paper_spotting_configs.py`: evaluator CAS(ME)² berbasis cache
  `output/training/spotting_casme2_signals`, tanpa data anxiety.
- Empat jalur sudah dibangun/disapu: evaluator bersama, FD peak Li/Moilanen,
  OF-FD proxy, multi-window temporal, plus boundary beta/fixed window.

Output utama:
- `output/training/paper_spotting_configs/summary.md`
- `output/training/paper_spotting_configs/results.csv`
- `output/training/paper_spotting_configs/split_selection.csv`

Hasil CAS(ME)² penuh: `current_mean_m` masih menang loose F1 dan subject split.
Best per family:
- baseline `current_mean_m`: P 0,2753 / R 0,3799 / F1 0,3192 / IoU50 F1 0,1392 / F 1,0764.
- best OF-FD proxy `of_fd_proxy_mad2.5_topmean_sw35_b0.3`: F1 0,2301 / IoU50 F1 0,1503 / F 0,3729 / FP-video 3,1279.
- best FD `fd_k17_tau0.45_topmean_bfixed`: F1 0,1900.
- best multi-window `multiwin_L45_tau0.3_topmean_b0.3`: F1 0,1653.

Subject split A/B picked `current_mean_m` on both halves for loose F1, but that
is not the downstream selection metric. Precision-first OF-FD proxy has cleaner
configs (e.g. P 0,3000 / FP-video 1,0581) and is now wired for downstream A/B as
`SPOT_ALGO=of_fd_proxy`. True OF-FD paper reproduction still requires dense
optical flow over 13/14 ROIs plus face/nose alignment; current result is
explicitly a proxy over POC-ABS ROI curves.

Command ready for Khalid to run full fold-first downstream A/B:

```bash
V3_PRESPLIT=1 \
V3_SPOT_ALGO=of_fd_proxy \
V3_SPOT_OF_FD_MAD=3.5 \
V3_SPOT_OF_FD_TOP=mean \
V3_SPOT_OF_FD_SMOOTH=35 \
V3_SPOT_OF_FD_BOUNDARY_BETA=0.3 \
V3_EXTRA_CONFIGS="experiments/configs/tabr_loso_roi25_reg.toml" \
  ./scripts/run_pipeline_v3.sh --fresh
```

Verification done:
- `.venv/bin/python -m py_compile scripts/process_spotting_pipeline.py scripts/eval_paper_spotting_configs.py features_extraction/poc.py`
- `bash -n scripts/run_pipeline_v3.sh`
- `V3_SPOT_ALGO=of_fd_proxy ./scripts/run_pipeline_v3.sh --dry-run --stage 1`
- Hanning sanity check: `(7,7)` window, center 1, corner 0, finite POC output.
- Limit evaluator run (`--limit 3`).
- Full cache sweep over 86 CAS(ME)² videos, 145 configs.

Do **not** run the full anxiety pipeline unless Khalid explicitly asks; user
contract forbids smoke/e2e/full runs unless requested.

## Keadaan 2026-10-13 (malam, lanjutan) — MODE FOLD-FIRST selesai dibangun, menunggu run

Atas permintaan user ("split sebelum spotting supaya tidak ada orang yang
terlihat di tengah"), pipeline v3 kini punya mode fold-first `V3_PRESPLIT=1`:
stage 0 membagi 56 orang → 44 train pool + 12 holdout (strata label-pair,
seed 42, `output/presplit/`), stage 1–7 berjalan HANYA pada 44 orang
(`SPOT_INCLUDE_PERSONS`), stage 8 mengevaluasi 12 orang holdout yang pertama
kali dibaca saat itu juga → satu fold final (model + satu angka jujur) di
`output/training/<dataset>_holdout/`.

Jujur: protokol lama sudah bebas bocor secara matematis (split
subjek-disjoint + fit di train saja); mode ini jaminan struktural, bukan
perbaikan bocor — ekspektasi gerak metrik ≈ 0.

File baru: `scripts/split_persons_presplit.py`,
`scripts/combine_feature_tables.py`. Diubah: `process_spotting_pipeline.py`
(env `SPOT_INCLUDE_PERSONS`, default no-op), `run_loso.py`
(`--test-persons-file`, mode LOSO lama tidak berubah), `run_pipeline_v3.sh`
(stage 0 + 8 di mode presplit; default 7 stage bit-identik).
Plan + verifikasi: `report/plans/2026-10-13-fold-first-presplit-holdout/`.

Perintah user (SATU run penuh — multi-config `V3_EXTRA_CONFIGS`: stage 6/7/8
mengulang per config, fitur sekali; dataset config ke-2 = `<ds>_cfg_roi25_reg`):
```bash
V3_PRESPLIT=1 V3_SPOT_SIGNAL=combo \
V3_EXTRA_CONFIGS="experiments/configs/tabr_loso_roi25_reg.toml" \
  ./scripts/run_pipeline_v3.sh --fresh
```
Fokus spotting: run ini memakai sinyal `combo` (z(mean_m)+z(Hpoc)) — kandidat
terkuat hasil deep dive (CAS(ME)² F1 0,3343 vs 0,3192 baseline, menang di
kedua fold validasi). Target user: ≥60% sebelum Maret; spotting adalah tuas
utama yang tersisa (bottleneck terukur = SNR gerakan latar, lihat
`report/findings/magnitude-deepdive.md`).
Bukti fold-first di log stage 1: `INCLUDE_PERSONS: 440 video diproses, 120
dilewati` — TERKONFIRMASI di run 21:54.

**HASIL RUN (2026-10-13 21:54, combo + 2 config):** NEGATIF untuk combo.
LOSO-44: compact 0,3864 / roi25_reg 0,4242 (mean_m dulu 45,83% pooled-56).
Holdout-12: compact 0,4167, roi25_reg 0,5278 (BA 0,5857, MCC +0,31, tapi CI
0,32–0,81 memuat baseline 0,5833). Gate within-subject: BA 0,5357, p=0,4577
— tidak ada sinyal. Kesimpulan: sinyal combo tidak berpindah dari CAS(ME)²
(lab, mikro terpose) ke data anxiety (lapangan 30 fps, gerakan latar berat).
`mean_m` tetap default. Dua resep spotting (mean_m, combo) sama-sama mentok
di fold-first; bottleneck = SNR gerakan latar. Sisa tuas ber-bukti:
`V3_SPOT_CUTOFF=0.5` (batas rapat), atau tambah N dari `datatest` (izin
dosen). Detail: PROGRESS.md entri "2026-10-13 (malam, lanjutan)".

**LANJUTAN 2 — lever spotting anti-noise sudah di-A/B, hasil NEGATIF.** Dua
kandidat pengganti combo yang GATED (default OFF = bit-identik), di deep dive
`report/findings/spotting-feature-deepdive.md`:
- `V3_SPOT_MOTION_COMP=1` — kompensasi gerakan global/rigid (median antar-blok
  dikurangi; noise kepala serentak hilang, ekspresi lokal selamat).
- `V3_SPOT_SIGNAL=mdmd` (jendela `V3_SPOT_MDMD_K=5`) — beda sinyal vs tetangga
  ±k (Wang 2017); tren lambat hilang, puncak tajam selamat.
Keduanya terverifikasi pada data sintetik + wiring pipeline (stage 1 & 8), lalu
dijalankan penuh fold-first:
`V3_PRESPLIT=1 V3_SPOT_MOTION_COMP=1 V3_SPOT_SIGNAL=mdmd
V3_EXTRA_CONFIGS="experiments/configs/tabr_loso_roi25_reg.toml"
./scripts/run_pipeline_v3.sh --fresh`.

Log utama: `logs/pipeline_v3_20261014_000216.log`. Stage 1 benar fold-first:
`INCLUDE_PERSONS: 440 video diproses, 120 dilewati`; stage 8 holdout:
`120 video diproses, 440 dilewati`. Stage 1 menghasilkan 2194 baris metadata.

Hasil terbaik run motion-comp+MDMD tetap setara acak / di bawah baseline:
- LOSO-44 terbaik (`roi25_reg_cfg_roi25_reg`): accuracy 0,4773 ± 0,0682,
  BA 0,4958, MCC −0,0087, AUC 0,5151.
- Holdout-12 terbaik (`roi25_reg_cfg_roi25_reg_holdout`): accuracy 0,4444 ±
  0,0962, BA 0,5048, MCC −0,0014, AUC 0,4762.
- Gate temporal within-subject: BA 0,5357, p=0,4428; fitur signifikan grup
  berubah 0/55, kontrol 4/55.

Keputusan magnitude/spotting per 2026-10-14: **jangan ganti default ke combo
atau mdmd**. `mean_m` tetap default karena paling stabil tervalidasi pada
CAS(ME)² dan tidak kalah oleh kandidat anxiety-side. `V3_SPOT_CUTOFF=0.5` masih
boleh jadi A/B sekunder untuk batas event lebih rapat, tetapi bukan harapan
utama. `datatest` dikonfirmasi 26 orang (bukan 49), 654 video, ada skor kontinu
— join nama+timestamp diperlukan dan butuh izin dosen. Detail: PROGRESS.md
"2026-10-14 dini hari".

## Keadaan 2026-10-13 (malam, sesudah fresh run v3 user) — gate run2 gugur

User menjalankan `run_pipeline_v3.sh --fresh` (mean_m default). Hasil:
TabR accuracy 45,83% (CI memuat baseline 57,14%), AUC 0,5664; GBDT 0,6071
(p=0,194, tidak signifikan); **gate within-subject run2 (BA 0,75, p=0,01)
TIDAK direplikasi** — v3 memberi 0,6389 p=0,070 (full) / 0,5556 p=0,358
(rise), dan pola Wilcoxon berbalik (kontrol 8/55 signifikan, berubah 0/60).
Kesimpulan: hasil signifikan run2 adalah artefak pipeline lama, bukan sinyal
kecemasan. Belum ada hasil yang terbukti di protokol LOSO.

Langkah berikutnya yang tersisa (belum diuji di sisi anxiety):
1. `V3_SPOT_SIGNAL=combo ./scripts/run_pipeline_v3.sh --fresh` — sinyal
   spotting tervalidasi di CAS(ME)² (F1 0,3343 vs 0,3192).
2. `V3_SPOT_CUTOFF=0.5` — batas event lebih rapat (F1 ketat 0,1637, durasi 41).
Detail: PROGRESS.md entri "2026-10-13 (malam)".

## Keadaan 2026-10-13 (malam) — sinyal Hpoc TERVALIDASI sebagai kandidat baru

Dari teks lengkap paper Rosiani et al. (2020): fitur M per blok di sana =
**nilai puncak POC (Hpoc)**, bukan |V| — kode kita membuangnya. Audit 86 video
CAS(ME)² (`scripts/audit_hpoc_casme2.py`, cache `casme2_hpoc_signals`):
**combo global z(mean_m)+z(hpoc) F1 0,3343 vs baseline 0,3192**, terpilih di
kedua fold validasi subjek (test 0,3262/0,3198). Resep persis paper (acuan
berurutan, eksklusi blok diam, block 5) gagal di data 30 fps.

Kode: `SPOT_SIGNAL=mean_m|hpoc|combo` di `process_spotting_pipeline.py`
(default TIDAK berubah, bit-identik), diteruskan `V3_SPOT_SIGNAL` di
`run_pipeline_v3.sh`. Uji A/B sisi anxiety:
`V3_SPOT_SIGNAL=combo ./scripts/run_pipeline_v3.sh --fresh`
Detail: `report/findings/magnitude-deepdive.md` §7. Koreksi FINAL.pdf
ditambah §7–10 di `report/findings/koreksi-final-pdf.md` (acuan frame-0,
smoother 3%, hitung blok 79/316 fitur, definisi M).

## Keadaan 2026-10-13 — deep dive magnitude SELESAI

Pertanyaan "definisi magnitude spotting mana yang terbaik untuk POC-ABS" sudah
terjawab terukur: **mean per ROI → mean antar ROI (yang sudah dipakai) tetap
terbaik** — peringkat puncak 0,146 vs 0,164-0,271 (10 video) dan F1 0,3192 vs
≤0,3184 (86 video, validasi split subjek tanpa pemenang lain yang stabil).
Detail: `report/findings/magnitude-deepdive.md` + `audit-spotting-casme2.md` §10.

Default pipeline tidak berubah angka. Yang baru:
- `SPOT_CUTOFF` env di `process_spotting_pipeline.py` (default 0,3).
- `V3_SPOT_CUTOFF` diteruskan `run_pipeline_v3.sh`. Uji cutoff 0,5 (batas
  onset/offset lebih rapat, F1 ketat lebih tinggi):
  `V3_SPOT_CUTOFF=0.5 ./scripts/run_pipeline_v3.sh --fresh`
- Koreksi FINAL.pdf siap tempel: `report/findings/koreksi-final-pdf.md`
  (block 9×9, 5 ROI, parameter deteksi, protokol LOSO, angka jujur).

Leak check: split LOSO per subjek terjadi SEBELUM preprocessing di kedua runner
(imputer/scaler/balancing fit di train saja) — `run_loso.py:654-662`,
`run_loso_lit_tabr.py:141-145`.

---

## Tujuan sesi ini

User memilih **fokus A** (dari tiga opsi yang ditawarkan): pertahankan kecemasan
sebagai target, dan pakai **CAS(ME)²** hanya untuk **memvalidasi tahap spotting**
— memberi `ApexPhase`/`POC-ABS` angka akurasi ber-ground-truth pertama. Sedikit
dari **fokus B**: metrik dipisah **macro vs micro**, karena micro-expression
adalah kasus tersulit dan paling relevan.

Alasan ini perlu: label kecemasan di dataset utama terbukti tercampur fase
(before 41/56 `anxiety_tinggi` vs after 25/56) dan fitur lebih kuat mengodekan
identitas daripada kondisi (same-subject NN retrieval 18,8% vs acak 0,9%).
Tahap spotting belum pernah diuji terhadap ground truth apa pun, jadi klaim
"bisa menemukan micro-expression" belum punya dasar.

## Keadaan sekarang — SIAP DIJALANKAN

CAS(ME)² sudah **diekspor** ke `/home/finny/datasets/casme2/rawvideo/` (97 video,
6,95 GB). Drive mentah (`/dev/nvme0n1p7`, "New Volume") **sering lepas sendiri** —
mount dulu kalau perlu: `udisksctl mount -b /dev/nvme0n1p7`.

Perintah benchmark (spotting 86 video, ±1 jam, 4 worker):

```bash
cd /home/finny/projects/Skripsi
.venv/bin/python scripts/eval_spotting_casme2.py
```

Uji cepat: `--limit 3`. Toleransi lain: `--tolerances 0 5 10`.
RAM sesak: `--workers 2`.
Keluaran: `output/training/spotting_casme2/{summary.md,matched.csv,false_positives.csv}`.

## Cara menguji parameter (FIX 2026-10-09)

Masalah 4.42: detektor mengeluarkan ~19 deteksi/video sedangkan GT ~2, dengan
plafon 25 = 5 ROI x `top_k_apex` 5. Akar masalahnya parameter pemilihan event,
tapi parameter itu dipakai bersama pipeline utama.

**Default pipeline TIDAK diubah** (mengubahnya akan membatalkan semua klip +
fitur + hasil training). Yang ditambahkan: kemampuan menguji parameter.

Sinyal POC-ABS dihitung sekali lalu di-cache (`spotting_casme2_signals/`), jadi
grid parameter hanya mengulang tahap deteksi: 2,4 detik vs ~3 menit.

```bash
cd /home/finny/projects/Skripsi
.venv/bin/python scripts/eval_spotting_casme2.py \
  --top-k 1 2 3 4 5 --prom-rel 0.04 --thresh meanstd mad
```

- `--top-k`, `--prom-rel`, `--thresh` menerima beberapa nilai = grid.
- `--signal-cache DIR` (default di atas), `--no-cache` untuk mematikan.
- Ringkasan: tabel grid + detail kombinasi terbaik (F1) + `matched.csv` /
  `false_positives.csv` untuk kombinasi itu.

**Temuan: `prom_rel` tidak binding.** 0,04 -> 0,20 mengurangi puncak mentah
(mulut 32 -> 27) tapi top-5 teratas tetap sama, jadi hasil akhir identik. Yang
mengikat hanya `top_k` dan mode ambang (`meanstd` vs `mad`).

Indikasi awal dari 2 video (top_k=1 F1 0,4615) **menyesatkan** — tidak bertahan
di 86 video (0,2006). Lihat bagian hasil di bawah.

## AUDIT + TELAAH MENDALAM (Iterasi 4.49, 2026-10-09)

Setelah verdict 4.48 ("tidak bekerja"), dilakukan **audit apa yang kita ubah sejak
kode asli** + telaah mendalam sinyal. Hasil lengkap:
`report/findings/audit-spotting-casme2.md`.

**Temuan kunci:** logika spotting ASLI tidak ada di file .py mana pun — ia hidup di
notebook `preprocess-anxiety/process_all_datasets.ipynb` (yang .py hanya stub
`NotImplementedError`). Jadi `scripts/process_spotting_pipeline.py` adalah
**reimplementasi**, dan audit menemukan 4 divergensi perilaku:

| # | aspek | asli (notebook) | sekarang | dampak |
|---|---|---|---|---|
| 1 | agregasi antar-ROI | **global** (1 sinyal) | **per-ROI** | **regresi** |
| 2 | acuan POC | frame berurutan | frame-0 | **perlu** (lihat bawah) |
| 3 | smoothing | 5% panjang (clamp 31) / tetap 28 | tetap 7 | **regresi** |
| 4 | peringkat puncak | **prominence** (generasi 1) | **nilai** | **regresi** |
| 5 | block_size | 7 | 9 | tidak berpengaruh |
| 6 | ROI | mata + alis terpisah | **sama** | tidak berubah |

### FIX yang diterapkan (F1 0,1637 → 0,3192)

| resep | P | R | F1 | det/video |
|---|---|---|---|---|
| sebelum (per-ROI / 7 / nilai) | 0,0971 | 0,5195 | 0,1637 | 19,2 |
| + agregasi global | 0,1837 | 0,2565 | 0,2141 | 5,0 |
| **+ 3% adaptif + prominence (sekarang)** | **0,2753** | **0,3799** | **0,3192** | 4,9 |
| `top_k=4` (terbaik) | 0,3079 | 0,3409 | 0,3236 | 4,0 |

Tervalidasi split subjek 2-fold: konfigurasi dipilih di satu paruh subjek, diukur
di paruh lain → F1 test **0,315 / 0,320** (pembanding pipeline lama 0,206–0,221).
Kedua fold memilih konfigurasi yang sama.

Perubahan kode:
- `SPOT_SIGNAL_MODE` default → `global_mean`
- `apex/apex_smoother.py`: window tetap 7 → **3% adaptif** (min 5)
- `apex/apex_phase.py`: `find_top_k_apex(..., ranking=)` baru (`'value'` default)
- `scripts/process_spotting_pipeline.py`: `SPOT_RANKING` (default `prominence`)
- `scripts/eval_spotting_casme2.py`: `detect_from_signals` ikut `SPOT_SIGNAL_MODE`

Verifikasi end-to-end: 3 video CAS(ME)² → 5 event/video, `region='global'`.

**Catatan:** klip + tabel fitur lama jadi tidak berlaku, perlu regenerasi.

### Hasil regenerasi (Iterasi 4.50, 2026-10-10)

Pipeline dijalankan ulang penuh (stage 1-7) ke tag baru; keluaran lama tidak
disentuh. Spotting: 7.094 → **2.647** event (12,7 → **4,8**/sample), semua
`region='global'`. Fitur: 97.808 → 62.955 baris frame.

| tahap | sebelum | sesudah | verdict |
|---|---|---|---|
| spotting F1 (CAS(ME)²) | 0,1637 | **0,3192** | diperbaiki, tervalidasi |
| gate within-subject (BA, temporal) | 0,500 (p 0,597) | **0,639 (p 0,105)** | naik, belum p<0,05 |
| gate per-frame (BA) | 0,583 (p 0,164) | **0,611 (p 0,124)** | naik, belum p<0,05 |
| LOSO accuracy | 0,4881 | **0,4821** | **tidak berubah** (baseline 0,5536) |
| LOSO AUC | 0,3974 | **0,4606** | naik, masih < 0,5 |
| baseline logistic | — | 0,5714 (p 0,2189) | tidak signifikan |

**Kesimpulan:** akar masalah spotting sudah ditemukan dan diperbaiki, dan itu
memang menaikkan sinyal (F1, gate, AUC). **Tetapi belum cukup**: pada protokol
LOSO lintas-subjek, accuracy masih di bawah baseline mayoritas dan AUC masih di
bawah 0,5. Jadi kegagalan klasifikasi kecemasan **bukan (kebanyakan) akibat
spotting yang rusak** — memperbaikinya tidak menyelamatkan klasifikasi.

## REPRESENTASI FITUR (Iterasi 4.51, 2026-10-10)

Temuan lengkap: `report/findings/audit-feature-representation.md`.

### Struktur label: PER-SESI, bukan per-orang

18 dari 56 subjek labelnya berubah antar sesi (17 naik→turun). Jadi ada dua
pertanyaan yang sering tertukar:

| pertanyaan | uji | n |
|---|---|---|
| **STATE** — wajah orang yang sama berubah antara sesi cemas vs tenang? | berpasangan dalam-subjek | 18 |
| **TRAIT** — tebak tingkat kecemasan orang yang belum dilihat? | LOSO lintas-subjek | 56 |

### Hasil

1. **TRAIT ceiling:** tidak ada fitur yang lolos derau seleksi
   (max |AUC−0,5| 0,2432 vs null 0,2379 ± 0,0251, **p = 0,385**).
2. **Ablasi keluarga:** sinyalnya ada di `rise` (kemiringan onset→apex), bukan
   magnitude. `rise` (55 fitur) BA **0,833**; SEMUA (335) BA 0,639; magnitude 0,611.
   Menambah fitur lain mengencerkan (rise+arah 0,750).
3. **Bukan artefak sesi:** pada 38 subjek yang labelnya tidak berubah, `rise`
   tidak bisa membedakan before/after (BA 0,461).
4. **Validasi bersarang:** keluarga dipilih hanya dari subjek latih → BA 0,778;
   `rise` terpilih 16/18 fold.
5. **Diterapkan:** `--descriptors rise --only-descriptors` di
   `build_temporal_features.py` → `poc_abs_rise_v3fixed.pkl` (55 fitur).
   Gerbang: BA **0,8333, p 0,0020** (sebelumnya 0,6389, p 0,1045).
   **SUPERSEDED — angka ini dari run yang `before`-nya tidak lengkap; yang benar
   0,7500 (p 0,0100), lihat "RUN ULANG BERSIH" di bawah.**
6. **TRAIT tetap tidak bekerja:** LOSO `rise` acc 0,4762, AUC 0,3978
   (SEMUA: 0,4821 / 0,4606; baseline 0,5536).

### Implikasi framing

Yang didukung data: **"POC-ABS mendeteksi perubahan status kecemasan (before vs
after ujian) pada orang yang sama"** — bukan "mengklasifikasi tingkat kecemasan
orang". Framing kedua tetap di bawah baseline mayoritas.

### Pipeline sudah memakai `rise` sebagai default (Iterasi 4.52)

`run_pipeline_v3.sh`: `V3_DESCRIPTORS` (default `rise`) + `V3_ONLY_DESCRIPTORS`
(default 1) → stage 4 memakai `--descriptors rise --only-descriptors`, dan stage 6
meneruskan `--drop-features` yang sesuai (default `_max_m$` MEMATALAKAN di mode
only-descriptors karena kolom itu sudah dibuang). Setel
`V3_DESCRIPTORS="peak ttp rise fall auc" V3_ONLY_DESCRIPTORS=0` untuk perilaku lama.

Dikonfirmasi pipeline penuh: gerbang `rise` signifikan; LOSO `rise`
acc 0,4762 / AUC 0,3978 (baseline mayoritas 0,5536); baseline logistic 0,5357
(p 0,4179) dan GBDT 0,4464 (p 0,8557) — dua-duanya tidak signifikan.

### RUN ULANG BERSIH — angka otoritatif (Iterasi 4.55)

Pipeline penuh dijalankan dari nol (`output/apex_run2`, 560/560 sample). Ini
menggantikan angka di atas.

**Temuan: run sebelumnya TIDAK lengkap.** Run lama pernah terputus lalu di-resume;
logika resume melewati sample yang direktori output-nya sudah ada, jadi sample
yang tertulis separuh (di paruh `before`) ikut terlewat.

| | run lama | **run bersih** |
|---|---|---|
| event | 2.647 | **2.667** |
| baris `before` | 35.019 | **35.477** (+458) |
| baris `after` | 27.936 | **27.936** (sama) |

Karena LOSO hanya memakai `after`, LOSO tidak berubah. Gerbang memakai KEDUA sesi,
jadi berubah dan yang lama terlalu tinggi:

| gerbang `rise` (55 fitur) | run lama | **run bersih** |
|---|---|---|
| balanced accuracy | 0,8333 | **0,7500** |
| p | 0,0050 | **0,0100** |

**Pakai 0,7500 (p 0,0100).** Rincian: `report/findings/audit-feature-representation.md` §10.

Hasil otoritatif:
- gerbang `rise`: **BA 0,7500, p 0,0100** (signifikan); per-frame: 0,6389, p 0,0647
- LOSO: train 72,06% / val 49,89% / **test 47,62%** (baseline mayoritas 55,36%),
  MCC −0,1037, AUC 0,3978
- baseline: logistic 53,57% (p 0,4179), GBDT 44,64% (p 0,8557)
- **overfit UNIVERSAL: 168/168 fold-seed** (train loss turun, val loss naik)

### DIAGNOSIS: model overfit sejak epoch 0 (Iterasi 4.54)

`--epochs-trace` di `run_loso.py` (dan diteruskan stage 6) mencetak kurva
per-epoch per seed: val_acc%, train_loss, val_loss, best epoch, + peringatan
overfit otomatis. Sumbernya `checkpoint.pt` → `training_log` + tfevents
`loss_train/` (cara yang sama dengan `notebooks/tabr_feature_pruning_tuning.ipynb`).

Fold 1 seed 0, tabel `rise`:

| epoch | 0 | 4 | 7 | 12 | 18 | 24 |
|---|---|---|---|---|---|---|
| train loss | 0.70 | 0.58 | 0.48 | 0.33 | 0.19 | **0.11** |
| val loss | 0.68 | 0.69 | 0.71 | 0.75 | 0.90 | **1.10** |
| val acc | 45% | 64% | **73%** | 45% | 45% | 45% |

Train loss turun, val loss NAIK terus → **overfit sejak epoch 0**. Ini menjelaskan
48,8% fold-seed "berhenti di epoch 0" (bukan bug early stopping) dan val acc yang
berupa tangga 9,1% (hanya ~11 subjek val, jadi pemilihan epoch lewat akurasi val
nyaris acak).

**Implikasi:** angka LOSO ~48% adalah hasil jujur model yang tidak bisa
generalisasi, BUKAN bukti fitur tidak bersinyal. Gerbang within-subject tetap
BA 0,833 pada fitur yang sama → sinyal STATE nyata, transfer antar-subjek gagal.
Langkah berikutnya: perbaiki rezim training (regularisasi / konfigurasi /
pemilihan epoch lewat val LOSS, bukan akurasi).

### Yang terlewat selama ini: notebook punya TIGA generasi

- **Gen 1** `micro_expression_spotting.ipynb`: savgol tetap 28, `find_peaks(prominence=0)`
  TANPA height, urut **prominence**, top 3.
- **Gen 2** `..._v2.ipynb` / `..._v2 Casme.ipynb`: `ApexSmoother` 5%/clamp 31, urut nilai.
- **Gen 3** `process_all_datasets.ipynb` = gen 2 + agregasi global (dipakai pipeline).

Pipeline memakai gen 2/3 tapi membuang dua hal dari gen 1: **window panjang** dan
**peringkat prominence**. Keduanya dikembalikan.

### Kenapa acuan frame-0 TIDAK dikembalikan

Uji sintetis (gerakan diketahui) + 31 video nyata:

| acuan | P@1 | P@5 |
|---|---|---|
| abs (frame-0, sekarang) | **0,048** | **0,144** |
| seq (berurutan, asli) | 0,000 | 0,048 |

POC mencari pergeseran **bilangan bulat**; pada 30 fps gerakan antar-frame
micro-expression **sub-piksel** → tak terlihat. Hanya pergeseran kumulatif dari
acuan tetap yang terlihat. Aslinya dipakai di video 60 fps (gerakan/frame >= 1 px).
**Mengembalikan ke berurutan akan memperburuk.**

### Mengapa sinyalnya tetap lemah

Pada sinyal global, 308 GT: persentil sinyal di frame apex **0,776** (acak 0,50),
tetapi puncak-apex berperingkat **0,226** (~124 dari ~549 puncak) → top-5 tak
menjangkau. `height = mean+std` menggugurkan 49% puncak ekspresi. F1 acak 0,106
vs kita 0,214 (2x acak). Transformasi sinyal (high-pass/z-score/rasio/turunan)
**semua lebih buruk** → masalahnya bukan drift. Grid detektor plateau F1 ~0,22-0,23.

## KESIMPULAN LAMA (Iterasi 4.48): spotting BELUM bekerja di CAS(ME)^2

*Sebagian disuperseded oleh audit 4.49 di atas — akarnya ternyata agregasi
per-ROI, bukan sekadar "tidak bekerja".*

Sudah diuji **semua** tuas yang masuk akal pada SELURUH 86 video, dengan
protokol yang sudah dibersihkan. Verdict: **tidak bekerja**, dan sebabnya
sekarang spesifik.

### Angka jujur (86 video, GroupKFold per video, ambang dipilih di data latih)

| metode | AUC | F1 |
|---|---|---|
| pipeline `top_k=5` (default) | — | 0,1637 |
| pipeline `top_k=1` | — | 0,2006 |
| puncak + fitur kaya | 0,6686 | 0,2156 |
| jendela w=64 | 0,6492 | 0,3715 |
| jendela w=96 | 0,6442 | 0,4281 |
| jendela w=128 | 0,6296 | 0,4068 |

### Tapi F1 0,43 itu ARTEFAK

window=96, diperiksa:

| ukuran | nilai |
|---|---|
| durasi event deteksi (median) | **209 frame** |
| durasi GT (median) | **29 frame** |
| F1 kalau tumpang tindih diperketat ke IoU ≥ 0,5 | **0,0061** |
| jarak pusat event ke apex GT (median) | 172 frame |
| lokalisasi ≤10 / ≤20 / ≤40 / ≤80 frame | 5,5% / 12,0% / 22,7% / 36,0% |

Event dibuat 7× terlalu panjang sehingga hampir selalu "beririsan" dengan GT.
Begitu tumpang tindih diukur wajar, hasilnya nol.

### Yang sudah terbukti BUKAN penyebab

Sinyal (memuncak di ekspresi, persentil 0,988), `top_k`, ambang, prominence,
perataan, agregasi mean/max/count, acuan abs/seq, perbesaran ROI, drift,
artefak awal, blink, fitur kaya (arah+koherensi), ukuran jendela.

### Tiga jebakan metodologi yang ditemukan dan ditutup

1. **Subset kecil menyesatkan.** window=16: AUC 0,71 pada 20 video vs 0,60 pada
   86. Semua angka 4.47 (F1 0,27 pada 15 video) terlalu optimistis.
2. **Ambang tidak boleh dipilih dari data uji.** Sekarang dipilih di sub-split
   data latih per fold (`--threshold-mode inner`, default). posthoc 0,4453 vs
   inner 0,4281.
3. **Pencocokan "beririsan" terlalu longgar** bila durasi event tidak dikontrol.
   Sekarang ada pemeriksaan IoU ≥ 0,5 + statistik durasi + lokalisasi.

## Jebakan OOM (sudah diperbaiki, 2026-10-09)

Run penuh pertama **dibunuh OOM killer** (bukan crash Python, bukan reboot):
`load_video_frames` memuat semua frame jadi list, lalu `build_roi_signals`
menyalinnya lagi ke grayscale. Video CAS(ME)² 4370 frame = ~5,3 GB per worker;
4 worker = ~21 GB vs RAM 15 GiB. Sekarang frame **di-strim**:
puncak 0,27 GB per video (~20x lebih kecil). Sinyal identik bit-per-bit.

Kalau RAM tetap sesak (Chrome/Discord jalan): `--workers 2`.

## Yang berubah

| berkas | perubahan |
|---|---|
| `scripts/eval_spotting_casme2.py` | **BARU**. Benchmark spotting vs GT CAS(ME)² |
| `scripts/process_spotting_pipeline.py` | eksekusi level-modul dipindah ke `main()`; `build_roi_signals` streaming (`iter_video_frames`); **default `SPOT_SIGNAL_MODE` → `global_mean`** (audit 4.49) |
| `report/documentation/changes-log.md` | Iterasi 4.39, 4.40 |
| `report/findings/audit-spotting-casme2.md` | **BARU**. Audit divergensi vs asli + telaah mendalam |
| `scripts/audit_*.py` | **BARU**. smoothing / agregasi / acuan / transform / grid detektor / block_size |

### Kenapa `process_spotting_pipeline.py` diubah

Dua alasan:

1. Dulu seluruh spotting berjalan di level modul, jadi `import` file itu langsung
   menulis `metadata.xlsx`/klip (pernah menghapus metadata). Benchmark butuh
   fungsi intinya (`build_roi_signals`, `detect_events_per_roi`, `init_worker`),
   jadi blok eksekusi dipindah ke `main()` + `if __name__ == '__main__'`.
2. `build_roi_signals` memuat seluruh video ke RAM (dan menyalinnya lagi ke
   grayscale). Video CAS(ME)² 4370 frame = ~5,3 GB/worker → OOM. Sekarang
   streaming lewat `iter_video_frames`. Sinyal identik bit-per-bit.

## Jebakan

- **Jangan re-tune spotting diam-diam.** Tujuan benchmark adalah mengukur apa
  adanya. Kalau parameter diubah, jalankan dua kali (sebelum/sesudah) dan
  laporkan keduanya.
- **Jangan pakai split bocor untuk mengejar 74%.** Angka lama itu inflasi
  kebocoran subjek.
- `CASME2_GT` / `CASME2_VIDEOS` bisa di-override lewat env kalau path berubah.
- 1 frame GT dianggap 1-based vs 0-based OpenCV → selisih 1 frame, diabaikan.

## Pertanyaan terbuka

1. Apakah recall micro tetap tinggi saat 86 video dijalankan penuh? Micro hanya
   57 dari 356 ekspresi.
2. Precision rendah karena threshold `mean+std` per ROI. Apakah menaikkan
   `SPOT_PROM_REL` menaikkan F1, atau hanya memindahkan recall ke precision?
3. Setelah spotting tervalidasi: apakah sinyal per-frame yang sama bisa dipakai
   untuk klasifikasi kecemasan, atau memang dua masalah berbeda?

## Konteks yang masih berlaku dari sesi sebelumnya

- POC-ABS tetap (penelitian dosen, ada di judul). AU/geometri sudah dibuang.
- Pipeline utama: `./scripts/run_pipeline_v3.sh` (device CPU default).
- Pipeline membuang 53.161 dari 97.808 baris (semua sesi `before`) secara sadar.
- Hasil LOSO terakhir: acc 0,4881, MCC −0,0521, AUC 0,3974, baseline 0,5536 —
  di bawah acak. Bukan target perbaikan sampai spotting/N tervalidasi.
- `datatest` (49 subjek, **0 overlap** dengan 56 subjek utama, ada `score`
  kontinu) tersedia di drive untuk menaikkan N bila diizinkan dosen.

## Plan baru 2026-10-14 — MyGo desktop pipeline dashboard

User ingin pipeline bisa dijalankan dari desktop native app, bukan command/script.
Plan ada di `report/plans/2026-10-14-pipeline-desktop-dashboard/`.

Inti keputusan: jangan bikin UI sebagai terminal skin. Buat kontrak pipeline
(machine-readable registry), Go run controller, `.pipeline/runs/<run-id>/` run
store, lalu MyGo native UI untuk pipeline switcher, setup, stage timeline,
diagnostics, dan report dashboard.

Urutan issue:
1. registry/kontrak pipeline;
2. run controller + structured run store;
3. MyGo app shell;
4. diagnostics/log inspector;
5. report parser/dashboard;
6. presets eksperimen;
7. compare/export;
8. stop/resume/rerun;
9. packaging/launch.

Catatan: app sebaiknya dibangun setelah atau bersamaan dengan refactor stage
`report/plans/2026-10-13-pipeline-stage-refactor/`, supaya entry point memakai
`pipeline/run.sh` dan stage bernomor. Jika belum, pakai compatibility adapter ke
`scripts/run_pipeline_v3.sh`.

UI direction terbaru dari Khalid: **Aqua OS Dashboard**, varian Frutiger Aero
yang bright, clean, dan daily-use. Gunakan sky/aqua depth, white-blue glossy
panels, green glass status blocks, soft highlights, and red only for real failure
states. Jangan jadi bubble wallpaper atau terminal skin; report dan diagnostics
tetap harus mudah dibaca.

## Keadaan 2026-10-14 — Pipeline Desk MVP MyGo native dibangun

Khalid memilih app desktop native MyGo untuk mengoperasikan pipeline tanpa hafal command. Desain final: **Aqua OS / Frutiger Aero**. Implementasi lokal ada di `desktop/pipelinedesk/`, launcher `./run desk`, registry `pipeline/registry.json`.

Fitur MVP:
- App native MyGo, bukan webview.
- Registry pipeline: `pipeline_v3`, `pipeline_v3_presplit`, `loso_only`, `casme2_spotting_eval`.
- Preset tanpa mengetik env vars: default v3, fresh v3, fold-first mean_m, fold-first ROI25, fold-first combo, fresh fold-first, LOSO compact, CAS(ME)2 quick.
- Run controller satu run: command + env disimpan, stdout/stderr ditangkap, events JSONL dan log tail disimpan di `.pipeline/runs/<run-id>/`.
- Dashboard: sidebar pipelines/runs, setup preset + dry-run, stage map, stage details, report summary, artifacts.
- Diagnostics konservatif: missing file/command, OOM, no folds, threshold/gate, unknown.
- Report parser tidak mengarang angka. Jika report tidak ada, UI menampilkan `[from report]` dan source path.

Verifikasi terakhir:
```bash
cd /home/finny/projects/Skripsi/desktop/pipelinedesk
/home/finny/.local/go/bin/go build ./...
/home/finny/.local/go/bin/go vet ./...
PIPELINE_DESK_ROOT=/home/finny/projects/Skripsi /home/finny/.local/go/bin/go test -run TestViewInteractions .
PIPELINE_DESK_ROOT=/home/finny/projects/Skripsi PIPELINE_DESK_SNAPSHOTS=/home/finny/projects/Skripsi/.amp/in/artifacts /home/finny/.local/go/bin/go test -run TestSnapshots .
```
Screenshot artifacts:
- `.amp/in/artifacts/pipelinedesk-setup.png`
- `.amp/in/artifacts/pipelinedesk-running.png`
- `.amp/in/artifacts/pipelinedesk-failed-report.png`

Catatan batasan:
- Jangan klaim full pipeline sudah dites. Tidak dijalankan karena kontrak user melarang smoke/e2e/full run kecuali diminta.
- `go` default PATH tidak tersedia; pakai `/home/finny/.local/go/bin/go` atau launcher `./run desk`.
- MyGo dependency memakai `replace github.com/egoist/mygo => /home/finny/projects/mygo`, sesuai checkout lokal saat ini.
- Future work: compare runs/export, resume/rerun aman, final packaging/icon setelah Khalid memberi direction icon.

### Pipeline Desk launcher display fix

If `./run desk` exits with `mygo: cannot open display`, the root launcher now auto-detects local Wayland/X11 sockets and exports `WAYLAND_DISPLAY` or `DISPLAY` before running MyGo. Verified on finny-pc: `./run desk` stays running with `WAYLAND_DISPLAY=wayland-1`; remaining GTK warnings are theme warnings, not fatal.

## Keadaan 2026-10-14 — Pipeline Desk: dead sidebar dihapus, screenshot final bersih

Lanjutan dari handoff Pipeline Desk sebelumnya. Dua hal yang masih menggantung di handoff lama sudah diselesaikan, satu masih terbuka.

### Selesai — screenshot final diverifikasi
Patch overlap terakhir sebelumnya sudah lulus build dan snapshot tapi belum pernah diinspeksi. Sekarang sudah diinspeksi dengan `view_media`:
- `.amp/in/artifacts/pipelinedesk-setup.png`
- `.amp/in/artifacts/pipelinedesk-running.png`
- `.amp/in/artifacts/pipelinedesk-failed-report.png`

Defect overlap hilang. Tidak ada teks stage timeline bocor di belakang card `Stage details`, tidak ada overlap di panel tengah, background Frutiger Aero tetap dekoratif. Failed state menandai `Stage 6: TRAINING` merah dan `Stage details` fokus ke stage itu.

### Selesai — dead sidebar shell dihapus
`view.go` masih memuat shell sidebar lama (layout yang ditolak: "pipelines should be above not on the side"). Sudah tidak terpanggil karena `view` mendelegasikan ke `viewVariant(c, variantRibbon)`. Dihapus 14 fungsi dari `view.go`, plus `recentRuns`/`displayCommand` dari `app.go`, plus 5 palette var dari `theme.go` yang hanya dipakai shell lama. 1991 → 1717 baris. `pipelinedesk-setup.png` byte-identical sebelum/sesudah, jadi render tidak berubah.

### Verifikasi
```bash
cd /home/finny/projects/Skripsi/desktop/pipelinedesk
/home/finny/.local/go/bin/go build ./...   # PASS
/home/finny/.local/go/bin/go vet ./...     # PASS
PIPELINE_DESK_ROOT=/home/finny/projects/Skripsi PIPELINE_DESK_SNAPSHOTS=/home/finny/projects/Skripsi/.amp/in/artifacts \
  /home/finny/.local/go/bin/go test -run 'TestSnapshots|TestVariantSnapshots|TestViewInteractions' .  # PASS
```
Launch: `./run desk` build sukses dan app jalan.

### Masih terbuka
1. **Varian prototipe** — `variantControlPanel` dan `variantLabMonitor` masih di `variants.go` dan masih dirender `TestVariantSnapshots`. Khalid belum memutuskan: simpan sebagai prototipe atau hapus.
2. **Dry-run real dari UI** — controller sudah tersambung tapi belum pernah dijalankan dari app, sesuai kontrak "jangan jalankan smoke/e2e/full run kecuali diminta".
3. **`reports/summary.json`** — controller menulis `run.json`, `events.jsonl`, `stages/run.log`; file report ternormalisasi masih future work. Report summary sekarang membaca Markdown yang sudah ada dan menampilkan `[from report]` kalau tidak ada.
4. **Compare runs/export (issue 07), stop/resume/rerun aman (issue 08), packaging + icon (issue 09)** — belum dikerjakan.
5. **Dua proses `mygo dev` lama masih hidup** (PID 148843, 148902, ~54 menit) meng-watch direktori yang sama; dibiarkan karena bukan milik thread ini. Matikan manual kalau mengganggu.

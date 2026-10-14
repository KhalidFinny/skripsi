# PROGRESS — Geometri Wajah + Head Pose

> **Ringkasan rapi semua perubahan + hasil train/val/test:**
> `report/documentation/ringkasan.md`
> File ini adalah catatan progres per sesi (detail teknis).
>
> **STRUKTUR BERUBAH (2026-10-13).** Pipeline kini di `pipeline/`
> (`./pipeline/run.sh`, stage di `pipeline/stages/`). Peta stage:
> `pipeline/README.md`. `scripts/` sudah tidak ada; kode lama → `legacy/`,
> eksperimen → `research/`. Entri bertanggal di bawah masih memakai path lama
> karena itu catatan zamannya.

## 2026-10-13 — EKSEKUSI: struktur folder dirapikan (stage pipeline terpisah)

### Arahan user
"go ahead with the folder and file rarrranging i need it to be able to see, need
it to be organized and tidy", lalu "delete duplicates and unused also just group
them on soe folders", dengan dua batasan tegas: **"but dont delete notebooks"**
dan **"the ones that are needed on recent result of training dont delete"**.

### Yang dikerjakan
Plan `report/plans/2026-10-13-pipeline-stage-refactor/` dieksekusi penuh.
`scripts/` (61 file) dihapus setelah semua isinya punya rumah baru:

| Tujuan | Isi |
|---|---|
| `pipeline/stages/stage_0..8` | 10 stage, bernomor dan bernama jelas |
| `pipeline/serve/` | `train_final.py`, `predict.py` |
| `pipeline/` | `run.sh` (dulu `run_pipeline_v3.sh`), `spotting_config.py`, `paths.py`, `README.md` |
| `research/casme2/` | 27 skrip eksperimen CAS(ME)² |
| `research/audits/` | 4 audit (anxiety_regime, feature_representation, identity_dominance, rise_control) |
| `legacy/` | 17 file lama + `legacy/README.md` (subfolder runners/ official_tabr/ export/ methods/ tools/) |

Rename yang menyesatkan: `comparasion/`→`shared/` (config & ROI) +
`legacy/comparasion/`, `src/`→`tabr/`, `features_extraction/`→`features/`,
`helper/helper.py`→`shared/helper.py`, `outputs/models/`→`models/`.

### Kenapa tiap stage punya nomor di namanya
Plan menulis `0_presplit.py`, tapi **file Python tidak boleh diawali angka**
(`import 1_spotting` = SyntaxError, sudah diuji). Empat modul stage diimpor file
lain, jadi dipakai `stage_N_nama.py`.

### Jebakan yang harus ditutup
Semua skrip stage mencari root repo lewat `Path(__file__).parent.parent`. Setelah
pindah dua tingkat ke `pipeline/stages/`, itu rusak dan semua impor gagal. Satu
helper `pipeline/paths.py` dipakai 10 stage; bootstrap disesuaikan ke
`parents[2]` (stage/serve) dan `parents[1]` (stage_7_baseline).

### Yang sengaja TIDAK dilakukan
- **`experiments/configs/` tidak dipindah.** 660 referensi menyebutnya, ±645 di
  antaranya ada di `third_party/.../DONE.json` — catatan permanen run training
  terakhir. Memindahkan = merusak provenance hasil, untungnya kecil.
- **Tidak ada notebook yang dihapus** (arahan user). 30 notebook dikelompokkan:
  `notebooks/preprocess|spotting|export|tabr|legacy/`.
- **Tidak ada artefak training yang dihapus** (arahan user): 47 folder / 31
  `summary.md` di `output/training/` utuh, `output/final_model/` utuh.
- Tidak ada file yang dihapus selain: 3 folder kosong, 4 log 0 byte,
  `desktop/pipelinedesk/.amp`. Tidak ada duplikat byte-identik di luar hasil.

### Verifikasi
- `./pipeline/run.sh --dry-run` → 7 stage, path benar.
- `V3_PRESPLIT=1 ./pipeline/run.sh --dry-run` → 8 stage (0–8).
- `bash -n pipeline/run.sh` dan `bash -n run` → bersih.
- `py_compile` bersih untuk `pipeline/ features/ tabr/ shared/ apex/ research/`.
- Impor diuji nyata: stage_1/5/6/7, stage_8, `shared.config`, `shared.roi`,
  `tabr.TabR`, `features.poc` semua OK.
- `grep` path lama di kode hidup → bersih (sisa hanya di `legacy/` + dokumen
  historis).
- `./run` (pintasan) diperbaiki; `pipeline/registry.json` (dipakai Pipeline
  Desk) diperbarui ke path baru.

### Belum
- **Belum di-commit** — menunggu perintah Khalid.
- Angka pipeline belum dibuktikan tidak berubah sampai run berikutnya.
- BAB III (Metodologi) masih placeholder.

## 2026-10-13 — Plan: refactor pipeline (stage terpisah + struktur folder)

### Arahan user
"plan for a refactor of pipeline files and folder restructure right now it looks
confusing and i cant find when i need a pipeline to show, so each stage should be
well separated and well mark on which is which, for instance where is the split,
the spotting, the apex etc".

### Yang dibuat
`report/plans/2026-10-13-pipeline-stage-refactor/` — **PLAN SAJA, belum
dieksekusi**. Isi: `CONTEXT.md`, `plan.md`, dan 7 issue.

Inti rencananya: pipeline dipindah ke **satu folder `pipeline/`** dengan stage
bernomor yang namanya menjelaskan urutan, lalu eksperimen dan kode legacy
dikeluarkan dari jalur pipeline.

### Temuan discovery (angka nyata)
`scripts/` berisi **61 file** dan habis terbagi tanpa sisa:

| Tujuan | Jumlah | Isi |
|---|---|---|
| `pipeline/stages/` | 10 | stage 0–8 |
| `pipeline/serve/` | 2 | train_final, predict |
| `pipeline/` | 2 | run.sh, spotting_config.py |
| `research/casme2/` | 26 | eksperimen CAS(ME)² |
| `research/audits/` | 4 | audit umum |
| `legacy/` | 17 | runner & skrip lama |
| **total** | **61** | |

`scripts/` **hilang sepenuhnya** setelah refactor.

### Tiga nama yang menyesatkan (diverifikasi hidup, bukan dead code)
- `comparasion/` — terdengar folder eksperimen, padahal `comparasion/core/`
  **dipakai produksi** oleh stage 2 (`ComparisonConfig`, `ROIExtractor`).
- `scripts/spotting.py` — bukan pipeline spotting, hanya dataclass
  `SpottingConfig` (52 baris). Pipeline spotting = `process_spotting_pipeline.py`.
- `src/` — isinya model TabR; namanya tidak memberi petunjuk apa pun.

### Jebakan teknis yang wajib ditangani
Tiap skrip stage mencari root repo dari lokasi dirinya:
`ROOT = Path(__file__).resolve().parent.parent`. Setelah pindah ke
`pipeline/stages/` (dua tingkat di bawah root), ini **rusak** dan semua impor
(`from apex import ...`, `from features_extraction ...`,
`from comparasion.core.config import ...`) gagal. Solusinya satu helper bersama
`pipeline/paths.py`, dipakai 10 stage.

### Blocker
**Ada pipeline yang sedang berjalan** saat plan ditulis (PID 314580,
`run_pipeline_v3.sh --fresh`, stage 1 spotting, ±32 menit). Memindahkan file
sekarang akan memutus proses itu. **Eksekusi harus menunggu run selesai.**

### Isi plan
7 issue, urut prioritas:
1. (critical) paket `pipeline/` + titik masuk + peta stage README
2. (critical) pindahkan 10 stage + perbaikan bootstrap `ROOT`
3. (high) pisahkan eksperimen CAS(ME)² → `research/`
4. (high) karantina 17 file legacy → `legacy/`
5. (medium) rename modul menyesatkan (`comparasion/`→`shared/`, `src/`→`tabr/`,
   `features_extraction/`→`features/`)
6. (medium) rapikan folder data (`outputs/`→`models/`, configs → `pipeline/configs/`)
7. (low) sinkronkan dokumen + perintah run (23 dokumen menyebut path lama)

Kalau Khalid ingin berhenti lebih awal: **setelah issue 01–02, pipeline sudah
ketemu dan stage sudah jelas** — itu inti permintaannya.

### Verifikasi plan
- Struktur plan dicek: 9 file, semua link issue di `plan.md` resolve.
- 7 tabel markdown valid (0 baris rusak), semua code fence seimbang.
- Aritmetika 61 file diverifikasi ulang secara programatik (26+4+17+10+4 = 61).
- **Tidak ada file yang dipindah, tidak ada kode yang diubah.** Plan saja.

### Belum
- Eksekusi plan (menunggu run selesai + persetujuan Khalid).
- BAB III (Metodologi) masih placeholder.

## 2026-10-13 (malam, lanjutan) — MODE FOLD-FIRST: split per orang SEBELUM spotting + evaluasi holdout

### Permintaan user
"Split train/test/val dari awal sebelum spotting supaya berjalan terpisah dan
tidak ada orang yang terlihat di tengah; coba roi25 lagi."

### Temuan verifikasi dulu (jujur)
Protokol lama SUDAH bebas bocor secara matematis: split LOSO subjek-disjoint
(`run_loso.py`), imputer/scaler/balance fit di train saja, spotting per video
dengan ambang self-referensial (mean+std per video), baseline netral per
orang. Tidak ada aliran informasi dari video orang test ke fitur train.
Jadi mode baru ini **bukan perbaikan bocor** — nilai gerak metrik ≈ 0.
Nilainya: jaminan STRUKTURAL (12 orang tidak pernah dibaca sampai evaluasi
akhir) + menutup serangan "tuning melihat semua orang" di sidang.

### Yang dibangun (plan: report/plans/2026-10-13-fold-first-presplit-holdout/)
1. `scripts/split_persons_presplit.py` — tahap 0: 56 orang → 44 train pool +
   12 holdout, strata label-pair (tinggi_both 24 / changed 18 / rendah_both
   14 → 5+4+3), seed 42 deterministik. Output `output/presplit/`.
2. `SPOT_INCLUDE_PERSONS` di `process_spotting_pipeline.py` — video orang di
   luar daftar TIDAK dibaca sama sekali. Terverifikasi di tree nyata:
   560 video = 440 train + 120 holdout, 0 tak dikenal. Default kosong =
   perilaku lama bit-identik.
3. `run_loso.py --test-persons-file` — mode SATU fold: test = 12 orang
   holdout, train/val = 44 sisanya (mesin fold sama: imputer/scaler fit
   train, scan val has_both_labels). Mode LOSO lama tidak berubah.
4. `scripts/combine_feature_tables.py` — gabung pkl temporal train+holdout
   dengan validasi keras: kolom identik (nama+urutan) DAN orang disjoint.
5. `run_pipeline_v3.sh` mode `V3_PRESPLIT=1`: stage 0 presplit → stage 1-7 di
   44 orang (SPOT_INCLUDE_PERSONS=train_persons.txt) → stage 8 evaluasi
   holdout (spotting 12 orang resep sama → fitur → combine → 1 fold final →
   collect). TOTAL_STAGES jadi 8. Dry-run kedua mode terverifikasi; `bash -n`
   bersih.
6. `V3_EXTRA_CONFIGS` (multi-config satu run): stage 6/7/8 mengulang per
   config dengan dataset turunan `<dataset>_cfg_<tag>`; FRESH membersihkan
   semuanya; baseline pembanding tetap sekali (fitur identik). Dry-run 2
   config terverifikasi (dataset primer + `_cfg_roi25_reg`).

### Cara menjalankan (user) — SATU perintah penuh
A/B roi25 BUKAN lagi run terpisah: `V3_EXTRA_CONFIGS` melatih semua config
dalam satu run (stage 6/7/8 mengulang per config; fitur stage 1-5 sekali).

```bash
# RUN PENUH: fold-first + sinyal spotting combo (tervalidasi CAS(ME)2:
# F1 0,3343 vs 0,3192) + 2 config (compact + roi25_reg kapasitas besar)
V3_PRESPLIT=1 V3_SPOT_SIGNAL=combo \
V3_EXTRA_CONFIGS="experiments/configs/tabr_loso_roi25_reg.toml" \
  ./scripts/run_pipeline_v3.sh --fresh
```

Output per config: `output/training/<dataset>/summary.md` (LOSO-44) dan
`output/training/<dataset>_holdout/summary.md` (12 orang). Dataset config
ke-2 = `convat_apex_anxiety_loso_roi25_reg_cfg_roi25_reg`.

### Hasil (run user 2026-10-13 21:54, fold-first + combo + 2 config, ~73 menit)

Eksekusi BENAR: stage 1 menulis `INCLUDE_PERSONS: 440 video diproses, 120
dilewati` — 12 orang holdout tidak dibaca sampai stage 8. Mesin fold-first
bekerja ujung-ke-ujung; model final ada di fold_000 tiap dataset _holdout.

**LOSO-44 (train pool):**
| config | accuracy | BA | MCC | AUC |
|---|---|---|---|---|
| compact | 0,3864 | 0,3968 | −0,2101 | 0,4484 |
| roi25_reg | 0,4242 | 0,4533 | −0,1020 | 0,4211 |

**HOLDOUT-12 (24 sesi, baseline mayoritas 0,5833):**
| config | accuracy | BA | MCC | AUC | CI |
|---|---|---|---|---|---|
| compact | 0,4167 | 0,4810 | −0,1296 | 0,5905 | 0,254–0,746 |
| roi25_reg | **0,5278** | **0,5857** | **+0,3085** | 0,6667 | 0,320–0,807 |

Gate within-subject (44 orang, combo): BA 0,5357, **p=0,4577** — tidak ada
sinyal; grup berubah 0/55 fitur signifikan.

**Bacaan jujur:**
1. **Sinyal combo TIDAK berpindah dari CAS(ME)² ke data anxiety.** LOSO train
   pool turun ke 38–42% (mean_m dulu 45,83% di 56 orang). Alasan plausible:
   CAS(ME)² = mikro-ekspresi terpose lab high-fps; anxiety = rekaman lapangan
   30 fps dengan gerakan latar berat — kanal Hpoc (kemiripan puncak POC)
   ikut rusak oleh noise latar, sedangkan mean_m mengkuantisasi noise.
   Combo tidak tervalidasi di sisi anxiety; `mean_m` tetap default.
2. Holdout roi25_reg (52,8% / BA 58,6% / MCC +0,31) terlihat "paling tidak
   jelek", TAPI n=24 sesi: CI memuat baseline 0,5833, AUC antar-seed
   tidak stabil (0,51–0,74), dan ia dipilih sebagai yang terbaik dari 2
   config pada 12 orang yang sama (inflasi seleksi). Tidak bisa diklaim
   > baseline.
3. Dua resep spotting lengkap sudah dicoba pada protokol fold-first: mean_m
   (45,83% pooled-56) dan combo (38–42% LOSO-44). Keduanya mentok.
   Bottleneck terukur tetap: SNR gerakan latar di spotting.
4. Yang tersisa dengan bukti: (a) cutoff 0,5 (batas event lebih rapat,
   tervalidasi F1-ketat di CAS(ME)²); (b) tambah N lewat `datatest`
   (49 subjek, 0 overlap — butuh izin dosen); (c) tulis apa adanya.

## 2026-10-13 (malam, lanjutan 2) — LEVER spotting anti-noise (motion-comp + MDMD), siap di-A/B

### Perintah user
"Fix sinyal & algoritma spotting, kerjakan lever 1 dan 2."

### Dasar (deep dive: report/findings/spotting-feature-deepdive.md)
Combo gagal bukan karena jumlah fitur, melainkan karena sinyalnya masih
frame-0-referensial dan TIDAK memakai pembalikan arah gerak. Dua lever
diimplementasikan, keduanya GATED (default OFF = perilaku lama bit-identik):

1. **LEVER 1 — Rigid/global motion compensation** (`V3_SPOT_MOTION_COMP=1`).
   Di `compute_roi_magnitudes`: kurangi median antar-blok (dx, dy) per frame,
   magnitude dihitung ulang dari DEVIASI lokal. Gerakan kepala/latar yang
   serentak di semua blok hilang; ekspresi lokal selamat. Terverifikasi pada
   data sintetik: blok serempak → 0; satu blok beda → 7 (terisolasi).
2. **LEVER 2 — MDMD-style signal** (`V3_SPOT_SIGNAL=mdmd`, jendela
   `V3_SPOT_MDMD_K=5`). Wang 2017: sinyal'[i] = sinyal[i] − rata-rata tetangga
   ±k, clip ≥ 0. Tren lambat (kepala) → ~0; puncak tajam (ekspresi) selamat.
   Terverifikasi: puncak 50 dipertahankan, tren linier & konstan → 0. Aktif
   juga via `V3_SPOT_MDMD=1`.

### Wiring
`process_spotting_pipeline.py`: `SPOT_MOTION_COMP`, `SPOT_MDMD`,
`SPOT_MDMD_K`, fungsi `_mdmd_difference`, cabang motion-comp di
`compute_roi_magnitudes`, hook `use_mdmd` di `build_roi_signals` (mematikan
want_hpoc). `run_pipeline_v3.sh`: meneruskan ke stage 1 DAN stage 8 (resep
sama). `bash -n` bersih; dry-run menunjukkan nilai lever tersubstitusi;
logika use_mdmd terverifikasi.

### Cara A/B (fold-first, 2 config)
```bash
V3_PRESPLIT=1 V3_SPOT_MOTION_COMP=1 V3_SPOT_SIGNAL=mdmd \
V3_EXTRA_CONFIGS="experiments/configs/tabr_loso_roi25_reg.toml" \
  ./scripts/run_pipeline_v3.sh --fresh
```

### Hasil
**Menunggu run user.** Pembanding apple-to-apple (protokol fold-first sama):
mean_m 45,83% (pooled-56) | combo LOSO-44 38–42%. Keputusan: kalau
motion-comp/MDMD tidak melewati mean_m, sinyal POC-ABS sudah mentok di SNR
gerakan latar — sisa tuas = tambah N (`datatest`, 26 orang terkonfirmasi,
butuh izin dosen + join nama+timestamp).

## 2026-10-13 (malam) — Fresh run v3 (user): gate within-subject run2 TIDAK direplikasi

### Konteks
User menjalankan `./scripts/run_pipeline_v3.sh --fresh` (sinyal spotting
mean_m default, bukan combo) — 2574 event, 7 stage, ~70 menit. Ini run anxiety
pertama setelah perbaikan pipeline (block 9, 5 ROI kanonik, acuan netral per
orang, fitur arah bertanda). Pembanding: run2 lama (`convat_apex_anxiety_loso_run2_*`).

### Hasil (LOSO 56 fold, level subjek)
| run | accuracy | AUC | sensitivity | specificity | gate within-subject (bal-acc, p) |
|---|---|---|---|---|---|
| run2 lama | 54,46% | 0,5204 | 0,79 | 0,15 | **0,7500, p=0,0100** (geo_temporal) |
| **v3 fresh** | 45,83% | 0,5664 | 0,75 | 0,24 | 0,6389, p=0,0697 (full) / 0,5556, p=0,3582 (rise) |
| baseline gbdt v3 | 0,6071 | — | 0,40 | 0,77 | (permutation p=0,194 — tidak signifikan) |

Per grup: before_sama 0,5789 vs baseline grup 0,6316 (−0,05); before_berubah
0,3333 vs 1,0. Bias prediksi +0,357 (model menebak positif 78,6% vs laju
sebenarnya 42,9%).

### Bacaan jujur (bukan "angka turun jadi lebih buruk")
1. **Satu-satunya hasil signifikan (gate BA 0,75, p=0,01) TIDAK tahan terhadap
   perbaikan pipeline.** Dengan fitur baru: 0/60 fitur signifikan Wilcoxon di
   grup berubah, sedangkan grup KONTROL punya 8/55 — pola berbalik: efek sesi
   terlihat di kontrol, bukan di berubah. Artinya hasil run2 kemungkinan besar
   artefak pipeline lama (mis. klip onset-terkontraksi, 3 ROI, block 7),
   bukan sinyal kecemasan.
2. AUC 0,5664 di atas run2 (0,5204) tapi CI accuracy memuat baseline —
   tidak terbukti lebih baik dari mayoritas. GBDT 0,6071 juga tidak
   signifikan (p=0,194).
3. Label: 17 dari 18 subjek "berubah" berubah SATU arah (turun). Deteksi arah
   perubahan (selisih after−before) bal-acc 0,5000 — tidak ada tanda tangan
   arah yang konsisten.
4. State of the art jujur per malam ini: belum ada model/fitur yang terbukti
   membawa sinyal anxiety pada protokol LOSO. Yang tersisa untuk diuji:
   sinyal spotting combo (`V3_SPOT_SIGNAL=combo`, tervalidasi di CAS(ME)²)
   dan/atau batas event lebih rapat (`V3_SPOT_CUTOFF=0.5`).

### Artefak
`output/training/convat_apex_anxiety_loso_roi25_reg{,_baseline}`,
`output/training/within_subject_v3_{poc,geo_temporal}`,
log `logs/pipeline_v3_20261013_191206.log`.

## 2026-10-13 (lanjutan 3) — Sinyal Hpoc: fitur M paper yang dibuang, MENANG tipis tapi konsisten

### Arahan user
"spotting dan apeks more deep dive — lihat paper Bu Ullah Rosiani, she said it
can be more than optical flow where it had its own magnitude. Find the most
optimized magnitude OR ANY OTHER spotting config/method. Jangan fokus POC/TabR,
fokus HANYA spotting + cari masalah dari FINAL.pdf."

### Temuan kunci dari teks lengkap paper (Rosiani et al. 2020, IJIES 13(6))
**Fitur M paper = NILAI PUNCAK POC (Hpoc), bukan |V|.** Bukti di paper: blok
contoh dengan XB=2, YB=2 diberi MB=0,46 (= nilai puncak 0,4687). Kode kita
(`vektor.py:37`) menghitung val_max lalu membuangnya. Hipotesis: Hpoc kontinu
di (0,1] — tidak terkuantisasi 1 piksel seperti |V| — jadi membawa sinyal
sub-piksel yang hilang di data 30 fps.

### Hasil audit (86 video CAS(ME)², 4 konfigurasi × 4 sinyal, resep deteksi baku)
| sinyal | F1 | vs baseline |
|---|---|---|
| **combo global: z(mean_m)+z(hpoc)** | **0,3343** | +1,5 poin |
| hpoc block 5 (ukuran paper) | 0,3329 | +1,4 |
| hpoc block 9 | 0,3245 | +0,5 |
| mean_m (baseline) | 0,3192 | — |
| resep persis paper: acuan berurutan (semua sinyal) | 0,21–0,25 | GAGAL |
| aturan eksklusi blok-diam paper (hpoc_drop_mov) | 0,22 | GAGAL |

Validasi split subjek: A→B pilih combo (test 0,3262), B→A pilih hpoc b5 (test
0,3198) — kedua fold memilih keluarga Hpoc, keduanya ≥ baseline. Pola paling
konsisten dari semua sweep sejauh ini. Combo per-ROI lebih lemah (0,3113) —
yang menang kombinasi level global.

### Yang diubah di kode
- `process_spotting_pipeline.py`: `SPOT_SIGNAL=mean_m|hpoc|combo` (default
  mean_m — terverifikasi bit-identik, tidak ada regresi).
- `run_pipeline_v3.sh`: meneruskan `V3_SPOT_SIGNAL`.
- Skrip baru: `scripts/audit_hpoc_casme2.py` + cache
  `output/training/casme2_hpoc_signals` (86 video).
- Findings: `magnitude-deepdive.md` §7, `koreksi-final-pdf.md` §7–10
  (tambahan: acuan frame-0 vs listing berurutan, smoother 5%→3%, float64→int,
  hitung blok 98→79 / fitur 392→316, definisi M).

### Uji A/B berikutnya di sisi anxiety (user yang menjalankan)
```bash
V3_SPOT_SIGNAL=combo ./scripts/run_pipeline_v3.sh --fresh
```

Plan: `report/plans/2026-10-13-hpoc-spotting-paper-alignment/` (3 isu selesai).

## 2026-10-13 (lanjutan 2) — Deep dive MEKANISME spotting lengkap (5 komponen)

### Arahan user
"spotting is still not perfect... deep dive the spotting mechanism, ALL of the
spotting stuff" — sweep sebelumnya baru menyentuh agregasi, bukan mekanismenya.

### Yang diuji (semua di CAS(ME)², resep deteksi baru)

1. **Sub-piksel POC** (serangan langsung ke bottleneck kuantisasi): koreksi
   parabolik pada puncak korelasi, termasuk saat puncak di tengah. Sintetis
   berfungsi (0,5px→0,28, 1px→0,99, 2px→1,97). **Di video nyata: 0,150 vs
   integer 0,146 — tidak ada perbedaan.** Kesimpulan: faktor pembatas adalah
   SNR gerakan latar (41% blok sudah bergerak tanpa ekspresi), bukan resolusi
   numerik. Kuantisasi bukan batas praktis.
2. **Koreksi skala ROI** (piksel asli vs resize): 0,150 vs 0,150 — tidak
   berpengaruh.
3. **Kegagalan landmark dlib**: 0,0% dari 24.709 frame — bukan masalah.
4. **Acuan baseline** (abs/lag30/lag10/seq, 41 video): abs menang telak
   (0,3486 vs ≤0,19) — frame-0 dikonfirmasi ketiga kalinya.
5. **Internals detektor** (merge/top_k/min_dur/uptick/radius, 86 video):
   KOMBI (topk4+mindur4+uptick0,9+radius200) F1 **0,3451** vs BASE 0,3192,
   menang di KEDUA fold validasi subjek (0,3469/0,3437). TAPI batas
   onset/offset memburuk (F1 ketat 0,0986 vs 0,1282; durasi 84 vs GT 28).
   Default pipeline untuk fitur tetap BASE; KOMBI dicatat sebagai opsi
   pelaporan spotting. radius 30-60 searah dengan cutoff 0,5 (batas lebih
   rapat, F1 ketat naik) — kandidat pasangan uji sisi anxiety.

### Skrip baru
`probe_spotting_mechanism_casme2.py`, `audit_detector_internals_casme2.py`,
`audit_baseline_recheck_casme2.py`. Findings: `magnitude-deepdive.md` §6,
`audit-spotting-casme2.md` §11-12.

### Status mekanisme spotting setelah deep dive penuh
Terukur dan tertutup: agregasi (mean), acuan (frame-0), detektor (BASE untuk
fitur / KOMBI untuk pelaporan), sub-piksel/skala/landmark (non-isu). Yang
tersisa untuk dibuktikan di sisi anxiety (user yang menjalankan): apakah batas
event lebih rapat (`V3_SPOT_CUTOFF=0.5`, atau +radius 30-60) mengangkat fitur.

## 2026-10-13 (lanjutan) — Deep dive magnitude spotting + sweep agregasi × cutoff

### Arahan user
Fokus ke spotting: deep dive magnitude yang dipakai, uji konfigurasi spotting,
pastikan split terjadi SEBELUM preprocessing (anti-leak), dan koreksi apa yang
salah di FINAL.pdf. Dasar pemikiran: pencipta POC-ABS (Rosiani 2020) melaporkan
POC-ABS mengungguli optical flow, jadi cari definisi magnitude spotting terbaik
untuk POC-ABS.

### Hasil utama (jawaban terukur)

1. **Definisi magnitude terbaik = mean per ROI lalu mean antar ROI (yang sudah
   dipakai).** Dua sudut pengukuran independen sepakat:
   - Peringkat puncak ekspresi (10 video CAS(ME)², 1,95 juta blok,
     `scripts/diag_magnitude_casme2.py`): mean **0,146** vs weighted 0,164,
     top25 0,172, count 0,217, max 0,271 (0=terbaik, 0,5=acak).
   - Sweep F1 86 video (`scripts/audit_mag_agg_casme2.py`, resep deteksi baru):
     mean_m **F1 0,3192** > motion_count 0,3184 > max_m 0,2986 > mean_y 0,2304
     > mean_x 0,1734 > angle_R 0,1140. Validasi split subjek A/B tidak memilih
     pemenang lain yang stabil (A→B motion_count, B→A max_m).
2. **Karakter magnitude**: 15 nilai diskret (oX/oY integer −4..4), 57,8% blok
   diam, saturasi batas minor (~5%), dan ekspresi hanya menaikkan fraksi blok
   bergerak 0,447 vs 0,409 baseline (1,09×) — bottleneck bukan definisi
   agregasi melainkan kuantisasi sinyal POC + gerakan latar video.
   Detail: `report/findings/magnitude-deepdive.md`.
3. **cutoff_ratio**: 0,3 menang F1 longgar di KEDUA fold → default tetap 0,3.
   0,5 menang F1 ketat (IoU≥0,5: 0,1637 vs 0,1282) + durasi 61→41 frame
   (GT median 28). Dibuka sebagai opsi `SPOT_CUTOFF` untuk uji A/B sisi anxiety.

### Leak check (permintaan eksplisit user)

Split LOSO per subjek terjadi SEBELUM preprocessing di kedua runner:
`run_loso.py` baris 654-662 dan `run_loso_lit_tabr.py` baris 141-145 —
imputer/scaler di-fit di train saja, val/test hanya transform; balancing hanya
di train. `subject_standardize` (opsional, bukan default) memakai statistik
subjek sendiri tanpa label. Aman.

### Yang diubah di kode

- `scripts/process_spotting_pipeline.py`: `SPOT_CUTOFF` env (default 0,3).
- `scripts/run_pipeline_v3.sh`: meneruskan `V3_SPOT_CUTOFF` (default 0,3).
- Skrip baru: `scripts/diag_magnitude_casme2.py`, `scripts/audit_mag_agg_casme2.py`.
- Findings: `report/findings/magnitude-deepdive.md` (baru),
  `report/findings/audit-spotting-casme2.md` §10 (sweep),
  `report/findings/koreksi-final-pdf.md` (baru — koreksi FINAL.pdf siap tempel).

### Koreksi FINAL.pdf (ringkasan, detail di findings)

Block 7→9, 3→5 ROI, parameter deteksi (distance 5/prominence 0.5 → distance 1/
prominence rel 0,04 + smoothing 3% adaptif + ranking prominence), protokol
GroupShuffleSplit+ensemble → LOSO 56 fold split-sebelum-preprocessing, angka
0,7579/0,58 (leaky) → 54,46% LOSO jujur + gate within-subject BA 0,75 p=0,01.

### Cara uji cutoff 0,5 di sisi anxiety (user yang menjalankan)

```bash
V3_SPOT_CUTOFF=0.5 ./scripts/run_pipeline_v3.sh --fresh
```

Plan: `report/plans/2026-10-13-spotting-magnitude-deepdive/` (4 isu selesai).

## 2026-10-13 — Ringkasan riset: timeline + tabel hasil (Iterasi 4.65)

### Arahan user
"i more needing a timeline so that i know the table of results is good but i need
a timeline time stamp on when what did it have, what is the result what is the
problem, then the next is the same but with the what we change also from before
and the new results from that change timestamp but keep the result table tho its
good".

### Yang diubah
`report/documentation/ringkasan.md` bagian 3 diganti dari "6 fase naratif"
menjadi **timeline bertimestamp** dengan 5 kolom:

    Waktu | Yang dikerjakan | Hasil | Masalah | Yang diubah -> hasil baru

Jadi tiap baris menjawab: kapan, apa yang dikerjakan, hasilnya apa, masalahnya
apa, lalu apa yang diubah untuk mengatasi masalah itu dan hasil barunya.

Dibagi 7 era (Era 1 membangun s/d Era 7 model final + proposal), ditutup
**ringkasan timeline 1 layar** (12 tonggak penting).

### Sumber timestamp (semua nyata, bukan karangan)
- `git log --format='%ad'` untuk era 2025-09 s/d 2026-08 (tanggal commit)
- nama file log `logs/*_YYYYMMDD_HHMMSS.log` untuk kejadian 2026-09 s/d 2026-10
- `stat -c '%y'` pada `output/training/*/summary.md` untuk waktu run selesai
- jam di dalam `logs/pipeline_v3_20261012_140147.log` untuk run terakhir
  (mulai 14:01:47, selesai 15:06:24)

### Tabel hasil diperbaiki
- Kolom "Tanggal" jadi "**Waktu**" dan diisi jam: 2026-09-17 11:41,
  2026-09-28 12:00, 2026-10-10 10:10, 2026-10-11 21:51, 2026-10-12 09:55,
  2026-10-12 13:36, 2026-10-12 13:37, 2026-10-12 15:06.
- **Urutan dibetulkan**: baris 11-13 sebelumnya tidak urut (LitTabR 09:55
  ditaruh setelah run 13:36). Sekarang benar-benar kronologis. Isi tabel tetap
  (user bilang tabelnya sudah bagus), hanya urutan + kolom waktu yang dirapikan.

### Verifikasi
- 19 tabel dicek strukturnya: 118 baris, **0 baris rusak**, 2 code fence.
- Render ke HTML + screenshot diperiksa: timeline dan tabel hasil tampil rapi.
- Angka tetap sama dengan sumbernya; tidak ada angka baru.

### Belum
- BAB III (Metodologi) masih placeholder.

## 2026-10-13 — Ringkasan riset: satu dokumen rapi (Iterasi 4.64)

### Arahan user
"changes log, progress, results update all for changes from the start what we add
why we add what we fiks on each changes on each runs, the result we need with
train test val until the most recent one in an md and it needs to be readable with
words that everyoen can understand not too much technical jargon and a more tidy
design".

### Yang dibuat
`report/documentation/ringkasan.md` — **BARU**. Satu dokumen yang merangkum
seluruh penelitian dalam bahasa sederhana, dengan tampilan tabel (bukan paragraf
panjang). Isinya:

1. Penelitian ini tentang apa (diagram alur + fakta dataset)
2. Cara membaca hasil (train / val / test dijelaskan)
3. **Perjalanan perubahan** dalam 6 fase, tiap fase pakai tabel
   "apa yang dikerjakan / kenapa / hasilnya"
4. **Tabel semua run (train / val / test)** — 14 baris, urut dari paling lama
   sampai **run paling baru**
5. Hasil tahap spotting CAS(ME)²
6. Hasil uji dalam-subjek (temuan terkuat, BA 0,75 p 0,010)
7. Kesimpulan jujur (berhasil / belum berhasil / langkah berikutnya)
8. Peta lokasi file + kamus istilah

### Penunjuk ditambahkan
Supaya tidak ada yang tersesat, ketiga dokumen lama diberi penunjuk ke ringkasan:
- `report/documentation/changes-log.md` — catatan di header
- `PROGRESS.md` — catatan di bawah judul
- `report/results/results.md` — catatan di header

### Verifikasi
- 16 tabel di `ringkasan.md` dicek strukturnya (jumlah kolom konsisten,
  0 baris rusak), 2 code fence seimbang.
- Semua angka diambil dari sumber yang sudah ada (`summary.md` tiap run,
  changes-log, `output/final_model/meta.json`). Tidak ada angka baru/karangan.
- Run paling baru yang ditampilkan = **STATE/session (2026-10-12)**:
  train 89,90% / val 62,50% / test 54,46%, baseline 57,14%.

### Belum
- BAB III (Metodologi) masih placeholder.

## 2026-10-13 — Akses bebas untuk 28 paper proposal (Iterasi 4.63)

### Arahan user
"can i get the paper that we used to be getting from somewhere where we dont need
to become a member or we dont need to purchase atleast just free sign in? because
some ieee papers are locked away and i need a more easier way to access them to
verify".

### Yang diubah
`report/documentation/research-papers.md` bagian "Tabel lengkap: 28 paper yang
dipakai di proposal" kini punya **dua tautan per baris**: DOI resmi dan
**akses bebas** (gratis, tanpa langganan/beli/anggota).

Sumber tautan gratis dicari lewat **Unpaywall API** (`api.unpaywall.org`), lalu
setiap tautan diuji satu per satu dengan `curl -L` supaya tidak ada tautan mati.

### Cara akses per kondisi paper
| Kondisi | Jalur gratis |
|---|---|
| Jurnal OA penuh (MDPI, Frontiers, Springer/BMC, JTIIK, Edu Komputika, IJIES, IEEE Access) | tautan gratis penerbit |
| IEEE tapi punya versi OA | PDF OA dari ieeexplore (ielx7) |
| IEEE/ACM tapi versi OA di arXiv | PDF arXiv |
| SAGE / J. Neuroscience tapi ada di PMC | PDF PMC |

### Kasus yang perlu dicatat
- **Lu dkk. 2022 (nomor 5, ACM)**: versi prosiding ACM-nya terkunci dan tidak
  punya salinan OA. Yang gratis adalah **versi jurnal lanjutannya** di arXiv
  (`2409.00017`) dengan penulis yang sama dan topik yang sama, tetapi **bukan
  artikel identik**. Ini ditulis eksplisit di md supaya tidak menyesatkan.
- **Zhao 2023 (JPROC)** dan **Li 2022 (TAFFC)** — dua paper IEEE yang dikira
  terkunci — ternyata punya PDF OA resmi dari IEEE (`ielx7`). Keduanya diunduh
  dan diperiksa: isinya benar artikel yang dimaksud (Zhao: 21 halaman; Li: 19
  halaman).
- **Ben 2022 (TPAMI)**, **Arik 2021 (AAAI)**, **Johnson 2021 (TBDATA)** → jalur
  arXiv.
- **Hur 2020** dan **Lei 2024** → jalur PubMed Central.

### Hasil uji tautan gratis (2026-10-13)
- **16 tautan** mengembalikan PDF langsung (`application/pdf`) tanpa login.
- **8 tautan** mengembalikan halaman artikel yang bisa dibaca.
- **MDPI, JTIIK, ACM** membalas 403 untuk permintaan otomatis (sudah dicoba
  dengan header peramban lengkap); halamannya normal saat dibuka manual.
- **Tidak ada tautan ke situs berbagi ilegal.** Semua tautan gratis berasal dari
  penerbit, arXiv, PubMed Central, atau situs jurnal resmi.

### Verifikasi
- Tabel: **28 baris**, 26 tautan DOI + 2 tautan arXiv, **30 tautan gratis**
  (2 baris punya dua tautan gratis: halaman arXiv dan PDF-nya).
- `proposal/main.typ` dan `refs.bib` **tidak disentuh**; `typst compile` tetap
  0 error, PDF **24 halaman**.

### Belum
- BAB III (Metodologi) masih placeholder.
- Daftar Gambar/Tabel masih disembunyikan sampai BAB III ada.

## 2026-10-12 — Paper proposal didata ulang di research-papers.md (Iterasi 4.62)

### Arahan user
"all the paper we found put it on the md of research paper the ones on the
proposal, and then give it the link that i can open and verify".

### Yang diubah
`report/documentation/research-papers.md` bagian "Sitasi BAB II Proposal"
(sejak Iterasi 4.58) diganti menjadi **"Paper yang Dipakai di Proposal
(2017-2026)"** yang memuat daftar lengkap **28 paper** yang benar-benar
disitasi di proposal, lengkap dengan tautan yang bisa diklik.

Struktur bagian baru:

    ## Paper yang Dipakai di Proposal (2017-2026)
    ### Substitusi sumber: 7 dari 28 sitasi proposal acuan ditolak
    ### Tabel lengkap: 28 paper yang dipakai di proposal
        A. Ekspresi wajah dan ekspresi mikro          (10 paper)
        B. Data tabular dan pembelajaran mesin         (6 paper)
        C. Kecemasan, stres, dan kesehatan mental      (9 paper)
        D. Nasional (minimal SINTA 2)                  (3 paper)
    ### Hasil pemeriksaan tautan (2026-10-13)
    ### Bentuk 2.1 dan isi Tabel 2.1
    ### Bentuk 2.2 Dasar Teori

Kolom tiap tabel: No, Penulis (tahun), Judul, Wadah, **Dipakai di** (letak
sitasinya di proposal), dan **Tautan** (langsung ke DOI/arXiv).

Daftar lama yang bernomor 101-131 dihapus karena sudah tidak sinkron: entri
seperti `liu2022tvli`, `archana2024deep`, `sinulingga2023keyframe`, dan
`huang2020embedding` sudah tidak dipakai lagi, sementara tabel 2.1 berubah dari
10 menjadi 5 baris. Isi baru dibuat dengan **membaca `refs.bib` langsung**, jadi
jumlahnya pasti 28 dan tidak ada yang terlewat atau berlebih.

Dua catatan basi ikut diperbaiki: baris "Huang dkk. 2020 dipertahankan" (padahal
sudah dihapus) dan baris klaim Liu dkk. (Liu sudah tidak dipakai).

### Verifikasi tautan
- 28 tautan diperiksa dengan `curl -L` pada 2026-10-13: **tidak ada tautan mati**.
  Kode 403/202 yang muncul dari IEEE, MDPI, SAGE, ACM, dan JTIIK adalah blokir
  bot penerbit, bukan DOI rusak (sudah dicatat di md).
- 27 DOI dicek lewat `api.crossref.org`: judul dan wadah terbit cocok.
  Pengecualian: **Prakoso dkk. 2026** (`10.25126/jtiik.2026133`) DOI-nya
  terdaftar dan mengarah ke JTIIK 13(3), tetapi metadata judul/penulis di
  Crossref masih kosong; **Sahu dkk. 2025** memakai DOI arXiv yang memang tidak
  ada di Crossref, dan laman arXiv-nya terbuka normal.

### Verifikasi
- Jumlah baris tabel = **28**, jumlah tautan = **28**, sama dengan jumlah entri
  `refs.bib`.
- `proposal/main.typ` tidak disentuh; `typst compile` tetap 0 error,
  PDF **24 halaman**.

### Belum
- BAB III (Metodologi) masih placeholder.
- Daftar Gambar/Tabel masih disembunyikan sampai BAB III ada.

## 2026-10-12 — Proposal: hapus Confusion Matrix dari dasar teori (Iterasi 4.61)

### Arahan user
"dont need confusion matriks on the dasar teori".

### Yang diubah
- `proposal/main.typ` — 2.2.6 **Confusion Matrix** diganti menjadi **2.2.6
  Metrik Evaluasi**. Definisi _confusion matrix_ dan Gambar 2.9 dihapus;
  yang tersisa hanya penetapan kelas positif/negatif dan rumus _accuracy_,
  _precision_, _recall_, serta _F1-score_ (metrik yang memang dipakai).
  Daftar Isi dan Daftar Gambar disesuaikan.
- `proposal/figures/fig2-9-confusion-matrix.png` — dihapus. Gambar BAB II
  menjadi **8** (Gambar 2.1-2.8).
- `proposal/refs.bib` — **tidak berubah** (28 entri). `yang2024confusion` tetap
  dipakai karena masih menjadi baris Tabel 2.1.
- `.amp/in/proposal/make_figures.py` — fungsi `fig_confusion_matrix` dihapus.

Metrik evaluasi tetap dipertahankan karena **Rumusan Masalah 1.2 dan Tujuan 1.3
menyebut _accuracy_, _precision_, _recall_, dan _F1-score_**, jadi rumusnya harus
tetap ada di dasar teori. Penomoran 2.2.1-2.2.6 tidak berubah.

### Verifikasi
- `typst compile` 0 error, PDF **24 halaman**, 28/28 entri pustaka tampil,
  0 em dash, 0 sitasi tak ter-resolve.
- Penomoran dicek dari PDF: 2.2.1-2.2.6 berurutan (termasuk 2.2.5 yang tidak
  ikut berubah), Gambar 2.1-2.8 dan Tabel 2.1-2.2 berurutan; Daftar Isi cocok
  dengan halaman cetak aslinya (2.2.5 -> 14, 2.2.6 -> 16).
- Render PDF ke PNG dan diperiksa visual (halaman 16).

### Belum
- BAB III (Metodologi) masih placeholder.
- Daftar Gambar/Tabel masih disembunyikan sampai BAB III ada.

## 2026-10-12 — Proposal: perampingan agar tidak terkesan menjiplak (Iterasi 4.60)

### Arahan user
"dont make it look like its polished... like latar belakang we cut in half like
were not aware of rules on making a paper, rumusan masalah only 1 or 2... need
only 5 on the rujukan and dasar teori to be not that detailed so that i dont
seem like ripping off someone".

Tujuannya: proposal tampak wajar sebagai proposal skripsi yang wajar, bukan
salinan rapi proposal acuan. Karena itu cakupannya justru dipersempit.

### Yang dirampingkan

| Bagian | Sebelum | Sesudah |
|---|---|---|
| 1.1 Latar Belakang | 114 baris | **67 baris** (dipotong ~setengah) |
| 1.2 Rumusan Masalah | 3 butir | **2 butir** |
| 1.3 Tujuan | 3 butir | **2 butir** (mengikuti rumusan masalah) |
| Tabel 2.1 rujukan | 10 penelitian | **5 penelitian** (sama dengan acuan) |
| 2.2 subbagian | 11 (2.2.1-2.2.11) | **6** (2.2.1-2.2.6) |
| 2.2.4 POC-ABS | 284 baris | **118 baris** |
| 2.2.5 Data Tabular + TabR | 117 baris | **93 baris** |
| 2.2.6 Confusion Matrix | 75 baris | **48 baris** |
| Total PDF | 33 halaman | **24 halaman** |

Rumusan masalah dan tujuan digabung: butir evaluasi metrik (_accuracy_,
_precision_, _recall_, _F1-score_) dilebur ke butir kedua, bukan dijadikan
butir tersendiri.

Tabel 2.1 akhir: Rosiani 2020, Choirina 2022, Gorishniy 2024, Pasaribu 2024,
Yang 2024. Rujukan lain yang benar-benar dipakai tetap disitasi di 2.2 dan
BAB I, hanya tidak dijadikan baris tabel.

### Yang dihapus dari 2.2
- Empat blok "Keterangan:" yang memerinci tiap variabel pada POC-ABS diganti
  satu paragraf; penurunan rumusnya tetap lengkap.
- Langkah POC-ABS per blok diringkas dari daftar bertingkat rinci menjadi
  daftar lima butir.
- Paragraf pemanis pada TabR (keunggulan berulang) dan Confusion Matrix
  (penjelasan TP/TN/FP/FN satu per satu) dihapus.
- Rincian internal FAISS (IVF, PQ, OPQ, nlist, nprobe) dan penjelasan umum
  pengolahan citra sudah dihapus pada iterasi sebelumnya.

### Sumber
Empat entri `refs.bib` dihapus karena tidak lagi disitasi setelah perampingan:
`archana2024deep`, `sinulingga2023keyframe`, `huang2020embedding`,
`liu2022tvli`. Total **28 entri**, semuanya tersitasi dan tampil. `Sahu 2025`
dipindah sitasinya ke 1.1 agar tetap terpakai.

### Verifikasi
- `typst compile` 0 error, PDF **24 halaman**, 28/28 entri pustaka tampil,
  0 em dash, 0 sitasi tak ter-resolve.
- Penomoran dicek dari PDF: 2.2.1-2.2.6, Gambar 2.1-2.9, dan Tabel 2.1-2.2
  berurutan; Daftar Isi cocok dengan halaman cetak aslinya (1.2 -> 3, 2.1 -> 5,
  2.2 -> 6, 2.2.4 -> 10, 2.2.5 -> 14, 2.2.6 -> 16).
- Render PDF ke PNG dan diperiksa visual (halaman 1-5).

### Belum
- BAB III (Metodologi) masih placeholder.
- Daftar Gambar/Tabel masih disembunyikan sampai BAB III ada.

## 2026-10-12 — Proposal 2.1 Penelitian Terdahulu (Iterasi 4.58)

### Arahan user
Koreksi: 2.1 harus berupa **penelitian terdahulu** yang menonjolkan capaian
pekerjaan yang sudah selesai, baru setelah itu dasar teori; **penomoran harus
benar**; dan **gambar harus baru**, bukan versi lain dari proposal yang
melanjutkan penelitian sebelumnya.

Koreksi lanjutan (final): 2.1 **tetap berbentuk tabel rujukan seperti proposal
acuan** (bukan telaah naratif), dan tema 2.1 **dibatasi pada bagian pembelajaran
mesin** yang dipakai penelitian ini. Entri POC-ABS dan TabR dipertahankan,
lalu ditambah paper yang kita pakai sendiri.

### Bentuk akhir 2.1
Satu paragraf pengantar + **Tabel 2.1 (10 penelitian, urut tahun)** + satu
paragraf penghubung ke 2.2 Dasar Teori. Kolomnya sama dengan proposal acuan:
Judul Jurnal, Tahun, Metode, Hasil Penelitian.

| # | Penelitian | Masuk karena |
|---|---|---|
| 1 | Rosiani dkk. 2020 | metode ekstraksi fitur (POC-ABS) |
| 2 | Arik & Pfister 2021 | definisi data tabular |
| 3 | Johnson dkk. 2021 | FAISS, mesin _retrieval_ TabR |
| 4 | Choirina dkk. 2022 | preseden nasional POC-ABS/ROI terbatas |
| 5 | Liu dkk. 2022 | pembanding berbasis citra |
| 6 | Li dkk. 2022 | survei pembelajaran mendalam ekspresi mikro |
| 7 | Chicco & Jurman 2023 | MCC dan metrik klasifikasi biner |
| 8 | Gorishniy dkk. 2024 | model klasifikasi (TabR) |
| 9 | Pasaribu dkk. 2024 | bukti TabR unggul pada klasifikasi |
| 10 | Yang & Berdine 2024 | dasar confusion matrix dan metrik |

Dibanding proposal acuan (5 baris: Rosiani, Arik, Liu, Gorishniy, Pasaribu),
yang **ditambahkan** adalah Johnson 2021 (FAISS) dan Li 2022 (survei) karena
keduanya dipakai penelitian ini, plus Choirina 2022, Chicco 2023, dan Yang 2024
yang sudah dipakai sebagai pengganti sitasi bermutu rendah. Penelitian
psikologi/kesehatan mental (Gavrilescu, Zhang, Sahu, Prakoso, Larasati)
**tidak dimasukkan** ke Tabel 2.1 sesuai arahan fokus ML; entri itu tetap
dipakai di BAB I.

### Bentuk akhir 2.2 (dasar teori)
Difokuskan pada **ekspresi mikro dan _anxiety_** serta metode yang dipakai,
bukan latar belakang umum ilmu komputer. Sebelas subbagian (2.2.1-2.2.11)
diringkas menjadi **enam**:

| Sebelum | Sesudah |
|---|---|
| 2.2.1 Ekspresi Wajah + 2.2.2 Ekspresi Mikro | 2.2.1 Ekspresi Mikro Wajah |
| 2.2.3 Gangguan Kecemasan | 2.2.2 Kecemasan dan Ekspresi Mikro |
| 2.2.4 Pengolahan Citra + 2.2.5 Deteksi Wajah + 2.2.6 Dlib | 2.2.3 Facial Landmark dan Dlib |
| 2.2.7 POC-ABS | 2.2.4 POC-ABS |
| 2.2.8 Data Tabular + 2.2.9 FAISS + 2.2.10 TabR | 2.2.5 Data Tabular dan TabR |
| 2.2.11 Confusion Matrix | 2.2.6 Confusion Matrix |

Dihapus karena umum dan tidak dipakai langsung: penjelasan umum pengolahan
citra, citra statis vs bergerak, deteksi wajah pada citra bergerak, serta
rincian internal FAISS (IVF, PQ, OPQ, nlist, nprobe). Tiga entri `refs.bib`
dihapus karena tidak lagi disitasi (`archana2024deep`, `sinulingga2023keyframe`,
`huang2020embedding`); total menjadi 29 entri dan semuanya tampil.

### Yang diubah
- `proposal/main.typ` — 2.1 berbentuk tabel rujukan (10 penelitian) dan 2.2
  dirampingkan dari 11 menjadi 6 subbagian; Daftar Isi disesuaikan. Versi telaah
  naratif 2.1 disimpan di `.amp/in/proposal/bab2-2.1-naratif-backup.typ`.
- `proposal/refs.bib` — 3 entri dihapus (`archana2024deep`,
  `sinulingga2023keyframe`, `huang2020embedding`) karena tidak lagi disitasi.
  Total menjadi **29 entri** dan semuanya tampil di Daftar Pustaka.
- `proposal/figures/` — **9 gambar diganti total**. Empat di antaranya dibuat
  dari data CASME II yang diproses sendiri (dlib + POC repo ini); lima sisanya
  diagram yang digambar dengan matplotlib. Generator:
  `.amp/in/proposal/make_figures.py`.
- `report/documentation/research-papers.md` — entri **127-131** ditambah
  (Gavrilescu 2019, Zhang 2020, Sahu 2025, Prakoso 2026, Larasati 2024) plus
  penjelasan bentuk 2.1 dan 2.2.

### Angka capaian yang diverifikasi (bukan dikarang)
Rosiani 2020: 94,3% SVM / 95,6% KNN, ~0,03 detik. Choirina 2022: 81,3%,
1,45 detik/video. Liu 2022: 1,53 juta parameter. Gavrilescu 2019: 87,2%
depresi / 77,9% kecemasan / 90,2% stres, 64 detik. Zhang 2020: 85,42%,
F1 85,28%, 2.092 klip. Sahu 2025: 91,0% multikelas / 92,33% biner, 91
partisipan. Bachtiar 2021: akurasi 0,76, 6,97e-3 detik.

### Tiga klaim dibuang karena tidak dapat diverifikasi
1. "AUC 0,98 / akurasi 0,93 pada dataset _electricity_" (Pasaribu 2024) —
   dataset itu memakai _random split_ yang **bocor**; TabReD
   (arXiv:2406.19380) mencatat retrieval bisa mencapai ~100% karena kebocoran.
2. "TabNet akurasi hingga 96,99%" — tidak ada di makalahnya.
3. "Liu 2022 UAR 0,70 / UF1 0,73 / 37,9 ms" — tidak dapat diverifikasi.

### Verifikasi
- `typst compile` 0 error, PDF **33 halaman**, 29/29 entri pustaka tampil,
  0 em dash, 0 sitasi tak ter-resolve.
- Penomoran dicek dari PDF: 2.2.1-2.2.6 berurutan, Gambar 2.1-2.9 dan
  Tabel 2.1-2.2 berurutan, Daftar Isi dicocokkan dengan halaman cetak aslinya
  (2.1 -> 7, 2.2 -> 9, 2.2.2 -> 11, 2.2.3 -> 13, 2.2.4 -> 14, 2.2.5 -> 21,
  2.2.6 -> 24) dan semuanya cocok.
- Render PDF ke PNG dan diperiksa visual (halaman 9-15, 21, 23). Tabel 2.1
  terpotong rapi dengan header berulang dan tidak ada sel yang meluber.

### Belum
- BAB III (Metodologi) masih placeholder.
- Daftar Gambar/Tabel masih disembunyikan sampai BAB III ada.

## 2026-10-12 — Proposal BAB II Landasan Teori (Iterasi 4.56)

### Arahan user
Lanjut ke BAB II proposal. Basisnya BAB II proposal rujukan (Syahrul Bhudi
Ferdiansyah) yang diparafrase supaya tidak berbeda bunyinya; bagian yang sudah
diubah sebelumnya dibiarkan. Aturan sumber: **2017-2026**, dan daftar papernya
dimasukkan ke `report/documentation/research-papers.md`.

### Yang ditulis
- `proposal/main.typ` — BAB II lengkap: 2.1 Studi Literatur (Tabel 2.1,
  5 penelitian) + 2.2 Dasar Teori (2.2.1-2.2.11) dengan 9 gambar, 2 tabel,
  dan seluruh persamaan POC-ABS serta TabR.
- `proposal/refs.bib` — 12 -> **32 entri**. Ditambah 20 entri baru
  (18 internasional akses terbuka + 2 nasional SINTA 2).
- `proposal/figures/` — **9 gambar BARU**, diekstrak dari PDF asli memakai
  `pdfimages` dan diperiksa satu per satu.
- `report/documentation/research-papers.md` — bagian baru "Sitasi BAB II
  Proposal": tabel substitusi + 26 rujukan bernomor 101-126.

### Audit sumber: 7 dari 28 sitasi BAB II asli DITOLAK
Aturan proposal (internasional akses terbuka, nasional minimal SINTA 2) tidak
dipenuhi oleh 7 sitasi di BAB II asli. Diverifikasi lewat SINTA + AJOL:

| sitasi asli | masalah | pengganti |
|---|---|---|
| Sathyanarayanan 2024 | AJBR: AJOL menyatakan "no longer meets criteria" | Chicco & Jurman 2023 (BioData Mining) |
| Sejati & Mardhiyyah 2021 | JurTI = **SINTA 5** | Bachtiar & Wafi 2021 (JTIIK, **SINTA 2**) |
| Nur Cahyo dkk. 2023 | JATI = **SINTA 4** | Bachtiar & Wafi 2021 (JTIIK, **SINTA 2**) |
| Nurshabrina dkk. 2024 | Action Research Literate = **SINTA 5** | Hur dkk. 2020 (J. Neuroscience) |
| Oktamarin dkk. 2022 | Bharasumba, tidak terindeks SINTA | Javaid dkk. 2023 |
| Dewi dkk. 2025 | sumber prevalensi lebih lemah | Wahdi dkk. 2025 |
| Schwarz dkk. 2022 | workshop CEUR-WS, bukan jurnal | Johnson dkk. 2021 (IEEE TBD) |

Satu sitasi lain (Watson dkk. 2022) tidak ditolak kualitasnya, tetapi
disatukan ke `hur2020anxiety` yang sudah dipakai di BAB I untuk klaim yang
sama. Arik & Pfister 2021 (TabNet) dipertahankan karena hanya untuk definisi
data tabular, bukan klaim performa; dicatat sebagai satu-satunya entri non-OA.

### Verifikasi
- 34 DOI diselesaikan lewat `api.crossref.org`: judul, penulis pertama, dan
  wadah terbit semuanya cocok. Rentang tahun hasil verifikasi 2020-2025.
- `typst compile` 0 error; PDF **35 halaman**.
- PDF dicek: 0 sitasi tak ter-resolve, 0 em dash, 0 entri pustaka di luar
  2017-2026, Daftar Isi cocok dengan halaman aslinya.
- Render PDF ke PNG dan diperiksa visual: halaman BAB II (9-31), seluruh 9
  gambar, Tabel 2.1 dan 2.2, blok persamaan POC-ABS dan TabR, serta Daftar
  Pustaka.
- Tiga cacat tata letak ditemukan lewat render dan diperbaiki: keterangan
  gambar tampil "Gambar Gambar 2.1"; Tabel 2.1 menimpa isinya karena lebih
  tinggi dari satu halaman; dan sel "Metode" pada Tabel 2.1 meluber ke kolom
  berikutnya sampai header "Tahun" terpotong (lebar kolom disetel ulang).
- Daftar Pustaka: 32/32 entri refs.bib muncul, tidak ada yang kosong.

### Belum
- BAB III (Metodologi) masih placeholder.
- Daftar Gambar/Tabel masih disembunyikan
  (`tampilkan-daftar-gambar-tabel = false`) sampai BAB III ada.

## 2026-10-12 — Model FINAL yang bisa dipakai + reframe STATE (Iterasi 4.57)

### Arahan user
Berhenti menunjukkan angka evaluasi yang "belum selesai"; user butuh MODEL
yang bisa dipakai (bukan sekadar alat tuning), plus perintah lengkap dari awal
sampai akhir. User juga memutuskan arah tesis: bukan "tebak tingkat kecemasan
orang" (TRAIT, gagal konsisten) tapi "apakah orang ini cemas HARI INI"
(STATE — tempat gerbang within-subject signifikan BA 0,75, p 0,010).

### Yang dibangun (artefak nyata, bukan angka)
- `scripts/train_final_model.py` — BARU. Latih LitTabR di SEMUA data (bukan
  per-fold), simpan artefak ke `output/final_model/`:
  `model.ckpt` (bobot), `preprocessor.joblib` (imputer+scaler+kolom),
  `context.npz` (context FAISS), `meta.json`. train_acc 68,6% (konvergensi).
- `scripts/predict.py` — BARU. Muat artefak, prediksi tabel fitur baru:
  per baris prob + keputusan (ANXIETY TINGGI/RENDAH) + keyakinan, plus
  ringkasan per subjek. Terverifikasi end-to-end pada 3 subjek demo.
- `scripts/run_pipeline_v3.sh` — `V3_LABEL_UNIT` (default `session`) →
  stage 6 melatih pertanyaan STATE (semua sesi before+after), bukan TRAIT.
- `src/TabR.py` — ctx buffer `persistent=False` supaya checkpoint bersih;
  predict memuat bobot langsung (ctx dari context.npz).

### Perintah lengkap (awal → model siap pakai)
```bash
udisksctl mount -b /dev/nvme0n1p7   # driv mentah (sering lepas)
# pipeline penuh fresh (spotting→fitur→gerbang→training STATE→hasil)
V3_OUT_ROOT=output/apex_state V3_FEAT_TAG=poc_abs_state \
LOSO_DATASET=convat_apex_anxiety_loso_state_session \
bash scripts/run_pipeline_v3.sh --fresh
# model final siap pakai
.venv/bin/python scripts/train_final_model.py
.venv/bin/python scripts/predict.py --features <tabel.pkl> --out hasil.csv
```

### Hasil training STATE (fresh run, official TabR, 2026-10-12)
test (subjek) **54,46%**, train 89,9% / val 62,5%, AUC 0,5204,
sensitivity 0,79 / specificity 0,15. Naik dari TRAIT (48,2%) tapi masih di
bawah baseline mayoritas 57,14% dan CI memuat baseline → BELUM terbukti
lebih baik dari acak pada klasifikasi lintas-subjek. Yang tetap signifikan:
gerbang within-subject berpasangan (BA 0,75, p 0,010).

### Catatan jujur untuk tesis
Model final BERFUNGSI mekanis (muat → prediksi → keputusan). Tapi angka
lintas-subjek belum kuat; hasil yang bisa dipertahankan di sidang adalah
deteksi PERUBAHAN status dalam-subjek (0,75), bukan klasifikasi trait.
Framing BAB I perlu memihak STATE/perubahan, bukan "membedakan anxiety vs
tidak" untuk orang sembarang.

## 2026-10-11 — Kembali ke metode asli: LitTabR per-frame, LOSO bersih (Iterasi 4.56)

### Arahan user
Berhenti menambah audit; perbaiki DARI metode asli proposal (skripsinew BAB
III): POC-ABS per-frame → flatten → TabR kustom (Lightning+FAISS+freeze),
bukan jalur resmi-TabR di atas agregat subjek. Plan:
`report/plans/2026-10-11-lit-tabr-perframe-loso/`.

### Temuan kunci saat implementasi
- Metode asli TIDAK pernah dievaluasi bersih: angka ~74% notebook berasal dari
  holdout 4 subjek + split val level-frame (bocor dalam-subjek).
- Rezim terbalik: per-frame = ~19k baris train × 60 fitur (n>>d), vs agregat
  44×55 (d>>n, penyebab struktural overfit 168/168 fold-seed).
- `src/TabR.py` asli punya freeze yang TIDAK PERNAH berlaku
  (`on_validation_epoch_start` membangun ulang context tiap epoch) →
  ditambah guard `ctx_frozen`. Context sekarang buffer (ikut device model).
- Bug lingkungan: pembacaan berkas sempat flapping antar-tool (stale replay);
  diverifikasi lewat hex dump + byte count.

### Implementasi
- `scripts/run_loso_lit_tabr.py` — BARU. LOSO 56 fold per-frame:
  test=1 subjek, val=20% subjek train (disjoint), balancing subjek+context
  resep asli, imputer+scaler fit di train, LitTabR d=128 m=4 freeze@6,
  batch 128 lr 3e-4 ≤50 epoch EarlyStopping(val_loss,10). Resume per fold.
- `src/TabR.py` — guard freeze + buffer context + hapus print per-validasi.
- `src/data_module.py` — `num_workers` jadi parameter (default 0).

### Smoke (3 fold, seed 72)
✓/✓/✗ (2/3 benar); ctx ~17-19k seimbang; epoch 12 (freeze@6 jalan);
~70 detik/fold di GTX 1650 Ti → estimasi full ~70 menit. Resume DONE teruji.

### KOLAPS ditemukan dan diperbaiki (self-retrieval leak)
Run full pertama: SEMUA fold memprediksi kelas 1 dengan prob ~0,98 (frame_acc
98% atau ~1%). Akar masalah struktural, bukan tuning: saat training, frame
query ADA di dalam context FAISS → tetangga terdekat adalah dirinya sendiri
(jarak ~0) → label bocor lewat jalur retrieval, encoder tidak pernah belajar;
val subjek-disjoint yang jujur menghentikan training di epoch ~2 sebelum
encoder sempat belajar apa pun. Notebook asli tidak pernah melihat ini karena
val-nya level-frame (kebocoran yang sama membuat val_loss tampak bagus).
Fix di `src/TabR.py`: saat `self.training`, ambil m+1 tetangga lalu buang
kolom pertama (diri sendiri); saat eval ambil m (query tidak ada di context).
Smoke ulang: prob jadi jujur (0,46-0,63), frame_acc 44-73%. INI perbaikan
pertama "dari metode asli": mekanisme retrieval asli tidak sah untuk data
per-frame tanpa self-exclusion.

### Sedang berjalan
DIHENTIKAN atas perintah user — user yang menjalankan sendiri dari stage 1.
Perintah:

```bash
# full LOSO 56 fold x 1 seed (~70 menit di GTX 1650 Ti, resume otomatis)
.venv/bin/python scripts/run_loso_lit_tabr.py --tag after_s1 --seeds 1

# opsi lain:
#   --force                      ulang semua fold dari nol
#   --folds 0 1 2 --tag smoke    smoke 3 fold dulu
#   --seeds 3                    3 seed/fold (issue 04)
#   --phases before after --tag both_s1   varian STATE kedua sesi
# hasil: output/training/lit_tabr_perframe_<tag>/summary.md
```

Catatan: progress Lightning (tqdm per epoch) aktif; baris `fold NNN [✓/✗]`
dicetak tiap fold selesai. Kode final — jalankan apa adanya.

## 2026-10-09 (malam) — Audit spotting CAS(ME)² + telaah mendalam

### Riset / audit
- **Ditemukan:** logika spotting ASLI tidak ada di file .py mana pun. `preprocess-anxiety/spotting.py`
  (versi asli) hanya stub `NotImplementedError`; logika sesungguhnya ada di
  `preprocess-anxiety/process_all_datasets.ipynb`. `scripts/process_spotting_pipeline.py`
  adalah reimplementasi, jadi pembanding "kode asli" = notebook (backup
  `/home/finny/projects/Skripsi-backup-2026-08-25`).
- Diff vs backup menemukan 4 divergensi perilaku: (1) agregasi antar-ROI global→per-ROI,
  (2) acuan POC berurutan→frame-0, (3) smoothing 5%/clamp-31→tetap-7, (4) block_size 7→9.
  Definisi ROI ternyata SUDAH cocok dengan notebook (yang menyimpang adalah
  `comparasion/core/config.py`, jalur lain).

### Hasil terukur (86 video, protokol benchmark)
- Agregasi **global** (asli) F1 0,2141 @5 det/video; **per-ROI** (default lama) F1 0,1637
  @19,2 det/video. → per-ROI adalah regresi.
- Acuan **abs** (frame-0) mengalahkan **seq** (berurutan, asli): P@1 0,048 vs 0,000.
  Uji sintetis: POC buta pada gerakan sub-piksel; pada 30 fps gerakan antar-frame
  micro-expression sub-piksel, jadi acuan tetap justru perlu.
- Sinyal tetap lemah: persentil di apex 0,776, tapi puncak-apex berperingkat 0,226;
  `height=mean+std` menggugurkan 49% puncak ekspresi. Transformasi sinyal (high-pass,
  z-score, rasio, turunan) semua lebih buruk. Grid detektor plateau F1 ~0,22-0,23.
  F1 acak 0,106 vs kita 0,214.

### Implementasi
- `scripts/process_spotting_pipeline.py` — default `SPOT_SIGNAL_MODE` dikembalikan
  `roi_signals` → `global_mean` (mengembalikan agregasi asli).
- `apex/apex_smoother.py` — window tetap 7 → **3% adaptif** (min 5).
- `apex/apex_phase.py` — `find_top_k_apex(..., ranking=)` baru (`'value'` default,
  `'prominence'` untuk resep baru).
- `scripts/process_spotting_pipeline.py` — `SPOT_RANKING` (default `prominence`),
  diteruskan lewat `DetectParams.ranking`.
- `scripts/eval_spotting_casme2.py` — `detect_from_signals` ikut `SPOT_SIGNAL_MODE`.
- `scripts/audit_*.py` — BARU (lihat `report/findings/audit-spotting-casme2.md`).
- `scripts/baseline_probe_casme2.py` — `signals_for_video` diubah jadi streaming.
- `report/findings/audit-spotting-casme2.md` — BARU.

### Deep dive notebook (temuan utama)
Notebook punya TIGA generasi logika spotting. Gen 1
(`micro_expression_spotting.ipynb`) memakai **savgol window tetap 28**,
`find_peaks(prominence=0)` **tanpa height**, dan peringkat **PROMINENCE** (top 3).
Pipeline memakai gen 2/3 tapi dengan window tetap 7 dan peringkat **NILAI** —
dua hal itu regresi.

- Efek window: F1 0,2141 (tetap 7) → 0,2602 (28 / 5% clamp 31).
- Efek peringkat: 0,2602 → 0,3144 (nilai → prominence).
- Gabungan (3% adaptif + prominence): **0,3179**.
- Validasi split subjek 2-fold (pilih di satu paruh, ukur di paruh lain):
  F1 test **0,3152 / 0,3202**, kedua fold memilih konfigurasi yang sama
  (pembanding pipeline lama 0,206–0,221).

### Hasil akhir (86 video, toleransi 0, default pipeline)
| resep | P | R | F1 | det/video |
|---|---|---|---|---|
| sebelum audit (per-ROI/7/nilai) | 0,0971 | 0,5195 | 0,1637 | 19,2 |
| + agregasi global | 0,1837 | 0,2565 | 0,2141 | 5,0 |
| **+ 3% adaptif + prominence** | **0,2753** | **0,3799** | **0,3192** | 4,9 |
| `top_k=4` (terbaik) | 0,3079 | 0,3409 | 0,3236 | 4,0 |

F1 micro ikut naik (0,1250 → 0,2342 pada `top_k=4`).

### Verifikasi
- Pipeline dijalankan pada 3 video CAS(ME)² dengan default baru: 5 event/video,
  `region='global'`, fase onset/apex/offset wajar.
- Benchmark 86 video (sinyal dari cache): F1 0,1637 → 0,3192.
- Validasi split subjek 2-fold: 0,315 / 0,320.
- `py_compile` semua berkas yang diubah: ok.

### Dampak
Klip event + tabel fitur lama **tidak berlaku lagi** (parameter deteksi berubah),
perlu regenerasi sebelum training. `ApexSmoother` juga dipakai
`extract_features_poc_abs.py` (window klip pendek bergeser 7 → 5).

## 2026-10-10 — Regenerasi pipeline kecemasan + LOSO (Iterasi 4.50)

### Dijalankan
- Data mentah disalin lokal dulu (560 `.avi`, 9,5 GB) karena drive eksternal
  97% penuh dan lepas-mount sendiri.
- Pipeline penuh stage 1-7 dengan tag baru (keluaran lama tidak disentuh):
  `V3_OUT_ROOT=output/apex_fixed`, `V3_FEAT_TAG=…v3fixed`,
  `LOSO_DATASET=convat_apex_anxiety_loso_v3fixed`.
- `run_pipeline_v3.sh` ditambah override `V3_FEAT_TAG` / `V3_GATE_TAG` supaya
  bisa jalan ke direktori baru tanpa menimpa hasil lama.

### Hasil
| tahap | sebelum | sesudah |
|---|---|---|
| spotting event/sample | 12,7 | **4,8** (2.647 event) |
| fitur baris frame | 97.808 | 62.955 |
| gate within-subject BA (temporal) | 0,500 (p 0,597) | **0,639 (p 0,105)** |
| LOSO accuracy | 0,4881 | **0,4821** (baseline 0,5536) |
| LOSO AUC | 0,3974 | **0,4606** |

### Verdict
Perbaikan spotting **nyata** (F1 0,164 → 0,319; gate BA 0,50 → 0,64) tapi
**belum mengubah kesimpulan klasifikasi**: accuracy tetap di bawah baseline
mayoritas dan AUC masih < 0,5. Kegagalan klasifikasi kecemasan bukan (kebanyakan)
akibat spotting yang rusak.

### Catatan proses
- Run pertama mati di tengah (executor diganti); pipeline punya resume otomatis,
  jadi dijalankan ulang dengan `setsid` dan lanjut dari sample ke-305.
- Sanity check 60 fps sebelum regenerasi: drift TIDAK terjadi (hi/lo 4,09),
  window berdampak kecil (73 vs 71 puncak), durasi 10 → 14 frame.
- Koreksi: klaim "dominasi identitas 0,79" memakai klip event hasil spotting lama
  dan tidak bisa direproduksi (eta-kuadrat: 0,030 → 0,041).

## 2026-10-10 (lanjutan) — Representasi fitur (Iterasi 4.51)

### Temuan kunci
Label itu **per-sesi**, bukan per-orang: 18 dari 56 subjek labelnya berubah antar
sesi (17 naik→turun). Jadi ada dua pertanyaan berbeda: STATE (orang sama, sesi
beda) dan TRAIT (orang beda).

### Hasil
- **TRAIT ceiling:** tidak ada fitur yang lolos derau seleksi
  (max |AUC−0,5| 0,2432 vs null 0,2379 ± 0,0251, p = 0,385).
- **Ablasi keluarga:** sinyal ada di `rise` (kemiringan onset→apex), bukan
  magnitude. rise 55 fitur → BA 0,833; SEMUA 335 → 0,639; magnitude → 0,611.
  Menambah fitur mengencerkan (rise+arah 0,750).
- **Uji kontrol:** pada 38 subjek yang labelnya tidak berubah, `rise` tidak bisa
  membedakan before/after (BA 0,461) → bukan artefak sesi.
- **Validasi bersarang:** keluarga dipilih dari subjek latih saja → BA 0,778;
  `rise` terpilih 16/18 fold.
- **TRAIT tetap gagal:** LOSO rise acc 0,4762 / AUC 0,3978 (baseline 0,5536).

### Implementasi
- `scripts/build_temporal_features.py` — tambah `--descriptors` dan
  `--only-descriptors`.
- `experiments/features/apex/poc_abs_rise_v3fixed.pkl` — tabel 55 fitur `rise`.
- `scripts/audit_feature_representation.py`, `audit_feature_family_casme2.py`,
  `audit_rise_control.py` — BARU.
- `report/findings/audit-feature-representation.md` — BARU.

### Verifikasi
- Gerbang within-subject resmi repo: BA **0,8333, p 0,0020** (sebelumnya
  0,6389, p 0,1045).
- LOSO 56 fold × 3 seed dijalankan pada tabel `rise` dan tabel lama; keduanya
  di bawah baseline mayoritas.
- Semua skrip `py_compile`: ok.

### Implikasi
Framing yang didukung data: "POC-ABS mendeteksi perubahan status kecemasan
(before vs after ujian) pada orang yang sama", bukan "mengklasifikasi tingkat
kecemasan orang".

### FIX pipeline (Iterasi 4.52)
Stage 4 SELALU membangun tabel 5 deskriptor (335 fitur), jadi pipeline tetap
melatih representasi lemah walau tabel `rise` sudah dibuat. `run_pipeline_v3.sh`
diperbaiki:
- `V3_DESCRIPTORS` (default `rise`) + `V3_ONLY_DESCRIPTORS` (default 1) →
  stage 4 memakai `--descriptors rise --only-descriptors`; nama berkas jadi
  `..._poc_temporal_rise.pkl` supaya berkas lama tidak tertimpa.
- Stage 6 meneruskan `--drop-features`; default run_loso `_max_m$` MEMATALAKAN
  kalau tidak ada kolom yang cocok (mode only-descriptors membuang `*_max_m`).
  Sekarang dikosongkan di mode itu.
- `V3_DESCRIPTORS="peak ttp rise fall auc" V3_ONLY_DESCRIPTORS=0` memulihkan
  perilaku lama.

Dikonfirmasi lewat pipeline penuh (stage 5–7):
- gerbang `rise` (55 fitur): BA **0,8333, p 0,0050**
  (**SUPERSEDED** → run bersih memberi **0,7500, p 0,0100**; lihat "RUN ULANG
  BERSIH" di bawah. Angka lama dari data `before` yang tidak lengkap.)
- LOSO `rise`: acc 0,4762, AUC 0,3978 (baseline mayoritas 0,5536)
- baseline logistic 0,5357 (p 0,4179), GBDT 0,4464 (p 0,8557) — dua-duanya
  tidak signifikan, jadi kegagalan TRAIT bukan kekhususan TabR.
- Hasil lama tidak tertimpa (tag gerbang & dataset dipisah).

### RUN ULANG BERSIH (Iterasi 4.55) — angka otoritatif

Pipeline penuh dari nol (`output/apex_run2`, 560/560 sample).

**Run sebelumnya TIDAK lengkap**: pernah terputus lalu di-resume, dan logika
resume melewati sample yang direktori output-nya sudah ada → sample yang tertulis
separuh (paruh `before`) terlewat.

| | run lama | **run bersih** |
|---|---|---|
| event | 2.647 | **2.667** |
| baris `before` | 35.019 | **35.477** |
| baris `after` | 27.936 | **27.936** (sama) |

LOSO hanya memakai `after` → tidak berubah. Gerbang memakai kedua sesi → berubah:

| gerbang `rise` | lama | **bersih** |
|---|---|---|
| BA | 0,8333 | **0,7500** |
| p | 0,0050 | **0,0100** |

Angka otoritatif: gerbang `rise` **BA 0,7500 (p 0,0100)**; per-frame 0,6389
(p 0,0647); LOSO test **47,62%** (baseline 55,36%), MCC −0,1037, AUC 0,3978;
baseline logistic 53,57% (p 0,4179), GBDT 44,64% (p 0,8557);
**overfit 168/168 fold-seed**.

### Train / Val / Test (persen) + fix bug seed (Iterasi 4.53)

`collect_loso_results.py` sekarang menampilkan train/val/test dari `summary.json`
tiap fold-seed, dalam persen:

| run | train | val | test |
|---|---|---|---|
| roi25_reg | 82,82% | 61,50% | 48,80% |
| v3fixed | 87,80% | 58,33% | 48,21% |
| v3fixed_rise | 72,06% | 49,89% | 47,62% |

Pola seragam: train jauh di atas val (hafalan), val ~50%, test ~48% — di bawah
baseline mayoritas 55,36%. **48,8% fold-seed berhenti di epoch 0** (epoch terbaik
median 1), jadi model praktis tidak terlatih; summary.md kini memperingatkan ini
otomatis. Angka LOSO mengukur model yang tidak belajar, bukan batas fitur.

Bug yang ditemukan sambil itu: jumlah seed dihitung HANYA dari fold pertama, jadi
`roi25_reg` (fold_000 parsial, 1 seed) diam-diam cuma memakai seed 0. Sudah
diperbaiki (gabungan semua fold); hasilnya kembali 0,4884 ± 0,0866.

## 2026-10-06

### Riset
- Baca handoff thread `T-01a10ee2-9111-74db-ac17-cc3bbe810c30` (LOSO run results):
  `d1`/`d2` invalid (369 fitur, hasil identik bit-per-bit), `d3` terburuk
  (42,9%), `reg` 62,5% tapi CI memuat baseline 55,4%.
- Web search: fitur mana yang literatur rekomendasikan untuk kecemasan dari
  wajah, dan apa yang benar-benar bekerja pada N kecil.
- Temuan kunci: AnxietyFaceTrack (TAFFC 2026) → 3D landmark 88–91%, head pose
  85–89,7%; StressGAT (LOSO 88,62%, 58 peserta) → mekanisme Differential AU =
  normalkan terhadap baseline netral tiap orang.
- Keputusan: tambah keluarga fitur geometri/head pose dari landmark yang sudah
  dihitung, bukan tuning TabR lagi.

### Implementasi
- `features_extraction/geometry.py` — BARU. 15 fitur statis + 6 kecepatan.
- `comparasion/core/roi.py` — `extract_landmarks`, `extract_rois_from_landmarks`,
  `extract_rois` jadi pembungkus tipis.
- `scripts/extract_features_poc_abs.py` — `--with-geometry`, tiga tabel dari
  satu pass (POC saja / geometri saja / gabungan).
- `scripts/run_loso.py` — `--quiet`.
- `scripts/run_pipeline_v3.sh` — stage 2/3/4/5/6/7 memakai tabel gabungan;
  gerbang 3 keluarga fitur; config default dan nama dataset LOSO diperbaiki.

### Bug yang ditemukan dan diperbaiki (semua sebelum diserahkan)
1. `_extract_region` memakai `np.ndarray` → indeks slice harus `int()`.
   Tanpa itu `TypeError`.
2. `geo_pitch` duduk di ±179° (model +Y naik vs citra +Y turun) → melompat 360°
   saat melewati titik wrap, merusak fitur kecepatan. Diperbaiki dengan
   menyatakan rotasi relatif acuan frontal `diag(1,-1,-1)`.
3. `_head_pose_proxy` semula mengembalikan rasio, bukan derajat → frame yang
   jatuh ke cadangan akan melompat skala. Disamakan ke derajat.

### Verifikasi yang dijalankan
- Parse AST 4 berkas + `bash -n` pipeline: ok.
- `--help` ekstraktor dan `run_loso`: ok. `--dry-run` pipeline: ok.
- ROI identik bit-per-bit (6 frame nyata, 5 ROI) antara jalur lama dan baru.
- Geometri pada 400 frame nyata: semua finite, sudut jauh dari titik wrap.
- Ekstraksi `--limit 5 --with-geometry`: POC 48 kolom tanpa `geo_*`; geometri 34
  kolom (13 identitas + 21 `geo_*`); gabungan 69 kolom; 0 NaN; 0 kolom konstan.
- `--quiet` 1 fold/1 seed: 460 baris/26.617 byte → 22 baris/1.631 byte;
  `DONE.json`/`report.json`/split/train.log tertulis.
- Shim `tqdm`: `import tqdm.auto` dan `tqdm.std` tetap jalan.

### Dokumentasi
- `report/findings/geometri-headpose.md` (dasar riset + batas).
- `report/plans/2026-10-06-geometri-headpose-fusion/plan.md` (rencana + bukti).
- `report/documentation/changes-log.md` Iterasi 4.25.
- `HANDOFF.md` (berkas ini pasangannya).

### HASIL (pipeline penuh dijalankan user, 2026-10-06 21:23–22:03)
- Kelengkapan: 56/56 fold DONE, 0 FAILED, 168 report.json, ekstraksi 0 error.
- Gerbang: POC statis 0/35 (acc 0,4444); **geometri 0/21 (acc 0,4444, p 0,7512)**;
  gabungan 0/206 (acc 0,6111, p 0,2040).
- Kunci: acc gabungan 0,6111 IDENTIK dengan POC temporal saja → geometri
  menyumbang NOL.
- LOSO gabungan: acc 0,5595 ± 0,0103, seed-ensemble 0,4821,
  CI 0,3567–0,6099 (memuat baseline 0,5536), MCC +0,1007.
- Pembanding: logistic 0,4464, gbdt 0,3571 (di bawah acak).
- vs run terbaik `reg` (POC saja 237 fitur): 0,6250 / MCC +0,2272 → menambah
  geometri MEMPERBURUK (fitur 237 → 385, d/n 5,4 → 8,8).
- **Bug saya ditemukan saat memeriksa hasil:** ambiguitas planar solvePnP pada
  roll → 1.472 baris (1,46%) |roll| > 170 di 5 subjek, head_motion sampai
  359,86°/frame. Diperbaiki dengan `normalize_roll()` (lipat ke (-90,90]);
  terverifikasi roll maks |8,64| pada 600 frame, head_motion maks 8,14.
  Verifikasi lama saya (400 frame, beberapa klip) terlalu sempit.
- Angka run belum final karena roll masih rusak saat training; kesimpulan tidak
  berubah (17 dari 21 fitur bersih sudah punya kesempatan, tidak lolos FDR).
- Nuansa: p mentah terkecil POC 0,0075 dan geometri 0,0352, dua-duanya bersih di
  kontrol, tapi tidak lolos FDR (n=18) → "tidak terdeteksi", bukan "terbukti nol".

### BATCH A: 6 bug diperbaiki + diverifikasi (2026-10-06, setelah run penuh)
- **#1 (membatalkan kesimpulan)**: `VarianceThreshold(1e-4)` jalan pada nilai
  MENTAH sebelum scaler → filter SKALA, bukan filter "fitur statis". Terukur:
  geometri 26/42 lolos (385 kolom) → setelah scale-dulu jadi **42/42 (402)**.
  16 kolom geometri tidak pernah masuk model, termasuk `geo_lip_corner_drop`
  (p gerbang 0,0352) dan `geo_mouth_open` (rekomendasi paper BINUS).
  Jadi "geometri menyumbang nol" **belum teruji**.
- **#2**: roll solvePnP ambigu → `normalize_roll()`; tabel tersimpan masih
  rusak → butuh re-ekstraksi.
- **#3**: permutasi gerbang global → berpasangan. p: POC 0,7761→0,8010;
  geometri 0,7512→0,7363; gabungan 0,2040→0,1542.
- **#4**: ambang Youden bisa `inf` (1/56 fold) → `inf ± nan`; sekarang
  0,5250 ± 0,0322.
- **#5**: heading "Level subject" untuk tabel frame; judul gerbang hardcoded.
- **#6**: `--force` pipeline tidak diteruskan ke stage 6 → 56 fold dilewati
  diam-diam. Sudah diteruskan (`FORCE_ARG`).
- Berkas: `run_loso.py`, `run_loso_baseline.py`, `within_subject_test.py`,
  `collect_loso_results.py`, `run_pipeline_v3.sh`.
- Verifikasi pada artefak nyata tanpa training. Re-run BELUM.

### Belum
- Re-run dengan keenam perbaikan: `./scripts/run_pipeline_v3.sh --force`
  (~1 jam). `--force` wajib.
- Baca `output/training/within_subject_v3_geo/summary.md` sebagai wasit.

## 2026-10-09

### Tujuan
Fokus A: validasi tahap spotting pakai CAS(ME)² (ground truth onset/apex/offset).
Sedikit fokus B: metrik dipisah macro vs micro.

### Ekspor CAS(ME)²
- `7z` build ini TIDAK punya codec RAR; `unrar` tidak terpasang (butuh sudo).
- Dipakai `libarchive-c` (pip ke venv, tanpa sudo) → baca RAR v4.
- `rawvideo.rar` (6,95 GB, 97 avi) → `/home/finny/datasets/casme2/rawvideo/`.
  Drive 97% penuh (1,6 GB bebas), jadi diekspor ke `/home` (55 GB bebas).
- Konvensi dicatat: dataset mentah di `~/datasets/<nama>/` (seperti `anxiety_raw`).

### Pemetaan ground truth
- `code_final.xlsx` punya 356 ekspresi; nama ekspresi (`anger1_2`) ≠ nama file
  (`15_0401girlcrashing.avi`). Dipetakan lewat sheet "naming rule 1/2".
- Hasil: 308 ekspresi beranotasi lengkap (57 micro, 251 macro), 86 video,
  22 subjek. Semua offset GT < jumlah frame video → pemetaan benar.

### Kode
- `scripts/process_spotting_pipeline.py` — blok eksekusi level-modul dipindah ke
  `main()`. Sekarang aman diimpor (dulu import = tulis metadata.xlsx/klip).
  Pipeline tetap jalan: diuji, `main()` dipanggil, validasi path tetap.
- `scripts/eval_spotting_casme2.py` — BARU. Spotting dijalankan SEKALI per video,
  lalu dicocokkan ulang per toleransi (dulu sempat jalan ulang per toleransi).

### Verifikasi
- `load_ground_truth`: 308 ekspresi, 0 offset di luar video.
- Smoke test 2 video end-to-end: recall 1,0000, precision 0,1515, F1 0,2632,
  5 TP / 28 FP / 0 FN, error apex median 6 frame. Detektor sensitif, tidak spesifik.
- `py_compile` OK untuk kedua berkas.

### Belum
- Jalankan penuh: `.venv/bin/python scripts/eval_spotting_casme2.py` (86 video, ±1 jam).
- Angka final precision/recall/F1 macro vs micro.

## 2026-10-09 (lanjutan) — OOM fix

### Gejala
Run penuh `eval_spotting_casme2.py` menghentikan mesin. Bukan crash Python,
bukan reboot: OOM killer membunuh proses (09:29:16 dan 09:32:07), swap 5 GB,
load average 27. Discord + Chrome ikut memicu.

### Akar masalah
`load_video_frames` memuat semua frame jadi list; `build_roi_signals` menyalin
lagi ke grayscale. Video CAS(ME)² 4370 frame = ~5,3 GB per worker; 4 worker =
~21 GB vs RAM 15 GiB. Video anxiety pendek (median 436 frame) tak pernah kena.

### Perbaikan
- `process_spotting_pipeline.py`: `iter_video_frames()` generator +
  `count_video_frames()`; `build_roi_signals` menerima generator & tak lagi
  menyalin semua frame ke grayscale.
- `eval_spotting_casme2.py`: `detect_in_video` memakai streaming; `+--workers`
  (default 3).

### Verifikasi
- Sinyal streaming vs list: identik, maxdiff 0,0 (5 ROI, 1075 frame).
- Smoke test 2 video: `matched.csv` IDENTIK dengan sebelum fix → murni memori.
- Puncak RSS video 4370 frame: 0,27 GB (dari ~5,3 GB), ~20x lebih kecil.

### Belum
- Jalankan penuh: `.venv/bin/python scripts/eval_spotting_casme2.py`

## 2026-10-09 (lanjutan) — Proposal BAB I

### Arahan
Hanya BAB I (1.1-1.5), jangan BAB II-III. Sitasi maksimum 2017-2026.
Tanpa em dash. Bahasa lebih sederhana tapi tetap akademik.

### Masalah
3 sitasi inti naskah lama terbit pra-2017: Ekman 1992 (emosi dasar),
Robinson 2013 (fear vs anxiety), Yan 2014 (CASME II). Dipakai di kalimat
penting, jadi butuh pengganti, bukan sekadar dihapus.

### Pengganti (terverifikasi, akses terbuka)
- `hur2020anxiety` (J. Neuroscience 40(41):7949-7964, 2020) -> fear vs anxiety.
- `li2022mesurvey` (IEEE TAFFC 13(4):2028-2046, 2022) -> kelas cadangan
  dataset micro-expression.
- Daftar emosi dasar -> pakai `oh2018survey` yang sudah ada.
- Sitasi CASME II dialihkan ke `li2022mesurvey`.

### Diubah
- `proposal/main.typ`: 1.1 ditulis ulang; 1.2-1.5 dirapikan.
- `proposal/refs.bib`: hapus 3 entri pra-2017, tambah 2 entri baru, header
  mencatat aturan rentang tahun.

### Verifikasi
- `typst compile` sukses, 12 halaman, 0 error.
- PDF: 0 em dash, 0 sitasi tak ter-resolve, semua tahun pustaka 2018-2026.
- Screenshot halaman 1 dan 3 diperiksa.

## 2026-10-09 (lanjutan) — Hasil benchmark CAS(ME)²

### Hasil run penuh (86 video, 308 GT, 1647 deteksi)
| metrik | tol 0 | tol 5 |
|---|---|---|
| precision | 0,0971 | 0,1044 |
| recall | 0,5195 | 0,5584 |
| F1 | 0,1637 | 0,1760 |
| recall macro | 0,5498 | 0,5777 |
| recall micro | 0,3860 | 0,4737 |
| error apex median | 7 frame | 7 frame |

### Temuan
- Detektor = peak-finder beranggaran tetap: 19,2 deteksi/video (maks 25 =
  5 ROI x top_k 5) vs GT median 2. Precision rendah itu aritmetika, bukan
  kesalahan lokasi (error apex cuma 7 frame).
- Recall micro 0,386: menemukan ~4 dari 10 micro-expression. Angka
  ber-ground-truth pertama untuk klaim ini.
- Tidak sebanding dengan 94-96% klaim lama (itu klasifikasi, bukan deteksi).

### Fix artefak
- `false_positives.csv` sebelumnya tanpa kolom `video` -> tidak bisa
  dianalisis. Sudah diperbaiki; smoke test memastikan deteksi tidak berubah.

## 2026-10-09 (lanjutan) — Fix: parameter detektor bisa diuji + cache sinyal

### Masalah
Detektor mengeluarkan ~19 deteksi/video vs GT ~2; plafon 25 = 5 ROI x top_k 5.
Parameter pemilihan event tidak bisa diuji tanpa mengubah pipeline utama.

### Perbaikan
- `process_spotting_pipeline.py`: `DetectParams` + `resolve_detect_params()`.
  `detect_events_per_roi()` / `detect_events()` menerima `params` opsional.
  `params=None` = perilaku lama persis. **Default pipeline tidak diubah.**
- `eval_spotting_casme2.py`: sinyal dihitung sekali + di-cache (npz), grid
  parameter hanya mengulang deteksi. `+--top-k/--prom-rel/--thresh` (grid),
  `+--signal-cache/--no-cache`.

### Temuan
- `prom_rel` TIDAK binding: 0,04 -> 0,20 mengurangi puncak mentah (mulut 32->27)
  tapi top-5 tetap sama -> hasil identik. Yang mengikat: `top_k` + mode ambang.
- Indikasi awal (2 video): top_k=1 F1 0,4615 vs top_k=5 0,2632.

### Verifikasi
- Kesetaraan jalur lama: no-param == explicit-globals (14 event identik).
- Kesetaraan end-to-end: default params mereproduksi smoke test lama persis.
- Cache: 2,4 detik vs ~3 menit.
- Bug diperbaiki: `np.savez_compressed` menambah `.npz` sendiri saat nama tmp
  tidak berakhiran `.npz` -> ditulis lewat file object.

### Belum
- Sweep penuh (user jalankan): `--top-k 1 2 3 4 5 --thresh meanstd mad`

## 2026-10-09 (lanjutan) — Sweep + diagnosis spotting CAS(ME)²

### Hasil sweep (86 video, 308 GT, 10 kombinasi)
F1 turun monoton terhadap top_k; SEMUA buruk:
  top_k=1 meanstd: P 0,1838 R 0,2208 **F1 0,2006** (terbaik)
  top_k=2: F1 0,1931 | top_k=3: 0,1789 | top_k=4: 0,1632 | top_k=5: 0,1637
Catatan: indikasi 2-video sebelumnya (F1 0,4615) MENYESATKAN.

### Diagnosis (5 uji)
1. Bukan plafon top_k: recall plafon (any-overlap) hanya 0,2370 (73/308).
   Jarak apex GT->deteksi median 131 frame. Deteksi di tempat salah.
2. Drift ada (93% video naik, median +0,199) TAPI detrend justru memperburuk
   (0,2403 -> 0,2078). Bukan penyebab.
3. **SINYAL BAGUS**: persentil sinyal di apex GT = 0,988 (acak 0,50);
   92,9% ekspresi di 10% teratas. POC-ABS memuncak di ekspresi.
4. Rantai filter: tanpa filter cov 1,000 (2774 det/video); height 0,987 (736);
   +prom 0,987 (623); **+top_k=5 0,487 (25)**; top_k=1 0,221 (5).
   -> `top_k` yang membunuh.
5. Tidak ada skor puncak yang memisahkan: puncak ekspresi median peringkat
   ~0,17; nilai mentah/prominence lokal/z lokal semuanya serupa.

### Kesimpulan
Spotting BELUM terbukti jalan (F1 0,20). Tapi kegagalannya di PEMILIHAN
PUNCAK, bukan di sinyal. ~125 puncak/ROI, puncak ekspresi tidak terpisah
jelas -> anggaran top_k apa pun mengorbankan precision atau recall.

### Arah berikutnya (belum dikerjakan)
Butuh penilai puncak (bukan geser top_k/threshold): fitur lokal per puncak
(rise/fall, durasi, koherensi antar-ROI).

### Evidence
logs/{diag_spotting,diag2,detrend,sig_test,filter_test,rank_test}.log

## 2026-10-09 (lanjutan) — 7 arah perbaikan spotting, semuanya mentok

### Diuji (semua pakai cache sinyal; baseline F1: top_k=5 = 0,1637, top_k=1 = 0,2006)
1. Skor puncak handcrafted (7 skor, anggaran 3,6/video): F1 terbaik **0,1748**
   (width). val (sekarang) 0,1319.
2. Agregasi mean/max/count x acuan abs/seq (4 video): variasi antar-video
   (0,065-0,274) > beda antar-konfigurasi. Tidak ada pemenang.
3. Perataan 4 window x 3 ambang (86 video): menaikkan ambang MEMPERBURUK
   peringkat ekspresi (0,044 -> 0,219) -> ekspresi bukan puncak terkuat.
4. Perbesar ROI 3x: persentil apex turun 0,999 -> 0,977, puncak naik 435 -> 472.
5. Blink (1.185 anotasi): hanya 5,6% FP. Bukan penyebab.
6. Detrend + artefak awal: detrend memperburuk (0,2403 -> 0,2078).
7. **Pembelajar** (31 fitur, GroupKFold per video, 53.600 kandidat):
   logistic AUC 0,6776, gbdt AUC 0,6706. **F1 terbaik 0,2047.**

### Kesimpulan
F1 ~0,20 = PLAFON sinyal POC-ABS magnitudo + pemilihan puncak, handcrafted
maupun pembelajaran. Sebab: ~700 puncak gerak/video vs 3,6 ekspresi, dan
puncak ekspresi tidak lebih kuat dari gerakan lain.

### Sudah dieliminasi (jangan diulang)
top_k, threshold, prominence, perataan, agregasi, acuan abs/seq, perbesaran
ROI, drift, artefak awal, blink.

### Skrip baru
`scripts/rank_peak_casme2.py`, `probe_signal_casme2.py`,
`probe_smoothing_casme2.py`, `probe_learned_rank_casme2.py`

## 2026-10-09 (lanjutan) — Fitur arah+koherensi: F1 0,20 -> 0,27

### Hipotesis
Skor/pembelajar atas MAGNITUDO saja mentok F1 ~0,20. Tapi pipeline menghitung
sinyal lain per ROI: arah (mean_x, mean_y) + koherensi (angle_R). Mungkin itu
yang membedakan ekspresi emosional dari gerakan lain.

### Hasil (15 video, 8.580 kandidat, 747 positif)
- Fitur kaya (61 fitur: 6 sinyal x 5 ROI x {nilai, z-lokal} + sup):
  **AUC 0,7183** (pembanding 0,6706) | **F1 terbaik 0,2702** (pembanding 0,2047)
- F1 terbaik pada 80 kandidat/video (GT hanya 3,6/video).
- Pada anggaran setara GT (3,6/video): F1 0,0699.

### Bacaan
Ada informasi pembeda di ARAH + KOHERENSI. Arah pengembangan benar. Tapi 0,27
belum "bagus" (literatur 0,4-0,7 dgn jaringan spasiotemporal dalam).

### Skrip baru
`scripts/probe_rich_features_casme2.py`

### Langkah berikut (belum dikerjakan)
1. Jalankan fitur kaya pada seluruh 86 video (angka final).
2. Analisis kepentingan fitur (mana yang menyumbang).
3. Klasifikasi JENDELA (sliding window) menggantikan per-puncak.

## 2026-10-09 (lanjutan) — Klasifikasi jendela: verdict negatif, bersih

### Tugas
(1) fitur kaya di SEMUA 86 video, (3) klasifikasi jendela (bukan per-puncak).

### Hasil (86 video, GroupKFold per video, ambang dipilih di data latih)
| metode | AUC | F1 |
|---|---|---|
| pipeline top_k=5 | — | 0,1637 |
| pipeline top_k=1 | — | 0,2006 |
| puncak + fitur kaya | 0,6686 | 0,2156 |
| jendela w=64 | 0,6492 | 0,3715 |
| jendela w=96 | 0,6442 | 0,4281 |
| jendela w=128 | 0,6296 | 0,4068 |

### Tapi F1 0,43 itu ARTEFAK (window=96)
- durasi event deteksi median 209 frame vs GT 29 frame (7x terlalu panjang)
- IoU >= 0,5: F1 turun jadi 0,0061
- lokalisasi: pusat event meleset median 172 frame; <=10 frame hanya 5,5%

### Verdict
Spotting TIDAK bekerja di CAS(ME)². Bukan sinyal (persentil 0,988), bukan
ambang, bukan ukuran jendela. Metode tidak melokalisasi ekspresi cukup tepat.

### Tiga jebakan metodologi ditutup
1. Subset kecil menyesatkan (w=16: AUC 0,71 @20 video vs 0,60 @86).
2. Ambang tidak boleh dipilih dari data uji -> mode `inner` (default).
   posthoc 0,4453 vs inner 0,4281.
3. Pencocokan "beririsan" terlalu longgar -> ditambah cek IoU>=0,5 + durasi +
   lokalisasi.

### Skrip baru
`scripts/rich_signals_casme2.py`, `scripts/window_spot_casme2.py`,
`scripts/rank_rich_casme2.py`

### Output disimpan
output/training/{spotting_casme2, rank_rich_full, window_honest_w64,
window_honest_w96, casme2_rich_signals}

## 2026-10-14 (dini hari) — A/B motion-comp + MDMD SELESAI, hasil negatif

### Konteks
Melanjutkan handoff thread `T-01a12b83-4b08-779c-b913-fa0826c3a0c7`: cek apakah
hasil run terbaru untuk konfigurasi magnitude/spotting sudah tercatat. Ternyata
`HANDOFF.md`/`PROGRESS.md` masih menulis motion-comp+MDMD sebagai "menunggu A/B",
padahal run penuh sudah selesai.

### Run yang diverifikasi
```bash
V3_PRESPLIT=1 V3_SPOT_MOTION_COMP=1 V3_SPOT_SIGNAL=mdmd \
V3_EXTRA_CONFIGS="experiments/configs/tabr_loso_roi25_reg.toml" \
  ./scripts/run_pipeline_v3.sh --fresh
```

Log utama: `logs/pipeline_v3_20261014_000216.log`.

Bukti protokol fold-first:
- Stage 0: 44 orang train pool, 12 orang holdout.
- Stage 1 spotting train-pool: `INCLUDE_PERSONS: 440 video diproses, 120
  dilewati`; metadata 2194 baris.
- Stage 8 spotting holdout: `INCLUDE_PERSONS: 120 video diproses, 440 dilewati`.
- Pipeline selesai 8/8 stage.

### Hasil LOSO-44
| config | accuracy | BA | MCC | AUC | bacaan |
|---|---:|---:|---:|---:|---|
| compact | 0,4545 ± 0,0227 | 0,4632 | −0,0771 | 0,4814 | di bawah baseline 0,5682 |
| roi25_reg | **0,4773 ± 0,0682** | **0,4958** | **−0,0087** | **0,5151** | terbaik, tetap setara acak |

### Hasil holdout-12
| config | accuracy | BA | MCC | AUC | bacaan |
|---|---:|---:|---:|---:|---|
| compact | 0,3333 ± 0,0833 | 0,4000 | −0,4430 | 0,4667 | gagal |
| roi25_reg | **0,4444 ± 0,0962** | **0,5048** | **−0,0014** | **0,4762** | terbaik, tetap di bawah baseline 0,5833 |

Gate temporal within-subject (`output/training/within_subject_v3_geo_temporal/summary.md`):
BA 0,5357, p=0,4428; fitur signifikan grup berubah 0/55, kontrol 4/55. Jadi
keluarga fitur ini masih tidak membawa sinyal kecemasan yang stabil.

### Keputusan magnitude / spotting
1. **Jangan jadikan `mdmd` atau `combo` default.** Keduanya mengubah spotting,
   tetapi tidak memperbaiki generalisasi subject-independent pada data anxiety.
2. **Default tetap `mean_m`.** Alasan: masih kandidat paling stabil dari deep
   dive magnitude CAS(ME)² (`mean_m` F1 0,3192; combo hanya unggul kecil di
   CAS(ME)² lalu gagal transfer; motion-comp+MDMD gagal di anxiety holdout).
3. `V3_SPOT_CUTOFF=0.5` masih boleh dicoba sebagai A/B sekunder untuk batas
   event lebih rapat, tapi ini bukan tuas utama karena masalahnya SNR gerakan
   latar, bukan sekadar formula magnitude.
4. Sisa jalan yang defensible: tambah N lewat `datatest` (26 orang, 654 video,
   skor kontinu, butuh join nama+timestamp + izin dosen) atau tulis hasil
   negatif: POC-ABS spotting tidak memberi sinyal kecemasan yang robust secara
   subject-independent pada dataset lapangan ini.

### Dokumentasi yang diperbaiki
`HANDOFF.md` diperbarui dari status "menunggu A/B" menjadi hasil negatif dengan
angka run 2026-10-14 dan keputusan konfigurasi magnitude.

## 2026-10-14 — Plan: paper-backed spotting configs untuk mengejar >60%

### Arahan user
Supervisor ingin hasil di atas 60%, jadi tidak boleh berhenti pada tulisan
negatif. Fokus berikutnya: breakdown spotting, cari konfigurasi dari paper/GitHub
(SpotFormer/SW-MRO, temporal state transition, Li et al. feature difference peak
detection, MDMD/MEGC baseline), lalu coba secara defensible.

### Temuan cepat dari FINAL.pdf
FINAL.pdf masih memakai klaim/metode lama:
- POC-ABS block size 7×7.
- ROI: mata-alis kanan, mata-alis kiri, mulut.
- Pengujian menghasilkan accuracy 58%.
Ini perlu ditutup dengan pipeline/evaluasi baru yang lebih kuat, bukan sekadar
menulis hasil negatif.

### Literatur yang dikunci
1. **SpotFormer / CSW-MRO (2024/2026)** — sliding-window multi-temporal-resolution
   optical flow. Window terbaik 17 frame pada 30 fps; CAS(ME)² overall F1 0,4841
   dengan model SpotFormer terlatih. Untuk repo ini: bisa dipakai sebagai ide
   fitur `swmro_inspired`, tapi bukan diklaim sebagai reproduksi SpotFormer kalau
   tidak melatih/memakai modelnya.
2. **ME-TST / temporal state transition (2024)** — video-level regression + joint
   spotting/recognition. Code ada, tetapi ini deep training, bukan config kecil
   drop-in untuk pipeline POC-ABS sekarang.
3. **Li et al. feature-difference + peak detection** — training-free. Formula
   threshold: `T = Cmean + tau*(Cmax-Cmean)`, min peak distance `k/2`; false
   positive dari blink/eye movement adalah masalah utama yang harus dilaporkan.
4. **MDMD MEGC2020 baseline** — config sumber: 6×6 blocks, 4 direction bins,
   k=12 micro / 39 macro untuk CAS(ME)², p=0,01, duration filter, IoU 0,5.

### Plan yang dibuat
`report/plans/2026-10-14-paper-spotting-configs/`:
- `CONTEXT.md`
- `plan.md`
- 8 issue: literature map, evaluator cache CAS(ME)², FD peak spotter,
  SW-MRO-inspired spotter, MDMD proper sweep, boundary calibration, promote winner
  to pipeline, FINAL.pdf coverage.

### Keputusan teknis
Jalur deterministik:
1. CAS(ME)² dulu, cache-based, agar cepat dan punya GT onset/apex/offset.
2. Pilih config di split subjek / train saja, bukan anxiety holdout.
3. Baru wire pemenang ke `run_pipeline_v3.sh` sebagai env-gated option.
4. Full fold-first anxiety run hanya setelah ada pemenang spotting yang masuk akal.

### Belum
- Belum implement evaluator/sweep.
- Belum menjalankan pipeline anxiety penuh.

## 2026-10-14 — Plan revision setelah critique: OF-FD naik prioritas, MDMD turun

### Koreksi arah
Critique benar: MDMD MEGC2020 terlalu lemah untuk jadi kandidat utama
(CAS(ME)² overall F1 0,0376; micro F1 0,0082). Itu floor/sanity check, bukan
baseline yang membantu keputusan. Plan direvisi agar tidak membuang waktu ke
MDMD sebelum kandidat yang lebih informatif.

### Perubahan plan
`report/plans/2026-10-14-paper-spotting-configs/` diperbarui:
- Success target dibuat eksplisit: **subject-level holdout accuracy ≥60%** untuk
  anxiety fold-first; BA/MCC/AUC tetap guardrail.
- Evaluator wajib melaporkan frame-based accuracy `F` dari benchmark paper
  (lebih kecil lebih baik): deviasi center + panjang interval pada TP. Ini lebih
  dekat ke kualitas klip untuk recognition daripada F1 longgar saja.
- Tambah precision-oriented diagnostics: precision at fixed recall / recall at
  fixed precision, FP/video, deteksi/video. Untuk anxiety recognition, false
  positives bisa lebih merusak daripada missed events.
- OF-FD / fixed-ROI optical-flow feature-difference dinaikkan jadi kandidat
  utama training-free modern: nose/face alignment, 14/13 ROI, optical-flow curve,
  denoise, peak/NMS.
- `SW-MRO-inspired` diganti nama menjadi `multi_window_temporal`: tidak boleh
  mengklaim SpotFormer tanpa trained Transformer. Anchor window training-free =
  L=35 dari benchmark paper; window 17 hanya diagnostic.
- MDMD dipindah ke issue low sebagai floor check.

### File plan yang diubah
- `CONTEXT.md`
- `plan.md`
- `issues/02-critical-cache-evaluator.md`
- `issues/03-high-fd-peak-spotter.md`
- `issues/04-high-multi-window-temporal-feature.md`
- `issues/05-high-of-fd-spotter.md`
- `issues/09-low-mdmd-floor-check.md`

### Belum
Belum implement evaluator. Langkah berikutnya tetap: common CAS(ME)² evaluator
cache-based dulu, lalu FD + OF-FD + multi-window sweep.

## 2026-10-14 — Paper-backed spotting sweep built + Hanning window fixed

### Perintah user
"do all 4 and fix hanning window" — jalankan empat item revisi: evaluator
CAS(ME)² cache-based, Li/Moilanen FD peak, OF-FD/fixed-ROI proxy, multi-window
temporal feature, plus koreksi Hanning di POC.

### Perubahan kode
- `features_extraction/poc.py`: Hanning sekarang benar-benar 2D:
  `np.outer(np.hanning(blockSize), np.hanning(blockSize))`, lalu diaplikasikan
  element-wise (`block * window`) sebelum `fft2`. Sebelumnya `np.dot(hann.T,
  hann)` menjadi skalar dan `np.dot(block, window)` bukan windowing 2D.
- `scripts/eval_paper_spotting_configs.py`: evaluator baru berbasis cache
  `output/training/spotting_casme2_signals`, tanpa menghitung ulang dlib/POC dan
  tanpa menyentuh data anxiety.
- Kandidat yang disapu:
  - `current_mean_m` baseline produksi.
  - `fd_peak`: k 8/12/17, tau 0,10/0,20/0,30/0,45, top ROI mean/2.
  - `multi_window_temporal`: L 17/25/35/45, tau 0,10/0,20/0,30; L=35 tetap
    anchor benchmark, L=17 hanya diagnostic.
  - `of_fd_proxy`: proxy OF-FD berbasis kurva ROI POC-ABS, MAD threshold,
    smoothing 15/35, top ROI 1/2/mean. Dinamai proxy karena belum memakai dense
    optical flow 14 ROI asli.
  - boundary refinement: fixed-window vs `boundary_beta=0.3`.

### Hasil CAS(ME)² penuh (86 video, 145 config)
Output: `output/training/paper_spotting_configs/{summary.md,results.csv,split_selection.csv}`.

Best per family:

| family | config | P | R | F1 | IoU50 F1 | F | det/video | FP/video |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| baseline | current_mean_m | 0,2753 | 0,3799 | **0,3192** | 0,1392 | 1,0764 | 4,9419 | 3,5814 |
| of_fd_proxy | of_fd_proxy_mad2.5_topmean_sw35_b0.3 | 0,2180 | 0,2435 | 0,2301 | **0,1503** | 0,3729 | 4,0000 | 3,1279 |
| fd_peak | fd_k17_tau0.45_topmean_bfixed | 0,1195 | 0,4643 | 0,1900 | 0,0930 | 0,4693 | 13,9186 | 12,2558 |
| multi_window_temporal | multiwin_L45_tau0.3_topmean_b0.3 | 0,0974 | 0,5455 | 0,1653 | 0,0758 | 0,5080 | 20,0581 | 18,1047 |

Subject split A/B selection picked `current_mean_m` on both halves:
- Train A → test B: F1 0,2857, F 1,0490, P 0,2446, R 0,3435.
- Train B → test A: F1 0,3445, F 1,0936, P 0,2988, R 0,4068.

Precision-oriented finding: OF-FD proxy can produce cleaner, shorter intervals
and lower FP load, e.g. `of_fd_proxy_mad3.5_topmean_sw35_b0.3` gives precision
0,3000 and FP/video 1,0581. For downstream recognition this is a valid A/B
candidate even though loose F1/recall is lower, because false-positive clips may
poison TabR more than missed events.

### Keputusan
Koreksi arah: jangan pakai loose F1 sebagai stop condition. `mean_m` tetap
high-recall baseline, tetapi precision-first `of_fd_proxy_mad3.5_topmean_sw35_b0.3`
sekarang di-wire sebagai `SPOT_ALGO=of_fd_proxy` untuk uji downstream. Ini bukan
klaim reproduksi OF-FD paper; proxy masih memakai kurva ROI POC-ABS, bukan dense
optical flow 13/14 ROI + nose-tip alignment. True OF-FD tetap next step kalau
proxy downstream bergerak positif.

Command downstream yang siap dijalankan user (full run, jangan dijalankan agent
tanpa izin):

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

### Verifikasi
- `.venv/bin/python -m py_compile scripts/process_spotting_pipeline.py scripts/eval_paper_spotting_configs.py features_extraction/poc.py` — PASS.
- `bash -n scripts/run_pipeline_v3.sh` — PASS.
- `V3_SPOT_ALGO=of_fd_proxy ./scripts/run_pipeline_v3.sh --dry-run --stage 1` — PASS; dry-run shows `SPOT_ALGO=of_fd_proxy` is forwarded.
- Hanning sanity check: `hannCalc()` shape `(7, 7)`, center 1, corner 0;
  `calcPOC()` output `(7, 7)` finite — PASS.
- Limit sweep: `.venv/bin/python scripts/eval_paper_spotting_configs.py --limit 3 --out output/training/paper_spotting_configs_limit3` — PASS.
- Full cache sweep: `.venv/bin/python scripts/eval_paper_spotting_configs.py --out output/training/paper_spotting_configs` — PASS.

### Belum
- Belum menjalankan full anxiety pipeline; user contract melarang smoke/e2e/full
  run kecuali diminta.
- Belum implement dense optical-flow OF-FD asli (13/14 ROI + face/nose alignment).

## 2026-10-14 — Plan: MyGo native desktop app untuk pipeline dashboard

### Arahan user
User ingin tidak perlu mengetik command/script setiap kali menjalankan pipeline.
Ide: bangun desktop native app memakai MyGo seperti Meiro/kupic, dengan dashboard,
switch pipeline, diagnosis masalah per stage, dan report yang enak dibaca.

### Yang dibuat
`report/plans/2026-10-14-pipeline-desktop-dashboard/` — **PLAN SAJA, belum
dieksekusi**. Isi: `CONTEXT.md`, `plan.md`, dan 9 issue.

### Keputusan utama
Jangan bikin app sebagai "terminal skin". Jalur yang dipilih:
1. pipeline tetap Python/bash dulu;
2. buat registry/kontrak pipeline yang machine-readable;
3. Go run controller menjalankan pipeline, stream log, simpan event terstruktur;
4. MyGo native UI menampilkan switcher, setup run, timeline stage, diagnostics,
   dan report dashboard;
5. report lama diparse ke `summary.json` agar bisa dibandingkan di UI.

### Arsitektur target
- `desktop/pipelinedesk/` untuk app MyGo native.
- `pipeline/registry.*` untuk daftar pipeline/stage/env/output/report.
- `.pipeline/runs/<run-id>/` untuk `run.json`, `events.jsonl`, stage logs, dan
  normalized report.

### Catatan penting
Plan ini sengaja bergantung pada plan refactor stage sebelumnya
`report/plans/2026-10-13-pipeline-stage-refactor/`. Kalau refactor itu belum
dieksekusi, app perlu adapter sementara untuk `scripts/run_pipeline_v3.sh`.

### Belum
- Belum implement app.
- Belum pilih arah visual. Sebelum UI dibangun, perlu keputusan Khalid: mau
  rasa kupic black control-room, Meiro Material app, atau dashboard lab riset.

### Update arah visual dari Khalid
Khalid memilih **brutalism** untuk app ini, "just because", supaya kelihatan
beda dan fun. Plan desktop dashboard diperbarui: arah visual bukan lagi terbuka.
Catatan batasnya: brutalism dipakai sebagai struktur visual (hard edges, thick
borders, blunt labels, kontras kuat), bukan UI berantakan atau terminal cosplay.
Report dan diagnostics tetap harus mudah dibaca.

### Update arah visual kedua
Khalid pivot ke **Frutiger Aero**. Ini sekarang arah utama app: glossy aqua/green,
nostalgic, fun, dengan glassy grouping dan status blocks yang jelas. Batasnya:
functional gloss, bukan bubble wallpaper yang bikin report/log susah dibaca.

### Update varian final
Khalid memilih varian **Aqua OS Dashboard** dari opsi Frutiger Aero. Ini jadi
arah final sementara: bright, clean, everyday-use, sky/aqua background,
white-blue glossy panels, green glass status blocks, dan red hanya untuk failure.

## 2026-10-14 — Pipeline Desk MVP (MyGo native desktop dashboard)

### Arahan user
Khalid ingin pipeline tidak lagi dioperasikan dengan hafalan command script. UI direction dipilih setelah eksplorasi: **Aqua OS / Frutiger Aero**, fun tetapi bukan design slop, tetap readable untuk diagnosa dan report.

### Yang dibangun
- `desktop/pipelinedesk/`: app native MyGo baru, bukan webview.
- `pipeline/registry.json`: registry pipeline yang dibaca app, berisi `pipeline_v3`, `pipeline_v3_presplit`, `loso_only`, dan `casme2_spotting_eval`.
- Go registry loader validasi command path, duplicate ID, stage wajib.
- Go controller menjalankan satu run, capture stdout/stderr, tulis `.pipeline/runs/<run-id>/run.json`, `events.jsonl`, dan `stages/run.log`.
- UI Aqua OS: pipeline switcher, run setup, dry-run toggle, preset select, stage map, stage details, report summary, artifacts.
- Diagnostics rule-based konservatif: missing file/command, OOM, no folds, threshold/gate, unknown.
- Report parser Markdown awal: mengambil metric table jika ada, dan pakai placeholder `[from report]` kalau report tidak ada, tidak mengarang angka.
- Snapshot/render harness MyGo untuk setup, running, failed/report.
- Root shortcut: `./run desk`.

### Verifikasi
Dijalankan di `desktop/pipelinedesk`:
- `/home/finny/.local/go/bin/go build ./...` PASS.
- `/home/finny/.local/go/bin/go vet ./...` PASS.
- `PIPELINE_DESK_ROOT=/home/finny/projects/Skripsi /home/finny/.local/go/bin/go test -run TestViewInteractions .` PASS, memverifikasi pipeline switch dan dry-run checkbox.
- `PIPELINE_DESK_ROOT=/home/finny/projects/Skripsi PIPELINE_DESK_SNAPSHOTS=/home/finny/projects/Skripsi/.amp/in/artifacts /home/finny/.local/go/bin/go test -run TestSnapshots .` PASS, menghasilkan screenshot setup/running/failed.
- Screenshots diinspeksi dengan `view_media`: setup tidak ada fake failure, running fokus stage aktif, failed state jelas, report missing jujur dengan placeholder, tidak ada panel overlap besar.

### Tidak dilakukan
- Tidak menjalankan full pipeline, smoke/e2e, atau dry-run real dari UI karena kontrak Khalid melarang test/smoke/e2e kecuali diminta.
- Packaging final app bundle/icon belum dibuat. `./run desk` untuk dev launch sudah ada.
- Compare runs/export dan resume/rerun aman masih future work.

## 2026-10-14 — Pipeline Desk launcher display fix

`./run desk` initially built the app but MyGo exited with `cannot open display` because this runner shell had neither `DISPLAY` nor `WAYLAND_DISPLAY`, even though `/run/user/1000/wayland-1` and `/tmp/.X11-unix/X0` existed. Fixed the launcher to auto-export `XDG_RUNTIME_DIR`, prefer `WAYLAND_DISPLAY=wayland-1`, fallback to `wayland-0`, then `DISPLAY=:0`.

Verification: `./run desk` now builds and stays running under MyGo dev. GTK only prints theme warnings.

## 2026-10-14 — Pipeline Desk: dead sidebar UI dihapus, screenshot final diverifikasi

### Yang diverifikasi
Screenshot final setelah patch overlap terakhir (yang sebelumnya belum diinspeksi) sudah dilihat dengan `view_media`:
- `.amp/in/artifacts/pipelinedesk-setup.png`
- `.amp/in/artifacts/pipelinedesk-running.png`
- `.amp/in/artifacts/pipelinedesk-failed-report.png`

Hasil: tidak ada lagi teks stage timeline yang bocor di belakang card `Stage details`, tidak ada overlap di panel tengah, background Frutiger Aero tetap dekoratif dan tidak mengganggu keterbacaan. Defect yang tercatat di handoff sebelumnya sudah hilang.

### Dead code dihapus
`view.go` masih menyimpan shell sidebar versi lama (layout yang Khalid tolak: "pipelines should be above not on the side"). Shell itu sudah tidak terpanggil karena `view` mendelegasikan ke `viewVariant(c, variantRibbon)`. Dihapus:
- `header`, `sidebar`, `pipelineRow`, `sidebarItem`, `mainContent`, `runSetup`, `stageMap`, `stageBlock`, `stageDetails`, `reportSummary`, `artifacts`, `glassPanel`, `sectionTitle`, `metricCard` dari `view.go`.
- `recentRuns` dan `displayCommand` dari `app.go` (tidak ada pemanggil).
- Palette var `aquaWater`, `aquaPanel`, `aquaPanelHi`, `aquaPanelLow`, `aquaGrey` dari `theme.go` (hanya dipakai shell lama).

`view.go` sekarang hanya berisi helper yang benar-benar dipakai variant: `view`, `focusStage`, `stageDetailState`, `detailRow`, `artifactChip`, `reportPath`, `displayTime`, `displayDuration`, `firstNonEmpty`. Total turun dari 1991 ke 1717 baris.

### Verifikasi
```bash
cd /home/finny/projects/Skripsi/desktop/pipelinedesk
/home/finny/.local/go/bin/go build ./...   # PASS
/home/finny/.local/go/bin/go vet ./...     # PASS
PIPELINE_DESK_ROOT=/home/finny/projects/Skripsi PIPELINE_DESK_SNAPSHOTS=/home/finny/projects/Skripsi/.amp/in/artifacts \
  /home/finny/.local/go/bin/go test -run 'TestSnapshots|TestVariantSnapshots|TestViewInteractions' .  # PASS
```
Snapshot `pipelinedesk-setup.png` byte-identical sebelum/sesudah (sha256 sama), jadi penghapusan dead code tidak mengubah render. Running/failed hanya beda timestamp live.

Launch check: `./run desk` build sukses dan app jalan (`✓ Built Pipeline Desk Dev`, `➜ Watching for changes`).

### Catatan
- Dua proses `mygo dev` dari thread sebelumnya masih hidup (PID 148843, 148902, ~54 menit) dan meng-watch direktori yang sama. Tidak dimatikan karena bukan milik thread ini.
- Varian `variantControlPanel` dan `variantLabMonitor` masih ada di `variants.go` dan masih dirender `TestVariantSnapshots`. Ini masih keputusan terbuka Khalid: dipertahankan sebagai prototipe atau dihapus.

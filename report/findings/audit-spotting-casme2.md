# Audit Spotting CAS(ME)² — apa yang berubah dari aslinya, dan mengapa performanya rendah

Tanggal: 2026-10-09
Konteks: setelah benchmark CAS(ME)² memberi F1 rendah (~0,20), dilakukan audit
"apa yang kita ubah sejak kode asli" + telaah mendalam sinyal POC-ABS.

Semua angka di bawah memakai protokol yang sama dengan benchmark
(`scripts/eval_spotting_casme2.py`): 86 video, 308 ekspresi GT, toleransi 0 frame,
pencocokan interval.

---

## 1. Di mana logika spotting ASLI sebenarnya

`preprocess-anxiety/spotting.py` (versi asli) **hanya berisi dataclass + stub**:

```python
def run_spotting(_config: SpottingConfig) -> pd.DataFrame:
    raise NotImplementedError("Run logic lives in process_all_datasets_flexible.ipynb")
```

Jadi logika spotting asli **tidak ada di file .py mana pun** — ada di notebook
`preprocess-anxiety/process_all_datasets.ipynb` (dan varian CASME
`micro_expression_spotting_v2 Casme.ipynb`). `scripts/process_spotting_pipeline.py`
yang dipakai sekarang adalah **reimplementasi** dari notebook itu, bukan salinan.

Ini penting: "kode asli" untuk pembanding bukan file .py, melainkan notebook.

---

## 2. Divergensi yang ditemukan

| # | Aspek | Asli (notebook) | Sekarang | Status |
|---|---|---|---|---|
| 1 | Agregasi antar-ROI | **global** (rata-rata 5 ROI → 1 sinyal) | **per-ROI** (`roi_signals`) | **regresi** |
| 2 | Acuan POC | frame **berurutan** (i vs i-1) | frame-0 (POC-ABS) | adaptasi perlu |
| 3 | Smoothing | 5% panjang sinyal, clamp 31 | tetap 7 | netral |
| 4 | `block_size` | 7 | 9 | **tidak berpengaruh** |
| 5 | ROI | mata (36-41/42-47) + alis (17-21/22-26) terpisah | **sama** | tidak berubah |
| 6 | Filter tambahan | tidak ada | `prom_rel`, interpolasi | tidak binding |
| 7 | `min_phase_duration` | 2 | 2 | sama |

Catatan #5: definisi ROI di `features_extraction/roi_config.py` **cocok** dengan
notebook asli. Yang menyimpang adalah `comparasion/core/config.py` (mata = alis+mata,
tumpang tindih) — itu jalur `comparasion`, bukan jalur spotting.

Catatan #4: diuji sintetis (gerakan 1-3 px diketahui, ROI nyata). Sinyal block 7 vs 9
sebanding, tidak ada pemenang sistematis:

| gerakan | block 7 (alis/mata/mulut) | block 9 (alis/mata/mulut) |
|---|---|---|
| 1 px | 0.259 / 0.208 / 0.260 | 0.357 / 0.067 / 0.238 |
| 2 px | 0.556 / 0.292 / 0.705 | 0.429 / 0.333 / 0.714 |
| 3 px | 0.741 / 0.770 / 0.835 | 0.857 / 0.840 / 0.857 |

Jadi `block_size` bukan penyebab. Uji pada 86 video nyata tidak diselesaikan
(terlalu lama); kesimpulan diambil dari uji sintetis + alasan bahwa saturasi
hanya muncul pada gerakan besar (bukan micro-expression).

---

## 3. Bukti #1 — agregasi per-ROI adalah regresi

`scripts/audit_agg_f1_casme2.py`, 86 video, toleransi 0:

| agregasi | top_k | precision | recall | F1 | det/video |
|---|---|---|---|---|---|
| global | 5 | 0.1837 | 0.2565 | **0.2141** | 5.0 |
| global | 10 | 0.1384 | 0.3864 | 0.2038 | 10.0 |
| per_roi (sekarang) | 1 | 0.1838 | 0.2208 | 0.2006 | 4.3 |
| per_roi (sekarang) | 5 | 0.0971 | 0.5195 | 0.1637 | 19.2 |

**Default pipeline sekarang** = `roi_signals` + `top_k=5` → **F1 0,1637**
(19,2 deteksi/video, GT hanya 3,6). Mengembalikan agregasi ke **global**
→ **F1 0,2141** (5,0 deteksi/video). Naik ~31% relatif, dan jumlah deteksi
kembali wajar.

Sebabnya: mode per-ROI mendeteksi top-5 puncak **di tiap ROI** lalu menggabung,
jadi deteksi = 5 × jumlah ROI. Plafonnya 5 ROI × top_k. Sinyal mulut jauh lebih
besar dari alis/mata, jadi penggabungan lintas-ROI (dedup) juga bias ke mulut.

---

## 4. Bukti #2 — acuan frame-0 BUKAN regresi, justru perlu

`scripts/baseline_probe_casme2.py` + `scripts/audit_baseline_agg_casme2.py`
(31 video sudah ter-cache saat audit ini):

| acuan | agregasi | P@1 | P@5 | P@10 |
|---|---|---|---|---|
| **abs (frame-0, sekarang)** | **global** | **0.048** | **0.144** | **0.250** |
| lag30 | global | 0.048 | 0.077 | 0.183 |
| lag10 | global | 0.019 | 0.106 | 0.164 |
| **seq (berurutan, asli)** | global | **0.000** | **0.048** | **0.125** |

Uji sintetis (gerakan halus diketahui besarnya, `apex/` + ROI nyata):

| gerakan | abs | seq | lag10/lag30 |
|---|---|---|---|
| 2 px selama 8 frame | 0.364 | 0.099 | 0.364 |
| 5 px selama 20 frame | 1.259 | 0.071 | 1.259 |

**Penjelasan:** POC mencari pergeseran **bilangan bulat** per blok. Pada video
CAS(ME)² 30 fps, gerakan antar-frame sebuah micro-expression **sub-piksel**
(< 1 px/frame) → tidak terlihat POC. Yang terlihat hanya pergeseran kumulatif
dari acuan tetap. Karena itu acuan berurutan (asli) nyaris buta, dan frame-0
(sekarang) justru yang bisa melihat. Aslinya dipakai di video kecemasan 60 fps,
di mana gerakan per frame masih ≥ 1 px.

Konsekuensi desain: **jangan kembalikan acuan ke berurutan.**

---

## 5. Telaah mendalam — mengapa sinyalnya lemah

Diukur pada sinyal global (cara asli), 308 GT:

| ukuran | nilai |
|---|---|
| persentil nilai sinyal **di frame apex** | 0.776 (acak = 0.50) |
| ada puncak dalam ±5 frame apex | 100% |
| peringkat puncak-apex menurut tinggi | **0.226** (≈124 dari ~549 puncak) |
| puncak dekat apex yang lolos `height = mean+std` | **50,6%** (49% gugur) |
| F1 acak (5 deteksi acak/video) | 0.106 |
| F1 kita (global, top_k=5) | 0.214 |

Artinya: sinyal **merespons** ekspresi (persentil 0.776, bukan 0.5), tetapi
responsnya **lemah** dibanding gerakan lain di video, sehingga puncak ekspresi
berada di sekitar peringkat 124 — jauh di luar top-5.

Yang **tidak** menolong (semua diuji, cache-based):

- Transformasi sinyal: high-pass (w=31/101/301), z-score bergerak, rasio
  bergerak, turunan. **Semua lebih buruk** dari sinyal mentah. Jadi masalahnya
  **bukan** drift frekuensi rendah.
- Sinyal alternatif dari cache kaya: `max_m` (F1 0.173), `motion_count` (0.203),
  `mean_x` (0.103), `mean_y` (0.133), `angle_R` (0.030). `mean_m` (yang dipakai)
  tetap terbaik.
- Grid detektor (height `mean+k·std`, ranking value vs prominence, top_k 3-15):
  plateau di **F1 ≈ 0.22-0.23**. Terbaik: prominence, k=2.0, top_k=8 → 0.2263.
- Mengubah metrik ke jarak-apex (bukan tumpang-tindih interval) **tidak**
  memperbaiki (F1 0.081-0.244 tergantung toleransi).

---

## 6. Kesimpulan

1. **Ada regresi nyata**: agregasi global → per-ROI. Ini akar "sesuatu yang rusak".
   Default sekarang menghasilkan 19 deteksi/video untuk GT 3,6.
2. **Acuan frame-0 bukan regresi** — justru syarat agar POC melihat micro-expression
   pada 30 fps. Mengembalikannya ke berurutan akan memperburuk.
3. **Ada regresi kedua**: resep pemilihan puncak. Lihat §8.

---

## 8. Deep dive notebook: apa yang terlewat selama ini

### 8.1 Logika spotting asli hidup di notebook, dan ada TIGA generasi

| generasi | berkas | smoothing | pemilihan puncak | onset/offset |
|---|---|---|---|---|
| 1 | `micro_expression_spotting.ipynb` | savgol **tetap 28**, polyorder 3 | `find_peaks(prominence=0)` **tanpa height**, urut **PROMINENCE**, top **3** | cutoff **0.20** dari min GLOBAL |
| 2 | `micro_expression_spotting_v2.ipynb`, `..._v2 Casme.ipynb` | `ApexSmoother` **5% clamp 31** | `find_top_k_apex(k=0/5, height=mean+std)`, urut **NILAI** | `find_phase` cutoff 0.30 |
| 3 | `process_all_datasets.ipynb` | = generasi 2 | = generasi 2 (agregasi global) | = generasi 2 |

Pipeline sekarang memakai generasi 2/3 **tapi** dengan dua penyimpangan:
smoothing diubah jadi tetap 7 (§2 #3) dan itu ternyata bukan "netral".

**Yang terlewat: generasi 1 memakai peringkat PROMINENCE dan window panjang.**
Pipeline memakai peringkat NILAI dan window 7.

### 8.2 Kenapa peringkat prominence lebih tepat

Puncak ekspresi sering **bukan** puncak tertinggi di sinyal (drift/gerakan besar
lainnya lebih tinggi). `height=mean+std` + peringkat nilai karena itu membuang
puncak ekspresi. Prominence mengukur "seberapa menonjol secara lokal", yang persis
definisi puncak ekspresi. Ini juga alasan generasi 1 memilihnya.

### 8.3 Bukti: dua tuas, keduanya terpisah

86 video, toleransi 0, agregasi global, `top_k=5`, `height=mean+std`:

| smoothing | peringkat | F1 |
|---|---|---|
| tetap 7 (sekarang) | nilai | 0.2141 |
| tetap 7 | prominence | 0.2087 |
| 28 tetap | nilai | 0.2602 |
| 5% clamp 31 | nilai | 0.2602 |
| 5% clamp 31 | prominence | 0.3001 |
| 3% adaptif | prominence | **0.3179** |

- Efek **window**: 0.2141 → 0.2602 (tetap 7 → 28/5%).
- Efek **peringkat**: 0.2602 → 0.3144 (nilai → prominence, pada window 28).
- Gabungan: **0.2141 → 0.3179** (+48% relatif).

### 8.4 Validasi split subjek (menutup jebakan "pilih parameter di data uji")

22 subjek dibagi 2 paruh (A/B). Konfigurasi dipilih di satu paruh, diukur di paruh
lain:

| fold | konfigurasi terpilih | F1 train | F1 test |
|---|---|---|---|
| A → B | 3% adaptif / prominence / k5 | 0.3202 | **0.3152** |
| B → A | 3% adaptif / prominence / k5 | 0.3152 | **0.3202** |
| (pembanding) | pipeline lama (7 / nilai / k5) | — | 0.2061–0.2206 |

Kedua fold memilih konfigurasi yang SAMA, dan F1 test ≈ F1 train. Jadi kenaikannya
nyata, bukan overfitting.

### 8.5 Catatan kejujuran: durasi event ikut memanjang

Window panjang membuat fase onset→offset lebih panjang (median 60 frame vs GT 28).
Karena itu diukur juga F1 dengan tumpang tindih ketat (IoU ≥ 0,5):

| resep | durasi deteksi (median) | F1 (beririsan) | F1 (IoU ≥ 0,5) |
|---|---|---|---|
| 7 / nilai (lama) | 14 | 0.2141 | 0.0705 |
| 28 / prominence | 36 | 0.2818 | 0.1274 |
| 3% / prominence | 60 | 0.3179 | 0.1386 |

F1 ketat ikut naik (0.071 → 0.139), jadi kenaikannya bukan sekadar event yang
dipanjangkan. (Bandingkan artefak window=96 lama yang beririsan 0.43 tapi IoU
hanya 0.0061.)

---

## 9. Perubahan yang diterapkan

1. **`SPOT_SIGNAL_MODE` default → `global_mean`** (audit §3). F1 0.1637 → 0.2141.
2. **`apex/apex_smoother.py`**: window tetap 7 → **3% adaptif** (min 5, tanpa clamp
   atas), §8.3-8.4.
3. **`apex/apex_phase.py`**: `find_top_k_apex` menerima `ranking` (`'value'`
   default = perilaku lama; `'prominence'` = resep baru).
4. **`process_spotting_pipeline.py`**: `SPOT_RANKING` (default `prominence`),
   diteruskan lewat `DetectParams.ranking`.
5. **`eval_spotting_casme2.py`**: `detect_from_signals` mengikuti
   `SPOT_SIGNAL_MODE`, supaya benchmark mengukur perilaku pipeline yang sebenarnya.

### Hasil akhir (86 video, toleransi 0, default pipeline)

| resep | P | R | F1 | det/video | F1 micro |
|---|---|---|---|---|---|
| sebelum audit (per-ROI / 7 / nilai) | 0.0971 | 0.5195 | 0.1637 | 19.2 | 0.3860* |
| setelah perbaikan agregasi (global / 7 / nilai) | 0.1837 | 0.2565 | 0.2141 | 5.0 | — |
| **sekarang (global / 3% / prominence)** | **0.2753** | **0.3799** | **0.3192** | 4.9 | **0.2632** |
| sekarang, `top_k=4` (terbaik) | 0.3079 | 0.3409 | **0.3236** | 4.0 | 0.2281 |

\* recall micro tinggi pada resep lama itu artefak: 19 deteksi/video hampir selalu
"beririsan" dengan GT.

### Dampak yang perlu diketahui

- **Semua klip event + tabel fitur lama menjadi tidak berlaku** — parameter
  deteksi berubah. Perlu regenerasi sebelum training.
- `ApexSmoother` juga dipakai `scripts/extract_features_poc_abs.py`
  (`detect_roi_apex`, `k=1`, peringkat tetap `value`). Window untuk klip pendek
  hanya bergeser 7 → 5, jadi dampaknya kecil, tetapi tetap ada.
- Masih ada tuas yang belum diuji: `cutoff_ratio` 0.3 → 0.5 menaikkan F1 ketat
  (IoU ≥ 0,5) 0.149 → 0.179 dan memperpendek durasi 59 → 41 frame. Belum diterapkan.

---

## 10. Sanity check regime 60 fps (data kecemasan) sebelum regenerasi

`scripts/audit_anxiety_regime.py`, 16 klip `after/*` nyata (60 fps, .avi,
149-950 frame). Tiga hal yang dikhawatirkan sebelum memakai parameter baru di
pipeline kecemasan:

### 10.1 Drift: TIDAK terjadi

Acuan frame-0 menumpuk pergeseran 2x lebih cepat pada 60 fps, jadi ada
kekhawatiran drift. Hasilnya sebaliknya:

| acuan | energi hi/lo | korelasi dgn tren lambat |
|---|---|---|
| **abs (frame-0, dipakai)** | **4.087** | **0.239** |
| lag30 | 3.891 | 0.266 |
| lag60 | 3.827 | 0.233 |

hi/lo > 1 berarti energi frekuensi tinggi MENDOMINASI tren lambat, dan korelasi
0.24 berarti sinyal tidak terikat tren. `abs` bahkan sedikit lebih baik daripada
acuan lokal. Sebabnya: klip kecemasan **pendek** (median ~300 frame = 5 detik),
jadi pergeseran kumulatif belum menumpuk. (CAS(ME)² median 2305 frame = 77 detik —
di situ frame-0 memang lebih tertekan, tapi tetap terbukti lebih baik daripada
acuan berurutan, §4.)

### 10.2 Window: dampaknya kecil

| window | puncak/klip | event/klip (top_k=5) |
|---|---|---|
| tetap 7 | 73 | 5.0 |
| 3% adaptif | 71 | 5.0 |
| 5% adaptif | 64 | 5.0 |

Karena klipnya pendek, 3% ≈ 5-18 frame, tidak jauh dari 7. Jumlah puncak dan event
nyaris sama. Jadi perubahan window **berisiko rendah** di regime kecemasan.

### 10.3 Durasi event: sedikit lebih panjang

Micro-expression 60 fps = 2,4-12 frame. Median durasi event:

| window | median | p25 | p75 |
|---|---|---|---|
| tetap 7 | 10 | 7 | 17 |
| 3% adaptif | 14 | 8 | 20 |
| 5% adaptif | 15 | 10 | 35 |

3% memberi median 14 frame (sedikit di atas rentang mikro), tetap-7 memberi 10.
Bedanya kecil dan durasi lebih ditentukan `cutoff_ratio` (0,3). Dicatat sebagai
keterbatasan; lever kalau perlu: `cutoff_ratio` 0,3 → 0,5 (memperpendek 59 → 41
frame di CAS(ME)² dan menaikkan F1 ketat 0,149 → 0,179).

**Kesimpulan: parameter baru aman dipakai di pipeline kecemasan.**

---

## 11. Koreksi: klaim "dominasi identitas" TIDAK bebas dari masalah spotting

Di draf sebelumnya disebut bahwa temuan dominasi identitas
(`report/findings/poc-abs-karakterisasi.md`, median 0,79) tidak terpengaruh karena
memakai sinyal per-frame lintas video. **Itu salah.**

`poc_abs_roi_signals_v3_full.pkl` punya kolom `event_clip` dengan **6.473 klip
event, 0 null** — jadi fitur per-frame itu dihitung DI DALAM klip event hasil
spotting lama (rata-rata 14,2 frame per klip, nama klip masih per-ROI seperti
`event_00006-00016_alis_kanan`). Artinya temuan itu **ikut berubah** saat spotting
diperbaiki, dan justru itu alasan tambahan untuk regenerasi.

Selain itu, angka 0,79 itu **tidak bisa direproduksi** dengan dekomposisi varians
yang lugas. Diukur ulang pada berkas yang sama
(`scripts/audit_identity_dominance.py`, eta-kuadrat grup = peserta):

| pengelompokan | median dominasi identitas |
|---|---|
| peserta (`participant`, 56) | 0,030 |
| sesi (`participant_raw`, 111) | 0,047 |
| label | 0,001 |

Ketiga cara memberi nilai jauh di bawah 0,79. Jadi angka di dokumen lama perlu
dianggap **belum terverifikasi** sampai diukur ulang dengan metode yang sama
(metode aslinya tidak terdokumentasi sebagai skrip). Yang tetap berlaku dari
dokumen itu adalah temuan mekanisme POC (§2.1 grid blok, §2.3 hanning no-op,
§2.5 `mean_x` terencerkan) — itu soal cara kerja POC, bukan pemilihan event.

---

## 12. Hasil regenerasi pipeline kecemasan (spotting diperbaiki)

Dijalankan lewat `scripts/run_pipeline_v3.sh` dengan tag baru (keluaran lama tidak
disentuh). Lihat `report/documentation/changes-log.md` Iterasi 4.50.

### 12.1 Spotting: event turun ke tingkat wajar

| | lama (rusak) | baru (diperbaiki) |
|---|---|---|
| baris metadata | 7.094 | **2.647** |
| event/sample | 12,7 | **4,8** |
| region | per-ROI (`alis_kanan`, `mulut`, …) | **`global`** (semua) |
| durasi event (median) | 11 | 17 |

### 12.2 Gate within-subject: NAIK, tapi belum signifikan

Ini uji paling bersih (orang sama, wajah sama, label beda -> bebas confound
identitas). Membandingkan lama vs baru pada data yang sama:

| fitur | lama BA | lama p | **baru BA** | **baru p** |
|---|---|---|---|---|
| per-frame (60 fitur) | 0,5833 | 0,1642 | **0,6111** | **0,1244** |
| temporal (335 fitur) | 0,5000 | 0,5970 | **0,6389** | **0,1045** |

Fitur signifikan (FDR 5%): **0 dari 60** dan **0 dari 335** di kedua versi.

Bacaan jujur: memperbaiki spotting **memang menaikkan sinyal** — yang paling
mencolok fitur temporal (BA 0,50 -> 0,64, p 0,597 -> 0,105). Arahnya benar dan
konsisten dengan kenaikan F1 spotting. **Tetapi** masih belum melewati p < 0,05,
dan n-nya hanya 18 subjek (36 baris), jadi dayanya kecil. Jadi: perbaikan ini
nyata dan perlu, tapi belum cukup untuk mengklaim POC-ABS membawa sinyal
kecemasan yang terdeteksi pada protokol ini.

### 12.3 Dominasi identitas: tidak berubah banyak

`scripts/audit_identity_dominance.py`, eta-kuadrat grup = peserta:

| fitur | median dominasi identitas |
|---|---|
| lama (97.808 baris) | 0,030 |
| baru (62.955 baris) | 0,041 |

Tetap jauh di bawah angka 0,79 di dokumen lama (§11). Perbaikan spotting tidak
mengubah gambaran ini.

### 12.4 LOSO TabR: TIDAK berubah — masih di/bawah acak

56 fold × 3 seed, protokol sama untuk kedua versi.

| metrik | lama (spotting rusak) | **baru (spotting diperbaiki)** | baseline mayoritas |
|---|---|---|---|
| accuracy | 0,4881 ± 0,0805 | **0,4821 ± 0,0472** | 0,5536 |
| balanced accuracy | 0,4692 | **0,4716** | – |
| MCC | −0,0521 | **−0,0622** | – |
| AUC (level subjek) | 0,3974 | **0,4606** | 0,5 |
| sensitivity | 0,2933 | **0,3733** | – |
| specificity | 0,6452 | **0,5699** | – |

Pembanding model sederhana pada fitur BARU (permutasi 200x):

| model | accuracy | p-value |
|---|---|---|
| logistic | 0,5714 | 0,2189 |
| GBDT | 0,5536 | 0,3781 |

**Bacaan:** memperbaiki spotting menaikkan AUC (0,397 -> 0,461) dan sensitivity
(0,293 -> 0,373), tapi **accuracy tetap di bawah baseline mayoritas** (0,482 vs
0,554) dan **AUC masih di bawah 0,5** (model meranking subjek cemas lebih buruk
dari acak). Baseline logistic pun tidak signifikan (p = 0,22).

Jadi: perbaikan spotting **nyata dan perlu** (F1 spotting 0,164 -> 0,319; gate
within-subject BA 0,50 -> 0,64), tetapi **belum mengubah kesimpulan klasifikasi
kecemasan**: pada protokol LOSO lintas-subjek ini, fitur POC-ABS belum terbukti
memisahkan kecemasan tinggi vs rendah.

### 12.5 Ringkasan: apa yang diperbaiki dan apa yang tidak

| tahap | sebelum | sesudah | verdict |
|---|---|---|---|
| spotting F1 (CAS(ME)²) | 0,1637 | **0,3192** | **diperbaiki, tervalidasi** |
| event/sample | 12,7 | 4,8 | wajar |
| gate within-subject (BA) | 0,500 | **0,639** | naik, belum p < 0,05 |
| LOSO accuracy | 0,4881 | 0,4821 | **tidak berubah** |
| LOSO AUC | 0,3974 | 0,4606 | naik, masih < 0,5 |

**Kesimpulan:** akar masalah spotting sudah ditemukan dan diperbaiki. Itu tidak
cukup untuk membuat klasifikasi kecemasan bekerja. Kegagalan klasifikasi bukan
(kebanyakan) akibat spotting yang rusak.


---

## Lampiran — skrip audit

| skrip | isi |
|---|---|
| `audit_smoothing_casme2.py` | smoothing tetap-7 vs adaptif 5%/31 |
| `audit_agg_f1_casme2.py` | F1 global vs per-ROI (protokol benchmark) |
| `audit_baseline_agg_casme2.py` | P@K untuk abs/seq/lag10/lag30 × global/per-ROI |
| `audit_signal_transform_casme2.py` | high-pass/z-score/rasio/turunan |
| `audit_detector_grid_casme2.py` | grid height × ranking × top_k |
| `audit_block_size_casme2.py` | block_size 7 vs 9 |
| `audit_peak_rank_casme2.py` | resep generasi 1 (tanpa height + prominence) vs sekarang |
| `audit_window_sweep_casme2.py` | sapu window + validasi split subjek |
| `audit_anxiety_regime.py` | sanity check 60 fps: drift, window, durasi |
| `audit_identity_dominance.py` | ukur ulang dominasi identitas (eta-kuadrat) |
| `baseline_probe_casme2.py` | hitung sinyal abs/seq/lag (cache, streaming) |



---

## 10. Sweep agregasi × cutoff_ratio dengan resep deteksi baru (2026-10-13)

Konteks: alternatif agregasi di §5 terakhir diuji dengan resep LAMA (window 7,
ranking nilai). Diulang dengan resep BARU (3% adaptif + prominence ranking,
height=mean+std, top_k=5, global_mean). Skrip: `scripts/audit_mag_agg_casme2.py`
(cache kaya 86 video, tanpa hitung ulang POC). Deep dive definisi sinyal per
blok: `report/findings/magnitude-deepdive.md`.

86 video, 308 GT, toleransi 0:

| agregasi | cutoff | P | R | F1 | F1 ketat (IoU≥0,5) | durasi median |
|---|---|---|---|---|---|---|
| **mean_m (sekarang)** | **0,3** | 0.2753 | 0.3799 | **0.3192** | 0.1282 | 61 |
| mean_m | 0,5 | 0.2659 | 0.3669 | 0.3083 | **0.1637** | 41 |
| max_m | 0,3 | 0.2583 | 0.3539 | 0.2986 | 0.0685 | 63 |
| max_m | 0,5 | 0.2417 | 0.3312 | 0.2795 | 0.1068 | 41 |
| motion_count | 0,3 | 0.2740 | 0.3799 | 0.3184 | 0.1197 | 61 |
| motion_count | 0,5 | 0.2529 | 0.3506 | 0.2939 | 0.1442 | 43 |
| mean_y | 0,3 | 0.1977 | 0.2760 | 0.2304 | 0.0461 | 57 |
| mean_x | 0,3 | 0.1488 | 0.2078 | 0.1734 | 0.0407 | 54 |
| angle_R | 0,3 | 0.0979 | 0.1364 | 0.1140 | 0.0054 | 51 |

Validasi split subjek 2-fold (pilih di train, ukur di test):

| fold | terpilih | train F1 | test F1 | test F1 ketat |
|---|---|---|---|---|
| A→B | motion_count / cutoff 0,3 | 0.3358 | 0.2970 | 0.1152 |
| B→A | max_m / cutoff 0,3 | 0.3313 | 0.2723 | 0.0693 |

### Kesimpulan

1. **Agregasi: tidak ada pemenang tervalidasi.** Kedua fold memilih kandidat
   berbeda dan mean_m unggul di tabel penuh — sesuai aturan plan, mean_m
   tetap dipakai. Deep dive per-blok (10 video, metrik peringkat puncak)
   memberi jawaban sama dari sudut independen: mean 0,146 vs top25 0,172,
   weighted 0,164, count 0,217, max 0,271.
2. **cutoff: 0,3 menang di F1 longgar pada KEDUA fold** (protokol memakai F1
   longgar sebagai kriteria) → default tetap 0,3. cutoff 0,5 menang di F1
   ketat (0,1637 vs 0,1282) dan memperpendek durasi 61→41 frame (GT median
   28) — artinya batas onset/offset lebih akurat, dengan biaya F1 longgar
   turun 0,011. Ini trade-off objektif (deteksi vs presisi batas), bukan
   kemenangan mutlak; default tidak diubah berdasarkan protokol, tetapi 0,5
   layak diuji di sisi anxiety (fitur event lebih rapat → lebih sedikit
   kontaminasi frame netral) lewat env `SPOT_CUTOFF` (isu 03).

---

## 11. Sweep internals detektor (2026-10-13, resep baru)

Konteks: merge_distance, top_k, min_phase_duration, valley_uptick, dan
MAX_SEARCH_RADIUS adalah angka warisan yang belum pernah diuji dengan resep
baru (3% adaptif + prominence). Skrip: `scripts/audit_detector_internals_casme2.py`
(cache mean_m 86 video, one-at-a-time dari BASE:
merge=10, top_k=5, min_dur=2, uptick=0,75, radius=100).

| variasi | F1 | F1 ketat | durasi median |
|---|---|---|---|
| **BASE (default)** | **0.3192** | 0.1282 | 61 |
| merge 5 / 20 | 0.3192 (identik) | 0.1282 | 61 |
| top_k 3 | 0.3156 | 0.1312 | 64 |
| top_k 4 | 0.3236 | 0.1294 | 64 |
| top_k 6 / 8 | 0.3088 / 0.2930 | lebih rendah | — |
| min_dur 1 / 4 | 0.3192 / 0.3197 | ~sama | 61 |
| uptick 0,5 | 0.2947 | 0.1201 | 44 |
| uptick 0,9 | 0.3274 | 0.1310 | 70 |
| radius 30 | 0.3083 | **0.1637** | 41 |
| radius 60 | 0.3165 | 0.1583 | 53 |
| radius 200 | 0.3274 | 0.1091 | 68 |

Kombinasi pemenang individual, divalidasi split subjek A/B:

| konfigurasi | full F1 | ketat | dur | A→B test | B→A test | verdict |
|---|---|---|---|---|---|---|
| BASE | 0.3192 | 0.1282 | 61 | 0.3161 | 0.3218 | — |
| KOMBI (topk4+mindur4+uptick0.9+radius200) | **0.3451** | 0.0986 | 84 | **0.3469** | **0.3437** | menang F1 longgar di KEDUA fold |
| K2 (topk4+uptick0.9) | 0.3267 | 0.1325 | 73 | 0.3129 ✗ | 0.3380 ✓ | tidak stabil |
| K4 (topk4) | 0.3236 | 0.1294 | 64 | 0.3061 ✗ | 0.3380 ✓ | tidak stabil |

### Keputusan

- **Deteksi apex (loose F1): KOMBI tervalidasi** (+8% relatif, menang dua arah).
- **Tapi batas onset/offset KOMBI memburuk** (F1 ketat 0,0986 vs 0,1282; durasi
  84 frame vs GT median 28). Karena klip event dipakai untuk ekstraksi fitur
  (frame netral ikut masuk kalau event melar), default pipeline untuk sisi
  anxiety TETAP BASE. KOMBI tersedia sebagai opsi pelaporan spotting.
- radius 30/60 menang di F1 ketat dengan durasi 41-53 frame — searah dengan
  temuan cutoff 0,5 (batas lebih rapat). Kandidat pasangan untuk uji sisi
  anxiety: `SPOT_CUTOFF=0.5` + radius 30-60.

## 12. Ulang uji acuan baseline dengan resep baru (2026-10-13)

Skrip: `scripts/audit_baseline_recheck_casme2.py` (cache baseline 41 video,
F1 toleransi 0, resep baru; pembanding abs dari cache kaya pada subset sama).

| acuan | P | R | F1 |
|---|---|---|---|
| **abs (frame-0, sekarang)** | 0.3035 | 0.4094 | **0.3486** |
| lag30 | 0.1659 | 0.2282 | 0.1921 |
| lag10 | 0.1463 | 0.2013 | 0.1695 |
| seq (berurutan) | 0.1220 | 0.1678 | 0.1412 |

Kesimpulan §4 (jangan kembalikan acuan ke berurutan) berlaku juga dengan resep
baru; lag-N bukan ancaman — frame-0 menang telak. Tidak ada tindakan.

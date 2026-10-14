# Deep dive magnitude POC-ABS: kuantisasi, saturasi, dan definisi sinyal terbaik

Tanggal: 2026-10-13
Plan: report/plans/2026-10-13-spotting-magnitude-deepdive (isu 01)
Data: 10 video CAS(ME)² (setiap ke-9 dari 86, stratifikasi macro+micro),
1.951.537 blok dianalisis. Skrip: `scripts/diag_magnitude_casme2.py`.

---

## 1. Kuantisasi magnitude per blok

Magnitude per blok = `sqrt(oX² + oY²)` dengan oX/oY integer −4..4 (block 9).
Hanya **15 nilai diskret** yang mungkin:

| magnitude | % blok | | magnitude | % blok |
|---|---|---|---|---|
| 0,000 | **57,81%** | | 3,162 | 1,07% |
| 1,000 | 16,47% | | 3,606 | 0,50% |
| 1,414 | 1,13% | | 4,000 | 4,98% |
| 2,000 | 8,10% | | 4,123 | 0,97% |
| 2,236 | 1,10% | | 4,243 | 0,21% |
| 2,828 | 0,25% | | 4,472 | 0,57% |
| 3,000 | 6,14% | | 5,000 | 0,46% |
| | | | 5,657 | 0,24% |

57,8% blok diam total; sinyal hidup di 42% blok sisanya yang nilainya
terkuantisasi kasar.

## 2. Saturasi batas pencarian (mode ABS, acuan frame-0)

| jenis | fraksi blok |
|---|---|
| \|oX\| = 4 (batas x) | 3,01% |
| \|oY\| = 4 (batas y) | 4,44% |
| keduanya | 0,24% |

Saturasi nyata tapi minor (~5% blok total). Block 9 cukup; menaikkan block
akan mengorbankan resolusi spasial (alis tinggal 1-2 baris blok, lihat
roi_config.py) untuk menutup saturasi yang kecil. **Tidak ada tindakan.**

## 3. Dilusi mean — seberapa besar sinyal ekspresi tertutup

| kondisi | fraksi blok bergerak (magnitude > 0) |
|---|---|
| saat GT ekspresi (onset..offset) | 0,447 |
| di luar ekspresi | 0,409 |
| rasio | **1,09×** |

Ekspresi hanya menambah ~9% relatif blok bergerak di atas tingkat gerakan
latar (video CAS(ME)² memang penuh gerakan kecil: kepala, kelopak, napas).
Artinya agregasi berbasis "berapa banyak blok bergerak" (count) pasti lemah —
dan memang terbukti lemah di semua pengukuran.

## 4. Definisi sinyal mana yang terbaik

Metrik: median peringkat relatif puncak ekspresi (urut **prominence**, resep
deteksi baru; 0 = terbaik, 0,5 = acak), agregasi global = mean antar ROI:

| definisi | peringkat |
|---|---|
| **mean (sekarang)** | **0,146** |
| weighted (bobot puncak korelasi) | 0,164 |
| top25 (mean 25% blok teratas) | 0,172 |
| count (fraksi blok bergerak) | 0,217 |
| max | 0,271 |

Catatan kejujuran: preview 2 video (macro saja) sempat menunjukkan top25
menang telak (0,091 vs 0,213). Pada 10 video hasilnya **terbalik** — artefak
sampel kecil. Ini alasan angka awal tidak boleh langsung dipercaya.

Konsisten dengan sweep F1 86 video (isu 02): mean_m F1 0,3192 tetap di atas
max_m (0,2986), motion_count (0,3184), mean_x (0,1734), mean_y (0,2304),
angle_R (0,1140), dan validasi split subjek tidak memilih pemenang lain yang
stabil.

## 5. Kesimpulan

1. **Definisi magnitude spotting terbaik untuk POC-ABS = mean per ROI lalu
   mean antar ROI (yang sekarang dipakai).** Lima alternatif terukur kalah.
   Tidak ada cache top25/weighted untuk 86 video yang dibangun — dua sudut
   pengukuran independen (peringkat puncak 10 video + F1 86 video) sama-sama
   menolaknya.
2. Mengapa mean menang secara mekanistik: gerakan wajah bersifat common-mode
   (40% blok bergerak bahkan tanpa ekspresi). mean mengukur *tingkat*
   perpindahan global wajah; puncak ekspresi muncul sebagai puncak prominence
   di atas tingkat itu. max mengejar satu blok noise, count hanya mengukur
   common-mode, top25 membuang informasi bentuk puncak.
3. Bottleneck spotting **bukan** definisi magnitude — melainkan sinyal POC
   integer itu sendiri (kuantisasi 15 nilai) dan gerakan latar video. Ini
   batas metode pada data 30 fps, bukan bug konfigurasi.

---

## 6. Mekanisme lain yang ikut diuji (2026-10-13, lanjutan)

Menjawab "spotting belum selesai — deep dive SEMUA mekanismenya":

| komponen mekanisme | hasil uji | verdict |
|---|---|---|
| sub-piksel POC (koreksi parabolik, termasuk di puncak tengah) | sintetis OK (0,5px→0,28, 1px→0,99, 2px→1,97); **nyata: 0,150 vs integer 0,146 — tidak ada bedanya** | tidak mengubah peringkat puncak; kuantisasi bukan batas praktis |
| koreksi skala ROI (piksel asli vs piksel resize) | 0,150 vs 0,150 | tidak berpengaruh di CAS(ME)² |
| kegagalan landmark dlib | **0,0% dari 24.709 frame** (10 video) | bukan masalah di CAS(ME)² |
| acuan baseline (abs/lag30/lag10/seq, resep baru, 41 video) | abs **0,3486** vs 0,19/0,17/0,14 | frame-0 menang telak (lagi) |
| internals detektor (5 parameter, 86 video) | KOMBI (topk4+mindur4+uptick0,9+radius200) F1 **0,3451**, menang A/B dua arah (0,3469/0,3437) | menang deteksi longgar; batas onset/offset memburuk (ketat 0,0986, durasi 84) — default fitur tetap BASE |

Mengapa sub-piksel tidak menolong padahal temuan §1 menunjukkan kuantisasi
kasar: faktor pembatas sinyal bukan resolusi pengukuran, melainkan GERAKAN
LATAR (§3: 41% blok sudah bergerak tanpa ekspresi). Memperhalus pengukuran
sinyal yang bising tidak mengubah urutan puncaknya. Batas metode pada data
30 fps ini bersifat informasi (SNR), bukan numerik.

---

## 7. Sinyal Hpoc — fitur M paper yang sebenarnya (2026-10-13, ronde 2)

Plan: `report/plans/2026-10-13-hpoc-spotting-paper-alignment` (isu 01).
Skrip: `scripts/audit_hpoc_casme2.py`. Cache: `output/training/casme2_hpoc_signals`
(86 video, 4 konfigurasi × 4 sinyal × 5 ROI). Resep deteksi DIPAKU sama dengan
audit agregasi (apple-to-apple dengan baseline mean_m F1 0,3192).

### 7.1 Divergensi dari paper Rosiani et al. (2020) yang ditemukan

Membaca teks lengkap paper POC-ABS (DOI 10.22266/ijies2020.1231.48):

1. **Fitur M paper = nilai puncak POC (Hpoc), BUKAN |V| = sqrt(X²+Y²).** Bukti
   di paper: contoh blok 28 dengan XB=2, YB=2 diberi MB28 = 0,46 — sama dengan
   "highest POC value 0,4687" yang ditampilkan, bukan 2,83. Kode kita
   (`vektor.py:37`) menghitung `val_max` lalu membuangnya.
2. **Acuan paper = frame berurutan** (Algoritma 1 baris 4: RF = img(f±1)).
3. **Block size terbaik paper = 5×5** (disapu 5–25).
4. **Blok tanpa gerak dikecualikan dari fitur** (eksplisit di §3.2 paper).
5. Angka 94,3%/95,6% (SVM/KNN) paper = klasifikasi frame-level 10-fold CV di
   CASME II — bukan LOSO dan bukan spotting F1, tidak sebanding dengan angka kita.

### 7.2 Hasil (86 video, 308 GT, cutoff 0,3 kecuali disebut)

| sinyal (global = mean antar ROI) | F1 | F1 ketat |
|---|---|---|
| **b9abs combo: z(mean_m)+z(hpoc_drop_mean)** | **0,3343** | 0,1409 |
| b5abs hpoc_drop_mean (block 5 paper) | 0,3329 | 0,1165 |
| b9abs hpoc_drop_mean | 0,3245 | 0,1054 |
| b9abs mean_m (**baseline sekarang**) | 0,3192 | 0,1282 |
| b9abs frac_mov (Pvector paper, Eq. 6) | 0,3184 | 0,1197 |
| b9abs hpoc_drop_mov (aturan eksklusi paper) | 0,2201 | 0,0446 |
| b9seq * (acuan berurutan paper, semua sinyal) | 0,2141–0,2493 | ≤0,0732 |

Validasi split subjek 2-fold (pilih di train, ukur di test): A→B memilih
**combo** (test F1 0,3262), B→A memilih **hpoc_drop_mean b5abs** (test F1
0,3198) — dua-duanya keluarga Hpoc, dan dua-duanya ≥ baseline 0,3192.
Ini pola yang lebih konsisten daripada semua sweep sebelumnya (yang selalu
memilih pemenang berbeda tanpa arah).

Varian combo per-ROI (z di dalam tiap ROI lalu mean): 0,3113 — lebih lemah;
kombinasi yang menang adalah di level sinyal GLOBAL.

### 7.3 Verdict

1. **Hpoc membawa informasi NYATA dan KOMPLEMENTER terhadap |V|.** Buktinya
   bukan hpoc sendirian menang (0,3245 vs 0,3192 — tipis), melainkan
   z(mean_m)+z(hpoc) mengalahkan KEDUA komponennya (0,3343) dan terpilih di
   kedua fold. Keuntungan +1,5 poin F1 — moderat, bukan terobosan; bottleneck
   SNR gerakan latar (§3) tetap berlaku.
2. **Resep persis paper GAGAL di data 30 fps kita**: acuan berurutan kalah
   jauh untuk KEEMPAT kalinya (sekarang juga untuk Hpoc), dan aturan eksklusi
   blok-diam (hpoc_drop_mov) jauh lebih buruk (0,22). Adaptasi yang benar:
   tetap acuan frame-0 + mean semua blok.
3. **Block 5 tidak diperlukan**: keuntungan b5abs vs b9abs untuk hpoc (0,3329
   vs 0,3245) tidak stabil lintas fold; combo terbaik justru di block 9.
4. **Tindakan**: `SPOT_SIGNAL=mean_m|hpoc|combo` dibuka di
   `process_spotting_pipeline.py` (default mean_m TIDAK berubah — terverifikasi
   bit-identik), diteruskan sebagai `V3_SPOT_SIGNAL` di `run_pipeline_v3.sh`.
   Uji A/B di sisi anxiety: `V3_SPOT_SIGNAL=combo ./scripts/run_pipeline_v3.sh --fresh`.
5. Definisi M fitur (Tabel 4.8 FINAL.pdf) TETAP |V| — yang berubah hanya
   sinyal spotting, bukan vektor fitur per blok.

Skrip: `scripts/probe_spotting_mechanism_casme2.py`,
`scripts/audit_detector_internals_casme2.py`,
`scripts/audit_baseline_recheck_casme2.py`.
Detail internals + baseline: `report/findings/audit-spotting-casme2.md` §11-12.

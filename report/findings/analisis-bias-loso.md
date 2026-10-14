# Akuntansi Bias — LOSO POC-ABS → ROI25 → TabR

Fokus: mengukur dan memisahkan **bias** pada hasil LOSO yang sudah ada
(`convat_apex_anxiety_loso_roi25_reg`, 56 fold, 3 seed), supaya angka
headline tidak dibaca lebih kuat dari yang sebenarnya.

Berkas ini pasangan dari `report/findings/literature-accuracy-drop-2021-2026.md`
(sebab penurunan akurasi). Daftar sitasinya di
`report/documentation/research-papers.md` (bagian "Bias, ambang, dan kalibrasi").

---

## 0. Angka yang dirujuk

Semua angka dihitung ulang dari artefak run, bukan dari ingatan:

| Sumber | Isi |
|---|---|
| `exp/tabr/convat_apex_anxiety_loso_roi25_reg/fold_*/0-evaluation/*/report.json` | 168 report (56 fold × 3 seed), 0 FAILED |
| `fold_*/test_split.csv` + `predictions.npz` | proba & label test per fold |
| `fold_*/per_subject.csv` (via `./run collect`) | 1 baris = 1 subjek × seed |

Level subjek, 56 subjek (25 positif / 31 negatif), baseline mayoritas **0.5536**:

| metrik | nilai |
|---|---|
| accuracy (rata-rata antar seed) | 0.5952 ± 0.0899 |
| accuracy pooled, CI Wilson 95% | 0.6071, **0.4763–0.7242** |
| balanced accuracy | 0.5776 ± 0.0847 |
| MCC | **+0.1706 ± 0.1826** |
| sensitivity (anxiety_tinggi) | 0.4133 |
| specificity | 0.7419 |

Catatan penting: CI accuracy **memuat** baseline mayoritas (0.5536). Jadi
"59,5% vs 55,4%" belum terbukti lebih baik dari menebak kelas mayoritas.

---

## 1. Ringkasan: empat bias, urut dampak

| # | Bias | Besar | Akibat pada pembacaan |
|---|---|---|---|
| 1 | **Komposisi / paradoks Simpson** | di **setiap** grup model **di bawah** baseline grup sendiri (−0.056 dan −0.158) | keunggulan pooled +4,2 poin adalah artefak komposisi, bukan kemampuan |
| 2 | **Metrik** | accuracy 0.5952 vs MCC +0.1706; MCC per seed −0.020 s/d +0.345 | accuracy menutupi bahwa satu seed setara tebak acak |
| 3 | **Prediksi** | laju positif diprediksi 0.2679 vs sebenarnya 0.4464 → **−0.1786** | model condong menebak "rendah"; sensitivity 0.41 vs specificity 0.74 |
| 4 | **Ambang & kalibrasi** | ambang dipatok 0.5; proba terkompresi (bin 0.08 → laju nyata 0.42) | ambang 0.5 belum tentu titik kerja yang benar |

---

## 2. Bias 1 — Komposisi (paradoks Simpson)

`group` = grup fase subjek, diturunkan dari kolom `condition`:
`before_sama` (kondisi before = after) dan `before_berubah` (berubah).
Komposisinya sangat tidak seimbang antar grup:

| grup | n subjek | n positif | laju positif |
|---|---|---|---|
| `before_sama` | 38 | 24 | 0.6316 |
| `before_berubah` | 18 | 1 | 0.0556 |

Hasil model per grup (proba dirata-rata antar seed, 1 baris/subjek):

| grup | n | accuracy | baseline grup | selisih | MCC |
|---|---|---|---|---|---|
| `before_sama` | 38 | 0.4737 | 0.6316 | **−0.1579** | +0.0179 |
| `before_berubah` | 18 | 0.8889 | 0.9444 | **−0.0556** | −0.0588 |

**Di kedua grup model kalah dari baseline mayoritas grup itu sendiri**, padahal
accuracy pooled (0.6071) lebih tinggi dari baseline mayoritas global (0.5536).
Itu persis paradoks Simpson: angka pooled terlihat menang karena mencampur dua
prior kelas yang berbeda (`before_sama` 63% positif vs `before_berubah` 5,6%
positif). Menang di pooled = menang karena komposisi, bukan karena sinyal.

### Kenapa ini tidak boleh "diperbaiki" dengan memakai grup

Grup diturunkan dari `condition`, dan `condition` **adalah label**. Memakai grup
sebagai fitur, atau untuk mengoreksi prior, berarti memasukkan label ke input —
kebocoran. Jadi analisis per grup hanya **alat diagnosis**, bukan jalur
perbaikan. Ini sudah ditulis sebagai catatan di output `./run collect`.

---

## 3. Bias 2 — Metrik

Di komposisi 25/31, accuracy dan MCC tidak sepakat:

| metrik | pooled | per seed (0 / 1 / 2) |
|---|---|---|
| accuracy | 0.6071 | 0.6071 / 0.5000 / 0.6786 |
| balanced accuracy | 0.5832 | 0.5832 / 0.4903 / 0.6594 |
| MCC | +0.1869 | **+0.1869 / −0.0196 / +0.3446** |

- **Seed 1 MCC −0.0196** = setara tebak acak, walau accuracy-nya 0.5000
  (di bawah baseline mayoritas 0.5536). Accuracy menyembunyikan ini karena
  terlihat "cuma 5 poin di bawah baseline".
- Rentang MCC antar seed (−0.02 s/d +0.34) jauh lebih lebar dari rentang
  accuracy (0.50 s/d 0.68). MCC lebih jujur soal ketidakstabilan.
- MCC pooled +0.1869 = korelasi lemah, bukan bukti model belajar kondisi.

Literatur sepakat accuracy harus didampingi ukuran tahan-imbalance; MCC
dipromosikan sebagai pengganti ROC-AUC untuk klasifikasi biner
(Chicco & Jurman 2023). Tapi ada bantahan yang harus dikutip juga: MCC sendiri
terdegradasi di data sangat tak seimbang (Pattern Recognition Letters 2020).
Karena itu laporan ini menampilkan **tiga** ukuran sekaligus (accuracy,
balanced accuracy, MCC), bukan menukar satu dengan satu.

---

## 4. Bias 3 — Prediksi (model condong ke satu kelas)

| | nilai |
|---|---|
| laju positif SEBENARNYA | 0.4464 |
| laju positif yang DIPREDIKSI | 0.2679 |
| **bias (prediksi − sebenarnya)** | **−0.1786** |

Per seed: −0.1786 / −0.0357 / −0.1429 — konsisten negatif di ketiga seed.
Di tingkat baris (168 baris): 0.3274 vs 0.4464 → −0.119.

Artinya model sistematis **kurang berani menebak `anxiety_tinggi`**. Ini
konsisten dengan sensitivity 0.4133 vs specificity 0.7419 (selisih 33 poin).
Dua sebab yang mungkin, dan keduanya bisa dipisah:

1. **Ambang 0.5 belum cocok** untuk prior 45/55 → perbaikan: pilih ambang di val
   (bagian 5).
2. **Model memang tidak punya sinyal positif** → perbaikan tidak mungkin lewat
   ambang; ini kembali ke masalah representasi.

Yang penting: **jangan** menyimpulkan "model bagus karena specificity tinggi".
Specificity tinggi di sini sebagian besar hasil dari menebak kelas mayoritas.

---

## 5. Bias 4 — Ambang dan kalibrasi

### 5.1 Ambang

TabR menghitung label dari proba dengan ambang tetap 0.5
(`lib/metrics.py`: `labels = np.round(probs)`), dan 0.5 itu arbitrer. Ambang
yang jujur harus dipilih di data yang tidak dipakai mengukur (val).

**Gap yang ditemukan:** `run_loso.py` menyimpan `test_split.csv` tapi **tidak**
menyimpan urutan baris val. Akibatnya ambang pilihan-val **tidak bisa
direkonstruksi** dari artefak run lama. Sudah diperbaiki: `run_loso.py` sekarang
juga menulis `val_split.csv` per fold, dan `collect_loso_results.py` menghitung
ambang Youden per fold di val lalu menerapkannya ke test fold itu
(leak-free). Untuk run lama, bagian ini otomatis melaporkan "belum bisa dihitung".

### 5.2 Kalibrasi

Binning proba pooled (168 baris) menunjukkan **monoton tapi terkompresi**:

| bin proba | n | rata-rata proba | laju positif nyata |
|---|---|---|---|
| [0.0, 0.2) | 33 | 0.080 | 0.424 |
| [0.2, 0.4) | 42 | 0.305 | 0.310 |
| [0.4, 0.6) | 60 | 0.485 | 0.467 |
| [0.6, 0.8) | 18 | 0.689 | 0.556 |
| [0.8, 1.01) | 15 | 0.922 | 0.667 |

Urutan naik (model mengurutkan dengan benar) tapi skalanya jauh dari diagonal:
proba 0.08 seharusnya berarti ~8%, kenyataannya 42%. Proba 0.92 seharusnya
~92%, kenyataannya 67%. Model **under-confident** dan probanya tidak bisa
dibaca sebagai peluang.

Perbaikan: kalibrasi Platt (sigmoid) di val. Isotonic **tidak** dipakai di sini
karena butuh > ~1000 sampel; di 56 subjek isotonic overfit (sklearn docs
§1.16.3.2). Platt setelah undersampling juga terbukti paling tahan saat model
mendorong proba ke ekstrem (arXiv:2410.18144, 2024).

---

## 6. Bias 5 — Varians seed (ketidakstabilan)

Seed hanya berbeda inisialisasi, tapi:

| seed | accuracy | MCC |
|---|---|---|
| 0 | 0.6071 | +0.1869 |
| 1 | 0.5000 | −0.0196 |
| 2 | 0.6786 | +0.3446 |

Rentang accuracy antar seed = **17,9 poin**. Sebagian rentang itu berasal dari
satu subjek: di grup `before_berubah` (18 subjek, hanya **1** positif —
`dewita_anggraini`), seed 2 menebaknya positif pada proba **0.540005**, yaitu
0,04 di atas ambang; seed 0 dan 1 menebaknya negatif. Satu keputusan berbatas
tipis menggeser accuracy grup itu 5,6 poin.

Konsekuensi: **selisih antar-konfigurasi yang kurang dari ~10 poin tidak bisa
dibedakan dari derau** di N=56 dengan 1 label/subjek. Ini pagar untuk semua A/B
berikutnya. (Rata-rata pooled 3 seed sendiri cukup stabil: membuang subjek itu
mengubah accuracy pooled 0.5952 → 0.6000.)

---

## 7. Mitigasi

### Sudah diimplementasikan (tanpa training)

1. `collect_loso_results.py` sekarang melaporkan **MCC + balanced accuracy**
   di samping accuracy, **bias prediksi** (laju positif prediksi vs nyata), dan
   **tabel per grup dengan baseline grup sendiri** — jadi paradoks Simpson
   langsung kelihatan tiap kali `./run collect` dijalankan, bukan perlu
   dihitung manual lagi.
2. `run_loso.py` menulis `val_split.csv`, dan `collect_loso_results.py` bisa
   memilih ambang di val per fold (aktif otomatis setelah re-run LOSO).
3. Output collector menegaskan grup hanya alat diagnosis (larangan pakai grup
   sebagai fitur/koreksi prior).

### Perlu keputusan/jalankan sendiri

| Mitigasi | Alasan | Status |
|---|---|---|
| Laporkan MCC + balanced accuracy sebagai angka utama, bukan accuracy | accuracy bias di 45/55 (Chicco & Jurman 2023) | siap, sudah masuk laporan |
| Ambang dari val, bukan 0.5 | 0.5 arbitrer; bias prediksi −0.18 | kode siap, butuh re-run |
| Kalibrasi Platt di val | proba terkompresi, under-confident | belum; Platt (bukan isotonic) |
| `[data] score = "cross-entropy"` sebagai pemilihan epoch | TabR hanya punya `accuracy`/`cross-entropy`/`rmse` sebagai score; cross-entropy proper scoring rule, tidak bias ke mayoritas | usul A/B, 1 baris config |
| A/B apa pun harus > ~10 poin untuk bisa dipercaya | varians seed 17,9 poin di N=56 | aturan pembacaan |
| Jangan pakai `group` sebagai fitur/prior | `group` turunan label → bocor | larangan tetap |

### Yang tidak bisa diperbaiki di sini

- **Prior shift antar subjek.** Distribusi kelas berbeda antar grup fase.
  Koreksi prior butuh estimasi prior target; di N=56 per fold estimasinya
  terlalu berisik, dan label target tidak boleh dipakai (d2l §4.7).
- **Lebih banyak baris tidak menambah sampel.** Label milik subjek, jadi
  menambah frame/clip tidak menambah unit independen. Yang menambah sampel
  adalah menambah **subjek**.
- **Bias metrik level frame.** Sudah ditandai diagnostik di laporan; jangan
  dipakai sebagai performa.

---

## 8. Implikasi ke target 70%

Target "≥70% akurasi test dan gap train–test kecil" tidak bisa dinilai dari
angka accuracy sendirian, karena:

1. Accuracy pooled 0.6071 pun **di bawah baseline grup di kedua grup**
   (paradoks Simpson) → bukan bukti belajar.
2. CI 0.4763–0.7242 memuat baseline 0.5536 → belum signifikan.
3. Varians seed 17,9 poin → 70% tidak bisa dibedakan dari 60% di N=56.

Jadi angka yang layak dikejar bukan "accuracy 70%", tapi
**MCC > 0 dengan CI tidak memuat 0, dan tidak di bawah baseline grup di grup
mana pun**. Selama gerbang within-subject (`scripts/within_subject_test.py`)
masih menunjukkan sinyal setara efek sesi (onset 0.583 p=0.264; netral 0.528
p=0.473), menaikkan angka lewat konfigurasi atau ambang hanya memindahkan bias,
bukan menambah sinyal.

---

## 9. Reproduksi

```bash
# laporan + akuntansi bias (level subjek)
./run collect --exp convat_apex_anxiety_loso_roi25_reg \
  --features experiments/features/apex/poc_abs_roi_signals_neutral_temporal.pkl \
  --row-unit subject

# setelah re-run LOSO (val_split.csv terisi), kolom ambang-dari-val ikut muncul
./run loso --dataset convat_apex_anxiety_loso_roi25_reg \
  --features experiments/features/apex/poc_abs_roi_signals_neutral_temporal.pkl \
  --aggregate subject --subject-norm none \
  --config experiments/configs/tabr_loso_roi25_reg.toml
```

Keluaran: `output/training/<exp>/{summary.md,summary.csv,per_subject.csv}`.

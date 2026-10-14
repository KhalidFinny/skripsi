# Deep Dive — Spotting & Feature Extraction untuk Video Lapangan (noise gerakan)

> Tanggal: 2026-10-13. Pertanyaan: metode spotting/fitur mana yang tahan
> terhadap gerakan kepala/latar pada video LAPANGAN 30 fps (bukan lab), untuk
> dijadikan kandidat pengganti/pelengkap mean_m POC-ABS. Sumber: paper,
> GitHub, artikel teknis (bukan ingatan).

## TL;DR (urutan rekomendasi)

1. **MDMD + global-flow cancellation** — satu-satunya metode dengan mekanisme
   EKSPLISIT menolak gerakan kepala/latar, dan kodenya publik. Cocok di atas
   sinyal blok POC yang sudah kita punya. **Prioritas tertinggi.**
2. **Rigid motion compensation (face alignment + subtract dominant global
   flow)** — prasyarat nomor 1; sering jadi penyebab utama noise. Biaya rendah.
3. **DS-OMMA / dense-sampling** — meredam noise dengan merata-ratakan banyak
   sampel; valid di CASME2/CAS(ME)² tapi BUKAN terbukti di video lapangan.
4. Eulerian Video Motion Magnification (EMM) — penguat pra-sinyal; rapuh pada
   noise latar kalau tidak di-align dulu.
5. Deep apex spotter (SpotFormer, attention) — TIDAK layak: butuh data besar
   (86 video kita tidak cukup) dan tidak ada bukti di video lapangan.

---

## Bottleneck kita (sudah terukur, jangan di-debat ulang)

- CAS(ME)² & data anxiety: ~41% blok bergerak TANPA ekspresi → sinyal spotting
  tenggelam oleh gerakan non-ekspresi pada 30 fps lapangan.
- Sinyal `combo` (z(mean_m)+z(Hpoc)) yang MENANG di CAS(ME)² (lab, mikro
  terpose) justru MENURUNKAN akurasi di data anxiety (LOSO-44 38–42% vs
  mean_m 45,83% pooled-56). Pelajaran: **lab ≠ lapangan**; metode harus punya
  mekanisme anti-gerakan-global, bukan sekadar sinyal lebih halus.

---

## 1. MDMD — Main Directional Maximal Difference (PALING RELEVAN)

- **Apa:** untuk frame `Fi`, hitung optical flow `Fi-k→Fi` (HC) dan `Fi-k→Fi+k`
  (HT). Ubah ke polar (ρ, θ). Bagi arah θ ke `a` bin; **Main Direction Θ** =
  bin dengan vektor terbanyak. Ambil selisih magnitude `ρ_HCM − ρ_HTM` pada
  vektor arah Θ, urutkan, dan **`di` = rata-rata sepertiga teratas** selisih
  itu. Rangkaian `di` sepanjang video = sinyal spotting.
- **Kenapa tahan gerakan kepala/latar:** ide intinya — saat ekspresi terjadi,
  otot bergerak ke satu arah lalu KEMBALI (onset→apex→offset), sehingga arah
  gerakan dominan BERBALIK antara HC dan HT; gerakan kepala/global tidak
  memiliki pola balik yang tajam di jendela `2k`. Memakai *maximal difference
  pada arah utama* (bukan magnitude mentah) menekan komponen gerakan seragam
  (translasi/global) yang tidak berbalik cepat.
- **Validasi:** Neurocomputing 2017 (Wang dkk), "more robust than
  state-of-the-art" di CAS(ME)². Kode MEGC2020: github.com/HeyingGithub/
  Baseline-project-for-MEGC2020_spotting (Matlab+Python; `preprocess.py`
  crop wajah via dlib — SAMA dengan pipeline kita). Param MEGC: 6×6 blok,
  4 arah, k=12 (micro) / 39 (macro) untuk CAS(ME)².
- **Catatan jujur:** F1 baseline MEGC di CAS(ME)² micro hanya 0,0082 —
  spotting micro memang SANGAT sulit. Angka kita (F1 0,32–0,33 di CAS(ME)²
  macro-ish spotting) SUDAH jauh di atas baseline micro MEGC. Jadi MDMD bukan
  "lebih akurat", melainkan **lebih tahan-noise** — yang justru bottleneck kita.
- **Implementasi di POC kita:** `features_extraction/vektor.py` sudah
  menghasilkan per-blok `delta x, delta y` + arah relatif `oX, oY` → ρ & θ
  per blok tersedia. MDMD butuh flow di DUA jendela (HC, HT) per frame. Kita
  perlu POC antara frame `i-k`↔`i` dan `i-k`↔`i+k` (POC-ABS sekarang hanya
  frame-0↔i). **Kompleksitas: SEDANG** (perlu referensi multi-frame, bukan
  hanya frame-0). Ini alasan kuat mengapa combo/Hpoc gagal — ia masih
  frame-0-referensial dan tidak memakai pola balik arah.

## 2. Rigid Motion Compensation (PRASYARAT, biaya RENDAH)

- **Apa:** stabilisasi/align wajah per frame (dlib 68 → similarity transform),
  lalu sebelum spotting, kurangi **dominant global flow** (median/affine fit
  antar frame) dari medan flow. Sisa = gerakan LOKAL (ekspresi).
- **Kenapa:** gerakan kepala adalah gerakan GLOBAL/rigid — ia menggerakkan
  SEMUA blok serempak ke arah sama. Menguranginya menghilangkan sumber noise
  terbesar tanpa menyentuh sinyal ekspresi lokal. MDMD sendiri melakukan
  align+crop lebih dulu (preprocess.py).
- **Kode:** standar (OpenCV `estimateAffinePartial2D` / `cv2.phaseCorrelate`
  untuk global shift; dlib alignment sudah kita pakai). Tidak butuh repo
  khusus.
- **Kompleksitas: RENDAH.** Ini kandidat "fix root cause" pertama: sebelum
  mengganti sinyal magnitude, hilangkan komponen globalnya. Bisa diuji cepat
  sebagai A/B: `mean_m` pada flow yang sudah dikurangi global-median per frame.

## 3. DS-OMMA / Dense Sampling (MEREDAM noise via rata-rata)

- **Apa:** Dense Sampling Optical-flow Mean Magnitude & Angle — partisi wajah
  ke ROI adaptif, ambil mean magnitude+angle dari sampel PADAT (banyak titik).
- **Kenapa membantu:** dense sampling mengurangi pengaruh noise gerakan
  kepala & iluminasi dengan merata-ratakan banyak sampel (noise acak saling
  meniadakan; sinyal otot yang konsisten bertahan).
- **Validasi:** ICMEW 2018 — DS-OMMA > LBP-TOP & MDMO di CASME2 & CAS(ME)².
- **Catatan jujur:** validasi di LAB, bukan lapangan. Kita sudah melakukan
  hal serupa (mean per ROI). Nilai tambah: menambah **angle** sebagai kanal
  fitur (arah), yang kita belum pakai sebagai fitur — MDMD menunjukkan arah
  lebih informatif daripada magnitude saja. **Kompleksitas: RENDAH–SEDANG.**

## 4. LBP-TOP / HWP / Optical Strain (alternatif fitur, validasi LOSO)

- **LBP-TOP** (Zhao & Pietikäinen TPAMI 2007): tekstur spatio-temporal;
  baseline klasik, banyak yang mengalahkannya. Spotting LBP-χ² (Moilanen
  2014) pakai jendela geser + jarak Chi-square. **Bukan flow** → kebal
  terhadap cara hitung flow, tapi tetap peka gerakan global.
- **Optical strain** (Shreve 2011): deformasi lokal dari flow; dipakai
  membedakan macro vs micro. Sensitif terhadap kualitas flow.
- **Nilai untuk kita:** sebagai FITUR pelengkap (bukan pengganti POC) untuk
  memperkaya representasi per event; keduanya punya hasil LOSO di
  CASME2/CAS(ME)². **Kompleksitas: SEDANG.** Prioritas di bawah MDMD.

## 5. Eulerian Video Motion Magnification (EMM)

- **Apa:** dekomposisi spasial + band-pass temporal, amplifikasi pita frekuensi
  gerakan halus (dipakai Li 2017 untuk micro).
- **Kenapa berisiko:** EMM menguatkan SEMUA gerakan halus TERMASUK latar/
  kepala kalau wajah tidak di-align dulu. Di video lapangan 30 fps kita,
  amplifikasi noise bisa memperburuk SNR, bukan memperbaikinya.
- **Kompleksitas: SEDANG–TINGGI.** Coba HANYA setelah motion compensation (2).

## 6. Deep apex/interval spotter (SpotFormer, attention) — TIDAK LAYAK

- SpotFormer (multi-scale spatio-temporal transformer) & attention apex
  spotter melaporkan hasil di CAS(ME)²/SAMM, tapi (a) butuh data training
  besar — kita hanya punya 86 video CAS(ME)² / 560 video anxiety; (b) tidak
  ada bukti di video lapangan; (c) mengubah pipeline jadi deep = keluar dari
  batas tesis POC-ABS. **Ditolak untuk bottleneck kita.**

---

## Hubungan dengan "fitur 335 / 300-an" (combo seharusnya bekerja di sini)

Deskriptor temporal kita per lintasan onset→apex→offset = `{peak, ttp, rise,
fall, auc}` × sinyal dasar per ROI. Set penuh = 335 fitur; `rise` saja = 55;
magnitude-only = 125. Temuan penting dari deep dive:

- **Set 335-fitur penuh adalah tempat yang benar untuk menguji sinyal baru.**
  Kegagalan `combo` kemarin diuji pada protokol fold-first + representasi
  `rise`, bukan pada 335. TAPI kegagalan itu lebih fundamental: sinyal combo
  masih frame-0-referensial dan tidak memakai pola balik arah (MDMD),
  sehingga di video lapangan ia tetap menangkap gerakan latar.
- **Sebelum menambah fitur, perbaiki SINYAL SUMBERNYA.** Menambah deskriptor
  (335) di atas sinyal yang sudah tercemar gerakan global hanya menambah
  dimensi noise — persis hasil ablasi (SEMUA 335 BA 0,6389 < rise 55 0,8333
  pada gate lama). Urutan yang benar: (2) motion compensation → (1) MDMD/
  arah → baru uji ulang set 335.

## Rekomendasi langkah (berurutan, masing-masing bisa di-A/B)

1. **Global-flow cancellation + `mean_m`** (biaya rendah): A/B cepat.
2. **MDMD-style signal** (arah utama + maximal difference, multi-frame ref):
   kandidat pengganti sinyal spotting yang sesungguhnya anti-noise.
3. **Tambah kanal ANGLE** ke deskriptor (DS-OMMA-style), uji set 335 penuh.
4. (opsional) EMM setelah compensation stabil.

Tiap langkah diuji dengan protokol fold-first (V3_PRESPLIT=1) yang sama supaya
angka bisa dibandingkan apple-to-apple dengan mean_m (45,83%) dan combo
(38–42%) yang sudah tercatat.

## Sumber

- Wang S-J dkk. 2017. *A main directional maximal difference analysis for
  spotting facial movements from long-term videos.* Neurocomputing 230:382-389.
- He Y, Wang S-J dkk. 2020. *Spotting Macro- and Micro-expression Intervals
  in Long Video Sequences* (MEGC2020 baseline). arXiv:1912.11985 + kode
  github.com/HeyingGithub/Baseline-project-for-MEGC2020_spotting.
- Liu Y-J dkk. 2018. *DS-OMMA: ROI-based spatio-temporal feature.* ICMEW.
- Moilanen dkk. 2014. LBP-χ² spotting (ICPR); Zhao & Pietikäinen 2007 LBP-TOP
  (TPAMI); Shreve dkk. 2011 optical strain (FG).
- Liong dkk. 2018. *Less is more: ME recognition from apex frame* (Bi-WOOF).
- Duque dkk. 2018. Riesz pyramid spotting (WACV); Li 2017 EMM untuk micro.

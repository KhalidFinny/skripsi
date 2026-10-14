# Ringkasan Riset — Deteksi Kecemasan dari Video Wajah

Dokumen ini merangkum **seluruh perjalanan penelitian** dalam satu tempat: apa
yang dikerjakan, kenapa dikerjakan, apa yang diperbaiki, dan hasil angkanya
(training / validasi / pengujian) sampai run paling baru.

Ditulis dengan bahasa sederhana supaya bisa dibaca tanpa latar belakang teknis.
Istilah yang tidak bisa dihindari dijelaskan di **Kamus singkat** di bagian akhir.

**Terakhir diperbarui:** 2026-10-13

---

## 1. Penelitian ini tentang apa

Kita ingin tahu apakah **gerakan halus wajah** bisa dipakai untuk membaca
**tingkat kecemasan** seseorang.

Alurnya seperti ini:

```diagram
┌────────────────────┐
│  Video wajah       │
└─────────┬──────────┘
          ▼
┌────────────────────┐
│  Potong wajah      │  mata-alis kiri, mata-alis kanan, mulut
└─────────┬──────────┘
          ▼
┌────────────────────┐
│  Ukur gerakan      │  POC-ABS (antar-frame)
└─────────┬──────────┘
          ▼
┌────────────────────┐
│  Jadi tabel angka  │  satu baris = satu sampel
└─────────┬──────────┘
          ▼
┌────────────────────┐
│  Model TabR        │  → cemas tinggi / cemas rendah
└────────────────────┘
```

Yang jadi bahan penilaian:

| Hal | Nilai |
|---|---|
| Jumlah subjek | 56 orang |
| Jumlah sesi | 2 (sebelum ujian dan sesudah ujian) |
| Sumber data | direkam sendiri, dilabeli pakar |
| Kelas | `anxiety_tinggi` dan `anxiety_rendah` |

---

## 2. Cara membaca hasil di dokumen ini

Tiga angka yang selalu muncul di setiap run:

| Istilah | Artinya | Cara membacanya |
|---|---|---|
| **Train** | Akurasi pada data yang **dipakai belajar** | Tinggi itu wajar. Terlalu tinggi = hafalan |
| **Val** | Akurasi pada data yang **dipakai memilih model** | Kalau jauh di bawah train = model mulai hafal |
| **Test** | Akurasi pada **orang yang belum pernah dilihat** | **Ini angka yang menentukan** |

> **Penting.** Kalau **test lebih rendah dari baseline**, artinya model belum
> lebih pintar dari sekadar menebak kelas terbanyak. Baseline = kalau semua
> orang ditebak "cemas tinggi", berapa persen yang benar.

---

## 3. Timeline — kapan, apa yang dikerjakan, hasil, masalah

Tabel di bawah **kronologis**: makin ke bawah makin baru. Cara baca kolomnya:

| Kolom | Isinya |
|---|---|
| **Waktu** | Kapan kejadiannya (dari tanggal commit / jam log) |
| **Yang dikerjakan** | Apa yang dilakukan saat itu |
| **Hasil** | Angka atau keadaan setelah dikerjakan |
| **Masalah** | Apa yang ketahuan salah/kurang saat itu |
| **Yang diubah → hasil baru** | Perbaikan untuk masalah itu, dan hasil setelah diperbaiki |

Entri pertama belum punya kolom terakhir karena belum ada yang perlu diperbaiki.

---

### Era 1 — Membangun dari nol (2025-09 → 2026-08)

| Waktu | Yang dikerjakan | Hasil | Masalah | Yang diubah → hasil baru |
|---|---|---|---|---|
| 2025-09-13 03:07 | Commit pertama: ekstraksi frame dari video | kerangka proyek ada | belum ada model | 2025-09-18: tambah potong wajah |
| 2025-12-20 11:55 | Tambah POC-ABS, kuadran, vektor gerak | cara mengukur gerakan halus | belum pernah diuji | 2025-12-21: tambah model TabR |
| 2025-12-21 18:28 | Model TabR kustom (LitTabR v1–v21) | model bisa dilatih | akurasi 50–60% = menebak kelas mayoritas | 2026-04-06: ganti ke TabR resmi |
| 2026-02-14 14:39 | Tambah spotting + analitik q1–q5 | bisa mendeteksi momen gerakan | — | — |
| 2026-02-25 00:10 | Pendekatan baru deteksi apex | dipakai sampai sekarang | — | — |
| 2026-04-06 21:22 | Ganti ke TabR resmi (Yandex) | dasar model yang dipakai sekarang | — | — |
| 2026-05-18 00:48 | Merge PR #1 (apex/v3) | kode tergabung | — | — |
| 2026-08-26 10:07 | Bersihkan kode mati | repo lebih rapi | — | — |

---

### Era 2 — Audit dan perbaikan split (2026-08-25 → 2026-09-01)

| Waktu | Yang dikerjakan | Hasil | Masalah | Yang diubah → hasil baru |
|---|---|---|---|---|
| s/d 2026-08-25 | Baseline TabR resmi, split acak | train 97,36% / val 75,65% / **test 74,28%** | **BOCOR**: orang yang sama ada di data latih dan data uji → angka palsu tinggi | 2026-08-31: split diganti subjek-disjoint |
| 2026-08-31 | Split subjek-disjoint (392 fitur) | **test 61,23%** | angka turun 13 poin, tapi baru ini yang jujur | 2026-09-01: coba beberapa varian fitur |
| 2026-09-01 | Uji varian fitur 196 / 608 / roi25 / 392 ulang | 59,98% / 58,60% / **63,37%** / 62,71% | roi25 terbaik di split ini | 2026-09-17: diuji ulang dengan LOSO → tidak bertahan |

> **Kenapa ini penting.** Semua angka sebelum 2026-08-31 tidak sah. Model
> sebenarnya tidak sepintar yang terlihat — sebagian "kepintaran" itu karena dia
> sudah pernah melihat orang yang sama.

---

### Era 3 — Evaluasi jujur dengan LOSO (2026-09-17 → 2026-09-29)

| Waktu | Yang dikerjakan | Hasil | Masalah | Yang diubah → hasil baru |
|---|---|---|---|---|
| 2026-09-17 11:41 | LOSO 392, dihitung per frame | frame acc 60,41% | **metrik tidak bisa ditafsirkan**: 1 subjek per fold, jadi test tiap fold cuma 1 kelas | 2026-09-24: metrik dipindah ke **level subjek** |
| 2026-09-28 12:00 | LOSO roi25, level subjek, 56 fold × 3 seed | **test 55,36% = baseline 55,36%**, AUC 51,91% | model tidak lebih baik dari menebak | 2026-09-29: cari tahu apakah sinyalnya memang tidak ada |
| 2026-09-29 10:53 | Uji model sederhana (logistik) di fitur yang sama | AUC 52,52%, p = 0,28 | **tidak ada sinyal** di fitur roi25 | 2026-09-29: coba agregasi level subjek |
| 2026-09-29 11:23 | Eksperimen agregasi level subjek | 44,05% — **di bawah acak** | memperkuat: masalahnya di fitur, bukan di model | 2026-10-06: mulai perbaikan representasi fitur |

---

### Era 4 — Perbaikan metodologi (2026-10-06 → 2026-10-08)

| Waktu | Yang dikerjakan | Hasil | Masalah | Yang diubah → hasil baru |
|---|---|---|---|---|
| 2026-10-06 09:55 | Baseline netral per subjek + fitur temporal | acuan lebih adil | acuan lama (frame onset) ternyata artefak sesi | 2026-10-07: uji ulang dengan acuan baru |
| 2026-10-07 18:43–23:56 | Tiga run manual POC-only | arah sinyal mulai terlihat | masih belum signifikan | 2026-10-08: uji gerbang pada dataset lama |
| 2026-10-08 16:36 | Uji gerbang dalam-subjek | gerbang mulai terukur | dataset lama masih dari klip rusak | 2026-10-09: validasi tahap spotting |

---

### Era 5 — Validasi spotting CAS(ME)² (2026-10-09 → 2026-10-10)

Tahap spotting = menemukan **di frame mana** gerakan halus terjadi. Diuji pakai
dataset publik CAS(ME)² yang punya jawaban benar.

| Waktu | Yang dikerjakan | Hasil | Masalah | Yang diubah → hasil baru |
|---|---|---|---|---|
| 2026-10-09 09:11 | Siapkan CAS(ME)² (97 video tersedia, 86 dipakai benchmark) | data uji siap | klaim "bisa menemukan ekspresi mikro" belum pernah diuji | 2026-10-09 09:48: smoke test |
| 2026-10-09 09:48 | Smoke test spotting | pipeline jalan | — | 2026-10-09 15:03: uji skor peringkat |
| 2026-10-09 15:03 | Bandingkan skor peringkat puncak | terbaik F1 0,17 | semua skor lemah | 2026-10-09 16:51: coba klasifikasi jendela |
| 2026-10-09 16:51–16:54 | Klasifikasi jendela 64 & 96 frame | F1 **0,37** (w64) / **0,43** (w96) | masih banyak deteksi palsu | 2026-10-09 17:24: audit menyeluruh |
| 2026-10-09 17:24–19:42 | Audit: smoothing, transformasi sinyal, grid detektor, agregasi, sweep jendela | F1 naik ke **0,32** (top_k=4) | plafon ~0,20–0,32, tidak naik lagi | 2026-10-09 19:42: benchmark final + diagnosis |
| 2026-10-09 19:42 | Benchmark final 86 video | F1 0,20 (top_k=1) → **0,32** (top_k=4) | **pemilihan puncak** yang gagal, bukan sinyalnya | 2026-10-10 07:08: regenerasi pipeline |
| 2026-10-10 07:04 | Sanity check regime 60 fps | konfigurasi terverifikasi | — | — |
| 2026-10-10 07:08 → 10:10 | Regenerasi pipeline dengan spotting diperbaiki | event/sample **12,7 → 4,8**; F1 0,164 → **0,319** | event lama datang dari klip rusak | 2026-10-10 11:49: latih ulang dengan fitur baru |
| 2026-10-10 11:49 | LOSO dengan fitur `rise` | **test 48,21%** | masih di bawah baseline | 2026-10-11: run bersih dari nol |

---

### Era 6 — Run bersih dan temuan utama (2026-10-11)

| Waktu | Yang dikerjakan | Hasil | Masalah | Yang diubah → hasil baru |
|---|---|---|---|---|
| 2026-10-11 19:37–20:44 | Beberapa iterasi pipeline v3 | pipeline makin stabil | run sebelumnya terputus di tengah → data `before` tidak lengkap | 2026-10-11 20:45: hapus semua output, run dari nol |
| 2026-10-11 20:45:55 | **Run bersih penuh** stage 1–7 dari nol | 560/560 sample; 2.667 event; 63.413 baris | — | — |
| 2026-10-11 21:47 | Uji gerbang dalam-subjek | per-frame BA 0,639 (p 0,065); **`rise` BA 0,750 (p 0,010)** | per-frame belum signifikan | `rise` dipakai sebagai representasi utama |
| 2026-10-11 21:51 | LOSO `run2` | train 72,06% / val 49,89% / **test 47,62%** | AUC 0,398 (di bawah acak) | 2026-10-12: coba learning rate & per-frame |
| 2026-10-11 23:34 | LitTabR per-frame (metode asli) | test level subjek **41,07%** | lebih buruk dari jalur TabR resmi | kembali ke TabR resmi |

> **Temuan terpenting ada di 2026-10-11 21:47.** Uji paling bersih — orang yang
> sama, wajah yang sama, hanya beda sesi — memberi **BA 0,750, p 0,010**. Artinya
> mendeteksi **perubahan** kondisi dalam diri orang berhasil, sedangkan menebak
> tingkat kecemasan **orang baru** tidak.

---

### Era 7 — Model siap pakai, arah STATE, dan proposal (2026-10-12 → 2026-10-13)

| Waktu | Yang dikerjakan | Hasil | Masalah | Yang diubah → hasil baru |
|---|---|---|---|---|
| 2026-10-12 09:55 | Kumpulkan hasil LitTabR per-frame | test level subjek 41,07% | jalur ini kalah | kembali ke TabR resmi |
| 2026-10-12 13:36–13:37 | Run TabR resmi per-frame & `rise`, lr 3e-4 | test 49,13% / 48,21% | 73–89% fold berhenti di epoch 0 (tidak belajar) | 2026-10-12 14:01: pipeline STATE/session |
| 2026-10-12 14:01:47 | **Pipeline STATE/session** (semua sesi before+after) | stage 1–7 jalan | pertanyaan diubah: bukan "orang ini cemas?" tapi "kondisinya berubah?" | 2026-10-12 15:06: hasil keluar |
| 2026-10-12 15:00–15:06 | Gerbang v3 + LOSO STATE | gerbang `rise` **BA 0,750, p 0,010**; LOSO train 89,90% / val 62,50% / **test 54,46%** | test masih di bawah baseline 57,14% | 2026-10-12 16:17: simpan model final |
| 2026-10-12 16:17–16:26 | Simpan model final + skrip prediksi | model bisa memuat & memprediksi; uji 3 subjek berhasil | model dilatih semua data (tanpa test) — memang begitu tujuannya | — |
| 2026-10-12 → 13 | Proposal: BAB I, BAB II, 9 gambar baru, tabel 28 paper | proposal 24 halaman, kompilasi bersih | 7 dari 28 sitasi lama bermutu rendah | diganti sumber yang sah + tautan gratis |

---

### Ringkasan timeline dalam 1 layar

| Kapan | Tonggak |
|---|---|
| 2025-09-13 | Proyek mulai |
| 2025-12-20 | POC-ABS masuk |
| 2026-04-06 | TabR resmi dipakai |
| **2026-08-31** | **Split diganti jujur** (angka turun, tapi baru ini sah) |
| **2026-09-28** | **LOSO: 55,36% = baseline** → masalahnya di fitur |
| 2026-10-09 | Spotting diuji di CAS(ME)²: F1 0,20 → 0,43 |
| 2026-10-10 | Spotting diperbaiki: event/sample 12,7 → 4,8 |
| **2026-10-11 20:45** | **Run bersih penuh dari nol** |
| **2026-10-11 21:47** | **Temuan utama: BA 0,750, p 0,010** (dalam-subjek) |
| 2026-10-12 15:06 | Run STATE paling baru: test 54,46% |
| 2026-10-12 16:26 | Model final bisa dipakai |
| 2026-10-13 | Proposal BAB I–II selesai, dokumen ini dibuat |


## 4. Hasil semua run (train / validasi / test)

Urut dari yang paling lama ke yang paling baru. **Baris terakhir = run paling
baru.**

| # | Waktu | Run | Train | Val | Test | Catatan |
|---|---|---|---|---|---|---|
| 1 | s/d 2026-08-25 | TabR resmi, split bocor | 97,36% | 75,65% | 74,28% | **TIDAK SAH** (bocor subjek) |
| 2 | 2026-08-31 | 392 fitur, subjek-disjoint | – | – | 61,23% | level frame |
| 3 | 2026-09-01 | 196 fitur | – | – | 59,98% | level frame |
| 4 | 2026-09-01 | 608 fitur | – | – | 58,60% | level frame |
| 5 | 2026-09-01 | roi25 | – | – | 63,37% | terbaik di split lama |
| 6 | 2026-09-01 | 392 ulang (event baru) | – | – | 62,71% | level frame |
| 7 | 2026-09-17 11:41 | LOSO 392, level frame | – | – | 60,41% | tidak bisa ditafsirkan |
| 8 | 2026-09-28 12:00 | LOSO roi25, level subjek | – | – | **55,36%** | = baseline 55,36% |
| 9 | 2026-10-10 10:10 | LOSO v3 (spotting diperbaiki) | – | – | 48,21% | masih di bawah baseline |
| 10 | 2026-10-11 21:51 | LOSO `run2` (fitur `rise`) | 72,06% | 49,89% | 47,62% | AUC 0,398 |
| 11 | 2026-10-12 09:55 | LitTabR per-frame | 74,40% | 45,70% | 45,80% | level subjek **41,07%** |
| 12 | 2026-10-12 13:36 | `run2` `rise`, lr 3e-4 | 59,24% | 48,27% | 48,21% | 73% fold berhenti di epoch 0 |
| 13 | 2026-10-12 13:37 | `run2` per-frame, lr 3e-4 | 64,63% | 53,63% | 49,13% | 89% fold berhenti di epoch 0 |
| 14 | **2026-10-12 15:06** | **STATE/session (paling baru)** | **89,90%** | **62,50%** | **54,46%** | AUC 0,520 — lihat di bawah |

### Membaca baris terakhir (run paling baru)

| Angka | Nilai | Artinya |
|---|---|---|
| Train | 89,90% | Hafal data latih |
| Val | 62,50% | Mulai tidak stabil |
| **Test** | **54,46%** | **Masih di bawah baseline** |
| Baseline | 57,14% | Nebak "semua cemas tinggi" |
| AUC | 0,5204 | Hampir acak (acak = 0,5) |
| Sensitivitas | 0,79 | Sering bilang "cemas" |
| Spesifisitas | 0,15 | Hampir tidak pernah bilang "tidak cemas" |

**Kesimpulan baris terakhir:** model **berhasil secara mekanis** (bisa memuat,
memprediksi, mengeluarkan keputusan), tetapi **belum bisa menebak orang baru
dengan andal**. Angka test 54,46% masih di bawah baseline 57,14%, dan selang
kepercayaannya memuat baseline → belum terbukti lebih baik dari menebak.

### Pembanding model sederhana

Di data sekecil ini, model sederhana sering menyamai atau mengalahkan deep
learning. Jadi selalu disandingkan:

| Model | Akurasi (level subjek) | Baseline mayoritas | Signifikan? |
|---|---|---|---|
| Logistik | 53,57% | 55,36% | tidak (p = 0,42) |
| GBDT | 44,64% | 55,36% | tidak (p = 0,86) |
| TabR | 47,62% – 54,46% | 55,36% – 57,14% | tidak |

**Semuanya belum melewati baseline.** Artinya kegagalan ini bukan cuma soal
model, tapi soal sinyalnya.

### Model final yang disimpan

| Angka | Nilai |
|---|---|
| Train accuracy | 68,6% |
| Train balanced accuracy | 69,9% |
| Baris data | 27.936 |
| Jumlah fitur | 60 |

> Model ini dilatih pada **semua** data dan **tidak punya test set** — memang
> begitu tujuannya: jadi alat yang dipakai, bukan alat yang dinilai. Angka
> jujurnya memakai hasil LOSO (baris 14), yaitu **54,46%**.

---

## 5. Hasil tahap spotting (CAS(ME)²)

Tahap spotting = menemukan *di frame mana* gerakan halus terjadi. Diuji pakai
dataset publik CAS(ME)² yang punya jawaban benar (ground truth).

| Percobaan | F1 | Catatan |
|---|---|---|
| Pipeline awal | 0,200 | jauh dari memadai |
| Setelah grid parameter | 0,324 | setelan terbaik `top_k=4` |
| + fitur arah & koherensi | 0,27–0,32 | naik tipis |
| Klasifikasi jendela (64 frame) | 0,372 | ambang dipilih jujur per fold |
| Klasifikasi jendela (96 frame) | **0,428** | hasil spotting terbaik |

**Bacaan jujur:** F1 0,43 artinya masih **banyak deteksi palsu**. Ekspresi mikro
memang kasus tersulit (ingat: durasinya 0,04–0,2 detik). Ini dilaporkan apa
adanya, bukan disembunyikan.

---

## 6. Hasil uji "dalam diri orang yang sama" (temuan terkuat)

Ini uji paling bersih: **orang yang sama, wajah yang sama**, hanya berbeda sesi
(sebelum vs sesudah ujian). Jadi tidak ada gangguan identitas orang.

| Fitur yang dipakai | Balanced accuracy | p-value | Artinya |
|---|---|---|---|
| Per-frame (statis) | 0,639 | 0,065 | belum signifikan |
| **Dinamika onset (`rise`)** | **0,750** | **0,010** | **signifikan** |
| Vektor selisih | 0,500 | 0,61 | tidak ada sinyal |

> **Ini hasil yang bisa dipertahankan.** p = 0,010 berarti kemungkinan muncul
> kebetulan hanya 1%. Inilah dasar arah tesis diubah dari "tebak tingkat
> kecemasan orang" (gagal) menjadi "deteksi **perubahan** kondisi dalam diri
> orang" (berhasil).

---

## 7. Kesimpulan jujur

**Yang berhasil**

- Pipeline lengkap jalan dari video mentah sampai keputusan.
- Model bisa disimpan dan dipakai untuk memprediksi.
- Tahap spotting sudah divalidasi dengan dataset publik.
- Deteksi **perubahan** kondisi dalam diri orang yang sama: **BA 0,75, p 0,010**.
- Model sederhana sudah dijadikan pembanding, bukan disembunyikan.

**Yang belum berhasil**

- Menebak tingkat kecemasan **orang baru**: 54,46% vs baseline 57,14%.
- AUC ≈ 0,52 → nyaris acak.
- Fitur masih lebih kuat menandai *identitas* daripada *kecemasan*.
- Tahap spotting masih banyak deteksi palsu (F1 0,43).

**Langkah berikutnya**

- Tulis BAB III (metodologi) — masih kosong.
- Pertimbangkan framing tesis ke arah **state/perubahan**, bukan trait.
- Perkuat fitur dinamika onset (`rise`), karena di situ sinyalnya ada.

---

## 8. Di mana datanya

| Isi | Lokasi |
|---|---|
| **Pipeline (titik masuk)** | **`pipeline/run.sh`** |
| Peta stage + perintah | `pipeline/README.md` |
| Stage pipeline (0–8) | `pipeline/stages/stage_*_*.py` |
| Pakai model / latih final | `pipeline/serve/{predict,train_final}.py` |
| Definisi ROI | `features/roi_config.py` |
| Eksperimen CAS(ME)² | `research/casme2/` |
| Kode lama (tidak dipakai) | `legacy/` |
| Bobot model dlib | `models/` |
| Konfigurasi training | `experiments/configs/*.toml` |
| Tabel fitur | `experiments/features/apex/` |
| Dokumen ini (ringkasan) | `report/documentation/ringkasan.md` |
| Detail teknis tiap perubahan | `report/documentation/changes-log.md` |
| Catatan progres terbaru | `PROGRESS.md` |
| Hasil tiap run | `output/training/<nama-run>/summary.md` |
| Model siap pakai | `output/final_model/` |
| Paper yang dipakai + tautan | `report/documentation/research-papers.md` |
| Proposal skripsi | `proposal/proposal.pdf` |

Catatan: sebelum 2026-10-13 semua pipeline ada di `scripts/`. Sekarang
`scripts/` sudah tidak ada dan isinya dibagi ke `pipeline/`, `research/`, dan
`legacy/`.

---

## Kamus singkat

| Istilah | Arti sederhana |
|---|---|
| **Micro-expression** | Gerakan wajah sangat singkat (0,04–0,2 detik) yang muncul tanpa disadari |
| **POC-ABS** | Metode mengukur gerakan halus antar-frame video |
| **Fitur** | Angka hasil pengukuran yang jadi bahan model |
| **TabR** | Model yang menebak dengan cara mencari data yang mirip |
| **LOSO** | Cara uji jujur: satu orang dikeluarkan, diuji pada orang itu, diulang untuk semua orang |
| **Baseline** | Patokan sederhana (nebak kelas terbanyak) |
| **AUC** | Ukuran kemampuan memisahkan dua kelas. 0,5 = acak, 1,0 = sempurna |
| **Balanced accuracy** | Akurasi yang adil walau jumlah kelas tidak seimbang |
| **F1** | Gabungan ketepatan dan kelengkapan deteksi |
| **p-value** | Peluang hasil muncul kebetulan. Di bawah 0,05 = dianggap nyata |
| **Epoch** | Satu putaran belajar |
| **Overfit** | Model hafal data latih tapi gagal di data baru |
| **State / Trait** | State = kondisi saat itu. Trait = sifat bawaan orang |


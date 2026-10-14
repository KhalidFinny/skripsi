# 10 — Tabel fitur basi: re-ekstraksi dari metadata terbaru

**Severity:** critical (blocker)

## Current Problem

`experiments/features/apex/poc_abs_roi_signals.xlsx` bertanggal **2026-09-01**,
sementara `output/apex/metadata.xlsx` dan `output/apex/dataset/` bertanggal
**2026-09-22**. Tabel fitur tidak pernah dibuat ulang setelah re-spotting.

| | metadata + dataset | tabel fitur |
|---|---|---|
| `before` event | 3.639 | 1.493 |
| `before` subjek | 56 | 23 |
| `before/tidak` | 921 event / 15 subjek | **0 baris** |

Akibatnya:

- **2.146 event `before` hilang**; 33 subjek tidak punya data `before`.
- Seluruh blok `before/tidak` hilang, sehingga di tabel fitur `before` jadi
  100% `anxiety_tinggi`. Itu artefak kehilangan data, **bukan** protokol.
- Analisis grup `before_sama` (13) / `before_berubah` (10) di `summary.md`
  tidak sah — dihitung dari 23 subjek, bukan 56.
- Kesimpulan apa pun yang membandingkan `before` vs `after` tidak sah.

Yang tidak terpengaruh: headline LOSO (`--label-unit person` hanya memakai
`after`, dan `after` lengkap: 3.239 vs 3.244 event, 56 subjek).

## Target

`poc_abs_roi_signals.xlsx` + `_full.pkl` konsisten dengan metadata 22 Sep:
56 subjek untuk kedua fase, `before` = 41 anxiety / 15 tidak.

## Required Design

- Jalankan ulang `scripts/extract_features_poc_abs.py --roi-signals` terhadap
  `output/apex/dataset` + `output/apex/metadata.xlsx`.
- **Tabel lama diarsipkan dulu**, jangan ditimpa langsung: pindahkan ke
  `experiments/features/apex/poc_abs_roi_signals_stale_20260901.xlsx`.
- Bangun ulang cache dengan `scripts/build_feature_cache.py`.
- Dataset mentah sudah ada di mesin ini (`output/apex/dataset`, 9,5 GB,
  104.202 frame) — tidak perlu `/mnt/FINNY/dataset`.
- Estimasi: 6.878 event, jam-an (bandingkan Iterasi 3.4: spotting 560 video
  ~41 menit; ekstraksi lebih ringan dari spotting).
- Setelah selesai: jalankan ulang `collect_loso_results.py` untuk memperbaiki
  analisis grup.

## Tests

- Cek `phase × label` di tabel baru = 41/15 dan 25/31 per subjek.
- Cek jumlah event `before` = 3.639.
- Jalankan ulang `collect_loso_results.py` pada hasil LOSO lama; grup
  `before_*` harus berubah karena datanya kini lengkap.

## Done Criteria

- [ ] Tabel lama diarsipkan.
- [ ] Tabel fitur baru memuat 56 subjek `before` + 56 `after`.
- [ ] `before/tidak` tidak lagi 0 baris.
- [ ] Cache pkl dibangun ulang.
- [ ] Analisis grup di `summary.md` diperbarui.

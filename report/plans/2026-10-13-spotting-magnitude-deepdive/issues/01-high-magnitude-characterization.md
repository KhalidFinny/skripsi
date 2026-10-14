# 01 — Karakterisasi magnitude POC-ABS

**Severity:** high

## Current Problem

Magnitude per blok = `sqrt(oX² + oY²)` dengan oX/oY integer −4..4 (block 9):
hanya ~9 nilai diskret (0, 1, √2, 2, √5, √8, 3, √10, …, 5,66). Sinyal spotting
saat ini = mean magnitude seluruh blok ROI → mean antar ROI. Belum ada angka:

1. Berapa fraksi blok yang jenuh di batas (|oX|=4 atau |oY|=4) pada mode ABS
   (acuan frame-0) — saturasi meratakan bentuk puncak apex.
2. Berapa fraksi blok bergerak saat GT ekspresi vs di luar ekspresi — kalau
   ekspresi hanya menggerakkan 10-20% blok, mean menenggelamkan sinyal.
3. Definisi kandidat mana yang paling memisahkan frame ekspresi dari non-ekspresi
   (mean / max / mean top-25% / count blok bergerak / mean tertimbang nilai
   puncak korelasi).

## Target

Skrip `scripts/diag_magnitude_casme2.py` (per-blok, sampel ~10 video CAS(ME)²,
POC dihitung langsung) + findings `report/findings/magnitude-deepdive.md`
berisi:

- histogram nilai magnitude per blok + fraksi saturasi
- fraksi blok bergerak (magnitude > 0) saat GT onset..offset vs baseline
- peringkat relatif puncak ekspresi untuk tiap definisi kandidat
  (metrik sama seperti probe_signal_casme2: makin kecil makin baik, acak = 0,5)

## Required Design

- POC-ABS acuan frame-0, block 9, ROI dari `features_extraction/roi_config.py`
  — persis pipeline; jangan mengubah kode produksi.
- Sampel video dipilih deterministic (seed tetap), mencakup macro & micro GT.
- Kandidat "tertimbang" = mean magnitude diboboti nilai puncak korelasi POC
  per blok (val_max di vektor.py) — blok dengan korelasi rendah dianggap noise.

## Tests

Tidak ada (kontrak). Validasi = angka di findings konsisten dan dapat
direproduksi dari skrip.

## Done Criteria

- [x] Skrip jalan dan menghasilkan tiga tabel di atas (`scripts/diag_magnitude_casme2.py`, 10 video)
- [x] Findings tertulis dengan kesimpulan: definisi mana yang layak masuk sweep isu 02
  → `report/findings/magnitude-deepdive.md`: **mean tetap terbaik** (0,146 vs 0,164-0,271);
  tidak ada kandidat baru yang layak masuk sweep

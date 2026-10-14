# 02 — Tambahan koreksi FINAL.pdf bagian spotting

**Severity:** medium
**Status:** selesai (2026-10-13) — §7–10 ditambahkan ke
`report/findings/koreksi-final-pdf.md` (acuan frame-0, smoother 3%,
float64→int, 79 blok/316 fitur, definisi M + teks pengganti siap tempel).

## Masalah

Penyimpangan tambahan yang ditemukan saat membaca FINAL.pdf (hasil pdftotext)
pada ronde ini — belum tercakup di `report/findings/koreksi-final-pdf.md`:

1. **BAB V `build_magnitude_signal`**: didokumentasikan membandingkan frame
   berurutan (prev vs curr) dan memberi `mag = 0.0` saat landmark gagal.
   Kode sekarang: acuan frame-0 (`SPOT_ABS=1` default — pemenang audit,
   0,3486 vs 0,14) dan interpolasi linier untuk landmark gagal.
2. **BAB V `ApexSmoother`**: listing memakai window 5% dan
   `polyorder = min(3, window-2)`. Kode: 3% adaptif dan polyorder 2/3/4
   menurut ukuran window (apex/apex_smoother.py).
3. **BAB V `ApexPhase`**: distance 5, prominence 0.5. Kode: distance 1,
   prominence relatif 0,04×rentang (lantai 0,005), plus merge_distance 10,
   valley_uptick 0,75, radius 100 — tiga parameter terakhir tidak didokumentasikan.
4. **BAB V POC**: listing memakai float64 "agar numerik stabil". Kode: cast
   ke int (mengikuti paper). Pilih salah satu — dokumentasikan yang dijalankan.
5. **BAB IV/V daftar ROI & blok**: "mata-alis" 3 ROI, "mulut 70×35 → 10×5=50
   blok (7×7)", "total 98 blok × 4 = 392 fitur", Tabel 4.8 tiga kelompok fitur.
   Aktual: 5 ROI, block 9 (jumlah blok per ROI berbeda). Tabel 4.5.1 juga
   menyebut "area alis dan mulut" + "block size 7x7".
6. **Definisi M di Tabel 4.8** ("Magnitudo: besar intensitas pergerakan"):
   menunggu hasil isu 01 — bila Hpoc menang, definisi M di tulisan harus
   diubah ke nilai puncak korelasi (sesuai paper) dan justifikasinya dicantumkan.

## Yang dikerjakan

- Tambahkan bagian baru di `report/findings/koreksi-final-pdf.md` dengan teks
  pengganti siap tempel (pola bagian 1–5 yang sudah ada).

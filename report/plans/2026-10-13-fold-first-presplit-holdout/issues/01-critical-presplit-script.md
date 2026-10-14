# 01 — Pre-split script (critical)

## Current Problem

Tidak ada artefak split sebelum spotting. 56 orang baru dibagi di dalam
`run_loso.py` (stage 6), setelah spotting + ekstraksi fitur melihat semua
video.

## Target

`scripts/split_persons_presplit.py`:

- Scan `--raw-root` (struktur `<phase>/<condition>/<participant>_<ts>/q*/…`).
- Kumpulkan orang unik via `re.sub(r'_[0-9]+$', '', participant_raw)` — SAMA
  dengan `normalize_participant_key` di `extract_features_poc_abs.py`.
- Label pair per orang dari nama kondisi dir per fase (before/after) →
  strata: `tinggi_both` (24), `changed` (18), `rendah_both` (14).
  (condition `anxiety`→tinggi, `tidak`→rendah, sama seperti `map_label`.)
- Holdout `--test-people 12` (default) proporsional strata: 5+4+3, pemilihan
  dalam strata via `random.Random(--seed 42)` — deterministik.
- Tulis ke `--out output/presplit`:
  - `split.csv` — kolom `person,split,strata,n_sessions,conditions`
  - `train_persons.txt`, `test_persons.txt` — satu orang per baris
  - `summary.md` — tabel strata + daftar 12 orang + tanggal/seed
- `--dry-run`: cetak rencana tanpa menulis.

## Required Design

- Murni baca nama direktori — TIDAK membuka file video.
- Gagal keras kalau: orang tidak punya 2 fase, strata kosong, atau
  `--test-people` lebih besar dari strata terkecil yang dibutuhkan.
- Idempoten: tulis ulang output yang sama untuk seed yang sama.

## Tests

- `--dry-run` menunjukkan 56 orang, 44/12 split, strata 5/4/3.
- Jalankan dua kali → `split.csv` identik (diff kosong).

## Done Criteria

- [ ] Script ada, py_compile bersih
- [ ] Dry-run menunjukkan split strata benar
- [ ] Output deterministik untuk seed 42

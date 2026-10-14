# 01 — Paket `pipeline/` + titik masuk + peta stage (critical)

## Current Problem

Tidak ada satu tempat yang bisa disebut "pipeline". Yang ada:

- `scripts/` datar berisi 61 file; hanya 10 yang merupakan stage pipeline.
- Titik masuk `scripts/run_pipeline_v3.sh` tidak menonjol dan namanya tidak
  memberi tahu bahwa itu adalah pipeline utama.
- Nomor stage hanya hidup di dalam `run_pipeline_v3.sh` (fungsi `banner`) dan di
  nama file log. Dari struktur folder, tidak terlihat bahwa `0` = split dan
  `1` = spotting.

Khalid: *"i cant find when i need a pipeline to show, so each stage should be
well separated and well mark on which is which"*.

## Target

Struktur baru:

```
pipeline/
  README.md      peta stage + perintah run (jawaban "mulai dari sini")
  run.sh         titik masuk tunggal
  stages/
    0_presplit.py
    1_spotting.py
    2_extract_poc_abs.py
    3_cache.py
    4_temporal.py
    5_gate.py
    6_train_loso.py
    7_collect.py
    8_holdout.py
  serve/
    train_final.py
    predict.py
```

`pipeline/README.md` memuat:

1. Satu baris: "Pipeline dimulai dari sini: `./pipeline/run.sh`".
2. Tabel peta stage: nomor | nama | skrip | input | output.
3. Tabel "mau lihat apa?" → lokasi: split, spotting, apex, ROI, fitur, training,
   evaluasi holdout, pemakaian model.
4. Contoh perintah: default, `--fresh`, `--from N`, `--stage N`, `--dry-run`,
   `V3_PRESPLIT=1`, dan run dengan `V3_EXTRA_CONFIGS`.

## Required Design

- `pipeline/` adalah **satu-satunya** tempat pipeline; tidak ada stage yang
  tertinggal di `scripts/`.
- Nomor stage **tidak berubah** dari yang sekarang (0–8). Arti tiap nomor sama
  dengan `banner` di runner saat ini.
- `run.sh` tetap memakai infra yang sudah ada (`log`, `die`, `info`, `banner`,
  `run_stage`, `should_run`, `confirm_pause`) — jangan tulis ulang.
- Semua env var yang sudah dipakai tetap bekerja tanpa perubahan nama.
- `README.md` ditulis ringkas dan tabel-berat (bukan paragraf panjang), supaya
  enak dibaca di preview markdown.
- Tidak ada abstraksi baru yang tidak perlu: tidak ada registry stage, tidak ada
  plugin system. Cukup folder bernomor + runner + README.

## Tests

- `bash -n pipeline/run.sh` bersih.
- `./pipeline/run.sh --dry-run` mencetak 7 stage dengan path yang benar.
- `V3_PRESPLIT=1 ./pipeline/run.sh --dry-run` mencetak 8 stage (0–8).
- `pipeline/README.md` memuat baris peta untuk split, spotting, apex, training.

## Done Criteria

- [ ] Folder `pipeline/` ada dengan `run.sh`, `README.md`, `stages/`, `serve/`
- [ ] `README.md` punya tabel peta stage dan tabel "mau lihat apa?"
- [ ] `bash -n pipeline/run.sh` bersih
- [ ] `--dry-run` (default dan `V3_PRESPLIT=1`) mencetak urutan stage yang benar
- [ ] Env var lama tetap berfungsi (dicek di `--dry-run`)

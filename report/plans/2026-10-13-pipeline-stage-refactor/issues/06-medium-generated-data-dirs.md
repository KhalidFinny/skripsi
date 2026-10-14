# 06 — Rapikan folder data hasil (medium)

## Current Problem

Ada dua folder dengan nama nyaris sama, dan isinya berbeda jauh:

| Folder | Isi | Ukuran |
|---|---|---|
| `output/` | hasil pipeline kita (`apex_run2`, `apex_state`, `apex_v2`, `training`, `final_model`, `presplit`) | 13+ GB |
| `outputs/` | **satu file**: `models/shape_predictor_68_face_landmarks.dat` | 95 MB |

`outputs/` dengan isi satu file model adalah sisa kebiasaan lama. Nama
`outputs` vs `output` praktis tidak bisa dibedakan saat memindai daftar folder.

Selain itu `experiments/` mencampur dua hal berbeda:

```
experiments/configs/    36 KB  konfigurasi training (.toml) — input, bukan hasil
experiments/features/  173 MB  fitur hasil ekstraksi — generated
experiments/models/      0 B   kosong
```

Konfigurasi adalah **input** pipeline, sedangkan `features/` adalah **hasil**.
Menaruh keduanya di satu folder membuat batas input/hasil kabur.

Terverifikasi jalur model dlib muncul di **dua tempat**:

- `comparasion/core/config.py:22` → `Path("outputs/models/shape_predictor_68_face_landmarks.dat")`
  (relatif terhadap cwd)
- `process_spotting_pipeline.py:51` → `PROJECT_ROOT / 'outputs/models/shape_predictor_68_face_landmarks.dat'`
  (bisa dioverride `SPOT_PREDICTOR`)

## Target

```
models/                      ← bobot model, satu tempat
  shape_predictor_68_face_landmarks.dat

pipeline/configs/            ← was experiments/configs/
  tabr_loso_compact.toml
  tabr_loso_roi25_reg.toml
  ...

runs/                        ← hasil run (opsional; was output/)
```

Aturan yang jelas:

- **`models/`** — bobot model (dlib, checkpoint kalau nanti ada).
- **`pipeline/configs/`** — konfigurasi input pipeline.
- **`output/`** (atau `runs/`) — semua hasil run. Gitignored, berisi data besar.
- **`experiments/`** — dihapus setelah `configs/` pindah dan `features/` masuk ke
  `output/`; tidak ada lagi folder campuran.

## Required Design

- **Jangan hapus 13 GB data di `output/`.** Pindah nama `output/` → `runs/`
  **opsional** dan sebaiknya ditunda kalau ada run yang sedang berjalan, karena
  semua stage menulis ke `output/...` lewat env default. Kalau ditunda, cukup
  dokumentasikan di `pipeline/README.md` bahwa `output/` = hasil run.
- Kalau `output/` tetap dipakai namanya, **jangan** rename — biarkan, karena
  mengubahnya menyentuh puluhan default path dan tidak memberi manfaat besar.
  Yang penting `outputs/` (satu file) hilang.
- Setelah `models/` dibuat, perbarui **kedua** default jalur dlib
  (`shared/config.py` dan `pipeline/stages/1_spotting.py`), dan pastikan env
  `SPOT_PREDICTOR` tetap bekerja sebagai override.
- `experiments/features/` (173 MB) adalah generated. Pindahkan ke
  `output/features/` **atau** biarkan dan dokumentasikan. Kalau dipindah,
  perbarui default `FEAT_XLSX`/`FEAT_PKL` di runner.
- `.gitignore` disesuaikan: `models/` sudah ada di daftar ignore; pastikan
  folder baru tidak ikut ter-track kalau isinya besar.

## Tests

- `ls` di root tidak lagi menampilkan `outputs/`.
- `.venv/bin/python -c "from shared.config import ComparisonConfig; print(ComparisonConfig().predictor_path)"`
  menunjuk ke `models/shape_predictor_68_face_landmarks.dat` dan file itu ada.
- `.venv/bin/python pipeline/stages/1_spotting.py --help` tetap jalan tanpa
  `SPOT_PREDICTOR` diset.
- `SPOT_PREDICTOR=/tmp/x.dat .venv/bin/python pipeline/stages/1_spotting.py --help`
  membuktikan override masih bekerja.
- `./pipeline/run.sh --dry-run` menampilkan path config dari lokasi baru.

## Done Criteria

- [ ] `models/shape_predictor_68_face_landmarks.dat` ada
- [ ] `outputs/` sudah tidak ada
- [ ] Kedua default jalur dlib diperbarui; `SPOT_PREDICTOR` masih bekerja
- [ ] `pipeline/configs/` berisi konfigurasi; `experiments/configs/` tidak ada
- [ ] Tidak ada data besar yang terhapus
- [ ] `--dry-run` menampilkan path yang benar

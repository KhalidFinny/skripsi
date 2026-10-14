# 07 — Sinkronkan dokumen & semua perintah run (low)

## Current Problem

Setelah stage pindah, **23 dokumen** masih menyebut path lama. Yang paling
penting: perintah run yang dihafal Khalid berubah dari
`./scripts/run_pipeline_v3.sh` menjadi `./pipeline/run.sh`, dan dokumen yang
menjadi rujukan saat menjalankan pipeline masih memakai perintah lama.

Sebaran referensi `run_pipeline_v3.sh` di dokumen:

| Dokumen | Jumlah |
|---|---|
| `report/documentation/changes-log.md` | 29 |
| `PROGRESS.md` | 16 |
| `HANDOFF.md` | 11 |
| `report/plans/2026-10-06-geometri-headpose-fusion/plan.md` | 9 |
| `report/findings/*` (4 file) | 2 masing-masing |
| `report/documentation/progress.md` | 2 |
| plan lain (`2026-10-11`, `2026-10-13-*`) | 1–3 masing-masing |

## Target

Aturan yang jelas, supaya tidak menulis ulang sejarah:

**Dokumen hidup → diperbarui ke perintah baru:**

- `pipeline/README.md` (baru, dari issue 01) — rujukan utama.
- `PROGRESS.md` — perintah run di bagian teratas.
- `HANDOFF.md` — perintah run + struktur folder baru.
- `report/documentation/ringkasan.md` — peta lokasi file (bagian "Di mana datanya").
- `report/documentation/pipeline.md` — dokumen ini menjelaskan cara menjalankan
  pipeline, jadi wajib menunjuk `pipeline/run.sh` dan peta stage baru.

**Dokumen historis → dibiarkan, hanya diberi penunjuk:**

- `report/documentation/changes-log.md`, `report/documentation/progress.md`,
  `report/findings/*`, dan plan lama (`report/plans/2026-10-*`) adalah **catatan
  kejadian saat itu**. Path lama di dalamnya benar untuk zamannya. Jangan
  ditulis ulang.
- Tambahkan **satu baris penunjuk** di header `changes-log.md` (sudah ada
  penunjuk ke `ringkasan.md`) dan di `pipeline.md`:
  "Sejak 2026-10-13 pipeline ada di `pipeline/`; perintah lama `./scripts/run_pipeline_v3.sh`
  sekarang `./pipeline/run.sh`."

## Required Design

- **Jangan rewrite dokumen historis.** Mengubah catatan lama supaya cocok dengan
  struktur baru justru menghapus jejak keputusan. Cukup penunjuk di header.
- Perintah di dokumen hidup harus **bisa di-copy-paste** dan benar.
- `pipeline/README.md` memuat peta: perintah | artinya. Minimal:
  - `./pipeline/run.sh` — semua stage dari awal
  - `./pipeline/run.sh --fresh` — hapus output dulu, lalu jalan
  - `./pipeline/run.sh --from N` / `--stage N` — lanjut / satu stage
  - `./pipeline/run.sh --dry-run` — cetak rencana
  - `V3_PRESPLIT=1 ./pipeline/run.sh --fresh` — mode fold-first (8 stage)
  - `V3_EXTRA_CONFIGS="pipeline/configs/<x>.toml" ./pipeline/run.sh` — multi-config
  - `V3_SPOT_SIGNAL=mdmd V3_SPOT_MOTION_COMP=1 ./pipeline/run.sh` — resep spotting
- `report/documentation/ringkasan.md` bagian "Di mana datanya" diperbarui:
  pipeline → `pipeline/`, stage → `pipeline/stages/`, eksperimen →
  `research/`, legacy → `legacy/`, model → `models/`.
- Semua daftar "Must Not Forget" di plan lain yang menyebut path lama **tidak**
  diubah (historis), kecuali plan yang masih berjalan.

## Tests

- `grep -rn "scripts/run_pipeline_v3\|scripts/process_spotting_pipeline" pipeline/ PROGRESS.md HANDOFF.md report/documentation/ringkasan.md report/documentation/pipeline.md`
  harus kosong.
- Setiap perintah di `pipeline/README.md` diuji dengan `--dry-run` (kecuali yang
  menjalankan penuh).
- `./pipeline/run.sh --help` (kalau ada) menampilkan perintah yang sama dengan
  README.

## Done Criteria

- [ ] `pipeline/README.md` memuat peta perintah yang bisa di-copy-paste
- [ ] `PROGRESS.md`, `HANDOFF.md`, `ringkasan.md`, `pipeline.md` memakai perintah baru
- [ ] Dokumen historis diberi penunjuk, tidak ditulis ulang
- [ ] `grep` path lama di dokumen hidup bersih
- [ ] Semua perintah `--dry-run` di README terbukti jalan

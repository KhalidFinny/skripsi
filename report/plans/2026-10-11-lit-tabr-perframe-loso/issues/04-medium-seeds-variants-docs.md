# 04 — 3 seed + varian both-sessions + dokumen

**Severity:** medium

## Current Problem

Satu seed belum cukup untuk klaim (sebaran antar seed di pipeline ini historis
5–18 poin). Pertanyaan STATE (before+after) belum dijawab oleh metode asli.

## Target

1. `--tag after_s3 --seeds 3` (56 fold × 3 seed) → mean ± std accuracy subjek.
2. `--phases before after --tag both_s1 --seeds 1` → varian STATE
   (63.413 baris; label per sesi; fold tetap per subjek — kedua sesi subjek
   test ikut ter-holdout).
3. Perbarui `PROGRESS.md` (entri 2026-10-11), `HANDOFF.md` (cara menjalankan,
   hasil, jebakan), dan status plan ini.
4. Catat di PROGRESS: pembanding mana yang SAH (LOSO bersih) dan mana yang
   tidak (74% bocor).

## Required Design

- Bahasa Indonesia; angka persis seperti keluaran summary.md.
- Tidak menambah tuas/fitur baru di issue ini — murni konfirmasi + dokumentasi.

## Tests

DONE 56/56 untuk kedua tag; PROGRESS.md terbaca runtut oleh agen baru.

## Done Criteria

- [ ] after_s3 dan both_s1 selesai, angka mean±std tercatat.
- [ ] PROGRESS.md + HANDOFF.md diperbarui; plan status = selesai.

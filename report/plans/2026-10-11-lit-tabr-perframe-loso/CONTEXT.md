# CONTEXT — LitTabR Per-Frame dengan LOSO Bersih

## Problem

Pipeline saat ini menyimpang jauh dari metode asli proposal (skripsinew,
BAB III). Yang asli: video → frame → grayscale → dlib 68 landmark → 3 ROI →
POC-ABS per ROI (X, Y, θ, M) → merge+flatten → balancing + imputer + scaler →
**TabR kustom** (batch 128, ≤50 epoch, context freezing, retrieval FAISS).

Yang berjalan sekarang: spotting → klip event → deskriptor temporal `rise` →
agregat per subjek (44 baris × 55 fitur, d>>n) → TabR resmi batch 8 lr 1e-3.
Hasil bersih (run2): test 47,62% vs baseline 55,36%, MCC −0,1037, AUC 0,3978,
overfit universal 168/168 fold-seed sejak epoch 0 — 48,8% fold-seed "berhenti
di epoch 0", jadi angka itu mengukur model yang tidak belajar, bukan batas
fitur.

Metode asli TIDAK PERNAH dievaluasi bersih: angka lama (~74%) berasal dari
holdout kecil (n_external=2 subjek/kelas) dengan split val level-frame
(bocor dalam-subjek). Arahan user: berhenti pesimistis, perbaiki DARI aslinya,
pakai pipeline metode ini.

## Fix

Hidupkan lagi pipeline asli dengan setia, evaluasi dengan LOSO bersih:
baris = frame (bukan agregat subjek), subjek test keluar dari train/val/context,
val = 20% subjek train (bukan frame acak), keputusan subjek = mean prob frame.

Dasar optimisme berbasis bukti (bukan harapan):
- Rezim terbalik jadi n>>d: ~27k baris vs 60 fitur (sekarang 44×55). Retrieval
  TabR punya context nyata; d>>n adalah penyebab struktural overfit sekarang.
- Gerbang within-subject per-frame: BA 0,6389 — sinyal level-frame ada.
- Fitur lebih kaya dari aslinya: 60 sinyal (arah bertanda, koherensi R,
  motion count) vs 12 (X,Y,θ,M) di proposal, dari spotting yang sudah
  tervalidasi (F1 CAS(ME)² 0,3192).
- Konfigurasi asli yang paling matang (`notebooks/check_freeze_tabr.ipynb`):
  LR 3e-4, batch 128, freeze@6, m=4, patience 10, ≤50 epoch.

## Architecture Now

Lihat diagram di plan.md. Satu skrip baru: `scripts/run_loso_lit_tabr.py`.

## Key Files

- `scripts/run_loso_lit_tabr.py` — BARU. Runner LOSO (split, preprocess,
  context, training, metrik, resume, summary).
- `src/TabR.py` — fix nama param `freeze_context_epo` → cocok dengan
  `hparams.freeze_context_epoch` yang dibaca hook (bug laten, crash epoch 0).
- `src/data_module.py`, `src/encoder.py`, `src/value_correction.py` — dipakai
  apa adanya.
- `experiments/features/apex/poc_abs_run2_full.pkl` — input (63.413 baris
  frame; 35.477 before + 27.936 after; 60 fitur).
- `output/training/lit_tabr_perframe_*/` — output baru (hasil lama utuh).

## Important Behavior Changes

Tidak ada perubahan perilaku pada pipeline v3 yang ada. Ini jalur baru yang
berdampingan; `run_pipeline_v3.sh` tidak disentuh.

## Tests

Tanpa test otomatis (user tidak minta). Verifikasi = smoke 3 fold dengan
assert anti-bocor di dalam runner (set intersection kosong) + angka fold
masuk akal (bukan NaN, context > 0, epoch > 0 berjalan).

## Validation Done

(Akan diisi selama eksekusi.)

## Known Notes

- Label per-SESI (`anxiety_tinggi`/`rendah`). Varian default: after-only
  (setara headline 47,62%). Varian both-sessions = pertanyaan STATE, di issue 04.
- GPU 1650 Ti 4GB: model kecil (d=128, ~50k param), batch 128 → muat.
  FAISS IndexFlatL2 di CPU (desain asli), context ~22k×128 = ~11 MB.
- Estimasi: ~1–2 menit/fold di GPU → 56 fold × 1 seed ≈ 1–2 jam.
- Angka 74% lama TIDAK boleh diklaim sebagai pembanding sah (split bocor);
  pembanding sah = 47,62% (jalur agregat, LOSO bersih yang sama).

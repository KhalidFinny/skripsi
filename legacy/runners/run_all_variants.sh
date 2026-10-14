#!/usr/bin/env bash
# ============================================================================
# run_all_variants.sh — SATU PERINTAH: ulang penuh setelah perbaikan spotting.
#
#   spotting baru (per-ROI + interpolasi + threshold adaptif, TANPA event-signal)
#   -> fitur 392/608/roi25 -> npy 392/196/608/roi25 (split subjek-disjoint sama)
#   -> training semua -> collect hasil (macroF1 + bal_acc)
#
# Override mode spotting (opsional, default = perbaikan yang diimplementasikan):
#   SPOT_SIGNAL_MODE=global_mean   utk mempertahankan event set lama (komparabel)
#   SPOT_THRESH=mad                utk event lebih sedikit (threshold robust)
#   SPOT_INTERP=0                  nonaktifkan interpolasi landmark-gagal
#   SPOT_DISTANCE=1 SPOT_PROM_REL=0   nonaktifkan filter distance/prominence (event set lama)
#   (SPOT_PROM_REL default 0.04 = prominence relatif aktif; SPOT_DISTANCE default 1)
#
# Pemakaian:  ./scripts/run_all_variants.sh
#              ./scripts/run_all_variants.sh --no-spot   (lanjutkan: spotting sdh selesai)
# Waktu:      spotting ~1-3 jam (tanpa event-signal) + fitur ~45 mnt
#              + npy ~15 mnt + training ~2 jam  (GPU 4GB, 4 dataset)
# ============================================================================
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

NO_SPOT=0
[ "${1:-}" = "--no-spot" ] && NO_SPOT=1

SPOT_SIGNAL_MODE="${SPOT_SIGNAL_MODE:-roi_signals}"
SPOT_THRESH="${SPOT_THRESH:-meanstd}"
# SPOT_OVERWRITE=1 -> spotter MEMPROSES ULANG semua video (bukan resume dari dir lama)
export SPOT_SIGNAL_MODE SPOT_THRESH SPOT_INTERP="${SPOT_INTERP:-1}" SPOT_NO_EVENT_SIGNAL=1 SPOT_OVERWRITE=1

log() { echo "[$(date '+%F %T')] $*"; }

if [ "$NO_SPOT" = 0 ]; then
  log "=== [1/4] SPOTTING (mode=$SPOT_SIGNAL_MODE, thresh=$SPOT_THRESH, interp=$SPOT_INTERP, event-signal=SKIP) ==="
  ./scripts/run_pipeline.sh --mode anxiety --force --stage 1
else
  log "=== [1/4] SPOTTING DILEWATI (--no-spot), lanjut dari fitur ==="
fi

log "=== [2/4] EKSPOR FITUR: 392 / 608 / roi25 ==="
uv run python scripts/extract_features_poc_abs.py
uv run python scripts/extract_features_poc_abs.py --brows
uv run python scripts/extract_features_poc_abs.py --roi-signals

log "=== [3/4] EKSPOR NPY: 392 / 196 / 608 / roi25 (split subjek-disjoint sama) ==="
uv run python scripts/export_to_official_tabr_dataset.py
uv run python scripts/export_to_official_tabr_dataset.py --drop-derived --dataset convat_apex_anxiety_196
uv run python scripts/export_to_official_tabr_dataset.py --features experiments/features/apex/poc_abs_flatten_ordered_608.xlsx --dataset convat_apex_anxiety_608
uv run python scripts/export_to_official_tabr_dataset.py --features experiments/features/apex/poc_abs_roi_signals.xlsx --dataset convat_apex_anxiety_roi25

log "=== [4/4] TRAINING + COLLECT (4 dataset) ==="
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
cd "$ROOT/third_party/tabular-dl-tabr-official"
for ds in convat_apex_anxiety convat_apex_anxiety_196 convat_apex_anxiety_608 convat_apex_anxiety_roi25; do
  log "--- training $ds ---"
  PYTHONUNBUFFERED=1 "$ROOT/.venv/bin/python" bin/go.py --force "exp/tabr/$ds/0-tuning.toml"
done
cd "$ROOT"
for ds in convat_apex_anxiety convat_apex_anxiety_196 convat_apex_anxiety_608 convat_apex_anxiety_roi25; do
  log "--- collect $ds ---"
  uv run python scripts/collect_training_results.py --exp "$ds"
done

log "SELESAI. Bandingkan: output/training/<ds>/summary.md (test acc / macroF1 / bal_acc)"

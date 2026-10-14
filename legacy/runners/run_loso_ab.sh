#!/usr/bin/env bash
# ============================================================================
# run_loso_ab.sh — LOSO A/B dalam satu perintah (items 2 & 3).
#
#   items 2+3 langsung jalan di event features yang ADA (tanpa re-spotting):
#     * --imbalance frames       (item 3: oversample frame kelas minoritas)
#     * --variance-threshold     (item 2: buang blok statis; default lunak 1e-4)
#
# Pemakaian:
#   ./scripts/run_loso_ab.sh                    # semua fold, 3 seed
#   ./scripts/run_loso_ab.sh --seeds 1          # lebih cepat (1 seed/fold)
#   LOSO_ARGS="--seeds 1" ./scripts/run_loso_ab.sh
#
# Semua argumen diteruskan ke scripts/run_loso.py.
# ============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${ROOT}/.venv/bin/python"
[ -x "$PY" ] || PY=python

export PYTHONUNBUFFERED=1
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"

# Batasi thread CPU (torch/MKL/OpenBLAS dll) supaya tidak spawn banyak proses/thread
# dan hemat RAM. Naikkan LO_THREADS kalau mau lebih cepat (default 4).
LO_THREADS="${LO_THREADS:-4}"
export OMP_NUM_THREADS=$LO_THREADS
export MKL_NUM_THREADS=$LO_THREADS
export OPENBLAS_NUM_THREADS=$LO_THREADS
export NUMEXPR_NUM_THREADS=$LO_THREADS
export VECLIB_MAXIMUM_THREADS=$LO_THREADS
unset OMP_PROC_BIND

# Override penuh lewat env: LOSO_ARGS="--imbalance clips --variance-threshold 0"
EXTRA=("--imbalance" "frames" "--variance-threshold" "1e-4")
[ -n "${LOSO_ARGS:-}" ] && EXTRA=()   # abaikan default kalau user set LOSO_ARGS

exec "$PY" "${ROOT}/scripts/run_loso.py" "${EXTRA[@]}" "$@"
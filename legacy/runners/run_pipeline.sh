#!/usr/bin/env bash
# ============================================================================
# run_pipeline.sh — jalankan pipeline SPOTTING → FITUR → TRAINING
# secara BERURUTAN: satu stage selesai dulu, baru stage berikutnya dimulai.
# Tidak ada paralel. Setiap stage mencetak penjelasan: apa yang dilakukan,
# input, output, dan estimasi waktu. Gagal di satu stage = berhenti di situ.
#
# Pemakaian:
#   ./scripts/run_pipeline.sh                       mode datatest, semua stage
#   ./scripts/run_pipeline.sh --mode anxiety        dataset utama (112 subjek)
#   ./scripts/run_pipeline.sh --stage 2             HANYA stage 2
#   ./scripts/run_pipeline.sh --from 2              mulai dari stage 2
#   ./scripts/run_pipeline.sh --force               jalankan ulang walau output ada
#   ./scripts/run_pipeline.sh --pause               konfirmasi sebelum tiap stage
#   ./scripts/run_pipeline.sh --dry-run             cetak rencana saja, tanpa eksekusi
#   ./scripts/run_pipeline.sh --abs 1               USE_ABS_BASELINE=True (POC-ABS)
#   ./scripts/run_pipeline.sh --abs 0               USE_ABS_BASELINE=False (asli)
#
# Stage yang berlaku per mode:
#   datatest : 1 spotting, 2 fitur, 3 evaluasi (opsional, --eval)
#   anxiety  : 1 spotting, 2 fitur, 3 training LOSO (Leave-One-Subject-Out)
# ============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# ----------------------------------------------------------------------------
# Argumen
# ----------------------------------------------------------------------------
MODE="datatest"
FORCE=0
PAUSE=0
DRY=0
ABS=1
ONLY_STAGE=""
FROM_STAGE=1
RUN_EVAL=0

while [ $# -gt 0 ]; do
  case "$1" in
    --mode)   MODE="$2"; shift 2 ;;
    --stage)  ONLY_STAGE="$2"; FROM_STAGE="$2"; shift 2 ;;
    --from)   FROM_STAGE="$2"; shift 2 ;;
    --force)  FORCE=1; shift ;;
    --pause)  PAUSE=1; shift ;;
    --dry-run) DRY=1; shift ;;
    --abs)    ABS="$2"; shift 2 ;;
    --eval)   RUN_EVAL=1; shift ;;
    *) echo "ARGUMEN TIDAK DIKENAL: $1"; exit 1 ;;
  esac
done

# Python/jupyter langsung dari .venv (tanpa uv)
PY="$ROOT/.venv/bin/python"
JUPYTER="$ROOT/.venv/bin/jupyter"
[ -x "$PY" ] || PY="python"
[ -x "$JUPYTER" ] || JUPYTER="jupyter"

STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/pipeline_${MODE}_${STAMP}.log"

log() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }
die() { echo "[$(date '+%F %T')] GAGAL: $*" | tee -a "$LOG"; exit 1; }
info() { echo "  $*" | tee -a "$LOG"; }

# Daftarkan kernel jupyter 'skripsi' (idempotent) — dipakai nbconvert
ensure_kernel() {
  "$PY" -m ipykernel install --user --name skripsi --display-name "Skripsi" >/dev/null 2>&1 \
    || die "gagal mendaftarkan kernel 'skripsi' (cek ipykernel)"
}

banner() {
  local n="$1" total="$2" judul="$3" apa="$4" input="$5" output="$6" eta="$7"
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG"
  echo "STAGE $n/$total : $judul" | tee -a "$LOG"
  echo "  APA YANG DILAKUKAN : $apa" | tee -a "$LOG"
  echo "  INPUT              : $input" | tee -a "$LOG"
  echo "  OUTPUT             : $output" | tee -a "$LOG"
  echo "  ESTIMASI WAKTU     : $eta" | tee -a "$LOG"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG"
}

confirm_pause() {
  if [ "$PAUSE" = 1 ]; then
    read -r -p "  Lanjut stage berikutnya? (y/N) " ans
    [ "$ans" = "y" ] || { log "DIHENTIKAN oleh user."; exit 0; }
  fi
}

should_run() {
  local s="$1"
  [ -z "$ONLY_STAGE" ] || { [ "$ONLY_STAGE" = "$s" ] && return 0 || return 1; }
  [ "$s" -ge "$FROM_STAGE" ]
}

# ----------------------------------------------------------------------------
# Konfigurasi per mode
# ----------------------------------------------------------------------------
case "$MODE" in
  datatest)
    DS_ROOT="${SPOT_DATASET_ROOT_DATATEST:-/mnt/FINNY/dataset/datatest/labeled}"
    EXT=webm
    OUT_DIR="$ROOT/output/apex/datatest"
    FEAT_SCRIPT=scripts/extract_features_roi.py
    FEAT_ARGS=""
    FEAT_OUT="$ROOT/output/apex/datatest/features"
    TOTAL_STAGES=3
    ;;
  anxiety)
    DS_ROOT="${SPOT_DATASET_ROOT_ANXIETY:-/mnt/FINNY/dataset/anxiety_raw}"
    EXT=avi
    OUT_DIR="$ROOT/output/apex"
    FEAT_SCRIPT=scripts/extract_features_poc_abs.py
    # Baseline POC-ABS: 'neutral' = acuan netral per subjek (sebab #3, default baru),
    # 'onset' = frame onset klip (perilaku lama). Bisa dioverride lewat env.
    FEAT_BASELINE="${SPOT_FEAT_BASELINE:-neutral}"
    FEAT_OUT="$ROOT/experiments/features/apex/poc_abs_roi_signals.xlsx"
    FEAT_ARGS="--roi-signals --baseline $FEAT_BASELINE"
    if [ "$FEAT_BASELINE" = "neutral" ]; then
      # Nama berbeda supaya tabel lama (baseline onset) tidak ditimpa.
      FEAT_OUT="$ROOT/experiments/features/apex/poc_abs_roi_signals_neutral.xlsx"
      FEAT_ARGS="$FEAT_ARGS --output $FEAT_OUT"
    fi
    # Stage 3 (protokol diperbaiki): fitur temporal + normalisasi per subjek,
    # dataset & keluaran bernama baru supaya hasil lama tetap utuh.
    LOSO_FEATURES="${LOSO_FEATURES:-$ROOT/experiments/features/apex/poc_abs_roi_signals_neutral_temporal.pkl}"
    LOSO_DATASET="${LOSO_DATASET:-convat_apex_anxiety_loso_roi25_fixed}"
    LOSO_SUBJECT_NORM="${LOSO_SUBJECT_NORM:-subject}"
    TOTAL_STAGES=3
    ;;
  *) die "mode tidak dikenal: $MODE (pakai datatest | anxiety)" ;;
esac

# ----------------------------------------------------------------------------
# STAGE 0 — PRA-SYARAT (selalu dijalankan, kecuali mulai dari stage > 1)
# ----------------------------------------------------------------------------
if { [ -z "$ONLY_STAGE" ] && [ "$FROM_STAGE" -le 1 ]; } || [ "$ONLY_STAGE" = "0" ]; then
  banner 0 "$TOTAL_STAGES" "PRA-SYARAT" \
    "Cek semua yang dibutuhkan sebelum pipeline dimulai" \
    "-" "-" "sebentar"

  [ -x "$PY" ] || die "python .venv tidak ditemukan: $ROOT/.venv/bin/python (buat venv + install deps dulu)"
  [ -d "$ROOT/.venv" ] || die ".venv belum ada"
  [ -f "$ROOT/models/shape_predictor_68_face_landmarks.dat" ] || die "model dlib tidak ada. Unduh dulu (lihat report/documentation/before.md langkah 1)"
  [ -d "$DS_ROOT" ] || die "dataset tidak ditemukan: $DS_ROOT"
  [ -f "$ROOT/third_party/tabular-dl-tabr-official/bin/go.py" ] || die "repo TabR resmi belum di-clone"
  if [ "$MODE" = "anxiety" ]; then
    [ -f "$ROOT/third_party/tabular-dl-tabr-official/exp/tabr/convat_apex_anxiety/0-evaluation/13.toml" ] || die "config template LOSO tidak ada: exp/tabr/convat_apex_anxiety/0-evaluation/13.toml"
  fi
  "$PY" -c "import nbconvert, nbformat" >/dev/null 2>&1 || die "nbconvert belum terpasang di .venv"
  log "PRA-SYARAT OK: .venv, dlib model, dataset, TabR repo, nbconvert"
  confirm_pause
fi

# ----------------------------------------------------------------------------
# STAGE 1 — SPOTTING
# ----------------------------------------------------------------------------
if should_run 1; then
  if [ "$FORCE" = 0 ] && [ -f "$OUT_DIR/metadata.xlsx" ]; then
    log "STAGE 1/DILEWATI: spotting sudah selesai (metadata.xlsx ada). Pakai --force untuk ulang total."
  else
    banner 1 "$TOTAL_STAGES" "SPOTTING (mencari apex/event)" \
      "Deteksi wajah (dlib) -> POC-ABS per frame -> cari apex -> simpan klip event" \
      "$DS_ROOT  (*.$EXT)" \
      "$OUT_DIR/dataset/... + metadata.xlsx" \
      "LAMA (jam) - progress bar live; resume otomatis (sample yang sudah ada dilewati)"
    if [ "$DRY" = 1 ]; then
      info "[dry-run] (export SPOT_DATASET_ROOT=${DS_ROOT} SPOT_OUTPUT_ROOT=${OUT_DIR} SPOT_VIDEO_EXT=.$EXT; $PY scripts/process_spotting_pipeline.py)"
    else
      NB_LOG="$LOG_DIR/stage1_spotting_$STAMP.log"
      (SPOT_DATASET_ROOT="$DS_ROOT" SPOT_OUTPUT_ROOT="$OUT_DIR" SPOT_VIDEO_EXT=".$EXT" SPOT_ABS="${SPOT_ABS:-1}" \
       SPOT_OVERWRITE="${SPOT_OVERWRITE:-0}" SPOT_NO_EVENT_SIGNAL="${SPOT_NO_EVENT_SIGNAL:-0}" \
       MPLBACKEND=Agg PYTHONUNBUFFERED=1 "$PY" scripts/process_spotting_pipeline.py) 2>&1 | tee "$NB_LOG" \
        || { log "SPOTTING GAGAL - detail di $NB_LOG (tail):"; tail -30 "$NB_LOG"; die "SPOTTING GAGAL"; }
    fi
    log "STAGE 1 SELESAI. Output: $OUT_DIR/dataset + $OUT_DIR/metadata.xlsx"

    # ── 1b. Acuan netral per sample (dibutuhkan --baseline neutral) ──
    # Dibuat dari video mentah, jadi berlaku baik untuk klip yang baru saja
    # di-spotting maupun klip lama yang sudah ada (idempotent: skip bila ada).
    if [ "$DRY" = 1 ]; then
      info "[dry-run] $PY scripts/save_neutral_references.py --raw-root $DS_ROOT --dataset-root $OUT_DIR/dataset"
    else
      NEUTRAL_LOG="$LOG_DIR/stage1b_neutral_$STAMP.log"
      PYTHONUNBUFFERED=1 "$PY" scripts/save_neutral_references.py \
        --raw-root "$DS_ROOT" --dataset-root "$OUT_DIR/dataset" 2>&1 | tee "$NEUTRAL_LOG" \
        || { log "ACUAN NETRAL GAGAL - detail di $NEUTRAL_LOG (tail):"; tail -30 "$NEUTRAL_LOG"; die "ACUAN NETRAL GAGAL"; }
      log "STAGE 1b SELESAI. neutral.png per sample di $OUT_DIR/dataset"
    fi
  fi
  confirm_pause
fi

# ----------------------------------------------------------------------------
# STAGE 2 — EKSPOR FITUR
# ----------------------------------------------------------------------------
if should_run 2; then
  if [ "$FORCE" = 0 ] && [ -e "$FEAT_OUT" ]; then
    log "STAGE 2/DILEWATI: output fitur sudah ada ($FEAT_OUT). Pakai --force untuk jalankan ulang."
  else
    banner 2 "$TOTAL_STAGES" "EKSPOR FITUR (dari klip event)" \
      "Baca klip event -> POC-ABS per frame vs acuan ($FEAT_BASELINE) -> tabel fitur" \
      "$OUT_DIR/dataset/... + neutral.png per sample (SPOT_SAVE_NEUTRAL=1)" \
      "$FEAT_OUT" \
      "SEDANG (menit-jam) - progress bar live"
    if [ "$DRY" = 1 ]; then
      info "[dry-run] $PY $FEAT_SCRIPT $FEAT_ARGS"
    else
      NB_LOG="$LOG_DIR/stage2_export_$STAMP.log"
      log "Menjalankan ekspor fitur (progress bar live, log: $NB_LOG)..."
      (PYTHONUNBUFFERED=1 "$PY" "$FEAT_SCRIPT" $FEAT_ARGS) 2>&1 | tee "$NB_LOG" \
        || { log "EKSPOR FITUR GAGAL - detail di $NB_LOG (tail):"; tail -30 "$NB_LOG"; die "EKSPOR FITUR GAGAL"; }
    fi
    log "STAGE 2 SELESAI. Output: $FEAT_OUT"
  fi
  confirm_pause
fi

# ----------------------------------------------------------------------------
# STAGE 3 — anxiety: TRAINING LOSO | datatest: evaluasi (opsional)
# ----------------------------------------------------------------------------
if [ "$MODE" = "anxiety" ]; then
  if should_run 3; then
    banner 3 "$TOTAL_STAGES" "TRAINING LOSO (Leave-One-Subject-Out)" \
      "3a fitur temporal onset->apex->offset; 3b LOSO TabR (test=1 subjek, norm per subjek); 3c collect; 3d baseline logistik/GBDT + permutation" \
      "$FEAT_OUT" \
      "third_party/tabular-dl-tabr-official/exp/tabr/$LOSO_DATASET/fold_*/ + output/training/$LOSO_DATASET*/" \
      "LAMA (jam) - progress bar live; GPU 4GB, resume otomatis per fold (DONE.json)"

    # ── 3a. Fitur temporal ──
    if [ "$DRY" = 1 ]; then
      info "[dry-run] $PY scripts/build_temporal_features.py --input $FEAT_OUT --output $LOSO_FEATURES --no-xlsx"
    elif [ "$FORCE" = 0 ] && [ -e "$LOSO_FEATURES" ]; then
      log "STAGE 3a/DILEWATI: fitur temporal sudah ada ($LOSO_FEATURES). Pakai --force untuk ulang."
    else
      TEMP_LOG="$LOG_DIR/stage3a_temporal_$STAMP.log"
      PYTHONUNBUFFERED=1 "$PY" scripts/build_temporal_features.py \
        --input "$FEAT_OUT" --output "$LOSO_FEATURES" --no-xlsx 2>&1 | tee "$TEMP_LOG" \
        || { log "FITUR TEMPORAL GAGAL - detail di $TEMP_LOG (tail):"; tail -30 "$TEMP_LOG"; die "FITUR TEMPORAL GAGAL"; }
      log "STAGE 3a SELESAI. Output: $LOSO_FEATURES"
    fi

    # ── 3b. Training LOSO ──
    if [ "$DRY" = 1 ]; then
      info "[dry-run] $PY scripts/run_loso.py --dataset $LOSO_DATASET --features $LOSO_FEATURES --subject-norm $LOSO_SUBJECT_NORM"
    else
      export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
      TRAIN_LOG="$LOG_DIR/stage3_loso_$STAMP.log"
      log "Menjalankan training LOSO (log: $TRAIN_LOG)..."
      (PYTHONUNBUFFERED=1 "$PY" scripts/run_loso.py --dataset "$LOSO_DATASET" \
         --features "$LOSO_FEATURES" --subject-norm "$LOSO_SUBJECT_NORM") 2>&1 | tee "$TRAIN_LOG" \
        || { log "TRAINING LOSO GAGAL - detail di $TRAIN_LOG (tail):"; tail -30 "$TRAIN_LOG"; die "TRAINING LOSO GAGAL"; }

      # ── 3c. Kumpulkan hasil (level subjek, tanpa AUC) ──
      log "Mengumpulkan hasil LOSO ke output/training/$LOSO_DATASET/..."
      PYTHONUNBUFFERED=1 "$PY" scripts/collect_loso_results.py \
        --exp "$LOSO_DATASET" --features "$LOSO_FEATURES" 2>&1 | tee -a "$TRAIN_LOG" \
        || log "PERINGATAN: collect_loso_results.py gagal (manual: $PY scripts/collect_loso_results.py --exp $LOSO_DATASET)"

      # ── 3d. Baseline pembanding (logistik/GBDT + permutation test) ──
      log "Menjalankan baseline pembanding (logistik/GBDT)..."
      PYTHONUNBUFFERED=1 "$PY" scripts/run_loso_baseline.py \
        --dataset "${LOSO_DATASET}_baseline" --features "$LOSO_FEATURES" 2>&1 | tee -a "$TRAIN_LOG" \
        || log "PERINGATAN: run_loso_baseline.py gagal (tidak menggagalkan pipeline)"
    fi
    log "STAGE 3 SELESAI. Hasil: third_party/tabular-dl-tabr-official/exp/tabr/$LOSO_DATASET/ + output/training/$LOSO_DATASET/"
  fi
  confirm_pause
else
  if [ "$RUN_EVAL" = 1 ] && should_run 3; then
    banner 3 "$TOTAL_STAGES" "EVALUASI MODEL DI DATATEST (opsional)" \
      "Muat fitur 608 + model pretrained -> inferensi level event & subjek" \
      "$FEAT_OUT + model pretrained" \
      "hasil di notebook tabr_datatest_event_inference.ipynb" \
      "menit-jam"
    if [ "$DRY" = 1 ]; then
      info "[dry-run] $JUPYTER nbconvert --to notebook --execute --inplace notebooks/tabr_datatest_event_inference.ipynb"
    else
      ensure_kernel
      "$JUPYTER" nbconvert --to notebook --execute --inplace \
        --ExecutePreprocessor.kernel_name=skripsi \
        --ExecutePreprocessor.timeout=3600 \
        notebooks/tabr_datatest_event_inference.ipynb || die "EVALUASI DATATEST GAGAL"
    fi
    log "STAGE 3 SELESAI"
  elif [ "$RUN_EVAL" = 0 ] && should_run 3; then
    log "STAGE 3/DILEWATI: evaluasi datatest opsional. Jalankan dengan --eval."
  fi
fi

# ----------------------------------------------------------------------------
# Ringkasan
# ----------------------------------------------------------------------------
echo ""
log "══════════════════════════════════════════════════════════"
log "PIPELINE MODE=$MODE SELESAI"
log "Log lengkap: $LOG"
log "Stage yang dijalankan: dari stage $FROM_STAGE sampai selesai"
log "══════════════════════════════════════════════════════════"

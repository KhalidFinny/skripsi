#!/usr/bin/env bash
# ============================================================================
# run_pipeline_v3.sh — SPOTTING → EKSTRAKSI → FITUR → GERBANG → TRAINING → HASIL
# satu perintah, berurutan, gagal di satu stage = berhenti di situ.
#
# Ini pipeline BERSIH (v3): block_size POC 9 (bukan 7), definisi ROI dari
# features/roi_config.py (mata = kelopak saja, tidak lagi tumpang
# tindih dengan alis), fitur arah bertanda (mean_x/mean_y), frame onset ikut
# tersimpan, dan pemilihan epoch cross-entropy.
#
# Keluaran lama TIDAK disentuh: spotting menulis ke output/apex_v2/, fitur ke
# experiments/features/apex/*_v3*.
#
# Pemakaian:
#   ./pipeline/run.sh                 semua stage, dari awal
#   ./pipeline/run.sh --from 2        mulai dari stage 2 (lanjutkan)
#   ./pipeline/run.sh --stage 6       HANYA stage 6
#   ./pipeline/run.sh --force         jalankan ulang walau output ada
#   ./pipeline/run.sh --pause         konfirmasi sebelum tiap stage
#   ./pipeline/run.sh --dry-run       cetak rencana saja
#   ./pipeline/run.sh --no-gate       lewati stage gerbang (5)
#   ./pipeline/run.sh --no-train      berhenti setelah stage 5
#   ./pipeline/run.sh --fresh         HAPUS output/apex_v2 + fitur v3 dulu
#   ./pipeline/run.sh --config experiments/configs/tabr_loso_roi25_reg.toml
#   V3_PRESPLIT=1 ./pipeline/run.sh --fresh   MODE FOLD-FIRST (lihat bawah)
#
# Stage:
#   0 presplit      (HANYA mode fold-first: bagi 56 orang -> 44 train + 12 holdout,
#                    SEBELUM spotting; output/presplit/{split.csv,*_persons.txt})
#   1 spotting      (560 video, ~50 menit, resume otomatis; mode fold-first: 440
#                    video milik 44 orang train pool saja — 12 orang holdout
#                    TIDAK dibaca sampai stage 8)
#   2 ekstraksi     POC-ABS + geometri/head pose, satu pass (~35 menit)
#   3 cache pkl     (~3 menit)
#   4 temporal      (detik)
#   5 gerbang       within-subject x3 keluarga fitur (wasit: ada sinyal atau tidak)
#   6 training      LOSO TabR 56 fold x 3 seed, log ringkas (mode fold-first: 44 fold)
#   7 hasil         collect (MCC/bias/ambang dari val) + baseline pembanding
#   8 holdout       (HANYA mode fold-first: spotting+fitur 12 orang holdout ->
#                    gabung tabel -> SATU fold final (test=12 orang) -> model final
#                    + satu angka jujur di output/training/<dataset>_holdout/)
#
# MODE FOLD-FIRST (V3_PRESPLIT=1): split train/test per orang terjadi SEBELUM
# spotting. Secara matematis protokol lama sudah bebas bocor (split subjek-
# disjoint + imputer/scaler fit train saja), jadi mode ini BUKAN perbaikan
# bocor — ia jaminan STRUKTURAL: video 12 orang holdout tidak pernah dibaca
# sampai evaluasi akhir, dan semua keputusan tuning (config, deskriptor)
# hanya melihat 44 orang. Env pendamping:
#   V3_PRESPLIT_DIR=output/presplit  V3_TEST_PEOPLE=12  V3_PRESPLIT_SEED=42
#   V3_HOLDOUT_OUT_ROOT=output/apex_v2_holdout
#
# MULTI-CONFIG SATU RUN (bukan A/B manual): V3_EXTRA_CONFIGS berisi config
# tambahan (dipisah spasi) yang ikut dilatih di stage 6/7/8 dengan dataset
# turunan <dataset>_cfg_<tag>. Fitur (stage 1-5) hanya dihitung sekali.
# Contoh run penuh (fold-first + sinyal spotting combo tervalidasi CAS(ME)2
# + config roi25_reg kapasitas besar):
#   V3_PRESPLIT=1 V3_SPOT_SIGNAL=combo \
#   V3_EXTRA_CONFIGS="experiments/configs/tabr_loso_roi25_reg.toml" \
#     ./pipeline/run.sh --fresh
#
# LEVER spotting anti-noise (deep dive 2026-10-13, kandidat PENGGANTI combo
# yang gagal pindah ke data lapangan). Keduanya GATED, default tidak berubah:
#   V3_SPOT_MOTION_COMP=1  LEVER 1: kompensasi gerakan global/rigid (kurangi
#                          median antar-blok dx,dy per frame) -> buang gerakan
#                          kepala/latar yang serentak, sisakan deviasi lokal.
#   V3_SPOT_SIGNAL=mdmd    LEVER 2: Main Directional Maximal Difference
#                          (Wang 2017): beda sinyal vs rata-rata tetangga
#                          ±V3_SPOT_MDMD_K (default 5). Tren lambat (kepala)
#                          hilang, puncak tajam (ekspresi) selamat.
#   V3_SPOT_MDMD_K=5       jendela MDMD (frame).
# Contoh A/B kedua lever (fitur sekali, 2 config):
#   V3_PRESPLIT=1 V3_SPOT_MOTION_COMP=1 V3_SPOT_SIGNAL=mdmd \
#   V3_EXTRA_CONFIGS="experiments/configs/tabr_loso_roi25_reg.toml" \
#     ./pipeline/run.sh --fresh
#
# Precision-first OF-FD proxy (CAS(ME)^2 sweep 2026-10-14):
#   V3_SPOT_ALGO=of_fd_proxy
#   V3_SPOT_OF_FD_MAD=3.5 V3_SPOT_OF_FD_TOP=mean V3_SPOT_OF_FD_SMOOTH=35
#   V3_SPOT_OF_FD_BOUNDARY_BETA=0.3
# ============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# ----------------------------------------------------------------------------
# Argumen
# ----------------------------------------------------------------------------
FORCE=0
PAUSE=0
DRY=0
FRESH=0
NO_GATE=0
NO_TRAIN=0
ONLY_STAGE=""
FROM_STAGE=1

while [ $# -gt 0 ]; do
  case "$1" in
    --stage)    ONLY_STAGE="$2"; FROM_STAGE="$2"; shift 2 ;;
    --from)     FROM_STAGE="$2"; shift 2 ;;
    --force)    FORCE=1; shift ;;
    --pause)    PAUSE=1; shift ;;
    --dry-run)  DRY=1; shift ;;
    --fresh)    FRESH=1; shift ;;
    --no-gate)  NO_GATE=1; shift ;;
    --no-train) NO_TRAIN=1; shift ;;
    --config)   TRAIN_CONFIG="$2"; shift 2 ;;
    --dataset)  LOSO_DATASET="$2"; shift 2 ;;
    *) echo "ARGUMEN TIDAK DIKENAL: $1"; exit 1 ;;
  esac
done

# ----------------------------------------------------------------------------
# Konfigurasi (bisa dioverride lewat env)
# ----------------------------------------------------------------------------
PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || PY="python"

RAW_ROOT="${V3_RAW_ROOT:-/run/media/finny/New Volume/dataset/anxiety_raw}"
OUT_ROOT="${V3_OUT_ROOT:-$ROOT/output/apex_v2}"
FEAT_DIR="$ROOT/experiments/features/apex"

FEAT_TAG="${V3_FEAT_TAG:-poc_abs_roi_signals_v3}"
FEAT_XLSX="$FEAT_DIR/${FEAT_TAG}.xlsx"     # per frame, POC-ABS saja
FEAT_PKL="$FEAT_DIR/${FEAT_TAG}_full.pkl"

# ---------------------------------------------------------------------------
# DESKRIPTOR TEMPORAL (audit 2026-10-10, Iterasi 4.51)
# ---------------------------------------------------------------------------
# Default = `rise` SAJA. Ablasi keluarga fitur pada gerbang within-subject:
#   rise (55 fitur)  BA 0,8333  p 0,0020   <- signifikan
#   SEMUA (335)      BA 0,6389  p 0,1045
#   magnitude (125)  BA 0,6111  p 0,0995
# Menambah deskriptor lain MENGENCERKAN sinyal (rise+auc 0,694; rise+arah 0,750).
# `rise` = kemiringan onset->apex: yang informatif adalah KECEPATAN onset
# micro-expression, bukan besaran gerakan.
# Lihat report/findings/audit-feature-representation.md.
#
# V3_DESCRIPTORS="peak ttp rise fall auc" memulihkan perilaku lama (semua).
# Nama berkas ikut berubah supaya isinya jelas dan berkas lama tidak tertimpa.
V3_DESCRIPTORS="${V3_DESCRIPTORS:-rise}"
V3_ONLY_DESCRIPTORS="${V3_ONLY_DESCRIPTORS:-1}"
# Label training. Default `session` = pertanyaan STATE (tesis): "apakah orang
# ini cemas HARI INI" -> semua sesi (before+after), label = kondisi sesi.
# Ini beda dari `person` (pertanyaan TRAIT: tebak tingkat kecemasan orang),
# yang membuang sesi `before` dan gagal konsisten (test < baseline 55,36%).
# STATE adalah tempat gerbang within-subject signifikan (BA 0,75, p 0,010).
# Setel V3_LABEL_UNIT=person untuk perilaku trait lama.
V3_LABEL_UNIT="${V3_LABEL_UNIT:-session}"
ALL_DESCRIPTORS="peak ttp rise fall auc"
if [ "$V3_DESCRIPTORS" = "$ALL_DESCRIPTORS" ]; then
  DESC_SUFFIX=""
else
  DESC_SUFFIX="_$(echo "$V3_DESCRIPTORS" | tr ' ' '-')"
fi
FEAT_TEMPORAL="$FEAT_DIR/${FEAT_TAG}_poc_temporal${DESC_SUFFIX}.pkl"  # + onset->apex->offset
DESC_ARGS=(--descriptors $V3_DESCRIPTORS)
[ "$V3_ONLY_DESCRIPTORS" = "1" ] && DESC_ARGS+=(--only-descriptors)

# --drop-features: `*_max_m` (nilai tersensor di batas block_size) hanya ada
# kalau sinyal dasar per-frame ikut dibawa. Pada mode --only-descriptors kolom
# itu tidak ada, dan run_loso.py MEMATALAKAN drop yang tidak cocok dengan kolom
# mana pun ("tidak cocok dengan kolom mana pun") -> harus dikosongkan.
if [ "$V3_ONLY_DESCRIPTORS" = "1" ]; then
  V3_DROP_FEATURES="${V3_DROP_FEATURES:-}"
else
  V3_DROP_FEATURES="${V3_DROP_FEATURES:-_max_m\$}"
fi

# PIPELINE INI MURNI POC-ABS.
# Keluarga fitur geometri/head-pose (--with-geometry, "Differential AU") DIHAPUS
# dari alur. Dasarnya hasil terukur pada protokol LOSO bebas-bocor (changes-log
# Iterasi 4.2x dan 4.32):
#   POC-ABS saja    AUC 0,6142   (terbaik yang pernah dicatat)
#   POC + geometri  AUC 0,4387   -> BAWAH acak
# Fitur geometri mengodekan identitas subjek (72% varians = antar-orang), bukan
# kondisi kecemasan. Menambahkannya MENGHANCURKAN sinyal lemah yang sudah ada.
# Kode --with-geometry masih ada di extract_features_poc_abs.py kalau nanti perlu
# dibandingkan lagi; pipeline tidak lagi memanggilnya.
GATE_TAG="${V3_GATE_TAG:-within_subject_v3}"
TRAIN_FEATURES="${TRAIN_FEATURES:-$FEAT_TEMPORAL}"

LOSO_DATASET="${LOSO_DATASET:-convat_apex_anxiety_loso_roi25_reg}"
# CATATAN: default ini HARUS sama dengan `[data] path` di TRAIN_CONFIG. Di
# run_loso.py, --dataset selalu menimpa `[data] path` (lihat template['data']
# ['path'] = f':data/{dataset_name}'), jadi config yang di-tuning pada satu
# dataset bisa diam-diam dilatih pada dataset lain.
# Pernah terjadi: default masih `_v3_geo` (402 fitur) padahal config compact
# di-tuning di `_roi25_reg` (237 fitur) -> hasil jatuh ke bawah acak
# (MCC -0,0175, AUC 0,4723). run_loso.py kini memperingatkan kalau keduanya
# tidak cocok.
# Config default = KAPASITAS MINIMAL (compact). Dipilih karena satu-satunya yang
# overfitting-nya praktis NOL (gap train-val -0,0055, train < val) dan AUC-nya
# IDENTIK dengan config reg yang 4x lebih besar (0,6142). Config reg punya gap
# train-test 0,3327 = hafalan 33 poin yang harus dimaafkan di sidang.
# Config `_reg_ce` (cross-entropy) terbukti REGRESI: pemilihan epoch CE berhenti
# di epoch <= 1 pada 40-48 dari 56 fold, jadi model nyaris belum belajar
# (changes-log Iterasi 4.22). Jangan dipakai.
# Ganti dengan --config experiments/configs/tabr_loso_roi25_reg.toml kalau mau
# membandingkan dengan kapasitas lebih besar.
TRAIN_CONFIG="${TRAIN_CONFIG:-$ROOT/experiments/configs/tabr_loso_compact.toml}"
TRAIN_SEEDS="${V3_SEEDS:-3}"

# Daftar config yang dilatih dalam SATU run (bukan A/B manual terpisah).
# Config pertama = primer (dataset $LOSO_DATASET). Sisanya dari
# V3_EXTRA_CONFIGS (dipisah spasi); tiap config ekstra mendapat dataset
# turunan ${LOSO_DATASET}_cfg_<tag> supaya fold/hasilnya tidak menimpa primer.
# Tag = nama berkas tanpa .toml dan tanpa awalan tabr_loso_.
# Contoh: V3_EXTRA_CONFIGS="experiments/configs/tabr_loso_roi25_reg.toml"
#   -> dataset convat_apex_anxiety_loso_roi25_reg_cfg_roi25_reg
# Stage 6 (LOSO), 7 (collect), dan 8 (holdout) mengulang untuk tiap config;
# fitur (stage 1-5) hanya dihitung SEKALI karena identik.
CONFIG_LIST=("$TRAIN_CONFIG")
DATASET_LIST=("$LOSO_DATASET")
for extra in ${V3_EXTRA_CONFIGS:-}; do
  if [ ! -f "$extra" ]; then
    echo "GAGAL: V3_EXTRA_CONFIGS: config tidak ditemukan: $extra"; exit 1
  fi
  stem=$(basename "$extra" .toml); stem=${stem#tabr_loso_}
  CONFIG_LIST+=("$extra")
  DATASET_LIST+=("${LOSO_DATASET}_cfg_${stem}")
done

# ---------------------------------------------------------------------------
# MODE FOLD-FIRST (pre-split sebelum spotting). Lihat header.
# ---------------------------------------------------------------------------
PRESPLIT="${V3_PRESPLIT:-0}"
PRESPLIT_DIR="${V3_PRESPLIT_DIR:-$ROOT/output/presplit}"
HOLDOUT_OUT_ROOT="${V3_HOLDOUT_OUT_ROOT:-$ROOT/output/apex_v2_holdout}"

# --force HARUS diteruskan ke run_loso.py (bukan cuma stage 2-4): tanpa ini
# fold dilewati karena DONE.json lama dan pipeline melaporkan SELESAI dengan
# hasil lama - diam-diam. Didefinisikan sekali, dipakai stage 6 dan 8.
FORCE_ARG=()
[ "$FORCE" = 1 ] && FORCE_ARG=(--force)

STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/pipeline_v3_${STAMP}.log"

log()  { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }
die()  { echo "[$(date '+%F %T')] GAGAL: $*" | tee -a "$LOG"; exit 1; }
info() { echo "  $*" | tee -a "$LOG"; }

banner() {
  local n="$1" total="$2" judul="$3" apa="$4" input="$5" output="$6" eta="$7"
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG"
  echo "STAGE $n/$total : $judul" | tee -a "$LOG"
  echo "  APA YANG DILAKUKAN : $apa" | tee -a "$LOG"
  echo "  INPUT              : $input" | tee -a "$LOG"
  echo "  OUTPUT             : $output" | tee -a "$LOG"
  echo "  ESTIMASI WAKTU     : $eta" | tee -a "$LOG"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG"
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

run_stage() {
  # run_stage <n> <judul log> <perintah...>
  local n="$1"; shift
  local name="$1"; shift
  local stage_log="$LOG_DIR/stage${n}_${name}_${STAMP}.log"
  log "  log: $stage_log"
  ( PYTHONUNBUFFERED=1 "$@" ) 2>&1 | tee "$stage_log" \
    || { log "STAGE $n GAGAL - detail di $stage_log (tail):"; tail -30 "$stage_log"; die "STAGE $n GAGAL"; }
}

TOTAL_STAGES=7
[ "$PRESPLIT" = 1 ] && TOTAL_STAGES=8

log "══════════════════════════════════════════════════════════"
log "PIPELINE v3 — block_size 9, ROI kanonik, arah bertanda"
log "  RAW        : $RAW_ROOT"
log "  OUT        : $OUT_ROOT"
log "  FITUR      : $FEAT_XLSX"
log "  DATASET    : $LOSO_DATASET"
log "  CONFIG     : $TRAIN_CONFIG"
log "  seeds/fold : $TRAIN_SEEDS"
if [ "$PRESPLIT" = 1 ]; then
  log "  FOLD-FIRST : AKTIF — split per orang SEBELUM spotting"
  log "  presplit   : $PRESPLIT_DIR (train pool -> stage 1-7, holdout -> stage 8)"
  log "  holdout out: $HOLDOUT_OUT_ROOT"
fi
log "  Log        : $LOG"
log "══════════════════════════════════════════════════════════"

# ----------------------------------------------------------------------------
# Cek awal
# ----------------------------------------------------------------------------
[ -f "$ROOT/models/shape_predictor_68_face_landmarks.dat" ] \
  || die "shape predictor tidak ditemukan di models/"
[ -f "$TRAIN_CONFIG" ] || die "config training tidak ditemukan: $TRAIN_CONFIG"

if [ "$FRESH" = 1 ]; then
  # PENJAGA: klip event TIDAK BISA dibuat ulang tanpa video mentah. Kalau driv
  # raw tidak ter-mount, menghapus $OUT_ROOT berarti kehilangan 6.972 klip
  # (9,5 GB) yang tidak ada penggantinya. Karena itu hapus klip HANYA kalau
  # sumbernya benar-benar ada.
  if [ -d "$RAW_ROOT" ]; then
    log "FRESH: menghapus $OUT_ROOT (klip + metadata) dan fitur v3"
    [ "$DRY" = 1 ] || rm -rf "$OUT_ROOT"
    if [ "$PRESPLIT" = 1 ]; then
      # Presplit butuh driv mentah untuk scan nama direktori; klip holdout
      # juga tidak bisa dibuat ulang tanpanya. Keduanya di dalam penjaga yang
      # sama dengan $OUT_ROOT.
      log "FRESH (fold-first): menghapus $PRESPLIT_DIR dan $HOLDOUT_OUT_ROOT"
      [ "$DRY" = 1 ] || rm -rf "$PRESPLIT_DIR" "$HOLDOUT_OUT_ROOT"
      [ "$DRY" = 1 ] || rm -f "$FEAT_DIR"/${FEAT_TAG}_holdout*.xlsx "$FEAT_DIR"/${FEAT_TAG}_holdout*.pkl \
                            "$FEAT_DIR"/${FEAT_TAG}_combined*.pkl
    fi
  else
    log "FRESH: driv mentah TIDAK ada ($RAW_ROOT)."
    log "  Klip event TIDAK dihapus - kalau dihapus, tidak ada cara membuatnya ulang."
    log "  Metadata dibangun ulang dari klip yang ada (stage 1 resume)."
  fi
  [ "$DRY" = 1 ] || rm -f "$FEAT_DIR"/${FEAT_TAG}*.xlsx "$FEAT_DIR"/${FEAT_TAG}*.pkl
  # Semua config dalam run ini (primer + V3_EXTRA_CONFIGS) dibersihkan,
  # termasuk varian _holdout-nya pada mode fold-first.
  for ds in "${DATASET_LIST[@]}"; do
    [ "$DRY" = 1 ] || rm -rf "$ROOT/output/training/$ds" "$ROOT/output/training/${ds}_baseline" \
                          "$ROOT/third_party/tabular-dl-tabr-official/exp/tabr/$ds" \
                          "$ROOT/third_party/tabular-dl-tabr-official/data/$ds"
    if [ "$PRESPLIT" = 1 ]; then
      [ "$DRY" = 1 ] || rm -rf "$ROOT/output/training/${ds}_holdout" \
                            "$ROOT/third_party/tabular-dl-tabr-official/exp/tabr/${ds}_holdout" \
                            "$ROOT/third_party/tabular-dl-tabr-official/data/${ds}_holdout"
    fi
  done
  [ "$DRY" = 1 ] || rm -rf "$ROOT/output/training/${GATE_TAG}_poc" \
                        "$ROOT/output/training/${GATE_TAG}_geo_temporal"
  log "FRESH: fitur v3 + hasil training + exp/tabr + data dibersihkan (${#DATASET_LIST[@]} config)."
fi

# Driv mentah hanya dibutuhkan kalau stage 1 benar-benar akan menghitung ulang.
# Kalau klip sudah ada, stage 1 cukup membangun ulang metadata -> tanpa driv.
if should_run 1 && [ ! -d "$RAW_ROOT" ]; then
  if [ -d "$OUT_ROOT/dataset" ] && [ -n "$(find "$OUT_ROOT/dataset" -mindepth 6 -maxdepth 6 -type d -name 'event_*' -print -quit 2>/dev/null)" ]; then
    log "PERINGATAN: driv mentah tidak ada ($RAW_ROOT)."
    log "  Stage 1 akan MEMBANGUN ULANG metadata dari klip yang sudah ada (tanpa spotting ulang)."
    log "  Set V3_RAW_ROOT kalau memang ingin re-spotting dari video."
    SPOT_REBUILD_ONLY=1
  else
    die "dataset mentah tidak ditemukan: $RAW_ROOT (set V3_RAW_ROOT) dan tidak ada klip lama untuk dipakai ulang"
  fi
fi

# ----------------------------------------------------------------------------
# STAGE 0 — PRE-SPLIT (hanya mode fold-first)
# ----------------------------------------------------------------------------
# FROM_STAGE default = 1, jadi should_run 0 hanya true bila user minta eksplisit.
# Tapi presplit WAJIB ada sebelum stage 1 pada mode fold-first -> jalankan juga
# bila berkasnya belum ada (idempoten: seed tetap -> split tetap).
if [ "$PRESPLIT" = 1 ] && { should_run 0 || [ ! -s "$PRESPLIT_DIR/test_persons.txt" ]; }; then
  banner 0 "$TOTAL_STAGES" "PRE-SPLIT PER ORANG (sebelum spotting)" \
    "Bagi 56 orang -> train pool + ${V3_TEST_PEOPLE:-12} holdout test (strata label-pair, seed ${V3_PRESPLIT_SEED:-42}). Holdout TIDAK dibaca pipeline sampai stage 8." \
    "$RAW_ROOT (nama direktori saja, video tidak dibuka)" \
    "$PRESPLIT_DIR/{split.csv,train_persons.txt,test_persons.txt,summary.md}" \
    "CEPAT (detik)"
  if [ "$DRY" = 1 ]; then
    info "[dry-run] $PY pipeline/stages/stage_0_presplit.py --raw-root '$RAW_ROOT' --out $PRESPLIT_DIR --test-people ${V3_TEST_PEOPLE:-12} --seed ${V3_PRESPLIT_SEED:-42}"
  else
    run_stage 0 presplit "$PY" pipeline/stages/stage_0_presplit.py \
      --raw-root "$RAW_ROOT" --out "$PRESPLIT_DIR" \
      --test-people "${V3_TEST_PEOPLE:-12}" --seed "${V3_PRESPLIT_SEED:-42}"
    log "STAGE 0 SELESAI: $(wc -l < "$PRESPLIT_DIR/train_persons.txt") orang train pool, $(wc -l < "$PRESPLIT_DIR/test_persons.txt") orang holdout."
  fi
  confirm_pause
fi

# ----------------------------------------------------------------------------
# STAGE 1 — SPOTTING
# ----------------------------------------------------------------------------
if should_run 1; then
  banner 1 "$TOTAL_STAGES" "SPOTTING (cari apex/event)" \
    "Deteksi wajah (dlib) -> POC-ABS per frame -> cari apex -> simpan klip event + neutral.png" \
    "$RAW_ROOT (*.avi)" \
    "$OUT_ROOT/dataset/... + metadata.xlsx" \
    "SEDANG (~50 menit, 560 video) - resume otomatis: sample yang sudah ada dilewati"
  # Mode fold-first: spotting HANYA membaca video milik orang train pool.
  SPOT_INCLUDE=()
  if [ "$PRESPLIT" = 1 ]; then
    [ -s "$PRESPLIT_DIR/train_persons.txt" ] \
      || die "mode fold-first tapi $PRESPLIT_DIR/train_persons.txt tidak ada (jalankan stage 0)"
    SPOT_INCLUDE=(SPOT_INCLUDE_PERSONS="$PRESPLIT_DIR/train_persons.txt")
    info "fold-first: SPOT_INCLUDE_PERSONS=$PRESPLIT_DIR/train_persons.txt (holdout tidak dibaca)"
  fi
  if [ "$DRY" = 1 ]; then
    info "[dry-run] SPOT_DATASET_ROOT=$RAW_ROOT SPOT_OUTPUT_ROOT=$OUT_ROOT ${SPOT_INCLUDE[*]:-} SPOT_ALGO=${V3_SPOT_ALGO:-phase} SPOT_SIGNAL=${V3_SPOT_SIGNAL:-mean_m} SPOT_MOTION_COMP=${V3_SPOT_MOTION_COMP:-0} SPOT_MDMD=${V3_SPOT_MDMD:-0} SPOT_MDMD_K=${V3_SPOT_MDMD_K:-5} SPOT_REBUILD_METADATA_ONLY=${SPOT_REBUILD_ONLY:-0} $PY pipeline/stages/stage_1_spotting.py"
  else
    run_stage 1 spotting \
      env SPOT_DATASET_ROOT="$RAW_ROOT" \
          SPOT_OUTPUT_ROOT="$OUT_ROOT" \
          SPOT_VIDEO_EXT=".avi" \
          SPOT_ABS=1 \
          SPOT_OVERWRITE=0 \
          SPOT_NO_EVENT_SIGNAL=1 \
          SPOT_SAVE_NEUTRAL=1 \
          SPOT_CUTOFF="${V3_SPOT_CUTOFF:-0.3}" \
          SPOT_ALGO="${V3_SPOT_ALGO:-phase}" \
          SPOT_SIGNAL="${V3_SPOT_SIGNAL:-mean_m}" \
          SPOT_MOTION_COMP="${V3_SPOT_MOTION_COMP:-0}" \
          SPOT_MDMD="${V3_SPOT_MDMD:-0}" \
          SPOT_MDMD_K="${V3_SPOT_MDMD_K:-5}" \
          SPOT_OF_FD_MAD="${V3_SPOT_OF_FD_MAD:-3.5}" \
          SPOT_OF_FD_TOP="${V3_SPOT_OF_FD_TOP:-mean}" \
          SPOT_OF_FD_SMOOTH="${V3_SPOT_OF_FD_SMOOTH:-35}" \
          SPOT_OF_FD_WIDTH="${V3_SPOT_OF_FD_WIDTH:-35}" \
          SPOT_OF_FD_DISTANCE="${V3_SPOT_OF_FD_DISTANCE:-12}" \
          SPOT_OF_FD_BOUNDARY_BETA="${V3_SPOT_OF_FD_BOUNDARY_BETA:-0.3}" \
          SPOT_REBUILD_METADATA_ONLY="${SPOT_REBUILD_ONLY:-0}" \
          "${SPOT_INCLUDE[@]}" \
          MPLBACKEND=Agg \
      "$PY" pipeline/stages/stage_1_spotting.py
    [ -s "$OUT_ROOT/metadata.xlsx" ] || die "metadata.xlsx tidak terbentuk: $OUT_ROOT/metadata.xlsx"
    log "STAGE 1 SELESAI. metadata baris: $("$PY" -c "import pandas as pd;print(len(pd.read_excel('$OUT_ROOT/metadata.xlsx')))")"
  fi
  confirm_pause
fi

# ----------------------------------------------------------------------------
# STAGE 2 — EKSTRAKSI FITUR
# ----------------------------------------------------------------------------
if should_run 2; then
  banner 2 "$TOTAL_STAGES" "EKSTRAKSI FITUR POC-ABS" \
    "POC-ABS per frame vs acuan NETRAL per orang (5 ROI). Arah + magnitudo motion vector per blok." \
    "$OUT_ROOT/dataset/... + metadata.xlsx" \
    "$FEAT_XLSX" \
    "SEDANG (~30 menit) - 3 worker (4 worker pernah menyentuh 95C)"
  if [ "$DRY" = 1 ]; then
    info "[dry-run] FEAT_DATASET_ROOT=$OUT_ROOT/dataset $PY pipeline/stages/stage_2_extract_features.py --roi-signals --baseline neutral"
  elif [ "$FORCE" = 0 ] && [ -e "$FEAT_XLSX" ]; then
    log "STAGE 2/DILEWATI: sudah ada $FEAT_XLSX. Pakai --force untuk ulang."
  else
    run_stage 2 ekstraksi \
      env FEAT_WORKERS=3 \
          FEAT_DATASET_ROOT="$OUT_ROOT/dataset" \
          FEAT_METADATA_PATH="$OUT_ROOT/metadata.xlsx" \
      "$PY" pipeline/stages/stage_2_extract_features.py \
        --roi-signals --baseline neutral --output "$FEAT_XLSX"
    [ -s "$FEAT_XLSX" ] || die "tabel fitur tidak terbentuk: $FEAT_XLSX"
    log "STAGE 2 SELESAI. Output: $FEAT_XLSX"
  fi
  confirm_pause
fi

# ----------------------------------------------------------------------------
# STAGE 3 — CACHE PKL
# ----------------------------------------------------------------------------
if should_run 3; then
  banner 3 "$TOTAL_STAGES" "CACHE PKL" \
    "Konversi xlsx -> pkl (bit-identik) supaya pembacaan turun dari ~90s ke <1s" \
    "$FEAT_XLSX" \
    "$FEAT_PKL" \
    "CEPAT (~3 menit)"
  if [ "$DRY" = 1 ]; then
    info "[dry-run] $PY pipeline/stages/stage_3_cache.py --xlsx $FEAT_XLSX --pkl $FEAT_PKL"
  elif [ "$FORCE" = 0 ] && [ -e "$FEAT_PKL" ]; then
    log "STAGE 3/DILEWATI: sudah ada $FEAT_PKL. Pakai --force untuk ulang."
  else
    run_stage 3 cache "$PY" pipeline/stages/stage_3_cache.py --xlsx "$FEAT_XLSX" --pkl "$FEAT_PKL"
    log "STAGE 3 SELESAI. Output: $FEAT_PKL"
  fi
  confirm_pause
fi

# ----------------------------------------------------------------------------
# STAGE 4 — FITUR TEMPORAL
# ----------------------------------------------------------------------------
if should_run 4; then
  banner 4 "$TOTAL_STAGES" "FITUR TEMPORAL" \
    "Ringkas tiap lintasan onset->apex->offset jadi deskriptor ($V3_DESCRIPTORS) untuk sinyal POC-ABS (diagregasi mean+std saat training)" \
    "$FEAT_PKL" \
    "$FEAT_TEMPORAL" \
    "CEPAT (detik)"
  if [ "$DRY" = 1 ]; then
    info "[dry-run] $PY pipeline/stages/stage_4_temporal.py --input $FEAT_PKL --output $FEAT_TEMPORAL ${DESC_ARGS[*]} --no-xlsx"
  elif [ "$FORCE" = 0 ] && [ -e "$FEAT_TEMPORAL" ]; then
    log "STAGE 4/DILEWATI: sudah ada $FEAT_TEMPORAL. Pakai --force untuk ulang."
  else
    run_stage 4 temporal "$PY" pipeline/stages/stage_4_temporal.py \
      --input "$FEAT_PKL" --output "$FEAT_TEMPORAL" "${DESC_ARGS[@]}" --no-xlsx
    log "STAGE 4 SELESAI. Output: $FEAT_TEMPORAL"
  fi
  confirm_pause
fi

# ----------------------------------------------------------------------------
# STAGE 5 — GERBANG WITHIN-SUBJECT (wasit: ada sinyal atau tidak)
# ----------------------------------------------------------------------------
if [ "$NO_GATE" = 0 ] && should_run 5; then
  banner 5 "$TOTAL_STAGES" "GERBANG WITHIN-SUBJECT (POC-ABS)" \
    "Orang yang sama, wajah sama, label beda: uji berpasangan + klasifikasi LOSO dalam-subjek. Ini wasit apakah POC-ABS membawa sinyal." \
    "$FEAT_PKL (per frame) + $FEAT_TEMPORAL (temporal)" \
    "output/training/${GATE_TAG}_{poc,geo_temporal}/" \
    "CEPAT (menit)"
  if [ "$DRY" = 1 ]; then
    info "[dry-run] $PY pipeline/stages/stage_5_gate.py --features $FEAT_PKL --out output/training/${GATE_TAG}_poc"
    info "[dry-run] $PY pipeline/stages/stage_5_gate.py --features $FEAT_TEMPORAL --out output/training/${GATE_TAG}_geo_temporal"
  else
    run_stage 5 gerbang_poc "$PY" pipeline/stages/stage_5_gate.py \
      --features "$FEAT_PKL" --out output/training/${GATE_TAG}_poc
    run_stage 5 gerbang_gabungan "$PY" pipeline/stages/stage_5_gate.py \
      --features "$FEAT_TEMPORAL" --out output/training/${GATE_TAG}_geo_temporal
    log "STAGE 5 SELESAI. Ringkasan:"
    log "  output/training/${GATE_TAG}_poc/summary.md"
  fi
  confirm_pause
fi

if [ "$NO_TRAIN" = 1 ]; then
  log "NO-TRAIN: berhenti setelah stage 5 (sesuai --no-train)."
  log "Log lengkap: $LOG"
  exit 0
fi

# ----------------------------------------------------------------------------
# STAGE 6 — TRAINING LOSO TabR
# ----------------------------------------------------------------------------
if should_run 6; then
  banner 6 "$TOTAL_STAGES" "TRAINING LOSO TabR (${#CONFIG_LIST[@]} config)" \
    "fold LOSO (1 subjek = test) x $TRAIN_SEEDS seed, baris = subjek (mean+std), epoch dipilih via akurasi, log ringkas (1 baris/fold); diulang per config: ${DATASET_LIST[*]}" \
    "$TRAIN_FEATURES" \
    "third_party/tabular-dl-tabr-official/exp/tabr/<dataset>/fold_*/" \
    "LAMA (~1-2 jam per config) - resume otomatis per fold (DONE.json)"
  for ci in "${!CONFIG_LIST[@]}"; do
    CFG="${CONFIG_LIST[$ci]}"
    DS="${DATASET_LIST[$ci]}"
    [ "$ci" -eq 0 ] && STAGE_NAME="loso" || STAGE_NAME="loso_cfg_${ci}"
    log "  config $((ci + 1))/${#CONFIG_LIST[@]}: $CFG -> dataset $DS"
    if [ "$DRY" = 1 ]; then
      info "[dry-run] $PY pipeline/stages/stage_6_train_loso.py --dataset $DS --features $TRAIN_FEATURES --aggregate subject --subject-norm none --label-unit $V3_LABEL_UNIT --drop-features '$V3_DROP_FEATURES' --config $CFG --seeds $TRAIN_SEEDS --epochs-trace ${V3_EPOCHS_TRACE:-40} --device ${TRAIN_DEVICE:-cpu} --epochs-log $([ "$FORCE" = 1 ] && echo '--force ')--quiet"
      continue
    fi
    # Device default CPU: data ini 44 baris train x <=660 fitur, GPU tidak
    # mempercepat apa pun, tapi 168 konteks CUDA berurutan membebani driver di
    # GPU kecil (dilaporkan bikin mesin reboot). Set TRAIN_DEVICE=cuda untuk GPU.
    # Jangan export CUDA_VISIBLE_DEVICES di sini: run_loso.py yang mengaturnya
    # SESUAI --device, dan harus dilakukan sebelum torch diimpor.
    # FORCE_ARG didefinisikan di blok konfigurasi (dipakai juga stage 8).
    run_stage 6 "$STAGE_NAME" "$PY" pipeline/stages/stage_6_train_loso.py \
      --dataset "$DS" \
      --features "$TRAIN_FEATURES" \
      --aggregate subject \
      --subject-norm none \
      --label-unit "$V3_LABEL_UNIT" \
      --drop-features "$V3_DROP_FEATURES" \
      --device "${TRAIN_DEVICE:-cpu}" \
      --epochs-log \
      --config "$CFG" \
      --seeds "$TRAIN_SEEDS" \
      --epochs-trace "${V3_EPOCHS_TRACE:-40}" \
      "${FORCE_ARG[@]}" \
      --quiet

    # run_loso.py menangkap error PER FOLD dan tetap keluar dengan kode 0, jadi
    # tanpa cek ini pipeline bisa melaporkan "SELESAI" padahal SEMUA fold gagal
    # (pernah terjadi: config cross-entropy -> KeyError di 56/56 fold).
    DONE_N=$(find "$ROOT/third_party/tabular-dl-tabr-official/exp/tabr/$DS" \
             -name DONE.json 2>/dev/null | wc -l)
    if [ "$DONE_N" -eq 0 ]; then
      log "  tidak ada fold yang selesai. Contoh kegagalan terakhir:"
      LAST_FAIL=$(find "$ROOT/third_party/tabular-dl-tabr-official/exp/tabr/$DS" \
                  -name FAILED.txt 2>/dev/null | sort | tail -1)
      [ -n "$LAST_FAIL" ] && tail -15 "$LAST_FAIL" | tee -a "$LOG"
      die "TRAINING GAGAL: 0 fold selesai untuk $DS (detail: $LOG_DIR/stage6_${STAGE_NAME}_*.log)"
    fi
    log "  config $((ci + 1)) selesai: $DONE_N fold ($DS)"
  done
  [ "$DRY" = 1 ] || log "STAGE 6 SELESAI (${#CONFIG_LIST[@]} config)."
  confirm_pause
fi

# ----------------------------------------------------------------------------
# STAGE 7 — HASIL (collect + baseline pembanding)
# ----------------------------------------------------------------------------
if should_run 7; then
  banner 7 "$TOTAL_STAGES" "KUMPULKAN HASIL + BASELINE PEMBANDING (${#CONFIG_LIST[@]} config)" \
    "collect per config (MCC, balanced accuracy, bias prediksi, per-grup vs baseline grup, ambang dari val) + logistik/GBDT (sekali, fitur identik)" \
    "third_party/.../exp/tabr/<dataset>/" \
    "output/training/<dataset>{,_baseline}/" \
    "CEPAT (menit)"
  for ci in "${!DATASET_LIST[@]}"; do
    DS="${DATASET_LIST[$ci]}"
    [ "$ci" -eq 0 ] && STAGE_NAME="collect" || STAGE_NAME="collect_cfg_${ci}"
    if [ "$DRY" = 1 ]; then
      info "[dry-run] $PY pipeline/stages/stage_7_collect.py --exp $DS --features $TRAIN_FEATURES --row-unit subject"
      continue
    fi
    run_stage 7 "$STAGE_NAME" "$PY" pipeline/stages/stage_7_collect.py \
      --exp "$DS" --features "$TRAIN_FEATURES" --row-unit subject
  done
  if [ "$DRY" = 1 ]; then
    info "[dry-run] $PY pipeline/stages/stage_7_baseline.py --dataset ${LOSO_DATASET}_baseline --features $TRAIN_FEATURES --aggregate subject --subject-norm none"
  else
    # baseline pembanding: SEKALI saja (tidak bergantung config — fitur sama).
    # Jangan menggagalkan pipeline kalau ini gagal.
    BASE_LOG="$LOG_DIR/stage7_baseline_${STAMP}.log"
    if PYTHONUNBUFFERED=1 "$PY" pipeline/stages/stage_7_baseline.py \
         --dataset "${LOSO_DATASET}_baseline" --features "$TRAIN_FEATURES" \
         --aggregate subject --subject-norm none >"$BASE_LOG" 2>&1; then
      log "  baseline pembanding selesai ($BASE_LOG)"
    else
      log "  PERINGATAN: baseline pembanding gagal, tidak menggagalkan pipeline ($BASE_LOG)"
    fi
    log "STAGE 7 SELESAI (${#CONFIG_LIST[@]} config)."
  fi
  confirm_pause
fi

# ----------------------------------------------------------------------------
# STAGE 8 — EVALUASI HOLDOUT (hanya mode fold-first)
# ----------------------------------------------------------------------------
# 12 orang ini PERTAMA KALI dibaca di sini: spotting + fitur dengan resep yang
# SAMA (tanpa ada yang di-fit pada data holdout), lalu SATU fold final:
# test = 12 orang holdout, train/val = 44 orang train pool. Checkpoint fold
# ini adalah model final yang bisa ditunjukkan; metriknya = satu angka jujur.
if [ "$PRESPLIT" = 1 ] && should_run 8; then
  HOLDOUT_XLSX="$FEAT_DIR/${FEAT_TAG}_holdout.xlsx"
  HOLDOUT_PKL="$FEAT_DIR/${FEAT_TAG}_holdout_full.pkl"
  HOLDOUT_TEMPORAL="$FEAT_DIR/${FEAT_TAG}_holdout_poc_temporal${DESC_SUFFIX}.pkl"
  COMBINED_PKL="$FEAT_DIR/${FEAT_TAG}_combined${DESC_SUFFIX}.pkl"

  banner 8 "$TOTAL_STAGES" "EVALUASI HOLDOUT — 12 orang pertama kali dibaca (${#CONFIG_LIST[@]} config)" \
    "spotting+fitur 12 orang holdout (resep sama) -> gabung tabel -> 1 fold final per config (test=12 orang) -> model final per config" \
    "$RAW_ROOT (hanya 12 orang) + $TRAIN_FEATURES" \
    "$HOLDOUT_OUT_ROOT + $COMBINED_PKL + output/training/<dataset>_holdout/" \
    "SEDANG (~15 menit spotting + ~10 menit fitur + 1 fold per config)"
  [ -s "$PRESPLIT_DIR/test_persons.txt" ] \
    || die "mode fold-first tapi $PRESPLIT_DIR/test_persons.txt tidak ada (jalankan stage 0)"
  [ -s "$TRAIN_FEATURES" ] \
    || die "fitur train pool tidak ada: $TRAIN_FEATURES (jalankan stage 2-4 dulu)"
  [ ! -d "$RAW_ROOT" ] && die "stage 8 butuh driv mentah ($RAW_ROOT) untuk spotting 12 orang holdout"

  if [ "$DRY" = 1 ]; then
    info "[dry-run] SPOT_INCLUDE_PERSONS=$PRESPLIT_DIR/test_persons.txt SPOT_OUTPUT_ROOT=$HOLDOUT_OUT_ROOT $PY pipeline/stages/stage_1_spotting.py"
    info "[dry-run] FEAT_DATASET_ROOT=$HOLDOUT_OUT_ROOT/dataset $PY pipeline/stages/stage_2_extract_features.py --roi-signals --baseline neutral --output $HOLDOUT_XLSX"
    info "[dry-run] $PY pipeline/stages/stage_3_cache.py --xlsx $HOLDOUT_XLSX --pkl $HOLDOUT_PKL"
    info "[dry-run] $PY pipeline/stages/stage_4_temporal.py --input $HOLDOUT_PKL --output $HOLDOUT_TEMPORAL ${DESC_ARGS[*]} --no-xlsx"
    info "[dry-run] $PY pipeline/stages/stage_8_holdout_combine.py --inputs $TRAIN_FEATURES $HOLDOUT_TEMPORAL --output $COMBINED_PKL"
    for ci in "${!CONFIG_LIST[@]}"; do
      info "[dry-run] $PY pipeline/stages/stage_6_train_loso.py --dataset ${DATASET_LIST[$ci]}_holdout --features $COMBINED_PKL --test-persons-file $PRESPLIT_DIR/test_persons.txt --config ${CONFIG_LIST[$ci]} ... --quiet"
      info "[dry-run] $PY pipeline/stages/stage_7_collect.py --exp ${DATASET_LIST[$ci]}_holdout --features $COMBINED_PKL --row-unit subject"
    done
  else
    # 8a spotting 12 orang (resume otomatis per sample)
    run_stage 8 spotting_holdout \
      env SPOT_DATASET_ROOT="$RAW_ROOT" \
          SPOT_OUTPUT_ROOT="$HOLDOUT_OUT_ROOT" \
          SPOT_VIDEO_EXT=".avi" \
          SPOT_ABS=1 \
          SPOT_OVERWRITE=0 \
          SPOT_NO_EVENT_SIGNAL=1 \
          SPOT_SAVE_NEUTRAL=1 \
          SPOT_CUTOFF="${V3_SPOT_CUTOFF:-0.3}" \
          SPOT_ALGO="${V3_SPOT_ALGO:-phase}" \
          SPOT_SIGNAL="${V3_SPOT_SIGNAL:-mean_m}" \
          SPOT_MOTION_COMP="${V3_SPOT_MOTION_COMP:-0}" \
          SPOT_MDMD="${V3_SPOT_MDMD:-0}" \
          SPOT_MDMD_K="${V3_SPOT_MDMD_K:-5}" \
          SPOT_OF_FD_MAD="${V3_SPOT_OF_FD_MAD:-3.5}" \
          SPOT_OF_FD_TOP="${V3_SPOT_OF_FD_TOP:-mean}" \
          SPOT_OF_FD_SMOOTH="${V3_SPOT_OF_FD_SMOOTH:-35}" \
          SPOT_OF_FD_WIDTH="${V3_SPOT_OF_FD_WIDTH:-35}" \
          SPOT_OF_FD_DISTANCE="${V3_SPOT_OF_FD_DISTANCE:-12}" \
          SPOT_OF_FD_BOUNDARY_BETA="${V3_SPOT_OF_FD_BOUNDARY_BETA:-0.3}" \
          SPOT_INCLUDE_PERSONS="$PRESPLIT_DIR/test_persons.txt" \
          MPLBACKEND=Agg \
      "$PY" pipeline/stages/stage_1_spotting.py
    [ -s "$HOLDOUT_OUT_ROOT/metadata.xlsx" ] || die "metadata holdout tidak terbentuk"

    # 8b ekstraksi fitur holdout (flag identik dengan stage 2)
    if [ "$FORCE" = 0 ] && [ -e "$HOLDOUT_XLSX" ]; then
      log "STAGE 8/ekstraksi DILEWATI: sudah ada $HOLDOUT_XLSX. Pakai --force untuk ulang."
    else
      run_stage 8 ekstraksi_holdout \
        env FEAT_WORKERS=3 \
            FEAT_DATASET_ROOT="$HOLDOUT_OUT_ROOT/dataset" \
            FEAT_METADATA_PATH="$HOLDOUT_OUT_ROOT/metadata.xlsx" \
        "$PY" pipeline/stages/stage_2_extract_features.py \
          --roi-signals --baseline neutral --output "$HOLDOUT_XLSX"
    fi

    # 8c cache + 8d temporal + 8e gabung
    run_stage 8 cache_holdout "$PY" pipeline/stages/stage_3_cache.py \
      --xlsx "$HOLDOUT_XLSX" --pkl "$HOLDOUT_PKL"
    run_stage 8 temporal_holdout "$PY" pipeline/stages/stage_4_temporal.py \
      --input "$HOLDOUT_PKL" --output "$HOLDOUT_TEMPORAL" "${DESC_ARGS[@]}" --no-xlsx
    run_stage 8 combine "$PY" pipeline/stages/stage_8_holdout_combine.py \
      --inputs "$TRAIN_FEATURES" "$HOLDOUT_TEMPORAL" --output "$COMBINED_PKL"

    # 8f SATU fold final per config: test = 12 orang holdout
    for ci in "${!CONFIG_LIST[@]}"; do
      CFG="${CONFIG_LIST[$ci]}"
      DS_H="${DATASET_LIST[$ci]}_holdout"
      [ "$ci" -eq 0 ] && STAGE_NAME="loso_holdout" || STAGE_NAME="loso_holdout_cfg_${ci}"
      log "  holdout config $((ci + 1))/${#CONFIG_LIST[@]}: $CFG -> dataset $DS_H"
      run_stage 8 "$STAGE_NAME" "$PY" pipeline/stages/stage_6_train_loso.py \
        --dataset "$DS_H" \
        --features "$COMBINED_PKL" \
        --aggregate subject \
        --subject-norm none \
        --label-unit "$V3_LABEL_UNIT" \
        --drop-features "$V3_DROP_FEATURES" \
        --device "${TRAIN_DEVICE:-cpu}" \
        --epochs-log \
        --config "$CFG" \
        --seeds "$TRAIN_SEEDS" \
        --epochs-trace "${V3_EPOCHS_TRACE:-40}" \
        "${FORCE_ARG[@]}" \
        --test-persons-file "$PRESPLIT_DIR/test_persons.txt" \
        --quiet

      # 8g kumpulkan hasil holdout per config
      [ "$ci" -eq 0 ] && CNAME="collect_holdout" || CNAME="collect_holdout_cfg_${ci}"
      run_stage 8 "$CNAME" "$PY" pipeline/stages/stage_7_collect.py \
        --exp "$DS_H" --features "$COMBINED_PKL" --row-unit subject
      log "  hasil holdout $DS_H: output/training/$DS_H/summary.md"
    done
    log "STAGE 8 SELESAI (${#CONFIG_LIST[@]} config)."
  fi
  confirm_pause
fi

# ----------------------------------------------------------------------------
# Ringkasan
# ----------------------------------------------------------------------------
echo ""
log "══════════════════════════════════════════════════════════"
log "PIPELINE v3 SELESAI"
log "  Fitur    : $TRAIN_FEATURES"
for ds in "${DATASET_LIST[@]}"; do
  log "  Hasil    : output/training/$ds/summary.md"
  if [ "$PRESPLIT" = 1 ]; then
    log "  Holdout  : output/training/${ds}_holdout/summary.md (12 orang, pertama kali dibaca di stage 8)"
  fi
done
if [ "$PRESPLIT" = 1 ]; then
  log "  Split    : $PRESPLIT_DIR/split.csv"
fi
log "  Log      : $LOG"
log "  Wasit    : MCC (bukan accuracy) + per-grup vs baseline grup"
log "══════════════════════════════════════════════════════════"

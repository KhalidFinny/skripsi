#!/usr/bin/env python
"""Kumpulkan hasil LOSO TabR -> metrik level-SUBJEK (headline) + level-frame (diagnostik).

Kenapa level-subjek yang jadi headline:
  Tiap fold menahan 1 subjek, dan label di data ini milik subjek/sesi (semua frame
  satu subjek berlabel sama). Jadi test set tiap fold = SATU kelas -> metrik
  klasifikasi per-fold (accuracy, balanced accuracy) tidak terdefinisi.
  Satu-satunya angka yang bisa ditafsirkan adalah keputusan per subjek.

Probabilitas: predictions.npz menyimpan LOGITS (report.json: prediction_type=logits),
jadi harus lewat sigmoid dulu. Versi lama membandingkan logits langsung dengan 0.5
(threshold efektif ~0.62) -> recall kelas 0 jatuh palsu.

Contoh:
    ./run collect --exp convat_apex_anxiety_loso_roi25
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit
from sklearn.metrics import accuracy_score, balanced_accuracy_score, classification_report, roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
EXP_ROOT = ROOT / 'third_party/tabular-dl-tabr-official' / 'exp' / 'tabr'
DEFAULT_OUT = ROOT / 'output' / 'training'
DEFAULT_FEATURES = ROOT / 'experiments/features/apex/poc_abs_roi_signals_full.pkl'
if not DEFAULT_FEATURES.exists():
    DEFAULT_FEATURES = ROOT / 'experiments/features/apex/poc_abs_roi_signals.xlsx'

GROUP_ORDER = ['hanya_after', 'before_sama', 'before_berubah']


def load_seed_pool(exp_dir: Path, seed: int) -> dict:
    """Gabungkan proba/label test semua fold untuk satu seed (logits -> proba).

    Fold yang belum selesai (test_split.csv belum ditulis, mis. run dihentikan di
    tengah training) dilewati, bukan bikin script mati.

    Tiap fold disimpan terpisah di `folds` supaya ambang keputusan bisa dipilih
    di val fold itu sendiri (bukan di test, dan bukan digabung antar fold).
    """
    folds, skipped = [], []
    for fold_dir in sorted(exp_dir.glob('fold_*'), key=lambda p: int(p.name.split('_')[1])):
        run_dir = fold_dir / '0-evaluation' / str(seed)
        test_csv = fold_dir / 'test_split.csv'
        if not (run_dir / 'predictions.npz').exists() or not test_csv.exists():
            skipped.append(fold_dir.name)
            continue
        pred = np.load(run_dir / 'predictions.npz')
        test_df = pd.read_csv(test_csv)
        if len(pred['test']) != len(test_df):
            raise SystemExit(f'{fold_dir}: pred {len(pred["test"])} != rows {len(test_df)}')
        val_csv = fold_dir / 'val_split.csv'
        val_df = pd.read_csv(val_csv) if val_csv.exists() else None
        if val_df is not None and len(pred['val']) != len(val_df):
            val_df = None  # artefak tidak sinkron -> lewati analisis ambang fold ini
        folds.append({
            'probs': expit(pred['test'].astype(np.float64)),
            'labels': test_df['target'].to_numpy(),
            'subjects': test_df['participant'].to_numpy(),
            'val_probs': None if val_df is None else expit(pred['val'].astype(np.float64)),
            'val_labels': None if val_df is None else val_df['target'].to_numpy(),
        })
    if skipped:
        print(f'  lewati {len(skipped)} fold belum selesai: {skipped[:5]}'
              f'{" ..." if len(skipped) > 5 else ""}')
    if not folds:
        raise SystemExit(f'Tidak ada fold selesai di {exp_dir}')
    return {
        'folds': folds,
        'probs': np.concatenate([f['probs'] for f in folds]),
        'labels': np.concatenate([f['labels'] for f in folds]),
        'subjects': np.concatenate([f['subjects'] for f in folds]),
    }


def fold_score_summary(exp_dir: Path) -> dict | None:
    """Rata-rata akurasi train/val/test per fold-seed, dari `summary.json`.

    `summary.json` ditulis bin/tabr.py per fold per seed dan berisi `scores` =
    akurasi train/val/test pada epoch terbaik (`best_epoch`). Dipakai apa adanya
    supaya angkanya identik dengan yang dilaporkan training, bukan dihitung ulang
    dari prediksi (prediksi train tidak disimpan per baris).

    Catatan tafsir: test per fold hanya SATU subjek, jadi skor test per fold
    bernilai 0 atau 1 dan std-nya besar; yang bermakna adalah rata-ratanya.
    """
    tr, va, te, epochs = [], [], [], []
    for p in sorted(exp_dir.glob('fold_*/0-evaluation/*/summary.json')):
        try:
            d = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        s = d.get('scores')
        if not s:
            continue
        tr.append(float(s['train']))
        va.append(float(s['val']))
        te.append(float(s['test']))
        epochs.append(int(d.get('best_epoch', 0)))
    if not tr:
        return None
    ep = np.asarray(epochs)
    return {
        'n': len(tr),
        'train': float(np.mean(tr)), 'train_std': float(np.std(tr)),
        'val': float(np.mean(va)), 'val_std': float(np.std(va)),
        'test': float(np.mean(te)), 'test_std': float(np.std(te)),
        'best_epoch_median': float(np.median(ep)),
        'best_epoch_zero_frac': float((ep == 0).mean()),
    }


def val_threshold_metrics(pool: dict) -> dict:
    """Pilih ambang Youden di val tiap fold, lalu terapkan ke test fold itu.

    Ambang 0.5 itu pilihan arbitrer dan bias ke kelas mayoritas. Ambang yang
    jujur harus dipilih di data yang tidak dipakai mengukur (val), bukan di test.
    Mengembalikan None kalau val_split.csv tidak ada (run lama).
    """
    from sklearn.metrics import roc_curve

    if not any(f['val_probs'] is not None for f in pool['folds']):
        return None
    # Ambang diterapkan PER FOLD sebelum digabung. Kalau digabung dulu, iterasi
    # atas array 1-D menghasilkan skalar 0-d dan np.concatenate menolaknya
    # ("zero-dimensional arrays cannot be concatenated").
    fold_probs, fold_labels, fold_preds, thresholds = [], [], [], []
    for f in pool['folds']:
        if f['val_probs'] is None or len(np.unique(f['val_labels'])) < 2:
            continue
        fpr, tpr, thr = roc_curve(f['val_labels'], f['val_probs'])
        # thr[0] = inf (perilaku sklearn). Kalau argmax memilihnya, semua test
        # fold itu diprediksi 0 DAN rata-rata ambang jadi inf -> angka laporan
        # rusak ("inf ± nan"). Batasi pilihan ke ambang berhingga.
        candidates = np.where(np.isfinite(thr))[0]
        if candidates.size == 0:
            continue
        best = float(thr[candidates[int(np.argmax((tpr - fpr)[candidates]))]])
        p = np.atleast_1d(f['probs'])
        y = np.atleast_1d(f['labels'])
        fold_probs.append(p)
        fold_labels.append(y)
        fold_preds.append((p >= best).astype(int))
        thresholds.append(best)
    if not fold_probs:
        return None
    probs = np.concatenate(fold_probs)
    labels = np.concatenate(fold_labels)
    preds = np.concatenate(fold_preds)
    return {
        'n_folds': len(thresholds),
        'threshold_mean': float(np.mean(thresholds)),
        'accuracy': float((labels == preds).mean()),
        'bal_acc': float(balanced_accuracy_score(labels, preds)),
        'pred_pos_rate': float(preds.mean()),
        'true_pos_rate': float(labels.mean()),
    }


def subject_table(pool: dict) -> pd.DataFrame:
    """1 baris = 1 subjek: proba rata-rata, label mayoritas, dan prediksi."""
    df = pd.DataFrame({'subject': pool['subjects'], 'target': pool['labels'], 'proba': pool['probs']})
    g = df.groupby('subject').agg(
        proba=('proba', 'mean'),
        target_mean=('target', 'mean'),
        n_frames=('target', 'size'),
    )
    g['true'] = (g['target_mean'] > 0.5).astype(int)
    g['pred'] = (g['proba'] >= 0.5).astype(int)
    g['mixed'] = (g['target_mean'] > 0.0) & (g['target_mean'] < 1.0)
    return g.reset_index()


def subject_metrics(g: pd.DataFrame) -> dict:
    tp = int(((g['true'] == 1) & (g['pred'] == 1)).sum())
    tn = int(((g['true'] == 0) & (g['pred'] == 0)).sum())
    fp = int(((g['true'] == 0) & (g['pred'] == 1)).sum())
    fn = int(((g['true'] == 1) & (g['pred'] == 0)).sum())
    n = len(g)
    # MCC dihitung manual dari sel confusion: rumus sklearn memunculkan warning
    # dan mengembalikan 0 saat cuma satu kelas ada (sering terjadi di grup kecil).
    mcc_denom = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    # AUC dihitung dari proba LEVEL SUBJEK yang sudah dikumpulkan (bukan dari
    # lib TabR). Ini yang membuat AUC kembali dipakai tanpa mengembalikan patch
    # lib/metrics.py yang dihapus di Iterasi 4.1: tiap subjek menyumbang TEPAT
    # SATU proba dari model yang tidak pernah melihatnya, jadi AUC di sini
    # bebas-bocor dan terdefinisi walau test per fold cuma satu kelas.
    auc = float('nan')
    if g['true'].nunique() > 1 and 'proba' in g.columns:
        auc = float(roc_auc_score(g['true'], g['proba']))
    out = {
        'n': n,
        'n_pos': int(g['true'].sum()),
        'accuracy': (tp + tn) / n,
        'auc': auc,
        'mcc': ((tp * tn - fp * fn) / mcc_denom) if mcc_denom else float('nan'),
        'bal_acc': (tp / (tp + fn) + tn / (tn + fp)) / 2
                   if (tp + fn) and (tn + fp) else float('nan'),
        'pred_pos_rate': float(g['pred'].mean()),
        'true_pos_rate': float(g['true'].mean()),
        'sensitivity': tp / (tp + fn) if (tp + fn) else float('nan'),
        'specificity': tn / (tn + fp) if (tn + fp) else float('nan'),
        'ppv': tp / (tp + fp) if (tp + fp) else float('nan'),
        'npv': tn / (tn + fn) if (tn + fn) else float('nan'),
        'majority_baseline': max(g['true'].mean(), 1 - g['true'].mean()),
        'tp': tp, 'tn': tn, 'fp': fp, 'fn': fn,
    }
    return out


def frame_metrics(pool: dict) -> dict:
    """Diagnostik: 1 baris = 1 frame. bal_acc tidak terdefinisi kalau test 1 kelas.

    Bukan ukuran kemampuan model: di protokol LOSO tiap fold menahan satu subjek,
    jadi angka ini hanya menggambarkan komposisi kelas di dalam subjek.
    """
    pred = (pool['probs'] >= 0.5).astype(int)
    rep = classification_report(pool['labels'], pred, output_dict=True, zero_division=0)
    single_class = len(np.unique(pool['labels'])) < 2
    return {
        'accuracy': accuracy_score(pool['labels'], pred),
        'bal_acc': float('nan') if single_class else balanced_accuracy_score(pool['labels'], pred),
        'macroF1': rep['macro avg']['f1-score'],
        'recall_0': rep['0']['recall'],
        'recall_1': rep['1']['recall'],
        'n': int(len(pool['labels'])),
        'n_pos': int(pool['labels'].sum()),
        'single_class': single_class,
    }


def load_subject_groups(features_path: Path) -> pd.DataFrame:
    """Peta subjek -> grup fase, dari tabel fitur penuh.

    hanya_after    : tidak punya rekaman 'before'
    before_sama    : punya 'before', kondisinya sama dengan 'after'
    before_berubah : punya 'before', kondisinya berubah di 'after'
    """
    if not features_path.exists():
        return pd.DataFrame(columns=['subject', 'group', 'before', 'after'])
    if features_path.suffix.lower() == '.pkl':
        df = pd.read_pickle(features_path)[['participant', 'phase', 'condition']]
    else:
        df = pd.read_excel(features_path, usecols=['participant', 'phase', 'condition'])
    piv = df.pivot_table(index='participant', columns='phase', values='condition',
                         aggfunc='first')
    rows = []
    for subject, r in piv.iterrows():
        before = r.get('before')
        after = r.get('after')
        if pd.isna(before):
            group = 'hanya_after'
        elif before == after:
            group = 'before_sama'
        else:
            group = 'before_berubah'
        rows.append({'subject': subject, 'group': group, 'before': before, 'after': after})
    return pd.DataFrame(rows)


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Interval kepercayaan Wilson 95% untuk proporsi binomial.

    Dipakai alih-alih interval normal karena N kecil (56 subjek) dan proporsi
    bisa dekat 0 atau 1, tempat interval normal bisa keluar dari [0, 1].
    """
    if n == 0:
        return float('nan'), float('nan')
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def fmt_ci(successes: int, n: int) -> str:
    low, high = wilson_interval(successes, n)
    if math.isnan(low):
        return 'n/a'
    return f'{low:.4f}–{high:.4f}'


def fmt(vals: pd.Series, pct: bool = False) -> str:
    vals = vals.dropna()
    if len(vals) == 0:
        return 'n/a'
    scale = 100 if pct else 1
    if len(vals) > 1:
        return f'{vals.mean() * scale:.4f} ± {vals.std() * scale:.4f}'
    return f'{vals.mean() * scale:.4f}'


def main() -> None:
    parser = argparse.ArgumentParser(description='Kumpulkan hasil LOSO TabR (level subjek).')
    parser.add_argument('--exp', default='convat_apex_anxiety_loso_roi25')
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--features', type=Path, default=DEFAULT_FEATURES,
                        help='tabel fitur penuh, dipakai untuk grup fase per subjek')
    parser.add_argument('--row-unit', choices=['frame', 'clip', 'subject'], default='frame',
                        help="Isi satu baris di dataset yang dilatih. Hanya memengaruhi "
                             "penamaan bagian sekunder di summary.md: 'frame' (default) "
                             "untuk protokol baris-per-frame, 'clip'/'subject' kalau run "
                             "memakai --aggregate (baris sudah diringkas).")
    args = parser.parse_args()

    exp_dir = EXP_ROOT / args.exp
    fold_dirs = sorted(exp_dir.glob('fold_*'), key=lambda p: int(p.name.split('_')[1]))
    if not fold_dirs:
        raise SystemExit(f'Tidak ada fold di {exp_dir}')
    # Jumlah seed diambil dari GABUNGAN semua fold, bukan hanya fold pertama.
    # Bug yang diperbaiki: `fold_dirs[0]` bisa saja fold parsial (mis. sisa run
    # lama yang cuma punya seed 0) sehingga `n_seeds` terbaca 1 dan seed 1..N-1
    # di 55 fold lain DIBUANG DIAM-DIAM dari laporan. Terjadi nyata pada
    # convat_apex_anxiety_loso_roi25_reg: fold_000 punya 1 seed, fold lain 3.
    seed_ids = set()
    for fd in fold_dirs:
        eval_dir = fd / '0-evaluation'
        if not eval_dir.is_dir():
            continue
        for d in eval_dir.iterdir():
            if d.is_dir() and d.name.isdigit():
                seed_ids.add(int(d.name))
    n_seeds = max(seed_ids) + 1 if seed_ids else 0
    if n_seeds == 0:
        raise SystemExit('Tidak ada seed run di fold mana pun.')
    missing = sorted(s for s in range(n_seeds) if s not in seed_ids)
    if missing:
        print(f'  catatan: seed {missing} tidak ada di semua fold (fold parsial dilewati)')
    print(f'Fold: {len(fold_dirs)}, seeds/fold: {n_seeds}')

    groups = load_subject_groups(args.features)
    if groups.empty:
        print(f'PERINGATAN: {args.features} tidak ada -> grup fase dilewati.')
    else:
        print(f'Grup subjek: {groups["group"].value_counts().to_dict()}')

    seed_rows, subject_rows = [], []
    for seed in range(n_seeds):
        pool = load_seed_pool(exp_dir, seed)
        subj = subject_table(pool)
        if not groups.empty:
            subj = subj.merge(groups[['subject', 'group']], on='subject', how='left')
            subj['group'] = subj['group'].fillna('tidak_diketahui')
        else:
            subj['group'] = 'tidak_diketahui'
        sm = subject_metrics(subj)
        fm = frame_metrics(pool)
        vm = val_threshold_metrics(pool)
        seed_rows.append({'seed': seed, **{f'subject_{k}': v for k, v in sm.items()},
                          **{f'frame_{k}': v for k, v in fm.items()},
                          **({f'thr_{k}': v for k, v in vm.items()} if vm else {})})
        subject_rows.append(subj.assign(seed=seed))
        print(f'seed {seed}: subjek acc {sm["accuracy"]:.4f} '
              f'(sens {sm["sensitivity"]:.3f} / spec {sm["specificity"]:.3f}) | '
              f'frame acc {fm["accuracy"]:.4f}')

    df = pd.DataFrame(seed_rows)
    per_subject = pd.concat(subject_rows, ignore_index=True)
    out_dir = args.out / args.exp
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / 'summary.csv', index=False)
    per_subject.to_csv(out_dir / 'per_subject.csv', index=False)

    n_mixed = int(per_subject['mixed'].sum())
    # Seed-ensemble: proba dirata-rata antar seed per subjek, LALU di-threshold ulang.
    # Sebelumnya `pred` tidak dihitung ulang, sehingga subject_metrics() memakai
    # kolom `pred` lama dan drop_duplicates() menyisakan baris seed 0 -> angka
    # "pooled antar seed" sebenarnya HANYA seed 0 (menyesatkan).
    pooled = per_subject.copy()
    pooled['proba'] = pooled.groupby('subject')['proba'].transform('mean')
    pooled = pooled.drop_duplicates('subject')
    pooled['pred'] = (pooled['proba'] >= 0.5).astype(int)
    pooled_m = subject_metrics(pooled)

    lines = [
        f'# Hasil LOSO TabR - {args.exp}',
        '',
        f'{len(fold_dirs)} fold (1 subjek/fold), {n_seeds} seed per fold. '
        'Tiap subjek jadi test tepat sekali; model tidak pernah lihat dia.',
        '',
        '**Metrik utama = level subjek.** Label di data ini milik subjek/sesi, jadi test '
        'set tiap fold cuma satu kelas: metrik klasifikasi per fold tidak terdefinisi. '
        'Yang bisa ditafsirkan hanya keputusan per subjek.',
        '',
    ]

    # --- Train / Val / Test (persen) ---
    fss = fold_score_summary(exp_dir)
    if fss is not None:
        gap = fss['train'] - fss['val']
        lines += [
            '## Train / Val / Test (akurasi, persen)',
            '',
            f'Dari `summary.json` tiap fold-seed ({fss["n"]} fold-seed, '
            f'epoch terbaik median {fss["best_epoch_median"]:.0f}; '
            f'{fss["best_epoch_zero_frac"] * 100:.1f}% berhenti di epoch 0).',
            '',
            '| split | akurasi | std antar fold-seed | jumlah baris/split |',
            '|---|---|---|---|',
            f'| train | **{fss["train"] * 100:.2f}%** | ±{fss["train_std"] * 100:.2f} | '
            f'~43 subjek (dipotong val) |',
            f'| val | **{fss["val"] * 100:.2f}%** | ±{fss["val_std"] * 100:.2f} | ~11 subjek |',
            f'| test | **{fss["test"] * 100:.2f}%** | ±{fss["test_std"] * 100:.2f} | '
            f'1 subjek/fold |',
            '',
            f'Gap train − val = **{gap * 100:+.2f} poin**. Gap besar berarti model menghafal '
            'data latih, bukan belajar pola yang berlaku di subjek baru.',
            '',
            'Catatan: test tiap fold hanya SATU subjek, jadi skor test per fold bernilai '
            '0% atau 100% dan std-nya besar (±). Yang bermakna adalah rata-ratanya, yang '
            'sama dengan baris `accuracy` di tabel bawah.',
            '',
        ]
        if fss['best_epoch_zero_frac'] >= 0.4:
            lines += [
                f'**PERINGATAN: training tidak berjalan.** '
                f'{fss["best_epoch_zero_frac"] * 100:.1f}% fold-seed punya `best_epoch` = 0, '
                'artinya skor validasi TIDAK PERNAH membaik setelah epoch pertama. Model '
                'praktis tidak terlatih, jadi angka di bawah mengukur model yang nyaris '
                'tidak belajar, bukan batas kemampuan fiturnya. Periksa learning rate, '
                'kapasitas, dan skema pemilihan epoch sebelum menyimpulkan apa pun.',
                '',
            ]

    lines += [
        '## Level subjek (1 keputusan per subjek)',
        '',
        '| metrik | nilai (mean ± std antar seed) | 95% CI (seed-ensemble) |',
        '|---|---|---|',
        f'| accuracy | {fmt(df["subject_accuracy"])} | '
        f'{fmt_ci(pooled_m["tp"] + pooled_m["tn"], pooled_m["n"])} |',
        f'| balanced accuracy | {fmt(df["subject_bal_acc"])} | – |',
        f'| MCC | {fmt(df["subject_mcc"])} | – |',
        f'| AUC (proba level subjek) | {fmt(df["subject_auc"])} | – |',
        f'| sensitivity (anxiety_tinggi) | {fmt(df["subject_sensitivity"])} | '
        f'{fmt_ci(pooled_m["tp"], pooled_m["tp"] + pooled_m["fn"])} |',
        f'| specificity | {fmt(df["subject_specificity"])} | '
        f'{fmt_ci(pooled_m["tn"], pooled_m["tn"] + pooled_m["fp"])} |',
        f'| PPV | {fmt(df["subject_ppv"])} | '
        f'{fmt_ci(pooled_m["tp"], pooled_m["tp"] + pooled_m["fp"])} |',
        f'| NPV | {fmt(df["subject_npv"])} | '
        f'{fmt_ci(pooled_m["tn"], pooled_m["tn"] + pooled_m["fn"])} |',
        f'| baseline mayoritas | {fmt(df["subject_majority_baseline"])} | – |',
        f'| subjek / kelas positif | {int(df["subject_n"].iloc[0])} / {int(df["subject_n_pos"].iloc[0])} | – |',
        '',
        'CI = Wilson 95% pada seed-ensemble: proba dirata-rata antar seed per subjek, '
        'lalu di-threshold 0.5. Bukan rata-rata CI per seed.',
        'Bandingkan accuracy dengan baseline mayoritas: kalau CI memuat baseline, model '
        'tidak terbukti lebih baik dari menebak kelas mayoritas.',
        '',
        'AUC dihitung dari proba LEVEL SUBJEK (1 proba/subjek dari model yang tidak '
        'pernah melihat subjek itu), jadi bebas-bocor dan tetap terdefinisi walau test '
        'per fold cuma satu kelas. AUC TIDAK bergantung ambang 0.5, jadi ia mengukur '
        'kemampuan MERANKING subjek cemas di atas subjek tidak cemas. Acuan: 0.5 = acak. '
        'Kalau AUC ~0.5 walau accuracy terlihat di atas baseline, keunggulan accuracy '
        'itu artefak ambang/komposisi, bukan kemampuan memisahkan.',
        '',
        '### Confusion (dijumlahkan antar seed)',
        '',
        '| | pred 0 (rendah) | pred 1 (tinggi) |',
        '|---|---|---|',
        f'| true 0 (rendah) | TN {int(df["subject_tn"].sum())} | FP {int(df["subject_fp"].sum())} |',
        f'| true 1 (tinggi) | FN {int(df["subject_fn"].sum())} | TP {int(df["subject_tp"].sum())} |',
        '',
        f'Pooling seed-ensemble: accuracy {pooled_m["accuracy"]:.4f}, '
        f'sensitivity {pooled_m["sensitivity"]:.4f}, specificity {pooled_m["specificity"]:.4f}, '
        f'AUC {pooled_m["auc"]:.4f}',
        '',
    ]

    lines += [
        '## Akuntansi bias',
        '',
        'Empat bias yang harus dibaca bersama accuracy, supaya angka headline tidak '
        'menyesatkan di data tak seimbang (56 subjek, 25 positif).',
        '',
        '### 1. Bias prediksi (model condong ke kelas mana)',
        '',
        '| | nilai |',
        '|---|---|',
        f'| laju positif SEBENARNYA | {pooled_m["true_pos_rate"]:.4f} |',
        f'| laju positif yang DIPREDIKSI | {pooled_m["pred_pos_rate"]:.4f} |',
        f'| bias (prediksi - sebenarnya) | '
        f'{pooled_m["pred_pos_rate"] - pooled_m["true_pos_rate"]:+.4f} |',
        '',
        'Bias negatif = model kurang berani menebak kelas positif. Cek juga '
        'sensitivity vs specificity: selisih besar = ambang 0.5 belum cocok untuk '
        'data ini (ambang sebaiknya dipilih di val, bukan di test).',
        '',
        '### 2. Bias metrik (accuracy vs ukuran tahan-imbalance)',
        '',
        f'- accuracy pooled {pooled_m["accuracy"]:.4f}, balanced accuracy '
        f'{pooled_m["bal_acc"]:.4f}, MCC {pooled_m["mcc"]:+.4f}, '
        f'AUC {pooled_m["auc"]:.4f}.',
        '- Kalau balanced accuracy dan MCC jauh lebih rendah dari accuracy, '
        'keunggulan accuracy datang dari menebak kelas mayoritas.',
        '- MCC 0 = setara tebak acak, jadi tanda +1/-1 yang penting, bukan '
        'besarnya accuracy.',
        f'- AUC {pooled_m["auc"]:.4f} (acak 0.5) mengukur perankingan tanpa ambang. '
        'Kalau AUC ~0.5 sementara accuracy di atas baseline, yang diukur accuracy '
        'adalah ambang + komposisi kelas, bukan kemampuan memisahkan.',
        '',
        '### 3. Bias komposisi / paradoks Simpson (uji per grup)',
        '',
        'Accuracy pooled bisa lebih tinggi dari baseline mayoritas global, padahal '
        'di SETIAP grup fase model kalah dari baseline mayoritas grup itu sendiri. '
        'Itu paradoks Simpson: keunggulan pooled cuma artefak komposisi kelas.',
        'Bandingkan kolom `accuracy` dengan `baseline grup` dan lihat `selisih`.',
        '',
    ]

    thr_cols = [c for c in df.columns if c.startswith('thr_')]
    lines += ['### 4. Bias ambang keputusan (0.5 itu arbitrer)', '']
    if thr_cols:
        lines += [
            'Ambang Youden dipilih di **val tiap fold**, lalu diterapkan ke test '
            'fold itu (bukan dipilih di test).',
            '',
            '| | ambang 0.5 | ambang dari val |',
            '|---|---|---|',
            f'| accuracy | {fmt(df["subject_accuracy"])} | {fmt(df["thr_accuracy"])} |',
            f'| balanced accuracy | {fmt(df["subject_bal_acc"])} | {fmt(df["thr_bal_acc"])} |',
            f'| laju positif prediksi | {fmt(df["subject_pred_pos_rate"])} | '
            f'{fmt(df["thr_pred_pos_rate"])} |',
            f'| ambang terpilih (rata-rata) | 0.5000 | {fmt(df["thr_threshold_mean"])} |',
            '',
            'Kalau ambang dari val lebih baik, angka di kolom 0.5 bukan kemampuan '
            'model — itu cuma ambang yang belum disetel.',
        ]
    else:
        lines += [
            'Belum bisa dihitung: `val_split.csv` tidak ada di run ini (fitur ini '
            'baru ditambahkan). Ambang masih dipatok 0.5, yang bias ke kelas '
            'mayoritas. Jalankan ulang LOSO supaya kolom ini terisi.',
        ]
    lines.append('')

    if not groups.empty:
        lines += ['## Per grup fase subjek (uji paradoks Simpson)', '',
                  '`baseline grup` = baseline mayoritas DIHITUNG DI GRUP ITU SENDIRI, '
                  'bukan baseline global. Kalau selisih negatif di semua grup, '
                  'keunggulan pooled tidak bisa dipercaya.', '',
                  '| grup | n | n positif | accuracy | baseline grup | selisih | MCC |',
                  '|---|---|---|---|---|---|---|']
        for gname in GROUP_ORDER + sorted(set(per_subject['group']) - set(GROUP_ORDER)):
            sel = pooled[pooled['group'] == gname]
            if len(sel) == 0:
                continue
            gm = subject_metrics(sel)
            lines.append(f'| {gname} | {gm["n"]} | {gm["n_pos"]} | {gm["accuracy"]:.4f} | '
                         f'{gm["majority_baseline"]:.4f} | '
                         f'{gm["accuracy"] - gm["majority_baseline"]:+.4f} | '
                         f'{gm["mcc"]:+.4f} |')
        lines.append('')
        lines.append('Catatan: `group` diturunkan dari kolom `condition`, yang '
                     'MERUPAKAN label. Jadi grup ini hanya alat diagnosis, tidak boleh '
                     'dipakai sebagai fitur atau untuk koreksi prior — itu kebocoran label.')
        lines.append('')

    lines += [
        '## Level frame (diagnostik komposisi, BUKAN performa)',
        '',
        'Angka di bawah menghitung frame, tapi label milik subjek: tiap fold LOSO '
        'menahan satu subjek sehingga test-nya satu kelas. Tabel ini hanya '
        'menggambarkan komposisi kelas di dalam subjek, bukan kemampuan model.',
        '',
        '| metrik | nilai |',
        '|---|---|',
        f'| accuracy | {fmt(df["frame_accuracy"])} |',
        f'| macroF1 | {fmt(df["frame_macroF1"])} |',
        f'| balanced accuracy | {fmt(df["frame_bal_acc"])} |',
        f'| recall kelas rendah / tinggi | {fmt(df["frame_recall_0"])} / {fmt(df["frame_recall_1"])} |',
        f'| baris | {int(df["frame_n"].iloc[0])} |',
        '',
        'Catatan:',
        f'- {len(fold_dirs)} fold punya test set satu kelas.',
        f'- Satuan baris training: `{args.row_unit}` (tidak mengubah tabel frame di atas).',
        f'- Subjek dengan label ambigu (test-nya memuat 2 kelas): {n_mixed} '
        '(0 kalau label unit = person; > 0 berarti run memakai label unit = session).',
        '- File: summary.csv (per seed), per_subject.csv (per seed x subjek).',
    ]
    (out_dir / 'summary.md').write_text('\n'.join(lines) + '\n')
    print('\n' + '\n'.join(lines))


if __name__ == '__main__':
    main()

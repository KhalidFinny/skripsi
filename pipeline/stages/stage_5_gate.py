#!/usr/bin/env python
"""Uji berpasangan dalam-subjek: apakah fitur POC-ABS membawa sinyal kecemasan?

Konteks (sebab #1 penurunan akurasi LOSO):
  Semua perbandingan antar subjek tercampur identitas orang. Dataset ini punya
  alat yang belum dipakai untuk memisahkannya: sebagian subjek mengubah label
  antar sesi (before vs after). Untuk mereka, yang dibandingkan adalah ORANG
  YANG SAMA, WAJAH YANG SAMA, dengan label berbeda -> tidak ada confound
  identitas sama sekali.

Dua uji:

  1. Uji berpasangan per fitur (Wilcoxon signed-rank).
     H0: selisih fitur (after - before) berpusat di nol pada subjek yang
     labelnya berubah. Dikoreksi Benjamini-Hochberg (FDR).
     KONTROL: subjek yang labelnya TIDAK berubah. Di grup itu tidak boleh ada
     perbedaan sistematis; kalau ada, efeknya efek sesi/waktu, bukan kecemasan.

  2. Klasifikasi dalam-subjek LOSO.
     36 baris (18 subjek x 2 sesi), label = label sesi. Test = 1 subjek
     (2 barisnya). Kalau akurasi ~50%, fitur tidak membedakan sesi orang yang
     sama -> keluarga fitur ini tidak membawa sinyal.

Contoh:
    .venv/bin/python pipeline/stages/stage_5_gate.py
    .venv/bin/python pipeline/stages/stage_5_gate.py --features experiments/features/apex/poc_abs_roi_signals_temporal.pkl
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, matthews_corrcoef
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FEATURES = ROOT / 'experiments/features/apex/poc_abs_roi_signals_full.pkl'
FALLBACK_FEATURES = ROOT / 'experiments/features/apex/poc_abs_roi_signals.xlsx'
DEFAULT_OUT = ROOT / 'output/training/within_subject_paired'
RANDOM_SEED = 72


def load_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == '.pkl':
        return pd.read_pickle(path)
    if path.suffix.lower() == '.csv':
        return pd.read_csv(path)
    return pd.read_excel(path)


def loso_scores(trues: list, preds: list) -> tuple[float, float, float]:
    """(balanced accuracy, accuracy, MCC) dengan label 0/1 EKSPLISIT.

    Penting: `balanced_accuracy_score` tanpa label eksplisit DEGENERASI kalau
    `y_true` hanya memuat satu kelas. sklearn saat itu menghitung recall atas
    kelas yang benar-benar muncul saja, sehingga bisa melaporkan 1,0000 padahal
    model TIDAK PERNAH menebak kelas minoritas. Confusion matrix dengan
    `labels=[0, 1]` memaksa kelas yang tidak muncul tetap dihitung dengan
    recall 0, jadi angkanya tidak bisa menipu.
    """
    t = np.asarray(trues)
    p = np.asarray(preds)
    cm = confusion_matrix(t, p, labels=[0, 1])
    denom = cm.sum(axis=1)
    recalls = np.divide(np.diag(cm), denom, out=np.zeros(2, dtype=float), where=denom > 0)
    return (float(recalls.mean()),
            float((t == p).mean()),
            float(matthews_corrcoef(t, p)))


def majority_label(y: np.ndarray) -> int:
    return int(np.bincount(np.asarray(y, dtype=int), minlength=2).argmax())


def benjamini_hochberg(pvals: np.ndarray) -> np.ndarray:
    """q-value FDR; NaN dilewatkan."""
    p = np.asarray(pvals, dtype=float)
    ok = ~np.isnan(p)
    q = np.full_like(p, np.nan)
    idx = np.where(ok)[0]
    if len(idx) == 0:
        return q
    order = idx[np.argsort(p[idx])]
    m = len(order)
    prev = 1.0
    for rank, i in enumerate(reversed(order), start=1):
        val = p[i] * m / (m - rank + 1)
        prev = min(prev, val)
        q[i] = prev
    return q


def paired_feature_tests(df: pd.DataFrame, feature_cols: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Uji berpasangan per fitur, grup 'berubah' dan grup kontrol 'sama'."""
    piv = df.groupby(['participant', 'phase'])['label'].first().unstack()
    both = piv.dropna()
    changed = both.index[both['before'] != both['after']].tolist()
    same = both.index[both['before'] == both['after']].tolist()

    def session_means(subjects: list[str]) -> dict[str, pd.DataFrame]:
        out = {}
        for ph in ('before', 'after'):
            sub = df[(df['phase'] == ph) & (df['participant'].isin(subjects))]
            out[ph] = sub.groupby('participant')[feature_cols].mean()
        return out

    def test_group(subjects: list[str]) -> pd.DataFrame:
        means = session_means(subjects)
        diff = (means['after'] - means['before']).dropna()
        rows = []
        for col in feature_cols:
            d = diff[col].to_numpy(dtype=float)
            d = d[~np.isnan(d)]
            if len(d) < 5 or np.allclose(d, 0):
                rows.append({'feature': col, 'n': len(d), 'mean_diff': float('nan'),
                             'median_diff': float('nan'), 'p_value': float('nan')})
                continue
            try:
                _, p = stats.wilcoxon(d, zero_method='wilcox')
            except ValueError:
                p = float('nan')
            rows.append({'feature': col, 'n': len(d), 'mean_diff': float(d.mean()),
                         'median_diff': float(np.median(d)), 'p_value': float(p)})
        out = pd.DataFrame(rows)
        out['q_value'] = benjamini_hochberg(out['p_value'].to_numpy())
        return out

    return test_group(changed).assign(group='berubah'), test_group(same).assign(group='sama')


def paired_permutation(data: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Balik label DI DALAM tiap subjek (null yang sesuai desain berpasangan).

    Desainnya berpasangan: tiap subjek menyumbang dua sesi (before/after) dengan
    label berbeda, jadi null yang benar adalah "label tiap subjek dibalik atau
    tidak". Mengacak label GLOBAL (versi lama) memutus pasangan sesi dan
    menyebarkan label antar subjek, sehingga null tidak mewakili desainnya.

    Dampak terukur pada run 2026-10-06 (200 permutasi): POC p 0,7761 -> 0,8010;
    geometri 0,7512 -> 0,8109; gabungan 0,2040 -> 0,1542. Kesimpulan tidak
    berubah, tapi metode lama tidak bisa dipertahankan di sidang.
    """
    perm = data.copy()
    targets = perm['target'].to_numpy().copy()
    for idx in perm.groupby('subject').groups.values():
        rows = np.asarray(idx)
        if rng.random() < 0.5:
            targets[rows] = 1 - targets[rows]
    perm['target'] = targets
    return perm


def within_subject_loso(df: pd.DataFrame, feature_cols: list[str], n_perm: int) -> dict:
    """LOSO: test = 1 subjek (2 sesinya), train = subjek lain. Label = label sesi."""
    piv = df.groupby(['participant', 'phase'])['label'].first().unstack().dropna()
    changed = piv.index[piv['before'] != piv['after']].tolist()

    rows = []
    for subject in changed:
        for ph in ('before', 'after'):
            sub = df[(df['participant'] == subject) & (df['phase'] == ph)]
            if sub.empty:
                continue
            rec = {'subject': subject, 'phase': ph, 'label': sub['label'].iloc[0],
                   'target': int(sub['target'].iloc[0])}
            rec.update(sub[feature_cols].mean().to_dict())
            rows.append(rec)
    data = pd.DataFrame(rows)
    if data.empty or data['target'].nunique() < 2:
        return {'n_rows': 0, 'n_subjects': 0, 'balanced_accuracy': float('nan'), 'p_value': float('nan')}

    def loso_accuracy(frame: pd.DataFrame, target_col: str) -> float:
        preds, trues = [], []
        for subject in frame['subject'].unique():
            tr = frame[frame['subject'] != subject]
            te = frame[frame['subject'] == subject]
            if te.empty:
                continue
            tr_y = tr[target_col].to_numpy()
            if len(np.unique(tr_y)) < 2:
                # Train cuma satu kelas -> model tidak bisa dilatih. JANGAN buang
                # fold ini: membuangnya berarti subjek minoritas tidak pernah
                # dievaluasi dan hasilnya tampak sempurna. Tebak kelas mayoritas
                # train supaya kesalahannya benar-benar terhitung.
                preds.extend([majority_label(tr_y)] * len(te))
                trues.extend(te[target_col].to_numpy().tolist())
                continue
            scaler = StandardScaler()
            Xtr = scaler.fit_transform(tr[feature_cols].to_numpy(dtype=float))
            Xte = scaler.transform(te[feature_cols].to_numpy(dtype=float))
            clf = LogisticRegression(max_iter=2000, class_weight='balanced', random_state=RANDOM_SEED)
            clf.fit(Xtr, tr_y)
            preds.extend(clf.predict(Xte).tolist())
            trues.extend(te[target_col].to_numpy().tolist())
        if not trues:
            return float('nan')
        # Balanced accuracy (label eksplisit) supaya tidak menipu saat satu
        # kelas tidak pernah ditebak.
        return loso_scores(trues, preds)[0]

    observed = loso_accuracy(data, 'target')
    rng = np.random.default_rng(RANDOM_SEED)
    null = []
    for _ in range(n_perm):
        perm = paired_permutation(data, rng)
        acc = loso_accuracy(perm, 'target')
        if not math.isnan(acc):
            null.append(acc)
    null_arr = np.asarray(null)
    hits = int((null_arr >= observed).sum()) if len(null_arr) else 0
    return {
        'n_rows': int(len(data)),
        'n_subjects': int(data['subject'].nunique()),
        'balanced_accuracy': float(observed),
        'null_mean': float(null_arr.mean()) if len(null_arr) else float('nan'),
        'null_std': float(null_arr.std()) if len(null_arr) else float('nan'),
        'p_value': (1 + hits) / (1 + len(null_arr)) if len(null_arr) else float('nan'),
    }


def within_subject_diff_loso(df: pd.DataFrame, feature_cols: list[str], n_perm: int) -> dict:
    """Deteksi PERUBAHAN dalam diri orang yang sama lewat vektor SELISIH sesi.

    Berbeda dari `within_subject_loso` (yang mengklasifikasi 2 sesi memakai nilai
    mentah, 36 baris), di sini yang diklasifikasi adalah `after - before` (18 baris).
    Pengurangan menghapus identitas subjek secara EKSAK, bukan kira-kira lewat
    penskalaan - jadi ini formulasi paling bersih untuk "apakah kecemasan berubah".

    Label: 1 bila sesi `after` berlabel anxiety_tinggi (kecemasan NAIK), 0 bila turun.
    Hanya subjek yang labelnya benar-benar berubah yang ikut (sisanya selisih = derau).

    Metrik utama = BALANCED accuracy, bukan accuracy mentah. Di data ini pembagian
    arah hampir selalu satu arah (mis. 17 turun : 1 naik), jadi accuracy mentah
    didominasi kelas mayoritas dan bisa terbaca 1,0000 hanya dengan selalu
    menebak "turun" - angka itu tidak mengukur apa pun. Balanced accuracy dan MCC
    tidak bisa dinaikkan dengan cara itu.

    Null: label diacak ANTAR subjek sambil vektor selisih dibiarkan. Kalau skor
    observasi tidak melebihi null, arah selisih tidak membawa informasi arah
    perubahan - artinya tidak ada tanda tangan kecemasan yang konsisten antar-orang.
    """
    piv = df.groupby(['participant', 'phase'])['label'].first().unstack().dropna()
    changed = piv.index[piv['before'] != piv['after']].tolist()

    rows, labels, groups = [], [], []
    for subject in changed:
        rec = {}
        ok = True
        for ph in ('before', 'after'):
            sub = df[(df['participant'] == subject) & (df['phase'] == ph)]
            if sub.empty:
                ok = False
                break
            rec[ph] = sub[feature_cols].mean()
        if not ok:
            continue
        rows.append((rec['after'] - rec['before']).to_numpy(dtype=float))
        labels.append(1 if piv.loc[subject, 'after'] == 'anxiety_tinggi' else 0)
        groups.append(subject)

    if not rows or len(set(labels)) < 2:
        return {'n_subjects': 0, 'balanced_accuracy': float('nan'), 'accuracy': float('nan'),
                'mcc': float('nan'), 'p_value': float('nan'),
                'baseline': float('nan'), 'n_up': 0, 'n_down': 0}

    X = np.asarray(rows, dtype=float)
    y = np.asarray(labels, dtype=int)
    g = np.asarray(groups)

    def loso_scores_for(Xm: np.ndarray, ym: np.ndarray) -> tuple[float, float, float]:
        """(balanced accuracy, accuracy mentah, MCC) dari prediksi LOSO."""
        preds, trues = [], []
        for subject in np.unique(g):
            tr, te = g != subject, g == subject
            if te.sum() == 0:
                continue
            tr_y = ym[tr]
            if len(np.unique(tr_y)) < 2:
                # Train cuma satu kelas (mis. saat subjek minoritas jadi test:
                # 17 sisa semuanya kelas mayoritas). JANGAN buang fold ini --
                # membuangnya membuat subjek minoritas tidak pernah dievaluasi
                # dan balanced accuracy palsu jadi 1,0000. Tebak mayoritas train
                # supaya kesalahannya benar-benar terhitung.
                preds.extend([majority_label(tr_y)] * int(te.sum()))
                trues.extend(ym[te].tolist())
                continue
            scaler = StandardScaler()
            Xtr = scaler.fit_transform(Xm[tr])
            Xte = scaler.transform(Xm[te])
            clf = LogisticRegression(max_iter=2000, class_weight='balanced', random_state=RANDOM_SEED)
            clf.fit(Xtr, tr_y)
            preds.extend(clf.predict(Xte).tolist())
            trues.extend(ym[te].tolist())
        if not trues:
            return float('nan'), float('nan'), float('nan')
        return loso_scores(trues, preds)

    observed, observed_acc, observed_mcc = loso_scores_for(X, y)
    baseline = max(y.mean(), 1 - y.mean())

    rng = np.random.default_rng(RANDOM_SEED)
    null = []
    for _ in range(n_perm):
        bal = loso_scores_for(X, rng.permutation(y))[0]
        if not math.isnan(bal):
            null.append(bal)
    null_arr = np.asarray(null)
    hits = int((null_arr >= observed).sum()) if len(null_arr) else 0
    return {
        'n_subjects': int(len(y)),
        'n_up': int((y == 1).sum()),
        'n_down': int((y == 0).sum()),
        'balanced_accuracy': float(observed),
        'accuracy': float(observed_acc),
        'mcc': float(observed_mcc),
        'baseline': float(baseline),
        'null_mean': float(null_arr.mean()) if len(null_arr) else float('nan'),
        'null_std': float(null_arr.std()) if len(null_arr) else float('nan'),
        'p_value': (1 + hits) / (1 + len(null_arr)) if len(null_arr) else float('nan'),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Uji berpasangan dalam-subjek untuk fitur POC-ABS.')
    parser.add_argument('--features', type=Path, default=None)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--permutations', type=int, default=200)
    args = parser.parse_args()

    path = args.features
    if path is None:
        path = DEFAULT_FEATURES if DEFAULT_FEATURES.exists() else FALLBACK_FEATURES
    if not path.exists():
        raise SystemExit(f'Tabel fitur tidak ditemukan: {path}')

    df = load_table(path)
    if 'target' not in df.columns:
        df = df.copy()
        df['target'] = df['label'].map({'anxiety_rendah': 0, 'anxiety_tinggi': 1})
    meta_cols = {'phase', 'condition', 'label', 'participant', 'participant_raw', 'question',
                 'question_no', 'sample', 'clip', 'event_clip', 'event_no', 'clip_path',
                 'frame', 'target', 'event_id', 'date'}
    feature_cols = [c for c in df.columns
                    if c not in meta_cols and pd.api.types.is_numeric_dtype(df[c])]
    # Judul laporan tidak boleh di-hardcode "POC-ABS": script ini dipakai untuk
    # beberapa keluarga fitur (POC-ABS, geometri, gabungan).
    family = path.stem
    print(f'Fitur : {path} ({len(df)} baris, {len(feature_cols)} fitur)')

    changed, same = paired_feature_tests(df, feature_cols)
    n_changed = int(changed['n'].iloc[0]) if len(changed) else 0
    n_same = int(same['n'].iloc[0]) if len(same) else 0
    sig_changed = int((changed['q_value'] < 0.05).sum())
    sig_same = int((same['q_value'] < 0.05).sum())
    print(f'Subjek label berubah: {n_changed} | kontrol (label sama): {n_same}')
    print(f'Fitur signifikan (FDR 5%) - berubah: {sig_changed}/{len(feature_cols)} | '
          f'kontrol: {sig_same}/{len(feature_cols)}')

    loso = within_subject_loso(df, feature_cols, args.permutations)
    print(f'Klasifikasi dalam-subjek LOSO: bal-acc {loso["balanced_accuracy"]:.4f} '
          f'(null {loso.get("null_mean", float("nan")):.4f}, p {loso["p_value"]:.4f})')

    diff = within_subject_diff_loso(df, feature_cols, args.permutations)
    print(f'Deteksi PERUBAHAN (selisih after-before): bal-acc {diff["balanced_accuracy"]:.4f} '
          f'(acc {diff["accuracy"]:.4f}, MCC {diff["mcc"]:+.4f}, baseline {diff["baseline"]:.4f}, '
          f'null {diff.get("null_mean", float("nan")):.4f}, p {diff["p_value"]:.4f}) | '
          f'naik={diff["n_up"]} turun={diff["n_down"]}')

    args.out.mkdir(parents=True, exist_ok=True)
    merged = pd.concat([changed, same], ignore_index=True)
    merged.to_csv(args.out / 'paired_features.csv', index=False)

    lines = [
        f'# Uji berpasangan dalam-subjek ({family})',
        '',
        f'Tabel fitur: `{path.name}` ({len(df)} baris, {len(feature_cols)} fitur).',
        '',
        'Orang yang sama, wajah yang sama, label berbeda -> tanpa confound identitas.',
        '',
        '## 1. Uji berpasangan per fitur (Wilcoxon, FDR Benjamini-Hochberg 5%)',
        '',
        f'| grup | n subjek | fitur signifikan |',
        '|---|---|---|',
        f'| label BERUBAH | {n_changed} | {sig_changed}/{len(feature_cols)} |',
        f'| kontrol (label sama) | {n_same} | {sig_same}/{len(feature_cols)} |',
        '',
        'Grup kontrol tidak boleh punya perbedaan sistematis. Kalau kontrol ikut',
        'signifikan, efeknya efek sesi/waktu, bukan kecemasan.',
        '',
        '### Fitur signifikan di grup "berubah"',
        '',
    ]
    top = changed[changed['q_value'] < 0.05].sort_values('q_value')
    if len(top):
        lines += ['| fitur | mean(after-before) | q-value |', '|---|---|---|']
        for row in top.itertuples(index=False):
            lines.append(f'| {row.feature} | {row.mean_diff:+.4f} | {row.q_value:.4f} |')
    else:
        lines.append('Tidak ada.')
    lines += ['', '## 2. Klasifikasi dalam-subjek LOSO', '',
              f'- baris: {loso["n_rows"]} ({loso["n_subjects"]} subjek x 2 sesi)',
              f'- balanced accuracy: {loso["balanced_accuracy"]:.4f}',
              f'- null: {loso.get("null_mean", float("nan")):.4f} '
              f'± {loso.get("null_std", float("nan")):.4f}',
              f'- p-value: {loso["p_value"]:.4f}',
              '',
              'Null memakai permutasi BERPASANGAN: label tiap subjek dibalik atau',
              'tidak, bukan diacak global. Itu yang sesuai desain (tiap subjek =',
              '2 sesi, label berbeda).',
              '',
              f'Bacaan: kalau balanced accuracy ~0.50 dan p besar, fitur `{family}` tidak',
              'membedakan sesi orang yang sama -> keluarga fitur ini tidak membawa',
              'sinyal kecemasan yang bisa dipakai, dan tidak ada model yang bisa',
              'menyelamatkannya.',
              '',
              'Catatan metode: fold yang set training-nya cuma satu kelas tidak',
              'dibuang, melainkan diprediksi kelas mayoritas train. Membuangnya akan',
              'membuat subjek minoritas tidak pernah dievaluasi dan balanced accuracy',
              'terbaca sempurna padahal model tidak pernah menebak kelas itu.',
              '',
              'File: paired_features.csv',
              '',
              '## 3. Deteksi PERUBAHAN dalam diri orang yang sama (vektor selisih)',
              '',
              'Formulasi berbeda dari bagian 2: yang diklasifikasi adalah `after - before`',
              '(1 baris per subjek), bukan 2 sesi memakai nilai mentah. Pengurangan',
              'menghapus identitas subjek secara EKSAK, bukan kira-kira lewat penskalaan.',
              '',
              f'- subjek (label berubah): {diff["n_subjects"]} (naik {diff["n_up"]}, turun {diff["n_down"]})',
              f'- balanced accuracy: {diff["balanced_accuracy"]:.4f}',
              f'- accuracy mentah: {diff["accuracy"]:.4f} | MCC: {diff["mcc"]:+.4f}',
              f'- baseline mayoritas: {diff["baseline"]:.4f}',
              f'- null (balanced accuracy, label diacak antar subjek): '
              f'{diff.get("null_mean", float("nan")):.4f} '
              f'± {diff.get("null_std", float("nan")):.4f}',
              f'- p-value: {diff["p_value"]:.4f}',
              '',
              'Metrik utama BALANCED accuracy, bukan accuracy mentah. Kalau arah perubahan',
              'hampir seluruhnya satu arah (mis. 17 turun : 1 naik), accuracy mentah bisa',
              'terbaca 1,0000 hanya dengan selalu menebak kelas mayoritas dan tidak',
              'mengukur apa pun. Balanced accuracy dan MCC tidak bisa naik dengan cara itu.',
              '',
              f'Bacaan: kalau balanced accuracy tidak melebihi 0,50 DAN p besar, arah selisih',
              f'tidak membawa informasi arah perubahan kecemasan. Tidak ada tanda tangan',
              f'kecemasan yang konsisten antar-orang di keluarga fitur `{family}`.']

    (args.out / 'summary.md').write_text('\n'.join(lines) + '\n')
    print(f'\nKeluaran: {args.out}')


if __name__ == '__main__':
    main()

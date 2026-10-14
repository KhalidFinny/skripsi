#!/usr/bin/env python
"""UJI KONTROL untuk temuan `rise` (dan keluarga lain).

Ablasi keluarga menemukan `desc:rise` memberi balanced accuracy 0,833 (p 0,005)
pada gerbang within-subject (18 subjek yang labelnya berubah). Tapi ada penjelasan
saingan yang harus dibunuh dulu:

  ARTEFAK SESI: `before` dan `after` direkam pada waktu berbeda. Kalau fitur
  mendeteksi "before vs after" untuk SEMUA subjek (termasuk yang labelnya TIDAK
  berubah), maka yang terdeteksi adalah efek sesi (lelah, postur, kamera), bukan
  kecemasan.

Desain uji:
  - grup BERUBAH (18 subjek): label sebelum != sesudah  -> target = label sesi
  - grup KONTROL (38 subjek): label sebelum == sesudah  -> target = sesi
    (before=1, after=0). Tidak ada label kecemasan yang berubah di grup ini,
    jadi BA tinggi di sini = artefak sesi.

Kalau BA(berubah) >> BA(kontrol), sinyalnya terkait label. Kalau setara, artefak.

Cara pakai:
    .venv/bin/python scripts/audit_rise_control.py \
        --features experiments/features/apex/poc_abs_roi_signals_v3fixed_poc_temporal.pkl
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT, ROOT / 'pipeline' / 'stages'):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from audit_feature_family_casme2 import families  # noqa: E402
from stage_5_gate import RANDOM_SEED, majority_label  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

META = {'phase', 'condition', 'label', 'participant', 'participant_raw', 'question',
        'question_no', 'sample', 'clip', 'event_clip', 'event_no', 'clip_path',
        'frame', 'target', 'event_id', 'date'}


def build_session_rows(df: pd.DataFrame, cols: list[str], subjects: list[str],
                       target_from: str) -> pd.DataFrame:
    """1 baris per (subjek, sesi): fitur = rata-rata, target sesuai `target_from`."""
    rows = []
    for s in subjects:
        for ph in ('before', 'after'):
            sub = df[(df['participant'] == s) & (df['phase'] == ph)]
            if sub.empty:
                continue
            lab = sub['label'].iloc[0]
            if target_from == 'label':
                y = int(lab == 'anxiety_tinggi')
            else:  # sesi
                y = int(ph == 'before')
            rec = {'subject': s, 'phase': ph, 'y': y}
            rec.update(sub[cols].mean().to_dict())
            rows.append(rec)
    return pd.DataFrame(rows)


def loso_ba(data: pd.DataFrame, cols: list[str], n_perm: int, rng) -> tuple[float, float]:
    def acc(frame: pd.DataFrame, ycol: str) -> float:
        preds, trues = [], []
        for s in frame['subject'].unique():
            tr, te = frame[frame['subject'] != s], frame[frame['subject'] == s]
            if te.empty:
                continue
            tr_y = tr[ycol].to_numpy()
            if len(np.unique(tr_y)) < 2:
                preds.extend([majority_label(tr_y)] * len(te))
                trues.extend(te[ycol].tolist())
                continue
            sc = StandardScaler()
            Xtr = sc.fit_transform(tr[cols].to_numpy(dtype=float))
            Xte = sc.transform(te[cols].to_numpy(dtype=float))
            clf = LogisticRegression(max_iter=2000, class_weight='balanced',
                                     random_state=RANDOM_SEED)
            clf.fit(Xtr, tr_y)
            preds.extend(clf.predict(Xte).tolist())
            trues.extend(te[ycol].tolist())
        # balanced accuracy
        t = np.asarray(trues); p = np.asarray(preds)
        sens = (p[t == 1] == 1).mean() if (t == 1).any() else float('nan')
        spec = (p[t == 0] == 0).mean() if (t == 0).any() else float('nan')
        return float(np.nanmean([sens, spec]))

    obs = acc(data, 'y')
    null = []
    for _ in range(n_perm):
        perm = data.copy()
        # acak label antar subjek (blok 2 sesi tetap bersama)
        subs = perm['subject'].unique()
        order = rng.permutation(len(subs))
        mapping = {}
        for i, s in enumerate(subs):
            src = subs[order[i]]
            mapping[s] = perm[perm['subject'] == src]['y'].to_numpy()
        for s, vals in mapping.items():
            perm.loc[perm['subject'] == s, 'y'] = vals
        a = acc(perm, 'y')
        if not np.isnan(a):
            null.append(a)
    null = np.asarray(null)
    p = (1 + int((null >= obs).sum())) / (1 + len(null)) if len(null) else float('nan')
    return obs, float(p)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--features', type=Path, required=True)
    ap.add_argument('--permutations', type=int, default=500)
    ap.add_argument('--out', type=Path, default=ROOT / 'output/training/audit_rise_control')
    args = ap.parse_args()

    df = pd.read_pickle(args.features)
    all_cols = [c for c in df.columns if c not in META and pd.api.types.is_numeric_dtype(df[c])]
    fams = families(all_cols)
    keep = ['SEMUA', 'arah', 'desc:rise', 'koherensi', 'magnitude']
    fams = {k: fams[k] for k in keep if k in fams}

    piv = df.groupby(['participant', 'phase'])['label'].first().unstack()
    changed = piv.index[piv['before'] != piv['after']].tolist()
    control = piv.index[piv['before'] == piv['after']].tolist()
    print(f'berubah: {len(changed)} | kontrol: {len(control)}')

    rng = np.random.default_rng(RANDOM_SEED)
    rows = []
    print(f"\n{'keluarga':12s} {'n':>4s} {'BA(berubah,label)':>18s} {'p':>7s} "
          f"{'BA(kontrol,sesi)':>17s} {'p':>7s}")
    for name, cols in fams.items():
        d1 = build_session_rows(df, cols, changed, 'label')
        b1, p1 = loso_ba(d1, cols, args.permutations, rng)
        d2 = build_session_rows(df, cols, control, 'session')
        b2, p2 = loso_ba(d2, cols, args.permutations, rng)
        rows.append({'family': name, 'n': len(cols), 'ba_changed': b1, 'p_changed': p1,
                     'ba_control': b2, 'p_control': p2})
        print(f'{name:12s} {len(cols):4d} {b1:18.4f} {p1:7.4f} {b2:17.4f} {p2:7.4f}', flush=True)

    args.out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.out / 'summary.csv', index=False)
    print(f'\nKeluaran: {args.out}/summary.csv')


if __name__ == '__main__':
    main()

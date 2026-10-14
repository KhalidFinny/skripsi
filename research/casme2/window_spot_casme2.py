#!/usr/bin/env python
"""Spotting CAS(ME)^2 dengan klasifikasi JENDELA (bukan per-puncak).

Kenapa: pendekatan sebelumnya (Iterasi 4.46-4.47) memberi satu PUNCAK ke
pengklasifikasi, padahal ekspresi punya PROFIL TEMPORAL (naik, apex, turun).
Skrip ini menggeser jendela di sepanjang video, merangkum tiap jendela, lalu
mengklasifikasikannya. Jendela positif yang berdampingan digabung menjadi satu
event, baru dicocokkan dengan ground truth.

Fitur per jendela, untuk tiap (ROI x sinyal): mean, std, max, slope, dan
selisih paruh-awal vs paruh-akhir. Sinyal kaya (6 per ROI) berasal dari cache
`rich_signals_casme2.py`.

Evaluasi: GroupKFold per VIDEO (model tidak pernah melihat video uji), lalu
event digabung dan dicocokkan dengan GT memakai aturan yang sama dengan
`eval_spotting_casme2.py` supaya angkanya sebanding.

Cara pakai:
    .venv/bin/python scripts/window_spot_casme2.py
    .venv/bin/python scripts/window_spot_casme2.py --window 32 --stride 4
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT, ROOT / 'pipeline' / 'stages'):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import eval_spotting_casme2 as bench  # noqa: E402
import rich_signals_casme2 as rich  # noqa: E402

DEFAULT_OUT = ROOT / 'output/training/window_spot_casme2'


def build_windows(video: str, sig: dict[str, np.ndarray], gt: list[dict],
                  size: int, stride: int) -> pd.DataFrame:
    """Satu baris per jendela, fitur dihitung vektor (sliding_window_view).

    Loop per jendela di Python terlalu lambat untuk sweep parameter; di sini
    seluruh jendela dihitung sekaligus per sinyal.
    """
    keys = list(sig.keys())
    n = len(sig[keys[0]])
    starts = np.arange(0, max(1, n - size + 1), stride)
    centers = starts + size // 2
    label = np.zeros(len(starts), dtype=np.int8)
    for x in gt:
        label |= ((centers >= x['onset']) & (centers <= x['offset'])).astype(np.int8)

    half = size // 2
    cols: dict[str, np.ndarray] = {}
    for k in keys:
        arr = np.asarray(sig[k], dtype=float)
        sw = np.lib.stride_tricks.sliding_window_view(arr, size)[::stride]
        cols[f'{k}__mean'] = sw.mean(axis=1)
        cols[f'{k}__std'] = sw.std(axis=1)
        cols[f'{k}__max'] = sw.max(axis=1)
        cols[f'{k}__range'] = sw.max(axis=1) - sw.min(axis=1)
        cols[f'{k}__slope'] = sw[:, half:].mean(axis=1) - sw[:, :half].mean(axis=1)

    d = pd.DataFrame(cols)
    d['video'] = video
    d['start'] = starts
    d['end'] = starts + size
    d['center'] = centers
    d['label'] = label
    return d


def windows_to_events(w: pd.DataFrame, scores: np.ndarray, threshold,
                      max_gap: int) -> list[dict]:
    """Gabungkan jendela positif berdampingan menjadi event.

    `threshold` boleh skalar atau array per-baris (dipakai saat ambang dipilih
    per fold, sehingga tiap video punya ambangnya sendiri).
    """
    w = w.assign(score=scores)
    thr = np.asarray(threshold, dtype=float)
    if thr.ndim == 0:
        positive = w.score.to_numpy() >= float(thr)
    else:
        positive = w.score.to_numpy() >= thr
    pos = w[positive].sort_values('start')
    if pos.empty:
        return []
    events = []
    cur_start = int(pos.iloc[0]['start'])
    cur_end = int(pos.iloc[0]['end'])
    cur_scores = [float(pos.iloc[0]['score'])]
    for row in pos.iloc[1:].itertuples():
        if int(row.start) - cur_end <= max_gap:
            cur_end = max(cur_end, int(row.end))
            cur_scores.append(float(row.score))
        else:
            events.append({'onset': cur_start + 1, 'offset': cur_end,
                           'score': float(np.mean(cur_scores))})
            cur_start, cur_end, cur_scores = int(row.start), int(row.end), [float(row.score)]
    events.append({'onset': cur_start + 1, 'offset': cur_end, 'score': float(np.mean(cur_scores))})
    return events


def match_events(gt: list[dict], det: list[dict], min_iou: float = 0.0) -> tuple[int, int, int]:
    """Cocokkan event deteksi ke GT (satu-ke-satu, ambil skor tertinggi dulu).

    `min_iou` > 0 memperketat: selain beririsan, tumpang tindih harus mencapai
    IoU minimum. Dipakai untuk memeriksa apakah hasil bagus hanya karena event
    deteksi dibuat sangat panjang sehingga selalu menutupi GT.
    """
    used_gt, tp = set(), 0
    for d in sorted(det, key=lambda e: -e['score']):
        best = None
        for gi, g in enumerate(gt):
            if gi in used_gt:
                continue
            if d['onset'] <= g['offset'] and g['onset'] <= d['offset']:
                if min_iou > 0:
                    inter = min(d['offset'], g['offset']) - max(d['onset'], g['onset']) + 1
                    union = max(d['offset'], g['offset']) - min(d['onset'], g['onset']) + 1
                    if union <= 0 or inter / union < min_iou:
                        continue
                best = gi
                break
        if best is None:
            continue
        used_gt.add(best)
        tp += 1
    return tp, len(det) - tp, len(gt) - tp


def _matched_gt_indices(gt: list[dict], det: list[dict]) -> set[int]:
    """Indeks GT yang berhasil dicocokkan (urutan sama dengan match_events)."""
    used: set[int] = set()
    for d in sorted(det, key=lambda e: -e['score']):
        for gi, g in enumerate(gt):
            if gi in used:
                continue
            if d['onset'] <= g['offset'] and g['onset'] <= d['offset']:
                used.add(gi)
                break
    return used


def main() -> None:
    ap = argparse.ArgumentParser(description='Spotting jendela CAS(ME)^2.')
    ap.add_argument('--cache-dir', type=Path, default=rich.DEFAULT_CACHE)
    ap.add_argument('--out', type=Path, default=DEFAULT_OUT)
    ap.add_argument('--window', type=int, default=32)
    ap.add_argument('--stride', type=int, default=4)
    ap.add_argument('--max-gap', type=int, default=None,
                    help='jarak maksimum antar jendela positif agar digabung jadi satu '
                         'event. Default = --window (perilaku awal). Nilai tetap membuat '
                         'perbandingan antar ukuran jendela tidak terkontaminasi '
                         'penggabungan yang ikut membesar.')
    ap.add_argument('--thresholds', type=float, nargs='+', default=[0.1, 0.2, 0.3, 0.5, 0.7],
                    help='kandidat ambang yang disapu. Kalau --threshold-mode inner, ambang '
                         'DIPILIH di dalam tiap fold (bukan dari prediksi uji).')
    ap.add_argument('--threshold-mode', choices=['inner', 'posthoc'], default='inner',
                    help="'inner' (default, jujur): untuk tiap fold, ambang dipilih di "
                         "sub-split dari data LATIH saja, lalu diterapkan ke data uji. "
                         "'posthoc': ambang terbaik dicari langsung di prediksi uji -- "
                         "angka F1-nya OPTIMISTIS (seleksi bocor), hanya untuk diagnosis.")
    ap.add_argument('--folds', type=int, default=5)
    ap.add_argument('--limit', type=int, default=None, help='batasi jumlah video (uji cepat)')
    args = ap.parse_args()

    gt = bench.load_ground_truth(bench.DEFAULT_GT, bench.DEFAULT_VIDEOS)
    gt_by_video = {v: g.to_dict('records') for v, g in gt.groupby('video')}

    frames = []
    for v in sorted(gt_by_video):
        sig = rich.load(rich.cache_file(args.cache_dir, v))
        if sig is None:
            continue
        frames.append(build_windows(v, sig, gt_by_video[v], args.window, args.stride))
        if args.limit and len(frames) >= args.limit:
            break
    if not frames:
        raise SystemExit(f'Tidak ada cache sinyal di {args.cache_dir}. '
                         f'Jalankan scripts/rich_signals_casme2.py dulu.')
    d = pd.concat(frames, ignore_index=True)
    meta = ['video', 'start', 'end', 'center', 'label']
    cols = [c for c in d.columns if c not in meta]
    X = d[cols].to_numpy(dtype=float)
    y = d['label'].to_numpy()
    groups = d['video'].to_numpy()
    print(f'jendela: {len(d)} | positif: {y.sum()} ({y.mean():.4f}) | '
          f'fitur: {len(cols)} | video: {d.video.nunique()}')
    print(f'window={args.window} stride={args.stride}')

    oof = np.zeros(len(y))
    thr_per_window = np.full(len(y), np.nan)
    n_splits = min(args.folds, d.video.nunique())
    max_gap = args.max_gap if args.max_gap is not None else args.window

    def event_f1_for(frame: pd.DataFrame, scores: np.ndarray, gt_lookup: dict,
                     thresholds: list[float], max_gap: int) -> tuple[float, float]:
        """F1 event terbaik + ambangnya, dihitung pada subset yang diberikan.

        `scores` HARUS sejajar posisi dengan `frame` (bukan indeks global),
        karena `frame` di sini bisa berupa potongan dari tabel besar.
        """
        best_f1, best_thr = -1.0, thresholds[0]
        for t in thresholds:
            tp = fp = fn = 0
            for v in sorted(set(frame['video'])):
                mask = (frame['video'] == v).to_numpy()
                if not mask.any():
                    continue
                det = windows_to_events(frame[mask], scores[mask], t, max_gap=max_gap)
                a, b, c = match_events(gt_lookup[v], det)
                tp += a; fp += b; fn += c
            p = tp / (tp + fp) if tp + fp else 0.0
            r = tp / (tp + fn) if tp + fn else 0.0
            f1 = 2 * p * r / (p + r) if p + r else 0.0
            if f1 > best_f1:
                best_f1, best_thr = f1, t
        return best_f1, best_thr

    chosen = []
    for fold_i, (tr, te) in enumerate(GroupKFold(n_splits=n_splits).split(X, y, groups)):
        if args.threshold_mode == 'inner':
            # Bagi video LATIH menjadi inner-train / inner-val untuk memilih ambang.
            tr_videos = np.array(sorted(set(groups[tr])))
            rng = np.random.default_rng(72 + fold_i)
            rng.shuffle(tr_videos)
            cut = max(1, int(len(tr_videos) * 0.75))
            inner_tr_v, inner_va_v = set(tr_videos[:cut]), set(tr_videos[cut:])
            mask_tr = np.isin(groups[tr], list(inner_tr_v))
            m_inner = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06, max_depth=3)
            m_inner.fit(X[tr][mask_tr], y[tr][mask_tr])
            sub_va = d.iloc[tr][~mask_tr]
            if len(sub_va):
                sc_va = m_inner.predict_proba(X[tr][~mask_tr])[:, 1]
                _, thr_star = event_f1_for(sub_va, sc_va, gt_by_video,
                                           args.thresholds, max_gap)
            else:
                thr_star = args.thresholds[len(args.thresholds) // 2]
        else:
            thr_star = float('nan')  # ditentukan post-hoc setelah semua prediksi ada
        chosen.append(thr_star)
        m_full = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06, max_depth=3)
        m_full.fit(X[tr], y[tr])
        oof[te] = m_full.predict_proba(X[te])[:, 1]
        thr_per_window[te] = thr_star
        print(f'  fold {fold_i + 1}/{n_splits}: ambang dipilih = {thr_star:.3f}', flush=True)

    from sklearn.metrics import roc_auc_score
    print(f'AUC (level jendela) = {roc_auc_score(y, oof):.4f}')

    # Event-level. Mode 'inner': pakai ambang per fold (jujur). Mode 'posthoc':
    # sapu ambang di prediksi uji (optimistis, hanya untuk diagnosis).
    rows = []
    type_rows = []
    sweep = [float('nan')] if args.threshold_mode == 'inner' else list(args.thresholds)
    for thr in sweep:
        tp = fp = fn = 0
        per_type = {t: {'tp': 0, 'fn': 0} for t in ('macro', 'micro')}
        for v in sorted(gt_by_video):
            sub = d[d.video == v]
            if sub.empty:
                continue
            idx = sub.index.to_numpy()
            sc = oof[idx]
            t_used = thr_per_window[idx] if args.threshold_mode == 'inner' else thr
            det = windows_to_events(sub, sc, t_used, max_gap=max_gap)
            g = gt_by_video[v]
            a, b, c = match_events(g, det)
            tp += a; fp += b; fn += c
            used = _matched_gt_indices(g, det)
            for gi, x in enumerate(g):
                t = x['expr_type']
                if gi in used:
                    per_type[t]['tp'] += 1
                else:
                    per_type[t]['fn'] += 1
        p = tp / (tp + fp) if tp + fp else float('nan')
        r = tp / (tp + fn) if tp + fn else float('nan')
        f1 = 2 * p * r / (p + r) if p and r and not np.isnan(p) and not np.isnan(r) else 0.0
        rows.append({'threshold': thr, 'tp': tp, 'fp': fp, 'fn': fn,
                     'precision': p, 'recall': r, 'f1': f1})
        for t in ('macro', 'micro'):
            n_gt = int((gt['expr_type'] == t).sum())
            hit = per_type[t]['tp']
            type_rows.append({'threshold': thr, 'type': t, 'n_gt': n_gt,
                              'recall': hit / n_gt if n_gt else float('nan')})
        label = ('ambang per-fold (inner)' if args.threshold_mode == 'inner'
                 else f'thr={thr:.2f} (posthoc, OPTIMISTIS)')
        print(f'  {label}: P={p:.4f} R={r:.4f} F1={f1:.4f} (TP {tp}, FP {fp}, FN {fn})',
              flush=True)
        print(f'         recall macro={per_type["macro"]["tp"]}/{per_type["macro"]["tp"] + per_type["macro"]["fn"]} '
              f'micro={per_type["micro"]["tp"]}/{per_type["micro"]["tp"] + per_type["micro"]["fn"]}',
              flush=True)

    # Pemeriksaan kejujuran: apakah event deteksi jauh lebih panjang dari GT?
    # Kalau ya, "beririsan" jadi syarat yang terlalu longgar.
    det_lens, gt_lens = [], []
    strict_tp = strict_fp = strict_fn = 0
    for v in sorted(gt_by_video):
        sub = d[d.video == v]
        if sub.empty:
            continue
        idx = sub.index.to_numpy()
        t_used = (thr_per_window[idx] if args.threshold_mode == 'inner'
                  else float(np.median(thr_per_window[idx])) if not np.isnan(thr_per_window[idx]).all()
                  else args.thresholds[0])
        det = windows_to_events(sub, oof[idx], t_used, max_gap=max_gap)
        g = gt_by_video[v]
        det_lens += [e['offset'] - e['onset'] + 1 for e in det]
        gt_lens += [x['offset'] - x['onset'] + 1 for x in g]
        a, b, c = match_events(g, det, min_iou=0.5)
        strict_tp += a; strict_fp += b; strict_fn += c
    sp = strict_tp / (strict_tp + strict_fp) if strict_tp + strict_fp else float('nan')
    sr = strict_tp / (strict_tp + strict_fn) if strict_tp + strict_fn else float('nan')
    sf1 = 2 * sp * sr / (sp + sr) if sp and sr and not np.isnan(sp) and not np.isnan(sr) else 0.0
    print(f'\n  durasi event deteksi: median {np.median(det_lens):.0f} frame '
          f'(n={len(det_lens)}, {len(det_lens) / len(gt_by_video):.1f}/video)', flush=True)
    print(f'  durasi GT           : median {np.median(gt_lens):.0f} frame', flush=True)
    print(f'  dengan syarat IoU >= 0,5: P={sp:.4f} R={sr:.4f} F1={sf1:.4f}', flush=True)

    # Lokalisasi: seberapa dekat pusat event terdekat ke apex GT? Ini memisahkan
    # "batas event terlalu lebar" (bisa diperbaiki) dari "tidak menemukan tempatnya".
    center_dists = []
    for v in sorted(gt_by_video):
        sub = d[d.video == v]
        if sub.empty:
            continue
        idx = sub.index.to_numpy()
        t_used = (thr_per_window[idx] if args.threshold_mode == 'inner'
                  else args.thresholds[0])
        det = windows_to_events(sub, oof[idx], t_used, max_gap=max_gap)
        if not det:
            center_dists += [10 ** 6] * len(gt_by_video[v])
            continue
        centers = np.array([(e['onset'] + e['offset']) / 2 for e in det])
        for x in gt_by_video[v]:
            center_dists.append(float(np.min(np.abs(centers - x['apex']))))
    cd = np.array(center_dists)
    loc = {f'within_{t}': float((cd <= t).mean()) for t in (10, 20, 40, 80)}
    print(f'  lokalisasi (jarak pusat event ke apex GT): median {np.median(cd):.0f} frame | '
          + ' '.join(f'<={t}:{loc[f"within_{t}"]:.3f}' for t in (10, 20, 40, 80)), flush=True)
    strict = {'precision': sp, 'recall': sr, 'f1': sf1,
              'det_median_len': float(np.median(det_lens)),
              'gt_median_len': float(np.median(gt_lens)),
              'loc_median_dist': float(np.median(cd)), **loc}

    args.out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.out / 'summary.csv', index=False)
    pd.DataFrame(type_rows).to_csv(args.out / 'per_type.csv', index=False)
    best = max(rows, key=lambda r: (r['f1'] if not np.isnan(r['f1']) else -1))
    thr_desc = ('ambang dipilih per fold dari data latih (inner, jujur)'
                if args.threshold_mode == 'inner'
                else 'ambang disapu di prediksi uji (posthoc, OPTIMISTIS)')
    lines = ['# Spotting CAS(ME)^2 dengan klasifikasi jendela', '',
             f'- jendela: {len(d)} ({d.video.nunique()} video) | positif {y.sum()} ({y.mean():.4f})',
             f'- window={args.window} frame, stride={args.stride}, max_gap={max_gap}, '
             f'fitur={len(cols)}',
             f'- AUC level jendela: {roc_auc_score(y, oof):.4f}',
             f'- GroupKFold {n_splits} (per video, tidak pernah lihat video uji)',
             f'- ambang: {thr_desc}',
             f'- ambang terpilih per fold: {[round(c, 3) for c in chosen]}',
             '', '| threshold | precision | recall | F1 | TP | FP | FN |', '|---|---|---|---|---|---|---|']
    for r in rows:
        thr_txt = 'inner' if np.isnan(r['threshold']) else f'{r["threshold"]:.2f}'
        lines.append(f'| {thr_txt} | {r["precision"]:.4f} | {r["recall"]:.4f} | '
                     f'{r["f1"]:.4f} | {r["tp"]} | {r["fp"]} | {r["fn"]} |')
    lines += ['', '## Recall per tipe', '',
              '| threshold | tipe | n GT | recall |', '|---|---|---|---|']
    for r in type_rows:
        thr_txt = 'inner' if np.isnan(r['threshold']) else f'{r["threshold"]:.2f}'
        lines.append(f'| {thr_txt} | {r["type"]} | {r["n_gt"]} | {r["recall"]:.4f} |')
    lines += ['', '## Pemeriksaan kejujuran (durasi event)', '',
              f'- durasi event deteksi: median {strict["det_median_len"]:.0f} frame',
              f'- durasi GT: median {strict["gt_median_len"]:.0f} frame',
              f'- kalau tumpang tindih diperketat ke IoU >= 0,5: '
              f'P={strict["precision"]:.4f} R={strict["recall"]:.4f} F1={strict["f1"]:.4f}',
              '',
              'Selisih antara F1 longgar dan F1 IoU>=0,5 menunjukkan seberapa besar '
              'keunggulan berasal dari event yang dibuat panjang.',
              '',
              '## Lokalisasi (jarak pusat event ke apex GT)', '',
              f'- median jarak: {strict["loc_median_dist"]:.0f} frame',
              f'- dalam 10 frame: {strict["within_10"]:.3f}',
              f'- dalam 20 frame: {strict["within_20"]:.3f}',
              f'- dalam 40 frame: {strict["within_40"]:.3f}',
              f'- dalam 80 frame: {strict["within_80"]:.3f}',
              '',
              'Ini memisahkan dua kemungkinan: batas event yang terlalu lebar (masih '
              'bisa diperbaiki dengan penajaman batas) versus metode yang memang tidak '
              'menemukan tempat ekspresinya.',
              '',
              'Dua jebakan metodologi yang ditutup di sini:',
              '1. Hasil subset kecil TIDAK stabil (window=16: AUC 0,71 pada 20 video vs 0,60 '
              'pada 86), jadi angka dihitung pada seluruh video.',
              '2. Ambang TIDAK dipilih dari prediksi uji. Pada mode posthoc, menyapu ambang '
              'di data uji lalu melaporkan F1 terbaik adalah seleksi yang bocor dan angkanya '
              'optimistis; mode inner memilih ambang dari data latih saja.']
    (args.out / 'summary.md').write_text('\n'.join(lines) + '\n')
    print(f'\nF1 = {best["f1"]:.4f}')
    print(f'Keluaran: {args.out}/summary.md')


if __name__ == '__main__':
    main()

#!/usr/bin/env python
"""SANITY CHECK regime 60 fps (data kecemasan) sebelum regenerasi penuh.

Tiga hal yang diuji pada klip kecemasan NYATA (60 fps, .avi, ~950 frame/klip):

1. DRIFT: acuan frame-0 pada 60 fps menumpuk pergeseran 2x lebih cepat daripada
   30 fps. Apakah sinyal didominasi tren lambat? Diukur sebagai rasio energi
   frekuensi tinggi vs rendah, dan dibandingkan dengan acuan lokal (lag30/lag60).

2. WINDOW: apakah panjang window hasil tuning di CAS(ME)^2 (30 fps, didominasi
   makro) masih masuk akal di 60 fps yang menargetkan MIKRO? Diukur jumlah
   puncak + event top_k=5 untuk window 7 vs 3% vs 5%.

3. MIKRO: apakah event yang ditemukan berdurasi wajar untuk micro-expression
   (1/25-1/5 detik = 2,4-12 frame pada 60 fps)?

Cara pakai:
    .venv/bin/python scripts/audit_anxiety_regime.py --limit 16
"""

from __future__ import annotations

import argparse
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT, ROOT / 'pipeline' / 'stages'):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import stage_1_spotting as spot  # noqa: E402
from features.poc import POC  # noqa: E402
from features.vektor import Vektor  # noqa: E402

MODES = ('abs', 'lag30', 'lag60')
DEFAULT_ROOT = Path('/home/finny/datasets/anxiety_avi')


def _crop(gray, lm):
    out = {}
    for r, idx in spot.config.regions.items():
        if lm is None:
            out[r] = None
            continue
        try:
            roi = spot.extract_region(gray, lm, idx)
            if roi.size == 0:
                out[r] = None
                continue
            tw, th = spot.config.target_size[r]
            out[r] = cv2.resize(roi, (tw, th))
        except Exception:
            out[r] = None
    return out


def signals_for_video(video: str) -> dict[str, list[float]]:
    """Sinyal global (mean antar-ROI) untuk abs/lag30/lag60, satu pass."""
    regions = spot.config.regions
    out = {m: [] for m in MODES}
    hist = []
    frame0 = None
    n = 0
    cap = cv2.VideoCapture(video)
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            lm = spot.detect_landmarks(gray, spot.WORKER_DETECTOR, spot.WORKER_PREDICTOR)
            cur = _crop(gray, lm)
            if n == 0:
                frame0 = cur
            else:
                hist.append((n, cur))
                for mode in MODES:
                    # abs = acuan frame-0 (pergeseran kumulatif);
                    # lagN = acuan frame n-N (pergeseran lokal).
                    ref_i = 0 if mode == 'abs' else max(0, n - int(mode[3:]))
                    ref = frame0 if ref_i == 0 else None
                    if ref is None:
                        for idx, c in hist:
                            if idx == ref_i:
                                ref = c
                                break
                    if ref is None:
                        out[mode].append(np.nan)
                        continue
                    mags = []
                    for r in regions:
                        a, c = ref.get(r), cur.get(r)
                        if a is None or c is None:
                            continue
                        try:
                            poc = POC(a, c, spot.config.block_size)
                            q = Vektor(poc.getPOC(), spot.config.block_size).getVektor()
                            m = [float(x[4]) for x in q]
                            if m:
                                mags.append(float(np.mean(m)))
                        except Exception:
                            pass
                    out[mode].append(float(np.mean(mags)) if mags else np.nan)
                if len(hist) > 61:
                    hist.pop(0)
            n += 1
    finally:
        cap.release()
    if n < 5 or frame0 is None or all(v is None for v in frame0.values()):
        return {}
    for k in out:
        out[k] = spot._interpolate_signal(out[k])
    return out


def worker(video: str) -> tuple[str, dict]:
    try:
        return video, signals_for_video(video)
    except Exception as exc:
        return video, {'error': repr(exc)}


def smooth_fixed(x: np.ndarray, w: int) -> np.ndarray:
    from scipy.signal import savgol_filter
    w = min(w, len(x) - 1)
    if w % 2 == 0:
        w -= 1
    if w < 5:
        return x
    po = 2 if w <= 7 else (3 if w <= 15 else 4)
    return savgol_filter(x, w, po)


def smooth_pct(x: np.ndarray, pct: float) -> np.ndarray:
    w = int(len(x) * pct)
    if w % 2 == 0:
        w += 1
    w = max(5, w)
    if w >= len(x):
        w = len(x) - 1 if len(x) % 2 == 0 else len(x) - 2
    if w < 5:
        return x
    po = 2 if w <= 7 else (3 if w <= 15 else 4)
    from scipy.signal import savgol_filter
    return savgol_filter(x, w, po)


def trend_metrics(x: np.ndarray) -> dict:
    """Rasio energi frekuensi tinggi vs rendah. Rendah = didominasi drift."""
    w = min(121, len(x) - 1)
    if w % 2 == 0:
        w -= 1
    if w < 5:
        return {'hi_lo': float('nan'), 'corr_trend': float('nan')}
    low = smooth_fixed(x, w)
    hi = x - low
    return {'hi_lo': float(np.std(hi) / max(np.std(low), 1e-9)),
            'corr_trend': float(np.corrcoef(x, low)[0, 1]) if np.std(x) > 0 else float('nan')}


def peaks_and_events(sig: np.ndarray, window: str, top_k: int = 5) -> tuple[int, int, list[int]]:
    from scipy.signal import find_peaks
    if window == 'fix7':
        sm = smooth_fixed(sig, 7)
    elif window == 'pct3':
        sm = smooth_pct(sig, 0.03)
    elif window == 'pct5':
        sm = smooth_pct(sig, 0.05)
    else:
        sm = sig
    if len(sm) < 10:
        return 0, 0, []
    pk, _ = find_peaks(sm, distance=1)
    h = float(sm.mean() + sm.std())
    if len(pk) == 0:
        return 0, 0, []
    from scipy.signal import peak_prominences
    prom = peak_prominences(sm, pk)[0]
    keep = [i for i in np.argsort(-prom) if sm[pk[i]] > h][:top_k]
    ap = sorted(pk[i] for i in keep)
    durs = []
    # durasi kasar: jarak antar setengah tetangga
    for a in ap:
        durs.append(0)
    return len(pk), len(ap), durs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    ap.add_argument('--limit', type=int, default=16)
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--out', type=Path, default=ROOT / 'output/training/audit_anxiety_regime')
    args = ap.parse_args()

    vids = sorted(args.root.rglob('after/*/*/q*/*.avi'))
    if not vids:
        vids = sorted(args.root.rglob('*.avi'))
    if args.limit and args.limit < len(vids):
        step = max(1, len(vids) // args.limit)
        vids = vids[::step][:args.limit]
    print(f'klip diuji: {len(vids)}')

    results = {}
    with ProcessPoolExecutor(max_workers=max(1, args.workers),
                             initializer=spot.init_worker,
                             initargs=(str(ROOT / 'models/shape_predictor_68_face_landmarks.dat'),)) as ex:
        futs = {ex.submit(worker, str(v)): v for v in vids}
        for i, f in enumerate(as_completed(futs), 1):
            v, sig = f.result()
            if 'error' in sig:
                print(f'  GAGAL {Path(v).name[:40]}: {sig["error"]}')
                continue
            results[str(v)] = sig
            print(f'  [{i}/{len(vids)}] {Path(v).name[:45]} frames={len(sig["abs"])}', flush=True)

    print(f'\nberhasil: {len(results)} klip\n')

    # ---- 1. drift per acuan ----
    print('=== 1. DRIFT: energi frekuensi tinggi vs rendah (rendah = didominasi tren) ===')
    print(f"{'acuan':8s} {'hi/lo':>8s} {'corr_trend':>11s}")
    drift = {}
    for mode in MODES:
        hs, cs = [], []
        for sig in results.values():
            x = np.nan_to_num(np.asarray(sig[mode], dtype=float), nan=0.0)
            if len(x) < 130:
                continue
            m = trend_metrics(x)
            hs.append(m['hi_lo']); cs.append(m['corr_trend'])
        drift[mode] = {'hi_lo': float(np.median(hs)), 'corr_trend': float(np.median(cs))}
        print(f"{mode:8s} {drift[mode]['hi_lo']:8.3f} {drift[mode]['corr_trend']:11.3f}")

    # ---- 2. window ----
    print('\n=== 2. WINDOW: jumlah puncak & event top_k=5 ===')
    print(f"{'window':8s} {'puncak/klip':>12s} {'event/klip':>11s}")
    win_rows = {}
    for w in ('fix7', 'pct3', 'pct5'):
        pks, evs = [], []
        for sig in results.values():
            x = np.nan_to_num(np.asarray(sig['abs'], dtype=float), nan=0.0)
            npk, nev, _ = peaks_and_events(x, w)
            pks.append(npk); evs.append(nev)
        win_rows[w] = {'puncak': float(np.median(pks)), 'event': float(np.median(evs))}
        print(f"{w:8s} {win_rows[w]['puncak']:12.0f} {win_rows[w]['event']:11.1f}")

    # ---- 3. durasi event (pakai ApexPhase, sama seperti pipeline) ----
    print('\n=== 3. DURASI event (micro-expression 60fps = 2,4-12 frame) ===')
    from apex import ApexPhase
    from scipy.signal import find_peaks, peak_prominences
    for w in ('fix7', 'pct3', 'pct5'):
        durs = []
        for sig in results.values():
            x = np.nan_to_num(np.asarray(sig['abs'], dtype=float), nan=0.0)
            sm = smooth_fixed(x, 7) if w == 'fix7' else smooth_pct(x, 0.03 if w == 'pct3' else 0.05)
            if len(sm) < 10:
                continue
            det = ApexPhase(distance_threshold=1, prominence_threshold=0.0, cutoff_ratio=0.3)
            pk, _ = find_peaks(sm, distance=1, height=float(sm.mean() + sm.std()))
            if len(pk) == 0:
                continue
            prom = peak_prominences(sm, pk)[0]
            ap = sorted(pk[i] for i in np.argsort(-prom)[:5])
            ph = det.find_phase(sm.tolist(), ap) if ap else {}
            for a in ap:
                p = ph.get(a)
                if p is None:
                    continue
                durs.append(int(p['end'] - p['start']))
        if durs:
            print(f"{w:8s} median={np.median(durs):5.0f}  p25={np.percentile(durs,25):5.0f}  "
                  f"p75={np.percentile(durs,75):5.0f}  (n={len(durs)})")

    args.out.mkdir(parents=True, exist_ok=True)
    lines = ['# Sanity check regime 60 fps (data kecemasan)', '',
             f'klip: {len(results)} (after/*)', '',
             '## 1. Drift', '',
             '| acuan | hi/lo | corr_trend |', '|---|---|---|']
    for m in MODES:
        lines.append(f"| {m} | {drift[m]['hi_lo']:.3f} | {drift[m]['corr_trend']:.3f} |")
    lines += ['', '## 2. Window', '', '| window | puncak/klip | event/klip |', '|---|---|---|']
    for w, r in win_rows.items():
        lines.append(f"| {w} | {r['puncak']:.0f} | {r['event']:.1f} |")
    (args.out / 'summary.md').write_text('\n'.join(lines) + '\n')
    print(f'\nKeluaran: {args.out}/summary.md')


if __name__ == '__main__':
    main()

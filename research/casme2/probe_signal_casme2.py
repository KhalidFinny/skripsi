#!/usr/bin/env python
"""Uji sinyal mana yang paling memisahkan puncak ekspresi (CAS(ME)^2).

Benchmark 4.45 + rank_peak menunjukkan: sinyal POC-ABS (mean magnitudo, acuan
frame-0) memuncak di ekspresi (persentil 0,988) TAPI puncak ekspresi hanya
peringkat ~17% di antara ~125 puncak/ROI. Tidak ada skor puncak handcrafted
yang memisahkan.

Skrip ini menguji apakah yang salah adalah DEFINISI SINYALNYA:
  agregasi : mean (dipakai sekarang) / max / count blok bergerak
  acuan    : frame-0 (POC-ABS, sekarang) / frame sebelumnya (berurutan)

Metrik: peringkat relatif puncak ekspresi terbaik (0 = skor tertinggi).
Makin kecil makin baik. Acak = 0,5.

Cara pakai:
    .venv/bin/python scripts/probe_signal_casme2.py --videos 4
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
from scipy.signal import find_peaks

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT, ROOT / 'pipeline' / 'stages'):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import eval_spotting_casme2 as bench  # noqa: E402
import stage_1_spotting as spot  # noqa: E402
from apex import ApexSmoother  # noqa: E402
from features.poc import POC  # noqa: E402
from features.quadran import Quadran  # noqa: E402
from features.vektor import Vektor  # noqa: E402


def signals_multi(video: Path) -> dict[str, dict[str, list[float]]]:
    """{mode: {roi: sinyal}} untuk mode 'abs' dan 'seq', tiap mode 3 agregasi."""
    cap = cv2.VideoCapture(str(video))
    grays, lms = [], []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        grays.append(gray)
        lms.append(spot.detect_landmarks(gray, spot.WORKER_DETECTOR, spot.WORKER_PREDICTOR))
    cap.release()

    regions = spot.config.regions
    out = {m: {k: {r: [] for r in regions} for k in ('mean', 'max', 'count')}
           for m in ('abs', 'seq')}
    if lms[0] is None:
        return out

    def one(ref_g, ref_lm, cur_g, cur_lm, region):
        a = spot.extract_region(ref_g, ref_lm, regions[region])
        c = spot.extract_region(cur_g, cur_lm, regions[region])
        if a.size == 0 or c.size == 0:
            return None
        tw, th = spot.config.target_size[region]
        poc = POC(cv2.resize(a, (tw, th)), cv2.resize(c, (tw, th)), spot.config.block_size)
        q = Quadran(Vektor(poc.getPOC(), spot.config.block_size).getVektor()).getQuadran()
        mags = np.array([float(x[4]) for x in q], dtype=float)
        if mags.size == 0:
            return None
        return float(mags.mean()), float(mags.max()), float((mags > 0).mean())

    for i in range(1, len(grays)):
        cur_lm = lms[i]
        for region in regions:
            vals = {}
            if cur_lm is not None:
                a = one(grays[0], lms[0], grays[i], cur_lm, region)
                b = one(grays[i - 1], lms[i - 1], grays[i], cur_lm, region) if lms[i - 1] is not None else None
                if a:
                    vals['abs'] = a
                if b:
                    vals['seq'] = b
            for m in ('abs', 'seq'):
                v = vals.get(m)
                for k, j in (('mean', 0), ('max', 1), ('count', 2)):
                    out[m][k][region].append(v[j] if v else np.nan)

    for m in out:
        for k in out[m]:
            out[m][k] = {r: spot._interpolate_signal(v) for r, v in out[m][k].items()}
    return out


def rank_quality(sig: dict[str, list[float]], gt: list[dict]) -> tuple[float, int]:
    """Median peringkat relatif puncak ekspresi terbaik + jumlah puncak."""
    rq, n = [], 0
    for _r, s in sig.items():
        sm = np.asarray(ApexSmoother.smooth(s), dtype=float)
        if len(sm) < 10:
            continue
        pk, _ = find_peaks(sm, distance=1, height=sm.mean() + sm.std(),
                           prominence=max(0.04 * (sm.max() - sm.min()), 0.005))
        n += len(pk)
        if len(pk) < 5:
            continue
        order = np.argsort(-sm[pk])
        rank_of = {int(pk[o]): k for k, o in enumerate(order)}
        for x in gt:
            cand = [int(i) for i in pk if i + 1 - 6 <= x['offset'] and x['onset'] <= i + 1 + 6]
            if cand:
                rq.append(min(rank_of[i] for i in cand) / len(pk))
    return (float(np.median(rq)) if rq else float('nan')), n


def main() -> None:
    ap = argparse.ArgumentParser(description='Uji definisi sinyal untuk spotting CAS(ME)^2.')
    ap.add_argument('--videos', type=int, default=4)
    args = ap.parse_args()

    gt = bench.load_ground_truth(bench.DEFAULT_GT, bench.DEFAULT_VIDEOS)
    vids = sorted(gt['video'].unique())[:args.videos]
    spot.init_worker(str(bench.PREDICTOR))

    agg = {}
    for i, v in enumerate(vids, 1):
        g = gt[gt.video == v].to_dict('records')
        multi = signals_multi(Path(v))
        line = []
        for m in ('abs', 'seq'):
            for k in ('mean', 'max', 'count'):
                rq, n = rank_quality(multi[m][k], g)
                agg.setdefault((m, k), []).append(rq)
                line.append(f'{m}/{k}:{rq:.3f}({n})')
        print(f'  [{i}/{len(vids)}] {Path(v).name} gt={len(g)} | ' + ' '.join(line), flush=True)

    print('\n=== median peringkat relatif puncak ekspresi (0=terbaik, 0,5=acak)')
    rows = sorted(agg.items(), key=lambda kv: np.nanmedian(kv[1]))
    for (m, k), vals in rows:
        print(f'  {m:3s} / {k:5s}: {np.nanmedian(vals):.3f}')
    print('\nBaseline sekarang = abs / mean.')


if __name__ == '__main__':
    main()

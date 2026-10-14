#!/usr/bin/env python
"""AUDIT block_size POC: 7 (asli notebook) vs 9 (sekarang).

Satu-satunya divergensi tersisa yang belum diuji. `roi_config.py` mengubah
block_size 7 -> 9 dengan alasan mengurangi saturasi POC. Tapi ROI alis tingginya
hanya 20 px: pada block_size 9 itu cuma ~2 blok, nyaris degenerate.

Skrip menghitung sinyal POC-ABS (acuan frame-0, agregasi global) untuk KEDUA
block_size dalam satu pass per video, lalu mengukur F1 dengan protokol benchmark.

Cara pakai:
    .venv/bin/python scripts/audit_block_size_casme2.py --workers 3
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

import eval_spotting_casme2 as bench  # noqa: E402
import stage_1_spotting as spot  # noqa: E402
from features.poc import POC  # noqa: E402
from features.quadran import Quadran  # noqa: E402
from features.vektor import Vektor  # noqa: E402

BLOCK_SIZES = (7, 9)
DEFAULT_CACHE = ROOT / 'output/training/casme2_blocksize_signals'


def signals_for_video(video: str) -> dict[str, list[float]]:
    regions = spot.config.regions
    out: dict[str, list[float]] = {f'b{b}__{r}': [] for b in BLOCK_SIZES for r in regions}
    ref: dict[str, np.ndarray | None] = {}
    n = 0
    cap = cv2.VideoCapture(video)
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            lm = spot.detect_landmarks(gray, spot.WORKER_DETECTOR, spot.WORKER_PREDICTOR)
            cur = {}
            for r, idx in regions.items():
                cur[r] = None
                if lm is None:
                    continue
                try:
                    roi = spot.extract_region(gray, lm, idx)
                    if roi.size == 0:
                        continue
                    tw, th = spot.config.target_size[r]
                    cur[r] = cv2.resize(roi, (tw, th))
                except Exception:
                    cur[r] = None
            if n == 0:
                ref = cur
            else:
                for r in regions:
                    for b in BLOCK_SIZES:
                        a, c = ref.get(r), cur.get(r)
                        if a is None or c is None:
                            out[f'b{b}__{r}'].append(np.nan)
                            continue
                        try:
                            poc = POC(a, c, b)
                            q = Vektor(poc.getPOC(), b).getVektor()
                            mags = np.array([float(x[4]) for x in q], dtype=float)
                            out[f'b{b}__{r}'].append(float(mags.mean()) if mags.size else np.nan)
                        except Exception:
                            out[f'b{b}__{r}'].append(np.nan)
            n += 1
    finally:
        cap.release()
    if n < 5 or not ref or all(v is None for v in ref.values()):
        return {}
    for k in out:
        out[k] = spot._interpolate_signal(out[k])
    return out


def cache_file(cache_dir: Path, video: str) -> Path:
    v = Path(video)
    return cache_dir / f'{v.parent.name}_{v.stem}.npz'


def load(path: Path):
    if not path.exists():
        return None
    try:
        with np.load(path) as z:
            return {k: z[k].astype(float) for k in z.files}
    except (OSError, ValueError):
        return None


def save(path: Path, sig: dict[str, list[float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    with open(tmp, 'wb') as fh:
        np.savez_compressed(fh, **{k: np.asarray(v, dtype=float) for k, v in sig.items()})
    tmp.replace(path)


def worker(job: tuple[str, str]) -> tuple[str, bool, str]:
    video, cache_path = job
    path = Path(cache_path)
    if load(path) is not None:
        return video, True, 'cached'
    try:
        sig = signals_for_video(video)
    except Exception as exc:
        return video, False, repr(exc)
    if not sig:
        return video, False, 'kosong'
    save(path, sig)
    return video, True, f'{len(next(iter(sig.values())))} frame'


def detect(sig: np.ndarray, top_k: int) -> list[dict]:
    sm = np.asarray(spot.ApexSmoother.smooth(sig.tolist()), dtype=float)
    h = float(sm.mean() + sm.std())
    d = spot.ApexPhase(distance_threshold=1, prominence_threshold=0.005, cutoff_ratio=0.3)
    ap = d.find_top_k_apex(sm.tolist(), k=top_k, height=h)
    ph = d.find_phase(sm.tolist(), ap) if ap else {}
    out = []
    for a in ap:
        p = ph.get(a)
        if p is None or int(p['end'] - p['start']) < 2:
            continue
        out.append({'onset': spot.signal_index_to_frame_index(int(p['start'])),
                    'apex': spot.signal_index_to_frame_index(int(a)),
                    'offset': spot.signal_index_to_frame_index(int(p['end'])),
                    'region': 'global'})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache-dir', type=Path, default=DEFAULT_CACHE)
    ap.add_argument('--workers', type=int, default=3)
    ap.add_argument('--top-k', type=int, nargs='+', default=[5, 8])
    ap.add_argument('--limit', type=int, default=0,
                    help='kalau >0, uji hanya ~N video (disebar merata) supaya cepat')
    ap.add_argument('--out', type=Path, default=ROOT / 'output/training/audit_block_size_casme2')
    args = ap.parse_args()

    gt = bench.load_ground_truth(bench.DEFAULT_GT, bench.DEFAULT_VIDEOS)
    gt_by = {v: g.to_dict('records') for v, g in gt.groupby('video')}
    videos = sorted(gt_by)
    if args.limit and args.limit < len(videos):
        step = max(1, len(videos) // args.limit)
        videos = videos[::step][:args.limit]
        gt_by = {v: gt_by[v] for v in videos}
    args.cache_dir.mkdir(parents=True, exist_ok=True)

    jobs = [(v, str(cache_file(args.cache_dir, v))) for v in videos]
    ok = fail = 0
    with ProcessPoolExecutor(max_workers=max(1, args.workers),
                             initializer=spot.init_worker,
                             initargs=(str(bench.PREDICTOR),)) as ex:
        futures = {ex.submit(worker, j): j[0] for j in jobs}
        for i, fut in enumerate(as_completed(futures), 1):
            video, success, info = fut.result()
            ok += success; fail += (not success)
            if not success:
                print(f'  GAGAL {Path(video).name}: {info}', flush=True)
            elif i % 20 == 0:
                print(f'  [{i}/{len(jobs)}] ok={ok} gagal={fail}', flush=True)
    print(f'sinyal: {ok} ok, {fail} gagal')

    rows = []
    print(f"\n{'block':>6s} {'top_k':>6s} {'P':>7s} {'R':>7s} {'F1':>7s} {'det/video':>10s}")
    for b in BLOCK_SIZES:
        for k in args.top_k:
            tp = fp = fn = ndet = nvid = 0
            for v, g in gt_by.items():
                sig = load(cache_file(args.cache_dir, v))
                if sig is None:
                    continue
                nvid += 1
                regions = list(spot.config.regions)
                keys = [f'b{b}__{r}' for r in regions if f'b{b}__{r}' in sig]
                if not keys:
                    continue
                n = min(len(sig[k_]) for k_ in keys)
                glob = np.mean([np.asarray(sig[k_][:n], dtype=float) for k_ in keys], axis=0)
                if len(glob) < 10:
                    continue
                det = detect(glob, k)
                ndet += len(det)
                p, f, f_ = bench.match_events(g, det, 0)
                tp += len(p); fp += len(f); fn += len(f_)
            sc = bench.scores(tp, fp, fn)
            rows.append({'block_size': b, 'top_k': k, 'precision': sc['precision'],
                         'recall': sc['recall'], 'f1': sc['f1'],
                         'det_per_video': ndet / max(1, nvid)})
            print(f"{b:6d} {k:6d} {sc['precision']:7.4f} {sc['recall']:7.4f} "
                  f"{sc['f1']:7.4f} {ndet/max(1,nvid):10.1f}", flush=True)

    args.out.mkdir(parents=True, exist_ok=True)
    import pandas as pd
    pd.DataFrame(rows).to_csv(args.out / 'summary.csv', index=False)
    lines = ['# Audit block_size POC pada CAS(ME)^2', '',
             'Agregasi global, acuan frame-0, toleransi 0 frame.', '',
             '| block_size | top_k | precision | recall | F1 | det/video |',
             '|---|---|---|---|---|---|']
    for r in rows:
        lines.append(f"| {r['block_size']} | {r['top_k']} | {r['precision']:.4f} | "
                     f"{r['recall']:.4f} | {r['f1']:.4f} | {r['det_per_video']:.1f} |")
    (args.out / 'summary.md').write_text('\n'.join(lines) + '\n')
    print(f'\nKeluaran: {args.out}/summary.md')


if __name__ == '__main__':
    main()

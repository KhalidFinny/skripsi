from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EXP_ROOT = ROOT / 'third_party/tabular-dl-tabr-official' / 'exp' / 'tabr'
DEFAULT_OUT = ROOT / 'output' / 'training'


def scalar_metrics(metrics: dict) -> dict:
    out = {}
    for split, values in metrics.items():
        if not isinstance(values, dict):
            continue
        for key, value in values.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                out[f'{split}_{key}'] = value
    return out


def balanced_metrics(metrics: dict) -> dict:
    """Metrik seimbang per split: macroF1 dan balanced accuracy (rata-rata recall kelas)."""
    out = {}
    for split, values in metrics.items():
        if not isinstance(values, dict):
            continue
        macro = values.get('macro avg')
        if isinstance(macro, dict) and isinstance(macro.get('f1-score'), (int, float)):
            out[f'{split}_macroF1'] = macro['f1-score']
        recalls = [
            values[k]['recall']
            for k in ('0', '1')
            if isinstance(values.get(k), dict) and isinstance(values[k].get('recall'), (int, float))
        ]
        if len(recalls) == 2:
            out[f'{split}_bal_acc'] = sum(recalls) / 2
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description='Kumpulkan hasil training TabR ke folder hasil.')
    parser.add_argument('--exp', default='convat_apex_anxiety')
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    exp_dir = EXP_ROOT / args.exp
    eval_dir = exp_dir / '0-evaluation'
    if not eval_dir.is_dir():
        raise SystemExit(f'Tidak ada {eval_dir} - training belum dijalankan.')

    rows = []
    for run_dir in sorted(eval_dir.iterdir()):
        if not (run_dir.is_dir() and run_dir.name.isdigit()):
            continue
        report_path = run_dir / 'report.json'
        if not report_path.exists():
            continue
        with open(report_path) as f:
            report = json.load(f)
        metrics = report.get('metrics', {})
        row = {
            'seed': int(run_dir.name),
            'val_score': metrics.get('val', {}).get('score'),
            'test_score': metrics.get('test', {}).get('score'),
            'time': report.get('time'),
        }
        row.update(scalar_metrics(metrics))
        row.update(balanced_metrics(metrics))
        row['run_dir'] = str(run_dir)
        rows.append(row)

    if not rows:
        raise SystemExit(f'Tidak ada report.json di {eval_dir} - training gagal/terputus.')

    df = pd.DataFrame(rows).sort_values('val_score', ascending=False).reset_index(drop=True)
    best = df.iloc[0]
    best_seed = int(best['seed'])

    out_dir = args.out / args.exp
    out_dir.mkdir(parents=True, exist_ok=True)

    table = df.drop(columns=['run_dir'])
    table.to_csv(out_dir / 'summary.csv', index=False)

    shutil.copy(eval_dir / str(best_seed) / 'report.json', out_dir / 'best_report.json')
    for toml_name in ['0-tuning.toml', f'{best_seed}.toml']:
        src = exp_dir / toml_name
        if src.exists():
            shutil.copy(src, out_dir / toml_name)

    lines = [
        f'# Hasil Training TabR - {args.exp}',
        '',
        f'Total run dengan report.json: {len(df)}',
        f'Run terbaik (val_score): seed {best_seed} - val {best["val_score"]:.4f} / test {best["test_score"]:.4f}',
        '',
        '## Semua run (urut val_score)',
        '',
        table.to_string(index=False),
        '',
        'File: summary.csv (semua run), best_report.json + config (run terbaik).',
    ]
    (out_dir / 'summary.md').write_text('\n'.join(lines))

    print(f'Hasil training: {out_dir}')
    print()
    print(f'Run terbaik: seed {best_seed} (val_score {best["val_score"]:.4f})')
    for split in ['train', 'val', 'test']:
        parts = []
        for col in table.columns:
            if col.startswith(f'{split}_') and pd.notna(best[col]):
                parts.append(f'{col.split("_", 1)[1]}={best[col]:.4f}')
        if parts:
            print(f'  {split}: ' + ', '.join(parts))
    print()
    print(f'  - summary.md / summary.csv : semua run')
    print(f'  - best_report.json         : report run terbaik (seed {best_seed})')
    print(f'  - config TOML              : 0-tuning.toml + {best_seed}.toml')


if __name__ == '__main__':
    main()

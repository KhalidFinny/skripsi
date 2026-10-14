from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler


RANDOM_SEED = 72
ROOT = Path(__file__).resolve().parent.parent
_PARSER = argparse.ArgumentParser(description='Ekspor fitur POC-ABS ke format TabR (split subjek-disjoint).')
_PARSER.add_argument('--features', type=Path, default=ROOT / 'experiments/features/apex/poc_abs_flatten_ordered.xlsx')
_PARSER.add_argument('--dataset', default='convat_apex_anxiety')
_PARSER.add_argument('--drop-derived', action='store_true', help='buang kolom _t/_m (turunan pasti dari x,y)')
_ARGS = _PARSER.parse_args()

FEATURES_PATH = _ARGS.features
OFFICIAL_ROOT = ROOT / 'third_party/tabular-dl-tabr-official'
DATASET_NAME = _ARGS.dataset
OUT_DIR = OFFICIAL_ROOT / 'data' / DATASET_NAME


def balance_train_clips_by_label(df_train: pd.DataFrame, seed: int = 42):
    rng = random.Random(seed)
    event_table_train = (
        df_train[['event_id', 'label', 'target', 'phase', 'participant', 'question', 'clip', 'event_clip']]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    grouped = {}
    for label_name, label_df in event_table_train.groupby('label', sort=True):
        clip_table = (
            label_df[['participant', 'question', 'clip', 'label']]
            .drop_duplicates()
            .sort_values(['participant', 'question', 'clip'], kind='stable')
            .reset_index(drop=True)
        )
        grouped[label_name] = clip_table
    min_clip_count = min(len(x) for x in grouped.values())
    selected_clip_keys = []
    for label_name, clip_table in grouped.items():
        clip_records = clip_table.to_dict('records')
        rng.shuffle(clip_records)
        chosen = clip_records[:min_clip_count]
        selected_clip_keys.extend([
            (row['participant'], row['question'], row['clip'], row['label'])
            for row in chosen
        ])
    selected_clip_keys = set(selected_clip_keys)
    return df_train[
        df_train.apply(lambda row: (row['participant'], row['question'], row['clip'], row['label']) in selected_clip_keys, axis=1)
    ].copy()


def main():
    print('[1/7] Baca tabel fitur:', FEATURES_PATH)
    df = pd.read_excel(FEATURES_PATH)
    label_map = {'anxiety_rendah': 0, 'anxiety_tinggi': 1}
    df = df[df['label'].isin(label_map)].copy()
    df['target'] = df['label'].map(label_map)
    df['event_id'] = (
        df['phase'].astype(str) + '||' + df['participant'].astype(str) + '||' +
        df['question'].astype(str) + '||' + df['clip'].astype(str) + '||' + df['event_clip'].astype(str)
    )
    print(f'      baris={len(df)}, kelas:', df['label'].value_counts().to_dict())

    print('[2/7] Split subjek-disjoint (GroupShuffleSplit: test 20%, val 20%)')
    participants = pd.Series(df['participant'].unique())
    gss_test = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=RANDOM_SEED)
    train_val_idx, test_idx = next(gss_test.split(participants, groups=participants))
    train_val_parts = participants.iloc[train_val_idx]
    test_parts = participants.iloc[test_idx]
    gss_val = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=RANDOM_SEED)
    train_idx, val_idx = next(gss_val.split(train_val_parts, groups=train_val_parts))
    train_parts = train_val_parts.iloc[train_idx]
    val_parts = train_val_parts.iloc[val_idx]
    df_tr = df[df['participant'].isin(train_parts)].copy()
    df_val = df[df['participant'].isin(val_parts)].copy()
    df_external = df[df['participant'].isin(test_parts)].copy()
    print(f'      subjek train={len(train_parts)}, val={len(val_parts)}, test={len(test_parts)}')
    print(f'      baris train={len(df_tr)}, val={len(df_val)}, external={len(df_external)}')

    for part_name, part_df in [('train', df_tr), ('val', df_val), ('test', df_external)]:
        labels = set(part_df['label'])
        if labels != {'anxiety_rendah', 'anxiety_tinggi'}:
            raise SystemExit(
                f'Split {part_name} tidak punya kedua kelas (label={sorted(labels)}). '
                'Subjek-disjoint tapi tidak seimbang - coba seed lain / stratifikasi subjek.'
            )

    print('[3/7] Balance train clips per label')
    df_tr = balance_train_clips_by_label(df_tr, seed=RANDOM_SEED)
    print(f'      train setelah balance={len(df_tr)} baris')

    print('[4/7] Impute + StandardScaler (fit di train saja)')
    meta_cols = [
        'phase', 'condition', 'label', 'participant', 'participant_raw', 'question', 'question_no',
        'sample', 'clip', 'event_clip', 'event_no', 'clip_path', 'frame', 'target', 'event_id',
    ]
    feature_cols = [c for c in df.columns if c not in meta_cols]
    if _ARGS.drop_derived:
        n_before = len(feature_cols)
        feature_cols = [c for c in feature_cols if not re.match(r'^.*_[tm]\d+$', c)]
        print(f'      drop-derived: {n_before} -> {len(feature_cols)} fitur (buang _t/_m, turunan x,y)')

    imputer = SimpleImputer(strategy='mean')
    scaler = StandardScaler()
    X_train = scaler.fit_transform(imputer.fit_transform(df_tr[feature_cols])).astype(np.float32)
    X_val = scaler.transform(imputer.transform(df_val[feature_cols])).astype(np.float32)
    X_test = scaler.transform(imputer.transform(df_external[feature_cols])).astype(np.float32)
    y_train = df_tr['target'].to_numpy(dtype=np.int64)
    y_val = df_val['target'].to_numpy(dtype=np.int64)
    y_test = df_external['target'].to_numpy(dtype=np.int64)

    print('[5/7] Simpan npy + info:', OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    np.save(OUT_DIR / 'X_num_train.npy', X_train)
    np.save(OUT_DIR / 'X_num_val.npy', X_val)
    np.save(OUT_DIR / 'X_num_test.npy', X_test)
    np.save(OUT_DIR / 'Y_train.npy', y_train)
    np.save(OUT_DIR / 'Y_val.npy', y_val)
    np.save(OUT_DIR / 'Y_test.npy', y_test)
    (OUT_DIR / 'READY').write_text('')
    (OUT_DIR / 'info.json').write_text(json.dumps({'task_type': 'binclass', 'name': 'Convat Apex Anxiety', 'id': DATASET_NAME}, indent=2))
    (OUT_DIR / 'feature_cols.json').write_text(json.dumps(feature_cols, indent=2))
    df_tr.to_csv(OUT_DIR / 'train_split.csv', index=False)
    df_val.to_csv(OUT_DIR / 'val_split.csv', index=False)
    df_external.to_csv(OUT_DIR / 'test_split.csv', index=False)
    print('[7/7] Selesai:', OUT_DIR)


if __name__ == '__main__':
    main()

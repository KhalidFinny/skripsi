#!/usr/bin/env python3
"""split_persons_presplit.py — Tahap 0 fold-first: bagi ORANG sebelum spotting.

Memindai raw root (<phase>/<condition>/<participant>_<ts>/q*/...), mengelompokkan
56 orang, dan menahan sebagian (--test-people) sebagai HOLDOUT TEST yang tidak
boleh dibaca pipeline sampai evaluasi akhir. Stratifikasi memakai label-pair
per orang (kondisi sesi before/after):

  tinggi_both : before=anxiety & after=anxiety   (label anxiety_tinggi dua-duanya)
  changed     : kondisi berubah antar sesi       (18 orang — kunci pertanyaan STATE)
  rendah_both : before=tidak & after=tidak

Normalisasi nama orang SAMA dengan extract_features_poc_abs.py
(`re.sub(r'_[0-9]+$', '', participant_raw)`), jadi himpunan orang di sini
identik dengan kolom `participant` di tabel fitur.

Output (di --out, default output/presplit):
  split.csv         person,split,strata,n_sessions,conditions
  train_persons.txt satu orang per baris (dipakai SPOT_INCLUDE_PERSONS)
  test_persons.txt  satu orang per baris (dibaca HANYA oleh stage 8 holdout)
  summary.md        tabel strata + daftar orang + seed/tanggal

Deterministik: seed yang sama -> split yang sama.
Script ini HANYA membaca nama direktori; tidak membuka file video.
"""
from __future__ import annotations

import argparse
import random
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

PHASES = ('before', 'after')
CONDITION_TO_LABEL = {'anxiety': 'anxiety_tinggi', 'tidak': 'anxiety_rendah'}


def normalize_person(participant_raw: str) -> str:
    return re.sub(r'_[0-9]+$', '', participant_raw)


def scan_persons(raw_root: Path) -> dict[str, dict[str, str]]:
    """person -> {phase: condition}. Gagal keras pada struktur tak terduga."""
    persons: dict[str, dict[str, str]] = {}
    for phase in PHASES:
        phase_dir = raw_root / phase
        if not phase_dir.is_dir():
            sys.exit(f'GAGAL: direktori fase tidak ada: {phase_dir}')
        for cond_dir in sorted(p for p in phase_dir.iterdir() if p.is_dir()):
            condition = cond_dir.name
            if condition not in CONDITION_TO_LABEL:
                continue  # abaikan direktori lain (bukan kondisi)
            for part_dir in sorted(p for p in cond_dir.iterdir() if p.is_dir()):
                person = normalize_person(part_dir.name)
                slot = persons.setdefault(person, {})
                if phase in slot and slot[phase] != condition:
                    sys.exit(
                        f'GAGAL: {person} punya 2 kondisi di fase {phase}: '
                        f'{slot[phase]} vs {condition}. Struktur dataset tidak '
                        f'sesuai asumsi (1 kondisi per orang per fase).'
                    )
                slot[phase] = condition
    return persons


def strata_of(conditions: dict[str, str]) -> str:
    labels = {CONDITION_TO_LABEL[conditions[p]] for p in PHASES}
    if len(labels) == 2:
        return 'changed'
    return 'tinggi_both' if labels == {'anxiety_tinggi'} else 'rendah_both'


def allocate(test_people: int, strata_counts: dict[str, int], total: int) -> dict[str, int]:
    """Alokasi proporsional dengan largest remainder. Jumlah = test_people."""
    quotas = {s: test_people * n / total for s, n in strata_counts.items()}
    alloc = {s: int(q) for s, q in quotas.items()}
    sisa = test_people - sum(alloc.values())
    for s in sorted(quotas, key=lambda s: quotas[s] - int(quotas[s]), reverse=True)[:sisa]:
        alloc[s] += 1
    return alloc


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--raw-root', type=Path,
                    default=Path('/run/media/finny/New Volume/dataset/anxiety_raw'))
    ap.add_argument('--out', type=Path, default=Path('output/presplit'))
    ap.add_argument('--test-people', type=int, default=12)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--dry-run', action='store_true', help='cetak rencana tanpa menulis file')
    args = ap.parse_args()

    persons = scan_persons(args.raw_root)
    total = len(persons)
    if total == 0:
        sys.exit(f'GAGAL: tidak ada peserta di {args.raw_root}')

    # Validasi: tiap orang harus punya kedua fase (asumsi label-unit=session).
    kurang = [p for p, c in persons.items() if set(c) != set(PHASES)]
    if kurang:
        sys.exit(
            f'GAGAL: {len(kurang)} orang tidak punya 2 fase lengkap '
            f'(contoh: {sorted(kurang)[:5]}). Pre-split mengasumsikan 2 sesi/orang.'
        )

    strata_map: dict[str, list[str]] = {}
    for person, conditions in persons.items():
        strata_map.setdefault(strata_of(conditions), []).append(person)
    strata_counts = {s: len(v) for s, v in strata_map.items()}

    if args.test_people >= total:
        sys.exit(f'GAGAL: --test-people {args.test_people} >= total orang {total}')
    alloc = allocate(args.test_people, strata_counts, total)
    for s, n in alloc.items():
        if n > strata_counts[s]:
            sys.exit(f'GAGAL: strata {s} hanya {strata_counts[s]} orang, diminta {n}')

    rng = random.Random(args.seed)
    test_persons: list[str] = []
    rows = []
    for s in sorted(strata_map):
        members = sorted(strata_map[s])
        picked = set(rng.sample(members, alloc[s]))
        test_persons.extend(sorted(picked))
        for person in members:
            rows.append({
                'person': person,
                'split': 'test' if person in picked else 'train',
                'strata': s,
                'n_sessions': len(persons[person]),
                'conditions': ';'.join(f'{p}={persons[person][p]}' for p in PHASES),
            })
    test_persons.sort()
    train_persons = sorted(r['person'] for r in rows if r['split'] == 'train')

    df = pd.DataFrame(rows).sort_values(['split', 'strata', 'person'],
                                        ascending=[False, True, True])
    alloc_str = ', '.join(f'{s}={alloc[s]}/{strata_counts[s]}' for s in sorted(alloc))
    print(f'Orang total     : {total}')
    print(f'Strata          : {strata_counts}')
    print(f'Holdout test    : {len(test_persons)} orang ({alloc_str})')
    print(f'Train pool      : {len(train_persons)} orang')
    print(f'Seed            : {args.seed}')
    if args.dry_run:
        print('\n[dry-run] daftar test:')
        for p in test_persons:
            print(f'  {p}  ({strata_of(persons[p])})')
        return

    args.out.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out / 'split.csv', index=False)
    (args.out / 'train_persons.txt').write_text('\n'.join(train_persons) + '\n')
    (args.out / 'test_persons.txt').write_text('\n'.join(test_persons) + '\n')

    md = [
        '# Pre-split fold-first (sebelum spotting)',
        '',
        f'- Dibuat   : {datetime.now():%Y-%m-%d %H:%M:%S}',
        f'- Raw root : `{args.raw_root}`',
        f'- Seed     : {args.seed}',
        f'- Total    : {total} orang -> train {len(train_persons)}, HOLDOUT TEST {len(test_persons)}',
        f'- Strata   : {strata_counts}',
        f'- Alokasi  : {alloc_str}',
        '',
        '## Holdout test (JANGAN dibaca pipeline sampai evaluasi akhir)',
        '',
        '| person | strata | kondisi |',
        '|---|---|---|',
    ]
    for p in test_persons:
        md.append(f'| {p} | {strata_of(persons[p])} | '
                  f'{"; ".join(f"{ph}={persons[p][ph]}" for ph in PHASES)} |')
    md += [
        '',
        '## Cara pakai',
        '',
        '- Stage 1-7 pipeline: `SPOT_INCLUDE_PERSONS=<dir>/train_persons.txt`',
        '- Stage 8 holdout  : `SPOT_INCLUDE_PERSONS=<dir>/test_persons.txt` + '
        '`run_loso.py --test-persons-file <dir>/test_persons.txt`',
    ]
    (args.out / 'summary.md').write_text('\n'.join(md) + '\n')
    print(f'\nTertulis: {args.out}/split.csv, train_persons.txt, test_persons.txt, summary.md')


if __name__ == '__main__':
    main()

# 03 — Pisahkan eksperimen CAS(ME)² dari pipeline (high)

## Current Problem

Dari 61 file di `scripts/`, **26 adalah skrip eksperimen CAS(ME)²** dan
**4 adalah audit umum**. Semuanya duduk bersebelahan dengan 10 stage pipeline,
sehingga tidak ada cara membedakan "kode produksi" dari "kode penyelidikan"
tanpa membuka satu per satu.

26 skrip CAS(ME)² (semuanya mengandung `casme2` di namanya):

```
audit_agg_f1_casme2.py            audit_peak_rank_casme2.py
audit_baseline_agg_casme2.py      audit_signal_transform_casme2.py
audit_baseline_recheck_casme2.py  audit_smoothing_casme2.py
audit_block_size_casme2.py        audit_window_sweep_casme2.py
audit_detector_grid_casme2.py     baseline_probe_casme2.py
audit_detector_internals_casme2.py diag_magnitude_casme2.py
audit_feature_family_casme2.py    diag_roi_signal_casme2.py
audit_hpoc_casme2.py              eval_spotting_casme2.py
audit_mag_agg_casme2.py           probe_learned_rank_casme2.py
audit_baseline_agg_casme2.py      probe_rich_features_casme2.py
probe_signal_casme2.py            probe_smoothing_casme2.py
probe_spotting_mechanism_casme2.py rank_peak_casme2.py
rank_rich_casme2.py               rich_signals_casme2.py
window_spot_casme2.py
```

4 audit umum (tidak spesifik CAS(ME)²):

```
audit_anxiety_regime.py        audit_identity_dominance.py
audit_feature_representation.py audit_rise_control.py
```

Catatan penting: skrip-skrip ini **dipakai** — sebagian sudah menghasilkan temuan
yang tercatat di `report/findings/` (mis. `magnitude-deepdive.md`,
`spotting-feature-deepdive.md`, `audit-spotting-casme2.md`). Jadi ini **bukan
sampah**; hanya salah tempat.

## Target

```
research/
  casme2/      26 skrip eksperimen CAS(ME)²
  audits/      4 audit umum
  README.md    apa isi tiap subfolder + skrip mana menghasilkan temuan mana
```

`research/README.md` menautkan skrip ke dokumen temuan terkait, mis.:

| Skrip | Menghasilkan |
|---|---|
| `casme2/audit_smoothing_casme2.py` | `report/findings/audit-spotting-casme2.md` |
| `casme2/diag_magnitude_casme2.py` | `report/findings/magnitude-deepdive.md` |
| `casme2/probe_spotting_mechanism_casme2.py` | `report/findings/spotting-feature-deepdive.md` |

## Required Design

- **Tidak ada skrip eksperimen yang dihapus.** Semua dipindah, isi tidak diubah.
- Skrip eksperimen juga memakai pola `ROOT = Path(__file__).resolve().parent.parent`.
  Setelah pindah ke `research/casme2/` (dua tingkat di bawah root), pola itu
  harus menyesuaikan dengan cara yang sama seperti stage (lihat issue 02).
  Boleh memakai helper yang sama (`pipeline/paths.py`) atau pola `parents[2]`
  yang konsisten.
- Skrip eksperimen tidak boleh diimpor oleh pipeline. Setelah pindah,
  pastikan tidak ada stage yang mengimpor `research/`.
- Jangan pindahkan data yang dihasilkan skrip ini (`output/training/audit_*`,
  `output/training/probe_*`) — itu sudah gitignored dan tidak perlu dirapikan.

## Tests

- `.venv/bin/python -m py_compile research/casme2/*.py research/audits/*.py`
- `grep -rn "scripts/audit_\|scripts/probe_\|scripts/diag_\|scripts/rank_" --include=*.sh --include=*.py .`
  harus kosong di luar `legacy/` dan dokumen lama.
- `ls scripts/` tidak lagi memuat nama yang mengandung `casme2`.

## Done Criteria

- [ ] 26 skrip CAS(ME)² ada di `research/casme2/`
- [ ] 4 audit umum ada di `research/audits/`
- [ ] `research/README.md` ada, menautkan skrip ke dokumen temuan
- [ ] `py_compile` bersih untuk semua file yang dipindah
- [ ] Tidak ada stage pipeline yang mengimpor `research/`
- [ ] Tidak ada skrip eksperimen yang terhapus

"""Titik tunggal yang tahu di mana root repo berada.

Skrip stage ada di `pipeline/stages/`, jadi root repo adalah dua tingkat di
atasnya. Semua stage memakai helper ini supaya tidak ada salinan
`Path(__file__).resolve().parent.parent` yang gampang salah saat file dipindah.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[1]


def ensure_on_path() -> None:
    """Pastikan root repo ada di sys.path sebelum mengimpor modul proyek."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

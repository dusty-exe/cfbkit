"""Where the data lives.

Raw CFBD Starter Pack CSVs are read-only vendor data and live outside this
repo (personal-use license, ~1.1 GB). Derived Parquet also lives outside the
repo. Both are overridable by environment variable.
"""

from __future__ import annotations

import os
from pathlib import Path

RAW_ROOT = Path(os.environ.get("CFB_RAW_ROOT", Path.home() / "Desktop/artifacts/data"))
PARQUET_ROOT = Path(os.environ.get("CFB_PARQUET_ROOT", Path.home() / "Desktop/cfb-data"))

PLAYS_GLOB = str(RAW_ROOT / "plays/*/*_plays.csv")
DRIVES_GLOB = str(RAW_ROOT / "drives/drives_*.csv")
GAMES_CSV = RAW_ROOT / "games.csv"
TEAMS_CSV = RAW_ROOT / "teams.csv"
CONFERENCES_CSV = RAW_ROOT / "conferences.csv"

PLAYS_PARQUET = PARQUET_ROOT / "plays"
DRIVES_PARQUET = PARQUET_ROOT / "drives.parquet"
GAMES_PARQUET = PARQUET_ROOT / "games.parquet"
TEAMS_PARQUET = PARQUET_ROOT / "teams.parquet"


def check_raw() -> None:
    """Fail loudly and early if the vendor data isn't where we think."""
    if not RAW_ROOT.exists():
        raise FileNotFoundError(
            f"Raw data root not found: {RAW_ROOT}\n"
            "Set CFB_RAW_ROOT to the Starter Pack's data/ directory."
        )

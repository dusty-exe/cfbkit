"""CFBD roster pull -> Parquet. Adds the one thing play-by-play lacks: position.

The play-by-play carries no player fields at all -- names live only inside
playText, and nothing there says whether a pass catcher is a WR, TE or RB.
Rosters close that gap and are the join key for any player-level work.

The API key is read from $CFBD_API_KEY, else ~/.config/cfbd/api_key. It is
deliberately never stored in this repo, which is public.
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path

import duckdb

from .paths import PARQUET_ROOT

API = "https://api.collegefootballdata.com/roster"
ROSTER_PARQUET = PARQUET_ROOT / "roster.parquet"
KEY_FILE = Path.home() / ".config/cfbd/api_key"


def api_key() -> str:
    key = os.environ.get("CFBD_API_KEY")
    if key:
        return key.strip()
    if KEY_FILE.exists():
        return KEY_FILE.read_text().strip()
    raise RuntimeError(
        "No CFBD API key. Set $CFBD_API_KEY or write it to ~/.config/cfbd/api_key "
        "(chmod 600). Free key at https://collegefootballdata.com"
    )


def fetch_season(year: int, key: str, classification: str = "fbs") -> list[dict]:
    req = urllib.request.Request(
        f"{API}?year={year}&classification={classification}",
        headers={"Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def build(seasons: range | list[int], pause: float = 1.0) -> Path:
    """Pull rosters and write one Parquet keyed by (season, team, player)."""
    key = api_key()
    rows = []
    for year in seasons:
        data = fetch_season(year, key)
        for p in data:
            first, last = (p.get("firstName") or ""), (p.get("lastName") or "")
            name = f"{first} {last}".strip()
            if not name or not p.get("position"):
                continue
            rows.append(dict(season=year, team=p.get("team"), player=name,
                             position=p["position"], jersey=p.get("jersey"),
                             player_id=p.get("id"),
                             height=p.get("height"), weight=p.get("weight"),
                             year_in_school=p.get("year")))
        print(f"  {year}: {len(data):>6} roster rows", flush=True)
        time.sleep(pause)

    PARQUET_ROOT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    # UNNEST alone yields a single struct column; alias and star-expand it.
    con.execute("CREATE TABLE r AS SELECT u.* FROM (SELECT UNNEST($rows) AS u)",
                {"rows": rows})
    con.sql("SELECT * FROM r").write_parquet(str(ROSTER_PARQUET))
    print(f"wrote {ROSTER_PARQUET} ({len(rows):,} rows)")
    return ROSTER_PARQUET


if __name__ == "__main__":
    build(range(2015, 2025))

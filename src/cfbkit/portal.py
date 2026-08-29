"""CFBD transfer portal -> Parquet.

Origin and destination let you measure talent FLOW between tiers, which the
static talent composite cannot show: a roster's recruiting-star total can
rise while its actual quality falls, if it is trading proven producers for
unproven former blue-chips.
"""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

import duckdb

from .paths import PARQUET_ROOT
from .roster import api_key

API = "https://api.collegefootballdata.com/player/portal"
PORTAL_PARQUET = PARQUET_ROOT / "portal.parquet"


def build(seasons: range | list[int], pause: float = 0.5) -> Path:
    key = api_key()
    rows = []
    for year in seasons:
        req = urllib.request.Request(f"{API}?year={year}",
                                     headers={"Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=90) as r:
            data = json.load(r)
        for d in data:
            rows.append(dict(
                season=int(d["season"]),
                player=f"{d.get('firstName') or ''} {d.get('lastName') or ''}".strip(),
                position=d.get("position"), origin=d.get("origin"),
                destination=d.get("destination"),
                stars=d.get("stars"), rating=d.get("rating"),
                eligibility=d.get("eligibility")))
        print(f"  {year}: {len(data):>5} transfers", flush=True)
        time.sleep(pause)
    con = duckdb.connect()
    con.execute("CREATE TABLE p AS SELECT u.* FROM (SELECT UNNEST($rows) AS u)",
                {"rows": rows})
    con.sql("SELECT * FROM p").write_parquet(str(PORTAL_PARQUET))
    print(f"wrote {PORTAL_PARQUET} ({len(rows):,} rows)")
    return PORTAL_PARQUET


if __name__ == "__main__":
    build(range(2018, 2026))

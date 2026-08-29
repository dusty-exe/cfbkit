"""CFBD 247-composite team talent ratings -> Parquet.

Talent is a recruiting *input* measure, independent of on-field results, so
it can be compared against performance to ask whether an outcome gap is
explained by the talent a program accumulates.
"""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

import duckdb

from .paths import PARQUET_ROOT
from .roster import api_key

API = "https://api.collegefootballdata.com/talent"
TALENT_PARQUET = PARQUET_ROOT / "talent.parquet"


def build(seasons: range | list[int], pause: float = 0.5) -> Path:
    key = api_key()
    rows = []
    for year in seasons:
        req = urllib.request.Request(f"{API}?year={year}",
                                     headers={"Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.load(r)
        rows += [dict(season=int(d["year"]), team=d["team"],
                      talent=float(d["talent"])) for d in data if d.get("talent")]
        print(f"  {year}: {len(data):>4} teams", flush=True)
        time.sleep(pause)
    con = duckdb.connect()
    con.execute("CREATE TABLE t AS SELECT u.* FROM (SELECT UNNEST($rows) AS u)",
                {"rows": rows})
    con.sql("SELECT * FROM t").write_parquet(str(TALENT_PARQUET))
    print(f"wrote {TALENT_PARQUET} ({len(rows):,} rows)")
    return TALENT_PARQUET


if __name__ == "__main__":
    build(range(2011, 2026))

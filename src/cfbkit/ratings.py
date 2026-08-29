"""CFBD SP+ team ratings -> Parquet. The standard public CFB power metric."""

from __future__ import annotations

import json, time, urllib.request
from pathlib import Path

import duckdb

from .paths import PARQUET_ROOT
from .roster import api_key

API = "https://api.collegefootballdata.com/ratings/sp"
SP_PARQUET = PARQUET_ROOT / "sp_ratings.parquet"


def build(seasons: range | list[int], pause: float = 0.4) -> Path:
    key = api_key()
    rows = []
    for year in seasons:
        req = urllib.request.Request(f"{API}?year={year}",
                                     headers={"Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.load(r)
        for d in data:
            if not d.get("team") or d.get("rating") is None:
                continue
            rows.append(dict(season=int(d["year"]), team=d["team"],
                             conference=d.get("conference"),
                             sp_rating=float(d["rating"]),
                             sp_ranking=d.get("ranking"),
                             sos=d.get("sos")))
        print(f"  {year}: {len(data):>4} teams", flush=True)
        time.sleep(pause)
    con = duckdb.connect()
    con.execute("CREATE TABLE r AS SELECT u.* FROM (SELECT UNNEST($rows) AS u)", {"rows": rows})
    con.sql("SELECT * FROM r").write_parquet(str(SP_PARQUET))
    print(f"wrote {SP_PARQUET} ({len(rows):,} rows)")
    return SP_PARQUET


if __name__ == "__main__":
    build(range(2011, 2026))

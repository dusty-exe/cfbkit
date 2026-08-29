# cfbkit

Data layer and models for custom college football advanced metrics. Stable and
boring by design — this should not churn when modeling opinions change. Those
live in `cfb-research`.

## Layout of the computation

```
raw play-by-play  ->  EP model  ->  EPA/PPA  ->  weighting  ->  aggregates
   (this repo)      (this repo)   (this repo)   (research)     (both)
```

## Data

Raw CSVs are the CFBD Starter Pack v2.0 (2026 Preseason Edition), **personal
use, do not redistribute** — so they live outside this repo and are never
committed.

| | Default path | Override |
|---|---|---|
| Raw CSV | `~/Desktop/artifacts/data` | `CFB_RAW_ROOT` |
| Derived Parquet | `~/Desktop/cfb-data` | `CFB_PARQUET_ROOT` |

Build the Parquet (~11s, 955 MB CSV -> 187 MB Parquet):

```bash
uv run python -m cfbkit.ingest
```

Read it:

```python
from cfbkit.data import connect
con = connect()          # views: plays, games, drives, teams
con.sql("SELECT * FROM plays WHERE season = 2025").show()
```

## Coverage

3,711,469 plays across 2003–2025, 20,630 games. 3,510,645 plays pass the
default model filter (scrimmage downs, valid clock, non-spring).

## What ingest fixes

The raw files need real work before they're usable:

- **No season/week/season_type columns.** They exist only in the file path
  (`plays/2024/regular_5_plays.csv`) and are parsed out.
- **Column order drifts by season** (2003 puts timeouts last), so every read
  is `union_by_name`.
- **`clock` is a stringified Python dict** — `"{'seconds': 16, 'minutes': 3}"`
  — parsed into `clock_seconds`, plus `half_seconds_remaining` and
  `game_seconds_remaining`.
- **FCS is in the data.** ~27 conferences appear. Join `teams.classification`
  to filter; there is no FBS flag on the play rows.
- **Bad rows are flagged, not dropped**: `is_synthetic_id` (20,206 plays with
  negative CFBD ids, mostly 2020–2025 — real plays, real text),
  `is_clock_valid` (155 rows with impossible clocks or period 0),
  `is_spring` (175 COVID spring-2021 plays filed under season 2020).

## `ppa` is the benchmark, not a feature

The raw plays carry CFBD's own `ppa`. It is ~20% null on the model population
(kickoffs, timeouts, penalties, end-of-period). Never train on it — it is what
the rebuilt EP model gets validated against.

"""Raw CFBD Starter Pack CSVs -> typed Parquet.

Runs once; everything downstream reads the Parquet. Two things the raw files
force on us:

1. Plays CSVs carry no season/week/season_type columns -- those live only in
   the file path (``plays/2024/regular_5_plays.csv``), so we parse them out.
2. Column *order* drifts across seasons (2003 puts the timeout columns last),
   so every read is union_by_name.
"""

from __future__ import annotations

import duckdb

from .paths import (
    DRIVES_GLOB,
    DRIVES_PARQUET,
    GAMES_CSV,
    GAMES_PARQUET,
    PARQUET_ROOT,
    PLAYS_GLOB,
    PLAYS_PARQUET,
    TEAMS_CSV,
    TEAMS_PARQUET,
    check_raw,
)

# Clock arrives as a stringified Python dict: "{'seconds': 16, 'minutes': 3}".
# Match on the bare word to sidestep the embedded single quotes.
_MINUTES = r"regexp_extract(clock, 'minutes[^a-z0-9]*([0-9]+)', 1)"
_SECONDS = r"regexp_extract(clock, 'seconds[^a-z0-9]*([0-9]+)', 1)"

PLAYS_SQL = f"""
WITH raw AS (
    SELECT *
    FROM read_csv('{PLAYS_GLOB}', union_by_name = true, filename = true,
                  sample_size = -1, ignore_errors = false)
),
parsed AS (
    SELECT
        * EXCLUDE (filename, clock),
        CAST(regexp_extract(filename, 'plays/([0-9]{{4}})/', 1) AS SMALLINT) AS season,
        regexp_extract(filename, '/([a-z_]+)_[0-9]+_plays\\.csv$', 1) AS season_type,
        CAST(regexp_extract(filename, '_([0-9]+)_plays\\.csv$', 1) AS TINYINT) AS week,
        TRY_CAST({_MINUTES} AS INTEGER) AS clock_minutes,
        TRY_CAST({_SECONDS} AS INTEGER) AS clock_seconds_part
    FROM raw
)
SELECT
    * EXCLUDE (clock_minutes, clock_seconds_part),
    COALESCE(clock_minutes, 0) * 60 + COALESCE(clock_seconds_part, 0) AS clock_seconds,
    -- Seconds left in the current half and in regulation. Overtime gets 0:
    -- untimed, so time-remaining features are meaningless there.
    CASE WHEN period IN (1, 3) THEN 900 ELSE 0 END
        + CASE WHEN period <= 4
               THEN COALESCE(clock_minutes, 0) * 60 + COALESCE(clock_seconds_part, 0)
               ELSE 0 END                                  AS half_seconds_remaining,
    CASE WHEN period <= 4
         THEN (4 - period) * 900
              + COALESCE(clock_minutes, 0) * 60 + COALESCE(clock_seconds_part, 0)
         ELSE 0 END                                        AS game_seconds_remaining,
    CASE WHEN period <= 2 THEN 1 WHEN period <= 4 THEN 2 ELSE 3 END AS half,
    period > 4                                             AS is_overtime,
    -- Spring 2021 (COVID) games are filed under season 2020. Different sport;
    -- flagged so callers can drop them rather than silently mixing them in.
    starts_with(season_type, 'spring')                     AS is_spring,
    offenseScore - defenseScore                            AS score_diff,
    -- CFBD backfills some plays with negative ids (~0.5%, mostly 2020-2025).
    -- The play text is real, so these are kept, not dropped -- just marked.
    id < 0                                                 AS is_synthetic_id,
    -- A handful of rows carry impossible clocks (e.g. 58:00 in the 4th) and
    -- 103 rows have period 0. Time-based features are unusable on these.
    (period BETWEEN 1 AND 4 AND clock_seconds BETWEEN 0 AND 900)
        OR period > 4                                      AS is_clock_valid
FROM parsed
"""


def build_plays(con: duckdb.DuckDBPyConnection) -> None:
    PLAYS_PARQUET.mkdir(parents=True, exist_ok=True)
    con.sql(PLAYS_SQL).write_parquet(
        str(PLAYS_PARQUET), partition_by=["season"], overwrite=True
    )


def build_games(con: duckdb.DuckDBPyConnection) -> None:
    con.sql(
        f"SELECT * FROM read_csv('{GAMES_CSV}', union_by_name = true, sample_size = -1)"
    ).write_parquet(str(GAMES_PARQUET))


def build_drives(con: duckdb.DuckDBPyConnection) -> None:
    con.sql(
        f"SELECT * FROM read_csv('{DRIVES_GLOB}', union_by_name = true, sample_size = -1)"
    ).write_parquet(str(DRIVES_PARQUET))


def build_teams(con: duckdb.DuckDBPyConnection) -> None:
    con.sql(
        f"SELECT * FROM read_csv('{TEAMS_CSV}', union_by_name = true, sample_size = -1)"
    ).write_parquet(str(TEAMS_PARQUET))


def build_all() -> None:
    check_raw()
    PARQUET_ROOT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    for name, fn in (
        ("teams", build_teams),
        ("games", build_games),
        ("drives", build_drives),
        ("plays", build_plays),
    ):
        print(f"building {name} ...", flush=True)
        fn(con)
    print(f"done -> {PARQUET_ROOT}")


if __name__ == "__main__":
    build_all()

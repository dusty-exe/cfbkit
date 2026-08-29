"""Read side. Everything downstream starts here."""

from __future__ import annotations

import duckdb

from .paths import DRIVES_PARQUET, GAMES_PARQUET, PLAYS_PARQUET, TEAMS_PARQUET
from .roster import ROSTER_PARQUET


def connect() -> duckdb.DuckDBPyConnection:
    """A connection with `plays`, `games`, `drives`, `teams` registered as views."""
    con = duckdb.connect()
    con.sql(
        f"""
        CREATE VIEW plays AS
            SELECT * FROM read_parquet('{PLAYS_PARQUET}/**/*.parquet',
                                       hive_partitioning = true);
        CREATE VIEW games  AS SELECT * FROM read_parquet('{GAMES_PARQUET}');
        CREATE VIEW drives AS SELECT * FROM read_parquet('{DRIVES_PARQUET}');
        CREATE VIEW teams  AS SELECT * FROM read_parquet('{TEAMS_PARQUET}');
        """
    )
    if ROSTER_PARQUET.exists():
        con.sql(f"""
            CREATE VIEW roster AS
            SELECT *, {name_key('player')} AS name_key
            FROM read_parquet('{ROSTER_PARQUET}')
        """)
    return con


def name_key(col: str) -> str:
    """SQL for a join key between playText names and roster names.

    playText and the roster disagree on suffixes and punctuation -- "John
    Metchie III" vs "John Metchie", "Jo'quavious" vs "Joquavious". Lowercasing
    and stripping both lifts the FBS reception match rate from 77% to 98%.
    """
    return (f"lower(regexp_replace(regexp_replace({col}, "
            r"'\s+(jr|sr|ii|iii|iv|v)\.?$', '', 'i'), '[^A-Za-z]', '', 'g'))")


# Receiver name as it appears in playText (terse format, 2015-2024).
RECEIVER_EXPR = "trim(regexp_extract(playText, 'pass complete to (.+?) for ', 1))"


# Scrimmage plays only, usable clock, no COVID spring games. This is the
# default population for EP work -- kickoffs and PATs (down 0) are excluded
# from *fitting*, but stay in the raw table because next-scoring-event
# labeling needs them.
MODEL_FILTER = "down BETWEEN 1 AND 4 AND is_clock_valid AND NOT is_spring"


def plays(con: duckdb.DuckDBPyConnection, seasons: list[int] | None = None,
          model_only: bool = True) -> duckdb.DuckDBPyRelation:
    where = [MODEL_FILTER] if model_only else []
    if seasons:
        where.append(f"season IN ({','.join(str(s) for s in seasons)})")
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    return con.sql(f"SELECT * FROM plays {clause}")

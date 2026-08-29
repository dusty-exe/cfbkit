"""Read side. Everything downstream starts here."""

from __future__ import annotations

import duckdb

from .paths import DRIVES_PARQUET, GAMES_PARQUET, PLAYS_PARQUET, TEAMS_PARQUET


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
    return con


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

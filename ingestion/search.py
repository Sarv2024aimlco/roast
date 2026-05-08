import time
import sqlite3
from ingestion.database import get_connection

FORTY_FIVE_DAYS_SECONDS = 3_888_000


def insert_signal(
    role: str,
    company_type: str,
    market: str,
    source: str,
    signal_type: str,
    content: str,
) -> int:
    """
    Insert one scraped market signal into the database.
    Returns the id of the newly inserted row.
    The FTS5 index and trigger update automatically — nothing extra needed.
    """
    conn = get_connection()

    with conn:
        cursor = conn.execute(
            """
            INSERT INTO market_signals
                (role, company_type, market, source, signal_type, content, fetched_at)
            VALUES
                (?, ?, ?, ?, ?, ?, ?)
            """,
            (role, company_type, market, source, signal_type, content, int(time.time())),
        )
        row_id = cursor.lastrowid

    conn.close()
    if row_id is None:
        raise RuntimeError("Failed to insert market signal")
    return row_id


def search_signals(
    role: str,
    company_type: str,
    market: str,
    query: str,
    limit: int = 15,
) -> list[dict]:
    """
    Search for relevant market signals for a given combination.

    Two steps:
    1. Filter by role + company_type + market + within 45 days
    2. Rank by FTS5 BM25 relevance score against the query

    Returns up to `limit` rows as dicts, best match first.
    """
    cutoff = int(time.time()) - FORTY_FIVE_DAYS_SECONDS

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT
            s.id,
            s.role,
            s.company_type,
            s.market,
            s.source,
            s.signal_type,
            s.content,
            s.fetched_at,
            fts.rank
        FROM market_signals s
        JOIN market_signals_fts fts ON s.id = fts.rowid
        WHERE
            s.role         = ?
            AND s.company_type = ?
            AND s.market       = ?
            AND s.fetched_at   > ?
            AND market_signals_fts MATCH ?
        ORDER BY fts.rank
        LIMIT ?
        """,
        (role, company_type, market, cutoff, query, limit),
    ).fetchall()

    conn.close()

    return [dict(row) for row in rows]


def delete_signals_for_combo(role: str, company_type: str, market: str) -> int:
    """
    Delete all signals for a combination.
    Called by the monthly cron before inserting fresh data.
    The delete trigger keeps FTS5 in sync automatically.
    Returns number of rows deleted.
    """
    conn = get_connection()

    with conn:
        cursor = conn.execute(
            """
            DELETE FROM market_signals
            WHERE role = ? AND company_type = ? AND market = ?
            """,
            (role, company_type, market),
        )
        deleted = cursor.rowcount

    conn.close()
    return deleted


def count_signals_for_combo(role: str, company_type: str, market: str) -> int:
    """
    Count how many signals exist for a combination.
    Used to check if a combination is in the database before deciding
    whether to fire a live Tavily fetch.
    """
    conn = get_connection()

    row = conn.execute(
        """
        SELECT COUNT(*) FROM market_signals
        WHERE role = ? AND company_type = ? AND market = ?
        AND fetched_at > ?
        """,
        (role, company_type, market, int(time.time()) - FORTY_FIVE_DAYS_SECONDS),
    ).fetchone()

    conn.close()
    return 0 if row is None else row[0]

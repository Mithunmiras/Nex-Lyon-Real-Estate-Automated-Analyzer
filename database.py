"""
Nex-Lyon Real Estate Analyzer - Database Layer
SQLite with historical price tracking and schema migration.
"""

import sqlite3
import datetime
from config import DB_NAME


def _connect():
    """Return a connection with dict-style row access."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# ─── Schema ────────────────────────────────────────────────────────────────────

def create_db():
    """Create all tables (or upgrade an existing database)."""
    conn = _connect()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS scrape_sessions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp       TEXT    NOT NULL,
            source          TEXT,
            mode            TEXT,
            listings_found  INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS properties (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            title           TEXT,
            price           INTEGER,
            location        TEXT    DEFAULT 'Lyon',
            arrondissement  TEXT,
            size            REAL,
            rooms           INTEGER,
            dpe             TEXT,
            description     TEXT,
            price_per_m2    REAL,
            url             TEXT,
            first_seen      TEXT,
            last_seen       TEXT,
            session_id      INTEGER,
            is_active       INTEGER DEFAULT 1
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            property_id     INTEGER,
            price           INTEGER,
            price_per_m2    REAL,
            recorded_at     TEXT,
            FOREIGN KEY (property_id) REFERENCES properties(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            property_id     INTEGER,
            score           REAL,
            roi_5yr         REAL,
            is_undervalued  INTEGER DEFAULT 0,
            summary         TEXT,
            analyzed_at     TEXT,
            FOREIGN KEY (property_id) REFERENCES properties(id)
        )
    """)

    # Upgrade legacy schema (adds columns that may be missing from old versions)
    for col, ctype in [
        ("arrondissement", "TEXT"),
        ("rooms", "INTEGER"),
        ("url", "TEXT"),
        ("first_seen", "TEXT"),
        ("last_seen", "TEXT"),
        ("session_id", "INTEGER"),
        ("is_active", "INTEGER DEFAULT 1"),
    ]:
        try:
            c.execute(f"ALTER TABLE properties ADD COLUMN {col} {ctype}")
        except sqlite3.OperationalError:
            pass  # column already exists

    conn.commit()
    conn.close()


# ─── Scrape Sessions ──────────────────────────────────────────────────────────

def create_session(source: str, mode: str) -> int:
    """Record a scrape session. Returns the session_id."""
    conn = _connect()
    now = datetime.datetime.now().isoformat()
    cur = conn.execute(
        "INSERT INTO scrape_sessions (timestamp, source, mode) VALUES (?, ?, ?)",
        (now, source, mode),
    )
    sid = cur.lastrowid
    conn.commit()
    conn.close()
    return sid


def update_session_count(session_id: int, count: int):
    conn = _connect()
    conn.execute(
        "UPDATE scrape_sessions SET listings_found = ? WHERE id = ?",
        (count, session_id),
    )
    conn.commit()
    conn.close()


# ─── Properties ────────────────────────────────────────────────────────────────

def upsert_property(data: dict, session_id: int):
    """
    Insert a new property or update an existing one (matched by title + arrondissement).
    Records a price_history entry on insert or when the price changes.
    Returns (property_id, is_new).
    """
    conn = _connect()
    c = conn.cursor()
    now = datetime.datetime.now().isoformat()

    c.execute(
        "SELECT id, price FROM properties WHERE title = ? AND arrondissement = ?",
        (data.get("title", ""), data.get("arrondissement", "")),
    )
    row = c.fetchone()

    if row:
        prop_id = row["id"]
        old_price = row["price"]
        c.execute(
            "UPDATE properties SET last_seen = ?, session_id = ? WHERE id = ?",
            (now, session_id, prop_id),
        )
        # Track price change
        if old_price != data.get("price"):
            price_m2 = data["price"] / data["size"] if data.get("size") else 0
            c.execute(
                "UPDATE properties SET price = ?, price_per_m2 = ? WHERE id = ?",
                (data["price"], price_m2, prop_id),
            )
            c.execute(
                "INSERT INTO price_history (property_id, price, price_per_m2, recorded_at) "
                "VALUES (?, ?, ?, ?)",
                (prop_id, data["price"], price_m2, now),
            )
        conn.commit()
        conn.close()
        return prop_id, False  # existing
    else:
        price_m2 = data["price"] / data["size"] if data.get("size") else 0
        c.execute("""
            INSERT INTO properties
            (title, price, location, arrondissement, size, rooms, dpe,
             description, price_per_m2, url, first_seen, last_seen, session_id, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (
            data.get("title", ""),
            data.get("price", 0),
            "Lyon",
            data.get("arrondissement", ""),
            data.get("size", 0),
            data.get("rooms", 0),
            data.get("dpe", ""),
            data.get("description", ""),
            price_m2,
            data.get("url", ""),
            now, now, session_id,
        ))
        prop_id = c.lastrowid
        # Initial price snapshot
        c.execute(
            "INSERT INTO price_history (property_id, price, price_per_m2, recorded_at) "
            "VALUES (?, ?, ?, ?)",
            (prop_id, data.get("price", 0), price_m2, now),
        )
        conn.commit()
        conn.close()
        return prop_id, True  # new


def get_all_properties() -> list[dict]:
    """Return all active properties ordered by arrondissement."""
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM properties WHERE is_active = 1 ORDER BY arrondissement, price_per_m2"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_price_history(property_id: int) -> list[dict]:
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM price_history WHERE property_id = ? ORDER BY recorded_at",
        (property_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_session_count() -> int:
    conn = _connect()
    row = conn.execute("SELECT COUNT(*) as cnt FROM scrape_sessions").fetchone()
    conn.close()
    return row["cnt"]


def get_first_session_date():
    conn = _connect()
    row = conn.execute("SELECT MIN(timestamp) as ts FROM scrape_sessions").fetchone()
    conn.close()
    return row["ts"] if row else None


# ─── Analyses ──────────────────────────────────────────────────────────────────

def save_analysis(property_id: int, analysis: dict):
    """Save an analysis result (each run appends, enabling historical comparison)."""
    conn = _connect()
    now = datetime.datetime.now().isoformat()
    conn.execute("""
        INSERT INTO analyses (property_id, score, roi_5yr, is_undervalued, summary, analyzed_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        property_id,
        analysis.get("score", 0),
        analysis.get("roi_5yr", 0),
        1 if analysis.get("is_undervalued") else 0,
        analysis.get("summary", ""),
        now,
    ))
    conn.commit()
    conn.close()

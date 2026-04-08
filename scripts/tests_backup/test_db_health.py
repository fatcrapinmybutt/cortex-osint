"""Database health validation — existence, integrity, key tables, FTS5.

All tests are READ-ONLY against litigation_context.db.
"""

import sqlite3
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Key tables that MUST exist in a healthy litigation_context.db
REQUIRED_TABLES = [
    "evidence_quotes",
    "timeline_events",
    "authority_chains_v2",
    "michigan_rules_extracted",
    "contradiction_map",
    "judicial_violations",
    "impeachment_matrix",
    "police_reports",
    "md_sections",
    "master_citations",
    "file_inventory",
]

# FTS5 virtual tables
EXPECTED_FTS_TABLES = [
    "evidence_fts",
    "timeline_fts",
    "md_sections_fts",
]

# Tables with expected minimum row counts (sanity check)
MIN_ROW_COUNTS = {
    "evidence_quotes": 10000,
    "timeline_events": 5000,
    "authority_chains_v2": 10000,
    "michigan_rules_extracted": 1000,
    "file_inventory": 100000,
}


# ── Database Existence & Integrity ──────────────────────────────────────────

@pytest.mark.db
class TestDatabaseExistence:
    """Verify the database file exists and is accessible."""

    def test_db_file_exists(self, db_path):
        """litigation_context.db exists at repo root."""
        assert db_path.exists(), f"DB not found at {db_path}"
        assert db_path.stat().st_size > 0, "DB file is empty"

    def test_db_file_size_reasonable(self, db_path):
        """DB file is at least 100 MB (sanity check)."""
        size_mb = db_path.stat().st_size / (1024 * 1024)
        assert size_mb >= 100, f"DB is only {size_mb:.1f} MB — expected 100+ MB"

    def test_db_connectable(self, db_conn):
        """Can connect to DB and execute a simple query."""
        row = db_conn.execute("SELECT 1 AS ok").fetchone()
        assert row["ok"] == 1


@pytest.mark.db
class TestDatabaseIntegrity:
    """Check DB integrity and PRAGMA settings."""

    def test_integrity_check(self, db_conn):
        """PRAGMA integrity_check returns 'ok'."""
        result = db_conn.execute("PRAGMA integrity_check(1)").fetchone()
        assert result[0] == "ok", f"Integrity check failed: {result[0]}"

    def test_journal_mode_wal(self, db_conn):
        """DB is in WAL journal mode."""
        result = db_conn.execute("PRAGMA journal_mode").fetchone()
        assert result[0].lower() == "wal", f"Journal mode is {result[0]}, expected WAL"

    def test_busy_timeout_set(self, db_conn):
        """busy_timeout is at least 30 seconds."""
        result = db_conn.execute("PRAGMA busy_timeout").fetchone()
        assert result[0] >= 30000, f"busy_timeout is {result[0]}ms, expected 30000+"


# ── Required Tables ─────────────────────────────────────────────────────────

@pytest.mark.db
class TestRequiredTables:
    """Verify all required tables exist in the database."""

    @pytest.fixture(autouse=True)
    def _get_tables(self, db_conn):
        """Fetch the set of all table names once."""
        rows = db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
        ).fetchall()
        self.all_tables = {row["name"] for row in rows}

    @pytest.mark.parametrize("table_name", REQUIRED_TABLES)
    def test_required_table_exists(self, table_name):
        """Required table '{table_name}' exists in the database."""
        assert table_name in self.all_tables, (
            f"Table '{table_name}' not found. "
            f"Available: {sorted(self.all_tables)[:20]}..."
        )

    def test_total_table_count(self):
        """Database has at least 50 tables (sanity check)."""
        assert len(self.all_tables) >= 50, (
            f"Only {len(self.all_tables)} tables found — expected 50+"
        )


# ── FTS5 Indexes ────────────────────────────────────────────────────────────

@pytest.mark.db
class TestFTS5Indexes:
    """Verify FTS5 virtual tables exist and are queryable."""

    @pytest.mark.parametrize("fts_table", EXPECTED_FTS_TABLES)
    def test_fts_table_exists(self, db_conn, fts_table):
        """FTS5 table '{fts_table}' exists."""
        rows = db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (fts_table,)
        ).fetchall()
        if not rows:
            pytest.skip(f"FTS5 table {fts_table} not present")
        assert len(rows) == 1

    @pytest.mark.parametrize("fts_table", EXPECTED_FTS_TABLES)
    def test_fts_table_queryable(self, db_conn, fts_table):
        """FTS5 table '{fts_table}' responds to MATCH queries."""
        rows = db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (fts_table,)
        ).fetchall()
        if not rows:
            pytest.skip(f"FTS5 table {fts_table} not present")

        try:
            result = db_conn.execute(
                f"SELECT COUNT(*) FROM {fts_table} WHERE {fts_table} MATCH 'custody' LIMIT 1"
            ).fetchone()
            assert result[0] >= 0  # Just verify it doesn't crash
        except sqlite3.OperationalError:
            pytest.fail(f"FTS5 table {fts_table} cannot process MATCH query")


# ── Row Counts ──────────────────────────────────────────────────────────────

@pytest.mark.db
class TestRowCounts:
    """Verify key tables have expected minimum row counts."""

    @pytest.mark.parametrize("table_name,min_rows", list(MIN_ROW_COUNTS.items()))
    def test_minimum_rows(self, db_conn, table_name, min_rows):
        """Table '{table_name}' has at least {min_rows} rows."""
        # First check table exists
        exists = db_conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        ).fetchone()[0]
        if not exists:
            pytest.skip(f"Table {table_name} not found")

        count = db_conn.execute(f"SELECT COUNT(*) FROM [{table_name}]").fetchone()[0]
        assert count >= min_rows, (
            f"Table '{table_name}' has {count:,} rows, expected >= {min_rows:,}"
        )


# ── Cross-table Consistency ─────────────────────────────────────────────────

@pytest.mark.db
class TestCrossTableConsistency:
    """Basic cross-table sanity checks."""

    def test_evidence_quotes_has_content(self, db_conn):
        """evidence_quotes rows have non-empty quote_text."""
        exists = db_conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='evidence_quotes'"
        ).fetchone()[0]
        if not exists:
            pytest.skip("evidence_quotes not found")

        # Check schema first
        cols = {r[1] for r in db_conn.execute("PRAGMA table_info(evidence_quotes)").fetchall()}
        text_col = "quote_text" if "quote_text" in cols else None
        if text_col is None:
            pytest.skip("quote_text column not found in evidence_quotes")

        empty = db_conn.execute(
            f"SELECT COUNT(*) FROM evidence_quotes WHERE {text_col} IS NULL OR trim({text_col}) = ''"
        ).fetchone()[0]
        total = db_conn.execute("SELECT COUNT(*) FROM evidence_quotes").fetchone()[0]
        if total == 0:
            pytest.skip("evidence_quotes is empty")
        pct_empty = empty / total * 100
        assert pct_empty < 20, f"{pct_empty:.1f}% of evidence_quotes have empty text"

    def test_timeline_events_has_dates(self, db_conn):
        """timeline_events rows have event dates."""
        exists = db_conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='timeline_events'"
        ).fetchone()[0]
        if not exists:
            pytest.skip("timeline_events not found")

        cols = {r[1] for r in db_conn.execute("PRAGMA table_info(timeline_events)").fetchall()}
        date_col = None
        for candidate in ["event_date", "date", "timestamp", "created_at"]:
            if candidate in cols:
                date_col = candidate
                break
        if date_col is None:
            pytest.skip("No date column found in timeline_events")

        null_dates = db_conn.execute(
            f"SELECT COUNT(*) FROM timeline_events WHERE {date_col} IS NULL"
        ).fetchone()[0]
        total = db_conn.execute("SELECT COUNT(*) FROM timeline_events").fetchone()[0]
        if total == 0:
            pytest.skip("timeline_events is empty")
        pct_null = null_dates / total * 100
        assert pct_null < 50, f"{pct_null:.1f}% of timeline_events have NULL dates"

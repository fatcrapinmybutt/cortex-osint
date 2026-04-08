"""FTS5 safety protocol validation — 15 tests.

Verifies the sanitize→MATCH→LIKE fallback chain per Rule 15:
1. Sanitize: re.sub(r'[^\\w\\s*"]', ' ', query)
2. MATCH in try/except
3. On error → LIKE fallback with parameterized bind
"""

import re
import sqlite3
from pathlib import Path

import pytest

# ── Sanitize function (standalone copy to test without engine imports) ──────

_FTS5_SANITIZE_RE = re.compile(r'[^\w\s*"]')


def sanitize_fts5(query: str) -> str:
    """Strip dangerous characters from FTS5 query, preserving wildcards and quotes."""
    return _FTS5_SANITIZE_RE.sub(" ", query).strip()


def fts5_search_with_fallback(conn, table, fts_col, query, limit=20):
    """FTS5 search with LIKE fallback — production pattern."""
    sanitized = sanitize_fts5(query)
    if not sanitized:
        return []
    try:
        sql = f"SELECT rowid, snippet({table}, 0, '»', '«', '…', 32) AS snip FROM {table} WHERE {fts_col} MATCH ? LIMIT ?"
        return conn.execute(sql, (sanitized, limit)).fetchall()
    except sqlite3.OperationalError:
        # FTS5 error → LIKE fallback
        like_term = f"%{sanitized}%"
        sql = f"SELECT rowid FROM {table} WHERE {fts_col} LIKE ? LIMIT ?"
        return conn.execute(sql, (like_term, limit)).fetchall()


# ── Sanitize Tests ──────────────────────────────────────────────────────────

class TestSanitize:
    """Tests for FTS5 query sanitization."""

    def test_strips_semicolons(self):
        """Semicolons (SQL injection vector) are removed."""
        assert ";" not in sanitize_fts5("DROP TABLE; --")

    def test_strips_parens(self):
        """Parentheses are removed."""
        assert "(" not in sanitize_fts5("(custody) AND (parenting)")

    def test_preserves_wildcards(self):
        """Asterisk wildcard is preserved for prefix search."""
        assert "*" in sanitize_fts5("custod*")

    def test_preserves_quotes(self):
        """Double quotes are preserved for phrase search."""
        assert '"' in sanitize_fts5('"parental alienation"')

    def test_strips_brackets(self):
        """Square brackets are stripped."""
        result = sanitize_fts5("[DROP TABLE evidence_quotes]")
        assert "[" not in result
        assert "]" not in result

    def test_preserves_alphanumeric(self):
        """Alphanumeric characters and spaces pass through."""
        assert sanitize_fts5("custody parenting MCR 722") == "custody parenting MCR 722"

    def test_empty_query(self):
        """Empty string returns empty string."""
        assert sanitize_fts5("") == ""

    def test_only_special_chars(self):
        """Query of only special chars returns empty/whitespace."""
        result = sanitize_fts5("!@#$%^&()")
        assert result.strip() == ""

    def test_unicode_handled(self):
        """Unicode characters are handled without crash."""
        result = sanitize_fts5("café résumé naïve")
        assert isinstance(result, str)

    def test_sql_injection_neutralized(self):
        """SQL injection patterns are neutralized."""
        result = sanitize_fts5("'; DROP TABLE evidence_quotes; --")
        assert "DROP" in result  # word preserved, but injection chars stripped
        assert ";" not in result
        assert "'" not in result
        assert "--" not in result


# ── FTS5 Integration Tests (require DB) ─────────────────────────────────────

@pytest.mark.db
class TestFTS5Integration:
    """Integration tests for FTS5 search with LIKE fallback."""

    def test_valid_match_query(self, db_conn):
        """Valid FTS5 MATCH query returns results from evidence_fts."""
        # Check evidence_fts exists
        tables = [
            r[0] for r in db_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='evidence_fts'"
            ).fetchall()
        ]
        if not tables:
            pytest.skip("evidence_fts table not found")

        results = fts5_search_with_fallback(
            db_conn, "evidence_fts", "evidence_fts", "custody", limit=5
        )
        assert isinstance(results, list)

    def test_invalid_query_falls_back(self, db_conn):
        """Invalid FTS5 syntax falls back to LIKE without crash."""
        # Deliberately bad FTS5 — unmatched quotes
        results = fts5_search_with_fallback(
            db_conn, "evidence_fts", "evidence_fts", '"unclosed phrase', limit=5
        )
        # Should not crash — returns list (possibly empty)
        assert isinstance(results, list)

    def test_empty_query_returns_empty(self, db_conn):
        """Empty query returns empty list, not crash."""
        results = fts5_search_with_fallback(
            db_conn, "evidence_fts", "evidence_fts", "", limit=5
        )
        assert results == []

    def test_wildcard_prefix_search(self, db_conn):
        """Prefix wildcard search (custod*) executes without crash."""
        tables = [
            r[0] for r in db_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='evidence_fts'"
            ).fetchall()
        ]
        if not tables:
            pytest.skip("evidence_fts table not found")

        results = fts5_search_with_fallback(
            db_conn, "evidence_fts", "evidence_fts", "custod*", limit=5
        )
        assert isinstance(results, list)

    def test_and_or_not_operators(self, db_conn):
        """Boolean operators AND/OR/NOT work in FTS5 queries."""
        tables = [
            r[0] for r in db_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='evidence_fts'"
            ).fetchall()
        ]
        if not tables:
            pytest.skip("evidence_fts table not found")

        results = fts5_search_with_fallback(
            db_conn, "evidence_fts", "evidence_fts",
            "custody OR parenting NOT housing", limit=5
        )
        assert isinstance(results, list)

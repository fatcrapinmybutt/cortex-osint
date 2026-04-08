"""
LitigationOS DuckDB Analytics Engine
High-performance analytical queries using DuckDB's columnar engine.
Reads from SQLite (litigation_context.db) via DuckDB's SQLite scanner.
"""

__all__ = [
    "get_analytics_connection",
    "AnalyticsEngine",
    "quick_query",
]

import os
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import duckdb

DB_PATH = Path(__file__).parent.parent.parent.parent / "litigation_context.db"


def get_analytics_connection(
    db_path: Optional[str] = None,
    read_only: bool = True,
) -> duckdb.DuckDBPyConnection:
    """Create a DuckDB connection with SQLite attached.

    DuckDB reads SQLite via its scanner extension (10-100x faster for
    analytical queries like GROUP BY, window functions, cross-table joins).
    """
    conn = duckdb.connect(":memory:")
    conn.execute("INSTALL sqlite; LOAD sqlite;")
    conn.execute("SET sqlite_all_varchar = true;")

    path = db_path or str(DB_PATH)
    mode = "READ_ONLY" if read_only else "READ_WRITE"
    conn.execute(f"ATTACH '{path}' AS lit (TYPE SQLITE, {mode});")
    return conn


class AnalyticsEngine:
    """High-performance analytics over litigation_context.db via DuckDB."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(DB_PATH)
        self._conn: Optional[duckdb.DuckDBPyConnection] = None

    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            self._conn = get_analytics_connection(self.db_path)
        return self._conn

    def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def evidence_heatmap(self) -> list[dict]:
        """Evidence density by lane and category — which areas are strongest/weakest."""
        rows = self.conn.execute("""
            SELECT
                COALESCE(lane, 'UNASSIGNED') as lane,
                COALESCE(category, 'uncategorized') as category,
                COUNT(*) as count,
                COUNT(DISTINCT source_file) as sources
            FROM lit.evidence_quotes
            GROUP BY lane, category
            ORDER BY count DESC
        """).fetchall()
        return [
            {"lane": r[0], "category": r[1], "count": int(r[2]), "sources": int(r[3])}
            for r in rows
        ]

    def authority_coverage(self) -> list[dict]:
        """Authority chain coverage by lane — where are citation gaps."""
        rows = self.conn.execute("""
            SELECT
                COALESCE(lane, 'NONE') as lane,
                COUNT(*) as chains,
                COUNT(DISTINCT primary_citation) as unique_primary,
                COUNT(DISTINCT supporting_citation) as unique_supporting
            FROM lit.authority_chains_v2
            GROUP BY lane
            ORDER BY chains DESC
        """).fetchall()
        return [
            {
                "lane": r[0],
                "chains": int(r[1]),
                "unique_primary": int(r[2]),
                "unique_supporting": int(r[3]),
            }
            for r in rows
        ]

    def timeline_density(self, bucket: str = "month") -> list[dict]:
        """Timeline event density by time period.

        Args:
            bucket: "day", "month", or "year"
        """
        fmt = {"day": "%Y-%m-%d", "month": "%Y-%m", "year": "%Y"}.get(bucket, "%Y-%m")
        rows = self.conn.execute(f"""
            SELECT
                strftime(CAST(event_date AS VARCHAR), '{fmt}') as period,
                COUNT(*) as events
            FROM lit.timeline_events
            WHERE event_date IS NOT NULL AND CAST(event_date AS VARCHAR) != ''
            GROUP BY period
            ORDER BY period
        """).fetchall()
        return [{"period": r[0], "events": int(r[1])} for r in rows]

    def impeachment_arsenal(self, target: Optional[str] = None) -> list[dict]:
        """Impeachment ammunition summary by target person."""
        where = ""
        params = []
        if target:
            where = "WHERE LOWER(CAST(category AS VARCHAR)) LIKE LOWER('%' || ? || '%')"
            params = [target]

        rows = self.conn.execute(f"""
            SELECT
                COALESCE(category, 'unknown') as target,
                COUNT(*) as total,
                AVG(CAST(impeachment_value AS DOUBLE)) as avg_value,
                MAX(CAST(impeachment_value AS INTEGER)) as max_value,
                COUNT(DISTINCT source_file) as sources
            FROM lit.impeachment_matrix
            {where}
            GROUP BY category
            ORDER BY total DESC
        """, params).fetchall()
        return [
            {
                "target": r[0],
                "total": int(r[1]),
                "avg_value": round(float(r[2] or 0), 1),
                "max_value": int(r[3] or 0),
                "sources": int(r[4]),
            }
            for r in rows
        ]

    def filing_readiness_matrix(self) -> list[dict]:
        """Cross-join filing packages with evidence/authority/impeachment counts."""
        rows = self.conn.execute("""
            WITH packages AS (
                SELECT DISTINCT lane FROM lit.filing_packages
            ),
            ev_counts AS (
                SELECT lane, COUNT(*) as evidence_count
                FROM lit.evidence_quotes
                WHERE lane IS NOT NULL
                GROUP BY lane
            ),
            auth_counts AS (
                SELECT lane, COUNT(*) as authority_count
                FROM lit.authority_chains_v2
                WHERE lane IS NOT NULL
                GROUP BY lane
            )
            SELECT
                p.lane,
                COALESCE(e.evidence_count, 0) as evidence,
                COALESCE(a.authority_count, 0) as authorities
            FROM packages p
            LEFT JOIN ev_counts e ON p.lane = e.lane
            LEFT JOIN auth_counts a ON p.lane = a.lane
            ORDER BY p.lane
        """).fetchall()
        return [
            {"lane": r[0], "evidence": int(r[1]), "authorities": int(r[2])}
            for r in rows
        ]

    def contradiction_network(self, min_severity: str = "medium") -> list[dict]:
        """Contradiction map summary — who contradicts whom about what."""
        severity_order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        min_level = severity_order.get(min_severity, 2)

        rows = self.conn.execute("""
            SELECT
                source_a, source_b, severity,
                COUNT(*) as contradictions,
                GROUP_CONCAT(DISTINCT lane) as lanes
            FROM lit.contradiction_map
            GROUP BY source_a, source_b, severity
            ORDER BY contradictions DESC
        """).fetchall()

        return [
            {
                "source_a": r[0],
                "source_b": r[1],
                "severity": r[2],
                "count": int(r[3]),
                "lanes": r[4],
            }
            for r in rows
            if severity_order.get(str(r[2]).lower(), 0) >= min_level
        ]

    def separation_counter(self) -> dict:
        """Dynamic separation day counter with harm metrics."""
        anchor = date(2025, 7, 29)
        days = (date.today() - anchor).days
        return {
            "last_contact": "2025-07-29",
            "days_separated": days,
            "weeks": days // 7,
            "months_approx": round(days / 30.44, 1),
            "constitutional_harm": "Ongoing deprivation of fundamental parental right",
            "authority": "Troxel v. Granville, 530 U.S. 57 (2000)",
        }

    def full_dashboard(self) -> dict:
        """Complete litigation dashboard — all metrics in one call."""
        return {
            "separation": self.separation_counter(),
            "evidence_by_lane": self.evidence_heatmap()[:20],
            "authority_coverage": self.authority_coverage(),
            "impeachment_summary": self.impeachment_arsenal(),
            "timestamp": datetime.now().isoformat(),
        }


def quick_query(sql: str, params: list = None) -> list[dict]:
    """One-shot analytical query against litigation_context.db via DuckDB."""
    conn = get_analytics_connection()
    try:
        result = conn.execute(sql, params or [])
        cols = [desc[0] for desc in result.description]
        return [dict(zip(cols, row)) for row in result.fetchall()]
    finally:
        conn.close()

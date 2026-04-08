"""FORTRESS Anomaly Detector — Row count delta analysis and trend tracking.

Compares current database row counts against stored baselines to detect
unexpected drops (data loss) or spikes (runaway inserts). Saves snapshots
for multi-day trend analysis.
"""

import os
import sqlite3
import logging
from dataclasses import dataclass
from typing import Optional

from .health import _open_connection, _is_exfat, BASELINE_DDL

logger = logging.getLogger(__name__)

SNAPSHOT_DDL = """
CREATE TABLE IF NOT EXISTS db_health_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_time TEXT NOT NULL DEFAULT (datetime('now')),
    table_name TEXT NOT NULL,
    row_count INTEGER NOT NULL
);
"""


@dataclass
class Anomaly:
    """A detected deviation from baseline row counts."""

    table: str
    expected: int
    actual: int
    severity: str  # INFO, WARN, CRITICAL
    message: str


class AnomalyDetector:
    """Detect row count anomalies by comparing current state to baseline."""

    def __init__(self, db_path: str) -> None:
        self.db_path = os.path.abspath(db_path)
        self.exfat = _is_exfat(self.db_path)
        self.baseline: dict[str, int] = {}
        self._ensure_tables()
        self._load_baseline()

    def _conn(self) -> sqlite3.Connection:
        return _open_connection(self.db_path, exfat=self.exfat)

    def _ensure_tables(self) -> None:
        conn = self._conn()
        try:
            conn.executescript(BASELINE_DDL + SNAPSHOT_DDL)
            conn.commit()
        finally:
            conn.close()

    def _load_baseline(self) -> None:
        """Load baseline row counts from db_health_baseline."""
        conn = self._conn()
        try:
            exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='db_health_baseline'"
            ).fetchone()
            if not exists:
                return
            for row in conn.execute(
                "SELECT table_name, row_count FROM db_health_baseline"
            ).fetchall():
                self.baseline[row[0]] = row[1]
        finally:
            conn.close()

    def detect(self, current_counts: dict[str, int]) -> list[Anomaly]:
        """Compare current counts to baseline and return anomalies."""
        anomalies: list[Anomaly] = []

        for table, actual in current_counts.items():
            expected = self.baseline.get(table)
            if expected is None:
                # New table, no baseline yet — informational only
                anomalies.append(Anomaly(
                    table=table,
                    expected=0,
                    actual=actual,
                    severity="INFO",
                    message=f"New table '{table}' with {actual:,} rows (no baseline)",
                ))
                continue

            if expected == 0:
                # Baseline is zero — growth is expected, only flag extreme
                if actual > 100000:
                    anomalies.append(Anomaly(
                        table=table,
                        expected=0,
                        actual=actual,
                        severity="WARN",
                        message=f"'{table}' grew from 0 to {actual:,} rows",
                    ))
                continue

            ratio = actual / expected
            pct_change = abs(ratio - 1.0) * 100

            if ratio < 0.1:
                # >90% drop — critical data loss signal
                anomalies.append(Anomaly(
                    table=table,
                    expected=expected,
                    actual=actual,
                    severity="CRITICAL",
                    message=f"'{table}' dropped {pct_change:.0f}%: {expected:,} → {actual:,}",
                ))
            elif ratio < 0.5:
                # >50% drop — warning
                anomalies.append(Anomaly(
                    table=table,
                    expected=expected,
                    actual=actual,
                    severity="WARN",
                    message=f"'{table}' dropped {pct_change:.0f}%: {expected:,} → {actual:,}",
                ))
            elif ratio > 4.0:
                # >300% growth — critical runaway
                anomalies.append(Anomaly(
                    table=table,
                    expected=expected,
                    actual=actual,
                    severity="CRITICAL",
                    message=f"'{table}' grew {pct_change:.0f}%: {expected:,} → {actual:,}",
                ))
            elif ratio > 2.0:
                # >100% growth — warning
                anomalies.append(Anomaly(
                    table=table,
                    expected=expected,
                    actual=actual,
                    severity="WARN",
                    message=f"'{table}' grew {pct_change:.0f}%: {expected:,} → {actual:,}",
                ))
            elif ratio > 1.5 or ratio < 0.9:
                # Moderate change — informational
                direction = "grew" if ratio > 1 else "dropped"
                anomalies.append(Anomaly(
                    table=table,
                    expected=expected,
                    actual=actual,
                    severity="INFO",
                    message=f"'{table}' {direction} {pct_change:.0f}%: {expected:,} → {actual:,}",
                ))

        return anomalies

    def save_snapshot(self, current_counts: dict[str, int]) -> int:
        """Save current row counts as a timestamped snapshot for trend analysis."""
        conn = self._conn()
        try:
            conn.executescript(SNAPSHOT_DDL)
            params = [(tbl, cnt) for tbl, cnt in current_counts.items()]
            conn.executemany(
                "INSERT INTO db_health_snapshots (table_name, row_count) VALUES (?, ?)",
                params,
            )
            conn.commit()
            return len(params)
        finally:
            conn.close()

    def get_trend(self, table_name: str, days: int = 7) -> list[dict]:
        """Return row count trend for a table over the last N days."""
        conn = self._conn()
        try:
            exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='db_health_snapshots'"
            ).fetchone()
            if not exists:
                return []

            rows = conn.execute(
                "SELECT snapshot_time, row_count FROM db_health_snapshots "
                "WHERE table_name = ? AND snapshot_time >= datetime('now', ?) "
                "ORDER BY snapshot_time ASC",
                (table_name, f"-{days} days"),
            ).fetchall()
            return [{"time": r[0], "count": r[1]} for r in rows]
        finally:
            conn.close()

    def update_baseline(self, current_counts: dict[str, int]) -> int:
        """Update baseline with current counts (call after confirming healthy state)."""
        conn = self._conn()
        try:
            conn.executescript(BASELINE_DDL)
            params = [(tbl, cnt) for tbl, cnt in current_counts.items()]
            conn.executemany(
                "INSERT OR REPLACE INTO db_health_baseline "
                "(table_name, row_count, last_updated, last_verified) "
                "VALUES (?, ?, datetime('now'), datetime('now'))",
                params,
            )
            conn.commit()
            return len(params)
        finally:
            conn.close()

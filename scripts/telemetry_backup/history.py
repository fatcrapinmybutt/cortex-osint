"""Telemetry history — track system metrics over time for trend analysis."""
import sqlite3
import json
from datetime import datetime

DB_PATH = r"C:\Users\andre\LitigationOS\litigation_context.db"


class TelemetryHistory:
    """Stores and retrieves telemetry snapshots for historical trend analysis."""

    def __init__(self, db_path=None):
        self._conn = None
        self._db_path = db_path or DB_PATH

    @property
    def conn(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path)
            self._conn.execute("PRAGMA busy_timeout=60000")
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA cache_size=-32000")
            self._ensure_table()
        return self._conn

    def _ensure_table(self):
        """Create the telemetry_snapshots table if it does not exist."""
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS telemetry_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                separation_days INTEGER,
                cpu_percent REAL,
                memory_percent REAL,
                disk_c_free_gb REAL,
                db_size_mb REAL,
                wal_size_mb REAL,
                evidence_count INTEGER,
                authority_count INTEGER,
                timeline_count INTEGER,
                snapshot_json TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """
        )
        self.conn.commit()

    def store(self, snapshot):
        """Store a telemetry snapshot.

        Args:
            snapshot: Dict from TelemetryEngine.collect_snapshot().

        Returns:
            The rowid of the inserted record.
        """
        sys_m = snapshot.get("system", {})
        db_m = snapshot.get("database", {})
        cursor = self.conn.execute(
            """
            INSERT INTO telemetry_snapshots
            (timestamp, separation_days, cpu_percent, memory_percent, disk_c_free_gb,
             db_size_mb, wal_size_mb, evidence_count, authority_count, timeline_count,
             snapshot_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                snapshot.get("timestamp"),
                snapshot.get("separation_days"),
                sys_m.get("cpu_percent"),
                sys_m.get("memory_percent"),
                sys_m.get("disk_c_free_gb"),
                db_m.get("db_size_mb"),
                db_m.get("wal_size_mb"),
                db_m.get("evidence_quotes"),
                db_m.get("authority_chains"),
                db_m.get("timeline_events"),
                json.dumps(snapshot),
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_trend(self, limit=50):
        """Get recent telemetry trends.

        Args:
            limit: Maximum number of records to return.

        Returns:
            List of tuples with trend data (most recent first).
        """
        return self.conn.execute(
            """
            SELECT timestamp, separation_days, cpu_percent, memory_percent,
                   disk_c_free_gb, db_size_mb, evidence_count
            FROM telemetry_snapshots
            ORDER BY created_at DESC LIMIT ?
        """,
            (limit,),
        ).fetchall()

    def get_latest(self):
        """Get the most recent snapshot as a dict, or None."""
        row = self.conn.execute(
            "SELECT snapshot_json FROM telemetry_snapshots "
            "ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        if row and row[0]:
            return json.loads(row[0])
        return None

    def count(self):
        """Return total number of stored snapshots."""
        return self.conn.execute(
            "SELECT COUNT(*) FROM telemetry_snapshots"
        ).fetchone()[0]

    def close(self):
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

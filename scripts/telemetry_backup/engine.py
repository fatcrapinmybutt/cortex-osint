"""System Telemetry Engine — real-time health metrics for LitigationOS."""
import sqlite3
import os
import json
import time
import psutil
from datetime import datetime, date
from pathlib import Path
from collections import defaultdict

DB_PATH = r"C:\Users\andre\LitigationOS\litigation_context.db"


class TelemetryEngine:
    """Collects real-time system health metrics for LitigationOS."""

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
        return self._conn

    def close(self):
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def collect_snapshot(self):
        """Collect a full system telemetry snapshot."""
        return {
            "timestamp": datetime.now().isoformat(),
            "separation_days": (date.today() - date(2025, 7, 29)).days,
            "system": self._system_metrics(),
            "database": self._database_metrics(),
            "evidence": self._evidence_metrics(),
            "filing": self._filing_metrics(),
            "engines": self._engine_metrics(),
        }

    def _system_metrics(self):
        """CPU, memory, disk usage."""
        vm = psutil.virtual_memory()
        disk_c = psutil.disk_usage("C:\\")
        metrics = {
            "cpu_percent": psutil.cpu_percent(interval=0.5),
            "memory_used_gb": round(vm.used / (1024**3), 2),
            "memory_total_gb": round(vm.total / (1024**3), 2),
            "memory_percent": vm.percent,
            "disk_c_free_gb": round(disk_c.free / (1024**3), 2),
            "disk_c_percent": disk_c.percent,
        }

        # Collect additional drive info when available
        for letter in ["D", "F", "G", "I", "J"]:
            try:
                usage = psutil.disk_usage(f"{letter}:\\")
                metrics[f"disk_{letter.lower()}_free_gb"] = round(
                    usage.free / (1024**3), 2
                )
            except (FileNotFoundError, OSError):
                pass

        return metrics

    def _database_metrics(self):
        """DB size, WAL size, key table row counts."""
        db_size = 0
        if os.path.exists(self._db_path):
            db_size = os.path.getsize(self._db_path) / (1024**2)

        wal_path = self._db_path + "-wal"
        wal_size = 0
        if os.path.exists(wal_path):
            wal_size = os.path.getsize(wal_path) / (1024**2)

        # Single consolidated query for all key table counts
        try:
            row = self.conn.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM evidence_quotes) AS eq,
                    (SELECT COUNT(*) FROM authority_chains_v2) AS ac,
                    (SELECT COUNT(*) FROM timeline_events) AS te,
                    (SELECT COUNT(*) FROM impeachment_matrix) AS im,
                    (SELECT COUNT(*) FROM contradiction_map) AS cm,
                    (SELECT COUNT(*) FROM judicial_violations) AS jv
            """
            ).fetchone()
        except sqlite3.OperationalError:
            row = (0, 0, 0, 0, 0, 0)

        # Count total tables
        table_count = self.conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]

        return {
            "db_size_mb": round(db_size, 1),
            "wal_size_mb": round(wal_size, 1),
            "table_count": table_count,
            "evidence_quotes": row[0],
            "authority_chains": row[1],
            "timeline_events": row[2],
            "impeachment_matrix": row[3],
            "contradictions": row[4],
            "judicial_violations": row[5],
        }

    def _evidence_metrics(self):
        """Evidence coverage by lane and category."""
        try:
            lanes = self.conn.execute(
                "SELECT lane, COUNT(*) FROM evidence_quotes "
                "WHERE lane IS NOT NULL AND lane != '' "
                "GROUP BY lane ORDER BY COUNT(*) DESC LIMIT 10"
            ).fetchall()
        except sqlite3.OperationalError:
            lanes = []

        try:
            categories = self.conn.execute(
                "SELECT category, COUNT(*) FROM evidence_quotes "
                "WHERE category IS NOT NULL AND category != '' "
                "GROUP BY category ORDER BY COUNT(*) DESC LIMIT 10"
            ).fetchall()
        except sqlite3.OperationalError:
            categories = []

        return {
            "by_lane": dict(lanes),
            "by_category": dict(categories),
        }

    def _filing_metrics(self):
        """Filing package status and deadlines."""
        filings = []
        deadlines = []

        # Adaptive: check what columns exist in filing_packages
        try:
            cols = {
                r[1]
                for r in self.conn.execute(
                    "PRAGMA table_info(filing_packages)"
                ).fetchall()
            }
            if cols:
                id_col = "filing_id" if "filing_id" in cols else "id"
                title_col = "title" if "title" in cols else "name"
                status_col = "status" if "status" in cols else "phase"
                select_cols = []
                for c in [id_col, title_col, status_col]:
                    if c in cols:
                        select_cols.append(c)
                    else:
                        select_cols.append(f"NULL AS {c}")
                filings = self.conn.execute(
                    f"SELECT {', '.join(select_cols)} FROM filing_packages"
                ).fetchall()
        except sqlite3.OperationalError:
            pass

        try:
            cols = {
                r[1]
                for r in self.conn.execute(
                    "PRAGMA table_info(deadlines)"
                ).fetchall()
            }
            if cols:
                title_col = "title" if "title" in cols else "description"
                due_col = "due_date" if "due_date" in cols else "deadline"
                status_col = "status" if "status" in cols else "'pending'"
                deadlines = self.conn.execute(
                    f"SELECT {title_col}, {due_col}, {status_col} "
                    f"FROM deadlines ORDER BY {due_col} LIMIT 5"
                ).fetchall()
        except sqlite3.OperationalError:
            pass

        return {
            "total_filings": len(filings),
            "filings": [
                {"id": f[0], "title": f[1], "status": f[2]} for f in filings
            ],
            "upcoming_deadlines": [
                {"title": d[0], "due": d[1], "status": d[2]} for d in deadlines
            ],
        }

    def _engine_metrics(self):
        """Check which engines exist and have __init__.py."""
        engine_dir = Path(r"C:\Users\andre\LitigationOS\00_SYSTEM\engines")
        engines = {}
        if engine_dir.exists():
            for d in sorted(engine_dir.iterdir()):
                if d.is_dir() and not d.name.startswith(("_", ".")):
                    has_init = (d / "__init__.py").exists()
                    if has_init:
                        engines[d.name] = {"exists": True, "has_init": True}
        return {"count": len(engines), "engines": engines}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

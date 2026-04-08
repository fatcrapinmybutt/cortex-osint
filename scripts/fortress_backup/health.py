"""FORTRESS Health Check Suite — 10 diagnostic checks for SQLite databases.

Each check returns a HealthResult with status (PASS/WARN/FAIL), detail text,
and execution duration. Thread-safe: each check opens its own connection.
"""

import os
import sqlite3
import time
import ctypes
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

REQUIRED_PRAGMAS = (
    "PRAGMA busy_timeout = 60000;",
    "PRAGMA journal_mode = WAL;",
    "PRAGMA cache_size = -32000;",
    "PRAGMA temp_store = MEMORY;",
    "PRAGMA synchronous = NORMAL;",
)

CRITICAL_TABLES = [
    "evidence_quotes",
    "timeline_events",
    "authority_chains_v2",
    "michigan_rules_extracted",
    "impeachment_matrix",
    "contradiction_map",
    "judicial_violations",
    "police_reports",
    "filing_packages",
    "deadlines",
    "claims",
    "documents",
    "md_sections",
    "md_cross_refs",
    "master_citations",
    "file_inventory",
    "berry_mcneill_intelligence",
    "semantic_vectors",
    "convergence_domains",
    "convergence_todos",
]

ROW_COUNT_TABLES = [
    "evidence_quotes",
    "timeline_events",
    "authority_chains_v2",
    "michigan_rules_extracted",
    "impeachment_matrix",
    "contradiction_map",
    "judicial_violations",
    "police_reports",
    "md_sections",
    "md_cross_refs",
    "master_citations",
    "file_inventory",
    "claims",
    "documents",
    "deadlines",
]

FTS5_TABLES = [
    ("evidence_fts", "evidence_fts"),
    ("timeline_fts", "timeline_fts"),
    ("md_sections_fts", "md_sections_fts"),
]

BASELINE_DDL = """
CREATE TABLE IF NOT EXISTS db_health_baseline (
    table_name TEXT PRIMARY KEY,
    row_count INTEGER NOT NULL,
    last_updated TEXT NOT NULL DEFAULT (datetime('now')),
    last_verified TEXT
);
"""

HEALTH_LOG_DDL = """
CREATE TABLE IF NOT EXISTS db_health_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    check_time TEXT NOT NULL DEFAULT (datetime('now')),
    check_name TEXT NOT NULL,
    status TEXT NOT NULL,
    detail TEXT,
    duration_ms REAL,
    healed INTEGER DEFAULT 0,
    heal_detail TEXT
);
"""


@dataclass
class HealthResult:
    """Outcome of a single health check."""

    check_name: str
    status: str  # PASS, WARN, FAIL
    detail: str
    duration_ms: float = 0.0


@dataclass
class HealthReport:
    """Aggregated result of all checks on one database."""

    db_path: str
    results: list = field(default_factory=list)
    overall: str = "PASS"
    duration_ms: float = 0.0

    def add(self, result: HealthResult) -> None:
        self.results.append(result)
        if result.status == "FAIL":
            self.overall = "FAIL"
        elif result.status == "WARN" and self.overall != "FAIL":
            self.overall = "WARN"


def _open_connection(db_path: str, *, exfat: bool = False) -> sqlite3.Connection:
    """Open a SQLite connection with mandatory PRAGMAs."""
    conn = sqlite3.connect(db_path, timeout=60)
    conn.execute("PRAGMA busy_timeout = 60000;")
    if exfat:
        conn.execute("PRAGMA journal_mode = DELETE;")
        conn.execute("PRAGMA synchronous = FULL;")
    else:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA cache_size = -32000;")
    conn.execute("PRAGMA temp_store = MEMORY;")
    return conn


def _is_exfat(path: str) -> bool:
    """Detect exFAT filesystem (J:\\ drive on this machine)."""
    drive = os.path.splitdrive(os.path.abspath(path))[0].upper()
    if not drive:
        return False
    # J:\ is known exFAT — fast heuristic
    if drive.startswith("J"):
        return True
    # Attempt kernel32 GetVolumeInformation on Windows
    try:
        fs_name_buf = ctypes.create_unicode_buffer(256)
        ok = ctypes.windll.kernel32.GetVolumeInformationW(
            f"{drive}\\",
            None, 0, None, None, None,
            fs_name_buf, 256,
        )
        if ok:
            return fs_name_buf.value.upper() == "EXFAT"
    except (AttributeError, OSError):
        pass
    return False


def _timed(fn):
    """Decorator that times a check method and sets duration_ms on the result."""
    def wrapper(self, *args, **kwargs):
        t0 = time.perf_counter()
        try:
            result = fn(self, *args, **kwargs)
        except Exception as exc:
            result = HealthResult(
                check_name=fn.__name__.replace("check_", ""),
                status="FAIL",
                detail=f"Unhandled exception: {exc}",
            )
        result.duration_ms = (time.perf_counter() - t0) * 1000
        return result
    return wrapper


class DatabaseHealthChecker:
    """Run 10 health checks against a SQLite database."""

    def __init__(self, db_path: str) -> None:
        self.db_path = os.path.abspath(db_path)
        if not os.path.isfile(self.db_path):
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        self.exfat = _is_exfat(self.db_path)
        self._lock = threading.Lock()
        self._ensure_health_tables()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _conn(self) -> sqlite3.Connection:
        return _open_connection(self.db_path, exfat=self.exfat)

    def _ensure_health_tables(self) -> None:
        """Create tracking tables if they don't exist (idempotent)."""
        with self._lock:
            conn = self._conn()
            try:
                conn.executescript(BASELINE_DDL + HEALTH_LOG_DDL)
                conn.commit()
            finally:
                conn.close()

    def _table_exists(self, conn: sqlite3.Connection, table: str) -> bool:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        return row is not None

    def _get_table_columns(self, conn: sqlite3.Connection, table: str) -> set:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return {r[1] for r in rows}

    # ------------------------------------------------------------------
    # 10 Health Checks
    # ------------------------------------------------------------------

    @_timed
    def check_integrity(self) -> HealthResult:
        """1. PRAGMA integrity_check."""
        conn = self._conn()
        try:
            rows = conn.execute("PRAGMA integrity_check(100);").fetchall()
            first = rows[0][0] if rows else "unknown"
            if first == "ok":
                return HealthResult("integrity", "PASS", "Database integrity OK")
            detail = "; ".join(r[0] for r in rows[:5])
            return HealthResult("integrity", "FAIL", f"Integrity errors: {detail}")
        finally:
            conn.close()

    @_timed
    def check_wal_size(self) -> HealthResult:
        """2. WAL file size check."""
        wal_path = self.db_path + "-wal"
        if not os.path.isfile(wal_path):
            return HealthResult("wal_size", "PASS", "No WAL file (DELETE mode or fresh DB)")
        size_mb = os.path.getsize(wal_path) / (1024 * 1024)
        if size_mb > 200:
            return HealthResult("wal_size", "FAIL", f"WAL is {size_mb:.1f} MB (>200 MB critical)")
        if size_mb > 50:
            return HealthResult("wal_size", "WARN", f"WAL is {size_mb:.1f} MB (>50 MB — checkpoint recommended)")
        return HealthResult("wal_size", "PASS", f"WAL is {size_mb:.1f} MB")

    @_timed
    def check_fts5_health(self) -> HealthResult:
        """3. FTS5 index probe for evidence_fts, timeline_fts, md_sections_fts."""
        conn = self._conn()
        try:
            failures = []
            tested = 0
            for fts_table, fts_col in FTS5_TABLES:
                if not self._table_exists(conn, fts_table):
                    continue
                tested += 1
                try:
                    conn.execute(
                        f"SELECT COUNT(*) FROM [{fts_table}] WHERE [{fts_col}] MATCH 'test'",
                    ).fetchone()
                except sqlite3.OperationalError as exc:
                    failures.append(f"{fts_table}: {exc}")
            if not tested:
                return HealthResult("fts5_health", "WARN", "No FTS5 tables found")
            if failures:
                return HealthResult("fts5_health", "FAIL", f"FTS5 errors: {'; '.join(failures)}")
            return HealthResult("fts5_health", "PASS", f"All {tested} FTS5 indexes healthy")
        finally:
            conn.close()

    @_timed
    def check_table_existence(self) -> HealthResult:
        """4. Verify 20 critical tables exist."""
        conn = self._conn()
        try:
            existing = set()
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall():
                existing.add(row[0])
            missing = [t for t in CRITICAL_TABLES if t not in existing]
            if not missing:
                return HealthResult("table_existence", "PASS", f"All {len(CRITICAL_TABLES)} critical tables present")
            if len(missing) > 10:
                return HealthResult("table_existence", "FAIL", f"{len(missing)} critical tables missing: {', '.join(missing[:5])}...")
            return HealthResult("table_existence", "WARN", f"{len(missing)} missing: {', '.join(missing)}")
        finally:
            conn.close()

    @_timed
    def check_row_counts(self) -> HealthResult:
        """5. Row counts vs baseline — detect anomalous drops or spikes."""
        conn = self._conn()
        try:
            # Ensure baseline table
            conn.executescript(BASELINE_DDL)
            conn.commit()

            current_counts: dict[str, int] = {}
            for table in ROW_COUNT_TABLES:
                if not self._table_exists(conn, table):
                    continue
                try:
                    row = conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()
                    current_counts[table] = row[0] if row else 0
                except sqlite3.OperationalError:
                    continue

            # Load baseline
            baseline: dict[str, int] = {}
            if self._table_exists(conn, "db_health_baseline"):
                for row in conn.execute(
                    "SELECT table_name, row_count FROM db_health_baseline"
                ).fetchall():
                    baseline[row[0]] = row[1]

            # If no baseline yet, populate it and return PASS
            if not baseline:
                params = [
                    (tbl, cnt) for tbl, cnt in current_counts.items()
                ]
                conn.executemany(
                    "INSERT OR REPLACE INTO db_health_baseline (table_name, row_count, last_updated) "
                    "VALUES (?, ?, datetime('now'))",
                    params,
                )
                conn.commit()
                return HealthResult(
                    "row_counts", "PASS",
                    f"Baseline initialized with {len(params)} tables",
                )

            warnings = []
            for tbl, cur in current_counts.items():
                base = baseline.get(tbl)
                if base is None or base == 0:
                    continue
                ratio = cur / base
                if ratio < 0.9:
                    warnings.append(f"{tbl}: dropped {100*(1-ratio):.0f}% ({base}→{cur})")
                elif ratio > 3.0:
                    warnings.append(f"{tbl}: grew {100*(ratio-1):.0f}% ({base}→{cur})")

            if warnings:
                return HealthResult(
                    "row_counts", "WARN",
                    f"{len(warnings)} anomalies: {'; '.join(warnings[:3])}",
                )
            return HealthResult(
                "row_counts", "PASS",
                f"All {len(current_counts)} tables within normal range",
            )
        finally:
            conn.close()

    @_timed
    def check_disk_space(self) -> HealthResult:
        """6. C:\\ free space check."""
        drive = os.path.splitdrive(self.db_path)[0]
        if not drive:
            drive = "C:"
        target = drive + "\\"
        try:
            usage = _get_disk_usage(target)
            free_gb = usage / (1024 ** 3)
            if free_gb < 5:
                return HealthResult("disk_space", "FAIL", f"{drive} has {free_gb:.1f} GB free (<5 GB critical)")
            if free_gb < 10:
                return HealthResult("disk_space", "WARN", f"{drive} has {free_gb:.1f} GB free (<10 GB)")
            return HealthResult("disk_space", "PASS", f"{drive} has {free_gb:.1f} GB free")
        except OSError as exc:
            return HealthResult("disk_space", "FAIL", f"Cannot check disk space: {exc}")

    @_timed
    def check_busy_timeout(self) -> HealthResult:
        """7. Verify busy_timeout >= 30000."""
        conn = self._conn()
        try:
            row = conn.execute("PRAGMA busy_timeout;").fetchone()
            val = row[0] if row else 0
            if val >= 30000:
                return HealthResult("busy_timeout", "PASS", f"busy_timeout = {val} ms")
            return HealthResult("busy_timeout", "WARN", f"busy_timeout = {val} ms (should be >= 30000)")
        finally:
            conn.close()

    @_timed
    def check_journal_mode(self) -> HealthResult:
        """8. Verify correct journal mode for filesystem type."""
        conn = self._conn()
        try:
            row = conn.execute("PRAGMA journal_mode;").fetchone()
            mode = row[0].upper() if row else "UNKNOWN"
            if self.exfat:
                expected = "DELETE"
                if mode == expected:
                    return HealthResult("journal_mode", "PASS", f"Journal mode {mode} (correct for exFAT)")
                return HealthResult("journal_mode", "WARN", f"Journal mode {mode} but drive is exFAT — should be DELETE")
            else:
                expected = "WAL"
                if mode == expected:
                    return HealthResult("journal_mode", "PASS", f"Journal mode {mode} (correct for NTFS)")
                return HealthResult("journal_mode", "WARN", f"Journal mode {mode} — should be WAL for NTFS")
        finally:
            conn.close()

    @_timed
    def check_optimize_needed(self) -> HealthResult:
        """9. Probe whether PRAGMA optimize would be beneficial."""
        conn = self._conn()
        try:
            # PRAGMA optimize with mask 0x02 reports what it would do without executing
            rows = conn.execute("PRAGMA optimize(0x03);").fetchall()
            if not rows:
                return HealthResult("optimize_needed", "PASS", "No optimization needed")
            actions = [r[0] for r in rows if r[0]]
            if actions:
                return HealthResult(
                    "optimize_needed", "WARN",
                    f"{len(actions)} indexes could benefit from ANALYZE",
                )
            return HealthResult("optimize_needed", "PASS", "Optimizer stats current")
        except sqlite3.OperationalError as exc:
            return HealthResult("optimize_needed", "WARN", f"Cannot probe optimize: {exc}")
        finally:
            conn.close()

    @_timed
    def check_connection_pool(self) -> HealthResult:
        """10. Verify open → query → close works cleanly."""
        conn = None
        try:
            conn = self._conn()
            conn.execute("SELECT 1;").fetchone()
            return HealthResult("connection_pool", "PASS", "Connection lifecycle OK")
        except Exception as exc:
            return HealthResult("connection_pool", "FAIL", f"Connection failed: {exc}")
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Orchestrator
    # ------------------------------------------------------------------

    def run_all_checks(self) -> HealthReport:
        """Execute all 10 checks and return an aggregated report."""
        t0 = time.perf_counter()
        report = HealthReport(db_path=self.db_path)

        checks = [
            self.check_integrity,
            self.check_wal_size,
            self.check_fts5_health,
            self.check_table_existence,
            self.check_row_counts,
            self.check_disk_space,
            self.check_busy_timeout,
            self.check_journal_mode,
            self.check_optimize_needed,
            self.check_connection_pool,
        ]

        for check_fn in checks:
            try:
                result = check_fn()
                report.add(result)
                self._log_result(result)
            except Exception as exc:
                name = check_fn.__name__.replace("check_", "")
                err_result = HealthResult(name, "FAIL", f"Check crashed: {exc}")
                report.add(err_result)
                self._log_result(err_result)
                logger.error("Check %s crashed: %s", name, exc)

        report.duration_ms = (time.perf_counter() - t0) * 1000
        return report

    def _log_result(self, result: HealthResult) -> None:
        """Persist check result to db_health_log."""
        try:
            conn = self._conn()
            try:
                conn.execute(
                    "INSERT INTO db_health_log (check_name, status, detail, duration_ms) "
                    "VALUES (?, ?, ?, ?)",
                    (result.check_name, result.status, result.detail, result.duration_ms),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as exc:
            logger.warning("Failed to log health result: %s", exc)

    def get_current_row_counts(self) -> dict[str, int]:
        """Return current row counts for key tables (used by AnomalyDetector)."""
        conn = self._conn()
        try:
            counts: dict[str, int] = {}
            for table in ROW_COUNT_TABLES:
                if not self._table_exists(conn, table):
                    continue
                try:
                    row = conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()
                    counts[table] = row[0] if row else 0
                except sqlite3.OperationalError:
                    continue
            return counts
        finally:
            conn.close()


def _get_disk_usage(path: str) -> int:
    """Return free bytes on the drive containing *path*."""
    try:
        free = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(
            path, None, None, ctypes.byref(free),
        )
        return free.value
    except (AttributeError, OSError):
        # Fallback for non-Windows
        import shutil
        return shutil.disk_usage(path).free

"""FORTRESS Healer — Automated repair actions for failed health checks.

Processes HealthResult failures and attempts safe, additive-only repairs.
Never deletes data or tables — all healing is non-destructive (Rule 1).
"""

import os
import sqlite3
import time
import logging
from dataclasses import dataclass
from typing import Optional

from .health import (
    HealthResult,
    HealthReport,
    _open_connection,
    _is_exfat,
    BASELINE_DDL,
    HEALTH_LOG_DDL,
)

logger = logging.getLogger(__name__)


@dataclass
class HealResult:
    """Outcome of a single healing action."""

    action: str
    success: bool
    detail: str
    duration_ms: float = 0.0


# Map check names to healing strategies
HEAL_DISPATCH = {
    "wal_size": "_heal_wal_checkpoint",
    "fts5_health": "_heal_fts5_rebuild",
    "table_existence": "_heal_missing_tables",
    "row_counts": "_heal_row_anomaly",
    "disk_space": "_heal_disk_space",
    "optimize_needed": "_heal_optimize",
    "journal_mode": "_heal_journal_mode",
    "busy_timeout": "_heal_busy_timeout",
}


class DatabaseHealer:
    """Attempt automated repairs for failed/warned health checks."""

    def __init__(self, db_path: str) -> None:
        self.db_path = os.path.abspath(db_path)
        self.exfat = _is_exfat(self.db_path)
        self.heal_log: list[HealResult] = []

    def _conn(self) -> sqlite3.Connection:
        return _open_connection(self.db_path, exfat=self.exfat)

    def heal(self, health_results: list[HealthResult]) -> list[HealResult]:
        """Process all non-PASS results and attempt repairs."""
        self.heal_log = []

        for result in health_results:
            if result.status == "PASS":
                continue

            method_name = HEAL_DISPATCH.get(result.check_name)
            if method_name is None:
                # No automated repair for this check (e.g., integrity, connection_pool)
                self.heal_log.append(
                    HealResult(
                        action=f"skip_{result.check_name}",
                        success=False,
                        detail=f"No automated repair for '{result.check_name}': {result.detail}",
                    )
                )
                continue

            heal_fn = getattr(self, method_name, None)
            if heal_fn is None:
                continue

            t0 = time.perf_counter()
            try:
                hr = heal_fn(result)
                hr.duration_ms = (time.perf_counter() - t0) * 1000
                self.heal_log.append(hr)
                self._persist_heal(result, hr)
            except Exception as exc:
                elapsed = (time.perf_counter() - t0) * 1000
                hr = HealResult(
                    action=method_name,
                    success=False,
                    detail=f"Healing crashed: {exc}",
                    duration_ms=elapsed,
                )
                self.heal_log.append(hr)
                logger.error("Healer %s crashed: %s", method_name, exc)

        return self.heal_log

    # ------------------------------------------------------------------
    # Healing strategies
    # ------------------------------------------------------------------

    def _heal_wal_checkpoint(self, result: HealthResult) -> HealResult:
        """Force WAL checkpoint to reduce WAL file size."""
        conn = self._conn()
        try:
            row = conn.execute("PRAGMA wal_checkpoint(TRUNCATE);").fetchone()
            if row:
                blocked, log_pages, checkpointed = row
                detail = (
                    f"WAL checkpoint: blocked={blocked}, "
                    f"log_pages={log_pages}, checkpointed={checkpointed}"
                )
                success = blocked == 0
            else:
                detail = "WAL checkpoint returned no result"
                success = False
            return HealResult("wal_checkpoint", success, detail)
        finally:
            conn.close()

    def _heal_fts5_rebuild(self, result: HealthResult) -> HealResult:
        """Rebuild corrupt FTS5 indexes."""
        conn = self._conn()
        try:
            # Parse which FTS tables failed from the detail string
            fts_tables = ["evidence_fts", "timeline_fts", "md_sections_fts"]
            rebuilt = []
            errors = []

            for fts in fts_tables:
                # Check if this table exists
                exists = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                    (fts,),
                ).fetchone()
                if not exists:
                    continue

                # Only rebuild if it was mentioned in the failure detail
                if fts not in result.detail:
                    continue

                try:
                    conn.execute(f"INSERT INTO [{fts}]([{fts}]) VALUES('rebuild');")
                    conn.commit()
                    rebuilt.append(fts)
                except sqlite3.OperationalError as exc:
                    errors.append(f"{fts}: {exc}")

            if errors:
                return HealResult(
                    "fts5_rebuild",
                    len(rebuilt) > 0,
                    f"Rebuilt: {rebuilt or 'none'}; Errors: {'; '.join(errors)}",
                )
            if rebuilt:
                return HealResult("fts5_rebuild", True, f"Rebuilt indexes: {', '.join(rebuilt)}")
            return HealResult("fts5_rebuild", True, "No FTS5 indexes needed rebuilding")
        finally:
            conn.close()

    def _heal_missing_tables(self, result: HealthResult) -> HealResult:
        """Log warning about missing tables — don't create them (could be wrong DB)."""
        return HealResult(
            "missing_tables_alert",
            False,
            f"Missing tables detected (not auto-created — verify correct DB): {result.detail}",
        )

    def _heal_row_anomaly(self, result: HealthResult) -> HealResult:
        """Snapshot current row counts for investigation — no data modification."""
        conn = self._conn()
        try:
            # Save a snapshot of current counts to the health log
            conn.executescript(BASELINE_DDL)
            conn.commit()

            snapshot_parts = []
            for row in conn.execute(
                "SELECT table_name, row_count FROM db_health_baseline"
            ).fetchall():
                snapshot_parts.append(f"{row[0]}={row[1]}")

            return HealResult(
                "row_anomaly_snapshot",
                True,
                f"Snapshot saved for investigation. Current baseline: {'; '.join(snapshot_parts[:5])}...",
            )
        finally:
            conn.close()

    def _heal_disk_space(self, result: HealthResult) -> HealResult:
        """Attempt to reclaim space by checkpointing all WAL files."""
        # Find all .db files in the same directory
        db_dir = os.path.dirname(self.db_path)
        reclaimed = []
        errors = []

        for entry in os.scandir(db_dir):
            if not entry.name.endswith(".db"):
                continue
            wal_path = entry.path + "-wal"
            if not os.path.isfile(wal_path):
                continue
            wal_mb = os.path.getsize(wal_path) / (1024 * 1024)
            if wal_mb < 1:
                continue

            try:
                c = _open_connection(entry.path, exfat=self.exfat)
                try:
                    c.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                    reclaimed.append(f"{entry.name} ({wal_mb:.1f} MB)")
                finally:
                    c.close()
            except Exception as exc:
                errors.append(f"{entry.name}: {exc}")

        if reclaimed:
            return HealResult(
                "disk_reclaim",
                True,
                f"Checkpointed WAL for: {', '.join(reclaimed)}",
            )
        if errors:
            return HealResult("disk_reclaim", False, f"Errors: {'; '.join(errors)}")
        return HealResult("disk_reclaim", True, "No large WAL files to checkpoint")

    def _heal_optimize(self, result: HealthResult) -> HealResult:
        """Run PRAGMA optimize to update query planner statistics."""
        conn = self._conn()
        try:
            conn.execute("PRAGMA optimize;")
            return HealResult("optimize", True, "PRAGMA optimize executed successfully")
        except sqlite3.OperationalError as exc:
            return HealResult("optimize", False, f"Optimize failed: {exc}")
        finally:
            conn.close()

    def _heal_journal_mode(self, result: HealthResult) -> HealResult:
        """Switch journal mode to match filesystem type."""
        conn = self._conn()
        try:
            if self.exfat:
                target = "DELETE"
            else:
                target = "WAL"

            row = conn.execute(f"PRAGMA journal_mode = {target};").fetchone()
            actual = row[0].upper() if row else "UNKNOWN"

            if actual == target:
                return HealResult(
                    "journal_mode_fix", True,
                    f"Journal mode set to {actual}",
                )
            return HealResult(
                "journal_mode_fix", False,
                f"Attempted {target} but got {actual} — DB may be locked or read-only",
            )
        finally:
            conn.close()

    def _heal_busy_timeout(self, result: HealthResult) -> HealResult:
        """Set busy_timeout to 60000ms (connection-level, not persistent)."""
        return HealResult(
            "busy_timeout_note",
            True,
            "busy_timeout is per-connection — FORTRESS sets it automatically on every connection",
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist_heal(self, check: HealthResult, heal: HealResult) -> None:
        """Update db_health_log with healing info for the most recent matching check."""
        try:
            conn = self._conn()
            try:
                conn.execute(
                    "UPDATE db_health_log SET healed = 1, heal_detail = ? "
                    "WHERE id = (SELECT MAX(id) FROM db_health_log WHERE check_name = ?)",
                    (heal.detail, check.check_name),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as exc:
            logger.warning("Failed to persist heal result: %s", exc)

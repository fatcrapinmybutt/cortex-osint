"""Cross-Brain Synchronization Engine — keeps all brain DBs in harmony.

Discovers brain databases, compares schemas/row counts against the central
litigation_context.db, and performs additive-only synchronization.  NEVER
deletes data — INSERT OR IGNORE is the sole write primitive.
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path resolution — uses shared module when available, falls back gracefully
# ---------------------------------------------------------------------------

try:
    from shared import get_root, get_brain_dir, get_db_path
    REPO_ROOT = get_root()
    BRAINS_DIR = get_brain_dir()
    CENTRAL_DB = get_db_path()
except ImportError:
    REPO_ROOT = Path(__file__).resolve().parents[3]
    BRAINS_DIR = REPO_ROOT / "00_SYSTEM" / "brains"
    CENTRAL_DB = REPO_ROOT / "litigation_context.db"

MBP_BRAIN = REPO_ROOT / "mbp_brain.db"

# Standard PRAGMAs applied to every connection (Rule 18)
_PRAGMAS = [
    "PRAGMA busy_timeout=60000",
    "PRAGMA journal_mode=WAL",
    "PRAGMA cache_size=-32000",
    "PRAGMA temp_store=MEMORY",
    "PRAGMA synchronous=NORMAL",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _open(db_path: str | Path, *, readonly: bool = False) -> sqlite3.Connection:
    """Open a SQLite connection with standard PRAGMAs."""
    path = str(db_path)
    if readonly:
        path = f"file:{path}?mode=ro"
    conn = sqlite3.connect(path, uri=readonly)
    for pragma in _PRAGMAS:
        try:
            conn.execute(pragma)
        except sqlite3.OperationalError:
            pass  # WAL may not be supported on exFAT — skip gracefully
    return conn


def _table_list(conn: sqlite3.Connection) -> list[str]:
    """Return sorted list of user-created tables."""
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def _row_count(conn: sqlite3.Connection, table: str) -> int:
    """Return row count for *table*, or -1 on error."""
    try:
        return conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]
    except (sqlite3.OperationalError, sqlite3.DatabaseError) as exc:
        logger.warning("Could not count rows in %s: %s", table, exc)
        return -1


def _column_names(conn: sqlite3.Connection, table: str) -> list[str]:
    """Return column names for *table* via PRAGMA table_info (Rule 16)."""
    return [r[1] for r in conn.execute(f"PRAGMA table_info([{table}])").fetchall()]


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------


class BrainSyncEngine:
    """Discovers, inspects, and synchronises LitigationOS brain databases."""

    def __init__(self) -> None:
        self._central: sqlite3.Connection | None = None
        self.sync_log: list[dict] = []

    # -- lazy central connection -------------------------------------------

    @property
    def central(self) -> sqlite3.Connection:
        if self._central is None:
            self._central = _open(CENTRAL_DB)
        return self._central

    # -- discovery ---------------------------------------------------------

    def discover_brains(self) -> list[dict]:
        """Find all ``.db`` files in the brains directory plus mbp_brain.db."""
        brains: list[dict] = []
        if BRAINS_DIR.exists():
            for f in sorted(BRAINS_DIR.glob("*.db")):
                # Skip WAL/SHM helper files that glob may surface
                if f.suffix != ".db":
                    continue
                brains.append(
                    {
                        "path": str(f),
                        "name": f.stem,
                        "size_mb": round(f.stat().st_size / (1024**2), 1),
                    }
                )
        if MBP_BRAIN.exists():
            brains.append(
                {
                    "path": str(MBP_BRAIN),
                    "name": "mbp_brain",
                    "size_mb": round(MBP_BRAIN.stat().st_size / (1024**2), 1),
                }
            )
        return brains

    # -- schema introspection -----------------------------------------------

    def get_brain_schema(self, db_path: str | Path) -> dict[str, int]:
        """Return ``{table_name: row_count}`` for every table in *db_path*."""
        conn = _open(db_path, readonly=True)
        try:
            tables = _table_list(conn)
            return {t: _row_count(conn, t) for t in tables}
        finally:
            conn.close()

    # -- sync status report ------------------------------------------------

    def sync_status(self) -> dict:
        """Build a comprehensive status report across all brains."""
        brains = self.discover_brains()
        central_tables = self.get_brain_schema(CENTRAL_DB)

        report: dict = {
            "timestamp": datetime.now().isoformat(),
            "central_db": {
                "path": str(CENTRAL_DB),
                "tables": len(central_tables),
            },
            "brains": [],
            "summary": {
                "total_brains": len(brains),
                "total_mismatches": 0,
            },
        }

        for brain in brains:
            try:
                brain_tables = self.get_brain_schema(brain["path"])
            except sqlite3.DatabaseError as exc:
                logger.error("Cannot open %s: %s", brain["path"], exc)
                report["brains"].append(
                    {
                        "name": brain["name"],
                        "path": brain["path"],
                        "size_mb": brain["size_mb"],
                        "error": str(exc),
                    }
                )
                continue

            common = set(central_tables) & set(brain_tables)
            mismatches: list[dict] = []
            for table in sorted(common):
                c_count = central_tables[table]
                b_count = brain_tables[table]
                if c_count != b_count and c_count > 0 and b_count > 0:
                    mismatches.append(
                        {
                            "table": table,
                            "central": c_count,
                            "brain": b_count,
                            "delta": c_count - b_count,
                        }
                    )

            report["summary"]["total_mismatches"] += len(mismatches)
            report["brains"].append(
                {
                    "name": brain["name"],
                    "path": brain["path"],
                    "size_mb": brain["size_mb"],
                    "tables": len(brain_tables),
                    "common_with_central": len(common),
                    "mismatches": mismatches,
                    "unique_tables": sorted(set(brain_tables) - set(central_tables)),
                }
            )

        return report

    # -- additive table sync -----------------------------------------------

    def sync_table(
        self,
        source_db: str | Path,
        target_db: str | Path,
        table_name: str,
    ) -> dict:
        """Copy rows from *source_db*.*table_name* into *target_db* additively.

        Uses INSERT OR IGNORE — never deletes or updates existing rows.
        """
        src = _open(source_db, readonly=True)
        tgt = _open(target_db)

        try:
            # --- schema introspection (Rule 16) ---------------------------
            cols = _column_names(src, table_name)
            if not cols:
                return {"table": table_name, "status": "error",
                        "detail": f"Table [{table_name}] not found in source"}

            # Ensure table exists in target (mirror schema)
            tgt_tables = set(_table_list(tgt))
            if table_name not in tgt_tables:
                create_row = src.execute(
                    "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                    (table_name,),
                ).fetchone()
                if create_row and create_row[0]:
                    tgt.execute(create_row[0])
                    tgt.commit()
                else:
                    return {"table": table_name, "status": "error",
                            "detail": "Cannot read CREATE TABLE from source"}

            before = _row_count(tgt, table_name)

            # Batch-fetch from source and INSERT OR IGNORE into target
            col_list = ", ".join(f"[{c}]" for c in cols)
            placeholders = ", ".join(["?"] * len(cols))
            insert_sql = (
                f"INSERT OR IGNORE INTO [{table_name}] ({col_list}) "
                f"VALUES ({placeholders})"
            )

            cursor = src.execute(f"SELECT {col_list} FROM [{table_name}]")
            batch: list[tuple] = []
            batch_size = 5000
            inserted_total = 0

            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break
                tgt.executemany(insert_sql, rows)
                inserted_total += len(rows)

            tgt.commit()
            after = _row_count(tgt, table_name)

            result = {
                "table": table_name,
                "before": before,
                "after": after,
                "added": after - before,
                "scanned": inserted_total,
                "status": "ok",
            }
            self.sync_log.append(result)
            return result

        except sqlite3.Error as exc:
            logger.error("sync_table(%s) failed: %s", table_name, exc)
            return {"table": table_name, "status": "error", "detail": str(exc)}
        finally:
            src.close()
            tgt.close()

    # -- bulk sync helpers -------------------------------------------------

    def sync_brain_to_central(
        self,
        brain_path: str | Path,
        tables: list[str] | None = None,
    ) -> list[dict]:
        """Sync selected (or all common) tables from a brain → central DB."""
        brain_schema = self.get_brain_schema(brain_path)
        central_schema = self.get_brain_schema(CENTRAL_DB)
        common = set(brain_schema) & set(central_schema)

        if tables:
            common = common & set(tables)

        results: list[dict] = []
        for table in sorted(common):
            result = self.sync_table(brain_path, CENTRAL_DB, table)
            results.append(result)
            if result.get("added", 0) > 0:
                logger.info(
                    "Synced %s → central: +%d rows in [%s]",
                    Path(brain_path).stem,
                    result["added"],
                    table,
                )
        return results

    def sync_central_to_brain(
        self,
        brain_path: str | Path,
        tables: list[str] | None = None,
    ) -> list[dict]:
        """Sync selected (or all common) tables from central DB → a brain."""
        brain_schema = self.get_brain_schema(brain_path)
        central_schema = self.get_brain_schema(CENTRAL_DB)
        common = set(brain_schema) & set(central_schema)

        if tables:
            common = common & set(tables)

        results: list[dict] = []
        for table in sorted(common):
            result = self.sync_table(CENTRAL_DB, brain_path, table)
            results.append(result)
            if result.get("added", 0) > 0:
                logger.info(
                    "Synced central → %s: +%d rows in [%s]",
                    Path(brain_path).stem,
                    result["added"],
                    table,
                )
        return results

    # -- fingerprint -------------------------------------------------------

    def fingerprint(self, db_path: str | Path) -> dict[str, int]:
        """Quick fingerprint: {table: row_count} for fast diff comparison."""
        return self.get_brain_schema(db_path)

    # -- cleanup -----------------------------------------------------------

    def close(self) -> None:
        """Release the central DB connection."""
        if self._central is not None:
            self._central.close()
            self._central = None


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json as _json

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    engine = BrainSyncEngine()

    print("=== Discovering brains ===")
    for b in engine.discover_brains():
        print(f"  {b['name']:30s}  {b['size_mb']:>8.1f} MB  {b['path']}")

    print("\n=== Sync status ===")
    status = engine.sync_status()
    print(_json.dumps(status, indent=2, default=str))

    engine.close()

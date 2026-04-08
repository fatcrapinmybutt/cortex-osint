"""SENTINEL File Organizer — Copies classified files to canonical locations.

NEVER deletes or moves original files (Rule 1 SACRED).
Copies with shutil.copy2 (metadata preservation), dedup checks via SHA-256,
and registers every action in file_inventory.
"""
from __future__ import annotations

import logging
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from .classifier import ClassificationResult, CATEGORY_DIRS

logger = logging.getLogger("sentinel.organizer")

# Repo root — configurable, defaults to LitigationOS root
REPO_ROOT = os.environ.get(
    "LITIGATIONOS_ROOT",
    str(Path(__file__).resolve().parents[3]),  # 00_SYSTEM/daemon/sentinel → repo root
)

DB_PATH = os.environ.get(
    "LITIGATIONOS_DB",
    os.path.join(REPO_ROOT, "litigation_context.db"),
)

# Standard PRAGMAs for every connection
_PRAGMAS = [
    "PRAGMA busy_timeout = 60000",
    "PRAGMA journal_mode = WAL",
    "PRAGMA cache_size = -32000",
    "PRAGMA temp_store = MEMORY",
    "PRAGMA synchronous = NORMAL",
]

LOG_DIR = os.path.join(REPO_ROOT, "logs")


def _get_db_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Open a SQLite connection with standard PRAGMAs."""
    conn = sqlite3.connect(db_path, timeout=60)
    conn.row_factory = sqlite3.Row
    for pragma in _PRAGMAS:
        conn.execute(pragma)
    return conn


def _verify_file_inventory_schema(conn: sqlite3.Connection) -> set[str]:
    """Return the set of column names in file_inventory, or empty if table missing."""
    try:
        rows = conn.execute("PRAGMA table_info(file_inventory)").fetchall()
        return {row["name"] for row in rows}
    except Exception:
        return set()


class FileOrganizer:
    """Copies classified files to canonical locations and registers in DB.

    Rules enforced:
    - NEVER deletes original files (Rule 1 SACRED)
    - Uses shutil.copy2 to preserve metadata
    - Dedup: skips if same SHA-256 already registered at destination
    - Logs all actions to logs/sentinel.log
    """

    def __init__(
        self,
        repo_root: str = REPO_ROOT,
        db_path: str = DB_PATH,
        dry_run: bool = False,
    ) -> None:
        self.repo_root = repo_root
        self.db_path = db_path
        self.dry_run = dry_run
        self._ensure_log_dir()
        self._file_handler = self._setup_file_logging()

        # Verify DB schema once
        self._columns: set[str] = set()
        self._schema_verified = False

    def _ensure_log_dir(self) -> None:
        os.makedirs(LOG_DIR, exist_ok=True)

    def _setup_file_logging(self) -> logging.FileHandler:
        log_path = os.path.join(LOG_DIR, "sentinel.log")
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        logger.addHandler(handler)
        return handler

    def _verify_schema(self) -> set[str]:
        """Lazy schema verification (once per session)."""
        if self._schema_verified:
            return self._columns
        try:
            conn = _get_db_connection(self.db_path)
            self._columns = _verify_file_inventory_schema(conn)
            conn.close()
            self._schema_verified = True
            if not self._columns:
                logger.warning("file_inventory table not found — DB registration will be skipped")
            else:
                logger.info("file_inventory schema verified: %d columns", len(self._columns))
        except Exception as exc:
            logger.error("Schema verification failed: %s", exc)
        return self._columns

    def organize(self, result: ClassificationResult) -> dict:
        """Copy a classified file to its canonical location and register in DB.

        Args:
            result: ClassificationResult from FileClassifier.classify()

        Returns:
            Dict with keys: copied (bool), dest_path (str), registered (bool),
            reason (str), duplicate (bool).
        """
        outcome = {
            "copied": False,
            "dest_path": "",
            "registered": False,
            "reason": "",
            "duplicate": False,
        }

        src = result.file_path
        if not os.path.isfile(src):
            outcome["reason"] = "Source file not found"
            logger.warning("SKIP — source not found: %s", src)
            return outcome

        # Build destination path
        canonical_subdir = result.canonical_dir
        dest_dir = os.path.join(self.repo_root, canonical_subdir)
        dest_path = os.path.join(dest_dir, os.path.basename(src))
        outcome["dest_path"] = dest_path

        # Dedup: check if this exact file (by SHA-256) is already at destination
        if os.path.isfile(dest_path) and result.sha256:
            existing_sha = self._file_sha256(dest_path)
            if existing_sha == result.sha256:
                outcome["duplicate"] = True
                outcome["reason"] = "Identical file already at destination (SHA-256 match)"
                logger.info("DEDUP — identical file exists: %s", dest_path)
                # Still register in DB if not there
                outcome["registered"] = self._register_in_db(result, dest_path)
                return outcome

            # Hash collision with different content — append suffix
            base, ext = os.path.splitext(os.path.basename(src))
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest_path = os.path.join(dest_dir, f"{base}_{ts}{ext}")
            outcome["dest_path"] = dest_path

        # Check DB for duplicate SHA-256 anywhere in file_inventory
        if result.sha256 and self._sha256_in_db(result.sha256):
            outcome["duplicate"] = True
            outcome["reason"] = "SHA-256 already registered in file_inventory"
            logger.info("DEDUP (DB) — SHA-256 already known: %s", result.sha256[:16])
            outcome["registered"] = True
            return outcome

        # Copy file
        if self.dry_run:
            outcome["reason"] = "DRY RUN — would copy"
            outcome["copied"] = True
            logger.info("DRY RUN — would copy %s → %s", src, dest_path)
        else:
            try:
                os.makedirs(dest_dir, exist_ok=True)
                shutil.copy2(src, dest_path)
                outcome["copied"] = True
                outcome["reason"] = "Copied successfully"
                logger.info("COPIED: %s → %s", src, dest_path)
            except Exception as exc:
                outcome["reason"] = f"Copy failed: {exc}"
                logger.error("COPY FAILED: %s → %s: %s", src, dest_path, exc)
                return outcome

        # Register in DB
        outcome["registered"] = self._register_in_db(result, dest_path)
        return outcome

    def _register_in_db(self, result: ClassificationResult, dest_path: str) -> bool:
        """Insert file record into file_inventory table."""
        columns = self._verify_schema()
        if not columns:
            logger.warning("Cannot register — file_inventory table not available")
            return False

        try:
            conn = _get_db_connection(self.db_path)

            # Build adaptive INSERT based on actual schema
            insert_cols = []
            insert_vals: list[object] = []

            col_map = {
                "file_path": dest_path,
                "file_name": os.path.basename(dest_path),
                "extension": os.path.splitext(dest_path)[1].lower(),
                "drive_letter": os.path.splitdrive(dest_path)[0].rstrip(":").upper() or "C",
                "size_bytes": result.file_size,
                "sha256": result.sha256,
                "lane": result.lane,
                "is_litigation_relevant": 1,
                "ingested": 0,
                "canonical_category": result.category,
                "source_table": "sentinel",
            }

            for col_name, col_val in col_map.items():
                if col_name in columns:
                    insert_cols.append(col_name)
                    insert_vals.append(col_val)

            if not insert_cols:
                logger.warning("No matching columns for INSERT")
                conn.close()
                return False

            placeholders = ", ".join("?" for _ in insert_cols)
            col_list = ", ".join(insert_cols)
            sql = f"INSERT OR IGNORE INTO file_inventory ({col_list}) VALUES ({placeholders})"

            conn.execute(sql, insert_vals)
            conn.commit()

            # Verify the insert
            verify_sql = "SELECT COUNT(*) FROM file_inventory WHERE file_path = ?"
            count = conn.execute(verify_sql, (dest_path,)).fetchone()[0]
            conn.close()

            if count > 0:
                logger.info("DB REGISTERED: %s (lane=%s, cat=%s)", dest_path, result.lane, result.category)
                return True
            else:
                logger.warning("DB INSERT verified but row not found: %s", dest_path)
                return False

        except Exception as exc:
            logger.error("DB registration failed for %s: %s", dest_path, exc)
            return False

    def _sha256_in_db(self, sha256: str) -> bool:
        """Check if a SHA-256 hash exists in file_inventory."""
        columns = self._verify_schema()
        if "sha256" not in columns:
            return False
        try:
            conn = _get_db_connection(self.db_path)
            row = conn.execute(
                "SELECT COUNT(*) FROM file_inventory WHERE sha256 = ?", (sha256,)
            ).fetchone()
            conn.close()
            return row[0] > 0
        except Exception:
            return False

    @staticmethod
    def _file_sha256(file_path: str) -> str:
        """Compute SHA-256 of a file."""
        import hashlib
        sha = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(1024 * 1024)
                    if not chunk:
                        break
                    sha.update(chunk)
            return sha.hexdigest()
        except Exception:
            return ""


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print(f"SENTINEL Organizer — repo root: {REPO_ROOT}")
    print(f"  DB: {DB_PATH}")
    print(f"  Log: {LOG_DIR}/sentinel.log")

    # Quick schema check
    cols = set()
    try:
        conn = _get_db_connection()
        cols = _verify_file_inventory_schema(conn)
        conn.close()
    except Exception as exc:
        print(f"  DB connection failed: {exc}")

    if cols:
        print(f"  file_inventory columns ({len(cols)}): {sorted(cols)}")
    else:
        print("  file_inventory table NOT FOUND")

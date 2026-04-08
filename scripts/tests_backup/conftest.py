"""Shared pytest fixtures for LitigationOS test suite.

Provides:
- db_path: resolved path to litigation_context.db
- db_conn: read-only SQLite connection with proper PRAGMAs
- tmp_dir: auto-cleaning temporary directory
- Skip markers for slow / resource-dependent tests
"""

import os
import sys
import sqlite3
import tempfile
import shutil
from pathlib import Path

import pytest

# ── Path setup (avoid shadow modules in repo root) ──────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # 00_SYSTEM -> LitigationOS
ENGINES_DIR = REPO_ROOT / "00_SYSTEM" / "engines"
DAEMON_DIR = REPO_ROOT / "00_SYSTEM" / "daemon"
SYSTEM_DIR = REPO_ROOT / "00_SYSTEM"

# Add engine parents to sys.path so `from engines.X import Y` works,
# but do NOT add repo root (shadow modules live there).
for p in (str(SYSTEM_DIR), str(REPO_ROOT / "00_SYSTEM")):
    if p not in sys.path:
        sys.path.insert(0, p)


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def db_path() -> Path:
    """Resolved path to the central litigation_context.db."""
    p = REPO_ROOT / "litigation_context.db"
    if not p.exists():
        pytest.skip("litigation_context.db not found at repo root")
    return p


@pytest.fixture(scope="function")
def db_conn(db_path):
    """Read-only SQLite connection with proper PRAGMAs.

    Opens in WAL mode with busy_timeout, cache, and temp_store.
    Yields the connection and closes it after the test.
    """
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA cache_size = -32000")
    conn.execute("PRAGMA temp_store = MEMORY")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA query_only = ON")
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture(scope="function")
def tmp_dir():
    """Temporary directory that auto-cleans after each test.

    Created inside 00_SYSTEM/tests/_tmp/ (never /tmp).
    """
    base = Path(__file__).parent / "_tmp"
    base.mkdir(exist_ok=True)
    d = tempfile.mkdtemp(dir=str(base))
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


# ── Custom markers ──────────────────────────────────────────────────────────

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (>5 seconds)")
    config.addinivalue_line("markers", "db: tests requiring litigation_context.db")
    config.addinivalue_line("markers", "engine: engine import tests")

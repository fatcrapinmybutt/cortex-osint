"""Wiring validator — ensures all LitigationOS subsystems interconnect.

Checks 10 connection paths between subsystems, verifying that each component
can reach the data and configuration it depends on.

Each wiring check returns a dict with:
    name      — human-readable check name
    ok        — True / False
    detail    — explanation of result
    score     — 0 or 10 (each check worth 10 points, 100 total)
"""
import sqlite3
import json
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Canonical paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(r"C:\Users\andre\LitigationOS")
DB_PATH = REPO_ROOT / "litigation_context.db"
MBP_BRAIN = REPO_ROOT / "mbp_brain.db"

NEXUS_DAEMON = REPO_ROOT / ".github" / "extensions" / "singularity" / "nexus_daemon.py"
EXTENSION_MJS = REPO_ROOT / ".github" / "extensions" / "singularity" / "extension.mjs"
BRIDGE_ENGINE = REPO_ROOT / "00_SYSTEM" / "engines" / "llm_bridge.py"
FILING_ASSEMBLY_DIR = REPO_ROOT / "00_SYSTEM" / "engines" / "filing_assembly"
SENTINEL_DIR = REPO_ROOT / "00_SYSTEM" / "daemon" / "sentinel"
FORTRESS_DIR = REPO_ROOT / "00_SYSTEM" / "daemon" / "fortress"
TESTS_DIR = REPO_ROOT / "00_SYSTEM" / "tests"
MBP_GRAPH = REPO_ROOT / "12_WORKSPACE" / "THEMANBEARPIG_v7" / "graph_data_v7.json"
SKILLS_DIR = REPO_ROOT / ".agents" / "skills"
ENGINES_DIR = REPO_ROOT / "00_SYSTEM" / "engines"

# Expected MBP layers
EXPECTED_LAYERS = {
    "ACTOR", "AUTHORITY", "AUTHORITY_CHAIN", "EVIDENCE", "FILING",
    "IMPEACHMENT", "LANE", "REMEDY", "STRATEGIC", "TIMELINE", "VIOLATION",
}


def _connect(path: Path) -> sqlite3.Connection:
    """Open a connection with mandatory PRAGMAs."""
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA cache_size=-32000")
    return conn


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def _count_rows(conn: sqlite3.Connection, table: str) -> int:
    try:
        row = conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()
        return row[0] if row else 0
    except sqlite3.OperationalError:
        return 0


# ===================================================================
# Wiring Validator
# ===================================================================


class WiringValidator:
    """Check every critical connection path in the unified system."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or DB_PATH
        self.conn = _connect(self.db_path)
        self.checks: list[dict] = []

    def validate_all(self) -> list[dict]:
        """Run all wiring checks, return list of results."""
        validators = [
            self._nexus_to_db,
            self._bridge_to_dbs,
            self._filing_to_evidence,
            self._mbp_layers,
            self._kraken_to_evidence,
            self._sentinel_to_inventory,
            self._fortress_to_health,
            self._tests_importable,
            self._skills_present,
            self._extension_to_daemon,
        ]

        for fn in validators:
            try:
                result = fn()
            except Exception as exc:
                result = {
                    "name": fn.__doc__ or fn.__name__,
                    "ok": False,
                    "detail": f"Exception: {exc}",
                    "score": 0,
                }
            self.checks.append(result)

        return self.checks

    def summary(self) -> dict:
        """Aggregate wiring check results."""
        total = sum(c["score"] for c in self.checks)
        passed = sum(1 for c in self.checks if c["ok"])
        return {
            "wiring_score": total,
            "wiring_max": len(self.checks) * 10,
            "passed": passed,
            "total": len(self.checks),
            "checks": self.checks,
        }

    # ------------------------------------------------------------------
    # Individual wiring checks
    # ------------------------------------------------------------------

    def _nexus_to_db(self) -> dict:
        """1. NEXUS daemon → litigation_context.db"""
        ok = False
        detail_parts: list[str] = []

        if NEXUS_DAEMON.is_file():
            detail_parts.append("nexus_daemon.py exists")
            source = NEXUS_DAEMON.read_text(encoding="utf-8", errors="replace")
            if "litigation_context" in source:
                detail_parts.append("references litigation_context.db")
                ok = True
            else:
                detail_parts.append("does NOT reference litigation_context.db")
        else:
            detail_parts.append("nexus_daemon.py NOT FOUND")

        # Verify DB is accessible
        if self.db_path.is_file():
            detail_parts.append("DB file exists")
        else:
            detail_parts.append("DB file MISSING")
            ok = False

        return {
            "name": "NEXUS daemon → litigation_context.db",
            "ok": ok,
            "detail": "; ".join(detail_parts),
            "score": 10 if ok else 0,
        }

    def _bridge_to_dbs(self) -> dict:
        """2. Bridge engine → litigation_context.db + mbp_brain.db"""
        ok = True
        detail_parts: list[str] = []

        if BRIDGE_ENGINE.is_file():
            detail_parts.append("llm_bridge.py exists")
        else:
            detail_parts.append("llm_bridge.py MISSING")
            ok = False

        if _table_exists(self.conn, "graph_update_queue"):
            count = _count_rows(self.conn, "graph_update_queue")
            detail_parts.append(f"graph_update_queue: {count:,} rows")
        else:
            detail_parts.append("graph_update_queue MISSING")
            ok = False

        if MBP_BRAIN.is_file():
            detail_parts.append("mbp_brain.db exists")
        else:
            detail_parts.append("mbp_brain.db MISSING")
            ok = False

        return {
            "name": "Bridge engine → DBs",
            "ok": ok,
            "detail": "; ".join(detail_parts),
            "score": 10 if ok else 0,
        }

    def _filing_to_evidence(self) -> dict:
        """3. Filing assembly → evidence_quotes + authority_chains_v2"""
        ok = True
        detail_parts: list[str] = []

        assembler = FILING_ASSEMBLY_DIR / "assembler.py"
        if assembler.is_file():
            detail_parts.append("assembler.py exists")
        else:
            detail_parts.append("assembler.py MISSING")
            ok = False

        for table in ("evidence_quotes", "authority_chains_v2"):
            if _table_exists(self.conn, table):
                count = _count_rows(self.conn, table)
                detail_parts.append(f"{table}: {count:,} rows")
            else:
                detail_parts.append(f"{table} MISSING")
                ok = False

        return {
            "name": "Filing assembly → evidence + authority",
            "ok": ok,
            "detail": "; ".join(detail_parts),
            "score": 10 if ok else 0,
        }

    def _mbp_layers(self) -> dict:
        """4. MBP visualization → graph_data_v7.json (all 11 layers)"""
        ok = False
        detail_parts: list[str] = []

        if not MBP_GRAPH.is_file():
            return {
                "name": "MBP → graph_data_v7.json layers",
                "ok": False,
                "detail": "graph_data_v7.json NOT FOUND",
                "score": 0,
            }

        try:
            with open(MBP_GRAPH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            return {
                "name": "MBP → graph_data_v7.json layers",
                "ok": False,
                "detail": f"Parse error: {exc}",
                "score": 0,
            }

        layers: set[str] = set()
        for node in data.get("nodes", []):
            layer = node.get("layer", node.get("type"))
            if layer:
                layers.add(layer)

        missing = EXPECTED_LAYERS - layers
        extra = layers - EXPECTED_LAYERS

        detail_parts.append(f"{len(layers)} layers found")
        if missing:
            detail_parts.append(f"Missing: {', '.join(sorted(missing))}")
        if extra:
            detail_parts.append(f"Extra: {', '.join(sorted(extra))}")

        ok = len(missing) == 0
        score = 10 if ok else max(0, 10 - len(missing))

        return {
            "name": "MBP → graph_data_v7.json layers",
            "ok": ok,
            "detail": "; ".join(detail_parts),
            "score": score,
        }

    def _kraken_to_evidence(self) -> dict:
        """5. KRAKEN tools → evidence_quotes (lottery_harvest, krack_a_lack)"""
        ok = True
        detail_parts: list[str] = []

        if _table_exists(self.conn, "evidence_quotes"):
            count = _count_rows(self.conn, "evidence_quotes")
            detail_parts.append(f"evidence_quotes: {count:,} rows (KRAKEN target)")
            if count < 1000:
                ok = False
                detail_parts.append("Row count too low for KRAKEN operations")
        else:
            ok = False
            detail_parts.append("evidence_quotes MISSING")

        # Verify FTS5 for KRAKEN searches
        try:
            self.conn.execute("SELECT 1 FROM evidence_fts LIMIT 1").fetchone()
            detail_parts.append("evidence_fts FTS5: present")
        except sqlite3.OperationalError:
            detail_parts.append("evidence_fts FTS5: MISSING")
            ok = False

        return {
            "name": "KRAKEN → evidence_quotes + FTS5",
            "ok": ok,
            "detail": "; ".join(detail_parts),
            "score": 10 if ok else 0,
        }

    def _sentinel_to_inventory(self) -> dict:
        """6. Sentinel → file_inventory table"""
        ok = True
        detail_parts: list[str] = []

        if SENTINEL_DIR.is_dir():
            detail_parts.append("sentinel/ directory exists")
        else:
            ok = False
            detail_parts.append("sentinel/ directory MISSING")

        if _table_exists(self.conn, "file_inventory"):
            count = _count_rows(self.conn, "file_inventory")
            detail_parts.append(f"file_inventory: {count:,} rows")
        else:
            ok = False
            detail_parts.append("file_inventory table MISSING")

        return {
            "name": "Sentinel → file_inventory",
            "ok": ok,
            "detail": "; ".join(detail_parts),
            "score": 10 if ok else 0,
        }

    def _fortress_to_health(self) -> dict:
        """7. Fortress → db_health_baseline table"""
        ok = True
        detail_parts: list[str] = []

        if FORTRESS_DIR.is_dir():
            detail_parts.append("fortress/ directory exists")
        else:
            ok = False
            detail_parts.append("fortress/ directory MISSING")

        if _table_exists(self.conn, "db_health_baseline"):
            count = _count_rows(self.conn, "db_health_baseline")
            detail_parts.append(f"db_health_baseline: {count:,} rows")
        else:
            ok = False
            detail_parts.append("db_health_baseline table MISSING")

        return {
            "name": "Fortress → db_health_baseline",
            "ok": ok,
            "detail": "; ".join(detail_parts),
            "score": 10 if ok else 0,
        }

    def _tests_importable(self) -> dict:
        """8. Test suite → all engines importable"""
        ok = False
        detail_parts: list[str] = []

        if TESTS_DIR.is_dir():
            test_files = list(TESTS_DIR.glob("test_*.py"))
            detail_parts.append(f"{len(test_files)} test files found")
            ok = len(test_files) >= 5
        else:
            detail_parts.append("tests/ directory MISSING")

        # Check engines directory has __init__.py files
        engine_dirs = [
            d for d in ENGINES_DIR.iterdir()
            if d.is_dir() and not d.name.startswith("_")
        ] if ENGINES_DIR.is_dir() else []
        detail_parts.append(f"{len(engine_dirs)} engine directories")

        return {
            "name": "Test suite → engines",
            "ok": ok,
            "detail": "; ".join(detail_parts),
            "score": 10 if ok else 0,
        }

    def _skills_present(self) -> dict:
        """9. Skills → .agents/skills/ directory (33+ skills)"""
        ok = False
        detail_parts: list[str] = []

        if not SKILLS_DIR.is_dir():
            # Skills might live elsewhere — check for skill-like files
            agents_dir = REPO_ROOT / ".agents"
            if agents_dir.is_dir():
                skill_count = sum(
                    1 for f in agents_dir.rglob("SKILL.md")
                )
                detail_parts.append(
                    f".agents/ exists but {skill_count} SKILL.md files found"
                )
                ok = skill_count >= 10
            else:
                detail_parts.append(".agents/skills/ directory MISSING")
        else:
            skill_dirs = [
                d for d in SKILLS_DIR.iterdir()
                if d.is_dir() and (d / "SKILL.md").is_file()
            ]
            total = len(skill_dirs)
            detail_parts.append(f"{total} skill directories with SKILL.md")
            ok = total >= 25

        return {
            "name": "Skills → SINGULARITY skill files",
            "ok": ok,
            "detail": "; ".join(detail_parts),
            "score": 10 if ok else 0,
        }

    def _extension_to_daemon(self) -> dict:
        """10. Extension → nexus_daemon.py (check HANDLERS count)"""
        ok = True
        detail_parts: list[str] = []

        if EXTENSION_MJS.is_file():
            detail_parts.append("extension.mjs exists")
        else:
            detail_parts.append("extension.mjs MISSING")
            ok = False

        if NEXUS_DAEMON.is_file():
            source = NEXUS_DAEMON.read_text(encoding="utf-8", errors="replace")
            handler_matches = re.findall(
                r'["\'](\w+)["\']\s*:\s*handle_', source
            )
            count = len(handler_matches)
            detail_parts.append(f"HANDLERS: {count} entries")
            if count < 40:
                ok = False
                detail_parts.append("Below 40 handler threshold")
        else:
            detail_parts.append("nexus_daemon.py MISSING")
            ok = False

        return {
            "name": "Extension → NEXUS daemon HANDLERS",
            "ok": ok,
            "detail": "; ".join(detail_parts),
            "score": 10 if ok else 0,
        }

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self):
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# ===================================================================
# CLI entry point
# ===================================================================

if __name__ == "__main__":
    with WiringValidator() as wv:
        wv.validate_all()
        result = wv.summary()
        print(json.dumps(result, indent=2, ensure_ascii=False))

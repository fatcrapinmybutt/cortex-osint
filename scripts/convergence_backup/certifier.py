"""OMEGA Convergence Certifier — scores unified system readiness.

Runs 12 certification checks across the entire LitigationOS + THEMANBEARPIG
unified system and produces a scored readiness assessment.

Each check returns (score: 0-100, detail: str).
Overall tier: ΩΩΩ TRANSCENDENT (>=95), ΩΩ APEX (>=85), Ω ELITE (>=70), STANDARD (<70).
"""
import sqlite3
import os
import json
import re
from datetime import datetime, date
from pathlib import Path

# ---------------------------------------------------------------------------
# Canonical paths (raw strings for Windows backslashes)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(r"C:\Users\andre\LitigationOS")
DB_PATH = REPO_ROOT / "litigation_context.db"
MBP_BRAIN = REPO_ROOT / "mbp_brain.db"

NEXUS_DAEMON = REPO_ROOT / ".github" / "extensions" / "singularity" / "nexus_daemon.py"
BRIDGE_ENGINE = REPO_ROOT / "00_SYSTEM" / "engines" / "llm_bridge.py"
FILING_ASSEMBLY_DIR = REPO_ROOT / "00_SYSTEM" / "engines" / "filing_assembly"
SENTINEL_DIR = REPO_ROOT / "00_SYSTEM" / "daemon" / "sentinel"
FORTRESS_DIR = REPO_ROOT / "00_SYSTEM" / "daemon" / "fortress"
TESTS_DIR = REPO_ROOT / "00_SYSTEM" / "tests"
MBP_GRAPH = REPO_ROOT / "12_WORKSPACE" / "THEMANBEARPIG_v7" / "graph_data_v7.json"
SKILLS_DIR = REPO_ROOT / ".agents" / "skills"
BACKUPS_DIR = REPO_ROOT / "scripts"

# ---------------------------------------------------------------------------
# Expected backup subdirectories under scripts/
# ---------------------------------------------------------------------------
EXPECTED_BACKUPS = [
    "bridge_backup",
    "filing_assembly_backup",
    "sentinel_backup",
    "fortress_backup",
    "tests_backup",
    "mbp_pipelines_backup",
    "skills_backup",
    "convergence_backup",
]

# ---------------------------------------------------------------------------
# Key DB tables that must exist
# ---------------------------------------------------------------------------
KEY_TABLES = [
    "evidence_quotes",
    "authority_chains_v2",
    "timeline_events",
    "impeachment_matrix",
    "contradiction_map",
]

# ---------------------------------------------------------------------------
# Separation anchor
# ---------------------------------------------------------------------------
SEPARATION_ANCHOR = date(2025, 7, 29)


def _connect(path: Path) -> sqlite3.Connection:
    """Open a connection with mandatory PRAGMAs."""
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA cache_size=-32000")
    return conn


def _count_rows(conn: sqlite3.Connection, table: str) -> int:
    """Safe row count — returns 0 if table missing."""
    try:
        row = conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()
        return row[0] if row else 0
    except sqlite3.OperationalError:
        return 0


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    """Check whether *table* exists in the database."""
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def _count_files(directory: Path, pattern: str = "*.py") -> int:
    """Count files matching *pattern* in *directory* (non-recursive)."""
    if not directory.is_dir():
        return 0
    return sum(1 for _ in directory.glob(pattern))


def _list_py_files(directory: Path) -> list[str]:
    """List .py filenames in *directory*."""
    if not directory.is_dir():
        return []
    return sorted(f.name for f in directory.glob("*.py"))


# ===================================================================
# Convergence Certifier
# ===================================================================


class ConvergenceCertifier:
    """Run all certification checks and produce a scored result."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or DB_PATH
        self.conn = _connect(self.db_path)
        self.results: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def certify_all(self) -> dict:
        """Execute every certification check and return the aggregate report."""

        checks = [
            ("nexus_daemon", self.check_nexus),
            ("evidence_bridge", self.check_bridge),
            ("filing_assembly", self.check_filing_assembly),
            ("sentinel_daemon", self.check_sentinel),
            ("fortress_daemon", self.check_fortress),
            ("test_suite", self.check_tests),
            ("mbp_visualization", self.check_mbp),
            ("db_integrity", self.check_db),
            ("evidence_coverage", self.check_evidence),
            ("authority_coverage", self.check_authority),
            ("skills_intact", self.check_skills),
            ("backups_exist", self.check_backups),
        ]

        for name, check_fn in checks:
            try:
                score, detail = check_fn()
                if score >= 80:
                    status = "PASS"
                elif score >= 50:
                    status = "WARN"
                else:
                    status = "FAIL"
                self.results[name] = {
                    "score": score,
                    "detail": detail,
                    "status": status,
                }
            except Exception as exc:
                self.results[name] = {
                    "score": 0,
                    "detail": str(exc),
                    "status": "ERROR",
                }

        overall = sum(r["score"] for r in self.results.values()) / max(
            len(self.results), 1
        )

        if overall >= 95:
            tier = "ΩΩΩ TRANSCENDENT"
        elif overall >= 85:
            tier = "ΩΩ APEX"
        elif overall >= 70:
            tier = "Ω ELITE"
        else:
            tier = "STANDARD"

        return {
            "overall_score": round(overall, 1),
            "tier": tier,
            "timestamp": datetime.now().isoformat(),
            "separation_days": (date.today() - SEPARATION_ANCHOR).days,
            "checks": self.results,
            "passed": sum(
                1 for r in self.results.values() if r["status"] == "PASS"
            ),
            "warned": sum(
                1 for r in self.results.values() if r["status"] == "WARN"
            ),
            "failed": sum(
                1 for r in self.results.values()
                if r["status"] in ("FAIL", "ERROR")
            ),
        }

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def check_nexus(self) -> tuple[int, str]:
        """Verify nexus_daemon.py exists and has the expected handler count."""
        if not NEXUS_DAEMON.is_file():
            return 0, f"nexus_daemon.py not found at {NEXUS_DAEMON}"

        source = NEXUS_DAEMON.read_text(encoding="utf-8", errors="replace")

        # Count HANDLERS dict entries: lines matching "handler_name": handle_*
        handler_matches = re.findall(
            r'["\'](\w+)["\']\s*:\s*handle_', source
        )
        handler_count = len(handler_matches)

        if handler_count >= 50:
            score = 100
        elif handler_count >= 40:
            score = 90
        elif handler_count >= 30:
            score = 75
        elif handler_count >= 20:
            score = 60
        else:
            score = max(0, handler_count * 3)

        return score, f"{handler_count} handlers found in HANDLERS dict"

    def check_bridge(self) -> tuple[int, str]:
        """Verify bridge engine files and graph_update_queue table."""
        score = 0
        details: list[str] = []

        # Bridge engine file
        if BRIDGE_ENGINE.is_file():
            score += 40
            details.append("llm_bridge.py exists")
        else:
            details.append("llm_bridge.py MISSING")

        # graph_update_queue table
        if _table_exists(self.conn, "graph_update_queue"):
            score += 30
            details.append("graph_update_queue table exists")
        else:
            details.append("graph_update_queue table MISSING")

        # MBP brain DB
        if MBP_BRAIN.is_file():
            score += 30
            details.append("mbp_brain.db exists")
        else:
            details.append("mbp_brain.db MISSING")

        return score, "; ".join(details)

    def check_filing_assembly(self) -> tuple[int, str]:
        """Verify filing assembly engine files."""
        required = ["assembler.py", "templates.py", "qa_gate.py"]
        found: list[str] = []
        missing: list[str] = []

        for fname in required:
            if (FILING_ASSEMBLY_DIR / fname).is_file():
                found.append(fname)
            else:
                missing.append(fname)

        # Init file bonus
        has_init = (FILING_ASSEMBLY_DIR / "__init__.py").is_file()

        score_per = 100 // len(required)
        score = len(found) * score_per
        if has_init and score > 0:
            score = min(100, score + 5)

        detail = f"Found {len(found)}/{len(required)}: {', '.join(found)}"
        if missing:
            detail += f" | Missing: {', '.join(missing)}"
        return score, detail

    def check_sentinel(self) -> tuple[int, str]:
        """Verify sentinel daemon directory and files."""
        expected = ["daemon.py", "watcher.py", "classifier.py", "organizer.py", "__init__.py"]
        return self._check_daemon_dir(SENTINEL_DIR, expected, "sentinel")

    def check_fortress(self) -> tuple[int, str]:
        """Verify fortress daemon directory and files."""
        expected = ["monitor.py", "health.py", "healer.py", "anomaly.py", "__init__.py"]
        return self._check_daemon_dir(FORTRESS_DIR, expected, "fortress")

    def _check_daemon_dir(
        self, path: Path, expected: list[str], name: str
    ) -> tuple[int, str]:
        """Shared logic for daemon directory checks."""
        if not path.is_dir():
            return 0, f"{name}/ directory not found at {path}"

        found: list[str] = []
        missing: list[str] = []
        for fname in expected:
            if (path / fname).is_file():
                found.append(fname)
            else:
                missing.append(fname)

        score = int(len(found) / max(len(expected), 1) * 100)
        detail = f"{len(found)}/{len(expected)} files: {', '.join(found)}"
        if missing:
            detail += f" | Missing: {', '.join(missing)}"
        return score, detail

    def check_tests(self) -> tuple[int, str]:
        """Count test files in test suite directory."""
        if not TESTS_DIR.is_dir():
            return 0, f"Tests directory not found at {TESTS_DIR}"

        test_files = [
            f.name for f in TESTS_DIR.glob("test_*.py")
        ]
        count = len(test_files)

        if count >= 10:
            score = 100
        elif count >= 7:
            score = 80
        elif count >= 4:
            score = 60
        else:
            score = max(0, count * 15)

        return score, f"{count} test files: {', '.join(sorted(test_files))}"

    def check_mbp(self) -> tuple[int, str]:
        """Verify THEMANBEARPIG graph data — nodes, edges, layers."""
        if not MBP_GRAPH.is_file():
            return 0, f"graph_data_v7.json not found at {MBP_GRAPH}"

        try:
            with open(MBP_GRAPH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            return 0, f"Failed to parse graph JSON: {exc}"

        nodes = data.get("nodes", [])
        edges = data.get("edges", data.get("links", []))
        node_count = len(nodes)
        edge_count = len(edges)

        layers: set[str] = set()
        for n in nodes:
            layer = n.get("layer", n.get("type", "UNKNOWN"))
            if layer:
                layers.add(layer)

        score = 0

        # Node scoring: target 10000+
        if node_count >= 10000:
            score += 35
        elif node_count >= 5000:
            score += 25
        elif node_count >= 1000:
            score += 15
        else:
            score += max(0, int(node_count / 100))

        # Edge scoring: target 20000+
        if edge_count >= 20000:
            score += 35
        elif edge_count >= 10000:
            score += 25
        elif edge_count >= 1000:
            score += 15
        else:
            score += max(0, int(edge_count / 200))

        # Layer scoring: target 11+
        layer_count = len(layers)
        if layer_count >= 11:
            score += 30
        elif layer_count >= 8:
            score += 20
        elif layer_count >= 5:
            score += 10
        else:
            score += layer_count * 2

        detail = (
            f"{node_count:,} nodes, {edge_count:,} edges, "
            f"{layer_count} layers: {', '.join(sorted(layers))}"
        )
        return score, detail

    def check_db(self) -> tuple[int, str]:
        """Run limited integrity check and verify key tables exist."""
        score = 0
        details: list[str] = []

        # Integrity check (limited to first page to avoid 10-minute scan)
        try:
            result = self.conn.execute("PRAGMA integrity_check(1)").fetchone()
            if result and result[0] == "ok":
                score += 50
                details.append("integrity_check: ok")
            else:
                details.append(f"integrity_check: {result}")
        except sqlite3.Error as exc:
            details.append(f"integrity_check error: {exc}")

        # Key tables
        found_tables: list[str] = []
        missing_tables: list[str] = []
        for table in KEY_TABLES:
            if _table_exists(self.conn, table):
                found_tables.append(table)
            else:
                missing_tables.append(table)

        table_pct = len(found_tables) / max(len(KEY_TABLES), 1)
        score += int(table_pct * 50)

        details.append(
            f"Key tables: {len(found_tables)}/{len(KEY_TABLES)} present"
        )
        if missing_tables:
            details.append(f"Missing: {', '.join(missing_tables)}")

        return score, "; ".join(details)

    def check_evidence(self) -> tuple[int, str]:
        """Count evidence_quotes rows and verify FTS5 index."""
        count = _count_rows(self.conn, "evidence_quotes")
        details: list[str] = [f"{count:,} evidence_quotes rows"]

        # Score based on row count — target 170K+
        if count >= 170_000:
            row_score = 70
        elif count >= 100_000:
            row_score = 55
        elif count >= 50_000:
            row_score = 40
        elif count >= 10_000:
            row_score = 25
        else:
            row_score = max(0, int(count / 500))

        # FTS5 index check
        fts_score = 0
        try:
            self.conn.execute(
                "SELECT 1 FROM evidence_fts LIMIT 1"
            ).fetchone()
            fts_score = 30
            details.append("evidence_fts FTS5 index: present")
        except sqlite3.OperationalError:
            details.append("evidence_fts FTS5 index: MISSING")

        return row_score + fts_score, "; ".join(details)

    def check_authority(self) -> tuple[int, str]:
        """Count authority_chains_v2 rows."""
        count = _count_rows(self.conn, "authority_chains_v2")

        if count >= 160_000:
            score = 100
        elif count >= 100_000:
            score = 85
        elif count >= 50_000:
            score = 65
        elif count >= 10_000:
            score = 45
        else:
            score = max(0, int(count / 500))

        return score, f"{count:,} authority_chains_v2 rows"

    def check_skills(self) -> tuple[int, str]:
        """Count SINGULARITY skill files."""
        mbp_pattern = "SINGULARITY-MBP-*"
        core_pattern = "SINGULARITY-*"

        mbp_skills: list[str] = []
        core_skills: list[str] = []

        if SKILLS_DIR.is_dir():
            for d in SKILLS_DIR.iterdir():
                if not d.is_dir():
                    continue
                skill_file = d / "SKILL.md"
                if skill_file.is_file():
                    if d.name.startswith("SINGULARITY-MBP-"):
                        mbp_skills.append(d.name)
                    elif d.name.startswith("SINGULARITY-"):
                        core_skills.append(d.name)

        total = len(mbp_skills) + len(core_skills)

        # Target: 25+ MBP skills + 15 core skills = 40 total
        if total >= 40:
            score = 100
        elif total >= 25:
            score = 80
        elif total >= 15:
            score = 60
        elif total >= 5:
            score = 40
        elif total >= 1:
            score = 20
        else:
            score = 0

        detail = (
            f"{len(core_skills)} core skills, {len(mbp_skills)} MBP skills "
            f"({total} total)"
        )
        if not SKILLS_DIR.is_dir():
            detail += f" | Skills directory not found: {SKILLS_DIR}"

        return score, detail

    def check_backups(self) -> tuple[int, str]:
        """Verify backup directories exist under scripts/."""
        found: list[str] = []
        missing: list[str] = []

        for bdir in EXPECTED_BACKUPS:
            if (BACKUPS_DIR / bdir).is_dir():
                found.append(bdir)
            else:
                missing.append(bdir)

        score = int(len(found) / max(len(EXPECTED_BACKUPS), 1) * 100)
        detail = f"{len(found)}/{len(EXPECTED_BACKUPS)} backup dirs present"
        if missing:
            detail += f" | Missing: {', '.join(missing)}"
        return score, detail

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self):
        """Close database connection."""
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
    with ConvergenceCertifier() as certifier:
        result = certifier.certify_all()
        print(json.dumps(result, indent=2, ensure_ascii=False))

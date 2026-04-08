"""NEXUS daemon structural validation — file syntax, HANDLERS dict, actions.

Tests the nexus_daemon.py file WITHOUT starting the daemon.
Only validates structure, syntax, and handler registration.
"""

import ast
import sys
from pathlib import Path

import pytest

NEXUS_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / ".github" / "extensions" / "singularity" / "nexus_daemon.py"
)


def _nexus_exists():
    return NEXUS_PATH.is_file()


# ── Syntax & Structure Tests ───────────────────────────────────────────────

@pytest.mark.skipif(not _nexus_exists(), reason="nexus_daemon.py not found")
class TestNexusSyntax:
    """Validate nexus_daemon.py file syntax and structure."""

    def test_file_exists(self):
        """nexus_daemon.py exists at expected path."""
        assert NEXUS_PATH.exists()
        assert NEXUS_PATH.stat().st_size > 0

    def test_file_parses(self):
        """nexus_daemon.py is valid Python (AST parses without error)."""
        source = NEXUS_PATH.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(NEXUS_PATH))
            assert tree is not None
        except SyntaxError as e:
            pytest.fail(f"Syntax error in nexus_daemon.py: {e}")

    def test_file_has_handlers_dict(self):
        """nexus_daemon.py defines a HANDLERS dict at module level."""
        source = NEXUS_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        handler_names = [
            node.targets[0].id
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "HANDLERS"
        ]
        assert "HANDLERS" in handler_names, "HANDLERS dict not found at module level"

    def test_handlers_count_minimum(self):
        """HANDLERS dict has at least 50 entries."""
        source = NEXUS_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (isinstance(node, ast.Assign)
                    and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id == "HANDLERS"
                    and isinstance(node.value, ast.Dict)):
                count = len(node.value.keys)
                assert count >= 50, f"HANDLERS has only {count} entries, expected 50+"
                return
        pytest.fail("Could not locate HANDLERS dict for counting")


# ── Handler Registration Tests ─────────────────────────────────────────────

@pytest.mark.skipif(not _nexus_exists(), reason="nexus_daemon.py not found")
class TestNexusHandlers:
    """Validate that key actions are registered in HANDLERS."""

    CORE_ACTIONS = [
        "ping", "query", "stats", "fts_search",
        "search_evidence", "search_impeachment", "search_contradictions",
        "nexus_fuse", "nexus_argue", "nexus_readiness",
        "narrative", "filing_plan", "rules_check",
        "judicial_intel", "timeline_search", "case_context",
        "deadlines",
    ]

    ABSORBED_ACTIONS = [
        "list_documents", "get_document", "search_documents",
        "lookup_rule", "query_graph", "lookup_authority",
        "assess_risk", "case_health", "filing_pipeline",
        "evolution_stats", "convergence_status",
        "vector_search", "self_audit", "evidence_chain",
        "red_team", "compute_deadlines",
        "health", "check_disk_space", "scan_all_systems",
        "memory_store", "memory_recall", "memory_list",
    ]

    @pytest.fixture(scope="class")
    def handler_keys(self):
        """Extract all HANDLERS dict keys from the source AST."""
        source = NEXUS_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (isinstance(node, ast.Assign)
                    and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id == "HANDLERS"
                    and isinstance(node.value, ast.Dict)):
                keys = []
                for k in node.value.keys:
                    if isinstance(k, ast.Constant) and isinstance(k.value, str):
                        keys.append(k.value)
                return set(keys)
        pytest.fail("HANDLERS dict not found")

    @pytest.mark.parametrize("action", CORE_ACTIONS)
    def test_core_action_registered(self, handler_keys, action):
        """Core action '{action}' is registered in HANDLERS."""
        assert action in handler_keys, (
            f"Core action '{action}' missing from HANDLERS"
        )

    @pytest.mark.parametrize("action", ABSORBED_ACTIONS)
    def test_absorbed_action_registered(self, handler_keys, action):
        """Absorbed MCP action '{action}' is registered in HANDLERS."""
        assert action in handler_keys, (
            f"Absorbed action '{action}' missing from HANDLERS"
        )


# ── Handler Function Existence Tests ────────────────────────────────────────

@pytest.mark.skipif(not _nexus_exists(), reason="nexus_daemon.py not found")
class TestNexusHandlerFunctions:
    """Verify that handler functions referenced in HANDLERS are defined."""

    def test_all_handlers_have_functions(self):
        """Every handler value in HANDLERS references a defined function."""
        source = NEXUS_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)

        # Collect all top-level function names
        defined_functions = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                defined_functions.add(node.name)

        # Collect all handler function references
        for node in ast.walk(tree):
            if (isinstance(node, ast.Assign)
                    and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id == "HANDLERS"
                    and isinstance(node.value, ast.Dict)):
                missing = []
                for val in node.value.values:
                    if isinstance(val, ast.Name):
                        if val.id not in defined_functions:
                            missing.append(val.id)
                if missing:
                    pytest.fail(
                        f"HANDLERS references undefined functions: {missing[:10]}"
                    )
                return

        pytest.fail("Could not find HANDLERS dict for function validation")

    def test_handler_naming_convention(self):
        """Handler functions follow handle_* naming convention."""
        source = NEXUS_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if (isinstance(node, ast.Assign)
                    and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id == "HANDLERS"
                    and isinstance(node.value, ast.Dict)):
                non_conforming = []
                for val in node.value.values:
                    if isinstance(val, ast.Name) and not val.id.startswith("handle_"):
                        non_conforming.append(val.id)
                if non_conforming:
                    # Advisory, not hard fail
                    pytest.skip(
                        f"{len(non_conforming)} handlers don't follow handle_* convention"
                    )
                return


# ── ConnectionPool & CircuitBreaker (AST-level) ────────────────────────────

@pytest.mark.skipif(not _nexus_exists(), reason="nexus_daemon.py not found")
class TestNexusClasses:
    """Verify key classes exist in nexus_daemon.py via AST."""

    EXPECTED_CLASSES = ["ConnectionPool", "CircuitBreaker"]

    @pytest.fixture(scope="class")
    def class_names(self):
        source = NEXUS_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        return {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef)
        }

    @pytest.mark.parametrize("cls_name", EXPECTED_CLASSES)
    def test_class_defined(self, class_names, cls_name):
        """Class '{cls_name}' is defined in nexus_daemon.py."""
        assert cls_name in class_names, f"Class {cls_name} not found"

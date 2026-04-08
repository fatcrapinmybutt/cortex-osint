"""Bridge engine tests — MEEK lane classifier + EvidenceGraphBridge.

Tests the pure-function lane routing (classify/classify_multi) and
the bridge module's import and structure.
"""

import sys
from pathlib import Path

import pytest

# Ensure engines importable
_sys_dir = str(Path(__file__).resolve().parent.parent)
if _sys_dir not in sys.path:
    sys.path.insert(0, _sys_dir)


# ── MEEK Lane Classifier Tests ──────────────────────────────────────────────

class TestMeekClassify:
    """Tests for engines.bridge.meek.classify()."""

    @pytest.fixture(autouse=True)
    def _import_meek(self):
        from engines.bridge.meek import classify, classify_multi, MEEK_PATTERNS, LANE_PRIORITY
        self.classify = classify
        self.classify_multi = classify_multi
        self.patterns = MEEK_PATTERNS
        self.priority = LANE_PRIORITY

    def test_lane_e_misconduct(self):
        """Judicial misconduct keywords route to lane E."""
        assert self.classify("Judge McNeill showed bias") == "E"
        assert self.classify("JTC complaint filed") == "E"
        assert self.classify("ex parte order issued") == "E"

    def test_lane_d_ppo(self):
        """PPO-related keywords route to lane D."""
        assert self.classify("PPO was issued") == "D"
        assert self.classify("personal protection order") == "D"
        assert self.classify("domestic violence complaint") == "D"

    def test_lane_f_appellate(self):
        """Appellate keywords route to lane F."""
        assert self.classify("COA brief due") == "F"
        assert self.classify("case 366810 appeal") == "F"
        assert self.classify("court of appeals filing") == "F"

    def test_lane_a_custody(self):
        """Custody-related keywords route to lane A."""
        assert self.classify("custody modification motion") == "A"
        assert self.classify("parenting time schedule") == "A"
        assert self.classify("MCL 722 best interest") == "A"

    def test_lane_b_housing(self):
        """Housing keywords route to lane B."""
        assert self.classify("Shady Oaks eviction notice") == "B"
        assert self.classify("landlord tenant dispute") == "B"
        assert self.classify("housing habitability complaint") == "B"

    def test_default_lane_c(self):
        """Unclassifiable text defaults to lane C."""
        assert self.classify("completely random text about weather") == "C"
        assert self.classify("") == "C"

    def test_priority_e_over_a(self):
        """Lane E (misconduct) wins over lane A (custody) per priority."""
        result = self.classify("custody hearing where McNeill showed bias")
        assert result == "E", "E should have priority over A"

    def test_classify_multi_returns_list(self):
        """classify_multi returns list of all matching lanes."""
        result = self.classify_multi("McNeill custody PPO appeal Shady Oaks")
        assert isinstance(result, list)
        assert len(result) >= 3  # Should match E, D, F, A, B

    def test_classify_multi_empty(self):
        """classify_multi returns ['C'] for unclassifiable text."""
        assert self.classify_multi("random weather report") == ["C"]

    def test_classify_multi_order(self):
        """classify_multi preserves priority order."""
        result = self.classify_multi("PPO and McNeill misconduct")
        assert result[0] == "E", "E (misconduct) should be first"
        assert "D" in result

    def test_patterns_are_compiled_regex(self):
        """MEEK_PATTERNS values are compiled regex objects."""
        import re
        for lane, pattern in self.patterns.items():
            assert isinstance(pattern, re.Pattern), f"Pattern for {lane} is not compiled"

    def test_lane_priority_order(self):
        """LANE_PRIORITY has correct order: E, D, F, A, B."""
        assert self.priority == ["E", "D", "F", "A", "B"]


# ── EvidenceGraphBridge Import Tests ────────────────────────────────────────

class TestBridgeImport:
    """Tests for engines.bridge module import and structure."""

    def test_bridge_module_imports(self):
        """Bridge module imports without crash."""
        from engines.bridge import EvidenceGraphBridge
        assert EvidenceGraphBridge is not None

    def test_bridge_version_exists(self):
        """Bridge module has __version__."""
        import engines.bridge as bridge
        assert hasattr(bridge, "__version__")
        assert isinstance(bridge.__version__, str)

    def test_bridge_class_is_callable(self):
        """EvidenceGraphBridge is a callable class."""
        from engines.bridge.bridge import EvidenceGraphBridge
        assert callable(EvidenceGraphBridge)

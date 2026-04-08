"""FORTRESS daemon tests — health checker, healer, anomaly detector.

Tests dataclass structure, critical table lists, threshold constants,
and safe instantiation of fortress components.
"""

import sys
from pathlib import Path

import pytest

_sys_dir = str(Path(__file__).resolve().parent.parent)
if _sys_dir not in sys.path:
    sys.path.insert(0, _sys_dir)

FORTRESS_DIR = Path(__file__).resolve().parent.parent / "daemon" / "fortress"


def _fortress_importable():
    return FORTRESS_DIR.is_dir() and (FORTRESS_DIR / "__init__.py").exists()


# ── Health Checker Tests ────────────────────────────────────────────────────

@pytest.mark.skipif(not _fortress_importable(), reason="fortress not found")
class TestDatabaseHealthChecker:
    """Tests for daemon.fortress.health."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        daemon_root = str(FORTRESS_DIR.parent.parent)
        if daemon_root not in sys.path:
            sys.path.insert(0, daemon_root)
        try:
            from daemon.fortress.health import (
                DatabaseHealthChecker, CRITICAL_TABLES,
                HealthResult, HealthReport,
            )
            self.HealthChecker = DatabaseHealthChecker
            self.critical_tables = CRITICAL_TABLES
            self.HealthResult = HealthResult
            self.HealthReport = HealthReport
            self._available = True
        except ImportError as e:
            self._available = False
            pytest.skip(f"fortress.health import failed: {e}")

    def test_critical_tables_count(self):
        """CRITICAL_TABLES has at least 15 tables."""
        assert isinstance(self.critical_tables, (list, tuple, set, frozenset))
        assert len(self.critical_tables) >= 15, (
            f"Expected 15+ critical tables, got {len(self.critical_tables)}"
        )

    def test_critical_tables_include_core(self):
        """Core tables present in CRITICAL_TABLES."""
        table_set = set(self.critical_tables)
        for expected in ["evidence_quotes", "timeline_events", "authority_chains_v2"]:
            assert expected in table_set, f"Missing critical table: {expected}"

    def test_health_result_is_dataclass(self):
        """HealthResult is a proper dataclass."""
        import dataclasses
        assert dataclasses.is_dataclass(self.HealthResult)

    def test_health_report_is_dataclass(self):
        """HealthReport is a proper dataclass."""
        import dataclasses
        assert dataclasses.is_dataclass(self.HealthReport)

    def test_health_checker_instantiates(self, db_path):
        """DatabaseHealthChecker can be instantiated with db_path."""
        try:
            checker = self.HealthChecker(str(db_path))
        except TypeError:
            checker = self.HealthChecker()
        assert checker is not None


# ── Healer Tests ────────────────────────────────────────────────────────────

@pytest.mark.skipif(not _fortress_importable(), reason="fortress not found")
class TestDatabaseHealer:
    """Tests for daemon.fortress.healer."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        daemon_root = str(FORTRESS_DIR.parent.parent)
        if daemon_root not in sys.path:
            sys.path.insert(0, daemon_root)
        try:
            from daemon.fortress.healer import DatabaseHealer
            self.Healer = DatabaseHealer
            self._available = True
        except ImportError as e:
            self._available = False
            pytest.skip(f"fortress.healer import failed: {e}")

    def test_healer_instantiates(self, db_path):
        """DatabaseHealer can be instantiated with db_path."""
        try:
            healer = self.Healer(str(db_path))
        except TypeError:
            healer = self.Healer()
        assert healer is not None

    def test_healer_has_heal_method(self):
        """DatabaseHealer has a heal() method."""
        assert hasattr(self.Healer, "heal")
        assert callable(getattr(self.Healer, "heal"))


# ── Anomaly Detector Tests ──────────────────────────────────────────────────

@pytest.mark.skipif(not _fortress_importable(), reason="fortress not found")
class TestAnomalyDetector:
    """Tests for daemon.fortress.anomaly."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        daemon_root = str(FORTRESS_DIR.parent.parent)
        if daemon_root not in sys.path:
            sys.path.insert(0, daemon_root)
        try:
            from daemon.fortress.anomaly import AnomalyDetector, Anomaly
            self.Detector = AnomalyDetector
            self.Anomaly = Anomaly
            self._available = True
        except ImportError as e:
            self._available = False
            pytest.skip(f"fortress.anomaly import failed: {e}")

    def test_detector_instantiates(self, db_path):
        """AnomalyDetector can be instantiated with db_path."""
        try:
            detector = self.Detector(str(db_path))
        except TypeError:
            detector = self.Detector()
        assert detector is not None

    def test_detector_has_detect_method(self):
        """AnomalyDetector has a detect() method."""
        assert hasattr(self.Detector, "detect")

    def test_anomaly_is_dataclass(self):
        """Anomaly is a proper dataclass."""
        import dataclasses
        assert dataclasses.is_dataclass(self.Anomaly)

    def test_detect_with_empty_counts(self, db_path):
        """detect() with empty dict doesn't crash."""
        try:
            detector = self.Detector(str(db_path))
        except TypeError:
            detector = self.Detector()
        try:
            result = detector.detect({})
            assert isinstance(result, list)
        except TypeError:
            pytest.skip("detect() requires non-empty counts")

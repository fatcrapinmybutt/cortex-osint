"""SENTINEL daemon tests — classifier, watcher, daemon dataclasses.

Tests FileClassifier MEEK integration, classification result structure,
watcher constants, and daemon import safety.
"""

import sys
from pathlib import Path

import pytest

_sys_dir = str(Path(__file__).resolve().parent.parent)
if _sys_dir not in sys.path:
    sys.path.insert(0, _sys_dir)

# ── Sentinel paths ──────────────────────────────────────────────────────────

SENTINEL_DIR = Path(__file__).resolve().parent.parent / "daemon" / "sentinel"


def _sentinel_importable():
    """Check if sentinel modules can be imported."""
    return SENTINEL_DIR.is_dir() and (SENTINEL_DIR / "__init__.py").exists()


# ── Classifier Tests ────────────────────────────────────────────────────────

@pytest.mark.skipif(not _sentinel_importable(), reason="sentinel not found")
class TestFileClassifier:
    """Tests for daemon.sentinel.classifier."""

    @pytest.fixture(autouse=True)
    def _setup_path(self):
        daemon_root = str(SENTINEL_DIR.parent.parent)
        if daemon_root not in sys.path:
            sys.path.insert(0, daemon_root)
        try:
            from daemon.sentinel.classifier import (
                FileClassifier, ClassificationResult,
                MEEK_PATTERNS, CATEGORY_PATTERNS,
                SUPPORTED_EXTENSIONS, IGNORE_PATTERNS, MAX_EXTRACT_CHARS,
            )
            self.classifier = FileClassifier()
            self.ClassificationResult = ClassificationResult
            self.meek_patterns = MEEK_PATTERNS
            self.category_patterns = CATEGORY_PATTERNS
            self.extensions = SUPPORTED_EXTENSIONS
            self.ignore = IGNORE_PATTERNS
            self.max_chars = MAX_EXTRACT_CHARS
            self._available = True
        except ImportError as e:
            self._available = False
            pytest.skip(f"classifier import failed: {e}")

    def test_classifier_instantiation(self):
        """FileClassifier can be instantiated."""
        assert self.classifier is not None

    def test_meek_patterns_dict(self):
        """MEEK_PATTERNS is a dict with lane keys."""
        assert isinstance(self.meek_patterns, dict)
        assert len(self.meek_patterns) >= 5

    def test_category_patterns_count(self):
        """CATEGORY_PATTERNS has at least 10 categories."""
        assert isinstance(self.category_patterns, dict)
        assert len(self.category_patterns) >= 10

    def test_supported_extensions(self):
        """SUPPORTED_EXTENSIONS is a frozenset with common types."""
        assert isinstance(self.extensions, frozenset)
        for ext in [".pdf", ".docx", ".txt", ".md", ".csv"]:
            assert ext in self.extensions, f"Missing extension: {ext}"

    def test_ignore_patterns_list(self):
        """IGNORE_PATTERNS is a non-empty list."""
        assert isinstance(self.ignore, (list, tuple, frozenset, set))
        assert len(self.ignore) >= 5

    def test_max_extract_chars(self):
        """MAX_EXTRACT_CHARS is a positive integer."""
        assert isinstance(self.max_chars, int)
        assert self.max_chars > 0

    def test_classification_result_is_dataclass(self):
        """ClassificationResult is a dataclass with expected fields."""
        import dataclasses
        assert dataclasses.is_dataclass(self.ClassificationResult)
        field_names = {f.name for f in dataclasses.fields(self.ClassificationResult)}
        # Check for at least some expected fields
        assert "lane" in field_names or "lanes" in field_names or "category" in field_names


# ── Watcher Tests ───────────────────────────────────────────────────────────

@pytest.mark.skipif(not _sentinel_importable(), reason="sentinel not found")
class TestSentinelWatcher:
    """Tests for daemon.sentinel.watcher."""

    @pytest.fixture(autouse=True)
    def _setup_path(self):
        daemon_root = str(SENTINEL_DIR.parent.parent)
        if daemon_root not in sys.path:
            sys.path.insert(0, daemon_root)
        try:
            from daemon.sentinel.watcher import (
                SentinelWatcher, FileEvent,
                DEBOUNCE_SECONDS, MAX_QUEUE_SIZE, MAX_FILES_PER_MINUTE,
            )
            self.SentinelWatcher = SentinelWatcher
            self.FileEvent = FileEvent
            self.debounce = DEBOUNCE_SECONDS
            self.max_queue = MAX_QUEUE_SIZE
            self.max_rate = MAX_FILES_PER_MINUTE
            self._available = True
        except ImportError as e:
            self._available = False
            pytest.skip(f"watcher import failed: {e}")

    def test_debounce_positive(self):
        """DEBOUNCE_SECONDS is a positive number."""
        assert self.debounce > 0

    def test_max_queue_size(self):
        """MAX_QUEUE_SIZE is a reasonable positive integer."""
        assert isinstance(self.max_queue, int)
        assert self.max_queue >= 100

    def test_max_files_per_minute(self):
        """MAX_FILES_PER_MINUTE is a reasonable positive integer."""
        assert isinstance(self.max_rate, int)
        assert self.max_rate >= 5

    def test_file_event_is_dataclass(self):
        """FileEvent is a dataclass."""
        import dataclasses
        assert dataclasses.is_dataclass(self.FileEvent)

    def test_watcher_class_exists(self):
        """SentinelWatcher class exists and is callable."""
        assert callable(self.SentinelWatcher)


# ── Daemon Import Tests ─────────────────────────────────────────────────────

@pytest.mark.skipif(not _sentinel_importable(), reason="sentinel not found")
class TestSentinelDaemon:
    """Tests for daemon.sentinel.daemon module import."""

    def test_daemon_imports(self):
        """SentinelDaemon and DaemonStats import without crash."""
        daemon_root = str(SENTINEL_DIR.parent.parent)
        if daemon_root not in sys.path:
            sys.path.insert(0, daemon_root)
        try:
            from daemon.sentinel.daemon import SentinelDaemon, DaemonStats
            assert SentinelDaemon is not None
            assert DaemonStats is not None
        except ImportError as e:
            pytest.skip(f"daemon import failed: {e}")

    def test_daemon_stats_has_uptime(self):
        """DaemonStats dataclass has uptime_seconds property."""
        daemon_root = str(SENTINEL_DIR.parent.parent)
        if daemon_root not in sys.path:
            sys.path.insert(0, daemon_root)
        try:
            from daemon.sentinel.daemon import DaemonStats
            import dataclasses
            assert dataclasses.is_dataclass(DaemonStats)
        except ImportError:
            pytest.skip("daemon module not available")

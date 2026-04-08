"""SENTINEL Watcher — Filesystem monitor using watchdog.

Watches configurable directories for new/modified files, debounces
rapid changes, and feeds them into the processing queue.
"""
from __future__ import annotations

import logging
import os
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .classifier import SUPPORTED_EXTENSIONS, IGNORE_PATTERNS

logger = logging.getLogger("sentinel.watcher")

# ---------------------------------------------------------------------------
# Configuration defaults
# ---------------------------------------------------------------------------
DEFAULT_WATCH_DIRS: list[str] = [
    os.path.expanduser("~\\Downloads"),
    os.path.expanduser("~\\Desktop"),
    "D:\\",
    "F:\\",
    "G:\\",
    "I:\\",
]

DEBOUNCE_SECONDS: float = 5.0
MAX_QUEUE_SIZE: int = 1000
MAX_FILES_PER_MINUTE: int = 10


@dataclass
class FileEvent:
    """A filesystem event to be processed."""
    path: str
    event_type: str  # "created" | "modified"
    timestamp: float = field(default_factory=time.time)


class _EventHandler:
    """Watchdog event handler that feeds into the SentinelWatcher queue.

    Implements the watchdog FileSystemEventHandler interface manually
    so we can work with or without the watchdog library installed.
    """

    def __init__(self, watcher: SentinelWatcher) -> None:
        self._watcher = watcher

    def dispatch(self, event: object) -> None:
        """Route watchdog events to on_created / on_modified."""
        if getattr(event, "is_directory", False):
            return
        event_type = getattr(event, "event_type", "")
        src_path = getattr(event, "src_path", "")
        if event_type == "created":
            self.on_created(src_path)
        elif event_type == "modified":
            self.on_modified(src_path)

    def on_created(self, src_path: str) -> None:
        self._watcher._enqueue(src_path, "created")

    def on_modified(self, src_path: str) -> None:
        self._watcher._enqueue(src_path, "modified")


class SentinelWatcher:
    """Monitors directories for new litigation-relevant files.

    Uses the watchdog library for filesystem events with debouncing,
    rate limiting, and a bounded processing queue.

    Usage::

        watcher = SentinelWatcher(watch_dirs=[...])
        watcher.start()
        # ... process watcher.queue items ...
        watcher.stop()
    """

    def __init__(
        self,
        watch_dirs: Optional[list[str]] = None,
        debounce_seconds: float = DEBOUNCE_SECONDS,
        max_queue: int = MAX_QUEUE_SIZE,
        max_per_minute: int = MAX_FILES_PER_MINUTE,
        recursive: bool = True,
    ) -> None:
        self.watch_dirs: list[str] = self._validate_dirs(watch_dirs or DEFAULT_WATCH_DIRS)
        self.debounce_seconds = debounce_seconds
        self.max_per_minute = max_per_minute
        self.recursive = recursive
        self.queue: deque[FileEvent] = deque(maxlen=max_queue)

        # Debounce tracking: path → last_seen_timestamp
        self._seen: dict[str, float] = {}
        self._seen_lock = threading.Lock()

        # Rate limiting
        self._minute_window: list[float] = []
        self._rate_lock = threading.Lock()

        # Watchdog state
        self._observer: Optional[object] = None
        self._running = False
        self._start_time: Optional[float] = None

        # Stats
        self.stats = {
            "events_received": 0,
            "events_debounced": 0,
            "events_rate_limited": 0,
            "events_queued": 0,
            "events_ignored_ext": 0,
            "events_ignored_pattern": 0,
        }

    @staticmethod
    def _validate_dirs(dirs: list[str]) -> list[str]:
        """Filter to directories that actually exist."""
        valid = []
        for d in dirs:
            if os.path.isdir(d):
                valid.append(d)
            else:
                logger.debug("Watch directory not found, skipping: %s", d)
        return valid

    def _should_process(self, file_path: str) -> bool:
        """Check extension and ignore patterns."""
        name = os.path.basename(file_path)
        for pat in IGNORE_PATTERNS:
            if pat.search(name):
                self.stats["events_ignored_pattern"] += 1
                return False
        ext = os.path.splitext(name)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            self.stats["events_ignored_ext"] += 1
            return False
        return True

    def _is_debounced(self, file_path: str) -> bool:
        """Return True if this path was seen recently (within debounce window)."""
        now = time.time()
        with self._seen_lock:
            last = self._seen.get(file_path, 0.0)
            if now - last < self.debounce_seconds:
                self.stats["events_debounced"] += 1
                return True
            self._seen[file_path] = now
            # Prune old entries periodically
            if len(self._seen) > 5000:
                cutoff = now - self.debounce_seconds * 2
                self._seen = {k: v for k, v in self._seen.items() if v > cutoff}
        return False

    def _is_rate_limited(self) -> bool:
        """Return True if we've hit the per-minute rate limit."""
        now = time.time()
        with self._rate_lock:
            cutoff = now - 60.0
            self._minute_window = [t for t in self._minute_window if t > cutoff]
            if len(self._minute_window) >= self.max_per_minute:
                self.stats["events_rate_limited"] += 1
                return True
            self._minute_window.append(now)
        return False

    def _enqueue(self, file_path: str, event_type: str) -> None:
        """Process a raw filesystem event through filters and into the queue."""
        self.stats["events_received"] += 1

        if not self._should_process(file_path):
            return
        if self._is_debounced(file_path):
            return
        if self._is_rate_limited():
            return

        event = FileEvent(path=file_path, event_type=event_type)
        self.queue.append(event)
        self.stats["events_queued"] += 1
        logger.info("Queued [%s]: %s", event_type, file_path)

    def start(self) -> None:
        """Start watching all configured directories."""
        if self._running:
            logger.warning("Watcher already running")
            return

        if not self.watch_dirs:
            logger.error("No valid watch directories configured")
            return

        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            class _WDHandler(FileSystemEventHandler):
                def __init__(inner_self, watcher: SentinelWatcher) -> None:
                    super().__init__()
                    inner_self._watcher = watcher

                def on_created(inner_self, event: object) -> None:
                    if not getattr(event, "is_directory", False):
                        inner_self._watcher._enqueue(
                            getattr(event, "src_path", ""), "created"
                        )

                def on_modified(inner_self, event: object) -> None:
                    if not getattr(event, "is_directory", False):
                        inner_self._watcher._enqueue(
                            getattr(event, "src_path", ""), "modified"
                        )

            observer = Observer()
            handler = _WDHandler(self)
            for d in self.watch_dirs:
                try:
                    observer.schedule(handler, d, recursive=self.recursive)
                    logger.info("Watching: %s (recursive=%s)", d, self.recursive)
                except Exception as exc:
                    logger.warning("Cannot watch %s: %s", d, exc)

            observer.start()
            self._observer = observer
            self._running = True
            self._start_time = time.time()
            logger.info(
                "SENTINEL Watcher started — monitoring %d directories", len(self.watch_dirs)
            )
        except ImportError:
            logger.error(
                "watchdog library not installed. Install with: pip install watchdog"
            )
            raise

    def stop(self) -> None:
        """Stop watching."""
        if not self._running:
            logger.info("Watcher not running")
            return
        if self._observer is not None:
            self._observer.stop()  # type: ignore[attr-defined]
            self._observer.join(timeout=10)  # type: ignore[attr-defined]
            self._observer = None
        self._running = False
        logger.info("SENTINEL Watcher stopped")

    def status(self) -> dict:
        """Return current watcher status and statistics."""
        uptime = 0.0
        if self._start_time and self._running:
            uptime = time.time() - self._start_time
        return {
            "running": self._running,
            "watch_dirs": self.watch_dirs,
            "queue_size": len(self.queue),
            "queue_max": self.queue.maxlen,
            "uptime_seconds": round(uptime, 1),
            **self.stats,
        }

    def drain_queue(self, max_items: int = 50) -> list[FileEvent]:
        """Remove and return up to max_items from the front of the queue."""
        items: list[FileEvent] = []
        while self.queue and len(items) < max_items:
            items.append(self.queue.popleft())
        return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    action = sys.argv[1] if len(sys.argv) > 1 else "status"

    if action == "start":
        watcher = SentinelWatcher()
        watcher.start()
        print(f"SENTINEL Watcher started — monitoring {len(watcher.watch_dirs)} directories")
        print("Press Ctrl+C to stop...")
        try:
            while True:
                time.sleep(2)
                items = watcher.drain_queue()
                for item in items:
                    print(f"  [{item.event_type}] {item.path}")
        except KeyboardInterrupt:
            watcher.stop()
            print("\nStopped.")
    elif action == "status":
        watcher = SentinelWatcher()
        st = watcher.status()
        print("SENTINEL Watcher Status:")
        for k, v in st.items():
            print(f"  {k}: {v}")
    elif action == "stop":
        print("Stop is handled via Ctrl+C or daemon manager.")
    else:
        print(f"Usage: python -I watcher.py {{start|stop|status}}")
        sys.exit(1)

"""SENTINEL Daemon — Main orchestrator for file watching, classification, and organization.

Combines SentinelWatcher + FileClassifier + FileOrganizer into a single
daemon loop that automatically processes new files.

CLI::

    python -I daemon.py start    # Start watching + processing
    python -I daemon.py stop     # (use Ctrl+C or kill PID)
    python -I daemon.py status   # Show stats and configuration
    python -I daemon.py test     # Dry-run classify 5 sample files
"""
from __future__ import annotations

import logging
import os
import signal
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .classifier import FileClassifier, ClassificationResult
from .organizer import FileOrganizer, REPO_ROOT
from .watcher import SentinelWatcher, FileEvent

logger = logging.getLogger("sentinel.daemon")

LOG_DIR = os.path.join(REPO_ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)


@dataclass
class DaemonStats:
    """Runtime statistics for the SENTINEL daemon."""
    files_seen: int = 0
    files_classified: int = 0
    files_copied: int = 0
    files_duplicate: int = 0
    files_skipped: int = 0
    errors: int = 0
    start_time: float = 0.0

    @property
    def uptime_seconds(self) -> float:
        if self.start_time <= 0:
            return 0.0
        return time.time() - self.start_time

    def as_dict(self) -> dict:
        return {
            "files_seen": self.files_seen,
            "files_classified": self.files_classified,
            "files_copied": self.files_copied,
            "files_duplicate": self.files_duplicate,
            "files_skipped": self.files_skipped,
            "errors": self.errors,
            "uptime_seconds": round(self.uptime_seconds, 1),
        }


class SentinelDaemon:
    """Main daemon that ties together watcher, classifier, and organizer.

    Lifecycle::

        daemon = SentinelDaemon()
        daemon.start()    # blocks until stop() or Ctrl+C
        daemon.status()   # print stats
    """

    def __init__(
        self,
        watch_dirs: Optional[list[str]] = None,
        dry_run: bool = False,
        poll_interval: float = 2.0,
    ) -> None:
        self.dry_run = dry_run
        self.poll_interval = poll_interval
        self.stats = DaemonStats()
        self._running = False

        self.watcher = SentinelWatcher(watch_dirs=watch_dirs)
        self.classifier = FileClassifier()
        self.organizer = FileOrganizer(dry_run=dry_run)

    def start(self) -> None:
        """Start the daemon: begin watching and processing files."""
        if self._running:
            logger.warning("Daemon already running")
            return

        self._running = True
        self.stats.start_time = time.time()

        # Setup signal handlers for graceful shutdown
        original_sigint = signal.getsignal(signal.SIGINT)
        original_sigterm = signal.getsignal(signal.SIGTERM)

        def _shutdown(signum: int, frame: object) -> None:
            logger.info("Received signal %d — shutting down", signum)
            self._running = False

        signal.signal(signal.SIGINT, _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)

        try:
            self.watcher.start()
            logger.info(
                "SENTINEL Daemon started (dry_run=%s, poll=%.1fs)",
                self.dry_run, self.poll_interval,
            )
            print(f"SENTINEL Daemon running — monitoring {len(self.watcher.watch_dirs)} directories")
            if self.dry_run:
                print("  ⚠ DRY RUN mode — no files will be copied or registered")
            print("  Press Ctrl+C to stop.\n")

            # Main processing loop
            while self._running:
                self.process_queue()
                time.sleep(self.poll_interval)

        except Exception as exc:
            logger.error("Daemon error: %s", exc)
            raise
        finally:
            self.stop()
            signal.signal(signal.SIGINT, original_sigint)
            signal.signal(signal.SIGTERM, original_sigterm)

    def stop(self) -> None:
        """Stop the daemon gracefully."""
        self._running = False
        try:
            self.watcher.stop()
        except Exception as exc:
            logger.warning("Error stopping watcher: %s", exc)
        logger.info("SENTINEL Daemon stopped. Stats: %s", self.stats.as_dict())

    def process_queue(self) -> int:
        """Process all items currently in the watcher queue.

        Returns:
            Number of items processed.
        """
        items = self.watcher.drain_queue(max_items=50)
        if not items:
            return 0

        processed = 0
        for event in items:
            self._process_single(event)
            processed += 1
        return processed

    def _process_single(self, event: FileEvent) -> None:
        """Process a single file event: classify → organize → register."""
        self.stats.files_seen += 1
        file_path = event.path

        # Skip if file no longer exists (transient)
        if not os.path.isfile(file_path):
            self.stats.files_skipped += 1
            logger.debug("SKIP — file gone: %s", file_path)
            return

        try:
            # Classify
            result = self.classifier.classify(file_path)
            self.stats.files_classified += 1

            logger.info(
                "CLASSIFIED: %s → lane=%s cat=%s conf=%.2f",
                os.path.basename(file_path),
                result.lane,
                result.category,
                result.confidence,
            )

            # Organize (copy + register)
            outcome = self.organizer.organize(result)

            if outcome["duplicate"]:
                self.stats.files_duplicate += 1
            elif outcome["copied"]:
                self.stats.files_copied += 1
            else:
                self.stats.files_skipped += 1

        except Exception as exc:
            self.stats.errors += 1
            logger.error("ERROR processing %s: %s", file_path, exc)

    def status(self) -> dict:
        """Return combined status from daemon + watcher."""
        watcher_status = self.watcher.status()
        daemon_status = self.stats.as_dict()
        return {
            "daemon": daemon_status,
            "watcher": watcher_status,
            "dry_run": self.dry_run,
            "classifier": {
                "pdf_support": self.classifier._pdf_available,
                "docx_support": self.classifier._docx_available,
            },
        }

    def test_classify(self, count: int = 5) -> list[ClassificationResult]:
        """Find and classify a sample of files for testing (dry-run).

        Searches the Downloads and Desktop directories for test files.

        Args:
            count: Number of files to classify.

        Returns:
            List of ClassificationResult objects.
        """
        test_dirs = [
            os.path.expanduser("~\\Downloads"),
            os.path.expanduser("~\\Desktop"),
        ]

        candidates: list[str] = []
        for d in test_dirs:
            if not os.path.isdir(d):
                continue
            try:
                for entry in os.scandir(d):
                    if entry.is_file() and self.classifier.should_process(entry.path):
                        candidates.append(entry.path)
                        if len(candidates) >= count * 3:
                            break
            except PermissionError:
                continue

        results: list[ClassificationResult] = []
        for fpath in candidates[:count]:
            try:
                result = self.classifier.classify(fpath)
                results.append(result)
            except Exception as exc:
                logger.warning("Test classify failed on %s: %s", fpath, exc)

        return results


def _print_status(daemon: SentinelDaemon) -> None:
    """Pretty-print daemon status."""
    st = daemon.status()
    print("═══ SENTINEL Daemon Status ═══")
    print(f"  Running: {st['watcher']['running']}")
    print(f"  Dry Run: {st['dry_run']}")
    print(f"  PDF support: {st['classifier']['pdf_support']}")
    print(f"  DOCX support: {st['classifier']['docx_support']}")
    print(f"\n  Watch Dirs ({len(st['watcher']['watch_dirs'])}):")
    for d in st["watcher"]["watch_dirs"]:
        print(f"    • {d}")
    print(f"\n  Queue: {st['watcher']['queue_size']} / {st['watcher']['queue_max']}")
    print(f"\n  Daemon Stats:")
    for k, v in st["daemon"].items():
        print(f"    {k}: {v}")
    print(f"\n  Watcher Stats:")
    for k, v in st["watcher"].items():
        if k not in ("running", "watch_dirs", "queue_size", "queue_max"):
            print(f"    {k}: {v}")


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Also log to file
    file_handler = logging.FileHandler(
        os.path.join(LOG_DIR, "sentinel.log"), encoding="utf-8"
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logging.getLogger("sentinel").addHandler(file_handler)

    action = sys.argv[1] if len(sys.argv) > 1 else "status"

    if action == "start":
        daemon = SentinelDaemon()
        daemon.start()

    elif action == "test":
        print("═══ SENTINEL Test Mode (dry-run) ═══\n")
        daemon = SentinelDaemon(dry_run=True)
        results = daemon.test_classify(count=5)
        if not results:
            print("  No test files found in Downloads/Desktop")
            return
        for i, r in enumerate(results, 1):
            print(f"  [{i}] {os.path.basename(r.file_path)}")
            print(f"      Lane: {r.lane} | Category: {r.category} | Confidence: {r.confidence}")
            print(f"      SHA-256: {r.sha256[:16]}...")
            print(f"      Summary: {r.summary[:80]}")
            print()

        # Also test organizer dry-run
        print("  --- Dry-run organize ---")
        for r in results[:2]:
            outcome = daemon.organizer.organize(r)
            print(f"  {os.path.basename(r.file_path)}: {outcome['reason']}")
            print(f"    → {outcome['dest_path']}")
        print()

    elif action == "status":
        daemon = SentinelDaemon()
        _print_status(daemon)

    elif action == "stop":
        print("SENTINEL: Use Ctrl+C or kill the daemon process to stop.")

    else:
        print("SENTINEL Daemon — Self-Organizing File System")
        print(f"Usage: python -I {sys.argv[0]} {{start|stop|status|test}}")
        print()
        print("  start   — Start watching directories and processing files")
        print("  stop    — Stop the daemon (Ctrl+C or kill PID)")
        print("  status  — Show current configuration and statistics")
        print("  test    — Dry-run classify 5 sample files")
        sys.exit(1)


if __name__ == "__main__":
    main()

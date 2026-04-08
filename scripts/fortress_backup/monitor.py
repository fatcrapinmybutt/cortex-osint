"""FORTRESS Monitor — Orchestrator daemon for multi-DB health monitoring.

Coordinates health checks, anomaly detection, auto-healing, and markdown
report generation across all LitigationOS databases.

Usage (CLI):
    python -I monitor.py check   # Run health checks on all DBs
    python -I monitor.py heal    # Check + auto-heal failures
    python -I monitor.py baseline # Update row count baselines
    python -I monitor.py status  # Print summary status
    python -I monitor.py report  # Generate markdown health report
"""

import argparse
import os
import sys
import time
import logging
from datetime import datetime
from typing import Optional

from .health import DatabaseHealthChecker, HealthReport
from .healer import DatabaseHealer
from .anomaly import AnomalyDetector, Anomaly

logger = logging.getLogger(__name__)

# Resolve repo root relative to this file (00_SYSTEM/daemon/fortress/ → repo root)
_REPO_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
)

DEFAULT_DBS = [
    os.path.join(_REPO_ROOT, "litigation_context.db"),
    os.path.join(_REPO_ROOT, "mbp_brain.db"),
    os.path.join(_REPO_ROOT, "claim_evidence_links.db"),
    os.path.join(_REPO_ROOT, "db.sqlite"),
]

REPORT_DIR = os.path.join(_REPO_ROOT, "logs", "fortress")


class DatabaseMonitor:
    """Orchestrate health checks, healing, and reporting across databases."""

    def __init__(self, db_paths: Optional[list[str]] = None) -> None:
        self.db_paths = [
            p for p in (db_paths or DEFAULT_DBS) if os.path.isfile(p)
        ]
        if not self.db_paths:
            raise FileNotFoundError(
                f"No databases found. Checked: {db_paths or DEFAULT_DBS}"
            )
        self.results: dict[str, HealthReport] = {}
        self.anomalies: dict[str, list[Anomaly]] = {}
        self.heal_results: dict[str, list] = {}

    def run_cycle(self, auto_heal: bool = False) -> dict[str, HealthReport]:
        """Run health checks (and optionally heal) across all monitored databases."""
        self.results.clear()
        self.anomalies.clear()
        self.heal_results.clear()

        for db_path in self.db_paths:
            db_name = os.path.basename(db_path)
            try:
                # Health checks
                checker = DatabaseHealthChecker(db_path)
                report = checker.run_all_checks()
                self.results[db_name] = report

                # Anomaly detection
                detector = AnomalyDetector(db_path)
                current_counts = _get_row_counts(db_path, checker)
                anomalies = detector.detect(current_counts)
                self.anomalies[db_name] = anomalies
                detector.save_snapshot(current_counts)

                # Auto-heal if requested and something is wrong
                if auto_heal and report.overall != "PASS":
                    healer = DatabaseHealer(db_path)
                    heal_log = healer.heal(report.results)
                    self.heal_results[db_name] = heal_log

            except Exception as exc:
                logger.error("Monitor cycle failed for %s: %s", db_name, exc)
                error_report = HealthReport(db_path=db_path)
                from .health import HealthResult

                error_report.add(HealthResult(
                    check_name="monitor_error",
                    status="FAIL",
                    detail=f"Monitor error: {exc}",
                ))
                self.results[db_name] = error_report

        return self.results

    def update_baselines(self) -> dict[str, int]:
        """Update row count baselines for all monitored databases."""
        updated = {}
        for db_path in self.db_paths:
            db_name = os.path.basename(db_path)
            try:
                checker = DatabaseHealthChecker(db_path)
                counts = _get_row_counts(db_path, checker)
                detector = AnomalyDetector(db_path)
                n = detector.update_baseline(counts)
                updated[db_name] = n
            except Exception as exc:
                logger.error("Baseline update failed for %s: %s", db_name, exc)
                updated[db_name] = -1
        return updated

    def status_summary(self) -> str:
        """Return a compact status string for all databases."""
        if not self.results:
            self.run_cycle(auto_heal=False)

        lines = ["FORTRESS Status Summary", "=" * 50]
        for db_name, report in self.results.items():
            icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(
                report.overall, "❓"
            )
            checks = len(report.results)
            fails = sum(1 for r in report.results if r.status == "FAIL")
            warns = sum(1 for r in report.results if r.status == "WARN")
            lines.append(
                f"{icon} {db_name}: {report.overall} "
                f"({checks} checks, {fails} fails, {warns} warns)"
            )

            # Anomalies
            anoms = self.anomalies.get(db_name, [])
            crits = [a for a in anoms if a.severity == "CRITICAL"]
            if crits:
                for a in crits:
                    lines.append(f"    🔴 {a.message}")

        lines.append(f"\nTimestamp: {datetime.now().isoformat(timespec='seconds')}")
        return "\n".join(lines)

    def generate_report(self) -> str:
        """Generate a full markdown health report and save to logs/fortress/."""
        if not self.results:
            self.run_cycle(auto_heal=False)

        ts = datetime.now()
        ts_str = ts.strftime("%Y%m%d_%H%M%S")
        ts_human = ts.strftime("%Y-%m-%d %H:%M:%S")

        lines = [
            f"# FORTRESS Health Report",
            f"",
            f"**Generated:** {ts_human}  ",
            f"**Databases monitored:** {len(self.results)}  ",
            f"",
        ]

        # Overall status table
        lines.append("## Summary\n")
        lines.append("| Database | Status | Checks | Pass | Warn | Fail |")
        lines.append("|----------|--------|--------|------|------|------|")
        for db_name, report in self.results.items():
            checks = len(report.results)
            passes = sum(1 for r in report.results if r.status == "PASS")
            warns = sum(1 for r in report.results if r.status == "WARN")
            fails = sum(1 for r in report.results if r.status == "FAIL")
            icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(
                report.overall, "❓"
            )
            lines.append(
                f"| {db_name} | {icon} {report.overall} | {checks} | "
                f"{passes} | {warns} | {fails} |"
            )
        lines.append("")

        # Detailed results per DB
        for db_name, report in self.results.items():
            lines.append(f"## {db_name}\n")
            lines.append(f"**Path:** `{report.db_path}`  ")
            lines.append(f"**Overall:** {report.overall}\n")
            lines.append("| Check | Status | Detail | Duration |")
            lines.append("|-------|--------|--------|----------|")
            for r in report.results:
                icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(
                    r.status, "❓"
                )
                dur = f"{r.duration_ms:.0f}ms" if r.duration_ms > 0 else "—"
                detail_safe = r.detail.replace("|", "\\|")[:120]
                lines.append(f"| {r.check_name} | {icon} {r.status} | {detail_safe} | {dur} |")
            lines.append("")

            # Anomalies for this DB
            anoms = self.anomalies.get(db_name, [])
            if anoms:
                lines.append("### Anomalies\n")
                for a in anoms:
                    sev_icon = {"INFO": "ℹ️", "WARN": "⚠️", "CRITICAL": "🔴"}.get(
                        a.severity, "❓"
                    )
                    lines.append(f"- {sev_icon} **{a.severity}** {a.message}")
                lines.append("")

            # Heal results
            heals = self.heal_results.get(db_name, [])
            if heals:
                lines.append("### Healing Actions\n")
                for h in heals:
                    icon = "✅" if h.success else "❌"
                    lines.append(
                        f"- {icon} **{h.action}**: {h.detail} ({h.duration_ms:.0f}ms)"
                    )
                lines.append("")

        report_text = "\n".join(lines)

        # Save to file
        os.makedirs(REPORT_DIR, exist_ok=True)
        report_path = os.path.join(REPORT_DIR, f"health_{ts_str}.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_text)

        logger.info("Report written to %s", report_path)
        return report_path


def _get_row_counts(
    db_path: str, checker: DatabaseHealthChecker
) -> dict[str, int]:
    """Get current row counts for monitored tables."""
    from .health import ROW_COUNT_TABLES, _open_connection, _is_exfat

    counts: dict[str, int] = {}
    exfat = _is_exfat(db_path)
    conn = _open_connection(db_path, exfat=exfat)
    try:
        existing = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        for table in ROW_COUNT_TABLES:
            if table not in existing:
                continue
            try:
                row = conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()
                counts[table] = row[0] if row else 0
            except Exception:
                counts[table] = -1
    finally:
        conn.close()
    return counts


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------


def main() -> None:
    """CLI interface for FORTRESS monitor."""
    parser = argparse.ArgumentParser(
        prog="fortress",
        description="FORTRESS — Self-healing database infrastructure daemon",
    )
    parser.add_argument(
        "command",
        choices=["check", "heal", "baseline", "status", "report"],
        help="Operation to perform",
    )
    parser.add_argument(
        "--db",
        action="append",
        help="Database path(s) to monitor (can be repeated). Defaults to LitigationOS DBs.",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress stdout output")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    try:
        monitor = DatabaseMonitor(db_paths=args.db)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.command == "check":
        monitor.run_cycle(auto_heal=False)
        if not args.quiet:
            print(monitor.status_summary())

    elif args.command == "heal":
        monitor.run_cycle(auto_heal=True)
        if not args.quiet:
            print(monitor.status_summary())
            heals = sum(len(v) for v in monitor.heal_results.values())
            successes = sum(
                sum(1 for h in v if h.success)
                for v in monitor.heal_results.values()
            )
            print(f"\nHealing: {successes}/{heals} actions succeeded")

    elif args.command == "baseline":
        updated = monitor.update_baselines()
        if not args.quiet:
            for db, n in updated.items():
                status = f"{n} tables" if n >= 0 else "FAILED"
                print(f"  {db}: {status}")

    elif args.command == "status":
        print(monitor.status_summary())

    elif args.command == "report":
        monitor.run_cycle(auto_heal=False)
        path = monitor.generate_report()
        if not args.quiet:
            print(f"Report written to: {path}")
            print(monitor.status_summary())

    # Exit code: 0 = all PASS, 1 = any WARN, 2 = any FAIL
    statuses = [r.overall for r in monitor.results.values()]
    if "FAIL" in statuses:
        sys.exit(2)
    elif "WARN" in statuses:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()

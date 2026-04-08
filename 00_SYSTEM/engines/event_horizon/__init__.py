"""
EVENT HORIZON Δ∞ — The Autonomous-Multi-Agent-Omega-Engine
===========================================================

12-subsystem engine for intelligent, self-evolving filesystem organization.

Usage:
    python -m event_horizon --zone ROOT --dry-run
    python -m event_horizon --zone ROOT --execute
    python -m event_horizon --zone 06_DATA --dry-run
    python -m event_horizon --census
"""
from __future__ import annotations

__all__ = ["EventHorizonOrchestrator"]

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import REPO_ROOT, RoutingPlan, MoveMetrics, QualityReport
from .state import StateDB
from .genesis import Genesis
from .oracle import Oracle
from .promethean import Promethean
from .elysium import Elysium
from .hydra import Hydra
from .ouroboros import Ouroboros
from .eschaton import Eschaton
from .supernova import Supernova
from .emergence import Emergence
from .transcendent import Transcendent
from .apotheosis import Apotheosis

__version__ = "1.5.0"
__codename__ = "EVENT HORIZON"

log = logging.getLogger("event_horizon")

# Minimum free disk space required to run (bytes)
MIN_DISK_FREE_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB


def _check_disk_space(path: Path, min_bytes: int = MIN_DISK_FREE_BYTES) -> tuple[bool, int]:
    """Check available disk space. Returns (ok, free_bytes)."""
    try:
        import shutil
        usage = shutil.disk_usage(str(path))
        return usage.free >= min_bytes, usage.free
    except Exception:
        return True, -1  # Can't check — proceed with caution


def _score_delta(before, after) -> str:
    """Compute score delta string from two 'XX.X/100' strings."""
    try:
        b = float(str(before).split("/")[0])
        a = float(str(after).split("/")[0])
        d = a - b
        return f"{d:+.1f} ({before} -> {after})"
    except (TypeError, ValueError, IndexError):
        return f"{before} -> {after}"


class Engine:
    """EVENT HORIZON -- Autonomous filesystem intelligence engine.
    
    Pipeline: GENESIS -> ORACLE -> PROMETHEAN -> ELYSIUM
    
    Pre-flight checks:
    - Disk space >= 2 GB free
    - State DB writable and healthy
    - Root path exists
    
    Usage:
        engine = Engine()
        report = engine.run("ROOT", dry_run=True)
        print(report.summary())
    """

    def __init__(self, root: Path = REPO_ROOT, db_path: Optional[Path] = None):
        self.root = Path(root) if not isinstance(root, Path) else root
        if db_path is not None and not isinstance(db_path, Path):
            db_path = Path(db_path)
        if not self.root.exists():
            raise FileNotFoundError(f"Repository root not found: {self.root}")

        if db_path is None:
            db_path = self.root / "00_SYSTEM" / "engines" / "event_horizon" / "event_horizon.db"

        # Pre-flight: disk space
        ok, free = _check_disk_space(self.root)
        if not ok:
            free_mb = free / (1024 * 1024)
            raise RuntimeError(
                f"Insufficient disk space: {free_mb:.0f} MB free, "
                f"need {MIN_DISK_FREE_BYTES // (1024*1024)} MB minimum. "
                f"Free space before running."
            )
        if free > 0:
            log.info("Pre-flight: %.1f GB free disk space", free / (1024**3))

        # Initialize subsystems with resilient state DB
        self.state = StateDB(db_path)
        self.genesis = Genesis(self.root)
        self.oracle = Oracle(self.root, self.state)
        self.promethean = Promethean(self.root, self.state)
        self.elysium = Elysium(self.root)
        self.hydra = Hydra(self.root, self.state)
        self.ouroboros = Ouroboros(self.root, self.state)
        self.eschaton = Eschaton(self.root, self.state)
        self.supernova = Supernova(self.root, self.state)
        self.emergence = Emergence(self.root, self.state)
        self.transcendent = Transcendent(self.root, self.state)
        self.apotheosis = Apotheosis(self.root, self.state)

    def run(self, zone: str, dry_run: bool = True) -> dict:
        """Execute the full 4-subsystem MVP pipeline on a zone.
        
        Returns a summary dict with plan, metrics, and quality report.
        """
        mode = "DRY-RUN" if dry_run else "LIVE"
        log.info("=" * 60)
        log.info("EVENT HORIZON v%s -- %s", __version__, mode)
        log.info("Zone: %s", zone)
        log.info("=" * 60)

        # Start run in state DB
        with self.state:
            run_id = self.state.start_run(zone, dry_run)

            # -- GENESIS: Scan --
            log.info("[GENESIS] Scanning...")
            manifests = self.genesis.scan(zone)
            self.state.save_manifests(run_id, manifests)
            log.info("[GENESIS] %d files profiled", len(manifests))

            # -- ORACLE: Decide --
            log.info("[ORACLE] Routing decisions...")
            plan = self.oracle.decide(manifests)
            self.state.save_decisions(run_id, plan.decisions)
            log.info("[ORACLE] %d routable, %d skipped", plan.routable, len(plan.skipped))

            # -- ELYSIUM PRE-CHECK: Validate plan --
            log.info("[ELYSIUM] Pre-flight validation...")
            pre_report = self.elysium.validate(plan, dry_run=True)
            log.info("[ELYSIUM] Pre-check: %s", "PASSED" if pre_report.passed else "ISSUES")

            # -- PROMETHEAN: Execute --
            log.info("[PROMETHEAN] Executing...")
            metrics = self.promethean.execute(plan, dry_run=dry_run, run_id=run_id)
            log.info("[PROMETHEAN] %d ok, %d err", metrics.success_count, metrics.error_count)

            # -- ELYSIUM POST-CHECK: Validate results --
            log.info("[ELYSIUM] Post-flight validation...")
            post_report = self.elysium.validate(plan, metrics, dry_run=dry_run)
            self.state.save_quality(run_id, post_report)
            log.info("[ELYSIUM] Post-check: %s", "PASSED" if post_report.passed else "FAILED")

            # Finalize run
            self.state.finish_run(run_id, "completed", {
                "success_count": metrics.success_count,
                "error_count": metrics.error_count,
            })

        # Build summary
        summary = self._build_summary(zone, mode, run_id, manifests, plan, metrics, post_report)
        self._print_summary(summary)
        return summary

    def protected_run(self, zone: str, dry_run: bool = True) -> dict:
        """HYDRA-protected run with sharding, retry, WAL, and genetic memory.
        
        Use this for large zones (06_DATA, 04_ANALYSIS) or any zone where
        resilience matters more than speed.
        """
        report = self.hydra.protected_run(zone, dry_run=dry_run)
        return {
            "engine": f"{__codename__} v{__version__} + HYDRA",
            "zone": zone,
            "mode": "DRY-RUN" if dry_run else "LIVE",
            "hydra": {
                "status": report.final_status,
                "shards": f"{report.shards_succeeded}/{report.total_shards}",
                "files_moved": report.files_moved,
                "files_errored": report.files_errored,
                "phoenix_restarts": report.phoenix_restarts,
                "genetic_lessons": report.genetic_lessons,
                "elapsed": f"{report.elapsed_seconds:.1f}s",
                "success_rate": f"{report.success_rate:.1%}",
            },
        }

    def _build_summary(self, zone, mode, run_id, manifests, plan, metrics, post_report):
        """Build the summary dict from pipeline results."""
        summary = {
            "engine": f"{__codename__} v{__version__}",
            "zone": zone,
            "mode": mode,
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "scan": {
                "total_files": len(manifests),
            },
            "routing": {
                "routable": plan.routable,
                "skipped": len(plan.skipped),
                "stats": plan.stats,
            },
            "execution": {
                "success": metrics.success_count,
                "errors": metrics.error_count,
                "total": metrics.total_attempted,
            },
            "quality": {
                "passed": post_report.passed,
                "score": post_report.overall_score,
                "gates_passed": post_report.gates_passed,
                "gates_total": post_report.gates_total,
                "results": [
                    {"gate": r.gate.value, "passed": r.passed, "score": r.score, "details": r.details}
                    for r in post_report.results
                ],
            },
        }

        # Print summary
        return summary

    def census(self) -> dict[str, int]:
        """Quick file census across all zones."""
        return self.genesis.quick_census()

    def evolve(self, run_id: Optional[int] = None) -> dict:
        """Run OUROBOROS self-improvement on the latest (or specified) run.

        Returns an evolution record dict.
        """
        record = self.ouroboros.evolve(run_id)
        return {
            "engine": f"{__codename__} v{__version__} + OUROBOROS",
            "cycle": record.cycle_id,
            "run_id": record.run_id,
            "weaknesses": record.weaknesses_found,
            "mutations_proposed": record.mutations_proposed,
            "mutations_accepted": record.mutations_accepted,
            "accuracy_before": f"{record.accuracy_before:.1%}",
            "accuracy_after": f"{record.accuracy_after:.1%}",
            "delta": f"+{record.delta:.1%}",
            "lessons_stored": record.lessons_stored,
            "detail": {
                "weaknesses": [
                    {"category": w.category, "severity": w.severity,
                     "description": w.description, "count": w.affected_count}
                    for w in record.weaknesses
                ],
                "mutations": [
                    {"target": m.target, "description": m.description,
                     "impact": m.expected_impact, "confidence": m.confidence}
                    for m in record.mutations
                ],
            },
        }

    def convergence(self, run_id: Optional[int] = None) -> dict:
        """Measure ESCHATON convergence score.

        Returns a convergence summary dict.
        """
        score = self.eschaton.measure(run_id)
        rec = self.eschaton.recommend_next(score)
        # Flatten rec to avoid circular refs (all_recommendations embeds dicts only)
        next_action = {
            "zone": rec.get("zone", "NONE"),
            "reason": rec.get("reason", ""),
            "estimated_files": rec.get("estimated_files", 0),
            "priority": rec.get("priority", 0),
            "impact": rec.get("impact", "none"),
        }
        return {
            "engine": f"{__codename__} v{__version__} + ESCHATON",
            "state": score.state.value,
            "score": f"{score.score:.1%}",
            "files_sorted": score.files_sorted,
            "files_total": score.files_total,
            "root_files": score.root_files,
            "bloated_zones": score.bloated_zones,
            "cycle": score.cycle,
            "continue": self.eschaton.should_continue(score),
            "next_action": next_action,
        }

    def harvest(self, targets: Optional[list] = None,
                digest_limit: Optional[int] = None,
                profile_limit: Optional[int] = None) -> dict:
        """Run SUPERNOVA parts harvester pipeline.

        Scans targets (default: 00_SYSTEM, 07_CODE, Desktop), fingerprints,
        classifies, clusters, ranks, and generates a manifest with forge
        recommendations.
        """
        return self.supernova.run(
            targets=targets,
            digest_limit=digest_limit,
            profile_limit=profile_limit,
        )

    def emergence_scan(self) -> dict:
        """Run EVENT HORIZON emergence detection.

        Discovers novel patterns in the filesystem and routing data:
        temporal clusters, citation chains, orphan zones, size anomalies,
        name clusters, and cross-references.
        """
        report = self.emergence.scan()
        return {
            "engine": f"{__codename__} v{__version__} + EMERGENCE",
            "signals": report.signal_count,
            "high_confidence": len(report.high_confidence),
            "files_analyzed": report.total_files_analyzed,
            "elapsed": f"{report.elapsed_seconds:.1f}s",
            "detail": [
                {"type": s.signal_type, "description": s.description,
                 "confidence": s.confidence, "affected": s.affected_count,
                 "recommendation": s.recommendation}
                for s in report.signals
            ],
        }

    def fuse(self) -> dict:
        """Run TRANSCENDENT cross-domain fusion.

        Fuses data from all available subsystems to discover compound
        insights that no single subsystem could produce alone.
        """
        report = self.transcendent.fuse()
        return {
            "engine": f"{__codename__} v{__version__} + TRANSCENDENT",
            "subsystems_analyzed": report.subsystems_analyzed,
            "insights": len(report.insights),
            "high_impact": len(report.high_impact),
            "elapsed": f"{report.elapsed_seconds:.1f}s",
            "detail": [
                {"type": i.fusion_type, "title": i.title,
                 "impact": i.impact, "recommendation": i.recommendation}
                for i in report.insights
            ],
        }

    def meta_assess(self) -> dict:
        """Run APOTHEOSIS meta-intelligence assessment.

        Observes all 12 subsystems, checks health, computes system score,
        and generates prioritized recommendations.
        """
        report = self.apotheosis.assess()
        return {
            "engine": f"{__codename__} v{__version__} + APOTHEOSIS",
            "system_score": f"{report.system_score:.1f}/100",
            "active": f"{report.active_count}/12",
            "total_rows": report.total_rows,
            "recommendations": len(report.recommendations),
            "elapsed": f"{report.elapsed_seconds:.1f}s",
            "health": [
                {"subsystem": h.name, "status": h.status, "lines": h.file_lines,
                 "rows": h.total_rows, "notes": h.notes}
                for h in report.health
            ],
            "recs": [
                {"priority": r.priority, "category": r.category,
                 "title": r.title, "impact": r.impact}
                for r in report.recommendations
            ],
        }

    # ------------------------------------------------------------------
    # FULL CONVERGENCE — All 12 subsystems, autonomous, self-improving
    # ------------------------------------------------------------------
    def converge(self, zones: Optional[list] = None, dry_run: bool = True,
                 max_evolve_cycles: int = 3) -> dict:
        """Execute the FULL CONVERGENCE pipeline — all 12 subsystems in order.

        This is the apex operation. It chains every subsystem in dependency
        order, feeds each subsystem's output into the next, runs self-
        improvement loops, and produces a comprehensive convergence report.

        Pipeline:
            Phase 1 — SCAN:    GENESIS census (all zones)
            Phase 2 — ROUTE:   ORACLE + PROMETHEAN + ELYSIUM per zone (HYDRA-protected)
            Phase 3 — HARVEST: SUPERNOVA parts scan
            Phase 4 — DETECT:  EMERGENCE pattern discovery
            Phase 5 — EVOLVE:  OUROBOROS self-improvement (up to max_evolve_cycles)
            Phase 6 — MEASURE: ESCHATON convergence scoring
            Phase 7 — FUSE:    TRANSCENDENT cross-domain fusion
            Phase 8 — ASSESS:  APOTHEOSIS meta-intelligence (final score)

        Each phase logs progress, catches errors (HYDRA-resilient), and
        feeds forward. The engine self-improves between routing and
        measurement, so each cycle is better than the last.

        Args:
            zones:  Which zones to route. Default: ["ROOT"] (safest).
                    Use ["06_DATA", "04_ANALYSIS"] for wave 1.
            dry_run: True = preview only, False = actually move files.
            max_evolve_cycles: How many OUROBOROS improvement cycles (1-5).

        Returns:
            Comprehensive convergence report dict.
        """
        import time
        t0 = time.time()
        zones = zones or ["ROOT"]

        report = {
            "engine": f"{__codename__} v{__version__} -- FULL CONVERGENCE",
            "mode": "DRY-RUN" if dry_run else "LIVE",
            "zones": zones,
            "phases": {},
            "errors": [],
            "system_score_before": None,
            "system_score_after": None,
        }

        def _phase(name: str, fn, *args, **kwargs):
            """Execute a phase with timing and error capture."""
            log.info("=" * 50)
            log.info("CONVERGENCE PHASE: %s", name)
            log.info("=" * 50)
            pt0 = time.time()
            try:
                result = fn(*args, **kwargs)
                elapsed = time.time() - pt0
                report["phases"][name] = {
                    "status": "OK",
                    "elapsed": round(elapsed, 1),
                    "result": result,
                }
                log.info("[%s] completed in %.1fs", name, elapsed)
                return result
            except Exception as exc:
                elapsed = time.time() - pt0
                err_msg = f"{type(exc).__name__}: {exc}"
                log.error("[%s] FAILED after %.1fs: %s", name, elapsed, err_msg)
                report["phases"][name] = {
                    "status": "FAILED",
                    "elapsed": round(elapsed, 1),
                    "error": err_msg,
                }
                report["errors"].append({"phase": name, "error": err_msg})
                return None

        # ------ PHASE 0: BASELINE ASSESSMENT ------
        baseline = _phase("0_BASELINE", self.meta_assess)
        if baseline:
            report["system_score_before"] = baseline.get("system_score")

        # ------ PHASE 1: GENESIS CENSUS ------
        _phase("1_GENESIS_CENSUS", self.census)

        # ------ PHASE 2: ROUTING per zone (HYDRA-protected) ------
        for zone in zones:
            phase_name = f"2_ROUTE_{zone}"
            _phase(phase_name, self.protected_run, zone, dry_run=dry_run)

        # ------ PHASE 3: SUPERNOVA HARVEST ------
        # Use local targets only (no external drives — speed)
        harvest_targets = [
            str(self.root / "00_SYSTEM"),
            str(self.root / "07_CODE"),
        ]
        _phase("3_SUPERNOVA_HARVEST", self.harvest,
               targets=harvest_targets, digest_limit=5000, profile_limit=5000)

        # ------ PHASE 4: EMERGENCE DETECTION ------
        _phase("4_EMERGENCE_DETECT", self.emergence_scan)

        # ------ PHASE 5: OUROBOROS SELF-IMPROVEMENT (iterative) ------
        evolve_results = []
        for cycle in range(1, max_evolve_cycles + 1):
            phase_name = f"5_EVOLVE_CYCLE_{cycle}"
            result = _phase(phase_name, self.evolve)
            if result:
                evolve_results.append(result)
                delta = result.get("delta", "+0.0%")
                log.info("Evolution cycle %d: accuracy %s -> %s (%s)",
                         cycle, result["accuracy_before"],
                         result["accuracy_after"], delta)
                # Stop early if improvement is negligible
                try:
                    delta_val = float(delta.strip("+%")) / 100
                    if delta_val < 0.005:
                        log.info("Improvement < 0.5%% — stopping evolution early")
                        break
                except (ValueError, ZeroDivisionError):
                    pass
            else:
                break
        report["phases"]["5_EVOLVE_SUMMARY"] = {
            "status": "OK",
            "cycles_run": len(evolve_results),
            "total_mutations": sum(r.get("mutations_accepted", 0) for r in evolve_results),
            "final_accuracy": evolve_results[-1].get("accuracy_after") if evolve_results else "N/A",
        }

        # ------ PHASE 6: ESCHATON CONVERGENCE SCORE ------
        _phase("6_ESCHATON_CONVERGENCE", self.convergence)

        # ------ PHASE 7: TRANSCENDENT FUSION ------
        _phase("7_TRANSCENDENT_FUSE", self.fuse)

        # ------ PHASE 8: APOTHEOSIS FINAL ASSESSMENT ------
        final = _phase("8_APOTHEOSIS_FINAL", self.meta_assess)
        if final:
            report["system_score_after"] = final.get("system_score")

        # ------ SUMMARY ------
        elapsed_total = time.time() - t0
        phases_ok = sum(1 for p in report["phases"].values()
                        if isinstance(p, dict) and p.get("status") == "OK")
        phases_total = len(report["phases"])

        report["summary"] = {
            "phases_passed": f"{phases_ok}/{phases_total}",
            "errors": len(report["errors"]),
            "elapsed_total": f"{elapsed_total:.1f}s",
            "score_delta": _score_delta(
                report["system_score_before"],
                report["system_score_after"],
            ),
            "verdict": "CONVERGED" if not report["errors"] else "PARTIAL",
        }

        return report

    def _print_summary(self, summary: dict):
        """Pretty-print the run summary."""
        s = summary
        q = s["quality"]
        print()
        print(f"+{'='*58}+")
        print(f"|  EVENT HORIZON -- Run Summary{' '*28}|")
        print(f"+{'='*58}+")
        print(f"|  Zone:    {s['zone']:<47}|")
        print(f"|  Mode:    {s['mode']:<47}|")
        print(f"|  Scanned: {s['scan']['total_files']:<47}|")
        print(f"|  Routed:  {s['routing']['routable']:<47}|")
        print(f"|  Moved:   {s['execution']['success']:<47}|")
        print(f"|  Errors:  {s['execution']['errors']:<47}|")
        print(f"+{'='*58}+")
        icon = "PASS" if q["passed"] else "FAIL"
        print(f"||  Quality: [{icon}] {q['gates_passed']}/{q['gates_total']} gates -- score {q['score']:.2f}{' '*14}||")
        for r in q["results"]:
            gi = "OK" if r["passed"] else "XX"
            name = r["gate"][:20].ljust(20)
            print(f"||    [{gi}] {name} {r['score']:.2f}  {r['details'][:25]:<25}||")
        print(f"+{'='*58}+")
        print()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        prog="event_horizon",
        description="EVENT HORIZON Δ∞ — Autonomous filesystem intelligence engine",
    )
    parser.add_argument(
        "--zone", type=str, default="ROOT",
        help="Zone to process: ROOT, 06_DATA, 04_ANALYSIS, etc.",
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=True,
        help="Preview routing decisions without moving files (default)",
    )
    parser.add_argument(
        "--execute", action="store_true",
        help="Actually move files (overrides --dry-run)",
    )
    parser.add_argument(
        "--census", action="store_true",
        help="Quick file count per zone (no routing)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--hydra", action="store_true",
        help="Use HYDRA-protected run (sharding, retry, WAL, genetic memory)",
    )
    parser.add_argument(
        "--verify", action="store_true",
        help="Run integrity verification on a zone (post-run check)",
    )
    parser.add_argument(
        "--evolve", action="store_true",
        help="Run OUROBOROS self-improvement on the latest run",
    )
    parser.add_argument(
        "--convergence", action="store_true",
        help="Measure ESCHATON convergence score",
    )
    parser.add_argument(
        "--dashboard", action="store_true",
        help="Print ESCHATON convergence dashboard",
    )
    parser.add_argument(
        "--harvest", action="store_true",
        help="Run SUPERNOVA parts harvester (scan, classify, rank)",
    )
    parser.add_argument(
        "--harvest-targets", nargs="*", default=None,
        help="Custom target directories for SUPERNOVA harvest",
    )
    parser.add_argument(
        "--harvest-dashboard", action="store_true",
        help="Print SUPERNOVA harvest dashboard",
    )
    parser.add_argument(
        "--emergence", action="store_true",
        help="Run EVENT HORIZON emergence detection (discover novel patterns)",
    )
    parser.add_argument(
        "--emergence-dashboard", action="store_true",
        help="Print EVENT HORIZON emergence dashboard",
    )
    parser.add_argument(
        "--fuse", action="store_true",
        help="Run TRANSCENDENT cross-domain fusion analysis",
    )
    parser.add_argument(
        "--fuse-dashboard", action="store_true",
        help="Print TRANSCENDENT fusion dashboard",
    )
    parser.add_argument(
        "--assess", action="store_true",
        help="Run APOTHEOSIS meta-intelligence assessment",
    )
    parser.add_argument(
        "--god-dashboard", action="store_true",
        help="Print APOTHEOSIS god-layer dashboard (full system overview)",
    )
    parser.add_argument(
        "--converge", action="store_true",
        help="FULL CONVERGENCE: run all 12 subsystems in dependency order",
    )
    parser.add_argument(
        "--converge-zones", nargs="*", default=None,
        help="Zones to route during convergence (default: ROOT)",
    )
    parser.add_argument(
        "--evolve-cycles", type=int, default=3,
        help="Max OUROBOROS self-improvement cycles during convergence (default: 3)",
    )
    parser.add_argument(
        "--root", type=str, default=None,
        help="Repository root (default: auto-detect)",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    root = Path(args.root) if args.root else REPO_ROOT
    engine = Engine(root)

    if args.census:
        census = engine.census()
        if args.json:
            print(json.dumps(census, indent=2))
        else:
            print("\nEVENT HORIZON -- File Census")
            print("-" * 40)
            total = 0
            for zone, count in sorted(census.items()):
                total += max(count, 0)
                indicator = "[!]" if count > 10000 else "[~]" if count > 1000 else "[ ]"
                print(f"  {indicator} {zone:<25} {count:>8,}")
            print("-" * 40)
            print(f"  {'TOTAL':<25} {total:>8,}")
        return

    if args.verify:
        results = engine.hydra.verify_integrity(args.zone)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"\nHYDRA Integrity Verification -- {args.zone}")
            print(f"  Verified: {results['verified']}")
            print(f"  Missing:  {results['missing']}")
        return

    if args.evolve:
        summary = engine.evolve()
        if args.json:
            print(json.dumps(summary, indent=2, default=str))
        else:
            print(f"\nOUROBOROS -- Evolution Cycle {summary['cycle']}")
            print(f"  Run:        {summary['run_id']}")
            print(f"  Weaknesses: {summary['weaknesses']}")
            print(f"  Mutations:  {summary['mutations_accepted']}/{summary['mutations_proposed']}")
            print(f"  Accuracy:   {summary['accuracy_before']} -> {summary['accuracy_after']} ({summary['delta']})")
            print(f"  Lessons:    {summary['lessons_stored']}")
        return

    if args.convergence:
        summary = engine.convergence()
        if args.json:
            print(json.dumps(summary, indent=2, default=str))
        else:
            print(f"\nESCHATON -- Convergence Report")
            print(f"  State:     {summary['state']}")
            print(f"  Score:     {summary['score']}")
            print(f"  Canonical: {summary['files_sorted']:,} / {summary['files_total']:,}")
            print(f"  Root:      {summary['root_files']} loose files")
            if summary['bloated_zones']:
                print(f"  Bloated:   {', '.join(summary['bloated_zones'][:3])}")
            print(f"  Continue:  {'YES' if summary['continue'] else 'CONVERGED'}")
            nxt = summary['next_action']
            print(f"  Next:      {nxt.get('zone', 'NONE')} -- {nxt.get('reason', '')[:60]}")
        return

    if args.dashboard:
        print(engine.eschaton.dashboard())
        return

    if args.harvest:
        summary = engine.harvest(targets=args.harvest_targets)
        if args.json:
            print(json.dumps(summary, indent=2, default=str))
        else:
            s = summary["stats"]
            print(f"\nSUPERNOVA -- Harvest Complete")
            print(f"  Scanned:    {s['files_scanned']:,}")
            print(f"  Hashed:     {s['files_hashed']:,}")
            print(f"  Profiled:   {s['files_profiled']:,}")
            print(f"  Classified: {s['files_classified']:,}")
            print(f"  Clusters:   {s['clusters_found']:,}")
            print(f"  Duplicates: {s['duplicates_found']:,}")
            print(f"  Engines:    {s['your_engines']:,}")
            print(f"  Tools:      {s['your_tools']:,}")
            dup_mb = s['reclaimable_bytes'] / 1_048_576
            print(f"  Reclaimable: {dup_mb:.1f} MB")
            print(f"  Elapsed:    {s['elapsed']:.1f}s")
            if summary.get("forge_recommendations"):
                print(f"\n  Forge Recommendations ({len(summary['forge_recommendations'])}):")
                for rec in summary["forge_recommendations"][:5]:
                    d = rec["dir"]
                    # Show just the last 2 path components
                    short = os.sep.join(d.rsplit(os.sep, 2)[-2:])
                    print(f"    [{rec['relevance']:>5.1f}] {short} ({rec['files']} files)")
        return

    if args.harvest_dashboard:
        print(engine.supernova.dashboard())
        return

    if args.emergence:
        summary = engine.emergence_scan()
        if args.json:
            print(json.dumps(summary, indent=2, default=str))
        else:
            print(f"\nEVENT HORIZON -- Emergence Scan")
            print(f"  Files analyzed: {summary['files_analyzed']:,}")
            print(f"  Signals:        {summary['signals']}")
            print(f"  High-conf:      {summary['high_confidence']}")
            print(f"  Elapsed:        {summary['elapsed']}")
            if summary["detail"]:
                print(f"\n  Signals:")
                for s in summary["detail"][:10]:
                    print(f"    [{s['confidence']:.2f}] {s['type']:<12} {s['description'][:50]}")
        return

    if args.emergence_dashboard:
        print(engine.emergence.dashboard())
        return

    if args.fuse:
        summary = engine.fuse()
        if args.json:
            print(json.dumps(summary, indent=2, default=str))
        else:
            print(f"\nTRANSCENDENT -- Cross-Domain Fusion")
            print(f"  Subsystems:   {', '.join(summary['subsystems_analyzed'])}")
            print(f"  Insights:     {summary['insights']}")
            print(f"  High-impact:  {summary['high_impact']}")
            print(f"  Elapsed:      {summary['elapsed']}")
            if summary["detail"]:
                print(f"\n  Insights:")
                for i in summary["detail"][:10]:
                    icon = {"critical": "!!", "high": ">>", "medium": "--", "low": ".."}.get(i["impact"], "??")
                    print(f"    [{icon}] {i['title'][:55]}")
        return

    if args.fuse_dashboard:
        print(engine.transcendent.dashboard())
        return

    if args.assess:
        summary = engine.meta_assess()
        if args.json:
            print(json.dumps(summary, indent=2, default=str))
        else:
            print(f"\nAPOTHEOSIS -- Meta-Intelligence Assessment")
            print(f"  System Score: {summary['system_score']}")
            print(f"  Active:       {summary['active']}")
            print(f"  Total Rows:   {summary['total_rows']:,}")
            print(f"  Recs:         {summary['recommendations']}")
            if summary["health"]:
                print(f"\n  Subsystem Health:")
                for h in summary["health"]:
                    icon = {"ACTIVE": "OK", "IDLE": "--", "MISSING": "XX"}.get(h["status"], "??")
                    print(f"    [{icon}] {h['subsystem']:<14} {h['lines']:>4}L  {h['rows']:>8,} rows")
        return

    if args.god_dashboard:
        print(engine.apotheosis.dashboard())
        return

    if args.converge:
        dry_run = not args.execute
        summary = engine.converge(
            zones=args.converge_zones,
            dry_run=dry_run,
            max_evolve_cycles=args.evolve_cycles,
        )
        if args.json:
            # Strip large nested results for clean JSON output
            slim = {k: v for k, v in summary.items() if k != "phases"}
            slim["phase_statuses"] = {
                name: p.get("status", "?") if isinstance(p, dict) else "?"
                for name, p in summary.get("phases", {}).items()
            }
            print(json.dumps(slim, indent=2, default=str))
        else:
            s = summary.get("summary", {})
            print()
            print(f"+{'='*62}+")
            print(f"|  EVENT HORIZON v{__version__} -- FULL CONVERGENCE{' '*15}|")
            print(f"+{'='*62}+")
            print(f"|  Mode:          {summary['mode']:<44}|")
            print(f"|  Zones:         {', '.join(summary['zones']):<44}|")
            print(f"|  Phases:        {s.get('phases_passed', '?'):<44}|")
            print(f"|  Errors:        {s.get('errors', '?'):<44}|")
            print(f"|  Elapsed:       {s.get('elapsed_total', '?'):<44}|")
            print(f"|  Score Delta:   {s.get('score_delta', '?'):<44}|")
            print(f"|  Verdict:       {s.get('verdict', '?'):<44}|")
            print(f"+{'='*62}+")
            print()
            # Phase-by-phase summary
            print("  Phase Results:")
            for name, phase in summary.get("phases", {}).items():
                if isinstance(phase, dict):
                    status = phase.get("status", "?")
                    elapsed = phase.get("elapsed", 0)
                    icon = "OK" if status == "OK" else "XX"
                    print(f"    [{icon}] {name:<30} {elapsed:>6.1f}s")
            if summary.get("errors"):
                print()
                print("  Errors:")
                for err in summary["errors"]:
                    print(f"    [{err['phase']}] {err['error'][:60]}")
        return

    dry_run = not args.execute

    if args.hydra:
        summary = engine.protected_run(args.zone, dry_run=dry_run)
    else:
        summary = engine.run(args.zone, dry_run=dry_run)

    if args.json:
        print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()

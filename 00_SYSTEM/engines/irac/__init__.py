"""IRAC Analysis Engine — Automated legal argument synthesis.

Queries irac_analyses table (162+ entries) and generates structured
Issue→Rule→Application→Conclusion arguments for each legal claim.
Integrates with evidence_quotes, authority_chains_v2, and rebuttal_matrix.
"""

__all__ = [
    "IRACArgument",
    "LaneAnalysis",
    "IRACEngine",
    "get_engine",
]

import sqlite3
import json
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parents[3] / "litigation_context.db"

SEPARATION_ANCHOR = datetime(2025, 7, 29)


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA cache_size=-32000")
    return conn


@dataclass
class IRACArgument:
    claim_id: str
    vehicle: str
    lane: str
    issue: str
    rule: str
    application: str
    conclusion: str
    strength: str  # strong, moderate, developing
    evidence_count: int = 0
    defendant: str = ""
    source: str = ""
    rebuttal_count: int = 0
    authority_count: int = 0


@dataclass
class LaneAnalysis:
    lane: str
    total_arguments: int = 0
    strong: int = 0
    moderate: int = 0
    developing: int = 0
    evidence_total: int = 0
    arguments: list = field(default_factory=list)


class IRACEngine:
    """Automated IRAC analysis engine for Pigors v Watson litigation."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or str(DB_PATH)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=60000")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA cache_size=-32000")
        return conn

    def get_argument(self, claim_id: str) -> Optional[IRACArgument]:
        """Get a single IRAC argument by claim_id."""
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM irac_analyses WHERE claim_id = ? LIMIT 1",
                (claim_id,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_arg(row, conn)
        finally:
            conn.close()

    def get_arguments_by_lane(self, lane: str, strength_filter: Optional[str] = None) -> list:
        """Get all IRAC arguments for a filing lane."""
        conn = self._conn()
        try:
            if strength_filter:
                rows = conn.execute(
                    "SELECT * FROM irac_analyses WHERE lane = ? AND strength = ? ORDER BY claim_id",
                    (lane, strength_filter)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM irac_analyses WHERE lane = ? ORDER BY strength DESC, claim_id",
                    (lane,)
                ).fetchall()
            return [self._row_to_arg(r, conn) for r in rows]
        finally:
            conn.close()

    def get_strong_arguments(self) -> list:
        """Get all 'strong' IRAC arguments across all lanes."""
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT * FROM irac_analyses WHERE strength = 'strong' ORDER BY lane, claim_id"
            ).fetchall()
            return [self._row_to_arg(r, conn) for r in rows]
        finally:
            conn.close()

    def get_lane_analysis(self, lane: str) -> LaneAnalysis:
        """Get comprehensive analysis for a lane with strength breakdown."""
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT * FROM irac_analyses WHERE lane = ? ORDER BY strength DESC",
                (lane,)
            ).fetchall()
            args = [self._row_to_arg(r, conn) for r in rows]
            analysis = LaneAnalysis(
                lane=lane,
                total_arguments=len(args),
                strong=sum(1 for a in args if a.strength == "strong"),
                moderate=sum(1 for a in args if a.strength == "moderate"),
                developing=sum(1 for a in args if a.strength == "developing"),
                evidence_total=sum(a.evidence_count for a in args),
                arguments=args,
            )
            return analysis
        finally:
            conn.close()

    def get_all_lanes_summary(self) -> dict:
        """Get summary across all lanes."""
        conn = self._conn()
        try:
            rows = conn.execute("""
                SELECT lane, strength, COUNT(*) as cnt, SUM(evidence_count) as ev
                FROM irac_analyses GROUP BY lane, strength ORDER BY lane
            """).fetchall()
            summary = {}
            for r in rows:
                lane = r["lane"]
                if lane not in summary:
                    summary[lane] = {"total": 0, "strong": 0, "moderate": 0, "developing": 0, "evidence": 0}
                summary[lane][r["strength"]] = r["cnt"]
                summary[lane]["total"] += r["cnt"]
                summary[lane]["evidence"] += r["ev"] or 0
            return summary
        finally:
            conn.close()

    def generate_brief_section(self, lane: str, max_arguments: int = 10) -> str:
        """Generate a court-ready argument section from IRAC analyses.

        Outputs IRAC-structured text suitable for inclusion in motions/briefs.
        Dynamic separation day count computed at generation time.
        """
        args = self.get_arguments_by_lane(lane, strength_filter="strong")
        if not args:
            args = self.get_arguments_by_lane(lane)
        args = args[:max_arguments]

        sep_days = (datetime.now() - SEPARATION_ANCHOR).days
        sections = []
        for i, arg in enumerate(args, 1):
            text = arg.application or ""
            # Dynamic day count replacement
            text = text.replace("[SEPARATION_DAYS]", str(sep_days))
            text = text.replace("329 consecutive days", f"{sep_days} consecutive days")

            section = f"""### {i}. {arg.issue}

**Issue:** {arg.issue}

**Rule:** {arg.rule}

**Application:** {text}

**Conclusion:** {arg.conclusion}
"""
            sections.append(section)

        header = f"## ARGUMENT (Lane {lane} — {len(args)} Issues)\n\n"
        return header + "\n---\n\n".join(sections)

    def find_gaps(self) -> list:
        """Find lanes with weak or missing IRAC coverage."""
        conn = self._conn()
        try:
            expected_lanes = {"A", "B", "C", "D", "E", "F"}
            rows = conn.execute(
                "SELECT DISTINCT lane FROM irac_analyses"
            ).fetchall()
            covered = {r["lane"] for r in rows}
            gaps = []

            for lane in expected_lanes:
                if lane not in covered:
                    gaps.append({"lane": lane, "issue": "NO IRAC coverage", "severity": "CRITICAL"})
                    continue
                analysis = self.get_lane_analysis(lane)
                if analysis.strong == 0:
                    gaps.append({"lane": lane, "issue": "No strong arguments", "severity": "HIGH"})
                if analysis.total_arguments < 3:
                    gaps.append({"lane": lane, "issue": f"Only {analysis.total_arguments} arguments (need 3+)", "severity": "MEDIUM"})

            return gaps
        finally:
            conn.close()

    def get_rebuttal_support(self, claim_id: str) -> list:
        """Get rebuttal matrix entries supporting an IRAC argument."""
        conn = self._conn()
        try:
            # Match by claim_id pattern in filing_use
            rows = conn.execute(
                "SELECT adversary, claim_text, rebuttal_text, strength, lane "
                "FROM rebuttal_matrix WHERE filing_use LIKE ? OR claim_type LIKE ? "
                "ORDER BY strength DESC LIMIT 20",
                (f"%{claim_id}%", f"%{claim_id}%")
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def _row_to_arg(self, row: sqlite3.Row, conn: sqlite3.Connection) -> IRACArgument:
        """Convert a DB row to an IRACArgument with enrichment."""
        arg = IRACArgument(
            claim_id=row["claim_id"] or "",
            vehicle=row["vehicle_name"] or "",
            lane=row["lane"] or "",
            issue=row["issue"] or "",
            rule=row["rule"] or "",
            application=row["application"] or "",
            conclusion=row["conclusion"] or "",
            strength=row["strength"] or "moderate",
            evidence_count=row["evidence_count"] or 0,
            defendant=row["defendant"] or "",
            source=row["source"] or "",
        )
        # Enrich with rebuttal count
        try:
            reb = conn.execute(
                "SELECT COUNT(*) as cnt FROM rebuttal_matrix WHERE lane = ?",
                (arg.lane,)
            ).fetchone()
            arg.rebuttal_count = reb["cnt"] if reb else 0
        except Exception:
            pass
        return arg

    def to_json(self, lane: Optional[str] = None) -> str:
        """Export analysis as JSON."""
        if lane:
            analysis = self.get_lane_analysis(lane)
            data = {
                "lane": analysis.lane,
                "total": analysis.total_arguments,
                "strong": analysis.strong,
                "moderate": analysis.moderate,
                "developing": analysis.developing,
                "arguments": [asdict(a) for a in analysis.arguments],
            }
        else:
            data = self.get_all_lanes_summary()
        return json.dumps(data, indent=2, default=str)


def get_engine(**kwargs) -> IRACEngine:
    """Factory function for engine registry."""
    return IRACEngine(**kwargs)

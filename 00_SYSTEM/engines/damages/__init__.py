"""Dynamic Damages Calculator Engine — Per-lane, treble, §1983 punitive.

Queries damages_calculation table (30+ entries) and computes dynamic totals
with separation day multipliers and statutory caps/treble damages.
"""

__all__ = [
    "DamageItem",
    "LaneDamages",
    "TotalDamages",
    "DamagesEngine",
    "get_engine",
]

import sqlite3
import json
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path
from datetime import datetime, date

DB_PATH = Path(__file__).resolve().parents[3] / "litigation_context.db"

SEPARATION_ANCHOR = date(2025, 7, 29)

# Statutory multipliers and caps
TREBLE_DAMAGES_LANES = {"B"}  # Housing: MCL 600.2919 treble damages
SECTION_1983_LANES = {"C", "E"}  # Federal civil rights — punitive multiplier
PUNITIVE_MULTIPLIER_1983 = 3.0  # Typical §1983 punitive ratio

# Per-day rates for dynamic computation
PER_DAY_RATES = {
    "custody_deprivation": {"conservative": 100, "aggressive": 500},
    "parenting_time_loss": {"conservative": 75, "aggressive": 300},
    "wrongful_imprisonment": {"conservative": 137, "aggressive": 500},
    "appeal_deprivation": {"conservative": 75, "aggressive": 450},
}


def _separation_days() -> int:
    """Dynamic separation day count from Jul 29, 2025."""
    return (date.today() - SEPARATION_ANCHOR).days


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA cache_size=-32000")
    return conn


@dataclass
class DamageItem:
    lane: str
    category: str
    description: str
    conservative: float
    aggressive: float
    basis: str
    evidence_source: str = ""
    is_dynamic: bool = False  # True if computed from separation days
    multiplier: float = 1.0


@dataclass
class LaneDamages:
    lane: str
    items: list = field(default_factory=list)
    subtotal_conservative: float = 0.0
    subtotal_aggressive: float = 0.0
    treble_applied: bool = False
    punitive_applied: bool = False
    total_conservative: float = 0.0
    total_aggressive: float = 0.0


@dataclass
class TotalDamages:
    lanes: dict = field(default_factory=dict)
    grand_conservative: float = 0.0
    grand_aggressive: float = 0.0
    separation_days: int = 0
    computed_at: str = ""


class DamagesEngine:
    """Dynamic damages calculator for Pigors v Watson litigation."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or str(DB_PATH)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=60000")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA cache_size=-32000")
        return conn

    def get_lane_damages(self, lane: str) -> LaneDamages:
        """Get damages for a specific lane with dynamic computation."""
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT * FROM damages_calculation WHERE lane = ? AND is_summary = 0 ORDER BY category",
                (lane,)
            ).fetchall()

            sep_days = _separation_days()
            items = []

            for r in rows:
                cat = r["category"].lower() if r["category"] else ""
                con = r["conservative_amount"] or 0
                agg = r["aggressive_amount"] or 0
                is_dynamic = False

                # Dynamic per-day computation for time-based damages
                if "per-day" in cat or "per day" in cat:
                    for rate_key, rates in PER_DAY_RATES.items():
                        if rate_key.replace("_", " ") in cat.replace("-", " ").replace("—", " "):
                            con = rates["conservative"] * sep_days
                            agg = rates["aggressive"] * sep_days
                            is_dynamic = True
                            break
                elif con == 0 and agg == 0 and ("deprivation" in cat or "liberty" in cat):
                    # Aggregate liberty items — compute from per-day
                    con = PER_DAY_RATES["custody_deprivation"]["conservative"] * sep_days
                    agg = PER_DAY_RATES["custody_deprivation"]["aggressive"] * sep_days
                    is_dynamic = True

                items.append(DamageItem(
                    lane=lane,
                    category=r["category"],
                    description=r["description"] or r["category"],
                    conservative=con,
                    aggressive=agg,
                    basis=r["basis"] or "",
                    evidence_source=r["evidence_source"] or "",
                    is_dynamic=is_dynamic,
                ))

            subtotal_con = sum(i.conservative for i in items)
            subtotal_agg = sum(i.aggressive for i in items)
            total_con = subtotal_con
            total_agg = subtotal_agg
            treble = False
            punitive = False

            # Apply treble damages for housing (Lane B)
            if lane in TREBLE_DAMAGES_LANES:
                total_con = subtotal_con * 3
                total_agg = subtotal_agg * 3
                treble = True

            # Apply punitive multiplier for §1983 lanes
            if lane in SECTION_1983_LANES:
                total_con = subtotal_con + (subtotal_con * PUNITIVE_MULTIPLIER_1983)
                total_agg = subtotal_agg + (subtotal_agg * PUNITIVE_MULTIPLIER_1983)
                punitive = True

            return LaneDamages(
                lane=lane,
                items=items,
                subtotal_conservative=subtotal_con,
                subtotal_aggressive=subtotal_agg,
                treble_applied=treble,
                punitive_applied=punitive,
                total_conservative=total_con,
                total_aggressive=total_agg,
            )
        finally:
            conn.close()

    def get_total_damages(self) -> TotalDamages:
        """Compute total damages across all lanes."""
        conn = self._conn()
        try:
            lane_rows = conn.execute(
                "SELECT DISTINCT lane FROM damages_calculation WHERE is_summary = 0"
            ).fetchall()
            lanes = [r["lane"] for r in lane_rows]

            result = TotalDamages(
                separation_days=_separation_days(),
                computed_at=datetime.now().isoformat(),
            )

            for lane in lanes:
                ld = self.get_lane_damages(lane)
                result.lanes[lane] = ld
                result.grand_conservative += ld.total_conservative
                result.grand_aggressive += ld.total_aggressive

            return result
        finally:
            conn.close()

    def get_damages_summary_text(self) -> str:
        """Generate court-ready damages summary text."""
        total = self.get_total_damages()
        sep = total.separation_days

        lines = [
            f"## DAMAGES SUMMARY (Computed {datetime.now().strftime('%B %d, %Y')})",
            f"### Separation: {sep} consecutive days since July 29, 2025\n",
        ]

        for lane_key in sorted(total.lanes.keys()):
            ld = total.lanes[lane_key]
            lane_name = {
                "A": "Custody/Parenting (Lane A)",
                "B": "Housing (Lane B — Treble Damages)",
                "C": "Federal §1983 (Lane C — Punitive)",
                "D": "PPO/Contempt (Lane D)",
                "E": "Judicial Misconduct §1983 (Lane E — Punitive)",
                "F": "Appellate (Lane F)",
            }.get(lane_key, f"Lane {lane_key}")

            lines.append(f"### {lane_name}")
            for item in ld.items:
                dynamic_tag = " *(dynamic)*" if item.is_dynamic else ""
                lines.append(
                    f"- {item.category}: ${item.conservative:,.0f} – ${item.aggressive:,.0f}{dynamic_tag}"
                )
            lines.append(f"  **Subtotal:** ${ld.subtotal_conservative:,.0f} – ${ld.subtotal_aggressive:,.0f}")
            if ld.treble_applied:
                lines.append(f"  **After Treble (MCL 600.2919):** ${ld.total_conservative:,.0f} – ${ld.total_aggressive:,.0f}")
            if ld.punitive_applied:
                lines.append(f"  **After Punitive (§1983 3x):** ${ld.total_conservative:,.0f} – ${ld.total_aggressive:,.0f}")
            lines.append("")

        lines.append(f"### GRAND TOTAL")
        lines.append(f"- **Conservative:** ${total.grand_conservative:,.0f}")
        lines.append(f"- **Aggressive:** ${total.grand_aggressive:,.0f}")
        lines.append(f"\n*All per-day calculations use {sep} days from July 29, 2025.*")

        return "\n".join(lines)

    def get_filing_damages(self, lane: str) -> str:
        """Get damages text formatted for inclusion in a specific filing."""
        ld = self.get_lane_damages(lane)
        sep = _separation_days()

        lines = [f"Plaintiff seeks the following damages:\n"]
        for i, item in enumerate(ld.items, 1):
            dynamic = f" ({sep} days × per-day rate)" if item.is_dynamic else ""
            lines.append(f"{i}. **{item.category}**: ${item.conservative:,.0f} to ${item.aggressive:,.0f}{dynamic}")
            if item.basis:
                lines.append(f"   *Basis: {item.basis}*")

        if ld.treble_applied:
            lines.append(f"\nPlaintiff is entitled to treble damages under MCL 600.2919, "
                         f"yielding a range of ${ld.total_conservative:,.0f} to ${ld.total_aggressive:,.0f}.")
        elif ld.punitive_applied:
            lines.append(f"\nPunitive damages under 42 USC §1983 are warranted given the "
                         f"deliberate and knowing nature of the constitutional violations, "
                         f"yielding a range of ${ld.total_conservative:,.0f} to ${ld.total_aggressive:,.0f}.")

        return "\n".join(lines)

    def to_json(self) -> str:
        """Export full damages calculation as JSON."""
        total = self.get_total_damages()
        data = {
            "separation_days": total.separation_days,
            "computed_at": total.computed_at,
            "grand_conservative": total.grand_conservative,
            "grand_aggressive": total.grand_aggressive,
            "lanes": {},
        }
        for k, ld in total.lanes.items():
            data["lanes"][k] = {
                "subtotal_conservative": ld.subtotal_conservative,
                "subtotal_aggressive": ld.subtotal_aggressive,
                "total_conservative": ld.total_conservative,
                "total_aggressive": ld.total_aggressive,
                "treble": ld.treble_applied,
                "punitive": ld.punitive_applied,
                "items": [asdict(i) for i in ld.items],
            }
        return json.dumps(data, indent=2, default=str)


def get_engine(**kwargs) -> DamagesEngine:
    """Factory function for engine registry."""
    return DamagesEngine(**kwargs)

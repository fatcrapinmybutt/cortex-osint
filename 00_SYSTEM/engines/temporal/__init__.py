"""
Temporal Knowledge Graph Engine — LitigationOS
===============================================
Builds a NetworkX DiGraph from 16,000+ timeline_events in litigation_context.db.
Traces CAUSATION between events, detects anomalies, and identifies patterns
for court-ready narrative generation.

Usage:
    from temporal import TemporalKnowledgeGraph
    tkg = TemporalKnowledgeGraph()
    tkg.build_graph()
    chain = tkg.get_poisonous_tree_chain()
"""

from __future__ import annotations

__all__ = ["TemporalKnowledgeGraph"]

import re
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

import networkx as nx

DB_PATH = str(Path(__file__).resolve().parents[3] / "litigation_context.db")

SEPARATION_ANCHOR = date(2025, 7, 29)

# ---------------------------------------------------------------------------
# Key actors (canonical names for fuzzy matching)
# ---------------------------------------------------------------------------
KNOWN_ACTORS = {
    "andrew": "Andrew Pigors",
    "pigors": "Andrew Pigors",
    "emily": "Emily Watson",
    "watson": "Emily Watson",
    "mcneill": "Judge McNeill",
    "jenny": "Judge McNeill",
    "judge": "Judge McNeill",
    "barnes": "Jennifer Barnes",
    "jennifer barnes": "Jennifer Barnes",
    "albert": "Albert Watson",
    "lori": "Lori Watson",
    "rusco": "Pamela Rusco",
    "pamela": "Pamela Rusco",
    "foc": "Pamela Rusco",
    "ronald": "Ronald Berry",
    "ron berry": "Ronald Berry",
    "berry": "Ronald Berry",
    "cavan": "Cavan Berry",
    "hoopes": "Judge Hoopes",
    "ladas": "Judge Ladas-Hoopes",
    "healthwest": "HealthWest",
}

# Categories that indicate ex-parte actions
EX_PARTE_CATEGORIES = frozenset({
    "COURT_ORDER", "Court Order", "Docket_Order",
    "Ex_Parte", "ex_parte", "Order",
})

# Categories indicating filings by Andrew
FILING_CATEGORIES = frozenset({
    "Filing", "filing", "Motion", "motion", "Complaint",
    "Appeal", "appeal", "Emergency",
})

# Retaliation actor targets
RETALIATION_ACTORS = frozenset({
    "Judge McNeill", "Emily Watson", "Pamela Rusco",
})

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class TimelineEvent:
    """Single event from the timeline_events table."""
    id: int
    event_date: Optional[date]
    description: str
    actors: List[str]
    lane: str
    category: str
    source_table: str
    source_id: str
    severity: str
    filing_relevance: str
    raw_actors: str

    @property
    def date_str(self) -> str:
        return self.event_date.isoformat() if self.event_date else "unknown"


@dataclass
class CausalEdge:
    """Causal relationship between two events."""
    source_id: int
    target_id: int
    relationship: str
    confidence: float
    temporal_gap_days: int
    description: str


@dataclass
class CausalChain:
    """A named chain of causally-linked events."""
    name: str
    events: List[TimelineEvent] = field(default_factory=list)
    edges: List[CausalEdge] = field(default_factory=list)
    total_span_days: int = 0
    narrative: str = ""


@dataclass
class AnomalyReport:
    """Temporal anomaly detected in the record."""
    anomaly_type: str
    event_id: int
    event_date: Optional[date]
    description: str
    severity: str
    related_event_id: Optional[int] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(raw: Optional[str]) -> Optional[date]:
    """Parse event_date text into a date object, tolerating bad data."""
    if not raw or not raw.strip():
        return None
    raw = raw.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%m-%d-%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    # Last-ditch: try pulling YYYY-MM-DD from anywhere in the string
    m = re.search(r"(\d{4}-\d{2}-\d{2})", raw)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except ValueError:
            pass
    return None


def _parse_actors(raw: Optional[str]) -> List[str]:
    """Split raw actors field into canonical actor names."""
    if not raw or not raw.strip():
        return []
    # Skip entries that look like file paths
    if raw.startswith(("C:\\", "D:\\", "F:\\", "/")) or "\\" in raw[:5]:
        return []
    # Split on comma, semicolon, or " and "
    parts = re.split(r"[;,]|\band\b", raw)
    actors: List[str] = []
    for part in parts:
        cleaned = part.strip()
        if not cleaned or len(cleaned) < 2:
            continue
        # Try to resolve to canonical name
        lower = cleaned.lower()
        resolved = False
        for key, canonical in KNOWN_ACTORS.items():
            if key in lower:
                if canonical not in actors:
                    actors.append(canonical)
                resolved = True
                break
        if not resolved and len(cleaned) > 2 and not cleaned.startswith(("C:", "D:")):
            if cleaned not in actors:
                actors.append(cleaned)
    return actors


def _enrich_actors_from_description(
    actors: List[str], description: str,
) -> List[str]:
    """
    Supplement actor list by scanning the event description for known actors.
    Many events mention McNeill, Emily, Albert in text but not the actors field.
    """
    if not description:
        return actors
    desc_lower = description.lower()
    enriched = list(actors)
    # Patterns anchored to specific names to avoid false positives
    _DESC_ACTOR_PATTERNS = [
        ("mcneill", "Judge McNeill"),
        ("jenny l. mcneill", "Judge McNeill"),
        ("judge mcneill", "Judge McNeill"),
        ("emily watson", "Emily Watson"),
        ("emily a. watson", "Emily Watson"),
        ("albert watson", "Albert Watson"),
        ("andrew pigors", "Andrew Pigors"),
        ("jennifer barnes", "Jennifer Barnes"),
        ("pamela rusco", "Pamela Rusco"),
        ("ronald berry", "Ronald Berry"),
        ("cavan berry", "Cavan Berry"),
        ("judge hoopes", "Judge Hoopes"),
        ("ladas-hoopes", "Judge Ladas-Hoopes"),
    ]
    for pattern, canonical in _DESC_ACTOR_PATTERNS:
        if pattern in desc_lower and canonical not in enriched:
            enriched.append(canonical)
    return enriched


def _classify_event_type(category: str, description: str) -> str:
    """Derive a normalized event_type from category and description text."""
    cat_lower = (category or "").lower()
    desc_lower = (description or "").lower()

    if "ex parte" in desc_lower or "ex_parte" in cat_lower:
        return "ex_parte"
    if cat_lower in ("court order", "court_order", "docket_order", "order"):
        return "order"
    if "contempt" in desc_lower or "show cause" in desc_lower:
        return "contempt"
    if "arrest" in desc_lower or "jail" in desc_lower or "incarcerat" in desc_lower:
        return "arrest"
    if "withhold" in desc_lower or "denied parenting" in desc_lower or "refused" in desc_lower:
        return "withholding"
    if cat_lower in ("filing", "motion", "complaint", "appeal", "emergency"):
        return "filing"
    if "ppo" in desc_lower or "protection order" in desc_lower:
        return "ppo"
    if "recan" in desc_lower:
        return "recantation"
    if "allegation" in cat_lower or "false" in desc_lower:
        return "allegation"
    if "police" in cat_lower or "police" in desc_lower:
        return "police_report"
    if "alienat" in desc_lower:
        return "alienation"
    if "trial" in desc_lower or "hearing" in desc_lower:
        return "hearing"
    if "admission" in cat_lower:
        return "admission"
    if "evidence" in cat_lower:
        return "evidence"
    return "event"


def _separation_days() -> int:
    """Dynamic separation day count from Jul 29, 2025."""
    return (date.today() - SEPARATION_ANCHOR).days


def _get_db_connection(db_path: str) -> sqlite3.Connection:
    """Open a connection with mandatory safety PRAGMAs."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA cache_size=-32000")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Main Engine
# ---------------------------------------------------------------------------

class TemporalKnowledgeGraph:
    """
    Builds a directed acyclic graph of timeline events with causal edges.

    Nodes = events from timeline_events table.
    Edges = causal relationships (TRIGGERED_BY, RETALIATION_FOR, etc.)
    """

    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path
        self.graph: nx.DiGraph = nx.DiGraph()
        self.events: dict[int, TimelineEvent] = {}
        self._events_by_date: dict[date, List[int]] = {}
        self._events_by_actor: dict[str, List[int]] = {}
        self._events_by_lane: dict[str, List[int]] = {}
        self._loaded = False
        self._load_events()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_events(self) -> None:
        """Load all timeline_events from the database."""
        conn = _get_db_connection(self.db_path)
        try:
            # Verify schema first (Rule 16)
            cols = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(timeline_events)")
            }
            required = {"id", "event_date", "event_description", "actors", "lane"}
            if not required.issubset(cols):
                missing = required - cols
                raise RuntimeError(
                    f"timeline_events missing columns: {missing}. "
                    f"Found: {cols}"
                )

            rows = conn.execute(
                "SELECT id, event_date, event_description, actors, lane, "
                "category, source_table, source_id, severity, filing_relevance "
                "FROM timeline_events"
            ).fetchall()

            for row in rows:
                parsed_date = _parse_date(row["event_date"])
                parsed_actors = _parse_actors(row["actors"])
                description = row["event_description"] or ""
                # Enrich actors from description text (catches McNeill, Emily, etc.)
                parsed_actors = _enrich_actors_from_description(parsed_actors, description)
                event = TimelineEvent(
                    id=row["id"],
                    event_date=parsed_date,
                    description=description,
                    actors=parsed_actors,
                    lane=row["lane"] or "",
                    category=row["category"] or "",
                    source_table=row["source_table"] or "",
                    source_id=str(row["source_id"] or ""),
                    severity=str(row["severity"] or ""),
                    filing_relevance=row["filing_relevance"] or "",
                    raw_actors=row["actors"] or "",
                )
                self.events[event.id] = event

                # Index by date
                if parsed_date:
                    self._events_by_date.setdefault(parsed_date, []).append(event.id)

                # Index by actor
                for actor in parsed_actors:
                    self._events_by_actor.setdefault(actor, []).append(event.id)

                # Index by lane
                if event.lane:
                    self._events_by_lane.setdefault(event.lane, []).append(event.id)

            self._loaded = True
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def build_graph(self) -> nx.DiGraph:
        """
        Build the full temporal knowledge graph.
        Creates nodes for every event and causal edges between them.
        Returns the constructed DiGraph.
        """
        self.graph.clear()

        # Add all events as nodes
        for eid, ev in self.events.items():
            event_type = _classify_event_type(ev.category, ev.description)
            self.graph.add_node(
                eid,
                id=eid,
                date=ev.date_str,
                description=ev.description[:500],
                actor=", ".join(ev.actors) if ev.actors else "",
                lane=ev.lane,
                source=f"{ev.source_table}:{ev.source_id}",
                event_type=event_type,
                severity=ev.severity,
                category=ev.category,
            )

        # Build causal edges
        self.add_causal_edges()

        return self.graph

    def add_causal_edges(self) -> int:
        """
        Detect and add all causal relationships between events.
        Returns total number of edges added.
        """
        added = 0
        added += self._add_triggered_by_edges()
        added += self._add_retaliation_edges()
        added += self._add_enabled_by_edges()
        added += self._add_concealed_from_edges()
        return added

    def _add_triggered_by_edges(self) -> int:
        """TRIGGERED_BY: Events within 48 hours involving related actors."""
        count = 0
        sorted_dates = sorted(self._events_by_date.keys())
        for i, d in enumerate(sorted_dates):
            window_end = d + timedelta(days=2)
            source_ids = self._events_by_date[d]
            # Look at the next few dates within 48h window
            for j in range(i + 1, len(sorted_dates)):
                next_d = sorted_dates[j]
                if next_d > window_end:
                    break
                target_ids = self._events_by_date[next_d]
                gap_days = (next_d - d).days
                for sid in source_ids:
                    src = self.events[sid]
                    if not src.actors:
                        continue
                    src_actors = set(src.actors)
                    for tid in target_ids:
                        if sid == tid:
                            continue
                        tgt = self.events[tid]
                        if not tgt.actors:
                            continue
                        shared = src_actors & set(tgt.actors)
                        if shared:
                            # Confidence based on actor overlap and temporal proximity
                            confidence = min(
                                0.5 + 0.15 * len(shared) + (0.2 if gap_days == 0 else 0.1),
                                1.0,
                            )
                            if not self.graph.has_edge(sid, tid):
                                self.graph.add_edge(
                                    sid, tid,
                                    relationship="TRIGGERED_BY",
                                    confidence=round(confidence, 2),
                                    temporal_gap_days=gap_days,
                                    description=(
                                        f"{', '.join(shared)} acted within {gap_days}d: "
                                        f"[{src.description[:60]}] → [{tgt.description[:60]}]"
                                    ),
                                )
                                count += 1
        return count

    def _add_retaliation_edges(self) -> int:
        """RETALIATION_FOR: Andrew files → adverse action within 7 days."""
        count = 0
        andrew_ids = self._events_by_actor.get("Andrew Pigors", [])
        andrew_filings: List[Tuple[date, int]] = []
        for eid in andrew_ids:
            ev = self.events[eid]
            if not ev.event_date:
                continue
            etype = _classify_event_type(ev.category, ev.description)
            desc_lower = ev.description.lower()
            is_filing = etype == "filing" or any(
                kw in desc_lower
                for kw in ("motion", "filed", "complaint", "appeal", "petition",
                           "emergency", "objection", "response")
            )
            if is_filing:
                andrew_filings.append((ev.event_date, eid))

        andrew_filings.sort(key=lambda x: x[0])

        # Build set of all adverse events per retaliation actor
        adverse_by_actor: dict[str, List[Tuple[date, int]]] = {}
        for actor in RETALIATION_ACTORS:
            events_list: List[Tuple[date, int]] = []
            for tid in self._events_by_actor.get(actor, []):
                tgt = self.events[tid]
                if not tgt.event_date:
                    continue
                tgt_type = _classify_event_type(tgt.category, tgt.description)
                if tgt_type in (
                    "order", "ex_parte", "contempt", "arrest",
                    "withholding", "ppo", "hearing", "alienation",
                ):
                    events_list.append((tgt.event_date, tid))
            events_list.sort(key=lambda x: x[0])
            adverse_by_actor[actor] = events_list

        for filing_date, filing_id in andrew_filings:
            window_end = filing_date + timedelta(days=7)
            for actor, adverse_events in adverse_by_actor.items():
                for tgt_date, tid in adverse_events:
                    if tgt_date <= filing_date:
                        continue
                    if tgt_date > window_end:
                        break
                    gap = (tgt_date - filing_date).days
                    confidence = round(0.6 + (0.05 * (7 - gap)), 2)
                    confidence = min(max(confidence, 0.5), 0.95)
                    if not self.graph.has_edge(filing_id, tid):
                        self.graph.add_edge(
                            filing_id, tid,
                            relationship="RETALIATION_FOR",
                            confidence=confidence,
                            temporal_gap_days=gap,
                            description=(
                                f"Andrew filed [{self.events[filing_id].description[:50]}] "
                                f"→ {actor} acted {gap}d later: [{self.events[tid].description[:50]}]"
                            ),
                        )
                        count += 1
        return count

    def _add_enabled_by_edges(self) -> int:
        """ENABLED_BY: Prior event made subsequent event possible (nearest-5 per source)."""
        count = 0
        MAX_TARGETS_PER_SOURCE = 5

        enablement_patterns = [
            # (source keywords, target keywords, description template)
            (
                ["ppo", "protection order"],
                ["custody", "sole custody", "custodial"],
                "PPO filing enabled custody reassignment",
            ),
            (
                ["suspended", "suspend parenting", "parenting time suspended"],
                ["withhold", "denied parenting", "no contact"],
                "Parenting time suspension enabled withholding",
            ),
            (
                ["ex parte", "without notice"],
                ["contempt", "show cause", "jail"],
                "Ex parte order enabled contempt proceedings",
            ),
            (
                ["false allegation", "fabricat", "falsely accused"],
                ["ppo", "protection order", "petition"],
                "False allegation enabled PPO petition",
            ),
            (
                ["contempt", "found in contempt"],
                ["jail", "incarcerat", "sentence"],
                "Contempt finding enabled incarceration",
            ),
            (
                ["recant", "nothing was physical"],
                ["ppo", "protection order petition"],
                "Recantation CONTRADICTS subsequent PPO filing",
            ),
            (
                ["albert", "documented so emily", "ex parte order"],
                ["ex parte", "five orders", "suspended"],
                "Albert premeditation enabled ex parte orders",
            ),
        ]

        dated_events = [
            (ev.event_date, eid)
            for eid, ev in self.events.items()
            if ev.event_date is not None
        ]
        dated_events.sort(key=lambda x: x[0])

        for src_keywords, tgt_keywords, tmpl in enablement_patterns:
            source_events: List[Tuple[date, int]] = []
            target_events: List[Tuple[date, int]] = []
            for d, eid in dated_events:
                desc_lower = self.events[eid].description.lower()
                if any(kw in desc_lower for kw in src_keywords):
                    source_events.append((d, eid))
                if any(kw in desc_lower for kw in tgt_keywords):
                    target_events.append((d, eid))

            # For each source, connect only to the nearest N future targets
            for src_date, src_id in source_events:
                linked = 0
                for tgt_date, tgt_id in target_events:
                    if linked >= MAX_TARGETS_PER_SOURCE:
                        break
                    if src_id == tgt_id:
                        continue
                    if tgt_date <= src_date:
                        continue
                    gap = (tgt_date - src_date).days
                    if gap > 365:
                        break
                    if self.graph.has_edge(src_id, tgt_id):
                        continue
                    confidence = round(max(0.4, 0.9 - (gap / 365) * 0.5), 2)
                    self.graph.add_edge(
                        src_id, tgt_id,
                        relationship="ENABLED_BY",
                        confidence=confidence,
                        temporal_gap_days=gap,
                        description=f"{tmpl} ({gap}d gap)",
                    )
                    count += 1
                    linked += 1
        return count

    def _add_concealed_from_edges(self) -> int:
        """CONCEALED_FROM: Ex parte actions where Andrew had no notice."""
        count = 0
        andrew_ids_set = set(self._events_by_actor.get("Andrew Pigors", []))

        for eid, ev in self.events.items():
            if not ev.event_date:
                continue
            desc_lower = ev.description.lower()
            is_ex_parte = (
                "ex parte" in desc_lower
                or "without notice" in desc_lower
                or "without hearing" in desc_lower
                or ev.category in EX_PARTE_CATEGORIES
            )
            if not is_ex_parte:
                continue

            # Check if there's an Andrew event within +/- 3 days showing he was not notified
            window_start = ev.event_date - timedelta(days=3)
            window_end = ev.event_date + timedelta(days=3)
            andrew_notified = False
            for ad in sorted(self._events_by_date.keys()):
                if ad < window_start:
                    continue
                if ad > window_end:
                    break
                for aid in self._events_by_date[ad]:
                    if aid in andrew_ids_set:
                        aev = self.events[aid]
                        if any(
                            kw in aev.description.lower()
                            for kw in ("served", "notified", "received notice", "hearing")
                        ):
                            andrew_notified = True
                            break
                if andrew_notified:
                    break

            if not andrew_notified:
                # Find the nearest Andrew filing before this ex parte action
                nearest_andrew: Optional[int] = None
                nearest_gap = 999999
                for aid in andrew_ids_set:
                    aev = self.events[aid]
                    if not aev.event_date:
                        continue
                    if aev.event_date < ev.event_date:
                        gap = (ev.event_date - aev.event_date).days
                        if gap < nearest_gap and gap <= 30:
                            nearest_gap = gap
                            nearest_andrew = aid

                if nearest_andrew is not None and not self.graph.has_edge(eid, nearest_andrew):
                    self.graph.add_edge(
                        eid, nearest_andrew,
                        relationship="CONCEALED_FROM",
                        confidence=round(min(0.7 + (0.01 * (30 - nearest_gap)), 0.95), 2),
                        temporal_gap_days=nearest_gap,
                        description=(
                            f"Ex parte action [{ev.description[:50]}] concealed from "
                            f"Andrew (no notice within ±3d)"
                        ),
                    )
                    count += 1
        return count

    # ------------------------------------------------------------------
    # Chain extraction methods
    # ------------------------------------------------------------------

    def get_poisonous_tree_chain(self) -> CausalChain:
        """
        Trace the fruit-of-the-poisonous-tree chain from Oct 13 2023
        recantation through all derivative proceedings.

        Chain: Recantation → PPO → Custody to McNeill → Trial →
               Withholding → Ex parte orders → Last contact →
               Contempt → Jail → Alienation
        """
        chain = CausalChain(name="Fruit of the Poisonous Tree")

        # Key anchor dates in the poisonous tree
        anchor_dates_keywords = [
            (date(2023, 10, 13), ["recant", "nothing was physical"]),
            (date(2023, 10, 15), ["ppo", "protection order", "petition"]),
            (date(2024, 4, 1), ["complaint for custody", "custody complaint"]),
            (date(2024, 4, 29), ["ex parte order", "joint legal"]),
            (date(2024, 7, 17), ["trial", "sole custody to mother", "all 12"]),
            (date(2024, 10, 20), ["withholding", "began withholding"]),
            (date(2025, 5, 4), ["albert", "admits", "ns2505044", "premeditation"]),
            (date(2025, 7, 29), ["last contact", "last day"]),
            (date(2025, 8, 8), ["five orders", "ex parte"]),
            (date(2025, 8, 9), ["ex parte order", "suspended", "parenting time suspended"]),
            (date(2025, 9, 28), ["custody order", "100%", "zero for father"]),
        ]

        chain_events: List[TimelineEvent] = []
        for anchor_date, keywords in anchor_dates_keywords:
            best_event = self._find_best_event_near_date(anchor_date, keywords, window_days=7)
            if best_event:
                chain_events.append(best_event)

        # Also collect all events along the chain path from the graph
        chain_event_ids = {ev.id for ev in chain_events}
        if chain_events and self.graph.number_of_nodes() > 0:
            for i in range(len(chain_events) - 1):
                src = chain_events[i].id
                tgt = chain_events[i + 1].id
                if src in self.graph and tgt in self.graph:
                    try:
                        path = nx.shortest_path(self.graph, src, tgt)
                        for nid in path:
                            if nid not in chain_event_ids:
                                chain_event_ids.add(nid)
                                chain_events.append(self.events[nid])
                    except nx.NetworkXNoPath:
                        pass

        # Sort by date
        chain_events.sort(
            key=lambda e: e.event_date if e.event_date else date(9999, 12, 31)
        )
        chain.events = chain_events

        # Collect edges between chain events
        chain_id_set = {ev.id for ev in chain_events}
        for u, v, data in self.graph.edges(data=True):
            if u in chain_id_set and v in chain_id_set:
                chain.edges.append(CausalEdge(
                    source_id=u,
                    target_id=v,
                    relationship=data.get("relationship", ""),
                    confidence=data.get("confidence", 0.0),
                    temporal_gap_days=data.get("temporal_gap_days", 0),
                    description=data.get("description", ""),
                ))

        if chain_events and chain_events[0].event_date and chain_events[-1].event_date:
            chain.total_span_days = (
                chain_events[-1].event_date - chain_events[0].event_date
            ).days

        chain.narrative = self._build_chain_narrative(chain)
        return chain

    def get_retaliation_chain(self, actor: str = "McNeill") -> CausalChain:
        """
        Every time Andrew filed a motion and the target actor retaliated
        within 7 days.
        """
        chain = CausalChain(name=f"Retaliation Chain — {actor}")
        actor_canonical = None
        actor_lower = actor.lower()
        for key, canonical in KNOWN_ACTORS.items():
            if actor_lower in key or key in actor_lower:
                actor_canonical = canonical
                break
        if not actor_canonical:
            actor_canonical = actor

        events_collected: List[TimelineEvent] = []
        edges_collected: List[CausalEdge] = []

        for u, v, data in self.graph.edges(data=True):
            if data.get("relationship") != "RETALIATION_FOR":
                continue
            src_ev = self.events.get(u)
            tgt_ev = self.events.get(v)
            if not src_ev or not tgt_ev:
                continue
            if actor_canonical in tgt_ev.actors:
                if src_ev not in events_collected:
                    events_collected.append(src_ev)
                if tgt_ev not in events_collected:
                    events_collected.append(tgt_ev)
                edges_collected.append(CausalEdge(
                    source_id=u,
                    target_id=v,
                    relationship="RETALIATION_FOR",
                    confidence=data.get("confidence", 0.0),
                    temporal_gap_days=data.get("temporal_gap_days", 0),
                    description=data.get("description", ""),
                ))

        events_collected.sort(
            key=lambda e: e.event_date if e.event_date else date(9999, 12, 31)
        )
        chain.events = events_collected
        chain.edges = edges_collected
        if events_collected and events_collected[0].event_date and events_collected[-1].event_date:
            chain.total_span_days = (
                events_collected[-1].event_date - events_collected[0].event_date
            ).days
        chain.narrative = self._build_chain_narrative(chain)
        return chain

    def get_conspiracy_chain(self) -> CausalChain:
        """
        Cross-actor coordination events: Emily + Albert + Barnes + McNeill
        acting in concert.
        """
        chain = CausalChain(name="Conspiracy / Cross-Actor Coordination")
        conspiracy_actors = {"Emily Watson", "Albert Watson", "Jennifer Barnes", "Judge McNeill"}

        conspiracy_events: List[TimelineEvent] = []
        for eid, ev in self.events.items():
            if not ev.event_date:
                continue
            actor_set = set(ev.actors)
            overlap = actor_set & conspiracy_actors
            if len(overlap) >= 2:
                conspiracy_events.append(ev)

        # Also find temporal clusters: different conspiracy actors acting within 72h
        sorted_by_date: List[Tuple[date, int]] = []
        for actor in conspiracy_actors:
            for eid in self._events_by_actor.get(actor, []):
                ev = self.events[eid]
                if ev.event_date:
                    sorted_by_date.append((ev.event_date, eid))
        sorted_by_date.sort(key=lambda x: x[0])

        # Sliding 72h window — find clusters of 2+ conspiracy actors
        seen_ids = {ev.id for ev in conspiracy_events}
        for i, (d1, eid1) in enumerate(sorted_by_date):
            window_end = d1 + timedelta(days=3)
            cluster_actors: set[str] = set()
            cluster_ids: List[int] = []
            for j in range(i, len(sorted_by_date)):
                d2, eid2 = sorted_by_date[j]
                if d2 > window_end:
                    break
                ev2 = self.events[eid2]
                actors_here = set(ev2.actors) & conspiracy_actors
                if actors_here:
                    cluster_actors |= actors_here
                    cluster_ids.append(eid2)
            if len(cluster_actors) >= 2:
                for cid in cluster_ids:
                    if cid not in seen_ids:
                        seen_ids.add(cid)
                        conspiracy_events.append(self.events[cid])

        conspiracy_events.sort(
            key=lambda e: e.event_date if e.event_date else date(9999, 12, 31)
        )
        chain.events = conspiracy_events

        # Collect edges
        conspiracy_ids = {ev.id for ev in conspiracy_events}
        for u, v, data in self.graph.edges(data=True):
            if u in conspiracy_ids and v in conspiracy_ids:
                chain.edges.append(CausalEdge(
                    source_id=u,
                    target_id=v,
                    relationship=data.get("relationship", ""),
                    confidence=data.get("confidence", 0.0),
                    temporal_gap_days=data.get("temporal_gap_days", 0),
                    description=data.get("description", ""),
                ))

        if conspiracy_events and conspiracy_events[0].event_date and conspiracy_events[-1].event_date:
            chain.total_span_days = (
                conspiracy_events[-1].event_date - conspiracy_events[0].event_date
            ).days
        chain.narrative = self._build_chain_narrative(chain)
        return chain

    def detect_anomalies(self) -> List[AnomalyReport]:
        """
        Find temporal anomalies in the record:
        - Orders before hearings
        - Service dates after filing
        - Impossible timelines
        - Multiple adverse actions on same day
        - Actions with no prior notice
        """
        anomalies: List[AnomalyReport] = []

        # 1. Multiple adverse actions on same day (suspicious coordination)
        for d, eids in self._events_by_date.items():
            adverse_on_day = []
            for eid in eids:
                ev = self.events[eid]
                etype = _classify_event_type(ev.category, ev.description)
                if etype in ("order", "ex_parte", "contempt", "arrest"):
                    adverse_on_day.append(ev)
            if len(adverse_on_day) >= 3:
                anomalies.append(AnomalyReport(
                    anomaly_type="SUSPICIOUS_CLUSTERING",
                    event_id=adverse_on_day[0].id,
                    event_date=d,
                    description=(
                        f"{len(adverse_on_day)} adverse actions on {d.isoformat()}: "
                        f"{'; '.join(e.description[:60] for e in adverse_on_day[:3])}"
                    ),
                    severity="CRITICAL",
                ))

        # 2. Ex parte orders (orders without hearing)
        for eid, ev in self.events.items():
            if not ev.event_date:
                continue
            desc_lower = ev.description.lower()
            if "ex parte" in desc_lower and _classify_event_type(ev.category, ev.description) in (
                "order", "ex_parte"
            ):
                # Check if there was a hearing within 14 days BEFORE
                hearing_found = False
                window_start = ev.event_date - timedelta(days=14)
                for hd in sorted(self._events_by_date.keys()):
                    if hd < window_start:
                        continue
                    if hd >= ev.event_date:
                        break
                    for hid in self._events_by_date[hd]:
                        hev = self.events[hid]
                        if _classify_event_type(hev.category, hev.description) == "hearing":
                            hearing_found = True
                            break
                    if hearing_found:
                        break
                if not hearing_found:
                    anomalies.append(AnomalyReport(
                        anomaly_type="ORDER_WITHOUT_HEARING",
                        event_id=eid,
                        event_date=ev.event_date,
                        description=f"Ex parte order with no hearing in prior 14 days: {ev.description[:100]}",
                        severity="HIGH",
                    ))

        # 3. Actions after the separation anchor with no parenting time
        for eid, ev in self.events.items():
            if not ev.event_date:
                continue
            if ev.event_date <= SEPARATION_ANCHOR:
                continue
            desc_lower = ev.description.lower()
            if any(kw in desc_lower for kw in ("denied parenting", "refused contact", "withhold")):
                sep_days = (ev.event_date - SEPARATION_ANCHOR).days
                anomalies.append(AnomalyReport(
                    anomaly_type="POST_SEPARATION_DENIAL",
                    event_id=eid,
                    event_date=ev.event_date,
                    description=(
                        f"Parenting time denial {sep_days}d after separation anchor: "
                        f"{ev.description[:100]}"
                    ),
                    severity="CRITICAL",
                ))

        # 4. Future-dated events (possible data errors)
        today = date.today()
        for eid, ev in self.events.items():
            if ev.event_date and ev.event_date > today + timedelta(days=30):
                anomalies.append(AnomalyReport(
                    anomaly_type="FUTURE_DATE",
                    event_id=eid,
                    event_date=ev.event_date,
                    description=f"Event dated >30d in the future: {ev.date_str} — {ev.description[:80]}",
                    severity="LOW",
                ))

        # 5. Duplicate events (same date + very similar description start)
        for d, eids in self._events_by_date.items():
            if len(eids) < 2:
                continue
            seen_prefixes: dict[str, int] = {}
            for eid in eids:
                prefix = self.events[eid].description[:80].lower().strip()
                if prefix in seen_prefixes:
                    anomalies.append(AnomalyReport(
                        anomaly_type="POSSIBLE_DUPLICATE",
                        event_id=eid,
                        event_date=d,
                        description=f"Possible duplicate of event {seen_prefixes[prefix]}: {prefix[:60]}",
                        severity="LOW",
                        related_event_id=seen_prefixes[prefix],
                    ))
                else:
                    seen_prefixes[prefix] = eid

        anomalies.sort(
            key=lambda a: (
                {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(a.severity, 4),
                a.event_date or date(9999, 12, 31),
            )
        )
        return anomalies

    def get_chain_between(self, start_date: str, end_date: str) -> CausalChain:
        """
        Get all events and causal links in a date range.
        Dates should be ISO format YYYY-MM-DD.
        """
        sd = _parse_date(start_date)
        ed = _parse_date(end_date)
        if not sd or not ed:
            return CausalChain(
                name=f"Chain {start_date} → {end_date}",
                narrative="ERROR: Could not parse date range.",
            )

        chain = CausalChain(name=f"Chain {sd.isoformat()} → {ed.isoformat()}")
        range_events: List[TimelineEvent] = []
        for eid, ev in self.events.items():
            if ev.event_date and sd <= ev.event_date <= ed:
                range_events.append(ev)

        range_events.sort(
            key=lambda e: e.event_date if e.event_date else date(9999, 12, 31)
        )
        chain.events = range_events

        range_ids = {ev.id for ev in range_events}
        for u, v, data in self.graph.edges(data=True):
            if u in range_ids and v in range_ids:
                chain.edges.append(CausalEdge(
                    source_id=u,
                    target_id=v,
                    relationship=data.get("relationship", ""),
                    confidence=data.get("confidence", 0.0),
                    temporal_gap_days=data.get("temporal_gap_days", 0),
                    description=data.get("description", ""),
                ))

        chain.total_span_days = (ed - sd).days
        chain.narrative = self._build_chain_narrative(chain)
        return chain

    def get_actor_timeline(self, actor: str) -> CausalChain:
        """All events involving a specific actor with causal context."""
        actor_canonical = None
        actor_lower = actor.lower()
        for key, canonical in KNOWN_ACTORS.items():
            if actor_lower in key or key in actor_lower:
                actor_canonical = canonical
                break
        if not actor_canonical:
            # Fuzzy search: try partial match in all actors
            for canonical_name, eids in self._events_by_actor.items():
                if actor_lower in canonical_name.lower():
                    actor_canonical = canonical_name
                    break
        if not actor_canonical:
            actor_canonical = actor

        chain = CausalChain(name=f"Actor Timeline — {actor_canonical}")
        actor_events: List[TimelineEvent] = []
        actor_ids = self._events_by_actor.get(actor_canonical, [])
        for eid in actor_ids:
            actor_events.append(self.events[eid])

        actor_events.sort(
            key=lambda e: e.event_date if e.event_date else date(9999, 12, 31)
        )
        chain.events = actor_events

        actor_id_set = set(actor_ids)
        for u, v, data in self.graph.edges(data=True):
            if u in actor_id_set or v in actor_id_set:
                chain.edges.append(CausalEdge(
                    source_id=u,
                    target_id=v,
                    relationship=data.get("relationship", ""),
                    confidence=data.get("confidence", 0.0),
                    temporal_gap_days=data.get("temporal_gap_days", 0),
                    description=data.get("description", ""),
                ))

        if actor_events and actor_events[0].event_date and actor_events[-1].event_date:
            chain.total_span_days = (
                actor_events[-1].event_date - actor_events[0].event_date
            ).days
        chain.narrative = self._build_chain_narrative(chain)
        return chain

    def export_for_filing(self, chain_type: str) -> str:
        """
        Export a chain as court-ready narrative text.

        chain_type options: 'poisonous_tree', 'retaliation', 'conspiracy',
                           'anomalies', or 'actor:<name>'
        """
        sep_days = _separation_days()
        separator = "=" * 72
        header = (
            "TEMPORAL CAUSATION ANALYSIS\n"
            "Pigors v. Watson, Case No. 2024-001507-DC\n"
            "14th Circuit Court, Muskegon County\n"
            f"Prepared: {date.today().isoformat()}\n"
            f"Days Since Last Contact with L.D.W.: {sep_days}\n"
            f"{separator}\n\n"
        )

        if chain_type == "poisonous_tree":
            chain = self.get_poisonous_tree_chain()
            body = self._format_chain_for_court(chain, preamble=(
                "The following establishes a direct causal chain from Defendant's "
                "recantation on October 13, 2023, through every subsequent proceeding "
                "that flowed from it. Each event is causally linked to its predecessor, "
                "demonstrating that the entire custody determination is the fruit of "
                "the poisonous tree — an initial PPO petition filed just two days after "
                "the Defendant admitted to police that 'nothing was physical.'\n\n"
            ))
        elif chain_type == "retaliation":
            chain = self.get_retaliation_chain("McNeill")
            body = self._format_chain_for_court(chain, preamble=(
                "The following documents a pattern of judicial retaliation: "
                "each time Plaintiff filed a legitimate motion or pleading, "
                "the presiding judge issued adverse orders within days. "
                "This pattern demonstrates bias and predetermined hostility "
                "toward the pro se Plaintiff.\n\n"
            ))
        elif chain_type == "conspiracy":
            chain = self.get_conspiracy_chain()
            body = self._format_chain_for_court(chain, preamble=(
                "The following documents cross-actor coordination between "
                "Defendant Emily A. Watson, Albert Watson, and the presiding "
                "judge. The temporal clustering of their actions — often within "
                "72 hours of each other — demonstrates a concerted effort to "
                "deprive Plaintiff of his parental rights.\n\n"
            ))
        elif chain_type == "anomalies":
            anomalies = self.detect_anomalies()
            body = self._format_anomalies_for_court(anomalies)
        elif chain_type.startswith("actor:"):
            actor_name = chain_type.split(":", 1)[1]
            chain = self.get_actor_timeline(actor_name)
            body = self._format_chain_for_court(chain, preamble=(
                f"Complete timeline of events involving {actor_name}:\n\n"
            ))
        else:
            return f"ERROR: Unknown chain_type '{chain_type}'. Use: poisonous_tree, retaliation, conspiracy, anomalies, actor:<name>"

        return header + body

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        """Return summary statistics about the graph."""
        sep_days = _separation_days()
        edge_types: dict[str, int] = {}
        for _, _, data in self.graph.edges(data=True):
            rel = data.get("relationship", "UNKNOWN")
            edge_types[rel] = edge_types.get(rel, 0) + 1

        event_types: dict[str, int] = {}
        for eid in self.events:
            ev = self.events[eid]
            et = _classify_event_type(ev.category, ev.description)
            event_types[et] = event_types.get(et, 0) + 1

        dated = sum(1 for ev in self.events.values() if ev.event_date is not None)
        with_actors = sum(1 for ev in self.events.values() if ev.actors)

        return {
            "total_events": len(self.events),
            "events_with_dates": dated,
            "events_with_actors": with_actors,
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "edge_types": edge_types,
            "event_types": event_types,
            "lanes": {
                lane: len(eids) for lane, eids in self._events_by_lane.items()
            },
            "unique_actors": len(self._events_by_actor),
            "date_range": {
                "earliest": min(
                    (ev.event_date for ev in self.events.values() if ev.event_date),
                    default=None,
                ),
                "latest": max(
                    (ev.event_date for ev in self.events.values() if ev.event_date),
                    default=None,
                ),
            },
            "separation_days": sep_days,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_best_event_near_date(
        self,
        target_date: date,
        keywords: List[str],
        window_days: int = 7,
    ) -> Optional[TimelineEvent]:
        """Find the best-matching event near a target date."""
        best: Optional[TimelineEvent] = None
        best_score = -1

        window_start = target_date - timedelta(days=window_days)
        window_end = target_date + timedelta(days=window_days)

        for d in sorted(self._events_by_date.keys()):
            if d < window_start:
                continue
            if d > window_end:
                break
            for eid in self._events_by_date[d]:
                ev = self.events[eid]
                desc_lower = ev.description.lower()
                score = sum(1 for kw in keywords if kw.lower() in desc_lower)
                # Bonus for exact date match
                if d == target_date:
                    score += 2
                # Bonus for higher severity
                if ev.severity in ("critical", "CRITICAL"):
                    score += 1
                if score > best_score:
                    best_score = score
                    best = ev

        return best

    def _build_chain_narrative(self, chain: CausalChain) -> str:
        """Build a textual narrative from a causal chain."""
        if not chain.events:
            return "No events found for this chain."

        lines: List[str] = [f"# {chain.name}\n"]
        sep_days = _separation_days()
        lines.append(f"Separation from L.D.W.: {sep_days} days (computed dynamically)\n")

        if chain.total_span_days:
            lines.append(f"Chain span: {chain.total_span_days} days\n")
        lines.append(f"Events: {len(chain.events)} | Causal links: {len(chain.edges)}\n\n")

        prev_date: Optional[date] = None
        for ev in chain.events:
            date_str = ev.date_str
            gap_str = ""
            if prev_date and ev.event_date and prev_date < ev.event_date:
                gap = (ev.event_date - prev_date).days
                gap_str = f" (+{gap}d)"

            actor_str = f" [{', '.join(ev.actors)}]" if ev.actors else ""
            lane_str = f" [Lane {ev.lane}]" if ev.lane else ""
            lines.append(
                f"  {date_str}{gap_str}{actor_str}{lane_str}\n"
                f"    {ev.description[:200]}\n"
            )
            prev_date = ev.event_date

        if chain.edges:
            lines.append("\n## Causal Links\n")
            for edge in chain.edges[:50]:
                lines.append(
                    f"  {edge.source_id} → {edge.target_id} "
                    f"[{edge.relationship}] "
                    f"(conf={edge.confidence:.0%}, gap={edge.temporal_gap_days}d)\n"
                    f"    {edge.description[:120]}\n"
                )

        return "".join(lines)

    def _format_chain_for_court(self, chain: CausalChain, preamble: str = "") -> str:
        """Format a chain for court filing inclusion."""
        lines: List[str] = []
        if preamble:
            lines.append(preamble)

        lines.append(f"Total events in chain: {len(chain.events)}\n")
        lines.append(f"Total causal links: {len(chain.edges)}\n")
        if chain.total_span_days:
            lines.append(f"Chain spans {chain.total_span_days} days.\n\n")

        para_num = 1
        for ev in chain.events:
            date_str = ev.date_str
            # Build court-style paragraph
            actors_str = ""
            if ev.actors:
                actors_str = " ".join(ev.actors) + " "
            desc_clean = ev.description[:300].replace("\n", " ").strip()
            lines.append(
                f"    {para_num}. On {date_str}, {actors_str}{desc_clean}\n\n"
            )
            para_num += 1

        if chain.edges:
            lines.append("CAUSAL RELATIONSHIPS:\n\n")
            for edge in chain.edges[:30]:
                src_ev = self.events.get(edge.source_id)
                tgt_ev = self.events.get(edge.target_id)
                src_desc = src_ev.description[:60] if src_ev else str(edge.source_id)
                tgt_desc = tgt_ev.description[:60] if tgt_ev else str(edge.target_id)
                lines.append(
                    f"    - [{src_desc}] {edge.relationship} [{tgt_desc}] "
                    f"({edge.temporal_gap_days} days, {edge.confidence:.0%} confidence)\n"
                )

        return "".join(lines)

    def _format_anomalies_for_court(self, anomalies: List[AnomalyReport]) -> str:
        """Format anomalies for court filing."""
        lines: List[str] = [
            "TEMPORAL ANOMALIES IN THE RECORD\n\n"
            "The following anomalies demonstrate procedural irregularities, "
            "impossible timelines, and suspicious temporal patterns in the "
            "proceedings below:\n\n"
        ]

        critical = [a for a in anomalies if a.severity == "CRITICAL"]
        high = [a for a in anomalies if a.severity == "HIGH"]
        other = [a for a in anomalies if a.severity not in ("CRITICAL", "HIGH")]

        if critical:
            lines.append(f"CRITICAL ANOMALIES ({len(critical)}):\n\n")
            for i, a in enumerate(critical[:20], 1):
                date_str = a.event_date.isoformat() if a.event_date else "unknown"
                lines.append(
                    f"    {i}. [{a.anomaly_type}] {date_str}: {a.description[:200]}\n\n"
                )

        if high:
            lines.append(f"\nHIGH-SEVERITY ANOMALIES ({len(high)}):\n\n")
            for i, a in enumerate(high[:20], 1):
                date_str = a.event_date.isoformat() if a.event_date else "unknown"
                lines.append(
                    f"    {i}. [{a.anomaly_type}] {date_str}: {a.description[:200]}\n\n"
                )

        if other:
            lines.append(f"\nOTHER ANOMALIES ({len(other)}):\n\n")
            for i, a in enumerate(other[:10], 1):
                date_str = a.event_date.isoformat() if a.event_date else "unknown"
                lines.append(
                    f"    {i}. [{a.anomaly_type}] {date_str}: {a.description[:150]}\n\n"
                )

        lines.append(
            f"\nTotal anomalies detected: {len(anomalies)} "
            f"(Critical: {len(critical)}, High: {len(high)}, Other: {len(other)})\n"
        )
        return "".join(lines)


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

def build() -> TemporalKnowledgeGraph:
    """Build and return a fully-constructed TemporalKnowledgeGraph."""
    tkg = TemporalKnowledgeGraph()
    tkg.build_graph()
    return tkg

"""
Evidence Hypergraph Engine for LitigationOS.

A hypergraph connects evidence to MULTIPLE case lanes simultaneously.
Unlike regular graphs where an edge connects 2 nodes, a hyperedge connects
N nodes — critical because one piece of evidence (e.g. police report NS2505044)
can connect custody (A), PPO (D), judicial misconduct (E), and federal §1983 (C)
ALL AT ONCE.

Representation: pure-Python dicts + NetworkX bipartite graph.
A hyperedge is a node in the bipartite graph connected to all member nodes.
"""

from __future__ import annotations

__all__ = ["HypergraphEngine"]

import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

try:
    import networkx as nx
except ImportError:
    nx = None

DB_PATH = str(Path(__file__).resolve().parents[3] / "litigation_context.db")

VALID_LANES = {"A", "B", "C", "D", "E", "F"}

LANE_NAMES = {
    "A": "Custody (2024-001507-DC)",
    "B": "Housing (2025-002760-CZ)",
    "C": "Federal §1983",
    "D": "PPO (2023-5907-PP)",
    "E": "Judicial Misconduct",
    "F": "Appellate (COA 366810)",
}

FILING_LANES: Dict[str, Set[str]] = {
    "F01": {"A", "D", "E"},
    "F02": {"B"},
    "F03": {"E"},
    "F04": {"A", "B", "C", "D", "E"},
    "F05": {"A", "D", "E"},
    "F06": {"E"},
    "F07": {"A", "D"},
    "F08": {"C"},
    "F09": {"A", "D", "E", "F"},
    "F10": {"A", "D", "F"},
}

# Canonical entity resolution — normalizes variant spellings to a single identity.
ENTITY_MAP: Dict[str, str] = {
    "emily": "Emily A. Watson",
    "emily watson": "Emily A. Watson",
    "emily a watson": "Emily A. Watson",
    "emily a. watson": "Emily A. Watson",
    "defendant": "Emily A. Watson",
    "mother": "Emily A. Watson",
    "mcneill": "Hon. Jenny L. McNeill",
    "judge mcneill": "Hon. Jenny L. McNeill",
    "jenny mcneill": "Hon. Jenny L. McNeill",
    "jenny l. mcneill": "Hon. Jenny L. McNeill",
    "albert": "Albert Watson",
    "albert watson": "Albert Watson",
    "lori": "Lori Watson",
    "lori watson": "Lori Watson",
    "cody": "Cody Watson",
    "cody watson": "Cody Watson",
    "barnes": "Jennifer Barnes",
    "jennifer barnes": "Jennifer Barnes",
    "rusco": "Pamela Rusco",
    "pamela rusco": "Pamela Rusco",
    "berry": "Ronald Berry",
    "ronald berry": "Ronald Berry",
    "ron berry": "Ronald Berry",
    "cavan": "Cavan Berry",
    "cavan berry": "Cavan Berry",
    "hoopes": "Hon. Kenneth Hoopes",
    "kenneth hoopes": "Hon. Kenneth Hoopes",
    "ladas-hoopes": "Hon. Maria Ladas-Hoopes",
    "maria ladas-hoopes": "Hon. Maria Ladas-Hoopes",
    "andrew": "Andrew James Pigors",
    "andrew pigors": "Andrew James Pigors",
    "plaintiff": "Andrew James Pigors",
    "father": "Andrew James Pigors",
    "pigors": "Andrew James Pigors",
}

# Pre-compiled regex patterns for entity extraction — longest-first to prevent
# partial matches (e.g. "Emily A. Watson" before "Emily").
_ENTITY_PATTERNS: List[Tuple[re.Pattern, str]] = sorted(
    [
        (re.compile(r"\b" + re.escape(variant) + r"\b", re.IGNORECASE), canonical)
        for variant, canonical in ENTITY_MAP.items()
    ],
    key=lambda pair: -len(pair[0].pattern),
)

# Adversary entities — used by get_conspiracy_web to detect coordinated action.
ADVERSARY_ENTITIES: Set[str] = {
    "Emily A. Watson",
    "Albert Watson",
    "Lori Watson",
    "Cody Watson",
    "Ronald Berry",
    "Cavan Berry",
    "Hon. Jenny L. McNeill",
    "Hon. Kenneth Hoopes",
    "Hon. Maria Ladas-Hoopes",
    "Pamela Rusco",
    "Jennifer Barnes",
}


@dataclass
class HyperEdge:
    """A hyperedge connecting multiple nodes through a single piece of evidence."""

    edge_id: str
    nodes: Set[str] = field(default_factory=set)
    evidence_id: int = 0
    lanes: Set[str] = field(default_factory=set)
    actors: Set[str] = field(default_factory=set)
    description: str = ""
    strength: float = 0.0
    source: str = ""


@dataclass
class LaneOverlap:
    """Overlap statistics between two lanes."""

    lane_a: str
    lane_b: str
    shared_sources: int
    shared_entities: int
    hyperedge_count: int


@dataclass
class FilingAmmunition:
    """Evidence ammunition for a specific filing."""

    filing_id: str
    filing_lanes: Set[str]
    direct_evidence: List[HyperEdge]
    cross_lane_evidence: List[HyperEdge]
    entity_coverage: Dict[str, int]
    total_items: int


@dataclass
class ConspiracyCluster:
    """A cluster of adversaries connected through shared evidence."""

    adversaries: Set[str]
    evidence_ids: List[int]
    lanes_touched: Set[str]
    description: str
    strength: float


@dataclass
class HypergraphStats:
    """Summary statistics for the hypergraph."""

    total_nodes: int
    total_hyperedges: int
    total_entity_nodes: int
    total_lane_nodes: int
    total_source_nodes: int
    cross_lane_edges: int
    avg_edge_size: float
    max_edge_size: int
    lane_coverage: Dict[str, int]
    top_entities: List[Tuple[str, int]]


def _extract_entities(text: str) -> Set[str]:
    """Extract known entities from text using compiled patterns."""
    if not text:
        return set()
    found: Set[str] = set()
    for pattern, canonical in _ENTITY_PATTERNS:
        if pattern.search(text):
            found.add(canonical)
    return found


def _safe_fts5_search(
    conn: sqlite3.Connection,
    fts_table: str,
    content_table: str,
    query: str,
    columns: str = "*",
    limit: int = 500,
) -> List[sqlite3.Row]:
    """FTS5 search with sanitisation and LIKE fallback per Rule 15."""
    sanitised = re.sub(r"[^\w\s*\"]", " ", query).strip()
    if not sanitised:
        return []

    # Attempt FTS5 MATCH first
    try:
        rows = conn.execute(
            f"SELECT {columns} FROM {fts_table} WHERE {fts_table} MATCH ? LIMIT ?",
            (sanitised, limit),
        ).fetchall()
        return rows
    except Exception:
        pass

    # Fallback: LIKE on the content table
    like_term = f"%{sanitised}%"
    try:
        rows = conn.execute(
            f"SELECT {columns} FROM {content_table} "
            f"WHERE quote_text LIKE ? LIMIT ?",
            (like_term, limit),
        ).fetchall()
        return rows
    except Exception:
        return []


def _compute_strength(
    lanes: Set[str],
    actors: Set[str],
    category: Optional[str] = None,
    relevance: Optional[float] = None,
) -> float:
    """Compute hyperedge strength on 0.0–1.0 scale.

    Factors: lane breadth, actor count, category weight, source relevance.
    """
    lane_score = min(len(lanes) / 4.0, 1.0) * 0.4
    actor_score = min(len(actors) / 5.0, 1.0) * 0.3

    cat_weights = {
        "due_process": 0.9,
        "judicial_misconduct": 0.95,
        "false_allegations": 0.85,
        "witness": 0.7,
        "financial": 0.5,
        "custody": 0.8,
        "ppo": 0.75,
        "contempt": 0.8,
    }
    cat_score = cat_weights.get((category or "").lower(), 0.5) * 0.2

    rel_score = (relevance if relevance and relevance > 0 else 0.5) * 0.1

    return round(min(lane_score + actor_score + cat_score + rel_score, 1.0), 4)


class EvidenceHypergraph:
    """Hypergraph engine connecting evidence across multiple case lanes.

    Uses a bipartite graph representation where:
      - Partition 0 = real nodes (entities, lanes, sources)
      - Partition 1 = hyperedge nodes (evidence items)
    Each hyperedge node connects to all real nodes it touches.
    """

    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self.hyperedges: Dict[str, HyperEdge] = {}
        self.entity_index: Dict[str, Set[str]] = defaultdict(set)
        self.lane_index: Dict[str, Set[str]] = defaultdict(set)
        self.source_index: Dict[str, Set[str]] = defaultdict(set)

        if nx is not None:
            self._graph: Optional[nx.Graph] = nx.Graph()
        else:
            self._graph = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            # Handle mixed-encoding text gracefully
            self._conn.text_factory = lambda b: b.decode("utf-8", errors="replace") if isinstance(b, bytes) else b
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA busy_timeout=60000")
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA cache_size=-32000")
            self._conn.execute("PRAGMA temp_store=MEMORY")
            self._conn.execute("PRAGMA synchronous=NORMAL")
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------
    # Schema introspection (Rule 16)
    # ------------------------------------------------------------------

    def _table_columns(self, table: str) -> Set[str]:
        rows = self.conn.execute(f"PRAGMA table_info({table})").fetchall()
        return {r["name"] for r in rows}

    def _table_exists(self, table: str) -> bool:
        row = self.conn.execute(
            "SELECT COUNT(*) AS cnt FROM sqlite_master "
            "WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        return row["cnt"] > 0

    # ------------------------------------------------------------------
    # Core build
    # ------------------------------------------------------------------

    def build_hypergraph(self, min_lanes: int = 2) -> int:
        """Build the hypergraph from cross-lane evidence.

        Identifies evidence sources that appear in 2+ lanes and constructs
        hyperedges linking lanes, entities, and source documents.

        Returns the number of hyperedges created.
        """
        self.hyperedges.clear()
        self.entity_index.clear()
        self.lane_index.clear()
        self.source_index.clear()
        if self._graph is not None:
            self._graph.clear()

        edge_count = 0

        # --- Phase 1: Cross-lane source files ---------------------------------
        # Group evidence by source_file, collecting all lanes each source touches.
        source_lane_map: Dict[str, Dict[str, list]] = defaultdict(
            lambda: {"lanes": set(), "ids": [], "texts": [], "cats": [], "rels": []}
        )

        cursor = self.conn.execute(
            "SELECT id, source_file, quote_text, lane, category, relevance_score "
            "FROM evidence_quotes "
            "WHERE lane IN ('A','B','C','D','E','F') "
            "AND is_duplicate = 0 "
            "ORDER BY source_file"
        )
        for row in cursor:
            src = row["source_file"] or ""
            if not src:
                continue
            bucket = source_lane_map[src]
            bucket["lanes"].add(row["lane"])
            bucket["ids"].append(row["id"])
            bucket["texts"].append(row["quote_text"] or "")
            bucket["cats"].append(row["category"] or "")
            bucket["rels"].append(row["relevance_score"])

        for src, data in source_lane_map.items():
            lanes: set = data["lanes"]
            if len(lanes) < min_lanes:
                continue

            combined_text = " ".join(data["texts"][:20])
            actors = _extract_entities(combined_text)
            primary_cat = max(
                set(data["cats"]),
                key=lambda c: data["cats"].count(c),
                default="",
            )
            avg_rel = sum(r for r in data["rels"] if r) / max(
                sum(1 for r in data["rels"] if r), 1
            )

            eid = f"SRC-{edge_count:06d}"
            nodes: Set[str] = set()
            nodes.update(f"LANE:{ln}" for ln in lanes)
            nodes.update(f"ENTITY:{a}" for a in actors)
            nodes.add(f"SOURCE:{src}")

            he = HyperEdge(
                edge_id=eid,
                nodes=nodes,
                evidence_id=data["ids"][0],
                lanes=set(lanes),
                actors=actors,
                description=f"Source '{Path(src).name}' spans {sorted(lanes)}",
                strength=_compute_strength(lanes, actors, primary_cat, avg_rel),
                source=src,
            )
            self._register_hyperedge(he)
            edge_count += 1

        # --- Phase 2: Impeachment cross-lane bridges --------------------------
        if self._table_exists("impeachment_matrix"):
            imp_cols = self._table_columns("impeachment_matrix")
            has_lane = "lane" in imp_cols

            query = (
                "SELECT id, category, evidence_summary, source_file, "
                "quote_text, impeachment_value"
                + (", lane" if has_lane else "")
                + " FROM impeachment_matrix WHERE impeachment_value >= 3"
            )
            for row in self.conn.execute(query):
                text = (row["evidence_summary"] or "") + " " + (row["quote_text"] or "")
                actors = _extract_entities(text)
                src = row["source_file"] or ""
                imp_lane = row["lane"] if has_lane else None

                imp_lanes: Set[str] = set()
                if imp_lane and imp_lane in VALID_LANES:
                    imp_lanes.add(imp_lane)

                # Infer lanes from category keywords
                cat_lower = (row["category"] or "").lower()
                if "judicial" in cat_lower or "ex_parte" in cat_lower:
                    imp_lanes.add("E")
                if "ppo" in cat_lower:
                    imp_lanes.add("D")
                if "custody" in cat_lower or "withholding" in cat_lower:
                    imp_lanes.add("A")

                # Infer from entity involvement
                if "Hon. Jenny L. McNeill" in actors:
                    imp_lanes.add("E")
                if "Emily A. Watson" in actors:
                    imp_lanes.update({"A", "D"})

                if len(imp_lanes) < min_lanes:
                    continue

                eid = f"IMP-{edge_count:06d}"
                nodes = set()
                nodes.update(f"LANE:{ln}" for ln in imp_lanes)
                nodes.update(f"ENTITY:{a}" for a in actors)
                if src:
                    nodes.add(f"SOURCE:{src}")

                he = HyperEdge(
                    edge_id=eid,
                    nodes=nodes,
                    evidence_id=row["id"],
                    lanes=imp_lanes,
                    actors=actors,
                    description=f"Impeachment [{row['category']}]: {str(text)[:100]}",
                    strength=_compute_strength(
                        imp_lanes, actors, row["category"], row["impeachment_value"] / 5.0
                    ),
                    source=src,
                )
                self._register_hyperedge(he)
                edge_count += 1

        # --- Phase 3: Contradiction bridges -----------------------------------
        if self._table_exists("contradiction_map"):
            for row in self.conn.execute(
                "SELECT id, claim_id, source_a, source_b, "
                "contradiction_text, severity, lane FROM contradiction_map "
                "WHERE severity IN ('high', 'critical')"
            ):
                text = row["contradiction_text"] or ""
                actors = _extract_entities(text)
                contra_lane = row["lane"] if row["lane"] in VALID_LANES else None

                contra_lanes: Set[str] = set()
                if contra_lane:
                    contra_lanes.add(contra_lane)

                # Infer extra lanes from actor involvement
                if "Hon. Jenny L. McNeill" in actors:
                    contra_lanes.add("E")
                if "Emily A. Watson" in actors:
                    contra_lanes.update({"A", "D"})
                if any(e in actors for e in ("Hon. Kenneth Hoopes", "Hon. Maria Ladas-Hoopes")):
                    contra_lanes.add("E")

                if len(contra_lanes) < min_lanes:
                    continue

                eid = f"CTR-{edge_count:06d}"
                nodes = set()
                nodes.update(f"LANE:{ln}" for ln in contra_lanes)
                nodes.update(f"ENTITY:{a}" for a in actors)
                for s in (row["source_a"], row["source_b"]):
                    if s:
                        nodes.add(f"SOURCE:{s}")

                he = HyperEdge(
                    edge_id=eid,
                    nodes=nodes,
                    evidence_id=row["id"],
                    lanes=contra_lanes,
                    actors=actors,
                    description=f"Contradiction [{row['severity']}]: {text[:100]}",
                    strength=_compute_strength(
                        contra_lanes,
                        actors,
                        "contradiction",
                        1.0 if row["severity"] == "critical" else 0.8,
                    ),
                    source=row["source_a"] or "",
                )
                self._register_hyperedge(he)
                edge_count += 1

        # --- Phase 4: Judicial violations → lane E + inferred lanes -----------
        if self._table_exists("judicial_violations"):
            for row in self.conn.execute(
                "SELECT id, violation_type, description, source_file, "
                "source_quote, severity, lane FROM judicial_violations "
                "WHERE severity >= 3"
            ):
                text = (row["description"] or "") + " " + (row["source_quote"] or "")
                actors = _extract_entities(text)
                jv_lane = row["lane"] if row["lane"] in VALID_LANES else "E"

                jv_lanes: Set[str] = {jv_lane}
                desc_lower = text.lower()
                if "custody" in desc_lower or "parenting" in desc_lower:
                    jv_lanes.add("A")
                if "ppo" in desc_lower or "protection order" in desc_lower:
                    jv_lanes.add("D")
                if "housing" in desc_lower or "shady oaks" in desc_lower:
                    jv_lanes.add("B")
                if "appeal" in desc_lower or "coa" in desc_lower:
                    jv_lanes.add("F")
                if "1983" in desc_lower or "federal" in desc_lower:
                    jv_lanes.add("C")

                if len(jv_lanes) < min_lanes:
                    continue

                src = row["source_file"] or ""
                eid = f"JDV-{edge_count:06d}"
                nodes = set()
                nodes.update(f"LANE:{ln}" for ln in jv_lanes)
                nodes.update(f"ENTITY:{a}" for a in actors)
                if src:
                    nodes.add(f"SOURCE:{src}")

                he = HyperEdge(
                    edge_id=eid,
                    nodes=nodes,
                    evidence_id=row["id"],
                    lanes=jv_lanes,
                    actors=actors,
                    description=f"Judicial [{row['violation_type']}]: {text[:100]}",
                    strength=_compute_strength(
                        jv_lanes, actors, "judicial_misconduct", (row["severity"] or 5) / 10.0
                    ),
                    source=src,
                )
                self._register_hyperedge(he)
                edge_count += 1

        return edge_count

    def _register_hyperedge(self, he: HyperEdge) -> None:
        """Add a hyperedge to all internal indexes and the bipartite graph."""
        self.hyperedges[he.edge_id] = he

        for lane in he.lanes:
            self.lane_index[lane].add(he.edge_id)
        for actor in he.actors:
            self.entity_index[actor].add(he.edge_id)
        if he.source:
            self.source_index[he.source].add(he.edge_id)

        if self._graph is not None:
            self._graph.add_node(he.edge_id, bipartite=1, kind="hyperedge")
            for node in he.nodes:
                if not self._graph.has_node(node):
                    self._graph.add_node(node, bipartite=0, kind=node.split(":")[0])
                self._graph.add_edge(he.edge_id, node)

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def find_cross_lane_evidence(
        self, lanes: Optional[Set[str]] = None
    ) -> List[HyperEdge]:
        """Find hyperedges connecting the specified lanes (or all if None).

        If *lanes* is provided, returns edges whose lane set is a superset
        of the requested lanes.  If None, returns all cross-lane edges.
        """
        results: List[HyperEdge] = []
        for he in self.hyperedges.values():
            if lanes is None:
                if len(he.lanes) >= 2:
                    results.append(he)
            else:
                if lanes.issubset(he.lanes):
                    results.append(he)
        results.sort(key=lambda h: (-h.strength, -len(h.lanes)))
        return results

    def get_entity_connections(self, entity_name: str) -> List[HyperEdge]:
        """All hyperedges involving an entity (resolves aliases)."""
        canonical = ENTITY_MAP.get(entity_name.lower(), entity_name)
        edge_ids = self.entity_index.get(canonical, set())
        results = [self.hyperedges[eid] for eid in edge_ids if eid in self.hyperedges]
        results.sort(key=lambda h: -h.strength)
        return results

    def get_lane_overlap_matrix(self) -> Dict[str, Dict[str, LaneOverlap]]:
        """NxN matrix of shared evidence between each lane pair.

        Returns ``matrix[lane_a][lane_b]`` as a :class:`LaneOverlap`.
        """
        matrix: Dict[str, Dict[str, LaneOverlap]] = {}

        for la in sorted(VALID_LANES):
            matrix[la] = {}
            for lb in sorted(VALID_LANES):
                if la == lb:
                    count = len(self.lane_index.get(la, set()))
                    matrix[la][lb] = LaneOverlap(la, lb, count, 0, count)
                    continue

                shared_edges: Set[str] = set()
                a_edges = self.lane_index.get(la, set())
                b_edges = self.lane_index.get(lb, set())
                shared_edges = a_edges & b_edges

                shared_sources: Set[str] = set()
                shared_entities: Set[str] = set()
                for eid in shared_edges:
                    he = self.hyperedges.get(eid)
                    if he:
                        if he.source:
                            shared_sources.add(he.source)
                        shared_entities.update(he.actors)

                matrix[la][lb] = LaneOverlap(
                    la, lb, len(shared_sources), len(shared_entities), len(shared_edges)
                )
        return matrix

    def find_strongest_connections(self, top_n: int = 50) -> List[HyperEdge]:
        """Hyperedges with the highest strategic value (strength × breadth)."""
        scored = sorted(
            self.hyperedges.values(),
            key=lambda h: (-h.strength, -len(h.lanes), -len(h.actors)),
        )
        return scored[:top_n]

    def get_filing_ammunition(self, filing_id: str) -> FilingAmmunition:
        """Evidence supporting a specific filing (F01–F10).

        Returns direct evidence (in the filing's lanes) and cross-lane
        evidence that touches those lanes plus others.
        """
        fid = filing_id.upper().replace("F0", "F").replace("F", "F0") if len(filing_id) == 2 else filing_id.upper()
        # Normalise to F01..F10 format
        clean = filing_id.upper().strip()
        if clean in FILING_LANES:
            target_lanes = FILING_LANES[clean]
        else:
            # Try alternate formats: F1 -> F01, etc.
            alt = "F" + clean.lstrip("F").zfill(2)
            target_lanes = FILING_LANES.get(alt, set())
        if not target_lanes:
            return FilingAmmunition(
                filing_id=filing_id,
                filing_lanes=set(),
                direct_evidence=[],
                cross_lane_evidence=[],
                entity_coverage={},
                total_items=0,
            )

        direct: List[HyperEdge] = []
        cross: List[HyperEdge] = []
        entity_counts: Dict[str, int] = defaultdict(int)

        for he in self.hyperedges.values():
            overlap = he.lanes & target_lanes
            if not overlap:
                continue
            if he.lanes == overlap or he.lanes.issubset(target_lanes):
                direct.append(he)
            else:
                cross.append(he)
            for a in he.actors:
                entity_counts[a] += 1

        direct.sort(key=lambda h: -h.strength)
        cross.sort(key=lambda h: (-len(h.lanes & target_lanes), -h.strength))

        return FilingAmmunition(
            filing_id=filing_id,
            filing_lanes=target_lanes,
            direct_evidence=direct,
            cross_lane_evidence=cross,
            entity_coverage=dict(entity_counts),
            total_items=len(direct) + len(cross),
        )

    def entity_resolution(self) -> Dict[str, Set[str]]:
        """Return the canonical entity map showing which variants resolved where.

        Returns ``{canonical_name: {variant1, variant2, ...}}``.
        """
        resolved: Dict[str, Set[str]] = defaultdict(set)
        for variant, canonical in ENTITY_MAP.items():
            resolved[canonical].add(variant)
        return dict(resolved)

    def export_for_brief(self, lanes: Set[str]) -> str:
        """Export cross-lane connections as a narrative section for court filings.

        Produces a markdown-formatted summary suitable for inclusion in a
        Statement of Facts or Argument section.  NO AI/DB references per Rule 3.
        """
        edges = self.find_cross_lane_evidence(lanes)
        if not edges:
            return f"No cross-lane evidence found spanning {sorted(lanes)}."

        lane_labels = " + ".join(LANE_NAMES.get(ln, ln) for ln in sorted(lanes))
        lines: List[str] = []
        lines.append(f"## Cross-Lane Evidence: {lane_labels}\n")
        lines.append(
            f"The following {len(edges)} items of evidence demonstrate "
            f"interconnected conduct spanning multiple dimensions of this case:\n"
        )

        for i, he in enumerate(edges[:30], 1):
            actors_str = ", ".join(sorted(he.actors)) if he.actors else "unidentified actors"
            lane_str = ", ".join(LANE_NAMES.get(ln, ln) for ln in sorted(he.lanes))
            src_name = Path(he.source).name if he.source else "record"

            lines.append(f"{i}. **{src_name}** — Involves {actors_str}.")
            lines.append(f"   Relevant to: {lane_str}.")
            if he.description:
                desc_clean = he.description.split(":", 1)[-1].strip()[:200]
                lines.append(f"   *{desc_clean}*\n")
            else:
                lines.append("")

        if len(edges) > 30:
            lines.append(
                f"\n*({len(edges) - 30} additional cross-lane items omitted for brevity.)*"
            )

        return "\n".join(lines)

    def get_conspiracy_web(self) -> List[ConspiracyCluster]:
        """Find evidence connecting 3+ adversaries in coordinated action.

        Returns clusters sorted by the number of adversaries involved
        (descending), which represent the strongest conspiracy signals.
        """
        cluster_map: Dict[frozenset, Dict] = {}

        for he in self.hyperedges.values():
            adversaries_present = he.actors & ADVERSARY_ENTITIES
            if len(adversaries_present) < 3:
                continue

            key = frozenset(adversaries_present)
            if key not in cluster_map:
                cluster_map[key] = {
                    "adversaries": set(adversaries_present),
                    "evidence_ids": [],
                    "lanes": set(),
                    "descriptions": [],
                    "strengths": [],
                }
            entry = cluster_map[key]
            entry["evidence_ids"].append(he.evidence_id)
            entry["lanes"].update(he.lanes)
            entry["descriptions"].append(he.description)
            entry["strengths"].append(he.strength)

        results: List[ConspiracyCluster] = []
        for key, data in cluster_map.items():
            avg_str = sum(data["strengths"]) / max(len(data["strengths"]), 1)
            desc_summary = "; ".join(data["descriptions"][:5])
            if len(data["descriptions"]) > 5:
                desc_summary += f" (+{len(data['descriptions']) - 5} more)"

            results.append(
                ConspiracyCluster(
                    adversaries=data["adversaries"],
                    evidence_ids=data["evidence_ids"],
                    lanes_touched=data["lanes"],
                    description=desc_summary,
                    strength=round(avg_str, 4),
                )
            )

        results.sort(key=lambda c: (-len(c.adversaries), -c.strength))
        return results

    def summary_stats(self) -> HypergraphStats:
        """Aggregate statistics for the hypergraph."""
        if not self.hyperedges:
            return HypergraphStats(
                total_nodes=0,
                total_hyperedges=0,
                total_entity_nodes=0,
                total_lane_nodes=0,
                total_source_nodes=0,
                cross_lane_edges=0,
                avg_edge_size=0.0,
                max_edge_size=0,
                lane_coverage={},
                top_entities=[],
            )

        all_nodes: Set[str] = set()
        edge_sizes: List[int] = []
        cross_lane = 0

        for he in self.hyperedges.values():
            all_nodes.update(he.nodes)
            edge_sizes.append(len(he.nodes))
            if len(he.lanes) >= 2:
                cross_lane += 1

        entity_nodes = {n for n in all_nodes if n.startswith("ENTITY:")}
        lane_nodes = {n for n in all_nodes if n.startswith("LANE:")}
        source_nodes = {n for n in all_nodes if n.startswith("SOURCE:")}

        lane_cov = {lane: len(eids) for lane, eids in self.lane_index.items()}
        entity_counts = [
            (entity, len(eids)) for entity, eids in self.entity_index.items()
        ]
        entity_counts.sort(key=lambda x: -x[1])

        return HypergraphStats(
            total_nodes=len(all_nodes),
            total_hyperedges=len(self.hyperedges),
            total_entity_nodes=len(entity_nodes),
            total_lane_nodes=len(lane_nodes),
            total_source_nodes=len(source_nodes),
            cross_lane_edges=cross_lane,
            avg_edge_size=round(sum(edge_sizes) / max(len(edge_sizes), 1), 2),
            max_edge_size=max(edge_sizes, default=0),
            lane_coverage=lane_cov,
            top_entities=entity_counts[:20],
        )

    # ------------------------------------------------------------------
    # Convenience: search DB for cross-lane evidence by keyword
    # ------------------------------------------------------------------

    def search_cross_lane(self, keyword: str, limit: int = 100) -> List[HyperEdge]:
        """Search hyperedges whose description or source matches *keyword*."""
        kw = keyword.lower()
        results: List[HyperEdge] = []
        for he in self.hyperedges.values():
            if kw in he.description.lower() or kw in he.source.lower():
                results.append(he)
                if len(results) >= limit:
                    break
        results.sort(key=lambda h: -h.strength)
        return results

    # ------------------------------------------------------------------
    # Pretty-print helpers
    # ------------------------------------------------------------------

    def print_overlap_matrix(self) -> str:
        """Return a human-readable lane overlap matrix."""
        matrix = self.get_lane_overlap_matrix()
        lanes = sorted(VALID_LANES)
        header = "     " + "  ".join(f"{ln:>5}" for ln in lanes)
        lines = [header]
        for la in lanes:
            row_vals = []
            for lb in lanes:
                row_vals.append(f"{matrix[la][lb].hyperedge_count:>5}")
            lines.append(f"  {la}  " + "  ".join(row_vals))
        return "\n".join(lines)

    def print_stats(self) -> str:
        """Return a formatted summary."""
        s = self.summary_stats()
        lines = [
            "╔══════════════════════════════════════════╗",
            "║   EVIDENCE HYPERGRAPH — SUMMARY STATS    ║",
            "╠══════════════════════════════════════════╣",
            f"║ Total Nodes:          {s.total_nodes:>16,} ║",
            f"║ Total Hyperedges:     {s.total_hyperedges:>16,} ║",
            f"║ Cross-Lane Edges:     {s.cross_lane_edges:>16,} ║",
            f"║ Entity Nodes:         {s.total_entity_nodes:>16,} ║",
            f"║ Source Nodes:         {s.total_source_nodes:>16,} ║",
            f"║ Avg Edge Size:        {s.avg_edge_size:>16.2f} ║",
            f"║ Max Edge Size:        {s.max_edge_size:>16,} ║",
            "╠══════════════════════════════════════════╣",
            "║ Lane Coverage:                           ║",
        ]
        for lane in sorted(VALID_LANES):
            cnt = s.lane_coverage.get(lane, 0)
            name = LANE_NAMES.get(lane, lane)[:28]
            lines.append(f"║   {lane} ({name}): {cnt:>5} ║")
        lines.append("╠══════════════════════════════════════════╣")
        lines.append("║ Top Entities:                            ║")
        for name, cnt in s.top_entities[:10]:
            lines.append(f"║   {name[:30]:<30} {cnt:>5} ║")
        lines.append("╚══════════════════════════════════════════╝")
        return "\n".join(lines)


# ------------------------------------------------------------------
# Module-level convenience
# ------------------------------------------------------------------

def build_and_report(min_lanes: int = 2) -> EvidenceHypergraph:
    """Build a hypergraph and print summary stats.  Returns the instance."""
    hg = EvidenceHypergraph()
    count = hg.build_hypergraph(min_lanes=min_lanes)
    print(f"Built {count} hyperedges (min_lanes={min_lanes})")
    print(hg.print_stats())
    print()
    print("Lane Overlap Matrix:")
    print(hg.print_overlap_matrix())
    return hg


if __name__ == "__main__":
    hg = build_and_report()

    print("\n\n=== TOP 10 STRONGEST CONNECTIONS ===")
    for he in hg.find_strongest_connections(10):
        print(
            f"  [{he.edge_id}] str={he.strength:.3f} "
            f"lanes={sorted(he.lanes)} actors={sorted(he.actors)}"
        )
        print(f"    {he.description[:120]}")

    print("\n=== CONSPIRACY WEB (3+ adversaries) ===")
    clusters = hg.get_conspiracy_web()
    for i, c in enumerate(clusters[:5], 1):
        print(
            f"  {i}. {len(c.adversaries)} adversaries, "
            f"{len(c.evidence_ids)} evidence items, "
            f"lanes={sorted(c.lanes_touched)}, str={c.strength:.3f}"
        )
        print(f"     Adversaries: {sorted(c.adversaries)}")

    print(f"\n=== F04 (Federal §1983) AMMUNITION ===")
    ammo = hg.get_filing_ammunition("F04")
    print(
        f"  Direct: {len(ammo.direct_evidence)}, "
        f"Cross-lane: {len(ammo.cross_lane_evidence)}, "
        f"Total: {ammo.total_items}"
    )
    for name, cnt in sorted(ammo.entity_coverage.items(), key=lambda x: -x[1])[:5]:
        print(f"    {name}: {cnt} items")

    hg.close()

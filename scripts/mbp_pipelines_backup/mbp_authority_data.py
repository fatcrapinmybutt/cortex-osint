#!/usr/bin/env python3
"""
MBP Authority Chain Binding Layer — Data Pipeline
Extracts authority_chains_v2 citation hierarchy (primary→supporting).
Outputs D3.js-compatible tree nodes and relationship edges.
"""
import json
import os
import sqlite3
import re
from collections import defaultdict
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "LitigationOS", "litigation_context.db")
if not os.path.exists(DB_PATH):
    DB_PATH = os.path.join("C:\\Users\\andre\\LitigationOS", "litigation_context.db")

OUTPUT_DIR = os.path.join("C:\\Users\\andre\\LitigationOS", "12_WORKSPACE", "THEMANBEARPIG_v7")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "layer_authority_data.json")

AUTHORITY_TYPE_COLORS = {
    "MCR": "#ffd93d",      # Court Rules — gold
    "MCL": "#f39c12",      # Statutes — amber
    "MRE": "#e67e22",      # Evidence Rules — orange
    "USC": "#3498db",      # Federal — blue
    "CONST": "#2ecc71",    # Constitutional — green
    "CASE": "#9b59b6",     # Case Law — purple
    "FRCP": "#1abc9c",     # Fed Rules — teal
    "OTHER": "#95a5a6",    # Other — gray
}

RELATIONSHIP_WEIGHTS = {
    "supports": 1.0,
    "cites": 0.8,
    "co_cited": 0.5,
    "interprets": 0.9,
    "modifies": 0.7,
    "overrides": 0.6,
    "extends": 0.8,
}


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA cache_size=-32000")
    return conn


def classify_citation(cite_text):
    """Classify a citation into authority type."""
    if not cite_text:
        return "OTHER"
    cite = cite_text.upper().strip()
    if re.search(r"\bMCR\b", cite):
        return "MCR"
    if re.search(r"\bMCL\b", cite):
        return "MCL"
    if re.search(r"\bMRE\b", cite):
        return "MRE"
    if re.search(r"\bU\.?S\.?C\.?\b|\b42\s+USC\b|\b28\s+USC\b", cite):
        return "USC"
    if re.search(r"\bCONST\b|\bAMEND\b|\bART\b.*\b(SECT|§)\b", cite):
        return "CONST"
    if re.search(r"\bFRCP\b|\bFED\.?\s*R\b", cite):
        return "FRCP"
    if re.search(r"\b\d+\s+MICH\b|\bMICH\s+APP\b|\bNW\s*2D\b|\bUS\s+\d+\b", cite):
        return "CASE"
    if re.search(r"\bV\.?\s+\b", cite) and re.search(r"\b\d+\b", cite):
        return "CASE"
    return "OTHER"


def normalize_lane(lane_str):
    if not lane_str or lane_str.strip() == "":
        return "ALL"
    lane = lane_str.strip().upper()
    for primary in ["A", "B", "C", "D", "E", "F", "CRIMINAL"]:
        if primary in lane:
            return primary
    return "ALL"


def extract_authority_data():
    conn = get_connection()
    nodes = []
    edges = []

    verify_cols = [r[1] for r in conn.execute("PRAGMA table_info(authority_chains_v2)").fetchall()]

    # --- 1. Get top citations by connection count ---
    top_primary = conn.execute(
        "SELECT primary_citation, COUNT(*) as cnt "
        "FROM authority_chains_v2 "
        "GROUP BY primary_citation ORDER BY cnt DESC LIMIT 150"
    ).fetchall()

    top_supporting = conn.execute(
        "SELECT supporting_citation, COUNT(*) as cnt "
        "FROM authority_chains_v2 "
        "GROUP BY supporting_citation ORDER BY cnt DESC LIMIT 150"
    ).fetchall()

    # Collect all unique citations from top entries
    top_cites = {}
    for r in top_primary:
        top_cites[r["primary_citation"]] = top_cites.get(r["primary_citation"], 0) + r["cnt"]
    for r in top_supporting:
        top_cites[r["supporting_citation"]] = top_cites.get(r["supporting_citation"], 0) + r["cnt"]

    # Rank and take top 300
    ranked_cites = sorted(top_cites.items(), key=lambda x: -x[1])[:300]
    cite_set = {c[0] for c in ranked_cites}

    # --- 2. Get lanes per citation ---
    cite_lanes = defaultdict(set)
    for cite_text, _ in ranked_cites:
        rows = conn.execute(
            "SELECT DISTINCT lane FROM authority_chains_v2 "
            "WHERE primary_citation = ? OR supporting_citation = ? LIMIT 10",
            (cite_text, cite_text),
        ).fetchall()
        for r in rows:
            cite_lanes[cite_text].add(normalize_lane(r["lane"]))

    # --- 3. Get relationships among top citations ---
    placeholders = ",".join("?" for _ in cite_set)
    chain_rows = conn.execute(
        f"SELECT primary_citation, supporting_citation, relationship, lane, source_type "
        f"FROM authority_chains_v2 "
        f"WHERE primary_citation IN ({placeholders}) AND supporting_citation IN ({placeholders})",
        list(cite_set) + list(cite_set),
    ).fetchall()

    # --- 4. Get relationship type distribution ---
    rel_dist = conn.execute(
        "SELECT relationship, COUNT(*) as cnt FROM authority_chains_v2 GROUP BY relationship ORDER BY cnt DESC LIMIT 20"
    ).fetchall()

    # --- 5. Get source type distribution ---
    src_dist = conn.execute(
        "SELECT source_type, COUNT(*) as cnt FROM authority_chains_v2 "
        "WHERE source_type IS NOT NULL GROUP BY source_type ORDER BY cnt DESC LIMIT 15"
    ).fetchall()

    conn.close()

    # === BUILD NODES ===

    # Authority type hub nodes
    type_counts = defaultdict(int)
    for cite_text, count in ranked_cites:
        atype = classify_citation(cite_text)
        type_counts[atype] += 1

    for atype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        nodes.append({
            "id": f"ach-type-{atype.lower()}",
            "label": f"{atype} ({count} authorities)",
            "type": "AuthorityType",
            "layer": "AUTHORITY_CHAIN",
            "lane": "ALL",
            "size": min(25, 8 + count / 10),
            "color": AUTHORITY_TYPE_COLORS.get(atype, "#95a5a6"),
            "metadata": {"authority_type": atype, "count": count},
        })

    # Individual citation nodes
    for cite_text, count in ranked_cites:
        atype = classify_citation(cite_text)
        cite_id = re.sub(r"[^a-zA-Z0-9]", "_", cite_text)[:50]
        lanes = sorted(cite_lanes.get(cite_text, {"ALL"}))

        nodes.append({
            "id": f"ach-cite-{cite_id}",
            "label": cite_text[:60],
            "type": "Citation",
            "layer": "AUTHORITY_CHAIN",
            "lane": lanes[0] if len(lanes) == 1 else ",".join(lanes[:3]),
            "size": min(18, 3 + (count / 50)),
            "color": AUTHORITY_TYPE_COLORS.get(atype, "#95a5a6"),
            "metadata": {
                "citation": cite_text,
                "authority_type": atype,
                "connection_count": count,
                "lanes": lanes,
            },
        })

        # Edge: type hub → citation
        edges.append({
            "source": f"ach-type-{atype.lower()}",
            "target": f"ach-cite-{cite_id}",
            "type": "CLASSIFIES",
            "layer": "AUTHORITY_CHAIN",
            "weight": min(1.0, count / 200),
            "label": atype,
        })

    # Build node ID lookup for edges
    node_ids = {n["id"] for n in nodes}
    cite_to_id = {}
    for cite_text, _ in ranked_cites:
        cite_id = re.sub(r"[^a-zA-Z0-9]", "_", cite_text)[:50]
        cite_to_id[cite_text] = f"ach-cite-{cite_id}"

    # Citation chain edges (deduplicated)
    edge_seen = set()
    for r in chain_rows:
        src_id = cite_to_id.get(r["primary_citation"])
        tgt_id = cite_to_id.get(r["supporting_citation"])
        if src_id and tgt_id and src_id != tgt_id:
            edge_key = (src_id, tgt_id, r["relationship"])
            if edge_key not in edge_seen:
                edge_seen.add(edge_key)
                rel = r["relationship"] or "co_cited"
                edges.append({
                    "source": src_id,
                    "target": tgt_id,
                    "type": "CITES",
                    "layer": "AUTHORITY_CHAIN",
                    "weight": RELATIONSHIP_WEIGHTS.get(rel, 0.5),
                    "label": rel,
                })

    result = {
        "layer": "AUTHORITY_CHAIN",
        "generated": datetime.utcnow().isoformat(),
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "unique_citations": len(ranked_cites),
            "authority_types": dict(type_counts),
            "relationship_types": {r["relationship"]: r["cnt"] for r in rel_dist},
            "source_types": {r["source_type"]: r["cnt"] for r in src_dist},
        },
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"[AUTHORITY_CHAIN] Nodes: {len(nodes)} | Edges: {len(edges)}")
    print(f"  Unique citations: {len(ranked_cites)}")
    print(f"  Authority types: {dict(type_counts)}")
    print(f"  Chain edges: {len(edge_seen)}")
    print(f"  Output: {OUTPUT_FILE}")
    return result


if __name__ == "__main__":
    extract_authority_data()

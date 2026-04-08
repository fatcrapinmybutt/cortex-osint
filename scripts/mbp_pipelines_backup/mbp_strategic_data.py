#!/usr/bin/env python3
"""
MBP Strategic Positioning Layer — Data Pipeline
Extracts evidence counts, authority counts, filing readiness per lane.
Outputs D3.js-compatible nodes/edges for lane-clustered strategic view.
"""
import json
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "LitigationOS", "litigation_context.db")
if not os.path.exists(DB_PATH):
    DB_PATH = os.path.join("C:\\Users\\andre\\LitigationOS", "litigation_context.db")

OUTPUT_DIR = os.path.join("C:\\Users\\andre\\LitigationOS", "12_WORKSPACE", "THEMANBEARPIG_v7")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "layer_strategic_data.json")

LANE_COLORS = {
    "A": "#e74c3c",  # Custody — red
    "B": "#e67e22",  # Housing — orange
    "C": "#3498db",  # Federal — blue
    "D": "#9b59b6",  # PPO — purple
    "E": "#e84393",  # Judicial — pink
    "F": "#00b894",  # Appellate — green
    "CRIMINAL": "#636e72",  # Criminal — gray
    "ALL": "#fdcb6e",  # Cross-lane — yellow
    "UNASSIGNED": "#b2bec3",  # Unassigned — light gray
}

LANE_LABELS = {
    "A": "Lane A: Custody (2024-001507-DC)",
    "B": "Lane B: Housing (2025-002760-CZ)",
    "C": "Lane C: Federal §1983",
    "D": "Lane D: PPO (2023-5907-PP)",
    "E": "Lane E: Judicial Misconduct",
    "F": "Lane F: Appellate (COA 366810)",
    "CRIMINAL": "CRIMINAL (2025-25245676SM)",
}


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA cache_size=-32000")
    return conn


def verify_table(conn, table_name):
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]
    return cols


def normalize_lane(lane_str):
    """Normalize lane values to primary lanes."""
    if not lane_str or lane_str.strip() == "":
        return "UNASSIGNED"
    lane = lane_str.strip().upper()
    for primary in ["A", "B", "C", "D", "E", "F", "CRIMINAL"]:
        if primary in lane:
            return primary
    if lane in ("ALL", "REF", "FILING", "MULTI-COURT"):
        return "ALL"
    return "UNASSIGNED"


def extract_strategic_data():
    conn = get_connection()
    nodes = []
    edges = []

    # --- Verify schemas ---
    ev_cols = verify_table(conn, "evidence_quotes")
    ac_cols = verify_table(conn, "authority_chains_v2")
    fp_cols = verify_table(conn, "filing_packages")
    dl_cols = verify_table(conn, "deadlines")
    jv_cols = verify_table(conn, "judicial_violations")

    # --- 1. Evidence counts per lane ---
    ev_lane_counts = defaultdict(int)
    rows = conn.execute("SELECT lane, COUNT(*) as cnt FROM evidence_quotes GROUP BY lane").fetchall()
    for r in rows:
        lane = normalize_lane(r["lane"])
        ev_lane_counts[lane] += r["cnt"]

    # --- 2. Authority counts per lane ---
    auth_lane_counts = defaultdict(int)
    rows = conn.execute("SELECT lane, COUNT(*) as cnt FROM authority_chains_v2 GROUP BY lane").fetchall()
    for r in rows:
        lane = normalize_lane(r["lane"])
        auth_lane_counts[lane] += r["cnt"]

    # --- 3. Judicial violations per lane ---
    jv_lane_counts = defaultdict(int)
    if "lane" in jv_cols:
        rows = conn.execute("SELECT lane, COUNT(*) as cnt FROM judicial_violations GROUP BY lane").fetchall()
        for r in rows:
            lane = normalize_lane(r["lane"])
            jv_lane_counts[lane] += r["cnt"]

    # --- 4. Filing packages per lane ---
    filing_data = {}
    if "lane" in fp_cols:
        rows = conn.execute("SELECT filing_id, title, lane, status, doc_count FROM filing_packages").fetchall()
        for r in rows:
            lane = normalize_lane(r["lane"])
            filing_data[r["filing_id"]] = {
                "title": r["title"],
                "lane": lane,
                "status": r["status"],
                "doc_count": r["doc_count"] or 0,
            }

    # --- 5. Deadlines ---
    deadline_data = []
    rows = conn.execute("SELECT id, title, due_date, filing_id, status, urgency FROM deadlines").fetchall()
    for r in rows:
        deadline_data.append(dict(r))

    # --- 6. Top evidence categories per lane ---
    cat_by_lane = defaultdict(lambda: defaultdict(int))
    rows = conn.execute(
        "SELECT lane, category, COUNT(*) as cnt FROM evidence_quotes "
        "WHERE category IS NOT NULL AND category != '' GROUP BY lane, category"
    ).fetchall()
    for r in rows:
        lane = normalize_lane(r["lane"])
        cat_by_lane[lane][r["category"]] += r["cnt"]

    # --- 7. Cross-lane connections (evidence that spans multiple lanes) ---
    cross_lane_rows = conn.execute(
        "SELECT lane, COUNT(*) as cnt FROM evidence_quotes WHERE lane LIKE '%,%' GROUP BY lane"
    ).fetchall()
    cross_lane_links = []
    for r in cross_lane_rows:
        parts = [p.strip().upper() for p in r["lane"].split(",") if p.strip()]
        for i in range(len(parts)):
            for j in range(i + 1, len(parts)):
                cross_lane_links.append((parts[i], parts[j], r["cnt"]))

    conn.close()

    # === BUILD NODES ===
    all_lanes = sorted(set(list(ev_lane_counts.keys()) + list(auth_lane_counts.keys())))
    primary_lanes = [l for l in all_lanes if l in LANE_COLORS]

    # Lane hub nodes
    for lane in primary_lanes:
        ev_count = ev_lane_counts.get(lane, 0)
        auth_count = auth_lane_counts.get(lane, 0)
        jv_count = jv_lane_counts.get(lane, 0)
        total_strength = ev_count + auth_count + jv_count

        nodes.append({
            "id": f"str-lane-{lane}",
            "label": LANE_LABELS.get(lane, f"Lane {lane}"),
            "type": "LaneHub",
            "layer": "STRATEGIC",
            "lane": lane,
            "size": min(30, 8 + (total_strength / 5000)),
            "color": LANE_COLORS.get(lane, "#b2bec3"),
            "metadata": {
                "evidence_count": ev_count,
                "authority_count": auth_count,
                "violation_count": jv_count,
                "total_strength": total_strength,
            },
        })

    # Evidence density nodes per lane (top 5 categories per lane)
    for lane in primary_lanes:
        cats = cat_by_lane.get(lane, {})
        top_cats = sorted(cats.items(), key=lambda x: -x[1])[:5]
        for cat, count in top_cats:
            cat_id = cat.lower().replace(" ", "_").replace("/", "_")[:30]
            node_id = f"str-ev-{lane}-{cat_id}"
            nodes.append({
                "id": node_id,
                "label": f"{cat} ({count})",
                "type": "EvidenceCluster",
                "layer": "STRATEGIC",
                "lane": lane,
                "size": min(20, 4 + (count / 500)),
                "color": LANE_COLORS.get(lane, "#b2bec3"),
                "metadata": {"category": cat, "count": count},
            })
            edges.append({
                "source": f"str-lane-{lane}",
                "target": node_id,
                "type": "HAS_EVIDENCE",
                "layer": "STRATEGIC",
                "weight": min(1.0, count / 10000),
                "label": f"{count} items",
            })

    # Filing package nodes
    for fid, fdata in filing_data.items():
        lane = fdata["lane"]
        nodes.append({
            "id": f"str-filing-{fid}",
            "label": f"{fid}: {fdata['title'][:40]}",
            "type": "FilingPackage",
            "layer": "STRATEGIC",
            "lane": lane,
            "size": 10,
            "color": "#4d96ff",
            "metadata": {
                "filing_id": fid,
                "status": fdata["status"],
                "doc_count": fdata["doc_count"],
            },
        })
        if f"str-lane-{lane}" in [n["id"] for n in nodes]:
            edges.append({
                "source": f"str-lane-{lane}",
                "target": f"str-filing-{fid}",
                "type": "HAS_FILING",
                "layer": "STRATEGIC",
                "weight": 0.8,
                "label": fdata["status"],
            })

    # Deadline nodes
    for dl in deadline_data:
        fid = dl.get("filing_id", "")
        dl_id = f"str-deadline-{dl['id']}"
        nodes.append({
            "id": dl_id,
            "label": f"DL: {dl['title'][:40]}",
            "type": "Deadline",
            "layer": "STRATEGIC",
            "lane": "ALL",
            "size": 6 + (dl.get("urgency", 5) / 2),
            "color": "#ff4444" if dl.get("urgency", 5) >= 8 else "#ffd93d",
            "metadata": {
                "due_date": dl.get("due_date"),
                "status": dl.get("status"),
                "urgency": dl.get("urgency"),
            },
        })
        if fid and f"str-filing-{fid}" in [n["id"] for n in nodes]:
            edges.append({
                "source": f"str-filing-{fid}",
                "target": dl_id,
                "type": "HAS_DEADLINE",
                "layer": "STRATEGIC",
                "weight": 0.9,
                "label": dl.get("due_date", ""),
            })

    # Cross-lane connection edges
    link_agg = defaultdict(int)
    for src, tgt, cnt in cross_lane_links:
        key = tuple(sorted([src, tgt]))
        link_agg[key] += cnt

    for (src, tgt), cnt in link_agg.items():
        if f"str-lane-{src}" in [n["id"] for n in nodes] and f"str-lane-{tgt}" in [n["id"] for n in nodes]:
            edges.append({
                "source": f"str-lane-{src}",
                "target": f"str-lane-{tgt}",
                "type": "CROSS_LANE",
                "layer": "STRATEGIC",
                "weight": min(1.0, cnt / 1000),
                "label": f"{cnt} shared evidence",
            })

    result = {
        "layer": "STRATEGIC",
        "generated": datetime.utcnow().isoformat(),
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "lanes_covered": len(primary_lanes),
            "evidence_total": sum(ev_lane_counts.values()),
            "authority_total": sum(auth_lane_counts.values()),
        },
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"[STRATEGIC] Nodes: {len(nodes)} | Edges: {len(edges)}")
    print(f"  Lanes: {', '.join(primary_lanes)}")
    print(f"  Evidence total: {sum(ev_lane_counts.values()):,}")
    print(f"  Authority total: {sum(auth_lane_counts.values()):,}")
    print(f"  Output: {OUTPUT_FILE}")
    return result


if __name__ == "__main__":
    extract_strategic_data()

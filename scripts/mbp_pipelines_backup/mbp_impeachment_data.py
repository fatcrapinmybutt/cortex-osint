#!/usr/bin/env python3
"""
MBP Impeachment Weapons Layer — Data Pipeline
Extracts impeachment_matrix (value >= 5) and contradiction_map entries.
Outputs D3.js nodes for adversary targets with cross-exam ammunition edges.
"""
import json
import os
import sqlite3
import sys
import re
from collections import defaultdict
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "LitigationOS", "litigation_context.db")
if not os.path.exists(DB_PATH):
    DB_PATH = os.path.join("C:\\Users\\andre\\LitigationOS", "litigation_context.db")

OUTPUT_DIR = os.path.join("C:\\Users\\andre\\LitigationOS", "12_WORKSPACE", "THEMANBEARPIG_v7")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "layer_impeachment_data.json")

SEVERITY_COLORS = {
    "critical": "#e74c3c",
    "high": "#e67e22",
    "medium": "#f1c40f",
    "low": "#95a5a6",
}

CATEGORY_COLORS = {
    "FALSE_ALLEGATIONS": "#e74c3c",
    "ALBERT_PREMEDITATED": "#d63031",
    "ALIENATION": "#e84393",
    "CREDIBILITY": "#fdcb6e",
    "EVIDENCE_FABRICATION": "#ff7675",
    "JUDICIAL_BIAS": "#a29bfe",
    "PPO_ABUSE": "#6c5ce7",
    "CONTEMPT_ABUSE": "#00b894",
    "DUE_PROCESS": "#0984e3",
    "METH_PROJECTION": "#d35400",
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


def extract_target_from_text(text):
    """Extract adversary target names from evidence text."""
    targets = set()
    patterns = [
        r"\b(Emily\s*(?:A\.?\s*)?Watson)\b",
        r"\b(Watson)\b",
        r"\b(McNeill|Judge\s+McNeill)\b",
        r"\b(Albert\s+Watson)\b",
        r"\b(Pamela\s+Rusco|Rusco)\b",
        r"\b(Ronald?\s+Berry)\b",
        r"\b(Jennifer\s+Barnes|Barnes)\b",
        r"\b(Hoopes|Judge\s+Hoopes)\b",
        r"\b(Ladas-Hoopes|Ladas)\b",
    ]
    if text:
        for pat in patterns:
            if re.search(pat, text, re.IGNORECASE):
                m = re.search(pat, text, re.IGNORECASE)
                name = m.group(1).strip()
                # Normalize
                name_lower = name.lower()
                if "watson" in name_lower and "albert" not in name_lower:
                    targets.add("Emily A. Watson")
                elif "albert" in name_lower:
                    targets.add("Albert Watson")
                elif "mcneill" in name_lower:
                    targets.add("Judge McNeill")
                elif "rusco" in name_lower:
                    targets.add("Pamela Rusco")
                elif "berry" in name_lower:
                    targets.add("Ronald Berry")
                elif "barnes" in name_lower:
                    targets.add("Jennifer Barnes")
                elif "hoopes" in name_lower:
                    targets.add("Judge Hoopes")
                elif "ladas" in name_lower:
                    targets.add("Judge Ladas-Hoopes")
    return targets


def extract_impeachment_data():
    conn = get_connection()
    nodes = []
    edges = []

    imp_cols = verify_table(conn, "impeachment_matrix")
    con_cols = verify_table(conn, "contradiction_map")

    # --- 1. Impeachment Matrix (value >= 5) ---
    imp_rows = conn.execute(
        "SELECT id, category, evidence_summary, source_file, quote_text, "
        "impeachment_value, cross_exam_question, filing_relevance, event_date "
        "FROM impeachment_matrix WHERE impeachment_value >= 5 "
        "ORDER BY impeachment_value DESC"
    ).fetchall()

    # Track adversary targets
    target_stats = defaultdict(lambda: {"count": 0, "total_value": 0, "categories": defaultdict(int)})

    # Category hub nodes
    category_counts = defaultdict(int)
    for r in imp_rows:
        category_counts[r["category"]] += 1

    # Create category hub nodes (top 15)
    top_categories = sorted(category_counts.items(), key=lambda x: -x[1])[:15]
    for cat, count in top_categories:
        cat_id = cat.lower().replace(" ", "_")[:30] if cat else "unknown"
        color = CATEGORY_COLORS.get(cat, "#636e72")
        nodes.append({
            "id": f"imp-cat-{cat_id}",
            "label": f"{cat} ({count})",
            "type": "ImpeachmentCategory",
            "layer": "IMPEACHMENT",
            "lane": "ALL",
            "size": min(25, 6 + (count / 100)),
            "color": color,
            "metadata": {"category": cat, "count": count},
        })

    # Sample high-value impeachment items (top 200 by value)
    for r in imp_rows[:200]:
        imp_id = f"imp-item-{r['id']}"
        cat = r["category"] or "UNKNOWN"
        cat_id = cat.lower().replace(" ", "_")[:30]
        value = r["impeachment_value"] or 5

        summary = (r["evidence_summary"] or "")[:80]
        nodes.append({
            "id": imp_id,
            "label": summary,
            "type": "ImpeachmentWeapon",
            "layer": "IMPEACHMENT",
            "lane": "ALL",
            "size": 3 + (value / 2),
            "color": "#e74c3c" if value >= 9 else "#e67e22" if value >= 7 else "#f1c40f",
            "metadata": {
                "impeachment_value": value,
                "category": cat,
                "cross_exam_question": (r["cross_exam_question"] or "")[:200],
                "event_date": r["event_date"],
                "source_file": r["source_file"],
            },
        })

        # Edge: category → item
        if f"imp-cat-{cat_id}" in [n["id"] for n in nodes]:
            edges.append({
                "source": f"imp-cat-{cat_id}",
                "target": imp_id,
                "type": "IMPEACHES",
                "layer": "IMPEACHMENT",
                "weight": value / 10.0,
                "label": f"value={value}",
            })

        # Track targets from text
        all_text = f"{r['evidence_summary'] or ''} {r['quote_text'] or ''} {r['cross_exam_question'] or ''}"
        targets = extract_target_from_text(all_text)
        for tname in targets:
            target_stats[tname]["count"] += 1
            target_stats[tname]["total_value"] += value
            target_stats[tname]["categories"][cat] += 1

    # --- 2. Adversary target nodes ---
    for tname, stats in sorted(target_stats.items(), key=lambda x: -x[1]["total_value"]):
        tid = tname.lower().replace(" ", "_").replace(".", "")[:30]
        avg_val = stats["total_value"] / max(stats["count"], 1)
        nodes.append({
            "id": f"imp-target-{tid}",
            "label": f"TARGET: {tname}",
            "type": "AdversaryTarget",
            "layer": "IMPEACHMENT",
            "lane": "ALL",
            "size": min(30, 8 + (stats["count"] / 20)),
            "color": "#d63031",
            "metadata": {
                "name": tname,
                "impeachment_count": stats["count"],
                "total_value": stats["total_value"],
                "avg_value": round(avg_val, 1),
                "top_categories": dict(sorted(stats["categories"].items(), key=lambda x: -x[1])[:5]),
            },
        })

        # Connect target to its top categories
        for cat, cnt in sorted(stats["categories"].items(), key=lambda x: -x[1])[:3]:
            cat_id = cat.lower().replace(" ", "_")[:30]
            if f"imp-cat-{cat_id}" in [n["id"] for n in nodes]:
                edges.append({
                    "source": f"imp-target-{tid}",
                    "target": f"imp-cat-{cat_id}",
                    "type": "TARGETED_BY",
                    "layer": "IMPEACHMENT",
                    "weight": min(1.0, cnt / 50),
                    "label": f"{cnt} items",
                })

    # --- 3. Contradiction Map ---
    con_rows = conn.execute(
        "SELECT id, claim_id, source_a, source_b, contradiction_text, severity, lane "
        "FROM contradiction_map ORDER BY severity DESC"
    ).fetchall()

    # Contradiction severity hub nodes
    sev_counts = defaultdict(int)
    for r in con_rows:
        sev_counts[r["severity"] or "unknown"] += 1

    for sev, count in sev_counts.items():
        nodes.append({
            "id": f"imp-sev-{sev}",
            "label": f"Contradictions: {sev.upper()} ({count})",
            "type": "ContradictionSeverity",
            "layer": "IMPEACHMENT",
            "lane": "ALL",
            "size": min(20, 6 + (count / 100)),
            "color": SEVERITY_COLORS.get(sev, "#636e72"),
            "metadata": {"severity": sev, "count": count},
        })

    # Sample contradictions (top 150)
    for r in con_rows[:150]:
        con_id = f"imp-con-{r['id']}"
        sev = r["severity"] or "unknown"
        text = (r["contradiction_text"] or "")[:80]

        nodes.append({
            "id": con_id,
            "label": text,
            "type": "Contradiction",
            "layer": "IMPEACHMENT",
            "lane": r["lane"] or "ALL",
            "size": 5 if sev == "critical" else 4,
            "color": SEVERITY_COLORS.get(sev, "#636e72"),
            "metadata": {
                "claim_id": r["claim_id"],
                "source_a": r["source_a"],
                "source_b": r["source_b"],
                "severity": sev,
            },
        })

        # Edge: severity hub → contradiction
        edges.append({
            "source": f"imp-sev-{sev}",
            "target": con_id,
            "type": "CONTRADICTS",
            "layer": "IMPEACHMENT",
            "weight": 0.9 if sev == "critical" else 0.7,
            "label": sev,
        })

    conn.close()

    result = {
        "layer": "IMPEACHMENT",
        "generated": datetime.utcnow().isoformat(),
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "impeachment_items": len(imp_rows),
            "high_value_items": len([r for r in imp_rows if (r["impeachment_value"] or 0) >= 8]),
            "contradiction_count": len(con_rows),
            "adversary_targets": len(target_stats),
        },
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"[IMPEACHMENT] Nodes: {len(nodes)} | Edges: {len(edges)}")
    print(f"  Impeachment items (>=5): {len(imp_rows):,}")
    print(f"  High value (>=8): {len([r for r in imp_rows if (r['impeachment_value'] or 0) >= 8]):,}")
    print(f"  Contradictions: {len(con_rows):,}")
    print(f"  Adversary targets: {len(target_stats)}")
    print(f"  Output: {OUTPUT_FILE}")
    return result


if __name__ == "__main__":
    extract_impeachment_data()

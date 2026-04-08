#!/usr/bin/env python3
"""
MBP Filing Timeline Layer — Data Pipeline
Extracts timeline_events with dates, filing_packages with deadlines.
Outputs temporal nodes for Gantt-style lane swimlane visualization.
"""
import json
import os
import sqlite3
import re
from collections import defaultdict
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "LitigationOS", "litigation_context.db")
if not os.path.exists(DB_PATH):
    DB_PATH = os.path.join("C:\\Users\\andre\\LitigationOS", "litigation_context.db")

OUTPUT_DIR = os.path.join("C:\\Users\\andre\\LitigationOS", "12_WORKSPACE", "THEMANBEARPIG_v7")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "layer_timeline_data.json")

LANE_COLORS = {
    "A": "#e74c3c",
    "B": "#e67e22",
    "C": "#3498db",
    "D": "#9b59b6",
    "E": "#e84393",
    "F": "#00b894",
    "CRIMINAL": "#636e72",
    "ALL": "#fdcb6e",
}

CATEGORY_ICONS = {
    "court_order": "⚖️",
    "filing": "📄",
    "hearing": "🎤",
    "incident": "⚠️",
    "contact": "👤",
    "deadline": "⏰",
    "separation": "💔",
    "arrest": "🚔",
    "evidence": "🔍",
}

SEVERITY_SIZES = {
    "critical": 12,
    "high": 9,
    "medium": 6,
    "low": 4,
}


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA cache_size=-32000")
    return conn


def normalize_lane(lane_str):
    if not lane_str or lane_str.strip() == "":
        return "ALL"
    lane = lane_str.strip().upper()
    for primary in ["A", "B", "C", "D", "E", "F", "CRIMINAL"]:
        if primary in lane:
            return primary
    return "ALL"


def parse_date(date_str):
    """Parse various date formats, return ISO date string or None."""
    if not date_str or date_str.strip() == "":
        return None
    date_str = date_str.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(date_str[:19], fmt).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            continue
    # Try extracting just a date pattern
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", date_str)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


def extract_timeline_data():
    conn = get_connection()
    nodes = []
    edges = []

    # Verify schemas
    te_cols = [r[1] for r in conn.execute("PRAGMA table_info(timeline_events)").fetchall()]
    dl_cols = [r[1] for r in conn.execute("PRAGMA table_info(deadlines)").fetchall()]
    fp_cols = [r[1] for r in conn.execute("PRAGMA table_info(filing_packages)").fetchall()]

    # --- 1. Timeline events with valid dates ---
    # Get distribution first
    total_events = conn.execute("SELECT COUNT(*) FROM timeline_events").fetchone()[0]
    dated_events = conn.execute(
        "SELECT COUNT(*) FROM timeline_events WHERE event_date IS NOT NULL AND event_date != ''"
    ).fetchone()[0]

    # Get events with severity-based sampling
    # Critical/high: all; medium: sample; low: sample more aggressively
    high_sev_events = conn.execute(
        "SELECT id, event_date, event_description, actors, lane, category, severity, filing_relevance "
        "FROM timeline_events "
        "WHERE event_date IS NOT NULL AND event_date != '' "
        "AND (severity = 'critical' OR severity = 'high') "
        "ORDER BY event_date"
    ).fetchall()

    medium_events = conn.execute(
        "SELECT id, event_date, event_description, actors, lane, category, severity, filing_relevance "
        "FROM timeline_events "
        "WHERE event_date IS NOT NULL AND event_date != '' "
        "AND severity = 'medium' "
        "ORDER BY event_date LIMIT 200"
    ).fetchall()

    # Also get key milestone events regardless of severity
    milestone_events = conn.execute(
        "SELECT id, event_date, event_description, actors, lane, category, severity, filing_relevance "
        "FROM timeline_events "
        "WHERE event_date IS NOT NULL AND event_date != '' "
        "AND (category LIKE '%order%' OR category LIKE '%hearing%' OR category LIKE '%filing%' "
        "     OR category LIKE '%arrest%' OR category LIKE '%trial%' OR category LIKE '%separation%') "
        "ORDER BY event_date LIMIT 200"
    ).fetchall()

    # Merge and deduplicate by ID
    all_events_map = {}
    for r in list(high_sev_events) + list(medium_events) + list(milestone_events):
        all_events_map[r["id"]] = r

    all_events = sorted(all_events_map.values(), key=lambda r: r["event_date"] or "")

    # --- 2. Lane swimlane structure ---
    lane_event_counts = defaultdict(int)
    lane_date_ranges = defaultdict(lambda: {"min": "9999", "max": "0000"})

    for r in all_events:
        lane = normalize_lane(r["lane"])
        lane_event_counts[lane] += 1
        parsed = parse_date(r["event_date"])
        if parsed:
            if parsed < lane_date_ranges[lane]["min"]:
                lane_date_ranges[lane]["min"] = parsed
            if parsed > lane_date_ranges[lane]["max"]:
                lane_date_ranges[lane]["max"] = parsed

    # Create lane swimlane nodes
    lane_y_positions = {"A": 0.1, "B": 0.2, "C": 0.3, "D": 0.4, "E": 0.5, "F": 0.6, "CRIMINAL": 0.7, "ALL": 0.85}
    for lane, count in sorted(lane_event_counts.items()):
        nodes.append({
            "id": f"tl-lane-{lane}",
            "label": f"Lane {lane} ({count} events)",
            "type": "TimelineLane",
            "layer": "TIMELINE",
            "lane": lane,
            "size": 6,
            "color": LANE_COLORS.get(lane, "#636e72"),
            "metadata": {
                "event_count": count,
                "date_range": dict(lane_date_ranges[lane]),
                "y_position": lane_y_positions.get(lane, 0.9),
            },
        })

    # --- 3. Event nodes ---
    for r in all_events:
        parsed_date = parse_date(r["event_date"])
        if not parsed_date:
            continue

        lane = normalize_lane(r["lane"])
        sev = (r["severity"] or "medium").lower()
        cat = (r["category"] or "event").lower()

        desc = (r["event_description"] or "")[:80]
        icon = ""
        for key, emoji in CATEGORY_ICONS.items():
            if key in cat:
                icon = emoji
                break

        event_id = f"tl-ev-{r['id']}"
        nodes.append({
            "id": event_id,
            "label": f"{icon} {desc}",
            "type": "TimelineEvent",
            "layer": "TIMELINE",
            "lane": lane,
            "size": SEVERITY_SIZES.get(sev, 5),
            "color": LANE_COLORS.get(lane, "#636e72"),
            "metadata": {
                "date": parsed_date,
                "category": r["category"],
                "actors": r["actors"],
                "severity": sev,
                "filing_relevance": r["filing_relevance"],
                "y_position": lane_y_positions.get(lane, 0.9),
            },
        })

        # Edge: lane → event
        edges.append({
            "source": f"tl-lane-{lane}",
            "target": event_id,
            "type": "CONTAINS_EVENT",
            "layer": "TIMELINE",
            "weight": 0.9 if sev == "critical" else 0.6 if sev == "high" else 0.3,
            "label": parsed_date,
        })

    # --- 4. Deadline nodes ---
    deadline_rows = conn.execute(
        "SELECT id, title, due_date, filing_id, court, case_number, status, urgency, notes "
        "FROM deadlines ORDER BY due_date"
    ).fetchall()

    for r in deadline_rows:
        parsed_date = parse_date(r["due_date"])
        dl_id = f"tl-dl-{r['id']}"
        urgency = r["urgency"] or 5

        nodes.append({
            "id": dl_id,
            "label": f"DL: {(r['title'] or '')[:50]}",
            "type": "Deadline",
            "layer": "TIMELINE",
            "lane": "ALL",
            "size": 8 + urgency,
            "color": "#ff4444" if urgency >= 8 else "#ffd93d" if urgency >= 5 else "#00b894",
            "metadata": {
                "date": parsed_date,
                "due_date": r["due_date"],
                "status": r["status"],
                "urgency": urgency,
                "court": r["court"],
                "case_number": r["case_number"],
                "filing_id": r["filing_id"],
            },
        })

    # --- 5. Filing package milestone nodes ---
    filing_rows = conn.execute(
        "SELECT filing_id, title, lane, case_number, status, doc_count FROM filing_packages"
    ).fetchall()

    for r in filing_rows:
        lane = normalize_lane(r["lane"])
        fid = f"tl-fp-{r['filing_id']}"

        nodes.append({
            "id": fid,
            "label": f"PKG {r['filing_id']}: {(r['title'] or '')[:40]}",
            "type": "FilingMilestone",
            "layer": "TIMELINE",
            "lane": lane,
            "size": 10,
            "color": "#4d96ff",
            "metadata": {
                "filing_id": r["filing_id"],
                "status": r["status"],
                "doc_count": r["doc_count"] or 0,
                "case_number": r["case_number"],
            },
        })

        # Connect filing to its lane
        if f"tl-lane-{lane}" in [n["id"] for n in nodes]:
            edges.append({
                "source": f"tl-lane-{lane}",
                "target": fid,
                "type": "HAS_FILING",
                "layer": "TIMELINE",
                "weight": 0.8,
                "label": r["status"] or "unknown",
            })

    # --- 6. Key milestone markers (hardcoded critical dates) ---
    milestones = [
        ("2023-10-13", "Emily recants: 'nothing was physical'", "D", "critical"),
        ("2023-10-15", "Emily files PPO — 2 days after recanting", "D", "critical"),
        ("2024-04-01", "Andrew files Complaint for Custody", "A", "critical"),
        ("2024-04-29", "EX PARTE ORDER — Joint legal/physical 50/50", "A", "critical"),
        ("2024-07-17", "TRIAL — Sole custody to Mother", "A", "critical"),
        ("2025-05-04", "Albert admits reports for ex parte custody", "E", "critical"),
        ("2025-07-29", "LAST CONTACT — Father's last day with L.D.W.", "A", "critical"),
        ("2025-08-09", "EX PARTE ORDER — ALL parenting time SUSPENDED", "A", "critical"),
        ("2025-09-28", "CUSTODY ORDER — Emily 100%, zero for Father", "A", "critical"),
        ("2026-03-25", "Emergency Motion filed (restore parenting time)", "A", "high"),
    ]

    for i, (mdate, mdesc, mlane, msev) in enumerate(milestones):
        ms_id = f"tl-milestone-{i}"
        nodes.append({
            "id": ms_id,
            "label": f"[!] {mdesc}",
            "type": "CriticalMilestone",
            "layer": "TIMELINE",
            "lane": mlane,
            "size": 15,
            "color": "#d63031",
            "metadata": {
                "date": mdate,
                "severity": msev,
                "is_milestone": True,
                "y_position": lane_y_positions.get(mlane, 0.5),
            },
        })

    conn.close()

    # --- Category distribution ---
    cat_dist = defaultdict(int)
    for n in nodes:
        if n.get("metadata", {}).get("category"):
            cat_dist[n["metadata"]["category"]] += 1

    result = {
        "layer": "TIMELINE",
        "generated": datetime.utcnow().isoformat(),
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "total_db_events": total_events,
            "dated_events": dated_events,
            "exported_events": len(all_events),
            "deadlines": len(deadline_rows),
            "filing_packages": len(filing_rows),
            "critical_milestones": len(milestones),
            "lanes_with_events": len(lane_event_counts),
        },
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"[TIMELINE] Nodes: {len(nodes)} | Edges: {len(edges)}")
    print(f"  DB events total: {total_events:,} | With dates: {dated_events:,}")
    print(f"  Exported events: {len(all_events):,}")
    print(f"  Deadlines: {len(deadline_rows)} | Filings: {len(filing_rows)}")
    print(f"  Critical milestones: {len(milestones)}")
    print(f"  Output: {OUTPUT_FILE}")
    return result


if __name__ == "__main__":
    extract_timeline_data()

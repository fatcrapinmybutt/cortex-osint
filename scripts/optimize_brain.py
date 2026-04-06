#!/usr/bin/env python3
"""
optimize_brain.py — Add FTS5 + composite indexes + ANALYZE to mbp_brain.db
Eliminates 896ms LIKE searches → sub-ms FTS5. Adds composite indexes for common queries.
"""
import sqlite3
import sys
import time
from pathlib import Path

BRAIN_DB = Path(__file__).resolve().parent.parent / "mbp_brain.db"

def main():
    if not BRAIN_DB.exists():
        print(f"ERROR: {BRAIN_DB} not found")
        return 1

    conn = sqlite3.connect(str(BRAIN_DB))
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA cache_size = -32000")

    total_start = time.perf_counter()

    # ── 1. FTS5 virtual table on nodes (label + description) ──────────
    print("=" * 60)
    print("Phase 1: FTS5 virtual table for nodes")
    has_fts = conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='nodes_fts'"
    ).fetchone()[0]

    if has_fts:
        print("  nodes_fts already exists — rebuilding...")
        conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild')")
    else:
        print("  Creating nodes_fts (content-synced with nodes)...")
        t0 = time.perf_counter()
        conn.execute("""
            CREATE VIRTUAL TABLE nodes_fts USING fts5(
                label, description, id,
                content='nodes',
                content_rowid='rowid',
                tokenize='porter unicode61'
            )
        """)
        # Populate from existing nodes
        conn.execute("""
            INSERT INTO nodes_fts(rowid, label, description, id)
            SELECT rowid, label, COALESCE(description,''), id FROM nodes
        """)
        elapsed = time.perf_counter() - t0
        row_count = conn.execute("SELECT count(*) FROM nodes_fts").fetchone()[0]
        print(f"  [OK] nodes_fts created: {row_count:,} rows in {elapsed:.1f}s")

    # Also create FTS triggers for auto-sync on INSERT/UPDATE/DELETE
    print("  Creating auto-sync triggers...")
    conn.executescript("""
        CREATE TRIGGER IF NOT EXISTS nodes_fts_ai AFTER INSERT ON nodes BEGIN
            INSERT INTO nodes_fts(rowid, label, description, id)
            VALUES (new.rowid, new.label, COALESCE(new.description,''), new.id);
        END;
        CREATE TRIGGER IF NOT EXISTS nodes_fts_ad AFTER DELETE ON nodes BEGIN
            INSERT INTO nodes_fts(nodes_fts, rowid, label, description, id)
            VALUES ('delete', old.rowid, old.label, COALESCE(old.description,''), old.id);
        END;
        CREATE TRIGGER IF NOT EXISTS nodes_fts_au AFTER UPDATE ON nodes BEGIN
            INSERT INTO nodes_fts(nodes_fts, rowid, label, description, id)
            VALUES ('delete', old.rowid, old.label, COALESCE(old.description,''), old.id);
            INSERT INTO nodes_fts(rowid, label, description, id)
            VALUES (new.rowid, new.label, COALESCE(new.description,''), new.id);
        END;
    """)
    print("  [OK] Auto-sync triggers installed")

    # ── 2. Composite indexes ──────────────────────────────────────────
    print("\nPhase 2: Composite indexes")
    indexes = [
        ("idx_nodes_layer_type", "nodes", "layer, node_type"),
        ("idx_nodes_lane_layer", "nodes", "lane, layer"),
        ("idx_edges_source_type", "edges", "source_id, edge_type"),
        ("idx_edges_target_type", "edges", "target_id, edge_type"),
        ("idx_edges_type_weight", "edges", "edge_type, weight DESC"),
        ("idx_chains_strength", "chains", "strength_score DESC"),
        ("idx_gaps_priority_resolved", "gaps", "priority, resolved"),
    ]
    for name, table, cols in indexes:
        t0 = time.perf_counter()
        conn.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table}({cols})")
        elapsed = time.perf_counter() - t0
        print(f"  [OK] {name} ({elapsed:.3f}s)")

    # ── 3. Run ANALYZE for query planner stats ────────────────────────
    print("\nPhase 3: ANALYZE (update query planner statistics)")
    t0 = time.perf_counter()
    conn.execute("ANALYZE")
    elapsed = time.perf_counter() - t0
    print(f"  [OK] ANALYZE complete ({elapsed:.1f}s)")

    conn.commit()

    # ── 4. Benchmark: FTS5 vs LIKE ────────────────────────────────────
    print("\nPhase 4: Benchmark validation")
    test_queries = ["custody", "McNeill", "PPO", "disqualification"]
    for q in test_queries:
        # FTS5
        t0 = time.perf_counter()
        fts_rows = conn.execute(
            "SELECT n.* FROM nodes_fts f JOIN nodes n ON f.rowid = n.rowid "
            "WHERE nodes_fts MATCH ? LIMIT 200", (q,)
        ).fetchall()
        fts_ms = (time.perf_counter() - t0) * 1000

        # LIKE (old method)
        t0 = time.perf_counter()
        like_rows = conn.execute(
            "SELECT * FROM nodes WHERE label LIKE ? OR description LIKE ? LIMIT 200",
            (f"%{q}%", f"%{q}%"),
        ).fetchall()
        like_ms = (time.perf_counter() - t0) * 1000

        speedup = like_ms / fts_ms if fts_ms > 0 else float("inf")
        print(f"  '{q}': FTS5={fts_ms:.1f}ms ({len(fts_rows)} rows) vs LIKE={like_ms:.1f}ms ({len(like_rows)} rows) → {speedup:.0f}× faster")

    # ── 5. Final stats ────────────────────────────────────────────────
    total_elapsed = time.perf_counter() - total_start
    idx_count = conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='index'"
    ).fetchone()[0]
    fts_count = conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='table' AND name LIKE '%_fts%'"
    ).fetchone()[0]
    trigger_count = conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='trigger'"
    ).fetchone()[0]

    print(f"\n{'=' * 60}")
    print(f"OPTIMIZATION COMPLETE in {total_elapsed:.1f}s")
    print(f"  Indexes: {idx_count} | FTS5 tables: {fts_count} | Triggers: {trigger_count}")
    print(f"  DB size: {BRAIN_DB.stat().st_size / 1048576:.1f} MB")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Evidence Graph Bridge — Event-driven litigation_context.db → mbp_brain.db sync.

Reads new/changed evidence from litigation_context.db, extracts entity nodes and
relationship edges, and upserts them into mbp_brain.db for the THEMANBEARPIG
visualization layer.  Operates incrementally via a queue table so full rebuilds
are unnecessary after initial sync.
"""

import hashlib
import json
import logging
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Optional

from .meek import classify as meek_classify

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path constants (centralised — change here if drives move)
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(os.environ.get(
    "LITIGATIONOS_ROOT",
    r"C:\Users\andre\LitigationOS",
))
LITIGATION_DB_PATH = _REPO_ROOT / "litigation_context.db"
MBP_BRAIN_DB_PATH = _REPO_ROOT / "mbp_brain.db"

# ---------------------------------------------------------------------------
# Source tables we sync, with the text column(s) to read for entity extraction
# ---------------------------------------------------------------------------
SOURCE_TABLE_CONFIG: dict[str, dict] = {
    "evidence_quotes": {
        "text_cols": ["quote_text"],
        "id_col": "rowid",
        "edge_type": "supports",
        "layer": "evidence",
    },
    "timeline_events": {
        "text_cols": ["event_description"],
        "id_col": "rowid",
        "edge_type": "temporal",
        "layer": "timeline",
    },
    "impeachment_matrix": {
        "text_cols": ["evidence_summary", "cross_exam_question"],
        "id_col": "rowid",
        "edge_type": "impeaches",
        "layer": "impeachment",
    },
    "contradiction_map": {
        "text_cols": ["contradiction_text"],
        "id_col": "rowid",
        "edge_type": "contradicts",
        "layer": "contradiction",
    },
    "authority_chains_v2": {
        "text_cols": ["primary_citation", "supporting_citation"],
        "id_col": "rowid",
        "edge_type": "cites",
        "layer": "authority",
    },
}

# ---------------------------------------------------------------------------
# Entity extraction compiled patterns
# ---------------------------------------------------------------------------
_RE_PERSON = re.compile(
    r"\b([A-Z][a-z]{1,20})\s+([A-Z][a-z]{1,20}(?:\s+[A-Z][a-z]{1,20})?)\b"
)
_RE_MCR = re.compile(r"\bMCR\s+(\d+\.\d+(?:\([A-Za-z0-9]+\))*)", re.IGNORECASE)
_RE_MCL = re.compile(r"\bMCL\s+(\d+\.\d+[a-z]?(?:\([A-Za-z0-9]+\))*)", re.IGNORECASE)
_RE_MRE = re.compile(r"\bMRE\s+(\d+(?:\([A-Za-z0-9]+\))*)", re.IGNORECASE)
_RE_USC = re.compile(r"\b(\d+)\s+U\.?S\.?C\.?\s+(?:§\s*)?(\d+[a-z]?)", re.IGNORECASE)
_RE_CASE_NO = re.compile(r"\b(\d{4}-\d{2,8}-[A-Z]{2,4})\b")
_RE_ISO_DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")

# Noise filter: common English word-pairs that look like person names
_PERSON_NOISE = frozenset({
    "best interest", "court order", "united states", "supreme court",
    "circuit court", "trial court", "personal protection", "law enforcement",
    "child protective", "friend court", "district court", "good cause",
    "due process", "clear convincing", "change circumstances",
    "general rule", "other factors", "mental health",
})


def _stable_id(*parts: str) -> str:
    """Deterministic 12-char hex id from concatenated parts."""
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:12]


def _connect(path: Path, *, readonly: bool = False) -> sqlite3.Connection:
    """Open a SQLite connection with mandatory PRAGMAs."""
    if not path.exists() and readonly:
        raise FileNotFoundError(f"Database not found: {path}")
    uri = f"file:///{path.as_posix()}"
    if readonly:
        uri += "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=120)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA cache_size = -32000")
    conn.execute("PRAGMA temp_store = MEMORY")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    """Return the set of column names for *table* via PRAGMA table_info."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {r["name"] for r in rows}


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


# ═══════════════════════════════════════════════════════════════════════════
# Main Engine
# ═══════════════════════════════════════════════════════════════════════════

class EvidenceGraphBridge:
    """Event-driven pipeline: litigation_context.db → mbp_brain.db."""

    def __init__(
        self,
        litigation_db: Optional[Path] = None,
        mbp_db: Optional[Path] = None,
    ):
        self._lit_path = litigation_db or LITIGATION_DB_PATH
        self._mbp_path = mbp_db or MBP_BRAIN_DB_PATH
        # Lazy connections
        self._lit_conn: Optional[sqlite3.Connection] = None
        self._mbp_conn: Optional[sqlite3.Connection] = None
        # Cache verified source-table schemas
        self._verified_tables: dict[str, set[str]] = {}

    # ── connection properties (lazy, auto-reconnect) ──────────────────────

    @property
    def lit_conn(self) -> sqlite3.Connection:
        if self._lit_conn is None:
            self._lit_conn = _connect(self._lit_path)
            logger.info("Connected to litigation_context.db (%s)", self._lit_path)
        return self._lit_conn

    @property
    def mbp_conn(self) -> sqlite3.Connection:
        if self._mbp_conn is None:
            self._mbp_conn = _connect(self._mbp_path)
            logger.info("Connected to mbp_brain.db (%s)", self._mbp_path)
        return self._mbp_conn

    def close(self) -> None:
        for label, conn in [("lit", self._lit_conn), ("mbp", self._mbp_conn)]:
            if conn is not None:
                try:
                    conn.close()
                except Exception as exc:
                    logger.warning("Error closing %s connection: %s", label, exc)
        self._lit_conn = None
        self._mbp_conn = None

    # ── schema bootstrap ──────────────────────────────────────────────────

    def ensure_queue_table(self) -> None:
        """Create graph_update_queue in litigation_context.db if not exists."""
        self.lit_conn.executescript("""
            CREATE TABLE IF NOT EXISTS graph_update_queue (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                source_table TEXT NOT NULL,
                source_rowid INTEGER NOT NULL,
                event_type  TEXT    DEFAULT 'INSERT',
                lane        TEXT,
                processed   INTEGER DEFAULT 0,
                created_at  TEXT    DEFAULT (datetime('now')),
                processed_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_guq_unprocessed
                ON graph_update_queue(processed, created_at);
            CREATE INDEX IF NOT EXISTS idx_guq_source
                ON graph_update_queue(source_table, source_rowid);
        """)
        logger.info("graph_update_queue table ensured in litigation_context.db")

    def ensure_mbp_tables(self) -> None:
        """Create nodes/edges tables in mbp_brain.db if they don't already exist.

        Uses the schema that already exists in production mbp_brain.db so the
        bridge is compatible with existing data.
        """
        self.mbp_conn.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (
                id              TEXT PRIMARY KEY,
                node_type       TEXT,
                layer           TEXT,
                label           TEXT,
                description     TEXT,
                date_start      TEXT,
                date_end        TEXT,
                severity        REAL,
                confidence      REAL,
                readiness       REAL,
                binding_strength TEXT,
                source_table    TEXT,
                source_id       TEXT,
                lane            TEXT,
                metadata        TEXT,
                created_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_nodes_type_lane
                ON nodes(node_type, lane);
            CREATE INDEX IF NOT EXISTS idx_nodes_layer
                ON nodes(layer);
            CREATE INDEX IF NOT EXISTS idx_nodes_source
                ON nodes(source_table, source_id);

            CREATE TABLE IF NOT EXISTS edges (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id   TEXT NOT NULL,
                target_id   TEXT NOT NULL,
                edge_type   TEXT,
                weight      REAL DEFAULT 1.0,
                evidence    TEXT,
                source_table TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
            CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
            CREATE INDEX IF NOT EXISTS idx_edges_type   ON edges(edge_type);
        """)
        logger.info("nodes/edges tables ensured in mbp_brain.db")

    # ── queue operations ──────────────────────────────────────────────────

    def queue_event(
        self,
        source_table: str,
        source_rowid: int,
        event_type: str = "INSERT",
        lane: Optional[str] = None,
    ) -> None:
        """Insert a single event into graph_update_queue."""
        self.lit_conn.execute(
            "INSERT INTO graph_update_queue "
            "(source_table, source_rowid, event_type, lane) VALUES (?, ?, ?, ?)",
            (source_table, source_rowid, event_type, lane),
        )
        self.lit_conn.commit()

    def queue_bulk(
        self,
        rows: list[tuple[str, int, str, Optional[str]]],
    ) -> int:
        """Bulk-insert events. Each row is (source_table, source_rowid, event_type, lane)."""
        self.lit_conn.executemany(
            "INSERT INTO graph_update_queue "
            "(source_table, source_rowid, event_type, lane) VALUES (?, ?, ?, ?)",
            rows,
        )
        self.lit_conn.commit()
        return len(rows)

    # ── entity extraction ─────────────────────────────────────────────────

    @staticmethod
    def classify_lane(text: str) -> str:
        """MEEK lane classification (delegates to meek module)."""
        return meek_classify(text)

    @staticmethod
    def extract_entities(
        text: str,
        source_table: str,
        source_id: str,
    ) -> list[tuple[str, str, str]]:
        """Extract entity nodes from *text*.

        Returns list of (node_id, label, node_type) tuples.
        """
        if not text:
            return []

        entities: list[tuple[str, str, str]] = []
        seen: set[str] = set()

        def _add(label: str, ntype: str) -> None:
            nid = _stable_id(ntype, label)
            if nid not in seen:
                seen.add(nid)
                entities.append((nid, label, ntype))

        # Persons
        for m in _RE_PERSON.finditer(text):
            full = m.group(0).strip()
            if full.lower() in _PERSON_NOISE:
                continue
            if len(full) < 4:
                continue
            _add(full, "person")

        # Legal citations
        for m in _RE_MCR.finditer(text):
            _add(f"MCR {m.group(1)}", "rule")
        for m in _RE_MCL.finditer(text):
            _add(f"MCL {m.group(1)}", "statute")
        for m in _RE_MRE.finditer(text):
            _add(f"MRE {m.group(1)}", "rule")
        for m in _RE_USC.finditer(text):
            _add(f"{m.group(1)} USC {m.group(2)}", "federal_statute")

        # Case numbers
        for m in _RE_CASE_NO.finditer(text):
            _add(m.group(1), "case")

        # Dates
        for m in _RE_ISO_DATE.finditer(text):
            _add(m.group(1), "date")

        return entities

    # ── edge generation ───────────────────────────────────────────────────

    @staticmethod
    def generate_edges(
        source_node_id: str,
        entity_nodes: list[tuple[str, str, str]],
        source_table: str,
    ) -> list[tuple[str, str, str, float, str]]:
        """Create edges from a source document node to its extracted entities.

        Returns list of (source_id, target_id, edge_type, weight, source_table).
        """
        table_cfg = SOURCE_TABLE_CONFIG.get(source_table, {})
        edge_type = table_cfg.get("edge_type", "references")
        weight = 1.0

        edges: list[tuple[str, str, str, float, str]] = []
        for node_id, _label, _ntype in entity_nodes:
            edges.append((source_node_id, node_id, edge_type, weight, source_table))

        # Cross-entity edges: connect persons to citations found in the same row
        persons = [n for n in entity_nodes if n[2] == "person"]
        citations = [n for n in entity_nodes if n[2] in ("rule", "statute", "federal_statute")]
        for p_id, _, _ in persons:
            for c_id, _, _ in citations:
                edges.append((p_id, c_id, "associated_with", 0.5, source_table))

        return edges

    # ── source row reading (schema-adaptive) ──────────────────────────────

    def _verify_source_table(self, table: str) -> set[str]:
        """Verify a source table exists and cache its columns."""
        if table in self._verified_tables:
            return self._verified_tables[table]
        if not _table_exists(self.lit_conn, table):
            logger.warning("Source table '%s' does not exist in litigation_context.db", table)
            self._verified_tables[table] = set()
            return set()
        cols = _table_columns(self.lit_conn, table)
        self._verified_tables[table] = cols
        return cols

    def _read_source_row(self, table: str, rowid: int) -> Optional[dict]:
        """Read a single row from a source table, returning dict or None."""
        cols = self._verify_source_table(table)
        if not cols:
            return None
        cfg = SOURCE_TABLE_CONFIG.get(table)
        if cfg is None:
            logger.warning("No config for source table '%s'", table)
            return None

        # Build column list from config, only including columns that actually exist
        want_cols = list(cfg["text_cols"])
        id_col = cfg["id_col"]

        # Also grab lane if present
        if "lane" in cols:
            want_cols.append("lane")
        if "category" in cols:
            want_cols.append("category")
        if "source_file" in cols:
            want_cols.append("source_file")
        if "event_date" in cols:
            want_cols.append("event_date")
        if "severity" in cols:
            want_cols.append("severity")

        available = [c for c in want_cols if c in cols]
        if not available:
            return None

        select_clause = ", ".join(available)
        try:
            row = self.lit_conn.execute(
                f"SELECT {select_clause} FROM {table} WHERE {id_col} = ?",
                (rowid,),
            ).fetchone()
        except sqlite3.OperationalError as exc:
            logger.error("Error reading %s rowid %d: %s", table, rowid, exc)
            return None

        if row is None:
            return None

        return dict(row)

    # ── queue processing (core pipeline) ──────────────────────────────────

    def process_queue(self, batch_size: int = 100) -> int:
        """Process unprocessed queue items → extract entities → upsert graph.

        Returns the number of queue items processed.
        """
        self.ensure_queue_table()
        self.ensure_mbp_tables()

        queue_items = self.lit_conn.execute(
            "SELECT id, source_table, source_rowid, event_type, lane "
            "FROM graph_update_queue "
            "WHERE processed = 0 "
            "ORDER BY created_at "
            "LIMIT ?",
            (batch_size,),
        ).fetchall()

        if not queue_items:
            return 0

        processed_count = 0
        node_batch: list[tuple] = []
        edge_batch: list[tuple] = []
        processed_ids: list[int] = []

        for item in queue_items:
            qid = item["id"]
            table = item["source_table"]
            rowid = item["source_rowid"]
            lane_override = item["lane"]

            row_data = self._read_source_row(table, rowid)
            if row_data is None:
                # Source row deleted or table missing — mark processed, skip
                processed_ids.append(qid)
                processed_count += 1
                continue

            # Combine text columns for entity extraction
            cfg = SOURCE_TABLE_CONFIG[table]
            text_parts = []
            for col in cfg["text_cols"]:
                val = row_data.get(col)
                if val:
                    text_parts.append(str(val))
            combined_text = " ".join(text_parts)

            # Lane: use override, then row's own lane, then MEEK classification
            lane = lane_override or row_data.get("lane") or self.classify_lane(combined_text)

            # Create a source-document node
            src_node_id = _stable_id(table, str(rowid))
            src_label = combined_text[:120] if combined_text else f"{table}:{rowid}"
            layer = cfg.get("layer", "evidence")
            severity = row_data.get("severity")
            date_start = row_data.get("event_date")
            metadata = json.dumps(
                {"source_file": row_data.get("source_file", "")},
                ensure_ascii=False,
            )

            node_batch.append((
                src_node_id,        # id
                "document",         # node_type
                layer,              # layer
                src_label,          # label
                combined_text[:500] if combined_text else None,  # description
                date_start,         # date_start
                None,               # date_end
                float(severity) if severity is not None else None,  # severity
                None,               # confidence
                None,               # readiness
                None,               # binding_strength
                table,              # source_table
                str(rowid),         # source_id
                lane,               # lane
                metadata,           # metadata
            ))

            # Extract entities and create their nodes
            entities = self.extract_entities(combined_text, table, str(rowid))
            for eid, elabel, etype in entities:
                node_batch.append((
                    eid, etype, layer, elabel, None,
                    None, None, None, None, None, None,
                    table, str(rowid), lane, None,
                ))

            # Generate edges
            raw_edges = self.generate_edges(src_node_id, entities, table)
            for s_id, t_id, e_type, w, s_table in raw_edges:
                evidence_ref = json.dumps(
                    {"source_table": s_table, "source_rowid": rowid},
                    ensure_ascii=False,
                )
                edge_batch.append((s_id, t_id, e_type, w, evidence_ref, s_table))

            processed_ids.append(qid)
            processed_count += 1

        # Upsert nodes into mbp_brain.db
        if node_batch:
            self.mbp_conn.executemany(
                "INSERT OR REPLACE INTO nodes "
                "(id, node_type, layer, label, description, "
                " date_start, date_end, severity, confidence, readiness, "
                " binding_strength, source_table, source_id, lane, metadata) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                node_batch,
            )

        # Insert edges (no REPLACE — edges accumulate)
        if edge_batch:
            self.mbp_conn.executemany(
                "INSERT INTO edges "
                "(source_id, target_id, edge_type, weight, evidence, source_table) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                edge_batch,
            )

        self.mbp_conn.commit()

        # Mark queue items processed
        if processed_ids:
            placeholders = ",".join("?" * len(processed_ids))
            self.lit_conn.execute(
                f"UPDATE graph_update_queue "
                f"SET processed = 1, processed_at = datetime('now') "
                f"WHERE id IN ({placeholders})",
                processed_ids,
            )
            self.lit_conn.commit()

        logger.info(
            "Processed %d queue items → %d nodes, %d edges",
            processed_count, len(node_batch), len(edge_batch),
        )
        return processed_count

    # ── full sync ─────────────────────────────────────────────────────────

    def sync_full(
        self,
        tables: Optional[list[str]] = None,
        page_size: int = 5000,
    ) -> dict[str, int]:
        """Full sync: queue all rows from source tables, then process.

        Returns dict of {table_name: rows_queued}.
        """
        self.ensure_queue_table()
        target_tables = tables or list(SOURCE_TABLE_CONFIG.keys())
        result: dict[str, int] = {}

        for table in target_tables:
            cols = self._verify_source_table(table)
            if not cols:
                logger.warning("Skipping %s — table not found", table)
                result[table] = 0
                continue

            cfg = SOURCE_TABLE_CONFIG[table]
            id_col = cfg["id_col"]

            # Count total rows
            try:
                total = self.lit_conn.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()[0]
            except sqlite3.OperationalError as exc:
                logger.error("Cannot count %s: %s", table, exc)
                result[table] = 0
                continue

            logger.info("Full sync: %s — %d rows to queue", table, total)

            queued = 0
            offset = 0
            while offset < total:
                rows = self.lit_conn.execute(
                    f"SELECT {id_col} FROM {table} LIMIT ? OFFSET ?",
                    (page_size, offset),
                ).fetchall()

                if not rows:
                    break

                batch = [(table, r[0], "FULL_SYNC", None) for r in rows]
                self.queue_bulk(batch)
                queued += len(batch)
                offset += page_size

                if queued % 10000 < page_size:
                    logger.info("  %s: queued %d / %d", table, queued, total)

            result[table] = queued
            logger.info("Full sync queued %d rows from %s", queued, table)

        # Now process everything
        total_processed = 0
        while True:
            n = self.process_queue(batch_size=500)
            if n == 0:
                break
            total_processed += n
            if total_processed % 5000 < 500:
                logger.info("  Processing: %d items done so far", total_processed)

        logger.info("Full sync complete — %d total items processed", total_processed)
        return result

    # ── stats ─────────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Return bridge health statistics."""
        stats: dict = {}

        # Queue stats
        if _table_exists(self.lit_conn, "graph_update_queue"):
            row = self.lit_conn.execute(
                "SELECT "
                "  (SELECT COUNT(*) FROM graph_update_queue WHERE processed = 0) AS pending, "
                "  (SELECT COUNT(*) FROM graph_update_queue WHERE processed = 1) AS done, "
                "  (SELECT MAX(processed_at) FROM graph_update_queue) AS last_sync"
            ).fetchone()
            stats["queue_pending"] = row["pending"]
            stats["queue_done"] = row["done"]
            stats["last_sync"] = row["last_sync"]
        else:
            stats["queue_pending"] = 0
            stats["queue_done"] = 0
            stats["last_sync"] = None

        # Graph stats from mbp_brain.db
        if _table_exists(self.mbp_conn, "nodes") and _table_exists(self.mbp_conn, "edges"):
            row = self.mbp_conn.execute(
                "SELECT "
                "  (SELECT COUNT(*) FROM nodes) AS node_count, "
                "  (SELECT COUNT(*) FROM edges) AS edge_count"
            ).fetchone()
            stats["node_count"] = row["node_count"]
            stats["edge_count"] = row["edge_count"]
        else:
            stats["node_count"] = 0
            stats["edge_count"] = 0

        return stats

    # ── context manager ───────────────────────────────────────────────────

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


# ═══════════════════════════════════════════════════════════════════════════
# CLI entry point
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Evidence Graph Bridge — litigation_context.db → mbp_brain.db"
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("stats", help="Show bridge statistics")
    sub.add_parser("init", help="Create queue and graph tables")

    p_queue = sub.add_parser("queue", help="Queue an event")
    p_queue.add_argument("table", help="Source table name")
    p_queue.add_argument("rowid", type=int, help="Source row ID")
    p_queue.add_argument("--event", default="INSERT", help="Event type")
    p_queue.add_argument("--lane", default=None, help="Lane override")

    p_process = sub.add_parser("process", help="Process pending queue items")
    p_process.add_argument("--batch", type=int, default=100, help="Batch size")

    p_sync = sub.add_parser("sync", help="Full sync from source tables")
    p_sync.add_argument("--tables", nargs="*", default=None, help="Tables to sync")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    with EvidenceGraphBridge() as bridge:
        if args.command == "init":
            bridge.ensure_queue_table()
            bridge.ensure_mbp_tables()
            print("Tables initialised.")

        elif args.command == "stats":
            s = bridge.get_stats()
            for k, v in s.items():
                print(f"  {k}: {v}")

        elif args.command == "queue":
            bridge.queue_event(args.table, args.rowid, args.event, args.lane)
            print(f"Queued {args.table}:{args.rowid} ({args.event})")

        elif args.command == "process":
            n = bridge.process_queue(batch_size=args.batch)
            print(f"Processed {n} items.")

        elif args.command == "sync":
            result = bridge.sync_full(tables=args.tables)
            for tbl, cnt in result.items():
                print(f"  {tbl}: {cnt} rows queued")

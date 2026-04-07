#!/usr/bin/env python3
"""NEXUS v2 — Persistent Litigation Intelligence Daemon.

Architecture: Long-running Python process communicating via line-delimited JSON
over stdin/stdout. Keeps ALL database connections warm for sub-5ms responses.

Backends:
  - SQLite WAL (litigation_context.db) — primary OLTP
  - DuckDB (analytical overlays) — 10-100× faster aggregations
  - LanceDB (semantic search, 75K vectors) — sub-ms similarity

Protocol: One JSON object per line on stdin, one JSON response per line on stdout.
  Request:  {"id": "abc", "action": "query", "sql": "SELECT ...", "params": [...]}
  Response: {"id": "abc", "ok": true, "rows": [...], "columns": [...], "count": N}
  Error:    {"id": "abc", "ok": false, "error": "message"}

Actions (59):
  # Core
  query / analytics / fts_search / stats / ping
  # Evidence & Search
  search_evidence / search_impeachment / search_contradictions / search_authority
  # NEXUS Intelligence
  nexus_fuse / nexus_argue / nexus_readiness / nexus_damages
  # LEXOS Instant
  narrative / filing_plan / rules_check / adversary / gap_analysis / cross_connect
  # Case Operations
  judicial_intel / timeline_search / case_context / filing_status / deadlines
  # Document Management (NEW)
  list_documents / get_document / search_documents / ingest_pdf / bulk_ingest
  # Knowledge Graph & Rules (NEW)
  lookup_rule / query_graph / lookup_authority
  # Intelligence (NEW)
  assess_risk / get_vehicle_map / case_health / adversary_threats
  filing_pipeline / get_subagent_spec
  # Evolution Pipeline (NEW)
  evolution_stats / search_evolved / cross_refs / convergence_status
  # System & Master Data (NEW)
  stats_extended / self_test / ingest_csv / query_master
  # Advanced Intelligence (NEW)
  vector_search / self_audit / evidence_chain / compute_deadlines / red_team
  # Resilience & Diagnostics (ABSORBED from MCP)
  health / record_error / get_error_summary / check_disk_space / scan_all_systems
  # Document Lifecycle (ABSORBED from MCP)
  document_exists / hash_exists / delete_document / insert_document
  # Evolution Write Pipeline (ABSORBED from MCP)
  evolve_md / evolve_txt / evolve_pages
  # Fleet Dispatch (ABSORBED from MCP)
  dispatch_to_swarm

Started by extension.mjs on load. Stays alive for entire session.
"""

import json
import re
import sqlite3
import sys
import os
import traceback
from datetime import datetime, date, timedelta
from enum import Enum
import shutil
import hashlib
import threading

# ── stdout guard: ALL output goes through protocol, never bare prints ─────
_original_stdout = sys.stdout
_original_stderr = sys.stderr

# Redirect stderr to a log file so import warnings don't corrupt JSON-RPC
LOG_PATH = os.path.join(os.environ.get("TEMP", "."), "nexus_daemon.log")
try:
    _log_file = open(LOG_PATH, "a", encoding="utf-8")
    sys.stderr = _log_file
except OSError:
    pass

# ── Optional imports (graceful degradation) ───────────────────────────────
_HAS_DUCKDB = False
_HAS_LANCEDB = False

try:
    import duckdb
    _HAS_DUCKDB = True
except ImportError:
    pass

try:
    import lancedb
    _HAS_LANCEDB = True
except ImportError:
    pass

# ── Configuration ─────────────────────────────────────────────────────────
DB_PATH = r"C:\Users\andre\LitigationOS\litigation_context.db"
LANCEDB_PATH = r"C:\Users\andre\LitigationOS\00_SYSTEM\engines\semantic\lancedb_store"

PRAGMAS = [
    "PRAGMA busy_timeout = 60000",
    "PRAGMA journal_mode = WAL",
    "PRAGMA cache_size = -32000",
    "PRAGMA temp_store = MEMORY",
    "PRAGMA synchronous = NORMAL",
    "PRAGMA mmap_size = 268435456",
]

# ── FTS5 Safety ───────────────────────────────────────────────────────────
def sanitize_fts5(query):
    """Sanitize FTS5 query: keep alphanumeric, spaces, quotes, wildcards."""
    return re.sub(r'[^\w\s*"]', ' ', query).strip()

# ── Connection Pool (warm, persistent) ────────────────────────────────────

class ConnectionPool:
    """Persistent database connections — opened once, used throughout session."""

    def __init__(self):
        self._sqlite = None
        self._duckdb = None
        self._lancedb_table = None

    @property
    def sqlite(self):
        if self._sqlite is None:
            self._sqlite = sqlite3.connect(DB_PATH)
            self._sqlite.row_factory = sqlite3.Row
            for pragma in PRAGMAS:
                self._sqlite.execute(pragma)
        return self._sqlite

    @property
    def duck(self):
        if self._duckdb is None and _HAS_DUCKDB:
            self._duckdb = duckdb.connect(":memory:")
            self._duckdb.execute("INSTALL sqlite; LOAD sqlite;")
            self._duckdb.execute(f"ATTACH '{DB_PATH}' AS lit (TYPE sqlite, READ_ONLY)")
        return self._duckdb

    @property
    def lance_table(self):
        if self._lancedb_table is None and _HAS_LANCEDB:
            try:
                db = lancedb.connect(LANCEDB_PATH)
                tables = db.table_names()
                if tables:
                    self._lancedb_table = db.open_table(tables[0])
            except Exception:
                pass
        return self._lancedb_table

    def close(self):
        if self._sqlite:
            self._sqlite.close()
        if self._duckdb:
            self._duckdb.close()


pool = ConnectionPool()

# ── CircuitBreaker (absorbed from MCP db.py) ──────────────────────────────

class CircuitBreakerState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """Trip after N failures, auto-reset after cooldown.

    States: CLOSED (normal) → OPEN (blocking) → HALF_OPEN (testing).
    Ported from MCP db.py lines 188-238, upgraded with thread safety.
    """

    def __init__(self, failure_threshold=5, reset_timeout=60):
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._last_failure_time = None
        self._lock = threading.Lock()

    def record_failure(self):
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now()
            if self._failure_count >= self._failure_threshold:
                self._state = CircuitBreakerState.OPEN

    def record_success(self):
        with self._lock:
            self._failure_count = 0
            self._state = CircuitBreakerState.CLOSED

    def allow_request(self):
        with self._lock:
            if self._state == CircuitBreakerState.CLOSED:
                return True
            if self._state == CircuitBreakerState.OPEN:
                if self._last_failure_time and \
                   (datetime.now() - self._last_failure_time).total_seconds() > self._reset_timeout:
                    self._state = CircuitBreakerState.HALF_OPEN
                    return True
                return False
            return True  # HALF_OPEN allows one request

    def reset(self):
        with self._lock:
            self._state = CircuitBreakerState.CLOSED
            self._failure_count = 0
            self._last_failure_time = None

    @property
    def status(self):
        return {
            "state": self._state.value,
            "failure_count": self._failure_count,
            "threshold": self._failure_threshold,
            "reset_timeout": self._reset_timeout,
            "last_failure": str(self._last_failure_time) if self._last_failure_time else None,
        }


# ── Error Codes + Recovery Hints (absorbed from MCP db.py) ────────────────

class ErrorCode(Enum):
    ERR_DB_CONNECT = "ERR_DB_CONNECT"
    ERR_PDF_PERMISSION = "ERR_PDF_PERMISSION"
    ERR_PDF_TIMEOUT = "ERR_PDF_TIMEOUT"
    ERR_FTS_SYNTAX = "ERR_FTS_SYNTAX"
    ERR_DB_LOCKED = "ERR_DB_LOCKED"
    ERR_PATH_TRAVERSAL = "ERR_PATH_TRAVERSAL"
    ERR_DISK_FULL = "ERR_DISK_FULL"
    ERR_EVOLUTION_FAIL = "ERR_EVOLUTION_FAIL"


_RECOVERY_HINTS = {
    ErrorCode.ERR_DB_CONNECT: "Check DB path exists and is not locked. Verify WAL mode PRAGMAs.",
    ErrorCode.ERR_PDF_PERMISSION: "File may be open in another program. Close it and retry.",
    ErrorCode.ERR_PDF_TIMEOUT: "PDF extraction timed out. Try a smaller file or increase timeout.",
    ErrorCode.ERR_FTS_SYNTAX: "FTS5 query syntax error. Sanitize query and retry with LIKE fallback.",
    ErrorCode.ERR_DB_LOCKED: "Database is locked. Another process may hold a write lock. Wait and retry.",
    ErrorCode.ERR_PATH_TRAVERSAL: "Path is outside allowed directories. Check _SAFE_ROOTS.",
    ErrorCode.ERR_DISK_FULL: "Disk is full or below 1GB free. Free space before proceeding.",
    ErrorCode.ERR_EVOLUTION_FAIL: "Evolution pipeline failed. Check source files and DB schema.",
}


# ── Health Status Singleton (absorbed from MCP db.py) ─────────────────────

class HealthStatus:
    """Singleton tracking system health — startup time, graph status, degradation."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.startup_time = datetime.now()
            cls._instance.graphs_loaded = False
            cls._instance.graph_errors = []
            cls._instance.degraded = False
            cls._instance.circuit_breaker = CircuitBreaker()
        return cls._instance

    @property
    def status(self):
        uptime = (datetime.now() - self.startup_time).total_seconds()
        return {
            "startup_time": str(self.startup_time),
            "uptime_seconds": round(uptime, 1),
            "graphs_loaded": self.graphs_loaded,
            "graph_errors": self.graph_errors[:5],
            "degraded": self.degraded,
            "circuit_breaker": self.circuit_breaker.status,
        }


health = HealthStatus()

# ── Path Traversal Protection (absorbed from MCP db.py) ───────────────────

_SAFE_ROOTS = [
    os.path.normpath("C:\\Users\\andre\\LitigationOS"),
    os.path.normpath("D:\\"),
    os.path.normpath("F:\\"),
    os.path.normpath("G:\\"),
    os.path.normpath("H:\\"),
    os.path.normpath("I:\\"),
    os.path.normpath("J:\\"),
]


def _validate_path(p):
    """Ensure path is under an allowed root. Raises ValueError on traversal."""
    real = os.path.normpath(os.path.realpath(p))
    for root in _SAFE_ROOTS:
        if real.startswith(root):
            return real
    raise ValueError(f"Path traversal blocked: {p} not under any safe root")


# ── Table Existence Check ─────────────────────────────────────────────────

def _table_exists(conn, table_name):
    """Check if a table exists in the database."""
    row = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    ).fetchone()
    return row[0] > 0 if row else False


# ── Evolution Helpers (ported from MCP db.py) ─────────────────────────────

_RE_MD_HEADING = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
_RE_MCR = re.compile(r"MCR\s+\d+\.\d+[A-Za-z]?(?:\([^)]+\))?")
_RE_MCL = re.compile(r"MCL\s+\d+\.\d+[a-z]?")
_RE_VEHICLE = re.compile(r"\b(?:motion|petition|complaint|brief|application|order)\s+(?:for|to|of)\s+\w+", re.IGNORECASE)
_RE_AGENT = re.compile(r"AGENT:([A-Z_]+)")
_RE_AUTHORITY = re.compile(r"(?:\d+\s+(?:Mich(?:\s+App)?|US|USC|F\.?(?:2d|3d|4th))\s+\d+)")


def _extract_md_sections(text, source_file, source_path):
    """Parse markdown text into section dicts with heading hierarchy."""
    sections = []
    headings = list(_RE_MD_HEADING.finditer(text))

    if not headings:
        sections.append({
            "level": 0, "title": source_file, "path": source_path,
            "content": text[:50000], "source_file": source_file,
        })
        return sections

    for i, m in enumerate(headings):
        level = len(m.group(1))
        title = m.group(2).strip()
        start = m.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        content = text[start:end].strip()[:50000]
        sections.append({
            "level": level, "title": title,
            "path": f"{source_path}#{title.replace(' ', '-').lower()}",
            "content": content, "source_file": source_file,
        })
    return sections


def _extract_cross_refs(text):
    """Extract legal cross-references from text via compiled regex patterns."""
    refs = []
    for m in _RE_MCR.finditer(text):
        refs.append({"ref_type": "rule", "ref_value": m.group(), "confidence": 0.7})
    for m in _RE_MCL.finditer(text):
        refs.append({"ref_type": "rule", "ref_value": m.group(), "confidence": 0.7})
    for m in _RE_VEHICLE.finditer(text):
        refs.append({"ref_type": "vehicle", "ref_value": m.group(), "confidence": 0.5})
    for m in _RE_AGENT.finditer(text):
        refs.append({"ref_type": "agent", "ref_value": m.group(1), "confidence": 0.8})
    for m in _RE_AUTHORITY.finditer(text):
        refs.append({"ref_type": "authority", "ref_value": m.group(), "confidence": 0.6})
    return refs


def _link_ref_to_graph(conn, ref_value):
    """Try to find matching graph_node for a cross-reference value."""
    if not _table_exists(conn, "graph_nodes"):
        return None
    try:
        row = conn.execute(
            "SELECT id, graph_source FROM graph_nodes WHERE label LIKE ? LIMIT 1",
            (f"%{ref_value}%",)
        ).fetchone()
        if row:
            return {"graph_node_id": row[0], "graph_source": row[1]}
    except Exception:
        pass
    return None


# ── Stats Tables ──────────────────────────────────────────────────────────
STATS_TABLES = [
    "evidence_quotes", "authority_chains_v2", "michigan_rules_extracted",
    "timeline_events", "md_sections", "master_citations", "file_inventory",
    "md_cross_refs", "contradiction_map", "judicial_violations",
    "impeachment_matrix", "police_reports", "berry_mcneill_intelligence",
    "documents", "deadlines", "filing_packages", "legal_statutes",
    "michigan_case_law", "court_abbreviations", "catalogue_fts",
]

# ── FTS5 Configuration ───────────────────────────────────────────────────
FTS_CONFIG = {
    "evidence_quotes": {
        "fts_table": "evidence_fts",
        "join": "evidence_quotes eq ON eq.id = evidence_fts.rowid",
        "snippet_col": 0,
        "extra_cols": ["eq.source_file", "eq.category", "eq.lane", "eq.relevance_score"],
    },
    "timeline_events": {
        "fts_table": "timeline_fts",
        "join": None,
        "snippet_col": 0,
        "extra_cols": ["actors"],
    },
}

LIKE_CONFIG = {
    "police_reports": {
        "text_col": "full_text",
        "cols": ["filename", "allegations", "exculpatory", "false_reports"],
    },
    "michigan_rules_extracted": {
        "text_col": "full_text",
        "cols": ["rule_number", "rule_type", "title"],
    },
}

# ══════════════════════════════════════════════════════════════════════════
# ACTION HANDLERS
# ══════════════════════════════════════════════════════════════════════════

def handle_ping(_req):
    """Health check."""
    caps = ["sqlite"]
    if _HAS_DUCKDB: caps.append("duckdb")
    if _HAS_LANCEDB: caps.append("lancedb")
    return {"ok": True, "status": "alive", "capabilities": caps, "db": DB_PATH}


def handle_query(req):
    """Execute parameterized SQL query (READ-ONLY — writes blocked by policy)."""
    sql = req.get("sql", "").strip()
    params = req.get("params", [])
    max_rows = min(req.get("max_rows", 50), 500)

    if not sql:
        return {"ok": False, "error": "No SQL provided"}

    conn = pool.sqlite
    is_write = sql.upper().lstrip().startswith(("INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "REPLACE"))

    # READ-ONLY POLICY: Block all write operations per user mandate (2026-04-14).
    # All DB writes must go through exec_python scripts for auditability and safety.
    if is_write:
        return {"ok": False, "error": "BLOCKED: MCP extension is READ-ONLY. Use exec_python with a script for DB writes."}

    try:
        cur = conn.execute(sql, params)

        rows = cur.fetchmany(max_rows + 1)
        truncated = len(rows) > max_rows
        if truncated:
            rows = rows[:max_rows]

        columns = [desc[0] for desc in cur.description] if cur.description else []
        data = [dict(zip(columns, row)) for row in rows]
        return {
            "ok": True,
            "columns": columns,
            "rows": data,
            "count": len(data),
            "truncated": truncated,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def handle_analytics(req):
    """DuckDB analytical query (10-100× faster for aggregations)."""
    if not _HAS_DUCKDB or pool.duck is None:
        return handle_query(req)  # graceful fallback to SQLite

    sql = req.get("sql", "").strip()
    params = req.get("params", [])
    max_rows = min(req.get("max_rows", 50), 500)

    if not sql:
        return {"ok": False, "error": "No SQL provided"}

    try:
        if params:
            result = pool.duck.execute(sql, params)
        else:
            result = pool.duck.execute(sql)

        rows = result.fetchmany(max_rows)
        columns = [desc[0] for desc in result.description]
        data = [dict(zip(columns, row)) for row in rows]
        return {
            "ok": True,
            "columns": columns,
            "rows": data,
            "count": len(data),
            "engine": "duckdb",
        }
    except Exception as e:
        return {"ok": False, "error": f"DuckDB: {e}"}


def handle_stats(_req):
    """Key table row counts."""
    conn = pool.sqlite
    stats = {}
    for table in STATS_TABLES:
        try:
            cnt = conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]
            stats[table] = cnt
        except Exception:
            stats[table] = -1
    return {"ok": True, "stats": stats}


def handle_fts_search(req):
    """FTS5 search with snippet + LIKE fallback."""
    table = req.get("table", "evidence_quotes")
    query = req.get("query", "")
    limit = min(req.get("limit", 25), 100)
    conn = pool.sqlite

    safe_q = sanitize_fts5(query)
    if not safe_q:
        return {"ok": False, "error": "Empty query after sanitization"}

    # FTS5 path
    if table in FTS_CONFIG:
        cfg = FTS_CONFIG[table]
        fts = cfg["fts_table"]
        try:
            if cfg["join"]:
                sql = (
                    f"SELECT snippet({fts}, {cfg['snippet_col']}, '<b>', '</b>', '...', 40) AS excerpt, "
                    f"{', '.join(cfg['extra_cols'])} "
                    f"FROM {fts} JOIN {cfg['join']} "
                    f"WHERE {fts} MATCH ? ORDER BY rank LIMIT ?"
                )
            else:
                extra = (", " + ", ".join(cfg["extra_cols"])) if cfg["extra_cols"] else ""
                sql = (
                    f"SELECT snippet({fts}, {cfg['snippet_col']}, '<b>', '</b>', '...', 40) AS excerpt{extra} "
                    f"FROM {fts} WHERE {fts} MATCH ? ORDER BY rank LIMIT ?"
                )
            rows = conn.execute(sql, (safe_q, limit)).fetchall()
            columns = [desc[0] for desc in conn.execute(sql, (safe_q, 1)).description] if rows else ["excerpt"]
            return {
                "ok": True,
                "columns": columns,
                "rows": [dict(zip(columns, r)) for r in rows],
                "count": len(rows),
                "engine": "fts5",
            }
        except Exception:
            pass  # fall through to LIKE

    # LIKE fallback
    if table in LIKE_CONFIG:
        cfg = LIKE_CONFIG[table]
        cols = ", ".join(cfg["cols"])
        sql = f"SELECT {cols} FROM {table} WHERE {cfg['text_col']} LIKE ? LIMIT ?"
        rows = conn.execute(sql, (f"%{query}%", limit)).fetchall()
        columns = cfg["cols"]
        return {
            "ok": True,
            "columns": columns,
            "rows": [dict(zip(columns, r)) for r in rows],
            "count": len(rows),
            "engine": "like_fallback",
        }

    return {"ok": False, "error": f"Unknown search table: {table}"}


def handle_search_evidence(req):
    """Search evidence_quotes via FTS5."""
    req["table"] = "evidence_quotes"
    return handle_fts_search(req)


def handle_search_impeachment(req):
    """Search impeachment_matrix."""
    conn = pool.sqlite
    target = req.get("target", "")
    category = req.get("category", "")
    min_sev = req.get("min_severity", 1)
    limit = min(req.get("limit", 25), 100)

    conditions, params = ["impeachment_value >= ?"], [min_sev]
    if target:
        conditions.append("target LIKE ?")
        params.append(f"%{target}%")
    if category:
        conditions.append("category LIKE ?")
        params.append(f"%{category}%")

    where = " AND ".join(conditions)
    sql = f"SELECT * FROM impeachment_matrix WHERE {where} ORDER BY impeachment_value DESC LIMIT ?"
    params.append(limit)

    try:
        cur = conn.execute(sql, params)
        columns = [d[0] for d in cur.description]
        rows = [dict(zip(columns, r)) for r in cur.fetchall()]
        return {"ok": True, "columns": columns, "rows": rows, "count": len(rows)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def handle_search_contradictions(req):
    """Search contradiction_map."""
    conn = pool.sqlite
    entity = req.get("entity", "")
    severity = req.get("severity", "")
    lane = req.get("lane", "")
    limit = min(req.get("limit", 25), 100)

    conditions, params = [], []
    if entity:
        conditions.append("(source_a LIKE ? OR source_b LIKE ? OR contradiction_text LIKE ?)")
        params.extend([f"%{entity}%"] * 3)
    if severity:
        conditions.append("severity = ?")
        params.append(severity)
    if lane:
        conditions.append("lane = ?")
        params.append(lane)

    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"SELECT * FROM contradiction_map{where} ORDER BY CASE severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END LIMIT ?"
    params.append(limit)

    try:
        cur = conn.execute(sql, params)
        columns = [d[0] for d in cur.description]
        rows = [dict(zip(columns, r)) for r in cur.fetchall()]
        return {"ok": True, "columns": columns, "rows": rows, "count": len(rows)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def handle_search_authority(req):
    """Search authority_chains_v2."""
    conn = pool.sqlite
    citation = req.get("citation", "")
    lane = req.get("lane", "")
    source_type = req.get("source_type", "")
    limit = min(req.get("limit", 25), 100)

    conditions, params = [], []
    if citation:
        conditions.append("(primary_citation LIKE ? OR supporting_citation LIKE ?)")
        params.extend([f"%{citation}%", f"%{citation}%"])
    if lane:
        conditions.append("lane = ?")
        params.append(lane)
    if source_type:
        conditions.append("source_type = ?")
        params.append(source_type)

    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"SELECT primary_citation, supporting_citation, relationship, source_document, source_type, lane FROM authority_chains_v2{where} LIMIT ?"
    params.append(limit)

    try:
        cur = conn.execute(sql, params)
        columns = [d[0] for d in cur.description]
        rows = [dict(zip(columns, r)) for r in cur.fetchall()]
        return {"ok": True, "columns": columns, "rows": rows, "count": len(rows)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def handle_nexus_fuse(req):
    """Cross-table evidence fusion — searches 5 sources simultaneously."""
    topic = req.get("topic", "")
    lanes = req.get("lanes", [])
    limit = min(req.get("limit", 50), 100)
    conn = pool.sqlite
    safe_q = sanitize_fts5(topic)
    results = {}

    # 1. evidence_quotes (FTS5)
    try:
        sql = ("SELECT snippet(evidence_fts, 0, '<b>', '</b>', '...', 40) AS excerpt, "
               "eq.source_file, eq.category, eq.lane "
               "FROM evidence_fts JOIN evidence_quotes eq ON eq.id = evidence_fts.rowid "
               "WHERE evidence_fts MATCH ? ORDER BY rank LIMIT ?")
        rows = conn.execute(sql, (safe_q, limit)).fetchall()
        results["evidence"] = [{"excerpt": r[0], "source": r[1], "category": r[2], "lane": r[3]} for r in rows]
    except Exception:
        try:
            rows = conn.execute(
                "SELECT quote_text, source_file, category, lane FROM evidence_quotes WHERE quote_text LIKE ? LIMIT ?",
                (f"%{topic}%", limit)
            ).fetchall()
            results["evidence"] = [{"excerpt": r[0][:200], "source": r[1], "category": r[2], "lane": r[3]} for r in rows]
        except Exception:
            results["evidence"] = []

    # 2. timeline_events (FTS5)
    try:
        rows = conn.execute(
            "SELECT snippet(timeline_fts, 0, '<b>', '</b>', '...', 40) AS excerpt, actors "
            "FROM timeline_fts WHERE timeline_fts MATCH ? ORDER BY rank LIMIT ?",
            (safe_q, limit)
        ).fetchall()
        results["timeline"] = [{"excerpt": r[0], "actors": r[1]} for r in rows]
    except Exception:
        results["timeline"] = []

    # 3. police_reports (LIKE)
    try:
        rows = conn.execute(
            "SELECT filename, allegations, exculpatory FROM police_reports WHERE full_text LIKE ? LIMIT ?",
            (f"%{topic}%", min(limit, 20))
        ).fetchall()
        results["police"] = [{"filename": r[0], "allegations": r[1], "exculpatory": r[2]} for r in rows]
    except Exception:
        results["police"] = []

    # 4. impeachment_matrix
    try:
        rows = conn.execute(
            "SELECT target, category, evidence_summary, impeachment_value FROM impeachment_matrix "
            "WHERE evidence_summary LIKE ? OR quote_text LIKE ? ORDER BY impeachment_value DESC LIMIT ?",
            (f"%{topic}%", f"%{topic}%", min(limit, 20))
        ).fetchall()
        results["impeachment"] = [{"target": r[0], "category": r[1], "summary": r[2], "value": r[3]} for r in rows]
    except Exception:
        results["impeachment"] = []

    # 5. authority_chains_v2
    try:
        rows = conn.execute(
            "SELECT primary_citation, supporting_citation, relationship, lane FROM authority_chains_v2 "
            "WHERE primary_citation LIKE ? OR supporting_citation LIKE ? LIMIT ?",
            (f"%{topic}%", f"%{topic}%", min(limit, 20))
        ).fetchall()
        results["authority"] = [{"primary": r[0], "supporting": r[1], "relationship": r[2], "lane": r[3]} for r in rows]
    except Exception:
        results["authority"] = []

    total = sum(len(v) for v in results.values())
    return {"ok": True, "topic": topic, "total_hits": total, "results": results}


def handle_nexus_argue(req):
    """Argument chain synthesis — evidence + authorities + impeachment for a claim."""
    claim = req.get("claim", "")
    lane = req.get("lane", "")
    limit = min(req.get("limit", 10), 50)
    conn = pool.sqlite
    safe_q = sanitize_fts5(claim)
    chain = {"claim": claim, "evidence": [], "authorities": [], "impeachment": []}

    # Evidence
    try:
        rows = conn.execute(
            "SELECT snippet(evidence_fts, 0, '<b>', '</b>', '...', 40), eq.source_file, eq.lane "
            "FROM evidence_fts JOIN evidence_quotes eq ON eq.id = evidence_fts.rowid "
            "WHERE evidence_fts MATCH ? ORDER BY rank LIMIT ?",
            (safe_q, limit)
        ).fetchall()
        chain["evidence"] = [{"excerpt": r[0], "source": r[1], "lane": r[2]} for r in rows]
    except Exception:
        pass

    # Authorities
    try:
        rows = conn.execute(
            "SELECT primary_citation, supporting_citation, relationship FROM authority_chains_v2 "
            "WHERE primary_citation LIKE ? OR supporting_citation LIKE ? LIMIT ?",
            (f"%{claim}%", f"%{claim}%", limit)
        ).fetchall()
        chain["authorities"] = [{"primary": r[0], "supporting": r[1], "relationship": r[2]} for r in rows]
    except Exception:
        pass

    # Impeachment
    try:
        rows = conn.execute(
            "SELECT target, cross_exam_question, impeachment_value FROM impeachment_matrix "
            "WHERE evidence_summary LIKE ? ORDER BY impeachment_value DESC LIMIT ?",
            (f"%{claim}%", limit)
        ).fetchall()
        chain["impeachment"] = [{"target": r[0], "question": r[1], "value": r[2]} for r in rows]
    except Exception:
        pass

    # Strength score
    e_score = min(len(chain["evidence"]) * 10, 40)
    a_score = min(len(chain["authorities"]) * 15, 40)
    i_score = min(len(chain["impeachment"]) * 10, 20)
    total = e_score + a_score + i_score
    rating = "STRONG" if total >= 70 else "MODERATE" if total >= 40 else "WEAK"
    chain["strength"] = {"score": total, "rating": rating}

    return {"ok": True, **chain}


def handle_nexus_readiness(req):
    """Filing readiness dashboard."""
    conn = pool.sqlite
    lane = req.get("lane", "")
    filings = []

    try:
        tables_check = {
            "evidence_quotes": "SELECT lane, COUNT(*) FROM evidence_quotes GROUP BY lane",
            "authority_chains_v2": "SELECT lane, COUNT(*) FROM authority_chains_v2 WHERE lane IS NOT NULL GROUP BY lane",
            "impeachment_matrix": "SELECT 'ALL', COUNT(*) FROM impeachment_matrix",
        }
        lane_data = {}
        for _tbl, sql in tables_check.items():
            for row in conn.execute(sql).fetchall():
                ln = row[0] or "UNKNOWN"
                lane_data.setdefault(ln, {"evidence": 0, "authority": 0, "impeachment": 0})
                if "evidence" in _tbl:
                    lane_data[ln]["evidence"] = row[1]
                elif "authority" in _tbl:
                    lane_data[ln]["authority"] = row[1]
                elif "impeachment" in _tbl:
                    for k in lane_data:
                        lane_data[k]["impeachment"] = row[1]

        for ln, counts in sorted(lane_data.items()):
            if lane and ln != lane:
                continue
            score = min(counts["evidence"] // 10, 40) + min(counts["authority"] // 5, 40) + min(counts["impeachment"] // 5, 20)
            filings.append({
                "lane": ln,
                "evidence_count": counts["evidence"],
                "authority_count": counts["authority"],
                "impeachment_count": counts["impeachment"],
                "readiness_score": min(score, 100),
            })
    except Exception as e:
        return {"ok": False, "error": str(e)}

    return {"ok": True, "filings": filings}


def handle_nexus_damages(req):
    """Aggregate damages across claims."""
    conn = pool.sqlite
    lane = req.get("lane", "")
    try:
        # Check if damages table exists
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%damage%'").fetchall()]
        if not tables:
            # Hardcoded damages model from case intelligence
            damages = [
                {"category": "Lost parenting time", "conservative": 100000, "aggressive": 500000, "lane": "A"},
                {"category": "False imprisonment", "conservative": 50000, "aggressive": 200000, "lane": "A"},
                {"category": "Lost employment", "conservative": 80000, "aggressive": 160000, "lane": "A"},
                {"category": "Lost housing", "conservative": 40000, "aggressive": 120000, "lane": "B"},
                {"category": "Emotional distress", "conservative": 100000, "aggressive": 500000, "lane": "C"},
                {"category": "Punitive (§1983)", "conservative": 250000, "aggressive": 1000000, "lane": "C"},
            ]
            if lane:
                damages = [d for d in damages if d["lane"] == lane]
            total_low = sum(d["conservative"] for d in damages)
            total_high = sum(d["aggressive"] for d in damages)
            return {"ok": True, "damages": damages, "total_conservative": total_low, "total_aggressive": total_high}

        sql = f"SELECT * FROM {tables[0]}"
        if lane:
            sql += f" WHERE lane = ?"
            rows = conn.execute(sql, (lane,)).fetchall()
        else:
            rows = conn.execute(sql).fetchall()
        columns = [d[0] for d in conn.execute(f"PRAGMA table_info({tables[0]})").fetchall()]
        return {"ok": True, "rows": [dict(zip(columns, r)) for r in rows], "count": len(rows)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def handle_narrative(req):
    """Chronological narrative builder from timeline_events."""
    conn = pool.sqlite
    query = req.get("query", "")
    lane = req.get("lane", "")
    limit = min(req.get("limit", 50), 200)
    safe_q = sanitize_fts5(query)

    events = []
    try:
        if safe_q:
            rows = conn.execute(
                "SELECT event_date, event_description, actors, lane FROM timeline_fts "
                "JOIN timeline_events te ON te.id = timeline_fts.rowid "
                "WHERE timeline_fts MATCH ? ORDER BY te.event_date LIMIT ?",
                (safe_q, limit)
            ).fetchall()
        else:
            sql = "SELECT event_date, event_description, actors, lane FROM timeline_events"
            params = []
            if lane:
                sql += " WHERE lane = ?"
                params.append(lane)
            sql += " ORDER BY event_date DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()
        events = [{"date": r[0], "description": r[1], "actors": r[2], "lane": r[3]} for r in rows]
    except Exception:
        # LIKE fallback
        try:
            rows = conn.execute(
                "SELECT event_date, event_description, actors, lane FROM timeline_events "
                "WHERE event_description LIKE ? ORDER BY event_date LIMIT ?",
                (f"%{query}%", limit)
            ).fetchall()
            events = [{"date": r[0], "description": r[1], "actors": r[2], "lane": r[3]} for r in rows]
        except Exception:
            pass

    return {"ok": True, "events": events, "total": len(events), "lane": lane or "ALL"}


def handle_filing_plan(req):
    """Filing strategy with deadlines."""
    conn = pool.sqlite
    lane = req.get("lane", "")

    filings = []
    try:
        sql = "SELECT * FROM filing_packages"
        if lane:
            sql += " WHERE lane = ?"
            rows = conn.execute(sql, (lane,)).fetchall()
        else:
            rows = conn.execute(sql).fetchall()

        cols = [d[0] for d in conn.execute("PRAGMA table_info(filing_packages)").fetchall()]
        for r in rows:
            filings.append(dict(zip([c[1] for c in conn.execute("PRAGMA table_info(filing_packages)").fetchall()], r)))
    except Exception:
        # Hardcoded filing plan from case matrix
        filings = [
            {"filing": "Emergency Motion to Restore", "lane": "A", "deadline": "FILED 3/25/2026", "court": "14th Circuit", "fee": "$20", "status": "filed"},
            {"filing": "MCR 2.003 Disqualification", "lane": "A", "deadline": "ASAP", "court": "14th Circuit", "fee": "$20", "status": "ready"},
            {"filing": "COA Brief 366810", "lane": "F", "deadline": "Apr 30, 2026", "court": "MI Court of Appeals", "fee": "$375", "status": "ready"},
            {"filing": "MSC Superintending Control", "lane": "E", "deadline": "Strategic", "court": "MI Supreme Court", "fee": "$375", "status": "drafting"},
            {"filing": "Federal §1983", "lane": "C", "deadline": "Strategic", "court": "WDMI", "fee": "$405", "status": "drafting"},
            {"filing": "JTC Complaint", "lane": "E", "deadline": "None", "court": "JTC", "fee": "$0", "status": "ready"},
            {"filing": "PPO Termination", "lane": "D", "deadline": "TBD", "court": "14th Circuit", "fee": "$20", "status": "ready"},
        ]
        if lane:
            filings = [f for f in filings if f.get("lane") == lane]

    return {"ok": True, "filings": filings, "total": len(filings)}


def handle_rules_check(req):
    """Procedural compliance validator."""
    conn = pool.sqlite
    query = req.get("query", "")
    limit = min(req.get("limit", 10), 50)

    rules = []
    try:
        rows = conn.execute(
            "SELECT rule_number, rule_type, title, full_text FROM michigan_rules_extracted "
            "WHERE rule_number LIKE ? OR title LIKE ? OR full_text LIKE ? LIMIT ?",
            (f"%{query}%", f"%{query}%", f"%{query}%", limit)
        ).fetchall()
        rules = [{"rule_number": r[0], "rule_type": r[1], "title": r[2], "full_text": r[3][:600] if r[3] else ""} for r in rows]
    except Exception as e:
        return {"ok": False, "error": str(e)}

    return {"ok": True, "rules": rules, "count": len(rules)}


def handle_adversary(req):
    """Deep adversary profile builder."""
    conn = pool.sqlite
    person = req.get("person", "")
    if not person:
        return {"ok": False, "error": "No person specified"}

    profile = {"person": person, "impeachment_items": [], "contradictions": [], "timeline_events": [], "credibility_score": 0}

    # Impeachment
    try:
        rows = conn.execute(
            "SELECT category, evidence_summary, impeachment_value, cross_exam_question FROM impeachment_matrix "
            "WHERE target LIKE ? ORDER BY impeachment_value DESC LIMIT 20",
            (f"%{person}%",)
        ).fetchall()
        profile["impeachment_items"] = [{"category": r[0], "summary": r[1], "value": r[2], "question": r[3]} for r in rows]
    except Exception:
        pass

    # Contradictions
    try:
        rows = conn.execute(
            "SELECT source_a, source_b, contradiction_text, severity FROM contradiction_map "
            "WHERE source_a LIKE ? OR source_b LIKE ? ORDER BY CASE severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 ELSE 3 END LIMIT 20",
            (f"%{person}%", f"%{person}%")
        ).fetchall()
        profile["contradictions"] = [{"source_a": r[0], "source_b": r[1], "text": r[2], "severity": r[3]} for r in rows]
    except Exception:
        pass

    # Timeline
    try:
        safe_q = sanitize_fts5(person)
        rows = conn.execute(
            "SELECT event_date, event_description FROM timeline_fts "
            "JOIN timeline_events te ON te.id = timeline_fts.rowid "
            "WHERE timeline_fts MATCH ? ORDER BY te.event_date DESC LIMIT 20",
            (safe_q,)
        ).fetchall()
        profile["timeline_events"] = [{"date": r[0], "description": r[1]} for r in rows]
    except Exception:
        pass

    # Credibility score (higher = less credible = more impeachable)
    imp_score = min(len(profile["impeachment_items"]) * 5, 40)
    con_score = min(len(profile["contradictions"]) * 10, 40)
    profile["credibility_score"] = 100 - imp_score - con_score
    profile["weakness_count"] = len(profile["impeachment_items"]) + len(profile["contradictions"])

    return {"ok": True, **profile}


def handle_gap_analysis(req):
    """Missing evidence, claims, and filings detector."""
    conn = pool.sqlite
    lane = req.get("lane", "")

    gaps = {"missing_evidence": [], "weak_authority": [], "unfiled_motions": []}

    # Check evidence density per lane
    try:
        rows = conn.execute(
            "SELECT lane, COUNT(*) as cnt FROM evidence_quotes GROUP BY lane ORDER BY cnt"
        ).fetchall()
        min_threshold = 100
        for r in rows:
            if r[1] < min_threshold and (not lane or r[0] == lane):
                gaps["missing_evidence"].append({"lane": r[0], "count": r[1], "gap": f"Only {r[1]} evidence items (need {min_threshold}+)"})
    except Exception:
        pass

    # Check authority chain completeness
    try:
        rows = conn.execute(
            "SELECT lane, COUNT(DISTINCT primary_citation) as cites FROM authority_chains_v2 WHERE lane IS NOT NULL GROUP BY lane"
        ).fetchall()
        for r in rows:
            if r[1] < 10 and (not lane or r[0] == lane):
                gaps["weak_authority"].append({"lane": r[0], "citations": r[1], "gap": f"Only {r[1]} unique citations"})
    except Exception:
        pass

    return {"ok": True, "gaps": gaps}


def handle_cross_connect(req):
    """Cross-lane intelligence fusion."""
    topic = req.get("topic", "")
    conn = pool.sqlite
    connections = {}

    safe_q = sanitize_fts5(topic)

    # Search evidence across all lanes
    try:
        rows = conn.execute(
            "SELECT eq.lane, COUNT(*) FROM evidence_fts "
            "JOIN evidence_quotes eq ON eq.id = evidence_fts.rowid "
            "WHERE evidence_fts MATCH ? GROUP BY eq.lane",
            (safe_q,)
        ).fetchall()
        connections["evidence_by_lane"] = {r[0]: r[1] for r in rows}
    except Exception:
        try:
            rows = conn.execute(
                "SELECT lane, COUNT(*) FROM evidence_quotes WHERE quote_text LIKE ? GROUP BY lane",
                (f"%{topic}%",)
            ).fetchall()
            connections["evidence_by_lane"] = {r[0]: r[1] for r in rows}
        except Exception:
            connections["evidence_by_lane"] = {}

    # Authority cross-references
    try:
        rows = conn.execute(
            "SELECT lane, COUNT(*) FROM authority_chains_v2 WHERE primary_citation LIKE ? OR supporting_citation LIKE ? GROUP BY lane",
            (f"%{topic}%", f"%{topic}%")
        ).fetchall()
        connections["authority_by_lane"] = {r[0]: r[1] for r in rows}
    except Exception:
        connections["authority_by_lane"] = {}

    total = sum(connections.get("evidence_by_lane", {}).values()) + sum(connections.get("authority_by_lane", {}).values())
    lanes_touched = set(list(connections.get("evidence_by_lane", {}).keys()) + list(connections.get("authority_by_lane", {}).keys()))
    connections["lanes_touched"] = sorted(lanes_touched)
    connections["total_hits"] = total

    return {"ok": True, "topic": topic, "connections": connections}


def handle_judicial_intel(req):
    """Judicial intelligence findings."""
    conn = pool.sqlite
    judge = req.get("judge", "")

    intel = {"violations": [], "berry_intel": [], "patterns": {}}

    # Judicial violations
    try:
        sql = "SELECT * FROM judicial_violations"
        params = []
        if judge:
            sql += " WHERE judge LIKE ? OR description LIKE ?"
            params.extend([f"%{judge}%", f"%{judge}%"])
        sql += " LIMIT 50"
        cur = conn.execute(sql, params)
        cols = [d[0] for d in cur.description]
        intel["violations"] = [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception:
        pass

    # Berry-McNeill intelligence
    try:
        sql = "SELECT * FROM berry_mcneill_intelligence"
        if judge:
            sql += f" WHERE intelligence LIKE '%{judge}%' OR category LIKE '%{judge}%'"
        sql += " LIMIT 30"
        cur = conn.execute(sql)
        cols = [d[0] for d in cur.description]
        intel["berry_intel"] = [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception:
        pass

    # Pattern summary
    try:
        rows = conn.execute(
            "SELECT violation_type, COUNT(*) FROM judicial_violations GROUP BY violation_type ORDER BY COUNT(*) DESC LIMIT 10"
        ).fetchall()
        intel["patterns"] = {r[0]: r[1] for r in rows}
    except Exception:
        pass

    intel["total_violations"] = len(intel["violations"])
    return {"ok": True, **intel}


def handle_timeline_search(req):
    """Timeline events search."""
    conn = pool.sqlite
    query = req.get("query", "")
    date_from = req.get("date_from", "")
    date_to = req.get("date_to", "")
    actor = req.get("actor", "")
    limit = min(req.get("limit", 30), 200)

    conditions, params = [], []
    if query:
        safe_q = sanitize_fts5(query)
        try:
            rows = conn.execute(
                "SELECT te.event_date, te.event_description, te.actors, te.lane "
                "FROM timeline_fts JOIN timeline_events te ON te.id = timeline_fts.rowid "
                "WHERE timeline_fts MATCH ? ORDER BY te.event_date LIMIT ?",
                (safe_q, limit)
            ).fetchall()
            return {"ok": True, "events": [{"date": r[0], "description": r[1], "actors": r[2], "lane": r[3]} for r in rows], "count": len(rows)}
        except Exception:
            conditions.append("event_description LIKE ?")
            params.append(f"%{query}%")

    if date_from:
        conditions.append("event_date >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("event_date <= ?")
        params.append(date_to)
    if actor:
        conditions.append("actors LIKE ?")
        params.append(f"%{actor}%")

    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"SELECT event_date, event_description, actors, lane FROM timeline_events{where} ORDER BY event_date DESC LIMIT ?"
    params.append(limit)

    try:
        rows = conn.execute(sql, params).fetchall()
        return {"ok": True, "events": [{"date": r[0], "description": r[1], "actors": r[2], "lane": r[3]} for r in rows], "count": len(rows)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def handle_case_context(req):
    """Comprehensive context for active cases."""
    conn = pool.sqlite
    case_id = req.get("case_id", "")

    context = {"stats": {}, "filings": [], "recent_timeline": []}

    # Stats
    for table in ["evidence_quotes", "authority_chains_v2", "timeline_events", "impeachment_matrix", "contradiction_map", "judicial_violations"]:
        try:
            context["stats"][table] = conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]
        except Exception:
            context["stats"][table] = -1

    # Separation counter
    sep_date = date(2025, 7, 29)
    context["separation_days"] = (date.today() - sep_date).days

    # Recent timeline
    try:
        rows = conn.execute(
            "SELECT event_date, event_description, lane FROM timeline_events ORDER BY event_date DESC LIMIT 10"
        ).fetchall()
        context["recent_timeline"] = [{"date": r[0], "description": r[1], "lane": r[2]} for r in rows]
    except Exception:
        pass

    return {"ok": True, **context}


def handle_filing_status(req):
    """Filing package status."""
    lane = req.get("lane", "")
    conn = pool.sqlite

    try:
        sql = "SELECT * FROM filing_packages WHERE lane = ?"
        cur = conn.execute(sql, (lane,))
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        return {"ok": True, "filings": rows, "count": len(rows)}
    except Exception:
        # Fallback to hardcoded data
        packages = {
            "F1": {"name": "MSC Petition", "status": "complete"},
            "F3": {"name": "MCR 2.003 Disqualification", "status": "complete"},
            "F4": {"name": "Federal §1983", "status": "complete"},
            "F5": {"name": "MSC Original Action", "status": "complete"},
            "F6": {"name": "JTC Complaint", "status": "32 exhibits missing"},
            "F8": {"name": "PPO Termination", "status": "complete"},
            "F9": {"name": "COA Brief", "status": "complete"},
            "F10": {"name": "COA Emergency", "status": "complete"},
        }
        if lane in packages:
            return {"ok": True, "filings": [packages[lane]], "count": 1}
        return {"ok": True, "filings": list(packages.values()), "count": len(packages)}


def handle_deadlines(req):
    """Check litigation deadlines."""
    conn = pool.sqlite
    days_ahead = req.get("days_ahead", 30)

    deadlines = []
    try:
        rows = conn.execute(
            "SELECT * FROM deadlines WHERE due_date <= date('now', '+' || ? || ' days') ORDER BY due_date",
            (days_ahead,)
        ).fetchall()
        cols = [d[0] for d in conn.execute("PRAGMA table_info(deadlines)").fetchall()]
        col_names = [c[1] for c in conn.execute("PRAGMA table_info(deadlines)").fetchall()]
        deadlines = [dict(zip(col_names, r)) for r in rows]
    except Exception:
        # Hardcoded critical deadlines
        deadlines = [
            {"filing": "COA Brief 366810", "due_date": "2026-04-30", "court": "MI Court of Appeals", "urgency": "high"},
            {"filing": "Criminal Trial", "due_date": "2026-04-07", "court": "60th District", "urgency": "critical"},
        ]

    # Color-code urgency
    today = date.today()
    for d in deadlines:
        try:
            due = datetime.strptime(d.get("due_date", ""), "%Y-%m-%d").date()
            days_left = (due - today).days
            if days_left < 0:
                d["color"] = "🔴 OVERDUE"
            elif days_left <= 3:
                d["color"] = "🟠 CRITICAL"
            elif days_left <= 7:
                d["color"] = "🟡 URGENT"
            else:
                d["color"] = "🟢 OK"
            d["days_left"] = days_left
        except Exception:
            d["color"] = "⚪ UNKNOWN"

    return {"ok": True, "deadlines": deadlines, "count": len(deadlines)}




# ══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS (shared by ported MCP handlers)
# ══════════════════════════════════════════════════════════════════════════


def _table_exists(table_name):
    """Check if a table exists in the database."""
    try:
        row = pool.sqlite.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        ).fetchone()
        return row is not None
    except Exception:
        return False


def _count_table(conn, table_name):
    """Count rows in a table safely."""
    if not _table_exists(table_name):
        return 0
    try:
        row = conn.execute(f"SELECT COUNT(*) FROM [{table_name}]").fetchone()
        return row[0] if row else 0
    except Exception:
        return 0


def _paginated_query(conn, sql, params, limit=20, offset=0):
    """Execute a paginated query returning column names and row dicts."""
    full_sql = f"{sql} LIMIT ? OFFSET ?"
    full_params = list(params) + [limit, offset]
    cur = conn.execute(full_sql, full_params)
    columns = [desc[0] for desc in cur.description] if cur.description else []
    rows = [dict(zip(columns, r)) for r in cur.fetchall()]
    return columns, rows


# ══════════════════════════════════════════════════════════════════════════
# DOCUMENT MANAGEMENT HANDLERS
# ══════════════════════════════════════════════════════════════════════════


def handle_list_documents(req):
    """List documents in the knowledge base with metadata."""
    conn = pool.sqlite
    if not _table_exists("documents"):
        return {"ok": True, "documents": [], "count": 0, "note": "documents table not found"}

    limit = min(req.get("limit", 20), 100)
    offset = req.get("offset", 0)
    name_filter = req.get("name_filter")

    cols_info = conn.execute("PRAGMA table_info(documents)").fetchall()
    col_names = {c[1] for c in cols_info}

    select_cols = []
    for c in ["id", "file_name", "title", "file_path", "file_size_bytes",
              "page_count", "created_at", "doc_type", "content_preview"]:
        if c in col_names:
            select_cols.append(c)
    if "id" not in col_names:
        select_cols.insert(0, "rowid AS id")
    if not select_cols:
        select_cols = ["*"]

    sql = f"SELECT {', '.join(select_cols)} FROM documents"
    params = []
    if name_filter:
        filter_col = next((c for c in ["file_name", "title", "file_path"] if c in col_names), None)
        if filter_col:
            sql += f" WHERE {filter_col} LIKE ?"
            params.append(f"%{name_filter}%")

    sql += " ORDER BY rowid DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    try:
        cur = conn.execute(sql, params)
        columns = [desc[0] for desc in cur.description] if cur.description else []
        rows = [dict(zip(columns, r)) for r in cur.fetchall()]
        total = _count_table(conn, "documents")
        return {"ok": True, "documents": rows, "count": len(rows), "total": total}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def handle_get_document(req):
    """Retrieve full extracted text of a document by ID."""
    conn = pool.sqlite
    doc_id = req.get("document_id")
    if not doc_id:
        return {"ok": False, "error": "document_id required"}

    page_numbers = req.get("page_numbers")
    doc_meta = {}

    if _table_exists("documents"):
        try:
            doc = conn.execute(
                "SELECT * FROM documents WHERE rowid = ?", (doc_id,)
            ).fetchone()
            if doc:
                doc_meta = dict(doc)
        except Exception:
            pass

    pages = []
    if _table_exists("pages"):
        try:
            cols_info = conn.execute("PRAGMA table_info(pages)").fetchall()
            pcols = {c[1] for c in cols_info}
            doc_col = next((c for c in ["document_id", "doc_id"] if c in pcols), None)
            text_col = next((c for c in ["text", "content", "page_text"] if c in pcols), None)
            page_col = next((c for c in ["page_number", "page_num", "page"] if c in pcols), None)

            if doc_col and text_col:
                if page_numbers and page_col:
                    ph = ",".join("?" * len(page_numbers))
                    sql = f"SELECT {page_col}, {text_col} FROM pages WHERE {doc_col} = ? AND {page_col} IN ({ph}) ORDER BY {page_col}"
                    cur = conn.execute(sql, [doc_id] + list(page_numbers))
                else:
                    order = f"ORDER BY {page_col}" if page_col else ""
                    sql = f"SELECT {page_col or 'rowid'} AS page_number, {text_col} FROM pages WHERE {doc_col} = ? {order}"
                    cur = conn.execute(sql, (doc_id,))
                pages = [{"page": r[0], "text": r[1]} for r in cur.fetchall()]
        except Exception as e:
            return {"ok": False, "error": f"Error reading pages: {e}"}

    return {"ok": True, "document": doc_meta, "pages": pages, "page_count": len(pages)}


def handle_search_documents(req):
    """Full-text search across all ingested PDF content."""
    conn = pool.sqlite
    query = req.get("query", "").strip()
    if not query:
        return {"ok": False, "error": "query required"}

    limit = min(req.get("limit", 20), 100)
    offset = req.get("offset", 0)
    clean = sanitize_fts5(query)

    if _table_exists("pages_fts") and _table_exists("pages"):
        try:
            cur = conn.execute(
                """SELECT p.document_id, p.page_number,
                          snippet(pages_fts, 0, '>>>', '<<<', '...', 60) AS snippet
                   FROM pages_fts
                   JOIN pages p ON p.rowid = pages_fts.rowid
                   WHERE pages_fts MATCH ?
                   ORDER BY rank LIMIT ? OFFSET ?""",
                (clean, limit, offset)
            )
            columns = [desc[0] for desc in cur.description]
            rows = [dict(zip(columns, r)) for r in cur.fetchall()]
            return {"ok": True, "results": rows, "count": len(rows), "engine": "fts5"}
        except Exception:
            pass

    if _table_exists("pages"):
        try:
            cur = conn.execute(
                """SELECT document_id, page_number,
                          substr(text, max(1, instr(lower(text), lower(?)) - 60), 150) AS snippet
                   FROM pages WHERE text LIKE ?
                   LIMIT ? OFFSET ?""",
                (query, f"%{query}%", limit, offset)
            )
            columns = [desc[0] for desc in cur.description]
            rows = [dict(zip(columns, r)) for r in cur.fetchall()]
            return {"ok": True, "results": rows, "count": len(rows), "engine": "like"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    return {"ok": True, "results": [], "count": 0, "note": "No searchable content tables found"}


def handle_ingest_pdf(_req):
    """Ingest a PDF. BLOCKED: daemon is read-only."""
    return {"ok": False, "error": "BLOCKED: Daemon is READ-ONLY. Use exec_python with a dedicated ingest script."}


def handle_bulk_ingest(_req):
    """Bulk ingest PDFs. BLOCKED: daemon is read-only."""
    return {"ok": False, "error": "BLOCKED: Daemon is READ-ONLY. Use exec_python with a dedicated ingest script."}


# ══════════════════════════════════════════════════════════════════════════
# KNOWLEDGE GRAPH & RULES HANDLERS
# ══════════════════════════════════════════════════════════════════════════


def handle_lookup_rule(req):
    """Look up Michigan Court Rules (MCR/MCL) by citation or keyword."""
    conn = pool.sqlite
    query = req.get("query", "").strip()
    if not query:
        return {"ok": False, "error": "query required"}

    limit = min(req.get("limit", 20), 100)
    offset = req.get("offset", 0)

    if not _table_exists("michigan_rules_extracted"):
        return {"ok": True, "rules": [], "count": 0, "note": "michigan_rules_extracted not found"}

    try:
        cur = conn.execute(
            """SELECT rule_number, rule_type, title, full_text
               FROM michigan_rules_extracted
               WHERE rule_number LIKE ?
               LIMIT ? OFFSET ?""",
            (f"%{query}%", limit, offset)
        )
        columns = [desc[0] for desc in cur.description]
        results = [dict(zip(columns, r)) for r in cur.fetchall()]
        if results:
            return {"ok": True, "rules": results, "count": len(results), "match": "citation"}
    except Exception:
        pass

    try:
        cur = conn.execute(
            """SELECT rule_number, rule_type, title,
                      substr(full_text, 1, 500) AS excerpt
               FROM michigan_rules_extracted
               WHERE full_text LIKE ? OR title LIKE ?
               LIMIT ? OFFSET ?""",
            (f"%{query}%", f"%{query}%", limit, offset)
        )
        columns = [desc[0] for desc in cur.description]
        results = [dict(zip(columns, r)) for r in cur.fetchall()]
    except Exception as e:
        return {"ok": False, "error": str(e)}

    return {"ok": True, "rules": results, "count": len(results), "match": "text"}


def handle_query_graph(req):
    """Search the knowledge graph for authorities, case law, forms, procedures."""
    conn = pool.sqlite
    query = req.get("query", "").strip()
    if not query:
        return {"ok": False, "error": "query required"}

    limit = min(req.get("limit", 20), 100)
    node_type = req.get("node_type")
    graph_source = req.get("graph_source")
    results = []

    for table in ["knowledge_graph", "graph_nodes", "authority_graph"]:
        if not _table_exists(table):
            continue

        cols_info = conn.execute(f"PRAGMA table_info([{table}])").fetchall()
        col_names = {c[1] for c in cols_info}

        where_parts = []
        params = []
        label_col = next((c for c in ["label", "name", "node_id"] if c in col_names), None)
        if label_col:
            search_expr = f"({label_col} LIKE ?"
            params.append(f"%{query}%")
            if "node_id" in col_names and label_col != "node_id":
                search_expr += " OR node_id LIKE ?"
                params.append(f"%{query}%")
            search_expr += ")"
            where_parts.append(search_expr)

        if node_type and "node_type" in col_names:
            where_parts.append("node_type = ?")
            params.append(node_type)
        if graph_source and "graph_source" in col_names:
            where_parts.append("graph_source = ?")
            params.append(graph_source)

        if not where_parts:
            continue

        try:
            params.append(limit)
            cur = conn.execute(
                f"SELECT * FROM [{table}] WHERE {' AND '.join(where_parts)} LIMIT ?", params
            )
            columns = [desc[0] for desc in cur.description]
            rows = [dict(zip(columns, r)) for r in cur.fetchall()]
            results.extend(rows)
        except Exception:
            continue

    return {"ok": True, "nodes": results[:limit], "count": min(len(results), limit)}


def handle_lookup_authority(req):
    """Look up specific legal authorities (case law, statutes, court rules)."""
    conn = pool.sqlite
    query = req.get("query", "").strip()
    if not query:
        return {"ok": False, "error": "query required"}

    limit = min(req.get("limit", 20), 100)
    node_type = req.get("node_type")
    results = []

    if _table_exists("authority_chains_v2"):
        try:
            where = "primary_citation LIKE ? OR supporting_citation LIKE ?"
            params = [f"%{query}%", f"%{query}%"]
            if node_type:
                where += " AND source_type = ?"
                params.append(node_type)
            params.append(limit)
            cur = conn.execute(
                f"""SELECT primary_citation, supporting_citation, relationship,
                           source_document, source_type, lane
                    FROM authority_chains_v2 WHERE {where} LIMIT ?""", params
            )
            columns = [desc[0] for desc in cur.description]
            results.extend([dict(zip(columns, r)) for r in cur.fetchall()])
        except Exception:
            pass

    if _table_exists("master_citations") and len(results) < limit:
        try:
            cols_info = conn.execute("PRAGMA table_info(master_citations)").fetchall()
            cn = {c[1] for c in cols_info}
            cit_col = next((c for c in ["citation", "cite", "reference"] if c in cn), None)
            if cit_col:
                cur = conn.execute(
                    f"SELECT * FROM master_citations WHERE [{cit_col}] LIKE ? LIMIT ?",
                    (f"%{query}%", limit - len(results))
                )
                columns = [desc[0] for desc in cur.description]
                results.extend([dict(zip(columns, r)) for r in cur.fetchall()])
        except Exception:
            pass

    return {"ok": True, "authorities": results[:limit], "count": min(len(results), limit)}


# ══════════════════════════════════════════════════════════════════════════
# INTELLIGENCE HANDLERS
# ══════════════════════════════════════════════════════════════════════════


def handle_assess_risk(req):
    """Assess litigation risks from the risk event taxonomy."""
    conn = pool.sqlite
    severity_min = req.get("severity_min", 0)
    risk_class = req.get("risk_class")
    results = []

    for table in ["risk_events", "litigation_risks", "risk_taxonomy"]:
        if not _table_exists(table):
            continue

        cols_info = conn.execute(f"PRAGMA table_info([{table}])").fetchall()
        col_names = {c[1] for c in cols_info}

        where_parts = []
        params = []

        sev_col = next((c for c in ["severity", "severity_score", "risk_score"] if c in col_names), None)
        if sev_col and severity_min > 0:
            where_parts.append(f"{sev_col} >= ?")
            params.append(severity_min)

        class_col = next((c for c in ["risk_class", "classification", "category"] if c in col_names), None)
        if class_col and risk_class:
            where_parts.append(f"{class_col} = ?")
            params.append(risk_class)

        where = " AND ".join(where_parts) if where_parts else "1=1"
        order = f"ORDER BY {sev_col} DESC" if sev_col else "ORDER BY rowid DESC"

        try:
            cur = conn.execute(f"SELECT * FROM [{table}] WHERE {where} {order} LIMIT 50", params)
            columns = [desc[0] for desc in cur.description]
            results = [dict(zip(columns, r)) for r in cur.fetchall()]
        except Exception:
            continue
        break

    return {"ok": True, "risks": results, "count": len(results)}


def handle_get_vehicle_map(req):
    """Map relief type to litigation vehicle, authority chain, and deadlines."""
    conn = pool.sqlite
    relief_type = req.get("relief_type", "").strip()
    if not relief_type:
        return {"ok": False, "error": "relief_type required"}

    results = []
    if _table_exists("md_sections_fts") and _table_exists("md_sections"):
        clean = sanitize_fts5(relief_type)
        if clean:
            try:
                cur = conn.execute(
                    """SELECT ms.file_path, ms.heading, ms.content
                       FROM md_sections_fts
                       JOIN md_sections ms ON ms.rowid = md_sections_fts.rowid
                       WHERE md_sections_fts MATCH ?
                       ORDER BY rank LIMIT 20""", (clean,)
                )
                for row in cur.fetchall():
                    text = (row[2] or "").lower()
                    if any(kw in text for kw in ["vehicle", "authority", "element", "deadline", "relief"]):
                        results.append({"file": row[0], "heading": row[1], "excerpt": (row[2] or "")[:500]})
            except Exception:
                pass

    if not results and _table_exists("md_sections"):
        try:
            cur = conn.execute(
                """SELECT file_path, heading, substr(content, 1, 500) AS excerpt
                   FROM md_sections
                   WHERE content LIKE ?
                     AND (content LIKE '%vehicle%' OR content LIKE '%authority%' OR content LIKE '%deadline%')
                   LIMIT 20""", (f"%{relief_type}%",)
            )
            results = [{"file": r[0], "heading": r[1], "excerpt": r[2]} for r in cur.fetchall()]
        except Exception:
            pass

    return {"ok": True, "vehicle_map": results, "count": len(results)}


def handle_case_health(_req):
    """Case health dashboard — evidence, harms, impeachment, contradictions, deadlines."""
    conn = pool.sqlite
    health = {}
    for table, key in [
        ("evidence_quotes", "evidence_count"),
        ("timeline_events", "timeline_count"),
        ("impeachment_matrix", "impeachment_count"),
        ("contradiction_map", "contradiction_count"),
        ("judicial_violations", "judicial_violation_count"),
        ("authority_chains_v2", "authority_count"),
        ("police_reports", "police_report_count"),
        ("deadlines", "deadline_count"),
        ("filing_packages", "filing_count"),
    ]:
        health[key] = _count_table(conn, table)
    health["separation_days"] = (date.today() - date(2025, 7, 29)).days
    return {"ok": True, "health": health}


def handle_adversary_threats(req):
    """Ranked adversary threat matrix with harm counts."""
    conn = pool.sqlite
    limit = min(req.get("limit", 20), 200)

    if not _table_exists("impeachment_matrix"):
        return {"ok": True, "threats": [], "count": 0, "note": "impeachment_matrix not found"}

    cols_info = conn.execute("PRAGMA table_info(impeachment_matrix)").fetchall()
    col_names = {c[1] for c in cols_info}
    target_col = next((c for c in ["target", "actor", "person", "witness"] if c in col_names), None)
    results = []

    if target_col:
        try:
            cur = conn.execute(
                f"""SELECT {target_col} AS adversary,
                           COUNT(*) AS harm_count,
                           COUNT(DISTINCT category) AS category_spread
                    FROM impeachment_matrix
                    GROUP BY {target_col}
                    ORDER BY harm_count DESC LIMIT ?""", (limit,)
            )
            columns = [desc[0] for desc in cur.description]
            results = [dict(zip(columns, r)) for r in cur.fetchall()]
        except Exception:
            pass

    return {"ok": True, "threats": results, "count": len(results)}


def handle_filing_pipeline(_req):
    """Filing pipeline — every action with phase, readiness, risk score, gaps."""
    conn = pool.sqlite

    for table in ["filing_packages", "filing_readiness"]:
        if _table_exists(table):
            try:
                cur = conn.execute(f"SELECT * FROM [{table}] ORDER BY rowid")
                columns = [desc[0] for desc in cur.description]
                results = [dict(zip(columns, r)) for r in cur.fetchall()]
                return {"ok": True, "pipeline": results, "count": len(results), "source": table}
            except Exception:
                continue

    return {"ok": True, "pipeline": [], "count": 0, "note": "No filing pipeline table found"}


def handle_get_subagent_spec(req):
    """Retrieve the specification for a SUPERPIN sub-agent."""
    conn = pool.sqlite
    agent_name = req.get("agent_name", "").strip()
    if not agent_name:
        return {"ok": False, "error": "agent_name required"}

    results = []
    if _table_exists("md_sections_fts") and _table_exists("md_sections"):
        clean = sanitize_fts5(agent_name)
        if clean:
            try:
                cur = conn.execute(
                    """SELECT ms.file_path, ms.heading, ms.content
                       FROM md_sections_fts
                       JOIN md_sections ms ON ms.rowid = md_sections_fts.rowid
                       WHERE md_sections_fts MATCH ?
                       ORDER BY rank LIMIT 10""", (clean,)
                )
                for row in cur.fetchall():
                    text = row[2] or ""
                    if "agent" in text.lower() or agent_name.lower() in text.lower():
                        results.append({"file": row[0], "heading": row[1], "excerpt": text[:1000]})
            except Exception:
                pass

    if not results and _table_exists("md_sections"):
        try:
            cur = conn.execute(
                """SELECT file_path, heading, substr(content, 1, 1000) AS excerpt
                   FROM md_sections WHERE content LIKE ? LIMIT 10""",
                (f"%{agent_name}%",)
            )
            results = [{"file": r[0], "heading": r[1], "excerpt": r[2]} for r in cur.fetchall()]
        except Exception:
            pass

    return {"ok": True, "agent_spec": results, "count": len(results)}


# ══════════════════════════════════════════════════════════════════════════
# EVOLUTION PIPELINE HANDLERS
# ══════════════════════════════════════════════════════════════════════════


def handle_evolution_stats(_req):
    """Evolution coverage statistics dashboard."""
    conn = pool.sqlite
    stats = {
        "md_sections": _count_table(conn, "md_sections"),
        "md_cross_refs": _count_table(conn, "md_cross_refs"),
    }

    if _table_exists("pdf_sections"):
        stats["pdf_sections"] = _count_table(conn, "pdf_sections")

    if _table_exists("md_sections"):
        try:
            cur = conn.execute(
                """SELECT
                       SUM(CASE WHEN file_path LIKE '%.md' THEN 1 ELSE 0 END) AS md_count,
                       SUM(CASE WHEN file_path LIKE '%.txt' THEN 1 ELSE 0 END) AS txt_count,
                       SUM(CASE WHEN file_path LIKE '%.pdf' THEN 1 ELSE 0 END) AS pdf_count,
                       COUNT(DISTINCT file_path) AS files_evolved
                   FROM md_sections"""
            )
            row = cur.fetchone()
            if row:
                stats.update({"md_files": row[0] or 0, "txt_files": row[1] or 0,
                              "pdf_files": row[2] or 0, "files_evolved": row[3] or 0})
        except Exception:
            pass

    if _table_exists("md_cross_refs"):
        try:
            cur = conn.execute(
                "SELECT ref_type, COUNT(*) AS cnt FROM md_cross_refs GROUP BY ref_type ORDER BY cnt DESC"
            )
            stats["cross_ref_types"] = [{"type": r[0], "count": r[1]} for r in cur.fetchall()]
        except Exception:
            pass

    return {"ok": True, "evolution": stats}


def handle_search_evolved(req):
    """FTS5 search across all evolved content (md, txt, pdf sections)."""
    conn = pool.sqlite
    query = req.get("query", "").strip()
    if not query:
        return {"ok": False, "error": "query required"}

    limit = min(req.get("limit", 20), 100)
    source_type = req.get("source_type")
    clean = sanitize_fts5(query)

    if _table_exists("md_sections_fts") and _table_exists("md_sections"):
        try:
            fts_where = ""
            params = [clean]
            if source_type:
                fts_where = " AND ms.file_path LIKE ?"
                params.append(f"%.{source_type}")
            params.append(limit)

            cur = conn.execute(
                f"""SELECT ms.file_path, ms.heading,
                           snippet(md_sections_fts, 0, '>>>', '<<<', '...', 60) AS snippet
                    FROM md_sections_fts
                    JOIN md_sections ms ON ms.rowid = md_sections_fts.rowid
                    WHERE md_sections_fts MATCH ?{fts_where}
                    ORDER BY rank LIMIT ?""", params
            )
            columns = [desc[0] for desc in cur.description]
            rows = [dict(zip(columns, r)) for r in cur.fetchall()]
            return {"ok": True, "results": rows, "count": len(rows), "engine": "fts5"}
        except Exception:
            pass

    if _table_exists("md_sections"):
        try:
            like_where = ""
            params = [query, f"%{query}%"]
            if source_type:
                like_where = " AND file_path LIKE ?"
                params.append(f"%.{source_type}")
            params.append(limit)

            cur = conn.execute(
                f"""SELECT file_path, heading,
                           substr(content, max(1, instr(lower(content), lower(?)) - 60), 150) AS snippet
                    FROM md_sections WHERE content LIKE ?{like_where}
                    LIMIT ?""", params
            )
            columns = [desc[0] for desc in cur.description]
            rows = [dict(zip(columns, r)) for r in cur.fetchall()]
            return {"ok": True, "results": rows, "count": len(rows), "engine": "like"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    return {"ok": True, "results": [], "count": 0, "note": "No evolved content tables found"}


def handle_cross_refs(req):
    """Query the cross-reference network for matching references."""
    conn = pool.sqlite
    query = req.get("query", "").strip()
    if not query:
        return {"ok": False, "error": "query required"}

    limit = min(req.get("limit", 50), 200)
    ref_type = req.get("ref_type")

    if not _table_exists("md_cross_refs"):
        return {"ok": True, "cross_refs": [], "count": 0, "note": "md_cross_refs not found"}

    cols_info = conn.execute("PRAGMA table_info(md_cross_refs)").fetchall()
    col_names = {c[1] for c in cols_info}
    val_col = next((c for c in ["ref_value", "value", "reference"] if c in col_names), None)
    type_col = next((c for c in ["ref_type", "type"] if c in col_names), None)
    sec_col = next((c for c in ["section_id", "source_section"] if c in col_names), None)
    file_col = next((c for c in ["file_path", "source_file"] if c in col_names), None)

    select_parts = []
    if type_col: select_parts.append(type_col)
    if val_col: select_parts.append(val_col)
    if sec_col: select_parts.append(sec_col)
    if file_col: select_parts.append(file_col)
    if not select_parts:
        select_parts = ["*"]

    where_parts = []
    params = []
    if val_col:
        where_parts.append(f"{val_col} LIKE ?")
        params.append(f"%{query}%")
    if ref_type and type_col:
        where_parts.append(f"{type_col} = ?")
        params.append(ref_type)

    if not where_parts:
        return {"ok": True, "cross_refs": [], "count": 0}

    params.append(limit)
    try:
        cur = conn.execute(
            f"SELECT {', '.join(select_parts)} FROM md_cross_refs WHERE {' AND '.join(where_parts)} LIMIT ?",
            params
        )
        columns = [desc[0] for desc in cur.description]
        rows = [dict(zip(columns, r)) for r in cur.fetchall()]
        return {"ok": True, "cross_refs": rows, "count": len(rows)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def handle_convergence_status(_req):
    """Check convergence status of the knowledge base."""
    conn = pool.sqlite
    status = {"converged": False, "quality_score": 0, "core_tables": {}}

    for t in ["evidence_quotes", "authority_chains_v2", "michigan_rules_extracted",
              "timeline_events", "md_sections", "md_cross_refs"]:
        status["core_tables"][t] = _count_table(conn, t)

    if _table_exists("convergence_domains"):
        try:
            cur = conn.execute(
                "SELECT status, COUNT(*) AS cnt FROM convergence_domains GROUP BY status"
            )
            status["domain_status"] = {r[0]: r[1] for r in cur.fetchall()}
        except Exception:
            pass

    if _table_exists("convergence_waves"):
        try:
            cur = conn.execute(
                "SELECT wave_id, wave_name, status FROM convergence_waves WHERE status != 'COMPLETE' ORDER BY wave_number LIMIT 5"
            )
            status["pending_waves"] = [{"wave_id": r[0], "name": r[1], "status": r[2]} for r in cur.fetchall()]
        except Exception:
            pass

    total = sum(status["core_tables"].values())
    if total > 500000:
        status["quality_score"] = 90
    elif total > 100000:
        status["quality_score"] = 70
    elif total > 10000:
        status["quality_score"] = 50
    else:
        status["quality_score"] = 30
    status["converged"] = status["quality_score"] >= 80

    return {"ok": True, "convergence": status}


# ══════════════════════════════════════════════════════════════════════════
# SYSTEM & MASTER DATA HANDLERS
# ══════════════════════════════════════════════════════════════════════════


def handle_stats_extended(_req):
    """Extended stats including graphs, rules, risk data, and DB size."""
    conn = pool.sqlite
    stats = {}
    for t in STATS_TABLES:
        stats[t] = _count_table(conn, t)

    for t in ["knowledge_graph", "graph_nodes", "risk_events", "convergence_domains",
              "legal_theories", "bates_registry", "filing_readiness"]:
        if _table_exists(t):
            stats[t] = _count_table(conn, t)

    try:
        stats["db_size_mb"] = round(os.path.getsize(DB_PATH) / (1024 * 1024), 1)
    except OSError:
        stats["db_size_mb"] = None

    return {"ok": True, "stats": stats}


def handle_self_test(_req):
    """Run diagnostic self-tests on the litigation database."""
    conn = pool.sqlite
    tests = []

    try:
        conn.execute("SELECT 1")
        tests.append({"test": "db_connectivity", "status": "PASS"})
    except Exception as e:
        tests.append({"test": "db_connectivity", "status": "FAIL", "error": str(e)})

    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()]
        tests.append({"test": "schema_presence", "status": "PASS", "table_count": len(tables)})
    except Exception as e:
        tests.append({"test": "schema_presence", "status": "FAIL", "error": str(e)})

    if _table_exists("evidence_fts"):
        try:
            conn.execute("SELECT * FROM evidence_fts WHERE evidence_fts MATCH 'test' LIMIT 1")
            tests.append({"test": "fts5_roundtrip", "status": "PASS"})
        except Exception as e:
            tests.append({"test": "fts5_roundtrip", "status": "FAIL", "error": str(e)})
    else:
        tests.append({"test": "fts5_roundtrip", "status": "SKIP", "reason": "evidence_fts not found"})

    for t in ["evidence_quotes", "authority_chains_v2", "timeline_events"]:
        count = _count_table(conn, t)
        tests.append({"test": f"table_{t}", "status": "PASS" if count > 0 else "WARN", "count": count})

    tests.append({
        "test": "duckdb",
        "status": "PASS" if (_HAS_DUCKDB and pool.duck) else "SKIP",
        **({} if (_HAS_DUCKDB and pool.duck) else {"reason": "DuckDB not available"})
    })
    tests.append({
        "test": "lancedb",
        "status": "PASS" if (_HAS_LANCEDB and pool.lance_table) else "SKIP",
        **({} if (_HAS_LANCEDB and pool.lance_table) else {"reason": "LanceDB not available"})
    })

    all_pass = all(t["status"] in ("PASS", "SKIP") for t in tests)
    return {"ok": True, "tests": tests, "all_pass": all_pass}


def handle_ingest_csv(_req):
    """Ingest master CSV datasets. BLOCKED: daemon is read-only."""
    return {"ok": False, "error": "BLOCKED: Daemon is READ-ONLY. Use exec_python with a dedicated CSV ingest script."}


def handle_query_master(req):
    """Search across master CSV data with optional dataset filtering."""
    conn = pool.sqlite
    query = req.get("query", "").strip()
    if not query:
        return {"ok": False, "error": "query required"}

    limit = min(req.get("limit", 20), 100)
    dataset = req.get("dataset")

    for table in ["master_csv_data", "master_data"]:
        if not _table_exists(table):
            continue

        cols_info = conn.execute(f"PRAGMA table_info([{table}])").fetchall()
        col_names = {c[1] for c in cols_info}
        text_col = next((c for c in ["text_content", "content", "text", "data"] if c in col_names), None)
        ds_col = next((c for c in ["dataset_name", "dataset", "source"] if c in col_names), None)

        if not text_col:
            continue

        where = f"{text_col} LIKE ?"
        params = [f"%{query}%"]
        if dataset and ds_col:
            where += f" AND {ds_col} = ?"
            params.append(dataset)
        params.append(limit)

        try:
            cur = conn.execute(f"SELECT * FROM [{table}] WHERE {where} LIMIT ?", params)
            columns = [desc[0] for desc in cur.description]
            results = [dict(zip(columns, r)) for r in cur.fetchall()]
            if results:
                return {"ok": True, "results": results, "count": len(results), "source": table}
        except Exception:
            continue

    return {"ok": True, "results": [], "count": 0}


# ══════════════════════════════════════════════════════════════════════════
# ADVANCED INTELLIGENCE HANDLERS (vector search, audit, chains, deadlines)
# ══════════════════════════════════════════════════════════════════════════


def handle_vector_search(req):
    """Real vector similarity search via LanceDB (not FTS5 stub)."""
    query = req.get("query", "").strip()
    if not query:
        return {"ok": False, "error": "query required"}
    top_k = min(req.get("top_k", 10), 50)

    if not (_HAS_LANCEDB and pool.lance_table is not None):
        clean = sanitize_fts5(query)
        if _table_exists("evidence_fts"):
            try:
                cur = pool.sqlite.execute(
                    """SELECT quote_text, source_file, category, lane,
                              rank AS score
                       FROM evidence_fts
                       JOIN evidence_quotes ON evidence_quotes.rowid = evidence_fts.rowid
                       WHERE evidence_fts MATCH ? ORDER BY rank LIMIT ?""",
                    (clean, top_k)
                )
                cols = [d[0] for d in cur.description]
                rows = [dict(zip(cols, r)) for r in cur.fetchall()]
                return {"ok": True, "results": rows, "count": len(rows), "engine": "fts5_fallback"}
            except Exception:
                pass
        return {"ok": True, "results": [], "count": 0, "note": "LanceDB not available, FTS5 fallback empty"}

    try:
        results = pool.lance_table.search(query).limit(top_k).to_list()
        formatted = []
        for r in results:
            item = {"score": round(float(r.get("_distance", 0)), 4)}
            for k in ["text", "content", "source", "category", "lane", "id"]:
                if k in r:
                    item[k] = r[k]
            formatted.append(item)
        return {"ok": True, "results": formatted, "count": len(formatted), "engine": "lancedb"}
    except Exception as e:
        return {"ok": False, "error": f"LanceDB search failed: {e}"}


def handle_self_audit(_req):
    """Data-quality audit — quality score 0-100 with findings."""
    conn = pool.sqlite
    findings = []
    scores = {"documents": 0, "evidence": 0, "authority": 0, "evolution": 0, "system": 0}

    doc_count = _count_table(conn, "documents")
    page_count = _count_table(conn, "pages")
    if doc_count > 0:
        scores["documents"] = min(20, doc_count // 5)
    if page_count > 0:
        scores["documents"] = min(20, scores["documents"] + page_count // 50)
    if doc_count == 0:
        findings.append({"severity": "HIGH", "finding": "No documents ingested"})

    ev_count = _count_table(conn, "evidence_quotes")
    tl_count = _count_table(conn, "timeline_events")
    scores["evidence"] = min(20, ev_count // 5000 + tl_count // 1000)
    if ev_count == 0:
        findings.append({"severity": "CRITICAL", "finding": "evidence_quotes table empty"})

    auth_count = _count_table(conn, "authority_chains_v2")
    rule_count = _count_table(conn, "michigan_rules_extracted")
    scores["authority"] = min(20, auth_count // 5000 + rule_count // 500)
    if auth_count == 0:
        findings.append({"severity": "HIGH", "finding": "authority_chains_v2 empty"})

    md_count = _count_table(conn, "md_sections")
    xref_count = _count_table(conn, "md_cross_refs")
    scores["evolution"] = min(20, md_count // 5000 + xref_count // 1000)

    table_count = len(conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall())
    scores["system"] = min(20, table_count // 40)

    total = sum(scores.values())
    return {
        "ok": True,
        "quality_score": total,
        "max_score": 100,
        "component_scores": scores,
        "findings": findings,
        "finding_count": len(findings),
        "summary": {
            "documents": doc_count, "pages": page_count,
            "evidence_quotes": ev_count, "timeline_events": tl_count,
            "authority_chains": auth_count, "rules": rule_count,
            "md_sections": md_count, "cross_refs": xref_count,
            "tables": table_count
        }
    }


def handle_evidence_chain(req):
    """Trace the evidence chain for a legal claim."""
    conn = pool.sqlite
    claim = req.get("claim", "").strip()
    if not claim:
        return {"ok": False, "error": "claim required"}

    chain = {"claim": claim, "sections": [], "cross_refs": [], "sources": [], "completeness": 0}

    if _table_exists("md_sections_fts") and _table_exists("md_sections"):
        clean = sanitize_fts5(claim)
        if clean:
            try:
                cur = conn.execute(
                    """SELECT ms.file_path, ms.heading,
                              snippet(md_sections_fts, 0, '>>>', '<<<', '...', 80) AS snippet
                       FROM md_sections_fts
                       JOIN md_sections ms ON ms.rowid = md_sections_fts.rowid
                       WHERE md_sections_fts MATCH ? ORDER BY rank LIMIT 15""", (clean,)
                )
                chain["sections"] = [{"file": r[0], "heading": r[1], "snippet": r[2]} for r in cur.fetchall()]
            except Exception:
                pass

    if _table_exists("md_cross_refs"):
        try:
            cols_info = conn.execute("PRAGMA table_info(md_cross_refs)").fetchall()
            cn = {c[1] for c in cols_info}
            val_col = next((c for c in ["ref_value", "value"] if c in cn), None)
            if val_col:
                cur = conn.execute(
                    f"SELECT * FROM md_cross_refs WHERE {val_col} LIKE ? LIMIT 20",
                    (f"%{claim}%",)
                )
                cols = [d[0] for d in cur.description]
                chain["cross_refs"] = [dict(zip(cols, r)) for r in cur.fetchall()]
        except Exception:
            pass

    if _table_exists("evidence_fts"):
        clean = sanitize_fts5(claim)
        if clean:
            try:
                cur = conn.execute(
                    """SELECT quote_text, source_file, category
                       FROM evidence_fts
                       JOIN evidence_quotes ON evidence_quotes.rowid = evidence_fts.rowid
                       WHERE evidence_fts MATCH ? ORDER BY rank LIMIT 10""", (clean,)
                )
                chain["sources"] = [{"quote": r[0], "source": r[1], "category": r[2]} for r in cur.fetchall()]
            except Exception:
                pass

    parts = sum(1 for v in [chain["sections"], chain["cross_refs"], chain["sources"]] if v)
    chain["completeness"] = round(parts / 3 * 100)
    chain["gaps"] = []
    if not chain["sections"]:
        chain["gaps"].append("No evolved sections match this claim")
    if not chain["cross_refs"]:
        chain["gaps"].append("No cross-references found")
    if not chain["sources"]:
        chain["gaps"].append("No direct evidence quotes found")

    return {"ok": True, "chain": chain}


def handle_compute_deadlines(req):
    """Compute legal deadlines from a trigger event and date."""
    trigger_event = req.get("trigger_event", "").strip()
    trigger_date_str = req.get("trigger_date", "").strip()
    if not trigger_event or not trigger_date_str:
        return {"ok": False, "error": "trigger_event and trigger_date required"}

    try:
        trigger_date = datetime.strptime(trigger_date_str, "%Y-%m-%d").date()
    except ValueError:
        return {"ok": False, "error": f"Invalid date format: {trigger_date_str}. Use YYYY-MM-DD."}

    rules = {
        "motion_served": [
            {"name": "Response due", "days": 21, "rule": "MCR 2.108(A)(1)"},
            {"name": "Reply brief due", "days": 28, "rule": "MCR 2.119(F)(1)"},
            {"name": "Hearing (earliest)", "days": 9, "rule": "MCR 2.119(C)(1)"},
        ],
        "complaint_filed": [
            {"name": "Answer due", "days": 21, "rule": "MCR 2.108(A)(1)"},
            {"name": "Default possible", "days": 22, "rule": "MCR 2.603"},
        ],
        "order_entered": [
            {"name": "Motion for reconsideration", "days": 21, "rule": "MCR 2.119(F)(1)"},
            {"name": "Claim of appeal", "days": 21, "rule": "MCR 7.204(A)(1)"},
            {"name": "Application for leave (COA)", "days": 21, "rule": "MCR 7.205(A)"},
            {"name": "Application for leave (MSC)", "days": 56, "rule": "MCR 7.305(C)(2)"},
        ],
        "ppo_served": [
            {"name": "Motion to terminate/modify", "days": 14, "rule": "MCR 3.707(A)"},
        ],
        "appeal_filed": [
            {"name": "Appellant brief due", "days": 56, "rule": "MCR 7.212(A)(1)"},
            {"name": "Appellee brief due", "days": 91, "rule": "MCR 7.212(A)(2)"},
            {"name": "Reply brief due", "days": 112, "rule": "MCR 7.212(A)(3)"},
        ],
    }

    event_rules = rules.get(trigger_event, [])
    if not event_rules:
        known = list(rules.keys())
        return {"ok": False, "error": f"Unknown trigger: {trigger_event}. Known: {known}"}

    deadlines = []
    for r in event_rules:
        due = trigger_date + timedelta(days=r["days"])
        days_left = (due - date.today()).days
        urgency = "🔴 OVERDUE" if days_left < 0 else "🟠 CRITICAL" if days_left <= 3 else "🟡 URGENT" if days_left <= 7 else "🟢 OK"
        deadlines.append({
            "name": r["name"], "days_from_trigger": r["days"],
            "due_date": due.isoformat(), "days_left": days_left,
            "urgency": urgency, "rule": r["rule"]
        })

    deadlines.sort(key=lambda d: d["due_date"])
    return {"ok": True, "trigger_event": trigger_event, "trigger_date": trigger_date_str,
            "deadlines": deadlines, "count": len(deadlines)}


def handle_red_team(req):
    """Red-team validate a legal claim or argument."""
    conn = pool.sqlite
    claim = req.get("claim", "").strip()
    if not claim:
        return {"ok": False, "error": "claim required"}

    findings = []
    scores = {"authority": 0, "evidence": 0, "consistency": 0}

    if _table_exists("authority_chains_v2"):
        try:
            cur = conn.execute(
                "SELECT COUNT(*) FROM authority_chains_v2 WHERE primary_citation LIKE ? OR supporting_citation LIKE ?",
                (f"%{claim}%", f"%{claim}%")
            )
            auth_count = cur.fetchone()[0]
            scores["authority"] = min(33, auth_count * 3)
            if auth_count == 0:
                findings.append({"severity": "CRITICAL", "area": "authority",
                                 "finding": f"No authority chain found for '{claim}'"})
        except Exception:
            pass

    if _table_exists("evidence_fts"):
        clean = sanitize_fts5(claim)
        if clean:
            try:
                cur = conn.execute(
                    "SELECT COUNT(*) FROM evidence_fts WHERE evidence_fts MATCH ?", (clean,)
                )
                ev_count = cur.fetchone()[0]
                scores["evidence"] = min(34, ev_count * 2)
                if ev_count < 3:
                    findings.append({"severity": "HIGH", "area": "evidence",
                                     "finding": f"Weak evidence support ({ev_count} quotes)"})
            except Exception:
                pass

    if _table_exists("contradiction_map"):
        try:
            cur = conn.execute(
                "SELECT COUNT(*) FROM contradiction_map WHERE contradiction_text LIKE ?",
                (f"%{claim}%",)
            )
            contra_count = cur.fetchone()[0]
            scores["consistency"] = max(0, 33 - contra_count * 5)
            if contra_count > 0:
                findings.append({"severity": "HIGH", "area": "consistency",
                                 "finding": f"{contra_count} contradictions touch this claim"})
            else:
                scores["consistency"] = 33
        except Exception:
            scores["consistency"] = 20

    total = sum(scores.values())
    status = "FILING_READY" if total >= 70 else "NEEDS_WORK" if total >= 40 else "NOT_READY"
    return {
        "ok": True, "claim": claim, "total_score": total, "max_score": 100,
        "component_scores": scores, "findings": findings,
        "status": status, "finding_count": len(findings)
    }




# ══════════════════════════════════════════════════════════════════════════
# ABSORBED MCP CAPABILITIES (13 new handlers)
# ══════════════════════════════════════════════════════════════════════════

def handle_health(req):
    """Composite health check: CircuitBreaker + HealthStatus + error summary."""
    reset_cb = req.get("reset_circuit_breaker", False)
    if reset_cb:
        health.circuit_breaker.reset()

    result = health.status
    result["ok"] = True

    # Recent error summary (last 24h)
    try:
        conn = pool.sqlite
        if _table_exists(conn, "error_log"):
            rows = conn.execute(
                """SELECT error_code, tool_name, COUNT(*) as cnt,
                          MAX(created_at) as last_seen
                   FROM error_log
                   WHERE created_at > datetime('now', '-24 hours')
                   GROUP BY error_code, tool_name
                   ORDER BY cnt DESC LIMIT 20"""
            ).fetchall()
            result["recent_errors"] = [dict(r) for r in rows]
        else:
            result["recent_errors"] = []
    except Exception as e:
        result["recent_errors"] = [{"error": str(e)}]

    return result


def handle_record_error(req):
    """Record an error event to the error_log table for telemetry."""
    error_code = req.get("error_code", "UNKNOWN")
    tool_name = req.get("tool_name", "unknown")
    message = req.get("message", "")

    conn = pool.sqlite
    # Ensure error_log table exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS error_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            error_code TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            message TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute(
        "INSERT INTO error_log (error_code, tool_name, message) VALUES (?, ?, ?)",
        (error_code, tool_name, message[:2000])
    )
    conn.commit()

    # Update circuit breaker
    health.circuit_breaker.record_failure()

    return {"ok": True, "action": "error_recorded", "error_code": error_code}


def handle_get_error_summary(req):
    """Error telemetry: group errors by code+tool from error_log."""
    hours = req.get("hours", 24)
    conn = pool.sqlite

    if not _table_exists(conn, "error_log"):
        return {"ok": True, "rows": [], "count": 0, "message": "No error_log table"}

    try:
        rows = conn.execute(
            """SELECT error_code, tool_name, COUNT(*) as cnt,
                      MAX(created_at) as last_seen,
                      MIN(created_at) as first_seen
               FROM error_log
               WHERE created_at > datetime('now', ? || ' hours')
               GROUP BY error_code, tool_name
               ORDER BY cnt DESC LIMIT 50""",
            (f"-{hours}",)
        ).fetchall()
        data = [dict(r) for r in rows]

        # Add recovery hints
        for row in data:
            try:
                code = ErrorCode(row["error_code"])
                row["recovery_hint"] = _RECOVERY_HINTS.get(code, "")
            except ValueError:
                row["recovery_hint"] = ""

        return {"ok": True, "rows": data, "count": len(data), "hours": hours}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def handle_check_disk_space(req):
    """Disk space across all litigation drives using shutil.disk_usage()."""
    drives = req.get("drives", ["C:", "D:", "F:", "G:", "I:", "J:"])
    results = []

    for drive in drives:
        drive_path = drive if drive.endswith("\\") else drive + "\\"
        try:
            usage = shutil.disk_usage(drive_path)
            results.append({
                "drive": drive,
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "percent_used": round(usage.used * 100 / usage.total, 1) if usage.total else 0,
                "status": "OK" if usage.free > 1024**3 else "LOW" if usage.free > 512*1024**2 else "CRITICAL",
            })
        except OSError:
            results.append({"drive": drive, "status": "UNAVAILABLE"})

    critical = [r for r in results if r.get("status") == "CRITICAL"]
    return {
        "ok": True,
        "drives": results,
        "critical_count": len(critical),
        "warning": "DISK SPACE CRITICAL" if critical else None,
    }


def handle_scan_all_systems(req):
    """Composite system scan: DB integrity, FTS5, disk, connections, circuit breaker."""
    results = {"ok": True, "checks": {}, "pass_count": 0, "fail_count": 0}
    conn = pool.sqlite

    # 1. DB connectivity
    try:
        conn.execute("SELECT 1")
        results["checks"]["db_connect"] = {"status": "PASS"}
        results["pass_count"] += 1
    except Exception as e:
        results["checks"]["db_connect"] = {"status": "FAIL", "error": str(e)}
        results["fail_count"] += 1

    # 2. DB integrity check (quick)
    try:
        row = conn.execute("PRAGMA quick_check(1)").fetchone()
        ok = row[0] == "ok" if row else False
        results["checks"]["db_integrity"] = {"status": "PASS" if ok else "FAIL"}
        results["pass_count" if ok else "fail_count"] += 1
    except Exception as e:
        results["checks"]["db_integrity"] = {"status": "FAIL", "error": str(e)}
        results["fail_count"] += 1

    # 3. FTS5 round-trip
    try:
        if _table_exists(conn, "evidence_fts"):
            conn.execute("SELECT COUNT(*) FROM evidence_fts WHERE evidence_fts MATCH 'test'")
            results["checks"]["fts5"] = {"status": "PASS"}
        else:
            results["checks"]["fts5"] = {"status": "SKIP", "reason": "No evidence_fts table"}
        results["pass_count"] += 1
    except Exception as e:
        results["checks"]["fts5"] = {"status": "FAIL", "error": str(e)}
        results["fail_count"] += 1

    # 4. DuckDB
    if _HAS_DUCKDB and pool.duck:
        try:
            pool.duck.execute("SELECT 1")
            results["checks"]["duckdb"] = {"status": "PASS"}
            results["pass_count"] += 1
        except Exception as e:
            results["checks"]["duckdb"] = {"status": "FAIL", "error": str(e)}
            results["fail_count"] += 1
    else:
        results["checks"]["duckdb"] = {"status": "SKIP", "reason": "Not available"}

    # 5. LanceDB
    if _HAS_LANCEDB and pool.lance_table is not None:
        results["checks"]["lancedb"] = {"status": "PASS"}
        results["pass_count"] += 1
    else:
        results["checks"]["lancedb"] = {"status": "SKIP", "reason": "Not available"}

    # 6. Disk space (C: only for speed)
    try:
        usage = shutil.disk_usage("C:\\")
        free_gb = usage.free / (1024**3)
        results["checks"]["disk_c"] = {
            "status": "PASS" if free_gb > 1 else "WARN",
            "free_gb": round(free_gb, 2),
        }
        results["pass_count"] += 1
    except Exception as e:
        results["checks"]["disk_c"] = {"status": "FAIL", "error": str(e)}
        results["fail_count"] += 1

    # 7. Circuit breaker
    cb = health.circuit_breaker
    results["checks"]["circuit_breaker"] = {
        "status": "PASS" if cb.allow_request() else "FAIL",
        **cb.status,
    }
    results["pass_count" if cb.allow_request() else "fail_count"] += 1

    # 8. Health status
    results["health"] = health.status

    return results


def handle_evolve_md(req):
    """Evolve .md files into cross-reference knowledge layer (WRITE operation).

    Walks directory for .md files, extracts sections via headings,
    extracts cross-refs (MCR/MCL/case law), links to graph nodes.
    Inserts to md_sections + md_cross_refs. Skips already-evolved files.
    Ported from MCP db.py evolve_all_md_files (lines 1468-1529).
    """
    directory = req.get("directory", "")
    if not directory:
        return {"ok": False, "error": "No directory provided"}

    try:
        real_dir = _validate_path(directory)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    if not os.path.isdir(real_dir):
        return {"ok": False, "error": f"Not a directory: {real_dir}"}

    conn = pool.sqlite
    # Ensure tables exist
    conn.execute("""CREATE TABLE IF NOT EXISTS md_sections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_file TEXT, source_path TEXT, level INTEGER,
        title TEXT, content TEXT, source_type TEXT DEFAULT 'md',
        created_at TEXT DEFAULT (datetime('now'))
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS md_cross_refs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        section_id INTEGER, ref_type TEXT, ref_value TEXT,
        confidence REAL, graph_node_id TEXT, graph_source TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    # Get already-evolved files
    evolved = set()
    try:
        rows = conn.execute(
            "SELECT DISTINCT source_file FROM md_sections WHERE source_type = 'md'"
        ).fetchall()
        evolved = {r[0] for r in rows}
    except Exception:
        pass

    stats = {"files_found": 0, "files_evolved": 0, "files_skipped": 0,
             "sections_created": 0, "cross_refs_created": 0, "errors": []}

    for root, _, files in os.walk(real_dir):
        for fname in files:
            if not fname.endswith(".md"):
                continue
            stats["files_found"] += 1
            fpath = os.path.join(root, fname)

            if fname in evolved:
                stats["files_skipped"] += 1
                continue

            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read(500000)  # 500KB max

                sections = _extract_md_sections(text, fname, fpath)
                for sec in sections:
                    cur = conn.execute(
                        """INSERT INTO md_sections (source_file, source_path, level, title, content, source_type)
                           VALUES (?, ?, ?, ?, ?, 'md')""",
                        (sec["source_file"], sec["path"], sec["level"], sec["title"], sec["content"])
                    )
                    section_id = cur.lastrowid
                    stats["sections_created"] += 1

                    xrefs = _extract_cross_refs(sec["content"])
                    for xr in xrefs:
                        graph_link = _link_ref_to_graph(conn, xr["ref_value"])
                        gn_id = graph_link["graph_node_id"] if graph_link else None
                        gs = graph_link["graph_source"] if graph_link else None
                        conn.execute(
                            """INSERT INTO md_cross_refs (section_id, ref_type, ref_value, confidence, graph_node_id, graph_source)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                            (section_id, xr["ref_type"], xr["ref_value"], xr["confidence"], gn_id, gs)
                        )
                        stats["cross_refs_created"] += 1

                stats["files_evolved"] += 1
                evolved.add(fname)

            except Exception as e:
                stats["errors"].append({"file": fname, "error": str(e)[:200]})

    conn.commit()
    return {"ok": True, **stats}


def handle_evolve_txt(req):
    """Evolve .txt files into cross-reference knowledge layer (WRITE operation).

    Each .txt file treated as single section. Extracts cross-refs, links to graph.
    Ported from MCP db.py evolve_all_txt_files (lines 1532-1590).
    """
    directory = req.get("directory", "")
    if not directory:
        return {"ok": False, "error": "No directory provided"}

    try:
        real_dir = _validate_path(directory)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    if not os.path.isdir(real_dir):
        return {"ok": False, "error": f"Not a directory: {real_dir}"}

    conn = pool.sqlite
    conn.execute("""CREATE TABLE IF NOT EXISTS md_sections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_file TEXT, source_path TEXT, level INTEGER,
        title TEXT, content TEXT, source_type TEXT DEFAULT 'md',
        created_at TEXT DEFAULT (datetime('now'))
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS md_cross_refs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        section_id INTEGER, ref_type TEXT, ref_value TEXT,
        confidence REAL, graph_node_id TEXT, graph_source TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    evolved = set()
    try:
        rows = conn.execute(
            "SELECT DISTINCT source_file FROM md_sections WHERE source_type = 'txt'"
        ).fetchall()
        evolved = {r[0] for r in rows}
    except Exception:
        pass

    stats = {"files_found": 0, "files_evolved": 0, "files_skipped": 0,
             "sections_created": 0, "cross_refs_created": 0, "errors": []}

    for root, _, files in os.walk(real_dir):
        for fname in files:
            if not fname.endswith(".txt"):
                continue
            stats["files_found"] += 1
            fpath = os.path.join(root, fname)

            if fname in evolved:
                stats["files_skipped"] += 1
                continue

            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read(500000)

                cur = conn.execute(
                    """INSERT INTO md_sections (source_file, source_path, level, title, content, source_type)
                       VALUES (?, ?, 0, ?, ?, 'txt')""",
                    (fname, fpath, fname, text[:50000])
                )
                section_id = cur.lastrowid
                stats["sections_created"] += 1

                xrefs = _extract_cross_refs(text)
                for xr in xrefs:
                    graph_link = _link_ref_to_graph(conn, xr["ref_value"])
                    gn_id = graph_link["graph_node_id"] if graph_link else None
                    gs = graph_link["graph_source"] if graph_link else None
                    conn.execute(
                        """INSERT INTO md_cross_refs (section_id, ref_type, ref_value, confidence, graph_node_id, graph_source)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (section_id, xr["ref_type"], xr["ref_value"], xr["confidence"], gn_id, gs)
                    )
                    stats["cross_refs_created"] += 1

                stats["files_evolved"] += 1
                evolved.add(fname)

            except Exception as e:
                stats["errors"].append({"file": fname, "error": str(e)[:200]})

    conn.commit()
    return {"ok": True, **stats}


def handle_evolve_pages(req):
    """Evolve ingested PDF pages into cross-reference knowledge layer (WRITE operation).

    Iterates documents→pages, creates sections per page, extracts cross-refs.
    Ported from MCP db.py evolve_from_pages (lines 1593-1662).
    """
    document_id = req.get("document_id")  # None = all documents
    conn = pool.sqlite

    if not _table_exists(conn, "pages"):
        return {"ok": False, "error": "No 'pages' table — ingest PDFs first"}

    conn.execute("""CREATE TABLE IF NOT EXISTS md_sections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_file TEXT, source_path TEXT, level INTEGER,
        title TEXT, content TEXT, source_type TEXT DEFAULT 'md',
        created_at TEXT DEFAULT (datetime('now'))
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS md_cross_refs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        section_id INTEGER, ref_type TEXT, ref_value TEXT,
        confidence REAL, graph_node_id TEXT, graph_source TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    # Get already-evolved page sources
    evolved_sources = set()
    try:
        rows = conn.execute(
            "SELECT DISTINCT source_file FROM md_sections WHERE source_type = 'pdf'"
        ).fetchall()
        evolved_sources = {r[0] for r in rows}
    except Exception:
        pass

    # Build document query
    if document_id:
        doc_rows = conn.execute("SELECT id, file_name FROM documents WHERE id = ?", (document_id,)).fetchall()
    else:
        # Adaptive column check
        cols = {r[1] for r in conn.execute("PRAGMA table_info(documents)").fetchall()}
        name_col = "file_name" if "file_name" in cols else "title" if "title" in cols else "file_path"
        doc_rows = conn.execute(f"SELECT id, {name_col} FROM documents").fetchall()

    stats = {"documents_found": len(doc_rows), "pages_evolved": 0, "pages_skipped": 0,
             "sections_created": 0, "cross_refs_created": 0, "errors": []}

    for doc_id, doc_name in doc_rows:
        source_key = f"pdf:{doc_id}:{doc_name}"
        if source_key in evolved_sources:
            stats["pages_skipped"] += 1
            continue

        try:
            pages = conn.execute(
                "SELECT page_number, text_content FROM pages WHERE document_id = ? ORDER BY page_number",
                (doc_id,)
            ).fetchall()

            for page_num, text in pages:
                if not text or not text.strip():
                    continue

                title = f"{doc_name} — Page {page_num}"
                cur = conn.execute(
                    """INSERT INTO md_sections (source_file, source_path, level, title, content, source_type)
                       VALUES (?, ?, 0, ?, ?, 'pdf')""",
                    (source_key, f"document:{doc_id}/page:{page_num}", title, text[:50000])
                )
                section_id = cur.lastrowid
                stats["sections_created"] += 1

                xrefs = _extract_cross_refs(text)
                for xr in xrefs:
                    graph_link = _link_ref_to_graph(conn, xr["ref_value"])
                    gn_id = graph_link["graph_node_id"] if graph_link else None
                    gs = graph_link["graph_source"] if graph_link else None
                    conn.execute(
                        """INSERT INTO md_cross_refs (section_id, ref_type, ref_value, confidence, graph_node_id, graph_source)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (section_id, xr["ref_type"], xr["ref_value"], xr["confidence"], gn_id, gs)
                    )
                    stats["cross_refs_created"] += 1

                stats["pages_evolved"] += 1

            evolved_sources.add(source_key)

        except Exception as e:
            stats["errors"].append({"document": doc_name, "error": str(e)[:200]})

    conn.commit()
    return {"ok": True, **stats}


def handle_document_exists(req):
    """Check if a document is already indexed (by file_path)."""
    file_path = req.get("file_path", "")
    if not file_path:
        return {"ok": False, "error": "No file_path provided"}

    conn = pool.sqlite
    if not _table_exists(conn, "documents"):
        return {"ok": True, "exists": False, "message": "No documents table"}

    cols = {r[1] for r in conn.execute("PRAGMA table_info(documents)").fetchall()}
    path_col = "file_path" if "file_path" in cols else "source_path" if "source_path" in cols else None

    if not path_col:
        return {"ok": True, "exists": False, "message": "No path column in documents"}

    row = conn.execute(f"SELECT id FROM documents WHERE {path_col} = ? LIMIT 1", (file_path,)).fetchone()
    return {"ok": True, "exists": row is not None, "document_id": row[0] if row else None}


def handle_hash_exists(req):
    """Check if a document with given SHA-256 hash exists."""
    sha256 = req.get("sha256", "")
    if not sha256:
        return {"ok": False, "error": "No sha256 provided"}

    conn = pool.sqlite
    if not _table_exists(conn, "documents"):
        return {"ok": True, "exists": False}

    cols = {r[1] for r in conn.execute("PRAGMA table_info(documents)").fetchall()}
    hash_col = "sha256_hash" if "sha256_hash" in cols else "sha256" if "sha256" in cols else None

    if not hash_col:
        return {"ok": True, "exists": False, "message": "No hash column"}

    row = conn.execute(f"SELECT id FROM documents WHERE {hash_col} = ? LIMIT 1", (sha256,)).fetchone()
    return {"ok": True, "exists": row is not None, "document_id": row[0] if row else None}


def handle_delete_document(req):
    """Delete a document and its pages from the knowledge base (WRITE operation)."""
    doc_id = req.get("document_id")
    if not doc_id:
        return {"ok": False, "error": "No document_id provided"}

    conn = pool.sqlite
    if not _table_exists(conn, "documents"):
        return {"ok": False, "error": "No documents table"}

    # Delete pages first (cascade)
    pages_deleted = 0
    if _table_exists(conn, "pages"):
        cur = conn.execute("DELETE FROM pages WHERE document_id = ?", (doc_id,))
        pages_deleted = cur.rowcount

    cur = conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    doc_deleted = cur.rowcount
    conn.commit()

    return {
        "ok": True, "action": "deleted",
        "document_id": doc_id, "document_deleted": doc_deleted,
        "pages_deleted": pages_deleted,
    }


def handle_insert_document(req):
    """Insert a new document record (WRITE operation)."""
    file_path = req.get("file_path", "")
    file_name = req.get("file_name", "")
    sha256 = req.get("sha256", "")
    page_count = req.get("page_count", 0)
    file_size = req.get("file_size", 0)

    if not file_path:
        return {"ok": False, "error": "No file_path provided"}

    try:
        _validate_path(file_path)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    conn = pool.sqlite
    conn.execute("""CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_name TEXT, file_path TEXT, sha256_hash TEXT,
        page_count INTEGER DEFAULT 0, file_size_bytes INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    cur = conn.execute(
        """INSERT INTO documents (file_name, file_path, sha256_hash, page_count, file_size_bytes)
           VALUES (?, ?, ?, ?, ?)""",
        (file_name or os.path.basename(file_path), file_path, sha256, page_count, file_size)
    )
    conn.commit()

    return {"ok": True, "action": "inserted", "document_id": cur.lastrowid}


def handle_dispatch_to_swarm(req):
    """Agent routing recommendations based on task description.

    Matches task keywords to agent specializations and returns ranked recommendations.
    """
    task = req.get("task", "")
    if not task:
        return {"ok": False, "error": "No task provided"}

    task_lower = task.lower()

    # Agent capability matrix
    agents = [
        {"name": "filing-forge-master", "keywords": ["filing", "motion", "brief", "packet", "bates", "service", "qa"],
         "role": "Filing packages, QA, Bates stamps, service tracking"},
        {"name": "evidence-warfare-commander", "keywords": ["evidence", "gap", "impeachment", "contradiction", "witness"],
         "role": "Evidence triage, gap analysis, impeachment prep"},
        {"name": "judicial-accountability-engine", "keywords": ["judge", "mcneill", "judicial", "jtc", "misconduct", "bias", "canon"],
         "role": "Judicial misconduct documentation, JTC complaints"},
        {"name": "timeline-forensics", "keywords": ["timeline", "chronology", "transcript", "hearing", "testimony"],
         "role": "Extract testimony/rulings, build timelines"},
        {"name": "appellate-record-builder", "keywords": ["appeal", "coa", "msc", "appendix", "record", "brief"],
         "role": "COA/MSC record assembly, appendices"},
        {"name": "family-law-guardian", "keywords": ["custody", "parenting", "child", "gal", "best interest", "factor"],
         "role": "Custody analysis, MCL 722.23 factors"},
        {"name": "damages-calculator", "keywords": ["damages", "cost", "fee", "mileage", "economic", "punitive"],
         "role": "Calculate damages across all categories"},
        {"name": "case-strategy-architect", "keywords": ["strategy", "plan", "priority", "sequence", "war"],
         "role": "High-level litigation strategy and prioritization"},
        {"name": "compliance-auditor", "keywords": ["redact", "pii", "compliance", "audit", "child name"],
         "role": "Redact PII, audit filing compliance"},
        {"name": "contempt-prosecutor", "keywords": ["contempt", "show cause", "violation", "enforce"],
         "role": "Contempt motions, show cause proceedings"},
        {"name": "federal-1983-specialist", "keywords": ["1983", "federal", "civil rights", "qualified immunity", "monell"],
         "role": "42 USC §1983 claims, federal complaints"},
        {"name": "deep-research", "keywords": ["research", "case law", "statute", "legal theory", "web"],
         "role": "Deep legal and factual research with web search"},
    ]

    scored = []
    for agent in agents:
        score = sum(3 for kw in agent["keywords"] if kw in task_lower)
        if score > 0:
            scored.append({**agent, "relevance_score": score})

    scored.sort(key=lambda x: x["relevance_score"], reverse=True)
    top = scored[:5] if scored else [{"name": "case-strategy-architect", "role": "Default: strategy", "relevance_score": 1}]

    return {
        "ok": True,
        "task": task[:200],
        "recommendations": top,
        "count": len(top),
    }


# ══════════════════════════════════════════════════════════════════════════
# AGENT MEMORY (ABSORBED from agent-memory MCP — ZERO external dependency)
# ══════════════════════════════════════════════════════════════════════════

def _ensure_memory_table(conn):
    """Create agent_memory table and FTS5 index if they don't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            fact TEXT NOT NULL,
            citations TEXT,
            reason TEXT,
            session_id TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    try:
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS agent_memory_fts
            USING fts5(subject, fact, citations, reason,
                       content=agent_memory, content_rowid=id)
        """)
    except Exception:
        pass  # FTS5 index may already exist


def handle_memory_store(req):
    """Store a fact in persistent agent memory."""
    conn = ConnectionPool.get_sqlite()
    _ensure_memory_table(conn)

    subject = req.get("subject", "").strip()
    fact = req.get("fact", "").strip()
    citations = req.get("citations", "").strip()
    reason = req.get("reason", "").strip()
    session_id = req.get("session_id", "")

    if not fact:
        return {"ok": False, "error": "fact is required"}

    cur = conn.execute(
        "INSERT INTO agent_memory (subject, fact, citations, reason, session_id) "
        "VALUES (?, ?, ?, ?, ?)",
        (subject, fact, citations, reason, session_id),
    )
    row_id = cur.lastrowid
    conn.commit()

    # Sync FTS5 index
    try:
        conn.execute(
            "INSERT INTO agent_memory_fts(rowid, subject, fact, citations, reason) "
            "VALUES (?, ?, ?, ?, ?)",
            (row_id, subject, fact, citations, reason),
        )
        conn.commit()
    except Exception:
        pass

    return {"ok": True, "id": row_id, "action": "memory_store"}


def handle_memory_recall(req):
    """Search agent memory via FTS5 with LIKE fallback."""
    conn = ConnectionPool.get_sqlite()
    _ensure_memory_table(conn)

    query = req.get("query", "").strip()
    subject = req.get("subject", "").strip()
    limit = min(int(req.get("limit", 20)), 100)

    if not query and not subject:
        return {"ok": False, "error": "query or subject required"}

    cols = ["id", "subject", "fact", "citations", "reason", "session_id", "created_at"]
    rows = []

    # FTS5 path
    if query:
        safe_q = sanitize_fts5(query)
        if safe_q:
            try:
                rows = conn.execute(
                    "SELECT am.id, am.subject, am.fact, am.citations, am.reason, "
                    "am.session_id, am.created_at "
                    "FROM agent_memory am "
                    "JOIN agent_memory_fts fts ON am.id = fts.rowid "
                    "WHERE agent_memory_fts MATCH ? "
                    "ORDER BY rank LIMIT ?",
                    (safe_q, limit),
                ).fetchall()
            except Exception:
                pass

    # LIKE fallback
    if not rows:
        term = query or subject
        param = f"%{term}%"
        try:
            rows = conn.execute(
                "SELECT id, subject, fact, citations, reason, session_id, created_at "
                "FROM agent_memory "
                "WHERE subject LIKE ? OR fact LIKE ? OR citations LIKE ? OR reason LIKE ? "
                "ORDER BY created_at DESC LIMIT ?",
                (param, param, param, param, limit),
            ).fetchall()
        except Exception:
            rows = []

    results = [dict(zip(cols, r)) for r in rows]
    return {"ok": True, "rows": results, "count": len(results), "columns": cols}


def handle_memory_list(req):
    """List recent agent memories with optional subject filter."""
    conn = ConnectionPool.get_sqlite()
    _ensure_memory_table(conn)

    limit = min(int(req.get("limit", 20)), 100)
    subject = req.get("subject", "").strip()
    cols = ["id", "subject", "fact", "citations", "reason", "session_id", "created_at"]

    try:
        if subject:
            rows = conn.execute(
                "SELECT id, subject, fact, citations, reason, session_id, created_at "
                "FROM agent_memory WHERE subject LIKE ? "
                "ORDER BY created_at DESC LIMIT ?",
                (f"%{subject}%", limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, subject, fact, citations, reason, session_id, created_at "
                "FROM agent_memory ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    except Exception:
        return {"ok": True, "rows": [], "count": 0, "columns": cols}

    results = [dict(zip(cols, r)) for r in rows]
    return {"ok": True, "rows": results, "count": len(results), "columns": cols}


# ══════════════════════════════════════════════════════════════════════════
# ACTION ROUTER
# ══════════════════════════════════════════════════════════════════════════

HANDLERS = {
    # Core (existing 24)
    "ping": handle_ping,
    "query": handle_query,
    "analytics": handle_analytics,
    "stats": handle_stats,
    "fts_search": handle_fts_search,
    "search_evidence": handle_search_evidence,
    "search_impeachment": handle_search_impeachment,
    "search_contradictions": handle_search_contradictions,
    "search_authority": handle_search_authority,
    "nexus_fuse": handle_nexus_fuse,
    "nexus_argue": handle_nexus_argue,
    "nexus_readiness": handle_nexus_readiness,
    "nexus_damages": handle_nexus_damages,
    "narrative": handle_narrative,
    "filing_plan": handle_filing_plan,
    "rules_check": handle_rules_check,
    "adversary": handle_adversary,
    "gap_analysis": handle_gap_analysis,
    "cross_connect": handle_cross_connect,
    "judicial_intel": handle_judicial_intel,
    "timeline_search": handle_timeline_search,
    "case_context": handle_case_context,
    "filing_status": handle_filing_status,
    "deadlines": handle_deadlines,
    # Document management (new)
    "list_documents": handle_list_documents,
    "get_document": handle_get_document,
    "search_documents": handle_search_documents,
    "ingest_pdf": handle_ingest_pdf,
    "bulk_ingest": handle_bulk_ingest,
    # Knowledge graph & rules (new)
    "lookup_rule": handle_lookup_rule,
    "query_graph": handle_query_graph,
    "lookup_authority": handle_lookup_authority,
    # Intelligence (new)
    "assess_risk": handle_assess_risk,
    "get_vehicle_map": handle_get_vehicle_map,
    "case_health": handle_case_health,
    "adversary_threats": handle_adversary_threats,
    "filing_pipeline": handle_filing_pipeline,
    "get_subagent_spec": handle_get_subagent_spec,
    # Evolution pipeline (new)
    "evolution_stats": handle_evolution_stats,
    "search_evolved": handle_search_evolved,
    "cross_refs": handle_cross_refs,
    "convergence_status": handle_convergence_status,
    # System & master data (new)
    "stats_extended": handle_stats_extended,
    "self_test": handle_self_test,
    "ingest_csv": handle_ingest_csv,
    "query_master": handle_query_master,
    # Advanced intelligence (new)
    "vector_search": handle_vector_search,
    "self_audit": handle_self_audit,
    "evidence_chain": handle_evidence_chain,
    "compute_deadlines": handle_compute_deadlines,
    "red_team": handle_red_team,
    # Resilience & Diagnostics (ABSORBED from MCP)
    "health": handle_health,
    "record_error": handle_record_error,
    "get_error_summary": handle_get_error_summary,
    "check_disk_space": handle_check_disk_space,
    "scan_all_systems": handle_scan_all_systems,
    # Document Lifecycle (ABSORBED from MCP)
    "document_exists": handle_document_exists,
    "hash_exists": handle_hash_exists,
    "delete_document": handle_delete_document,
    "insert_document": handle_insert_document,
    # Evolution Write Pipeline (ABSORBED from MCP)
    "evolve_md": handle_evolve_md,
    "evolve_txt": handle_evolve_txt,
    "evolve_pages": handle_evolve_pages,
    # Fleet Dispatch (ABSORBED from MCP)
    "dispatch_to_swarm": handle_dispatch_to_swarm,
    # Agent Memory (ABSORBED from agent-memory MCP)
    "memory_store": handle_memory_store,
    "memory_recall": handle_memory_recall,
    "memory_list": handle_memory_list,
}


# ══════════════════════════════════════════════════════════════════════════
# MAIN EVENT LOOP (persistent — reads stdin forever)
# ══════════════════════════════════════════════════════════════════════════

def main():
    """Read line-delimited JSON requests from stdin, dispatch, write responses."""
    # Force UTF-8 on stdin/stdout
    if hasattr(sys.stdin, "reconfigure"):
        try:
            sys.stdin.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(_original_stdout, "reconfigure"):
        try:
            _original_stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    # Signal readiness
    _original_stdout.write(json.dumps({"ok": True, "status": "ready", "pid": os.getpid()}) + "\n")
    _original_stdout.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        req_id = None
        try:
            req = json.loads(line)
            req_id = req.get("id")
            action = req.get("action", "")

            handler = HANDLERS.get(action)
            if not handler:
                response = {"ok": False, "error": f"Unknown action: {action}"}
            else:
                response = handler(req)

            if req_id:
                response["id"] = req_id

        except json.JSONDecodeError as e:
            response = {"ok": False, "error": f"Invalid JSON: {e}"}
        except Exception as e:
            response = {"ok": False, "error": str(e), "traceback": traceback.format_exc()[:500]}
            if req_id:
                response["id"] = req_id

        try:
            out = json.dumps(response, default=str)
            _original_stdout.write(out + "\n")
            _original_stdout.flush()
        except Exception:
            _original_stdout.write(json.dumps({"ok": False, "error": "Serialization failed"}) + "\n")
            _original_stdout.flush()


if __name__ == "__main__":
    main()

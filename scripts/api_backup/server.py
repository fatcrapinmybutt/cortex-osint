"""Litigation Intelligence API — REST endpoints for LitigationOS data.

Lightweight HTTP server using Python's built-in http.server module.
All database connections are READ-ONLY via PRAGMA query_only=ON.
FTS5 queries use sanitize + try/except + LIKE fallback per Rule 15.
"""

import json
import os
import re
import sqlite3
import sys
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

DB_PATH = os.environ.get(
    "LITIGATIONOS_DB",
    str(Path(__file__).resolve().parents[2] / "litigation_context.db"),
)
DEFAULT_PORT = 8742
SEPARATION_ANCHOR = date(2025, 7, 29)


class LitigationAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for litigation intelligence queries."""

    # ── connection helpers ───────────────────────────────────────────

    def _get_db(self):
        """Open a read-only SQLite connection with safety PRAGMAs."""
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA busy_timeout=60000")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA cache_size=-32000")
        conn.execute("PRAGMA query_only=ON")
        conn.row_factory = sqlite3.Row
        return conn

    # ── response helpers ─────────────────────────────────────────────

    def _send_json(self, data, status=200):
        body = json.dumps(data, default=str, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, message, status=400):
        self._send_json({"error": message}, status)

    def _sanitize_fts5(self, query):
        """Strip non-word chars except wildcards and quotes (Rule 15)."""
        return re.sub(r'[^\w\s*"]', " ", query).strip()

    def _param(self, params, key, default=None):
        """Extract a single query-string value."""
        vals = params.get(key)
        if vals:
            return vals[0]
        return default

    def _param_int(self, params, key, default, lo=1, hi=200):
        """Extract an integer param clamped to [lo, hi]."""
        raw = self._param(params, key, str(default))
        try:
            return max(lo, min(int(raw), hi))
        except (ValueError, TypeError):
            return default

    # ── CORS pre-flight ──────────────────────────────────────────────

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ── router ───────────────────────────────────────────────────────

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        params = parse_qs(parsed.query)

        routes = {
            "/api/health": self._health,
            "/api/stats": self._stats,
            "/api/separation": self._separation,
            "/api/evidence/search": self._evidence_search,
            "/api/evidence/lanes": self._evidence_lanes,
            "/api/authority/search": self._authority_search,
            "/api/impeachment": self._impeachment,
            "/api/contradictions": self._contradictions,
            "/api/timeline": self._timeline,
            "/api/deadlines": self._deadlines,
            "/api/filings": self._filings,
            "/api/judicial": self._judicial,
            "/api/adversary": self._adversary,
        }

        handler = routes.get(path)
        if handler:
            try:
                handler(params)
            except Exception as exc:
                self._send_error(f"Internal error: {exc}", 500)
        elif path == "/api":
            self._send_json({
                "name": "LitigationOS Intelligence API",
                "version": "1.0.0",
                "endpoints": sorted(routes.keys()),
                "separation_days": (date.today() - SEPARATION_ANCHOR).days,
            })
        else:
            self._send_error("Not found", 404)

    # ── /api/health ──────────────────────────────────────────────────

    def _health(self, params):
        conn = self._get_db()
        try:
            row = conn.execute(
                "SELECT "
                "(SELECT COUNT(*) FROM evidence_quotes) AS eq, "
                "(SELECT COUNT(*) FROM authority_chains_v2) AS ac"
            ).fetchone()
            self._send_json({
                "status": "ok",
                "evidence_quotes": row["eq"],
                "authority_chains": row["ac"],
                "separation_days": (date.today() - SEPARATION_ANCHOR).days,
                "db_path": DB_PATH,
            })
        finally:
            conn.close()

    # ── /api/stats ───────────────────────────────────────────────────

    def _stats(self, params):
        conn = self._get_db()
        try:
            row = conn.execute(
                "SELECT "
                "(SELECT COUNT(*) FROM evidence_quotes) AS evidence, "
                "(SELECT COUNT(*) FROM authority_chains_v2) AS authorities, "
                "(SELECT COUNT(*) FROM timeline_events) AS timeline, "
                "(SELECT COUNT(*) FROM impeachment_matrix) AS impeachment, "
                "(SELECT COUNT(*) FROM contradiction_map) AS contradictions, "
                "(SELECT COUNT(*) FROM judicial_violations) AS judicial"
            ).fetchone()
            self._send_json({
                "evidence": row["evidence"],
                "authorities": row["authorities"],
                "timeline": row["timeline"],
                "impeachment": row["impeachment"],
                "contradictions": row["contradictions"],
                "judicial": row["judicial"],
            })
        finally:
            conn.close()

    # ── /api/separation ──────────────────────────────────────────────

    def _separation(self, params):
        days = (date.today() - SEPARATION_ANCHOR).days
        self._send_json({
            "days": days,
            "weeks": round(days / 7, 1),
            "months": round(days / 30.44, 1),
            "anchor": "2025-07-29",
            "message": f"L.D.W. has been separated from his father for {days} days.",
        })

    # ── /api/evidence/search?q=...&limit=N&lane=X ───────────────────

    def _evidence_search(self, params):
        q = self._param(params, "q", "")
        if not q:
            return self._send_error("Missing ?q= parameter")
        limit = self._param_int(params, "limit", 50)
        lane = self._param(params, "lane")

        conn = self._get_db()
        try:
            safe_q = self._sanitize_fts5(q)
            rows = None
            # FTS5 attempt
            try:
                if lane:
                    rows = conn.execute(
                        "SELECT quote_text, source_file, category, lane, relevance_score "
                        "FROM evidence_quotes "
                        "WHERE lane = ? AND rowid IN "
                        "(SELECT rowid FROM evidence_fts WHERE evidence_fts MATCH ?) "
                        "LIMIT ?",
                        [lane, safe_q, limit],
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT quote_text, source_file, category, lane, relevance_score "
                        "FROM evidence_quotes "
                        "WHERE rowid IN "
                        "(SELECT rowid FROM evidence_fts WHERE evidence_fts MATCH ?) "
                        "LIMIT ?",
                        [safe_q, limit],
                    ).fetchall()
            except Exception:
                rows = None

            # LIKE fallback (Rule 15)
            if rows is None:
                if lane:
                    rows = conn.execute(
                        "SELECT quote_text, source_file, category, lane, relevance_score "
                        "FROM evidence_quotes "
                        "WHERE lane = ? AND quote_text LIKE ? LIMIT ?",
                        [lane, f"%{q}%", limit],
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT quote_text, source_file, category, lane, relevance_score "
                        "FROM evidence_quotes WHERE quote_text LIKE ? LIMIT ?",
                        [f"%{q}%", limit],
                    ).fetchall()

            results = [
                {
                    "quote": r["quote_text"],
                    "source": r["source_file"],
                    "category": r["category"],
                    "lane": r["lane"],
                    "relevance": r["relevance_score"],
                }
                for r in rows
            ]
            self._send_json({"results": results, "count": len(results)})
        finally:
            conn.close()

    # ── /api/evidence/lanes ──────────────────────────────────────────

    def _evidence_lanes(self, params):
        conn = self._get_db()
        try:
            rows = conn.execute(
                "SELECT lane, COUNT(*) AS cnt FROM evidence_quotes "
                "WHERE lane IS NOT NULL AND lane != '' "
                "GROUP BY lane ORDER BY cnt DESC"
            ).fetchall()
            self._send_json({
                "lanes": [{"lane": r["lane"], "count": r["cnt"]} for r in rows],
            })
        finally:
            conn.close()

    # ── /api/authority/search?q=...&limit=N ──────────────────────────

    def _authority_search(self, params):
        q = self._param(params, "q", "")
        if not q:
            return self._send_error("Missing ?q= parameter")
        limit = self._param_int(params, "limit", 50)

        conn = self._get_db()
        try:
            rows = conn.execute(
                "SELECT primary_citation, supporting_citation, relationship, "
                "source_document, source_type, lane "
                "FROM authority_chains_v2 "
                "WHERE primary_citation LIKE ? OR supporting_citation LIKE ? "
                "LIMIT ?",
                [f"%{q}%", f"%{q}%", limit],
            ).fetchall()
            results = [
                {
                    "primary": r["primary_citation"],
                    "supporting": r["supporting_citation"],
                    "relationship": r["relationship"],
                    "source_document": r["source_document"],
                    "source_type": r["source_type"],
                    "lane": r["lane"],
                }
                for r in rows
            ]
            self._send_json({"results": results, "count": len(results)})
        finally:
            conn.close()

    # ── /api/impeachment?target=X&limit=N ────────────────────────────

    def _impeachment(self, params):
        target = self._param(params, "target")
        limit = self._param_int(params, "limit", 25, hi=100)

        conn = self._get_db()
        try:
            if target:
                rows = conn.execute(
                    "SELECT category, evidence_summary, impeachment_value, "
                    "cross_exam_question, source_file, event_date "
                    "FROM impeachment_matrix "
                    "WHERE evidence_summary LIKE ? "
                    "OR cross_exam_question LIKE ? "
                    "ORDER BY impeachment_value DESC LIMIT ?",
                    [f"%{target}%", f"%{target}%", limit],
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT category, evidence_summary, impeachment_value, "
                    "cross_exam_question, source_file, event_date "
                    "FROM impeachment_matrix "
                    "ORDER BY impeachment_value DESC LIMIT ?",
                    [limit],
                ).fetchall()
            results = [
                {
                    "category": r["category"],
                    "summary": r["evidence_summary"],
                    "value": r["impeachment_value"],
                    "question": r["cross_exam_question"],
                    "source": r["source_file"],
                    "date": r["event_date"],
                }
                for r in rows
            ]
            self._send_json({"results": results, "count": len(results)})
        finally:
            conn.close()

    # ── /api/contradictions?entity=X&limit=N ─────────────────────────

    def _contradictions(self, params):
        entity = self._param(params, "entity")
        limit = self._param_int(params, "limit", 25, hi=100)

        conn = self._get_db()
        try:
            if entity:
                rows = conn.execute(
                    "SELECT source_a, source_b, contradiction_text, severity, lane "
                    "FROM contradiction_map "
                    "WHERE source_a LIKE ? OR source_b LIKE ? "
                    "OR contradiction_text LIKE ? "
                    "ORDER BY severity DESC LIMIT ?",
                    [f"%{entity}%", f"%{entity}%", f"%{entity}%", limit],
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT source_a, source_b, contradiction_text, severity, lane "
                    "FROM contradiction_map ORDER BY severity DESC LIMIT ?",
                    [limit],
                ).fetchall()
            results = [
                {
                    "source_a": r["source_a"],
                    "source_b": r["source_b"],
                    "text": r["contradiction_text"],
                    "severity": r["severity"],
                    "lane": r["lane"],
                }
                for r in rows
            ]
            self._send_json({"results": results, "count": len(results)})
        finally:
            conn.close()

    # ── /api/timeline?q=...&limit=N ──────────────────────────────────

    def _timeline(self, params):
        q = self._param(params, "q")
        limit = self._param_int(params, "limit", 50)

        conn = self._get_db()
        try:
            if q:
                safe_q = self._sanitize_fts5(q)
                rows = None
                try:
                    rows = conn.execute(
                        "SELECT event_date, event_description, actors, lane, "
                        "category, severity "
                        "FROM timeline_events "
                        "WHERE rowid IN "
                        "(SELECT rowid FROM timeline_fts "
                        " WHERE timeline_fts MATCH ?) "
                        "ORDER BY event_date LIMIT ?",
                        [safe_q, limit],
                    ).fetchall()
                except Exception:
                    rows = None

                if rows is None:
                    rows = conn.execute(
                        "SELECT event_date, event_description, actors, lane, "
                        "category, severity "
                        "FROM timeline_events "
                        "WHERE event_description LIKE ? "
                        "ORDER BY event_date LIMIT ?",
                        [f"%{q}%", limit],
                    ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT event_date, event_description, actors, lane, "
                    "category, severity "
                    "FROM timeline_events ORDER BY event_date DESC LIMIT ?",
                    [limit],
                ).fetchall()

            results = [
                {
                    "date": r["event_date"],
                    "description": r["event_description"],
                    "actors": r["actors"],
                    "lane": r["lane"],
                    "category": r["category"],
                    "severity": r["severity"],
                }
                for r in rows
            ]
            self._send_json({"results": results, "count": len(results)})
        finally:
            conn.close()

    # ── /api/deadlines ───────────────────────────────────────────────

    def _deadlines(self, params):
        conn = self._get_db()
        try:
            rows = conn.execute(
                "SELECT title, due_date, status, filing_id, court, "
                "case_number, urgency, notes "
                "FROM deadlines ORDER BY due_date"
            ).fetchall()
            today = date.today().isoformat()
            results = []
            for r in rows:
                due = r["due_date"] or ""
                if due and due < today and r["status"] != "complete":
                    flag = "🔴 OVERDUE"
                elif due and due <= (date.today().__class__.fromisoformat(
                    f"{date.today().year}-{date.today().month:02d}-"
                    f"{min(date.today().day + 3, 28):02d}"
                ) if hasattr(date, "fromisoformat") else date.today()).isoformat():
                    flag = "🟠 CRITICAL"
                else:
                    flag = "🟢 OK"
                results.append({
                    "title": r["title"],
                    "due_date": due,
                    "status": r["status"],
                    "filing_id": r["filing_id"],
                    "court": r["court"],
                    "case_number": r["case_number"],
                    "urgency": r["urgency"] or flag,
                    "notes": r["notes"],
                })
            self._send_json({"results": results, "count": len(results)})
        finally:
            conn.close()

    # ── /api/filings ─────────────────────────────────────────────────

    def _filings(self, params):
        conn = self._get_db()
        try:
            rows = conn.execute(
                "SELECT filing_id, title, status, lane, case_number, "
                "doc_count, total_size_kb "
                "FROM filing_packages ORDER BY filing_id"
            ).fetchall()
            results = [
                {
                    "filing_id": r["filing_id"],
                    "title": r["title"],
                    "status": r["status"],
                    "lane": r["lane"],
                    "case_number": r["case_number"],
                    "doc_count": r["doc_count"],
                    "size_kb": r["total_size_kb"],
                }
                for r in rows
            ]
            self._send_json({"results": results, "count": len(results)})
        finally:
            conn.close()

    # ── /api/judicial?judge=X&limit=N ────────────────────────────────

    def _judicial(self, params):
        judge = self._param(params, "judge")
        limit = self._param_int(params, "limit", 50)

        conn = self._get_db()
        try:
            if judge:
                rows = conn.execute(
                    "SELECT violation_type, description, date_occurred, "
                    "mcr_rule, canon, source_file, severity, lane "
                    "FROM judicial_violations "
                    "WHERE description LIKE ? OR source_quote LIKE ? "
                    "LIMIT ?",
                    [f"%{judge}%", f"%{judge}%", limit],
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT violation_type, description, date_occurred, "
                    "mcr_rule, canon, source_file, severity, lane "
                    "FROM judicial_violations LIMIT ?",
                    [limit],
                ).fetchall()
            results = [
                {
                    "type": r["violation_type"],
                    "description": r["description"],
                    "date": r["date_occurred"],
                    "mcr_rule": r["mcr_rule"],
                    "canon": r["canon"],
                    "source": r["source_file"],
                    "severity": r["severity"],
                    "lane": r["lane"],
                }
                for r in rows
            ]
            self._send_json({"results": results, "count": len(results)})
        finally:
            conn.close()

    # ── /api/adversary?target=X ──────────────────────────────────────

    def _adversary(self, params):
        target = self._param(params, "target", "")
        if not target:
            return self._send_error("Missing ?target= parameter")

        conn = self._get_db()
        try:
            evidence = conn.execute(
                "SELECT COUNT(*) FROM evidence_quotes WHERE quote_text LIKE ?",
                [f"%{target}%"],
            ).fetchone()[0]
            impeach = conn.execute(
                "SELECT COUNT(*) FROM impeachment_matrix "
                "WHERE evidence_summary LIKE ? OR cross_exam_question LIKE ?",
                [f"%{target}%", f"%{target}%"],
            ).fetchone()[0]
            contras = conn.execute(
                "SELECT COUNT(*) FROM contradiction_map "
                "WHERE source_a LIKE ? OR source_b LIKE ? "
                "OR contradiction_text LIKE ?",
                [f"%{target}%", f"%{target}%", f"%{target}%"],
            ).fetchone()[0]
            tl_events = conn.execute(
                "SELECT COUNT(*) FROM timeline_events "
                "WHERE event_description LIKE ? OR actors LIKE ?",
                [f"%{target}%", f"%{target}%"],
            ).fetchone()[0]
            judicial = conn.execute(
                "SELECT COUNT(*) FROM judicial_violations "
                "WHERE description LIKE ? OR source_quote LIKE ?",
                [f"%{target}%", f"%{target}%"],
            ).fetchone()[0]
            total = evidence + impeach + contras + tl_events + judicial
            self._send_json({
                "target": target,
                "evidence_quotes": evidence,
                "impeachment": impeach,
                "contradictions": contras,
                "timeline_events": tl_events,
                "judicial_violations": judicial,
                "total_mentions": total,
            })
        finally:
            conn.close()

    # ── suppress default logging ─────────────────────────────────────

    def log_message(self, format, *args):
        """Suppress default stderr logging."""


def start_server(port=DEFAULT_PORT, bind="127.0.0.1"):
    """Start the Litigation Intelligence API server."""
    server = HTTPServer((bind, port), LitigationAPIHandler)
    sep_days = (date.today() - SEPARATION_ANCHOR).days
    print(f"LitigationOS Intelligence API v1.0.0")
    print(f"  Listening: http://{bind}:{port}/api")
    print(f"  Database:  {DB_PATH}")
    print(f"  Separation: {sep_days} days since {SEPARATION_ANCHOR}")
    print(f"  Endpoints: {len([k for k in dir(LitigationAPIHandler) if k.startswith('_') and not k.startswith('__')])} routes")
    print(f"Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    bind = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
    start_server(port, bind)

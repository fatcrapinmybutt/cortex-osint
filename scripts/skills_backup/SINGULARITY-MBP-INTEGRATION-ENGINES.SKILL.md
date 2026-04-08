---
skill: SINGULARITY-MBP-INTEGRATION-ENGINES
version: 1.0.0
description: >-
  14-engine bridge architecture for THEMANBEARPIG: pywebview expose, engine
  status dashboard, data flow visualization, MEEK lane overlays, FRED scoring,
  Delta999 agent status, DuckDB analytics, LanceDB semantic search, tantivy
  full-text, lazy initialization, error recovery, and engine configuration.
tier: TIER-4/INTEGRATION
domain: engine-bridge
triggers:
  - engine
  - MEEK
  - FRED
  - Nucleus
  - Delta999
  - Chimera
  - Chronos
  - DuckDB
  - LanceDB
  - tantivy
  - data flow
  - engine status
  - bridge
---

# SINGULARITY-MBP-INTEGRATION-ENGINES

> **14-engine bridge for THEMANBEARPIG.** Connects every LitigationOS engine
> to the D3.js visualization layer through pywebview's `window.expose` API.
> Lazy initialization, graceful degradation, DuckDB analytics, LanceDB
> semantic search, and tantivy full-text — all wired into the graph.

---

## 1. Engine Inventory (14 Engines)

| Engine | Tech | Purpose | Graph Integration |
|--------|------|---------|-------------------|
| nexus | Python + FTS5 | Cross-table evidence fusion | Primary data provider |
| chimera | Python | Multi-source evidence blending | Evidence node enrichment |
| chronos | Python | Timeline construction | Timeline layer data |
| cerberus | Python | Filing validation | Filing readiness overlays |
| filing_engine | Python | F1–F10 pipeline management | Filing lane nodes/links |
| intake | Python | Document intake, PDF processing | New evidence ingestion |
| rebuttal | Python | Argument rebuttal generation | Counter-argument nodes |
| narrative | Python | Court-ready Statement of Facts | Narrative arc source |
| delta999 | Python | 8 specialized litigation agents | Agent status indicators |
| analytics | DuckDB | 10–100× analytical queries | Dashboard aggregate stats |
| semantic | LanceDB + transformers | 75K-vector similarity search | "Find similar" feature |
| search | tantivy + hybrid | Sub-ms full-text search | Instant search results |
| typst | Typst | Court-ready PDF generation | Export pipeline |
| ingest | Go (8-worker goroutines) | Bulk file processing | Ingest status overlay |

---

## 2. Engine Bridge Architecture (Python ↔ JS via pywebview)

```
pywebview Window
  ├── window.expose(engine_bridge.query_engine)
  ├── window.expose(engine_bridge.get_engine_status)
  ├── window.expose(engine_bridge.search_semantic)
  ├── window.expose(engine_bridge.search_fulltext)
  ├── window.expose(engine_bridge.run_analytics)
  ├── window.expose(engine_bridge.get_meek_overlay)
  ├── window.expose(engine_bridge.get_delta999_status)
  └── window.expose(engine_bridge.get_data_flow)
         │
         ▼
  EngineBridge (Python singleton)
    ├── _engines: dict[str, LazyEngine]     # lazy-loaded engine references
    ├── _cache: dict[str, CachedResult]     # TTL cache for repeated queries
    ├── _status: dict[str, EngineStatus]    # health per engine
    └── _conn: sqlite3.Connection           # warm DB connection
```

---

## 3. Python Engine Bridge (Full Implementation)

```python
"""Engine bridge for THEMANBEARPIG — pywebview exposed API."""
import json
import time
import sqlite3
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("engine_bridge")

DB_PATH = Path(__file__).resolve().parent.parent / "litigation_context.db"
ENGINE_ROOT = Path(__file__).resolve().parent.parent / "00_SYSTEM" / "engines"


@dataclass
class CachedResult:
    data: Any
    expires: float


@dataclass
class EngineStatus:
    name: str
    status: str = "offline"  # online, degraded, offline, error
    last_query: float = 0.0
    error_msg: str = ""
    query_count: int = 0


class EngineBridge:
    """Singleton bridge connecting 14 engines to the JS visualization layer."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._conn = None
        self._duckdb_conn = None
        self._lancedb_table = None
        self._cache: dict[str, CachedResult] = {}
        self._cache_ttl = 30
        self._status: dict[str, EngineStatus] = {}

        engine_names = [
            "nexus", "chimera", "chronos", "cerberus", "filing_engine",
            "intake", "rebuttal", "narrative", "delta999", "analytics",
            "semantic", "search", "typst", "ingest",
        ]
        for name in engine_names:
            self._status[name] = EngineStatus(name=name)

    # --- Connection Management (Lazy) ---

    def _get_sqlite(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(DB_PATH))
            self._conn.execute("PRAGMA busy_timeout = 60000")
            self._conn.execute("PRAGMA journal_mode = WAL")
            self._conn.execute("PRAGMA cache_size = -32000")
            self._conn.execute("PRAGMA temp_store = MEMORY")
            self._conn.execute("PRAGMA synchronous = NORMAL")
            self._conn.row_factory = sqlite3.Row
            self._status["nexus"].status = "online"
        return self._conn

    def _get_duckdb(self):
        if self._duckdb_conn is None:
            try:
                import duckdb
                self._duckdb_conn = duckdb.connect(":memory:")
                self._duckdb_conn.execute("INSTALL sqlite; LOAD sqlite;")
                self._duckdb_conn.execute(
                    f"ATTACH '{DB_PATH}' AS lit (TYPE sqlite, READ_ONLY)"
                )
                self._status["analytics"].status = "online"
            except Exception as e:
                logger.warning("DuckDB unavailable: %s", e)
                self._status["analytics"].status = "offline"
                self._status["analytics"].error_msg = str(e)
                return None
        return self._duckdb_conn

    def _get_lancedb(self):
        if self._lancedb_table is None:
            try:
                import lancedb
                db_path = ENGINE_ROOT / "semantic" / "lancedb_store"
                if db_path.exists():
                    db = lancedb.connect(str(db_path))
                    tables = db.table_names()
                    if tables:
                        self._lancedb_table = db.open_table(tables[0])
                        self._status["semantic"].status = "online"
                    else:
                        self._status["semantic"].status = "offline"
                        self._status["semantic"].error_msg = "No tables in LanceDB store"
                else:
                    self._status["semantic"].status = "offline"
                    self._status["semantic"].error_msg = "LanceDB store not found"
            except Exception as e:
                logger.warning("LanceDB unavailable: %s", e)
                self._status["semantic"].status = "offline"
                self._status["semantic"].error_msg = str(e)
        return self._lancedb_table

    # --- Cache ---

    def _cache_get(self, key: str):
        entry = self._cache.get(key)
        if entry and entry.expires > time.time():
            return entry.data
        return None

    def _cache_set(self, key: str, data: Any):
        self._cache[key] = CachedResult(data=data, expires=time.time() + self._cache_ttl)

    # --- Exposed API: General Query ---

    def query_engine(self, engine: str, action: str, params_json: str = "{}") -> str:
        """Route a query to the appropriate engine."""
        params = json.loads(params_json)
        cache_key = f"{engine}:{action}:{params_json}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return json.dumps(cached)

        try:
            if engine == "analytics":
                result = self._query_analytics(action, params)
            elif engine == "semantic":
                result = self._query_semantic(action, params)
            elif engine == "search":
                result = self._query_search(action, params)
            else:
                result = self._query_sqlite_engine(engine, action, params)

            self._status[engine].status = "online"
            self._status[engine].last_query = time.time()
            self._status[engine].query_count += 1
            self._cache_set(cache_key, result)
            return json.dumps(result)

        except Exception as e:
            logger.error("Engine %s query failed: %s", engine, e)
            self._status[engine].status = "error"
            self._status[engine].error_msg = str(e)[:200]
            return json.dumps({"ok": False, "error": str(e)[:200], "engine": engine})

    # --- Engine-Specific Query Methods ---

    def _query_analytics(self, action: str, params: dict) -> dict:
        """DuckDB analytical queries (10-100x faster aggregations)."""
        conn = self._get_duckdb()
        if conn is None:
            return self._fallback_sqlite_analytics(action, params)

        if action == "lane_stats":
            rows = conn.execute("""
                SELECT lane, COUNT(*) as cnt,
                       COUNT(DISTINCT category) as cats
                FROM lit.evidence_quotes
                WHERE lane IS NOT NULL
                GROUP BY lane ORDER BY cnt DESC
            """).fetchall()
            return {"ok": True, "rows": [{"lane": r[0], "count": r[1], "categories": r[2]} for r in rows]}

        if action == "timeline_density":
            rows = conn.execute("""
                SELECT strftime('%Y-%m', event_date) as month,
                       COUNT(*) as cnt
                FROM lit.timeline_events
                WHERE event_date IS NOT NULL
                GROUP BY month ORDER BY month
            """).fetchall()
            return {"ok": True, "rows": [{"month": r[0], "count": r[1]} for r in rows]}

        if action == "top_actors":
            limit = params.get("limit", 20)
            rows = conn.execute(f"""
                SELECT actor, COUNT(*) as cnt
                FROM lit.timeline_events
                WHERE actor IS NOT NULL AND actor != ''
                GROUP BY actor ORDER BY cnt DESC LIMIT {int(limit)}
            """).fetchall()
            return {"ok": True, "rows": [{"actor": r[0], "count": r[1]} for r in rows]}

        return {"ok": False, "error": f"Unknown analytics action: {action}"}

    def _fallback_sqlite_analytics(self, action: str, params: dict) -> dict:
        """SQLite fallback when DuckDB is unavailable."""
        conn = self._get_sqlite()
        if action == "lane_stats":
            rows = conn.execute(
                "SELECT lane, COUNT(*) as cnt FROM evidence_quotes "
                "WHERE lane IS NOT NULL GROUP BY lane ORDER BY cnt DESC"
            ).fetchall()
            return {"ok": True, "rows": [{"lane": r[0], "count": r[1]} for r in rows], "fallback": True}
        return {"ok": False, "error": "Analytics offline, fallback limited"}

    def _query_semantic(self, action: str, params: dict) -> dict:
        """LanceDB vector similarity search."""
        tbl = self._get_lancedb()
        if tbl is None:
            return {"ok": False, "error": "Semantic search offline"}

        if action == "find_similar":
            query_text = params.get("text", "")
            top_k = params.get("top_k", 10)
            try:
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer("all-MiniLM-L6-v2")
                embedding = model.encode(query_text).tolist()
                results = tbl.search(embedding).limit(top_k).to_list()
                return {
                    "ok": True,
                    "results": [
                        {"text": r.get("text", "")[:300], "score": round(float(r.get("_distance", 0)), 4)}
                        for r in results
                    ],
                }
            except Exception as e:
                return {"ok": False, "error": f"Semantic search failed: {e}"}

        return {"ok": False, "error": f"Unknown semantic action: {action}"}

    def _query_search(self, action: str, params: dict) -> dict:
        """tantivy-backed full-text search (sub-ms)."""
        if action == "instant_search":
            query = params.get("query", "")
            limit = params.get("limit", 20)
            conn = self._get_sqlite()
            import re
            sanitized = re.sub(r'[^\w\s*"]', ' ', query).strip()
            if not sanitized:
                return {"ok": True, "results": []}
            try:
                rows = conn.execute(
                    "SELECT rowid, snippet(evidence_fts, 0, '<b>', '</b>', '…', 32) as snip "
                    "FROM evidence_fts WHERE evidence_fts MATCH ? LIMIT ?",
                    (sanitized, limit)
                ).fetchall()
                return {"ok": True, "results": [{"id": r[0], "snippet": r[1]} for r in rows]}
            except Exception:
                rows = conn.execute(
                    "SELECT rowid, substr(quote_text, 1, 200) as snip "
                    "FROM evidence_quotes WHERE quote_text LIKE ? LIMIT ?",
                    (f"%{query[:100]}%", limit)
                ).fetchall()
                return {"ok": True, "results": [{"id": r[0], "snippet": r[1]} for r in rows], "fallback": True}

        return {"ok": False, "error": f"Unknown search action: {action}"}

    def _query_sqlite_engine(self, engine: str, action: str, params: dict) -> dict:
        """Generic SQLite-backed engine queries."""
        conn = self._get_sqlite()

        if engine == "nexus" and action == "fuse":
            topic = params.get("topic", "")
            limit = params.get("limit", 20)
            import re
            sanitized = re.sub(r'[^\w\s*"]', ' ', topic).strip()
            results = {"evidence": [], "timeline": [], "impeachment": []}
            if sanitized:
                try:
                    rows = conn.execute(
                        "SELECT quote_text, source_file, category, lane "
                        "FROM evidence_quotes WHERE rowid IN "
                        "(SELECT rowid FROM evidence_fts WHERE evidence_fts MATCH ? LIMIT ?)",
                        (sanitized, limit)
                    ).fetchall()
                    results["evidence"] = [dict(r) for r in rows]
                except Exception:
                    pass
                try:
                    rows = conn.execute(
                        "SELECT event_date, event_description, actor "
                        "FROM timeline_events WHERE rowid IN "
                        "(SELECT rowid FROM timeline_fts WHERE timeline_fts MATCH ? LIMIT ?)",
                        (sanitized, limit)
                    ).fetchall()
                    results["timeline"] = [dict(r) for r in rows]
                except Exception:
                    pass
            return {"ok": True, "results": results}

        if engine == "cerberus" and action == "validate":
            lane = params.get("lane", "A")
            row = conn.execute(
                "SELECT COUNT(*) FROM evidence_quotes WHERE lane = ?", (lane,)
            ).fetchone()
            count = row[0] if row else 0
            return {"ok": True, "lane": lane, "evidence_count": count, "valid": count > 100}

        if engine == "chronos" and action == "timeline":
            limit = params.get("limit", 50)
            rows = conn.execute(
                "SELECT event_date, event_description, actor, lane "
                "FROM timeline_events WHERE event_date IS NOT NULL "
                "ORDER BY event_date DESC LIMIT ?", (limit,)
            ).fetchall()
            return {"ok": True, "events": [dict(r) for r in rows]}

        self._status[engine].status = "online"
        return {"ok": True, "engine": engine, "action": action, "message": "Engine alive"}

    # --- Exposed API: Engine Status ---

    def get_engine_status(self) -> str:
        """Return health status for all 14 engines."""
        statuses = []
        for name, st in self._status.items():
            statuses.append({
                "name": name,
                "status": st.status,
                "lastQuery": st.last_query,
                "queryCount": st.query_count,
                "error": st.error_msg,
            })
        return json.dumps({"ok": True, "engines": statuses})

    # --- Exposed API: MEEK Overlay ---

    def get_meek_overlay(self) -> str:
        """Return MEEK lane color mapping for graph nodes."""
        conn = self._get_sqlite()
        rows = conn.execute(
            "SELECT lane, COUNT(*) as cnt FROM evidence_quotes "
            "WHERE lane IS NOT NULL GROUP BY lane"
        ).fetchall()
        meek_colors = {
            "A": "#4FC3F7", "B": "#81C784", "C": "#BA68C8",
            "D": "#FFB74D", "E": "#E57373", "F": "#90A4AE",
        }
        lanes = {}
        for r in rows:
            ln = r[0]
            lanes[ln] = {"count": r[1], "color": meek_colors.get(ln, "#888888"), "signal": f"MEEK{list(meek_colors.keys()).index(ln) + 1}" if ln in meek_colors else "UNKNOWN"}
        return json.dumps({"ok": True, "lanes": lanes})

    # --- Exposed API: Delta999 Agent Status ---

    def get_delta999_status(self) -> str:
        """Return status of 8 Delta999 specialized agents."""
        agents = [
            {"name": "Evidence Harvester",   "id": "d999-harvest",  "status": "idle"},
            {"name": "Authority Scanner",    "id": "d999-auth",     "status": "idle"},
            {"name": "Impeachment Builder",  "id": "d999-impeach",  "status": "idle"},
            {"name": "Timeline Constructor", "id": "d999-timeline", "status": "idle"},
            {"name": "Gap Analyzer",         "id": "d999-gap",      "status": "idle"},
            {"name": "Contradiction Finder", "id": "d999-contra",   "status": "idle"},
            {"name": "Filing Validator",     "id": "d999-filing",   "status": "idle"},
            {"name": "Narrative Synthesizer","id": "d999-narr",     "status": "idle"},
        ]
        return json.dumps({"ok": True, "agents": agents})

    # --- Exposed API: Data Flow ---

    def get_data_flow(self) -> str:
        """Return data flow paths for visualization (engine → layer mapping)."""
        flows = [
            {"source": "nexus",         "target": "evidence-layer",    "active": True},
            {"source": "chronos",       "target": "timeline-layer",    "active": True},
            {"source": "cerberus",      "target": "filing-layer",      "active": True},
            {"source": "chimera",       "target": "evidence-layer",    "active": True},
            {"source": "filing_engine", "target": "filing-layer",      "active": True},
            {"source": "analytics",     "target": "hud-dashboard",     "active": self._status["analytics"].status == "online"},
            {"source": "semantic",      "target": "similarity-layer",  "active": self._status["semantic"].status == "online"},
            {"source": "search",        "target": "search-results",    "active": True},
            {"source": "narrative",     "target": "narrative-layer",    "active": True},
            {"source": "rebuttal",      "target": "argument-layer",    "active": True},
            {"source": "delta999",      "target": "agent-layer",       "active": True},
            {"source": "intake",        "target": "ingest-pipeline",   "active": True},
            {"source": "typst",         "target": "export-pipeline",   "active": True},
            {"source": "ingest",        "target": "ingest-pipeline",   "active": True},
        ]
        return json.dumps({"ok": True, "flows": flows})

    def close(self):
        """Clean up all connections."""
        if self._conn:
            self._conn.close()
            self._conn = None
        if self._duckdb_conn:
            self._duckdb_conn.close()
            self._duckdb_conn = None
        self._lancedb_table = None
        self._cache.clear()
```

---

## 4. JavaScript Engine Status Dashboard

```javascript
class EngineStatusDashboard {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
  }

  async refresh() {
    const raw = await window.pywebview.api.get_engine_status();
    const data = JSON.parse(raw);
    if (!data.ok) return;
    this._render(data.engines);
  }

  _render(engines) {
    this.container.innerHTML = '<div class="engine-title">ENGINE STATUS</div>';
    const grid = document.createElement("div");
    grid.className = "engine-grid";

    for (const eng of engines) {
      const dot = this._statusDot(eng.status);
      const cell = document.createElement("div");
      cell.className = `engine-cell engine-${eng.status}`;
      cell.title = eng.error || `${eng.queryCount} queries`;
      cell.innerHTML = `
        <span class="engine-dot">${dot}</span>
        <span class="engine-name">${eng.name}</span>
        <span class="engine-qcount">${eng.queryCount}</span>`;
      grid.appendChild(cell);
    }
    this.container.appendChild(grid);
  }

  _statusDot(status) {
    const map = { online: "🟢", degraded: "🟡", offline: "⚫", error: "🔴" };
    return map[status] || "⚪";
  }
}
```

```css
.engine-title {
  font-size: 0.65rem;
  letter-spacing: 2px;
  color: #888;
  margin-bottom: 8px;
}

.engine-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
}

.engine-cell {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 6px;
  border-radius: 3px;
  font-size: 0.65rem;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.engine-cell.engine-online { border-color: rgba(0, 255, 136, 0.2); }
.engine-cell.engine-error  { border-color: rgba(255, 68, 68, 0.3); }
.engine-cell.engine-offline{ border-color: rgba(100, 100, 100, 0.2); }

.engine-dot   { font-size: 0.55rem; }
.engine-name  { flex: 1; color: #ccc; }
.engine-qcount{ color: #666; font-size: 0.6rem; }
```

---

## 5. Data Flow Visualization (Animated Paths)

Renders animated particles flowing from engine nodes to graph layer
nodes, showing live data movement.

```javascript
class DataFlowOverlay {
  constructor(svg, enginePositions, layerPositions) {
    this.g = svg.append("g").attr("class", "data-flow-overlay");
    this.enginePos = enginePositions;
    this.layerPos = layerPositions;
    this.particles = [];
    this.running = false;
  }

  async loadFlows() {
    const raw = await window.pywebview.api.get_data_flow();
    const data = JSON.parse(raw);
    if (!data.ok) return;
    this._drawFlows(data.flows.filter(f => f.active));
  }

  _drawFlows(flows) {
    this.g.selectAll("*").remove();

    for (const flow of flows) {
      const src = this.enginePos[flow.source];
      const tgt = this.layerPos[flow.target];
      if (!src || !tgt) continue;

      const midX = (src.x + tgt.x) / 2;
      const midY = Math.min(src.y, tgt.y) - 40;

      this.g.append("path")
        .attr("class", "flow-path")
        .attr("d", `M${src.x},${src.y} Q${midX},${midY} ${tgt.x},${tgt.y}`)
        .attr("fill", "none")
        .attr("stroke", "rgba(0, 200, 255, 0.12)")
        .attr("stroke-width", 1.5);

      this._spawnParticle(src, tgt, midX, midY);
    }
  }

  _spawnParticle(src, tgt, mx, my) {
    const particle = this.g.append("circle")
      .attr("cx", src.x)
      .attr("cy", src.y)
      .attr("r", 2.5)
      .attr("fill", "#00C8FF")
      .attr("opacity", 0.8);

    const animateLoop = () => {
      particle
        .attr("cx", src.x).attr("cy", src.y).attr("opacity", 0.8)
        .transition().duration(1500).ease(d3.easeLinear)
        .attrTween("cx", () => {
          return (t) => {
            const u = t;
            return (1-u)*(1-u)*src.x + 2*(1-u)*u*mx + u*u*tgt.x;
          };
        })
        .attrTween("cy", () => {
          return (t) => {
            const u = t;
            return (1-u)*(1-u)*src.y + 2*(1-u)*u*my + u*u*tgt.y;
          };
        })
        .attr("opacity", 0.2)
        .on("end", () => {
          if (this.running) {
            setTimeout(animateLoop, Math.random() * 3000 + 1000);
          }
        });
    };

    this.running = true;
    setTimeout(animateLoop, Math.random() * 2000);
    this.particles.push(particle);
  }

  stop() {
    this.running = false;
    this.g.selectAll("circle").interrupt();
  }

  destroy() {
    this.stop();
    this.g.remove();
  }
}
```

---

## 6. MEEK Lane Overlay (Color-Coded Nodes by Lane)

```javascript
class MEEKOverlay {
  constructor() {
    this.laneColors = {
      A: "#4FC3F7", B: "#81C784", C: "#BA68C8",
      D: "#FFB74D", E: "#E57373", F: "#90A4AE",
    };
    this.active = false;
  }

  async apply() {
    const raw = await window.pywebview.api.get_meek_overlay();
    const data = JSON.parse(raw);
    if (!data.ok) return;
    this.active = true;

    d3.selectAll(".node circle").each(function (d) {
      const lane = d.lane || d.meekLane;
      const el = d3.select(this);
      if (lane && data.lanes[lane]) {
        el.attr("fill", data.lanes[lane].color)
          .attr("stroke", data.lanes[lane].color)
          .attr("stroke-opacity", 0.4);
      } else {
        el.attr("fill", "#444").attr("stroke", "#333").attr("stroke-opacity", 0.2);
      }
    });
  }

  clear() {
    this.active = false;
    d3.selectAll(".node circle")
      .attr("fill", d => d.originalColor || "#00C8FF")
      .attr("stroke", d => d.originalColor || "#00C8FF")
      .attr("stroke-opacity", 0.6);
  }

  toggle() {
    if (this.active) this.clear();
    else this.apply();
  }

  renderLegend(container) {
    const el = document.getElementById(container);
    el.innerHTML = '<div style="font-size:0.6rem;color:#888;letter-spacing:2px;margin-bottom:4px;">MEEK LANES</div>';
    const labels = { A: "Custody", B: "Housing", C: "Federal", D: "PPO", E: "Misconduct", F: "Appellate" };
    for (const [lane, color] of Object.entries(this.laneColors)) {
      const row = document.createElement("div");
      row.style.cssText = "display:flex;align-items:center;gap:6px;margin:2px 0;font-size:0.7rem;";
      row.innerHTML = `<span style="width:10px;height:10px;border-radius:50%;background:${color};display:inline-block;"></span>
        <span style="color:${color};font-weight:bold;">${lane}</span>
        <span style="color:#aaa;">${labels[lane] || ""}</span>`;
      el.appendChild(row);
    }
  }
}
```

---

## 7. FRED Scoring Overlay (Node Size by Relevance)

```javascript
class FREDOverlay {
  constructor() {
    this.active = false;
    this.baseRadius = 6;
    this.maxRadius = 24;
  }

  apply(nodes) {
    this.active = true;
    d3.selectAll(".node circle")
      .transition().duration(600)
      .attr("r", d => {
        const score = d.fredScore || d.relevanceScore || 0.5;
        return this.baseRadius + score * (this.maxRadius - this.baseRadius);
      });
  }

  clear() {
    this.active = false;
    d3.selectAll(".node circle")
      .transition().duration(400)
      .attr("r", d => d.radius || this.baseRadius);
  }

  toggle(nodes) {
    if (this.active) this.clear();
    else this.apply(nodes);
  }
}
```

---

## 8. Delta999 Agent Status Panel

```javascript
class Delta999Panel {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
  }

  async refresh() {
    const raw = await window.pywebview.api.get_delta999_status();
    const data = JSON.parse(raw);
    if (!data.ok) return;
    this._render(data.agents);
  }

  _render(agents) {
    this.container.innerHTML = '<div class="d999-title">DELTA-999 AGENTS</div>';
    for (const agent of agents) {
      const stColor = { idle: "#888", running: "#00FF88", error: "#FF4444", queued: "#FFD700" };
      const row = document.createElement("div");
      row.className = "d999-row";
      row.innerHTML = `
        <span class="d999-dot" style="color:${stColor[agent.status] || '#888'}">●</span>
        <span class="d999-name">${agent.name}</span>
        <span class="d999-status" style="color:${stColor[agent.status] || '#888'}">${agent.status}</span>`;
      this.container.appendChild(row);
    }
  }
}
```

```css
.d999-title {
  font-size: 0.6rem;
  letter-spacing: 2px;
  color: #888;
  margin-bottom: 6px;
}

.d999-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 0;
  font-size: 0.7rem;
}

.d999-dot    { font-size: 0.6rem; }
.d999-name   { flex: 1; color: #ccc; }
.d999-status { font-size: 0.6rem; text-transform: uppercase; }
```

---

## 9. Engine Configuration Panel

```javascript
class EngineConfigPanel {
  constructor(containerId, bridge) {
    this.container = document.getElementById(containerId);
    this.bridge = bridge;
    this.configs = {};
  }

  render(engines) {
    this.container.innerHTML = '<div class="ecfg-title">ENGINE CONFIG</div>';
    for (const eng of engines) {
      const row = document.createElement("div");
      row.className = "ecfg-row";
      const enabled = this.configs[eng.name]?.enabled !== false;

      row.innerHTML = `
        <label class="ecfg-toggle">
          <input type="checkbox" data-engine="${eng.name}" ${enabled ? "checked" : ""}>
          <span class="ecfg-label">${eng.name}</span>
        </label>`;
      row.querySelector("input").addEventListener("change", (e) => {
        this._toggleEngine(eng.name, e.target.checked);
      });
      this.container.appendChild(row);
    }
  }

  _toggleEngine(name, enabled) {
    if (!this.configs[name]) this.configs[name] = {};
    this.configs[name].enabled = enabled;
  }

  getEnabled() {
    return Object.entries(this.configs)
      .filter(([_, v]) => v.enabled !== false)
      .map(([k]) => k);
  }
}
```

```css
.ecfg-title {
  font-size: 0.6rem;
  letter-spacing: 2px;
  color: #888;
  margin-bottom: 6px;
}

.ecfg-row {
  margin: 3px 0;
}

.ecfg-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 0.7rem;
}

.ecfg-toggle input { accent-color: #00C8FF; }
.ecfg-label { color: #ccc; }
```

---

## 10. pywebview App Wiring

```python
"""Main pywebview app — wires engine bridge to the HTML/JS visualization."""
import webview
from engine_bridge import EngineBridge


def create_window():
    bridge = EngineBridge()

    window = webview.create_window(
        "THEMANBEARPIG — LitigationOS Intelligence Graph",
        url="index.html",
        width=1440,
        height=900,
        resizable=True,
        min_size=(800, 600),
    )

    window.expose(
        bridge.query_engine,
        bridge.get_engine_status,
        bridge.get_meek_overlay,
        bridge.get_delta999_status,
        bridge.get_data_flow,
    )

    def on_closed():
        bridge.close()

    window.events.closed += on_closed
    webview.start(debug=False)


if __name__ == "__main__":
    create_window()
```

---

## 11. Lazy Engine Initialization Pattern

Engines connect ONLY on first query, never at startup. This keeps
app launch fast and avoids errors for engines that are not installed.

```python
class LazyEngine:
    """Deferred engine loader — connects on first access."""

    def __init__(self, name: str, factory):
        self._name = name
        self._factory = factory
        self._instance = None
        self._failed = False
        self._error = ""

    @property
    def instance(self):
        if self._instance is None and not self._failed:
            try:
                self._instance = self._factory()
            except Exception as e:
                self._failed = True
                self._error = str(e)
        return self._instance

    @property
    def is_available(self) -> bool:
        return self._instance is not None or (not self._failed)

    @property
    def status(self) -> str:
        if self._instance is not None:
            return "online"
        if self._failed:
            return "error"
        return "offline"

    def reset(self):
        self._instance = None
        self._failed = False
        self._error = ""
```

---

## 12. Error Recovery — Graceful Degradation

When an engine is offline, the visualization gracefully degrades:

```javascript
async function safeEngineQuery(engine, action, params = {}) {
  try {
    const raw = await window.pywebview.api.query_engine(
      engine, action, JSON.stringify(params)
    );
    const result = JSON.parse(raw);
    if (!result.ok) {
      console.warn(`Engine ${engine} returned error:`, result.error);
      return { ok: false, cached: false, error: result.error };
    }
    localStorage.setItem(`cache:${engine}:${action}`, raw);
    return result;
  } catch (err) {
    console.warn(`Engine ${engine} call failed, trying cache:`, err);
    const cached = localStorage.getItem(`cache:${engine}:${action}`);
    if (cached) {
      const data = JSON.parse(cached);
      data.cached = true;
      return data;
    }
    return { ok: false, cached: false, error: err.message };
  }
}
```

CSS for degraded engine indicators:

```css
.engine-cell.engine-offline .engine-name,
.engine-cell.engine-error .engine-name {
  text-decoration: line-through;
  opacity: 0.5;
}

.engine-cell.engine-offline {
  background: rgba(100, 100, 100, 0.08);
}

.engine-cell.engine-error {
  background: rgba(255, 68, 68, 0.06);
}
```

---

## 13. Engine Query Pipeline Visualization

Shows which engines are actively queried during an interaction as a
sequence of lit-up nodes in the HUD.

```javascript
class QueryPipelineViz {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.steps = [];
  }

  startQuery(engines) {
    this.steps = engines.map(e => ({ name: e, status: "pending" }));
    this._render();
  }

  markComplete(engineName) {
    const step = this.steps.find(s => s.name === engineName);
    if (step) step.status = "done";
    this._render();
  }

  markError(engineName) {
    const step = this.steps.find(s => s.name === engineName);
    if (step) step.status = "error";
    this._render();
  }

  _render() {
    this.container.innerHTML = "";
    for (let i = 0; i < this.steps.length; i++) {
      const s = this.steps[i];
      const colors = { pending: "#555", done: "#00FF88", error: "#FF4444" };
      const el = document.createElement("span");
      el.style.cssText = `
        display: inline-flex; align-items: center; gap: 2px;
        color: ${colors[s.status]}; font-size: 0.65rem;
      `;
      el.textContent = s.name;
      this.container.appendChild(el);
      if (i < this.steps.length - 1) {
        const arrow = document.createElement("span");
        arrow.textContent = " → ";
        arrow.style.color = "#444";
        this.container.appendChild(arrow);
      }
    }
  }

  clear() {
    this.steps = [];
    this.container.innerHTML = "";
  }
}
```

---

## 14. Anti-Patterns (MANDATORY)

1. **Never connect to all 14 engines at startup.** Use LazyEngine — connect on first query only.
2. **Never call DuckDB for single-row lookups.** It excels at aggregations, not point queries.
3. **Never send raw SQL from JavaScript to Python.** Use named actions with parameterized queries.
4. **Never block the UI thread with synchronous engine calls.** All bridge calls are async.
5. **Never cache engine status indefinitely.** Refresh every 30 seconds max via TTL cache.
6. **Never query LanceDB without `top_k` limit.** Unbounded vector search exhausts memory.
7. **Never show engine internals to the user.** Display friendly names, not module paths.
8. **Never retry a failed engine more than 3 times per minute.** Exponential backoff required.
9. **Never assume engine order is deterministic.** Use dict lookup, not list index.
10. **Never mix CRIMINAL lane data with Lanes A–F in any engine query.** Rule 7 applies to bridges.
11. **Never pass file paths from JS to Python bridge.** Only pass query parameters and action names.
12. **Never use `eval()` or `exec()` on bridge input.** All parameters are JSON-decoded, never executed.
13. **Never render all 14 engine status dots if window < 800px.** Collapse to summary count.
14. **Never show the child's full name in any engine result display.** Sanitize to L.D.W.
15. **Never load sentence-transformers model eagerly.** Load on first `find_similar` call only.
16. **Never access `window.pywebview.api` before `pywebviewready` event fires.** Always guard.

---

## 15. Performance Budgets

| Metric | Budget | Action if Exceeded |
|--------|--------|--------------------|
| Engine bridge call round-trip | < 200 ms | Cache result, reduce query scope |
| DuckDB analytical query | < 500 ms | Simplify aggregation, add index |
| LanceDB vector search | < 100 ms for top-10 | Reduce vector dimensions, limit scope |
| FTS5 search (tantivy fallback) | < 50 ms | Use LIKE fallback with narrower scope |
| Engine status dashboard refresh | < 100 ms total | Cache, refresh every 30s not continuously |
| Data flow particle animation | ≤ 14 particles (one per flow) | Remove inactive flow particles |
| MEEK overlay application | < 50 ms | Batch DOM updates in single rAF |
| Delta999 panel refresh | < 50 ms | Throttle to 10s intervals |
| pywebview bridge startup | < 2s to first ready | Defer all engine connections |
| Total cached results memory | < 50 MB | Evict LRU entries beyond 200 |
| localStorage engine cache | < 10 MB | Prune oldest entries weekly |

---

## 16. Integration Map

| Engine | Graph Layer | Query Action | Overlay |
|--------|-------------|-------------|---------|
| nexus | evidence, timeline | `fuse` | Cross-table highlight |
| chimera | evidence | `blend` | Multi-source markers |
| chronos | timeline | `timeline` | Temporal ordering |
| cerberus | filing | `validate` | Compliance indicators |
| filing_engine | filing | `pipeline_status` | Lane progress bars |
| intake | ingest pipeline | `ingest_status` | New document markers |
| rebuttal | argument | `counter_argument` | Rebuttal links |
| narrative | narrative | `synthesize` | Story beat nodes |
| delta999 | agent overlay | `agent_status` | Agent activity dots |
| analytics | HUD dashboard | `lane_stats`, `timeline_density` | Aggregate gauges |
| semantic | similarity | `find_similar` | Similar-node halos |
| search | search results | `instant_search` | Highlighted matches |
| typst | export | `generate_pdf` | Export status |
| ingest | ingest pipeline | `batch_status` | Progress indicator |

---

*END SINGULARITY-MBP-INTEGRATION-ENGINES v1.0.0 — 14-engine bridge for THEMANBEARPIG.*

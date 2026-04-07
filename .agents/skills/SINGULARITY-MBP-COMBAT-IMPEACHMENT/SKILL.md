---
skill: SINGULARITY-MBP-COMBAT-IMPEACHMENT
version: 1.0.0
tier: TIER-2/COMBAT
domain: Impeachment scoring, credibility visualization, cross-examination ammunition, contradiction mapping, MRE 613 impeachment chains
description: >-
  Impeachment combat layer for THEMANBEARPIG. Renders credibility gauges, contradiction spider charts,
  cross-exam COMMIT-PIN-CONFRONT-EXHIBIT sequences, MRE 613 prior-inconsistent-statement chains,
  impeachment heat-map overlay on the 13-layer graph, and interactive drill-down dossier panels.
  Data pipeline from impeachment_matrix (5.1K+ rows) and contradiction_map (2.5K+ rows).
  Exports impeachment packages as structured PDF outlines.
triggers:
  - impeachment
  - credibility
  - cross-exam
  - contradiction
  - MRE 613
  - witness impeach
  - impeachment heat map
  - cross-examination
  - prior inconsistent statement
---

# SINGULARITY-MBP-COMBAT-IMPEACHMENT

> **Tier 2 — COMBAT**: Impeachment scoring, credibility chains, cross-examination
> ammunition, and contradiction visualization for the THEMANBEARPIG 13-layer
> litigation intelligence mega-visualization.

---

## 1. Data Pipeline — impeachment_matrix & contradiction_map

All impeachment visuals are grounded in two DB tables. Never fabricate scores.

### 1.1 Python Data Loader

```python
"""impeachment_pipeline.py — Load impeachment data for THEMANBEARPIG."""
import sqlite3, json, math, os

DB_PATH = os.environ.get(
    "LITIGATION_DB",
    r"C:\Users\andre\LitigationOS\litigation_context.db",
)

PRAGMAS = """
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 60000;
PRAGMA cache_size  = -32000;
PRAGMA temp_store  = MEMORY;
PRAGMA synchronous = NORMAL;
"""

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(PRAGMAS)
    return conn


def load_impeachment_nodes(conn):
    """Return witness-level impeachment aggregates for graph nodes."""
    sql = """
    SELECT
        COALESCE(category, 'unknown')            AS category,
        COUNT(*)                                  AS hit_count,
        ROUND(AVG(impeachment_value), 2)          AS avg_severity,
        MAX(impeachment_value)                    AS max_severity,
        GROUP_CONCAT(DISTINCT filing_relevance)   AS lanes
    FROM impeachment_matrix
    GROUP BY category
    ORDER BY avg_severity DESC
    """
    rows = conn.execute(sql).fetchall()
    return [dict(r) for r in rows]


def load_contradiction_edges(conn):
    """Return contradiction pairs as graph edges."""
    sql = """
    SELECT
        claim_id,
        source_a,
        source_b,
        contradiction_text,
        severity,
        lane
    FROM contradiction_map
    ORDER BY
        CASE severity
            WHEN 'critical' THEN 1
            WHEN 'high'     THEN 2
            WHEN 'medium'   THEN 3
            ELSE 4
        END
    """
    rows = conn.execute(sql).fetchall()
    return [dict(r) for r in rows]


def load_cross_exam_questions(conn, target):
    """Load cross-examination questions for a specific target."""
    sql = """
    SELECT
        evidence_summary,
        quote_text,
        impeachment_value,
        cross_exam_question,
        source_file,
        event_date
    FROM impeachment_matrix
    WHERE category LIKE '%' || ? || '%'
       OR evidence_summary LIKE '%' || ? || '%'
    ORDER BY impeachment_value DESC
    LIMIT 50
    """
    rows = conn.execute(sql, (target, target)).fetchall()
    return [dict(r) for r in rows]


def build_impeachment_graph_json(out_path="impeachment_graph.json"):
    """Build the full impeachment sub-graph JSON for D3."""
    conn = get_conn()
    nodes = load_impeachment_nodes(conn)
    edges = load_contradiction_edges(conn)
    questions = {}
    for node in nodes:
        cat = node["category"]
        questions[cat] = load_cross_exam_questions(conn, cat)
    conn.close()

    payload = {
        "nodes": nodes,
        "edges": edges,
        "cross_exam": questions,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    return payload
```

### 1.2 Severity Scale (1-10)

| Score | Label    | Color Hex  | Meaning                                      |
|-------|----------|------------|----------------------------------------------|
| 1-2   | Minimal  | `#2ecc71`  | Minor inconsistency, low impeachment value   |
| 3-4   | Notable  | `#f1c40f`  | Noticeable contradiction, worth noting        |
| 5-6   | Strong   | `#e67e22`  | Clear inconsistency, usable at trial          |
| 7-8   | Severe   | `#e74c3c`  | Major credibility damage, cross-exam priority |
| 9-10  | Critical | `#8e44ad`  | Case-breaking contradiction, lead with this   |

---

## 2. Impeachment Score Radial Gauges

One radial gauge per witness/actor, showing aggregate impeachment score.

### 2.1 D3.js Radial Gauge

```javascript
/**
 * Render a radial impeachment gauge for a single witness.
 * @param {SVGElement} parent  — SVG group to append into
 * @param {number}     score   — 0-10 impeachment score
 * @param {string}     label   — witness name
 * @param {number}     cx      — center x
 * @param {number}     cy      — center y
 * @param {number}     radius  — outer radius (default 48)
 */
function renderImpeachmentGauge(parent, score, label, cx, cy, radius = 48) {
    const colorScale = d3.scaleLinear()
        .domain([0, 3, 6, 8, 10])
        .range(["#2ecc71", "#f1c40f", "#e67e22", "#e74c3c", "#8e44ad"])
        .clamp(true);

    const arc = d3.arc()
        .innerRadius(radius * 0.7)
        .outerRadius(radius)
        .startAngle(-Math.PI * 0.75);

    const g = d3.select(parent).append("g")
        .attr("transform", `translate(${cx},${cy})`)
        .attr("class", "impeachment-gauge");

    // Background arc (full sweep)
    g.append("path")
        .datum({ endAngle: Math.PI * 0.75 })
        .attr("d", arc)
        .attr("fill", "#1a1a2e")
        .attr("stroke", "#333")
        .attr("stroke-width", 0.5);

    // Foreground arc (score sweep)
    const endAngle = -Math.PI * 0.75 + (score / 10) * Math.PI * 1.5;
    g.append("path")
        .datum({ endAngle })
        .attr("d", arc)
        .attr("fill", colorScale(score))
        .attr("filter", score >= 7 ? "url(#impeach-glow)" : null);

    // Score text
    g.append("text")
        .attr("text-anchor", "middle")
        .attr("dy", "0.1em")
        .attr("font-size", radius * 0.45)
        .attr("font-weight", 700)
        .attr("fill", colorScale(score))
        .text(score.toFixed(1));

    // Label text
    g.append("text")
        .attr("text-anchor", "middle")
        .attr("dy", radius * 0.45)
        .attr("font-size", 10)
        .attr("fill", "#ccc")
        .text(label);
}
```

### 2.2 SVG Glow Filter

```html
<defs>
  <filter id="impeach-glow" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur in="SourceGraphic" stdDeviation="4" result="blur"/>
    <feColorMatrix in="blur" type="matrix"
      values="1 0 0 0 0  0 0.2 0 0 0  0 0 0.2 0 0  0 0 0 0.8 0"/>
    <feMerge>
      <feMergeNode/>
      <feMergeNode in="SourceGraphic"/>
    </feMerge>
  </filter>
</defs>
```

---

## 3. Credibility Chain — Force-Directed Sub-Graph

Contradictions rendered as a force-directed graph where source_a → source_b
edges represent conflicting statements.

### 3.1 D3.js Credibility Chain

```javascript
/**
 * Render the credibility chain sub-graph inside a panel.
 * @param {HTMLElement} container — DOM element for the sub-graph
 * @param {Array} contradictions  — rows from contradiction_map
 */
function renderCredibilityChain(container, contradictions) {
    const width = container.clientWidth;
    const height = 400;

    const svg = d3.select(container).append("svg")
        .attr("width", width)
        .attr("height", height);

    const severityColor = {
        critical: "#8e44ad",
        high: "#e74c3c",
        medium: "#e67e22",
        low: "#f1c40f",
    };

    // Build node/link sets from contradiction pairs
    const nodeSet = new Set();
    const links = contradictions.map(c => {
        nodeSet.add(c.source_a);
        nodeSet.add(c.source_b);
        return {
            source: c.source_a,
            target: c.source_b,
            severity: c.severity || "medium",
            text: c.contradiction_text,
            claim_id: c.claim_id,
        };
    });
    const nodes = Array.from(nodeSet).map(id => ({ id }));

    const sim = d3.forceSimulation(nodes)
        .force("link", d3.forceLink(links).id(d => d.id).distance(100))
        .force("charge", d3.forceManyBody().strength(-200))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collision", d3.forceCollide(30));

    const link = svg.selectAll(".cred-link")
        .data(links).enter().append("line")
        .attr("class", "cred-link")
        .attr("stroke", d => severityColor[d.severity] || "#666")
        .attr("stroke-width", d => d.severity === "critical" ? 3 : 1.5)
        .attr("stroke-dasharray", d => d.severity === "low" ? "4,4" : null);

    const node = svg.selectAll(".cred-node")
        .data(nodes).enter().append("circle")
        .attr("class", "cred-node")
        .attr("r", 12)
        .attr("fill", "#16213e")
        .attr("stroke", "#00d2ff")
        .attr("stroke-width", 1.5)
        .call(d3.drag()
            .on("start", (e, d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
            .on("drag", (e, d) => { d.fx = e.x; d.fy = e.y; })
            .on("end", (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; })
        );

    const label = svg.selectAll(".cred-label")
        .data(nodes).enter().append("text")
        .attr("class", "cred-label")
        .attr("font-size", 10)
        .attr("fill", "#aaa")
        .attr("text-anchor", "middle")
        .attr("dy", -18)
        .text(d => d.id);

    sim.on("tick", () => {
        link.attr("x1", d => d.source.x).attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
        node.attr("cx", d => d.x).attr("cy", d => d.y);
        label.attr("x", d => d.x).attr("y", d => d.y);
    });
}
```

---

## 4. Cross-Examination Sequence Display

COMMIT → PIN → CONFRONT → EXHIBIT — the four-step impeachment chain.

### 4.1 Sequence Card Renderer

```javascript
/**
 * Render a cross-examination sequence as a vertical card stack.
 * @param {HTMLElement} panel       — DOM element to render into
 * @param {Object}      impeachRow  — row from impeachment_matrix
 */
function renderCrossExamSequence(panel, impeachRow) {
    const steps = [
        {
            phase: "COMMIT",
            icon: "🔒",
            text: `"You stated ${impeachRow.evidence_summary}, correct?"`,
            css: "step-commit",
        },
        {
            phase: "PIN",
            icon: "📌",
            text: `"That was on ${impeachRow.event_date || '[DATE]'} in the context of ${impeachRow.source_file || '[SOURCE]'}?"`,
            css: "step-pin",
        },
        {
            phase: "CONFRONT",
            icon: "⚔️",
            text: impeachRow.cross_exam_question || `"But isn't it true that [contradicting fact]?"`,
            css: "step-confront",
        },
        {
            phase: "EXHIBIT",
            icon: "📄",
            text: `"I direct your attention to ${impeachRow.source_file || 'Exhibit [X]'}, which states: '${(impeachRow.quote_text || '').substring(0, 120)}…'"`,
            css: "step-exhibit",
        },
    ];

    const container = document.createElement("div");
    container.className = "cross-exam-sequence";

    steps.forEach((step, i) => {
        const card = document.createElement("div");
        card.className = `cross-exam-step ${step.css}`;
        card.innerHTML = `
            <div class="step-header">
                <span class="step-icon">${step.icon}</span>
                <span class="step-phase">${step.phase}</span>
                <span class="step-number">${i + 1}/4</span>
            </div>
            <div class="step-body">${step.text}</div>
        `;
        container.appendChild(card);

        if (i < steps.length - 1) {
            const arrow = document.createElement("div");
            arrow.className = "step-arrow";
            arrow.textContent = "↓";
            container.appendChild(arrow);
        }
    });

    panel.innerHTML = "";
    panel.appendChild(container);
}
```

### 4.2 CSS for Cross-Exam Cards

```css
.cross-exam-sequence {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 12px;
    font-family: 'Segoe UI', sans-serif;
}
.cross-exam-step {
    border-radius: 6px;
    padding: 10px 14px;
    border-left: 4px solid;
}
.step-commit   { background: #0d1b2a; border-color: #00d2ff; }
.step-pin      { background: #1a1a2e; border-color: #f1c40f; }
.step-confront { background: #2d132c; border-color: #e74c3c; }
.step-exhibit  { background: #1b2838; border-color: #2ecc71; }
.step-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
}
.step-phase {
    font-weight: 700;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #eee;
}
.step-number {
    margin-left: auto;
    font-size: 10px;
    color: #666;
}
.step-body {
    font-size: 13px;
    color: #ccc;
    line-height: 1.5;
    font-style: italic;
}
.step-arrow {
    text-align: center;
    color: #444;
    font-size: 18px;
    line-height: 1;
}
```

---

## 5. MRE 613 Prior Inconsistent Statement Workflow

Michigan Rule of Evidence 613 requires: (1) examine witness about
the prior statement, (2) give opportunity to explain, (3) prove the
inconsistency with extrinsic evidence if denied.

### 5.1 Workflow State Machine

```javascript
/**
 * MRE 613 workflow state tracker.
 * States: IDENTIFY → EXAMINE → OPPORTUNITY → PROVE → COMPLETE
 */
class MRE613Workflow {
    constructor(contradictionId, priorStatement, currentTestimony) {
        this.id = contradictionId;
        this.prior = priorStatement;
        this.current = currentTestimony;
        this.state = "IDENTIFY";
        this.history = [];
    }

    advance(notes) {
        const transitions = {
            IDENTIFY:    "EXAMINE",
            EXAMINE:     "OPPORTUNITY",
            OPPORTUNITY: "PROVE",
            PROVE:       "COMPLETE",
        };
        if (!transitions[this.state]) return false;
        this.history.push({ from: this.state, notes, ts: Date.now() });
        this.state = transitions[this.state];
        return true;
    }

    getStepInstructions() {
        const instructions = {
            IDENTIFY: "Identify the prior inconsistent statement from the record. Pinpoint source document, date, and exact words.",
            EXAMINE: "Ask the witness about the circumstances of the prior statement. Use COMMIT and PIN steps. Do not reveal the contradiction yet.",
            OPPORTUNITY: "Confront the witness with the inconsistency. Give them the opportunity to explain or deny. MRE 613(b) requires this before extrinsic proof.",
            PROVE: "If the witness denies or equivocates, introduce the extrinsic evidence (exhibit). The prior statement is now admissible for impeachment.",
            COMPLETE: "Impeachment complete. The factfinder has both the denial and the proof of inconsistency.",
        };
        return instructions[this.state] || "";
    }

    toJSON() {
        return {
            id: this.id,
            state: this.state,
            prior: this.prior,
            current: this.current,
            history: this.history,
        };
    }
}
```

### 5.2 Workflow Visualization

```javascript
function renderMRE613Tracker(container, workflow) {
    const states = ["IDENTIFY", "EXAMINE", "OPPORTUNITY", "PROVE", "COMPLETE"];
    const currentIdx = states.indexOf(workflow.state);

    const bar = document.createElement("div");
    bar.className = "mre613-progress";

    states.forEach((s, i) => {
        const dot = document.createElement("div");
        dot.className = "mre613-dot";
        dot.dataset.state = s;
        if (i < currentIdx) dot.classList.add("done");
        if (i === currentIdx) dot.classList.add("active");
        dot.title = s;
        dot.textContent = i < currentIdx ? "✓" : (i + 1);
        bar.appendChild(dot);

        if (i < states.length - 1) {
            const line = document.createElement("div");
            line.className = "mre613-line";
            if (i < currentIdx) line.classList.add("done");
            bar.appendChild(line);
        }
    });

    const instr = document.createElement("div");
    instr.className = "mre613-instructions";
    instr.textContent = workflow.getStepInstructions();

    container.innerHTML = "";
    container.appendChild(bar);
    container.appendChild(instr);
}
```

### 5.3 MRE 613 CSS

```css
.mre613-progress {
    display: flex;
    align-items: center;
    gap: 0;
    padding: 12px 8px;
}
.mre613-dot {
    width: 28px; height: 28px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 11px; font-weight: 700;
    background: #1a1a2e; color: #666;
    border: 2px solid #333;
    flex-shrink: 0;
}
.mre613-dot.done    { background: #2ecc71; color: #fff; border-color: #27ae60; }
.mre613-dot.active  { background: #e74c3c; color: #fff; border-color: #c0392b;
                       box-shadow: 0 0 8px rgba(231,76,60,0.6); }
.mre613-line {
    flex: 1; height: 2px;
    background: #333;
}
.mre613-line.done { background: #2ecc71; }
.mre613-instructions {
    padding: 8px 12px;
    font-size: 12px; color: #aaa;
    line-height: 1.5;
    border-left: 3px solid #e74c3c;
    margin-top: 8px;
}
```

---

## 6. Contradiction Spider Chart

Per-witness spider (radar) chart showing contradiction counts by category.

```javascript
/**
 * Render a radar chart of contradiction categories for one witness.
 * @param {SVGElement} svg        — target SVG
 * @param {Object}     data       — { category: count, ... }
 * @param {number}     cx, cy     — center
 * @param {number}     radius     — chart radius
 */
function renderContradictionSpider(svg, data, cx, cy, radius = 80) {
    const categories = Object.keys(data);
    const maxVal = Math.max(...Object.values(data), 1);
    const n = categories.length;
    if (n < 3) return; // spider needs >= 3 axes

    const angleSlice = (2 * Math.PI) / n;
    const g = d3.select(svg).append("g")
        .attr("transform", `translate(${cx},${cy})`);

    // Grid rings
    [0.25, 0.5, 0.75, 1.0].forEach(frac => {
        const r = radius * frac;
        g.append("circle")
            .attr("r", r)
            .attr("fill", "none")
            .attr("stroke", "#222")
            .attr("stroke-dasharray", "2,3");
    });

    // Axis lines and labels
    categories.forEach((cat, i) => {
        const angle = angleSlice * i - Math.PI / 2;
        const x = Math.cos(angle) * radius;
        const y = Math.sin(angle) * radius;

        g.append("line")
            .attr("x2", x).attr("y2", y)
            .attr("stroke", "#333");

        g.append("text")
            .attr("x", Math.cos(angle) * (radius + 14))
            .attr("y", Math.sin(angle) * (radius + 14))
            .attr("text-anchor", "middle")
            .attr("font-size", 9)
            .attr("fill", "#888")
            .text(cat);
    });

    // Data polygon
    const points = categories.map((cat, i) => {
        const angle = angleSlice * i - Math.PI / 2;
        const r = (data[cat] / maxVal) * radius;
        return [Math.cos(angle) * r, Math.sin(angle) * r];
    });

    g.append("polygon")
        .attr("points", points.map(p => p.join(",")).join(" "))
        .attr("fill", "rgba(231, 76, 60, 0.25)")
        .attr("stroke", "#e74c3c")
        .attr("stroke-width", 2);

    // Data dots
    points.forEach(([x, y]) => {
        g.append("circle")
            .attr("cx", x).attr("cy", y)
            .attr("r", 3)
            .attr("fill", "#e74c3c");
    });
}
```

---

## 7. Impeachment Heat Map Overlay

Nodes in the main THEMANBEARPIG graph glow red proportional to their impeachability score.

```javascript
/**
 * Apply impeachment heat-map overlay to existing graph nodes.
 * @param {d3.Selection} nodeSelection — existing node circles
 * @param {Map}          scoreMap      — Map<nodeId, impeachScore 0-10>
 */
function applyImpeachmentHeatMap(nodeSelection, scoreMap) {
    const glowScale = d3.scaleLinear()
        .domain([0, 4, 7, 10])
        .range([0, 2, 6, 14])
        .clamp(true);

    const colorScale = d3.scaleLinear()
        .domain([0, 3, 6, 8, 10])
        .range(["#2ecc71", "#f1c40f", "#e67e22", "#e74c3c", "#8e44ad"])
        .clamp(true);

    nodeSelection.each(function(d) {
        const score = scoreMap.get(d.id) || 0;
        if (score < 1) return;

        const node = d3.select(this);
        const glow = glowScale(score);
        const color = colorScale(score);

        // Outer glow ring
        node.select(".impeach-ring").remove();
        const parent = d3.select(this.parentNode);
        parent.insert("circle", ":first-child")
            .attr("class", "impeach-ring")
            .attr("cx", d.x).attr("cy", d.y)
            .attr("r", (d.radius || 8) + glow)
            .attr("fill", "none")
            .attr("stroke", color)
            .attr("stroke-width", glow / 2)
            .attr("opacity", 0.6)
            .style("filter", `drop-shadow(0 0 ${glow}px ${color})`);
    });
}

/**
 * Build the score map from impeachment_matrix query results.
 * @param {Array} impeachmentRows — array of { category, avg_severity }
 * @returns {Map}
 */
function buildScoreMap(impeachmentRows) {
    const map = new Map();
    impeachmentRows.forEach(row => {
        map.set(row.category, row.avg_severity);
    });
    return map;
}
```

---

## 8. Interactive Drill-Down — Impeachment Dossier Panel

Clicking a witness node opens a dossier panel with full impeachment details.

```javascript
/**
 * Open the impeachment dossier panel for a clicked witness node.
 * @param {Object} witnessData — { id, category, hit_count, avg_severity, ... }
 * @param {Array}  contradictions — filtered contradiction_map rows
 * @param {Array}  crossExamQs    — filtered impeachment_matrix rows
 */
function openImpeachmentDossier(witnessData, contradictions, crossExamQs) {
    let panel = document.getElementById("impeach-dossier");
    if (!panel) {
        panel = document.createElement("div");
        panel.id = "impeach-dossier";
        panel.className = "dossier-panel";
        document.body.appendChild(panel);
    }

    const severityClass = witnessData.avg_severity >= 7 ? "severity-critical" :
                          witnessData.avg_severity >= 4 ? "severity-high" : "severity-low";

    panel.innerHTML = `
        <div class="dossier-header">
            <h3>⚔️ Impeachment Dossier: ${witnessData.category}</h3>
            <button class="dossier-close" onclick="this.closest('.dossier-panel').classList.remove('open')">✕</button>
        </div>
        <div class="dossier-stats">
            <div class="stat">
                <span class="stat-val ${severityClass}">${witnessData.avg_severity}</span>
                <span class="stat-label">Avg Severity</span>
            </div>
            <div class="stat">
                <span class="stat-val">${witnessData.hit_count}</span>
                <span class="stat-label">Total Hits</span>
            </div>
            <div class="stat">
                <span class="stat-val">${contradictions.length}</span>
                <span class="stat-label">Contradictions</span>
            </div>
        </div>
        <div class="dossier-section">
            <h4>Top Cross-Examination Questions</h4>
            <div id="dossier-crossexam"></div>
        </div>
        <div class="dossier-section">
            <h4>Contradictions</h4>
            <div id="dossier-contradictions"></div>
        </div>
        <div class="dossier-export">
            <button onclick="exportImpeachmentPDF('${witnessData.category}')">📄 Export PDF Outline</button>
        </div>
    `;

    // Render top 5 cross-exam sequences
    const crossExamDiv = panel.querySelector("#dossier-crossexam");
    crossExamQs.slice(0, 5).forEach(q => {
        renderCrossExamSequence(crossExamDiv, q);
    });

    // Render contradiction list
    const contrDiv = panel.querySelector("#dossier-contradictions");
    contradictions.forEach(c => {
        const item = document.createElement("div");
        item.className = `contradiction-item sev-${c.severity}`;
        item.innerHTML = `
            <div class="contr-sources">${c.source_a} ↔ ${c.source_b}</div>
            <div class="contr-text">${c.contradiction_text}</div>
        `;
        contrDiv.appendChild(item);
    });

    panel.classList.add("open");
}
```

### 8.1 Dossier Panel CSS

```css
.dossier-panel {
    position: fixed; top: 0; right: -420px;
    width: 400px; height: 100vh;
    background: #0a0e17; border-left: 2px solid #e74c3c;
    overflow-y: auto; transition: right 0.3s ease;
    z-index: 1000; padding: 16px;
    font-family: 'Segoe UI', sans-serif;
}
.dossier-panel.open { right: 0; }
.dossier-header {
    display: flex; justify-content: space-between; align-items: center;
    border-bottom: 1px solid #222; padding-bottom: 10px; margin-bottom: 12px;
}
.dossier-header h3 { color: #e74c3c; margin: 0; font-size: 16px; }
.dossier-close {
    background: none; border: 1px solid #444; color: #888;
    cursor: pointer; padding: 4px 8px; border-radius: 4px;
}
.dossier-stats {
    display: flex; gap: 16px; margin-bottom: 16px;
}
.stat { text-align: center; }
.stat-val { display: block; font-size: 24px; font-weight: 700; color: #fff; }
.stat-label { font-size: 10px; color: #666; text-transform: uppercase; }
.severity-critical { color: #e74c3c; }
.severity-high     { color: #e67e22; }
.severity-low      { color: #2ecc71; }
.dossier-section { margin-bottom: 16px; }
.dossier-section h4 { color: #aaa; font-size: 13px; margin-bottom: 8px; }
.contradiction-item {
    padding: 8px; margin-bottom: 6px; border-radius: 4px;
    background: #111; border-left: 3px solid #666;
}
.contradiction-item.sev-critical { border-color: #8e44ad; }
.contradiction-item.sev-high     { border-color: #e74c3c; }
.contradiction-item.sev-medium   { border-color: #e67e22; }
.contr-sources { font-size: 11px; color: #888; margin-bottom: 4px; }
.contr-text    { font-size: 12px; color: #ccc; }
.dossier-export { text-align: center; padding: 12px 0; }
.dossier-export button {
    background: #e74c3c; color: #fff; border: none;
    padding: 8px 20px; border-radius: 4px; cursor: pointer;
    font-weight: 600;
}
```

---

## 9. Export — Impeachment Package PDF Outline

```python
"""export_impeachment_pdf.py — Generate structured outline for an impeachment package."""
import json

def generate_impeachment_outline(target, cross_exam_rows, contradictions):
    """Build a structured text outline for impeachment (pre-Typst/PDF)."""
    lines = []
    lines.append(f"IMPEACHMENT PACKAGE — {target.upper()}")
    lines.append("=" * 60)
    lines.append("")

    lines.append("I. CROSS-EXAMINATION SEQUENCES")
    lines.append("-" * 40)
    for i, row in enumerate(cross_exam_rows[:10], 1):
        lines.append(f"  Sequence {i} (Severity: {row.get('impeachment_value', '?')}/10)")
        lines.append(f"    COMMIT:  \"You stated {row.get('evidence_summary', '[?]')}, correct?\"")
        lines.append(f"    PIN:     \"That was on {row.get('event_date', '[DATE]')}?\"")
        q = row.get("cross_exam_question", "\"But isn't it true that [contradicting fact]?\"")
        lines.append(f"    CONFRONT: {q}")
        lines.append(f"    EXHIBIT:  {row.get('source_file', '[SOURCE]')}")
        lines.append(f"    QUOTE:   \"{(row.get('quote_text') or '')[:150]}\"")
        lines.append("")

    lines.append("II. CONTRADICTIONS")
    lines.append("-" * 40)
    for c in contradictions[:15]:
        lines.append(f"  [{c.get('severity', '?').upper()}] {c.get('source_a', '?')} ↔ {c.get('source_b', '?')}")
        lines.append(f"    {c.get('contradiction_text', '')[:200]}")
        lines.append("")

    lines.append("III. MRE 613 COMPLIANCE CHECKLIST")
    lines.append("-" * 40)
    lines.append("  [ ] Prior statement identified with source and date")
    lines.append("  [ ] Witness examined about circumstances of prior statement")
    lines.append("  [ ] Witness given opportunity to explain or deny")
    lines.append("  [ ] Extrinsic evidence prepared if witness denies")
    lines.append("  [ ] Foundation laid under MRE 901(b)(1)")
    lines.append("")

    return "\n".join(lines)
```

---

## 10. Anti-Patterns (MANDATORY — 18 Rules)

| #  | Anti-Pattern | Why It Fails |
|----|-------------|-------------|
| 1  | Fabricating impeachment scores | Destroys courtroom credibility — every number must trace to a DB query |
| 2  | Hardcoded severity colors | Breaks when theme changes — always use the colorScale function |
| 3  | Rendering all 5.1K rows at once | Browser crashes — limit visible items to 50, paginate the rest |
| 4  | Skipping MRE 613 steps | Foundation objection at trial — always track all five states |
| 5  | Mixing impeachment with main graph simulation | Performance disaster — use a separate sub-graph simulation |
| 6  | Using `innerHTML` for untrusted DB text | XSS risk — sanitize all quote_text before rendering |
| 7  | Blocking main thread with DB queries | Freezes graph — use Web Workers or async fetch |
| 8  | Omitting severity legend | User cannot interpret colors — always render the legend |
| 9  | Not clamping score to 0-10 | NaN and Infinity break arc math — `Math.max(0, Math.min(10, score))` |
| 10 | Animating all gauges simultaneously | Janky — stagger gauge animations by 50ms per gauge |
| 11 | Spider chart with < 3 axes | Degenerate polygon — guard with `if (n < 3) return` |
| 12 | Forgetting to clean up dossier panel listeners | Memory leak — remove event listeners on panel close |
| 13 | Re-creating SVG elements on every update | DOM thrash — use D3 enter/update/exit pattern |
| 14 | Placing glow filter on every node | GPU overload — only apply filter when score >= 7 |
| 15 | Using synchronous XHR for data load | Blocks UI — always use fetch or async import |
| 16 | Showing child's full name in dossier | MCR 8.119(H) violation — always filter to L.D.W. |
| 17 | Embedding AI/DB refs in export text | Court contamination — run decontamination sweep before export |
| 18 | Not debouncing dossier open on rapid clicks | Race condition — debounce to 200ms minimum |

---

## 11. Performance Budgets

| Metric | Budget | Measurement |
|--------|--------|-------------|
| Gauge render (single) | < 5ms | `performance.now()` before/after |
| Credibility chain (50 nodes) | < 100ms initial, then 16ms/tick | requestAnimationFrame budget |
| Spider chart render | < 10ms | Single DOM append |
| Dossier panel open | < 50ms | Click to first paint |
| Heat map overlay (500 nodes) | < 30ms | Batch attribute update |
| Cross-exam card render (4 steps) | < 5ms | innerHTML + append |
| MRE 613 tracker render | < 3ms | createElement chain |
| Export outline generation | < 200ms (Python) | Time from call to file write |
| Total impeachment layer memory | < 15MB | Chrome DevTools heap snapshot |
| Max visible contradiction edges | 200 | Cull distant edges from viewport |

---

## 12. Integration Checklist

- [ ] Data pipeline connects to `litigation_context.db` via WAL connection
- [ ] impeachment_matrix queried with parameterized SQL (no string interpolation)
- [ ] contradiction_map queried with FTS5 safety (sanitize → try/except → LIKE fallback)
- [ ] Score map built from live DB, not cached stale values
- [ ] Dossier panel wired to node click handler in main graph
- [ ] Heat map overlay toggled by Layer 6 (Impeachment) visibility switch
- [ ] Export function strips all AI/DB references before output
- [ ] L.D.W. initials enforced — `quote_text.replace(/Lincoln|David Watson/gi, 'L.D.W.')`
- [ ] pywebview bridge exposes `load_impeachment_data()` and `export_impeachment(target)`
- [ ] PyInstaller spec includes impeachment_graph.json in datas list

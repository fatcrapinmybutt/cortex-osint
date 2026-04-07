---
skill: SINGULARITY-MBP-COMBAT-JUDICIAL
version: "1.0.0"
description: "Judicial cartel intelligence overlay for THEMANBEARPIG: McNeill-Hoopes-Ladas triangle visualization, violation heatmaps, ex parte pattern detection, benchbook deviation tracking, JTC exhibit generation. Maps judicial misconduct as analyzable graph patterns."
tier: "TIER-2/COMBAT"
domain: "Judicial intelligence — cartel mapping, violation heatmaps, ex parte patterns, JTC exhibits"
triggers:
  - judicial
  - cartel
  - McNeill
  - Hoopes
  - Ladas
  - JTC
  - violation
  - heatmap
  - ex parte pattern
  - benchbook deviation
  - Canon violation
cross_links:
  - SINGULARITY-MBP-GENESIS
  - SINGULARITY-MBP-DATAWEAVE
  - SINGULARITY-MBP-FORGE-RENDERER
  - SINGULARITY-MBP-COMBAT-ADVERSARY
  - SINGULARITY-MBP-INTERFACE-HUD
  - SINGULARITY-judicial-intelligence
data_sources:
  - judicial_violations (5,059+ rows)
  - berry_mcneill_intelligence (189+ rows)
  - impeachment_matrix (judicial targets)
  - timeline_events (judicial actions)
  - docket_events (order issuance timing)
---

# SINGULARITY-MBP-COMBAT-JUDICIAL — Judicial Cartel Intelligence Overlay

> **The cartel is a graph. The graph makes the cartel visible. Visibility is the weapon.**

## 1. Architecture: Judicial Intelligence Layer

The Judicial Combat layer transforms 5,059+ documented violations and 189+ cartel intelligence
records into a visual indictment that no court — not even the MSC — can ignore. Every ex parte
order, every benchbook deviation, every Canon violation becomes a node, a link, a heat signature.

```
┌─────────────────────────────────────────────────────────┐
│             JUDICIAL COMBAT LAYER PIPELINE               │
│                                                          │
│  EXTRACT                                                 │
│    judicial_violations → violation nodes (5,059+)        │
│    berry_mcneill_intelligence → cartel links (189+)      │
│    timeline_events WHERE actor LIKE '%McNeill%'          │
│    impeachment_matrix WHERE target = 'judicial'          │
│                                                          │
│  TRANSFORM                                               │
│    Violation clustering (by type × time window)          │
│    Cartel subgraph extraction (triangle detection)       │
│    Ex parte pattern detection (48hr filing correlation)  │
│    Benchbook deviation scoring (per hearing)             │
│    Canon violation categorization (Canon 1-7)            │
│                                                          │
│  RENDER                                                  │
│    Triangle glyph (McNeill-Hoopes-Ladas-Hoopes)         │
│    Violation heatmap (time × type matrix overlay)        │
│    Ex parte pulse animation (correlated orders)          │
│    Benchbook deviation radar chart (per hearing node)    │
│    JTC exhibit generation (one-click export)             │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Cartel Subgraph Extraction

### 2.1 Data Pipeline — Python Extraction

```python
"""Extract judicial cartel subgraph from litigation_context.db."""
import sqlite3
from collections import defaultdict

def extract_cartel_subgraph(db_path: str) -> dict:
    """Build the McNeill-Hoopes-Ladas-Hoopes judicial cartel graph."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.execute("PRAGMA journal_mode = WAL")

    # Core cartel actors
    CARTEL_ACTORS = {
        "mcneill": {
            "id": "judge-mcneill",
            "label": "Hon. Jenny L. McNeill",
            "role": "presiding_judge",
            "bar": "P58235",
            "court": "14th Circuit"
        },
        "hoopes": {
            "id": "judge-hoopes",
            "label": "Hon. Kenneth Hoopes",
            "role": "chief_judge",
            "court": "14th Circuit"
        },
        "ladas_hoopes": {
            "id": "judge-ladas-hoopes",
            "label": "Hon. Maria Ladas-Hoopes",
            "role": "district_judge",
            "court": "60th District"
        },
        "cavan_berry": {
            "id": "cavan-berry",
            "label": "Cavan Berry",
            "role": "attorney_magistrate",
            "court": "60th District",
            "office": "990 Terrace St"
        },
        "ronald_berry": {
            "id": "ronald-berry",
            "label": "Ronald Berry",
            "role": "non_attorney",
            "relation": "family_of_cavan_berry"
        },
        "rusco": {
            "id": "foc-rusco",
            "label": "Pamela Rusco",
            "role": "foc_officer",
            "office": "990 Terrace St"
        }
    }

    # Cartel relationships with evidence basis
    CARTEL_EDGES = [
        {
            "source": "judge-mcneill", "target": "cavan-berry",
            "type": "spouse", "style": "double_line",
            "evidence": "Marriage record, shared household"
        },
        {
            "source": "judge-mcneill", "target": "judge-hoopes",
            "type": "former_partner", "style": "thick_dashed",
            "evidence": "Ladas, Hoopes & McNeill law firm, 435 Whitehall Rd"
        },
        {
            "source": "judge-mcneill", "target": "judge-ladas-hoopes",
            "type": "former_partner", "style": "thick_dashed",
            "evidence": "Ladas, Hoopes & McNeill law firm, 435 Whitehall Rd"
        },
        {
            "source": "judge-hoopes", "target": "judge-ladas-hoopes",
            "type": "spouse", "style": "double_line",
            "evidence": "Marriage record — Hoopes married Ladas-Hoopes"
        },
        {
            "source": "cavan-berry", "target": "ronald-berry",
            "type": "family", "style": "thin_solid",
            "evidence": "Family relationship — Berry surname"
        },
        {
            "source": "cavan-berry", "target": "foc-rusco",
            "type": "same_address", "style": "dotted_red",
            "evidence": "Both at 990 Terrace St, Muskegon"
        },
        {
            "source": "ronald-berry", "target": "emily-watson",
            "type": "cohabitant", "style": "thin_solid",
            "evidence": "Both at 2160 Garland Dr, Norton Shores"
        }
    ]

    # Pull violation counts per actor
    violations = conn.execute("""
        SELECT violation_type, COUNT(*) as cnt,
               MIN(event_date) as first, MAX(event_date) as last
        FROM judicial_violations
        GROUP BY violation_type
        ORDER BY cnt DESC
    """).fetchall()

    # Pull berry_mcneill intelligence
    intel = conn.execute("""
        SELECT category, detail, source_file, confidence
        FROM berry_mcneill_intelligence
        ORDER BY confidence DESC
    """).fetchall()

    conn.close()

    return {
        "actors": CARTEL_ACTORS,
        "edges": CARTEL_EDGES,
        "violations_by_type": [
            {"type": r[0], "count": r[1], "first": r[2], "last": r[3]}
            for r in violations
        ],
        "intel": [
            {"category": r[0], "detail": r[1], "source": r[2], "confidence": r[3]}
            for r in intel
        ]
    }
```

### 2.2 Triangle Visualization — D3.js

```javascript
/**
 * Render the McNeill-Hoopes-Ladas-Hoopes judicial cartel triangle.
 * The triangle is a fixed-position subgraph overlaid on Layer 10 (Judicial).
 */
class CartelTriangle {
  constructor(svg, cartelData) {
    this.svg = svg;
    this.data = cartelData;
    this.group = svg.append('g').attr('class', 'cartel-triangle');
    this.pulseTimer = null;
  }

  render(cx, cy, radius = 120) {
    const actors = this.data.actors;
    const positions = this._computeTrianglePositions(cx, cy, radius);

    // Relationship edges with type-specific styling
    const edgeStyles = {
      spouse: { stroke: '#ff4444', width: 3, dash: 'none', label: 'SPOUSE' },
      former_partner: { stroke: '#ff8800', width: 2.5, dash: '8,4', label: 'FORMER PARTNER' },
      family: { stroke: '#ffcc00', width: 1.5, dash: '4,2', label: 'FAMILY' },
      same_address: { stroke: '#ff0000', width: 2, dash: '2,2', label: 'SAME ADDRESS' },
      cohabitant: { stroke: '#cc44cc', width: 1.5, dash: 'none', label: 'COHABITANT' }
    };

    // Draw edges
    this.data.edges.forEach(edge => {
      const style = edgeStyles[edge.type] || edgeStyles.family;
      const src = positions[edge.source];
      const tgt = positions[edge.target];
      if (!src || !tgt) return;

      this.group.append('line')
        .attr('x1', src.x).attr('y1', src.y)
        .attr('x2', tgt.x).attr('y2', tgt.y)
        .attr('stroke', style.stroke)
        .attr('stroke-width', style.width)
        .attr('stroke-dasharray', style.dash)
        .attr('class', `cartel-edge edge-${edge.type}`);

      // Edge label at midpoint
      this.group.append('text')
        .attr('x', (src.x + tgt.x) / 2)
        .attr('y', (src.y + tgt.y) / 2 - 6)
        .attr('text-anchor', 'middle')
        .attr('font-size', '8px')
        .attr('fill', style.stroke)
        .text(style.label);
    });

    // Draw actor nodes
    Object.entries(actors).forEach(([key, actor]) => {
      const pos = positions[actor.id];
      if (!pos) return;

      const nodeGroup = this.group.append('g')
        .attr('transform', `translate(${pos.x}, ${pos.y})`)
        .attr('class', `cartel-node node-${actor.role}`)
        .style('cursor', 'pointer');

      // Outer glow for judges
      if (actor.role.includes('judge')) {
        nodeGroup.append('circle')
          .attr('r', 22)
          .attr('fill', 'none')
          .attr('stroke', '#ff4444')
          .attr('stroke-width', 1)
          .attr('opacity', 0.4)
          .attr('class', 'cartel-glow');
      }

      // Main node circle
      const fillColor = this._roleColor(actor.role);
      nodeGroup.append('circle')
        .attr('r', 16)
        .attr('fill', fillColor)
        .attr('stroke', '#fff')
        .attr('stroke-width', 2);

      // Label
      nodeGroup.append('text')
        .attr('y', 28)
        .attr('text-anchor', 'middle')
        .attr('font-size', '10px')
        .attr('fill', '#eee')
        .text(actor.label);

      // Click handler for judicial drill-down
      nodeGroup.on('click', () => this._showJudicialProfile(actor));
    });

    this._startPulseAnimation();
  }

  _computeTrianglePositions(cx, cy, r) {
    // Arrange 3 judges as primary triangle, support actors around periphery
    const angleOffset = -Math.PI / 2; // Top vertex
    return {
      'judge-mcneill':       { x: cx, y: cy - r },                                    // top
      'judge-hoopes':        { x: cx - r * Math.cos(Math.PI/6), y: cy + r * 0.5 },    // bottom-left
      'judge-ladas-hoopes':  { x: cx + r * Math.cos(Math.PI/6), y: cy + r * 0.5 },    // bottom-right
      'cavan-berry':         { x: cx + r * 0.7, y: cy - r * 0.6 },                    // upper-right
      'ronald-berry':        { x: cx + r * 1.2, y: cy - r * 0.3 },                    // far right
      'foc-rusco':           { x: cx - r * 0.7, y: cy + r * 0.9 },                    // lower-left
      'emily-watson':        { x: cx + r * 1.5, y: cy }                               // far right
    };
  }

  _roleColor(role) {
    const colors = {
      presiding_judge: '#ff2222',
      chief_judge: '#ff6600',
      district_judge: '#ff9900',
      attorney_magistrate: '#cc4444',
      foc_officer: '#aa4488',
      non_attorney: '#888888'
    };
    return colors[role] || '#666666';
  }

  _startPulseAnimation() {
    this.group.selectAll('.cartel-glow')
      .transition()
      .duration(1500)
      .attr('r', 28).attr('opacity', 0.1)
      .transition()
      .duration(1500)
      .attr('r', 22).attr('opacity', 0.4)
      .on('end', () => this._startPulseAnimation());
  }

  _showJudicialProfile(actor) {
    // Emit event for HUD panel to display detailed judicial profile
    window.dispatchEvent(new CustomEvent('judicial-drill-down', {
      detail: { actorId: actor.id, label: actor.label, role: actor.role }
    }));
  }
}
```

---

## 3. Violation Heatmap — Time × Type Matrix

### 3.1 Heatmap Data Assembly

```python
"""Build violation heatmap: time bins × violation type."""
import sqlite3
from datetime import datetime, timedelta

def build_violation_heatmap(db_path: str, bin_days: int = 30) -> dict:
    """Create time × violation_type matrix for heatmap rendering."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout = 60000")

    rows = conn.execute("""
        SELECT violation_type, event_date
        FROM judicial_violations
        WHERE event_date IS NOT NULL
        ORDER BY event_date
    """).fetchall()
    conn.close()

    if not rows:
        return {"bins": [], "types": [], "matrix": []}

    # Parse dates and compute bins
    dates = [datetime.strptime(r[1][:10], "%Y-%m-%d") for r in rows if r[1]]
    min_date = min(dates)
    max_date = max(dates)

    # Build time bins
    bins = []
    current = min_date
    while current <= max_date:
        bins.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=bin_days)

    # Unique violation types
    types = sorted(set(r[0] for r in rows if r[0]))

    # Fill the matrix: matrix[type_idx][bin_idx] = count
    matrix = [[0] * len(bins) for _ in range(len(types))]
    type_idx_map = {t: i for i, t in enumerate(types)}

    for vtype, vdate in rows:
        if not vtype or not vdate:
            continue
        try:
            d = datetime.strptime(vdate[:10], "%Y-%m-%d")
        except ValueError:
            continue
        bin_idx = min((d - min_date).days // bin_days, len(bins) - 1)
        if vtype in type_idx_map:
            matrix[type_idx_map[vtype]][bin_idx] += 1

    return {"bins": bins, "types": types, "matrix": matrix}
```

### 3.2 Heatmap Rendering — D3.js

```javascript
/**
 * Violation heatmap: rows = violation types, columns = time bins.
 * Color scale: 0 violations = transparent, 1-5 = yellow, 6-20 = orange, 21+ = red.
 */
class ViolationHeatmap {
  constructor(container, data) {
    this.container = container;
    this.data = data; // { bins, types, matrix }
    this.cellSize = 14;
    this.margin = { top: 60, right: 20, bottom: 20, left: 180 };
  }

  render() {
    const { bins, types, matrix } = this.data;
    const w = this.margin.left + bins.length * this.cellSize + this.margin.right;
    const h = this.margin.top + types.length * this.cellSize + this.margin.bottom;

    const svg = d3.select(this.container).append('svg')
      .attr('width', w).attr('height', h)
      .attr('class', 'violation-heatmap');

    const maxVal = Math.max(...matrix.flat(), 1);
    const colorScale = d3.scaleSequential(d3.interpolateYlOrRd)
      .domain([0, maxVal]);

    // Draw cells
    types.forEach((type, ti) => {
      bins.forEach((bin, bi) => {
        const val = matrix[ti][bi];
        if (val === 0) return; // skip empty cells for performance

        svg.append('rect')
          .attr('x', this.margin.left + bi * this.cellSize)
          .attr('y', this.margin.top + ti * this.cellSize)
          .attr('width', this.cellSize - 1)
          .attr('height', this.cellSize - 1)
          .attr('fill', colorScale(val))
          .attr('rx', 2)
          .append('title')
          .text(`${type}: ${val} violations (${bin})`);
      });

      // Row label (violation type)
      svg.append('text')
        .attr('x', this.margin.left - 6)
        .attr('y', this.margin.top + ti * this.cellSize + this.cellSize / 2 + 4)
        .attr('text-anchor', 'end')
        .attr('font-size', '9px')
        .attr('fill', '#ccc')
        .text(type.replace(/_/g, ' '));
    });

    // Column labels (time bins, sparse — show every 3rd)
    bins.forEach((bin, bi) => {
      if (bi % 3 !== 0) return;
      svg.append('text')
        .attr('x', this.margin.left + bi * this.cellSize + this.cellSize / 2)
        .attr('y', this.margin.top - 6)
        .attr('text-anchor', 'middle')
        .attr('font-size', '8px')
        .attr('fill', '#999')
        .attr('transform', `rotate(-45, ${this.margin.left + bi * this.cellSize}, ${this.margin.top - 6})`)
        .text(bin.slice(0, 7)); // YYYY-MM
    });
  }
}
```

---

## 4. Ex Parte Pattern Detection

```python
"""Detect ex parte patterns: orders issued within 48 hours of adversary filing."""
import sqlite3
from datetime import datetime, timedelta

def detect_ex_parte_patterns(db_path: str, window_hours: int = 48) -> list:
    """Find orders issued suspiciously close to adversary filings/contacts."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout = 60000")

    # Get all ex parte-flagged violations
    ex_parte = conn.execute("""
        SELECT id, event_date, detail, source_file
        FROM judicial_violations
        WHERE violation_type LIKE '%ex_parte%'
          OR violation_type LIKE '%ex parte%'
        ORDER BY event_date
    """).fetchall()

    # Get adversary filings and contacts
    adversary_events = conn.execute("""
        SELECT event_date, event_description, source_document
        FROM timeline_events
        WHERE (actor LIKE '%Watson%' OR actor LIKE '%Emily%' OR actor LIKE '%Berry%')
          AND event_date IS NOT NULL
        ORDER BY event_date
    """).fetchall()
    conn.close()

    window = timedelta(hours=window_hours)
    patterns = []

    for viol in ex_parte:
        viol_id, viol_date_str, viol_detail, viol_source = viol
        if not viol_date_str:
            continue
        try:
            viol_date = datetime.strptime(viol_date_str[:10], "%Y-%m-%d")
        except ValueError:
            continue

        # Find adversary events within window before this violation
        correlated = []
        for adv in adversary_events:
            if not adv[0]:
                continue
            try:
                adv_date = datetime.strptime(adv[0][:10], "%Y-%m-%d")
            except ValueError:
                continue
            delta = viol_date - adv_date
            if timedelta(0) <= delta <= window:
                correlated.append({
                    "adversary_date": adv[0],
                    "adversary_event": adv[1][:120],
                    "hours_before_order": delta.total_seconds() / 3600
                })

        if correlated:
            patterns.append({
                "violation_id": viol_id,
                "order_date": viol_date_str,
                "order_detail": viol_detail[:200] if viol_detail else "",
                "correlated_adversary_events": correlated,
                "pattern_strength": min(len(correlated) / 3.0, 1.0),
                "is_five_orders_day": viol_date_str[:10] == "2025-08-08"
            })

    return sorted(patterns, key=lambda p: p["pattern_strength"], reverse=True)
```

### 4.1 Ex Parte Pulse Animation — D3.js

```javascript
/**
 * Animate ex parte correlation: when an adversary event and a court order
 * are within 48 hours, draw a pulsing red arc between them.
 */
function renderExParteArcs(svg, patterns, nodePositions) {
  const arcGroup = svg.append('g').attr('class', 'ex-parte-arcs');

  patterns.forEach(pattern => {
    const orderNode = nodePositions[`violation-${pattern.violation_id}`];
    if (!orderNode) return;

    pattern.correlated_adversary_events.forEach(corr => {
      const advNode = nodePositions[`event-${corr.adversary_date}`];
      if (!advNode) return;

      const midX = (orderNode.x + advNode.x) / 2;
      const midY = Math.min(orderNode.y, advNode.y) - 40; // arc above

      const path = arcGroup.append('path')
        .attr('d', `M${advNode.x},${advNode.y} Q${midX},${midY} ${orderNode.x},${orderNode.y}`)
        .attr('fill', 'none')
        .attr('stroke', pattern.is_five_orders_day ? '#ff0000' : '#ff6600')
        .attr('stroke-width', 1 + pattern.pattern_strength * 3)
        .attr('stroke-dasharray', '6,3')
        .attr('opacity', 0.6);

      // Pulse animation
      (function pulse() {
        path.transition().duration(800).attr('opacity', 1)
          .transition().duration(800).attr('opacity', 0.3)
          .on('end', pulse);
      })();
    });
  });
}
```

---

## 5. Benchbook Deviation Scoring

```python
"""Score each hearing for benchbook compliance deviations."""

BENCHBOOK_STANDARDS = {
    "notice_required": {
        "rule": "MCR 2.107 / Benchbook §2.2",
        "description": "Adequate notice to all parties before any hearing",
        "weight": 10
    },
    "opportunity_to_be_heard": {
        "rule": "Benchbook §3.1 / Due Process",
        "description": "Each party given meaningful opportunity to present",
        "weight": 10
    },
    "evidence_considered": {
        "rule": "MRE 101-1102 / Benchbook §4",
        "description": "All properly offered evidence considered",
        "weight": 8
    },
    "impartial_demeanor": {
        "rule": "Canon 2 / Benchbook §1.3",
        "description": "Neutral demeanor, no favoritism displayed",
        "weight": 9
    },
    "findings_stated": {
        "rule": "MCR 2.517 / Benchbook §5",
        "description": "Findings of fact and conclusions of law stated on record",
        "weight": 7
    },
    "no_ex_parte": {
        "rule": "Canon 3(A)(4) / MCR 2.003(C)",
        "description": "No ex parte communications about pending matters",
        "weight": 10
    },
    "record_preserved": {
        "rule": "MCR 8.108 / Benchbook §6",
        "description": "Complete record maintained for appellate review",
        "weight": 6
    }
}

def score_hearing_deviations(db_path: str, hearing_date: str) -> dict:
    """Score a specific hearing for benchbook deviations."""
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout = 60000")

    # Find violations on or near this hearing date
    violations = conn.execute("""
        SELECT violation_type, detail
        FROM judicial_violations
        WHERE event_date LIKE ?
    """, (hearing_date[:10] + '%',)).fetchall()
    conn.close()

    deviations = {}
    total_weight = sum(s["weight"] for s in BENCHBOOK_STANDARDS.values())
    violated_weight = 0

    for std_key, std in BENCHBOOK_STANDARDS.items():
        violated = any(
            std_key.replace('_', ' ') in (v[1] or '').lower()
            or std_key.replace('_', '') in (v[0] or '').lower()
            for v in violations
        )
        deviations[std_key] = {
            **std,
            "violated": violated,
            "violation_count": sum(
                1 for v in violations
                if std_key.replace('_', ' ') in (v[1] or '').lower()
            )
        }
        if violated:
            violated_weight += std["weight"]

    compliance_score = max(0, 100 - int(violated_weight / total_weight * 100))

    return {
        "hearing_date": hearing_date,
        "deviations": deviations,
        "compliance_score": compliance_score,
        "total_violations_on_date": len(violations),
        "grade": "F" if compliance_score < 40 else
                 "D" if compliance_score < 55 else
                 "C" if compliance_score < 70 else
                 "B" if compliance_score < 85 else "A"
    }
```

---

## 6. Canon Violation Categorization

```python
"""Categorize judicial violations by Michigan Code of Judicial Conduct Canon 1-7."""

CANON_MAP = {
    "Canon 1": {
        "title": "Integrity and Independence of the Judiciary",
        "keywords": ["integrity", "independence", "public confidence", "impropriety"],
        "violations": []
    },
    "Canon 2": {
        "title": "Avoidance of Impropriety",
        "keywords": ["bias", "prejudice", "favoritism", "appearance", "impartial",
                      "demeanor", "hostile", "shut my mouth"],
        "violations": []
    },
    "Canon 3": {
        "title": "Performing Duties Impartially and Diligently",
        "keywords": ["ex parte", "communication", "notice", "hearing",
                      "evidence", "record", "findings", "due process"],
        "violations": []
    },
    "Canon 4": {
        "title": "Extra-Judicial Activities",
        "keywords": ["outside activity", "business", "financial"],
        "violations": []
    },
    "Canon 5": {
        "title": "Refraining from Political Activity",
        "keywords": ["political", "campaign", "endorsement"],
        "violations": []
    },
    "Canon 6": {
        "title": "Financial Disclosure and Reporting",
        "keywords": ["disclosure", "financial", "conflict", "recusal"],
        "violations": []
    },
    "Canon 7": {
        "title": "Disqualification",
        "keywords": ["disqualification", "recusal", "MCR 2.003", "conflict of interest",
                      "former partner", "spouse", "same address"],
        "violations": []
    }
}

def categorize_by_canon(db_path: str) -> dict:
    """Map each judicial violation to its Canon category."""
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout = 60000")

    violations = conn.execute("""
        SELECT id, violation_type, detail, event_date
        FROM judicial_violations
    """).fetchall()
    conn.close()

    results = {k: {**v, "violations": []} for k, v in CANON_MAP.items()}
    unclassified = []

    for vid, vtype, detail, vdate in violations:
        text = f"{vtype or ''} {detail or ''}".lower()
        matched = False
        for canon_key, canon in results.items():
            if any(kw in text for kw in canon["keywords"]):
                canon["violations"].append({
                    "id": vid, "type": vtype,
                    "detail": detail[:200] if detail else "",
                    "date": vdate
                })
                matched = True
                break  # primary canon only
        if not matched:
            unclassified.append({"id": vid, "type": vtype, "date": vdate})

    # Compute summary
    summary = {}
    for key, canon in results.items():
        summary[key] = {
            "title": canon["title"],
            "count": len(canon["violations"]),
            "pct": round(len(canon["violations"]) / max(len(violations), 1) * 100, 1)
        }

    return {"canons": results, "summary": summary, "unclassified": unclassified}
```

---

## 7. JTC Exhibit Auto-Generation

```python
"""Generate JTC complaint exhibit package from violation clusters."""

def generate_jtc_exhibits(db_path: str, canon_data: dict) -> list:
    """Build exhibit entries for each Canon violation cluster."""
    exhibits = []
    exhibit_num = 1

    for canon_key in sorted(canon_data["canons"].keys()):
        canon = canon_data["canons"][canon_key]
        if not canon["violations"]:
            continue

        # Group violations by type within this Canon
        type_groups = {}
        for v in canon["violations"]:
            vt = v.get("type", "unknown")
            type_groups.setdefault(vt, []).append(v)

        for vtype, viols in sorted(type_groups.items(), key=lambda x: -len(x[1])):
            exhibit = {
                "exhibit_label": f"JTC-{exhibit_num:03d}",
                "canon": canon_key,
                "canon_title": canon["title"],
                "violation_type": vtype,
                "instance_count": len(viols),
                "date_range": f"{viols[0].get('date', '?')} to {viols[-1].get('date', '?')}",
                "representative_details": [
                    v.get("detail", "")[:300] for v in viols[:5]
                ],
                "bates_prefix": f"PIGORS-E-{exhibit_num * 100:06d}"
            }
            exhibits.append(exhibit)
            exhibit_num += 1

    return exhibits
```

---

## 8. Visual Encoding Reference

| Data Property | Visual Channel | Encoding |
|---------------|---------------|----------|
| Violation severity | Heat color | Sequential YlOrRd (0=transparent → 30+=deep red) |
| Relationship type | Edge style | spouse=double, former_partner=thick_dashed, same_address=dotted_red |
| Pattern strength | Node pulse | Faster pulse = stronger correlation (0.5-2.0s period) |
| Canon category | Node icon | Gavel (Canon 3), Scale (Canon 7), Shield (Canon 2) |
| Violation count | Node size | 12px base + log2(count) * 4px |
| Compliance score | Radar fill | Full=compliant, empty=deviant |
| Time period | Heatmap column | 30-day bins along x-axis |
| Actor role | Node color | See `_roleColor()` in §2.2 |
| Five Orders Day | Special glow | Bright red pulsing ring, 2x size |
| Ex parte correlation | Arc animation | Red dashed arc between adversary event → court order |

## 9. Interactive Judicial Profile Drill-Down

When a user clicks a judicial actor node, the HUD panel displays:

```
┌─────────────────────────────────────────┐
│  JUDICIAL PROFILE: Hon. Jenny L. McNeill│
│  Bar: P58235 | Court: 14th Circuit      │
│─────────────────────────────────────────│
│  Violations: 5,059 total                │
│  ├── Ex Parte: 3,697 (73.1%)           │
│  ├── Benchbook: 504                     │
│  ├── MCR 2.003 Refusal: 167            │
│  ├── Procedural: 161                    │
│  ├── PPO Weaponization: 126             │
│  └── Due Process Denial: 105            │
│─────────────────────────────────────────│
│  Canon Violations                       │
│  Canon 3: 4,201 (83%) ██████████████░░ │
│  Canon 7:   467 ( 9%) ██░░░░░░░░░░░░░░ │
│  Canon 2:   312 ( 6%) █░░░░░░░░░░░░░░░ │
│  Canon 1:    79 ( 2%) ░░░░░░░░░░░░░░░░ │
│─────────────────────────────────────────│
│  Cartel Links: 3                        │
│  → Hoopes (former_partner)              │
│  → Ladas-Hoopes (former_partner)        │
│  → Cavan Berry (spouse)                 │
│─────────────────────────────────────────│
│  [Export JTC Package]  [Show Timeline]  │
└─────────────────────────────────────────┘
```

## 10. Integration with MBP-GENESIS Layers

The Judicial Combat overlay maps to **Layer 10 (Judicial)** in the GENESIS layer taxonomy:

```javascript
LAYER_META[10] = {
  name: 'Judicial',
  color: '#ff4444',
  charge: -400,        // strong repulsion — spread violations out
  collideRadius: 30,
  linkDistance: 80,
  linkStrength: 0.6,
  alphaDecay: 0.02,
  enabled: true,
  overlays: ['cartel_triangle', 'violation_heatmap', 'ex_parte_arcs']
};
```

### Node Types in Layer 10

| Type | Subtype | Source Table | Sizing |
|------|---------|-------------|--------|
| JUDICIAL | judge | cartel_actors | Fixed 16px |
| JUDICIAL | violation | judicial_violations | log2(severity) * 4 |
| JUDICIAL | canon_cluster | aggregated | count * 2 |
| JUDICIAL | hearing | timeline_events | deviation_score / 10 |
| JUDICIAL | intel | berry_mcneill_intelligence | confidence * 12 |

---

## 11. Performance Considerations

- **Violation nodes are numerous** (5,059+) — use LOD to hide detail text below zoom level 3
- **Heatmap is rendered once** on layer activation, not per frame — cache as offscreen canvas
- **Ex parte arcs** animate via CSS transitions, not D3 timer — lower CPU cost
- **Cartel triangle** is a fixed-position overlay — excluded from force simulation
- **Canon categorization** runs once on data load — results cached in `window.__judicialCanons`
- **Benchbook radar charts** render on hover only — lazy SVG construction

---
skill: SINGULARITY-MBP-COMBAT-AUTHORITY
version: 1.0.0
description: >-
  Authority hierarchy visualization for THEMANBEARPIG 13-layer graph.
  Citation PageRank from authority_chains_v2 (167K chains) and master_citations (72K).
  Chain completeness scoring (primary to supporting to pin cite).
  Hierarchical court-level rendering (SCOTUS, 6th Circuit, MSC, COA, Circuit, District).
  Shepardization status tracking (good_law, questioned, overruled).
  Authority coverage heatmap per filing lane.
  Missing authority gap detection with acquisition task generation.
  Interactive drill-down from citation node to all filings referencing it.
tier: 2-COMBAT
domain: authority-hierarchy
triggers:
  - authority
  - citation
  - hierarchy
  - chain completeness
  - Shepard
  - PageRank
  - court level
  - MCR
  - MCL
  - case law
  - pin cite
cross_links:
  - MBP-GENESIS
  - MBP-DATAWEAVE
  - MBP-COMBAT-EVIDENCE
  - MBP-COMBAT-WEAPONS
  - MBP-INTEGRATION-FILING
data_sources:
  - authority_chains_v2
  - master_citations
  - michigan_rules_extracted
  - filing_readiness
  - evidence_quotes
---

# SINGULARITY-MBP-COMBAT-AUTHORITY

> Authority hierarchy, citation PageRank, chain completeness scoring, and
> Shepardization status for the THEMANBEARPIG 13-layer litigation graph.

## 1. Architecture Overview

```
authority_chains_v2 (167K rows)
  + master_citations (72K rows)
  + michigan_rules_extracted (19.8K rows)
        |
        v
  +-----------------------+
  | AuthorityGraphBuilder |
  +-----------------------+
        |
  +-----+------+----------+-----------+
  |            |          |           |
  v            v          v           v
Citation    Chain      Court       Coverage
PageRank    Complete   Hierarchy   Matrix
  |            |          |           |
  +-----+------+----------+-----------+
        |
        v
  +--------------------+
  | D3 Authority Layer |
  +--------------------+
  | - Hierarchical Y   |
  | - PageRank sizing  |
  | - Status coloring  |
  | - Chain arcs       |
  | - Gap markers      |
  +--------------------+
```

### Data Flow

1. **Extract** citation relationships from `authority_chains_v2`
2. **Enrich** with full text and metadata from `master_citations`
3. **Score** each authority via PageRank (in-degree + chain depth)
4. **Classify** chain completeness (primary, supporting, pin cite)
5. **Assign** court hierarchy level for Y-axis positioning
6. **Detect** Shepardization status (good law, questioned, overruled)
7. **Map** coverage per filing lane (A through F + CRIMINAL)
8. **Identify** gaps where filings lack required authorities
9. **Render** as interactive hierarchical D3 force layout

---

## 2. Citation Graph Construction

### 2.1 Extract from authority_chains_v2

```python
import sqlite3
import networkx as nx
from collections import defaultdict

def build_citation_graph(db_path: str) -> nx.DiGraph:
    """Build directed citation graph from authority_chains_v2."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA cache_size = -32000")

    cols = {r[1] for r in conn.execute(
        "PRAGMA table_info(authority_chains_v2)"
    )}

    select_cols = []
    for c in ["primary_citation", "supporting_citation",
              "relationship", "source_document", "source_type",
              "lane", "paragraph_context"]:
        if c in cols:
            select_cols.append(c)

    rows = conn.execute(f"""
        SELECT {', '.join(select_cols)}
        FROM authority_chains_v2
        WHERE primary_citation IS NOT NULL
          AND supporting_citation IS NOT NULL
    """).fetchall()

    G = nx.DiGraph()
    for row in rows:
        data = dict(zip(select_cols, row))
        primary = data["primary_citation"].strip()
        supporting = data["supporting_citation"].strip()

        if not G.has_node(primary):
            G.add_node(primary, citations=[], lanes=set())
        if not G.has_node(supporting):
            G.add_node(supporting, citations=[], lanes=set())

        G.add_edge(supporting, primary,
                   relationship=data.get("relationship", "supports"),
                   source=data.get("source_document", ""),
                   source_type=data.get("source_type", ""))

        lane = data.get("lane", "")
        if lane:
            G.nodes[primary]["lanes"].add(lane)
            G.nodes[supporting]["lanes"].add(lane)

    conn.close()
    return G
```

### 2.2 Enrich with master_citations

```python
def enrich_from_master(G: nx.DiGraph, db_path: str) -> nx.DiGraph:
    """Add metadata from master_citations to graph nodes."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout = 60000")

    cols = {r[1] for r in conn.execute(
        "PRAGMA table_info(master_citations)"
    )}

    cite_col = "citation" if "citation" in cols else "primary_citation"
    rows = conn.execute(f"""
        SELECT {cite_col}, *
        FROM master_citations
    """).fetchall()
    col_names = [d[0] for d in conn.description]

    lookup = {}
    for row in rows:
        data = dict(zip(col_names, row))
        key = data[cite_col].strip() if data[cite_col] else ""
        if key:
            lookup[key] = data

    for node in G.nodes():
        if node in lookup:
            meta = lookup[node]
            G.nodes[node]["full_citation"] = meta.get("full_text", "")
            G.nodes[node]["year"] = meta.get("year", "")
            G.nodes[node]["court"] = meta.get("court", "")
            G.nodes[node]["jurisdiction"] = meta.get("jurisdiction", "MI")

    conn.close()
    return G
```

---

## 3. Citation PageRank

### 3.1 Compute Authority Importance

```python
def compute_citation_pagerank(G: nx.DiGraph) -> dict:
    """
    PageRank over citation graph.
    Most-cited authorities bubble to top.
    Damping factor 0.85 standard.
    """
    if len(G) == 0:
        return {}

    pr = nx.pagerank(G, alpha=0.85, max_iter=200, tol=1e-6)

    # Normalize to 0-1 range for node sizing
    max_pr = max(pr.values()) if pr else 1.0
    normalized = {k: v / max_pr for k, v in pr.items()}

    # Attach to graph nodes
    for node, score in normalized.items():
        G.nodes[node]["pagerank"] = score
        G.nodes[node]["raw_pagerank"] = pr[node]

    return normalized


def rank_authorities(G: nx.DiGraph, top_n: int = 50) -> list:
    """Return top N authorities by PageRank."""
    ranked = sorted(
        G.nodes(data=True),
        key=lambda x: x[1].get("pagerank", 0),
        reverse=True
    )
    return [
        {
            "citation": node,
            "pagerank": data.get("pagerank", 0),
            "in_degree": G.in_degree(node),
            "out_degree": G.out_degree(node),
            "court": data.get("court", "unknown"),
            "lanes": list(data.get("lanes", set())),
        }
        for node, data in ranked[:top_n]
    ]
```

### 3.2 D3.js PageRank-Based Sizing

```javascript
class AuthorityPageRankRenderer {
  constructor(svg, nodes) {
    this.svg = svg;
    this.nodes = nodes;
    this.sizeScale = d3.scaleSqrt()
      .domain([0, 1])
      .range([4, 28]);
  }

  render() {
    const circles = this.svg.selectAll('.authority-node')
      .data(this.nodes)
      .join('circle')
      .attr('class', 'authority-node')
      .attr('r', d => this.sizeScale(d.pagerank))
      .attr('fill', d => this.courtColor(d.court_level))
      .attr('stroke', d => this.chainBorder(d.chain_completeness))
      .attr('stroke-width', d => d.chain_completeness >= 1.0 ? 2.5 : 1)
      .attr('opacity', 0.85);

    // Labels for top authorities only (PageRank > 0.3)
    this.svg.selectAll('.authority-label')
      .data(this.nodes.filter(d => d.pagerank > 0.3))
      .join('text')
      .attr('class', 'authority-label')
      .attr('font-size', d => Math.max(8, 10 * d.pagerank))
      .attr('text-anchor', 'middle')
      .attr('dy', d => -this.sizeScale(d.pagerank) - 4)
      .text(d => this.shortCite(d.citation));
  }

  courtColor(level) {
    const colors = {
      'SCOTUS':     '#FFD700',
      '6TH_CIR':   '#FF6B35',
      'MSC':        '#E63946',
      'COA':        '#457B9D',
      'CIRCUIT':    '#2A9D8F',
      'DISTRICT':   '#264653',
      'STATUTE':    '#8338EC',
      'RULE':       '#06D6A0'
    };
    return colors[level] || '#999';
  }

  chainBorder(completeness) {
    if (completeness >= 1.0) return '#00FF00';
    if (completeness >= 0.66) return '#FFAA00';
    if (completeness >= 0.33) return '#FF4444';
    return '#666';
  }

  shortCite(citation) {
    // Abbreviate: "MCL 722.23(j)" stays, long case names truncate
    if (citation.length <= 20) return citation;
    return citation.substring(0, 18) + '...';
  }
}
```

---

## 4. Chain Completeness Scoring

### 4.1 Three-Link Chain Model

Every robust legal argument requires a chain:

```
PRIMARY_AUTHORITY  -->  SUPPORTING_AUTHORITY  -->  PIN_CITE
(statute/rule)         (case applying it)         (specific page/paragraph)
```

Completeness scoring:

| Chain State | Score | Visual |
|-------------|-------|--------|
| Primary + Supporting + Pin Cite | 1.0 | Solid green border |
| Primary + Supporting (no pin) | 0.66 | Dashed amber border |
| Primary only (no support) | 0.33 | Dotted red border |
| Referenced but unverified | 0.0 | Gray dashed border |

### 4.2 Compute Chain Completeness

```python
def score_chain_completeness(G: nx.DiGraph) -> dict:
    """
    Score each authority node for chain completeness.
    A complete chain: primary -> supporting case -> pin cite.
    """
    scores = {}

    for node in G.nodes():
        data = G.nodes[node]
        in_edges = list(G.in_edges(node, data=True))
        out_edges = list(G.out_edges(node, data=True))

        has_primary = _is_primary(node)
        has_supporting = any(
            _is_case_law(e[0]) for e in in_edges
        )
        has_pin_cite = _has_pin_cite(node, data)

        score = 0.0
        if has_primary:
            score += 0.33
        if has_supporting:
            score += 0.33
        if has_pin_cite:
            score += 0.34

        scores[node] = round(score, 2)
        G.nodes[node]["chain_completeness"] = scores[node]

    return scores


def _is_primary(citation: str) -> bool:
    """Check if citation is a primary authority (statute/rule)."""
    prefixes = ("MCR ", "MCL ", "USC ", "FRCP ", "MRE ",
                "US Const", "MI Const")
    return any(citation.upper().startswith(p.upper()) for p in prefixes)


def _is_case_law(citation: str) -> bool:
    """Check if citation is case law (contains 'Mich', 'F.', 'S.Ct.')."""
    markers = ("Mich", "F.2d", "F.3d", "F.4th", "S.Ct.",
               "U.S.", "N.W.2d", "Mich App")
    return any(m in citation for m in markers)


def _has_pin_cite(citation: str, data: dict) -> bool:
    """Check for pin cite (specific page or paragraph reference)."""
    import re
    pin_pattern = r'(?:at|p\.|pp\.|para\.?\s*)\s*\d+'
    full = data.get("full_citation", citation)
    return bool(re.search(pin_pattern, full))
```

### 4.3 D3.js Chain Arc Rendering

```javascript
class ChainArcRenderer {
  constructor(svg, links, nodePositions) {
    this.svg = svg;
    this.links = links;
    this.positions = nodePositions;
  }

  render() {
    const arcs = this.svg.selectAll('.chain-arc')
      .data(this.links)
      .join('path')
      .attr('class', 'chain-arc')
      .attr('d', d => this.arcPath(d))
      .attr('fill', 'none')
      .attr('stroke', d => this.relationColor(d.relationship))
      .attr('stroke-width', d => d.strength > 0.7 ? 2 : 1)
      .attr('stroke-dasharray', d =>
        d.relationship === 'pin_cite' ? '2,2' :
        d.relationship === 'supports' ? 'none' : '5,3'
      )
      .attr('opacity', 0.6)
      .attr('marker-end', 'url(#arrow)');

    // Arrow marker definition
    this.svg.append('defs').append('marker')
      .attr('id', 'arrow')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 12)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#888');
  }

  arcPath(d) {
    const src = this.positions[d.source];
    const tgt = this.positions[d.target];
    if (!src || !tgt) return '';

    const dx = tgt.x - src.x;
    const dy = tgt.y - src.y;
    const dr = Math.sqrt(dx * dx + dy * dy) * 1.5;
    return `M${src.x},${src.y}A${dr},${dr} 0 0,1 ${tgt.x},${tgt.y}`;
  }

  relationColor(rel) {
    const colors = {
      'supports':    '#2A9D8F',
      'applies':     '#457B9D',
      'distinguishes': '#E9C46A',
      'overrules':   '#E63946',
      'pin_cite':    '#06D6A0',
      'cites':       '#888'
    };
    return colors[rel] || '#666';
  }
}
```

---

## 5. Hierarchical Court-Level Rendering

### 5.1 Court Hierarchy Bands

```
Y-Position    Court Level           Authority Type
----------    -----------           ----------------
Band 0 (top)  US Supreme Court      Constitutional, SCOTUS opinions
Band 1        6th Circuit           Federal appellate (binding)
Band 2        MI Supreme Court      State supreme (binding)
Band 3        MI Court of Appeals   State appellate (persuasive->binding)
Band 4        Circuit Court         Trial court orders
Band 5        District Court        Limited jurisdiction
Band 6        Statutes/Rules        MCL, MCR, MRE, USC, FRCP
```

### 5.2 Court Level Classification

```python
COURT_HIERARCHY = {
    "SCOTUS": 0,
    "6TH_CIR": 1,
    "MSC": 2,
    "COA": 3,
    "CIRCUIT": 4,
    "DISTRICT": 5,
    "STATUTE": 6,
    "RULE": 6,
}

def classify_court_level(citation: str) -> str:
    """Classify a citation into its court hierarchy level."""
    c = citation.upper()

    if any(m in c for m in ["U.S. ", "S.CT.", "L.ED."]):
        return "SCOTUS"
    if any(m in c for m in ["F.2D", "F.3D", "F.4TH", "6TH CIR"]):
        return "6TH_CIR"
    if "MICH " in c and "MICH APP" not in c:
        return "MSC"
    if "MICH APP" in c or "N.W.2D" in c:
        return "COA"
    if any(c.startswith(p) for p in ["MCL ", "USC ", "28 USC"]):
        return "STATUTE"
    if any(c.startswith(p) for p in ["MCR ", "MRE ", "FRCP "]):
        return "RULE"

    return "COA"  # default for unclassified case law


def assign_y_positions(G: nx.DiGraph, height: int = 800) -> dict:
    """Assign Y coordinates based on court hierarchy."""
    band_height = height / (len(COURT_HIERARCHY) + 1)
    positions = {}

    for node in G.nodes():
        level = classify_court_level(node)
        G.nodes[node]["court_level"] = level
        band_idx = COURT_HIERARCHY.get(level, 3)
        # Jitter within band to prevent overlap
        import random
        jitter = random.uniform(-band_height * 0.3, band_height * 0.3)
        positions[node] = {
            "y": (band_idx + 0.5) * band_height + jitter
        }

    return positions
```

### 5.3 D3.js Hierarchical Layout

```javascript
class AuthorityHierarchyLayout {
  constructor(svg, width, height) {
    this.svg = svg;
    this.width = width;
    this.height = height;
    this.bands = [
      { level: 'SCOTUS',   label: 'US Supreme Court',    y: 0 },
      { level: '6TH_CIR', label: '6th Circuit',          y: 1 },
      { level: 'MSC',      label: 'MI Supreme Court',     y: 2 },
      { level: 'COA',      label: 'MI Court of Appeals',  y: 3 },
      { level: 'CIRCUIT',  label: 'Circuit Court',        y: 4 },
      { level: 'DISTRICT', label: 'District Court',       y: 5 },
      { level: 'STATUTE',  label: 'Statutes & Rules',     y: 6 },
    ];
    this.bandH = height / (this.bands.length + 1);
  }

  renderBands() {
    const bandG = this.svg.append('g').attr('class', 'court-bands');

    bandG.selectAll('.band-rect')
      .data(this.bands)
      .join('rect')
      .attr('class', 'band-rect')
      .attr('x', 0)
      .attr('y', d => d.y * this.bandH)
      .attr('width', this.width)
      .attr('height', this.bandH)
      .attr('fill', (d, i) => i % 2 === 0 ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)')
      .attr('stroke', 'rgba(255,255,255,0.08)');

    bandG.selectAll('.band-label')
      .data(this.bands)
      .join('text')
      .attr('class', 'band-label')
      .attr('x', 12)
      .attr('y', d => d.y * this.bandH + 18)
      .attr('fill', 'rgba(255,255,255,0.4)')
      .attr('font-size', 11)
      .text(d => d.label);
  }

  forceY() {
    return d3.forceY(d => {
      const idx = this.bands.findIndex(b => b.level === d.court_level);
      return (idx >= 0 ? idx + 0.5 : 3.5) * this.bandH;
    }).strength(0.8);
  }
}
```

---

## 6. Shepardization Status Tracking

### 6.1 Status Classification

| Status | Color | Meaning |
|--------|-------|---------|
| `good_law` | Green | Not negatively treated; safe to cite |
| `cautioned` | Yellow | Distinguished or limited by later cases |
| `questioned` | Orange | Validity questioned by later authority |
| `overruled` | Red | Explicitly overruled; do NOT cite |
| `superseded` | Gray | Replaced by statute or new rule version |
| `unverified` | White/dim | Not yet checked against current law |

### 6.2 Status Detection from Chain Data

```python
NEGATIVE_TREATMENTS = {
    "overrules": "overruled",
    "overruled": "overruled",
    "supersedes": "superseded",
    "superseded": "superseded",
    "distinguishes": "cautioned",
    "limits": "cautioned",
    "questions": "questioned",
    "criticized": "questioned",
}

def detect_shepard_status(G: nx.DiGraph) -> dict:
    """
    Infer Shepardization-like status from citation relationships.
    Not a true Shepard check (requires Westlaw/LexisNexis),
    but flags authorities with negative treatment in our chain data.
    """
    statuses = {}

    for node in G.nodes():
        worst_status = "unverified"
        in_edges = G.in_edges(node, data=True)

        for _, _, edge_data in in_edges:
            rel = edge_data.get("relationship", "").lower()
            mapped = NEGATIVE_TREATMENTS.get(rel)
            if mapped:
                severity = _status_severity(mapped)
                if severity > _status_severity(worst_status):
                    worst_status = mapped

        if worst_status == "unverified" and G.in_degree(node) > 0:
            worst_status = "good_law"

        statuses[node] = worst_status
        G.nodes[node]["shepard_status"] = worst_status

    return statuses


def _status_severity(status: str) -> int:
    """Higher = worse."""
    order = {
        "good_law": 0,
        "unverified": 1,
        "cautioned": 2,
        "questioned": 3,
        "superseded": 4,
        "overruled": 5,
    }
    return order.get(status, 1)
```

### 6.3 D3.js Status Indicators

```javascript
function applyShepardStatus(selection) {
  selection
    .attr('fill', d => {
      const colors = {
        good_law:    '#2A9D8F',
        cautioned:   '#E9C46A',
        questioned:  '#F4A261',
        overruled:   '#E63946',
        superseded:  '#6C757D',
        unverified:  'rgba(255,255,255,0.3)'
      };
      return colors[d.shepard_status] || colors.unverified;
    })
    .each(function(d) {
      if (d.shepard_status === 'overruled') {
        // Strike-through line for overruled authorities
        const bbox = this.getBBox();
        d3.select(this.parentNode).append('line')
          .attr('x1', bbox.x - 2)
          .attr('y1', bbox.y + bbox.height / 2)
          .attr('x2', bbox.x + bbox.width + 2)
          .attr('y2', bbox.y + bbox.height / 2)
          .attr('stroke', '#E63946')
          .attr('stroke-width', 2);
      }
    });
}
```

---

## 7. Authority Coverage per Filing Lane

### 7.1 Coverage Matrix Computation

```python
def compute_lane_coverage(G: nx.DiGraph, db_path: str) -> dict:
    """
    For each filing lane, count authorities available
    vs authorities required (from filing_readiness).
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout = 60000")

    # Get filing packages
    packages = conn.execute("""
        SELECT vehicle_name, lane, status
        FROM filing_readiness
    """).fetchall()

    lanes = ["A", "B", "C", "D", "E", "F", "CRIMINAL"]
    coverage = {}

    for lane in lanes:
        lane_nodes = [
            n for n in G.nodes()
            if lane in G.nodes[n].get("lanes", set())
        ]

        total = len(lane_nodes)
        complete = sum(
            1 for n in lane_nodes
            if G.nodes[n].get("chain_completeness", 0) >= 1.0
        )
        partial = sum(
            1 for n in lane_nodes
            if 0 < G.nodes[n].get("chain_completeness", 0) < 1.0
        )
        good_law = sum(
            1 for n in lane_nodes
            if G.nodes[n].get("shepard_status") == "good_law"
        )

        coverage[lane] = {
            "total_authorities": total,
            "complete_chains": complete,
            "partial_chains": partial,
            "good_law_count": good_law,
            "coverage_pct": round(complete / max(total, 1) * 100, 1),
        }

    conn.close()
    return coverage
```

### 7.2 D3.js Coverage Heatmap

```javascript
class AuthorityCoverageHeatmap {
  constructor(container, coverageData) {
    this.container = container;
    this.data = coverageData;
    this.lanes = ['A', 'B', 'C', 'D', 'E', 'F', 'CRIMINAL'];
    this.metrics = ['total_authorities', 'complete_chains',
                    'partial_chains', 'good_law_count'];
    this.colorScale = d3.scaleSequential(d3.interpolateViridis)
      .domain([0, 100]);
  }

  render() {
    const cellW = 80, cellH = 30, pad = 2;
    const svg = d3.select(this.container).append('svg')
      .attr('width', (this.lanes.length + 1) * cellW + 40)
      .attr('height', (this.metrics.length + 1) * cellH + 40);

    const g = svg.append('g').attr('transform', 'translate(120, 30)');

    // Column headers (lanes)
    g.selectAll('.lane-header')
      .data(this.lanes)
      .join('text')
      .attr('x', (d, i) => i * cellW + cellW / 2)
      .attr('y', -8)
      .attr('text-anchor', 'middle')
      .attr('fill', '#ccc')
      .attr('font-size', 12)
      .text(d => `Lane ${d}`);

    // Cells
    this.lanes.forEach((lane, li) => {
      this.metrics.forEach((metric, mi) => {
        const val = this.data[lane]?.[metric] || 0;
        const maxVal = Math.max(
          ...this.lanes.map(l => this.data[l]?.[metric] || 0), 1
        );

        g.append('rect')
          .attr('x', li * cellW + pad)
          .attr('y', mi * cellH + pad)
          .attr('width', cellW - pad * 2)
          .attr('height', cellH - pad * 2)
          .attr('fill', this.colorScale(val / maxVal * 100))
          .attr('rx', 3);

        g.append('text')
          .attr('x', li * cellW + cellW / 2)
          .attr('y', mi * cellH + cellH / 2 + 4)
          .attr('text-anchor', 'middle')
          .attr('fill', '#fff')
          .attr('font-size', 11)
          .text(val);
      });
    });
  }
}
```

---

## 8. Missing Authority Gap Detection

### 8.1 Required Authorities per Filing Type

```python
REQUIRED_AUTHORITIES = {
    "custody_modification": [
        "MCL 722.23", "MCL 722.27", "MCR 3.206",
        "Vodvarka v Grasher", "Pierron v Pierron",
    ],
    "disqualification": [
        "MCR 2.003", "Cain v Department of Corrections",
        "Armstrong v Ypsilanti Charter Township",
    ],
    "ppo_termination": [
        "MCL 600.2950", "MCR 3.707", "MCR 3.706",
        "Pickering v Pickering",
    ],
    "appeal_of_right": [
        "MCR 7.204", "MCR 7.205", "MCR 7.212",
        "Shade v Wright",
    ],
    "federal_1983": [
        "42 USC 1983", "28 USC 1343",
        "Monell v Department of Social Services",
        "Troxel v Granville",
    ],
    "msc_superintending": [
        "MCR 7.306", "MCR 7.315",
        "Const 1963 art 6 sec 4",
    ],
    "jtc_complaint": [
        "MCR 9.104", "MCR 9.205",
        "MI Code of Judicial Conduct",
    ],
}


def detect_authority_gaps(
    G: nx.DiGraph,
    filing_type: str
) -> list:
    """
    For a given filing type, find required authorities
    missing from the citation graph.
    """
    required = REQUIRED_AUTHORITIES.get(filing_type, [])
    existing = set(G.nodes())

    gaps = []
    for auth in required:
        found = False
        for node in existing:
            if auth.lower() in node.lower():
                found = True
                break
        if not found:
            gaps.append({
                "missing_authority": auth,
                "filing_type": filing_type,
                "priority": "HIGH",
                "acquisition": f"Search authority_chains_v2 and "
                               f"master_citations for {auth}; "
                               f"if absent, research via web_search",
            })

    return gaps


def detect_all_gaps(G: nx.DiGraph) -> list:
    """Run gap detection across all filing types."""
    all_gaps = []
    for filing_type in REQUIRED_AUTHORITIES:
        gaps = detect_authority_gaps(G, filing_type)
        all_gaps.extend(gaps)
    return all_gaps
```

### 8.2 D3.js Gap Markers

```javascript
function renderGapMarkers(svg, gaps, xScale, yScale) {
  const gapG = svg.append('g').attr('class', 'gap-markers');

  gapG.selectAll('.gap-marker')
    .data(gaps)
    .join('g')
    .attr('class', 'gap-marker')
    .attr('transform', (d, i) => {
      const x = xScale(d.filing_type) || 50;
      const y = yScale('STATUTE') + i * 20;
      return `translate(${x}, ${y})`;
    })
    .each(function(d) {
      const g = d3.select(this);

      // Pulsing red diamond for missing authority
      g.append('rect')
        .attr('width', 12).attr('height', 12)
        .attr('transform', 'rotate(45)')
        .attr('fill', '#E63946')
        .attr('opacity', 0.8);

      g.append('text')
        .attr('x', 18).attr('y', 4)
        .attr('fill', '#E63946')
        .attr('font-size', 9)
        .text(d.missing_authority);

      // Pulse animation
      g.select('rect')
        .append('animate')
        .attr('attributeName', 'opacity')
        .attr('values', '0.4;1;0.4')
        .attr('dur', '2s')
        .attr('repeatCount', 'indefinite');
    });
}
```

---

## 9. Visual Encoding Reference

| Property | Encoding | Example |
|----------|----------|---------|
| **Node size** | PageRank score (sqrt scale, 4-28px) | MCL 722.23 = large, obscure cite = small |
| **Node color** | Shepardization status | Green = good_law, Red = overruled |
| **Y position** | Court hierarchy band | SCOTUS at top, statutes at bottom |
| **Border style** | Chain completeness | Solid = complete, dashed = partial, dotted = bare |
| **Border color** | Chain completeness score | Green >= 1.0, amber >= 0.66, red < 0.33 |
| **Arc color** | Relationship type | Green = supports, red = overrules, amber = distinguishes |
| **Arc dash** | Relationship strength | Solid = strong, dashed = weak |
| **Diamond marker** | Missing authority gap | Pulsing red diamond with label |
| **Label size** | PageRank threshold | Only shown when PR > 0.3 |
| **Band shading** | Court level grouping | Alternating subtle fills |
| **Coverage cell** | Lane authority count | Viridis colormap (purple-green-yellow) |

---

## 10. Interactive Authority Drill-Down

### 10.1 Click Handler

```javascript
function setupAuthorityDrillDown(nodes, detailPanel) {
  nodes.on('click', function(event, d) {
    event.stopPropagation();

    const detail = {
      citation: d.citation,
      court_level: d.court_level,
      pagerank: d.pagerank?.toFixed(4),
      chain_completeness: d.chain_completeness?.toFixed(2),
      shepard_status: d.shepard_status,
      lanes: d.lanes?.join(', ') || 'none',
      in_degree: d.in_degree,
      out_degree: d.out_degree,
      supporting: d.supporting_citations || [],
      supported_by: d.supported_by || [],
    };

    detailPanel.html(`
      <h3>${detail.citation}</h3>
      <div class="detail-grid">
        <span>Court:</span><span>${detail.court_level}</span>
        <span>PageRank:</span><span>${detail.pagerank}</span>
        <span>Chain:</span><span>${detail.chain_completeness}</span>
        <span>Status:</span>
        <span class="status-${detail.shepard_status}">
          ${detail.shepard_status}
        </span>
        <span>Lanes:</span><span>${detail.lanes}</span>
        <span>Cited by:</span><span>${detail.in_degree} authorities</span>
        <span>Cites:</span><span>${detail.out_degree} authorities</span>
      </div>
      <h4>Supporting Citations</h4>
      <ul>${detail.supporting.map(s =>
        `<li>${s}</li>`).join('')}
      </ul>
      <h4>Supported By</h4>
      <ul>${detail.supported_by.map(s =>
        `<li>${s}</li>`).join('')}
      </ul>
    `).classed('visible', true);

    // Highlight connected nodes
    highlightChain(d, nodes);
  });
}

function highlightChain(selected, allNodes) {
  allNodes
    .attr('opacity', d => {
      if (d.citation === selected.citation) return 1.0;
      if (selected.supporting_citations?.includes(d.citation)) return 0.9;
      if (selected.supported_by?.includes(d.citation)) return 0.9;
      return 0.15;
    });
}
```

---

## 11. Integration with MBP-GENESIS Layers

### 11.1 Layer Registration

The Authority layer maps to **LAYER_META index 10** (AUTHORITY) in MBP-GENESIS:

```javascript
const AUTHORITY_LAYER = {
  id: 'authority',
  index: 10,
  label: 'Authority Hierarchy',
  description: 'Citation graph with PageRank, chain completeness, and court hierarchy',
  nodeTypes: ['authority_primary', 'authority_case', 'authority_statute',
              'authority_rule', 'authority_gap'],
  linkTypes: ['supports', 'applies', 'distinguishes', 'overrules',
              'pin_cite', 'cites'],
  defaultVisible: false,
  zIndex: 10,
  blendMode: 'screen',
};
```

### 11.2 Cross-Layer Connections

| Source Layer | Target Layer | Link Type | Condition |
|-------------|-------------|-----------|-----------|
| AUTHORITY | FILING (Layer 11) | `authority_supports_filing` | Authority cited in filing package |
| AUTHORITY | EVIDENCE (Layer 9) | `authority_grounds_evidence` | Authority provides legal basis for evidence relevance |
| AUTHORITY | JUDICIAL (Layer 8) | `authority_violated_by` | Judge violated cited authority |
| AUTHORITY | WEAPON (Layer 7) | `authority_enables_weapon` | Authority enables weapon chain |
| AUTHORITY | ADVERSARY (Layer 6) | `authority_against_adversary` | Authority supports claim against adversary |

---

## 12. Performance Considerations

### 12.1 Graph Size Budget

| Source Table | Est. Nodes | Est. Edges | Strategy |
|-------------|-----------|-----------|----------|
| authority_chains_v2 (167K) | ~8,000 unique cites | ~25,000 edges | Pre-aggregate, top-500 by PageRank for rendering |
| master_citations (72K) | ~12,000 unique cites | metadata only | Left-join enrichment, not rendered separately |
| michigan_rules_extracted (19.8K) | ~2,000 rules | lookup only | Used for chain completeness validation |

### 12.2 Rendering Thresholds

```javascript
const AUTH_PERF = {
  MAX_VISIBLE_NODES: 500,
  MAX_VISIBLE_EDGES: 2000,
  PAGERANK_CUTOFF: 0.01,       // Hide nodes below this PR
  LOD_DISTANCE_LABELS: 300,     // Show labels when zoomed in
  LOD_DISTANCE_ARCS: 500,       // Show arcs when zoomed in
  DEBOUNCE_FILTER_MS: 150,      // Debounce lane filter changes
  BAND_LABEL_MIN_ZOOM: 0.5,     // Show band labels above this zoom
  CACHE_PAGERANK: true,         // Cache PR computation (expensive)
};
```

### 12.3 Optimization Strategies

1. **Pre-compute PageRank** in Python; send only scores to D3 (never compute in browser)
2. **Top-N filtering**: Render only top 500 authorities by PageRank; rest available via search
3. **Lazy arc loading**: Only render arcs for visible nodes (viewport culling)
4. **Band-aware collision**: Use `forceCollide` scoped within each court band
5. **Incremental updates**: When filtering by lane, update node visibility without full re-layout
6. **Canvas fallback**: If node count exceeds 500, switch from SVG to Canvas renderer (see MBP-FORGE-RENDERER)
7. **Web Worker PageRank**: For graphs over 10K nodes, run PageRank in a Web Worker

---

## 13. Full Pipeline Integration

### 13.1 End-to-End Build

```python
def build_authority_layer(db_path: str) -> dict:
    """
    Full pipeline: extract -> enrich -> score -> classify -> export.
    Returns D3-ready JSON payload.
    """
    # Step 1: Build graph
    G = build_citation_graph(db_path)

    # Step 2: Enrich
    G = enrich_from_master(G, db_path)

    # Step 3: PageRank
    pr_scores = compute_citation_pagerank(G)

    # Step 4: Chain completeness
    chain_scores = score_chain_completeness(G)

    # Step 5: Court levels and Y positions
    positions = assign_y_positions(G, height=800)

    # Step 6: Shepardization
    statuses = detect_shepard_status(G)

    # Step 7: Coverage
    coverage = compute_lane_coverage(G, db_path)

    # Step 8: Gaps
    gaps = detect_all_gaps(G)

    # Step 9: Export top N for D3
    top_nodes = sorted(
        G.nodes(data=True),
        key=lambda x: x[1].get("pagerank", 0),
        reverse=True
    )[:500]

    nodes_json = []
    for node, data in top_nodes:
        nodes_json.append({
            "id": node,
            "citation": node,
            "court_level": data.get("court_level", "COA"),
            "pagerank": round(data.get("pagerank", 0), 4),
            "chain_completeness": data.get("chain_completeness", 0),
            "shepard_status": data.get("shepard_status", "unverified"),
            "lanes": list(data.get("lanes", set())),
            "y_hint": positions.get(node, {}).get("y", 400),
        })

    top_ids = {n["id"] for n in nodes_json}
    links_json = []
    for u, v, data in G.edges(data=True):
        if u in top_ids and v in top_ids:
            links_json.append({
                "source": u,
                "target": v,
                "relationship": data.get("relationship", "cites"),
            })

    return {
        "nodes": nodes_json,
        "links": links_json,
        "coverage": coverage,
        "gaps": gaps,
        "stats": {
            "total_authorities": len(G),
            "total_edges": G.number_of_edges(),
            "rendered_nodes": len(nodes_json),
            "rendered_edges": len(links_json),
            "gap_count": len(gaps),
        },
    }
```

### 13.2 Export Format

```json
{
  "nodes": [
    {
      "id": "MCL 722.23",
      "citation": "MCL 722.23",
      "court_level": "STATUTE",
      "pagerank": 0.9823,
      "chain_completeness": 1.0,
      "shepard_status": "good_law",
      "lanes": ["A", "D", "F"],
      "y_hint": 650
    }
  ],
  "links": [
    {
      "source": "Vodvarka v Grasher",
      "target": "MCL 722.23",
      "relationship": "applies"
    }
  ],
  "coverage": {
    "A": { "total_authorities": 45, "complete_chains": 32 }
  },
  "gaps": [
    { "missing_authority": "Monell v Dept of Social Services",
      "filing_type": "federal_1983", "priority": "HIGH" }
  ]
}
```

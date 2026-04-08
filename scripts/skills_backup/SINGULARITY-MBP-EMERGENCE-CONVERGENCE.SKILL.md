---
name: SINGULARITY-MBP-EMERGENCE-CONVERGENCE
description: "Cross-layer intelligence for THEMANBEARPIG: DBSCAN clustering, emergence signal detection, novelty scoring, convergence metrics, gap-to-acquisition task generation. Detects hidden connections between graph layers, computes lane readiness, identifies evidence gaps, and tracks build-to-build deltas for self-improvement. Fuses convergence_domains, filing_readiness, evidence_quotes, and authority_chains into actionable intelligence."
version: "2.0.0"
forged_from:
  - All COMBAT skills (cross-layer intelligence)
  - SINGULARITY-MBP-DATAWEAVE
  - convergence_domains (105 rows)
  - convergence_waves (10)
  - convergence_todos (37)
tier: "TIER-5/EMERGENCE"
domain: "Cross-layer intelligence — DBSCAN clustering, emergence detection, convergence metrics, gap→acquisition"
triggers:
  - convergence
  - emergence
  - cross-layer
  - DBSCAN
  - clustering
  - novelty
  - gap detection
  - acquisition
  - pattern detection
  - convergence metric
---

# SINGULARITY-MBP-EMERGENCE-CONVERGENCE v2.0

> **Where isolated data becomes interconnected intelligence. Where THEMANBEARPIG becomes conscious.**

## Layer 1: Cross-Layer Link Discovery

### 1.1 Automated Cross-Layer Connection Engine

```python
def discover_cross_layer_links(nodes: list, existing_links: list) -> list:
    """
    Find hidden connections between nodes on different layers.
    Uses shared entity names, dates, case numbers, and semantic proximity.
    """
    from collections import defaultdict
    import re

    new_links = []
    by_name = defaultdict(list)
    by_date = defaultdict(list)
    by_case = defaultdict(list)

    for node in nodes:
        label = (node.get('label') or '').lower()
        layer = node.get('layer', '')

        for name_part in label.split():
            if len(name_part) > 3:
                by_name[name_part].append(node)

        desc = node.get('desc', '')
        dates = re.findall(r'20\d{2}-\d{2}-\d{2}', desc)
        for d in dates:
            by_date[d].append(node)

        cases = re.findall(r'\d{4}-\d{4,6}', desc)
        for c in cases:
            by_case[c].append(node)

    existing_pairs = {(l['source'], l['target']) for l in existing_links}

    def add_link(n1, n2, link_type, reason):
        pair = (n1['id'], n2['id'])
        reverse = (n2['id'], n1['id'])
        if pair not in existing_pairs and reverse not in existing_pairs:
            existing_pairs.add(pair)
            new_links.append({
                'source': n1['id'], 'target': n2['id'],
                'layer': 'emergence', 'type': link_type,
                'color': '#ff00ff33', 'weight': 0.5, 'desc': reason
            })

    for key, group in by_name.items():
        layers = set(n['layer'] for n in group)
        if len(layers) > 1:
            for i, n1 in enumerate(group):
                for n2 in group[i+1:]:
                    if n1['layer'] != n2['layer']:
                        add_link(n1, n2, 'entity_match',
                                 f'Shared entity "{key}" across {n1["layer"]}↔{n2["layer"]}')

    for date, group in by_date.items():
        layers = set(n['layer'] for n in group)
        if len(layers) > 1:
            for i, n1 in enumerate(group[:5]):
                for n2 in group[i+1:5]:
                    if n1['layer'] != n2['layer']:
                        add_link(n1, n2, 'temporal_cooccurrence',
                                 f'Same date {date} across layers')

    return new_links
```

## Layer 2: DBSCAN Clustering for Emergence Detection

### 2.1 Spatial Clustering on Force Layout Positions

```javascript
function dbscanCluster(nodes, eps = 80, minPts = 3) {
  const NOISE = -1, UNVISITED = -2;
  nodes.forEach(n => { n._cluster = UNVISITED; });
  let clusterId = 0;

  function regionQuery(node) {
    return nodes.filter(other => {
      if (other === node) return false;
      const dx = (node.x || 0) - (other.x || 0);
      const dy = (node.y || 0) - (other.y || 0);
      return Math.sqrt(dx * dx + dy * dy) < eps;
    });
  }

  function expandCluster(node, neighbors, cId) {
    node._cluster = cId;
    const queue = [...neighbors];
    while (queue.length > 0) {
      const current = queue.shift();
      if (current._cluster === NOISE) current._cluster = cId;
      if (current._cluster !== UNVISITED) continue;
      current._cluster = cId;
      const cn = regionQuery(current);
      if (cn.length >= minPts) queue.push(...cn);
    }
  }

  nodes.forEach(node => {
    if (node._cluster !== UNVISITED) return;
    const neighbors = regionQuery(node);
    if (neighbors.length < minPts) node._cluster = NOISE;
    else { expandCluster(node, neighbors, clusterId); clusterId++; }
  });
  return clusterId;
}
```

### 2.2 Cross-Layer Cluster Analysis

```javascript
function analyzeEmergentClusters(nodes) {
  const clusterCount = dbscanCluster(nodes, 80, 3);
  const clusters = {};
  nodes.forEach(n => {
    if (n._cluster >= 0) {
      if (!clusters[n._cluster]) clusters[n._cluster] = { id: n._cluster, nodes: [], layers: new Set() };
      clusters[n._cluster].nodes.push(n);
      clusters[n._cluster].layers.add(n.layer);
    }
  });
  const emergent = Object.values(clusters).filter(c => c.layers.size > 1);
  emergent.forEach(c => {
    c.novelty = computeNoveltyScore(c);
    c.layers = Array.from(c.layers);
    c.description = `${c.nodes.length} nodes across ${c.layers.length} layers: ${c.layers.join(', ')}`;
  });
  return emergent.sort((a, b) => b.novelty - a.novelty);
}

function computeNoveltyScore(cluster) {
  const layerCounts = {};
  cluster.nodes.forEach(n => { layerCounts[n.layer] = (layerCounts[n.layer] || 0) + 1; });
  const total = cluster.nodes.length;
  let entropy = 0;
  Object.values(layerCounts).forEach(count => {
    const p = count / total;
    if (p > 0) entropy -= p * Math.log2(p);
  });
  const maxEntropy = Math.log2(Object.keys(layerCounts).length);
  return maxEntropy > 0 ? (entropy / maxEntropy) * 10 : 0;
}
```

## Layer 3: Convergence Metrics Dashboard

### 3.1 Lane Readiness from DB

```python
def compute_convergence_metrics(db_path: str) -> dict:
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout=60000")
    metrics = {}
    try:
        rows = conn.execute("""
            SELECT lane, AVG(confidence) as avg_conf, COUNT(*) as filings,
                   SUM(CASE WHEN status = 'FILED' THEN 1 ELSE 0 END) as filed
            FROM filing_readiness GROUP BY lane
        """).fetchall()
        for r in rows:
            metrics[r[0]] = {
                'lane': r[0], 'avg_confidence': round(r[1] or 0, 1),
                'total_filings': r[2], 'filed_count': r[3],
                'convergence_pct': round((r[3] / max(r[2], 1)) * 100, 1)
            }
        ev_rows = conn.execute("""
            SELECT lane, COUNT(*) as cnt FROM evidence_quotes
            WHERE is_duplicate = 0 GROUP BY lane
        """).fetchall()
        for r in ev_rows:
            if r[0] in metrics: metrics[r[0]]['evidence_count'] = r[1]

        auth_rows = conn.execute("""
            SELECT lane, COUNT(*) as total,
                   SUM(CASE WHEN chain_complete = 1 THEN 1 ELSE 0 END) as complete
            FROM authority_chains_v2 GROUP BY lane
        """).fetchall()
        for r in auth_rows:
            if r[0] in metrics:
                metrics[r[0]]['authority_completeness'] = round((r[2] / max(r[1], 1)) * 100, 1)
    except Exception:
        pass
    conn.close()
    return metrics
```

### 3.2 Convergence Gauge Rendering

```javascript
function renderConvergenceGauges(container, metrics) {
  const LANE_COLORS = {
    'A': '#4488ff', 'B': '#00ff88', 'C': '#ff8800',
    'D': '#ff4444', 'E': '#aa44ff', 'F': '#ffcc00'
  };
  const panel = container.append('div').attr('id', 'convergence-panel')
    .style('position', 'fixed').style('bottom', '10px')
    .style('left', '50%').style('transform', 'translateX(-50%)')
    .style('background', '#0a0a1eee').style('border', '1px solid #ff00ff44')
    .style('border-radius', '8px').style('padding', '8px 16px')
    .style('display', 'flex').style('gap', '16px');

  Object.entries(metrics).forEach(([lane, m]) => {
    const gauge = panel.append('div').style('text-align', 'center');
    const color = LANE_COLORS[lane] || '#666';
    const pct = m.convergence_pct || 0;
    const svg = gauge.append('svg').attr('width', 40).attr('height', 40);
    svg.append('circle').attr('cx', 20).attr('cy', 20).attr('r', 16)
      .attr('fill', 'none').attr('stroke', '#222').attr('stroke-width', 3);
    const circ = 2 * Math.PI * 16;
    svg.append('circle').attr('cx', 20).attr('cy', 20).attr('r', 16)
      .attr('fill', 'none').attr('stroke', color).attr('stroke-width', 3)
      .attr('stroke-dasharray', `${(pct/100)*circ} ${circ}`)
      .attr('transform', 'rotate(-90 20 20)');
    svg.append('text').attr('x', 20).attr('y', 24).attr('text-anchor', 'middle')
      .attr('fill', color).attr('font-size', '9px').attr('font-weight', 'bold')
      .text(`${Math.round(pct)}%`);
    gauge.append('div').style('color', color).style('font-size', '8px')
      .style('font-weight', 'bold').text(`Lane ${lane}`);
  });
}
```

## Layer 4: Gap → Acquisition Task Generation

### 4.1 Identify Missing Evidence & Generate Tasks

```python
def generate_acquisition_tasks(db_path: str) -> list:
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout=60000")
    tasks = []
    try:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if 'convergence_todos' in tables:
            rows = conn.execute("""
                SELECT todo_id, title, description, wave_id FROM convergence_todos
                WHERE status = 'PENDING' ORDER BY wave_id LIMIT 20
            """).fetchall()
            for r in rows:
                tasks.append({
                    'type': 'convergence', 'id': r[0], 'title': r[1],
                    'description': r[2], 'wave': r[3], 'priority': 'HIGH'
                })
        if 'filing_readiness' in tables and 'evidence_quotes' in tables:
            rows = conn.execute("""
                SELECT fr.vehicle_name, fr.lane, COUNT(eq.id) as ev_count
                FROM filing_readiness fr
                LEFT JOIN evidence_quotes eq ON eq.lane = fr.lane AND eq.is_duplicate = 0
                GROUP BY fr.vehicle_name, fr.lane HAVING ev_count < 50
            """).fetchall()
            for r in rows:
                tasks.append({
                    'type': 'evidence_gap', 'filing': r[0], 'lane': r[1],
                    'evidence_count': r[2],
                    'title': f"Acquire more evidence for {r[0]} (Lane {r[1]})",
                    'priority': 'CRITICAL' if r[2] < 10 else 'HIGH'
                })
    except Exception:
        pass
    conn.close()
    return tasks
```

## Layer 5: Self-Improvement Cycle Tracking

```javascript
function trackBuildDelta(currentBuild, previousBuild) {
  const delta = {
    nodes_added: currentBuild.nodeCount - (previousBuild?.nodeCount || 0),
    links_added: currentBuild.linkCount - (previousBuild?.linkCount || 0),
    layers_added: currentBuild.layerCount - (previousBuild?.layerCount || 0),
    new_clusters: 0, new_cross_links: 0
  };
  const history = JSON.parse(localStorage.getItem('mbp_build_history') || '[]');
  history.push({ timestamp: new Date().toISOString(), ...currentBuild, delta });
  while (history.length > 50) history.shift();
  localStorage.setItem('mbp_build_history', JSON.stringify(history));
  return delta;
}
```

## Anti-Patterns (15 Rules)

1. NEVER create cross-layer links without evidence of shared entities
2. NEVER run DBSCAN with eps too small — use visual feedback to calibrate
3. NEVER report novelty scores without the entropy calculation
4. NEVER compute convergence without querying live DB state
5. NEVER generate acquisition tasks for CRIMINAL lane (Rule 7 — separate)
6. NEVER cache convergence metrics across sessions — always fresh
7. NEVER display gap counts without traceable SQL queries (Rule 20)
8. NEVER round convergence percentages without stating the denominator
9. NEVER create phantom connections (fabricated cross-links with no basis)
10. NEVER mark a lane as converged without verifying ALL components
11. NEVER skip the evidence_count verification before flagging gaps
12. NEVER display convergence UI during jury presentation mode
13. NEVER compute build deltas without localStorage persistence
14. NEVER assume filing_readiness schema — PRAGMA table_info first
15. NEVER run DBSCAN on >5000 nodes without spatial indexing optimization

## Performance Budgets

| Operation | Budget | Technique |
|-----------|--------|-----------|
| Cross-layer discovery | <500ms | Name/date indexing |
| DBSCAN clustering | <200ms | O(n²) with eps pruning |
| Convergence metrics | <300ms | Single compound SQL |
| Acquisition tasks | <200ms | JOIN with HAVING |
| Build delta | <10ms | localStorage read/write |

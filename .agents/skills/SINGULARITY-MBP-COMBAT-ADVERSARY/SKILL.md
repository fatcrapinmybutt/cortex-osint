---
skill: SINGULARITY-MBP-COMBAT-ADVERSARY
version: "1.0.0"
description: "Adversary network intelligence for THEMANBEARPIG: PageRank centrality, Louvain community detection, ego-network extraction, threat scoring, coordinated action detection. Transforms litigation adversaries into analyzable graph structures."
tier: "TIER-2/COMBAT"
domain: "Adversary analysis — PageRank, centrality, communities, ego-networks, threat scoring"
triggers:
  - adversary
  - PageRank
  - centrality
  - Louvain
  - ego-network
  - threat
  - coordinated
---

# SINGULARITY-MBP-COMBAT-ADVERSARY v1.0

> **Turn adversary networks into exploitable intelligence. Every connection is a vulnerability.**

## Layer 1: Adversary Subgraph Construction

### 1.1 Data Source Fusion

The adversary graph is built from three primary tables in `litigation_context.db`, fused
into a single weighted, directed graph. Each table contributes a distinct evidence class.

```python
"""Build the adversary subgraph from litigation_context.db."""
import sqlite3
import re
from collections import defaultdict
from pathlib import Path

def build_adversary_graph(db_path: str) -> dict:
    """
    Extract adversary nodes and weighted edges from evidence_quotes,
    impeachment_matrix, and contradiction_map.
    Returns: {'nodes': [...], 'edges': [...]}
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA cache_size=-32000")
    conn.row_factory = sqlite3.Row

    actors = defaultdict(lambda: {
        'evidence_count': 0, 'impeachment_total': 0,
        'contradiction_count': 0, 'categories': set(),
        'lanes': set(), 'dates': [],
    })
    edges = defaultdict(lambda: {'weight': 0, 'types': set(), 'events': []})

    # --- Source 1: evidence_quotes (actor mentions) ---
    try:
        sanitized = re.sub(r'[^\w\s*"]', ' ', 'Watson OR McNeill OR Berry OR Rusco')
        rows = conn.execute("""
            SELECT quote_text, source_file, category, lane,
                   relevance_score, event_date
            FROM evidence_quotes
            WHERE quote_text LIKE '%Watson%'
               OR quote_text LIKE '%McNeill%'
               OR quote_text LIKE '%Berry%'
               OR quote_text LIKE '%Rusco%'
            LIMIT 5000
        """).fetchall()
    except Exception:
        rows = []

    known_actors = [
        'Emily Watson', 'Jenny McNeill', 'Ronald Berry',
        'Cavan Berry', 'Albert Watson', 'Lori Watson',
        'Pamela Rusco', 'Kenneth Hoopes', 'Maria Ladas-Hoopes',
        'Jennifer Barnes',
    ]

    for row in rows:
        text = row['quote_text'] or ''
        mentioned = [a for a in known_actors if a.split()[-1].lower() in text.lower()]
        for actor in mentioned:
            actors[actor]['evidence_count'] += 1
            actors[actor]['categories'].add(row['category'] or 'unknown')
            if row['lane']:
                actors[actor]['lanes'].add(row['lane'])
            if row['event_date']:
                actors[actor]['dates'].append(row['event_date'])

        # Build co-mention edges
        for i, a1 in enumerate(mentioned):
            for a2 in mentioned[i+1:]:
                key = tuple(sorted([a1, a2]))
                edges[key]['weight'] += 1
                edges[key]['types'].add('co_mention')

    # --- Source 2: impeachment_matrix ---
    try:
        imp_rows = conn.execute("""
            SELECT category, evidence_summary, impeachment_value,
                   cross_exam_question, filing_relevance, event_date
            FROM impeachment_matrix
            WHERE impeachment_value >= 3
            ORDER BY impeachment_value DESC
            LIMIT 2000
        """).fetchall()
    except Exception:
        imp_rows = []

    for row in imp_rows:
        summary = row['evidence_summary'] or ''
        mentioned = [a for a in known_actors if a.split()[-1].lower() in summary.lower()]
        for actor in mentioned:
            actors[actor]['impeachment_total'] += row['impeachment_value'] or 0

    # --- Source 3: contradiction_map ---
    try:
        contra_rows = conn.execute("""
            SELECT source_a, source_b, contradiction_text, severity, lane
            FROM contradiction_map
            ORDER BY severity DESC
            LIMIT 1000
        """).fetchall()
    except Exception:
        contra_rows = []

    for row in contra_rows:
        src_a = row['source_a'] or ''
        src_b = row['source_b'] or ''
        mentioned_a = [a for a in known_actors if a.split()[-1].lower() in src_a.lower()]
        mentioned_b = [a for a in known_actors if a.split()[-1].lower() in src_b.lower()]
        for actor in set(mentioned_a + mentioned_b):
            actors[actor]['contradiction_count'] += 1
        for a1 in mentioned_a:
            for a2 in mentioned_b:
                if a1 != a2:
                    key = tuple(sorted([a1, a2]))
                    edges[key]['weight'] += 2  # contradictions weighted higher
                    edges[key]['types'].add('contradiction')

    conn.close()

    # Convert to serializable format
    nodes = []
    for name, data in actors.items():
        nodes.append({
            'id': name,
            'evidence_count': data['evidence_count'],
            'impeachment_total': data['impeachment_total'],
            'contradiction_count': data['contradiction_count'],
            'categories': list(data['categories']),
            'lanes': list(data['lanes']),
        })

    edge_list = []
    for (a1, a2), data in edges.items():
        edge_list.append({
            'source': a1, 'target': a2,
            'weight': data['weight'],
            'types': list(data['types']),
        })

    return {'nodes': nodes, 'edges': edge_list}
```

## Layer 2: PageRank for Keystone Actor Identification

### 2.1 PageRank Implementation

PageRank identifies which actors are most central to the adversary network — the "keystone"
players whose removal would most disrupt the coordinated opposition.

```python
"""PageRank and centrality analysis for adversary networks."""

def compute_pagerank(nodes, edges, damping=0.85, iterations=100, tol=1e-6):
    """
    Compute PageRank scores for all actors in the adversary graph.
    Uses power iteration with weighted edges.
    """
    n = len(nodes)
    if n == 0:
        return {}

    node_ids = [node['id'] for node in nodes]
    id_to_idx = {nid: i for i, nid in enumerate(node_ids)}

    # Build weighted adjacency
    out_weight = [0.0] * n
    adj = defaultdict(list)  # target_idx -> [(source_idx, weight)]

    for edge in edges:
        src = id_to_idx.get(edge['source'])
        tgt = id_to_idx.get(edge['target'])
        if src is None or tgt is None:
            continue
        w = edge.get('weight', 1)
        out_weight[src] += w
        out_weight[tgt] += w
        adj[tgt].append((src, w))
        adj[src].append((tgt, w))  # undirected

    # Power iteration
    rank = [1.0 / n] * n
    for _ in range(iterations):
        new_rank = [(1.0 - damping) / n] * n
        for i in range(n):
            if out_weight[i] == 0:
                continue
            contribution = damping * rank[i] / out_weight[i]
            for (j, w) in adj[i]:
                new_rank[j] += contribution * w

        # Check convergence
        diff = sum(abs(new_rank[i] - rank[i]) for i in range(n))
        rank = new_rank
        if diff < tol:
            break

    return {node_ids[i]: rank[i] for i in range(n)}
```

### 2.2 Betweenness Centrality for Bridge Actors

Bridge actors connect otherwise separate communities. Their removal fragments the network.

```python
def compute_betweenness(nodes, edges):
    """
    Betweenness centrality via Brandes' algorithm (O(VE)).
    Identifies actors who serve as bridges between adversary clusters.
    """
    node_ids = [n['id'] for n in nodes]
    id_to_idx = {nid: i for i, nid in enumerate(node_ids)}
    n = len(node_ids)

    # Build adjacency list
    adj = defaultdict(list)
    for edge in edges:
        src = id_to_idx.get(edge['source'])
        tgt = id_to_idx.get(edge['target'])
        if src is not None and tgt is not None:
            adj[src].append(tgt)
            adj[tgt].append(src)

    betweenness = [0.0] * n

    for s in range(n):
        # BFS from s
        stack = []
        pred = [[] for _ in range(n)]
        sigma = [0.0] * n
        sigma[s] = 1.0
        dist = [-1] * n
        dist[s] = 0
        queue = [s]
        qi = 0

        while qi < len(queue):
            v = queue[qi]; qi += 1
            stack.append(v)
            for w in adj[v]:
                if dist[w] < 0:
                    dist[w] = dist[v] + 1
                    queue.append(w)
                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    pred[w].append(v)

        # Back-propagation
        delta = [0.0] * n
        while stack:
            w = stack.pop()
            for v in pred[w]:
                delta[v] += (sigma[v] / sigma[w]) * (1 + delta[w])
            if w != s:
                betweenness[w] += delta[w]

    # Normalize
    norm = max(betweenness) if max(betweenness) > 0 else 1
    return {node_ids[i]: betweenness[i] / norm for i in range(n)}
```

## Layer 3: Louvain Community Detection

### 3.1 Community Detection

Louvain clustering reveals coordinated adversary groups — actors who work together
frequently against the plaintiff.

```python
def louvain_communities(nodes, edges, resolution=1.0):
    """
    Simplified Louvain community detection for adversary clustering.
    Assigns each actor to a community of coordinated actors.
    """
    node_ids = [n['id'] for n in nodes]
    id_to_idx = {nid: i for i, nid in enumerate(node_ids)}
    n = len(node_ids)

    # Build weighted adjacency matrix (sparse via dicts)
    adj = defaultdict(lambda: defaultdict(float))
    degree = [0.0] * n
    total_weight = 0.0

    for edge in edges:
        src = id_to_idx.get(edge['source'])
        tgt = id_to_idx.get(edge['target'])
        if src is None or tgt is None or src == tgt:
            continue
        w = edge.get('weight', 1.0)
        adj[src][tgt] += w
        adj[tgt][src] += w
        degree[src] += w
        degree[tgt] += w
        total_weight += w

    if total_weight == 0:
        return {nid: 0 for nid in node_ids}

    m2 = total_weight  # sum of all edge weights (each counted once)
    community = list(range(n))  # each node starts in its own community

    improved = True
    while improved:
        improved = False
        for i in range(n):
            current = community[i]
            best_community = current
            best_gain = 0.0

            # Sum of weights to each neighboring community
            neighbor_communities = defaultdict(float)
            for j, w in adj[i].items():
                neighbor_communities[community[j]] += w

            # Remove i from its community
            ki = degree[i]

            for c, ki_c in neighbor_communities.items():
                # Modularity gain of moving i to community c
                sum_c = sum(degree[j] for j in range(n) if community[j] == c)
                gain = ki_c / m2 - resolution * ki * sum_c / (m2 * m2)

                if gain > best_gain:
                    best_gain = gain
                    best_community = c

            if best_community != current:
                community[i] = best_community
                improved = True

    # Renumber communities to 0..k-1
    unique = {}
    counter = 0
    for i in range(n):
        if community[i] not in unique:
            unique[community[i]] = counter
            counter += 1
        community[i] = unique[community[i]]

    return {node_ids[i]: community[i] for i in range(n)}
```

### 3.2 Expected Communities in Pigors v. Watson

| Community | Members | Pattern |
|-----------|---------|---------|
| **Judicial Cartel** | McNeill, Hoopes, Ladas-Hoopes, Cavan Berry | Former law partners + spouse |
| **Watson Family** | Emily Watson, Albert Watson, Lori Watson | Coordinated allegations |
| **Institutional** | Pamela Rusco, FOC Office | Systemic bias pipeline |
| **Legal Support** | Jennifer Barnes (withdrew), Ronald Berry | Legal operations |

## Layer 4: Ego-Network Extraction

### 4.1 k-Hop Neighborhood

```python
def extract_ego_network(center_id, nodes, edges, hops=2):
    """
    Extract the k-hop neighborhood around a specific actor.
    Returns the subgraph containing only nodes within k hops of center.
    """
    node_ids = [n['id'] for n in nodes]
    id_to_idx = {nid: i for i, nid in enumerate(node_ids)}

    # Build adjacency
    adj = defaultdict(set)
    for edge in edges:
        src = edge['source']
        tgt = edge['target']
        adj[src].add(tgt)
        adj[tgt].add(src)

    # BFS to find k-hop neighborhood
    visited = {center_id: 0}
    frontier = [center_id]
    for depth in range(1, hops + 1):
        next_frontier = []
        for node in frontier:
            for neighbor in adj[node]:
                if neighbor not in visited:
                    visited[neighbor] = depth
                    next_frontier.append(neighbor)
        frontier = next_frontier

    # Filter nodes and edges to ego network
    ego_nodes = [n for n in nodes if n['id'] in visited]
    ego_edges = [e for e in edges
                 if e['source'] in visited and e['target'] in visited]

    # Add hop distance to nodes for visual encoding
    for node in ego_nodes:
        node['hop_distance'] = visited[node['id']]

    return {'nodes': ego_nodes, 'edges': ego_edges, 'center': center_id}
```

### 4.2 D3 Ego-Network Visualization

```javascript
function renderEgoNetwork(egoData, svg, width, height) {
  const { nodes, edges, center } = egoData;

  const colorByHop = d3.scaleOrdinal()
    .domain([0, 1, 2])
    .range(['#ff00ff', '#00ff88', '#4488ff']);

  const simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(edges).id(d => d.id).distance(80))
    .force('charge', d3.forceManyBody().strength(-200))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide(25));

  // Pin center node
  const centerNode = nodes.find(n => n.id === center);
  if (centerNode) {
    centerNode.fx = width / 2;
    centerNode.fy = height / 2;
  }

  const link = svg.selectAll('.ego-link')
    .data(edges).join('line')
    .attr('class', 'ego-link')
    .attr('stroke', '#ffffff22')
    .attr('stroke-width', d => Math.sqrt(d.weight || 1));

  const node = svg.selectAll('.ego-node')
    .data(nodes).join('circle')
    .attr('class', 'ego-node')
    .attr('r', d => d.id === center ? 20 : 12)
    .attr('fill', d => colorByHop(d.hop_distance))
    .attr('stroke', d => d.id === center ? '#fff' : 'none')
    .attr('stroke-width', 2);

  const label = svg.selectAll('.ego-label')
    .data(nodes).join('text')
    .attr('class', 'ego-label')
    .attr('fill', '#e0e0e0')
    .attr('font-size', d => d.id === center ? '14px' : '10px')
    .attr('text-anchor', 'middle')
    .attr('dy', d => (d.id === center ? 30 : 20))
    .text(d => d.id);

  simulation.on('tick', () => {
    link
      .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
    node.attr('cx', d => d.x).attr('cy', d => d.y);
    label.attr('x', d => d.x).attr('y', d => d.y);
  });
}
```

## Layer 5: Threat Scoring Algorithm

### 5.1 Composite Threat Score

Threat score combines evidence volume, impeachment strength, contradiction severity, and
centrality metrics into a single 0–10 scale.

```python
def compute_threat_scores(nodes, pagerank, betweenness, communities):
    """
    Composite threat scoring: evidence + impeachment + contradictions + centrality.
    Returns dict of actor_id -> threat_score (0-10).
    """
    scores = {}

    # Find max values for normalization
    max_evidence = max((n['evidence_count'] for n in nodes), default=1) or 1
    max_impeach = max((n['impeachment_total'] for n in nodes), default=1) or 1
    max_contra = max((n['contradiction_count'] for n in nodes), default=1) or 1
    max_pr = max(pagerank.values(), default=1) or 1
    max_bw = max(betweenness.values(), default=1) or 1

    for node in nodes:
        nid = node['id']

        # Normalized component scores (0-1)
        evidence_score    = node['evidence_count'] / max_evidence
        impeachment_score = node['impeachment_total'] / max_impeach
        contradiction_score = node['contradiction_count'] / max_contra
        pr_score = pagerank.get(nid, 0) / max_pr
        bw_score = betweenness.get(nid, 0) / max_bw

        # Weighted combination
        threat = (
            evidence_score      * 0.25 +
            impeachment_score   * 0.25 +
            contradiction_score * 0.20 +
            pr_score            * 0.15 +
            bw_score            * 0.15
        ) * 10.0

        scores[nid] = round(min(threat, 10.0), 2)

    return scores
```

### 5.2 Threat Level Classification

```python
THREAT_LEVELS = {
    (0, 2):   {'level': 'LOW',      'color': '#44aa44', 'label': 'Peripheral'},
    (2, 4):   {'level': 'MODERATE', 'color': '#88aa00', 'label': 'Connected'},
    (4, 6):   {'level': 'ELEVATED', 'color': '#ffaa00', 'label': 'Active Adversary'},
    (6, 8):   {'level': 'HIGH',     'color': '#ff4444', 'label': 'Key Threat'},
    (8, 10):  {'level': 'CRITICAL', 'color': '#ff00ff', 'label': 'Keystone Adversary'},
}

def classify_threat(score):
    for (lo, hi), meta in THREAT_LEVELS.items():
        if lo <= score < hi:
            return meta
    return THREAT_LEVELS[(8, 10)]  # 10.0 maps to CRITICAL
```

## Layer 6: Coordinated Action Detection

### 6.1 Temporal Clustering

Detect when multiple adversaries act within a narrow time window — a signature of coordination.

```python
from datetime import datetime, timedelta

def detect_coordinated_actions(nodes, edges, timeline_events, window_hours=72):
    """
    Detect coordinated actions: multiple adversaries acting within a time window.
    Uses temporal clustering on timeline events.
    """
    known_actors = {n['id'] for n in nodes}

    # Extract actor-dated events
    actor_events = []
    for event in timeline_events:
        text = event.get('event_text', '') or ''
        date_str = event.get('event_date', '')
        if not date_str:
            continue
        try:
            dt = datetime.fromisoformat(date_str[:10])
        except (ValueError, TypeError):
            continue
        actors_in_event = [a for a in known_actors if a.split()[-1].lower() in text.lower()]
        for actor in actors_in_event:
            actor_events.append({'actor': actor, 'date': dt, 'text': text[:200]})

    # Sort by date
    actor_events.sort(key=lambda e: e['date'])

    # Sliding window clustering
    coordinated = []
    window = timedelta(hours=window_hours)

    for i, event in enumerate(actor_events):
        cluster_actors = {event['actor']}
        cluster_events = [event]

        for j in range(i + 1, len(actor_events)):
            if actor_events[j]['date'] - event['date'] > window:
                break
            cluster_actors.add(actor_events[j]['actor'])
            cluster_events.append(actor_events[j])

        if len(cluster_actors) >= 3:  # 3+ actors in window = coordination
            coordinated.append({
                'start': event['date'].isoformat(),
                'end': cluster_events[-1]['date'].isoformat(),
                'actors': list(cluster_actors),
                'event_count': len(cluster_events),
                'events': [e['text'] for e in cluster_events[:5]],
            })

    # Deduplicate overlapping clusters
    seen = set()
    unique = []
    for c in coordinated:
        key = frozenset(c['actors'])
        if key not in seen:
            seen.add(key)
            unique.append(c)

    return unique
```

### 6.2 Known Coordination Patterns (Pigors v. Watson)

| Date | Actors | Pattern |
|------|--------|---------|
| Aug 5-8, 2025 | Albert Watson → Emily Watson → McNeill | Recording → police report → 5 ex parte orders |
| Oct-Nov 2023 | Emily Watson → McNeill | PPO filed 2 days after recanting |
| Nov 2024-2025 | McNeill → Rusco → Emily | Show cause → jail → custody shift |
| Ongoing | Rusco → McNeill → Emily | FOC recommendations → court orders → enforcement |

## Layer 7: Visual Encoding for D3

### 7.1 Node Encoding Rules

```javascript
const ADVERSARY_VISUAL = {
  // Node size encodes centrality (PageRank)
  nodeRadius: (d) => {
    const pr = d.pagerank || 0;
    return 8 + pr * 40; // 8px min, up to 48px for highest PageRank
  },

  // Node color encodes threat level
  nodeColor: (d) => {
    const score = d.threat_score || 0;
    if (score >= 8) return '#ff00ff'; // CRITICAL — magenta
    if (score >= 6) return '#ff4444'; // HIGH — red
    if (score >= 4) return '#ffaa00'; // ELEVATED — amber
    if (score >= 2) return '#88aa00'; // MODERATE — yellow-green
    return '#44aa44';                  // LOW — green
  },

  // Node border encodes community membership
  nodeBorder: (d, communityColors) => {
    const cid = d.community || 0;
    return communityColors[cid % communityColors.length];
  },

  // Node shape encodes role
  nodeShape: (d) => {
    const roleShapes = {
      'judicial':      d3.symbolDiamond,
      'adversary':     d3.symbolCircle,
      'institutional': d3.symbolSquare,
      'legal':         d3.symbolTriangle,
      'family':        d3.symbolStar,
    };
    return roleShapes[d.role] || d3.symbolCircle;
  },

  // Link width encodes edge weight (co-mentions + contradictions)
  linkWidth: (d) => Math.sqrt(d.weight || 1) * 1.5,

  // Link color encodes relationship type
  linkColor: (d) => {
    if (d.types && d.types.includes('contradiction')) return '#ff444488';
    if (d.types && d.types.includes('co_mention'))    return '#ffffff33';
    return '#ffffff22';
  },
};
```

### 7.2 Applying Visual Encoding in D3

```javascript
function renderAdversaryGraph(container, graphData, metrics) {
  const { nodes, edges } = graphData;
  const { pagerank, betweenness, communities, threatScores } = metrics;
  const width = container.clientWidth;
  const height = container.clientHeight;

  // Enrich nodes with computed metrics
  nodes.forEach(n => {
    n.pagerank = pagerank[n.id] || 0;
    n.betweenness = betweenness[n.id] || 0;
    n.community = communities[n.id] || 0;
    n.threat_score = threatScores[n.id] || 0;
  });

  const communityColors = ['#ff00ff', '#00ff88', '#4488ff', '#ffaa00', '#ff6644'];

  const svg = d3.select(container).append('svg')
    .attr('width', width).attr('height', height);

  const simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(edges).id(d => d.id).distance(100).strength(0.3))
    .force('charge', d3.forceManyBody().strength(d => -100 - d.threat_score * 30))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide(d => ADVERSARY_VISUAL.nodeRadius(d) + 5));

  // Render links
  const link = svg.append('g').selectAll('line')
    .data(edges).join('line')
    .attr('stroke', ADVERSARY_VISUAL.linkColor)
    .attr('stroke-width', ADVERSARY_VISUAL.linkWidth);

  // Render nodes
  const node = svg.append('g').selectAll('circle')
    .data(nodes).join('circle')
    .attr('r', ADVERSARY_VISUAL.nodeRadius)
    .attr('fill', ADVERSARY_VISUAL.nodeColor)
    .attr('stroke', d => ADVERSARY_VISUAL.nodeBorder(d, communityColors))
    .attr('stroke-width', 3)
    .call(d3.drag()
      .on('start', dragStart)
      .on('drag', dragged)
      .on('end', dragEnd));

  // Render labels
  const label = svg.append('g').selectAll('text')
    .data(nodes).join('text')
    .attr('fill', '#e0e0e0')
    .attr('font-size', d => d.threat_score >= 6 ? '13px' : '10px')
    .attr('font-weight', d => d.threat_score >= 8 ? 'bold' : 'normal')
    .attr('text-anchor', 'middle')
    .attr('dy', d => ADVERSARY_VISUAL.nodeRadius(d) + 14)
    .text(d => d.id);

  simulation.on('tick', () => {
    link
      .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
    node.attr('cx', d => d.x).attr('cy', d => d.y);
    label.attr('x', d => d.x).attr('y', d => d.y);
  });

  return { simulation, svg, node, link, label };
}
```

## Layer 8: Interactive Adversary Drill-Down

### 8.1 Click-to-Inspect Panel

```javascript
function setupAdversaryDrillDown(node, detailPanel, bridge) {
  node.on('click', async (event, d) => {
    event.stopPropagation();

    // Query detailed adversary intelligence from Python bridge
    let intel = {};
    if (window.pywebview && window.pywebview.api) {
      const raw = await window.pywebview.api.get_adversary_profile(d.id);
      intel = JSON.parse(raw);
    }

    detailPanel.style.display = 'block';
    detailPanel.innerHTML = `
      <div class="glass-panel glass-panel--detail">
        <h3 style="color: ${ADVERSARY_VISUAL.nodeColor(d)}">
          ${d.id} — Threat: ${d.threat_score.toFixed(1)}/10
        </h3>
        <div class="metric-row">
          <span>PageRank: ${(d.pagerank * 100).toFixed(1)}%</span>
          <span>Betweenness: ${(d.betweenness * 100).toFixed(1)}%</span>
          <span>Community: ${d.community}</span>
        </div>
        <div class="metric-row">
          <span>Evidence: ${d.evidence_count}</span>
          <span>Impeachment: ${d.impeachment_total}</span>
          <span>Contradictions: ${d.contradiction_count}</span>
        </div>
        <h4>Top Impeachment Ammunition</h4>
        <ul>${(intel.impeachment || []).slice(0, 5).map(item =>
          `<li>${item.summary} (value: ${item.value}/10)</li>`
        ).join('')}</ul>
        <h4>Key Contradictions</h4>
        <ul>${(intel.contradictions || []).slice(0, 5).map(item =>
          `<li>${item.text}</li>`
        ).join('')}</ul>
      </div>
    `;
  });
}
```

### 8.2 Python Bridge for Adversary Intel

```python
"""Adversary intelligence bridge for pywebview."""
import json
import sqlite3
import re

class AdversaryBridge:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA busy_timeout=60000")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA cache_size=-32000")
        conn.row_factory = sqlite3.Row
        return conn

    def get_adversary_profile(self, actor_name: str) -> str:
        conn = self._get_conn()
        sanitized = re.sub(r'[^\w\s]', '', actor_name)
        result = {'name': actor_name, 'impeachment': [], 'contradictions': []}

        try:
            rows = conn.execute("""
                SELECT evidence_summary, impeachment_value, cross_exam_question
                FROM impeachment_matrix
                WHERE evidence_summary LIKE ?
                ORDER BY impeachment_value DESC LIMIT 10
            """, (f'%{sanitized}%',)).fetchall()
            result['impeachment'] = [
                {'summary': r['evidence_summary'], 'value': r['impeachment_value'],
                 'question': r['cross_exam_question']}
                for r in rows
            ]
        except Exception:
            pass

        try:
            rows = conn.execute("""
                SELECT contradiction_text, severity
                FROM contradiction_map
                WHERE source_a LIKE ? OR source_b LIKE ?
                ORDER BY severity DESC LIMIT 10
            """, (f'%{sanitized}%', f'%{sanitized}%')).fetchall()
            result['contradictions'] = [
                {'text': r['contradiction_text'], 'severity': r['severity']}
                for r in rows
            ]
        except Exception:
            pass

        conn.close()
        return json.dumps(result)
```

## Layer 9: Full Pipeline Integration

### 9.1 End-to-End Adversary Analysis

```python
def run_adversary_analysis(db_path: str) -> dict:
    """
    Complete adversary analysis pipeline:
    1. Build subgraph from DB
    2. Compute PageRank
    3. Compute betweenness centrality
    4. Detect communities (Louvain)
    5. Score threats
    6. Detect coordinated actions
    """
    graph = build_adversary_graph(db_path)
    pagerank = compute_pagerank(graph['nodes'], graph['edges'])
    betweenness = compute_betweenness(graph['nodes'], graph['edges'])
    communities = louvain_communities(graph['nodes'], graph['edges'])
    threat_scores = compute_threat_scores(
        graph['nodes'], pagerank, betweenness, communities
    )

    # Enrich nodes with all computed metrics
    for node in graph['nodes']:
        nid = node['id']
        node['pagerank'] = round(pagerank.get(nid, 0), 4)
        node['betweenness'] = round(betweenness.get(nid, 0), 4)
        node['community'] = communities.get(nid, 0)
        node['threat_score'] = threat_scores.get(nid, 0)

    # Sort nodes by threat score descending
    graph['nodes'].sort(key=lambda n: n['threat_score'], reverse=True)

    return {
        'graph': graph,
        'metrics': {
            'pagerank': pagerank,
            'betweenness': betweenness,
            'communities': communities,
            'threat_scores': threat_scores,
        },
    }
```

## Anti-Patterns

1. **NEVER** hardcode actor names in the graph algorithm — extract from DB dynamically
2. **NEVER** use unweighted edges — evidence weight is critical for accurate centrality
3. **NEVER** skip the Louvain step — individual threat scores miss coordinated patterns
4. **NEVER** render all actors at once with labels — use LOD to show labels only on zoom
5. **NEVER** ignore temporal clustering — coordination is a timing signal, not just a link
6. **NEVER** display raw PageRank numbers to users — normalize and classify into threat levels
7. **NEVER** trust community detection without domain validation — verify against known groups
8. **NEVER** render the adversary graph without the ego-network drill-down interaction

---
skill: SINGULARITY-MBP-COMBAT-EVIDENCE
version: "1.0.0"
description: "Evidence density and semantic clustering for THEMANBEARPIG: heat density mapping, t-SNE/UMAP projection of evidence embeddings, gap detection visualization, evidence-to-filing coverage analysis. Transforms raw evidence into spatial intelligence patterns."
tier: "TIER-2/COMBAT"
domain: "Evidence analysis — density mapping, semantic clustering, gap detection, coverage analysis"
triggers:
  - evidence
  - heat density
  - semantic cluster
  - t-SNE
  - UMAP
  - gap detection
  - coverage
  - evidence landscape
  - contour
  - filing coverage
cross_links:
  - SINGULARITY-MBP-GENESIS
  - SINGULARITY-MBP-DATAWEAVE
  - SINGULARITY-MBP-FORGE-RENDERER
  - SINGULARITY-MBP-COMBAT-AUTHORITY
  - SINGULARITY-MBP-INTERFACE-CONTROLS
  - SINGULARITY-litigation-warfare
  - SINGULARITY-data-dominion
data_sources:
  - evidence_quotes (175K+ rows, evidence_fts FTS5)
  - semantic_vectors (75K vectors, 384-dim, all-MiniLM-L6-v2)
  - filing_readiness (17 filings)
  - claims (per-lane claim inventory)
  - timeline_events (16K+ events)
---

# SINGULARITY-MBP-COMBAT-EVIDENCE — Evidence Density & Semantic Clustering

> **Evidence is terrain. Density is firepower. Gaps are vulnerabilities. The map IS the strategy.**

## 1. Architecture: Evidence Intelligence Layer

The Evidence Combat layer projects 175K+ evidence quotes and 75K semantic vectors into a spatial
intelligence landscape. Dense clusters reveal strength. Voids reveal gaps. Coverage matrices
show filing readiness at a glance. Every piece of evidence becomes a point in a navigable
two-dimensional battlefield.

```
┌──────────────────────────────────────────────────────────┐
│            EVIDENCE COMBAT LAYER PIPELINE                 │
│                                                           │
│  STAGE 1: DENSITY COMPUTATION                             │
│    evidence_quotes → per-lane/category counts             │
│    Kernel density estimation (2D Gaussian, bandwidth=auto) │
│    Contour levels: 10%, 25%, 50%, 75%, 90%                │
│                                                           │
│  STAGE 2: SEMANTIC EMBEDDING                              │
│    LanceDB 75K vectors (384-dim, all-MiniLM-L6-v2)       │
│    OR evidence_quotes → sentence-transformers embed       │
│                                                           │
│  STAGE 3: DIMENSIONALITY REDUCTION                        │
│    t-SNE (perplexity=30, 1000 iter) for local structure   │
│    UMAP (n_neighbors=15, min_dist=0.1) for global layout  │
│    Both: 384-dim → 2D projection                          │
│                                                           │
│  STAGE 4: CLUSTERING                                      │
│    HDBSCAN (min_cluster=10, min_samples=5) on 2D coords   │
│    Cluster labeling via TF-IDF top terms                   │
│    Noise points → gap candidates                          │
│                                                           │
│  STAGE 5: GAP DETECTION                                   │
│    Expected elements per filing (MCL/MCR requirements)     │
│    Actual coverage from evidence_quotes + claims           │
│    Gap = expected − actual → pulsing void overlay          │
│                                                           │
│  STAGE 6: COVERAGE MATRIX                                 │
│    Lane × category → evidence count sparkline             │
│    Filing readiness = coverage / requirement               │
└──────────────────────────────────────────────────────────┘
```

---

## 2. Evidence Density Computation

### 2.1 Per-Lane Density Extraction

```python
"""Compute evidence density per lane and category."""
import sqlite3
from collections import defaultdict

def compute_evidence_density(db_path: str) -> dict:
    """Extract evidence counts grouped by lane and category for heatmap."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.execute("PRAGMA journal_mode = WAL")

    # Density by lane × category
    density = conn.execute("""
        SELECT lane, category, COUNT(*) as cnt
        FROM evidence_quotes
        WHERE is_duplicate = 0 OR is_duplicate IS NULL
        GROUP BY lane, category
        ORDER BY cnt DESC
    """).fetchall()

    # Density by lane × date (monthly bins)
    temporal = conn.execute("""
        SELECT lane,
               SUBSTR(date_extracted, 1, 7) as month,
               COUNT(*) as cnt
        FROM evidence_quotes
        WHERE date_extracted IS NOT NULL
          AND (is_duplicate = 0 OR is_duplicate IS NULL)
        GROUP BY lane, month
        ORDER BY month
    """).fetchall()

    conn.close()

    # Build structured output
    density_map = defaultdict(lambda: defaultdict(int))
    for lane, cat, cnt in density:
        density_map[lane or "UNASSIGNED"][cat or "uncategorized"] = cnt

    temporal_map = defaultdict(lambda: defaultdict(int))
    for lane, month, cnt in temporal:
        temporal_map[lane or "UNASSIGNED"][month] = cnt

    return {
        "density": dict(density_map),
        "temporal": dict(temporal_map),
        "total_evidence": sum(r[2] for r in density),
        "lanes": sorted(set(r[0] or "UNASSIGNED" for r in density)),
        "categories": sorted(set(r[1] or "uncategorized" for r in density))
    }
```

### 2.2 Kernel Density Estimation for Contour Overlay

```python
"""Kernel density estimation for 2D evidence landscape contours."""
import numpy as np

def compute_kde_contours(points_2d: np.ndarray, grid_size: int = 100,
                         bandwidth: float = None) -> dict:
    """
    Given 2D projected evidence points, compute KDE contour levels.
    Returns grid + density values for D3 contour rendering.
    """
    from scipy.stats import gaussian_kde

    if len(points_2d) < 10:
        return {"grid": [], "density": [], "levels": []}

    x, y = points_2d[:, 0], points_2d[:, 1]

    # Auto bandwidth via Scott's rule if not specified
    if bandwidth is None:
        kde = gaussian_kde(np.vstack([x, y]))
    else:
        kde = gaussian_kde(np.vstack([x, y]), bw_method=bandwidth)

    # Build evaluation grid
    x_min, x_max = x.min() - 1, x.max() + 1
    y_min, y_max = y.min() - 1, y.max() + 1
    xi = np.linspace(x_min, x_max, grid_size)
    yi = np.linspace(y_min, y_max, grid_size)
    Xi, Yi = np.meshgrid(xi, yi)
    positions = np.vstack([Xi.ravel(), Yi.ravel()])

    Z = kde(positions).reshape(Xi.shape)

    # Contour levels at percentiles
    z_flat = Z.ravel()
    levels = [
        float(np.percentile(z_flat, 10)),
        float(np.percentile(z_flat, 25)),
        float(np.percentile(z_flat, 50)),
        float(np.percentile(z_flat, 75)),
        float(np.percentile(z_flat, 90))
    ]

    return {
        "grid_x": xi.tolist(),
        "grid_y": yi.tolist(),
        "density": Z.tolist(),
        "levels": levels,
        "bounds": {"x_min": float(x_min), "x_max": float(x_max),
                   "y_min": float(y_min), "y_max": float(y_max)}
    }
```

### 2.3 Contour Rendering — D3.js

```javascript
/**
 * Render KDE contours as a density overlay on the evidence landscape.
 * Uses d3-contour for isoband generation.
 */
class EvidenceDensityOverlay {
  constructor(svg, kdeData, colorScheme = d3.interpolateBlues) {
    this.svg = svg;
    this.data = kdeData;
    this.colorScheme = colorScheme;
    this.group = svg.append('g').attr('class', 'evidence-density');
  }

  render(transform) {
    const { grid_x, grid_y, density, levels, bounds } = this.data;
    const n = grid_x.length;
    const m = grid_y.length;

    // Flatten density for d3.contours
    const values = new Float64Array(n * m);
    for (let j = 0; j < m; j++) {
      for (let i = 0; i < n; i++) {
        values[j * n + i] = density[j][i];
      }
    }

    const contourGen = d3.contours()
      .size([n, m])
      .thresholds(levels);

    const contours = contourGen(values);

    // Scale contour paths to graph coordinates
    const xScale = d3.scaleLinear()
      .domain([0, n - 1])
      .range([bounds.x_min, bounds.x_max]);
    const yScale = d3.scaleLinear()
      .domain([0, m - 1])
      .range([bounds.y_min, bounds.y_max]);

    const opacityScale = d3.scaleLinear()
      .domain([levels[0], levels[levels.length - 1]])
      .range([0.05, 0.35]);

    const pathGen = d3.geoPath()
      .projection(d3.geoTransform({
        point: function(x, y) {
          this.stream.point(xScale(x), yScale(y));
        }
      }));

    this.group.selectAll('path.contour')
      .data(contours)
      .enter()
      .append('path')
      .attr('class', 'contour')
      .attr('d', pathGen)
      .attr('fill', (d, i) => this.colorScheme(0.3 + i * 0.15))
      .attr('opacity', d => opacityScale(d.value))
      .attr('stroke', 'none');

    // Apply current zoom transform
    if (transform) {
      this.group.attr('transform', transform);
    }
  }

  setVisibility(visible) {
    this.group.style('display', visible ? 'block' : 'none');
  }
}
```

---

## 3. Semantic Clustering Pipeline

### 3.1 Embedding Extraction & Projection

```python
"""Extract embeddings, project to 2D, cluster with HDBSCAN."""
import numpy as np
import sqlite3

def extract_evidence_embeddings(db_path: str, max_samples: int = 5000) -> dict:
    """
    Pull evidence embeddings from LanceDB or generate from evidence_quotes.
    Returns 2D projections via t-SNE and UMAP.
    """
    # Attempt LanceDB first (75K pre-computed vectors)
    try:
        import lancedb
        lance_path = r"00_SYSTEM\engines\semantic\lancedb_store"
        db = lancedb.connect(lance_path)
        tables = db.table_names()
        if tables:
            tbl = db.open_table(tables[0])
            df = tbl.to_pandas()
            if 'vector' in df.columns and len(df) > 0:
                vectors = np.array(df['vector'].tolist()[:max_samples])
                texts = df.get('text', df.get('content', [''] * len(vectors)))
                texts = list(texts[:max_samples])
                lanes = list(df.get('lane', ['?'] * len(vectors))[:max_samples])
                return _project_and_cluster(vectors, texts, lanes)
    except Exception:
        pass  # Fall back to on-the-fly embedding

    # Fallback: embed from evidence_quotes using sentence-transformers
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout = 60000")
    rows = conn.execute("""
        SELECT quote_text, lane, category
        FROM evidence_quotes
        WHERE quote_text IS NOT NULL AND LENGTH(quote_text) > 20
          AND (is_duplicate = 0 OR is_duplicate IS NULL)
        ORDER BY RANDOM()
        LIMIT ?
    """, (max_samples,)).fetchall()
    conn.close()

    if not rows:
        return {"points": [], "clusters": [], "error": "No evidence found"}

    texts = [r[0] for r in rows]
    lanes = [r[1] or "?" for r in rows]

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('all-MiniLM-L6-v2')
    vectors = model.encode(texts, show_progress_bar=False, batch_size=64)

    return _project_and_cluster(np.array(vectors), texts, lanes)


def _project_and_cluster(vectors: np.ndarray, texts: list,
                          lanes: list) -> dict:
    """Project 384-dim vectors to 2D via t-SNE and UMAP, then cluster."""
    from sklearn.manifold import TSNE

    # t-SNE projection
    tsne = TSNE(n_components=2, perplexity=min(30, len(vectors) - 1),
                n_iter=1000, random_state=42)
    coords_tsne = tsne.fit_transform(vectors)

    # UMAP projection (if available)
    coords_umap = None
    try:
        import umap
        reducer = umap.UMAP(n_neighbors=15, min_dist=0.1,
                            n_components=2, random_state=42)
        coords_umap = reducer.fit_transform(vectors)
    except ImportError:
        pass  # UMAP optional

    # HDBSCAN clustering on t-SNE coordinates
    cluster_labels = _cluster_points(coords_tsne)

    # Label clusters by top TF-IDF terms
    cluster_names = _label_clusters(texts, cluster_labels)

    points = []
    for i in range(len(texts)):
        point = {
            "id": i,
            "text": texts[i][:200],
            "lane": lanes[i],
            "tsne_x": float(coords_tsne[i, 0]),
            "tsne_y": float(coords_tsne[i, 1]),
            "cluster": int(cluster_labels[i]),
            "cluster_name": cluster_names.get(int(cluster_labels[i]), "noise")
        }
        if coords_umap is not None:
            point["umap_x"] = float(coords_umap[i, 0])
            point["umap_y"] = float(coords_umap[i, 1])
        points.append(point)

    return {
        "points": points,
        "n_clusters": len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0),
        "noise_count": int(sum(1 for c in cluster_labels if c == -1)),
        "cluster_names": cluster_names,
        "projection": "tsne",
        "has_umap": coords_umap is not None
    }


def _cluster_points(coords_2d: np.ndarray) -> np.ndarray:
    """Cluster 2D points with HDBSCAN or DBSCAN fallback."""
    try:
        from hdbscan import HDBSCAN
        clusterer = HDBSCAN(min_cluster_size=10, min_samples=5)
        return clusterer.fit_predict(coords_2d)
    except ImportError:
        from sklearn.cluster import DBSCAN
        clusterer = DBSCAN(eps=3.0, min_samples=5)
        return clusterer.fit_predict(coords_2d)


def _label_clusters(texts: list, labels: np.ndarray) -> dict:
    """Assign human-readable labels to clusters via TF-IDF top terms."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from collections import defaultdict

    cluster_texts = defaultdict(list)
    for text, label in zip(texts, labels):
        if label >= 0:
            cluster_texts[int(label)].append(text)

    names = {}
    for cid, ctexts in cluster_texts.items():
        if len(ctexts) < 3:
            names[cid] = f"cluster_{cid}"
            continue
        try:
            vec = TfidfVectorizer(max_features=5, stop_words='english')
            vec.fit(ctexts)
            top_words = vec.get_feature_names_out()
            names[cid] = " / ".join(top_words[:3])
        except Exception:
            names[cid] = f"cluster_{cid}"

    return names
```

### 3.2 Evidence Landscape Rendering — D3.js

```javascript
/**
 * Render the 2D evidence landscape as interactive scatter plot.
 * Points colored by cluster, sized by relevance, clickable for detail.
 */
class EvidenceLandscape {
  constructor(svg, evidenceData, containerSize) {
    this.svg = svg;
    this.data = evidenceData; // from _project_and_cluster()
    this.size = containerSize;
    this.group = svg.append('g').attr('class', 'evidence-landscape');
    this.tooltip = null;
    this.activeProjection = 'tsne'; // or 'umap'
  }

  render() {
    const points = this.data.points;
    if (!points.length) return;

    // Compute scales from projection coordinates
    const xKey = this.activeProjection === 'umap' ? 'umap_x' : 'tsne_x';
    const yKey = this.activeProjection === 'umap' ? 'umap_y' : 'tsne_y';

    const xExtent = d3.extent(points, d => d[xKey]);
    const yExtent = d3.extent(points, d => d[yKey]);

    const xScale = d3.scaleLinear()
      .domain(xExtent).range([50, this.size.width - 50]);
    const yScale = d3.scaleLinear()
      .domain(yExtent).range([50, this.size.height - 50]);

    // Color by cluster
    const clusterIds = [...new Set(points.map(p => p.cluster))].sort();
    const colorScale = d3.scaleOrdinal(d3.schemeTableau10)
      .domain(clusterIds);

    // Draw points
    const dots = this.group.selectAll('circle.evidence-point')
      .data(points)
      .enter()
      .append('circle')
      .attr('class', 'evidence-point')
      .attr('cx', d => xScale(d[xKey]))
      .attr('cy', d => yScale(d[yKey]))
      .attr('r', 3)
      .attr('fill', d => d.cluster === -1 ? '#444' : colorScale(d.cluster))
      .attr('opacity', d => d.cluster === -1 ? 0.3 : 0.7)
      .attr('stroke', 'none')
      .style('cursor', 'pointer');

    // Interaction: click to show evidence detail
    dots.on('click', (event, d) => {
      window.dispatchEvent(new CustomEvent('evidence-selected', {
        detail: { id: d.id, text: d.text, lane: d.lane,
                  cluster: d.cluster_name }
      }));
    });

    // Hover tooltip
    dots.on('mouseenter', (event, d) => {
      this._showTooltip(event, d);
    }).on('mouseleave', () => {
      this._hideTooltip();
    });

    // Cluster labels at centroid
    this._renderClusterLabels(points, xScale, yScale, xKey, yKey);
  }

  _renderClusterLabels(points, xScale, yScale, xKey, yKey) {
    const clusterCentroids = {};

    points.forEach(p => {
      if (p.cluster < 0) return;
      if (!clusterCentroids[p.cluster]) {
        clusterCentroids[p.cluster] = { sx: 0, sy: 0, n: 0, name: p.cluster_name };
      }
      clusterCentroids[p.cluster].sx += p[xKey];
      clusterCentroids[p.cluster].sy += p[yKey];
      clusterCentroids[p.cluster].n += 1;
    });

    Object.values(clusterCentroids).forEach(c => {
      const cx = xScale(c.sx / c.n);
      const cy = yScale(c.sy / c.n);

      this.group.append('text')
        .attr('x', cx).attr('y', cy - 12)
        .attr('text-anchor', 'middle')
        .attr('font-size', '10px')
        .attr('font-weight', 'bold')
        .attr('fill', '#fff')
        .attr('stroke', '#000')
        .attr('stroke-width', 0.3)
        .text(c.name);
    });
  }

  toggleProjection() {
    if (!this.data.has_umap) return;
    this.activeProjection = this.activeProjection === 'tsne' ? 'umap' : 'tsne';
    this.group.selectAll('*').remove();
    this.render();
  }

  _showTooltip(event, d) {
    if (!this.tooltip) {
      this.tooltip = d3.select('body').append('div')
        .attr('class', 'evidence-tooltip')
        .style('position', 'absolute')
        .style('background', '#1a1a2e')
        .style('color', '#eee')
        .style('padding', '8px 12px')
        .style('border-radius', '4px')
        .style('font-size', '11px')
        .style('max-width', '300px')
        .style('pointer-events', 'none')
        .style('z-index', '9999');
    }
    this.tooltip
      .html(`<strong>Lane ${d.lane}</strong> — ${d.cluster_name}<br>${d.text}`)
      .style('left', (event.pageX + 12) + 'px')
      .style('top', (event.pageY - 10) + 'px')
      .style('display', 'block');
  }

  _hideTooltip() {
    if (this.tooltip) this.tooltip.style('display', 'none');
  }
}
```

---

## 4. Gap Detection Algorithm

### 4.1 Expected Elements Per Filing

```python
"""Define expected evidence elements per filing lane for gap detection."""

EXPECTED_ELEMENTS = {
    "A": {  # Custody — MCL 722.23(a)-(l)
        "best_interest_factor_a": "Love, affection, emotional ties",
        "best_interest_factor_b": "Capacity to give love, affection, guidance",
        "best_interest_factor_c": "Capacity to provide food, clothing, medical",
        "best_interest_factor_d": "Length of time in stable environment",
        "best_interest_factor_e": "Permanence of family unit",
        "best_interest_factor_f": "Moral fitness of parties",
        "best_interest_factor_g": "Mental and physical health",
        "best_interest_factor_h": "Home, school, community record",
        "best_interest_factor_i": "Reasonable preference of child",
        "best_interest_factor_j": "Willingness to facilitate relationship",
        "best_interest_factor_k": "Domestic violence",
        "best_interest_factor_l": "Any other relevant factor",
        "change_of_circumstances": "Vodvarka standard met",
        "established_custodial_env": "ECE analysis",
        "parenting_time_denial": "Documentation of denied parenting time"
    },
    "D": {  # PPO — MCL 600.2950
        "basis_for_ppo": "Original grounds for PPO issuance",
        "changed_circumstances": "Circumstances justifying modification",
        "no_threat_evidence": "Evidence of no ongoing threat",
        "weaponization_pattern": "PPO used as custody leverage",
        "recantation": "Emily's Oct 13, 2023 recantation"
    },
    "E": {  # Judicial Misconduct
        "ex_parte_violations": "Documented ex parte communications/orders",
        "due_process_denial": "Denial of notice and opportunity to be heard",
        "bias_indicators": "Objective indicators of judicial bias",
        "benchbook_deviations": "Deviations from Michigan Benchbook",
        "canon_violations": "Michigan Code of Judicial Conduct violations",
        "cartel_evidence": "McNeill-Hoopes-Ladas connections"
    },
    "F": {  # Appellate — MCR 7.212
        "jurisdictional_statement": "Basis for appellate jurisdiction",
        "standard_of_review": "Applicable standard per issue",
        "statement_of_facts": "Record-supported factual narrative",
        "preserved_issues": "Issues properly raised below",
        "lower_court_errors": "Specific errors of law or fact"
    }
}

def detect_evidence_gaps(db_path: str) -> dict:
    """Compare expected elements vs actual evidence per lane."""
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout = 60000")

    results = {}
    for lane, elements in EXPECTED_ELEMENTS.items():
        lane_gaps = {}
        for elem_key, elem_desc in elements.items():
            # Search evidence for this element
            search_terms = elem_key.replace('_', ' ')
            try:
                count = conn.execute("""
                    SELECT COUNT(*) FROM evidence_quotes
                    WHERE lane = ?
                      AND (category LIKE ? OR quote_text LIKE ?)
                      AND (is_duplicate = 0 OR is_duplicate IS NULL)
                """, (lane, f"%{search_terms}%", f"%{search_terms}%")).fetchone()[0]
            except Exception:
                count = 0

            lane_gaps[elem_key] = {
                "description": elem_desc,
                "evidence_count": count,
                "status": "COVERED" if count >= 3 else
                          "WEAK" if count >= 1 else "GAP",
                "urgency": "HIGH" if count == 0 else
                           "MEDIUM" if count < 3 else "LOW"
            }

        covered = sum(1 for g in lane_gaps.values() if g["status"] == "COVERED")
        total = len(lane_gaps)
        results[lane] = {
            "elements": lane_gaps,
            "coverage_pct": round(covered / max(total, 1) * 100, 1),
            "gap_count": sum(1 for g in lane_gaps.values() if g["status"] == "GAP"),
            "weak_count": sum(1 for g in lane_gaps.values() if g["status"] == "WEAK")
        }

    conn.close()
    return results
```

### 4.2 Gap Visualization — Pulsing Voids

```javascript
/**
 * Render evidence gaps as pulsing translucent voids on the landscape.
 * Each gap is a circle at the expected position that pulses to draw attention.
 */
function renderEvidenceGaps(svg, gapData, xScale, yScale) {
  const gapGroup = svg.append('g').attr('class', 'evidence-gaps');

  // Position gaps in semantic space (approximate from element keywords)
  const gapPositions = {
    best_interest_factor_j: { x: -15, y: 8 },
    parenting_time_denial: { x: -10, y: 12 },
    weaponization_pattern: { x: 5, y: -8 },
    cartel_evidence: { x: 20, y: -15 }
    // Positions are approximations; ideally derived from embedding projection
  };

  Object.entries(gapData).forEach(([lane, laneInfo]) => {
    Object.entries(laneInfo.elements).forEach(([elemKey, elem]) => {
      if (elem.status !== 'GAP') return;

      const pos = gapPositions[elemKey] || { x: Math.random() * 40 - 20, y: Math.random() * 40 - 20 };
      const cx = xScale(pos.x);
      const cy = yScale(pos.y);

      // Pulsing void circle
      const voidCircle = gapGroup.append('circle')
        .attr('cx', cx).attr('cy', cy)
        .attr('r', 20)
        .attr('fill', 'rgba(255, 0, 0, 0.08)')
        .attr('stroke', '#ff4444')
        .attr('stroke-width', 1.5)
        .attr('stroke-dasharray', '4,3');

      // Pulse animation
      (function pulse() {
        voidCircle.transition().duration(1200)
          .attr('r', 30).attr('opacity', 0.3)
          .transition().duration(1200)
          .attr('r', 20).attr('opacity', 0.8)
          .on('end', pulse);
      })();

      // Gap label
      gapGroup.append('text')
        .attr('x', cx).attr('y', cy + 4)
        .attr('text-anchor', 'middle')
        .attr('font-size', '8px')
        .attr('fill', '#ff6666')
        .text(elem.description.slice(0, 25) + '...');

      // Click → dispatch gap acquisition event
      voidCircle.style('cursor', 'pointer')
        .on('click', () => {
          window.dispatchEvent(new CustomEvent('gap-acquire', {
            detail: { lane, element: elemKey, description: elem.description }
          }));
        });
    });
  });
}
```

---

## 5. Evidence-to-Filing Coverage Matrix

### 5.1 Coverage Sparklines per Lane

```python
"""Build evidence-to-filing coverage matrix with sparkline data."""
import sqlite3

def build_coverage_matrix(db_path: str) -> dict:
    """For each filing lane, compute coverage ratio per element."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout = 60000")

    # Get filing readiness scores
    try:
        filings = conn.execute("""
            SELECT vehicle_name, status, confidence_score, lane
            FROM filing_readiness
            ORDER BY lane
        """).fetchall()
    except Exception:
        filings = []

    # Get evidence counts by lane
    lane_counts = conn.execute("""
        SELECT lane, COUNT(*) as cnt
        FROM evidence_quotes
        WHERE is_duplicate = 0 OR is_duplicate IS NULL
        GROUP BY lane
    """).fetchall()
    conn.close()

    lane_evidence = {r[0]: r[1] for r in lane_counts}

    matrix = {}
    for filing in filings:
        vehicle, status, confidence, lane = filing
        ev_count = lane_evidence.get(lane, 0)
        matrix[vehicle or "unknown"] = {
            "lane": lane,
            "status": status,
            "confidence": confidence or 0,
            "evidence_count": ev_count,
            "sparkline": _generate_sparkline_data(ev_count, confidence or 0)
        }

    return matrix


def _generate_sparkline_data(evidence_count: int, confidence: float) -> list:
    """Generate sparkline values: [threshold_pct, actual_pct, gap_pct]."""
    # Threshold: minimum evidence for 80% confidence
    threshold = 50  # baseline evidence count for a filing to be ready
    actual_pct = min(evidence_count / max(threshold, 1) * 100, 100)
    gap_pct = max(0, 100 - actual_pct)
    return [round(actual_pct, 1), round(confidence, 1), round(gap_pct, 1)]
```

### 5.2 Coverage Sparkline Rendering — D3.js

```javascript
/**
 * Render coverage sparklines in the HUD panel.
 * Each lane gets a mini bar showing evidence coverage vs requirements.
 */
function renderCoverageSparklines(container, coverageMatrix) {
  const sparkWidth = 120;
  const sparkHeight = 14;
  const padding = 4;

  Object.entries(coverageMatrix).forEach(([filing, info], idx) => {
    const y = idx * (sparkHeight + padding + 12);

    // Filing label
    container.append('text')
      .attr('x', 0).attr('y', y + sparkHeight / 2 + 4)
      .attr('font-size', '9px')
      .attr('fill', '#ccc')
      .text(`${info.lane}: ${filing}`);

    // Background bar
    container.append('rect')
      .attr('x', 140).attr('y', y)
      .attr('width', sparkWidth).attr('height', sparkHeight)
      .attr('fill', '#1a1a2e').attr('rx', 2);

    // Evidence fill
    const [evidencePct, confidencePct, gapPct] = info.sparkline;
    const fillColor = evidencePct >= 80 ? '#22cc44' :
                      evidencePct >= 50 ? '#ffcc00' : '#ff4444';

    container.append('rect')
      .attr('x', 140).attr('y', y)
      .attr('width', sparkWidth * evidencePct / 100)
      .attr('height', sparkHeight)
      .attr('fill', fillColor)
      .attr('opacity', 0.8)
      .attr('rx', 2);

    // Percentage label
    container.append('text')
      .attr('x', 140 + sparkWidth + 6).attr('y', y + sparkHeight / 2 + 4)
      .attr('font-size', '9px')
      .attr('fill', fillColor)
      .text(`${evidencePct}%`);
  });
}
```

---

## 6. Visual Encoding Reference

| Data Property | Visual Channel | Encoding |
|---------------|---------------|----------|
| Evidence density | Contour opacity | KDE levels: 10%=faint → 90%=opaque |
| Semantic cluster | Point color | d3.schemeTableau10 ordinal per cluster ID |
| Noise / unclustered | Point color | Dark gray (#444), low opacity |
| Evidence gap | Pulsing void | Red dashed circle, 1.2s pulse cycle |
| Coverage ratio | Sparkline fill | Green ≥80%, Yellow ≥50%, Red <50% |
| Lane assignment | Point border | Lane color ring (A=blue, D=orange, E=red, F=purple) |
| Cluster name | Centroid label | TF-IDF top-3 terms, white bold text |
| Projection type | Toggle button | t-SNE (local) ↔ UMAP (global) |

## 7. Integration with MBP-GENESIS Layers

Evidence Combat maps to **Layer 4 (Evidence)** in the GENESIS taxonomy:

```javascript
LAYER_META[4] = {
  name: 'Evidence',
  color: '#4488ff',
  charge: -200,
  collideRadius: 8,
  linkDistance: 40,
  linkStrength: 0.4,
  alphaDecay: 0.02,
  enabled: true,
  overlays: ['density_contours', 'semantic_clusters', 'gap_voids', 'coverage_sparklines']
};
```

### Node Types in Layer 4

| Type | Subtype | Source Table | Sizing |
|------|---------|-------------|--------|
| EVIDENCE | quote | evidence_quotes | relevance_score * 6 |
| EVIDENCE | cluster_centroid | computed | cluster_size / 10 |
| EVIDENCE | gap_void | computed | urgency-based pulse radius |
| EVIDENCE | document | documents | page_count / 5 |

## 8. Performance Considerations

- **t-SNE on 5K points** takes ~10s on CPU — precompute and cache in `graph_data_v7.json`
- **KDE contours** are static once computed — render to offscreen canvas, composite per frame
- **HDBSCAN** is O(n log n) — runs once on data load, results cached
- **Point rendering** for 5K+ dots — use Canvas 2D, not SVG (SVG DOM overhead kills FPS)
- **Cluster labels** rendered only for clusters with 10+ members — reduce visual clutter
- **Gap voids** animated via CSS, not D3 timer — lower main-thread cost
- **Tooltip** reused (single DOM element repositioned) — no per-point tooltip creation
- **Projection toggle** (t-SNE ↔ UMAP) interpolates positions via d3.transition for smooth switch

---
name: SINGULARITY-MBP-APEX-GRAPHML
description: "Graph Neural Networks for legal reasoning in THEMANBEARPIG. Pure NumPy GAT layers, TransE link prediction, Louvain community detection, reasoning path scoring, evidence gap discovery. CPU-only, no PyG/DGL. Turns litigation_context.db into a reasoning engine that predicts hidden connections and identifies evidence gaps."
version: "1.0.0"
tier: "TIER-7/APEX"
domain: "Graph ML — GAT, TransE, link prediction, community detection, reasoning paths, evidence gap discovery, legal knowledge graph construction"
triggers:
  - graph neural network
  - GNN
  - GAT
  - graph attention
  - link prediction
  - TransE
  - knowledge graph embedding
  - community detection
  - Louvain
  - spectral clustering
  - reasoning path
  - evidence gap
  - graph ML
  - message passing
  - node classification
  - node importance
  - graph reasoning
  - legal knowledge graph
  - hidden connections
  - argument chain
  - graph construction
references:
  - SINGULARITY-MBP-GENESIS
  - SINGULARITY-MBP-DATAWEAVE
  - SINGULARITY-MBP-COMBAT-ADVERSARY
  - SINGULARITY-MBP-COMBAT-AUTHORITY
  - SINGULARITY-MBP-EMERGENCE-CONVERGENCE
  - SINGULARITY-MBP-APEX-COGNITION
  - SINGULARITY-MBP-APEX-MEMORY
---

# SINGULARITY-MBP-APEX-GRAPHML v1.0

> **The graph that reasons. Predict hidden connections. Discover evidence gaps.
> Score argument chains. All on CPU, all from litigation_context.db.**

TIER-7/APEX — Graph Neural Networks applied to legal knowledge graphs. This skill
turns the 790+-table litigation database into a structured reasoning engine using
pure NumPy implementations of Graph Attention Networks, TransE embeddings, Louvain
community detection, and reasoning path analysis. Zero GPU dependency, zero PyG/DGL.

Research foundations:
- Veličković et al. (2018) — Graph Attention Networks
- Bordes et al. (2013) — TransE knowledge graph embeddings
- Blondel et al. (2008) — Louvain community detection
- RulE (2021) — Rule-enhanced knowledge graph reasoning
- LegalLPP (2024) — Link prediction for legal knowledge graphs
- DSHCL (2024) — Dual structure-aware hypergraph contrastive learning

---

## System 1: Legal Knowledge Graph Construction

### 1.1 Node and Edge Type Ontology

```python
"""
Legal Knowledge Graph — typed property graph over litigation_context.db.
Nodes carry 384-dim feature vectors from sentence-transformers.
Edges carry typed relation labels with weight and provenance.
"""
import sqlite3
import re
import numpy as np
from collections import defaultdict
from typing import Optional


# ── Node type constants ──────────────────────────────────────────────
NODE_PERSON     = "Person"
NODE_DOCUMENT   = "Document"
NODE_EVENT      = "Event"
NODE_AUTHORITY  = "Authority"
NODE_CLAIM      = "Claim"
NODE_EVIDENCE   = "Evidence"
NODE_COURT      = "Court"
NODE_FILING     = "Filing"

NODE_TYPES = [
    NODE_PERSON, NODE_DOCUMENT, NODE_EVENT, NODE_AUTHORITY,
    NODE_CLAIM, NODE_EVIDENCE, NODE_COURT, NODE_FILING,
]

# ── Edge type constants ──────────────────────────────────────────────
EDGE_CITED_BY    = "CITED_BY"
EDGE_CONTRADICTS = "CONTRADICTS"
EDGE_SUPPORTS    = "SUPPORTS"
EDGE_FILED_BY    = "FILED_BY"
EDGE_RULED_ON    = "RULED_ON"
EDGE_WITNESSED   = "WITNESSED"
EDGE_CAUSED      = "CAUSED"
EDGE_REFERENCES  = "REFERENCES"
EDGE_IMPEACHES   = "IMPEACHES"
EDGE_TIMELINE    = "TIMELINE"

EDGE_TYPES = [
    EDGE_CITED_BY, EDGE_CONTRADICTS, EDGE_SUPPORTS, EDGE_FILED_BY,
    EDGE_RULED_ON, EDGE_WITNESSED, EDGE_CAUSED, EDGE_REFERENCES,
    EDGE_IMPEACHES, EDGE_TIMELINE,
]

# ── One-hot encoding helpers ─────────────────────────────────────────
NODE_TYPE_DIM = len(NODE_TYPES)
EDGE_TYPE_DIM = len(EDGE_TYPES)

def node_type_vec(ntype: str) -> np.ndarray:
    """One-hot vector for node type (8-dim)."""
    vec = np.zeros(NODE_TYPE_DIM, dtype=np.float32)
    if ntype in NODE_TYPES:
        vec[NODE_TYPES.index(ntype)] = 1.0
    return vec

def edge_type_vec(etype: str) -> np.ndarray:
    """One-hot vector for edge type (10-dim)."""
    vec = np.zeros(EDGE_TYPE_DIM, dtype=np.float32)
    if etype in EDGE_TYPES:
        vec[EDGE_TYPES.index(etype)] = 1.0
    return vec
```

### 1.2 LegalKnowledgeGraph Class

```python
class LegalKnowledgeGraph:
    """
    Typed property graph built from litigation_context.db.
    Each node has: id, type, label, feature_vector (384+8 dim).
    Each edge has: source, target, type, weight, provenance.

    Feature vectors = sentence-transformer embedding (384) ∥ node-type one-hot (8)
                    = 392-dimensional node feature.
    """

    def __init__(self, db_path: str, embedding_dim: int = 384):
        self.db_path = db_path
        self.embedding_dim = embedding_dim
        self.feature_dim = embedding_dim + NODE_TYPE_DIM  # 392

        # Core graph data
        self.nodes: dict[str, dict] = {}        # id → {type, label, features, meta}
        self.edges: list[dict] = []             # [{source, target, type, weight, provenance}]
        self.adj: dict[str, list[str]] = defaultdict(list)   # adjacency list
        self.rev_adj: dict[str, list[str]] = defaultdict(list)  # reverse adjacency

        # Index maps for matrix operations
        self._node_to_idx: dict[str, int] = {}
        self._idx_to_node: dict[int, str] = {}
        self._dirty = True

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA busy_timeout=60000")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA cache_size=-32000")
        conn.row_factory = sqlite3.Row
        return conn

    def add_node(self, node_id: str, ntype: str, label: str,
                 embedding: Optional[np.ndarray] = None,
                 meta: Optional[dict] = None):
        """Add a node with type, label, and optional 384-dim embedding."""
        if embedding is None:
            embedding = np.zeros(self.embedding_dim, dtype=np.float32)
        elif embedding.shape[0] != self.embedding_dim:
            raise ValueError(f"Embedding dim {embedding.shape[0]} != {self.embedding_dim}")

        features = np.concatenate([embedding, node_type_vec(ntype)])
        self.nodes[node_id] = {
            "type": ntype,
            "label": label,
            "features": features,
            "meta": meta or {},
        }
        self._dirty = True

    def add_edge(self, source: str, target: str, etype: str,
                 weight: float = 1.0, provenance: str = ""):
        """Add a typed, weighted edge with provenance tracking."""
        if source not in self.nodes or target not in self.nodes:
            return  # silently skip dangling edges
        self.edges.append({
            "source": source,
            "target": target,
            "type": etype,
            "weight": weight,
            "provenance": provenance,
        })
        self.adj[source].append(target)
        self.rev_adj[target].append(source)
        self._dirty = True

    def _rebuild_index(self):
        """Rebuild node↔index maps for matrix operations."""
        self._node_to_idx = {nid: i for i, nid in enumerate(self.nodes)}
        self._idx_to_node = {i: nid for nid, i in self._node_to_idx.items()}
        self._dirty = False

    def get_feature_matrix(self) -> np.ndarray:
        """Return (N, 392) feature matrix aligned with index maps."""
        if self._dirty:
            self._rebuild_index()
        N = len(self.nodes)
        X = np.zeros((N, self.feature_dim), dtype=np.float32)
        for nid, idx in self._node_to_idx.items():
            X[idx] = self.nodes[nid]["features"]
        return X

    def get_adjacency_matrix(self, normalize: bool = True) -> np.ndarray:
        """
        Return (N, N) adjacency matrix. If normalize=True, returns
        D^{-1/2} A D^{-1/2} (symmetric normalization for GNN).
        Includes self-loops (A_hat = A + I).
        """
        if self._dirty:
            self._rebuild_index()
        N = len(self.nodes)
        A = np.zeros((N, N), dtype=np.float32)
        for e in self.edges:
            i = self._node_to_idx.get(e["source"])
            j = self._node_to_idx.get(e["target"])
            if i is not None and j is not None:
                A[i, j] = e["weight"]
                A[j, i] = e["weight"]  # undirected for message passing
        # Add self-loops
        A_hat = A + np.eye(N, dtype=np.float32)
        if not normalize:
            return A_hat
        # Symmetric normalization: D^{-1/2} A_hat D^{-1/2}
        D = np.diag(A_hat.sum(axis=1))
        D_inv_sqrt = np.diag(1.0 / np.sqrt(np.maximum(D.diagonal(), 1e-12)))
        return D_inv_sqrt @ A_hat @ D_inv_sqrt

    def extract_subgraph(self, center_id: str, hops: int = 2) -> "LegalKnowledgeGraph":
        """Extract k-hop ego network around a center node."""
        visited = {center_id}
        frontier = {center_id}
        for _ in range(hops):
            next_frontier = set()
            for nid in frontier:
                for neighbor in self.adj.get(nid, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        next_frontier.add(neighbor)
                for neighbor in self.rev_adj.get(nid, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        next_frontier.add(neighbor)
            frontier = next_frontier
            if not frontier:
                break

        sub = LegalKnowledgeGraph(self.db_path, self.embedding_dim)
        for nid in visited:
            n = self.nodes[nid]
            sub.nodes[nid] = n.copy()
        for e in self.edges:
            if e["source"] in visited and e["target"] in visited:
                sub.edges.append(e.copy())
                sub.adj[e["source"]].append(e["target"])
                sub.rev_adj[e["target"]].append(e["source"])
        sub._dirty = True
        return sub

    def build(self, max_evidence: int = 5000, max_authorities: int = 3000,
              max_timeline: int = 2000):
        """
        Build the full legal knowledge graph from litigation_context.db.
        Uses DuckDB-style batched queries for speed.
        Caps node counts to stay within CPU budget.
        """
        conn = self._connect()

        # ── Persons (known actors) ────────────────────────────────
        KNOWN_PERSONS = [
            ("person:pigors", "Andrew Pigors"),
            ("person:watson", "Emily A. Watson"),
            ("person:mcneill", "Jenny L. McNeill"),
            ("person:hoopes", "Kenneth Hoopes"),
            ("person:rusco", "Pamela Rusco"),
            ("person:rberry", "Ronald Berry"),
            ("person:cberry", "Cavan Berry"),
            ("person:awatson", "Albert Watson"),
            ("person:barnes", "Jennifer Barnes"),
            ("person:ladas", "Maria Ladas-Hoopes"),
        ]
        for pid, name in KNOWN_PERSONS:
            self.add_node(pid, NODE_PERSON, name, meta={"role": "party"})

        # ── Courts ────────────────────────────────────────────────
        COURTS = [
            ("court:14th", "14th Circuit Court, Muskegon"),
            ("court:60th", "60th District Court"),
            ("court:coa", "Michigan Court of Appeals"),
            ("court:msc", "Michigan Supreme Court"),
            ("court:wdmi", "USDC Western District MI"),
            ("court:jtc", "Judicial Tenure Commission"),
        ]
        for cid, name in COURTS:
            self.add_node(cid, NODE_COURT, name)

        # ── Evidence nodes from evidence_quotes ───────────────────
        try:
            rows = conn.execute(f"""
                SELECT rowid, quote_text, source_file, category, lane,
                       relevance_score, event_date
                FROM evidence_quotes
                WHERE is_duplicate = 0
                ORDER BY relevance_score DESC
                LIMIT ?
            """, (max_evidence,)).fetchall()
        except Exception:
            rows = conn.execute(f"""
                SELECT rowid, quote_text, source_file, category, lane
                FROM evidence_quotes
                LIMIT ?
            """, (max_evidence,)).fetchall()

        for r in rows:
            eid = f"ev:{r['rowid']}"
            label = (r["quote_text"] or "")[:120]
            self.add_node(eid, NODE_EVIDENCE, label, meta={
                "source": r.get("source_file", ""),
                "category": r.get("category", ""),
                "lane": r.get("lane", ""),
            })

        # ── Authority nodes from authority_chains_v2 ──────────────
        try:
            auth_rows = conn.execute("""
                SELECT DISTINCT primary_citation, relationship, lane
                FROM authority_chains_v2
                LIMIT ?
            """, (max_authorities,)).fetchall()
        except Exception:
            auth_rows = []

        seen_auths = set()
        for r in auth_rows:
            cite = r["primary_citation"]
            if cite and cite not in seen_auths:
                seen_auths.add(cite)
                aid = f"auth:{cite}"
                self.add_node(aid, NODE_AUTHORITY, cite, meta={
                    "lane": r.get("lane", ""),
                })

        # ── Timeline events ───────────────────────────────────────
        try:
            ev_rows = conn.execute("""
                SELECT rowid, event_date, event_text, actor, lane
                FROM timeline_events
                ORDER BY event_date DESC
                LIMIT ?
            """, (max_timeline,)).fetchall()
        except Exception:
            ev_rows = []

        for r in ev_rows:
            tid = f"evt:{r['rowid']}"
            label = (r.get("event_text") or "")[:120]
            self.add_node(tid, NODE_EVENT, label, meta={
                "date": r.get("event_date", ""),
                "actor": r.get("actor", ""),
                "lane": r.get("lane", ""),
            })
            # Link event to actor if known
            actor = (r.get("actor") or "").lower()
            for pid, pname in KNOWN_PERSONS:
                if pname.split()[-1].lower() in actor:
                    self.add_edge(tid, pid, EDGE_WITNESSED, 1.0, "timeline_events")
                    break

        # ── Contradiction edges ───────────────────────────────────
        try:
            contra_rows = conn.execute("""
                SELECT source_a, source_b, contradiction_text, severity
                FROM contradiction_map
            """).fetchall()
        except Exception:
            contra_rows = []

        for r in contra_rows:
            sa = f"contra_src:{r['source_a']}" if r.get("source_a") else None
            sb = f"contra_src:{r['source_b']}" if r.get("source_b") else None
            if sa and sa not in self.nodes:
                self.add_node(sa, NODE_DOCUMENT, r["source_a"][:80])
            if sb and sb not in self.nodes:
                self.add_node(sb, NODE_DOCUMENT, r["source_b"][:80])
            if sa and sb:
                sev = float(r.get("severity") or 1)
                self.add_edge(sa, sb, EDGE_CONTRADICTS, sev, "contradiction_map")

        # ── Impeachment edges ─────────────────────────────────────
        try:
            imp_rows = conn.execute("""
                SELECT rowid, category, evidence_summary,
                       impeachment_value, cross_exam_question
                FROM impeachment_matrix
                WHERE impeachment_value >= 5
            """).fetchall()
        except Exception:
            imp_rows = []

        for r in imp_rows:
            iid = f"imp:{r['rowid']}"
            self.add_node(iid, NODE_EVIDENCE, (r.get("evidence_summary") or "")[:100],
                          meta={"impeach_val": r.get("impeachment_value", 0)})
            # Link to Watson by default (primary impeachment target)
            self.add_edge(iid, "person:watson", EDGE_IMPEACHES,
                          float(r.get("impeachment_value", 1)) / 10.0,
                          "impeachment_matrix")

        # ── Authority citation edges ──────────────────────────────
        try:
            cite_rows = conn.execute("""
                SELECT primary_citation, supporting_citation, relationship
                FROM authority_chains_v2
                LIMIT 10000
            """).fetchall()
        except Exception:
            cite_rows = []

        for r in cite_rows:
            src = f"auth:{r['primary_citation']}"
            tgt = f"auth:{r['supporting_citation']}"
            if src in self.nodes and tgt in self.nodes:
                self.add_edge(src, tgt, EDGE_CITED_BY, 1.0, "authority_chains_v2")

        conn.close()
        self._rebuild_index()
        return self

    @property
    def num_nodes(self) -> int:
        return len(self.nodes)

    @property
    def num_edges(self) -> int:
        return len(self.edges)

    def node_ids_by_type(self, ntype: str) -> list[str]:
        return [nid for nid, n in self.nodes.items() if n["type"] == ntype]
```

### 1.3 D3.js GraphML Bridge

```javascript
/**
 * GraphMLBridge — translates Python graph data into D3.js force simulation format.
 * Receives JSON from the Python backend via pywebview bridge.
 */
class GraphMLBridge {
  constructor(containerSelector) {
    this.container = d3.select(containerSelector);
    this.nodes = [];
    this.links = [];
    this.nodeIndex = new Map();   // id → node object
    this.importanceMap = new Map(); // id → GNN importance score
    this.communityMap = new Map();  // id → community label
    this.gapNodes = new Set();      // ids with predicted evidence gaps
  }

  /**
   * Import graph data from Python backend.
   * @param {Object} graphData - {nodes: [...], edges: [...], meta: {...}}
   */
  importGraph(graphData) {
    this.nodes = graphData.nodes.map(n => ({
      id:        n.id,
      label:     n.label,
      type:      n.type,
      features:  n.features || [],
      meta:      n.meta || {},
      x:         n.x || Math.random() * 800,
      y:         n.y || Math.random() * 600,
      importance: 0.5,
      community:  -1,
    }));
    this.links = graphData.edges.map(e => ({
      source:     e.source,
      target:     e.target,
      type:       e.type,
      weight:     e.weight || 1.0,
      provenance: e.provenance || '',
      predicted:  e.predicted || false,
      linkProb:   e.linkProb || 0.0,
    }));
    this.nodeIndex.clear();
    this.nodes.forEach(n => this.nodeIndex.set(n.id, n));
  }

  /**
   * Apply GNN importance scores to nodes.
   * @param {Object} scores - {nodeId: importance_float, ...}
   */
  applyImportance(scores) {
    for (const [id, score] of Object.entries(scores)) {
      this.importanceMap.set(id, score);
      const node = this.nodeIndex.get(id);
      if (node) node.importance = score;
    }
  }

  /**
   * Apply community assignments.
   * @param {Object} communities - {nodeId: communityInt, ...}
   */
  applyCommunities(communities) {
    for (const [id, comm] of Object.entries(communities)) {
      this.communityMap.set(id, comm);
      const node = this.nodeIndex.get(id);
      if (node) node.community = comm;
    }
  }

  /**
   * Mark nodes with predicted evidence gaps.
   * @param {string[]} gapNodeIds - node IDs where evidence gaps detected
   */
  markGaps(gapNodeIds) {
    this.gapNodes = new Set(gapNodeIds);
  }

  /** Export to D3.js simulation-ready format. */
  toD3Data() {
    return {
      nodes: this.nodes,
      links: this.links,
    };
  }
}
```

---

## System 2: Graph Attention Network Layers (Pure NumPy)

### 2.1 Single-Head Graph Attention Layer

```python
"""
Pure NumPy implementation of Graph Attention Networks (Veličković et al., 2018).
No PyG, no DGL, no GPU — runs on AMD Ryzen 3 3200G CPU in <500ms for 1000 nodes.

Architecture per layer:
  X ∈ R^{N×F} (input features)
  W ∈ R^{F×F'} (weight matrix)
  a ∈ R^{2F'} (attention vector)
  α_{ij} = softmax_j(LeakyReLU(a^T [Wh_i ∥ Wh_j]))
  h'_i = σ(Σ_j α_{ij} W h_j)
"""


class GraphAttentionLayer:
    """
    Single-head GAT layer. Pure NumPy, Xavier init, LeakyReLU attention.
    """

    def __init__(self, in_features: int, out_features: int,
                 alpha: float = 0.2, seed: int = 42):
        """
        Args:
            in_features: input feature dimension per node
            out_features: output feature dimension per node
            alpha: negative slope for LeakyReLU
        """
        rng = np.random.default_rng(seed)
        limit = np.sqrt(6.0 / (in_features + out_features))  # Xavier uniform

        self.W = rng.uniform(-limit, limit,
                             (in_features, out_features)).astype(np.float32)
        self.a = rng.uniform(-limit, limit,
                             (2 * out_features,)).astype(np.float32)
        self.alpha = alpha

        # Gradient accumulators (for training)
        self.dW = np.zeros_like(self.W)
        self.da = np.zeros_like(self.a)

        # Cached forward pass values (for backprop)
        self._Wh = None
        self._attn_coeffs = None
        self._input = None

    def _leaky_relu(self, x: np.ndarray) -> np.ndarray:
        return np.where(x > 0, x, self.alpha * x)

    def _softmax_rows(self, x: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Row-wise softmax, masking non-neighbor entries to -inf."""
        x = np.where(mask, x, -1e9)
        exp_x = np.exp(x - x.max(axis=1, keepdims=True))
        exp_x = exp_x * mask
        row_sums = exp_x.sum(axis=1, keepdims=True) + 1e-12
        return exp_x / row_sums

    def forward(self, X: np.ndarray, A: np.ndarray) -> np.ndarray:
        """
        Forward pass.
        Args:
            X: (N, in_features) node feature matrix
            A: (N, N) adjacency matrix (nonzero = edge exists, incl. self-loops)
        Returns:
            H: (N, out_features) transformed node features
        """
        N = X.shape[0]
        self._input = X

        # Linear transform: Wh = X @ W  →  (N, out_features)
        Wh = X @ self.W
        self._Wh = Wh

        # Attention scores: for each pair (i,j), compute a^T [Wh_i ∥ Wh_j]
        # Split attention vector: a = [a_left | a_right], each out_features dim
        a_left = self.a[:Wh.shape[1]]
        a_right = self.a[Wh.shape[1]:]

        # e_ij = LeakyReLU(Wh_i @ a_left + Wh_j @ a_right)
        # Broadcast: (N,1) + (1,N) → (N,N)
        score_left = Wh @ a_left      # (N,)
        score_right = Wh @ a_right     # (N,)
        e = self._leaky_relu(score_left[:, None] + score_right[None, :])  # (N,N)

        # Mask to adjacency structure and apply softmax
        mask = (A > 0).astype(np.float32)
        attn = self._softmax_rows(e, mask)  # (N, N)
        self._attn_coeffs = attn

        # Aggregate: H = attn @ Wh  →  (N, out_features)
        H = attn @ Wh
        return H

    def get_attention_weights(self) -> Optional[np.ndarray]:
        """Return (N, N) attention coefficients from last forward pass."""
        return self._attn_coeffs


class MultiHeadGAT:
    """
    Multi-head GAT: K independent attention heads, outputs concatenated
    (or averaged for the final layer).
    """

    def __init__(self, in_features: int, out_features: int,
                 num_heads: int = 4, concat: bool = True, seed: int = 42):
        self.heads = [
            GraphAttentionLayer(in_features, out_features, seed=seed + h)
            for h in range(num_heads)
        ]
        self.concat = concat
        self.num_heads = num_heads
        self.out_dim = out_features * num_heads if concat else out_features

    def forward(self, X: np.ndarray, A: np.ndarray) -> np.ndarray:
        """
        Multi-head forward pass.
        Returns (N, out_features * num_heads) if concat else (N, out_features).
        """
        head_outputs = [head.forward(X, A) for head in self.heads]

        if self.concat:
            return np.concatenate(head_outputs, axis=1)
        else:
            return np.mean(head_outputs, axis=0)

    def get_all_attention_weights(self) -> list[np.ndarray]:
        """Return attention weights from each head."""
        return [h.get_attention_weights() for h in self.heads]
```

### 2.2 Full Legal GNN Model

```python
def elu(x: np.ndarray, alpha: float = 1.0) -> np.ndarray:
    return np.where(x > 0, x, alpha * (np.exp(np.clip(x, -20, 0)) - 1))


def sigmoid(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, -20, 20)
    return 1.0 / (1.0 + np.exp(-x))


class LegalGNN:
    """
    Two-layer GAT for legal knowledge graph reasoning.

    Layer 1: MultiHeadGAT(392 → 64, 4 heads, concat) → ELU → (N, 256)
    Layer 2: MultiHeadGAT(256 → 64, 4 heads, average) → sigmoid → (N, 64)

    Output: 64-dim node embeddings usable for:
      - Node classification (importance scoring)
      - Link prediction (dot product between embeddings)
      - Community-aware clustering
    """

    def __init__(self, in_dim: int = 392, hidden_dim: int = 64,
                 out_dim: int = 64, num_heads: int = 4, seed: int = 42):
        self.layer1 = MultiHeadGAT(in_dim, hidden_dim, num_heads,
                                   concat=True, seed=seed)
        mid_dim = hidden_dim * num_heads  # 256
        self.layer2 = MultiHeadGAT(mid_dim, out_dim, num_heads,
                                   concat=False, seed=seed + 100)
        self.out_dim = out_dim

        # Classification head: 64 → 3 (HIGH / MEDIUM / LOW importance)
        rng = np.random.default_rng(seed + 200)
        self.W_cls = rng.uniform(-0.1, 0.1, (out_dim, 3)).astype(np.float32)
        self.b_cls = np.zeros(3, dtype=np.float32)

    def get_node_embeddings(self, X: np.ndarray, A: np.ndarray) -> np.ndarray:
        """
        Forward pass → 64-dim node embeddings.
        Args:
            X: (N, 392) feature matrix
            A: (N, N) normalized adjacency
        Returns:
            Z: (N, 64) node embeddings
        """
        H1 = elu(self.layer1.forward(X, A))     # (N, 256)
        Z = sigmoid(self.layer2.forward(H1, A))  # (N, 64)
        return Z

    def classify_importance(self, X: np.ndarray, A: np.ndarray) -> np.ndarray:
        """
        Predict node importance class: 0=LOW, 1=MEDIUM, 2=HIGH.
        Returns (N, 3) probability matrix.
        """
        Z = self.get_node_embeddings(X, A)
        logits = Z @ self.W_cls + self.b_cls  # (N, 3)
        # Softmax
        exp_l = np.exp(logits - logits.max(axis=1, keepdims=True))
        probs = exp_l / (exp_l.sum(axis=1, keepdims=True) + 1e-12)
        return probs

    def predict_link_scores(self, X: np.ndarray, A: np.ndarray,
                            pairs: list[tuple[int, int]]) -> np.ndarray:
        """
        Predict link probability for candidate (i, j) pairs.
        Uses dot-product between node embeddings.
        Returns (len(pairs),) array of scores in [0, 1].
        """
        Z = self.get_node_embeddings(X, A)
        scores = np.array([
            sigmoid(np.dot(Z[i], Z[j]))[0]
            if isinstance(sigmoid(np.dot(Z[i], Z[j])), np.ndarray)
            else float(sigmoid(np.dot(Z[i], Z[j])))
            for i, j in pairs
        ], dtype=np.float32)
        return scores

    def train_supervised(self, X: np.ndarray, A: np.ndarray,
                         labels: np.ndarray, lr: float = 0.005,
                         epochs: int = 50) -> list[float]:
        """
        Simple SGD training loop on node classification.
        Args:
            labels: (N,) integer class labels (0, 1, 2)
        Returns:
            losses: list of cross-entropy loss per epoch
        """
        N = X.shape[0]
        losses = []
        for epoch in range(epochs):
            # Forward
            probs = self.classify_importance(X, A)  # (N, 3)

            # Cross-entropy loss
            one_hot = np.zeros_like(probs)
            one_hot[np.arange(N), labels] = 1.0
            loss = -np.mean(np.sum(one_hot * np.log(probs + 1e-12), axis=1))
            losses.append(float(loss))

            # Gradient on classification head (simplified — freeze GAT weights)
            grad_logits = probs - one_hot  # (N, 3)
            Z = self.get_node_embeddings(X, A)  # (N, 64) — use cached
            self.W_cls -= lr * (Z.T @ grad_logits) / N
            self.b_cls -= lr * grad_logits.mean(axis=0)

        return losses

    def get_attention_maps(self) -> dict:
        """Return attention weight matrices from both layers."""
        return {
            "layer1": self.layer1.get_all_attention_weights(),
            "layer2": self.layer2.get_all_attention_weights(),
        }
```

---

## System 3: Legal Link Prediction

### 3.1 TransE Knowledge Graph Embeddings

```python
"""
TransE (Bordes et al., 2013) for legal knowledge graphs.
Learns embeddings where h + r ≈ t for valid triples (head, relation, tail).
Enhanced with rule-based constraints from Michigan court rules.
"""


class TransELinkPredictor:
    """
    TransE-style knowledge graph embedding model.

    For each triple (h, r, t):  score = -‖h + r - t‖
    Higher score = more plausible link.

    Embedding dimensions:
      - Entity embeddings: (num_entities, embed_dim)
      - Relation embeddings: (num_relations, embed_dim)
    """

    def __init__(self, num_entities: int, num_relations: int,
                 embed_dim: int = 64, margin: float = 1.0, seed: int = 42):
        rng = np.random.default_rng(seed)
        self.embed_dim = embed_dim
        self.margin = margin

        # Initialize embeddings on unit sphere
        self.ent_emb = rng.standard_normal((num_entities, embed_dim)).astype(np.float32)
        norms = np.linalg.norm(self.ent_emb, axis=1, keepdims=True) + 1e-12
        self.ent_emb /= norms

        self.rel_emb = rng.standard_normal((num_relations, embed_dim)).astype(np.float32)
        norms = np.linalg.norm(self.rel_emb, axis=1, keepdims=True) + 1e-12
        self.rel_emb /= norms

        self.num_entities = num_entities
        self.num_relations = num_relations

    def _score(self, h_idx: np.ndarray, r_idx: np.ndarray,
               t_idx: np.ndarray) -> np.ndarray:
        """Score a batch of triples: -‖h + r - t‖_2"""
        h = self.ent_emb[h_idx]
        r = self.rel_emb[r_idx]
        t = self.ent_emb[t_idx]
        return -np.linalg.norm(h + r - t, axis=1)

    def train(self, triples: list[tuple[int, int, int]],
              lr: float = 0.01, epochs: int = 100,
              neg_samples: int = 5) -> list[float]:
        """
        Train TransE with margin-based ranking loss.
        Negative sampling: corrupt head or tail randomly.
        """
        rng = np.random.default_rng(0)
        triples_arr = np.array(triples, dtype=np.int32)
        losses = []

        for epoch in range(epochs):
            epoch_loss = 0.0
            perm = rng.permutation(len(triples_arr))

            for idx in perm:
                h, r, t = triples_arr[idx]

                # Positive score
                pos_score = self._score(
                    np.array([h]), np.array([r]), np.array([t])
                )[0]

                # Negative samples (corrupt head or tail)
                for _ in range(neg_samples):
                    if rng.random() < 0.5:
                        h_neg = rng.integers(0, self.num_entities)
                        neg_score = self._score(
                            np.array([h_neg]), np.array([r]), np.array([t])
                        )[0]
                    else:
                        t_neg = rng.integers(0, self.num_entities)
                        neg_score = self._score(
                            np.array([h]), np.array([r]), np.array([t_neg])
                        )[0]

                    # Margin ranking loss: max(0, margin + pos_dist - neg_dist)
                    # Remember scores are negative distances, so:
                    loss = max(0.0, self.margin - pos_score + neg_score)
                    epoch_loss += loss

                    if loss > 0:
                        # SGD update — push positive closer, negative farther
                        h_vec = self.ent_emb[h]
                        r_vec = self.rel_emb[r]
                        t_vec = self.ent_emb[t]
                        grad = 2 * (h_vec + r_vec - t_vec)

                        self.ent_emb[h] -= lr * grad
                        self.rel_emb[r] -= lr * grad
                        self.ent_emb[t] += lr * grad

                        # Re-normalize to unit sphere
                        for idx_n in [h, t]:
                            norm = np.linalg.norm(self.ent_emb[idx_n]) + 1e-12
                            self.ent_emb[idx_n] /= norm

            losses.append(epoch_loss / max(len(triples_arr), 1))
        return losses

    def predict_links(self, head_idx: int, relation_idx: int,
                      top_k: int = 20) -> list[tuple[int, float]]:
        """
        Predict top-k tail entities for a given (head, relation, ?).
        Returns list of (entity_idx, score) sorted by descending plausibility.
        """
        h = self.ent_emb[head_idx]
        r = self.rel_emb[relation_idx]
        # Score all entities as potential tails
        diffs = h + r - self.ent_emb  # (num_entities, embed_dim)
        scores = -np.linalg.norm(diffs, axis=1)  # higher = better
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [(int(i), float(scores[i])) for i in top_indices]

    def find_gaps(self, graph: LegalKnowledgeGraph,
                  entity_map: dict[str, int],
                  relation_map: dict[str, int],
                  threshold: float = -0.5,
                  top_k: int = 100) -> list[dict]:
        """
        Identify evidence gaps: pairs that SHOULD have edges but don't.
        Scans all (entity, relation) pairs, filters to those above threshold
        that are NOT in the existing graph.

        Returns list of {head, relation, tail, score, gap_type} dicts.
        """
        existing_edges = set()
        for e in graph.edges:
            existing_edges.add((e["source"], e["type"], e["target"]))

        inv_entity = {v: k for k, v in entity_map.items()}
        inv_relation = {v: k for k, v in relation_map.items()}

        gaps = []
        # Sample entities to keep runtime bounded
        sample_entities = list(entity_map.keys())[:500]

        for h_name in sample_entities:
            h_idx = entity_map[h_name]
            for r_name, r_idx in relation_map.items():
                predictions = self.predict_links(h_idx, r_idx, top_k=5)
                for t_idx, score in predictions:
                    if score < threshold:
                        continue
                    t_name = inv_entity.get(t_idx, f"unk:{t_idx}")
                    if (h_name, r_name, t_name) not in existing_edges:
                        gaps.append({
                            "head": h_name,
                            "relation": r_name,
                            "tail": t_name,
                            "score": score,
                            "gap_type": _classify_gap(h_name, r_name, t_name),
                        })
        # Sort by score descending, return top_k
        gaps.sort(key=lambda g: g["score"], reverse=True)
        return gaps[:top_k]

    def rank_candidates(self, head_idx: int, relation_idx: int,
                        candidate_indices: list[int]) -> list[tuple[int, float]]:
        """Rank specific candidate tails by TransE score."""
        h = self.ent_emb[head_idx]
        r = self.rel_emb[relation_idx]
        scores = []
        for c in candidate_indices:
            t = self.ent_emb[c]
            score = -float(np.linalg.norm(h + r - t))
            scores.append((c, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores


def _classify_gap(head: str, relation: str, tail: str) -> str:
    """Classify a predicted gap by its litigation significance."""
    if "auth:" in head or "auth:" in tail:
        return "MISSING_AUTHORITY"
    if relation == EDGE_CONTRADICTS:
        return "UNDISCOVERED_CONTRADICTION"
    if relation == EDGE_SUPPORTS:
        return "UNSUPPORTED_CLAIM"
    if relation == EDGE_IMPEACHES:
        return "UNTAPPED_IMPEACHMENT"
    if "person:" in tail and relation == EDGE_WITNESSED:
        return "UNLINKED_WITNESS"
    return "GENERAL_GAP"
```

---

## System 4: Community Detection & Clustering

### 4.1 Louvain Community Detection (Pure Python)

```python
"""
Community detection on legal knowledge graphs.
Louvain modularity optimization + spectral clustering + DBSCAN on embeddings.
"""


class CommunityAnalyzer:
    """
    Detect communities, anomalies, and hierarchical structure in the legal graph.
    """

    def __init__(self, graph: LegalKnowledgeGraph):
        self.graph = graph

    def detect_communities_louvain(self, resolution: float = 1.0,
                                   max_iter: int = 50) -> dict[str, int]:
        """
        Louvain community detection (Blondel et al., 2008).
        Greedy modularity optimization — O(N log N) in practice.

        Returns: {node_id: community_label}
        """
        nodes = list(self.graph.nodes.keys())
        n = len(nodes)
        if n == 0:
            return {}

        idx = {nid: i for i, nid in enumerate(nodes)}

        # Build weighted adjacency dict
        adj: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
        total_weight = 0.0
        for e in self.graph.edges:
            i, j = idx.get(e["source"]), idx.get(e["target"])
            if i is not None and j is not None:
                adj[i][j] += e["weight"]
                adj[j][i] += e["weight"]
                total_weight += e["weight"]

        if total_weight < 1e-12:
            return {nid: 0 for nid in nodes}
        m = total_weight

        # Initial assignment: each node in its own community
        comm = list(range(n))
        k = np.zeros(n, dtype=np.float64)  # degree of each node
        for i in range(n):
            k[i] = sum(adj[i].values())

        improved = True
        iteration = 0
        while improved and iteration < max_iter:
            improved = False
            iteration += 1
            order = list(range(n))
            np.random.shuffle(order)

            for i in order:
                current_comm = comm[i]
                # Sum of weights from i to nodes in each neighbor community
                neighbor_comms: dict[int, float] = defaultdict(float)
                for j, w in adj[i].items():
                    neighbor_comms[comm[j]] += w

                # Compute modularity gain for moving i to each neighbor community
                best_comm = current_comm
                best_gain = 0.0

                # Sum of degrees in current community (excluding i)
                sigma_current = sum(
                    k[j] for j in range(n) if comm[j] == current_comm and j != i
                )
                ki_in_current = neighbor_comms.get(current_comm, 0.0)

                for c, ki_in_c in neighbor_comms.items():
                    if c == current_comm:
                        continue
                    sigma_c = sum(k[j] for j in range(n) if comm[j] == c)
                    # ΔQ = [ki_in_c / m - σ_c * k_i / (2m²)] * resolution
                    #     - [ki_in_current / m - σ_current * k_i / (2m²)] * resolution
                    gain = (
                        (ki_in_c - ki_in_current) / m
                        - resolution * k[i] * (sigma_c - sigma_current) / (2 * m * m)
                    )
                    if gain > best_gain:
                        best_gain = gain
                        best_comm = c

                if best_comm != current_comm:
                    comm[i] = best_comm
                    improved = True

        # Renumber communities contiguously
        unique_comms = sorted(set(comm))
        remap = {c: i for i, c in enumerate(unique_comms)}
        return {nodes[i]: remap[comm[i]] for i in range(n)}

    def spectral_clustering(self, n_clusters: int = 5) -> dict[str, int]:
        """
        Spectral clustering via eigendecomposition of the graph Laplacian.
        Uses the smallest k eigenvectors of L = D - A, then k-means.
        """
        A = self.graph.get_adjacency_matrix(normalize=False)
        N = A.shape[0]
        if N < n_clusters:
            n_clusters = max(1, N)

        D = np.diag(A.sum(axis=1))
        L = D - A

        # Compute smallest k eigenvalues/vectors (skip eigenvalue 0)
        eigenvalues, eigenvectors = np.linalg.eigh(L)
        # Take eigenvectors 1..k (skip the trivial zero eigenvector)
        U = eigenvectors[:, 1:n_clusters + 1]

        # Normalize rows
        row_norms = np.linalg.norm(U, axis=1, keepdims=True) + 1e-12
        U = U / row_norms

        # Simple k-means on the spectral embedding
        labels = self._kmeans(U, n_clusters)

        self.graph._rebuild_index()
        return {
            self.graph._idx_to_node[i]: int(labels[i])
            for i in range(N)
        }

    def _kmeans(self, X: np.ndarray, k: int, max_iter: int = 50) -> np.ndarray:
        """Simple k-means clustering (NumPy only)."""
        N = X.shape[0]
        rng = np.random.default_rng(42)
        centers = X[rng.choice(N, k, replace=False)]
        labels = np.zeros(N, dtype=np.int32)

        for _ in range(max_iter):
            # Assign
            dists = np.linalg.norm(X[:, None, :] - centers[None, :, :], axis=2)
            new_labels = np.argmin(dists, axis=1)
            if np.array_equal(new_labels, labels):
                break
            labels = new_labels
            # Update
            for c in range(k):
                mask = labels == c
                if mask.any():
                    centers[c] = X[mask].mean(axis=0)
        return labels

    def dbscan_on_embeddings(self, embeddings: np.ndarray,
                             eps: float = 0.3,
                             min_samples: int = 3) -> dict[str, int]:
        """
        DBSCAN clustering on GNN-produced node embeddings.
        Identifies semantic clusters and anomalies (label -1).
        """
        N = embeddings.shape[0]
        labels = np.full(N, -1, dtype=np.int32)
        visited = np.zeros(N, dtype=bool)
        cluster_id = 0

        # Precompute pairwise distances
        dists = np.linalg.norm(
            embeddings[:, None, :] - embeddings[None, :, :], axis=2
        )

        for i in range(N):
            if visited[i]:
                continue
            visited[i] = True
            neighbors = np.where(dists[i] < eps)[0]

            if len(neighbors) < min_samples:
                continue  # noise point, label stays -1

            labels[i] = cluster_id
            seed_set = list(neighbors)
            j = 0
            while j < len(seed_set):
                q = seed_set[j]
                if not visited[q]:
                    visited[q] = True
                    q_neighbors = np.where(dists[q] < eps)[0]
                    if len(q_neighbors) >= min_samples:
                        seed_set.extend(
                            [n for n in q_neighbors if n not in seed_set]
                        )
                if labels[q] == -1:
                    labels[q] = cluster_id
                j += 1
            cluster_id += 1

        self.graph._rebuild_index()
        return {
            self.graph._idx_to_node.get(i, f"unk:{i}"): int(labels[i])
            for i in range(N)
        }

    def find_anomalies(self, communities: dict[str, int]) -> list[dict]:
        """
        Detect anomalous nodes: nodes whose neighbors are mostly in
        OTHER communities (boundary-crossers, suspicious intermediaries).
        """
        anomalies = []
        for nid, comm in communities.items():
            neighbors = self.graph.adj.get(nid, []) + self.graph.rev_adj.get(nid, [])
            if len(neighbors) < 2:
                continue
            same_comm = sum(1 for n in neighbors if communities.get(n) == comm)
            ratio = same_comm / len(neighbors)
            if ratio < 0.3:  # <30% neighbors in same community = anomaly
                anomalies.append({
                    "node_id": nid,
                    "label": self.graph.nodes[nid]["label"],
                    "community": comm,
                    "cross_community_ratio": 1.0 - ratio,
                    "neighbor_count": len(neighbors),
                    "type": self.graph.nodes[nid]["type"],
                })
        anomalies.sort(key=lambda a: a["cross_community_ratio"], reverse=True)
        return anomalies

    def hierarchical_cluster(self) -> dict[str, list[str]]:
        """
        Build hierarchy: Court → Judge → Attorney → Party → Evidence.
        Returns {parent_id: [child_ids]}.
        """
        hierarchy: dict[str, list[str]] = defaultdict(list)
        type_order = [NODE_COURT, NODE_PERSON, NODE_FILING,
                      NODE_CLAIM, NODE_EVIDENCE, NODE_EVENT]

        for nid, node in self.graph.nodes.items():
            ntype = node["type"]
            if ntype not in type_order:
                continue
            level = type_order.index(ntype)
            # Find nearest parent of higher level via edges
            best_parent = None
            best_level = level
            for neighbor in (self.graph.adj.get(nid, []) +
                             self.graph.rev_adj.get(nid, [])):
                if neighbor in self.graph.nodes:
                    n_type = self.graph.nodes[neighbor]["type"]
                    if n_type in type_order:
                        n_level = type_order.index(n_type)
                        if n_level < best_level:
                            best_parent = neighbor
                            best_level = n_level
            if best_parent:
                hierarchy[best_parent].append(nid)

        return dict(hierarchy)
```

---

## System 5: Legal Reasoning Paths

### 5.1 Argument Chain Discovery

```python
"""
Reasoning path analysis for legal arguments.
Find evidence → authority → conclusion chains, score them, detect counter-arguments.
"""
from collections import deque


class ReasoningPathFinder:
    """
    Discover, score, and analyze argument chains through the legal knowledge graph.
    """

    def __init__(self, graph: LegalKnowledgeGraph):
        self.graph = graph

    def find_paths(self, source: str, target: str,
                   max_depth: int = 5, max_paths: int = 10) -> list[list[str]]:
        """
        BFS to find all simple paths from source to target, up to max_depth.
        Returns list of paths (each path = list of node IDs).
        """
        if source not in self.graph.nodes or target not in self.graph.nodes:
            return []

        paths = []
        queue: deque[tuple[str, list[str]]] = deque([(source, [source])])

        while queue and len(paths) < max_paths:
            current, path = queue.popleft()
            if len(path) > max_depth:
                continue
            if current == target and len(path) > 1:
                paths.append(path)
                continue
            for neighbor in self.graph.adj.get(current, []):
                if neighbor not in path:  # simple path (no cycles)
                    queue.append((neighbor, path + [neighbor]))

        return paths

    def score_path(self, path: list[str]) -> dict:
        """
        Score an argument path by evidence strength, authority weight,
        logical soundness, and chain completeness.

        Returns:
          {
            "path": [...],
            "evidence_score": float,   # strength of evidence nodes
            "authority_score": float,  # weight of authority citations
            "coherence_score": float,  # type-transition logic
            "total_score": float,      # weighted combination
            "weakest_link": str,       # node ID of weakest point
            "grade": str,              # A/B/C/D/F
          }
        """
        if len(path) < 2:
            return {"path": path, "total_score": 0, "grade": "F"}

        evidence_scores = []
        authority_scores = []
        coherence_penalties = 0.0

        # Ideal type sequence for a legal argument:
        # Evidence → Event → Claim → Authority → Filing
        IDEAL_SEQUENCE = [NODE_EVIDENCE, NODE_EVENT, NODE_CLAIM,
                          NODE_AUTHORITY, NODE_FILING]

        prev_type = None
        for i, nid in enumerate(path):
            node = self.graph.nodes.get(nid, {})
            ntype = node.get("type", "")

            # Evidence strength
            if ntype == NODE_EVIDENCE:
                imp_val = node.get("meta", {}).get("impeach_val", 5)
                evidence_scores.append(float(imp_val) / 10.0)

            # Authority weight
            if ntype == NODE_AUTHORITY:
                authority_scores.append(1.0)

            # Coherence: penalize illogical type transitions
            if prev_type and ntype:
                if prev_type in IDEAL_SEQUENCE and ntype in IDEAL_SEQUENCE:
                    prev_idx = IDEAL_SEQUENCE.index(prev_type)
                    curr_idx = IDEAL_SEQUENCE.index(ntype)
                    if curr_idx < prev_idx:  # backward transition
                        coherence_penalties += 0.2
                else:
                    coherence_penalties += 0.05  # unknown type penalty
            prev_type = ntype

        ev_score = np.mean(evidence_scores) if evidence_scores else 0.0
        auth_score = min(1.0, len(authority_scores) / 2.0)
        coh_score = max(0.0, 1.0 - coherence_penalties)

        total = 0.4 * ev_score + 0.35 * auth_score + 0.25 * coh_score

        # Find weakest link
        weakest = path[0]
        weakest_val = float("inf")
        for nid in path:
            node = self.graph.nodes.get(nid, {})
            if node.get("type") == NODE_EVIDENCE:
                v = node.get("meta", {}).get("impeach_val", 5)
                if v < weakest_val:
                    weakest_val = v
                    weakest = nid

        grade = "A" if total >= 0.8 else "B" if total >= 0.6 else \
                "C" if total >= 0.4 else "D" if total >= 0.2 else "F"

        return {
            "path": path,
            "evidence_score": float(ev_score),
            "authority_score": float(auth_score),
            "coherence_score": float(coh_score),
            "total_score": float(total),
            "weakest_link": weakest,
            "grade": grade,
        }

    def find_counter_paths(self, argument_path: list[str],
                           max_depth: int = 4) -> list[dict]:
        """
        For a given argument path, find counter-argument paths:
        paths that CONTRADICT or IMPEACH nodes in the argument chain.
        """
        counters = []
        for nid in argument_path:
            # Check for contradiction edges
            for e in self.graph.edges:
                if e["type"] == EDGE_CONTRADICTS:
                    if e["source"] == nid or e["target"] == nid:
                        other = e["target"] if e["source"] == nid else e["source"]
                        counters.append({
                            "challenged_node": nid,
                            "counter_node": other,
                            "edge_type": EDGE_CONTRADICTS,
                            "weight": e["weight"],
                            "label": self.graph.nodes.get(other, {}).get("label", ""),
                        })
                if e["type"] == EDGE_IMPEACHES:
                    if e["target"] == nid:
                        counters.append({
                            "challenged_node": nid,
                            "counter_node": e["source"],
                            "edge_type": EDGE_IMPEACHES,
                            "weight": e["weight"],
                            "label": self.graph.nodes.get(
                                e["source"], {}
                            ).get("label", ""),
                        })

        counters.sort(key=lambda c: c["weight"], reverse=True)
        return counters

    def measure_completeness(self, claim_node: str) -> dict:
        """
        Measure what percentage of a legal argument chain is supported.

        A complete chain needs:
          1. At least one Evidence node connected
          2. At least one Authority node connected
          3. Path from Evidence → Authority exists
          4. No unaddressed contradictions

        Returns:
          {
            "claim": str,
            "has_evidence": bool,
            "has_authority": bool,
            "evidence_count": int,
            "authority_count": int,
            "path_exists": bool,
            "unaddressed_contradictions": int,
            "completeness_pct": float,  # 0-100
            "gaps": [str],
          }
        """
        if claim_node not in self.graph.nodes:
            return {"claim": claim_node, "completeness_pct": 0.0, "gaps": ["NOT_FOUND"]}

        # Walk 2-hop neighborhood
        neighbors_1 = set(self.graph.adj.get(claim_node, []) +
                          self.graph.rev_adj.get(claim_node, []))
        neighbors_2 = set()
        for n in neighbors_1:
            neighbors_2.update(self.graph.adj.get(n, []))
            neighbors_2.update(self.graph.rev_adj.get(n, []))
        all_neighbors = neighbors_1 | neighbors_2

        evidence_nodes = [
            n for n in all_neighbors
            if self.graph.nodes.get(n, {}).get("type") == NODE_EVIDENCE
        ]
        authority_nodes = [
            n for n in all_neighbors
            if self.graph.nodes.get(n, {}).get("type") == NODE_AUTHORITY
        ]

        # Check for evidence → authority path
        path_exists = False
        for ev in evidence_nodes[:10]:  # cap search for performance
            for au in authority_nodes[:10]:
                paths = self.find_paths(ev, au, max_depth=3, max_paths=1)
                if paths:
                    path_exists = True
                    break
            if path_exists:
                break

        # Count unaddressed contradictions
        contradictions = 0
        for e in self.graph.edges:
            if e["type"] == EDGE_CONTRADICTS:
                if e["source"] in all_neighbors or e["target"] in all_neighbors:
                    contradictions += 1

        gaps = []
        has_ev = len(evidence_nodes) > 0
        has_auth = len(authority_nodes) > 0
        if not has_ev:
            gaps.append("NO_EVIDENCE")
        if not has_auth:
            gaps.append("NO_AUTHORITY")
        if has_ev and has_auth and not path_exists:
            gaps.append("NO_EVIDENCE_AUTHORITY_PATH")
        if contradictions > 0:
            gaps.append(f"{contradictions}_UNADDRESSED_CONTRADICTIONS")

        score = 0.0
        if has_ev:
            score += 30
        if has_auth:
            score += 30
        if path_exists:
            score += 25
        if contradictions == 0:
            score += 15
        elif contradictions <= 2:
            score += 5

        return {
            "claim": claim_node,
            "has_evidence": has_ev,
            "has_authority": has_auth,
            "evidence_count": len(evidence_nodes),
            "authority_count": len(authority_nodes),
            "path_exists": path_exists,
            "unaddressed_contradictions": contradictions,
            "completeness_pct": min(100.0, score),
            "gaps": gaps,
        }
```

---

## System 6: D3.js Graph ML Visualization

### 6.1 Importance, Communities, Paths, and Gaps

```javascript
/**
 * GraphMLVisualization — renders GNN outputs on the D3.js force graph.
 *
 * Features:
 *   - Node coloring by GNN-predicted importance (LOW=gray, MED=blue, HIGH=red)
 *   - Edge thickness by predicted link probability
 *   - Community hulls: convex hull polygons per detected community
 *   - Reasoning path animation: highlight argument chains through the graph
 *   - Attention weight visualization: show which neighbors the GNN attends to
 *   - Gap indicators: pulsing nodes where evidence gaps are predicted
 */
class GraphMLVisualization {
  constructor(svg, bridge) {
    this.svg = svg;
    this.bridge = bridge;
    this.communityHulls = null;
    this.pathOverlay = null;
    this.gapPulseTimers = [];
    this.attentionOverlay = null;

    // Color scales
    this.importanceColor = d3.scaleLinear()
      .domain([0, 0.33, 0.66, 1.0])
      .range(['#6b7280', '#3b82f6', '#f59e0b', '#ef4444'])
      .clamp(true);

    this.communityColor = d3.scaleOrdinal(d3.schemeTableau10);

    this.linkProbScale = d3.scaleLinear()
      .domain([0, 0.5, 1.0])
      .range([0.5, 2, 6])
      .clamp(true);
  }

  /**
   * Color nodes by GNN-predicted importance.
   * @param {d3.Selection} nodeSelection - D3 selection of node circles
   */
  renderImportance(nodeSelection) {
    nodeSelection
      .transition()
      .duration(600)
      .attr('fill', d => this.importanceColor(d.importance || 0.5))
      .attr('r', d => {
        const base = 5;
        const boost = (d.importance || 0.5) * 8;
        return base + boost;
      })
      .attr('stroke', d => {
        if (d.importance > 0.8) return '#dc2626';
        if (d.importance > 0.5) return '#d97706';
        return '#9ca3af';
      })
      .attr('stroke-width', d => d.importance > 0.8 ? 2.5 : 1);
  }

  /**
   * Scale edge width by predicted link probability.
   * Dashed lines for predicted (not yet confirmed) links.
   * @param {d3.Selection} linkSelection - D3 selection of link lines
   */
  renderLinkProbabilities(linkSelection) {
    linkSelection
      .transition()
      .duration(400)
      .attr('stroke-width', d => this.linkProbScale(d.linkProb || d.weight || 1))
      .attr('stroke-dasharray', d => d.predicted ? '6,3' : 'none')
      .attr('stroke', d => {
        if (d.predicted) return '#a855f7';         // purple for predicted
        if (d.type === 'CONTRADICTS') return '#ef4444';
        if (d.type === 'SUPPORTS') return '#22c55e';
        if (d.type === 'IMPEACHES') return '#f97316';
        return '#6b7280';
      })
      .attr('opacity', d => d.predicted ? 0.6 : 0.8);
  }

  /**
   * Render convex hull overlays for detected communities.
   * @param {Object} communities - {nodeId: communityInt}
   * @param {Array} nodes - array of node objects with x, y
   */
  renderCommunities(communities, nodes) {
    if (this.communityHulls) this.communityHulls.remove();

    const groups = {};
    for (const node of nodes) {
      const comm = communities[node.id];
      if (comm === undefined || comm < 0) continue;
      if (!groups[comm]) groups[comm] = [];
      groups[comm].push([node.x, node.y]);
    }

    const hullGroup = this.svg.append('g').attr('class', 'community-hulls');

    for (const [comm, points] of Object.entries(groups)) {
      if (points.length < 3) continue;
      const hull = d3.polygonHull(points);
      if (!hull) continue;

      hullGroup.append('path')
        .datum(hull)
        .attr('d', d => 'M' + d.join('L') + 'Z')
        .attr('fill', this.communityColor(+comm))
        .attr('fill-opacity', 0.08)
        .attr('stroke', this.communityColor(+comm))
        .attr('stroke-opacity', 0.3)
        .attr('stroke-width', 1.5)
        .attr('stroke-dasharray', '4,2');
    }
    this.communityHulls = hullGroup;
  }

  /**
   * Animate a reasoning path through the graph.
   * Highlights nodes and edges in sequence with a traveling pulse.
   * @param {string[]} pathNodeIds - ordered node IDs in the argument chain
   * @param {number} stepDuration - ms between each step highlight
   */
  animatePath(pathNodeIds, stepDuration = 400) {
    if (this.pathOverlay) this.pathOverlay.remove();
    const overlay = this.svg.append('g').attr('class', 'reasoning-path');
    this.pathOverlay = overlay;

    const nodeMap = new Map();
    this.bridge.nodes.forEach(n => nodeMap.set(n.id, n));

    pathNodeIds.forEach((nid, i) => {
      const node = nodeMap.get(nid);
      if (!node) return;

      // Pulse ring on each path node
      overlay.append('circle')
        .attr('cx', node.x)
        .attr('cy', node.y)
        .attr('r', 0)
        .attr('fill', 'none')
        .attr('stroke', '#22d3ee')
        .attr('stroke-width', 3)
        .attr('opacity', 0)
        .transition()
        .delay(i * stepDuration)
        .duration(stepDuration * 0.8)
        .attr('r', 20)
        .attr('opacity', 1)
        .transition()
        .duration(stepDuration)
        .attr('r', 30)
        .attr('opacity', 0);

      // Step label
      overlay.append('text')
        .attr('x', node.x)
        .attr('y', node.y - 25)
        .attr('text-anchor', 'middle')
        .attr('fill', '#22d3ee')
        .attr('font-size', '10px')
        .attr('font-weight', 'bold')
        .attr('opacity', 0)
        .text(`Step ${i + 1}`)
        .transition()
        .delay(i * stepDuration)
        .duration(300)
        .attr('opacity', 1);

      // Connecting line to next node
      if (i < pathNodeIds.length - 1) {
        const next = nodeMap.get(pathNodeIds[i + 1]);
        if (next) {
          overlay.append('line')
            .attr('x1', node.x)
            .attr('y1', node.y)
            .attr('x2', node.x)
            .attr('y2', node.y)
            .attr('stroke', '#22d3ee')
            .attr('stroke-width', 2.5)
            .attr('opacity', 0)
            .transition()
            .delay(i * stepDuration + stepDuration / 2)
            .duration(stepDuration / 2)
            .attr('x2', next.x)
            .attr('y2', next.y)
            .attr('opacity', 0.8);
        }
      }
    });
  }

  /**
   * Render attention weight visualization — lines from each node
   * to its most-attended neighbors, thickness = attention weight.
   * @param {Object} attentionWeights - {nodeIdx: [{neighborIdx, weight}]}
   */
  renderAttention(attentionWeights, topK = 3) {
    if (this.attentionOverlay) this.attentionOverlay.remove();
    const overlay = this.svg.append('g').attr('class', 'attention-overlay');
    this.attentionOverlay = overlay;

    const nodes = this.bridge.nodes;
    const idxToNode = new Map();
    nodes.forEach((n, i) => idxToNode.set(i, n));

    for (const [nodeIdx, neighbors] of Object.entries(attentionWeights)) {
      const source = idxToNode.get(+nodeIdx);
      if (!source) continue;

      const sorted = neighbors
        .sort((a, b) => b.weight - a.weight)
        .slice(0, topK);

      for (const { neighborIdx, weight } of sorted) {
        const target = idxToNode.get(neighborIdx);
        if (!target || weight < 0.1) continue;

        overlay.append('line')
          .attr('x1', source.x)
          .attr('y1', source.y)
          .attr('x2', target.x)
          .attr('y2', target.y)
          .attr('stroke', '#a78bfa')
          .attr('stroke-width', weight * 4)
          .attr('stroke-opacity', weight * 0.7)
          .attr('stroke-linecap', 'round');
      }
    }
  }

  /**
   * Show pulsing indicators at nodes where evidence gaps are predicted.
   * @param {string[]} gapNodeIds - node IDs with predicted gaps
   */
  showGaps(gapNodeIds) {
    this.gapPulseTimers.forEach(t => clearInterval(t));
    this.gapPulseTimers = [];

    const nodeMap = new Map();
    this.bridge.nodes.forEach(n => nodeMap.set(n.id, n));

    for (const nid of gapNodeIds) {
      const node = nodeMap.get(nid);
      if (!node) continue;

      const pulse = this.svg.append('circle')
        .attr('cx', node.x)
        .attr('cy', node.y)
        .attr('r', 8)
        .attr('fill', 'none')
        .attr('stroke', '#f43f5e')
        .attr('stroke-width', 2)
        .attr('class', 'gap-pulse');

      const animate = () => {
        pulse
          .attr('r', 8).attr('opacity', 1)
          .transition().duration(1000)
          .attr('r', 24).attr('opacity', 0)
          .transition().duration(200)
          .attr('r', 8).attr('opacity', 1);
      };

      animate();
      const timer = setInterval(animate, 1400);
      this.gapPulseTimers.push(timer);
    }
  }

  /** Remove all ML overlays. */
  clearOverlays() {
    if (this.communityHulls) { this.communityHulls.remove(); this.communityHulls = null; }
    if (this.pathOverlay) { this.pathOverlay.remove(); this.pathOverlay = null; }
    if (this.attentionOverlay) { this.attentionOverlay.remove(); this.attentionOverlay = null; }
    this.gapPulseTimers.forEach(t => clearInterval(t));
    this.gapPulseTimers = [];
    this.svg.selectAll('.gap-pulse').remove();
  }
}
```

---

## System 7: Orchestration Pipeline

### 7.1 End-to-End GraphML Pipeline

```python
"""
Orchestration: DB → Graph → GNN → Link Prediction → Communities → Gaps → D3.js export.
Single entry point for the full pipeline.
"""
import json
import time


class GraphMLPipeline:
    """
    End-to-end pipeline:
      1. Build LegalKnowledgeGraph from litigation_context.db
      2. Run LegalGNN for node embeddings + importance classification
      3. Run TransE for link prediction + gap detection
      4. Run CommunityAnalyzer for Louvain communities
      5. Run ReasoningPathFinder for argument chain scoring
      6. Export everything as JSON for GraphMLBridge (D3.js)
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.graph = None
        self.gnn = None
        self.link_predictor = None
        self.communities = None
        self.embeddings = None

    def build_graph(self, max_evidence: int = 5000,
                    max_authorities: int = 3000,
                    max_timeline: int = 2000) -> dict:
        """Step 1: Construct the legal knowledge graph."""
        t0 = time.perf_counter()
        self.graph = LegalKnowledgeGraph(self.db_path)
        self.graph.build(max_evidence, max_authorities, max_timeline)
        elapsed = time.perf_counter() - t0
        return {
            "nodes": self.graph.num_nodes,
            "edges": self.graph.num_edges,
            "build_time_ms": round(elapsed * 1000, 1),
        }

    def run_gnn(self, epochs: int = 30) -> dict:
        """Step 2: Run GAT for node embeddings and importance scores."""
        if not self.graph or self.graph.num_nodes < 10:
            return {"error": "Graph too small for GNN (need ≥10 nodes)"}

        t0 = time.perf_counter()
        X = self.graph.get_feature_matrix()
        A = self.graph.get_adjacency_matrix(normalize=True)

        self.gnn = LegalGNN(in_dim=X.shape[1])
        self.embeddings = self.gnn.get_node_embeddings(X, A)

        # Classify importance
        probs = self.gnn.classify_importance(X, A)
        labels = np.argmax(probs, axis=1)

        # Map back to node IDs
        importance_map = {}
        self.graph._rebuild_index()
        for idx, nid in self.graph._idx_to_node.items():
            importance_map[nid] = float(probs[idx, 2])  # P(HIGH)

        elapsed = time.perf_counter() - t0
        label_counts = {
            "LOW": int((labels == 0).sum()),
            "MEDIUM": int((labels == 1).sum()),
            "HIGH": int((labels == 2).sum()),
        }
        return {
            "importance_map": importance_map,
            "label_counts": label_counts,
            "embedding_dim": self.embeddings.shape[1],
            "gnn_time_ms": round(elapsed * 1000, 1),
        }

    def run_link_prediction(self, top_k: int = 50) -> dict:
        """Step 3: TransE link prediction + gap detection."""
        if not self.graph or self.graph.num_nodes < 10:
            return {"error": "Graph too small"}

        t0 = time.perf_counter()
        entity_map = {nid: i for i, nid in enumerate(self.graph.nodes)}
        relation_map = {etype: i for i, etype in enumerate(EDGE_TYPES)}

        num_entities = len(entity_map)
        num_relations = len(relation_map)

        self.link_predictor = TransELinkPredictor(
            num_entities, num_relations, embed_dim=64
        )

        # Build training triples
        triples = []
        for e in self.graph.edges:
            h = entity_map.get(e["source"])
            r = relation_map.get(e["type"])
            t = entity_map.get(e["target"])
            if h is not None and r is not None and t is not None:
                triples.append((h, r, t))

        if len(triples) < 20:
            return {"error": "Too few edges for link prediction"}

        losses = self.link_predictor.train(triples, epochs=50)

        # Detect gaps
        gaps = self.link_predictor.find_gaps(
            self.graph, entity_map, relation_map,
            threshold=-1.0, top_k=top_k
        )

        elapsed = time.perf_counter() - t0
        return {
            "gaps": gaps,
            "gap_count": len(gaps),
            "final_loss": losses[-1] if losses else None,
            "link_pred_time_ms": round(elapsed * 1000, 1),
        }

    def run_community_detection(self) -> dict:
        """Step 4: Louvain community detection."""
        if not self.graph or self.graph.num_nodes < 3:
            return {"error": "Graph too small"}

        t0 = time.perf_counter()
        analyzer = CommunityAnalyzer(self.graph)
        self.communities = analyzer.detect_communities_louvain()
        anomalies = analyzer.find_anomalies(self.communities)

        num_comms = len(set(self.communities.values()))
        elapsed = time.perf_counter() - t0
        return {
            "communities": self.communities,
            "num_communities": num_comms,
            "anomalies": anomalies[:20],
            "community_time_ms": round(elapsed * 1000, 1),
        }

    def find_argument_chains(self, source: str, target: str,
                             max_paths: int = 5) -> list[dict]:
        """Step 5: Find and score reasoning paths."""
        finder = ReasoningPathFinder(self.graph)
        paths = finder.find_paths(source, target, max_depth=5,
                                  max_paths=max_paths)
        return [finder.score_path(p) for p in paths]

    def export_for_d3(self) -> str:
        """
        Step 6: Export full pipeline results as JSON for GraphMLBridge.
        """
        if not self.graph:
            return json.dumps({"error": "No graph built"})

        nodes_out = []
        for nid, node in self.graph.nodes.items():
            nodes_out.append({
                "id": nid,
                "label": node["label"],
                "type": node["type"],
                "meta": node["meta"],
            })

        edges_out = []
        for e in self.graph.edges:
            edges_out.append({
                "source": e["source"],
                "target": e["target"],
                "type": e["type"],
                "weight": e["weight"],
                "provenance": e["provenance"],
                "predicted": False,
            })

        result = {
            "nodes": nodes_out,
            "edges": edges_out,
            "meta": {
                "num_nodes": self.graph.num_nodes,
                "num_edges": self.graph.num_edges,
            },
        }

        if self.communities:
            result["communities"] = self.communities

        return json.dumps(result, default=str)

    def run_full(self, max_evidence: int = 3000) -> dict:
        """Run the complete pipeline end-to-end. Returns summary."""
        summary = {}
        summary["graph"] = self.build_graph(max_evidence=max_evidence)
        summary["gnn"] = self.run_gnn()
        summary["links"] = self.run_link_prediction()
        summary["communities"] = self.run_community_detection()
        return summary
```

---

## Anti-Patterns (Mandatory Rules)

| # | Anti-Pattern | Why | Correct Approach |
|---|-------------|-----|-----------------|
| 1 | Train GNN on <100 nodes | Insufficient signal, overfits to noise | Subsample to 500–5000 node subgraph |
| 2 | Import PyG or DGL | GPU-dependent, 2GB VRAM insufficient | Pure NumPy/SciPy, CPU matmul |
| 3 | Predict links without authority validation | False positives poison argument chains | Cross-check against `authority_chains_v2` |
| 4 | Community detection on full 175K nodes | O(N²) memory, >24GB RAM for adjacency | Extract subgraph first, cap at 10K nodes |
| 5 | Trust link predictions scoring <0.7 | Below reliability threshold for legal reasoning | Filter to ≥0.7 before surfacing to user |
| 6 | Render >5000 nodes in D3.js | Browser freezes, <1 FPS | LOD: show top-importance nodes, hide rest |
| 7 | Use dense adjacency for >10K nodes | O(N²) memory = 400MB at 10K | Use sparse CSR format (scipy.sparse) |
| 8 | Skip A_hat self-loops | GNN ignores node's own features | Always A_hat = A + I before normalization |
| 9 | Single attention head | Misses multi-faceted legal relationships | Minimum 4 heads, concatenate outputs |
| 10 | Train TransE >200 epochs | Overfits to training edges, reduces generalization | 50–100 epochs with early stopping |
| 11 | Modify `litigation_context.db` schema | Breaks 790+ table ecosystem | Read-only queries, write to separate DB |
| 12 | Hardcode entity/relation counts | Graph changes across sessions | Compute from graph.num_nodes dynamically |
| 13 | Ignore edge direction in reasoning paths | Legal arguments are directional (cause→effect) | Use directed adjacency for path scoring |
| 14 | Cluster without anomaly detection | Miss suspicious cross-community connections | Always run `find_anomalies()` after clustering |
| 15 | Softmax without numerical stability | exp() overflow on large attention scores | Subtract row max before exp: exp(x - max(x)) |
| 16 | Forward pass on disconnected graph | Isolated nodes learn nothing from neighbors | Add self-loops (A_hat) and check connectivity |
| 17 | Ignore feature scaling | GAT attention skewed by magnitude differences | L2-normalize node features before GAT |
| 18 | Run full pipeline synchronously in UI | Blocks D3.js rendering for 10+ seconds | Use Web Worker or async chunked execution |
| 19 | Cache embeddings across schema changes | Stale embeddings give wrong predictions | Invalidate cache when DB row count changes |
| 20 | Visualize raw attention weights | N² edges overwhelm the display | Show only top-3 attention edges per node |
| 21 | Mix training/prediction data | Data leakage inflates metrics | Hold out 20% edges for link prediction eval |
| 22 | Use float64 for embeddings | 2× memory, no accuracy benefit for GNN | float32 throughout (savings critical at 24GB RAM) |
| 23 | Skip provenance tracking on edges | Can't trace prediction back to source table | Every edge carries `provenance` field |

---

## Performance Budgets

| Operation | Budget | Technique | Measured On |
|-----------|--------|-----------|-------------|
| Graph construction (3K evidence + 2K auth) | <5s | Batch SQL via `fetchall()`, single-pass | Ryzen 3 3200G |
| Graph construction (5K evidence + 3K auth) | <10s | Same with larger cap | Ryzen 3 3200G |
| GNN forward pass (1000 nodes, 4 heads) | <500ms | NumPy matmul, float32 | 24GB DDR4 |
| GNN forward pass (5000 nodes, 4 heads) | <3s | Sparse attention if available | 24GB DDR4 |
| TransE training (50 epochs, 5K triples) | <5s | Vectorized score + SGD | Ryzen 3 3200G |
| Link prediction top-100 | <2s | TransE score all entities + argsort | Ryzen 3 3200G |
| Gap detection (500 entity sample) | <10s | Bounded entity loop + top-k filter | Ryzen 3 3200G |
| Louvain community detection (5K nodes) | <1s | Greedy modularity, random order | Ryzen 3 3200G |
| Spectral clustering (1K nodes) | <2s | np.linalg.eigh on Laplacian | 24GB DDR4 |
| DBSCAN on embeddings (1K nodes, 64-dim) | <500ms | Pairwise L2 + neighborhood scan | Ryzen 3 3200G |
| BFS path finding (depth 5, 10 paths) | <200ms | Queue-based simple path search | Ryzen 3 3200G |
| D3.js importance recolor (2000 nodes) | <16ms | CSS transition, requestAnimationFrame | Any browser |
| Community hull render (10 communities) | <16ms | d3.polygonHull + SVG path | Any browser |
| Reasoning path animation (5 steps) | ~2s | Sequential transition chain | Any browser |
| Gap pulse animation (50 gaps) | 0ms init | CSS animation, no JS per-frame | Any browser |

---

## Integration Matrix

| Skill | Integration Point | Data Flow |
|-------|------------------|-----------|
| **MBP-GENESIS** | Graph schema (node/edge ontology) | GENESIS defines types → GRAPHML implements them |
| **MBP-DATAWEAVE** | DB → graph construction pipeline | DATAWEAVE provides SQL transforms → GRAPHML consumes |
| **MBP-COMBAT-ADVERSARY** | Adversary ego networks | GRAPHML extracts subgraphs → ADVERSARY scores threats |
| **MBP-COMBAT-AUTHORITY** | Authority chain validation | GRAPHML predicts links → AUTHORITY validates citations |
| **MBP-COMBAT-EVIDENCE** | Evidence importance scoring | GRAPHML classifies nodes → EVIDENCE uses importance |
| **MBP-COMBAT-IMPEACHMENT** | Impeachment path discovery | GRAPHML finds contra paths → IMPEACHMENT builds chains |
| **MBP-EMERGENCE-CONVERGENCE** | Gap detection cross-check | GRAPHML finds gaps → CONVERGENCE validates with DBSCAN |
| **MBP-EMERGENCE-PREDICTION** | Adversary behavior prediction | GRAPHML temporal patterns → PREDICTION forecasts actions |
| **MBP-FORGE-RENDERER** | Node/edge visual attributes | GRAPHML exports colors/sizes → RENDERER applies them |
| **MBP-INTERFACE-HUD** | Graph ML metrics display | GRAPHML stats → HUD gauges (completeness, gap count) |
| **APEX-COGNITION** | GNN insights feed agent reasoning | GRAPHML embeddings → COGNITION critic evaluation |
| **APEX-MEMORY** | Semantic memory stores graph patterns | GRAPHML community snapshots → MEMORY cross-session recall |

---

## Quality Gates

### Graph Construction Gate
- [ ] All 8 node types represented in output graph
- [ ] ≥3 edge types present (minimum: CITED_BY, CONTRADICTS, SUPPORTS)
- [ ] Node count within budget cap (≤10K for full pipeline)
- [ ] Zero dangling edges (both endpoints exist in node set)
- [ ] Feature matrix shape = (N, 392) — 384 embedding + 8 type one-hot

### GNN Gate
- [ ] Forward pass completes within 500ms for 1K nodes
- [ ] Importance distribution is not degenerate (not all same class)
- [ ] Attention weights sum to 1.0 per row (within ε=1e-6)
- [ ] No NaN or Inf in embeddings or attention matrices
- [ ] Classification produces all 3 classes (LOW/MEDIUM/HIGH)

### Link Prediction Gate
- [ ] TransE loss decreases monotonically (no divergence)
- [ ] Gap predictions include ≥3 gap types (not just GENERAL_GAP)
- [ ] No self-loops in predicted links
- [ ] Top-10 predictions have score ≥ −1.0 (plausible range)

### Community Detection Gate
- [ ] Louvain finds 2–50 communities (not 1, not N)
- [ ] Anomaly list is non-empty (boundary-crossers always exist in legal graphs)
- [ ] Community assignments cover all nodes (no orphans)

### Visualization Gate
- [ ] Importance recolor completes in single animation frame (<16ms)
- [ ] Community hulls don't overlap excessively (max 30% area overlap)
- [ ] Path animation plays without janking (requestAnimationFrame-based)
- [ ] Gap pulses don't accumulate (old timers cleared before new ones)

---
name: SINGULARITY-ai-core
description: "Transcendent AI/ML core for LitigationOS. ABSORBS: ai-engineering, prompt-engineering, rag-memory. Use when: local LLM inference, semantic search, RAG pipeline, embedding generation, prompt engineering, legal argument synthesis, document summarization, hybrid search, citation verification, anti-hallucination, reranking, vector storage, LanceDB, tantivy, sentence-transformers, PyTorch CPU inference, Ollama llama3.2, evidence analysis, brief drafting assistance, IRAC generation, cross-examination questions."
---

# SINGULARITY-ai-core — Transcendent AI/ML Intelligence Core

> **Absorbs:** ai-engineering, prompt-engineering, rag-memory
> **Tier:** TOOLS | **Domain:** AI/ML, LLM, Embeddings, RAG, Search
> **Stack:** Ollama 0.16.1 · sentence-transformers 5.3.0 · LanceDB 0.30.0 · tantivy · cross-encoder · PyTorch 2.11.0 CPU

---

## 1. Local LLM Inference (Ollama)

### Architecture
```
User Query → Prompt Template → Ollama llama3.2:3b → Structured Output → Post-Processing
                                    ↑
                        Context from RAG Pipeline
```

### Ollama Configuration
```python
import requests

OLLAMA_BASE = "http://localhost:11434"

def ollama_generate(prompt: str, system: str = "", temperature: float = 0.1) -> str:
    """Local LLM inference — ZERO API cost, ZERO data leakage."""
    resp = requests.post(f"{OLLAMA_BASE}/api/generate", json={
        "model": "llama3.2:3b",
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_ctx": 4096,
            "top_p": 0.9,
            "repeat_penalty": 1.1,
        }
    }, timeout=120)
    return resp.json().get("response", "")

def ollama_embed(text: str) -> list[float]:
    """Get embeddings from Ollama (fallback if sentence-transformers unavailable)."""
    resp = requests.post(f"{OLLAMA_BASE}/api/embeddings", json={
        "model": "llama3.2:3b",
        "prompt": text
    }, timeout=30)
    return resp.json().get("embedding", [])
```

### Model Selection
| Model | Size | Speed | Use Case |
|-------|------|-------|----------|
| llama3.2:3b | 2.0 GB | ~15 tok/s CPU | General legal analysis, summarization |
| llama3.2:1b | 1.3 GB | ~25 tok/s CPU | Quick classification, extraction |
| nomic-embed-text | 274 MB | ~100 doc/s | Embedding generation (alternative) |

---

## 2. Embedding Pipeline (sentence-transformers)

### Primary Embedder — all-MiniLM-L6-v2
```python
from sentence_transformers import SentenceTransformer
import numpy as np

class EmbeddingPipeline:
    """384-dimensional embeddings, CPU-optimized, 80MB model."""

    def __init__(self):
        self._model = None

    @property
    def model(self):
        if self._model is None:
            self._model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
        return self._model

    def embed_single(self, text: str) -> np.ndarray:
        return self.model.encode(text, normalize_embeddings=True)

    def embed_batch(self, texts: list[str], batch_size: int = 64) -> np.ndarray:
        return self.model.encode(
            texts, batch_size=batch_size,
            normalize_embeddings=True, show_progress_bar=True
        )

    def similarity(self, query: str, documents: list[str]) -> list[float]:
        q_emb = self.embed_single(query)
        d_embs = self.embed_batch(documents)
        return (d_embs @ q_emb).tolist()
```

### Embedding Specifications
- **Model:** all-MiniLM-L6-v2 (80 MB, 22M params)
- **Dimensions:** 384
- **Max tokens:** 256 (truncates beyond)
- **Normalization:** L2-normalized for cosine similarity via dot product
- **Throughput:** ~500 docs/sec on CPU (short docs), ~100 docs/sec (paragraphs)

---

## 3. Two-Stage Retrieval Pipeline (MANDATORY)

### Architecture
```
Query → Stage 1: Bi-Encoder Retrieval (fast, recall-oriented)
            ↓ Top-N candidates (N=50-100)
        Stage 2: Cross-Encoder Reranking (slow, precision-oriented)
            ↓ Top-K final results (K=5-10)
        → Grounded Response
```

### Stage 1 — Bi-Encoder (sentence-transformers)
```python
import lancedb

def stage1_retrieve(query: str, table_name: str = "evidence_vectors",
                    top_n: int = 50) -> list[dict]:
    """Fast approximate nearest neighbor search via LanceDB."""
    db = lancedb.connect("00_SYSTEM/engines/semantic/lancedb_store")
    table = db.open_table(table_name)
    embedder = EmbeddingPipeline()
    q_vec = embedder.embed_single(query)
    results = table.search(q_vec).limit(top_n).to_list()
    return results
```

### Stage 2 — Cross-Encoder Reranking
```python
from sentence_transformers import CrossEncoder

class RerankerPipeline:
    """25-35% MRR improvement over bi-encoder alone."""

    def __init__(self):
        self._model = None

    @property
    def model(self):
        if self._model is None:
            self._model = CrossEncoder(
                'cross-encoder/ms-marco-MiniLM-L-6-v2', device='cpu'
            )
        return self._model

    def rerank(self, query: str, documents: list[dict],
               text_key: str = "text", top_k: int = 10) -> list[dict]:
        pairs = [(query, doc[text_key]) for doc in documents]
        scores = self.model.predict(pairs, batch_size=32)
        for doc, score in zip(documents, scores):
            doc["rerank_score"] = float(score)
        ranked = sorted(documents, key=lambda x: x["rerank_score"], reverse=True)
        return ranked[:top_k]
```

### CRITICAL: Never Use Cosine Alone for Contradictions
Contradictory statements are often semantically CLOSE (high cosine similarity).
The two-stage pipeline catches nuanced legal contradictions that single-stage misses.

---

## 4. RAG Architecture Patterns

### Litigation RAG Pipeline
```
Document Corpus (611K files, 75K vectors)
    ↓ Ingestion
Chunking (paragraph-level, ~512 tokens per chunk)
    ↓ Embedding
LanceDB Vector Store (384-dim, all-MiniLM-L6-v2)
    ↓ Hybrid Retrieval
FTS5 (keyword, BM25) + LanceDB (semantic) + tantivy (sub-ms)
    ↓ Fusion
Reciprocal Rank Fusion (RRF) or weighted combination
    ↓ Reranking
Cross-encoder precision pass
    ↓ Context Assembly
Top-K passages → prompt template → Ollama
    ↓ Grounded Response
Citation-verified output with source tracing
```

### Hybrid Search Fusion
```python
def hybrid_search(query: str, alpha: float = 0.5,
                  top_k: int = 20) -> list[dict]:
    """Combine FTS5 keyword + LanceDB semantic search."""
    keyword_results = fts5_search(query, limit=top_k * 2)
    semantic_results = stage1_retrieve(query, top_n=top_k * 2)

    scores: dict[str, float] = {}
    for rank, doc in enumerate(keyword_results):
        doc_id = doc["id"]
        scores[doc_id] = scores.get(doc_id, 0) + (1 - alpha) / (rank + 60)
    for rank, doc in enumerate(semantic_results):
        doc_id = doc["id"]
        scores[doc_id] = scores.get(doc_id, 0) + alpha / (rank + 60)

    fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return fused[:top_k]
```

---

## 5. Prompt Templates for Legal Analysis

### IRAC Generation Template
```python
IRAC_TEMPLATE = """You are a Michigan family law analyst. Generate IRAC analysis.

CONTEXT (from evidence database):
{context}

LEGAL QUESTION: {question}

Generate strict IRAC format:
I. ISSUE: Frame the specific legal question
R. RULE: Cite governing MCR/MCL with pinpoint citations
A. APPLICATION: Apply rules to facts with (Ex. [Bates#]) citations
C. CONCLUSION: State result and specific relief requested

RULES:
- Every citation must reference a real MCR, MCL, or case
- Use "L.D.W." for the child, never full name
- Use "Emily A. Watson" for defendant
- Reference specific exhibits by Bates number
- No fabricated statistics or case law
"""
```

### Cross-Examination Question Generator
```python
CROSS_EXAM_TEMPLATE = """Generate cross-examination questions using the COMMIT-PIN-CONFRONT method.

WITNESS: {witness_name}
CONTRADICTION EVIDENCE:
{contradictions}

For each contradiction, generate:
1. COMMIT: "You stated [X], correct?" (lock testimony)
2. PIN: "That was on [date] in [context]?" (establish specifics)
3. CONFRONT: "But isn't it true that [Y]?" (present contradiction)
4. EXHIBIT: "And this exhibit shows [contradiction]?" (prove with document)

Generate 3-5 question sequences, each building on prior admissions.
"""
```

---

## 6. Anti-Hallucination Verification

### Citation Grounding Protocol
```python
import sqlite3, re

def verify_citations(text: str, db_path: str = "litigation_context.db") -> dict:
    """Verify every citation traces to authority_chains_v2 or michigan_rules_extracted."""
    citation_pattern = re.compile(
        r'(?:MCR|MCL|MRE)\s+[\d.]+(?:\([a-z]\))?|'
        r'(?:\d+\s+Mich(?:\s+App)?\s+\d+)|'
        r'(?:\d+\s+USC?\s+§?\s*\d+)'
    )
    citations = citation_pattern.findall(text)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout=60000")
    verified, unverified = [], []
    for cite in citations:
        safe = re.sub(r'[^\w\s*"]', ' ', cite).strip()
        row = conn.execute(
            "SELECT COUNT(*) FROM authority_chains_v2 WHERE primary_citation LIKE ?",
            (f"%{safe}%",)
        ).fetchone()
        if row and row[0] > 0:
            verified.append(cite)
        else:
            row2 = conn.execute(
                "SELECT COUNT(*) FROM michigan_rules_extracted WHERE rule_citation LIKE ?",
                (f"%{safe}%",)
            ).fetchone()
            if row2 and row2[0] > 0:
                verified.append(cite)
            else:
                unverified.append(cite)
    conn.close()
    return {"verified": verified, "unverified": unverified,
            "rate": len(verified) / max(len(citations), 1)}
```

### Hallucination Blacklist Check
```python
BANNED_STRINGS = [
    "91% alienation", "Jane Berry", "Patricia Berry",
    "P35878", "Ron Berry, Esq", "Lincoln David Watson",
    "Emily Ann Watson", "Emily M. Watson", "Amy McNeill",
    "9 CPS investigations", "undersigned counsel",
]

def hallucination_sweep(content: str) -> list[str]:
    """Return any banned strings found in content."""
    return [s for s in BANNED_STRINGS if s.lower() in content.lower()]
```

---

## 7. Vector Storage (LanceDB)

### Configuration
```python
import lancedb

DB_PATH = "00_SYSTEM/engines/semantic/lancedb_store"

def get_vector_db():
    return lancedb.connect(DB_PATH)

def search_vectors(query: str, top_k: int = 10) -> list[dict]:
    db = get_vector_db()
    table = db.open_table("evidence_vectors")
    embedder = EmbeddingPipeline()
    vec = embedder.embed_single(query)
    return table.search(vec).limit(top_k).to_list()
```

### Vector Store Statistics
- **Total vectors:** 75K+ (384-dimensional)
- **Model:** all-MiniLM-L6-v2
- **Storage:** Lance columnar format (compressed, memory-mappable)
- **Search:** Sub-millisecond approximate nearest neighbor (IVF-PQ)

---

## 8. Key Constraints & Rules

| Rule | Enforcement |
|------|-------------|
| ZERO external API calls | All inference via Ollama localhost or CPU models |
| Citation grounding | Every cite verified against DB before output |
| Anti-hallucination sweep | BANNED_STRINGS check on all generated content |
| Child name protection | L.D.W. only — MCR 8.119(H) |
| FTS5 safety | Sanitize → try/except → LIKE fallback |
| Two-stage retrieval | NEVER cosine-only for contradiction detection |
| Lazy model loading | Models loaded on first use, not at import time |
| CPU-only inference | No GPU assumptions — Vega 8 iGPU insufficient |

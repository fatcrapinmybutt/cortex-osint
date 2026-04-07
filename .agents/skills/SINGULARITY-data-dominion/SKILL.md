---
name: SINGULARITY-data-dominion
version: "2.0.0"
description: "Transcendent data engineering and database mastery for LitigationOS. Use when: SQL queries, DuckDB analytics, LanceDB vectors, Polars DataFrames, FTS5 search, RAG pipelines, SQLite optimization, schema design, data migration, cross-database federation, vector embeddings, semantic search, indexing strategy, query optimization, connection pooling, WAL mode, PRAGMA tuning, batch operations."
---

# SINGULARITY-data-dominion — Transcendent Data Engineering

> **Version:** 2.0.0 | **Tier:** CORE | **Domain:** Data Engineering & Database Mastery
> **Absorbs:** data-engineering + database-mastery + rag-memory
> **Activation:** "SQL", "query", "database", "DuckDB", "LanceDB", "vector", "FTS5", "Polars", "analytics", "RAG", "embedding", "schema"

---

## Layer 1: SQLite Mastery (litigation_context.db — 1.3 GB, 790+ tables)

### Connection Setup — Three-Tier Strategy

Every connection MUST set these PRAGMAs. Missing any = guaranteed SQLITE_BUSY under load.

```python
import sqlite3
from shared import get_db, sanitize_fts5, config

# Tier 1 — Multiplexer (hot path, high-throughput)
conn = get_db("litigation_context")
conn.execute("PRAGMA busy_timeout = 180000")    # 3 min
conn.execute("PRAGMA journal_mode = WAL")
conn.execute("PRAGMA cache_size = -131072")      # 128 MB
conn.execute("PRAGMA mmap_size = 12884901888")   # 12 GB on NVMe
conn.execute("PRAGMA temp_store = MEMORY")
conn.execute("PRAGMA synchronous = NORMAL")

# Tier 2 — Standard (MCP, daemon, engines)
conn.execute("PRAGMA busy_timeout = 60000")      # 60 s
conn.execute("PRAGMA cache_size = -32000")        # 32 MB
conn.execute("PRAGMA temp_store = MEMORY")
conn.execute("PRAGMA synchronous = NORMAL")

# Tier 3 — Simple (one-off scripts, temp queries)
conn.execute("PRAGMA busy_timeout = 30000")      # 30 s
conn.execute("PRAGMA cache_size = -8000")         # 8 MB
```

### FTS5 Safety Protocol (Rule 15 — MANDATORY)

Every FTS5 query must follow this exact sequence. No exceptions.

```python
import re

def safe_fts5_search(conn, table, fts_table, query, limit=25):
    """FTS5 search with sanitization and LIKE fallback."""
    # Step 1: Sanitize — strip everything except word chars, spaces, wildcards, quotes
    clean = re.sub(r'[^\w\s*"]', ' ', query).strip()
    if not clean:
        return []

    # Step 2: Try FTS5 MATCH
    try:
        rows = conn.execute(f"""
            SELECT *, snippet({fts_table}, 0, '>>>', '<<<', '...', 32) AS snip
            FROM {fts_table}
            WHERE {fts_table} MATCH ?
            ORDER BY rank LIMIT ?
        """, (clean, limit)).fetchall()
        if rows:
            return rows
    except Exception:
        pass  # FTS5 failed — fall through to LIKE

    # Step 3: LIKE fallback with parameterized bind
    like_param = f"%{clean}%"
    return conn.execute(f"""
        SELECT * FROM {table}
        WHERE quote_text LIKE ? OR category LIKE ?
        LIMIT ?
    """, (like_param, like_param, limit)).fetchall()
```

### Schema Introspection (Rule 16 — Before ANY Unfamiliar Table)

```python
def get_columns(conn, table_name):
    """Introspect table schema before querying. MANDATORY for unfamiliar tables."""
    cols = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    if not cols:
        raise ValueError(f"Table '{table_name}' does not exist")
    return {row[1]: row[2] for row in cols}  # {name: type}

def adaptive_select(conn, table, required_cols, optional_cols=None):
    """Build SELECT dynamically based on actual schema."""
    actual = set(get_columns(conn, table).keys())
    select_cols = [c for c in required_cols if c in actual]
    if optional_cols:
        select_cols += [c for c in optional_cols if c in actual]
    if not select_cols:
        raise ValueError(f"No required columns found in {table}")
    return f"SELECT {', '.join(select_cols)} FROM {table}"
```

### Batch Operations (10-100× Faster)

```python
# CORRECT — executemany batch insert
rows = [(r["text"], r["source"], r["lane"]) for r in evidence_data]
conn.executemany(
    "INSERT OR IGNORE INTO evidence_quotes (quote_text, source_file, lane) VALUES (?, ?, ?)",
    rows
)
conn.commit()

# WRONG — row-by-row (10-100× slower)
for r in evidence_data:
    conn.execute("INSERT INTO evidence_quotes ...", (r["text"],))
    conn.commit()  # commit per row = disaster
```

### Consolidate COUNT(*) Calls

```sql
-- CORRECT — single round-trip with subqueries
SELECT
    (SELECT COUNT(*) FROM evidence_quotes) AS evidence_count,
    (SELECT COUNT(*) FROM timeline_events) AS timeline_count,
    (SELECT COUNT(*) FROM authority_chains_v2) AS authority_count,
    (SELECT COUNT(*) FROM impeachment_matrix) AS impeachment_count;

-- WRONG — 4 separate queries (4 round-trips)
SELECT COUNT(*) FROM evidence_quotes;
SELECT COUNT(*) FROM timeline_events;
-- ... etc
```

### Composite Indexes for Hot Queries

```sql
-- Evidence by lane + category (hot query in MEEK routing)
CREATE INDEX IF NOT EXISTS idx_eq_lane_cat ON evidence_quotes(lane, category);

-- Authority chains by citation + lane
CREATE INDEX IF NOT EXISTS idx_ac_cite_lane ON authority_chains_v2(primary_citation, lane);

-- Timeline by date range (chronology builder)
CREATE INDEX IF NOT EXISTS idx_te_date ON timeline_events(event_date);

-- Impeachment by target + severity (cross-exam prep)
CREATE INDEX IF NOT EXISTS idx_imp_target_sev ON impeachment_matrix(target, impeachment_value DESC);
```

### Cursor-Based Pagination (NOT OFFSET)

```sql
-- CORRECT — cursor-based (fast at any depth, O(log n))
SELECT id, quote_text, source_file
FROM evidence_quotes
WHERE id > :last_seen_id
ORDER BY id LIMIT 50;

-- WRONG — OFFSET (degrades linearly, scans skipped rows)
SELECT id, quote_text, source_file
FROM evidence_quotes
ORDER BY id LIMIT 50 OFFSET 150000;  -- scans 150K rows to skip them
```

### Cross-Database Federation with ATTACH

```python
# Federation across 70+ databases on 6 drives
conn.execute("ATTACH DATABASE ? AS authority", (str(authority_db_path),))
conn.execute("ATTACH DATABASE ? AS brain", (str(brain_db_path),))

# Cross-DB join (prefix ALL table refs with schema alias)
results = conn.execute("""
    SELECT e.quote_text, a.citation_text, b.interpretation
    FROM main.evidence_quotes e
    JOIN authority.authority_chains_v2 a ON e.authority_id = a.id
    JOIN brain.interpretations b ON a.citation_id = b.citation_id
    WHERE e.lane = ?
""", ("A",)).fetchall()

# exFAT drives (J:\) — NO WAL MODE
# conn for J:\ databases:
conn_j = sqlite3.connect("file:///J:/path/db.sqlite?immutable=1", uri=True)
# Or if writes needed:
conn_j.execute("PRAGMA journal_mode = DELETE")
conn_j.execute("PRAGMA synchronous = FULL")
```

---

## Layer 2: DuckDB Analytics (10-100× Faster Than SQLite OLAP)

### When to Use DuckDB vs SQLite

| Query Type | Use DuckDB | Use SQLite |
|------------|-----------|------------|
| GROUP BY with 100K+ rows | ✅ 10-100× faster | ❌ Slow |
| Window functions (RANK, LAG) | ✅ Optimized | ⚠️ Works but slower |
| Complex CTEs with aggregation | ✅ Columnar advantage | ❌ Row-store penalty |
| Single-row INSERT/UPDATE | ❌ Not designed for OLTP | ✅ Fast |
| FTS5 text search | ❌ No FTS5 | ✅ Native support |
| Point lookups by ID | ❌ Overhead not worth it | ✅ Sub-ms with index |
| Analytical dashboards | ✅ Purpose-built | ❌ Too slow |

### DuckDB + SQLite Scanner Integration

```python
import duckdb

con = duckdb.connect()
con.install_extension("sqlite_scanner")
con.load_extension("sqlite_scanner")

# ATTACH litigation_context.db as read-only
con.execute("ATTACH 'litigation_context.db' AS lit (TYPE sqlite, READ_ONLY)")

# 10-100× faster analytical query
result = con.execute("""
    SELECT lane, category,
           COUNT(*) AS cnt,
           COUNT(DISTINCT source_file) AS unique_sources
    FROM lit.evidence_quotes
    WHERE lane IN ('A', 'D', 'E')
    GROUP BY lane, category
    ORDER BY cnt DESC
""").fetchdf()
```

### Litigation Analytics Patterns

```sql
-- Judicial violation trends by month (DuckDB)
SELECT strftime(event_date, '%Y-%m') AS month,
       violation_type,
       COUNT(*) AS violations
FROM lit.judicial_violations
GROUP BY month, violation_type
ORDER BY month, violations DESC;

-- Evidence density heatmap per lane + category
SELECT lane, category,
       COUNT(*) AS evidence_count,
       AVG(CAST(impeachment_value AS FLOAT)) AS avg_severity
FROM lit.impeachment_matrix
GROUP BY lane, category
HAVING evidence_count > 5
ORDER BY avg_severity DESC;

-- Filing readiness aggregation with window functions
SELECT lane, vehicle_name,
       evidence_count, authority_count,
       RANK() OVER (ORDER BY evidence_count + authority_count DESC) AS readiness_rank
FROM lit.filing_readiness;
```

---

## Layer 3: LanceDB Vector Search (75K Vectors, 384-dim)

### Embedding Generation

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")  # 80 MB, CPU-fast

# Generate embeddings for evidence text
texts = ["parental alienation documented", "ex parte order issued"]
embeddings = model.encode(texts, normalize_embeddings=True)
# Shape: (2, 384) — 384-dimensional unit vectors
```

### Vector Search via NEXUS Tool

```python
# Preferred: use the vector_search extension tool
# Returns semantically similar content from 75K vectors
result = vector_search(query="judicial bias ex parte orders", top_k=10)
```

### Hybrid Search: BM25 + Vector Fusion

```python
def hybrid_search(query, keyword_weight=0.4, vector_weight=0.6, top_k=20):
    """Combine BM25 keyword search with vector semantic search."""
    # Stage 1: BM25 keyword results (tantivy/FTS5)
    keyword_results = safe_fts5_search(conn, "evidence_quotes", "evidence_fts", query)

    # Stage 2: Vector similarity results (LanceDB)
    vector_results = vector_search(query=query, top_k=top_k)

    # Stage 3: Reciprocal Rank Fusion (RRF)
    scores = {}
    for rank, r in enumerate(keyword_results):
        scores[r["id"]] = keyword_weight / (60 + rank)
    for rank, r in enumerate(vector_results):
        rid = r.get("id", rank)
        scores[rid] = scores.get(rid, 0) + vector_weight / (60 + rank)

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
```

### When to Use Each Search Mode

| Need | Method | Tool |
|------|--------|------|
| Exact phrase match | FTS5 with quotes | `search_evidence` |
| Conceptual similarity | Vector search | `vector_search` |
| Best overall relevance | Hybrid (BM25 + vector) | Custom fusion |
| Cross-exam ammunition | Impeachment search | `search_impeachment` |
| Specific citation lookup | Authority search | `search_authority_chains` |

### Cross-Encoder Reranking (25-35% MRR Boost)

```python
from sentence_transformers import CrossEncoder

reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

# Rerank top-50 candidates from bi-encoder retrieval
pairs = [(query, doc["text"]) for doc in candidates[:50]]
scores = reranker.predict(pairs)

# Sort by cross-encoder score for precision
reranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
```

---

## Layer 4: Polars DataFrames (2-10× Faster Than pandas)

### Lazy Evaluation for Large Datasets

```python
import polars as pl

# Lazy frame — computation deferred until .collect()
lf = pl.scan_csv("evidence_export.csv")
result = (
    lf.filter(pl.col("lane") == "A")
      .group_by("category")
      .agg([
          pl.col("quote_text").count().alias("count"),
          pl.col("impeachment_value").mean().alias("avg_severity"),
      ])
      .sort("count", descending=True)
      .collect()
)
```

### DuckDB → Polars Integration

```python
import duckdb, polars as pl

con = duckdb.connect()
# DuckDB query → Polars DataFrame (zero-copy via Arrow)
df = con.execute("""
    SELECT lane, category, COUNT(*) AS cnt
    FROM lit.evidence_quotes GROUP BY lane, category
""").pl()  # .pl() returns Polars DataFrame directly
```

---

## Layer 5: RAG Pipeline Architecture

### End-to-End Pipeline

```
Document Ingestion (pypdfium2, python-docx)
    ↓
Chunking (512 tokens, 64-token overlap)
    ↓
Embedding (all-MiniLM-L6-v2, 384-dim, CPU)
    ↓
Storage (LanceDB — 75K vectors on disk)
    ↓
Retrieval (hybrid: BM25 keyword + vector cosine)
    ↓
Reranking (cross-encoder/ms-marco-MiniLM)
    ↓
Generation (Ollama llama3.2:3b local OR context assembly)
```

### PDF Extraction (pypdfium2 — 5× Faster Than PyMuPDF)

```python
import pypdfium2 as pdfium

def extract_pdf_text(path, max_pages=30):
    """Extract text from PDF using pypdfium2 (5× faster than PyMuPDF)."""
    pdf = pdfium.PdfDocument(path)
    pages = []
    for i in range(min(len(pdf), max_pages)):
        page = pdf[i]
        text = page.get_textpage().get_text_range()
        pages.append({"page_number": i + 1, "text": text})
    pdf.close()
    return pages
```

---

## Anti-Patterns (VIOLATIONS = IMMEDIATE FAILURE)

| # | Anti-Pattern | Correct Pattern |
|---|-------------|-----------------|
| 1 | `LIKE '%term%'` when FTS5 exists | FTS5 MATCH with sanitization + LIKE fallback |
| 2 | Hardcoded DB paths `r"C:\Users\andre\..."` | `shared.get_db()` or `shared.get_db_path()` |
| 3 | pandas for DataFrames | Polars (2-10× faster, lazy evaluation) |
| 4 | Query without `PRAGMA table_info()` on unfamiliar tables | Always introspect schema first |
| 5 | `OFFSET` pagination on 100K+ tables | Cursor-based `WHERE id > :last_seen` |
| 6 | Row-by-row INSERT in loops | `executemany()` batch insert |
| 7 | Multiple separate `COUNT(*)` calls | Single query with subqueries |
| 8 | `json.load()` for large JSON | `orjson` (small) or `ijson` streaming (large) |
| 9 | WAL mode on exFAT (J:\ drive) | DELETE mode or `immutable=1` URI |
| 10 | Missing `PRAGMA busy_timeout` | Always set ≥30000 ms |
| 11 | `SELECT *` in hot paths | Explicit column lists |
| 12 | Cosine similarity alone for contradictions | Two-stage: bi-encoder → cross-encoder |
| 13 | No commit after batch insert | `conn.commit()` after `executemany` |
| 14 | Opening DB inside shell commands | Dedicated Python scripts with proper PRAGMAs |
| 15 | Trusting `CREATE TABLE IF NOT EXISTS` for schema | It silently skips different schemas — introspect |

## Performance Budgets

| Operation | Target | Degraded | Unacceptable |
|-----------|--------|----------|--------------|
| Single-row lookup (indexed) | < 1 ms | < 5 ms | > 50 ms |
| FTS5 search (25 results) | < 10 ms | < 50 ms | > 200 ms |
| DuckDB GROUP BY (100K rows) | < 50 ms | < 200 ms | > 1 s |
| Vector search (top-10) | < 20 ms | < 100 ms | > 500 ms |
| Batch insert (1000 rows) | < 100 ms | < 500 ms | > 2 s |
| Cross-DB ATTACH + query | < 200 ms | < 1 s | > 5 s |
| Cross-encoder rerank (50 pairs) | < 500 ms | < 2 s | > 5 s |
| Full hybrid search pipeline | < 300 ms | < 1 s | > 3 s |

## Decision Matrix: Which Tool for Which Data Task

| Task | Primary Tool | Fallback | Why |
|------|-------------|----------|-----|
| Point lookup by ID | SQLite | — | Sub-ms with index |
| Full-text keyword search | FTS5 + BM25 | LIKE fallback | Ranked relevance |
| Semantic similarity | LanceDB vector | FTS5 keyword | Conceptual matching |
| Analytical aggregation | DuckDB | SQLite GROUP BY | 10-100× columnar |
| DataFrame manipulation | Polars | DuckDB SQL | Lazy eval, zero-copy |
| JSON parsing (< 100 MB) | orjson | json stdlib | 10× speed |
| JSON parsing (> 100 MB) | ijson streaming | — | O(1) memory |
| PDF text extraction | pypdfium2 | PyMuPDF | 5× faster |
| Schema validation | msgspec.Struct | — | 10-80× vs pydantic |
| Cross-table fusion | nexus_fuse tool | Manual JOINs | 5 sources at once |

## Key NEXUS Extension Tools

| Tool | Action | Use For |
|------|--------|---------|
| `query_litigation_db` | `query` | Parameterized SQL (read/write) |
| `search_evidence` | `search_evidence` | FTS5 evidence search |
| `vector_search` | `vector_search` | Semantic similarity |
| `nexus_fuse` | `nexus_fuse` | Cross-table fusion |
| `search_impeachment` | `search_impeachment` | Cross-exam ammunition |
| `search_contradictions` | `search_contradictions` | Adversary inconsistencies |
| `search_authority_chains` | `search_authority` | Citation chain lookup |

---

*END OF SINGULARITY-data-dominion v2.0.0 — DuckDB · LanceDB · Polars · FTS5 · RAG · ZERO API*

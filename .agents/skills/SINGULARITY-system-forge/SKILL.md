---
name: SINGULARITY-system-forge
version: "2.0.0"
description: "Transcendent system design and engine architecture for LitigationOS. Use when: designing engines, Go concurrent systems, Rust CLI tools, performance optimization, clean code practices, SOLID principles, architecture decisions, system design patterns, engine fleet management, daemon architecture, connection pooling, thread safety, error recovery, circuit breakers, graceful degradation."
---

# SINGULARITY-system-forge — Transcendent System Architecture

> **Version:** 2.0.0 | **Tier:** CORE | **Domain:** System Design & Engine Architecture
> **Absorbs:** system-design + performance-optimization + devops-cloud + clean-code
> **Activation:** "engine", "architecture", "Go", "Rust", "performance", "optimization", "system design", "daemon", "SOLID", "refactor"

---

## Layer 1: Engine Architecture (14 Engines)

### Engine Directory Structure

```
00_SYSTEM/engines/{engine_name}/
├── __init__.py          # Exports primary class, declares __version__
├── engine.py            # Core engine logic
├── config.py            # Engine-specific configuration (optional)
├── tests/
│   └── test_{engine}.py # Smoke tests (MANDATORY)
└── README.md            # Engine documentation (optional)
```

### Engine Registration Pattern

```python
# 00_SYSTEM/engines/myengine/__init__.py
"""MyEngine — brief description of purpose."""
__version__ = "1.0.0"
from .engine import MyEngine  # lazy import, NO side effects at module level
```

### CRITICAL: No Stdout Clobbering (35 files fixed in cf1f4fad8)

Module-level stdout replacement corrupts ALL importers — MCP servers, test harnesses, CLI runtime.

```python
# ❌ BANNED — module-level stdout replacement
import sys
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
sys.stdout.reconfigure(encoding='utf-8')

# ✅ SAFE — inside __main__ guard with try/except
if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, OSError):
        pass  # not a real terminal
```

### No Module-Level Side Effects

Engine modules must be safe to import without triggering I/O, connections, or processes.

```python
# ❌ WRONG — DB connection fires at import time
class Engine:
    conn = sqlite3.connect("litigation_context.db")

# ✅ CORRECT — lazy initialization via property
class Engine:
    def __init__(self):
        self._conn = None

    @property
    def conn(self):
        if self._conn is None:
            self._conn = get_db("litigation_context")
        return self._conn
```

### Import from shared Module (MANDATORY)

```python
from shared import get_db, sanitize_fts5, config, get_db_path

# Never import sqlite3 directly for DB connections
# get_db() handles: PRAGMAs, WAL mode, busy_timeout, filesystem-aware journal mode
```

### Smoke Test Requirements (Every Engine)

```python
# tests/test_myengine.py — MANDATORY minimum
import importlib

def test_engine_import():
    """Module imports without stdout corruption or missing deps."""
    mod = importlib.import_module("engines.myengine")
    assert hasattr(mod, "MyEngine")
    assert hasattr(mod, "__version__")

def test_engine_instantiate():
    """Primary class instantiates without crashing."""
    from engines.myengine import MyEngine
    engine = MyEngine()  # may use mock config
    assert engine is not None

def test_engine_basic_operation():
    """One representative operation returns expected type."""
    from engines.myengine import MyEngine
    engine = MyEngine()
    result = engine.health_check()
    assert isinstance(result, dict)
```

### Engine Inventory (14 Active)

| Engine | Backend | Purpose | Hot Path |
|--------|---------|---------|----------|
| nexus | Python + FTS5 | Cross-table evidence fusion | ✅ |
| chimera | Python | Multi-source evidence blending | ✅ |
| chronos | Python | Timeline construction | ✅ |
| cerberus | Python | Filing validation | ✅ |
| filing_engine | Python | Filing pipeline F1-F10 | ✅ |
| intake | Python | Document intake, PDF processing | ⚠️ |
| rebuttal | Python | Argument rebuttal generation | ⚠️ |
| narrative | Python | Court-ready Statement of Facts | ⚠️ |
| delta999 | Python | 8 specialized litigation agents | ⚠️ |
| analytics | DuckDB | 10-100× analytical queries | ✅ |
| semantic | LanceDB + transformers | Vector similarity search | ✅ |
| search | tantivy + hybrid | Sub-ms keyword + semantic fusion | ✅ |
| typst | Typst | Court-formatted PDF generation | ⚠️ |
| ingest | Go | 8-worker goroutine file processing | ✅ |

---

## Layer 2: Go Concurrent Systems (Ingest Engine)

### 8-Worker Goroutine Pipeline

```go
// Simplified architecture of the Go ingest engine
func main() {
    files := make(chan string, 100)    // buffered channel
    results := make(chan Result, 100)

    // Spawn 8 worker goroutines
    var wg sync.WaitGroup
    for i := 0; i < 8; i++ {
        wg.Add(1)
        go func(id int) {
            defer wg.Done()
            for path := range files {
                result, err := processFile(path)
                if err != nil {
                    log.Printf("worker %d: error processing %s: %v", id, path, err)
                    continue  // skip, don't crash
                }
                results <- result
            }
        }(i)
    }

    // Feed files from directory scan
    go func() {
        walkDir(rootPath, files)
        close(files)
    }()

    // Collect results
    go func() {
        wg.Wait()
        close(results)
    }()

    // Write to SQLite (single writer, avoids lock contention)
    for r := range results {
        insertToDB(r)
    }
}
```

### Error Handling with Error Groups

```go
import "golang.org/x/sync/errgroup"

g, ctx := errgroup.WithContext(context.Background())
g.SetLimit(8)  // max 8 concurrent goroutines

for _, file := range files {
    file := file  // capture loop variable
    g.Go(func() error {
        select {
        case <-ctx.Done():
            return ctx.Err()
        default:
            return processFile(file)
        }
    })
}

if err := g.Wait(); err != nil {
    log.Fatal("pipeline failed:", err)
}
```

### Cross-Language Integration (Go → SQLite → Python)

```
Go ingest engine (8 workers)
    ↓ writes to SQLite (WAL mode, single writer)
    ↓
litigation_context.db
    ↓ read by Python engines (WAL allows concurrent readers)
    ↓
Python analysis/search/filing engines
```

### When to Use Go vs Rust vs Python

| Criteria | Go | Rust | Python |
|----------|-----|------|--------|
| Concurrent I/O (file processing) | ✅ Best | ⚠️ More complex | ❌ GIL limits |
| CPU-bound CLI tools | ⚠️ Good | ✅ Best (zero-cost abstractions) | ❌ Too slow |
| ML/AI inference | ❌ Limited ecosystem | ❌ Limited ecosystem | ✅ PyTorch, transformers |
| Rapid prototyping | ⚠️ Verbose | ❌ Steep learning curve | ✅ Fastest iteration |
| Database orchestration | ⚠️ OK | ❌ Overkill | ✅ Best SQLite bindings |
| Full-text search engine | ⚠️ OK | ✅ tantivy | ⚠️ Bindings to Rust |
| Build time | ✅ ~2s | ❌ ~30s+ | ✅ None (interpreted) |

---

## Layer 3: Rust CLI Tools

### Installed Toolchain

| Tool | Version | Purpose | Speed vs Legacy |
|------|---------|---------|-----------------|
| fd | 10.4.2 | File finding | 5× faster than find/dir |
| bat | 0.26.1 | Syntax-highlighted viewing | Replaces cat/type |
| dust | 1.2.4 | Disk space analysis | Visual, fast |
| hyperfine | 1.20.0 | CLI benchmarking | Accurate timing |
| tokei | 12.1.2 | Code statistics | Fast LOC counting |
| tantivy | latest | Full-text search (BM25) | Sub-ms queries |
| rg (ripgrep) | latest | Text search | 5-10× faster than grep |

### fd Usage Patterns (File Discovery)

```bash
# Find all PDFs across all drives (5× faster than Get-ChildItem)
fd -e pdf -a . C:\ D:\ I:\

# Find Python files modified in last 7 days
fd -e py --changed-within 7d . 00_SYSTEM/

# Find files matching pattern, exclude archives
fd -e md "FILING|MOTION" 05_FILINGS/ --exclude 11_ARCHIVES
```

### tantivy Full-Text Search (Sub-ms BM25)

```python
# Python bindings to tantivy (Rust FTS engine)
import tantivy

schema = tantivy.SchemaBuilder()
schema.add_text_field("title", stored=True)
schema.add_text_field("body", stored=True)
index = tantivy.Index(schema.build())

# Sub-ms query on indexed corpus
searcher = index.searcher()
query = index.parse_query("parental alienation ex parte", ["title", "body"])
results = searcher.search(query, limit=10)
```

---

## Layer 4: NEXUS Daemon Architecture

### Architecture Overview

```
Copilot CLI Session
  └── extension.mjs (Node.js — spawns daemon ONCE)
       └── nexus_daemon.py (PERSISTENT Python subprocess)
            ├── SQLite WAL connection (warm, always open)
            ├── DuckDB (analytical queries, ATTACH'd read-only)
            ├── LanceDB (semantic search, 75K vectors)
            └── JSON-RPC over stdin/stdout (line-delimited)
```

### Line-Delimited JSON-RPC Protocol

```json
// Request (one line)
{"id": "abc-123", "action": "query", "sql": "SELECT COUNT(*) FROM evidence_quotes", "params": []}

// Response (one line)
{"id": "abc-123", "ok": true, "rows": [[175432]], "columns": ["count"], "count": 1}

// Error response
{"id": "abc-123", "ok": false, "error": "no such table: nonexistent"}
```

### Connection Pool (Lazy Singleton)

```python
class ConnectionPool:
    """Lazy singleton connection pool for warm DB access."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._sqlite = None
            cls._instance._duckdb = None
            cls._instance._lancedb = None
        return cls._instance

    @property
    def sqlite(self):
        if self._sqlite is None:
            self._sqlite = sqlite3.connect("litigation_context.db")
            self._sqlite.execute("PRAGMA busy_timeout = 60000")
            self._sqlite.execute("PRAGMA journal_mode = WAL")
            self._sqlite.execute("PRAGMA cache_size = -32000")
            self._sqlite.execute("PRAGMA mmap_size = 268435456")
            self._sqlite.execute("PRAGMA temp_store = MEMORY")
            self._sqlite.execute("PRAGMA synchronous = NORMAL")
        return self._sqlite
```

### Circuit Breaker Pattern

States: CLOSED → OPEN (after N failures) → HALF_OPEN (after timeout) → CLOSED (on success).
Use on all external I/O: DB connections, daemon calls, file operations on USB drives.
Track `failures`, `threshold=5`, `recovery_timeout=30s`, `last_failure_time`.

---

## Layer 5: Performance Optimization

### Profiling Methodology

```python
# Quick profile with cProfile
import cProfile
cProfile.run('engine.process(data)', sort='cumulative')

# Line-level profiling for hot functions
# pip install line_profiler
# kernprof -l -v script.py
```

### Memory Optimization Principles

```python
# ✅ Streaming (O(1) memory)
def process_large_file(path):
    with open(path, 'r') as f:
        for line in f:  # one line at a time
            yield parse(line)

# ❌ Loading (O(n) memory — crashes on GB files)
def process_large_file(path):
    with open(path, 'r') as f:
        data = f.read()  # entire file in memory
    return parse(data)

# ✅ Generator pipeline (composable, O(1))
evidence = (parse(line) for line in open("evidence.csv"))
filtered = (e for e in evidence if e["lane"] == "A")
batched = list(itertools.islice(filtered, 1000))
```

### I/O Optimization

```python
# ✅ Batch DB operations
conn.executemany("INSERT INTO t VALUES (?, ?)", batch_of_1000)
conn.commit()

# ✅ mmap for large file reads (NVMe SSD optimal)
import mmap
with open(path, 'r') as f:
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    content = mm[offset:offset+size]
```

### Hardware Constraints

| Component | Spec | Optimization Implication |
|-----------|------|------------------------|
| CPU | AMD Ryzen 3 3200G (4C/4T) | Max 4 parallel Python processes |
| RAM | 24 GB | Keep DB cache < 2 GB total |
| GPU | Vega 8 (2 GB VRAM, integrated) | CPU-only inference (no CUDA) |
| SSD | 238 GB NVMe (C:\) | mmap safe, WAL fast |
| USB drives | 58-466 GB USB 2.0/3.0 | 10-100× slower I/O than SSD |

---

## Layer 6: Clean Code & SOLID Principles

### SOLID in LitigationOS

| Principle | Application | Example |
|-----------|-------------|---------|
| **S**ingle Responsibility | Each engine does ONE thing | nexus = fusion, chronos = timeline |
| **O**pen/Closed | Engines extensible via config, not code changes | New MEEK lane = config update |
| **L**iskov Substitution | All engines implement common interface | `engine.health_check()` contract |
| **I**nterface Segregation | Engines expose minimal API | Filing engine doesn't expose search |
| **D**ependency Inversion | Engines depend on shared abstractions | `get_db()` not `sqlite3.connect()` |

### GoF Patterns in Use

| Pattern | Where Used | Purpose |
|---------|-----------|---------|
| **Singleton** | ConnectionPool, CircuitBreaker | Single shared resource |
| **Factory** | Engine instantiation via shared module | `get_analytics_engine()` |
| **Strategy** | MEEK lane routing | Swappable classification logic |
| **Observer** | File watchers (watchdog) | React to filesystem changes |
| **Template Method** | Engine base class | Shared lifecycle, custom logic |
| **Chain of Responsibility** | FTS5 → LIKE fallback | Cascading search strategies |

### Code Smell Detection Checklist

| Smell | Detection | Fix |
|-------|-----------|-----|
| God class (> 500 lines) | `tokei` line count | Split into focused modules |
| Long parameter list (> 5) | Manual review | Introduce parameter object |
| Duplicate code | `rg` pattern search | Extract shared function |
| Dead code | `vulture` or manual | Remove (archive to 11_ARCHIVES/) |
| Magic numbers | `rg '\b\d{3,}\b'` | Named constants |
| Hardcoded paths | `rg 'C:\\\\Users'` | `shared.config` centralization |

---

## Anti-Patterns (VIOLATIONS = IMMEDIATE FAILURE)

| # | Anti-Pattern | Correct Pattern |
|---|-------------|-----------------|
| 1 | Stdout clobbering at module level | `__main__` guard with try/except |
| 2 | DB connection at import time | Lazy initialization via property |
| 3 | Missing `__version__` in engine `__init__.py` | Always declare version |
| 4 | No smoke tests for engine | 3 minimum tests: import, instantiate, basic op |
| 5 | Hardcoded DB paths in engine code | `shared.get_db()` or `shared.config` |
| 6 | `import sqlite3` directly | `from shared import get_db` |
| 7 | Single-threaded file processing for bulk work | Go ingest engine (8-worker goroutines) |
| 8 | Loading entire file into memory | Streaming generators, mmap |
| 9 | Sequential operations that can be parallelized | Goroutines (Go) or task agents (Python) |
| 10 | Missing error handling in daemon handlers | try/except with structured error response |
| 11 | No circuit breaker for external dependencies | CircuitBreaker class on all I/O |
| 12 | God class engines (> 500 lines) | Split into focused modules |
| 13 | `pass` / `TODO` / `raise NotImplementedError` in production | Every function fully operational |
| 14 | `Get-ChildItem -Recurse` for file scanning | `fd` (Rust, 5× faster) |
| 15 | Manual JSON serialization | `orjson` (10× faster, Rust-backed) |

## Performance Budgets

| Operation | Target | Degraded | Unacceptable |
|-----------|--------|----------|--------------|
| Engine import time | < 50 ms | < 200 ms | > 500 ms |
| Engine instantiation | < 100 ms | < 500 ms | > 2 s |
| Daemon startup (cold) | < 3 s | < 5 s | > 10 s |
| Daemon action (warm) | < 5 ms | < 50 ms | > 200 ms |
| Go file processing (per file) | < 1 ms | < 5 ms | > 20 ms |
| fd directory scan (10K files) | < 500 ms | < 2 s | > 5 s |
| tantivy search (index hit) | < 1 ms | < 5 ms | > 20 ms |
| Python import chain (all engines) | < 2 s | < 5 s | > 10 s |

## Decision Matrix: Architecture Choices

| Decision | Option A | Option B | Choose |
|----------|----------|----------|--------|
| New CLI tool | Python script | Rust binary | Rust if CPU-bound; Python if DB/ML |
| Bulk file processing | Python threads | Go goroutines | Go (GIL-free, channel-safe) |
| Full-text search | SQLite FTS5 | tantivy (Rust) | tantivy for hot path; FTS5 for DB-integrated |
| Court PDF generation | python-docx | Typst | Typst (instant compile, court-ready) |
| JSON handling | json stdlib | orjson | orjson always (10× faster, Rust) |
| Config format | .env / .ini | JSONC | JSONC (litigationos.config.jsonc) |
| Error reporting | print/logging | Structured JSON | Structured JSON in daemon; logging in scripts |
| DB access | Direct sqlite3 | shared.get_db() | shared.get_db() always (Rule 30) |

---

*END OF SINGULARITY-system-forge v2.0.0 — Go · Rust · NEXUS · SOLID · 14 Engines · ZERO Bloat*

---
name: SINGULARITY-code-mastery
description: "Transcendent polyglot code mastery for LitigationOS. ABSORBS: typescript-python, fullstack, backend, testing. Use when: Python engines/ML, Go concurrent ingest, Rust CLI tools, TypeScript extensions, DuckDB analytics, LanceDB vectors, sentence-transformers, Ollama local LLM, pytest testing, 142+ eval tests, clean code, SOLID, design patterns, cross-language integration, shared module usage."
---

# SINGULARITY-code-mastery — Transcendent Polyglot Engineering

> **Absorbs:** typescript-python, fullstack, backend, testing
> **Tier:** TOOLS | **Domain:** Polyglot Development, Testing, Clean Code
> **Stack:** Python 3.12 · Go 1.26.1 · Rust 1.94.1 · TypeScript/Node.js 25.8.1

---

## 1. Python Best Practices (LitigationOS Core)

### Shared Module Usage (MANDATORY)
```python
# CORRECT — centralized, portable
from shared import get_db, sanitize_fts5, config, get_db_path

conn = get_db("litigation_context")        # Auto-PRAGMAs, WAL, busy_timeout
path = get_db_path("authority_master")     # Centralized path resolution
safe_q = sanitize_fts5(user_input)         # FTS5 injection prevention

# WRONG — hardcoded paths (Rule 30 violation)
conn = sqlite3.connect(r"C:\Users\andre\LitigationOS\litigation_context.db")
```

### Lazy Initialization (No Module-Level Side Effects)
```python
# CORRECT — lazy connection
class Engine:
    def __init__(self):
        self._conn = None

    @property
    def conn(self):
        if self._conn is None:
            self._conn = get_db("litigation_context")
        return self._conn

# WRONG — connects at import time
class Engine:
    conn = sqlite3.connect("litigation_context.db")  # fires on import!
```

### No Stdout Clobbering (35 files fixed in cf1f4fad8)
```python
# BANNED at module level — corrupts MCP/extension pipes
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8')
sys.stdout.reconfigure(encoding='utf-8')

# SAFE — inside __main__ guard only
if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, OSError):
        pass
```

### FTS5 Safety Protocol (Rule 15)
```python
import re
import sqlite3

def safe_fts5_search(conn: sqlite3.Connection, table: str,
                     fts_table: str, query: str, limit: int = 25) -> list:
    """FTS5 search with sanitization and LIKE fallback."""
    sanitized = re.sub(r'[^\w\s*"]', ' ', query).strip()
    if not sanitized:
        return []
    try:
        return conn.execute(f"""
            SELECT *, snippet({fts_table}, 0, '<b>', '</b>', '...', 32) AS snip
            FROM {fts_table}
            WHERE {fts_table} MATCH ?
            ORDER BY rank LIMIT ?
        """, (sanitized, limit)).fetchall()
    except sqlite3.OperationalError:
        # FTS5 crash fallback — parameterized LIKE
        return conn.execute(f"""
            SELECT * FROM {table}
            WHERE quote_text LIKE '%' || ? || '%'
            LIMIT ?
        """, (query, limit)).fetchall()
```

### Database Connection Template
```python
import sqlite3

def get_connection(db_path: str) -> sqlite3.Connection:
    """Standard connection with mandatory PRAGMAs."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA cache_size = -32000")    # 32 MB
    conn.execute("PRAGMA temp_store = MEMORY")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.row_factory = sqlite3.Row
    return conn
```

---

## 2. Go Patterns (Concurrent Ingest Engine)

### Goroutine Worker Pool
```go
package main

import (
    "crypto/sha256"
    "encoding/hex"
    "io"
    "os"
    "sync"
)

func hashFile(path string) (string, error) {
    f, err := os.Open(path)
    if err != nil {
        return "", err
    }
    defer f.Close()
    h := sha256.New()
    if _, err := io.Copy(h, f); err != nil {
        return "", err
    }
    return hex.EncodeToString(h.Sum(nil)), nil
}

func processWorker(jobs <-chan string, results chan<- Result, wg *sync.WaitGroup) {
    defer wg.Done()
    for path := range jobs {
        hash, err := hashFile(path)
        info, _ := os.Stat(path)
        results <- Result{
            Path: path,
            Hash: hash,
            Size: info.Size(),
            Err:  err,
        }
    }
}
```

### Error Handling (Go Style)
```go
// CORRECT — explicit error handling, no panics in production
result, err := processFile(path)
if err != nil {
    log.Printf("WARN: skipping %s: %v", path, err)
    errorCount++
    continue
}

// WRONG — panic in library code
if err != nil {
    panic(err)  // Never in production ingest pipeline
}
```

---

## 3. Rust CLI Tool Patterns

### fd Integration (File Discovery)
```rust
// fd is pre-built — we consume it via subprocess
// Key flags for LitigationOS evidence hunting:
// fd -e pdf -t f --no-ignore . C:\       # All PDFs on C:
// fd -e pdf -S +1M "watson" I:\          # Large Watson PDFs on I:
// fd -t f --changed-within 7d .          # Recent files
```

### tantivy Integration (Full-Text Search)
```rust
use tantivy::{schema::*, Index, ReloadPolicy};
use tantivy::collector::TopDocs;
use tantivy::query::QueryParser;

fn create_evidence_index() -> tantivy::Result<Index> {
    let mut schema_builder = Schema::builder();
    schema_builder.add_text_field("content", TEXT | STORED);
    schema_builder.add_text_field("source", STRING | STORED);
    schema_builder.add_text_field("lane", STRING | STORED);
    schema_builder.add_u64_field("page", STORED);
    let schema = schema_builder.build();
    Index::create_in_dir("./tantivy_index", schema)
}
```

---

## 4. TypeScript Extension Development

### Extension Architecture (extension.mjs)
```javascript
// Copilot CLI Extension — manages NEXUS daemon lifecycle
import { spawn } from 'child_process';

let daemon = null;
const pendingRequests = new Map();

function startDaemon() {
    daemon = spawn('python', ['-I', 'nexus_daemon.py'], {
        stdio: ['pipe', 'pipe', 'pipe'],
        env: { ...process.env, PYTHONUTF8: '1' }
    });

    daemon.stdout.on('data', (chunk) => {
        const lines = chunk.toString().split('\n').filter(Boolean);
        for (const line of lines) {
            try {
                const msg = JSON.parse(line);
                const resolver = pendingRequests.get(msg.id);
                if (resolver) {
                    resolver(msg);
                    pendingRequests.delete(msg.id);
                }
            } catch (e) { /* skip non-JSON lines */ }
        }
    });
}

async function callDaemon(payload) {
    const id = crypto.randomUUID();
    payload.id = id;
    return new Promise((resolve, reject) => {
        pendingRequests.set(id, resolve);
        daemon.stdin.write(JSON.stringify(payload) + '\n');
        setTimeout(() => {
            if (pendingRequests.has(id)) {
                pendingRequests.delete(id);
                reject(new Error('Daemon timeout'));
            }
        }, 30000);
    });
}
```

### Tool Registration Pattern
```javascript
export default {
    name: "singularity",
    tools: [
        {
            name: "query_litigation_db",
            description: "SQL query against litigation_context.db",
            parameters: {
                sql: { type: "string", description: "SQL query", required: true },
                params: { type: "array", description: "Bind parameters" },
                max_rows: { type: "number", description: "Max rows (default 50)" }
            },
            async handler(params) {
                const result = await callDaemon({
                    action: "query", sql: params.sql,
                    params: params.params || [], max_rows: params.max_rows || 50
                });
                return formatResult(result);
            }
        }
    ]
};
```

---

## 5. Testing Strategy

### pytest Configuration
```python
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "-q --tb=short"
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks integration tests requiring DB",
    "smoke: marks engine smoke tests",
]
```

### Engine Smoke Test Template
```python
"""Smoke test template — every engine MUST have at least one."""
import importlib
import pytest

ENGINE_NAME = "nexus"
EXPECTED_CLASS = "NexusEngine"

def test_engine_import():
    """Engine module imports without stdout corruption or missing deps."""
    mod = importlib.import_module(f"engines.{ENGINE_NAME}")
    assert hasattr(mod, EXPECTED_CLASS)

def test_engine_instantiate():
    """Primary class instantiates without crashing."""
    mod = importlib.import_module(f"engines.{ENGINE_NAME}")
    cls = getattr(mod, EXPECTED_CLASS)
    engine = cls()
    assert engine is not None

@pytest.mark.integration
def test_engine_basic_query():
    """One representative operation returns expected type."""
    mod = importlib.import_module(f"engines.{ENGINE_NAME}")
    cls = getattr(mod, EXPECTED_CLASS)
    engine = cls()
    result = engine.search("test query")
    assert isinstance(result, (list, dict))
```

### Test Patterns for LitigationOS
```python
# DB test fixture with WAL mode
@pytest.fixture
def db_conn(tmp_path):
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")
    yield conn
    conn.close()

# FTS5 test
def test_fts5_search(db_conn):
    db_conn.execute("CREATE VIRTUAL TABLE test_fts USING fts5(content)")
    db_conn.execute("INSERT INTO test_fts VALUES (?)", ("custody modification",))
    rows = db_conn.execute(
        "SELECT * FROM test_fts WHERE test_fts MATCH ?", ("custody",)
    ).fetchall()
    assert len(rows) == 1

# Anti-hallucination test
def test_no_banned_strings():
    from pathlib import Path
    BANNED = ["Jane Berry", "Patricia Berry", "91% alienation"]
    for md in Path("05_FILINGS").rglob("*.md"):
        content = md.read_text(encoding='utf-8', errors='replace')
        for banned in BANNED:
            assert banned.lower() not in content.lower(), \
                f"HALLUCINATION: '{banned}' found in {md}"
```

---

## 6. Cross-Language Integration

### Python ↔ Go
```python
# Python calls Go binary for ingest
import subprocess
result = subprocess.run(
    ["go", "run", "00_SYSTEM/engines/ingest/main.go", "--workers=8", "--dir=I:\\"],
    capture_output=True, text=True, timeout=600
)
```

### Python ↔ Rust
```python
# Python calls fd (Rust) for file discovery
files = subprocess.run(
    ["fd", "-e", "pdf", "-t", "f", ".", "I:\\"],
    capture_output=True, text=True
).stdout.strip().split('\n')
```

### TypeScript ↔ Python (NEXUS Daemon)
```
extension.mjs → stdin JSON-RPC → nexus_daemon.py → stdout JSON response
```

---

## 7. SOLID Principles Applied to LitigationOS

| Principle | Application |
|-----------|-------------|
| **S** — Single Responsibility | Each engine handles ONE domain (nexus=fusion, chronos=timeline) |
| **O** — Open/Closed | Engines extend via plugins, not modification of core |
| **L** — Liskov Substitution | All search engines implement same `search(query) → results` interface |
| **I** — Interface Segregation | Separate interfaces for read-only vs read-write DB operations |
| **D** — Dependency Inversion | Engines depend on `shared.get_db()` abstraction, not sqlite3 directly |

---

## 8. Key Rules & Constraints

| Rule | Enforcement |
|------|-------------|
| No stubs | `pass`, `TODO`, `raise NotImplementedError` = FORBIDDEN in committed code |
| Shared module | All DB access through `shared.get_db()` — never raw sqlite3.connect |
| No stdout clobber | Module-level `sys.stdout` changes = BANNED |
| Lazy initialization | No DB connections, file I/O, or network at import time |
| Shadow modules | 22 files in repo root shadow stdlib — never CWD to repo root |
| Script location | All inline Python → `D:\LitigationOS_tmp\` (Rule 22) |
| Error = upgrade | On error: identify root cause → decompose → fix. Never reduce scope |
| Test coverage | Every engine must have at least one smoke test |

---
name: SINGULARITY-debug-ops
description: "Transcendent debugging and quality assurance for LitigationOS. Use when: systematic debugging, error triage, test creation, traceback analysis, regression hunting, flaky test diagnosis, performance profiling, code review, QA gates, smoke tests, integration tests, engine validation, FTS5 crash recovery, SQLITE_BUSY diagnosis, EAGAIN pipe debugging, shadow module conflicts, encoding crashes."
version: "1.0.0"
forged_from:
  - debugging-mastery
  - testing-quality
  - code-review
tier: "SPEC"
domain: "Systematic debugging, QA, testing, error triage, regression prevention"
triggers:
  - debug
  - error
  - test
  - traceback
  - fix
  - broken
  - failing
  - crash
  - regression
  - flaky
  - quality
  - QA
  - smoke test
  - coverage
cross_links:
  - SINGULARITY-code-mastery
  - SINGULARITY-data-dominion
  - SINGULARITY-system-forge
---

# SINGULARITY-debug-ops — Transcendent Debugging & Quality Assurance

> Every bug is an upgrade opportunity. Every test is a shield. Every crash is intelligence.

## 1. Systematic Debugging Protocol (5-Layer Root Cause Analysis)

### Layer 1: Observe — Gather Raw Evidence
```python
# NEVER guess. Read the FULL traceback first.
# Extract: exception type, message, file, line, call stack depth
import traceback

def capture_debug_context(exc: Exception) -> dict:
    """Capture complete debug context from an exception."""
    tb = traceback.extract_tb(exc.__traceback__)
    return {
        'exception_type': type(exc).__name__,
        'message': str(exc),
        'file': tb[-1].filename if tb else 'unknown',
        'line': tb[-1].lineno if tb else 0,
        'function': tb[-1].name if tb else 'unknown',
        'stack_depth': len(tb),
        'full_traceback': traceback.format_exception(type(exc), exc, exc.__traceback__),
        'call_chain': [f"{frame.filename}:{frame.lineno} in {frame.name}" for frame in tb],
    }
```

### Layer 2: Reproduce — Isolate the Trigger
```python
# Minimum Reproducible Example (MRE) construction:
# 1. Strip everything not needed to trigger the bug
# 2. Replace DB with in-memory SQLite
# 3. Replace file I/O with StringIO
# 4. Mock external dependencies
# 5. Run in isolation (python -I flag to avoid shadow modules)

def create_mre(failing_function, *args, **kwargs):
    """Attempt to reproduce a failure in isolation."""
    import io, sqlite3, unittest.mock as mock

    # Isolated DB
    db = sqlite3.connect(":memory:")
    db.execute("PRAGMA journal_mode=WAL")

    # Capture stdout/stderr
    captured = io.StringIO()

    try:
        with mock.patch('sys.stdout', captured):
            result = failing_function(*args, **kwargs)
        return {'reproduced': False, 'result': result}
    except Exception as e:
        return {'reproduced': True, 'error': capture_debug_context(e)}
```

### Layer 3: Hypothesize — Pattern-Match Known Failure Modes
```
LitigationOS Known Failure Taxonomy (22 patterns):

DATABASE:
  DB-001: SQLITE_BUSY          → Missing PRAGMA busy_timeout (Rule 18)
  DB-002: FTS5 crash            → Unsanitized query chars (Rule 15)
  DB-003: Column not found      → Schema mismatch, no PRAGMA table_info (Rule 16)
  DB-004: DB locked             → WAL checkpoint needed or concurrent writes
  DB-005: No such table         → Pipeline-created vs DDL-defined schema gap

ENCODING:
  ENC-001: cp1252 crash         → PowerShell stdout encoding (why Rule 22 exists)
  ENC-002: UnicodeDecodeError   → File opened without encoding='utf-8'
  ENC-003: orjson bytes vs str  → orjson returns bytes, not str

FILE SYSTEM:
  FS-001: Shadow module import  → 22 hijacking files at repo root (json.py, typing.py)
  FS-002: Path too long         → Windows 260-char limit
  FS-003: exFAT WAL failure     → J:\ drive has no file locking (Rule: DELETE mode)
  FS-004: Permission denied     → File locked by another process

PIPE/SHELL:
  PIPE-001: write EAGAIN        → Too many concurrent shells (max 2)
  PIPE-002: Invalid shell ID    → Shell pool exhausted
  PIPE-003: Truncated output    → Pipe buffer overflow (64KB limit)

ENGINE:
  ENG-001: stdout clobbering    → Module-level sys.stdout replacement
  ENG-002: Import side effects  → DB connections at import time
  ENG-003: Missing __init__.py  → Engine directory not a Python package
  ENG-004: Circular import      → Engine A imports Engine B imports Engine A

AGENT:
  AGT-001: git index.lock       → Background agent holding lock
  AGT-002: 429 rate limit       → >2 concurrent agents
  AGT-003: Context compaction   → Agent results lost before read
```

### Layer 4: Test — Verify the Hypothesis
```python
# Binary search isolation: disable half the code, does bug persist?
# If yes: bug is in remaining half. Recurse.
# If no: bug is in disabled half. Recurse.

def binary_search_debug(code_blocks: list, test_function) -> int:
    """Find the smallest code block that triggers the failure."""
    if len(code_blocks) <= 1:
        return 0

    mid = len(code_blocks) // 2
    # Test first half
    try:
        test_function(code_blocks[:mid])
        # First half passes, bug in second half
        return mid + binary_search_debug(code_blocks[mid:], test_function)
    except Exception:
        # First half fails, bug in first half
        return binary_search_debug(code_blocks[:mid], test_function)
```

### Layer 5: Fix — Surgical Repair + Regression Shield
```python
# Every fix MUST include:
# 1. The fix itself (minimal, surgical)
# 2. A test that FAILS without the fix and PASSES with it
# 3. A comment explaining WHY (not what) the fix does
# 4. Verification the fix doesn't break existing tests

def verify_fix(fix_function, test_suite):
    """Verify a fix passes all tests and doesn't regress."""
    import unittest
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(test_suite)
    return {
        'tests_run': result.testsRun,
        'failures': len(result.failures),
        'errors': len(result.errors),
        'passed': result.wasSuccessful(),
    }
```

## 2. LitigationOS-Specific Debug Recipes

### 2.1 FTS5 Crash Recovery
```python
import re, sqlite3

def debug_fts5(db_path: str, table: str, query: str):
    """Debug and recover from FTS5 failures."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout=60000")

    # Step 1: Sanitize query (Rule 15)
    sanitized = re.sub(r'[^\w\s*"]', ' ', query).strip()

    # Step 2: Check FTS5 table health
    try:
        conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
    except sqlite3.OperationalError as e:
        if 'no such table' in str(e):
            return {'status': 'MISSING_TABLE', 'fix': f'Rebuild {table} FTS5 index'}
        raise

    # Step 3: Try MATCH with sanitized query
    try:
        rows = conn.execute(
            f"SELECT rowid, snippet({table}, 0, '>>>', '<<<', '...', 40) "
            f"FROM {table} WHERE {table} MATCH ? LIMIT 10",
            (sanitized,)
        ).fetchall()
        return {'status': 'OK', 'rows': len(rows)}
    except sqlite3.OperationalError as e:
        # Step 4: LIKE fallback
        like_query = f"%{sanitized.split()[0]}%"
        # Get first text column
        cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
        text_col = next((c[1] for c in cols if c[2] == 'TEXT'), cols[0][1])
        rows = conn.execute(
            f"SELECT rowid, substr({text_col}, 1, 200) "
            f"FROM {table} WHERE {text_col} LIKE ? LIMIT 10",
            (like_query,)
        ).fetchall()
        return {'status': 'FTS5_FAILED_LIKE_FALLBACK', 'error': str(e), 'rows': len(rows)}

    # Step 5: If corrupt, rebuild
    # conn.execute(f"INSERT INTO {table}({table}) VALUES('rebuild')")
```

### 2.2 SQLITE_BUSY Diagnosis
```python
def diagnose_busy(db_path: str) -> dict:
    """Diagnose SQLITE_BUSY errors."""
    import os, sqlite3

    result = {'db_path': db_path}

    # Check WAL file
    wal = db_path + '-wal'
    shm = db_path + '-shm'
    result['wal_exists'] = os.path.exists(wal)
    result['wal_size'] = os.path.getsize(wal) if result['wal_exists'] else 0
    result['shm_exists'] = os.path.exists(shm)

    # Large WAL = checkpoint needed
    if result['wal_size'] > 50 * 1024 * 1024:  # 50MB
        result['recommendation'] = 'WAL checkpoint needed (>50MB)'

    # Try connection with escalating timeouts
    for timeout in [1000, 5000, 30000, 60000]:
        try:
            conn = sqlite3.connect(db_path, timeout=timeout/1000)
            conn.execute(f"PRAGMA busy_timeout={timeout}")
            conn.execute("SELECT 1").fetchone()
            result['accessible_at_timeout'] = timeout
            conn.close()
            break
        except sqlite3.OperationalError:
            continue

    return result
```

### 2.3 Shadow Module Detection
```python
def audit_shadow_modules(repo_root: str) -> list:
    """Find files at repo root that shadow Python stdlib/packages."""
    import os, sys

    KNOWN_SHADOWS = {
        'json.py', 'typing.py', 'tokenize.py', 'numpy.py', 'pandas.py',
        'ast.py', 'io.py', 'os.py', 'sys.py', 'math.py', 'time.py',
        'collections.py', 'logging.py', 'sqlite3.py', 'csv.py',
        'pathlib.py', 'hashlib.py', 'socket.py', 're.py', 'abc.py'
    }

    shadows = []
    for f in os.listdir(repo_root):
        if f.endswith('.py') and f in KNOWN_SHADOWS:
            shadows.append({
                'file': f,
                'path': os.path.join(repo_root, f),
                'risk': 'CRITICAL',
                'fix': 'Use python -I flag or set CWD away from repo root'
            })

    # Also check for __init__.py that could create package conflicts
    for d in os.listdir(repo_root):
        dp = os.path.join(repo_root, d)
        if os.path.isdir(dp) and d in sys.stdlib_module_names:
            init = os.path.join(dp, '__init__.py')
            if os.path.exists(init):
                shadows.append({
                    'file': d + '/',
                    'path': dp,
                    'risk': 'HIGH',
                    'fix': 'Rename directory to avoid stdlib conflict'
                })

    return shadows
```

### 2.4 EAGAIN / Pipe Buffer Debugging
```
Diagnosis Flow:
1. Check active shell count: list_powershell → count > 2 = CAUSE
2. Check for unbounded output: any command without | Select-Object -First N?
3. Check for nested shells: shell spawning another shell?
4. Check for detached orphans: processes still alive from prior sessions

Recovery:
1. stop_powershell on ALL shells
2. Wait 5 seconds for pipe buffer drain
3. Create ONE new named shell
4. If still failing → switch to exec_python/exec_command (zero pipe risk)
```

## 3. Test Architecture for LitigationOS

### 3.1 Smoke Test Template (Every Engine)
```python
"""Smoke test for {ENGINE_NAME} engine."""
import importlib
import pytest

ENGINE = "{engine_module_name}"
PRIMARY_CLASS = "{PrimaryClassName}"

def test_import():
    """Engine imports without stdout corruption or missing deps."""
    mod = importlib.import_module(ENGINE)
    assert mod is not None

def test_class_exists():
    """Primary class is defined."""
    mod = importlib.import_module(ENGINE)
    assert hasattr(mod, PRIMARY_CLASS), f"{PRIMARY_CLASS} not found in {ENGINE}"

def test_instantiate():
    """Primary class instantiates without crashing."""
    mod = importlib.import_module(ENGINE)
    cls = getattr(mod, PRIMARY_CLASS)
    # Use mock DB path if constructor requires it
    try:
        instance = cls()
    except TypeError:
        instance = cls(db_path=":memory:")
    assert instance is not None

def test_no_stdout_clobbering():
    """Import does NOT replace sys.stdout."""
    import sys
    original = sys.stdout
    importlib.import_module(ENGINE)
    assert sys.stdout is original, "Engine clobbered sys.stdout on import!"
```

### 3.2 Integration Test Patterns
```python
"""Integration test with real DB."""
import sqlite3, pytest, tempfile, os

@pytest.fixture
def test_db():
    """Create a minimal test database with required tables."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")

    # Create minimal schema
    conn.executescript("""
        CREATE TABLE evidence_quotes (
            id INTEGER PRIMARY KEY,
            quote_text TEXT,
            source_file TEXT,
            category TEXT,
            lane TEXT,
            relevance_score REAL DEFAULT 0.5,
            is_duplicate INTEGER DEFAULT 0
        );
        CREATE VIRTUAL TABLE evidence_fts USING fts5(
            quote_text, source_file, category,
            content=evidence_quotes, content_rowid=id
        );
        CREATE TABLE timeline_events (
            id INTEGER PRIMARY KEY,
            event_date TEXT,
            event_text TEXT,
            actor TEXT,
            lane TEXT
        );
    """)

    # Insert sample data
    conn.executemany(
        "INSERT INTO evidence_quotes (quote_text, source_file, category, lane) VALUES (?, ?, ?, ?)",
        [
            ("Emily denied parenting time", "appclose.pdf", "custody", "A"),
            ("McNeill issued ex parte order", "order_2025.pdf", "judicial", "E"),
            ("Albert admitted premeditation", "NS2505044.pdf", "custody", "A"),
        ]
    )
    conn.commit()
    conn.close()

    yield path
    os.unlink(path)


def test_fts5_round_trip(test_db):
    """FTS5 index returns correct results."""
    conn = sqlite3.connect(test_db)
    # Rebuild FTS5
    conn.execute("INSERT INTO evidence_fts(evidence_fts) VALUES('rebuild')")
    rows = conn.execute(
        "SELECT quote_text FROM evidence_fts WHERE evidence_fts MATCH 'parenting'"
    ).fetchall()
    assert len(rows) >= 1
    assert 'parenting' in rows[0][0].lower()
    conn.close()
```

### 3.3 QA Gate Automation
```python
def run_qa_gate(filing_path: str) -> dict:
    """Automated QA gate for court filings."""
    import re

    with open(filing_path, 'r', encoding='utf-8') as f:
        content = f.read()

    results = {'path': filing_path, 'gates': {}, 'passed': True}

    # Gate 1: No generic placeholders
    placeholders = re.findall(r'\[(?:ANDREW_REQUIRED|VERIFY|INSERT|TBD|TODO|PLACEHOLDER|ATTACH)[^\]]*\]', content)
    results['gates']['no_placeholders'] = len(placeholders) == 0
    if placeholders:
        results['passed'] = False
        results['placeholder_count'] = len(placeholders)

    # Gate 2: No hallucinated names
    BANNED = ['Jane Berry', 'Patricia Berry', 'P35878', '91% alienation',
              'Emily A. Watson', 'Lincoln David Watson', 'Ron Berry Esq',
              'Amy McNeill', 'Emily Ann Watson', 'Emily M. Watson']
    for term in BANNED:
        if term.lower() in content.lower():
            results['gates']['no_hallucinations'] = False
            results['passed'] = False
            break
    else:
        results['gates']['no_hallucinations'] = True

    # Gate 3: Correct year
    old_years = re.findall(r'\b202[0-5]\b', content)
    results['gates']['correct_year'] = len(old_years) == 0

    # Gate 4: Child name protection
    results['gates']['child_protected'] = 'lincoln' not in content.lower()

    # Gate 5: No AI artifacts
    AI_TERMS = ['LitigationOS', 'MANBEARPIG', 'EGCP', 'SINGULARITY', 'MEEK',
                'evidence_quotes', 'authority_chains', 'impeachment_matrix']
    for term in AI_TERMS:
        if term in content:
            results['gates']['no_ai_artifacts'] = False
            results['passed'] = False
            break
    else:
        results['gates']['no_ai_artifacts'] = True

    return results
```

## 4. Performance Profiling

### 4.1 Query Profiling
```python
import time, functools

def profile_query(func):
    """Decorator to profile DB query execution time."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        if elapsed > 1.0:
            import logging
            logging.warning(f"SLOW QUERY: {func.__name__} took {elapsed:.2f}s")
        return result
    return wrapper
```

### 4.2 Memory Profiling for Large Operations
```python
import os

def check_memory_pressure() -> dict:
    """Check current process memory usage."""
    import psutil
    proc = psutil.Process(os.getpid())
    mem = proc.memory_info()
    return {
        'rss_mb': mem.rss / (1024 * 1024),
        'vms_mb': mem.vms / (1024 * 1024),
        'warning': mem.rss > 500 * 1024 * 1024,  # >500MB
        'critical': mem.rss > 1024 * 1024 * 1024,  # >1GB
    }
```

## 5. Error Recovery Escalation Matrix

| Error | Level 1 (Automatic) | Level 2 (Agent) | Level 3 (User) |
|-------|---------------------|-----------------|----------------|
| FTS5 crash | LIKE fallback | Rebuild index | Manual inspect |
| SQLITE_BUSY | Retry 3× backoff | WAL checkpoint | Kill processes |
| Import error | Try alternate import | Check shadow mods | Install package |
| EAGAIN | Switch to exec_python | Stop all shells | Restart session |
| Test failure | Read traceback | Binary search | Review logic |
| Memory OOM | Streaming mode | Chunk processing | Increase limits |
| Encoding crash | PYTHONUTF8=1 | Explicit encoding | Check locale |
| Path not found | Search all drives | Check archives | Ask user |

## Anti-Patterns (MANDATORY)

1. **NEVER** say "it works on my machine" — reproduce in isolation first
2. **NEVER** fix a bug without adding a regression test
3. **NEVER** swallow exceptions silently (`except: pass` is FORBIDDEN)
4. **NEVER** debug by print-spamming — use structured logging
5. **NEVER** skip the hypothesis step — random changes waste time
6. **NEVER** leave a broken test "for later" — fix immediately or mark skip with reason
7. **NEVER** ignore FTS5 sanitization — unsanitized queries WILL crash
8. **NEVER** run Python from repo root — shadow modules WILL hijack imports
9. **NEVER** use PowerShell for debugging when exec_python works
10. **NEVER** assume column names — PRAGMA table_info FIRST (Rule 16)

## Performance Budgets

| Operation | Budget | Action if exceeded |
|-----------|--------|-------------------|
| Single DB query | <100ms | Add index or rewrite |
| FTS5 search | <50ms | Check query syntax |
| Engine import | <500ms | Remove side effects |
| Full test suite | <30s | Parallelize or optimize |
| Smoke test (each) | <2s | Remove heavy init |
| QA gate scan | <5s | Stream file, don't load all |

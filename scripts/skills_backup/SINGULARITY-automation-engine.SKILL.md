---
name: SINGULARITY-automation-engine
description: "Transcendent automation engine for LitigationOS. ABSORBS: automation-scraping, developer-experience, git-workflow. Use when: Go ingest engine, 8-worker goroutine pipeline, Rust CLI toolkit (fd/bat/dust), 7-drive file inventory, 611K+ files, dedup pipeline, content-based dedup, git workflow, shell management, session continuity, file watching, watchdog, process management, drive scanning, evidence hunting."
---

# SINGULARITY-automation-engine — Transcendent Automation & Ingest Engine

> **Absorbs:** automation-scraping, developer-experience, git-workflow
> **Tier:** TOOLS | **Domain:** File Processing, Ingest, CLI, Automation
> **Stack:** Go 1.26.1 · Rust (fd 10.4.2/bat 0.26.1/dust 1.2.4) · Python watchdog · git

---

## 1. Go Ingest Engine (8-Worker Goroutine Pipeline)

### Architecture
```
File Discovery (fd Rust scanner)
    ↓ File paths channel
Dispatcher (main goroutine)
    ↓ Distributes to worker pool
┌──────────┬──────────┬──────────┬──────────┐
│ Worker 1 │ Worker 2 │ Worker 3 │ Worker 4 │
│ Worker 5 │ Worker 6 │ Worker 7 │ Worker 8 │
└──────────┴──────────┴──────────┴──────────┘
    ↓ Results channel
Collector (aggregates results, writes to DB)
    ↓
SQLite (WAL mode, batch inserts via executemany)
```

### Go Worker Pool Pattern
```go
package ingest

import (
    "sync"
    "path/filepath"
)

const NumWorkers = 8

type FileResult struct {
    Path     string
    Size     int64
    SHA256   string
    MIMEType string
    Lane     string
    Error    error
}

func ProcessFiles(paths <-chan string, results chan<- FileResult, wg *sync.WaitGroup) {
    defer wg.Done()
    for path := range paths {
        result := processOneFile(path)
        results <- result
    }
}

func RunPipeline(rootDirs []string) []FileResult {
    paths := make(chan string, 1000)
    results := make(chan FileResult, 1000)
    var wg sync.WaitGroup

    // Spawn 8 workers
    for i := 0; i < NumWorkers; i++ {
        wg.Add(1)
        go ProcessFiles(paths, results, &wg)
    }

    // Feed file paths
    go func() {
        for _, dir := range rootDirs {
            filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
                if err == nil && !info.IsDir() {
                    paths <- path
                }
                return nil
            })
        }
        close(paths)
    }()

    // Collect results
    go func() {
        wg.Wait()
        close(results)
    }()

    var all []FileResult
    for r := range results {
        all = append(all, r)
    }
    return all
}
```

### Ingest Performance
| Metric | Value |
|--------|-------|
| Files processed | 57,000+ |
| Error rate | 0.0% |
| Workers | 8 goroutines |
| Throughput | ~2,000 files/sec (metadata), ~200 files/sec (content extraction) |
| Memory | <500 MB peak |

---

## 2. Rust CLI Toolkit

### fd — File Finder (5-50× faster than Get-ChildItem/find)
```bash
# Find all PDFs across litigation drives
fd -e pdf -t f . C:\ D:\ I:\ J:\

# Find files modified in last 7 days
fd -t f --changed-within 7d . C:\Users\andre\LitigationOS

# Find by pattern with size filter
fd -e pdf -S +1M "watson|custody|PPO" I:\

# Count files by extension
fd -t f -e pdf . C:\ | wc -l
fd -t f -e docx . I:\ | wc -l

# Exclude directories
fd -t f --exclude 11_ARCHIVES --exclude .git . C:\Users\andre\LitigationOS

# Execute command on each found file (e.g., compute SHA-256)
fd -e pdf -t f . I:\ -x sha256sum {}
```

### fd Usage Patterns for Evidence Hunting
```python
import subprocess

def fd_search(pattern: str, paths: list[str], extensions: list[str] | None = None,
              max_results: int = 500) -> list[str]:
    """Use fd (Rust) for blazing-fast file discovery."""
    cmd = ["fd", "-t", "f", "--no-ignore"]
    if extensions:
        for ext in extensions:
            cmd.extend(["-e", ext])
    cmd.append(pattern)
    cmd.extend(paths)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    lines = result.stdout.strip().split('\n')
    return [l for l in lines if l][:max_results]

def fd_inventory(root: str) -> dict[str, int]:
    """Count files by extension using fd."""
    result = subprocess.run(
        ["fd", "-t", "f", ".", root],
        capture_output=True, text=True, timeout=60
    )
    from collections import Counter
    from pathlib import Path
    exts = Counter()
    for line in result.stdout.strip().split('\n'):
        if line:
            exts[Path(line).suffix.lower()] += 1
    return dict(exts.most_common(30))
```

### bat — Syntax-Highlighted Viewer
```bash
# View file with syntax highlighting
bat --style=numbers,grid evidence_file.py

# View specific line range
bat --line-range 50:100 motion_draft.md

# View with diff highlighting
bat --diff old_motion.md new_motion.md

# Plain mode (no decorations) for piping
bat --plain --paging=never file.txt
```

### dust — Disk Usage Visualization
```bash
# Analyze disk usage for LitigationOS
dust -n 20 C:\Users\andre\LitigationOS

# Show only directories over 100MB
dust -s 100M C:\Users\andre\LitigationOS

# Compare drive usage across all drives
dust -d 1 C:\ D:\ I:\ J:\
```

---

## 3. 7-Drive File Inventory (611K+ Files)

### Drive Topology
| Drive | Type | Size | Files | Role |
|-------|------|------|-------|------|
| C:\ | NVMe SSD | 238 GB | ~125K | Primary — active DBs, engines |
| D:\ | USB | 466 GB | ~50K | Archives, temp scripts |
| F:\ | USB Flash | 58 GB | ~30K | Backups, evidence |
| G:\ | USB Flash | 58 GB | ~25K | Evidence, source docs |
| H:\ | — | — | — | Safety snapshots |
| I:\ | SD Card | ~30 GB | ~40K | Sorted evidence, dedup target |
| J:\ | USB 2TB | 1953 GB | ~341K | Centralization target (exFAT) |

### Inventory Management
```python
import sqlite3
from pathlib import Path

def update_inventory(drive: str, db_path: str = "litigation_context.db"):
    """Update file_inventory table for a drive using fd."""
    import subprocess
    result = subprocess.run(
        ["fd", "-t", "f", "--no-ignore", ".", f"{drive}:\\"],
        capture_output=True, text=True, timeout=300
    )
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    rows = []
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        p = Path(line)
        try:
            stat = p.stat()
            rows.append((
                str(p), p.name, p.suffix.lower(), drive,
                stat.st_size, stat.st_mtime
            ))
        except OSError:
            continue
    conn.executemany("""
        INSERT OR REPLACE INTO file_inventory
        (file_path, file_name, extension, drive, file_size, modified_time)
        VALUES (?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()
    conn.close()
    return len(rows)
```

---

## 4. Content-Based Dedup Pipeline

### USER MANDATE: No Hashing Alone — Peek Inside Documents
```python
import hashlib
from pathlib import Path

class ContentDeduplicator:
    """Content-based dedup that peeks inside files (not hash-only)."""

    def __init__(self, db_path: str = "litigation_context.db"):
        self.db_path = db_path

    def compute_hash(self, path: Path) -> str:
        sha = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                sha.update(chunk)
        return sha.hexdigest()

    def peek_content(self, path: Path) -> str:
        """Read first 1000 + last 500 chars for content comparison."""
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return self._peek_pdf(path)
        elif suffix == ".docx":
            return self._peek_docx(path)
        else:
            return self._peek_text(path)

    def _peek_text(self, path: Path) -> str:
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                head = f.read(1000)
                f.seek(0, 2)
                size = f.tell()
                if size > 1500:
                    f.seek(max(0, size - 500))
                    tail = f.read(500)
                else:
                    tail = ""
            return head + "|||" + tail
        except Exception:
            return ""

    def _peek_pdf(self, path: Path) -> str:
        try:
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(str(path))
            text = ""
            for i in range(min(2, len(pdf))):
                page = pdf[i]
                tp = page.get_textpage()
                text += tp.get_text_bounded()[:500]
                tp.close()
                page.close()
            pdf.close()
            return text
        except Exception:
            return ""

    def _peek_docx(self, path: Path) -> str:
        try:
            from docx import Document
            doc = Document(str(path))
            paras = [p.text for p in doc.paragraphs[:10]]
            return "\n".join(paras)[:1500]
        except Exception:
            return ""

    def find_duplicates(self, paths: list[Path]) -> list[tuple[Path, Path, float]]:
        """Stage 1: hash cluster, Stage 2: content verify."""
        hash_groups: dict[str, list[Path]] = {}
        for p in paths:
            h = self.compute_hash(p)
            hash_groups.setdefault(h, []).append(p)

        dupes = []
        for h, group in hash_groups.items():
            if len(group) > 1:
                for i in range(1, len(group)):
                    content_a = self.peek_content(group[0])
                    content_b = self.peek_content(group[i])
                    similarity = self._compare(content_a, content_b)
                    if similarity > 0.95:
                        dupes.append((group[0], group[i], similarity))
        return dupes

    def _compare(self, a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        common = len(set(a.split()) & set(b.split()))
        total = len(set(a.split()) | set(b.split()))
        return common / max(total, 1)
```

---

## 5. Git Workflow Automation

### Commit Conventions
```bash
# Feature work
git commit -m "feat(engine): add DuckDB analytics engine

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"

# Evidence/filing work
git commit -m "evidence: ingest 847 new PDFs from I:\ drive

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"

# Checkpoint commits
git commit -m "checkpoint: session-42 — COA brief draft complete

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Session Handoff Protocol
```python
def session_handoff(work_done: str, work_pending: str,
                    critical_state: str) -> str:
    """Generate session handoff record for continuity."""
    import sqlite3
    from datetime import datetime
    conn = sqlite3.connect("litigation_context.db")
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("""
        INSERT INTO session_handoff
        (session_id, work_completed, work_pending, critical_state, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (f"session-{datetime.now():%Y%m%d%H%M}",
          work_done, work_pending, critical_state,
          datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return "Handoff recorded"
```

---

## 6. Shell Management & Process Control

### Max 2 Concurrent Async Shells (EAGAIN Prevention)
```
Pre-spawn checklist:
1. list_powershell → count active shells
2. Active must be < 2
3. Wait 2 seconds between spawns
4. Chain related commands with &&
5. Stop shells IMMEDIATELY after reading output
```

### Safe Python Execution
```bash
# NEVER use python -c "..." in PowerShell — quoting breaks
# ALWAYS write to temp file and execute:
$env:PYTHONUTF8 = "1"
python -I D:\LitigationOS_tmp\script.py

# Or use agent_profile.ps1 wrappers:
. C:\Users\andre\LitigationOS\00_SYSTEM\tools\agent_profile.ps1
sspy file.py         # syntax check
srun script.py       # safe run (avoids shadow modules)
```

---

## 7. File Watching (watchdog)

### Auto-Ingest New Evidence
```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path

class EvidenceWatcher(FileSystemEventHandler):
    """Watch directories for new evidence files and auto-ingest."""

    WATCH_EXTENSIONS = {'.pdf', '.docx', '.txt', '.csv', '.json', '.md'}

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() in self.WATCH_EXTENSIONS:
            self.ingest_file(path)

    def ingest_file(self, path: Path):
        """Queue file for ingestion pipeline."""
        import sqlite3
        conn = sqlite3.connect("litigation_context.db")
        conn.execute("PRAGMA busy_timeout=60000")
        conn.execute("""
            INSERT OR IGNORE INTO ingest_queue (file_path, status, queued_at)
            VALUES (?, 'pending', datetime('now'))
        """, (str(path),))
        conn.commit()
        conn.close()

def start_watcher(directories: list[str]):
    observer = Observer()
    handler = EvidenceWatcher()
    for d in directories:
        observer.schedule(handler, d, recursive=True)
    observer.start()
    return observer
```

---

## 8. Key Rules & Constraints

| Rule | Enforcement |
|------|-------------|
| No file deletion | Move to 11_ARCHIVES/ only — every file has evidentiary value |
| Content-based dedup | Peek inside documents, never hash-only |
| Drive awareness | exFAT (J:\) = no WAL, no file locking |
| Shell limit | Max 2 concurrent async shells |
| Python safety | Never CWD to repo root (shadow modules), use -I flag |
| Script location | All inline Python → D:\LitigationOS_tmp\ |
| Git trailers | Co-authored-by: Copilot on every commit |
| fd over os.walk | 5-50× faster, always prefer fd for file discovery |

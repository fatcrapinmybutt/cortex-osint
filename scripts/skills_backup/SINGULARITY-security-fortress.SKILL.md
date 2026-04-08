---
name: SINGULARITY-security-fortress
description: "Full-spectrum security for LitigationOS. Use when: evidence protection, encryption, access control, audit trails, compliance scanning, vulnerability assessment, PII redaction, MCR 8.119(H) child name enforcement, filing sanitization, credential management, supply chain security, secure coding practices, OWASP patterns, input validation, path traversal prevention, SQL injection prevention."
version: "1.0.0"
forged_from:
  - appsec
  - crypto-infra
  - offensive-security
tier: "SPEC"
domain: "Full-spectrum security, evidence protection, compliance, privacy"
triggers:
  - security
  - encryption
  - compliance
  - protection
  - audit
  - vulnerability
  - redaction
  - PII
  - credential
  - injection
  - sanitization
  - OWASP
  - path traversal
cross_links:
  - SINGULARITY-debug-ops
  - SINGULARITY-code-mastery
  - SINGULARITY-system-forge
  - SINGULARITY-document-forge
---

# SINGULARITY-security-fortress — Full-Spectrum Security

> The litigation database contains the most sensitive data a person can have —
> custody records, police reports, financial records, medical evaluations,
> recordings, and the full strategy for multiple active court cases.
> Security is not optional. It is existential.

## 1. Threat Model for LitigationOS

### 1.1 Asset Classification
```
TIER 1 — CRITICAL (compromise = case loss)
  - litigation_context.db (1.3 GB, 790+ tables)
  - Filing packages (05_FILINGS/GOLDEN_SET/)
  - Audio/video evidence (recordings)
  - Strategy documents (04_ANALYSIS/)
  - Brain databases (00_SYSTEM/brains/)

TIER 2 — HIGH (compromise = significant harm)
  - Police reports (NSPD records)
  - Medical evaluations (HealthWest)
  - Financial records
  - AppClose communication logs
  - Adversary dossiers (04_ANALYSIS/ADVERSARY_TRACKS/)

TIER 3 — MEDIUM (compromise = operational disruption)
  - Engine source code (00_SYSTEM/engines/)
  - Extension code (.github/extensions/)
  - Configuration files
  - Session state and checkpoints

TIER 4 — LOW (public or near-public)
  - Court rules (MCR/MCL — public law)
  - SCAO forms (publicly available)
  - Open-source dependencies
```

### 1.2 Threat Actors
```
1. OPPOSING PARTY (Emily A. Watson, Ronald Berry)
   - Motivation: Gain litigation advantage, discover strategy
   - Capability: Physical access to shared locations, social engineering
   - Vector: Device theft, shoulder surfing, shared cloud accounts

2. HOSTILE COURT ACTORS (McNeill, Hoopes, Rusco)
   - Motivation: Protect judicial positions, suppress evidence
   - Capability: Subpoena power, contempt power, court orders
   - Vector: Discovery orders, device seizure during incarceration

3. THIRD-PARTY ADVERSARIES
   - Motivation: Identity theft, financial fraud
   - Capability: Remote exploitation, phishing
   - Vector: Unpatched software, weak passwords, public WiFi

4. ACCIDENTAL DISCLOSURE
   - Motivation: None (human error)
   - Capability: N/A
   - Vector: Misconfigured sharing, wrong attachment, print left behind
```

## 2. Evidence Protection Framework

### 2.1 Encryption at Rest
```python
"""Evidence encryption for portable drives and backups."""
import hashlib, os, secrets
from pathlib import Path

# For file-level encryption when evidence leaves the primary machine
def derive_key(password: str, salt: bytes) -> bytes:
    """PBKDF2-HMAC-SHA256 key derivation."""
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 310000, dklen=32)

def encrypt_evidence_file(src: Path, dst: Path, password: str) -> dict:
    """Encrypt a single evidence file with AES-256-GCM."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    salt = secrets.token_bytes(16)
    key = derive_key(password, salt)
    nonce = secrets.token_bytes(12)
    aesgcm = AESGCM(key)

    with open(src, 'rb') as f:
        plaintext = f.read()

    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    with open(dst, 'wb') as f:
        f.write(salt + nonce + ciphertext)

    return {
        'source': str(src),
        'encrypted': str(dst),
        'size_original': len(plaintext),
        'size_encrypted': len(salt) + len(nonce) + len(ciphertext),
        'algorithm': 'AES-256-GCM',
        'kdf': 'PBKDF2-HMAC-SHA256 (310000 iterations)'
    }
```

### 2.2 Integrity Verification
```python
"""SHA-256 integrity verification for evidence chain of custody."""
import hashlib
from pathlib import Path

def compute_evidence_hash(file_path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Streaming SHA-256 hash for evidence integrity."""
    sha = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(chunk_size):
            sha.update(chunk)
    return sha.hexdigest()

def verify_evidence_integrity(manifest: list[dict]) -> dict:
    """Verify all evidence files match their recorded hashes."""
    results = {'total': len(manifest), 'verified': 0, 'failed': [], 'missing': []}

    for item in manifest:
        path = Path(item['path'])
        if not path.exists():
            results['missing'].append(str(path))
            continue

        current_hash = compute_evidence_hash(path)
        if current_hash == item['sha256']:
            results['verified'] += 1
        else:
            results['failed'].append({
                'path': str(path),
                'expected': item['sha256'],
                'actual': current_hash
            })

    return results
```

## 3. PII Protection & Compliance

### 3.1 MCR 8.119(H) Child Name Enforcement
```python
"""MANDATORY: Child's full name must NEVER appear in any output."""
import re

# L.D.W. = Andrew's son. MCR 8.119(H) requires initials only.
CHILD_NAME_PATTERNS = [
    r'\bLincoln\b',
    r'\bLincoln\s+David\b',
    r'\bLincoln\s+David\s+Watson\b',
    r'\bLincoln\s+D\.\s+Watson\b',
    r'\bL\.?\s*D\.?\s*Watson\b(?!\s*\()',  # But NOT "L.D.W."
]

CHILD_FULL_NAME_REGEX = re.compile(
    '|'.join(CHILD_NAME_PATTERNS), re.IGNORECASE
)

def enforce_child_name_protection(content: str) -> tuple[str, int]:
    """Replace any occurrence of child's full name with 'L.D.W.'"""
    count = len(CHILD_FULL_NAME_REGEX.findall(content))
    sanitized = CHILD_FULL_NAME_REGEX.sub('L.D.W.', content)
    return sanitized, count

def scan_for_pii_violations(file_path: str) -> list:
    """Scan a file for PII violations."""
    violations = []
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        for i, line in enumerate(f, 1):
            # Child name
            if CHILD_FULL_NAME_REGEX.search(line):
                violations.append({
                    'line': i, 'type': 'CHILD_NAME',
                    'severity': 'CRITICAL',
                    'text': line.strip()[:100]
                })
            # SSN pattern
            if re.search(r'\b\d{3}-\d{2}-\d{4}\b', line):
                violations.append({
                    'line': i, 'type': 'SSN',
                    'severity': 'CRITICAL',
                    'text': '[REDACTED]'
                })
            # DOB in certain contexts
            if re.search(r'\b(?:DOB|born|birth)\b.*?\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', line, re.I):
                violations.append({
                    'line': i, 'type': 'DOB',
                    'severity': 'HIGH',
                    'text': line.strip()[:100]
                })
    return violations
```

### 3.2 Filing Sanitization (Rule 3 — No AI Artifacts)
```python
"""Strip ALL AI/DB references before court-facing output."""

AI_ARTIFACT_PATTERNS = [
    # System names
    r'\bLitigationOS\b', r'\bMANBEARPIG\b', r'\bTHEMANBEARPIG\b',
    r'\bEGCP\b', r'\bSINGULARITY\b', r'\bMEEK\b', r'\bKRAKEN\b',
    r'\bNEXUS\s*daemon\b', r'\bCORTEX\b', r'\bORACLE\b',
    r'\bPROMETHEUS\b', r'\bATHENA\b', r'\bCHRONOS\b',

    # Database artifacts
    r'\bevidence_quotes\b', r'\bauthority_chains\b', r'\bimpeachment_matrix\b',
    r'\bcontradiction_map\b', r'\bjudicial_violations\b', r'\btimeline_events\b',
    r'\bfiling_readiness\b', r'\bconvergence_domains\b',

    # File paths
    r'C:\\Users\\andre\\', r'D:\\LitigationOS', r'00_SYSTEM',
    r'04_ANALYSIS', r'\.agents\\', r'\.github\\extensions',

    # Scoring artifacts
    r'\bLOCUS\s*score\b', r'\brelevance_score\b', r'\bconfidence\s*=\s*\d',
    r'\bimpeachment_value\b', r'\bnovelty\s*score\b',

    # AI terminology
    r'\bFTS5\b', r'\bBM25\b', r'\bvector\s*search\b',
    r'\bsemantic\s*similarity\b', r'\bcross-encoder\b',
]

import re

AI_ARTIFACT_REGEX = re.compile(
    '|'.join(AI_ARTIFACT_PATTERNS), re.IGNORECASE
)

def scan_for_ai_artifacts(content: str) -> list:
    """Find ALL AI/system artifacts that must be removed from court filings."""
    findings = []
    for i, line in enumerate(content.split('\n'), 1):
        matches = AI_ARTIFACT_REGEX.findall(line)
        if matches:
            findings.append({
                'line': i,
                'matches': matches,
                'text': line.strip()[:120]
            })
    return findings

def filing_sanitization_gate(file_path: str) -> dict:
    """PASS/FAIL gate: returns FAIL if ANY AI artifact found."""
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    artifacts = scan_for_ai_artifacts(content)
    pii = scan_for_pii_violations(file_path)

    return {
        'file': file_path,
        'ai_artifacts': len(artifacts),
        'pii_violations': len(pii),
        'passed': len(artifacts) == 0 and len(pii) == 0,
        'details': {
            'ai': artifacts[:10],
            'pii': pii[:10]
        }
    }
```

## 4. Input Validation & Injection Prevention

### 4.1 SQL Injection Prevention
```python
"""ALL database queries MUST use parameterized binds."""

# CORRECT — parameterized
def safe_query(conn, table: str, column: str, value: str):
    # Validate table/column names against allowlist
    ALLOWED_TABLES = {
        'evidence_quotes', 'timeline_events', 'impeachment_matrix',
        'contradiction_map', 'judicial_violations', 'authority_chains_v2',
        'police_reports', 'filing_readiness', 'deadlines'
    }
    if table not in ALLOWED_TABLES:
        raise ValueError(f"Table '{table}' not in allowlist")

    # Column validation via PRAGMA
    valid_cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in valid_cols:
        raise ValueError(f"Column '{column}' not in {table}")

    # Parameterized query — safe
    return conn.execute(
        f"SELECT * FROM {table} WHERE {column} = ? LIMIT 100",
        (value,)
    ).fetchall()

# FORBIDDEN — string interpolation
# conn.execute(f"SELECT * FROM {table} WHERE name = '{user_input}'")
```

### 4.2 Path Traversal Prevention
```python
"""Prevent path traversal attacks in file operations."""
import os
from pathlib import Path

ALLOWED_ROOTS = [
    Path(r"C:\Users\andre\LitigationOS"),
    Path(r"D:\LitigationOS_tmp"),
    Path(r"I:\"),
    Path(r"J:\LitigationOS_CENTRAL"),
]

def validate_path(requested_path: str) -> Path:
    """Validate a path is within allowed directories."""
    resolved = Path(requested_path).resolve()

    for root in ALLOWED_ROOTS:
        try:
            resolved.relative_to(root.resolve())
            return resolved
        except ValueError:
            continue

    raise PermissionError(
        f"Path '{resolved}' is outside allowed directories: "
        f"{[str(r) for r in ALLOWED_ROOTS]}"
    )
```

## 5. Audit Trail

### 5.1 Evidence Access Logging
```python
"""Log all access to evidence files for chain of custody."""
import json, time
from pathlib import Path

AUDIT_LOG = Path(r"C:\Users\andre\LitigationOS\logs\evidence_audit.jsonl")

def log_evidence_access(action: str, file_path: str, actor: str = "system",
                        details: str = "") -> None:
    """Append to audit log. NEVER delete audit entries."""
    entry = {
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'action': action,  # READ, COPY, MOVE, INGEST, EXPORT
        'file_path': file_path,
        'actor': actor,
        'details': details
    }

    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry) + '\n')
```

### 5.2 Database Change Tracking
```python
"""Track all writes to litigation_context.db."""

def create_audit_trigger(conn, table_name: str):
    """Create audit triggers for INSERT/UPDATE/DELETE on a table."""
    # Create audit table if not exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT (datetime('now')),
            table_name TEXT,
            operation TEXT,
            old_data TEXT,
            new_data TEXT
        )
    """)

    # INSERT trigger
    conn.execute(f"""
        CREATE TRIGGER IF NOT EXISTS audit_{table_name}_insert
        AFTER INSERT ON {table_name}
        BEGIN
            INSERT INTO _audit_log (table_name, operation, new_data)
            VALUES ('{table_name}', 'INSERT', json_object('rowid', NEW.rowid));
        END
    """)
    conn.commit()
```

## 6. Secure Coding Standards for LitigationOS

### 6.1 Dependency Security
```python
# Check for known vulnerabilities in Python packages
# pip install pip-audit
# pip-audit --strict --desc

# MANDATORY before any new package install:
# 1. Check PyPI for maintenance status (last release < 6 months)
# 2. Check GitHub for open security issues
# 3. Verify Python 3.12 compatibility
# 4. Check license compatibility (MIT, Apache 2.0, BSD preferred)
# 5. Prefer packages with type stubs
```

### 6.2 Secret Management
```python
"""No secrets in source code. Ever."""
import os

# CORRECT — environment variables
DB_PASSWORD = os.environ.get('LITIGATIONOS_DB_KEY', '')
API_KEY = os.environ.get('LITIGATIONOS_API_KEY', '')

# CORRECT — .env file (NOT committed to git)
# .gitignore must contain: .env, *.key, *.pem, *.p12

# FORBIDDEN — hardcoded secrets
# PASSWORD = "my_secret_password"
# API_KEY = "sk-abc123..."
```

## 7. Backup & Recovery Security

### 7.1 Secure Backup Protocol
```python
def secure_backup(db_path: str, backup_dir: str) -> dict:
    """Create integrity-verified backup of a database."""
    import shutil, hashlib, time
    from pathlib import Path

    src = Path(db_path)
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    dst = Path(backup_dir) / f"{src.stem}_backup_{timestamp}{src.suffix}"

    # Copy with integrity
    shutil.copy2(str(src), str(dst))

    # Verify copy
    src_hash = compute_evidence_hash(src)
    dst_hash = compute_evidence_hash(dst)

    return {
        'source': str(src),
        'backup': str(dst),
        'size': src.stat().st_size,
        'sha256': src_hash,
        'verified': src_hash == dst_hash,
        'timestamp': timestamp
    }
```

## Anti-Patterns (MANDATORY — ZERO TOLERANCE)

1. **NEVER** store passwords or keys in source code or config files committed to git
2. **NEVER** use string formatting for SQL queries — parameterized binds ONLY
3. **NEVER** accept user-provided file paths without validation against allowlist
4. **NEVER** expose child's full name in any output (MCR 8.119(H))
5. **NEVER** leave AI/system artifacts in court-facing documents (Rule 3)
6. **NEVER** transmit evidence over unencrypted channels
7. **NEVER** delete audit log entries (append-only, Rule 1)
8. **NEVER** disable WAL mode on NTFS drives (integrity protection)
9. **NEVER** run untrusted code with access to litigation database
10. **NEVER** use `eval()` or `exec()` with user-provided strings
11. **NEVER** store evidence on cloud services without encryption
12. **NEVER** share database connection strings in error messages
13. **NEVER** log PII (SSN, DOB, child name) in application logs
14. **NEVER** skip integrity verification after file copy/move operations
15. **NEVER** use MD5 or SHA-1 for integrity verification — SHA-256 minimum

## Performance Budgets

| Operation | Budget | Technique |
|-----------|--------|-----------|
| PII scan (per file) | <100ms | Compiled regex, streaming |
| AI artifact scan | <50ms | Pre-compiled pattern set |
| SHA-256 hash (1GB) | <3s | Streaming 1MB chunks |
| Path validation | <1ms | Resolved path comparison |
| Audit log write | <5ms | Append-only JSONL |
| Filing sanitization gate | <500ms | Combined PII + AI scan |

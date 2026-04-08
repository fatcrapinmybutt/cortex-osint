"""LitigationOS Unified Apex File Organizer v2.0.0

Combines the best of:
  - OMEGA-FLATTEN (30-folder taxonomy, MEEK patterns, magic bytes, entity extraction,
    litigation scoring 0-10, 3-phase dedup via SequenceMatcher)
  - ai_organizer_stack / smart_organizer (scan-then-plan mode, JSONL ledger, checkpoint)
  - Foldr (preview, undo, watch mode via watchdog)
  - Web research best-practices 2025 (sentence-transformers fallback, cursor pagination)

Architecture:
  - Plan-first: --plan generates a plan.csv (no moves)
  - Apply: --apply executes the plan (with ledger + checkpoint)
  - Dedup: --dedup runs 3-phase content-based deduplication
  - Watch: --watch monitors a root and organizes new arrivals in real-time
  - DB sync: --sync-db updates file_inventory in litigation_context.db after moves

Run with:
  python -I D:/LitigationOS_tmp/unified_organizer.py --scan C:/path --plan
  python -I D:/LitigationOS_tmp/unified_organizer.py --scan C:/path --apply
  python -I D:/LitigationOS_tmp/unified_organizer.py --dedup I:/
  python -I D:/LitigationOS_tmp/unified_organizer.py --watch I:/ --apply

Author: LitigationOS SINGULARITY v7.0
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import os
import re
import shutil
import sqlite3
import sys
import time
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, FrozenSet, Iterator, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# Version
# ─────────────────────────────────────────────────────────────────────────────

__version__ = "2.0.0"

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("unified_organizer")

# ─────────────────────────────────────────────────────────────────────────────
# 30-Folder Taxonomy (from OMEGA-FLATTEN config.py)
# ─────────────────────────────────────────────────────────────────────────────

EXTENSION_MAP: Dict[str, str] = {
    # PDF
    ".pdf": "PDF",
    # DOCX
    ".docx": "DOCX", ".doc": "DOCX", ".rtf": "DOCX", ".odt": "DOCX", ".wps": "DOCX",
    # MARKDOWN
    ".md": "MD", ".markdown": "MD", ".mdx": "MD", ".rst": "MD",
    # TXT
    ".txt": "TXT", ".text": "TXT", ".asc": "TXT", ".nfo": "TXT",
    # HTML
    ".html": "HTML", ".htm": "HTML", ".css": "HTML",
    ".mhtml": "HTML", ".mht": "HTML", ".xhtml": "HTML",
    # JSON
    ".json": "JSON", ".jsonl": "JSON", ".geojson": "JSON",
    ".ndjson": "JSON", ".har": "JSON",
    # CSV / spreadsheets
    ".csv": "CSV", ".tsv": "CSV", ".xlsx": "CSV", ".xls": "CSV",
    ".ods": "CSV", ".numbers": "CSV",
    # XML
    ".xml": "XML", ".xsl": "XML", ".xslt": "XML", ".xsd": "XML",
    ".dtd": "XML", ".rss": "XML", ".atom": "XML", ".plist": "XML",
    # IMG
    ".png": "IMG", ".jpg": "IMG", ".jpeg": "IMG", ".gif": "IMG",
    ".bmp": "IMG", ".tiff": "IMG", ".tif": "IMG", ".webp": "IMG",
    ".ico": "IMG", ".heic": "IMG", ".svg": "IMG",
    ".raw": "IMG", ".cr2": "IMG", ".nef": "IMG", ".arw": "IMG", ".dng": "IMG",
    # VIDEO
    ".mp4": "VIDEO", ".avi": "VIDEO", ".mov": "VIDEO", ".mkv": "VIDEO",
    ".wmv": "VIDEO", ".flv": "VIDEO", ".webm": "VIDEO", ".m4v": "VIDEO",
    ".mpg": "VIDEO", ".mpeg": "VIDEO", ".3gp": "VIDEO", ".ts": "VIDEO", ".vob": "VIDEO",
    # AUDIO
    ".mp3": "AUDIO", ".wav": "AUDIO", ".m4a": "AUDIO", ".ogg": "AUDIO",
    ".flac": "AUDIO", ".aac": "AUDIO", ".wma": "AUDIO", ".opus": "AUDIO",
    ".aiff": "AUDIO", ".mid": "AUDIO", ".midi": "AUDIO",
    # MEDIA (design)
    ".psd": "MEDIA", ".ai": "MEDIA", ".sketch": "MEDIA", ".fig": "MEDIA",
    ".xd": "MEDIA", ".indd": "MEDIA", ".eps": "MEDIA", ".cdr": "MEDIA", ".blend": "MEDIA",
    # PY
    ".py": "PY", ".pyw": "PY", ".pyi": "PY", ".pyx": "PY",
    # CODE (other languages)
    ".js": "CODE", ".ts": "CODE", ".jsx": "CODE", ".tsx": "CODE",
    ".go": "CODE", ".java": "CODE", ".c": "CODE", ".cpp": "CODE",
    ".h": "CODE", ".hpp": "CODE", ".cs": "CODE", ".rs": "CODE",
    ".rb": "CODE", ".php": "CODE", ".sh": "CODE", ".ps1": "CODE",
    ".bat": "CODE", ".cmd": "CODE", ".sql": "CODE", ".r": "CODE",
    ".scala": "CODE", ".kt": "CODE", ".swift": "CODE", ".lua": "CODE",
    ".pl": "CODE", ".vbs": "CODE", ".asm": "CODE",
    # DB
    ".db": "DB", ".sqlite": "DB", ".sqlite3": "DB", ".mdb": "DB", ".accdb": "DB",
    # DATA (binary)
    ".dat": "DATA", ".bin": "DATA", ".parquet": "DATA", ".avro": "DATA",
    ".pickle": "DATA", ".pkl": "DATA", ".npy": "DATA", ".npz": "DATA",
    ".h5": "DATA", ".hdf5": "DATA", ".feather": "DATA", ".arrow": "DATA",
    ".bson": "DATA", ".msgpack": "DATA",
    # EMAIL
    ".eml": "EMAIL", ".msg": "EMAIL", ".mbox": "EMAIL",
    ".pst": "EMAIL", ".ost": "EMAIL", ".emlx": "EMAIL",
    # PPTX
    ".pptx": "PPTX", ".ppt": "PPTX", ".key": "PPTX", ".odp": "PPTX",
    # CONFIG
    ".ini": "CONFIG", ".yaml": "CONFIG", ".yml": "CONFIG", ".toml": "CONFIG",
    ".env": "CONFIG", ".cfg": "CONFIG", ".conf": "CONFIG",
    ".properties": "CONFIG", ".reg": "CONFIG", ".inf": "CONFIG",
    ".editorconfig": "CONFIG", ".gitignore": "CONFIG", ".dockerignore": "CONFIG",
    # LOG
    ".log": "LOG", ".logs": "LOG",
    # ARCHIVE
    ".zip": "ARCHIVE", ".rar": "ARCHIVE", ".7z": "ARCHIVE",
    ".tar": "ARCHIVE", ".gz": "ARCHIVE", ".bz2": "ARCHIVE",
    ".xz": "ARCHIVE", ".tgz": "ARCHIVE", ".cab": "ARCHIVE",
    ".iso": "ARCHIVE", ".dmg": "ARCHIVE",
    # EXE
    ".exe": "EXE", ".msi": "EXE", ".dll": "EXE", ".sys": "EXE",
    ".drv": "EXE", ".ocx": "EXE", ".com": "EXE", ".scr": "EXE",
    ".appx": "EXE", ".apk": "EXE", ".deb": "EXE", ".rpm": "EXE",
    # FONT
    ".ttf": "FONT", ".otf": "FONT", ".woff": "FONT", ".woff2": "FONT", ".eot": "FONT",
    # CERT
    ".pem": "CERT", ".crt": "CERT", ".key": "CERT", ".cer": "CERT",
    ".p12": "CERT", ".pfx": "CERT", ".csr": "CERT", ".jks": "CERT",
    # BACKUP
    ".bak": "BACKUP", ".old": "BACKUP", ".orig": "BACKUP", ".swp": "BACKUP", ".sav": "BACKUP",
    # TEMP
    ".tmp": "TEMP", ".cache": "TEMP", ".temp": "TEMP",
}

# LEGAL folder has no extension — detected purely by content
TEXT_FOLDERS: FrozenSet[str] = frozenset({
    "MD", "TXT", "JSON", "CSV", "PY", "CODE", "HTML", "XML", "CONFIG", "LOG", "LEGAL",
})

# ─────────────────────────────────────────────────────────────────────────────
# Magic bytes (16-byte sniff for binary classification)
# ─────────────────────────────────────────────────────────────────────────────

_MAGIC: List[Tuple[bytes, str]] = [
    (b"SQLite format 3", "DB"),
    (b"%PDF", "PDF"),
    (b"\x89PNG\r\n\x1a\n", "IMG"),
    (b"\xff\xd8\xff", "IMG"),       # JPEG
    (b"GIF87a", "IMG"),
    (b"GIF89a", "IMG"),
    (b"\x00\x00\x01\x00", "IMG"),  # ICO
    (b"fLaC", "AUDIO"),             # FLAC
    (b"OggS", "AUDIO"),             # OGG
    (b"ID3", "AUDIO"),              # MP3 (ID3 tag)
    (b"\xff\xfb", "AUDIO"),         # MP3
    (b"\xff\xf3", "AUDIO"),
    (b"\xff\xf2", "AUDIO"),
    (b"RIFF", "MEDIA"),             # AVI/WAV (generic RIFF)
    (b"\x1aE\xdf\xa3", "VIDEO"),   # MKV/WebM
    (b"Rar!\x1a\x07", "ARCHIVE"),
    (b"\x1f\x8b", "ARCHIVE"),       # GZIP
    (b"7z\xbc\xaf\x27\x1c", "ARCHIVE"),
    (b"PK\x03\x04", "ARCHIVE"),    # ZIP (also DOCX/XLSX/PPTX — overridden by ext)
    (b"PK\x05\x06", "ARCHIVE"),
    (b"MZ", "EXE"),                 # PE executable
    (b"\x7fELF", "EXE"),            # ELF
]

def sniff_magic(path: str) -> Optional[str]:
    """Return folder name from first 16 bytes, or None if unrecognised."""
    try:
        with open(path, "rb") as f:
            header = f.read(16)
        for magic, folder in _MAGIC:
            if header.startswith(magic):
                return folder
    except OSError:
        pass
    return None

# ─────────────────────────────────────────────────────────────────────────────
# MEEK lane routing (E→D→F→A→B priority)
# ─────────────────────────────────────────────────────────────────────────────

_MEEK_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("E", re.compile(
        r"judicial.misconduct|jtc|disqualif|recusal|mcr\s*2\.003|"
        r"mcneill|jenny.mcneill|ex.parte|hostile.record|benchbook|"
        r"judicial.tenure|canon\s+\d|bias",
        re.IGNORECASE,
    )),
    ("D", re.compile(
        r"personal.protection.order|ppo|stalking|harassment|"
        r"restraining.order|no.contact|protection.order|domestic.violence",
        re.IGNORECASE,
    )),
    ("F", re.compile(
        r"court.of.appeals|coa|366810|supreme.court|msc|appellate|"
        r"leave.to.appeal|brief.on.appeal|appendix",
        re.IGNORECASE,
    )),
    ("A", re.compile(
        r"custody|parenting.time|parenting-time|visitation|watson|"
        r"emily.watson|l\.d\.w|friend.of.the.court|foc|pamela.rusco|"
        r"child.support|best.interest|parental.alienation|001507",
        re.IGNORECASE,
    )),
    ("B", re.compile(
        r"shady.oaks|garland|norton.shores|lockout|title|sewage|"
        r"egle|habitability|water.shutoff|utility|mobile.home|002760",
        re.IGNORECASE,
    )),
]

def detect_meek_lane(path: str, text: str = "") -> Optional[str]:
    """Return the highest-priority matching MEEK lane, or None."""
    combined = (os.path.basename(path) + " " + text[:4096]).lower()
    for lane, pattern in _MEEK_PATTERNS:
        if pattern.search(combined):
            return lane
    return None

# ─────────────────────────────────────────────────────────────────────────────
# Entity extraction (from OMEGA-FLATTEN analyzer.py)
# ─────────────────────────────────────────────────────────────────────────────

_RE_NAMES = re.compile(r"\b([A-Z][a-z]{2,}(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]{2,})\b")
_RE_DATES_MDY = re.compile(
    r"\b((?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2})\b"
)
_RE_DATES_YMD = re.compile(
    r"\b((?:19|20)\d{2}-(?:0?[1-9]|1[0-2])-(?:0?[1-9]|[12]\d|3[01]))\b"
)
_RE_DATES_LONG = re.compile(
    r"\b((?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+\d{1,2},?\s+\d{4})\b",
    re.IGNORECASE,
)
_RE_CASE_NUMBERS = re.compile(r"\b(\d{4}-\d{4,6}-[A-Z]{2})\b")
_RE_DOLLAR = re.compile(r"\$[\d,]+\.?\d*")
_RE_MCL = re.compile(r"\bMCL\s+\d+\.\d+[a-z]?\b", re.IGNORECASE)
_RE_MCR = re.compile(r"\bMCR\s+\d+\.\d+[a-z]?\b", re.IGNORECASE)
_RE_EVIDENCE_MARKERS = re.compile(
    r"\b(?:exhibit|evidence|affidavit|sworn|notarized|testimony|"
    r"deposition|subpoena|discovery|admission|stipulation|declaration)\b",
    re.IGNORECASE,
)
_RE_MEEK_DENSITY = re.compile(
    r"\b(?:custody|parenting.time|ppo|protection.order|shady.oaks|"
    r"judicial.misconduct|jtc|disqualification|recusal|appellate|"
    r"court.of.appeals|watson|mcneill|lockout|title|friend.of.the.court|"
    r"foc|contempt|garnishment|best.interest|domestic.violence)\b",
    re.IGNORECASE,
)

def extract_entities(text: str) -> Dict[str, List[str]]:
    """Extract litigation-relevant entities from text."""
    names = list(dict.fromkeys(_RE_NAMES.findall(text)[:50]))
    dates = list(dict.fromkeys(
        _RE_DATES_MDY.findall(text) +
        _RE_DATES_YMD.findall(text) +
        _RE_DATES_LONG.findall(text)
    ))[:50]
    case_numbers = list(dict.fromkeys(_RE_CASE_NUMBERS.findall(text)))[:20]
    dollars = list(dict.fromkeys(_RE_DOLLAR.findall(text)))[:30]
    mcl_cites = list(dict.fromkeys(_RE_MCL.findall(text)))[:30]
    mcr_cites = list(dict.fromkeys(_RE_MCR.findall(text)))[:30]
    return {
        "names": names,
        "dates": dates,
        "case_numbers": case_numbers,
        "dollar_amounts": dollars,
        "mcl_citations": mcl_cites,
        "mcr_citations": mcr_cites,
    }

def score_litigation(text: str, entities: Dict[str, List[str]], ext: str) -> Tuple[float, str]:
    """Score litigation relevance 0–10 and assign evidence_value (high/medium/low/none)."""
    score = 0.0
    # MEEK keyword density (0-3)
    meek_hits = len(_RE_MEEK_DENSITY.findall(text[:8192]))
    if meek_hits >= 10:
        score += 3.0
    elif meek_hits >= 5:
        score += 2.0
    elif meek_hits >= 2:
        score += 1.0
    elif meek_hits >= 1:
        score += 0.5
    # Entity richness (0-2)
    entity_count = (
        len(entities.get("names", []))
        + len(entities.get("dates", []))
        + len(entities.get("case_numbers", []))
        + len(entities.get("dollar_amounts", []))
    )
    if entity_count >= 15:
        score += 2.0
    elif entity_count >= 8:
        score += 1.5
    elif entity_count >= 3:
        score += 1.0
    elif entity_count >= 1:
        score += 0.5
    # Legal citations (0-2)
    cites = entities.get("mcl_citations", []) + entities.get("mcr_citations", [])
    if len(cites) >= 5:
        score += 2.0
    elif len(cites) >= 2:
        score += 1.5
    elif len(cites) >= 1:
        score += 1.0
    # Evidence markers (0-2)
    ev_hits = len(_RE_EVIDENCE_MARKERS.findall(text[:8192]))
    if ev_hits >= 5:
        score += 2.0
    elif ev_hits >= 2:
        score += 1.5
    elif ev_hits >= 1:
        score += 0.5
    # File type bonus (0-1)
    if ext in (".pdf", ".docx", ".doc"):
        score += 1.0
    score = min(score, 10.0)
    if score >= 7.0:
        return round(score, 2), "high"
    elif score >= 4.0:
        return round(score, 2), "medium"
    elif score >= 1.5:
        return round(score, 2), "low"
    return round(score, 2), "none"

# ─────────────────────────────────────────────────────────────────────────────
# Directories & files to skip
# ─────────────────────────────────────────────────────────────────────────────

SKIP_DIRS: FrozenSet[str] = frozenset({
    "$Recycle.Bin", "$RECYCLE.BIN", "System Volume Information", "Windows",
    "ProgramData", "Program Files", "Program Files (x86)", "Recovery",
    "PerfLogs", "Config.Msi", "__pycache__", ".git", "node_modules",
    ".venv", "venv", ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "WindowsApps", "MSOCache", "build", "dist",
    # LitigationOS internal paths — never touch
    "00_SYSTEM", "brains", ".github", "pytools_venv",
})

SKIP_FILES: FrozenSet[str] = frozenset({
    "desktop.ini", "thumbs.db", "Thumbs.db", ".DS_Store", "ntuser.dat",
    "NTUSER.DAT", "ntuser.dat.LOG1", "ntuser.dat.LOG2", "ntuser.pol",
    "UsrClass.dat", "pagefile.sys", "swapfile.sys", "hiberfil.sys",
    "DumpStack.log.tmp",
})

# Protected paths — files under these are NEVER moved
PROTECTED_PATH_PARTS: FrozenSet[str] = frozenset({
    ".github", "00_SYSTEM", "brains", "engines",
    "pytools_venv", ".mcp_venv", "node_modules",
})

# Protected file extensions that are NEVER moved
PROTECTED_EXTENSIONS: FrozenSet[str] = frozenset({
    ".db", ".sqlite", ".sqlite3",  # databases
    ".db-shm", ".db-wal",          # WAL sidecar files
    ".exe", ".msi",                # executables
    ".spec",                       # PyInstaller specs
})

# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────

CHECKPOINT_PATH = Path(r"D:\LitigationOS_tmp\organizer_checkpoint.json")
LEDGER_PATH = Path(r"D:\LitigationOS_tmp\organizer_ledger.jsonl")
PLAN_CSV_PATH = Path(r"D:\LitigationOS_tmp\organizer_plan.csv")
LITIGATION_DB = Path(r"C:\Users\andre\LitigationOS\litigation_context.db")

CONTENT_PREVIEW_SIZE = 4096   # bytes for text preview
MAX_ANALYZE_SIZE = 50 * 1024 * 1024   # skip text analysis above 50 MB
BATCH_SIZE = 500
CHECKPOINT_INTERVAL = 1000
DEDUP_SIMILARITY_THRESHOLD = 0.85
DEDUP_NAME_THRESHOLD = 0.80

# ─────────────────────────────────────────────────────────────────────────────
# SHA-256 helper
# ─────────────────────────────────────────────────────────────────────────────

def sha256_file(path: str, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while True:
                data = f.read(chunk)
                if not data:
                    break
                h.update(data)
    except OSError:
        return ""
    return h.hexdigest()

# ─────────────────────────────────────────────────────────────────────────────
# Content preview for text classification
# ─────────────────────────────────────────────────────────────────────────────

def read_content_preview(path: str, size: int = CONTENT_PREVIEW_SIZE) -> str:
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            with open(path, "r", encoding=enc, errors="replace") as f:
                return f.read(size)
        except (OSError, UnicodeDecodeError):
            continue
    return ""

# ─────────────────────────────────────────────────────────────────────────────
# File classification
# ─────────────────────────────────────────────────────────────────────────────

def classify_file(path: str, size: int) -> str:
    """Return the taxonomy folder for this file (30-folder taxonomy)."""
    ext = os.path.splitext(path)[1].lower()
    # 1. Extension-based lookup
    if ext and ext in EXTENSION_MAP:
        folder = EXTENSION_MAP[ext]
        # DOCX/XLSX/PPTX are stored as ZIP — trust extension, not magic
        if folder in ("DOCX", "CSV", "PPTX"):
            return folder
        return folder
    # 2. Magic bytes for unknown extensions or extension-less files
    magic = sniff_magic(path)
    if magic:
        return magic
    # 3. Content peek for small text files — try to detect LEGAL
    if size < MAX_ANALYZE_SIZE and size > 0 and not ext:
        preview = read_content_preview(path, 1024)
        if preview and _RE_MEEK_DENSITY.search(preview):
            return "LEGAL"
    return "_UNKNOWN"

def is_protected(path: str) -> bool:
    """Return True if this file must never be moved."""
    path_lower = path.lower()
    # Protected by path component
    parts = path_lower.replace("\\", "/").split("/")
    for part in parts:
        if part in {p.lower() for p in PROTECTED_PATH_PARTS}:
            return True
    # Protected by extension
    ext = os.path.splitext(path)[1].lower()
    if ext in PROTECTED_EXTENSIONS:
        return True
    # Never touch files named something in SKIP_FILES
    if os.path.basename(path) in SKIP_FILES:
        return True
    return False

# ─────────────────────────────────────────────────────────────────────────────
# Scanner — os.scandir iterative (memory-safe for 600K+ files)
# ─────────────────────────────────────────────────────────────────────────────

def scan_root(
    root: str,
    max_files: Optional[int] = None,
) -> Iterator[Dict[str, Any]]:
    """Yield file info dicts for every qualifying file under root."""
    stack = [root]
    count = 0
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                entries = list(it)
        except (PermissionError, OSError):
            continue
        for entry in entries:
            if entry.is_dir(follow_symlinks=False):
                if entry.name not in SKIP_DIRS:
                    stack.append(entry.path)
                continue
            if not entry.is_file(follow_symlinks=False):
                continue
            if entry.name in SKIP_FILES:
                continue
            if is_protected(entry.path):
                continue
            try:
                stat = entry.stat(follow_symlinks=False)
            except OSError:
                continue
            size = stat.st_size
            ext = os.path.splitext(entry.name)[1].lower()
            yield {
                "path": entry.path,
                "name": entry.name,
                "ext": ext,
                "size": size,
                "drive": os.path.splitdrive(entry.path)[0].rstrip(":").upper(),
                "folder": classify_file(entry.path, size),
            }
            count += 1
            if max_files and count >= max_files:
                return

# ─────────────────────────────────────────────────────────────────────────────
# Plan generation (dry run)
# ─────────────────────────────────────────────────────────────────────────────

def generate_plan(
    root: str,
    dest_root: str,
    max_files: Optional[int] = None,
    analyze: bool = False,
) -> List[Dict[str, Any]]:
    """Scan root and build a plan (list of move operations). No files are moved."""
    plan: List[Dict[str, Any]] = []
    stats: Dict[str, int] = defaultdict(int)
    t0 = time.perf_counter()

    for i, info in enumerate(scan_root(root, max_files), 1):
        if i % 1000 == 0:
            elapsed = time.perf_counter() - t0
            log.info("Scanned %d files in %.1fs …", i, elapsed)

        folder = info["folder"]
        stats[folder] += 1

        # Proposed destination
        dest_dir = os.path.join(dest_root, folder)
        dest_path = os.path.join(dest_dir, info["name"])

        # Resolve name collision
        if os.path.exists(dest_path):
            stem, sfx = os.path.splitext(info["name"])
            dest_path = os.path.join(dest_dir, f"{stem}_{i}{sfx}")

        row: Dict[str, Any] = {
            "src": info["path"],
            "dst": dest_path,
            "folder": folder,
            "size": info["size"],
            "ext": info["ext"],
            "drive": info["drive"],
            "lane": None,
            "lit_score": 0.0,
            "ev_value": "none",
        }

        if analyze and info["size"] < MAX_ANALYZE_SIZE and folder in TEXT_FOLDERS:
            preview = read_content_preview(info["path"])
            if preview:
                row["lane"] = detect_meek_lane(info["path"], preview)
                entities = extract_entities(preview)
                row["lit_score"], row["ev_value"] = score_litigation(
                    preview, entities, info["ext"]
                )
                # Override folder if content is clearly legal
                if row["lit_score"] >= 5.0 and folder in ("TXT", "MD", "_UNKNOWN"):
                    row["folder"] = "LEGAL"
                    dest_dir = os.path.join(dest_root, "LEGAL")
                    dest_path = os.path.join(dest_dir, info["name"])
                    row["dst"] = dest_path
        else:
            row["lane"] = detect_meek_lane(info["path"])

        plan.append(row)

    elapsed = time.perf_counter() - t0
    log.info(
        "Plan: %d files in %.1fs — %s",
        len(plan), elapsed,
        " | ".join(f"{k}:{v}" for k, v in sorted(stats.items()) if v > 0),
    )
    return plan

def save_plan_csv(plan: List[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "src", "dst", "folder", "size", "ext", "drive", "lane", "lit_score", "ev_value"
        ])
        writer.writeheader()
        writer.writerows(plan)
    log.info("Plan saved → %s (%d rows)", path, len(plan))

def load_plan_csv(path: Path) -> List[Dict[str, Any]]:
    plan = []
    with open(path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            plan.append(row)
    log.info("Loaded plan: %d rows from %s", len(plan), path)
    return plan

# ─────────────────────────────────────────────────────────────────────────────
# JSONL audit ledger
# ─────────────────────────────────────────────────────────────────────────────

def write_ledger(entry: Dict[str, Any]) -> None:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

# ─────────────────────────────────────────────────────────────────────────────
# Checkpoint (crash-resume)
# ─────────────────────────────────────────────────────────────────────────────

def load_checkpoint() -> Dict[str, Any]:
    if CHECKPOINT_PATH.exists():
        try:
            with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_checkpoint(data: Dict[str, Any]) -> None:
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(CHECKPOINT_PATH) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, CHECKPOINT_PATH)

# ─────────────────────────────────────────────────────────────────────────────
# Apply plan (execute moves)
# ─────────────────────────────────────────────────────────────────────────────

def apply_plan(plan: List[Dict[str, Any]], resume_from: int = 0) -> Dict[str, int]:
    """Move files according to plan with ledger + checkpoint recovery."""
    moved = 0
    skipped = 0
    errors = 0
    t0 = time.perf_counter()

    for i, row in enumerate(plan):
        if i < resume_from:
            continue
        src = row["src"]
        dst = row["dst"]

        if not os.path.exists(src):
            write_ledger({"op": "skip", "reason": "src_missing", "src": src, "ts": time.time()})
            skipped += 1
            continue

        if is_protected(src):
            write_ledger({"op": "skip", "reason": "protected", "src": src, "ts": time.time()})
            skipped += 1
            continue

        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            # Avoid clobbering if dst already exists
            if os.path.exists(dst):
                stem, sfx = os.path.splitext(os.path.basename(dst))
                dst = os.path.join(os.path.dirname(dst), f"{stem}_{i}{sfx}")
                row["dst"] = dst  # update for ledger
            shutil.move(src, dst)
            write_ledger({"op": "move", "src": src, "dst": dst, "ts": time.time()})
            moved += 1
        except OSError as e:
            write_ledger({"op": "error", "src": src, "dst": dst, "err": str(e), "ts": time.time()})
            errors += 1
            log.warning("Move failed: %s → %s: %s", src, dst, e)

        if (i + 1) % CHECKPOINT_INTERVAL == 0:
            save_checkpoint({"resume_from": i + 1, "moved": moved, "errors": errors})
            elapsed = time.perf_counter() - t0
            log.info(
                "Progress: %d/%d — moved=%d errors=%d (%.1fs)",
                i + 1, len(plan), moved, errors, elapsed,
            )

    save_checkpoint({"resume_from": len(plan), "moved": moved, "errors": errors, "done": True})
    elapsed = time.perf_counter() - t0
    log.info(
        "Apply complete: moved=%d skipped=%d errors=%d in %.1fs",
        moved, skipped, errors, elapsed,
    )
    return {"moved": moved, "skipped": skipped, "errors": errors}

# ─────────────────────────────────────────────────────────────────────────────
# 3-Phase Deduplication (from OMEGA-FLATTEN deduplicator.py)
# ─────────────────────────────────────────────────────────────────────────────

def _content_similarity(path_a: str, path_b: str) -> float:
    """SequenceMatcher similarity between two text files (first 4096 bytes each)."""
    try:
        text_a = read_content_preview(path_a, 4096)
        text_b = read_content_preview(path_b, 4096)
        if not text_a or not text_b:
            return 0.0
        return SequenceMatcher(None, text_a, text_b).ratio()
    except Exception:
        return 0.0

def _name_similarity(stem_a: str, stem_b: str) -> float:
    return SequenceMatcher(None, stem_a.lower(), stem_b.lower()).ratio()

def run_dedup(roots: List[str], dry_run: bool = True) -> Dict[str, int]:
    """
    3-Phase dedup across roots.
    Phase 1: SHA-256 exact duplicates
    Phase 2: SequenceMatcher content similarity ≥ 0.85 (text files < 1 MB)
    Phase 3: Size + filename stem similarity ≥ 0.80

    Canonical: largest file. Dupes moved to {drive}:\\_DEDUP\\  (NEVER deleted).
    """
    log.info("Dedup: scanning %d roots …", len(roots))

    # Index: (path, size, ext, sha256) for all files
    file_records: List[Dict[str, Any]] = []
    t0 = time.perf_counter()
    for root in roots:
        for info in scan_root(root):
            file_records.append(info)

    log.info("Dedup: indexed %d files in %.1fs", len(file_records), time.perf_counter() - t0)

    # ── Phase 1: SHA-256 exact duplicates ──────────────────────────────────
    log.info("Dedup Phase 1: SHA-256 exact matches …")
    sha_index: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    deduped_ids: set = set()

    for rec in file_records:
        sha = sha256_file(rec["path"])
        if sha:
            rec["sha256"] = sha
            sha_index[sha].append(rec)

    phase1_clusters = 0
    phase1_dupes = 0
    for sha, group in sha_index.items():
        if len(group) < 2:
            continue
        # Canonical = largest file
        canonical = max(group, key=lambda r: r["size"])
        dupes = [r for r in group if r["path"] != canonical["path"]]
        for dupe in dupes:
            deduped_ids.add(dupe["path"])
            if not dry_run:
                _move_to_dedup(dupe["path"])
            write_ledger({
                "op": "dedup_p1", "canonical": canonical["path"],
                "dupe": dupe["path"], "sha": sha, "dry_run": dry_run,
                "ts": time.time(),
            })
        phase1_clusters += 1
        phase1_dupes += len(dupes)
    log.info("Phase 1: %d clusters, %d duplicates", phase1_clusters, phase1_dupes)

    # ── Phase 2: Content similarity (text files < 1 MB) ──────────────────
    log.info("Dedup Phase 2: content similarity (SequenceMatcher ≥ %.2f) …",
             DEDUP_SIMILARITY_THRESHOLD)
    TEXT_EXTS = frozenset({".txt", ".md", ".json", ".csv", ".html", ".xml",
                           ".py", ".js", ".ts", ".sql", ".log", ".rtf"})
    text_recs = [
        r for r in file_records
        if r["ext"] in TEXT_EXTS
        and r["size"] < 1_000_000
        and r["path"] not in deduped_ids
    ]

    # Group by size bucket (only compare files within 3× size range)
    phase2_clusters = 0
    phase2_dupes = 0
    text_recs.sort(key=lambda r: r["size"])
    compared = set()
    for i, rec_a in enumerate(text_recs):
        if rec_a["path"] in deduped_ids:
            continue
        for j in range(i + 1, len(text_recs)):
            rec_b = text_recs[j]
            if rec_b["path"] in deduped_ids:
                continue
            # Size bucket: max 3× ratio
            if rec_b["size"] > rec_a["size"] * 3:
                break
            pair = (min(rec_a["path"], rec_b["path"]), max(rec_a["path"], rec_b["path"]))
            if pair in compared:
                continue
            compared.add(pair)
            sim = _content_similarity(rec_a["path"], rec_b["path"])
            if sim >= DEDUP_SIMILARITY_THRESHOLD:
                canonical = rec_a if rec_a["size"] >= rec_b["size"] else rec_b
                dupe = rec_b if canonical is rec_a else rec_a
                deduped_ids.add(dupe["path"])
                if not dry_run:
                    _move_to_dedup(dupe["path"])
                write_ledger({
                    "op": "dedup_p2", "canonical": canonical["path"],
                    "dupe": dupe["path"], "similarity": round(sim, 3),
                    "dry_run": dry_run, "ts": time.time(),
                })
                phase2_clusters += 1
                phase2_dupes += 1
    log.info("Phase 2: %d clusters, %d duplicates", phase2_clusters, phase2_dupes)

    # ── Phase 3: Size + filename stem similarity ──────────────────────────
    log.info("Dedup Phase 3: size + stem similarity (≥ %.2f) …", DEDUP_NAME_THRESHOLD)
    size_groups: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for rec in file_records:
        if rec["path"] not in deduped_ids:
            size_groups[rec["size"]].append(rec)

    phase3_clusters = 0
    phase3_dupes = 0
    for size, group in size_groups.items():
        if len(group) < 2 or len(group) > 20:
            continue
        processed = set()
        for i, rec_a in enumerate(group):
            if rec_a["path"] in processed or rec_a["path"] in deduped_ids:
                continue
            stem_a = os.path.splitext(rec_a["name"])[0]
            for rec_b in group[i + 1:]:
                if rec_b["path"] in processed or rec_b["path"] in deduped_ids:
                    continue
                stem_b = os.path.splitext(rec_b["name"])[0]
                if _name_similarity(stem_a, stem_b) >= DEDUP_NAME_THRESHOLD:
                    canonical = rec_a
                    dupe = rec_b
                    processed.add(dupe["path"])
                    deduped_ids.add(dupe["path"])
                    if not dry_run:
                        _move_to_dedup(dupe["path"])
                    write_ledger({
                        "op": "dedup_p3", "canonical": canonical["path"],
                        "dupe": dupe["path"], "size": size,
                        "stem_a": stem_a, "stem_b": stem_b,
                        "dry_run": dry_run, "ts": time.time(),
                    })
                    phase3_clusters += 1
                    phase3_dupes += 1

    log.info("Phase 3: %d clusters, %d duplicates", phase3_clusters, phase3_dupes)

    total_dupes = phase1_dupes + phase2_dupes + phase3_dupes
    log.info(
        "Dedup COMPLETE: %d total duplicates (P1=%d P2=%d P3=%d) — dry_run=%s",
        total_dupes, phase1_dupes, phase2_dupes, phase3_dupes, dry_run,
    )
    return {
        "total_files": len(file_records),
        "phase1_dupes": phase1_dupes,
        "phase2_dupes": phase2_dupes,
        "phase3_dupes": phase3_dupes,
        "total_dupes": total_dupes,
    }

def _move_to_dedup(path: str) -> None:
    """Move a duplicate to {drive}:\\_DEDUP\\{folder}\\ (NEVER delete)."""
    drive = os.path.splitdrive(path)[0]  # e.g. "C:"
    folder = os.path.basename(os.path.dirname(path))
    dedup_dir = os.path.join(drive, os.sep, "_DEDUP", folder)
    os.makedirs(dedup_dir, exist_ok=True)
    dst = os.path.join(dedup_dir, os.path.basename(path))
    if os.path.exists(dst):
        stem, sfx = os.path.splitext(os.path.basename(path))
        dst = os.path.join(dedup_dir, f"{stem}_{int(time.time())}{sfx}")
    try:
        shutil.move(path, dst)
    except OSError as e:
        log.warning("Dedup move failed: %s → %s: %s", path, dst, e)

# ─────────────────────────────────────────────────────────────────────────────
# DB Sync — update file_inventory in litigation_context.db
# ─────────────────────────────────────────────────────────────────────────────

def sync_to_db(plan: List[Dict[str, Any]]) -> int:
    """Update file_inventory in litigation_context.db for moved files."""
    if not LITIGATION_DB.exists():
        log.warning("litigation_context.db not found at %s — skipping DB sync", LITIGATION_DB)
        return 0
    try:
        conn = sqlite3.connect(str(LITIGATION_DB))
        conn.execute("PRAGMA busy_timeout=60000")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA cache_size=-32000")
        # Check if file_inventory table exists
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        if "file_inventory" not in tables:
            log.warning("file_inventory table not found in litigation_context.db")
            conn.close()
            return 0
        updated = 0
        batch = []
        for row in plan:
            batch.append((row["dst"], row["src"]))
            if len(batch) >= BATCH_SIZE:
                conn.executemany(
                    "UPDATE file_inventory SET file_path = ? WHERE file_path = ?",
                    batch,
                )
                updated += conn.total_changes
                conn.commit()
                batch.clear()
        if batch:
            conn.executemany(
                "UPDATE file_inventory SET file_path = ? WHERE file_path = ?",
                batch,
            )
            updated += conn.total_changes
            conn.commit()
        conn.close()
        log.info("DB sync: updated %d file_inventory rows", updated)
        return updated
    except sqlite3.Error as e:
        log.error("DB sync error: %s", e)
        return 0

# ─────────────────────────────────────────────────────────────────────────────
# Watch mode (real-time via watchdog)
# ─────────────────────────────────────────────────────────────────────────────

def run_watch(root: str, dest_root: str) -> None:
    """Monitor root for new files and organize them on arrival."""
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        log.error("watchdog not installed. Run: pip install watchdog")
        sys.exit(1)

    class OrganizerHandler(FileSystemEventHandler):
        def on_created(self, event):
            if event.is_directory:
                return
            path = event.src_path
            if is_protected(path):
                return
            time.sleep(0.5)  # wait for file to finish writing
            try:
                size = os.path.getsize(path)
            except OSError:
                return
            folder = classify_file(path, size)
            dest_dir = os.path.join(dest_root, folder)
            os.makedirs(dest_dir, exist_ok=True)
            dst = os.path.join(dest_dir, os.path.basename(path))
            if os.path.exists(dst):
                stem, sfx = os.path.splitext(os.path.basename(path))
                dst = os.path.join(dest_dir, f"{stem}_{int(time.time())}{sfx}")
            try:
                shutil.move(path, dst)
                write_ledger({"op": "watch_move", "src": path, "dst": dst, "ts": time.time()})
                log.info("WATCH: %s → %s/%s", os.path.basename(path), folder, os.path.basename(dst))
            except OSError as e:
                log.warning("WATCH move failed: %s", e)

    observer = Observer()
    observer.schedule(OrganizerHandler(), root, recursive=True)
    observer.start()
    log.info("Watching %s → %s (Ctrl+C to stop)", root, dest_root)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=f"LitigationOS Unified Apex Organizer v{__version__}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview plan (no moves):
  python -I %(prog)s --scan I:\\ --dest I:\\_ORGANIZED --plan

  # Execute plan:
  python -I %(prog)s --scan I:\\ --dest I:\\_ORGANIZED --apply

  # Resume after crash:
  python -I %(prog)s --resume

  # Apply a saved plan.csv:
  python -I %(prog)s --apply-existing

  # Dedup only:
  python -I %(prog)s --dedup I:\\ D:\\

  # Watch mode:
  python -I %(prog)s --watch I:\\ --dest I:\\_ORGANIZED

  # Plan + analyze (litigation scoring):
  python -I %(prog)s --scan I:\\ --dest I:\\_ORGANIZED --plan --analyze
""",
    )
    p.add_argument("--scan", metavar="ROOT", help="Root directory to scan")
    p.add_argument("--dest", metavar="DEST", help="Destination root for organized folders")
    p.add_argument("--plan", action="store_true", help="Generate plan CSV only (no moves)")
    p.add_argument("--apply", action="store_true", help="Scan and apply moves")
    p.add_argument("--apply-existing", action="store_true",
                   help=f"Apply an existing plan CSV at {PLAN_CSV_PATH}")
    p.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    p.add_argument("--dedup", nargs="+", metavar="ROOT",
                   help="Run 3-phase dedup on one or more roots")
    p.add_argument("--dedup-apply", action="store_true",
                   help="Actually move dupes (default is dry-run)")
    p.add_argument("--watch", metavar="ROOT", help="Watch ROOT for new files (real-time organize)")
    p.add_argument("--max-files", type=int, default=None,
                   help="Limit files scanned (for testing)")
    p.add_argument("--analyze", action="store_true",
                   help="Score litigation relevance during plan (slower)")
    p.add_argument("--sync-db", action="store_true",
                   help="Update file_inventory in litigation_context.db after moves")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # ── Watch mode ──────────────────────────────────────────────────────────
    if args.watch:
        dest = args.dest or os.path.join(args.watch, "_ORGANIZED")
        run_watch(args.watch, dest)
        return

    # ── Dedup ────────────────────────────────────────────────────────────────
    if args.dedup:
        result = run_dedup(args.dedup, dry_run=not args.dedup_apply)
        print(json.dumps(result, indent=2))
        return

    # ── Resume from checkpoint ────────────────────────────────────────────
    if args.resume:
        ckpt = load_checkpoint()
        if not ckpt:
            log.error("No checkpoint found at %s", CHECKPOINT_PATH)
            sys.exit(1)
        resume_from = ckpt.get("resume_from", 0)
        log.info("Resuming from op %d …", resume_from)
        plan = load_plan_csv(PLAN_CSV_PATH)
        result = apply_plan(plan, resume_from=resume_from)
        if args.sync_db:
            sync_to_db(plan)
        print(json.dumps(result, indent=2))
        return

    # ── Apply existing plan CSV ───────────────────────────────────────────
    if args.apply_existing:
        plan = load_plan_csv(PLAN_CSV_PATH)
        result = apply_plan(plan)
        if args.sync_db:
            sync_to_db(plan)
        print(json.dumps(result, indent=2))
        return

    # ── Scan required for plan/apply ─────────────────────────────────────
    if not args.scan:
        parser.print_help()
        sys.exit(1)

    if not args.dest:
        # Default: create _ORGANIZED in the scanned root
        drive = os.path.splitdrive(args.scan)[0]
        args.dest = os.path.join(drive, os.sep, "_ORGANIZED")
        log.info("No --dest specified; using %s", args.dest)

    if args.plan:
        plan = generate_plan(args.scan, args.dest, args.max_files, analyze=args.analyze)
        save_plan_csv(plan, PLAN_CSV_PATH)
        # Print summary
        folders: Dict[str, int] = defaultdict(int)
        for row in plan:
            folders[row["folder"]] += 1
        total = len(plan)
        total_size = sum(r.get("size", 0) for r in plan)
        print(f"\n{'─'*60}")
        print(f"  Plan: {total:,} files ({total_size / 1e9:.2f} GB)")
        print(f"  Saved → {PLAN_CSV_PATH}")
        print(f"{'─'*60}")
        for folder, count in sorted(folders.items(), key=lambda x: -x[1]):
            print(f"  {folder:<12} {count:>8,}")
        print(f"{'─'*60}")
        if args.analyze:
            high = sum(1 for r in plan if r.get("ev_value") == "high")
            med = sum(1 for r in plan if r.get("ev_value") == "medium")
            print(f"  HIGH evidence: {high:,}  MEDIUM: {med:,}")
            print(f"{'─'*60}")
        print("\nRun with --apply to execute moves.")
        return

    if args.apply:
        plan = generate_plan(args.scan, args.dest, args.max_files, analyze=args.analyze)
        save_plan_csv(plan, PLAN_CSV_PATH)
        result = apply_plan(plan)
        if args.sync_db:
            sync_to_db(plan)
        print(json.dumps(result, indent=2))
        return

    parser.print_help()

if __name__ == "__main__":
    main()

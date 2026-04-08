"""Filing QA Gate — Decontamination sweeps and validation checks.

Ensures court filings are free of AI/DB artifacts, hallucinations,
stale dates, generic placeholders, and rule violations before submission.
"""

import re
import logging
from datetime import date

logger = logging.getLogger(__name__)

# ── Hallucination Blacklist (Rule 3 + anti-hallucination protocol) ──────────

HALLUCINATION_BLACKLIST: list[str] = [
    "Jane Berry",
    "Patricia Berry",
    "P35878",
    "91% alienation",
    "Ron Berry, Esq",
    "Ron Berry Esq",
    "Amy McNeill",
    "Emily Ann Watson",
    "Emily M. Watson",
    "Watson-Pigors",
    "undersigned counsel",
    "attorney for Plaintiff",
    "attorney for plaintiff",
    "counsel for Plaintiff",
]

# Child's full name variants — NEVER in filings (MCR 8.119(H))
_CHILD_NAME_PATTERNS: list[re.Pattern] = [
    re.compile(r"Lincoln\s+David", re.IGNORECASE),
    re.compile(r"Lincoln\s+D\.\s+Watson", re.IGNORECASE),
    re.compile(r"Lincoln\s+Watson", re.IGNORECASE),
    re.compile(r"L\.D\.\s+Watson", re.IGNORECASE),
]

# ── AI / DB Contamination Patterns (Rule 3 — ONE HIT = FAIL) ───────────────

AI_CONTAMINATION_PATTERNS: list[str] = [
    "LitigationOS",
    "MANBEARPIG",
    "EGCP",
    "SINGULARITY",
    "MEEK",
    "evidence_quotes",
    "authority_chains",
    "impeachment_matrix",
    "litigation_context",
    "mbp_brain",
    "nexus_daemon",
    "LOCUS",
    "FTS5",
    "NEXUS",
    "daemon",
    "brain.db",
    "file_inventory",
    "timeline_fts",
    "evidence_fts",
    "md_sections",
    "DuckDB",
    "LanceDB",
    "tantivy",
    "Polars",
    "orjson",
    "pypdfium2",
    "sentence-transformers",
]

# Path patterns that should never appear in court filings
_PATH_PATTERNS: list[re.Pattern] = [
    re.compile(r"C:\\Users\\andre", re.IGNORECASE),
    re.compile(r"D:\\LitigationOS", re.IGNORECASE),
    re.compile(r"00_SYSTEM", re.IGNORECASE),
    re.compile(r"09_REFERENCE", re.IGNORECASE),
    re.compile(r"04_ANALYSIS", re.IGNORECASE),
    re.compile(r"12_WORKSPACE", re.IGNORECASE),
    re.compile(r"\.github[/\\]", re.IGNORECASE),
]

# ── Placeholder Patterns (unresolved content markers) ───────────────────────

PLACEHOLDER_PATTERNS: list[re.Pattern] = [
    re.compile(r"\[ANDREW_REQUIRED[^\]]*\]"),
    re.compile(r"\[VERIFY[^\]]*\]"),
    re.compile(r"\[COMPUTE[^\]]*\]"),
    re.compile(r"\[INSERT[^\]]*\]"),
    re.compile(r"\[TBD[^\]]*\]"),
    re.compile(r"\[PLACEHOLDER[^\]]*\]"),
    re.compile(r"\[TODO[^\]]*\]"),
    re.compile(r"\[ATTACH[^\]]*\]"),
]

# ── Stale Year Detection ───────────────────────────────────────────────────

_STALE_YEAR_PATTERN = re.compile(
    r"(?:dated|filed|date|january|february|march|april|may|june|july|august|"
    r"september|october|november|december)\s+\d{1,2},?\s+(202[0-5])",
    re.IGNORECASE,
)


# ── Public Interface ────────────────────────────────────────────────────────

def decontaminate(text: str) -> str:
    """Strip ALL AI/DB references from filing text (Rule 3).

    Replaces contamination strings with empty string.
    Raises ValueError if any contamination persists after cleaning.
    """
    cleaned = text

    for pattern in AI_CONTAMINATION_PATTERNS:
        cleaned = cleaned.replace(pattern, "")

    for regex in _PATH_PATTERNS:
        cleaned = regex.sub("", cleaned)

    # Verify no residual contamination
    remaining = _find_contamination(cleaned)
    if remaining:
        raise ValueError(
            f"Decontamination FAILED — residual contamination found: "
            f"{remaining[:5]}"
        )
    return cleaned


def validate(content: str) -> tuple[bool, list[str]]:
    """Run all QA checks on filing content.

    Returns:
        (passed, issues) — passed is True only when zero issues found.
    """
    issues: list[str] = []

    # 1. Hallucination check
    for banned in HALLUCINATION_BLACKLIST:
        if banned.lower() in content.lower():
            issues.append(f"HALLUCINATION: '{banned}' found in content")

    # 2. Child full name check (MCR 8.119(H))
    for pat in _CHILD_NAME_PATTERNS:
        match = pat.search(content)
        if match:
            issues.append(
                f"CHILD NAME VIOLATION: '{match.group()}' — must use L.D.W. only"
            )

    # 3. AI/DB contamination check (Rule 3)
    contamination = _find_contamination(content)
    for item in contamination:
        issues.append(f"AI CONTAMINATION: '{item}' found — must be removed")

    # 4. Placeholder check
    for pat in PLACEHOLDER_PATTERNS:
        matches = pat.findall(content)
        for m in matches:
            issues.append(f"UNRESOLVED PLACEHOLDER: {m}")

    # 5. Stale year check
    stale_years = _STALE_YEAR_PATTERN.findall(content)
    for year in stale_years:
        if int(year) < 2026:
            issues.append(
                f"STALE YEAR: '{year}' found in date context — must be 2026"
            )

    # 6. Pro se compliance (Rule 4)
    pro_se_violations = [
        "undersigned counsel",
        "attorney for plaintiff",
        "counsel for plaintiff",
        "attorney for the plaintiff",
    ]
    for phrase in pro_se_violations:
        if phrase.lower() in content.lower():
            issues.append(
                f"PRO SE VIOLATION: '{phrase}' found — "
                f"use 'Plaintiff, appearing pro se'"
            )

    # 7. Judge name check (Rule 6 — TWO L's)
    if re.search(r"McNeil\b", content) and not re.search(r"McNeill\b", content):
        issues.append(
            "JUDGE NAME ERROR: 'McNeil' (one L) found — "
            "must be 'McNeill' (TWO L's)"
        )

    # 8. Hardcoded separation day count (Rule 29)
    sep_day_patterns = re.findall(
        r"(\d{3,})\s*days?\s*(?:of\s+)?(?:separation|since\s+last\s+contact|"
        r"without\s+(?:seeing|contact))",
        content,
        re.IGNORECASE,
    )
    for count in sep_day_patterns:
        issues.append(
            f"HARDCODED DAY COUNT: '{count} days' — "
            f"must be computed dynamically at render time (Rule 29)"
        )

    passed = len(issues) == 0
    if not passed:
        logger.warning(
            "QA GATE FAILED: %d issue(s) found", len(issues)
        )
    else:
        logger.info("QA GATE PASSED — filing content is clean")

    return passed, issues


# ── Internal Helpers ────────────────────────────────────────────────────────

def _find_contamination(text: str) -> list[str]:
    """Return list of AI/DB contamination strings found in text."""
    found: list[str] = []
    text_lower = text.lower()

    for pattern in AI_CONTAMINATION_PATTERNS:
        if pattern.lower() in text_lower:
            found.append(pattern)

    for regex in _PATH_PATTERNS:
        if regex.search(text):
            found.append(regex.pattern)

    return found

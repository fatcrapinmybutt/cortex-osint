"""
LitigationOS Typst Filing Engine
Generates court-ready PDFs from database content using Typst templates.
"""

import json
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional


TEMPLATE_DIR = Path(__file__).parent / "templates"
TYPST_BIN = shutil.which("typst") or str(Path.home() / ".cargo" / "bin" / "typst.exe")

CHILD_NAME_PATTERN = re.compile(
    r"\b(?:Lincoln\s+(?:Dean\s+)?(?:Watson|Pigors|Watson[- ]Pigors))\b",
    re.IGNORECASE,
)


@dataclass
class FilingMetadata:
    case_number: str = "2024-001507-DC"
    court: str = "14TH JUDICIAL CIRCUIT COURT"
    county: str = "MUSKEGON COUNTY"
    judge: str = "HON. JENNY L. McNEILL"
    plaintiff: str = "ANDREW JAMES PIGORS"
    defendant: str = "EMILY A. WATSON"
    document_title: str = ""
    filing_date: str = ""


@dataclass
class ServiceParty:
    name: str
    address: str


DEFAULT_SERVICE_PARTIES = [
    ServiceParty("Emily A. Watson", "2160 Garland Dr, Norton Shores, MI 49441"),
    ServiceParty("Muskegon County FOC", "990 Terrace St, Muskegon, MI 49442"),
]


def sanitize_child_name(text: str) -> str:
    """Replace child's full name with L.D.W. per MCR 8.119(H)."""
    return CHILD_NAME_PATTERN.sub("L.D.W.", text)


def escape_typst(text: str) -> str:
    """Escape special Typst characters in user content."""
    replacements = {
        "#": "\\#",
        "$": "\\$",
        "@": "\\@",
        "<": "\\<",
        ">": "\\>",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _get_db_connection(db_path: str) -> sqlite3.Connection:
    """Open SQLite connection with mandatory PRAGMAs."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA cache_size = -32000")
    return conn


def compute_separation_days() -> int:
    """Compute days since last contact with L.D.W. (July 29, 2025)."""
    anchor = date(2025, 7, 29)
    return (date.today() - anchor).days


class TypstFilingEngine:
    """Generates court-ready filings using Typst templates."""

    def __init__(self, db_path: str = "litigation_context.db"):
        self.db_path = db_path
        self.template_dir = TEMPLATE_DIR

    def generate_motion(
        self,
        title: str,
        body_sections: list[dict],
        relief_requested: list[str],
        metadata: Optional[FilingMetadata] = None,
        service_parties: Optional[list[ServiceParty]] = None,
        output_path: Optional[str] = None,
    ) -> str:
        """Generate a motion PDF from structured content.

        Args:
            title: Document title (e.g., "Motion to Restore Parenting Time")
            body_sections: List of {heading: str, paragraphs: list[str]}
            relief_requested: List of relief items
            metadata: Filing metadata (defaults to Lane A custody case)
            service_parties: Parties for certificate of service
            output_path: Where to save the PDF (auto-generated if None)

        Returns:
            Path to generated PDF
        """
        meta = metadata or FilingMetadata()
        meta.document_title = title
        if not meta.filing_date:
            meta.filing_date = datetime.now().strftime("%B %d, %Y")

        parties = service_parties or DEFAULT_SERVICE_PARTIES

        typst_content = self._build_motion_typst(meta, body_sections, relief_requested, parties)
        return self._compile(typst_content, output_path or self._default_output_path(title))

    def generate_brief(
        self,
        title: str,
        issues: list[dict],
        metadata: Optional[FilingMetadata] = None,
        output_path: Optional[str] = None,
    ) -> str:
        """Generate a brief with IRAC analysis sections.

        Args:
            title: Brief title
            issues: List of {issue, rule, application, conclusion}
            metadata: Filing metadata
            output_path: Where to save PDF

        Returns:
            Path to generated PDF
        """
        meta = metadata or FilingMetadata()
        meta.document_title = title
        if not meta.filing_date:
            meta.filing_date = datetime.now().strftime("%B %d, %Y")

        typst_content = self._build_brief_typst(meta, issues)
        return self._compile(typst_content, output_path or self._default_output_path(title))

    def get_evidence_for_claim(self, claim: str, limit: int = 20) -> list[dict]:
        """Query evidence_quotes for a specific claim/topic."""
        conn = _get_db_connection(self.db_path)
        try:
            query = re.sub(r"[^\w\s*\"]", " ", claim)
            try:
                rows = conn.execute(
                    """SELECT id, quote_text, source_file, page_number, category
                       FROM evidence_quotes
                       WHERE id IN (
                           SELECT rowid FROM evidence_fts WHERE evidence_fts MATCH ?
                       )
                       LIMIT ?""",
                    (query, limit),
                ).fetchall()
            except Exception:
                rows = conn.execute(
                    """SELECT id, quote_text, source_file, page_number, category
                       FROM evidence_quotes
                       WHERE quote_text LIKE '%' || ? || '%'
                       LIMIT ?""",
                    (claim, limit),
                ).fetchall()
            return [
                {
                    "id": r[0],
                    "text": sanitize_child_name(r[1]) if r[1] else "",
                    "source": r[2] or "",
                    "page": r[3],
                    "category": r[4] or "",
                }
                for r in rows
            ]
        finally:
            conn.close()

    def get_authorities_for_claim(self, claim: str, limit: int = 15) -> list[dict]:
        """Query authority_chains_v2 for supporting citations."""
        conn = _get_db_connection(self.db_path)
        try:
            rows = conn.execute(
                """SELECT primary_citation, supporting_citation, relationship, paragraph_context
                   FROM authority_chains_v2
                   WHERE primary_citation LIKE '%' || ? || '%'
                      OR supporting_citation LIKE '%' || ? || '%'
                      OR paragraph_context LIKE '%' || ? || '%'
                   LIMIT ?""",
                (claim, claim, claim, limit),
            ).fetchall()
            return [
                {
                    "primary": r[0] or "",
                    "supporting": r[1] or "",
                    "relationship": r[2] or "",
                    "context": sanitize_child_name(r[3]) if r[3] else "",
                }
                for r in rows
            ]
        finally:
            conn.close()

    def _build_motion_typst(
        self,
        meta: FilingMetadata,
        sections: list[dict],
        relief: list[str],
        parties: list[ServiceParty],
    ) -> str:
        lines = [
            f'#import "michigan-court.typ": michigan-court, signature-block, certificate-of-service, numbered-paragraphs',
            "",
            "#show: michigan-court.with(",
            f'  case-number: "{meta.case_number}",',
            f'  court: "{meta.court}",',
            f'  county: "{meta.county}",',
            f'  judge: "{meta.judge}",',
            f'  plaintiff: "{meta.plaintiff}",',
            f'  defendant: "{meta.defendant}",',
            f'  document-title: "{escape_typst(meta.document_title)}",',
            ")",
            "",
            f'#text(weight: "bold")[NOW COMES] Plaintiff, {meta.plaintiff}, appearing _pro se_, and respectfully moves this Honorable Court as follows:',
            "",
        ]

        for section in sections:
            heading = section.get("heading", "")
            paragraphs = section.get("paragraphs", [])
            lines.append(f"== {heading.upper()}")
            lines.append("")
            if paragraphs:
                lines.append("#numbered-paragraphs(")
                for p in paragraphs:
                    safe = sanitize_child_name(escape_typst(p))
                    lines.append(f"  [{safe}],")
                lines.append(")")
                lines.append("")

        lines.append("== RELIEF REQUESTED")
        lines.append("")
        lines.append("WHEREFORE, Plaintiff respectfully requests that this Court:")
        lines.append("")
        lines.append("#numbered-paragraphs(")
        for r in relief:
            safe = sanitize_child_name(escape_typst(r))
            lines.append(f"  [{safe}],")
        lines.append(")")
        lines.append("")
        lines.append(f'#signature-block(date: "{meta.filing_date}")')
        lines.append("")

        party_strs = ", ".join(
            f'(name: "{p.name}", address: "{p.address}")' for p in parties
        )
        lines.append("#certificate-of-service(")
        lines.append(f'  date: "{meta.filing_date}",')
        lines.append(f"  parties: ({party_strs},),")
        lines.append(")")

        return "\n".join(lines)

    def _build_brief_typst(self, meta: FilingMetadata, issues: list[dict]) -> str:
        lines = [
            f'#import "michigan-court.typ": michigan-court, signature-block, certificate-of-service, irac-section',
            "",
            "#show: michigan-court.with(",
            f'  case-number: "{meta.case_number}",',
            f'  document-title: "{escape_typst(meta.document_title)}",',
            ")",
            "",
        ]

        for i, issue in enumerate(issues, 1):
            lines.append(f"== ISSUE {i}")
            lines.append("")
            lines.append("#irac-section(")
            for key in ("issue", "rule", "application", "conclusion"):
                val = sanitize_child_name(escape_typst(issue.get(key, "")))
                lines.append(f'  {key}: [{val}],')
            lines.append(")")
            lines.append("")

        lines.append(f'#signature-block(date: "{meta.filing_date}")')
        return "\n".join(lines)

    def _compile(self, typst_content: str, output_path: str) -> str:
        """Compile Typst source to PDF."""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".typ", dir=str(self.template_dir),
            delete=False, encoding="utf-8",
        ) as f:
            f.write(typst_content)
            temp_path = f.name

        try:
            result = subprocess.run(
                [TYPST_BIN, "compile", temp_path, str(output)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Typst compilation failed: {result.stderr}")
            return str(output)
        finally:
            os.unlink(temp_path)

    def _default_output_path(self, title: str) -> str:
        safe = re.sub(r"[^\w\s-]", "", title).strip().replace(" ", "_")
        return str(Path("05_FILINGS") / f"{safe}_{date.today().isoformat()}.pdf")

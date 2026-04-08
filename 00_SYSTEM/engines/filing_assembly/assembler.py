"""Autonomous Filing Assembly Engine — end-to-end packet generation.

Takes a filing lane (F1-F10 or A-F) and produces a court-ready packet
family: motion + brief + affidavit + exhibit index + exhibits +
proposed order + MC 12 Certificate of Service.

Usage:
    from engines.filing_assembly import FilingAssembler

    fa = FilingAssembler()
    result = fa.assemble_packet("F7")
    print(result["manifest"])
"""

import logging
import os
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path

from .qa_gate import decontaminate, validate
from .templates import (
    COURT_FORMATS,
    DEFENDANT_ADDRESS,
    DEFENDANT_NAME,
    FOC_ADDRESS,
    FOC_NAME,
    JUDGE_NAME,
    PLAINTIFF_NAME,
    build_caption_text,
    get_court_format,
    render_cos,
    render_proposed_order,
    render_signature,
    render_verification,
    separation_days,
)

logger = logging.getLogger(__name__)

_DEFAULT_DB = Path(r"C:\Users\andre\LitigationOS\litigation_context.db")
_DEFAULT_OUTPUT = Path(r"C:\Users\andre\LitigationOS\05_FILINGS\ASSEMBLY_OUTPUT")

# ── FTS5 Safety (Rule 15) ──────────────────────────────────────────────────

def _sanitize_fts5(query: str) -> str:
    """Sanitize a query string for safe FTS5 MATCH usage."""
    return re.sub(r'[^\w\s*"]', " ", query).strip()


# ── Helpers ─────────────────────────────────────────────────────────────────

def _safe_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    """Return set of column names for *table* (Rule 16 — always verify)."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    """Check if a table exists in the database."""
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


# ════════════════════════════════════════════════════════════════════════════
# FilingAssembler
# ════════════════════════════════════════════════════════════════════════════

class FilingAssembler:
    """Autonomous court-ready packet generation engine.

    Connects lazily to litigation_context.db, queries evidence/authorities/
    impeachment, and assembles a complete packet family for the requested
    filing lane.
    """

    def __init__(self, db_path: str | Path | None = None):
        self._db_path = Path(db_path) if db_path else _DEFAULT_DB
        self._conn: sqlite3.Connection | None = None

    # ── Connection management ───────────────────────────────────────────

    @property
    def conn(self) -> sqlite3.Connection:
        """Lazy DB connection with mandatory PRAGMAs (Rule 18)."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA busy_timeout = 60000")
            self._conn.execute("PRAGMA journal_mode = WAL")
            self._conn.execute("PRAGMA cache_size = -32000")
            self._conn.execute("PRAGMA temp_store = MEMORY")
            self._conn.execute("PRAGMA synchronous = NORMAL")
            logger.info("Connected to %s with standard PRAGMAs", self._db_path)
        return self._conn

    def close(self) -> None:
        """Explicitly close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ── Filing Info ─────────────────────────────────────────────────────

    def get_filing_info(self, lane: str) -> dict:
        """Query filing_packages for lane metadata.

        Accepts F1-F10 or lane letter (A-F).
        """
        cols = _safe_columns(self.conn, "filing_packages")
        if not cols:
            logger.warning("filing_packages table has no columns or missing")
            return {"lane": lane, "title": "Unknown Filing", "case_number": ""}

        rows = self.conn.execute(
            "SELECT * FROM filing_packages WHERE lane = ? OR filing_id = ?",
            (lane, lane),
        ).fetchall()

        if not rows:
            logger.warning("No filing_packages row for lane=%s", lane)
            return {"lane": lane, "title": "Unknown Filing", "case_number": ""}

        row = rows[0]
        return {col: row[col] for col in cols if col in row.keys()}

    # ── Evidence Query ──────────────────────────────────────────────────

    def query_evidence(
        self,
        lane: str,
        keywords: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Query evidence_quotes for the given lane.

        Uses FTS5 with sanitize→try/except→LIKE fallback (Rule 15).
        """
        if not _table_exists(self.conn, "evidence_quotes"):
            logger.warning("evidence_quotes table missing")
            return []

        cols = _safe_columns(self.conn, "evidence_quotes")
        has_lane = "lane" in cols

        results: list[dict] = []

        # FTS5 path
        if keywords and _table_exists(self.conn, "evidence_fts"):
            safe_q = _sanitize_fts5(keywords)
            if safe_q:
                try:
                    sql = (
                        "SELECT eq.quote_text, eq.source_file, eq.page_number, "
                        "eq.category, eq.lane "
                        "FROM evidence_fts ef "
                        "JOIN evidence_quotes eq ON ef.rowid = eq.id "
                        "WHERE evidence_fts MATCH ? "
                    )
                    params: list = [safe_q]
                    if has_lane:
                        sql += "AND eq.lane = ? "
                        params.append(lane.strip().upper())
                    sql += "AND eq.is_duplicate = 0 "
                    sql += "ORDER BY rank LIMIT ?"
                    params.append(limit)
                    rows = self.conn.execute(sql, params).fetchall()
                    results = [dict(r) for r in rows]
                    if results:
                        return results
                except sqlite3.OperationalError as exc:
                    logger.warning("FTS5 failed (%s), falling back to LIKE", exc)

        # LIKE fallback
        sql_parts = [
            "SELECT quote_text, source_file, page_number, category, lane "
            "FROM evidence_quotes WHERE is_duplicate = 0"
        ]
        params_like: list = []

        if has_lane:
            sql_parts.append("AND lane = ?")
            params_like.append(lane.strip().upper())

        if keywords:
            words = keywords.split()
            for word in words[:5]:
                sql_parts.append("AND quote_text LIKE ?")
                params_like.append(f"%{word}%")

        sql_parts.append("ORDER BY relevance_score DESC LIMIT ?")
        params_like.append(limit)

        rows = self.conn.execute(" ".join(sql_parts), params_like).fetchall()
        return [dict(r) for r in rows]

    # ── Authority Query ─────────────────────────────────────────────────

    def query_authorities(self, topic: str, limit: int = 30) -> list[dict]:
        """Query authority_chains_v2 for citations related to *topic*."""
        if not _table_exists(self.conn, "authority_chains_v2"):
            logger.warning("authority_chains_v2 table missing")
            return []

        like_term = f"%{topic}%"
        rows = self.conn.execute(
            "SELECT primary_citation, supporting_citation, relationship, "
            "paragraph_context, lane "
            "FROM authority_chains_v2 "
            "WHERE primary_citation LIKE ? OR paragraph_context LIKE ? "
            "ORDER BY id DESC LIMIT ?",
            (like_term, like_term, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Impeachment Query ───────────────────────────────────────────────

    def query_impeachment(
        self,
        target: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """Query impeachment_matrix for cross-examination ammunition."""
        if not _table_exists(self.conn, "impeachment_matrix"):
            logger.warning("impeachment_matrix table missing")
            return []

        if target:
            like_target = f"%{target}%"
            rows = self.conn.execute(
                "SELECT category, evidence_summary, source_file, quote_text, "
                "impeachment_value, cross_exam_question, filing_relevance "
                "FROM impeachment_matrix "
                "WHERE evidence_summary LIKE ? OR quote_text LIKE ? "
                "ORDER BY impeachment_value DESC LIMIT ?",
                (like_target, like_target, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT category, evidence_summary, source_file, quote_text, "
                "impeachment_value, cross_exam_question, filing_relevance "
                "FROM impeachment_matrix "
                "ORDER BY impeachment_value DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Caption Builder ─────────────────────────────────────────────────

    def build_caption(self, filing_info: dict) -> str:
        """Generate the court caption block for a filing."""
        return build_caption_text(filing_info)

    # ── IRAC Section Builder ────────────────────────────────────────────

    @staticmethod
    def build_irac_section(
        issue: str,
        rule: str,
        application: str,
        conclusion: str,
    ) -> str:
        """Format an IRAC argument section."""
        lines = [
            "I. ISSUE",
            "",
            f"    {issue}",
            "",
            "R. RULE",
            "",
            f"    {rule}",
            "",
            "A. APPLICATION",
            "",
            f"    {application}",
            "",
            "C. CONCLUSION",
            "",
            f"    {conclusion}",
        ]
        return "\n".join(lines)

    # ── Certificate of Service ──────────────────────────────────────────

    def build_cos(
        self,
        filing_info: dict,
        service_date: date | None = None,
    ) -> str:
        """Generate MC 12 Certificate of Service.

        Barnes WITHDREW Mar 2026 — serve Emily Watson directly.
        Include FOC for custody/PT lanes (A, D).
        """
        title = filing_info.get("title", "Filing")
        lane = filing_info.get("lane", "A")
        include_foc = lane.upper() in ("A", "D", "F1", "F3", "F7", "F8")
        return render_cos(
            document_title=title,
            service_date=service_date,
            include_foc=include_foc,
        )

    # ── Exhibit Index ───────────────────────────────────────────────────

    @staticmethod
    def build_exhibit_index(exhibits: list[dict], lane: str = "A") -> str:
        """Generate a formatted exhibit index table.

        Each exhibit dict should have: label, description, source, pages.
        Bates numbers are assigned sequentially: PIGORS-{LANE}-NNNNNN.
        """
        lane_letter = lane.strip().upper()[:1] if lane else "A"
        lines = [
            "EXHIBIT INDEX",
            "",
            "| Exhibit | Description | Source | Pages | Bates Range |",
            "|---------|-------------|--------|-------|-------------|",
        ]

        bates_counter = 1
        for ex in exhibits:
            label = ex.get("label", "")
            desc = ex.get("description", "")
            source = ex.get("source", "")
            pages = ex.get("pages", 1)
            bates_start = f"PIGORS-{lane_letter}-{bates_counter:06d}"
            bates_end = f"PIGORS-{lane_letter}-{bates_counter + pages - 1:06d}"
            bates_range = f"{bates_start} – {bates_end}"
            lines.append(
                f"| {label} | {desc} | {source} | {pages} | {bates_range} |"
            )
            bates_counter += pages

        return "\n".join(lines)

    # ── Decontamination ─────────────────────────────────────────────────

    @staticmethod
    def decontaminate(text: str) -> str:
        """Strip ALL AI/DB references per Rule 3. Delegates to qa_gate."""
        return decontaminate(text)

    # ── Validation ──────────────────────────────────────────────────────

    @staticmethod
    def validate_filing(content: str) -> tuple[bool, list[str]]:
        """Run QA gate on filing content. Delegates to qa_gate.validate."""
        return validate(content)

    # ════════════════════════════════════════════════════════════════════
    # MAIN ASSEMBLY
    # ════════════════════════════════════════════════════════════════════

    def assemble_packet(
        self,
        lane: str,
        output_dir: str | Path | None = None,
    ) -> dict:
        """Assemble a complete filing packet for *lane*.

        Produces:
          - motion.md       (IRAC-structured motion body)
          - cos.md          (MC 12 Certificate of Service)
          - exhibit_index.md
          - proposed_order.md
          - verification.md (affidavit verification clause)
          - manifest.json   (assembly metadata)

        Returns a manifest dict with file list, status, and any QA issues.
        """
        lane = lane.strip().upper()
        today = date.today()

        # 1. Filing info
        filing_info = self.get_filing_info(lane)
        title = filing_info.get("title", f"Filing {lane}")
        case_number = filing_info.get("case_number", "")
        logger.info("Assembling packet for %s: %s", lane, title)

        # Ensure filing_info has lane for downstream use
        if "lane" not in filing_info:
            filing_info["lane"] = lane

        # 2. Query evidence, authorities, impeachment
        evidence = self.query_evidence(lane, keywords=title, limit=50)
        authorities = self.query_authorities(title, limit=30)
        impeachment = self.query_impeachment(target="Watson", limit=20)

        ev_count = len(evidence)
        auth_count = len(authorities)
        imp_count = len(impeachment)
        logger.info(
            "Gathered %d evidence, %d authorities, %d impeachment items",
            ev_count, auth_count, imp_count,
        )

        # 3. Build caption
        caption = self.build_caption(filing_info)

        # 4. Build motion body with IRAC
        sep = separation_days(today)
        motion_body = self._build_motion_body(
            filing_info, caption, evidence, authorities, today, sep
        )

        # 5. Build exhibit index from evidence
        exhibits = self._evidence_to_exhibits(evidence, lane)
        exhibit_index = self.build_exhibit_index(exhibits, lane)

        # 6. Certificate of Service
        cos_text = self.build_cos(filing_info, service_date=today)

        # 7. Proposed Order
        order_text = render_proposed_order(
            filing_info,
            motion_title=title,
            relief_line=(
                "Plaintiff's motion is GRANTED and the relief requested therein "
                "is hereby ordered."
            ),
        )

        # 8. Verification clause
        verification = render_verification(filing_date=today)

        # 9. Decontamination sweep on all text blocks
        clean_parts: dict[str, str] = {}
        all_parts = {
            "motion": motion_body,
            "exhibit_index": exhibit_index,
            "cos": cos_text,
            "proposed_order": order_text,
            "verification": verification,
        }
        for name, text in all_parts.items():
            try:
                clean_parts[name] = self.decontaminate(text)
            except ValueError as exc:
                logger.error("Decontamination FAILED on %s: %s", name, exc)
                clean_parts[name] = text

        # 10. QA Validation
        combined_text = "\n\n".join(clean_parts.values())
        passed, issues = self.validate_filing(combined_text)

        # 11. Write to output directory
        out_dir = Path(output_dir) if output_dir else _DEFAULT_OUTPUT / lane
        out_dir.mkdir(parents=True, exist_ok=True)

        files_written: list[str] = []
        file_map = {
            "motion.md": clean_parts["motion"],
            "exhibit_index.md": clean_parts["exhibit_index"],
            "cos.md": clean_parts["cos"],
            "proposed_order.md": clean_parts["proposed_order"],
            "verification.md": clean_parts["verification"],
        }

        for filename, content in file_map.items():
            fpath = out_dir / filename
            fpath.write_text(content, encoding="utf-8")
            files_written.append(str(fpath))
            logger.info("Wrote %s (%d chars)", fpath, len(content))

        # 12. Manifest
        manifest = {
            "lane": lane,
            "title": title,
            "case_number": case_number,
            "assembled_at": datetime.now().isoformat(),
            "separation_days": sep,
            "evidence_count": ev_count,
            "authority_count": auth_count,
            "impeachment_count": imp_count,
            "files": files_written,
            "output_dir": str(out_dir),
            "qa_passed": passed,
            "qa_issues": issues,
            "status": "QA_PASSED" if passed else "QA_ISSUES_FOUND",
        }

        # Write manifest
        import json as _json

        manifest_path = out_dir / "manifest.json"
        manifest_path.write_text(
            _json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        files_written.append(str(manifest_path))

        logger.info(
            "Packet assembly %s — %d files written to %s",
            "PASSED" if passed else "ISSUES FOUND",
            len(files_written),
            out_dir,
        )
        return manifest

    # ── Internal: Motion Body Builder ───────────────────────────────────

    def _build_motion_body(
        self,
        filing_info: dict,
        caption: str,
        evidence: list[dict],
        authorities: list[dict],
        filing_date: date,
        sep_days: int,
    ) -> str:
        """Construct the motion document with IRAC structure."""
        title = filing_info.get("title", "Motion")
        fmt = get_court_format(filing_info.get("lane", "A"))

        sections: list[str] = []

        # Caption
        sections.append(caption)
        sections.append("")
        sections.append(title.upper())
        sections.append("=" * len(title))
        sections.append("")

        # Introduction
        sections.append("INTRODUCTION")
        sections.append("")
        intro = (
            f"    Plaintiff, Andrew James Pigors, appearing pro se, "
            f"respectfully moves this {fmt['court']} for the relief "
            f"described herein. As of the date of this filing, Plaintiff "
            f"has been separated from the minor child, L.D.W., for "
            f"{sep_days} days — a period computed from July 29, 2025, "
            f"the date of last contact."
        )
        sections.append(intro)
        sections.append("")

        # Statement of Facts (from evidence)
        sections.append("STATEMENT OF FACTS")
        sections.append("")
        if evidence:
            for i, ev in enumerate(evidence[:15], 1):
                quote = ev.get("quote_text", "")
                source = ev.get("source_file", "unknown source")
                page = ev.get("page_number")
                page_str = f", p. {page}" if page else ""
                sections.append(
                    f"    {i}. {quote} ({source}{page_str}.)"
                )
                sections.append("")
        else:
            sections.append(
                "    [ACQUIRE: Evidence not found in database for this lane. "
                "Searched: evidence_quotes (0 rows). "
                "Likely source: case file documents. Priority: HIGH]"
            )
            sections.append("")

        # IRAC Argument
        sections.append("ARGUMENT")
        sections.append("")

        # Build IRAC from authorities
        if authorities:
            primary = authorities[0]
            citation = primary.get("primary_citation", "")
            context = primary.get("paragraph_context", "")
            supporting = primary.get("supporting_citation", "")

            irac = self.build_irac_section(
                issue=(
                    f"Whether this Court should grant the relief requested "
                    f"in Plaintiff's {title}."
                ),
                rule=(
                    f"Under {citation}, {context[:300] if context else ''} "
                    f"See also {supporting}." if supporting else
                    f"Under {citation}, {context[:300] if context else ''}."
                ),
                application=(
                    f"Here, Plaintiff has been separated from the minor child, "
                    f"L.D.W., for {sep_days} days since July 29, 2025. "
                    f"The evidence cited in the Statement of Facts demonstrates "
                    f"that the requested relief is warranted."
                ),
                conclusion=(
                    f"For the foregoing reasons, Plaintiff respectfully requests "
                    f"that this Court grant the relief requested herein."
                ),
            )
            sections.append(irac)
        else:
            sections.append(
                "    [ACQUIRE: No authority chains found for this filing topic. "
                "Searched: authority_chains_v2 (0 rows). "
                "Likely source: MCR/MCL research. Priority: HIGH]"
            )
        sections.append("")

        # Relief Requested
        sections.append("RELIEF REQUESTED")
        sections.append("")
        sections.append(
            f"    WHEREFORE, Plaintiff, Andrew James Pigors, appearing pro se, "
            f"respectfully requests that this Honorable Court grant the "
            f"following relief:"
        )
        sections.append("")
        sections.append(f"    1. Grant Plaintiff's {title};")
        sections.append(
            "    2. Grant such other and further relief as this Court "
            "deems just and proper."
        )
        sections.append("")

        # Signature
        sections.append(render_signature(filing_date))
        sections.append("")

        return "\n".join(sections)

    # ── Internal: Evidence → Exhibits ───────────────────────────────────

    @staticmethod
    def _evidence_to_exhibits(
        evidence: list[dict],
        lane: str,
    ) -> list[dict]:
        """Convert evidence query results into exhibit dicts for indexing."""
        exhibits: list[dict] = []
        seen_sources: set[str] = set()
        label_counter = 1

        for ev in evidence:
            source = ev.get("source_file", "")
            if not source or source in seen_sources:
                continue
            seen_sources.add(source)

            label_num = label_counter
            label_counter += 1
            # Generate letter labels A-Z, then AA, AB, etc.
            if label_num <= 26:
                label = chr(64 + label_num)
            else:
                label = chr(64 + ((label_num - 1) // 26)) + chr(
                    65 + ((label_num - 1) % 26)
                )

            exhibits.append({
                "label": f"Ex. {label}",
                "description": ev.get("category", "Evidence"),
                "source": source,
                "pages": 1,
            })

            if label_counter > 52:
                break

        return exhibits

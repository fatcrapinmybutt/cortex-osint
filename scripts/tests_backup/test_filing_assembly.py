"""Filing assembly tests — qa_gate, templates, assembler.

Tests decontamination sweeps, hallucination blacklists, separation_days(),
court format routing, and assembler class import.
"""

import sys
from datetime import date
from pathlib import Path

import pytest

_sys_dir = str(Path(__file__).resolve().parent.parent)
if _sys_dir not in sys.path:
    sys.path.insert(0, _sys_dir)


# ── QA Gate Tests ───────────────────────────────────────────────────────────

class TestQAGateValidation:
    """Tests for engines.filing_assembly.qa_gate.validate()."""

    @pytest.fixture(autouse=True)
    def _import_qa(self):
        from engines.filing_assembly.qa_gate import (
            validate, decontaminate,
            HALLUCINATION_BLACKLIST, AI_CONTAMINATION_PATTERNS,
            PLACEHOLDER_PATTERNS,
        )
        self.validate = validate
        self.decontaminate = decontaminate
        self.blacklist = HALLUCINATION_BLACKLIST
        self.contamination = AI_CONTAMINATION_PATTERNS
        self.placeholders = PLACEHOLDER_PATTERNS

    def test_clean_content_passes(self):
        """Clean filing content passes all QA checks."""
        content = (
            "Plaintiff, appearing pro se, respectfully requests this "
            "Honorable Court grant the relief requested herein. "
            "Dated: January 15, 2026."
        )
        passed, issues = self.validate(content)
        assert passed is True, f"Clean content should pass: {issues}"
        assert issues == []

    def test_hallucination_detected(self):
        """Hallucinated names are caught."""
        for banned in ["Jane Berry", "Patricia Berry", "Ron Berry, Esq"]:
            passed, issues = self.validate(f"Attorney {banned} appeared for defendant.")
            assert not passed, f"'{banned}' should fail validation"
            assert any("HALLUCINATION" in i for i in issues)

    def test_child_name_violation(self):
        """Full child name triggers MCR 8.119(H) violation."""
        passed, issues = self.validate("Lincoln David was present at the hearing.")
        assert not passed, "Child's full name should fail"
        assert any("CHILD NAME" in i for i in issues)

    def test_ai_contamination_caught(self):
        """AI/DB references trigger contamination failure."""
        for contam in ["LitigationOS", "evidence_quotes", "MANBEARPIG"]:
            passed, issues = self.validate(f"Analysis from {contam} shows bias.")
            assert not passed, f"'{contam}' should trigger contamination check"
            assert any("CONTAMINATION" in i for i in issues)

    def test_placeholder_detected(self):
        """Unresolved placeholders are flagged."""
        passed, issues = self.validate("Filed on [ANDREW_REQUIRED: date].")
        assert not passed
        assert any("PLACEHOLDER" in i for i in issues)

    def test_stale_year_detected(self):
        """Dates with years before 2026 are flagged."""
        passed, issues = self.validate("Filed on January 15, 2025.")
        assert not passed
        assert any("STALE YEAR" in i for i in issues)

    def test_pro_se_violation(self):
        """'undersigned counsel' triggers pro se violation."""
        passed, issues = self.validate("The undersigned counsel submits this motion.")
        assert not passed
        assert any("PRO SE" in i for i in issues)

    def test_judge_name_single_l(self):
        """McNeil (one L) without McNeill triggers error."""
        passed, issues = self.validate("Judge McNeil ruled against the motion.")
        assert not passed
        assert any("JUDGE NAME" in i for i in issues)

    def test_judge_name_correct(self):
        """McNeill (two Ls) does NOT trigger error."""
        clean = "Hon. Jenny L. McNeill presided over the hearing on January 10, 2026."
        passed, issues = self.validate(clean)
        assert passed, f"Correct judge name should pass: {issues}"

    def test_path_contamination(self):
        """File paths trigger contamination."""
        passed, issues = self.validate(r"Data from C:\Users\andre\LitigationOS shows pattern.")
        assert not passed
        assert any("CONTAMINATION" in i for i in issues)


class TestQAGateDecontaminate:
    """Tests for engines.filing_assembly.qa_gate.decontaminate()."""

    @pytest.fixture(autouse=True)
    def _import_qa(self):
        from engines.filing_assembly.qa_gate import decontaminate
        self.decontaminate = decontaminate

    def test_removes_ai_refs(self):
        """Decontaminate removes AI system names."""
        result = self.decontaminate("LitigationOS found evidence.")
        assert "LitigationOS" not in result

    def test_removes_path_refs(self):
        """Decontaminate removes file paths."""
        result = self.decontaminate(r"Source: C:\Users\andre\file.txt is relevant.")
        assert r"C:\Users\andre" not in result

    def test_clean_text_unchanged(self):
        """Text with no contamination passes through unchanged."""
        clean = "Plaintiff respectfully requests relief."
        assert self.decontaminate(clean) == clean

    def test_blacklist_count(self):
        """Hallucination blacklist has at least 10 entries."""
        from engines.filing_assembly.qa_gate import HALLUCINATION_BLACKLIST
        assert len(HALLUCINATION_BLACKLIST) >= 10

    def test_contamination_count(self):
        """AI contamination patterns has at least 20 entries."""
        from engines.filing_assembly.qa_gate import AI_CONTAMINATION_PATTERNS
        assert len(AI_CONTAMINATION_PATTERNS) >= 20


# ── Templates Tests ─────────────────────────────────────────────────────────

class TestTemplates:
    """Tests for engines.filing_assembly.templates."""

    @pytest.fixture(autouse=True)
    def _import_templates(self):
        from engines.filing_assembly.templates import (
            separation_days, get_court_format, render_signature,
            SEPARATION_ANCHOR, COURT_FORMATS,
            PLAINTIFF_NAME, DEFENDANT_NAME, JUDGE_NAME, CHILD_INITIALS,
        )
        self.separation_days = separation_days
        self.get_court_format = get_court_format
        self.render_signature = render_signature
        self.anchor = SEPARATION_ANCHOR
        self.formats = COURT_FORMATS
        self.plaintiff = PLAINTIFF_NAME
        self.defendant = DEFENDANT_NAME
        self.judge = JUDGE_NAME
        self.child = CHILD_INITIALS

    def test_separation_anchor_date(self):
        """Separation anchor is July 29, 2025."""
        assert self.anchor == date(2025, 7, 29)

    def test_separation_days_positive(self):
        """separation_days() returns positive number for dates after anchor."""
        result = self.separation_days(as_of=date(2026, 1, 1))
        expected = (date(2026, 1, 1) - date(2025, 7, 29)).days
        assert result == expected

    def test_separation_days_at_anchor(self):
        """separation_days() returns 0 at the anchor date."""
        assert self.separation_days(as_of=date(2025, 7, 29)) == 0

    def test_separation_days_dynamic(self):
        """separation_days() with no arg uses today (never hardcoded)."""
        result = self.separation_days()
        expected = (date.today() - date(2025, 7, 29)).days
        assert result == expected

    def test_court_formats_all_lanes(self):
        """COURT_FORMATS has entries for lanes A through F."""
        for lane in "ABCDEF":
            assert lane in self.formats, f"Missing format for lane {lane}"

    def test_get_court_format_lane_a(self):
        """get_court_format('A') returns 14th Circuit Court."""
        fmt = self.get_court_format("A")
        assert "14th Circuit" in fmt["court"]
        assert fmt["case_number"] == "2024-001507-DC"

    def test_get_court_format_filing_id(self):
        """get_court_format('F1') maps F1 to lane A."""
        fmt = self.get_court_format("F1")
        assert fmt["case_number"] == "2024-001507-DC"

    def test_get_court_format_invalid_raises(self):
        """get_court_format with invalid lane raises ValueError."""
        with pytest.raises(ValueError):
            self.get_court_format("Z")

    def test_render_signature_has_pro_se(self):
        """Signature block includes 'appearing pro se'."""
        sig = self.render_signature(filing_date=date(2026, 3, 25))
        assert "pro se" in sig.lower()
        assert self.plaintiff in sig

    def test_render_signature_date(self):
        """Signature block uses the provided date."""
        sig = self.render_signature(filing_date=date(2026, 4, 1))
        assert "April 01, 2026" in sig

    def test_party_names_correct(self):
        """Party identity constants are correct."""
        assert self.plaintiff == "ANDREW JAMES PIGORS"
        assert self.defendant == "EMILY A. WATSON"
        assert self.judge == "Hon. Jenny L. McNeill"
        assert self.child == "L.D.W."


# ── Assembler Import Tests ──────────────────────────────────────────────────

class TestAssemblerImport:
    """Tests for engines.filing_assembly.assembler module import."""

    def test_assembler_imports(self):
        """FilingAssembler class imports without crash."""
        from engines.filing_assembly import FilingAssembler
        assert FilingAssembler is not None

    def test_assembler_version(self):
        """Filing assembly module has __version__."""
        import engines.filing_assembly as fa
        assert hasattr(fa, "__version__")

    def test_assembler_is_callable(self):
        """FilingAssembler is a callable class."""
        from engines.filing_assembly.assembler import FilingAssembler
        assert callable(FilingAssembler)

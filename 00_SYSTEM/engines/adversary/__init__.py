"""
AdversaryEngine — Adversary Modeling for Pigors v Watson
========================================================
Builds, persists, and queries adversary profiles from litigation_context.db.
Analyzes escalation patterns, predicts responses, generates counter-strategies.
"""

from __future__ import annotations

__all__ = ["AdversaryProfile", "AdversaryEngine"]

import json
import re
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

DB_PATH = str(Path(__file__).resolve().parents[3] / "litigation_context.db")

# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------

@dataclass
class AdversaryProfile:
    name: str
    role: str  # defendant, judge, attorney, foc, witness, entity
    threat_level: int = 5  # 1-10
    behavior_patterns: list = field(default_factory=list)
    contradictions: list = field(default_factory=list)
    impeachment_ammo: list = field(default_factory=list)
    timeline_events: list = field(default_factory=list)
    weaknesses: list = field(default_factory=list)
    predicted_responses: list = field(default_factory=list)
    counter_strategies: list = field(default_factory=list)
    filing_relevance: dict = field(default_factory=dict)
    contradiction_count: int = 0
    impeachment_count: int = 0

# ---------------------------------------------------------------------------
# Seed data — hardcoded intelligence for the 17+ adversaries
# ---------------------------------------------------------------------------

_SEED_PROFILES: list[dict] = [
    {
        "name": "Emily A. Watson",
        "role": "defendant",
        "threat_level": 10,
        "behavior_patterns": [
            "escalating_false_allegations",
            "parental_alienation",
            "police_weaponization",
            "ppo_weaponization",
            "child_withholding",
            "projection",
            "evidence_fabrication",
        ],
        "weaknesses": [
            "Recanted Oct 13 2023 'nothing was physical' (NSPD-2023-08121) then filed PPO 2 days later",
            "Officer Randall report: Emily admitted METH USE",
            "Escalation pattern provably documented — suicidal → arsenic → assault → drugs → threats",
            "Arsenic allegation disproved by ER toxicology NEGATIVE",
            "AppClose messages show normal parental communication, not threats",
            "Barnes withdrew Mar 2026 — Emily now unrepresented",
            "Albert Watson NS2505044 admission links Emily to premeditated ex parte attack",
        ],
        "predicted_responses": [
            "Will file emergency motion claiming father is dangerous if we file custody modification",
            "Will seek new PPO if parenting time restored",
            "Will allege non-compliance with any condition the court sets",
            "Will claim financial hardship to resist any sanctions",
            "May attempt to relocate with child to evade jurisdiction",
        ],
        "counter_strategies": [
            "Lead with recantation timeline — PPO filed 2 days after 'nothing was physical'",
            "Present Officer Randall meth admission to impeach drug allegations against Andrew",
            "Use AppClose records to disprove 'threats' narrative",
            "Compile all cleared welfare checks to show pattern of false reports",
            "Request drug testing for both parties — Emily's own admission is on record",
            "Cite MCL 722.23(j) factor j willingness to facilitate — Emily's withholding since Oct 2024",
        ],
        "filing_relevance": {"A_CUSTODY": 10, "D_PPO": 9, "C_FEDERAL": 8, "E_MISCONDUCT": 6, "F_APPELLATE": 7},
    },
    {
        "name": "Hon. Jenny L. McNeill",
        "role": "judge",
        "threat_level": 10,
        "behavior_patterns": [
            "ex_parte_orders_without_notice",
            "contempt_abuse",
            "denial_of_court_access",
            "evidence_exclusion",
            "medication_coercion",
            "retaliation_against_filings",
            "bias_toward_mother",
            "disqualification_refusal",
        ],
        "weaknesses": [
            "3697 documented ex parte violations",
            "Married to Cavan Berry — attorney magistrate 60th District, office at 990 Terrace (same as FOC)",
            "Former law partner with Hoopes and Ladas-Hoopes at Ladas Hoopes & McNeill",
            "'Do not file anymore, I will not look at it' — verbatim denial of court access",
            "Sentenced Andrew to jail for objecting in court — told him to 'shut my mouth'",
            "Discussed making prescription medication condition for parenting time — unlawful practice of medicine",
            "Aug 8 2025 Five Orders Day — 5 ex parte orders in single day with zero notice",
            "Excluded HealthWest eval despite it being court-ordered — father deemed fit",
            "59 total days jail via contempt for birthday messages on court-approved platform",
        ],
        "predicted_responses": [
            "Will deny disqualification motion and retaliate with sanctions",
            "Will issue orders without hearing if emergency motion filed",
            "Will exclude father's evidence while admitting mother's without foundation",
            "May refer Andrew for psychological evaluation as delay tactic",
            "Will rely on 'judicial discretion' defense for JTC complaint",
        ],
        "counter_strategies": [
            "MCR 2.003 disqualification — specific bias facts in affidavit, not conclusions",
            "MSC superintending control MCR 7.306 — bypass entire 14th Circuit",
            "JTC complaint documenting pattern, not isolated incidents",
            "Federal 42 USC 1983 — judicial immunity does not cover non-judicial acts",
            "Preserve verbatim record of every denial for appellate review",
            "File in MSC if Chief Judge (Hoopes) is also compromised — MCR 7.306(A)",
        ],
        "filing_relevance": {"E_MISCONDUCT": 10, "A_CUSTODY": 9, "F_APPELLATE": 10, "C_FEDERAL": 9, "D_PPO": 7},
    },
    {
        "name": "Jennifer Barnes P55406",
        "role": "attorney",
        "threat_level": 4,
        "behavior_patterns": [
            "collusion_indicators",
            "withdrew_before_accountability",
            "ex_parte_communication",
        ],
        "weaknesses": [
            "Withdrew Mar 2026 — timing suggests avoidance of accountability",
            "Potential ex parte communications with court during representation",
            "Emily now unrepresented — Barnes withdrawal weakens defense",
        ],
        "predicted_responses": [
            "Will not appear — has withdrawn from case",
            "May claim privilege if subpoenaed about ex parte communications",
        ],
        "counter_strategies": [
            "Subpoena Barnes for deposition re: ex parte communications",
            "Reference withdrawal timing in filings as consciousness of guilt indicator",
            "Serve Emily directly — Barnes no longer shields her from process",
        ],
        "filing_relevance": {"A_CUSTODY": 4, "E_MISCONDUCT": 5, "C_FEDERAL": 3},
    },
    {
        "name": "Pamela Rusco",
        "role": "foc",
        "threat_level": 8,
        "behavior_patterns": [
            "systemic_bias_toward_mother",
            "coordinate_with_court",
            "healthwest_collusion",
            "ignore_father_evidence",
        ],
        "weaknesses": [
            "Office at 990 Terrace St — same address as Cavan Berry (McNeill spouse)",
            "FOC recommendations consistently favor Emily despite contradicting evidence",
            "Colluded with HealthWest on mental health eval that was later excluded",
            "Failed to investigate father's complaints about withholding",
        ],
        "predicted_responses": [
            "Will issue recommendation against father if custody mod filed",
            "Will defer to judge's prior rulings rather than conduct independent analysis",
            "Will minimize father's evidence of withholding",
        ],
        "counter_strategies": [
            "Object to FOC involvement citing structural bias — MCL 552.505",
            "Request independent evaluator outside Muskegon County",
            "Document 990 Terrace address overlap for disqualification support",
            "File FOC objection within 21 days of any adverse recommendation",
        ],
        "filing_relevance": {"A_CUSTODY": 9, "E_MISCONDUCT": 7, "C_FEDERAL": 6},
    },
    {
        "name": "Ronald Berry",
        "role": "witness",
        "threat_level": 7,
        "behavior_patterns": [
            "non_attorney_legal_assistance",
            "mcneill_family_connection",
            "cohabitation_with_defendant",
            "shadow_legal_operations",
        ],
        "weaknesses": [
            "Non-attorney providing legal assistance to Emily — potential UPL violation",
            "Related to Cavan Berry (McNeill's spouse) — family connection to presiding judge",
            "Lives at 2160 Garland Dr with Emily — potential witness impeachment",
            "Coordinated ex parte communications with court",
        ],
        "predicted_responses": [
            "Will deny family connection to McNeill/Berry when confronted",
            "Will claim only provided personal support, not legal advice",
        ],
        "counter_strategies": [
            "Depose Ronald Berry on relationship to Cavan Berry and McNeill",
            "Subpoena communications between Ronald Berry and court",
            "Use Berry connection as additional MCR 2.003 disqualification grounds",
            "Reference in MSC application as evidence of systemic corruption",
        ],
        "filing_relevance": {"E_MISCONDUCT": 9, "A_CUSTODY": 5, "C_FEDERAL": 7},
    },
    {
        "name": "Cavan Berry",
        "role": "witness",
        "threat_level": 8,
        "behavior_patterns": [
            "spousal_connection_to_judge",
            "shared_office_with_foc",
            "attorney_magistrate_position",
        ],
        "weaknesses": [
            "Attorney magistrate at 60th District — office at 990 Terrace St (same as FOC)",
            "Married to Hon. Jenny L. McNeill — direct conflict of interest",
            "Related to Ronald Berry who cohabits with defendant Emily",
            "Position creates structural bias pipeline: Berry → McNeill → FOC → custody outcome",
        ],
        "predicted_responses": [
            "Will assert judicial/spousal privilege if deposed",
            "Will deny any influence on McNeill's custody rulings",
        ],
        "counter_strategies": [
            "Map Berry-McNeill-FOC address overlap (990 Terrace) in MSC filing",
            "Use as centerpiece of three-court judicial cartel argument",
            "Federal 1983 — conspiracy between state actors",
            "JTC complaint naming structural conflict",
        ],
        "filing_relevance": {"E_MISCONDUCT": 10, "C_FEDERAL": 9, "A_CUSTODY": 6},
    },
    {
        "name": "Albert Watson",
        "role": "witness",
        "threat_level": 7,
        "behavior_patterns": [
            "premeditated_ex_parte_coordination",
            "intimidation",
            "coercion",
            "police_weaponization",
        ],
        "weaknesses": [
            "NS2505044: admitted to police 'They want this documented so Emily can go tomorrow to get an Ex Parte order'",
            "Kitchen recording: 'I will make sure you don't see your son'",
            "Coordinated with Emily on premeditated ex parte attack — Aug 5-8 2025 timeline",
            "Called police to create paper trail FOR Emily's custody filing",
        ],
        "predicted_responses": [
            "Will deny premeditation despite police report documenting admission",
            "Will claim recordings were taken without consent — rebut with MCL 750.539c one-party",
            "Will attempt to minimize role in custody strategy",
        ],
        "counter_strategies": [
            "NS2505044 police report is devastating — use verbatim in every filing",
            "Authenticate kitchen recording per Sullivan v Gray, 117 Mich App 476 (1982)",
            "Timeline proof: Aug 5 recording → Aug 7 Albert police call → Aug 8 five ex parte orders",
            "Depose Albert on his statement to police — cannot deny what's in official report",
        ],
        "filing_relevance": {"A_CUSTODY": 9, "E_MISCONDUCT": 6, "C_FEDERAL": 7, "F_APPELLATE": 7},
    },
    {
        "name": "Lori Watson",
        "role": "witness",
        "threat_level": 5,
        "behavior_patterns": [
            "prosecutorial_connection",
            "family_coordination",
            "witness_coaching",
        ],
        "weaknesses": [
            "Kent County prosecutor's office connection — potential influence pipeline",
            "Participated in family coordination against Andrew",
            "Kitchen recording may capture her involvement in custody strategy",
        ],
        "predicted_responses": [
            "Will support Emily's narrative as family member",
            "Will deny prosecutor office influence",
        ],
        "counter_strategies": [
            "Explore Kent County prosecutor connection for conflict of interest",
            "Cross-examine on family coordination in custody strategy",
            "Use kitchen recording transcript if she is captured on it",
        ],
        "filing_relevance": {"A_CUSTODY": 5, "C_FEDERAL": 4},
    },
    {
        "name": "Hon. Kenneth Hoopes",
        "role": "judge",
        "threat_level": 8,
        "behavior_patterns": [
            "former_law_partner_of_mcneill",
            "dismissed_housing_case_with_prejudice",
            "compromised_chief_judge",
        ],
        "weaknesses": [
            "Former law partner of McNeill at Ladas, Hoopes & McNeill (435 Whitehall Rd)",
            "Dismissed housing case 2025-002760-CZ with prejudice",
            "As Chief Judge, responsible for MCR 2.003 reassignment — but is himself compromised",
            "Cannot serve as neutral reassignment authority due to partnership history",
        ],
        "predicted_responses": [
            "Will protect McNeill if disqualification motion routed through him",
            "Will deny partnership creates conflict of interest",
        ],
        "counter_strategies": [
            "Bypass Hoopes entirely — go directly to MSC for reassignment per MCR 7.306",
            "Document Ladas Hoopes & McNeill partnership in MSC application",
            "Argue entire 14th Circuit is compromised — three former partners across three courts",
            "Federal 1983 — conspiracy element strengthened by documented partnership",
        ],
        "filing_relevance": {"E_MISCONDUCT": 9, "B_HOUSING": 8, "C_FEDERAL": 8, "F_APPELLATE": 7},
    },
    {
        "name": "Hon. Maria Ladas-Hoopes",
        "role": "judge",
        "threat_level": 7,
        "behavior_patterns": [
            "former_law_partner_of_mcneill",
            "wife_of_chief_judge",
            "three_court_cartel_member",
        ],
        "weaknesses": [
            "Former law partner at Ladas, Hoopes & McNeill",
            "Wife of Chief Judge Kenneth Hoopes",
            "60th District Court judge — same court where Cavan Berry is attorney magistrate",
            "Three-court cartel: McNeill (14th Circuit) + Hoopes (14th Circuit Chief) + Ladas-Hoopes (60th District)",
            "Andrew lost home, son, and freedom across all three courts",
        ],
        "predicted_responses": [
            "Will defer to McNeill's rulings if case comes before 60th District",
            "Will deny partnership/family relationships create conflict",
        ],
        "counter_strategies": [
            "Include in three-court cartel argument for MSC",
            "Document 435 Whitehall Rd partnership address in JTC complaint",
            "Federal 1983 — conspiracy across multiple courts strengthens claim",
        ],
        "filing_relevance": {"E_MISCONDUCT": 8, "C_FEDERAL": 8},
    },
    {
        "name": "Shady Oaks MHP",
        "role": "entity",
        "threat_level": 6,
        "behavior_patterns": [
            "illegal_eviction",
            "property_destruction",
            "habitability_violations",
            "title_interference",
        ],
        "weaknesses": [
            "Pattern of housing code violations across portfolio",
            "Illegal lockout/eviction without court order",
            "Water shutoff / utility abuse documented",
            "Property destruction or removal",
        ],
        "predicted_responses": [
            "Will claim Andrew abandoned property",
            "Will assert corporate veil — blame management company not owner",
            "Will produce fabricated lease violation notices",
        ],
        "counter_strategies": [
            "Document chain of title and ownership for piercing corporate veil",
            "Collect housing code violation records from local enforcement",
            "Photograph/video all property condition evidence",
            "FOIA local code enforcement records",
        ],
        "filing_relevance": {"B_HOUSING": 10, "C_FEDERAL": 5},
    },
    {
        "name": "Alden Global Capital",
        "role": "entity",
        "threat_level": 5,
        "behavior_patterns": [
            "pattern_of_housing_violations",
            "corporate_parent_liability",
            "cost_cutting_at_resident_expense",
        ],
        "weaknesses": [
            "Nationwide pattern of housing violations across portfolio",
            "Corporate parent of Shady Oaks — Monell-style liability argument",
            "Public reporting on predatory practices",
        ],
        "predicted_responses": [
            "Will invoke corporate veil / separate entity defense",
            "Will file motion to dismiss for lack of personal jurisdiction",
            "Will hire major firm to litigate aggressively",
        ],
        "counter_strategies": [
            "Research Alden Global Capital housing litigation in other jurisdictions",
            "Build pattern evidence from public court records nationally",
            "Pierce corporate veil through control/alter ego doctrine",
        ],
        "filing_relevance": {"B_HOUSING": 8, "C_FEDERAL": 6},
    },
    {
        "name": "Martini",
        "role": "foc",
        "threat_level": 6,
        "behavior_patterns": [
            "biased_recommendations",
            "ignore_father_evidence",
            "rubber_stamp_mother_position",
        ],
        "weaknesses": [
            "Recommendations consistently align with Emily's position",
            "Failed to investigate Andrew's documented concerns",
            "Pattern of dismissing father's evidence without analysis",
        ],
        "predicted_responses": [
            "Will produce adverse recommendation on any custody modification",
            "Will defer to McNeill's prior findings rather than independent analysis",
        ],
        "counter_strategies": [
            "Request different FOC caseworker citing documented bias",
            "Object within 21 days to any adverse FOC recommendation — MCR 3.218",
            "File formal complaint with FOC chief referee",
        ],
        "filing_relevance": {"A_CUSTODY": 7, "E_MISCONDUCT": 4},
    },
    {
        "name": "HealthWest",
        "role": "entity",
        "threat_level": 5,
        "behavior_patterns": [
            "colluded_with_foc",
            "evaluation_excluded_by_court",
            "biased_assessment_process",
        ],
        "weaknesses": [
            "Court-ordered eval found father fit — LOCUS Score 12 (Level One)",
            "Psychosis=0, Substance=0, Danger=0 — all clear",
            "McNeill EXCLUDED this favorable eval from record — MRE 901/702-703 violation",
            "Colluded with Rusco on assessment process",
        ],
        "predicted_responses": [
            "Will claim evaluation was properly conducted within protocols",
            "Will resist releasing full records citing patient privacy",
        ],
        "counter_strategies": [
            "Use HealthWest eval AS evidence — it CLEARS Andrew on every metric",
            "Challenge McNeill's exclusion of court-ordered eval as reversible error",
            "Subpoena HealthWest records and communications with Rusco",
            "HIPAA authorization already given — privacy objection fails",
        ],
        "filing_relevance": {"A_CUSTODY": 8, "F_APPELLATE": 7, "E_MISCONDUCT": 5},
    },
    {
        "name": "DJ Hilson",
        "role": "witness",
        "threat_level": 4,
        "behavior_patterns": [
            "prosecutorial_discretion_abuse",
            "selective_enforcement",
        ],
        "weaknesses": [
            "Muskegon County Prosecutor — selective enforcement pattern",
            "Failed to prosecute Emily's documented false reports",
            "9 NSPD contacts with zero arrests/charges against Andrew",
        ],
        "predicted_responses": [
            "Will claim prosecutorial discretion shields decisions from review",
        ],
        "counter_strategies": [
            "Document selective prosecution pattern in federal 1983 complaint",
            "FOIA all case referrals involving Pigors and Watson",
        ],
        "filing_relevance": {"C_FEDERAL": 6, "E_MISCONDUCT": 4},
    },
    {
        "name": "Gilbert C. Berry",
        "role": "witness",
        "threat_level": 3,
        "behavior_patterns": [
            "berry_family_network",
        ],
        "weaknesses": [
            "Part of Berry family network connected to McNeill through Cavan Berry",
            "Potential participant in coordinated ex parte communications",
        ],
        "predicted_responses": [
            "Will deny any involvement in custody proceedings",
        ],
        "counter_strategies": [
            "Map Berry family network for MSC conspiracy argument",
            "Include in discovery requests for communications with court personnel",
        ],
        "filing_relevance": {"E_MISCONDUCT": 5, "C_FEDERAL": 4},
    },
    {
        "name": "Kyle McNeill Berry",
        "role": "witness",
        "threat_level": 3,
        "behavior_patterns": [
            "mcneill_berry_family_member",
        ],
        "weaknesses": [
            "McNeill-Berry family member — named in timeline events",
            "Connection strengthens judicial cartel argument",
        ],
        "predicted_responses": [
            "Will deny involvement in custody proceedings",
        ],
        "counter_strategies": [
            "Include in Berry-McNeill network map for MSC and federal filings",
        ],
        "filing_relevance": {"E_MISCONDUCT": 4, "C_FEDERAL": 3},
    },
]


# ---------------------------------------------------------------------------
# Helper: safe FTS5 query
# ---------------------------------------------------------------------------

def _sanitize_fts5(query: str) -> str:
    """Sanitize input for FTS5 MATCH — strip non-word chars except * and quotes."""
    return re.sub(r'[^\w\s*"]', " ", query).strip()


def _fts_or_like(
    conn: sqlite3.Connection,
    fts_table: str,
    content_col: str,
    base_table: str,
    term: str,
    extra_cols: str = "*",
    limit: int = 200,
) -> list[sqlite3.Row]:
    """Try FTS5 MATCH first; fall back to LIKE on failure."""
    safe = _sanitize_fts5(term)
    if not safe:
        return []
    try:
        return conn.execute(
            f"SELECT {extra_cols} FROM {fts_table} WHERE {fts_table} MATCH ? LIMIT ?",
            (safe, limit),
        ).fetchall()
    except Exception:
        return conn.execute(
            f"SELECT {extra_cols} FROM {base_table} WHERE {content_col} LIKE ? LIMIT ?",
            (f"%{term}%", limit),
        ).fetchall()


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class AdversaryEngine:
    """Adversary modeling engine for Pigors v Watson."""

    def __init__(self, db_path: Optional[str | Path] = None):
        self._db_path = Path(db_path) if db_path else DB_PATH
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_table()

    # -- connection management ------------------------------------------------

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA busy_timeout=60000")
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA cache_size=-32000")
            self._conn.execute("PRAGMA temp_store=MEMORY")
            self._conn.execute("PRAGMA synchronous=NORMAL")
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    # -- schema ---------------------------------------------------------------

    def _ensure_table(self):
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS adversary_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL,
                threat_level INTEGER DEFAULT 5,
                behavior_patterns TEXT,
                weaknesses TEXT,
                predicted_responses TEXT,
                counter_strategies TEXT,
                contradiction_count INTEGER DEFAULT 0,
                impeachment_count INTEGER DEFAULT 0,
                filing_relevance TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()

    # -- DB evidence queries --------------------------------------------------

    def _query_contradictions(self, name: str) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT id, claim_id, source_a, source_b, contradiction_text, severity, lane
               FROM contradiction_map
               WHERE source_a LIKE ? OR source_b LIKE ? OR contradiction_text LIKE ?
               ORDER BY CASE severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 ELSE 3 END
               LIMIT 100""",
            (f"%{name}%", f"%{name}%", f"%{name}%"),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "claim_id": r["claim_id"],
                "source_a": r["source_a"],
                "source_b": r["source_b"],
                "text": r["contradiction_text"],
                "severity": r["severity"],
                "lane": r["lane"],
            }
            for r in rows
        ]

    def _query_impeachment(self, name: str) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT id, category, evidence_summary, quote_text,
                      impeachment_value, cross_exam_question, filing_relevance, event_date
               FROM impeachment_matrix
               WHERE evidence_summary LIKE ? OR quote_text LIKE ? OR cross_exam_question LIKE ?
               ORDER BY impeachment_value DESC
               LIMIT 100""",
            (f"%{name}%", f"%{name}%", f"%{name}%"),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "category": r["category"],
                "summary": r["evidence_summary"],
                "quote": r["quote_text"],
                "value": r["impeachment_value"],
                "cross_exam_q": r["cross_exam_question"],
                "filing_rel": r["filing_relevance"],
                "date": r["event_date"],
            }
            for r in rows
        ]

    def _query_timeline(self, name: str) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT id, event_date, event_description, actors, lane, category, severity
               FROM timeline_events
               WHERE actors LIKE ? OR event_description LIKE ?
               ORDER BY event_date ASC
               LIMIT 200""",
            (f"%{name}%", f"%{name}%"),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "date": r["event_date"],
                "description": r["event_description"],
                "actors": r["actors"],
                "lane": r["lane"],
                "category": r["category"],
                "severity": r["severity"],
            }
            for r in rows
        ]

    def _query_judicial_violations(self, name: str) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT id, violation_type, description, date_occurred,
                      mcr_rule, canon, severity, lane
               FROM judicial_violations
               WHERE description LIKE ? OR source_quote LIKE ?
               ORDER BY severity DESC
               LIMIT 200""",
            (f"%{name}%", f"%{name}%"),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "type": r["violation_type"],
                "description": r["description"],
                "date": r["date_occurred"],
                "mcr_rule": r["mcr_rule"],
                "canon": r["canon"],
                "severity": r["severity"],
                "lane": r["lane"],
            }
            for r in rows
        ]

    def _query_police_reports(self, name: str) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT id, filename, officers, incident_numbers, dates,
                      allegations, exculpatory, key_quotes
               FROM police_reports
               WHERE full_text LIKE ? OR allegations LIKE ? OR key_quotes LIKE ?
               LIMIT 50""",
            (f"%{name}%", f"%{name}%", f"%{name}%"),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "filename": r["filename"],
                "officers": r["officers"],
                "incident_numbers": r["incident_numbers"],
                "dates": r["dates"],
                "allegations": r["allegations"],
                "exculpatory": r["exculpatory"],
                "key_quotes": r["key_quotes"],
            }
            for r in rows
        ]

    def _query_evidence_quotes(self, name: str, limit: int = 50) -> list[dict]:
        """Query evidence_quotes via FTS5 (evidence_fts) with LIKE fallback."""
        conn = self._get_conn()
        safe = _sanitize_fts5(name)
        rows: list[sqlite3.Row] = []
        if safe:
            try:
                rows = conn.execute(
                    """SELECT id, source_file, quote_text, page_number, category, lane, relevance_score
                       FROM evidence_fts WHERE evidence_fts MATCH ? ORDER BY rank LIMIT ?""",
                    (safe, limit),
                ).fetchall()
            except Exception:
                pass
        if not rows:
            rows = conn.execute(
                """SELECT id, source_file, quote_text, page_number, category, lane, relevance_score
                   FROM evidence_quotes
                   WHERE quote_text LIKE ? AND (is_duplicate = 0 OR is_duplicate IS NULL)
                   ORDER BY relevance_score DESC LIMIT ?""",
                (f"%{name}%", limit),
            ).fetchall()
        return [
            {
                "id": r["id"],
                "source": r["source_file"],
                "quote": (r["quote_text"] or "")[:300],
                "page": r["page_number"],
                "category": r["category"],
                "lane": r["lane"],
                "score": r["relevance_score"],
            }
            for r in rows
        ]

    # -- profile building -----------------------------------------------------

    def _build_profile(self, seed: dict) -> AdversaryProfile:
        """Build a full profile from seed data + live DB queries."""
        name = seed["name"]
        # Short search keys for DB queries
        search_keys = self._search_keys(name)

        # Aggregate DB data across all search keys
        contradictions: list[dict] = []
        impeachment: list[dict] = []
        timeline: list[dict] = []
        for key in search_keys:
            contradictions.extend(self._query_contradictions(key))
            impeachment.extend(self._query_impeachment(key))
            timeline.extend(self._query_timeline(key))

        # Judicial-specific queries
        jv: list[dict] = []
        police: list[dict] = []
        if seed["role"] == "judge":
            for key in search_keys:
                jv.extend(self._query_judicial_violations(key))
        if seed["role"] in ("defendant", "witness"):
            for key in search_keys:
                police.extend(self._query_police_reports(key))

        # Deduplicate by id
        contradictions = _dedup_by_key(contradictions, "id")
        impeachment = _dedup_by_key(impeachment, "id")
        timeline = _dedup_by_key(timeline, "id")
        jv = _dedup_by_key(jv, "id")
        police = _dedup_by_key(police, "id")

        # Merge judicial violations into timeline view
        all_events = timeline[:]
        for v in jv:
            all_events.append(
                {
                    "id": f"jv-{v['id']}",
                    "date": v["date"],
                    "description": f"[{v['type']}] {v['description']}"[:300],
                    "actors": name,
                    "lane": v["lane"],
                    "category": v["type"],
                    "severity": str(v.get("severity", "")),
                }
            )
        for p in police:
            all_events.append(
                {
                    "id": f"pr-{p['id']}",
                    "date": p.get("dates", ""),
                    "description": f"[POLICE] {p['filename']} — {(p.get('allegations') or '')[:150]}",
                    "actors": name,
                    "lane": "A_CUSTODY",
                    "category": "police_report",
                    "severity": "high",
                }
            )

        return AdversaryProfile(
            name=name,
            role=seed["role"],
            threat_level=seed["threat_level"],
            behavior_patterns=seed.get("behavior_patterns", []),
            contradictions=contradictions[:50],
            impeachment_ammo=impeachment[:50],
            timeline_events=all_events[:100],
            weaknesses=seed.get("weaknesses", []),
            predicted_responses=seed.get("predicted_responses", []),
            counter_strategies=seed.get("counter_strategies", []),
            filing_relevance=seed.get("filing_relevance", {}),
            contradiction_count=len(contradictions),
            impeachment_count=len(impeachment),
        )

    @staticmethod
    def _search_keys(name: str) -> list[str]:
        """Generate search variants for a name (first, last, full)."""
        keys = [name]
        parts = name.replace("Hon. ", "").replace("P55406", "").strip().split()
        if len(parts) >= 2:
            keys.append(parts[-1])  # last name
            keys.append(parts[0])   # first name
            if len(parts) == 3 and parts[1] not in ("A.", "L.", "C."):
                keys.append(f"{parts[0]} {parts[-1]}")  # first+last
        # Remove duplicates while preserving order
        seen: set[str] = set()
        out: list[str] = []
        for k in keys:
            kl = k.lower()
            if kl not in seen and len(k) > 2:
                seen.add(kl)
                out.append(k)
        return out

    # -- persistence ----------------------------------------------------------

    def _persist_profile(self, profile: AdversaryProfile):
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO adversary_profiles
               (name, role, threat_level, behavior_patterns, weaknesses,
                predicted_responses, counter_strategies, contradiction_count,
                impeachment_count, filing_relevance, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
               ON CONFLICT(name) DO UPDATE SET
                 role=excluded.role,
                 threat_level=excluded.threat_level,
                 behavior_patterns=excluded.behavior_patterns,
                 weaknesses=excluded.weaknesses,
                 predicted_responses=excluded.predicted_responses,
                 counter_strategies=excluded.counter_strategies,
                 contradiction_count=excluded.contradiction_count,
                 impeachment_count=excluded.impeachment_count,
                 filing_relevance=excluded.filing_relevance,
                 updated_at=datetime('now')
            """,
            (
                profile.name,
                profile.role,
                profile.threat_level,
                json.dumps(profile.behavior_patterns),
                json.dumps(profile.weaknesses),
                json.dumps(profile.predicted_responses),
                json.dumps(profile.counter_strategies),
                profile.contradiction_count,
                profile.impeachment_count,
                json.dumps(profile.filing_relevance),
            ),
        )
        conn.commit()

    # -- public API -----------------------------------------------------------

    def build_all_profiles(self) -> list[AdversaryProfile]:
        """Build and persist all 17+ adversary profiles from seed + live DB data."""
        profiles: list[AdversaryProfile] = []
        for seed in _SEED_PROFILES:
            p = self._build_profile(seed)
            self._persist_profile(p)
            profiles.append(p)
        return profiles

    def get_profile(self, name: str) -> Optional[AdversaryProfile]:
        """Retrieve a profile by partial name match. Re-builds from DB if stale."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM adversary_profiles WHERE name LIKE ? LIMIT 1",
            (f"%{name}%",),
        ).fetchone()
        if row is None:
            # Try building from seed
            for seed in _SEED_PROFILES:
                if name.lower() in seed["name"].lower():
                    p = self._build_profile(seed)
                    self._persist_profile(p)
                    return p
            return None
        return self._row_to_profile(row)

    def get_all_profiles(self) -> list[AdversaryProfile]:
        """Return all persisted profiles. Builds if table is empty."""
        conn = self._get_conn()
        count = conn.execute("SELECT COUNT(*) FROM adversary_profiles").fetchone()[0]
        if count == 0:
            return self.build_all_profiles()
        rows = conn.execute(
            "SELECT * FROM adversary_profiles ORDER BY threat_level DESC"
        ).fetchall()
        return [self._row_to_profile(r) for r in rows]

    def get_by_threat_level(self, min_level: int = 7) -> list[AdversaryProfile]:
        """Return profiles at or above the given threat level."""
        conn = self._get_conn()
        count = conn.execute("SELECT COUNT(*) FROM adversary_profiles").fetchone()[0]
        if count == 0:
            self.build_all_profiles()
        rows = conn.execute(
            "SELECT * FROM adversary_profiles WHERE threat_level >= ? ORDER BY threat_level DESC",
            (min_level,),
        ).fetchall()
        return [self._row_to_profile(r) for r in rows]

    def get_relevant_for_filing(self, lane: str) -> list[AdversaryProfile]:
        """Return adversaries relevant to a specific case lane, sorted by relevance."""
        profiles = self.get_all_profiles()
        scored: list[tuple[int, AdversaryProfile]] = []
        for p in profiles:
            score = p.filing_relevance.get(lane, 0)
            if score > 0:
                scored.append((score, p))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored]

    def get_impeachment_package(self, name: str) -> dict:
        """Complete impeachment ammunition for a named adversary."""
        search_keys = self._search_keys(name)
        contradictions: list[dict] = []
        impeachment: list[dict] = []
        evidence: list[dict] = []
        police: list[dict] = []
        for key in search_keys:
            contradictions.extend(self._query_contradictions(key))
            impeachment.extend(self._query_impeachment(key))
            evidence.extend(self._query_evidence_quotes(key, limit=30))
            police.extend(self._query_police_reports(key))
        contradictions = _dedup_by_key(contradictions, "id")
        impeachment = _dedup_by_key(impeachment, "id")
        evidence = _dedup_by_key(evidence, "id")
        police = _dedup_by_key(police, "id")

        # Separate by severity/value tiers
        critical_contradictions = [c for c in contradictions if c.get("severity") == "critical"]
        high_value_impeachment = [i for i in impeachment if (i.get("value") or 0) >= 7]

        return {
            "target": name,
            "total_contradictions": len(contradictions),
            "critical_contradictions": critical_contradictions[:20],
            "all_contradictions": contradictions[:50],
            "total_impeachment": len(impeachment),
            "high_value_impeachment": high_value_impeachment[:20],
            "all_impeachment": impeachment[:50],
            "supporting_evidence": evidence[:30],
            "police_reports": police[:20],
            "cross_exam_questions": [
                i["cross_exam_q"]
                for i in impeachment
                if i.get("cross_exam_q")
            ][:30],
        }

    def refresh_profile(self, name: str) -> Optional[AdversaryProfile]:
        """Re-query DB and update a profile. Returns refreshed profile."""
        for seed in _SEED_PROFILES:
            if name.lower() in seed["name"].lower():
                p = self._build_profile(seed)
                self._persist_profile(p)
                return p
        return None

    # -- behavior analysis ----------------------------------------------------

    def analyze_escalation(self, name: str) -> dict:
        """Detect escalation patterns for a named adversary."""
        keys = self._search_keys(name)
        events: list[dict] = []
        for k in keys:
            events.extend(self._query_timeline(k))
        events = _dedup_by_key(events, "id")
        events.sort(key=lambda e: e.get("date") or "0000")

        # Classify events into escalation levels
        levels = {
            "verbal": [],
            "police_contact": [],
            "court_filing": [],
            "ppo": [],
            "custody_action": [],
            "contempt": [],
            "incarceration": [],
            "child_withholding": [],
        }

        level_keywords = {
            "verbal": ["threat", "harass", "yell", "argue", "verbal"],
            "police_contact": ["police", "nspd", "officer", "911", "welfare check", "report"],
            "court_filing": ["motion", "filed", "filing", "complaint", "petition"],
            "ppo": ["ppo", "protection order", "stalking", "5907"],
            "custody_action": ["custody", "parenting time", "ex parte", "sole custody"],
            "contempt": ["contempt", "show cause", "sanction", "SC#"],
            "incarceration": ["jail", "incarcerat", "arrest", "surrender", "bond"],
            "child_withholding": ["withhold", "denied visit", "no contact", "refused parenting"],
        }

        for ev in events:
            desc = (ev.get("description") or "").lower()
            cat = (ev.get("category") or "").lower()
            combined = f"{desc} {cat}"
            for level_name, kws in level_keywords.items():
                if any(kw in combined for kw in kws):
                    levels[level_name].append(ev)

        # Compute escalation timeline
        escalation_sequence: list[dict] = []
        for level_name in [
            "verbal", "police_contact", "court_filing", "ppo",
            "custody_action", "contempt", "incarceration", "child_withholding",
        ]:
            items = levels[level_name]
            if items:
                earliest = min((e.get("date") or "9999") for e in items)
                escalation_sequence.append({
                    "level": level_name,
                    "count": len(items),
                    "earliest": earliest,
                    "sample": (items[0].get("description") or "")[:200],
                })

        return {
            "adversary": name,
            "total_events": len(events),
            "escalation_levels": {k: len(v) for k, v in levels.items()},
            "escalation_sequence": escalation_sequence,
            "pattern_detected": len(escalation_sequence) >= 3,
            "highest_level_reached": (
                escalation_sequence[-1]["level"] if escalation_sequence else "none"
            ),
        }

    def analyze_retaliation(self, name: str) -> dict:
        """Detect retaliation against Andrew's filings by this adversary."""
        keys = self._search_keys(name)
        events: list[dict] = []
        for k in keys:
            events.extend(self._query_timeline(k))
        events = _dedup_by_key(events, "id")

        andrew_filings: list[dict] = []
        adversary_responses: list[dict] = []
        retaliation_pairs: list[dict] = []

        for ev in events:
            desc = (ev.get("description") or "").lower()
            actors = (ev.get("actors") or "").lower()
            is_andrew_action = "andrew" in actors and any(
                kw in desc for kw in ["filed", "motion", "complaint", "objection", "appeal"]
            )
            is_adversary_response = name.split()[-1].lower() in actors and any(
                kw in desc
                for kw in [
                    "ex parte", "order", "contempt", "denied", "suspended",
                    "sanction", "jail", "ppo", "dismissed", "struck",
                ]
            )
            if is_andrew_action:
                andrew_filings.append(ev)
            if is_adversary_response:
                adversary_responses.append(ev)

        # Pair filings with responses within 14 days
        for filing in andrew_filings:
            fd = filing.get("date") or ""
            if not fd or len(fd) < 10:
                continue
            for resp in adversary_responses:
                rd = resp.get("date") or ""
                if not rd or len(rd) < 10:
                    continue
                try:
                    f_dt = datetime.strptime(fd[:10], "%Y-%m-%d")
                    r_dt = datetime.strptime(rd[:10], "%Y-%m-%d")
                    delta = (r_dt - f_dt).days
                    if 0 <= delta <= 14:
                        retaliation_pairs.append({
                            "filing": filing.get("description", "")[:200],
                            "filing_date": fd,
                            "response": resp.get("description", "")[:200],
                            "response_date": rd,
                            "days_gap": delta,
                        })
                except ValueError:
                    continue

        return {
            "adversary": name,
            "andrew_filings_count": len(andrew_filings),
            "adversary_responses_count": len(adversary_responses),
            "retaliation_pairs": retaliation_pairs[:20],
            "retaliation_pattern_detected": len(retaliation_pairs) >= 2,
        }

    def predict_response(self, name: str, our_action: str) -> list[dict]:
        """Predict what adversary will do when we file a specific action."""
        profile = self.get_profile(name)
        if profile is None:
            return [{"prediction": f"No profile found for {name}", "confidence": 0}]

        # Map our actions to likely responses based on behavior patterns
        action_response_map: dict[str, list[dict]] = {
            "custody_modification": [
                {"prediction": "File emergency counter-motion alleging danger to child", "confidence": 9, "basis": "escalating_false_allegations"},
                {"prediction": "Request new FOC investigation biased toward mother", "confidence": 8, "basis": "systemic_bias_toward_mother"},
                {"prediction": "Seek new PPO to block father's contact", "confidence": 7, "basis": "ppo_weaponization"},
                {"prediction": "Allege non-compliance with prior court orders", "confidence": 7, "basis": "evidence_fabrication"},
            ],
            "disqualification": [
                {"prediction": "Judge denies motion and retaliates with sanctions", "confidence": 9, "basis": "disqualification_refusal"},
                {"prediction": "Chief Judge (Hoopes) refuses reassignment due to partnership", "confidence": 8, "basis": "former_law_partner_of_mcneill"},
                {"prediction": "Judge issues adverse order before disqualification heard", "confidence": 7, "basis": "ex_parte_orders_without_notice"},
            ],
            "msc_application": [
                {"prediction": "Judge accelerates adverse orders before MSC can act", "confidence": 7, "basis": "retaliation_against_filings"},
                {"prediction": "Emily files response claiming father's conduct warrants current orders", "confidence": 6, "basis": "escalating_false_allegations"},
            ],
            "contempt_motion": [
                {"prediction": "Emily claims compliance and fabricates documentation", "confidence": 8, "basis": "evidence_fabrication"},
                {"prediction": "Judge dismisses motion without hearing", "confidence": 7, "basis": "denial_of_court_access"},
            ],
            "ppo_termination": [
                {"prediction": "Emily alleges new threats to justify continuation", "confidence": 8, "basis": "escalating_false_allegations"},
                {"prediction": "Judge denies termination without best interest analysis", "confidence": 7, "basis": "bias_toward_mother"},
            ],
            "federal_1983": [
                {"prediction": "Defendants invoke judicial immunity defense", "confidence": 9, "basis": "judicial discretion"},
                {"prediction": "Defendants file 12(b)(6) motion to dismiss for failure to state a claim", "confidence": 8, "basis": "standard defense"},
                {"prediction": "Defendants remove to federal court and seek stay of state proceedings", "confidence": 6, "basis": "litigation strategy"},
            ],
            "coa_appeal": [
                {"prediction": "Emily files cross-appeal or appellee brief defending trial court", "confidence": 7, "basis": "standard appellate defense"},
                {"prediction": "Judge issues additional orders to moot appeal", "confidence": 6, "basis": "retaliation_against_filings"},
            ],
            "emergency_motion": [
                {"prediction": "Judge denies without hearing or with same-day adverse ruling", "confidence": 8, "basis": "ex_parte_orders_without_notice"},
                {"prediction": "Emily files response with new allegations of danger", "confidence": 7, "basis": "escalating_false_allegations"},
            ],
        }

        # Normalize action
        action_lower = our_action.lower().replace(" ", "_").replace("-", "_")
        best_key = None
        for key in action_response_map:
            if key in action_lower or action_lower in key:
                best_key = key
                break
        if best_key is None:
            # Fuzzy match: check if any key words appear
            for key in action_response_map:
                key_words = key.split("_")
                if any(w in action_lower for w in key_words if len(w) > 3):
                    best_key = key
                    break

        if best_key is None:
            # Generic prediction based on profile patterns
            return [
                {
                    "prediction": f"{name} likely to respond with denial and counter-attack",
                    "confidence": 5,
                    "basis": "general_behavior",
                },
                {
                    "prediction": "Expect procedural delay tactics",
                    "confidence": 5,
                    "basis": "general_behavior",
                },
            ]

        # Filter by adversary's actual behavior patterns
        predictions = action_response_map[best_key]
        relevant: list[dict] = []
        for pred in predictions:
            basis = pred["basis"]
            if basis in profile.behavior_patterns or pred["confidence"] >= 7:
                relevant.append(pred)
            else:
                # Still include but lower confidence
                relevant.append({**pred, "confidence": max(1, pred["confidence"] - 2)})
        return relevant

    def get_counter_strategy(self, name: str, their_action: str) -> list[dict]:
        """Recommend counter-moves for an adversary's action."""
        profile = self.get_profile(name)
        if profile is None:
            return [{"strategy": f"No profile found for {name}", "authority": ""}]

        action_lower = their_action.lower()

        # Build counter-strategy database
        counter_db: list[dict] = [
            {
                "trigger": ["emergency motion", "ex parte", "danger allegation"],
                "strategy": "Immediately file response with AppClose evidence showing normal communication",
                "authority": "MCR 2.119(F)(3)",
                "priority": 10,
            },
            {
                "trigger": ["ppo", "protection order", "stalking"],
                "strategy": "File motion to terminate PPO — recantation Oct 13 2023 destroys basis",
                "authority": "MCR 3.707(B), MCL 600.2950",
                "priority": 9,
            },
            {
                "trigger": ["contempt", "show cause", "jail"],
                "strategy": "Challenge due process — demand jury trial for contempt exceeding 93 days",
                "authority": "MCL 600.1715, US Const Amend VI",
                "priority": 10,
            },
            {
                "trigger": ["denied", "dismissed", "struck"],
                "strategy": "Preserve for appeal — file objection on record within 21 days",
                "authority": "MCR 7.204(A), MCR 7.205",
                "priority": 8,
            },
            {
                "trigger": ["foc recommendation", "foc report"],
                "strategy": "File FOC objection within 21 days citing structural bias",
                "authority": "MCR 3.218, MCL 552.505",
                "priority": 8,
            },
            {
                "trigger": ["sanction", "vexatious", "frivolous"],
                "strategy": "Cite right to petition courts — 1st Amend & Const 1963 art 1 sec 3",
                "authority": "US Const Amend I, MI Const art 1 § 3",
                "priority": 9,
            },
            {
                "trigger": ["deny disqualification", "refuse recusal"],
                "strategy": "Immediately file MSC superintending control — MCR 7.306",
                "authority": "MCR 7.306, MI Const art 6 § 4",
                "priority": 10,
            },
            {
                "trigger": ["exclude evidence", "strike", "inadmissible"],
                "strategy": "Make offer of proof on record, preserve for appeal MRE 103(a)(2)",
                "authority": "MRE 103(a)(2)",
                "priority": 8,
            },
            {
                "trigger": ["relocat", "move with child", "change address"],
                "strategy": "File emergency motion to prevent relocation — MCL 722.31",
                "authority": "MCL 722.31, MCR 3.211",
                "priority": 10,
            },
            {
                "trigger": ["motion to dismiss", "12(b)(6)", "failure to state"],
                "strategy": "Amend complaint to cure deficiencies, oppose with specific factual basis",
                "authority": "FRCP 15(a), MCR 2.118",
                "priority": 8,
            },
            {
                "trigger": ["judicial immunity", "absolute immunity"],
                "strategy": "Argue acts were non-judicial (administrative/enforcement) — no immunity",
                "authority": "Mireles v Waco, 502 US 9 (1991); Stump v Sparkman, 435 US 349 (1978)",
                "priority": 9,
            },
            {
                "trigger": ["withhold", "denied visit", "no contact"],
                "strategy": "File emergency motion to restore parenting time with separation day count",
                "authority": "MCL 722.27a, MCR 3.214",
                "priority": 10,
            },
        ]

        matches: list[dict] = []
        for item in counter_db:
            if any(t in action_lower for t in item["trigger"]):
                matches.append({
                    "strategy": item["strategy"],
                    "authority": item["authority"],
                    "priority": item["priority"],
                })

        if not matches:
            # Return profile's stored counter strategies
            return [
                {"strategy": cs, "authority": "", "priority": 5}
                for cs in profile.counter_strategies[:5]
            ]

        matches.sort(key=lambda m: m["priority"], reverse=True)
        return matches

    # -- utility --------------------------------------------------------------

    @staticmethod
    def _row_to_profile(row: sqlite3.Row) -> AdversaryProfile:
        """Convert a DB row to AdversaryProfile dataclass."""
        return AdversaryProfile(
            name=row["name"],
            role=row["role"],
            threat_level=row["threat_level"],
            behavior_patterns=_safe_json_load(row["behavior_patterns"]),
            contradictions=[],  # not stored in DB table — re-query on demand
            impeachment_ammo=[],
            timeline_events=[],
            weaknesses=_safe_json_load(row["weaknesses"]),
            predicted_responses=_safe_json_load(row["predicted_responses"]),
            counter_strategies=_safe_json_load(row["counter_strategies"]),
            filing_relevance=_safe_json_load(row["filing_relevance"]),
            contradiction_count=row["contradiction_count"],
            impeachment_count=row["impeachment_count"],
        )

    def summary(self) -> str:
        """Return a text summary of all adversary profiles."""
        profiles = self.get_all_profiles()
        lines = [f"ADVERSARY ENGINE — {len(profiles)} profiles\n"]
        for p in profiles:
            lines.append(
                f"  [{p.threat_level:2d}/10] {p.name:<30s} ({p.role}) "
                f"— {p.contradiction_count} contradictions, {p.impeachment_count} impeachment items"
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _safe_json_load(val) -> list | dict:
    if val is None:
        return []
    if isinstance(val, (list, dict)):
        return val
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return []


def _dedup_by_key(items: list[dict], key: str) -> list[dict]:
    """Deduplicate a list of dicts by a given key, preserving order."""
    seen: set = set()
    out: list[dict] = []
    for item in items:
        k = item.get(key)
        if k not in seen:
            seen.add(k)
            out.append(item)
    return out

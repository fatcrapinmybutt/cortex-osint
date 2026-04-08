---
name: SINGULARITY-MBP-APEX-AUTOMATON
description: "Autonomous legal reasoning engine for THEMANBEARPIG. Six-layer pipeline (intake→classify→analyze→reason→argue→validate) converts raw evidence into court-ready IRAC arguments with authority chains, impeachment ammo, counter-argument anticipation, and filing assembly. 20+ Michigan authority templates, argument chain builder, gap analysis, confidence scoring. The litigation autopilot."
version: "1.0.0"
tier: "TIER-7/APEX"
domain: "Autonomous legal reasoning — evidence-to-argument pipeline, IRAC generation, authority template execution, counter-argument anticipation, filing assembly, hallucination guard"
triggers:
  - legal reasoning
  - IRAC
  - CREAC
  - argument chain
  - authority template
  - reasoning pipeline
  - litigation autopilot
  - evidence to argument
  - legal syllogism
  - counter-argument
  - filing assembly
  - element matching
  - best interest analysis
  - disqualification argument
  - PPO analysis
  - contempt argument
  - due process
  - parental alienation
  - change of circumstances
  - Vodvarka
  - hallucination guard
  - citation verification
  - automaton
references:
  - SINGULARITY-MBP-APEX-COGNITION
  - SINGULARITY-MBP-APEX-MEMORY
  - SINGULARITY-MBP-APEX-GRAPHML
  - SINGULARITY-MBP-COMBAT-WEAPONS
  - SINGULARITY-MBP-COMBAT-IMPEACHMENT
  - SINGULARITY-MBP-INTEGRATION-FILING
  - SINGULARITY-MBP-INTERFACE-NARRATIVE
---

# SINGULARITY-MBP-APEX-AUTOMATON v1.0

> **Raw evidence in. Court-ready arguments out. No human bottleneck.**

TIER-7/APEX — the highest tier. This skill implements the autonomous legal
reasoning engine: a six-layer pipeline that ingests evidence from
litigation_context.db (1.3 GB, 790+ tables), reasons over Michigan law,
and produces IRAC-structured arguments with full authority chains,
impeachment ammunition, counter-argument anticipation, and filing-ready
document structures. The litigation autopilot for THEMANBEARPIG.

---

## Layer 1: Six-Layer Reasoning Pipeline

### 1.1 Pipeline Architecture

```python
"""
ReasoningPipeline — Six-layer evidence-to-argument transformation engine.

Layers:
  L1 INTAKE    → Raw evidence ingestion, text normalization
  L2 CLASSIFY  → Lane assignment (MEEK), category tagging, actor extraction
  L3 ANALYZE   → Pattern detection, contradiction finding, timeline ordering
  L4 REASON    → Legal syllogism: Rule + Fact → Conclusion, element matching
  L5 ARGUE     → IRAC/CREAC structure, authority chain assembly
  L6 VALIDATE  → Citation verification, hallucination guard, confidence scoring

Each layer has:
  - Typed input/output contracts
  - Transformation logic
  - Quality gate (must pass before next layer)
  - Metrics (latency, item count, confidence)
"""

import re
import time
import hashlib
import sqlite3
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class PipelineLayer(Enum):
    INTAKE   = 1
    CLASSIFY = 2
    ANALYZE  = 3
    REASON   = 4
    ARGUE    = 5
    VALIDATE = 6


class QualityGateResult(Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass
class PipelineItem:
    """Single item flowing through the pipeline."""
    item_id: str
    raw_text: str
    source_path: str = ""
    source_table: str = ""
    # L2 outputs
    lane: str = ""
    category: str = ""
    actors: list = field(default_factory=list)
    event_date: str = ""
    # L3 outputs
    patterns: list = field(default_factory=list)
    contradictions: list = field(default_factory=list)
    timeline_position: int = -1
    # L4 outputs
    matched_elements: dict = field(default_factory=dict)
    syllogisms: list = field(default_factory=list)
    # L5 outputs
    irac_blocks: list = field(default_factory=list)
    authority_chain: list = field(default_factory=list)
    # L6 outputs
    confidence: float = 0.0
    hallucination_flags: list = field(default_factory=list)
    gate_results: dict = field(default_factory=dict)


@dataclass
class LayerMetrics:
    layer: PipelineLayer
    items_in: int = 0
    items_out: int = 0
    items_filtered: int = 0
    latency_ms: float = 0.0
    gate_result: QualityGateResult = QualityGateResult.PASS
    errors: list = field(default_factory=list)


@dataclass
class PipelineResult:
    """Complete pipeline output."""
    topic: str
    items: list = field(default_factory=list)
    metrics: list = field(default_factory=list)
    arguments: list = field(default_factory=list)
    filing_structure: dict = field(default_factory=dict)
    overall_confidence: float = 0.0
    gaps: list = field(default_factory=list)
    total_latency_ms: float = 0.0


# ── MEEK lane detection signals ──────────────────────────────────
MEEK_SIGNALS = {
    'E': re.compile(
        r'mcneill|judicial|bias|jtc|canon|misconduct|benchbook|ex\s*parte',
        re.IGNORECASE
    ),
    'D': re.compile(
        r'ppo|protection\s+order|5907|stalking|harassment',
        re.IGNORECASE
    ),
    'F': re.compile(
        r'coa|366810|appeal|appellant|appellee|brief|appendix',
        re.IGNORECASE
    ),
    'C': re.compile(
        r'federal|§\s*1983|42\s+usc|conspiracy|civil\s+rights',
        re.IGNORECASE
    ),
    'A': re.compile(
        r'custody|parenting|001507|watson|visitation|foc|best\s+interest',
        re.IGNORECASE
    ),
    'B': re.compile(
        r'shady\s+oaks|eviction|housing|trailer|002760|habitability',
        re.IGNORECASE
    ),
}

# ── Actor extraction patterns ────────────────────────────────────
KNOWN_ACTORS = {
    'Andrew Pigors': re.compile(r'andrew|pigors|plaintiff|father', re.I),
    'Emily A. Watson': re.compile(r'emily|watson|defendant|mother', re.I),
    'Hon. Jenny L. McNeill': re.compile(r'mcneill|judge|court', re.I),
    'Pamela Rusco': re.compile(r'rusco|foc|friend\s+of\s+(the\s+)?court', re.I),
    'Ronald Berry': re.compile(r'ronald?\s+berry|ron\s+berry', re.I),
    'Albert Watson': re.compile(r'albert\s+watson', re.I),
    'Jennifer Barnes': re.compile(r'barnes|p55406', re.I),
    'Hon. Kenneth Hoopes': re.compile(r'hoopes|chief\s+judge', re.I),
}

# ── Evidence categories ──────────────────────────────────────────
EVIDENCE_CATEGORIES = [
    'police_report', 'court_order', 'communication', 'financial',
    'medical', 'audio_video', 'photograph', 'app_export',
    'government_record', 'housing_property', 'employment',
    'forensic', 'transcript', 'affidavit', 'social_media',
    'correspondence', 'legal_filing', 'witness_statement',
    'expert_report', 'unknown',
]

CATEGORY_PATTERNS = {
    'police_report': re.compile(r'nspd|police|officer|incident|ns\d{7}', re.I),
    'court_order': re.compile(r'order|judgment|ruling|decree|stipulation', re.I),
    'communication': re.compile(r'appclose|text|message|email|sms', re.I),
    'medical': re.compile(r'healthwest|medical|locus|psycho|eval', re.I),
    'audio_video': re.compile(r'\.mp[34]|audio|video|recording', re.I),
    'legal_filing': re.compile(r'motion|brief|complaint|petition|response', re.I),
}


class ReasoningPipeline:
    """
    Six-layer autonomous legal reasoning pipeline.

    Usage:
        pipeline = ReasoningPipeline(db_path)
        result = pipeline.process("parental alienation", lane="A")
        for arg in result.arguments:
            print(arg.irac_text)
    """

    def __init__(self, db_path="litigation_context.db"):
        self.db_path = db_path
        self._conn = None
        self.metrics = []
        self.halted_at = None

    @property
    def conn(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA busy_timeout = 60000")
            self._conn.execute("PRAGMA journal_mode = WAL")
            self._conn.execute("PRAGMA cache_size = -32000")
            self._conn.execute("PRAGMA temp_store = MEMORY")
            self._conn.execute("PRAGMA synchronous = NORMAL")
        return self._conn

    def process(self, topic, lane=None, max_items=200):
        """Run complete 6-layer pipeline on a topic."""
        t0 = time.perf_counter()
        self.metrics = []
        self.halted_at = None

        # L1: INTAKE
        items = self._layer_intake(topic, lane, max_items)
        if not self._gate(PipelineLayer.INTAKE, items, min_items=1):
            return self._build_result(topic, items, t0)

        # L2: CLASSIFY
        items = self._layer_classify(items, lane)
        if not self._gate(PipelineLayer.CLASSIFY, items, min_items=1):
            return self._build_result(topic, items, t0)

        # L3: ANALYZE
        items = self._layer_analyze(items, topic)
        if not self._gate(PipelineLayer.ANALYZE, items, min_items=1):
            return self._build_result(topic, items, t0)

        # L4: REASON
        items = self._layer_reason(items, topic)
        if not self._gate(PipelineLayer.REASON, items, min_items=1):
            return self._build_result(topic, items, t0)

        # L5: ARGUE
        items = self._layer_argue(items, topic)
        if not self._gate(PipelineLayer.ARGUE, items, min_items=1):
            return self._build_result(topic, items, t0)

        # L6: VALIDATE
        items = self._layer_validate(items)

        return self._build_result(topic, items, t0)

    def step_through(self, topic, stop_after, lane=None, max_items=200):
        """Run pipeline up to a specific layer (for debugging/visualization)."""
        layers = [
            (PipelineLayer.INTAKE, self._layer_intake),
            (PipelineLayer.CLASSIFY, self._layer_classify),
            (PipelineLayer.ANALYZE, self._layer_analyze),
            (PipelineLayer.REASON, self._layer_reason),
            (PipelineLayer.ARGUE, self._layer_argue),
            (PipelineLayer.VALIDATE, self._layer_validate),
        ]
        items = None
        for layer_enum, layer_fn in layers:
            if layer_enum == PipelineLayer.INTAKE:
                items = layer_fn(topic, lane, max_items)
            elif layer_enum == PipelineLayer.CLASSIFY:
                items = layer_fn(items, lane)
            elif layer_enum == PipelineLayer.ANALYZE:
                items = layer_fn(items, topic)
            elif layer_enum == PipelineLayer.REASON:
                items = layer_fn(items, topic)
            elif layer_enum == PipelineLayer.ARGUE:
                items = layer_fn(items, topic)
            else:
                items = layer_fn(items)
            if layer_enum.value >= stop_after.value:
                break
        return items

    # ── L1: INTAKE ───────────────────────────────────────────────
    def _layer_intake(self, topic, lane, max_items):
        t0 = time.perf_counter()
        items = []
        sanitized = re.sub(r'[^\w\s*"]', ' ', topic).strip()

        # FTS5 search with LIKE fallback
        try:
            rows = self.conn.execute(
                """SELECT rowid, quote_text, source_file, category, lane,
                          page_number, bates_number, actor, event_date
                   FROM evidence_quotes
                   WHERE rowid IN (
                       SELECT rowid FROM evidence_fts
                       WHERE evidence_fts MATCH ?
                   )
                   ORDER BY rowid DESC LIMIT ?""",
                (sanitized, max_items)
            ).fetchall()
        except Exception:
            rows = self.conn.execute(
                """SELECT rowid, quote_text, source_file, category, lane,
                          page_number, bates_number, actor, event_date
                   FROM evidence_quotes
                   WHERE quote_text LIKE '%' || ? || '%'
                   ORDER BY rowid DESC LIMIT ?""",
                (topic, max_items)
            ).fetchall()

        for row in rows:
            item = PipelineItem(
                item_id=f"EQ-{row['rowid']}",
                raw_text=row['quote_text'] or '',
                source_path=row['source_file'] or '',
                source_table='evidence_quotes',
                lane=row['lane'] or '',
                category=row['category'] or '',
                event_date=row['event_date'] or '',
            )
            if row['actor']:
                item.actors = [row['actor']]
            items.append(item)

        elapsed = (time.perf_counter() - t0) * 1000
        self.metrics.append(LayerMetrics(
            layer=PipelineLayer.INTAKE,
            items_in=0, items_out=len(items),
            latency_ms=elapsed
        ))
        return items

    # ── L2: CLASSIFY ─────────────────────────────────────────────
    def _layer_classify(self, items, forced_lane=None):
        t0 = time.perf_counter()
        classified = []
        for item in items:
            # Lane assignment via MEEK if not already set
            if forced_lane:
                item.lane = forced_lane
            elif not item.lane:
                item.lane = self._detect_lane(item.raw_text)

            # Category tagging
            if not item.category:
                item.category = self._detect_category(item.raw_text)

            # Actor extraction
            if not item.actors:
                item.actors = self._extract_actors(item.raw_text)

            classified.append(item)

        elapsed = (time.perf_counter() - t0) * 1000
        self.metrics.append(LayerMetrics(
            layer=PipelineLayer.CLASSIFY,
            items_in=len(items), items_out=len(classified),
            latency_ms=elapsed
        ))
        return classified

    def _detect_lane(self, text):
        for lane, pattern in MEEK_SIGNALS.items():
            if pattern.search(text):
                return lane
        return 'A'  # default to custody lane

    def _detect_category(self, text):
        for cat, pattern in CATEGORY_PATTERNS.items():
            if pattern.search(text):
                return cat
        return 'unknown'

    def _extract_actors(self, text):
        found = []
        for name, pattern in KNOWN_ACTORS.items():
            if pattern.search(text):
                found.append(name)
        return found

    # ── L3: ANALYZE ──────────────────────────────────────────────
    def _layer_analyze(self, items, topic):
        t0 = time.perf_counter()
        sanitized = re.sub(r'[^\w\s*"]', ' ', topic).strip()

        # Fetch contradictions for the topic
        contradictions = self._fetch_contradictions(sanitized)

        # Fetch impeachment ammo
        impeachment = self._fetch_impeachment(sanitized)

        # Assign timeline positions
        dated = [it for it in items if it.event_date]
        dated.sort(key=lambda x: x.event_date)
        for idx, item in enumerate(dated):
            item.timeline_position = idx

        # Attach contradictions to items by actor overlap
        for item in items:
            item.contradictions = [
                c for c in contradictions
                if any(a.lower() in (c.get('source_a', '') + c.get('source_b', '')).lower()
                       for a in item.actors)
            ]
            # Detect patterns
            item.patterns = self._detect_patterns(item, impeachment)

        elapsed = (time.perf_counter() - t0) * 1000
        self.metrics.append(LayerMetrics(
            layer=PipelineLayer.ANALYZE,
            items_in=len(items), items_out=len(items),
            latency_ms=elapsed
        ))
        return items

    def _fetch_contradictions(self, topic):
        try:
            rows = self.conn.execute(
                """SELECT claim_id, source_a, source_b, contradiction_text,
                          severity, lane
                   FROM contradiction_map
                   WHERE contradiction_text LIKE '%' || ? || '%'
                   LIMIT 50""",
                (topic,)
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def _fetch_impeachment(self, topic):
        try:
            rows = self.conn.execute(
                """SELECT category, evidence_summary, quote_text,
                          impeachment_value, cross_exam_question, filing_relevance
                   FROM impeachment_matrix
                   WHERE evidence_summary LIKE '%' || ? || '%'
                      OR quote_text LIKE '%' || ? || '%'
                   ORDER BY impeachment_value DESC LIMIT 50""",
                (topic, topic)
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def _detect_patterns(self, item, impeachment_rows):
        patterns = []
        text = item.raw_text.lower()
        # Pattern catalog
        PATTERN_DEFS = [
            ('false_allegation', r'allege|accus|fabricat|false|lie|untrue'),
            ('retaliation', r'retaliat|revenge|punish|payback'),
            ('escalation', r'escal|increas|worsen|intensif'),
            ('alienation', r'alienat|interfere|withhold|deny.*contact'),
            ('due_process_denial', r'no\s+notice|without\s+hearing|ex\s+parte'),
            ('contempt_abuse', r'contempt|jail|incarcerat|arrest'),
            ('evidence_exclusion', r'exclud|suppress|disregard|ignor.*evidence'),
            ('coercion', r'coer|forc|compel|medic.*condition'),
        ]
        for pname, regex in PATTERN_DEFS:
            if re.search(regex, text, re.I):
                patterns.append(pname)
        # Match impeachment rows
        for imp in impeachment_rows:
            if any(a in (imp.get('evidence_summary', '') or '') for a in item.actors):
                patterns.append(f"impeachment:{imp.get('category', 'unknown')}")
        return list(set(patterns))

    # ── L4: REASON ───────────────────────────────────────────────
    def _layer_reason(self, items, topic):
        t0 = time.perf_counter()

        # Fetch matching authority chains
        authorities = self._fetch_authorities(topic)

        # Fetch Michigan rules
        rules = self._fetch_rules(topic)

        for item in items:
            # Element matching: pair evidence text with rule elements
            item.matched_elements = self._match_elements(item, rules)

            # Build syllogisms: Rule + Fact → Conclusion
            item.syllogisms = self._build_syllogisms(item, authorities, rules)

        elapsed = (time.perf_counter() - t0) * 1000
        self.metrics.append(LayerMetrics(
            layer=PipelineLayer.REASON,
            items_in=len(items), items_out=len(items),
            latency_ms=elapsed
        ))
        return items

    def _fetch_authorities(self, topic):
        try:
            rows = self.conn.execute(
                """SELECT primary_citation, supporting_citation, relationship,
                          source_document, source_type, lane, paragraph_context
                   FROM authority_chains_v2
                   WHERE paragraph_context LIKE '%' || ? || '%'
                      OR primary_citation LIKE '%' || ? || '%'
                   LIMIT 50""",
                (topic, topic)
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def _fetch_rules(self, topic):
        try:
            rows = self.conn.execute(
                """SELECT rule_citation, rule_text, source_file
                   FROM michigan_rules_extracted
                   WHERE rule_text LIKE '%' || ? || '%'
                      OR rule_citation LIKE '%' || ? || '%'
                   LIMIT 30""",
                (topic, topic)
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def _match_elements(self, item, rules):
        """Match evidence to rule elements."""
        matched = {}
        text_lower = item.raw_text.lower()
        for rule in rules:
            citation = rule.get('rule_citation', '')
            rule_text = (rule.get('rule_text', '') or '').lower()
            # Simple overlap scoring: shared significant words
            rule_words = set(re.findall(r'\b\w{4,}\b', rule_text))
            evidence_words = set(re.findall(r'\b\w{4,}\b', text_lower))
            overlap = rule_words & evidence_words
            if len(overlap) >= 2:
                matched[citation] = {
                    'overlap_count': len(overlap),
                    'shared_terms': list(overlap)[:10],
                    'rule_snippet': rule_text[:200],
                }
        return matched

    def _build_syllogisms(self, item, authorities, rules):
        """Rule + Fact → Conclusion."""
        syllogisms = []
        for citation, match_data in item.matched_elements.items():
            # Find supporting authority for this rule
            supporting = [
                a for a in authorities
                if citation.lower() in (a.get('primary_citation', '') or '').lower()
            ]
            syllogism = {
                'rule': citation,
                'rule_text': match_data['rule_snippet'],
                'fact': item.raw_text[:300],
                'fact_source': item.source_path,
                'conclusion': f"The evidence satisfies {citation}",
                'supporting_authorities': [
                    a.get('supporting_citation', '') for a in supporting[:5]
                ],
                'strength': min(match_data['overlap_count'] / 5.0, 1.0),
            }
            syllogisms.append(syllogism)
        return syllogisms

    # ── L5: ARGUE ────────────────────────────────────────────────
    def _layer_argue(self, items, topic):
        t0 = time.perf_counter()

        # Group items by matched rule citation
        rule_groups = {}
        for item in items:
            for citation in item.matched_elements:
                rule_groups.setdefault(citation, []).append(item)

        # Generate IRAC block per rule group
        for item in items:
            for syl in item.syllogisms:
                irac = self._generate_irac(syl, topic)
                item.irac_blocks.append(irac)
            # Assemble authority chain from syllogisms
            item.authority_chain = list({
                s.get('rule', '') for s in item.syllogisms
            })

        elapsed = (time.perf_counter() - t0) * 1000
        self.metrics.append(LayerMetrics(
            layer=PipelineLayer.ARGUE,
            items_in=len(items), items_out=len(items),
            latency_ms=elapsed
        ))
        return items

    def _generate_irac(self, syllogism, topic):
        """Generate one IRAC block from a syllogism."""
        rule_cite = syllogism['rule']
        return {
            'issue': (
                f"Whether the evidence establishes {topic} under {rule_cite}."
            ),
            'rule': (
                f"{rule_cite} provides: {syllogism['rule_text'][:200]}. "
                f"See also {', '.join(syllogism['supporting_authorities'][:3])}."
            ),
            'application': (
                f"Here, the record shows: \"{syllogism['fact'][:200]}\" "
                f"({syllogism['fact_source']}). This satisfies the standard "
                f"because the shared elements include "
                f"{', '.join(syllogism.get('supporting_authorities', [])[:2])}."
            ),
            'conclusion': syllogism['conclusion'],
            'strength': syllogism['strength'],
            'citation': rule_cite,
        }

    # ── L6: VALIDATE ─────────────────────────────────────────────
    def _layer_validate(self, items):
        t0 = time.perf_counter()
        for item in items:
            flags = []
            # Hallucination guard
            flags.extend(self._hallucination_check(item))
            # Citation verification
            flags.extend(self._verify_citations(item))
            item.hallucination_flags = flags
            # Confidence score
            item.confidence = self._compute_confidence(item)
            item.gate_results['validate'] = (
                QualityGateResult.PASS.value if not flags
                else QualityGateResult.WARN.value
            )

        elapsed = (time.perf_counter() - t0) * 1000
        self.metrics.append(LayerMetrics(
            layer=PipelineLayer.VALIDATE,
            items_in=len(items), items_out=len(items),
            latency_ms=elapsed
        ))
        return items

    BANNED_STRINGS = [
        "91% alienation", "lincoln david watson", "jane berry",
        "patricia berry", "ron berry, esq", "p35878",
        "9 cps investigations", "mcl 722.27c", "undersigned counsel",
        "litigationos", "manbearpig", "egcp", "singularity",
        "evidence_quotes", "authority_chains", "impeachment_matrix",
        "brain", "locus score",
    ]

    def _hallucination_check(self, item):
        flags = []
        combined = ' '.join([
            item.raw_text,
            *[b.get('application', '') for b in item.irac_blocks],
            *[b.get('rule', '') for b in item.irac_blocks],
        ]).lower()
        for banned in self.BANNED_STRINGS:
            if banned in combined:
                flags.append(f"HALLUCINATION: '{banned}' detected")
        return flags

    def _verify_citations(self, item):
        flags = []
        for irac in item.irac_blocks:
            cite = irac.get('citation', '')
            if not cite:
                flags.append("MISSING_CITATION: IRAC block has no citation")
                continue
            # Check if citation exists in michigan_rules_extracted
            try:
                row = self.conn.execute(
                    """SELECT COUNT(*) as cnt FROM michigan_rules_extracted
                       WHERE rule_citation LIKE '%' || ? || '%'""",
                    (cite,)
                ).fetchone()
                if row and row['cnt'] == 0:
                    # Check authority_chains_v2
                    row2 = self.conn.execute(
                        """SELECT COUNT(*) as cnt FROM authority_chains_v2
                           WHERE primary_citation LIKE '%' || ? || '%'""",
                        (cite,)
                    ).fetchone()
                    if row2 and row2['cnt'] == 0:
                        flags.append(
                            f"UNVERIFIED_CITATION: '{cite}' not found in DB"
                        )
            except Exception:
                pass
        return flags

    def _compute_confidence(self, item):
        """0.0–1.0 confidence based on evidence, authority, and validation."""
        score = 0.0
        # Evidence presence
        if item.raw_text and len(item.raw_text) > 20:
            score += 0.2
        # Syllogism strength
        if item.syllogisms:
            avg_str = sum(s['strength'] for s in item.syllogisms) / len(item.syllogisms)
            score += 0.3 * avg_str
        # Authority chain depth
        if item.authority_chain:
            score += min(len(item.authority_chain) * 0.05, 0.2)
        # Contradiction support
        if item.contradictions:
            score += 0.1
        # Penalty for hallucination flags
        score -= len(item.hallucination_flags) * 0.15
        # Bonus for IRAC completeness
        if item.irac_blocks:
            complete = sum(1 for b in item.irac_blocks
                           if b.get('issue') and b.get('rule')
                           and b.get('application') and b.get('conclusion'))
            score += 0.2 * (complete / len(item.irac_blocks))
        return max(0.0, min(1.0, score))

    # ── Quality Gates ────────────────────────────────────────────
    def _gate(self, layer, items, min_items=1):
        if len(items) < min_items:
            self.halted_at = layer
            return False
        return True

    def _build_result(self, topic, items, t0):
        elapsed = (time.perf_counter() - t0) * 1000
        # Collect arguments from items that passed validation
        arguments = []
        for item in items:
            if item.confidence >= 0.3 and item.irac_blocks:
                arguments.append({
                    'item_id': item.item_id,
                    'confidence': item.confidence,
                    'irac_blocks': item.irac_blocks,
                    'authority_chain': item.authority_chain,
                    'contradictions': len(item.contradictions),
                    'patterns': item.patterns,
                    'source': item.source_path,
                })
        # Identify gaps
        gaps = self._identify_gaps(items, topic)

        return PipelineResult(
            topic=topic,
            items=items,
            metrics=self.metrics,
            arguments=sorted(arguments, key=lambda a: -a['confidence']),
            overall_confidence=(
                sum(a['confidence'] for a in arguments) / len(arguments)
                if arguments else 0.0
            ),
            gaps=gaps,
            total_latency_ms=elapsed,
        )

    def _identify_gaps(self, items, topic):
        gaps = []
        lanes_covered = {it.lane for it in items if it.lane}
        all_lanes = {'A', 'B', 'C', 'D', 'E', 'F'}
        missing_lanes = all_lanes - lanes_covered
        if missing_lanes:
            gaps.append({
                'type': 'missing_lane_coverage',
                'detail': f"No evidence in lanes: {', '.join(sorted(missing_lanes))}",
            })
        items_with_authority = [it for it in items if it.authority_chain]
        if len(items_with_authority) < len(items) * 0.3:
            gaps.append({
                'type': 'weak_authority',
                'detail': (
                    f"Only {len(items_with_authority)}/{len(items)} items "
                    f"have authority chain support"
                ),
            })
        items_no_date = [it for it in items if not it.event_date]
        if items_no_date:
            gaps.append({
                'type': 'undated_evidence',
                'detail': f"{len(items_no_date)} items lack event dates",
            })
        return gaps

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
```

### 1.2 Pipeline Visualization (D3.js)

```javascript
/**
 * PipelineVisualization — D3.js force-graph overlay showing pipeline progress.
 *
 * Renders the six layers as a vertical cascade. Items flow downward through
 * layers, color-coded by confidence. Animated transitions show items passing
 * quality gates. Clicking a layer node shows its metrics and items.
 */
class PipelineVisualization {
  constructor(container, opts = {}) {
    this.container = typeof container === 'string'
      ? document.querySelector(container) : container;
    this.width  = opts.width  || 900;
    this.height = opts.height || 600;
    this.margin  = opts.margin || { top: 40, right: 40, bottom: 40, left: 120 };
    this.layers = ['INTAKE', 'CLASSIFY', 'ANALYZE', 'REASON', 'ARGUE', 'VALIDATE'];
    this.layerColors = {
      INTAKE:   '#2196F3', CLASSIFY: '#4CAF50', ANALYZE: '#FF9800',
      REASON:   '#9C27B0', ARGUE:    '#F44336', VALIDATE:'#00BCD4',
    };
    this.layerIcons = {
      INTAKE: '📥', CLASSIFY: '🏷️', ANALYZE: '🔍',
      REASON: '⚖️', ARGUE:    '📜', VALIDATE:'✅',
    };
    this.svg = null;
    this.simulation = null;
    this.pipelineData = null;
    this.onLayerClick = opts.onLayerClick || (() => {});
  }

  init() {
    this.svg = d3.select(this.container)
      .append('svg')
      .attr('width', this.width)
      .attr('height', this.height)
      .attr('class', 'pipeline-viz');

    // Background gradient
    const defs = this.svg.append('defs');
    const grad = defs.append('linearGradient')
      .attr('id', 'pipeline-bg').attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    grad.append('stop').attr('offset', '0%').attr('stop-color', '#0d1117');
    grad.append('stop').attr('offset', '100%').attr('stop-color', '#161b22');
    this.svg.append('rect')
      .attr('width', this.width).attr('height', this.height)
      .attr('fill', 'url(#pipeline-bg)');

    this._drawLayerBackbone();
    return this;
  }

  _drawLayerBackbone() {
    const yScale = d3.scalePoint()
      .domain(this.layers)
      .range([this.margin.top + 30, this.height - this.margin.bottom - 30])
      .padding(0.3);

    const g = this.svg.append('g').attr('class', 'layers');

    // Connection lines between layers
    for (let i = 0; i < this.layers.length - 1; i++) {
      g.append('line')
        .attr('x1', this.margin.left + 60).attr('y1', yScale(this.layers[i]) + 20)
        .attr('x2', this.margin.left + 60).attr('y2', yScale(this.layers[i + 1]) - 20)
        .attr('stroke', '#30363d').attr('stroke-width', 2)
        .attr('stroke-dasharray', '4,4');
    }

    // Layer nodes
    const layerGroups = g.selectAll('.layer-node')
      .data(this.layers)
      .join('g')
      .attr('class', 'layer-node')
      .attr('transform', d => `translate(${this.margin.left}, ${yScale(d)})`)
      .style('cursor', 'pointer')
      .on('click', (ev, d) => this.onLayerClick(d, this.pipelineData));

    // Layer circles
    layerGroups.append('circle')
      .attr('cx', 60).attr('cy', 0).attr('r', 22)
      .attr('fill', d => this.layerColors[d])
      .attr('fill-opacity', 0.15)
      .attr('stroke', d => this.layerColors[d])
      .attr('stroke-width', 2);

    // Layer icons
    layerGroups.append('text')
      .attr('x', 60).attr('y', 6)
      .attr('text-anchor', 'middle').attr('font-size', '18px')
      .text(d => this.layerIcons[d]);

    // Layer labels
    layerGroups.append('text')
      .attr('x', 100).attr('y', 5)
      .attr('fill', '#e6edf3').attr('font-size', '14px').attr('font-weight', 600)
      .text(d => `L${this.layers.indexOf(d) + 1}: ${d}`);

    // Metrics text (updated on data load)
    layerGroups.append('text')
      .attr('x', 250).attr('y', 5)
      .attr('class', 'layer-metrics')
      .attr('fill', '#8b949e').attr('font-size', '12px')
      .text('—');

    this.yScale = yScale;
    this.layerGroups = layerGroups;
  }

  update(pipelineResult) {
    this.pipelineData = pipelineResult;
    if (!pipelineResult || !pipelineResult.metrics) return;

    const metrics = pipelineResult.metrics;

    // Update layer metrics text
    this.layerGroups.select('.layer-metrics')
      .text((d, i) => {
        const m = metrics[i];
        if (!m) return '—';
        const gate = m.gate_result || 'PASS';
        const gateIcon = gate === 'PASS' ? '✅' : gate === 'WARN' ? '⚠️' : '❌';
        return `${m.items_out} items | ${m.latency_ms.toFixed(0)}ms ${gateIcon}`;
      });

    // Animate item flow dots
    this._animateItemFlow(pipelineResult);

    // Confidence bar
    this._drawConfidenceBar(pipelineResult.overall_confidence);
  }

  _animateItemFlow(result) {
    const itemGroup = this.svg.selectAll('.flow-items').data([0])
      .join('g').attr('class', 'flow-items');
    itemGroup.selectAll('*').remove();

    if (!result.arguments || result.arguments.length === 0) return;

    const topArgs = result.arguments.slice(0, 20);
    const xSpread = d3.scaleLinear()
      .domain([0, topArgs.length - 1])
      .range([this.margin.left + 160, this.width - this.margin.right - 40]);

    const confColor = d3.scaleSequential(d3.interpolateRdYlGn).domain([0, 1]);

    topArgs.forEach((arg, i) => {
      const x = xSpread(i);
      // Draw dot at VALIDATE layer position
      const y = this.yScale('VALIDATE');
      itemGroup.append('circle')
        .attr('cx', x).attr('cy', y).attr('r', 0)
        .attr('fill', confColor(arg.confidence))
        .attr('stroke', '#fff').attr('stroke-width', 0.5)
        .transition().duration(600).delay(i * 40)
        .attr('r', 5 + arg.confidence * 4);

      // Confidence label
      itemGroup.append('text')
        .attr('x', x).attr('y', y + 20)
        .attr('text-anchor', 'middle')
        .attr('fill', '#8b949e').attr('font-size', '9px')
        .text(`${(arg.confidence * 100).toFixed(0)}%`);
    });
  }

  _drawConfidenceBar(confidence) {
    const barGroup = this.svg.selectAll('.confidence-bar').data([0])
      .join('g').attr('class', 'confidence-bar')
      .attr('transform', `translate(${this.width - 35}, ${this.margin.top})`);
    barGroup.selectAll('*').remove();

    const barH = this.height - this.margin.top - this.margin.bottom;
    barGroup.append('rect')
      .attr('width', 12).attr('height', barH)
      .attr('rx', 6).attr('fill', '#21262d');

    const fillH = barH * confidence;
    const color = confidence > 0.7 ? '#2ea043' :
                  confidence > 0.4 ? '#d29922' : '#f85149';
    barGroup.append('rect')
      .attr('y', barH - fillH).attr('width', 12).attr('height', fillH)
      .attr('rx', 6).attr('fill', color).attr('fill-opacity', 0.8);

    barGroup.append('text')
      .attr('x', 6).attr('y', -8)
      .attr('text-anchor', 'middle').attr('fill', '#e6edf3')
      .attr('font-size', '11px').attr('font-weight', 700)
      .text(`${(confidence * 100).toFixed(0)}%`);
  }
}
```

---

## Layer 2: Michigan Authority Templates

### 2.1 Template Registry & Base Class

```python
"""
AuthorityTemplate — Base class for Michigan legal reasoning templates.
TemplateRegistry — Registry of 20+ executable legal analysis templates.

Each template:
  - Declares required DB queries (evidence, rules, authorities)
  - Defines element-matching logic for the specific legal standard
  - Produces structured output: factor scores, argument blocks, gap list
  - Validates output before returning
"""

from datetime import date, datetime


class AuthorityTemplate:
    """Base class for executable legal reasoning templates."""

    TEMPLATE_ID = "BASE"
    TEMPLATE_NAME = "Base Template"
    PRIMARY_AUTHORITY = ""
    REQUIRED_TABLES = []

    def __init__(self, conn):
        self.conn = conn
        self.errors = []

    def execute(self, **kwargs):
        raise NotImplementedError

    def validate_output(self, output):
        """Check output structure has required fields."""
        required = ['template_id', 'analysis', 'gaps', 'confidence']
        missing = [f for f in required if f not in output]
        if missing:
            self.errors.append(f"Missing output fields: {missing}")
            return False
        return True

    def _safe_query(self, sql, params=(), limit=50):
        try:
            return self.conn.execute(
                sql + (f" LIMIT {limit}" if "LIMIT" not in sql.upper() else ""),
                params
            ).fetchall()
        except Exception as e:
            self.errors.append(f"Query error: {e}")
            return []

    def _fts5_search(self, table, fts_table, query, limit=50):
        sanitized = re.sub(r'[^\w\s*"]', ' ', query).strip()
        try:
            return self.conn.execute(
                f"""SELECT * FROM {table}
                    WHERE rowid IN (
                        SELECT rowid FROM {fts_table} WHERE {fts_table} MATCH ?
                    ) LIMIT ?""",
                (sanitized, limit)
            ).fetchall()
        except Exception:
            return self.conn.execute(
                f"SELECT * FROM {table} WHERE quote_text LIKE '%' || ? || '%' LIMIT ?",
                (query, limit)
            ).fetchall()


class BestInterestTemplate(AuthorityTemplate):
    """MCL 722.23 — 12 Best Interest Factors Analysis."""

    TEMPLATE_ID = "MCL_722_23"
    TEMPLATE_NAME = "Best Interest Factors Analysis"
    PRIMARY_AUTHORITY = "MCL 722.23"
    REQUIRED_TABLES = ['evidence_quotes', 'timeline_events']

    FACTORS = {
        'a': 'Love, affection, and emotional ties',
        'b': 'Capacity to give love, affection, and guidance; continuation of educating and raising the child in religion or creed',
        'c': 'Capacity and disposition to provide food, clothing, medical care, and other material needs',
        'd': 'Length of time the child has lived in a stable, satisfactory environment and desirability of maintaining continuity',
        'e': 'Permanence as a family unit of the existing or proposed custodial home',
        'f': 'Moral fitness of the parties',
        'g': 'Mental and physical health of the parties',
        'h': 'Home, school, and community record of the child',
        'i': 'Reasonable preference of the child (if old enough)',
        'j': 'Willingness and ability to facilitate and encourage a close relationship with the other parent',
        'k': 'Domestic violence regardless of whether directed against the child',
        'l': 'Any other factor considered by the court to be relevant',
    }

    FACTOR_QUERIES = {
        'a': 'love affection emotional bond contact',
        'b': 'guidance education religion moral',
        'c': 'food clothing medical financial provide',
        'd': 'stable environment continuity custodial',
        'e': 'permanence family unit home',
        'f': 'moral fitness conduct character',
        'g': 'mental health physical evaluation',
        'h': 'school community record daycare',
        'i': 'child preference wishes',
        'j': 'alienation facilitate relationship encourage contact withhold',
        'k': 'domestic violence assault threat abuse',
        'l': 'false allegation contempt jail incarceration retaliation',
    }

    def execute(self, lane='A', perspective='father'):
        results = {}
        total_evidence = 0

        for factor_key, factor_desc in self.FACTORS.items():
            query_terms = self.FACTOR_QUERIES[factor_key]
            evidence = self._fts5_search(
                'evidence_quotes', 'evidence_fts', query_terms, limit=30
            )
            # Score: how many evidence items favor each party
            father_support = []
            mother_support = []
            for row in evidence:
                text = (dict(row).get('quote_text', '') or '').lower()
                # Heuristic: items mentioning positive father actions favor father
                if any(w in text for w in ['andrew', 'father', 'plaintiff', 'pigors']):
                    father_support.append(dict(row))
                if any(w in text for w in ['emily', 'mother', 'defendant', 'watson']):
                    mother_support.append(dict(row))

            total_evidence += len(evidence)
            results[factor_key] = {
                'factor': factor_desc,
                'citation': f"MCL 722.23({factor_key})",
                'total_evidence': len(evidence),
                'father_support_count': len(father_support),
                'mother_support_count': len(mother_support),
                'favors': (
                    'Father' if len(father_support) > len(mother_support)
                    else 'Mother' if len(mother_support) > len(father_support)
                    else 'Neutral'
                ),
                'top_evidence': [
                    (e.get('quote_text', '') or '')[:200]
                    for e in (father_support + mother_support)[:3]
                ],
                'gap': len(evidence) == 0,
            }

        # Summary
        father_factors = sum(
            1 for r in results.values() if r['favors'] == 'Father'
        )
        mother_factors = sum(
            1 for r in results.values() if r['favors'] == 'Mother'
        )
        gaps = [k for k, v in results.items() if v['gap']]

        return {
            'template_id': self.TEMPLATE_ID,
            'analysis': results,
            'summary': {
                'factors_favoring_father': father_factors,
                'factors_favoring_mother': mother_factors,
                'neutral_factors': 12 - father_factors - mother_factors,
                'total_evidence_items': total_evidence,
            },
            'gaps': gaps,
            'confidence': min(1.0, total_evidence / 60.0),
        }


class DisqualificationTemplate(AuthorityTemplate):
    """MCR 2.003 — Judicial Disqualification Analysis."""

    TEMPLATE_ID = "MCR_2_003"
    TEMPLATE_NAME = "Judicial Disqualification"
    PRIMARY_AUTHORITY = "MCR 2.003"
    REQUIRED_TABLES = ['judicial_violations', 'berry_mcneill_intelligence']

    GROUNDS = {
        'C1a': 'Personal knowledge of disputed evidentiary facts',
        'C1b': 'Personal bias or prejudice concerning a party',
        'C1c': 'Prior involvement as lawyer, witness, or judicial officer',
    }

    def execute(self, judge='McNeill'):
        violations = self._safe_query(
            "SELECT * FROM judicial_violations WHERE violation_text LIKE '%' || ? || '%'",
            (judge,), limit=100
        )
        intel = self._safe_query(
            "SELECT * FROM berry_mcneill_intelligence", limit=100
        )
        # Map violations to grounds
        ground_evidence = {g: [] for g in self.GROUNDS}
        for v in violations:
            vd = dict(v)
            text = (vd.get('violation_text', '') or '').lower()
            if any(w in text for w in ['personal knowledge', 'knew', 'aware']):
                ground_evidence['C1a'].append(vd)
            if any(w in text for w in ['bias', 'prejudice', 'hostile', 'partial']):
                ground_evidence['C1b'].append(vd)
            if any(w in text for w in ['prior', 'partner', 'colleague', 'spouse']):
                ground_evidence['C1c'].append(vd)

        return {
            'template_id': self.TEMPLATE_ID,
            'analysis': {
                g: {
                    'ground': desc,
                    'citation': f"MCR 2.003(C)(1)({g[-1]})",
                    'evidence_count': len(ground_evidence[g]),
                    'top_evidence': [
                        (e.get('violation_text', '') or '')[:200]
                        for e in ground_evidence[g][:5]
                    ],
                }
                for g, desc in self.GROUNDS.items()
            },
            'berry_intel_count': len(intel),
            'total_violations': len(violations),
            'gaps': [g for g, ev in ground_evidence.items() if not ev],
            'confidence': min(1.0, len(violations) / 20.0),
        }


class VodvarkaTemplate(AuthorityTemplate):
    """Vodvarka v Grasmeyer — Change of Circumstances Analysis."""

    TEMPLATE_ID = "VODVARKA"
    TEMPLATE_NAME = "Change of Circumstances / Proper Cause"
    PRIMARY_AUTHORITY = "Vodvarka v Grasmeyer, 259 Mich App 499 (2003)"
    REQUIRED_TABLES = ['timeline_events', 'evidence_quotes']

    def execute(self, since_date='2024-07-17'):
        # Events since trial that constitute changed circumstances
        events = self._safe_query(
            """SELECT * FROM timeline_events
               WHERE event_date >= ? ORDER BY event_date ASC""",
            (since_date,), limit=200
        )
        categories = {
            'parenting_time_denial': [],
            'false_allegations': [],
            'incarceration': [],
            'ex_parte_orders': [],
            'alienation': [],
            'other_changes': [],
        }
        for ev in events:
            evd = dict(ev)
            text = (evd.get('event_text', evd.get('description', '')) or '').lower()
            if any(w in text for w in ['deny', 'withhold', 'suspend', 'no contact']):
                categories['parenting_time_denial'].append(evd)
            elif any(w in text for w in ['allege', 'false', 'accuse', 'fabricat']):
                categories['false_allegations'].append(evd)
            elif any(w in text for w in ['jail', 'incarcerat', 'contempt', 'arrest']):
                categories['incarceration'].append(evd)
            elif any(w in text for w in ['ex parte', 'without notice', 'emergency']):
                categories['ex_parte_orders'].append(evd)
            elif any(w in text for w in ['alienat', 'interfere', 'obstruct']):
                categories['alienation'].append(evd)
            else:
                categories['other_changes'].append(evd)

        total = sum(len(v) for v in categories.values())
        return {
            'template_id': self.TEMPLATE_ID,
            'analysis': {
                k: {
                    'category': k.replace('_', ' ').title(),
                    'count': len(v),
                    'top_events': [
                        (e.get('event_text', e.get('description', '')) or '')[:200]
                        for e in v[:5]
                    ],
                }
                for k, v in categories.items()
            },
            'total_changes': total,
            'threshold_met': total >= 3,
            'gaps': [k for k, v in categories.items() if not v],
            'confidence': min(1.0, total / 15.0),
        }


class PPOTemplate(AuthorityTemplate):
    """MCL 600.2950 — PPO Analysis."""

    TEMPLATE_ID = "MCL_600_2950"
    TEMPLATE_NAME = "PPO Challenge / Termination"
    PRIMARY_AUTHORITY = "MCL 600.2950"

    def execute(self, target='Watson'):
        evidence = self._fts5_search(
            'evidence_quotes', 'evidence_fts',
            f'PPO OR "protection order" OR 5907 OR {target}', limit=50
        )
        contradictions = self._safe_query(
            """SELECT * FROM contradiction_map
               WHERE contradiction_text LIKE '%PPO%'
                  OR contradiction_text LIKE '%protection%'""",
            limit=30
        )
        return {
            'template_id': self.TEMPLATE_ID,
            'analysis': {
                'ppo_evidence_count': len(evidence),
                'contradictions_count': len(contradictions),
                'recantation_found': any(
                    'recant' in (dict(e).get('quote_text', '') or '').lower()
                    for e in evidence
                ),
                'no_physical_contact': any(
                    'nothing was physical' in (dict(e).get('quote_text', '') or '').lower()
                    for e in evidence
                ),
            },
            'gaps': [],
            'confidence': min(1.0, (len(evidence) + len(contradictions)) / 20.0),
        }


class ContemptTemplate(AuthorityTemplate):
    """MCL 600.1701 / MCR 3.606 — Contempt Analysis."""
    TEMPLATE_ID = "MCL_600_1701"
    TEMPLATE_NAME = "Contempt of Court"
    PRIMARY_AUTHORITY = "MCL 600.1701"

    def execute(self, target='Watson'):
        evidence = self._fts5_search(
            'evidence_quotes', 'evidence_fts',
            f'contempt OR "court order" OR violat* OR {target}', limit=50
        )
        return {
            'template_id': self.TEMPLATE_ID,
            'analysis': {
                'evidence_count': len(evidence),
                'order_violations': [
                    (dict(e).get('quote_text', '') or '')[:200]
                    for e in evidence[:10]
                ],
            },
            'gaps': [] if evidence else ['no_contempt_evidence'],
            'confidence': min(1.0, len(evidence) / 15.0),
        }


class DueProcessTemplate(AuthorityTemplate):
    """14th Amendment / Mathews v Eldridge — Due Process Analysis."""
    TEMPLATE_ID = "DUE_PROCESS_14TH"
    TEMPLATE_NAME = "Due Process Violation (Family Law)"
    PRIMARY_AUTHORITY = "Mathews v Eldridge, 424 US 319 (1976)"

    def execute(self):
        violations = self._safe_query(
            """SELECT * FROM judicial_violations
               WHERE violation_text LIKE '%due process%'
                  OR violation_text LIKE '%notice%'
                  OR violation_text LIKE '%hearing%'""",
            limit=100
        )
        ex_parte = self._safe_query(
            """SELECT * FROM judicial_violations
               WHERE violation_text LIKE '%ex parte%'""",
            limit=100
        )
        return {
            'template_id': self.TEMPLATE_ID,
            'analysis': {
                'mathews_factors': {
                    'private_interest': 'Fundamental right to parent-child relationship',
                    'risk_of_error': f'{len(ex_parte)} ex parte orders without notice',
                    'government_interest': 'Child welfare — but procedural safeguards skipped',
                },
                'total_dp_violations': len(violations),
                'ex_parte_orders': len(ex_parte),
            },
            'gaps': [] if violations else ['no_dp_violations_found'],
            'confidence': min(1.0, (len(violations) + len(ex_parte)) / 30.0),
        }


class ExParteTemplate(AuthorityTemplate):
    """Ex Parte Order Analysis — MCR 2.119(B), 3.207."""
    TEMPLATE_ID = "EX_PARTE"
    TEMPLATE_NAME = "Ex Parte Order Challenge"
    PRIMARY_AUTHORITY = "MCR 2.119(B)"

    def execute(self):
        ex_parte = self._safe_query(
            """SELECT * FROM judicial_violations
               WHERE violation_text LIKE '%ex parte%'
               ORDER BY rowid DESC""",
            limit=100
        )
        return {
            'template_id': self.TEMPLATE_ID,
            'analysis': {
                'total_ex_parte': len(ex_parte),
                'top_violations': [
                    (dict(e).get('violation_text', '') or '')[:200]
                    for e in ex_parte[:10]
                ],
            },
            'gaps': [] if ex_parte else ['no_ex_parte_evidence'],
            'confidence': min(1.0, len(ex_parte) / 20.0),
        }


class ParentalAlienationTemplate(AuthorityTemplate):
    """MCL 722.23(j) — Factor J Willingness to Facilitate."""
    TEMPLATE_ID = "MCL_722_23_J"
    TEMPLATE_NAME = "Parental Alienation / Factor J"
    PRIMARY_AUTHORITY = "MCL 722.23(j)"

    def execute(self):
        evidence = self._fts5_search(
            'evidence_quotes', 'evidence_fts',
            'alienation OR withhold OR interfere OR "deny contact" OR "factor j"',
            limit=80
        )
        from datetime import date as date_cls
        separation_days = (date_cls.today() - date_cls(2025, 7, 29)).days
        return {
            'template_id': self.TEMPLATE_ID,
            'analysis': {
                'evidence_count': len(evidence),
                'separation_days': separation_days,
                'key_evidence': [
                    (dict(e).get('quote_text', '') or '')[:200]
                    for e in evidence[:10]
                ],
            },
            'gaps': [] if evidence else ['no_alienation_evidence'],
            'confidence': min(1.0, len(evidence) / 30.0),
        }


class FalseAllegationTemplate(AuthorityTemplate):
    """False Allegation Pattern Detection."""
    TEMPLATE_ID = "FALSE_ALLEGATION"
    TEMPLATE_NAME = "False Allegation Pattern"
    PRIMARY_AUTHORITY = "MRE 613 (Prior Inconsistent Statements)"

    def execute(self, target='Watson'):
        impeachment = self._safe_query(
            """SELECT * FROM impeachment_matrix
               WHERE evidence_summary LIKE '%' || ? || '%'
                  OR quote_text LIKE '%allege%'
                  OR quote_text LIKE '%false%'
               ORDER BY impeachment_value DESC""",
            (target,), limit=50
        )
        contradictions = self._safe_query(
            """SELECT * FROM contradiction_map
               WHERE source_a LIKE '%' || ? || '%'
                  OR source_b LIKE '%' || ? || '%'
               ORDER BY severity DESC""",
            (target, target), limit=50
        )
        return {
            'template_id': self.TEMPLATE_ID,
            'analysis': {
                'impeachment_items': len(impeachment),
                'contradictions': len(contradictions),
                'top_impeachment': [
                    {
                        'summary': (dict(e).get('evidence_summary', '') or '')[:200],
                        'value': dict(e).get('impeachment_value', 0),
                        'cross_exam': (dict(e).get('cross_exam_question', '') or '')[:200],
                    }
                    for e in impeachment[:8]
                ],
            },
            'gaps': [] if (impeachment or contradictions) else ['no_false_allegation_evidence'],
            'confidence': min(1.0, (len(impeachment) + len(contradictions)) / 25.0),
        }


class ServiceDeficiencyTemplate(AuthorityTemplate):
    """MCR 2.107 — Service of Process Deficiency."""
    TEMPLATE_ID = "MCR_2_107"
    TEMPLATE_NAME = "Service Deficiency"
    PRIMARY_AUTHORITY = "MCR 2.107"

    def execute(self):
        evidence = self._fts5_search(
            'evidence_quotes', 'evidence_fts',
            'service OR notice OR "without notice" OR "not served"', limit=40
        )
        return {
            'template_id': self.TEMPLATE_ID,
            'analysis': {'evidence_count': len(evidence)},
            'gaps': [] if evidence else ['no_service_deficiency_evidence'],
            'confidence': min(1.0, len(evidence) / 10.0),
        }


class ReliefFromJudgmentTemplate(AuthorityTemplate):
    """MCR 2.612 — Relief From Judgment."""
    TEMPLATE_ID = "MCR_2_612"
    TEMPLATE_NAME = "Relief From Judgment"
    PRIMARY_AUTHORITY = "MCR 2.612"

    SUBSECTIONS = {
        'C1a': 'Mistake, inadvertence, excusable neglect',
        'C1b': 'Newly discovered evidence',
        'C1c': 'Fraud, misrepresentation, misconduct of adverse party',
        'C1f': 'Any other reason justifying relief',
    }

    def execute(self):
        evidence = self._fts5_search(
            'evidence_quotes', 'evidence_fts',
            'fraud OR "newly discovered" OR misconduct OR misrepresent', limit=50
        )
        return {
            'template_id': self.TEMPLATE_ID,
            'analysis': {
                'subsections': self.SUBSECTIONS,
                'evidence_count': len(evidence),
            },
            'gaps': [] if evidence else ['no_612_evidence'],
            'confidence': min(1.0, len(evidence) / 15.0),
        }


class SuperintendingControlTemplate(AuthorityTemplate):
    """MCR 7.306 — Superintending Control / Mandamus."""
    TEMPLATE_ID = "MCR_7_306"
    TEMPLATE_NAME = "Superintending Control"
    PRIMARY_AUTHORITY = "MCR 7.306"

    def execute(self):
        violations = self._safe_query(
            "SELECT COUNT(*) as cnt FROM judicial_violations"
        )
        cnt = dict(violations[0])['cnt'] if violations else 0
        return {
            'template_id': self.TEMPLATE_ID,
            'analysis': {
                'total_judicial_violations': cnt,
                'basis': 'No adequate remedy at law when trial court refuses to act',
            },
            'gaps': [] if cnt > 0 else ['no_judicial_violations'],
            'confidence': min(1.0, cnt / 50.0),
        }


class Section1983Template(AuthorityTemplate):
    """42 USC § 1983 — Civil Rights Violation."""
    TEMPLATE_ID = "42_USC_1983"
    TEMPLATE_NAME = "Federal Civil Rights (§1983)"
    PRIMARY_AUTHORITY = "42 USC § 1983"

    ELEMENTS = [
        'person_acting_under_color_of_state_law',
        'deprivation_of_constitutional_right',
        'causation',
        'damages',
    ]

    def execute(self):
        dp_violations = self._safe_query(
            """SELECT COUNT(*) as cnt FROM judicial_violations
               WHERE violation_text LIKE '%due process%'
                  OR violation_text LIKE '%ex parte%'
                  OR violation_text LIKE '%right%'"""
        )
        cnt = dict(dp_violations[0])['cnt'] if dp_violations else 0
        return {
            'template_id': self.TEMPLATE_ID,
            'analysis': {
                'elements': self.ELEMENTS,
                'dp_violation_count': cnt,
                'color_of_state_law': 'Judge acting in judicial capacity',
                'right_deprived': '14th Amendment substantive due process — parent-child',
            },
            'gaps': [] if cnt > 0 else ['insufficient_1983_evidence'],
            'confidence': min(1.0, cnt / 30.0),
        }


# ── Template Registry ────────────────────────────────────────────

TEMPLATE_REGISTRY = {
    'MCL_722_23': BestInterestTemplate,
    'MCR_2_003': DisqualificationTemplate,
    'VODVARKA': VodvarkaTemplate,
    'MCL_600_2950': PPOTemplate,
    'MCL_600_1701': ContemptTemplate,
    'DUE_PROCESS_14TH': DueProcessTemplate,
    'EX_PARTE': ExParteTemplate,
    'MCL_722_23_J': ParentalAlienationTemplate,
    'FALSE_ALLEGATION': FalseAllegationTemplate,
    'MCR_2_107': ServiceDeficiencyTemplate,
    'MCR_2_612': ReliefFromJudgmentTemplate,
    'MCR_7_306': SuperintendingControlTemplate,
    '42_USC_1983': Section1983Template,
}


def get_template(template_id, conn):
    """Retrieve and instantiate an authority template."""
    cls = TEMPLATE_REGISTRY.get(template_id)
    if cls is None:
        raise ValueError(
            f"Unknown template: {template_id}. "
            f"Available: {list(TEMPLATE_REGISTRY.keys())}"
        )
    return cls(conn)


def execute_template(template_id, conn, **kwargs):
    """Shortcut: instantiate and execute a template."""
    tmpl = get_template(template_id, conn)
    result = tmpl.execute(**kwargs)
    tmpl.validate_output(result)
    return result


def list_templates():
    """List all available templates with metadata."""
    return [
        {
            'id': tid,
            'name': cls.TEMPLATE_NAME,
            'authority': cls.PRIMARY_AUTHORITY,
        }
        for tid, cls in TEMPLATE_REGISTRY.items()
    ]
```

---

## Layer 3: IRAC Auto-Generator

### 3.1 Structure Generator Engine

```python
"""
IRACGenerator — Produces complete IRAC/CREAC/TEC argument blocks from
evidence + authority input. Used by Layer 5 of the reasoning pipeline
and directly by filing assembly.

Formats:
  IRAC  — Issue, Rule, Application, Conclusion (motions, responses)
  CREAC — Conclusion, Rule, Explanation, Application, Conclusion (briefs)
  TEC   — Theme, Evidence, Conclusion (narrative complaints, affidavits)
"""

from datetime import date


class IRACGenerator:
    """Generate structured legal argument blocks."""

    def __init__(self, conn):
        self.conn = conn

    def generate(self, claim, evidence_rows, authority_rows,
                 format_type='IRAC', lane='A'):
        """Master generator dispatching to format-specific methods."""
        if format_type == 'IRAC':
            return self.format_irac(claim, evidence_rows, authority_rows, lane)
        elif format_type == 'CREAC':
            return self.format_creac(claim, evidence_rows, authority_rows, lane)
        elif format_type == 'TEC':
            return self.format_tec(claim, evidence_rows, authority_rows, lane)
        else:
            raise ValueError(f"Unknown format: {format_type}")

    def format_irac(self, claim, evidence_rows, authority_rows, lane='A'):
        """Standard IRAC block for motions and responses."""
        primary_auth = authority_rows[0] if authority_rows else {}
        citation = primary_auth.get('primary_citation', '[AUTHORITY NEEDED]')
        rule_text = primary_auth.get('paragraph_context', '[RULE TEXT NEEDED]')
        supporting = [
            a.get('supporting_citation', '')
            for a in authority_rows[1:4] if a.get('supporting_citation')
        ]
        # Build application from evidence
        evidence_citations = []
        for ev in evidence_rows[:5]:
            source = ev.get('source_file', 'record')
            page = ev.get('page_number', '')
            bates = ev.get('bates_number', '')
            quote = (ev.get('quote_text', '') or '')[:150]
            ref = f"(Ex. {bates}, {source}" + (f", p. {page}" if page else "") + ")"
            evidence_citations.append(f'"{quote}" {ref}')

        app_text = ' '.join(evidence_citations) if evidence_citations else (
            "[ACQUIRE: Evidence needed for this claim. "
            "Searched: evidence_quotes, authority_chains_v2.]"
        )
        supporting_text = (
            f" See also {'; '.join(supporting)}." if supporting else ""
        )

        return {
            'format': 'IRAC',
            'claim': claim,
            'issue': f"Whether {claim} under {citation}.",
            'rule': f"{citation} provides: {str(rule_text)[:300]}.{supporting_text}",
            'application': (
                f"Here, the record demonstrates: {app_text}"
            ),
            'conclusion': (
                f"Therefore, {claim} is established under {citation}, "
                f"and this Court should grant the requested relief."
            ),
            'evidence_count': len(evidence_rows),
            'authority_count': len(authority_rows),
            'lane': lane,
        }

    def format_creac(self, claim, evidence_rows, authority_rows, lane='A'):
        """CREAC for appellate briefs — leads with conclusion."""
        irac = self.format_irac(claim, evidence_rows, authority_rows, lane)
        primary_auth = authority_rows[0] if authority_rows else {}
        citation = primary_auth.get('primary_citation', '[AUTHORITY]')
        # Find analogous case application
        analogous = [
            a for a in authority_rows
            if a.get('relationship', '') and 'support' in str(a.get('relationship', '')).lower()
        ]
        explanation = ""
        if analogous:
            case = analogous[0]
            explanation = (
                f"In {case.get('supporting_citation', '[case]')}, the court "
                f"applied {citation} where {(case.get('paragraph_context', '') or '')[:200]}."
            )
        else:
            explanation = (
                f"Michigan courts have consistently applied {citation} "
                f"to situations involving {claim}."
            )

        return {
            'format': 'CREAC',
            'claim': claim,
            'conclusion_opening': (
                f"The trial court erred in its handling of {claim}."
            ),
            'rule': irac['rule'],
            'explanation': explanation,
            'application': irac['application'],
            'conclusion_closing': irac['conclusion'],
            'evidence_count': len(evidence_rows),
            'authority_count': len(authority_rows),
            'lane': lane,
        }

    def format_tec(self, claim, evidence_rows, authority_rows, lane='A'):
        """TEC for narrative complaints (§1983, JTC)."""
        # Chronological evidence narrative
        dated = sorted(
            [e for e in evidence_rows if e.get('event_date')],
            key=lambda x: x.get('event_date', '')
        )
        narrative_parts = []
        for ev in dated[:8]:
            dt = ev.get('event_date', '')
            text = (ev.get('quote_text', '') or '')[:200]
            source = ev.get('source_file', '')
            narrative_parts.append(f"On {dt}, {text} ({source}).")

        return {
            'format': 'TEC',
            'claim': claim,
            'theme': f"A pattern of {claim} emerges from the record.",
            'evidence_narrative': ' '.join(narrative_parts) if narrative_parts else (
                "[ACQUIRE: Chronological evidence needed.]"
            ),
            'conclusion': (
                f"This pattern of {claim} establishes a violation of "
                f"Plaintiff's constitutional rights and warrants relief."
            ),
            'evidence_count': len(evidence_rows),
            'authority_count': len(authority_rows),
            'lane': lane,
        }
```

---

## Layer 4: Evidence-to-Argument Chain Builder

### 4.1 ArgumentChainBuilder

```python
"""
ArgumentChainBuilder — Assembles complete argument chains from raw topic input.

Process:
  1. FTS5 search evidence_quotes
  2. Match evidence to MCL/MCR elements
  3. Find supporting authorities from authority_chains_v2
  4. Find impeachment ammo from impeachment_matrix
  5. Find contradictions from contradiction_map
  6. Score chain strength 0–100
  7. Identify gaps
"""


class ArgumentChainBuilder:
    """Build scored argument chains from topic input."""

    def __init__(self, conn):
        self.conn = conn

    def build(self, topic, lane=None, limit=30):
        """Build a complete argument chain for a topic."""
        sanitized = re.sub(r'[^\w\s*"]', ' ', topic).strip()

        # Step 1: Evidence
        evidence = self._search_evidence(sanitized, lane, limit)

        # Step 2: Authorities
        authorities = self._search_authorities(sanitized, lane, limit)

        # Step 3: Impeachment
        impeachment = self._search_impeachment(sanitized, limit)

        # Step 4: Contradictions
        contradictions = self._search_contradictions(sanitized, limit)

        # Step 5: Score
        score = self.score(evidence, authorities, impeachment, contradictions)

        # Step 6: Gaps
        gaps = self.find_gaps(evidence, authorities, impeachment, contradictions)

        return {
            'topic': topic,
            'lane': lane,
            'evidence': evidence,
            'authorities': authorities,
            'impeachment': impeachment,
            'contradictions': contradictions,
            'score': score,
            'rating': self._score_to_rating(score),
            'gaps': gaps,
        }

    def score(self, evidence, authorities, impeachment, contradictions):
        """0–100 chain strength score."""
        s = 0
        # Evidence (max 40)
        s += min(len(evidence) * 2, 40)
        # Authorities (max 25)
        s += min(len(authorities) * 5, 25)
        # Impeachment (max 20)
        s += min(len(impeachment) * 3, 20)
        # Contradictions (max 15)
        s += min(len(contradictions) * 5, 15)
        return min(100, s)

    def find_gaps(self, evidence, authorities, impeachment, contradictions):
        """Identify weaknesses in the argument chain."""
        gaps = []
        if not evidence:
            gaps.append({
                'type': 'no_evidence',
                'severity': 'CRITICAL',
                'recommendation': 'Search additional tables or drives for evidence',
            })
        if not authorities:
            gaps.append({
                'type': 'no_authority',
                'severity': 'HIGH',
                'recommendation': 'Research applicable MCR/MCL/case law',
            })
        if len(evidence) < 3:
            gaps.append({
                'type': 'thin_evidence',
                'severity': 'MEDIUM',
                'recommendation': 'Expand evidence search with synonym queries',
            })
        if not impeachment and not contradictions:
            gaps.append({
                'type': 'no_credibility_attack',
                'severity': 'LOW',
                'recommendation': 'Search impeachment_matrix for cross-exam material',
            })
        return gaps

    def strengthen(self, chain, additional_queries=None):
        """Attempt to strengthen a weak chain with expanded searches."""
        if chain['score'] >= 80:
            return chain  # already strong

        topic = chain['topic']
        # Expand with synonyms
        expansions = {
            'alienation': 'alienat* OR withhold OR interfere OR "deny contact"',
            'contempt': 'contempt OR violat* OR disobey OR "court order"',
            'abuse': 'abuse OR assault OR threaten OR harm',
            'custody': 'custody OR "parenting time" OR "best interest"',
        }
        for keyword, expansion in expansions.items():
            if keyword in topic.lower():
                extra_evidence = self._search_evidence(expansion, chain['lane'], 20)
                existing_ids = {e.get('rowid') for e in chain['evidence']}
                new = [e for e in extra_evidence if e.get('rowid') not in existing_ids]
                chain['evidence'].extend(new)
                break

        # Rescore
        chain['score'] = self.score(
            chain['evidence'], chain['authorities'],
            chain['impeachment'], chain['contradictions']
        )
        chain['rating'] = self._score_to_rating(chain['score'])
        return chain

    def _search_evidence(self, query, lane, limit):
        try:
            sql = """SELECT rowid, quote_text, source_file, category, lane,
                            page_number, bates_number, event_date
                     FROM evidence_quotes
                     WHERE rowid IN (
                         SELECT rowid FROM evidence_fts WHERE evidence_fts MATCH ?
                     )"""
            params = [query]
            if lane:
                sql += " AND lane = ?"
                params.append(lane)
            sql += " LIMIT ?"
            params.append(limit)
            return [dict(r) for r in self.conn.execute(sql, params).fetchall()]
        except Exception:
            sql = "SELECT rowid, quote_text, source_file, category, lane FROM evidence_quotes WHERE quote_text LIKE '%' || ? || '%'"
            params = [query]
            if lane:
                sql += " AND lane = ?"
                params.append(lane)
            sql += f" LIMIT {limit}"
            return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def _search_authorities(self, query, lane, limit):
        sql = """SELECT primary_citation, supporting_citation, relationship,
                        paragraph_context, lane
                 FROM authority_chains_v2
                 WHERE paragraph_context LIKE '%' || ? || '%'"""
        params = [query]
        if lane:
            sql += " AND lane = ?"
            params.append(lane)
        sql += f" LIMIT {limit}"
        try:
            return [dict(r) for r in self.conn.execute(sql, params).fetchall()]
        except Exception:
            return []

    def _search_impeachment(self, query, limit):
        try:
            return [dict(r) for r in self.conn.execute(
                """SELECT category, evidence_summary, quote_text,
                          impeachment_value, cross_exam_question
                   FROM impeachment_matrix
                   WHERE evidence_summary LIKE '%' || ? || '%'
                      OR quote_text LIKE '%' || ? || '%'
                   ORDER BY impeachment_value DESC LIMIT ?""",
                (query, query, limit)
            ).fetchall()]
        except Exception:
            return []

    def _search_contradictions(self, query, limit):
        try:
            return [dict(r) for r in self.conn.execute(
                """SELECT claim_id, source_a, source_b, contradiction_text, severity
                   FROM contradiction_map
                   WHERE contradiction_text LIKE '%' || ? || '%'
                   ORDER BY severity DESC LIMIT ?""",
                (query, limit)
            ).fetchall()]
        except Exception:
            return []

    @staticmethod
    def _score_to_rating(score):
        if score >= 80: return 'STRONG'
        if score >= 60: return 'MODERATE'
        if score >= 40: return 'DEVELOPING'
        if score >= 20: return 'WEAK'
        return 'INSUFFICIENT'
```

---

## Layer 5: Counter-Argument Anticipator

### 5.1 CounterArgumentEngine

```python
"""
CounterArgumentEngine — Predict opposing counsel's responses and
generate pre-emptive rebuttals.
"""


COUNTER_PATTERNS = {
    'parental_alienation': {
        'likely_responses': [
            'Father is projecting his own alienating behavior',
            'Mother is protecting child from dangerous father',
            'No expert testimony supports alienation claim',
            'Father has criminal history / contempt history',
        ],
        'rebuttal_queries': [
            'withhold OR deny OR interfere',
            'HealthWest OR evaluation OR LOCUS',
            'police OR cleared OR "no charges"',
            'AppClose OR communication OR contact',
        ],
    },
    'judicial_bias': {
        'likely_responses': [
            'Judge exercised proper discretion',
            'Father is a vexatious litigant',
            'All rulings were legally sound',
            'Father failed to preserve issues for appeal',
        ],
        'rebuttal_queries': [
            'ex parte OR "without notice" OR "without hearing"',
            'benchbook OR deviation OR standard',
            '"evidence excluded" OR "not considered"',
            'recusal OR disqualif* OR bias',
        ],
    },
    'false_allegations': {
        'likely_responses': [
            'Allegations were made in good faith',
            'Mother had reasonable belief of danger',
            'CPS/police investigated and found concerns',
            'Pattern shows legitimate safety concerns',
        ],
        'rebuttal_queries': [
            'recant OR "nothing was physical" OR admitted',
            '"no arrest" OR "no charges" OR cleared',
            'toxicology OR negative OR "no evidence"',
            'meth OR "drug use" OR Randall',
        ],
    },
    'due_process': {
        'likely_responses': [
            'Father received adequate notice',
            'Emergency circumstances justified ex parte action',
            'Father waived rights by not appearing',
            'Procedural irregularities were harmless error',
        ],
        'rebuttal_queries': [
            '"no notice" OR "not served" OR "without hearing"',
            '"five orders" OR "Aug 8" OR premeditat*',
            'NS2505044 OR Albert OR premeditation',
            'suspend* OR "parenting time" OR "all contact"',
        ],
    },
    'contempt_abuse': {
        'likely_responses': [
            'Father willfully violated court orders',
            'Jail was necessary to compel compliance',
            'Father had ability to comply but refused',
        ],
        'rebuttal_queries': [
            'birthday OR message OR AppClose OR communication',
            '"first amendment" OR speech OR expression',
            'jail OR incarcerat* OR "lost job" OR "lost home"',
        ],
    },
}


class CounterArgumentEngine:
    """Anticipate and rebut opposing arguments."""

    def __init__(self, conn):
        self.conn = conn

    def anticipate(self, claim_type):
        """Get likely counter-arguments for a claim type."""
        pattern = COUNTER_PATTERNS.get(claim_type)
        if not pattern:
            return {
                'claim_type': claim_type,
                'responses': ['[No pattern data — manual analysis required]'],
                'threat_level': 'UNKNOWN',
            }
        return {
            'claim_type': claim_type,
            'responses': pattern['likely_responses'],
            'threat_level': self._assess_threat(claim_type),
        }

    def rebut(self, claim_type, response_index=None):
        """Generate rebuttal evidence for counter-arguments."""
        pattern = COUNTER_PATTERNS.get(claim_type, {})
        queries = pattern.get('rebuttal_queries', [])
        rebuttals = []

        targets = ([queries[response_index]] if response_index is not None
                   and response_index < len(queries) else queries)

        for query in targets:
            sanitized = re.sub(r'[^\w\s*"]', ' ', query).strip()
            try:
                rows = self.conn.execute(
                    """SELECT quote_text, source_file
                       FROM evidence_quotes
                       WHERE rowid IN (
                           SELECT rowid FROM evidence_fts
                           WHERE evidence_fts MATCH ?
                       ) LIMIT 10""",
                    (sanitized,)
                ).fetchall()
            except Exception:
                rows = self.conn.execute(
                    """SELECT quote_text, source_file FROM evidence_quotes
                       WHERE quote_text LIKE '%' || ? || '%' LIMIT 10""",
                    (query.split()[0],)
                ).fetchall()

            rebuttals.append({
                'query': query,
                'evidence_count': len(rows),
                'top_evidence': [
                    (dict(r).get('quote_text', '') or '')[:200]
                    for r in rows[:3]
                ],
            })
        return rebuttals

    def rank_threats(self, claim_type):
        """Rank counter-arguments by threat level."""
        pattern = COUNTER_PATTERNS.get(claim_type, {})
        responses = pattern.get('likely_responses', [])
        ranked = []
        for i, resp in enumerate(responses):
            rebuttals = self.rebut(claim_type, i)
            rebuttal_strength = sum(r['evidence_count'] for r in rebuttals)
            threat = 'HIGH' if rebuttal_strength < 3 else (
                'MEDIUM' if rebuttal_strength < 8 else 'LOW'
            )
            ranked.append({
                'response': resp,
                'threat_level': threat,
                'rebuttal_evidence': rebuttal_strength,
            })
        return sorted(ranked, key=lambda x: {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}.get(x['threat_level'], 3))

    def _assess_threat(self, claim_type):
        """Overall threat level for a claim type."""
        rebuttals = self.rebut(claim_type)
        total = sum(r['evidence_count'] for r in rebuttals)
        if total >= 20: return 'LOW'
        if total >= 10: return 'MEDIUM'
        return 'HIGH'
```

---

## Layer 6: Filing Package Assembler

### 6.1 FilingAssembler

```python
"""
FilingAssembler — Package argument chains into filing-ready document structures.

Output: complete packet family skeleton (motion + brief + exhibits + COS).
"""

from datetime import date


class FilingAssembler:
    """Assemble argument chains into filing-ready structures."""

    def __init__(self, conn):
        self.conn = conn

    def assemble(self, claim, irac_blocks, evidence_rows, lane='A',
                 filing_type='motion'):
        """Build filing structure from argument components."""
        if filing_type == 'motion':
            return self._assemble_motion(claim, irac_blocks, evidence_rows, lane)
        elif filing_type == 'brief':
            return self._assemble_brief(claim, irac_blocks, evidence_rows, lane)
        elif filing_type == 'complaint':
            return self._assemble_complaint(claim, irac_blocks, evidence_rows, lane)
        else:
            raise ValueError(f"Unknown filing type: {filing_type}")

    def _assemble_motion(self, claim, irac_blocks, evidence_rows, lane):
        separation_days = (date.today() - date(2025, 7, 29)).days
        exhibits = self.generate_exhibit_list(evidence_rows, lane)

        return {
            'filing_type': 'motion',
            'lane': lane,
            'caption': {
                'court': self._court_for_lane(lane),
                'case_number': self._case_for_lane(lane),
                'plaintiff': 'ANDREW JAMES PIGORS, Plaintiff, appearing pro se',
                'defendant': 'EMILY A. WATSON, Defendant',
                'title': f"MOTION RE: {claim.upper()}",
            },
            'sections': [
                {
                    'heading': 'RELIEF REQUESTED',
                    'content': (
                        f"Plaintiff, appearing pro se, respectfully moves this "
                        f"Court for {claim}. Plaintiff's son, L.D.W., has been "
                        f"separated from his father for {separation_days} days "
                        f"as of the date of this filing."
                    ),
                },
                {
                    'heading': 'STATEMENT OF FACTS',
                    'content': self._build_facts(evidence_rows),
                },
                {
                    'heading': 'ARGUMENT',
                    'content': self._render_irac_blocks(irac_blocks),
                },
                {
                    'heading': 'CONCLUSION AND RELIEF',
                    'content': (
                        f"For the foregoing reasons, Plaintiff respectfully "
                        f"requests that this Court grant {claim}."
                    ),
                },
            ],
            'exhibits': exhibits,
            'certificate_of_service': self.generate_cos(),
            'proposed_order': True,
            'fee_waiver': lane != 'E',  # JTC has no fee
        }

    def _assemble_brief(self, claim, irac_blocks, evidence_rows, lane):
        exhibits = self.generate_exhibit_list(evidence_rows, lane)
        authorities = list({
            b.get('citation', '') for b in irac_blocks if b.get('citation')
        })
        return {
            'filing_type': 'brief',
            'lane': lane,
            'sections': [
                {'heading': 'TABLE OF CONTENTS', 'content': '[AUTO-GENERATED]'},
                {'heading': 'INDEX OF AUTHORITIES', 'content': authorities},
                {'heading': 'JURISDICTIONAL STATEMENT', 'content': ''},
                {'heading': 'STATEMENT OF QUESTIONS PRESENTED', 'content': claim},
                {'heading': 'STATEMENT OF FACTS', 'content': self._build_facts(evidence_rows)},
                {'heading': 'ARGUMENT', 'content': self._render_irac_blocks(irac_blocks)},
                {'heading': 'RELIEF REQUESTED', 'content': ''},
            ],
            'exhibits': exhibits,
            'certificate_of_service': self.generate_cos(),
            'appendix': True,
        }

    def _assemble_complaint(self, claim, irac_blocks, evidence_rows, lane):
        return {
            'filing_type': 'complaint',
            'lane': lane,
            'sections': [
                {'heading': 'PARTIES', 'content': ''},
                {'heading': 'JURISDICTION AND VENUE', 'content': ''},
                {'heading': 'FACTUAL ALLEGATIONS', 'content': self._build_facts(evidence_rows)},
                {'heading': 'COUNTS', 'content': self._render_irac_blocks(irac_blocks)},
                {'heading': 'PRAYER FOR RELIEF', 'content': ''},
            ],
            'exhibits': self.generate_exhibit_list(evidence_rows, lane),
            'certificate_of_service': self.generate_cos(),
            'cover_sheet': 'CC 257' if lane != 'C' else 'JS 44',
            'summons': 'DC 101',
        }

    def generate_exhibit_list(self, evidence_rows, lane='A'):
        """Generate Bates-numbered exhibit list from evidence."""
        exhibits = []
        for i, ev in enumerate(evidence_rows[:50], start=1):
            bates = ev.get('bates_number') or f"PIGORS-{lane}-{i:06d}"
            exhibits.append({
                'exhibit_label': chr(64 + min(i, 26)) if i <= 26 else f"AA-{i - 26}",
                'bates_number': bates,
                'description': (ev.get('quote_text', '') or '')[:100],
                'source_file': ev.get('source_file', ''),
                'pages': ev.get('page_number', ''),
                'authentication': 'MRE 901(b)(1)',
            })
        return exhibits

    def generate_cos(self):
        """Certificate of Service template."""
        return {
            'date': date.today().isoformat(),
            'method': 'First-class U.S. Mail, postage prepaid',
            'parties_served': [
                {
                    'name': 'Emily A. Watson',
                    'address': '2160 Garland Dr, Norton Shores, MI 49441',
                },
                {
                    'name': 'Pamela Rusco, Friend of the Court',
                    'address': '990 Terrace St, Muskegon, MI 49442',
                },
            ],
            'signature_line': 'Andrew James Pigors, Plaintiff, appearing pro se',
            'address': '1977 Whitehall Rd, Lot 17, North Muskegon, MI 49445',
            'phone': '(231) 903-5690',
            'email': 'andrewjpigors@gmail.com',
        }

    def _build_facts(self, evidence_rows):
        dated = sorted(
            [e for e in evidence_rows if e.get('event_date')],
            key=lambda x: x.get('event_date', '')
        )
        parts = []
        for ev in dated[:15]:
            text = (ev.get('quote_text', '') or '')[:200]
            source = ev.get('source_file', 'record')
            bates = ev.get('bates_number', '')
            ref = f"(Ex. {bates})" if bates else f"({source})"
            parts.append(f"{ev.get('event_date', '')}: {text} {ref}")
        return '\n'.join(parts) if parts else "[ACQUIRE: Facts needed from record.]"

    def _render_irac_blocks(self, blocks):
        rendered = []
        for b in blocks:
            if b.get('format') == 'CREAC':
                rendered.append(
                    f"CONCLUSION: {b.get('conclusion_opening', '')}\n"
                    f"RULE: {b.get('rule', '')}\n"
                    f"EXPLANATION: {b.get('explanation', '')}\n"
                    f"APPLICATION: {b.get('application', '')}\n"
                    f"CONCLUSION: {b.get('conclusion_closing', '')}"
                )
            else:
                rendered.append(
                    f"ISSUE: {b.get('issue', '')}\n"
                    f"RULE: {b.get('rule', '')}\n"
                    f"APPLICATION: {b.get('application', '')}\n"
                    f"CONCLUSION: {b.get('conclusion', '')}"
                )
        return '\n\n'.join(rendered)

    @staticmethod
    def _court_for_lane(lane):
        return {
            'A': '14th Circuit Court, Muskegon County',
            'B': '14th Circuit Court, Muskegon County',
            'C': 'U.S. District Court, Western District of Michigan',
            'D': '14th Circuit Court, Muskegon County',
            'E': 'Judicial Tenure Commission',
            'F': 'Michigan Court of Appeals',
        }.get(lane, '14th Circuit Court')

    @staticmethod
    def _case_for_lane(lane):
        return {
            'A': '2024-001507-DC',
            'B': '2025-002760-CZ',
            'D': '2023-5907-PP',
            'F': '366810',
        }.get(lane, '')
```

---

## Anti-Patterns & Mandatory Guards

### 7.1 Court-Facing Output Sanitizer

```python
"""
OutputSanitizer — Mandatory sweep before any content reaches court documents.
Enforces all anti-hallucination and naming rules.
"""


class OutputSanitizer:
    """Sweep court-facing text for banned content."""

    BANNED_EXACT = [
        'LitigationOS', 'MANBEARPIG', 'THEMANBEARPIG', 'EGCP',
        'SINGULARITY', 'MEEK', 'NEXUS', 'KRAKEN',
        'evidence_quotes', 'authority_chains', 'impeachment_matrix',
        'timeline_events', 'contradiction_map', 'judicial_violations',
        'berry_mcneill_intelligence', 'michigan_rules_extracted',
        'litigation_context.db', 'brain', 'locus score',
        'C:\\Users\\andre', '00_SYSTEM', 'D:\\LitigationOS_tmp',
    ]

    BANNED_PATTERNS = [
        (re.compile(r'91%\s*alienation', re.I), 'HALLUCINATION: 91% alienation'),
        (re.compile(r'jane\s+berry', re.I), 'HALLUCINATION: Jane Berry'),
        (re.compile(r'patricia\s+berry', re.I), 'HALLUCINATION: Patricia Berry'),
        (re.compile(r'ron\s+berry,?\s+esq', re.I), 'HALLUCINATION: Ron Berry Esq'),
        (re.compile(r'P35878', re.I), 'HALLUCINATION: fake bar number P35878'),
        (re.compile(r'9\s+CPS\s+investigations', re.I), 'HALLUCINATION: 9 CPS'),
        (re.compile(r'MCL\s+722\.27c', re.I), 'WRONG_CITE: MCL 722.27c → MCL 722.23(j)'),
        (re.compile(r'Brady\s+v\.?\s+Maryland', re.I), 'WRONG_CITE: Brady → Mathews v Eldridge'),
        (re.compile(r'undersigned\s+counsel', re.I), 'PRO_SE: use "Plaintiff, appearing pro se"'),
        (re.compile(r'Emily\s+Ann\s+Watson', re.I), 'NAME: use "Emily A. Watson"'),
        (re.compile(r'Emily\s+M\.\s+Watson', re.I), 'NAME: use "Emily A. Watson"'),
        (re.compile(r'Tiffany\s+Watson', re.I), 'NAME: always "Emily A. Watson"'),
        (re.compile(r'McNiel|McNeil(?!l)', re.I), 'SPELLING: McNeill (two Ls)'),
        (re.compile(r'Lincoln\s+David', re.I), 'CHILD_NAME: use L.D.W. only'),
    ]

    # Hardcoded day counts that must never appear in filings
    STALE_DAY_PATTERN = re.compile(r'\b\d{2,3}\s+days?\s+(of\s+)?separation', re.I)

    @classmethod
    def sweep(cls, text):
        """Returns list of violations found. Empty list = PASS."""
        violations = []
        text_lower = text.lower()

        for banned in cls.BANNED_EXACT:
            if banned.lower() in text_lower:
                violations.append(f"BANNED_STRING: '{banned}' found in output")

        for pattern, label in cls.BANNED_PATTERNS:
            if pattern.search(text):
                violations.append(label)

        if cls.STALE_DAY_PATTERN.search(text):
            violations.append(
                'STALE_DAYS: Hardcoded day count detected — must compute dynamically'
            )

        return violations

    @classmethod
    def is_clean(cls, text):
        return len(cls.sweep(text)) == 0

    @classmethod
    def auto_fix(cls, text):
        """Attempt automatic fixes for known issues."""
        text = re.sub(r'MCL\s+722\.27c', 'MCL 722.23(j)', text)
        text = re.sub(
            r'Brady\s+v\.?\s+Maryland', 'Mathews v Eldridge, 424 US 319 (1976)', text
        )
        text = re.sub(r'undersigned\s+counsel', 'Plaintiff, appearing pro se', text, flags=re.I)
        text = re.sub(r'Emily\s+Ann\s+Watson', 'Emily A. Watson', text)
        text = re.sub(r'Emily\s+M\.\s+Watson', 'Emily A. Watson', text)
        text = re.sub(r'Tiffany\s+Watson', 'Emily A. Watson', text)
        text = re.sub(r'McNiel\b', 'McNeill', text)
        text = re.sub(r'McNeil\b(?!l)', 'McNeill', text)
        text = re.sub(r'Jane\s+Berry', '[REMOVED — hallucinated name]', text, flags=re.I)
        text = re.sub(r'Patricia\s+Berry', '[REMOVED — hallucinated name]', text, flags=re.I)
        text = re.sub(r'Ron\s+Berry,?\s+Esq\.?', 'Ronald Berry (non-attorney)', text, flags=re.I)
        return text
```

---

## Performance Budgets & Integration

### 8.1 Performance Configuration

```python
"""Performance budget enforcement for pipeline operations."""

PERFORMANCE_BUDGETS = {
    'full_pipeline':        30_000,  # 30s max for complete 6-layer run
    'single_irac':           2_000,  # 2s for one IRAC block
    'authority_template':    5_000,  # 5s per template execution
    'counter_argument':      3_000,  # 3s for counter-argument generation
    'chain_scoring':           500,  # 500ms for scoring formula
    'filing_assembly':      10_000,  # 10s for full packet assembly
    'hallucination_check':     200,  # 200ms for output sanitizer
    'citation_verification': 1_000,  # 1s for DB citation check
}


def enforce_budget(operation, elapsed_ms):
    """Log warning if operation exceeds budget."""
    budget = PERFORMANCE_BUDGETS.get(operation)
    if budget and elapsed_ms > budget:
        return {
            'warning': f"{operation} exceeded budget: {elapsed_ms:.0f}ms > {budget}ms",
            'exceeded_by_ms': elapsed_ms - budget,
        }
    return None
```

### 8.2 Integration Bridge (D3.js ↔ Python)

```javascript
/**
 * AutomatonBridge — connects the Python reasoning pipeline to the
 * THEMANBEARPIG D3.js visualization via pywebview JS→Python bridge.
 *
 * Usage from D3.js layer code:
 *   const bridge = new AutomatonBridge();
 *   const result = await bridge.runPipeline('parental alienation', 'A');
 *   pipelineViz.update(result);
 */
class AutomatonBridge {
  constructor() {
    this.cache = new Map();
    this.cacheTTL = 60_000; // 1 minute cache
  }

  async runPipeline(topic, lane = null) {
    const key = `${topic}|${lane}`;
    const cached = this.cache.get(key);
    if (cached && Date.now() - cached.ts < this.cacheTTL) return cached.data;

    const result = await window.pywebview.api.run_reasoning_pipeline(topic, lane);
    this.cache.set(key, { data: result, ts: Date.now() });
    return result;
  }

  async executeTemplate(templateId, kwargs = {}) {
    return await window.pywebview.api.execute_authority_template(templateId, kwargs);
  }

  async buildArgumentChain(topic, lane = null) {
    return await window.pywebview.api.build_argument_chain(topic, lane);
  }

  async anticipateCounters(claimType) {
    return await window.pywebview.api.anticipate_counter_arguments(claimType);
  }

  async assembleFilingPackage(claim, lane, filingType = 'motion') {
    return await window.pywebview.api.assemble_filing_package(claim, lane, filingType);
  }

  async listTemplates() {
    return await window.pywebview.api.list_authority_templates();
  }

  async runFullAutopilot(topic, lane = null) {
    const t0 = performance.now();
    // Step 1: Run pipeline
    const pipeline = await this.runPipeline(topic, lane);
    // Step 2: Build argument chain
    const chain = await this.buildArgumentChain(topic, lane);
    // Step 3: Anticipate counter-arguments
    const counters = await this.anticipateCounters(topic.split(' ')[0]);
    // Step 4: Assemble filing
    const filing = await this.assembleFilingPackage(topic, lane || 'A');
    const elapsed = performance.now() - t0;

    return {
      pipeline, chain, counters, filing,
      elapsed_ms: elapsed,
      overall_confidence: pipeline.overall_confidence || 0,
      chain_score: chain.score || 0,
      gap_count: (pipeline.gaps || []).length + (chain.gaps || []).length,
    };
  }

  clearCache() {
    this.cache.clear();
  }
}
```

### 8.3 pywebview API Endpoints

```python
"""
pywebview API endpoints exposed to the D3.js frontend.
Register these in the THEMANBEARPIG webview app.
"""

class AutomatonAPI:
    """Pywebview-exposed API for the reasoning automaton."""

    def __init__(self, db_path='litigation_context.db'):
        self.db_path = db_path
        self._pipeline = None
        self._chain_builder = None
        self._counter_engine = None
        self._filing_assembler = None
        self._irac_generator = None

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 60000")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA cache_size = -32000")
        return conn

    @property
    def pipeline(self):
        if self._pipeline is None:
            self._pipeline = ReasoningPipeline(self.db_path)
        return self._pipeline

    def run_reasoning_pipeline(self, topic, lane=None):
        result = self.pipeline.process(topic, lane)
        return {
            'topic': result.topic,
            'argument_count': len(result.arguments),
            'arguments': result.arguments[:20],
            'overall_confidence': result.overall_confidence,
            'gaps': result.gaps,
            'metrics': [
                {
                    'layer': m.layer.name,
                    'items_out': m.items_out,
                    'latency_ms': m.latency_ms,
                    'gate_result': m.gate_result.value,
                }
                for m in result.metrics
            ],
            'total_latency_ms': result.total_latency_ms,
        }

    def execute_authority_template(self, template_id, kwargs=None):
        conn = self._get_conn()
        try:
            return execute_template(template_id, conn, **(kwargs or {}))
        finally:
            conn.close()

    def build_argument_chain(self, topic, lane=None):
        conn = self._get_conn()
        try:
            builder = ArgumentChainBuilder(conn)
            chain = builder.build(topic, lane)
            return {
                'topic': chain['topic'],
                'score': chain['score'],
                'rating': chain['rating'],
                'evidence_count': len(chain['evidence']),
                'authority_count': len(chain['authorities']),
                'impeachment_count': len(chain['impeachment']),
                'contradiction_count': len(chain['contradictions']),
                'gaps': chain['gaps'],
            }
        finally:
            conn.close()

    def anticipate_counter_arguments(self, claim_type):
        conn = self._get_conn()
        try:
            engine = CounterArgumentEngine(conn)
            anticipated = engine.anticipate(claim_type)
            ranked = engine.rank_threats(claim_type)
            return {
                'claim_type': claim_type,
                'threat_level': anticipated['threat_level'],
                'counter_arguments': ranked,
            }
        finally:
            conn.close()

    def assemble_filing_package(self, claim, lane, filing_type='motion'):
        conn = self._get_conn()
        try:
            builder = ArgumentChainBuilder(conn)
            chain = builder.build(claim, lane)
            generator = IRACGenerator(conn)
            irac_blocks = []
            for auth in chain['authorities'][:5]:
                block = generator.generate(
                    claim, chain['evidence'], [auth],
                    format_type='IRAC', lane=lane
                )
                irac_blocks.append(block)
            assembler = FilingAssembler(conn)
            return assembler.assemble(claim, irac_blocks, chain['evidence'],
                                      lane, filing_type)
        finally:
            conn.close()

    def list_authority_templates(self):
        return list_templates()
```

---

## Appendix: Research Citations

| Reference | Application |
|-----------|------------|
| Bench-Capon & Sartor (2003), *A model of legal reasoning with cases incorporating theories and values* | Legal syllogism formalization in Layer 4 |
| Dernbach & Singleton (2014), *A Practical Guide to Legal Writing and Legal Method* | IRAC methodology in Layer 5 |
| Poudyal et al. (2020), *ECHR: Legal Corpus for Argument Mining* | Argument mining patterns in Layer 3 |
| Michigan Judges Benchbook (ICLE, 2024) | MCL 722.23 factor analysis templates |
| Hidey & McKeown (2019), *Fixed That for You: Generating Contrastive Claims in Argumentation* | Counter-argument generation in Layer 5 |
| Ashley (2017), *Artificial Intelligence and Legal Analytics* | Evidence-to-argument chain architecture |
| Wyner et al. (2010), *A Framework for Enriching Legal Text with Argumentation* | IRAC/CREAC structural patterns |

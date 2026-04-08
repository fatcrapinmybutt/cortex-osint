---
name: SINGULARITY-litigation-warfare
version: "2.0.0"
description: "Transcendent litigation warfare system for LitigationOS. Use when: evidence hunting, adversary profiling, custody analysis, MCL 722.23 factors, impeachment prep, contradiction detection, deadline tracking, docket management, case operations, best interest analysis, parental alienation documentation, false allegation rebuttal, credibility assessment, witness preparation, deposition strategy."
---

# SINGULARITY-litigation-warfare — Master Litigation Combat System

> **Tier:** COMBAT | **Domain:** Evidence Fusion · Adversary Profiling · Custody Strategy · Case Operations
> **Absorbs:** adversary-warfare + case-operations + custody-strategy + evidence-intelligence
> **Activation:** evidence, adversary, custody, best interest, MCL 722.23, impeachment, deadline, docket

---

## LAYER 1: EVIDENCE INTELLIGENCE

### 1.1 Evidence Hunting — Tool Selection Matrix

| Scenario | Primary Tool | Fallback | Speed |
|----------|-------------|----------|-------|
| Keyword search across evidence | `search_evidence` (FTS5) | `query_litigation_db` with LIKE | ~5ms |
| Cross-table fusion (5 sources) | `nexus_fuse` | Manual 5-query sequence | ~20ms |
| Semantic similarity search | `vector_search` (LanceDB 75K vectors) | FTS5 keyword fallback | ~10ms |
| Impeachment ammunition | `search_impeachment` | `query_litigation_db` on impeachment_matrix | ~5ms |
| Contradiction detection | `search_contradictions` | Manual cross-reference | ~5ms |
| Authority chain lookup | `search_authority_chains` | `lookup_authority` | ~5ms |
| Argument synthesis + scoring | `nexus_argue` | Manual evidence + authority assembly | ~30ms |
| Timeline event search | `timeline_search` | FTS5 on timeline_fts | ~5ms |
| Full-spectrum topic search | `nexus_fuse` with topic | N/A | ~25ms |

### 1.2 Evidence Atom Structure

Every evidence atom in `evidence_quotes` carries these fields:

```
quote_text       — Verbatim extracted text (NEVER paraphrased)
source_file      — Absolute path to source document
page_number      — Page within source (NULL if non-paginated)
bates_number     — PIGORS-{LANE}-{NNNNNN} stamp (NULL until assigned)
category         — One of 20 evidence categories
lane             — Case lane: A (custody), B (housing), D (PPO), E (judicial), F (appeal)
relevance_score  — 0.0-1.0 computed relevance
actor            — Person referenced or acting
event_date       — Date of event (ISO 8601)
is_duplicate     — 0 = unique, 1 = dedup'd
```

### 1.3 FTS5 Search Patterns (Rule 15 Compliant)

**MANDATORY sanitization before ANY FTS5 query:**

```python
import re

def safe_fts5(query: str) -> str:
    """Sanitize input for FTS5 MATCH — Rule 15."""
    return re.sub(r'[^\w\s*"]', ' ', query).strip()

# Usage with fallback:
try:
    rows = conn.execute(
        "SELECT quote_text, source_file FROM evidence_fts WHERE evidence_fts MATCH ? LIMIT 25",
        (safe_fts5(query),)
    ).fetchall()
except Exception:
    # LIKE fallback — parameterized, never interpolated
    rows = conn.execute(
        "SELECT quote_text, source_file FROM evidence_quotes WHERE quote_text LIKE '%' || ? || '%' LIMIT 25",
        (query,)
    ).fetchall()
```

**FTS5 query syntax cheat sheet:**
- AND (implicit): `custody alienation` → both terms
- OR: `custody OR parenting` → either term
- NOT: `custody NOT ppo` → exclude
- Phrase: `"parental alienation"` → exact phrase
- Prefix: `custod*` → prefix match
- Column filter: `quote_text:alienation` → single column

### 1.4 Cross-Table Fusion Methodology

`nexus_fuse` searches 5 tables simultaneously for a topic:

```
evidence_quotes  (FTS5)  → Direct evidence atoms with quotes
timeline_events  (FTS5)  → Chronological events with dates
police_reports   (LIKE)  → NSPD incident reports
impeachment_matrix (LIKE) → Cross-examination ammunition
authority_chains (LIKE)  → Legal authority support
```

**When to use nexus_fuse vs individual tools:**
- **nexus_fuse**: Broad topic investigation ("What do we know about X?")
- **search_evidence**: Targeted quote extraction
- **search_impeachment**: Building cross-exam questions
- **nexus_argue**: Synthesizing a complete argument chain with strength scoring

### 1.5 Evidence Grading Criteria

| Grade | Score | Criteria |
|-------|-------|----------|
| **HIGH** | 0.8-1.0 | Direct quote, dated, attributed, corroborated by 2+ sources |
| **MEDIUM** | 0.5-0.79 | Indirect evidence, single source, requires authentication context |
| **LOW** | 0.0-0.49 | Circumstantial, undated, unattributed, or uncorroborated |

HIGH findings auto-persist to `evidence_quotes` DB. MEDIUM reviewed before persist. LOW flagged for manual triage.

### 1.6 Deduplication Protocol

**Content-based dedup (NOT hash-only — user mandate):**

1. SHA-256 hash clusters potential duplicates
2. Open BOTH files, compare first 1000 + last 500 characters
3. If content matches → mark `is_duplicate = 1`, preserve original
4. Record in `dedup_clusters` with both paths + match confidence
5. **NEVER delete** — move duplicate to `I:\` dedup folder

---

## LAYER 2: ADVERSARY PROFILING

### 2.1 Deep Adversary Scan Methodology

**Tool chain for building adversary dossiers:**

```
Step 1: adversary_scan(target="Emily Watson")
        → Queries evidence_quotes, impeachment_matrix, contradiction_map,
          timeline_events, judicial_violations, berry_mcneill_intelligence

Step 2: lexos_adversary(person="Emily Watson")
        → Builds comprehensive profile: credibility score, weaknesses,
          contradiction count, impeachment ammunition

Step 3: search_impeachment(target="Watson", min_severity=7)
        → High-value cross-examination material

Step 4: search_contradictions(entity="Watson", severity="critical")
        → Self-contradictions and inter-witness contradictions
```

### 2.2 Credibility Scoring Algorithm

```
credibility_score = 100 - (
    contradiction_count * 5 +
    false_allegation_count * 10 +
    projection_count * 8 +
    inconsistent_statement_count * 3 +
    debunked_claim_count * 15
)
# Clamped to 0-100 range
```

**Emily A. Watson credibility factors:**
- 7+ debunked false allegations (arsenic, assault, drugs, sexual assault, child danger, mental instability, cocaine straw)
- Meth admission projection (Officer Randall report: Emily admitted meth use → accused Andrew)
- PPO filed 2 days after recanting ("nothing was physical" — NSPD-2023-08121)
- Albert Watson premeditation admission (NS2505044 — "so Emily can go tomorrow to get an Ex Parte order")
- 305+ interference incidents documented via AppClose

### 2.3 False Allegation Pattern Identification

| Allegation | Evidence Count | Status | Key Rebuttal |
|------------|---------------|--------|-------------|
| Arsenic/poisoning | 37 | DEBUNKED | ER toxicology NEGATIVE |
| Physical assault | 0 direct | DEBUNKED | No police report, no injuries |
| Sexual assault | 15 | DEBUNKED | No investigation initiated |
| Cocaine straw | 5 | DEBUNKED | Never tested |
| Meth use (projection) | 160 | DEBUNKED | Emily admitted to meth — Officer Randall |
| Child abuse/danger | 49 | DEBUNKED | HealthWest all clear |
| Mental instability | 91 | DEBUNKED | LOCUS=12, Level One |

**Pattern:** Emily's allegations are projections of her own conduct. Each allegation escalates after Andrew asserts parental rights.

### 2.4 Watson-Specific Adversary Intelligence

**Albert Watson — Key Adverse Witness:**
- NS2505044 (Aug 7, 2025): Told police "They want this documented so Emily can go tomorrow to get an Ex Parte order for full custody of her son"
- Kitchen recording (Nov 2024): "I will make sure you don't see your son"
- Called police TO CREATE a record for Emily's ex parte filing
- Audio: `I:\08_AUDIO\albert and Emily audio nov 30 2023.mp3`
- Video: `I:\Appclose\EVERYTHIING\videos\Albertemily.mp4`

**Ronald Berry — Shadow Legal Operations:**
- NON-ATTORNEY providing legal assistance to Emily
- Related to Cavan Berry (McNeill's spouse)
- Lives at 2160 Garland Dr with Emily
- Coordinated ex parte communications with court

---

## LAYER 3: CUSTODY STRATEGY (MCL 722.23)

### 3.1 All 12 Best Interest Factors — Scoring Methodology

| Factor | MCL 722.23 | Focus | Father Score | Key Evidence |
|--------|-----------|-------|-------------|-------------|
| (a) | Love, affection, emotional ties | Bond quality | STRONG | 305+ AppClose contacts, birthday messages |
| (b) | Capacity to give love/guidance | Parenting ability | STRONG | HealthWest LOCUS=12 |
| (c) | Capacity to provide food/shelter/medical | Material provision | MODERATE | 2 homes lost to incarceration |
| (d) | Length of time in stable environment | ECE stability | CONTESTED | Emily's withholding disrupted ECE |
| (e) | Permanence of family unit | Continuity | CONTESTED | Father excluded by court orders |
| (f) | Moral fitness | Character | STRONG (father) | Zero arrests vs Emily meth admission |
| (g) | Mental/physical health | Fitness | STRONG | HealthWest: Psychosis=0, Substance=0, Danger=0 |
| (h) | Home, school, community record | Integration | MODERATE | Disrupted by incarceration/orders |
| (i) | Reasonable preference of child | Child's voice | N/A | L.D.W. too young (DOB: Nov 9, 2022) |
| (j) | Willingness to facilitate relationship | Alienation | CRITICAL | Emily withholds; Father facilitates |
| (k) | Domestic violence | DV history | CRITICAL | Emily's false allegations debunked |
| (l) | Other relevant factors | Catch-all | STRONG | Judicial cartel, 59 days jail |

### 3.2 Factor (j) — Alienation Documentation

**Query for alienation evidence:**
```sql
SELECT quote_text, source_file, event_date, actor
FROM evidence_quotes
WHERE (category LIKE '%alienation%' OR quote_text LIKE '%withhold%'
       OR quote_text LIKE '%denied parenting%' OR quote_text LIKE '%no contact%')
  AND lane = 'A' AND is_duplicate = 0
ORDER BY event_date DESC LIMIT 50;
```

**Key alienation timeline:**
- Oct 20, 2024: Emily begins withholding child
- Jul 29, 2025: LAST CONTACT — Father's last day with L.D.W.
- Aug 8, 2025: Five ex parte orders suspend ALL parenting time
- Sep 28, 2025: Custody order — Emily 100%, Father 0%
- TODAY: `(today - date(2025,7,29)).days` days of separation (COMPUTE DYNAMICALLY)

### 3.3 Vodvarka Standard (Change of Circumstances)

*Vodvarka v Grasmeyer*, 259 Mich App 499 (2003):
- Must show **proper cause** or **change of circumstances** before court revisits custody
- Change must be significant, material, and since the last custody order
- Changes: 230+ day separation, incarceration based on birthday messages, premeditated ex parte attack

### 3.4 Emergency Motion Strategies

**Trigger conditions for emergency motion:**
1. Child safety at immediate risk
2. Complete denial of parenting time (>30 days)
3. Ex parte orders without notice
4. Constitutional rights actively being violated

**Emergency Motion filed Mar 25, 2026** — restore parenting time.

---

## LAYER 4: CASE OPERATIONS

### 4.1 Deadline Management

```python
# Check all deadlines within 30 days:
check_deadlines(days_ahead=30)

# Compute deadlines from a trigger event:
compute_deadlines(trigger_event="motion_served", trigger_date="2026-04-01")
# Returns: response_due (21 days), hearing_date, etc.
```

**Current critical deadlines:**
- COA Brief 366810 — due per court schedule
- Criminal trial 2025-25245676SM — Apr 7, 2026
- Emergency motion response monitoring

### 4.2 Filing Pipeline (Lanes F1-F10)

```python
# Check readiness across all filing lanes:
nexus_readiness()          # All lanes
nexus_readiness(lane="F")  # Appellate lane only

# Filing status for specific lane:
filing_status(lane="F9")   # COA Brief status

# Full pipeline view:
filing_pipeline()          # Every action with phase, readiness %, risk score, gaps
```

### 4.3 Separation Counter (NEVER HARDCODE)

```python
from datetime import date
separation_days = (date.today() - date(2025, 7, 29)).days
# Use separation_counter() tool for formatted output
```

**Rule 29 VIOLATION:** Embedding a static day count (e.g., "230 days") in any filing. ALWAYS compute at render time.

### 4.4 Service Protocol (Post-Barnes Withdrawal)

Barnes (P55406) WITHDREW March 2026. Emily is now UNREPRESENTED.

**Serve directly:**
- Emily A. Watson, 2160 Garland Dr, Norton Shores, MI 49441
- FOC: Pamela Rusco, 990 Terrace St, Muskegon, MI 49442 (custody/PT matters)
- MC 12 Certificate of Service with EVERY filing

### 4.5 Gap Analysis

```python
# Detect missing evidence, unfiled motions, weak authority chains:
lexos_gap_analysis()          # All lanes
lexos_gap_analysis(lane="A")  # Custody lane only

# Cross-lane intelligence connections:
lexos_cross_connect(topic="parental alienation")
```

---

## ANTI-PATTERNS (MANDATORY — 18 Rules)

| # | Anti-Pattern | Correct Practice |
|---|-------------|-----------------|
| 1 | Using `LIKE '%term%'` without trying FTS5 first | Always FTS5 → LIKE fallback chain |
| 2 | Hardcoding separation day count | `(today - date(2025,7,29)).days` always |
| 3 | Citing Barnes as current attorney | Barnes WITHDREW Mar 2026 — Emily unrepresented |
| 4 | Using "Emily A. Watson" as correct name | It IS correct — never "Tiffany", "Emily Ann", "Emily M." |
| 5 | Writing child's full name | L.D.W. only — MCR 8.119(H) |
| 6 | Citing MCL 722.27c | DOES NOT EXIST — correct is MCL 722.23(j) |
| 7 | Citing Brady v Maryland in family law | Criminal only — use Mathews v Eldridge for due process |
| 8 | Fabricating statistics ("91% alienation score") | Every number must trace to a specific SQL query |
| 9 | Hash-only deduplication | Content-based peek required (user mandate) |
| 10 | Searching one table when five are available | Use nexus_fuse for cross-table fusion |
| 11 | Ignoring CRIMINAL lane separation | 2025-25245676SM has ZERO connection to Lanes A-F |
| 12 | Rounding evidence counts | Exact COUNT(*) with traceable query |
| 13 | Using "Jane Berry" or "Patricia Berry" | HALLUCINATIONS — never existed. Delete on sight |
| 14 | Skipping FTS5 sanitization | `re.sub(r'[^\w\s*"]', ' ', query)` MANDATORY |
| 15 | Serving Barnes instead of Emily | Barnes withdrew — serve Emily directly |
| 16 | Using MCP tools when NEXUS available | NEXUS is 100× faster (warm daemon vs cold spawn) |
| 17 | Placing AI/DB references in filings | Rule 3 contamination sweep mandatory |
| 18 | Reporting results without dedup | Always DISTINCT/GROUP BY per Rule 21 |

---

## DECISION MATRICES

### When to Deploy Each Evidence Tool

```
User says "find evidence about X"
  → nexus_fuse(topic="X")  [5-source cross-table]

User says "build impeachment for person Y"
  → search_impeachment(target="Y", min_severity=7)
  → search_contradictions(entity="Y")
  → adversary_scan(target="Y")

User says "what authorities support claim Z"
  → nexus_argue(claim="Z")  [evidence + authorities + impeachment + strength score]

User says "check custody factors"
  → nexus_case_map(case_type="custody")  [all 12 MCL 722.23 factors]

User says "what's missing"
  → lexos_gap_analysis()  [missing evidence, unfiled motions, weak chains]

User says "timeline of event X"
  → timeline_search(query="X")  [chronological events]
  → lexos_narrative(query="X", lane="A")  [narrative builder]
```

### Adversary Engagement Escalation

```
Level 1: Profile           → lexos_adversary(person="X")
Level 2: Deep scan         → adversary_scan(target="X")
Level 3: Impeachment build → search_impeachment + search_contradictions
Level 4: Full dossier      → All of above + timeline_search + nexus_fuse
Level 5: War room          → Deploy adversary-war-room agent
```

---

## PERFORMANCE BUDGETS

| Operation | Target | Max Acceptable | Tool |
|-----------|--------|---------------|------|
| FTS5 evidence search | <5ms | 50ms | search_evidence |
| Cross-table fusion | <25ms | 200ms | nexus_fuse |
| Vector similarity | <10ms | 100ms | vector_search |
| Argument synthesis | <30ms | 300ms | nexus_argue |
| Deadline check | <5ms | 50ms | check_deadlines |
| Gap analysis | <50ms | 500ms | lexos_gap_analysis |
| Adversary deep scan | <100ms | 1s | adversary_scan |
| Filing readiness | <20ms | 200ms | nexus_readiness |

All budgets assume warm NEXUS daemon connection. Cold MCP spawn adds ~500ms per call.

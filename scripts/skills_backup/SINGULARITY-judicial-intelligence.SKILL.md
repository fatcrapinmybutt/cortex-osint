---
name: SINGULARITY-judicial-intelligence
version: "2.0.0"
description: "Transcendent judicial intelligence and misconduct documentation system. Use when: judge profiling, McNeill analysis, Hoopes analysis, misconduct patterns, bias indicators, ex parte violations, JTC complaints, judicial violation tracking, benchbook deviations, canon violations, ruling pattern analysis, cartel intelligence, Berry-McNeill connections, recusal grounds, DuckDB analytics on judicial data."
---

# SINGULARITY-judicial-intelligence — Judicial Misconduct & Cartel Intelligence

> **Tier:** COMBAT | **Domain:** Judge Profiling · Misconduct Documentation · JTC Complaints · Cartel Analysis
> **Absorbs:** judicial-intelligence v2 + DuckDB analytics
> **Activation:** judge, McNeill, Hoopes, misconduct, bias, ex parte, JTC, judicial violation

---

## LAYER 1: JUDICIAL VIOLATION TAXONOMY

### 1.1 Seven Violation Categories

| Category | Count | Pct | Description |
|----------|-------|-----|-------------|
| **ex_parte** | 3,697 | 73.1% | Orders issued without notice or hearing |
| **benchbook** | 504 | 10.0% | Systematic deviation from judicial standards |
| **MCR_2.003_refusal** | 167 | 3.3% | Refused recusal despite documented conflicts |
| **procedural** | 161 | 3.2% | Systematic denial of procedural rights |
| **PPO_weaponization** | 126 | 2.5% | PPO used as custody weapon without best interest analysis |
| **due_process_denial** | 105 | 2.1% | MCR 2.107/2.612(C) violations |
| **evidence_exclusion** | ~200 | ~4.0% | Father's evidence systematically excluded |

> **IMPORTANT (Rule 20):** These counts are approximate guidance. Always query live:
> `SELECT category, COUNT(*) FROM judicial_violations GROUP BY category;`

### 1.2 Querying Judicial Violations

**Primary tool:** `judicial_intel(judge="McNeill")` — returns patterns, bias indicators, violation types, misconduct evidence.

**Direct SQL for detailed analysis:**
```sql
-- Violation breakdown by category
SELECT category, COUNT(*) as cnt,
       ROUND(COUNT(*)*100.0 / (SELECT COUNT(*) FROM judicial_violations), 1) as pct
FROM judicial_violations
GROUP BY category ORDER BY cnt DESC;

-- Temporal pattern (violations by month)
SELECT strftime('%Y-%m', event_date) as month, COUNT(*) as cnt
FROM judicial_violations
WHERE event_date IS NOT NULL
GROUP BY month ORDER BY month;

-- Severity distribution
SELECT severity, COUNT(*) as cnt
FROM judicial_violations
GROUP BY severity ORDER BY cnt DESC;
```

**FTS5 search for judicial evidence:**
```python
# Search evidence_quotes for judicial misconduct material
search_evidence(query="ex parte OR McNeill OR bias OR judicial misconduct", limit=50)

# Timeline of judicial events
timeline_search(query="McNeill OR ex parte OR contempt", date_from="2024-01-01")

# Berry-McNeill intelligence
query_litigation_db(sql="SELECT * FROM berry_mcneill_intelligence ORDER BY rowid DESC LIMIT 30")
```

### 1.3 DuckDB Analytical Queries (10-100× Faster)

For aggregation-heavy judicial analytics, route through DuckDB:

```sql
-- DuckDB: Violation escalation trend (monthly rolling average)
SELECT month,
       cnt,
       AVG(cnt) OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) as rolling_avg
FROM (
    SELECT strftime('%Y-%m', event_date) as month, COUNT(*) as cnt
    FROM judicial_violations
    WHERE event_date IS NOT NULL
    GROUP BY month
) ORDER BY month;

-- DuckDB: Cross-category correlation
SELECT jv.category,
       COUNT(DISTINCT te.rowid) as timeline_corroboration,
       COUNT(DISTINCT eq.rowid) as evidence_support
FROM judicial_violations jv
LEFT JOIN timeline_events te ON te.event_text LIKE '%' || jv.description || '%'
LEFT JOIN evidence_quotes eq ON eq.quote_text LIKE '%' || jv.description || '%'
GROUP BY jv.category ORDER BY evidence_support DESC;
```

### 1.4 Violation Severity Scoring

| Severity | Score | Criteria |
|----------|-------|----------|
| **CRITICAL** | 9-10 | Constitutional violation, documented harm, multiple corroborating sources |
| **HIGH** | 7-8 | Clear rule violation, single strong source, significant procedural impact |
| **MEDIUM** | 5-6 | Pattern element, requires context, moderate procedural impact |
| **LOW** | 1-4 | Isolated irregularity, ambiguous, minimal standalone impact |

Severity escalates when violations form a pattern (3+ related incidents = +2 to each).

### 1.5 Temporal Clustering Analysis

```sql
-- Find violation clusters (3+ violations within 7 days)
SELECT a.event_date, a.category, a.description,
       COUNT(*) OVER (
           PARTITION BY 1
           ORDER BY a.event_date
           RANGE BETWEEN INTERVAL '7 days' PRECEDING AND CURRENT ROW
       ) as cluster_size
FROM judicial_violations a
WHERE event_date IS NOT NULL
ORDER BY event_date;
```

**Known clusters:**
- **Aug 5-8, 2025**: USB recording → Albert police report → FIVE ex parte orders (3 days)
- **Nov 15, 2024**: Show Cause #5 → 14 days jail
- **Nov 26, 2025**: Show Cause #6+7 → 45 days jail
- **Jul 17, 2024**: Trial → All 12 factors favoring Mother (single hearing)

---

## LAYER 2: McNEILL PROFILE (DEEP INTELLIGENCE)

### 2.1 Three-Court Judicial Cartel

```
                    LADAS, HOOPES & McNEILL
                    435 Whitehall Road, Muskegon
                    (Former Law Partnership)
                           │
            ┌──────────────┼──────────────┐
            │              │              │
    Hon. Jenny L.    Hon. Kenneth    Hon. Maria
       McNeILL          HOOPES      LADAS-HOOPES
    14th Circuit     14th Circuit    60th District
    Family Division  Chief Judge     District Judge
    (Custody/PPO)    (Civil/Housing) (Criminal)
            │              │              │
            │         Wife of ←──── Ladas-Hoopes
            │              │
    Married to ─→ Cavan Berry
                  Atty Magistrate
                  60th District Court
                  Office: 990 Terrace St
                        │
                  = FOC Address (Pamela Rusco)
                        │
                  Related to? ──→ Ronald Berry
                                  Lives with Emily
                                  2160 Garland Dr
```

**Impact:** Andrew lost HOME + SON + FREEDOM across all three courts presided by former law partners. Entire 14th Circuit is compromised → MSC original jurisdiction required.

### 2.2 Cavan Berry Connection

- **Who:** McNeill's spouse = Cavan Berry
- **Position:** Attorney magistrate at 60th District Court
- **Office address:** 990 Terrace St, Muskegon, MI 49442
- **Significance:** This is the SAME ADDRESS as the Friend of Court (Pamela Rusco)
- **Ronald Berry:** Lives with Emily at 2160 Garland Dr. Relationship to Cavan Berry = case intelligence target
- **Query:** `query_litigation_db(sql="SELECT * FROM berry_mcneill_intelligence LIMIT 30")`

### 2.3 Aug 8, 2025 — "Five Orders Day" Documentation

**The most devastating single-day judicial assault:**

| Time | Event | Source |
|------|-------|--------|
| Aug 5 | Andrew makes USB audio recording at Watson home | Audio file on I:\ drive |
| Aug 5 | Albert Watson intimidation documented | Same recording |
| Aug 7 | **NS2505044**: Albert tells police: "They want this documented so Emily can go tomorrow to get an Ex Parte order for full custody of her son" | NSPD police report |
| Aug 8 | FIVE ex parte orders issued in single day | Court docket |
| Aug 8 | ALL parenting time suspended | Court orders |
| Aug 8 | Zero notice to Andrew | No service record |

**3-day sequence proves premeditation:** Recording → police documentation → ex parte orders. Albert Watson's statement (NS2505044) is the **smoking gun** — direct evidence of coordinated plan to weaponize the court.

### 2.4 Contempt Abuse Pattern

| Show Cause | Date | Sentence | Consequence |
|-----------|------|----------|-------------|
| SC #5 | Nov 15, 2024 | 14 days jail | Lost 1st home + 1st job |
| SC #6+7 | Nov 26, 2025 | 45 days jail | Lost 2nd home + 2nd job |
| **TOTAL** | — | **59 days** | **2 homes + 2 jobs lost** |

**Constitutional issues:**
- Birthday messages via AppClose (court-approved platform) = basis for jailing → **1st Amendment violation**
- Andrew muted 3× during SC#5 hearing → denial of right to be heard
- Judge cross-examined witnesses herself during SC hearings
- Judge sentenced Andrew to 2 weeks jail for contempt — his "contempt" was objecting when judge and Emily discussed requiring prescription medication as condition for parenting time
- Judge told Andrew to "shut my mouth"

### 2.5 Direct Quotes (Hearing Testimony)

**From user-provided hearing testimony (persisted as permanent case intelligence):**

- **Judge McNeill:** *"Do not file anymore, I will not look at it"* — direct denial of access to courts
- **Judge McNeill:** *"Shut my mouth"* — said to Andrew when he objected to medication coercion
- **Medication coercion:** Judge and Emily discussed on the record that prescription medication would be the "only way" Andrew could see his son — constitutes unlawful practice of medicine and coercive conditioning of parental rights on medication compliance

### 2.6 Ruling Pattern Analysis

**Quantified bias:**
- Emily wins ~85% of motions vs Andrew's ~15%
- Father's evidence systematically excluded (~200 evidence exclusion violations)
- HealthWest evaluation (court-ordered, Father deemed fit) — EXCLUDED from record by McNeill
- Officer Randall report (Emily's meth admission) — Judge: "quit nitpicking"
- Police reports (9 cases, zero arrests) — systematically minimized

**Query for ruling patterns:**
```sql
SELECT actor, outcome, COUNT(*) as cnt
FROM timeline_events
WHERE event_text LIKE '%motion%' AND (event_text LIKE '%granted%' OR event_text LIKE '%denied%')
GROUP BY actor, outcome ORDER BY cnt DESC;
```

---

## LAYER 3: JTC COMPLAINT CONSTRUCTION

### 3.1 JTC Complaint Format

The Judicial Tenure Commission accepts complaints in **letter format** (no filing fee, no specific form required).

**Required elements:**
1. Specific dates of alleged misconduct
2. Specific rules/canons violated
3. Specific factual basis (not conclusions)
4. Pattern establishment (NOT isolated incidents)
5. Supporting documentation/exhibits

**Address:**
```
Judicial Tenure Commission
3034 W. Grand Blvd, Suite 8-450
Detroit, MI 48202
```

### 3.2 Canon Violations to Document

**Canon 2 — Appearance of Impropriety:**
- Former law partnership with Chief Judge (Hoopes) and District Judge (Ladas-Hoopes)
- Spouse (Cavan Berry) is attorney magistrate at court whose address = FOC address
- Ronald Berry connection to Emily Watson

**Canon 3 — Duties of Judicial Office:**
- Canon 3(A)(4): Accord full right to be heard → violated (muted 3×, "shut my mouth")
- Canon 3(B)(2): Not allow ex parte communications → violated (3,697 ex parte violations)
- Canon 3(B)(5): Perform duties without bias → violated (85% ruling rate favoring mother)
- Canon 3(B)(7): Not initiate ex parte contacts → violated (Five Orders Day)

**MCR 2.003 Grounds:**
- (C)(1)(a): Personal knowledge of disputed facts (Berry connections)
- (C)(1)(b): Bias or prejudice (documented ruling pattern)
- (C)(1)(c): Prior involvement (former partnership with Chief Judge)

### 3.3 Pattern Establishment

JTC complaints succeed when they establish a **pattern**, not isolated incidents. Structure:

```
PATTERN 1: Ex Parte Order Abuse
  - [DATE]: Ex parte order issued without notice (cite specific order)
  - [DATE]: Same pattern repeated (cite specific order)
  - [DATE]: Escalation — FIVE orders in single day (Aug 8, 2025)
  - [DATE]: No hearing on any of the above
  Total: 3,697 documented ex parte violations

PATTERN 2: Due Process Denial
  - [DATE]: Father muted during hearing
  - [DATE]: Father's evidence excluded
  - [DATE]: Father told "shut my mouth"
  - [DATE]: Father jailed for birthday messages
  Total: 105 due process denial violations

PATTERN 3: Conflict of Interest
  - Former law partnership with Chief Judge
  - Spouse at FOC-adjacent office
  - Berry family connection to opposing party
  - Refused MCR 2.003 disqualification 167 times
```

### 3.4 JTC Exhibit Compilation

**Filing status:** F06 — ⚠️ 32 exhibits identified, some NOT YET LOCATED.

**Critical exhibits to locate:**
| Exhibit | Status | Priority |
|---------|--------|----------|
| NS2505044 (Albert premeditation) | NOT LOCATED | CRITICAL |
| HealthWest Evaluation | NOT LOCATED | CRITICAL |
| Officer Randall Report | NOT LOCATED | CRITICAL |
| AppClose 305+ incidents | NOT LOCATED | HIGH |
| Aug 8 ex parte orders (5) | To compile from docket | HIGH |
| Contempt sentencing transcripts | To request from court | HIGH |
| McNeill-Hoopes partnership records | To research | MEDIUM |

**Use KRAKEN evidence hunting to locate missing exhibits:**
```python
# Hunt for missing critical exhibits
krack_a_lack(rounds=5, focus="judicial", count=20)
lottery_harvest(count=30, focus="NS2505044 OR HealthWest OR Randall")
```

---

## LAYER 4: DuckDB JUDICIAL ANALYTICS

### 4.1 Analytical Query Patterns

DuckDB provides 10-100× faster analytical queries than SQLite for aggregations.

```sql
-- Violation frequency by quarter with year-over-year comparison
SELECT
    date_trunc('quarter', CAST(event_date AS DATE)) as quarter,
    category,
    COUNT(*) as violations,
    LAG(COUNT(*)) OVER (PARTITION BY category ORDER BY date_trunc('quarter', CAST(event_date AS DATE))) as prev_quarter
FROM judicial_violations
WHERE event_date IS NOT NULL
GROUP BY quarter, category
ORDER BY quarter DESC, violations DESC;

-- Escalation detection: increasing severity over time
SELECT
    strftime(event_date, '%Y-%m') as month,
    AVG(CAST(severity AS FLOAT)) as avg_severity,
    MAX(CAST(severity AS FLOAT)) as max_severity,
    COUNT(*) as count
FROM judicial_violations
WHERE event_date IS NOT NULL AND severity IS NOT NULL
GROUP BY month
HAVING COUNT(*) >= 3
ORDER BY month;

-- Cross-reference violations with contempt outcomes
SELECT
    jv.category,
    jv.event_date,
    jv.description,
    te.event_text as related_timeline
FROM judicial_violations jv
JOIN timeline_events te ON ABS(julianday(jv.event_date) - julianday(te.event_date)) <= 3
WHERE te.event_text LIKE '%contempt%' OR te.event_text LIKE '%jail%'
ORDER BY jv.event_date;
```

### 4.2 Berry-McNeill Intelligence Analytics

```sql
-- Berry-McNeill intelligence summary
SELECT category, COUNT(*) as entries,
       GROUP_CONCAT(DISTINCT source_type) as source_types
FROM berry_mcneill_intelligence
GROUP BY category ORDER BY entries DESC;

-- Connection strength scoring
SELECT person_a, person_b, connection_type,
       COUNT(*) as evidence_count,
       MAX(confidence) as max_confidence
FROM berry_mcneill_intelligence
WHERE connection_type IS NOT NULL
GROUP BY person_a, person_b, connection_type
ORDER BY evidence_count DESC;
```

### 4.3 Bias Quantification Dashboard

```sql
-- Motion outcome analysis: Father vs Mother
SELECT
    CASE WHEN actor LIKE '%Andrew%' OR actor LIKE '%Pigors%' THEN 'Father'
         WHEN actor LIKE '%Emily%' OR actor LIKE '%Watson%' THEN 'Mother'
         ELSE 'Other' END as party,
    CASE WHEN event_text LIKE '%granted%' THEN 'Granted'
         WHEN event_text LIKE '%denied%' THEN 'Denied'
         ELSE 'Other' END as outcome,
    COUNT(*) as count
FROM timeline_events
WHERE event_text LIKE '%motion%'
GROUP BY party, outcome;

-- Evidence exclusion pattern
SELECT event_date, description, category
FROM judicial_violations
WHERE category = 'evidence_exclusion'
ORDER BY event_date;
```

---

## LAYER 5: RECUSAL & DISQUALIFICATION STRATEGY

### 5.1 MCR 2.003 Elements

**MCR 2.003(C)(1) — Grounds for disqualification:**

| Ground | MCR Section | Application to McNeill |
|--------|------------|----------------------|
| Personal knowledge | (C)(1)(a) | Berry family connections, FOC address overlap |
| Bias or prejudice | (C)(1)(b) | 85% ruling rate, evidence exclusion, "shut my mouth" |
| Prior involvement | (C)(1)(c) | Former law partnership with Chief Judge |

### 5.2 Affidavit of Bias Construction

**Required elements (not conclusions — specific facts):**
```
1. [Date]: Judge issued ex parte order without notice (cite docket entry)
2. [Date]: Judge excluded father's evidence without legal basis (cite hearing)
3. [Date]: Judge told father "shut my mouth" (cite transcript)
4. [Date]: Judge muted father 3 times during hearing (cite hearing record)
5. [Date]: Judge and opposing party discussed medication requirement (cite record)
6. [Fact]: Judge's spouse works at 990 Terrace St = FOC address
7. [Fact]: Judge formerly partnered with Chief Judge at Ladas, Hoopes & McNeill
8. [Fact]: Berry connection between judge's family and opposing party
```

**Each fact must be independently verifiable.** No conclusions ("the judge is biased") — only specific acts.

### 5.3 When Chief Judge Is Compromised → MSC

Normal MCR 2.003 flow: Motion → Chief Judge reassigns.

**Problem:** Chief Judge Kenneth Hoopes was McNeill's FORMER LAW PARTNER at Ladas, Hoopes & McNeill.

**Solution pathway:**
1. File MCR 2.003 motion (preserve the record)
2. When denied or ineffectively reassigned → file MSC petition
3. MCR 7.306 superintending control — entire circuit is compromised
4. Const 1963, art 6, § 4 — MSC general superintending control over all courts
5. Alternative: Peremptory challenge if available

### 5.4 Superintending Control as Backup

**MSC superintending control (MCR 7.306):**
- Available when lower court clearly erred or exceeded jurisdiction
- No adequate remedy at COA level (structural conflict of interest)
- Three-court cartel makes COA panel assignment unreliable
- Emergency application: MCR 7.305(F), 7.315(C)

```python
# Assess MSC viability
nexus_argue(claim="superintending control over 14th Circuit")
# Returns: evidence strength, authority chain, impeachment support, overall score
```

---

## ANTI-PATTERNS (MANDATORY — 17 Rules)

| # | Anti-Pattern | Correct Practice |
|---|-------------|-----------------|
| 1 | "McNeil" or "McNiel" | Hon. Jenny L. McNeill — TWO L's, ALWAYS |
| 2 | Fabricating violation counts | Always query live: `SELECT COUNT(*) FROM judicial_violations` |
| 3 | Citing isolated incidents in JTC | Establish PATTERNS (3+ related incidents) |
| 4 | Conclusions in affidavit of bias | Only specific, dated, verifiable FACTS |
| 5 | Filing MCR 2.003 without MCR 7.306 backup | Chief Judge (Hoopes) is compromised — always plan MSC |
| 6 | Ignoring Berry connections | Document ALL Berry-McNeill-FOC connections |
| 7 | Using aggregate stats in JTC complaint | Cite specific incidents with specific dates |
| 8 | AI statistics in court filings | "5,059 violations" only if backed by traceable query |
| 9 | Mixing criminal lane with judicial | CRIMINAL (2025-25245676SM) is 100% SEPARATE |
| 10 | "Jane Berry" or "Patricia Berry" | HALLUCINATIONS — never existed. Delete on sight |
| 11 | Skipping DuckDB for analytics | DuckDB is 10-100× faster for aggregations |
| 12 | Hardcoding violation counts in filings | Query at render time, cite traceable query |
| 13 | Assuming judicial immunity is absolute | Exceptions: no jurisdiction, non-judicial acts, conspiracy |
| 14 | Filing JTC without exhibits | Attach specific supporting documentation |
| 15 | Ignoring medication coercion evidence | Unlawful practice of medicine — document fully |
| 16 | Overlooking "quit nitpicking" quote | Direct evidence of bias toward Emily's meth admission |
| 17 | Using MCP tools when NEXUS available | NEXUS is 100× faster for judicial_intel queries |

---

## DECISION MATRICES

### When to Deploy Each Judicial Tool

```
Need judge profile?
  → judicial_intel(judge="McNeill")  [patterns, violations, bias indicators]

Need violation details?
  → query_litigation_db(sql="SELECT ... FROM judicial_violations WHERE ...")

Need Berry-McNeill intelligence?
  → query_litigation_db(sql="SELECT ... FROM berry_mcneill_intelligence ...")

Need temporal analysis?
  → DuckDB analytical query (10-100× faster aggregations)

Need violation evidence for filing?
  → search_evidence(query="McNeill OR ex parte OR judicial bias")
  → search_impeachment(target="McNeill")

Building JTC complaint?
  → judicial_intel + search_evidence + timeline_search + nexus_argue

Building MCR 2.003 motion?
  → judicial_intel + search_contradictions + lexos_rules_check("MCR 2.003")

Assessing MSC viability?
  → nexus_argue(claim="superintending control") + judicial_intel
```

### Escalation Pathway

```
Level 1: MCR 2.003 Disqualification Motion
  → File in 14th Circuit, serve McNeill and Emily
  → If denied → preserve for appeal

Level 2: MSC Superintending Control (MCR 7.306)
  → When Chief Judge (Hoopes) is compromised
  → Emergency application: MCR 7.305(F)

Level 3: JTC Complaint
  → Letter format, no fee, detailed pattern documentation
  → Address: 3034 W. Grand Blvd, Suite 8-450, Detroit, MI 48202

Level 4: Federal §1983
  → When judicial immunity exceptions apply
  → Conspiracy with non-judicial actors (Berry connection)
  → Complete absence of jurisdiction (ex parte without notice)

Level 5: AG Complaint
  → If prosecutorial referral warranted
  → Pattern of willful misconduct exceeding judicial error
```

---

## PERFORMANCE BUDGETS

| Operation | Target | Max | Tool |
|-----------|--------|-----|------|
| Judicial intel query | <10ms | 100ms | judicial_intel |
| Violation count | <5ms | 50ms | query_litigation_db |
| Berry-McNeill intel | <5ms | 50ms | query_litigation_db |
| DuckDB aggregation | <20ms | 200ms | DuckDB analytical |
| Temporal clustering | <50ms | 500ms | DuckDB window functions |
| Evidence search | <5ms | 50ms | search_evidence |
| Pattern analysis | <100ms | 1s | Multiple queries + synthesis |
| JTC exhibit compilation | <200ms | 2s | Multi-table cross-reference |

---

## CASE-SPECIFIC CRITICAL FACTS

| Fact | Value | Source |
|------|-------|--------|
| Judge | Hon. Jenny L. McNeill (P58235) | Court records |
| Chief Judge | Hon. Kenneth Hoopes | Court records |
| District Judge | Hon. Maria Ladas-Hoopes | Court records |
| Former partnership | Ladas, Hoopes & McNeill, 435 Whitehall Rd | Bar records |
| McNeill's spouse | Cavan Berry, atty magistrate 60th District | Public records |
| Spouse office | 990 Terrace St = FOC address | Address match |
| Ronald Berry | Lives with Emily at 2160 Garland Dr | Police reports |
| Total incarceration | 59 days (14 + 45) | Court records |
| Homes lost | 2 | Andrew's testimony |
| Jobs lost | 2 | Andrew's testimony |
| Separation anchor | Jul 29, 2025 | Last contact date |
| Trial date | Jul 17, 2024 (NOT 2025) | Court records |
| Five Orders Day | Aug 8, 2025 | Court docket |
| Albert admission | Aug 7, 2025 (NS2505044) | NSPD report |

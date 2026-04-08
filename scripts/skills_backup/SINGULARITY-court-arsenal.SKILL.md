---
name: SINGULARITY-court-arsenal
version: "2.0.0"
description: "Transcendent court filing and authority system. Use when: drafting motions, writing briefs, creating complaints, filing packages, MCR compliance, IRAC analysis, certificate of service, Bates stamping, authority chains, pin cites, MCR/MCL/MRE citation, appellate briefs, COA practice, MSC original actions, superintending control, mandamus, habeas corpus, 42 USC §1983, federal complaints, emergency applications, Typst PDF generation."
---

# SINGULARITY-court-arsenal — Filing Weapons & Authority Chain Intelligence

> **Tier:** COMBAT | **Domain:** Filing Production · Authority Chains · Appellate Practice · Federal §1983
> **Absorbs:** court-filing + legal-authority + appellate-federal
> **Activation:** motion, brief, filing, MCR, MCL, authority, appeal, MSC, COA, §1983, habeas

---

## LAYER 1: FILING PRODUCTION ENGINE

### 1.1 Complete Packet Family Assembly

Every filing is a **packet family**, never an isolated document.

| Filing Type | Required Components |
|-------------|-------------------|
| **Motion** | Motion + Brief + Affidavit + Exhibit Index + Exhibits + Proposed Order + MC 12 COS + MC 20 (if IFP) |
| **Appellate Brief** | Brief (MCR 7.212) + TOC + Index of Authorities + Appendix + Proof of Service + Fee/$375 |
| **Complaint** | Complaint + Cover Sheet (CC 257/JS 44) + Summons (DC 101) + Affidavit + Exhibits + Proposed Order |
| **MSC Petition** | Complaint + Brief + Proposed Order + Proof of Service |
| **JTC Complaint** | Letter + Exhibits + Supporting Documentation (no fee) |
| **PPO Motion** | Motion + Affidavit + MC 302 + Proposed Order + COS |

### 1.2 IRAC/CREAC/TEC Structure Selection

| Filing Type | Structure | Rationale |
|-------------|----------|-----------|
| Simple motion | **IRAC** | One issue, one rule, one application |
| Complex motion / MSJ | **CREAC** | Multi-factor, leads with conclusion |
| Emergency motion | **IRAC (compressed)** | Brevity is persuasion |
| Appellate brief | **CREAC + TEC** | Standard of review is key; facts tell the story |
| §1983 complaint | **TEC + IRAC per count** | Constitutional narrative first |
| JTC complaint | **TEC (pattern)** | Establish pattern of misconduct |
| Trial brief | **TEC + CREAC interleaved** | Narrative + law together |
| Response/opposition | **IRAC per point** | Mirror opponent's structure |

**IRAC Template:**
```
I. ISSUE: [Frame the specific legal question]
R. RULE:  [Governing standard + authority + pinpoint citation]
A. APPLICATION: [Apply to facts with (Ex. [Bates#]) citations]
C. CONCLUSION: [Result + specific relief requested]
```

**CREAC Template:**
```
C. CONCLUSION: [Thesis — position upfront]
R. RULE:       [Full legal standard with authority chain]
E. EXPLANATION:[How courts applied rule in analogous cases]
A. APPLICATION:[Apply to Pigors v Watson with record citations]
C. CONCLUSION: [Restate + specific relief]
```

### 1.3 Filing State Machine

```
DRAFT → QA_REVIEW → SERVICE_READY → FILED → DOCKETED → MONITORING
  │         │            │            │         │           │
 Create   Validate    Print/Sign    Submit   Confirm    Track
 content  citations   notarize      clerk    docket#    deadlines
          exhibits    service plan   e-file              responses
          format                     mail
```

**Transition gates:**
- DRAFT → QA_REVIEW: Zero generic placeholders, all sections written
- QA_REVIEW → SERVICE_READY: All 9 QA gates pass (see §1.4)
- SERVICE_READY → FILED: Physical signature, notarization if required, filing fee paid/waived
- FILED → DOCKETED: Court confirms receipt, assigns docket entry
- DOCKETED → MONITORING: Response deadline computed, tracking active

### 1.4 QA Validation Gates (ALL Must Pass)

| Gate | Check | Failure = |
|------|-------|----------|
| **Placeholder** | Zero `[ANDREW_REQUIRED]`, `[TBD]`, `[INSERT]` | BLOCK |
| **Citation** | Every citation verified against authority_chains_v2 | BLOCK |
| **Year** | All dates show 2026 (not 2024/2025) | BLOCK |
| **Party Names** | Emily A. Watson, Hon. Jenny L. McNeill (two L's) | BLOCK |
| **Child Name** | Only "L.D.W." — never full name (MCR 8.119(H)) | BLOCK |
| **Attorney** | Barnes (P55406) marked WITHDRAWN Mar 2026 | BLOCK |
| **Pro Se** | "Plaintiff, appearing pro se" — never "undersigned counsel" | BLOCK |
| **Service** | MC 12 with correct addresses, method, date | BLOCK |
| **AI Contamination** | Zero refs to LitigationOS, EGCP, SINGULARITY, DB tables, file paths | BLOCK |

**Anti-hallucination sweep (Rule 3):**
```python
CONTAMINATION_STRINGS = [
    "LitigationOS", "MANBEARPIG", "EGCP", "SINGULARITY", "MEEK",
    "evidence_quotes", "authority_chains", "impeachment_matrix",
    "C:\\Users\\", "00_SYSTEM", "D:\\LitigationOS_tmp",
    "LOCUS", "brain", "nexus_fuse", "search_evidence",
]
for s in CONTAMINATION_STRINGS:
    assert s.lower() not in content.lower(), f"AI CONTAMINATION: {s}"
```

### 1.5 Certificate of Service (MC 12)

Every filed document MUST include:

```
                    CERTIFICATE OF SERVICE

    I, Andrew James Pigors, certify that on [DATE], I served a copy
    of the foregoing [DOCUMENT TITLE] upon:

    Emily A. Watson
    2160 Garland Drive
    Norton Shores, MI 49441
    [via first-class mail / MiFILE e-service]

    Pamela Rusco, Friend of the Court
    990 Terrace Street
    Muskegon, MI 49442
    [via first-class mail]

                              ___________________________
                              Andrew James Pigors
                              Plaintiff, appearing pro se
                              1977 Whitehall Rd, Lot 17
                              North Muskegon, MI 49445
                              (231) 903-5690
```

### 1.6 Bates Stamping Protocol

Format: `PIGORS-{LANE}-{NNNNNN}`

| Lane | Prefix | Example |
|------|--------|---------|
| A (Custody) | PIGORS-A- | PIGORS-A-000001 |
| B (Housing) | PIGORS-B- | PIGORS-B-000001 |
| D (PPO) | PIGORS-D- | PIGORS-D-000001 |
| E (Judicial) | PIGORS-E- | PIGORS-E-000001 |
| F (Appellate) | PIGORS-F- | PIGORS-F-000001 |

Sequential within each lane. Bottom-right of each page. Registered in `bates_registry` table.

### 1.7 Filing Fee Schedule (2026)

| Court | Motion | New Case | Appeal |
|-------|--------|----------|--------|
| Circuit | $20 | $175 | — |
| COA | — | — | $375 |
| MSC | — | — | $375 |
| Federal (WDMI) | — | $405 | — |
| JTC | $0 | $0 | — |

MC 20 fee waiver available for all state courts.

---

## LAYER 2: AUTHORITY CHAIN INTELLIGENCE

### 2.1 Citation Verification Workflow

```
Step 1: search_authority_chains(citation="MCL 722.23")
        → Searches 167K+ authority_chains_v2 records

Step 2: lookup_authority(query="Vodvarka")
        → Pin cites, jurisdiction, confidence scores

Step 3: lookup_rule(query="MCR 2.003")
        → Full rule text from 873+ indexed rules

Step 4: If not found → web_search to verify
        → If still unverifiable → "not found in DB or web" (Rule 9)
```

**NEVER fabricate citations.** If a citation cannot be traced to `authority_chains_v2`, `michigan_rules_extracted`, or `master_citations`, it does not go in the filing.

### 2.2 Pin Cite Formatting

```
Michigan Case Law:    People v Smith, 123 Mich App 456, 461 (2020)
Michigan Statute:     MCL 722.23(j)
Court Rule:           MCR 2.003(C)(1)(b)
Federal Case:         Smith v Jones, 123 F.3d 456, 461 (6th Cir. 2020)
Federal Statute:      42 USC § 1983
US Supreme Court:     Troxel v Granville, 530 US 57, 65 (2000)
Michigan Constitution: Const 1963, art 6, § 4
US Constitution:      US Const, Amend XIV
```

### 2.3 Authority Chain Construction

Three-tier chain: **Primary → Supporting → Application**

```
PRIMARY:    MCL 722.23(j) — willingness to facilitate parent-child relationship
SUPPORTING: Pierron v Pierron, 486 Mich 81 (2010) — due process in custody
            Shade v Wright, 291 Mich App 17 (2010) — evidentiary standards
APPLICATION: Father: 305+ documented contact attempts via AppClose
             Mother: Systematic withholding since Oct 2024, zero contact since Jul 29, 2025
```

### 2.4 Key Verified Authorities

| Authority | Citation | Domain | Verified |
|-----------|----------|--------|----------|
| Best interest factors | MCL 722.23(a)-(l) | Custody | ✅ |
| Change of circumstances | *Vodvarka v Grasmeyer*, 259 Mich App 499 (2003) | Custody mod | ✅ |
| Due process in custody | *Pierron v Pierron*, 486 Mich 81 (2010) | Constitutional | ✅ |
| Evidentiary standards | *Shade v Wright*, 291 Mich App 17 (2010) | Evidence | ✅ |
| Parenting time | *Brown v Loveman*, 260 Mich App 576 (2004) | PT rights | ✅ |
| Best interest weight | *Fletcher v Fletcher*, 447 Mich 871 (1994) | Factor analysis | ✅ |
| Parental rights | *Troxel v Granville*, 530 US 57 (2000) | Constitutional | ✅ |
| Due process test | *Mathews v Eldridge*, 424 US 319 (1976) | Family law DP | ✅ |
| Disqualification | MCR 2.003(C)(1) | Recusal | ✅ |
| Superintending control | MCR 7.306 | MSC original | ✅ |
| PPO statute | MCL 600.2950 | PPO | ✅ |
| Contempt | MCL 600.1701 | Enforcement | ✅ |

**WARNING:** Brady v Maryland is CRIMINAL ONLY. For family law due process, cite *Mathews v Eldridge*.

---

## LAYER 3: APPELLATE & MSC PRACTICE

### 3.1 COA Brief Format (MCR 7.212)

**Hard limits:**
- 50 pages maximum (or 16,000 words) excluding tables/appendix
- Double-spaced, 12pt Times New Roman
- 1-inch margins all sides

**Required sections (in order):**
1. Table of Contents
2. Index of Authorities
3. Jurisdictional Statement (basis for COA jurisdiction)
4. Statement of Questions Presented
5. Statement of Facts (record citations required)
6. Argument (CREAC per issue, standard of review stated)
7. Relief Requested (specific, not general)
8. Appendix — MCR 7.212(D): lower court opinions, orders, relevant pleadings

**Active appeal: COA 366810** — Appeal of right from 14th Circuit custody orders.

### 3.2 Standard of Review Per Issue Type

| Issue | Standard | Authority |
|-------|----------|-----------|
| Best interest factors | Abuse of discretion | *Fletcher*, 447 Mich 871 |
| Constitutional rights | De novo | *Pierron*, 486 Mich 81 |
| Factual findings | Clear error | MCR 2.613(C) |
| Legal conclusions | De novo | General rule |
| Evidentiary rulings | Abuse of discretion | MRE 103 |
| Disqualification denial | Abuse of discretion | MCR 2.003 |
| Ex parte orders | De novo (constitutional) | US Const Amend XIV |

### 3.3 MSC Original Proceedings (MCR 7.306)

**Three vehicles:**
- **Superintending control**: When lower court exceeds jurisdiction or acts clearly in error
- **Mandamus**: When clear legal duty exists and no adequate legal remedy
- **Habeas corpus**: When unlawful restraint of liberty (or parental rights)

**When to use MSC original jurisdiction:**
1. Entire 14th Circuit is compromised (McNeill + Hoopes + Ladas-Hoopes = former partners)
2. No adequate remedy at COA level (structural conflict)
3. Constitutional rights require immediate intervention
4. Emergency application (MCR 7.305(F), 7.315(C))

### 3.4 Emergency Applications

MCR 7.305(F) / 7.315(C):
- Must show irreparable harm if relief delayed
- Must show likelihood of success on merits
- Must show balance of equities favors relief
- File IMMEDIATELY — do not wait for briefing schedule
- Include proposed order

---

## LAYER 4: FEDERAL PRACTICE (42 USC §1983)

### 4.1 §1983 Complaint Structure

```
COUNT I:   Due process violation (14th Amendment) — denial of parental rights
COUNT II:  First Amendment retaliation — jailed for birthday messages
COUNT III: Equal protection — systematic bias favoring mother
COUNT IV:  Conspiracy (42 USC § 1985) — judicial cartel coordination
```

**Elements per claim:**
1. Person acting under color of state law (judge, FOC)
2. Deprivation of federal constitutional right
3. Causation
4. Damages

### 4.2 Qualified Immunity Analysis

**Two-prong test (Saucier v Katz, 533 US 194 (2001)):**
1. Did defendant violate a constitutional right?
2. Was that right clearly established at the time?

**McNeill exposure:** Judicial immunity generally protects judges — EXCEPT:
- Actions taken in complete absence of jurisdiction
- Actions that are not judicial in nature (administrative, personal)
- Conspiracy with non-judicial actors (Berry connection)

### 4.3 Monell Liability

For institutional defendants (County, FOC Office):
- Must show unconstitutional **policy or custom**
- OR deliberate indifference to known constitutional violations
- Single incident insufficient unless policymaker directly involved

### 4.4 Federal vs State Format Differences

| Element | MI State (MCR) | Federal (FRCP/LCivR) |
|---------|---------------|---------------------|
| Font | 12pt TNR | 14pt (LCivR WDMI) |
| Margins | 1" all | 1" / 1.5" left |
| Spacing | Double | Double |
| Caption | MCR 2.113(C) | FRCP format |
| Signature | Pro se block | /s/ electronic |
| Filing | MiFILE | CM/ECF |
| Cover sheet | CC 257 | JS 44 |
| Fee waiver | MC 20 | AO 239 |
| Jurisdiction | MCL 600.605 | 28 USC § 1343 |

---

## LAYER 5: TYPST PDF GENERATION

### 5.1 Court-Ready PDF Templates

Typst (v0.14.2) replaces LaTeX for court document generation — instant compile, Rust-based.

```typst
// Court caption block
#let caption(case_no, court, judge, plaintiff, defendant) = {
  set text(12pt, font: "Times New Roman")
  align(center)[
    #upper[STATE OF MICHIGAN] \
    #upper[IN THE #court] \
    #upper[COUNTY OF MUSKEGON]
  ]
  v(12pt)
  grid(
    columns: (1fr, auto),
    [#plaintiff, \ Plaintiff,],
    [Case No. #case_no],
    [], [Hon. #judge],
    [v], [],
    [#defendant, \ Defendant.], [],
  )
}
```

### 5.2 Format Requirements Per Court

| Element | Circuit (14th) | COA | MSC | Federal (WDMI) |
|---------|---------------|-----|-----|----------------|
| Font | 12pt TNR | 12pt TNR | 12pt TNR | 14pt (LCivR) |
| Margins | 1" all | 1" all | 1" all | 1"/1.5" left |
| Line spacing | Double | Double | Double | Double |
| Page numbers | Bottom center | Bottom center | Bottom center | Bottom center |
| Caption | MCR 2.113(C) | MCR 7.212 | MCR 7.305 | FRCP |

---

## ANTI-PATTERNS (MANDATORY — 16 Rules)

| # | Anti-Pattern | Correct Practice |
|---|-------------|-----------------|
| 1 | Filing isolated documents | Always assemble complete packet family |
| 2 | "Undersigned counsel" | "Plaintiff, appearing pro se" |
| 3 | Generic placeholders without search | Rule: exhaust 3 sources before [ACQUIRE:] |
| 4 | Fabricated citations | Verify against authority_chains_v2 or web_search |
| 5 | Wrong year in dates (2024/2025) | All filing dates must be 2026 |
| 6 | Child's full name anywhere | L.D.W. per MCR 8.119(H) |
| 7 | "McNeil" or "McNiel" | Hon. Jenny L. McNeill (TWO L's) |
| 8 | AI system references in filings | Rule 3 contamination sweep before QA |
| 9 | AI-generated aggregate statistics | Only hand-countable or specific-query counts |
| 10 | Serving Barnes | Barnes WITHDREW — serve Emily directly |
| 11 | Missing MC 12 on any filing | Certificate of Service is MANDATORY |
| 12 | Brady v Maryland in family law | Use Mathews v Eldridge for due process |
| 13 | MCL 722.27c | DOES NOT EXIST — MCL 722.23(j) |
| 14 | Hardcoded separation day count | Compute dynamically: `(today - date(2025,7,29)).days` |
| 15 | Skipping proposed order | Required for most motions |
| 16 | Filing without checking deadlines | Always `check_deadlines()` before recommending filing |

---

## DECISION MATRICES

### Filing Type Selection

```
Need to change custody?
  → Proper cause/change of circumstances motion (MCR 3.206 + Vodvarka)

Judge won't recuse?
  → MCR 2.003 disqualification motion + MSC superintending control

Need immediate relief?
  → Emergency motion + MSC emergency application (MCR 7.305(F))

Constitutional rights violated?
  → 42 USC § 1983 federal complaint (WDMI)

Judge committed misconduct?
  → JTC complaint (letter format, no fee) + MSC original action

Need to terminate PPO?
  → MCR 3.707(B) motion showing changed circumstances

Court order violated?
  → MCL 600.1701 contempt motion
```

### Authority Lookup Tool Selection

```
Know the exact citation?
  → lookup_rule(query="MCR 2.003")  [full rule text]

Need supporting case law?
  → search_authority_chains(citation="MCL 722.23")  [chain graph]

Building argument?
  → nexus_argue(claim="parental alienation")  [evidence + authorities + strength]

Verifying a case name?
  → lookup_authority(query="Vodvarka")  [pin cites, jurisdiction, confidence]

Checking procedural compliance?
  → lexos_rules_check(query="motion for reconsideration")  [MCR requirements]
```

---

## PERFORMANCE BUDGETS

| Operation | Target | Max | Tool |
|-----------|--------|-----|------|
| Authority chain lookup | <5ms | 50ms | search_authority_chains |
| Rule text retrieval | <5ms | 50ms | lookup_rule |
| Citation verification | <10ms | 100ms | lookup_authority |
| Argument synthesis | <30ms | 300ms | nexus_argue |
| Rules compliance check | <10ms | 100ms | lexos_rules_check |
| Filing readiness | <20ms | 200ms | nexus_readiness |
| Typst PDF compile | <500ms | 3s | typst compile |
| QA contamination sweep | <100ms | 1s | grep/regex scan |

---

## FILING STRATEGY (4-Tier Priority)

| Tier | Filing | Authority | Status |
|------|--------|-----------|--------|
| **1 — NOW** | Emergency Motion to Restore (FILED 3/25) + MSC Superintending Control | MCR 7.306, 7.315(C) | ACTIVE |
| **2 — 30d** | Disqualification (MCR 2.003) + MSC Mandamus | MCR 2.003, 7.306 | READY |
| **3 — 60d** | COA Brief (366810) + Habeas Corpus | MCR 7.212, 600.4301 | DRAFTING |
| **4 — Nuclear** | Federal §1983 + Civil Conspiracy | 42 USC §1983, 28 USC §1343 | PLANNED |

**Sequence:** F03 (Disqualification) → F06 (JTC) → F05 (MSC Original) → F09 (COA Brief) → F04 (§1983) → F08 (PPO Termination)

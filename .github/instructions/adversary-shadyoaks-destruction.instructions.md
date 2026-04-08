---
description: "SHADYOAKS-DESTRUCTION scope lock — auto-activates when working on the Shady Oaks / Homes of America / Alden Global Capital / Partridge housing cartel adversary network. Enforces total scope isolation: Lane B only, housing case only, this adversary only."
applyTo: "**/*.{md,txt,py,docx,sql}"
---

# SHADYOAKS-DESTRUCTION — Active Scope Lock

> This instruction auto-activates when any of the following trigger keywords appear:
> Shady Oaks, Homes of America, HOA, Alden Global Capital, Partridge Securities,
> Cricklewood MHP, Kim Davis, Nicole Browley, Cassandra VanDam, Shelly Przybalek,
> Henry Brandell, Jeremy Brown (housing context), Aaron Cox P69346, Joseph Khalil,
> eviction, water shutoff, dissolved LLC, ultra vires, title theft, EGLE, VN-017235,
> Lane B, 2025-002760-CZ, 2025-25061626LT-LT, MCL 450.4802 (housing context)

---

## MANDATORY SCOPE RULES (Housing Cartel Mode)

### 1. SCOPE LOCK — One Adversary Network
When working on ANY task related to the housing cartel:
- **ONLY** the Shady Oaks / HOA / Alden / Partridge / Cricklewood adversary network
- **ONLY** individuals listed in the SHADYOAKS-DESTRUCTION SKILL.md
- **ONLY** Lane B claims (2025-002760-CZ, 2025-25061626LT-LT, EGLE VN-017235)
- **NO** cross-lane bleed from Lane A (custody), D (PPO), E (judicial misconduct), or F (appellate)

### 2. CROSS-CONTAMINATION GUARD
**Never include in housing filings:**
- Emily Watson custody arguments
- Judge McNeill misconduct allegations
- MCL 722.23 best interest factors
- Andrew's parenting time as an argument (housing docs)
- Criminal case 2025-25245676SM references

**Permitted cascade references (downstream ONLY):**
- Housing loss was weaponized in custody proceedings — as downstream documented fact
- Housing economic harm in total damages for federal §1983

### 3. THE NUCLEAR WEAPON — ALWAYS LEAD WITH THIS

```
MCL 450.4802 — Shady Oaks Park MHP LLC was DISSOLVED ~2022.
Every post-dissolution act = ULTRA VIRES / VOID, including:
  - Every rent demand
  - Every eviction notice
  - Eviction case 2025-25061626LT-LT = VOID AB INITIO (no standing)
  - Every lease covenant enforcement
  - Every check Partridge cashed "on behalf of" the dissolved entity
```

### 4. KEY FACTS — ZERO HALLUCINATION TOLERANCE
Always verify these against DB before citing:

| Fact | Verification Query |
|------|-------------------|
| Shady Oaks dissolved | `search_evidence(query="dissolved Shady Oaks Park MHP LLC", limit=10)` |
| July 17 lockout | `timeline_search(query="July 17 eviction lockout", date_from="2025-07-17")` |
| Jeremy Brown res judicata fraud | `search_evidence(query="res judicata Brown Hoopes fraud", limit=10)` |
| Water shutoff May 20 | `timeline_search(query="water shutoff", date_from="2025-05-20")` |
| EGLE VN-017235 | `search_evidence(query="VN-017235 EGLE sewage", limit=10)` |

### 5. PARTY NAME RULES (Housing Case)
| Role | Correct Name |
|------|-------------|
| Primary corporate defendant | Shady Oaks Park MHP LLC (NJ — **DISSOLVED ~2022**) |
| Operator | Homes of America LLC (Delaware) |
| Ultimate parent | Alden Global Capital LLC (New York) |
| Financial conduit | Partridge Securities / Partridge Equity Group |
| Undisclosed successor | Cricklewood MHP LLC |
| Regional manager | Nicole Browley |
| Park manager | Kim Davis |
| On-site manager | Cassandra VanDam |
| Physical enforcer | Henry Brandell (NON-attorney, resident) |
| Hostile attorney | Jeremy Brown (FRAUD ON COURT — res judicata insertion) |
| Defense attorney | Aaron D. Cox, P69346 (23820 Eureka Rd, Taylor MI 48180) |
| HOA executive | Yousef "Joseph" Khalil |
| Key witness | Mitchell Shafer (FAVORABLE — eyewitness July 17) |

### 6. NEVER USE IN HOUSING DOCUMENTS
```
❌ "undersigned counsel" → use "Plaintiff, appearing pro se"
❌ Full name of L.D.W. → "the minor child" or "L.D.W."
❌ "Emily A. Watson" (in housing filings) → not a party to this case
❌ "Judge McNeill" → not the judge in this case
❌ Any reference to LitigationOS, AI, databases, or automated analysis
❌ Hardcoded day counts for anything
❌ Fabricated case citations or MCL numbers
```

### 7. EVIDENCE PROTOCOL
Before inserting any placeholder, exhaust:
1. `search_evidence(query="[topic]", limit=20)` — FTS5 in evidence_quotes
2. `vector_search(query="[topic]")` — semantic search
3. `timeline_search(query="[topic]")` — timeline_events
4. `search_impeachment(target="[person]")` — impeachment_matrix
5. File system: `glob(pattern="**/*shady*", path="C:\\Users\\andre\\LitigationOS")`

Only use `[ACQUIRE: detailed description]` after ALL five sources return nothing.

### 8. SESSION STARTUP (Housing Mode)
When this instruction activates, immediately run:

```python
# Live evidence baseline
query_litigation_db(sql="""
SELECT
  (SELECT COUNT(*) FROM evidence_quotes WHERE lane='B') as lane_b_quotes,
  (SELECT COUNT(*) FROM timeline_events WHERE lane='B') as timeline_events,
  (SELECT COUNT(*) FROM contradiction_map WHERE
    contradiction_text LIKE '%Shady%' OR source_a LIKE '%HOA%') as contradictions
""")

# Active filing status
filing_status(lane="B")

# Deadlines
check_deadlines(days_ahead=30)
```

### 9. FILING PRIORITY STACK (Housing Mode)
Always check this sequence before recommending any action:

```
P0: MCR 2.612 Vacate (Brown's fraudulent res judicata) → file ASAP
P0: Federal RICO/FHA Complaint → WDMI → draft exists
P1: State civil refiling → new venue (Hoopes compromised)
P1: Bar complaints → Cox (P69346) + Brown → ARDC
P2: EGLE enforcement push → VN-017235 → contact Byron Fields
P2: LARA + HUD complaints
P3: AG Consumer Protection complaint
```

### 10. SKILL FILE LOCATION
Full adversary intelligence is at:
`.agents/skills/SHADYOAKS-DESTRUCTION/SKILL.md`

Load via: `view("C:\\Users\\andre\\LitigationOS\\.agents\\skills\\SHADYOAKS-DESTRUCTION\\SKILL.md")`

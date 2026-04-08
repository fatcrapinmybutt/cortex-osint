# SINGULARITY-KRAKEN — Multi-Tentacle Evidence Hunting System

> **Version:** 1.0.0 | **Tier:** COMBAT | **Domain:** Autonomous Evidence Discovery
> **Absorbs:** evidence-intelligence + lottery-harvest + dossier-expansion
> **Activation:** "kraken", "hunt evidence", "lottery harvest", "find evidence", "expand dossiers"

## IDENTITY

PROJECT KRAKEN is the autonomous evidence hunting and intelligence harvesting system for
LitigationOS. It discovers, extracts, analyzes, and persists evidence from 206K+ files
across 6 drives using a content-first "lottery" methodology — reading actual file content,
not filtering by filename.

## ARCHITECTURE

```
┌─────────────────────────────────────────────────────────┐
│                  PROJECT KRAKEN v1.0                     │
├─────────────────────────────────────────────────────────┤
│  FILE DISCOVERY                                          │
│  ├── fd (Rust) → fast drives (C:\, D:\)                 │
│  ├── file_inventory DB → slow drives (F:, G:, I:, J:)  │
│  └── 206,035 unique files, ~30s discovery               │
├─────────────────────────────────────────────────────────┤
│  CONTENT EXTRACTION                                      │
│  ├── pypdfium2 → PDF (30 page cap)                      │
│  ├── python-docx → DOCX paragraphs                      │
│  └── encoding cascade → TXT/CSV/HTML/JSON/MD            │
├─────────────────────────────────────────────────────────┤
│  ANALYSIS ENGINE                                         │
│  ├── 22 adversary compiled regex patterns                │
│  ├── 6 legal authority types (MCR/MCL/MRE/USC/FRCP/CL) │
│  ├── 8 evidence categories                               │
│  ├── Key quote extraction (sentence-level)               │
│  └── Focus-mode scoring boost                            │
├─────────────────────────────────────────────────────────┤
│  AUTO-PERSISTENCE                                        │
│  ├── HIGH → evidence_quotes DB + dossier files           │
│  ├── MEDIUM → dossier files only                         │
│  ├── Dedup → kraken_processed tracking table             │
│  └── Round tracking → kraken_rounds table                │
├─────────────────────────────────────────────────────────┤
│  OUTPUT                                                  │
│  ├── Scored results (HIGH/MEDIUM/LOW)                    │
│  ├── Expanded adversary dossiers (21 targets)            │
│  ├── JSON result logs per round                          │
│  └── Cumulative status report                            │
└─────────────────────────────────────────────────────────┘
```

## TOOLS & SCRIPTS

| Tool | Location | Purpose |
|------|----------|---------|
| **kraken.py** | `D:\LitigationOS_tmp\kraken.py` | Main orchestrator (572 lines) |
| **lottery_harvest** | Copilot extension tool | Quick lottery via extension |
| **dossier_status** | Copilot extension tool | Check all dossier files |
| **intel_dashboard** | Copilot extension tool | DB intelligence summary |
| **adversary_scan** | Copilot extension tool | Deep adversary profile |
| **file_universe** | Copilot extension tool | File counts by drive/extension |
| **separation_counter** | Copilot extension tool | Dynamic separation days |

## USAGE

### CLI (Full Power)
```bash
python -I D:\LitigationOS_tmp\kraken.py                     # 1 round, 10 files
python -I D:\LitigationOS_tmp\kraken.py --rounds 5          # 5 rounds
python -I D:\LitigationOS_tmp\kraken.py --count 20          # 20 files per round
python -I D:\LitigationOS_tmp\kraken.py --focus judicial    # judicial focus
python -I D:\LitigationOS_tmp\kraken.py --drives C,D        # specific drives
python -I D:\LitigationOS_tmp\kraken.py --status            # stats report
```

### In-Session (via Extension)
```
lottery_harvest --count 10 --focus custody
dossier_status
intel_dashboard
```

## FOCUS MODES (6)

| Mode | Boosted Targets | Use When |
|------|----------------|----------|
| **adversary** | Watson family, Berry connections | Building family conspiracy case |
| **judicial** | McNeill, Hoopes, Ladas-Hoopes, Berry, Rusco | JTC/MSC filings |
| **housing** | Shady Oaks, VanDam, Browley, Brandell, Brown, Cox, EGLE | Lane B evidence |
| **custody** | Emily Watson, FOC, Rusco, Albert Watson | Lane A filings |
| **ppo** | Emily Watson, McNeill, Ronald Berry | Lane D strategy |
| **legal** | All legal authority patterns boosted 2× | Authority chain building |

## ADVERSARY PATTERN LIBRARY (22 Compiled Regex)

Each adversary has a compiled regex pattern for fast full-content scanning:
- Watson family: Emily, Albert, Lori (3 patterns)
- Berry family: Ronald, Cavan (2 patterns)
- Judicial: McNeill, Hoopes, Ladas-Hoopes (3 patterns)
- FOC: Rusco, Martini, FOC institution (3 patterns)
- Attorneys: Barnes, Brown, Cox, Brandell (4 patterns)
- Housing: Shady Oaks, VanDam, Browley, Hilson, Duguid (5 patterns)
- Environmental: EGLE, Kim Davis (2 patterns)

## EVIDENCE CATEGORIES (8)

custody, PPO, judicial, housing, criminal, financial, police, medical

## LEGAL AUTHORITY PATTERNS (6)

MCR (Michigan Court Rules), MCL (Michigan Compiled Laws), MRE (Michigan Rules of Evidence),
USC (United States Code), FRCP (Federal Rules of Civil Procedure), Case Law (Mich App, F.2d, S.Ct.)

## SCORING ALGORITHM

```
value_score = (adversaries × 3) + (legal_authorities × 2) + categories + key_quotes
+ focus_boost (if matching focus mode targets)

HIGH  = score ≥ 10  → Auto-persist to DB + expand dossiers
MEDIUM = score 4-9  → Expand dossiers only
LOW   = score < 4   → Track only (no persistence)
```

## DATABASE TABLES

### kraken_processed (dedup tracking)
- file_hash, file_path, file_size, processed_at, round_id
- value_score, value_label, adversaries_found, legal_found, categories
- persisted_to_db, focus_mode

### kraken_rounds (round metadata)
- round_id, started_at, completed_at, files_scanned
- high_count, medium_count, low_count
- focus_mode, drives, new_evidence_rows

## DOSSIER AUTO-EXPANSION

21 adversary → dossier file mappings. When KRAKEN finds a HIGH or MEDIUM file
mentioning a tracked adversary, it automatically appends a formatted section to
the corresponding dossier file in `04_ANALYSIS/ADVERSARY_TRACKS/`:

```markdown
### KRAKEN Hunt (KRK-20260405-143022-R3) — 2026-04-05
**Source:** `evidence_file.pdf` (HIGH)
**Mentions:** 7 references
**Legal refs:** MCR: 3, MCL: 2
- "Key quote extracted from the document..."
```

## QUALITY GUARANTEES

1. **Content-first**: NEVER filter by filename — always READ file content
2. **Dedup**: Every file hashed and tracked — zero repeat processing
3. **Verified persistence**: SELECT after INSERT to confirm writes
4. **Focus boosting**: Targeted modes amplify scoring for relevant patterns
5. **Resilient extraction**: Multi-encoding fallback (utf-8 → latin-1 → cp1252)
6. **PDF safety**: 30-page cap prevents OOM on massive documents
7. **Score traceability**: Every score maps to specific regex matches

## MULTI-ROUND STRATEGY

For comprehensive evidence saturation:
1. **Round 1-3**: `--focus all` — cast wide net
2. **Round 4-5**: `--focus judicial` — deepen judicial misconduct
3. **Round 6-7**: `--focus housing` — strengthen Shady Oaks case
4. **Round 8-10**: `--focus custody` — custody/alienation evidence
5. **Review**: `--status` — assess coverage, identify gaps
6. **Repeat**: Continue until diminishing returns

## RELATIONSHIP TO OTHER SYSTEMS

| System | KRAKEN's Role |
|--------|--------------|
| **THEMANBEARPIG** | KRAKEN feeds new nodes/links for graph visualization |
| **Filing Engine** | KRAKEN-discovered evidence feeds filing packages |
| **Nexus Engine** | KRAKEN quotes power nexus_fuse cross-table search |
| **Dossier System** | KRAKEN auto-expands 21 adversary dossier files |
| **Authority Chains** | KRAKEN-found legal citations feed authority_chains_v2 |
| **Impeachment Matrix** | KRAKEN quotes with contradictions feed impeachment |

## VERSION HISTORY

- **v1.0.0** (2026-04-05): Initial release. fd + DB discovery, 22 adversary patterns,
  6 legal authority types, 8 evidence categories, auto-persist, dossier expansion,
  focus modes, multi-round execution, dedup tracking, status reporting.

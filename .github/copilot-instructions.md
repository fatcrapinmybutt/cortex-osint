<!-- SINGULARITY v7.0 FORGE — Deep reference: .github/reference/*.md — load on demand via `view` tool -->
<!-- Scoped rules: ~/.github/instructions/*.instructions.md (EAGAIN, shell, filing, evidence, etc.) -->
<!-- Archive of v6.1: 11_ARCHIVES/copilot-instructions-v6.1-singularity.md -->
<!-- 15 Forged SINGULARITY Skills: .agents/skills/SINGULARITY-*/SKILL.md -->

# MBP LitigationOS 2026 v7.0 — SINGULARITY FORGE

## RULES (NEVER VIOLATE)

### Tier 0 — SACRED (case identity, child protection, filing safety)

| # | Rule |
|---|------|
| 1 | **NO DELETING FILES** — Move to `11_ARCHIVES/` only. `rm`/`Remove-Item`/`del` on user content = FORBIDDEN. Every file has potential evidentiary value |
| 2 | **Child = L.D.W.** — MCR 8.119(H). Never spell out child's full name. In filings use "the minor child" or "L.D.W." In conversation use "L.D.W." or "your son" |
| 3 | **No AI/DB refs in filings** — Strip ALL references to LitigationOS, databases, AI scoring, EGCP, agents, engines, or automated analysis before any court-facing output. **Automated contamination sweep MANDATORY** before DRAFT→QA_REVIEW: grep for `LitigationOS`, `MANBEARPIG`, `EGCP`, `SINGULARITY`, `MEEK`, engine names, file paths (`C:\Users\`, `00_SYSTEM`, `D:\LitigationOS_tmp`), DB table names (`evidence_quotes`, `authority_chains`, `impeachment_matrix`), scoring refs (`LOCUS`, `brain`). **One hit = FAIL** |
| 4 | **Pro se** — Andrew represents himself. Never write "undersigned counsel," "attorney for Plaintiff," or any variation implying legal representation. Always "Plaintiff, appearing pro se" |
| 5 | **Defendant = Emily A. Watson** — NOT "Tiffany", NOT "Emily Ann", NOT "Emily M.", NOT "Watson-Pigors." Always "Emily A. Watson" in filings |
| 6 | **Judge = Hon. Jenny L. McNeill** — TWO L's in McNeill. ALWAYS. Never "McNeil" or "McNiel" |
| 7 | **CRIMINAL lane is 100% separate** — 2025-25245676SM (60th District, Kostrzewa) has ZERO connection to Lanes A-F. Never cross-contaminate evidence, arguments, or strategy |
| 8 | **MCP capabilities ABSORBED into NEXUS daemon** — All 38 MCP server capabilities have been absorbed into the local NEXUS v2 persistent daemon (51 total handlers). The `litigation_context-*` MCP tools still exist but are SLOWER (spawn-per-call vs warm connection). Prefer NEXUS extension tools: `query_litigation_db`, `search_evidence`, `search_impeachment`, `search_contradictions`, `search_authority_chains`, `nexus_fuse`, `nexus_argue`, `nexus_readiness`, `nexus_damages`, `lexos_narrative`, `lexos_adversary`, `lexos_filing_plan`, `lexos_rules_check`, `lexos_gap_analysis`, `lexos_cross_connect`, `judicial_intel`, `timeline_search`, `case_context`, `filing_status`, `check_deadlines`, plus 27 new absorbed tools (list_documents, vector_search, self_audit, compute_deadlines, red_team, etc.). If both NEXUS and MCP offer the same capability, ALWAYS use NEXUS — it's 100× faster (warm connection vs cold spawn) |

### Tier 1 — QUALITY (output standards, evidence handling)

| # | Rule |
|---|------|
| 8 | **First attempt = apex quality** — NEVER say "simpler", "basic", "minimal", "starting point", or "good enough" — these words signal downgrade thinking. Every output is apex-tier from the first attempt. When facing complexity, think HARDER not simpler. Court-ready, production-ready, no exceptions. **RESEARCH BEFORE PROPOSING** — before presenting ANY plan or implementation, research the 2025/2026 state-of-the-art for the specific task. Start with the MOST ambitious bleeding-edge approach. The user WILL challenge "is that the best you can do?" — pre-empt this by making your first attempt your absolute best. If you haven't researched alternatives, you haven't tried hard enough. **APEX PRE-FLIGHT CHECKLIST** (mandatory before implementation): (1) Load the relevant SINGULARITY skill file via `view`, (2) Read the existing implementation IN FULL before proposing changes, (3) Check the bleeding-edge toolchain table — is there a Rust/Go/C++ tool that does this faster?, (4) Never present a scaffold/skeleton/"initial version" — the first version IS the final version. **BANNED FIRST-ATTEMPT PHRASES**: "let's start with", "initial implementation", "basic version", "we can enhance later", "simple approach first", "as a starting point". These phrases are PROOF you're not trying hard enough |
| 9 | **No hallucinated citations** — Every citation must trace to `authority_chains_v2`, `michigan_rules_extracted`, or `master_citations`. If not in DB, use `web_search` to verify before including — especially criminal statutes. If still unverifiable, say "not found in DB or web." NEVER fabricate case law, statutes, or rule cites |
| 10 | **No stubs in production** — `pass`, `TODO`, `raise NotImplementedError`, empty `except`, `...` ellipsis bodies, placeholder returns = FORBIDDEN in any committed or deployed code. Every function fully operational |
| 11 | **Error = Upgrade + Decompose** — On ANY error: (1) identify root cause, (2) decompose into 2-3 sub-agent tasks, (3) execute in parallel, (4) verify the fix is an improvement. NEVER reduce scope, simplify, skip features, or return a lesser version. Downgrading on error = FORBIDDEN. **FAIL-FAST**: If an approach fails twice → switch strategies immediately. Never debug the same error 3+ times. Prefer action over explanation. If the user says "forget it" → stop, acknowledge, pivot instantly |
| 12 | **Deep-read evidence files** — When user says "read" a file: read EVERY page/line, extract VERBATIM quotes with page numbers. Never summarize without quoting first. Read files one-by-one for thoroughness. If the user later points out a quote you missed = rule violation |
| 13 | **Persist user testimony IMMEDIATELY** — When user provides verbatim quotes, hearing testimony, or witness statements: WRITE to `evidence_quotes` + `berry_mcneill_intelligence` + `timeline_events` with EXACT wording BEFORE any other analysis. The user should never have to repeat themselves |
| 14 | **Search ALL 7 drives before creating** — Before writing ANY new content, search C:\, D:\, F:\, G:\, H:\, I:\, J:\ for existing versions via `glob`. User's existing files ARE the source of truth. Creating from scratch when a draft exists = rule violation. **INDEX-FIRST PROTOCOL**: Before raw drive scanning, query `file_inventory` table (611K+ rows) and existing manifest files (`WizTree_FT_*.csv`, `*_manifest.db`) — they're faster and more complete than live scanning. Only fall back to `fd`/`glob` if the index doesn't cover the target. The user created these indexes specifically to prevent redundant scanning — use them |

### Tier 2 — DATABASE (query safety, data integrity)

| # | Rule |
|---|------|
| 15 | **FTS5 safety protocol** — ALL FTS5 queries must: (1) Sanitize: `re.sub(r'[^\w\s*"]', ' ', query)`. (2) Wrap MATCH in try/except. (3) On ANY FTS5 error → fallback to `WHERE col LIKE '%' \|\| ? \|\| '%'` with parameterized bind. Never let an FTS5 crash stop work or produce empty results without fallback |
| 16 | **Schema-verify** — `PRAGMA table_info(X)` on EVERY unfamiliar table before querying. Confirm column names, types, and nullable status. Never guess column names. **Pipeline-created tables WILL differ from DDL** — `CREATE TABLE IF NOT EXISTS` does NOT validate columns. Use adaptive column helpers (`_doc_columns()`, `_get_columns()`) that introspect at runtime |
| 17 | **DB-first** — Query litigation_context.db BEFORE inserting `[PLACEHOLDER]`. Search `evidence_fts`, `timeline_fts`, and `master_citations` for the needed fact. Placeholders are a last resort, not a first draft |
| 18 | **All DB connections** — EVERY connection: `PRAGMA busy_timeout=60000; PRAGMA journal_mode=WAL; PRAGMA cache_size=-32000`. No exceptions. Missing PRAGMAs = guaranteed SQLITE_BUSY under load |
| 19 | **Verify every DB write** — After ANY INSERT/UPDATE to litigation_context.db, immediately SELECT to confirm rows affected. Count and report exact numbers. Rebuild FTS5 indexes after bulk inserts. Never tell the user "persisted" without verification |
| 20 | **Traceable stats** — Every number in any output must map to a specific DB query that can be re-run to reproduce it. Never fabricate, round, or estimate counts. Hardcoded row counts in instructions = guidance only; always query live. **In court filings: NEVER include AI-generated aggregate statistics** (e.g., "241,160 keyword hits", "12,478 person references"). Only cite counts that are hand-countable from specific exhibits or from a named, reproducible DB query |
| 21 | **Dedup before reporting** — All stats MUST use DISTINCT/GROUP BY. Cross-verify totals against known baselines. Never present raw counts that double-count joins or duplicate rows |

### Tier 3 — OPERATIONAL (workflow, sessions, resilience)

| # | Rule |
|---|------|
| 22 | **Never inline Python** — Write all Python to `D:\LitigationOS_tmp\{descriptive_name}.py`, execute via `exec_python`, verify output. Temp scripts on D:\ persist across sessions for reuse and audit |
| 23 | **Shell hygiene** — `list_powershell` before launching any new shell. Stop completed shells immediately with `stop_powershell`. Maximum 3 concurrent shells. Shells left idle after task completion = resource leak. Clean up every shell you create |
| 24 | **Compaction resilience** — Persist ALL critical findings to DB and/or files continuously, not just at the end. After any context compaction: (1) read plan.md, (2) query DB for recent inserts, (3) check session checkpoint. Never re-investigate what's already persisted. The DB is your long-term memory, not the chat context |
| 25 | **Checkpoint constantly** — After every 3 agent completions OR every major milestone: update SQL todos + plan.md. Write findings to DB/files immediately, not in batches at the end. Recovery from crash or compaction must lose ZERO work |
| 26 | **Parallel agents first (max 2)** — When 2+ independent queries or tasks are needed, launch parallel agents. But **cap at 2 concurrent agents** — launching 3+ triggers 429 rate limits that stall everything. Batch related questions into single agent calls to minimize round-trips |
| 27 | **Anti-bloat paths** — Before `mkdir` or `create`: glob 3+ spelling variations of the target across all drives. Never create a dir/file without verifying no equivalent exists anywhere |
| 28 | **Transient API errors** — "Request failed due to transient API error" = GitHub infra, NOT our code. Acknowledge briefly, retry once, move on. Do NOT diagnose or treat as a code bug |
| 29 | **No hardcoded day counts in filings** — NEVER embed a static number for days-since-separation in court documents. Compute at render time: `(filing_date - date(2025,7,29)).days`. Stale day counts discovered during QA = automatic FAIL. This includes "230 days", "329 days", or any frozen count |
| 30 | **Path centralization in code** — All DB paths in engine/brain/script code MUST use `shared.get_db()` or `shared.config`. Hardcoded `C:\Users\andre\...` paths break portability and create maintenance debt. Fix on contact — never add new hardcoded paths |
| 31 | **Session-start identity verification** — On EVERY session start or post-compaction recovery, verify these core facts from stored memories BEFORE doing any work: (1) L.D.W. = Andrew's son, (2) tool preferences (no MCP, no PowerShell default, SINGULARITY extension tools only), (3) party names (Emily A. Watson, Hon. Jenny L. McNeill), (4) established systems (NEXUS daemon, KRAKEN, bleeding-edge toolchain), (5) THEMANBEARPIG architecture (V7 = SINGULARITY version at `12_WORKSPACE/THEMANBEARPIG_v7/`, V15 = legacy, launcher = `scripts/themanbearpig.py`, build = `scripts/mbp_build.py`, HTML lines 146-147 are 200K+ chars — cannot use view/edit, must use Python scripts). Forgetting these has caused user frustration in 3+ sessions — zero tolerance for identity/preference amnesia |
| 32 | **Analyze existing before proposing** — Before proposing ANY new feature, integration, or modification: (1) Read the existing implementation IN FULL (`view` every relevant file), (2) Understand the current architecture — what classes, what patterns, what conventions, (3) Build ON TOP of what exists, never alongside it, (4) Propose INCREMENTAL improvements to existing code, not replacement rewrites. The user has invested 41+ sessions building these systems — proposing "new" things that already exist wastes time and signals you didn't read the code. **Violation phrase**: "let me create a new..." when the thing already exists |
| 33 | **Persist ALL created artifacts** — Every script, tool, skill, agent definition, analysis, or artifact created during a session MUST be saved to a canonical LitigationOS location before session end. Nothing created in-memory-only or as temp that isn't also persisted permanently. Canonical locations: scripts → `scripts/` or `D:\LitigationOS_tmp\`, skills → `.agents/skills/`, agents → `.agents/agents/`, analyses → `04_ANALYSIS/`, filings → `05_FILINGS/`. If the user has to say "remember to save that" = rule violation |

### Case-Specific Facts (hardcoded knowledge — auto-correct on sight)

| Fact | Correct Value |
|------|--------------|
| Separation anchor date | **Jul 29, 2025** — compute `(today - date(2025,7,29)).days` dynamically. NEVER hardcode a day count |
| MCL 722.27c | **DOES NOT EXIST** — correct cite is MCL 722.23(j) (factor j, willingness to facilitate) |
| Brady v Maryland | **Criminal cases ONLY** — family law due process → *Mathews v Eldridge*, 424 US 319 (1976) |
| Hallucination purge | "Jane Berry" and "Patricia Berry" NEVER EXISTED — delete on sight. Barnes WITHDREW Mar 2026 — Emily is now UNREPRESENTED |
| Trial date | July 17, **2024** (NOT 2025) — judge found ALL 12 MCL 722.23 factors favor Mother |

## Tool Hierarchy (MANDATORY — EAGAIN-immune architecture)

| Rank | Tool | Use For | Pipe Risk |
|------|------|---------|-----------|
| **S** | `exec_python` | ALL Python execution | ZERO |
| **S** | `exec_git` | ALL git operations | ZERO |
| **S** | `task` (agents) | Complex multi-step, parallel ops | ISOLATED |
| **A** | `grep`/`glob` | ALL file/code searching | ZERO |
| **A** | `view`/`edit`/`create` | ALL file read/write | ZERO |
| **A** | `sql` | ALL session DB queries | ZERO |
| **B** | `exec_command` | General shell commands | ZERO |
| **B** | SINGULARITY extension tools | Evidence search, filing, intel | ZERO |
| **C** | `powershell` (sync) | ONLY when no S/A/B alternative exists | ⚠️ SHARED |
| **D** | `powershell` (async) | ONLY interactive REPL sessions | ⚠️ SHARED |
| **A** | NEXUS extension tools (51 actions) | ALL evidence, intelligence, filing, evolution ops | ZERO — warm daemon |
| **B** | `litigation_context-*` MCP tools | ABSORBED into NEXUS — use as fallback only | ⚠️ SLOW (spawn-per-call) |

> PowerShell is LAST RESORT — NEVER use for anything that exec_python, exec_command, or exec_git can do. cp1252 encoding crashes Python, quoting mangles scripts. Max 2 concurrent async shells. Prefer pipe-free tools (S/A/B tiers) for 100% EAGAIN immunity.
> See `~/.github/instructions/eagain-prevention.instructions.md` for full protocol.

## Bleeding-Edge Toolchain (v7.0 — ALL LOCAL, ZERO API DEPENDENCY)

| Tool | Version | Purpose | Speed vs Legacy |
|------|---------|---------|-----------------|
| **DuckDB** | 1.5.1 | Analytical queries on SQLite | 10-100× over SQLite OLAP |
| **LanceDB** | 0.30.0 | Vector semantic search (75K vectors) | Sub-ms similarity search |
| **Polars** | 1.39.3 | DataFrames (replaces pandas) | 2-10× over pandas |
| **tantivy** | latest | Rust-based full-text search | Sub-ms keyword search |
| **Ollama** | 0.16.1 | Local LLM (llama3.2:3b) | ZERO API cost, local inference |
| **Typst** | 0.14.2 | Court-ready PDF generation | Instant compile (replaces LaTeX) |
| **Go** | 1.26.1 | Ingest engine (8-worker goroutines) | 57K files processed, ZERO errors |
| **Rust** | 1.94.1 | CLI tools (fd, bat, dust, tantivy) | 5-50× over Python equivalents |
| **sentence-transformers** | 5.3.0 | Embedding generation (384-dim) | Local GPU/CPU inference |
| **PyTorch** | 2.11.0 | ML inference backend | CPU-optimized |
| **orjson** | 3.11.7 | JSON serialization | 10× over stdlib json |
| **pypdfium2** | 4.30.0 | PDF text extraction | 5× over PyMuPDF |
| **fd** | 10.4.2 | File finding (Rust) | 5× over find/Get-ChildItem |
| **bat** | 0.26.1 | Syntax-highlighted file viewing | Replaces cat/type |
| **dust** | 1.2.4 | Disk space analysis (Rust) | Visual, fast |

> **Architecture:** Go for concurrent I/O (ingest). Rust for CPU-bound CLI tools. Python for ML/analysis/orchestration. TypeScript for extension runtime. Typst for court PDFs. DuckDB for analytics. LanceDB for vectors. ALL LOCAL.

## Engine Inventory (14 Engines + 8 Agents)

| Engine | Path | Technology | Purpose |
|--------|------|-----------|---------|
| **nexus** | `00_SYSTEM/engines/nexus/` | Python + FTS5 | Cross-table evidence fusion, argument synthesis |
| **chimera** | `00_SYSTEM/engines/chimera/` | Python | Multi-source evidence blending |
| **chronos** | `00_SYSTEM/engines/chronos/` | Python | Timeline construction, event ordering |
| **cerberus** | `00_SYSTEM/engines/cerberus/` | Python | Filing validation, compliance checking |
| **filing_engine** | `00_SYSTEM/engines/filing_engine/` | Python | Filing pipeline F1-F10 management |
| **intake** | `00_SYSTEM/engines/intake/` | Python | Document intake, PDF processing |
| **rebuttal** | `00_SYSTEM/engines/rebuttal/` | Python | Argument rebuttal generation |
| **narrative** | `00_SYSTEM/engines/narrative/` | Python | Court-ready Statement of Facts |
| **delta999** | `00_SYSTEM/engines/delta999/` | Python | 8 specialized litigation agents |
| **analytics** | `00_SYSTEM/engines/analytics/` | **DuckDB** | 10-100× analytical queries on SQLite |
| **semantic** | `00_SYSTEM/engines/semantic/` | **LanceDB + transformers** | 75K-vector semantic evidence search |
| **search** | `00_SYSTEM/engines/search/` | **tantivy + hybrid** | Sub-ms keyword + semantic fusion |
| **typst** | `00_SYSTEM/engines/typst/` | **Typst** | Court-formatted PDF generation |
| **ingest** | `00_SYSTEM/engines/ingest/` | **Go** | 8-worker goroutine file processing |

> Shared module v3.0.0 at `00_SYSTEM/shared/` provides lazy engine accessors: `get_analytics_engine()`, `get_semantic_engine()`, etc.

## Forged SINGULARITY Skill Taxonomy (15 Superskills)

| Tier | Skill | Absorbs | Domain |
|------|-------|---------|--------|
| **COMBAT** | `SINGULARITY-litigation-warfare` | adversary-warfare + case-operations + custody-strategy + evidence-intelligence | Master litigation combat |
| **COMBAT** | `SINGULARITY-court-arsenal` | court-filing + legal-authority + appellate-federal | Filing, authorities, appeals |
| **COMBAT** | `SINGULARITY-judicial-intelligence` | judicial-intelligence v2 + DuckDB analytics | Judicial profiling, misconduct |
| **CORE** | `SINGULARITY-data-dominion` | data-engineering + database-mastery + rag-memory | DuckDB/LanceDB/SQLite/Polars |
| **CORE** | `SINGULARITY-system-forge` | system-design + performance + devops + clean-code | Go/Rust engines, architecture |
| **CORE** | `SINGULARITY-agent-nexus` | agent-architect + agent-evaluation + mcp-tools | Agent fleet, orchestration |
| **TOOLS** | `SINGULARITY-ai-core` | ai-engineering + prompt-engineering | Ollama, embeddings, RAG |
| **TOOLS** | `SINGULARITY-document-forge` | file-format-mastery + technical-writing | Typst PDF, court docs |
| **TOOLS** | `SINGULARITY-automation-engine` | automation-scraping + dev-experience + git-workflow | Go ingest, fd/bat, CLI |
| **TOOLS** | `SINGULARITY-code-mastery` | typescript-python + fullstack + backend + testing | Polyglot Go/Rust/Python/TS |
| **SPEC** | `SINGULARITY-debug-ops` | debugging-mastery + testing-quality + code-review | Systematic debugging, QA |
| **SPEC** | `SINGULARITY-security-fortress` | appsec + crypto-infra + offensive-security | Full-spectrum security |
| **APP** | `SINGULARITY-ui-engineering` | fullstack-web + design-ux + React/Next.js/D3 | Beautiful litigation UI |
| **APP** | `SINGULARITY-product-architecture` | backend-api + system-design + SaaS | Commercial product arch |
| **APP** | `SINGULARITY-creative-engine` | ai-media + messaging + mobile + marketing | Branding, mobile, growth |

> Full skill files at `.agents/skills/SINGULARITY-*/SKILL.md`. Each 300-500 lines of actionable, bleeding-edge guidance.

## Critical Timeline

| Date | Event |
|------|-------|
| 2023-10-13 | Emily recants: "nothing was physical" (NSPD-2023-08121) |
| 2023-10-15 | Emily files PPO (2023-5907-PP) — 2 days after recanting |
| 2024-04-01 | Andrew files Complaint for Custody |
| 2024-04-29 | **EX PARTE ORDER** — Joint legal/physical, 50/50 |
| 2024-07-17 | **TRIAL** — Sole custody to Mother (judgment under attack) |
| 2024-10-20 | Emily begins withholding child |
| 2025-05-04 | Albert Watson admits reports used for ex parte custody (NS2505044) |
| 2025-07-29 | **LAST CONTACT** — Father's last day with L.D.W. (separation anchor date) |
| 2025-08-09 | **EX PARTE ORDER** — ALL parenting time SUSPENDED |
| 2025-09-28 | **CUSTODY ORDER** — Emily 100%, zero for Father |
| 2026-03-25 | Emergency Motion filed (restore parenting time) |
| **TODAY** | **Separation: `(today - 2025-07-29).days` days.** Compute dynamically, ALWAYS. |

**NOTE:** Trial was July 17, **2024** (NOT 2025). Judge found ALL 12 MCL 722.23 factors favor Mother.

## Case Matrix

| Lane | Case Number | Court | Judge | Status |
|------|------------|-------|-------|--------|
| A | 2024-001507-DC | 14th Circuit, Muskegon | Hon. Jenny L. McNeill | Active — custody mod + emergency motion |
| B | 2025-002760-CZ | 14th Circuit, Civil | Hon. Kenneth Hoopes | **Dismissed w/ prejudice** |
| C | — | USDC Western District MI | TBD | Drafting — 42 USC §1983 |
| D | 2023-5907-PP | 14th Circuit, Muskegon | Hon. Jenny L. McNeill | Active — PPO termination |
| E | MULTI | JTC / MSC | Various | Active — complaints filed |
| F | COA 366810 | MI Court of Appeals / MSC | Panel TBD | Appeal of right |
| CRIMINAL | 2025-25245676SM | 60th District | Kostrzewa | Trial Apr 7, 2026 |

> ⚠️ **CRIMINAL IS 100% SEPARATE** — zero connection to Lanes A-F. Never cross-contaminate.

## Parties

- **Plaintiff:** Andrew James Pigors (pro se) — 1977 Whitehall Rd, Lot 17, North Muskegon, MI 49445 — (231) 903-5690 · andrewjpigors@gmail.com
- **Defendant:** Emily A. Watson (fka Pigors) — 2160 Garland Dr, Norton Shores, MI 49441
- **Opp. Counsel:** Jennifer Barnes P55406 — **WITHDREW Mar 2026** — Emily now UNREPRESENTED
- **Judge:** Hon. Jenny L. McNeill (P58235) — married to Cavan Berry (atty magistrate 60th District, office 990 Terrace St = FOC address)
- **Chief Judge:** Hon. Kenneth Hoopes — **FORMER LAW PARTNER of McNeill** at Ladas, Hoopes & McNeill
- **FOC:** Pamela Rusco (990 Terrace St — same address as judge's spouse)
- **Child:** L.D.W. (DOB: Nov 9, 2022, male) — MCR 8.119(H) initials ONLY
- **Emily's boyfriend:** Ronald Berry — NON-ATTORNEY, lives at 2160 Garland Dr
- **Emily's father:** Albert Watson — admitted reports used for ex parte custody leverage (NS2505044)
- **District Judge:** Hon. Maria Ladas-Hoopes (60th District) — FORMER LAW PARTNER of McNeill, wife of Chief Judge

> ⚠️ **THREE-COURT JUDICIAL CARTEL**: McNeill + Hoopes + Ladas-Hoopes = former partners at Ladas, Hoopes & McNeill (435 Whitehall Rd). Andrew lost HOME + SON + FREEDOM across all three courts. Entire 14th Circuit compromised → MSC original jurisdiction required.

## Mission & Quality

**MISSION: Undo EVERYTHING Judge McNeill and Emily Watson have done.**

- Every claim → cite MCR/MCL/case law (no naked claims)
- Every fact → trace to evidence_quotes or documents
- Every filing → IRAC structure, adversarial counter-argument, court-ready
- Always check deadlines before any filing recommendation
- Always assess MSC viability for judicial overreach issues
- Always consider multi-jurisdiction options for constitutional violations
- Separation counter → `(today - date(2025,7,29)).days` in every urgency assessment
- No external APIs — everything from litigation_context.db and local filesystem
- Mega-tasks → decompose into waves of 3, get confirmation, execute sequentially

## Key DB Tables

| Table | ~Rows | FTS5 Index | Notes |
|-------|-------|------------|-------|
| `evidence_quotes` | 175K+ | `evidence_fts` | Core evidence — always search first |
| `authority_chains_v2` | 167K+ | — | Citation chain graph (6.6× since v6.1) |
| `michigan_rules_extracted` | 19.8K | — | MCR/MCL/MRE full text (8.1× since v6.1) |
| `timeline_events` | 16.8K+ | `timeline_fts` | Chronological events |
| `md_sections` | 133K+ | `md_sections_fts` | Evolved .md file sections |
| `master_citations` | 72K+ | — | Full citation universe |
| `file_inventory` | 611K+ | — | All files across 7 drives |
| `md_cross_refs` | 26K+ | — | Cross-reference network |
| `contradiction_map` | 2.5K+ | — | Adversary contradictions |
| `judicial_violations` | 1.9K+ | — | Judicial misconduct evidence |
| `impeachment_matrix` | 5.1K+ | — | Cross-examination ammo |
| `police_reports` | 356 | — | NSPD incident reports |
| `berry_mcneill_intelligence` | 189+ | — | Judicial cartel intelligence |
| `semantic_vectors` | 75K+ | — | LanceDB (384-dim, all-MiniLM-L6-v2) |

> Row counts are approximate guidance — always query live per Rule 20.
> FTS5 safety per Rule 15: sanitize → try/except → LIKE fallback.
> Schema-verify per Rule 16: `PRAGMA table_info(X)` before new table queries.

## Filing Strategy (4-Tier)

| Tier | Filing | Authority |
|------|--------|-----------|
| **1 — NOW** | Emergency Motion to Restore (FILED 3/25) + MSC Superintending Control | MCR 7.306, 7.315(C) |
| **2 — 30d** | Disqualification (MCR 2.003) + MSC Mandamus | MCR 2.003, 7.306 |
| **3 — 60d** | COA Brief (366810) + Habeas Corpus | MCR 7.212, 600.4301 |
| **4 — Nuclear** | Federal §1983 + Civil Conspiracy | 42 USC §1983, 28 USC §1343 |

## Error Recovery Protocol

| Failure | Recovery | Escalation |
|---------|----------|------------|
| DB SQLITE_BUSY | Retry 3× with exponential backoff (1s→2s→4s). Verify PRAGMAs on connection | If persistent: check for WAL checkpoint lock, restart connection |
| FTS5 crash | Catch exception → fallback to parameterized LIKE query → return results with notice | If table corrupt: `INSERT INTO evidence_fts(evidence_fts) VALUES('rebuild')` |
| Table/column missing | `PRAGMA table_info()` → check 7 brain DBs + litigation_context.db → report which tables exist | If genuinely missing: create or flag as gap in plan.md |
| Agent dies | Read last checkpoint → respawn with full context from plan.md + DB | If repeated: decompose into smaller sub-tasks per Rule 11 |
| Empty results | Try broader search terms → check alternate tables → LIKE fallback → report "not found in DB" with tables searched | Never return nothing silently — always list what was searched |
| Python exec fails | Read full traceback → fix script → re-execute. Never report "script failed" without the fix | If unfixable: decompose per Rule 11, try alternate approach |
| Shell/EAGAIN | Use S/A-tier tools instead (exec_python, exec_git, grep, view). PowerShell is last resort | If PowerShell required: check shell count first per Rule 23 |

## Key File Paths

| Resource | Path |
|----------|------|
| Core DB | `litigation_context.db` (~1.3 GB, repo root) |
| Brain DBs | `00_SYSTEM/brains/*.db` |
| Shared Module | `00_SYSTEM/shared/` (v3.0.0 — get_db, sanitize_fts5, quick_query, fast_dataframe) |
| Engines (legacy) | `00_SYSTEM/engines/{nexus,chimera,chronos,cerberus,filing_engine,intake,rebuttal,narrative,delta999}/` |
| Engines (bleeding-edge) | `00_SYSTEM/engines/{analytics,semantic,search,typst,ingest}/` |
| MCP Servers | `00_SYSTEM/mcp_server/` |
| Daemon | `00_SYSTEM/daemon/` (watchdog, auto_ingest, task_queue) |
| Filing Templates | `00_SYSTEM/templates/filing_framework/` (caption, COS, deadline, checklist) |
| Filings | `05_FILINGS/` |
| Filing Stacks | `Desktop/PIGORS_v_WATSON_FILING_STACKS/` |
| Reference Docs | `.github/reference/` (db-schema, engine-inventory, msc-jurisdiction, authority-weapons, filing-pipeline) |
| Canon Structure | `_CANON.md` (13 canonical folders: 00_SYSTEM through 12_WORKSPACE) |
| Scoped Rules | `~/.github/instructions/*.instructions.md` |
| Hooks | `.github/hooks/` (governance-audit, session-logger, filing-qa) |
| Verify Script | `scripts/verify.bat` — run for fast feedback (<1s) |
| Temp Scripts | `D:\LitigationOS_tmp\` — all inline Python goes here per Rule 22 |

### Drive Inventory

| Drive | Contents | Priority |
|-------|----------|----------|
| C:\ | LitigationOS repo, core DB, all engines | PRIMARY |
| D:\ | Backups, temp scripts (`D:\LitigationOS_tmp\`), data exports | SECONDARY |
| F:\ | Config, evidence, emails, AppClose exports | EVIDENCE |
| G:\ | Source PDFs, scanned documents | SOURCE |
| H:\ | Safety snapshots, full DB backups | BACKUP |
| I:\ | Sorted legacy files | ARCHIVE |
| J:\ | Court rules, Albert Watson folder, legal reference | REFERENCE |

## Agent Fleet Patterns

Deploy **parallel agents** whenever possible. Key patterns:

| Pattern | Agents | Workflow |
|---------|--------|----------|
| **MSC Filing** | 4 explore + 1 general-purpose | Scan evidence/authorities/deadlines/rules in parallel → draft once complete |
| **Evidence Saturation** | 5 explore | Search evidence_fts, judicial_violations, impeachment, contradictions simultaneously |
| **Multi-Jurisdiction** | 1 explore + 2 general-purpose + 1 task | Jurisdiction query → parallel MSC + §1983 drafts → citation verification |
| **Deep Dive (person)** | 3 explore + 1 general-purpose | Pattern analysis + impeachment + contradictions → synthesize brief |

Agent types: `explore` (fast, DB/file queries) · `task` (commands, success/fail) · `general-purpose` (complex analysis, drafting) · `code-review` (diff analysis)

## Core Legal Concepts → Authority Map

| Concept | Authority | | Concept | Authority |
|---------|-----------|---|---------|-----------|
| best_interest_factors | MCL 722.23 | | superintending_control | MCR 7.306; art 6 § 4 |
| established_custodial_env | MCL 722.27(1)(c) | | mandamus | MCR 7.306 |
| parental_alienation | MCL 722.23(j) | | habeas_corpus | art 1 § 12; MCL 600.4301 |
| change_of_circumstances | *Vodvarka v Grasher* | | emergency_application | MCR 7.305(F); 7.315(C) |
| disqualification | MCR 2.003 | | federal_1983 | 42 USC § 1983; 28 USC § 1343 |
| ppo | MCL 600.2950 | | contempt | MCL 600.1701; MCR 3.606 |
| appeal_of_right | MCR 7.204/7.205 | | due_process_custody | US Const Amend XIV; *Troxel* |
| parenting_time | MCL 722.27a | | factor_j_willingness | MCL 722.23(j) |
| service_of_process | MCR 2.105 | | summary_disposition | MCR 2.116 |
| friend_of_court | MCL 552.501 et seq | | guardian_ad_litem | MCR 3.915; MCL 722.24 |

> Full 29-concept list + MLLM API methods: `.github/reference/msc-jurisdiction.md`

## Shell Management Protocol

> Accumulated stale shells waste memory and cause EAGAIN pipe failures. This protocol is MANDATORY.

1. **Before launching ANY shell:** `list_powershell` to see current count. If ≥3 active → stop oldest completed shell first
2. **After reading shell output:** `stop_powershell` immediately. Do not leave completed shells alive
3. **Max concurrent:** 3 shells. If you need a 4th, stop one first. No exceptions
4. **Naming:** Use descriptive shellIds (`verify-fts5`, `build-engine`, not `40`, `74`, `85`)
5. **At session boundaries:** Stop ALL shells. Leaving shells alive across context boundaries = memory leak
6. **Prefer S/A-tier tools:** `exec_python`, `exec_git`, `exec_command`, `grep`, `glob` have ZERO shell overhead. Use these instead of PowerShell whenever possible

## Compaction Resilience Protocol

> Context compaction summarizes earlier conversation, causing loss of investigation context. This protocol prevents re-work.

1. **Persist continuously, not in batches** — Write findings to DB/files AS you discover them. Don't accumulate discoveries in chat context waiting for a "final write." Each discovery → immediate INSERT
2. **plan.md is your post-compaction lifeline** — Update plan.md with: current phase, what's been completed, what's in progress, and key discoveries. After compaction, reading plan.md must tell you EXACTLY where you left off
3. **SQL todos track execution state** — Keep todo status current (`in_progress`, `done`, `blocked`). After compaction, `SELECT * FROM todos WHERE status != 'done'` instantly recovers your work queue
4. **Never re-investigate what's in the DB** — If a fact exists in `evidence_quotes`, `timeline_events`, `berry_mcneill_intelligence`, or `impeachment_matrix`, it's already persisted. Query the DB before re-reading source files
5. **User testimony = permanent record** — When the user provides testimony (quotes, dates, events), write to DB within the SAME agent turn. If compaction loses it, the user has to repeat themselves = Rule 13 violation
6. **Read checkpoints after compaction** — Session checkpoints at `session-state/{id}/checkpoints/` contain prior work. Read the most recent checkpoint to recover full context

## Judicial Intelligence (critical hearing testimony)

> User-provided testimony from hearings, persisted as permanent case intelligence.

- **Hearing 1 (re: suspension of parenting time):** Judge McNeill stated verbatim: *"Do not file anymore, I will not look at it"* — direct denial of access to courts
- **4th continued hearing (re: ex parte suspension):** Andrew successfully cross-examined witnesses despite judge cross-examining them herself. Same hearing: judge sentenced Andrew to 2 weeks jail for contempt — his "contempt" was objecting when judge and Emily discussed requiring prescription medication as condition for parenting time. Andrew stated neither was qualified or legally authorized to mandate medication. Judge told him to *"shut my mouth"*
- **Medication coercion:** Judge McNeill and Emily Watson discussed on the record that prescription medication would be the "only way" Andrew could see his son — constitutes unlawful practice of medicine and coercive conditioning of parental rights on medication compliance

## Document QA Protocol

When reviewing files: READ ALL → EXTRACT citations/facts/dates → CROSS-REFERENCE against DB → FLAG hallucinations/wrong dates/AI artifacts/child's full name → FIX surgically → VALIDATE

### Auto-Fix Targets
- `MCL 722.27c` → `MCL 722.23(j)` · Child's full name → `L.D.W.` · Hardcoded day counts → dynamic calc · `undersigned counsel` → `Plaintiff, appearing pro se` · AI scoring/LitigationOS refs → remove · `Brady v Maryland` in family law → `Mathews v Eldridge` · "Jane Berry" / "Patricia Berry" → DELETE (hallucinations) · Barnes as current counsel → "WITHDREW Mar 2026"

*END OF SINGULARITY v7.0 FORGE — 15 Superskills · 14 Engines · Bleeding-Edge Toolchain · ZERO API Dependency*

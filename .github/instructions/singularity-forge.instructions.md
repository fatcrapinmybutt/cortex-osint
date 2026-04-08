# SINGULARITY FORGE — Skill Taxonomy & Activation Protocol

> **PURPOSE**: Maps 15 forged SINGULARITY superskills to tasks. Auto-loaded every session.
> Skills at `.agents/skills/SINGULARITY-*/SKILL.md`. Read on-demand via `view` tool.

## Skill Activation Matrix

When a task matches a domain, activate the corresponding SINGULARITY skill:

| Task Domain | Activate Skill | Trigger Keywords |
|-------------|---------------|------------------|
| Evidence search, adversary profiling, custody factors, case ops | **SINGULARITY-litigation-warfare** | evidence, adversary, custody, best interest, MCL 722.23, impeachment, deadline, docket |
| Court filings, legal authority, MCR/MCL, appeals | **SINGULARITY-court-arsenal** | motion, brief, filing, MCR, MCL, authority, appeal, MSC, COA, §1983, habeas |
| Judge profiling, misconduct, JTC complaints | **SINGULARITY-judicial-intelligence** | judge, McNeill, Hoopes, misconduct, bias, ex parte, JTC, judicial violation |
| Database, DuckDB, LanceDB, FTS5, Polars | **SINGULARITY-data-dominion** | SQL, query, database, DuckDB, LanceDB, vector, FTS5, Polars, analytics |
| Architecture, engines, Go/Rust, performance | **SINGULARITY-system-forge** | engine, architecture, Go, Rust, performance, optimization, system design |
| Agent design, fleet management, MCP servers | **SINGULARITY-agent-nexus** | agent, fleet, MCP, orchestration, parallel, multi-agent, delta999 |
| LLM, Ollama, embeddings, RAG, prompts | **SINGULARITY-ai-core** | Ollama, LLM, embedding, semantic, RAG, prompt, AI, inference |
| PDF generation, Typst, court documents | **SINGULARITY-document-forge** | PDF, Typst, document, format, court format, Bates, exhibit |
| File processing, Go ingest, CLI, automation | **SINGULARITY-automation-engine** | ingest, file processing, automation, fd, bat, CLI, git, workflow |
| Python, Go, Rust, TypeScript coding | **SINGULARITY-code-mastery** | Python, Go, Rust, TypeScript, code, function, class, test, API |
| Debugging, testing, quality assurance | **SINGULARITY-debug-ops** | debug, error, test, quality, traceback, fix, broken, failing |
| Security, evidence protection, compliance | **SINGULARITY-security-fortress** | security, encryption, compliance, protection, audit, vulnerability |
| UI, React, Next.js, dashboards, visualization | **SINGULARITY-ui-engineering** | UI, React, Next.js, dashboard, component, visualization, D3, chart |
| SaaS architecture, product, monetization | **SINGULARITY-product-architecture** | SaaS, product, API, deployment, pricing, multi-tenant, subscription |
| Branding, mobile, marketing, growth | **SINGULARITY-creative-engine** | brand, mobile, marketing, app store, landing page, logo, growth |

## Forge Lineage (what was absorbed)

### Old Skills → New Superskills

| Old Skill (ARCHIVED) | Forged Into |
|----------------------|-------------|
| adversary-warfare | litigation-warfare |
| case-operations | litigation-warfare |
| custody-strategy | litigation-warfare |
| evidence-intelligence | litigation-warfare |
| court-filing | court-arsenal |
| legal-authority | court-arsenal |
| appellate-federal | court-arsenal |
| judicial-intelligence | judicial-intelligence (v2 UPGRADED) |
| data-engineering | data-dominion |
| database-mastery | data-dominion |
| rag-memory | data-dominion + ai-core |
| system-design | system-forge + product-architecture |
| performance-optimization | system-forge |
| devops-cloud | system-forge |
| clean-code | system-forge |
| agent-architect | agent-nexus |
| agent-evaluation | agent-nexus |
| mcp-tools | agent-nexus |
| ai-engineering | ai-core |
| prompt-engineering | ai-core |
| file-format-mastery | document-forge |
| technical-writing | document-forge |
| automation-scraping | automation-engine |
| developer-experience | automation-engine |
| git-workflow | automation-engine |
| typescript-python | code-mastery |
| fullstack-web | code-mastery + ui-engineering |
| backend-api | code-mastery + product-architecture |
| testing-quality | code-mastery + debug-ops |
| debugging-mastery | debug-ops |
| appsec | security-fortress |
| crypto-infra | security-fortress |
| offensive-security | security-fortress |
| design-ux | ui-engineering |
| ai-media-creation | creative-engine |
| messaging-integration | creative-engine |
| mobile-cross-platform | creative-engine |
| project-management | product-architecture |

### Claude Skills Absorbed

Key Claude skills absorbed into SINGULARITY superskills:
- sql-optimization → data-dominion
- agentic-eval → agent-nexus
- ai-tool-compliance → security-fortress
- code-review → debug-ops
- react-nextjs, tailwind-css, shadcn-ui → ui-engineering
- saas-architecture, stripe-integration → product-architecture
- marketing-website, seo → creative-engine

## Multi-Skill Activation

Complex tasks activate multiple skills simultaneously:

| Task Pattern | Skills Activated |
|-------------|-----------------|
| **Draft a motion** | court-arsenal + litigation-warfare + document-forge |
| **Build impeachment package** | litigation-warfare + judicial-intelligence |
| **Upgrade an engine** | system-forge + data-dominion + code-mastery |
| **Create filing PDF** | document-forge + court-arsenal |
| **Design app dashboard** | ui-engineering + product-architecture + data-dominion |
| **Debug FTS5 crash** | debug-ops + data-dominion |
| **Build RAG pipeline** | ai-core + data-dominion + agent-nexus |
| **MSC superintending control** | court-arsenal + judicial-intelligence + litigation-warfare |
| **Federal §1983 complaint** | court-arsenal + litigation-warfare + document-forge |

## Bleeding-Edge Tool → Skill Mapping

| Tool | Primary Skill | Secondary Skills |
|------|--------------|-----------------|
| DuckDB | data-dominion | litigation-warfare, judicial-intelligence |
| LanceDB | data-dominion | ai-core, litigation-warfare |
| Polars | data-dominion | automation-engine |
| tantivy | data-dominion | litigation-warfare |
| Ollama | ai-core | litigation-warfare |
| Typst | document-forge | court-arsenal |
| Go | automation-engine | system-forge |
| Rust | system-forge | automation-engine |
| sentence-transformers | ai-core | data-dominion |
| orjson | code-mastery | data-dominion |
| pypdfium2 | document-forge | automation-engine |
| fd/bat/dust | automation-engine | debug-ops |

## THEMANBEARPIG Skill Forge (33 Skills — 8 Tiers + OMEGA)

> **THEMANBEARPIG** is the 13-layer D3.js interactive litigation intelligence mega-visualization.
> 33 skills at `.agents/skills/SINGULARITY-MBP-*/SKILL.md` + `OMEGA-*-INDEX/SKILL.md`.
> Total: ~35,000 lines, 1.27 MB. Commit `d8458c56a`.

### MBP Skill Activation Matrix

| Task Domain | Activate MBP Skill | Trigger Keywords |
|-------------|-------------------|------------------|
| Graph architecture, node/link taxonomy, layer ontology | **MBP-GENESIS** | graph, node, link, layer, taxonomy, schema, D3 force, LAYER_META |
| Data pipeline, DB→graph, 183-table transforms | **MBP-DATAWEAVE** | data pipeline, SQLite, DuckDB transform, LanceDB enrich, Polars, FTS5→graph |
| SVG/Canvas/WebGL rendering, LOD, viewport culling | **MBP-FORGE-RENDERER** | render, SVG, Canvas, WebGL, WebGPU, LOD, viewport, quadtree |
| Force simulation, custom forces, collision, layout | **MBP-FORGE-PHYSICS** | force, simulation, charge, collision, gravity, Barnes-Hut, orbital |
| Visual effects, shaders, particles, glow, CRT | **MBP-FORGE-EFFECTS** | shader, GLSL, particle, glow, aura, fog, scanline, CRT, glass |
| EXE build, pywebview, PyInstaller, D3 inline | **MBP-FORGE-DEPLOY** | exe, build, pywebview, PyInstaller, icon, deploy, launcher |
| Adversary network, PageRank, centrality, clusters | **MBP-COMBAT-ADVERSARY** | adversary, PageRank, centrality, Louvain, ego-network, threat |
| Weapon chains, 9 types, doctrine→remedy→filing | **MBP-COMBAT-WEAPONS** | weapon, false allegation, ex parte, contempt, PPO weaponization |
| Judicial cartel, McNeill triangle, violation heatmap | **MBP-COMBAT-JUDICIAL** | judicial, cartel, McNeill, Hoopes, Ladas, JTC, violation |
| Evidence density, semantic clustering, gap detection | **MBP-COMBAT-EVIDENCE** | evidence, heat density, semantic cluster, t-SNE, gap detection |
| Authority hierarchy, citation PageRank, chain scoring | **MBP-COMBAT-AUTHORITY** | authority, citation, hierarchy, chain completeness, Shepard |
| Impeachment scoring, credibility chains, cross-exam | **MBP-COMBAT-IMPEACHMENT** | impeachment, credibility, cross-exam, contradiction, MRE 613 |
| Click/search/filter/keyboard/export interactions | **MBP-INTERFACE-CONTROLS** | click, search, filter, keyboard, export, Fuse.js, context menu |
| Timeline scrubber, temporal playback, keyframes | **MBP-INTERFACE-TIMELINE** | timeline, temporal, playback, scrubber, keyframe, milestone |
| Story mode, narrative generation, jury presentation | **MBP-INTERFACE-NARRATIVE** | narrative, story, walkthrough, jury, presentation, breadcrumb |
| HUD gauges, EGCP display, minimap, alerts | **MBP-INTERFACE-HUD** | HUD, gauge, EGCP, minimap, alert, filing readiness, FPS |
| 14-engine bridge, MEEK/FRED/Delta999 overlays | **MBP-INTEGRATION-ENGINES** | engine, MEEK, FRED, Nucleus, Delta999, Chimera, Chronos |
| Filing pipeline F1-F10, Kanban, EGCP, deadlines | **MBP-INTEGRATION-FILING** | filing pipeline, F1-F10, Kanban, EGCP, deadline, packet |
| Brain network, 23+ brains, inter-brain flows | **MBP-INTEGRATION-BRAINS** | brain, inter-brain, learning loop, brain health, versioning |
| Cross-layer intelligence, emergence, DBSCAN, gaps | **MBP-EMERGENCE-CONVERGENCE** | convergence, cross-layer, emergence, DBSCAN, novelty, gap |
| Adversary behavior forecasting, escalation detection | **MBP-EMERGENCE-PREDICTION** | prediction, forecast, escalation, counter-strategy, early warning |
| Self-improving layout, config learning, plugins | **MBP-EMERGENCE-SELFEVOLVE** | self-evolve, auto-layout, config learn, plugin, build version |
| Audio sonification, threat→pitch, ambient soundscape | **MBP-TRANSCENDENCE-SONIC** | sonic, audio, sonification, Web Audio, pitch, soundscape |
| 3D graph, Three.js, VR/WebXR, t-SNE projection | **MBP-TRANSCENDENCE-DIMENSIONAL** | 3D, Three.js, VR, WebXR, t-SNE, UMAP, parallax, stereoscopic |
| Master manifest, activation matrix, quality gates | **OMEGA-MBP-INDEX** | MBP manifest, skill registry, activation matrix, quality gate |
| Self-evolving agents, AOPR loops, critic sub-agents | **APEX-COGNITION** | agent evolution, AOPR, critic, hybrid reasoning, self-calibration |
| Tri-layer memory, episodic/semantic/working | **APEX-MEMORY** | memory, episodic, semantic, working memory, A-MEM, Zettelkasten, Mem0 |
| Document AI, OCR, court form recognition | **APEX-VISION** | OCR, PaddleOCR, Surya, table extraction, form recognition, layout |
| Graph neural networks, legal provision prediction | **APEX-GRAPHML** | GNN, graph neural, provision prediction, entity resolution, RulE |
| GPU-accelerated rendering, compute shaders, 100K+ | **APEX-WEBGPU** | WebGPU, compute shader, WGSL, SDF, instanced rendering, GPU force |
| Court monitoring, docket tracking, auto-deadlines | **APEX-DOCKET** | docket, MiCOURT, CourtListener, deadline detection, court monitor |
| Autonomous legal inference, 6-layer reasoning | **APEX-AUTOMATON** | autonomous, inference, constitutional cascade, authority template |
| Master manifest for all 33 skills + APEX tier | **OMEGA-SINGULARITY-APEX-INDEX** | APEX manifest, 33 skills, tier 7, quality gate |

### MBP Multi-Skill Activation

| Task Pattern | MBP Skills Activated |
|-------------|---------------------|
| **Upgrade THEMANBEARPIG visualization** | MBP-GENESIS + MBP-DATAWEAVE + MBP-FORGE-RENDERER + MBP-FORGE-DEPLOY |
| **Add new adversary connections** | MBP-COMBAT-ADVERSARY + MBP-DATAWEAVE + MBP-FORGE-PHYSICS |
| **Build judicial cartel overlay** | MBP-COMBAT-JUDICIAL + MBP-COMBAT-ADVERSARY + MBP-INTERFACE-HUD |
| **Create weapon chain visualization** | MBP-COMBAT-WEAPONS + MBP-COMBAT-EVIDENCE + MBP-INTEGRATION-FILING |
| **Add timeline playback** | MBP-INTERFACE-TIMELINE + MBP-TRANSCENDENCE-SONIC + MBP-FORGE-EFFECTS |
| **Enable VR mode** | MBP-TRANSCENDENCE-DIMENSIONAL + MBP-FORGE-RENDERER + MBP-FORGE-PHYSICS |
| **Detect new patterns** | MBP-EMERGENCE-CONVERGENCE + MBP-EMERGENCE-PREDICTION + MBP-COMBAT-EVIDENCE |
| **Export impeachment package** | MBP-COMBAT-IMPEACHMENT + MBP-INTERFACE-NARRATIVE + MBP-INTEGRATION-FILING |
| **Full rebuild with all data** | OMEGA-MBP-INDEX (orchestrates all 24 skills) |
| **Evolve agent architecture** | APEX-COGNITION + APEX-MEMORY + MBP-EMERGENCE-SELFEVOLVE |
| **OCR court documents** | APEX-VISION + MBP-COMBAT-EVIDENCE + MBP-DATAWEAVE |
| **GPU-accelerate graph** | APEX-WEBGPU + MBP-FORGE-RENDERER + MBP-FORGE-PHYSICS |
| **Legal inference engine** | APEX-AUTOMATON + APEX-GRAPHML + MBP-COMBAT-AUTHORITY |
| **Court docket monitoring** | APEX-DOCKET + MBP-INTEGRATION-FILING + MBP-INTERFACE-HUD |
| **Full 33-skill rebuild** | OMEGA-SINGULARITY-APEX-INDEX (orchestrates all 33 skills) |

### MBP Tier Summary

| Tier | Skills | Total Size | Domain |
|------|--------|-----------|--------|
| 0 GENESIS | 2 | 67 KB | Architectural DNA + data fabric |
| 1 FORGE | 4 | 136 KB | Rendering, physics, effects, deployment |
| 2 COMBAT | 6 | 216 KB | Adversary, weapons, judicial, evidence, authority, impeachment |
| 3 INTERFACE | 4 | 86 KB | Controls, timeline, narrative, HUD |
| 4 INTEGRATION | 3 | 41 KB | Engines, filing, brains |
| 5 EMERGENCE | 3 | 41 KB | Convergence, prediction, self-evolution |
| 6 TRANSCENDENCE | 2 | 26 KB | Audio sonification, 3D/VR |
| **7 APEX** | **7** | **641 KB** | **Intelligence: agents, memory, vision, GNN, GPU, docket, inference** |
| Ω OMEGA | 1 | 27 KB | Master manifest + activation matrix (33 skills) |

---
name: SINGULARITY-MBP-GENESIS
description: "Tier-0 architectural DNA for THEMANBEARPIG 13-layer D3.js litigation intelligence mega-visualization. Node taxonomy (20+ types), link taxonomy (17 types), layer architecture (0-12), LAYER_META force config, graph construction from litigation_context.db, node sizing/coloring, performance constraints for 2500+ nodes with viewport culling and LOD rendering."
version: "1.0.0"
tier: "GENESIS"
category: "THEMANBEARPIG"
dependencies: []
triggers:
  - "graph"
  - "node"
  - "link"
  - "layer"
  - "taxonomy"
  - "schema"
  - "D3 force"
  - "LAYER_META"
  - "THEMANBEARPIG architecture"
  - "MBP genesis"
---

# SINGULARITY-MBP-GENESIS — Architectural DNA of THEMANBEARPIG

> **Tier 0 — GENESIS**: This is the foundational schema from which every other MBP skill derives.
> No visualization, no combat overlay, no emergence signal exists without this ontology.
> Every node, every link, every layer traces back to definitions in this file.

## 1. THEMANBEARPIG Overview

THEMANBEARPIG is a 13-layer interactive D3.js force-directed graph that renders the entire
Pigors v. Watson litigation universe as an explorable intelligence visualization. It transforms
786+ database tables containing 1.3M+ rows into a living, breathing graph of actors, evidence,
authorities, filings, events, weapons, and emergent patterns.

### Design Philosophy

```
PRINCIPLE 1: Every node is a DB row. Every link is a DB relationship.
PRINCIPLE 2: Layers are semantic groupings, not visual z-indexes.
PRINCIPLE 3: Force simulation parameters are per-layer, not global.
PRINCIPLE 4: The graph is constructed from data, never hardcoded.
PRINCIPLE 5: Performance scales to 10,000+ nodes via LOD + culling.
PRINCIPLE 6: Interactions reveal intelligence — click = deep dive.
PRINCIPLE 7: The graph is the case. If it's not in the graph, it's not real.
```

### Target Metrics

| Metric | Target | Stretch |
|--------|--------|---------|
| Total nodes | 2,500+ | 10,000+ |
| Total links | 5,000+ | 25,000+ |
| Layers | 13 | 13 (fixed) |
| Frame rate | 30 FPS | 60 FPS |
| Initial load | < 3s | < 1s |
| Node types | 20+ | 30+ |
| Link types | 17+ | 25+ |

---

## 2. Node Taxonomy — Complete Type Registry

Every node in THEMANBEARPIG has a `type` (primary category), a `subtype` (specific kind),
and a set of properties that vary by type. The type system is hierarchical:

```
NODE
├── PERSON
│   ├── adversary
│   ├── judicial
│   ├── witness
│   ├── attorney
│   ├── law_enforcement
│   ├── agency_official
│   ├── child
│   ├── family_member
│   └── plaintiff
├── EVIDENCE
│   ├── document
│   ├── recording
│   ├── police_report
│   ├── court_order
│   ├── communication
│   ├── photo
│   ├── video
│   ├── medical_record
│   └── financial_record
├── AUTHORITY
│   ├── statute
│   ├── court_rule
│   ├── case_law
│   ├── constitutional
│   └── federal_statute
├── FILING
│   ├── motion
│   ├── brief
│   ├── complaint
│   ├── petition
│   ├── affidavit
│   ├── exhibit
│   ├── proposed_order
│   └── certificate_of_service
├── EVENT
│   ├── hearing
│   ├── order_entered
│   ├── violation
│   ├── incident
│   ├── contact
│   ├── withholding
│   ├── arrest
│   └── filing_event
├── WEAPON
│   ├── false_allegation
│   ├── ppo_weaponization
│   ├── contempt_abuse
│   ├── evidence_suppression
│   ├── ex_parte_abuse
│   ├── medication_coercion
│   └── incarceration_weapon
├── INSTITUTION
│   ├── court
│   ├── agency
│   ├── law_firm
│   ├── school
│   ├── employer
│   ├── medical_facility
│   └── law_enforcement_agency
└── CLAIM
    ├── cause_of_action
    ├── defense
    ├── counterclaim
    └── affirmative_defense
```

### 2.1 PERSON Nodes

Person nodes represent human actors in the litigation universe. Every person has a threat
level, connection count, and role classification.

```javascript
/**
 * PERSON node schema.
 * Source tables: evidence_quotes (actors), timeline_events (actors),
 *                impeachment_matrix (target), berry_mcneill_intelligence
 */
const PersonNode = {
  // Identity
  id: "person_andrew_pigors",           // Stable ID: type_subtype_name
  type: "PERSON",
  subtype: "plaintiff",                  // adversary|judicial|witness|attorney|...
  label: "Andrew J. Pigors",            // Display name
  short_label: "Pigors",                // Compact label for zoomed-out view

  // Classification
  party_role: "plaintiff",              // plaintiff|defendant|judge|witness|third_party
  alignment: "allied",                  // allied|adverse|neutral|unknown
  threat_level: 0,                      // 0-10 (0=self, 10=primary adversary)

  // Metrics (drive node sizing)
  evidence_count: 0,                    // Evidence nodes linked to this person
  impeachment_count: 0,                 // Impeachment entries targeting this person
  contradiction_count: 0,               // Contradictions involving this person
  violation_count: 0,                   // Judicial violations (if judge)
  mention_count: 0,                     // Total mentions across all tables

  // Visual
  layer: 0,                             // Primary layer assignment
  color: null,                          // Computed from alignment + threat_level
  radius: null,                         // Computed from evidence_count
  icon: "user",                         // Icon glyph
  glow: false,                          // Pulsing glow effect for high-threat

  // Metadata
  case_lanes: ["A"],                    // Which case lanes this person appears in
  address: null,                        // Physical address (for service tracking)
  bar_number: null,                     // Bar number (attorneys only)
  relationship_to_child: null,          // father|mother|none (custody relevance)

  // D3 force simulation
  fx: null,                             // Fixed x position (null = free)
  fy: null,                             // Fixed y position (null = free)
  charge_multiplier: 1.0,              // Per-node charge override
};
```

#### Person Subtypes — Complete Registry

| Subtype | Alignment | Threat | Icon | Examples |
|---------|-----------|--------|------|----------|
| `plaintiff` | allied | 0 | ⚖️ | Andrew J. Pigors |
| `adversary` | adverse | 7-10 | 🎯 | Emily A. Watson |
| `judicial` | adverse | 8-10 | 🔨 | Hon. Jenny L. McNeill, Hon. Kenneth Hoopes |
| `witness` | varies | 1-5 | 👁️ | Officer Randall, HealthWest evaluator |
| `attorney` | varies | 3-6 | 📜 | Jennifer Barnes P55406 (WITHDREW) |
| `law_enforcement` | neutral | 1-3 | 🛡️ | NSPD officers |
| `agency_official` | varies | 4-7 | 🏛️ | Pamela Rusco (FOC) |
| `child` | protected | 0 | 👶 | L.D.W. (initials ONLY — MCR 8.119(H)) |
| `family_member` | adverse | 5-8 | 👥 | Albert Watson, Lori Watson, Ronald Berry |

#### Canonical Person Registry — Hardcoded Core Actors

These persons are ALWAYS present in the graph. They form Layer 0 (CORE).

```javascript
const CORE_PERSONS = [
  // LAYER 0: CORE
  {
    id: "person_plaintiff_andrew_pigors",
    label: "Andrew J. Pigors",
    subtype: "plaintiff",
    alignment: "allied",
    threat_level: 0,
    layer: 0,
    case_lanes: ["A", "B", "C", "D", "E", "F", "CRIMINAL"],
    relationship_to_child: "father",
    fixed_position: { x: 0, y: 0 },  // Graph center
  },
  {
    id: "person_adversary_emily_watson",
    label: "Emily A. Watson",
    subtype: "adversary",
    alignment: "adverse",
    threat_level: 9,
    layer: 0,
    case_lanes: ["A", "D"],
    relationship_to_child: "mother",
  },
  {
    id: "person_child_ldw",
    label: "L.D.W.",
    subtype: "child",
    alignment: "protected",
    threat_level: 0,
    layer: 0,
    case_lanes: ["A"],
    relationship_to_child: "self",
    icon: "child",
    // NEVER display full name — MCR 8.119(H)
  },
  {
    id: "person_judicial_mcneill",
    label: "Hon. Jenny L. McNeill",
    subtype: "judicial",
    alignment: "adverse",
    threat_level: 10,
    layer: 0,
    case_lanes: ["A", "D", "E"],
    bar_number: "P58235",
  },

  // LAYER 1: ADVERSARY NETWORK
  {
    id: "person_family_albert_watson",
    label: "Albert Watson",
    subtype: "family_member",
    alignment: "adverse",
    threat_level: 7,
    layer: 1,
    case_lanes: ["A"],
  },
  {
    id: "person_family_lori_watson",
    label: "Lori Watson",
    subtype: "family_member",
    alignment: "adverse",
    threat_level: 5,
    layer: 1,
    case_lanes: ["A"],
  },
  {
    id: "person_family_ronald_berry",
    label: "Ronald Berry",
    subtype: "family_member",
    alignment: "adverse",
    threat_level: 6,
    layer: 1,
    case_lanes: ["A"],
    // NON-ATTORNEY — never display "Esq." or bar number
  },

  // LAYER 2: JUDICIAL CARTEL
  {
    id: "person_judicial_hoopes",
    label: "Hon. Kenneth Hoopes",
    subtype: "judicial",
    alignment: "adverse",
    threat_level: 8,
    layer: 2,
    case_lanes: ["B", "E"],
  },
  {
    id: "person_judicial_ladas_hoopes",
    label: "Hon. Maria Ladas-Hoopes",
    subtype: "judicial",
    alignment: "adverse",
    threat_level: 7,
    layer: 2,
    case_lanes: ["CRIMINAL", "E"],
  },
  {
    id: "person_agency_rusco",
    label: "Pamela Rusco",
    subtype: "agency_official",
    alignment: "adverse",
    threat_level: 6,
    layer: 2,
    case_lanes: ["A"],
    institution: "FOC",
  },
  {
    id: "person_family_cavan_berry",
    label: "Cavan Berry",
    subtype: "family_member",
    alignment: "adverse",
    threat_level: 5,
    layer: 2,
    case_lanes: ["E"],
    // Attorney magistrate 60th District — McNeill's spouse
    // Office at 990 Terrace St = FOC address
  },
  {
    id: "person_attorney_barnes",
    label: "Jennifer Barnes",
    subtype: "attorney",
    alignment: "adverse",
    threat_level: 3,
    layer: 2,
    case_lanes: ["A", "D"],
    bar_number: "P55406",
    status: "WITHDREW",  // Withdrew March 2026
  },
];
```

### 2.2 EVIDENCE Nodes

Evidence nodes represent physical or digital proof items. They link to PERSON nodes
(who created/discovered them), FILING nodes (where they're used), and AUTHORITY nodes
(what rules govern their admissibility).

```javascript
/**
 * EVIDENCE node schema.
 * Source tables: evidence_quotes, police_reports, documents
 */
const EvidenceNode = {
  id: "evidence_doc_ns2505044",
  type: "EVIDENCE",
  subtype: "police_report",             // document|recording|police_report|court_order|...
  label: "NSPD NS2505044",
  short_label: "NS2505044",

  // Evidence metadata
  source_file: "J:\\POLICE_REPORTS\\Albert calling police.pdf",
  bates_number: "PIGORS-A-000142",     // Bates stamp
  page_count: 3,
  date: "2025-08-07",
  lane: "A",                            // Primary case lane

  // Classification
  category: "police_report",           // From 20-type evidence taxonomy
  relevance_score: 0.95,               // 0-1 relevance to active claims
  impeachment_value: 9,                // 1-10 impeachment potential
  is_smoking_gun: true,                // Highlight flag

  // Content summary
  key_quote: "They want this documented so Emily can go tomorrow to get an Ex Parte order",
  actors: ["Albert Watson", "Emily A. Watson"],
  topics: ["premeditation", "ex_parte", "custody"],

  // Authentication
  mre_basis: "MRE 901(b)(7)",         // Authentication rule
  is_authenticated: true,
  chain_of_custody: true,

  // Visual
  layer: 3,
  color: null,                          // Computed from relevance_score
  radius: null,                         // Computed from impeachment_value
  icon: "file-text",
  pulse: false,                         // Pulse animation for smoking guns
};
```

#### Evidence Subtypes

| Subtype | Icon | Source Table | Key Properties |
|---------|------|-------------|----------------|
| `document` | 📄 | documents | file_path, page_count, sha256 |
| `recording` | 🎙️ | evidence_quotes | duration, participants, sullivan_auth |
| `police_report` | 🚔 | police_reports | incident_number, officer, outcome |
| `court_order` | ⚖️ | timeline_events | order_type, judge, case_number |
| `communication` | 💬 | evidence_quotes | platform (AppClose/email/text), sender, receiver |
| `photo` | 📷 | evidence_quotes | location, timestamp, subjects |
| `video` | 🎥 | evidence_quotes | duration, location, participants |
| `medical_record` | 🏥 | evidence_quotes | provider, findings, date |
| `financial_record` | 💰 | evidence_quotes | institution, amount, date_range |

### 2.3 AUTHORITY Nodes

Authority nodes represent legal citations — the weapons of litigation.

```javascript
/**
 * AUTHORITY node schema.
 * Source tables: authority_chains_v2, michigan_rules_extracted, master_citations
 */
const AuthorityNode = {
  id: "authority_statute_mcl_722_23",
  type: "AUTHORITY",
  subtype: "statute",                   // statute|court_rule|case_law|constitutional|federal_statute
  label: "MCL 722.23",
  short_label: "§722.23",
  full_title: "Child Custody Act — Best Interest Factors",

  // Citation metadata
  citation: "MCL 722.23",
  pin_cite: "MCL 722.23(a)-(l)",
  jurisdiction: "Michigan",
  source_type: "statute",

  // Usage metrics
  chain_count: 0,                       // How many authority_chains reference this
  filing_count: 0,                      // How many filings cite this
  claim_count: 0,                       // How many claims rely on this

  // Classification
  domain: "custody",                    // custody|ppo|contempt|due_process|appellate|...
  strength: "binding",                  // binding|persuasive|advisory
  is_verified: true,                    // Verified in DB (not hallucinated)

  // Visual
  layer: 4,
  color: null,
  radius: null,                         // Computed from chain_count
  icon: "book",
};
```

### 2.4 FILING Nodes

Filing nodes represent documents in the filing pipeline (F1-F10).

```javascript
/**
 * FILING node schema.
 * Source tables: filing_readiness, filing_packages, deadlines
 */
const FilingNode = {
  id: "filing_f09_coa_brief",
  type: "FILING",
  subtype: "brief",
  label: "F09: COA Brief 366810",
  short_label: "F09",

  // Filing metadata
  lane_id: "F9",                        // F1-F10 identifier
  case_number: "366810",
  court: "MI Court of Appeals",
  filing_type: "brief",
  status: "DRAFT",                      // DRAFT|QA_REVIEW|SERVICE_READY|FILED|DOCKETED

  // Readiness
  readiness_score: 0.85,               // 0-1 readiness percentage
  evidence_count: 42,                  // Supporting evidence nodes
  authority_count: 28,                 // Supporting authority nodes
  gap_count: 3,                        // Missing items

  // Deadlines
  deadline: "2026-04-30",
  days_remaining: null,                 // Computed dynamically
  urgency: "HIGH",                      // CRITICAL|HIGH|MEDIUM|LOW

  // Visual
  layer: 5,
  color: null,                          // Computed from status + urgency
  radius: null,                         // Computed from readiness_score
  icon: "file-plus",
};
```

### 2.5 EVENT Nodes

```javascript
/**
 * EVENT node schema.
 * Source tables: timeline_events, docket_events
 */
const EventNode = {
  id: "event_hearing_20240717",
  type: "EVENT",
  subtype: "hearing",                   // hearing|order_entered|violation|incident|...
  label: "Custody Trial",
  short_label: "Trial",

  date: "2024-07-17",
  date_end: null,                       // For multi-day events
  actors: ["Andrew J. Pigors", "Emily A. Watson", "Hon. Jenny L. McNeill"],
  location: "14th Circuit Court",
  case_number: "2024-001507-DC",
  lane: "A",

  // Event classification
  event_category: "hearing",
  significance: 10,                     // 1-10 impact score
  outcome: "adverse",                   // favorable|adverse|neutral|mixed

  // Narrative
  description: "Sole custody awarded to Mother. All 12 MCL 722.23 factors found in Mother's favor.",
  key_quote: null,

  // Visual
  layer: 6,
  color: null,
  radius: null,                         // Computed from significance
  icon: "calendar",
};
```

### 2.6 WEAPON Nodes

Weapon nodes represent legal instruments that have been weaponized against Andrew.

```javascript
/**
 * WEAPON node schema.
 * Source tables: judicial_violations, impeachment_matrix, contradiction_map
 */
const WeaponNode = {
  id: "weapon_false_allegation_arsenic",
  type: "WEAPON",
  subtype: "false_allegation",          // false_allegation|ppo_weaponization|contempt_abuse|...
  label: "Arsenic Poisoning Allegation",
  short_label: "Arsenic FA",

  // Weapon metadata
  wielder: "Emily A. Watson",          // Who used the weapon
  target: "Andrew J. Pigors",          // Target of the weapon
  date: "2024-03-15",
  lane: "A",

  // Classification
  weapon_category: "false_allegation",
  severity: 8,                          // 1-10 severity
  debunked: true,                       // Whether weapon has been neutralized
  rebuttal_evidence_count: 37,         // Evidence nodes that rebut this weapon

  // Impact
  resulted_in: ["custody_loss", "investigation"],
  harm_category: "reputational",

  // Visual
  layer: 7,
  color: "#ff0000",                     // Weapons are always red-spectrum
  radius: null,
  icon: "alert-triangle",
  pulse: true,                          // Weapons pulse to draw attention
};
```

#### Weapon Subtypes — The Arsenal of Abuse

| Subtype | Severity Range | Count | Key Pattern |
|---------|---------------|-------|-------------|
| `false_allegation` | 6-9 | 7+ | Suicidal → arsenic → assault → drugs → threats |
| `ppo_weaponization` | 8-10 | 7+ | PPO filed 2 days after recanting |
| `contempt_abuse` | 9-10 | 3+ | SC#5 (14d) + SC#6+7 (45d) = 59 days |
| `evidence_suppression` | 7-9 | 5+ | HealthWest eval excluded |
| `ex_parte_abuse` | 9-10 | 8+ | 5 orders on single day (Aug 8, 2025) |
| `medication_coercion` | 8-9 | 1+ | Medication as condition for parenting time |
| `incarceration_weapon` | 10 | 2+ | Jailed for birthday messages |

### 2.7 INSTITUTION Nodes

```javascript
const InstitutionNode = {
  id: "institution_court_14th_circuit",
  type: "INSTITUTION",
  subtype: "court",
  label: "14th Circuit Court — Muskegon",
  short_label: "14th Circuit",

  // Metadata
  address: "Muskegon County, MI",
  jurisdiction: "Michigan",
  role: "trial_court",

  // Connections
  judges: ["person_judicial_mcneill", "person_judicial_hoopes"],
  cases: ["2024-001507-DC", "2023-5907-PP", "2025-002760-CZ"],

  layer: 2,
  icon: "building",
};
```

### 2.8 CLAIM Nodes

```javascript
const ClaimNode = {
  id: "claim_coa_parental_alienation",
  type: "CLAIM",
  subtype: "cause_of_action",
  label: "Parental Alienation — MCL 722.23(j)",
  short_label: "Factor (j)",

  // Claim metadata
  legal_basis: "MCL 722.23(j)",
  claim_type: "cause_of_action",
  lane: "A",
  status: "active",

  // Strength metrics
  evidence_count: 2404,                // Supporting evidence
  authority_count: 12,                 // Supporting authorities
  impeachment_count: 45,              // Cross-exam ammunition
  strength_score: 0.92,               // 0-1 overall strength

  // Elements
  elements: [
    "Willingness to facilitate close relationship",
    "Pattern of interference with parenting time",
    "False allegations to limit contact",
  ],
  elements_met: 3,
  elements_total: 3,

  layer: 10,
  icon: "target",
};
```

---

## 3. Link Taxonomy — Complete Relationship Registry

Links connect nodes across and within layers. Every link has a `type`, `strength`,
and directional semantics (source → target).

```javascript
/**
 * Link schema — universal for all link types.
 */
const GraphLink = {
  id: "link_filed_by_motion_pigors",
  source: "filing_f09_coa_brief",      // Source node ID
  target: "person_plaintiff_andrew_pigors", // Target node ID
  type: "FILED_BY",                     // Relationship type
  strength: 0.8,                        // 0-1 link strength (affects force simulation)
  label: null,                          // Optional link label
  date: "2026-04-15",                  // When this relationship was established
  bidirectional: false,                // One-way or two-way
  layer: null,                          // Inherit from source node's layer
  style: "solid",                       // solid|dashed|dotted|animated
  color: null,                          // Computed from type
  width: null,                          // Computed from strength
};
```

### 3.1 Complete Link Type Registry

#### Procedural Links (Filing ↔ Person)

| Type | Direction | Meaning | Style | Color |
|------|-----------|---------|-------|-------|
| `FILED_BY` | Filing → Person | Person filed this document | solid | `#4a90d9` |
| `AGAINST` | Filing → Person | Filing targets this person | solid | `#e74c3c` |
| `REGARDING` | Filing → Person | Filing mentions this person | dashed | `#95a5a6` |
| `PRESIDES_OVER` | Person → Filing/Event | Judge presides over case | solid | `#8e44ad` |
| `ASSIGNED_TO` | Filing → Institution | Filed in this court | solid | `#3498db` |

#### Evidentiary Links (Evidence ↔ *)

| Type | Direction | Meaning | Style | Color |
|------|-----------|---------|-------|-------|
| `SUPPORTS` | Evidence → Claim/Filing | Evidence supports claim/filing | solid | `#27ae60` |
| `CONTRADICTS` | Evidence → Evidence | Two pieces of evidence conflict | animated | `#e74c3c` |
| `AUTHENTICATES` | Person → Evidence | Person can authenticate evidence | dashed | `#f39c12` |
| `CREATED_BY` | Evidence → Person | Person created/obtained this evidence | solid | `#3498db` |
| `EXHIBITS` | Filing → Evidence | Filing includes this as exhibit | solid | `#9b59b6` |

#### Relational Links (Person ↔ Person)

| Type | Direction | Meaning | Style | Color |
|------|-----------|---------|-------|-------|
| `MARRIED_TO` | Person ↔ Person | Spousal relationship | solid, thick | `#e91e63` |
| `RELATED_TO` | Person ↔ Person | Family relationship | solid | `#ff9800` |
| `LIVES_WITH` | Person ↔ Person | Cohabitation | dashed | `#ff9800` |
| `EMPLOYS` | Institution → Person | Employment relationship | solid | `#607d8b` |
| `REPRESENTS` | Person → Person | Attorney represents party | solid | `#795548` |

#### Adversarial Links (Combat Intelligence)

| Type | Direction | Meaning | Style | Color |
|------|-----------|---------|-------|-------|
| `RETALIATES` | Person → Person/Event | Retaliatory action | animated, red | `#ff0000` |
| `COORDINATES_WITH` | Person ↔ Person | Coordinated adverse action | dashed, red | `#ff4444` |
| `CONSPIRES_WITH` | Person ↔ Person | Conspiracy link | animated, red | `#cc0000` |
| `WIELDS` | Person → Weapon | Person used this weapon | solid, red | `#e74c3c` |
| `TARGETS` | Weapon → Person | Weapon was used against person | solid, red | `#c0392b` |

#### Authority Links (Legal Citations)

| Type | Direction | Meaning | Style | Color |
|------|-----------|---------|-------|-------|
| `CITES` | Filing/Claim → Authority | Document cites this authority | solid | `#2ecc71` |
| `SUPERSEDES` | Authority → Authority | Newer authority supersedes older | dashed | `#e67e22` |
| `AMENDS` | Authority → Authority | Amendment relationship | dashed | `#f1c40f` |
| `VIOLATES` | Person/Event → Authority | Action violates this rule | animated | `#e74c3c` |
| `GOVERNS` | Authority → Claim | Authority governs this claim | solid | `#1abc9c` |

#### Cartel Links (Judicial Intelligence)

| Type | Direction | Meaning | Style | Color |
|------|-----------|---------|-------|-------|
| `FORMER_PARTNER` | Person ↔ Person | Former law firm partners | thick, red | `#ff0000` |
| `SPOUSE_OF` | Person ↔ Person | Judicial spouse connection | thick, red | `#e91e63` |
| `SHARES_ADDRESS` | Person/Institution ↔ Person/Institution | Same physical address | dashed | `#ff6600` |
| `EX_PARTE_WITH` | Person → Person | Ex parte communication | animated, red | `#ff0000` |

### 3.2 Link Construction Rules

```javascript
/**
 * Link factory — creates properly typed links with computed visual properties.
 */
function createLink(source, target, type, metadata = {}) {
  const LINK_DEFAULTS = {
    // Procedural
    FILED_BY:         { strength: 0.7, color: "#4a90d9", style: "solid", width: 2 },
    AGAINST:          { strength: 0.8, color: "#e74c3c", style: "solid", width: 2 },
    REGARDING:        { strength: 0.3, color: "#95a5a6", style: "dashed", width: 1 },
    PRESIDES_OVER:    { strength: 0.9, color: "#8e44ad", style: "solid", width: 3 },
    ASSIGNED_TO:      { strength: 0.5, color: "#3498db", style: "solid", width: 1 },
    // Evidentiary
    SUPPORTS:         { strength: 0.6, color: "#27ae60", style: "solid", width: 2 },
    CONTRADICTS:      { strength: 0.9, color: "#e74c3c", style: "animated", width: 3 },
    AUTHENTICATES:    { strength: 0.4, color: "#f39c12", style: "dashed", width: 1 },
    CREATED_BY:       { strength: 0.5, color: "#3498db", style: "solid", width: 1 },
    EXHIBITS:         { strength: 0.6, color: "#9b59b6", style: "solid", width: 2 },
    // Relational
    MARRIED_TO:       { strength: 1.0, color: "#e91e63", style: "solid", width: 4 },
    RELATED_TO:       { strength: 0.8, color: "#ff9800", style: "solid", width: 3 },
    LIVES_WITH:       { strength: 0.7, color: "#ff9800", style: "dashed", width: 2 },
    EMPLOYS:          { strength: 0.5, color: "#607d8b", style: "solid", width: 1 },
    REPRESENTS:       { strength: 0.8, color: "#795548", style: "solid", width: 2 },
    // Adversarial
    RETALIATES:       { strength: 0.9, color: "#ff0000", style: "animated", width: 3 },
    COORDINATES_WITH: { strength: 0.8, color: "#ff4444", style: "dashed", width: 2 },
    CONSPIRES_WITH:   { strength: 1.0, color: "#cc0000", style: "animated", width: 4 },
    WIELDS:           { strength: 0.7, color: "#e74c3c", style: "solid", width: 2 },
    TARGETS:          { strength: 0.8, color: "#c0392b", style: "solid", width: 2 },
    // Authority
    CITES:            { strength: 0.5, color: "#2ecc71", style: "solid", width: 1 },
    SUPERSEDES:       { strength: 0.6, color: "#e67e22", style: "dashed", width: 2 },
    AMENDS:           { strength: 0.4, color: "#f1c40f", style: "dashed", width: 1 },
    VIOLATES:         { strength: 0.9, color: "#e74c3c", style: "animated", width: 3 },
    GOVERNS:          { strength: 0.6, color: "#1abc9c", style: "solid", width: 2 },
    // Cartel
    FORMER_PARTNER:   { strength: 1.0, color: "#ff0000", style: "solid", width: 5 },
    SPOUSE_OF:        { strength: 1.0, color: "#e91e63", style: "solid", width: 5 },
    SHARES_ADDRESS:   { strength: 0.7, color: "#ff6600", style: "dashed", width: 2 },
    EX_PARTE_WITH:    { strength: 0.9, color: "#ff0000", style: "animated", width: 4 },
  };

  const defaults = LINK_DEFAULTS[type] || { strength: 0.5, color: "#999", style: "solid", width: 1 };

  return {
    id: `link_${type.toLowerCase()}_${source}_${target}`,
    source,
    target,
    type,
    ...defaults,
    ...metadata,
    bidirectional: ["MARRIED_TO", "RELATED_TO", "LIVES_WITH", "COORDINATES_WITH",
                    "CONSPIRES_WITH", "FORMER_PARTNER", "SPOUSE_OF",
                    "SHARES_ADDRESS"].includes(type),
  };
}
```

---

## 4. Layer Architecture — The 13 Layers of THEMANBEARPIG

Each layer is a semantic grouping of nodes that share a conceptual domain.
Layers are NOT z-indexes — they are filter/visibility groups with independent
force simulation parameters.

### 4.1 Layer Definitions

```javascript
/**
 * LAYER_META — Master configuration for all 13 layers.
 * Each layer defines: visual properties, force parameters, data sources, and filter rules.
 */
const LAYER_META = {
  0: {
    id: 0,
    name: "CORE",
    description: "Central actors — the gravitational center of the litigation universe",
    color_primary: "#ffffff",
    color_secondary: "#e0e0e0",
    background: "radial-gradient(circle, #1a1a2e 0%, #0d0d1a 100%)",
    node_types: ["PERSON"],
    subtypes: ["plaintiff", "adversary", "child", "judicial"],
    max_nodes: 4,
    always_visible: true,
    z_order: 100,  // Highest z-order — always on top

    // Force simulation parameters
    force: {
      charge: -800,              // Strong repulsion — core actors spread wide
      charge_min_distance: 100,
      charge_max_distance: 500,
      collision_radius: 60,
      link_distance: 200,
      link_strength: 0.8,
      center_strength: 0.3,     // Strong pull to center
      radial_radius: 0,         // No radial constraint (centered)
      radial_strength: 0,
      velocity_decay: 0.4,
      alpha_decay: 0.02,
    },

    // Data source queries
    data_sources: [
      {
        table: "evidence_quotes",
        query: "SELECT DISTINCT actor FROM evidence_quotes WHERE actor IN ('Andrew Pigors', 'Emily Watson', 'Jenny McNeill')",
        node_factory: "createPersonNode",
      },
    ],
  },

  1: {
    id: 1,
    name: "ADVERSARY",
    description: "Emily's network — family members, allies, co-conspirators",
    color_primary: "#ff6b6b",
    color_secondary: "#ee5a24",
    background: "radial-gradient(circle, #2d1f1f 0%, #1a0d0d 100%)",
    node_types: ["PERSON"],
    subtypes: ["adversary", "family_member", "witness"],
    max_nodes: 20,
    always_visible: false,
    z_order: 90,

    force: {
      charge: -400,
      charge_min_distance: 50,
      charge_max_distance: 400,
      collision_radius: 40,
      link_distance: 150,
      link_strength: 0.6,
      center_strength: 0.05,
      radial_radius: 250,       // Orbit around core at 250px
      radial_strength: 0.3,
      velocity_decay: 0.4,
      alpha_decay: 0.02,
    },

    data_sources: [
      {
        table: "impeachment_matrix",
        query: "SELECT DISTINCT target AS actor FROM impeachment_matrix WHERE target LIKE '%Watson%' OR target LIKE '%Berry%'",
        node_factory: "createPersonNode",
      },
    ],
  },

  2: {
    id: 2,
    name: "JUDICIAL",
    description: "Court actors — judges, FOC, attorneys, court staff",
    color_primary: "#8e44ad",
    color_secondary: "#9b59b6",
    background: "radial-gradient(circle, #1a1a2e 0%, #0d0d1f 100%)",
    node_types: ["PERSON", "INSTITUTION"],
    subtypes: ["judicial", "agency_official", "attorney", "court"],
    max_nodes: 30,
    always_visible: false,
    z_order: 85,

    force: {
      charge: -350,
      charge_min_distance: 40,
      charge_max_distance: 350,
      collision_radius: 35,
      link_distance: 120,
      link_strength: 0.5,
      center_strength: 0.03,
      radial_radius: 350,
      radial_strength: 0.25,
      velocity_decay: 0.4,
      alpha_decay: 0.025,
    },

    data_sources: [
      {
        table: "judicial_violations",
        query: "SELECT DISTINCT judge_name AS actor FROM judicial_violations",
        node_factory: "createPersonNode",
      },
      {
        table: "berry_mcneill_intelligence",
        query: "SELECT DISTINCT entity_name AS actor FROM berry_mcneill_intelligence",
        node_factory: "createPersonNode",
      },
    ],
  },

  3: {
    id: 3,
    name: "EVIDENCE",
    description: "Document and recording nodes — the proof layer",
    color_primary: "#3498db",
    color_secondary: "#2980b9",
    background: "radial-gradient(circle, #0d1f2d 0%, #061018 100%)",
    node_types: ["EVIDENCE"],
    subtypes: ["document", "recording", "police_report", "court_order",
               "communication", "photo", "video", "medical_record", "financial_record"],
    max_nodes: 500,
    always_visible: false,
    z_order: 70,

    force: {
      charge: -100,             // Light repulsion — many nodes, keep compact
      charge_min_distance: 20,
      charge_max_distance: 200,
      collision_radius: 15,
      link_distance: 80,
      link_strength: 0.3,
      center_strength: 0.01,
      radial_radius: 500,
      radial_strength: 0.15,
      velocity_decay: 0.5,
      alpha_decay: 0.03,
    },

    data_sources: [
      {
        table: "evidence_quotes",
        query: `SELECT source_file, category, lane,
                       COUNT(*) as quote_count,
                       MAX(CAST(relevance_score AS REAL)) as max_relevance
                FROM evidence_quotes
                WHERE is_duplicate = 0
                GROUP BY source_file
                ORDER BY quote_count DESC
                LIMIT 500`,
        node_factory: "createEvidenceNode",
      },
    ],
  },

  4: {
    id: 4,
    name: "AUTHORITY",
    description: "Legal citations and rules — the weapons of law",
    color_primary: "#2ecc71",
    color_secondary: "#27ae60",
    background: "radial-gradient(circle, #0d2d1f 0%, #061810 100%)",
    node_types: ["AUTHORITY"],
    subtypes: ["statute", "court_rule", "case_law", "constitutional", "federal_statute"],
    max_nodes: 200,
    always_visible: false,
    z_order: 65,

    force: {
      charge: -150,
      charge_min_distance: 25,
      charge_max_distance: 250,
      collision_radius: 20,
      link_distance: 100,
      link_strength: 0.4,
      center_strength: 0.02,
      radial_radius: 550,
      radial_strength: 0.2,
      velocity_decay: 0.45,
      alpha_decay: 0.025,
    },

    data_sources: [
      {
        table: "authority_chains_v2",
        query: `SELECT primary_citation, supporting_citation, relationship,
                       source_type, lane, COUNT(*) as chain_count
                FROM authority_chains_v2
                GROUP BY primary_citation
                ORDER BY chain_count DESC
                LIMIT 200`,
        node_factory: "createAuthorityNode",
      },
    ],
  },

  5: {
    id: 5,
    name: "FILING",
    description: "Filing pipeline F1-F10 — the actionable output layer",
    color_primary: "#e67e22",
    color_secondary: "#d35400",
    background: "radial-gradient(circle, #2d1f0d 0%, #180d06 100%)",
    node_types: ["FILING"],
    subtypes: ["motion", "brief", "complaint", "petition", "affidavit",
               "exhibit", "proposed_order", "certificate_of_service"],
    max_nodes: 50,
    always_visible: false,
    z_order: 75,

    force: {
      charge: -250,
      charge_min_distance: 30,
      charge_max_distance: 300,
      collision_radius: 30,
      link_distance: 130,
      link_strength: 0.5,
      center_strength: 0.02,
      radial_radius: 400,
      radial_strength: 0.2,
      velocity_decay: 0.4,
      alpha_decay: 0.02,
    },

    data_sources: [
      {
        table: "filing_readiness",
        query: "SELECT * FROM filing_readiness ORDER BY confidence DESC",
        node_factory: "createFilingNode",
      },
    ],
  },

  6: {
    id: 6,
    name: "TIMELINE",
    description: "Chronological event nodes — the temporal spine",
    color_primary: "#f1c40f",
    color_secondary: "#f39c12",
    background: "radial-gradient(circle, #2d2d0d 0%, #181806 100%)",
    node_types: ["EVENT"],
    subtypes: ["hearing", "order_entered", "violation", "incident",
               "contact", "withholding", "arrest", "filing_event"],
    max_nodes: 300,
    always_visible: false,
    z_order: 60,

    force: {
      charge: -80,
      charge_min_distance: 15,
      charge_max_distance: 180,
      collision_radius: 12,
      link_distance: 60,
      link_strength: 0.2,
      center_strength: 0.01,
      radial_radius: 600,
      radial_strength: 0.15,
      velocity_decay: 0.5,
      alpha_decay: 0.03,
      // Timeline uses x-axis for temporal ordering
      temporal_force: true,
      temporal_scale: "linear",   // linear|log
      temporal_strength: 0.8,
    },

    data_sources: [
      {
        table: "timeline_events",
        query: `SELECT event_date, event_text, category, lane, actor
                FROM timeline_events
                WHERE event_date IS NOT NULL
                ORDER BY event_date DESC
                LIMIT 300`,
        node_factory: "createEventNode",
      },
    ],
  },

  7: {
    id: 7,
    name: "WEAPON",
    description: "Weaponized legal instruments — false allegations, PPO abuse, contempt",
    color_primary: "#e74c3c",
    color_secondary: "#c0392b",
    background: "radial-gradient(circle, #2d0d0d 0%, #180606 100%)",
    node_types: ["WEAPON"],
    subtypes: ["false_allegation", "ppo_weaponization", "contempt_abuse",
               "evidence_suppression", "ex_parte_abuse", "medication_coercion",
               "incarceration_weapon"],
    max_nodes: 50,
    always_visible: false,
    z_order: 80,

    force: {
      charge: -300,
      charge_min_distance: 40,
      charge_max_distance: 350,
      collision_radius: 35,
      link_distance: 140,
      link_strength: 0.6,
      center_strength: 0.02,
      radial_radius: 300,
      radial_strength: 0.25,
      velocity_decay: 0.35,
      alpha_decay: 0.02,
    },

    data_sources: [
      {
        table: "impeachment_matrix",
        query: `SELECT category, evidence_summary, impeachment_value,
                       cross_exam_question, filing_relevance
                FROM impeachment_matrix
                WHERE impeachment_value >= 7
                ORDER BY impeachment_value DESC
                LIMIT 50`,
        node_factory: "createWeaponNode",
      },
    ],
  },

  8: {
    id: 8,
    name: "CARTEL",
    description: "Judicial cartel connections — McNeill/Hoopes/Ladas-Hoopes triangle",
    color_primary: "#ff0000",
    color_secondary: "#cc0000",
    background: "radial-gradient(circle, #2d0000 0%, #1a0000 100%)",
    node_types: ["PERSON", "INSTITUTION"],
    subtypes: ["judicial", "agency_official", "court", "law_firm"],
    max_nodes: 15,
    always_visible: false,
    z_order: 95,

    force: {
      charge: -500,
      charge_min_distance: 60,
      charge_max_distance: 400,
      collision_radius: 50,
      link_distance: 180,
      link_strength: 0.9,       // Tight coupling — cartel sticks together
      center_strength: 0.05,
      radial_radius: 200,
      radial_strength: 0.3,
      velocity_decay: 0.3,
      alpha_decay: 0.015,
    },

    data_sources: [
      {
        table: "berry_mcneill_intelligence",
        query: "SELECT * FROM berry_mcneill_intelligence ORDER BY created_at DESC",
        node_factory: "createCartelNode",
      },
    ],
  },

  9: {
    id: 9,
    name: "IMPEACHMENT",
    description: "Credibility attack chains — contradictions, lies, perjury",
    color_primary: "#e91e63",
    color_secondary: "#c2185b",
    background: "radial-gradient(circle, #2d0d1a 0%, #18060d 100%)",
    node_types: ["EVIDENCE", "WEAPON"],
    subtypes: ["contradiction", "impeachment_chain", "credibility_attack"],
    max_nodes: 100,
    always_visible: false,
    z_order: 78,

    force: {
      charge: -200,
      charge_min_distance: 25,
      charge_max_distance: 250,
      collision_radius: 22,
      link_distance: 100,
      link_strength: 0.5,
      center_strength: 0.02,
      radial_radius: 450,
      radial_strength: 0.2,
      velocity_decay: 0.45,
      alpha_decay: 0.025,
    },

    data_sources: [
      {
        table: "contradiction_map",
        query: `SELECT claim_id, source_a, source_b, contradiction_text, severity, lane
                FROM contradiction_map
                ORDER BY severity DESC
                LIMIT 100`,
        node_factory: "createImpeachmentNode",
      },
    ],
  },

  10: {
    id: 10,
    name: "CLAIM",
    description: "Causes of action — the 27 COAs across all lanes",
    color_primary: "#00bcd4",
    color_secondary: "#0097a7",
    background: "radial-gradient(circle, #0d2d2d 0%, #061818 100%)",
    node_types: ["CLAIM"],
    subtypes: ["cause_of_action", "defense", "counterclaim", "affirmative_defense"],
    max_nodes: 40,
    always_visible: false,
    z_order: 72,

    force: {
      charge: -250,
      charge_min_distance: 30,
      charge_max_distance: 300,
      collision_radius: 28,
      link_distance: 120,
      link_strength: 0.4,
      center_strength: 0.02,
      radial_radius: 500,
      radial_strength: 0.2,
      velocity_decay: 0.4,
      alpha_decay: 0.02,
    },

    data_sources: [
      {
        table: "claims",
        query: "SELECT * FROM claims WHERE status = 'active' ORDER BY strength_score DESC",
        node_factory: "createClaimNode",
      },
    ],
  },

  11: {
    id: 11,
    name: "EMERGENCE",
    description: "Auto-discovered cross-layer connections — DBSCAN clusters, novelty signals",
    color_primary: "#00e676",
    color_secondary: "#00c853",
    background: "radial-gradient(circle, #0d2d0d 0%, #061806 100%)",
    node_types: ["EVIDENCE", "PERSON", "EVENT"],
    subtypes: ["emergence_cluster", "novelty_signal", "gap_indicator"],
    max_nodes: 50,
    always_visible: false,
    z_order: 55,

    force: {
      charge: -120,
      charge_min_distance: 20,
      charge_max_distance: 200,
      collision_radius: 18,
      link_distance: 90,
      link_strength: 0.3,
      center_strength: 0.01,
      radial_radius: 650,
      radial_strength: 0.1,
      velocity_decay: 0.5,
      alpha_decay: 0.03,
    },

    data_sources: [],  // Computed from cross-layer analysis, not direct DB query
  },

  12: {
    id: 12,
    name: "PREDICTION",
    description: "Adversary behavior forecasts — escalation, retaliation, timing",
    color_primary: "#ff9100",
    color_secondary: "#ff6d00",
    background: "radial-gradient(circle, #2d1a0d 0%, #180d06 100%)",
    node_types: ["EVENT"],
    subtypes: ["prediction", "forecast", "counter_strategy"],
    max_nodes: 20,
    always_visible: false,
    z_order: 50,

    force: {
      charge: -200,
      charge_min_distance: 30,
      charge_max_distance: 250,
      collision_radius: 25,
      link_distance: 110,
      link_strength: 0.4,
      center_strength: 0.01,
      radial_radius: 700,
      radial_strength: 0.1,
      velocity_decay: 0.45,
      alpha_decay: 0.025,
    },

    data_sources: [],  // Computed from temporal pattern analysis
  },
};
```

### 4.2 Layer Interaction Rules

```javascript
/**
 * Cross-layer link rules — which layers can connect to which.
 * This prevents visual spaghetti by restricting link routing.
 */
const LAYER_CONNECTIONS = {
  //        0  1  2  3  4  5  6  7  8  9  10 11 12
  /* 0 */  [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],  // CORE connects to all
  /* 1 */  [1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1],  // ADVERSARY
  /* 2 */  [1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 0, 0],  // JUDICIAL
  /* 3 */  [1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0],  // EVIDENCE
  /* 4 */  [1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0],  // AUTHORITY
  /* 5 */  [1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0],  // FILING
  /* 6 */  [1, 1, 1, 1, 0, 1, 1, 1, 0, 0, 0, 1, 1],  // TIMELINE
  /* 7 */  [1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 0, 0],  // WEAPON
  /* 8 */  [1, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0],  // CARTEL
  /* 9 */  [1, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0],  // IMPEACHMENT
  /*10 */  [1, 0, 1, 1, 1, 1, 0, 1, 0, 0, 1, 0, 0],  // CLAIM
  /*11 */  [1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1],  // EMERGENCE
  /*12 */  [1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1],  // PREDICTION
};

/**
 * Check if a link between two layers is permitted.
 */
function canConnect(sourceLayer, targetLayer) {
  return LAYER_CONNECTIONS[sourceLayer][targetLayer] === 1;
}
```

---

## 5. Graph Construction from Database

THEMANBEARPIG builds its graph entirely from `litigation_context.db`. No hardcoded data
beyond the CORE_PERSONS registry. This section defines the complete data pipeline.

### 5.1 Master Build Pipeline

```python
"""
THEMANBEARPIG Graph Builder — Master Pipeline
Reads from litigation_context.db, produces JSON graph for D3.js.

Usage:
    python mbp_graph_builder.py --output build/mbp_graph.json
"""

import sqlite3
import json
import hashlib
from pathlib import Path
from datetime import date

DB_PATH = Path(r"C:\Users\andre\LitigationOS\litigation_context.db")

def connect():
    """Open WAL connection with optimal PRAGMAs."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA cache_size = -32000")
    conn.execute("PRAGMA temp_store = MEMORY")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def stable_id(*parts):
    """Generate a deterministic node ID from parts."""
    raw = "_".join(str(p).lower().replace(" ", "_") for p in parts)
    return raw[:80]  # Cap length for readability


def build_person_nodes(conn):
    """Build PERSON nodes from multiple source tables."""
    persons = {}

    # 1. Core persons (always present)
    for p in CORE_PERSONS:
        persons[p["id"]] = p

    # 2. From evidence_quotes — extract unique actors
    rows = conn.execute("""
        SELECT actor, lane, COUNT(*) as cnt
        FROM evidence_quotes
        WHERE actor IS NOT NULL AND actor != ''
        GROUP BY actor, lane
        ORDER BY cnt DESC
        LIMIT 100
    """).fetchall()

    for r in rows:
        pid = stable_id("person", "witness", r["actor"])
        if pid not in persons:
            persons[pid] = {
                "id": pid,
                "type": "PERSON",
                "subtype": "witness",
                "label": r["actor"],
                "short_label": r["actor"].split()[-1] if r["actor"] else "Unknown",
                "alignment": "unknown",
                "threat_level": 3,
                "evidence_count": r["cnt"],
                "layer": 1 if r["lane"] in ("A", "D") else 2,
                "case_lanes": [r["lane"]] if r["lane"] else [],
            }
        else:
            persons[pid]["evidence_count"] = persons[pid].get("evidence_count", 0) + r["cnt"]

    # 3. From impeachment_matrix — adversary targets
    rows = conn.execute("""
        SELECT target, COUNT(*) as cnt, MAX(impeachment_value) as max_imp
        FROM impeachment_matrix
        WHERE target IS NOT NULL
        GROUP BY target
        ORDER BY cnt DESC
    """).fetchall()

    for r in rows:
        pid = stable_id("person", "adversary", r["target"])
        if pid in persons:
            persons[pid]["impeachment_count"] = r["cnt"]
            persons[pid]["threat_level"] = min(10, max(
                persons[pid].get("threat_level", 0),
                int(r["max_imp"] or 0)
            ))
        # New persons from impeachment are already captured as CORE_PERSONS

    # 4. From judicial_violations — judges
    rows = conn.execute("""
        SELECT judge_name, COUNT(*) as cnt
        FROM judicial_violations
        WHERE judge_name IS NOT NULL
        GROUP BY judge_name
    """).fetchall()

    for r in rows:
        pid = stable_id("person", "judicial", r["judge_name"])
        if pid in persons:
            persons[pid]["violation_count"] = r["cnt"]

    return list(persons.values())


def build_evidence_nodes(conn):
    """Build EVIDENCE nodes from evidence_quotes grouped by source_file."""
    rows = conn.execute("""
        SELECT source_file, category, lane,
               COUNT(*) as quote_count,
               MAX(CAST(relevance_score AS REAL)) as max_relevance,
               MIN(event_date) as earliest_date
        FROM evidence_quotes
        WHERE source_file IS NOT NULL AND is_duplicate = 0
        GROUP BY source_file
        HAVING quote_count >= 2
        ORDER BY quote_count DESC
        LIMIT 500
    """).fetchall()

    nodes = []
    for r in rows:
        eid = stable_id("evidence", r["category"] or "doc", r["source_file"])
        fname = Path(r["source_file"]).name if r["source_file"] else "Unknown"
        nodes.append({
            "id": eid,
            "type": "EVIDENCE",
            "subtype": classify_evidence_subtype(fname),
            "label": fname[:50],
            "short_label": fname[:20],
            "source_file": r["source_file"],
            "category": r["category"],
            "lane": r["lane"],
            "relevance_score": r["max_relevance"] or 0.5,
            "quote_count": r["quote_count"],
            "date": r["earliest_date"],
            "layer": 3,
        })
    return nodes


def classify_evidence_subtype(filename):
    """Classify evidence subtype from filename."""
    fn = filename.lower()
    if any(x in fn for x in ["nspd", "police", "incident"]):
        return "police_report"
    if any(x in fn for x in [".mp3", ".wav", ".m4a", "audio", "recording"]):
        return "recording"
    if any(x in fn for x in [".mp4", ".mov", ".avi", "video"]):
        return "video"
    if any(x in fn for x in [".jpg", ".png", ".jpeg", "photo", "screenshot"]):
        return "photo"
    if any(x in fn for x in ["order", "judgment", "ruling"]):
        return "court_order"
    if any(x in fn for x in ["appclose", "email", "message", "text"]):
        return "communication"
    if any(x in fn for x in ["medical", "health", "eval"]):
        return "medical_record"
    return "document"


def build_authority_nodes(conn):
    """Build AUTHORITY nodes from authority_chains_v2."""
    rows = conn.execute("""
        SELECT primary_citation, source_type, lane,
               COUNT(*) as chain_count
        FROM authority_chains_v2
        WHERE primary_citation IS NOT NULL
        GROUP BY primary_citation
        ORDER BY chain_count DESC
        LIMIT 200
    """).fetchall()

    nodes = []
    for r in rows:
        aid = stable_id("authority", r["source_type"] or "rule", r["primary_citation"])
        citation = r["primary_citation"]
        nodes.append({
            "id": aid,
            "type": "AUTHORITY",
            "subtype": classify_authority_subtype(citation),
            "label": citation[:50],
            "short_label": citation[:20],
            "citation": citation,
            "source_type": r["source_type"],
            "lane": r["lane"],
            "chain_count": r["chain_count"],
            "layer": 4,
        })
    return nodes


def classify_authority_subtype(citation):
    """Classify authority subtype from citation text."""
    c = citation.upper()
    if "MCR" in c:
        return "court_rule"
    if "MCL" in c:
        return "statute"
    if "USC" in c or "FRCP" in c:
        return "federal_statute"
    if "CONST" in c or "AMEND" in c:
        return "constitutional"
    if " V " in c or " V. " in c:
        return "case_law"
    return "statute"


def build_event_nodes(conn):
    """Build EVENT nodes from timeline_events."""
    rows = conn.execute("""
        SELECT event_date, event_text, category, lane, actor
        FROM timeline_events
        WHERE event_date IS NOT NULL AND event_text IS NOT NULL
        ORDER BY event_date DESC
        LIMIT 300
    """).fetchall()

    nodes = []
    for r in rows:
        eid = stable_id("event", r["category"] or "generic",
                        r["event_date"], r["event_text"][:30])
        nodes.append({
            "id": eid,
            "type": "EVENT",
            "subtype": classify_event_subtype(r["category"]),
            "label": (r["event_text"] or "")[:60],
            "short_label": (r["event_text"] or "")[:25],
            "date": r["event_date"],
            "category": r["category"],
            "lane": r["lane"],
            "actor": r["actor"],
            "layer": 6,
        })
    return nodes


def classify_event_subtype(category):
    """Map timeline category to event subtype."""
    mapping = {
        "hearing": "hearing",
        "order": "order_entered",
        "violation": "violation",
        "incident": "incident",
        "contact": "contact",
        "withholding": "withholding",
        "arrest": "arrest",
        "filing": "filing_event",
    }
    return mapping.get((category or "").lower(), "incident")


def build_weapon_nodes(conn):
    """Build WEAPON nodes from impeachment_matrix (high-severity)."""
    rows = conn.execute("""
        SELECT category, evidence_summary, impeachment_value,
               cross_exam_question, filing_relevance, event_date
        FROM impeachment_matrix
        WHERE impeachment_value >= 7
        ORDER BY impeachment_value DESC
        LIMIT 50
    """).fetchall()

    nodes = []
    for r in rows:
        wid = stable_id("weapon", r["category"] or "unknown",
                        (r["evidence_summary"] or "")[:30])
        nodes.append({
            "id": wid,
            "type": "WEAPON",
            "subtype": classify_weapon_subtype(r["category"]),
            "label": (r["evidence_summary"] or "")[:60],
            "short_label": (r["category"] or "Unknown")[:25],
            "category": r["category"],
            "severity": r["impeachment_value"] or 5,
            "cross_exam_question": r["cross_exam_question"],
            "filing_relevance": r["filing_relevance"],
            "date": r["event_date"],
            "layer": 7,
        })
    return nodes


def classify_weapon_subtype(category):
    """Map impeachment category to weapon subtype."""
    cat = (category or "").lower()
    if "false" in cat or "allegation" in cat:
        return "false_allegation"
    if "ppo" in cat or "protection" in cat:
        return "ppo_weaponization"
    if "contempt" in cat or "jail" in cat:
        return "contempt_abuse"
    if "evidence" in cat or "suppress" in cat or "exclud" in cat:
        return "evidence_suppression"
    if "ex parte" in cat:
        return "ex_parte_abuse"
    if "medic" in cat or "prescription" in cat:
        return "medication_coercion"
    return "false_allegation"


def build_links(conn, nodes):
    """Build links from relationships in the database."""
    links = []
    node_ids = {n["id"] for n in nodes}

    # 1. CONTRADICTS links from contradiction_map
    rows = conn.execute("""
        SELECT source_a, source_b, contradiction_text, severity, lane
        FROM contradiction_map
        WHERE source_a IS NOT NULL AND source_b IS NOT NULL
        LIMIT 200
    """).fetchall()

    for r in rows:
        sid = stable_id("evidence", "doc", r["source_a"])
        tid = stable_id("evidence", "doc", r["source_b"])
        if sid in node_ids and tid in node_ids:
            links.append({
                "source": sid,
                "target": tid,
                "type": "CONTRADICTS",
                "strength": min(1.0, (r["severity"] or 5) / 10.0),
                "label": (r["contradiction_text"] or "")[:40],
                "style": "animated",
                "color": "#e74c3c",
                "width": max(1, (r["severity"] or 5) // 2),
            })

    # 2. VIOLATES links from judicial_violations
    rows = conn.execute("""
        SELECT judge_name, violation_type, COUNT(*) as cnt
        FROM judicial_violations
        WHERE judge_name IS NOT NULL
        GROUP BY judge_name, violation_type
        LIMIT 100
    """).fetchall()

    for r in rows:
        sid = stable_id("person", "judicial", r["judge_name"])
        tid = stable_id("weapon", r["violation_type"] or "violation",
                        r["judge_name"][:20])
        if sid in node_ids:
            links.append({
                "source": sid,
                "target": tid,
                "type": "VIOLATES",
                "strength": min(1.0, r["cnt"] / 100.0),
                "style": "animated",
                "color": "#e74c3c",
                "width": min(5, max(1, r["cnt"] // 20)),
            })

    # 3. CITES links from authority_chains_v2
    rows = conn.execute("""
        SELECT primary_citation, supporting_citation, relationship, lane
        FROM authority_chains_v2
        WHERE primary_citation IS NOT NULL AND supporting_citation IS NOT NULL
        GROUP BY primary_citation, supporting_citation
        LIMIT 300
    """).fetchall()

    for r in rows:
        sid = stable_id("authority", "rule", r["primary_citation"])
        tid = stable_id("authority", "rule", r["supporting_citation"])
        if sid in node_ids and tid in node_ids and sid != tid:
            links.append({
                "source": sid,
                "target": tid,
                "type": "CITES",
                "strength": 0.5,
                "style": "solid",
                "color": "#2ecc71",
                "width": 1,
            })

    # 4. CARTEL links (hardcoded — these are verified facts)
    cartel_links = [
        ("person_judicial_mcneill", "person_family_cavan_berry", "SPOUSE_OF"),
        ("person_judicial_mcneill", "person_judicial_hoopes", "FORMER_PARTNER"),
        ("person_judicial_mcneill", "person_judicial_ladas_hoopes", "FORMER_PARTNER"),
        ("person_judicial_hoopes", "person_judicial_ladas_hoopes", "MARRIED_TO"),
        ("person_family_cavan_berry", "person_agency_rusco", "SHARES_ADDRESS"),
        ("person_family_ronald_berry", "person_family_cavan_berry", "RELATED_TO"),
        ("person_family_ronald_berry", "person_adversary_emily_watson", "LIVES_WITH"),
        ("person_adversary_emily_watson", "person_family_albert_watson", "RELATED_TO"),
        ("person_adversary_emily_watson", "person_family_lori_watson", "RELATED_TO"),
    ]

    for src, tgt, ltype in cartel_links:
        if src in node_ids and tgt in node_ids:
            links.append({
                "source": src,
                "target": tgt,
                "type": ltype,
                **LINK_DEFAULTS.get(ltype, {}),
            })

    return links


def build_graph():
    """Master graph builder — produces complete D3.js-ready JSON."""
    conn = connect()

    # Build all node types
    persons = build_person_nodes(conn)
    evidence = build_evidence_nodes(conn)
    authorities = build_authority_nodes(conn)
    events = build_event_nodes(conn)
    weapons = build_weapon_nodes(conn)

    all_nodes = persons + evidence + authorities + events + weapons

    # Deduplicate by ID
    seen = set()
    unique_nodes = []
    for n in all_nodes:
        if n["id"] not in seen:
            seen.add(n["id"])
            unique_nodes.append(n)

    # Build links
    links = build_links(conn, unique_nodes)

    # Compute visual properties
    for node in unique_nodes:
        compute_node_visuals(node)

    # Compute separation counter dynamically
    sep_date = date(2025, 7, 29)
    sep_days = (date.today() - sep_date).days

    graph = {
        "metadata": {
            "generated": date.today().isoformat(),
            "node_count": len(unique_nodes),
            "link_count": len(links),
            "layer_count": 13,
            "separation_days": sep_days,
            "version": "1.0.0",
        },
        "nodes": unique_nodes,
        "links": links,
        "layers": LAYER_META,
    }

    conn.close()
    return graph
```

---

## 6. Node Sizing and Coloring Rules

Node visual properties are COMPUTED, never hardcoded. The computation depends on
the node type and its associated metrics.

### 6.1 Sizing Rules

```javascript
/**
 * Compute node radius based on type-specific metrics.
 * Returns radius in pixels (min 8, max 60).
 */
function computeRadius(node) {
  const MIN_RADIUS = 8;
  const MAX_RADIUS = 60;

  let raw;
  switch (node.type) {
    case "PERSON":
      // Threat level (0-10) is the primary driver
      // Evidence count adds secondary scaling
      raw = 15 + (node.threat_level || 0) * 3
            + Math.log2(1 + (node.evidence_count || 0)) * 2;
      break;

    case "EVIDENCE":
      // Relevance score (0-1) and quote count
      raw = 10 + (node.relevance_score || 0.5) * 15
            + Math.log2(1 + (node.quote_count || 0)) * 3;
      // Smoking guns get 50% boost
      if (node.is_smoking_gun) raw *= 1.5;
      break;

    case "AUTHORITY":
      // Chain count = how many things cite this authority
      raw = 10 + Math.log2(1 + (node.chain_count || 0)) * 5;
      break;

    case "FILING":
      // Readiness score (0-1) determines size
      raw = 15 + (node.readiness_score || 0) * 25;
      break;

    case "EVENT":
      // Significance (1-10)
      raw = 8 + (node.significance || 5) * 3;
      break;

    case "WEAPON":
      // Severity (1-10) with emphasis on high-severity weapons
      raw = 12 + (node.severity || 5) * 4;
      break;

    case "INSTITUTION":
      raw = 20;  // Fixed size for institutions
      break;

    case "CLAIM":
      // Strength score (0-1)
      raw = 12 + (node.strength_score || 0.5) * 30;
      break;

    default:
      raw = 12;
  }

  return Math.max(MIN_RADIUS, Math.min(MAX_RADIUS, raw));
}
```

### 6.2 Coloring Rules

```javascript
/**
 * Color palette by node type and classification.
 */
const COLOR_PALETTE = {
  PERSON: {
    allied:    "#4fc3f7",    // Bright blue — friendly
    adverse:   "#ef5350",    // Red — adversary
    neutral:   "#bdbdbd",    // Gray — neutral
    protected: "#ffd54f",    // Gold — child (special)
    unknown:   "#78909c",    // Blue-gray
  },
  EVIDENCE: {
    police_report:   "#42a5f5",
    recording:       "#ab47bc",
    court_order:     "#5c6bc0",
    communication:   "#26a69a",
    photo:           "#66bb6a",
    video:           "#ab47bc",
    medical_record:  "#ec407a",
    financial_record:"#ffa726",
    document:        "#78909c",
  },
  AUTHORITY: {
    statute:          "#66bb6a",
    court_rule:       "#4db6ac",
    case_law:         "#81c784",
    constitutional:   "#aed581",
    federal_statute:  "#4dd0e1",
  },
  FILING: {
    DRAFT:          "#78909c",
    QA_REVIEW:      "#ffa726",
    SERVICE_READY:  "#66bb6a",
    FILED:          "#42a5f5",
    DOCKETED:       "#7e57c2",
    MONITORING:     "#26a69a",
  },
  EVENT: {
    favorable: "#66bb6a",
    adverse:   "#ef5350",
    neutral:   "#bdbdbd",
    mixed:     "#ffa726",
  },
  WEAPON: {
    low:    "#ff8a65",       // 1-3 severity
    medium: "#ef5350",       // 4-6 severity
    high:   "#d32f2f",       // 7-8 severity
    critical:"#b71c1c",      // 9-10 severity
  },
  INSTITUTION: {
    court:                 "#5c6bc0",
    agency:                "#7e57c2",
    law_firm:              "#8d6e63",
    law_enforcement_agency:"#546e7a",
  },
  CLAIM: {
    active:   "#4dd0e1",
    pending:  "#ffa726",
    dismissed:"#78909c",
  },
};


/**
 * Compute node color from type + classification.
 */
function computeColor(node) {
  const palette = COLOR_PALETTE[node.type];
  if (!palette) return "#78909c";

  switch (node.type) {
    case "PERSON":
      return palette[node.alignment] || palette.unknown;
    case "EVIDENCE":
      return palette[node.subtype] || palette.document;
    case "AUTHORITY":
      return palette[node.subtype] || palette.statute;
    case "FILING":
      return palette[node.status] || palette.DRAFT;
    case "EVENT":
      return palette[node.outcome] || palette.neutral;
    case "WEAPON": {
      const sev = node.severity || 5;
      if (sev >= 9) return palette.critical;
      if (sev >= 7) return palette.high;
      if (sev >= 4) return palette.medium;
      return palette.low;
    }
    case "INSTITUTION":
      return palette[node.subtype] || palette.court;
    case "CLAIM":
      return palette[node.status] || palette.active;
    default:
      return "#78909c";
  }
}


/**
 * Compute all visual properties for a node.
 */
function computeNodeVisuals(node) {
  node.radius = computeRadius(node);
  node.color = computeColor(node);

  // Glow effect for high-threat persons and smoking-gun evidence
  node.glow = (node.type === "PERSON" && (node.threat_level || 0) >= 8)
           || (node.type === "EVIDENCE" && node.is_smoking_gun)
           || (node.type === "WEAPON" && (node.severity || 0) >= 9);

  // Pulse animation for urgent items
  node.pulse = (node.type === "FILING" && node.urgency === "CRITICAL")
            || (node.type === "WEAPON" && (node.severity || 0) >= 8);

  // Opacity based on relevance (evidence nodes only)
  if (node.type === "EVIDENCE") {
    node.opacity = 0.4 + (node.relevance_score || 0.5) * 0.6;
  } else {
    node.opacity = 1.0;
  }
}
```

---

## 7. Performance Constraints and Optimization

THEMANBEARPIG must render 2,500+ nodes at 30+ FPS on modest hardware
(AMD Ryzen 3 3200G, 24GB RAM, Vega 8 integrated GPU). This demands aggressive
optimization at every layer.

### 7.1 Level of Detail (LOD) Rendering

```javascript
/**
 * LOD system — reduce rendering complexity based on zoom level.
 *
 * Zoom Level  | Node Rendering        | Link Rendering      | Labels
 * ------------|----------------------|--------------------|---------
 * < 0.3       | Circles only (no icon)| Hidden             | Hidden
 * 0.3 - 0.6   | Circles + color       | Major links only   | Core only
 * 0.6 - 1.0   | Full icons            | All visible links  | Layer names
 * 1.0 - 2.0   | Icons + metrics       | All + animated     | Node labels
 * > 2.0       | Full detail + tooltips| All + labels       | Full text
 */
const LOD_THRESHOLDS = {
  MINIMAL:      0.3,    // Below this: dots only
  LOW:          0.6,    // Circles with color
  MEDIUM:       1.0,    // Full node rendering
  HIGH:         2.0,    // Detailed rendering
  ULTRA:        3.0,    // Maximum detail
};

function getLODLevel(zoomScale) {
  if (zoomScale < LOD_THRESHOLDS.MINIMAL) return "MINIMAL";
  if (zoomScale < LOD_THRESHOLDS.LOW) return "LOW";
  if (zoomScale < LOD_THRESHOLDS.MEDIUM) return "MEDIUM";
  if (zoomScale < LOD_THRESHOLDS.HIGH) return "HIGH";
  return "ULTRA";
}

function shouldRenderLabel(node, lod) {
  switch (lod) {
    case "MINIMAL": return false;
    case "LOW":     return node.layer === 0;  // Core actors only
    case "MEDIUM":  return node.type === "PERSON" || node.type === "FILING";
    case "HIGH":    return true;
    case "ULTRA":   return true;
    default:        return false;
  }
}

function shouldRenderIcon(node, lod) {
  switch (lod) {
    case "MINIMAL": return false;
    case "LOW":     return false;
    case "MEDIUM":  return true;
    case "HIGH":    return true;
    case "ULTRA":   return true;
    default:        return false;
  }
}
```

### 7.2 Viewport Culling with Quadtree

```javascript
/**
 * Quadtree-based viewport culling.
 * Only render nodes within the visible viewport + margin.
 * D3's built-in d3.quadtree handles spatial indexing.
 */
function getVisibleNodes(nodes, viewport, margin = 100) {
  const { x, y, width, height } = viewport;
  const left   = x - margin;
  const right  = x + width + margin;
  const top    = y - margin;
  const bottom = y + height + margin;

  return nodes.filter(n =>
    n.x >= left && n.x <= right &&
    n.y >= top  && n.y <= bottom
  );
}

/**
 * For link culling: only render links where at least one endpoint is visible.
 */
function getVisibleLinks(links, visibleNodeIds) {
  const idSet = new Set(visibleNodeIds);
  return links.filter(l =>
    idSet.has(typeof l.source === "object" ? l.source.id : l.source) ||
    idSet.has(typeof l.target === "object" ? l.target.id : l.target)
  );
}
```

### 7.3 Canvas vs SVG Decision Matrix

```
NODE COUNT     RENDERER        REASON
< 500          SVG             DOM events, CSS styling, accessibility
500 - 2000     Canvas          Performance, still interactive via hit detection
2000 - 5000    Canvas + WebGL  GPU-accelerated rendering
> 5000         WebGL (PixiJS)  Full GPU, instanced rendering
```

```javascript
/**
 * Renderer selection based on node count.
 */
function selectRenderer(nodeCount) {
  if (nodeCount < 500)  return "svg";
  if (nodeCount < 2000) return "canvas";
  if (nodeCount < 5000) return "canvas-webgl";
  return "webgl";
}
```

### 7.4 Force Simulation Performance

```javascript
/**
 * Force simulation optimization for 2500+ nodes.
 *
 * Key optimizations:
 * 1. Barnes-Hut approximation (theta = 0.9) for charge forces
 * 2. Warm start — don't reset alpha on data updates
 * 3. Adaptive alpha decay — faster decay when layout stabilizes
 * 4. Worker thread for simulation (Web Worker)
 */
const SIMULATION_CONFIG = {
  // Barnes-Hut theta — higher = faster but less accurate
  // 0.9 is good for 2500+ nodes
  theta: 0.9,

  // Alpha parameters
  alpha_start: 1.0,
  alpha_min: 0.001,
  alpha_decay: 0.0228,        // Default D3 value
  alpha_target: 0,

  // Velocity decay — how quickly nodes slow down
  velocity_decay: 0.4,

  // Iteration budget per frame
  iterations_per_tick: 1,      // Keep at 1 for 60fps

  // Web Worker offloading
  use_worker: true,            // Offload simulation to worker thread
  worker_tick_rate: 16,        // ~60fps in worker

  // Warm restart on data change
  warm_restart_alpha: 0.3,    // Don't fully restart — just nudge
};
```

### 7.5 Memory Budget

```
COMPONENT          ESTIMATED SIZE     NOTES
2500 nodes         ~2.5 MB            ~1KB per node (properties + D3 internals)
5000 links         ~2.0 MB            ~400 bytes per link
Quadtree           ~1.0 MB            Spatial index
Canvas buffer      ~8.0 MB            1920x1080 @ 32bpp double-buffered
D3 simulation      ~3.0 MB            Force calculation state
Total              ~16.5 MB           Well within 24GB system RAM
```

---

## 8. Data Refresh Protocol

The graph should support incremental updates without full rebuild.

### 8.1 Incremental Update Strategy

```javascript
/**
 * Incremental graph update — merge new data without resetting simulation.
 *
 * 1. Query DB for rows modified since last_updated timestamp
 * 2. Create/update nodes for changed rows
 * 3. Create/update links for changed relationships
 * 4. Remove nodes for deleted rows
 * 5. Warm-restart simulation (alpha = 0.3, not 1.0)
 */
function incrementalUpdate(graph, newNodes, newLinks) {
  const existingIds = new Set(graph.nodes.map(n => n.id));

  // Add new nodes
  for (const node of newNodes) {
    if (!existingIds.has(node.id)) {
      computeNodeVisuals(node);
      graph.nodes.push(node);
    } else {
      // Update existing node properties (preserve position)
      const existing = graph.nodes.find(n => n.id === node.id);
      Object.assign(existing, node, { x: existing.x, y: existing.y });
      computeNodeVisuals(existing);
    }
  }

  // Merge new links
  const existingLinkIds = new Set(graph.links.map(l =>
    `${l.source?.id || l.source}_${l.target?.id || l.target}_${l.type}`
  ));

  for (const link of newLinks) {
    const linkId = `${link.source}_${link.target}_${link.type}`;
    if (!existingLinkIds.has(linkId)) {
      graph.links.push(link);
    }
  }

  return graph;
}
```

### 8.2 Cache Strategy

```javascript
/**
 * Graph cache with timestamp-based invalidation.
 * Full rebuild: every 5 minutes or on manual trigger.
 * Incremental: every 30 seconds when graph is visible.
 */
const CACHE_CONFIG = {
  full_rebuild_interval: 300000,    // 5 minutes in ms
  incremental_interval: 30000,      // 30 seconds
  storage_key: "mbp_graph_cache",
  max_cache_age: 3600000,           // 1 hour — force full rebuild
};
```

---

## 9. Interaction Model

### 9.1 Node Interactions

| Action | Result |
|--------|--------|
| **Click** | Select node → show detail panel with all properties |
| **Double-click** | Expand node → show connected nodes (lazy load) |
| **Right-click** | Context menu: "Show evidence", "Build impeachment", "Trace authority" |
| **Hover** | Tooltip with key metrics (type, threat, evidence count) |
| **Drag** | Move node, fix position (shift+drag to unfix) |

### 9.2 Layer Interactions

| Action | Result |
|--------|--------|
| **Layer toggle** | Show/hide entire layer (checkbox in HUD) |
| **Layer solo** | Show only this layer + CORE (double-click layer name) |
| **Layer focus** | Zoom to fit all nodes in this layer |
| **Layer opacity** | Slider to fade non-focused layers |

### 9.3 Search

```javascript
/**
 * Fuse.js fuzzy search across all nodes.
 * Returns ranked results with highlighting.
 */
const SEARCH_CONFIG = {
  keys: [
    { name: "label", weight: 0.4 },
    { name: "short_label", weight: 0.2 },
    { name: "citation", weight: 0.2 },
    { name: "key_quote", weight: 0.1 },
    { name: "id", weight: 0.1 },
  ],
  threshold: 0.3,             // Fuzzy match threshold
  includeMatches: true,
  minMatchCharLength: 2,
};
```

---

## 10. Export Formats

THEMANBEARPIG must support multiple export formats for different consumers:

| Format | Consumer | Content |
|--------|----------|---------|
| `mbp_graph.json` | D3.js renderer | Full graph with all properties |
| `neo4j_nodes.csv` + `neo4j_edges.csv` | Neo4j import | Bloom-ready graph data |
| `gephi_gexf.xml` | Gephi | GEXF format for static analysis |
| `mermaid.md` | Documentation | Simplified Mermaid flowchart |
| `adjacency.json` | NetworkX | Adjacency list for Python analysis |

---

## 11. Quality Gates

### Graph Build PASS Gate

```
□ All CORE_PERSONS present (4 minimum)
□ Node count ≥ 100 (graph is not trivially empty)
□ Link count ≥ node_count * 0.5 (sufficient connectivity)
□ All 13 layers have ≥ 1 node each (or documented reason for empty)
□ No orphan nodes (every node has ≥ 1 link)
□ No duplicate node IDs
□ No self-referential links (source ≠ target)
□ Child node labeled "L.D.W." only (MCR 8.119(H))
□ No hallucinated persons (Jane Berry, Patricia Berry)
□ Separation counter computed dynamically
□ All node radii within [8, 60] range
□ All link widths within [1, 5] range
□ CARTEL links present (McNeill↔Hoopes↔Ladas-Hoopes triangle)
□ Frame rate ≥ 30 FPS at 2500 nodes
□ JSON output < 50 MB
```

### Anti-Hallucination Checks (Graph-Specific)

```python
BANNED_NODE_LABELS = [
    "Jane Berry", "Patricia Berry", "P35878",
    "Ron Berry, Esq", "Amy McNeill",
    "Emily Ann Watson", "Emily M. Watson",
    "Lincoln David Watson",  # Child's full name
]

def validate_graph(graph):
    """Validate graph against quality gates."""
    errors = []
    for node in graph["nodes"]:
        label = node.get("label", "")
        for banned in BANNED_NODE_LABELS:
            if banned.lower() in label.lower():
                errors.append(f"HALLUCINATION: Node '{node['id']}' contains banned label '{banned}'")

        # Child name check
        if node.get("subtype") == "child" and node.get("label") != "L.D.W.":
            errors.append(f"MCR 8.119(H) VIOLATION: Child node '{node['id']}' uses label '{node['label']}' instead of 'L.D.W.'")

    return errors
```

---

## 12. File Manifest

| File | Purpose | Size Target |
|------|---------|-------------|
| `mbp_graph_builder.py` | Master graph construction from DB | 800-1200 lines |
| `mbp_graph.json` | Built graph output (D3.js ready) | 5-50 MB |
| `mbp_layer_config.js` | LAYER_META + force simulation params | 300-500 lines |
| `mbp_node_types.js` | Node type definitions + factories | 400-600 lines |
| `mbp_link_types.js` | Link type definitions + factories | 200-400 lines |
| `mbp_visuals.js` | Sizing, coloring, LOD rules | 300-500 lines |
| `mbp_performance.js` | Culling, caching, worker offloading | 200-400 lines |
| `mbp_export.py` | Export to Neo4j CSV, GEXF, Mermaid | 300-500 lines |

---

## 13. Cross-Skill Dependencies

This GENESIS skill is the foundation. Other MBP skills depend on it:

| Dependent Skill | Uses From GENESIS |
|----------------|-------------------|
| **MBP-DATAWEAVE** | Node schemas, link schemas, LAYER_META, DB query templates |
| **MBP-FORGE-RENDERER** | LOD thresholds, color palette, sizing rules, renderer selection |
| **MBP-FORGE-PHYSICS** | LAYER_META force parameters, simulation config |
| **MBP-FORGE-EFFECTS** | Glow/pulse flags, color palette, opacity rules |
| **MBP-FORGE-DEPLOY** | Graph JSON schema, file manifest, export formats |
| **MBP-COMBAT-ADVERSARY** | PERSON node schema, threat_level, alignment |
| **MBP-COMBAT-WEAPONS** | WEAPON node schema, weapon subtypes, severity |
| **MBP-COMBAT-JUDICIAL** | CARTEL links, judicial node schema, violation_count |
| **MBP-COMBAT-EVIDENCE** | EVIDENCE node schema, relevance_score, smoking_gun |
| **MBP-COMBAT-AUTHORITY** | AUTHORITY node schema, chain_count, subtype classification |
| **MBP-COMBAT-IMPEACHMENT** | IMPEACHMENT node schema, contradiction links |
| **MBP-INTERFACE-CONTROLS** | Search config, interaction model, node click handlers |
| **MBP-INTERFACE-TIMELINE** | EVENT node schema, temporal_force config |
| **MBP-INTERFACE-NARRATIVE** | Layer descriptions, node labels, link labels |
| **MBP-INTERFACE-HUD** | Layer toggle config, metadata display |
| **MBP-INTEGRATION-ENGINES** | DB query templates, data_sources config |
| **MBP-INTEGRATION-FILING** | FILING node schema, readiness_score, lane_id |
| **MBP-INTEGRATION-BRAINS** | Graph JSON schema for brain feeding |
| **MBP-EMERGENCE-CONVERGENCE** | EMERGENCE layer, cross-layer connection matrix |
| **MBP-EMERGENCE-PREDICTION** | PREDICTION layer, temporal_force config |
| **MBP-EMERGENCE-SELFEVOLVE** | LAYER_META structure for parameter learning |
| **MBP-TRANSCENDENCE-SONIC** | threat_level → pitch mapping, severity → volume |
| **MBP-TRANSCENDENCE-DIMENSIONAL** | Node position schema (x,y → x,y,z promotion) |
| **OMEGA-MBP-INDEX** | Complete type registry, layer manifest, quality gates |

---

*END OF SINGULARITY-MBP-GENESIS v1.0.0 — The Architectural DNA of THEMANBEARPIG*
*13 Layers · 20+ Node Types · 17+ Link Types · 2,500+ Nodes · Production-Ready*

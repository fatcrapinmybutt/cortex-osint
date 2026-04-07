---
skill: SINGULARITY-MBP-COMBAT-WEAPONS
version: "1.0.0"
description: "Weapon chain visualization for THEMANBEARPIG: 9 litigation weapon types, doctrine-to-remedy-to-filing chains, PPO weaponization tracking, false allegation mapping, contempt abuse patterns. Renders offensive and defensive legal arsenals as directed acyclic graphs."
tier: "TIER-2/COMBAT"
domain: "Weapon chains — false allegations, ex parte abuse, contempt, PPO weaponization, filing chains"
triggers:
  - weapon
  - false allegation
  - ex parte
  - contempt
  - PPO weaponization
  - chain
  - arsenal
---

# SINGULARITY-MBP-COMBAT-WEAPONS v1.0

> **Every adversary tactic has a counter-weapon. Map them. Chain them. Deploy them.**

## Layer 1: Weapon Type Taxonomy (9 Types)

### 1.1 Weapon Type Definitions

```python
"""9-type weapon taxonomy for litigation intelligence visualization."""

WEAPON_TYPES = {
    'false_allegation': {
        'id': 'W1',
        'label': 'False Allegation',
        'icon': '⚠️',
        'shape': 'triangle',
        'color': '#ff4444',
        'description': 'Fabricated claims used to gain procedural advantage',
        'subtypes': [
            'suicidal_ideation', 'poisoning', 'assault',
            'drug_use', 'child_endangerment', 'threats',
        ],
        'indicators': [
            'no_police_report', 'no_medical_evidence', 'recanted',
            'contradicted_by_witness', 'pattern_of_escalation',
        ],
        'counter_weapons': ['impeachment', 'police_clearance', 'mre_613'],
    },
    'ppo_weaponization': {
        'id': 'W2',
        'label': 'PPO Weaponization',
        'icon': '🛡️',
        'shape': 'shield',
        'color': '#ff6600',
        'description': 'Protection orders misused as custody leverage',
        'subtypes': [
            'retaliatory_filing', 'no_basis_allegation',
            'contempt_trap', 'parenting_time_block',
        ],
        'indicators': [
            'filed_after_recanting', 'no_physical_contact',
            'used_for_custody_leverage', 'multiple_ppo_attempts',
        ],
        'counter_weapons': ['ppo_termination', 'mcl_600_2950', 'pattern_evidence'],
    },
    'contempt_abuse': {
        'id': 'W3',
        'label': 'Contempt Abuse',
        'icon': '⛓️',
        'shape': 'hexagon',
        'color': '#ff0088',
        'description': 'Weaponized contempt for protected speech/conduct',
        'subtypes': [
            'speech_punishment', 'birthday_message_contempt',
            'excessive_sentence', 'retaliatory_filing',
        ],
        'indicators': [
            'protected_speech', 'disproportionate_sentence',
            'no_willful_violation', 'first_amendment_issue',
        ],
        'counter_weapons': ['1st_amendment', 'purge_conditions', 'appeal'],
    },
    'ex_parte_order': {
        'id': 'W4',
        'label': 'Ex Parte Order',
        'icon': '🔒',
        'shape': 'diamond',
        'color': '#ff00ff',
        'description': 'Orders issued without notice or hearing',
        'subtypes': [
            'custody_suspension', 'parenting_time_suspension',
            'no_contact_order', 'emergency_without_emergency',
        ],
        'indicators': [
            'no_notice_to_party', 'no_hearing', 'no_emergency_basis',
            'premeditated', 'multiple_same_day',
        ],
        'counter_weapons': ['due_process', 'mathews_v_eldridge', 'mcr_2_107'],
    },
    'evidence_suppression': {
        'id': 'W5',
        'label': 'Evidence Suppression',
        'icon': '🚫',
        'shape': 'octagon',
        'color': '#8844ff',
        'description': 'Systematic exclusion of favorable evidence',
        'subtypes': [
            'evaluation_excluded', 'police_report_ignored',
            'recording_blocked', 'witness_prevented',
        ],
        'indicators': [
            'court_ordered_eval_excluded', 'officer_testimony_ignored',
            'favorable_evidence_rejected', 'mre_violation',
        ],
        'counter_weapons': ['mre_901', 'mre_702', 'appeal_evidentiary'],
    },
    'parenting_time_denial': {
        'id': 'W6',
        'label': 'Parenting Time Denial',
        'icon': '🚷',
        'shape': 'circle',
        'color': '#cc4400',
        'description': 'Systematic withholding of court-ordered parenting time',
        'subtypes': [
            'complete_withholding', 'conditional_access',
            'medication_coercion', 'supervised_only',
        ],
        'indicators': [
            'separation_days_counter', 'appclose_interference',
            'medication_as_condition', 'no_makeup_time',
        ],
        'counter_weapons': ['mcl_722_27a', 'contempt_motion', 'best_interest_j'],
    },
    'financial_warfare': {
        'id': 'W7',
        'label': 'Financial Warfare',
        'icon': '💰',
        'shape': 'square',
        'color': '#44aa00',
        'description': 'Economic attacks through litigation costs',
        'subtypes': [
            'repeated_motions', 'jail_causing_job_loss',
            'housing_loss', 'attorney_fee_drain',
        ],
        'indicators': [
            'multiple_job_losses', 'multiple_housing_losses',
            'filing_fee_burden', 'pro_se_disadvantage',
        ],
        'counter_weapons': ['fee_waiver', 'sanctions', 'damages_claim'],
    },
    'institutional_capture': {
        'id': 'W8',
        'label': 'Institutional Capture',
        'icon': '🏛️',
        'shape': 'pentagon',
        'color': '#0088ff',
        'description': 'Adversary influence over institutional actors',
        'subtypes': [
            'foc_bias', 'judicial_relationship',
            'law_enforcement_capture', 'agency_coordination',
        ],
        'indicators': [
            'former_law_partners', 'spouse_in_system',
            'same_office_address', 'pattern_of_favorable_rulings',
        ],
        'counter_weapons': ['mcr_2_003', 'jtc_complaint', 'msc_original'],
    },
    'retaliation': {
        'id': 'W9',
        'label': 'Retaliation',
        'icon': '🔥',
        'shape': 'star',
        'color': '#ff2222',
        'description': 'Punitive response to legitimate legal activity',
        'subtypes': [
            'filing_retaliation', 'complaint_retaliation',
            'witness_intimidation', 'escalation_after_objection',
        ],
        'indicators': [
            'action_within_72h_of_filing', 'escalation_pattern',
            'punishment_for_objecting', 'new_charges_after_complaint',
        ],
        'counter_weapons': ['1st_amendment_retaliation', 'section_1983', 'pattern_evidence'],
    },
}
```

### 1.2 Weapon Type Constants for D3

```javascript
const WEAPON_CONFIG = {
  W1: { shape: d3.symbolTriangle,  color: '#ff4444', label: 'False Allegation' },
  W2: { shape: d3.symbolWye,       color: '#ff6600', label: 'PPO Weaponization' },
  W3: { shape: d3.symbolDiamond,   color: '#ff0088', label: 'Contempt Abuse' },
  W4: { shape: d3.symbolSquare,    color: '#ff00ff', label: 'Ex Parte Order' },
  W5: { shape: d3.symbolCross,     color: '#8844ff', label: 'Evidence Suppression' },
  W6: { shape: d3.symbolCircle,    color: '#cc4400', label: 'PT Denial' },
  W7: { shape: d3.symbolSquare,    color: '#44aa00', label: 'Financial Warfare' },
  W8: { shape: d3.symbolDiamond,   color: '#0088ff', label: 'Institutional Capture' },
  W9: { shape: d3.symbolStar,      color: '#ff2222', label: 'Retaliation' },
};
```

## Layer 2: Building Weapon Chains from Database

### 2.1 Evidence-Backed Weapon Extraction

```python
"""Extract weapon instances from timeline_events and evidence_quotes."""
import sqlite3
import re
from collections import defaultdict

WEAPON_KEYWORDS = {
    'false_allegation':       ['alleged', 'fabricat', 'false', 'debunked', 'recant', 'no evidence'],
    'ppo_weaponization':      ['PPO', 'protection order', '5907', 'restraining'],
    'contempt_abuse':         ['contempt', 'jail', 'incarcerat', 'show cause', 'purge'],
    'ex_parte_order':         ['ex parte', 'without notice', 'without hearing', 'suspended'],
    'evidence_suppression':   ['excluded', 'suppressed', 'ignored', 'overruled', 'denied admission'],
    'parenting_time_denial':  ['withheld', 'denied parenting', 'no contact', 'suspended visit'],
    'financial_warfare':      ['lost job', 'lost hous', 'evict', 'fee', 'cost', 'financial'],
    'institutional_capture':  ['FOC', 'Rusco', 'former partner', 'Berry', 'conflict of interest'],
    'retaliation':            ['retaliat', 'punish', 'retribut', 'escalat', 'in response to'],
}

def extract_weapon_instances(db_path: str) -> list:
    """
    Scan timeline_events and evidence_quotes for weapon pattern matches.
    Returns list of weapon instances with source, date, type, and evidence.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA cache_size=-32000")
    conn.row_factory = sqlite3.Row

    weapons = []

    # Scan timeline_events
    try:
        events = conn.execute("""
            SELECT event_date, event_text, source_document, lane, actor
            FROM timeline_events
            WHERE event_date IS NOT NULL
            ORDER BY event_date
            LIMIT 10000
        """).fetchall()
    except Exception:
        events = []

    for event in events:
        text = (event['event_text'] or '').lower()
        for weapon_type, keywords in WEAPON_KEYWORDS.items():
            if any(kw.lower() in text for kw in keywords):
                weapons.append({
                    'type': weapon_type,
                    'date': event['event_date'],
                    'text': event['event_text'][:300],
                    'source': event['source_document'] or 'timeline',
                    'lane': event['lane'] or 'unknown',
                    'actor': event['actor'] or 'unknown',
                    'source_table': 'timeline_events',
                })

    # Scan evidence_quotes for additional weapon instances
    try:
        quotes = conn.execute("""
            SELECT quote_text, source_file, category, lane, event_date
            FROM evidence_quotes
            WHERE category IN ('judicial_violation', 'false_allegation',
                               'ppo', 'contempt', 'custody')
            LIMIT 5000
        """).fetchall()
    except Exception:
        quotes = []

    for quote in quotes:
        text = (quote['quote_text'] or '').lower()
        for weapon_type, keywords in WEAPON_KEYWORDS.items():
            if any(kw.lower() in text for kw in keywords):
                weapons.append({
                    'type': weapon_type,
                    'date': quote['event_date'] or '',
                    'text': quote['quote_text'][:300],
                    'source': quote['source_file'] or 'evidence',
                    'lane': quote['lane'] or 'unknown',
                    'actor': '',
                    'source_table': 'evidence_quotes',
                })

    conn.close()

    # Deduplicate by (type, date, first 100 chars of text)
    seen = set()
    unique = []
    for w in weapons:
        key = (w['type'], w['date'], w['text'][:100])
        if key not in seen:
            seen.add(key)
            unique.append(w)

    return sorted(unique, key=lambda w: w['date'] or '0000')
```

## Layer 3: Doctrine → Remedy → Filing DAGs

### 3.1 Chain Definition

Each weapon type has a counter-chain: the legal doctrine that applies, the remedy available,
and the specific filing vehicle that delivers it.

```python
"""Doctrine → Remedy → Filing chains for each weapon type."""

WEAPON_CHAINS = {
    'false_allegation': {
        'doctrine': [
            {'cite': 'MRE 613', 'text': 'Prior inconsistent statement impeachment'},
            {'cite': 'MRE 608', 'text': 'Character for truthfulness'},
            {'cite': 'MCL 722.23(j)', 'text': 'Willingness to facilitate relationship'},
        ],
        'remedy': [
            {'type': 'impeachment', 'text': 'Cross-examination with prior statements'},
            {'type': 'sanctions', 'text': 'MCR 2.114 sanctions for frivolous claims'},
            {'type': 'custody_factor', 'text': 'Factor (j) — false allegations pattern'},
        ],
        'filing': [
            {'vehicle': 'Motion for Sanctions', 'rule': 'MCR 2.114'},
            {'vehicle': 'Trial Brief re: Credibility', 'rule': 'MRE 608/613'},
            {'vehicle': 'Motion to Modify Custody', 'rule': 'MCR 3.206'},
        ],
    },
    'ppo_weaponization': {
        'doctrine': [
            {'cite': 'MCL 600.2950', 'text': 'PPO issuance requirements'},
            {'cite': 'Pickering v Pickering', 'text': 'PPO must not replace custody orders'},
            {'cite': 'MCR 3.707', 'text': 'Modification and termination of PPO'},
        ],
        'remedy': [
            {'type': 'termination', 'text': 'Motion to terminate PPO — no basis'},
            {'type': 'modification', 'text': 'Motion to modify PPO conditions'},
            {'type': 'pattern_evidence', 'text': 'Show pattern of weaponized filings'},
        ],
        'filing': [
            {'vehicle': 'Motion to Terminate PPO', 'rule': 'MCR 3.707(B)'},
            {'vehicle': 'Motion for Sanctions', 'rule': 'MCR 2.114'},
            {'vehicle': 'Brief re: PPO Pattern', 'rule': 'MCR 2.119'},
        ],
    },
    'contempt_abuse': {
        'doctrine': [
            {'cite': 'US Const Amend I', 'text': 'Protected speech cannot be contempt basis'},
            {'cite': 'MCL 600.1715', 'text': 'Purge conditions must be achievable'},
            {'cite': 'In re Contempt of Dougherty', 'text': 'Proportionality requirement'},
        ],
        'remedy': [
            {'type': 'appeal', 'text': 'Appeal contempt finding — due process violation'},
            {'type': 'habeas', 'text': 'Habeas corpus if currently incarcerated'},
            {'type': 'section_1983', 'text': 'Federal claim for unconstitutional jailing'},
        ],
        'filing': [
            {'vehicle': 'Appeal of Contempt', 'rule': 'MCR 7.204'},
            {'vehicle': 'Habeas Corpus Petition', 'rule': 'MCL 600.4301'},
            {'vehicle': '42 USC §1983 Complaint', 'rule': '28 USC §1343'},
        ],
    },
    'ex_parte_order': {
        'doctrine': [
            {'cite': 'Mathews v Eldridge', 'text': 'Due process balancing test'},
            {'cite': 'MCR 2.107', 'text': 'Notice requirements'},
            {'cite': 'US Const Amend XIV', 'text': 'Procedural due process'},
        ],
        'remedy': [
            {'type': 'vacatur', 'text': 'Motion to vacate ex parte order'},
            {'type': 'disqualification', 'text': 'MCR 2.003 judicial bias'},
            {'type': 'federal_claim', 'text': '§1983 for deprivation under color of law'},
        ],
        'filing': [
            {'vehicle': 'Motion to Vacate', 'rule': 'MCR 2.612(C)'},
            {'vehicle': 'Disqualification Motion', 'rule': 'MCR 2.003'},
            {'vehicle': 'MSC Superintending Control', 'rule': 'MCR 7.306'},
        ],
    },
    'evidence_suppression': {
        'doctrine': [
            {'cite': 'MRE 901', 'text': 'Authentication requirements'},
            {'cite': 'MRE 702-703', 'text': 'Expert testimony admissibility'},
            {'cite': 'Sullivan v Gray', 'text': 'One-party recording consent'},
        ],
        'remedy': [
            {'type': 'appeal', 'text': 'Appeal evidentiary exclusion'},
            {'type': 'new_evidence', 'text': 'MCR 2.612(C)(1)(b) newly discovered evidence'},
            {'type': 'bias_evidence', 'text': 'Use exclusion pattern as bias indicator'},
        ],
        'filing': [
            {'vehicle': 'Motion for Reconsideration', 'rule': 'MCR 2.119(F)'},
            {'vehicle': 'Appeal — Evidentiary Error', 'rule': 'MCR 7.212'},
            {'vehicle': 'JTC Complaint', 'rule': 'MI Const art 6 § 30'},
        ],
    },
    'parenting_time_denial': {
        'doctrine': [
            {'cite': 'MCL 722.27a', 'text': 'Parenting time is a right, not a privilege'},
            {'cite': 'MCL 722.23(j)', 'text': 'Factor (j) — facilitate relationship'},
            {'cite': 'Troxel v Granville', 'text': 'Fundamental right to parent'},
        ],
        'remedy': [
            {'type': 'enforcement', 'text': 'Motion to enforce parenting time'},
            {'type': 'modification', 'text': 'Motion to modify custody based on denial'},
            {'type': 'contempt', 'text': 'Contempt motion for willful violation'},
        ],
        'filing': [
            {'vehicle': 'FOC Parenting Time Complaint', 'rule': 'FOC 89'},
            {'vehicle': 'Emergency Motion to Restore', 'rule': 'MCR 3.206'},
            {'vehicle': 'Motion for Contempt', 'rule': 'MCR 3.606'},
        ],
    },
    'financial_warfare': {
        'doctrine': [
            {'cite': 'MCR 2.114(E)', 'text': 'Sanctions for frivolous filings'},
            {'cite': 'MCR 2.625', 'text': 'Costs and attorney fees'},
            {'cite': '42 USC § 1988', 'text': 'Federal fee shifting'},
        ],
        'remedy': [
            {'type': 'fee_waiver', 'text': 'MC 20 fee waiver application'},
            {'type': 'sanctions', 'text': 'Sanctions for vexatious litigation'},
            {'type': 'damages', 'text': 'Economic damages in civil complaint'},
        ],
        'filing': [
            {'vehicle': 'Fee Waiver Application', 'rule': 'MC 20'},
            {'vehicle': 'Motion for Sanctions', 'rule': 'MCR 2.114(E)'},
            {'vehicle': 'Civil Damages Complaint', 'rule': 'MCR 2.111'},
        ],
    },
    'institutional_capture': {
        'doctrine': [
            {'cite': 'MCR 2.003', 'text': 'Disqualification for conflict of interest'},
            {'cite': 'MI Const art 6 § 4', 'text': 'Superintending control'},
            {'cite': 'Canon 2', 'text': 'Judicial appearance of impropriety'},
        ],
        'remedy': [
            {'type': 'disqualification', 'text': 'MCR 2.003 motion for judicial recusal'},
            {'type': 'jtc', 'text': 'JTC complaint for institutional corruption'},
            {'type': 'msc', 'text': 'MSC original jurisdiction — circuit compromised'},
        ],
        'filing': [
            {'vehicle': 'Disqualification Motion', 'rule': 'MCR 2.003'},
            {'vehicle': 'JTC Complaint', 'rule': 'MI Const art 6 § 30'},
            {'vehicle': 'MSC Original Action', 'rule': 'MCR 7.306'},
        ],
    },
    'retaliation': {
        'doctrine': [
            {'cite': 'US Const Amend I', 'text': 'Right to petition government'},
            {'cite': '42 USC § 1983', 'text': 'Deprivation under color of law'},
            {'cite': 'Crawford v Marion County', 'text': 'Retaliation for exercise of rights'},
        ],
        'remedy': [
            {'type': 'federal_claim', 'text': '§1983 First Amendment retaliation'},
            {'type': 'pattern_evidence', 'text': 'Document retaliation timeline'},
            {'type': 'injunction', 'text': 'Seek injunctive relief against retaliation'},
        ],
        'filing': [
            {'vehicle': '42 USC §1983 Complaint', 'rule': '28 USC §1343'},
            {'vehicle': 'Emergency Motion for Protection', 'rule': 'MCR 3.206'},
            {'vehicle': 'JTC Complaint — Retaliation', 'rule': 'MI Const art 6 § 30'},
        ],
    },
}
```

## Layer 4: Weapon Effectiveness Scoring

### 4.1 Scoring Algorithm

```python
def score_weapon_effectiveness(weapon_instances: list, weapon_type: str) -> dict:
    """
    Score how effectively a weapon type has been deployed against plaintiff.
    Higher score = more damage inflicted = higher priority counter-weapon.
    """
    instances = [w for w in weapon_instances if w['type'] == weapon_type]
    if not instances:
        return {'score': 0, 'frequency': 0, 'duration': 'N/A', 'severity': 'NONE'}

    frequency = len(instances)

    # Date span
    dated = [w for w in instances if w['date'] and w['date'] > '2000']
    if len(dated) >= 2:
        dates = sorted(d['date'] for d in dated)
        duration_desc = f"{dates[0][:10]} to {dates[-1][:10]}"
    else:
        duration_desc = 'single event'

    # Lane spread (more lanes = broader attack)
    lanes = set(w['lane'] for w in instances if w['lane'] != 'unknown')
    lane_spread = len(lanes)

    # Severity weights by type
    type_severity = {
        'false_allegation': 7, 'ppo_weaponization': 8, 'contempt_abuse': 9,
        'ex_parte_order': 10, 'evidence_suppression': 6,
        'parenting_time_denial': 9, 'financial_warfare': 7,
        'institutional_capture': 10, 'retaliation': 8,
    }
    base_severity = type_severity.get(weapon_type, 5)

    # Composite score: frequency × severity × lane_spread (normalized to 0-10)
    raw = (frequency * base_severity * max(lane_spread, 1)) ** 0.5
    score = min(round(raw, 1), 10.0)

    severity_label = (
        'CRITICAL' if score >= 8 else
        'HIGH' if score >= 6 else
        'MODERATE' if score >= 4 else
        'LOW'
    )

    return {
        'score': score,
        'frequency': frequency,
        'duration': duration_desc,
        'severity': severity_label,
        'lanes': list(lanes),
    }
```

## Layer 5: Defensive Countermeasure Mapping

### 5.1 Counter-Weapon Selection

```python
def select_counter_weapons(weapon_type: str, effectiveness_score: float) -> list:
    """
    Select and prioritize counter-weapons based on weapon type and its effectiveness.
    Higher effectiveness → more aggressive counter-weapons unlocked.
    """
    chain = WEAPON_CHAINS.get(weapon_type, {})
    if not chain:
        return []

    counters = []

    # Always include doctrinal counter
    for doctrine in chain.get('doctrine', []):
        counters.append({
            'stage': 'doctrine',
            'cite': doctrine['cite'],
            'text': doctrine['text'],
            'priority': 'ALWAYS',
        })

    # Include remedy at score >= 3
    if effectiveness_score >= 3:
        for remedy in chain.get('remedy', []):
            counters.append({
                'stage': 'remedy',
                'type': remedy['type'],
                'text': remedy['text'],
                'priority': 'HIGH' if effectiveness_score >= 6 else 'MODERATE',
            })

    # Include filing vehicles at score >= 5
    if effectiveness_score >= 5:
        for filing in chain.get('filing', []):
            counters.append({
                'stage': 'filing',
                'vehicle': filing['vehicle'],
                'rule': filing['rule'],
                'priority': 'CRITICAL' if effectiveness_score >= 8 else 'HIGH',
            })

    return counters
```

## Layer 6: D3 Weapon Chain DAG Visualization

### 6.1 DAG Layout and Rendering

```javascript
function renderWeaponChainDAG(container, weaponType, chainData) {
  const width = container.clientWidth;
  const height = 400;
  const config = WEAPON_CONFIG[WEAPON_TYPES_MAP[weaponType]] || WEAPON_CONFIG.W1;

  const svg = d3.select(container).append('svg')
    .attr('width', width).attr('height', height);

  // Three columns: Doctrine → Remedy → Filing
  const columns = [
    { label: 'DOCTRINE', x: width * 0.15, items: chainData.doctrine || [] },
    { label: 'REMEDY',   x: width * 0.50, items: chainData.remedy || [] },
    { label: 'FILING',   x: width * 0.85, items: chainData.filing || [] },
  ];

  // Column headers
  svg.selectAll('.col-header')
    .data(columns).join('text')
    .attr('x', d => d.x)
    .attr('y', 30)
    .attr('text-anchor', 'middle')
    .attr('fill', '#888')
    .attr('font-size', '12px')
    .attr('font-weight', 'bold')
    .text(d => d.label);

  // Place nodes in each column
  const nodes = [];
  const links = [];

  columns.forEach((col, ci) => {
    col.items.forEach((item, ri) => {
      const y = 70 + ri * 60;
      const node = {
        id: `${ci}-${ri}`,
        x: col.x, y,
        label: item.cite || item.type || item.vehicle || '',
        detail: item.text || item.rule || '',
        column: ci,
      };
      nodes.push(node);

      // Link from previous column nodes
      if (ci > 0) {
        const prevCol = columns[ci - 1];
        prevCol.items.forEach((_, pri) => {
          links.push({
            source: `${ci-1}-${pri}`,
            target: `${ci}-${ri}`,
          });
        });
      }
    });
  });

  // Render links as curved paths
  const nodeMap = Object.fromEntries(nodes.map(n => [n.id, n]));

  svg.append('g').selectAll('path')
    .data(links).join('path')
    .attr('d', d => {
      const s = nodeMap[d.source];
      const t = nodeMap[d.target];
      const mx = (s.x + t.x) / 2;
      return `M ${s.x + 60} ${s.y} C ${mx} ${s.y}, ${mx} ${t.y}, ${t.x - 60} ${t.y}`;
    })
    .attr('fill', 'none')
    .attr('stroke', config.color + '66')
    .attr('stroke-width', 2);

  // Render nodes as rounded rectangles
  const nodeGroups = svg.append('g').selectAll('g')
    .data(nodes).join('g')
    .attr('transform', d => `translate(${d.x - 55}, ${d.y - 18})`);

  nodeGroups.append('rect')
    .attr('width', 110).attr('height', 36)
    .attr('rx', 6).attr('ry', 6)
    .attr('fill', (d) => d.column === 2 ? config.color + '33' : '#1a1a3a')
    .attr('stroke', config.color + '88')
    .attr('stroke-width', 1);

  nodeGroups.append('text')
    .attr('x', 55).attr('y', 14)
    .attr('text-anchor', 'middle')
    .attr('fill', '#e0e0e0')
    .attr('font-size', '10px')
    .attr('font-weight', 'bold')
    .text(d => d.label.substring(0, 18));

  nodeGroups.append('text')
    .attr('x', 55).attr('y', 28)
    .attr('text-anchor', 'middle')
    .attr('fill', '#888')
    .attr('font-size', '8px')
    .text(d => d.detail.substring(0, 24));

  // Weapon type header
  svg.append('text')
    .attr('x', width / 2).attr('y', 15)
    .attr('text-anchor', 'middle')
    .attr('fill', config.color)
    .attr('font-size', '14px')
    .attr('font-weight', 'bold')
    .text(`⚔ ${config.label} — Counter-Chain`);
}
```

## Layer 7: Animated Weapon Chain Traversal

### 7.1 Chain Walk Animation

```javascript
function animateChainTraversal(svg, links, nodeMap, config) {
  const totalDuration = 2000;
  const stepDuration = totalDuration / links.length;

  links.forEach((link, i) => {
    const s = nodeMap[link.source];
    const t = nodeMap[link.target];

    // Animated particle traveling along the chain
    const particle = svg.append('circle')
      .attr('r', 5)
      .attr('fill', config.color)
      .attr('opacity', 0);

    particle
      .transition().delay(i * stepDuration)
      .duration(0).attr('opacity', 1)
      .attr('cx', s.x).attr('cy', s.y)
      .transition().duration(stepDuration).ease(d3.easeCubicInOut)
      .attr('cx', t.x).attr('cy', t.y)
      .transition().duration(300)
      .attr('opacity', 0)
      .remove();

    // Highlight link being traversed
    svg.selectAll('path')
      .filter((_, pi) => pi === i)
      .transition().delay(i * stepDuration)
      .duration(stepDuration)
      .attr('stroke', config.color)
      .attr('stroke-width', 3)
      .transition().duration(500)
      .attr('stroke', config.color + '66')
      .attr('stroke-width', 2);
  });
}
```

## Layer 8: Cross-Lane Weapon Correlation

### 8.1 Multi-Lane Weapon Matrix

```python
def build_weapon_matrix(weapon_instances: list) -> dict:
    """
    Build a weapon-type × lane matrix showing where weapons are deployed.
    Reveals cross-lane coordination patterns.
    """
    matrix = {}
    for w in weapon_instances:
        wtype = w['type']
        lane = w['lane'] or 'unknown'
        if wtype not in matrix:
            matrix[wtype] = {}
        matrix[wtype][lane] = matrix[wtype].get(lane, 0) + 1

    return matrix
```

### 8.2 D3 Heatmap for Weapon × Lane

```javascript
function renderWeaponLaneHeatmap(container, matrix) {
  const weaponTypes = Object.keys(matrix);
  const lanes = [...new Set(weaponTypes.flatMap(w => Object.keys(matrix[w])))];

  const cellSize = 50;
  const margin = { top: 80, left: 180 };
  const width = margin.left + lanes.length * cellSize + 40;
  const height = margin.top + weaponTypes.length * cellSize + 40;

  const svg = d3.select(container).append('svg')
    .attr('width', width).attr('height', height);

  // Find max for color scale
  let maxVal = 0;
  for (const wt of weaponTypes)
    for (const l of lanes)
      maxVal = Math.max(maxVal, matrix[wt]?.[l] || 0);

  const colorScale = d3.scaleSequential(d3.interpolateInferno)
    .domain([0, maxVal]);

  // Column headers (lanes)
  svg.selectAll('.lane-label')
    .data(lanes).join('text')
    .attr('x', (_, i) => margin.left + i * cellSize + cellSize / 2)
    .attr('y', margin.top - 10)
    .attr('text-anchor', 'middle')
    .attr('fill', '#aaa').attr('font-size', '11px')
    .text(d => d);

  // Row headers (weapon types)
  svg.selectAll('.weapon-label')
    .data(weaponTypes).join('text')
    .attr('x', margin.left - 10)
    .attr('y', (_, i) => margin.top + i * cellSize + cellSize / 2 + 4)
    .attr('text-anchor', 'end')
    .attr('fill', '#aaa').attr('font-size', '10px')
    .text(d => d.replace(/_/g, ' '));

  // Heat cells
  for (let wi = 0; wi < weaponTypes.length; wi++) {
    for (let li = 0; li < lanes.length; li++) {
      const val = matrix[weaponTypes[wi]]?.[lanes[li]] || 0;
      svg.append('rect')
        .attr('x', margin.left + li * cellSize)
        .attr('y', margin.top + wi * cellSize)
        .attr('width', cellSize - 2)
        .attr('height', cellSize - 2)
        .attr('rx', 4)
        .attr('fill', val > 0 ? colorScale(val) : '#111')
        .attr('stroke', '#333');

      if (val > 0) {
        svg.append('text')
          .attr('x', margin.left + li * cellSize + cellSize / 2 - 1)
          .attr('y', margin.top + wi * cellSize + cellSize / 2 + 4)
          .attr('text-anchor', 'middle')
          .attr('fill', val > maxVal * 0.6 ? '#000' : '#fff')
          .attr('font-size', '12px')
          .attr('font-weight', 'bold')
          .text(val);
      }
    }
  }
}
```

## Layer 9: Full Pipeline Integration

### 9.1 End-to-End Weapon Analysis

```python
def run_weapon_analysis(db_path: str) -> dict:
    """
    Complete weapon analysis pipeline:
    1. Extract weapon instances from DB
    2. Score effectiveness per type
    3. Select counter-weapons
    4. Build cross-lane matrix
    5. Prepare visualization data
    """
    instances = extract_weapon_instances(db_path)

    results = {}
    for weapon_type in WEAPON_TYPES:
        effectiveness = score_weapon_effectiveness(instances, weapon_type)
        counters = select_counter_weapons(weapon_type, effectiveness['score'])
        chain = WEAPON_CHAINS.get(weapon_type, {})

        results[weapon_type] = {
            'meta': WEAPON_TYPES[weapon_type],
            'effectiveness': effectiveness,
            'counter_weapons': counters,
            'chain': chain,
            'instance_count': effectiveness['frequency'],
        }

    matrix = build_weapon_matrix(instances)

    return {
        'weapons': results,
        'matrix': matrix,
        'total_instances': len(instances),
        'most_effective': max(results.items(),
                              key=lambda x: x[1]['effectiveness']['score'])[0],
    }
```

## Anti-Patterns

1. **NEVER** hardcode weapon instance dates — extract from DB dynamically
2. **NEVER** display weapon chains without linking to source evidence
3. **NEVER** omit the counter-weapon for any weapon type — every attack has a response
4. **NEVER** render the DAG without animated traversal — static DAGs are unreadable
5. **NEVER** mix offensive weapons (adversary) with defensive weapons (plaintiff) in the same view
6. **NEVER** use red for all weapon types — distinct color per type is essential for scanning
7. **NEVER** skip the cross-lane matrix — coordination patterns only emerge in cross-lane view
8. **NEVER** forget to include the separation day counter when displaying parenting_time_denial

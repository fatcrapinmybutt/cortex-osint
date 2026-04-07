---
name: SINGULARITY-MBP-INTEGRATION-BRAINS
description: "Brain network visualization for THEMANBEARPIG: 23+ brain DB topology, inter-brain data flows, health monitoring, learning loop spiral, knowledge density heatmap, version timeline."
version: "1.0.0"
tier: "TIER-4/INTEGRATION"
domain: "Brain network visualization — DB topology, inter-brain flows, health dashboard, learning loops, knowledge density"
triggers:
  - brain
  - inter-brain
  - learning loop
  - brain health
  - versioning
  - knowledge flow
  - brain network
  - brain topology
  - brain dashboard
  - brain monitoring
cross_links:
  - SINGULARITY-MBP-GENESIS
  - SINGULARITY-MBP-DATAWEAVE
  - SINGULARITY-MBP-INTERFACE-HUD
  - SINGULARITY-MBP-FORGE-RENDERER
  - SINGULARITY-MBP-FORGE-PHYSICS
  - SINGULARITY-MBP-INTEGRATION-ENGINES
  - SINGULARITY-MBP-COMBAT-EVIDENCE
  - SINGULARITY-MBP-EMERGENCE-CONVERGENCE
---

# SINGULARITY-MBP-INTEGRATION-BRAINS v1.0

> **The neural architecture of LitigationOS made visible. 23+ brain databases as a living force-directed network — data flowing between nodes like synaptic pulses.**

## Layer 1: Brain Network Topology

### 1.1 Brain Database Registry

Every brain database in LitigationOS, with its location, purpose, and connectivity.

```javascript
/**
 * THEMANBEARPIG Brain Network Registry
 * Maps all 23+ brain databases with metadata for force-graph rendering.
 */
const BRAIN_REGISTRY = [
  // Tier 1: HOT — C:\ NVMe SSD (WAL mode)
  {
    id: 'litigation_context',
    label: 'Litigation Context',
    path: 'C:\\Users\\andre\\LitigationOS\\litigation_context.db',
    tier: 'HOT',
    category: 'central',
    color: '#ef4444',
    description: 'Central hub — 790+ tables, 1.3 GB',
    expectedSize: 1400,  // MB approximate
    icon: '🧠',
  },
  {
    id: 'authority_master',
    label: 'Authority Master',
    path: 'C:\\Users\\andre\\LitigationOS\\09_DATA\\authority_master.db',
    tier: 'HOT',
    category: 'legal',
    color: '#3b82f6',
    description: 'Legal authorities — MCR, MCL, case law',
    expectedSize: 83,
    icon: '⚖️',
  },
  {
    id: 'ec',
    label: 'Evidence Chains',
    path: 'C:\\Users\\andre\\LitigationOS\\09_DATA\\ec.db',
    tier: 'HOT',
    category: 'evidence',
    color: '#10b981',
    description: 'Evidence chain relationships',
    expectedSize: 29,
    icon: '🔗',
  },
  {
    id: 'mcr_rules',
    label: 'MCR Rules',
    path: 'C:\\Users\\andre\\LitigationOS\\mcr_rules.db',
    tier: 'HOT',
    category: 'legal',
    color: '#6366f1',
    description: 'Michigan Court Rules full text',
    expectedSize: 4,
    icon: '📜',
  },
  {
    id: 'court_forms',
    label: 'Court Forms',
    path: 'C:\\Users\\andre\\LitigationOS\\court_forms.db',
    tier: 'HOT',
    category: 'legal',
    color: '#8b5cf6',
    description: 'SCAO court form catalog',
    expectedSize: 0.1,
    icon: '📋',
  },
  {
    id: 'mbp_brain',
    label: 'MBP Brain',
    path: 'C:\\Users\\andre\\LitigationOS\\mbp_brain.db',
    tier: 'HOT',
    category: 'intelligence',
    color: '#f59e0b',
    description: 'THEMANBEARPIG graph intelligence',
    expectedSize: 50,
    icon: '🐻',
  },
  {
    id: 'claim_evidence_links',
    label: 'Claim-Evidence Links',
    path: 'C:\\Users\\andre\\LitigationOS\\claim_evidence_links.db',
    tier: 'HOT',
    category: 'evidence',
    color: '#14b8a6',
    description: 'Claim-to-evidence binding graph',
    expectedSize: 10,
    icon: '🔗',
  },
  {
    id: 'skills_registry',
    label: 'Skills Registry',
    path: 'C:\\Users\\andre\\LitigationOS\\.agents\\skills_registry.db',
    tier: 'HOT',
    category: 'system',
    color: '#6b7280',
    description: 'Agent skill definitions and activation',
    expectedSize: 1,
    icon: '🎯',
  },
  {
    id: 'file_catalog',
    label: 'File Catalog',
    path: 'C:\\Users\\andre\\LitigationOS\\00_SYSTEM\\file_catalog.db',
    tier: 'HOT',
    category: 'system',
    color: '#a855f7',
    description: 'Universal file inventory — 611K+ files',
    expectedSize: 233,
    icon: '📁',
  },
  {
    id: 'litigation_lite',
    label: 'Litigation Lite',
    path: 'C:\\Users\\andre\\LitigationOS\\09_DATA\\litigation_lite.db',
    tier: 'HOT',
    category: 'central',
    color: '#f97316',
    description: 'Lightweight query subset of main DB',
    expectedSize: 50,
    icon: '⚡',
  },
  // Tier 1: HOT — Brain DBs in 00_SYSTEM/brains/
  {
    id: 'interpretation_brain',
    label: 'Interpretation Brain',
    path: 'C:\\Users\\andre\\LitigationOS\\00_SYSTEM\\brains\\interpretation_brain.db',
    tier: 'HOT',
    category: 'intelligence',
    color: '#ec4899',
    description: 'Legal interpretation and analysis engine',
    expectedSize: 200,
    icon: '🧩',
  },
  {
    id: 'narrative_brain',
    label: 'Narrative Brain',
    path: 'C:\\Users\\andre\\LitigationOS\\00_SYSTEM\\brains\\narrative_brain.db',
    tier: 'HOT',
    category: 'intelligence',
    color: '#f43f5e',
    description: 'Narrative construction and story engine',
    expectedSize: 150,
    icon: '📖',
  },
  {
    id: 'authority_brain',
    label: 'Authority Brain',
    path: 'C:\\Users\\andre\\LitigationOS\\00_SYSTEM\\brains\\authority_brain.db',
    tier: 'HOT',
    category: 'intelligence',
    color: '#0ea5e9',
    description: 'Authority chain synthesis and validation',
    expectedSize: 200,
    icon: '🏛️',
  },
  {
    id: 'evidence_brain',
    label: 'Evidence Brain',
    path: 'C:\\Users\\andre\\LitigationOS\\00_SYSTEM\\brains\\evidence_brain.db',
    tier: 'HOT',
    category: 'intelligence',
    color: '#22c55e',
    description: 'Evidence classification and scoring',
    expectedSize: 100,
    icon: '🔍',
  },
  // Tier 2: WARM — J:\ USB exFAT (DELETE journal mode)
  {
    id: 'omega_dedup',
    label: 'Omega Dedup',
    path: 'J:\\LitigationOS_CENTRAL\\DATABASES\\MANIFESTS\\omega_dedup.db',
    tier: 'WARM',
    category: 'system',
    color: '#78716c',
    description: 'Content deduplication clusters',
    expectedSize: 592,
    icon: '♻️',
  },
  {
    id: 'ocr_master',
    label: 'OCR Master',
    path: 'J:\\LitigationOS_CENTRAL\\DATABASES\\OCR\\ocr_master.db',
    tier: 'WARM',
    category: 'processing',
    color: '#a1a1aa',
    description: 'OCR extraction results across all drives',
    expectedSize: 231,
    icon: '👁️',
  },
  {
    id: 'script_forge',
    label: 'Script Forge',
    path: 'C:\\Users\\andre\\LitigationOS\\script_forge.db',
    tier: 'HOT',
    category: 'system',
    color: '#64748b',
    description: 'Tool and script repository',
    expectedSize: 211,
    icon: '🔧',
  },
  {
    id: 'drive_i_manifest',
    label: 'Drive I Manifest',
    path: 'J:\\LitigationOS_CENTRAL\\DATABASES\\MANIFESTS\\drive_i_manifest.db',
    tier: 'WARM',
    category: 'system',
    color: '#94a3b8',
    description: 'I:\\ drive full file manifest',
    expectedSize: 1400,
    icon: '💾',
  },
];

/**
 * Inter-brain data flow edges.
 * Each edge represents a known data dependency or query pattern.
 */
const BRAIN_FLOWS = [
  // Evidence pipeline: intake → classify → index → synthesize
  { source: 'file_catalog',         target: 'litigation_context', type: 'ingest',    weight: 5, label: 'File discovery' },
  { source: 'ocr_master',           target: 'litigation_context', type: 'ingest',    weight: 4, label: 'OCR text extraction' },
  { source: 'litigation_context',   target: 'evidence_brain',     type: 'feed',      weight: 5, label: 'Evidence atoms' },
  { source: 'litigation_context',   target: 'authority_brain',    type: 'feed',      weight: 5, label: 'Authority chains' },
  { source: 'litigation_context',   target: 'narrative_brain',    type: 'feed',      weight: 4, label: 'Timeline events' },
  { source: 'litigation_context',   target: 'interpretation_brain', type: 'feed',    weight: 4, label: 'Legal analysis' },
  { source: 'litigation_context',   target: 'mbp_brain',          type: 'feed',      weight: 5, label: 'Graph data' },
  { source: 'litigation_context',   target: 'litigation_lite',    type: 'mirror',    weight: 3, label: 'Lite subset' },

  // Cross-brain synthesis
  { source: 'evidence_brain',       target: 'claim_evidence_links', type: 'synthesis', weight: 4, label: 'Evidence↔Claim binding' },
  { source: 'authority_brain',      target: 'mcr_rules',          type: 'reference', weight: 3, label: 'Rule lookup' },
  { source: 'authority_brain',      target: 'authority_master',    type: 'reference', weight: 4, label: 'Authority validation' },
  { source: 'authority_brain',      target: 'court_forms',         type: 'reference', weight: 2, label: 'Form requirements' },
  { source: 'narrative_brain',      target: 'evidence_brain',     type: 'query',     weight: 3, label: 'Evidence for narrative' },
  { source: 'interpretation_brain', target: 'authority_brain',    type: 'query',     weight: 3, label: 'Authority for analysis' },
  { source: 'ec',                   target: 'claim_evidence_links', type: 'feed',    weight: 3, label: 'Chain linking' },
  { source: 'mbp_brain',            target: 'evidence_brain',     type: 'query',     weight: 3, label: 'Evidence for graph' },
  { source: 'omega_dedup',          target: 'file_catalog',       type: 'dedup',     weight: 2, label: 'Dedup results' },
  { source: 'drive_i_manifest',     target: 'file_catalog',       type: 'ingest',    weight: 2, label: 'Drive I files' },

  // Skills and system
  { source: 'skills_registry',      target: 'mbp_brain',          type: 'config',    weight: 1, label: 'Skill definitions' },
  { source: 'script_forge',         target: 'litigation_context', type: 'tools',     weight: 2, label: 'Script recipes' },
];

const FLOW_COLORS = {
  ingest:    '#10b981',
  feed:      '#3b82f6',
  synthesis: '#8b5cf6',
  reference: '#f59e0b',
  query:     '#ec4899',
  mirror:    '#06b6d4',
  dedup:     '#78716c',
  config:    '#6b7280',
  tools:     '#a855f7',
};
```

### 1.2 Force-Directed Brain Network

```javascript
/**
 * D3.js force-directed graph of brain databases.
 * Node size = log(row_count), edge thickness = flow weight.
 * Tier-based radial positioning: HOT center, WARM outer ring.
 */
function createBrainNetwork(container, brainData, flowData, width, height) {
  const svg = d3.select(container)
    .append('svg')
    .attr('width', width)
    .attr('height', height)
    .attr('viewBox', `0 0 ${width} ${height}`);

  const g = svg.append('g')
    .attr('class', 'brain-network');

  // Zoom behavior
  const zoom = d3.zoom()
    .scaleExtent([0.3, 5])
    .on('zoom', (event) => g.attr('transform', event.transform));
  svg.call(zoom);

  // Prepare node data with computed sizes
  const nodes = brainData.map(brain => ({
    ...brain,
    radius: Math.max(12, Math.min(50, Math.log2(brain.rowCount || 1) * 5)),
    fx: brain.tier === 'HOT' ? null : null,
    fy: brain.tier === 'HOT' ? null : null,
  }));

  const nodeMap = new Map(nodes.map(n => [n.id, n]));
  const links = flowData
    .filter(f => nodeMap.has(f.source) && nodeMap.has(f.target))
    .map(f => ({
      ...f,
      source: f.source,
      target: f.target,
    }));

  // Force simulation with tier-based radial force
  const simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links)
      .id(d => d.id)
      .distance(d => 120 - d.weight * 8)
      .strength(d => 0.1 + d.weight * 0.05))
    .force('charge', d3.forceManyBody()
      .strength(d => -200 - d.radius * 5))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide()
      .radius(d => d.radius + 10))
    .force('radial', d3.forceRadial(
      d => d.tier === 'HOT' ? 100 : 300,
      width / 2, height / 2
    ).strength(0.05));

  // Edge glow filter
  const defs = svg.append('defs');
  defs.append('filter')
    .attr('id', 'edge-glow')
    .append('feGaussianBlur')
    .attr('in', 'SourceGraphic')
    .attr('stdDeviation', '2');

  // Draw edges (flow paths)
  const linkGroup = g.append('g').attr('class', 'brain-links');
  const linkElements = linkGroup.selectAll('line')
    .data(links)
    .enter()
    .append('line')
    .attr('stroke', d => FLOW_COLORS[d.type] || '#374151')
    .attr('stroke-width', d => Math.max(1, d.weight * 0.8))
    .attr('stroke-opacity', 0.5)
    .attr('filter', 'url(#edge-glow)');

  // Draw nodes (brain databases)
  const nodeGroup = g.append('g').attr('class', 'brain-nodes');
  const nodeElements = nodeGroup.selectAll('g')
    .data(nodes)
    .enter()
    .append('g')
    .attr('class', d => `brain-node brain-${d.id}`)
    .style('cursor', 'pointer')
    .call(d3.drag()
      .on('start', (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x; d.fy = d.y;
      })
      .on('drag', (event, d) => {
        d.fx = event.x; d.fy = event.y;
      })
      .on('end', (event, d) => {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null; d.fy = null;
      }));

  // Node outer ring (tier indicator)
  nodeElements.append('circle')
    .attr('r', d => d.radius + 3)
    .attr('fill', 'none')
    .attr('stroke', d => d.tier === 'HOT' ? '#ef4444' : '#78716c')
    .attr('stroke-width', 2)
    .attr('stroke-dasharray', d => d.tier === 'WARM' ? '4,2' : 'none');

  // Node fill circle
  nodeElements.append('circle')
    .attr('r', d => d.radius)
    .attr('fill', d => d.color)
    .attr('opacity', 0.8)
    .attr('stroke', '#1e1e2e')
    .attr('stroke-width', 2);

  // Node icon
  nodeElements.append('text')
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'central')
    .attr('font-size', d => Math.max(10, d.radius * 0.6))
    .text(d => d.icon);

  // Node label
  nodeElements.append('text')
    .attr('y', d => d.radius + 16)
    .attr('text-anchor', 'middle')
    .attr('fill', '#e5e7eb')
    .attr('font-size', '10px')
    .attr('font-weight', 'bold')
    .text(d => d.label);

  // Node size label (row count)
  nodeElements.append('text')
    .attr('y', d => d.radius + 28)
    .attr('text-anchor', 'middle')
    .attr('fill', '#9ca3af')
    .attr('font-size', '9px')
    .text(d => d.rowCount ? `${formatCount(d.rowCount)} rows` : '');

  // Simulation tick
  simulation.on('tick', () => {
    linkElements
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y);

    nodeElements
      .attr('transform', d => `translate(${d.x}, ${d.y})`);
  });

  return { svg, simulation, nodes, links };
}

function formatCount(n) {
  if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return String(n);
}
```

## Layer 2: Brain Health Dashboard

### 2.1 Health Monitoring Panel

```javascript
/**
 * Real-time brain health dashboard.
 * Traffic light indicators per brain: 🟢 healthy, 🟡 degraded, 🔴 failed.
 * Metrics: size, row count, last modified, WAL status, integrity.
 */
const HEALTH_THRESHOLDS = {
  sizeGrowth: { warn: 1.5, critical: 2.0 },   // ratio vs expected
  staleDays:  { warn: 7,   critical: 30 },     // days since last modification
  walPages:   { warn: 1000, critical: 10000 },  // uncommitted WAL pages
};

function renderBrainHealthDashboard(container, brainHealthData) {
  const dashboard = d3.select(container)
    .append('div')
    .attr('class', 'brain-health-dashboard')
    .style('display', 'grid')
    .style('grid-template-columns', 'repeat(auto-fill, minmax(300px, 1fr))')
    .style('gap', '12px')
    .style('padding', '16px');

  brainHealthData.forEach(brain => {
    const health = computeHealthStatus(brain);
    const card = dashboard.append('div')
      .attr('class', `brain-health-card health-${health.status}`)
      .style('background', '#1e1e2e')
      .style('border-radius', '10px')
      .style('padding', '14px')
      .style('border', `1px solid ${health.color}`);

    // Header with traffic light
    const header = card.append('div')
      .style('display', 'flex')
      .style('align-items', 'center')
      .style('gap', '8px')
      .style('margin-bottom', '10px');

    header.append('span')
      .style('font-size', '20px')
      .text(brain.icon || '🧠');

    header.append('span')
      .style('color', '#e5e7eb')
      .style('font-weight', 'bold')
      .style('font-size', '13px')
      .style('flex', '1')
      .text(brain.label);

    header.append('span')
      .style('width', '12px')
      .style('height', '12px')
      .style('border-radius', '50%')
      .style('background', health.color)
      .style('box-shadow', `0 0 8px ${health.color}`);

    // Metrics grid
    const metrics = [
      { label: 'Size',     value: formatSize(brain.sizeBytes), icon: '💾' },
      { label: 'Tables',   value: String(brain.tableCount || 0), icon: '📊' },
      { label: 'Rows',     value: formatCount(brain.rowCount || 0), icon: '📝' },
      { label: 'Modified', value: brain.lastModified || 'Unknown', icon: '📅' },
      { label: 'Journal',  value: brain.journalMode || 'Unknown', icon: '📒' },
      { label: 'Tier',     value: brain.tier, icon: brain.tier === 'HOT' ? '🔥' : '❄️' },
    ];

    const metricsGrid = card.append('div')
      .style('display', 'grid')
      .style('grid-template-columns', '1fr 1fr')
      .style('gap', '4px');

    metrics.forEach(m => {
      const row = metricsGrid.append('div')
        .style('display', 'flex')
        .style('justify-content', 'space-between')
        .style('padding', '3px 0');

      row.append('span')
        .style('color', '#9ca3af')
        .style('font-size', '11px')
        .text(`${m.icon} ${m.label}`);

      row.append('span')
        .style('color', '#e5e7eb')
        .style('font-size', '11px')
        .style('font-weight', 'bold')
        .text(m.value);
    });

    // Health warnings
    if (health.warnings.length > 0) {
      const warningBox = card.append('div')
        .style('margin-top', '8px')
        .style('padding', '6px 8px')
        .style('background', health.status === 'failed' ? '#ef444420' : '#f59e0b20')
        .style('border-radius', '6px')
        .style('font-size', '10px')
        .style('color', health.status === 'failed' ? '#ef4444' : '#f59e0b');

      health.warnings.forEach(w => {
        warningBox.append('div').text(`⚠️ ${w}`);
      });
    }
  });

  return dashboard;
}

function computeHealthStatus(brain) {
  const warnings = [];
  let status = 'healthy';
  let color = '#10b981';

  // Check if file accessible
  if (!brain.accessible) {
    return { status: 'failed', color: '#ef4444', warnings: ['Database file not accessible'] };
  }

  // Check stale data
  if (brain.daysSinceModified > HEALTH_THRESHOLDS.staleDays.critical) {
    warnings.push(`Not modified in ${brain.daysSinceModified} days`);
    status = 'failed'; color = '#ef4444';
  } else if (brain.daysSinceModified > HEALTH_THRESHOLDS.staleDays.warn) {
    warnings.push(`Stale: ${brain.daysSinceModified} days since last change`);
    status = 'degraded'; color = '#f59e0b';
  }

  // Check WAL on exFAT (should be DELETE mode)
  if (brain.tier === 'WARM' && brain.journalMode === 'wal') {
    warnings.push('WAL mode on exFAT drive — risk of corruption');
    status = 'failed'; color = '#ef4444';
  }

  // Check size anomaly
  if (brain.expectedSize && brain.sizeBytes) {
    const sizeRatio = brain.sizeBytes / (brain.expectedSize * 1024 * 1024);
    if (sizeRatio > HEALTH_THRESHOLDS.sizeGrowth.critical) {
      warnings.push(`Size ${formatSize(brain.sizeBytes)} is ${sizeRatio.toFixed(1)}× expected`);
      status = 'degraded'; color = '#f59e0b';
    }
  }

  // Check WAL uncommitted pages
  if (brain.walPages > HEALTH_THRESHOLDS.walPages.critical) {
    warnings.push(`${brain.walPages} uncommitted WAL pages — checkpoint needed`);
    status = 'degraded'; color = '#f59e0b';
  }

  // Check integrity
  if (brain.integrityCheck === 'not ok') {
    warnings.push('INTEGRITY CHECK FAILED — database may be corrupt');
    status = 'failed'; color = '#ef4444';
  }

  return { status, color, warnings };
}

function formatSize(bytes) {
  if (!bytes) return '0 B';
  if (bytes >= 1073741824) return `${(bytes / 1073741824).toFixed(1)} GB`;
  if (bytes >= 1048576) return `${(bytes / 1048576).toFixed(1)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${bytes} B`;
}
```

## Layer 3: Inter-Brain Flow Visualization

### 3.1 Animated Flow Particles

```javascript
/**
 * Animated particles flowing along edges showing data movement between brains.
 * Particle speed and density proportional to flow weight.
 * Color matches flow type (ingest=green, feed=blue, synthesis=purple, etc.)
 */
function createFlowParticles(svg, links, simulation) {
  const particleGroup = svg.select('.brain-network')
    .append('g')
    .attr('class', 'flow-particles');

  const particles = [];

  // Spawn particles for each active flow
  links.forEach(link => {
    const count = Math.max(1, link.weight);
    const speed = 0.003 + link.weight * 0.001;
    const color = FLOW_COLORS[link.type] || '#374151';

    for (let i = 0; i < count; i++) {
      particles.push({
        link,
        t: i / count,          // position along edge (0..1)
        speed,
        color,
        radius: 2 + link.weight * 0.3,
        active: true,
      });
    }
  });

  // Render particle dots
  const particleDots = particleGroup.selectAll('circle')
    .data(particles)
    .enter()
    .append('circle')
    .attr('r', d => d.radius)
    .attr('fill', d => d.color)
    .attr('opacity', 0.8);

  // Particle glow trail
  const trailFilter = svg.select('defs')
    .append('filter')
    .attr('id', 'particle-glow');
  trailFilter.append('feGaussianBlur')
    .attr('in', 'SourceGraphic')
    .attr('stdDeviation', '1.5');

  particleDots.attr('filter', 'url(#particle-glow)');

  // Animation loop
  function animateParticles() {
    particles.forEach(p => {
      if (!p.active) return;
      p.t += p.speed;
      if (p.t > 1) p.t -= 1; // loop back
    });

    particleDots
      .attr('cx', d => {
        const src = d.link.source;
        const tgt = d.link.target;
        return src.x + (tgt.x - src.x) * d.t;
      })
      .attr('cy', d => {
        const src = d.link.source;
        const tgt = d.link.target;
        return src.y + (tgt.y - src.y) * d.t;
      });

    requestAnimationFrame(animateParticles);
  }

  animateParticles();
  return { particles, particleDots };
}
```

### 3.2 Flow Rate Indicators

```javascript
/**
 * Edge labels showing flow rate (queries/sec or rows transferred).
 * Visible on hover, positioned at edge midpoint.
 */
function addFlowLabels(svg, links) {
  const labelGroup = svg.select('.brain-network')
    .append('g')
    .attr('class', 'flow-labels');

  const labels = labelGroup.selectAll('g')
    .data(links)
    .enter()
    .append('g')
    .attr('class', 'flow-label')
    .style('opacity', 0)
    .style('pointer-events', 'none');

  labels.append('rect')
    .attr('rx', 4)
    .attr('fill', '#1e1e2e')
    .attr('stroke', d => FLOW_COLORS[d.type] || '#374151')
    .attr('stroke-width', 1);

  labels.append('text')
    .attr('fill', '#e5e7eb')
    .attr('font-size', '9px')
    .attr('text-anchor', 'middle')
    .text(d => d.label);

  // Show on hover
  svg.selectAll('.brain-links line')
    .on('mouseenter', function(event, d) {
      d3.select(`.flow-label:nth-child(${links.indexOf(d) + 1})`)
        .transition()
        .duration(200)
        .style('opacity', 1);
    })
    .on('mouseleave', function(event, d) {
      d3.selectAll('.flow-label')
        .transition()
        .duration(200)
        .style('opacity', 0);
    });

  return labels;
}
```

## Layer 4: Learning Loop Spiral

### 4.1 Evidence Processing Spiral Visualization

```javascript
/**
 * Spiral/helix visualization showing evidence processing stages.
 * Evidence flows through: Ingest → Classify → Atomize → Index →
 * Cross-Reference → Synthesize → File
 * Each stage is a ring on the spiral with particles moving through.
 */
const LEARNING_STAGES = [
  { id: 'ingest',      label: 'Ingest',         color: '#10b981', icon: '📥', radius: 40 },
  { id: 'classify',    label: 'Classify',        color: '#3b82f6', icon: '🏷️', radius: 70 },
  { id: 'atomize',     label: 'Atomize',         color: '#8b5cf6', icon: '⚛️', radius: 100 },
  { id: 'index',       label: 'Index',           color: '#f59e0b', icon: '📇', radius: 130 },
  { id: 'crossref',    label: 'Cross-Reference', color: '#ec4899', icon: '🔗', radius: 160 },
  { id: 'synthesize',  label: 'Synthesize',      color: '#ef4444', icon: '🧬', radius: 190 },
  { id: 'file',        label: 'File',            color: '#06b6d4', icon: '📁', radius: 220 },
];

function renderLearningSpiral(container, stageMetrics, cx, cy) {
  const svg = d3.select(container)
    .append('svg')
    .attr('width', 500)
    .attr('height', 500)
    .attr('viewBox', '0 0 500 500');

  const g = svg.append('g')
    .attr('transform', `translate(${cx || 250}, ${cy || 250})`);

  // Draw concentric rings for each stage
  LEARNING_STAGES.forEach((stage, i) => {
    const metrics = stageMetrics[stage.id] || {};
    const completionPct = metrics.completion || 0;

    // Background ring
    g.append('circle')
      .attr('r', stage.radius)
      .attr('fill', 'none')
      .attr('stroke', '#374151')
      .attr('stroke-width', 8)
      .attr('opacity', 0.3);

    // Progress arc
    const arc = d3.arc()
      .innerRadius(stage.radius - 4)
      .outerRadius(stage.radius + 4)
      .startAngle(0)
      .endAngle(2 * Math.PI * completionPct / 100);

    g.append('path')
      .attr('d', arc)
      .attr('fill', stage.color)
      .attr('opacity', 0.8);

    // Stage label at right side of ring
    const labelAngle = -Math.PI / 4 + (i * Math.PI / 10);
    const lx = (stage.radius + 20) * Math.cos(labelAngle);
    const ly = (stage.radius + 20) * Math.sin(labelAngle);

    g.append('text')
      .attr('x', lx)
      .attr('y', ly)
      .attr('text-anchor', lx > 0 ? 'start' : 'end')
      .attr('fill', stage.color)
      .attr('font-size', '10px')
      .attr('font-weight', 'bold')
      .text(`${stage.icon} ${stage.label} (${completionPct}%)`);

    // Item count at the stage
    if (metrics.count !== undefined) {
      g.append('text')
        .attr('x', lx)
        .attr('y', ly + 14)
        .attr('text-anchor', lx > 0 ? 'start' : 'end')
        .attr('fill', '#9ca3af')
        .attr('font-size', '9px')
        .text(`${formatCount(metrics.count)} items`);
    }
  });

  // Central label
  g.append('text')
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'central')
    .attr('fill', '#e5e7eb')
    .attr('font-size', '14px')
    .attr('font-weight', 'bold')
    .text('Learning Loop');

  // Spiral connector path (Archimedean spiral from center to outer ring)
  const spiralPoints = [];
  const maxR = LEARNING_STAGES[LEARNING_STAGES.length - 1].radius;
  for (let angle = 0; angle < 4 * Math.PI; angle += 0.05) {
    const r = 30 + (maxR - 30) * (angle / (4 * Math.PI));
    spiralPoints.push([r * Math.cos(angle), r * Math.sin(angle)]);
  }

  const spiralLine = d3.line().curve(d3.curveBasisOpen);
  g.append('path')
    .attr('d', spiralLine(spiralPoints))
    .attr('fill', 'none')
    .attr('stroke', '#4b5563')
    .attr('stroke-width', 1)
    .attr('stroke-dasharray', '4,4')
    .attr('opacity', 0.5);

  return svg;
}
```

## Layer 5: Brain Version Timeline

### 5.1 Schema Evolution Timeline

```javascript
/**
 * Timeline showing brain database evolution:
 * table creation dates, major data loads, schema migrations.
 * Horizontal timeline with vertical event markers.
 */
function renderBrainTimeline(container, events, width, height) {
  const margin = { top: 40, right: 40, bottom: 60, left: 40 };
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;

  const svg = d3.select(container)
    .append('svg')
    .attr('width', width)
    .attr('height', height);

  const g = svg.append('g')
    .attr('transform', `translate(${margin.left}, ${margin.top})`);

  const timeExtent = d3.extent(events, d => new Date(d.date));
  const xScale = d3.scaleTime()
    .domain(timeExtent)
    .range([0, innerW]);

  // Category color mapping
  const categoryColors = {
    'table_created':  '#10b981',
    'data_load':      '#3b82f6',
    'schema_change':  '#f59e0b',
    'backup':         '#8b5cf6',
    'migration':      '#ef4444',
    'optimization':   '#06b6d4',
  };

  // Time axis
  g.append('g')
    .attr('transform', `translate(0, ${innerH})`)
    .call(d3.axisBottom(xScale)
      .ticks(d3.timeMonth.every(1))
      .tickFormat(d3.timeFormat('%b %Y')))
    .selectAll('text')
    .attr('fill', '#9ca3af')
    .attr('font-size', '10px')
    .attr('transform', 'rotate(-30)')
    .attr('text-anchor', 'end');

  // Central timeline bar
  g.append('line')
    .attr('x1', 0).attr('y1', innerH / 2)
    .attr('x2', innerW).attr('y2', innerH / 2)
    .attr('stroke', '#4b5563')
    .attr('stroke-width', 2);

  // Event markers (alternating above/below timeline)
  events.forEach((event, i) => {
    const x = xScale(new Date(event.date));
    const above = i % 2 === 0;
    const yBase = innerH / 2;
    const yOffset = above ? -30 - (i % 3) * 25 : 30 + (i % 3) * 25;
    const y = yBase + yOffset;
    const color = categoryColors[event.category] || '#6b7280';

    // Connector line
    g.append('line')
      .attr('x1', x).attr('y1', yBase)
      .attr('x2', x).attr('y2', y)
      .attr('stroke', color)
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '2,2');

    // Event dot
    g.append('circle')
      .attr('cx', x).attr('cy', y)
      .attr('r', 5)
      .attr('fill', color)
      .attr('stroke', '#1e1e2e')
      .attr('stroke-width', 2);

    // Event label
    g.append('text')
      .attr('x', x + 10).attr('y', y + 4)
      .attr('fill', '#e5e7eb')
      .attr('font-size', '9px')
      .text(`${event.brainId}: ${event.description}`);

    // Event dot on timeline
    g.append('circle')
      .attr('cx', x).attr('cy', yBase)
      .attr('r', 3)
      .attr('fill', color);
  });

  return svg;
}
```

## Layer 6: Knowledge Density Heatmap

### 6.1 Brain × Topic Density Grid

```javascript
/**
 * Grid heatmap showing knowledge density per brain per topic area.
 * Rows = brains, Columns = topics (custody, PPO, judicial, etc.)
 * Cell color intensity = row count for that topic in that brain.
 * Identifies sparse areas needing attention (cold spots).
 */
const KNOWLEDGE_TOPICS = [
  'custody', 'parenting_time', 'ppo', 'contempt',
  'judicial_misconduct', 'due_process', 'housing',
  'federal_1983', 'appellate', 'evidence', 'authority',
  'false_allegations', 'impeachment', 'damages',
];

function renderKnowledgeDensityHeatmap(container, densityData, brains) {
  const cellSize = 40;
  const labelWidth = 160;
  const headerHeight = 100;
  const width = labelWidth + KNOWLEDGE_TOPICS.length * cellSize + 40;
  const height = headerHeight + brains.length * cellSize + 40;

  const svg = d3.select(container)
    .append('svg')
    .attr('width', width)
    .attr('height', height);

  const g = svg.append('g')
    .attr('transform', `translate(${labelWidth}, ${headerHeight})`);

  // Determine max density for color scale
  const allValues = Object.values(densityData).flatMap(row =>
    Object.values(row)
  );
  const maxDensity = d3.max(allValues) || 1;

  const colorScale = d3.scaleSequential(d3.interpolateViridis)
    .domain([0, Math.log2(maxDensity + 1)]);

  // Column headers (topics)
  KNOWLEDGE_TOPICS.forEach((topic, j) => {
    svg.append('text')
      .attr('x', labelWidth + j * cellSize + cellSize / 2)
      .attr('y', headerHeight - 10)
      .attr('transform', `rotate(-45, ${labelWidth + j * cellSize + cellSize / 2}, ${headerHeight - 10})`)
      .attr('text-anchor', 'end')
      .attr('fill', '#9ca3af')
      .attr('font-size', '10px')
      .text(topic.replace(/_/g, ' '));
  });

  // Row labels (brains) and cells
  brains.forEach((brain, i) => {
    // Row label
    svg.append('text')
      .attr('x', labelWidth - 8)
      .attr('y', headerHeight + i * cellSize + cellSize / 2 + 4)
      .attr('text-anchor', 'end')
      .attr('fill', brain.color || '#e5e7eb')
      .attr('font-size', '10px')
      .text(`${brain.icon} ${brain.label}`);

    // Cells
    KNOWLEDGE_TOPICS.forEach((topic, j) => {
      const value = (densityData[brain.id] || {})[topic] || 0;
      const logValue = Math.log2(value + 1);

      const cell = g.append('g')
        .attr('transform', `translate(${j * cellSize}, ${i * cellSize})`);

      cell.append('rect')
        .attr('width', cellSize - 2)
        .attr('height', cellSize - 2)
        .attr('rx', 4)
        .attr('fill', value > 0 ? colorScale(logValue) : '#1e1e2e')
        .attr('stroke', '#374151')
        .attr('stroke-width', 0.5);

      // Show count for non-zero cells
      if (value > 0) {
        cell.append('text')
          .attr('x', (cellSize - 2) / 2)
          .attr('y', (cellSize - 2) / 2 + 4)
          .attr('text-anchor', 'middle')
          .attr('fill', logValue > (Math.log2(maxDensity + 1) / 2) ? '#000' : '#fff')
          .attr('font-size', '9px')
          .attr('font-weight', 'bold')
          .text(formatCount(value));
      }

      // Tooltip on hover
      cell.append('title')
        .text(`${brain.label} × ${topic}: ${value} items`);
    });
  });

  // Legend
  const legendWidth = 200;
  const legendX = labelWidth;
  const legendY = height - 25;

  const legendScale = d3.scaleLinear()
    .domain([0, legendWidth])
    .range([0, Math.log2(maxDensity + 1)]);

  for (let x = 0; x < legendWidth; x += 2) {
    svg.append('rect')
      .attr('x', legendX + x)
      .attr('y', legendY)
      .attr('width', 2)
      .attr('height', 10)
      .attr('fill', colorScale(legendScale(x)));
  }

  svg.append('text')
    .attr('x', legendX).attr('y', legendY + 22)
    .attr('fill', '#9ca3af').attr('font-size', '9px')
    .text('0');

  svg.append('text')
    .attr('x', legendX + legendWidth).attr('y', legendY + 22)
    .attr('text-anchor', 'end')
    .attr('fill', '#9ca3af').attr('font-size', '9px')
    .text(formatCount(maxDensity));

  svg.append('text')
    .attr('x', legendX + legendWidth / 2).attr('y', legendY + 22)
    .attr('text-anchor', 'middle')
    .attr('fill', '#9ca3af').attr('font-size', '9px')
    .text('Knowledge Density (log scale)');

  return svg;
}
```

## Layer 7: pywebview Bridge

### 7.1 Python Bridge for Brain Data

```python
"""
pywebview Python bridge for brain network visualization.
Scans 00_SYSTEM/brains/*.db and all registered brain paths.
Gets PRAGMA stats, checks WAL status, computes health.
ALWAYS uses PRAGMA table_info() before querying (Rule 16).
NEVER opens WAL on exFAT (Rule — infrastructure instructions).
"""
import sqlite3
import json
import os
from datetime import datetime, date
from pathlib import Path

class BrainBridge:
    """Python↔JS bridge for brain network visualization."""

    BRAIN_PATHS = {
        'litigation_context': Path(r'C:\Users\andre\LitigationOS\litigation_context.db'),
        'authority_master': Path(r'C:\Users\andre\LitigationOS\09_DATA\authority_master.db'),
        'ec': Path(r'C:\Users\andre\LitigationOS\09_DATA\ec.db'),
        'mcr_rules': Path(r'C:\Users\andre\LitigationOS\mcr_rules.db'),
        'court_forms': Path(r'C:\Users\andre\LitigationOS\court_forms.db'),
        'mbp_brain': Path(r'C:\Users\andre\LitigationOS\mbp_brain.db'),
        'claim_evidence_links': Path(r'C:\Users\andre\LitigationOS\claim_evidence_links.db'),
        'file_catalog': Path(r'C:\Users\andre\LitigationOS\00_SYSTEM\file_catalog.db'),
        'script_forge': Path(r'C:\Users\andre\LitigationOS\script_forge.db'),
        'litigation_lite': Path(r'C:\Users\andre\LitigationOS\09_DATA\litigation_lite.db'),
        'skills_registry': Path(r'C:\Users\andre\LitigationOS\.agents\skills_registry.db'),
    }

    EXFAT_DRIVES = {'J'}

    def _is_exfat(self, path: Path) -> bool:
        """Check if path is on an exFAT drive (no WAL support)."""
        drive = str(path)[0].upper()
        return drive in self.EXFAT_DRIVES

    def _safe_connect(self, db_path: Path) -> sqlite3.Connection:
        """Connect with filesystem-aware journal mode."""
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.execute("PRAGMA busy_timeout=60000")
        conn.execute("PRAGMA cache_size=-32000")
        conn.execute("PRAGMA temp_store=MEMORY")

        if self._is_exfat(db_path):
            conn.execute("PRAGMA journal_mode=DELETE")
            conn.execute("PRAGMA synchronous=FULL")
        else:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")

        conn.row_factory = sqlite3.Row
        return conn

    def _get_table_count(self, conn: sqlite3.Connection) -> int:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM sqlite_master WHERE type='table'"
        ).fetchone()
        return row['cnt']

    def _get_total_rows(self, conn: sqlite3.Connection) -> int:
        """Sum row counts across all tables. Uses fast approximation."""
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'"
        ).fetchall()

        total = 0
        for t in tables:
            try:
                row = conn.execute(
                    f'SELECT COUNT(*) as cnt FROM "{t["name"]}"'
                ).fetchone()
                total += row['cnt']
            except sqlite3.OperationalError:
                pass
        return total

    def _get_wal_pages(self, conn: sqlite3.Connection) -> int:
        try:
            row = conn.execute("PRAGMA wal_checkpoint(PASSIVE)").fetchone()
            return row[1] if row else 0
        except sqlite3.OperationalError:
            return 0

    def _get_journal_mode(self, conn: sqlite3.Connection) -> str:
        row = conn.execute("PRAGMA journal_mode").fetchone()
        return row[0] if row else 'unknown'

    def scan_all_brains(self) -> str:
        """Scan all registered brain databases and return health data."""
        results = []

        # Also scan 00_SYSTEM/brains/ directory
        brains_dir = Path(r'C:\Users\andre\LitigationOS\00_SYSTEM\brains')
        if brains_dir.exists():
            for db_file in brains_dir.glob('*.db'):
                brain_id = db_file.stem
                if brain_id not in self.BRAIN_PATHS:
                    self.BRAIN_PATHS[brain_id] = db_file

        for brain_id, db_path in self.BRAIN_PATHS.items():
            info = {
                'id': brain_id,
                'path': str(db_path),
                'accessible': False,
                'tier': 'WARM' if self._is_exfat(db_path) else 'HOT',
            }

            if not db_path.exists():
                info['error'] = 'File not found'
                results.append(info)
                continue

            try:
                stat = db_path.stat()
                info['sizeBytes'] = stat.st_size
                info['lastModified'] = datetime.fromtimestamp(
                    stat.st_mtime
                ).strftime('%Y-%m-%d %H:%M')
                info['daysSinceModified'] = (
                    date.today() - datetime.fromtimestamp(stat.st_mtime).date()
                ).days
                info['accessible'] = True

                conn = self._safe_connect(db_path)
                info['tableCount'] = self._get_table_count(conn)
                info['rowCount'] = self._get_total_rows(conn)
                info['journalMode'] = self._get_journal_mode(conn)
                info['walPages'] = self._get_wal_pages(conn)

                # Quick integrity check (fast mode)
                try:
                    check = conn.execute(
                        "PRAGMA quick_check(1)"
                    ).fetchone()
                    info['integrityCheck'] = check[0] if check else 'unknown'
                except sqlite3.OperationalError:
                    info['integrityCheck'] = 'skipped'

                conn.close()

            except Exception as e:
                info['error'] = str(e)

            results.append(info)

        return json.dumps(results, default=str)

    def get_brain_tables(self, brain_id: str) -> str:
        """Get table list for a specific brain database."""
        db_path = self.BRAIN_PATHS.get(brain_id)
        if not db_path or not db_path.exists():
            return json.dumps({'error': f'Brain {brain_id} not found'})

        conn = self._safe_connect(db_path)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()

        result = []
        for t in tables:
            tname = t['name']
            try:
                cols = conn.execute(f'PRAGMA table_info("{tname}")').fetchall()
                cnt = conn.execute(
                    f'SELECT COUNT(*) as cnt FROM "{tname}"'
                ).fetchone()
                result.append({
                    'name': tname,
                    'columns': [c['name'] for c in cols],
                    'column_count': len(cols),
                    'row_count': cnt['cnt'],
                })
            except sqlite3.OperationalError as e:
                result.append({
                    'name': tname,
                    'error': str(e),
                })

        conn.close()
        return json.dumps(result, default=str)

    def get_knowledge_density(self) -> str:
        """Compute knowledge density per brain per topic for the heatmap."""
        topics = [
            'custody', 'parenting_time', 'ppo', 'contempt',
            'judicial_misconduct', 'due_process', 'housing',
            'federal_1983', 'appellate', 'evidence', 'authority',
            'false_allegations', 'impeachment', 'damages',
        ]

        density = {}
        main_db = self.BRAIN_PATHS.get('litigation_context')
        if not main_db or not main_db.exists():
            return json.dumps(density)

        conn = self._safe_connect(main_db)

        # Check which FTS tables exist
        tables = {r['name'] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}

        has_evidence_fts = 'evidence_fts' in tables
        has_timeline_fts = 'timeline_fts' in tables

        for brain_id in self.BRAIN_PATHS:
            density[brain_id] = {}
            for topic in topics:
                count = 0
                if brain_id == 'litigation_context':
                    # Count evidence_quotes matching topic
                    if has_evidence_fts:
                        try:
                            import re
                            safe_topic = re.sub(r'[^\w\s*"]', ' ', topic).strip()
                            row = conn.execute(
                                "SELECT COUNT(*) as cnt FROM evidence_fts "
                                "WHERE evidence_fts MATCH ?",
                                (safe_topic,)
                            ).fetchone()
                            count = row['cnt']
                        except sqlite3.OperationalError:
                            # FTS5 fallback to LIKE
                            row = conn.execute(
                                "SELECT COUNT(*) as cnt FROM evidence_quotes "
                                "WHERE quote_text LIKE ?",
                                (f'%{topic}%',)
                            ).fetchone()
                            count = row['cnt']
                    elif 'evidence_quotes' in tables:
                        row = conn.execute(
                            "SELECT COUNT(*) as cnt FROM evidence_quotes "
                            "WHERE quote_text LIKE ?",
                            (f'%{topic}%',)
                        ).fetchone()
                        count = row['cnt']

                density[brain_id][topic] = count

        conn.close()
        return json.dumps(density)

    def get_inter_brain_flows(self) -> str:
        """Return the inter-brain flow definitions for edge rendering."""
        return json.dumps(BRAIN_FLOWS_DATA)


# Flow data matching the JavaScript BRAIN_FLOWS constant
BRAIN_FLOWS_DATA = [
    {'source': 'file_catalog', 'target': 'litigation_context',
     'type': 'ingest', 'weight': 5, 'label': 'File discovery'},
    {'source': 'ocr_master', 'target': 'litigation_context',
     'type': 'ingest', 'weight': 4, 'label': 'OCR text extraction'},
    {'source': 'litigation_context', 'target': 'evidence_brain',
     'type': 'feed', 'weight': 5, 'label': 'Evidence atoms'},
    {'source': 'litigation_context', 'target': 'authority_brain',
     'type': 'feed', 'weight': 5, 'label': 'Authority chains'},
    {'source': 'litigation_context', 'target': 'narrative_brain',
     'type': 'feed', 'weight': 4, 'label': 'Timeline events'},
    {'source': 'litigation_context', 'target': 'interpretation_brain',
     'type': 'feed', 'weight': 4, 'label': 'Legal analysis'},
    {'source': 'litigation_context', 'target': 'mbp_brain',
     'type': 'feed', 'weight': 5, 'label': 'Graph data'},
    {'source': 'evidence_brain', 'target': 'claim_evidence_links',
     'type': 'synthesis', 'weight': 4, 'label': 'Evidence-Claim binding'},
    {'source': 'authority_brain', 'target': 'mcr_rules',
     'type': 'reference', 'weight': 3, 'label': 'Rule lookup'},
    {'source': 'authority_brain', 'target': 'authority_master',
     'type': 'reference', 'weight': 4, 'label': 'Authority validation'},
    {'source': 'narrative_brain', 'target': 'evidence_brain',
     'type': 'query', 'weight': 3, 'label': 'Evidence for narrative'},
    {'source': 'ec', 'target': 'claim_evidence_links',
     'type': 'feed', 'weight': 3, 'label': 'Chain linking'},
]
```

## Layer 8: CSS Styling

### 8.1 Brain Network Styles

```css
/* THEMANBEARPIG Brain Network Layer Styles */

.brain-network-layer {
  font-family: 'JetBrains Mono', 'Cascadia Code', 'Fira Code', monospace;
  background: #0d0d1a;
  color: #e5e7eb;
}

.brain-node {
  transition: filter 0.2s ease;
}

.brain-node:hover {
  filter: brightness(1.3) drop-shadow(0 0 8px currentColor);
}

.brain-node circle {
  transition: r 0.3s ease, opacity 0.3s ease;
}

.brain-node:hover circle:first-child {
  r: calc(attr(r) + 4);
}

.brain-links line {
  transition: stroke-opacity 0.3s ease, stroke-width 0.3s ease;
}

.brain-links line:hover {
  stroke-opacity: 0.9;
  stroke-width: 3;
}

.flow-particle {
  pointer-events: none;
}

.brain-health-card {
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.brain-health-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
}

.brain-health-card.health-healthy {
  border-left: 3px solid #10b981;
}

.brain-health-card.health-degraded {
  border-left: 3px solid #f59e0b;
  animation: glow-warn 3s ease-in-out infinite;
}

.brain-health-card.health-failed {
  border-left: 3px solid #ef4444;
  animation: glow-error 2s ease-in-out infinite;
}

@keyframes glow-warn {
  0%, 100% { box-shadow: 0 0 4px rgba(245, 158, 11, 0.2); }
  50%      { box-shadow: 0 0 16px rgba(245, 158, 11, 0.4); }
}

@keyframes glow-error {
  0%, 100% { box-shadow: 0 0 4px rgba(239, 68, 68, 0.3); }
  50%      { box-shadow: 0 0 20px rgba(239, 68, 68, 0.5); }
}

.heatmap-cell {
  transition: opacity 0.15s ease;
}

.heatmap-cell:hover {
  opacity: 1 !important;
  stroke: #fff;
  stroke-width: 2;
}

.spiral-ring {
  transition: stroke-width 0.3s ease;
}

.spiral-ring:hover {
  stroke-width: 12;
}

.timeline-event {
  cursor: pointer;
  transition: transform 0.2s ease;
}

.timeline-event:hover {
  transform: scale(1.5);
}

.flow-label {
  pointer-events: none;
  transition: opacity 0.2s ease;
}
```

## Layer 9: Anti-Patterns

### 9.1 Brain Network Anti-Patterns (Mandatory Compliance)

| # | Anti-Pattern | Why It Fails | Correct Approach |
|---|---|---|---|
| 1 | Opening WAL on exFAT drives | No file locking on exFAT → silent corruption | Use DELETE journal mode for J:\ drives |
| 2 | Querying brain DBs without busy_timeout | SQLITE_BUSY under concurrent access | `PRAGMA busy_timeout=60000` on every connection |
| 3 | Assuming schema matches DDL | Pipeline-created tables differ from code DDL | `PRAGMA table_info()` before every first query |
| 4 | Scanning all brains sequentially | 23+ DBs × integrity check = 30+ seconds | Parallel scan with ThreadPoolExecutor(max_workers=4) |
| 5 | Keeping brain connections open indefinitely | Connection leaks exhaust file descriptors | Context manager or explicit close after scan |
| 6 | Rendering all 23+ brain nodes simultaneously | Force sim thrashes with >20 nodes visible | LOD: show tier groups, expand on click |
| 7 | Animating >100 flow particles | requestAnimationFrame budget exceeded | Cap at 50 particles, batch updates |
| 8 | Computing row counts with full table scans | Slow on million-row tables | Use `sqlite_stat1` estimates when available |
| 9 | Hardcoding brain file paths | Breaks portability between machines | Use registry pattern with path resolution |
| 10 | Running integrity_check(full) on large DBs | 10+ minutes on litigation_context.db (1.3 GB) | Use quick_check(1) for health dashboard |
| 11 | Displaying raw file paths in visualization | Exposes machine-specific paths | Show brain label + tier only in UI |
| 12 | Missing error handling on DB open | Missing/locked DBs crash the whole layer | Try/catch with graceful degradation per brain |
| 13 | Rebuilding force simulation on every data refresh | Jarring layout jumps | Update node data in-place, alpha reheat only |
| 14 | Using module-level DB connections | Stdout clobbering, import side effects | Lazy init in @property or factory method |
| 15 | Polling brain health every second | CPU waste, disk I/O for no benefit | Poll every 60 seconds or on user action |
| 16 | Logging brain scan results to stdout | Corrupts pywebview JSON bridge | Use stderr or log file only |

### 9.2 Data Integrity Rules

- NEVER write to brain databases from the visualization layer — read-only scanning only
- NEVER display raw SQL or file paths to the user in the pywebview UI
- NEVER assume a brain database has any specific tables — always introspect first
- NEVER cache brain health data for more than 120 seconds — staleness hides real problems
- ALWAYS close database connections after scanning — open connections block WAL checkpoints
- ALWAYS handle missing brains gracefully — some may be on disconnected USB drives

## Layer 10: Performance Budgets

### 10.1 Target Times

| Operation | Budget | Technique |
|---|---|---|
| Full brain scan (23+ DBs) | < 5s total | Parallel ThreadPoolExecutor, quick_check only |
| Single brain health check | < 200ms | PRAGMA quick_check(1), no full integrity |
| Force simulation init | < 300ms | Pre-positioned nodes by tier, low alpha |
| Force simulation settle | < 2s | alphaDecay=0.02, velocityDecay=0.3 |
| Flow particle render | < 2ms/frame | Canvas fallback for >50 particles |
| Heatmap render | < 150ms | Pre-computed density, batch rect inserts |
| Spiral render | < 100ms | Static arcs, animation via CSS |
| Timeline render | < 200ms | Pre-sorted events, clip off-screen |
| Knowledge density query | < 3s | FTS5 for main DB, skip WARM tier |
| Brain topology refresh | < 500ms | Diff-based update, reuse DOM nodes |
| Node hover highlight | < 8ms | CSS class toggle, no reflow |
| Edge hover label | < 5ms | Pre-rendered, toggle visibility |

### 10.2 Memory Budgets

| Resource | Budget | Notes |
|---|---|---|
| Brain node DOM elements | < 60 | ~3 elements per brain (ring + fill + label) |
| Flow particles | ≤ 50 | Cap regardless of edge count |
| Heatmap cells | < 400 | 23 brains × 14 topics = 322 cells |
| Open DB connections | ≤ 3 concurrent | Close after scan, reopen on demand |
| Cached health data | < 500 KB | JSON serialized scan results |
| Timeline events | < 200 | Filter to significant events only |

## Layer 11: Integration with Other MBP Skills

### 11.1 Cross-Skill Data Flow

```
MBP-DATAWEAVE ──brain_registry──→ BRAIN TOPOLOGY
MBP-INTEGRATION-ENGINES ──engine_status──→ BRAIN HEALTH (engines use brains)
MBP-INTERFACE-HUD ──health_gauge──→ HUD PANEL (brain health summary)
MBP-COMBAT-EVIDENCE ──evidence_density──→ KNOWLEDGE HEATMAP
MBP-COMBAT-AUTHORITY ──authority_density──→ KNOWLEDGE HEATMAP
MBP-EMERGENCE-CONVERGENCE ──convergence_score──→ LEARNING SPIRAL
MBP-FORGE-RENDERER ──render_pipeline──→ ALL VISUALIZATIONS
MBP-GENESIS ──layer_config──→ LAYER REGISTRATION
MBP-INTEGRATION-FILING ──filing_data──→ BRAIN FLOW (filing_readiness queries)
```

### 11.2 Layer Registration

```javascript
/**
 * Register the Brain Network layer with THEMANBEARPIG layer system.
 * Layer 11 in the 13-layer architecture.
 */
const BRAIN_NETWORK_LAYER = {
  id: 'brain-network',
  name: 'Brain Network',
  order: 11,
  icon: '🧠',
  color: '#ec4899',
  visible: true,
  interactive: true,

  init(graphState) {
    this.bridge = graphState.bridges.brain;
    this.brainData = [];
    this.flowData = [];
    this.healthData = [];
    this._lastScan = 0;
  },

  async load() {
    const [brains, flows] = await Promise.all([
      this.bridge.scan_all_brains(),
      this.bridge.get_inter_brain_flows(),
    ]);
    this.brainData = JSON.parse(brains);
    this.flowData = JSON.parse(flows);
    this._lastScan = Date.now();
  },

  render(container) {
    const width = 1200;
    const height = 800;

    // Merge registry metadata with scan data
    const enrichedBrains = this.brainData.map(scan => {
      const reg = BRAIN_REGISTRY.find(r => r.id === scan.id) || {};
      return { ...reg, ...scan };
    });

    const { svg, simulation } = createBrainNetwork(
      container, enrichedBrains, this.flowData, width, height
    );
    createFlowParticles(svg, simulation.force('link').links(), simulation);
    addFlowLabels(svg, simulation.force('link').links());

    // Health dashboard below the network
    renderBrainHealthDashboard(container, enrichedBrains);
  },

  async update(delta) {
    // Refresh brain health every 60 seconds
    if (Date.now() - this._lastScan > 60000) {
      await this.load();
      this._lastScan = Date.now();
    }
  },

  destroy() {
    this.brainData = [];
    this.flowData = [];
  },
};
```

---
name: SINGULARITY-MBP-INTEGRATION-FILING
description: "Filing pipeline F1-F10 Kanban visualization, EGCP scoring radar, deadline timeline with urgency alerts, packet assembly status, and filing readiness dashboard for THEMANBEARPIG 13-layer graph."
version: "1.0.0"
tier: "TIER-4/INTEGRATION"
domain: "Filing pipeline visualization — Kanban board, EGCP scoring, deadline tracking, packet assembly, readiness dashboard"
triggers:
  - filing pipeline
  - F1-F10
  - Kanban
  - EGCP
  - deadline
  - packet
  - readiness
  - filing status
  - filing dashboard
  - packet assembly
cross_links:
  - SINGULARITY-MBP-GENESIS
  - SINGULARITY-MBP-DATAWEAVE
  - SINGULARITY-MBP-INTERFACE-HUD
  - SINGULARITY-MBP-INTERFACE-TIMELINE
  - SINGULARITY-MBP-COMBAT-EVIDENCE
  - SINGULARITY-MBP-COMBAT-AUTHORITY
  - SINGULARITY-MBP-INTEGRATION-ENGINES
  - SINGULARITY-MBP-FORGE-RENDERER
---

# SINGULARITY-MBP-INTEGRATION-FILING v1.0

> **The filing pipeline as a living, breathing Kanban war board. Every filing from DRAFT to DOCKETED, tracked in real-time with EGCP scoring and deadline countdowns.**

## Layer 1: Filing Pipeline Kanban Board

### 1.1 Kanban Column Architecture

The Kanban board maps directly to the filing state machine:
`DRAFT → QA_REVIEW → SERVICE_READY → FILED → DOCKETED → MONITORING`

```javascript
/**
 * THEMANBEARPIG Filing Pipeline Kanban Board
 * D3.js drag-and-drop Kanban with lane-colored cards, confidence gauges,
 * and real-time deadline countdowns.
 */

const KANBAN_COLUMNS = [
  { id: 'DRAFT',         label: 'Draft',         color: '#6b7280', icon: '📝' },
  { id: 'QA_REVIEW',     label: 'QA Review',     color: '#f59e0b', icon: '🔍' },
  { id: 'SERVICE_READY', label: 'Service Ready', color: '#3b82f6', icon: '📬' },
  { id: 'FILED',         label: 'Filed',         color: '#8b5cf6', icon: '📁' },
  { id: 'DOCKETED',      label: 'Docketed',      color: '#10b981', icon: '✅' },
  { id: 'MONITORING',    label: 'Monitoring',    color: '#06b6d4', icon: '👁️' }
];

const LANE_COLORS = {
  A: '#ef4444', // Custody — red
  B: '#f97316', // Housing — orange
  C: '#8b5cf6', // Federal — purple
  D: '#ec4899', // PPO — pink
  E: '#f59e0b', // Judicial — amber
  F: '#3b82f6', // Appellate — blue
};

const LANE_LABELS = {
  A: 'Custody (2024-001507-DC)',
  B: 'Housing (2025-002760-CZ)',
  C: 'Federal (42 USC §1983)',
  D: 'PPO (2023-5907-PP)',
  E: 'Judicial (JTC/MSC)',
  F: 'Appellate (COA 366810)',
};

function createKanbanBoard(container, filingData) {
  const svg = d3.select(container)
    .append('svg')
    .attr('width', '100%')
    .attr('height', '100%')
    .attr('viewBox', '0 0 1920 1080');

  const columnWidth = 280;
  const columnGap = 20;
  const headerHeight = 60;
  const cardHeight = 140;
  const cardGap = 12;
  const startX = 40;
  const startY = 80;

  // Column backgrounds
  const columns = svg.selectAll('.kanban-column')
    .data(KANBAN_COLUMNS)
    .enter()
    .append('g')
    .attr('class', 'kanban-column')
    .attr('transform', (d, i) => `translate(${startX + i * (columnWidth + columnGap)}, ${startY})`);

  columns.append('rect')
    .attr('width', columnWidth)
    .attr('height', 900)
    .attr('rx', 12)
    .attr('fill', '#1e1e2e')
    .attr('stroke', d => d.color)
    .attr('stroke-width', 2)
    .attr('opacity', 0.85);

  // Column headers
  columns.append('text')
    .attr('x', columnWidth / 2)
    .attr('y', 30)
    .attr('text-anchor', 'middle')
    .attr('fill', d => d.color)
    .attr('font-size', '16px')
    .attr('font-weight', 'bold')
    .text(d => `${d.icon} ${d.label}`);

  // Column count badges
  columns.append('text')
    .attr('x', columnWidth / 2)
    .attr('y', 52)
    .attr('text-anchor', 'middle')
    .attr('fill', '#9ca3af')
    .attr('font-size', '12px')
    .text(d => {
      const count = filingData.filter(f => f.status === d.id).length;
      return `${count} filing${count !== 1 ? 's' : ''}`;
    });

  return { svg, columns };
}
```

### 1.2 Filing Card Renderer

Each card shows the filing name, lane, confidence score, deadline countdown, and component status.

```javascript
/**
 * Render a single filing card inside the Kanban column.
 * Cards are color-coded by lane and show mini EGCP gauges.
 */
function renderFilingCard(parent, filing, index) {
  const cardY = 70 + index * (140 + 12);
  const cardWidth = 256;
  const cardHeight = 140;
  const laneColor = LANE_COLORS[filing.lane] || '#6b7280';

  const card = parent.append('g')
    .attr('class', `filing-card filing-${filing.id}`)
    .attr('transform', `translate(12, ${cardY})`)
    .style('cursor', 'grab')
    .call(d3.drag()
      .on('start', onDragStart)
      .on('drag', onDragMove)
      .on('end', onDragEnd));

  // Card background with lane accent
  card.append('rect')
    .attr('width', cardWidth)
    .attr('height', cardHeight)
    .attr('rx', 8)
    .attr('fill', '#2a2a3e')
    .attr('stroke', laneColor)
    .attr('stroke-width', 1.5);

  // Lane color bar (left edge)
  card.append('rect')
    .attr('width', 5)
    .attr('height', cardHeight)
    .attr('rx', 2)
    .attr('fill', laneColor);

  // Filing name
  card.append('text')
    .attr('x', 16)
    .attr('y', 22)
    .attr('fill', '#e5e7eb')
    .attr('font-size', '13px')
    .attr('font-weight', 'bold')
    .text(truncate(filing.vehicle_name || filing.name, 30));

  // Lane badge
  card.append('rect')
    .attr('x', cardWidth - 36)
    .attr('y', 8)
    .attr('width', 28)
    .attr('height', 20)
    .attr('rx', 4)
    .attr('fill', laneColor)
    .attr('opacity', 0.8);

  card.append('text')
    .attr('x', cardWidth - 22)
    .attr('y', 22)
    .attr('text-anchor', 'middle')
    .attr('fill', '#fff')
    .attr('font-size', '11px')
    .attr('font-weight', 'bold')
    .text(filing.lane);

  // Confidence gauge (mini arc)
  const confidence = filing.confidence || 0;
  const gaugeX = 40;
  const gaugeY = 65;
  const gaugeR = 22;
  const gaugeColor = confidence >= 80 ? '#10b981' :
                     confidence >= 50 ? '#f59e0b' : '#ef4444';

  const arc = d3.arc()
    .innerRadius(gaugeR - 5)
    .outerRadius(gaugeR)
    .startAngle(-Math.PI * 0.75)
    .endAngle(-Math.PI * 0.75 + (Math.PI * 1.5 * confidence / 100));

  card.append('path')
    .attr('transform', `translate(${gaugeX}, ${gaugeY})`)
    .attr('d', arc)
    .attr('fill', gaugeColor);

  // Confidence percentage text
  card.append('text')
    .attr('x', gaugeX)
    .attr('y', gaugeY + 5)
    .attr('text-anchor', 'middle')
    .attr('fill', gaugeColor)
    .attr('font-size', '12px')
    .attr('font-weight', 'bold')
    .text(`${confidence}%`);

  // Deadline countdown
  const daysLeft = filing.days_until_deadline;
  const deadlineColor = daysLeft < 0 ? '#ef4444' :
                        daysLeft <= 3 ? '#f97316' :
                        daysLeft <= 7 ? '#f59e0b' : '#10b981';

  card.append('text')
    .attr('x', 110)
    .attr('y', 56)
    .attr('fill', deadlineColor)
    .attr('font-size', '11px')
    .text(daysLeft < 0 ? `🔴 ${Math.abs(daysLeft)}d OVERDUE` :
          daysLeft <= 3 ? `🟠 ${daysLeft}d left` :
          daysLeft <= 7 ? `🟡 ${daysLeft}d left` :
          daysLeft !== null ? `🟢 ${daysLeft}d left` : 'No deadline');

  // Component status icons
  const components = filing.components || {};
  const compX = 16;
  const compY = 105;
  const statuses = [
    { key: 'motion',    label: 'Mot' },
    { key: 'brief',     label: 'Brf' },
    { key: 'affidavit', label: 'Aff' },
    { key: 'exhibits',  label: 'Exh' },
    { key: 'cos',       label: 'COS' },
    { key: 'order',     label: 'Ord' },
  ];

  statuses.forEach((comp, i) => {
    const status = components[comp.key];
    const icon = status === 'complete' ? '✅' :
                 status === 'in_progress' ? '⏳' : '❌';
    card.append('text')
      .attr('x', compX + i * 40)
      .attr('y', compY)
      .attr('fill', '#9ca3af')
      .attr('font-size', '10px')
      .text(`${icon}${comp.label}`);
  });

  // Evidence count badge
  card.append('text')
    .attr('x', 110)
    .attr('y', 75)
    .attr('fill', '#9ca3af')
    .attr('font-size', '10px')
    .text(`📄 ${filing.evidence_count || 0} evidence · ⚖️ ${filing.authority_count || 0} auth`);

  return card;
}

function truncate(str, max) {
  if (!str) return '';
  return str.length > max ? str.slice(0, max - 1) + '…' : str;
}
```

### 1.3 Drag-and-Drop State Transitions

```javascript
/**
 * Kanban drag-and-drop handlers.
 * Cards can be dragged between columns to update filing status.
 * Validates transitions (no skipping columns).
 */
const VALID_TRANSITIONS = {
  'DRAFT':         ['QA_REVIEW'],
  'QA_REVIEW':     ['DRAFT', 'SERVICE_READY'],
  'SERVICE_READY': ['QA_REVIEW', 'FILED'],
  'FILED':         ['DOCKETED'],
  'DOCKETED':      ['MONITORING'],
  'MONITORING':    [],
};

let dragState = { filing: null, startX: 0, startY: 0, originCol: null };

function onDragStart(event, d) {
  dragState.filing = d;
  dragState.startX = event.x;
  dragState.startY = event.y;
  dragState.originCol = d.status;
  d3.select(this).raise().style('cursor', 'grabbing');
  d3.select(this).select('rect').attr('stroke-width', 3);
}

function onDragMove(event, d) {
  const dx = event.x - dragState.startX;
  const dy = event.y - dragState.startY;
  d3.select(this).attr('transform', function() {
    const current = d3.select(this).attr('transform');
    const match = current.match(/translate\(([^,]+),\s*([^)]+)\)/);
    if (match) {
      return `translate(${parseFloat(match[1]) + dx}, ${parseFloat(match[2]) + dy})`;
    }
    return current;
  });
  dragState.startX = event.x;
  dragState.startY = event.y;

  highlightDropTargets(event, d);
}

function onDragEnd(event, d) {
  d3.select(this).style('cursor', 'grab');
  d3.select(this).select('rect').attr('stroke-width', 1.5);

  const targetCol = getDropTarget(event);
  if (targetCol && VALID_TRANSITIONS[dragState.originCol]?.includes(targetCol)) {
    transitionFiling(d, targetCol);
  } else {
    snapBack(d3.select(this), d);
  }
  clearDropHighlights();
}

function transitionFiling(filing, newStatus) {
  filing.status = newStatus;
  // Persist via pywebview bridge
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.update_filing_status(filing.id, newStatus);
  }
  rebuildKanban();
}

function highlightDropTargets(event, filing) {
  const validTargets = VALID_TRANSITIONS[filing.status] || [];
  d3.selectAll('.kanban-column rect')
    .attr('stroke-width', function(d) {
      return validTargets.includes(d.id) ? 3 : 2;
    })
    .attr('stroke-dasharray', function(d) {
      return validTargets.includes(d.id) ? '8,4' : 'none';
    });
}

function clearDropHighlights() {
  d3.selectAll('.kanban-column rect')
    .attr('stroke-width', 2)
    .attr('stroke-dasharray', 'none');
}

function getDropTarget(event) {
  const columnWidth = 280;
  const columnGap = 20;
  const startX = 40;
  const x = event.sourceEvent.clientX;

  for (let i = 0; i < KANBAN_COLUMNS.length; i++) {
    const colX = startX + i * (columnWidth + columnGap);
    if (x >= colX && x <= colX + columnWidth) {
      return KANBAN_COLUMNS[i].id;
    }
  }
  return null;
}

function snapBack(selection, filing) {
  // Animate card back to original position
  selection.transition()
    .duration(300)
    .ease(d3.easeBackOut)
    .attr('transform', selection.attr('data-origin-transform'));
}
```

## Layer 2: EGCP Scoring Visualization

### 2.1 EGCP Diamond/Radar Chart

EGCP = Evidence, Gaps, Confidence, Priority. Four axes rendered as a diamond radar chart per filing.

```javascript
/**
 * EGCP radar/diamond chart per filing.
 * Axes: Evidence (count/coverage), Gaps (inverse — fewer gaps = higher),
 * Confidence (readiness %), Priority (urgency score).
 */
const EGCP_AXES = [
  { key: 'evidence',   label: 'Evidence',   angle: 0,           color: '#10b981' },
  { key: 'gaps',       label: 'Gaps',       angle: Math.PI / 2, color: '#ef4444' },
  { key: 'confidence', label: 'Confidence', angle: Math.PI,     color: '#3b82f6' },
  { key: 'priority',   label: 'Priority',   angle: 3 * Math.PI / 2, color: '#f59e0b' },
];

function renderEGCPDiamond(container, filing, cx, cy, radius) {
  const g = container.append('g')
    .attr('class', `egcp-diamond egcp-${filing.id}`)
    .attr('transform', `translate(${cx}, ${cy})`);

  // Background grid rings (25%, 50%, 75%, 100%)
  [0.25, 0.5, 0.75, 1.0].forEach(level => {
    const points = EGCP_AXES.map(axis => {
      const r = radius * level;
      return [
        r * Math.cos(axis.angle - Math.PI / 2),
        r * Math.sin(axis.angle - Math.PI / 2)
      ];
    });
    g.append('polygon')
      .attr('points', points.map(p => p.join(',')).join(' '))
      .attr('fill', 'none')
      .attr('stroke', '#374151')
      .attr('stroke-width', 0.5)
      .attr('opacity', 0.5);
  });

  // Axis lines
  EGCP_AXES.forEach(axis => {
    const endX = radius * Math.cos(axis.angle - Math.PI / 2);
    const endY = radius * Math.sin(axis.angle - Math.PI / 2);
    g.append('line')
      .attr('x1', 0).attr('y1', 0)
      .attr('x2', endX).attr('y2', endY)
      .attr('stroke', '#4b5563')
      .attr('stroke-width', 1);
  });

  // Data polygon
  const scores = {
    evidence:   Math.min(filing.evidence_score || 0, 100) / 100,
    gaps:       Math.min(filing.gap_score || 0, 100) / 100,
    confidence: Math.min(filing.confidence || 0, 100) / 100,
    priority:   Math.min(filing.priority_score || 0, 100) / 100,
  };

  const dataPoints = EGCP_AXES.map(axis => {
    const r = radius * scores[axis.key];
    return [
      r * Math.cos(axis.angle - Math.PI / 2),
      r * Math.sin(axis.angle - Math.PI / 2)
    ];
  });

  const readiness = (scores.evidence + scores.gaps + scores.confidence + scores.priority) / 4;
  const fillColor = readiness >= 0.75 ? '#10b98133' :
                    readiness >= 0.50 ? '#f59e0b33' : '#ef444433';
  const strokeColor = readiness >= 0.75 ? '#10b981' :
                      readiness >= 0.50 ? '#f59e0b' : '#ef4444';

  g.append('polygon')
    .attr('points', dataPoints.map(p => p.join(',')).join(' '))
    .attr('fill', fillColor)
    .attr('stroke', strokeColor)
    .attr('stroke-width', 2)
    .attr('opacity', 0)
    .transition()
    .duration(800)
    .ease(d3.easeElasticOut.amplitude(1).period(0.4))
    .attr('opacity', 1);

  // Data point dots
  EGCP_AXES.forEach((axis, i) => {
    g.append('circle')
      .attr('cx', dataPoints[i][0])
      .attr('cy', dataPoints[i][1])
      .attr('r', 4)
      .attr('fill', axis.color)
      .attr('stroke', '#1e1e2e')
      .attr('stroke-width', 2);
  });

  // Axis labels
  EGCP_AXES.forEach(axis => {
    const labelR = radius + 18;
    const lx = labelR * Math.cos(axis.angle - Math.PI / 2);
    const ly = labelR * Math.sin(axis.angle - Math.PI / 2);
    g.append('text')
      .attr('x', lx).attr('y', ly)
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'middle')
      .attr('fill', axis.color)
      .attr('font-size', '11px')
      .attr('font-weight', 'bold')
      .text(axis.label);
  });

  // Center readiness score
  g.append('text')
    .attr('x', 0).attr('y', 2)
    .attr('text-anchor', 'middle')
    .attr('fill', strokeColor)
    .attr('font-size', '16px')
    .attr('font-weight', 'bold')
    .text(`${Math.round(readiness * 100)}%`);

  return g;
}
```

### 2.2 EGCP Score Transition Animations

```javascript
/**
 * Animate EGCP diamond transitions when scores update.
 * Morphs the data polygon from old shape to new shape.
 */
function animateEGCPUpdate(container, filingId, newScores) {
  const diamond = container.select(`.egcp-${filingId}`);
  if (diamond.empty()) return;

  const radius = 60;
  const newPoints = EGCP_AXES.map(axis => {
    const r = radius * Math.min(newScores[axis.key] || 0, 100) / 100;
    return [
      r * Math.cos(axis.angle - Math.PI / 2),
      r * Math.sin(axis.angle - Math.PI / 2)
    ];
  });

  diamond.select('polygon:nth-of-type(5)')
    .transition()
    .duration(600)
    .ease(d3.easeCubicInOut)
    .attr('points', newPoints.map(p => p.join(',')).join(' '));

  // Pulse the center score
  const readiness = Object.values(newScores).reduce((a, b) => a + b, 0) / (4 * 100);
  diamond.select('text:last-of-type')
    .transition()
    .duration(200)
    .attr('font-size', '22px')
    .transition()
    .duration(400)
    .attr('font-size', '16px')
    .text(`${Math.round(readiness * 100)}%`);
}
```

## Layer 3: Deadline Timeline

### 3.1 Horizontal Deadline Timeline

```javascript
/**
 * Horizontal timeline showing all filing deadlines.
 * Past deadlines on left, future on right. Today marker in center.
 * Color-coded urgency: 🔴 overdue, 🟠 ≤3 days, 🟡 ≤7 days, 🟢 OK
 */
function renderDeadlineTimeline(container, deadlines, width, height) {
  const margin = { top: 40, right: 60, bottom: 40, left: 60 };
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;

  const svg = d3.select(container)
    .append('svg')
    .attr('width', width)
    .attr('height', height);

  const g = svg.append('g')
    .attr('transform', `translate(${margin.left}, ${margin.top})`);

  const today = new Date();
  const timeRange = d3.extent(deadlines, d => new Date(d.due_date));
  const minDate = d3.timeDay.offset(
    d3.min([today, timeRange[0] || today]), -14);
  const maxDate = d3.timeDay.offset(
    d3.max([today, timeRange[1] || today]), 30);

  const xScale = d3.scaleTime()
    .domain([minDate, maxDate])
    .range([0, innerW]);

  // Timeline axis
  const xAxis = d3.axisBottom(xScale)
    .ticks(d3.timeWeek.every(1))
    .tickFormat(d3.timeFormat('%b %d'));

  g.append('g')
    .attr('transform', `translate(0, ${innerH / 2 + 30})`)
    .call(xAxis)
    .selectAll('text')
    .attr('fill', '#9ca3af')
    .attr('font-size', '10px');

  // Today marker
  const todayX = xScale(today);
  g.append('line')
    .attr('x1', todayX).attr('y1', 0)
    .attr('x2', todayX).attr('y2', innerH)
    .attr('stroke', '#60a5fa')
    .attr('stroke-width', 2)
    .attr('stroke-dasharray', '6,3');

  g.append('text')
    .attr('x', todayX).attr('y', -8)
    .attr('text-anchor', 'middle')
    .attr('fill', '#60a5fa')
    .attr('font-size', '12px')
    .attr('font-weight', 'bold')
    .text('TODAY');

  // Deadline markers
  deadlines.forEach((deadline, i) => {
    const dueDate = new Date(deadline.due_date);
    const daysLeft = Math.ceil((dueDate - today) / (1000 * 60 * 60 * 24));
    const x = xScale(dueDate);
    const y = 20 + (i % 4) * 50;

    const urgencyColor = daysLeft < 0  ? '#ef4444' :
                         daysLeft <= 3 ? '#f97316' :
                         daysLeft <= 7 ? '#f59e0b' : '#10b981';

    const urgencyIcon = daysLeft < 0  ? '🔴' :
                        daysLeft <= 3 ? '🟠' :
                        daysLeft <= 7 ? '🟡' : '🟢';

    // Connection line to axis
    g.append('line')
      .attr('x1', x).attr('y1', y + 12)
      .attr('x2', x).attr('y2', innerH / 2 + 25)
      .attr('stroke', urgencyColor)
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '3,2')
      .attr('opacity', 0.6);

    // Deadline diamond marker
    const diamond = g.append('g')
      .attr('transform', `translate(${x}, ${y})`);

    diamond.append('polygon')
      .attr('points', '0,-10 10,0 0,10 -10,0')
      .attr('fill', urgencyColor)
      .attr('stroke', '#1e1e2e')
      .attr('stroke-width', 1.5);

    // Filing label
    diamond.append('text')
      .attr('x', 16).attr('y', 0)
      .attr('dominant-baseline', 'middle')
      .attr('fill', '#e5e7eb')
      .attr('font-size', '11px')
      .text(`${urgencyIcon} ${truncate(deadline.name, 20)}`);

    // Days countdown
    diamond.append('text')
      .attr('x', 16).attr('y', 14)
      .attr('fill', urgencyColor)
      .attr('font-size', '10px')
      .attr('font-weight', 'bold')
      .text(daysLeft < 0 ? `${Math.abs(daysLeft)}d overdue!` :
            daysLeft === 0 ? 'DUE TODAY!' :
            `${daysLeft}d remaining`);

    // Pulsing alert for critical deadlines (overdue or ≤3 days)
    if (daysLeft <= 3) {
      diamond.append('circle')
        .attr('r', 18)
        .attr('fill', 'none')
        .attr('stroke', urgencyColor)
        .attr('stroke-width', 2)
        .attr('opacity', 0.8)
        .append('animate')
        .attr('attributeName', 'r')
        .attr('values', '14;22;14')
        .attr('dur', '1.5s')
        .attr('repeatCount', 'indefinite');

      diamond.select('circle')
        .append('animate')
        .attr('attributeName', 'opacity')
        .attr('values', '0.8;0.2;0.8')
        .attr('dur', '1.5s')
        .attr('repeatCount', 'indefinite');
    }
  });

  return svg;
}
```

### 3.2 Deadline Countdown Timers

```javascript
/**
 * Live countdown timers that tick every second for critical deadlines.
 * Updates the HUD panel with remaining time in d:hh:mm:ss format.
 */
function startDeadlineCountdowns(deadlines) {
  const criticalDeadlines = deadlines.filter(d => {
    const days = Math.ceil((new Date(d.due_date) - new Date()) / 86400000);
    return days >= -7 && days <= 14;
  });

  function updateCountdowns() {
    const now = new Date();
    criticalDeadlines.forEach(dl => {
      const diff = new Date(dl.due_date) - now;
      const el = document.getElementById(`countdown-${dl.id}`);
      if (!el) return;

      if (diff <= 0) {
        const overdue = Math.abs(diff);
        const d = Math.floor(overdue / 86400000);
        const h = Math.floor((overdue % 86400000) / 3600000);
        el.textContent = `OVERDUE: ${d}d ${h}h`;
        el.style.color = '#ef4444';
      } else {
        const d = Math.floor(diff / 86400000);
        const h = Math.floor((diff % 86400000) / 3600000);
        const m = Math.floor((diff % 3600000) / 60000);
        const s = Math.floor((diff % 60000) / 1000);
        el.textContent = `${d}d ${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
        el.style.color = d <= 3 ? '#f97316' : d <= 7 ? '#f59e0b' : '#10b981';
      }
    });
    requestAnimationFrame(updateCountdowns);
  }

  requestAnimationFrame(updateCountdowns);
}
```

## Layer 4: Packet Assembly Status

### 4.1 Packet Component Checklist

```javascript
/**
 * Visual checklist per filing showing component completion.
 * Interactive — click to mark components complete.
 */
const PACKET_COMPONENTS = [
  { key: 'motion',        label: 'Motion',         icon: '📋', required: true },
  { key: 'brief',         label: 'Brief/Memo',     icon: '📝', required: false },
  { key: 'affidavit',     label: 'Affidavit',      icon: '✍️',  required: true },
  { key: 'exhibit_index', label: 'Exhibit Index',   icon: '📑', required: true },
  { key: 'exhibits',      label: 'Exhibits',        icon: '📎', required: true },
  { key: 'proposed_order',label: 'Proposed Order',   icon: '⚖️',  required: false },
  { key: 'cos',           label: 'Cert of Service', icon: '📬', required: true },
  { key: 'fee_waiver',    label: 'Fee Waiver (MC20)',icon: '💰', required: false },
];

const COMPONENT_STATES = {
  complete:    { icon: '✅', color: '#10b981', label: 'Complete' },
  in_progress: { icon: '⏳', color: '#f59e0b', label: 'In Progress' },
  not_started: { icon: '❌', color: '#ef4444', label: 'Not Started' },
  not_needed:  { icon: '⬜', color: '#6b7280', label: 'Not Needed' },
};

function renderPacketAssembly(container, filing) {
  const components = filing.components || {};
  const wrapper = container.append('div')
    .attr('class', 'packet-assembly')
    .style('background', '#1e1e2e')
    .style('border-radius', '12px')
    .style('padding', '16px');

  // Header
  wrapper.append('h3')
    .style('color', LANE_COLORS[filing.lane] || '#e5e7eb')
    .style('margin', '0 0 12px 0')
    .text(`📦 ${filing.vehicle_name || filing.name}`);

  // Progress bar
  const totalRequired = PACKET_COMPONENTS.filter(c => c.required).length;
  const completedRequired = PACKET_COMPONENTS.filter(c =>
    c.required && components[c.key] === 'complete'
  ).length;
  const progress = totalRequired > 0 ? completedRequired / totalRequired : 0;

  const progressBar = wrapper.append('div')
    .style('background', '#374151')
    .style('height', '8px')
    .style('border-radius', '4px')
    .style('margin-bottom', '12px')
    .style('overflow', 'hidden');

  progressBar.append('div')
    .style('width', `${progress * 100}%`)
    .style('height', '100%')
    .style('background', progress >= 1.0 ? '#10b981' :
                          progress >= 0.5 ? '#f59e0b' : '#ef4444')
    .style('border-radius', '4px')
    .style('transition', 'width 0.5s ease');

  wrapper.append('div')
    .style('color', '#9ca3af')
    .style('font-size', '11px')
    .style('margin-bottom', '8px')
    .text(`${completedRequired}/${totalRequired} required components complete (${Math.round(progress * 100)}%)`);

  // Component list
  PACKET_COMPONENTS.forEach(comp => {
    const status = components[comp.key] || 'not_started';
    const state = COMPONENT_STATES[status] || COMPONENT_STATES.not_started;

    const row = wrapper.append('div')
      .style('display', 'flex')
      .style('align-items', 'center')
      .style('padding', '6px 8px')
      .style('margin-bottom', '4px')
      .style('border-radius', '6px')
      .style('background', status === 'complete' ? '#10b98110' : 'transparent')
      .style('cursor', 'pointer');

    row.append('span')
      .style('margin-right', '8px')
      .style('font-size', '14px')
      .text(state.icon);

    row.append('span')
      .style('flex', '1')
      .style('color', state.color)
      .style('font-size', '13px')
      .text(`${comp.icon} ${comp.label}`);

    if (comp.required) {
      row.append('span')
        .style('color', '#ef4444')
        .style('font-size', '9px')
        .style('padding', '2px 6px')
        .style('background', '#ef444420')
        .style('border-radius', '4px')
        .text('REQUIRED');
    }

    row.append('span')
      .style('color', '#6b7280')
      .style('font-size', '11px')
      .text(state.label);
  });

  return wrapper;
}
```

## Layer 5: Filing Readiness Dashboard

### 5.1 Aggregate Readiness Grid

```javascript
/**
 * Aggregate filing readiness dashboard across all lanes.
 * Shows readiness scores, evidence counts, authority completeness,
 * impeachment availability per filing.
 */
function renderReadinessDashboard(container, filings) {
  const grid = container.append('div')
    .attr('class', 'readiness-dashboard')
    .style('display', 'grid')
    .style('grid-template-columns', 'repeat(auto-fill, minmax(320px, 1fr))')
    .style('gap', '16px')
    .style('padding', '16px');

  filings.forEach(filing => {
    const card = grid.append('div')
      .style('background', '#1e1e2e')
      .style('border', `1px solid ${LANE_COLORS[filing.lane] || '#374151'}`)
      .style('border-radius', '12px')
      .style('padding', '16px');

    // Filing header
    card.append('div')
      .style('display', 'flex')
      .style('justify-content', 'space-between')
      .style('margin-bottom', '12px')
      .html(`
        <span style="color: ${LANE_COLORS[filing.lane]}; font-weight: bold;">
          Lane ${filing.lane}: ${filing.vehicle_name || filing.name}
        </span>
        <span style="color: ${filing.confidence >= 80 ? '#10b981' :
                               filing.confidence >= 50 ? '#f59e0b' : '#ef4444'};
               font-weight: bold; font-size: 20px;">
          ${filing.confidence || 0}%
        </span>
      `);

    // Metric rows
    const metrics = [
      { label: 'Evidence Quotes',     value: filing.evidence_count || 0,   target: 20,  icon: '📄' },
      { label: 'Authority Chains',    value: filing.authority_count || 0,  target: 10,  icon: '⚖️' },
      { label: 'Impeachment Items',   value: filing.impeachment_count || 0, target: 5, icon: '🎯' },
      { label: 'Contradictions',      value: filing.contradiction_count || 0, target: 3, icon: '⚡' },
      { label: 'Timeline Events',     value: filing.timeline_count || 0,  target: 15,  icon: '📅' },
    ];

    metrics.forEach(m => {
      const pct = Math.min(m.value / m.target, 1.0);
      const color = pct >= 1.0 ? '#10b981' : pct >= 0.5 ? '#f59e0b' : '#ef4444';

      const row = card.append('div')
        .style('margin-bottom', '8px');

      row.append('div')
        .style('display', 'flex')
        .style('justify-content', 'space-between')
        .style('margin-bottom', '2px')
        .html(`
          <span style="color: #9ca3af; font-size: 12px;">${m.icon} ${m.label}</span>
          <span style="color: ${color}; font-size: 12px; font-weight: bold;">
            ${m.value}/${m.target}
          </span>
        `);

      const bar = row.append('div')
        .style('background', '#374151')
        .style('height', '4px')
        .style('border-radius', '2px')
        .style('overflow', 'hidden');

      bar.append('div')
        .style('width', `${pct * 100}%`)
        .style('height', '100%')
        .style('background', color)
        .style('border-radius', '2px');
    });
  });

  return grid;
}
```

## Layer 6: pywebview Bridge

### 6.1 Python Bridge for Filing Data

```python
"""
pywebview Python bridge for filing pipeline data.
Queries filing_readiness, filing_packages, deadlines tables
from litigation_context.db.
ALWAYS uses PRAGMA table_info() before querying (Rule 16).
"""
import sqlite3
import json
from datetime import date, datetime
from pathlib import Path

class FilingBridge:
    """Python↔JS bridge for filing pipeline visualization."""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = str(Path(__file__).parent / 'litigation_context.db')
        self.db_path = db_path
        self._conn = None

    @property
    def conn(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.execute("PRAGMA busy_timeout=60000")
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA cache_size=-32000")
            self._conn.execute("PRAGMA temp_store=MEMORY")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _get_columns(self, table_name: str) -> set:
        """Rule 16: Schema-verify before querying."""
        rows = self.conn.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()
        return {row['name'] for row in rows}

    def _table_exists(self, table_name: str) -> bool:
        row = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM sqlite_master "
            "WHERE type='table' AND name=?", (table_name,)
        ).fetchone()
        return row['cnt'] > 0

    def get_filing_pipeline(self) -> str:
        """Get all filings with status, lane, confidence, and component info."""
        filings = []

        if self._table_exists('filing_readiness'):
            cols = self._get_columns('filing_readiness')
            select_cols = []
            if 'vehicle_name' in cols: select_cols.append('vehicle_name')
            if 'lane' in cols: select_cols.append('lane')
            if 'status' in cols: select_cols.append('status')
            if 'confidence' in cols: select_cols.append('confidence')
            if 'evidence_count' in cols: select_cols.append('evidence_count')
            if 'authority_count' in cols: select_cols.append('authority_count')
            if 'impeachment_count' in cols: select_cols.append('impeachment_count')

            if select_cols:
                sql = f"SELECT {', '.join(select_cols)} FROM filing_readiness"
                rows = self.conn.execute(sql).fetchall()
                filings = [dict(r) for r in rows]

        # Enrich with deadline data
        if self._table_exists('deadlines'):
            dcols = self._get_columns('deadlines')
            for filing in filings:
                vname = filing.get('vehicle_name', '')
                if 'vehicle_name' in dcols and 'due_date' in dcols:
                    dl = self.conn.execute(
                        "SELECT due_date FROM deadlines "
                        "WHERE vehicle_name = ? ORDER BY due_date ASC LIMIT 1",
                        (vname,)
                    ).fetchone()
                    if dl:
                        due = datetime.strptime(dl['due_date'], '%Y-%m-%d').date()
                        filing['due_date'] = dl['due_date']
                        filing['days_until_deadline'] = (due - date.today()).days

        return json.dumps(filings, default=str)

    def get_deadlines(self) -> str:
        """Get all deadlines with urgency classification."""
        if not self._table_exists('deadlines'):
            return json.dumps([])

        cols = self._get_columns('deadlines')
        rows = self.conn.execute(
            "SELECT * FROM deadlines ORDER BY due_date ASC"
        ).fetchall()

        deadlines = []
        for r in rows:
            dl = dict(r)
            if 'due_date' in dl and dl['due_date']:
                try:
                    due = datetime.strptime(dl['due_date'], '%Y-%m-%d').date()
                    days_left = (due - date.today()).days
                    dl['days_left'] = days_left
                    dl['urgency'] = (
                        'overdue' if days_left < 0 else
                        'critical' if days_left <= 3 else
                        'urgent' if days_left <= 7 else
                        'ok'
                    )
                except (ValueError, TypeError):
                    dl['days_left'] = None
                    dl['urgency'] = 'unknown'
            deadlines.append(dl)

        return json.dumps(deadlines, default=str)

    def get_packet_status(self, vehicle_name: str) -> str:
        """Get packet assembly status for a specific filing."""
        if not self._table_exists('filing_packages'):
            return json.dumps({})

        cols = self._get_columns('filing_packages')
        if 'vehicle_name' not in cols:
            return json.dumps({})

        rows = self.conn.execute(
            "SELECT * FROM filing_packages WHERE vehicle_name = ?",
            (vehicle_name,)
        ).fetchall()

        return json.dumps([dict(r) for r in rows], default=str)

    def update_filing_status(self, filing_id: str, new_status: str) -> str:
        """Update filing status in the pipeline."""
        valid_statuses = {
            'DRAFT', 'QA_REVIEW', 'SERVICE_READY',
            'FILED', 'DOCKETED', 'MONITORING'
        }
        if new_status not in valid_statuses:
            return json.dumps({'ok': False, 'error': f'Invalid status: {new_status}'})

        if not self._table_exists('filing_readiness'):
            return json.dumps({'ok': False, 'error': 'filing_readiness table not found'})

        cols = self._get_columns('filing_readiness')
        if 'status' not in cols or 'vehicle_name' not in cols:
            return json.dumps({'ok': False, 'error': 'Required columns missing'})

        self.conn.execute(
            "UPDATE filing_readiness SET status = ? WHERE vehicle_name = ?",
            (new_status, filing_id)
        )
        self.conn.commit()

        # Verify write (Rule 19)
        verify = self.conn.execute(
            "SELECT status FROM filing_readiness WHERE vehicle_name = ?",
            (filing_id,)
        ).fetchone()

        return json.dumps({
            'ok': True,
            'verified_status': verify['status'] if verify else None
        })

    def get_separation_days(self) -> str:
        """Compute separation days dynamically (Rule 29)."""
        anchor = date(2025, 7, 29)
        days = (date.today() - anchor).days
        return json.dumps({
            'days': days,
            'weeks': round(days / 7, 1),
            'months': round(days / 30.44, 1),
            'anchor_date': '2025-07-29',
            'computed_at': datetime.now().isoformat()
        })
```

## Layer 7: CSS Styling

### 7.1 Filing Pipeline Styles

```css
/* THEMANBEARPIG Filing Pipeline Layer Styles */

.filing-pipeline-layer {
  font-family: 'JetBrains Mono', 'Cascadia Code', 'Fira Code', monospace;
  background: #0d0d1a;
  color: #e5e7eb;
}

.kanban-board {
  display: flex;
  gap: 16px;
  padding: 20px;
  overflow-x: auto;
  min-height: 600px;
}

.kanban-column {
  min-width: 280px;
  background: #1e1e2e;
  border-radius: 12px;
  border: 1px solid #374151;
}

.kanban-column.drop-target {
  border-color: #60a5fa;
  border-style: dashed;
  box-shadow: 0 0 20px rgba(96, 165, 250, 0.15);
}

.filing-card {
  cursor: grab;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.filing-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
}

.filing-card.dragging {
  cursor: grabbing;
  opacity: 0.85;
  transform: scale(1.03);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
  z-index: 1000;
}

.egcp-diamond {
  transition: transform 0.3s ease;
}

.egcp-diamond:hover {
  transform: scale(1.1);
}

.deadline-marker {
  transition: transform 0.2s ease;
}

.deadline-marker:hover {
  transform: scale(1.3);
}

.deadline-marker.overdue {
  animation: pulse-red 1.5s ease-in-out infinite;
}

.deadline-marker.critical {
  animation: pulse-orange 2s ease-in-out infinite;
}

@keyframes pulse-red {
  0%, 100% { filter: drop-shadow(0 0 4px #ef4444); }
  50%      { filter: drop-shadow(0 0 16px #ef4444); }
}

@keyframes pulse-orange {
  0%, 100% { filter: drop-shadow(0 0 4px #f97316); }
  50%      { filter: drop-shadow(0 0 12px #f97316); }
}

.readiness-card {
  background: #1e1e2e;
  border-radius: 12px;
  border: 1px solid #374151;
  padding: 16px;
  transition: border-color 0.3s ease;
}

.readiness-card:hover {
  border-color: #60a5fa;
}

.progress-bar {
  height: 6px;
  background: #374151;
  border-radius: 3px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease-out;
}

.packet-checklist-item {
  display: flex;
  align-items: center;
  padding: 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s ease;
}

.packet-checklist-item:hover {
  background: #374151;
}

.countdown-timer {
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.05em;
}
```

## Layer 8: Anti-Patterns

### 8.1 Filing Pipeline Anti-Patterns (Mandatory Compliance)

| # | Anti-Pattern | Why It Fails | Correct Approach |
|---|---|---|---|
| 1 | Displaying AI scoring in court documents | Rule 3: Strip ALL AI/DB refs | EGCP is internal only; filings use plain language |
| 2 | Hardcoding day counts in deadline display | Rule 29: Stale counts = FAIL | Always `(today - due_date).days` at render time |
| 3 | Showing CRIMINAL lane mixed with A-F | Rule 7: 100% separate | CRIMINAL lane is NEVER shown on the Kanban board |
| 4 | Rendering child's full name on cards | MCR 8.119(H): initials only | Always "L.D.W." in any visible text |
| 5 | Querying without PRAGMA table_info first | Rule 16: Schema-verify | Call `_get_columns()` before every query |
| 6 | Opening WAL connections on exFAT drives | J:\ has no file locking | DELETE journal mode for J:\ databases |
| 7 | Displaying fabricated statistics | Rule 20: Traceable stats | Every number maps to a specific DB query |
| 8 | Showing "Emily A. Watson" on cards | Rule 5: Correct name format | Use "Emily A. Watson" (per defendant naming rule) |
| 9 | Skipping DB write verification | Rule 19: Verify every write | SELECT after INSERT/UPDATE to confirm |
| 10 | Running FTS5 without sanitization | Rule 15: FTS5 safety | `re.sub(r'[^\w\s*"]', ' ', query)` before MATCH |
| 11 | Using PowerShell for data extraction | Tier S/A tools preferred | Use `exec_python` or bridge methods |
| 12 | Placing DB connections at module level | Engine safety rules | Lazy init in `@property` or `__init__` |
| 13 | Rendering >100 cards without virtualization | Causes frame drops | Virtual scroll: only render visible cards |
| 14 | Polling deadlines with setInterval | Drift and battery drain | Use requestAnimationFrame for countdowns |
| 15 | Drag events without throttling | >60 events/sec on fast mice | Throttle drag handler to 16ms (60fps) |
| 16 | Storing filing status only in JS state | Lost on refresh | Persist via pywebview bridge to SQLite |

### 8.2 Data Integrity Rules

- NEVER display a readiness score without querying the actual evidence_count, authority_count, and impeachment_count from the database
- NEVER cache deadline data for more than 60 seconds — deadlines are time-sensitive
- NEVER allow drag-and-drop to skip states (DRAFT → FILED is invalid)
- NEVER show confidence scores without showing the component breakdown that produces them
- ALWAYS compute separation days dynamically: `(today - date(2025, 7, 29)).days`

## Layer 9: Performance Budgets

### 9.1 Target Frame Times

| Operation | Budget | Technique |
|---|---|---|
| Kanban initial render | < 200ms | Pre-sort filings by status, batch DOM inserts |
| Card drag frame | < 16ms (60fps) | Throttle drag events, use transform not layout |
| EGCP diamond render | < 50ms per chart | Pre-calculate arc paths, cache axis geometry |
| EGCP score animation | < 600ms total | d3.transition with easeElasticOut |
| Deadline timeline render | < 150ms | Pre-sort by date, clip off-screen markers |
| Countdown timer tick | < 1ms per update | textContent only, no DOM restructuring |
| Packet checklist render | < 30ms per filing | HTML string concatenation, single innerHTML |
| Readiness dashboard | < 300ms for all lanes | Grid layout, CSS transitions for bars |
| DB query (filing_readiness) | < 50ms | Indexed columns, prepared statements |
| DB query (deadlines) | < 30ms | date index on due_date column |
| Full board rebuild | < 500ms | Diff-based update, reuse existing DOM nodes |
| Drop target highlight | < 8ms | CSS class toggle only, no reflow |

### 9.2 Memory Budgets

| Resource | Budget | Notes |
|---|---|---|
| Kanban DOM nodes | < 500 | Virtual scroll if >30 filings per column |
| EGCP SVG paths | < 200 | One diamond per visible filing |
| Deadline markers | < 100 | Clip off-screen markers |
| Filing data cache | < 2 MB | Refresh every 60s from DB |
| Countdown timers | < 20 active | Only critical/urgent deadlines get live timers |

## Layer 10: Data Pipeline SQL

### 10.1 Filing Pipeline Queries

```sql
-- Filing readiness overview (always PRAGMA table_info first)
PRAGMA table_info(filing_readiness);

-- Get all filings with status and scores
SELECT
  vehicle_name,
  lane,
  status,
  confidence,
  evidence_count,
  authority_count,
  impeachment_count,
  contradiction_count
FROM filing_readiness
ORDER BY
  CASE status
    WHEN 'DRAFT' THEN 1
    WHEN 'QA_REVIEW' THEN 2
    WHEN 'SERVICE_READY' THEN 3
    WHEN 'FILED' THEN 4
    WHEN 'DOCKETED' THEN 5
    WHEN 'MONITORING' THEN 6
    ELSE 7
  END,
  lane ASC;

-- Deadlines with urgency classification
SELECT
  d.id,
  d.vehicle_name AS name,
  d.due_date,
  d.description,
  d.status,
  julianday(d.due_date) - julianday('now') AS days_left,
  CASE
    WHEN julianday(d.due_date) - julianday('now') < 0 THEN 'overdue'
    WHEN julianday(d.due_date) - julianday('now') <= 3 THEN 'critical'
    WHEN julianday(d.due_date) - julianday('now') <= 7 THEN 'urgent'
    ELSE 'ok'
  END AS urgency
FROM deadlines d
WHERE d.status != 'COMPLETE'
ORDER BY d.due_date ASC;

-- Filing package component status
SELECT
  fp.vehicle_name,
  fp.component_type,
  fp.component_status,
  fp.file_path,
  fp.last_updated
FROM filing_packages fp
ORDER BY fp.vehicle_name, fp.component_type;

-- Cross-table filing enrichment (evidence + authority + impeachment counts per lane)
SELECT
  fr.vehicle_name,
  fr.lane,
  fr.confidence,
  (SELECT COUNT(*) FROM evidence_quotes eq
   WHERE eq.lane = fr.lane AND eq.is_duplicate = 0) AS live_evidence_count,
  (SELECT COUNT(*) FROM authority_chains_v2 ac
   WHERE ac.lane = fr.lane) AS live_authority_count,
  (SELECT COUNT(*) FROM impeachment_matrix im
   WHERE im.filing_relevance LIKE '%' || fr.lane || '%') AS live_impeachment_count
FROM filing_readiness fr
ORDER BY fr.lane;
```

## Layer 11: Integration with Other MBP Skills

### 11.1 Cross-Skill Data Flow

```
MBP-COMBAT-EVIDENCE ──evidence_count──→ FILING READINESS
MBP-COMBAT-AUTHORITY ──authority_count──→ FILING READINESS
MBP-COMBAT-IMPEACHMENT ──impeachment_count──→ FILING READINESS
MBP-INTERFACE-TIMELINE ──deadline_events──→ DEADLINE TIMELINE
MBP-INTERFACE-HUD ──readiness_gauge──→ HUD PANEL
MBP-INTEGRATION-ENGINES ──engine_status──→ PACKET ASSEMBLY
MBP-DATAWEAVE ──filing_data──→ KANBAN CARDS
MBP-GENESIS ──layer_config──→ LAYER REGISTRATION
MBP-FORGE-RENDERER ──render_pipeline──→ ALL VISUALIZATIONS
```

### 11.2 Layer Registration

```javascript
/**
 * Register the Filing Pipeline layer with THEMANBEARPIG layer system.
 * Layer 10 in the 13-layer architecture.
 */
const FILING_PIPELINE_LAYER = {
  id: 'filing-pipeline',
  name: 'Filing Pipeline',
  order: 10,
  icon: '📋',
  color: '#8b5cf6',
  visible: true,
  interactive: true,

  init(graphState) {
    this.bridge = graphState.bridges.filing;
    this.filingData = [];
    this.deadlineData = [];
  },

  async load() {
    const [filings, deadlines] = await Promise.all([
      this.bridge.get_filing_pipeline(),
      this.bridge.get_deadlines(),
    ]);
    this.filingData = JSON.parse(filings);
    this.deadlineData = JSON.parse(deadlines);
  },

  render(container) {
    createKanbanBoard(container, this.filingData);
    renderDeadlineTimeline(container, this.deadlineData, 1200, 200);
    renderReadinessDashboard(container, this.filingData);
    startDeadlineCountdowns(this.deadlineData);
  },

  update(delta) {
    // Refresh deadline countdowns — no DOM rebuild needed
  },

  destroy() {
    this.filingData = [];
    this.deadlineData = [];
  },
};
```

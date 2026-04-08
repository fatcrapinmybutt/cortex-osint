---
name: SINGULARITY-MBP-FORGE-PHYSICS
description: "Force simulation, custom litigation forces, collision detection, layout algorithms, and physics optimization for THEMANBEARPIG. Use when: tuning force parameters, creating custom forces (orbital, lane gravity, temporal, conspiracy), switching layouts (radial, hierarchical, timeline, swimlane), Barnes-Hut optimization, Web Worker simulation, constraint systems, node dragging, multi-layout transitions, physics presets, simulation lifecycle."
version: "1.0.0"
tier: "TIER-1/FORGE"
domain: "Force simulation — D3-force, custom forces, collision, layout algorithms, Barnes-Hut, physics presets"
triggers:
  - force
  - simulation
  - charge
  - collision
  - gravity
  - Barnes-Hut
  - orbital
  - layout
  - physics
  - drag
  - pin
  - constraint
  - radial
  - hierarchical
  - timeline layout
  - swimlane
cross_links:
  - SINGULARITY-MBP-GENESIS
  - SINGULARITY-MBP-DATAWEAVE
  - SINGULARITY-MBP-FORGE-RENDERER
  - SINGULARITY-MBP-FORGE-EFFECTS
  - SINGULARITY-MBP-EMERGENCE-CONVERGENCE
  - SINGULARITY-MBP-EMERGENCE-SELFEVOLVE
  - SINGULARITY-MBP-INTERFACE-CONTROLS
data_sources:
  - graph_nodes (from MBP-DATAWEAVE)
  - graph_links (from MBP-DATAWEAVE)
  - LAYER_META (from MBP-GENESIS)
  - localStorage (user physics preferences)
---

# SINGULARITY-MBP-FORGE-PHYSICS

> **The gravitational engine of THEMANBEARPIG. Every node finds its place through forces that mirror the litigation reality — judges exert gravity wells, conspiracies cluster, evidence orbits actors, and timelines flow.**

---

## Domain 1: D3-Force Simulation Architecture

### 1.1 Complete Force Simulation Manager

```javascript
/**
 * PhysicsEngine — manages the D3 force simulation lifecycle for THEMANBEARPIG.
 * Handles 2,500+ nodes at 60fps on AMD Vega 8 (integrated GPU).
 */
class PhysicsEngine {
  constructor(options = {}) {
    this.simulation = null;
    this.nodes = [];
    this.links = [];
    this.pinned = new Set();
    this.activeLayout = 'force';
    this.isRunning = false;
    this.tickCount = 0;
    this.frameTimeBudget = 5; // ms allocated for physics per frame

    // Position buffers — pre-allocated typed arrays for performance
    this.posX = null;
    this.posY = null;
    this.velX = null;
    this.velY = null;

    // Configuration
    this.config = {
      useWorker: options.useWorker ?? true,
      workerThreshold: options.workerThreshold ?? 1000,
      maxVelocity: options.maxVelocity ?? 50,
      boundaryPadding: options.boundaryPadding ?? 50,
      width: options.width ?? 1920,
      height: options.height ?? 1080,
      ...options
    };

    this.worker = null;
    this.preset = 'calm';
    this.listeners = new Map();
  }

  /**
   * Initialize simulation with graph data.
   * @param {Array} nodes — from MBP-DATAWEAVE
   * @param {Array} links — from MBP-DATAWEAVE
   */
  init(nodes, links) {
    this.nodes = nodes;
    this.links = links;

    // Pre-allocate typed arrays for positions/velocities
    const n = nodes.length;
    this.posX = new Float64Array(n);
    this.posY = new Float64Array(n);
    this.velX = new Float64Array(n);
    this.velY = new Float64Array(n);

    // Initialize with warm-start positions if available
    const saved = this._loadPositions();
    nodes.forEach((node, i) => {
      if (saved && saved[node.id]) {
        node.x = saved[node.id].x;
        node.y = saved[node.id].y;
      } else {
        // Distribute by lane for initial spread
        node.x = this._laneX(node.layer) + (Math.random() - 0.5) * 200;
        node.y = this.config.height / 2 + (Math.random() - 0.5) * 400;
      }
      this.posX[i] = node.x;
      this.posY[i] = node.y;
    });

    // Decide: main thread or Web Worker
    if (this.config.useWorker && n > this.config.workerThreshold && typeof Worker !== 'undefined') {
      this._initWorkerSimulation();
    } else {
      this._initMainThreadSimulation();
    }

    this.isRunning = true;
  }

  _laneX(layer) {
    const LANE_POSITIONS = {
      adversary: 0.15, weapons: 0.25, judicial: 0.35,
      evidence: 0.45, authority: 0.55, impeachment: 0.65,
      filing: 0.75, timeline: 0.5, brain: 0.85,
      emergence: 0.5, prediction: 0.5, hud: 0.5, controls: 0.5
    };
    return (LANE_POSITIONS[layer] || 0.5) * this.config.width;
  }

  _initMainThreadSimulation() {
    const preset = PHYSICS_PRESETS[this.preset];

    this.simulation = d3.forceSimulation(this.nodes)
      .force('link', d3.forceLink(this.links)
        .id(d => d.id)
        .distance(d => this._linkDistance(d))
        .strength(d => this._linkStrength(d)))
      .force('charge', d3.forceManyBody()
        .strength(d => this._chargeStrength(d))
        .theta(0.9)
        .distanceMax(500))
      .force('center', d3.forceCenter(
        this.config.width / 2,
        this.config.height / 2).strength(0.02))
      .force('collide', d3.forceCollide()
        .radius(d => (d.radius || 8) + 2)
        .strength(0.7)
        .iterations(2))
      .force('laneGravity', this._forceLaneGravity())
      .force('boundary', this._forceBoundary())
      .alpha(preset.alpha)
      .alphaDecay(0.005)
      .velocityDecay(preset.velocityDecay)
      .on('tick', () => this._onTick())
      .on('end', () => this._onEnd());
  }

  _chargeStrength(d) {
    const base = PHYSICS_PRESETS[this.preset].charge;
    // Judicial nodes have stronger repulsion (gravity wells)
    if (d.type === 'judge' || d.type === 'judicial') return base * 3;
    // Institutions are large
    if (d.type === 'institution') return base * 2;
    // Evidence is light
    if (d.type === 'evidence') return base * 0.5;
    return base;
  }

  _linkDistance(link) {
    const base = PHYSICS_PRESETS[this.preset].linkDistance;
    const TYPE_MULTIPLIERS = {
      family: 0.6, legal: 0.8, conspiracy: 0.5,
      temporal: 1.2, evidence_support: 0.7,
      cross_layer: 1.5, emergence: 2.0
    };
    return base * (TYPE_MULTIPLIERS[link.type] || 1.0);
  }

  _linkStrength(link) {
    const TYPE_STRENGTHS = {
      family: 0.8, legal: 0.6, conspiracy: 0.9,
      temporal: 0.3, evidence_support: 0.5,
      cross_layer: 0.2, emergence: 0.1
    };
    return TYPE_STRENGTHS[link.type] || 0.4;
  }

  _onTick() {
    this.tickCount++;

    // Clamp velocities
    this.nodes.forEach((n, i) => {
      if (this.pinned.has(n.id)) {
        n.vx = 0;
        n.vy = 0;
        return;
      }
      const v = Math.sqrt(n.vx * n.vx + n.vy * n.vy);
      if (v > this.config.maxVelocity) {
        const scale = this.config.maxVelocity / v;
        n.vx *= scale;
        n.vy *= scale;
      }
      // Update typed arrays
      this.posX[i] = n.x;
      this.posY[i] = n.y;
    });

    // Emit tick event for renderer
    this._emit('tick', { tickCount: this.tickCount });
  }

  _onEnd() {
    this.isRunning = false;
    this._savePositions();
    this._emit('settled', { tickCount: this.tickCount });
  }

  // --- Public API ---

  reheat(alpha = 0.3) {
    if (this.simulation) {
      this.simulation.alpha(alpha).restart();
      this.isRunning = true;
    }
  }

  reheatLocal(nodeId, alpha = 0.2, radius = 200) {
    // Only disturb nodes within radius of the target
    const target = this.nodes.find(n => n.id === nodeId);
    if (!target) return;

    this.nodes.forEach(n => {
      const dx = n.x - target.x;
      const dy = n.y - target.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < radius && !this.pinned.has(n.id)) {
        n.vx += (Math.random() - 0.5) * 10;
        n.vy += (Math.random() - 0.5) * 10;
      }
    });
    this.reheat(alpha);
  }

  pinNode(nodeId) {
    const node = this.nodes.find(n => n.id === nodeId);
    if (node) {
      node.fx = node.x;
      node.fy = node.y;
      this.pinned.add(nodeId);
    }
  }

  unpinNode(nodeId) {
    const node = this.nodes.find(n => n.id === nodeId);
    if (node) {
      node.fx = null;
      node.fy = null;
      this.pinned.delete(nodeId);
    }
  }

  setPreset(presetName, transition = true) {
    if (!PHYSICS_PRESETS[presetName]) return;
    const target = PHYSICS_PRESETS[presetName];

    if (transition) {
      this._transitionPreset(this.preset, presetName, 500);
    } else {
      this._applyPreset(target);
    }
    this.preset = presetName;
  }

  stop() {
    if (this.simulation) {
      this.simulation.stop();
      this.isRunning = false;
    }
    if (this.worker) {
      this.worker.terminate();
      this.worker = null;
    }
  }

  destroy() {
    this.stop();
    this._savePositions();
    this.nodes = [];
    this.links = [];
    this.posX = null;
    this.posY = null;
    this.listeners.clear();
  }

  // --- Event System ---

  on(event, callback) {
    if (!this.listeners.has(event)) this.listeners.set(event, []);
    this.listeners.get(event).push(callback);
    return this;
  }

  _emit(event, data) {
    (this.listeners.get(event) || []).forEach(cb => cb(data));
  }

  // --- Persistence ---

  _savePositions() {
    const positions = {};
    this.nodes.forEach(n => {
      positions[n.id] = { x: n.x, y: n.y };
    });
    try {
      localStorage.setItem('mbp_node_positions', JSON.stringify(positions));
    } catch (e) { /* quota exceeded — ignore */ }
  }

  _loadPositions() {
    try {
      const raw = localStorage.getItem('mbp_node_positions');
      return raw ? JSON.parse(raw) : null;
    } catch (e) { return null; }
  }

  _applyPreset(preset) {
    if (!this.simulation) return;
    this.simulation.force('charge').strength(preset.charge);
    this.simulation.force('link').distance(preset.linkDistance);
    this.simulation.velocityDecay(preset.velocityDecay);
    this.simulation.alpha(preset.alpha).restart();
  }

  _transitionPreset(fromName, toName, durationMs) {
    const from = PHYSICS_PRESETS[fromName];
    const to = PHYSICS_PRESETS[toName];
    const startTime = performance.now();

    const step = () => {
      const elapsed = performance.now() - startTime;
      const t = Math.min(elapsed / durationMs, 1);
      const ease = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2; // ease-in-out

      const blended = {
        charge: from.charge + (to.charge - from.charge) * ease,
        linkDistance: from.linkDistance + (to.linkDistance - from.linkDistance) * ease,
        velocityDecay: from.velocityDecay + (to.velocityDecay - from.velocityDecay) * ease,
        alpha: to.alpha
      };
      this._applyPreset(blended);

      if (t < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }
}
```

### 1.2 Physics Presets

```javascript
const PHYSICS_PRESETS = {
  calm: {
    charge: -30,
    linkDistance: 80,
    alpha: 0.3,
    velocityDecay: 0.6,
    description: 'Gentle layout — nodes settle slowly, minimal movement'
  },
  energetic: {
    charge: -100,
    linkDistance: 50,
    alpha: 0.8,
    velocityDecay: 0.3,
    description: 'Active simulation — strong repulsion, fast convergence'
  },
  clustered: {
    charge: -200,
    linkDistance: 30,
    alpha: 0.5,
    velocityDecay: 0.4,
    description: 'Tight clusters — connected nodes pulled close'
  },
  spread: {
    charge: -50,
    linkDistance: 150,
    alpha: 0.3,
    velocityDecay: 0.5,
    description: 'Wide spread — nodes push far apart for readability'
  },
  timeline: {
    charge: -40,
    linkDistance: 100,
    alpha: 0.4,
    velocityDecay: 0.5,
    forceX: 0.3,
    description: 'Timeline mode — horizontal time axis emphasis'
  },
  radial: {
    charge: -60,
    linkDistance: 60,
    alpha: 0.5,
    velocityDecay: 0.4,
    description: 'Radial — concentric rings by importance'
  },
  judicial_gravity: {
    charge: -80,
    linkDistance: 70,
    alpha: 0.6,
    velocityDecay: 0.35,
    description: 'Judicial gravity well — judge nodes as massive attractors'
  },
  conspiracy: {
    charge: -150,
    linkDistance: 40,
    alpha: 0.7,
    velocityDecay: 0.35,
    description: 'Conspiracy clustering — adversary connections tighten dramatically'
  }
};
```

---

## Domain 2: Custom Litigation Forces

### 2.1 Lane Gravity Force

```javascript
/**
 * Pulls nodes toward their assigned case lane region on the X axis.
 * Lane A (Custody) = left, Lane F (Appellate) = right, CRIMINAL = isolated bottom.
 */
function forceLaneGravity(strength = 0.05) {
  let nodes;

  const LANE_TARGETS = {
    'A': 0.12, 'B': 0.25, 'C': 0.75, 'D': 0.38,
    'E': 0.50, 'F': 0.62, 'CRIMINAL': 0.90
  };

  function force(alpha) {
    for (let i = 0; i < nodes.length; i++) {
      const node = nodes[i];
      if (node.fx != null) continue; // skip pinned

      const lane = node.lane || node.layer;
      // Map layer names to lanes
      const mappedLane = LAYER_TO_LANE[lane] || null;
      if (!mappedLane) continue;

      const targetX = LANE_TARGETS[mappedLane];
      if (targetX == null) continue;

      const targetPixelX = targetX * _width;
      node.vx += (targetPixelX - node.x) * strength * alpha;
    }
  }

  let _width = 1920;

  force.initialize = function(n) { nodes = n; };
  force.width = function(w) { _width = w; return force; };
  force.strength = function(s) { strength = s; return force; };

  return force;
}

const LAYER_TO_LANE = {
  'adversary': 'A', 'weapons': 'D', 'judicial': 'E',
  'evidence': 'A', 'authority': 'F', 'impeachment': 'A',
  'filing': 'F', 'timeline': null, 'brain': null,
  'emergence': null, 'hud': null, 'controls': null
};
```

### 2.2 Orbital Force (Actors Orbit Judge)

```javascript
/**
 * Creates orbital paths where party nodes orbit around judicial nodes.
 * Judge McNeill is the primary gravity well — all connected parties orbit her.
 */
function forceOrbital(centerNodeId, orbitRadius = 200, angularVelocity = 0.001) {
  let nodes;
  let centerNode = null;
  let orbiters = [];

  function force(alpha) {
    if (!centerNode) return;
    const cx = centerNode.x || 0;
    const cy = centerNode.y || 0;

    orbiters.forEach((orbiter, i) => {
      if (orbiter.fx != null) return; // skip pinned

      // Compute desired orbital position
      const angle = (performance.now() * angularVelocity) + (i * 2 * Math.PI / orbiters.length);
      const targetX = cx + Math.cos(angle) * orbitRadius;
      const targetY = cy + Math.sin(angle) * orbitRadius;

      // Soft spring toward orbital position
      orbiter.vx += (targetX - orbiter.x) * 0.02 * alpha;
      orbiter.vy += (targetY - orbiter.y) * 0.02 * alpha;
    });
  }

  force.initialize = function(n) {
    nodes = n;
    centerNode = nodes.find(nd => nd.id === centerNodeId);
    // Orbiters = nodes directly linked to center
    orbiters = nodes.filter(nd =>
      nd.id !== centerNodeId &&
      nd._links && nd._links.some(l =>
        l.source === centerNodeId || l.target === centerNodeId ||
        l.source?.id === centerNodeId || l.target?.id === centerNodeId
      )
    );
  };

  force.radius = function(r) { orbitRadius = r; return force; };
  force.speed = function(s) { angularVelocity = s; return force; };

  return force;
}
```

### 2.3 Temporal Force (Chronological Y-Axis)

```javascript
/**
 * Pushes nodes along the Y axis based on their date.
 * Oldest events at top, newest at bottom. Nodes without dates float free.
 */
function forceTemporal(strength = 0.1) {
  let nodes;
  let _height = 1080;
  let _dateRange = null;

  function force(alpha) {
    if (!_dateRange) return;
    const [minDate, maxDate] = _dateRange;
    const range = maxDate - minDate || 1;

    for (let i = 0; i < nodes.length; i++) {
      const node = nodes[i];
      if (node.fx != null) continue;

      const dateVal = node._dateMs;
      if (dateVal == null) continue;

      const normalizedY = ((dateVal - minDate) / range);
      const targetY = 50 + normalizedY * (_height - 100); // 50px top/bottom margin

      node.vy += (targetY - node.y) * strength * alpha;
    }
  }

  force.initialize = function(n) {
    nodes = n;
    // Pre-compute date values
    let min = Infinity, max = -Infinity;
    nodes.forEach(node => {
      const dateStr = node.date || node.event_date;
      if (dateStr) {
        const ms = new Date(dateStr).getTime();
        if (!isNaN(ms)) {
          node._dateMs = ms;
          if (ms < min) min = ms;
          if (ms > max) max = ms;
        }
      }
    });
    _dateRange = (min < Infinity) ? [min, max] : null;
  };

  force.height = function(h) { _height = h; return force; };
  force.strength = function(s) { strength = s; return force; };

  return force;
}
```

### 2.4 Conspiracy Cluster Force

```javascript
/**
 * Connected adversary nodes attract more strongly than normal links.
 * Makes the Berry-McNeill-Watson cartel visually cluster together.
 */
function forceConspiracyCluster(strength = 0.08) {
  let nodes;
  let conspiratorIds = new Set();

  function force(alpha) {
    // Pull conspirators toward their centroid
    const conspirators = nodes.filter(n => conspiratorIds.has(n.id));
    if (conspirators.length < 2) return;

    let cx = 0, cy = 0;
    conspirators.forEach(n => { cx += n.x; cy += n.y; });
    cx /= conspirators.length;
    cy /= conspirators.length;

    conspirators.forEach(n => {
      if (n.fx != null) return;
      n.vx += (cx - n.x) * strength * alpha;
      n.vy += (cy - n.y) * strength * alpha;
    });
  }

  force.initialize = function(n) {
    nodes = n;
    // Auto-detect conspirators: nodes with type 'adversary' or in adversary layer
    conspiratorIds = new Set(
      nodes.filter(nd =>
        nd.type === 'adversary' ||
        nd.layer === 'adversary' ||
        (nd.tags && nd.tags.includes('conspiracy'))
      ).map(nd => nd.id)
    );
  };

  force.addConspirator = function(id) { conspiratorIds.add(id); return force; };
  force.strength = function(s) { strength = s; return force; };

  return force;
}
```

### 2.5 Separation Force (CRIMINAL Lane Isolation)

```javascript
/**
 * Rule 7: CRIMINAL lane is 100% separate. This force ensures CRIMINAL nodes
 * are pushed away from all non-CRIMINAL nodes with strong repulsion.
 */
function forceSeparation(strength = 0.15, minDistance = 300) {
  let nodes;
  let criminalNodes = [];
  let otherNodes = [];

  function force(alpha) {
    for (const cNode of criminalNodes) {
      if (cNode.fx != null) continue;
      for (const oNode of otherNodes) {
        const dx = cNode.x - oNode.x;
        const dy = cNode.y - oNode.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;

        if (dist < minDistance) {
          const push = ((minDistance - dist) / dist) * strength * alpha;
          cNode.vx += dx * push;
          cNode.vy += dy * push;
        }
      }
    }
  }

  force.initialize = function(n) {
    nodes = n;
    criminalNodes = nodes.filter(nd => nd.lane === 'CRIMINAL' || nd.layer === 'criminal');
    otherNodes = nodes.filter(nd => nd.lane !== 'CRIMINAL' && nd.layer !== 'criminal');
  };

  force.minDistance = function(d) { minDistance = d; return force; };
  force.strength = function(s) { strength = s; return force; };

  return force;
}
```

### 2.6 Evidence Magnet Force

```javascript
/**
 * Evidence nodes are attracted to their strongest connected actor.
 * Creates visual clusters of evidence around the people they pertain to.
 */
function forceEvidenceMagnet(strength = 0.04) {
  let nodes;
  let evidenceNodes = [];

  function force(alpha) {
    for (const ev of evidenceNodes) {
      if (ev.fx != null || !ev._magnetTarget) continue;
      const target = ev._magnetTarget;
      ev.vx += (target.x - ev.x) * strength * alpha;
      ev.vy += (target.y - ev.y) * strength * alpha;
    }
  }

  force.initialize = function(n) {
    nodes = n;
    const nodeMap = new Map(nodes.map(nd => [nd.id, nd]));

    evidenceNodes = nodes.filter(nd => nd.type === 'evidence' || nd.layer === 'evidence');
    evidenceNodes.forEach(ev => {
      // Find strongest connected actor
      let bestTarget = null, bestWeight = 0;
      (ev._links || []).forEach(link => {
        const otherId = (link.source?.id || link.source) === ev.id
          ? (link.target?.id || link.target)
          : (link.source?.id || link.source);
        const other = nodeMap.get(otherId);
        if (other && (other.type === 'person' || other.type === 'actor')) {
          const w = link.weight || 1;
          if (w > bestWeight) { bestWeight = w; bestTarget = other; }
        }
      });
      ev._magnetTarget = bestTarget;
    });
  };

  force.strength = function(s) { strength = s; return force; };
  return force;
}
```

### 2.7 Boundary Force

```javascript
/**
 * Keeps all nodes within the viewport bounds.
 * Soft bounce — nodes decelerate and reverse near edges.
 */
function forceBoundary(padding = 50) {
  let nodes;
  let _width = 1920, _height = 1080;

  function force(alpha) {
    const minX = padding, maxX = _width - padding;
    const minY = padding, maxY = _height - padding;
    const bounce = 0.5;

    for (let i = 0; i < nodes.length; i++) {
      const node = nodes[i];
      if (node.fx != null) continue;

      if (node.x < minX) { node.x = minX; node.vx = Math.abs(node.vx) * bounce; }
      if (node.x > maxX) { node.x = maxX; node.vx = -Math.abs(node.vx) * bounce; }
      if (node.y < minY) { node.y = minY; node.vy = Math.abs(node.vy) * bounce; }
      if (node.y > maxY) { node.y = maxY; node.vy = -Math.abs(node.vy) * bounce; }
    }
  }

  force.initialize = function(n) { nodes = n; };
  force.size = function(w, h) { _width = w; _height = h; return force; };
  force.padding = function(p) { padding = p; return force; };

  return force;
}
```

---

## Domain 3: Layout Algorithms

### 3.1 Layout Manager

```javascript
/**
 * Manages multiple layout algorithms and smooth transitions between them.
 */
class LayoutManager {
  constructor(physicsEngine) {
    this.physics = physicsEngine;
    this.currentLayout = 'force';
    this.isTransitioning = false;
    this.layouts = {};

    // Register all layouts
    this.layouts.force = new ForceLayout();
    this.layouts.radial = new RadialLayout();
    this.layouts.hierarchical = new HierarchicalLayout();
    this.layouts.circular = new CircularLayout();
    this.layouts.grid = new GridLayout();
    this.layouts.swimlane = new SwimlaneLayout();
    this.layouts.timeline = new TimelineLayout();
    this.layouts.tree = new TreeLayout();
  }

  /**
   * Switch to a different layout with animated transition.
   * @param {string} layoutName
   * @param {number} duration — transition time in ms (default 500)
   */
  switchTo(layoutName, duration = 500) {
    if (!this.layouts[layoutName] || this.isTransitioning) return;

    const nodes = this.physics.nodes;
    const targetPositions = this.layouts[layoutName].compute(nodes, this.physics.links, {
      width: this.physics.config.width,
      height: this.physics.config.height
    });

    // Pause simulation during transition
    if (this.physics.simulation) {
      this.physics.simulation.stop();
    }

    // Animated lerp from current to target positions
    this.isTransitioning = true;
    const startPositions = nodes.map(n => ({ x: n.x, y: n.y }));
    const startTime = performance.now();

    const animate = () => {
      const elapsed = performance.now() - startTime;
      const t = Math.min(elapsed / duration, 1);
      // Ease-in-out cubic
      const ease = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

      nodes.forEach((node, i) => {
        if (node.fx != null) return; // respect pinned
        const start = startPositions[i];
        const target = targetPositions[i] || start;
        node.x = start.x + (target.x - start.x) * ease;
        node.y = start.y + (target.y - start.y) * ease;
      });

      this.physics._emit('tick', { transition: true });

      if (t < 1) {
        requestAnimationFrame(animate);
      } else {
        this.isTransitioning = false;
        this.currentLayout = layoutName;

        // Restart simulation if going back to force layout
        if (layoutName === 'force') {
          this.physics.reheat(0.3);
        } else {
          // Pin all nodes in non-force layouts
          nodes.forEach(n => { n.fx = n.x; n.fy = n.y; });
        }
        this.physics._emit('layoutChanged', { layout: layoutName });
      }
    };

    requestAnimationFrame(animate);
  }
}
```

### 3.2 Radial Layout

```javascript
class RadialLayout {
  compute(nodes, links, bounds) {
    const { width, height } = bounds;
    const cx = width / 2, cy = height / 2;

    // Sort by importance (descending) — most important at center
    const sorted = [...nodes].sort((a, b) =>
      (b.importance || b.evidence_count || 0) - (a.importance || a.evidence_count || 0)
    );

    // Assign to concentric rings
    const ringCapacities = [1, 6, 12, 24, 48, 96, 192]; // Fibonacci-ish
    const ringRadii = [0, 60, 120, 200, 300, 420, 560];
    let ringIndex = 0, posInRing = 0;

    return sorted.map((node, i) => {
      // Find which ring this node belongs to
      let capacity = ringCapacities[ringIndex] || 192;
      if (posInRing >= capacity && ringIndex < ringRadii.length - 1) {
        ringIndex++;
        posInRing = 0;
        capacity = ringCapacities[ringIndex] || 192;
      }

      const radius = ringRadii[ringIndex] || (560 + (ringIndex - 6) * 80);
      const angle = (posInRing / capacity) * 2 * Math.PI - Math.PI / 2;

      posInRing++;

      return {
        x: cx + Math.cos(angle) * radius,
        y: cy + Math.sin(angle) * radius
      };
    });
  }
}
```

### 3.3 Hierarchical Layout (Dagre-Style)

```javascript
class HierarchicalLayout {
  compute(nodes, links, bounds) {
    const { width, height } = bounds;
    const nodeMap = new Map(nodes.map(n => [n.id, n]));

    // Build adjacency for topological ordering
    const children = new Map();
    const parents = new Map();
    links.forEach(l => {
      const src = l.source?.id || l.source;
      const tgt = l.target?.id || l.target;
      if (!children.has(src)) children.set(src, []);
      children.get(src).push(tgt);
      if (!parents.has(tgt)) parents.set(tgt, []);
      parents.get(tgt).push(src);
    });

    // Find roots (nodes with no parents)
    const roots = nodes.filter(n => !parents.has(n.id) || parents.get(n.id).length === 0);
    if (roots.length === 0) {
      // No clear hierarchy — fall back to importance-based
      const sorted = [...nodes].sort((a, b) => (b.importance || 0) - (a.importance || 0));
      roots.push(sorted[0]);
    }

    // BFS level assignment
    const levels = new Map();
    const queue = roots.map(r => ({ id: r.id, level: 0 }));
    const visited = new Set();

    while (queue.length > 0) {
      const { id, level } = queue.shift();
      if (visited.has(id)) continue;
      visited.add(id);
      levels.set(id, level);

      (children.get(id) || []).forEach(childId => {
        if (!visited.has(childId)) {
          queue.push({ id: childId, level: level + 1 });
        }
      });
    }

    // Assign unvisited nodes to level 0
    nodes.forEach(n => { if (!levels.has(n.id)) levels.set(n.id, 0); });

    // Position by level
    const maxLevel = Math.max(...levels.values(), 0);
    const levelHeight = height / (maxLevel + 2);
    const levelCounts = new Map();

    return nodes.map(node => {
      const level = levels.get(node.id) || 0;
      const count = (levelCounts.get(level) || 0) + 1;
      levelCounts.set(level, count);

      return {
        x: width * (count / (nodes.filter(n => levels.get(n.id) === level).length + 1)),
        y: levelHeight * (level + 1)
      };
    });
  }
}
```

### 3.4 Swimlane Layout

```javascript
class SwimlaneLayout {
  compute(nodes, links, bounds) {
    const { width, height } = bounds;

    const LANES = ['A', 'B', 'C', 'D', 'E', 'F', 'CRIMINAL'];
    const laneWidth = width / (LANES.length + 1);

    // Group nodes by lane
    const laneBuckets = {};
    LANES.forEach(l => { laneBuckets[l] = []; });
    laneBuckets['OTHER'] = [];

    nodes.forEach(n => {
      const lane = n.lane || LAYER_TO_LANE[n.layer] || 'OTHER';
      if (laneBuckets[lane]) {
        laneBuckets[lane].push(n);
      } else {
        laneBuckets['OTHER'].push(n);
      }
    });

    // Position within each lane
    const positions = new Map();
    const allLanes = [...LANES, 'OTHER'];

    allLanes.forEach((lane, laneIdx) => {
      const bucket = laneBuckets[lane] || [];
      const cx = laneWidth * (laneIdx + 0.5);
      const rowHeight = Math.max(30, height / (bucket.length + 1));

      // Sort by date within lane
      bucket.sort((a, b) => {
        const da = a.date || a.event_date || '';
        const db = b.date || b.event_date || '';
        return da.localeCompare(db);
      });

      bucket.forEach((node, i) => {
        positions.set(node.id, {
          x: cx + (Math.random() - 0.5) * laneWidth * 0.6,
          y: rowHeight * (i + 1)
        });
      });
    });

    return nodes.map(n => positions.get(n.id) || { x: width / 2, y: height / 2 });
  }
}
```

### 3.5 Timeline Layout

```javascript
class TimelineLayout {
  compute(nodes, links, bounds) {
    const { width, height } = bounds;

    // Separate dated and undated nodes
    const dated = [];
    const undated = [];

    nodes.forEach(n => {
      const dateStr = n.date || n.event_date;
      if (dateStr) {
        const ms = new Date(dateStr).getTime();
        if (!isNaN(ms)) {
          dated.push({ node: n, ms });
        } else {
          undated.push(n);
        }
      } else {
        undated.push(n);
      }
    });

    // Date range
    const minMs = Math.min(...dated.map(d => d.ms));
    const maxMs = Math.max(...dated.map(d => d.ms));
    const range = maxMs - minMs || 1;
    const margin = 80;

    // Group by actor for Y positioning
    const actorRows = new Map();
    let rowCount = 0;

    const positions = new Map();

    dated.forEach(({ node, ms }) => {
      const actor = node.actor || node.target_actor || node.type || 'unknown';
      if (!actorRows.has(actor)) {
        actorRows.set(actor, rowCount++);
      }
      const row = actorRows.get(actor);
      const x = margin + ((ms - minMs) / range) * (width - 2 * margin);
      const totalRows = Math.max(rowCount, 1);
      const y = margin + (row / totalRows) * (height - 2 * margin);

      positions.set(node.id, { x, y });
    });

    // Undated nodes stacked at the right edge
    undated.forEach((node, i) => {
      positions.set(node.id, {
        x: width - margin,
        y: margin + (i / Math.max(undated.length, 1)) * (height - 2 * margin)
      });
    });

    return nodes.map(n => positions.get(n.id) || { x: width / 2, y: height / 2 });
  }
}
```

### 3.6 Circular Layout

```javascript
class CircularLayout {
  compute(nodes, links, bounds) {
    const { width, height } = bounds;
    const cx = width / 2, cy = height / 2;
    const radius = Math.min(width, height) * 0.4;

    // Group by type for arc segments
    const groups = new Map();
    nodes.forEach(n => {
      const type = n.type || n.layer || 'other';
      if (!groups.has(type)) groups.set(type, []);
      groups.get(type).push(n);
    });

    const totalNodes = nodes.length;
    let globalIndex = 0;

    const positions = new Map();

    groups.forEach((groupNodes, type) => {
      groupNodes.forEach(node => {
        const angle = (globalIndex / totalNodes) * 2 * Math.PI - Math.PI / 2;
        positions.set(node.id, {
          x: cx + Math.cos(angle) * radius,
          y: cy + Math.sin(angle) * radius
        });
        globalIndex++;
      });
    });

    return nodes.map(n => positions.get(n.id) || { x: cx, y: cy });
  }
}
```

### 3.7 Grid Layout

```javascript
class GridLayout {
  compute(nodes, links, bounds) {
    const { width, height } = bounds;
    const n = nodes.length;
    const cols = Math.ceil(Math.sqrt(n * (width / height)));
    const rows = Math.ceil(n / cols);
    const cellW = width / (cols + 1);
    const cellH = height / (rows + 1);

    return nodes.map((node, i) => ({
      x: cellW * ((i % cols) + 1),
      y: cellH * (Math.floor(i / cols) + 1)
    }));
  }
}
```

### 3.8 Force Layout (Default — Delegates to D3)

```javascript
class ForceLayout {
  compute(nodes, links, bounds) {
    // Force layout doesn't pre-compute — it uses the simulation
    // Return current positions as-is (simulation will take over)
    return nodes.map(n => ({ x: n.x || bounds.width / 2, y: n.y || bounds.height / 2 }));
  }
}
```

### 3.9 Tree Layout (Dendrogram)

```javascript
class TreeLayout {
  compute(nodes, links, bounds) {
    const { width, height } = bounds;

    // Build tree from links (find root by most connections)
    const degrees = new Map();
    links.forEach(l => {
      const src = l.source?.id || l.source;
      const tgt = l.target?.id || l.target;
      degrees.set(src, (degrees.get(src) || 0) + 1);
      degrees.set(tgt, (degrees.get(tgt) || 0) + 1);
    });

    // Root = highest degree
    let rootId = nodes[0]?.id;
    let maxDeg = 0;
    degrees.forEach((deg, id) => { if (deg > maxDeg) { maxDeg = deg; rootId = id; } });

    // BFS from root
    const children = new Map();
    links.forEach(l => {
      const src = l.source?.id || l.source;
      const tgt = l.target?.id || l.target;
      if (!children.has(src)) children.set(src, []);
      children.get(src).push(tgt);
    });

    const positions = new Map();
    const visited = new Set();
    const queue = [{ id: rootId, depth: 0, offset: 0.5, span: 1.0 }];

    while (queue.length > 0) {
      const { id, depth, offset, span } = queue.shift();
      if (visited.has(id)) continue;
      visited.add(id);

      positions.set(id, {
        x: offset * width,
        y: (depth + 1) * (height / 10)
      });

      const kids = (children.get(id) || []).filter(k => !visited.has(k));
      kids.forEach((kid, i) => {
        const kidSpan = span / kids.length;
        const kidOffset = offset - span / 2 + kidSpan * (i + 0.5);
        queue.push({ id: kid, depth: depth + 1, offset: kidOffset, span: kidSpan });
      });
    }

    // Unvisited nodes
    nodes.forEach(n => {
      if (!positions.has(n.id)) {
        positions.set(n.id, { x: width / 2, y: height - 50 });
      }
    });

    return nodes.map(n => positions.get(n.id));
  }
}
```

---

## Domain 4: Barnes-Hut Optimization

### 4.1 Quadtree for N-Body Simulation

```javascript
/**
 * Barnes-Hut quadtree for O(n log n) force calculation.
 * Used by D3's forceManyBody internally, but exposed here for custom forces.
 */
class BarnesHutTree {
  constructor(nodes, theta = 0.9) {
    this.theta = theta;
    this.root = null;
    this.build(nodes);
  }

  build(nodes) {
    if (nodes.length === 0) return;

    // Compute bounding box
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    nodes.forEach(n => {
      if (n.x < minX) minX = n.x;
      if (n.x > maxX) maxX = n.x;
      if (n.y < minY) minY = n.y;
      if (n.y > maxY) maxY = n.y;
    });

    const size = Math.max(maxX - minX, maxY - minY) + 1;
    this.root = { x: minX, y: minY, size, mass: 0, cx: 0, cy: 0, children: null, node: null };

    nodes.forEach(n => this._insert(this.root, n));
    this._computeMass(this.root);
  }

  _insert(quad, node) {
    if (quad.node === null && quad.children === null) {
      quad.node = node;
      return;
    }

    if (quad.children === null) {
      // Split
      const halfSize = quad.size / 2;
      quad.children = [
        { x: quad.x, y: quad.y, size: halfSize, mass: 0, cx: 0, cy: 0, children: null, node: null },
        { x: quad.x + halfSize, y: quad.y, size: halfSize, mass: 0, cx: 0, cy: 0, children: null, node: null },
        { x: quad.x, y: quad.y + halfSize, size: halfSize, mass: 0, cx: 0, cy: 0, children: null, node: null },
        { x: quad.x + halfSize, y: quad.y + halfSize, size: halfSize, mass: 0, cx: 0, cy: 0, children: null, node: null }
      ];
      // Re-insert existing node
      if (quad.node) {
        this._insertIntoChild(quad, quad.node);
        quad.node = null;
      }
    }

    this._insertIntoChild(quad, node);
  }

  _insertIntoChild(quad, node) {
    const halfSize = quad.size / 2;
    const midX = quad.x + halfSize;
    const midY = quad.y + halfSize;

    let idx;
    if (node.x < midX) {
      idx = node.y < midY ? 0 : 2;
    } else {
      idx = node.y < midY ? 1 : 3;
    }

    this._insert(quad.children[idx], node);
  }

  _computeMass(quad) {
    if (quad.node) {
      quad.mass = quad.node.mass || 1;
      quad.cx = quad.node.x;
      quad.cy = quad.node.y;
      return;
    }

    if (!quad.children) return;

    let totalMass = 0, totalCX = 0, totalCY = 0;
    quad.children.forEach(child => {
      this._computeMass(child);
      totalMass += child.mass;
      totalCX += child.cx * child.mass;
      totalCY += child.cy * child.mass;
    });

    quad.mass = totalMass;
    quad.cx = totalMass > 0 ? totalCX / totalMass : quad.x + quad.size / 2;
    quad.cy = totalMass > 0 ? totalCY / totalMass : quad.y + quad.size / 2;
  }

  /**
   * Calculate force on a node using Barnes-Hut approximation.
   * @returns {Object} { fx, fy } — accumulated force vector
   */
  calculateForce(node, chargeStrength = -30) {
    let fx = 0, fy = 0;

    const traverse = (quad) => {
      if (quad.mass === 0) return;
      if (quad.node === node) return;

      const dx = quad.cx - node.x;
      const dy = quad.cy - node.y;
      const distSq = dx * dx + dy * dy;
      const dist = Math.sqrt(distSq) || 0.01;

      // Barnes-Hut criterion: if far enough, treat as single body
      if (quad.node || quad.size / dist < this.theta) {
        const strength = chargeStrength * quad.mass / distSq;
        fx += dx * strength / dist;
        fy += dy * strength / dist;
        return;
      }

      // Otherwise, recurse into children
      if (quad.children) {
        quad.children.forEach(child => traverse(child));
      }
    };

    traverse(this.root);
    return { fx, fy };
  }
}
```

---

## Domain 5: Collision Detection & Resolution

### 5.1 Broad-Phase with Quadtree

```javascript
class CollisionSystem {
  constructor() {
    this.grid = null;
    this.cellSize = 50;
  }

  /**
   * Detect and resolve all node-node overlaps.
   * Uses spatial hash grid for O(n) broad phase.
   */
  resolveAll(nodes) {
    // Build spatial hash
    this.grid = new Map();
    nodes.forEach(node => {
      const cellX = Math.floor(node.x / this.cellSize);
      const cellY = Math.floor(node.y / this.cellSize);
      const key = `${cellX},${cellY}`;
      if (!this.grid.has(key)) this.grid.set(key, []);
      this.grid.get(key).push(node);
    });

    // Check each node against neighbors in adjacent cells
    nodes.forEach(node => {
      if (node.fx != null) return; // pinned

      const cellX = Math.floor(node.x / this.cellSize);
      const cellY = Math.floor(node.y / this.cellSize);

      for (let dx = -1; dx <= 1; dx++) {
        for (let dy = -1; dy <= 1; dy++) {
          const key = `${cellX + dx},${cellY + dy}`;
          const cell = this.grid.get(key);
          if (!cell) continue;

          cell.forEach(other => {
            if (other === node) return;
            this._resolveOverlap(node, other);
          });
        }
      }
    });
  }

  _resolveOverlap(a, b) {
    const ra = (a.radius || 8) + 2;
    const rb = (b.radius || 8) + 2;
    const minDist = ra + rb;

    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const dist = Math.sqrt(dx * dx + dy * dy) || 0.01;

    if (dist < minDist) {
      const overlap = (minDist - dist) / dist * 0.5;
      const pushX = dx * overlap;
      const pushY = dy * overlap;

      if (a.fx == null) { a.x -= pushX; a.y -= pushY; }
      if (b.fx == null) { b.x += pushX; b.y += pushY; }
    }
  }
}
```

---

## Domain 6: Node Interaction System

### 6.1 Drag, Select, Pin Controller

```javascript
class InteractionController {
  constructor(physicsEngine, svg) {
    this.physics = physicsEngine;
    this.svg = svg;
    this.selectedNodes = new Set();
    this.isDragging = false;
    this.dragNode = null;
    this.lassoPoints = [];
    this.isLassoing = false;

    this._setupDrag();
    this._setupLasso();
    this._setupKeyboard();
  }

  _setupDrag() {
    const self = this;
    this.dragBehavior = d3.drag()
      .on('start', function(event, d) {
        self.isDragging = true;
        self.dragNode = d;

        // Pull node from simulation
        if (!event.active) self.physics.reheat(0.1);
        d.fx = d.x;
        d.fy = d.y;
      })
      .on('drag', function(event, d) {
        d.fx = event.x;
        d.fy = event.y;

        // If multi-selected, drag all selected nodes
        if (self.selectedNodes.has(d.id) && self.selectedNodes.size > 1) {
          const dx = event.x - d.x;
          const dy = event.y - d.y;
          self.selectedNodes.forEach(id => {
            if (id === d.id) return;
            const node = self.physics.nodes.find(n => n.id === id);
            if (node) { node.fx = (node.fx || node.x) + dx; node.fy = (node.fy || node.y) + dy; }
          });
        }
      })
      .on('end', function(event, d) {
        self.isDragging = false;
        self.dragNode = null;

        if (event.sourceEvent?.shiftKey) {
          // Shift+release = pin
          self.physics.pinNode(d.id);
        } else {
          // Release back to simulation
          d.fx = null;
          d.fy = null;
        }

        // Unpin multi-selected unless shift held
        if (!event.sourceEvent?.shiftKey) {
          self.selectedNodes.forEach(id => {
            if (id !== d.id) {
              const node = self.physics.nodes.find(n => n.id === id);
              if (node) { node.fx = null; node.fy = null; }
            }
          });
        }

        if (!event.active) self.physics.simulation?.alphaTarget(0);
      });
  }

  _setupLasso() {
    const self = this;

    this.svg.on('mousedown.lasso', function(event) {
      if (!event.altKey) return; // Alt+drag for lasso
      self.isLassoing = true;
      self.lassoPoints = [d3.pointer(event)];

      self.lassoPath = self.svg.append('path')
        .attr('class', 'lasso')
        .attr('fill', 'rgba(100,100,255,0.1)')
        .attr('stroke', '#6666ff')
        .attr('stroke-width', 1)
        .attr('stroke-dasharray', '4 2');
    });

    this.svg.on('mousemove.lasso', function(event) {
      if (!self.isLassoing) return;
      self.lassoPoints.push(d3.pointer(event));
      self.lassoPath.attr('d', `M${self.lassoPoints.map(p => p.join(',')).join('L')}Z`);
    });

    this.svg.on('mouseup.lasso', function() {
      if (!self.isLassoing) return;
      self.isLassoing = false;

      // Select nodes inside lasso polygon
      self.physics.nodes.forEach(node => {
        if (self._pointInPolygon([node.x, node.y], self.lassoPoints)) {
          self.selectedNodes.add(node.id);
        }
      });

      if (self.lassoPath) self.lassoPath.remove();
      self.physics._emit('selectionChanged', { selected: [...self.selectedNodes] });
    });
  }

  _setupKeyboard() {
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        // Clear selection
        this.selectedNodes.clear();
        this.physics._emit('selectionChanged', { selected: [] });
      }
      if (e.key === 'Delete' && this.selectedNodes.size > 0) {
        // Unpin all selected
        this.selectedNodes.forEach(id => this.physics.unpinNode(id));
      }
    });
  }

  _pointInPolygon(point, polygon) {
    const [px, py] = point;
    let inside = false;
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
      const [xi, yi] = polygon[i];
      const [xj, yj] = polygon[j];
      if (((yi > py) !== (yj > py)) && (px < (xj - xi) * (py - yi) / (yj - yi) + xi)) {
        inside = !inside;
      }
    }
    return inside;
  }

  applyTo(nodeSelection) {
    nodeSelection.call(this.dragBehavior);
  }
}
```

---

## Domain 7: Web Worker Simulation Bridge

### 7.1 Worker Thread for Heavy Simulation

```javascript
// --- physics_worker.js (runs in Web Worker) ---

let simulation = null;
let nodes = [];
let links = [];

self.onmessage = function(e) {
  const { type, data } = e.data;

  switch (type) {
    case 'init': {
      nodes = data.nodes;
      links = data.links;
      const preset = data.preset;

      // Import d3-force in worker (via importScripts or bundled)
      // Using minimal force implementation for worker
      simulation = createMinimalSimulation(nodes, links, preset);
      simulation.on('tick', () => {
        // Send positions back to main thread
        const positions = new Float64Array(nodes.length * 2);
        nodes.forEach((n, i) => {
          positions[i * 2] = n.x;
          positions[i * 2 + 1] = n.y;
        });
        self.postMessage({ type: 'tick', positions }, [positions.buffer]);
      });
      break;
    }

    case 'reheat': {
      if (simulation) simulation.alpha(data.alpha).restart();
      break;
    }

    case 'pin': {
      const node = nodes.find(n => n.id === data.id);
      if (node) { node.fx = data.x; node.fy = data.y; }
      break;
    }

    case 'unpin': {
      const node = nodes.find(n => n.id === data.id);
      if (node) { node.fx = null; node.fy = null; }
      break;
    }

    case 'updatePreset': {
      applyPresetToSimulation(simulation, data.preset);
      break;
    }

    case 'stop': {
      if (simulation) simulation.stop();
      break;
    }
  }
};

function createMinimalSimulation(nodes, links, preset) {
  // Minimal D3-compatible force simulation for worker context
  // In production: bundle d3-force as ES module and import it
  // For now: assumes d3-force is available via importScripts
  importScripts('https://d3js.org/d3-force.v3.min.js');

  return d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d => d.id).distance(preset.linkDistance))
    .force('charge', d3.forceManyBody().strength(preset.charge).theta(0.9))
    .force('center', d3.forceCenter(960, 540))
    .force('collide', d3.forceCollide().radius(10))
    .velocityDecay(preset.velocityDecay)
    .alpha(preset.alpha);
}
```

### 7.2 Main Thread Worker Bridge

```javascript
class WorkerBridge {
  constructor(workerPath = 'physics_worker.js') {
    this.worker = new Worker(workerPath);
    this.nodes = [];
    this.onTick = null;

    this.worker.onmessage = (e) => {
      if (e.data.type === 'tick') {
        // Transfer positions from ArrayBuffer
        const positions = new Float64Array(e.data.positions);
        this.nodes.forEach((n, i) => {
          n.x = positions[i * 2];
          n.y = positions[i * 2 + 1];
        });
        if (this.onTick) this.onTick();
      }
    };
  }

  init(nodes, links, preset) {
    this.nodes = nodes;
    // Transfer node/link data to worker (structured clone)
    this.worker.postMessage({
      type: 'init',
      data: {
        nodes: nodes.map(n => ({
          id: n.id, x: n.x, y: n.y, fx: n.fx, fy: n.fy,
          mass: n.mass, radius: n.radius, type: n.type, layer: n.layer
        })),
        links: links.map(l => ({
          source: l.source?.id || l.source,
          target: l.target?.id || l.target,
          type: l.type, weight: l.weight
        })),
        preset
      }
    });
  }

  reheat(alpha) { this.worker.postMessage({ type: 'reheat', data: { alpha } }); }
  pin(id, x, y) { this.worker.postMessage({ type: 'pin', data: { id, x, y } }); }
  unpin(id) { this.worker.postMessage({ type: 'unpin', data: { id } }); }
  stop() { this.worker.postMessage({ type: 'stop' }); }
  terminate() { this.worker.terminate(); }
}
```

---

## Domain 8: Performance Profiler

### 8.1 Physics Performance Monitor

```javascript
class PhysicsProfiler {
  constructor() {
    this.frameTimes = [];
    this.tickTimes = [];
    this.maxSamples = 120;
    this.isVisible = false;
  }

  startTick() {
    this._tickStart = performance.now();
  }

  endTick() {
    if (this._tickStart) {
      this.tickTimes.push(performance.now() - this._tickStart);
      if (this.tickTimes.length > this.maxSamples) this.tickTimes.shift();
    }
  }

  recordFrame(frameTimeMs) {
    this.frameTimes.push(frameTimeMs);
    if (this.frameTimes.length > this.maxSamples) this.frameTimes.shift();
  }

  get avgTickMs() {
    if (this.tickTimes.length === 0) return 0;
    return this.tickTimes.reduce((a, b) => a + b, 0) / this.tickTimes.length;
  }

  get avgFrameMs() {
    if (this.frameTimes.length === 0) return 0;
    return this.frameTimes.reduce((a, b) => a + b, 0) / this.frameTimes.length;
  }

  get fps() {
    return this.avgFrameMs > 0 ? 1000 / this.avgFrameMs : 60;
  }

  get isOverBudget() {
    return this.avgTickMs > 5; // 5ms budget for physics
  }

  /**
   * Auto-degrade physics quality if over budget.
   * Returns recommended theta increase for Barnes-Hut.
   */
  getQualityAdjustment() {
    if (this.avgTickMs > 8) return { theta: 1.5, ticksPerFrame: 1 };
    if (this.avgTickMs > 5) return { theta: 1.2, ticksPerFrame: 1 };
    if (this.avgTickMs < 2) return { theta: 0.7, ticksPerFrame: 4 };
    return { theta: 0.9, ticksPerFrame: 2 };
  }

  render(container) {
    if (!this.isVisible) return;

    let panel = container.select('#physics-profiler');
    if (panel.empty()) {
      panel = container.append('div')
        .attr('id', 'physics-profiler')
        .style('position', 'fixed')
        .style('top', '60px')
        .style('right', '10px')
        .style('z-index', '998')
        .style('background', '#0a0a1ecc')
        .style('border', '1px solid #00ff8844')
        .style('border-radius', '4px')
        .style('padding', '6px 10px')
        .style('font-family', 'monospace')
        .style('font-size', '10px')
        .style('color', '#00ff88');
    }

    const fpsColor = this.fps >= 55 ? '#00ff88' : this.fps >= 30 ? '#ffcc00' : '#ff4444';

    panel.html(`
      <div style="color:${fpsColor};font-weight:bold">
        ⚡ ${Math.round(this.fps)} FPS
      </div>
      <div>Physics: ${this.avgTickMs.toFixed(1)}ms</div>
      <div>Frame: ${this.avgFrameMs.toFixed(1)}ms</div>
      <div>Budget: ${this.isOverBudget ? '🔴 OVER' : '🟢 OK'}</div>
    `);
  }

  toggle() {
    this.isVisible = !this.isVisible;
    if (!this.isVisible) {
      d3.select('#physics-profiler').remove();
    }
  }
}
```

---

## Domain 9: Physics GUI Controls

### 9.1 Real-Time Parameter Sliders

```javascript
function createPhysicsControls(container, physicsEngine) {
  const panel = container.append('div')
    .attr('id', 'physics-controls')
    .style('position', 'fixed')
    .style('right', '10px')
    .style('top', '150px')
    .style('width', '200px')
    .style('z-index', '997')
    .style('background', '#0a0a1eee')
    .style('border', '1px solid #4488ff44')
    .style('border-radius', '8px')
    .style('padding', '12px')
    .style('font-family', 'monospace')
    .style('font-size', '11px')
    .style('color', '#aaa');

  panel.append('div')
    .style('color', '#4488ff')
    .style('font-weight', 'bold')
    .style('margin-bottom', '8px')
    .text('⚙ Physics Controls');

  // Preset selector
  const presetDiv = panel.append('div').style('margin-bottom', '8px');
  presetDiv.append('label').text('Preset: ');
  const presetSelect = presetDiv.append('select')
    .style('background', '#1a1a3e')
    .style('color', '#fff')
    .style('border', '1px solid #444')
    .style('border-radius', '3px');

  Object.keys(PHYSICS_PRESETS).forEach(name => {
    presetSelect.append('option').attr('value', name).text(name);
  });
  presetSelect.property('value', physicsEngine.preset);
  presetSelect.on('change', function() {
    physicsEngine.setPreset(this.value, true);
  });

  // Sliders
  const sliders = [
    { label: 'Charge', key: 'charge', min: -300, max: 0, step: 5 },
    { label: 'Link Dist', key: 'linkDistance', min: 10, max: 300, step: 5 },
    { label: 'Velocity Decay', key: 'velocityDecay', min: 0.1, max: 0.9, step: 0.05 },
  ];

  sliders.forEach(s => {
    const row = panel.append('div').style('margin-bottom', '6px');
    row.append('label').text(`${s.label}: `);
    const valueLabel = row.append('span').style('float', 'right').style('color', '#fff');

    const slider = row.append('input')
      .attr('type', 'range')
      .attr('min', s.min)
      .attr('max', s.max)
      .attr('step', s.step)
      .style('width', '100%')
      .property('value', PHYSICS_PRESETS[physicsEngine.preset][s.key]);

    valueLabel.text(slider.property('value'));

    slider.on('input', function() {
      const val = +this.value;
      valueLabel.text(val);

      if (s.key === 'charge') {
        physicsEngine.simulation?.force('charge').strength(val);
      } else if (s.key === 'linkDistance') {
        physicsEngine.simulation?.force('link').distance(val);
      } else if (s.key === 'velocityDecay') {
        physicsEngine.simulation?.velocityDecay(val);
      }
      physicsEngine.reheat(0.1);
    });
  });

  // Layout buttons
  panel.append('div')
    .style('margin-top', '12px')
    .style('color', '#4488ff')
    .style('font-weight', 'bold')
    .text('📐 Layouts');

  const layoutNames = ['force', 'radial', 'hierarchical', 'circular', 'swimlane', 'timeline', 'grid', 'tree'];
  const btnRow = panel.append('div').style('display', 'flex').style('flex-wrap', 'wrap').style('gap', '4px').style('margin-top', '4px');

  layoutNames.forEach(name => {
    btnRow.append('button')
      .text(name.charAt(0).toUpperCase() + name.slice(1))
      .style('background', '#1a1a3e')
      .style('color', '#88aaff')
      .style('border', '1px solid #334')
      .style('border-radius', '3px')
      .style('padding', '2px 6px')
      .style('cursor', 'pointer')
      .style('font-size', '9px')
      .on('click', () => {
        if (physicsEngine._layoutManager) {
          physicsEngine._layoutManager.switchTo(name);
        }
      });
  });

  // Action buttons
  panel.append('div').style('margin-top', '8px');
  panel.append('button')
    .text('🔄 Reheat')
    .style('background', '#1a3a1e').style('color', '#00ff88').style('border', '1px solid #00ff8844')
    .style('border-radius', '3px').style('padding', '4px 8px').style('cursor', 'pointer').style('margin-right', '4px')
    .on('click', () => physicsEngine.reheat(0.5));

  panel.append('button')
    .text('📌 Unpin All')
    .style('background', '#3a1a1e').style('color', '#ff4444').style('border', '1px solid #ff444444')
    .style('border-radius', '3px').style('padding', '4px 8px').style('cursor', 'pointer')
    .on('click', () => {
      physicsEngine.nodes.forEach(n => { n.fx = null; n.fy = null; });
      physicsEngine.pinned.clear();
      physicsEngine.reheat(0.3);
    });

  return panel;
}
```

---

## Anti-Patterns (MANDATORY — 20 Rules)

1. **NEVER** run simulation on main thread with >1000 nodes — use Web Worker
2. **NEVER** use `setTimeout` for animation — always `requestAnimationFrame`
3. **NEVER** restart simulation from random positions after layout switch — warm-start from current
4. **NEVER** apply forces to pinned nodes (check `fx != null`)
5. **NEVER** skip velocity clamping — max velocity = 50px/tick
6. **NEVER** use linear interpolation for layout transitions — use ease-in-out cubic
7. **NEVER** run simulation when tab is not visible — use `visibilitychange` listener
8. **NEVER** allocate new arrays per tick — pre-allocate typed array buffers
9. **NEVER** compute distances with `Math.sqrt` when only comparing — use squared distance
10. **NEVER** apply gravity to CRIMINAL lane nodes toward other lanes (Rule 7 isolation)
11. **NEVER** let alpha exceed 1.0 or go below 0
12. **NEVER** skip the collision broadphase for >100 nodes — use spatial hash
13. **NEVER** store positions in node objects for the worker — use `Float64Array` transfer
14. **NEVER** use `d3.forceSimulation().stop()` without saving positions first
15. **NEVER** forget to clamp node positions to viewport bounds
16. **NEVER** transition between presets without smooth interpolation (jarring jumps)
17. **NEVER** ignore `devicePixelRatio` — force positions must account for HiDPI
18. **NEVER** run more than 4 simulation ticks per frame — diminishing returns
19. **NEVER** skip Barnes-Hut theta adjustment when performance degrades
20. **NEVER** forget to dispose the Web Worker on component unmount

---

## Performance Budgets

| Operation | Budget | Technique |
|-----------|--------|-----------|
| Force tick (2500 nodes) | <5ms | Barnes-Hut θ=0.9, spatial hash collision |
| Layout transition | <500ms | Ease-in-out cubic animation |
| Position save | <2ms | `localStorage.setItem` (JSON string) |
| Collision broad-phase | <1ms | Spatial hash grid, O(n) |
| Collision narrow-phase | <2ms | Circle-circle distance check |
| Worker message transfer | <0.5ms | `Float64Array` Transferable |
| Preset transition | <500ms | Smooth interpolation, 60fps |
| Drag response | <1ms | Direct `fx/fy` assignment |
| Lasso selection | <5ms | Point-in-polygon, O(n) |
| Quadtree rebuild | <3ms | Full rebuild every 10 frames |

---

## Integration Map

| Skill | Data Flow |
|-------|-----------|
| **MBP-GENESIS** | Node/link schema → force parameters |
| **MBP-DATAWEAVE** | Graph data → simulation init |
| **MBP-FORGE-RENDERER** | Position arrays → rendering pipeline |
| **MBP-FORGE-EFFECTS** | Link paths → particle trajectories |
| **MBP-EMERGENCE-CONVERGENCE** | Simulation positions → DBSCAN clustering |
| **MBP-EMERGENCE-SELFEVOLVE** | User slider adjustments → learned preferences |
| **MBP-INTERFACE-CONTROLS** | Drag/select events → selection state |
| **MBP-INTERFACE-HUD** | Performance metrics → FPS gauge |

---

## Quality Gates

| Gate | Requirement |
|------|-------------|
| **QG-PHY-001** | 60fps with 2,500 nodes on AMD Vega 8 |
| **QG-PHY-002** | Smooth layout transitions (no teleporting) |
| **QG-PHY-003** | CRIMINAL lane always isolated |
| **QG-PHY-004** | Pinned nodes immovable by forces |
| **QG-PHY-005** | Web Worker fallback if main thread >5ms/tick |
| **QG-PHY-006** | All positions saved to localStorage on stop |
| **QG-PHY-007** | No force applied beyond viewport bounds + 200px |
| **QG-PHY-008** | Preset transitions complete in <500ms |
| **QG-PHY-009** | Lasso selection works with Alt+drag |
| **QG-PHY-010** | Barnes-Hut theta auto-adjusts based on performance |

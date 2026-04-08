---
skill: SINGULARITY-MBP-FORGE-EFFECTS
version: "1.0.0"
description: "Visual effects for THEMANBEARPIG: GLSL shaders, particle systems, glow/aura rendering, CRT scanlines, glass morphism, fog of war. Covers WebGL shader pipeline, SVG filters, CSS backdrop effects, animated transitions, and post-processing compositing for the litigation mega-visualization."
tier: "TIER-1/FORGE"
domain: "Visual effects — shaders, particles, glow, aura, fog, scanlines, glass, post-processing"
triggers:
  - shader
  - GLSL
  - particle
  - glow
  - aura
  - fog
  - scanline
  - CRT
  - glass
  - effect
---

# SINGULARITY-MBP-FORGE-EFFECTS v1.0

> **Weaponized aesthetics. Every pixel serves the litigation mission.**

## Layer 1: WebGL Shader Pipeline for Node Glow/Aura

### 1.1 Architecture Overview

THEMANBEARPIG renders 2500+ nodes across 13 layers. Raw SVG cannot handle per-node glow
at that scale. The effects pipeline composites WebGL post-processing over the D3 SVG layer
using an overlay `<canvas>` element positioned absolutely above the graph SVG.

```
┌─────────────────────────────────────────┐
│  Post-Processing Canvas (WebGL)         │  ← glow, bloom, scanlines, fog
│  ┌───────────────────────────────────┐  │
│  │  D3 SVG Layer (force graph)      │  │  ← nodes, links, labels
│  │  ┌─────────────────────────────┐  │  │
│  │  │  Background Canvas          │  │  │  ← starfield, grid, ambient
│  │  └─────────────────────────────┘  │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### 1.2 WebGL Context Setup

```javascript
function createEffectsCanvas(container) {
  const canvas = document.createElement('canvas');
  canvas.id = 'effects-overlay';
  canvas.style.cssText = `
    position: absolute; top: 0; left: 0;
    width: 100%; height: 100%;
    pointer-events: none; z-index: 50;
  `;
  container.appendChild(canvas);

  const gl = canvas.getContext('webgl2', {
    alpha: true, premultipliedAlpha: false,
    antialias: false, preserveDrawingBuffer: false,
  });
  if (!gl) {
    console.warn('WebGL2 unavailable — falling back to SVG filters');
    return { canvas, gl: null, fallback: true };
  }
  gl.enable(gl.BLEND);
  gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
  return { canvas, gl, fallback: false };
}
```

### 1.3 Glow/Aura GLSL Shaders

```glsl
// vertex_glow.glsl — fullscreen quad
attribute vec2 a_position;
varying vec2 v_uv;
void main() {
  v_uv = a_position * 0.5 + 0.5;
  gl_Position = vec4(a_position, 0.0, 1.0);
}
```

```glsl
// fragment_glow.glsl — radial glow per node
precision mediump float;
varying vec2 v_uv;

uniform vec2 u_resolution;
uniform vec2 u_nodes[256];       // node screen positions (max 256 glowing nodes)
uniform vec4 u_colors[256];      // RGBA per node
uniform float u_radii[256];      // glow radius per node
uniform int u_count;             // active glow count
uniform float u_time;            // animation clock

void main() {
  vec2 fragCoord = v_uv * u_resolution;
  vec4 color = vec4(0.0);

  for (int i = 0; i < 256; i++) {
    if (i >= u_count) break;
    float dist = distance(fragCoord, u_nodes[i]);
    float radius = u_radii[i];
    // Smooth radial falloff with pulse animation
    float pulse = 1.0 + 0.15 * sin(u_time * 2.0 + float(i) * 0.7);
    float intensity = smoothstep(radius * pulse, 0.0, dist);
    intensity *= intensity; // quadratic falloff for soft glow
    color += u_colors[i] * intensity * 0.6;
  }

  color.a = min(color.a, 0.85); // cap opacity to preserve readability
  gl_FragColor = color;
}
```

### 1.4 Shader Compilation Helper

```javascript
function compileShader(gl, type, source) {
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    console.error('Shader compile error:', gl.getShaderInfoLog(shader));
    gl.deleteShader(shader);
    return null;
  }
  return shader;
}

function createGlowProgram(gl, vertSrc, fragSrc) {
  const vert = compileShader(gl, gl.VERTEX_SHADER, vertSrc);
  const frag = compileShader(gl, gl.FRAGMENT_SHADER, fragSrc);
  if (!vert || !frag) return null;

  const program = gl.createProgram();
  gl.attachShader(program, vert);
  gl.attachShader(program, frag);
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    console.error('Program link error:', gl.getProgramInfoLog(program));
    return null;
  }
  return program;
}
```

### 1.5 Node Glow Data Extraction from D3

```javascript
function extractGlowNodes(simulation, threatLevels) {
  const glowNodes = [];
  simulation.nodes().forEach(node => {
    const threat = threatLevels[node.id] || 0;
    if (threat < 3) return; // only glow nodes with threat >= 3

    glowNodes.push({
      x: node.x, y: node.y,
      color: threatToColor(threat),
      radius: 20 + threat * 8, // glow radius scales with threat
    });
  });
  return glowNodes.slice(0, 256); // shader supports max 256
}

function threatToColor(threat) {
  // threat 1-10 → green → yellow → red → magenta
  const colors = [
    [0, 1, 0.53, 0.3],   // 1-3: green (low)
    [1, 0.84, 0, 0.4],   // 4-6: amber (medium)
    [1, 0.2, 0.2, 0.5],  // 7-8: red (high)
    [1, 0, 1, 0.6],      // 9-10: magenta (critical)
  ];
  const idx = Math.min(Math.floor((threat - 1) / 3), 3);
  return colors[idx];
}
```

## Layer 2: Particle Systems for Evidence Discovery

### 2.1 Particle Emitter Architecture

When new evidence is discovered (via KRAKEN lottery harvest), particles burst from the
source node and travel along link paths to connected nodes — visually showing evidence
propagation through the adversary network.

```javascript
class ParticleSystem {
  constructor(canvas, maxParticles = 2000) {
    this.ctx = canvas.getContext('2d');
    this.particles = [];
    this.maxParticles = maxParticles;
    this.pool = []; // object pool for GC prevention
  }

  emit(x, y, count, config = {}) {
    const {
      color = '#00ff88',
      speed = 2,
      lifetime = 60,   // frames
      spread = Math.PI * 2,
      size = 3,
      decay = 0.95,
    } = config;

    for (let i = 0; i < count && this.particles.length < this.maxParticles; i++) {
      const angle = Math.random() * spread - spread / 2;
      const vel = speed * (0.5 + Math.random() * 0.5);
      const p = this.pool.pop() || {};
      Object.assign(p, {
        x, y,
        vx: Math.cos(angle) * vel,
        vy: Math.sin(angle) * vel,
        life: lifetime,
        maxLife: lifetime,
        size,
        color,
        decay,
        active: true,
      });
      this.particles.push(p);
    }
  }

  emitAlongPath(source, target, count, config = {}) {
    const dx = target.x - source.x;
    const dy = target.y - source.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    const angle = Math.atan2(dy, dx);

    for (let i = 0; i < count; i++) {
      const t = i / count;
      const px = source.x + dx * t + (Math.random() - 0.5) * 10;
      const py = source.y + dy * t + (Math.random() - 0.5) * 10;
      this.emit(px, py, 1, {
        ...config,
        speed: 1 + Math.random(),
        spread: 0.3,
      });
    }
  }

  update() {
    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i];
      p.x += p.vx;
      p.y += p.vy;
      p.vx *= p.decay;
      p.vy *= p.decay;
      p.life--;
      if (p.life <= 0) {
        p.active = false;
        this.pool.push(this.particles.splice(i, 1)[0]);
      }
    }
  }

  render() {
    const ctx = this.ctx;
    for (const p of this.particles) {
      const alpha = p.life / p.maxLife;
      ctx.globalAlpha = alpha;
      ctx.fillStyle = p.color;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size * alpha, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }
}
```

### 2.2 Evidence Discovery Burst Effect

```javascript
function onEvidenceDiscovered(nodeId, category, simulation) {
  const node = simulation.nodes().find(n => n.id === nodeId);
  if (!node) return;

  const categoryColors = {
    'judicial_violation': '#ff00ff',
    'false_allegation':   '#ff4444',
    'impeachment':        '#ffaa00',
    'custody':            '#00aaff',
    'ppo':                '#ff6600',
    'financial':          '#44ff44',
    'default':            '#00ff88',
  };
  const color = categoryColors[category] || categoryColors.default;

  // Burst from discovery node
  particles.emit(node.x, node.y, 30, {
    color, speed: 4, lifetime: 90, size: 4,
  });

  // Trail particles along links to connected nodes
  const connected = simulation.force('link').links()
    .filter(l => l.source.id === nodeId || l.target.id === nodeId);

  connected.forEach(link => {
    const target = link.source.id === nodeId ? link.target : link.source;
    particles.emitAlongPath(node, target, 8, { color, lifetime: 120 });
  });
}
```

## Layer 3: CRT Scanline Overlay

### 3.1 CSS-Based Scanline Effect (Performant)

```css
#crt-overlay {
  position: fixed; top: 0; left: 0;
  width: 100vw; height: 100vh;
  pointer-events: none; z-index: 100;
  background: repeating-linear-gradient(
    0deg,
    rgba(0, 0, 0, 0.15) 0px,
    rgba(0, 0, 0, 0.15) 1px,
    transparent 1px,
    transparent 3px
  );
  mix-blend-mode: multiply;
  opacity: 0.4;
}

/* Subtle screen flicker */
@keyframes crt-flicker {
  0%   { opacity: 0.38; }
  5%   { opacity: 0.42; }
  10%  { opacity: 0.39; }
  100% { opacity: 0.40; }
}
#crt-overlay { animation: crt-flicker 0.15s infinite; }

/* Chromatic aberration on hover */
.node:hover {
  filter: drop-shadow(-2px 0 0 rgba(255, 0, 0, 0.3))
          drop-shadow(2px 0 0 rgba(0, 255, 255, 0.3));
}
```

### 3.2 WebGL CRT Post-Processing Shader

```glsl
// fragment_crt.glsl — full CRT post-processing pass
precision mediump float;
varying vec2 v_uv;
uniform sampler2D u_scene;     // rendered scene texture
uniform vec2 u_resolution;
uniform float u_time;
uniform float u_scanlineIntensity;  // 0.0 to 1.0
uniform float u_vignetteStrength;   // 0.0 to 1.0
uniform float u_curvature;          // barrel distortion 0.0 to 0.3

vec2 curveUV(vec2 uv) {
  uv = uv * 2.0 - 1.0;
  uv *= 1.0 + u_curvature * dot(uv, uv);
  return uv * 0.5 + 0.5;
}

void main() {
  vec2 uv = curveUV(v_uv);
  if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) {
    gl_FragColor = vec4(0.0); return;
  }

  // Chromatic aberration
  float aberration = 0.002;
  float r = texture2D(u_scene, uv + vec2(aberration, 0.0)).r;
  float g = texture2D(u_scene, uv).g;
  float b = texture2D(u_scene, uv - vec2(aberration, 0.0)).b;
  vec3 color = vec3(r, g, b);

  // Scanlines
  float scanline = sin(uv.y * u_resolution.y * 3.14159) * 0.5 + 0.5;
  color *= 1.0 - u_scanlineIntensity * (1.0 - scanline) * 0.3;

  // Vignette
  vec2 vig = uv * (1.0 - uv);
  float vignette = vig.x * vig.y * 15.0;
  vignette = pow(vignette, u_vignetteStrength * 0.5);
  color *= vignette;

  // Subtle noise
  float noise = fract(sin(dot(uv * u_time, vec2(12.9898, 78.233))) * 43758.5453);
  color += (noise - 0.5) * 0.02;

  gl_FragColor = vec4(color, 1.0);
}
```

### 3.3 CRT Toggle Control

```javascript
const crtState = { enabled: true, intensity: 0.4 };

function toggleCRT() {
  crtState.enabled = !crtState.enabled;
  document.getElementById('crt-overlay').style.display =
    crtState.enabled ? 'block' : 'none';
}

document.addEventListener('keydown', e => {
  if (e.key === 'F7') toggleCRT();                    // toggle on/off
  if (e.key === '+' && e.ctrlKey) crtState.intensity =
    Math.min(1, crtState.intensity + 0.1);             // increase
  if (e.key === '-' && e.ctrlKey) crtState.intensity =
    Math.max(0, crtState.intensity - 0.1);             // decrease
});
```

## Layer 4: Glass Morphism Panels

### 4.1 Panel Styles

```css
.glass-panel {
  background: rgba(10, 10, 30, 0.6);
  backdrop-filter: blur(12px) saturate(1.4);
  -webkit-backdrop-filter: blur(12px) saturate(1.4);
  border: 1px solid rgba(255, 0, 255, 0.15);
  border-radius: 12px;
  box-shadow:
    0 4px 30px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
  color: #e0e0e0;
  padding: 16px;
}

.glass-panel--hud {
  background: rgba(10, 10, 30, 0.75);
  border-color: rgba(0, 255, 136, 0.2);
  font-family: 'JetBrains Mono', 'Cascadia Code', monospace;
  font-size: 12px;
}

.glass-panel--detail {
  background: rgba(20, 15, 40, 0.7);
  border-color: rgba(100, 100, 255, 0.2);
  max-height: 60vh;
  overflow-y: auto;
}

.glass-panel--alert {
  background: rgba(40, 10, 10, 0.75);
  border-color: rgba(255, 50, 50, 0.4);
  animation: alert-pulse 2s ease-in-out infinite;
}

@keyframes alert-pulse {
  0%, 100% { border-color: rgba(255, 50, 50, 0.4); }
  50%      { border-color: rgba(255, 50, 50, 0.8); }
}
```

### 4.2 Panel Builder

```javascript
function createGlassPanel(id, variant, position) {
  const panel = document.createElement('div');
  panel.id = id;
  panel.className = `glass-panel glass-panel--${variant}`;
  Object.assign(panel.style, {
    position: 'fixed',
    zIndex: '200',
    ...position, // { top, left, right, bottom, width, height }
  });
  document.body.appendChild(panel);
  return panel;
}

// HUD panel (top-left)
const hud = createGlassPanel('hud-main', 'hud', {
  top: '12px', left: '12px', width: '280px',
});

// Detail panel (right sidebar)
const detail = createGlassPanel('detail-panel', 'detail', {
  top: '12px', right: '12px', width: '360px', bottom: '12px',
});
detail.style.display = 'none'; // shown on node click
```

## Layer 5: Fog of War for Unexplored Graph Regions

### 5.1 Fog Rendering

Regions of the graph the user has not yet explored remain obscured with a semi-transparent
fog. As the user clicks on nodes and navigates, the fog clears around explored areas.

```javascript
class FogOfWar {
  constructor(canvas, gridSize = 40) {
    this.ctx = canvas.getContext('2d');
    this.gridSize = gridSize;
    this.explored = new Set(); // grid cell keys
    this.revealRadius = 120;   // pixels of fog cleared per exploration
  }

  cellKey(x, y) {
    const gx = Math.floor(x / this.gridSize);
    const gy = Math.floor(y / this.gridSize);
    return `${gx},${gy}`;
  }

  reveal(x, y) {
    const r = Math.ceil(this.revealRadius / this.gridSize);
    const cx = Math.floor(x / this.gridSize);
    const cy = Math.floor(y / this.gridSize);
    for (let dx = -r; dx <= r; dx++) {
      for (let dy = -r; dy <= r; dy++) {
        if (dx * dx + dy * dy <= r * r) {
          this.explored.add(`${cx + dx},${cy + dy}`);
        }
      }
    }
  }

  render(width, height) {
    const ctx = this.ctx;
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = 'rgba(5, 5, 20, 0.7)';
    ctx.fillRect(0, 0, width, height);

    // Clear explored regions
    ctx.globalCompositeOperation = 'destination-out';
    for (const key of this.explored) {
      const [gx, gy] = key.split(',').map(Number);
      const x = (gx + 0.5) * this.gridSize;
      const y = (gy + 0.5) * this.gridSize;

      const gradient = ctx.createRadialGradient(x, y, 0, x, y, this.gridSize);
      gradient.addColorStop(0, 'rgba(0,0,0,1)');
      gradient.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = gradient;
      ctx.fillRect(
        x - this.gridSize, y - this.gridSize,
        this.gridSize * 2, this.gridSize * 2
      );
    }
    ctx.globalCompositeOperation = 'source-over';
  }
}
```

### 5.2 Integration with Node Click

```javascript
const fog = new FogOfWar(fogCanvas);

// Reveal fog when user clicks/explores a node
function onNodeClick(node) {
  fog.reveal(node.x, node.y);
  // Also reveal connected neighbors (1-hop)
  const neighbors = getNeighbors(node.id);
  neighbors.forEach(n => fog.reveal(n.x, n.y));
}
```

## Layer 6: SVG Filter Chains

### 6.1 Reusable Filter Definitions

```html
<svg width="0" height="0">
  <defs>
    <!-- Soft glow filter for low-threat nodes -->
    <filter id="glow-soft" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur in="SourceGraphic" stdDeviation="3" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>

    <!-- Intense glow for high-threat nodes -->
    <filter id="glow-intense" x="-100%" y="-100%" width="300%" height="300%">
      <feGaussianBlur in="SourceGraphic" stdDeviation="6" result="blur1"/>
      <feGaussianBlur in="SourceGraphic" stdDeviation="12" result="blur2"/>
      <feMerge>
        <feMergeNode in="blur2"/>
        <feMergeNode in="blur1"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>

    <!-- Evidence category color matrix -->
    <filter id="color-judicial">
      <feColorMatrix type="matrix" values="
        1.2 0   0   0 0.1
        0   0.3 0   0 0
        0   0   1.3 0 0.2
        0   0   0   1 0"/>
    </filter>

    <!-- Drop shadow for selected nodes -->
    <filter id="shadow-selected" x="-30%" y="-30%" width="160%" height="160%">
      <feDropShadow dx="0" dy="0" stdDeviation="5" flood-color="#00ff88" flood-opacity="0.6"/>
    </filter>

    <!-- Turbulence distortion for contested nodes -->
    <filter id="contested">
      <feTurbulence type="fractalNoise" baseFrequency="0.02" numOctaves="2" result="turb"/>
      <feDisplacementMap in="SourceGraphic" in2="turb" scale="3"/>
    </filter>
  </defs>
</svg>
```

### 6.2 Dynamic Filter Assignment

```javascript
function assignNodeFilter(node) {
  const threat = node.threat_level || 0;
  if (node.selected) return 'url(#shadow-selected)';
  if (node.contested) return 'url(#contested)';
  if (threat >= 7) return 'url(#glow-intense)';
  if (threat >= 3) return 'url(#glow-soft)';
  if (node.type === 'judicial') return 'url(#color-judicial)';
  return 'none';
}

// Apply in D3 tick function
nodeSelection.attr('filter', d => assignNodeFilter(d));
```

## Layer 7: Animated Transitions Between Graph States

### 7.1 State Transition Engine

```javascript
const TRANSITION_DURATION = 800;
const TRANSITION_EASE = d3.easeCubicInOut;

function transitionToLayer(layerName, simulation, nodeSelection, linkSelection) {
  const layerNodes = getNodesForLayer(layerName);
  const layerLinks = getLinksForLayer(layerName);
  const layerNodeIds = new Set(layerNodes.map(n => n.id));

  // Fade out nodes not in the target layer
  nodeSelection
    .transition().duration(TRANSITION_DURATION).ease(TRANSITION_EASE)
    .attr('opacity', d => layerNodeIds.has(d.id) ? 1.0 : 0.05)
    .attr('r', d => layerNodeIds.has(d.id) ? nodeRadius(d) : 2);

  // Fade out links not in the target layer
  linkSelection
    .transition().duration(TRANSITION_DURATION).ease(TRANSITION_EASE)
    .attr('stroke-opacity', d =>
      layerNodeIds.has(d.source.id) && layerNodeIds.has(d.target.id) ? 0.6 : 0.02
    );
}

function transitionToFull(nodeSelection, linkSelection) {
  nodeSelection
    .transition().duration(TRANSITION_DURATION).ease(TRANSITION_EASE)
    .attr('opacity', 1.0)
    .attr('r', d => nodeRadius(d));
  linkSelection
    .transition().duration(TRANSITION_DURATION).ease(TRANSITION_EASE)
    .attr('stroke-opacity', 0.4);
}
```

## Layer 8: Post-Processing Compositing Pipeline

### 8.1 Render Pipeline Order

```javascript
class RenderPipeline {
  constructor(width, height) {
    this.passes = [];
    this.width = width;
    this.height = height;
  }

  addPass(name, renderFn, enabled = true) {
    this.passes.push({ name, render: renderFn, enabled });
  }

  execute(timestamp) {
    for (const pass of this.passes) {
      if (!pass.enabled) continue;
      pass.render(timestamp, this.width, this.height);
    }
  }
}

// Build the pipeline
const pipeline = new RenderPipeline(window.innerWidth, window.innerHeight);
pipeline.addPass('background',  renderBackground);
pipeline.addPass('fog',         (t, w, h) => fog.render(w, h));
pipeline.addPass('d3-graph',    () => {}); // D3 handles its own SVG render
pipeline.addPass('particles',   (t) => { particles.update(); particles.render(); });
pipeline.addPass('glow',        renderGlowPass);
pipeline.addPass('scanlines',   renderCRTPass, crtState.enabled);
pipeline.addPass('hud',         renderHUD);

// Drive with requestAnimationFrame
function animate(timestamp) {
  pipeline.execute(timestamp);
  requestAnimationFrame(animate);
}
requestAnimationFrame(animate);
```

## Layer 9: Performance Budgets

### 9.1 Per-Effect Frame Budget (Target: 60 FPS = 16.67ms total)

| Effect | Budget | Technique | Fallback |
|--------|--------|-----------|----------|
| Node glow (WebGL) | 2ms | GPU shader, max 256 nodes | SVG filter `glow-soft` |
| Particles | 1.5ms | Object pool, canvas 2D | Disable at > 1000 particles |
| CRT scanlines | 0.5ms | CSS repeating-gradient | Remove `mix-blend-mode` |
| Glass panels | 0ms | Pure CSS, GPU-composited | Remove `backdrop-filter` |
| Fog of war | 1ms | Canvas 2D compositing | Static overlay |
| SVG filters | 1ms | Max 3 filters active | Remove `feTurbulence` |
| Transitions | 0.5ms | D3 transition, eased | Instant snap |
| **Total effects** | **6.5ms** | — | — |
| **Remaining for D3** | **10ms** | Force simulation + DOM | — |

### 9.2 Adaptive Quality System

```javascript
const perfMonitor = {
  frameTimes: [],
  maxSamples: 60,

  recordFrame(dt) {
    this.frameTimes.push(dt);
    if (this.frameTimes.length > this.maxSamples) this.frameTimes.shift();
  },

  get avgFrameTime() {
    if (!this.frameTimes.length) return 16;
    return this.frameTimes.reduce((a, b) => a + b) / this.frameTimes.length;
  },

  adjustQuality(pipeline, particles) {
    const avg = this.avgFrameTime;
    if (avg > 20) {
      // Drop to low quality
      pipeline.passes.find(p => p.name === 'scanlines').enabled = false;
      pipeline.passes.find(p => p.name === 'glow').enabled = false;
      particles.maxParticles = 500;
    } else if (avg > 14) {
      // Medium quality
      pipeline.passes.find(p => p.name === 'scanlines').enabled = true;
      pipeline.passes.find(p => p.name === 'glow').enabled = false;
      particles.maxParticles = 1000;
    } else {
      // Full quality
      pipeline.passes.find(p => p.name === 'scanlines').enabled = true;
      pipeline.passes.find(p => p.name === 'glow').enabled = true;
      particles.maxParticles = 2000;
    }
  }
};
```

### 9.3 Python-Side Effect Configuration

```python
"""Effect preset management for THEMANBEARPIG pywebview bridge."""
import json

EFFECT_PRESETS = {
    'performance': {
        'glow': False, 'particles': False, 'crt': False,
        'fog': False, 'glass': True, 'transitions': True,
    },
    'balanced': {
        'glow': True, 'particles': True, 'crt': True,
        'fog': False, 'glass': True, 'transitions': True,
    },
    'cinematic': {
        'glow': True, 'particles': True, 'crt': True,
        'fog': True, 'glass': True, 'transitions': True,
    },
}

class EffectsBridge:
    """Exposed to JS via pywebview js_api."""
    def __init__(self):
        self.current_preset = 'balanced'

    def get_preset(self, name: str) -> str:
        preset = EFFECT_PRESETS.get(name, EFFECT_PRESETS['balanced'])
        return json.dumps(preset)

    def set_preset(self, name: str) -> str:
        if name in EFFECT_PRESETS:
            self.current_preset = name
            return json.dumps({'ok': True, 'preset': name})
        return json.dumps({'ok': False, 'error': f'Unknown preset: {name}'})
```

## Anti-Patterns

1. **NEVER** apply SVG `filter` to > 50 nodes simultaneously — use WebGL for bulk glow
2. **NEVER** use `feTurbulence` on more than 5 elements — extremely expensive
3. **NEVER** allocate particles in the render loop — use object pooling
4. **NEVER** run CRT shader at full resolution on integrated GPUs — use half-res pass
5. **NEVER** forget `pointer-events: none` on overlay canvases — blocks graph interaction
6. **NEVER** use `box-shadow` for animated glow — use `drop-shadow` filter or WebGL
7. **NEVER** composite effects without the adaptive quality monitor running
8. **NEVER** skip the performance budget check when adding new effects

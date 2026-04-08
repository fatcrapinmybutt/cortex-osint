---
name: SINGULARITY-MBP-FORGE-RENDERER
version: "1.0.0"
description: "SVG/Canvas/WebGL/WebGPU rendering for THEMANBEARPIG. LOD, viewport culling, quadtree spatial indexing, PixiJS WebGL, 2500+ node rendering, label optimization, edge bundling, layer compositing. USE FOR: render, SVG, Canvas, WebGL, WebGPU, LOD, viewport, quadtree, PixiJS, label, edge bundling, compositing, heatmap, glow, sprite batch, instanced rendering, GPU acceleration, framebuffer, render pipeline, tile-based rendering."
tier: "TIER-1/FORGE"
domain: "Rendering architecture — multi-backend pipeline for 2500+ node litigation graphs"
triggers:
  - render
  - SVG
  - Canvas
  - WebGL
  - WebGPU
  - LOD
  - viewport
  - quadtree
  - PixiJS
  - label optimization
  - edge bundling
  - compositing
  - heatmap
  - sprite batch
cross_links:
  - SINGULARITY-MBP-GENESIS
  - SINGULARITY-MBP-FORGE-PHYSICS
  - SINGULARITY-MBP-FORGE-EFFECTS
  - SINGULARITY-MBP-FORGE-DEPLOY
  - SINGULARITY-ui-engineering
data_sources:
  - graph_data_v7.json
  - LAYER_META configurations
  - D3 force simulation output
---

# SINGULARITY-MBP-FORGE-RENDERER

> **The visual cortex of THEMANBEARPIG. Every pixel is a weapon. Every frame is evidence.**

## Architecture: 4-Tier Rendering Pipeline

```
┌─────────────────────────────────────────────────────┐
│                  RENDER PIPELINE                     │
│                                                      │
│  Tier 0: DATA PREP                                   │
│    graph_data_v7.json → parse → typed arrays         │
│    Node/Link classification → render buckets          │
│                                                      │
│  Tier 1: SPATIAL INDEX (Quadtree)                    │
│    d3.quadtree() for O(log n) spatial queries        │
│    Viewport frustum → visible node set               │
│    LOD distance thresholds per zoom level             │
│                                                      │
│  Tier 2: BACKEND SELECTION                           │
│    < 500 nodes visible  → SVG (crisp, interactive)   │
│    500-2000 visible     → Canvas 2D (fast, batched)  │
│    > 2000 visible       → WebGL/PixiJS (GPU accel)   │
│    Future: WebGPU compute shaders for force sim       │
│                                                      │
│  Tier 3: COMPOSITING                                 │
│    Layer-ordered rendering (back to front)            │
│    Bloom/glow post-processing                        │
│    HUD overlay (always on top, never occluded)       │
└─────────────────────────────────────────────────────┘
```

## Layer 1: Quadtree Spatial Index

### 1.1 Viewport Culling (Critical for 2500+ nodes)

```javascript
class SpatialIndex {
  constructor() {
    this.quadtree = null;
    this.visibleNodes = [];
    this.visibleLinks = [];
  }

  rebuild(nodes) {
    this.quadtree = d3.quadtree()
      .x(d => d.x)
      .y(d => d.y)
      .addAll(nodes);
  }

  queryViewport(transform, width, height) {
    // Invert screen coords to graph coords
    const x0 = (0 - transform.x) / transform.k;
    const y0 = (0 - transform.y) / transform.k;
    const x1 = (width - transform.x) / transform.k;
    const y1 = (height - transform.y) / transform.k;

    // Pad viewport by 10% for smooth scrolling
    const pad = Math.max(x1 - x0, y1 - y0) * 0.1;

    this.visibleNodes = [];
    this.quadtree.visit((node, nx0, ny0, nx1, ny1) => {
      // Skip if quadtree cell is entirely outside viewport
      if (nx0 > x1 + pad || nx1 < x0 - pad ||
          ny0 > y1 + pad || ny1 < y0 - pad) return true;

      if (!node.length && node.data) {
        const d = node.data;
        if (d.x >= x0 - pad && d.x <= x1 + pad &&
            d.y >= y0 - pad && d.y <= y1 + pad) {
          this.visibleNodes.push(d);
        }
      }
      return false;
    });

    return this.visibleNodes;
  }

  findNearest(x, y, radius) {
    return this.quadtree.find(x, y, radius);
  }
}
```

### 1.2 Level-of-Detail (LOD) System

```javascript
const LOD_THRESHOLDS = {
  // zoom level → rendering detail
  FULL:    { minZoom: 1.5, labels: true,  icons: true,  edges: 'curved', glow: true  },
  MEDIUM:  { minZoom: 0.5, labels: 'hover', icons: true, edges: 'straight', glow: false },
  LOW:     { minZoom: 0.2, labels: false, icons: false, edges: 'straight', glow: false },
  DOTS:    { minZoom: 0.0, labels: false, icons: false, edges: false,     glow: false }
};

function getLOD(zoom) {
  if (zoom >= LOD_THRESHOLDS.FULL.minZoom) return 'FULL';
  if (zoom >= LOD_THRESHOLDS.MEDIUM.minZoom) return 'MEDIUM';
  if (zoom >= LOD_THRESHOLDS.LOW.minZoom) return 'LOW';
  return 'DOTS';
}

function renderNodeAtLOD(ctx, node, lod, transform) {
  const screenX = node.x * transform.k + transform.x;
  const screenY = node.y * transform.k + transform.y;
  const r = (node.r || 6) * transform.k;

  switch (lod) {
    case 'FULL':
      // Full rendering: circle + icon + label + glow
      drawGlow(ctx, screenX, screenY, r, node._layerColor);
      drawCircle(ctx, screenX, screenY, r, node._layerColor);
      drawIcon(ctx, screenX, screenY, r, node.icon);
      drawLabel(ctx, screenX, screenY + r + 12, node.label, node._layerColor);
      break;

    case 'MEDIUM':
      // Circle + conditional label
      drawCircle(ctx, screenX, screenY, r, node._layerColor);
      if (node._hovered) {
        drawLabel(ctx, screenX, screenY + r + 12, node.label, node._layerColor);
      }
      break;

    case 'LOW':
      // Simple circle only
      ctx.fillStyle = node._layerColor || '#888';
      ctx.beginPath();
      ctx.arc(screenX, screenY, Math.max(r, 2), 0, Math.PI * 2);
      ctx.fill();
      break;

    case 'DOTS':
      // Single pixel dot
      ctx.fillStyle = node._layerColor || '#666';
      ctx.fillRect(screenX - 1, screenY - 1, 2, 2);
      break;
  }
}
```

## Layer 2: Multi-Backend Rendering

### 2.1 SVG Renderer (< 500 nodes)

```javascript
class SVGRenderer {
  constructor(container) {
    this.svg = d3.select(container).append('svg')
      .attr('width', '100%')
      .attr('height', '100%')
      .style('position', 'absolute');

    this.linkGroup = this.svg.append('g').attr('class', 'links');
    this.nodeGroup = this.svg.append('g').attr('class', 'nodes');
    this.labelGroup = this.svg.append('g').attr('class', 'labels');
  }

  render(nodes, links, transform) {
    // Links
    const linkSel = this.linkGroup.selectAll('line')
      .data(links, d => d.source.id + '-' + d.target.id);

    linkSel.enter().append('line')
      .merge(linkSel)
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y)
      .attr('stroke', d => d.color || '#333')
      .attr('stroke-width', d => d.weight || 1)
      .attr('stroke-opacity', 0.4);

    linkSel.exit().remove();

    // Nodes
    const nodeSel = this.nodeGroup.selectAll('circle')
      .data(nodes, d => d.id);

    nodeSel.enter().append('circle')
      .merge(nodeSel)
      .attr('cx', d => d.x)
      .attr('cy', d => d.y)
      .attr('r', d => d.r || 6)
      .attr('fill', d => d._layerColor || '#888')
      .attr('stroke', d => d._selected ? '#fff' : 'none')
      .attr('stroke-width', 2);

    nodeSel.exit().remove();

    // Transform
    this.linkGroup.attr('transform', transform);
    this.nodeGroup.attr('transform', transform);
    this.labelGroup.attr('transform', transform);
  }

  destroy() {
    this.svg.remove();
  }
}
```

### 2.2 Canvas 2D Renderer (500-2000 nodes)

```javascript
class CanvasRenderer {
  constructor(container) {
    const rect = container.getBoundingClientRect();
    this.canvas = document.createElement('canvas');
    this.canvas.width = rect.width * (window.devicePixelRatio || 1);
    this.canvas.height = rect.height * (window.devicePixelRatio || 1);
    this.canvas.style.width = rect.width + 'px';
    this.canvas.style.height = rect.height + 'px';
    container.appendChild(this.canvas);

    this.ctx = this.canvas.getContext('2d');
    this.ctx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);

    this.width = rect.width;
    this.height = rect.height;
  }

  render(nodes, links, transform, lod) {
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.width, this.height);
    ctx.save();
    ctx.translate(transform.x, transform.y);
    ctx.scale(transform.k, transform.k);

    // Batch links by color for fewer state changes
    if (lod !== 'DOTS') {
      const linksByColor = {};
      links.forEach(l => {
        const color = l.color || '#333';
        if (!linksByColor[color]) linksByColor[color] = [];
        linksByColor[color].push(l);
      });

      Object.entries(linksByColor).forEach(([color, batch]) => {
        ctx.strokeStyle = color;
        ctx.globalAlpha = 0.3;
        ctx.lineWidth = 0.5;
        ctx.beginPath();
        batch.forEach(l => {
          ctx.moveTo(l.source.x, l.source.y);
          ctx.lineTo(l.target.x, l.target.y);
        });
        ctx.stroke();
      });
    }

    // Batch nodes by color
    ctx.globalAlpha = 1.0;
    const nodesByColor = {};
    nodes.forEach(n => {
      const color = n._layerColor || '#888';
      if (!nodesByColor[color]) nodesByColor[color] = [];
      nodesByColor[color].push(n);
    });

    Object.entries(nodesByColor).forEach(([color, batch]) => {
      ctx.fillStyle = color;
      ctx.beginPath();
      batch.forEach(n => {
        const r = n.r || 5;
        ctx.moveTo(n.x + r, n.y);
        ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
      });
      ctx.fill();
    });

    // Labels at high LOD
    if (lod === 'FULL') {
      ctx.fillStyle = '#ccc';
      ctx.font = '10px Inter, sans-serif';
      ctx.textAlign = 'center';
      nodes.forEach(n => {
        if (n.label) {
          ctx.fillText(n.label, n.x, n.y + (n.r || 5) + 12);
        }
      });
    }

    ctx.restore();
  }

  destroy() {
    this.canvas.remove();
  }
}
```

### 2.3 WebGL Renderer via PixiJS (2000+ nodes)

```javascript
class WebGLRenderer {
  constructor(container) {
    this.app = new PIXI.Application({
      width: container.clientWidth,
      height: container.clientHeight,
      backgroundColor: 0x0a0a1e,
      antialias: true,
      resolution: window.devicePixelRatio || 1,
      autoDensity: true
    });
    container.appendChild(this.app.view);

    this.worldContainer = new PIXI.Container();
    this.linkGraphics = new PIXI.Graphics();
    this.nodeContainer = new PIXI.Container();

    this.worldContainer.addChild(this.linkGraphics);
    this.worldContainer.addChild(this.nodeContainer);
    this.app.stage.addChild(this.worldContainer);

    this.spritePool = [];
    this.nodeSprites = new Map();
  }

  render(nodes, links, transform) {
    // Update world transform
    this.worldContainer.x = transform.x;
    this.worldContainer.y = transform.y;
    this.worldContainer.scale.set(transform.k);

    // Draw links
    this.linkGraphics.clear();
    links.forEach(l => {
      const color = parseInt((l.color || '#333333').replace('#', ''), 16);
      this.linkGraphics.lineStyle(0.5, color, 0.3);
      this.linkGraphics.moveTo(l.source.x, l.source.y);
      this.linkGraphics.lineTo(l.target.x, l.target.y);
    });

    // Update or create node sprites
    const seen = new Set();
    nodes.forEach(n => {
      seen.add(n.id);
      let sprite = this.nodeSprites.get(n.id);
      if (!sprite) {
        sprite = this.createNodeSprite(n);
        this.nodeSprites.set(n.id, sprite);
        this.nodeContainer.addChild(sprite);
      }
      sprite.x = n.x;
      sprite.y = n.y;
      sprite.tint = parseInt((n._layerColor || '#888888').replace('#', ''), 16);
    });

    // Remove stale sprites
    this.nodeSprites.forEach((sprite, id) => {
      if (!seen.has(id)) {
        this.nodeContainer.removeChild(sprite);
        this.nodeSprites.delete(id);
      }
    });
  }

  createNodeSprite(node) {
    const g = new PIXI.Graphics();
    g.beginFill(0xffffff);
    g.drawCircle(0, 0, node.r || 5);
    g.endFill();
    const texture = this.app.renderer.generateTexture(g);
    const sprite = new PIXI.Sprite(texture);
    sprite.anchor.set(0.5);
    sprite.interactive = true;
    sprite._nodeId = node.id;
    return sprite;
  }

  destroy() {
    this.app.destroy(true, { children: true });
  }
}
```

## Layer 3: Edge Bundling

### 3.1 Force-Directed Edge Bundling (FDEB)

```javascript
function bundleEdges(links, nodes, iterations = 6, step = 0.04) {
  // Subdivide edges into segments
  const subdivisions = 12;
  const bundledLinks = links.map(l => {
    const points = [];
    for (let i = 0; i <= subdivisions; i++) {
      const t = i / subdivisions;
      points.push({
        x: l.source.x + (l.target.x - l.source.x) * t,
        y: l.source.y + (l.target.y - l.source.y) * t
      });
    }
    return { ...l, _points: points };
  });

  // Iterative bundling: attract compatible edge segments
  for (let iter = 0; iter < iterations; iter++) {
    const stepSize = step / (iter + 1);
    for (let i = 0; i < bundledLinks.length; i++) {
      for (let j = i + 1; j < bundledLinks.length; j++) {
        const compatibility = edgeCompatibility(bundledLinks[i], bundledLinks[j]);
        if (compatibility > 0.5) {
          // Attract subdivision points
          for (let k = 1; k < subdivisions; k++) {
            const pi = bundledLinks[i]._points[k];
            const pj = bundledLinks[j]._points[k];
            const dx = (pj.x - pi.x) * stepSize * compatibility;
            const dy = (pj.y - pi.y) * stepSize * compatibility;
            pi.x += dx; pi.y += dy;
            pj.x -= dx; pj.y -= dy;
          }
        }
      }
    }
  }

  return bundledLinks;
}

function edgeCompatibility(e1, e2) {
  // Angle compatibility
  const dx1 = e1.target.x - e1.source.x;
  const dy1 = e1.target.y - e1.source.y;
  const dx2 = e2.target.x - e2.source.x;
  const dy2 = e2.target.y - e2.source.y;
  const len1 = Math.sqrt(dx1*dx1 + dy1*dy1) || 1;
  const len2 = Math.sqrt(dx2*dx2 + dy2*dy2) || 1;
  const dot = (dx1*dx2 + dy1*dy2) / (len1 * len2);
  return Math.abs(dot);  // 0 = perpendicular, 1 = parallel
}

function drawBundledEdge(ctx, link) {
  if (!link._points || link._points.length < 3) return;
  ctx.beginPath();
  ctx.moveTo(link._points[0].x, link._points[0].y);
  for (let i = 1; i < link._points.length - 1; i++) {
    const cp = link._points[i];
    const next = link._points[i + 1];
    const mx = (cp.x + next.x) / 2;
    const my = (cp.y + next.y) / 2;
    ctx.quadraticCurveTo(cp.x, cp.y, mx, my);
  }
  const last = link._points[link._points.length - 1];
  ctx.lineTo(last.x, last.y);
  ctx.stroke();
}
```

## Layer 4: Layer Compositing

### 4.1 Multi-Layer Rendering Order

```javascript
const LAYER_RENDER_ORDER = [
  // Background layers first (dimmer, behind)
  { layer: 'filing',      opacity: 0.3, blur: 0 },
  { layer: 'authority',   opacity: 0.4, blur: 0 },
  { layer: 'evidence',    opacity: 0.5, blur: 0 },
  { layer: 'timeline',    opacity: 0.4, blur: 0 },
  // Mid layers
  { layer: 'weapon',      opacity: 0.6, blur: 0 },
  { layer: 'impeachment', opacity: 0.6, blur: 0 },
  { layer: 'cartel',      opacity: 0.7, blur: 0 },
  // Foreground layers (brighter, on top)
  { layer: 'adversary',   opacity: 0.8, blur: 0 },
  { layer: 'judicial',    opacity: 0.9, blur: 0 },
  // Active/focused layer always on top
  { layer: '_active',     opacity: 1.0, blur: 0 }
];

function renderLayered(ctx, nodes, links, activeLayer, transform) {
  LAYER_RENDER_ORDER.forEach(layerConfig => {
    const layerName = layerConfig.layer;
    if (layerName === '_active') return; // render last

    const layerNodes = nodes.filter(n => n.layer === layerName);
    const layerLinks = links.filter(l =>
      l.source.layer === layerName || l.target.layer === layerName);

    ctx.globalAlpha = layerName === activeLayer ? 1.0 : layerConfig.opacity;
    renderBatch(ctx, layerNodes, layerLinks, transform);
  });

  // Active layer always rendered last (on top)
  if (activeLayer) {
    const activeNodes = nodes.filter(n => n.layer === activeLayer);
    const activeLinks = links.filter(l =>
      l.source.layer === activeLayer || l.target.layer === activeLayer);
    ctx.globalAlpha = 1.0;
    renderBatch(ctx, activeNodes, activeLinks, transform);
  }
}
```

## Layer 5: Label Optimization

### 5.1 Collision-Free Label Placement

```javascript
class LabelPlacer {
  constructor() {
    this.labelRects = [];
  }

  clear() { this.labelRects = []; }

  place(x, y, text, fontSize, priority) {
    const width = text.length * fontSize * 0.6;
    const height = fontSize * 1.2;

    // Try 8 positions around the node
    const offsets = [
      { dx: 0, dy: height + 4 },       // below
      { dx: 0, dy: -(height + 4) },     // above
      { dx: width/2 + 8, dy: 0 },       // right
      { dx: -(width/2 + 8), dy: 0 },    // left
      { dx: width/2, dy: height },       // bottom-right
      { dx: -width/2, dy: height },      // bottom-left
      { dx: width/2, dy: -height },      // top-right
      { dx: -width/2, dy: -height }      // top-left
    ];

    for (const off of offsets) {
      const rect = {
        x: x + off.dx - width/2,
        y: y + off.dy - height/2,
        width, height, text,
        priority
      };

      if (!this.overlaps(rect)) {
        this.labelRects.push(rect);
        return { x: x + off.dx, y: y + off.dy, visible: true };
      }
    }

    // All positions overlap — hide low-priority labels
    if (priority > 5) {
      const rect = {
        x: x - width/2, y: y + height,
        width, height, text, priority
      };
      this.labelRects.push(rect);
      return { x, y: y + height + 4, visible: true };
    }

    return { x: 0, y: 0, visible: false };
  }

  overlaps(rect) {
    return this.labelRects.some(existing =>
      rect.x < existing.x + existing.width &&
      rect.x + rect.width > existing.x &&
      rect.y < existing.y + existing.height &&
      rect.y + rect.height > existing.y
    );
  }
}
```

## Layer 6: Heatmap Rendering

### 6.1 Evidence Density Heatmap

```javascript
function renderHeatmap(ctx, nodes, width, height, transform, radius = 50) {
  // Create offscreen canvas for heatmap
  const offscreen = document.createElement('canvas');
  offscreen.width = width;
  offscreen.height = height;
  const octx = offscreen.getContext('2d');

  // Draw intensity points
  nodes.forEach(n => {
    const sx = n.x * transform.k + transform.x;
    const sy = n.y * transform.k + transform.y;
    const intensity = (n.evidence_count || 1) / 50; // normalize

    const gradient = octx.createRadialGradient(sx, sy, 0, sx, sy, radius);
    gradient.addColorStop(0, `rgba(255, 0, 0, ${Math.min(intensity, 0.8)})`);
    gradient.addColorStop(1, 'rgba(255, 0, 0, 0)');
    octx.fillStyle = gradient;
    octx.fillRect(sx - radius, sy - radius, radius * 2, radius * 2);
  });

  // Color ramp: blue → cyan → green → yellow → red
  const imageData = octx.getImageData(0, 0, width, height);
  const pixels = imageData.data;
  for (let i = 0; i < pixels.length; i += 4) {
    const intensity = pixels[i + 3] / 255; // use alpha as intensity
    const [r, g, b] = heatColor(intensity);
    pixels[i] = r;
    pixels[i + 1] = g;
    pixels[i + 2] = b;
    pixels[i + 3] = intensity > 0.05 ? Math.floor(intensity * 180) : 0;
  }
  octx.putImageData(imageData, 0, 0);

  // Composite onto main canvas
  ctx.globalCompositeOperation = 'screen';
  ctx.drawImage(offscreen, 0, 0);
  ctx.globalCompositeOperation = 'source-over';
}

function heatColor(t) {
  // 0=transparent, 0.25=blue, 0.5=green, 0.75=yellow, 1.0=red
  if (t < 0.25) return [0, 0, Math.floor(t * 4 * 255)];
  if (t < 0.5)  return [0, Math.floor((t - 0.25) * 4 * 255), 255 - Math.floor((t - 0.25) * 4 * 255)];
  if (t < 0.75) return [Math.floor((t - 0.5) * 4 * 255), 255, 0];
  return [255, 255 - Math.floor((t - 0.75) * 4 * 255), 0];
}
```

## Layer 7: Minimap

### 7.1 Overview Minimap Component

```javascript
class Minimap {
  constructor(container, mainWidth, mainHeight) {
    this.scale = 0.12;
    this.width = mainWidth * this.scale;
    this.height = mainHeight * this.scale;

    this.canvas = document.createElement('canvas');
    this.canvas.width = this.width;
    this.canvas.height = this.height;
    this.canvas.style.cssText = `
      position: fixed; bottom: 10px; right: 10px;
      border: 1px solid #ff00ff44; border-radius: 4px;
      background: #0a0a1ecc; cursor: pointer; z-index: 998;
    `;
    container.appendChild(this.canvas);
    this.ctx = this.canvas.getContext('2d');

    // Click on minimap → navigate
    this.canvas.addEventListener('click', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const mx = (e.clientX - rect.left) / this.scale;
      const my = (e.clientY - rect.top) / this.scale;
      this.onNavigate?.(mx, my);
    });
  }

  render(nodes, transform, mainWidth, mainHeight) {
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.width, this.height);

    // Draw all nodes as tiny dots
    ctx.globalAlpha = 0.6;
    nodes.forEach(n => {
      ctx.fillStyle = n._layerColor || '#888';
      ctx.fillRect(
        (n.x + 2000) * this.scale * 0.1,
        (n.y + 2000) * this.scale * 0.1,
        2, 2
      );
    });

    // Draw viewport rectangle
    ctx.globalAlpha = 1.0;
    ctx.strokeStyle = '#ff00ff';
    ctx.lineWidth = 1;
    const vx = (-transform.x / transform.k + 2000) * this.scale * 0.1;
    const vy = (-transform.y / transform.k + 2000) * this.scale * 0.1;
    const vw = (mainWidth / transform.k) * this.scale * 0.1;
    const vh = (mainHeight / transform.k) * this.scale * 0.1;
    ctx.strokeRect(vx, vy, vw, vh);
  }
}
```

## Performance Budgets (60 FPS target on AMD Ryzen 3 + Vega 8)

| Metric | Budget | Technique |
|--------|--------|-----------|
| Frame time | <16.6ms | requestAnimationFrame, batch draw calls |
| Quadtree rebuild | <5ms | O(n log n), incremental updates |
| Viewport cull | <2ms | Quadtree visit with early termination |
| Link rendering | <8ms | Batched by color, single beginPath per batch |
| Node rendering | <4ms | Batched fillRect for DOTS, batched arc for circles |
| Label placement | <3ms | Priority-sorted, collision-skip for low priority |
| Edge bundling | <50ms | Pre-computed, cached until graph changes |
| Heatmap | <20ms | Offscreen canvas, compositor blend |
| LOD switch | <1ms | Threshold check, no re-allocation |
| Minimap | <2ms | Pre-scaled, simple dot rendering |

## Anti-Patterns (MANDATORY — 20 Rules)

1. **NEVER** render all 2500 nodes at DOTS LOD with individual arc() calls — use fillRect
2. **NEVER** skip viewport culling — rendering off-screen nodes wastes 60%+ frame time
3. **NEVER** rebuild quadtree every frame — only on node position changes
4. **NEVER** use SVG for >500 visible nodes — DOM overhead kills FPS
5. **NEVER** draw labels at zoom < 0.5 — unreadable and expensive
6. **NEVER** create new Canvas/WebGL context per frame — reuse
7. **NEVER** use globalCompositeOperation without resetting — bleeds into next draw
8. **NEVER** draw individual link strokes — batch by color in single path
9. **NEVER** skip devicePixelRatio scaling — renders blurry on HiDPI
10. **NEVER** run edge bundling during interaction — pre-compute and cache
11. **NEVER** allocate arrays inside render loop — pre-allocate and reuse
12. **NEVER** use string concatenation for color values in hot path — cache hex→int conversion
13. **NEVER** render minimap at full resolution — 12% scale is sufficient
14. **NEVER** skip layer opacity for inactive layers — visual noise overwhelms
15. **NEVER** render heatmap every frame — cache and invalidate on data change
16. **NEVER** use getImageData in render loop — pixel manipulation is CPU-bound
17. **NEVER** draw text without measuring — cache textWidth for label placement
18. **NEVER** create textures per-frame in WebGL — pool and reuse PIXI textures
19. **NEVER** ignore transform.k for radius scaling — nodes must scale with zoom
20. **NEVER** use setTimeout for animation — always requestAnimationFrame

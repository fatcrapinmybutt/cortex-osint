---
name: SINGULARITY-ui-engineering
description: "Transcendent UI engineering system for litigation visualization and desktop apps. Use when: D3.js force graphs, PixiJS WebGL rendering, pywebview desktop bridges, CustomTkinter screens, Flet next-gen UI, React/Next.js dashboards, Tailwind CSS, shadcn/ui components, SVG/Canvas optimization, LOD rendering, responsive design, accessibility, THEMANBEARPIG 13-layer mega-visualization, evidence gallery, timeline scrubber, filing Kanban, dashboard layout, data storytelling, legal graph visualization, 2500+ node rendering, viewport culling, quadtree spatial indexing, force simulation tuning, WebGL shaders, HUD overlays, minimap, search/filter UI."
---

# SINGULARITY-ui-engineering — Transcendent UI Engineering

> **Absorbs:** fullstack-web, design-ux, React/Next.js/D3
> **Tier:** APP | **Domain:** Visualization, Desktop, Web, Mobile-ready
> **Stack:** D3.js v7 · PixiJS v8 · pywebview · CustomTkinter · Flet · React 19 · Next.js 15 · Tailwind CSS v4 · shadcn/ui

---

## 1. THEMANBEARPIG Mega-Visualization Architecture

### 13-Layer Ontology (D3.js v7 + PixiJS WebGL Hybrid)

```
Layer 0:  SUBSTRATE    — Background grid, fog-of-war, ambient effects
Layer 1:  ADVERSARY    — Person nodes, PageRank centrality, ego networks
Layer 2:  WEAPONS      — 9 weapon types (false allegations → contempt chains)
Layer 3:  JUDICIAL     — McNeill triangle, cartel connections, violation heatmap
Layer 4:  EVIDENCE     — Density clusters, semantic t-SNE, gap voids
Layer 5:  AUTHORITY    — Citation hierarchy, chain completeness, Shepard signals
Layer 6:  IMPEACHMENT  — Credibility scores, contradiction chains, cross-exam links
Layer 7:  TIMELINE     — Temporal scrubber, keyframe milestones, playback
Layer 8:  FILING       — F1-F10 Kanban, EGCP readiness, deadline countdown
Layer 9:  BRAINS       — 23+ brain network, inter-brain flows, health gauges
Layer 10: ENGINES      — 14 engine overlays, MEEK/FRED/Delta999 status
Layer 11: HUD          — Gauges, minimap, FPS counter, alert ticker
Layer 12: NARRATIVE    — Story mode, guided walkthrough, jury presentation
```

### Node Budget & LOD Strategy

| Zoom Level | Nodes Visible | Render Method | Detail |
|------------|---------------|---------------|--------|
| Galaxy (< 0.3x) | 2500+ | PixiJS WebGL sprites | Dots + color only |
| Cluster (0.3-0.7x) | 500-1000 | PixiJS + label sprites | Icons + truncated labels |
| Neighborhood (0.7-1.5x) | 50-200 | SVG overlay on Canvas | Full labels + edges |
| Detail (> 1.5x) | 10-50 | Full SVG DOM | Rich tooltips, expand panels |

```javascript
// LOD renderer pattern — hybrid D3 + PixiJS
class LODRenderer {
  constructor(pixiApp, svgLayer) {
    this.pixi = pixiApp;
    this.svg = svgLayer;
    this.quadtree = d3.quadtree();
    this.zoomLevel = 1.0;
  }

  updateViewport(transform) {
    this.zoomLevel = transform.k;
    const visible = this.quadtree
      .visit(viewportCuller(transform, this.pixi.screen))
      .filter(n => n.visible);

    if (this.zoomLevel < 0.3) {
      this.renderWebGLSprites(visible);
      this.svg.selectAll('*').remove();
    } else if (this.zoomLevel < 1.5) {
      this.renderWebGLSprites(visible);
      this.renderSVGLabels(visible.slice(0, 200));
    } else {
      this.pixi.stage.removeChildren();
      this.renderFullSVG(visible.slice(0, 50));
    }
  }
}
```

### D3 Force Simulation Tuning for Legal Graphs

```javascript
const simulation = d3.forceSimulation(nodes)
  .force('charge', d3.forceManyBody()
    .strength(d => d.type === 'judge' ? -800 : -200)
    .distanceMax(400)
    .theta(0.9))  // Barnes-Hut approximation — 0.9 for speed, 0.5 for accuracy
  .force('link', d3.forceLink(links)
    .id(d => d.id)
    .distance(d => LINK_DISTANCES[d.relationship] || 100)
    .strength(d => d.weight * 0.3))
  .force('center', d3.forceCenter(width / 2, height / 2).strength(0.05))
  .force('collision', d3.forceCollide()
    .radius(d => NODE_RADII[d.type] + 5)
    .iterations(2))
  .force('radial', d3.forceRadial(
    d => LAYER_RADII[d.layer] || 300,
    width / 2, height / 2
  ).strength(0.3))
  .alphaDecay(0.02)       // Slower cooling — more stable layout
  .velocityDecay(0.4)     // Higher friction — less oscillation
  .alphaTarget(0.001);    // Near-zero resting energy

// Orbital force for layer separation
function forceOrbital(layerRadii) {
  return function(alpha) {
    for (const node of nodes) {
      const target = layerRadii[node.layer] || 300;
      const dx = node.x - width / 2;
      const dy = node.y - height / 2;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const k = (target - dist) * alpha * 0.1;
      node.vx += (dx / dist) * k;
      node.vy += (dy / dist) * k;
    }
  };
}
```

---

## 2. PixiJS WebGL Rendering (2500+ Nodes)

### Sprite-Based Node Rendering

```javascript
import { Application, Container, Sprite, Texture, Graphics } from 'pixi.js';

class GraphRenderer {
  constructor(canvas, width, height) {
    this.app = new Application();
    await this.app.init({ canvas, width, height, antialias: true,
      backgroundColor: 0x0a0a0f, resolution: window.devicePixelRatio });

    this.edgeGraphics = new Graphics();
    this.nodeContainer = new Container();
    this.app.stage.addChild(this.edgeGraphics, this.nodeContainer);
  }

  renderNodes(nodes) {
    this.nodeContainer.removeChildren();
    const textures = this.buildTextureAtlas(); // Pre-render node types to atlas

    for (const node of nodes) {
      const sprite = new Sprite(textures[node.type]);
      sprite.anchor.set(0.5);
      sprite.x = node.x;
      sprite.y = node.y;
      sprite.scale.set(NODE_SCALES[node.type] || 0.5);
      sprite.tint = LAYER_COLORS[node.layer];
      sprite.eventMode = 'static';
      sprite.on('pointerover', () => this.showTooltip(node));
      this.nodeContainer.addChild(sprite);
    }
  }

  renderEdges(links) {
    this.edgeGraphics.clear();
    for (const link of links) {
      const alpha = Math.min(link.weight * 0.5, 0.8);
      this.edgeGraphics.moveTo(link.source.x, link.source.y);
      this.edgeGraphics.lineTo(link.target.x, link.target.y);
      this.edgeGraphics.stroke({ width: 1, color: 0x334455, alpha });
    }
  }
}
```

### Viewport Culling with Quadtree

```javascript
function viewportCuller(transform, screen) {
  const invK = 1 / transform.k;
  const x0 = (0 - transform.x) * invK;
  const y0 = (0 - transform.y) * invK;
  const x1 = (screen.width - transform.x) * invK;
  const y1 = (screen.height - transform.y) * invK;
  const pad = 50 * invK; // Buffer zone

  return function(node, bx0, by0, bx1, by1) {
    if (bx0 > x1 + pad || bx1 < x0 - pad ||
        by0 > y1 + pad || by1 < y0 - pad) {
      return true; // Skip — outside viewport
    }
    if (node.data) node.data.visible = true;
  };
}
```

---

## 3. pywebview Desktop Application

### Bridge Pattern (Python ↔ JavaScript)

```python
import webview
import json
from pathlib import Path

class LitigationBridge:
    """Python API exposed to JavaScript via pywebview."""

    def __init__(self, db_path: str):
        self._db = None
        self._db_path = db_path

    @property
    def db(self):
        if self._db is None:
            import sqlite3
            self._db = sqlite3.connect(self._db_path)
            self._db.execute("PRAGMA busy_timeout=60000")
            self._db.execute("PRAGMA journal_mode=WAL")
        return self._db

    def get_graph_data(self, layer: int) -> str:
        rows = self.db.execute(
            "SELECT id, label, type, x, y FROM graph_nodes WHERE layer = ?",
            (layer,)
        ).fetchall()
        return json.dumps([dict(zip(['id','label','type','x','y'], r)) for r in rows])

    def search_evidence(self, query: str) -> str:
        import re
        clean = re.sub(r'[^\w\s*"]', ' ', query).strip()
        try:
            rows = self.db.execute(
                "SELECT quote_text, source_file FROM evidence_fts WHERE evidence_fts MATCH ? LIMIT 20",
                (clean,)
            ).fetchall()
        except Exception:
            rows = self.db.execute(
                "SELECT quote_text, source_file FROM evidence_quotes WHERE quote_text LIKE ? LIMIT 20",
                (f'%{clean}%',)
            ).fetchall()
        return json.dumps([{'quote': r[0], 'source': r[1]} for r in rows])

    def get_separation_days(self) -> int:
        from datetime import date
        return (date.today() - date(2025, 7, 29)).days

if __name__ == '__main__':
    bridge = LitigationBridge("litigation_context.db")
    window = webview.create_window(
        'THEMANBEARPIG — Litigation Intelligence',
        url='index.html', js_api=bridge,
        width=1600, height=1000, resizable=True, min_size=(1200, 800)
    )
    webview.start(debug=False)
```

### JavaScript Bridge Calls

```javascript
// Call Python from JS (pywebview exposes bridge as window.pywebview.api)
async function loadGraphData(layer) {
  const raw = await window.pywebview.api.get_graph_data(layer);
  return JSON.parse(raw);
}

async function searchEvidence(query) {
  const raw = await window.pywebview.api.search_evidence(query);
  return JSON.parse(raw);
}
```

---

## 4. CustomTkinter Legacy Screens

### Screen Template Pattern

```python
import customtkinter as ctk

class EvidenceGalleryScreen(ctk.CTkFrame):
    def __init__(self, master, db_conn, **kwargs):
        super().__init__(master, **kwargs)
        self.db = db_conn
        self._build_ui()

    def _build_ui(self):
        # Search bar
        self.search_var = ctk.StringVar()
        ctk.CTkEntry(self, textvariable=self.search_var,
                     placeholder_text="Search evidence...",
                     width=400).pack(pady=10)
        ctk.CTkButton(self, text="Search", command=self._search).pack(pady=5)

        # Results table
        self.results_frame = ctk.CTkScrollableFrame(self, width=800, height=500)
        self.results_frame.pack(fill="both", expand=True, padx=10, pady=10)

    def _search(self):
        query = self.search_var.get()
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        # FTS5 safe search
        import re
        clean = re.sub(r'[^\w\s*"]', ' ', query).strip()
        rows = self.db.execute(
            "SELECT quote_text, source_file, category FROM evidence_quotes "
            "WHERE quote_text LIKE ? LIMIT 50", (f'%{clean}%',)
        ).fetchall()
        for i, row in enumerate(rows):
            ctk.CTkLabel(self.results_frame, text=row[0][:120],
                         anchor="w", wraplength=700).grid(row=i, column=0, sticky="w")
```

---

## 5. Flet Next-Gen Desktop UI

### Flet Application Pattern

```python
import flet as ft

def main(page: ft.Page):
    page.title = "LitigationOS Dashboard"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20

    # Navigation rail
    rail = ft.NavigationRail(
        selected_index=0,
        destinations=[
            ft.NavigationRailDestination(icon=ft.Icons.DASHBOARD, label="Dashboard"),
            ft.NavigationRailDestination(icon=ft.Icons.SEARCH, label="Evidence"),
            ft.NavigationRailDestination(icon=ft.Icons.TIMELINE, label="Timeline"),
            ft.NavigationRailDestination(icon=ft.Icons.FOLDER, label="Filings"),
        ],
        on_change=lambda e: switch_view(e.control.selected_index),
    )

    content = ft.Column(expand=True)

    def switch_view(index):
        content.controls.clear()
        if index == 0:
            content.controls.append(build_dashboard())
        elif index == 1:
            content.controls.append(build_evidence_search())
        elif index == 2:
            content.controls.append(build_timeline())
        elif index == 3:
            content.controls.append(build_filing_kanban())
        page.update()

    page.add(ft.Row([rail, ft.VerticalDivider(width=1), content], expand=True))
    switch_view(0)

ft.app(target=main)
```

---

## 6. Dashboard Layout Patterns for Litigation Intelligence

### KPI Card Grid

```
┌────────────────┬────────────────┬────────────────┬────────────────┐
│ SEPARATION     │ EVIDENCE       │ FILINGS        │ DEADLINES      │
│ ███ days       │ 175K quotes    │ 8/10 ready     │ 3 URGENT       │
│ ▲ +1 today     │ ▲ +42 new      │ ● F09 next     │ ⚠ COA Apr 15   │
└────────────────┴────────────────┴────────────────┴────────────────┘
┌────────────────────────────────┬────────────────────────────────────┐
│ FILING KANBAN (F1-F10)         │ ADVERSARY THREAT MATRIX            │
│ ┌─────┬─────┬─────┬─────┐     │ ┌─────────────────────────────┐   │
│ │DRAFT│ QA  │READY│FILED│     │ │ Watson ████████░░ 8.2/10    │   │
│ │ F06 │ F03 │ F09 │ F01 │     │ │ McNeill █████████░ 9.1/10   │   │
│ │     │     │ F10 │ F04 │     │ │ Berry ██████░░░░ 5.8/10     │   │
│ │     │     │     │ F05 │     │ │ Rusco ████░░░░░░ 4.2/10     │   │
│ └─────┴─────┴─────┴─────┘     │ └─────────────────────────────┘   │
└────────────────────────────────┴────────────────────────────────────┘
┌────────────────────────────────────────────────────────────────────┐
│ TIMELINE (scrollable, filterable by lane A-F + CRIMINAL)           │
│ ──●──●───●────●──●──────●───●──●────●──●──●──────●──●──►          │
│   2023    2024         2025              2026                      │
└────────────────────────────────────────────────────────────────────┘
```

---

## 7. Accessibility & Performance Standards

### Accessibility Checklist

- All interactive elements: `aria-label`, `role`, `tabindex`
- Color contrast: WCAG AA minimum (4.5:1 text, 3:1 large text)
- Keyboard navigation: Tab/Shift-Tab through all controls
- Screen reader: Semantic HTML, live regions for dynamic updates
- Reduced motion: `prefers-reduced-motion` media query disables animations
- Focus indicators: Visible focus rings on all interactive elements

### Performance Budgets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Initial render | < 500ms | Time to first meaningful paint |
| Graph layout (2500 nodes) | < 2s | Force simulation convergence |
| Search response | < 100ms | FTS5 query + render results |
| Zoom/pan FPS | 60fps | PixiJS WebGL render loop |
| Memory (graph loaded) | < 200MB | Chrome DevTools heap snapshot |
| Bundle size (web) | < 500KB gzip | Webpack analyzer |

### Rendering Pipeline Optimization

```javascript
// RequestAnimationFrame loop with frame budget
let lastFrame = 0;
const FRAME_BUDGET = 16.67; // 60fps target

function renderLoop(timestamp) {
  const elapsed = timestamp - lastFrame;
  if (elapsed >= FRAME_BUDGET) {
    lastFrame = timestamp;
    simulation.tick();
    if (needsRerender) {
      renderer.renderNodes(simulation.nodes());
      renderer.renderEdges(simulation.links());
      needsRerender = false;
    }
  }
  requestAnimationFrame(renderLoop);
}
```

---

## 8. Data Visualization Best Practices for Legal Data

### Color Semantics for Litigation

| Element | Color | Hex | Meaning |
|---------|-------|-----|---------|
| Plaintiff evidence | Electric blue | `#3b82f6` | Our side |
| Defendant evidence | Crimson red | `#ef4444` | Adverse |
| Judicial actions | Gold | `#f59e0b` | Court/judge |
| Deadlines (OK) | Green | `#22c55e` | On track |
| Deadlines (urgent) | Orange | `#f97316` | ≤7 days |
| Deadlines (overdue) | Red | `#dc2626` | Past due |
| Neutral/system | Slate | `#64748b` | Infrastructure |

### Graph Node Type Sizing

| Node Type | Radius | Rationale |
|-----------|--------|-----------|
| Judge | 24px | Central authority figure |
| Party (plaintiff/defendant) | 20px | Key actors |
| Witness | 14px | Supporting cast |
| Evidence document | 10px | Numerous, cluster-able |
| Legal authority | 12px | Citation network |
| Filing | 16px | Action items |
| Event (timeline) | 8px | High volume, small footprint |

---

*SINGULARITY-ui-engineering v1.0 — D3 + PixiJS + pywebview + Flet + React — Apex Visualization*

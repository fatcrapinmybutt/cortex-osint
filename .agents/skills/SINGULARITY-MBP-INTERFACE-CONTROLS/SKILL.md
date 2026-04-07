---
skill: SINGULARITY-MBP-INTERFACE-CONTROLS
version: 1.0.0
tier: TIER-3/INTERFACE
domain: Click handlers, fuzzy search, filter panels, keyboard shortcuts, export, drag-drop, lasso selection, zoom/pan, context menus, tooltips, selection state, accessibility
description: >-
  Interaction layer for THEMANBEARPIG 13-layer graph. Click/double-click/right-click
  handlers, Fuse.js fuzzy search across all layers, multi-select filter panel, keyboard
  shortcuts (1-6 rooms, Ctrl+F, Esc), PNG/SVG/JSON/CSV export, drag-drop node
  rearrangement, lasso selection, zoom/pan controls, context menus, tooltip system,
  selection state management, and WCAG accessibility.
triggers:
  - click handler
  - search
  - filter
  - keyboard shortcut
  - export
  - drag and drop
  - lasso
  - zoom
  - pan
  - context menu
  - tooltip
  - selection
  - accessibility
---

# SINGULARITY-MBP-INTERFACE-CONTROLS

> **Tier 3 — INTERFACE**: Complete interaction system for the THEMANBEARPIG
> 13-layer litigation intelligence mega-visualization. Every user gesture from
> click to keyboard to export, built for pywebview + PyInstaller desktop.

---

## 1. Click Handler Architecture

Three tiers: single-click (select), double-click (drill-down), right-click (context menu).

### 1.1 Unified Click Dispatcher

```javascript
/**
 * Attach all click handlers to graph node selection.
 * @param {d3.Selection} nodeSelection — the circles/groups for graph nodes
 * @param {Object}       state         — shared SelectionState instance
 */
function attachClickHandlers(nodeSelection, state) {
    let clickTimer = null;
    const DOUBLE_CLICK_MS = 300;

    nodeSelection
        .on("click", function (event, d) {
            event.stopPropagation();
            if (clickTimer) {
                clearTimeout(clickTimer);
                clickTimer = null;
                handleDoubleClick(d, state);
                return;
            }
            clickTimer = setTimeout(() => {
                clickTimer = null;
                handleSingleClick(event, d, state);
            }, DOUBLE_CLICK_MS);
        })
        .on("contextmenu", function (event, d) {
            event.preventDefault();
            event.stopPropagation();
            openContextMenu(event, d, state);
        });

    // Click on empty background clears selection
    d3.select("#graph-svg").on("click", () => {
        state.clearSelection();
        closeContextMenu();
    });
}

function handleSingleClick(event, d, state) {
    if (event.ctrlKey || event.metaKey) {
        state.toggleNode(d.id);
    } else if (event.shiftKey) {
        state.extendSelection(d.id);
    } else {
        state.selectSingle(d.id);
    }
    updateSelectionVisuals(state);
}

function handleDoubleClick(d, state) {
    state.selectSingle(d.id);
    openDrillDownPanel(d);
}
```

### 1.2 Drill-Down Panel

```javascript
function openDrillDownPanel(nodeData) {
    const panel = document.getElementById("drill-panel") ||
        (() => { const p = document.createElement("div"); p.id = "drill-panel"; document.body.appendChild(p); return p; })();

    panel.className = "drill-panel open";
    panel.innerHTML = `
        <div class="drill-header">
            <span class="drill-type">${nodeData.type || 'NODE'}</span>
            <span class="drill-title">${nodeData.label || nodeData.id}</span>
            <button class="drill-close" onclick="document.getElementById('drill-panel').classList.remove('open')">✕</button>
        </div>
        <div class="drill-body">
            <div class="drill-meta">
                <div>Layer: ${nodeData.layer || '?'}</div>
                <div>Connections: ${nodeData.degree || 0}</div>
                <div>Severity: ${nodeData.severity || 'N/A'}</div>
            </div>
            <div class="drill-details" id="drill-details"></div>
        </div>
    `;
    if (typeof loadDrillDetails === "function") {
        loadDrillDetails(nodeData, document.getElementById("drill-details"));
    }
}
```

---

## 2. Fuzzy Search with Fuse.js

Search across all 13 layers — nodes, edges, labels — with ranked results.

### 2.1 Search Engine Setup

```javascript
/**
 * Initialize Fuse.js search index from all graph nodes.
 * @param {Array} allNodes — flat array of node objects from all 13 layers
 * @returns {Fuse} configured Fuse instance
 */
function initSearch(allNodes) {
    const options = {
        keys: [
            { name: "label", weight: 0.4 },
            { name: "id", weight: 0.2 },
            { name: "type", weight: 0.15 },
            { name: "layer", weight: 0.1 },
            { name: "metadata", weight: 0.15 },
        ],
        threshold: 0.35,
        distance: 100,
        minMatchCharLength: 2,
        includeScore: true,
        includeMatches: true,
    };
    return new Fuse(allNodes, options);
}

/**
 * Execute search and render results.
 * @param {Fuse}        fuse       — initialized Fuse instance
 * @param {string}      query      — user input
 * @param {HTMLElement}  container  — results list element
 * @param {Function}     onSelect  — callback(nodeId) when result clicked
 */
function executeSearch(fuse, query, container, onSelect) {
    if (!query || query.length < 2) {
        container.innerHTML = "";
        container.classList.remove("visible");
        return;
    }

    const results = fuse.search(query).slice(0, 20);
    container.innerHTML = "";

    if (results.length === 0) {
        container.innerHTML = '<div class="search-empty">No results</div>';
        container.classList.add("visible");
        return;
    }

    results.forEach((r, idx) => {
        const item = document.createElement("div");
        item.className = "search-result";
        item.dataset.nodeId = r.item.id;
        item.tabIndex = 0;
        item.setAttribute("role", "option");
        item.setAttribute("aria-selected", idx === 0 ? "true" : "false");

        const matchStr = highlightMatches(r);
        const score = ((1 - r.score) * 100).toFixed(0);

        item.innerHTML = `
            <span class="sr-layer">${r.item.layer || '?'}</span>
            <span class="sr-label">${matchStr}</span>
            <span class="sr-score">${score}%</span>
        `;
        item.addEventListener("click", () => onSelect(r.item.id));
        container.appendChild(item);
    });
    container.classList.add("visible");
}

function highlightMatches(fuseResult) {
    let text = fuseResult.item.label || fuseResult.item.id;
    if (!fuseResult.matches) return text;
    const match = fuseResult.matches.find(m => m.key === "label" || m.key === "id");
    if (!match) return text;

    let result = "";
    let lastIdx = 0;
    for (const [start, end] of match.indices) {
        result += text.slice(lastIdx, start);
        result += `<mark>${text.slice(start, end + 1)}</mark>`;
        lastIdx = end + 1;
    }
    result += text.slice(lastIdx);
    return result;
}
```

### 2.2 Search Bar CSS

```css
.search-bar {
    position: fixed; top: 12px; left: 50%; transform: translateX(-50%);
    width: 360px; z-index: 500;
    display: none;
}
.search-bar.visible { display: block; }
.search-input {
    width: 100%; padding: 10px 14px;
    background: #0d1117; color: #e6edf3;
    border: 1px solid #30363d; border-radius: 8px;
    font-size: 14px; outline: none;
}
.search-input:focus { border-color: #58a6ff; box-shadow: 0 0 0 3px rgba(88,166,255,0.15); }
.search-results {
    max-height: 320px; overflow-y: auto;
    background: #161b22; border: 1px solid #30363d;
    border-top: none; border-radius: 0 0 8px 8px;
    display: none;
}
.search-results.visible { display: block; }
.search-result {
    display: flex; align-items: center; gap: 8px;
    padding: 8px 12px; cursor: pointer;
    border-bottom: 1px solid #21262d;
}
.search-result:hover, .search-result:focus { background: #1c2333; outline: none; }
.sr-layer { font-size: 10px; color: #8b949e; min-width: 30px; }
.sr-label { flex: 1; font-size: 13px; color: #c9d1d9; }
.sr-label mark { background: rgba(88,166,255,0.3); color: #fff; border-radius: 2px; padding: 0 2px; }
.sr-score { font-size: 10px; color: #484f58; }
.search-empty { padding: 12px; text-align: center; color: #484f58; font-size: 13px; }
```

---

## 3. Filter Panel

Multi-select layers, actor types, date ranges, severity thresholds.

```javascript
/**
 * Build and manage the filter panel state.
 */
class FilterPanel {
    constructor(allLayers, allActorTypes) {
        this.layers = new Set(allLayers);
        this.actorTypes = new Set(allActorTypes);
        this.severityMin = 0;
        this.severityMax = 10;
        this.dateFrom = null;
        this.dateTo = null;
        this.listeners = [];
    }

    onChange(fn) { this.listeners.push(fn); }

    _emit() { this.listeners.forEach(fn => fn(this.getFilters())); }

    toggleLayer(layer) {
        this.layers.has(layer) ? this.layers.delete(layer) : this.layers.add(layer);
        this._emit();
    }

    toggleActorType(type) {
        this.actorTypes.has(type) ? this.actorTypes.delete(type) : this.actorTypes.add(type);
        this._emit();
    }

    setSeverityRange(min, max) {
        this.severityMin = min;
        this.severityMax = max;
        this._emit();
    }

    setDateRange(from, to) {
        this.dateFrom = from;
        this.dateTo = to;
        this._emit();
    }

    getFilters() {
        return {
            layers: new Set(this.layers),
            actorTypes: new Set(this.actorTypes),
            severityMin: this.severityMin,
            severityMax: this.severityMax,
            dateFrom: this.dateFrom,
            dateTo: this.dateTo,
        };
    }

    applyToNodes(nodes) {
        const f = this.getFilters();
        return nodes.filter(n => {
            if (!f.layers.has(n.layer)) return false;
            if (n.actorType && !f.actorTypes.has(n.actorType)) return false;
            if (n.severity != null && (n.severity < f.severityMin || n.severity > f.severityMax)) return false;
            if (f.dateFrom && n.date && n.date < f.dateFrom) return false;
            if (f.dateTo && n.date && n.date > f.dateTo) return false;
            return true;
        });
    }

    render(container) {
        container.innerHTML = `
            <div class="filter-section">
                <h4>Layers</h4>
                <div id="filter-layers" class="filter-chips"></div>
            </div>
            <div class="filter-section">
                <h4>Severity</h4>
                <input type="range" id="filter-sev-min" min="0" max="10" value="${this.severityMin}" step="1">
                <input type="range" id="filter-sev-max" min="0" max="10" value="${this.severityMax}" step="1">
                <span id="sev-display">${this.severityMin}–${this.severityMax}</span>
            </div>
            <div class="filter-section">
                <h4>Date Range</h4>
                <input type="date" id="filter-date-from" value="${this.dateFrom || ''}">
                <input type="date" id="filter-date-to" value="${this.dateTo || ''}">
            </div>
        `;

        const layerDiv = container.querySelector("#filter-layers");
        [...this.layers].forEach(layer => {
            const chip = document.createElement("button");
            chip.className = "filter-chip active";
            chip.textContent = layer;
            chip.addEventListener("click", () => {
                this.toggleLayer(layer);
                chip.classList.toggle("active");
            });
            layerDiv.appendChild(chip);
        });

        container.querySelector("#filter-sev-min").addEventListener("input", e => {
            this.setSeverityRange(+e.target.value, this.severityMax);
            container.querySelector("#sev-display").textContent = `${this.severityMin}–${this.severityMax}`;
        });
        container.querySelector("#filter-sev-max").addEventListener("input", e => {
            this.setSeverityRange(this.severityMin, +e.target.value);
            container.querySelector("#sev-display").textContent = `${this.severityMin}–${this.severityMax}`;
        });
        container.querySelector("#filter-date-from").addEventListener("change", e => {
            this.setDateRange(e.target.value || null, this.dateTo);
        });
        container.querySelector("#filter-date-to").addEventListener("change", e => {
            this.setDateRange(this.dateFrom, e.target.value || null);
        });
    }
}
```

### 3.1 Filter Panel CSS

```css
.filter-panel {
    position: fixed; left: 0; top: 60px;
    width: 240px; height: calc(100vh - 60px);
    background: #0d1117; border-right: 1px solid #21262d;
    padding: 12px; overflow-y: auto; z-index: 400;
    transform: translateX(-100%); transition: transform 0.25s ease;
}
.filter-panel.open { transform: translateX(0); }
.filter-section { margin-bottom: 16px; }
.filter-section h4 { color: #8b949e; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }
.filter-chips { display: flex; flex-wrap: wrap; gap: 4px; }
.filter-chip {
    padding: 4px 10px; border-radius: 12px; font-size: 11px;
    cursor: pointer; border: 1px solid #30363d;
    background: #21262d; color: #8b949e;
}
.filter-chip.active { background: #1f6feb; color: #fff; border-color: #58a6ff; }
input[type="range"] { width: 100%; accent-color: #58a6ff; }
input[type="date"] {
    width: 100%; padding: 4px 8px; margin-bottom: 4px;
    background: #161b22; color: #c9d1d9; border: 1px solid #30363d;
    border-radius: 4px; font-size: 12px;
}
```

---

## 4. Keyboard Shortcuts System

```javascript
/**
 * Register all keyboard shortcuts. Call once at app init.
 * @param {Object} api — object with methods: toggleSearch, zoomIn, zoomOut,
 *                        fitToScreen, toggleFilter, exportPNG, navigateRoom
 */
function registerKeyboardShortcuts(api) {
    const shortcuts = {
        "1":          () => api.navigateRoom(1),
        "2":          () => api.navigateRoom(2),
        "3":          () => api.navigateRoom(3),
        "4":          () => api.navigateRoom(4),
        "5":          () => api.navigateRoom(5),
        "6":          () => api.navigateRoom(6),
        "Escape":     () => api.closeAllPanels(),
        "Delete":     () => api.deleteSelected(),
        "+":          () => api.zoomIn(),
        "-":          () => api.zoomOut(),
        "0":          () => api.fitToScreen(),
        "f":          () => api.toggleFilter(),
        "l":          () => api.toggleLasso(),
        "?":          () => api.showShortcutHelp(),
    };

    const ctrlShortcuts = {
        "f":  () => api.toggleSearch(),
        "a":  () => api.selectAll(),
        "e":  () => api.exportPNG(),
        "s":  () => api.exportSVG(),
        "d":  () => api.exportJSON(),
    };

    document.addEventListener("keydown", (e) => {
        if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;

        const key = e.key.toLowerCase();
        if ((e.ctrlKey || e.metaKey) && ctrlShortcuts[key]) {
            e.preventDefault();
            ctrlShortcuts[key]();
            return;
        }
        if (!e.ctrlKey && !e.metaKey && !e.altKey && shortcuts[e.key]) {
            shortcuts[e.key]();
        }
    });
}
```

### 4.1 Shortcut Help Overlay

```javascript
function showShortcutHelp() {
    let overlay = document.getElementById("shortcut-help");
    if (overlay) { overlay.remove(); return; }

    overlay = document.createElement("div");
    overlay.id = "shortcut-help";
    overlay.className = "shortcut-overlay";
    overlay.innerHTML = `
        <div class="shortcut-card">
            <h3>⌨️ Keyboard Shortcuts</h3>
            <div class="shortcut-grid">
                <div class="sc-group"><h4>Navigation</h4>
                    <div class="sc"><kbd>1</kbd>–<kbd>6</kbd> Room navigation</div>
                    <div class="sc"><kbd>+</kbd>/<kbd>-</kbd> Zoom in/out</div>
                    <div class="sc"><kbd>0</kbd> Fit to screen</div>
                    <div class="sc"><kbd>Arrow keys</kbd> Pan</div>
                </div>
                <div class="sc-group"><h4>Actions</h4>
                    <div class="sc"><kbd>Ctrl+F</kbd> Search</div>
                    <div class="sc"><kbd>Ctrl+A</kbd> Select all</div>
                    <div class="sc"><kbd>Ctrl+E</kbd> Export PNG</div>
                    <div class="sc"><kbd>Ctrl+S</kbd> Export SVG</div>
                    <div class="sc"><kbd>Ctrl+D</kbd> Export JSON</div>
                </div>
                <div class="sc-group"><h4>Tools</h4>
                    <div class="sc"><kbd>F</kbd> Toggle filters</div>
                    <div class="sc"><kbd>L</kbd> Lasso select</div>
                    <div class="sc"><kbd>Esc</kbd> Close panels</div>
                    <div class="sc"><kbd>Del</kbd> Remove selected</div>
                    <div class="sc"><kbd>?</kbd> This help</div>
                </div>
            </div>
            <button onclick="this.closest('.shortcut-overlay').remove()">Close</button>
        </div>
    `;
    document.body.appendChild(overlay);
}
```

---

## 5. Export System

### 5.1 PNG Screenshot via html2canvas

```javascript
async function exportPNG() {
    const svgEl = document.getElementById("graph-svg");
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    const svgData = new XMLSerializer().serializeToString(svgEl);
    const img = new Image();
    const blob = new Blob([svgData], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);

    return new Promise((resolve) => {
        img.onload = () => {
            canvas.width = img.naturalWidth * 2;
            canvas.height = img.naturalHeight * 2;
            ctx.scale(2, 2);
            ctx.drawImage(img, 0, 0);
            URL.revokeObjectURL(url);

            canvas.toBlob(pngBlob => {
                const a = document.createElement("a");
                a.href = URL.createObjectURL(pngBlob);
                a.download = `THEMANBEARPIG_${new Date().toISOString().slice(0,10)}.png`;
                a.click();
                URL.revokeObjectURL(a.href);
                resolve();
            }, "image/png");
        };
        img.src = url;
    });
}
```

### 5.2 SVG Export

```javascript
function exportSVG() {
    const svgEl = document.getElementById("graph-svg").cloneNode(true);
    svgEl.setAttribute("xmlns", "http://www.w3.org/2000/svg");

    const styles = document.createElement("style");
    styles.textContent = getComputedStyles();
    svgEl.insertBefore(styles, svgEl.firstChild);

    const blob = new Blob([new XMLSerializer().serializeToString(svgEl)], { type: "image/svg+xml" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `THEMANBEARPIG_${new Date().toISOString().slice(0,10)}.svg`;
    a.click();
    URL.revokeObjectURL(a.href);
}
```

### 5.3 JSON Data Dump

```javascript
function exportJSON(nodes, links) {
    const payload = {
        exportDate: new Date().toISOString(),
        application: "THEMANBEARPIG",
        version: "1.0.0",
        nodeCount: nodes.length,
        linkCount: links.length,
        nodes: nodes.map(n => ({ id: n.id, label: n.label, layer: n.layer, x: n.x, y: n.y, type: n.type })),
        links: links.map(l => ({ source: l.source.id || l.source, target: l.target.id || l.target, type: l.type })),
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `THEMANBEARPIG_data_${new Date().toISOString().slice(0,10)}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
}
```

### 5.4 CSV Evidence Export

```javascript
function exportCSV(nodes) {
    const headers = ["id", "label", "layer", "type", "severity", "date"];
    const rows = nodes.map(n => headers.map(h => `"${String(n[h] || '').replace(/"/g, '""')}"`).join(","));
    const csv = [headers.join(","), ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `THEMANBEARPIG_evidence_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
}
```

---

## 6. Drag-and-Drop Node Rearrangement

```javascript
function enableNodeDrag(simulation) {
    return d3.drag()
        .on("start", function (event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
            d3.select(this).classed("dragging", true);
        })
        .on("drag", function (event, d) {
            d.fx = event.x;
            d.fy = event.y;
        })
        .on("end", function (event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d3.select(this).classed("dragging", false);
            // Persist position via pywebview bridge
            if (window.pywebview && window.pywebview.api) {
                window.pywebview.api.saveNodePosition(d.id, d.x, d.y);
            }
        });
}
```

---

## 7. Lasso Selection Tool

```javascript
class LassoTool {
    constructor(svg, nodeSelection, state) {
        this.svg = svg;
        this.nodes = nodeSelection;
        this.state = state;
        this.active = false;
        this.path = null;
        this.points = [];
    }

    enable() {
        this.active = true;
        this.svg.style.cursor = "crosshair";

        this.svg.addEventListener("mousedown", this._start);
        this.svg.addEventListener("mousemove", this._move);
        this.svg.addEventListener("mouseup", this._end);
    }

    disable() {
        this.active = false;
        this.svg.style.cursor = "default";
        this.svg.removeEventListener("mousedown", this._start);
        this.svg.removeEventListener("mousemove", this._move);
        this.svg.removeEventListener("mouseup", this._end);
        if (this.path) { this.path.remove(); this.path = null; }
    }

    _start = (e) => {
        if (e.button !== 0) return;
        this.points = [this._svgPoint(e)];
        this.path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        this.path.setAttribute("class", "lasso-path");
        this.path.setAttribute("fill", "rgba(88,166,255,0.1)");
        this.path.setAttribute("stroke", "#58a6ff");
        this.path.setAttribute("stroke-width", "1.5");
        this.path.setAttribute("stroke-dasharray", "4,4");
        this.svg.appendChild(this.path);
    };

    _move = (e) => {
        if (!this.path) return;
        this.points.push(this._svgPoint(e));
        const d = "M" + this.points.map(p => `${p.x},${p.y}`).join("L") + "Z";
        this.path.setAttribute("d", d);
    };

    _end = () => {
        if (!this.path || this.points.length < 3) {
            if (this.path) this.path.remove();
            this.path = null;
            return;
        }

        const selected = [];
        this.nodes.each(function (d) {
            if (pointInPolygon(d.x, d.y, this.points)) {
                selected.push(d.id);
            }
        }.bind(this));

        this.state.setSelection(selected);
        updateSelectionVisuals(this.state);

        this.path.remove();
        this.path = null;
        this.points = [];
    };

    _svgPoint(e) {
        const ctm = this.svg.getScreenCTM().inverse();
        const pt = this.svg.createSVGPoint();
        pt.x = e.clientX; pt.y = e.clientY;
        const svgPt = pt.matrixTransform(ctm);
        return { x: svgPt.x, y: svgPt.y };
    }
}

function pointInPolygon(x, y, polygon) {
    let inside = false;
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
        const xi = polygon[i].x, yi = polygon[i].y;
        const xj = polygon[j].x, yj = polygon[j].y;
        if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) {
            inside = !inside;
        }
    }
    return inside;
}
```

---

## 8. Zoom & Pan Controls

```javascript
function setupZoomPan(svg, graphGroup) {
    const zoom = d3.zoom()
        .scaleExtent([0.1, 8])
        .on("zoom", (event) => {
            graphGroup.attr("transform", event.transform);
        });

    d3.select(svg).call(zoom);

    return {
        zoomIn()      { d3.select(svg).transition().duration(300).call(zoom.scaleBy, 1.3); },
        zoomOut()     { d3.select(svg).transition().duration(300).call(zoom.scaleBy, 0.75); },
        fitToScreen() {
            const bounds = graphGroup.node().getBBox();
            const fullWidth = svg.clientWidth, fullHeight = svg.clientHeight;
            const scale = 0.9 * Math.min(fullWidth / bounds.width, fullHeight / bounds.height);
            const tx = fullWidth / 2 - scale * (bounds.x + bounds.width / 2);
            const ty = fullHeight / 2 - scale * (bounds.y + bounds.height / 2);
            d3.select(svg).transition().duration(500)
                .call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(scale));
        },
        panTo(x, y) {
            d3.select(svg).transition().duration(400)
                .call(zoom.translateTo, x, y);
        },
        getTransform() { return d3.zoomTransform(svg); },
        reset() { d3.select(svg).transition().duration(300).call(zoom.transform, d3.zoomIdentity); },
    };
}
```

---

## 9. Context Menu System

```javascript
function openContextMenu(event, nodeData, state) {
    closeContextMenu();
    const menu = document.createElement("div");
    menu.id = "ctx-menu";
    menu.className = "context-menu";
    menu.style.left = `${event.clientX}px`;
    menu.style.top = `${event.clientY}px`;

    const actions = [
        { label: "📋 View Dossier",       fn: () => openDrillDownPanel(nodeData) },
        { label: "🔗 Find Connections",    fn: () => highlightConnections(nodeData.id) },
        { label: "⚔️ Impeachment Data",    fn: () => openImpeachmentDossier(nodeData, [], []) },
        { label: "📐 Derive Cause of Action", fn: () => deriveCOA(nodeData) },
        { label: "📤 Export Sub-Graph",    fn: () => exportSubGraph(nodeData.id) },
        { label: "🎯 Center on Node",     fn: () => zoomApi.panTo(nodeData.x, nodeData.y) },
        { label: "📌 Pin Position",        fn: () => { nodeData.fx = nodeData.x; nodeData.fy = nodeData.y; } },
        { label: "📌 Unpin",              fn: () => { nodeData.fx = null; nodeData.fy = null; } },
    ];

    actions.forEach(a => {
        const item = document.createElement("div");
        item.className = "ctx-item";
        item.textContent = a.label;
        item.addEventListener("click", () => { a.fn(); closeContextMenu(); });
        menu.appendChild(item);
    });

    document.body.appendChild(menu);
    document.addEventListener("click", closeContextMenu, { once: true });
}

function closeContextMenu() {
    const existing = document.getElementById("ctx-menu");
    if (existing) existing.remove();
}
```

### 9.1 Context Menu CSS

```css
.context-menu {
    position: fixed; z-index: 900;
    background: #161b22; border: 1px solid #30363d;
    border-radius: 8px; padding: 4px 0;
    min-width: 200px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.5);
}
.ctx-item {
    padding: 8px 14px; cursor: pointer;
    font-size: 13px; color: #c9d1d9;
}
.ctx-item:hover { background: #1c2333; }
```

---

## 10. Tooltip System

```javascript
class TooltipManager {
    constructor(delay = 400) {
        this.delay = delay;
        this.timer = null;
        this.el = document.createElement("div");
        this.el.className = "graph-tooltip";
        this.el.setAttribute("role", "tooltip");
        document.body.appendChild(this.el);
    }

    attach(selection) {
        selection
            .on("mouseenter", (event, d) => {
                this.timer = setTimeout(() => this.show(event, d), this.delay);
            })
            .on("mousemove", (event) => {
                this.el.style.left = `${event.clientX + 12}px`;
                this.el.style.top = `${event.clientY - 10}px`;
            })
            .on("mouseleave", () => {
                clearTimeout(this.timer);
                this.el.classList.remove("visible");
            });
    }

    show(event, d) {
        this.el.innerHTML = `
            <div class="tt-header">${d.label || d.id}</div>
            <div class="tt-row"><span>Layer:</span> ${d.layer || '?'}</div>
            <div class="tt-row"><span>Type:</span> ${d.type || '?'}</div>
            ${d.severity != null ? `<div class="tt-row"><span>Severity:</span> ${d.severity}/10</div>` : ''}
            ${d.date ? `<div class="tt-row"><span>Date:</span> ${d.date}</div>` : ''}
            ${d.degree ? `<div class="tt-row"><span>Connections:</span> ${d.degree}</div>` : ''}
        `;
        this.el.style.left = `${event.clientX + 12}px`;
        this.el.style.top = `${event.clientY - 10}px`;
        this.el.classList.add("visible");
    }

    destroy() {
        this.el.remove();
    }
}
```

### 10.1 Tooltip CSS

```css
.graph-tooltip {
    position: fixed; z-index: 800;
    background: #0d1117; border: 1px solid #30363d;
    border-radius: 6px; padding: 8px 12px;
    pointer-events: none; opacity: 0;
    transition: opacity 0.15s; max-width: 260px;
    font-family: 'Segoe UI', sans-serif;
}
.graph-tooltip.visible { opacity: 1; }
.tt-header { font-weight: 700; color: #e6edf3; font-size: 13px; margin-bottom: 4px; }
.tt-row { font-size: 11px; color: #8b949e; }
.tt-row span { color: #58a6ff; }
```

---

## 11. Selection State Management

```javascript
class SelectionState {
    constructor() {
        this.selected = new Set();
        this.listeners = [];
    }

    onChange(fn) { this.listeners.push(fn); }
    _emit() { this.listeners.forEach(fn => fn(this.selected)); }

    selectSingle(id) { this.selected.clear(); this.selected.add(id); this._emit(); }
    toggleNode(id) { this.selected.has(id) ? this.selected.delete(id) : this.selected.add(id); this._emit(); }
    setSelection(ids) { this.selected = new Set(ids); this._emit(); }
    clearSelection() { this.selected.clear(); this._emit(); }
    isSelected(id) { return this.selected.has(id); }
    count() { return this.selected.size; }

    extendSelection(id) {
        this.selected.add(id);
        this._emit();
    }
}

function updateSelectionVisuals(state) {
    d3.selectAll(".graph-node")
        .classed("selected", d => state.isSelected(d.id))
        .attr("stroke-width", d => state.isSelected(d.id) ? 3 : 1.5)
        .attr("stroke", d => state.isSelected(d.id) ? "#58a6ff" : d._originalStroke || "#333");

    const count = state.count();
    const badge = document.getElementById("selection-badge");
    if (badge) {
        badge.textContent = count > 0 ? `${count} selected` : "";
        badge.style.display = count > 0 ? "inline-block" : "none";
    }
}
```

---

## 12. Accessibility (WCAG 2.1 AA)

```javascript
function applyAccessibility(nodeSelection, linkSelection) {
    nodeSelection
        .attr("role", "img")
        .attr("tabindex", 0)
        .attr("aria-label", d => `${d.type || 'Node'}: ${d.label || d.id}, Layer ${d.layer || 'unknown'}${d.severity != null ? ', severity ' + d.severity : ''}`)
        .on("keydown", function (event, d) {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                handleSingleClick(event, d, window._selectionState);
            }
        });

    linkSelection
        .attr("role", "presentation")
        .attr("aria-hidden", "true");

    const svg = document.getElementById("graph-svg");
    svg.setAttribute("role", "application");
    svg.setAttribute("aria-label", "THEMANBEARPIG litigation intelligence graph — 13 layers of case data. Use keyboard or mouse to explore nodes and connections.");

    const liveRegion = document.createElement("div");
    liveRegion.id = "graph-live-region";
    liveRegion.setAttribute("role", "status");
    liveRegion.setAttribute("aria-live", "polite");
    liveRegion.className = "sr-only";
    document.body.appendChild(liveRegion);
}

function announceToScreenReader(message) {
    const region = document.getElementById("graph-live-region");
    if (region) region.textContent = message;
}
```

### 12.1 Screen Reader CSS

```css
.sr-only {
    position: absolute; width: 1px; height: 1px;
    padding: 0; margin: -1px; overflow: hidden;
    clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0;
}
```

---

## 13. Anti-Patterns (MANDATORY — 18 Rules)

| #  | Anti-Pattern | Why It Fails |
|----|-------------|-------------|
| 1  | Using `setTimeout(0)` for double-click detection | Too fast — use 250-350ms threshold |
| 2  | Attaching handlers inside render loops | Stacking listeners — attach once, use data binding |
| 3  | Using `window.open` for export downloads | Blocked by popup blockers — use `<a>` click trigger |
| 4  | Non-debounced search input | Freezes on every keystroke — debounce 200ms minimum |
| 5  | Rendering all Fuse.js results | DOM thrash with 1000+ matches — cap at 20 visible results |
| 6  | Forgetting to close context menu on outside click | Stale menus stack — always dismiss on next click |
| 7  | Lasso without SVG coordinate transform | Coordinates wrong — always use `getScreenCTM().inverse()` |
| 8  | Zoom without scale extent limits | User zooms to infinity — clamp with `scaleExtent([0.1, 8])` |
| 9  | Not preventing default on keyboard shortcuts | Browser actions fire — `e.preventDefault()` on Ctrl combos |
| 10 | Tooltip without pointer-events:none | Tooltip blocks node clicks — CSS must include this rule |
| 11 | Drag without simulation alpha reset | Nodes freeze after drag — call `alphaTarget(0)` on drag end |
| 12 | Export without embedded styles | Exported SVG is unstyled — inline critical CSS into SVG |
| 13 | Selection state using array instead of Set | O(n) lookup — use Set for O(1) `has()` checks |
| 14 | Keyboard handler on wrong element | Input fields trigger shortcuts — guard with `tagName` check |
| 15 | Filter panel without debounced emit | Re-renders graph on every checkbox — batch filter changes |
| 16 | Context menu positioned outside viewport | Clipped — bounds-check against `window.innerWidth/Height` |
| 17 | Missing ARIA labels on nodes | Inaccessible to screen readers — always set `aria-label` |
| 18 | Export including child's full name | MCR 8.119(H) violation — sanitize all exported data |

---

## 14. Performance Budgets

| Metric | Budget | Measurement |
|--------|--------|-------------|
| Single-click to visual feedback | < 16ms | One frame budget |
| Search result render (20 items) | < 30ms | Fuse.search + DOM append |
| Filter apply (2500 nodes) | < 50ms | Filter + visibility toggle |
| Context menu open | < 10ms | createElement + position |
| Lasso selection (100 nodes) | < 20ms | Point-in-polygon + state update |
| PNG export (2x resolution) | < 2s | SVG → Canvas → Blob |
| SVG export (full graph) | < 500ms | Clone + serialize |
| Tooltip show | < 5ms | innerHTML + position |
| Zoom animation | 60fps | D3 zoom transition |
| Keyboard shortcut response | < 16ms | Event → action |

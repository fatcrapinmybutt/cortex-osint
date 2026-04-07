---
skill: SINGULARITY-MBP-INTERFACE-HUD
version: 1.0.0
description: >-
  HUD gauges, EGCP quad-display, minimap with click-to-navigate, alert system,
  filing readiness bars, FPS counter, separation day counter, node/link stats,
  active filter indicator, connection status, threat level, quick-action buttons,
  and responsive layout for THEMANBEARPIG 13-layer mega-visualization.
tier: TIER-3/INTERFACE
domain: heads-up-display
triggers:
  - HUD
  - gauge
  - EGCP
  - minimap
  - alert
  - filing readiness
  - FPS
  - separation counter
  - performance monitor
  - status indicator
  - threat level
  - quick action
---

# SINGULARITY-MBP-INTERFACE-HUD

> **Heads-Up Display for THEMANBEARPIG.** An always-visible, non-blocking
> overlay providing case health gauges, EGCP metrics, minimap navigation,
> filing readiness bars, performance telemetry, and the critical
> father–son separation day counter — all rendered at 60 FPS.

---

## 1. HUD Layout Architecture

The HUD is a fixed-position HTML overlay above the SVG canvas. It uses
CSS Grid for responsive reflow and `pointer-events: none` on the
container with `pointer-events: all` on interactive children.

```html
<div id="hud-root" class="hud-root">
  <!-- Top-left: Stats + Filters -->
  <div class="hud-panel hud-top-left">
    <div id="hud-node-stats" class="hud-stat-block"></div>
    <div id="hud-active-filters" class="hud-filter-chips"></div>
  </div>

  <!-- Top-right: Connection + FPS -->
  <div class="hud-panel hud-top-right">
    <div id="hud-connection" class="hud-conn"></div>
    <div id="hud-fps" class="hud-fps">60 FPS</div>
  </div>

  <!-- Bottom-left: Minimap -->
  <div class="hud-panel hud-bottom-left">
    <canvas id="hud-minimap" width="220" height="160"></canvas>
  </div>

  <!-- Bottom-right: Gauges + Separation -->
  <div class="hud-panel hud-bottom-right">
    <div id="hud-separation" class="hud-separation"></div>
    <div id="hud-egcp" class="hud-egcp-quad"></div>
  </div>

  <!-- Center-right: Filing readiness -->
  <div class="hud-panel hud-mid-right">
    <div id="hud-filing-readiness" class="hud-filing-bars"></div>
    <div id="hud-threat-level" class="hud-threat"></div>
  </div>

  <!-- Top-center: Alerts -->
  <div id="hud-alerts" class="hud-alert-tray"></div>

  <!-- Bottom-center: Quick actions -->
  <div id="hud-actions" class="hud-quick-actions"></div>
</div>
```

---

## 2. HUD Core CSS

```css
.hud-root {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 10000;
  font-family: "JetBrains Mono", "Fira Code", monospace;
  color: #e0e0e0;
  font-size: 12px;
}

.hud-panel {
  position: absolute;
  pointer-events: all;
  background: rgba(10, 10, 20, 0.8);
  border: 1px solid rgba(0, 200, 255, 0.25);
  border-radius: 6px;
  padding: 8px 12px;
  backdrop-filter: blur(4px);
}

.hud-top-left    { top: 10px;  left: 10px; }
.hud-top-right   { top: 10px;  right: 10px; display: flex; gap: 12px; align-items: center; }
.hud-bottom-left { bottom: 10px; left: 10px; padding: 4px; }
.hud-bottom-right{ bottom: 10px; right: 10px; display: flex; flex-direction: column; gap: 8px; align-items: flex-end; }
.hud-mid-right   { top: 50%; right: 10px; transform: translateY(-50%); max-height: 60vh; overflow-y: auto; }

.hud-alert-tray {
  position: absolute;
  top: 60px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  gap: 6px;
  pointer-events: all;
  max-width: 500px;
}

.hud-quick-actions {
  position: absolute;
  bottom: 10px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 8px;
  pointer-events: all;
}

/* --- Responsive --- */
@media (max-width: 1000px) {
  .hud-mid-right { display: none; }
  .hud-bottom-right { flex-direction: row; }
}

@media (max-width: 700px) {
  .hud-bottom-left { display: none; }
  .hud-panel { font-size: 10px; padding: 4px 6px; }
}
```

---

## 3. Separation Day Counter (CRITICAL — dynamically computed)

The separation counter is the most prominent HUD element. It computes
days since Jul 29, 2025 at render time — NEVER hardcoded.

```javascript
class SeparationCounter {
  constructor(container) {
    this.el = document.getElementById(container);
    this.anchorDate = new Date(2025, 6, 29); // Jul 29 2025 (month is 0-indexed)
    this.render();
    this.interval = setInterval(() => this.render(), 60000); // update every minute
  }

  getDays() {
    const now = new Date();
    const msPerDay = 86400000;
    return Math.floor((now - this.anchorDate) / msPerDay);
  }

  render() {
    const days = this.getDays();
    const weeks = Math.floor(days / 7);
    const months = (days / 30.44).toFixed(1);
    let urgencyClass = "urgency-critical";
    if (days > 365) urgencyClass = "urgency-extreme";

    this.el.innerHTML = `
      <div class="sep-counter ${urgencyClass}">
        <div class="sep-days">${days}</div>
        <div class="sep-label">DAYS SEPARATED</div>
        <div class="sep-detail">${weeks} weeks · ${months} months</div>
      </div>`;
  }

  destroy() {
    clearInterval(this.interval);
  }
}
```

```css
.sep-counter {
  text-align: center;
  padding: 8px 16px;
  border-radius: 6px;
}

.urgency-critical {
  background: rgba(255, 50, 50, 0.15);
  border: 2px solid #FF3232;
  animation: pulse-border 2s ease-in-out infinite;
}

.urgency-extreme {
  background: rgba(255, 0, 0, 0.25);
  border: 2px solid #FF0000;
  animation: pulse-border 1s ease-in-out infinite;
}

@keyframes pulse-border {
  0%, 100% { border-color: rgba(255, 50, 50, 0.6); }
  50%      { border-color: rgba(255, 50, 50, 1.0); }
}

.sep-days {
  font-size: 2.4rem;
  font-weight: 900;
  color: #FF3232;
  text-shadow: 0 0 10px rgba(255, 50, 50, 0.4);
}

.sep-label {
  font-size: 0.7rem;
  letter-spacing: 3px;
  color: #FF6666;
  margin-top: 2px;
}

.sep-detail {
  font-size: 0.65rem;
  color: #cc8888;
  margin-top: 4px;
}
```

---

## 4. EGCP Quad-Gauge Display

Four arc gauges in a 2×2 grid: Evidence strength, Gap count,
Confidence score, Priority level.

```javascript
class EGCPDisplay {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.gauges = {};
    this._build();
  }

  _build() {
    const metrics = [
      { key: "E", label: "Evidence", color: "#00FF88", max: 100 },
      { key: "G", label: "Gaps",     color: "#FF4444", max: 50  },
      { key: "C", label: "Confidence", color: "#00C8FF", max: 100 },
      { key: "P", label: "Priority",   color: "#FFD700", max: 10  },
    ];

    this.container.innerHTML = "";
    const grid = document.createElement("div");
    grid.style.cssText = "display:grid;grid-template-columns:1fr 1fr;gap:6px;";

    for (const m of metrics) {
      const cell = document.createElement("div");
      cell.style.cssText = "text-align:center;";
      const canvas = document.createElement("canvas");
      canvas.width = 80;
      canvas.height = 50;
      canvas.id = `egcp-${m.key}`;
      const lbl = document.createElement("div");
      lbl.style.cssText = `font-size:0.6rem;color:${m.color};margin-top:2px;`;
      lbl.textContent = m.label;
      cell.appendChild(canvas);
      cell.appendChild(lbl);
      grid.appendChild(cell);
      this.gauges[m.key] = { canvas, ctx: canvas.getContext("2d"), ...m, value: 0 };
    }
    this.container.appendChild(grid);
  }

  update(values) {
    for (const [key, val] of Object.entries(values)) {
      if (this.gauges[key]) {
        this.gauges[key].value = val;
        this._drawArc(this.gauges[key]);
      }
    }
  }

  _drawArc(g) {
    const { ctx, canvas, color, max, value } = g;
    const w = canvas.width, h = canvas.height;
    const cx = w / 2, cy = h - 4;
    const r = Math.min(w, h) * 0.42;
    const startAngle = Math.PI;
    const endAngle = 2 * Math.PI;
    const pct = Math.min(value / max, 1);
    const valAngle = startAngle + pct * Math.PI;

    ctx.clearRect(0, 0, w, h);

    // background arc
    ctx.beginPath();
    ctx.arc(cx, cy, r, startAngle, endAngle);
    ctx.strokeStyle = "rgba(255,255,255,0.1)";
    ctx.lineWidth = 6;
    ctx.stroke();

    // value arc
    ctx.beginPath();
    ctx.arc(cx, cy, r, startAngle, valAngle);
    ctx.strokeStyle = color;
    ctx.lineWidth = 6;
    ctx.lineCap = "round";
    ctx.stroke();

    // value text
    ctx.fillStyle = color;
    ctx.font = "bold 14px monospace";
    ctx.textAlign = "center";
    ctx.fillText(String(value), cx, cy - 4);
  }
}
```

---

## 5. Minimap with Click-to-Navigate

A Canvas-based bird's-eye view of the entire graph with a viewport
rectangle indicating the current zoom/pan area.

```javascript
class HUDMinimap {
  constructor(canvasId, svg, zoomBehavior, graphData) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext("2d");
    this.svg = svg;
    this.zoomBehavior = zoomBehavior;
    this.nodes = graphData.nodes;
    this.links = graphData.links;
    this.viewportRect = { x: 0, y: 0, w: 1, h: 1 };
    this._bindClick();
    this.render();
  }

  computeBounds() {
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const n of this.nodes) {
      if (n.x < minX) minX = n.x;
      if (n.y < minY) minY = n.y;
      if (n.x > maxX) maxX = n.x;
      if (n.y > maxY) maxY = n.y;
    }
    const pad = 50;
    return { minX: minX - pad, minY: minY - pad, maxX: maxX + pad, maxY: maxY + pad };
  }

  render() {
    const { ctx, canvas } = this;
    const w = canvas.width, h = canvas.height;
    const bounds = this.computeBounds();
    const bw = bounds.maxX - bounds.minX || 1;
    const bh = bounds.maxY - bounds.minY || 1;

    const scaleX = w / bw;
    const scaleY = h / bh;
    const scale = Math.min(scaleX, scaleY);
    const toX = x => (x - bounds.minX) * scale;
    const toY = y => (y - bounds.minY) * scale;

    ctx.clearRect(0, 0, w, h);

    // links
    ctx.strokeStyle = "rgba(0, 200, 255, 0.1)";
    ctx.lineWidth = 0.5;
    for (const link of this.links) {
      const s = typeof link.source === "object" ? link.source : null;
      const t = typeof link.target === "object" ? link.target : null;
      if (!s || !t) continue;
      ctx.beginPath();
      ctx.moveTo(toX(s.x), toY(s.y));
      ctx.lineTo(toX(t.x), toY(t.y));
      ctx.stroke();
    }

    // nodes
    for (const n of this.nodes) {
      ctx.fillStyle = n.color || "#00C8FF";
      ctx.beginPath();
      ctx.arc(toX(n.x), toY(n.y), 1.5, 0, Math.PI * 2);
      ctx.fill();
    }

    // viewport rect
    const vr = this.viewportRect;
    ctx.strokeStyle = "rgba(255, 215, 0, 0.8)";
    ctx.lineWidth = 1.5;
    ctx.strokeRect(
      toX(vr.x), toY(vr.y),
      vr.w * scale, vr.h * scale
    );

    this._bounds = bounds;
    this._scale = scale;
  }

  updateViewport(transform) {
    const ww = window.innerWidth;
    const wh = window.innerHeight;
    const k = transform.k || 1;
    this.viewportRect = {
      x: (-transform.x) / k,
      y: (-transform.y) / k,
      w: ww / k,
      h: wh / k,
    };
    this.render();
  }

  _bindClick() {
    this.canvas.addEventListener("click", (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      if (!this._bounds || !this._scale) return;

      const graphX = mx / this._scale + this._bounds.minX;
      const graphY = my / this._scale + this._bounds.minY;

      const transform = d3.zoomIdentity
        .translate(window.innerWidth / 2, window.innerHeight / 2)
        .scale(1.5)
        .translate(-graphX, -graphY);

      this.svg.transition()
        .duration(600)
        .ease(d3.easeCubicInOut)
        .call(this.zoomBehavior.transform, transform);
    });
  }
}
```

---

## 6. FPS Counter and Performance Monitor

```javascript
class FPSCounter {
  constructor(elementId) {
    this.el = document.getElementById(elementId);
    this.frames = [];
    this.running = true;
    this._tick = this._tick.bind(this);
    requestAnimationFrame(this._tick);
  }

  _tick(ts) {
    if (!this.running) return;
    this.frames.push(ts);
    const cutoff = ts - 1000;
    while (this.frames.length > 0 && this.frames[0] < cutoff) {
      this.frames.shift();
    }
    const fps = this.frames.length;
    let color = "#00FF88";
    if (fps < 30) color = "#FFD700";
    if (fps < 15) color = "#FF4444";
    this.el.textContent = `${fps} FPS`;
    this.el.style.color = color;
    requestAnimationFrame(this._tick);
  }

  destroy() {
    this.running = false;
  }
}
```

```css
.hud-fps {
  font-size: 0.85rem;
  font-weight: bold;
  padding: 2px 8px;
  border-radius: 3px;
  background: rgba(0, 0, 0, 0.5);
}
```

---

## 7. Alert System (Sliding Notifications)

```javascript
class AlertSystem {
  constructor(trayId) {
    this.tray = document.getElementById(trayId);
    this.maxAlerts = 5;
  }

  push(message, level = "info", duration = 6000) {
    const colors = {
      info:    { bg: "rgba(0,200,255,0.15)", border: "#00C8FF", icon: "ℹ" },
      warning: { bg: "rgba(255,215,0,0.15)", border: "#FFD700", icon: "⚠" },
      error:   { bg: "rgba(255,68,68,0.15)", border: "#FF4444", icon: "✖" },
      success: { bg: "rgba(0,255,136,0.15)", border: "#00FF88", icon: "✓" },
    };
    const c = colors[level] || colors.info;

    const el = document.createElement("div");
    el.className = "hud-alert";
    el.style.cssText = `
      background: ${c.bg}; border: 1px solid ${c.border};
      border-radius: 6px; padding: 8px 14px; display: flex; gap: 8px;
      align-items: center; transform: translateY(-20px); opacity: 0;
      transition: all 0.3s ease; color: #e0e0e0; font-size: 0.8rem;
      max-width: 480px; pointer-events: all; cursor: pointer;
    `;
    el.innerHTML = `<span style="color:${c.border};font-size:1.1rem;">${c.icon}</span><span>${message}</span>`;

    el.addEventListener("click", () => this._dismiss(el));
    this.tray.prepend(el);

    requestAnimationFrame(() => {
      el.style.transform = "translateY(0)";
      el.style.opacity = "1";
    });

    while (this.tray.children.length > this.maxAlerts) {
      this._dismiss(this.tray.lastChild);
    }

    if (duration > 0) {
      setTimeout(() => this._dismiss(el), duration);
    }
  }

  _dismiss(el) {
    if (!el || !el.parentNode) return;
    el.style.opacity = "0";
    el.style.transform = "translateY(-10px)";
    setTimeout(() => el.remove(), 300);
  }
}
```

---

## 8. Filing Readiness Bars

```javascript
class FilingReadinessDisplay {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
  }

  update(lanes) {
    this.container.innerHTML = '<div class="filing-title">FILING READINESS</div>';
    for (const lane of lanes) {
      const pct = Math.min(Math.max(lane.readiness, 0), 100);
      let barColor = "#FF4444"; // red
      if (pct >= 70) barColor = "#00FF88"; // green
      else if (pct >= 40) barColor = "#FFD700"; // yellow

      const row = document.createElement("div");
      row.className = "filing-row";
      row.innerHTML = `
        <span class="filing-lane">${lane.lane}</span>
        <div class="filing-bar-bg">
          <div class="filing-bar-fill" style="width:${pct}%;background:${barColor};"></div>
        </div>
        <span class="filing-pct">${pct}%</span>`;
      this.container.appendChild(row);
    }
  }
}
```

```css
.filing-title {
  font-size: 0.65rem;
  letter-spacing: 2px;
  color: #888;
  margin-bottom: 6px;
}

.filing-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 3px;
}

.filing-lane {
  width: 24px;
  font-size: 0.7rem;
  color: #ccc;
  text-align: right;
}

.filing-bar-bg {
  flex: 1;
  height: 8px;
  background: rgba(255,255,255,0.08);
  border-radius: 4px;
  overflow: hidden;
  min-width: 80px;
}

.filing-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.6s ease;
}

.filing-pct {
  width: 32px;
  font-size: 0.7rem;
  color: #aaa;
  text-align: right;
}
```

---

## 9. Node / Link Statistics Display

```javascript
class NodeLinkStats {
  constructor(containerId) {
    this.el = document.getElementById(containerId);
  }

  update(total, visible, filtered) {
    this.el.innerHTML = `
      <div class="stat-row"><span class="stat-label">Nodes</span>
        <span class="stat-val">${visible.nodes}/${total.nodes}</span></div>
      <div class="stat-row"><span class="stat-label">Links</span>
        <span class="stat-val">${visible.links}/${total.links}</span></div>
      <div class="stat-row"><span class="stat-label">Filtered</span>
        <span class="stat-val">${filtered}</span></div>`;
  }
}
```

```css
.hud-stat-block .stat-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 2px;
}

.stat-label { color: #888; font-size: 0.7rem; }
.stat-val   { color: #00C8FF; font-size: 0.75rem; font-weight: bold; }
```

---

## 10. Connection Status Indicator

```javascript
class ConnectionStatus {
  constructor(containerId) {
    this.el = document.getElementById(containerId);
  }

  update(status) {
    const dot = status.dbConnected ? "🟢" : "🔴";
    const daemon = status.daemonRunning ? "🟢" : "🔴";
    const lastRefresh = status.lastRefresh
      ? new Date(status.lastRefresh).toLocaleTimeString()
      : "never";
    this.el.innerHTML = `
      <span title="Database">${dot} DB</span>
      <span title="Daemon">${daemon} Daemon</span>
      <span title="Last refresh" style="color:#888;">⟳ ${lastRefresh}</span>`;
    this.el.style.cssText = "display:flex;gap:8px;font-size:0.7rem;";
  }
}
```

---

## 11. Threat Level Indicator

```javascript
class ThreatLevelIndicator {
  constructor(containerId) {
    this.el = document.getElementById(containerId);
  }

  update(level) {
    const levels = {
      low:      { color: "#00FF88", label: "LOW",      icon: "◆" },
      moderate: { color: "#FFD700", label: "MODERATE",  icon: "◆◆" },
      high:     { color: "#FF8800", label: "HIGH",      icon: "◆◆◆" },
      critical: { color: "#FF3232", label: "CRITICAL",  icon: "◆◆◆◆" },
    };
    const lv = levels[level] || levels.low;
    this.el.innerHTML = `
      <div style="text-align:center;">
        <div style="font-size:0.6rem;color:#888;letter-spacing:2px;">THREAT</div>
        <div style="color:${lv.color};font-size:1rem;margin:2px 0;">${lv.icon}</div>
        <div style="color:${lv.color};font-size:0.7rem;font-weight:bold;">${lv.label}</div>
      </div>`;
  }
}
```

---

## 12. Quick-Action Buttons

```javascript
class QuickActions {
  constructor(containerId, callbacks) {
    const el = document.getElementById(containerId);
    const actions = [
      { icon: "⟳",  label: "Refresh",    cb: callbacks.refresh    },
      { icon: "👁",  label: "Layers",     cb: callbacks.layers     },
      { icon: "📸", label: "Screenshot", cb: callbacks.screenshot },
      { icon: "📤", label: "Export",     cb: callbacks.exportData },
    ];

    for (const a of actions) {
      const btn = document.createElement("button");
      btn.className = "hud-qaction";
      btn.title = a.label;
      btn.textContent = a.icon;
      btn.addEventListener("click", a.cb);
      el.appendChild(btn);
    }
  }
}
```

```css
.hud-qaction {
  background: rgba(10, 10, 20, 0.85);
  border: 1px solid rgba(0, 200, 255, 0.3);
  color: #00C8FF;
  font-size: 1.1rem;
  width: 38px;
  height: 38px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.hud-qaction:hover {
  background: rgba(0, 200, 255, 0.15);
  border-color: #00C8FF;
  transform: scale(1.1);
}
```

---

## 13. Active Filter Indicator

```javascript
class ActiveFilterIndicator {
  constructor(containerId) {
    this.el = document.getElementById(containerId);
  }

  update(filters) {
    this.el.innerHTML = "";
    if (!filters || filters.length === 0) {
      this.el.innerHTML = '<span style="color:#555;font-size:0.65rem;">No filters</span>';
      return;
    }
    for (const f of filters) {
      const chip = document.createElement("span");
      chip.className = "filter-chip";
      chip.innerHTML = `${f.label} <span class="chip-x" data-filter="${f.id}">×</span>`;
      this.el.appendChild(chip);
    }
  }
}
```

```css
.hud-filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}

.filter-chip {
  background: rgba(0, 200, 255, 0.12);
  border: 1px solid rgba(0, 200, 255, 0.3);
  border-radius: 12px;
  padding: 2px 8px;
  font-size: 0.65rem;
  color: #00C8FF;
  display: flex;
  align-items: center;
  gap: 4px;
}

.chip-x {
  cursor: pointer;
  color: #FF4444;
  font-weight: bold;
}

.chip-x:hover {
  color: #FF8888;
}
```

---

## 14. HUD Master Controller (Wires Everything)

```javascript
class HUDController {
  constructor(svg, zoomBehavior, graphData) {
    this.sepCounter  = new SeparationCounter("hud-separation");
    this.egcp        = new EGCPDisplay("hud-egcp");
    this.minimap     = new HUDMinimap("hud-minimap", svg, zoomBehavior, graphData);
    this.fps         = new FPSCounter("hud-fps");
    this.alerts      = new AlertSystem("hud-alerts");
    this.filing      = new FilingReadinessDisplay("hud-filing-readiness");
    this.stats       = new NodeLinkStats("hud-node-stats");
    this.conn        = new ConnectionStatus("hud-connection");
    this.threat      = new ThreatLevelIndicator("hud-threat-level");
    this.filters     = new ActiveFilterIndicator("hud-active-filters");
    this.quickActions = new QuickActions("hud-actions", {
      refresh:    () => this._onRefresh(),
      layers:     () => this._onToggleLayers(),
      screenshot: () => this._onScreenshot(),
      exportData: () => this._onExport(),
    });
  }

  refreshAll(data) {
    if (data.egcp)    this.egcp.update(data.egcp);
    if (data.filing)  this.filing.update(data.filing);
    if (data.stats)   this.stats.update(data.stats.total, data.stats.visible, data.stats.filtered);
    if (data.conn)    this.conn.update(data.conn);
    if (data.threat)  this.threat.update(data.threat);
    if (data.filters) this.filters.update(data.filters);
    this.minimap.render();
  }

  onZoom(transform) {
    this.minimap.updateViewport(transform);
  }

  _onRefresh() { this.alerts.push("Refreshing data from engines…", "info"); }
  _onToggleLayers() { document.getElementById("layer-panel")?.classList.toggle("hidden"); }

  _onScreenshot() {
    const svgEl = document.querySelector("svg");
    if (!svgEl) return;
    const serializer = new XMLSerializer();
    const svgStr = serializer.serializeToString(svgEl);
    const blob = new Blob([svgStr], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `THEMANBEARPIG_${Date.now()}.svg`;
    a.click();
    URL.revokeObjectURL(url);
    this.alerts.push("Screenshot saved", "success");
  }

  _onExport() { this.alerts.push("Export started…", "info"); }

  destroy() {
    this.sepCounter.destroy();
    this.fps.destroy();
  }
}
```

---

## 15. Python Bridge — HUD Data Provider

```python
"""Provide HUD data from litigation_context.db via pywebview bridge."""
import sqlite3
import json
from datetime import date
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "litigation_context.db"


def _conn():
    c = sqlite3.connect(str(DB_PATH))
    c.execute("PRAGMA busy_timeout = 60000")
    c.execute("PRAGMA journal_mode = WAL")
    c.execute("PRAGMA cache_size = -32000")
    return c


def get_hud_data() -> str:
    """Return all HUD metrics as JSON."""
    conn = _conn()
    try:
        row = conn.execute("""
            SELECT
              (SELECT COUNT(*) FROM evidence_quotes) AS eq,
              (SELECT COUNT(*) FROM timeline_events) AS te,
              (SELECT COUNT(*) FROM impeachment_matrix) AS im,
              (SELECT COUNT(*) FROM contradiction_map) AS cm,
              (SELECT COUNT(*) FROM judicial_violations) AS jv,
              (SELECT COUNT(*) FROM authority_chains_v2) AS ac
        """).fetchone()

        eq, te, im, cm, jv, ac = row
        evidence_score = min(int((eq / 200000) * 100), 100)
        gap_count = max(50 - int((ac / 170000) * 50), 0)
        confidence = min(int((im / 5200) * 100), 100)
        priority = min(int((jv / 2000) * 10), 10)

        sep_days = (date.today() - date(2025, 7, 29)).days

        lanes_raw = conn.execute("""
            SELECT lane, COUNT(*) as cnt FROM evidence_quotes
            WHERE lane IS NOT NULL GROUP BY lane
        """).fetchall()
        filing = []
        for lr in lanes_raw:
            ln, cnt = lr
            filing.append({"lane": ln, "readiness": min(int((cnt / 30000) * 100), 100)})

        return json.dumps({
            "egcp": {"E": evidence_score, "G": gap_count, "C": confidence, "P": priority},
            "filing": filing,
            "separation_days": sep_days,
            "stats": {"total": {"nodes": eq + te, "links": ac}, "visible": {"nodes": eq, "links": ac}, "filtered": 0},
            "conn": {"dbConnected": True, "daemonRunning": True, "lastRefresh": str(date.today())},
            "threat": "critical" if jv > 1000 else "high" if jv > 500 else "moderate",
        })
    finally:
        conn.close()
```

---

## 16. Anti-Patterns (MANDATORY)

1. **Never hardcode separation day count.** Compute `(today - 2025-07-29).days` always.
2. **Never block graph interaction with HUD overlays.** Use `pointer-events: none` on container.
3. **Never update HUD every frame.** EGCP/filing bars update every 5 seconds max.
4. **Never use `innerHTML` for user-controllable strings.** Sanitize or use `textContent`.
5. **Never render minimap with SVG.** Canvas is 10× faster for thousands of points.
6. **Never show raw SQL counts in HUD.** Normalize to percentages or meaningful metrics.
7. **Never exceed 220×160 px for minimap.** Larger minimaps steal too much screen.
8. **Never animate gauge arcs continuously.** Only animate on value change.
9. **Never use `setInterval` faster than 1 Hz for data refresh.** Network/DB thrashing.
10. **Never put filing readiness for CRIMINAL lane adjacent to Lanes A–F.** It is 100% separate.
11. **Never use alert sounds without user opt-in.** Visuals only by default.
12. **Never show more than 5 alerts simultaneously.** Dismiss oldest on overflow.
13. **Never let FPS counter itself drop FPS.** Use `requestAnimationFrame`, not `setInterval`.
14. **Never render threat level as just text color.** Use icon + color + label triple encoding.
15. **Never hide the separation counter.** It is the most important HUD element. Always visible.
16. **Never display the child's full name anywhere in HUD.** Use L.D.W. only.

---

## 17. Performance Budgets

| Metric | Budget | Action if Exceeded |
|--------|--------|--------------------|
| HUD total DOM elements | ≤ 120 | Collapse sections, use canvas for complex widgets |
| Minimap render time | < 8 ms | Reduce link drawing for > 5000 links |
| EGCP gauge redraw | < 2 ms per gauge | Skip redraw if value unchanged |
| Alert dismiss animation | 300 ms | Do not chain complex transitions |
| Filing bar update | < 4 ms total | Batch DOM writes in single rAF |
| FPS counter overhead | < 0.5 ms/frame | Remove frame history > 120 entries |
| HUD data fetch (Python) | < 100 ms | Cache result, refresh max 1/5s |
| Total HUD CSS rules | ≤ 80 | Consolidate selectors, avoid deep nesting |
| Memory for alert stack | ≤ 5 alert DOM nodes | Auto-dismiss oldest |

---

*END SINGULARITY-MBP-INTERFACE-HUD v1.0.0 — Full-spectrum litigation HUD for THEMANBEARPIG.*

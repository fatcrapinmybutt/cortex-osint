---
skill: SINGULARITY-MBP-INTERFACE-TIMELINE
version: 1.0.0
tier: TIER-3/INTERFACE
domain: Timeline scrubber, temporal playback, keyframe animation, milestone markers, actor swimlanes, density heatmap, escalation sparkline, date brushing
description: >-
  Temporal control layer for THEMANBEARPIG 13-layer graph. Horizontal timeline
  scrubber (2023-2026), temporal node filtering, play/pause/speed playback,
  keyframe snapshots at critical dates, milestone markers, actor swimlanes,
  density heatmap strip, escalation sparkline, date-range brushing, fade
  animations, and dynamic separation counter integration.
triggers:
  - timeline
  - temporal
  - playback
  - scrubber
  - keyframe
  - milestone
  - swimlane
  - date range
  - animation
  - separation counter
---

# SINGULARITY-MBP-INTERFACE-TIMELINE

> **Tier 3 — INTERFACE**: Temporal control layer for the THEMANBEARPIG 13-layer
> litigation intelligence mega-visualization. Scrub through 2023-2026 to watch
> the case unfold, animate nodes fading in/out, and visualize escalation.

---

## 1. Core Timeline Data Model

### 1.1 Python Data Pipeline

```python
"""timeline_pipeline.py — Load temporal data for THEMANBEARPIG timeline widget."""
import sqlite3, json, os
from datetime import date, datetime
from collections import Counter

DB_PATH = os.environ.get(
    "LITIGATION_DB",
    r"C:\Users\andre\LitigationOS\litigation_context.db",
)

PRAGMAS = """
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 60000;
PRAGMA cache_size  = -32000;
PRAGMA temp_store  = MEMORY;
PRAGMA synchronous = NORMAL;
"""

SEPARATION_ANCHOR = date(2025, 7, 29)

CRITICAL_MILESTONES = [
    {"date": "2023-10-13", "label": "Emily recants", "type": "evidence"},
    {"date": "2023-10-15", "label": "PPO filed", "type": "adversary"},
    {"date": "2023-12-03", "label": "PPO granted ex parte", "type": "judicial"},
    {"date": "2024-04-01", "label": "Custody complaint filed", "type": "filing"},
    {"date": "2024-04-29", "label": "Ex parte order — 50/50", "type": "judicial"},
    {"date": "2024-07-17", "label": "TRIAL — sole to Mother", "type": "critical"},
    {"date": "2024-10-20", "label": "Withholding begins", "type": "adversary"},
    {"date": "2024-11-15", "label": "SC#5 — 14 days jail", "type": "critical"},
    {"date": "2025-05-04", "label": "Albert admits premeditation", "type": "evidence"},
    {"date": "2025-07-29", "label": "LAST CONTACT with L.D.W.", "type": "critical"},
    {"date": "2025-08-07", "label": "NS2505044 — smoking gun", "type": "evidence"},
    {"date": "2025-08-08", "label": "FIVE ex parte orders", "type": "judicial"},
    {"date": "2025-09-28", "label": "Custody order — 100% Emily", "type": "critical"},
    {"date": "2025-11-26", "label": "SC#6+7 — 45 days jail", "type": "critical"},
    {"date": "2026-03-25", "label": "Emergency motion filed", "type": "filing"},
]


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(PRAGMAS)
    return conn


def load_timeline_events(conn, limit=5000):
    """Load timeline events with dates for temporal filtering."""
    sql = """
    SELECT
        event_date,
        event_description,
        COALESCE(lane, 'unknown') AS lane,
        COALESCE(actor, 'unknown') AS actor,
        COALESCE(category, 'event') AS category
    FROM timeline_events
    WHERE event_date IS NOT NULL
      AND event_date != ''
      AND LENGTH(event_date) >= 10
    ORDER BY event_date ASC
    LIMIT ?
    """
    rows = conn.execute(sql, (limit,)).fetchall()
    return [dict(r) for r in rows]


def compute_density_histogram(events, bin_days=7):
    """Compute event density per time bin for heatmap strip."""
    if not events:
        return []
    dates = []
    for e in events:
        try:
            dates.append(datetime.strptime(e["event_date"][:10], "%Y-%m-%d").date())
        except (ValueError, TypeError):
            continue
    if not dates:
        return []

    min_date = min(dates)
    max_date = max(dates)
    bins = []
    current = min_date
    while current <= max_date:
        bin_end = current + __import__("datetime").timedelta(days=bin_days)
        count = sum(1 for d in dates if current <= d < bin_end)
        bins.append({
            "start": current.isoformat(),
            "end": bin_end.isoformat(),
            "count": count,
        })
        current = bin_end
    return bins


def compute_escalation_series(events):
    """Compute severity escalation trend over time."""
    severity_map = {"critical": 10, "high": 8, "medium": 5, "low": 2, "event": 1}
    series = []
    for e in events:
        sev = severity_map.get(e.get("category", "event"), 1)
        series.append({
            "date": e["event_date"][:10],
            "severity": sev,
            "label": (e.get("event_description") or "")[:80],
        })
    return series


def compute_separation_days():
    """Dynamic separation counter — never hardcode."""
    today = date.today()
    delta = today - SEPARATION_ANCHOR
    return {
        "days": delta.days,
        "weeks": delta.days // 7,
        "months": round(delta.days / 30.44, 1),
        "anchor": SEPARATION_ANCHOR.isoformat(),
        "today": today.isoformat(),
    }


def build_actor_swimlanes(events):
    """Group events by actor for swimlane rendering."""
    lanes = {}
    for e in events:
        actor = e.get("actor", "unknown")
        if actor not in lanes:
            lanes[actor] = []
        lanes[actor].append({
            "date": e["event_date"][:10],
            "text": (e.get("event_description") or "")[:100],
            "category": e.get("category", "event"),
        })
    # Sort by activity volume, keep top 8
    sorted_actors = sorted(lanes.items(), key=lambda x: -len(x[1]))[:8]
    return dict(sorted_actors)


def build_timeline_json(out_path="timeline_data.json"):
    """Build the full timeline payload for D3."""
    conn = get_conn()
    events = load_timeline_events(conn)
    conn.close()

    payload = {
        "events": events,
        "milestones": CRITICAL_MILESTONES,
        "density": compute_density_histogram(events),
        "escalation": compute_escalation_series(events),
        "swimlanes": build_actor_swimlanes(events),
        "separation": compute_separation_days(),
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    return payload
```

---

## 2. Horizontal Timeline Scrubber Widget

### 2.1 D3.js Scrubber

```javascript
/**
 * Render the horizontal timeline scrubber at the bottom of the graph.
 * @param {HTMLElement} container — parent element
 * @param {Object}      config   — { minDate, maxDate, onScrub, milestones }
 */
function renderTimelineScrubber(container, config) {
    const margin = { left: 60, right: 60, top: 30, bottom: 20 };
    const width = container.clientWidth - margin.left - margin.right;
    const height = 120;

    const svg = d3.select(container).append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        .attr("class", "timeline-svg");

    const g = svg.append("g")
        .attr("transform", `translate(${margin.left},${margin.top})`);

    const xScale = d3.scaleTime()
        .domain([new Date(config.minDate), new Date(config.maxDate)])
        .range([0, width]);

    // Axis
    const xAxis = d3.axisBottom(xScale)
        .ticks(d3.timeMonth.every(3))
        .tickFormat(d3.timeFormat("%b %Y"));

    g.append("g")
        .attr("class", "timeline-axis")
        .attr("transform", `translate(0,${height - 30})`)
        .call(xAxis)
        .selectAll("text")
        .attr("fill", "#8b949e")
        .attr("font-size", 10);

    // Track line
    g.append("line")
        .attr("class", "timeline-track")
        .attr("x1", 0).attr("x2", width)
        .attr("y1", height - 30).attr("y2", height - 30)
        .attr("stroke", "#30363d").attr("stroke-width", 2);

    // Milestone markers
    if (config.milestones) {
        const milestoneColors = {
            critical: "#e74c3c",
            judicial: "#8e44ad",
            adversary: "#e67e22",
            evidence: "#2ecc71",
            filing: "#3498db",
        };

        config.milestones.forEach(m => {
            const x = xScale(new Date(m.date));
            if (x < 0 || x > width) return;

            // Vertical line
            g.append("line")
                .attr("x1", x).attr("x2", x)
                .attr("y1", 0).attr("y2", height - 30)
                .attr("stroke", milestoneColors[m.type] || "#666")
                .attr("stroke-width", 1.5)
                .attr("stroke-dasharray", "3,3")
                .attr("opacity", 0.7);

            // Dot on track
            g.append("circle")
                .attr("cx", x).attr("cy", height - 30)
                .attr("r", 5)
                .attr("fill", milestoneColors[m.type] || "#666")
                .attr("stroke", "#0d1117")
                .attr("stroke-width", 1.5);

            // Label (stagger vertically to avoid overlap)
            const yOff = (config.milestones.indexOf(m) % 3) * 14;
            g.append("text")
                .attr("x", x).attr("y", -5 - yOff)
                .attr("text-anchor", "middle")
                .attr("font-size", 9)
                .attr("fill", milestoneColors[m.type] || "#888")
                .text(m.label);
        });
    }

    // Draggable handle
    const handle = g.append("g").attr("class", "timeline-handle");
    const handleX = xScale(new Date(config.maxDate));

    handle.append("line")
        .attr("class", "handle-line")
        .attr("x1", handleX).attr("x2", handleX)
        .attr("y1", -5).attr("y2", height - 25)
        .attr("stroke", "#58a6ff").attr("stroke-width", 2);

    handle.append("rect")
        .attr("class", "handle-grip")
        .attr("x", handleX - 8).attr("y", height - 45)
        .attr("width", 16).attr("height", 20)
        .attr("rx", 4)
        .attr("fill", "#58a6ff")
        .attr("cursor", "ew-resize");

    // Date display above handle
    const dateLabel = handle.append("text")
        .attr("class", "handle-date")
        .attr("x", handleX).attr("y", height - 50)
        .attr("text-anchor", "middle")
        .attr("font-size", 11).attr("font-weight", 700)
        .attr("fill", "#58a6ff")
        .text(d3.timeFormat("%b %d, %Y")(new Date(config.maxDate)));

    // Drag behavior
    const drag = d3.drag()
        .on("drag", (event) => {
            const newX = Math.max(0, Math.min(width, event.x));
            handle.select(".handle-line").attr("x1", newX).attr("x2", newX);
            handle.select(".handle-grip").attr("x", newX - 8);
            const newDate = xScale.invert(newX);
            dateLabel.attr("x", newX).text(d3.timeFormat("%b %d, %Y")(newDate));
            if (config.onScrub) config.onScrub(newDate);
        });

    handle.call(drag);

    return { xScale, svg, handle, setDate };

    function setDate(date) {
        const x = xScale(new Date(date));
        handle.select(".handle-line").attr("x1", x).attr("x2", x);
        handle.select(".handle-grip").attr("x", x - 8);
        dateLabel.attr("x", x).text(d3.timeFormat("%b %d, %Y")(new Date(date)));
        if (config.onScrub) config.onScrub(new Date(date));
    }
}
```

---

## 3. Temporal Filtering — Show Only Nodes at Scrubbed Date

```javascript
/**
 * Filter graph nodes based on the current timeline position.
 * Nodes without dates are always visible. Nodes with dates
 * after the scrubber position fade out.
 *
 * @param {d3.Selection} nodeSelection — all graph node elements
 * @param {d3.Selection} linkSelection — all graph link elements
 * @param {Date}         currentDate   — scrubber position
 */
function applyTemporalFilter(nodeSelection, linkSelection, currentDate) {
    const cutoff = currentDate.getTime();

    nodeSelection.each(function (d) {
        const node = d3.select(this);
        if (!d.date) {
            node.attr("opacity", 1).style("pointer-events", "all");
            return;
        }
        const nodeDate = new Date(d.date).getTime();
        if (nodeDate <= cutoff) {
            node.attr("opacity", 1).style("pointer-events", "all");
        } else {
            node.attr("opacity", 0.08).style("pointer-events", "none");
        }
    });

    linkSelection.each(function (l) {
        const link = d3.select(this);
        const srcDate = l.source.date ? new Date(l.source.date).getTime() : 0;
        const tgtDate = l.target.date ? new Date(l.target.date).getTime() : 0;
        const visible = srcDate <= cutoff && tgtDate <= cutoff;
        link.attr("opacity", visible ? 0.6 : 0.03)
            .style("pointer-events", visible ? "all" : "none");
    });
}
```

---

## 4. Playback Controls

Play, pause, speed selection — auto-advance the scrubber through time.

```javascript
class TimelinePlayback {
    constructor(scrubber, nodeSelection, linkSelection, config) {
        this.scrubber = scrubber;
        this.nodes = nodeSelection;
        this.links = linkSelection;
        this.minDate = new Date(config.minDate);
        this.maxDate = new Date(config.maxDate);
        this.currentDate = new Date(this.minDate);
        this.speed = 1;
        this.playing = false;
        this.animFrameId = null;
        this.msPerDay = 100;
        this.lastTick = 0;
    }

    play() {
        this.playing = true;
        this.lastTick = performance.now();
        this._tick();
        this._updateButtons();
    }

    pause() {
        this.playing = false;
        if (this.animFrameId) cancelAnimationFrame(this.animFrameId);
        this._updateButtons();
    }

    togglePlay() {
        this.playing ? this.pause() : this.play();
    }

    setSpeed(multiplier) {
        this.speed = multiplier;
        document.querySelectorAll(".speed-btn").forEach(btn => {
            btn.classList.toggle("active", +btn.dataset.speed === multiplier);
        });
    }

    jumpTo(dateStr) {
        this.currentDate = new Date(dateStr);
        this.scrubber.setDate(dateStr);
        applyTemporalFilter(this.nodes, this.links, this.currentDate);
    }

    _tick() {
        if (!this.playing) return;
        const now = performance.now();
        const elapsed = now - this.lastTick;
        this.lastTick = now;

        const daysToAdvance = (elapsed / this.msPerDay) * this.speed;
        this.currentDate = new Date(
            this.currentDate.getTime() + daysToAdvance * 86400000
        );

        if (this.currentDate >= this.maxDate) {
            this.currentDate = new Date(this.maxDate);
            this.pause();
        }

        this.scrubber.setDate(this.currentDate.toISOString().slice(0, 10));
        applyTemporalFilter(this.nodes, this.links, this.currentDate);

        this.animFrameId = requestAnimationFrame(() => this._tick());
    }

    _updateButtons() {
        const playBtn = document.getElementById("play-btn");
        if (playBtn) playBtn.textContent = this.playing ? "⏸" : "▶";
    }
}
```

### 4.1 Playback UI

```javascript
function renderPlaybackControls(container, playback) {
    container.innerHTML = `
        <div class="playback-bar">
            <button id="play-btn" class="pb-btn" title="Play/Pause">▶</button>
            <button class="pb-btn" id="reset-btn" title="Reset">⏮</button>
            <div class="speed-group">
                <button class="speed-btn" data-speed="1">1×</button>
                <button class="speed-btn" data-speed="2">2×</button>
                <button class="speed-btn" data-speed="5">5×</button>
                <button class="speed-btn active" data-speed="10">10×</button>
            </div>
            <div class="jump-group" id="jump-buttons"></div>
            <div class="separation-counter" id="sep-counter"></div>
        </div>
    `;

    document.getElementById("play-btn").addEventListener("click", () => playback.togglePlay());
    document.getElementById("reset-btn").addEventListener("click", () => {
        playback.jumpTo(playback.minDate.toISOString().slice(0, 10));
    });

    document.querySelectorAll(".speed-btn").forEach(btn => {
        btn.addEventListener("click", () => playback.setSpeed(+btn.dataset.speed));
    });

    // Jump-to buttons for key dates
    const jumpDates = [
        { date: "2024-07-17", label: "Trial" },
        { date: "2025-07-29", label: "Last Contact" },
        { date: "2025-08-08", label: "5 Ex Parte" },
        { date: "2025-09-28", label: "Custody Order" },
    ];
    const jumpDiv = document.getElementById("jump-buttons");
    jumpDates.forEach(j => {
        const btn = document.createElement("button");
        btn.className = "jump-btn";
        btn.textContent = j.label;
        btn.title = j.date;
        btn.addEventListener("click", () => playback.jumpTo(j.date));
        jumpDiv.appendChild(btn);
    });
}
```

### 4.2 Playback CSS

```css
.playback-bar {
    display: flex; align-items: center; gap: 8px;
    padding: 8px 16px;
    background: #0d1117; border-top: 1px solid #21262d;
}
.pb-btn {
    width: 36px; height: 36px; border-radius: 50%;
    background: #21262d; color: #c9d1d9; border: 1px solid #30363d;
    font-size: 16px; cursor: pointer; display: flex;
    align-items: center; justify-content: center;
}
.pb-btn:hover { background: #30363d; }
.speed-group { display: flex; gap: 2px; }
.speed-btn {
    padding: 4px 8px; font-size: 11px;
    background: #161b22; color: #8b949e; border: 1px solid #30363d;
    cursor: pointer; border-radius: 4px;
}
.speed-btn.active { background: #1f6feb; color: #fff; border-color: #58a6ff; }
.jump-group { display: flex; gap: 4px; margin-left: 12px; }
.jump-btn {
    padding: 4px 10px; font-size: 10px;
    background: #161b22; color: #c9d1d9; border: 1px solid #30363d;
    border-radius: 12px; cursor: pointer;
}
.jump-btn:hover { background: #1c2333; border-color: #58a6ff; }
.separation-counter {
    margin-left: auto; font-size: 14px; font-weight: 700;
    color: #e74c3c; font-family: 'Courier New', monospace;
}
```

---

## 5. Keyframe System

Define snapshots at critical dates — user can jump between them.

```javascript
class KeyframeManager {
    constructor(milestones) {
        this.keyframes = milestones.map((m, i) => ({
            index: i,
            date: m.date,
            label: m.label,
            type: m.type,
        }));
        this.currentIndex = 0;
    }

    current() { return this.keyframes[this.currentIndex]; }

    next() {
        if (this.currentIndex < this.keyframes.length - 1) {
            this.currentIndex++;
            return this.current();
        }
        return null;
    }

    previous() {
        if (this.currentIndex > 0) {
            this.currentIndex--;
            return this.current();
        }
        return null;
    }

    jumpToIndex(idx) {
        if (idx >= 0 && idx < this.keyframes.length) {
            this.currentIndex = idx;
            return this.current();
        }
        return null;
    }

    findNearest(dateStr) {
        const target = new Date(dateStr).getTime();
        let best = 0, bestDist = Infinity;
        this.keyframes.forEach((kf, i) => {
            const dist = Math.abs(new Date(kf.date).getTime() - target);
            if (dist < bestDist) { best = i; bestDist = dist; }
        });
        this.currentIndex = best;
        return this.current();
    }

    renderKeyframeStrip(container, onSelect) {
        container.innerHTML = "";
        this.keyframes.forEach((kf, i) => {
            const btn = document.createElement("button");
            btn.className = `kf-btn ${i === this.currentIndex ? 'active' : ''}`;
            btn.innerHTML = `<span class="kf-date">${kf.date.slice(5)}</span><span class="kf-label">${kf.label}</span>`;
            btn.addEventListener("click", () => {
                this.currentIndex = i;
                onSelect(kf);
                container.querySelectorAll(".kf-btn").forEach((b, j) => {
                    b.classList.toggle("active", j === i);
                });
            });
            container.appendChild(btn);
        });
    }
}
```

### 5.1 Keyframe Strip CSS

```css
.keyframe-strip {
    display: flex; gap: 4px; overflow-x: auto;
    padding: 6px 12px; background: #0d1117;
    border-bottom: 1px solid #21262d;
}
.kf-btn {
    display: flex; flex-direction: column; align-items: center;
    padding: 4px 10px; border-radius: 6px;
    background: #161b22; border: 1px solid #21262d;
    cursor: pointer; white-space: nowrap; flex-shrink: 0;
}
.kf-btn.active { border-color: #58a6ff; background: #1c2333; }
.kf-date { font-size: 10px; color: #58a6ff; }
.kf-label { font-size: 9px; color: #8b949e; }
```

---

## 6. Actor Swimlanes

Horizontal tracks per person showing their activity over time.

```javascript
function renderActorSwimlanes(container, swimlaneData, xScale) {
    const actors = Object.keys(swimlaneData);
    const laneHeight = 40;
    const width = container.clientWidth - 120;
    const totalHeight = actors.length * laneHeight + 40;

    const svg = d3.select(container).append("svg")
        .attr("width", width + 120)
        .attr("height", totalHeight)
        .attr("class", "swimlane-svg");

    const g = svg.append("g").attr("transform", "translate(110, 20)");

    const actorColors = d3.scaleOrdinal(d3.schemeTableau10);

    actors.forEach((actor, i) => {
        const y = i * laneHeight;
        const events = swimlaneData[actor];

        // Lane background
        g.append("rect")
            .attr("x", 0).attr("y", y)
            .attr("width", width).attr("height", laneHeight - 4)
            .attr("fill", i % 2 === 0 ? "#0d1117" : "#111622")
            .attr("rx", 3);

        // Actor label
        svg.append("text")
            .attr("x", 105).attr("y", y + 20 + laneHeight / 2 - 8)
            .attr("text-anchor", "end")
            .attr("font-size", 10).attr("fill", "#8b949e")
            .text(actor.length > 15 ? actor.slice(0, 14) + "…" : actor);

        // Event dots
        events.forEach(evt => {
            const cx = xScale(new Date(evt.date));
            if (cx < 0 || cx > width) return;

            g.append("circle")
                .attr("cx", cx).attr("cy", y + laneHeight / 2 - 2)
                .attr("r", 3)
                .attr("fill", actorColors(actor))
                .attr("opacity", 0.8)
                .append("title")
                .text(`${evt.date}: ${evt.text}`);
        });
    });
}
```

---

## 7. Density Heatmap Strip

Color-coded strip showing event density along the timeline.

```javascript
function renderDensityHeatmap(container, densityBins, xScale) {
    const width = container.clientWidth - 120;
    const height = 16;

    const svg = d3.select(container).append("svg")
        .attr("width", width + 120)
        .attr("height", height + 4)
        .attr("class", "density-svg");

    const g = svg.append("g").attr("transform", "translate(110, 2)");

    const maxCount = Math.max(...densityBins.map(b => b.count), 1);
    const colorScale = d3.scaleSequential(d3.interpolateInferno)
        .domain([0, maxCount]);

    densityBins.forEach(bin => {
        const x1 = xScale(new Date(bin.start));
        const x2 = xScale(new Date(bin.end));
        if (x2 < 0 || x1 > width) return;

        g.append("rect")
            .attr("x", Math.max(0, x1))
            .attr("y", 0)
            .attr("width", Math.max(1, x2 - x1))
            .attr("height", height)
            .attr("fill", colorScale(bin.count))
            .attr("rx", 1)
            .append("title")
            .text(`${bin.start} — ${bin.count} events`);
    });

    // Label
    svg.append("text")
        .attr("x", 105).attr("y", height / 2 + 4)
        .attr("text-anchor", "end")
        .attr("font-size", 9).attr("fill", "#484f58")
        .text("Density");
}
```

---

## 8. Escalation Sparkline

Severity trend line overlaid on the timeline area.

```javascript
function renderEscalationSparkline(container, escalationSeries, xScale) {
    const width = container.clientWidth - 120;
    const height = 40;

    const svg = d3.select(container).append("svg")
        .attr("width", width + 120)
        .attr("height", height + 4)
        .attr("class", "escalation-svg");

    const g = svg.append("g").attr("transform", "translate(110, 2)");

    const yScale = d3.scaleLinear()
        .domain([0, 10])
        .range([height, 0]);

    const line = d3.line()
        .x(d => xScale(new Date(d.date)))
        .y(d => yScale(d.severity))
        .curve(d3.curveBasis);

    // Area fill
    const area = d3.area()
        .x(d => xScale(new Date(d.date)))
        .y0(height)
        .y1(d => yScale(d.severity))
        .curve(d3.curveBasis);

    g.append("path")
        .datum(escalationSeries)
        .attr("d", area)
        .attr("fill", "rgba(231,76,60,0.15)");

    g.append("path")
        .datum(escalationSeries)
        .attr("d", line)
        .attr("fill", "none")
        .attr("stroke", "#e74c3c")
        .attr("stroke-width", 1.5);

    // Label
    svg.append("text")
        .attr("x", 105).attr("y", height / 2 + 4)
        .attr("text-anchor", "end")
        .attr("font-size", 9).attr("fill", "#484f58")
        .text("Escalation");
}
```

---

## 9. Date Range Brushing

Click-drag on the timeline to select a date window.

```javascript
function enableDateBrush(svg, xScale, onBrush) {
    const brushHeight = 80;

    const brush = d3.brushX()
        .extent([[0, 0], [xScale.range()[1], brushHeight]])
        .on("end", (event) => {
            if (!event.selection) {
                onBrush(null, null);
                return;
            }
            const [x0, x1] = event.selection;
            const dateFrom = xScale.invert(x0);
            const dateTo = xScale.invert(x1);
            onBrush(dateFrom, dateTo);
        });

    const brushGroup = d3.select(svg).select("g")
        .append("g")
        .attr("class", "timeline-brush")
        .call(brush);

    // Style the brush selection rectangle
    brushGroup.selectAll(".selection")
        .attr("fill", "rgba(88,166,255,0.2)")
        .attr("stroke", "#58a6ff");

    return brushGroup;
}
```

---

## 10. Node Fade Animation

Nodes smoothly fade in/out as the timeline progresses.

```javascript
function applyTemporalFadeAnimation(nodeSelection, linkSelection, currentDate, duration = 300) {
    const cutoff = currentDate.getTime();

    nodeSelection.transition()
        .duration(duration)
        .attr("opacity", d => {
            if (!d.date) return 1;
            return new Date(d.date).getTime() <= cutoff ? 1 : 0.06;
        })
        .on("end", function (d) {
            d3.select(this).style("pointer-events",
                (!d.date || new Date(d.date).getTime() <= cutoff) ? "all" : "none"
            );
        });

    linkSelection.transition()
        .duration(duration)
        .attr("opacity", l => {
            const srcOk = !l.source.date || new Date(l.source.date).getTime() <= cutoff;
            const tgtOk = !l.target.date || new Date(l.target.date).getTime() <= cutoff;
            return (srcOk && tgtOk) ? 0.6 : 0.02;
        });
}
```

---

## 11. Separation Counter Integration

Dynamic days-since display — always computed, never hardcoded.

```javascript
function renderSeparationCounter(container) {
    const anchor = new Date("2025-07-29T00:00:00");
    const now = new Date();
    const diffMs = now.getTime() - anchor.getTime();
    const days = Math.floor(diffMs / 86400000);
    const weeks = Math.floor(days / 7);
    const months = (days / 30.44).toFixed(1);

    container.innerHTML = `
        <div class="sep-counter">
            <span class="sep-days">${days}</span>
            <span class="sep-unit">DAYS</span>
            <span class="sep-detail">${weeks}w · ${months}mo</span>
            <span class="sep-label">since last contact with L.D.W.</span>
        </div>
    `;
}
```

### 11.1 Separation Counter CSS

```css
.sep-counter {
    display: flex; align-items: baseline; gap: 6px;
    font-family: 'Courier New', monospace;
}
.sep-days {
    font-size: 20px; font-weight: 900;
    color: #e74c3c;
    text-shadow: 0 0 8px rgba(231,76,60,0.4);
}
.sep-unit { font-size: 10px; color: #e74c3c; font-weight: 700; }
.sep-detail { font-size: 10px; color: #8b949e; }
.sep-label { font-size: 9px; color: #484f58; }
```

---

## 12. Full Integration — Assembling the Timeline Panel

```javascript
function initTimelinePanel(graphNodes, graphLinks, timelineData) {
    const panel = document.getElementById("timeline-panel");
    if (!panel) return;

    const xScale = d3.scaleTime()
        .domain([new Date("2023-10-01"), new Date("2026-06-30")])
        .range([0, panel.clientWidth - 120]);

    // 1. Keyframe strip
    const kfContainer = document.createElement("div");
    kfContainer.className = "keyframe-strip";
    panel.appendChild(kfContainer);

    const kfManager = new KeyframeManager(timelineData.milestones);
    kfManager.renderKeyframeStrip(kfContainer, (kf) => {
        playback.jumpTo(kf.date);
    });

    // 2. Density heatmap
    renderDensityHeatmap(panel, timelineData.density, xScale);

    // 3. Escalation sparkline
    renderEscalationSparkline(panel, timelineData.escalation, xScale);

    // 4. Main scrubber
    const scrubberContainer = document.createElement("div");
    scrubberContainer.className = "scrubber-container";
    panel.appendChild(scrubberContainer);

    const scrubber = renderTimelineScrubber(scrubberContainer, {
        minDate: "2023-10-01",
        maxDate: "2026-06-30",
        milestones: timelineData.milestones,
        onScrub: (date) => {
            applyTemporalFadeAnimation(
                d3.selectAll(".graph-node"),
                d3.selectAll(".graph-link"),
                date
            );
        },
    });

    // 5. Playback controls
    const pbContainer = document.createElement("div");
    panel.appendChild(pbContainer);

    const playback = new TimelinePlayback(
        scrubber,
        d3.selectAll(".graph-node"),
        d3.selectAll(".graph-link"),
        { minDate: "2023-10-01", maxDate: "2026-06-30" }
    );
    renderPlaybackControls(pbContainer, playback);

    // 6. Separation counter
    renderSeparationCounter(document.getElementById("sep-counter"));

    // 7. Swimlanes (collapsible)
    const swimContainer = document.createElement("div");
    swimContainer.className = "swimlane-container collapsed";
    panel.appendChild(swimContainer);

    const swimToggle = document.createElement("button");
    swimToggle.className = "swim-toggle";
    swimToggle.textContent = "▸ Actor Swimlanes";
    swimToggle.addEventListener("click", () => {
        swimContainer.classList.toggle("collapsed");
        swimToggle.textContent = swimContainer.classList.contains("collapsed")
            ? "▸ Actor Swimlanes" : "▾ Actor Swimlanes";
        if (!swimContainer.classList.contains("collapsed") && !swimContainer.dataset.rendered) {
            renderActorSwimlanes(swimContainer, timelineData.swimlanes, xScale);
            swimContainer.dataset.rendered = "true";
        }
    });
    panel.insertBefore(swimToggle, swimContainer);

    return { scrubber, playback, kfManager };
}
```

---

## 13. Timeline Panel CSS

```css
#timeline-panel {
    position: fixed; bottom: 0; left: 0; right: 0;
    background: #0d1117; border-top: 2px solid #21262d;
    z-index: 300; max-height: 40vh; overflow-y: auto;
}
.scrubber-container { padding: 0 8px; }
.timeline-axis line, .timeline-axis path { stroke: #30363d; }
.swimlane-container { padding: 0 8px; }
.swimlane-container.collapsed { display: none; }
.swim-toggle {
    display: block; width: 100%; text-align: left;
    padding: 6px 16px; background: #111622;
    color: #8b949e; border: none; border-top: 1px solid #21262d;
    cursor: pointer; font-size: 11px;
}
.swim-toggle:hover { background: #161b22; }
```

---

## 14. Anti-Patterns (MANDATORY — 18 Rules)

| #  | Anti-Pattern | Why It Fails |
|----|-------------|-------------|
| 1  | Hardcoding separation day count | Stale within 24 hours — always compute `(today - 2025-07-29).days` |
| 2  | Parsing dates with `new Date(string)` without validation | Invalid dates crash timeline — validate format first |
| 3  | Loading all 16.8K events into D3 at once | Browser grinds — pre-aggregate with density bins on Python side |
| 4  | Animating node opacity without `requestAnimationFrame` | Janky — always use rAF or D3 transitions |
| 5  | Not clamping scrubber handle to track bounds | Handle escapes viewport — `Math.max(0, Math.min(width, x))` |
| 6  | Using `setInterval` for playback loop | Drifts and can't sync to frame rate — use rAF |
| 7  | Swimlanes for more than 8 actors | Vertical overflow — cap at top 8 by activity volume |
| 8  | Not debouncing scrub callback | Fires hundreds of times during drag — debounce or throttle to 16ms |
| 9  | Density bins smaller than 3 days | Too many rectangles — minimum 7-day bins |
| 10 | Escalation sparkline without smoothing | Noisy spikes — use `d3.curveBasis` |
| 11 | Milestone labels overlapping each other | Unreadable — stagger y-offsets with modular arithmetic |
| 12 | Playing past max date without stopping | Infinite loop — check bounds and call `pause()` |
| 13 | Date brush without clear/reset mechanism | Trapped in selection — handle null selection to clear filter |
| 14 | Rendering swimlanes when panel is collapsed | Wasted work — lazy-render only when expanded |
| 15 | Not syncing timeline with filter panel date range | Conflicting state — timeline scrub should update filter dates |
| 16 | Using child's full name in milestone labels | MCR 8.119(H) violation — always L.D.W. |
| 17 | Embedding LitigationOS/DB refs in exported timeline | Court contamination — decontaminate before export |
| 18 | Tickmark labels clashing with milestone text | Visual noise — hide tick labels that overlap milestones |

---

## 15. Performance Budgets

| Metric | Budget | Measurement |
|--------|--------|-------------|
| Scrubber drag response | < 16ms per frame | Must maintain 60fps during drag |
| Temporal filter (2500 nodes) | < 30ms | Opacity toggle is cheap |
| Fade animation (2500 nodes) | 300ms transition, 60fps | D3 transition handles batching |
| Density heatmap render | < 20ms | Pre-computed bins, simple rects |
| Escalation sparkline render | < 15ms | Single path + area |
| Swimlane render (8 actors, 500 events) | < 100ms | Batch circle append |
| Playback tick | < 8ms overhead | rAF budget minus render time |
| Keyframe jump | < 50ms | Date set + filter + animation start |
| Date brush selection | < 20ms | D3 brush + callback |
| Separation counter update | < 1ms | Pure arithmetic + DOM write |
| Timeline panel total memory | < 10MB | Chrome DevTools heap snapshot |
| Max visible milestone markers | 20 | Cull markers outside viewport |

---

## 16. pywebview Bridge Integration

```python
"""timeline_bridge.py — pywebview API for timeline data."""
import webview
import json

class TimelineAPI:
    def __init__(self, db_path):
        self.db_path = db_path

    def get_timeline_data(self):
        """Called from JS: window.pywebview.api.get_timeline_data()"""
        from timeline_pipeline import build_timeline_json
        payload = build_timeline_json()
        return json.dumps(payload, default=str)

    def get_separation_days(self):
        """Called from JS: window.pywebview.api.get_separation_days()"""
        from timeline_pipeline import compute_separation_days
        return json.dumps(compute_separation_days())

    def save_keyframe_positions(self, keyframes_json):
        """Persist custom keyframe order to local storage."""
        import os
        path = os.path.join(os.path.dirname(self.db_path), "keyframe_config.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write(keyframes_json)
        return json.dumps({"ok": True})
```

---

## 17. Integration Checklist

- [ ] Timeline data loaded from `timeline_events` via WAL connection with parameterized SQL
- [ ] Milestones sourced from `CRITICAL_MILESTONES` constant, not hardcoded in JS
- [ ] Separation counter computed dynamically: `(today - 2025-07-29).days`
- [ ] Density histogram pre-computed in Python, not in browser
- [ ] Escalation series uses actual event categories, not fabricated scores
- [ ] Temporal filter wired to scrubber's `onScrub` callback
- [ ] Playback uses `requestAnimationFrame`, not `setInterval`
- [ ] Swimlanes lazy-rendered only when panel is expanded
- [ ] Date brush syncs with FilterPanel date range
- [ ] L.D.W. initials enforced in all milestone labels and event descriptions
- [ ] No LitigationOS/AI/DB references in any exported timeline data
- [ ] pywebview bridge exposes `get_timeline_data()` and `get_separation_days()`
- [ ] PyInstaller spec includes `timeline_data.json` in datas if pre-built

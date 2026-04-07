---
skill: SINGULARITY-MBP-INTERFACE-NARRATIVE
version: 1.0.0
description: >-
  Story mode, narrative generation, guided walkthroughs, jury presentation mode,
  breadcrumb trails, cinematic camera, chapter system, evidence spotlight,
  progressive reveal, presentation export, and voice-over hooks for
  THEMANBEARPIG 13-layer litigation intelligence mega-visualization.
  Pywebview desktop, D3.js force graph, PyInstaller bundled.
tier: TIER-3/INTERFACE
domain: narrative-visualization
triggers:
  - narrative
  - story
  - walkthrough
  - jury
  - presentation
  - breadcrumb
  - cinematic
  - chapter
  - guided tour
  - voice-over
  - reveal
  - spotlight
---

# SINGULARITY-MBP-INTERFACE-NARRATIVE

> **Story mode engine for THEMANBEARPIG.** Converts a 13-layer litigation
> knowledge graph into a guided, cinematic, jury-ready narrative experience
> with animated camera, breadcrumb trails, evidence spotlights, and
> voice-over integration.

---

## 1. Narrative Arc Schema

Every story is a JSON document consumed by the walkthrough engine.
The schema supports chapters, beats (steps), camera targets, narration
text, and transition configuration.

```json
{
  "storyId": "custody-timeline-v1",
  "title": "The Custody Case: A Father's Fight",
  "author": "LitigationOS",
  "created": "2026-04-01T00:00:00Z",
  "chapters": [
    {
      "id": "ch-1",
      "title": "Chapter 1 — The Beginning",
      "beats": [
        {
          "id": "beat-1-1",
          "nodeIds": ["evt-2024-04-01"],
          "highlightLinks": ["link-complaint-filed"],
          "camera": { "x": 320, "y": 180, "zoom": 2.5 },
          "transition": { "duration": 1200, "ease": "cubicInOut" },
          "narration": "On April 1, 2024, Andrew filed a Complaint for Custody — the first legal move to protect L.D.W.",
          "evidenceSpotlight": ["PIGORS-A-000001"],
          "pause": 4000
        },
        {
          "id": "beat-1-2",
          "nodeIds": ["evt-2024-04-29"],
          "camera": { "x": 480, "y": 220, "zoom": 2.0 },
          "transition": { "duration": 1000, "ease": "cubicInOut" },
          "narration": "On April 29, the court issued an Ex Parte Order granting joint legal and physical custody with 50/50 parenting time.",
          "evidenceSpotlight": [],
          "pause": 5000
        }
      ]
    }
  ],
  "settings": {
    "autoAdvance": true,
    "showBreadcrumbs": true,
    "voiceEnabled": false,
    "juryMode": false,
    "overlayOpacity": 0.85
  }
}
```

---

## 2. Story Mode Controller (JavaScript)

The controller owns playback state: current chapter, current beat,
play/pause, skip, and auto-advance timer.

```javascript
class StoryModeController {
  constructor(svg, simulation, storyData) {
    this.svg = svg;
    this.simulation = simulation;
    this.story = storyData;
    this.chapterIdx = 0;
    this.beatIdx = 0;
    this.playing = false;
    this.timer = null;
    this.breadcrumbs = [];
    this.overlay = this._createOverlay();
    this.breadcrumbTrail = this._createBreadcrumbTrail();
  }

  get currentChapter() {
    return this.story.chapters[this.chapterIdx] || null;
  }

  get currentBeat() {
    const ch = this.currentChapter;
    return ch ? ch.beats[this.beatIdx] || null : null;
  }

  play() {
    this.playing = true;
    this._executeBeat(this.currentBeat);
  }

  pause() {
    this.playing = false;
    clearTimeout(this.timer);
  }

  next() {
    const ch = this.currentChapter;
    if (!ch) return;
    if (this.beatIdx < ch.beats.length - 1) {
      this.beatIdx++;
    } else if (this.chapterIdx < this.story.chapters.length - 1) {
      this.chapterIdx++;
      this.beatIdx = 0;
    } else {
      this.playing = false;
      this._showFinale();
      return;
    }
    if (this.playing) this._executeBeat(this.currentBeat);
  }

  prev() {
    if (this.beatIdx > 0) {
      this.beatIdx--;
    } else if (this.chapterIdx > 0) {
      this.chapterIdx--;
      const ch = this.currentChapter;
      this.beatIdx = ch.beats.length - 1;
    }
    this._executeBeat(this.currentBeat);
  }

  jumpTo(chapterIdx, beatIdx) {
    this.chapterIdx = chapterIdx;
    this.beatIdx = beatIdx;
    this._executeBeat(this.currentBeat);
  }

  _executeBeat(beat) {
    if (!beat) return;
    this._moveCinematicCamera(beat.camera, beat.transition);
    this._highlightNodes(beat.nodeIds);
    this._highlightLinks(beat.highlightLinks || []);
    this._spotlightEvidence(beat.evidenceSpotlight || []);
    this._updateNarration(beat.narration);
    this._addBreadcrumb(beat);
    this._updateChapterTitle();

    if (this.playing && this.story.settings.autoAdvance) {
      const wait = beat.pause || 4000;
      this.timer = setTimeout(() => this.next(), wait + (beat.transition?.duration || 800));
    }
  }

  _moveCinematicCamera(cam, trans) {
    if (!cam) return;
    const dur = trans?.duration || 800;
    const ease = this._resolveEase(trans?.ease || "cubicInOut");
    const transform = d3.zoomIdentity
      .translate(window.innerWidth / 2, window.innerHeight / 2)
      .scale(cam.zoom)
      .translate(-cam.x, -cam.y);
    this.svg.transition()
      .duration(dur)
      .ease(ease)
      .call(this.zoomBehavior.transform, transform);
  }

  _resolveEase(name) {
    const map = {
      cubicInOut: d3.easeCubicInOut,
      linear: d3.easeLinear,
      elasticOut: d3.easeElasticOut,
      bounceOut: d3.easeBounceOut,
      quadInOut: d3.easeQuadInOut,
    };
    return map[name] || d3.easeCubicInOut;
  }

  _highlightNodes(nodeIds) {
    const idSet = new Set(nodeIds);
    d3.selectAll(".node")
      .classed("narrative-active", d => idSet.has(d.id))
      .classed("narrative-dimmed", d => !idSet.has(d.id));
  }

  _highlightLinks(linkIds) {
    const idSet = new Set(linkIds);
    d3.selectAll(".link")
      .classed("narrative-link-active", d => idSet.has(d.id))
      .classed("narrative-link-dimmed", d => !idSet.has(d.id));
  }

  _spotlightEvidence(batesNums) {
    if (!batesNums.length) return;
    const bSet = new Set(batesNums);
    d3.selectAll(".node")
      .filter(d => d.batesNumber && bSet.has(d.batesNumber))
      .each(function () {
        const el = d3.select(this);
        el.select("circle")
          .transition().duration(300)
          .attr("r", d => (d.radius || 6) * 2.2)
          .attr("stroke", "#FFD700")
          .attr("stroke-width", 4)
          .transition().duration(600)
          .attr("r", d => (d.radius || 6) * 1.5)
          .attr("stroke-width", 2);
      });
  }

  _updateNarration(text) {
    this.overlay.select(".narration-text")
      .text(text || "")
      .style("opacity", 0)
      .transition().duration(500)
      .style("opacity", 1);
  }

  _updateChapterTitle() {
    const ch = this.currentChapter;
    if (!ch) return;
    this.overlay.select(".chapter-title").text(ch.title);
    this.overlay.select(".beat-counter")
      .text(`${this.beatIdx + 1} / ${ch.beats.length}`);
  }

  _addBreadcrumb(beat) {
    this.breadcrumbs.push({ x: beat.camera.x, y: beat.camera.y, id: beat.id });
    this._renderBreadcrumbTrail();
  }

  _createOverlay() {
    const ov = d3.select("body").append("div")
      .attr("class", "narrative-overlay")
      .style("position", "fixed")
      .style("bottom", "0")
      .style("left", "0")
      .style("width", "100%")
      .style("pointer-events", "none")
      .style("z-index", "9000");

    ov.append("div").attr("class", "chapter-title");
    ov.append("div").attr("class", "narration-text");
    ov.append("div").attr("class", "beat-counter");
    return ov;
  }

  _createBreadcrumbTrail() {
    return this.svg.append("g").attr("class", "breadcrumb-trail");
  }

  _renderBreadcrumbTrail() {
    const line = d3.line()
      .x(d => d.x)
      .y(d => d.y)
      .curve(d3.curveCatmullRom.alpha(0.5));

    this.breadcrumbTrail.selectAll("path").remove();

    if (this.breadcrumbs.length >= 2) {
      this.breadcrumbTrail.append("path")
        .attr("d", line(this.breadcrumbs))
        .attr("fill", "none")
        .attr("stroke", "rgba(0, 200, 255, 0.6)")
        .attr("stroke-width", 3)
        .attr("stroke-dasharray", function () {
          return this.getTotalLength();
        })
        .attr("stroke-dashoffset", function () {
          return this.getTotalLength();
        })
        .transition().duration(800)
        .attr("stroke-dashoffset", 0);
    }

    this.breadcrumbTrail.selectAll("circle")
      .data(this.breadcrumbs, d => d.id)
      .join("circle")
      .attr("cx", d => d.x)
      .attr("cy", d => d.y)
      .attr("r", 5)
      .attr("fill", "#00C8FF")
      .attr("opacity", 0.8);
  }

  _showFinale() {
    this.overlay.select(".narration-text")
      .text("— End of Narrative —")
      .style("font-size", "1.4em");
  }

  setZoomBehavior(zb) {
    this.zoomBehavior = zb;
  }

  destroy() {
    clearTimeout(this.timer);
    this.overlay.remove();
    this.breadcrumbTrail.remove();
  }
}
```

---

## 3. Jury Presentation Mode (CSS + JS)

Jury mode strips visual complexity and uses large fonts, high contrast,
and dramatic one-at-a-time reveal animations.

```css
/* --- Jury Presentation Mode --- */
body.jury-mode {
  background: #000 !important;
}

.jury-mode .node.narrative-dimmed circle {
  opacity: 0.05;
}

.jury-mode .node.narrative-active circle {
  stroke: #FFD700;
  stroke-width: 4px;
  filter: drop-shadow(0 0 12px #FFD700);
}

.jury-mode .link.narrative-link-dimmed {
  opacity: 0.02;
}

.jury-mode .link.narrative-link-active {
  stroke: #FF4444;
  stroke-width: 3px;
  filter: drop-shadow(0 0 6px #FF4444);
}

.jury-mode .narrative-overlay {
  background: linear-gradient(to top, rgba(0,0,0,0.95), transparent);
  padding: 40px 60px;
}

.jury-mode .chapter-title {
  font-family: "Georgia", serif;
  font-size: 2rem;
  color: #FFD700;
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 2px;
}

.jury-mode .narration-text {
  font-family: "Georgia", serif;
  font-size: 1.6rem;
  color: #FFFFFF;
  line-height: 1.8;
  max-width: 900px;
}

.jury-mode .beat-counter {
  font-family: monospace;
  font-size: 0.9rem;
  color: #888;
  margin-top: 8px;
}

.jury-mode .breadcrumb-trail path {
  stroke: rgba(255, 215, 0, 0.5);
  stroke-width: 4;
}

.jury-mode .breadcrumb-trail circle {
  fill: #FFD700;
}
```

```javascript
function toggleJuryMode(storyController, enabled) {
  document.body.classList.toggle("jury-mode", enabled);
  storyController.story.settings.juryMode = enabled;
  if (enabled) {
    storyController.simulation.alphaTarget(0).stop();
    d3.selectAll(".layer-toggle, .search-panel, .filter-bar")
      .style("display", "none");
  } else {
    storyController.simulation.alphaTarget(0.05).restart();
    d3.selectAll(".layer-toggle, .search-panel, .filter-bar")
      .style("display", null);
  }
}
```

---

## 4. Progressive Reveal — "Build the Case" Mode

Progressive reveal shows nothing initially, then adds nodes and links
beat-by-beat so the audience watches the case *construct itself*.

```javascript
class ProgressiveRevealEngine {
  constructor(graphData, svg) {
    this.allNodes = graphData.nodes;
    this.allLinks = graphData.links;
    this.revealedNodeIds = new Set();
    this.revealedLinkIds = new Set();
    this.svg = svg;
  }

  hideAll() {
    d3.selectAll(".node").style("opacity", 0).style("pointer-events", "none");
    d3.selectAll(".link").style("opacity", 0);
  }

  revealNodes(nodeIds, duration = 800) {
    nodeIds.forEach(id => this.revealedNodeIds.add(id));
    d3.selectAll(".node")
      .filter(d => nodeIds.includes(d.id))
      .transition().duration(duration)
      .style("opacity", 1)
      .style("pointer-events", "all")
      .select("circle")
        .attr("r", 0)
        .transition().duration(duration / 2)
        .attr("r", d => d.radius || 6);
  }

  revealLinks(linkIds, duration = 600) {
    linkIds.forEach(id => this.revealedLinkIds.add(id));
    d3.selectAll(".link")
      .filter(d => linkIds.includes(d.id))
      .each(function () {
        const el = d3.select(this);
        const totalLen = this.getTotalLength ? this.getTotalLength() : 100;
        el.attr("stroke-dasharray", totalLen)
          .attr("stroke-dashoffset", totalLen)
          .transition().duration(duration)
          .style("opacity", 1)
          .attr("stroke-dashoffset", 0);
      });
  }

  revealBeat(beat) {
    this.revealNodes(beat.nodeIds || []);
    this.revealLinks(beat.highlightLinks || [], 600);
  }

  reset() {
    this.revealedNodeIds.clear();
    this.revealedLinkIds.clear();
    this.hideAll();
  }
}
```

---

## 5. Voice-Over Integration (Web Speech API)

Hooks for text-to-speech narration driven by beat narration text.

```javascript
class VoiceOverEngine {
  constructor() {
    this.synth = window.speechSynthesis;
    this.voice = null;
    this.rate = 0.95;
    this.pitch = 1.0;
    this.speaking = false;
    this._selectVoice();
  }

  _selectVoice() {
    const trySelect = () => {
      const voices = this.synth.getVoices();
      this.voice = voices.find(v => v.name.includes("Microsoft David"))
        || voices.find(v => v.lang === "en-US" && !v.localService)
        || voices[0] || null;
    };
    trySelect();
    if (!this.voice) {
      this.synth.addEventListener("voiceschanged", trySelect, { once: true });
    }
  }

  speak(text, onEnd) {
    this.stop();
    if (!text) return;
    const utt = new SpeechSynthesisUtterance(text);
    utt.voice = this.voice;
    utt.rate = this.rate;
    utt.pitch = this.pitch;
    utt.onend = () => { this.speaking = false; if (onEnd) onEnd(); };
    utt.onerror = () => { this.speaking = false; };
    this.speaking = true;
    this.synth.speak(utt);
  }

  stop() {
    if (this.synth.speaking) this.synth.cancel();
    this.speaking = false;
  }

  setRate(r) { this.rate = Math.max(0.5, Math.min(2.0, r)); }
  setPitch(p) { this.pitch = Math.max(0.5, Math.min(1.5, p)); }
}
```

---

## 6. Presentation Export

Generate a structured slide-deck outline from the narrative arc JSON,
suitable for external tools or direct HTML rendering.

```javascript
function exportPresentationOutline(story) {
  const slides = [];
  slides.push({
    type: "title",
    title: story.title,
    subtitle: `Generated ${new Date().toISOString().slice(0, 10)}`,
  });

  for (const chapter of story.chapters) {
    slides.push({
      type: "chapter-divider",
      title: chapter.title,
    });
    for (const beat of chapter.beats) {
      slides.push({
        type: "content",
        chapter: chapter.title,
        narration: beat.narration,
        evidence: beat.evidenceSpotlight || [],
        focusNodes: beat.nodeIds,
      });
    }
  }

  slides.push({ type: "closing", title: "Conclusion" });
  return JSON.stringify(slides, null, 2);
}
```

---

## 7. Narrative Playback Controls (HTML + CSS)

```html
<div id="narrative-controls" class="narrative-controls">
  <button id="nc-prev" title="Previous beat">⏮</button>
  <button id="nc-play" title="Play / Pause">▶</button>
  <button id="nc-next" title="Next beat">⏭</button>
  <span id="nc-progress">1 / 12</span>
  <label>
    <input type="checkbox" id="nc-voice"> Voice
  </label>
  <label>
    <input type="checkbox" id="nc-jury"> Jury Mode
  </label>
</div>
```

```css
.narrative-controls {
  position: fixed;
  bottom: 120px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(15, 15, 25, 0.92);
  border: 1px solid rgba(0, 200, 255, 0.3);
  border-radius: 8px;
  padding: 8px 20px;
  z-index: 9500;
  pointer-events: all;
}

.narrative-controls button {
  background: none;
  border: 1px solid rgba(0, 200, 255, 0.5);
  color: #00C8FF;
  font-size: 1.2rem;
  padding: 6px 14px;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
}

.narrative-controls button:hover {
  background: rgba(0, 200, 255, 0.15);
}

.narrative-controls span {
  color: #ccc;
  font-family: monospace;
  font-size: 0.85rem;
}

.narrative-controls label {
  color: #aaa;
  font-size: 0.8rem;
  cursor: pointer;
}
```

```javascript
function wireNarrativeControls(storyCtrl, voiceEngine) {
  const playBtn = document.getElementById("nc-play");
  const prevBtn = document.getElementById("nc-prev");
  const nextBtn = document.getElementById("nc-next");
  const voiceCb = document.getElementById("nc-voice");
  const juryCb = document.getElementById("nc-jury");
  const progress = document.getElementById("nc-progress");

  playBtn.addEventListener("click", () => {
    if (storyCtrl.playing) {
      storyCtrl.pause();
      voiceEngine.stop();
      playBtn.textContent = "▶";
    } else {
      storyCtrl.play();
      playBtn.textContent = "⏸";
    }
  });

  prevBtn.addEventListener("click", () => { storyCtrl.prev(); voiceEngine.stop(); });
  nextBtn.addEventListener("click", () => { storyCtrl.next(); voiceEngine.stop(); });

  juryCb.addEventListener("change", (e) => {
    toggleJuryMode(storyCtrl, e.target.checked);
  });

  const origExecute = storyCtrl._executeBeat.bind(storyCtrl);
  storyCtrl._executeBeat = function (beat) {
    origExecute(beat);
    const ch = this.currentChapter;
    if (ch) progress.textContent = `${this.beatIdx + 1} / ${ch.beats.length}`;
    if (voiceCb.checked && beat?.narration) {
      voiceEngine.speak(beat.narration);
    }
  };
}
```

---

## 8. Cinematic Camera Utilities

```javascript
function flyToNode(svg, zoomBehavior, node, zoom = 2.5, duration = 1000) {
  const transform = d3.zoomIdentity
    .translate(window.innerWidth / 2, window.innerHeight / 2)
    .scale(zoom)
    .translate(-node.x, -node.y);
  svg.transition()
    .duration(duration)
    .ease(d3.easeCubicInOut)
    .call(zoomBehavior.transform, transform);
}

function flyAlongPath(svg, zoomBehavior, points, zoom, stepDuration) {
  let chain = svg;
  for (const pt of points) {
    const t = d3.zoomIdentity
      .translate(window.innerWidth / 2, window.innerHeight / 2)
      .scale(zoom)
      .translate(-pt.x, -pt.y);
    chain = chain.transition()
      .duration(stepDuration)
      .ease(d3.easeCubicInOut)
      .call(zoomBehavior.transform, t);
  }
  return chain;
}

function resetCamera(svg, zoomBehavior, duration = 600) {
  svg.transition()
    .duration(duration)
    .ease(d3.easeCubicOut)
    .call(zoomBehavior.transform, d3.zoomIdentity);
}
```

---

## 9. Python Bridge — Load / Save Narratives

```python
"""Narrative story persistence via pywebview bridge."""
import json
import os
from pathlib import Path

NARRATIVE_DIR = Path(__file__).resolve().parent.parent / "04_ANALYSIS" / "NARRATIVES"


def save_story(story_json: str) -> dict:
    """Save a narrative arc JSON to disk."""
    NARRATIVE_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(story_json)
    sid = data.get("storyId", "untitled")
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in sid)
    path = NARRATIVE_DIR / f"{safe_name}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"ok": True, "path": str(path)}


def load_story(story_id: str) -> dict:
    """Load a narrative arc JSON from disk."""
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in story_id)
    path = NARRATIVE_DIR / f"{safe_name}.json"
    if not path.exists():
        return {"ok": False, "error": f"Story not found: {story_id}"}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {"ok": True, "story": data}


def list_stories() -> dict:
    """List all saved narrative arcs."""
    NARRATIVE_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(NARRATIVE_DIR.glob("*.json"))
    stories = []
    for f in files:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            stories.append({
                "storyId": d.get("storyId", f.stem),
                "title": d.get("title", "Untitled"),
                "chapters": len(d.get("chapters", [])),
            })
        except (json.JSONDecodeError, KeyError):
            continue
    return {"ok": True, "stories": stories}
```

---

## 10. Anti-Patterns (MANDATORY — violations break narrative UX)

1. **Never auto-play on load.** Always wait for explicit user action.
2. **Never skip camera transitions.** Jarring jumps destroy spatial context.
3. **Never hard-code beat pause durations.** Use narration length × 50ms as minimum.
4. **Never render narration inside SVG.** Use HTML overlay — SVG text is unreadable.
5. **Never block the main thread during voice synthesis.** SpeechSynthesis is async.
6. **Never store narrative JSON in the DB.** Narratives are files in `04_ANALYSIS/`.
7. **Never dim ALL nodes to zero opacity.** Keep a 0.05 floor so the graph skeleton shows.
8. **Never mutate original graph data for reveal.** Use CSS classes, not data deletion.
9. **Never rely solely on color for narrative state.** Use size + glow + animation.
10. **Never allow keyboard shortcuts during jury mode.** Lock to play/pause/prev/next.
11. **Never expose file paths in narration text.** It is court-facing.
12. **Never play voice-over while previous utterance still speaks.** Cancel first.
13. **Never generate breadcrumb trail with raw line segments.** Use CatmullRom curve.
14. **Never create a story with > 50 beats per chapter.** Split into smaller chapters.
15. **Never animate more than 20 nodes simultaneously during reveal.** Stagger them.
16. **Never put the child's full name in any narration text.** Always L.D.W.

---

## 11. Performance Budgets

| Metric | Budget | Action if Exceeded |
|--------|--------|--------------------|
| Camera transition duration | 600–1500 ms | Reduce node count in view |
| Beat execution total time | < 200 ms (excluding transition) | Defer spotlight to rAF |
| Narration overlay render | < 16 ms | Avoid layout thrash in overlay |
| Breadcrumb trail path recalc | < 8 ms | Simplify path for > 100 crumbs |
| Progressive reveal per beat | ≤ 20 nodes | Batch larger reveals across beats |
| Voice synth latency | < 500 ms to first word | Pre-buffer next utterance |
| Total story JSON size | < 500 KB | Compress or split into volumes |
| Simultaneous CSS transitions | ≤ 30 elements | Use class toggling, not per-node |
| Memory for breadcrumb points | < 5000 entries | Prune oldest on overflow |

---

## 12. Integration Points

| Component | Interface | Direction |
|-----------|-----------|-----------|
| Graph renderer | `.node` / `.link` CSS classes | Narrative reads/styles |
| Zoom behavior | `d3.zoom()` instance | Narrative drives camera |
| pywebview bridge | `window.expose(save_story, load_story)` | JS ↔ Python file I/O |
| HUD | `narrative-overlay` z-index 9000 | Narrative below HUD (9500) |
| Timeline scrubber | Beat timestamps | Narrative syncs to timeline |
| Evidence layer | Bates number mapping | Spotlight queries by Bates |
| Engine bridge | `nexus_fuse` for real-time evidence | Enriches narration dynamically |

---

*END SINGULARITY-MBP-INTERFACE-NARRATIVE v1.0.0 — Cinematic litigation storytelling for THEMANBEARPIG.*

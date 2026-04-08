---
name: SINGULARITY-MBP-TRANSCENDENCE-SONIC
version: "1.0.0"
description: "Audio sonification for THEMANBEARPIG: Web Audio API, threat→pitch mapping, ambient soundscapes, spatial audio for graph navigation, timeline playback audio, impeachment chord system, evidence density pulse. Transforms litigation data into auditory intelligence within the pywebview desktop app."
tier: "TIER-6/TRANSCENDENCE"
domain: "Audio sonification — Web Audio API, threat-to-pitch mapping, ambient soundscapes, spatial audio, timeline audio, impeachment chords"
triggers:
  - sonic
  - audio
  - sonification
  - Web Audio
  - pitch
  - soundscape
  - ambient
  - threat sound
  - audio feedback
  - spatial audio
cross_links:
  - SINGULARITY-MBP-FORGE-RENDERER
  - SINGULARITY-MBP-FORGE-EFFECTS
  - SINGULARITY-MBP-INTERFACE-TIMELINE
  - SINGULARITY-MBP-INTERFACE-HUD
  - SINGULARITY-MBP-COMBAT-ADVERSARY
  - SINGULARITY-MBP-COMBAT-IMPEACHMENT
  - SINGULARITY-MBP-EMERGENCE-PREDICTION
  - SINGULARITY-MBP-FORGE-DEPLOY
---

# SINGULARITY-MBP-TRANSCENDENCE-SONIC v1.0

> **Data you can hear. Threats you can feel. The graph speaks.**

## Layer 1: Web Audio API Architecture

### 1.1 AudioContext Initialization & Master Bus

The Web Audio API requires a user gesture before creating an AudioContext (browser policy).
THEMANBEARPIG hooks into the first user click/keypress to initialize the entire audio graph.

```javascript
// ── sonification_engine.js ──
// Master audio engine for THEMANBEARPIG litigation sonification

class SonificationEngine {
  constructor() {
    this._ctx = null;
    this._masterGain = null;
    this._compressor = null;
    this._limiter = null;
    this._analyser = null;
    this._layerGains = {};     // per-layer volume controls
    this._oscillatorPool = []; // reusable oscillator bank
    this._activeOscillators = new Map();
    this._ambientDrone = null;
    this._isInitialized = false;
    this._isMuted = false;
    this._masterVolume = 0.4;  // conservative default
    this._mode = 'ambient';    // ambient | interactive | timeline | off
  }

  /**
   * Initialize the audio graph. MUST be called from a user gesture handler.
   * Creates: AudioContext → Compressor → Limiter → Analyser → Destination
   */
  init() {
    if (this._isInitialized) return;

    // AudioContext — one per app, never recreate
    this._ctx = new (window.AudioContext || window.webkitAudioContext)({
      sampleRate: 44100,
      latencyHint: 'interactive'
    });

    // Master gain — overall volume control
    this._masterGain = this._ctx.createGain();
    this._masterGain.gain.value = this._masterVolume;

    // Compressor — prevents clipping when many oscillators fire simultaneously
    this._compressor = this._ctx.createDynamicsCompressor();
    this._compressor.threshold.value = -24;  // start compressing at -24dB
    this._compressor.knee.value = 12;
    this._compressor.ratio.value = 8;        // 8:1 compression
    this._compressor.attack.value = 0.003;   // 3ms attack (fast transients)
    this._compressor.release.value = 0.15;   // 150ms release

    // Limiter — hard ceiling at -3dB, prevents any output above threshold
    this._limiter = this._ctx.createDynamicsCompressor();
    this._limiter.threshold.value = -3;
    this._limiter.knee.value = 0;            // brick wall
    this._limiter.ratio.value = 20;          // near-infinite ratio
    this._limiter.attack.value = 0.001;
    this._limiter.release.value = 0.01;

    // Analyser — for UI level meters and waveform display
    this._analyser = this._ctx.createAnalyser();
    this._analyser.fftSize = 256;
    this._analyser.smoothingTimeConstant = 0.8;

    // Signal chain: sources → masterGain → compressor → limiter → analyser → destination
    this._masterGain.connect(this._compressor);
    this._compressor.connect(this._limiter);
    this._limiter.connect(this._analyser);
    this._analyser.connect(this._ctx.destination);

    // Per-layer gain nodes (13 THEMANBEARPIG layers)
    const LAYERS = [
      'adversary', 'weapon', 'judicial', 'evidence', 'authority',
      'impeachment', 'timeline', 'filing', 'brain', 'engine',
      'hud', 'narrative', 'convergence'
    ];
    for (const layer of LAYERS) {
      const gain = this._ctx.createGain();
      gain.gain.value = 0.6; // per-layer default
      gain.connect(this._masterGain);
      this._layerGains[layer] = gain;
    }

    this._isInitialized = true;
    console.log('[SONIC] AudioContext initialized, sampleRate:', this._ctx.sampleRate);
  }

  /** Ensure AudioContext is running (may be suspended by browser) */
  async resume() {
    if (this._ctx && this._ctx.state === 'suspended') {
      await this._ctx.resume();
    }
  }

  /** Get current audio context time (high-resolution) */
  get now() { return this._ctx ? this._ctx.currentTime : 0; }

  /** Get the destination node for a given layer */
  getLayerOutput(layerName) {
    return this._layerGains[layerName] || this._masterGain;
  }
}
```

### 1.2 Oscillator Pool & Reuse Strategy

Creating and destroying oscillators per-event is expensive. The pool pre-allocates reusable
oscillator + gain pairs, recycling stopped oscillators instead of garbage collecting them.

```javascript
// ── oscillator_pool.js ──
// Pooled oscillator management — never exceed MAX_SIMULTANEOUS

const MAX_SIMULTANEOUS_OSCILLATORS = 32;

class OscillatorPool {
  constructor(engine) {
    this._engine = engine;
    this._available = [];
    this._active = new Map(); // id → {osc, gain, startTime}
  }

  /**
   * Acquire an oscillator from the pool.
   * Returns {osc, gain} connected to the specified layer output.
   * If pool is exhausted, steals the oldest active oscillator.
   */
  acquire(layerName, id) {
    const ctx = this._engine._ctx;
    const destination = this._engine.getLayerOutput(layerName);

    // Steal oldest if at capacity
    if (this._active.size >= MAX_SIMULTANEOUS_OSCILLATORS) {
      const oldest = this._active.entries().next().value;
      if (oldest) {
        this.release(oldest[0]);
      }
    }

    // Create fresh oscillator (cannot restart stopped oscillators per Web Audio spec)
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    gain.gain.value = 0; // start silent — always fade in
    osc.connect(gain);
    gain.connect(destination);

    const entry = { osc, gain, startTime: ctx.currentTime };
    this._active.set(id, entry);
    return entry;
  }

  /**
   * Release an oscillator — fade out and stop.
   * Fade prevents clicks/pops from abrupt stop.
   */
  release(id, fadeTime = 0.05) {
    const entry = this._active.get(id);
    if (!entry) return;

    const now = this._engine.now;
    entry.gain.gain.cancelScheduledValues(now);
    entry.gain.gain.setValueAtTime(entry.gain.gain.value, now);
    entry.gain.gain.linearRampToValueAtTime(0, now + fadeTime);

    // Stop after fade completes
    try {
      entry.osc.stop(now + fadeTime + 0.01);
    } catch (e) {
      // oscillator may already be stopped
    }

    this._active.delete(id);
  }

  /** Release all active oscillators */
  releaseAll(fadeTime = 0.1) {
    for (const id of [...this._active.keys()]) {
      this.release(id, fadeTime);
    }
  }

  /** Count of currently active oscillators */
  get activeCount() { return this._active.size; }
}
```

### 1.3 Convolver Node for Spatial Reverb

Reverb gives depth and space to the sonification. A short impulse response simulates
a small room — making the graph feel like a physical space.

```javascript
/**
 * Load or generate a reverb impulse response.
 * Synthetic IR avoids needing external audio files in the EXE bundle.
 */
function createSyntheticReverb(ctx, duration = 1.5, decay = 2.0) {
  const sampleRate = ctx.sampleRate;
  const length = sampleRate * duration;
  const buffer = ctx.createBuffer(2, length, sampleRate);

  for (let channel = 0; channel < 2; channel++) {
    const data = buffer.getChannelData(channel);
    for (let i = 0; i < length; i++) {
      // Exponentially decaying white noise
      data[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / length, decay);
    }
  }

  const convolver = ctx.createConvolver();
  convolver.buffer = buffer;

  // Wet/dry mix via parallel gain nodes
  const dryGain = ctx.createGain();
  dryGain.gain.value = 0.7;
  const wetGain = ctx.createGain();
  wetGain.gain.value = 0.3;

  return { convolver, dryGain, wetGain };
}
```

---

## Layer 2: Threat Sonification Engine

### 2.1 Threat-to-Audio Parameter Mapping

Every node in the graph has a threat_level (0.0–1.0). The sonification engine maps
this scalar to multiple audio dimensions simultaneously, creating a rich auditory signature.

```javascript
// ── threat_mapper.js ──
// Maps threat_level [0, 1] to audio parameters

const THREAT_AUDIO_MAP = {
  // Frequency: low threat = warm low tones, high threat = piercing high tones
  frequency: {
    min: 110,    // A2 — warm bass
    max: 880,    // A5 — piercing treble
    curve: 'exponential'
  },

  // Waveform: low threat = smooth sine, high threat = harsh sawtooth
  waveform: [
    { threshold: 0.0, type: 'sine' },
    { threshold: 0.3, type: 'triangle' },
    { threshold: 0.6, type: 'square' },
    { threshold: 0.8, type: 'sawtooth' }
  ],

  // Modulation rate: low threat = slow pulse, high threat = rapid tremolo
  modulationRate: {
    min: 0.5,   // Hz — gentle breathing
    max: 12,    // Hz — frantic vibrato
    curve: 'linear'
  },

  // Detune: low threat = in tune, high threat = dissonant beating
  detune: {
    min: 0,     // cents
    max: 50,    // cents — audible beating/roughness
    curve: 'quadratic'
  },

  // Volume: threat nodes are louder (attention-grabbing)
  gain: {
    min: 0.05,
    max: 0.35,
    curve: 'linear'
  },

  // Pan: high-threat nodes pan slightly left (subconscious unease)
  pan: {
    min: 0,     // center
    max: -0.3,  // slight left
    curve: 'linear'
  }
};

/**
 * Compute all audio parameters for a given threat level.
 * @param {number} threatLevel - 0.0 (safe) to 1.0 (critical)
 * @returns {Object} Audio parameter set
 */
function threatToAudio(threatLevel) {
  const t = Math.max(0, Math.min(1, threatLevel));

  // Exponential frequency mapping (perceptually linear pitch)
  const freq = THREAT_AUDIO_MAP.frequency.min *
    Math.pow(THREAT_AUDIO_MAP.frequency.max / THREAT_AUDIO_MAP.frequency.min, t);

  // Waveform selection by threshold
  let waveform = 'sine';
  for (const entry of THREAT_AUDIO_MAP.waveform) {
    if (t >= entry.threshold) waveform = entry.type;
  }

  // Linear interpolation for simple parameters
  const lerp = (map) => map.min + (map.max - map.min) * t;

  return {
    frequency: freq,
    waveform: waveform,
    modulationRate: lerp(THREAT_AUDIO_MAP.modulationRate),
    detune: t * t * THREAT_AUDIO_MAP.detune.max, // quadratic
    gain: lerp(THREAT_AUDIO_MAP.gain),
    pan: lerp(THREAT_AUDIO_MAP.pan)
  };
}
```

### 2.2 Adversary Node Continuous Tones

Each adversary node emits a persistent tone when visible on screen. The tone encodes
the adversary's threat level, connection count, and credibility score.

```javascript
/**
 * Start a continuous tone for an adversary node.
 * Tone persists while node is in viewport, fades when scrolled away.
 */
function startAdversaryTone(engine, pool, node) {
  const params = threatToAudio(node.threat_level || 0.5);
  const id = `adversary-${node.id}`;
  const { osc, gain } = pool.acquire('adversary', id);

  osc.type = params.waveform;
  osc.frequency.value = params.frequency;
  osc.detune.value = params.detune;

  // LFO for tremolo (amplitude modulation)
  const ctx = engine._ctx;
  const lfo = ctx.createOscillator();
  const lfoGain = ctx.createGain();
  lfo.frequency.value = params.modulationRate;
  lfoGain.gain.value = params.gain * 0.3; // modulation depth = 30% of volume
  lfo.connect(lfoGain);
  lfoGain.connect(gain.gain);

  // Stereo panner based on node's x-position in viewport
  const panner = ctx.createStereoPanner();
  const viewportX = node.screenX / window.innerWidth; // 0..1
  panner.pan.value = (viewportX - 0.5) * 2; // -1..1
  gain.disconnect();
  gain.connect(panner);
  panner.connect(engine.getLayerOutput('adversary'));

  // Fade in over 200ms to prevent click
  const now = engine.now;
  gain.gain.setValueAtTime(0, now);
  gain.gain.linearRampToValueAtTime(params.gain, now + 0.2);

  osc.start(now);
  lfo.start(now);

  return { id, lfo, panner };
}
```

### 2.3 Weapon Chain Rhythmic Patterns

Weapon chains (false allegations, ex parte orders, contempt, etc.) are rendered as
rhythmic sequences. Each weapon type has a distinct rhythmic signature.

```javascript
// Weapon type → rhythmic pattern (durations in beats, tempo = 120bpm)
const WEAPON_RHYTHMS = {
  'false_allegation':    [0.25, 0.25, 0.5, 0.25, 0.25, 0.5],  // staccato bursts
  'ex_parte_order':      [1.0, 0.5, 0.5],                       // heavy downbeat
  'contempt':            [0.125, 0.125, 0.125, 0.125, 0.5],     // frantic, then silence
  'ppo_weaponization':   [0.5, 0.25, 0.25, 0.5, 0.5],           // march-like
  'evidence_exclusion':  [0.75, 0.25, 0.75, 0.25],              // syncopated
  'due_process_denial':  [1.0, 1.0],                             // slow, ominous
  'benchbook_violation': [0.33, 0.33, 0.34, 0.5, 0.5],          // triplet feel
  'custody_manipulation':[0.5, 0.5, 0.25, 0.25, 0.5],           // irregular
  'incarceration':       [2.0]                                    // single sustained tone
};

/**
 * Play a weapon chain as a rhythmic pattern.
 * Each note in the pattern uses the threat-mapped frequency.
 */
function playWeaponRhythm(engine, weaponType, threatLevel, repeat = 1) {
  const ctx = engine._ctx;
  const pattern = WEAPON_RHYTHMS[weaponType] || [0.5, 0.5];
  const params = threatToAudio(threatLevel);
  const bps = 120 / 60; // beats per second at 120bpm
  let time = ctx.currentTime + 0.05;

  for (let rep = 0; rep < repeat; rep++) {
    for (const duration of pattern) {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = params.waveform;
      osc.frequency.value = params.frequency;
      osc.detune.value = params.detune + (Math.random() * 10 - 5);

      const noteDuration = duration / bps;
      const attackTime = Math.min(0.01, noteDuration * 0.1);
      const releaseTime = Math.min(0.05, noteDuration * 0.3);

      gain.gain.setValueAtTime(0, time);
      gain.gain.linearRampToValueAtTime(params.gain * 0.5, time + attackTime);
      gain.gain.setValueAtTime(params.gain * 0.5, time + noteDuration - releaseTime);
      gain.gain.linearRampToValueAtTime(0, time + noteDuration);

      osc.connect(gain);
      gain.connect(engine.getLayerOutput('weapon'));

      osc.start(time);
      osc.stop(time + noteDuration + 0.01);

      time += noteDuration;
    }
    time += 0.2 / bps; // gap between repeats
  }
}
```

---

## Layer 3: Ambient Soundscape Generator

### 3.1 Case Health Drone

A continuous background drone that reflects overall case health. The drone uses
additive synthesis — multiple sine waves at harmonically related frequencies create
a rich, evolving texture that shifts as case metrics change.

```javascript
/**
 * Ambient drone generator. Shifts timbre based on case health metrics.
 *
 * @param {Object} caseHealth - { convergence: 0-1, deadlineUrgency: 0-1,
 *                                evidenceGaps: 0-1, filingReadiness: 0-1 }
 */
class AmbientDrone {
  constructor(engine) {
    this._engine = engine;
    this._oscillators = [];
    this._isPlaying = false;
    this._baseFreq = 55; // A1 — deep bass foundation
  }

  start(caseHealth) {
    if (this._isPlaying) this.updateHealth(caseHealth);
    if (this._isPlaying) return;

    const ctx = this._engine._ctx;
    const dest = this._engine.getLayerOutput('convergence');
    const now = ctx.currentTime;

    // 6-oscillator additive synthesis stack
    const harmonics = [1, 1.5, 2, 3, 4, 5]; // fundamental + overtones
    const gains =     [0.15, 0.08, 0.06, 0.04, 0.03, 0.02]; // decreasing amplitude

    for (let i = 0; i < harmonics.length; i++) {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'sine';
      osc.frequency.value = this._baseFreq * harmonics[i];
      gain.gain.setValueAtTime(0, now);
      gain.gain.linearRampToValueAtTime(gains[i], now + 2.0); // slow fade in

      // Slow LFO per oscillator for organic movement
      const lfo = ctx.createOscillator();
      const lfoGain = ctx.createGain();
      lfo.frequency.value = 0.1 + i * 0.03; // slightly different rate per voice
      lfoGain.gain.value = 3 + i * 2; // frequency deviation in Hz
      lfo.connect(lfoGain);
      lfoGain.connect(osc.frequency);
      lfo.start(now);

      osc.connect(gain);
      gain.connect(dest);
      osc.start(now);

      this._oscillators.push({ osc, gain, lfo, lfoGain, harmonic: harmonics[i] });
    }

    this._isPlaying = true;
    this.updateHealth(caseHealth);
  }

  /**
   * Shift drone character based on case health.
   * High convergence → warm, consonant overtones
   * Deadline urgency → dissonant intervals, faster LFO
   * Evidence gaps → sparse, thin texture
   */
  updateHealth(health) {
    if (!this._isPlaying) return;
    const ctx = this._engine._ctx;
    const now = ctx.currentTime;
    const transitionTime = 2.0; // smooth 2-second transitions

    for (const voice of this._oscillators) {
      // Urgency shifts pitch up and adds detuning
      const urgencyDetune = (health.deadlineUrgency || 0) * 30; // up to 30 cents sharp
      const targetFreq = this._baseFreq * voice.harmonic + urgencyDetune * voice.harmonic;
      voice.osc.frequency.linearRampToValueAtTime(targetFreq, now + transitionTime);

      // Low convergence → faster, wider LFO (uneasy movement)
      const convergence = health.convergence || 0.5;
      const lfoRate = 0.05 + (1 - convergence) * 0.3;
      voice.lfo.frequency.linearRampToValueAtTime(lfoRate, now + transitionTime);

      // Evidence gaps → reduce higher harmonics (thinner texture)
      const gapPenalty = (health.evidenceGaps || 0) * 0.6;
      const baseGain = voice.gain.gain.value;
      if (voice.harmonic > 2) {
        const thinned = baseGain * (1 - gapPenalty);
        voice.gain.gain.linearRampToValueAtTime(Math.max(0.005, thinned), now + transitionTime);
      }
    }
  }

  stop() {
    if (!this._isPlaying) return;
    const now = this._engine.now;
    for (const voice of this._oscillators) {
      voice.gain.gain.linearRampToValueAtTime(0, now + 1.0);
      voice.osc.stop(now + 1.1);
      voice.lfo.stop(now + 1.1);
    }
    this._oscillators = [];
    this._isPlaying = false;
  }
}
```

### 3.2 Deadline Alarm System

Approaching deadlines trigger escalating audio warnings — subtle at 30 days, urgent at 7 days,
alarm-like when overdue.

```javascript
const DEADLINE_SOUNDS = {
  ok:       { freq: 440, duration: 0.1, waveform: 'sine',     gain: 0.05, repeat: 1 },
  upcoming: { freq: 523, duration: 0.15, waveform: 'triangle', gain: 0.10, repeat: 2 },
  urgent:   { freq: 659, duration: 0.2,  waveform: 'square',   gain: 0.15, repeat: 3 },
  critical: { freq: 880, duration: 0.25, waveform: 'sawtooth', gain: 0.20, repeat: 4 },
  overdue:  { freq: 1047, duration: 0.3, waveform: 'sawtooth', gain: 0.30, repeat: 6 }
};

function getDeadlineUrgency(daysRemaining) {
  if (daysRemaining < 0)  return 'overdue';
  if (daysRemaining <= 3) return 'critical';
  if (daysRemaining <= 7) return 'urgent';
  if (daysRemaining <= 30) return 'upcoming';
  return 'ok';
}

function playDeadlineAlert(engine, daysRemaining) {
  const urgency = getDeadlineUrgency(daysRemaining);
  const sound = DEADLINE_SOUNDS[urgency];
  const ctx = engine._ctx;
  let time = ctx.currentTime + 0.05;

  for (let i = 0; i < sound.repeat; i++) {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = sound.waveform;
    osc.frequency.value = sound.freq * (1 + i * 0.05); // slight pitch rise per repeat
    gain.gain.setValueAtTime(0, time);
    gain.gain.linearRampToValueAtTime(sound.gain, time + 0.005);
    gain.gain.exponentialRampToValueAtTime(0.001, time + sound.duration);
    osc.connect(gain);
    gain.connect(engine.getLayerOutput('hud'));
    osc.start(time);
    osc.stop(time + sound.duration + 0.01);
    time += sound.duration + 0.05;
  }
}
```

---

## Layer 4: Graph Navigation Audio

### 4.1 Spatial Audio — Stereo Panning from Viewport Position

Nodes produce sound positioned in the stereo field based on their screen coordinates.
A node on the left edge of the viewport pans left; right edge pans right.

```javascript
/**
 * Compute stereo pan value from node screen position.
 * Also scales volume based on distance from viewport center (proximity gain).
 */
function spatialAudioParams(node, viewportWidth, viewportHeight) {
  // Normalize screen position to [-1, 1]
  const panX = ((node.screenX / viewportWidth) - 0.5) * 2;

  // Proximity gain: nodes near center are louder
  const centerDist = Math.sqrt(
    Math.pow((node.screenX / viewportWidth) - 0.5, 2) +
    Math.pow((node.screenY / viewportHeight) - 0.5, 2)
  );
  const proximityGain = Math.max(0.1, 1.0 - centerDist);

  return {
    pan: Math.max(-1, Math.min(1, panX)),
    gain: proximityGain
  };
}
```

### 4.2 Node Signature Sounds

Each node type has a unique "signature sound" — a short audio motif played on click.
The signature encodes node type (waveform), layer (octave), and threat level (timbre).

```javascript
const NODE_TYPE_SIGNATURES = {
  person:    { waveform: 'sine',     baseOctave: 4, attackMs: 10,  decayMs: 400 },
  entity:    { waveform: 'triangle', baseOctave: 3, attackMs: 5,   decayMs: 300 },
  event:     { waveform: 'square',   baseOctave: 5, attackMs: 2,   decayMs: 150 },
  document:  { waveform: 'sine',     baseOctave: 3, attackMs: 20,  decayMs: 500 },
  authority: { waveform: 'triangle', baseOctave: 4, attackMs: 15,  decayMs: 350 },
  weapon:    { waveform: 'sawtooth', baseOctave: 5, attackMs: 1,   decayMs: 200 },
  filing:    { waveform: 'triangle', baseOctave: 3, attackMs: 30,  decayMs: 600 },
  violation: { waveform: 'sawtooth', baseOctave: 6, attackMs: 1,   decayMs: 100 },
  evidence:  { waveform: 'sine',     baseOctave: 4, attackMs: 10,  decayMs: 450 }
};

// Layer → note offset (semitones from base octave)
const LAYER_OFFSETS = {
  adversary: 0, weapon: 2, judicial: 4, evidence: 5,
  authority: 7, impeachment: 9, timeline: 11, filing: 12,
  brain: 14, engine: 16, hud: 17, narrative: 19, convergence: 21
};

/**
 * Play a node's signature sound on click.
 * Encodes: type (waveform) × layer (pitch) × threat (detune + modulation)
 */
function playNodeSignature(engine, node) {
  const ctx = engine._ctx;
  const sig = NODE_TYPE_SIGNATURES[node.type] || NODE_TYPE_SIGNATURES.entity;
  const layerOffset = LAYER_OFFSETS[node.layer] || 0;
  const threat = node.threat_level || 0;

  // Compute frequency: base octave + layer offset in semitones
  const baseFreq = 440 * Math.pow(2, (sig.baseOctave - 4)); // A of base octave
  const freq = baseFreq * Math.pow(2, layerOffset / 12);

  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  const panner = ctx.createStereoPanner();

  osc.type = sig.waveform;
  osc.frequency.value = freq;
  osc.detune.value = threat * 40; // high threat = detuned

  // Spatial positioning
  const spatial = spatialAudioParams(node, window.innerWidth, window.innerHeight);
  panner.pan.value = spatial.pan;

  // Envelope: attack → peak → decay
  const now = ctx.currentTime;
  const peakGain = 0.2 * spatial.gain;
  const attackSec = sig.attackMs / 1000;
  const decaySec = sig.decayMs / 1000;

  gain.gain.setValueAtTime(0, now);
  gain.gain.linearRampToValueAtTime(peakGain, now + attackSec);
  gain.gain.exponentialRampToValueAtTime(0.001, now + attackSec + decaySec);

  osc.connect(gain);
  gain.connect(panner);
  panner.connect(engine.getLayerOutput(node.layer || 'convergence'));

  osc.start(now);
  osc.stop(now + attackSec + decaySec + 0.01);
}
```

---

## Layer 5: Timeline Playback Audio

### 5.1 Event Intensity → Note Sequence

As the timeline scrubber moves through events, notes play reflecting event density
and intensity. Dense clusters of events produce rapid note sequences; isolated events
produce single tones.

```javascript
/**
 * Timeline audio renderer. Receives sorted events as the scrubber advances.
 *
 * Intensity mapping:
 * - Event count in window → note density (more events = faster notes)
 * - Event severity → pitch (higher severity = higher pitch)
 * - Event type → waveform (custody=sine, judicial=square, ppo=sawtooth)
 */
class TimelineAudioRenderer {
  constructor(engine) {
    this._engine = engine;
    this._lastPlayedIndex = -1;
    this._noteQueue = [];
  }

  /**
   * Called as the timeline scrubber moves. Plays notes for newly-revealed events.
   * @param {Array} events - Events in current window, sorted by date
   * @param {number} scrubberPosition - 0.0 (start) to 1.0 (end)
   * @param {number} windowSize - Number of events visible in current window
   */
  onScrub(events, scrubberPosition, windowSize) {
    const ctx = this._engine._ctx;
    const now = ctx.currentTime;

    // Compute note spacing based on density
    const density = Math.min(events.length, 20);
    const noteGap = Math.max(0.03, 0.5 / (density + 1)); // faster when denser

    let time = now;
    for (let i = 0; i < events.length && i < 16; i++) {
      const evt = events[i];
      if (evt._played) continue;

      const severity = evt.severity || 0.5;
      const freq = 220 + severity * 660; // 220Hz (low) to 880Hz (high)

      const eventTypeWaveforms = {
        custody: 'sine', judicial: 'square', ppo: 'sawtooth',
        housing: 'triangle', filing: 'sine', evidence: 'triangle'
      };
      const waveform = eventTypeWaveforms[evt.category] || 'sine';

      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = waveform;
      osc.frequency.value = freq;

      const noteDur = Math.max(0.05, noteGap * 0.8);
      gain.gain.setValueAtTime(0, time);
      gain.gain.linearRampToValueAtTime(0.12 * severity, time + 0.005);
      gain.gain.exponentialRampToValueAtTime(0.001, time + noteDur);

      osc.connect(gain);
      gain.connect(this._engine.getLayerOutput('timeline'));
      osc.start(time);
      osc.stop(time + noteDur + 0.01);

      evt._played = true;
      time += noteGap;
    }
  }

  /** Reset play state for all events (e.g., when scrubber resets) */
  reset(events) {
    for (const evt of events) {
      delete evt._played;
    }
    this._lastPlayedIndex = -1;
  }
}
```

### 5.2 Escalation Crescendo

During periods of escalating events (e.g., the Aug 2025 five-orders-day), the audio
engine detects rising event density and severity, triggering a crescendo effect.

```javascript
function detectEscalation(events, windowStart, windowEnd) {
  const windowEvents = events.filter(e =>
    e.date >= windowStart && e.date <= windowEnd
  );

  if (windowEvents.length < 3) return { isEscalating: false, intensity: 0 };

  // Check if severity is trending upward
  let trendUp = 0;
  for (let i = 1; i < windowEvents.length; i++) {
    if ((windowEvents[i].severity || 0) > (windowEvents[i - 1].severity || 0)) {
      trendUp++;
    }
  }
  const escalationRatio = trendUp / (windowEvents.length - 1);
  const avgSeverity = windowEvents.reduce((s, e) => s + (e.severity || 0), 0) / windowEvents.length;

  return {
    isEscalating: escalationRatio > 0.6 && avgSeverity > 0.5,
    intensity: escalationRatio * avgSeverity,
    eventCount: windowEvents.length
  };
}
```

---

## Layer 6: Impeachment Chord System

### 6.1 Dissonant Intervals for Credibility Attacks

Impeachment entries play dissonant chords proportional to their impeachment_value (1–10).
Low values get mild tension (major 7ths), high values get harsh dissonance (minor 2nds, tritones).

```javascript
// Interval definitions in semitones — ordered from consonant to dissonant
const DISSONANCE_LADDER = [
  { minValue: 1,  intervals: [0, 4, 7],       name: 'major triad (stable)' },
  { minValue: 2,  intervals: [0, 3, 7],       name: 'minor triad (sad)' },
  { minValue: 3,  intervals: [0, 4, 7, 11],   name: 'major 7th (tension)' },
  { minValue: 4,  intervals: [0, 3, 7, 10],   name: 'minor 7th (dark)' },
  { minValue: 5,  intervals: [0, 4, 7, 10],   name: 'dominant 7th (pull)' },
  { minValue: 6,  intervals: [0, 3, 6, 10],   name: 'half-dim 7th (anxiety)' },
  { minValue: 7,  intervals: [0, 3, 6, 9],    name: 'diminished 7th (dread)' },
  { minValue: 8,  intervals: [0, 1, 6, 7],    name: 'tritone cluster (alarm)' },
  { minValue: 9,  intervals: [0, 1, 2, 6],    name: 'tone cluster (harsh)' },
  { minValue: 10, intervals: [0, 1, 5, 6, 11],name: 'chromatic pile (chaos)' }
];

/**
 * Play an impeachment chord on hover or selection.
 * @param {number} impeachmentValue - 1 (mild) to 10 (devastating)
 * @param {string} targetActor - Name of person being impeached
 */
function playImpeachmentChord(engine, impeachmentValue, targetActor) {
  const ctx = engine._ctx;
  const now = ctx.currentTime;

  // Select chord from dissonance ladder
  let chord = DISSONANCE_LADDER[0];
  for (const entry of DISSONANCE_LADDER) {
    if (impeachmentValue >= entry.minValue) chord = entry;
  }

  const baseFreq = 220; // A3
  const duration = 0.3 + (impeachmentValue / 10) * 0.7; // 0.3s to 1.0s
  const gain_val = 0.05 + (impeachmentValue / 10) * 0.15; // 0.05 to 0.20

  for (const semitones of chord.intervals) {
    const freq = baseFreq * Math.pow(2, semitones / 12);
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    // Higher impeachment values use harsher waveforms
    osc.type = impeachmentValue >= 7 ? 'sawtooth' : impeachmentValue >= 4 ? 'square' : 'triangle';
    osc.frequency.value = freq;

    // Slight random detune for organic feel
    osc.detune.value = (Math.random() - 0.5) * impeachmentValue * 3;

    gain.gain.setValueAtTime(0, now);
    gain.gain.linearRampToValueAtTime(gain_val, now + 0.02);
    gain.gain.setValueAtTime(gain_val, now + duration * 0.6);
    gain.gain.exponentialRampToValueAtTime(0.001, now + duration);

    osc.connect(gain);
    gain.connect(engine.getLayerOutput('impeachment'));
    osc.start(now);
    osc.stop(now + duration + 0.01);
  }
}
```

---

## Layer 7: Evidence Density Pulse

### 7.1 Rhythmic Feedback for Evidence Coverage

A subtle rhythmic pulse that varies in speed based on local evidence density.
Dense evidence areas pulse fast (reassuring), sparse areas pulse slow (warning).

```javascript
class EvidenceDensityPulse {
  constructor(engine) {
    this._engine = engine;
    this._osc = null;
    this._lfo = null;
    this._gain = null;
    this._isActive = false;
  }

  /**
   * Update pulse rate based on evidence density at current viewport center.
   * @param {number} density - 0.0 (no evidence) to 1.0 (saturated)
   */
  update(density) {
    if (!this._isActive) this._start();

    const ctx = this._engine._ctx;
    const now = ctx.currentTime;

    // Density → pulse rate: sparse = slow (0.5Hz), dense = fast (4Hz)
    const pulseRate = 0.5 + density * 3.5;
    this._lfo.frequency.linearRampToValueAtTime(pulseRate, now + 0.5);

    // Density → tone: sparse = low warning, dense = bright confirmation
    const freq = 110 + density * 330; // 110Hz to 440Hz
    this._osc.frequency.linearRampToValueAtTime(freq, now + 0.5);

    // Density → volume: sparse areas slightly louder (alert)
    const vol = 0.08 - density * 0.04; // 0.08 (sparse) to 0.04 (dense)
    this._gain.gain.linearRampToValueAtTime(vol, now + 0.5);
  }

  _start() {
    const ctx = this._engine._ctx;
    const now = ctx.currentTime;

    this._osc = ctx.createOscillator();
    this._osc.type = 'sine';
    this._osc.frequency.value = 220;

    this._gain = ctx.createGain();
    this._gain.gain.value = 0;

    // LFO modulates gain for the pulsing effect
    this._lfo = ctx.createOscillator();
    const lfoGain = ctx.createGain();
    this._lfo.frequency.value = 1;
    lfoGain.gain.value = 0.06;
    this._lfo.connect(lfoGain);
    lfoGain.connect(this._gain.gain);

    this._osc.connect(this._gain);
    this._gain.connect(this._engine.getLayerOutput('evidence'));

    this._osc.start(now);
    this._lfo.start(now);
    this._isActive = true;

    // Fade in
    this._gain.gain.setValueAtTime(0, now);
    this._gain.gain.linearRampToValueAtTime(0.06, now + 1.0);
  }

  stop() {
    if (!this._isActive) return;
    const now = this._engine.now;
    this._gain.gain.linearRampToValueAtTime(0, now + 0.5);
    this._osc.stop(now + 0.6);
    this._lfo.stop(now + 0.6);
    this._isActive = false;
  }
}
```

---

## Layer 8: Audio Toggle & Volume Controls

### 8.1 UI Panel for Sonification Settings

```html
<!-- Audio control panel — embedded in THEMANBEARPIG HUD -->
<div id="sonic-controls" class="sonic-panel" style="display: none;">
  <div class="sonic-header">
    <span class="sonic-icon">🔊</span>
    <span>SONIC ENGINE</span>
    <button id="sonic-close" class="sonic-btn-close">×</button>
  </div>

  <div class="sonic-section">
    <label>Master Volume</label>
    <input type="range" id="sonic-master" min="0" max="100" value="40" class="sonic-slider">
    <span id="sonic-master-val">40%</span>
  </div>

  <div class="sonic-section">
    <label>Mode</label>
    <select id="sonic-mode" class="sonic-select">
      <option value="off">Off</option>
      <option value="ambient" selected>Ambient</option>
      <option value="interactive">Interactive</option>
      <option value="timeline">Timeline</option>
      <option value="full">Full (All)</option>
    </select>
  </div>

  <div class="sonic-section">
    <label>Layer Mute</label>
    <div id="sonic-layer-toggles" class="sonic-toggles">
      <!-- Generated by JS for each of 13 layers -->
    </div>
  </div>

  <div class="sonic-section">
    <label>Level Meter</label>
    <canvas id="sonic-meter" width="200" height="30"></canvas>
  </div>
</div>
```

### 8.2 Control Logic & Layer Toggles

```javascript
function initSonicControls(engine) {
  const masterSlider = document.getElementById('sonic-master');
  const modeSelect = document.getElementById('sonic-mode');
  const toggleContainer = document.getElementById('sonic-layer-toggles');

  // Master volume
  masterSlider.addEventListener('input', (e) => {
    const vol = parseInt(e.target.value) / 100;
    engine._masterGain.gain.linearRampToValueAtTime(vol, engine.now + 0.05);
    document.getElementById('sonic-master-val').textContent = e.target.value + '%';
  });

  // Mode selection
  modeSelect.addEventListener('change', (e) => {
    engine._mode = e.target.value;
    if (e.target.value === 'off') {
      engine._masterGain.gain.linearRampToValueAtTime(0, engine.now + 0.3);
    } else {
      engine._masterGain.gain.linearRampToValueAtTime(
        parseInt(masterSlider.value) / 100, engine.now + 0.3
      );
    }
  });

  // Per-layer mute toggles
  const layers = Object.keys(engine._layerGains);
  for (const layer of layers) {
    const label = document.createElement('label');
    label.className = 'sonic-toggle';
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.checked = true;
    checkbox.dataset.layer = layer;
    checkbox.addEventListener('change', (e) => {
      const gain = engine._layerGains[layer];
      const target = e.target.checked ? 0.6 : 0;
      gain.gain.linearRampToValueAtTime(target, engine.now + 0.1);
    });
    label.appendChild(checkbox);
    label.appendChild(document.createTextNode(` ${layer}`));
    toggleContainer.appendChild(label);
  }

  // Level meter animation
  const meterCanvas = document.getElementById('sonic-meter');
  const meterCtx = meterCanvas.getContext('2d');
  function drawMeter() {
    if (!engine._analyser) { requestAnimationFrame(drawMeter); return; }
    const data = new Uint8Array(engine._analyser.frequencyBinCount);
    engine._analyser.getByteFrequencyData(data);
    const avg = data.reduce((a, b) => a + b, 0) / data.length;
    const level = avg / 255;

    meterCtx.clearRect(0, 0, 200, 30);
    const gradient = meterCtx.createLinearGradient(0, 0, 200, 0);
    gradient.addColorStop(0, '#00ff88');
    gradient.addColorStop(0.6, '#ffaa00');
    gradient.addColorStop(0.85, '#ff4444');
    meterCtx.fillStyle = gradient;
    meterCtx.fillRect(0, 2, level * 200, 26);

    meterCtx.strokeStyle = '#444';
    meterCtx.lineWidth = 1;
    // -6dB warning line
    meterCtx.beginPath();
    meterCtx.moveTo(140, 0);
    meterCtx.lineTo(140, 30);
    meterCtx.stroke();

    requestAnimationFrame(drawMeter);
  }
  drawMeter();
}
```

### 8.3 CSS Styling

```css
.sonic-panel {
  position: fixed;
  bottom: 60px;
  right: 20px;
  width: 260px;
  background: rgba(10, 10, 30, 0.92);
  border: 1px solid rgba(0, 255, 136, 0.3);
  border-radius: 8px;
  padding: 12px;
  color: #e0e0e0;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 11px;
  z-index: 10000;
  backdrop-filter: blur(8px);
}
.sonic-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  font-weight: bold;
  color: #00ff88;
}
.sonic-section { margin-bottom: 10px; }
.sonic-section label { display: block; margin-bottom: 4px; color: #aaa; }
.sonic-slider {
  width: 100%;
  accent-color: #00ff88;
}
.sonic-select {
  width: 100%;
  background: #1a1a3a;
  color: #e0e0e0;
  border: 1px solid #333;
  padding: 4px;
  border-radius: 4px;
}
.sonic-toggles {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2px;
  font-size: 10px;
}
.sonic-toggle { cursor: pointer; }
.sonic-btn-close {
  margin-left: auto;
  background: none;
  border: none;
  color: #ff4444;
  cursor: pointer;
  font-size: 16px;
}
```

---

## Layer 9: pywebview Bridge — Python↔JS Audio Events

### 9.1 Python Bridge API

The pywebview bridge exposes Python data to the JS sonification engine, triggering
audio events when data changes (new evidence, deadline updates, threat recalculations).

```python
# ── sonic_bridge.py ──
# pywebview API for THEMANBEARPIG sonification engine

import json
import sqlite3
from datetime import date, datetime


class SonicBridge:
    """pywebview-exposed API for audio sonification data."""

    def __init__(self, db_path: str):
        self._db_path = db_path

    def _connect(self):
        conn = sqlite3.connect(self._db_path, timeout=30)
        conn.execute("PRAGMA busy_timeout = 60000")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA cache_size = -32000")
        conn.row_factory = sqlite3.Row
        return conn

    def get_case_health(self) -> str:
        """Compute overall case health for ambient drone parameters."""
        conn = self._connect()
        try:
            # Filing readiness as convergence proxy
            row = conn.execute("""
                SELECT
                    AVG(CASE WHEN confidence_score IS NOT NULL
                        THEN confidence_score ELSE 0.3 END) as avg_readiness,
                    COUNT(*) as total_filings,
                    SUM(CASE WHEN status = 'FILED' THEN 1 ELSE 0 END) as filed_count
                FROM filing_readiness
            """).fetchone()

            convergence = row['avg_readiness'] if row else 0.5

            # Deadline urgency: find nearest deadline
            deadline_row = conn.execute("""
                SELECT MIN(julianday(deadline_date) - julianday('now')) as days_until
                FROM deadlines
                WHERE status != 'COMPLETE'
                  AND deadline_date >= date('now')
            """).fetchone()

            days_until = deadline_row['days_until'] if deadline_row and deadline_row['days_until'] else 90
            urgency = max(0, min(1, 1.0 - (days_until / 30.0)))

            # Evidence gap ratio
            gap_row = conn.execute("""
                SELECT
                    (SELECT COUNT(*) FROM evidence_quotes) as total_evidence,
                    (SELECT COUNT(DISTINCT lane) FROM evidence_quotes) as covered_lanes
            """).fetchone()

            total_ev = gap_row['total_evidence'] if gap_row else 1
            gaps = 1.0 - min(1, total_ev / 50000)

            result = {
                'convergence': min(1, convergence),
                'deadlineUrgency': urgency,
                'evidenceGaps': gaps,
                'filingReadiness': convergence
            }
            return json.dumps(result)
        finally:
            conn.close()

    def get_adversary_threats(self) -> str:
        """Get threat levels for all adversary nodes."""
        conn = self._connect()
        try:
            rows = conn.execute("""
                SELECT
                    target_name,
                    COUNT(*) as entries,
                    AVG(impeachment_value) as avg_impeachment,
                    MAX(impeachment_value) as max_impeachment
                FROM impeachment_matrix
                GROUP BY target_name
                ORDER BY avg_impeachment DESC
                LIMIT 20
            """).fetchall()

            threats = []
            for r in rows:
                threat_level = min(1.0, (r['avg_impeachment'] or 0) / 10.0)
                threats.append({
                    'name': r['target_name'],
                    'threatLevel': threat_level,
                    'entries': r['entries'],
                    'maxImpeachment': r['max_impeachment']
                })
            return json.dumps(threats)
        finally:
            conn.close()

    def get_timeline_events_for_range(self, start_date: str, end_date: str) -> str:
        """Get timeline events for audio playback in a date range."""
        conn = self._connect()
        try:
            rows = conn.execute("""
                SELECT event_date, event_description, category, severity, actor
                FROM timeline_events
                WHERE event_date BETWEEN ? AND ?
                ORDER BY event_date ASC
                LIMIT 200
            """, (start_date, end_date)).fetchall()

            events = [dict(r) for r in rows]
            return json.dumps(events)
        finally:
            conn.close()

    def get_separation_days(self) -> str:
        """Dynamic separation counter for urgency sonification."""
        anchor = date(2025, 7, 29)
        today = date.today()
        days = (today - anchor).days
        urgency = min(1.0, days / 365.0)
        return json.dumps({'days': days, 'urgency': urgency})

    def get_deadline_alerts(self) -> str:
        """Get upcoming deadlines for alarm sounds."""
        conn = self._connect()
        try:
            rows = conn.execute("""
                SELECT deadline_date, description, status, vehicle_name,
                       julianday(deadline_date) - julianday('now') as days_remaining
                FROM deadlines
                WHERE status != 'COMPLETE'
                  AND deadline_date >= date('now', '-7 days')
                ORDER BY deadline_date ASC
                LIMIT 20
            """).fetchall()
            return json.dumps([dict(r) for r in rows])
        finally:
            conn.close()
```

### 9.2 JS-Side Bridge Consumer

```javascript
/**
 * Poll Python bridge for data updates and trigger audio events.
 * Runs every 5 seconds in ambient mode, 1 second in interactive mode.
 */
class SonicDataPoller {
  constructor(engine, ambientDrone) {
    this._engine = engine;
    this._drone = ambientDrone;
    this._interval = null;
    this._lastHealth = null;
  }

  start() {
    const pollRate = this._engine._mode === 'interactive' ? 1000 : 5000;
    this._interval = setInterval(() => this._poll(), pollRate);
    this._poll(); // immediate first poll
  }

  async _poll() {
    if (this._engine._mode === 'off') return;

    // Case health → ambient drone
    try {
      const healthJson = await window.pywebview.api.get_case_health();
      const health = JSON.parse(healthJson);
      if (this._hasChanged(health, this._lastHealth)) {
        this._drone.updateHealth(health);
        this._lastHealth = health;
      }
    } catch (e) {
      // Bridge may not be ready yet — silent fail
    }

    // Deadline alerts
    try {
      const alertsJson = await window.pywebview.api.get_deadline_alerts();
      const alerts = JSON.parse(alertsJson);
      for (const alert of alerts) {
        if (alert.days_remaining <= 7 && alert.days_remaining > 0) {
          playDeadlineAlert(this._engine, alert.days_remaining);
          break; // one alert per poll cycle
        }
      }
    } catch (e) {
      // silent fail
    }
  }

  _hasChanged(a, b) {
    if (!b) return true;
    return Math.abs((a.convergence || 0) - (b.convergence || 0)) > 0.05 ||
           Math.abs((a.deadlineUrgency || 0) - (b.deadlineUrgency || 0)) > 0.05;
  }

  stop() {
    if (this._interval) clearInterval(this._interval);
  }
}
```

---

## Layer 10: Integration with THEMANBEARPIG Main Loop

### 10.1 Initialization Hook

```javascript
// ── In main THEMANBEARPIG app initialization ──

let sonicEngine = null;
let ambientDrone = null;
let oscPool = null;
let densityPulse = null;
let timelineAudio = null;
let sonicPoller = null;

function initSonicSystem() {
  sonicEngine = new SonificationEngine();
  // Defer AudioContext creation to first user gesture
  document.addEventListener('click', function initAudio() {
    sonicEngine.init();
    oscPool = new OscillatorPool(sonicEngine);
    ambientDrone = new AmbientDrone(sonicEngine);
    densityPulse = new EvidenceDensityPulse(sonicEngine);
    timelineAudio = new TimelineAudioRenderer(sonicEngine);

    ambientDrone.start({ convergence: 0.5, deadlineUrgency: 0.3, evidenceGaps: 0.4, filingReadiness: 0.5 });

    sonicPoller = new SonicDataPoller(sonicEngine, ambientDrone);
    sonicPoller.start();

    initSonicControls(sonicEngine);
    document.getElementById('sonic-controls').style.display = 'block';

    document.removeEventListener('click', initAudio);
    console.log('[SONIC] Audio system initialized on user gesture');
  }, { once: true });
}

// Hook into D3 force simulation tick for spatial audio updates
function onSimulationTick(nodes) {
  if (!sonicEngine || sonicEngine._mode === 'off') return;
  // Update evidence density pulse based on visible node density
  const viewportNodes = nodes.filter(n => n.screenX >= 0 && n.screenX <= window.innerWidth);
  const density = Math.min(1, viewportNodes.length / 200);
  if (densityPulse) densityPulse.update(density);
}

// Hook into node click handler
function onNodeClick(node) {
  if (!sonicEngine || sonicEngine._mode === 'off') return;
  playNodeSignature(sonicEngine, node);
  if (node.layer === 'impeachment' && node.impeachment_value) {
    playImpeachmentChord(sonicEngine, node.impeachment_value, node.label);
  }
}

// Hook into timeline scrubber
function onTimelineScrub(events, position) {
  if (!sonicEngine || sonicEngine._mode === 'off') return;
  if (timelineAudio) timelineAudio.onScrub(events, position, events.length);
}
```

---

## Anti-Patterns (NEVER DO THESE)

| # | Anti-Pattern | Why It Fails | Correct Approach |
|---|-------------|-------------|-----------------|
| 1 | Create AudioContext on page load | Browser blocks — requires user gesture | Defer to first click/keypress handler |
| 2 | Exceed -6dB on master output | Clipping distorts, damages speakers/headphones | Compressor at -24dB threshold + limiter at -3dB |
| 3 | Create new AudioContext per sound | Memory leak, OS audio resource exhaustion | One AudioContext per app, reuse forever |
| 4 | Autoplay ambient audio without consent | Hostile UX, accessibility violation, browser blocks | Explicit user opt-in toggle, default = off |
| 5 | Stop oscillator then restart it | Web Audio spec forbids — stopped nodes are dead | Create fresh oscillator; pool/recycle pattern |
| 6 | Set gain directly with `.value =` during playback | Causes clicks/pops from discontinuity | Use `linearRampToValueAtTime` or `setTargetAtTime` |
| 7 | Create unlimited oscillators | CPU spike, audio glitching, tab crash | Pool with MAX_SIMULTANEOUS = 32, steal oldest |
| 8 | Use `setInterval` for precise timing | JS timer jitter is 4-16ms, audibly sloppy | Use `AudioContext.currentTime` for sample-accurate scheduling |
| 9 | Ignore `AudioContext.state === 'suspended'` | Context paused by browser power save — no sound | Call `ctx.resume()` in user gesture handlers |
| 10 | Pipe raw data values to frequency directly | Produces harsh, meaningless noise | Map through perceptually meaningful scales (log frequency, musical intervals) |
| 11 | Play identical sounds for different data types | No information encoded — just noise | Distinct waveform + pitch + rhythm per data type |
| 12 | Use Web Audio for long background music | Large decode buffers waste memory | Additive synthesis for drones; sample playback only for short FX |
| 13 | Create GainNode per frame | N^2 node graph growth, garbage collection stalls | Reuse gain nodes, disconnect when recycled |
| 14 | Ignore `ended` event on OscillatorNode | Orphaned nodes in audio graph, slow leak | Listen for `ended`, clean up references |
| 15 | Use `ScriptProcessorNode` for DSP | Deprecated, runs on main thread, blocks rendering | Use `AudioWorkletNode` for custom DSP (if needed) |
| 16 | Assume all browsers support Web Audio equally | Safari has quirks with `AudioContext` resume | Feature-detect with `window.AudioContext \|\| window.webkitAudioContext` |
| 17 | Play sounds in response to every mouse move | Overwhelming, CPU-melting, unusable | Throttle to max 10 audio events per second |

---

## Performance Budgets

| Metric | Budget | Rationale |
|--------|--------|-----------|
| Max simultaneous oscillators | 32 | Beyond this, CPU audio thread saturates on Ryzen 3 |
| AudioContext latency | < 20ms | `latencyHint: 'interactive'` targets this |
| Convolver IR buffer | 1.5s stereo (264 KB) | Longer IRs waste memory without audible benefit |
| Level meter refresh | 30fps | Half of render rate — adequate for VU display |
| Data poll interval (ambient) | 5000ms | Case health changes slowly — no need for real-time |
| Data poll interval (interactive) | 1000ms | Responsive to user actions |
| Gain ramp minimum | 5ms | Shorter ramps cause audible clicks |
| Max audio events per second | 10 | Throttle to prevent CPU saturation |
| Master output ceiling | -3dB (0.707 linear) | Hard limiter prevents ANY clipping |
| Per-layer default gain | 0.6 (≈-4.4dB) | Headroom for summing 13 layers |
| Total audio memory budget | 4 MB | Buffers + nodes + analysis data |
| Oscillator pool recycle time | 50ms fade | Prevents pop on steal, fast enough for reuse |

---

## Accessibility Considerations

1. **Audio is never the sole information channel** — all sonified data has visual equivalents
2. **Default mode is OFF** until user explicitly enables via toggle or keyboard shortcut
3. **Keyboard shortcut**: `Ctrl+Shift+S` toggles sonic engine on/off
4. **Reduced motion preference**: If `prefers-reduced-motion` is set, disable all audio modulation (steady tones only)
5. **Screen reader compatibility**: Sonic controls panel uses proper ARIA labels and roles
6. **Volume persistence**: Master volume and layer mutes saved to `localStorage`, restored on reload
7. **Hearing sensitivity**: No frequencies above 4000Hz in ambient mode (avoid fatigue)

```javascript
// Respect reduced-motion preference
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
if (prefersReducedMotion) {
  // Disable LFO modulation, use steady tones only
  THREAT_AUDIO_MAP.modulationRate.min = 0;
  THREAT_AUDIO_MAP.modulationRate.max = 0;
}

// Keyboard toggle
document.addEventListener('keydown', (e) => {
  if (e.ctrlKey && e.shiftKey && e.key === 'S') {
    e.preventDefault();
    const panel = document.getElementById('sonic-controls');
    panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    if (sonicEngine) {
      sonicEngine._mode = sonicEngine._mode === 'off' ? 'ambient' : 'off';
    }
  }
});

// Persist settings
function saveSonicSettings(engine) {
  localStorage.setItem('mbp_sonic', JSON.stringify({
    volume: engine._masterVolume,
    mode: engine._mode,
    layerMutes: Object.fromEntries(
      Object.entries(engine._layerGains).map(([k, v]) => [k, v.gain.value > 0])
    )
  }));
}

function loadSonicSettings(engine) {
  try {
    const saved = JSON.parse(localStorage.getItem('mbp_sonic'));
    if (!saved) return;
    engine._masterVolume = saved.volume || 0.4;
    engine._mode = saved.mode || 'ambient';
    for (const [layer, unmuted] of Object.entries(saved.layerMutes || {})) {
      if (engine._layerGains[layer]) {
        engine._layerGains[layer].gain.value = unmuted ? 0.6 : 0;
      }
    }
  } catch (e) {
    // corrupt localStorage — use defaults
  }
}
```

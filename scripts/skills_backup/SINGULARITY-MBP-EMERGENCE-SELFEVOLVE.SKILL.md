---
name: SINGULARITY-MBP-EMERGENCE-SELFEVOLVE
description: "Self-improving graph layout, configuration learning, plugin architecture, and build versioning for THEMANBEARPIG. Auto-optimizes force simulation parameters from user interaction, learns preferred configurations, manages plugin lifecycle, and tracks build versions with semantic versioning. localStorage persistence for cross-session learning."
version: "2.0.0"
tier: "TIER-5/EMERGENCE"
domain: "Self-evolution — auto-layout optimization, config learning, plugin management, build versioning"
triggers:
  - self-evolve
  - auto-layout
  - config learn
  - plugin
  - build version
  - optimization
  - self-improvement
  - adaptive layout
---

# SINGULARITY-MBP-EMERGENCE-SELFEVOLVE v2.0

> **The graph that learns from you and improves itself.**

## Layer 1: Adaptive Force Simulation

### 1.1 Parameter Auto-Tuning from User Interaction

```javascript
class AdaptiveForceOptimizer {
  constructor() {
    this.interactions = JSON.parse(localStorage.getItem('mbp_interactions') || '[]');
    this.bestConfig = JSON.parse(localStorage.getItem('mbp_best_config') || 'null');
    this.configHistory = JSON.parse(localStorage.getItem('mbp_config_history') || '[]');
  }

  recordInteraction(type, params) {
    this.interactions.push({
      type, params,
      timestamp: Date.now(),
      config: this.getCurrentConfig()
    });
    if (this.interactions.length > 500) this.interactions = this.interactions.slice(-500);
    localStorage.setItem('mbp_interactions', JSON.stringify(this.interactions));
  }

  getCurrentConfig() {
    return {
      chargeStrength: window._forceCharge || -300,
      linkDistance: window._forceLinkDist || 80,
      centerStrength: window._forceCenter || 0.05,
      collisionRadius: window._forceCollision || 20,
      alphaDecay: window._forceAlphaDecay || 0.02
    };
  }

  optimize() {
    if (this.interactions.length < 20) return null;

    const recent = this.interactions.slice(-50);
    const zoomOuts = recent.filter(i => i.type === 'zoom_out').length;
    const zoomIns = recent.filter(i => i.type === 'zoom_in').length;
    const drags = recent.filter(i => i.type === 'drag').length;
    const clicks = recent.filter(i => i.type === 'click').length;

    const config = { ...this.getCurrentConfig() };

    // If user zooms out a lot → nodes are too spread → increase charge (less repulsion)
    if (zoomOuts > zoomIns * 2) {
      config.chargeStrength = Math.min(config.chargeStrength + 50, -50);
      config.linkDistance = Math.max(config.linkDistance - 10, 30);
    }
    // If user zooms in a lot → nodes too clustered → decrease charge (more repulsion)
    if (zoomIns > zoomOuts * 2) {
      config.chargeStrength = Math.max(config.chargeStrength - 50, -1000);
      config.linkDistance = Math.min(config.linkDistance + 10, 200);
    }
    // If lots of dragging → layout isn't satisfying → increase alpha decay (settle faster)
    if (drags > clicks * 3) {
      config.alphaDecay = Math.min(config.alphaDecay + 0.005, 0.1);
    }

    this.bestConfig = config;
    this.configHistory.push({ ...config, timestamp: Date.now() });
    if (this.configHistory.length > 100) this.configHistory = this.configHistory.slice(-100);

    localStorage.setItem('mbp_best_config', JSON.stringify(config));
    localStorage.setItem('mbp_config_history', JSON.stringify(this.configHistory));

    return config;
  }

  applyConfig(simulation, config) {
    if (!config) return;
    simulation.force('charge').strength(config.chargeStrength);
    simulation.force('link').distance(config.linkDistance);
    if (simulation.force('center')) {
      simulation.force('center').strength(config.centerStrength);
    }
    simulation.force('collision').radius(config.collisionRadius);
    simulation.alphaDecay(config.alphaDecay);
    simulation.alpha(0.3).restart();
  }

  getEvolutionStats() {
    return {
      totalInteractions: this.interactions.length,
      configChanges: this.configHistory.length,
      currentConfig: this.getCurrentConfig(),
      bestConfig: this.bestConfig,
      learningRate: this.interactions.length > 20 ? 'ACTIVE' : 'LEARNING'
    };
  }
}
```

## Layer 2: Configuration Learning & Presets

### 2.1 Smart Preset System

```javascript
class ConfigPresetManager {
  constructor() {
    this.presets = JSON.parse(localStorage.getItem('mbp_presets') || '{}');
    this.defaultPresets = {
      'dense_exploration': {
        chargeStrength: -500, linkDistance: 60, centerStrength: 0.08,
        collisionRadius: 15, alphaDecay: 0.015,
        description: 'Tight clusters for exploring dense regions'
      },
      'overview': {
        chargeStrength: -150, linkDistance: 120, centerStrength: 0.03,
        collisionRadius: 30, alphaDecay: 0.03,
        description: 'Spread out for full-graph overview'
      },
      'presentation': {
        chargeStrength: -300, linkDistance: 100, centerStrength: 0.05,
        collisionRadius: 25, alphaDecay: 0.02,
        description: 'Balanced layout for presentations'
      },
      'adversary_focus': {
        chargeStrength: -400, linkDistance: 70, centerStrength: 0.06,
        collisionRadius: 20, alphaDecay: 0.02,
        description: 'Adversary network analysis mode'
      }
    };
  }

  savePreset(name, config) {
    this.presets[name] = { ...config, savedAt: Date.now() };
    localStorage.setItem('mbp_presets', JSON.stringify(this.presets));
  }

  loadPreset(name) {
    return this.presets[name] || this.defaultPresets[name] || null;
  }

  listPresets() {
    return {
      ...this.defaultPresets,
      ...this.presets
    };
  }

  deletePreset(name) {
    if (this.presets[name]) {
      delete this.presets[name];
      localStorage.setItem('mbp_presets', JSON.stringify(this.presets));
    }
  }
}
```

## Layer 3: Plugin Architecture

### 3.1 Plugin Lifecycle Manager

```javascript
class PluginManager {
  constructor() {
    this.plugins = new Map();
    this.hooks = {
      'beforeRender': [], 'afterRender': [],
      'beforeForce': [], 'afterForce': [],
      'onNodeClick': [], 'onLinkClick': [],
      'onDataLoad': [], 'onLayerChange': [],
      'onClusterDetected': [], 'onConvergenceUpdate': []
    };
  }

  register(plugin) {
    if (!plugin.id || !plugin.name) throw new Error('Plugin must have id and name');
    if (this.plugins.has(plugin.id)) return false;

    this.plugins.set(plugin.id, {
      ...plugin,
      enabled: true,
      registeredAt: Date.now()
    });

    // Auto-wire hooks
    Object.keys(this.hooks).forEach(hook => {
      if (typeof plugin[hook] === 'function') {
        this.hooks[hook].push({ pluginId: plugin.id, fn: plugin[hook] });
      }
    });
    return true;
  }

  unregister(pluginId) {
    this.plugins.delete(pluginId);
    Object.keys(this.hooks).forEach(hook => {
      this.hooks[hook] = this.hooks[hook].filter(h => h.pluginId !== pluginId);
    });
  }

  emit(hookName, ...args) {
    const handlers = this.hooks[hookName] || [];
    let result = args[0];
    for (const handler of handlers) {
      const plugin = this.plugins.get(handler.pluginId);
      if (plugin?.enabled) {
        try {
          const r = handler.fn.call(plugin, result, ...args.slice(1));
          if (r !== undefined) result = r;
        } catch (e) {
          console.error(`Plugin ${handler.pluginId} error in ${hookName}:`, e);
        }
      }
    }
    return result;
  }

  toggle(pluginId, enabled) {
    const plugin = this.plugins.get(pluginId);
    if (plugin) plugin.enabled = enabled;
  }

  listPlugins() {
    return Array.from(this.plugins.values()).map(p => ({
      id: p.id, name: p.name, enabled: p.enabled,
      description: p.description || ''
    }));
  }
}
```

## Layer 4: Build Versioning & Changelog

### 4.1 Semantic Version Tracker

```javascript
class BuildVersionTracker {
  constructor() {
    this.history = JSON.parse(localStorage.getItem('mbp_versions') || '[]');
    this.current = this.history[this.history.length - 1] || null;
  }

  recordBuild(buildInfo) {
    const version = {
      version: buildInfo.version || this.bumpVersion(),
      timestamp: new Date().toISOString(),
      nodeCount: buildInfo.nodeCount || 0,
      linkCount: buildInfo.linkCount || 0,
      layerCount: buildInfo.layerCount || 0,
      clusterCount: buildInfo.clusterCount || 0,
      pluginCount: buildInfo.pluginCount || 0,
      changes: buildInfo.changes || [],
      dataHash: buildInfo.dataHash || ''
    };

    this.history.push(version);
    this.current = version;

    if (this.history.length > 200) this.history = this.history.slice(-200);
    localStorage.setItem('mbp_versions', JSON.stringify(this.history));

    return version;
  }

  bumpVersion() {
    if (!this.current) return '1.0.0';
    const parts = this.current.version.split('.').map(Number);
    parts[2]++;
    return parts.join('.');
  }

  getChangelog(lastN = 10) {
    return this.history.slice(-lastN).reverse().map(v => ({
      version: v.version,
      date: v.timestamp,
      nodes: v.nodeCount,
      links: v.linkCount,
      changes: v.changes
    }));
  }

  getDelta() {
    if (this.history.length < 2) return null;
    const prev = this.history[this.history.length - 2];
    const curr = this.current;
    return {
      nodes: curr.nodeCount - prev.nodeCount,
      links: curr.linkCount - prev.linkCount,
      layers: curr.layerCount - prev.layerCount,
      version_jump: `${prev.version} → ${curr.version}`
    };
  }
}
```

## Anti-Patterns (10 Rules)

1. NEVER auto-apply config changes without user ability to revert
2. NEVER learn from fewer than 20 interactions — insufficient signal
3. NEVER persist plugin state that contains sensitive evidence
4. NEVER allow plugins to modify evidence data — read-only access
5. NEVER delete version history — append-only
6. NEVER apply force changes during active user drag interaction
7. NEVER optimize layout while data is still loading
8. NEVER store raw evidence quotes in localStorage (PII risk)
9. NEVER let plugin errors crash the main rendering loop
10. NEVER bump major version without significant data model changes

## Performance Budgets

| Operation | Budget | Technique |
|-----------|--------|-----------|
| Config optimization | <50ms | Windowed statistics |
| Preset load/save | <10ms | localStorage direct |
| Plugin hook dispatch | <20ms | Sequential with timeout |
| Version recording | <10ms | JSON stringify |
| Delta computation | <5ms | Simple arithmetic |

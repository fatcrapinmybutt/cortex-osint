---
name: SINGULARITY-MBP-APEX-WEBGPU
description: "GPU-accelerated graph rendering for THEMANBEARPIG. WebGPU compute shaders for force simulation, instanced SDF node rendering, LOD viewport culling, 100K+ node performance at 60fps. Falls back to Canvas2D. Integrates with D3 force layout."
version: "1.0.0"
tier: "TIER-7/APEX"
domain: "GPU rendering — WebGPU shaders, instanced drawing, force computation, LOD, viewport culling"
triggers:
  - WebGPU
  - GPU rendering
  - compute shader
  - instanced rendering
  - SDF nodes
  - 100K nodes
  - force GPU
  - WebGL fallback
---

# SINGULARITY-MBP-APEX-WEBGPU — GPU-Accelerated Graph Rendering

> **Tier 7 / APEX** — The highest-performance rendering layer for THEMANBEARPIG.
> Moves force simulation AND rendering to the GPU for 100K+ node graphs at 60 fps.
> Gracefully degrades: WebGPU → WebGL2 → Canvas2D.

---

## Table of Contents

1. [WebGPU Architecture](#1-webgpu-architecture)
2. [Compute Shader Force Simulation](#2-compute-shader-force-simulation)
3. [Instanced SDF Node Rendering](#3-instanced-sdf-node-rendering)
4. [Link Rendering](#4-link-rendering)
5. [Level of Detail (LOD) System](#5-level-of-detail-lod-system)
6. [Viewport Management](#6-viewport-management)
7. [Performance Optimization](#7-performance-optimization)
8. [CPU Fallback](#8-cpu-fallback)
9. [Integration with D3 Force Layout](#9-integration-with-d3-force-layout)
10. [Anti-Patterns](#10-anti-patterns)

---

## 1. WebGPU Architecture

### 1.1 Device & Adapter Initialization

WebGPU requires explicit capability negotiation. The initialization sequence MUST
handle every failure branch — a missing adapter, an unsupported feature, or a lost
device at any point during the session.

```javascript
// ── GPU Context Manager ─────────────────────────────────────────────
class GPUContext {
  constructor(canvas) {
    this.canvas = canvas;
    this.device = null;
    this.context = null;
    this.adapter = null;
    this.format = null;
    this.tier = 'none'; // 'webgpu' | 'webgl2' | 'canvas2d' | 'none'
    this.limits = {};
    this._lost = false;
  }

  async init() {
    // ── Tier 1: WebGPU ────────────────────────────────────────────
    if (navigator.gpu) {
      try {
        this.adapter = await navigator.gpu.requestAdapter({
          powerPreference: 'high-performance',
          // Prefer discrete GPU on systems with integrated + discrete
        });

        if (!this.adapter) {
          console.warn('[GPU] No WebGPU adapter — falling back');
          return this._initWebGL2();
        }

        // Query adapter limits BEFORE requesting device
        const adapterInfo = await this.adapter.requestAdapterInfo();
        console.log(`[GPU] Adapter: ${adapterInfo.vendor} ${adapterInfo.architecture}`);

        const adapterLimits = this.adapter.limits;
        this.limits = {
          maxBufferSize: adapterLimits.maxBufferSize,
          maxStorageBufferBindingSize: adapterLimits.maxStorageBufferBindingSize,
          maxComputeWorkgroupSizeX: adapterLimits.maxComputeWorkgroupSizeX,
          maxComputeInvocationsPerWorkgroup: adapterLimits.maxComputeInvocationsPerWorkgroup,
          maxStorageBuffersPerShaderStage: adapterLimits.maxStorageBuffersPerShaderStage,
        };

        // Request device with required features
        this.device = await this.adapter.requestDevice({
          requiredFeatures: [],
          requiredLimits: {
            maxStorageBufferBindingSize: Math.min(
              256 * 1024 * 1024, // 256 MB — enough for 100K nodes
              adapterLimits.maxStorageBufferBindingSize
            ),
            maxComputeWorkgroupSizeX: 256,
          },
        });

        // Listen for device loss (GPU crash, driver update, sleep/wake)
        this.device.lost.then((info) => {
          console.error(`[GPU] Device lost: ${info.reason} — ${info.message}`);
          this._lost = true;
          this._handleDeviceLoss(info.reason);
        });

        // Configure canvas context
        this.context = this.canvas.getContext('webgpu');
        this.format = navigator.gpu.getPreferredCanvasFormat();
        this.context.configure({
          device: this.device,
          format: this.format,
          alphaMode: 'premultiplied',
        });

        this.tier = 'webgpu';
        console.log('[GPU] WebGPU initialized successfully');
        return true;

      } catch (err) {
        console.error('[GPU] WebGPU init failed:', err);
        return this._initWebGL2();
      }
    }
    return this._initWebGL2();
  }

  // ── Tier 2: WebGL2 Fallback ───────────────────────────────────
  _initWebGL2() {
    const gl = this.canvas.getContext('webgl2', {
      antialias: true,
      alpha: true,
      premultipliedAlpha: true,
      powerPreference: 'high-performance',
    });
    if (gl) {
      this.context = gl;
      this.tier = 'webgl2';
      console.log('[GPU] WebGL2 fallback active');
      return true;
    }
    return this._initCanvas2D();
  }

  // ── Tier 3: Canvas2D Fallback ─────────────────────────────────
  _initCanvas2D() {
    this.context = this.canvas.getContext('2d');
    if (this.context) {
      this.tier = 'canvas2d';
      console.log('[GPU] Canvas2D fallback active — reduced node limit');
      return true;
    }
    this.tier = 'none';
    console.error('[GPU] No rendering context available');
    return false;
  }

  // ── Device Loss Recovery ──────────────────────────────────────
  async _handleDeviceLoss(reason) {
    if (reason === 'destroyed') return; // Intentional — do not recover

    console.log('[GPU] Attempting device recovery...');
    // Re-init after a short delay (driver may need time)
    await new Promise(r => setTimeout(r, 1000));

    this.device = null;
    this.context = null;
    const ok = await this.init();
    if (ok && this.tier === 'webgpu') {
      console.log('[GPU] Device recovered — rebuilding pipelines');
      this.onDeviceRecovered?.();
    }
  }

  destroy() {
    if (this.device) {
      this.device.destroy();
      this.device = null;
    }
  }
}
```

### 1.2 GPU Memory Management

All GPU buffers are pre-allocated at startup and reused every frame. The node buffer
stores position (x, y), velocity (vx, vy), mass, charge, size, color, shape, and
flags — packed into a struct-of-arrays layout for coalesced GPU memory access.

```javascript
// ── Buffer Layout Constants ─────────────────────────────────────
const NODE_STRIDE = 48; // bytes per node (12 floats × 4 bytes)
// Layout: [x, y, vx, vy, mass, charge, size, r, g, b, shape, flags]

const LINK_STRIDE = 16; // bytes per link (4 uint32)
// Layout: [sourceIdx, targetIdx, strength, restLength_packed]

const QUAD_STRIDE = 32; // bytes per quadtree cell (8 floats)
// Layout: [cx, cy, totalMass, comX, comY, halfWidth, childPtr, nodeIdx]

// Maximum allocations — resize if exceeded
const MAX_NODES = 131072;  // 128K — power of 2 for GPU alignment
const MAX_LINKS = 524288;  // 512K
const MAX_QUAD_CELLS = MAX_NODES * 2; // Quadtree can have ~2N cells

class GPUBufferManager {
  constructor(device) {
    this.device = device;
    this.buffers = new Map();
  }

  /**
   * Create a pair of storage buffers for ping-pong simulation.
   * Buffer A is current state, Buffer B is next state. Swap each tick.
   */
  createNodeBuffers(nodeCount) {
    const size = Math.min(nodeCount, MAX_NODES) * NODE_STRIDE;

    const bufferA = this.device.createBuffer({
      label: 'nodes-A',
      size,
      usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_SRC | GPUBufferUsage.COPY_DST,
    });
    const bufferB = this.device.createBuffer({
      label: 'nodes-B',
      size,
      usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_SRC | GPUBufferUsage.COPY_DST,
    });

    // Staging buffer for CPU readback (MAP_READ)
    const staging = this.device.createBuffer({
      label: 'nodes-staging',
      size,
      usage: GPUBufferUsage.MAP_READ | GPUBufferUsage.COPY_DST,
    });

    this.buffers.set('nodes-A', bufferA);
    this.buffers.set('nodes-B', bufferB);
    this.buffers.set('nodes-staging', staging);
    return { bufferA, bufferB, staging };
  }

  createLinkBuffer(linkCount) {
    const size = Math.min(linkCount, MAX_LINKS) * LINK_STRIDE;
    const buffer = this.device.createBuffer({
      label: 'links',
      size,
      usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST,
    });
    this.buffers.set('links', buffer);
    return buffer;
  }

  createUniformBuffer(label, size) {
    const buffer = this.device.createBuffer({
      label,
      size: Math.ceil(size / 16) * 16, // 16-byte alignment for uniforms
      usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST,
    });
    this.buffers.set(label, buffer);
    return buffer;
  }

  /**
   * Upload CPU data into a GPU buffer.
   * NEVER create a new buffer — always write into an existing one.
   */
  upload(label, data) {
    const buffer = this.buffers.get(label);
    if (!buffer) throw new Error(`[GPU] Unknown buffer: ${label}`);
    this.device.queue.writeBuffer(buffer, 0, data);
  }

  destroy() {
    for (const buf of this.buffers.values()) buf.destroy();
    this.buffers.clear();
  }
}
```

### 1.3 Pipeline Creation

Two pipeline families: **compute** (force simulation) and **render** (drawing).

```javascript
class PipelineFactory {
  constructor(device, format) {
    this.device = device;
    this.format = format;
    this.pipelineCache = new Map();
  }

  async createComputePipeline(label, shaderCode, entryPoint, bindGroupLayout) {
    const key = `compute:${label}`;
    if (this.pipelineCache.has(key)) return this.pipelineCache.get(key);

    const module = this.device.createShaderModule({ label, code: shaderCode });

    // Check for compilation errors before pipeline creation
    const info = await module.getCompilationInfo();
    for (const msg of info.messages) {
      if (msg.type === 'error') {
        throw new Error(`[GPU] Shader compile error in ${label}: ${msg.message}`);
      }
    }

    const pipeline = await this.device.createComputePipelineAsync({
      label,
      layout: this.device.createPipelineLayout({ bindGroupLayouts: [bindGroupLayout] }),
      compute: { module, entryPoint },
    });

    this.pipelineCache.set(key, pipeline);
    return pipeline;
  }

  async createRenderPipeline(label, shaderCode, vertexBufferLayouts, bindGroupLayout) {
    const key = `render:${label}`;
    if (this.pipelineCache.has(key)) return this.pipelineCache.get(key);

    const module = this.device.createShaderModule({ label, code: shaderCode });

    const pipeline = await this.device.createRenderPipelineAsync({
      label,
      layout: this.device.createPipelineLayout({ bindGroupLayouts: [bindGroupLayout] }),
      vertex: {
        module,
        entryPoint: 'vs_main',
        buffers: vertexBufferLayouts,
      },
      fragment: {
        module,
        entryPoint: 'fs_main',
        targets: [{
          format: this.format,
          blend: {
            color: { srcFactor: 'src-alpha', dstFactor: 'one-minus-src-alpha' },
            alpha: { srcFactor: 'one', dstFactor: 'one-minus-src-alpha' },
          },
        }],
      },
      primitive: {
        topology: 'triangle-strip',
        stripIndexFormat: undefined,
      },
      multisample: { count: 4 }, // 4× MSAA for crisp edges
    });

    this.pipelineCache.set(key, pipeline);
    return pipeline;
  }
}
```

---

## 2. Compute Shader Force Simulation

### 2.1 Architecture Overview

Force simulation runs ENTIRELY on the GPU. Each force type is a separate compute
shader dispatch, executed sequentially within a single command encoder:

```
┌──────────────────────────────────────────────────────┐
│  GPU Command Encoder (per tick)                      │
│                                                      │
│  1. buildQuadtree      — spatial index for Barnes-Hut│
│  2. chargeForce        — n-body repulsion O(n log n) │
│  3. linkForce          — spring attraction            │
│  4. collisionForce     — spatial hash overlap resolve │
│  5. centerGravity      — pull toward center           │
│  6. integrate          — Verlet velocity + positions  │
│  7. copyBack           — staging buffer for CPU read  │
│                                                      │
│  Total: 7 dispatches per tick, ~2ms for 10K nodes    │
└──────────────────────────────────────────────────────┘
```

### 2.2 Simulation Uniforms

Shared by all force compute shaders:

```wgsl
// ── Simulation Parameters (uniform buffer, updated per tick) ────
struct SimParams {
  node_count:     u32,
  link_count:     u32,
  alpha:          f32,    // Current simulation temperature (0..1)
  alpha_decay:    f32,    // Per-tick decay: alpha *= (1 - alpha_decay)
  alpha_min:      f32,    // Stop when alpha < alpha_min
  velocity_decay: f32,    // Friction: v *= velocity_decay (0.4–0.6)
  dt:             f32,    // Time step (usually 1.0)
  theta:          f32,    // Barnes-Hut accuracy (0.9 = fast, 0.5 = precise)
  center_x:       f32,    // Gravity center X
  center_y:       f32,    // Gravity center Y
  center_strength: f32,   // Gravity pull strength (0.01–0.1)
  charge_strength: f32,   // Charge repulsion (negative = repel, e.g. -30)
  charge_max_dist: f32,   // Max distance for charge force (e.g. 500)
  collision_radius: f32,  // Base collision radius
  collision_strength: f32, // Overlap resolution strength (0.5–1.0)
  padding:        f32,    // 16-byte alignment
}

// ── Node Data (storage buffer, read/write) ──────────────────────
struct Node {
  x:      f32,
  y:      f32,
  vx:     f32,
  vy:     f32,
  mass:   f32,
  charge: f32,
  radius: f32,
  r:      f32,
  g:      f32,
  b:      f32,
  shape:  f32,   // 0=circle, 1=rect, 2=diamond, 3=hex, 4=star
  flags:  f32,   // bit 0=fixed, bit 1=selected, bit 2=hovered
}
```

### 2.3 Barnes-Hut Quadtree Construction (GPU)

The quadtree is built on the GPU in three passes: bounding box reduction,
tree construction, and center-of-mass propagation.

```wgsl
// ── Pass 1: Compute bounding box via parallel reduction ─────────
@group(0) @binding(0) var<storage, read>       nodes:  array<Node>;
@group(0) @binding(1) var<storage, read_write> bounds: array<f32>;  // [minX, minY, maxX, maxY]
@group(0) @binding(2) var<uniform>             params: SimParams;

var<workgroup> local_min_x: array<f32, 256>;
var<workgroup> local_min_y: array<f32, 256>;
var<workgroup> local_max_x: array<f32, 256>;
var<workgroup> local_max_y: array<f32, 256>;

@compute @workgroup_size(256)
fn computeBounds(@builtin(global_invocation_id) gid: vec3u,
                 @builtin(local_invocation_id) lid: vec3u) {
  let idx = gid.x;
  let local_idx = lid.x;

  if (idx < params.node_count) {
    local_min_x[local_idx] = nodes[idx].x;
    local_min_y[local_idx] = nodes[idx].y;
    local_max_x[local_idx] = nodes[idx].x;
    local_max_y[local_idx] = nodes[idx].y;
  } else {
    local_min_x[local_idx] =  1e30;
    local_min_y[local_idx] =  1e30;
    local_max_x[local_idx] = -1e30;
    local_max_y[local_idx] = -1e30;
  }

  workgroupBarrier();

  // Tree reduction within workgroup
  for (var stride = 128u; stride > 0u; stride >>= 1u) {
    if (local_idx < stride) {
      local_min_x[local_idx] = min(local_min_x[local_idx], local_min_x[local_idx + stride]);
      local_min_y[local_idx] = min(local_min_y[local_idx], local_min_y[local_idx + stride]);
      local_max_x[local_idx] = max(local_max_x[local_idx], local_max_x[local_idx + stride]);
      local_max_y[local_idx] = max(local_max_y[local_idx], local_max_y[local_idx + stride]);
    }
    workgroupBarrier();
  }

  // First thread writes workgroup result via atomics
  if (local_idx == 0u) {
    atomicMin(&bounds[0], bitcast<u32>(local_min_x[0]));
    atomicMin(&bounds[1], bitcast<u32>(local_min_y[0]));
    atomicMax(&bounds[2], bitcast<u32>(local_max_x[0]));
    atomicMax(&bounds[3], bitcast<u32>(local_max_y[0]));
  }
}
```

### 2.4 Barnes-Hut Charge Force (GPU)

The core n-body repulsion. Each thread walks the quadtree for one node,
using the Barnes-Hut `θ` criterion to approximate distant clusters.

```wgsl
// ── Quadtree Cell Layout ────────────────────────────────────────
struct QuadCell {
  center_x:    f32,   // Center of mass X
  center_y:    f32,   // Center of mass Y
  total_mass:  f32,   // Total mass of this cell
  half_width:  f32,   // Half-width of this cell's bounding region
  child_nw:    i32,   // Index of NW child (-1 if leaf or empty)
  child_ne:    i32,   // Index of NE child
  child_sw:    i32,   // Index of SW child
  child_se:    i32,   // Index of SE child
}

@group(0) @binding(0) var<storage, read>       nodes:    array<Node>;
@group(0) @binding(1) var<storage, read_write> forces:   array<vec2f>;
@group(0) @binding(2) var<storage, read>       quadtree: array<QuadCell>;
@group(0) @binding(3) var<uniform>             params:   SimParams;

// Explicit stack for non-recursive tree walk (GPU has no call stack)
const STACK_DEPTH: u32 = 64u;

@compute @workgroup_size(256)
fn chargeForce(@builtin(global_invocation_id) gid: vec3u) {
  let idx = gid.x;
  if (idx >= params.node_count) { return; }

  let node = nodes[idx];
  var fx: f32 = 0.0;
  var fy: f32 = 0.0;

  // Stack-based tree traversal
  var stack: array<u32, STACK_DEPTH>;
  var sp: u32 = 0u;
  stack[sp] = 0u; // Root cell index
  sp += 1u;

  while (sp > 0u) {
    sp -= 1u;
    let cell_idx = stack[sp];
    let cell = quadtree[cell_idx];

    if (cell.total_mass < 0.001) { continue; } // Empty cell

    let dx = cell.center_x - node.x;
    let dy = cell.center_y - node.y;
    let dist_sq = dx * dx + dy * dy + 0.01; // Softening factor
    let dist = sqrt(dist_sq);

    // Barnes-Hut criterion: if cell width / distance < θ, treat as point mass
    let ratio = cell.half_width * 2.0 / dist;

    if (ratio < params.theta || (cell.child_nw < 0 && cell.child_ne < 0
        && cell.child_sw < 0 && cell.child_se < 0)) {
      // Approximate: use center-of-mass
      let strength = params.charge_strength * node.charge * cell.total_mass;
      let force = strength / dist_sq;
      let capped_force = clamp(force, -100.0, 100.0); // Prevent explosion

      if (dist > 0.1) {
        fx += capped_force * dx / dist;
        fy += capped_force * dy / dist;
      }
    } else {
      // Recurse: push children onto stack
      if (cell.child_nw >= 0 && sp < STACK_DEPTH) { stack[sp] = u32(cell.child_nw); sp += 1u; }
      if (cell.child_ne >= 0 && sp < STACK_DEPTH) { stack[sp] = u32(cell.child_ne); sp += 1u; }
      if (cell.child_sw >= 0 && sp < STACK_DEPTH) { stack[sp] = u32(cell.child_sw); sp += 1u; }
      if (cell.child_se >= 0 && sp < STACK_DEPTH) { stack[sp] = u32(cell.child_se); sp += 1u; }
    }
  }

  // Clamp maximum distance for charge force
  let max_f = params.charge_max_dist;
  fx = clamp(fx, -max_f, max_f);
  fy = clamp(fy, -max_f, max_f);

  forces[idx] = vec2f(fx, fy);
}
```

### 2.5 Link Force — Spring Calculation

```wgsl
// ── Link Data Layout ────────────────────────────────────────────
struct Link {
  source:       u32,
  target:       u32,
  strength:     f32,
  rest_length:  f32,
}

@group(0) @binding(0) var<storage, read>       nodes:  array<Node>;
@group(0) @binding(1) var<storage, read_write> forces: array<vec2f>;
@group(0) @binding(2) var<storage, read>       links:  array<Link>;
@group(0) @binding(3) var<uniform>             params: SimParams;

@compute @workgroup_size(256)
fn linkForce(@builtin(global_invocation_id) gid: vec3u) {
  let idx = gid.x;
  if (idx >= params.link_count) { return; }

  let link = links[idx];
  let src = nodes[link.source];
  let tgt = nodes[link.target];

  let dx = tgt.x - src.x;
  let dy = tgt.y - src.y;
  let dist = max(sqrt(dx * dx + dy * dy), 0.01);
  let displacement = dist - link.rest_length;

  // Hooke's law: F = -k * displacement
  let force_mag = link.strength * displacement * params.alpha;
  let fx = force_mag * dx / dist;
  let fy = force_mag * dy / dist;

  // Bias force toward lighter node (like D3)
  let total_mass = src.mass + tgt.mass;
  let bias_src = tgt.mass / total_mass;
  let bias_tgt = src.mass / total_mass;

  // Atomic add — multiple links may affect the same node
  atomicAdd(&forces[link.source].x, fx * bias_src);
  atomicAdd(&forces[link.source].y, fy * bias_src);
  atomicAdd(&forces[link.target].x, -fx * bias_tgt);
  atomicAdd(&forces[link.target].y, -fy * bias_tgt);
}
```

> **Note:** WGSL does not natively support `atomicAdd` on `f32`. In production, use
> atomic u32 with `bitcast` or accumulate in a separate per-link output buffer and
> reduce in a second pass. The code above shows the logical intent.

### 2.6 Collision Detection via Spatial Hash Grid

```wgsl
// ── Spatial Hash Grid ───────────────────────────────────────────
// Grid cells: each cell stores up to MAX_PER_CELL node indices
const GRID_DIM: u32 = 256u;
const MAX_PER_CELL: u32 = 16u;

@group(0) @binding(0) var<storage, read>       nodes:    array<Node>;
@group(0) @binding(1) var<storage, read_write> forces:   array<vec2f>;
@group(0) @binding(2) var<storage, read_write> grid:     array<u32>;  // GRID_DIM² × MAX_PER_CELL
@group(0) @binding(3) var<storage, read_write> counts:   array<atomic<u32>>; // GRID_DIM²
@group(0) @binding(4) var<uniform>             params:   SimParams;
@group(0) @binding(5) var<storage, read>       bounds:   array<f32>;  // [minX, minY, maxX, maxY]

fn getCellIndex(x: f32, y: f32) -> u32 {
  let minX = bounds[0]; let minY = bounds[1];
  let maxX = bounds[2]; let maxY = bounds[3];
  let cx = clamp(u32((x - minX) / (maxX - minX + 0.01) * f32(GRID_DIM)), 0u, GRID_DIM - 1u);
  let cy = clamp(u32((y - minY) / (maxY - minY + 0.01) * f32(GRID_DIM)), 0u, GRID_DIM - 1u);
  return cy * GRID_DIM + cx;
}

// Pass 1: Insert nodes into grid
@compute @workgroup_size(256)
fn gridInsert(@builtin(global_invocation_id) gid: vec3u) {
  let idx = gid.x;
  if (idx >= params.node_count) { return; }
  let cell = getCellIndex(nodes[idx].x, nodes[idx].y);
  let slot = atomicAdd(&counts[cell], 1u);
  if (slot < MAX_PER_CELL) {
    grid[cell * MAX_PER_CELL + slot] = idx;
  }
}

// Pass 2: Resolve overlaps in neighboring cells
@compute @workgroup_size(256)
fn collisionResolve(@builtin(global_invocation_id) gid: vec3u) {
  let idx = gid.x;
  if (idx >= params.node_count) { return; }

  let node = nodes[idx];
  let cx = u32((node.x - bounds[0]) / (bounds[2] - bounds[0] + 0.01) * f32(GRID_DIM));
  let cy = u32((node.y - bounds[1]) / (bounds[3] - bounds[1] + 0.01) * f32(GRID_DIM));

  var fx: f32 = 0.0;
  var fy: f32 = 0.0;

  // Check 3×3 neighborhood
  for (var dy: i32 = -1; dy <= 1; dy++) {
    for (var dx: i32 = -1; dx <= 1; dx++) {
      let nx = i32(cx) + dx;
      let ny = i32(cy) + dy;
      if (nx < 0 || nx >= i32(GRID_DIM) || ny < 0 || ny >= i32(GRID_DIM)) { continue; }

      let cell = u32(ny) * GRID_DIM + u32(nx);
      let count = min(atomicLoad(&counts[cell]), MAX_PER_CELL);

      for (var s = 0u; s < count; s++) {
        let other_idx = grid[cell * MAX_PER_CELL + s];
        if (other_idx == idx) { continue; }

        let other = nodes[other_idx];
        let ddx = node.x - other.x;
        let ddy = node.y - other.y;
        let dist_sq = ddx * ddx + ddy * ddy;
        let min_dist = (node.radius + other.radius) * params.collision_radius;
        let min_dist_sq = min_dist * min_dist;

        if (dist_sq < min_dist_sq && dist_sq > 0.001) {
          let dist = sqrt(dist_sq);
          let overlap = min_dist - dist;
          let resolve = overlap * params.collision_strength * 0.5;
          fx += resolve * ddx / dist;
          fy += resolve * ddy / dist;
        }
      }
    }
  }

  forces[idx] = vec2f(forces[idx].x + fx, forces[idx].y + fy);
}
```

### 2.7 Center Gravity Force

```wgsl
@group(0) @binding(0) var<storage, read>       nodes:  array<Node>;
@group(0) @binding(1) var<storage, read_write> forces: array<vec2f>;
@group(0) @binding(2) var<uniform>             params: SimParams;

@compute @workgroup_size(256)
fn centerGravity(@builtin(global_invocation_id) gid: vec3u) {
  let idx = gid.x;
  if (idx >= params.node_count) { return; }

  let node = nodes[idx];
  let dx = params.center_x - node.x;
  let dy = params.center_y - node.y;
  let dist = sqrt(dx * dx + dy * dy) + 0.01;

  let strength = params.center_strength * params.alpha * node.mass;
  forces[idx] = vec2f(
    forces[idx].x + dx * strength / dist,
    forces[idx].y + dy * strength / dist,
  );
}
```

### 2.8 Velocity Verlet Integration

```wgsl
@group(0) @binding(0) var<storage, read_write> nodes:  array<Node>;
@group(0) @binding(1) var<storage, read>       forces: array<vec2f>;
@group(0) @binding(2) var<uniform>             params: SimParams;

@compute @workgroup_size(256)
fn integrate(@builtin(global_invocation_id) gid: vec3u) {
  let idx = gid.x;
  if (idx >= params.node_count) { return; }

  // Skip fixed nodes (bit 0 of flags)
  if (u32(nodes[idx].flags) & 1u) != 0u {
    nodes[idx].vx = 0.0;
    nodes[idx].vy = 0.0;
    return;
  }

  // Apply accumulated force as acceleration (F = ma → a = F/m)
  let ax = forces[idx].x / max(nodes[idx].mass, 0.1);
  let ay = forces[idx].y / max(nodes[idx].mass, 0.1);

  // Velocity Verlet: v += a * dt, then apply decay
  var vx = (nodes[idx].vx + ax * params.dt) * params.velocity_decay;
  var vy = (nodes[idx].vy + ay * params.dt) * params.velocity_decay;

  // Clamp velocity to prevent explosion
  let speed = sqrt(vx * vx + vy * vy);
  let max_speed = 50.0;
  if (speed > max_speed) {
    vx = vx / speed * max_speed;
    vy = vy / speed * max_speed;
  }

  // Update position
  nodes[idx].x += vx * params.dt;
  nodes[idx].y += vy * params.dt;
  nodes[idx].vx = vx;
  nodes[idx].vy = vy;
}
```

### 2.9 Workgroup Size Optimization

```javascript
// ── Workgroup Size Selection ────────────────────────────────────
function getOptimalWorkgroupSize(device, nodeCount) {
  const maxX = device.limits.maxComputeWorkgroupSizeX; // Usually 256 or 1024
  const maxInvocations = device.limits.maxComputeInvocationsPerWorkgroup;

  // Prefer 256 for most GPUs — good occupancy on both AMD and NVIDIA
  // Use 64 for very small graphs (< 1K nodes) to avoid waste
  // Use 128 on integrated GPUs (Vega, Intel UHD) with limited CUs
  if (nodeCount < 1024) return 64;
  if (maxX >= 256 && maxInvocations >= 256) return 256;
  if (maxX >= 128) return 128;
  return 64;
}

function getDispatchCount(totalItems, workgroupSize) {
  return Math.ceil(totalItems / workgroupSize);
}
```

### 2.10 Simulation Tick Orchestration (JavaScript)

```javascript
class GPUForceSimulation {
  constructor(gpuContext, bufferManager, pipelineFactory) {
    this.gpu = gpuContext;
    this.buffers = bufferManager;
    this.pipelines = pipelineFactory;
    this.alpha = 1.0;
    this.alphaDecay = 0.0228; // ~300 ticks to cool
    this.alphaMin = 0.001;
    this.tickCount = 0;
    this.pingPong = 0; // 0 = A→B, 1 = B→A
  }

  tick() {
    if (this.alpha < this.alphaMin) return false; // Simulation cooled

    const device = this.gpu.device;
    const encoder = device.createCommandEncoder({ label: `sim-tick-${this.tickCount}` });
    const wgSize = getOptimalWorkgroupSize(device, this.nodeCount);
    const dispatch = getDispatchCount(this.nodeCount, wgSize);

    // Clear force accumulator
    encoder.clearBuffer(this.buffers.buffers.get('forces'));

    // 1. Build quadtree bounds
    const boundsPass = encoder.beginComputePass({ label: 'bounds' });
    boundsPass.setPipeline(this.boundsPipeline);
    boundsPass.setBindGroup(0, this.boundsBindGroup);
    boundsPass.dispatchWorkgroups(dispatch);
    boundsPass.end();

    // 2. Charge force (Barnes-Hut)
    const chargePass = encoder.beginComputePass({ label: 'charge' });
    chargePass.setPipeline(this.chargePipeline);
    chargePass.setBindGroup(0, this.chargeBindGroup);
    chargePass.dispatchWorkgroups(dispatch);
    chargePass.end();

    // 3. Link force (springs)
    const linkDispatch = getDispatchCount(this.linkCount, wgSize);
    const linkPass = encoder.beginComputePass({ label: 'link' });
    linkPass.setPipeline(this.linkPipeline);
    linkPass.setBindGroup(0, this.linkBindGroup);
    linkPass.dispatchWorkgroups(linkDispatch);
    linkPass.end();

    // 4. Collision detection
    const collisionPass = encoder.beginComputePass({ label: 'collision' });
    collisionPass.setPipeline(this.collisionPipeline);
    collisionPass.setBindGroup(0, this.collisionBindGroup);
    collisionPass.dispatchWorkgroups(dispatch);
    collisionPass.end();

    // 5. Center gravity
    const centerPass = encoder.beginComputePass({ label: 'center' });
    centerPass.setPipeline(this.centerPipeline);
    centerPass.setBindGroup(0, this.centerBindGroup);
    centerPass.dispatchWorkgroups(dispatch);
    centerPass.end();

    // 6. Integration (position + velocity update)
    const integratePass = encoder.beginComputePass({ label: 'integrate' });
    integratePass.setPipeline(this.integratePipeline);
    integratePass.setBindGroup(0, this.integrateBindGroup);
    integratePass.dispatchWorkgroups(dispatch);
    integratePass.end();

    // 7. Copy to staging buffer for CPU readback (async)
    encoder.copyBufferToBuffer(
      this.buffers.buffers.get('nodes-A'), 0,
      this.buffers.buffers.get('nodes-staging'), 0,
      this.nodeCount * NODE_STRIDE
    );

    device.queue.submit([encoder.finish()]);

    // Alpha decay
    this.alpha += (this.alphaMin - this.alpha) * this.alphaDecay;
    this.tickCount++;
    return true;
  }

  /**
   * Async readback — NEVER block the main thread.
   * Returns a Float32Array of node positions for D3 synchronization.
   */
  async readPositions() {
    const staging = this.buffers.buffers.get('nodes-staging');
    await staging.mapAsync(GPUMapMode.READ);
    const data = new Float32Array(staging.getMappedRange().slice());
    staging.unmap();
    return data;
  }
}
```

---

## 3. Instanced SDF Node Rendering

### 3.1 SDF Fundamentals

Signed Distance Functions define shape boundaries mathematically. Instead of
rasterizing a polygon, we evaluate a distance function per pixel:
- `d < 0` → inside the shape
- `d = 0` → on the boundary
- `d > 0` → outside the shape

This gives perfect anti-aliasing via `smoothstep` and resolution-independent
rendering — nodes look crisp at any zoom level.

### 3.2 Instanced Drawing Architecture

One draw call renders ALL nodes of the same type. Each node is a **fullscreen
quad** (4 vertices, triangle-strip) with per-instance data injected via a
storage buffer. The vertex shader positions the quad; the fragment shader
evaluates the SDF.

```
┌──────────────────────────────────────────────────┐
│  Render Pass                                     │
│                                                  │
│  draw(4 vertices, N instances)                   │
│    → Vertex Shader: position quad at node center │
│    → Fragment Shader: evaluate SDF per pixel     │
│                                                  │
│  One draw call for ALL nodes. Zero CPU overhead. │
└──────────────────────────────────────────────────┘
```

### 3.3 Vertex & Fragment Shaders (WGSL)

```wgsl
// ── Render Uniforms ─────────────────────────────────────────────
struct RenderParams {
  view_matrix:   mat3x3f,  // 2D transform: pan + zoom
  resolution:    vec2f,     // Canvas width, height
  zoom:          f32,       // Current zoom level
  time:          f32,       // Animation time (seconds)
  hover_idx:     i32,       // Hovered node index (-1 if none)
  select_idx:    i32,       // Selected node index (-1 if none)
  lod_level:     u32,       // Current LOD (0–4)
  glow_intensity: f32,      // Global glow multiplier
}

// ── Per-Instance Node Data (storage buffer) ─────────────────────
struct NodeInstance {
  x:       f32,
  y:       f32,
  radius:  f32,
  r:       f32,
  g:       f32,
  b:       f32,
  shape:   f32,   // 0=circle, 1=rect, 2=diamond, 3=hex, 4=star
  glow:    f32,   // Per-node glow intensity (0=none, 1=full)
  border:  f32,   // Border width in pixels
  opacity: f32,   // 0..1
  flags:   u32,   // bit 0=selected, bit 1=hovered, bit 2=dimmed
  _pad:    f32,
}

@group(0) @binding(0) var<uniform>       renderParams: RenderParams;
@group(0) @binding(1) var<storage, read> instances:    array<NodeInstance>;

struct VertexOutput {
  @builtin(position) clip_pos:  vec4f,
  @location(0)       local_uv:  vec2f,   // [-1, 1] quad coords
  @location(1) @interpolate(flat) inst_idx: u32,
}

// ── Vertex Shader ───────────────────────────────────────────────
@vertex
fn vs_main(
  @builtin(vertex_index)   vid: u32,
  @builtin(instance_index) iid: u32,
) -> VertexOutput {
  // Generate fullscreen quad: 4 vertices, triangle strip
  let uv = vec2f(
    f32((vid & 1u)),         // 0, 1, 0, 1
    f32((vid >> 1u) & 1u),   // 0, 0, 1, 1
  ) * 2.0 - 1.0;            // Map to [-1, 1]

  let inst = instances[iid];

  // Size in clip space (account for zoom + radius)
  let pad = 4.0; // Extra pixels for glow/AA
  let size = (inst.radius + pad) / renderParams.resolution * 2.0 * renderParams.zoom;

  // World-to-clip position
  let world_pos = vec2f(inst.x, inst.y);
  let view_pos = (renderParams.view_matrix * vec3f(world_pos, 1.0)).xy;
  let clip = view_pos / renderParams.resolution * 2.0 - 1.0;

  var out: VertexOutput;
  out.clip_pos = vec4f(clip + uv * size, 0.0, 1.0);
  out.local_uv = uv;
  out.inst_idx = iid;
  return out;
}

// ── SDF Primitives ──────────────────────────────────────────────
fn sdfCircle(p: vec2f, r: f32) -> f32 {
  return length(p) - r;
}

fn sdfRoundedRect(p: vec2f, halfSize: vec2f, cornerRadius: f32) -> f32 {
  let d = abs(p) - halfSize + vec2f(cornerRadius);
  return length(max(d, vec2f(0.0))) + min(max(d.x, d.y), 0.0) - cornerRadius;
}

fn sdfDiamond(p: vec2f, r: f32) -> f32 {
  let q = abs(p);
  return (q.x + q.y - r) * 0.7071; // 1/sqrt(2)
}

fn sdfHexagon(p: vec2f, r: f32) -> f32 {
  let k = vec3f(-0.866025, 0.5, 0.57735); // cos(30°), sin(30°), tan(30°)
  var q = abs(p);
  q -= 2.0 * min(dot(k.xy, q), 0.0) * k.xy;
  q -= vec2f(clamp(q.x, -k.z * r, k.z * r), r);
  return length(q) * sign(q.y);
}

fn sdfStar5(p: vec2f, r: f32) -> f32 {
  let k1 = vec2f(0.809016994, -0.587785252); // cos/sin 36°
  let k2 = vec2f(-k1.x, k1.y);
  var q = abs(p);
  q -= 2.0 * max(dot(k1, q), 0.0) * k1;
  q -= 2.0 * max(dot(k2, q), 0.0) * k2;
  q -= vec2f(clamp(q.x, 0.0, r), 0.0);
  return length(q) * sign(q.y) - r * 0.2;
}

// ── Fragment Shader ─────────────────────────────────────────────
@fragment
fn fs_main(in: VertexOutput) -> @location(0) vec4f {
  let inst = instances[in.inst_idx];
  let p = in.local_uv * (inst.radius + 4.0); // Scale UV to pixel coords
  let r = inst.radius;

  // Select SDF based on shape type
  var dist: f32;
  let shape = u32(inst.shape);
  switch (shape) {
    case 0u: { dist = sdfCircle(p, r); }
    case 1u: { dist = sdfRoundedRect(p, vec2f(r * 0.9, r * 0.6), r * 0.15); }
    case 2u: { dist = sdfDiamond(p, r); }
    case 3u: { dist = sdfHexagon(p, r); }
    case 4u: { dist = sdfStar5(p, r); }
    default: { dist = sdfCircle(p, r); }
  }

  // Anti-aliased fill
  let aa_width = 1.5; // pixels of anti-aliasing
  let fill_alpha = 1.0 - smoothstep(-aa_width, aa_width, dist);

  // Border ring
  let border_inner = abs(dist + inst.border * 0.5) - inst.border * 0.5;
  let border_alpha = 1.0 - smoothstep(-aa_width, aa_width, border_inner);

  // Base color
  var color = vec3f(inst.r, inst.g, inst.b);

  // Hover / selection highlight
  let is_hovered = (inst.flags & 2u) != 0u;
  let is_selected = (inst.flags & 1u) != 0u;
  let is_dimmed = (inst.flags & 4u) != 0u;

  if (is_selected) {
    color = mix(color, vec3f(1.0, 0.85, 0.0), 0.4); // Gold highlight
  }
  if (is_hovered) {
    color = mix(color, vec3f(1.0, 1.0, 1.0), 0.3); // Brighten
  }
  if (is_dimmed) {
    color *= 0.3; // Dim non-relevant nodes
  }

  // Glow effect (outer ring beyond shape boundary)
  let glow_dist = max(dist, 0.0);
  let glow_radius = r * 0.5 * inst.glow * renderParams.glow_intensity;
  let glow_alpha = exp(-glow_dist * glow_dist / max(glow_radius * glow_radius, 0.01));
  let glow_color = color * 1.5; // Brighter glow

  // Composite: glow behind, then fill, then border
  var final_color = glow_color * glow_alpha * 0.4;
  final_color = mix(final_color, color, fill_alpha);
  final_color = mix(final_color, vec3f(1.0), border_alpha * 0.8);

  let final_alpha = max(max(fill_alpha, border_alpha), glow_alpha * 0.3) * inst.opacity;

  if (final_alpha < 0.01) { discard; }

  return vec4f(final_color * final_alpha, final_alpha); // Premultiplied alpha
}
```

### 3.4 Node Shape Registry

| Shape ID | SDF Function     | Use Case (THEMANBEARPIG)         |
|----------|------------------|----------------------------------|
| 0        | Circle           | Default — people, generic nodes  |
| 1        | Rounded Rectangle| Documents, orders, filings       |
| 2        | Diamond          | Key evidence, critical nodes     |
| 3        | Hexagon          | Judicial actors, court entities   |
| 4        | Star (5-point)   | Smoking gun evidence, HIGH items |

### 3.5 Instance Buffer Update (JavaScript)

```javascript
function updateInstanceBuffer(device, buffer, nodes, viewState) {
  const FLOATS_PER_INSTANCE = 12; // Must match NodeInstance struct
  const data = new Float32Array(nodes.length * FLOATS_PER_INSTANCE);

  for (let i = 0; i < nodes.length; i++) {
    const n = nodes[i];
    const off = i * FLOATS_PER_INSTANCE;

    data[off + 0]  = n.x;
    data[off + 1]  = n.y;
    data[off + 2]  = n.radius ?? 8;
    data[off + 3]  = n.color?.[0] ?? 0.5; // r
    data[off + 4]  = n.color?.[1] ?? 0.5; // g
    data[off + 5]  = n.color?.[2] ?? 0.8; // b
    data[off + 6]  = n.shape ?? 0;
    data[off + 7]  = n.glow ?? 0;
    data[off + 8]  = n.border ?? 1.5;
    data[off + 9]  = n.opacity ?? 1.0;
    data[off + 10] = (n.selected ? 1 : 0) | (n.hovered ? 2 : 0) | (n.dimmed ? 4 : 0);
    data[off + 11] = 0; // padding
  }

  device.queue.writeBuffer(buffer, 0, data);
}
```

---

## 4. Link Rendering

### 4.1 Instanced Link Lines

Links are rendered as oriented quads — two triangles forming a rectangle with
controllable width. Each link instance carries: source/target positions (looked up
from the node buffer in the vertex shader), color, width, curve factor, and opacity.

```wgsl
// ── Link Instance Data ──────────────────────────────────────────
struct LinkInstance {
  src_x:    f32,
  src_y:    f32,
  tgt_x:    f32,
  tgt_y:    f32,
  r:        f32,
  g:        f32,
  b:        f32,
  width:    f32,
  curve:    f32,   // 0=straight, >0=curved (quadratic Bezier)
  opacity:  f32,
  has_arrow: f32,  // 0=no, 1=yes
  _pad:     f32,
}

@group(0) @binding(0) var<uniform>       renderParams: RenderParams;
@group(0) @binding(1) var<storage, read> linkInstances: array<LinkInstance>;

struct LinkVertexOut {
  @builtin(position) pos:   vec4f,
  @location(0)       uv:    vec2f,
  @location(1) @interpolate(flat) link_idx: u32,
  @location(2)       along: f32,   // 0..1 distance along the link
}

@vertex
fn vs_link(
  @builtin(vertex_index)   vid: u32,
  @builtin(instance_index) iid: u32,
) -> LinkVertexOut {
  let link = linkInstances[iid];

  // Quad vertices: 4 corners of a line segment
  let along = f32(vid / 2u);     // 0 or 1 (start or end)
  let side  = f32(vid % 2u) * 2.0 - 1.0; // -1 or +1

  let src = vec2f(link.src_x, link.src_y);
  let tgt = vec2f(link.tgt_x, link.tgt_y);

  // Optional curve via quadratic Bezier
  let mid = (src + tgt) * 0.5;
  let perp = normalize(vec2f(-(tgt.y - src.y), tgt.x - src.x));
  let ctrl = mid + perp * link.curve * length(tgt - src) * 0.3;

  // Evaluate Bezier at along parameter
  let t = along;
  let pos = (1.0 - t) * (1.0 - t) * src + 2.0 * (1.0 - t) * t * ctrl + t * t * tgt;

  // Tangent for perpendicular offset (line width)
  let tangent = normalize(2.0 * (1.0 - t) * (ctrl - src) + 2.0 * t * (tgt - ctrl));
  let normal = vec2f(-tangent.y, tangent.x);

  let half_width = link.width * 0.5 / renderParams.zoom;
  let world_pos = pos + normal * side * half_width;

  let view_pos = (renderParams.view_matrix * vec3f(world_pos, 1.0)).xy;
  let clip = view_pos / renderParams.resolution * 2.0 - 1.0;

  var out: LinkVertexOut;
  out.pos = vec4f(clip, 0.1, 1.0); // z=0.1 — behind nodes
  out.uv = vec2f(along, side * 0.5 + 0.5);
  out.link_idx = iid;
  out.along = along;
  return out;
}

// ── Arrow SDF (triangle at end of link) ─────────────────────────
fn sdfArrow(p: vec2f, size: f32) -> f32 {
  let q = vec2f(abs(p.x), p.y);
  return max(q.x * 0.866 + q.y * 0.5, -q.y) - size * 0.5;
}

@fragment
fn fs_link(in: LinkVertexOut) -> @location(0) vec4f {
  let link = linkInstances[in.link_idx];
  var color = vec3f(link.r, link.g, link.b);
  var alpha = link.opacity;

  // Anti-aliased edge
  let edge_dist = abs(in.uv.y - 0.5) * 2.0; // 0 at center, 1 at edge
  alpha *= 1.0 - smoothstep(0.7, 1.0, edge_dist);

  // Arrow at target end (along > 0.85)
  if (link.has_arrow > 0.5 && in.along > 0.85) {
    let arrow_uv = vec2f(
      (in.uv.y - 0.5) * 10.0,
      (in.along - 0.925) * 20.0,
    );
    let arrow_d = sdfArrow(arrow_uv, 3.0);
    let arrow_alpha = 1.0 - smoothstep(-1.0, 1.0, arrow_d);
    alpha = max(alpha, arrow_alpha * link.opacity);
  }

  if (alpha < 0.01) { discard; }
  return vec4f(color * alpha, alpha);
}
```

### 4.2 Link Color Encoding (THEMANBEARPIG)

| Relationship Type       | Color                    | Width |
|--------------------------|--------------------------|-------|
| Family / kinship         | `#6699CC` (steel blue)  | 2px   |
| Legal / court filing     | `#CC6633` (amber)       | 2px   |
| Financial / transaction  | `#33CC66` (green)       | 1.5px |
| Accusation / allegation  | `#CC3333` (red)         | 3px   |
| Communication            | `#9966CC` (purple)      | 1px   |
| Employment               | `#999999` (gray)        | 1px   |
| Evidence supports        | `#66CCCC` (teal)        | 2px   |
| Judicial cartel          | `#FF6600` (bright orange)| 4px  |
| Contradiction            | `#FF0066` (hot pink)    | 3px   |

### 4.3 Link Rendering Order

1. Draw ALL links first (z = 0.1, behind nodes).
2. Faded links (dimmed context) at 0.15 opacity.
3. Highlighted links (connected to hovered/selected) at full opacity.
4. Animated pulse for active legal connections.

---

## 5. Level of Detail (LOD) System

### 5.1 LOD Level Definitions

```javascript
const LOD_LEVELS = [
  {
    level: 0,
    name: 'cosmic',
    zoomRange: [0.0, 0.05],
    nodes: { shape: 'dot', minRadius: 1, maxRadius: 3 },
    links: { visible: false },
    labels: { visible: false },
    detail: 'Dots only — galaxy view',
  },
  {
    level: 1,
    name: 'cluster',
    zoomRange: [0.05, 0.2],
    nodes: { shape: 'simple', minRadius: 2, maxRadius: 6 },
    links: { visible: true, width: 0.5, opacity: 0.2 },
    labels: { visible: true, budget: 20, filter: 'clusters-only' },
    detail: 'Cluster labels, thin links',
  },
  {
    level: 2,
    name: 'neighborhood',
    zoomRange: [0.2, 0.6],
    nodes: { shape: 'colored', minRadius: 4, maxRadius: 12 },
    links: { visible: true, width: 1.0, opacity: 0.5 },
    labels: { visible: true, budget: 80, filter: 'important' },
    detail: 'Colored shapes, important labels',
  },
  {
    level: 3,
    name: 'street',
    zoomRange: [0.6, 2.0],
    nodes: { shape: 'full-sdf', minRadius: 6, maxRadius: 20 },
    links: { visible: true, width: 2.0, opacity: 0.8, arrows: true },
    labels: { visible: true, budget: 200, filter: 'all-in-view' },
    detail: 'Full detail, all labels in viewport',
  },
  {
    level: 4,
    name: 'microscope',
    zoomRange: [2.0, Infinity],
    nodes: { shape: 'full-sdf', minRadius: 10, maxRadius: 40, showMetadata: true },
    links: { visible: true, width: 3.0, opacity: 1.0, arrows: true, animated: true },
    labels: { visible: true, budget: 500, filter: 'all', showSubtext: true },
    detail: 'Maximum detail, metadata tooltips, animated links',
  },
];

function getLODLevel(zoom) {
  for (const lod of LOD_LEVELS) {
    if (zoom >= lod.zoomRange[0] && zoom < lod.zoomRange[1]) return lod;
  }
  return LOD_LEVELS[LOD_LEVELS.length - 1];
}
```

### 5.2 Viewport Frustum Culling

Only nodes inside the visible viewport are rendered. A CPU-side quadtree provides
O(log n) viewport queries:

```javascript
class ViewportQuadtree {
  constructor(bounds, maxDepth = 12, maxItems = 8) {
    this.root = null;
    this.maxDepth = maxDepth;
    this.maxItems = maxItems;
  }

  build(nodes) {
    // Compute bounding box
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const n of nodes) {
      if (n.x < minX) minX = n.x;
      if (n.y < minY) minY = n.y;
      if (n.x > maxX) maxX = n.x;
      if (n.y > maxY) maxY = n.y;
    }
    const pad = 50;
    this.root = this._createNode(minX - pad, minY - pad, maxX + pad, maxY + pad, 0);
    for (let i = 0; i < nodes.length; i++) {
      this._insert(this.root, nodes[i], i, 0);
    }
  }

  _createNode(x0, y0, x1, y1, depth) {
    return { x0, y0, x1, y1, depth, items: [], children: null };
  }

  _insert(node, point, idx, depth) {
    if (!this._contains(node, point.x, point.y)) return;
    if (node.items !== null && (node.items.length < this.maxItems || depth >= this.maxDepth)) {
      node.items.push(idx);
      return;
    }
    if (node.children === null) {
      this._subdivide(node);
      for (const existingIdx of node.items) {
        for (const child of node.children) {
          this._insert(child, { x: this._getX(existingIdx), y: this._getY(existingIdx) }, existingIdx, depth + 1);
        }
      }
      node.items = null;
    }
    for (const child of node.children) {
      this._insert(child, point, idx, depth + 1);
    }
  }

  _subdivide(node) {
    const mx = (node.x0 + node.x1) / 2;
    const my = (node.y0 + node.y1) / 2;
    const d = node.depth + 1;
    node.children = [
      this._createNode(node.x0, node.y0, mx, my, d), // NW
      this._createNode(mx, node.y0, node.x1, my, d),  // NE
      this._createNode(node.x0, my, mx, node.y1, d),  // SW
      this._createNode(mx, my, node.x1, node.y1, d),  // SE
    ];
  }

  _contains(node, x, y) {
    return x >= node.x0 && x <= node.x1 && y >= node.y0 && y <= node.y1;
  }

  /**
   * Query: return all node indices within the viewport rectangle.
   */
  queryViewport(viewX0, viewY0, viewX1, viewY1) {
    const results = [];
    this._queryRect(this.root, viewX0, viewY0, viewX1, viewY1, results);
    return results;
  }

  _queryRect(node, vx0, vy0, vx1, vy1, results) {
    if (!node) return;
    // Skip if node bounds don't intersect viewport
    if (node.x1 < vx0 || node.x0 > vx1 || node.y1 < vy0 || node.y0 > vy1) return;
    if (node.items !== null) {
      results.push(...node.items);
      return;
    }
    if (node.children) {
      for (const child of node.children) {
        this._queryRect(child, vx0, vy0, vx1, vy1, results);
      }
    }
  }
}
```

### 5.3 Dynamic Label Budget

Labels are expensive — rendered via a Canvas overlay, not the GPU. The label budget
limits how many labels are drawn per frame based on LOD level and viewport:

```javascript
class LabelManager {
  constructor(overlayCanvas) {
    this.ctx = overlayCanvas.getContext('2d');
    this.visible = [];
  }

  update(nodes, visibleIndices, lodLevel, viewTransform) {
    const budget = lodLevel.labels.budget;
    if (!lodLevel.labels.visible || budget === 0) {
      this.visible = [];
      return;
    }

    // Score each visible node for label priority
    const scored = visibleIndices.map(i => ({
      idx: i,
      priority: this._labelPriority(nodes[i], lodLevel),
    }));

    // Sort by priority descending, take top N
    scored.sort((a, b) => b.priority - a.priority);
    this.visible = scored.slice(0, budget).map(s => s.idx);
  }

  _labelPriority(node, lod) {
    let score = 0;
    if (node.selected) score += 1000;
    if (node.hovered) score += 500;
    score += (node.importance ?? 1) * 10;
    score += (node.links?.length ?? 0) * 2;
    if (node.label?.length > 0) score += 5;
    return score;
  }

  render(nodes, viewTransform) {
    this.ctx.clearRect(0, 0, this.ctx.canvas.width, this.ctx.canvas.height);
    this.ctx.font = '11px "Inter", sans-serif';
    this.ctx.textAlign = 'center';
    this.ctx.textBaseline = 'top';

    for (const idx of this.visible) {
      const n = nodes[idx];
      if (!n.label) continue;

      const [sx, sy] = viewTransform.worldToScreen(n.x, n.y);

      // Label shadow for readability
      this.ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
      this.ctx.fillText(n.label, sx + 1, sy + n.radius + 5);

      // Label text
      this.ctx.fillStyle = n.selected ? '#FFD700' : '#E0E0E0';
      this.ctx.fillText(n.label, sx, sy + n.radius + 4);
    }
  }
}
```

---

## 6. Viewport Management

### 6.1 View Transform

```javascript
class ViewTransform {
  constructor(width, height) {
    this.width = width;
    this.height = height;
    this.panX = 0;
    this.panY = 0;
    this.zoom = 1.0;
    this.targetPanX = 0;
    this.targetPanY = 0;
    this.targetZoom = 1.0;
    this.inertiaVX = 0;
    this.inertiaVY = 0;
  }

  worldToScreen(wx, wy) {
    return [
      (wx - this.panX) * this.zoom + this.width / 2,
      (wy - this.panY) * this.zoom + this.height / 2,
    ];
  }

  screenToWorld(sx, sy) {
    return [
      (sx - this.width / 2) / this.zoom + this.panX,
      (sy - this.height / 2) / this.zoom + this.panY,
    ];
  }

  /**
   * Returns the world-space bounding rectangle of the current viewport.
   */
  getViewportBounds() {
    const [x0, y0] = this.screenToWorld(0, 0);
    const [x1, y1] = this.screenToWorld(this.width, this.height);
    return { x0, y0, x1, y1 };
  }

  /**
   * Smooth animation toward target pan/zoom with inertia.
   */
  animate(dt) {
    const ease = 1.0 - Math.exp(-8 * dt); // Exponential ease-out

    this.panX += (this.targetPanX - this.panX) * ease + this.inertiaVX * dt;
    this.panY += (this.targetPanY - this.panY) * ease + this.inertiaVY * dt;
    this.zoom += (this.targetZoom - this.zoom) * ease;

    // Decay inertia
    this.inertiaVX *= 0.95;
    this.inertiaVY *= 0.95;
    if (Math.abs(this.inertiaVX) < 0.01) this.inertiaVX = 0;
    if (Math.abs(this.inertiaVY) < 0.01) this.inertiaVY = 0;

    // Clamp zoom
    this.zoom = Math.max(0.01, Math.min(50, this.zoom));
  }

  /**
   * Zoom centered on a screen point (mouse/touch position).
   */
  zoomAt(screenX, screenY, factor) {
    const [worldX, worldY] = this.screenToWorld(screenX, screenY);
    this.targetZoom *= factor;
    this.targetZoom = Math.max(0.01, Math.min(50, this.targetZoom));
    // Adjust pan so the point under the cursor stays fixed
    this.targetPanX = worldX - (screenX - this.width / 2) / this.targetZoom;
    this.targetPanY = worldY - (screenY - this.height / 2) / this.targetZoom;
  }

  /**
   * Generates a 3×3 view matrix for the GPU.
   */
  toMatrix3() {
    return new Float32Array([
      this.zoom, 0,         0,
      0,         this.zoom, 0,
      -this.panX * this.zoom + this.width / 2,
      -this.panY * this.zoom + this.height / 2,
      1,
    ]);
  }
}
```

### 6.2 GPU Hit Testing

Hit testing runs on the CPU using the quadtree — no GPU readback needed:

```javascript
function hitTest(screenX, screenY, nodes, visibleIndices, viewTransform) {
  const [worldX, worldY] = viewTransform.screenToWorld(screenX, screenY);

  let closest = -1;
  let closestDist = Infinity;

  for (const idx of visibleIndices) {
    const n = nodes[idx];
    const dx = worldX - n.x;
    const dy = worldY - n.y;
    const dist = dx * dx + dy * dy;
    const radius = (n.radius ?? 8) + 2; // 2px hit margin

    if (dist < radius * radius && dist < closestDist) {
      closestDist = dist;
      closest = idx;
    }
  }

  return closest;
}
```

### 6.3 Minimap

A minimap renders the entire graph in a small corner viewport:

```javascript
class Minimap {
  constructor(canvas, size = 150) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.size = size;
    canvas.width = size;
    canvas.height = size;
  }

  render(nodes, viewTransform, graphBounds) {
    const ctx = this.ctx;
    const s = this.size;
    ctx.clearRect(0, 0, s, s);

    // Background
    ctx.fillStyle = 'rgba(10, 10, 20, 0.8)';
    ctx.fillRect(0, 0, s, s);

    // Map graph bounds to minimap
    const { x0, y0, x1, y1 } = graphBounds;
    const gw = x1 - x0 || 1;
    const gh = y1 - y0 || 1;
    const scale = (s - 10) / Math.max(gw, gh);

    // Draw nodes as tiny dots
    ctx.fillStyle = 'rgba(100, 180, 255, 0.6)';
    for (const n of nodes) {
      const mx = (n.x - x0) * scale + 5;
      const my = (n.y - y0) * scale + 5;
      ctx.fillRect(mx, my, 2, 2);
    }

    // Draw viewport rectangle
    const vp = viewTransform.getViewportBounds();
    const vx = (vp.x0 - x0) * scale + 5;
    const vy = (vp.y0 - y0) * scale + 5;
    const vw = (vp.x1 - vp.x0) * scale;
    const vh = (vp.y1 - vp.y0) * scale;

    ctx.strokeStyle = 'rgba(255, 200, 50, 0.9)';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(vx, vy, vw, vh);

    // Border
    ctx.strokeStyle = 'rgba(60, 60, 80, 0.8)';
    ctx.lineWidth = 1;
    ctx.strokeRect(0, 0, s, s);
  }
}
```

---

## 7. Performance Optimization

### 7.1 Performance Budget Table

| Operation                    | Budget (10K) | Budget (100K) | Technique                        |
|------------------------------|-------------|---------------|----------------------------------|
| Force tick (all forces)      | < 2 ms      | < 16 ms       | GPU compute shaders              |
| Bounds computation           | < 0.1 ms    | < 0.5 ms      | Parallel reduction               |
| Quadtree build               | < 0.3 ms    | < 2 ms        | GPU radix sort + parallel build  |
| Barnes-Hut charge            | < 0.5 ms    | < 5 ms        | O(n log n) GPU tree walk         |
| Link springs                 | < 0.2 ms    | < 2 ms        | Per-link parallel compute        |
| Collision detection          | < 0.3 ms    | < 3 ms        | Spatial hash grid                |
| Integration                  | < 0.1 ms    | < 1 ms        | Per-node parallel                |
| Render frame (nodes)         | < 2 ms      | < 4 ms        | Instanced SDF drawing            |
| Render frame (links)         | < 1 ms      | < 3 ms        | Instanced quad lines             |
| Render frame (labels)        | < 1 ms      | < 2 ms        | Canvas overlay, budget-limited   |
| Hit test                     | < 0.5 ms    | < 1 ms        | CPU quadtree                     |
| Viewport query               | < 0.2 ms    | < 0.5 ms      | CPU quadtree range query         |
| Zoom/pan transition          | < 1 ms      | < 1 ms        | Smooth uniform update            |
| GPU ↔ CPU position readback  | < 2 ms      | < 5 ms        | Async staging buffer + mapAsync  |
| LOD recalculation            | < 0.1 ms    | < 0.1 ms      | Single zoom threshold check      |
| Total frame time             | < 6 ms      | < 16 ms       | All above combined               |

### 7.2 Frame Timing & Adaptive Quality

```javascript
class FrameTimer {
  constructor() {
    this.history = new Float64Array(120); // Last 120 frames
    this.idx = 0;
    this.avgMs = 16.67; // Initial guess: 60 fps
    this.adaptiveLevel = 1.0; // 1.0 = full quality, 0.0 = minimum
  }

  begin() {
    this._start = performance.now();
  }

  end() {
    const elapsed = performance.now() - this._start;
    this.history[this.idx % 120] = elapsed;
    this.idx++;

    // Running average of last 60 frames
    const count = Math.min(this.idx, 60);
    let sum = 0;
    for (let i = 0; i < count; i++) {
      sum += this.history[(this.idx - 1 - i) % 120];
    }
    this.avgMs = sum / count;

    // Adaptive quality control
    if (this.avgMs > 20) {
      // Below 50 FPS — reduce quality
      this.adaptiveLevel = Math.max(0.0, this.adaptiveLevel - 0.05);
    } else if (this.avgMs < 12) {
      // Above 80 FPS — increase quality
      this.adaptiveLevel = Math.min(1.0, this.adaptiveLevel + 0.02);
    }
  }

  get fps() { return 1000 / this.avgMs; }

  /**
   * Adaptive quality actions based on current level:
   * 1.0: Full SDF + glow + all links + max labels
   * 0.7: SDF without glow + reduced links + fewer labels
   * 0.4: Simple circles + thin links + cluster labels only
   * 0.0: Dots only + no links + no labels (emergency mode)
   */
  getQualitySettings() {
    const q = this.adaptiveLevel;
    return {
      nodeShape:       q > 0.5 ? 'full-sdf' : (q > 0.2 ? 'simple' : 'dot'),
      glowEnabled:     q > 0.7,
      linkOpacity:     Math.min(1.0, q + 0.3),
      linkArrows:      q > 0.6,
      labelBudget:     Math.floor(200 * q),
      msaaEnabled:     q > 0.8,
      collisionActive: q > 0.3,
    };
  }
}
```

### 7.3 GPU Memory Budget Tracking

```javascript
class GPUMemoryTracker {
  constructor(device) {
    this.device = device;
    this.allocations = new Map();
    this.totalBytes = 0;
    this.budgetBytes = 256 * 1024 * 1024; // 256 MB budget
  }

  track(label, buffer, size) {
    this.allocations.set(label, { buffer, size });
    this.totalBytes += size;

    if (this.totalBytes > this.budgetBytes) {
      console.warn(`[GPU Memory] Budget exceeded: ${this.formatBytes(this.totalBytes)} / ${this.formatBytes(this.budgetBytes)}`);
    }
  }

  formatBytes(b) {
    if (b < 1024) return `${b} B`;
    if (b < 1048576) return `${(b / 1024).toFixed(1)} KB`;
    return `${(b / 1048576).toFixed(1)} MB`;
  }

  report() {
    console.log(`[GPU Memory] Total: ${this.formatBytes(this.totalBytes)}`);
    for (const [label, info] of this.allocations) {
      console.log(`  ${label}: ${this.formatBytes(info.size)}`);
    }
  }

  /**
   * Per-graph-size memory estimates:
   *
   *  1K nodes:   ~0.5 MB (nodes + links + quadtree + uniforms)
   * 10K nodes:   ~5 MB
   * 50K nodes:  ~25 MB
   * 100K nodes: ~50 MB (within budget)
   * 200K nodes: ~100 MB (approaching limit — consider paging)
   */
  estimateForNodeCount(nodeCount, linkCount) {
    const nodesMem = nodeCount * NODE_STRIDE * 2;  // Ping-pong
    const linksMem = linkCount * LINK_STRIDE;
    const quadMem  = nodeCount * 2 * QUAD_STRIDE;
    const forcesMem = nodeCount * 8; // vec2f per node
    const stagingMem = nodeCount * NODE_STRIDE;
    const instanceMem = nodeCount * 48; // render instance
    const linkInstanceMem = linkCount * 48;
    return nodesMem + linksMem + quadMem + forcesMem + stagingMem + instanceMem + linkInstanceMem;
  }
}
```

### 7.4 Workload Reduction When FPS Drops

```javascript
function applyPerformanceDegradation(simulation, renderer, frameTimer) {
  const fps = frameTimer.fps;

  if (fps < 15) {
    // EMERGENCY: Skip force simulation, render dots only
    simulation.pause();
    renderer.setMode('emergency-dots');
    console.warn('[Perf] Emergency mode: simulation paused, dots only');
  } else if (fps < 30) {
    // DEGRADED: Simulate every other frame, reduce LOD
    simulation.setSkipFrames(2);
    renderer.setMaxNodes(Math.floor(renderer.totalNodes * 0.5));
    renderer.setLinkVisibility(false);
    console.warn('[Perf] Degraded: skip frames, reduce nodes');
  } else if (fps < 45) {
    // REDUCED: Disable glow, reduce label budget
    renderer.setGlowEnabled(false);
    renderer.setLabelBudget(50);
    renderer.setLinkArrows(false);
  } else {
    // FULL QUALITY
    simulation.setSkipFrames(1);
    renderer.restoreFullQuality();
  }
}
```

---

## 8. CPU Fallback

### 8.1 Canvas2D Renderer

When neither WebGPU nor WebGL2 is available (older browsers, restricted
environments), fall back to Canvas2D with a reduced node limit.

```javascript
class Canvas2DRenderer {
  constructor(canvas, maxNodes = 5000) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.maxNodes = maxNodes;
  }

  render(nodes, links, viewTransform, lodLevel) {
    const ctx = this.ctx;
    const w = this.canvas.width;
    const h = this.canvas.height;

    ctx.clearRect(0, 0, w, h);
    ctx.save();

    // Apply view transform
    ctx.translate(w / 2, h / 2);
    ctx.scale(viewTransform.zoom, viewTransform.zoom);
    ctx.translate(-viewTransform.panX, -viewTransform.panY);

    // Visible node subset
    const vp = viewTransform.getViewportBounds();
    const visibleNodes = nodes.filter(n =>
      n.x >= vp.x0 && n.x <= vp.x1 && n.y >= vp.y0 && n.y <= vp.y1
    ).slice(0, this.maxNodes);

    const visibleSet = new Set(visibleNodes.map(n => n.id));

    // Draw links
    if (lodLevel.links.visible) {
      ctx.globalAlpha = lodLevel.links.opacity ?? 0.3;
      ctx.lineWidth = (lodLevel.links.width ?? 1) / viewTransform.zoom;
      for (const link of links) {
        if (!visibleSet.has(link.source.id) && !visibleSet.has(link.target.id)) continue;
        ctx.strokeStyle = link.color ?? '#445566';
        ctx.beginPath();
        ctx.moveTo(link.source.x, link.source.y);
        ctx.lineTo(link.target.x, link.target.y);
        ctx.stroke();
      }
    }

    // Draw nodes
    ctx.globalAlpha = 1.0;
    for (const n of visibleNodes) {
      const r = Math.max(n.radius ?? 6, 2 / viewTransform.zoom);
      ctx.fillStyle = n.colorHex ?? '#6699CC';

      ctx.beginPath();
      ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
      ctx.fill();

      // Selection ring
      if (n.selected) {
        ctx.strokeStyle = '#FFD700';
        ctx.lineWidth = 2 / viewTransform.zoom;
        ctx.stroke();
      }
    }

    ctx.restore();
  }
}
```

### 8.2 Simplified Force Simulation (CPU)

```javascript
class CPUForceSimulation {
  constructor(nodes, links) {
    this.nodes = nodes;
    this.links = links;
    this.alpha = 1.0;
    this.alphaDecay = 0.02;
    this.alphaMin = 0.001;
  }

  tick() {
    if (this.alpha < this.alphaMin) return false;

    // Simple O(n²) charge (no Barnes-Hut — CPU can't handle 100K)
    const N = this.nodes.length;
    for (let i = 0; i < N; i++) {
      const ni = this.nodes[i];
      if (ni.fixed) continue;
      let fx = 0, fy = 0;

      // Charge repulsion (limit to 2000 nodes for n² feasibility)
      if (N < 2000) {
        for (let j = 0; j < N; j++) {
          if (i === j) continue;
          const nj = this.nodes[j];
          const dx = ni.x - nj.x;
          const dy = ni.y - nj.y;
          const dist2 = dx * dx + dy * dy + 1;
          const force = -30 * this.alpha / dist2;
          const dist = Math.sqrt(dist2);
          fx += force * dx / dist;
          fy += force * dy / dist;
        }
      }

      // Center gravity
      fx -= ni.x * 0.01 * this.alpha;
      fy -= ni.y * 0.01 * this.alpha;

      ni.vx = (ni.vx + fx) * 0.5;
      ni.vy = (ni.vy + fy) * 0.5;
    }

    // Link springs
    for (const link of this.links) {
      const s = link.source, t = link.target;
      const dx = t.x - s.x;
      const dy = t.y - s.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const force = (dist - (link.distance ?? 30)) * (link.strength ?? 0.3) * this.alpha;
      const fx = force * dx / dist;
      const fy = force * dy / dist;
      if (!s.fixed) { s.vx += fx * 0.5; s.vy += fy * 0.5; }
      if (!t.fixed) { t.vx -= fx * 0.5; t.vy -= fy * 0.5; }
    }

    // Position update
    for (const n of this.nodes) {
      if (n.fixed) continue;
      n.x += n.vx;
      n.y += n.vy;
      n.vx *= 0.5;
      n.vy *= 0.5;
    }

    this.alpha *= (1 - this.alphaDecay);
    return true;
  }
}
```

### 8.3 Progressive Enhancement Strategy

```
┌────────────────────────────────────────────────────────────────┐
│  Feature Detection → Capability Tier                          │
│                                                                │
│  navigator.gpu exists?                                         │
│    ├── YES → requestAdapter() succeeds?                        │
│    │    ├── YES → WebGPU tier (100K+ nodes)                    │
│    │    └── NO  → WebGL2 fallback                              │
│    └── NO  → canvas.getContext('webgl2')?                      │
│         ├── YES → WebGL2 tier (20K nodes, no compute shaders)  │
│         └── NO  → Canvas2D tier (5K nodes, CPU simulation)     │
│                                                                │
│  Each tier loads ONLY the code it needs (dynamic import):      │
│    WebGPU:   gpu-force.js + gpu-render.js + shaders.wgsl       │
│    WebGL2:   webgl-render.js + cpu-force.js                    │
│    Canvas2D: canvas-render.js + cpu-force.js (simplified)      │
└────────────────────────────────────────────────────────────────┘
```

```javascript
async function createRenderer(canvas) {
  // Tier 1: WebGPU
  if (navigator.gpu) {
    try {
      const { WebGPURenderer } = await import('./gpu-render.js');
      const renderer = new WebGPURenderer(canvas);
      if (await renderer.init()) return renderer;
    } catch (e) {
      console.warn('[Renderer] WebGPU failed, trying WebGL2:', e);
    }
  }

  // Tier 2: WebGL2
  const gl = canvas.getContext('webgl2');
  if (gl) {
    const { WebGL2Renderer } = await import('./webgl-render.js');
    return new WebGL2Renderer(canvas, gl);
  }

  // Tier 3: Canvas2D
  return new Canvas2DRenderer(canvas);
}
```

---

## 9. Integration with D3 Force Layout

### 9.1 D3 Data Model Bridge

THEMANBEARPIG uses D3 as the data model owner. The GPU handles physics and
rendering, but D3 manages the graph data structure:

```javascript
class D3GPUBridge {
  constructor(gpuSimulation, d3Simulation) {
    this.gpu = gpuSimulation;
    this.d3 = d3Simulation;
    this.nodes = []; // Shared reference
    this.links = [];
    this.mode = 'gpu'; // 'gpu' | 'cpu' | 'hybrid'
  }

  /**
   * Upload D3 node/link data to GPU buffers.
   * Call once on data change, NOT every frame.
   */
  syncToGPU() {
    const nodeData = new Float32Array(this.nodes.length * 12);
    for (let i = 0; i < this.nodes.length; i++) {
      const n = this.nodes[i];
      const off = i * 12;
      nodeData[off + 0]  = n.x ?? 0;
      nodeData[off + 1]  = n.y ?? 0;
      nodeData[off + 2]  = n.vx ?? 0;
      nodeData[off + 3]  = n.vy ?? 0;
      nodeData[off + 4]  = n.mass ?? 1;
      nodeData[off + 5]  = n.charge ?? -30;
      nodeData[off + 6]  = n.radius ?? 8;
      nodeData[off + 7]  = n.color?.[0] ?? 0.5;
      nodeData[off + 8]  = n.color?.[1] ?? 0.5;
      nodeData[off + 9]  = n.color?.[2] ?? 0.8;
      nodeData[off + 10] = n.shape ?? 0;
      nodeData[off + 11] = n.fx != null ? 1 : 0; // fixed flag
    }
    this.gpu.uploadNodes(nodeData);

    const linkData = new Uint32Array(this.links.length * 4);
    for (let i = 0; i < this.links.length; i++) {
      const l = this.links[i];
      const off = i * 4;
      linkData[off + 0] = typeof l.source === 'object' ? l.source.index : l.source;
      linkData[off + 1] = typeof l.target === 'object' ? l.target.index : l.target;
      // Pack strength and rest length into uint32 (float16 each)
      linkData[off + 2] = packFloat16(l.strength ?? 1);
      linkData[off + 3] = packFloat16(l.distance ?? 30);
    }
    this.gpu.uploadLinks(linkData);
  }

  /**
   * After GPU simulation tick, read positions back and update D3 nodes.
   * Uses async readback — does NOT block the main thread.
   */
  async syncFromGPU() {
    const positions = await this.gpu.readPositions();
    for (let i = 0; i < this.nodes.length; i++) {
      const off = i * 12;
      this.nodes[i].x  = positions[off + 0];
      this.nodes[i].y  = positions[off + 1];
      this.nodes[i].vx = positions[off + 2];
      this.nodes[i].vy = positions[off + 3];
    }
  }

  /**
   * Main animation loop: GPU tick → async readback → D3 update → render.
   */
  startAnimationLoop(renderer, labelManager) {
    const frameTimer = new FrameTimer();

    const loop = async () => {
      frameTimer.begin();

      // 1. GPU force simulation tick
      const running = this.gpu.tick();

      // 2. Async readback (non-blocking)
      if (this.gpu.tickCount % 3 === 0 || !running) {
        // Read back every 3rd frame to reduce GPU→CPU sync overhead
        await this.syncFromGPU();
      }

      // 3. Update quadtree for hit testing / culling
      const quadtree = new ViewportQuadtree();
      quadtree.build(this.nodes);

      // 4. Viewport culling
      const vp = renderer.viewTransform.getViewportBounds();
      const visibleIndices = quadtree.queryViewport(vp.x0, vp.y0, vp.x1, vp.y1);

      // 5. LOD selection
      const lod = getLODLevel(renderer.viewTransform.zoom);

      // 6. GPU render (one draw call for nodes, one for links)
      renderer.render(this.nodes, this.links, visibleIndices, lod);

      // 7. Label overlay (Canvas2D)
      labelManager.update(this.nodes, visibleIndices, lod, renderer.viewTransform);
      labelManager.render(this.nodes, renderer.viewTransform);

      // 8. Adaptive quality
      frameTimer.end();
      applyPerformanceDegradation(this.gpu, renderer, frameTimer);

      // 9. HUD update (FPS, node count, etc.)
      this._updateHUD(frameTimer, visibleIndices.length, lod);

      requestAnimationFrame(loop);
    };

    requestAnimationFrame(loop);
  }

  _updateHUD(frameTimer, visibleCount, lod) {
    // Emit custom event for HUD overlay
    window.dispatchEvent(new CustomEvent('mbp:frame-stats', {
      detail: {
        fps: frameTimer.fps.toFixed(1),
        frameMs: frameTimer.avgMs.toFixed(1),
        totalNodes: this.nodes.length,
        visibleNodes: visibleCount,
        totalLinks: this.links.length,
        lod: lod.name,
        quality: frameTimer.adaptiveLevel.toFixed(2),
        gpuMemory: this.gpu.memoryTracker?.totalBytes ?? 0,
        simAlpha: this.gpu.alpha.toFixed(4),
      },
    }));
  }
}
```

### 9.2 Event Bridge: GPU Hit Testing → D3 Callbacks

```javascript
class EventBridge {
  constructor(canvas, d3Bridge, viewTransform) {
    this.canvas = canvas;
    this.bridge = d3Bridge;
    this.viewTransform = viewTransform;
    this.hoveredNode = null;
    this.selectedNode = null;
    this.dragNode = null;
    this._visibleIndices = [];

    this._bindEvents();
  }

  setVisibleIndices(indices) {
    this._visibleIndices = indices;
  }

  _bindEvents() {
    this.canvas.addEventListener('pointermove', (e) => this._onPointerMove(e));
    this.canvas.addEventListener('pointerdown', (e) => this._onPointerDown(e));
    this.canvas.addEventListener('pointerup', (e) => this._onPointerUp(e));
    this.canvas.addEventListener('wheel', (e) => this._onWheel(e), { passive: false });
  }

  _onPointerMove(e) {
    const rect = this.canvas.getBoundingClientRect();
    const sx = e.clientX - rect.left;
    const sy = e.clientY - rect.top;

    if (this.dragNode !== null) {
      // Drag node — update position directly
      const [wx, wy] = this.viewTransform.screenToWorld(sx, sy);
      const n = this.bridge.nodes[this.dragNode];
      n.fx = wx;
      n.fy = wy;
      n.x = wx;
      n.y = wy;
      this.bridge.gpu.reheat(0.3); // Reheat simulation during drag
      return;
    }

    const hit = hitTest(sx, sy, this.bridge.nodes, this._visibleIndices, this.viewTransform);

    if (hit !== this.hoveredNode) {
      // Hover changed
      if (this.hoveredNode !== null) {
        this.bridge.nodes[this.hoveredNode].hovered = false;
        this.canvas.dispatchEvent(new CustomEvent('mbp:node-unhover', {
          detail: { index: this.hoveredNode },
        }));
      }
      this.hoveredNode = hit;
      if (hit !== -1) {
        this.bridge.nodes[hit].hovered = true;
        this.canvas.style.cursor = 'pointer';
        this.canvas.dispatchEvent(new CustomEvent('mbp:node-hover', {
          detail: { index: hit, node: this.bridge.nodes[hit] },
        }));
      } else {
        this.canvas.style.cursor = 'default';
      }
    }
  }

  _onPointerDown(e) {
    if (this.hoveredNode !== null && this.hoveredNode !== -1) {
      this.dragNode = this.hoveredNode;
      this.selectedNode = this.hoveredNode;
      this.bridge.nodes[this.hoveredNode].selected = true;
      this.canvas.setPointerCapture(e.pointerId);
      this.canvas.dispatchEvent(new CustomEvent('mbp:node-select', {
        detail: { index: this.hoveredNode, node: this.bridge.nodes[this.hoveredNode] },
      }));
    } else {
      // Deselect
      if (this.selectedNode !== null) {
        this.bridge.nodes[this.selectedNode].selected = false;
        this.selectedNode = null;
      }
      // Start pan
      this._panStart = { x: e.clientX, y: e.clientY };
    }
  }

  _onPointerUp(e) {
    if (this.dragNode !== null) {
      const n = this.bridge.nodes[this.dragNode];
      n.fx = null;
      n.fy = null;
      this.dragNode = null;
      this.canvas.releasePointerCapture(e.pointerId);
    }
    this._panStart = null;
  }

  _onWheel(e) {
    e.preventDefault();
    const rect = this.canvas.getBoundingClientRect();
    const sx = e.clientX - rect.left;
    const sy = e.clientY - rect.top;
    const factor = e.deltaY > 0 ? 0.9 : 1.1;
    this.viewTransform.zoomAt(sx, sy, factor);
  }
}
```

---

## 10. Anti-Patterns

### Hard Rules — NEVER Violate These

| # | Anti-Pattern | Why It's Fatal | Correct Approach |
|---|-------------|---------------|------------------|
| 1 | Block main thread with GPU readback | `mapAsync` is async for a reason — blocking freezes the entire UI | Always `await staging.mapAsync()` in an async function; never use synchronous polling loops |
| 2 | Create new GPU buffers per frame | Buffer creation is expensive (~1ms each); rapid allocation fragments GPU memory and triggers GC stalls | Pre-allocate all buffers at startup; reuse via `writeBuffer()` every frame |
| 3 | Render off-screen nodes | Drawing 100K nodes when only 2K are visible wastes 98% of GPU work | Viewport cull with quadtree BEFORE building the instance buffer; only upload visible nodes |
| 4 | Use full detail at far zoom | SDF glow + borders + labels on 1-pixel dots is invisible and wasteful | LOD system is mandatory — switch to dots-only at LOD 0 |
| 5 | Skip WebGPU capability check | Not all browsers/GPUs support WebGPU; hard crash on unsupported hardware | Always: `if (navigator.gpu)` → `requestAdapter()` → null check → fallback chain |
| 6 | Assume GPU memory is unlimited | Integrated GPUs (Vega 8) have 2 GB shared; discrete entry-level may have 2-4 GB | Track allocations via `GPUMemoryTracker`; budget to 256 MB max |
| 7 | Use textured quads for shapes | Textures require UV mapping, atlas management, and look blurry on zoom | SDF functions are resolution-independent, anti-aliased, and cheaper |
| 8 | Synchronize CPU↔GPU unnecessarily | Every `mapAsync` + readback adds 2-5ms latency; doing it every frame doubles frame time | Read back positions every 3rd frame or on demand; most rendering uses GPU-side data directly |
| 9 | Ignore device loss events | GPU devices can be lost due to driver updates, sleep/wake, or crashes — silent failure corrupts all rendering | Always listen to `device.lost`; implement automatic recovery with pipeline rebuild |
| 10 | Draw labels as geometry on GPU | Text rendering in shaders is extremely complex and slow; glyph atlases are fragile | Use a transparent Canvas2D overlay positioned on top of the WebGPU canvas |
| 11 | Process 100K+ nodes without LOD | Even GPU can't do full SDF + glow + labels for 100K nodes at 60 fps | LOD reduces per-node work by 10× at far zoom — mandatory for large graphs |
| 12 | Use if/else branching in inner shader loops | GPU wavefronts execute in lockstep; branches cause divergence where ALL paths execute | Use `select()`, `step()`, `smoothstep()` for branchless selection; batch by shape type |
| 13 | Allocate storage buffers inside animation loop | `createBuffer()` is a heavyweight API call; calling it 60× per second fragments memory | All buffers created once in `init()`; only `writeBuffer()` to update data |
| 14 | Skip the fallback chain | Some users will always be on older hardware; a broken graph is worse than a simple one | WebGPU → WebGL2 → Canvas2D — each tier must be functional, not just present |
| 15 | Hardcode workgroup sizes | Different GPUs have different optimal workgroup sizes (64 on some AMD, 256 on NVIDIA) | Query `device.limits.maxComputeWorkgroupSizeX` and select adaptively |
| 16 | Use `requestAnimationFrame` without frame timing | No visibility into performance problems; can't adapt quality | Always measure frame time; use `FrameTimer` for adaptive quality |
| 17 | Forget to unmap staging buffers | Mapped buffers block subsequent `mapAsync` calls; leads to deadlock | Always call `staging.unmap()` after reading, even on error paths |
| 18 | Mix premultiplied and straight alpha | Compositing artifacts (dark halos, wrong blending) | THEMANBEARPIG uses premultiplied alpha everywhere — canvas config + blend state + shader output |

### Shader Performance Rules

```
DO:
  ✓ Use vec4f operations (SIMD-friendly)
  ✓ Batch nodes by shape type for uniform SDF dispatch
  ✓ Use smoothstep() for anti-aliasing (hardware-accelerated)
  ✓ Compute SDF in fragment shader (per-pixel, resolution-independent)
  ✓ Use workgroupBarrier() for shared memory coordination
  ✓ Clamp forces to prevent simulation explosion

DON'T:
  ✗ Use f64 (not widely supported in WGSL, slow when available)
  ✗ Use dynamic array indexing in hot loops (may defeat optimization)
  ✗ Use discard in vertex shader (not legal in WGSL)
  ✗ Exceed STACK_DEPTH in tree traversal (silent corruption)
  ✗ Use sqrt() when distance² comparison suffices
  ✗ Unroll loops manually — the compiler does it better
```

---

## Appendix A: File Layout for THEMANBEARPIG WebGPU Module

```
build/THEMANBEARPIG/
├── index.html
├── main.js                 # Entry point — init, animation loop
├── gpu/
│   ├── context.js          # GPUContext — device init, fallback chain
│   ├── buffers.js          # GPUBufferManager — pre-allocated buffers
│   ├── pipelines.js        # PipelineFactory — compute + render pipelines
│   ├── memory-tracker.js   # GPUMemoryTracker — allocation budgets
│   └── shaders/
│       ├── force-bounds.wgsl       # Bounding box reduction
│       ├── force-charge.wgsl       # Barnes-Hut charge force
│       ├── force-link.wgsl         # Spring link force
│       ├── force-collision.wgsl    # Spatial hash collision
│       ├── force-center.wgsl       # Center gravity
│       ├── force-integrate.wgsl    # Verlet integration
│       ├── render-nodes.wgsl       # Instanced SDF node shader
│       └── render-links.wgsl       # Instanced link shader
├── simulation/
│   ├── gpu-simulation.js   # GPUForceSimulation orchestrator
│   ├── cpu-simulation.js   # CPUForceSimulation fallback
│   └── d3-bridge.js        # D3GPUBridge — data sync
├── render/
│   ├── gpu-renderer.js     # WebGPU instanced renderer
│   ├── webgl-renderer.js   # WebGL2 fallback renderer
│   ├── canvas-renderer.js  # Canvas2D fallback renderer
│   ├── lod.js              # LOD level manager
│   ├── labels.js           # LabelManager (Canvas overlay)
│   └── minimap.js          # Minimap renderer
├── spatial/
│   ├── quadtree.js         # ViewportQuadtree — culling + hit testing
│   └── viewport.js         # ViewTransform — pan/zoom/inertia
├── interaction/
│   ├── events.js           # EventBridge — pointer/wheel/keyboard
│   └── frame-timer.js      # FrameTimer — adaptive quality
└── data/
    └── graph-loader.js     # Load from litigation_context.db via bridge
```

---

## Appendix B: Browser Compatibility (2025–2026)

| Browser           | WebGPU | WebGL2 | Canvas2D | Notes                        |
|-------------------|--------|--------|----------|------------------------------|
| Chrome 113+       | ✅     | ✅     | ✅       | Full support since May 2023  |
| Edge 113+         | ✅     | ✅     | ✅       | Chromium-based, same as Chrome |
| Firefox 130+      | ✅     | ✅     | ✅       | Nightly → stable 2024       |
| Safari 18+        | ✅     | ✅     | ✅       | WebGPU since macOS Sonoma    |
| Chrome Android    | ⚠️     | ✅     | ✅       | WebGPU behind flag on some   |
| Firefox Android   | ❌     | ✅     | ✅       | No WebGPU yet                |
| Safari iOS 18+    | ✅     | ✅     | ✅       | WebGPU on A15+ chips         |
| pywebview (CEF)   | ⚠️     | ✅     | ✅       | Depends on Chromium version  |

> **THEMANBEARPIG target:** pywebview desktop app with embedded Chromium.
> WebGPU availability depends on the CEF/Chromium version bundled.
> ALWAYS include the Canvas2D fallback for maximum portability.

---

## Appendix C: GPU Hardware Compatibility

| GPU Family                  | WebGPU | Optimal Workgroup | Max Nodes (60fps) |
|-----------------------------|--------|-------------------|-------------------|
| NVIDIA RTX 30xx/40xx/50xx   | ✅     | 256               | 500K+             |
| NVIDIA GTX 10xx/16xx        | ✅     | 256               | 200K+             |
| AMD RX 6xxx/7xxx            | ✅     | 256               | 300K+             |
| AMD Vega 8 (integrated)     | ✅     | 64–128            | 30K–50K           |
| Intel UHD 630               | ✅     | 64                | 15K–25K           |
| Intel Iris Xe               | ✅     | 128               | 50K–80K           |
| Apple M1/M2/M3              | ✅     | 256               | 200K+             |
| Qualcomm Adreno 7xx         | ⚠️     | 64                | 10K–20K           |

> **Andrew's hardware:** AMD Vega 8 (integrated, 2GB shared VRAM).
> Optimal workgroup: 64–128. Realistic ceiling: ~30K–50K nodes at 60fps with full LOD.
> For 100K+ nodes on Vega 8: aggressive LOD + viewport culling is MANDATORY.

---

*END OF SINGULARITY-MBP-APEX-WEBGPU SKILL — TIER-7/APEX*
*Version 1.0.0 — WebGPU compute + SDF rendering + LOD + D3 bridge*
*Target: 100K+ nodes at 60fps with graceful degradation*

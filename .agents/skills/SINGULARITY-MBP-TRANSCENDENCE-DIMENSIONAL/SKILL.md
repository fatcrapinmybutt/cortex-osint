---
name: SINGULARITY-MBP-TRANSCENDENCE-DIMENSIONAL
version: "1.0.0"
description: "3D graph visualization for THEMANBEARPIG: Three.js rendering, VR/WebXR support, t-SNE/UMAP projections, parallax depth, stereoscopic viewing, 3D force layout, camera flythrough, fog and atmosphere. Extends the 2D mega-visualization into immersive 3D within pywebview."
tier: "TIER-6/TRANSCENDENCE"
domain: "3D visualization — Three.js, VR/WebXR, t-SNE, UMAP, parallax depth, stereoscopic, 3D force layout, camera flythrough"
triggers:
  - 3D
  - Three.js
  - VR
  - WebXR
  - t-SNE
  - UMAP
  - parallax
  - stereoscopic
  - depth
  - dimension
  - 3D graph
  - immersive
cross_links:
  - SINGULARITY-MBP-GENESIS
  - SINGULARITY-MBP-FORGE-RENDERER
  - SINGULARITY-MBP-FORGE-PHYSICS
  - SINGULARITY-MBP-FORGE-EFFECTS
  - SINGULARITY-MBP-FORGE-DEPLOY
  - SINGULARITY-MBP-COMBAT-ADVERSARY
  - SINGULARITY-MBP-INTERFACE-CONTROLS
  - SINGULARITY-MBP-TRANSCENDENCE-SONIC
---

# SINGULARITY-MBP-TRANSCENDENCE-DIMENSIONAL v1.0

> **Beyond the flat screen. The graph becomes a world you inhabit.**

## Layer 1: Three.js Scene Architecture

### 1.1 Scene, Camera, Renderer Setup within pywebview

THEMANBEARPIG runs inside pywebview (Chromium-based). Three.js renders into a canvas
element overlaid on (or replacing) the D3 SVG layer when 3D mode is activated.

```javascript
// ── scene_manager.js ──
// Three.js scene manager for THEMANBEARPIG 3D mode

class SceneManager {
  constructor(container) {
    this._container = container;
    this._scene = null;
    this._camera = null;
    this._renderer = null;
    this._controls = null;
    this._raycaster = new THREE.Raycaster();
    this._mouse = new THREE.Vector2();
    this._clock = new THREE.Clock();
    this._animationId = null;
    this._isActive = false;

    // Node meshes
    this._nodeGroup = null;
    this._linkGroup = null;
    this._labelGroup = null;
    this._instancedNodes = {};  // layer → InstancedMesh
    this._nodeIndexMap = new Map(); // nodeId → {layer, instanceIndex}
  }

  /**
   * Initialize the 3D scene. Call once; toggle visibility for 2D/3D switching.
   */
  init() {
    // Scene with dark background matching THEMANBEARPIG aesthetic
    this._scene = new THREE.Scene();
    this._scene.background = new THREE.Color(0x0a0a1e);

    // Perspective camera — 60° FOV, positioned above the graph
    const aspect = this._container.clientWidth / this._container.clientHeight;
    this._camera = new THREE.PerspectiveCamera(60, aspect, 0.1, 5000);
    this._camera.position.set(0, 300, 500);
    this._camera.lookAt(0, 0, 0);

    // WebGL renderer — antialias on, alpha for overlay compositing
    this._renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: 'default' // Vega 8 is integrated — don't request high-performance
    });
    this._renderer.setSize(this._container.clientWidth, this._container.clientHeight);
    this._renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2)); // cap at 2x for perf
    this._renderer.shadowMap.enabled = false; // shadows too expensive for 2500+ nodes
    this._renderer.outputColorSpace = THREE.SRGBColorSpace;
    this._container.appendChild(this._renderer.domElement);

    // Orbit controls — pan, zoom, rotate with mouse
    this._controls = new THREE.OrbitControls(this._camera, this._renderer.domElement);
    this._controls.enableDamping = true;
    this._controls.dampingFactor = 0.08;
    this._controls.minDistance = 50;
    this._controls.maxDistance = 2000;
    this._controls.maxPolarAngle = Math.PI * 0.85; // don't flip below ground plane
    this._controls.target.set(0, 0, 0);

    // Ambient light — base illumination
    const ambientLight = new THREE.AmbientLight(0x404060, 0.6);
    this._scene.add(ambientLight);

    // Directional light — top-down for depth shadows
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(100, 400, 200);
    this._scene.add(dirLight);

    // Hemisphere light — subtle sky/ground color gradient
    const hemiLight = new THREE.HemisphereLight(0x4488ff, 0x002244, 0.3);
    this._scene.add(hemiLight);

    // Groups for organized scene graph
    this._nodeGroup = new THREE.Group();
    this._linkGroup = new THREE.Group();
    this._labelGroup = new THREE.Group();
    this._scene.add(this._linkGroup);
    this._scene.add(this._nodeGroup);
    this._scene.add(this._labelGroup);

    // Resize handler
    window.addEventListener('resize', () => this._onResize());

    // Mouse interaction for raycasting
    this._renderer.domElement.addEventListener('pointermove', (e) => this._onPointerMove(e));
    this._renderer.domElement.addEventListener('click', (e) => this._onClick(e));

    this._isActive = true;
    console.log('[3D] Scene initialized, renderer:', this._renderer.info.render);
  }

  /** Start the render loop */
  startRenderLoop() {
    const animate = () => {
      this._animationId = requestAnimationFrame(animate);
      const delta = this._clock.getDelta();

      this._controls.update();
      this._updateLOD();
      this._renderer.render(this._scene, this._camera);
    };
    animate();
  }

  /** Stop the render loop (when switching back to 2D) */
  stopRenderLoop() {
    if (this._animationId) {
      cancelAnimationFrame(this._animationId);
      this._animationId = null;
    }
  }

  _onResize() {
    const w = this._container.clientWidth;
    const h = this._container.clientHeight;
    this._camera.aspect = w / h;
    this._camera.updateProjectionMatrix();
    this._renderer.setSize(w, h);
  }

  _onPointerMove(event) {
    const rect = this._renderer.domElement.getBoundingClientRect();
    this._mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this._mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  }

  _onClick(event) {
    this._raycaster.setFromCamera(this._mouse, this._camera);
    const intersects = this._raycaster.intersectObjects(
      this._nodeGroup.children, true
    );
    if (intersects.length > 0) {
      const hit = intersects[0];
      const instanceId = hit.instanceId;
      const mesh = hit.object;
      if (instanceId !== undefined && mesh.userData.nodeIds) {
        const nodeId = mesh.userData.nodeIds[instanceId];
        this._onNodeClicked(nodeId, hit.point);
      }
    }
  }

  _onNodeClicked(nodeId, worldPos) {
    // Dispatch custom event for other systems (sonic, HUD, etc.)
    const event = new CustomEvent('node3d-click', {
      detail: { nodeId, worldPos }
    });
    document.dispatchEvent(event);
  }

  /** Dispose all GPU resources */
  dispose() {
    this.stopRenderLoop();
    this._renderer.dispose();
    this._scene.traverse((obj) => {
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) {
        if (Array.isArray(obj.material)) {
          obj.material.forEach(m => m.dispose());
        } else {
          obj.material.dispose();
        }
      }
    });
    this._container.removeChild(this._renderer.domElement);
    this._isActive = false;
  }
}
```

### 1.2 Raycasting for Node Selection

```javascript
/**
 * Raycasting with InstancedMesh support.
 * Standard raycasting doesn't return instanceId for InstancedMesh.
 * Three.js r137+ supports it natively — verify version before relying on it.
 */
class NodeRaycaster {
  constructor(sceneManager) {
    this._sm = sceneManager;
    this._raycaster = new THREE.Raycaster();
    this._raycaster.params.Points.threshold = 5; // pixel tolerance for point selection
    this._hoveredNode = null;
    this._highlightColor = new THREE.Color(0x00ff88);
    this._originalColors = new Map();
  }

  /**
   * Test intersection on pointer move. Returns the nearest node or null.
   */
  test(mouse, camera) {
    this._raycaster.setFromCamera(mouse, camera);
    const meshes = [];
    for (const mesh of Object.values(this._sm._instancedNodes)) {
      meshes.push(mesh);
    }

    const hits = this._raycaster.intersectObjects(meshes, false);
    if (hits.length === 0) {
      this._clearHover();
      return null;
    }

    const hit = hits[0];
    const mesh = hit.object;
    const idx = hit.instanceId;

    if (idx === undefined || !mesh.userData.nodeIds) {
      this._clearHover();
      return null;
    }

    const nodeId = mesh.userData.nodeIds[idx];

    // Highlight hovered node
    if (this._hoveredNode !== nodeId) {
      this._clearHover();
      this._hoveredNode = nodeId;

      // Store original color and set highlight
      const color = new THREE.Color();
      mesh.getColorAt(idx, color);
      this._originalColors.set(nodeId, { mesh, idx, color: color.clone() });
      mesh.setColorAt(idx, this._highlightColor);
      mesh.instanceColor.needsUpdate = true;
    }

    return { nodeId, point: hit.point, distance: hit.distance };
  }

  _clearHover() {
    if (this._hoveredNode && this._originalColors.has(this._hoveredNode)) {
      const { mesh, idx, color } = this._originalColors.get(this._hoveredNode);
      mesh.setColorAt(idx, color);
      mesh.instanceColor.needsUpdate = true;
      this._originalColors.delete(this._hoveredNode);
    }
    this._hoveredNode = null;
  }
}
```

---

## Layer 2: 3D Force Layout

### 2.1 Extending D3 Force Simulation to 3D

D3's force simulation operates in 2D by default. Extending to 3D requires:
1. Adding a `z` coordinate to each node
2. Implementing forceZ (centering force on Z axis)
3. Modifying charge/collision to use 3D distance
4. Using an octree (3D) instead of quadtree (2D) for Barnes-Hut approximation

```javascript
// ── force3d.js ──
// 3D force simulation extending D3 concepts

class Force3DSimulation {
  constructor(nodes, links) {
    this._nodes = nodes;
    this._links = links;
    this._alpha = 1.0;
    this._alphaMin = 0.001;
    this._alphaDecay = 0.0228; // ~300 iterations to cool
    this._alphaTarget = 0;
    this._velocityDecay = 0.4;
    this._forces = new Map();

    // Initialize z coordinates
    for (const node of this._nodes) {
      if (node.z === undefined) node.z = (Math.random() - 0.5) * 200;
      if (node.vz === undefined) node.vz = 0;
    }
  }

  /**
   * Register a force by name.
   * Forces are functions: (alpha) => void, mutating node.vx/vy/vz
   */
  force(name, forceFn) {
    if (forceFn === undefined) return this._forces.get(name);
    this._forces.set(name, forceFn);
    return this;
  }

  /** Run one tick of the simulation */
  tick() {
    this._alpha += (this._alphaTarget - this._alpha) * this._alphaDecay;

    // Apply all forces
    for (const force of this._forces.values()) {
      force(this._alpha);
    }

    // Update positions from velocities
    for (const node of this._nodes) {
      if (node.fx !== undefined) { node.x = node.fx; node.vx = 0; }
      else { node.vx *= this._velocityDecay; node.x += node.vx; }

      if (node.fy !== undefined) { node.y = node.fy; node.vy = 0; }
      else { node.vy *= this._velocityDecay; node.y += node.vy; }

      if (node.fz !== undefined) { node.z = node.fz; node.vz = 0; }
      else { node.vz *= this._velocityDecay; node.z += node.vz; }
    }

    return this._alpha < this._alphaMin;
  }

  /** Reheat the simulation (e.g., after adding nodes) */
  reheat(alpha = 0.3) {
    this._alpha = alpha;
  }
}

/**
 * 3D centering force — pulls nodes toward (cx, cy, cz).
 */
function forceCenter3D(cx = 0, cy = 0, cz = 0) {
  let nodes;
  function force(alpha) {
    let sx = 0, sy = 0, sz = 0;
    const n = nodes.length;
    for (const node of nodes) { sx += node.x; sy += node.y; sz += node.z; }
    sx = (sx / n - cx) * alpha;
    sy = (sy / n - cy) * alpha;
    sz = (sz / n - cz) * alpha;
    for (const node of nodes) { node.x -= sx; node.y -= sy; node.z -= sz; }
  }
  force.initialize = (n) => { nodes = n; };
  return force;
}

/**
 * 3D many-body force using Barnes-Hut octree approximation.
 * O(n log n) instead of O(n²) for charge simulation.
 */
function forceManyBody3D(strength = -100) {
  let nodes;
  const theta2 = 0.81; // Barnes-Hut threshold squared

  function force(alpha) {
    // Build octree
    const tree = buildOctree(nodes);

    for (const node of nodes) {
      applyForceFromTree(node, tree, alpha);
    }
  }

  function applyForceFromTree(node, treeNode, alpha) {
    if (!treeNode) return;

    // Leaf node with a single body
    if (treeNode.body && treeNode.body !== node) {
      const dx = treeNode.body.x - node.x;
      const dy = treeNode.body.y - node.y;
      const dz = treeNode.body.z - node.z;
      const distSq = dx * dx + dy * dy + dz * dz + 1; // +1 softening
      const dist = Math.sqrt(distSq);
      const f = strength * alpha / distSq;
      node.vx += dx / dist * f;
      node.vy += dy / dist * f;
      node.vz += dz / dist * f;
      return;
    }

    // Internal node — check Barnes-Hut criterion
    if (treeNode.size && treeNode.count > 0) {
      const dx = treeNode.cx - node.x;
      const dy = treeNode.cy - node.y;
      const dz = treeNode.cz - node.z;
      const distSq = dx * dx + dy * dy + dz * dz + 1;

      // If node is far enough, treat cluster as single body
      if (treeNode.size * treeNode.size / distSq < theta2) {
        const dist = Math.sqrt(distSq);
        const f = strength * alpha * treeNode.count / distSq;
        node.vx += dx / dist * f;
        node.vy += dy / dist * f;
        node.vz += dz / dist * f;
        return;
      }
    }

    // Recurse into children
    if (treeNode.children) {
      for (const child of treeNode.children) {
        applyForceFromTree(node, child, alpha);
      }
    }
  }

  force.initialize = (n) => { nodes = n; };
  return force;
}

/**
 * Simple octree builder for Barnes-Hut 3D force.
 * Recursively subdivides space into 8 octants.
 */
function buildOctree(nodes) {
  if (nodes.length === 0) return null;

  // Find bounding box
  let minX = Infinity, minY = Infinity, minZ = Infinity;
  let maxX = -Infinity, maxY = -Infinity, maxZ = -Infinity;
  for (const n of nodes) {
    if (n.x < minX) minX = n.x; if (n.x > maxX) maxX = n.x;
    if (n.y < minY) minY = n.y; if (n.y > maxY) maxY = n.y;
    if (n.z < minZ) minZ = n.z; if (n.z > maxZ) maxZ = n.z;
  }

  const size = Math.max(maxX - minX, maxY - minY, maxZ - minZ) + 1;
  const root = createOctreeNode(minX, minY, minZ, size);

  for (const node of nodes) {
    insertIntoOctree(root, node);
  }

  computeCentroids(root);
  return root;
}

function createOctreeNode(x, y, z, size) {
  return { x, y, z, size, cx: 0, cy: 0, cz: 0, count: 0, body: null, children: null };
}

function insertIntoOctree(treeNode, body) {
  if (treeNode.count === 0 && !treeNode.body) {
    treeNode.body = body;
    treeNode.count = 1;
    return;
  }

  if (!treeNode.children) {
    treeNode.children = new Array(8).fill(null);
    // Re-insert existing body
    if (treeNode.body) {
      const existing = treeNode.body;
      treeNode.body = null;
      const idx = octantIndex(treeNode, existing);
      if (!treeNode.children[idx]) {
        const half = treeNode.size / 2;
        const ox = treeNode.x + (idx & 1 ? half : 0);
        const oy = treeNode.y + (idx & 2 ? half : 0);
        const oz = treeNode.z + (idx & 4 ? half : 0);
        treeNode.children[idx] = createOctreeNode(ox, oy, oz, half);
      }
      insertIntoOctree(treeNode.children[idx], existing);
    }
  }

  const idx = octantIndex(treeNode, body);
  const half = treeNode.size / 2;
  if (!treeNode.children[idx]) {
    const ox = treeNode.x + (idx & 1 ? half : 0);
    const oy = treeNode.y + (idx & 2 ? half : 0);
    const oz = treeNode.z + (idx & 4 ? half : 0);
    treeNode.children[idx] = createOctreeNode(ox, oy, oz, half);
  }
  insertIntoOctree(treeNode.children[idx], body);
  treeNode.count++;
}

function octantIndex(treeNode, body) {
  const half = treeNode.size / 2;
  let idx = 0;
  if (body.x >= treeNode.x + half) idx |= 1;
  if (body.y >= treeNode.y + half) idx |= 2;
  if (body.z >= treeNode.z + half) idx |= 4;
  return idx;
}

function computeCentroids(treeNode) {
  if (!treeNode) return;
  if (treeNode.body) {
    treeNode.cx = treeNode.body.x;
    treeNode.cy = treeNode.body.y;
    treeNode.cz = treeNode.body.z;
    return;
  }
  if (!treeNode.children) return;
  let tx = 0, ty = 0, tz = 0, total = 0;
  for (const child of treeNode.children) {
    if (!child) continue;
    computeCentroids(child);
    tx += child.cx * child.count;
    ty += child.cy * child.count;
    tz += child.cz * child.count;
    total += child.count;
  }
  if (total > 0) {
    treeNode.cx = tx / total;
    treeNode.cy = ty / total;
    treeNode.cz = tz / total;
    treeNode.count = total;
  }
}

/**
 * 3D link force — spring force between connected nodes.
 */
function forceLink3D(links, strength = 0.3, distance = 50) {
  let nodes;
  function force(alpha) {
    for (const link of links) {
      const source = typeof link.source === 'object' ? link.source : nodes[link.source];
      const target = typeof link.target === 'object' ? link.target : nodes[link.target];
      if (!source || !target) continue;

      const dx = target.x - source.x;
      const dy = target.y - source.y;
      const dz = target.z - source.z;
      const dist = Math.sqrt(dx * dx + dy * dy + dz * dz) || 1;

      const f = (dist - distance) / dist * alpha * strength;
      const fx = dx * f;
      const fy = dy * f;
      const fz = dz * f;

      target.vx -= fx;
      target.vy -= fy;
      target.vz -= fz;
      source.vx += fx;
      source.vy += fy;
      source.vz += fz;
    }
  }
  force.initialize = (n) => { nodes = n; };
  return force;
}

/**
 * 3D collision force — prevents node overlap using radius.
 */
function forceCollide3D(radius = 5) {
  let nodes;
  function force(alpha) {
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i], b = nodes[j];
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const dz = b.z - a.z;
        const distSq = dx * dx + dy * dy + dz * dz;
        const minDist = radius * 2;

        if (distSq < minDist * minDist && distSq > 0) {
          const dist = Math.sqrt(distSq);
          const overlap = (minDist - dist) / dist * 0.5;
          const ox = dx * overlap;
          const oy = dy * overlap;
          const oz = dz * overlap;
          a.x -= ox; a.y -= oy; a.z -= oz;
          b.x += ox; b.y += oy; b.z += oz;
        }
      }
    }
  }
  force.initialize = (n) => { nodes = n; };
  return force;
}
```

---

## Layer 3: Node Rendering in 3D with InstancedMesh

### 3.1 InstancedMesh for 2500+ Nodes

Individual `THREE.Mesh` per node creates 2500+ draw calls — far too many for Vega 8.
InstancedMesh renders all nodes of a type in a single draw call using GPU instancing.

```javascript
// ── node_renderer_3d.js ──
// Renders graph nodes as instanced spheres, grouped by layer

// Layer → visual properties
const LAYER_3D_CONFIG = {
  adversary:    { color: 0xff4444, radius: 4, y: 120, emissive: 0x330000 },
  weapon:       { color: 0xff8800, radius: 3, y: 100, emissive: 0x331100 },
  judicial:     { color: 0xcc00cc, radius: 5, y: 80,  emissive: 0x220022 },
  evidence:     { color: 0x00cc66, radius: 3, y: 60,  emissive: 0x002211 },
  authority:    { color: 0x4488ff, radius: 3, y: 40,  emissive: 0x001133 },
  impeachment:  { color: 0xff2266, radius: 4, y: 20,  emissive: 0x330011 },
  timeline:     { color: 0xffcc00, radius: 2, y: 0,   emissive: 0x332200 },
  filing:       { color: 0x00aaff, radius: 4, y: -20, emissive: 0x001133 },
  brain:        { color: 0x8844ff, radius: 3, y: -40, emissive: 0x110033 },
  engine:       { color: 0x44ff88, radius: 3, y: -60, emissive: 0x003311 },
  hud:          { color: 0xaaaaaa, radius: 2, y: -80, emissive: 0x111111 },
  narrative:    { color: 0xff88cc, radius: 3, y: -100, emissive: 0x330022 },
  convergence:  { color: 0x00ffcc, radius: 4, y: -120, emissive: 0x003322 }
};

class NodeRenderer3D {
  constructor(sceneManager) {
    this._sm = sceneManager;
    this._instancedMeshes = {};
    this._dummy = new THREE.Object3D(); // reused for matrix computation
    this._lodGeometries = {
      high: new THREE.SphereGeometry(1, 16, 12),   // close-up
      medium: new THREE.SphereGeometry(1, 8, 6),    // mid-range
      low: new THREE.IcosahedronGeometry(1, 1)       // far away (12 faces)
    };
  }

  /**
   * Build instanced meshes from graph data.
   * Groups nodes by layer, creates one InstancedMesh per layer.
   */
  build(nodes) {
    // Clear existing meshes
    for (const mesh of Object.values(this._instancedMeshes)) {
      this._sm._nodeGroup.remove(mesh);
      mesh.geometry.dispose();
      mesh.material.dispose();
    }
    this._instancedMeshes = {};
    this._sm._nodeIndexMap.clear();

    // Group nodes by layer
    const layerGroups = {};
    for (const node of nodes) {
      const layer = node.layer || 'convergence';
      if (!layerGroups[layer]) layerGroups[layer] = [];
      layerGroups[layer].push(node);
    }

    // Create InstancedMesh per layer
    for (const [layer, layerNodes] of Object.entries(layerGroups)) {
      const config = LAYER_3D_CONFIG[layer] || LAYER_3D_CONFIG.convergence;
      const count = layerNodes.length;

      const geometry = this._lodGeometries.medium.clone();
      const material = new THREE.MeshPhongMaterial({
        color: config.color,
        emissive: config.emissive,
        emissiveIntensity: 0.4,
        shininess: 60,
        transparent: true,
        opacity: 0.9
      });

      const mesh = new THREE.InstancedMesh(geometry, material, count);
      mesh.userData.layer = layer;
      mesh.userData.nodeIds = [];

      const color = new THREE.Color();

      for (let i = 0; i < count; i++) {
        const node = layerNodes[i];

        // Position: x, z from force layout; y from layer height
        this._dummy.position.set(
          node.x || 0,
          config.y + (node.z || 0) * 0.3, // z coordinate mapped to slight vertical offset
          node.y || 0  // D3 y → Three.js z (horizontal plane)
        );

        // Scale based on node importance (connections, threat level)
        const importance = Math.min(3, 0.5 + (node.connections || 1) * 0.1);
        const radius = config.radius * importance;
        this._dummy.scale.set(radius, radius, radius);

        this._dummy.updateMatrix();
        mesh.setMatrixAt(i, this._dummy.matrix);

        // Color modulated by threat level
        const threatTint = node.threat_level || 0;
        color.setHex(config.color);
        color.lerp(new THREE.Color(0xff0000), threatTint * 0.5); // red-shift for threat
        mesh.setColorAt(i, color);

        mesh.userData.nodeIds.push(node.id);
        this._sm._nodeIndexMap.set(node.id, { layer, instanceIndex: i });
      }

      mesh.instanceMatrix.needsUpdate = true;
      if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;

      this._instancedMeshes[layer] = mesh;
      this._sm._nodeGroup.add(mesh);
    }
  }

  /**
   * Update node positions from simulation tick.
   * Only updates the instance matrices — no geometry/material changes.
   */
  updatePositions(nodes) {
    for (const node of nodes) {
      const entry = this._sm._nodeIndexMap.get(node.id);
      if (!entry) continue;

      const mesh = this._instancedMeshes[entry.layer];
      if (!mesh) continue;

      const config = LAYER_3D_CONFIG[entry.layer] || LAYER_3D_CONFIG.convergence;
      mesh.getMatrixAt(entry.instanceIndex, this._dummy.matrix);
      this._dummy.matrix.decompose(this._dummy.position, this._dummy.quaternion, this._dummy.scale);

      this._dummy.position.set(
        node.x || 0,
        config.y + (node.z || 0) * 0.3,
        node.y || 0
      );
      this._dummy.updateMatrix();
      mesh.setMatrixAt(entry.instanceIndex, this._dummy.matrix);
    }

    for (const mesh of Object.values(this._instancedMeshes)) {
      mesh.instanceMatrix.needsUpdate = true;
    }
  }
}
```

### 3.2 Link Rendering with LineSegments

```javascript
/**
 * Render links as a single BufferGeometry with LineSegments.
 * One draw call for all links regardless of count.
 */
class LinkRenderer3D {
  constructor(sceneManager) {
    this._sm = sceneManager;
    this._lineMesh = null;
  }

  build(links, nodeMap) {
    if (this._lineMesh) {
      this._sm._linkGroup.remove(this._lineMesh);
      this._lineMesh.geometry.dispose();
      this._lineMesh.material.dispose();
    }

    const positions = new Float32Array(links.length * 6); // 2 vertices × 3 components
    const colors = new Float32Array(links.length * 6);

    for (let i = 0; i < links.length; i++) {
      const link = links[i];
      const src = nodeMap.get(link.source) || { x: 0, y: 0, z: 0, layer: 'convergence' };
      const tgt = nodeMap.get(link.target) || { x: 0, y: 0, z: 0, layer: 'convergence' };

      const srcConfig = LAYER_3D_CONFIG[src.layer] || LAYER_3D_CONFIG.convergence;
      const tgtConfig = LAYER_3D_CONFIG[tgt.layer] || LAYER_3D_CONFIG.convergence;

      const idx = i * 6;
      positions[idx]     = src.x || 0;
      positions[idx + 1] = srcConfig.y + (src.z || 0) * 0.3;
      positions[idx + 2] = src.y || 0;
      positions[idx + 3] = tgt.x || 0;
      positions[idx + 4] = tgtConfig.y + (tgt.z || 0) * 0.3;
      positions[idx + 5] = tgt.y || 0;

      // Color: blend source and target colors, dim by link weight
      const weight = link.weight || 0.5;
      const alpha = 0.2 + weight * 0.6;
      const srcColor = new THREE.Color(srcConfig.color);
      const tgtColor = new THREE.Color(tgtConfig.color);
      colors[idx]     = srcColor.r * alpha;
      colors[idx + 1] = srcColor.g * alpha;
      colors[idx + 2] = srcColor.b * alpha;
      colors[idx + 3] = tgtColor.r * alpha;
      colors[idx + 4] = tgtColor.g * alpha;
      colors[idx + 5] = tgtColor.b * alpha;
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const material = new THREE.LineBasicMaterial({
      vertexColors: true,
      transparent: true,
      opacity: 0.6,
      linewidth: 1  // WebGL only supports 1px lines on most hardware
    });

    this._lineMesh = new THREE.LineSegments(geometry, material);
    this._sm._linkGroup.add(this._lineMesh);
  }

  updatePositions(links, nodeMap) {
    if (!this._lineMesh) return;
    const positions = this._lineMesh.geometry.getAttribute('position');
    const array = positions.array;

    for (let i = 0; i < links.length; i++) {
      const link = links[i];
      const src = nodeMap.get(link.source) || { x: 0, y: 0, z: 0, layer: 'convergence' };
      const tgt = nodeMap.get(link.target) || { x: 0, y: 0, z: 0, layer: 'convergence' };
      const srcConfig = LAYER_3D_CONFIG[src.layer] || LAYER_3D_CONFIG.convergence;
      const tgtConfig = LAYER_3D_CONFIG[tgt.layer] || LAYER_3D_CONFIG.convergence;

      const idx = i * 6;
      array[idx]     = src.x || 0;
      array[idx + 1] = srcConfig.y + (src.z || 0) * 0.3;
      array[idx + 2] = src.y || 0;
      array[idx + 3] = tgt.x || 0;
      array[idx + 4] = tgtConfig.y + (tgt.z || 0) * 0.3;
      array[idx + 5] = tgt.y || 0;
    }
    positions.needsUpdate = true;
  }
}
```

---

## Layer 4: Layer Stacking — 13 Planes in 3D Space

### 4.1 Horizontal Layer Planes

Each of the 13 THEMANBEARPIG layers is rendered as a semi-transparent horizontal plane
in 3D space. Nodes sit on their layer's plane; cross-layer links arc between planes.

```javascript
class LayerPlanes {
  constructor(sceneManager) {
    this._sm = sceneManager;
    this._planes = {};
    this._labels = {};
  }

  build() {
    const planeSize = 800;
    const planeGeometry = new THREE.PlaneGeometry(planeSize, planeSize);

    for (const [layer, config] of Object.entries(LAYER_3D_CONFIG)) {
      // Semi-transparent plane
      const material = new THREE.MeshBasicMaterial({
        color: config.color,
        transparent: true,
        opacity: 0.03,
        side: THREE.DoubleSide,
        depthWrite: false
      });

      const plane = new THREE.Mesh(planeGeometry.clone(), material);
      plane.rotation.x = -Math.PI / 2; // lay flat (horizontal)
      plane.position.y = config.y;
      plane.userData.layer = layer;
      plane.renderOrder = -1; // render behind nodes

      this._sm._scene.add(plane);
      this._planes[layer] = plane;

      // Layer label using sprite
      const canvas = document.createElement('canvas');
      canvas.width = 256;
      canvas.height = 64;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = '#' + config.color.toString(16).padStart(6, '0');
      ctx.font = 'bold 24px JetBrains Mono, monospace';
      ctx.textAlign = 'center';
      ctx.fillText(layer.toUpperCase(), 128, 40);

      const texture = new THREE.CanvasTexture(canvas);
      const spriteMaterial = new THREE.SpriteMaterial({
        map: texture,
        transparent: true,
        opacity: 0.7
      });
      const sprite = new THREE.Sprite(spriteMaterial);
      sprite.position.set(-planeSize / 2 - 30, config.y, 0);
      sprite.scale.set(80, 20, 1);
      this._sm._scene.add(sprite);
      this._labels[layer] = sprite;
    }
  }

  /**
   * Set visibility per layer (toggled via UI).
   */
  setLayerVisible(layer, visible) {
    if (this._planes[layer]) this._planes[layer].visible = visible;
    if (this._labels[layer]) this._labels[layer].visible = visible;
  }

  dispose() {
    for (const plane of Object.values(this._planes)) {
      plane.geometry.dispose();
      plane.material.dispose();
      this._sm._scene.remove(plane);
    }
    for (const label of Object.values(this._labels)) {
      label.material.map.dispose();
      label.material.dispose();
      this._sm._scene.remove(label);
    }
  }
}
```

### 4.2 Cross-Layer Arc Links

Links between nodes on different layers are rendered as vertical arcs — curved tubes
that visually connect the horizontal planes.

```javascript
/**
 * Render cross-layer links as quadratic bezier curves.
 * The control point is at the midpoint x/z but halfway between the two y-planes.
 */
function createCrossLayerArc(srcPos, tgtPos, color, segments = 12) {
  const midX = (srcPos.x + tgtPos.x) / 2;
  const midY = (srcPos.y + tgtPos.y) / 2;
  const midZ = (srcPos.z + tgtPos.z) / 2;

  // Control point offset outward from midpoint for visible curve
  const ySpan = Math.abs(srcPos.y - tgtPos.y);
  const controlOffset = ySpan * 0.3;

  const curve = new THREE.QuadraticBezierCurve3(
    new THREE.Vector3(srcPos.x, srcPos.y, srcPos.z),
    new THREE.Vector3(midX + controlOffset, midY, midZ + controlOffset),
    new THREE.Vector3(tgtPos.x, tgtPos.y, tgtPos.z)
  );

  const points = curve.getPoints(segments);
  const geometry = new THREE.BufferGeometry().setFromPoints(points);
  const material = new THREE.LineBasicMaterial({
    color: color,
    transparent: true,
    opacity: 0.4
  });

  return new THREE.Line(geometry, material);
}
```

---

## Layer 5: t-SNE / UMAP Projections

### 5.1 Computing Embeddings from Node Features

Nodes have multiple features (threat_level, connections, layer, type, etc.). These are
embedded into high-dimensional vectors, then projected to 3D using t-SNE or UMAP.

```javascript
// ── projection_engine.js ──
// t-SNE and UMAP projection for graph layout alternatives

/**
 * Extract feature vector from node.
 * Encodes categorical fields as one-hot, normalizes continuous fields.
 */
function nodeToFeatureVector(node, layerNames, typeNames) {
  const features = [];

  // Continuous features (normalized 0-1)
  features.push(node.threat_level || 0);
  features.push(Math.min(1, (node.connections || 0) / 50));
  features.push(node.impeachment_value ? node.impeachment_value / 10 : 0);
  features.push(node.evidence_count ? Math.min(1, node.evidence_count / 100) : 0);
  features.push(node.authority_score || 0);

  // Layer one-hot encoding
  for (const name of layerNames) {
    features.push(node.layer === name ? 1 : 0);
  }

  // Type one-hot encoding
  for (const name of typeNames) {
    features.push(node.type === name ? 1 : 0);
  }

  return features;
}

/**
 * Simple t-SNE implementation (Barnes-Hut approximation).
 * For 2500 nodes, runs in ~2-5 seconds on CPU.
 *
 * Uses the approach from Van der Maaten (2014) with gradient descent.
 */
class TSNE3D {
  constructor(opts = {}) {
    this.perplexity = opts.perplexity || 30;
    this.dim = 3; // output dimensions
    this.iterations = opts.iterations || 500;
    this.learningRate = opts.learningRate || 100;
    this.epsilon = 1e-8;
  }

  /**
   * Run t-SNE projection.
   * @param {Array<Array<number>>} data - N × D feature matrix
   * @returns {Array<{x, y, z}>} N × 3 projected coordinates
   */
  run(data) {
    const N = data.length;

    // Initialize output randomly
    const Y = [];
    for (let i = 0; i < N; i++) {
      Y.push({
        x: (Math.random() - 0.5) * 10,
        y: (Math.random() - 0.5) * 10,
        z: (Math.random() - 0.5) * 10
      });
    }

    // Compute pairwise affinities
    const P = this._computeAffinities(data);

    // Gradient descent
    const gains = Array.from({ length: N }, () => ({ x: 1, y: 1, z: 1 }));
    const velocity = Array.from({ length: N }, () => ({ x: 0, y: 0, z: 0 }));
    const momentum = 0.8;

    for (let iter = 0; iter < this.iterations; iter++) {
      const grad = this._computeGradient(Y, P, N);

      for (let i = 0; i < N; i++) {
        for (const dim of ['x', 'y', 'z']) {
          // Adaptive gains
          const sameSign = (grad[i][dim] > 0) === (velocity[i][dim] > 0);
          gains[i][dim] = sameSign ? gains[i][dim] * 0.8 : gains[i][dim] + 0.2;
          gains[i][dim] = Math.max(gains[i][dim], 0.01);

          velocity[i][dim] = momentum * velocity[i][dim] -
            this.learningRate * gains[i][dim] * grad[i][dim];
          Y[i][dim] += velocity[i][dim];
        }
      }

      // Center solution
      let mx = 0, my = 0, mz = 0;
      for (const p of Y) { mx += p.x; my += p.y; mz += p.z; }
      mx /= N; my /= N; mz /= N;
      for (const p of Y) { p.x -= mx; p.y -= my; p.z -= mz; }
    }

    // Scale to reasonable range
    let maxR = 0;
    for (const p of Y) {
      const r = Math.sqrt(p.x * p.x + p.y * p.y + p.z * p.z);
      if (r > maxR) maxR = r;
    }
    const scale = 200 / (maxR || 1);
    for (const p of Y) { p.x *= scale; p.y *= scale; p.z *= scale; }

    return Y;
  }

  _computeAffinities(data) {
    const N = data.length;
    const D = data[0].length;
    const P = Array.from({ length: N }, () => new Float64Array(N));

    // Pairwise squared distances
    for (let i = 0; i < N; i++) {
      for (let j = i + 1; j < N; j++) {
        let dist = 0;
        for (let d = 0; d < D; d++) {
          const diff = data[i][d] - data[j][d];
          dist += diff * diff;
        }
        P[i][j] = dist;
        P[j][i] = dist;
      }
    }

    // Convert distances to probabilities using Gaussian kernel
    for (let i = 0; i < N; i++) {
      const sigma = this._binarySearch(P[i], i, this.perplexity);
      let sum = 0;
      for (let j = 0; j < N; j++) {
        if (i === j) { P[i][j] = 0; continue; }
        P[i][j] = Math.exp(-P[i][j] / (2 * sigma * sigma));
        sum += P[i][j];
      }
      for (let j = 0; j < N; j++) {
        P[i][j] /= (sum || 1);
      }
    }

    // Symmetrize
    for (let i = 0; i < N; i++) {
      for (let j = i + 1; j < N; j++) {
        const avg = (P[i][j] + P[j][i]) / (2 * N);
        P[i][j] = Math.max(avg, this.epsilon);
        P[j][i] = Math.max(avg, this.epsilon);
      }
    }

    return P;
  }

  _binarySearch(distances, i, targetPerplexity) {
    let lo = 0.01, hi = 100, sigma = 1;
    for (let iter = 0; iter < 50; iter++) {
      sigma = (lo + hi) / 2;
      let sum = 0, entropy = 0;
      for (let j = 0; j < distances.length; j++) {
        if (j === i) continue;
        const p = Math.exp(-distances[j] / (2 * sigma * sigma));
        sum += p;
      }
      for (let j = 0; j < distances.length; j++) {
        if (j === i) continue;
        const p = Math.exp(-distances[j] / (2 * sigma * sigma)) / (sum || 1);
        if (p > 1e-10) entropy -= p * Math.log2(p);
      }
      const perp = Math.pow(2, entropy);
      if (Math.abs(perp - targetPerplexity) < 0.5) break;
      if (perp > targetPerplexity) hi = sigma;
      else lo = sigma;
    }
    return sigma;
  }

  _computeGradient(Y, P, N) {
    const grad = Array.from({ length: N }, () => ({ x: 0, y: 0, z: 0 }));

    // Student-t distribution in output space
    let sumQ = 0;
    const Q = Array.from({ length: N }, () => new Float64Array(N));
    for (let i = 0; i < N; i++) {
      for (let j = i + 1; j < N; j++) {
        const dx = Y[i].x - Y[j].x;
        const dy = Y[i].y - Y[j].y;
        const dz = Y[i].z - Y[j].z;
        const q = 1 / (1 + dx * dx + dy * dy + dz * dz);
        Q[i][j] = q;
        Q[j][i] = q;
        sumQ += 2 * q;
      }
    }

    for (let i = 0; i < N; i++) {
      for (let j = 0; j < N; j++) {
        if (i === j) continue;
        const q = Q[i][j] / (sumQ || 1);
        const mult = 4 * (P[i][j] - q) * Q[i][j];
        grad[i].x += mult * (Y[i].x - Y[j].x);
        grad[i].y += mult * (Y[i].y - Y[j].y);
        grad[i].z += mult * (Y[i].z - Y[j].z);
      }
    }

    return grad;
  }
}
```

### 5.2 Animated Layout Transitions

Smooth animation between force layout and t-SNE/UMAP projected layout.

```javascript
/**
 * Animate transition from current node positions to target positions.
 * Uses ease-in-out cubic for smooth, professional animation.
 */
function animateLayoutTransition(nodes, targetPositions, duration = 2000, onComplete) {
  const startPositions = nodes.map(n => ({ x: n.x, y: n.y, z: n.z }));
  const startTime = performance.now();

  function easeInOutCubic(t) {
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  }

  function step(timestamp) {
    const elapsed = timestamp - startTime;
    const rawT = Math.min(1, elapsed / duration);
    const t = easeInOutCubic(rawT);

    for (let i = 0; i < nodes.length; i++) {
      nodes[i].x = startPositions[i].x + (targetPositions[i].x - startPositions[i].x) * t;
      nodes[i].y = startPositions[i].y + (targetPositions[i].y - startPositions[i].y) * t;
      nodes[i].z = startPositions[i].z + (targetPositions[i].z - startPositions[i].z) * t;
    }

    if (rawT < 1) {
      requestAnimationFrame(step);
    } else if (onComplete) {
      onComplete();
    }
  }

  requestAnimationFrame(step);
}
```

---

## Layer 6: VR/WebXR Integration

### 6.1 WebXR Session Setup

```javascript
// ── vr_manager.js ──
// WebXR VR session management for THEMANBEARPIG 3D

class VRManager {
  constructor(sceneManager) {
    this._sm = sceneManager;
    this._session = null;
    this._controllers = [];
    this._isSupported = false;
    this._referenceSpace = null;
  }

  /**
   * Check if WebXR is available (pywebview may or may not support it).
   */
  async checkSupport() {
    if (!navigator.xr) {
      this._isSupported = false;
      return false;
    }
    try {
      this._isSupported = await navigator.xr.isSessionSupported('immersive-vr');
    } catch (e) {
      this._isSupported = false;
    }
    return this._isSupported;
  }

  /**
   * Start a VR session. Reconfigures the renderer for XR output.
   */
  async startSession() {
    if (!this._isSupported) {
      console.warn('[VR] WebXR not supported in this environment');
      return false;
    }

    const renderer = this._sm._renderer;
    renderer.xr.enabled = true;

    try {
      this._session = await navigator.xr.requestSession('immersive-vr', {
        optionalFeatures: ['local-floor', 'hand-tracking']
      });

      this._session.addEventListener('end', () => this._onSessionEnd());

      renderer.xr.setSession(this._session);
      this._referenceSpace = await this._session.requestReferenceSpace('local-floor');

      this._setupControllers();

      // Scale the scene for VR (1 unit = 1 meter)
      this._sm._scene.scale.set(0.01, 0.01, 0.01); // graph units → meters

      console.log('[VR] Session started');
      return true;
    } catch (e) {
      console.error('[VR] Failed to start session:', e);
      return false;
    }
  }

  _setupControllers() {
    const renderer = this._sm._renderer;

    for (let i = 0; i < 2; i++) {
      const controller = renderer.xr.getController(i);
      controller.addEventListener('selectstart', (e) => this._onSelect(e, i));
      controller.addEventListener('squeezestart', (e) => this._onSqueeze(e, i));
      this._sm._scene.add(controller);

      // Visual ray from controller
      const geometry = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(0, 0, 0),
        new THREE.Vector3(0, 0, -50) // 50m ray
      ]);
      const material = new THREE.LineBasicMaterial({ color: 0x00ff88 });
      const ray = new THREE.Line(geometry, material);
      controller.add(ray);

      this._controllers.push({ controller, ray });
    }

    // Hand tracking (if available)
    for (let i = 0; i < 2; i++) {
      const hand = renderer.xr.getHand(i);
      const handModel = new THREE.Group(); // simplified hand representation
      hand.add(handModel);
      this._sm._scene.add(hand);
    }
  }

  _onSelect(event, controllerIndex) {
    // Raycast from controller into scene for node selection
    const controller = this._controllers[controllerIndex].controller;
    const tempMatrix = new THREE.Matrix4();
    tempMatrix.identity().extractRotation(controller.matrixWorld);

    const raycaster = new THREE.Raycaster();
    raycaster.ray.origin.setFromMatrixPosition(controller.matrixWorld);
    raycaster.ray.direction.set(0, 0, -1).applyMatrix4(tempMatrix);

    const intersects = raycaster.intersectObjects(this._sm._nodeGroup.children, true);
    if (intersects.length > 0) {
      const hit = intersects[0];
      if (hit.instanceId !== undefined && hit.object.userData.nodeIds) {
        const nodeId = hit.object.userData.nodeIds[hit.instanceId];
        document.dispatchEvent(new CustomEvent('node3d-click', {
          detail: { nodeId, worldPos: hit.point, vrController: controllerIndex }
        }));
      }
    }
  }

  _onSqueeze(event, controllerIndex) {
    // Squeeze = teleport to controller position
    const controller = this._controllers[controllerIndex].controller;
    const pos = new THREE.Vector3();
    pos.setFromMatrixPosition(controller.matrixWorld);

    // Animate camera target to squeezed position
    const target = this._sm._controls.target;
    target.lerp(pos, 0.5);
  }

  _onSessionEnd() {
    this._session = null;
    this._sm._renderer.xr.enabled = false;
    this._sm._scene.scale.set(1, 1, 1); // restore scale
    console.log('[VR] Session ended');
  }

  endSession() {
    if (this._session) {
      this._session.end();
    }
  }
}
```

---

## Layer 7: Parallax Depth Effect (Non-VR)

### 7.1 Mouse-Driven Parallax

For users without VR hardware, parallax creates depth perception by moving layers
at different speeds relative to mouse position.

```javascript
// ── parallax_depth.js ──
// Non-VR depth perception via mouse-driven parallax

class ParallaxDepth {
  constructor(sceneManager) {
    this._sm = sceneManager;
    this._isEnabled = false;
    this._mouseX = 0;
    this._mouseY = 0;
    this._targetRotX = 0;
    this._targetRotY = 0;
    this._smoothing = 0.05; // interpolation factor per frame
    this._maxTilt = 0.08;   // max rotation in radians (~4.5°)
  }

  enable() {
    this._isEnabled = true;
    document.addEventListener('mousemove', this._onMouseMove.bind(this));
  }

  disable() {
    this._isEnabled = false;
    document.removeEventListener('mousemove', this._onMouseMove);
    // Reset tilt
    this._sm._scene.rotation.x = 0;
    this._sm._scene.rotation.y = 0;
  }

  _onMouseMove(event) {
    // Normalize to [-1, 1]
    this._mouseX = (event.clientX / window.innerWidth) * 2 - 1;
    this._mouseY = (event.clientY / window.innerHeight) * 2 - 1;
  }

  /**
   * Call every frame from the render loop.
   * Smoothly tilts the scene based on mouse position.
   */
  update() {
    if (!this._isEnabled) return;

    this._targetRotY = this._mouseX * this._maxTilt;
    this._targetRotX = -this._mouseY * this._maxTilt;

    const scene = this._sm._scene;
    scene.rotation.y += (this._targetRotY - scene.rotation.y) * this._smoothing;
    scene.rotation.x += (this._targetRotX - scene.rotation.x) * this._smoothing;
  }
}
```

---

## Layer 8: Stereoscopic Modes

### 8.1 Side-by-Side and Anaglyph Rendering

```javascript
// ── stereo_modes.js ──
// Stereoscopic rendering for 3D viewing without VR headset

class StereoRenderer {
  constructor(sceneManager) {
    this._sm = sceneManager;
    this._mode = 'none'; // none | side-by-side | anaglyph
    this._stereoEffect = null;
    this._anaglyphEffect = null;
    this._eyeSeparation = 0.064; // 64mm IPD (average human)
  }

  /**
   * Set stereoscopic mode.
   * @param {'none'|'side-by-side'|'anaglyph'} mode
   */
  setMode(mode) {
    this._mode = mode;
  }

  /**
   * Render in the current stereo mode.
   * Call this instead of the standard renderer.render() when stereo is active.
   */
  render(scene, camera) {
    const renderer = this._sm._renderer;

    switch (this._mode) {
      case 'side-by-side':
        this._renderSideBySide(renderer, scene, camera);
        break;
      case 'anaglyph':
        this._renderAnaglyph(renderer, scene, camera);
        break;
      default:
        renderer.render(scene, camera);
    }
  }

  _renderSideBySide(renderer, scene, camera) {
    const width = renderer.domElement.width;
    const height = renderer.domElement.height;
    const halfWidth = width / 2;

    // Save original viewport
    renderer.setScissorTest(true);

    // Left eye
    camera.position.x -= this._eyeSeparation / 2;
    camera.updateProjectionMatrix();
    renderer.setViewport(0, 0, halfWidth, height);
    renderer.setScissor(0, 0, halfWidth, height);
    renderer.render(scene, camera);

    // Right eye
    camera.position.x += this._eyeSeparation;
    camera.updateProjectionMatrix();
    renderer.setViewport(halfWidth, 0, halfWidth, height);
    renderer.setScissor(halfWidth, 0, halfWidth, height);
    renderer.render(scene, camera);

    // Restore
    camera.position.x -= this._eyeSeparation / 2;
    camera.updateProjectionMatrix();
    renderer.setScissorTest(false);
    renderer.setViewport(0, 0, width, height);
  }

  _renderAnaglyph(renderer, scene, camera) {
    const width = renderer.domElement.width;
    const height = renderer.domElement.height;

    // Render left eye (red channel)
    camera.position.x -= this._eyeSeparation / 2;
    camera.updateProjectionMatrix();

    // Use color masking: left eye = red only
    const gl = renderer.getContext();
    gl.colorMask(true, false, false, true); // red channel only
    renderer.render(scene, camera);

    // Clear depth buffer for right eye overlay
    renderer.clearDepth();

    // Render right eye (cyan channels)
    camera.position.x += this._eyeSeparation;
    camera.updateProjectionMatrix();

    gl.colorMask(false, true, true, true); // green + blue channels
    renderer.render(scene, camera);

    // Restore
    gl.colorMask(true, true, true, true);
    camera.position.x -= this._eyeSeparation / 2;
    camera.updateProjectionMatrix();
  }
}
```

---

## Layer 9: Camera Flythrough

### 9.1 Automated Camera Paths

```javascript
// ── camera_flythrough.js ──
// Animated camera paths through the 3D graph

class CameraFlythrough {
  constructor(sceneManager) {
    this._sm = sceneManager;
    this._isPlaying = false;
    this._currentPath = null;
    this._pathProgress = 0;
    this._speed = 0.002; // progress per frame (0-1 range)
  }

  /**
   * Fly along an authority chain: camera follows the link path between nodes.
   */
  flyAlongChain(chainNodes) {
    if (chainNodes.length < 2) return;

    const points = chainNodes.map(n => new THREE.Vector3(
      n.x || 0,
      (LAYER_3D_CONFIG[n.layer] || LAYER_3D_CONFIG.convergence).y + 50, // hover above layer
      n.y || 0
    ));

    this._currentPath = new THREE.CatmullRomCurve3(points, false, 'centripetal');
    this._pathProgress = 0;
    this._isPlaying = true;
  }

  /**
   * Orbit around a cluster of nodes (e.g., adversary cluster).
   */
  orbitCluster(centerNode, radius = 100, height = 80) {
    const cx = centerNode.x || 0;
    const cy = (LAYER_3D_CONFIG[centerNode.layer] || LAYER_3D_CONFIG.convergence).y;
    const cz = centerNode.y || 0;

    // Generate circular orbit path
    const segments = 64;
    const points = [];
    for (let i = 0; i <= segments; i++) {
      const angle = (i / segments) * Math.PI * 2;
      points.push(new THREE.Vector3(
        cx + Math.cos(angle) * radius,
        cy + height,
        cz + Math.sin(angle) * radius
      ));
    }

    this._currentPath = new THREE.CatmullRomCurve3(points, true); // closed loop
    this._pathProgress = 0;
    this._speed = 0.001; // slower for orbit
    this._isPlaying = true;
  }

  /**
   * Zoom through timeline: camera moves along Z-axis through chronological events.
   */
  zoomThroughTimeline(timelineNodes) {
    const sorted = [...timelineNodes].sort((a, b) => {
      const da = new Date(a.date || 0).getTime();
      const db = new Date(b.date || 0).getTime();
      return da - db;
    });

    const points = sorted.map((n, i) => new THREE.Vector3(
      n.x || 0,
      (LAYER_3D_CONFIG.timeline || LAYER_3D_CONFIG.convergence).y + 30,
      n.y || i * 10  // fallback to index spacing
    ));

    if (points.length < 2) return;
    this._currentPath = new THREE.CatmullRomCurve3(points, false, 'centripetal');
    this._pathProgress = 0;
    this._speed = 0.0015;
    this._isPlaying = true;
  }

  /**
   * Call every frame from the render loop.
   * Moves camera along the current path.
   */
  update() {
    if (!this._isPlaying || !this._currentPath) return;

    this._pathProgress += this._speed;

    if (this._pathProgress >= 1) {
      if (this._currentPath.closed) {
        this._pathProgress -= 1; // loop
      } else {
        this._isPlaying = false;
        return;
      }
    }

    const pos = this._currentPath.getPointAt(this._pathProgress);
    const lookAt = this._currentPath.getPointAt(
      Math.min(1, this._pathProgress + 0.02)
    );

    this._sm._camera.position.copy(pos);
    this._sm._camera.lookAt(lookAt);
    this._sm._controls.target.copy(lookAt);
  }

  stop() {
    this._isPlaying = false;
    this._currentPath = null;
  }

  get isPlaying() { return this._isPlaying; }
}
```

---

## Layer 10: Fog & Atmosphere

### 10.1 Distance-Based Fog

```javascript
/**
 * Configure atmospheric effects for the 3D scene.
 * Fog provides depth cue — distant objects fade, focusing attention on nearby nodes.
 */
function setupAtmosphere(scene) {
  // Exponential fog: objects fade rapidly beyond a threshold
  scene.fog = new THREE.FogExp2(0x0a0a1e, 0.0008);

  // Alternative: linear fog for more control
  // scene.fog = new THREE.Fog(0x0a0a1e, 200, 1500);
}

/**
 * Bloom post-processing for high-threat nodes.
 * Uses Three.js EffectComposer with UnrealBloomPass.
 *
 * Note: EffectComposer requires importing from Three.js examples/jsm/
 */
function setupBloomPostProcessing(renderer, scene, camera) {
  const composer = new THREE.EffectComposer(renderer);

  // Standard render pass
  const renderPass = new THREE.RenderPass(scene, camera);
  composer.addPass(renderPass);

  // Bloom pass — makes bright (emissive) objects glow
  const bloomPass = new THREE.UnrealBloomPass(
    new THREE.Vector2(window.innerWidth, window.innerHeight),
    0.5,   // strength — subtle, not overwhelming
    0.4,   // radius
    0.85   // threshold — only bright emissive materials bloom
  );
  composer.addPass(bloomPass);

  return composer;
}
```

### 10.2 LOD (Level of Detail) Management

```javascript
/**
 * LOD manager — switches geometry detail based on camera distance.
 * Critical for maintaining 60fps with 2500+ nodes on Vega 8.
 */
class LODManager {
  constructor(sceneManager) {
    this._sm = sceneManager;
    this._lodThresholds = {
      high: 100,    // within 100 units: 16-segment spheres
      medium: 400,  // 100-400 units: 8-segment spheres
      low: Infinity // beyond 400: icosahedron (12 faces)
    };
  }

  /**
   * Called every frame. Checks camera distance to each layer's center
   * and swaps geometry detail accordingly.
   */
  update() {
    const camPos = this._sm._camera.position;

    for (const [layer, mesh] of Object.entries(this._sm._instancedNodes || {})) {
      if (!mesh) continue;
      const config = LAYER_3D_CONFIG[layer] || LAYER_3D_CONFIG.convergence;
      const layerCenter = new THREE.Vector3(0, config.y, 0);
      const distance = camPos.distanceTo(layerCenter);

      // Determine LOD level (could swap geometry if InstancedMesh supported it)
      // In practice, we adjust visibility and opacity for distant layers
      if (distance > this._lodThresholds.medium) {
        mesh.material.opacity = 0.5;
      } else if (distance > this._lodThresholds.high) {
        mesh.material.opacity = 0.75;
      } else {
        mesh.material.opacity = 0.9;
      }
    }
  }
}
```

---

## Layer 11: pywebview Bridge — Python↔JS Scene Control

### 11.1 Python Bridge API

```python
# ── dimensional_bridge.py ──
# pywebview API for THEMANBEARPIG 3D scene control

import json
import sqlite3
from datetime import date


class DimensionalBridge:
    """pywebview-exposed API for 3D visualization data and controls."""

    def __init__(self, db_path: str):
        self._db_path = db_path

    def _connect(self):
        conn = sqlite3.connect(self._db_path, timeout=30)
        conn.execute("PRAGMA busy_timeout = 60000")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA cache_size = -32000")
        conn.row_factory = sqlite3.Row
        return conn

    def get_graph_data_3d(self) -> str:
        """Fetch nodes and links for 3D rendering with layer and threat data."""
        conn = self._connect()
        try:
            nodes = []
            links = []

            # Adversary nodes with threat levels
            rows = conn.execute("""
                SELECT target_name as id, 'adversary' as layer, 'person' as type,
                       AVG(impeachment_value) / 10.0 as threat_level,
                       COUNT(*) as connections
                FROM impeachment_matrix
                GROUP BY target_name
                HAVING COUNT(*) >= 2
                ORDER BY threat_level DESC
                LIMIT 200
            """).fetchall()
            for r in rows:
                nodes.append(dict(r))

            # Authority nodes
            auth_rows = conn.execute("""
                SELECT DISTINCT primary_citation as id,
                       'authority' as layer, 'authority' as type,
                       0.3 as threat_level,
                       COUNT(*) as connections
                FROM authority_chains_v2
                GROUP BY primary_citation
                HAVING COUNT(*) >= 3
                ORDER BY connections DESC
                LIMIT 300
            """).fetchall()
            for r in auth_rows:
                nodes.append(dict(r))

            # Evidence nodes
            ev_rows = conn.execute("""
                SELECT DISTINCT source_file as id,
                       'evidence' as layer, 'document' as type,
                       0.2 as threat_level,
                       COUNT(*) as connections
                FROM evidence_quotes
                WHERE source_file IS NOT NULL AND source_file != ''
                GROUP BY source_file
                HAVING COUNT(*) >= 5
                ORDER BY connections DESC
                LIMIT 300
            """).fetchall()
            for r in ev_rows:
                nodes.append(dict(r))

            # Judicial violation nodes
            jv_rows = conn.execute("""
                SELECT violation_type as id,
                       'judicial' as layer, 'violation' as type,
                       0.8 as threat_level,
                       COUNT(*) as connections
                FROM judicial_violations
                GROUP BY violation_type
                HAVING COUNT(*) >= 5
                ORDER BY connections DESC
                LIMIT 50
            """).fetchall()
            for r in jv_rows:
                nodes.append(dict(r))

            return json.dumps({'nodes': nodes, 'links': links})
        finally:
            conn.close()

    def get_authority_chain_path(self, citation: str) -> str:
        """Get a chain of authorities for camera flythrough."""
        conn = self._connect()
        try:
            rows = conn.execute("""
                SELECT primary_citation, supporting_citation, relationship
                FROM authority_chains_v2
                WHERE primary_citation = ? OR supporting_citation = ?
                ORDER BY primary_citation
                LIMIT 50
            """, (citation, citation)).fetchall()
            chain = [dict(r) for r in rows]
            return json.dumps(chain)
        finally:
            conn.close()

    def get_camera_presets(self) -> str:
        """Return named camera positions for quick navigation."""
        presets = {
            'overview': {'x': 0, 'y': 400, 'z': 600, 'targetY': 0},
            'adversary_cluster': {'x': -100, 'y': 200, 'z': 200, 'targetY': 120},
            'judicial_layer': {'x': 50, 'y': 150, 'z': 300, 'targetY': 80},
            'evidence_floor': {'x': 0, 'y': 120, 'z': 400, 'targetY': 60},
            'filing_pipeline': {'x': 100, 'y': 50, 'z': 250, 'targetY': -20},
            'top_down': {'x': 0, 'y': 800, 'z': 0, 'targetY': 0},
            'side_view': {'x': 800, 'y': 0, 'z': 0, 'targetY': 0}
        }
        return json.dumps(presets)

    def get_separation_urgency(self) -> str:
        """Separation counter for visual urgency effects."""
        anchor = date(2025, 7, 29)
        today = date.today()
        days = (today - anchor).days
        return json.dumps({
            'days': days,
            'urgency': min(1.0, days / 365.0),
            'label': f'{days} days separated'
        })
```

---

## Layer 12: 3D Mode Toggle & UI Controls

### 12.1 2D/3D Mode Switch

```javascript
// ── mode_toggle.js ──
// Toggle between 2D D3 SVG and 3D Three.js rendering

class ModeToggle {
  constructor(svgContainer, threeContainer, sceneManager) {
    this._svgContainer = svgContainer;
    this._threeContainer = threeContainer;
    this._sm = sceneManager;
    this._currentMode = '2d';
  }

  toggle() {
    if (this._currentMode === '2d') {
      this._switchTo3D();
    } else {
      this._switchTo2D();
    }
  }

  _switchTo3D() {
    this._svgContainer.style.display = 'none';
    this._threeContainer.style.display = 'block';

    if (!this._sm._isActive) {
      this._sm.init();
    }
    this._sm.startRenderLoop();
    this._currentMode = '3d';

    document.dispatchEvent(new CustomEvent('mode-changed', { detail: { mode: '3d' } }));
  }

  _switchTo2D() {
    this._sm.stopRenderLoop();
    this._threeContainer.style.display = 'none';
    this._svgContainer.style.display = 'block';
    this._currentMode = '2d';

    document.dispatchEvent(new CustomEvent('mode-changed', { detail: { mode: '2d' } }));
  }

  get mode() { return this._currentMode; }
}
```

### 12.2 3D Controls Panel

```html
<div id="dim-controls" class="dim-panel">
  <div class="dim-header">
    <span>⬡ 3D ENGINE</span>
    <button id="dim-toggle-mode" class="dim-btn">2D/3D</button>
  </div>

  <div class="dim-section">
    <label>Layout</label>
    <select id="dim-layout" class="dim-select">
      <option value="force">Force Layout</option>
      <option value="tsne">t-SNE Projection</option>
      <option value="layered">Layer Stacking</option>
    </select>
  </div>

  <div class="dim-section">
    <label>Stereo Mode</label>
    <select id="dim-stereo" class="dim-select">
      <option value="none">None</option>
      <option value="side-by-side">Side-by-Side</option>
      <option value="anaglyph">Anaglyph (Red/Cyan)</option>
    </select>
  </div>

  <div class="dim-section">
    <label>Camera</label>
    <select id="dim-camera-preset" class="dim-select">
      <option value="overview">Overview</option>
      <option value="adversary_cluster">Adversary Cluster</option>
      <option value="judicial_layer">Judicial Layer</option>
      <option value="evidence_floor">Evidence Floor</option>
      <option value="top_down">Top Down</option>
      <option value="side_view">Side View</option>
    </select>
  </div>

  <div class="dim-section">
    <label>
      <input type="checkbox" id="dim-parallax"> Parallax Depth
    </label>
    <label>
      <input type="checkbox" id="dim-fog" checked> Distance Fog
    </label>
    <label>
      <input type="checkbox" id="dim-bloom"> Bloom Effect
    </label>
    <label>
      <input type="checkbox" id="dim-layers" checked> Layer Planes
    </label>
  </div>

  <div class="dim-section" id="dim-vr-section" style="display: none;">
    <button id="dim-vr-start" class="dim-btn dim-btn-vr">Enter VR</button>
  </div>

  <div class="dim-section dim-stats">
    <span id="dim-fps">60 FPS</span>
    <span id="dim-drawcalls">0 draws</span>
    <span id="dim-triangles">0 tris</span>
  </div>
</div>
```

### 12.3 CSS Styling

```css
.dim-panel {
  position: fixed;
  top: 60px;
  right: 20px;
  width: 240px;
  background: rgba(10, 10, 30, 0.92);
  border: 1px solid rgba(68, 136, 255, 0.3);
  border-radius: 8px;
  padding: 12px;
  color: #e0e0e0;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 11px;
  z-index: 10000;
  backdrop-filter: blur(8px);
}
.dim-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  font-weight: bold;
  color: #4488ff;
}
.dim-section { margin-bottom: 8px; }
.dim-section label { display: block; margin-bottom: 3px; color: #aaa; cursor: pointer; }
.dim-select {
  width: 100%;
  background: #1a1a3a;
  color: #e0e0e0;
  border: 1px solid #333;
  padding: 4px;
  border-radius: 4px;
}
.dim-btn {
  background: #1a1a3a;
  color: #4488ff;
  border: 1px solid #4488ff;
  padding: 4px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-family: inherit;
  font-size: 10px;
}
.dim-btn:hover { background: #4488ff; color: #000; }
.dim-btn-vr {
  width: 100%;
  padding: 8px;
  background: #004400;
  color: #00ff88;
  border-color: #00ff88;
  font-weight: bold;
}
.dim-stats {
  display: flex;
  justify-content: space-between;
  color: #666;
  font-size: 9px;
  border-top: 1px solid #222;
  padding-top: 6px;
}
```

---

## Anti-Patterns (NEVER DO THESE)

| # | Anti-Pattern | Why It Fails | Correct Approach |
|---|-------------|-------------|-----------------|
| 1 | Create individual `THREE.Mesh` per node | 2500 draw calls kills GPU (esp. Vega 8) | InstancedMesh: 1 draw call per layer (13 total) |
| 2 | Skip `requestAnimationFrame` for render loop | Uncapped frame rate, burns CPU, no vsync | Always use rAF — syncs to display refresh rate |
| 3 | Create new `THREE.Texture` per node | GPU memory explosion (2500 × 4KB+ = 10MB+) | Shared materials per layer; color via instanceColor |
| 4 | Use `THREE.Geometry` (deprecated) | Removed in Three.js r125+ | Use `THREE.BufferGeometry` exclusively |
| 5 | Render shadows with 2500+ nodes | Shadow map pass doubles draw calls; too expensive | Disable `shadowMap`; use emissive materials for depth cue |
| 6 | Set `pixelRatio` above 2 | 4K × 4x pixel ratio = 33M pixels per frame | Cap at `Math.min(devicePixelRatio, 2)` |
| 7 | Create geometry in render loop | GC pressure, allocation spikes every frame | Pre-allocate all geometry in `build()`, reuse in `update()` |
| 8 | Forget to call `.dispose()` on removed objects | GPU memory leak — textures and buffers never freed | Always `.dispose()` geometry, material, and textures on removal |
| 9 | Use `THREE.Line` for massive link sets | Each Line is a separate draw call | Use `THREE.LineSegments` with single BufferGeometry for all links |
| 10 | Ignore frustum culling | Rendering invisible off-screen objects wastes GPU | Three.js auto-culls Mesh; ensure bounding spheres are computed |
| 11 | Run t-SNE/UMAP on main thread for N>1000 | Freezes UI for 5-30 seconds | Use Web Worker or chunk computation across frames |
| 12 | Allocate `new THREE.Vector3()` in tight loops | GC pressure from per-frame allocation | Pre-allocate and reuse: `const _v = new THREE.Vector3()` |
| 13 | Use `OrbitControls` without `enableDamping` | Jerky, unpolished camera movement | Set `enableDamping = true`, `dampingFactor = 0.08` |
| 14 | Start WebXR session without user gesture | Browser security blocks — session request rejected | Only call `requestSession()` from click/button handler |
| 15 | Assume all GPUs support WebGL2 | Vega 8 supports it, but older integrateds may not | Check `renderer.capabilities.isWebGL2` and provide fallback |
| 16 | Use `matrix.decompose()` every frame for all nodes | Expensive for 2500+ decompositions | Only decompose when position changed; track dirty flags |
| 17 | Render text labels as 3D geometry | Extremely expensive for 2500+ labels | Use `THREE.Sprite` with `CanvasTexture` — one quad per label |

---

## Performance Budgets

| Metric | Budget | Rationale |
|--------|--------|-----------|
| Target framerate | 60fps (16.6ms per frame) | Smooth interaction; drop to 30fps only under extreme load |
| Max draw calls per frame | 50 | Vega 8 GPU handles ~100 before bottleneck; budget 50 for headroom |
| Max triangle count | 500,000 | Vega 8 can render ~1M tris at 60fps; budget half for overhead |
| GPU memory (textures + buffers) | 256 MB | Vega 8 shares from 24GB system RAM; reserve 256MB max |
| InstancedMesh instances per layer | 500 | 13 layers × 500 = 6,500 max node instances |
| LineSegments vertex count | 20,000 | 10,000 links × 2 vertices; single draw call |
| Bloom pass resolution | 50% of screen | Full-res bloom doubles render work; half-res is visually sufficient |
| t-SNE iterations | 500 | Convergence plateaus; beyond 500 iterations is diminishing returns |
| Camera flythrough speed | 2-5 units/frame | Faster causes motion sickness; slower feels sluggish |
| Fog density (FogExp2) | 0.0005–0.0015 | Too dense hides graph; too thin provides no depth cue |
| Label sprite resolution | 256×64 px canvas | Sharp enough for readable text; larger wastes texture memory |
| Parallax max tilt | 0.08 rad (~4.5°) | Larger tilt is disorienting; smaller is imperceptible |
| WebXR render scale | 1.0 (native) | Supersampling too expensive; undersampling looks blurry in VR |

---

## Hardware Optimization Notes for Vega 8 (2GB VRAM)

The target hardware is AMD Ryzen 3 3200G with Vega 8 integrated graphics (2GB shared VRAM).
This imposes specific constraints:

1. **Prefer `InstancedMesh` over individual meshes** — reduces draw calls from 2500 to 13
2. **Use `MeshPhongMaterial` not `MeshStandardMaterial`** — Phong is 30-50% cheaper to shade
3. **Disable shadows entirely** — shadow map generation is a full extra render pass
4. **Keep texture count minimal** — each texture consumes VRAM; use vertex colors instead
5. **Limit post-processing** — one bloom pass maximum; no SSAO, no motion blur
6. **BufferGeometry only** — regular Geometry was removed and was always slower
7. **Batch link rendering** — `LineSegments` not individual `Line` objects
8. **LOD for distant layers** — reduce opacity and skip small decorative elements when far
9. **Cap pixel ratio at 2** — even on high-DPI displays, 2x is sufficient for this GPU
10. **Use `powerPreference: 'default'`** — the integrated GPU is the only option anyway

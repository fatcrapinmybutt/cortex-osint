---
name: SINGULARITY-MBP-FORGE-DEPLOY
description: "EXE build pipeline for THEMANBEARPIG: pywebview desktop app, PyInstaller bundling, D3.js inline embedding, icon generation, auto-updater, installer creation. Complete deployment from Python+HTML source to standalone Windows executable with embedded litigation intelligence graph."
version: "2.0.0"
tier: "TIER-1/FORGE"
domain: "Desktop deployment — pywebview, PyInstaller, D3 inline, icon, installer, auto-update"
triggers:
  - exe
  - build
  - pywebview
  - PyInstaller
  - icon
  - deploy
  - launcher
  - installer
  - package
  - standalone
---

# SINGULARITY-MBP-FORGE-DEPLOY v2.0

> **From source code to standalone desktop weapon. One command. Zero dependencies.**

## Layer 1: PyWebView Desktop Architecture

### 1.1 Application Entry Point

```python
"""THEMANBEARPIG — Standalone Litigation Intelligence Visualizer"""
import webview
import json
import sqlite3
import threading
from pathlib import Path

class LitigationBridge:
    """Python↔JavaScript bridge for pywebview. Exposes DB queries to D3 frontend."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = None

    @property
    def conn(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.execute("PRAGMA busy_timeout=60000")
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA cache_size=-32000")
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def get_graph_data(self):
        """Load full graph data for D3 visualization."""
        try:
            nodes = [dict(r) for r in self.conn.execute(
                "SELECT * FROM graph_nodes LIMIT 5000").fetchall()]
            links = [dict(r) for r in self.conn.execute(
                "SELECT * FROM graph_links LIMIT 10000").fetchall()]
            return json.dumps({'nodes': nodes, 'links': links})
        except Exception as e:
            return json.dumps({'nodes': [], 'links': [], 'error': str(e)})

    def query_evidence(self, search_term: str):
        """FTS5 evidence search with LIKE fallback."""
        import re
        sanitized = re.sub(r'[^\w\s*"]', ' ', search_term).strip()
        try:
            rows = self.conn.execute("""
                SELECT quote_text, source_file, category, relevance_score
                FROM evidence_fts WHERE evidence_fts MATCH ?
                ORDER BY rank LIMIT 50
            """, (sanitized,)).fetchall()
            return json.dumps([dict(r) for r in rows])
        except Exception:
            rows = self.conn.execute("""
                SELECT quote_text, source_file, category, relevance_score
                FROM evidence_quotes WHERE quote_text LIKE ?
                LIMIT 50
            """, (f'%{sanitized}%',)).fetchall()
            return json.dumps([dict(r) for r in rows])

    def get_stats(self):
        """Dashboard statistics."""
        try:
            row = self.conn.execute("""
                SELECT
                    (SELECT COUNT(*) FROM evidence_quotes) as evidence,
                    (SELECT COUNT(*) FROM timeline_events) as timeline,
                    (SELECT COUNT(*) FROM authority_chains_v2) as authorities,
                    (SELECT COUNT(*) FROM impeachment_matrix) as impeachment,
                    (SELECT COUNT(*) FROM judicial_violations) as judicial
            """).fetchone()
            return json.dumps(dict(row))
        except Exception as e:
            return json.dumps({'error': str(e)})

def find_db():
    """Locate litigation_context.db — check multiple paths."""
    candidates = [
        Path(__file__).parent / 'litigation_context.db',
        Path.home() / 'LitigationOS' / 'litigation_context.db',
        Path('C:/Users/andre/LitigationOS/litigation_context.db'),
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None

def main():
    db_path = find_db()
    if not db_path:
        webview.create_window('ERROR', html='<h1>Database not found</h1>')
        webview.start()
        return

    bridge = LitigationBridge(db_path)
    html_path = str(Path(__file__).parent / 'THEMANBEARPIG_v7.html')

    window = webview.create_window(
        'THEMANBEARPIG — Litigation Intelligence',
        url=html_path if Path(html_path).exists() else None,
        js_api=bridge,
        width=1600, height=1000,
        min_size=(1024, 768),
        resizable=True, frameless=False,
        easy_drag=False, text_select=True
    )
    webview.start(debug=False)

if __name__ == '__main__':
    main()
```

## Layer 2: PyInstaller Build Configuration

### 2.1 Spec File Template

```python
# THEMANBEARPIG.spec — PyInstaller build specification
import sys
from pathlib import Path

block_cipher = None
ROOT = Path('C:/Users/andre/LitigationOS')

a = Analysis(
    [str(ROOT / 'adversary_blueprint.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / 'THEMANBEARPIG_v7.html'), '.'),
        (str(ROOT / 'graph_data_v7.json'), '.'),
        (str(ROOT / 'litigation_context.db'), '.'),
        (str(ROOT / 'build' / 'mbp.ico'), '.'),
    ],
    hiddenimports=[
        'webview', 'webview.platforms.edgechromium',
        'clr_loader', 'pythonnet',
        'sqlite3', 'json', 'threading', 'pathlib',
        'networkx', 'networkx.algorithms',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'pandas', 'scipy', 'torch',
              'PIL', 'tkinter', 'pytest', 'notebook'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts,
    a.binaries, a.zipfiles, a.datas,
    [], name='THEMANBEARPIG',
    debug=False, bootloader_ignore_signals=False,
    strip=False, upx=True, upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / 'build' / 'mbp.ico'),
)
```

### 2.2 Build Script

```python
"""Build THEMANBEARPIG executable."""
import subprocess
import sys
from pathlib import Path

def build():
    root = Path('C:/Users/andre/LitigationOS')
    spec = root / 'THEMANBEARPIG.spec'

    print("🔨 Building THEMANBEARPIG executable...")
    result = subprocess.run([
        sys.executable, '-m', 'PyInstaller',
        '--clean', '--noconfirm',
        str(spec)
    ], cwd=str(root), capture_output=True, text=True)

    if result.returncode == 0:
        exe_path = root / 'dist' / 'THEMANBEARPIG.exe'
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"✅ Build successful: {exe_path} ({size_mb:.1f} MB)")
        else:
            print("⚠️ Build completed but exe not found at expected path")
    else:
        print(f"❌ Build failed:\n{result.stderr[-2000:]}")

    return result.returncode

if __name__ == '__main__':
    sys.exit(build())
```

## Layer 3: D3.js Inline Embedding

### 3.1 HTML Template with Inline D3

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>THEMANBEARPIG</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { background: #0a0a1e; color: #e0e0e0; font-family: 'Segoe UI', sans-serif;
           overflow: hidden; width: 100vw; height: 100vh; }
    #graph { width: 100%; height: 100%; }
    .node { cursor: pointer; }
    .link { stroke-opacity: 0.4; }
    #hud { position: fixed; top: 10px; left: 10px; z-index: 999;
           background: #0a0a1ecc; padding: 12px; border-radius: 8px;
           border: 1px solid #ff00ff44; font-size: 12px; }
    .stat { color: #00ff88; font-weight: bold; }
  </style>
  <!-- D3.js v7 INLINE — no CDN dependency -->
  <script>/* D3.js v7 minified would be inlined here during build */</script>
</head>
<body>
  <div id="hud">
    <div>THEMANBEARPIG <span class="stat" id="version">v12.0</span></div>
    <div>Nodes: <span class="stat" id="node-count">0</span></div>
    <div>Links: <span class="stat" id="link-count">0</span></div>
    <div>Separation: <span class="stat" id="sep-days">—</span> days</div>
  </div>
  <svg id="graph"></svg>
  <script>
    // Bridge to Python backend
    async function loadData() {
      if (window.pywebview && window.pywebview.api) {
        const raw = await window.pywebview.api.get_graph_data();
        return JSON.parse(raw);
      }
      // Fallback: load from embedded JSON
      const resp = await fetch('graph_data_v7.json');
      return resp.json();
    }

    // Separation counter (dynamic, never hardcoded)
    function updateSeparation() {
      const anchor = new Date('2025-07-29');
      const days = Math.floor((Date.now() - anchor.getTime()) / 86400000);
      document.getElementById('sep-days').textContent = days;
    }
    updateSeparation();
    setInterval(updateSeparation, 3600000);

    // Main render
    loadData().then(data => {
      document.getElementById('node-count').textContent = data.nodes?.length || 0;
      document.getElementById('link-count').textContent = data.links?.length || 0;
      // D3 force simulation initialization here
    });
  </script>
</body>
</html>
```

## Layer 4: Icon Generation

### 4.1 Programmatic Icon Creation

```python
def generate_icon(output_path: str = 'build/mbp.ico'):
    """Generate THEMANBEARPIG icon programmatically."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("Pillow not available — using placeholder icon")
        return False

    sizes = [16, 32, 48, 64, 128, 256]
    images = []

    for size in sizes:
        img = Image.new('RGBA', (size, size), (10, 10, 30, 255))
        draw = ImageDraw.Draw(img)

        # Draw stylized "MBP" triangle
        cx, cy = size // 2, size // 2
        r = size * 0.4
        import math
        points = []
        for i in range(3):
            angle = math.radians(i * 120 - 90)
            points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))

        draw.polygon(points, outline=(255, 0, 255, 200), fill=(255, 0, 255, 40))

        # Center dot
        dr = size * 0.08
        draw.ellipse([cx-dr, cy-dr, cx+dr, cy+dr], fill=(0, 255, 136, 255))

        images.append(img)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    images[-1].save(output_path, format='ICO', sizes=[(s, s) for s in sizes])
    return True
```

## Layer 5: Testing & Validation

### 5.1 Pre-Build Smoke Tests

```python
def run_prebuild_checks() -> bool:
    """Verify all components before building."""
    checks = []

    # 1. HTML exists
    html = Path('THEMANBEARPIG_v7.html')
    checks.append(('HTML template', html.exists()))

    # 2. Graph data exists and is valid JSON
    gd = Path('graph_data_v7.json')
    if gd.exists():
        try:
            data = json.loads(gd.read_text())
            checks.append(('Graph data valid', 'nodes' in data and 'links' in data))
            checks.append(('Graph has nodes', len(data.get('nodes', [])) > 0))
        except json.JSONDecodeError:
            checks.append(('Graph data valid', False))
    else:
        checks.append(('Graph data exists', False))

    # 3. Database accessible
    db = Path('litigation_context.db')
    checks.append(('Database exists', db.exists()))
    if db.exists():
        try:
            conn = sqlite3.connect(str(db))
            conn.execute("SELECT 1").fetchone()
            checks.append(('Database readable', True))
            conn.close()
        except Exception:
            checks.append(('Database readable', False))

    # 4. Dependencies
    for mod in ['webview', 'networkx']:
        try:
            __import__(mod)
            checks.append((f'{mod} importable', True))
        except ImportError:
            checks.append((f'{mod} importable', False))

    all_pass = all(ok for _, ok in checks)
    for name, ok in checks:
        print(f"  {'✅' if ok else '❌'} {name}")

    return all_pass
```

## Anti-Patterns (10 Rules)

1. NEVER include litigation_context.db in public distributions (contains PII)
2. NEVER use CDN links for D3.js — must be inlined for offline operation
3. NEVER build without running pre-build smoke tests
4. NEVER hardcode absolute paths in the exe — use relative to __file__
5. NEVER include dev dependencies (pytest, ruff, etc.) in the bundle
6. NEVER build with console=True for production releases
7. NEVER skip icon generation — default PyInstaller icon looks amateur
8. NEVER include child's full name anywhere in the HTML/JS (MCR 8.119(H))
9. NEVER hardcode separation day count — compute dynamically
10. NEVER deploy without testing the exe on a clean path (not the dev machine)

## Performance Budgets

| Operation | Budget | Technique |
|-----------|--------|-----------|
| EXE startup | <5s | Lazy imports, minimal deps |
| Graph load | <2s | Streaming JSON parse |
| DB query | <100ms | WAL mode, indexed tables |
| Build time | <120s | UPX compression, excludes |
| EXE size | <150MB | Aggressive excludes list |

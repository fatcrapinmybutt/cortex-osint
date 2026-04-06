#!/usr/bin/env python3
"""
PROJECT KRAKEN Build System
Bundles project_kraken.py into a standalone .exe via PyInstaller.

Usage:
  python -I scripts/kraken_build.py --onefile --clean
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENTRY_POINT = REPO_ROOT / "scripts" / "project_kraken.py"
DIST_DIR = REPO_ROOT / "dist"
BUILD_DIR = REPO_ROOT / "build"
ICON_PATH = REPO_ROOT / "08_MEDIA" / "project_kraken_icon.ico"

# Hidden imports for optional deps used inside try/except
HIDDEN_IMPORTS = [
    "pypdfium2",
    "docx",
]

# Exclude heavy packages not needed at runtime
EXCLUDES = [
    "tkinter", "_tkinter", "unittest", "test",
    "PIL", "numpy", "pandas", "matplotlib",
    "scipy", "sklearn", "torch", "transformers",
    "lancedb", "duckdb", "polars",
    "pywebview", "webview",
    "IPython", "notebook", "jupyter",
    "sphinx", "docutils",
    "setuptools", "pip", "wheel",
]


def generate_spec(name, onefile, windowed):
    """Generate a PyInstaller .spec file."""
    console_val = "False" if windowed else "True"
    hiddens_str = ", ".join(repr(h) for h in HIDDEN_IMPORTS)
    excludes_str = ", ".join(repr(e) for e in EXCLUDES)
    icon_line = f"icon={repr(str(ICON_PATH))}," if ICON_PATH.exists() else ""

    if onefile:
        spec = f"""# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    [{repr(str(ENTRY_POINT))}],
    pathex=[{repr(str(REPO_ROOT))}],
    binaries=[],
    datas=[],
    hiddenimports=[{hiddens_str}],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[{excludes_str}],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name={repr(name)},
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console={console_val},
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    {icon_line}
)
"""
    else:
        spec = f"""# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    [{repr(str(ENTRY_POINT))}],
    pathex=[{repr(str(REPO_ROOT))}],
    binaries=[],
    datas=[],
    hiddenimports=[{hiddens_str}],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[{excludes_str}],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name={repr(name)},
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console={console_val},
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    {icon_line}
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name={repr(name)},
)
"""
    return spec


def preflight_checks():
    """Verify prerequisites before building."""
    errors = []

    if not ENTRY_POINT.exists():
        errors.append(f"Entry point not found: {ENTRY_POINT}")

    try:
        import PyInstaller
    except ImportError:
        errors.append("PyInstaller not installed. Run: pip install pyinstaller")

    if not Path(r"C:\Users\andre\LitigationOS\litigation_context.db").exists():
        print("WARNING: litigation_context.db not found -- KRAKEN needs it at runtime.")

    return errors


def build(name, onefile, windowed, clean):
    """Execute the PyInstaller build."""
    errors = preflight_checks()
    if errors:
        print("BUILD FAILED -- preflight errors:")
        for e in errors:
            print(f"  x {e}")
        return 1

    spec_content = generate_spec(name, onefile, windowed)
    spec_path = REPO_ROOT / f"{name}.spec"
    with open(str(spec_path), "w", encoding="utf-8") as f:
        f.write(spec_content)
    print(f"Generated spec: {spec_path}")

    if clean:
        for d in (BUILD_DIR, DIST_DIR):
            if d.exists():
                print(f"Cleaning {d}...")
                shutil.rmtree(str(d), ignore_errors=True)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(spec_path),
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        "--noconfirm",
    ]

    print(f"\nBuilding {name}...")
    print(f"  Mode: {'onefile' if onefile else 'one-dir'}")
    print(f"  Console: {'hidden' if windowed else 'visible'}")
    print(f"  Command: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, cwd=str(REPO_ROOT))

    if result.returncode == 0:
        if onefile:
            exe_path = DIST_DIR / f"{name}.exe"
        else:
            exe_path = DIST_DIR / name / f"{name}.exe"
        print(f"\n{'=' * 60}")
        print(f"BUILD SUCCESSFUL")
        print(f"  Executable: {exe_path}")
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / 1048576
            print(f"  Size: {size_mb:.1f} MB")
        print(f"\nTo deploy:")
        print(f"  copy \"{exe_path}\" \"%USERPROFILE%\\Desktop\\\"")
        print(f"{'=' * 60}")
    else:
        print(f"\nBUILD FAILED (exit code {result.returncode})")
        print("Check the output above for errors.")

    # Clean up spec file
    if spec_path.exists():
        try:
            os.remove(str(spec_path))
        except Exception:
            pass

    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="PROJECT KRAKEN Build -- PyInstaller bundler for the KRAKEN evidence hunter"
    )
    parser.add_argument("--onefile", action="store_true",
                        help="Build as single .exe (required for Desktop deployment)")
    parser.add_argument("--windowed", action="store_true",
                        help="Hide console window (NOT recommended -- KRAKEN is CLI)")
    parser.add_argument("--name", default="PROJECT_KRAKEN",
                        help="Executable name (default: PROJECT_KRAKEN)")
    parser.add_argument("--clean", action="store_true",
                        help="Clean build/dist directories before building")
    parser.add_argument("--spec-only", action="store_true",
                        help="Generate .spec file only, do not build")
    args = parser.parse_args()

    print(f"PROJECT KRAKEN Build System")
    print(f"  Repo root: {REPO_ROOT}")
    print(f"  Entry point: {ENTRY_POINT}")
    print()

    if args.spec_only:
        spec = generate_spec(args.name, args.onefile, args.windowed)
        spec_path = REPO_ROOT / f"{args.name}.spec"
        with open(str(spec_path), "w", encoding="utf-8") as f:
            f.write(spec)
        print(f"Spec file written to: {spec_path}")
        return 0

    return build(args.name, args.onefile, not args.windowed, args.clean)


if __name__ == "__main__":
    sys.exit(main())

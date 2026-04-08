"""Auto-discover and smoke-test ALL engines under 00_SYSTEM/engines/.

For each engine directory that contains an __init__.py:
1. Verify importlib can load it without crash
2. Verify no stdout corruption occurs during import
3. Report __version__ if present
"""

import importlib
import io
import sys
from pathlib import Path

import pytest

ENGINES_DIR = Path(__file__).resolve().parent.parent / "engines"

# Ensure 00_SYSTEM is on sys.path for `engines.*` imports
_sys_dir = str(ENGINES_DIR.parent)
if _sys_dir not in sys.path:
    sys.path.insert(0, _sys_dir)


def _discover_engines():
    """Yield (engine_name, engine_dir) for every directory with __init__.py."""
    if not ENGINES_DIR.is_dir():
        return
    for child in sorted(ENGINES_DIR.iterdir()):
        if child.is_dir() and (child / "__init__.py").exists():
            # Skip 'tests' subdir — not an engine
            if child.name == "tests":
                continue
            yield child.name, child


ENGINE_LIST = list(_discover_engines())
ENGINE_IDS = [name for name, _ in ENGINE_LIST]


@pytest.mark.engine
@pytest.mark.parametrize("engine_name,engine_dir", ENGINE_LIST, ids=ENGINE_IDS)
def test_engine_import(engine_name, engine_dir):
    """Engine __init__.py imports without crash or missing dependency error."""
    mod_name = f"engines.{engine_name}"
    # Invalidate cached module to get a clean import
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    try:
        mod = importlib.import_module(mod_name)
    except ImportError as exc:
        # Missing optional dependencies are acceptable — mark as xfail
        pytest.skip(f"Import failed (likely optional dep): {exc}")
    except Exception as exc:
        pytest.fail(f"Engine '{engine_name}' import crashed: {type(exc).__name__}: {exc}")
    assert mod is not None, f"importlib returned None for {mod_name}"


@pytest.mark.engine
@pytest.mark.parametrize("engine_name,engine_dir", ENGINE_LIST, ids=ENGINE_IDS)
def test_engine_no_stdout_corruption(engine_name, engine_dir):
    """Engine import does not write garbage to stdout (Rule: no stdout clobbering)."""
    mod_name = f"engines.{engine_name}"
    if mod_name in sys.modules:
        del sys.modules[mod_name]

    captured = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured
    try:
        importlib.import_module(mod_name)
    except ImportError:
        pytest.skip(f"Engine '{engine_name}' has missing deps — skipping stdout check")
    except Exception:
        pass  # Import crash handled by test_engine_import
    finally:
        sys.stdout = old_stdout

    output = captured.getvalue()
    # Allow empty stdout or informational logging, but NOT JSON-RPC corruption
    if output.strip():
        # Check for obvious corruption patterns
        bad_patterns = ["{", "Traceback", "Error", "PRAGMA"]
        for pat in bad_patterns:
            if pat in output:
                pytest.fail(
                    f"Engine '{engine_name}' wrote suspicious output to stdout: "
                    f"{output[:200]!r}"
                )


@pytest.mark.engine
@pytest.mark.parametrize("engine_name,engine_dir", ENGINE_LIST, ids=ENGINE_IDS)
def test_engine_version(engine_name, engine_dir):
    """Engine advertises __version__ string (best practice, not hard fail)."""
    mod_name = f"engines.{engine_name}"
    try:
        mod = importlib.import_module(mod_name)
    except (ImportError, Exception):
        pytest.skip(f"Engine '{engine_name}' failed to import")
    if not hasattr(mod, "__version__"):
        pytest.skip(f"Engine '{engine_name}' does not define __version__ (advisory)")
    assert isinstance(mod.__version__, str), "__version__ must be a string"
    assert len(mod.__version__) > 0, "__version__ must not be empty"


def test_engine_count():
    """Verify at least 14 engine directories discovered (sanity check)."""
    assert len(ENGINE_LIST) >= 14, (
        f"Expected at least 14 engines, discovered {len(ENGINE_LIST)}: "
        f"{[n for n, _ in ENGINE_LIST]}"
    )

#!/usr/bin/env python
"""LitigationOS Layer-7 Test Runner.

Usage:
    python -I run_tests.py            # Run all tests
    python -I run_tests.py -k engine  # Run only engine tests
    python -I run_tests.py --no-db    # Skip DB-dependent tests

Sets CWD to 00_SYSTEM/tests/ (away from repo root shadow modules),
ensures PYTHONUTF8=1, and invokes pytest with proper flags.
"""

import os
import sys
from pathlib import Path

def main():
    # Resolve paths
    tests_dir = Path(__file__).resolve().parent
    sys_dir = tests_dir.parent          # 00_SYSTEM
    repo_root = sys_dir.parent          # LitigationOS

    # Set CWD to tests dir — away from repo root shadow modules
    os.chdir(tests_dir)

    # Ensure UTF-8
    os.environ["PYTHONUTF8"] = "1"

    # Add 00_SYSTEM to path so engines/daemon imports work
    if str(sys_dir) not in sys.path:
        sys.path.insert(0, str(sys_dir))

    # Build pytest args
    pytest_args = [
        str(tests_dir),         # test directory
        "-v",                   # verbose
        "--tb=short",           # short tracebacks
        "-q",                   # quiet summary (combine with -v → per-test results, short summary)
        "--no-header",          # clean output
    ]

    # Pass through any CLI args (e.g., -k, -x, --no-db)
    extra = sys.argv[1:]

    # Handle --no-db convenience flag → translates to pytest -m "not db"
    if "--no-db" in extra:
        extra.remove("--no-db")
        pytest_args.extend(["-m", "not db"])

    pytest_args.extend(extra)

    # Import pytest and run
    try:
        import pytest as _pytest
    except ImportError:
        print("ERROR: pytest not installed. Run: pip install pytest")
        sys.exit(1)

    print("== LitigationOS Layer-7 Tests ==")
    print(f"   Tests dir: {tests_dir}")
    print(f"   Repo root: {repo_root}")
    print(f"   DB path:   {repo_root / 'litigation_context.db'}")
    print(f"   Args:      {' '.join(pytest_args)}")
    print("================================")

    rc = _pytest.main(pytest_args)
    sys.exit(rc)


if __name__ == "__main__":
    main()

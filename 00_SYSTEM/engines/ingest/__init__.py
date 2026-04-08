"""Go-based ingest engine — 8-worker goroutine file processing pipeline.

This engine is implemented in Go (main.go), not Python.
The compiled binary is `ingest.exe` in this directory.

Usage:
    import subprocess
    subprocess.run(['00_SYSTEM/engines/ingest/ingest.exe', ...])

Build:
    cd 00_SYSTEM/engines/ingest && go build -o ingest.exe
"""

__all__ = ["BINARY_PATH", "is_available"]

__version__ = "1.0.0"
__engine_type__ = "go_binary"

import os as _os

BINARY_PATH = _os.path.join(_os.path.dirname(__file__), "ingest.exe")


def is_available() -> bool:
    """Check if the Go binary is compiled and available."""
    return _os.path.isfile(BINARY_PATH)

"""LitigationOS Intelligence API — REST endpoints for litigation data.

Lightweight HTTP API using Python's built-in http.server.
All database access is READ-ONLY (PRAGMA query_only=ON).
"""

__version__ = "1.0.0"

from .server import LitigationAPIHandler, start_server
from .client import LitigationClient

__all__ = ["LitigationAPIHandler", "start_server", "LitigationClient"]

"""Litigation API client — query LitigationOS intelligence programmatically.

Usage:
    from api.client import LitigationClient
    client = LitigationClient()
    print(client.health())
    print(client.search_evidence("custody"))
"""

import json
import urllib.error
import urllib.parse
import urllib.request


class LitigationClient:
    """Simple HTTP client for the LitigationOS Intelligence API."""

    def __init__(self, base_url="http://127.0.0.1:8742"):
        self.base_url = base_url.rstrip("/")

    def _get(self, path, params=None):
        """Send GET request and return parsed JSON."""
        url = f"{self.base_url}{path}"
        if params:
            filtered = {k: v for k, v in params.items() if v is not None}
            if filtered:
                url += "?" + urllib.parse.urlencode(filtered)
        req = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                return {"error": f"HTTP {exc.code}: {body[:200]}"}
        except urllib.error.URLError as exc:
            return {"error": f"Connection failed: {exc.reason}"}

    def health(self):
        """GET /api/health — server health + separation days."""
        return self._get("/api/health")

    def stats(self):
        """GET /api/stats — row counts for key tables."""
        return self._get("/api/stats")

    def separation(self):
        """GET /api/separation — father-son separation counter."""
        return self._get("/api/separation")

    def search_evidence(self, q, limit=50, lane=None):
        """GET /api/evidence/search — FTS5 evidence search."""
        return self._get("/api/evidence/search", {"q": q, "limit": limit, "lane": lane})

    def evidence_lanes(self):
        """GET /api/evidence/lanes — evidence counts by lane."""
        return self._get("/api/evidence/lanes")

    def search_authority(self, q, limit=50):
        """GET /api/authority/search — authority chain search."""
        return self._get("/api/authority/search", {"q": q, "limit": limit})

    def impeachment(self, target=None, limit=25):
        """GET /api/impeachment — impeachment matrix search."""
        return self._get("/api/impeachment", {"target": target, "limit": limit})

    def contradictions(self, entity=None, limit=25):
        """GET /api/contradictions — contradiction map search."""
        return self._get("/api/contradictions", {"entity": entity, "limit": limit})

    def timeline(self, q=None, limit=50):
        """GET /api/timeline — timeline event search."""
        return self._get("/api/timeline", {"q": q, "limit": limit})

    def deadlines(self):
        """GET /api/deadlines — filing deadlines with urgency."""
        return self._get("/api/deadlines")

    def filings(self):
        """GET /api/filings — filing packages overview."""
        return self._get("/api/filings")

    def judicial(self, judge=None, limit=50):
        """GET /api/judicial — judicial violations."""
        return self._get("/api/judicial", {"judge": judge, "limit": limit})

    def adversary(self, target):
        """GET /api/adversary — adversary intelligence profile."""
        return self._get("/api/adversary", {"target": target})


if __name__ == "__main__":
    import sys

    client = LitigationClient()
    if len(sys.argv) < 2:
        print("Usage: python client.py <endpoint> [args...]")
        print("  health | stats | separation | evidence <q> | adversary <target>")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "health":
        print(json.dumps(client.health(), indent=2))
    elif cmd == "stats":
        print(json.dumps(client.stats(), indent=2))
    elif cmd == "separation":
        print(json.dumps(client.separation(), indent=2))
    elif cmd == "evidence" and len(sys.argv) > 2:
        print(json.dumps(client.search_evidence(sys.argv[2]), indent=2))
    elif cmd == "adversary" and len(sys.argv) > 2:
        print(json.dumps(client.adversary(sys.argv[2]), indent=2))
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

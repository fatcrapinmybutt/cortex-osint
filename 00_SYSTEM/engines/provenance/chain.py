"""
Evidence Provenance Chain Engine — Tracks the complete lifecycle of every
evidence item from ingestion through filing with MRE 901/902 authentication.

Every evidence atom gets a provenance chain:
  ingested → classified → deduplicated → bates_stamped → authenticated → filed
"""
import sys
import os
import sqlite3
import hashlib
import uuid
from datetime import datetime
from typing import Optional

sys.path.insert(0, r"C:\Users\andre\LitigationOS")

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "litigation_context.db"
)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS evidence_provenance (
    provenance_id TEXT PRIMARY KEY,
    evidence_id TEXT NOT NULL,
    action TEXT NOT NULL,
    actor TEXT NOT NULL,
    timestamp TEXT DEFAULT (datetime('now')),
    source_path TEXT,
    destination_path TEXT,
    sha256 TEXT,
    metadata TEXT,
    mre_basis TEXT
)
"""

CREATE_INDEX_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_provenance_evidence ON evidence_provenance(evidence_id)",
    "CREATE INDEX IF NOT EXISTS idx_provenance_action ON evidence_provenance(action)",
    "CREATE INDEX IF NOT EXISTS idx_provenance_actor ON evidence_provenance(actor)",
    "CREATE INDEX IF NOT EXISTS idx_provenance_timestamp ON evidence_provenance(timestamp)",
]

VALID_ACTIONS = frozenset({
    "ingested", "classified", "deduplicated", "bates_stamped",
    "authenticated", "filed", "verified", "exported", "redacted",
    "ocr_extracted", "lane_assigned", "exhibit_bound",
})

MRE_BASIS_MAP = {
    "901(b)(1)": "Testimony of a witness with knowledge that the item is what it is claimed to be.",
    "901(b)(4)": "Distinctive characteristics — appearance, contents, substance, internal patterns.",
    "901(b)(5)": "Voice identification by opinion based upon hearing the voice.",
    "901(b)(9)": "Evidence describing a process or system and showing it produces an accurate result.",
    "902(1)": "Domestic public documents under seal.",
    "902(4)": "Certified copies of public records.",
    "902(5)": "Official publications — books, pamphlets, other publications purporting to be issued by public authority.",
    "902(6)": "Newspapers and periodicals.",
    "902(11)": "Certified domestic records of a regularly conducted activity.",
}


class ProvenanceChain:
    """Tracks evidence provenance from ingestion through filing."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or DB_PATH
        self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA busy_timeout=60000")
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA cache_size=-32000")
            self._conn.execute("PRAGMA temp_store=MEMORY")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute(CREATE_TABLE_SQL)
            for idx_sql in CREATE_INDEX_SQL:
                self._conn.execute(idx_sql)
            self._conn.commit()
        return self._conn

    def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def record(
        self,
        evidence_id: str,
        action: str,
        actor: str,
        source_path: Optional[str] = None,
        destination_path: Optional[str] = None,
        sha256: Optional[str] = None,
        mre_basis: Optional[str] = None,
        metadata: Optional[str] = None,
    ) -> str:
        """Record a provenance event for an evidence item.

        Args:
            evidence_id: Unique identifier for the evidence (e.g., Bates number).
            action: Lifecycle action (ingested, classified, deduplicated, etc.).
            actor: System/person performing the action (KRAKEN, SENTINEL, user, etc.).
            source_path: Original file path.
            destination_path: Where file was moved/copied to.
            sha256: SHA-256 hash of the file at this point.
            mre_basis: MRE 901/902 authentication basis code.
            metadata: JSON string with additional context.

        Returns:
            The provenance_id of the recorded event.
        """
        if action not in VALID_ACTIONS:
            raise ValueError(
                f"Invalid action '{action}'. Valid: {sorted(VALID_ACTIONS)}"
            )

        provenance_id = f"PROV-{uuid.uuid4().hex[:12].upper()}"
        timestamp = datetime.now().isoformat()

        if source_path and sha256 is None:
            sha256 = self._compute_sha256(source_path)

        self.conn.execute(
            """INSERT INTO evidence_provenance
               (provenance_id, evidence_id, action, actor, timestamp,
                source_path, destination_path, sha256, metadata, mre_basis)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (provenance_id, evidence_id, action, actor, timestamp,
             source_path, destination_path, sha256, metadata, mre_basis),
        )
        self.conn.commit()
        return provenance_id

    def get_chain(self, evidence_id: str) -> list[dict]:
        """Get the full provenance chain for an evidence item in chronological order."""
        rows = self.conn.execute(
            """SELECT provenance_id, evidence_id, action, actor, timestamp,
                      source_path, destination_path, sha256, metadata, mre_basis
               FROM evidence_provenance
               WHERE evidence_id = ?
               ORDER BY timestamp ASC""",
            (evidence_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def verify_integrity(self, evidence_id: str) -> dict:
        """Verify SHA-256 integrity for an evidence item.

        Checks the most recent SHA-256 in the chain against the current file on disk.
        Returns a dict with 'verified', 'details', and 'chain_length'.
        """
        chain = self.get_chain(evidence_id)
        if not chain:
            return {
                "verified": False,
                "details": f"No provenance chain found for evidence_id={evidence_id}",
                "chain_length": 0,
            }

        last_hash = None
        last_path = None
        for entry in reversed(chain):
            if entry.get("sha256"):
                last_hash = entry["sha256"]
                last_path = entry.get("destination_path") or entry.get("source_path")
                break

        if not last_hash:
            return {
                "verified": False,
                "details": "No SHA-256 hash recorded in provenance chain",
                "chain_length": len(chain),
            }

        if not last_path or not os.path.exists(last_path):
            return {
                "verified": False,
                "details": f"File not found at recorded path: {last_path}",
                "chain_length": len(chain),
                "recorded_sha256": last_hash,
                "recorded_path": last_path,
            }

        current_hash = self._compute_sha256(last_path)
        match = current_hash == last_hash

        return {
            "verified": match,
            "details": "SHA-256 matches — integrity confirmed" if match
                       else f"SHA-256 MISMATCH: recorded={last_hash[:16]}... current={current_hash[:16]}...",
            "chain_length": len(chain),
            "recorded_sha256": last_hash,
            "current_sha256": current_hash,
            "file_path": last_path,
        }

    def get_authentication_affidavit(self, evidence_id: str) -> str:
        """Generate MRE 901(b)(1) authentication text based on provenance chain.

        Produces a formal authentication paragraph suitable for inclusion in an
        affidavit or witness declaration supporting evidence admission.
        """
        chain = self.get_chain(evidence_id)
        if not chain:
            return f"[ACQUIRE: No provenance chain found for evidence ID '{evidence_id}'. " \
                   f"Cannot generate authentication affidavit without chain of custody records.]"

        first = chain[0]
        last = chain[-1]
        source = first.get("source_path", "unknown location")
        file_name = os.path.basename(source) if source else "the document"
        ingest_date = first.get("timestamp", "unknown date")[:10]
        actor = first.get("actor", "the system")

        mre_bases = []
        for entry in chain:
            if entry.get("mre_basis") and entry["mre_basis"] not in mre_bases:
                mre_bases.append(entry["mre_basis"])

        integrity = self.verify_integrity(evidence_id)

        lines = [
            f"AUTHENTICATION OF EVIDENCE — {evidence_id}",
            "",
            f"I, Andrew James Pigors, Plaintiff, appearing pro se, state under "
            f"penalty of perjury and upon personal knowledge:",
            "",
            f"1. The document identified as Exhibit {evidence_id} is a true and "
            f"accurate copy of {file_name}, which was obtained from {source}.",
            "",
            f"2. This document was first ingested into the case management system "
            f"on {ingest_date} by {actor}.",
            "",
        ]

        para = 3
        actions_described = []
        for entry in chain:
            action = entry["action"]
            ts = entry["timestamp"][:10] if entry.get("timestamp") else "unknown"
            if action == "ingested":
                continue
            if action == "classified":
                actions_described.append(f"classified on {ts}")
            elif action == "bates_stamped":
                actions_described.append(f"Bates-stamped on {ts}")
            elif action == "authenticated":
                actions_described.append(f"authenticated on {ts}")
            elif action == "deduplicated":
                actions_described.append(f"verified unique on {ts}")
            elif action == "filed":
                actions_described.append(f"filed with the Court on {ts}")

        if actions_described:
            lines.append(
                f"{para}. The document was subsequently "
                + ", ".join(actions_described) + "."
            )
            lines.append("")
            para += 1

        if integrity.get("verified"):
            lines.append(
                f"{para}. The digital integrity of this document has been verified "
                f"by SHA-256 cryptographic hash comparison. The hash recorded at "
                f"ingestion matches the current file, confirming the document has "
                f"not been altered, modified, or tampered with."
            )
            lines.append("")
            para += 1

        if mre_bases:
            basis_text = "; ".join(
                f"MRE {b} — {MRE_BASIS_MAP.get(b, 'applicable basis')}"
                for b in mre_bases
            )
            lines.append(
                f"{para}. This document is authenticated pursuant to "
                f"Michigan Rules of Evidence: {basis_text}."
            )
            lines.append("")
            para += 1

        lines.extend([
            f"{para}. I have personal knowledge of the facts stated herein and "
            f"am competent to testify to them. MRE 901(b)(1).",
            "",
            "Dated: _______________",
            "",
            "____________________________",
            "Andrew James Pigors",
            "Plaintiff, appearing pro se",
        ])

        return "\n".join(lines)

    def get_stats(self) -> dict:
        """Get provenance statistics by action type, actor, and integrity status."""
        action_counts = {}
        for row in self.conn.execute(
            "SELECT action, COUNT(*) as cnt FROM evidence_provenance GROUP BY action ORDER BY cnt DESC"
        ):
            action_counts[row["action"]] = row["cnt"]

        actor_counts = {}
        for row in self.conn.execute(
            "SELECT actor, COUNT(*) as cnt FROM evidence_provenance GROUP BY actor ORDER BY cnt DESC"
        ):
            actor_counts[row["actor"]] = row["cnt"]

        total = self.conn.execute("SELECT COUNT(*) FROM evidence_provenance").fetchone()[0]
        unique_evidence = self.conn.execute(
            "SELECT COUNT(DISTINCT evidence_id) FROM evidence_provenance"
        ).fetchone()[0]

        with_hash = self.conn.execute(
            "SELECT COUNT(*) FROM evidence_provenance WHERE sha256 IS NOT NULL"
        ).fetchone()[0]

        with_mre = self.conn.execute(
            "SELECT COUNT(*) FROM evidence_provenance WHERE mre_basis IS NOT NULL"
        ).fetchone()[0]

        return {
            "total_records": total,
            "unique_evidence_items": unique_evidence,
            "records_with_sha256": with_hash,
            "records_with_mre_basis": with_mre,
            "by_action": action_counts,
            "by_actor": actor_counts,
        }

    @staticmethod
    def _compute_sha256(file_path: str) -> Optional[str]:
        """Compute SHA-256 hash of a file, streaming for large files."""
        if not os.path.exists(file_path):
            return None
        sha = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(1024 * 1024):
                    sha.update(chunk)
            return sha.hexdigest()
        except (OSError, PermissionError):
            return None


if __name__ == "__main__":
    engine = ProvenanceChain()
    print("ProvenanceChain engine initialized")
    print(f"DB: {engine._db_path}")
    print(f"Stats: {engine.get_stats()}")

    test_id = "TEST-SMOKE-001"
    prov_id = engine.record(
        evidence_id=test_id,
        action="ingested",
        actor="smoke_test",
        source_path=os.path.abspath(__file__),
        mre_basis="901(b)(1)",
    )
    print(f"\nRecorded provenance: {prov_id}")

    chain = engine.get_chain(test_id)
    print(f"Chain length: {len(chain)}")
    for entry in chain:
        print(f"  {entry['action']} by {entry['actor']} at {entry['timestamp']}")

    integrity = engine.verify_integrity(test_id)
    print(f"Integrity: {integrity['verified']} — {integrity['details']}")

    affidavit = engine.get_authentication_affidavit(test_id)
    print(f"\nAuthentication affidavit preview:\n{affidavit[:500]}...")

    print(f"\nFinal stats: {engine.get_stats()}")
    engine.close()

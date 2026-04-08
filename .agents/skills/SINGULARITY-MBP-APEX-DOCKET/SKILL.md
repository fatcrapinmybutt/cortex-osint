---
name: SINGULARITY-MBP-APEX-DOCKET
description: "Real-time court docket monitoring and deadline intelligence for LitigationOS. MiCOURT API, CourtListener webhooks, PACER integration, auto-deadline computation from Michigan Court Rules, push notifications, filing confirmation tracking, judge assignment monitoring."
version: "1.0.0"
tier: "TIER-7/APEX"
domain: "Court monitoring — docket scraping, deadline computation, filing verification, judge tracking"
triggers:
  - docket
  - court monitoring
  - deadline
  - filing confirmation
  - docket entry
  - MiCOURT
  - CourtListener
  - PACER
---

# SINGULARITY-MBP-APEX-DOCKET — Real-Time Court Docket Intelligence

> **Tier:** APEX (Tier 7) — Maximum autonomy, real-time monitoring, zero-miss deadline enforcement
> **Domain:** Court docket monitoring, deadline computation, filing verification, judge tracking
> **Stack:** Python asyncio + httpx + SQLite WAL + DuckDB analytics + D3.js overlay
> **Courts:** 14th Circuit (Muskegon), 60th District, MI Court of Appeals, MI Supreme Court, USDC WDMI

## Mission

Ensure ZERO missed deadlines, ZERO undetected docket entries, and ZERO surprise orders across
all active Pigors v. Watson cases. Every new court filing, order, or hearing notice triggers
automatic deadline computation, priority alerting, and graph visualization updates within seconds
of detection.

---

## Table of Contents

1. [Michigan Court Docket Architecture](#1-michigan-court-docket-architecture)
2. [Federal Court Integration](#2-federal-court-integration)
3. [Deadline Intelligence Engine](#3-deadline-intelligence-engine)
4. [Real-Time Monitoring Pipeline](#4-real-time-monitoring-pipeline)
5. [Alert and Notification System](#5-alert-and-notification-system)
6. [Filing Confirmation Tracking](#6-filing-confirmation-tracking)
7. [Judge Assignment Intelligence](#7-judge-assignment-intelligence)
8. [Case Matrix Integration](#8-case-matrix-integration)
9. [D3 Graph Integration](#9-d3-graph-integration)
10. [Data Persistence](#10-data-persistence)
11. [Anti-Patterns](#11-anti-patterns)
12. [Performance Budgets](#12-performance-budgets)
13. [Activation Matrix](#13-activation-matrix)

---

## 1. Michigan Court Docket Architecture

### 1.1 MiCOURT REST API Client

Michigan's Odyssey-based court management system exposes docket data through the MiCOURT
portal. The client must handle authentication, session management, and rate limiting for
sustained monitoring across multiple case numbers.

#### Authentication Flow

```python
"""
MiCOURT API client for Michigan state court docket monitoring.
Handles session auth, case lookup, docket retrieval, and rate limiting.
"""
import httpx
import asyncio
import hashlib
import time
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

logger = logging.getLogger("apex_docket.micourt")

MICOURT_BASE = "https://micourt.courts.michigan.gov/api/v1"
MICOURT_SEARCH = f"{MICOURT_BASE}/case/search"
MICOURT_DOCKET = f"{MICOURT_BASE}/case/{{case_id}}/docket"
MICOURT_FILING = f"{MICOURT_BASE}/case/{{case_id}}/filings"

# Rate limits: MiCOURT allows ~120 requests/hour per IP
RATE_LIMIT_REQUESTS = 100  # conservative margin
RATE_LIMIT_WINDOW = 3600   # seconds
MIN_POLL_INTERVAL = 14400  # 4 hours between full polls

@dataclass
class RateLimiter:
    """Token-bucket rate limiter for court API calls."""
    max_tokens: int = RATE_LIMIT_REQUESTS
    window_seconds: int = RATE_LIMIT_WINDOW
    tokens: int = field(default=RATE_LIMIT_REQUESTS)
    last_refill: float = field(default_factory=time.monotonic)

    def acquire(self) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        if elapsed >= self.window_seconds:
            self.tokens = self.max_tokens
            self.last_refill = now
        if self.tokens > 0:
            self.tokens -= 1
            return True
        return False

    @property
    def wait_time(self) -> float:
        if self.tokens > 0:
            return 0.0
        elapsed = time.monotonic() - self.last_refill
        return max(0.0, self.window_seconds - elapsed)


@dataclass
class MiCourtSession:
    """Authenticated session for MiCOURT API access."""
    session_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    rate_limiter: RateLimiter = field(default_factory=RateLimiter)
    client: Optional[httpx.AsyncClient] = None

    async def ensure_client(self):
        if self.client is None or self.client.is_closed:
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                headers={
                    "User-Agent": "LitigationOS-DocketMonitor/1.0",
                    "Accept": "application/json",
                },
                follow_redirects=True,
            )
        return self.client

    async def authenticate(self, username: str, password: str) -> bool:
        """Authenticate with MiCOURT. Credentials from env vars or keyring."""
        client = await self.ensure_client()
        try:
            resp = await client.post(
                f"{MICOURT_BASE}/auth/login",
                json={"username": username, "password": password},
            )
            if resp.status_code == 200:
                data = resp.json()
                self.session_token = data.get("token")
                ttl = data.get("expires_in", 3600)
                self.expires_at = datetime.now() + timedelta(seconds=ttl)
                self.client.headers["Authorization"] = f"Bearer {self.session_token}"
                logger.info("MiCOURT auth success, expires %s", self.expires_at)
                return True
            logger.error("MiCOURT auth failed: %d %s", resp.status_code, resp.text)
            return False
        except httpx.HTTPError as e:
            logger.error("MiCOURT auth HTTP error: %s", e)
            return False

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return True
        return datetime.now() >= self.expires_at - timedelta(minutes=5)

    async def close(self):
        if self.client and not self.client.is_closed:
            await self.client.aclose()
```

#### Case Search by Number, Party Name, Attorney

```python
@dataclass
class CaseSearchResult:
    case_id: str
    case_number: str
    court_name: str
    case_type: str
    filing_date: str
    parties: list
    judge: str
    status: str


async def search_case(
    session: MiCourtSession,
    *,
    case_number: Optional[str] = None,
    party_name: Optional[str] = None,
    attorney_name: Optional[str] = None,
    court_id: Optional[str] = None,
) -> list[CaseSearchResult]:
    """
    Search MiCOURT by case number, party name, or attorney.
    Supports wildcards in case number (e.g., '2024-001507-*').
    """
    if not session.rate_limiter.acquire():
        wait = session.rate_limiter.wait_time
        logger.warning("Rate limited — waiting %.1fs", wait)
        await asyncio.sleep(wait)
        session.rate_limiter.acquire()

    client = await session.ensure_client()
    params = {}
    if case_number:
        params["caseNumber"] = case_number
    if party_name:
        params["partyName"] = party_name
    if attorney_name:
        params["attorneyName"] = attorney_name
    if court_id:
        params["courtId"] = court_id

    results = []
    page = 1
    while True:
        params["page"] = page
        params["pageSize"] = 50
        try:
            resp = await client.get(MICOURT_SEARCH, params=params)
            resp.raise_for_status()
            data = resp.json()
            cases = data.get("cases", [])
            if not cases:
                break
            for c in cases:
                results.append(CaseSearchResult(
                    case_id=c["caseId"],
                    case_number=c["caseNumber"],
                    court_name=c["courtName"],
                    case_type=c["caseType"],
                    filing_date=c["filingDate"],
                    parties=c.get("parties", []),
                    judge=c.get("assignedJudge", "Unknown"),
                    status=c.get("status", "Unknown"),
                ))
            if len(cases) < 50:
                break
            page += 1
        except httpx.HTTPStatusError as e:
            logger.error("MiCOURT search HTTP %d: %s", e.response.status_code, e)
            break
        except httpx.HTTPError as e:
            logger.error("MiCOURT search error: %s", e)
            break
    return results
```

#### Docket Entry Retrieval with Pagination

```python
@dataclass
class DocketEntry:
    entry_id: str
    entry_date: str
    entry_text: str
    filing_party: Optional[str]
    document_type: Optional[str]
    page_count: Optional[int]
    judge: Optional[str]
    filed_by: Optional[str]
    amount: Optional[float]
    raw_data: dict = field(default_factory=dict)

    @property
    def fingerprint(self) -> str:
        """Content hash for dedup across polls."""
        content = f"{self.entry_date}|{self.entry_text}|{self.filing_party}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


async def get_docket_entries(
    session: MiCourtSession,
    case_id: str,
    *,
    since_date: Optional[str] = None,
    max_pages: int = 10,
) -> list[DocketEntry]:
    """
    Retrieve all docket entries for a case.
    Paginate through results; optionally filter to entries after since_date.
    """
    if not session.rate_limiter.acquire():
        await asyncio.sleep(session.rate_limiter.wait_time)
        session.rate_limiter.acquire()

    client = await session.ensure_client()
    url = MICOURT_DOCKET.format(case_id=case_id)
    entries = []
    page = 1

    while page <= max_pages:
        params = {"page": page, "pageSize": 100}
        if since_date:
            params["fromDate"] = since_date
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("entries", [])
            if not items:
                break
            for item in items:
                entries.append(DocketEntry(
                    entry_id=item.get("entryId", ""),
                    entry_date=item.get("entryDate", ""),
                    entry_text=item.get("description", ""),
                    filing_party=item.get("filingParty"),
                    document_type=item.get("documentType"),
                    page_count=item.get("pageCount"),
                    judge=item.get("judge"),
                    filed_by=item.get("filedBy"),
                    amount=item.get("amount"),
                    raw_data=item,
                ))
            if len(items) < 100:
                break
            page += 1
        except httpx.HTTPError as e:
            logger.error("Docket fetch error for %s page %d: %s", case_id, page, e)
            break

    return sorted(entries, key=lambda e: e.entry_date)
```

#### Filing Status Check

```python
@dataclass
class FilingStatus:
    filing_id: str
    case_number: str
    document_title: str
    filed_date: str
    status: str          # SUBMITTED, ACCEPTED, REJECTED, DOCKETED
    rejection_reason: Optional[str] = None
    docket_entry_id: Optional[str] = None
    envelope_number: Optional[str] = None


async def check_filing_status(
    session: MiCourtSession,
    case_id: str,
    filing_id: Optional[str] = None,
) -> list[FilingStatus]:
    """
    Check filing acceptance status on MiFILE/MiCOURT.
    If filing_id is None, returns all recent filings for the case.
    """
    if not session.rate_limiter.acquire():
        await asyncio.sleep(session.rate_limiter.wait_time)
        session.rate_limiter.acquire()

    client = await session.ensure_client()
    url = MICOURT_FILING.format(case_id=case_id)
    params = {}
    if filing_id:
        params["filingId"] = filing_id

    try:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        return [
            FilingStatus(
                filing_id=f["filingId"],
                case_number=f["caseNumber"],
                document_title=f["title"],
                filed_date=f["filedDate"],
                status=f["status"],
                rejection_reason=f.get("rejectionReason"),
                docket_entry_id=f.get("docketEntryId"),
                envelope_number=f.get("envelopeNumber"),
            )
            for f in data.get("filings", [])
        ]
    except httpx.HTTPError as e:
        logger.error("Filing status check error: %s", e)
        return []
```

#### Retry Logic with Exponential Backoff

```python
import random

async def retry_with_backoff(
    coro_factory,
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: bool = True,
):
    """
    Retry an async operation with exponential backoff.
    coro_factory must be a callable returning a fresh coroutine each call.
    """
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            return await coro_factory()
        except (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException) as e:
            last_exc = e
            if attempt == max_retries:
                break
            delay = min(base_delay * (2 ** attempt), max_delay)
            if jitter:
                delay *= 0.5 + random.random()
            logger.warning(
                "Retry %d/%d after %.1fs: %s", attempt + 1, max_retries, delay, e
            )
            await asyncio.sleep(delay)
    raise last_exc
```

### 1.2 TrueFiling Integration (COA / MSC)

TrueFiling is the e-filing system for the Michigan Court of Appeals and Supreme Court.
Filing confirmation and acceptance tracking requires monitoring the TrueFiling receipt
and mapping it back to the case docket.

```python
TRUEFILING_BASE = "https://michigan.truefiling.com/api"

@dataclass
class TrueFilingReceipt:
    envelope_id: str
    case_number: str
    court: str
    filed_date: str
    accepted_date: Optional[str]
    status: str          # SUBMITTED, UNDER_REVIEW, ACCEPTED, REJECTED
    documents: list
    filing_fee_paid: bool
    fee_amount: float
    confirmation_number: Optional[str]


async def check_truefiling_status(
    client: httpx.AsyncClient,
    envelope_id: str,
) -> Optional[TrueFilingReceipt]:
    """Check TrueFiling envelope acceptance status."""
    try:
        resp = await client.get(
            f"{TRUEFILING_BASE}/envelope/{envelope_id}/status"
        )
        resp.raise_for_status()
        data = resp.json()
        return TrueFilingReceipt(
            envelope_id=data["envelopeId"],
            case_number=data["caseNumber"],
            court=data["court"],
            filed_date=data["filedDate"],
            accepted_date=data.get("acceptedDate"),
            status=data["status"],
            documents=data.get("documents", []),
            filing_fee_paid=data.get("feePaid", False),
            fee_amount=data.get("feeAmount", 0.0),
            confirmation_number=data.get("confirmationNumber"),
        )
    except httpx.HTTPError as e:
        logger.error("TrueFiling status check error: %s", e)
        return None
```

### 1.3 MiFILE Integration (Circuit Court)

MiFILE handles electronic filing for Michigan trial courts including the 14th Circuit.
Filings submitted through MiFILE receive an envelope number that must be tracked
through acceptance and docketing.

```python
MIFILE_BASE = "https://mifile.courts.michigan.gov/api"

@dataclass
class MiFileEnvelope:
    envelope_id: str
    case_number: str
    court_code: str
    submitted_at: str
    status: str          # PENDING, ACCEPTED, REJECTED, RETURNED
    filed_documents: list
    return_reason: Optional[str] = None
    docket_confirmation: Optional[str] = None
    fee_status: str = "UNKNOWN"


async def check_mifile_envelope(
    client: httpx.AsyncClient,
    envelope_id: str,
) -> Optional[MiFileEnvelope]:
    """Check MiFILE envelope status for Circuit Court filings."""
    try:
        resp = await client.get(
            f"{MIFILE_BASE}/filings/envelope/{envelope_id}"
        )
        resp.raise_for_status()
        data = resp.json()
        return MiFileEnvelope(
            envelope_id=data["envelopeId"],
            case_number=data["caseNumber"],
            court_code=data["courtCode"],
            submitted_at=data["submittedAt"],
            status=data["status"],
            filed_documents=data.get("documents", []),
            return_reason=data.get("returnReason"),
            docket_confirmation=data.get("docketConfirmation"),
            fee_status=data.get("feeStatus", "UNKNOWN"),
        )
    except httpx.HTTPError as e:
        logger.error("MiFILE envelope check error: %s", e)
        return None
```

---

## 2. Federal Court Integration

### 2.1 PACER API Client (Western District of Michigan)

PACER (Public Access to Court Electronic Records) provides federal court docket access.
PACER charges per-page fees; the RECAP archive on CourtListener provides free cached copies.
Always check RECAP first, then fall back to PACER when needed.

```python
PACER_BASE = "https://pcl.uscourts.gov/pcl-public-api/rest"
PACER_SEARCH = f"{PACER_BASE}/cases/find"
PACER_DOCKET = f"{PACER_BASE}/cases/{{case_id}}/docket-entries"
RECAP_BASE = "https://www.courtlistener.com/api/rest/v4"

# PACER fee: $0.10/page, $3.00 cap per document
PACER_FEE_PER_PAGE = 0.10
PACER_FEE_CAP = 3.00

@dataclass
class PacerCredentials:
    """PACER login credentials — NEVER hardcode. Use env vars or keyring."""
    username: str
    password: str
    client_code: str = ""

    @classmethod
    def from_env(cls) -> "PacerCredentials":
        import os
        return cls(
            username=os.environ["PACER_USERNAME"],
            password=os.environ["PACER_PASSWORD"],
            client_code=os.environ.get("PACER_CLIENT_CODE", ""),
        )


@dataclass
class PacerSession:
    """Authenticated PACER session with cost tracking."""
    token: Optional[str] = None
    expires_at: Optional[datetime] = None
    total_cost: float = 0.0
    page_count: int = 0
    client: Optional[httpx.AsyncClient] = None
    rate_limiter: RateLimiter = field(
        default_factory=lambda: RateLimiter(max_tokens=60, window_seconds=60)
    )

    async def authenticate(self, creds: PacerCredentials) -> bool:
        """Authenticate with PACER NextGen API."""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                headers={"Accept": "application/json"},
            )
        try:
            resp = await self.client.post(
                f"{PACER_BASE}/login",
                json={
                    "loginId": creds.username,
                    "password": creds.password,
                    "clientCode": creds.client_code,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                self.token = data.get("nextGenCSO")
                ttl = data.get("expiresIn", 7200)
                self.expires_at = datetime.now() + timedelta(seconds=ttl)
                self.client.headers["X-NEXT-GEN-CSO"] = self.token
                logger.info("PACER auth success, expires %s", self.expires_at)
                return True
            logger.error("PACER auth failed: %d", resp.status_code)
            return False
        except httpx.HTTPError as e:
            logger.error("PACER auth error: %s", e)
            return False

    def track_cost(self, pages: int):
        cost = min(pages * PACER_FEE_PER_PAGE, PACER_FEE_CAP)
        self.total_cost += cost
        self.page_count += pages
        logger.info("PACER cost: +$%.2f (total $%.2f, %d pages)", cost, self.total_cost, self.page_count)
```

#### Case Search and Docket Report

```python
@dataclass
class FederalDocketEntry:
    entry_number: int
    date_filed: str
    description: str
    document_number: Optional[int]
    page_count: Optional[int]
    attachments: list
    filed_by: Optional[str]
    nature_of_filing: Optional[str]

    @property
    def fingerprint(self) -> str:
        content = f"{self.entry_number}|{self.date_filed}|{self.description}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


async def pacer_search_case(
    session: PacerSession,
    *,
    case_number: Optional[str] = None,
    party_name: Optional[str] = None,
    court_id: str = "miwb",  # Western District of Michigan
) -> list[dict]:
    """Search PACER for federal cases in Western District of Michigan."""
    if not session.rate_limiter.acquire():
        await asyncio.sleep(session.rate_limiter.wait_time)
        session.rate_limiter.acquire()

    params = {"courtId": court_id}
    if case_number:
        params["caseNumberFull"] = case_number
    if party_name:
        params["lastName"] = party_name

    try:
        resp = await session.client.get(PACER_SEARCH, params=params)
        resp.raise_for_status()
        data = resp.json()
        session.track_cost(1)
        return data.get("content", [])
    except httpx.HTTPError as e:
        logger.error("PACER search error: %s", e)
        return []


async def pacer_get_docket(
    session: PacerSession,
    case_id: str,
    *,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> list[FederalDocketEntry]:
    """Retrieve federal docket entries from PACER."""
    if not session.rate_limiter.acquire():
        await asyncio.sleep(session.rate_limiter.wait_time)
        session.rate_limiter.acquire()

    url = PACER_DOCKET.format(case_id=case_id)
    params = {}
    if date_from:
        params["dateFrom"] = date_from
    if date_to:
        params["dateTo"] = date_to

    try:
        resp = await session.client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        entries_raw = data.get("content", [])
        page_total = sum(e.get("pageCount", 0) for e in entries_raw)
        session.track_cost(max(1, page_total))
        return [
            FederalDocketEntry(
                entry_number=e.get("entryNumber", 0),
                date_filed=e.get("dateFiled", ""),
                description=e.get("description", ""),
                document_number=e.get("documentNumber"),
                page_count=e.get("pageCount"),
                attachments=e.get("attachments", []),
                filed_by=e.get("filedBy"),
                nature_of_filing=e.get("natureOfFiling"),
            )
            for e in entries_raw
        ]
    except httpx.HTTPError as e:
        logger.error("PACER docket error: %s", e)
        return []
```

### 2.2 RECAP / CourtListener Free Alternative

CourtListener's RECAP archive provides free access to many federal court documents.
Always check RECAP before paying PACER fees.

```python
@dataclass
class RecapResult:
    docket_id: int
    case_name: str
    case_number: str
    court: str
    date_filed: str
    entries: list
    is_complete: bool


async def recap_search(
    client: httpx.AsyncClient,
    case_number: str,
    court: str = "miwb",
) -> Optional[RecapResult]:
    """Search CourtListener RECAP for free cached docket data."""
    try:
        resp = await client.get(
            f"{RECAP_BASE}/dockets/",
            params={
                "docket_number": case_number,
                "court": court,
                "order_by": "-date_modified",
            },
            headers={"Authorization": f"Token {_get_cl_token()}"},
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if not results:
            return None

        docket = results[0]
        return RecapResult(
            docket_id=docket["id"],
            case_name=docket.get("case_name", ""),
            case_number=docket.get("docket_number", ""),
            court=docket.get("court", ""),
            date_filed=docket.get("date_filed", ""),
            entries=docket.get("docket_entries", []),
            is_complete=bool(docket.get("docket_entries")),
        )
    except httpx.HTTPError as e:
        logger.error("RECAP search error: %s", e)
        return None


def _get_cl_token() -> str:
    """Get CourtListener API token from environment."""
    import os
    return os.environ.get("COURTLISTENER_TOKEN", "")
```

### 2.3 RSS Feed Monitoring for Near Real-Time Updates

Federal courts publish RSS feeds for new docket entries. This provides near-real-time
monitoring without PACER fees.

```python
import xml.etree.ElementTree as ET

WDMI_RSS = "https://ecf.miwd.uscourts.gov/cgi-bin/rss_outside.pl"

@dataclass
class RSSEntry:
    title: str
    link: str
    pub_date: str
    case_number: str
    description: str
    guid: str


async def poll_federal_rss(
    client: httpx.AsyncClient,
    court_rss_url: str = WDMI_RSS,
    case_numbers: Optional[set] = None,
) -> list[RSSEntry]:
    """
    Poll federal court RSS feed for new docket entries.
    Filter to only our watched case numbers if provided.
    """
    try:
        resp = await client.get(court_rss_url, timeout=15.0)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        entries = []
        for item in root.findall(".//item"):
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            pub_date = item.findtext("pubDate", "")
            desc = item.findtext("description", "")
            guid = item.findtext("guid", link)

            case_num = _extract_case_number_from_rss(title)
            if case_numbers and case_num not in case_numbers:
                continue

            entries.append(RSSEntry(
                title=title,
                link=link,
                pub_date=pub_date,
                case_number=case_num,
                description=desc,
                guid=guid,
            ))
        return entries
    except (httpx.HTTPError, ET.ParseError) as e:
        logger.error("RSS poll error: %s", e)
        return []


def _extract_case_number_from_rss(title: str) -> str:
    """Extract case number from RSS title like '1:26-cv-00123 Pigors v. Watson'."""
    import re
    match = re.search(r"(\d+:\d+-\w+-\d+)", title)
    return match.group(1) if match else ""
```

### 2.4 CourtListener Webhook Setup

```python
async def register_courtlistener_webhook(
    client: httpx.AsyncClient,
    docket_id: int,
    callback_url: str,
) -> bool:
    """
    Register a webhook on CourtListener for real-time docket updates.
    Fires on new docket entries, minute orders, and opinions.
    """
    try:
        resp = await client.post(
            f"{RECAP_BASE}/alerts/",
            json={
                "docket": docket_id,
                "alert_type": 1,  # docket alert
                "name": f"LitigationOS-{docket_id}",
                "callback_url": callback_url,
            },
            headers={"Authorization": f"Token {_get_cl_token()}"},
        )
        resp.raise_for_status()
        logger.info("CourtListener webhook registered for docket %d", docket_id)
        return True
    except httpx.HTTPError as e:
        logger.error("Webhook registration error: %s", e)
        return False
```

---

## 3. Deadline Intelligence Engine

### 3.1 Michigan Court Rule Deadline Computation

The deadline engine encodes Michigan Court Rules as computable rules. Each rule specifies
a trigger event (e.g., "motion served"), the number of days to the deadline, whether
weekends/holidays adjust the date, and whether mail service adds 3 days.

```python
from datetime import date
from enum import Enum
from typing import NamedTuple

class DeadlineType(Enum):
    RESPONSE = "response"
    HEARING = "hearing"
    FILING = "filing"
    APPEAL = "appeal"
    SERVICE = "service"
    COMPLIANCE = "compliance"

class DayCountType(Enum):
    CALENDAR = "calendar"
    BUSINESS = "business"
    COURT = "court"     # excludes court holidays

class DeadlineRule(NamedTuple):
    rule_citation: str
    description: str
    trigger_event: str
    days: int
    day_count_type: DayCountType
    deadline_type: DeadlineType
    mail_extension_days: int     # MCR 2.107(C)(3): +3 for mail service
    adjusts_for_weekend: bool    # MCR 1.108: if last day is weekend/holiday, extend
    notes: str


# ────────────────────────────────────────────────────────────────────────────
# MICHIGAN COURT RULE DEADLINE TABLE (comprehensive)
# ────────────────────────────────────────────────────────────────────────────

MICHIGAN_DEADLINE_RULES: list[DeadlineRule] = [
    # ── MCR 2.108: Responsive Pleading ──
    DeadlineRule(
        rule_citation="MCR 2.108(A)(1)",
        description="Answer to complaint",
        trigger_event="complaint_served",
        days=21,
        day_count_type=DayCountType.CALENDAR,
        deadline_type=DeadlineType.RESPONSE,
        mail_extension_days=3,
        adjusts_for_weekend=True,
        notes="21 days after service; +3 if served by mail",
    ),
    DeadlineRule(
        rule_citation="MCR 2.108(A)(2)",
        description="Answer after default set aside",
        trigger_event="default_set_aside",
        days=7,
        day_count_type=DayCountType.CALENDAR,
        deadline_type=DeadlineType.RESPONSE,
        mail_extension_days=0,
        adjusts_for_weekend=True,
        notes="7 days after default set aside or as ordered",
    ),

    # ── MCR 2.116: Summary Disposition ──
    DeadlineRule(
        rule_citation="MCR 2.116(B)(1)",
        description="Response to summary disposition motion",
        trigger_event="summary_disposition_served",
        days=21,
        day_count_type=DayCountType.CALENDAR,
        deadline_type=DeadlineType.RESPONSE,
        mail_extension_days=3,
        adjusts_for_weekend=True,
        notes="21 days after service of motion; cross-motion also 21 days",
    ),
    DeadlineRule(
        rule_citation="MCR 2.116(B)(4)",
        description="Reply brief for summary disposition",
        trigger_event="summary_disposition_response_filed",
        days=7,
        day_count_type=DayCountType.CALENDAR,
        deadline_type=DeadlineType.RESPONSE,
        mail_extension_days=0,
        adjusts_for_weekend=True,
        notes="7 days after response is filed",
    ),

    # ── MCR 2.119: Motion Practice ──
    DeadlineRule(
        rule_citation="MCR 2.119(C)(1)",
        description="Response to motion",
        trigger_event="motion_served",
        days=21,
        day_count_type=DayCountType.CALENDAR,
        deadline_type=DeadlineType.RESPONSE,
        mail_extension_days=3,
        adjusts_for_weekend=True,
        notes="Standard response time for noticed motions",
    ),
    DeadlineRule(
        rule_citation="MCR 2.119(C)(2)",
        description="Reply brief to motion",
        trigger_event="motion_response_filed",
        days=7,
        day_count_type=DayCountType.CALENDAR,
        deadline_type=DeadlineType.RESPONSE,
        mail_extension_days=0,
        adjusts_for_weekend=True,
        notes="Optional reply brief, 7 days after response",
    ),
    DeadlineRule(
        rule_citation="MCR 2.119(E)(3)",
        description="Motion for reconsideration",
        trigger_event="order_entered",
        days=21,
        day_count_type=DayCountType.CALENDAR,
        deadline_type=DeadlineType.FILING,
        mail_extension_days=0,
        adjusts_for_weekend=True,
        notes="21 days from entry of order being challenged",
    ),
    DeadlineRule(
        rule_citation="MCR 2.119(F)(1)",
        description="Hearing notice — minimum advance",
        trigger_event="motion_filed",
        days=9,
        day_count_type=DayCountType.CALENDAR,
        deadline_type=DeadlineType.HEARING,
        mail_extension_days=3,
        adjusts_for_weekend=False,
        notes="Hearing must be at least 9 days after service of motion",
    ),

    # ── MCR 3.206: Custody / Parenting Time Modification ──
    DeadlineRule(
        rule_citation="MCR 3.206(C)(2)",
        description="Response to custody motion",
        trigger_event="custody_motion_served",
        days=21,
        day_count_type=DayCountType.CALENDAR,
        deadline_type=DeadlineType.RESPONSE,
        mail_extension_days=3,
        adjusts_for_weekend=True,
        notes="Response to motion to modify custody/parenting time per MCL 722.27",
    ),
    DeadlineRule(
        rule_citation="MCR 3.206(D)(2)",
        description="FOC investigation deadline",
        trigger_event="foc_investigation_ordered",
        days=56,
        day_count_type=DayCountType.CALENDAR,
        deadline_type=DeadlineType.COMPLIANCE,
        mail_extension_days=0,
        adjusts_for_weekend=False,
        notes="FOC must complete investigation within 56 days unless extended",
    ),

    # ── MCR 3.707: Personal Protection Orders ──
    DeadlineRule(
        rule_citation="MCR 3.707(A)(1)",
        description="PPO hearing after respondent request",
        trigger_event="ppo_hearing_requested",
        days=14,
        day_count_type=DayCountType.CALENDAR,
        deadline_type=DeadlineType.HEARING,
        mail_extension_days=0,
        adjusts_for_weekend=True,
        notes="Court must hold hearing within 14 days of respondent's request",
    ),
    DeadlineRule(
        rule_citation="MCR 3.707(A)(2)",
        description="Motion to terminate PPO",
        trigger_event="ppo_issued",
        days=0,     # can be filed at any time
        day_count_type=DayCountType.CALENDAR,
        deadline_type=DeadlineType.FILING,
        mail_extension_days=0,
        adjusts_for_weekend=False,
        notes="Motion to terminate/modify PPO may be filed at any time; no day limit",
    ),

    # ── MCR 7.204/7.205: Appeals of Right / Leave to Appeal ──
    DeadlineRule(
        rule_citation="MCR 7.204(A)(1)",
        description="Claim of appeal — appeal of right",
        trigger_event="final_order_entered",
        days=21,
        day_count_type=DayCountType.CALENDAR,
        deadline_type=DeadlineType.APPEAL,
        mail_extension_days=0,
        adjusts_for_weekend=True,
        notes="File claim of appeal within 21 days of final order or judgment",
    ),
    DeadlineRule(
        rule_citation="MCR 7.205(A)",
        description="Application for leave to appeal",
        trigger_event="order_entered",
        days=21,
        day_count_type=DayCountType.CALENDAR,
        deadline_type=DeadlineType.APPEAL,
        mail_extension_days=0,
        adjusts_for_weekend=True,
        notes="Leave application within 21 days of order; may be extended for good cause",
    ),
    DeadlineRule(
        rule_citation="MCR 7.205(F)(3)",
        description="Response to application for leave",
        trigger_event="leave_application_served",
        days=21,
        day_count_type=DayCountType.CALENDAR,
        deadline_type=DeadlineType.RESPONSE,
        mail_extension_days=3,
        adjusts_for_weekend=True,
        notes="Opposing party response to leave application",
    ),

    # ── MCR 7.212: Appellate Briefs ──
    DeadlineRule(
        rule_citation="MCR 7.212(A)(1)(a)",
        description="Appellant's brief — appeal of right",
        trigger_event="claim_of_appeal_filed",
        days=56,
        day_count_type=DayCountType.CALENDAR,
        deadline_type=DeadlineType.FILING,
        mail_extension_days=0,
        adjusts_for_weekend=True,
        notes="56 days from filing claim of appeal; may request extension",
    ),
    DeadlineRule(
        rule_citation="MCR 7.212(A)(1)(b)",
        description="Appellee's brief",
        trigger_event="appellant_brief_served",
        days=35,
        day_count_type=DayCountType.CALENDAR,
        deadline_type=DeadlineType.FILING,
        mail_extension_days=0,
        adjusts_for_weekend=True,
        notes="35 days after appellant's brief is served",
    ),
    DeadlineRule(
        rule_citation="MCR 7.212(A)(1)(c)",
        description="Appellant's reply brief",
        trigger_event="appellee_brief_served",
        days=21,
        day_count_type=DayCountType.CALENDAR,
        deadline_type=DeadlineType.FILING,
        mail_extension_days=0,
        adjusts_for_weekend=True,
        notes="Optional reply brief, 21 days after appellee's brief",
    ),

    # ── MCR 7.305: MSC Application ──
    DeadlineRule(
        rule_citation="MCR 7.305(C)(2)",
        description="Application for leave to appeal to MSC",
        trigger_event="coa_decision_issued",
        days=42,
        day_count_type=DayCountType.CALENDAR,
        deadline_type=DeadlineType.APPEAL,
        mail_extension_days=0,
        adjusts_for_weekend=True,
        notes="42 days from COA decision to apply to MSC",
    ),
    DeadlineRule(
        rule_citation="MCR 7.305(F)",
        description="Emergency application to MSC",
        trigger_event="emergency_arises",
        days=0,
        day_count_type=DayCountType.CALENDAR,
        deadline_type=DeadlineType.FILING,
        mail_extension_days=0,
        adjusts_for_weekend=False,
        notes="Emergency application may be filed at any time; no day limit",
    ),

    # ── MCR 7.306: Superintending Control ──
    DeadlineRule(
        rule_citation="MCR 7.306(A)",
        description="Complaint for superintending control",
        trigger_event="lower_court_action",
        days=0,
        day_count_type=DayCountType.CALENDAR,
        deadline_type=DeadlineType.FILING,
        mail_extension_days=0,
        adjusts_for_weekend=False,
        notes="No specific deadline; file when no adequate remedy exists",
    ),

    # ── MCR 2.612: Relief from Judgment ──
    DeadlineRule(
        rule_citation="MCR 2.612(C)(1)",
        description="Motion for relief from judgment (a)(b)(c)",
        trigger_event="judgment_entered",
        days=365,
        day_count_type=DayCountType.CALENDAR,
        deadline_type=DeadlineType.FILING,
        mail_extension_days=0,
        adjusts_for_weekend=False,
        notes="Grounds (a)(b)(c) must be filed within 1 year; ground (f) reasonable time",
    ),

    # ── MCR 2.003: Disqualification ──
    DeadlineRule(
        rule_citation="MCR 2.003(D)(1)",
        description="Motion for disqualification of judge",
        trigger_event="bias_discovered",
        days=0,
        day_count_type=DayCountType.CALENDAR,
        deadline_type=DeadlineType.FILING,
        mail_extension_days=0,
        adjusts_for_weekend=False,
        notes="File as soon as reasonable after discovering grounds for disqualification",
    ),

    # ── MCR 3.606: Contempt ──
    DeadlineRule(
        rule_citation="MCR 3.606(A)",
        description="Motion for contempt (civil)",
        trigger_event="order_violated",
        days=0,
        day_count_type=DayCountType.CALENDAR,
        deadline_type=DeadlineType.FILING,
        mail_extension_days=0,
        adjusts_for_weekend=False,
        notes="File when order violation occurs; no day limit but act promptly",
    ),
]


# ────────────────────────────────────────────────────────────────────────────
# MICHIGAN COURT HOLIDAY CALENDAR
# ────────────────────────────────────────────────────────────────────────────

def michigan_court_holidays(year: int) -> set[date]:
    """
    Return Michigan court holidays for a given year.
    Per MCR 8.110 and Michigan state government holiday schedule.
    """
    from dateutil.easter import easter

    holidays = set()

    # Fixed-date holidays
    holidays.add(date(year, 1, 1))    # New Year's Day
    holidays.add(date(year, 7, 4))    # Independence Day
    holidays.add(date(year, 11, 11))  # Veterans Day
    holidays.add(date(year, 12, 25))  # Christmas Day
    holidays.add(date(year, 12, 31))  # New Year's Eve (MI courts close)

    # MLK Day: 3rd Monday of January
    jan1 = date(year, 1, 1)
    first_monday = jan1 + timedelta(days=(7 - jan1.weekday()) % 7)
    holidays.add(first_monday + timedelta(weeks=2))

    # Presidents Day: 3rd Monday of February
    feb1 = date(year, 2, 1)
    first_monday = feb1 + timedelta(days=(7 - feb1.weekday()) % 7)
    holidays.add(first_monday + timedelta(weeks=2))

    # Memorial Day: last Monday of May
    may31 = date(year, 5, 31)
    holidays.add(may31 - timedelta(days=may31.weekday()))

    # Juneteenth
    holidays.add(date(year, 6, 19))

    # Labor Day: 1st Monday of September
    sep1 = date(year, 9, 1)
    holidays.add(sep1 + timedelta(days=(7 - sep1.weekday()) % 7))

    # Columbus/Indigenous Peoples Day: 2nd Monday of October
    oct1 = date(year, 10, 1)
    first_monday = oct1 + timedelta(days=(7 - oct1.weekday()) % 7)
    holidays.add(first_monday + timedelta(weeks=1))

    # Election Day: Tuesday after first Monday in November (even years)
    if year % 2 == 0:
        nov1 = date(year, 11, 1)
        first_monday = nov1 + timedelta(days=(7 - nov1.weekday()) % 7)
        holidays.add(first_monday + timedelta(days=1))

    # Thanksgiving: 4th Thursday of November
    nov1 = date(year, 11, 1)
    first_thurs = nov1 + timedelta(days=(3 - nov1.weekday()) % 7)
    thanksgiving = first_thurs + timedelta(weeks=3)
    holidays.add(thanksgiving)
    holidays.add(thanksgiving + timedelta(days=1))  # Day after Thanksgiving

    # Observed-date adjustment: if holiday falls on Saturday → Friday;
    # if on Sunday → Monday
    adjusted = set()
    for h in holidays:
        if h.weekday() == 5:   # Saturday
            adjusted.add(h - timedelta(days=1))
        elif h.weekday() == 6: # Sunday
            adjusted.add(h + timedelta(days=1))
        else:
            adjusted.add(h)
    return adjusted
```

### 3.2 Deadline Computation Engine

```python
def compute_deadline(
    trigger_date: date,
    rule: DeadlineRule,
    *,
    served_by_mail: bool = False,
) -> date:
    """
    Compute a deadline from a trigger event and a Michigan Court Rule.
    Handles:
    - Mail service extension (+3 days per MCR 2.107(C)(3))
    - Weekend/holiday adjustment per MCR 1.108
    - Calendar vs business day computation
    """
    if rule.days == 0:
        return trigger_date  # no day limit (e.g., contempt, superintending control)

    total_days = rule.days
    if served_by_mail and rule.mail_extension_days > 0:
        total_days += rule.mail_extension_days

    if rule.day_count_type == DayCountType.CALENDAR:
        deadline = trigger_date + timedelta(days=total_days)
    elif rule.day_count_type == DayCountType.BUSINESS:
        deadline = _add_business_days(trigger_date, total_days)
    else:
        deadline = _add_court_days(trigger_date, total_days)

    if rule.adjusts_for_weekend:
        deadline = _adjust_for_weekend_holiday(deadline)

    return deadline


def _add_business_days(start: date, days: int) -> date:
    """Add business days (Mon-Fri), skipping weekends."""
    current = start
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:  # Mon-Fri
            added += 1
    return current


def _add_court_days(start: date, days: int) -> date:
    """Add court days (Mon-Fri excluding court holidays)."""
    holidays = michigan_court_holidays(start.year)
    if start.month >= 11:
        holidays |= michigan_court_holidays(start.year + 1)
    current = start
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5 and current not in holidays:
            added += 1
    return current


def _adjust_for_weekend_holiday(d: date) -> date:
    """
    MCR 1.108: If the last day falls on a Saturday, Sunday, or legal
    holiday, the period runs until the end of the next day that is not
    a Saturday, Sunday, or legal holiday.
    """
    holidays = michigan_court_holidays(d.year)
    while d.weekday() >= 5 or d in holidays:
        d += timedelta(days=1)
        if d.month == 1 and d.day <= 3:
            holidays |= michigan_court_holidays(d.year)
    return d
```

### 3.3 Auto-Compute Response Deadlines from New Docket Entries

```python
import re

# Docket entry patterns → trigger events for deadline computation
ENTRY_PATTERN_MAP: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"ORDER", re.I), "order_entered", "MCR 2.119(E)(3)"),
    (re.compile(r"MOTION\s+(?:FOR|TO)", re.I), "motion_served", "MCR 2.119(C)(1)"),
    (re.compile(r"SUMMARY\s+DISPOSITION", re.I), "summary_disposition_served", "MCR 2.116(B)(1)"),
    (re.compile(r"SHOW\s+CAUSE", re.I), "order_entered", "MCR 3.606(A)"),
    (re.compile(r"NOTICE\s+OF\s+HEARING", re.I), "hearing_scheduled", ""),
    (re.compile(r"COMPLAINT", re.I), "complaint_served", "MCR 2.108(A)(1)"),
    (re.compile(r"CLAIM\s+OF\s+APPEAL", re.I), "claim_of_appeal_filed", "MCR 7.212(A)(1)(a)"),
    (re.compile(r"BRIEF\s+(?:OF|FOR)\s+APPELLANT", re.I), "appellant_brief_served", "MCR 7.212(A)(1)(b)"),
    (re.compile(r"BRIEF\s+(?:OF|FOR)\s+APPELLEE", re.I), "appellee_brief_served", "MCR 7.212(A)(1)(c)"),
    (re.compile(r"APPLICATION\s+FOR\s+LEAVE", re.I), "leave_application_served", "MCR 7.205(F)(3)"),
    (re.compile(r"PPO|PROTECTION\s+ORDER", re.I), "ppo_issued", "MCR 3.707(A)(1)"),
    (re.compile(r"OPINION", re.I), "coa_decision_issued", "MCR 7.305(C)(2)"),
    (re.compile(r"DEFAULT", re.I), "default_set_aside", "MCR 2.108(A)(2)"),
    (re.compile(r"CUSTODY|PARENTING\s+TIME", re.I), "custody_motion_served", "MCR 3.206(C)(2)"),
    (re.compile(r"CONTEMPT", re.I), "order_violated", "MCR 3.606(A)"),
    (re.compile(r"RECONSIDERATION", re.I), "order_entered", "MCR 2.119(E)(3)"),
]

# Build a lookup from trigger_event → DeadlineRule
_RULE_LOOKUP: dict[str, DeadlineRule] = {}
for rule in MICHIGAN_DEADLINE_RULES:
    _RULE_LOOKUP.setdefault(rule.trigger_event, rule)


def classify_docket_entry(entry_text: str) -> tuple[str, str]:
    """
    Classify a docket entry to determine its trigger event and applicable rule.
    Returns (trigger_event, rule_citation) or ("unknown", "").
    """
    for pattern, trigger, citation in ENTRY_PATTERN_MAP:
        if pattern.search(entry_text):
            return trigger, citation
    return "unknown", ""


def compute_deadlines_from_entry(
    entry_text: str,
    entry_date: date,
    *,
    served_by_mail: bool = False,
) -> list[dict]:
    """
    Given a new docket entry, compute all applicable deadlines.
    Returns a list of deadline dicts with date, rule, and description.
    """
    trigger, citation = classify_docket_entry(entry_text)
    if trigger == "unknown":
        return []

    results = []
    for rule in MICHIGAN_DEADLINE_RULES:
        if rule.trigger_event == trigger:
            dl = compute_deadline(entry_date, rule, served_by_mail=served_by_mail)
            results.append({
                "deadline_date": dl.isoformat(),
                "rule_citation": rule.rule_citation,
                "description": rule.description,
                "trigger_event": trigger,
                "trigger_date": entry_date.isoformat(),
                "served_by_mail": served_by_mail,
                "days_until": (dl - date.today()).days,
                "notes": rule.notes,
            })
    return results
```

### 3.4 Deadline Cascading

```python
def compute_cascade(
    initial_trigger: str,
    initial_date: date,
    served_by_mail: bool = False,
) -> list[dict]:
    """
    Compute the full cascade of deadlines from an initial event.
    Example: filing → service → response → hearing → order → reconsideration.
    """
    CASCADE_CHAINS = {
        "motion_served": [
            ("motion_served", "MCR 2.119(C)(1)"),
            ("motion_response_filed", "MCR 2.119(C)(2)"),
        ],
        "complaint_served": [
            ("complaint_served", "MCR 2.108(A)(1)"),
        ],
        "summary_disposition_served": [
            ("summary_disposition_served", "MCR 2.116(B)(1)"),
            ("summary_disposition_response_filed", "MCR 2.116(B)(4)"),
        ],
        "claim_of_appeal_filed": [
            ("claim_of_appeal_filed", "MCR 7.212(A)(1)(a)"),
            ("appellant_brief_served", "MCR 7.212(A)(1)(b)"),
            ("appellee_brief_served", "MCR 7.212(A)(1)(c)"),
        ],
    }

    chain = CASCADE_CHAINS.get(initial_trigger, [(initial_trigger, "")])
    results = []
    current_date = initial_date

    for trigger, _ in chain:
        rule = _RULE_LOOKUP.get(trigger)
        if rule is None:
            continue
        use_mail = served_by_mail if trigger == initial_trigger else False
        dl = compute_deadline(current_date, rule, served_by_mail=use_mail)
        results.append({
            "step": trigger,
            "trigger_date": current_date.isoformat(),
            "deadline_date": dl.isoformat(),
            "rule": rule.rule_citation,
            "description": rule.description,
            "days_until": (dl - date.today()).days,
        })
        current_date = dl
    return results
```

### 3.5 Statute of Limitations Tracking

```python
STATUTES_OF_LIMITATION: list[dict] = [
    {
        "claim": "42 USC § 1983 (civil rights)",
        "period_years": 3,
        "borrowing_state": "Michigan",
        "notes": "Borrows MI personal injury SOL — MCL 600.5805(2)",
    },
    {
        "claim": "MCL 600.5805(2) — personal injury",
        "period_years": 3,
        "borrowing_state": None,
        "notes": "General tort including assault, battery, IIED",
    },
    {
        "claim": "MCL 600.5805(10) — fraud",
        "period_years": 6,
        "borrowing_state": None,
        "notes": "Fraud on the court; runs from discovery of fraud",
    },
    {
        "claim": "MCL 600.5807(8) — contract",
        "period_years": 6,
        "borrowing_state": None,
        "notes": "Breach of contract (e.g., Shady Oaks lease)",
    },
    {
        "claim": "MCL 600.5813 — conversion",
        "period_years": 3,
        "borrowing_state": None,
        "notes": "Property conversion (e.g., personal property removed from home)",
    },
    {
        "claim": "MCL 600.5851 — minor's claims",
        "period_years": 1,
        "borrowing_state": None,
        "notes": "Runs from child reaching age 18; relevant for L.D.W.",
    },
]


def check_sol(
    claim_type: str,
    accrual_date: date,
    check_date: Optional[date] = None,
) -> dict:
    """Check whether a statute of limitations has expired for a claim type."""
    if check_date is None:
        check_date = date.today()

    for sol in STATUTES_OF_LIMITATION:
        if claim_type.lower() in sol["claim"].lower():
            expiration = accrual_date + timedelta(days=sol["period_years"] * 365)
            days_remaining = (expiration - check_date).days
            return {
                "claim": sol["claim"],
                "accrual_date": accrual_date.isoformat(),
                "expiration_date": expiration.isoformat(),
                "days_remaining": days_remaining,
                "expired": days_remaining < 0,
                "notes": sol["notes"],
            }
    return {"error": f"Unknown claim type: {claim_type}"}
```

---

## 4. Real-Time Monitoring Pipeline

### 4.1 Polling Architecture

```python
import sqlite3
from contextlib import contextmanager

# Polling intervals per court system
POLL_INTERVALS = {
    "micourt": 14400,       # 4 hours (rate limit safe)
    "federal_rss": 900,     # 15 minutes (RSS is free)
    "courtlistener": 0,     # webhook-driven, no polling
    "mifile": 7200,         # 2 hours (filing status checks)
    "truefiling": 7200,     # 2 hours (COA/MSC filing status)
    "manual": 0,            # user-triggered only
}

# Active cases to monitor
WATCHED_CASES = {
    "A": {"number": "2024-001507-DC", "court": "14th Circuit", "system": "micourt", "lane": "A"},
    "D": {"number": "2023-5907-PP", "court": "14th Circuit", "system": "micourt", "lane": "D"},
    "F": {"number": "366810", "court": "MI Court of Appeals", "system": "truefiling", "lane": "F"},
    "CRIMINAL": {"number": "2025-25245676SM", "court": "60th District", "system": "micourt", "lane": "CRIMINAL"},
}

@contextmanager
def get_monitor_db(db_path: str = "litigation_context.db"):
    """Get DB connection with correct PRAGMAs for docket monitoring."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA cache_size = -32000")
    conn.execute("PRAGMA temp_store = MEMORY")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


class DocketMonitor:
    """
    Main monitoring loop. Polls each court system at its configured interval,
    detects new entries, computes deadlines, and dispatches alerts.
    """

    def __init__(self, db_path: str = "litigation_context.db"):
        self.db_path = db_path
        self.last_poll: dict[str, float] = {}
        self.known_fingerprints: set[str] = set()
        self._load_known_fingerprints()

    def _load_known_fingerprints(self):
        """Load already-processed entry fingerprints from DB to avoid re-alerting."""
        with get_monitor_db(self.db_path) as conn:
            try:
                rows = conn.execute(
                    "SELECT entry_fingerprint FROM docket_monitor WHERE is_processed = 1"
                ).fetchall()
                self.known_fingerprints = {r["entry_fingerprint"] for r in rows}
            except sqlite3.OperationalError:
                self.known_fingerprints = set()

    def should_poll(self, system: str) -> bool:
        """Check if enough time has elapsed since last poll for this system."""
        interval = POLL_INTERVALS.get(system, 3600)
        if interval == 0:
            return False
        last = self.last_poll.get(system, 0)
        return (time.time() - last) >= interval

    async def poll_all(self):
        """Run one polling cycle across all court systems."""
        tasks = []
        for lane, case in WATCHED_CASES.items():
            system = case["system"]
            if self.should_poll(system):
                tasks.append(self._poll_case(lane, case))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _poll_case(self, lane: str, case_info: dict):
        """Poll a single case for new docket entries."""
        system = case_info["system"]
        case_number = case_info["number"]
        logger.info("Polling %s (%s) on %s", case_number, lane, system)
        self.last_poll[system] = time.time()

        # Actual API call would go here; simplified for architecture
        # entries = await get_docket_entries(session, case_id, since_date=last_check)
        # For each new entry:
        #   1. Check fingerprint against known_fingerprints
        #   2. Classify entry type
        #   3. Compute deadlines
        #   4. Persist to DB
        #   5. Dispatch alerts
```

### 4.2 New Docket Entry Detection

```python
class EntryType:
    ORDER = "ORDER"
    MOTION = "MOTION"
    HEARING_NOTICE = "HEARING_NOTICE"
    OPINION = "OPINION"
    SHOW_CAUSE = "SHOW_CAUSE"
    BRIEF = "BRIEF"
    RESPONSE = "RESPONSE"
    DEFAULT = "DEFAULT"
    STIPULATION = "STIPULATION"
    AFFIDAVIT = "AFFIDAVIT"
    JUDGMENT = "JUDGMENT"
    UNKNOWN = "UNKNOWN"


ENTRY_CLASSIFIERS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bORDER\b", re.I), EntryType.ORDER),
    (re.compile(r"\bSHOW\s+CAUSE\b", re.I), EntryType.SHOW_CAUSE),
    (re.compile(r"\bOPINION\b", re.I), EntryType.OPINION),
    (re.compile(r"\bJUDGMENT\b", re.I), EntryType.JUDGMENT),
    (re.compile(r"\bHEARING\s+NOTICE|NOTICE\s+OF\s+HEARING\b", re.I), EntryType.HEARING_NOTICE),
    (re.compile(r"\bMOTION\b", re.I), EntryType.MOTION),
    (re.compile(r"\bBRIEF\b", re.I), EntryType.BRIEF),
    (re.compile(r"\bRESPONSE|ANSWER\b", re.I), EntryType.RESPONSE),
    (re.compile(r"\bSTIPULATION\b", re.I), EntryType.STIPULATION),
    (re.compile(r"\bAFFIDAVIT\b", re.I), EntryType.AFFIDAVIT),
    (re.compile(r"\bDEFAULT\b", re.I), EntryType.DEFAULT),
]


def classify_entry(text: str) -> str:
    """Classify a docket entry by its text content."""
    for pattern, entry_type in ENTRY_CLASSIFIERS:
        if pattern.search(text):
            return entry_type
    return EntryType.UNKNOWN


def extract_filing_party(text: str) -> Optional[str]:
    """Extract the filing party from docket entry text."""
    patterns = [
        re.compile(r"filed\s+by\s+(.+?)(?:\.|$)", re.I),
        re.compile(r"(?:plaintiff|defendant|petitioner|respondent)\s+(\w[\w\s]+)", re.I),
    ]
    for p in patterns:
        m = p.search(text)
        if m:
            return m.group(1).strip()
    return None


def detect_new_entries(
    current: list[DocketEntry],
    known_fingerprints: set[str],
) -> list[DocketEntry]:
    """Return only entries not seen before (by content fingerprint)."""
    new = []
    for entry in current:
        if entry.fingerprint not in known_fingerprints:
            new.append(entry)
    return new
```

### 4.3 Event Classification Dispatch

```python
@dataclass
class DocketEvent:
    """Classified docket event with computed metadata."""
    entry: DocketEntry
    entry_type: str
    alert_priority: str      # P0, P1, P2, P3
    deadlines: list[dict]
    lane: str
    case_number: str


def process_new_entry(
    entry: DocketEntry,
    lane: str,
    case_number: str,
) -> DocketEvent:
    """
    Process a new docket entry: classify, compute priority, compute deadlines.
    """
    entry_type = classify_entry(entry.entry_text)

    # Priority assignment
    if entry_type in (EntryType.SHOW_CAUSE, EntryType.DEFAULT):
        priority = "P0"
    elif entry_type in (EntryType.ORDER, EntryType.JUDGMENT, EntryType.HEARING_NOTICE):
        priority = "P1"
    elif entry_type in (EntryType.MOTION, EntryType.RESPONSE, EntryType.BRIEF):
        priority = "P2"
    else:
        priority = "P3"

    # Compute deadlines from entry
    entry_date = date.fromisoformat(entry.entry_date) if entry.entry_date else date.today()
    deadlines = compute_deadlines_from_entry(
        entry.entry_text, entry_date, served_by_mail=False
    )

    return DocketEvent(
        entry=entry,
        entry_type=entry_type,
        alert_priority=priority,
        deadlines=deadlines,
        lane=lane,
        case_number=case_number,
    )
```

---

## 5. Alert and Notification System

### 5.1 Priority Level Definitions

| Level | Name | Trigger Examples | Response Time |
|-------|------|-----------------|---------------|
| **P0** | CRITICAL | Show cause, default, sanctions, bench warrant | Immediate — drop everything |
| **P1** | URGENT | New order, hearing scheduled, opinion issued | Within 4 hours |
| **P2** | IMPORTANT | Motion filed, response due, brief deadline | Within 24 hours |
| **P3** | INFO | Routine filings, certificate of service, fee payment | Log only |

### 5.2 Notification Channels

```python
import json
from pathlib import Path

ALERT_LOG_PATH = Path("logs/docket_alerts.jsonl")

@dataclass
class Alert:
    priority: str
    title: str
    body: str
    case_number: str
    lane: str
    deadline: Optional[str] = None
    rule_citation: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


def dispatch_alert(alert: Alert):
    """Dispatch alert through all configured channels."""
    # Channel 1: Structured JSON log (always)
    _log_alert(alert)
    # Channel 2: DB persistence (always)
    _persist_alert(alert)
    # Channel 3: Desktop notification (P0 and P1 only)
    if alert.priority in ("P0", "P1"):
        _desktop_notify(alert)
    # Channel 4: Console output (all priorities)
    _console_alert(alert)


def _log_alert(alert: Alert):
    """Append alert to structured JSON log file."""
    ALERT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ALERT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "priority": alert.priority,
            "title": alert.title,
            "body": alert.body,
            "case": alert.case_number,
            "lane": alert.lane,
            "deadline": alert.deadline,
            "rule": alert.rule_citation,
            "ts": alert.timestamp,
        }) + "\n")


def _persist_alert(alert: Alert):
    """Persist alert to litigation_context.db."""
    with get_monitor_db() as conn:
        conn.execute("""
            INSERT INTO docket_alerts (
                priority, title, body, case_number, lane,
                deadline_date, rule_citation, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            alert.priority, alert.title, alert.body,
            alert.case_number, alert.lane,
            alert.deadline, alert.rule_citation, alert.timestamp,
        ))
        conn.commit()


def _desktop_notify(alert: Alert):
    """Send Windows toast notification for critical alerts."""
    try:
        from plyer import notification
        notification.notify(
            title=f"[{alert.priority}] {alert.title}",
            message=alert.body[:256],
            app_name="LitigationOS Docket Monitor",
            timeout=30 if alert.priority == "P0" else 10,
        )
    except ImportError:
        logger.warning("plyer not installed — desktop notifications disabled")
    except Exception as e:
        logger.error("Desktop notification error: %s", e)


def _console_alert(alert: Alert):
    """Print alert to console with color coding."""
    colors = {"P0": "\033[91m", "P1": "\033[93m", "P2": "\033[96m", "P3": "\033[90m"}
    reset = "\033[0m"
    color = colors.get(alert.priority, "")
    print(f"{color}[{alert.priority}] {alert.title}: {alert.body}{reset}")
```

### 5.3 Alert Deduplication and Batching

```python
class AlertDeduplicator:
    """Prevent duplicate alerts for the same docket event."""

    def __init__(self, ttl_seconds: int = 86400):
        self.seen: dict[str, float] = {}
        self.ttl = ttl_seconds

    def is_duplicate(self, alert: Alert) -> bool:
        key = f"{alert.case_number}|{alert.title}|{alert.deadline}"
        now = time.time()
        # Expire old entries
        self.seen = {k: v for k, v in self.seen.items() if now - v < self.ttl}
        if key in self.seen:
            return True
        self.seen[key] = now
        return False


class AlertBatcher:
    """Batch low-priority alerts into periodic digests."""

    def __init__(self, batch_interval: int = 3600):
        self.queue: list[Alert] = []
        self.interval = batch_interval
        self.last_flush = time.time()

    def add(self, alert: Alert):
        if alert.priority in ("P0", "P1"):
            dispatch_alert(alert)  # immediate
        else:
            self.queue.append(alert)

    def flush_if_ready(self):
        if time.time() - self.last_flush >= self.interval and self.queue:
            digest = Alert(
                priority="P3",
                title=f"Docket Digest: {len(self.queue)} new entries",
                body="\n".join(f"- [{a.lane}] {a.title}" for a in self.queue[:20]),
                case_number="ALL",
                lane="ALL",
            )
            dispatch_alert(digest)
            self.queue.clear()
            self.last_flush = time.time()
```

---

## 6. Filing Confirmation Tracking

### 6.1 Filing Lifecycle State Machine

```
PREPARED ──► SUBMITTED ──► ACCEPTED ──► DOCKETED ──► SERVED
    │            │              │            │
    │            ▼              ▼            ▼
    │        REJECTED       RETURNED     PENDING
    │            │              │         SERVICE
    ▼            ▼              ▼
 ABANDONED   CORRECTED      RESUBMITTED
```

```python
FILING_STATES = [
    "PREPARED", "SUBMITTED", "ACCEPTED", "REJECTED",
    "RETURNED", "CORRECTED", "RESUBMITTED",
    "DOCKETED", "SERVED", "ABANDONED",
]

FILING_TRANSITIONS = {
    "PREPARED": ["SUBMITTED", "ABANDONED"],
    "SUBMITTED": ["ACCEPTED", "REJECTED", "RETURNED"],
    "ACCEPTED": ["DOCKETED"],
    "REJECTED": ["CORRECTED", "ABANDONED"],
    "RETURNED": ["RESUBMITTED", "ABANDONED"],
    "CORRECTED": ["SUBMITTED"],
    "RESUBMITTED": ["ACCEPTED", "REJECTED"],
    "DOCKETED": ["SERVED"],
    "SERVED": [],
    "ABANDONED": [],
}


@dataclass
class FilingTracker:
    filing_id: str
    case_number: str
    document_title: str
    lane: str
    current_state: str = "PREPARED"
    envelope_id: Optional[str] = None
    mc12_attached: bool = False
    fee_paid: bool = False
    fee_amount: float = 0.0
    submission_date: Optional[str] = None
    acceptance_date: Optional[str] = None
    docket_date: Optional[str] = None
    service_date: Optional[str] = None
    rejection_reason: Optional[str] = None
    history: list = field(default_factory=list)

    def transition(self, new_state: str, notes: str = ""):
        allowed = FILING_TRANSITIONS.get(self.current_state, [])
        if new_state not in allowed:
            raise ValueError(
                f"Invalid transition: {self.current_state} → {new_state}. "
                f"Allowed: {allowed}"
            )
        self.history.append({
            "from": self.current_state,
            "to": new_state,
            "timestamp": datetime.now().isoformat(),
            "notes": notes,
        })
        self.current_state = new_state

    def verify_service_proof(self) -> bool:
        """Verify MC 12 Certificate of Service is attached."""
        return self.mc12_attached
```

### 6.2 Filing Fee Verification

```python
FILING_FEES = {
    "circuit_motion": 20.00,
    "circuit_new_case": 175.00,
    "coa_appeal": 375.00,
    "msc_appeal": 375.00,
    "federal_complaint": 405.00,
    "federal_ifp": 0.00,
    "jtc_complaint": 0.00,
}


def verify_fee(filing_type: str, amount_paid: float, fee_waiver: bool = False) -> dict:
    """Verify correct filing fee was paid or waived."""
    expected = FILING_FEES.get(filing_type, 0.0)
    if fee_waiver:
        return {"ok": True, "expected": expected, "paid": 0.0, "waiver": True}
    if abs(amount_paid - expected) < 0.01:
        return {"ok": True, "expected": expected, "paid": amount_paid, "waiver": False}
    return {
        "ok": False,
        "expected": expected,
        "paid": amount_paid,
        "waiver": False,
        "shortfall": expected - amount_paid,
    }
```

---

## 7. Judge Assignment Intelligence

### 7.1 Judge-Case Tracking Matrix

```python
JUDGE_ASSIGNMENTS = {
    "2024-001507-DC": {
        "judge": "Hon. Jenny L. McNeill",
        "bar_number": "P58235",
        "court": "14th Circuit",
        "lane": "A",
        "conflicts": [
            "Spouse Cavan Berry is attorney magistrate at 60th District (990 Terrace St = FOC address)",
            "Former law partner with Chief Judge Hoopes at Ladas, Hoopes & McNeill",
            "Former law partner with Judge Ladas-Hoopes at same firm",
        ],
    },
    "2023-5907-PP": {
        "judge": "Hon. Jenny L. McNeill",
        "bar_number": "P58235",
        "court": "14th Circuit",
        "lane": "D",
        "conflicts": ["Same judge as Lane A — MCR 2.003 disqualification pending"],
    },
    "366810": {
        "judge": "Panel TBD",
        "bar_number": None,
        "court": "MI Court of Appeals",
        "lane": "F",
        "conflicts": [],
    },
    "2025-25245676SM": {
        "judge": "Hon. Kostrzewa",
        "bar_number": None,
        "court": "60th District",
        "lane": "CRIMINAL",
        "conflicts": ["Court where Cavan Berry (McNeill spouse) is attorney magistrate"],
    },
}


def detect_judge_conflict(case_number: str) -> list[str]:
    """Check for known judicial conflicts on a case."""
    info = JUDGE_ASSIGNMENTS.get(case_number)
    if not info:
        return []
    return info.get("conflicts", [])


def detect_reassignment(
    case_number: str,
    new_judge: str,
    previous_judge: str,
) -> dict:
    """
    Detect and analyze a judge reassignment event.
    Flag if reassigned TO a known compromised judge.
    """
    compromised = {"McNeill", "Hoopes", "Ladas-Hoopes"}
    is_concerning = any(name in new_judge for name in compromised)

    return {
        "case": case_number,
        "from": previous_judge,
        "to": new_judge,
        "is_concerning": is_concerning,
        "alert_priority": "P1" if is_concerning else "P3",
        "notes": "Reassigned to compromised judge" if is_concerning else "Routine reassignment",
    }
```

### 7.2 Cross-Reference with Judicial Violations

```python
def get_judge_violation_count(judge_name: str, db_path: str = "litigation_context.db") -> dict:
    """Query judicial_violations table for a specific judge."""
    with get_monitor_db(db_path) as conn:
        try:
            row = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN violation_type LIKE '%ex parte%' THEN 1 ELSE 0 END) as ex_parte,
                    SUM(CASE WHEN violation_type LIKE '%due process%' THEN 1 ELSE 0 END) as due_process,
                    SUM(CASE WHEN violation_type LIKE '%benchbook%' THEN 1 ELSE 0 END) as benchbook
                FROM judicial_violations
                WHERE judge_name LIKE ?
            """, (f"%{judge_name}%",)).fetchone()
            return dict(row) if row else {"total": 0}
        except sqlite3.OperationalError:
            return {"total": 0, "error": "judicial_violations table not found"}
```

---

## 8. Case Matrix Integration

### 8.1 Multi-Case Dashboard

```python
@dataclass
class CaseDashboardRow:
    lane: str
    case_number: str
    court: str
    judge: str
    status: str
    next_deadline: Optional[str]
    next_deadline_description: Optional[str]
    days_until_deadline: Optional[int]
    urgency: str             # OVERDUE, CRITICAL, URGENT, OK
    last_docket_entry: Optional[str]
    last_docket_date: Optional[str]


def build_dashboard(db_path: str = "litigation_context.db") -> list[CaseDashboardRow]:
    """Build multi-case dashboard with next deadlines and urgency levels."""
    rows = []
    for lane, case_info in WATCHED_CASES.items():
        with get_monitor_db(db_path) as conn:
            # Get next upcoming deadline
            try:
                dl = conn.execute("""
                    SELECT deadline_date, description
                    FROM deadlines
                    WHERE case_number = ? AND status = 'PENDING'
                    AND deadline_date >= date('now')
                    ORDER BY deadline_date ASC LIMIT 1
                """, (case_info["number"],)).fetchone()
            except sqlite3.OperationalError:
                dl = None

            # Get last docket entry
            try:
                last = conn.execute("""
                    SELECT entry_text, entry_date
                    FROM docket_monitor
                    WHERE case_number = ? ORDER BY entry_date DESC LIMIT 1
                """, (case_info["number"],)).fetchone()
            except sqlite3.OperationalError:
                last = None

        next_dl = dl["deadline_date"] if dl else None
        next_desc = dl["description"] if dl else None
        days_until = (date.fromisoformat(next_dl) - date.today()).days if next_dl else None

        if days_until is not None:
            if days_until < 0:
                urgency = "OVERDUE"
            elif days_until <= 3:
                urgency = "CRITICAL"
            elif days_until <= 7:
                urgency = "URGENT"
            else:
                urgency = "OK"
        else:
            urgency = "OK"

        judge_info = JUDGE_ASSIGNMENTS.get(case_info["number"], {})
        rows.append(CaseDashboardRow(
            lane=lane,
            case_number=case_info["number"],
            court=case_info["court"],
            judge=judge_info.get("judge", "TBD"),
            status="Active",
            next_deadline=next_dl,
            next_deadline_description=next_desc,
            days_until_deadline=days_until,
            urgency=urgency,
            last_docket_entry=last["entry_text"] if last else None,
            last_docket_date=last["entry_date"] if last else None,
        ))
    return rows
```

### 8.2 Cross-Case Deadline Conflict Detection

```python
def detect_deadline_conflicts(
    deadlines: list[dict],
    buffer_days: int = 2,
) -> list[dict]:
    """
    Detect cases where deadlines from different lanes fall within buffer_days
    of each other, requiring priority triage.
    """
    sorted_dl = sorted(deadlines, key=lambda d: d.get("deadline_date", ""))
    conflicts = []
    for i in range(len(sorted_dl) - 1):
        a = sorted_dl[i]
        b = sorted_dl[i + 1]
        da = date.fromisoformat(a["deadline_date"])
        db = date.fromisoformat(b["deadline_date"])
        gap = abs((db - da).days)
        if gap <= buffer_days and a.get("lane") != b.get("lane"):
            conflicts.append({
                "deadline_a": a,
                "deadline_b": b,
                "gap_days": gap,
                "recommendation": _prioritize(a, b),
            })
    return conflicts


def _prioritize(a: dict, b: dict) -> str:
    """Determine which deadline takes priority when they conflict."""
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    pa = priority_order.get(a.get("priority", "P3"), 3)
    pb = priority_order.get(b.get("priority", "P3"), 3)
    if pa < pb:
        return f"Prioritize {a['lane']} ({a['description']})"
    elif pb < pa:
        return f"Prioritize {b['lane']} ({b['description']})"
    return "Equal priority — file earliest deadline first"
```

---

## 9. D3 Graph Integration

### 9.1 Docket Events as Graph Nodes

Docket entries integrate into THEMANBEARPIG's 13-layer D3.js visualization as a dedicated
`DOCKET` layer. Each docket entry becomes a node; filing→order→response chains become links.

```javascript
// D3 node type for docket entries
const DOCKET_NODE_SCHEMA = {
    type: "DOCKET_ENTRY",
    layer: 14,                    // new layer added to 13-layer graph
    visual: {
        shape: "rect",           // rectangles for document nodes
        baseSize: { width: 24, height: 16 },
        cornerRadius: 3,
    },
    colorMap: {
        ORDER: "#ef4444",         // red — requires action
        MOTION: "#3b82f6",        // blue — filing activity
        HEARING_NOTICE: "#f59e0b", // amber — calendar event
        OPINION: "#8b5cf6",       // purple — appellate decision
        SHOW_CAUSE: "#dc2626",    // bright red — emergency
        BRIEF: "#06b6d4",         // cyan — appellate document
        RESPONSE: "#10b981",      // green — responsive filing
        DEFAULT: "#6b7280",       // gray — routine/unknown
    },
};

// Link types connecting docket nodes
const DOCKET_LINK_TYPES = {
    TRIGGERS: { stroke: "#f97316", dashArray: "5,3", label: "triggers" },
    RESPONDS_TO: { stroke: "#22c55e", dashArray: null, label: "responds to" },
    SUPERSEDES: { stroke: "#ef4444", dashArray: "8,4", label: "supersedes" },
    REFERENCES: { stroke: "#8b5cf6", dashArray: "2,2", label: "references" },
};
```

### 9.2 Temporal Layout

```javascript
// Force simulation configuration for docket timeline subgraph
const DOCKET_FORCE_CONFIG = {
    // Temporal x-axis: nodes positioned by date
    forceX: d3.forceX(d => timeScale(d.entry_date)).strength(0.8),
    // Lane separation on y-axis
    forceY: d3.forceY(d => laneScale(d.lane)).strength(0.6),
    // Prevent overlap
    collide: d3.forceCollide(d => d.size + 4).strength(0.7),
    // Weak charge to spread nodes
    charge: d3.forceManyBody().strength(-30).distanceMax(200),
};

function createDocketTimeline(entries, container, width, height) {
    const timeScale = d3.scaleTime()
        .domain(d3.extent(entries, d => new Date(d.entry_date)))
        .range([50, width - 50]);

    const laneScale = d3.scalePoint()
        .domain(["A", "D", "F", "CRIMINAL"])
        .range([80, height - 80])
        .padding(0.3);

    // Render nodes with pulse animation for new entries
    const nodes = container.selectAll(".docket-node")
        .data(entries, d => d.fingerprint)
        .join(
            enter => enter.append("rect")
                .attr("class", "docket-node")
                .attr("fill", d => DOCKET_NODE_SCHEMA.colorMap[d.entry_type] || "#6b7280")
                .attr("rx", 3)
                .call(enter => enter.transition().duration(800)
                    .attr("opacity", 1)
                    .attrTween("stroke-width", () => d3.interpolate(4, 1))
                ),
            update => update,
            exit => exit.transition().duration(300).attr("opacity", 0).remove()
        );
}
```

### 9.3 Pulse Animation for New Entries

```javascript
function pulseNewEntry(node) {
    node.append("circle")
        .attr("r", 0)
        .attr("fill", "none")
        .attr("stroke", "#f59e0b")
        .attr("stroke-width", 2)
        .transition()
        .duration(1500)
        .ease(d3.easeCircleOut)
        .attr("r", 30)
        .attr("stroke-opacity", 0)
        .remove();
}
```

---

## 10. Data Persistence

### 10.1 DB Schema for Docket Monitoring

```sql
-- Core docket monitoring table
CREATE TABLE IF NOT EXISTS docket_monitor (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_number TEXT NOT NULL,
    court TEXT NOT NULL,
    lane TEXT NOT NULL,
    entry_date TEXT,
    entry_text TEXT,
    entry_type TEXT,
    filing_party TEXT,
    document_type TEXT,
    page_count INTEGER,
    entry_fingerprint TEXT UNIQUE,
    computed_deadline TEXT,
    deadline_rule TEXT,
    alert_priority TEXT DEFAULT 'P3',
    is_processed INTEGER DEFAULT 0,
    raw_data TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_docket_case ON docket_monitor(case_number);
CREATE INDEX IF NOT EXISTS idx_docket_date ON docket_monitor(entry_date);
CREATE INDEX IF NOT EXISTS idx_docket_type ON docket_monitor(entry_type);
CREATE INDEX IF NOT EXISTS idx_docket_lane ON docket_monitor(lane);
CREATE INDEX IF NOT EXISTS idx_docket_fingerprint ON docket_monitor(entry_fingerprint);
CREATE INDEX IF NOT EXISTS idx_docket_priority ON docket_monitor(alert_priority);
CREATE INDEX IF NOT EXISTS idx_docket_unprocessed ON docket_monitor(is_processed) WHERE is_processed = 0;

-- Computed deadlines from docket entries
CREATE TABLE IF NOT EXISTS docket_deadlines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    docket_entry_id INTEGER REFERENCES docket_monitor(id),
    case_number TEXT NOT NULL,
    lane TEXT NOT NULL,
    deadline_date TEXT NOT NULL,
    rule_citation TEXT NOT NULL,
    description TEXT,
    trigger_event TEXT,
    trigger_date TEXT,
    served_by_mail INTEGER DEFAULT 0,
    status TEXT DEFAULT 'PENDING',  -- PENDING, MET, MISSED, WAIVED
    days_until INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_deadlines_date ON docket_deadlines(deadline_date);
CREATE INDEX IF NOT EXISTS idx_deadlines_status ON docket_deadlines(status);
CREATE INDEX IF NOT EXISTS idx_deadlines_case ON docket_deadlines(case_number);

-- Alert log
CREATE TABLE IF NOT EXISTS docket_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    priority TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    case_number TEXT,
    lane TEXT,
    deadline_date TEXT,
    rule_citation TEXT,
    is_read INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_alerts_priority ON docket_alerts(priority);
CREATE INDEX IF NOT EXISTS idx_alerts_unread ON docket_alerts(is_read) WHERE is_read = 0;

-- Filing lifecycle tracking
CREATE TABLE IF NOT EXISTS filing_lifecycle (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filing_id TEXT UNIQUE NOT NULL,
    case_number TEXT NOT NULL,
    lane TEXT NOT NULL,
    document_title TEXT,
    current_state TEXT DEFAULT 'PREPARED',
    envelope_id TEXT,
    mc12_attached INTEGER DEFAULT 0,
    fee_paid INTEGER DEFAULT 0,
    fee_amount REAL DEFAULT 0.0,
    submission_date TEXT,
    acceptance_date TEXT,
    docket_date TEXT,
    service_date TEXT,
    rejection_reason TEXT,
    state_history TEXT,  -- JSON array of transitions
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_filing_case ON filing_lifecycle(case_number);
CREATE INDEX IF NOT EXISTS idx_filing_state ON filing_lifecycle(current_state);
CREATE INDEX IF NOT EXISTS idx_filing_lane ON filing_lifecycle(lane);

-- Judge assignment tracking
CREATE TABLE IF NOT EXISTS judge_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_number TEXT NOT NULL,
    judge_name TEXT NOT NULL,
    bar_number TEXT,
    court TEXT,
    lane TEXT,
    assigned_date TEXT,
    removed_date TEXT,
    removal_reason TEXT,
    is_current INTEGER DEFAULT 1,
    conflicts TEXT,  -- JSON array
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_judge_case ON judge_assignments(case_number);
CREATE INDEX IF NOT EXISTS idx_judge_current ON judge_assignments(is_current) WHERE is_current = 1;
```

### 10.2 Integration with Existing Tables

```python
def sync_with_timeline_events(event: DocketEvent, db_path: str = "litigation_context.db"):
    """Sync a docket event to the timeline_events table."""
    with get_monitor_db(db_path) as conn:
        conn.execute("""
            INSERT OR IGNORE INTO timeline_events (
                event_date, event_description, event_type,
                source_document, actors, lane
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            event.entry.entry_date,
            event.entry.entry_text,
            event.entry_type,
            f"docket:{event.case_number}",
            event.entry.filing_party or "",
            event.lane,
        ))
        conn.commit()


def sync_with_deadlines_table(deadlines: list[dict], db_path: str = "litigation_context.db"):
    """Sync computed deadlines to the main deadlines table."""
    with get_monitor_db(db_path) as conn:
        for dl in deadlines:
            conn.execute("""
                INSERT OR IGNORE INTO deadlines (
                    case_number, deadline_date, description,
                    rule_citation, status, lane
                ) VALUES (?, ?, ?, ?, 'PENDING', ?)
            """, (
                dl.get("case_number", ""),
                dl["deadline_date"],
                dl["description"],
                dl["rule_citation"],
                dl.get("lane", ""),
            ))
        conn.commit()
```

---

## 11. Anti-Patterns

### Mandatory Rules — Violating Any of These Is a System Failure

| # | Anti-Pattern | Why It's Dangerous | Correct Approach |
|---|---|---|---|
| 1 | Hardcoded deadline day counts in filings or code | Day counts change with rule amendments; stale values cause missed deadlines | Always compute from `MICHIGAN_DEADLINE_RULES` table at runtime |
| 2 | Polling courts more frequently than their rate limit | IP ban, account suspension, or legal liability | Respect `POLL_INTERVALS`; use exponential backoff on 429/503 |
| 3 | PACER credentials in source code or config files | Credential theft, unauthorized PACER charges | Use `os.environ` or `keyring` library; never commit credentials |
| 4 | Ignoring weekend/holiday adjustments for deadlines | Filed one day late = waived right | Always run through `_adjust_for_weekend_holiday()` |
| 5 | Assuming docket entry text format is stable | Courts change CMS software, text formats drift | Parse defensively with fallback patterns; never fail on unrecognized format |
| 6 | Skipping filing confirmation verification | Filing rejected but treated as filed = missed deadline | Track every filing through `PREPARED → DOCKETED` lifecycle |
| 7 | Merging criminal lane data with civil lanes | Criminal discovery, strategy, and deadlines are 100% separate | Criminal lane has its own monitoring loop with zero cross-references |
| 8 | Auto-filing based on docket monitoring output | Pro se filings require human review for accuracy and strategy | Monitoring produces alerts and recommendations; human decides to file |
| 9 | Ignoring mail service extensions (+3 days) | MCR 2.107(C)(3) adds 3 calendar days when served by mail | Always check `served_by_mail` flag and add extension |
| 10 | Trusting MiCOURT 100% uptime | State court systems have maintenance windows and outages | Implement graceful degradation; cache last known state; retry on failure |
| 11 | Caching docket data without TTL expiration | Stale cache hides new entries; deadlines computed from old data | All cached docket data expires after `POLL_INTERVALS[system]` seconds |
| 12 | Alerting on already-processed entries | Alert fatigue; user ignores real emergencies buried in duplicates | Fingerprint-based dedup via `entry_fingerprint` column |
| 13 | Computing deadlines without verifying the source MCR | Wrong rule → wrong deadline → missed filing | Every computed deadline includes `rule_citation` traced to `MICHIGAN_DEADLINE_RULES` |
| 14 | Skipping statute of limitations check | Filing a time-barred claim wastes effort and damages credibility | Run `check_sol()` before recommending any new filing |
| 15 | Storing full document content downloaded from PACER | PACER terms of service restrict redistribution; storage costs | Store metadata and page counts only; link to PACER/RECAP for content |
| 16 | Using `datetime.now()` without timezone awareness | Court deadlines are in Eastern Time (Michigan); UTC offset matters | Use `datetime.now(tz=ZoneInfo("America/Detroit"))` for all court dates |
| 17 | Polling during court system maintenance windows | Wasted requests; potential for malformed responses during maintenance | Skip polls between 2-5 AM ET (common maintenance window) |
| 18 | Not verifying MC 12 (Proof of Service) attachment | Filing without service proof = defective service = potential default | `filing.verify_service_proof()` must return True before SUBMITTED state |

---

## 12. Performance Budgets

### Operation Latency Targets

| Operation | Budget | Technique | Failure Mode |
|-----------|--------|-----------|-------------|
| Docket poll (single case) | < 5s | Async HTTP with 30s timeout; circuit breaker on 3 failures | Degrade to cached + "stale" flag |
| Deadline computation | < 100ms | Pre-compiled `MICHIGAN_DEADLINE_RULES`; no DB lookup needed | Impossible to exceed with static rules |
| Alert dispatch (P0/P1) | < 500ms | Priority queue; desktop notify is async fire-and-forget | Log to file as fallback |
| Alert dispatch (P2/P3) | < 50ms | Append to batch queue; flush hourly | Queue in memory, flush on next cycle |
| DB persistence (single entry) | < 50ms | Single INSERT with WAL mode + 60s busy_timeout | Retry 3× with backoff |
| DB persistence (batch) | < 200ms | `executemany` for up to 100 entries | Split into smaller batches |
| Graph update (D3) | < 100ms | Incremental enter/update/exit; no full re-render | Debounce to 1 update per second |
| Dashboard refresh | < 500ms | Pre-computed dashboard rows; DuckDB for aggregates | Serve stale data + "computing" indicator |
| Full poll cycle (all cases) | < 30s | Parallel async polls; 4 cases × ~5s each | Timeout individual cases; partial results OK |
| Fingerprint dedup check | < 1ms | In-memory `set` of known fingerprints | Load from DB on startup; append as processed |

### Memory Budgets

| Component | Budget | Notes |
|-----------|--------|-------|
| Known fingerprints set | < 10 MB | ~500K fingerprints × 16 bytes each |
| Alert queue (P2/P3 batch) | < 1 MB | Max 1000 queued alerts before force-flush |
| Docket entry cache | < 50 MB | Last 10,000 entries across all cases |
| Rate limiter state | < 1 KB | Per-system token counts |
| Holiday calendar cache | < 10 KB | 2 years × ~20 holidays |

---

## 13. Activation Matrix

### When to Activate This Skill

| User Request | Activate? | Primary Action |
|---|---|---|
| "Check the docket" | ✅ | Poll all watched cases, report new entries |
| "What deadlines do I have?" | ✅ | Query `docket_deadlines` + `deadlines` tables |
| "Was my filing accepted?" | ✅ | Check MiFILE/TrueFiling envelope status |
| "Any new orders?" | ✅ | Filter docket entries by ORDER type |
| "Who is the judge on 366810?" | ✅ | Query `judge_assignments` table |
| "Compute deadline for motion served today" | ✅ | Run `compute_deadline()` with MCR 2.119 |
| "Show cause — what do I do?" | ✅ | P0 alert; compute response deadline |
| "Build impeachment package" | ❌ | Use `SINGULARITY-litigation-warfare` instead |
| "Draft a motion" | ❌ | Use `SINGULARITY-court-arsenal` instead |
| "Search evidence quotes" | ❌ | Use `search_evidence` tool instead |

### Multi-Skill Activation Patterns

| Task Pattern | Skills Activated Together |
|---|---|
| New order detected → draft response | **APEX-DOCKET** + court-arsenal + document-forge |
| Deadline approaching → prepare filing | **APEX-DOCKET** + litigation-warfare + court-arsenal |
| Judge reassigned → check conflicts | **APEX-DOCKET** + judicial-intelligence |
| Filing rejected → correct and refile | **APEX-DOCKET** + document-forge |
| Show cause issued → emergency motion | **APEX-DOCKET** + court-arsenal + litigation-warfare |
| COA brief deadline → build appendix | **APEX-DOCKET** + court-arsenal + document-forge |
| Cross-case deadline conflict | **APEX-DOCKET** (internal prioritization) |

### Integration Points with Existing Systems

| System | Integration | Data Flow |
|---|---|---|
| `litigation_context.db` | Read/write docket entries, deadlines, alerts | Bidirectional |
| `timeline_events` table | Write new docket events as timeline entries | Write-only |
| `deadlines` table | Write computed deadlines; read for dashboard | Bidirectional |
| `filing_packages` table | Read filing status; update lifecycle | Bidirectional |
| `judicial_violations` table | Read violation counts for judge intelligence | Read-only |
| NEXUS daemon | Route queries through warm SQLite/DuckDB connection | Read/write via daemon |
| THEMANBEARPIG D3 graph | Push new docket nodes via WebSocket or file | Write-only |
| `check_deadlines` tool | Consume computed deadlines for urgency display | Read-only |
| `filing_status` tool | Consume filing lifecycle state | Read-only |
| `compute_deadlines` tool | Use deadline engine for ad-hoc computation | Function call |

---

## Appendix A: Separation Counter Integration

Every docket monitoring report MUST include the father-son separation counter:

```python
from datetime import date

def separation_days() -> int:
    """Compute days since last contact with L.D.W. NEVER hardcode."""
    return (date.today() - date(2025, 7, 29)).days
```

**Current separation: `(today - 2025-07-29).days` days.** Compute dynamically, ALWAYS.

---

## Appendix B: Quick Reference — MCR Deadline Cheat Sheet

| Event | Rule | Days | Mail +3? | Weekend Adj? |
|---|---|---|---|---|
| Complaint served → Answer | MCR 2.108(A)(1) | 21 | ✅ | ✅ |
| Motion served → Response | MCR 2.119(C)(1) | 21 | ✅ | ✅ |
| Motion response → Reply | MCR 2.119(C)(2) | 7 | ❌ | ✅ |
| Order entered → Reconsideration | MCR 2.119(E)(3) | 21 | ❌ | ✅ |
| Motion filed → Hearing notice | MCR 2.119(F)(1) | 9 min | ✅ | ❌ |
| SJ motion → Response | MCR 2.116(B)(1) | 21 | ✅ | ✅ |
| SJ response → Reply | MCR 2.116(B)(4) | 7 | ❌ | ✅ |
| Final order → Claim of appeal | MCR 7.204(A)(1) | 21 | ❌ | ✅ |
| COA claim filed → Appellant's brief | MCR 7.212(A)(1)(a) | 56 | ❌ | ✅ |
| Appellant brief → Appellee brief | MCR 7.212(A)(1)(b) | 35 | ❌ | ✅ |
| Appellee brief → Reply brief | MCR 7.212(A)(1)(c) | 21 | ❌ | ✅ |
| COA decision → MSC application | MCR 7.305(C)(2) | 42 | ❌ | ✅ |
| Leave app served → Response | MCR 7.205(F)(3) | 21 | ✅ | ✅ |
| PPO hearing requested → Hearing | MCR 3.707(A)(1) | 14 | ❌ | ✅ |
| Judgment → Relief from judgment | MCR 2.612(C)(1) | 365 | ❌ | ❌ |

---

*END OF SINGULARITY-MBP-APEX-DOCKET SKILL v1.0.0 — 13 Sections · 28 MCR Rules Encoded · 18 Anti-Patterns · 4 Court Systems · Real-Time Pipeline*

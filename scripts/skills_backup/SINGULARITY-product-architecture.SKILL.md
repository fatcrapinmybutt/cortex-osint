---
name: SINGULARITY-product-architecture
description: "Transcendent product architecture system for commercial litigation platforms. Use when: SaaS design, multi-tenant architecture, API design (REST/GraphQL/gRPC), microservices, database sharding, Stripe billing, RBAC, deployment pipelines, monitoring, caching, rate limiting, webhooks, queue systems, FastAPI backends, PostgreSQL, Redis, Docker, Kubernetes, CI/CD, observability, performance optimization, privacy-safe demo mode, subscription tiers, commercial packaging, LitigationOS productization, white-label, marketplace."
---

# SINGULARITY-product-architecture — Transcendent Product Architecture

> **Absorbs:** backend-api, system-design, SaaS
> **Tier:** APP | **Domain:** Commercial Platform, Multi-Tenant, API, Infrastructure
> **Stack:** FastAPI · PostgreSQL · Redis · Docker · Kubernetes · Stripe · Celery · Prometheus

---

## 1. LitigationOS Commercial Architecture

### Product Tier Design

| Tier | Name | Target User | Monthly | Key Features |
|------|------|-------------|---------|--------------|
| FREE | Explorer | Pro se litigants | $0 | 1 case, 500 evidence items, basic search |
| PRO | Advocate | Active litigants | $29 | 5 cases, 10K evidence, FTS5, timeline |
| TEAM | Firm | Small law firms | $99 | 25 cases, unlimited evidence, analytics |
| ENTERPRISE | Platform | Large firms/orgs | Custom | Multi-tenant, API, SSO, SLA |

### System Architecture (High-Level)

```
                    ┌─────────────────────────────────┐
                    │         CDN (Cloudflare)         │
                    └─────────────┬───────────────────┘
                                  │
                    ┌─────────────▼───────────────────┐
                    │   Load Balancer (nginx/Traefik)  │
                    └──┬──────────┬───────────────┬───┘
                       │          │               │
              ┌────────▼──┐ ┌────▼─────┐  ┌──────▼──────┐
              │  Web App   │ │  API GW   │  │  WebSocket  │
              │ (Next.js)  │ │ (FastAPI) │  │  (Notify)   │
              └────────────┘ └────┬─────┘  └─────────────┘
                                  │
                    ┌─────────────▼───────────────────┐
                    │       Service Mesh               │
                    │  ┌─────┐ ┌──────┐ ┌──────────┐  │
                    │  │Evidence│Filing│ │ Analytics │  │
                    │  │Service│Engine│ │  Engine   │  │
                    │  └──┬──┘ └──┬──┘ └────┬─────┘  │
                    └─────┼──────┼─────────┼─────────┘
                          │      │         │
              ┌───────────▼──────▼─────────▼──────────┐
              │              Data Layer                 │
              │  ┌────────┐ ┌─────┐ ┌──────┐ ┌─────┐ │
              │  │PostgreSQL│Redis│ │S3/Minio│LanceDB│ │
              │  └────────┘ └─────┘ └──────┘ └─────┘ │
              └───────────────────────────────────────┘
```

---

## 2. Multi-Tenant Database Architecture

### Schema-per-Tenant (Recommended for Litigation Data Isolation)

```sql
-- Tenant registry in public schema
CREATE TABLE public.tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    plan TEXT NOT NULL DEFAULT 'free',
    schema_name TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    storage_quota_mb INT DEFAULT 500,
    case_limit INT DEFAULT 1,
    is_active BOOLEAN DEFAULT true
);

-- Create isolated schema per tenant
CREATE OR REPLACE FUNCTION create_tenant_schema(tenant_slug TEXT)
RETURNS VOID AS $$
DECLARE schema TEXT := 'tenant_' || replace(tenant_slug, '-', '_');
BEGIN
    EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I', schema);
    EXECUTE format('SET search_path TO %I', schema);

    -- Core tables per tenant
    CREATE TABLE cases (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        case_number TEXT NOT NULL,
        court TEXT,
        judge TEXT,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMPTZ DEFAULT now()
    );

    CREATE TABLE evidence_quotes (
        id BIGSERIAL PRIMARY KEY,
        case_id UUID REFERENCES cases(id),
        quote_text TEXT NOT NULL,
        source_file TEXT,
        category TEXT,
        lane TEXT,
        created_at TIMESTAMPTZ DEFAULT now()
    );

    CREATE TABLE filings (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        case_id UUID REFERENCES cases(id),
        filing_type TEXT NOT NULL,
        status TEXT DEFAULT 'draft',
        content JSONB,
        created_at TIMESTAMPTZ DEFAULT now()
    );

    RESET search_path;
END;
$$ LANGUAGE plpgsql;
```

### Tenant Context Middleware (FastAPI)

```python
from fastapi import Request, HTTPException
from contextvars import ContextVar

current_tenant: ContextVar[str] = ContextVar('current_tenant')

async def tenant_middleware(request: Request, call_next):
    tenant_slug = request.headers.get('X-Tenant-ID')
    if not tenant_slug:
        # Extract from subdomain: acme.litigationos.com
        host = request.headers.get('host', '')
        tenant_slug = host.split('.')[0] if '.' in host else None

    if not tenant_slug:
        raise HTTPException(status_code=400, detail="Tenant not identified")

    token = current_tenant.set(tenant_slug)
    try:
        response = await call_next(request)
    finally:
        current_tenant.reset(token)
    return response


def get_tenant_schema() -> str:
    slug = current_tenant.get()
    return f"tenant_{slug.replace('-', '_')}"
```

### Row-Level Security Alternative (Shared Schema)

```sql
-- For smaller deployments: shared tables with RLS
ALTER TABLE evidence_quotes ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON evidence_quotes
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- Set tenant context per request
SET app.current_tenant = 'abc-123-def';
```

---

## 3. API Design (FastAPI + OpenAPI)

### RESTful API Structure

```python
from fastapi import FastAPI, Depends, Query, Path
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime

app = FastAPI(
    title="LitigationOS API",
    version="1.0.0",
    description="Litigation intelligence platform API",
)

# --- Models ---

class EvidenceCreate(BaseModel):
    quote_text: str = Field(..., min_length=1, max_length=10000)
    source_file: Optional[str] = None
    category: Optional[str] = None
    lane: Optional[str] = Field(None, pattern=r'^[A-F]$')

class EvidenceResponse(BaseModel):
    id: int
    case_id: UUID
    quote_text: str
    source_file: Optional[str]
    category: Optional[str]
    lane: Optional[str]
    created_at: datetime

class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    per_page: int
    has_next: bool

# --- Routes ---

@app.post("/api/v1/cases/{case_id}/evidence", response_model=EvidenceResponse,
          status_code=201, tags=["evidence"])
async def create_evidence(
    case_id: UUID,
    body: EvidenceCreate,
    tenant: str = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
):
    """Create a new evidence quote linked to a case."""
    check_case_access(user, case_id, "write")
    return await evidence_service.create(tenant, case_id, body)


@app.get("/api/v1/cases/{case_id}/evidence", response_model=PaginatedResponse,
         tags=["evidence"])
async def list_evidence(
    case_id: UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    lane: Optional[str] = Query(None, pattern=r'^[A-F]$'),
    tenant: str = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
):
    """List evidence quotes with search and filtering."""
    check_case_access(user, case_id, "read")
    return await evidence_service.list(tenant, case_id, page, per_page, search, lane)
```

### API Versioning Strategy

```
/api/v1/...  — Current stable API
/api/v2/...  — Next version (breaking changes)
/api/beta/...— Experimental features (no SLA)
```

### Rate Limiting by Tier

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

TIER_LIMITS = {
    'free':       '100/hour',
    'pro':        '1000/hour',
    'team':       '5000/hour',
    'enterprise': '50000/hour',
}

@app.get("/api/v1/search")
@limiter.limit(lambda: TIER_LIMITS.get(current_plan(), '100/hour'))
async def search_evidence(request: Request, q: str):
    ...
```

---

## 4. Authentication & RBAC

### JWT + RBAC Architecture

```python
from enum import Enum

class Permission(str, Enum):
    CASE_READ = "case:read"
    CASE_WRITE = "case:write"
    EVIDENCE_READ = "evidence:read"
    EVIDENCE_WRITE = "evidence:write"
    FILING_READ = "filing:read"
    FILING_WRITE = "filing:write"
    ADMIN = "admin:all"
    BILLING = "billing:manage"

ROLE_PERMISSIONS = {
    'viewer':  {Permission.CASE_READ, Permission.EVIDENCE_READ, Permission.FILING_READ},
    'editor':  {Permission.CASE_READ, Permission.CASE_WRITE, Permission.EVIDENCE_READ,
                Permission.EVIDENCE_WRITE, Permission.FILING_READ, Permission.FILING_WRITE},
    'admin':   {p for p in Permission},
    'owner':   {p for p in Permission},
}

def require_permission(permission: Permission):
    async def check(user: User = Depends(get_current_user)):
        user_perms = ROLE_PERMISSIONS.get(user.role, set())
        if permission not in user_perms and Permission.ADMIN not in user_perms:
            raise HTTPException(403, "Insufficient permissions")
        return user
    return Depends(check)
```

---

## 5. Stripe Billing Integration

### Subscription Lifecycle

```python
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY

async def create_subscription(tenant_id: str, plan: str, payment_method: str):
    tenant = await get_tenant(tenant_id)

    if not tenant.stripe_customer_id:
        customer = stripe.Customer.create(
            email=tenant.owner_email,
            metadata={'tenant_id': tenant_id},
        )
        tenant.stripe_customer_id = customer.id
        await save_tenant(tenant)

    stripe.PaymentMethod.attach(payment_method, customer=tenant.stripe_customer_id)
    stripe.Customer.modify(tenant.stripe_customer_id,
                           invoice_settings={'default_payment_method': payment_method})

    subscription = stripe.Subscription.create(
        customer=tenant.stripe_customer_id,
        items=[{'price': PLAN_PRICE_IDS[plan]}],
        metadata={'tenant_id': tenant_id, 'plan': plan},
    )
    return subscription


# Webhook handler for subscription events
@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get('stripe-signature')
    event = stripe.Webhook.construct_event(payload, sig, settings.STRIPE_WEBHOOK_SECRET)

    if event.type == 'customer.subscription.updated':
        sub = event.data.object
        tenant_id = sub.metadata.get('tenant_id')
        await update_tenant_plan(tenant_id, sub.items.data[0].price.id, sub.status)
    elif event.type == 'customer.subscription.deleted':
        tenant_id = event.data.object.metadata.get('tenant_id')
        await downgrade_to_free(tenant_id)
    elif event.type == 'invoice.payment_failed':
        tenant_id = event.data.object.metadata.get('tenant_id')
        await notify_payment_failure(tenant_id)

    return {"status": "ok"}
```

---

## 6. Caching & Queue Architecture

### Redis Caching Strategy

```python
import redis.asyncio as redis
import json
from functools import wraps

pool = redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)

def cached(prefix: str, ttl: int = 300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = f"{prefix}:{hash(str(args) + str(kwargs))}"
            r = redis.Redis(connection_pool=pool)
            cached_val = await r.get(key)
            if cached_val:
                return json.loads(cached_val)
            result = await func(*args, **kwargs)
            await r.set(key, json.dumps(result, default=str), ex=ttl)
            return result
        return wrapper
    return decorator

# Cache invalidation on writes
async def invalidate_cache(tenant: str, entity: str):
    r = redis.Redis(connection_pool=pool)
    pattern = f"{entity}:{tenant}:*"
    async for key in r.scan_iter(pattern):
        await r.delete(key)
```

### Task Queue (Celery + Redis)

```python
from celery import Celery

celery_app = Celery('litigationos', broker=settings.REDIS_URL)
celery_app.conf.task_routes = {
    'tasks.ingest.*': {'queue': 'ingest'},
    'tasks.analytics.*': {'queue': 'analytics'},
    'tasks.notify.*': {'queue': 'notify'},
}

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def ingest_document(self, tenant_id: str, file_path: str):
    try:
        text = extract_pdf_text(file_path)
        atoms = atomize_document(text)
        store_evidence(tenant_id, atoms)
        invalidate_cache_sync(tenant_id, 'evidence')
    except Exception as exc:
        self.retry(exc=exc)
```

---

## 7. Deployment Architecture

### Docker Compose (Development)

```yaml
version: '3.9'
services:
  api:
    build: ./api
    ports: ["8000:8000"]
    environment:
      DATABASE_URL: postgresql://app:secret@db:5432/litigationos
      REDIS_URL: redis://cache:6379/0
    depends_on: [db, cache]

  web:
    build: ./web
    ports: ["3000:3000"]
    depends_on: [api]

  worker:
    build: ./api
    command: celery -A tasks worker -Q ingest,analytics,notify -c 4
    depends_on: [db, cache]

  db:
    image: postgres:16-alpine
    volumes: ["pgdata:/var/lib/postgresql/data"]
    environment:
      POSTGRES_DB: litigationos
      POSTGRES_USER: app
      POSTGRES_PASSWORD: secret

  cache:
    image: redis:7-alpine
    volumes: ["redisdata:/data"]

volumes:
  pgdata:
  redisdata:
```

### Monitoring Stack (Prometheus + Grafana)

```python
from prometheus_client import Counter, Histogram, Gauge

REQUEST_COUNT = Counter('http_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'Request latency', ['endpoint'])
ACTIVE_TENANTS = Gauge('active_tenants', 'Number of active tenants')
EVIDENCE_COUNT = Gauge('evidence_items_total', 'Total evidence items', ['tenant'])
QUEUE_SIZE = Gauge('task_queue_size', 'Pending tasks in queue', ['queue_name'])

@app.middleware("http")
async def metrics_middleware(request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    REQUEST_COUNT.labels(request.method, request.url.path, response.status_code).inc()
    REQUEST_LATENCY.labels(request.url.path).observe(duration)
    return response
```

---

## 8. Privacy-Safe Demo Mode

### Synthetic Data Generator

```python
import faker

fake = faker.Faker()

def generate_demo_case():
    return {
        'case_number': f"2024-{fake.random_int(100000, 999999)}-DC",
        'court': fake.random_element(['14th Circuit', '17th Circuit', '3rd Circuit']),
        'judge': f"Hon. {fake.first_name()} {fake.last_name()}",
        'parties': {
            'plaintiff': fake.name(),
            'defendant': fake.name(),
        },
        'evidence_count': fake.random_int(50, 500),
        'filing_count': fake.random_int(3, 15),
    }

def generate_demo_evidence(case_id, count=100):
    categories = ['custody', 'financial', 'communications', 'medical', 'police']
    return [{
        'case_id': case_id,
        'quote_text': fake.paragraph(nb_sentences=3),
        'source_file': f"exhibit_{fake.file_name(extension='pdf')}",
        'category': fake.random_element(categories),
        'lane': fake.random_element(['A', 'B', 'C', 'D', 'E', 'F']),
    } for _ in range(count)]
```

### Demo Mode Middleware

```python
DEMO_TENANT = "demo-sandbox"

async def demo_guard(request: Request, call_next):
    tenant = current_tenant.get(None)
    if tenant == DEMO_TENANT:
        if request.method in ('PUT', 'DELETE', 'PATCH'):
            raise HTTPException(403, "Demo mode: write operations are limited")
    return await call_next(request)
```

---

## 9. Scalability Patterns

### Connection Pooling (asyncpg)

```python
import asyncpg

class DatabasePool:
    def __init__(self):
        self._pool = None

    async def init(self):
        self._pool = await asyncpg.create_pool(
            dsn=settings.DATABASE_URL,
            min_size=5,
            max_size=20,
            command_timeout=30,
            statement_cache_size=100,
        )

    async def execute(self, query: str, *args, schema: str = 'public'):
        async with self._pool.acquire() as conn:
            await conn.execute(f"SET search_path TO {schema}")
            return await conn.fetch(query, *args)
```

### Horizontal Scaling Strategy

| Component | Scale Method | Trigger |
|-----------|-------------|---------|
| API servers | Horizontal (K8s HPA) | CPU > 70% or RPS > 500/pod |
| Workers | Horizontal (queue depth) | Queue depth > 100 |
| PostgreSQL | Read replicas | Read QPS > 1000 |
| Redis | Cluster mode | Memory > 80% |
| Storage | S3 lifecycle policies | Automatic tiering |

---

*SINGULARITY-product-architecture v1.0 — FastAPI + PostgreSQL + Redis + Stripe — Apex SaaS Platform*

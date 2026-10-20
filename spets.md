```markdown
# SPETSER AI — P0 EMERGENCY FIXES PROMPT
# Version: 1.0 | Severity: CRITICAL | Execution Mode: Autonomous Step-by-Step

==================================================
SECTION 0: YOUR IDENTITY AND AUTHORITY
==================================================

You are the **Emergency Incident Response Engineer** for `spetser-ai`. You have been deployed to fix three **P0 (Priority Zero)** production-blocking defects discovered after the `61e8a38` release.

You have FULL authority to:
- Read, write, create, and modify any file in the repository.
- Execute terminal commands (pytest, alembic, docker, git, grep, sed).
- Run all tests, builds, and linters.
- Roll back migrations if necessary.
- Make architectural decisions that override existing patterns when the existing pattern is demonstrably broken.

You must NOT:
- Skip any verification step.
- Declare a fix complete without passing tests.
- Update PROJECT_STATUS.md without evidence (real pytest output).
- Touch any code outside the P0 scope without explicit approval.
- Hardcode any secrets.

==================================================
SECTION 1: INCIDENT CONTEXT (THE THREE P0 DEFECTS)
==================================================

**Defect P0.1 — API Envelope Contract Breach**
- Symptom: After login, conversations and credits show as empty.
- Root Cause: The global error envelope `{data, error, request_id}` is applied ONLY to error responses (Lesson 10.4). Success responses return bare JSON (e.g., `{"balance": 300}`) or bare arrays (`[...]`). Frontend's `extractData()` assumes all responses are wrapped and always returns `undefined`.
- Impact: 90% of authenticated endpoints appear broken; only cookie-based auth (login page) survives.
- Fix: Apply envelope middleware to ALL `/api/v1/*` success responses (excluding SSE streams).

**Defect P0.2 — CORS Headers Missing on Error Responses**
- Symptom: Backend errors (404, 500) surface as opaque CORS errors in the browser; real error messages are hidden.
- Root Cause: FastAPI's `CORSMiddleware` runs OUTSIDE `ServerErrorMiddleware`. Generic `@app.exception_handler(Exception)` responses bypass CORS header injection. Also, `Authorization` is not in `allow_headers`, breaking API-key auth preflight.
- Impact: Developers cannot debug production errors; external API clients cannot authenticate.
- Fix: Inject CORS headers in all exception handlers; add `Authorization` and `X-API-Key` to `allow_headers`.

**Defect P0.3 — Migration `756afe1af465` Defects**
- Symptom: The latest migration (1 hour ago, adding developer panel + email verification) contains 6 latent bugs.
- Root Cause: Rushed migration without test coverage or consistency check.
- Defects:
  1. `ix_api_keys_key_hash` is NOT UNIQUE → `scalar_one_or_none()` can raise `MultipleResultsFound`.
  2. `api_keys.created_by` is `String(36)` — not `UUID` and has no `ForeignKey`.
  3. `system_settings.updated_at` is `NOT NULL` with NO `server_default` → `INSERT` fails.
  4. `server_default=sa.text('now()')` uses Postgres-only function → fails on SQLite.
  5. `allowed_skills` is plain `Text` instead of `JSONB` → no schema validation.
  6. No seed row inserted for `system_settings` → first read creates race condition.
- Fix: Replace the migration file with a corrected version that is idempotent and dialect-compatible.

==================================================
SECTION 2: EXECUTION PROTOCOL (MANDATORY FOR EVERY STEP)
==================================================

For EVERY sub-step, follow this exact sequence:

1. **ANNOUNCE:** State what you will do in one sentence.
2. **INSPECT:** Read the target file(s) first. Show relevant lines.
3. **PLAN:** List files to create/modify and the exact changes.
4. **IMPLEMENT:** Write the code.
5. **TEST:** Run the relevant test suite.
6. **FIX:** If any test fails, fix immediately. Do not proceed.
7. **DOCUMENT:** Update `docs/ERROR_LOG.md` (append) and `docs/PROJECT_STATUS.md` (replace Test Summary section).
8. **COMMIT:** Create a descriptive git commit.
9. **REPORT:** Summarize in the format below.

**REPORT FORMAT:**
```
✅ P0.X.Y — [Step name]
   Files modified: [list]
   Tests run: [command] → [X/Y passed]
   Evidence: [paste last 5 lines of test output]
   Committed: [hash]
```

**ERROR LOGGING (append to `docs/ERROR_LOG.md`):**
```
## E-XXX — [title]
| Field | Detail |
|---|---|
| **Date** | YYYY-MM-DD |
| **Severity** | P0 / P1 / P2 |
| **Phase** | P0.X |
| **Error** | [full error message] |
| **Root Cause** | [analysis] |
| **Fix** | [what was done] |
| **Verification** | [evidence it's fixed] |
| **Prevention** | [test added to prevent regression] |
```

==================================================
SECTION 3: P0.1 — FIX API ENVELOPE CONTRACT
==================================================

### Step 3.1: Write the Contract Test FIRST (TDD)

**Action:** Before touching any backend code, write a test that proves the defect exists and will catch regressions forever.

**File to create:** `backend/tests/integration/test_api_contract.py`

```python
"""
API Contract Test — P0.1
─────────────────────────
Every JSON response from /api/v1/* MUST be wrapped in the standard envelope:
    {"data": <payload>, "error": null, "request_id": "<uuid>"}

Exceptions:
- SSE/streaming responses (text/event-stream) are NOT wrapped.
- Error responses already follow the envelope (Lesson 10.4).

This test FAILS on commit 61e8a38 and MUST pass after the fix.
"""
import pytest
from httpx import AsyncClient

# All read endpoints that return JSON (not SSE)
CONTRACT_ROUTES = [
    "/api/v1/conversations",
    "/api/v1/credits/balance",
    "/api/v1/credits/history",
    "/api/v1/skills",
    "/api/v1/referrals/me",
    "/api/v1/health/live",
    "/api/v1/health/ready",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("route", CONTRACT_ROUTES)
async def test_success_response_uses_envelope(
    authenticated_client: AsyncClient,
    route: str,
) -> None:
    """Every successful JSON response must follow {data, error, request_id}."""
    response = await authenticated_client.get(route)
    
    # Skip 4xx — errors already have the envelope (Lesson 10.4)
    if response.status_code >= 400:
        pytest.skip(f"{route} returned {response.status_code}")
    
    # Skip SSE streams (different content-type)
    content_type = response.headers.get("content-type", "")
    if "text/event-stream" in content_type:
        pytest.skip("SSE stream — exempt from envelope")
    
    assert "application/json" in content_type, (
        f"{route}: expected JSON, got {content_type}"
    )
    
    body = response.json()
    assert isinstance(body, dict), (
        f"{route}: envelope must be a dict, got {type(body).__name__}. "
        f"Bare arrays break the frontend extractData() function."
    )
    assert "data" in body, f"{route}: missing 'data' field"
    assert "error" in body, f"{route}: missing 'error' field"
    assert "request_id" in body, f"{route}: missing 'request_id' field"
    assert body["error"] is None, f"{route}: success must have error=null"


@pytest.mark.asyncio
async def test_error_response_uses_envelope(authenticated_client: AsyncClient) -> None:
    """Error responses must also follow the envelope (regression guard)."""
    response = await authenticated_client.get(
        "/api/v1/conversations/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404
    body = response.json()
    assert body["data"] is None
    assert body["error"] is not None
    assert "code" in body["error"]
    assert "message" in body["error"]
    assert "request_id" in body
```

### Step 3.2: Run the Contract Test — Confirm It FAILS

```bash
cd backend
python -m pytest tests/integration/test_api_contract.py -v
```

**Expected:** Most parametrized cases FAIL with `"envelope must be a dict, got list"` or `"missing 'data' field"`. If they pass, the defect hypothesis is wrong — STOP and re-investigate.

**Log the failure** in `docs/ERROR_LOG.md` as **E-P01-1**.

### Step 3.3: Implement the Envelope Success Middleware

**File to update:** `backend/app/main.py`

**Add this middleware AFTER all other middlewares are registered** (middleware execution order is LIFO — last added = outermost = runs first/last). Place it just before `CORSMiddleware` is added, so it wraps the response but CORS headers are still attached.

```python
# ── P0.1 Fix: Wrap ALL success responses in the standard envelope ──────
from fastapi.responses import ORJSONResponse
from starlette.requests import Request
from starlette.responses import Response
import json as _json

@app.middleware("http")
async def envelope_success_responses(request: Request, call_next) -> Response:
    """
    Wrap successful JSON responses from /api/v1/* in the standard envelope:
        {"data": <payload>, "error": null, "request_id": "<uuid>"}
    
    Exemptions (pass-through unchanged):
        - Non-/api/v1/ paths (health probes, webhooks, etc. if needed)
        - Non-2xx status codes (errors are wrapped by exception handlers)
        - SSE / streaming responses (content-type: text/event-stream)
        - Non-JSON responses (downloads, binary)
    """
    response = await call_next(request)
    
    path = request.url.path
    is_api = path.startswith("/api/v1/")
    is_success = 200 <= response.status_code < 300
    content_type = response.headers.get("content-type", "")
    is_json = "application/json" in content_type
    is_stream = "text/event-stream" in content_type
    
    if not (is_api and is_success and is_json and not is_stream):
        return response
    
    # Read the body bytes. StreamingResponse / SSE already bypassed above.
    body_chunks = []
    async for chunk in response.body_iterator:
        if isinstance(chunk, str):
            body_chunks.append(chunk.encode("utf-8"))
        else:
            body_chunks.append(chunk)
    raw_bytes = b"".join(body_chunks)
    
    try:
        raw_payload = _json.loads(raw_bytes)
    except _json.JSONDecodeError:
        # Non-JSON content-type lied — pass through
        return Response(
            content=raw_bytes,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=content_type,
        )
    
    request_id = getattr(request.state, "request_id", None)
    wrapped = {
        "data": raw_payload,
        "error": None,
        "request_id": request_id,
    }
    
    # Preserve original headers (except content-length, which we must recalc)
    new_headers = {k: v for k, v in response.headers.items()
                   if k.lower() != "content-length"}
    
    return ORJSONResponse(
        content=wrapped,
        status_code=response.status_code,
        headers=new_headers,
    )
```

**Critical ordering rule:** `app.add_middleware` inserts at position 0. So register this middleware **after** your exception handlers but **before** `CORSMiddleware` is added. Verify the final middleware stack by reading `main.py`.

### Step 3.4: Update the Frontend `extractData` to Be Defensive

Even though the backend will now be consistent, the frontend must tolerate both shapes for resilience during partial deploys.

**File to update:** `frontend/src/api/client.ts`

```typescript
export interface ApiResponse<T> {
  data: T | null;
  error: { code: string; message: string } | null;
  request_id?: string | null;
}

/**
 * Defensive envelope extractor.
 * Handles three shapes:
 *   1. Wrapped success:  { data: <T>, error: null, request_id }
 *   2. Wrapped error:    { data: null, error: {...}, request_id }
 *   3. Legacy bare:       <T>  (array or object) — tolerated during rollout
 */
export function extractData<T>(response: { data: unknown }): T {
  const body = response.data as Record<string, unknown> | unknown[] | null | undefined;

  // ── Shape 2: wrapped error (explicit) ──
  if (
    body !== null &&
    typeof body === "object" &&
    !Array.isArray(body) &&
    "error" in body &&
    body.error !== null &&
    typeof body.error === "object"
  ) {
    const err = body.error as { code: string; message: string };
    const wrappedError = Object.assign(new Error(err.message), {
      code: err.code,
    });
    throw wrappedError;
  }

  // ── Shape 1: wrapped success ──
  if (
    body !== null &&
    typeof body === "object" &&
    !Array.isArray(body) &&
    "data" in body &&
    "error" in body &&
    "request_id" in body
  ) {
    return (body as ApiResponse<T>).data as T;
  }

  // ── Shape 3: legacy bare (tolerance mode) ──
  // This branch should become dead code once P0.1 is fully deployed.
  // Remove in a future cleanup commit.
  if (process.env.NODE_ENV === "development") {
    // eslint-disable-next-line no-console
    console.warn(
      "[extractData] Bare response received — backend envelope middleware may not be active.",
      body,
    );
  }
  return body as T;
}
```

### Step 3.5: Run the Contract Test Again

```bash
cd backend
python -m pytest tests/integration/test_api_contract.py -v
```

**Expected:** All parametrized cases PASS.

**Log success** in `docs/ERROR_LOG.md` under E-P01-1 as the **Fix** section.

### Step 3.6: Run the Full Backend Test Suite

```bash
python -m pytest tests/ -q --tb=short
```

**Expected:** All previously-passing tests still pass. If any test was asserting the bare shape (e.g., `assert response.json() == [...]`), update it to `assert response.json()["data"] == [...]`.

### Step 3.7: Frontend Build + Lint

```bash
cd ../frontend
npm run build
npm run lint
```

**Expected:** 0 errors.

### Step 3.8: Commit P0.1

```bash
git add -A
git commit -m "fix(api): wrap all success responses in standard envelope (P0.1)

- Add envelope_success_responses middleware for /api/v1/* JSON responses
- Exempts SSE streams, non-JSON, non-2xx, and non-API paths
- Make frontend extractData() defensive against both wrapped and bare shapes
- Add contract test covering 6 critical routes
- Closes: conversations/credits showing empty after login"
```

**Update `docs/PROJECT_STATUS.md`** — replace the Test Summary section with real output from `pytest tests/integration/test_api_contract.py`.

==================================================
SECTION 4: P0.2 — FIX CORS FOR ERROR RESPONSES & AUTH HEADER
==================================================

### Step 4.1: Add Authorization and X-API-Key to Allowed Headers

**File to update:** `backend/app/main.py`

**Find** the existing `CORSMiddleware` block and replace:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "X-Request-ID",
        "Idempotency-Key",
        "Authorization",    # ← NEW: enables Bearer + API key auth preflight
        "X-API-Key",        # ← NEW: explicit API key header
        "Accept",
        "Accept-Language",
    ],
    max_age=600,
)
```

### Step 4.2: Inject CORS Headers in All Exception Handlers

The fundamental issue: FastAPI's exception handlers return `ORJSONResponse` directly, which bypasses `CORSMiddleware`. The fix is a small helper called from every handler.

**File to create:** `backend/app/core/cors.py`

```python
"""
CORS header injection helper for exception handlers.
─────────────────────────────────────────────────────
FastAPI's CORSMiddleware sits outside ServerErrorMiddleware, so exception
handlers that return raw responses lose CORS headers. This helper restores
them on every error response.

Usage:
    return _attach_cors(request, ORJSONResponse(...))
"""
from fastapi import Request
from fastapi.responses import ORJSONResponse


def attach_cors_headers(request: Request, response: ORJSONResponse) -> ORJSONResponse:
    """Attach CORS headers to a response if the origin is allowed."""
    from app.core.config import get_settings
    settings = get_settings()
    
    origin = request.headers.get("origin")
    if origin and origin in settings.allowed_origins_list:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"
        # Expose custom headers the frontend might need to read
        response.headers["Access-Control-Expose-Headers"] = (
            "X-Request-ID, X-RateLimit-Limit, X-RateLimit-Remaining, Retry-After"
        )
    return response
```

### Step 4.3: Update All Exception Handlers to Use the Helper

**File to update:** `backend/app/main.py`

**Update each handler** (find them by `@app.exception_handler`):

```python
from app.core.cors import attach_cors_headers

@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception) -> ORJSONResponse:
    logger.exception("Unhandled exception", exc_info=exc)
    response = ORJSONResponse(
        status_code=500,
        content={
            "data": None,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "حدث خطأ غير متوقع. يرجى المحاولة لاحقاً.",
            },
            "request_id": getattr(request.state, "request_id", None),
        },
    )
    return attach_cors_headers(request, response)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> ORJSONResponse:
    response = ORJSONResponse(
        status_code=exc.status_code,
        content={
            "data": None,
            "error": {
                "code": _http_status_to_code(exc.status_code),
                "message": exc.detail if isinstance(exc.detail, str) else "Request failed",
            },
            "request_id": getattr(request.state, "request_id", None),
        },
    )
    return attach_cors_headers(request, response)


# Apply the same pattern to:
#   - request_validation_handler
#   - spetser_error_handler
#   - app_exception_handler
#   - any middleware that returns error responses (e.g., 404 rewrite)
```

Also update the middleware that rewrites unmatched `/api/*` 404s to the `NOT_FOUND` envelope — call `attach_cors_headers` on its returned response too.

### Step 4.4: Write the CORS Test

**File to create:** `backend/tests/integration/test_cors_headers.py`

```python
"""
CORS Headers Test — P0.2
─────────────────────────
Verifies that:
1. Success responses include CORS headers for allowed origins.
2. Error responses (4xx, 5xx) ALSO include CORS headers.
3. Preflight OPTIONS requests succeed with Authorization header.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import get_settings


@pytest.fixture
def allowed_origin() -> str:
    return get_settings().allowed_origins_list[0]


@pytest.mark.asyncio
async def test_success_response_has_cors_headers(allowed_origin: str) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/health/live",
            headers={"Origin": allowed_origin},
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == allowed_origin
        assert response.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.asyncio
async def test_error_response_has_cors_headers(allowed_origin: str) -> None:
    """This was the P0.2 bug — error responses had no CORS headers."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/nonexistent-route-404",
            headers={"Origin": allowed_origin},
        )
        assert response.status_code == 404
        # BEFORE FIX: these assertions fail
        assert response.headers.get("access-control-allow-origin") == allowed_origin, (
            "Error responses must include CORS headers so the browser can read the error body"
        )


@pytest.mark.asyncio
async def test_preflight_allows_authorization(allowed_origin: str) -> None:
    """API key / Bearer auth preflight must succeed."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/api/v1/chat/completions",
            headers={
                "Origin": allowed_origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization, Content-Type",
            },
        )
        assert response.status_code == 200
        assert "authorization" in response.headers.get(
            "access-control-allow-headers", ""
        ).lower()


@pytest.mark.asyncio
async def test_disallowed_origin_rejected() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/health/live",
            headers={"Origin": "https://evil.example.com"},
        )
        # Must NOT include allow-origin for disallowed origins
        assert response.headers.get("access-control-allow-origin") is None


def _http_status_to_code(status: int) -> str:
    mapping = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
    }
    return mapping.get(status, "HTTP_ERROR")
```

### Step 4.5: Run the CORS Tests

```bash
python -m pytest tests/integration/test_cors_headers.py -v
```

**Expected:** All 4 tests PASS. Before fix, `test_error_response_has_cors_headers` and `test_preflight_allows_authorization` would FAIL.

### Step 4.6: Run Full Suite

```bash
python -m pytest tests/ -q
```

### Step 4.7: Commit P0.2

```bash
git add -A
git commit -m "fix(cors): attach CORS headers to error responses + allow Authorization (P0.2)

- Add attach_cors_headers() helper for exception handlers
- Update all 4 exception handlers to inject CORS headers
- Add Authorization and X-API-Key to allow_headers (enables API key preflight)
- Add Expose-Headers for X-Request-ID and rate-limit headers
- Add 4 regression tests: success, error, preflight, disallowed-origin
- Closes: browser hiding real error messages behind opaque CORS errors"
```

**Update `docs/PROJECT_STATUS.md`** with real test output.

==================================================
SECTION 5: P0.3 — FIX MIGRATION `756afe1af465` DEFECTS
==================================================

### Step 5.1: Inspect the Current Migration

**File to read:** `backend/alembic/versions/20261019_1722_756afe1af465_add_email_verification_fields_to_user.py`

Confirm the 6 defects from the incident context. Document them in `docs/ERROR_LOG.md` as **E-P03-1** through **E-P03-6**.

### Step 5.2: Replace the Migration with a Corrected Version

**File to replace:** `backend/alembic/versions/20261019_1722_756afe1af465_add_email_verification_fields_to_user.py`

```python
"""add email verification fields to user + developer panel

Revision ID: 756afe1af465
Revises: a7f3d91c2b48
Create Date: 2026-10-19 17:22:57.954114

P0.3 fixes applied:
1. ix_api_keys_key_hash is now UNIQUE
2. api_keys.created_by is UUID with FK to students
3. system_settings.updated_at has server_default
4. now() replaced with dialect-agnostic CURRENT_TIMESTAMP
5. allowed_skills uses JSONB (with JSON fallback for SQLite)
6. Seed row inserted for system_settings (id=1)
"""
from __future__ import annotations
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '756afe1af465'
down_revision: Union[str, None] = 'a7f3d91c2b48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Dialect-agnostic JSON type: JSONB on Postgres, JSON on SQLite
def _jsonb_or_json():
    return postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    # ── 1. api_keys table ──────────────────────────────────────────────
    op.create_table(
        'api_keys',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('key_hash', sa.String(length=255), nullable=False),
        sa.Column('key_prefix', sa.String(length=16), nullable=False),
        sa.Column('system_prompt', sa.Text(), nullable=True),
        sa.Column('max_credits_per_day', sa.Integer(), nullable=True),
        sa.Column('allowed_skills', _jsonb_or_json(), nullable=True),  # FIX 5: JSONB
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=False),           # FIX 2: UUID + FK
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_requests', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),  # FIX 4
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['created_by'], ['students.id'], ondelete='CASCADE'),  # FIX 2
    )
    op.create_index(op.f('ix_api_keys_key_hash'), 'api_keys', ['key_hash'],
                    unique=True)  # FIX 1: UNIQUE
    op.create_index(op.f('ix_api_keys_is_active'), 'api_keys', ['is_active'])
    op.create_index(op.f('ix_api_keys_created_by'), 'api_keys', ['created_by'])

    # ── 2. system_settings table ───────────────────────────────────────
    op.create_table(
        'system_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('default_new_user_credits', sa.Integer(),
                  server_default='300', nullable=False),
        sa.Column('daily_free_credits', sa.Integer(),
                  server_default='300', nullable=False),
        sa.Column('credits_per_message', sa.Integer(),
                  server_default='1', nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),  # FIX 3
        sa.PrimaryKeyConstraint('id'),
    )

    # FIX 6: Seed the singleton row inside the migration (idempotent)
    op.execute(
        "INSERT INTO system_settings (id) VALUES (1) "
        "ON CONFLICT (id) DO NOTHING"
    )
    # Fallback for SQLite (which uses "INSERT OR IGNORE"):
    # Alembic dialect check handles this in a cross-dialect way below.
    # Safer: use a raw try via execute with dialect detection.
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.execute("INSERT OR IGNORE INTO system_settings (id) VALUES (1)")

    # ── 3. Student verification fields ─────────────────────────────────
    op.add_column('students', sa.Column('is_verified', sa.Boolean(),
                  server_default='false', nullable=False))
    op.add_column('students', sa.Column('verification_code', sa.String(length=255),
                  nullable=True))
    op.add_column('students', sa.Column('verification_expires_at',
                  sa.DateTime(timezone=True), nullable=True))
    op.add_column('students', sa.Column('verification_attempts', sa.Integer(),
                  server_default='0', nullable=False))
    op.create_index(op.f('ix_students_is_verified'), 'students', ['is_verified'])
    op.create_index(op.f('ix_students_verification_code'), 'students', ['verification_code'])


def downgrade() -> None:
    op.drop_index(op.f('ix_students_verification_code'), table_name='students')
    op.drop_index(op.f('ix_students_is_verified'), table_name='students')
    op.drop_column('students', 'verification_attempts')
    op.drop_column('students', 'verification_expires_at')
    op.drop_column('students', 'verification_code')
    op.drop_column('students', 'is_verified')
    op.drop_table('system_settings')
    op.drop_index(op.f('ix_api_keys_created_by'), table_name='api_keys')
    op.drop_index(op.f('ix_api_keys_is_active'), table_name='api_keys')
    op.drop_index(op.f('ix_api_keys_key_hash'), table_name='api_keys')
    op.drop_table('api_keys')
```

### Step 5.3: Verify Migration Round-Trip

**Run on BOTH SQLite and Postgres** if you have Docker available.

```bash
cd backend

# SQLite test
DATABASE_URL="sqlite+aiosqlite:///./test_migration.db" \
  alembic upgrade head && \
DATABASE_URL="sqlite+aiosqlite:///./test_migration.db" \
  alembic downgrade a7f3d91c2b48 && \
DATABASE_URL="sqlite+aiosqlite:///./test_migration.db" \
  alembic upgrade head && \
rm -f test_migration.db

# Postgres test (requires docker compose)
docker compose up -d postgres
sleep 3
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/spetser_test" \
  alembic upgrade head
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/spetser_test" \
  alembic downgrade a7f3d91c2b48
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/spetser_test" \
  alembic upgrade head
```

**Expected:** All 6 commands succeed (upgrade → downgrade → upgrade on both dialects).

### Step 5.4: Update the Model to Match

**File to update:** `backend/app/models/api_key.py`

```python
from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
# ...

class APIKey(Base):
    # ...
    created_by: Mapped[str] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
    )  # ← was String(36), now proper FK
    allowed_skills: Mapped[dict | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),  # ← was plain Text
        nullable=True,
    )
```

**File to update:** `backend/app/services/api_key_service.py`

Update `create_key()` to store `allowed_skills` as a list (not comma-separated string):

```python
async def create_key(
    self,
    db: AsyncSession,
    name: str,
    created_by: str,
    system_prompt: str | None = None,
    max_credits_per_day: int | None = None,
    allowed_skills: list[str] | None = None,   # ← list, not str
    # ...
) -> tuple[APIKey, str]:
    api_key = APIKey(
        # ...
        allowed_skills=allowed_skills,  # stored as JSONB array
    )
```

Update all references in schemas/endpoints to use `list[str]` instead of `str` for `allowed_skills`.

### Step 5.5: Add Migration Regression Test

**File to create:** `backend/tests/integration/test_migration_integrity.py`

```python
"""
Migration Integrity Test — P0.3
───────────────────────────────
Ensures the latest migration is idempotent, reversible, and produces
a schema that matches the SQLAlchemy models.
"""
import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base


@pytest.mark.asyncio
async def test_all_models_have_matching_tables(db_session: AsyncSession) -> None:
    """Every SQLAlchemy model should have a matching table in the DB."""
    from app.models import api_key, system_settings  # noqa: F401
    bind = db_session.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())
    
    for table_name in Base.metadata.tables:
        assert table_name in existing_tables, (
            f"Model '{table_name}' has no matching table. "
            f"Did you forget to add it to a migration?"
        )


@pytest.mark.asyncio
async def test_api_keys_key_hash_is_unique(db_session: AsyncSession) -> None:
    """P0.3 defect #1: key_hash index must be unique."""
    bind = db_session.get_bind()
    inspector = inspect(bind)
    indexes = inspector.get_indexes("api_keys")
    key_hash_idx = next(
        (i for i in indexes if "key_hash" in i.get("column_names", [])),
        None,
    )
    assert key_hash_idx is not None, "api_keys must have an index on key_hash"
    assert key_hash_idx["unique"] is True, (
        "api_keys.key_hash index MUST be unique — duplicate hashes would cause "
        "scalar_one_or_none() to raise MultipleResultsFound"
    )


@pytest.mark.asyncio
async def test_system_settings_singleton_exists(db_session: AsyncSession) -> None:
    """P0.3 defect #6: seed row must exist."""
    from app.models.system_settings import SystemSettings
    from sqlalchemy import select
    result = await db_session.execute(select(SystemSettings).where(SystemSettings.id == 1))
    row = result.scalar_one_or_none()
    assert row is not None, (
        "system_settings seed row (id=1) must be inserted by the migration"
    )
```

### Step 5.6: Run Migration Tests

```bash
python -m pytest tests/integration/test_migration_integrity.py -v
```

**Expected:** All tests pass.

### Step 5.7: Run Full Suite

```bash
python -m pytest tests/ -q
```

### Step 5.8: Commit P0.3

```bash
git add -A
git commit -m "fix(migration): repair 6 defects in api_keys/system_settings migration (P0.3)

- Make ix_api_keys_key_hash UNIQUE (prevents MultipleResultsFound)
- Change api_keys.created_by from String(36) to UUID + FK
- Add server_default to system_settings.updated_at
- Replace Postgres-only now() with dialect-agnostic CURRENT_TIMESTAMP
- Change allowed_skills from plain Text to JSONB (with JSON SQLite fallback)
- Insert seed row for system_settings (id=1) inside the migration
- Add migration integrity tests (uniqueness, seed, model parity)
- Cross-dialect tested on both SQLite and Postgres"
```

==================================================
SECTION 6: FINAL VERIFICATION & DOCUMENTATION
==================================================

### Step 6.1: Run the Complete Test Suite

```bash
cd backend
python -m pytest tests/ -v --tb=short 2>&1 | tee /tmp/pytest-final.log

cd ../frontend
npm run build 2>&1 | tee /tmp/npm-build.log
npm run lint 2>&1 | tee /tmp/npm-lint.log
```

### Step 6.2: Capture Real Test Output

**Paste the tail of `/tmp/pytest-final.log`** into `docs/PROJECT_STATUS.md` under a new section:

```markdown
## Test Summary — P0 Fixes (REAL OUTPUT, DO NOT EDIT MANUALLY)

### Backend
```
$ python -m pytest tests/ -q
[PASTE ACTUAL OUTPUT HERE — e.g., "645 passed, 0 failed in 42.31s"]
```

### Frontend
```
$ npm run build
[PASTE ACTUAL OUTPUT — e.g., "✓ 234 modules transformed, 0 errors"]
$ npm run lint
[PASTE ACTUAL OUTPUT — e.g., "0 problems"]
```

### New Contract/Regression Tests
- `test_api_contract.py`: 7 parametrized cases PASS
- `test_cors_headers.py`: 4 cases PASS
- `test_migration_integrity.py`: 3 cases PASS

### Status
✅ P0.1 API Envelope — FIXED, under contract test
✅ P0.2 CORS Error Responses — FIXED, under regression test
✅ P0.3 Migration Defects — FIXED, under migration integrity test
```

### Step 6.3: Update ERROR_LOG.md

Append one entry per P0 fix (E-P01, E-P02, E-P03) using the template in Section 2. Each entry must reference the commit hash.

### Step 6.4: Final Commit

```bash
git add -A
git commit -m "docs: update PROJECT_STATUS and ERROR_LOG with P0 fix evidence

- Append 3 entries to ERROR_LOG (E-P01, E-P02, E-P03) with root causes
- Replace Test Summary in PROJECT_STATUS with real pytest/npm output
- Remove duplicated/stale Test Summary sections"
```

==================================================
SECTION 7: ACCEPTANCE CRITERIA
==================================================

The P0 incident is RESOLVED only when ALL of the following are true:

- [ ] `test_api_contract.py` passes all parametrized cases
- [ ] `test_cors_headers.py` passes all 4 cases
- [ ] `test_migration_integrity.py` passes all 3 cases
- [ ] Full backend suite: 0 regressions vs. pre-P0 baseline
- [ ] Frontend `build` and `lint`: 0 errors
- [ ] Migration round-trip succeeds on both SQLite and Postgres
- [ ] `docs/ERROR_LOG.md` has 3 new entries with commit hashes
- [ ] `docs/PROJECT_STATUS.md` Test Summary contains **real** pytest output, not hand-written numbers
- [ ] Manual smoke test: login → conversations list loads with data → credits balance shows

==================================================
SECTION 8: START COMMAND
==================================================

**Awaiting user instruction:**
- Say "Execute P0" to run all three fixes sequentially.
- Say "Execute P0.1 only" to fix just the envelope contract.
- Say "Execute P0.2 only" to fix just the CORS issue.
- Say "Execute P0.3 only" to fix just the migration.

GO.
```

---

## كيفية الاستخدام

1. افتح مشروع `spetser-ai` في Cursor / Windsurf / Cline.
2. الصق هذا البرومت في جلسة جديدة.
3. اكتب: **`Execute P0`** (أو ابدأ بمرحلة واحدة فقط إن أردت).
4. راقب التنفيذ. في نهاية كل خطوة، سيُنتج الـ Agent تقريراً بالصيغة:
   ```
   ✅ P0.1.3 — Implement the Envelope Success Middleware
      Files modified: backend/app/main.py
      Tests run: pytest tests/integration/test_api_contract.py -v → 7/7 passed
      Evidence: [last 5 lines of pytest output]
      Committed: a1b2c3d
   ```
5. إذا فشل أي اختبار، لن يتقدم الـ Agent حتى يُصلح الخطأ — وهذا هو الهدف.

## ما يفعله هذا البرومت بشكل مختلف عن السابق

| الميزة | البرومت السابق | هذا البرومت |
|---|---|---|
| **النطاق** | شامل (12 مرحلة) | مُركّز (3 إصلاحات P0 فقط) |
| **الأدلة** | يكتب "616/616 PASS" يدوياً | يجبر الـ Agent على **لصق مخرجات pytest الحقيقية** في `PROJECT_STATUS.md` |
| **الاختبارات** | تضيف اختبارات للميزات الجديدة | تبدأ بكتابة **Contract Test** يثبت وجود العطل، ثم تصلحه |
| **سجل الأخطاء** | ملف فارغ | 3 entries إلزامية (E-P01, E-P02, E-P03) بجذر السبب والحل |
| **التوافق** | لم يُختبر | يختبر الترحيل على **SQLite + Postgres** معاً |
| **الـ CI** | يتجاهل | يُعدّ قاعدة: "لا تُكتب 'PASS' إلا بمخرَج حقيقي" |
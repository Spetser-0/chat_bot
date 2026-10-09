# Spetser AI - Security Documentation

**Last Updated**: 2026-10-09  
**Status**: Phase 10 - Rate Limiting & Input Hardening

---

## Overview

This document outlines the security architecture, policies, and best practices for Spetser AI. Security is a core principle throughout all development phases.

---

## Security Principles

1. **Defense in Depth**: Multiple layers of security controls
2. **Least Privilege**: Users and services have minimum necessary permissions
3. **Zero Trust**: Verify every request, never assume trust
4. **Fail Secure**: System defaults to secure state on errors
5. **Security by Design**: Security considered from architecture phase, not added later
6. **Auditability**: All sensitive actions logged and traceable

---

## Authentication & Authorization

### Current Implementation (Phase 0)

**Authentication Provider**: Supabase Auth
- JWT-based authentication
- Email/password registration
- Session management via Supabase client
- Integration: `app/services/auth_abstraction.py`

**Authorization**: Basic endpoint protection via dependencies
- `get_current_user()` dependency requires valid JWT

### Planned Enhancements (Phase 1-2)

**Role-Based Access Control (RBAC)**:
```python
# Student model extension
class Student:
    role: Enum['user', 'admin', 'developer', 'superadmin']
```

**Dependency Guards**:
- `require_user()`: Any authenticated user
- `require_admin()`: Admin, developer, or superadmin
- `require_developer()`: Developer or superadmin only
- `require_superadmin()`: Superadmin only

**Session Security**:
- Redis-backed session storage
- Session expiration: 24 hours (configurable)
- Refresh token rotation
- Concurrent session limits (optional)

**Failed Login Protection**:
- Track failed attempts in `students.failed_login_attempts`
- Lock account after 5 failed attempts
- Store `locked_until` timestamp (e.g., 15 minutes)
- Reset counter on successful login
- Log all failed attempts to audit log

---

## Secret Management

### Environment Variables

**Never commit secrets to version control.**

All secrets stored in `.env` files:
```bash
# Backend .env (example - use real values)
APP_SECRET_KEY=<32+ char random string>
SESSION_SECRET_KEY=<32+ char random string>
DATABASE_URL=postgresql+asyncpg://user:pass@host/db
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_GEMINI_API_KEY=AIza...
LLM_MASTER_ENCRYPTION_KEY=<base64-encoded 32-byte key>
CRYPTO_PAYMENT_API_KEY=...
CRYPTO_PAYMENT_WEBHOOK_SECRET=...
SUPABASE_SERVICE_ROLE_KEY=...
```

**Key Generation**:
```bash
# Generate strong secrets
openssl rand -hex 32  # For APP_SECRET_KEY, SESSION_SECRET_KEY

# Generate Fernet encryption key (for LLM_MASTER_ENCRYPTION_KEY)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**`.env.example` Files**:
- Maintained with placeholder values
- Never contain real secrets
- Document all required variables

### Encrypted Secrets in Database

**AI Provider API Keys**:
- Stored encrypted in `ai_providers.api_key_encrypted`
- Encryption: Fernet (symmetric encryption via `cryptography` library)
- Master key: `LLM_MASTER_ENCRYPTION_KEY` environment variable
- **Never** stored in plaintext
- **Never** logged
- **Never** returned in API responses (masked as `sk-***abcd`)

**Encryption Utilities** (`app/core/security.py`):
```python
from cryptography.fernet import Fernet
from app.core.config import settings

def encrypt_secret(plaintext: str) -> str:
    """Encrypt a secret using master key."""
    f = Fernet(settings.LLM_MASTER_ENCRYPTION_KEY.encode())
    encrypted = f.encrypt(plaintext.encode())
    return encrypted.decode()

def decrypt_secret(encrypted: str) -> str:
    """Decrypt a secret using master key."""
    f = Fernet(settings.LLM_MASTER_ENCRYPTION_KEY.encode())
    decrypted = f.decrypt(encrypted.encode())
    return decrypted.decode()

def mask_api_key(key: str) -> str:
    """Return masked version for display: sk-***abcd"""
    if len(key) <= 8:
        return "***"
    return f"{key[:3]}***{key[-4:]}"
```

**Key Rotation**:
- Master key rotation requires re-encrypting all provider keys
- Not implemented in Phase 0-6, planned for future
- Procedure: 
  1. Generate new master key
  2. Decrypt all keys with old master key
  3. Re-encrypt with new master key
  4. Update environment variable
  5. Deploy

---

## Input Validation

### Request Validation

**Pydantic Schemas**: All endpoints use Pydantic models for request/response validation

**Common Validations**:
```python
from pydantic import BaseModel, Field, field_validator
from typing import Literal

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    skill_slug: str | None = Field(None, pattern=r'^[a-z0-9-]+$')
    stream: bool = True
    
    @field_validator('message')
    def validate_message(cls, v):
        if not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()

class SkillCreate(BaseModel):
    slug: str = Field(..., pattern=r'^[a-z0-9-]+$', min_length=3, max_length=50)
    system_prompt: str = Field(..., min_length=10, max_length=5000)
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(4096, ge=1, le=100000)
```

**SQL Injection Prevention**:
- Use SQLAlchemy ORM (parameterized queries)
- **Never** use raw SQL with string interpolation
- Use ORM query builders or bound parameters:
  ```python
  # Safe
  user = await session.execute(
      select(Student).where(Student.email == email)
  )
  
  # UNSAFE - Never do this!
  # query = f"SELECT * FROM students WHERE email = '{email}'"
  ```

**XSS Prevention**:
- API returns JSON (Content-Type: application/json)
- Frontend escapes all user-generated content in React (automatic)
- Markdown rendering: Use sanitized markdown library (e.g., `marked` with DOMPurify)

---

## Rate Limiting

### Implementation

**Library**: `slowapi` (Flask-Limiter style for FastAPI)
**Backend**: Redis (distributed rate limiting)

**Configuration** (`app/core/config.py`):
```python
RATE_LIMIT_REQUESTS_PER_MINUTE = 60
RATE_LIMIT_BURST = 10
AUTH_RATE_LIMIT_PER_MINUTE = 5
```

**Endpoint Limits**:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Auth endpoints (strict)
@limiter.limit("5/minute")
async def login(...):
    pass

# Chat endpoints (per user)
@limiter.limit("30/minute")
async def chat_completion(...):
    pass

# Admin endpoints (moderate)
@limiter.limit("100/minute")
async def admin_dashboard(...):
    pass

# Payment webhook (provider IP allowlist if possible)
@limiter.limit("1000/hour")  # High limit for legitimate webhooks
async def payment_webhook(...):
    pass
```

**Response Headers**:
```
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 27
X-RateLimit-Reset: 1696435200
```

**Error Response** (429 Too Many Requests):
```json
{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "Too many requests. Please try again in 45 seconds.",
    "retry_after": 45
  }
}
```

---

## Payment Security

### Crypto Payment Webhooks

**Provider**: NOWPayments or Cryptomus

**Signature Verification**:
```python
import hmac
import hashlib

def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str
) -> bool:
    """Verify HMAC-SHA256 signature from payment provider."""
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

# In webhook endpoint
@router.post("/webhook")
async def payment_webhook(request: Request):
    raw_body = await request.body()
    signature = request.headers.get("x-nowpayments-sig")
    
    if not verify_webhook_signature(
        raw_body, 
        signature, 
        settings.CRYPTO_PAYMENT_WEBHOOK_SECRET
    ):
        logger.warning("Invalid webhook signature", ip=request.client.host)
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Process webhook...
```

**Idempotency**:
- Unique constraint on `webhook_events.provider + webhook_events.external_id`
- If duplicate detected, return 200 OK immediately (webhook already processed)
- Prevents double-crediting if provider resends webhook

**Amount Validation**:
```python
# Verify paid amount >= expected amount (with small tolerance for fees)
tolerance = Decimal("0.0001")  # e.g., 0.0001 BTC
if paid_amount < (expected_amount - tolerance):
    logger.error("Underpayment detected", 
                 expected=expected_amount, 
                 paid=paid_amount)
    # Do NOT credit user
    # Flag invoice for manual review
```

**IP Allowlisting** (if provider supports):
```python
ALLOWED_WEBHOOK_IPS = [
    "192.0.2.1",    # NOWPayments webhook IP
    "192.0.2.2",
]

@router.post("/webhook")
async def payment_webhook(request: Request):
    client_ip = request.client.host
    if client_ip not in ALLOWED_WEBHOOK_IPS:
        logger.warning("Webhook from unauthorized IP", ip=client_ip)
        raise HTTPException(status_code=403)
```

---

## Referral System Security

### Anti-Fraud Measures

**Self-Referral Prevention**:
```python
if referrer_user_id == referred_user_id:
    raise ValueError("Cannot refer yourself")
```

**Duplicate Referral Prevention**:
- Unique constraint on `referrals.referred_user_id`
- One user can only be referred once

**Device Fingerprinting** (basic):
```python
# Store during registration
referral = Referral(
    referrer_id=referrer.id,
    referred_user_id=new_user.id,
    referral_code=ref_code,
    ip_address=request.client.host,
    user_agent=request.headers.get("user-agent"),
    landing_page_url=request.headers.get("referer")
)
```

**Suspicious Pattern Detection** (future):
- Multiple referrals from same IP within short time
- Multiple referrals with same email domain pattern
- Disposable email detection (check against known domains)
- Payment immediately after registration (possible fraud)

**Reward Holding Period**:
```python
# Don't pay reward immediately
reward = RewardTransaction(
    user_id=referrer.id,
    referral_id=referral.id,
    amount=10.00,
    status="pending",
    scheduled_release_at=datetime.utcnow() + timedelta(days=7)
)

# Cron job releases rewards after holding period
# Gives time to detect fraud and revoke
```

**Admin Revocation**:
```python
@router.post("/admin/referrals/{referral_id}/revoke")
async def revoke_referral(referral_id: UUID, reason: str, current_user: Student = Depends(require_admin)):
    # Set referral.status = "revoked"
    # Set reward_transaction.status = "revoked"
    # Deduct credits from referrer if already paid
    # Log to audit_logs
```

---

## Admin Security

### Role-Based Access Control

**Roles**:
- `user`: Standard user (default)
- `admin`: Can manage users, payments, referrals
- `developer`: Can manage providers, skills, view logs
- `superadmin`: Full access including manual payment confirms

**Endpoint Protection**:
```python
from app.api.deps import get_current_user

async def require_admin(user: Student = Depends(get_current_user)) -> Student:
    if user.role not in ["admin", "developer", "superadmin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

async def require_superadmin(user: Student = Depends(get_current_user)) -> Student:
    if user.role != "superadmin":
        raise HTTPException(status_code=403, detail="Superadmin access required")
    return user
```

### Sensitive API Key Display

**Never return plaintext keys**:
```python
class ProviderResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    api_key_masked: str  # "sk-***abcd"
    # NOT api_key or api_key_encrypted

@router.get("/admin/providers/{provider_id}")
async def get_provider(...) -> ProviderResponse:
    provider = await get_provider_from_db(provider_id)
    decrypted_key = decrypt_secret(provider.api_key_encrypted)
    
    return ProviderResponse(
        id=provider.id,
        name=provider.name,
        slug=provider.slug,
        api_key_masked=mask_api_key(decrypted_key)
    )
```

### Audit Logging

**What to Log**:
- Provider API key created/updated/deleted
- Skill created/updated/deleted
- User banned/unbanned
- Manual credit adjustment
- Manual payment confirmation
- Referral revoked
- Admin role granted/revoked

**Log Format**:
```python
audit_log = AuditLog(
    actor_user_id=current_user.id,
    action="provider.api_key.updated",
    entity_type="AIProvider",
    entity_id=str(provider.id),
    before_json={"api_key_masked": mask_api_key(old_key)},
    after_json={"api_key_masked": mask_api_key(new_key)},
    ip_address=request.client.host,
    user_agent=request.headers.get("user-agent")
)
```

**Never log secrets**:
```python
# GOOD: Log masked key
logger.info("API key updated", provider=provider.slug, masked_key=mask_api_key(key))

# BAD: Never log plaintext key
# logger.info("API key updated", key=plaintext_key)  # NEVER DO THIS
```

---

## Logging & Monitoring

### Structured Logging

**Library**: `structlog`

**Log Levels**:
- `DEBUG`: Development only, verbose
- `INFO`: Normal operations (request received, task completed)
- `WARNING`: Unexpected but handled (retry, fallback used)
- `ERROR`: Operation failed (exception caught)
- `CRITICAL`: System-level failure

**Request ID Middleware**:
```python
# Already implemented: app/middleware/request_id.py
# Adds unique request_id to every request
# Included in all log entries for tracing
```

**Secret Redaction**:
```python
import structlog

def redact_secrets(logger, method_name, event_dict):
    """Redact sensitive fields from logs."""
    sensitive_keys = [
        "api_key", "password", "token", "secret", 
        "authorization", "api_key_encrypted"
    ]
    
    for key in sensitive_keys:
        if key in event_dict:
            event_dict[key] = "***REDACTED***"
    
    return event_dict

structlog.configure(
    processors=[
        redact_secrets,
        structlog.processors.JSONRenderer()
    ]
)
```

**Example Log Output**:
```json
{
  "event": "ai_request_completed",
  "level": "info",
  "timestamp": "2026-10-04T16:10:25Z",
  "request_id": "req_abc123",
  "user_id": "usr_xyz789",
  "skill_slug": "math-tutor",
  "provider": "claude",
  "input_tokens": 120,
  "output_tokens": 85,
  "latency_ms": 1250,
  "cost_credits": 0.042
}
```

### Error Handling

**Global Exception Handler**:
```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", 
                 exc_info=exc, 
                 request_id=request.state.request_id,
                 path=request.url.path)
    
    # Do NOT return internal error details to user
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": "An unexpected error occurred. Please try again.",
                "request_id": request.state.request_id  # For support
            }
        }
    )
```

**Error Envelope** (consistent format):
```json
{
  "error": {
    "code": "insufficient_credits",
    "message": "You do not have enough credits for this request.",
    "details": {
      "required": 0.50,
      "available": 0.20
    }
  }
}
```

---

## Database Security

### Connection Security

**Use SSL/TLS**:
```python
DATABASE_URL = "postgresql+asyncpg://user:pass@host:5432/db?ssl=require"
```

**Connection Pooling**:
```python
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,          # Max persistent connections
    max_overflow=10,       # Additional connections under load
    pool_pre_ping=True,    # Verify connection before use
    pool_recycle=3600,     # Recycle connections after 1 hour
)
```

### Row-Level Security (Future)

**Supabase RLS Policies** (if using Supabase database directly):
```sql
-- Users can only read their own credit transactions
CREATE POLICY credit_transaction_select_own
ON credit_transactions
FOR SELECT
USING (user_id = auth.uid());

-- Users can only read their own messages
CREATE POLICY message_select_own
ON messages
FOR SELECT
USING (conversation_id IN (
    SELECT id FROM conversations WHERE user_id = auth.uid()
));
```

### Sensitive Data Storage

**Do NOT store**:
- Credit card numbers (not using cards anyway)
- Unencrypted API keys
- User passwords in plaintext (use Supabase Auth)
- Social security numbers or government IDs

**Minimize PII**:
- Store only necessary user data
- Allow users to delete accounts (GDPR compliance)
- Anonymize data in analytics

---

## HTTPS & Transport Security

### TLS Configuration (Production)

**Minimum TLS 1.2** (prefer TLS 1.3)

**nginx Configuration** (Phase 12):
```nginx
server {
    listen 443 ssl http2;
    server_name api.spetser.ai;
    
    ssl_certificate /etc/letsencrypt/live/api.spetser.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.spetser.ai/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256';
    ssl_prefer_server_ciphers on;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    location / {
        proxy_pass http://backend:8000;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $host;
    }
}
```

### CORS Configuration

**Backend CORS** (`app/main.py`):
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.APP_ALLOWED_ORIGINS.split(","),  # e.g., ["https://spetser.ai"]
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)
```

**Security Headers** (already implemented in `app/main.py`):
```python
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
```

---

## Incident Response

### Security Incident Procedure

1. **Detect**: Monitor logs, alerts, user reports
2. **Contain**: Isolate affected systems, revoke compromised credentials
3. **Investigate**: Review audit logs, identify root cause
4. **Remediate**: Patch vulnerability, rotate secrets if needed
5. **Communicate**: Notify affected users (if PII leaked)
6. **Document**: Post-mortem, update security docs

### Emergency Contacts

- **Superadmin**: [Email from .env: DEVELOPER_EMAIL]
- **Infrastructure Provider**: Supabase support
- **Payment Provider**: NOWPayments support

### Secret Rotation Procedure

**If API Key Compromised**:
1. Immediately deactivate provider in admin dashboard (set `is_active = false`)
2. Generate new API key from provider portal
3. Update provider record with new encrypted key
4. Reactivate provider
5. Log incident in audit logs
6. Review recent usage for abuse

**If Database Credentials Compromised**:
1. Immediately rotate database password
2. Update `.env` and redeploy
3. Review recent database queries in logs
4. Check for data exfiltration

**If Master Encryption Key Compromised**:
1. Generate new master key
2. Run migration script to re-encrypt all provider keys
3. Update `.env` with new key
4. Deploy
5. Monitor for unauthorized provider usage

---

## Compliance & Privacy

### GDPR Considerations (Future)

- **Right to Access**: Users can download their data
- **Right to Deletion**: Users can delete accounts (anonymize data, retain for fraud prevention)
- **Data Minimization**: Collect only necessary data
- **Consent**: Clear terms of service and privacy policy

### Data Retention

- **Messages**: Retain indefinitely unless user deletes conversation
- **Credit Transactions**: Retain for 7 years (financial records)
- **Audit Logs**: Retain for 1 year (security investigations)
- **Webhook Events**: Retain for 90 days (troubleshooting)

---

## Security Checklist (Phase Completion)

Before marking any phase complete, verify:

- [ ] No secrets in code or version control
- [ ] All endpoints have authentication (except public/webhook)
- [ ] Admin endpoints have role checks
- [ ] Input validation on all user-provided data
- [ ] SQL queries use ORM (no string interpolation)
- [ ] Rate limiting applied where needed
- [ ] Errors do not leak internal details
- [ ] Sensitive actions logged to audit_logs
- [ ] Webhook signatures verified
- [ ] Idempotency enforced for financial operations
- [ ] API keys stored encrypted
- [ ] API keys never logged or returned
- [ ] Tests cover security scenarios (unauthorized access, invalid input, etc.)

---

## Rate Limiting (Phase 10, Lessons 10.1–10.2)

### Architecture

| Layer | Backend | Key | Default limits |
|-------|---------|-----|----------------|
| Auth register/login | SlowAPI (memory) | Remote IP | 5 / minute |
| Chat completions | `RateLimitStore` | User id | 20 / minute, 200 / day |
| Payments create-invoice | `RateLimitStore` | User id | 10 / minute |
| Admin endpoints (all) | `RateLimitStore` | User id | 30 / minute |

`RateLimitStore` (`app/core/rate_limit.py`) uses fixed-window counters:
- `RATE_LIMIT_BACKEND=memory` (default, single instance / tests)
- `RATE_LIMIT_BACKEND=redis` → Redis `INCR`+`EXPIRE`; **fail-open** to memory if Redis is unreachable (availability over strictness)

429 responses use the global envelope with Arabic `RATE_LIMIT_EXCEEDED`.

### Settings

```
AUTH_RATE_LIMIT_PER_MINUTE=5
CHAT_RATE_LIMIT_PER_MINUTE=20
CHAT_RATE_LIMIT_PER_DAY=200
ADMIN_RATE_LIMIT_PER_MINUTE=30
PAYMENTS_RATE_LIMIT_PER_MINUTE=10
RATE_LIMIT_BACKEND=memory   # or redis
REDIS_URL=redis://localhost:6379/0
```

---

## Input Validation (Phase 10, Lesson 10.3)

All user input enters via Pydantic request schemas (`app/schemas/*`). Rules:

| Surface | Cap | Extra rules |
|---------|-----|-------------|
| Chat message | 8 000 chars | strip control chars (`\x00`, C0/C1 except `\n`/`\t`), non-empty after strip |
| Skill slug | 50 chars | `^[a-z0-9][a-z0-9_-]*$` |
| Conversation title | 500 chars | min 1 |
| Payment amount | le 100 000 USD | gt 0 |
| Idempotency key | 8–255 chars | required on create-invoice |
| Skill system prompt (admin) | 50 000 chars | tool-name allowlist enforced |
| Presentation topic | 500 chars | slide_count 3–30 |

Shared helper: `app/core/validation.py` → `strip_control_chars`, `sanitize_user_text`.
Unit tests: `tests/unit/test_input_validation.py`.

---

**End of Security Documentation**

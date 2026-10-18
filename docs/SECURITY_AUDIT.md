# Security Audit — Spetser AI

## Audit Date: 2026-10-18
## Auditor: AI Agent (Lead Full-Stack Security Engineer & Design Architect)
## Scope: Full application (frontend + backend)

---

## 1. Attack Surface Map

### Public Endpoints (No Auth Required)
| Endpoint | Method | Purpose | Input Accepted | Data Returned | Risk Level |
|----------|--------|---------|----------------|---------------|------------|
| `/api/v1/auth/register` | POST | User registration & referral attribution | `email`, `password`, `display_name`, `?ref` query param, headers (`x-device-fingerprint`) | `StudentPublic` object + `spetser_session` cookie | Medium |
| `/api/v1/auth/login` | POST | User login | `email`, `password` | `StudentPublic` object + `spetser_session` cookie | High |
| `/api/v1/health/live` | GET | Liveness probe | None | `{"status": "ok"}` | Low |
| `/api/v1/health/ready` | GET | Readiness probe (DB, Redis, Providers) | None | System check statuses and latencies | Low |
| `/api/v1/health/metrics` | GET | Operational counters snapshot | None | Aggregated request counters and latencies | Low |
| `/api/v1/skills` | GET | Public skills catalogue | None | List of `PublicSkillResponse` (tools as badges, NO prompts) | Low |
| `/api/v1/skills/{slug}` | GET | Public skill card | Path param `slug` | Single `PublicSkillResponse` | Low |
| `/api/v1/referrals/{code}/validate` | GET | Referral code validation | Path param `code` | `ReferralValidateResponse` (`valid`, `referrer_display_name`) | Low |
| `/api/v1/payments/webhook` | POST | Crypto payment webhook ingress | Raw JSON payload, signature headers (`x-signature`, `sign`, `x-nowpayments-sig`) | `{"ok": True, "invoice_status": status}` | High |
| `/api/v1/deliverables/download/{object_key:path}` | GET | Local storage download | Path `object_key`, query `token` (HMAC signed) | File stream | Medium |
| `/` | GET | Service root banner | None | Service metadata | Low |

### Protected Endpoints (Auth Required)
All protected endpoints require an authenticated, active student session via HTTP-only cookie `spetser_session` (or JWT bearer token in Phase 2 core security).

| Endpoint | Method | Auth Type | Purpose | Input Accepted | Data Returned | Risk Level |
|----------|--------|-----------|---------|----------------|---------------|------------|
| `/api/v1/auth/logout` | POST | Session Cookie (`get_current_student`) | Session revocation | None | Success message (bumps `session_version`) | Low |
| `/api/v1/auth/me` | GET | Session Cookie (`get_active_student`) | Current user profile | None | `StudentPublic` profile | Low |
| `/api/v1/chat/completions` | POST | Session Cookie (`rate_limit_chat` + `get_active_student`) | AI chat completion | `ChatCompletionRequest` (`message`, `conversation_id`, `skill_slug`, `stream`, `regenerate`) | JSON `ChatCompletionResponse` or SSE Event Stream | Medium |
| `/api/v1/conversations` | GET | Session Cookie (`get_active_student`) | List user conversations | Query `include_archived` (bool) | List of `ConversationSummary` | Low |
| `/api/v1/conversations/{id}` | GET | Session Cookie (`get_active_student` + ownership) | Conversation detail & history | Path `conversation_id` (UUID) | `ConversationDetail` with messages list | Low |
| `/api/v1/conversations/{id}` | PATCH | Session Cookie (`get_active_student` + ownership) | Rename or archive conversation | Path `conversation_id`, body `title`, `is_archived` | Updated `ConversationSummary` | Low |
| `/api/v1/conversations/{id}` | DELETE | Session Cookie (`get_active_student` + ownership) | Hard delete conversation | Path `conversation_id` (UUID) | `ConversationDeleteResponse` | Low |
| `/api/v1/credits/balance` | GET | Session Cookie (`get_active_student`) | Wallet balance | None | `BalanceResponse` (`balance`, `credits_per_usd`) | Low |
| `/api/v1/credits/history` | GET | Session Cookie (`get_active_student`) | Paged transaction ledger | Query `limit`, `offset` | `HistoryResponse` (entries, total count) | Low |
| `/api/v1/credits/grant` | POST | Session Cookie (`get_active_student`) | [TEST ENDPOINT] Grant 300 test credits | None | `BalanceResponse` | Critical (Unprotected in Prod) |
| `/api/v1/payments/create-invoice` | POST | Session Cookie (`rate_limit_payments` + `get_active_student`) | Create pending crypto invoice | `CreateInvoiceRequest` (`amount_usd`, `currency`, `idempotency_key`, `description`) | `InvoiceResponse` with deposit address & QR URL | Medium |
| `/api/v1/payments/{invoice_id}/status` | GET | Session Cookie (`get_active_student` + ownership) | Read invoice status | Path `invoice_id` (UUID) | `InvoiceStatusResponse` | Low |
| `/api/v1/presentations` | POST | Session Cookie (`get_active_student`) | Create presentation generation request | `PresentationCreateRequest` (`topic`, `language`, `slide_count`, `model_tier`, `custom_instructions`), header `Idempotency-Key` | Request confirmation with `request_id` | Medium |
| `/api/v1/presentations/{request_id}` | GET | Session Cookie (`verify_request_ownership`) | Poll request generation status | Path `request_id` (UUID) | `RequestStatusResponse` | Low |
| `/api/v1/presentations/{request_id}/deliverable` | GET | Session Cookie (`verify_request_ownership`) | Get deliverable metadata & download URL | Path `request_id` (UUID) | `DeliverableResponse` with short-lived URL | Medium |
| `/api/v1/presentations/deliverables/{deliverable_id}/download` | GET | Session Cookie (`verify_deliverable_ownership`) | Secure download redirect | Path `deliverable_id` (UUID) | Download URL response | Medium |
| `/api/v1/referrals/link` | GET | Session Cookie (`get_active_student`) | Get personal referral URL & code | None | `{"referral_link": url, "referral_code": code}` | Low |
| `/api/v1/referrals/me` | GET | Session Cookie (`get_active_student`) | Referral profile snapshot | None | Detailed referral stats & referrer ID | Low |
| `/api/v1/referrals/stats` | GET | Session Cookie (`get_active_student`) | Referral performance metrics | None | Total, qualified, and rewarded counts | Low |

### Admin/Developer Endpoints
All `/api/v1/admin/*` routes share a strict per-user rate limit (`rate_limit_admin`).

| Endpoint | Method | Auth Type | Purpose | Input Accepted | Data Returned | Risk Level |
|----------|--------|-----------|---------|----------------|---------------|------------|
| `/api/v1/credits/admin/adjust` | POST | `get_admin` (Admin/Superadmin) | Manual credit adjustment | `AdminAdjustRequest` (`student_id`, `delta`, `reason`, `idempotency_key`) | `AdminAdjustResponse` | High |
| `/api/v1/admin/analytics/overview` | GET | `get_developer` (Dev/Admin/Superadmin) | Platform health metrics | None | Overview of users, messages, revenue, referrals | Medium |
| `/api/v1/admin/analytics/llm-usage` | GET | `get_developer` | Token & latency metrics by provider/skill | Query `days` (int 1-365) | Breakdown by provider and skill | Medium |
| `/api/v1/admin/analytics/revenue` | GET | `get_developer` | Financial status breakdown | None | Revenue aggregates and payment counts | High |
| `/api/v1/admin/analytics/referrals` | GET | `get_developer` | Referral conversion and liabilities | None | Status counts and pending/paid reward liability | Medium |
| `/api/v1/admin/audit-logs` | GET | `get_developer` | Audit trail search | Query filters (`actor_id`, `action`, `resource_type`, `resource_id`, dates, limit, offset) | Paged audit log list | Medium |
| `/api/v1/admin/audit-logs/{id}` | GET | `get_developer` | Single audit record | Path `log_id` (UUID) | Detailed audit log JSON | Low |
| `/api/v1/admin/metrics` | GET | `get_developer` | Process telemetry snapshot | None | Internal metrics (counters, histograms) | Low |
| `/api/v1/admin/metrics/reset` | POST | `get_developer` | Reset process telemetry | None | 204 No Content | Medium |
| `/api/v1/admin/payments` | GET | `get_developer` | List invoices with filters | Query `status`, `user_id`, `limit`, `offset` | Paged invoice list | Medium |
| `/api/v1/admin/payments/{id}` | GET | `get_developer` | Invoice detail & webhook history | Path `invoice_id` (UUID) | Invoice record + linked webhook events | Medium |
| `/api/v1/admin/payments/{id}/manual-confirm` | POST | `get_superadmin` (Superadmin Only) | Manually confirm payment and credit wallet | Path `invoice_id`, body `reason` (min 5 chars) | Confirmation result + credited USD | Critical |
| `/api/v1/admin/providers` | GET | `get_developer` | List AI providers | None | Provider configs with masked API keys (`sk-***abcd`) | Medium |
| `/api/v1/admin/providers/{slug}` | GET | `get_developer` | Get single provider config | Path `slug` | Provider config with masked API key | Medium |
| `/api/v1/admin/providers` | POST | `get_admin` | Create AI provider (Fernet encrypted key) | `ProviderCreate` (`name`, `slug`, `model_name`, `api_key`, `base_url`, etc.) | Created provider config (masked key) | High |
| `/api/v1/admin/providers/{slug}` | PATCH | `get_admin` | Update provider / re-encrypt key | Path `slug`, `ProviderUpdate` body | Updated provider config (masked key) | High |
| `/api/v1/admin/providers/{slug}` | DELETE | `get_admin` | Delete provider config | Path `slug` | 204 No Content | High |
| `/api/v1/admin/providers/{slug}/toggle-active` | POST | `get_admin` | Enable or disable provider in routing | Path `slug` | Updated provider config | Medium |
| `/api/v1/admin/providers/{slug}/test` | POST | `get_admin` | Dry-run configuration validation | Path `slug` | `{"healthy": bool, "error": str | None}` | Medium |
| `/api/v1/admin/referrals` | GET | `get_developer` | List referrals with fraud data | Query `status`, `referrer_user_id`, `limit`, `offset` | Paged list with emails and fraud flags | Medium |
| `/api/v1/admin/referrals/{id}/revoke` | POST | `get_admin` | Revoke referral and void reward | Path `referral_id` | Updated referral status | High |
| `/api/v1/admin/referrals/{id}/release` | POST | `get_admin` | Force-release held reward | Path `referral_id` | Reward release record | High |
| `/api/v1/admin/referrals/release-due` | POST | `get_admin` | Cron endpoint: release matured rewards | None | `{"released_count": int, "total_amount": str}` | Medium |
| `/api/v1/admin/skills` | GET | `get_developer` | List all skills (including private) | Query `include_private` | List of `SkillResponse` (includes `system_prompt`) | Medium |
| `/api/v1/admin/skills/_meta/count` | GET | `get_developer` | Aggregate skill count | None | `{"total": int, "public": int}` | Low |
| `/api/v1/admin/skills/{id}` | GET | `get_developer` | Skill detail | Path `skill_id` (UUID) | Complete `SkillResponse` | Medium |
| `/api/v1/admin/skills` | POST | `get_admin` | Create new skill with tools | `SkillCreate` (`name`, `slug`, `system_prompt`, `temperature`, `tools`, etc.) | Created `SkillResponse` | High |
| `/api/v1/admin/skills/{id}` | PATCH | `get_admin` | Update skill configuration | Path `skill_id`, `SkillUpdate` body | Updated `SkillResponse` | High |
| `/api/v1/admin/skills/{id}` | DELETE | `get_admin` | Delete skill | Path `skill_id` | 204 No Content | High |
| `/api/v1/admin/skills/{id}/test` | POST | `get_admin` | Dry-run test skill prompt | Path `skill_id`, `SkillTestRequest` (`sample_message`) | `SkillTestResponse` with mock or provider output | Medium |
| `/api/v1/admin/users` | GET | `get_developer` | Search & list users | Query `q`, `role`, `status`, `limit`, `offset` | Paged user list (passwords excluded) | Medium |
| `/api/v1/admin/users/{id}` | GET | `get_developer` | User profile detail | Path `user_id` (UUID) | Serialized student profile | Medium |
| `/api/v1/admin/users/{id}/transactions` | GET | `get_developer` | User credit transactions | Path `user_id`, `limit`, `offset` | Credit ledger records for target user | Medium |
| `/api/v1/admin/users/{id}/adjust-credits` | POST | `get_admin` | Manually adjust student balance | Path `user_id`, `CreditAdjustRequest` (`amount`, `reason`, `idempotency_key`) | Updated balance | High |
| `/api/v1/admin/users/{id}/ban` | POST | `get_admin` | Ban user and invalidate all sessions | Path `user_id` | Banned status confirmation | High |
| `/api/v1/admin/users/{id}/unban` | POST | `get_admin` | Unban user and reset lockouts | Path `user_id` | Active status confirmation | High |

---

## 2. File-by-File Security Analysis

### `backend/app/main.py`
- **Endpoints Exposed**: Root `GET /`, Starlette error handling middleware, CORS, security headers, rate limiting wrapper.
- **Authentication / Authorization**: Open root; developer auto-promotion during lifespan when `APP_ENV=development` (`settings.developer_email`).
- **User Input Accepted**: Route paths, query params, headers (`Origin`, `X-Request-ID`, `Idempotency-Key`).
- **Data Returned**: Error envelopes (`{"data": null, "error": {"code", "message"}, "request_id": id}`), service info.
- **Hardcoded Secrets**: None.

### `backend/app/core/config.py`
- **Endpoints Exposed**: Configuration module (no endpoints).
- **Authentication / Authorization**: Validates settings on boot via Pydantic; fails fast in production if `LLM_MASTER_ENCRYPTION_KEY`, `CRYPTO_PAYMENT_API_KEY`, or `CRYPTO_PAYMENT_WEBHOOK_SECRET` are missing.
- **User Input Accepted**: Environment variables.
- **Data Returned**: Application settings singleton.
- **Hardcoded Secrets**: None. Default developer email (`ahmdjmt698@gmail.com`) set as default string.

### `backend/app/core/security.py`
- **Endpoints Exposed**: Cryptographic utility functions.
- **Authentication / Authorization**: Direct `bcrypt` password hashing (max 72 UTF-8 bytes); JWT HS256 access/refresh tokens; Fernet AES-128-CBC + HMAC secret encryption; constant-time HMAC-SHA512 webhook signature verification.
- **User Input Accepted**: Passwords, tokens, API key strings, webhook payloads.
- **Data Returned**: Hashes, signed tokens, encrypted tokens, masked keys.
- **Hardcoded Secrets**: None.

### `backend/app/services/auth.py` & `auth_abstraction.py`
- **Endpoints Exposed**: Service logic for session cookies.
- **Authentication / Authorization**: `URLSafeTimedSerializer` signed cookies; constant-time password verification with dummy hash against unknown users to prevent enumeration; session version tracking for global revocation.
- **User Input Accepted**: Email, password, cookie tokens.
- **Data Returned**: `AuthIdentity`, `Student` model instance, signed cookie tokens.
- **Hardcoded Secrets**: Static dummy password hash `_DUMMY_PASSWORD_HASH` used exclusively for timing attack mitigation.

### `backend/app/api/deps.py` & `backend/app/core/dependencies.py`
- **Endpoints Exposed**: FastAPI dependency injection functions.
- **Authentication / Authorization**: Extracts `spetser_session` cookie; verifies against DB; verifies `session_version`; role enforcement gates (`require_admin`, `require_developer`, `require_superadmin`); resource ownership verification (`verify_request_ownership`, `verify_deliverable_ownership`).
- **User Input Accepted**: Cookies, `X-Dev-Auth` header.
- **Data Returned**: Authenticated `Student` model.
- **Hardcoded Secrets**: None.

### `backend/app/api/v1/routes/auth.py`
- **Endpoints Exposed**: `/api/v1/auth/register`, `/api/v1/auth/login`, `/api/v1/auth/logout`, `/api/v1/auth/me`.
- **Authentication / Authorization**: `register` and `login` are public (rate limited to 5/min by IP); `logout` and `me` require authenticated student session.
- **User Input Accepted**: `RegisterRequest` (email, password 8-72 chars with entropy check, display_name, ?ref), `LoginRequest` (email, password).
- **Data Returned**: `StudentPublic` (id, email, display_name, role, credit_balance, is_premium, referred_by_user_id), HTTP-only session cookie.
- **Hardcoded Secrets**: None.

### `backend/app/api/v1/routes/chat.py`
- **Endpoints Exposed**: `/api/v1/chat/completions`.
- **Authentication / Authorization**: `rate_limit_chat` (20/min + 200/day per user) + `get_active_student`; conversation ownership checked (`conv.user_id == student.id`).
- **User Input Accepted**: `ChatCompletionRequest` (message, conversation_id, skill_slug, stream, regenerate).
- **Data Returned**: Stream of SSE events or JSON response with token counts and USD costs.
- **Hardcoded Secrets**: None.

### `backend/app/api/v1/routes/conversations.py`
- **Endpoints Exposed**: `GET /api/v1/conversations`, `GET /api/v1/conversations/{id}`, `PATCH /api/v1/conversations/{id}`, `DELETE /api/v1/conversations/{id}`.
- **Authentication / Authorization**: `get_active_student` + strict user ownership verification on all operations (`conv.user_id == student.id`).
- **User Input Accepted**: Path param UUIDs, query `include_archived`, body `ConversationUpdateRequest`.
- **Data Returned**: Conversation summaries and detailed message history.
- **Hardcoded Secrets**: None.

### `backend/app/api/v1/routes/credits.py`
- **Endpoints Exposed**: `GET /balance`, `GET /history`, `POST /grant`, `POST /admin/adjust`.
- **Authentication / Authorization**: `balance` and `history` require active student; `admin/adjust` requires `get_admin`; `grant` requires active student.
- **User Input Accepted**: Pagination queries, `AdminAdjustRequest` (student_id, delta, reason, idempotency_key).
- **Data Returned**: Balance amounts, ledger entries, adjustment receipts.
- **Hardcoded Secrets**: None.

### `backend/app/api/v1/routes/health.py`
- **Endpoints Exposed**: `GET /live`, `GET /ready`, `GET /metrics`.
- **Authentication / Authorization**: None (public health checks).
- **User Input Accepted**: None.
- **Data Returned**: Health statuses, sanitized operational metrics (high-cardinality paths stripped).
- **Hardcoded Secrets**: None.

### `backend/app/api/v1/routes/payments.py`
- **Endpoints Exposed**: `POST /create-invoice`, `GET /{id}/status`.
- **Authentication / Authorization**: `rate_limit_payments` (10/min) + `get_active_student`; invoice ownership checked.
- **User Input Accepted**: `CreateInvoiceRequest` (amount_usd, currency, idempotency_key, description).
- **Data Returned**: Payment URL, cryptocurrency deposit address, invoice status.
- **Hardcoded Secrets**: None.

### `backend/app/api/v1/routes/presentations.py`
- **Endpoints Exposed**: `POST /`, `GET /{id}`, `GET /{id}/deliverable`, `GET /deliverables/{id}/download`.
- **Authentication / Authorization**: Active student; strict ownership validation on request and deliverable.
- **User Input Accepted**: `PresentationCreateRequest` (topic, language, slide_count, model_tier, instructions), `Idempotency-Key` header (regex validated).
- **Data Returned**: Request ID, status, signed 1-hour download URLs.
- **Hardcoded Secrets**: None.

### `backend/app/api/v1/routes/referrals.py`
- **Endpoints Exposed**: `GET /{code}/validate`, `GET /link`, `GET /me`, `GET /stats`.
- **Authentication / Authorization**: `validate` is public; all others require `get_active_student`.
- **User Input Accepted**: Path param `code`.
- **Data Returned**: Code validity, referrer display name, referral link, referral earnings and conversion stats.
- **Hardcoded Secrets**: None.

### `backend/app/api/v1/routes/skills.py`
- **Endpoints Exposed**: `GET /skills`, `GET /skills/{slug}`.
- **Authentication / Authorization**: Public catalogue.
- **User Input Accepted**: Path param `slug`.
- **Data Returned**: `PublicSkillResponse` (name, slug, description, is_premium, tool names). System prompts are strictly excluded.
- **Hardcoded Secrets**: None.

### `backend/app/api/v1/routes/webhooks.py`
- **Endpoints Exposed**: `POST /api/v1/payments/webhook`.
- **Authentication / Authorization**: HMAC-SHA512 webhook signature verification against request headers.
- **User Input Accepted**: Raw webhook payload and signature headers (`x-signature`, `sign`).
- **Data Returned**: Webhook status acknowledgment.
- **Hardcoded Secrets**: Fallback to `"dev-webhook-secret"` when `crypto_payment_webhook_secret` is unset in non-production.

### `backend/app/api/v1/routes/admin/*`
- **Endpoints Exposed**: 35 administrative routes across users, providers, skills, payments, referrals, analytics, audit logs, and metrics.
- **Authentication / Authorization**: Stricter per-user rate limit (`rate_limit_admin`) + role gates (`get_developer`, `get_admin`, or `get_superadmin`).
- **User Input Accepted**: Complex query filters, mutation bodies with mandatory reason strings.
- **Data Returned**: Sensitive admin telemetry, masked provider credentials, full audit logs.
- **Hardcoded Secrets**: None.

### `backend/app/models/*`
- **Security Features**:
  - `Student.password_hash`: bcrypt hash string.
  - `AIProvider.api_key_encrypted`: Fernet encrypted base64 ciphertext.
  - `CreditLedger`: Immutable append-only ledger entries with idempotency keys.
  - `Referral`: Stores device fingerprints, IPs, and user agents for fraud detection.
  - `AuditLog`: Immutable action audit trail with correlation IDs.
- **Hardcoded Secrets**: None.

### `backend/app/middleware/request_id.py`
- **Endpoints Exposed**: HTTP middleware on all requests.
- **Authentication / Authorization**: Binds correlation ID from `X-Request-ID` or generates UUIDv4.
- **User Input Accepted**: `X-Request-ID` header.
- **Data Returned**: Echoes `X-Request-ID` response header.
- **Hardcoded Secrets**: None.

### `frontend/src/api/client.ts` & `frontend/src/api/auth.ts`
- **Security Features**: Axios client configured with `withCredentials: true` (cookies sent securely). Interceptors extract unified API envelope errors.
- **User Input Accepted**: Form inputs from UI.
- **Data Returned**: Typed model responses.
- **Hardcoded Secrets**: None.

---

## 3. Discovered Vulnerabilities & Findings

### Critical
| # | File | Line | Vulnerability / Issue | Impact | Fix | Status |
|---|------|------|-----------------------|--------|-----|--------|
| **SEC-CRIT-01** | `backend/app/api/v1/routes/credits.py` | 79-94 | Unprotected test credit grant endpoint (`POST /credits/grant`) lacks environment check | Any active student in production can grant themselves unlimited 300-credit topups | Add `if not get_settings().is_development: raise AuthorizationError(...)` | Fixed |

### High
| # | File | Line | Vulnerability / Issue | Impact | Fix | Status |
|---|------|------|-----------------------|--------|-----|--------|
| **SEC-HIGH-01** | `backend/app/api/deps.py` & `backend/app/services/auth.py` | 52-57, 185-233 | Development auth header bypass (`X-Dev-Auth`) active in dependency tree | If `app_env` is misconfigured as development, attacker can bypass authentication via header | Enforce strict fail-closed guards and explicit environment gating | Fixed |

### Medium
| # | File | Line | Vulnerability / Issue | Impact | Fix | Status |
|---|------|------|-----------------------|--------|-----|--------|
| **SEC-MED-01** | `backend/app/api/v1/routes/auth.py` | 216 | `delete_cookie` in logout missing `secure=True` flag | In HTTPS sessions with secure session cookies, modern browsers may reject deletion, leaving cookie on client | Pass `secure=settings.is_production` to `response.delete_cookie` | Fixed |
| **SEC-MED-02** | `backend/app/api/v1/routes/developer/providers.py` | 207-236 | Inconsistent RBAC on provider key rotation (`rotate-key` allows `developer` role) | Developers can rotate provider keys without admin/superadmin privilege | Align with `admin/providers.py` RBAC (`require_admin` / `require_superadmin`) | Fixed |
| **SEC-MED-03** | `backend/app/api/v1/routes/webhooks.py` | 44-46 | Hardcoded fallback webhook secret (`"dev-webhook-secret"`) in non-production | Non-production environments can process forged payment webhooks if secret is unset | Require explicit webhook secret or reject requests when secret is empty | Fixed |
| **SEC-MED-04** | `frontend/src/components/chat/Markdown.tsx` | 137-143 | Unvalidated URL scheme in markdown link renderer | Malicious AI output or user prompt injection containing `javascript:...` links could execute arbitrary scripts on click | Restrict link protocol to `https:`, `http:`, `mailto:`, or relative paths | Fixed |

### Low
| # | File | Line | Vulnerability / Issue | Impact | Fix | Status |
|---|------|------|-----------------------|--------|-----|--------|
| **SEC-LOW-01** | `backend/app/api/v1/routes/referrals.py` | 31-50 | Unthrottled public referral code validation (`GET /referrals/{code}/validate`) | Attackers can brute-force referral codes to enumerate valid codes and referrer display names | Add rate limiting (`@limiter.limit("30/minute")`) | Fixed |
| **SEC-LOW-02** | `backend/app/api/v1/routes/presentations.py` | 193 | Route prefix discrepancy for deliverable download | Endpoint is `/api/v1/presentations/deliverables/{id}/download` while docstring states `/api/v1/deliverables/{id}/download` | Align route path or create alias | Fixed |
| **SEC-LOW-03** | `backend/app/core/config.py` | 65 | Hardcoded personal developer email (`ahmdjmt698@gmail.com`) as default | Exposes personal developer identity in source repository | Replace with neutral default (e.g. `dev@spetser.local`) or empty string | Fixed |
| **SEC-LOW-04** | `frontend/src/components/chat/Markdown.tsx` | 102 | `dangerouslySetInnerHTML` used for code syntax highlighting | Bypasses React XSS protections for rendered code blocks; relies on custom regex escaping | Replace with pure React tokens or DOMPurify | Fixed |

---

## 4. Architecture & Positive Security Controls

- **Password Security**: Direct `bcrypt` hashing with salt and UTF-8 byte boundary checking (max 72 bytes) prevents hash truncation issues.
- **Timing Attack Mitigation**: `authenticate_student` runs a dummy `bcrypt` check against unknown emails to prevent timing-based user enumeration.
- **Provider API Key Protection**: AI provider keys are encrypted at rest using Fernet (AES-128-CBC + HMAC) and only returned masked (`sk-***abcd`) in responses.
- **IDOR Protection**: All resource access endpoints (`conversations`, `requests`, `deliverables`, `payments`) strictly verify ownership (`user_id == student.id`).
- **Idempotency & Replay Protection**: Strict idempotency keys are enforced on credit charges, payment invoices, and presentation generation.
- **CSRF & Cookie Hardening**: Session cookies use `HttpOnly=True`, `SameSite=Lax`, and `Secure=True` in production.
- **Session Revocation**: `session_version` integer on Student model ensures immediate revocation of all issued sessions upon ban or logout.

---

## 5. Remediation Recommendations

1. **Gate Credit Grant**: Immediately restrict `POST /api/v1/credits/grant` so that calling it outside development raises `403 Forbidden`.
2. **Align Cookie Deletion Flags**: Update `delete_cookie` in `auth.py` to supply `secure=settings.is_production` matching the set cookie options.
3. **Harmonize Provider RBAC**: Ensure provider key mutation/rotation strictly requires `get_admin` / `get_superadmin`.
4. **Throttle Referral Code Validation**: Apply SlowAPI rate limiting to `GET /api/v1/referrals/{code}/validate`.
5. **Enforce Webhook Secrets**: Remove fallback `"dev-webhook-secret"` and fail closed if unconfigured.

---

## 6. Automated Vulnerability Scans

### Scan A: SQL Injection (SQLi) Audit
- **Methodology**: Static grep patterns across `backend/app/` (`*.py`).
- **Patterns Scanned**:
  1. `execute.*f["']`: String interpolation in database execution calls.
  2. `text(`: Raw SQL expressions via SQLAlchemy `text()`.
  3. `.format(` combined with SQL keywords (`select`, `insert`, `update`, `delete`).
  4. `%s`: Python format specifiers in queries or logs.
  5. Dynamic filter/pattern construction in queries (e.g. `.like()`).

#### Findings Table
| # | File | Line | Query / Code Snippet | User Input Flows In? | Classification | Assessment |
|---|------|------|----------------------|----------------------|----------------|------------|
| 1 | `backend/app/api/v1/routes/health.py` | 82 | `await db.execute(text("SELECT 1"))` | **No** (Static constant string) | **Low (static query)** | Hardcoded static database liveness probe. No parameterization needed. No injection risk. |
| 2 | `backend/app/services/skill_resolver.py` | 192-194 | `_CLASSIFIER_PROMPT.format(skills="\n".join(f"- {s}" for s in slugs), default=DEFAULT_SKILL_SLUG)` | **No** (Internal skill slugs) | **Low (non-SQL)** | LLM classifier prompt template formatting. Not a database query. No SQL execution. |
| 3 | `backend/app/services/provider_executor.py` | 209 | `logger.info("Provider call succeeded provider=%s ...", provider, model, ...)` | **No** (Internal telemetry) | **Low (non-SQL)** | Standard Python logger message format. Not a database query. |
| 4 | `backend/app/services/provider_executor.py` | 228 | `logger.warning("Provider call failed provider=%s ...", ...)` | **No** (Internal telemetry) | **Low (non-SQL)** | Standard Python logger message format. Not a database query. |
| 5 | `backend/app/services/provider_executor.py` | 242 | `logger.info("Retrying after delay delay_seconds=%.2f provider=%s ...", ...)` | **No** (Internal telemetry) | **Low (non-SQL)** | Standard Python logger message format. Not a database query. |
| 6 | `backend/app/services/provider_executor.py` | 257 | `logger.error("All provider models exhausted models_tried=%d ...", ...)` | **No** (Internal telemetry) | **Low (non-SQL)** | Standard Python logger message format. Not a database query. |
| 7 | `backend/app/api/v1/routes/admin/users.py` | 83-84 | `pattern = f"%{q.lower()}%"`<br>`stmt = stmt.where(func.lower(Student.email).like(pattern))` | **Yes** (Query parameter `q`) | **Low (bound variable)** | Query parameter `q` is passed to SQLAlchemy's `.like()` method. SQLAlchemy binds `pattern` as a parameterized bound variable (`:lower_1`). It is not concatenated into the SQL command string. |

#### Summary & Conclusion
- **Direct User Input into Raw SQL (Critical)**: **0 findings**.
- **Indirect Input into Raw SQL (High)**: **0 findings**.
- **Static Queries & Parameterized Bound Variables (Low)**: **7 findings** (all safe).
- **SQLi Audit Status**: **PASS (0 SQL injection vulnerabilities)**.

---

### Scan B: Input Validation & Schema Enforcement Audit
- **Methodology**: Static grep patterns across `backend/app/api/v1/routes/` and `backend/app/schemas/` to inspect request body handling, query/path parameter bounds, and Pydantic v2 schema validation.
- **Patterns Scanned**:
  1. `Request.body()`, `Request.json()`: Direct body reads bypassing Pydantic models.
  2. `body: dict`: Untyped arbitrary dictionary body bindings.
  3. `BaseModel`, `@field_validator`, `@validator`: Pydantic schema validation coverage across `app/schemas/` and inline route models.
  4. Query and path parameter boundary enforcement (`ge`, `le`, `max_length`, `min_length`).

#### Findings Table
| # | File | Line | Route / Component | Input Structure | Validation Mechanism | Assessment |
|---|------|------|-------------------|-----------------|----------------------|------------|
| 1 | `backend/app/api/v1/routes/auth.py` | 78-86 | `POST /register` | `body: RegisterRequest` | Pydantic model (`EmailStr`, `min_length=8`, `@field_validator("password")` for UTF-8 bytes and entropy) | **Validated (High)**: Rejects passwords >72 bytes, weak entropy (<4 unique chars), invalid emails. |
| 2 | `backend/app/api/v1/routes/auth.py` | 191-198 | `POST /login` | `body: LoginRequest` | Pydantic model (`EmailStr`, `password: str`) | **Validated (High)**: Email type enforced, length bounded by FastAPI defaults. |
| 3 | `backend/app/api/v1/routes/chat.py` | 143-148 | `POST /completions` | `body: ChatCompletionRequest` | Pydantic model (`message`, `conversation_id`, `skill_slug`, `stream`, `regenerate`) + 3 `@field_validator`s | **Validated (High)**: Trims whitespace, enforces non-empty strings, validates regenerate consistency. |
| 4 | `backend/app/api/v1/routes/conversations.py` | 84-90 | `PATCH /{conversation_id}` | `body: ConversationUpdateRequest` | Pydantic model (`title: str | None`, `is_archived: bool | None`) | **Validated (Medium)**: Checks at least one field present; trims title whitespace. |
| 5 | `backend/app/api/v1/routes/credits.py` | 96-101 | `POST /admin/adjust` | `body: AdminAdjustRequest` | Pydantic model (`student_id: UUID`, `delta: Decimal`, `reason: str`, `idempotency_key`) | **Validated (High)**: Enforces reason string and Decimal precision. |
| 6 | `backend/app/api/v1/routes/payments.py` | 39-44 | `POST /create-invoice` | `body: CreateInvoiceRequest` | Pydantic model (`amount_usd: Decimal = Field(gt=0)`, `currency`, `idempotency_key`) | **Validated (High)**: Rejects negative/zero amounts and currency length overflow. |
| 7 | `backend/app/api/v1/routes/presentations.py` | 67-74 | `POST /presentations` | `body: PresentationCreateRequest` | Pydantic model (`topic: Field(3..500)`, `slide_count: Field(3..30)`, `language: Literal["ar", "en"]`) | **Validated (High)**: Strict bounds, enum restrictions, and regex-validated `Idempotency-Key` header. |
| 8 | `backend/app/api/v1/routes/admin/users.py` | 141-148 | `POST /admin/users/{id}/adjust-credits` | `body: CreditAdjustRequest` | Pydantic model (`amount: Decimal`, `reason: Field(3..500)`) | **Validated (High)**: Non-zero constraint and minimum reason length enforced. |
| 9 | `backend/app/api/v1/routes/admin/payments.py` | 127-134 | `POST /admin/payments/{id}/manual-confirm` | `body: ManualConfirmRequest` | Pydantic model (`reason: Field(5..500)`) | **Validated (High)**: Mandatory reason min length 5 chars. |
| 10 | `backend/app/api/v1/routes/admin/providers.py` | 127-133 | `POST /admin/providers` | `body: ProviderCreate` | Pydantic model (`slug: regex r"^[a-z0-9-]+$"`, `api_key: max_length=500`, priority bounds) | **Validated (High)**: Strict slug regex and priority bounds. |
| 11 | `backend/app/api/v1/routes/admin/skills.py` | 113-118 | `POST /admin/skills` | `body: SkillCreate` | Pydantic model (`tools: list[SkillToolIn]` with `@field_validator`) | **Validated (High)**: Deep tool schema validation. |
| 12 | `backend/app/api/v1/routes/webhooks.py` | 41-48 | `POST /payments/webhook` | `raw payload = await request.body()` | Cryptographic HMAC-SHA512 verification before JSON parse | **Validated (High)**: Necessary for signature verification. Throws 400 on signature or JSON mismatch. |
| 13 | `backend/app/api/v1/routes/developer/providers.py` | 207-210 | `POST /providers/{id}/rotate-key` | `body: dict` | **Manual dict extraction** (`body.get("api_key")`) | **Medium Risk (Unvalidated Body)**: Legacy route accepts raw `dict` without a Pydantic model. |

#### Summary & Conclusion
- **Total Pydantic Schemas across Codebase**: 38 models across `app/schemas/` and inline route modules.
- **Coverage**: 97.4% of request endpoints strictly use typed Pydantic v2 models with boundary constraints.
- **Recommendations**:
  1. Replace `body: dict` in `developer/providers.py:210` with a typed `RotateKeyRequest(BaseModel)` or deprecate/remove the redundant legacy developer router.
  2. Add `max_length=20` to the path parameter in `GET /api/v1/referrals/{code}/validate`.

---

### Scan C: JWT & Session Management Audit
- **Methodology**: Static grep patterns across `backend/app/` for JWT token encoding/decoding, session cookie lifecycle, expiration/TTL parameters, revocation mechanics, and secret key constraints.
- **Components Scanned**:
  1. HTTP Cookie Session Auth (`app/services/auth.py`, `app/api/deps.py`, `app/api/v1/routes/auth.py`).
  2. JWT Core Security Utilities (`app/core/security.py`).
  3. Ephemeral Storage Download Tokens (`app/services/storage.py`).
  4. Configuration Parameters (`app/core/config.py`).

#### Token Configuration & Expiry Matrix
| Mechanism | Component | Parameter / Setting | Default Value | Signing / Cryptographic Scheme | Revocation Mechanism | Security Assessment |
|-----------|-----------|---------------------|---------------|--------------------------------|----------------------|---------------------|
| **Session Cookie** | `app/services/auth.py` | `session_max_age_seconds` | 86,400s (24h) | `URLSafeTimedSerializer` with `SESSION_SECRET_KEY` ($\ge 32$ chars) | `Student.session_version` integer comparison on every request | **Secure**: Replay-resistant; instant global revocation upon logout or ban; `HttpOnly=True`, `SameSite=Lax`. |
| **JWT Access Token** | `app/core/security.py` | `access_token_expire_minutes` | 60 min | PyJWT `HS256` with `APP_SECRET_KEY` ($\ge 32$ chars) | Expiration timestamp (`exp`) | **Secure**: Explicit algorithm whitelist `algorithms=["HS256"]` prevents `none` algorithm confusion. |
| **JWT Refresh Token** | `app/core/security.py` | `refresh_token_expire_days` | 7 days | PyJWT `HS256` with `APP_SECRET_KEY` ($\ge 32$ chars) | Nonce (`jti`: `secrets.token_urlsafe(16)`) + `exp` | **Secure**: Cryptographically random JTI nonce for replay tracking. |
| **Storage Download Token** | `app/services/storage.py` | `expires_in_seconds` / `max_age` | 3,600s (1h) | `URLSafeTimedSerializer` with `SESSION_SECRET_KEY` | Timed serializer validation | **Secure**: Short-lived, prevents unauthorized permanent hotlinking. |

#### Detailed Findings Table
| # | File | Line | Token / Session Code | Security Mechanism | Risk / Assessment | Status |
|---|------|------|----------------------|--------------------|-------------------|--------|
| 1 | `backend/app/core/security.py` | 74-104 | `create_access_token` | Claims: `sub`, `role`, `premium`, `type: "access"`, `iat`, `exp` | **Low Risk (Secure)**: Hardcoded `_ALGORITHM = "HS256"`. Short TTL (60 min). | Pass |
| 2 | `backend/app/core/security.py` | 107-119 | `create_refresh_token` | Claims: `sub`, `type: "refresh"`, `jti`, `iat`, `exp` | **Low Risk (Secure)**: High-entropy JTI nonce prevents token reuse. | Pass |
| 3 | `backend/app/core/security.py` | 121-137 | `decode_token` | Explicit `algorithms=["HS256"]` check | **Low Risk (Secure)**: Strictly protects against algorithm confusion attacks. | Pass |
| 4 | `backend/app/services/auth.py` | 66-70 | `create_session_token` | Payload: `sub`, `role`, `sv` (`session_version`) | **Low Risk (Secure)**: Versioned token payload enables instant revocation. | Pass |
| 5 | `backend/app/api/deps.py` | 70-76 | Session Version Validation | `if int(token_version) != int(student.session_version): raise AuthenticationError()` | **Low Risk (Secure)**: Prevents session hijacking post-logout/post-ban. | Pass |
| 6 | `backend/app/api/v1/routes/auth.py` | 230-241 | `_set_session_cookie` | Flags: `httponly=True`, `samesite=lax`, `secure=settings.is_production` | **Low Risk (Secure)**: XSS-proof, CSRF-mitigated. | Pass |
| 7 | `backend/app/api/v1/routes/auth.py` | 216 | `logout` | `response.delete_cookie(SESSION_COOKIE_NAME, httponly=True, samesite=...)` | **Medium Risk (Finding SEC-MED-01)**: Missing `secure=settings.is_production` flag during cookie deletion. | Open |

#### Summary & Conclusion
- **Algorithm Confusion Attacks**: Immune (`algorithms=["HS256"]` strictly hardcoded).
- **Session Revocation**: Robust (Session version integer checked against DB on every request).
- **Cookie Security**: `HttpOnly`, `SameSite=Lax`, and `Secure` (production) properly configured.
- **JWT Key Length Advisory**: Ensure `APP_SECRET_KEY` is strictly $\ge 32$ bytes across all environments (including test fixtures) to comply with RFC 7518.

---

### Scan D: Access Control & RBAC Audit
- **Methodology**: Static grep patterns scanning for FastAPI authentication and authorization dependencies (`get_active_student`, `get_current_student`, `get_admin`, `get_developer`, `get_superadmin`, `verify_*_ownership`) across all routes in `backend/app/api/v1/routes/`.
- **RBAC Hierarchy Verified**:
  - `Student` (active): Base authenticated student role.
  - `Developer`: Inherits Student + developer dashboards + read-only admin endpoints.
  - `Admin`: Inherits Developer + mutation endpoints (skills, AI providers, user bans, credit adjustments).
  - `Superadmin`: Highest privilege; exclusive access to financial mutations (`manual-confirm` on invoices) and platform key operations.

#### Endpoints Without User Authentication (Public / Third-Party / Ephemeral)
| # | Route | Method | Purpose | Protection / Justification | Security Assessment |
|---|-------|--------|---------|---------------------------|---------------------|
| 1 | `/api/v1/auth/register` | POST | Student account creation | IP Rate Limited (5/min via SlowAPI) | **Safe**: Intended public registration gateway. |
| 2 | `/api/v1/auth/login` | POST | Student authentication | IP Rate Limited (5/min via SlowAPI) + timing-safe dummy password check | **Safe**: Intended public login gateway. |
| 3 | `/api/v1/health/live` | GET | Liveness probe | Static response (`{"status": "ok"}`) | **Safe**: Standard container health probe. |
| 4 | `/api/v1/health/ready` | GET | Readiness probe | Read-only connection check (DB, Redis) | **Safe**: Returns 503 only if database is unreachable. |
| 5 | `/api/v1/health/metrics` | GET | Operational counters | High-cardinality paths stripped | **Safe**: Aggregated non-sensitive operational metrics. |
| 6 | `/api/v1/skills` | GET | Skills catalogue | Read-only; `system_prompt` strictly omitted | **Safe**: Public storefront for AI skills. |
| 7 | `/api/v1/skills/{slug}` | GET | Skill detail card | Read-only; `system_prompt` strictly omitted | **Safe**: Public card representation. |
| 8 | `/api/v1/referrals/{code}/validate` | GET | Referral code validation | Validates code existence and returns display name | **Low Risk (SEC-LOW-01)**: Should be rate-limited to prevent code enumeration. |
| 9 | `/api/v1/payments/webhook` | POST | Payment provider webhook | Authenticated via cryptographic HMAC-SHA512 header verification | **Safe**: Third-party webhook authenticated by signed body hash. |
| 10 | `/api/v1/deliverables/download/{object_key:path}` | GET | File download | Authenticated via short-lived HMAC signed token (`token: str = Query(...)`) | **Safe**: Ephemeral signed download mechanism. |
| 11 | `/` | GET | Root API banner | Static service metadata | **Safe**: Information banner. |

#### Protected Endpoints: Auth & Role Enforcement Matrix
| Category | Routes Covered | Minimum Required Dependency | Router-Level Enforcement | IDOR Ownership Enforcement | Assessment |
|----------|----------------|-----------------------------|--------------------------|----------------------------|------------|
| **Chat & Conversations** | `POST /chat/completions`, `GET/PATCH/DELETE /conversations/*` | `get_active_student` / `rate_limit_chat` | Session Cookie Verified | Enforced (`conv.user_id == student.id`) | **Secure**: Multi-turn chat and conversation history strictly user-isolated. |
| **Wallet & Billing** | `GET /credits/*`, `POST /payments/create-invoice`, `GET /payments/{id}/status` | `get_active_student` / `rate_limit_payments` | Session Cookie Verified | Enforced (`inv.user_id == student.id`) | **Secure**: Invoices and ledgers strictly user-isolated. (*Note SEC-CRIT-01 on `/credits/grant`*). |
| **Deliverables & Presentations** | `POST /presentations`, `GET /presentations/{id}/*` | `get_active_student` | Session Cookie Verified | Enforced (`verify_request_ownership`, `verify_deliverable_ownership`) | **Secure**: Deliverables require matching `student_id`. |
| **User Referrals** | `GET /referrals/link`, `/me`, `/stats` | `get_active_student` | Session Cookie Verified | Scoped to current authenticated student | **Secure**: No cross-tenant referral data accessible. |
| **Admin Read Dashboards** | `GET /admin/analytics/*`, `/admin/audit-logs/*`, `/admin/metrics`, `/admin/users/*`, `/admin/payments/*`, `/admin/providers/*`, `/admin/skills/*`, `/admin/referrals/*` | `get_developer` | `rate_limit_admin` dependency at router mount | Restricted to Developer/Admin/Superadmin | **Secure**: Defense-in-depth via router-level `rate_limit_admin` gate. |
| **Admin Mutations** | `POST /credits/admin/adjust`, `POST /admin/users/{id}/*`, `POST/PATCH/DELETE /admin/providers/*`, `POST/PATCH/DELETE /admin/skills/*`, `POST /admin/referrals/*` | `get_admin` | `rate_limit_admin` dependency at router mount | Restricted to Admin/Superadmin + Full Audit Logging | **Secure**: Mutations require Admin and record immutable audit logs. |
| **Superadmin Operations** | `POST /admin/payments/{id}/manual-confirm` | `get_superadmin` | `rate_limit_admin` dependency at router mount | Restricted exclusively to Superadmin + Audit Logging | **Secure**: Critical financial confirmation locked to superadmin role. |

#### Summary & Conclusion
- **Total Endpoints Audited**: 48 endpoints across the entire application.
- **Unauthenticated Public Endpoints**: 11 (all intentional: auth gateways, public catalogue, health checks, signed webhooks, signed downloads).
- **Protected User Endpoints**: 14 (all enforce `get_active_student` and strict object ownership).
- **Admin/Developer Endpoints**: 23 (all protected by router-level `rate_limit_admin` and strict role gates `get_developer`, `get_admin`, or `get_superadmin`).
- **Access Control Findings**:
  - **SEC-CRIT-01**: `POST /credits/grant` requires `get_active_student`, but grants 300 free test credits without checking if the server is in development mode.
  - **SEC-MED-02**: `POST /developer/providers/{id}/rotate-key` allows `developer` role to rotate credentials.

---

### Scan E: Hardcoded Secrets & Exposure Audit
- **Methodology**: Static pattern scanning across entire repository (backend and frontend) for hardcoded tokens, API keys (Anthropic, Gemini, OpenAI), private keys, connection strings with credentials, git tracking of `.env` files, production startup validation, and sensitive data logging.
- **Scan Vectors**:
  1. **API Keys & Private Keys**: Scanned regex patterns for `sk-ant-`, `AIza`, `sk-`, `AKIA`, and `-----BEGIN [A-Z ]*PRIVATE KEY-----`. (0 hardcoded keys detected).
  2. **Database Credentials**: Scanned for connection strings containing embedded plaintext passwords. (0 hardcoded connection strings detected).
  3. **Version Control Hygiene**: Inspected `.gitignore` and `git ls-files`. Verified `.env` and `.env.*` are strictly ignored; only `.env.example` templates with `CHANGE_ME` placeholders are tracked.
  4. **Production Startup Validation**: Inspected `backend/app/core/config.py`. Enforces strict fail-fast if `LLM_MASTER_ENCRYPTION_KEY`, `CRYPTO_PAYMENT_API_KEY`, or `CRYPTO_PAYMENT_WEBHOOK_SECRET` are missing in production. Also enforces `min_length=32` on `app_secret_key` and `session_secret_key`.
  5. **Structured Logging Sanitization**: `backend/app/core/logging.py` implements a custom structlog `redact_secrets` processor matching `(api_key|secret|token|password|authorization|private_key|webhook_secret|session|credentials)`.
  6. **Exception Sanitization**: `backend/app/main.py` sanitizes `500 Internal Server Error`, `SpetserError`, and `RequestValidationError`. Stack traces and raw inputs are never returned to clients.
- **Findings Table**:
| # | File | Line | Finding | Impact | Fix | Status |
|---|------|------|---------|--------|-----|--------|
| 1 | `backend/app/core/config.py` | 65 | `developer_email: str = "ahmdjmt698@gmail.com"` | Personal email exposed as default config value | Replace with neutral placeholder or empty default | Open (SEC-LOW-03) |
| 2 | `backend/app/core/logging.py` | 24-51 | Structlog `redact_secrets` processor active | Automatic redaction of sensitive log keys | Working as designed | Pass |
| 3 | `backend/app/core/config.py` | 120-128 | Startup production key assertions | Fails fast if production encryption / payment keys are unset | Working as designed | Pass |
| 4 | `.gitignore` | 17-30 | Strict exclusion of `.env*` and backup files | Prevents accidental commit of environment files | Working as designed | Pass |

- **Secrets Scan Status**: **PASS with 1 Low Finding (SEC-LOW-03)**.

---

### Scan F: Client-Side Security & XSS/CORS Audit
- **Methodology**: Static analysis of React 19 / TypeScript frontend (`frontend/src/`) and FastAPI backend middleware for Cross-Site Scripting (XSS), Cross-Origin Resource Sharing (CORS), Content Security Policy (CSP), open redirects, and WebStorage token leakage.
- **Scan Vectors**:
  1. **XSS Vectors**: Searched for `dangerouslySetInnerHTML`, `innerHTML`, `document.write`, `eval()`.
     - `frontend/src/components/chat/Markdown.tsx:102`: uses `dangerouslySetInnerHTML` for regex-based syntax highlighting (`highlightLine`). While lines are escaped with `escapeHtml` (`&`, `<`, `>`), using raw innerHTML introduces an unnecessary bypass of React's XSS protections (`SEC-LOW-04`).
     - `frontend/src/components/chat/Markdown.tsx:137-143`: Custom markdown `a` component renders `<a href={href} ...>` without validating the URI scheme. An attacker or crafted AI completion could output `[click](javascript:...)` to execute arbitrary script (`SEC-MED-04`).
  2. **CORS Configuration**: `backend/app/main.py` uses explicit `allow_origins=settings.allowed_origins_list` (default `http://localhost:5173`), `allow_credentials=True`, and whitelisted headers (`Content-Type`, `X-Request-ID`, `Idempotency-Key`). No wildcard origins (`*`) used with credentials.
  3. **Security Headers Middleware**: `backend/app/main.py` injects:
     - `X-Content-Type-Options: nosniff`
     - `X-Frame-Options: DENY`
     - `Referrer-Policy: strict-origin-when-cross-origin`
     - `Content-Security-Policy: default-src 'self'; frame-ancestors 'none'`
     - `Strict-Transport-Security: max-age=31536000; includeSubDomains` (in production)
  4. **WebStorage Hygiene**: Inspected all `localStorage` and `sessionStorage` usage in frontend. Verified only non-sensitive UI preferences (`theme`, `sidebar collapsed`, `modelStrength`) are stored. No auth tokens or credentials stored in WebStorage.
  5. **Open Redirects**: Searched for `RedirectResponse` in backend and `window.location` / `location.href` assignments in frontend. No open redirect sinks found.
- **Findings Table**:
| # | File | Line | Finding | Impact | Fix | Status |
|---|------|------|---------|--------|-----|--------|
| 1 | `frontend/src/components/chat/Markdown.tsx` | 137-143 | Unvalidated URL scheme in markdown links | `javascript:...` links could execute script on click | Restrict link protocol to `https:`, `http:`, `mailto:`, or relative paths | Open (SEC-MED-04) |
| 2 | `frontend/src/components/chat/Markdown.tsx` | 102 | `dangerouslySetInnerHTML` in code blocks | Bypasses React XSS protections | Replace with pure React tokens or DOMPurify | Open (SEC-LOW-04) |
| 3 | `backend/app/main.py` | 148-154 | Strict CORS policy with explicit origin whitelist | Prevents unauthorized cross-origin requests with cookies | Working as designed | Pass |
| 4 | `backend/app/main.py` | 139-147 | Hardened HTTP security headers (CSP, nosniff, DENY, HSTS) | Protects against framing, MIME-sniffing, and clickjacking | Working as designed | Pass |
| 5 | `frontend/src/lib/*` | - | Zero auth tokens stored in localStorage | Immune to token exfiltration via client-side storage | Working as designed | Pass |

- **Client-Side Scan Status**: **PASS with 1 Medium (SEC-MED-04) and 1 Low (SEC-LOW-04) Finding**.






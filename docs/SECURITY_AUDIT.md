# Spetser AI — Security Audit Report

## Summary
- **Date**: 2026-10-18
- **Auditor**: Lead Full-Stack Security Engineer & Design Architect
- **Scope**: Full Stack (Frontend + Backend + Infrastructure)
- **Methodology**: Inspired by `cloudflare/security-audit-skill` (Reconnaissance, Hunting, Validation)
- **Status**: Phase 1, Step 1.1 (Reconnaissance) Complete

## Discovered Findings

### Critical
| # | File | Line | Vulnerability / Issue | Impact | Fix | Status |
|---|------|------|-----------------------|--------|-----|--------|
| SEC-CRIT-01 | `backend/app/api/v1/routes/credits.py` | 79-94 | Unprotected test credit grant endpoint (`POST /credits/grant`) lacks environment check | Any active student in production can grant themselves unlimited 300-credit topups | Add `if not get_settings().is_development: raise AuthorizationError(...)` | Open |

### High
| # | File | Line | Vulnerability / Issue | Impact | Fix | Status |
|---|------|------|-----------------------|--------|-----|--------|
| SEC-HIGH-01 | `backend/app/api/deps.py` & `backend/app/services/auth.py` | 52-57, 185-233 | Development auth header bypass (`X-Dev-Auth`) active in dependency tree | If `app_env` is misconfigured as development, attacker can bypass authentication via header | Enforce strict fail-closed guards and explicit environment gating | Open |

### Medium
| # | File | Line | Vulnerability / Issue | Impact | Fix | Status |
|---|------|------|-----------------------|--------|-----|--------|
| SEC-MED-01 | `backend/app/api/v1/routes/auth.py` | 216 | `delete_cookie` in logout missing `secure=True` flag | In HTTPS sessions with secure session cookies, modern browsers may reject deletion, leaving cookie on client | Pass `secure=settings.is_production` to `response.delete_cookie` | Open |
| SEC-MED-02 | `backend/app/api/v1/routes/developer/providers.py` | 207-236 | Inconsistent RBAC on provider key rotation (`rotate-key` allows `developer` role) | Developers can rotate provider keys without admin/superadmin privilege | Align with `admin/providers.py` RBAC (`require_admin` / `require_superadmin`) | Open |
| SEC-MED-03 | `backend/app/api/v1/routes/webhooks.py` | 44-46 | Hardcoded fallback webhook secret (`"dev-webhook-secret"`) in non-production | Non-production environments can process forged payment webhooks if secret is unset | Require explicit webhook secret or reject requests when secret is empty | Open |

### Low
| # | File | Line | Vulnerability / Issue | Impact | Fix | Status |
|---|------|------|-----------------------|--------|-----|--------|
| SEC-LOW-01 | `backend/app/api/v1/routes/referrals.py` | 31-50 | Unthrottled public referral code validation (`GET /referrals/{code}/validate`) | Attackers can brute-force referral codes to enumerate valid codes and referrer display names | Add rate limiting (`@limiter.limit("30/minute")`) | Open |
| SEC-LOW-02 | `backend/app/api/v1/routes/presentations.py` | 193 | Route prefix discrepancy for deliverable download | Endpoint is `/api/v1/presentations/deliverables/{id}/download` while docstring states `/api/v1/deliverables/{id}/download` | Align route path or create alias | Open |

## Architecture & Positive Security Findings
- **Password Security**: Direct `bcrypt` hashing with salt and UTF-8 byte boundary checking (max 72 bytes) prevents hash truncation issues.
- **Timing Attack Mitigation**: `authenticate_student` runs a dummy `bcrypt` check against unknown emails to prevent timing-based user enumeration.
- **Provider API Key Protection**: AI provider keys are encrypted at rest using Fernet (AES-128-CBC + HMAC) and only returned masked (`sk-***abcd`) in responses.
- **IDOR Protection**: All resource access endpoints (`conversations`, `requests`, `deliverables`, `payments`) strictly verify ownership (`user_id == student.id`).
- **Idempotency & Replay Protection**: Strict idempotency keys are enforced on credit charges, payment invoices, and presentation generation.
- **CSRF & Cookie Hardening**: Session cookies use `HttpOnly=True`, `SameSite=Lax`, and `Secure=True` in production.
- **Session Revocation**: `session_version` integer on Student model ensures immediate revocation of all issued sessions upon ban or logout.

## Recommendations
1. Gate `POST /api/v1/credits/grant` immediately to ensure it can never be called in staging or production.
2. Update `delete_cookie` in `auth.py` to match cookie `secure` attribute.
3. Apply rate limiting to the public referral code validation endpoint.
4. Align RBAC on developer provider key rotation with admin policies.

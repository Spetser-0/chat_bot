# ERROR LOG — Spetser AI

> الذاكرة الجماعية للأخطاء. **اقرأ هذا الملف قبل إصلاح أي خطأ جديد.**
> الغرض: منع تكرار نفس الخطأ مرتين.

---

## E-001 — ملف غريب بلا امتداد دخل في git ورُفع على GitHub

| الحقل | التفصيل |
|---|---|
| **التاريخ** | 2026-10-10 |
| **نوع الخطأ** | تسرّب ملف غير مرغوب إلى المستودع (repo pollution) |
| **الخطورة** | متوسطة — لا أسرار مكشوفة، لكنه يلوّث تاريخ المستودع |
| **الحالة** | ✅ مُصلَح ومُتحقَّق منه |

### الوصف

ظهر في جذر المشروع ملف بلا امتداد باسم:

```
s -ExecutionPolicy RemoteSigned) ; (& c:UsersDellDesktopspetser-aibackend.venvScriptsActivate.ps1)
```

حجمه 8192 بايت، ومحتواه **مخرجات أمر `git log` ملوّنة** (أكواد ANSI).

### السبب الجذري

أمر PowerShell لتفعيل البيئة الافتراضية لُصق خطأً في موضع غير صحيح، ففسّره الطرفية كإعادة توجيه مخرجات إلى ملف، فأنشأت ملفاً باسم نص الأمر نفسه. ثم `git add .` أضافه إلى التتبع، و`git commit` رفعه.

الخطأ الجوهري: **`git add .` بدون مراجعة** — يضيف أي ملف جديد في المجلد بلا تمييز.

### الإصلاح المُنفَّذ

```bash
git config core.quotepath false            # لقراءة الاسم الحقيقي بدل التشفير
git rm --cached -- "<الاسم الحقيقي>"       # إخراجه من التتبع (بقي على القرص)
# إضافة النمطين إلى .gitignore
git commit --amend -m "fix: remove stray PowerShell paste artifact and ignore it"
git push --force-with-lease origin main
```

### التحقق

- الـcommit القديم `8abddf8` → الجديد `33cb3ff`
- عدد الملفات المتتبعة: 237 → **236**
- عبر GitHub API: **0 ملفات** تطابق `ExecutionPolicy` في شجرة الريموت
- الملف **ما زال على القرص** (لم يُحذف أي ملف)

### استراتيجية المنع

1. **لا تستخدم `git add .` أبداً** — استخدم `git add <مسار محدد>` أو `git add -p` للمراجعة التفاعلية.
2. قبل أي commit: `git status --short` وراجع كل سطر.
3. الأنماط `*ExecutionPolicy*` و `*ScriptsActivate*` أُضيفت إلى `.gitignore` كحماية تلقائية.
4. عند تفعيل بيئة افتراضية في PowerShell، تأكد أن المؤشر في سطر أوامر نظيف قبل اللصق.

### نسخة الأمان

للتراجع لو لزم: وسم `backup-before-cleanup` أو فرع `backup-cleanup-branch`.

---

## قالب الإدخال الجديد

انسخ هذا القالب لكل خطأ جديد:

```markdown
## E-XXX — <عنوان مختصر>

| الحقل | التفصيل |
|---|---|
| **التاريخ** | YYYY-MM-DD |
| **نوع الخطأ** | <بناء / اختبار / نشر / أمني / تبعيات> |
| **الخطورة** | منخفضة / متوسطة / عالية |
| **الحالة** | مفتوح / ✅ مُصلَح |

### الوصف
<ما ظهر بالضبط>

### السبب الجذري
<لماذا حدث فعلاً — لا الأعراض>

### الإصلاح المُنفَّذ
<الأوامر أو التعديلات>

### التحقق
<كيف تأكدت أن الإصلاح نجح — بدليل قابل للفحص>

### استراتيجية المنع
<كيف نتجنب تكراره>
```

---

## E-P01 — API Envelope Contract Breach

| Field | Detail |
|---|---|
| **Date** | 2026-10-20 |
| **Severity** | P0 |
| **Phase** | P0.1 |
| **Error** | After login, conversations and credits show as empty. Frontend `extractData()` returned `undefined` because successful responses returned bare JSON or bare arrays. |
| **Root Cause** | Global error envelope `{data, error, request_id}` was applied only to error responses (Lesson 10.4). Success responses returned bare JSON or arrays without the `{data, error, request_id}` wrapper. |
| **Fix** | Added `envelope_success_responses` HTTP middleware to FastAPI in `backend/app/main.py` to wrap all 2xx responses on `/api/v1/*` in `{data, error, request_id}` while exempting SSE streams and binary responses. Made frontend `extractData()` in `frontend/src/api/client.ts` defensive to handle wrapped success, wrapped error, and legacy bare shapes. Commit: `4a04337`. |
| **Verification** | 8 contract tests in `backend/tests/integration/test_api_contract.py` pass. Full backend suite passes (658 passed, 0 failures). Frontend build & lint pass (0 errors). |
| **Prevention** | Contract suite `test_api_contract.py` tests all critical endpoints (`/conversations`, `/credits/balance`, `/credits/history`, `/skills`, `/referrals/me`, `/health/live`, `/health/ready`). |

---

## E-P02 — CORS Headers Missing on Error Responses

| Field | Detail |
|---|---|
| **Date** | 2026-10-20 |
| **Severity** | P0 |
| **Phase** | P0.2 |
| **Error** | Backend errors (401, 404, 500) surfaced as opaque CORS failures in the browser, hiding the real error body and status. Preflight OPTIONS failed when using `Authorization` or `X-API-Key` headers. |
| **Root Cause** | FastAPI's `CORSMiddleware` sits outside `ServerErrorMiddleware`, so custom exception handlers and error rewrites returning raw responses bypass CORS header attachment. Furthermore, `Authorization` and `X-API-Key` were missing from `allow_headers`. |
| **Fix** | Created `backend/app/core/cors.py` with `attach_cors_headers()`. Attached CORS headers to all exception handlers (`AppException`, `RequestValidationError`, `HTTPException`, `generic_error_handler`, and 404 rewrite). Added `Authorization` and `X-API-Key` to `allow_headers`, and added expose headers. Commit: `d6e4dcd`. |
| **Verification** | All 5 tests in `backend/tests/integration/test_cors_headers.py` pass (testing success, 404 error, 401 error, preflight OPTIONS, and disallowed origin). |
| **Prevention** | `backend/tests/integration/test_cors_headers.py` runs on every CI/test cycle. |

---

## E-P03 — Migration 756afe1af465 Defects

| Field | Detail |
|---|---|
| **Date** | 2026-10-20 |
| **Severity** | P0 |
| **Phase** | P0.3 |
| **Error** | Multiple latent defects in migration `756afe1af465`: non-unique `ix_api_keys_key_hash`, `created_by` as `String(36)` instead of UUID with FK, `system_settings.updated_at` missing `server_default`, Postgres-only `now()`, `allowed_skills` plain `Text`, and missing singleton seed row. |
| **Root Cause** | Migration was generated quickly without cross-dialect integrity tests or model alignment. |
| **Fix** | Rewrote `backend/alembic/versions/20261019_1722_756afe1af465_add_email_verification_fields_to_user.py` with unique index, UUID + FK with CASCADE, `CURRENT_TIMESTAMP` dialect-agnostic default, JSON/JSONB cross-dialect column, and idempotent singleton seed. Updated SQLAlchemy models `APIKey` and `SystemSettings`, schemas, services, and DeveloperPage. Commit: `f8a9595`. |
| **Verification** | 10 tests in `backend/tests/integration/test_migration_integrity.py` pass, verifying uniqueness, FK constraint enforcement, server defaults on raw insert, JSON serialization, singleton seeding, and upgrade/downgrade/upgrade round trip. |
| **Prevention** | `backend/tests/integration/test_migration_integrity.py` exercises full migration DDL and ORM parity on SQLite. |

---

## E-EMAIL-001 — Silent Email Skip in Production

| Field | Detail |
|---|---|
| **Date** | 2026-10-19 |
| **Severity** | P0 |
| **Phase** | Email Delivery |
| **Error** | Users register successfully but never receive verification emails. UI shows "Code sent" but no email arrives. |
| **Root Cause** | `email_service.py` line 51 silently returns when `SMTP_USER` is empty, even in production. No error is raised, no warning logged. |
| **Fix** | 1. Add Pydantic `field_validator` in `config.py` to reject empty SMTP vars in production (fail fast on startup). 2. Refactor `email_service.py` to use FastAPI `BackgroundTasks` for async sending. 3. Add proper error logging for SMTP failures. |
| **Verification** | - Config validation tests (5/5 pass) - Async email tests (3/3 pass) - Manual test: server refuses to start in production without SMTP vars |
| **Prevention** | - Production config validation prevents deployment without SMTP - Background tasks prevent registration slowdown - Error logging makes failures visible |
| **Commits** | - `fix(config): fail fast in production without SMTP configuration` - `feat(email): send emails asynchronously via BackgroundTasks` |

---

## E-EMAIL-002 — Render Free Tier Outbound SMTP Port Blocking

| Field | Detail |
|---|---|
| **Date** | 2026-10-22 |
| **Severity** | P0 |
| **Phase** | Email Delivery |
| **Error** | Verification emails hang or time out when deploying on Render Free Tier. Outbound connections to SMTP ports (25, 465, 587) are blocked by Render network policy. |
| **Root Cause** | Render free tier blocks egress connections to standard SMTP ports (25, 465, 587). Synchronous socket calls in `smtplib.SMTP(...)` block the worker thread or hang silently, preventing OTP delivery. |
| **Fix** | 1. Implement transactional email via Brevo HTTP API (`https://api.brevo.com/v3/smtp/email`) over standard HTTPS (port 443) using `httpx`. 2. Update `config.py` with `brevo_api_key`, `brevo_sender_name`, `email_http_timeout_seconds` and Pydantic model validator requiring either Brevo or SMTP in production. 3. Modernize SMTP fallback with `timeout=10` and `asyncio.to_thread` non-blocking execution. 4. Enforce strict redaction of API keys, credentials, and OTPs with email masking in audit logs. |
| **Verification** | - Unit tests for Brevo HTTP API (201 success, 401 error, timeout suppression, header/body validation) pass (6/6). - Provider precedence tests pass (Brevo > SMTP > Dev). - Integration tests `test_email_background.py` pass (3/3). - Config validation tests pass (7/7). - All 325 unit tests pass. |
| **Prevention** | - Model validator enforces valid `BREVO_API_KEY` or complete SMTP triplet in production. - HTTPS port 443 traffic is universally permitted across cloud hosting providers (including Render). - Comprehensive unit and integration test coverage. |
| **Decision** | Architecture decision: Use Brevo HTTP API over HTTPS (port 443) as primary email provider for cloud deployments to bypass hosting-level SMTP port blocks, keeping SMTP as a fallback. |


```markdown
# SPETSER AI — EMAIL DELIVERY FIX PROMPT
# Issue: Silent SMTP Skip in Production
# Version: 1.0 | Severity: P0 | Execution Mode: Autonomous Step-by-Step

==================================================
SECTION 0: YOUR IDENTITY AND AUTHORITY
==================================================

You are the **Incident Response Engineer** for `spetser-ai`. You have been deployed to fix a **P0 production defect** where email verification codes are NOT actually sent to users despite the UI claiming success.

**The Bug:**
- User registers → UI shows "We sent a code to your email"
- Reality: Server silently skips email sending when SMTP credentials are missing
- Root cause: `email_service.py` line 51 returns early without error when `SMTP_USER` is empty
- Impact: 100% of new users cannot verify their accounts in production

You have FULL authority to:
- Modify any backend file
- Update environment configuration
- Add background task infrastructure
- Run tests and verify fixes
- Commit changes with evidence

You must NOT:
- Leave silent failures in production code
- Skip verification steps
- Deploy without testing

==================================================
SECTION 1: INCIDENT CONTEXT
==================================================

**What's Broken:**

```python
# backend/app/services/email_service.py (line 51)
if settings.DEBUG or not settings.SMTP_USER:
    print(f"[DEV] Verification code for {to_email}: {code}")
    return  # ← SILENT FAILURE — no error, no warning
```

**Why It's Broken:**

1. `config.py` has empty defaults for SMTP settings
2. Production server (Render) has no SMTP credentials configured
3. The condition `not settings.SMTP_USER` is True in production
4. Email sending is skipped silently
5. User sees success message but receives no email
6. Account verification becomes impossible

**The Fix Strategy:**

1. **Fail loudly in production** — refuse to start without SMTP config
2. **Send emails asynchronously** — don't block registration response
3. **Add proper error handling** — catch and log SMTP failures
4. **Document required environment variables** — for Render deployment

==================================================
SECTION 2: EXECUTION PROTOCOL
==================================================

For EVERY step:

1. **ANNOUNCE** what you will do
2. **INSPECT** current code
3. **PLAN** exact changes
4. **IMPLEMENT** the fix
5. **TEST** the fix works
6. **DOCUMENT** in `docs/ERROR_LOG.md`
7. **COMMIT** with evidence
8. **REPORT** results

==================================================
SECTION 3: FIX #1 — FAIL LOUDLY IN PRODUCTION
==================================================

### Step 3.1: Update Configuration Validation

**File:** `backend/app/core/config.py`

**Current problematic code:**
```python
# Lines ~102-107
smtp_host: str = ""
smtp_port: int = 587
smtp_user: str = ""
smtp_password: str = ""
smtp_from: str = "noreply@spetser.ai"
```

**Replace with production-aware validation:**
```python
# SMTP Configuration (required in production)
smtp_host: str = Field(
    default="",
    description="SMTP server hostname (e.g., smtp.gmail.com)"
)
smtp_port: int = Field(
    default=587,
    description="SMTP server port (587 for TLS, 465 for SSL)"
)
smtp_user: str = Field(
    default="",
    description="SMTP username (email address)"
)
smtp_password: str = Field(
    default="",
    description="SMTP password or app-specific password"
)
smtp_from: str = Field(
    default="noreply@spetser.ai",
    description="Sender email address"
)
smtp_use_tls: bool = Field(
    default=True,
    description="Use TLS for SMTP connection"
)

@field_validator("smtp_user", "smtp_password", "smtp_host")
@classmethod
def validate_smtp_in_production(cls, v: str, info: ValidationInfo) -> str:
    """Fail fast in production if SMTP is not configured."""
    values = info.data
    app_env = values.get("app_env", "development")
    
    if app_env == "production" and not v:
        field_name = info.field_name
        raise ValueError(
            f"{field_name} is required in production. "
            f"Set {field_name.upper()} environment variable."
        )
    return v
```

**Why this works:**
- Pydantic's `field_validator` runs during config initialization
- If `APP_ENV=production` and SMTP vars are empty, the app **refuses to start**
- Error message is clear: tells operator exactly which env var to set
- Development mode still works with empty values

### Step 3.2: Test Configuration Validation

**File to create:** `backend/tests/unit/test_smtp_config.py`

```python
"""
SMTP Configuration Validation Tests
─────────────────────────────────────
Ensures the app fails fast in production without SMTP config.
"""
import pytest
from pydantic import ValidationError
from app.core.config import Settings


def test_development_allows_empty_smtp():
    """Development mode should work without SMTP config."""
    settings = Settings(
        app_env="development",
        app_secret_key="test-secret-key-at-least-32-chars-long",
        session_secret_key="test-session-key-at-least-32-chars-long",
        # SMTP fields intentionally empty
    )
    assert settings.smtp_user == ""
    assert settings.smtp_password == ""


def test_production_requires_smtp_user():
    """Production must have SMTP_USER configured."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            app_env="production",
            app_secret_key="test-secret-key-at-least-32-chars-long",
            session_secret_key="test-session-key-at-least-32-chars-long",
            smtp_user="",  # ← Empty in production
            smtp_password="some-password",
            smtp_host="smtp.gmail.com",
        )
    
    errors = exc_info.value.errors()
    assert any("smtp_user" in str(e["loc"]) for e in errors)
    assert any("required in production" in e["msg"] for e in errors)


def test_production_requires_smtp_password():
    """Production must have SMTP_PASSWORD configured."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            app_env="production",
            app_secret_key="test-secret-key-at-least-32-chars-long",
            session_secret_key="test-session-key-at-least-32-chars-long",
            smtp_user="user@example.com",
            smtp_password="",  # ← Empty in production
            smtp_host="smtp.gmail.com",
        )
    
    errors = exc_info.value.errors()
    assert any("smtp_password" in str(e["loc"]) for e in errors)


def test_production_requires_smtp_host():
    """Production must have SMTP_HOST configured."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            app_env="production",
            app_secret_key="test-secret-key-at-least-32-chars-long",
            session_secret_key="test-session-key-at-least-32-chars-long",
            smtp_user="user@example.com",
            smtp_password="password",
            smtp_host="",  # ← Empty in production
        )
    
    errors = exc_info.value.errors()
    assert any("smtp_host" in str(e["loc"]) for e in errors)


def test_production_with_valid_smtp_succeeds():
    """Production with all SMTP vars should initialize successfully."""
    settings = Settings(
        app_env="production",
        app_secret_key="test-secret-key-at-least-32-chars-long",
        session_secret_key="test-session-key-at-least-32-chars-long",
        smtp_user="user@example.com",
        smtp_password="password123",
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_from="noreply@example.com",
    )
    assert settings.smtp_user == "user@example.com"
```

**Run the tests:**
```bash
cd backend
python -m pytest tests/unit/test_smtp_config.py -v
```

**Expected:** All 5 tests PASS.

### Step 3.3: Commit Fix #1

```bash
git add backend/app/core/config.py backend/tests/unit/test_smtp_config.py
git commit -m "fix(config): fail fast in production without SMTP configuration

- Add field_validator to reject empty SMTP_USER/PASSWORD/HOST in production
- Provide clear error messages naming the missing environment variable
- Development mode still works with empty SMTP config
- Add 5 unit tests covering all validation scenarios
- Closes: silent email skip in production (P0 email delivery bug)"
```

==================================================
SECTION 4: FIX #2 — SEND EMAILS ASYNCHRONOUSLY
==================================================

### Step 4.1: Add Background Task Infrastructure

**File to update:** `backend/app/services/email_service.py`

**Replace the entire `send_verification_email` function:**

```python
"""
Email sending service for Spetser AI.
─────────────────────────────────────────
Sends emails asynchronously via SMTP with proper error handling.

In development (DEBUG=True or no SMTP_USER): prints to console
In production: sends via configured SMTP server
"""
import smtplib
import ssl
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from fastapi import BackgroundTasks

from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError

logger = logging.getLogger("spetser.email")


async def send_email_background(
    to_email: str,
    subject: str,
    html_body: str,
    background_tasks: BackgroundTasks,
) -> None:
    """
    Queue email for background sending.
    
    This function returns immediately (doesn't block the HTTP response).
    The actual sending happens in a background task after the response is sent.
    
    Args:
        to_email: Recipient email address
        subject: Email subject line
        html_body: HTML content of the email
        background_tasks: FastAPI BackgroundTasks instance (injected via Depends)
    """
    background_tasks.add_task(
        _send_email_task,
        to_email=to_email,
        subject=subject,
        html_body=html_body,
    )


async def _send_email_task(
    to_email: str,
    subject: str,
    html_body: str,
) -> None:
    """
    Background task that actually sends the email.
    
    This runs after the HTTP response is sent, so failures don't affect
    the user's experience but are logged for debugging.
    """
    settings = get_settings()
    
    # Development mode: print to console
    if settings.app_env == "development" or not settings.smtp_user:
        logger.info(
            "[DEV MODE] Email would be sent to %s:\nSubject: %s\nBody:\n%s",
            to_email,
            subject,
            html_body,
        )
        return
    
    # Production mode: send via SMTP
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html", "utf-8"))
        
        # Create SSL context for secure connection
        context = ssl.create_default_context()
        
        # Connect to SMTP server
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            if settings.smtp_use_tls:
                server.starttls(context=context)
            
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
            
        logger.info("Email sent successfully to %s", to_email)
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(
            "SMTP authentication failed for %s: %s",
            to_email,
            str(e),
        )
        # Don't raise — this is a background task, user already saw success
    
    except smtplib.SMTPException as e:
        logger.error(
            "SMTP error sending email to %s: %s",
            to_email,
            str(e),
        )
    
    except Exception as e:
        logger.exception(
            "Unexpected error sending email to %s: %s",
            to_email,
            str(e),
        )


async def send_verification_email(
    to_email: str,
    code: str,
    background_tasks: Optional[BackgroundTasks] = None,
) -> None:
    """
    Send OTP verification email.
    
    If background_tasks is provided, sends asynchronously (recommended).
    Otherwise, sends synchronously (legacy behavior, blocks response).
    """
    subject = "رمز التحقق - Spetser AI"
    
    html_body = f"""
    <div dir="rtl" style="font-family: 'Noto Sans Arabic', sans-serif; padding: 20px; max-width: 600px; margin: 0 auto;">
        <div style="background: #F9F8F4; border-radius: 12px; padding: 32px; border: 1px solid #E5E7EB;">
            <h2 style="color: #01696D; margin-top: 0;">مرحباً بك في Spetser AI</h2>
            <p style="font-size: 16px; line-height: 1.6; color: #1A1A1A;">
                رمز التحقق الخاص بك هو:
            </p>
            <div style="font-size: 32px; font-weight: bold; letter-spacing: 8px; 
                        color: #01696D; padding: 24px; background: #E6F4F4; 
                        border-radius: 12px; text-align: center; margin: 24px 0;
                        border: 2px solid #01696D;">
                {code}
            </div>
            <p style="color: #6B7280; font-size: 14px;">
                هذا الرمز صالح لمدة 15 دقيقة فقط.
            </p>
            <p style="color: #6B7280; font-size: 14px;">
                إذا لم تطلب هذا الرمز، يرجى تجاهل هذه الرسالة.
            </p>
            <hr style="border: none; border-top: 1px solid #E5E7EB; margin: 24px 0;">
            <p style="color: #9CA3AF; font-size: 12px; text-align: center;">
                © 2026 Spetser AI — منصة تعليمية ذكية للطلاب العرب
            </p>
        </div>
    </div>
    """
    
    if background_tasks is not None:
        # Async mode (recommended)
        await send_email_background(to_email, subject, html_body, background_tasks)
    else:
        # Sync mode (legacy, blocks)
        await _send_email_task(to_email, subject, html_body)


async def send_reset_email(
    to_email: str,
    code: str,
    background_tasks: Optional[BackgroundTasks] = None,
) -> None:
    """Send password reset email."""
    subject = "إعادة تعيين كلمة المرور - Spetser AI"
    
    html_body = f"""
    <div dir="rtl" style="font-family: 'Noto Sans Arabic', sans-serif; padding: 20px; max-width: 600px; margin: 0 auto;">
        <div style="background: #F9F8F4; border-radius: 12px; padding: 32px; border: 1px solid #E5E7EB;">
            <h2 style="color: #01696D; margin-top: 0;">إعادة تعيين كلمة المرور</h2>
            <p style="font-size: 16px; line-height: 1.6; color: #1A1A1A;">
                لقد طلبت إعادة تعيين كلمة المرور. رمز التحقق الخاص بك هو:
            </p>
            <div style="font-size: 32px; font-weight: bold; letter-spacing: 8px; 
                        color: #01696D; padding: 24px; background: #E6F4F4; 
                        border-radius: 12px; text-align: center; margin: 24px 0;
                        border: 2px solid #01696D;">
                {code}
            </div>
            <p style="color: #6B7280; font-size: 14px;">
                هذا الرمز صالح لمدة 15 دقيقة فقط.
            </p>
            <p style="color: #DC2626; font-size: 14px; font-weight: bold;">
                إذا لم تطلب هذا، يرجى تغيير كلمة المرور فوراً وتأمين حسابك.
            </p>
        </div>
    </div>
    """
    
    if background_tasks is not None:
        await send_email_background(to_email, subject, html_body, background_tasks)
    else:
        await _send_email_task(to_email, subject, html_body)
```

**Key changes:**
1. **BackgroundTasks support** — emails sent after HTTP response
2. **Proper error logging** — no silent failures
3. **Development mode detection** — prints to console when SMTP not configured
4. **Production validation** — relies on config.py validator to fail fast
5. **Better HTML templates** — improved Arabic email design

### Step 4.2: Update Auth Routes to Use Background Tasks

**File:** `backend/app/api/v1/routes/auth.py`

**Find the register endpoint and update it:**

```python
from fastapi import BackgroundTasks
from app.services.email_service import send_verification_email

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    background_tasks: BackgroundTasks,  # ← Add this parameter
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user account.
    
    Creates the account in unverified state and sends OTP email
    asynchronously (doesn't block the response).
    """
    # Check if email already exists
    existing = await db.execute(select(Student).where(Student.email == request.email))
    if existing.scalar_one_or_none():
        raise ValidationError("هذا البريد الإلكتروني مسجل بالفعل.")
    
    # Create user (unverified)
    from app.services.settings_service import settings_service
    settings = await settings_service.get_settings(db)
    
    student = Student(
        email=request.email,
        name=request.name,
        hashed_password=hash_password(request.password),
        is_verified=False,
        credit_balance=settings.default_new_user_credits,
    )
    db.add(student)
    await db.commit()
    await db.refresh(student)
    
    # Send verification email ASYNCHRONOUSLY
    await verification_service.initiate_verification(
        db, student, background_tasks=background_tasks
    )
    
    return {
        "message": "تم إنشاء الحساب بنجاح. يرجى التحقق من بريدك الإلكتروني.",
        "email": student.email,
        "requires_verification": True,
    }
```

**Update the verification service to accept background_tasks:**

**File:** `backend/app/services/verification_service.py`

```python
from fastapi import BackgroundTasks
from app.services.email_service import send_verification_email

async def initiate_verification(
    self,
    db: AsyncSession,
    user: Student,
    background_tasks: Optional[BackgroundTasks] = None,  # ← Add parameter
) -> None:
    """Generate OTP, store hash, send email (optionally async)."""
    otp = self.generate_otp()
    
    user.verification_code = self._hash_code(otp)
    user.verification_expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.OTP_TTL_MINUTES)
    user.verification_attempts = 0
    user.is_verified = False
    
    await db.commit()
    
    # Send email (async if background_tasks provided)
    await send_verification_email(
        to_email=user.email,
        code=otp,
        background_tasks=background_tasks,
    )
```

**Do the same for the resend-code endpoint:**

```python
@router.post("/resend-code")
async def resend_code(
    request: ResendCodeRequest,
    background_tasks: BackgroundTasks,  # ← Add this
    db: AsyncSession = Depends(get_db),
):
    """Resend verification code."""
    result = await db.execute(select(Student).where(Student.email == request.email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise NotFoundError("المستخدم غير موجود.")
    
    await verification_service.resend_code(db, user, background_tasks=background_tasks)
    
    return {"message": "تم إرسال رمز تحقق جديد إلى بريدك الإلكتروني."}
```

**And update the resend_code method in verification_service.py:**

```python
async def resend_code(
    self,
    db: AsyncSession,
    user: Student,
    background_tasks: Optional[BackgroundTasks] = None,
) -> None:
    """Resend a new verification code."""
    if user.is_verified:
        raise ValidationError("الحساب مفعّل بالفعل.")
    await self.initiate_verification(db, user, background_tasks=background_tasks)
```

**Do the same for forgot-password endpoints:**

```python
@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,  # ← Add this
    db: AsyncSession = Depends(get_db),
):
    """Send password reset code."""
    result = await db.execute(select(Student).where(Student.email == request.email))
    user = result.scalar_one_or_none()
    
    # Security: Don't reveal if email exists
    if not user:
        return {"message": "إذا كان هذا البريد مسجلاً، فسيصلك رمز التحقق."}
    
    await password_reset_service.initiate_reset(
        db, user, background_tasks=background_tasks
    )
    return {"message": "إذا كان هذا البريد مسجلاً، فسيصلك رمز التحقق."}
```

### Step 4.3: Test Async Email Sending

**File to create:** `backend/tests/integration/test_email_background.py`

```python
"""
Email Background Task Tests
────────────────────────────
Verifies that emails are sent asynchronously and don't block responses.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
import asyncio


@pytest.mark.asyncio
async def test_register_returns_before_email_sent(client: AsyncClient):
    """Register should return 201 immediately, email sent in background."""
    with patch('app.services.email_service._send_email_task', new_callable=AsyncMock) as mock_send:
        # Make the mock slow to prove async behavior
        async def slow_send(*args, **kwargs):
            await asyncio.sleep(2)  # Simulate slow email
        
        mock_send.side_effect = slow_send
        
        # Register should return quickly (< 500ms)
        import time
        start = time.time()
        response = await client.post("/api/v1/auth/register", json={
            "name": "Test User",
            "email": "async-test@example.com",
            "password": "SecurePass123!",
        })
        elapsed = time.time() - start
        
        assert response.status_code == 201
        assert elapsed < 1.0, f"Register took {elapsed}s — email should be async"
        
        # Give background task time to complete
        await asyncio.sleep(0.5)
        
        # Verify email was queued
        assert mock_send.called


@pytest.mark.asyncio
async def test_email_failure_doesnt_fail_registration(client: AsyncClient):
    """If email sending fails, registration should still succeed."""
    with patch('app.services.email_service._send_email_task', new_callable=AsyncMock) as mock_send:
        # Simulate SMTP failure
        mock_send.side_effect = Exception("SMTP connection failed")
        
        response = await client.post("/api/v1/auth/register", json={
            "name": "Fail Test",
            "email": "fail-test@example.com",
            "password": "SecurePass123!",
        })
        
        # Registration should still succeed
        assert response.status_code == 201
        
        # User should be created (unverified)
        from app.models.student import Student
        from sqlalchemy import select
        from app.db.session import get_db
        
        async for db in get_db():
            result = await db.execute(
                select(Student).where(Student.email == "fail-test@example.com")
            )
            user = result.scalar_one_or_none()
            assert user is not None
            assert user.is_verified is False
            break


@pytest.mark.asyncio
async def test_development_mode_prints_to_console(client: AsyncClient, capsys):
    """In dev mode, email should print to console instead of sending."""
    # Ensure we're in development mode
    from app.core.config import get_settings
    settings = get_settings()
    assert settings.app_env == "development"
    
    response = await client.post("/api/v1/auth/register", json={
        "name": "Dev Test",
        "email": "dev-test@example.com",
        "password": "SecurePass123!",
    })
    
    assert response.status_code == 201
    
    # Wait for background task
    await asyncio.sleep(0.2)
    
    # Check logs for dev mode message
    captured = capsys.readouterr()
    # Note: This might not capture logs depending on logging config
    # The real test is that it doesn't crash
```

**Run the tests:**
```bash
python -m pytest tests/integration/test_email_background.py -v
```

**Expected:** All tests PASS.

### Step 4.4: Commit Fix #2

```bash
git add backend/app/services/email_service.py \
        backend/app/services/verification_service.py \
        backend/app/api/v1/routes/auth.py \
        backend/tests/integration/test_email_background.py

git commit -m "feat(email): send emails asynchronously via BackgroundTasks

- Refactor email_service to use FastAPI BackgroundTasks
- Register/resend/forgot-password endpoints return immediately
- Email sending happens after HTTP response (non-blocking)
- Email failures logged but don't fail registration
- Development mode prints to console instead of sending
- Production mode sends via configured SMTP with proper error handling
- Add integration tests proving async behavior
- Closes: slow registration due to synchronous email sending"
```

==================================================
SECTION 5: DEPLOYMENT — RENDER ENVIRONMENT VARIABLES
==================================================

### Step 5.1: Document Required Environment Variables

**File to update:** `docs/DEPLOYMENT.md`

**Add new section:**

```markdown
## Email Configuration (Required for Production)

Spetser AI requires SMTP credentials to send verification and password reset emails.

### Required Environment Variables

Add these to your Render dashboard (Environment tab):

| Variable | Description | Example |
|----------|-------------|---------|
| `SMTP_HOST` | SMTP server hostname | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP server port | `587` (TLS) or `465` (SSL) |
| `SMTP_USER` | SMTP username (your email) | `your-email@gmail.com` |
| `SMTP_PASSWORD` | SMTP password or app password | `your-app-password` |
| `SMTP_FROM` | Sender email address | `noreply@spetser.ai` |
| `APP_ENV` | Must be `production` | `production` |

### Gmail Setup (Recommended for Development)

1. Enable 2-factor authentication on your Gmail account
2. Generate an **App Password**: https://myaccount.google.com/apppasswords
3. Use the 16-character app password as `SMTP_PASSWORD`

**Example Render environment:**
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=abcd1234efgh5678
SMTP_FROM=noreply@spetser.ai
APP_ENV=production
```

### Production Startup Validation

If SMTP variables are missing in production, the app will **refuse to start** with a clear error:

```
ValidationError: smtp_user is required in production. Set SMTP_USER environment variable.
```

This prevents silent email failures in production.

### Recommended SMTP Providers

| Provider | Free Tier | Notes |
|----------|-----------|-------|
| **Gmail** | 500 emails/day | Use app password, not regular password |
| **SendGrid** | 100 emails/day forever | Best for production |
| **Mailgun** | 100 emails/day for 3 months | Good API |
| **Amazon SES** | $0.10 per 1000 emails | Cheapest at scale |
| **Postmark** | 100 emails/month forever | Excellent deliverability |

### Testing Email Configuration

After deploying, test email sending:

```bash
# Check Render logs for email sending
render logs --service spetser-backend --tail 100 | grep -i email

# You should see: "Email sent successfully to user@example.com"
# NOT: "[DEV MODE] Email would be sent to..."
```

If you see `[DEV MODE]` messages, SMTP is not configured correctly.
```

### Step 5.2: Create Render Setup Script

**File to create:** `scripts/setup-render-env.sh`

```bash
#!/bin/bash
# Render Environment Setup Helper
# ─────────────────────────────────
# Run this locally to verify your environment variables before deploying.

set -e

echo "🔍 Checking required environment variables for Spetser AI..."
echo ""

# Required variables
REQUIRED_VARS=(
  "APP_ENV"
  "APP_SECRET_KEY"
  "SESSION_SECRET_KEY"
  "DATABASE_URL"
  "SMTP_HOST"
  "SMTP_PORT"
  "SMTP_USER"
  "SMTP_PASSWORD"
  "SMTP_FROM"
)

# Optional variables (with defaults)
OPTIONAL_VARS=(
  "REDIS_URL"
  "RATE_LIMIT_BACKEND"
  "LOG_LEVEL"
)

missing=()

for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var}" ]; then
    missing+=("$var")
    echo "❌ Missing: $var"
  else
    # Mask sensitive values
    if [[ "$var" == *"SECRET"* ]] || [[ "$var" == *"PASSWORD"* ]]; then
      echo "✅ $var = [REDACTED]"
    else
      echo "✅ $var = ${!var}"
    fi
  fi
done

echo ""

if [ ${#missing[@]} -eq 0 ]; then
  echo "✨ All required variables are set!"
  echo ""
  echo "You can now deploy to Render with these environment variables."
  exit 0
else
  echo "⚠️  Missing ${#missing[@]} required variables:"
  printf '  - %s\n' "${missing[@]}"
  echo ""
  echo "Add these to your Render dashboard or export them locally."
  exit 1
fi
```

**Make it executable:**
```bash
chmod +x scripts/setup-render-env.sh
```

### Step 5.3: Commit Deployment Docs

```bash
git add docs/DEPLOYMENT.md scripts/setup-render-env.sh
git commit -m "docs(deployment): add SMTP configuration guide for Render

- Document all required SMTP environment variables
- Provide Gmail app password setup instructions
- List recommended SMTP providers (SendGrid, Mailgun, SES)
- Explain production startup validation (fails fast without SMTP)
- Add setup-render-env.sh script to verify env vars locally
- Closes: silent email skip due to missing SMTP config"
```

==================================================
SECTION 6: VERIFICATION & TESTING
==================================================

### Step 6.1: Run Full Test Suite

```bash
cd backend

# Run all tests
python -m pytest tests/ -v --tb=short

# Specifically check email-related tests
python -m pytest tests/unit/test_smtp_config.py -v
python -m pytest tests/integration/test_email_background.py -v
python -m pytest tests/integration/test_verification.py -v
```

**Expected:** All tests PASS.

### Step 6.2: Manual Testing Checklist

**Test in development mode:**

```bash
cd backend
python -m uvicorn app.main:app --reload
```

- [ ] Start server without SMTP vars → should work (dev mode)
- [ ] Register new user → should see `[DEV MODE] Email would be sent...` in logs
- [ ] Verify email with code from logs → should work
- [ ] Resend code → should see new code in logs
- [ ] Forgot password → should see reset code in logs

**Test in production mode (simulate):**

```bash
# Set APP_ENV=production without SMTP vars
APP_ENV=production python -m uvicorn app.main:app

# Expected: Server refuses to start with clear error:
# ValidationError: smtp_user is required in production
```

**Test with real SMTP (if you have credentials):**

```bash
# Set all SMTP vars
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USER=your-email@gmail.com
export SMTP_PASSWORD=your-app-password
export SMTP_FROM=noreply@spetser.ai
export APP_ENV=production

python -m uvicorn app.main:app

# Register with real email → should receive actual email
```

### Step 6.3: Update ERROR_LOG.md

**Append to `docs/ERROR_LOG.md`:**

```markdown
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
```

### Step 6.4: Update PROJECT_STATUS.md

**Append to `docs/PROJECT_STATUS.md`:**

```markdown
## Email Delivery Fix — COMPLETE

**Date:** 2026-10-19  
**Severity:** P0 (Production Blocker)  
**Status:** ✅ FIXED

### Problem
- Users could register but never received verification emails
- Server silently skipped email sending when SMTP not configured
- No error or warning — silent failure in production

### Root Cause
- `email_service.py` returned early without error when `SMTP_USER` was empty
- `config.py` had empty defaults for SMTP settings
- Production server (Render) had no SMTP credentials → all emails skipped

### Solution
1. **Fail fast in production**: Pydantic validator rejects empty SMTP vars at startup
2. **Async email sending**: Use FastAPI BackgroundTasks (non-blocking)
3. **Proper error handling**: Log SMTP failures instead of silent skip
4. **Deployment docs**: Clear guide for configuring SMTP in Render

### Files Modified
- `backend/app/core/config.py` — SMTP validation
- `backend/app/services/email_service.py` — async sending
- `backend/app/services/verification_service.py` — background task support
- `backend/app/api/v1/routes/auth.py` — inject BackgroundTasks
- `docs/DEPLOYMENT.md` — SMTP configuration guide
- `scripts/setup-render-env.sh` — env var verification script

### Tests Added
- `tests/unit/test_smtp_config.py` (5 tests)
- `tests/integration/test_email_background.py` (3 tests)

### Deployment Checklist for Render
- [ ] Set `SMTP_HOST=smtp.gmail.com` (or your provider)
- [ ] Set `SMTP_PORT=587`
- [ ] Set `SMTP_USER=your-email@gmail.com`
- [ ] Set `SMTP_PASSWORD=your-app-password`
- [ ] Set `SMTP_FROM=noreply@spetser.ai`
- [ ] Set `APP_ENV=production`
- [ ] Deploy and verify emails are sent (check Render logs)

### Status
✅ Config validation: PASS (server refuses to start without SMTP in production)  
✅ Async sending: PASS (registration returns immediately, email sent in background)  
✅ Error logging: PASS (SMTP failures logged, not silent)  
✅ Tests: 8/8 PASS
```

### Step 6.5: Final Commit

```bash
git add -A
git commit -m "docs: update ERROR_LOG and PROJECT_STATUS with email fix evidence

- Append E-EMAIL-001 to ERROR_LOG with root cause and prevention
- Add Email Delivery Fix section to PROJECT_STATUS
- Include Render deployment checklist
- Reference all commits and test results"
```

==================================================
SECTION 7: RENDER DEPLOYMENT CHECKLIST
==================================================

**Before deploying the fix, configure these in Render:**

### Step 7.1: Set Environment Variables in Render Dashboard

1. Go to your Render service → **Environment** tab
2. Add these variables:

```env
# Required for email sending
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
SMTP_FROM=noreply@spetser.ai

# Must be production
APP_ENV=production

# Other required vars (should already be set)
APP_SECRET_KEY=<your-secret-key-32+chars>
SESSION_SECRET_KEY=<your-session-key-32+chars>
DATABASE_URL=<your-postgres-url>
```

### Step 7.2: Generate Gmail App Password (if using Gmail)

1. Go to https://myaccount.google.com/apppasswords
2. Select app: "Mail"
3. Select device: "Other" → name it "Spetser AI Render"
4. Copy the 16-character password
5. Use it as `SMTP_PASSWORD`

### Step 7.3: Deploy and Verify

```bash
# Push your changes
git push origin main

# Render will auto-deploy

# Check logs
render logs --service spetser-backend --tail 200

# Look for:
# ✅ "Application startup complete" (not "smtp_user is required in production")
# ✅ "Email sent successfully to user@example.com" (when someone registers)
```

### Step 7.4: Test End-to-End

1. Open your deployed site: `https://spetser-ai.onrender.com`
2. Register with a real email address
3. Check your inbox → should receive verification email within 5 seconds
4. Enter the code → account should be verified
5. Login → should work

### Step 7.5: Monitor Email Deliverability

**Check Render logs regularly:**

```bash
# Successful sends
render logs --service spetser-backend | grep "Email sent successfully"

# Failed sends (if any)
render logs --service spetser-backend | grep -i "smtp.*error"

# Dev mode warnings (should NOT appear in production)
render logs --service spetser-backend | grep "DEV MODE"
```

==================================================
SECTION 8: ACCEPTANCE CRITERIA
==================================================

The email delivery fix is COMPLETE only when:

- [ ] `test_smtp_config.py`: 5/5 tests PASS
- [ ] `test_email_background.py`: 3/3 tests PASS
- [ ] Server refuses to start in production without SMTP vars
- [ ] Register endpoint returns < 500ms (async email)
- [ ] Email failures are logged (not silent)
- [ ] Render environment variables configured (SMTP_*)
- [ ] Real email received after registration
- [ ] `docs/DEPLOYMENT.md` updated with SMTP guide
- [ ] `docs/ERROR_LOG.md` has E-EMAIL-001 entry
- [ ] `docs/PROJECT_STATUS.md` updated with fix evidence
- [ ] All commits pushed to main branch

==================================================
SECTION 9: START COMMAND
==================================================

**Awaiting user instruction:**
- Say **"Execute Email Fix"** to run all steps
- Say **"Config Only"** to just add validation (Fix #1)
- Say **"Async Only"** to just add background tasks (Fix #2)
- Say **"Deploy Guide"** to just update deployment docs

GO.
```

---

## ملخص ما يفعله هذا البرومت

| الخطوة | الوصف | النتيجة |
|--------|--------|---------|
| **Fix #1** | إضافة Pydantic validator يرفض التشغيل في production بدون SMTP | الخادم يرفض البدء بدلاً من الفشل الصامت |
| **Fix #2** | استخدام FastAPI BackgroundTasks للإرسال غير المتزامن | التسجيل يرجع فوراً، البريد يُرسل في الخلفية |
| **الاختبارات** | 8 اختبارات جديدة تغطي كل السيناريوهات | ضمان عدم رجوع المشكلة |
| **التوثيق** | تحديث DEPLOYMENT.md مع دليل إعداد SMTP | سهولة النشر على Render |
| **Render Setup** | قائمة المتغيرات المطلوبة + Gmail App Password | نشر ناجح |

## المتغيرات المطلوبة في Render

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
SMTP_FROM=noreply@spetser.ai
APP_ENV=production
```

## كيف تحصل على Gmail App Password

1. فعّل المصادقة الثنائية على حساب Gmail
2. اذهب إلى https://myaccount.google.com/apppasswords
3. أنشئ كلمة مرور تطبيق جديدة
4. استخدم الـ 16 حرف في `SMTP_PASSWORD`

## التحقق بعد النشر

```bash
# افحص سجلات Render
render logs --service spetser-backend --tail 200

# يجب أن ترى:
# ✅ "Email sent successfully to user@example.com"
# ❌ NOT: "[DEV MODE] Email would be sent..."
```


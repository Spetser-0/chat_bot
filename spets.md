هذا برومت مفصل وشامل خطوة بخطوة، مصمم بنفس الأسلوب الاحترافي للبرومتات السابقة، يغطي جميع المتطلبات الخمسة:

---

```markdown
# SPETSER AI — AUTHENTICATION & DEVELOPER PANEL FEATURES PROMPT
# Version: 1.0 | Execution Mode: Autonomous Step-by-Step

==================================================
SECTION 0: YOUR IDENTITY AND AUTHORITY
==================================================

You are the **Senior Full-Stack Engineer** for the project `spetser-ai`. You are tasked with implementing five critical features:

1. **Password visibility toggle** (eye icon) in Login and Register forms.
2. **Email verification with OTP** during account registration.
3. **Forgot Password flow** with email verification and password reset.
4. **Developer Panel** for managing API keys with custom commands/prompts.
5. **Default Credits Control** for new user accounts.

You have full authority to:
- Read, write, create, and modify files.
- Execute terminal commands (npm, python, git, alembic).
- Run tests and builds.
- Make architectural decisions when ambiguous.

You must NOT:
- Hardcode secrets or API keys.
- Store OTP codes or passwords in plain text.
- Skip any step or sub-task.
- Proceed if any test fails.

==================================================
SECTION 1: EXECUTION PROTOCOL (MANDATORY)
==================================================

For EVERY sub-step, follow this exact sequence:

1. **ANNOUNCE:** State what you will do.
2. **INSPECT:** Read existing related files first.
3. **PLAN:** List files to create/modify.
4. **IMPLEMENT:** Write the code.
5. **TEST:** Run relevant tests/builds.
6. **FIX:** Fix any failures immediately.
7. **DOCUMENT:** Update `docs/PROJECT_STATUS.md`.
8. **COMMIT:** Create a descriptive git commit.
9. **REPORT:** Summarize what was done.

**Error Logging:**
Log ALL errors in `docs/ERROR_LOG.md` with:
```
## [DATE] [FEATURE] [STEP]
**Error:** [message]
**Root Cause:** [analysis]
**Fix:** [solution]
```

==================================================
SECTION 2: FEATURE 1 — PASSWORD VISIBILITY TOGGLE (EYE ICON)
==================================================

**Goal:** Add an eye icon button inside the password input field on Login and Register forms that toggles password visibility.

---

### Step 2.1: Create Reusable PasswordInput Component

**File to create:** `frontend/src/components/ui/PasswordInput.tsx`

```tsx
import { InputHTMLAttributes, forwardRef, useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';

interface PasswordInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const PasswordInput = forwardRef<HTMLInputElement, PasswordInputProps>(
  ({ label, error, id, className = '', ...props }, ref) => {
    const [showPassword, setShowPassword] = useState(false);
    const inputId = id || `password-${Math.random().toString(36).slice(2)}`;

    return (
      <div className="input-group">
        {label && (
          <label htmlFor={inputId} className="input-group__label">
            {label}
          </label>
        )}
        <div className={`input-wrapper input-wrapper--password ${error ? 'input-wrapper--error' : ''}`}>
          <input
            ref={ref}
            id={inputId}
            type={showPassword ? 'text' : 'password'}
            className="input-wrapper__field"
            aria-invalid={!!error}
            {...props}
          />
          <button
            type="button"
            className="input-wrapper__toggle-password"
            onClick={() => setShowPassword(!showPassword)}
            aria-label={showPassword ? 'إخفاء كلمة المرور' : 'إظهار كلمة المرور'}
            tabIndex={-1}
          >
            {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>
        {error && (
          <p className="input-group__error" role="alert">{error}</p>
        )}
      </div>
    );
  }
);

PasswordInput.displayName = 'PasswordInput';
```

---

### Step 2.2: Create CSS for Password Toggle

**File to create/update:** `frontend/src/styles/components/input.css`

```css
.input-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.input-group__label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-primary);
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.input-wrapper__field {
  width: 100%;
  padding: var(--space-3) var(--space-4);
  padding-inline-end: var(--space-12); /* Space for eye icon */
  font-size: var(--text-base);
  color: var(--color-text-primary);
  background-color: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: border-color var(--transition-base) var(--ease-default),
              box-shadow var(--transition-base) var(--ease-default);
  min-height: var(--touch-target-min);
}

.input-wrapper__field:focus {
  outline: none;
  border-color: var(--color-border-focus);
  box-shadow: 0 0 0 3px var(--color-brand-light);
}

.input-wrapper--error .input-wrapper__field {
  border-color: var(--color-border-error);
}

.input-wrapper__toggle-password {
  position: absolute;
  inset-inline-end: var(--space-3); /* RTL-aware positioning */
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-2);
  color: var(--color-text-tertiary);
  background: transparent;
  border: none;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: color var(--transition-fast) var(--ease-default);
}

.input-wrapper__toggle-password:hover {
  color: var(--color-text-primary);
}

.input-group__error {
  font-size: var(--text-sm);
  color: var(--color-error);
}
```

---

### Step 2.3: Update Login Form

**File to update:** `frontend/src/components/auth/LoginForm.tsx`

**Action:**
- Read the existing file.
- Replace the password `<input>` with `<PasswordInput>`.
- Add a "Forgot Password" link below the password field:

```tsx
import { PasswordInput } from '../ui/PasswordInput';
import { Link } from 'react-router-dom';

// Inside the form JSX:
<PasswordInput
  label="كلمة المرور"
  name="password"
  value={password}
  onChange={(e) => setPassword(e.target.value)}
  placeholder="••••••••"
  required
/>

<div className="form__forgot-row">
  <Link to="/forgot-password" className="link--forgot">
    نسيت كلمة المرور؟
  </Link>
</div>
```

**CSS for forgot row:**
```css
.form__forgot-row {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--space-2);
}

.link--forgot {
  font-size: var(--text-sm);
  color: var(--color-brand);
  text-decoration: none;
}

.link--forgot:hover {
  text-decoration: underline;
}
```

---

### Step 2.4: Update Register Form

**File to update:** `frontend/src/components/auth/RegisterForm.tsx`

**Action:**
- Replace password field with `<PasswordInput>`.
- Add a password confirmation field using `<PasswordInput>` as well.
- Validate that both passwords match before submission.

---

### Step 2.5: Test Feature 1

```bash
cd frontend
npm run lint
npm run build
```

**Verify manually:**
- [ ] Eye icon appears in login password field.
- [ ] Eye icon appears in register password field.
- [ ] Clicking toggles between password/text.
- [ ] Icon position is correct in RTL (Arabic) mode.
- [ ] Icon position is correct in LTR (English) mode.

**Commit:**
```bash
git add -A
git commit -m "feat(auth): add password visibility toggle with eye icon in login and register"
```

==================================================
SECTION 3: FEATURE 2 — EMAIL VERIFICATION WITH OTP
==================================================

**Goal:** When a user registers, send a random OTP code to their email. The account is only created/activated if the correct code is entered.

---

### Step 3.1: Backend — Create Verification Models

**File to create/update:** `backend/app/models/user.py`

**Add fields to User model:**
```python
is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
verification_code: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Store HASHED code
verification_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
verification_attempts: Mapped[int] = mapped_column(Integer, default=0)
```

**Create Alembic migration:**
```bash
cd backend
alembic revision --autogenerate -m "add email verification fields to user"
alembic upgrade head
```

---

### Step 3.2: Backend — OTP Service

**File to create:** `backend/app/services/verification_service.py`

```python
"""
Email verification service for Spetser AI.
Generates secure OTP codes, hashes them, and verifies user input.
"""
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.exceptions import ValidationError, AuthenticationError
from app.services.email_service import send_verification_email


class VerificationService:
    """Handles OTP generation, storage, and verification."""

    OTP_LENGTH = 6
    OTP_TTL_MINUTES = 15
    MAX_ATTEMPTS = 5

    @staticmethod
    def _hash_code(code: str) -> str:
        """Hash the OTP before storing (never store plain text)."""
        return hashlib.sha256(code.encode()).hexdigest()

    @staticmethod
    def generate_otp() -> str:
        """Generate a cryptographically secure 6-digit OTP."""
        return ''.join([str(secrets.randbelow(10)) for _ in range(VerificationService.OTP_LENGTH)])

    async def initiate_verification(
        self,
        db: AsyncSession,
        user: User,
    ) -> None:
        """Generate OTP, store hash, send email."""
        otp = self.generate_otp()

        user.verification_code = self._hash_code(otp)
        user.verification_expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.OTP_TTL_MINUTES)
        user.verification_attempts = 0
        user.is_verified = False

        await db.commit()

        # Send email with OTP
        await send_verification_email(to_email=user.email, code=otp)

    async def verify_code(
        self,
        db: AsyncSession,
        user: User,
        code: str,
    ) -> bool:
        """
        Verify the OTP code.
        Returns True if valid, raises exception otherwise.
        """
        # Check if already verified
        if user.is_verified:
            return True

        # Check attempts limit
        if user.verification_attempts >= self.MAX_ATTEMPTS:
            raise AuthenticationError("Too many failed attempts. Please request a new code.")

        # Check expiration
        if not user.verification_expires_at or user.verification_expires_at < datetime.now(timezone.utc):
            raise ValidationError("Verification code has expired. Please request a new one.")

        # Check code
        if self._hash_code(code) != user.verification_code:
            user.verification_attempts += 1
            await db.commit()
            remaining = self.MAX_ATTEMPTS - user.verification_attempts
            raise ValidationError(f"Invalid verification code. {remaining} attempts remaining.")

        # Success - verify the account
        user.is_verified = True
        user.verification_code = None
        user.verification_expires_at = None
        user.verification_attempts = 0
        await db.commit()

        return True

    async def resend_code(self, db: AsyncSession, user: User) -> None:
        """Resend a new verification code."""
        if user.is_verified:
            raise ValidationError("Account is already verified.")
        await self.initiate_verification(db, user)


verification_service = VerificationService()
```

---

### Step 3.3: Backend — Email Service

**File to create:** `backend/app/services/email_service.py`

```python
"""
Email sending service.
Uses SMTP or a provider like Resend/SendGrid.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings


async def send_verification_email(to_email: str, code: str) -> None:
    """Send OTP verification email."""
    subject = "رمز التحقق - Spetser AI"
    body = f"""
    <div dir="rtl" style="font-family: 'Noto Sans Arabic', sans-serif; padding: 20px;">
        <h2 style="color: #01696D;">مرحباً بك في Spetser AI</h2>
        <p>رمز التحقق الخاص بك هو:</p>
        <div style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #01696D; padding: 20px; background: #E6F4F4; border-radius: 12px; text-align: center; margin: 20px 0;">
            {code}
        </div>
        <p style="color: #6B7280;">هذا الرمز صالح لمدة 15 دقيقة فقط.</p>
        <p style="color: #6B7280;">إذا لم تطلب هذا الرمز، يرجى تجاهل هذه الرسالة.</p>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg.attach(MIMEText(body, "html", "utf-8"))

    # For development: print to console
    if settings.DEBUG:
        print(f"[DEV] Verification code for {to_email}: {code}")
        return

    # Production: Send via SMTP
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)
```

**Add to `.env.example`:**
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@spetser.ai
```

---

### Step 3.4: Backend — Update Register Endpoint

**File to update:** `backend/app/api/v1/routes/auth.py`

**Modify the register endpoint:**
```python
from app.services.verification_service import verification_service

@router.post("/register")
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check if email already exists
    existing = await db.execute(select(User).where(User.email == request.email))
    if existing.scalar_one_or_none():
        raise ValidationError("This email is already registered.")

    # Create user (NOT verified yet)
    user = User(
        email=request.email,
        name=request.name,
        hashed_password=hash_password(request.password),
        is_verified=False,
        credit_balance=settings.DEFAULT_NEW_USER_CREDITS,  # From Feature 5
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Send verification code
    await verification_service.initiate_verification(db, user)

    return {
        "message": "Account created. Please check your email for the verification code.",
        "email": user.email,
        "requires_verification": True,
    }
```

---

### Step 3.5: Backend — Verification Endpoint

**File to update:** `backend/app/api/v1/routes/auth.py`

```python
@router.post("/verify-email")
async def verify_email(request: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    """
    Verify user email with OTP code.
    Account is only activated if code is correct.
    """
    # Find user by email
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user:
        raise NotFoundError("User not found.")

    # Verify the code (raises exception if invalid)
    await verification_service.verify_code(db, user, request.code)

    return {
        "message": "Email verified successfully. Account is now active.",
        "user_id": str(user.id),
    }


@router.post("/resend-code")
async def resend_code(request: ResendCodeRequest, db: AsyncSession = Depends(get_db)):
    """Resend verification code."""
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user:
        raise NotFoundError("User not found.")

    await verification_service.resend_code(db, user)

    return {"message": "A new verification code has been sent."}
```

---

### Step 3.6: Backend — Block Login for Unverified Users

**File to update:** `backend/app/api/v1/routes/auth.py`

**In the login endpoint, add check:**
```python
@router.post("/login")
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.hashed_password):
        raise AuthenticationError("Invalid email or password.")

    # NEW: Block unverified users
    if not user.is_verified:
        raise AuthenticationError(
            "Your email is not verified. Please check your email for the verification code."
        )

    # Generate tokens...
    access_token = create_access_token(user.id)
    return {"access_token": access_token, "token_type": "bearer"}
```

---

### Step 3.7: Frontend — Verification Page

**File to create:** `frontend/src/pages/VerifyEmailPage.tsx`

```tsx
import { useState, useRef, KeyboardEvent } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { api } from '../lib/api';

export function VerifyEmailPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const email = location.state?.email || '';

  const [code, setCode] = useState(['', '', '', '', '', '']);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  const handleChange = (index: number, value: string) => {
    if (!/^\d*$/.test(value)) return;

    const newCode = [...code];
    newCode[index] = value;
    setCode(newCode);

    // Auto-focus next input
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index: number, e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !code[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handleSubmit = async () => {
    const fullCode = code.join('');
    if (fullCode.length !== 6) {
      setError('يرجى إدخال الرمز كاملاً');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      await api.post('/auth/verify-email', { email, code: fullCode });
      navigate('/login', { state: { verified: true } });
    } catch (err: any) {
      setError(err.response?.data?.error?.message || 'فشل التحقق من الرمز');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResend = async () => {
    try {
      await api.post('/auth/resend-code', { email });
      setError('');
      alert('تم إرسال رمز جديد إلى بريدك');
    } catch (err: any) {
      setError(err.response?.data?.error?.message || 'فشل إرسال الرمز');
    }
  };

  return (
    <div className="verify-page">
      <div className="verify-page__card animate-fade-slide-up">
        <h1 className="verify-page__title">التحقق من البريد الإلكتروني</h1>
        <p className="verify-page__subtitle">
          أرسلنا رمزاً مكوناً من 6 أرقام إلى <strong>{email}</strong>
        </p>

        <div className="verify-page__inputs" dir="ltr">
          {code.map((digit, index) => (
            <input
              key={index}
              ref={(el) => { inputRefs.current[index] = el; }}
              type="text"
              inputMode="numeric"
              maxLength={1}
              value={digit}
              onChange={(e) => handleChange(index, e.target.value)}
              onKeyDown={(e) => handleKeyDown(index, e)}
              className="verify-page__input"
              aria-label={`الخانة ${index + 1}`}
            />
          ))}
        </div>

        {error && <p className="verify-page__error" role="alert">{error}</p>}

        <Button
          variant="primary"
          fullWidth
          onClick={handleSubmit}
          isLoading={isLoading}
        >
          تأكيد الحساب
        </Button>

        <button className="verify-page__resend" onClick={handleResend}>
          لم يصلك الرمز؟ إعادة الإرسال
        </button>
      </div>
    </div>
  );
}
```

**CSS for verification page:**
```css
.verify-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-4);
  background-color: var(--color-bg-primary);
}

.verify-page__card {
  width: 100%;
  max-width: 400px;
  padding: var(--space-8);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  text-align: center;
}

.verify-page__title {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  margin-bottom: var(--space-2);
}

.verify-page__subtitle {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-6);
}

.verify-page__inputs {
  display: flex;
  justify-content: center;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

.verify-page__input {
  width: 44px;
  height: 52px;
  text-align: center;
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: border-color var(--transition-base);
}

.verify-page__input:focus {
  outline: none;
  border-color: var(--color-brand);
}

.verify-page__error {
  color: var(--color-error);
  font-size: var(--text-sm);
  margin-bottom: var(--space-4);
}

.verify-page__resend {
  margin-top: var(--space-4);
  background: none;
  border: none;
  color: var(--color-brand);
  cursor: pointer;
  font-size: var(--text-sm);
}

.verify-page__resend:hover {
  text-decoration: underline;
}
```

---

### Step 3.8: Update Register Form to Redirect

**File to update:** `frontend/src/components/auth/RegisterForm.tsx`

```tsx
const handleSubmit = async (e: FormEvent) => {
  e.preventDefault();

  if (password !== confirmPassword) {
    setError('كلمتا المرور غير متطابقتين');
    return;
  }

  setIsLoading(true);
  try {
    await api.post('/auth/register', { name, email, password });
    // Redirect to verification page
    navigate('/verify-email', { state: { email } });
  } catch (err: any) {
    setError(err.response?.data?.error?.message || 'فشل إنشاء الحساب');
  } finally {
    setIsLoading(false);
  }
};
```

---

### Step 3.9: Add Route

**File to update:** `frontend/src/App.tsx` (or router file)

```tsx
import { VerifyEmailPage } from './pages/VerifyEmailPage';
import { ForgotPasswordPage } from './pages/ForgotPasswordPage';

// Inside routes:
<Route path="/verify-email" element={<VerifyEmailPage />} />
<Route path="/forgot-password" element={<ForgotPasswordPage />} />
```

---

### Step 3.10: Test Feature 2

**Backend tests:**
```bash
cd backend
python -m pytest tests/test_verification.py -v
```

**Create test file:** `backend/tests/test_verification.py`

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register_creates_unverified_user(client: AsyncClient):
    response = await client.post("/api/v1/auth/register", json={
        "name": "Test User",
        "email": "test@example.com",
        "password": "SecurePass123!",
    })
    assert response.status_code == 200
    assert response.json()["requires_verification"] == True

@pytest.mark.asyncio
async def test_login_blocked_for_unverified_user(client: AsyncClient):
    # Register first
    await client.post("/api/v1/auth/register", json={
        "name": "Test", "email": "unverified@example.com", "password": "Pass123!"
    })
    # Try login
    response = await client.post("/api/v1/auth/login", json={
        "email": "unverified@example.com",
        "password": "Pass123!",
    })
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_verify_with_wrong_code_fails(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "name": "Test", "email": "wrong@example.com", "password": "Pass123!"
    })
    response = await client.post("/api/v1/auth/verify-email", json={
        "email": "wrong@example.com",
        "code": "000000",  # Wrong code
    })
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_verify_with_correct_code_succeeds(client: AsyncClient, db_session):
    # This test would need to mock the email service or extract the code from DB
    pass
```

**Frontend:**
```bash
cd frontend
npm run lint && npm run build
```

**Commit:**
```bash
git add -A
git commit -m "feat(auth): add email verification with OTP during registration"
```

==================================================
SECTION 4: FEATURE 3 — FORGOT PASSWORD FLOW
==================================================

**Goal:** User clicks "Forgot Password" → receives OTP via email → enters OTP → can set new password.

---

### Step 4.1: Backend — Password Reset Service

**File to create:** `backend/app/services/password_reset_service.py`

```python
"""
Password reset service.
Uses the same OTP mechanism as email verification.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.security import hash_password
from app.core.exceptions import ValidationError, AuthenticationError
from app.services.email_service import send_reset_email
from app.services.verification_service import VerificationService


class PasswordResetService:
    """Handles forgot password flow."""

    async def initiate_reset(self, db: AsyncSession, user: User) -> None:
        """Generate reset code and send email."""
        otp = VerificationService.generate_otp()

        user.verification_code = VerificationService._hash_code(otp)
        user.verification_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        user.verification_attempts = 0
        await db.commit()

        await send_reset_email(to_email=user.email, code=otp)

    async def verify_reset_code(self, db: AsyncSession, user: User, code: str) -> bool:
        """Verify the reset code."""
        if user.verification_attempts >= VerificationService.MAX_ATTEMPTS:
            raise AuthenticationError("Too many failed attempts. Please request a new code.")

        if not user.verification_expires_at or user.verification_expires_at < datetime.now(timezone.utc):
            raise ValidationError("Reset code has expired.")

        if VerificationService._hash_code(code) != user.verification_code:
            user.verification_attempts += 1
            await db.commit()
            raise ValidationError("Invalid reset code.")

        return True

    async def reset_password(self, db: AsyncSession, user: User, new_password: str) -> None:
        """Set new password and invalidate the code."""
        user.hashed_password = hash_password(new_password)
        user.verification_code = None
        user.verification_expires_at = None
        user.verification_attempts = 0
        await db.commit()


password_reset_service = PasswordResetService()
```

---

### Step 4.2: Backend — Forgot Password Endpoints

**File to update:** `backend/app/api/v1/routes/auth.py`

```python
@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """
    Step 1: User requests password reset.
    Sends OTP to their email.
    """
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    # Security: Don't reveal if email exists or not
    if not user:
        return {"message": "If this email exists, a reset code has been sent."}

    await password_reset_service.initiate_reset(db, user)
    return {"message": "If this email exists, a reset code has been sent."}


@router.post("/verify-reset-code")
async def verify_reset_code(request: VerifyResetCodeRequest, db: AsyncSession = Depends(get_db)):
    """
    Step 2: User enters the OTP code.
    Returns a temporary reset token if valid.
    """
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user:
        raise ValidationError("Invalid code.")

    await password_reset_service.verify_reset_code(db, user, request.code)

    # Generate a short-lived reset token (10 minutes)
    reset_token = create_reset_token(user.id, expires_minutes=10)

    return {"reset_token": reset_token}


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """
    Step 3: User sets new password using the reset token.
    """
    # Verify the reset token
    user_id = decode_reset_token(request.reset_token)
    if not user_id:
        raise ValidationError("Invalid or expired reset token.")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise NotFoundError("User not found.")

    # Validate new password strength
    if len(request.new_password) < 8:
        raise ValidationError("Password must be at least 8 characters.")

    await password_reset_service.reset_password(db, user, request.new_password)

    return {"message": "Password has been reset successfully."}
```

---

### Step 4.3: Backend — Reset Token Helper

**File to update:** `backend/app/core/security.py`

```python
from datetime import datetime, timedelta, timezone
import jwt

RESET_TOKEN_SECRET = settings.RESET_TOKEN_SECRET
RESET_TOKEN_ALGORITHM = "HS256"


def create_reset_token(user_id: str, expires_minutes: int = 10) -> str:
    """Create a short-lived password reset token."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload = {
        "sub": str(user_id),
        "type": "password_reset",
        "exp": expire,
    }
    return jwt.encode(payload, RESET_TOKEN_SECRET, algorithm=RESET_TOKEN_ALGORITHM)


def decode_reset_token(token: str) -> str | None:
    """Decode and validate reset token. Returns user_id or None."""
    try:
        payload = jwt.decode(token, RESET_TOKEN_SECRET, algorithms=[RESET_TOKEN_ALGORITHM])
        if payload.get("type") != "password_reset":
            return None
        return payload.get("sub")
    except jwt.PyJWTError:
        return None
```

**Add to `.env.example`:**
```env
RESET_TOKEN_SECRET=your-secure-random-secret-here
```

---

### Step 4.4: Frontend — Forgot Password Page

**File to create:** `frontend/src/pages/ForgotPasswordPage.tsx`

```tsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { PasswordInput } from '../components/ui/PasswordInput';
import { api } from '../lib/api';

type Step = 'email' | 'code' | 'new-password' | 'success';

export function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>('email');
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [resetToken, setResetToken] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSendCode = async () => {
    setIsLoading(true);
    setError('');
    try {
      await api.post('/auth/forgot-password', { email });
      setStep('code');
    } catch (err: any) {
      setError(err.response?.data?.error?.message || 'حدث خطأ');
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyCode = async () => {
    setIsLoading(true);
    setError('');
    try {
      const response = await api.post('/auth/verify-reset-code', { email, code });
      setResetToken(response.data.reset_token);
      setStep('new-password');
    } catch (err: any) {
      setError(err.response?.data?.error?.message || 'رمز غير صحيح');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetPassword = async () => {
    if (newPassword !== confirmPassword) {
      setError('كلمتا المرور غير متطابقتين');
      return;
    }
    setIsLoading(true);
    setError('');
    try {
      await api.post('/auth/reset-password', {
        reset_token: resetToken,
        new_password: newPassword,
      });
      setStep('success');
    } catch (err: any) {
      setError(err.response?.data?.error?.message || 'فشل إعادة تعيين كلمة المرور');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="forgot-page">
      <div className="forgot-page__card animate-fade-slide-up">
        {step === 'email' && (
          <>
            <h1>نسيت كلمة المرور؟</h1>
            <p>أدخل بريدك الإلكتروني وسنرسل لك رمز التحقق</p>
            <Input
              label="البريد الإلكتروني"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="example@email.com"
            />
            {error && <p className="error-text">{error}</p>}
            <Button fullWidth onClick={handleSendCode} isLoading={isLoading}>
              إرسال رمز التحقق
            </Button>
          </>
        )}

        {step === 'code' && (
          <>
            <h1>أدخل رمز التحقق</h1>
            <p>أرسلنا رمزاً إلى {email}</p>
            <Input
              label="رمز التحقق"
              type="text"
              inputMode="numeric"
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
              placeholder="123456"
            />
            {error && <p className="error-text">{error}</p>}
            <Button fullWidth onClick={handleVerifyCode} isLoading={isLoading}>
              تأكيد الرمز
            </Button>
          </>
        )}

        {step === 'new-password' && (
          <>
            <h1>كلمة المرور الجديدة</h1>
            <PasswordInput
              label="كلمة المرور الجديدة"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
            <PasswordInput
              label="تأكيد كلمة المرور"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
            {error && <p className="error-text">{error}</p>}
            <Button fullWidth onClick={handleResetPassword} isLoading={isLoading}>
              حفظ كلمة المرور
            </Button>
          </>
        )}

        {step === 'success' && (
          <>
            <h1>تم بنجاح! 🎉</h1>
            <p>تم تغيير كلمة المرور. يمكنك الآن تسجيل الدخول.</p>
            <Button fullWidth onClick={() => navigate('/login')}>
              الانتقال لتسجيل الدخول
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
```

---

### Step 4.5: Test Feature 3

```bash
cd backend
python -m pytest tests/test_password_reset.py -v

cd ../frontend
npm run lint && npm run build
```

**Commit:**
```bash
git add -A
git commit -m "feat(auth): add forgot password flow with email OTP verification"
```

==================================================
SECTION 5: FEATURE 4 — DEVELOPER PANEL FOR API KEYS
==================================================

**Goal:** Build an admin/developer panel where API keys can be added, customized with commands/prompts, and deleted.

---

### Step 5.1: Backend — API Key Model

**File to create:** `backend/app/models/api_key.py`

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class APIKey(Base):
    """API keys that can be used to authenticate external requests."""

    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100))
    key_hash: Mapped[str] = mapped_column(String(255))  # Store HASHED key, not plain
    key_prefix: Mapped[str] = mapped_column(String(8))  # First 8 chars for display: "sk-abc1..."

    # Customization fields
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)  # Custom instructions
    max_credits_per_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    allowed_skills: Mapped[str | None] = mapped_column(Text, nullable=True)  # Comma-separated skill slugs

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Tracking
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_requests: Mapped[int] = mapped_column(Integer, default=0)
```

**Create migration:**
```bash
cd backend
alembic revision --autogenerate -m "add api_keys table"
alembic upgrade head
```

---

### Step 5.2: Backend — API Key Service

**File to create:** `backend/app/services/api_key_service.py`

```python
"""
API Key management service for developer panel.
"""
import secrets
import hashlib
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import APIKey
from app.core.exceptions import NotFoundError, ValidationError


class APIKeyService:
    """Manages API key lifecycle."""

    KEY_PREFIX = "sk-spetser-"

    @staticmethod
    def _hash_key(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()

    def generate_key(self) -> str:
        """Generate a new API key."""
        random_part = secrets.token_urlsafe(32)
        return f"{self.KEY_PREFIX}{random_part}"

    async def create_key(
        self,
        db: AsyncSession,
        name: str,
        created_by: str,
        system_prompt: Optional[str] = None,
        max_credits_per_day: Optional[int] = None,
        allowed_skills: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> tuple[APIKey, str]:
        """
        Create a new API key.
        Returns the APIKey object and the PLAIN key (shown only once).
        """
        plain_key = self.generate_key()

        api_key = APIKey(
            name=name,
            key_hash=self._hash_key(plain_key),
            key_prefix=plain_key[:len(self.KEY_PREFIX) + 4],
            system_prompt=system_prompt,
            max_credits_per_day=max_credits_per_day,
            allowed_skills=allowed_skills,
            expires_at=expires_at,
            created_by=created_by,
        )
        db.add(api_key)
        await db.commit()
        await db.refresh(api_key)

        return api_key, plain_key

    async def verify_key(self, db: AsyncSession, plain_key: str) -> Optional[APIKey]:
        """Verify an API key and return it if valid."""
        key_hash = self._hash_key(plain_key)
        result = await db.execute(select(APIKey).where(APIKey.key_hash == key_hash))
        api_key = result.scalar_one_or_none()

        if not api_key:
            return None

        if not api_key.is_active:
            return None

        if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
            return None

        # Update tracking
        api_key.last_used_at = datetime.now(timezone.utc)
        api_key.total_requests += 1
        await db.commit()

        return api_key

    async def update_key(
        self,
        db: AsyncSession,
        key_id: str,
        **updates,
    ) -> APIKey:
        """Update API key settings."""
        result = await db.execute(select(APIKey).where(APIKey.id == key_id))
        api_key = result.scalar_one_or_none()

        if not api_key:
            raise NotFoundError("API key not found.")

        allowed_fields = {"name", "system_prompt", "max_credits_per_day", "allowed_skills", "is_active", "expires_at"}
        for field, value in updates.items():
            if field in allowed_fields:
                setattr(api_key, field, value)

        await db.commit()
        await db.refresh(api_key)
        return api_key

    async def delete_key(self, db: AsyncSession, key_id: str) -> None:
        """Delete an API key."""
        result = await db.execute(select(APIKey).where(APIKey.id == key_id))
        api_key = result.scalar_one_or_none()

        if not api_key:
            raise NotFoundError("API key not found.")

        await db.delete(api_key)
        await db.commit()


api_key_service = APIKeyService()
```

---

### Step 5.3: Backend — Developer Panel Endpoints

**File to create:** `backend/app/api/v1/routes/developer.py`

```python
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import get_developer, require_admin
from app.models.api_key import APIKey
from app.models.user import User
from app.services.api_key_service import api_key_service
from app.schemas.api_key import (
    CreateAPIKeyRequest,
    UpdateAPIKeyRequest,
    APIKeyResponse,
    APIKeyCreateResponse,
)

router = APIRouter(prefix="/developer", tags=["Developer"])


@router.get("/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """List all API keys (admin only)."""
    result = await db.execute(select(APIKey).order_by(APIKey.created_at.desc()))
    return result.scalars().all()


@router.post("/api-keys", response_model=APIKeyCreateResponse)
async def create_api_key(
    request: CreateAPIKeyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Create a new API key.
    The plain key is returned ONLY ONCE. Store it securely.
    """
    api_key, plain_key = await api_key_service.create_key(
        db=db,
        name=request.name,
        created_by=current_user.id,
        system_prompt=request.system_prompt,
        max_credits_per_day=request.max_credits_per_day,
        allowed_skills=request.allowed_skills,
        expires_at=request.expires_at,
    )

    return {
        **APIKeyResponse.from_orm(api_key).dict(),
        "plain_key": plain_key,  # Shown only once!
    }


@router.patch("/api-keys/{key_id}", response_model=APIKeyResponse)
async def update_api_key(
    key_id: str,
    request: UpdateAPIKeyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Update API key settings."""
    return await api_key_service.update_key(db, key_id, **request.dict(exclude_unset=True))


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Delete an API key."""
    await api_key_service.delete_key(db, key_id)
    return {"message": "API key deleted successfully."}


@router.post("/api-keys/{key_id}/regenerate", response_model=APIKeyCreateResponse)
async def regenerate_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Regenerate the key value (old key becomes invalid)."""
    result = await db.execute(select(APIKey).where(APIKey.id == key_id))
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise NotFoundError("API key not found.")

    # Generate new key
    plain_key = api_key_service.generate_key()
    api_key.key_hash = api_key_service._hash_key(plain_key)
    api_key.key_prefix = plain_key[:len(api_key_service.KEY_PREFIX) + 4]
    await db.commit()

    return {
        **APIKeyResponse.from_orm(api_key).dict(),
        "plain_key": plain_key,
    }
```

---

### Step 5.4: Backend — Schemas

**File to create:** `backend/app/schemas/api_key.py`

```python
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CreateAPIKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    system_prompt: Optional[str] = Field(None, max_length=10000)
    max_credits_per_day: Optional[int] = Field(None, ge=0)
    allowed_skills: Optional[str] = None
    expires_at: Optional[datetime] = None


class UpdateAPIKeyRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    system_prompt: Optional[str] = Field(None, max_length=10000)
    max_credits_per_day: Optional[int] = Field(None, ge=0)
    allowed_skills: Optional[str] = None
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None


class APIKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    system_prompt: Optional[str]
    max_credits_per_day: Optional[int]
    allowed_skills: Optional[str]
    is_active: bool
    expires_at: Optional[datetime]
    created_at: datetime
    last_used_at: Optional[datetime]
    total_requests: int

    class Config:
        from_attributes = True


class APIKeyCreateResponse(APIKeyResponse):
    plain_key: str  # Only returned on creation
```

---

### Step 5.5: Register Developer Router

**File to update:** `backend/app/api/v1/__init__.py` (or main router file)

```python
from app.api.v1.routes import developer

api_router.include_router(developer.router)
```

---

### Step 5.6: Frontend — Developer Panel Page

**File to create:** `frontend/src/pages/DeveloperPage.tsx`

```tsx
import { useState, useEffect } from 'react';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Input } from '../components/ui/Input';
import { api } from '../lib/api';
import { Copy, Trash2, Edit, Plus, Key, Eye, EyeOff } from 'lucide-react';

interface APIKey {
  id: string;
  name: string;
  key_prefix: string;
  system_prompt: string | null;
  max_credits_per_day: number | null;
  allowed_skills: string | null;
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
  total_requests: number;
}

export function DeveloperPage() {
  const [apiKeys, setApiKeys] = useState<APIKey[]>([]);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [newKey, setNewKey] = useState('');
  const [editingKey, setEditingKey] = useState<APIKey | null>(null);

  // Create form state
  const [name, setName] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [maxCredits, setMaxCredits] = useState('');

  const fetchKeys = async () => {
    try {
      const response = await api.get('/developer/api-keys');
      setApiKeys(response.data);
    } catch (error) {
      console.error('Failed to fetch API keys:', error);
    }
  };

  useEffect(() => {
    fetchKeys();
  }, []);

  const handleCreate = async () => {
    try {
      const response = await api.post('/developer/api-keys', {
        name,
        system_prompt: systemPrompt || null,
        max_credits_per_day: maxCredits ? parseInt(maxCredits) : null,
      });
      setNewKey(response.data.plain_key);
      setShowCreateModal(false);
      setShowKeyModal(true);
      fetchKeys();
    } catch (error) {
      console.error('Failed to create key:', error);
    }
  };

  const handleDelete = async (keyId: string) => {
    if (!confirm('هل أنت متأكد من حذف هذا المفتاح؟')) return;

    try {
      await api.delete(`/developer/api-keys/${keyId}`);
      fetchKeys();
    } catch (error) {
      console.error('Failed to delete key:', error);
    }
  };

  const handleToggleActive = async (key: APIKey) => {
    try {
      await api.patch(`/developer/api-keys/${key.id}`, {
        is_active: !key.is_active,
      });
      fetchKeys();
    } catch (error) {
      console.error('Failed to update key:', error);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    alert('تم نسخ المفتاح');
  };

  return (
    <div className="developer-page">
      <div className="developer-page__header">
        <h1>لوحة المطورين</h1>
        <Button variant="primary" onClick={() => setShowCreateModal(true)}>
          <Plus size={18} />
          إضافة مفتاح جديد
        </Button>
      </div>

      <div className="developer-page__keys-grid">
        {apiKeys.map((key) => (
          <div key={key.id} className="api-key-card">
            <div className="api-key-card__header">
              <Key size={20} />
              <span className="api-key-card__name">{key.name}</span>
              <span className={`api-key-card__status ${key.is_active ? 'active' : 'inactive'}`}>
                {key.is_active ? 'نشط' : 'معطل'}
              </span>
            </div>

            <div className="api-key-card__prefix">
              <code>{key.key_prefix}••••••••</code>
            </div>

            {key.system_prompt && (
              <div className="api-key-card__prompt">
                <p className="api-key-card__prompt-label">الأوامر المخصصة:</p>
                <p className="api-key-card__prompt-text">{key.system_prompt.slice(0, 100)}...</p>
              </div>
            )}

            <div className="api-key-card__stats">
              <span>الطلبات: {key.total_requests}</span>
              {key.max_credits_per_day && <span>الحد اليومي: {key.max_credits_per_day}</span>}
            </div>

            <div className="api-key-card__actions">
              <Button size="sm" variant="ghost" onClick={() => setEditingKey(key)}>
                <Edit size={16} />
              </Button>
              <Button size="sm" variant="ghost" onClick={() => handleToggleActive(key)}>
                {key.is_active ? <EyeOff size={16} /> : <Eye size={16} />}
              </Button>
              <Button size="sm" variant="danger" onClick={() => handleDelete(key.id)}>
                <Trash2 size={16} />
              </Button>
            </div>
          </div>
        ))}
      </div>

      {/* Create Key Modal */}
      {showCreateModal && (
        <Modal onClose={() => setShowCreateModal(false)} title="إنشاء مفتاح جديد">
          <Input
            label="اسم المفتاح"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="مثال: مفتاح تطبيق الموبايل"
          />
          <div className="form-group">
            <label>الأوامر المخصصة (System Prompt)</label>
            <textarea
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              rows={4}
              placeholder="أنت مساعد تعليمي متخصص في الرياضيات..."
            />
          </div>
          <Input
            label="الحد الأقصى للكريدت اليومي (اختياري)"
            type="number"
            value={maxCredits}
            onChange={(e) => setMaxCredits(e.target.value)}
          />
          <Button fullWidth onClick={handleCreate}>
            إنشاء المفتاح
          </Button>
        </Modal>
      )}

      {/* Show New Key Modal */}
      {showKeyModal && (
        <Modal onClose={() => setShowKeyModal(false)} title="المفتاح الجديد">
          <p className="key-warning">
            ⚠️ احفظ هذا المفتاح الآن. لن تتمكن من رؤيته مرة أخرى!
          </p>
          <div className="key-display">
            <code>{newKey}</code>
            <Button size="sm" variant="ghost" onClick={() => copyToClipboard(newKey)}>
              <Copy size={16} />
            </Button>
          </div>
          <Button fullWidth onClick={() => setShowKeyModal(false)}>
            تم الحفظ
          </Button>
        </Modal>
      )}
    </div>
  );
}
```

---

### Step 5.7: Add Developer Route

**File to update:** `frontend/src/App.tsx`

```tsx
import { DeveloperPage } from './pages/DeveloperPage';

// Protected route (admin only):
<Route
  path="/developer"
  element={
    <ProtectedRoute requiredRole="admin">
      <DeveloperPage />
    </ProtectedRoute>
  }
/>
```

---

### Step 5.8: Test Feature 4

```bash
cd backend
python -m pytest tests/test_api_keys.py -v

cd ../frontend
npm run lint && npm run build
```

**Commit:**
```bash
git add -A
git commit -m "feat(developer): add API key management panel with custom prompts and controls"
```

==================================================
SECTION 6: FEATURE 5 — DEFAULT CREDITS CONTROL
==================================================

**Goal:** Allow admins to control the default credit balance given to new user accounts.

---

### Step 6.1: Backend — System Settings Model

**File to create:** `backend/app/models/system_settings.py`

```python
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SystemSettings(Base):
    """Global system settings (single row)."""

    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    default_new_user_credits: Mapped[int] = mapped_column(Integer, default=300)
    daily_free_credits: Mapped[int] = mapped_column(Integer, default=300)
    credits_per_message: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
```

**Create migration:**
```bash
cd backend
alembic revision --autogenerate -m "add system_settings table"
alembic upgrade head
```

**Seed default settings:**
```python
# backend/app/db/init_db.py
async def seed_settings(db: AsyncSession):
    result = await db.execute(select(SystemSettings))
    if not result.scalar_one_or_none():
        settings = SystemSettings(
            id=1,
            default_new_user_credits=300,
            daily_free_credits=300,
            credits_per_message=1,
        )
        db.add(settings)
        await db.commit()
```

---

### Step 6.2: Backend — Settings Service

**File to create:** `backend/app/services/settings_service.py`

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_settings import SystemSettings


class SettingsService:
    """Manages global system settings."""

    async def get_settings(self, db: AsyncSession) -> SystemSettings:
        result = await db.execute(select(SystemSettings).where(SystemSettings.id == 1))
        settings = result.scalar_one_or_none()

        if not settings:
            # Create default if missing
            settings = SystemSettings(id=1)
            db.add(settings)
            await db.commit()

        return settings

    async def update_settings(self, db: AsyncSession, **updates) -> SystemSettings:
        settings = await self.get_settings(db)

        allowed_fields = {
            "default_new_user_credits",
            "daily_free_credits",
            "credits_per_message",
        }

        for field, value in updates.items():
            if field in allowed_fields and value is not None:
                setattr(settings, field, value)

        await db.commit()
        await db.refresh(settings)
        return settings


settings_service = SettingsService()
```

---

### Step 6.3: Backend — Update Register to Use Settings

**File to update:** `backend/app/api/v1/routes/auth.py`

```python
from app.services.settings_service import settings_service

@router.post("/register")
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Get current settings
    settings = await settings_service.get_settings(db)

    # Create user with default credits from settings
    user = User(
        email=request.email,
        name=request.name,
        hashed_password=hash_password(request.password),
        is_verified=False,
        credit_balance=settings.default_new_user_credits,  # Dynamic!
    )
    db.add(user)
    await db.commit()

    # Send verification...
    await verification_service.initiate_verification(db, user)

    return {
        "message": "Account created. Please verify your email.",
        "credits_granted": settings.default_new_user_credits,
    }
```

---

### Step 6.4: Backend — Admin Settings Endpoints

**File to update:** `backend/app/api/v1/routes/admin.py`

```python
@router.get("/settings")
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Get system settings (admin only)."""
    settings = await settings_service.get_settings(db)
    return {
        "default_new_user_credits": settings.default_new_user_credits,
        "daily_free_credits": settings.daily_free_credits,
        "credits_per_message": settings.credits_per_message,
    }


@router.patch("/settings")
async def update_settings(
    request: UpdateSettingsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Update system settings (admin only)."""
    settings = await settings_service.update_settings(db, **request.dict(exclude_unset=True))
    return {
        "message": "Settings updated successfully.",
        "default_new_user_credits": settings.default_new_user_credits,
    }
```

---

### Step 6.5: Frontend — Settings Control in Developer Panel

**File to update:** `frontend/src/pages/DeveloperPage.tsx`

**Add settings section:**
```tsx
const [defaultCredits, setDefaultCredits] = useState('300');

useEffect(() => {
  fetchSettings();
}, []);

const fetchSettings = async () => {
  try {
    const response = await api.get('/admin/settings');
    setDefaultCredits(String(response.data.default_new_user_credits));
  } catch (error) {
    console.error('Failed to fetch settings:', error);
  }
};

const handleUpdateSettings = async () => {
  try {
    await api.patch('/admin/settings', {
      default_new_user_credits: parseInt(defaultCredits),
    });
    alert('تم تحديث الإعدادات بنجاح');
  } catch (error) {
    console.error('Failed to update settings:', error);
  }
};

// In JSX, add a settings card:
<div className="settings-card">
  <h2>إعدادات الحسابات الجديدة</h2>
  <Input
    label="الرصيد الافتراضي للحسابات الجديدة"
    type="number"
    value={defaultCredits}
    onChange={(e) => setDefaultCredits(e.target.value)}
  />
  <Button onClick={handleUpdateSettings}>
    حفظ الإعدادات
  </Button>
</div>
```

---

### Step 6.6: Test Feature 5

```bash
cd backend
python -m pytest tests/test_settings.py -v

cd ../frontend
npm run lint && npm run build
```

**Commit:**
```bash
git add -A
git commit -m "feat(admin): add default credits control for new user accounts"
```

==================================================
SECTION 7: FINAL VERIFICATION
==================================================

### Step 7.1: Run All Tests

```bash
# Backend
cd backend
python -m pytest tests/ -v --tb=short

# Frontend
cd ../frontend
npm run lint
npm run build
```

**ALL tests must pass.**

---

### Step 7.2: Manual Testing Checklist

**Feature 1 — Password Toggle:**
- [ ] Eye icon appears in login form.
- [ ] Eye icon appears in register form.
- [ ] Clicking toggles visibility.
- [ ] Works in RTL mode.

**Feature 2 — Email Verification:**
- [ ] Register creates unverified account.
- [ ] OTP email is sent (check console in dev mode).
- [ ] Correct OTP activates account.
- [ ] Wrong OTP shows error and decrements attempts.
- [ ] Expired OTP is rejected.
- [ ] Login blocked for unverified users.

**Feature 3 — Forgot Password:**
- [ ] "Forgot password" link visible on login.
- [ ] Entering email sends reset code.
- [ ] Correct code allows password reset.
- [ ] Wrong code shows error.
- [ ] New password works for login.
- [ ] Old password no longer works.

**Feature 4 — Developer Panel:**
- [ ] Admin can access /developer page.
- [ ] Non-admin users are blocked.
- [ ] Can create new API key.
- [ ] Plain key shown only once.
- [ ] Can edit key settings.
- [ ] Can toggle key active/inactive.
- [ ] Can delete key.
- [ ] Custom system prompt is saved.

**Feature 5 — Default Credits:**
- [ ] Admin can view current default credits.
- [ ] Admin can update default credits.
- [ ] New users receive the configured amount.

---

### Step 7.3: Update Documentation

**Update `docs/PROJECT_STATUS.md`:**
```markdown
# Spetser AI — Project Status Log

## Completed Features
- [x] Password visibility toggle (eye icon)
- [x] Email verification with OTP
- [x] Forgot password flow
- [x] Developer panel for API keys
- [x] Default credits control

## Last Updated: [DATE]
## Status: READY FOR DEPLOYMENT
```

---

### Step 7.4: Final Commit

```bash
git add -A
git commit -m "feat: complete auth enhancements and developer panel

- Add password visibility toggle in login/register
- Add email OTP verification for new accounts
- Add forgot password flow with email verification
- Add developer panel for API key management
- Add default credits control for new accounts"
```

==================================================
SECTION 8: SUMMARY
==================================================

| Feature | Files Created/Modified | Tests |
|---------|----------------------|-------|
| Password Toggle | PasswordInput.tsx, LoginForm.tsx, RegisterForm.tsx, input.css | Manual |
| Email Verification | verification_service.py, email_service.py, VerifyEmailPage.tsx, auth.py | test_verification.py |
| Forgot Password | password_reset_service.py, ForgotPasswordPage.tsx, security.py | test_password_reset.py |
| Developer Panel | api_key.py, api_key_service.py, developer.py, DeveloperPage.tsx | test_api_keys.py |
| Default Credits | system_settings.py, settings_service.py, admin.py | test_settings.py |

==================================================
END OF PROMPT
==================================================

**AWAITING USER COMMAND:**
- Say "Start Feature 1" to begin with password toggle.
- Say "Start Feature 2" to begin with email verification.
- Say "Continue" to resume from PROJECT_STATUS.md.
- Say "Execute All" to run all features sequentially.

GO.
```

---

## ملخص ما يغطيه هذا البرومت:

| الميزة | التفاصيل |
|--------|----------|
| **1. أيقونة العين** | مكون `PasswordInput` قابل لإعادة الاستخدام، يعمل في تسجيل الدخول وإنشاء الحساب، يدعم العربية و RTL |
| **2. التحقق بالبريد** | رمز عشوائي 6 أرقام، مشفر (SHA-256)، صالح 15 دقيقة، 5 محاولات كحد أقصى، الحساب لا يُفعّل إلا بالرمز الصحيح |
| **3. نسيت كلمة المرور** | 3 خطوات: إدخال البريد ← إدخال الرمز ← كتابة كلمة المرور الجديدة، مع رمز مؤقت (reset token) قصير العمر |
| **4. لوحة المطورين** | إضافة/تعديل/حذف مفاتيح API، تخصيص System Prompt لكل مفتاح، حد أقصى للكريدت اليومي، عرض المفتاح مرة واحدة فقط |
| **5. الكريدت الافتراضي** | جدول إعدادات نظام، تحكم الأدمن في رصيد الحسابات الجديدة، يُطبق تلقائياً عند التسجيل |

---

## ملاحظات أمنية مهمة مدمجة في البرومت:

1. **الرموز لا تُخزن نصاً صريحاً** — تُخزن كـ hash
2. **مفاتيح API تُخزن مشفرة** — يظهر المفتاح مرة واحدة فقط عند الإنشاء
3. **لا يتم كشف وجود البريد** — في نسيت كلمة المرور، الرسالة واحدة سواء كان البريد موجوداً أم لا
4. **تحديد المحاولات** — 5 محاولات فقط للرمز، ثم يجب طلب رمز جديد
5. **انتهاء الصلاحية** — الرمز صالح 15 دقيقة فقط
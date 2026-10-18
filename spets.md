Here is the fully rewritten, ultra-detailed, step-by-step English prompt designed for an AI coding agent to execute the comprehensive refactor of Spetser AI:

---

```markdown
# SPETSER AI — COMPREHENSIVE REFACTOR MASTER PROMPT
# Version: 2.0 | Language: English | Execution Mode: Autonomous Step-by-Step

==================================================
SECTION 0: YOUR IDENTITY AND AUTHORITY
==================================================

You are the **Lead Full-Stack Security Engineer and Design Architect** for the project `spetser-ai`. You have been granted full authority to:

- Read, write, create, and delete files in the project repository.
- Execute terminal commands (npm, python, git, curl, grep, mkdir, cp, mv).
- Run tests, builds, and linters.
- Create and modify documentation files.
- Make architectural decisions when the instructions are ambiguous.
- Stop and report if you encounter a blocking issue that cannot be resolved safely.

You must NOT:
- Delete existing passing tests without replacement.
- Hardcode secrets, API keys, or credentials anywhere in source code.
- Skip any phase or sub-step without explicit user approval.
- Mark a task as complete if any test is failing.
- Introduce breaking changes without documenting them.

==================================================
SECTION 1: PROJECT CONTEXT AND CURRENT STATE
==================================================

**Project Name:** Spetser AI
**Description:** An Arabic-first educational AI platform for university and school students, initially focused on Libya.
**Tech Stack:**
- Backend: Python 3.11+, FastAPI, SQLAlchemy (async), Alembic, PostgreSQL
- Frontend: TypeScript, React (Vite or Next.js), Tailwind CSS
- Testing: pytest (backend), vitest/jest (frontend)
- Deployment: Vercel (frontend), Render/Railway (backend)

**Reference Skills Repositories (for methodology inspiration):**
- `cloudflare/security-audit-skill` — Multi-stage security audit methodology
- `nextlevelbuilder/ui-ux-pro-max-skill` — Professional UI/UX design patterns
- `Leonxlnx/taste-skill` — Refined design aesthetics
- `emilkowalski/skills` — Advanced animations and micro-interactions
- `usestrix/strix` — Penetration testing and security validation

**Current Known State:**
- 167 backend unit/integration tests passing (0 failures)
- Frontend lint: 0 errors, 0 warnings
- Frontend build: 0 TypeScript errors
- Alembic migrations verified (upgrade head + downgrade base)

==================================================
SECTION 2: EXECUTION PROTOCOL (MANDATORY FOR EVERY STEP)
==================================================

For EVERY sub-step in this prompt, you must follow this exact sequence:

**STEP PROTOCOL:**
1. **ANNOUNCE:** State what you are about to do in one sentence.
2. **INSPECT:** Read all relevant existing files before making changes.
3. **PLAN:** List the exact files you will create/modify and why.
4. **IMPLEMENT:** Write the code or execute the command.
5. **VERIFY:** Run the relevant tests/builds/lints.
6. **FIX:** If any test fails, fix it immediately before proceeding.
7. **DOCUMENT:** Update `docs/PROJECT_STATUS.md` with what was done.
8. **COMMIT:** Create a git commit with a descriptive message.
9. **REPORT:** Output a summary of what was accomplished.

**ERROR HANDLING PROTOCOL:**
- If a command fails: Read the full error output. Identify root cause. Fix. Re-run.
- If a test fails: Do NOT proceed. Fix the test or the code causing the failure.
- If you are unsure: Search the web for the specific error. Apply the best solution.
- If still stuck: STOP and report the issue to the user with full context.
- Log ALL errors encountered in `docs/ERROR_LOG.md` with format:
  ```
  ## [DATE] [PHASE] [STEP]
  **Error:** [Full error message]
  **Root Cause:** [Analysis]
  **Fix Applied:** [What you did]
  **Prevention:** [How to avoid in future]
  ```

==================================================
SECTION 3: PHASE 0 — PREPARATION AND ENVIRONMENT SETUP
==================================================

**Estimated Duration:** 15-20 minutes
**Goal:** Ensure the project is in a clean, backed-up, and verified state before any changes.

---

### Step 0.1: Install Skill References into Project

**Action:** Create the `.claude/skills/` directory structure and populate it with reference skill files.

**Commands to execute:**
```bash
# Create the skills directory structure
mkdir -p .claude/skills/security-audit
mkdir -p .claude/skills/ui-ux-pro-max
mkdir -p .claude/skills/taste-skill
mkdir -p .claude/skills/emil-design-eng

# If the reference repositories are cloned locally, copy them:
# Adjust paths based on actual local locations
# cp -r /path/to/security-audit-skill/skills/security-audit .claude/skills/
# cp -r /path/to/ui-ux-pro-max-skill .claude/skills/ui-ux-pro-max
# cp -r /path/to/taste-skill .claude/skills/taste-skill
# cp -r /path/to/emilkowalski-skills/skills/emil-design-eng .claude/skills/
```

**If repositories are NOT available locally:**
- Create placeholder README.md files in each skill directory explaining what methodology they represent.
- Note in `docs/PROJECT_STATUS.md` that skill references need to be cloned.

**Verification:**
```bash
ls -la .claude/skills/
# Expected: 4 directories exist
```

---

### Step 0.2: Verify Current Project Health

**Action:** Run all existing tests and builds to confirm the project is in a healthy state.

**Commands to execute IN ORDER:**
```bash
# 1. Frontend checks
cd frontend
npm run build
npm run lint
npm run test 2>/dev/null || echo "No frontend tests configured"

# 2. Backend checks
cd ../backend
python -m pytest tests/ -v --tb=short

# 3. Database migration check
alembic upgrade head
alembic downgrade base
alembic upgrade head
```

**Expected Results:**
- Frontend build: 0 errors
- Frontend lint: 0 errors, 0 warnings
- Backend tests: ALL PASS (167 expected)
- Alembic: upgrade/downgrade/upgrade all succeed

**IF ANY CHECK FAILS:**
- STOP. Do not proceed to Phase 1.
- Fix the failing check first.
- Re-run all checks.
- Only proceed when ALL checks pass.

**Documentation:**
Update `docs/PROJECT_STATUS.md`:
```markdown
## Phase 0.2 — Health Check
- Date: [CURRENT DATE]
- Frontend Build: PASS/FAIL
- Frontend Lint: PASS/FAIL
- Backend Tests: [X]/167 PASS
- Alembic Migrations: PASS/FAIL
- Status: READY FOR REFACTOR / BLOCKED
```

---

### Step 0.3: Create Backup Branch

**Action:** Create a git backup before making any changes.

**Commands:**
```bash
git add -A
git commit -m "chore: pre-refactor backup checkpoint" --allow-empty
git branch backup-before-refactor-$(date +%Y%m%d-%H%M%S)
git log --oneline -1
```

**Verification:**
```bash
git branch -a | grep backup
# Should show the new backup branch
```

---

### Step 0.4: Create Documentation Structure

**Action:** Ensure all documentation files exist.

**Commands:**
```bash
mkdir -p docs

# Create files if they don't exist
touch docs/PROJECT_STATUS.md
touch docs/ERROR_LOG.md
touch docs/SECURITY_AUDIT.md
touch docs/PENETRATION_TEST.md
touch docs/ARCHITECTURE.md
touch docs/API.md
touch docs/SECURITY.md
touch docs/CHANGELOG.md
touch docs/DESIGN_TOKENS.md
```

**Initialize `docs/PROJECT_STATUS.md`:**
```markdown
# Spetser AI — Project Status Log

## Current Phase: Phase 0 — Preparation
## Last Updated: [ISO TIMESTAMP]
## Status: IN PROGRESS

### Completed Steps
- [x] 0.1 Skill references directory created
- [x] 0.2 Health check verified
- [x] 0.3 Backup branch created
- [x] 0.4 Documentation structure initialized

### Next Steps
1. Begin Phase 1: Security Audit

### Test Summary
- Backend: 167/167 PASS
- Frontend Build: PASS
- Frontend Lint: PASS

### Resume Instructions
- Read this file first.
- Run: `cd backend && python -m pytest tests/ -q`
- Continue from: Phase 1, Step 1.1
```

---

### Step 0.5: Commit Phase 0

```bash
git add -A
git commit -m "feat(phase-0): preparation complete - skills, health check, backup, docs"
```

**PHASE 0 COMPLETE. Proceed to Phase 1.**

==================================================
SECTION 4: PHASE 1 — COMPREHENSIVE SECURITY AUDIT
==================================================

**Estimated Duration:** 45-60 minutes
**Goal:** Identify and document all security vulnerabilities across the entire application.
**Methodology:** Based on `cloudflare/security-audit-skill` — 6-stage audit process.

---

### Step 1.1: Reconnaissance — Map the Attack Surface

**Action:** Read and analyze all security-critical files.

**Files to READ (do not modify yet):**
```
backend/app/main.py
backend/app/core/config.py
backend/app/core/security.py
backend/app/services/auth_service.py
backend/app/api/v1/routes/  (ALL files in this directory)
backend/app/models/  (ALL files)
backend/app/middleware/  (ALL files, if exists)
frontend/src/lib/api.ts  (or equivalent API client)
```

**For each file, document:**
1. What endpoints are exposed?
2. What authentication/authorization is applied?
3. What user input is accepted?
4. What data is returned?
5. Are there any hardcoded secrets?

**Create a security map in `docs/SECURITY_AUDIT.md`:**
```markdown
# Security Audit — Spetser AI

## Audit Date: [DATE]
## Auditor: AI Agent
## Scope: Full application (frontend + backend)

## 1. Attack Surface Map

### Public Endpoints (No Auth Required)
| Endpoint | Method | Purpose | Risk Level |
|----------|--------|---------|------------|
| /api/v1/auth/register | POST | User registration | Medium |
| /api/v1/auth/login | POST | User login | High |
| /api/v1/health | GET | Health check | Low |

### Protected Endpoints (Auth Required)
| Endpoint | Method | Auth Type | Purpose | Risk Level |
|----------|--------|-----------|---------|------------|
| /api/v1/chat | POST | JWT Bearer | AI chat | Medium |
| /api/v1/credits/balance | GET | JWT Bearer | Get balance | Low |

### Admin/Developer Endpoints
| Endpoint | Method | Auth Type | Purpose | Risk Level |
|----------|--------|-----------|---------|------------|
| /api/v1/admin/* | ALL | JWT + Role | Admin ops | Critical |
```

---

### Step 1.2: Vulnerability Hunting — Automated Scans

**Action:** Run grep-based scans to identify potential vulnerabilities.

**A. SQL Injection Scan:**
```bash
# Search for string interpolation in SQL queries
grep -rn "execute.*f\"" backend/app/ --include="*.py" || true
grep -rn "text(" backend/app/ --include="*.py" || true
grep -rn "\.format(" backend/app/ --include="*.py" | grep -i "select\|insert\|update\|delete" || true
grep -rn "%s" backend/app/ --include="*.py" | grep -v "test\|#" || true
```

**For each finding:**
- Note the file, line number, and the query.
- Determine if user input flows into the query.
- Classify: Critical (direct user input), High (indirect input), Low (static query).

**B. Input Validation Scan:**
```bash
# Find endpoints that accept request body without validation
grep -rn "request\.\|Request\|Body\|Query\|Path" backend/app/api/v1/routes/ --include="*.py" | head -50

# Check if Pydantic models are used for validation
grep -rn "BaseModel\|validator\|field_validator" backend/app/schemas/ --include="*.py" | head -30
```

**C. JWT/Session Management Scan:**
```bash
# Find all JWT-related code
grep -rn "jwt\|JWT\|token\|Token\|session\|Session" backend/app/ --include="*.py" | grep -v "test\|__pycache__\|#" | head -40

# Check token expiry configuration
grep -rn "expire\|EXPIRE\|ttl\|TTL" backend/app/ --include="*.py" | head -20
```

**D. Access Control Scan:**
```bash
# Find all auth dependency usage
grep -rn "get_active_student\|get_current_user\|require_admin\|get_developer\|Depends" backend/app/api/ --include="*.py" | head -40

# Find endpoints WITHOUT auth dependencies
grep -rn "@router\.\(get\|post\|put\|delete\|patch\)" backend/app/api/v1/routes/ --include="*.py" | head -40
```

**E. CORS Configuration Scan:**
```bash
grep -rn "CORS\|cors\|allow_origins\|Access-Control" backend/app/ --include="*.py" | head -20
```

**F. Secrets Exposure Scan:**
```bash
# Check for hardcoded secrets
grep -rn "password\|secret\|api_key\|apikey\|token" backend/app/ --include="*.py" | grep -v "test\|#\|env\|config\|hash\|verify" | head -20

# Check .env is in .gitignore
cat .gitignore | grep -i "env"
```

**Document ALL findings in `docs/SECURITY_AUDIT.md` under Section 2.**

---

### Step 1.3: Vulnerability Validation

**Action:** For each potential vulnerability found in Step 1.2, validate it.

**For each finding:**
1. Read the full context (surrounding 20 lines of code).
2. Trace the data flow: Where does user input enter? Where does it go?
3. Determine if the vulnerability is exploitable.
4. Rate severity: Critical / High / Medium / Low / Info.
5. Propose the minimal fix.

**Validation Template (add to SECURITY_AUDIT.md):**
```markdown
### Finding #001
- **File:** `backend/app/api/v1/routes/chat.py`
- **Line:** 42
- **Type:** SQL Injection (Potential)
- **Code:** `query = f"SELECT * FROM messages WHERE user_id = {user_id}"`
- **Exploitable:** YES / NO
- **Severity:** CRITICAL
- **Impact:** Full database read access
- **Fix:** Use parameterized query: `select(Message).where(Message.user_id == user_id)`
- **Status:** OPEN / FIXED
```

---

### Step 1.4: Generate Security Audit Report

**Action:** Compile all findings into a structured report.

**Update `docs/SECURITY_AUDIT.md` with final format:**
```markdown
# Security Audit Report — Spetser AI

## Summary
- **Audit Date:** [DATE]
- **Auditor:** AI Security Agent
- **Scope:** Full application (frontend + backend)
- **Total Findings:** [COUNT]
- **Critical:** [COUNT]
- **High:** [COUNT]
- **Medium:** [COUNT]
- **Low:** [COUNT]

## Critical Findings
| # | File | Line | Vulnerability | Impact | Fix | Status |
|---|------|------|---------------|--------|-----|--------|
| 001 | ... | ... | ... | ... | ... | OPEN |

## High Findings
| # | File | Line | Vulnerability | Impact | Fix | Status |
|---|------|------|---------------|--------|-----|--------|

## Medium Findings
| # | File | Line | Vulnerability | Impact | Fix | Status |
|---|------|------|---------------|--------|-----|--------|

## Low Findings
| # | File | Line | Vulnerability | Impact | Fix | Status |
|---|------|------|---------------|--------|-----|--------|

## Recommendations (Priority Order)
1. [Most critical fix first]
2. [Second most critical]
3. ...

## Compliance Checklist
- [ ] No hardcoded secrets in source code
- [ ] All endpoints have appropriate auth
- [ ] Input validation on all user inputs
- [ ] CORS restricted to known origins
- [ ] JWT tokens have expiry
- [ ] Password hashing uses bcrypt/argon2
- [ ] Rate limiting implemented
- [ ] Error messages don't leak internals
```

---

### Step 1.5: Fix Critical and High Vulnerabilities

**Action:** Fix ALL Critical and High severity findings immediately.

**For each fix:**
1. Read the vulnerable code.
2. Write the fix.
3. Write a test that proves the vulnerability is fixed.
4. Run the test.
5. Run the full test suite to ensure no regressions.
6. Update the finding status in `docs/SECURITY_AUDIT.md` to FIXED.

**Example fix for SQL Injection:**
```python
# BEFORE (VULNERABLE):
query = f"SELECT * FROM messages WHERE user_id = {user_id}"
result = await db.execute(text(query))

# AFTER (FIXED):
from sqlalchemy import select
from app.models.message import Message

stmt = select(Message).where(Message.user_id == user_id)
result = await db.execute(stmt)
```

**Example fix for missing input validation:**
```python
# BEFORE (VULNERABLE):
@router.post("/chat")
async def chat(request: Request):
    message = await request.json()
    # No validation!

# AFTER (FIXED):
from pydantic import BaseModel, Field, field_validator

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    skill_slug: str | None = Field(None, max_length=100)
    
    @field_validator('message')
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        # Remove potential script tags
        import re
        v = re.sub(r'<script[^>]*>.*?</script>', '', v, flags=re.DOTALL | re.IGNORECASE)
        return v.strip()

@router.post("/chat")
async def chat(request: ChatRequest, current_user = Depends(get_active_student)):
    # Now request.message is validated and sanitized
```

---

### Step 1.6: Commit Phase 1

```bash
git add -A
git commit -m "security(phase-1): comprehensive security audit complete - [X] findings, [Y] fixed"
```

**Update `docs/PROJECT_STATUS.md`:**
```markdown
## Phase 1 — Security Audit COMPLETE
- Findings: [TOTAL] (Critical: [X], High: [Y], Medium: [Z], Low: [W])
- Fixed: [COUNT]
- Remaining: [COUNT] (Medium/Low - scheduled for later)
- Report: docs/SECURITY_AUDIT.md
```

**PHASE 1 COMPLETE. Proceed to Phase 2.**

==================================================
SECTION 5: PHASE 2 — UI/UX DESIGN SYSTEM
==================================================

**Estimated Duration:** 30-45 minutes
**Goal:** Establish a complete, consistent design system with tokens, colors, typography, spacing, and animation guidelines.
**Methodology:** Based on `nextlevelbuilder/ui-ux-pro-max-skill` + `Leonxlnx/taste-skill` + `emilkowalski/skills`.

---

### Step 2.1: Create Design Tokens File

**Action:** Create the master design tokens CSS file.

**File to create:** `frontend/src/styles/tokens.css`

**Exact content:**
```css
/* ============================================
   SPETSER AI — DESIGN TOKENS
   Inspired by: ui-ux-pro-max-skill, taste-skill, emilkowalski/skills
   ============================================ */

:root {
  /* ===== BRAND COLORS ===== */
  --color-brand: #01696D;
  --color-brand-hover: #017a7f;
  --color-brand-active: #015a5e;
  --color-brand-light: #E6F4F4;
  --color-brand-subtle: #F0FAFA;

  /* ===== SEMANTIC COLORS ===== */
  --color-success: #000000;
  --color-error: #DC2626;
  --color-error-hover: #B91C1C;
  --color-warning: #F59E0B;
  --color-info: #3B82F6;

  /* ===== BACKGROUND COLORS (Light Mode) ===== */
  --color-bg-primary: #F9F8F4;
  --color-bg-secondary: #FFFFFF;
  --color-bg-tertiary: #F3F2ED;
  --color-bg-elevated: #FFFFFF;
  --color-bg-overlay: rgba(0, 0, 0, 0.5);

  /* ===== TEXT COLORS (Light Mode) ===== */
  --color-text-primary: #1A1A1A;
  --color-text-secondary: #6B7280;
  --color-text-tertiary: #9CA3AF;
  --color-text-inverse: #FFFFFF;
  --color-text-brand: #01696D;

  /* ===== BORDER COLORS ===== */
  --color-border: #E5E7EB;
  --color-border-hover: #D1D5DB;
  --color-border-focus: #01696D;
  --color-border-error: #DC2626;

  /* ===== SPACING SCALE ===== */
  --space-0: 0px;
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
  --space-16: 64px;
  --space-20: 80px;
  --space-24: 96px;

  /* ===== TYPOGRAPHY ===== */
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
  --font-arabic: 'Noto Sans Arabic', 'Inter', sans-serif;

  --text-xs: 0.75rem;    /* 12px */
  --text-sm: 0.875rem;   /* 14px */
  --text-base: 1rem;     /* 16px */
  --text-lg: 1.125rem;   /* 18px */
  --text-xl: 1.25rem;    /* 20px */
  --text-2xl: 1.5rem;    /* 24px */
  --text-3xl: 1.875rem;  /* 30px */
  --text-4xl: 2.25rem;   /* 36px */

  --leading-tight: 1.25;
  --leading-normal: 1.5;
  --leading-relaxed: 1.75;

  --font-normal: 400;
  --font-medium: 500;
  --font-semibold: 600;
  --font-bold: 700;

  /* ===== BORDER RADIUS ===== */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-2xl: 24px;
  --radius-full: 9999px;

  /* ===== SHADOWS ===== */
  --shadow-xs: 0 1px 2px rgba(0, 0, 0, 0.03);
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -4px rgba(0, 0, 0, 0.05);
  --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.05);
  --shadow-2xl: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  --shadow-inner: inset 0 2px 4px rgba(0, 0, 0, 0.05);

  /* ===== TRANSITIONS ===== */
  --transition-fast: 150ms;
  --transition-base: 200ms;
  --transition-slow: 300ms;
  --transition-slower: 500ms;
  --transition-page: 600ms;

  --ease-default: cubic-bezier(0.4, 0, 0.2, 1);
  --ease-in: cubic-bezier(0.4, 0, 1, 1);
  --ease-out: cubic-bezier(0, 0, 0.2, 1);
  --ease-bounce: cubic-bezier(0.68, -0.55, 0.265, 1.55);

  /* ===== Z-INDEX SCALE ===== */
  --z-base: 0;
  --z-dropdown: 10;
  --z-sticky: 20;
  --z-fixed: 30;
  --z-modal-backdrop: 40;
  --z-modal: 50;
  --z-popover: 55;
  --z-toast: 60;
  --z-tooltip: 70;

  /* ===== BREAKPOINTS (for reference) ===== */
  /* sm: 640px, md: 768px, lg: 1024px, xl: 1280px, 2xl: 1536px */

  /* ===== TOUCH TARGETS ===== */
  --touch-target-min: 44px;
  --touch-target-comfortable: 48px;
}

/* ===== DARK MODE TOKENS ===== */
[data-theme="dark"] {
  --color-bg-primary: #0F0E17;
  --color-bg-secondary: #1A1923;
  --color-bg-tertiary: #252432;
  --color-bg-elevated: #2D2C3A;
  --color-bg-overlay: rgba(0, 0, 0, 0.7);

  --color-text-primary: #F9F8F4;
  --color-text-secondary: #A09FA8;
  --color-text-tertiary: #6B7280;
  --color-text-inverse: #1A1A1A;

  --color-border: #2D2C3A;
  --color-border-hover: #3D3C4A;
  --color-border-focus: #01696D;

  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.4);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
  --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
}

/* ===== RTL ADJUSTMENTS ===== */
[dir="rtl"] {
  --font-sans: 'Noto Sans Arabic', 'Inter', sans-serif;
}
```

---

### Step 2.2: Create Animation Guidelines

**Action:** Create a CSS file with reusable animation keyframes.

**File to create:** `frontend/src/styles/animations.css`

```css
/* ============================================
   SPETSER AI — ANIMATION SYSTEM
   Based on: emilkowalski/skills methodology
   ============================================ */

/* === KEYFRAMES === */

@keyframes fadeSlideUp {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeSlideDown {
  from {
    opacity: 0;
    transform: translateY(-12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes fadeOut {
  from { opacity: 1; }
  to { opacity: 0; }
}

@keyframes scaleIn {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes scaleOut {
  from {
    opacity: 1;
    transform: scale(1);
  }
  to {
    opacity: 0;
    transform: scale(0.95);
  }
}

@keyframes slideInRight {
  from {
    opacity: 0;
    transform: translateX(24px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes slideInLeft {
  from {
    opacity: 0;
    transform: translateX(-24px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes messageIn {
  from {
    opacity: 0;
    transform: translateY(8px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

/* === UTILITY CLASSES === */

.animate-fade-slide-up {
  animation: fadeSlideUp 0.5s var(--ease-out) both;
}

.animate-fade-slide-down {
  animation: fadeSlideDown 0.5s var(--ease-out) both;
}

.animate-fade-in {
  animation: fadeIn var(--transition-base) var(--ease-default) both;
}

.animate-scale-in {
  animation: scaleIn var(--transition-base) var(--ease-out) both;
}

.animate-message-in {
  animation: messageIn 0.3s var(--ease-out) both;
}

.animate-pulse {
  animation: pulse 2s var(--ease-default) infinite;
}

.animate-spin {
  animation: spin 1s linear infinite;
}

/* === STAGGER DELAYS (for lists) === */
.stagger-1 { animation-delay: 50ms; }
.stagger-2 { animation-delay: 100ms; }
.stagger-3 { animation-delay: 150ms; }
.stagger-4 { animation-delay: 200ms; }
.stagger-5 { animation-delay: 250ms; }
.stagger-6 { animation-delay: 300ms; }

/* === REDUCED MOTION === */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

### Step 2.3: Create Design Checklist Document

**Action:** Create a design quality checklist based on taste-skill principles.

**File to create:** `docs/DESIGN_CHECKLIST.md`

```markdown
# Design Quality Checklist — Spetser AI

## Visual Hierarchy
- [ ] Primary text: 16px minimum
- [ ] Headings: h1=24px, h2=20px, h3=18px
- [ ] Secondary text: 14px
- [ ] Caption text: 12px minimum
- [ ] Line height: 1.5 for body, 1.25 for headings

## Color & Contrast
- [ ] Text contrast ratio ≥ 4.5:1 (WCAG AA)
- [ ] Large text contrast ratio ≥ 3:1
- [ ] Brand color (#01696D) used consistently
- [ ] Error states use #DC2626
- [ ] Warning states use #F59E0B
- [ ] Dark mode has equivalent contrast

## Spacing & Layout
- [ ] Base spacing unit: 8px
- [ ] Consistent padding: 16px, 24px, 32px
- [ ] Card border-radius: 12px
- [ ] Button border-radius: 8px
- [ ] Input border-radius: 8px
- [ ] Grid gap: 16px

## Interactions
- [ ] Hover states on all interactive elements
- [ ] Focus states visible (keyboard navigation)
- [ ] Active/pressed states
- [ ] Disabled states (opacity 0.5 + cursor not-allowed)
- [ ] Loading states (spinner or skeleton)
- [ ] Transition duration: 200-300ms
- [ ] Easing: cubic-bezier(0.4, 0, 0.2, 1)

## Touch & Mobile
- [ ] Touch targets ≥ 44px
- [ ] Comfortable touch targets: 48px
- [ ] No horizontal scroll on mobile
- [ ] Bottom navigation thumb-friendly
- [ ] Input fields don't get hidden by keyboard

## Accessibility
- [ ] ARIA labels on icon-only buttons
- [ ] Alt text on images
- [ ] Keyboard navigation works
- [ ] Screen reader announcements for dynamic content
- [ ] Color is not the only indicator of state

## RTL Support
- [ ] Layout flips correctly with dir="rtl"
- [ ] Icons that indicate direction flip (arrows, chevrons)
- [ ] Text alignment adjusts
- [ ] Padding/margin logical properties used
```

---

### Step 2.4: Update Global Styles

**Action:** Create or update the global CSS file to import tokens and animations.

**File to create/update:** `frontend/src/styles/global.css`

```css
/* Import design system */
@import './tokens.css';
@import './animations.css';

/* === RESET & BASE === */
*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html {
  font-size: 16px;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}

body {
  font-family: var(--font-sans);
  font-size: var(--text-base);
  line-height: var(--leading-normal);
  color: var(--color-text-primary);
  background-color: var(--color-bg-primary);
  transition: background-color var(--transition-base) var(--ease-default),
              color var(--transition-base) var(--ease-default);
}

/* RTL Support */
[dir="rtl"] body {
  font-family: var(--font-arabic);
}

/* === FOCUS STYLES === */
:focus-visible {
  outline: 2px solid var(--color-border-focus);
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}

/* === SCROLLBAR === */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: var(--radius-full);
}

::-webkit-scrollbar-thumb:hover {
  background: var(--color-border-hover);
}

/* === SELECTION === */
::selection {
  background-color: var(--color-brand-light);
  color: var(--color-brand);
}

/* === LINKS === */
a {
  color: var(--color-brand);
  text-decoration: none;
  transition: color var(--transition-fast) var(--ease-default);
}

a:hover {
  color: var(--color-brand-hover);
}
```

---

### Step 2.5: Commit Phase 2

```bash
git add -A
git commit -m "design(phase-2): complete design system - tokens, animations, checklist, global styles"
```

**PHASE 2 COMPLETE. Proceed to Phase 3.**

==================================================
SECTION 6: PHASE 3 — FRONTEND REBUILD
==================================================

**Estimated Duration:** 2-3 hours
**Goal:** Rebuild the frontend component architecture using the design system from Phase 2.

---

### Step 3.1: Restructure Frontend Directory

**Action:** Ensure the frontend follows this exact structure.

**Target structure:**
```
frontend/src/
├── components/
│   ├── ui/                    # Reusable atomic components
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   ├── TextArea.tsx
│   │   ├── Select.tsx
│   │   ├── Modal.tsx
│   │   ├── Toast.tsx
│   │   ├── Card.tsx
│   │   ├── Badge.tsx
│   │   ├── Avatar.tsx
│   │   ├── Skeleton.tsx
│   │   ├── Spinner.tsx
│   │   └── index.ts          # Barrel export
│   ├── layout/
│   │   ├── Header.tsx
│   │   ├── Sidebar.tsx
│   │   ├── Footer.tsx
│   │   ├── MainLayout.tsx
│   │   └── index.ts
│   ├── chat/
│   │   ├── ChatWindow.tsx
│   │   ├── MessageList.tsx
│   │   ├── MessageBubble.tsx
│   │   ├── InputBox.tsx
│   │   ├── TypingIndicator.tsx
│   │   ├── SkillSelector.tsx
│   │   └── index.ts
│   ├── auth/
│   │   ├── LoginForm.tsx
│   │   ├── RegisterForm.tsx
│   │   ├── PasswordInput.tsx
│   │   ├── EmailVerification.tsx
│   │   └── index.ts
│   └── settings/
│       ├── ProfileSettings.tsx
│       ├── BillingSettings.tsx
│       ├── ColorModeSettings.tsx
│       └── index.ts
├── pages/
│   ├── HomePage.tsx
│   ├── ChatPage.tsx
│   ├── LoginPage.tsx
│   ├── RegisterPage.tsx
│   ├── VerifyEmailPage.tsx
│   ├── SettingsPage.tsx
│   └── NotFoundPage.tsx
├── hooks/
│   ├── useAuth.ts
│   ├── useTheme.ts
│   ├── useToast.ts
│   ├── useChat.ts
│   ├── useCredits.ts
│   └── index.ts
├── lib/
│   ├── api.ts
│   ├── utils.ts
│   ├── constants.ts
│   └── types.ts
├── styles/
│   ├── tokens.css
│   ├── animations.css
│   ├── global.css
│   └── components/
│       ├── button.css
│       ├── input.css
│       ├── card.css
│       ├── chat.css
│       └── modal.css
├── App.tsx
└── main.tsx
```

**Commands:**
```bash
cd frontend/src

# Create directories
mkdir -p components/ui components/layout components/chat components/auth components/settings
mkdir -p pages hooks lib styles/components

# Create barrel export files
echo "// UI Components" > components/ui/index.ts
echo "// Layout Components" > components/layout/index.ts
echo "// Chat Components" > components/chat/index.ts
echo "// Auth Components" > components/auth/index.ts
echo "// Settings Components" > components/settings/index.ts
echo "// Hooks" > hooks/index.ts
```

---

### Step 3.2: Build Core UI Components

**Action:** Create each atomic UI component with full TypeScript typing, accessibility, and design token usage.

#### 3.2.1 — Button Component

**File:** `frontend/src/components/ui/Button.tsx`

```tsx
import { ButtonHTMLAttributes, forwardRef } from 'react';
import { Loader2 } from 'lucide-react';

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  isLoading?: boolean;
  fullWidth?: boolean;
}

const sizeClasses: Record<ButtonSize, string> = {
  sm: 'btn--sm',
  md: 'btn--md',
  lg: 'btn--lg',
};

const variantClasses: Record<ButtonVariant, string> = {
  primary: 'btn--primary',
  secondary: 'btn--secondary',
  ghost: 'btn--ghost',
  danger: 'btn--danger',
  outline: 'btn--outline',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      isLoading = false,
      fullWidth = false,
      children,
      className = '',
      disabled,
      ...props
    },
    ref
  ) => {
    return (
      <button
        ref={ref}
        className={[
          'btn',
          variantClasses[variant],
          sizeClasses[size],
          fullWidth ? 'btn--full-width' : '',
          isLoading ? 'btn--loading' : '',
          className,
        ].filter(Boolean).join(' ')}
        disabled={disabled || isLoading}
        aria-busy={isLoading}
        {...props}
      >
        {isLoading && (
          <Loader2
            className="btn__spinner"
            size={size === 'sm' ? 14 : size === 'lg' ? 20 : 16}
            aria-hidden="true"
          />
        )}
        <span className={isLoading ? 'btn__content btn__content--hidden' : 'btn__content'}>
          {children}
        </span>
      </button>
    );
  }
);

Button.displayName = 'Button';
```

#### 3.2.2 — Input Component with Password Toggle

**File:** `frontend/src/components/ui/Input.tsx`

```tsx
import { InputHTMLAttributes, forwardRef, useState } from 'react';
import { Eye, EyeOff, AlertCircle } from 'lucide-react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
  isPassword?: boolean;
  leftIcon?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, hint, isPassword = false, leftIcon, className = '', id, ...props }, ref) => {
    const [showPassword, setShowPassword] = useState(false);
    const inputId = id || `input-${Math.random().toString(36).slice(2)}`;

    return (
      <div className="input-group">
        {label && (
          <label htmlFor={inputId} className="input-group__label">
            {label}
          </label>
        )}
        <div className={`input-wrapper ${error ? 'input-wrapper--error' : ''} ${className}`}>
          {leftIcon && <span className="input-wrapper__icon-left">{leftIcon}</span>}
          <input
            ref={ref}
            id={inputId}
            type={isPassword && !showPassword ? 'password' : 'text'}
            className="input-wrapper__field"
            aria-invalid={!!error}
            aria-describedby={error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined}
            {...props}
          />
          {isPassword && (
            <button
              type="button"
              className="input-wrapper__toggle-password"
              onClick={() => setShowPassword(!showPassword)}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              tabIndex={-1}
            >
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          )}
        </div>
        {error && (
          <p id={`${inputId}-error`} className="input-group__error" role="alert">
            <AlertCircle size={14} aria-hidden="true" />
            {error}
          </p>
        )}
        {hint && !error && (
          <p id={`${inputId}-hint`} className="input-group__hint">
            {hint}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';
```

#### 3.2.3 — Toast Notification System

**File:** `frontend/src/components/ui/Toast.tsx`

```tsx
import { create } from 'zustand';
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react';

type ToastType = 'success' | 'error' | 'warning' | 'info';

interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
}

interface ToastStore {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
  clearAll: () => void;
}

export const useToastStore = create<ToastStore>((set) => ({
  toasts: [],
  addToast: (toast) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    set((state) => ({
      toasts: [...state.toasts, { ...toast, id }],
    }));
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
      set((state) => ({
        toasts: state.toasts.filter((t) => t.id !== id),
      }));
    }, 5000);
  },
  removeToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),
  clearAll: () => set({ toasts: [] }),
}));

const iconMap: Record<ToastType, React.ReactNode> = {
  success: <CheckCircle size={20} className="toast__icon toast__icon--success" />,
  error: <XCircle size={20} className="toast__icon toast__icon--error" />,
  warning: <AlertTriangle size={20} className="toast__icon toast__icon--warning" />,
  info: <Info size={20} className="toast__icon toast__icon--info" />,
};

export function ToastContainer() {
  const { toasts, removeToast } = useToastStore();

  if (toasts.length === 0) return null;

  return (
    <div className="toast-container" role="region" aria-label="Notifications" aria-live="polite">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast toast--${toast.type}`} role="alert">
          <div className="toast__content">
            {iconMap[toast.type]}
            <div className="toast__text">
              <p className="toast__title">{toast.title}</p>
              {toast.message && <p className="toast__message">{toast.message}</p>}
            </div>
          </div>
          <button
            className="toast__close"
            onClick={() => removeToast(toast.id)}
            aria-label="Dismiss notification"
          >
            <X size={16} />
          </button>
        </div>
      ))}
    </div>
  );
}
```

---

### Step 3.3: Build Chat Components

**Action:** Create the chat interface components.

#### 3.3.1 — Message Bubble

**File:** `frontend/src/components/chat/MessageBubble.tsx`

```tsx
import ReactMarkdown from 'react-markdown';
import { User, Bot } from 'lucide-react';

interface MessageBubbleProps {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  isStreaming?: boolean;
}

export function MessageBubble({ role, content, timestamp, isStreaming = false }: MessageBubbleProps) {
  const isUser = role === 'user';

  return (
    <div className={`message ${isUser ? 'message--user' : 'message--assistant'} animate-message-in`}>
      <div className="message__avatar">
        {isUser ? <User size={20} /> : <Bot size={20} />}
      </div>
      <div className="message__content">
        <div className={`message__bubble ${isUser ? 'message__bubble--user' : 'message__bubble--assistant'}`}>
          {isUser ? (
            <p>{content}</p>
          ) : (
            <div className="message__markdown">
              <ReactMarkdown>{content}</ReactMarkdown>
            </div>
          )}
          {isStreaming && <span className="message__cursor" aria-hidden="true" />}
        </div>
        {timestamp && (
          <time className="message__timestamp" dateTime={timestamp}>
            {new Date(timestamp).toLocaleTimeString('ar-LY', { hour: '2-digit', minute: '2-digit' })}
          </time>
        )}
      </div>
    </div>
  );
}
```

#### 3.3.2 — Chat Input Box

**File:** `frontend/src/components/chat/InputBox.tsx`

```tsx
import { useState, useRef, KeyboardEvent } from 'react';
import { Send, StopCircle, Paperclip } from 'lucide-react';
import { Button } from '../ui/Button';

interface InputBoxProps {
  onSend: (message: string) => void;
  onStop?: () => void;
  isGenerating?: boolean;
  disabled?: boolean;
}

export function InputBox({ onSend, onStop, isGenerating = false, disabled = false }: InputBoxProps) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = () => {
    const trimmed = message.trim();
    if (!trimmed || isGenerating) return;
    onSend(trimmed);
    setMessage('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  };

  return (
    <div className="composer">
      <div className="composer__wrapper">
        <textarea
          ref={textareaRef}
          className="composer__textarea"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          placeholder="اكتب رسالتك هنا..."
          rows={1}
          disabled={disabled}
          aria-label="Chat message input"
        />
        <div className="composer__actions">
          {isGenerating && onStop ? (
            <Button
              variant="ghost"
              size="sm"
              onClick={onStop}
              aria-label="Stop generation"
            >
              <StopCircle size={20} />
            </Button>
          ) : (
            <Button
              variant="primary"
              size="sm"
              onClick={handleSubmit}
              disabled={!message.trim() || isGenerating || disabled}
              aria-label="Send message"
            >
              <Send size={18} />
            </Button>
          )}
        </div>
      </div>
      <p className="composer__hint">
        اضغط Enter للإرسال، Shift+Enter لسطر جديد
      </p>
    </div>
  );
}
```

---

### Step 3.4: Build Component CSS

**Action:** Create CSS files for each component using design tokens.

**File:** `frontend/src/styles/components/button.css`

```css
/* ============================================
   BUTTON COMPONENT STYLES
   ============================================ */

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  font-family: var(--font-sans);
  font-weight: var(--font-medium);
  border: none;
  cursor: pointer;
  border-radius: var(--radius-md);
  transition: all var(--transition-base) var(--ease-default);
  position: relative;
  white-space: nowrap;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}

/* Sizes */
.btn--sm {
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  min-height: 36px;
}

.btn--md {
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-base);
  min-height: var(--touch-target-min);
}

.btn--lg {
  padding: var(--space-4) var(--space-6);
  font-size: var(--text-lg);
  min-height: var(--touch-target-comfortable);
}

/* Variants */
.btn--primary {
  background-color: var(--color-brand);
  color: var(--color-text-inverse);
}

.btn--primary:hover:not(:disabled) {
  background-color: var(--color-brand-hover);
  box-shadow: var(--shadow-md);
}

.btn--primary:active:not(:disabled) {
  background-color: var(--color-brand-active);
  transform: translateY(1px);
}

.btn--secondary {
  background-color: var(--color-bg-tertiary);
  color: var(--color-text-primary);
}

.btn--secondary:hover:not(:disabled) {
  background-color: var(--color-border);
}

.btn--ghost {
  background-color: transparent;
  color: var(--color-text-secondary);
}

.btn--ghost:hover:not(:disabled) {
  background-color: var(--color-bg-tertiary);
  color: var(--color-text-primary);
}

.btn--danger {
  background-color: var(--color-error);
  color: white;
}

.btn--danger:hover:not(:disabled) {
  background-color: var(--color-error-hover);
}

.btn--outline {
  background-color: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-text-primary);
}

.btn--outline:hover:not(:disabled) {
  border-color: var(--color-brand);
  color: var(--color-brand);
}

/* States */
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn--full-width {
  width: 100%;
}

.btn--loading {
  pointer-events: none;
}

.btn__spinner {
  animation: spin 1s linear infinite;
}

.btn__content--hidden {
  visibility: hidden;
}
```

**File:** `frontend/src/styles/components/chat.css`

```css
/* ============================================
   CHAT COMPONENT STYLES
   ============================================ */

/* Message Layout */
.message {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-2) 0;
  max-width: 100%;
}

.message--user {
  flex-direction: row-reverse;
}

.message--assistant {
  flex-direction: row;
}

/* Avatar */
.message__avatar {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.message--user .message__avatar {
  background-color: var(--color-brand-light);
  color: var(--color-brand);
}

.message--assistant .message__avatar {
  background-color: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
}

/* Bubble */
.message__bubble {
  max-width: 70%;
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-xl);
  line-height: var(--leading-relaxed);
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.message__bubble--user {
  background-color: var(--color-brand);
  color: var(--color-text-inverse);
  border-bottom-right-radius: var(--radius-sm);
}

[dir="rtl"] .message__bubble--user {
  border-bottom-right-radius: var(--radius-xl);
  border-bottom-left-radius: var(--radius-sm);
}

.message__bubble--assistant {
  background-color: var(--color-bg-secondary);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
  border-bottom-left-radius: var(--radius-sm);
}

[dir="rtl"] .message__bubble--assistant {
  border-bottom-left-radius: var(--radius-xl);
  border-bottom-right-radius: var(--radius-sm);
}

/* Streaming Cursor */
.message__cursor {
  display: inline-block;
  width: 2px;
  height: 1em;
  background-color: currentColor;
  margin-left: 2px;
  animation: pulse 1s var(--ease-default) infinite;
}

/* Timestamp */
.message__timestamp {
  display: block;
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-top: var(--space-1);
}

/* Composer */
.composer {
  position: sticky;
  bottom: 0;
  padding: var(--space-4);
  background-color: var(--color-bg-primary);
  border-top: 1px solid var(--color-border);
}

.composer__wrapper {
  display: flex;
  align-items: flex-end;
  gap: var(--space-2);
  background-color: var(--color-bg-secondary);
  border: 2px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-2) var(--space-3);
  transition: border-color var(--transition-base) var(--ease-default),
              box-shadow var(--transition-base) var(--ease-default);
}

.composer__wrapper:focus-within {
  border-color: var(--color-brand);
  box-shadow: 0 0 0 3px var(--color-brand-light);
}

.composer__textarea {
  flex: 1;
  border: none;
  outline: none;
  resize: none;
  font-family: var(--font-sans);
  font-size: var(--text-base);
  line-height: var(--leading-normal);
  color: var(--color-text-primary);
  background: transparent;
  max-height: 200px;
  padding: var(--space-1) 0;
}

.composer__textarea::placeholder {
  color: var(--color-text-tertiary);
}

.composer__hint {
  text-align: center;
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-top: var(--space-2);
}

/* Responsive */
@media (max-width: 768px) {
  .message__bubble {
    max-width: 85%;
  }
  
  .composer {
    padding: var(--space-3);
  }
}
```

---

### Step 3.5: Verify Frontend Build

**Commands:**
```bash
cd frontend
npm run lint
npm run build
```

**Expected:** 0 errors, 0 warnings.

**If errors occur:** Fix them. Do not proceed until build is clean.

---

### Step 3.6: Commit Phase 3

```bash
git add -A
git commit -m "feat(phase-3): frontend rebuild - UI components, chat interface, design system integration"
```

**PHASE 3 COMPLETE. Proceed to Phase 4.**

==================================================
SECTION 7: PHASE 4 — BACKEND OPTIMIZATION
==================================================

**Estimated Duration:** 1-2 hours
**Goal:** Optimize backend performance, security, and error handling.

---

### Step 4.1: Optimize Database Connection Pool

**File to update:** `backend/app/db/session.py`

**Read the current file first, then ensure it contains:**
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,  # Verify connections before use
    echo=False,  # Set to True for SQL debugging only
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

async def get_db() -> AsyncSession:
    """Dependency that provides a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

---

### Step 4.2: Add Caching Layer

**File to create:** `backend/app/core/cache.py`

```python
"""
Redis caching utility for Spetser AI.
Provides decorator-based caching for expensive operations.
"""
import hashlib
import json
from functools import wraps
from typing import Any, Callable, Optional

import redis.asyncio as redis

from app.core.config import settings

# Initialize Redis connection
redis_client: Optional[redis.Redis] = None

async def get_redis() -> redis.Redis:
    """Get or create Redis connection."""
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return redis_client

def cache_result(ttl: int = 300, prefix: str = "cache"):
    """
    Decorator to cache function results in Redis.
    
    Args:
        ttl: Time-to-live in seconds (default: 5 minutes)
        prefix: Cache key prefix for namespacing
    
    Usage:
        @cache_result(ttl=600, prefix="user_credits")
        async def get_user_credits(user_id: str) -> dict:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                r = await get_redis()
                
                # Generate cache key from function name and arguments
                key_data = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
                cache_key = f"{prefix}:{hashlib.md5(key_data.encode()).hexdigest()}"
                
                # Try to get from cache
                cached = await r.get(cache_key)
                if cached is not None:
                    return json.loads(cached)
                
                # Execute function
                result = await func(*args, **kwargs)
                
                # Store in cache
                await r.setex(cache_key, ttl, json.dumps(result, default=str))
                
                return result
            except redis.RedisError:
                # If Redis is down, execute without caching
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator

async def invalidate_cache(pattern: str):
    """Invalidate all cache keys matching a pattern."""
    try:
        r = await get_redis()
        keys = await r.keys(pattern)
        if keys:
            await r.delete(*keys)
    except redis.RedisError:
        pass  # Silently fail if Redis is down
```

---

### Step 4.3: Add Rate Limiting Middleware

**File to create:** `backend/app/middleware/rate_limit.py`

```python
"""
Rate limiting middleware for Spetser AI.
Uses Redis for distributed rate limiting.
"""
import time
from typing import Callable

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

import redis.asyncio as redis

from app.core.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding window rate limiter using Redis.
    
    Configuration via environment:
    - RATE_LIMIT_REQUESTS: Max requests per window (default: 100)
    - RATE_LIMIT_WINDOW: Window size in seconds (default: 60)
    """
    
    def __init__(
        self,
        app,
        max_requests: int = 100,
        window_seconds: int = 60,
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._redis: redis.Redis | None = None
    
    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(settings.REDIS_URL)
        return self._redis
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Skip rate limiting for health checks
        if request.url.path in ("/api/v1/health", "/health"):
            return await call_next(request)
        
        # Get client identifier (IP or authenticated user)
        client_id = self._get_client_id(request)
        
        try:
            r = await self._get_redis()
            
            # Sliding window counter
            now = time.time()
            window_start = now - self.window_seconds
            key = f"rate_limit:{client_id}"
            
            # Remove old entries and add current request
            pipe = r.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, self.window_seconds + 1)
            results = await pipe.execute()
            
            request_count = results[2]
            
            if request_count > self.max_requests:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "Too many requests. Please try again later.",
                            "retry_after": self.window_seconds,
                        }
                    },
                    headers={
                        "Retry-After": str(self.window_seconds),
                        "X-RateLimit-Limit": str(self.max_requests),
                        "X-RateLimit-Remaining": "0",
                    },
                )
            
            # Add rate limit headers to response
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(self.max_requests)
            response.headers["X-RateLimit-Remaining"] = str(
                max(0, self.max_requests - request_count)
            )
            return response
            
        except redis.RedisError:
            # If Redis is down, allow the request but log warning
            return await call_next(request)
    
    def _get_client_id(self, request: Request) -> str:
        """Extract client identifier from request."""
        # Try to get user ID from auth header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            # Use a hash of the token as identifier
            import hashlib
            return hashlib.md5(auth_header.encode()).hexdigest()
        
        # Fall back to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        return request.client.host if request.client else "unknown"
```

---

### Step 4.4: Improve Error Handling

**File to create/update:** `backend/app/core/exceptions.py`

```python
"""
Custom exception classes and global error handler for Spetser AI.
"""
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


class AppException(HTTPException):
    """Base application exception with error code."""
    
    def __init__(self, status_code: int, detail: str, code: str):
        super().__init__(status_code=status_code, detail=detail)
        self.code = code


class AuthenticationError(AppException):
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            code="AUTH_ERROR",
        )


class AuthorizationError(AppException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            code="AUTHORIZATION_ERROR",
        )


class NotFoundError(AppException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            code="NOT_FOUND",
        )


class ValidationError(AppException):
    def __init__(self, detail: str = "Validation failed"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            code="VALIDATION_ERROR",
        )


class RateLimitError(AppException):
    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            code="RATE_LIMIT_EXCEEDED",
        )


class InsufficientCreditsError(AppException):
    def __init__(self, detail: str = "Insufficient credits"):
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=detail,
            code="INSUFFICIENT_CREDITS",
        )


class ExternalServiceError(AppException):
    def __init__(self, detail: str = "External service unavailable"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            code="EXTERNAL_SERVICE_ERROR",
        )


# === Global Exception Handlers ===

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle custom application exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.detail,
            }
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": errors,
            }
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected errors. Never leak internal details."""
    # Log the actual error internally
    import logging
    logger = logging.getLogger("spetser_ai")
    logger.exception(f"Unhandled exception: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred. Please try again.",
            }
        },
    )
```

---

### Step 4.5: Update main.py with Middleware and Handlers

**File to update:** `backend/app/main.py`

**Add these registrations (read existing file first, add missing parts):**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from app.middleware.rate_limit import RateLimitMiddleware
from fastapi.exceptions import RequestValidationError

app = FastAPI(
    title="Spetser AI API",
    version="1.0.0",
    description="Arabic-first educational AI platform",
)

# === MIDDLEWARE (order matters - first added = last executed) ===

# Rate Limiting
app.add_middleware(
    RateLimitMiddleware,
    max_requests=100,
    window_seconds=60,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,  # From config, not hardcoded
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    max_age=600,
)

# === EXCEPTION HANDLERS ===
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)
```

---

### Step 4.6: Run Backend Tests

```bash
cd backend
python -m pytest tests/ -v --tb=short
```

**ALL tests must pass. Fix any failures.**

---

### Step 4.7: Commit Phase 4

```bash
git add -A
git commit -m "perf(phase-4): backend optimization - connection pool, caching, rate limiting, error handling"
```

**PHASE 4 COMPLETE. Proceed to Phase 5.**

==================================================
SECTION 8: PHASE 5 — PENETRATION TESTING
==================================================

**Estimated Duration:** 45 minutes
**Goal:** Validate security controls through controlled testing.
**Methodology:** Based on `usestrix/strix` (simplified, safe, local-only).

---

### Step 5.1: Authentication Tests

**Execute these curl commands and record results:**

```bash
# Test 1: Login with wrong password (should return 401)
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"wrong_password"}'
# Expected: 401

# Test 2: Access protected endpoint without token (should return 401)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/conversations
# Expected: 401

# Test 3: Access protected endpoint with invalid token (should return 401)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/conversations \
  -H "Authorization: Bearer invalid_token_here"
# Expected: 401

# Test 4: Access admin endpoint with regular user token (should return 403)
# First get a valid token, then:
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/admin/users \
  -H "Authorization: Bearer [REGULAR_USER_TOKEN]"
# Expected: 403
```

---

### Step 5.2: Input Validation Tests

```bash
# Test 5: XSS attempt in chat message
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [VALID_TOKEN]" \
  -d '{"message":"<script>alert(1)</script>"}'
# Expected: Script tags should be sanitized or escaped in response

# Test 6: SQL Injection in login
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@spetser.ai\" OR \"1\"=\"1","password":"anything"}'
# Expected: 401 (not 200)

# Test 7: Extremely long input (should be rejected)
LONG_STRING=$(python3 -c "print('A' * 100000)")
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [VALID_TOKEN]" \
  -d "{\"message\":\"$LONG_STRING\"}"
# Expected: 422 (validation error)
```

---

### Step 5.3: Rate Limiting Test

```bash
# Test 8: Send 110 rapid requests (should get 429 after ~100)
for i in $(seq 1 110); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/health)
  if [ "$STATUS" = "429" ]; then
    echo "Rate limit triggered at request $i"
    break
  fi
done
# Expected: 429 triggered around request 100-110
```

---

### Step 5.4: Generate Penetration Test Report

**File to create/update:** `docs/PENETRATION_TEST.md`

```markdown
# Penetration Test Report — Spetser AI

## Summary
- **Test Date:** [DATE]
- **Tester:** AI Security Agent
- **Scope:** Authentication, Input Validation, Rate Limiting, Access Control
- **Environment:** Local Development

## Test Results

### Authentication
| # | Test | Expected | Actual | Status |
|---|------|----------|--------|--------|
| 1 | Wrong password login | 401 | [RESULT] | PASS/FAIL |
| 2 | No token on protected route | 401 | [RESULT] | PASS/FAIL |
| 3 | Invalid token | 401 | [RESULT] | PASS/FAIL |
| 4 | Regular user on admin route | 403 | [RESULT] | PASS/FAIL |

### Input Validation
| # | Test | Expected | Actual | Status |
|---|------|----------|--------|--------|
| 5 | XSS in chat message | Sanitized | [RESULT] | PASS/FAIL |
| 6 | SQL Injection in login | 401 | [RESULT] | PASS/FAIL |
| 7 | Oversized input | 422 | [RESULT] | PASS/FAIL |

### Rate Limiting
| # | Test | Expected | Actual | Status |
|---|------|----------|--------|--------|
| 8 | 110 rapid requests | 429 after ~100 | [RESULT] | PASS/FAIL |

## Vulnerabilities Found
[List any vulnerabilities discovered]

## Recommendations
1. [Priority recommendations]

## Sign-off
- [ ] All critical tests passed
- [ ] No exploitable vulnerabilities found
- [ ] Rate limiting functional
- [ ] Input validation comprehensive
```

---

### Step 5.5: Commit Phase 5

```bash
git add -A
git commit -m "security(phase-5): penetration testing complete - [X]/[Y] tests passed"
```

**PHASE 5 COMPLETE. Proceed to Phase 6.**

==================================================
SECTION 9: PHASE 6 — FINAL VERIFICATION AND DOCUMENTATION
==================================================

**Estimated Duration:** 30 minutes
**Goal:** Final verification, documentation, and deployment preparation.

---

### Step 6.1: Run Full Test Suite

```bash
# Backend
cd backend
python -m pytest tests/ -v --tb=short

# Frontend
cd ../frontend
npm run lint
npm run build
npm run test 2>/dev/null || true
```

**ALL must pass.**

---

### Step 6.2: Final Checklist Verification

**Verify each item:**

**Functionality:**
- [ ] User registration works
- [ ] Email verification works
- [ ] Login works
- [ ] Chat with AI works
- [ ] Streaming responses work
- [ ] Credits system works
- [ ] Settings page works
- [ ] Dark/Light mode works
- [ ] RTL layout works
- [ ] Mobile responsive works

**Security:**
- [ ] All protected endpoints require auth
- [ ] No hardcoded secrets
- [ ] Rate limiting active
- [ ] Input validation on all endpoints
- [ ] CORS restricted
- [ ] Error messages don't leak internals

**Performance:**
- [ ] Database connection pooling configured
- [ ] Caching layer implemented
- [ ] Frontend bundle size reasonable (<500KB initial)

---

### Step 6.3: Create Architecture Documentation

**File:** `docs/ARCHITECTURE.md`

```markdown
# Spetser AI — Architecture Documentation

## System Overview
[Describe the high-level architecture]

## Tech Stack
- Backend: Python 3.11+, FastAPI, SQLAlchemy Async, PostgreSQL
- Frontend: TypeScript, React, Vite, Tailwind CSS
- Cache: Redis
- Auth: JWT (Access + Refresh tokens)

## Directory Structure
[Document the final directory structure]

## API Endpoints
[List all endpoints with method, path, auth requirement]

## Database Schema
[Key tables and relationships]

## Security Architecture
[Auth flow, rate limiting, input validation]

## Deployment
[How to deploy frontend and backend]
```

---

### Step 6.4: Create API Documentation

**File:** `docs/API.md`

Document every endpoint with:
- Method and path
- Auth requirement
- Request body schema
- Response schema
- Error codes
- Example curl command

---

### Step 6.5: Update CHANGELOG

**File:** `docs/CHANGELOG.md`

```markdown
# Changelog

## [1.0.0] - [DATE]

### Added
- Comprehensive security audit (Phase 1)
- Complete design system with tokens (Phase 2)
- Rebuilt frontend component library (Phase 3)
- Redis caching layer (Phase 4)
- Rate limiting middleware (Phase 4)
- Custom error handling (Phase 4)
- Penetration testing (Phase 5)
- Full documentation suite (Phase 6)

### Security
- Fixed [X] critical vulnerabilities
- Fixed [Y] high-severity vulnerabilities
- Added input validation to all endpoints
- Implemented rate limiting (100 req/min)
- Hardened CORS configuration

### Changed
- Database connection pool optimized (20 connections)
- Error responses standardized
- Frontend component architecture restructured

### Fixed
- [List specific bugs fixed]
```

---

### Step 6.6: Final Commit and Status Update

```bash
git add -A
git commit -m "docs(phase-6): final verification, documentation, and release preparation"
```

**Update `docs/PROJECT_STATUS.md` to final state:**
```markdown
# Spetser AI — Project Status Log

## Current Phase: ALL PHASES COMPLETE
## Last Updated: [ISO TIMESTAMP]
## Status: READY FOR DEPLOYMENT

### Completed Phases
- [x] Phase 0: Preparation and Setup
- [x] Phase 1: Security Audit ([X] findings, [Y] fixed)
- [x] Phase 2: UI/UX Design System
- [x] Phase 3: Frontend Rebuild
- [x] Phase 4: Backend Optimization
- [x] Phase 5: Penetration Testing ([X]/[Y] tests passed)
- [x] Phase 6: Final Verification and Documentation

### Test Summary
- Backend: [X]/[X] PASS
- Frontend Build: PASS
- Frontend Lint: PASS
- Pen Tests: [X]/[Y] PASS

### Next Steps
1. Deploy to staging environment
2. Run smoke tests on staging
3. Deploy to production
4. Monitor for 48 hours
```

---

### Step 6.7: Deployment Commands

```bash
# Build frontend for production
cd frontend
npm run build

# Start backend for production
cd ../backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Or with Docker:
docker compose up --build -d
```

**PHASE 6 COMPLETE. PROJECT REFACTOR FINISHED.**

==================================================
SECTION 10: SUMMARY TABLE
==================================================

| Phase | Description | Est. Duration | Key Deliverables |
|-------|-------------|---------------|------------------|
| 0 | Preparation & Setup | 15 min | Backup, health check, docs structure |
| 1 | Security Audit | 45 min | SECURITY_AUDIT.md, vulnerability fixes |
| 2 | UI/UX Design System | 30 min | tokens.css, animations.css, design checklist |
| 3 | Frontend Rebuild | 2-3 hrs | UI components, chat interface, CSS |
| 4 | Backend Optimization | 1-2 hrs | Caching, rate limiting, error handling |
| 5 | Penetration Testing | 45 min | PENETRATION_TEST.md, curl tests |
| 6 | Final Verification | 30 min | Architecture docs, API docs, changelog |

**Total Estimated Duration:** 5-7 hours

==================================================
SECTION 11: CRITICAL REMINDERS
==================================================

1. **NEVER skip tests.** If a test fails, stop and fix it.
2. **NEVER hardcode secrets.** Use environment variables only.
3. **ALWAYS commit after each phase.** This creates rollback points.
4. **ALWAYS update PROJECT_STATUS.md.** This is the memory of the project.
5. **ALWAYS log errors in ERROR_LOG.md.** This prevents repeating mistakes.
6. **SECURITY FIRST.** Do not deploy any change without security verification.
7. **BACKUP BEFORE DESTRUCTIVE OPERATIONS.** Always create a branch before major changes.
8. **TEST ON MOBILE.** Verify responsive design at 375px width.
9. **TEST RTL.** Verify Arabic layout renders correctly.
10. **DOCUMENT EVERYTHING.** Future you will thank present you.

==================================================
END OF PROMPT
==================================================

**AWAITING USER COMMAND:**
- Say "Start Phase 0" to begin execution.
- Say "Continue" to resume from where we left off (reads PROJECT_STATUS.md).
- Say "Skip to Phase [N]" to jump to a specific phase (use with caution).

GO.
```

---

هذا البرومبت الآن:

1. **مفصل جداً** — كل خطوة تحتوي على الكود الفعلي، الأوامر الدقيقة، والملفات المستهدفة
2. **باللغة الإنجليزية** — جاهز لأي أداة AI
3. **خطوة بخطوة** — 6 مراحل، كل مرحلة مقسمة لخطوات فرعية مرقمة
4. **يحتوي على بروتوكول صارم** — كل خطوة تتبع نفس التسلسل: أعلن ← افحص ← خطط ← نفذ ← تحقق ← أصلح ← وثق ← التزم ← أبلغ
5. **معالجة أخطاء مدمجة** — بروتوكول واضح للتعامل مع أي فشل
6. **ملف حالة مستمر** — `PROJECT_STATUS.md` يحدَّث بعد كل خطوة
7. **سجل أخطاء** — `ERROR_LOG.md` يمنع تكرار الأخطاء
# البرومت الشامل — إعادة بناء Spetser AI

> **الهدف:** تطبيق إصلاحات شاملة على مشروع Spetser AI بالاعتماد على أفضل الممارسات من:
> - `cloudflare/security-audit-skill` — تدقيق أمني متعدد المراحل
> - `nextlevelbuilder/ui-ux-pro-max-skill` — تصميم UI/UX احترافي
> - `Leonxlnx/taste-skill` — مهارات التصميم الراقي
> - `emilkowalski/skills` — حركات وتفاعلات متقدمة
> - `usestrix/strix` — اختبار الاختراق والأمان

---

## المرحلة 0: التحضير والإعداد

### 0.1 تنصيب المهارات في المشروع

قم بإنشاء مجلد `.claude/skills/` في جذر المشروع، ثم انسخ المهارات التالية:

```
.claude/skills/
├── security-audit/           # من cloudflare/security-audit-skill
├── ui-ux-pro-max/            # من nextlevelbuilder/ui-ux-pro-max-skill
├── taste-skill/              # من Leonxlnx/taste-skill (3 مهارات فرعية)
└── emil-design-eng/          # من emilkowalski/skills
```

**الأوامر:**
```bash
mkdir -p .claude/skills
cp -r "$(pwd)/../audit-skill/security-audit-skill/skills/security-audit" .claude/skills/
cp -r "$(pwd)/../ui-ux-pro-max-skill" .claude/skills/ui-ux-pro-max
cp -r "$(pwd)/../taste-skill" .claude/skills/taste-skill
cp -r "$(pwd)/../emilkowalski-skills/skills/emil-design-eng" .claude/skills/
```

### 0.2 التحقق من الحالة الحالية

```bash
cd frontend && npm run build && npm run lint && npm run test
cd ../backend && python -m pytest tests/ -v --tb=short
```

**المطلوب:** تأكد أن كل الاختبارات الحالية تعمل قبل البدء. إذا كان هناك خطأ، قم بإصلاحه أولاً.

### 0.3 نسخة احتياطية

```bash
git add -A
git commit -m "chore: backup before comprehensive refactor"
git branch backup-before-refactor-$(date +%Y%m%d)
```

---

## المرحلة 1: التدقيق الأمني الشامل (Security Audit)

> مستوحى من `cloudflare/security-audit-skill` مع 6 مراحل

### 1.1 الاستطلاع (Reconnaissance)

افحص بنية المشروع وحدد الحدود الأمنية:

**الخطوات:**
1. اقرأ جميع ملفات البنية التحتية: `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/core/security.py`
2. حدد جميع نقاط النهاية (endpoints) في `backend/app/api/v1/routes/`
3. افحص نماذج البيانات في `backend/app/models/`
4. افحص خدمة المصادقة: `backend/app/services/auth_service.py`
5. افحص استخدام JWT و session management
6. افحص CORS و middleware الأمان

**الأسئلة الرئيسية:**
- هل جميع نقاط النهاية المحمية تستخدم `get_active_student` بشكل صحيح؟
- هل توجد أي بيانات اعتماد (credentials) مكشوفة في الكود؟
- هل يتم التحقق من الصلاحيات على كل مستوى؟
- هل توجد ثغرات XSS أو CSRF أو Injection؟

### 1.2 البحث عن الثغرات (Hunting)

نفّذ الفحوصات التالية:

**أ. حقن SQL (SQL Injection):**
```bash
# ابحث عن استعلامات غير parameterize
grep -r "execute.*f\"" backend/app/ || true
grep -r "text(" backend/app/ || true
grep -r "\.format(" backend/app/ || true
grep -r "%.*%" backend/app/ || true
```

**ب. التحقق من المدخلات (Input Validation):**
```bash
# ابحث عن مدخلات غير محققة
grep -r "request\." backend/app/api/v1/routes/ | grep -v "validate\|verify\|check" | head -30
```

**ج. إدارة الجلسات (Session Management):**
```bash
# افحص JWT token handling
grep -r "jwt\|token\|session" backend/app/ --include="*.py" | grep -v "test\|#" | head -30
```

**د. أذونات الوصول (Access Control):**
```bash
# افحص require_admin / get_active_student usage
grep -r "require_admin\|get_active_student\|get_developer" backend/app/ --include="*.py" | head -30
```

### 1.3 التحقق من الثغرات (Validation)

لكل ثغرة محتملة:
1. حدد الملف والسطر
2. حدد التأثير الأمني
3. اقترح الإصلاح الأدنى
4. تحقق من أن الإصلاح لا يكسر الوظائف الحالية

### 1.4 تقرير التدقيق

أنشئ ملف `docs/SECURITY_AUDIT.md` يحتوي على:

```markdown
# تقرير التدقيق الأمني — Spetser AI

## ملخص
- التاريخ: [التاريخ]
- المدقق: Hermes Agent
- النطاق: تطبيق كامل (frontend + backend)

## الثغرات المكتشة

### حرجة (Critical)
| # | الملف | السطر | الثغرة | التأثير | الإصلاح |
|---|-------|-------|--------|---------|---------|

### عالية (High)
| # | الملف | السطر | الثغرة | التأثير | الإصلاح |

### متوسطة (Medium)
| # | الملف | السطر | الثغرة | التأثير | الإصلاح |

### منخفضة (Low)
| # | الملف | السطر | الثغرة | التأثير | الإصلاح |

## التوصيات
1. ...
```

---

## المرحلة 2: تصميم واجهة المستخدم (UI/UX Design)

> مستوحى من `nextlevelbuilder/ui-ux-pro-max-skill` + `taste-skill` + `emilkowalski/skills`

### 2.1 مبادئ التصميم الأساسية

استخدم المبادئ التالية من `emilkowalski/skills`:

**أ. اختيار الحركة الصحيحة (Animation Selection):**
- استخدم `ease-out` للدخول (enter animations)
- استخدم `ease-in` للخروج (exit animations)
- استخدم `cubic-bezier(0.4, 0, 0.2, 1)` للانتقالات العامة
- مدة الانتقال: 200-300ms للعناصر الصغيرة، 400-600ms للصفحات

**ب. التسلسل الهرمي البصري (Visual Hierarchy):**
- حجم الخط الأساسي: 16px
- حجم الخط للعناوين: 24px (h1), 20px (h2), 18px (h3)
- التباعد: 8px base, 16px, 24px, 32px, 48px, 64px
- نصف قطر الحدود: 8px (صغيرة), 12px (متوسطة), 16px (كبيرة)

**ج. نظام الألوان (Color System):**
- **اللون الأساسي (Brand):** `#01696D` (Teal)
- **الخلفية:** `#F9F8F4` (light mode) / `#0F0E17` (dark mode)
- **اللون الناجح:** `#000000` (أسود — تم تغييره من الأخضر)
- **اللون الخطائي:** `#DC2626` (أحمر)
- **اللون التحذيري:** `#F59E0B` (برتقالي)

**د. المكونات (Components):**
- استخدم مكونات `lucide-react` للأيقونات
- استخدم بطاقات بحدود خفيفة (border-radius: 12px)
- استخدم ظلال خفيفة للعناصر العائمة

### 2.2 تحسين التصميم الحالي

**الصفحة الرئيسية (HomePage):**
```css
/* الحركات */
.home__hero { animation: fadeSlideUp 0.5s cubic-bezier(0.4, 0, 0.2, 1); }
.home__skill-card { transition: transform 0.2s ease, box-shadow 0.2s ease; }
.home__skill-card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.08); }

/* التباعد */
.home__section { margin-bottom: 32px; }
.home__grid { display: grid; gap: 16px; }

/* الاستجابة */
@media (max-width: 768px) {
  .home__grid { grid-template-columns: 1fr; }
}
```

**المحادثة (ChatPage):**
```css
/* الفقاعات */
.chat__bubble {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 16px;
  animation: messageIn 0.3s ease;
}
.chat__bubble--user { border-bottom-right-radius: 4px; }
.chat__bubble--ai { border-bottom-left-radius: 4px; }

/* شريط الإدخال */
.composer {
  border: 2px solid transparent;
  transition: border-color 0.2s ease;
}
.composer:focus-within { border-color: var(--color-primary); }
```

### 2.3 تصميم الوضع الداكن (Dark Mode)

```css
[data-theme="dark"] {
  --bg-primary: #0F0E17;
  --bg-secondary: #1A1923;
  --bg-tertiary: #252432;
  --text-primary: #F9F8F4;
  --text-secondary: #A09FA8;
  --border-color: #2D2C3A;
  --color-primary: #01696D;
  --color-primary-hover: #017a7f;
  --shadow-color: rgba(0, 0, 0, 0.3);
}
```

### 2.4 قائمة مراجعة التصميم (Design Checklist)

مستوحاة من `taste-skill`:

- [ ] **التباين:** نسبة التباين ≥ 4.5:1 للنصوص الأساسية
- [ ] **حجم الخط:** لا يقل عن 14px للنصوص الصغيرة
- [ ] **حجم اللمس:** لا يقل عن 44px للأزرار
- [ ] **التباعد:** متسق على مستوى الصفحة
- [ ] **الحركة:** مدة 200-500ms، منحنيات طبيعية
- [ ] **الحالات:** hover, focus, active, disabled واضحة
- [ ] **التنقل:** مسار واضح للمستخدم
- [ ] **التغذية الراجعة:** رسائل نجاح/خطأ واضحة
- [ ] **إمكانية الوصول:** ARIA labels، keyboard navigation

---

## المرحلة 3: إعادة بناء الواجهة الأمامية (Frontend Rebuild)

### 3.1 إعادة هيكلة المكونات

```
frontend/src/
├── components/
│   ├── ui/                    # مكونات قابلة لإعادة الاستخدام
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   ├── Modal.tsx
│   │   ├── Toast.tsx
│   │   └── Card.tsx
│   ├── layout/
│   │   ├── Header.tsx
│   │   ├── Sidebar.tsx
│   │   └── Footer.tsx
│   └── chat/
│       ├── ChatWindow.tsx
│       ├── MessageList.tsx
│       ├── MessageBubble.tsx
│       └── InputBox.tsx
├── pages/
│   ├── HomePage.tsx
│   ├── ChatPage.tsx
│   ├── LoginPage.tsx
│   └── SettingsPage.tsx
├── hooks/
│   ├── useAuth.ts
│   ├── useTheme.ts
│   └── useToast.ts
├── lib/
│   ├── api.ts
│   └── utils.ts
├── styles/
│   ├── tokens.css            # Design tokens
│   ├── global.css             # أنماط عامة
│   └── components/            # أنماط المكونات
│       ├── button.css
│       ├── card.css
│       └── chat.css
└── App.tsx
```

### 3.2 مكونات UI الأساسية

**Button.tsx:**
```tsx
import { ButtonHTMLAttributes, forwardRef } from 'react';
import { Loader2 } from 'lucide-react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', isLoading, children, className, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={`btn btn--${variant} btn--${size} ${className || ''}`}
        disabled={isLoading || props.disabled}
        {...props}
      >
        {isLoading && <Loader2 className="btn__spinner" size={16} />}
        {children}
      </button>
    );
  }
);
```

**Toast.tsx (إشعارات):**
```tsx
import { create } from 'zustand';
import { CheckCircle, XCircle, AlertCircle, X } from 'lucide-react';

interface Toast {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
}

interface ToastStore {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
}

export const useToast = create<ToastStore>((set) => ({
  toasts: [],
  addToast: (toast) => {
    const id = Math.random().toString(36).slice(2);
    set((state) => ({ toasts: [...state.toasts, { ...toast, id }] }));
    setTimeout(() => {
      set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }));
    }, 5000);
  },
  removeToast: (id) => set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
}));
```

### 3.3 نظام التصميم (Design Tokens)

**tokens.css:**
```css
:root {
  /* Colors */
  --color-brand: #01696D;
  --color-brand-hover: #017a7f;
  --color-brand-light: #E6F4F4;
  
  --color-success: #000000;
  --color-error: #DC2626;
  --color-warning: #F59E0B;
  --color-info: #3B82F6;
  
  --color-bg-primary: #F9F8F4;
  --color-bg-secondary: #FFFFFF;
  --color-bg-tertiary: #F3F2ED;
  
  --color-text-primary: #1A1A1A;
  --color-text-secondary: #6B7280;
  --color-text-tertiary: #9CA3AF;
  
  --color-border: #E5E7EB;
  --color-border-focus: #01696D;
  
  /* Spacing */
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
  
  /* Typography */
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
  
  --text-xs: 12px;
  --text-sm: 14px;
  --text-base: 16px;
  --text-lg: 18px;
  --text-xl: 20px;
  --text-2xl: 24px;
  --text-3xl: 30px;
  --text-4xl: 36px;
  
  /* Border Radius */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-full: 9999px;
  
  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
  
  /* Transitions */
  --transition-fast: 150ms;
  --transition-base: 200ms;
  --transition-slow: 300ms;
  --transition-slower: 500ms;
  
  /* Z-Index */
  --z-dropdown: 10;
  --z-sticky: 20;
  --z-fixed: 30;
  --z-modal-backdrop: 40;
  --z-modal: 50;
  --z-toast: 60;
}

[data-theme="dark"] {
  --color-bg-primary: #0F0E17;
  --color-bg-secondary: #1A1923;
  --color-bg-tertiary: #252432;
  
  --color-text-primary: #F9F8F4;
  --color-text-secondary: #A09FA8;
  --color-text-tertiary: #6B7280;
  
  --color-border: #2D2C3A;
  --color-border-focus: #01696D;
}
```

---

## المرحلة 4: تحسين الواجهة الخلفية (Backend Optimization)

### 4.1 تحسين الأداء

**أ. تحسين قاعدة البيانات:**
```python
# backend/app/db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    echo=False,
)

async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

**ب. إضافة التخزين المؤقت (Caching):**
```python
# backend/app/core/cache.py
from functools import wraps
import hashlib
import json
from typing import Callable, Any

def cache_result(ttl: int = 300):
    """Cache decorator for function results."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{hashlib.md5(json.dumps([args, kwargs], default=str).encode()).hexdigest()}"
            # Try to get from cache
            cached = await redis.get(key)
            if cached:
                return json.loads(cached)
            # Execute and cache
            result = await func(*args, **kwargs)
            await redis.setex(key, ttl, json.dumps(result, default=str))
            return result
        return wrapper
    return decorator
```

### 4.2 تحسين الأمان

**أ. إضافة rate limiting:**
```python
# backend/app/middleware/rate_limit.py
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import time

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 100, window: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window
        self.requests = {}
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        now = time.time()
        
        # Clean old entries
        self.requests = {k: v for k, v in self.requests.items() if now - v['start'] < self.window}
        
        if client_ip not in self.requests:
            self.requests[client_ip] = {'count': 1, 'start': now}
        else:
            self.requests[client_ip]['count'] += 1
        
        if self.requests[client_ip]['count'] > self.max_requests:
            raise HTTPException(status_code=429, detail="Too many requests")
        
        return await call_next(request)
```

**ب. تحسين CORS:**
```python
# backend/app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://spetser-ai.vercel.app", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    max_age=600,
)
```

### 4.3 إدارة الأخطاء

```python
# backend/app/core/exceptions.py
from fastapi import HTTPException, status

class AppException(HTTPException):
    def __init__(self, status_code: int, detail: str, code: str):
        super().__init__(status_code=status_code, detail=detail)
        self.code = code

class AuthenticationError(AppException):
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            code="AUTH_ERROR"
        )

class ValidationError(AppException):
    def __init__(self, detail: str = "Validation failed"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            code="VALIDATION_ERROR"
        )

class NotFoundError(AppException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            code="NOT_FOUND"
        )
```

---

## المرحلة 5: اختبار الاختراق (Penetration Testing)

> مستوحى من `usestrix/strix` (نسخة مبسطة وآمنة للاختبار المحلي)

### 5.1 اختبارات أساسية

**أ. اختبار المصادقة:**
```bash
# اختبار تسجيل الدخول
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"wrong"}'

# التحقق من رفض الطلبات غير المصرح بها
curl http://localhost:8000/api/v1/conversations \
  -H "Authorization: Bearer invalid_token"
```

**ب. اختبار المدخلات:**
```bash
# اختبار XSS
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"<script>alert(1)</script>"}'

# اختبار SQL Injection
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin\" OR \"1\"=\"1","password":"anything"}'
```

**ج. اختبار Rate Limiting:**
```bash
# إرسال 100 طلب متتالي
for i in {1..100}; do
  curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/v1/credits/balance
done
```

### 5.2 تقرير الاختبارات

أنشئ `docs/PENETRATION_TEST.md`:

```markdown
# تقرير اختبار الاختراق — Spetser AI

## الملخص
- التاريخ: [التاريخ]
- النطاق: API endpoints, Authentication, Input Validation

## النتائج

### ناجحة (Passed)
- [x] رفض المصادقة الخاطئة
- [x] حماية CSRF
- [x] تشفير كلمات المرور
- [x] إدارة الجلسات

### تحتاج تحسين (Needs Improvement)
- [ ] Rate limiting
- [ ] Input sanitization
- [ ] Error messages (لا تكشف معلومات حساسة)

### فاشلة (Failed)
- [ ] أي ثغرة حرجة
```

---

## المرحلة 6: التحقق النهائي والتوثيق

### 6.1 قائمة التحقق النهائية

**الوظائف:**
- [ ] تسجيل الدخول يعمل
- [ ] تسجيل الحساب يعمل
- [ ] المحادثات تعمل
- [ ] الرصيد يعمل
- [ ] الإعدادات تعمل

**الأمان:**
- [ ] جميع نقاط النهاية المحمية تعمل
- [ ] لا توجد بيانات اعتماد مكشوفة
- [ ] Rate limiting يعمل
- [ ] Input validation يعمل

**التصميم:**
- [ ] التباين مقبول
- [ ] الحركة سلسة
- [ ] الاستجابة للشاشات المختلفة
- [ ] الوضع الداكن يعمل

### 6.2 التوثيق

أنشئ الملفات التالية:

1. `docs/ARCHITECTURE.md` — بنية المشروع
2. `docs/API.md` — توثيق API
3. `docs/SECURITY.md` — سياسات الأمان
4. `docs/CHANGELOG.md` — سجل التغييرات

### 6.3 النشر

```bash
# بناء الواجهة الأمامية
cd frontend
npm run build
npm run preview  # اختبار محلي

# تشغيل الواجهة الخلفية
cd ../backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## ملخص المراحل

| المرحلة | الوصف | المدة التقديرة |
|---------|--------|---------------|
| 0 | التحضير والإعداد | 15 دقيقة |
| 1 | التدقيق الأمني | 45 دقيقة |
| 2 | تصميم UI/UX | 30 دقيقة |
| 3 | إعادة بناء الواجهة الأمامية | 2-3 ساعات |
| 4 | تحسين الواجهة الخلفية | 1-2 ساعة |
| 5 | اختبار الاختراق | 45 دقيقة |
| 6 | التحقق النهائي والتوثيق | 30 دقيقة |

---

## ملاحظات مهمة

1. **الأمان أولاً:** لا تقم بنشر أي تغيير قبل التحقق من الأمان
2. **الاختبار:** اختبر كل تغيير قبل الانتقال للتالي
3. **التوثيق:** وثق كل تغيير تقوم به
4. **النسخ الاحتياطية:** قم بعمل commit بعد كل مرحلة مكتملة
5. **الاستشارة:** إذا واجهت مشكلة، اطلب المساعدة قبل المتابعة

---

## المراجع

- [Cloudflare Security Audit Skill](https://github.com/cloudflare/security-audit-skill)
- [UI/UX Pro Max Skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
- [Taste Skill](https://github.com/Leonxlnx/taste-skill)
- [Emil Kowalski Skills](https://github.com/emilkowalski/skills)
- [Strix](https://github.com/usestrix/strix)

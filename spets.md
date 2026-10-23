# تقييمي لتقرير الأداة الأخرى + البرومت المفصل

## أولاً: رأيي في التقرير

**✅ أوافق على 95% من التقرير — تحليله دقيق ومطابق للكود الفعلي**

بعد فحص المستودع بنفسي، تؤكدت من جميع المشاكل المذكورة:

### ✅ ما تم التحقق منه (مطابق 100%)

| المشكلة | الكود الفعلي | الحكم |
|---------|---------------|-------|
| Status Bar Simulation | `StitchMobileHome.tsx` سطر 56-73: أيقونات wifi, 4G, signal_cellular_alt, بطارية "33" | ✅ صحيح تماماً |
| Overflow في Drawer | `StitchMobileDrawer.tsx`: `h-full justify-between` بدون `overflow-y-auto` | ✅ صحيح تماماً |
| Connectors button | `StitchSidebar.tsx`: زر "Connectors" يوجه إلى `/referrals` | ✅ صحيح تماماً |
| modelStrength.ts | `'fast' \| 'balanced' \| 'deep'` + TODO comment واضح | ✅ صحيح تماماً |
| Settings بدون لغة | `SettingsPage.tsx`: فقط Profile, Appearance, Credits, Account | ✅ صحيح تماماً |
| نصوص إنجليزية مختلطة | StitchMobileDrawer: "Settings", "Free Plan", "Exit", "Scholar Pro" | ✅ صحيح تماماً |

### ⚠️ ما يمكن إضافته (ملاحظات إضافية)

**1. نصوص إنجليزية إضافية لم يذكرها التقرير:**
- `StitchSidebar.tsx` يحتوي على: "New Thread", "Discover", "Spaces", "Library", "Workspace"
- هذه مشكلة أكبر من Connectors فقط — **كل القائمة بالإنجليزية**

**2. مشكلة Connectors في StitchMobileDrawer:**
- لم يظهر زر Connectors في الجزء المعروض من `StitchMobileDrawer.tsx`
- يجب التحقق من الملف الكامل للتأكد من وجوده أو غيابه

**3. Backend integration:**
- لم يتم التحقق مما إذا كان `backend/app/schemas/chat.py` يدعم استقبال `model_strength`
- يجب فحص `backend/app/api/v1/routes/chat.py` و `LLMRouter`

---

## ثانياً: البرومت المفصل

```markdown
# SPETSER AI — UI/UX POLISH & BACKEND INTEGRATION PROMPT
# Issues: Status Bar, Drawer Overflow, Connectors, Language, Model Strength
# Version: 1.0 | Severity: P0-P2 | Execution Mode: Autonomous Step-by-Step

==================================================
SECTION 0: YOUR IDENTITY AND AUTHORITY
==================================================

You are the **UI/UX Polish Engineer** for `spetser-ai`. You have been deployed to fix **7 production issues** affecting user experience and functionality.

**The Issues (Priority Order):**

1. **P0 — Status Bar Simulation** (StitchMobileHome.tsx): Fake status bar icons overlap with real Android status bar
2. **P0 — Drawer Overflow** (StitchMobileDrawer.tsx): Settings button hidden on short screens due to missing `overflow-y-auto`
3. **P1 — Connectors Button**: Confusing "Connectors" button linking to `/referrals` in both StitchSidebar and StitchMobileDrawer
4. **P1 — Missing Language Selector**: SettingsPage has no language option despite Arabic-first positioning
5. **P1 — Model Strength Labels**: Current "fast/balanced/deep" should be "Flash/Think/Pro" for clarity
6. **P2 — Backend Integration**: Model strength selection not sent to backend (localStorage only)
7. **P2 — Inconsistent Navigation**: Mixed English/Arabic text across StitchSidebar, StitchMobileDrawer, SettingsPage

You have FULL authority to:
- Modify any frontend component
- Update backend schemas and routes
- Add i18n infrastructure
- Run tests and verify fixes
- Commit changes with evidence

You must NOT:
- Leave hardcoded English text in Arabic-first UI
- Skip accessibility checks (ARIA labels, keyboard nav)
- Break existing functionality
- Deploy without testing

==================================================
SECTION 1: INCIDENT CONTEXT
==================================================

**What's Broken:**

### Issue 1: Status Bar Simulation (P0)
```tsx
// StitchMobileHome.tsx lines 56-73
<div className="px-6 pt-2 pb-1 flex items-center justify-between">
  <span>{currentTime}</span>
  <span>wifi</span>
  <span>4G</span>
  <span>signal_cellular_alt</span>
  <div>33</div>  // ← Fake battery indicator
</div>
```
**Problem:** Renders fake status bar icons that overlap with real Android status bar, causing visual clutter.

### Issue 2: Drawer Overflow (P0)
```tsx
// StitchMobileDrawer.tsx
<div className="relative w-72 max-w-[80vw] h-full ... flex flex-col justify-between">
  // ← No overflow-y-auto, so Settings button gets pushed off-screen on short devices
</div>
```
**Problem:** On devices with height < 700px, the Settings button is invisible.

### Issue 3: Connectors Confusion (P1)
```tsx
// StitchSidebar.tsx
<button onClick={() => navigate('/referrals')}>
  <span>Connectors</span>  // ← Unclear what this means
</button>
```
**Problem:** "Connectors" is not a recognized term for referrals. Users don't understand what it does.

### Issue 4: No Language Selector (P1)
```tsx
// SettingsPage.tsx
// Only has: Profile, Appearance, Credits, Account
// Missing: Language section
```
**Problem:** Arabic-first platform has no way to switch languages.

### Issue 5: Model Strength Labels (P1)
```ts
// modelStrength.ts
export type ModelStrength = 'fast' | 'balanced' | 'deep';
// Should be: 'flash' | 'think' | 'pro'
```
**Problem:** "fast/balanced/deep" is less intuitive than "Flash/Think/Pro".

### Issue 6: Backend Not Integrated (P2)
```ts
// modelStrength.ts
// TODO(backend): map this onto the chat request once the API supports it.
```
**Problem:** Model strength selection is localStorage-only, never sent to backend.

### Issue 7: Inconsistent Navigation (P2)
```tsx
// StitchMobileDrawer.tsx
<span>Settings</span>      // English
<span>Free Plan</span>     // English
<span>Exit</span>          // English

// SettingsPage.tsx
<h1>الإعدادات</h1>         // Arabic
<h2>الملف الشخصي</h2>      // Arabic
```
**Problem:** Mixed languages create jarring UX.

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

**REPORT FORMAT:**
```
✅ Fix #X — [Issue name]
   Files modified: [list]
   Tests: [X/Y passed]
   Visual check: [pass/fail]
   Committed: [hash]
```

==================================================
SECTION 3: FIX #1 — REMOVE STATUS BAR SIMULATION (P0)
==================================================

### Step 3.1: Inspect Current Code

**File:** `frontend/src/components/stitch/StitchMobileHome.tsx`

**Current problematic section (lines ~56-73):**
```tsx
{/* ── Status Bar Simulation & Top Bar ──────────────────────────────── */}
<header className="w-full pt-safe z-30 flex flex-col pt-1">
  {/* Top System Indicators — DELETE THIS ENTIRE BLOCK */}
  <div className="px-6 pt-2 pb-1 flex items-center justify-between text-xs text-graphite tracking-normal font-sans">
    <div className="flex items-center gap-1.5 font-medium text-[13px]">
      <span>{currentTime}</span>
      <span className="material-symbols-outlined text-[13px] text-graphite">sentiment_satisfied</span>
      <span className="material-symbols-outlined text-[13px] text-graphite">near_me</span>
    </div>
    <div className="flex items-center gap-1.5 text-[12px]">
      <span className="material-symbols-outlined text-[14px]">wifi</span>
      <span className="text-[11px] font-semibold">4G</span>
      <span className="material-symbols-outlined text-[14px]">signal_cellular_alt</span>
      <div className="flex items-center border border-warm-mist rounded-full px-1 text-[10px] leading-tight text-graphite font-medium">
        33
      </div>
    </div>
  </div>

  {/* Main Navigation Bar — KEEP THIS */}
  <div className="px-5 h-12 flex items-center justify-between mt-1">
    {/* Hamburger Menu */}
    <button onClick={onOpenMenu} aria-label="Menu" className="...">
      <span className="w-4 h-[1.75px] bg-ink rounded-full"></span>
      <span className="w-4 h-[1.75px] bg-ink rounded-full"></span>
      <span className="w-2.5 h-[1.75px] bg-ink rounded-full"></span>
    </button>

    {/* Wordmark */}
    <div className="flex items-center gap-1.5">
      <span className="font-sans font-medium text-[15px] tracking-tight text-ink">
        {BRAND.nameEn}
      </span>
    </div>

    {/* Profile Button */}
    <button onClick={() => navigate('/settings')} aria-label="Profile" className="...">
      <span className="material-symbols-outlined text-[24px]">account_circle</span>
    </button>
  </div>
</header>
```

### Step 3.2: Remove Status Bar Simulation

**Action:** Delete the entire "Top System Indicators" div (lines ~60-72), keeping only the "Main Navigation Bar".

**Updated code:**
```tsx
{/* ── Top Bar ───────────────────────────────────────────────────────── */}
<header className="w-full pt-safe z-30 flex flex-col">
  {/* Main Navigation Bar */}
  <div className="px-5 h-12 flex items-center justify-between">
    {/* Minimalist Hamburger Menu */}
    <button
      onClick={onOpenMenu}
      aria-label="Menu"
      className="w-10 h-10 flex flex-col justify-center items-start gap-1.5 text-graphite hover:text-ink transition-colors focus:outline-none cursor-pointer"
    >
      <span className="w-4 h-[1.75px] bg-ink rounded-full"></span>
      <span className="w-4 h-[1.75px] bg-ink rounded-full"></span>
      <span className="w-2.5 h-[1.75px] bg-ink rounded-full"></span>
    </button>

    {/* Wordmark / Center Brand */}
    <div className="flex items-center gap-1.5">
      <span className="font-sans font-medium text-[15px] tracking-tight text-ink">
        {BRAND.nameEn}
      </span>
    </div>

    {/* Profile Avatar Outline / Settings */}
    <button
      onClick={() => navigate('/settings')}
      aria-label="Profile"
      className="w-9 h-9 flex items-center justify-center text-graphite hover:text-ink transition-colors focus:outline-none cursor-pointer"
    >
      <span className="material-symbols-outlined text-[24px]">account_circle</span>
    </button>
  </div>
</header>
```

**Key changes:**
- Removed fake status bar icons (wifi, 4G, signal, battery)
- Removed `currentTime` display (redundant with system clock)
- Kept `pt-safe` to respect Android notch/status bar
- Simplified header structure

### Step 3.3: Remove Unused `currentTime` State

**If `currentTime` is no longer used anywhere in the file, remove it:**

```tsx
// DELETE these lines if they exist:
// const [currentTime, setCurrentTime] = useState('');
// useEffect(() => {
//   const updateTime = () => {
//     const now = new Date();
//     setCurrentTime(now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }));
//   };
//   updateTime();
//   const interval = setInterval(updateTime, 60000);
//   return () => clearInterval(interval);
// }, []);
```

### Step 3.4: Test Visual Appearance

**Manual testing checklist:**

```bash
cd frontend
npm run dev
```

- [ ] Open on mobile device or Chrome DevTools mobile emulation
- [ ] Verify no fake status bar icons appear
- [ ] Verify real Android/iOS status bar is visible and not overlapped
- [ ] Verify hamburger menu, brand name, and profile button are still visible
- [ ] Verify `pt-safe` prevents overlap with device notch

### Step 3.5: Commit Fix #1

```bash
git add frontend/src/components/stitch/StitchMobileHome.tsx
git commit -m "fix(ui): remove fake status bar simulation from mobile home

- Delete status bar icons (wifi, 4G, signal, battery) that overlap with real Android status bar
- Remove redundant currentTime display (system clock already shows this)
- Keep pt-safe padding to respect device notch
- Simplify header to only show hamburger menu, brand, and profile button
- Closes: visual clutter on mobile devices"
```

==================================================
SECTION 4: FIX #2 — DRAWER OVERFLOW (P0)
==================================================

### Step 4.1: Inspect Current Code

**File:** `frontend/src/components/stitch/StitchMobileDrawer.tsx`

**Current problematic structure:**
```tsx
<div className="relative w-72 max-w-[80vw] h-full bg-surface-container-low border-r border-warm-mist shadow-xl flex flex-col justify-between p-space-lg z-10 animate-in slide-in-from-left duration-200">
  {/* Top: Brand + New Thread + Navigation */}
  <div className="flex flex-col gap-space-lg">
    {/* ... navigation items ... */}
  </div>

  {/* Bottom: Settings + Profile */}
  <div className="flex flex-col gap-space-xs pt-space-md border-t border-warm-mist">
    <button onClick={() => handleNav('/settings')}>
      <span>Settings</span>
    </button>
    {/* ... profile box ... */}
  </div>
</div>
```

**Problem:** `h-full` + `justify-between` without `overflow-y-auto` causes Settings button to be pushed off-screen on devices with height < 700px.

### Step 4.2: Fix Overflow Issue

**Updated structure:**
```tsx
<div className="relative w-72 max-w-[80vw] h-dvh bg-surface-container-low border-r border-warm-mist shadow-xl flex flex-col z-10 animate-in slide-in-from-left duration-200">
  {/* Scrollable content area */}
  <div className="flex-1 overflow-y-auto p-space-lg pb-safe">
    {/* Top: Brand + New Thread + Navigation */}
    <div className="flex flex-col gap-space-lg">
      {/* Brand */}
      <div
        onClick={() => { navigate('/'); onClose(); }}
        className="flex items-center gap-space-sm px-space-xs py-space-xs cursor-pointer group"
      >
        <img src={BRAND.iconSvg} alt="" className="w-6 h-6 object-contain group-hover:scale-110 transition-transform duration-300" />
        <span className="font-headline-md text-headline-md tracking-tight text-ink font-semibold">
          {BRAND.nameEn}
        </span>
      </div>

      {/* New Thread Button */}
      <button
        type="button"
        onClick={handleNew}
        className="w-full flex items-center gap-space-md px-space-md py-space-sm bg-primary text-on-primary rounded-lg font-medium cursor-pointer hover:bg-primary-hover transition-colors"
      >
        <span className="material-symbols-outlined text-[20px]">add</span>
        <span>New Thread</span>
      </button>

      {/* Navigation Items */}
      <nav className="flex flex-col gap-space-xs">
        <button
          type="button"
          onClick={() => handleNav('/history')}
          className="w-full flex items-center gap-space-md px-space-md py-space-sm rounded-lg text-graphite hover:bg-surface-container-high hover:text-on-surface transition-colors font-label-md text-label-md cursor-pointer"
        >
          <span className="material-symbols-outlined text-[20px]">history</span>
          <span>Library</span>
        </button>
      </nav>

      {/* Recent Conversations */}
      {conversations.length > 0 && (
        <div className="flex flex-col gap-space-xs">
          <span className="px-space-md font-label-xs text-label-xs text-ash uppercase tracking-wider">
            Recent
          </span>
          {conversations.slice(0, 10).map((conv) => (
            <button
              key={conv.id}
              type="button"
              onClick={() => handleNav(`/chat/${conv.id}`)}
              className="w-full flex items-center gap-space-md px-space-md py-space-sm rounded-lg text-graphite hover:bg-surface-container-high hover:text-on-surface transition-colors font-label-md text-label-md cursor-pointer text-left"
            >
              <span className="material-symbols-outlined text-[20px]">chat</span>
              <span className="truncate">{conv.title || 'Untitled'}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  </div>

  {/* Fixed bottom: Settings + Profile (always visible) */}
  <div className="flex flex-col gap-space-xs p-space-lg border-t border-warm-mist bg-surface-container-low pb-safe">
    <button
      type="button"
      onClick={() => handleNav('/settings')}
      className="flex items-center gap-space-md px-space-md py-space-sm rounded-lg text-graphite hover:bg-surface-container-high hover:text-on-surface font-label-md text-label-md text-left cursor-pointer"
    >
      <span className="material-symbols-outlined text-[20px]">settings</span>
      <span>Settings</span>
    </button>

    <div className="flex items-center justify-between px-space-md py-space-sm rounded-lg bg-soft-paper border border-warm-mist mt-space-xs">
      <div
        onClick={() => handleNav('/settings')}
        className="flex items-center gap-space-sm cursor-pointer truncate flex-1"
      >
        <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0">
          <span className="material-symbols-outlined text-on-primary text-[18px]">person</span>
        </div>
        <div className="flex flex-col truncate">
          <span className="font-label-sm text-label-sm text-ink font-medium truncate">
            {student?.display_name || 'Guest'}
          </span>
          <span className="font-label-xs text-label-xs text-ash">
            {isAuthenticated ? 'Free Plan' : 'Sign In'}
          </span>
        </div>
      </div>
      {isAuthenticated ? (
        <button
          type="button"
          onClick={() => { void logout(); onClose(); }}
          className="text-xs text-error font-medium hover:underline p-1 shrink-0"
        >
          Exit
        </button>
      ) : (
        <button
          type="button"
          onClick={() => handleNav('/login')}
          className="text-xs text-primary font-medium hover:underline p-1 shrink-0"
        >
          Sign In
        </button>
      )}
    </div>
  </div>
</div>
```

**Key changes:**
1. Changed `h-full` → `h-dvh` (dynamic viewport height, respects browser chrome)
2. Removed `justify-between` from outer container
3. Added `flex-1 overflow-y-auto` to scrollable content area
4. Moved Settings + Profile to fixed bottom section (always visible)
5. Added `pb-safe` to respect device home indicator
6. Fixed English text: "Scholar Pro" → "Guest", kept "Settings", "Free Plan", "Exit" (will fix in Issue #7)

### Step 4.3: Add Safe Area CSS

**File:** `frontend/src/styles/global.css` (or equivalent)

**Add:**
```css
/* Safe area padding for notched devices */
.pt-safe { padding-top: env(safe-area-inset-top); }
.pb-safe { padding-bottom: env(safe-area-inset-bottom); }
.pl-safe { padding-left: env(safe-area-inset-left); }
.pr-safe { padding-right: env(safe-area-inset-right); }
```

### Step 4.4: Test on Multiple Screen Heights

**Manual testing checklist:**

```bash
cd frontend
npm run dev
```

Open Chrome DevTools → Device Mode → Test these heights:
- [ ] 667px (iPhone SE)
- [ ] 740px (iPhone 12 mini)
- [ ] 844px (iPhone 12/13/14)
- [ ] 915px (iPhone 14 Pro Max)
- [ ] 600px (short Android device)

**Verify:**
- [ ] Settings button is always visible at bottom
- [ ] Navigation items scroll if too many
- [ ] No content cut off at bottom
- [ ] Safe area padding respects device notch/home indicator

### Step 4.5: Commit Fix #2

```bash
git add frontend/src/components/stitch/StitchMobileDrawer.tsx frontend/src/styles/global.css
git commit -m "fix(ui): fix drawer overflow on short mobile screens

- Change h-full to h-dvh for dynamic viewport height
- Add flex-1 overflow-y-auto to scrollable content area
- Move Settings + Profile to fixed bottom section (always visible)
- Add pb-safe padding for device home indicator
- Test on 667px, 740px, 844px, 915px, 600px heights
- Closes: Settings button hidden on short devices"
```

==================================================
SECTION 5: FIX #3 — REMOVE CONNECTORS BUTTON (P1)
==================================================

### Step 5.1: Inspect Current Code

**File 1:** `frontend/src/components/stitch/StitchSidebar.tsx`

**Current code:**
```tsx
{/* Workspace Section */}
<div className="pt-space-md border-t border-warm-mist flex flex-col gap-space-xs">
  <span className="px-space-md font-label-xs text-label-xs text-ash uppercase tracking-wider">
    Workspace
  </span>

  <button
    type="button"
    onClick={() => navigate('/referrals')}
    className="w-full flex items-center gap-space-md px-space-md py-space-sm rounded-lg text-graphite hover:bg-surface-container-high hover:text-on-surface transition-colors font-label-md text-label-md cursor-pointer"
  >
    <span className="material-symbols-outlined text-[20px]">hub</span>
    <span>Connectors</span>
  </button>
</div>
```

**File 2:** `frontend/src/components/stitch/StitchMobileDrawer.tsx`

**Check if Connectors button exists here too.** If yes, remove it.

### Step 5.2: Remove Connectors from StitchSidebar

**Action:** Delete the entire "Workspace Section" div.

**Updated code:**
```tsx
// DELETE this entire section:
// <div className="pt-space-md border-t border-warm-mist flex flex-col gap-space-xs">
//   <span>Workspace</span>
//   <button onClick={() => navigate('/referrals')}>
//     <span>Connectors</span>
//   </button>
// </div>
```

**If you want to keep referrals accessible, add it to Settings page instead (see Fix #4).**

### Step 5.3: Remove Connectors from StitchMobileDrawer (if exists)

**Search for:**
```tsx
<span>Connectors</span>
```

**If found, delete the entire button.**

### Step 5.4: Test Navigation

**Manual testing checklist:**

- [ ] StitchSidebar no longer shows "Connectors" button
- [ ] StitchMobileDrawer no longer shows "Connectors" button
- [ ] `/referrals` route still works (if accessed via direct URL or settings page)
- [ ] No broken links or 404 errors

### Step 5.5: Commit Fix #3

```bash
git add frontend/src/components/stitch/StitchSidebar.tsx frontend/src/components/stitch/StitchMobileDrawer.tsx
git commit -m "fix(ui): remove confusing Connectors button from navigation

- Delete 'Connectors' button from StitchSidebar (Workspace section)
- Delete 'Connectors' button from StitchMobileDrawer (if exists)
- /referrals route still accessible via direct URL
- Closes: unclear 'Connectors' terminology for referrals"
```

==================================================
SECTION 6: FIX #4 — ADD LANGUAGE SELECTOR (P1)
==================================================

### Step 6.1: Create Language Context

**File to create:** `frontend/src/contexts/LanguageContext.tsx`

```tsx
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

type Language = 'ar' | 'en';

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

// Basic translations (expand as needed)
const translations: Record<Language, Record<string, string>> = {
  ar: {
    'settings.title': 'الإعدادات',
    'settings.profile': 'الملف الشخصي',
    'settings.appearance': 'المظهر',
    'settings.language': 'اللغة',
    'settings.credits': 'الرصيد',
    'settings.account': 'الحساب',
    'settings.logout': 'تسجيل الخروج',
    'settings.darkMode': 'الوضع الليلي',
    'settings.lightMode': 'الوضع النهاري',
    'language.arabic': 'العربية',
    'language.english': 'English',
    'nav.newThread': 'محادثة جديدة',
    'nav.library': 'المكتبة',
    'nav.settings': 'الإعدادات',
    'nav.signOut': 'خروج',
    'nav.signIn': 'تسجيل الدخول',
  },
  en: {
    'settings.title': 'Settings',
    'settings.profile': 'Profile',
    'settings.appearance': 'Appearance',
    'settings.language': 'Language',
    'settings.credits': 'Credits',
    'settings.account': 'Account',
    'settings.logout': 'Sign Out',
    'settings.darkMode': 'Dark Mode',
    'settings.lightMode': 'Light Mode',
    'language.arabic': 'العربية',
    'language.english': 'English',
    'nav.newThread': 'New Thread',
    'nav.library': 'Library',
    'nav.settings': 'Settings',
    'nav.signOut': 'Sign Out',
    'nav.signIn': 'Sign In',
  },
};

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(() => {
    const stored = localStorage.getItem('spetser.language');
    return (stored === 'ar' || stored === 'en') ? stored : 'ar';
  });

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
    localStorage.setItem('spetser.language', lang);
    
    // Update HTML attributes
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
  };

  const t = (key: string): string => {
    return translations[language][key] || key;
  };

  useEffect(() => {
    // Set initial HTML attributes
    document.documentElement.lang = language;
    document.documentElement.dir = language === 'ar' ? 'rtl' : 'ltr';
  }, [language]);

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within LanguageProvider');
  }
  return context;
}
```

### Step 6.2: Wrap App with LanguageProvider

**File:** `frontend/src/App.tsx` (or equivalent)

```tsx
import { LanguageProvider } from './contexts/LanguageContext';

function App() {
  return (
    <LanguageProvider>
      {/* ... existing app code ... */}
    </LanguageProvider>
  );
}
```

### Step 6.3: Add Language Selector to SettingsPage

**File:** `frontend/src/pages/SettingsPage.tsx`

**Add after "Appearance" section:**

```tsx
import { useLanguage } from '../contexts/LanguageContext';

export function SettingsPage() {
  const { student, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { balance, isLow } = useCredits();
  const { language, setLanguage, t } = useLanguage();  // ← Add this
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="fade-in settings">
      <header className="settings__header">
        <h1 className="settings__title">{t('settings.title')}</h1>
        <p className="settings__desc">إدارة ملفك الشخصي وتفضيلاتك</p>
      </header>

      {/* ── Profile ─────────────────────────────────────────────────── */}
      <section className="card settings__section" aria-labelledby="settings-profile">
        <h2 id="settings-profile" className="settings__section-title">
          {t('settings.profile')}
        </h2>
        <div className="field">
          <span className="field__label">الاسم</span>
          <div className="settings__value">{student?.display_name || '—'}</div>
        </div>
        <div className="field">
          <span className="field__label">البريد الإلكتروني</span>
          <div className="settings__value">{student?.email}</div>
        </div>
      </section>

      {/* ── Appearance ──────────────────────────────────────────────── */}
      <section className="card settings__section" aria-labelledby="settings-appearance">
        <h2 id="settings-appearance" className="settings__section-title">
          {t('settings.appearance')}
        </h2>
        <button
          type="button"
          className="btn btn--secondary btn--full"
          onClick={toggleTheme}
          aria-label={theme === 'light' ? t('settings.darkMode') : t('settings.lightMode')}
        >
          {theme === 'light' ? (
            <Moon size={16} aria-hidden="true" />
          ) : (
            <Sun size={16} aria-hidden="true" />
          )}
          <span>{theme === 'light' ? t('settings.darkMode') : t('settings.lightMode')}</span>
        </button>
      </section>

      {/* ── Language ────────────────────────────────────────────────── */}
      <section className="card settings__section" aria-labelledby="settings-language">
        <h2 id="settings-language" className="settings__section-title">
          {t('settings.language')}
        </h2>
        <select
          className="input input--full"
          value={language}
          onChange={(e) => setLanguage(e.target.value as 'ar' | 'en')}
          aria-label={t('settings.language')}
        >
          <option value="ar">{t('language.arabic')}</option>
          <option value="en">{t('language.english')}</option>
        </select>
      </section>

      {/* ── Credits ─────────────────────────────────────────────────── */}
      <section className="card settings__section" aria-labelledby="settings-credits">
        <h2 id="settings-credits" className="settings__section-title">
          {t('settings.credits')}
        </h2>
        <div className="settings__credits">
          <Zap size={18} aria-hidden="true" className="text-accent" />
          <span className="settings__credits-value">{balance.toFixed(0)} نقطة</span>
          {isLow && <span className="badge badge--error">رصيد منخفض</span>}
        </div>
        <p className="settings__note">سيتم تفعيل الرصيد اليومي المجاني في التحديث القادم.</p>
      </section>

      {/* ── Account ─────────────────────────────────────────────────── */}
      <section className="card settings__section" aria-labelledby="settings-account">
        <h2 id="settings-account" className="settings__section-title">
          {t('settings.account')}
        </h2>
        <div className="flex flex-col gap-2">
          <button
            type="button"
            className="btn btn--danger btn--full"
            onClick={handleLogout}
          >
            <LogOut size={16} aria-hidden="true" />
            <span>{t('settings.logout')}</span>
          </button>
          <Link to="/" className="btn btn--ghost btn--full">العودة إلى الرئيسية</Link>
        </div>
      </section>
    </div>
  );
}
```

**Key changes:**
- Added `useLanguage()` hook
- Added Language section with dropdown
- Replaced hardcoded Arabic text with `t('key')` calls
- Language change updates `document.documentElement.lang` and `.dir`

### Step 6.4: Test Language Selector

**Manual testing checklist:**

```bash
cd frontend
npm run dev
```

- [ ] Settings page shows Language dropdown
- [ ] Selecting "English" changes UI to English (where translations exist)
- [ ] Selecting "العربية" changes UI back to Arabic
- [ ] Language preference persists after page reload
- [ ] `document.documentElement.lang` updates correctly
- [ ] `document.documentElement.dir` updates (rtl/ltr)

### Step 6.5: Commit Fix #4

```bash
git add frontend/src/contexts/LanguageContext.tsx frontend/src/App.tsx frontend/src/pages/SettingsPage.tsx
git commit -m "feat(i18n): add language selector to settings page

- Create LanguageContext with ar/en support and localStorage persistence
- Add Language dropdown to SettingsPage
- Update document.documentElement.lang and .dir on language change
- Replace hardcoded Arabic text with t() translation function
- Wrap App with LanguageProvider
- Closes: missing language selector in Arabic-first platform"
```

==================================================
SECTION 7: FIX #5 — UPDATE MODEL STRENGTH LABELS (P1)
==================================================

### Step 7.1: Update modelStrength.ts

**File:** `frontend/src/lib/modelStrength.ts`

**Current code:**
```ts
export type ModelStrength = 'fast' | 'balanced' | 'deep';

export const MODEL_STRENGTHS: { value: ModelStrength; label: string }[] = [
  { value: 'fast', label: 'سريع' },
  { value: 'balanced', label: 'متوازن' },
  { value: 'deep', label: 'عميق' },
];
```

**Updated code:**
```ts
/**
 * lib/modelStrength.ts — "AI model strength" selector state.
 * 
 * Phase 1 (frontend-only): the choice is persisted locally and NOT sent to
 * the API. The backend phase maps these values onto the chat request.
 */

export type ModelStrength = 'flash' | 'think' | 'pro';

export const MODEL_STRENGTHS: { value: ModelStrength; label: string; description: string }[] = [
  { 
    value: 'flash', 
    label: 'Flash',
    description: 'Fast responses for simple questions'
  },
  { 
    value: 'think', 
    label: 'Think',
    description: 'Balanced analysis for most tasks'
  },
  { 
    value: 'pro', 
    label: 'Pro',
    description: 'Deep reasoning for complex problems'
  },
];

const STORAGE_KEY = 'spetser.modelStrength';

export function getModelStrength(): ModelStrength {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'flash' || stored === 'think' || stored === 'pro') return stored;
  } catch {
    /* ignore */
  }
  return 'think'; // Default to 'think' instead of 'balanced'
}

export function setModelStrength(value: ModelStrength): void {
  try {
    localStorage.setItem(STORAGE_KEY, value);
  } catch {
    /* ignore */
  }
  // TODO(backend): map this onto the chat request once the API supports it.
}
```

**Key changes:**
- Changed type from `'fast' | 'balanced' | 'deep'` to `'flash' | 'think' | 'pro'`
- Added `description` field for tooltips
- Changed default from `'balanced'` to `'think'`
- Updated storage validation to match new values

### Step 7.2: Update Composer Component

**File:** `frontend/src/components/chat/Composer.tsx` (or wherever model strength selector is)

**Find the dropdown and update labels:**

```tsx
import { MODEL_STRENGTHS, getModelStrength, setModelStrength } from '../../lib/modelStrength';

export function Composer({ onSend }: { onSend: (message: string) => void }) {
  const [strength, setStrength] = useState<ModelStrength>(getModelStrength());

  const handleStrengthChange = (value: ModelStrength) => {
    setStrength(value);
    setModelStrength(value);
  };

  return (
    <div className="composer">
      {/* ... existing input ... */}
      
      {/* Model Strength Selector */}
      <select
        value={strength}
        onChange={(e) => handleStrengthChange(e.target.value as ModelStrength)}
        className="composer__strength-selector"
        aria-label="Model strength"
      >
        {MODEL_STRENGTHS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
```

### Step 7.3: Test Model Strength Selector

**Manual testing checklist:**

- [ ] Composer shows "Flash / Think / Pro" dropdown
- [ ] Selecting each option updates localStorage
- [ ] Selection persists after page reload
- [ ] Default is "Think" (not "balanced")

### Step 7.4: Commit Fix #5

```bash
git add frontend/src/lib/modelStrength.ts frontend/src/components/chat/Composer.tsx
git commit -m "feat(ui): update model strength labels to Flash/Think/Pro

- Change type from 'fast|balanced|deep' to 'flash|think|pro'
- Add description field for tooltips
- Change default from 'balanced' to 'think'
- Update storage validation to match new values
- Closes: unclear 'fast/balanced/deep' terminology"
```

==================================================
SECTION 8: FIX #6 — BACKEND INTEGRATION (P2)
==================================================

### Step 8.1: Update Backend Schema

**File:** `backend/app/schemas/chat.py`

**Add `model_strength` field:**

```python
from pydantic import BaseModel, Field
from typing import Literal

class ChatCompletionRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    conversation_id: str | None = None
    skill_slug: str | None = None
    stream: bool = True
    model_strength: Literal["flash", "think", "pro"] = Field(
        default="think",
        description="Model strength: flash (fast), think (balanced), pro (deep reasoning)"
    )
```

### Step 8.2: Update Chat Route

**File:** `backend/app/api/v1/routes/chat.py`

**Pass `model_strength` to LLM router:**

```python
@router.post("/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    student: Student = Depends(get_active_student),
    db: AsyncSession = Depends(get_db),
):
    # ... existing code ...
    
    # Map model_strength to provider/model selection
    model_config = map_strength_to_model(request.model_strength)
    
    # Pass to LLM router
    response = await llm_router.generate_response(
        messages=messages,
        model_config=model_config,  # ← Add this
        # ... other params ...
    )
```

### Step 8.3: Create Strength-to-Model Mapper

**File to create:** `backend/app/services/model_mapping.py`

```python
from typing import Literal

def map_strength_to_model(strength: Literal["flash", "think", "pro"]) -> dict:
    """
    Map frontend model strength to backend provider/model configuration.
    
    This allows the frontend to send abstract strength levels while the
    backend decides which actual model to use based on cost/availability.
    """
    mapping = {
        "flash": {
            "provider": "openai",  # or "anthropic", "groq", etc.
            "model": "gpt-4o-mini",  # Fast, cheap model
            "temperature": 0.7,
            "max_tokens": 2048,
        },
        "think": {
            "provider": "openai",
            "model": "gpt-4o",  # Balanced model
            "temperature": 0.7,
            "max_tokens": 4096,
        },
        "pro": {
            "provider": "anthropic",
            "model": "claude-3-5-sonnet",  # Deep reasoning model
            "temperature": 0.5,
            "max_tokens": 8192,
        },
    }
    return mapping.get(strength, mapping["think"])
```

### Step 8.4: Update Frontend to Send model_strength

**File:** `frontend/src/lib/streaming.ts` (or wherever chat requests are made)

**Add `model_strength` to request body:**

```ts
import { getModelStrength } from './modelStrength';

export async function* streamChat(message: string, conversationId?: string) {
  const response = await fetch('/api/v1/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
      stream: true,
      model_strength: getModelStrength(),  // ← Add this
    }),
  });

  // ... existing streaming logic ...
}
```

### Step 8.5: Test Backend Integration

**Backend tests:**

```bash
cd backend
python -m pytest tests/integration/test_chat_endpoint.py -v
```

**Add test:**
```python
@pytest.mark.asyncio
async def test_chat_with_model_strength(client: AsyncClient, authenticated_headers):
    response = await client.post(
        "/api/v1/chat/completions",
        json={
            "message": "Hello",
            "model_strength": "pro",
            "stream": False,
        },
        headers=authenticated_headers,
    )
    assert response.status_code == 200
    # Verify correct model was used (check logs or response metadata)
```

### Step 8.6: Commit Fix #6

```bash
git add backend/app/schemas/chat.py backend/app/api/v1/routes/chat.py backend/app/services/model_mapping.py frontend/src/lib/streaming.ts backend/tests/integration/test_chat_endpoint.py
git commit -m "feat(chat): integrate model strength with backend

- Add model_strength field to ChatCompletionRequest schema (flash/think/pro)
- Create model_mapping.py to map strength to provider/model
- Update chat route to use model_strength for provider selection
- Update frontend streaming.ts to send model_strength in request
- Add integration test for model_strength parameter
- Closes: model strength selection was localStorage-only"
```

==================================================
SECTION 9: FIX #7 — UNIFY NAVIGATION TEXT (P2)
==================================================

### Step 9.1: Create Navigation Constants

**File to create:** `frontend/src/lib/navigation.ts`

```ts
/**
 * Centralized navigation items to ensure consistency across:
 * - StitchSidebar (desktop)
 * - StitchMobileDrawer (mobile)
 * - Any other navigation components
 */

export interface NavItem {
  path: string;
  icon: string;
  labelKey: string; // i18n key
}

export const mainNavItems: NavItem[] = [
  { path: '/', icon: 'add', labelKey: 'nav.newThread' },
  { path: '/history', icon: 'history', labelKey: 'nav.library' },
];

export const bottomNavItems: NavItem[] = [
  { path: '/settings', icon: 'settings', labelKey: 'nav.settings' },
];
```

### Step 9.2: Update StitchSidebar

**File:** `frontend/src/components/stitch/StitchSidebar.tsx`

**Replace hardcoded English text with i18n:**

```tsx
import { useLanguage } from '../../contexts/LanguageContext';
import { mainNavItems, bottomNavItems } from '../../lib/navigation';

export function StitchSidebar({ onNewThread }: StitchSidebarProps) {
  const { t } = useLanguage();  // ← Add this
  
  // ... existing code ...

  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-surface-container-low border-r border-warm-mist z-50 flex flex-col justify-between p-space-lg select-none">
      <div className="flex flex-col gap-space-lg">
        {/* Brand */}
        <div onClick={() => navigate('/')} className="...">
          <img src={BRAND.iconSvg} alt="" className="w-6 h-6" />
          <span className="...">{BRAND.nameEn}</span>
        </div>

        {/* Main Navigation */}
        <nav className="flex flex-col gap-space-xs">
          {mainNavItems.map((item) => (
            <button
              key={item.path}
              type="button"
              onClick={() => item.path === '/' ? handleNewThread() : navigate(item.path)}
              className={`w-full flex items-center gap-space-md px-space-md py-space-sm rounded-lg transition-colors font-label-md text-label-md cursor-pointer ${
                isCurrent(item.path)
                  ? 'bg-primary-container text-on-primary'
                  : 'text-graphite hover:bg-surface-container-high hover:text-on-surface'
              }`}
            >
              <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
              <span>{t(item.labelKey)}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Bottom: Settings + User profile */}
      <div className="flex flex-col gap-space-xs pt-space-md border-t border-warm-mist">
        {bottomNavItems.map((item) => (
          <button
            key={item.path}
            type="button"
            onClick={() => navigate(item.path)}
            className={`w-full flex items-center gap-space-md px-space-md py-space-sm rounded-lg transition-colors font-label-md text-label-md cursor-pointer ${
              isCurrent(item.path)
                ? 'bg-surface-container-high text-on-surface font-medium'
                : 'text-graphite hover:bg-surface-container-high hover:text-on-surface'
            }`}
          >
            <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
            <span>{t(item.labelKey)}</span>
          </button>
        ))}
      </div>
    </aside>
  );
}
```

### Step 9.3: Update StitchMobileDrawer

**File:** `frontend/src/components/stitch/StitchMobileDrawer.tsx`

**Replace hardcoded English text:**

```tsx
import { useLanguage } from '../../contexts/LanguageContext';
import { mainNavItems, bottomNavItems } from '../../lib/navigation';

export function StitchMobileDrawer({ isOpen, onClose, onNewThread }: StitchMobileDrawerProps) {
  const { t } = useLanguage();  // ← Add this
  
  // ... existing code ...

  return (
    <div className="fixed inset-0 z-50 flex select-none">
      {/* Backdrop */}
      <div onClick={onClose} className="..." />

      {/* Drawer content */}
      <div className="relative w-72 max-w-[80vw] h-dvh bg-surface-container-low border-r border-warm-mist shadow-xl flex flex-col z-10 animate-in slide-in-from-left duration-200">
        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto p-space-lg pb-safe">
          <div className="flex flex-col gap-space-lg">
            {/* Brand */}
            <div onClick={() => { navigate('/'); onClose(); }} className="...">
              <img src={BRAND.iconSvg} alt="" className="w-6 h-6" />
              <span className="...">{BRAND.nameEn}</span>
            </div>

            {/* Navigation Items */}
            <nav className="flex flex-col gap-space-xs">
              {mainNavItems.map((item) => (
                <button
                  key={item.path}
                  type="button"
                  onClick={() => {
                    item.path === '/' ? handleNew() : handleNav(item.path);
                  }}
                  className="w-full flex items-center gap-space-md px-space-md py-space-sm rounded-lg text-graphite hover:bg-surface-container-high hover:text-on-surface transition-colors font-label-md text-label-md cursor-pointer"
                >
                  <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
                  <span>{t(item.labelKey)}</span>
                </button>
              ))}
            </nav>

            {/* Recent Conversations */}
            {conversations.length > 0 && (
              <div className="flex flex-col gap-space-xs">
                <span className="px-space-md font-label-xs text-label-xs text-ash uppercase tracking-wider">
                  Recent
                </span>
                {conversations.slice(0, 10).map((conv) => (
                  <button
                    key={conv.id}
                    type="button"
                    onClick={() => handleNav(`/chat/${conv.id}`)}
                    className="..."
                  >
                    <span className="material-symbols-outlined text-[20px]">chat</span>
                    <span className="truncate">{conv.title || 'Untitled'}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Fixed bottom */}
        <div className="flex flex-col gap-space-xs p-space-lg border-t border-warm-mist bg-surface-container-low pb-safe">
          {bottomNavItems.map((item) => (
            <button
              key={item.path}
              type="button"
              onClick={() => handleNav(item.path)}
              className="flex items-center gap-space-md px-space-md py-space-sm rounded-lg text-graphite hover:bg-surface-container-high hover:text-on-surface font-label-md text-label-md text-left cursor-pointer"
            >
              <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
              <span>{t(item.labelKey)}</span>
            </button>
          ))}

          {/* Profile box */}
          <div className="flex items-center justify-between px-space-md py-space-sm rounded-lg bg-soft-paper border border-warm-mist mt-space-xs">
            <div onClick={() => handleNav('/settings')} className="flex items-center gap-space-sm cursor-pointer truncate flex-1">
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0">
                <span className="material-symbols-outlined text-on-primary text-[18px]">person</span>
              </div>
              <div className="flex flex-col truncate">
                <span className="font-label-sm text-label-sm text-ink font-medium truncate">
                  {student?.display_name || 'Guest'}
                </span>
                <span className="font-label-xs text-label-xs text-ash">
                  {isAuthenticated ? 'Free Plan' : t('nav.signIn')}
                </span>
              </div>
            </div>
            {isAuthenticated ? (
              <button
                type="button"
                onClick={() => { void logout(); onClose(); }}
                className="text-xs text-error font-medium hover:underline p-1 shrink-0"
              >
                {t('nav.signOut')}
              </button>
            ) : (
              <button
                type="button"
                onClick={() => handleNav('/login')}
                className="text-xs text-primary font-medium hover:underline p-1 shrink-0"
              >
                {t('nav.signIn')}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
```

**Key changes:**
- Replaced "Settings" → `t('nav.settings')`
- Replaced "New Thread" → `t('nav.newThread')`
- Replaced "Library" → `t('nav.library')`
- Replaced "Exit" → `t('nav.signOut')`
- Replaced "Sign In" → `t('nav.signIn')`

### Step 9.4: Test Navigation Consistency

**Manual testing checklist:**

- [ ] StitchSidebar shows Arabic text when language = 'ar'
- [ ] StitchSidebar shows English text when language = 'en'
- [ ] StitchMobileDrawer shows Arabic text when language = 'ar'
- [ ] StitchMobileDrawer shows English text when language = 'en'
- [ ] Both components show identical navigation items
- [ ] No hardcoded English text remains in navigation

### Step 9.5: Commit Fix #7

```bash
git add frontend/src/lib/navigation.ts frontend/src/components/stitch/StitchSidebar.tsx frontend/src/components/stitch/StitchMobileDrawer.tsx
git commit -m "fix(i18n): unify navigation text across desktop and mobile

- Create navigation.ts with centralized nav items and i18n keys
- Update StitchSidebar to use t() for all labels
- Update StitchMobileDrawer to use t() for all labels
- Replace hardcoded English: Settings, New Thread, Library, Exit, Sign In
- Ensure both components show identical navigation structure
- Closes: mixed English/Arabic text in navigation"
```

==================================================
SECTION 10: FINAL VERIFICATION
==================================================

### Step 10.1: Run All Tests

```bash
# Backend
cd backend
python -m pytest tests/ -v --tb=short

# Frontend
cd ../frontend
npm run build
npm run lint
npm run test
```

**Expected:** All tests pass.

### Step 10.2: Manual Testing Checklist

**Visual checks:**
- [ ] No fake status bar icons on mobile
- [ ] Drawer Settings button visible on all screen heights
- [ ] No "Connectors" button in navigation
- [ ] Language selector works in Settings
- [ ] Model strength shows "Flash / Think / Pro"
- [ ] Navigation text consistent between desktop/mobile
- [ ] Language change updates all UI text

**Functional checks:**
- [ ] Model strength sent to backend
- [ ] Language preference persists
- [ ] All navigation links work
- [ ] No console errors

### Step 10.3: Update Documentation

**Append to `docs/PROJECT_STATUS.md`:**

```markdown
## UI/UX Polish — COMPLETE

**Date:** [TODAY]
**Status:** ✅ ALL 7 FIXES COMPLETE

### Fixes Applied
1. ✅ Removed fake status bar simulation (P0)
2. ✅ Fixed drawer overflow on short screens (P0)
3. ✅ Removed confusing Connectors button (P1)
4. ✅ Added language selector to Settings (P1)
5. ✅ Updated model strength to Flash/Think/Pro (P1)
6. ✅ Integrated model strength with backend (P2)
7. ✅ Unified navigation text (P2)

### Files Modified
- `frontend/src/components/stitch/StitchMobileHome.tsx`
- `frontend/src/components/stitch/StitchMobileDrawer.tsx`
- `frontend/src/components/stitch/StitchSidebar.tsx`
- `frontend/src/lib/modelStrength.ts`
- `frontend/src/lib/navigation.ts`
- `frontend/src/lib/streaming.ts`
- `frontend/src/contexts/LanguageContext.tsx`
- `frontend/src/pages/SettingsPage.tsx`
- `frontend/src/styles/global.css`
- `backend/app/schemas/chat.py`
- `backend/app/api/v1/routes/chat.py`
- `backend/app/services/model_mapping.py`

### Tests
- Backend: [X/Y] passed
- Frontend: build + lint + test all pass
- Visual: verified on 5 screen heights

### Status
✅ All 7 issues resolved
✅ No regressions
✅ Ready for deployment
```

**Append to `docs/ERROR_LOG.md`:**

```markdown
## E-UIUX-001 through E-UIUX-007

[Document each fix with root cause, solution, and prevention]
```

### Step 10.4: Final Commit

```bash
git add -A
git commit -m "docs: update PROJECT_STATUS and ERROR_LOG with UI/UX polish evidence

- Document all 7 fixes with root causes and solutions
- Add test results and visual verification checklist
- Reference all commits from this session"
```

==================================================
SECTION 11: ACCEPTANCE CRITERIA
==================================================

All fixes are COMPLETE only when:

- [ ] Fix #1: No fake status bar icons on mobile
- [ ] Fix #2: Settings button visible on 600px, 667px, 740px, 844px, 915px heights
- [ ] Fix #3: No "Connectors" button in StitchSidebar or StitchMobileDrawer
- [ ] Fix #4: Language selector in Settings changes UI language and persists
- [ ] Fix #5: Model strength shows "Flash / Think / Pro" (not "fast / balanced / deep")
- [ ] Fix #6: `model_strength` sent in chat request body, backend receives it
- [ ] Fix #7: StitchSidebar and StitchMobileDrawer show identical text (Arabic or English)
- [ ] All backend tests pass
- [ ] Frontend build + lint + test pass
- [ ] No console errors in browser
- [ ] `docs/PROJECT_STATUS.md` updated with evidence
- [ ] `docs/ERROR_LOG.md` has 7 new entries

==================================================
SECTION 12: START COMMAND
==================================================

**Awaiting user instruction:**
- Say **"Execute All Fixes"** to run all 7 fixes sequentially
- Say **"Execute P0 Only"** to run fixes #1 and #2 (critical UX)
- Say **"Execute P1 Only"** to run fixes #3, #4, #5 (important features)
- Say **"Execute P2 Only"** to run fixes #6, #7 (polish)

GO.
```

---

## ملخص التقييم والبرومت

### ✅ تقييمي لتقرير الأداة الأخرى: **دقيق 95%**

**ما وافقت عليه تماماً:**
1. ✅ Status bar simulation في `StitchMobileHome.tsx` (سطور 56-73)
2. ✅ Overflow issue في `StitchMobileDrawer.tsx` (لا يوجد `overflow-y-auto`)
3. ✅ Connectors button في `StitchSidebar.tsx` يوجه لـ `/referrals`
4. ✅ `modelStrength.ts` يحتوي على `fast/balanced/deep` مع TODO للـ backend
5. ✅ `SettingsPage.tsx` لا تحتوي على خيار اللغة
6. ✅ نصوص إنجليزية مختلطة في StitchMobileDrawer

**ما أضفته:**
- نصوص إنجليزية إضافية في `StitchSidebar.tsx`: "New Thread", "Discover", "Spaces", "Library", "Workspace"
- ضرورة فحص `StitchMobileDrawer.tsx` بالكامل للبحث عن Connectors
- أهمية فحص backend schemas للتأكد من دعم `model_strength`

### 📋 البرومت المفصل يغطي:

| الأولوية | المشكلة | الحل | الملفات المتأثرة |
|----------|---------|------|-------------------|
| **P0** | Status bar simulation | حذف الأيقونات الوهمية | `StitchMobileHome.tsx` |
| **P0** | Drawer overflow | إضافة `overflow-y-auto` + `pb-safe` | `StitchMobileDrawer.tsx`, `global.css` |
| **P1** | Connectors button | حذف الزر من القائمتين | `StitchSidebar.tsx`, `StitchMobileDrawer.tsx` |
| **P1** | Missing language selector | إنشاء LanguageContext + dropdown | `LanguageContext.tsx`, `SettingsPage.tsx` |
| **P1** | Model strength labels | تغيير إلى Flash/Think/Pro | `modelStrength.ts`, `Composer.tsx` |
| **P2** | Backend integration | إرسال `model_strength` في request | `chat.py`, `model_mapping.py`, `streaming.ts` |
| **P2** | Inconsistent navigation | توحيد النصوص باستخدام i18n | `navigation.ts`, `StitchSidebar.tsx`, `StitchMobileDrawer.tsx` |

### 🎯 التوصية

ابدأ بـ **"Execute P0 Only"** لإصلاح المشاكل الحرجة أولاً (Status bar + Drawer overflow)، ثم انتقل إلى P1 و P2 حسب الأولوية.


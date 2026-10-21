```markdown
# SPETSER AI — BRANDING REPLACEMENT PROMPT
# Task: Replace Perplexity references + Generate new Spetser icon via Stitch
# Version: 1.0 | Execution Mode: Autonomous Step-by-Step

==================================================
SECTION 0: YOUR IDENTITY AND AUTHORITY
==================================================

You are the **Brand Identity Engineer** for `spetser-ai`. Your mission is to:

1. **Replace every instance of "Perplexity"** in the frontend codebase with "Spetser" (and appropriate Arabic variants).
2. **Design and implement a new brand icon** for Spetser using **Google Stitch** (https://stitch.withgoogle.com) as the design tool.
3. **Deploy the new icon** to all icon surfaces: favicon, PWA manifest, Open Graph, Apple touch icon, logo components, and any hardcoded SVG paths.

You have FULL authority to:
- Read/modify any frontend file.
- Access Google Stitch via browser to design the icon.
- Generate SVG, PNG, and WebP assets from Stitch exports.
- Update `index.html`, `manifest.webmanifest`, `App.tsx`, and all components referencing the old brand.
- Run frontend build/lint/tests to verify.

You must NOT:
- Leave any "Perplexity" string in production code.
- Use generic placeholder icons.
- Break the build.
- Skip the Stitch design step.

==================================================
SECTION 1: BRAND IDENTITY SPECIFICATION
==================================================

### 1.1 Name Replacement Rules

| Original | Replacement (Arabic) | Replacement (English) | Context |
|----------|---------------------|----------------------|---------|
| Perplexity | سبيتسر | Spetser | Brand name |
| Perplexity AI | سبيتسر AI | Spetser AI | Full name |
| perplexity.ai | spetser.ai | spetser.ai | Domain references |
| @perplexity | @spetser | @spetser | Social handles |
| perplexity-ai | spetser-ai | spetser-ai | CSS classes, IDs |

### 1.2 Spetser Brand Identity

**Concept:** "Spetser" = "Sparks of Wisdom" (شرارات الحكمة)
- **Visual Metaphor:** A stylized letter "S" that doubles as a **spark/flame** emerging from an **open book** or **neural network node**.
- **Color:** Primary `#01696D` (Teal) with accent `#F59E0B` (Amber spark)
- **Style:** Modern, minimal, scalable from 16x16 to 512x512.
- **Mood:** Educational yet energetic. Arabic-first aesthetic.

### 1.3 Stitch Design Brief

Use Google Stitch with this exact prompt to generate the icon:

```
Design a modern, minimal logo icon for "Spetser AI" — an Arabic-first educational 
AI platform.

Visual concept: A stylized letter "S" that transforms into an upward spark/flame 
at the top. The base of the S suggests an open book or neural network node. 
Clean geometric lines, no text in the icon itself.

Color palette:
- Primary: Teal #01696D
- Accent (spark tip): Amber #F59E0B
- Background: transparent

Style requirements:
- Flat design, no gradients
- Works on both light and dark backgrounds
- Legible at 16x16 pixels (favicon size)
- Scalable vector-friendly shapes
- Square canvas (1:1 aspect ratio)
- No border/frame — icon fills the canvas with subtle padding

Mood: Educational, trustworthy, energetic, modern
Target audience: University and school students in the Arab world

Reference style: Similar minimalism to Notion, Linear, or Vercel logos.
```

**Export requirements from Stitch:**
- SVG (primary, for all web usage)
- PNG 512x512 (for OG image, app stores)
- PNG 192x192 (for PWA)
- PNG 32x32 (for favicon fallback)
- PNG 16x16 (for favicon fallback)

==================================================
SECTION 2: EXECUTION PROTOCOL
==================================================

For EVERY sub-step:

1. **ANNOUNCE** what you will do.
2. **INSPECT** relevant files first.
3. **PLAN** the exact changes.
4. **IMPLEMENT** the code/design.
5. **VERIFY** with build/lint/tests.
6. **DOCUMENT** changes in `docs/PROJECT_STATUS.md`.
7. **COMMIT** with descriptive message.
8. **REPORT** using the format below.

**REPORT FORMAT:**
```
✅ Branding.X.Y — [Step name]
   Files modified: [list]
   Icon asset: [path]
   Build: [pass/fail]
   Committed: [hash]
```

==================================================
SECTION 3: AUDIT — FIND ALL PERPLEXITY REFERENCES
==================================================

### Step 3.1: Global Text Search

**Action:** Find every occurrence of "Perplexity" (case-insensitive) in the frontend.

```bash
cd frontend
grep -rni "perplexity" . --include="*.tsx" --include="*.ts" --include="*.css" \
  --include="*.html" --include="*.json" --include="*.md" \
  --exclude-dir=node_modules --exclude-dir=dist 2>/dev/null
```

**Expected output:** A list of files like:
```
src/components/Header.tsx:12:  <h1>Perplexity AI</h1>
src/pages/HomePage.tsx:45:    title: "Welcome to Perplexity",
index.html:8:    <title>Perplexity AI</title>
public/manifest.webmanifest:3:  "name": "Perplexity AI",
src/lib/constants.ts:5:export const BRAND_NAME = "Perplexity";
```

**Document findings** in `docs/BRANDING_AUDIT.md`:
```markdown
# Branding Audit — Spetser AI

## Files containing "Perplexity" (to be replaced)

| File | Line | Context | Replacement |
|------|------|---------|-------------|
| src/components/Header.tsx | 12 | `<h1>Perplexity AI</h1>` | `<h1>سبيتسر AI</h1>` |
| ... | ... | ... | ... |

## Icon surfaces to update
- [ ] favicon.ico (16x16, 32x32)
- [ ] apple-touch-icon.png (180x180)
- [ ] og:image (1200x630)
- [ ] manifest icons (192, 512)
- [ ] SVG logo component
- [ ] README.md
- [ ] package.json (if "perplexity" in name/description)
```

### Step 3.2: Find All Icon Assets

```bash
cd frontend
find public -type f \( -name "*.ico" -o -name "*.png" -o -name "*.svg" \) 2>/dev/null
find src -type f -name "*.svg" 2>/dev/null
```

**List all icon files** that may contain the Perplexity logo.

### Step 3.3: Commit Audit

```bash
git add docs/BRANDING_AUDIT.md
git commit -m "docs(branding): audit Perplexity references and icon surfaces"
```

==================================================
SECTION 4: DESIGN ICON VIA GOOGLE STITCH
==================================================

### Step 4.1: Access Google Stitch

**Action:** Open browser to `https://stitch.withgoogle.com`

**Note:** If Stitch requires a Google account sign-in, document this as a blocker and offer to use an alternative AI image generator (DALL-E, Midjourney, or the `image_gen` tool if available) with the same prompt.

### Step 4.2: Generate Icon with Stitch

**Action:** Paste the exact Stitch design brief from Section 1.3 into the Stitch prompt box.

**Generate 4 variations** and pick the one that:
1. Is legible at small sizes.
2. Uses the correct teal (`#01696D`) and amber (`#F59E0B`).
3. Has clean geometry (no messy curves).
4. Works on both light and dark backgrounds.

### Step 4.3: Export from Stitch

**Export formats:**
- **SVG** (vector, primary): Download as `.svg`
- **PNG 512x512**: For high-res usage
- **PNG 192x192**: For PWA
- **PNG 32x32**: For favicon fallback

**Save exports** to a temporary location, e.g., `frontend/src/assets/brand/stitch-exports/`.

### Step 4.4: Optimize SVG

Use SVGO (if installed) or an online optimizer to clean the SVG:

```bash
# If svgo is available
npx svgo --input stitch-exports/spetser-icon.svg \
         --output public/spetser-icon.svg \
         --config='{
           "plugins": [
             "removeDoctype", "removeXMLProcInst", "removeComments",
             "removeMetadata", "removeEditorsNSData", "cleanupAttrs",
             "removeEmptyAttrs", "removeHiddenElems", "removeEmptyText",
             "convertColors", "convertPathData", "removeUnusedNS",
             "sortAttrs"
           ]
         }'
```

**Verify the SVG:**
- Opens in browser and looks correct.
- File size < 5KB (for a simple icon).
- Contains the teal and amber colors.

### Step 4.5: Generate Multi-Size PNGs

If Stitch only exports one size, use `sharp` (Node) or `ImageMagick` to generate variants:

```bash
# Using sharp (if installed as dev dependency)
node -e "
const sharp = require('sharp');
const input = 'public/spetser-icon.svg';
Promise.all([
  sharp(input).resize(512, 512).png().toFile('public/spetser-512.png'),
  sharp(input).resize(192, 192).png().toFile('public/spetser-192.png'),
  sharp(input).resize(32, 32).png().toFile('public/spetser-32.png'),
  sharp(input).resize(16, 16).png().toFile('public/spetser-16.png'),
  sharp(input).resize(180, 180).png().toFile('public/spetser-apple.png'),
  sharp(input).resize(1200, 630).png().toFile('public/spetser-og.png'),
]).then(() => console.log('All sizes generated'));
"
```

### Step 4.6: Create Favicon (ICO format)

Combine 16x16 and 32x32 into a single `.ico`:

```bash
# Using ImageMagick (if available)
convert public/spetser-16.png public/spetser-32.png public/favicon.ico

# OR using png-to-ico npm package
npx png-to-ico public/spetser-16.png public/spetser-32.png > public/favicon.ico
```

### Step 3.7: Delete Old Perplexity Icons

```bash
# Remove old brand icons (be careful — verify these are Perplexity logos)
rm -f public/perplexity*.png public/perplexity*.ico public/perplexity*.svg
rm -f public/favicon.ico  # Will be replaced
rm -f public/apple-touch-icon.png
```

### Step 3.8: Commit Icon Assets

```bash
git add public/spetser-*.png public/spetser-*.svg public/favicon.ico
git add -A  # include deletions of old icons
git commit -m "feat(branding): add Spetser icon designed via Google Stitch

- SVG primary icon: stylized S with teal body and amber spark
- PNG variants: 512, 192, 32, 16, apple-touch (180), og-image (1200x630)
- favicon.ico with 16x16 and 32x32 embedded
- Removed old Perplexity icon assets"
```

==================================================
SECTION 5: UPDATE ALL PERPLEXITY TEXT REFERENCES
==================================================

### Step 5.1: Update `index.html`

**File:** `frontend/index.html`

Replace:
```html
<title>Perplexity AI</title>
<meta name="description" content="Perplexity AI helps you..." />
<link rel="icon" href="/favicon.ico" />
<link rel="apple-touch-icon" href="/apple-touch-icon.png" />
<meta property="og:title" content="Perplexity AI" />
<meta property="og:image" content="/perplexity-og.png" />
```

With:
```html
<title>سبيتسر AI — مساعدك التعليمي الذكي</title>
<meta name="description" content="سبيتسر AI منصة تعليمية ذكية مخصصة للطلاب العرب. احصل على إجابات دقيقة بالعربية." />
<link rel="icon" type="image/x-icon" href="/favicon.ico" />
<link rel="icon" type="image/svg+xml" href="/spetser-icon.svg" />
<link rel="apple-touch-icon" sizes="180x180" href="/spetser-apple.png" />
<meta property="og:title" content="سبيتسر AI — مساعدك التعليمي الذكي" />
<meta property="og:description" content="منصة تعليمية ذكية مخصصة للطلاب العرب" />
<meta property="og:image" content="/spetser-og.png" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta name="theme-color" content="#01696D" />
```

### Step 5.2: Update `manifest.webmanifest` (PWA)

**File:** `frontend/public/manifest.webmanifest`

Replace:
```json
{
  "name": "Perplexity AI",
  "short_name": "Perplexity",
  "description": "AI-powered answers",
  "icons": [
    { "src": "/perplexity-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/perplexity-512.png", "sizes": "512x512", "type": "image/png" }
  ],
  "theme_color": "#01696D",
  "background_color": "#F9F8F4",
  "display": "standalone"
}
```

With:
```json
{
  "name": "سبيتسر AI",
  "short_name": "سبيتسر",
  "description": "منصة تعليمية ذكية مخصصة للطلاب العرب",
  "start_url": "/",
  "icons": [
    {
      "src": "/spetser-192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/spetser-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/spetser-icon.svg",
      "sizes": "any",
      "type": "image/svg+xml"
    }
  ],
  "theme_color": "#01696D",
  "background_color": "#F9F8F4",
  "display": "standalone",
  "lang": "ar",
  "dir": "rtl"
}
```

### Step 5.3: Update Constants File

**File:** `frontend/src/lib/constants.ts` (or create if missing)

```typescript
// Branding constants — single source of truth
export const BRAND = {
  name: 'سبيتسر',
  nameEn: 'Spetser',
  fullName: 'سبيتسر AI',
  fullNameEn: 'Spetser AI',
  domain: 'spetser.ai',
  tagline: 'مساعدك التعليمي الذكي',
  taglineEn: 'Your intelligent learning companion',

  // Colors (must match design tokens)
  colorPrimary: '#01696D',
  colorAccent: '#F59E0B',
  colorBgLight: '#F9F8F4',
  colorBgDark: '#0F0E17',

  // Social
  twitter: '@spetser_ai',

  // Icons
  favicon: '/favicon.ico',
  iconSvg: '/spetser-icon.svg',
  iconPng512: '/spetser-512.png',
  iconPng192: '/spetser-192.png',
  appleTouchIcon: '/spetser-apple.png',
  ogImage: '/spetser-og.png',
} as const;
```

### Step 5.4: Update All Component References

For every file flagged in the audit (Step 3.1), replace hardcoded strings with constants:

**Before:**
```tsx
<h1>Perplexity AI</h1>
<p>Welcome to Perplexity</p>
```

**After:**
```tsx
import { BRAND } from '../lib/constants';

<h1>{BRAND.fullName}</h1>
<p>مرحباً بك في {BRAND.name}</p>
```

### Step 5.5: Update SVG Logo Component

**File:** `frontend/src/components/Logo.tsx` (or equivalent)

```tsx
import { BRAND } from '../lib/constants';

interface LogoProps {
  size?: number;
  variant?: 'full' | 'icon';
  className?: string;
}

export function Logo({ size = 32, variant = 'full', className = '' }: LogoProps) {
  if (variant === 'icon') {
    return (
      <img
        src={BRAND.iconSvg}
        alt={BRAND.name}
        width={size}
        height={size}
        className={className}
      />
    );
  }

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <img
        src={BRAND.iconSvg}
        alt=""
        width={size}
        height={size}
        aria-hidden="true"
      />
      <span
        className="font-bold"
        style={{ color: `var(--color-brand, ${BRAND.colorPrimary})` }}
      >
        {BRAND.fullName}
      </span>
    </div>
  );
}
```

### Step 5.6: Update `package.json`

**File:** `frontend/package.json`

If the `name` or `description` field contains "perplexity", replace it:
```json
{
  "name": "spetser-ai-frontend",
  "description": "Spetser AI — Arabic-first educational AI platform",
  ...
}
```

### Step 5.7: Update `README.md`

**File:** `frontend/README.md` (and root `README.md`)

Replace all "Perplexity" references with "Spetser". Add a branding section:
```markdown
## Branding

- **Name:** سبيتسر AI (Spetser AI)
- **Primary color:** `#01696D` (Teal)
- **Accent color:** `#F59E0B` (Amber)
- **Icon:** Designed via Google Stitch — stylized "S" with spark motif
- **Logo assets:** Located in `public/spetser-*.{svg,png}` and `public/favicon.ico`
```

### Step 5.8: Verify No Remaining References

```bash
cd frontend
grep -rni "perplexity" . --include="*.tsx" --include="*.ts" --include="*.css" \
  --include="*.html" --include="*.json" --include="*.md" \
  --exclude-dir=node_modules --exclude-dir=dist 2>/dev/null
```

**Expected:** Empty output (or only `BRANDING_AUDIT.md` and `CHANGELOG.md` mentioning the migration).

If any remain, fix them and re-run.

### Step 5.9: Commit Text Replacements

```bash
git add -A
git commit -m "feat(branding): replace all Perplexity references with Spetser

- Update index.html meta tags (title, description, OG, theme-color)
- Update manifest.webmanifest with Arabic name and RTL dir
- Create src/lib/constants.ts with BRAND object (single source of truth)
- Replace hardcoded strings in all components with BRAND.* constants
- Add Logo component supporting icon-only and full variants
- Update package.json name and description
- Update README.md branding section
- Verified: zero remaining 'perplexity' references in source"
```

==================================================
SECTION 6: VERIFICATION
==================================================

### Step 6.1: Build Verification

```bash
cd frontend
npm run build
```

**Expected:** Build succeeds with 0 errors.

### Step 6.2: Lint Verification

```bash
npm run lint
```

**Expected:** 0 errors, 0 warnings.

### Step 6.3: Visual Verification (Manual)

Open the dev server and check:
- [ ] Browser tab shows "سبيتسر AI" favicon (the new teal S with spark)
- [ ] Page title is "سبيتسر AI — مساعدك التعليمي الذكي"
- [ ] Header logo shows the new icon + "سبيتسر AI" text
- [ ] PWA install prompt shows "سبيتسر AI" with new icon
- [ ] When sharing URL, OG image is the 1200x630 Spetser image
- [ ] No "Perplexity" text anywhere in the UI
- [ ] Dark mode still looks correct (teal works on dark bg)

### Step 6.4: Automated Branding Test

**File to create:** `frontend/src/lib/branding.test.ts`

```typescript
import { describe, it, expect } from 'vitest';
import { BRAND } from './constants';

describe('Branding Constants', () => {
  it('uses Spetser name, not Perplexity', () => {
    expect(BRAND.name).toBe('سبيتسر');
    expect(BRAND.nameEn).toBe('Spetser');
    expect(BRAND.name.toLowerCase()).not.toContain('perplexity');
  });

  it('uses correct brand colors', () => {
    expect(BRAND.colorPrimary).toBe('#01696D');
    expect(BRAND.colorAccent).toBe('#F59E0B');
  });

  it('references correct icon paths', () => {
    expect(BRAND.iconSvg).toMatch(/spetser.*\.svg$/);
    expect(BRAND.favicon).toMatch(/favicon\.ico$/);
    expect(BRAND.ogImage).toMatch(/spetser.*og.*\.png$/);
  });
});
```

Run:
```bash
npm run test -- src/lib/branding.test.ts
```

### Step 6.5: Icon Asset Verification Test

**File to create:** `frontend/tests/icon-assets.test.ts`

```typescript
import { describe, it, expect } from 'vitest';
import { existsSync, statSync } from 'fs';
import { join } from 'path';

const PUBLIC_DIR = join(__dirname, '../public');

describe('Spetser icon assets', () => {
  const requiredAssets = [
    'favicon.ico',
    'spetser-icon.svg',
    'spetser-512.png',
    'spetser-192.png',
    'spetser-32.png',
    'spetser-16.png',
    'spetser-apple.png',
    'spetser-og.png',
  ];

  for (const asset of requiredAssets) {
    it(`${asset} exists and is non-empty`, () => {
      const path = join(PUBLIC_DIR, asset);
      expect(existsSync(path)).toBe(true);
      expect(statSync(path).size).toBeGreaterThan(0);
    });
  }

  it('SVG icon is valid', () => {
    const svgPath = join(PUBLIC_DIR, 'spetser-icon.svg');
    const content = readFileSync(svgPath, 'utf-8');
    expect(content).toContain('<svg');
    expect(content).toContain('</svg>');
    expect(content).toContain('#01696D'); // teal
    expect(content).toContain('#F59E0B'); // amber spark
  });

  it('no old Perplexity icons remain', () => {
    const files = readdirSync(PUBLIC_DIR);
    const perplexityFiles = files.filter((f) =>
      f.toLowerCase().includes('perplexity')
    );
    expect(perplexityFiles).toEqual([]);
  });
});
```

Run:
```bash
npm run test -- tests/icon-assets.test.ts
```

### Step 6.6: Final Full Test Run

```bash
npm run lint
npm run test
npm run build
```

All must pass.

### Step 6.7: Commit Verification Tests

```bash
git add -A
git commit -m "test(branding): add branding constants and icon asset tests

- branding.test.ts: verifies BRAND constants use Spetser, correct colors
- icon-assets.test.ts: verifies all required PNG/SVG/ICO assets exist
  and old Perplexity icons are removed
- All tests pass alongside existing suite"
```

==================================================
SECTION 7: DOCUMENTATION & HANDOFF
==================================================

### Step 7.1: Update PROJECT_STATUS.md

Append to `docs/PROJECT_STATUS.md`:

```markdown
## Branding Replacement — COMPLETE

**Date:** [TODAY]
**Commit:** [HASH]

### Changes
- Replaced ALL "Perplexity" references with "Spetser" (Arabic: سبيتسر)
- Designed new icon via Google Stitch: stylized "S" with teal body (#01696D) and amber spark (#F59E0B)
- Generated icon assets: SVG + PNG variants (512, 192, 32, 16, apple, og)
- Updated index.html meta tags, PWA manifest, all components
- Created `src/lib/constants.ts` as single source of truth for branding
- Added `Logo` component for consistent brand display

### Icon Assets (all in `public/`)
| File | Size | Purpose |
|------|------|---------|
| favicon.ico | ~5KB | Browser tab (16x16 + 32x32) |
| spetser-icon.svg | ~2KB | Primary scalable vector |
| spetser-512.png | 512x512 | PWA install, high-res |
| spetser-192.png | 192x192 | PWA manifest |
| spetser-apple.png | 180x180 | iOS home screen |
| spetser-og.png | 1200x630 | Social share preview |

### Tests Added
- `src/lib/branding.test.ts` — validates BRAND constants
- `tests/icon-assets.test.ts` — validates icon file existence and format

### Status
✅ Build: PASS
✅ Lint: PASS
✅ Tests: ALL PASS
✅ Visual: Verified (favicon, header, PWA, OG image)
```

### Step 7.2: Update ERROR_LOG.md (if any issues occurred)

If any step failed (e.g., Stitch unavailable, SVGO not installed), log it with the workaround used.

### Step 7.3: Final Commit

```bash
git add -A
git commit -m "docs(branding): update PROJECT_STATUS with branding replacement evidence"
```

==================================================
SECTION 8: FALLBACK PLAN (IF STITCH UNAVAILABLE)
==================================================

If Google Stitch is not accessible (requires sign-in, is down, or rate-limits), use this fallback:

### Fallback 8.1: Use Built-in Image Generator

Call the `image_gen` tool (if available in your environment) with the exact prompt from Section 1.3.

### Fallback 8.2: Hand-Craft SVG

If no image tool is available, create a simple but clean SVG manually:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <!-- Stylized S with spark -->
  <defs>
    <linearGradient id="spark" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#F59E0B"/>
      <stop offset="100%" stop-color="#01696D"/>
    </linearGradient>
  </defs>
  
  <!-- Main S body -->
  <path d="M 65 25
           C 65 15, 35 15, 35 25
           C 35 35, 65 40, 65 50
           C 65 65, 35 65, 35 55"
        stroke="#01696D" stroke-width="10" fill="none" stroke-linecap="round"/>
  
  <!-- Spark at top -->
  <path d="M 65 25 L 68 15 L 62 18 L 65 8 L 60 17 L 55 12 L 58 20"
        fill="#F59E0B" stroke="none"/>
</svg>
```

Save as `public/spetser-icon.svg` and continue with Step 4.5 (generate PNGs).

**Document the fallback** in `docs/BRANDING_AUDIT.md`:
> "Google Stitch was unavailable; icon hand-crafted as SVG. Future iteration should regenerate via Stitch for higher design polish."

==================================================
SECTION 9: ACCEPTANCE CRITERIA
==================================================

Branding replacement is COMPLETE only when:

- [ ] `grep -ri perplexity frontend/src frontend/public` returns 0 results
- [ ] `favicon.ico` contains the new Spetser icon
- [ ] `spetser-icon.svg` exists and renders correctly
- [ ] All 5 PNG variants exist (512, 192, 32, 16, apple, og)
- [ ] `index.html` meta tags use Spetser branding
- [ ] `manifest.webmanifest` uses Arabic name + RTL direction
- [ ] `BRAND` constants file exists as single source of truth
- [ ] `Logo` component exists and is used in Header
- [ ] `branding.test.ts` passes
- [ ] `icon-assets.test.ts` passes
- [ ] Full build/lint/test suite passes
- [ ] Visual verification: no "Perplexity" anywhere in UI
- [ ] `PROJECT_STATUS.md` updated with evidence

==================================================
SECTION 10: START COMMAND
==================================================

**Awaiting user instruction:**
- Say **"Execute Branding"** to run all steps.
- Say **"Audit Only"** to just run Section 3 (find Perplexity references).
- Say **"Design Only"** to just run Section 4 (Stitch icon generation).

GO.
```

---

## ملخص ما يفعله هذا البرومت

| الخطوة | الوصف |
|--------|--------|
| **1. التدقيق (Audit)** | يبحث عن كل نص "Perplexity" وكل ملف أيقونة قديم |
| **2. تصميم الأيقونة** | يفتح Google Stitch ويولد أيقونة "S" مع شرارة بألوان العلامة التجارية |
| **3. تصدير الأيقونة** | يُصدّر SVG + PNG بأحجام متعددة (16, 32, 192, 512, apple, og) |
| **4. توليد favicon** | يجمع الأحجام الصغيرة في ملف `.ico` واحد |
| **5. استبدال النصوص** | يحدّث `index.html`, `manifest.webmanifest`, `constants.ts`, وكل المكونات |
| **6. مكون Logo** | ينشئ مكون `Logo.tsx` قابل لإعادة الاستخدام |
| **7. اختبارات تلقائية** | يكتب `branding.test.ts` و`icon-assets.test.ts` لمنع الرجوع |
| **8. خطة بديلة** | إذا تعذّر Stitch، يُولّد SVG يدوياً كبديل |

## نصائح عند التشغيل

1. **ابدأ بـ "Audit Only"** لمعرفة نطاق التغييرات قبل الشروع في التنفيذ.
2. **تأكد من الوصول إلى Stitch** قبل البدء — إذا كان يحتاج تسجيل دخول Google، قد تحتاج لتوفير session نشط.
3. **راجع الأيقونة يدوياً** قبل اعتمادها: افتح `spetser-icon.svg` في المتصفح وتأكد أنها تبدو جيدة بأحجام مختلفة.
4. **اختبر على جهاز محمول** بعد النشر للتأكد أن PWA تظهر الأيقونة الجديدة بشكل صحيح.

هل تريد أن أبدأ بتنفيذ **"Audit Only"** أولاً لفحص نطاق التغييرات في مشروعك الحالي؟
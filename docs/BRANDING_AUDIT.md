# Branding Audit — Spetser AI

## Files containing "Perplexity" (to be replaced)

| File | Line | Context | Replacement |
|------|------|---------|-------------|
| `frontend/src/components/AppShell.tsx` | 4 | `* On the home page ('/'), it renders the exact Stitch Perplexity interface directly.` | `* On the home page ('/'), it renders the exact Stitch Spetser interface directly.` |
| `frontend/src/components/AppShell.tsx` | 109 | `<span className="brand-mark__name">Perplexity</span>` | `<span className="brand-mark__name">{BRAND.nameEn}</span>` |
| `frontend/src/components/stitch/StitchSidebar.tsx` | 49 | `<span className="font-headline-md text-headline-md tracking-tight text-ink font-semibold">Perplexity</span>` | `<span className="font-headline-md text-headline-md tracking-tight text-ink font-semibold">{BRAND.nameEn}</span>` |
| `frontend/src/components/stitch/StitchMobileDrawer.tsx` | 55 | `<span className="font-headline-md text-headline-md tracking-tight text-ink font-semibold">Perplexity</span>` | `<span className="font-headline-md text-headline-md tracking-tight text-ink font-semibold">{BRAND.nameEn}</span>` |
| `frontend/src/components/stitch/StitchMobileHome.tsx` | 89 | `<span className="font-sans font-medium text-[15px] tracking-tight text-ink">Perplexity</span>` | `<span className="font-sans font-medium text-[15px] tracking-tight text-ink">{BRAND.nameEn}</span>` |
| `frontend/src/components/stitch/StitchMobileHome.tsx` | 105 | `{/* Stylized Perplexity Asterisk / Starburst in Deep Teal (Stitch exact SVG) */}` | `{/* Stylized Spetser Brand Icon (S with Spark tip) */}` |
| `frontend/src/components/stitch/StitchMobileHome.tsx` | 107-129 | Perplexity 12-arm Asterisk SVG | Replaced with Spetser Logo / S-Spark Brand Mark |
| `frontend/src/contexts/ThemeContext.tsx` | 8 | `* (matching the Perplexity reference). OS preference is intentionally` | `* (matching the Spetser reference). OS preference is intentionally` |
| `frontend/src/index.css` | 2354 | `/* Stitch Project 65770937400041676 — Exact Perplexity Replica Utilities */` | `/* Stitch Project 65770937400041676 — Exact Spetser Replica Utilities */` |
| `frontend/src/pages/HomePage.tsx` | 5 | `* - Desktop View (>= 768px): Stitch Perplexity Search Desk with Left Sidebar,` | `* - Desktop View (>= 768px): Stitch Spetser Search Desk with Left Sidebar,` |
| `frontend/src/pages/HomePage.tsx` | 8 | `* - Mobile View (< 768px): Stitch Perplexity Mobile with Top Bar (Hamburger, Brand, Profile),` | `* - Mobile View (< 768px): Stitch Spetser Mobile with Top Bar (Hamburger, Brand, Profile),` |

## Icon surfaces to update
- [x] `public/favicon.ico` (16x16, 32x32 multi-resolution icon)
- [x] `public/spetser-icon.svg` (Scalable primary vector icon)
- [x] `public/spetser-512.png` (512x512 PWA install / high-res)
- [x] `public/spetser-192.png` (192x192 PWA manifest)
- [x] `public/spetser-apple.png` (180x180 Apple touch icon)
- [x] `public/spetser-32.png` (32x32 icon)
- [x] `public/spetser-16.png` (16x16 icon)
- [x] `public/spetser-og.png` (1200x630 Open Graph preview image)
- [x] `public/manifest.webmanifest` (PWA configuration with Arabic title and RTL)
- [x] `frontend/index.html` (Meta tags, title, OG tags, theme-color `#01696D`)
- [x] `frontend/src/components/Logo.tsx` (Reusable Logo component)
- [x] `frontend/src/lib/constants.ts` (BRAND single source of truth)
- [x] `frontend/package.json` (Package metadata)
- [x] `frontend/README.md` (Branding documentation)

## Icon Design Note
- SVG icon designed with stylized "S" curving upwards from base node into an amber spark (`#F59E0B`) with teal body (`#01696D`).
- Fallback note: High-fidelity clean SVG generated meeting all Section 1.2 and 1.3 specifications (scalable, flat geometry, transparent background, vibrant teal and amber).

# Spetser AI — Frontend UI Refresh (Phase 1: Chat Interface)

> **Paste this whole file into Antigravity.** It is self-contained.
> Source of truth: the **Google Stitch reference design (visual language)** +
> **the product owner's chat-interface specification (structure)**.

---

## 0. Repository context

- Monorepo root: `spetser-ai/`. Work **only** inside `frontend/`.
- Stack: **React 19 + Vite 8 + TypeScript 6**, React Router 7, TanStack Query 5,
  `react-hook-form` + `zod`, **`lucide-react`** (already installed).
- **There is NO Tailwind and NO UI kit.** All styling is hand-written CSS in a
  single file: `frontend/src/index.css`. Extend it; do not add a CSS framework,
  CSS-in-JS, or CSS Modules. Do not add any new dependency except none — you
  already have everything you need.
- The design system is documented in `docs/DESIGN_TOKENS.json` and implemented
  in `frontend/src/index.css`. Its documented reference is **Perplexity AI,
  matched 16/17**. The palette is therefore already correct.
- Existing hooks you must reuse: `useAuth()` (`src/contexts/useAuth`),
  `useTheme()` (`src/contexts/useTheme`), `useCredits()` (`src/hooks/useCredits`).
- Existing API client: `src/api/*.ts` via `src/api/client.ts`.

### Current routes (`src/App.tsx`)
| Path | Component |
|---|---|
| `/login`, `/register`, `/r/:code` | public |
| `/` | `HomePage` |
| `/chat`, `/chat/:conversationId` | `ChatPage` |
| `/presentations/new`, `/history`, `/referrals` | placeholders |
| `/admin/*` | admin (code-split) |

### Conversation API shape (already implemented — do not change)
```ts
interface ConversationSummary {
  id: string; title: string | null; active_skill_slug: string | null;
  is_archived: boolean; created_at: string; updated_at: string;
}
```
**There is no projects/folders field and no projects endpoint.**

---

## 1. Objective

Turn the student-facing app into a **chat-first interface**: one unified sidebar
(New chat / Projects / Chats / Recently), a spacious conversation area, a modern
composer with attachment + model-strength controls, and floating quick-action
chips above the composer that act as context setters.

Visual language follows the Stitch reference: cream canvas, single teal accent,
flat surfaces, hairline borders, pill controls, line icons.

---

## 2. HARD CONSTRAINTS — violating any of these fails the task

1. **Do NOT touch `backend/`.** No new endpoints, no new network calls, no
   changes to `src/api/*` contracts.
2. **Projects and Recently are client-side only** (`localStorage`). There is no
   projects API — **do not invent one** and do not call the backend for them.
3. **Do NOT modify existing colour/typography/spacing token values.** The only
   permitted token additions are the two listed in §3.
4. **Arabic-first RTL.** Use CSS **logical properties only**
   (`inset-inline-start`, `margin-inline`, `border-inline-end`, …).
   **No `left`, `right`, `margin-left`, `padding-right` anywhere in new code.**
   In RTL the sidebar sits on the **right**.
5. **Remove every emoji used as an icon** in the student UI (`🏠 🖥️ 💬 🎁 📚 🔢 🕐 ⚡ ＋ ⋯ ✏️ 📦 🗑️`).
   Replace with `lucide-react` components carrying `aria-hidden="true"`.
   Keep text-only emoji out; use icons.
6. **Preserve all existing accessibility affordances**: `SkipLink`, `aria-label`
   on every icon-only button, `aria-current` for the active chat, `aria-pressed`
   for toggle chips, visible `:focus-visible` rings, `@media (prefers-reduced-motion)`.
7. **Dark theme must keep working** (`[data-theme="dark"]`). Check every new
   surface for unreadable contrast.
8. **Do not break `/admin/*`.** Admin pages import from `index.css` too.
9. Keep TypeScript strict-clean: `npm run build` runs `tsc -b` first.

---

## 3. Tokens to ADD (these two, and only these)

```css
:root {
  --color-sidebar:        #faf4e8;  /* warm cream plane for the sidebar */
  --color-sidebar-border: #eee7d8;
}
[data-theme="dark"] {
  --color-sidebar:        #1a191f;
  --color-sidebar-border: #302e37;
}
```

Everything else stays exactly as-is.

---

## 4. Work plan — file by file

### 4.1 NEW `src/components/layout/AppSidebar.tsx`
One sidebar, used by the whole student app. Sections top → bottom:

1. **Brand** — keep the existing `.brand-mark` markup (teal square `س` + name +
   subtitle `مساعدك الأكاديمي`).
2. **Primary action** — full-width teal button, `SquarePen` icon,
   label **`محادثة جديدة`**, navigates to `/chat`.
3. **`المشاريع`** section
   - header row: section label + `Plus` icon button, `aria-label="مشروع جديد"`
   - creating opens an **inline text input** (no modal); Enter commits, Escape cancels
   - each project row: `Folder` icon, name, chat-count badge, and a `MoreHorizontal`
     menu with `إعادة تسمية` / `حذف`
   - clicking a project expands it to list its chats; each chat has a
     `X` button (`aria-label="إزالة من المشروع"`) to detach it
4. **`المحادثات`** section — the conversation list. Reuse the existing
   rename / archive / delete behaviour from `ConversationSidebar.tsx`,
   including Escape-to-close on the menu. Active chat gets
   `aria-current="true"` and the `--active` background.
5. **`الأخيرة`** section — last 5 chats opened (from `localStorage`), collapsed
   by default, each row navigates to it.
6. **Footer** — in this order:
   - credits badge (reuse `.credit-badge`; opens `BuyCreditsModal`)
   - theme toggle (`Sun` / `Moon`, `aria-label` switches)
   - settings link to `/settings` (`Settings` icon, label `الإعدادات`)
   - user card: circular avatar with the first letter of
     `display_name || email`, the name, and a logout `LogOut` icon button

Add a detached-chat path: in the `المحادثات` list each row's `MoreHorizontal`
menu gains one extra item — `إضافة إلى مشروع ▸` — listing existing projects plus
`مشروع جديد…`.

### 4.2 NEW `src/lib/projects.ts`
A single, typed, `localStorage`-backed module. Every read/write wrapped in
`try/catch` and never throwing (private mode / quota). Keys namespaced
`spetser.projects`, `spetser.recent`.

```ts
export interface Project { id: string; name: string; createdAt: string }
export interface RecentEntry { conversationId: string; openedAt: string }

export function listProjects(): Project[]
export function createProject(name: string): Project
export function renameProject(id: string, name: string): void
export function deleteProject(id: string): void
export function addChatToProject(projectId: string, conversationId: string): void
export function removeChatFromProject(projectId: string, conversationId: string): void
export function projectOfChat(conversationId: string): string | null
export function listRecent(): RecentEntry[]
export function touchRecent(conversationId: string): void
```
Use `crypto.randomUUID()` for ids. Export a `subscribe(cb)` / `notify()` pair (or
a tiny `useSyncExternalStore` hook `useProjects()`) so the sidebar re-renders on
mutation.

### 4.3 NEW `src/lib/modelStrength.ts`
```ts
export type ModelStrength = 'fast' | 'balanced' | 'deep';
export const MODEL_STRENGTHS: { value: ModelStrength; label: string }[] = [
  { value: 'fast',     label: 'سريع' },
  { value: 'balanced', label: 'متوازن' },
  { value: 'deep',     label: 'عميق' },
];
export function getModelStrength(): ModelStrength      // localStorage, default 'balanced'
export function setModelStrength(v: ModelStrength): void
```
With a `// TODO(backend): map to the chat request once supported.` comment.

### 4.4 NEW `src/lib/quickActions.ts`
```ts
export type QuickActionId = 'presentation' | 'math' | 'report';
export const QUICK_ACTIONS = [
  { id: 'presentation', label: 'إنشاء عرض تقديمي', icon: 'Presentation' },
  { id: 'math',         label: 'حل مسائل رياضية',  icon: 'Calculator'   },
  { id: 'report',       label: 'كتابة بحث / تقرير', icon: 'FileText'     },
] as const;
```
`// TODO(backend): wire each id to the matching active_skill_slug.`

### 4.5 REWRITE `src/components/chat/Composer.tsx`
One large rounded box (`--radius-lg`, `--shadow-sm`, teal focus ring via
`--shadow-focus` on `:focus-within`). Layout, top → bottom, **inside the box**:

- **textarea** — `min-height` 72px, auto-grows to 200px, placeholder
  **`اسأل أي شيء...`**, `Enter` submits, `Shift+Enter` newlines.
- **selected-files row** (only when files are chosen) — removable chips, each
  with a `X` button, file name truncated, and a small `FileText`/`Image` icon.
- **toolbar row** (`justify-content: space-between`):
  - start cluster:
    - `Paperclip` icon button, `aria-label="إرفاق ملف"`, opens a hidden
      `<input type="file" multiple>`; `onFilesChange?: (files: File[]) => void`.
      **UI only — do not upload.**
    - **model pill**: `<button>` showing a status dot + current label + `ChevronDown`.
      Opens a menu with the three options; selecting one updates state **and**
      `setModelStrength`. `aria-haspopup="listbox"`, `aria-expanded`, Escape closes.
      **UI only — do not send it to the API.**
  - end cluster:
    - `Mic` icon button, `aria-label="الإدخال الصوتي"`, `disabled`,
      `title="قريباً"`.
    - circular teal submit button (40×40, `--radius-full`), `ArrowUp` icon,
      `aria-label="إرسال"`, disabled while empty or streaming.

### 4.6 NEW `src/components/chat/QuickActions.tsx`
A row of chips rendered **directly above the composer**, floating over its top
edge: the wrapper is `position: relative`, the row uses a **negative
`margin-block-end`** and `z-index: 2` so the chips overlap the composer's top
border. Chips sit in a fl‑wrap row, centred on mobile.

- Each chip: `lucide-react` icon + Arabic label from `QUICK_ACTIONS`, pill shape.
- **At most one active.** Clicking an inactive chip activates it; clicking the
  active one deactivates. Set `aria-pressed`.
- Active style: teal fill, white text, subtle shadow. Inactive: transparent
  background, hairline border, secondary text colour.
- When a chip is active, the composer shows a small badge above the textarea:
  **`الوضع: {label}`** with a `X` to clear it.
- **UI only** — the selected id is local state (lift it to the page so the
  composer can read it). Do not call the API.

### 4.7 REWRITE `src/pages/HomePage.tsx`
Chat-first empty state. Centred column, `max-width: var(--content-max-width)`,
generous top padding:

1. teal mark (inline asterisk-style SVG or `Sparkles`), ~40px, `aria-hidden`
2. `h1` — `أهلاً، {display_name}` (fallback `مرحباً بك`)
3. subtitle — `اسأل أي شيء، أو ابدأ من أحد الأزرار بالأسفل`
4. `<QuickActions>` + `<Composer>`
5. `أحدث المحادثات` — a 2×2 grid of `.card`s (one column under 480px). Each card:
   title, a muted badge for its skill when present, relative time in Arabic, and
   the whole card is a link to `/chat/{id}`. Show `عرض الكل` linking to `/history`.
   Empty state when there are none.

**Remove the old feature grid** (`FEATURES` / `FeatureCard`) from this page — its
entry points are now the quick-action chips. Delete the now-unused types too.

### 4.8 UPDATE `src/pages/ChatPage.tsx`
- Drop the duplicated `chat-layout__sidebar`; render `<AppSidebar />` instead
  (keep the mobile drawer behaviour).
- Conversation area: `max-width: var(--content-max-width)`, centred, roomy
  vertical rhythm, message bubbles unchanged in styling.
- Composer docked at the bottom with `<QuickActions>` above it.
- When a conversation opens, call `touchRecent(id)`.

### 4.9 UPDATE `src/components/AppShell.tsx`
- Replace the inline `<aside>` block with `<AppSidebar />`.
- Keep `--topbar-height: 56px`. Topbar keeps the credit badge and theme toggle,
  and gains a **mobile hamburger** (`Menu` icon, `aria-label="القائمة"`,
  `aria-expanded`) visible only under 768px.
- Mobile: the sidebar becomes a fixed overlay drawer (translate 100% → 0 when
  `data-open="true"`) with a scrim behind it; clicking the scrim or pressing
  Escape closes it. Reuse the existing mobile pattern already in `index.css`.

### 4.10 UPDATE `src/index.css`
Add the two tokens (§3) and new classes:
`.app-sidebar__section`, `.app-sidebar__section-head`, `.app-sidebar__section-title`,
`.sidebar-project`, `.sidebar-project__chats`, `.quick-actions`, `.quick-action-chip`,
`.quick-action-chip--active`, `.composer__files`, `.composer__file-chip`,
`.model-pill`, `.model-pill__menu`, `.mode-badge`, `.mobile-scrim`, `.user-card`.

Change: the sidebar background uses `var(--color-sidebar)` and its border
`var(--color-sidebar-border)` (both `.app-shell__sidebar` and
`.chat-layout__sidebar`).

Keep the existing `@media (max-width: 768px)` block working.

### 4.11 NEW `src/pages/SettingsPage.tsx` + route `/settings`
Minimal but real, inside `RequireAuth` + `AppShell`:
- profile card: display name (read-only for now), email (read-only)
- appearance: theme toggle (reuse `useTheme`)
- credits: current balance + note
  **`سيتم تفعيل الرصيد اليومي المجاني في التحديث القادم.`**
- account: logout button
Add the route to `src/App.tsx`.

---

## 5. Exact Arabic strings (use verbatim)

| Key | String |
|---|---|
| new chat | `محادثة جديدة` |
| projects | `المشاريع` |
| new project | `مشروع جديد` |
| chats | `المحادثات` |
| recently | `الأخيرة` |
| settings | `الإعدادات` |
| search/composer placeholder | `اسأل أي شيء...` |
| send | `إرسال` |
| attach | `إرفاق ملف` |
| voice | `الإدخال الصوتي` |
| coming soon | `قريباً` |
| quick action 1 | `إنشاء عرض تقديمي` |
| quick action 2 | `حل مسائل رياضية` |
| quick action 3 | `كتابة بحث / تقرير` |
| mode badge prefix | `الوضع:` |
| home heading | `أهلاً، {name}` |
| home subtitle | `اسأل أي شيء، أو ابدأ من أحد الأزرار بالأسفل` |
| latest chats | `أحدث المحادثات` |
| view all | `عرض الكل` |
| rename / delete | `إعادة تسمية` / `حذف` |
| add to project | `إضافة إلى مشروع` |
| remove from project | `إزالة من المشروع` |
| daily credit note | `سيتم تفعيل الرصيد اليومي المجاني في التحديث القادم.` |

---

## 6. Acceptance criteria

- [ ] `npm run build` passes with a clean `tsc -b`
- [ ] `npm run lint` reports no new problems
- [ ] `npm run test` still passes
- [ ] Sidebar renders, in order: brand → `محادثة جديدة` → `المشاريع` →
      `المحادثات` → `الأخيرة` → footer (credits, theme, settings, user card)
- [ ] A created project **persists across a page reload**
- [ ] A chat added to a project **persists across a page reload**
- [ ] Quick-action chips: exactly one active at a time, correct `aria-pressed`,
      active chip visually distinct, mode badge shows in the composer
- [ ] Composer shows: attach button → model pill → mic → circular send
- [ ] Choosing files renders removable chips inside the composer
- [ ] The model choice persists across reload
- [ ] **No emoji-as-icon remains anywhere in the student UI**
- [ ] No `left` / `right` / `margin-left` / `padding-right` in new CSS
- [ ] Renders correctly at **375px** width with the sidebar as a drawer
- [ ] Dark theme has no unreadable text
- [ ] `/admin/*` still loads

---

## 7. Verification — run these and paste the raw output

```bash
cd frontend
npm run build 2>&1 | tail -25
npm run lint  2>&1 | tail -25
npm run test  2>&1 | tail -25
npm run dev
```

Then **screenshot both themes at desktop and 375px** and attach them.
A report without the pasted command output is not accepted.

---

## 8. Explicitly OUT OF SCOPE for this phase

- Anything in `backend/`
- Email verification / OTP
- Daily free credits (300/day)
- Real file upload to R2
- Real model-strength routing
- Real skill selection wiring

Leave the `TODO(backend)` markers where noted so the next phase can find them.

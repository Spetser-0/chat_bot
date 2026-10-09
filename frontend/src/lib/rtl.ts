/**
 * lib/rtl.ts
 * ──────────
 * RTL/LTR helpers (Phase 9, Lesson 9.2).
 *
 * The app is Arabic-first: the document defaults to dir="rtl" (index.html).
 * These utilities support optional LTR (e.g. English content, code blocks)
 * and safe direction-aware formatting.
 */

export type Dir = 'rtl' | 'ltr';

/** True when the document is in right-to-left mode. */
export function isRTL(): boolean {
  if (typeof document === 'undefined') return true;
  return document.documentElement.dir === 'rtl';
}

/** Current document direction ('rtl' by default). */
export function getDocumentDir(): Dir {
  if (typeof document === 'undefined') return 'rtl';
  return document.documentElement.dir === 'ltr' ? 'ltr' : 'rtl';
}

/** Set the document direction (flips the whole layout atomically). */
export function setDocumentDir(dir: Dir): void {
  if (typeof document === 'undefined') return;
  document.documentElement.dir = dir;
  document.documentElement.lang = dir === 'rtl' ? 'ar' : 'en';
}

/**
 * Mark an element subtree as LTR (e.g. a code block inside an RTL page).
 * Adds the .ltr class, which index.css styles with Inter + direction:ltr.
 */
export function applyLtr(el: HTMLElement): void {
  el.classList.add('ltr');
  el.dir = 'ltr';
}

/**
 * Mirror-aware logical CSS properties cheat sheet (do NOT use physical):
 *   margin-inline-start / margin-inline-end   (not margin-left/right)
 *   padding-inline-start / padding-inline-end (not padding-left/right)
 *   border-inline-start / border-inline-end   (not border-left/right)
 *   inset-inline-start / inset-inline-end     (not left/right)
 *   text-align: start / end                   (not left/right)
 */
export const LOGICAL_CSS_REMINDERS = 'use-inline-logical-properties' as const;

/**
 * components/ui/SkipLink.tsx
 * ──────────────────────────
 * Keyboard-only skip-to-content link (Phase 9, Lesson 9.9).
 * Visually hidden until focused; jumps past nav/sidebar to #main-content.
 */
export function SkipLink() {
  return (
    <a href="#main-content" className="skip-link">
      تخطَّ إلى المحتوى الرئيسي
    </a>
  );
}

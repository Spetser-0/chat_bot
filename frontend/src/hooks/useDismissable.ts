/**
 * hooks/useDismissable.ts
 * ────────────────────────
 * Shared keyboard-dismiss pattern for menus/modals (Phase 9, Lesson 9.9).
 * - Escape closes
 * - Optional outside click (menus)
 * - Optional focus restore to the element that opened the overlay
 */
import { useEffect, useRef } from 'react';

interface UseDismissableOptions {
  open: boolean;
  onClose: () => void;
  /** Listen for mousedown outside the container (menus). */
  outsideClick?: boolean;
  /** Restore focus to the previously focused element on close. */
  restoreFocus?: boolean;
}

export function useDismissable<T extends HTMLElement>({
  open,
  onClose,
  outsideClick = false,
  restoreFocus = true,
}: UseDismissableOptions) {
  const ref = useRef<T>(null);
  const previouslyFocused = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;

    if (restoreFocus) {
      previouslyFocused.current = document.activeElement as HTMLElement | null;
    }

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        onClose();
      }
    };
    document.addEventListener('keydown', onKeyDown);

    let onOutside: ((e: MouseEvent) => void) | undefined;
    if (outsideClick) {
      onOutside = (e: MouseEvent) => {
        if (ref.current && !ref.current.contains(e.target as Node)) {
          onClose();
        }
      };
      document.addEventListener('mousedown', onOutside);
    }

    return () => {
      document.removeEventListener('keydown', onKeyDown);
      if (onOutside) document.removeEventListener('mousedown', onOutside);
      if (restoreFocus && previouslyFocused.current) {
        previouslyFocused.current.focus();
      }
    };
  }, [open, onClose, outsideClick, restoreFocus]);

  return ref;
}

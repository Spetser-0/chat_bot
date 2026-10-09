/**
 * components/chat/Composer.tsx
 * ────────────────────────────
 * Fixed-bottom message composer (Phase 9, Lessons 9.1 + 9.4).
 * While streaming, the send button becomes a stop button.
 */
import { useRef, useState, type FormEvent, type KeyboardEvent } from 'react';

interface ComposerProps {
  onSend?: (message: string) => void;
  onStop?: () => void;
  disabled?: boolean;
  isStreaming?: boolean;
  placeholder?: string;
}

export function Composer({
  onSend,
  onStop,
  disabled = false,
  isStreaming = false,
  placeholder = 'اكتب رسالتك هنا…',
}: ComposerProps) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const canSend = value.trim().length > 0 && !disabled && !isStreaming;

  const submit = () => {
    if (!canSend) return;
    onSend?.(value.trim());
    setValue('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (isStreaming) return;
    submit();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter sends; Shift+Enter makes a newline (ChatGPT convention).
    // Arabic IME: don't submit while composing.
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  };

  const autoGrow = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  };

  return (
    <form onSubmit={handleSubmit} aria-label="منطقة كتابة الرسالة">
      <div className="prompt-composer">
        <textarea
          ref={textareaRef}
          className="prompt-composer__textarea"
          value={value}
          onChange={(e) => { setValue(e.target.value); autoGrow(); }}
          onKeyDown={handleKeyDown}
          placeholder={isStreaming ? 'جاري الرد…' : placeholder}
          disabled={disabled}
          rows={1}
          aria-label="نص الرسالة"
        />
        <div className="prompt-composer__toolbar">
          <span className="text-xs text-muted">
            Enter للإرسال · Shift+Enter لسطر جديد
          </span>
          {isStreaming ? (
            <button
              type="button"
              className="btn btn--danger btn--sm"
              onClick={onStop}
              aria-label="إيقاف توليد الرد"
            >
              ⏹ إيقاف
            </button>
          ) : (
            <button
              type="submit"
              className="btn btn--primary btn--sm"
              disabled={!canSend}
              aria-label="إرسال الرسالة"
            >
              إرسال ↑
            </button>
          )}
        </div>
      </div>
    </form>
  );
}

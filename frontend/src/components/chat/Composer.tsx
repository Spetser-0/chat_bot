/**
 * components/chat/Composer.tsx
 * ──────────────────────────────
 * Large modern composer: auto-growing textarea, removable attachment chips,
 * a model-strength pill, a mic button and a circular teal send button.
 * A quick-action mode badge floats above the box when a mode is active.
 *
 * Phase 1 (frontend-only): attachments and model strength are UI state only —
 * nothing is uploaded and nothing is sent to the API.
 */
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import {
  ArrowUp,
  ChevronDown,
  FileText,
  Image,
  Mic,
  Paperclip,
  X,
} from 'lucide-react';
import {
  MODEL_STRENGTHS,
  getModelStrength,
  setModelStrength,
  type ModelStrength,
} from '../../lib/modelStrength';

interface ComposerProps {
  onSend?: (message: string) => void;
  onStop?: () => void;
  disabled?: boolean;
  isStreaming?: boolean;
  placeholder?: string;
  modeLabel?: string | null;
  onClearMode?: () => void;
  onFilesChange?: (files: File[]) => void;
}

export function Composer({
  onSend,
  onStop,
  disabled = false,
  isStreaming = false,
  placeholder = 'اسأل أي شيء...',
  modeLabel,
  onClearMode,
  onFilesChange,
}: ComposerProps) {
  const [value, setValue] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [strength, setStrength] = useState<ModelStrength>(() => getModelStrength());
  const [menuOpen, setMenuOpen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const canSend = value.trim().length > 0 && !disabled && !isStreaming;
  const strengthLabel = MODEL_STRENGTHS.find((s) => s.value === strength)?.label ?? 'متوازن';

  // Escape closes the model-strength menu.
  useEffect(() => {
    if (!menuOpen) return;
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.key === 'Escape') setMenuOpen(false);
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [menuOpen]);

  const submit = () => {
    if (!canSend) return;
    onSend?.(value.trim());
    setValue('');
    setFiles([]);
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (isStreaming) return;
    submit();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter sends; Shift+Enter makes a newline. Arabic IME: don't submit
    // while composing.
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

  const pickFiles = (list: FileList | null) => {
    if (!list) return;
    const next = [...files, ...Array.from(list)];
    setFiles(next);
    onFilesChange?.(next);
  };

  const removeFile = (index: number) => {
    const next = files.filter((_, i) => i !== index);
    setFiles(next);
    onFilesChange?.(next);
  };

  const chooseStrength = (v: ModelStrength) => {
    setStrength(v);
    setModelStrength(v);
    setMenuOpen(false);
  };

  return (
    <form onSubmit={handleSubmit} aria-label="منطقة كتابة الرسالة" className="composer">
      {modeLabel && (
        <div className="mode-badge" role="status">
          <span>الوضع: {modeLabel}</span>
          <button
            type="button"
            className="mode-badge__clear"
            onClick={onClearMode}
            aria-label="إلغاء الوضع"
          >
            <X size={13} aria-hidden="true" />
          </button>
        </div>
      )}

      <div className="prompt-composer">
        <textarea
          ref={textareaRef}
          className="prompt-composer__textarea"
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            autoGrow();
          }}
          onKeyDown={handleKeyDown}
          placeholder={isStreaming ? 'جاري الرد…' : placeholder}
          disabled={disabled}
          rows={1}
          aria-label="نص الرسالة"
        />

        {files.length > 0 && (
          <div className="composer__files" aria-label="الملفات المرفقة">
            {files.map((file, i) => (
              <span className="composer__file-chip" key={`${file.name}-${i}`}>
                {file.type.startsWith('image/') ? (
                  <Image size={13} aria-hidden="true" />
                ) : (
                  <FileText size={13} aria-hidden="true" />
                )}
                <span className="composer__file-name">{file.name}</span>
                <button
                  type="button"
                  className="composer__file-remove"
                  onClick={() => removeFile(i)}
                  aria-label={`إزالة ${file.name}`}
                >
                  <X size={12} aria-hidden="true" />
                </button>
              </span>
            ))}
          </div>
        )}

        <div className="prompt-composer__toolbar">
          <div className="composer__tools">
            <button
              type="button"
              className="icon-btn icon-btn--sm"
              onClick={() => fileInputRef.current?.click()}
              aria-label="إرفاق ملف"
              title="إرفاق ملف"
            >
              <Paperclip size={17} aria-hidden="true" />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              className="sr-only"
              aria-hidden="true"
              tabIndex={-1}
              onChange={(e) => {
                pickFiles(e.target.files);
                e.target.value = '';
              }}
            />

            <div className="model-pill">
              <button
                type="button"
                className="model-pill__trigger"
                onClick={() => setMenuOpen((o) => !o)}
                aria-haspopup="listbox"
                aria-expanded={menuOpen}
                aria-label="قوة النموذج"
              >
                <span className="model-pill__dot" aria-hidden="true" />
                <span>{strengthLabel}</span>
                <ChevronDown size={14} aria-hidden="true" />
              </button>
              {menuOpen && (
                <div className="model-pill__menu" role="listbox" aria-label="قوة النموذج">
                  {MODEL_STRENGTHS.map((s) => (
                    <button
                      key={s.value}
                      type="button"
                      role="option"
                      aria-selected={s.value === strength}
                      className={`model-pill__option${s.value === strength ? ' model-pill__option--active' : ''}`}
                      onClick={() => chooseStrength(s.value)}
                    >
                      {s.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="composer__actions">
            <button
              type="button"
              className="icon-btn icon-btn--sm"
              disabled
              title="قريباً"
              aria-label="الإدخال الصوتي"
            >
              <Mic size={17} aria-hidden="true" />
            </button>
            {isStreaming ? (
              <button
                type="button"
                className="composer__send composer__send--stop"
                onClick={onStop}
                aria-label="إيقاف توليد الرد"
              >
                <X size={18} aria-hidden="true" />
              </button>
            ) : (
              <button
                type="submit"
                className="composer__send"
                disabled={!canSend}
                aria-label="إرسال"
              >
                <ArrowUp size={18} aria-hidden="true" />
              </button>
            )}
          </div>
        </div>
      </div>
    </form>
  );
}

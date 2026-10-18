import { useState, useRef, type KeyboardEvent } from 'react';
import { Send, StopCircle } from 'lucide-react';
import { Button } from '../ui/Button';

export interface InputBoxProps {
  onSend: (message: string) => void;
  onStop?: () => void;
  isGenerating?: boolean;
  disabled?: boolean;
}

export function InputBox({ onSend, onStop, isGenerating = false, disabled = false }: InputBoxProps) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = () => {
    const trimmed = message.trim();
    if (!trimmed || isGenerating) return;
    onSend(trimmed);
    setMessage('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  };

  return (
    <div className="composer">
      <div className="composer__wrapper">
        <textarea
          ref={textareaRef}
          className="composer__textarea"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          placeholder="اكتب رسالتك هنا..."
          rows={1}
          disabled={disabled}
          aria-label="Chat message input"
        />
        <div className="composer__actions">
          {isGenerating && onStop ? (
            <Button
              variant="ghost"
              size="sm"
              onClick={onStop}
              aria-label="Stop generation"
            >
              <StopCircle size={20} />
            </Button>
          ) : (
            <Button
              variant="primary"
              size="sm"
              onClick={handleSubmit}
              disabled={!message.trim() || isGenerating || disabled}
              aria-label="Send message"
            >
              <Send size={18} />
            </Button>
          )}
        </div>
      </div>
      <p className="composer__hint">
        اضغط Enter للإرسال، Shift+Enter لسطر جديد
      </p>
    </div>
  );
}

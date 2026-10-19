import { type InputHTMLAttributes, forwardRef, useState, useId } from 'react';
import { Eye, EyeOff, AlertCircle } from 'lucide-react';

export interface PasswordInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
  containerClassName?: string;
}

export const PasswordInput = forwardRef<HTMLInputElement, PasswordInputProps>(
  ({ label, error, hint, id, className = '', containerClassName = '', ...props }, ref) => {
    const [showPassword, setShowPassword] = useState(false);
    const reactId = useId();
    const inputId = id || `password-${reactId}`;

    return (
      <div className={`input-group ${containerClassName}`}>
        {label && (
          <label htmlFor={inputId} className="input-group__label field__label">
            {label}
          </label>
        )}
        <div className={`input-wrapper input-wrapper--password ${error ? 'input-wrapper--error input--error' : ''}`}>
          <input
            ref={ref}
            id={inputId}
            type={showPassword ? 'text' : 'password'}
            className={`input-wrapper__field input ${className}`}
            aria-invalid={!!error}
            aria-describedby={error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined}
            dir="ltr"
            {...props}
          />
          <button
            type="button"
            className="input-wrapper__toggle-password"
            onClick={() => setShowPassword(!showPassword)}
            aria-label={showPassword ? 'إخفاء كلمة المرور' : 'إظهار كلمة المرور'}
            title={showPassword ? 'إخفاء كلمة المرور' : 'إظهار كلمة المرور'}
            tabIndex={-1}
          >
            {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>
        {error && (
          <p id={`${inputId}-error`} className="input-group__error field__error" role="alert">
            <AlertCircle size={14} aria-hidden="true" style={{ display: 'inline', marginInlineEnd: 4 }} />
            {error}
          </p>
        )}
        {hint && !error && (
          <p id={`${inputId}-hint`} className="input-group__hint field__hint">
            {hint}
          </p>
        )}
      </div>
    );
  }
);

PasswordInput.displayName = 'PasswordInput';

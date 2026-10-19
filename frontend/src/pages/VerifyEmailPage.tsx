/**
 * pages/VerifyEmailPage.tsx — OTP verification for new accounts
 */
import { useState, useRef, useEffect, type ClipboardEvent, type KeyboardEvent } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { AuthLayout } from '../components/layout/AuthLayout';
import { Button } from '../components/ui/Button';
import { api } from '../lib/api';

export function VerifyEmailPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const email = (location.state as { email?: string } | null)?.email || '';

  const [code, setCode] = useState<string[]>(['', '', '', '', '', '']);
  const [isLoading, setIsLoading] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Cooldown countdown effect
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = setInterval(() => {
      setResendCooldown((prev) => prev - 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [resendCooldown]);

  // Focus first input on mount
  useEffect(() => {
    inputRefs.current[0]?.focus();
  }, []);

  const handleChange = (index: number, val: string) => {
    // Only accept numeric input
    const clean = val.replace(/\D/g, '');
    if (!clean && val !== '') return;

    const newCode = [...code];
    newCode[index] = clean.slice(-1); // Take last digit
    setCode(newCode);
    setError(null);

    // Auto-focus next input if filled
    if (clean && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index: number, e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !code[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e: ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').trim().replace(/\D/g, '');
    if (!pasted) return;

    const digits = pasted.slice(0, 6).split('');
    const newCode = [...code];
    digits.forEach((d, i) => {
      newCode[i] = d;
    });
    setCode(newCode);
    setError(null);

    // Focus last filled or next input
    const focusIndex = Math.min(digits.length, 5);
    inputRefs.current[focusIndex]?.focus();
  };

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const fullCode = code.join('');

    if (fullCode.length !== 6) {
      setError('يرجى إدخال الرمز كاملاً (6 أرقام)');
      return;
    }

    if (!email) {
      setError('لم يتم تحديد البريد الإلكتروني. يرجى إعادة المحاولة من صفحة التسجيل.');
      return;
    }

    setIsLoading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      await api.post('/auth/verify-email', { email, code: fullCode });
      setSuccessMessage('تم التحقق من الحساب بنجاح! جاري تحويلك...');
      setTimeout(() => {
        navigate('/login', { state: { verified: true, email }, replace: true });
      }, 1200);
    } catch (err: any) {
      const msg = err.response?.data?.error?.message || err.message || 'فشل التحقق من الرمز';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleResend = async () => {
    if (resendCooldown > 0 || isResending) return;

    if (!email) {
      setError('البريد الإلكتروني مفقود. يرجى الرجوع لصفحة التسجيل.');
      return;
    }

    setIsResending(true);
    setError(null);

    try {
      await api.post('/auth/resend-code', { email });
      setSuccessMessage('تم إرسال رمز تحقق جديد إلى بريدك الإلكتروني.');
      setResendCooldown(60);
      setCode(['', '', '', '', '', '']);
      inputRefs.current[0]?.focus();
    } catch (err: any) {
      const msg = err.response?.data?.error?.message || err.message || 'فشل إرسال رمز التحقق';
      setError(msg);
    } finally {
      setIsResending(false);
    }
  };

  return (
    <AuthLayout
      title="التحقق من البريد الإلكتروني"
      subtitle={email ? `أرسلنا رمزاً مكوناً من 6 أرقام إلى ${email}` : 'أدخل الرمز المكون من 6 أرقام لتفعيل حسابك'}
    >
      <div className="card fade-in" style={{ padding: 'var(--space-6)', display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
        {error && (
          <div
            role="alert"
            style={{
              padding: 'var(--space-3)',
              borderRadius: 'var(--radius-md)',
              background: 'var(--color-error-bg)',
              color: 'var(--color-error)',
              fontSize: 'var(--text-sm)',
              textAlign: 'center',
            }}
          >
            {error}
          </div>
        )}

        {successMessage && (
          <div
            role="status"
            style={{
              padding: 'var(--space-3)',
              borderRadius: 'var(--radius-md)',
              background: 'var(--color-success-bg)',
              color: 'var(--color-accent)',
              fontSize: 'var(--text-sm)',
              textAlign: 'center',
              fontWeight: 'var(--font-medium)',
            }}
          >
            {successMessage}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          <div
            className="verify-inputs"
            dir="ltr"
            style={{
              display: 'flex',
              justifyContent: 'center',
              gap: 'var(--space-2)',
              marginBlock: 'var(--space-2)',
            }}
          >
            {code.map((digit, index) => (
              <input
                key={index}
                ref={(el) => { inputRefs.current[index] = el; }}
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={1}
                value={digit}
                onChange={(e) => handleChange(index, e.target.value)}
                onKeyDown={(e) => handleKeyDown(index, e)}
                onPaste={handlePaste}
                style={{
                  width: '46px',
                  height: '54px',
                  textAlign: 'center',
                  fontSize: 'var(--text-xl)',
                  fontWeight: 'var(--font-bold)',
                  color: 'var(--color-text-primary)',
                  backgroundColor: 'var(--color-surface)',
                  border: '2px solid var(--color-border)',
                  borderRadius: 'var(--radius-md)',
                  outline: 'none',
                  transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
                }}
                className="verify-digit-input"
                aria-label={`الرقم ${index + 1}`}
              />
            ))}
          </div>

          <Button
            type="submit"
            variant="primary"
            fullWidth
            isLoading={isLoading}
            disabled={code.join('').length !== 6 || isLoading}
          >
            تأكيد الحساب
          </Button>
        </form>

        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'var(--space-2)', marginTop: 'var(--space-2)' }}>
          <button
            type="button"
            onClick={handleResend}
            disabled={resendCooldown > 0 || isResending}
            className="text-accent text-sm"
            style={{
              background: 'none',
              border: 'none',
              cursor: resendCooldown > 0 ? 'not-allowed' : 'pointer',
              opacity: resendCooldown > 0 ? 0.6 : 1,
              textDecoration: 'underline',
              padding: 'var(--space-1)',
            }}
          >
            {isResending
              ? 'جاري إرسال الرمز...'
              : resendCooldown > 0
              ? `إعادة الإرسال بعد ${resendCooldown} ثانية`
              : 'لم يصلك الرمز؟ إعادة الإرسال'}
          </button>

          <Link to="/login" className="text-muted text-xs" style={{ marginTop: 'var(--space-2)' }}>
            العودة لتسجيل الدخول
          </Link>
        </div>
      </div>
    </AuthLayout>
  );
}

/**
 * pages/ForgotPasswordPage.tsx — Forgot Password Flow (spets.md Feature 3)
 */
import { useState, useRef, type KeyboardEvent, type ClipboardEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { AuthLayout } from '../components/layout/AuthLayout';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { PasswordInput } from '../components/ui/PasswordInput';
import { api } from '../lib/api';
import { CheckCircle2, ArrowRight } from 'lucide-react';

type Step = 'email' | 'code' | 'new-password' | 'success';

export function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>('email');
  const [email, setEmail] = useState('');
  const [code, setCode] = useState<string[]>(['', '', '', '', '', '']);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [resetToken, setResetToken] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resendMessage, setResendMessage] = useState<string | null>(null);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  const handleSendCode = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!email.trim() || !email.includes('@')) {
      setError('يرجى إدخال بريد إلكتروني صالح');
      return;
    }

    setIsLoading(true);
    setError(null);
    setResendMessage(null);

    try {
      await api.post('/auth/forgot-password', { email: email.trim().toLowerCase() });
      setStep('code');
      // Focus first digit
      setTimeout(() => inputRefs.current[0]?.focus(), 100);
    } catch (err: any) {
      setError(err.response?.data?.error?.message || err.message || 'حدث خطأ أثناء إرسال الرمز');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDigitChange = (index: number, val: string) => {
    const clean = val.replace(/\D/g, '');
    if (!clean && val !== '') return;

    const newCode = [...code];
    newCode[index] = clean.slice(-1);
    setCode(newCode);
    setError(null);

    if (clean && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleDigitKeyDown = (index: number, e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !code[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handleDigitPaste = (e: ClipboardEvent<HTMLInputElement>) => {
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

    const focusIndex = Math.min(digits.length, 5);
    inputRefs.current[focusIndex]?.focus();
  };

  const handleVerifyCode = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const fullCode = code.join('');

    if (fullCode.length !== 6) {
      setError('يرجى إدخال الرمز المكون من 6 أرقام');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await api.post('/auth/verify-reset-code', {
        email: email.trim().toLowerCase(),
        code: fullCode,
      });
      const token = response.data?.reset_token || response.data?.data?.reset_token;
      if (!token) {
        throw new Error('فشل استلام رمز استعادة كلمة المرور');
      }
      setResetToken(token);
      setStep('new-password');
    } catch (err: any) {
      setError(err.response?.data?.error?.message || err.message || 'رمز التحقق غير صحيح أو منتهي الصلاحية');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetPassword = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();

    if (newPassword.length < 8) {
      setError('كلمة المرور يجب أن تكون 8 أحرف على الأقل');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('كلمتا المرور غير متطابقتين');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await api.post('/auth/reset-password', {
        reset_token: resetToken,
        new_password: newPassword,
      });
      setStep('success');
    } catch (err: any) {
      setError(err.response?.data?.error?.message || err.message || 'فشل إعادة تعيين كلمة المرور');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResend = async () => {
    setIsLoading(true);
    setError(null);
    setResendMessage(null);
    try {
      await api.post('/auth/forgot-password', { email: email.trim().toLowerCase() });
      setResendMessage('تم إرسال رمز تحقق جديد إلى بريدك.');
      setCode(['', '', '', '', '', '']);
      inputRefs.current[0]?.focus();
    } catch (err: any) {
      setError(err.response?.data?.error?.message || err.message || 'فشل إعادة الإرسال');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout
      title={
        step === 'email'
          ? 'نسيت كلمة المرور؟'
          : step === 'code'
          ? 'أدخل رمز التحقق'
          : step === 'new-password'
          ? 'كلمة المرور الجديدة'
          : 'تم بنجاح!'
      }
      subtitle={
        step === 'email'
          ? 'أدخل بريدك الإلكتروني وسنرسل لك رمز التحقق'
          : step === 'code'
          ? `أرسلنا رمزاً مكوناً من 6 أرقام إلى ${email}`
          : step === 'new-password'
          ? 'أدخل كلمة المرور الجديدة لحسابك'
          : 'تم تغيير كلمة المرور بنجاح'
      }
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

        {resendMessage && (
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
            {resendMessage}
          </div>
        )}

        {/* ── STEP 1: Email ── */}
        {step === 'email' && (
          <form onSubmit={handleSendCode} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
            <div className="field">
              <label htmlFor="forgot-email" className="field__label field__label--required">
                البريد الإلكتروني
              </label>
              <Input
                id="forgot-email"
                type="email"
                dir="ltr"
                placeholder="example@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
              />
            </div>

            <Button type="submit" variant="primary" fullWidth isLoading={isLoading}>
              إرسال رمز التحقق
            </Button>

            <div style={{ textAlign: 'center', marginTop: 'var(--space-2)' }}>
              <Link to="/login" className="text-muted text-sm">
                تذكرت كلمة المرور؟ <span className="text-accent">تسجيل الدخول</span>
              </Link>
            </div>
          </form>
        )}

        {/* ── STEP 2: OTP Code ── */}
        {step === 'code' && (
          <form onSubmit={handleVerifyCode} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
            <div
              dir="ltr"
              style={{
                display: 'flex',
                justifyContent: 'center',
                gap: 'var(--space-2)',
                marginBlock: 'var(--space-2)',
              }}
            >
              {code.map((digit, idx) => (
                <input
                  key={idx}
                  ref={(el) => { inputRefs.current[idx] = el; }}
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={1}
                  value={digit}
                  onChange={(e) => handleDigitChange(idx, e.target.value)}
                  onKeyDown={(e) => handleDigitKeyDown(idx, e)}
                  onPaste={handleDigitPaste}
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
                  }}
                  aria-label={`الرقم ${idx + 1}`}
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
              تأكيد الرمز
            </Button>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 'var(--space-2)' }}>
              <button
                type="button"
                onClick={handleResend}
                disabled={isLoading}
                className="text-accent text-sm"
                style={{ background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}
              >
                لم يصلك الرمز؟ إعادة الإرسال
              </button>

              <button
                type="button"
                onClick={() => setStep('email')}
                className="text-muted text-xs"
                style={{ background: 'none', border: 'none', cursor: 'pointer' }}
              >
                تغيير البريد
              </button>
            </div>
          </form>
        )}

        {/* ── STEP 3: New Password ── */}
        {step === 'new-password' && (
          <form onSubmit={handleResetPassword} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
            <PasswordInput
              id="new-password"
              label="كلمة المرور الجديدة"
              placeholder="••••••••"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              hint="8 أحرف على الأقل"
              required
              autoFocus
            />

            <PasswordInput
              id="confirm-password"
              label="تأكيد كلمة المرور"
              placeholder="••••••••"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />

            <Button
              type="submit"
              variant="primary"
              fullWidth
              isLoading={isLoading}
              disabled={!newPassword || !confirmPassword || isLoading}
            >
              حفظ كلمة المرور الجديدة
            </Button>
          </form>
        )}

        {/* ── STEP 4: Success ── */}
        {step === 'success' && (
          <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'var(--space-4)', padding: 'var(--space-4) 0' }}>
            <CheckCircle2 size={56} style={{ color: 'var(--color-accent)' }} />
            <p style={{ fontSize: 'var(--text-base)', color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
              تم تحديث كلمة المرور لحسابك بنجاح. يمكنك الآن تسجيل الدخول باستخدام كلمة المرور الجديدة.
            </p>
            <Button
              variant="primary"
              fullWidth
              onClick={() => navigate('/login', { state: { email }, replace: true })}
            >
              الانتقال لتسجيل الدخول
              <ArrowRight size={16} style={{ marginInlineStart: 'var(--space-2)' }} />
            </Button>
          </div>
        )}
      </div>
    </AuthLayout>
  );
}

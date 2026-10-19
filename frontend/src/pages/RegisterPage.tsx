/**
 * pages/RegisterPage.tsx — New student registration
 * Supports referral capture via ?ref= (Phase 7 backend, Phase 9 UI).
 */
import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { useAuth } from '../contexts/useAuth';
import { AuthLayout } from '../components/layout/AuthLayout';
import { PasswordInput } from '../components/ui/PasswordInput';

const registerSchema = z.object({
  display_name: z.string().min(2, 'الاسم يجب أن يحتوي على حرفين على الأقل').max(200),
  email: z.string().email('بريد إلكتروني غير صحيح'),
  password: z.string()
    .min(8, 'كلمة المرور يجب أن تكون 8 أحرف على الأقل')
    .max(128),
  confirm_password: z.string(),
}).refine((d) => d.password === d.confirm_password, {
  message: 'كلمتا المرور غير متطابقتين',
  path: ['confirm_password'],
});

type RegisterForm = z.infer<typeof registerSchema>;

export function RegisterPage() {
  const { register: registerUser } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const refCode = searchParams.get('ref')?.trim() || undefined;
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterForm>({ resolver: zodResolver(registerSchema) });

  const onSubmit = async (data: RegisterForm) => {
    setServerError(null);
    try {
      await registerUser(data.email, data.password, data.display_name, refCode);
      navigate('/verify-email', { state: { email: data.email }, replace: true });
    } catch (err: unknown) {
      setServerError(err instanceof Error ? err.message : 'حدث خطأ أثناء إنشاء الحساب.');
    }
  };

  return (
    <AuthLayout title="إنشاء حساب جديد" subtitle="ابدأ مع Spetser AI مجاناً">
      <form
        onSubmit={handleSubmit(onSubmit)}
        className="card fade-in"
        style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}
        noValidate
      >
        {refCode && (
          <div
            role="status"
            style={{
              padding: 'var(--space-3)', borderRadius: 'var(--radius-md)',
              background: 'var(--color-success-bg)', color: 'var(--color-success)',
              fontSize: 'var(--text-sm)', textAlign: 'center',
            }}
          >
            🎉 تم استخدام رابط دعوة — سجّل عبر الصديق الذي دعاك!
          </div>
        )}

        {serverError && (
          <div
            role="alert"
            style={{
              padding: 'var(--space-3)', borderRadius: 'var(--radius-md)',
              background: 'var(--color-error-bg)', color: 'var(--color-error)',
              fontSize: 'var(--text-sm)',
            }}
          >
            {serverError}
          </div>
        )}

        <div className="field">
          <label htmlFor="reg-name" className="field__label field__label--required">الاسم</label>
          <input id="reg-name" type="text" autoComplete="name"
            className={`input${errors.display_name ? ' input--error' : ''}`}
            {...register('display_name')} />
          {errors.display_name && <span className="field__error" role="alert">{errors.display_name.message}</span>}
        </div>

        <div className="field">
          <label htmlFor="reg-email" className="field__label field__label--required">البريد الإلكتروني</label>
          <input id="reg-email" type="email" autoComplete="email" dir="ltr"
            className={`input${errors.email ? ' input--error' : ''}`}
            {...register('email')} />
          {errors.email && <span className="field__error" role="alert">{errors.email.message}</span>}
        </div>

        <PasswordInput
          id="reg-password"
          label="كلمة المرور"
          autoComplete="new-password"
          hint="8 أحرف على الأقل"
          error={errors.password?.message}
          {...register('password')}
        />

        <PasswordInput
          id="reg-confirm"
          label="تأكيد كلمة المرور"
          autoComplete="new-password"
          error={errors.confirm_password?.message}
          {...register('confirm_password')}
        />

        <button type="submit"
          className={`btn btn--primary btn--full${isSubmitting ? ' btn--loading' : ''}`}
          disabled={isSubmitting} aria-busy={isSubmitting}>
          {!isSubmitting && 'إنشاء الحساب'}
        </button>

        <p className="text-sm text-muted" style={{ textAlign: 'center' }}>
          لديك حساب بالفعل؟{' '}
          <Link to="/login" className="text-accent">تسجيل الدخول</Link>
        </p>
      </form>
    </AuthLayout>
  );
}

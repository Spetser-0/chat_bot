/**
 * pages/RegisterPage.tsx — New student registration
 */
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { useAuth } from '../contexts/AuthContext';

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
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterForm>({ resolver: zodResolver(registerSchema) });

  const onSubmit = async (data: RegisterForm) => {
    setServerError(null);
    try {
      await registerUser(data.email, data.password, data.display_name);
      navigate('/', { replace: true });
    } catch (err: any) {
      setServerError(err.message || 'حدث خطأ أثناء إنشاء الحساب.');
    }
  };

  return (
    <div style={{ maxWidth: 420, margin: '0 auto', paddingTop: 'var(--space-8)' }}>
      <div style={{ textAlign: 'center', marginBottom: 'var(--space-8)' }}>
        <div style={{
          width: 48, height: 48,
          background: 'var(--color-deep-teal)',
          borderRadius: 'var(--radius-lg)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: 'white', fontSize: 'var(--text-xl)', fontWeight: 'var(--font-semibold)',
          margin: '0 auto var(--space-4)',
        }} aria-hidden="true">
          س
        </div>
        <h1 style={{ fontSize: 'var(--text-xl)', fontWeight: 'var(--font-semibold)', marginBottom: 'var(--space-1)' }}>
          إنشاء حساب جديد
        </h1>
        <p className="text-muted text-sm">ابدأ مع Spetser AI مجاناً</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="card fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }} noValidate>
        {serverError && (
          <div role="alert" style={{ background: 'var(--color-error-bg)', padding: 'var(--space-3)', borderRadius: 'var(--radius-md)', color: 'var(--color-error)', fontSize: 'var(--text-sm)' }}>
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

        <div className="field">
          <label htmlFor="reg-password" className="field__label field__label--required">كلمة المرور</label>
          <input id="reg-password" type="password" autoComplete="new-password" dir="ltr"
            className={`input${errors.password ? ' input--error' : ''}`}
            {...register('password')} />
          {errors.password && <span className="field__error" role="alert">{errors.password.message}</span>}
          <span className="field__hint">8 أحرف على الأقل</span>
        </div>

        <div className="field">
          <label htmlFor="reg-confirm" className="field__label field__label--required">تأكيد كلمة المرور</label>
          <input id="reg-confirm" type="password" autoComplete="new-password" dir="ltr"
            className={`input${errors.confirm_password ? ' input--error' : ''}`}
            {...register('confirm_password')} />
          {errors.confirm_password && <span className="field__error" role="alert">{errors.confirm_password.message}</span>}
        </div>

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
    </div>
  );
}

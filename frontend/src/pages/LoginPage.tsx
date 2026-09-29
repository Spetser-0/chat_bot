/**
 * pages/LoginPage.tsx — Login form with RTL layout
 */
import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { useAuth } from '../contexts/AuthContext';

const loginSchema = z.object({
  email: z.string().email('بريد إلكتروني غير صحيح'),
  password: z.string().min(1, 'كلمة المرور مطلوبة'),
});

type LoginForm = z.infer<typeof loginSchema>;

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [serverError, setServerError] = useState<string | null>(null);

  const from = (location.state as any)?.from?.pathname || '/';

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) });

  const onSubmit = async (data: LoginForm) => {
    setServerError(null);
    try {
      await login(data.email, data.password);
      navigate(from, { replace: true });
    } catch (err: any) {
      setServerError(err.message || 'حدث خطأ. يرجى المحاولة مجدداً.');
    }
  };

  return (
    <div style={{ maxWidth: 400, margin: '0 auto', paddingTop: 'var(--space-8)' }}>
      {/* Brand */}
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
          تسجيل الدخول
        </h1>
        <p className="text-muted text-sm">
          مرحباً بك في Spetser AI
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="card fade-in" style={{ gap: 'var(--space-4)', display: 'flex', flexDirection: 'column' }} noValidate>
        {/* Server error */}
        {serverError && (
          <div role="alert" className="error-state" style={{ padding: 'var(--space-3)', borderRadius: 'var(--radius-md)', background: 'var(--color-error-bg)' }}>
            <span className="text-error text-sm">{serverError}</span>
          </div>
        )}

        {/* Email */}
        <div className="field">
          <label htmlFor="login-email" className="field__label field__label--required">
            البريد الإلكتروني
          </label>
          <input
            id="login-email"
            type="email"
            autoComplete="email"
            dir="ltr"
            className={`input${errors.email ? ' input--error' : ''}`}
            {...register('email')}
          />
          {errors.email && (
            <span className="field__error" role="alert">{errors.email.message}</span>
          )}
        </div>

        {/* Password */}
        <div className="field">
          <label htmlFor="login-password" className="field__label field__label--required">
            كلمة المرور
          </label>
          <input
            id="login-password"
            type="password"
            autoComplete="current-password"
            dir="ltr"
            className={`input${errors.password ? ' input--error' : ''}`}
            {...register('password')}
          />
          {errors.password && (
            <span className="field__error" role="alert">{errors.password.message}</span>
          )}
        </div>

        <button
          type="submit"
          className={`btn btn--primary btn--full${isSubmitting ? ' btn--loading' : ''}`}
          disabled={isSubmitting}
          aria-busy={isSubmitting}
        >
          {!isSubmitting && 'دخول'}
        </button>

        <p className="text-sm text-muted" style={{ textAlign: 'center' }}>
          ليس لديك حساب؟{' '}
          <Link to="/register" className="text-accent">إنشاء حساب</Link>
        </p>
      </form>
    </div>
  );
}

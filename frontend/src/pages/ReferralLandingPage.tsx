/**
 * pages/ReferralLandingPage.tsx
 * ─────────────────────────────
 * Public referral landing at /r/:code (Phase 9, Lesson 9.3).
 * Validates the code via GET /referrals/{code}/validate and funnels
 * the visitor to /register?ref=CODE (backend captures ?ref= — Phase 7).
 */
import { Link, Navigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AuthLayout } from '../components/layout/AuthLayout';
import { useAuth } from '../contexts/useAuth';
import { referralsApi } from '../api/referrals';

type LandingState = 'loading' | 'valid' | 'invalid';

export function ReferralLandingPage() {
  const { code = '' } = useParams<{ code: string }>();
  const { isAuthenticated } = useAuth();

  const { data, isLoading } = useQuery({
    queryKey: ['referral', 'validate', code],
    queryFn: () => referralsApi.validate(code),
    enabled: code.length > 0,
    retry: false,
    staleTime: 60_000,
  });

  const state: LandingState = isLoading ? 'loading' : data?.valid ? 'valid' : 'invalid';

  // Already logged in — no need to register.
  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  if (state === 'loading') {
    return (
      <AuthLayout title="جاري التحقق من رابط الدعوة…">
        <div className="empty-state" role="status" aria-live="polite">
          <div className="spinner spinner--lg" />
        </div>
      </AuthLayout>
    );
  }

  if (state === 'invalid') {
    return (
      <AuthLayout title="رابط الدعوة غير صالح" subtitle="كود الدعوة غير موجود أو تم إلغاؤه.">
        <div className="card" style={{ textAlign: 'center', gap: 'var(--space-4)', display: 'flex', flexDirection: 'column' }}>
          <p className="text-secondary text-sm">
            يمكنك إنشاء حساب جديد مباشرة والاستفادة لاحقاً من روابط الدعوة الخاصة بك.
          </p>
          <Link to="/register" className="btn btn--primary btn--full">
            إنشاء حساب
          </Link>
          <Link to="/login" className="btn btn--ghost btn--full">
            لدي حساب بالفعل
          </Link>
        </div>
      </AuthLayout>
    );
  }

  const referrerName = data?.referrer_display_name || 'صديقك';

  return (
    <AuthLayout
      title={`${referrerName} دعاك للانضمام`}
      subtitle="انضم إلى Spetser AI وابدأ رحلتك الأكاديمية مع الذكاء الاصطناعي."
    >
      <div
        className="card fade-in"
        style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)', textAlign: 'center' }}
      >
        <div style={{ fontSize: '2rem' }} aria-hidden="true">🎉</div>
        <p className="text-secondary text-sm">
          قم بإنشاء حسابك الآن — سيتم توثيق الدعوة تلقائياً عبر رابط الصديق.
        </p>
        <Link
          to={`/register?ref=${encodeURIComponent(code)}`}
          className="btn btn--primary btn--full"
          aria-label="إنشاء حساب عبر رابط الدعوة"
        >
          إنشاء حساب وقبول الدعوة
        </Link>
        <Link to="/login" className="btn btn--ghost btn--full">
          لدي حساب بالفعل — تسجيل الدخول
        </Link>
      </div>
    </AuthLayout>
  );
}

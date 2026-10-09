/**
 * pages/ReferralPage.tsx
 * ──────────────────────
 * "Invite Friends" page (Phase 9, Lesson 9.7).
 * Shows the personal referral link + code, copy button, share shortcuts,
 * and stats: invited / qualified / rewarded / earnings.
 */
import { useCallback, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useReferral } from '../hooks/useReferral';

export function ReferralPage() {
  const { stats, isLoading, isError, refetch } = useReferral();
  const queryClient = useQueryClient();
  const [copied, setCopied] = useState(false);
  const referralLink = stats?.referral_link ?? '';

  const copyLink = useCallback(async () => {
    if (!referralLink) return;
    try {
      await navigator.clipboard.writeText(referralLink);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable */
    }
  }, [referralLink]);

  const refresh = useCallback(async () => {
    await refetch();
    void queryClient.invalidateQueries({ queryKey: ['auth', 'me'] });
  }, [queryClient, refetch]);

  if (isLoading) {
    return (
      <div className="empty-state" role="status" aria-live="polite">
        <div className="spinner spinner--lg" />
      </div>
    );
  }

  if (isError || !stats) {
    return (
      <div className="empty-state">
        <div className="empty-state__icon">⚠️</div>
        <div className="empty-state__title">تعذر تحميل بيانات الدعوة</div>
        <button className="btn btn--primary" onClick={refresh}>
          إعادة المحاولة
        </button>
      </div>
    );
  }

  const shareText = encodeURIComponent(
    `انضم إلى Spetser AI عبر رابطي وابدأ رحلتك الأكاديمية مع الذكاء الاصطناعي! ${stats.referral_link}`,
  );
  const whatsappUrl = `https://wa.me/?text=${shareText}`;
  const telegramUrl = `https://t.me/share/url?url=${encodeURIComponent(stats.referral_link)}&text=${encodeURIComponent('انضم إلى Spetser AI!')}`;

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)', maxWidth: 720 }}>
      <div>
        <h1 style={{ fontSize: 'var(--text-2xl)', fontWeight: 'var(--font-semibold)', marginBottom: 'var(--space-1)' }}>
          🎁 ادعُ أصدقاءك واكسب رصيداً
        </h1>
        <p className="text-secondary text-sm">
          شارك رابطك الخاص — عند شحن رصيد صديقك يصلك عمولة تلقائياً بعد فترة حجز قصيرة.
        </p>
      </div>

      {/* Link + copy */}
      <section className="card" aria-labelledby="referral-link-title" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
        <h2 id="referral-link-title" className="text-lg font-semibold">
          رابط الدعوة الخاص بك
        </h2>
        <div className="code-block" dir="ltr">
          <div className="code-block__header">
            <span className="code-block__lang">referral link</span>
            <button
              type="button"
              className="code-copy-btn"
              onClick={copyLink}
              aria-label={copied ? 'تم النسخ' : 'نسخ الرابط'}
            >
              {copied ? '✓ نُسخ' : '📋 نسخ'}
            </button>
          </div>
          <pre className="code-block__pre">
            <code>{stats.referral_link}</code>
          </pre>
        </div>
        <p className="text-sm text-muted">
          الكود: <code className="inline-code" dir="ltr">{stats.referral_code}</code>
        </p>
        <div className="flex gap-2" style={{ flexWrap: 'wrap' }}>
          <a
            className="btn btn--secondary btn--sm"
            href={whatsappUrl}
            target="_blank"
            rel="noopener noreferrer"
          >
            📲 واتساب
          </a>
          <a
            className="btn btn--secondary btn--sm"
            href={telegramUrl}
            target="_blank"
            rel="noopener noreferrer"
          >
            ✈️ تيليجرام
          </a>
          <button className="btn btn--ghost btn--sm" onClick={copyLink}>
            📋 نسخ الرابط
          </button>
        </div>
      </section>

      {/* Stats */}
      <section aria-labelledby="referral-stats-title" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
        <div className="flex items-center justify-between">
          <h2 id="referral-stats-title" className="text-lg font-semibold">
            إحصائياتك
          </h2>
          <button className="btn btn--ghost btn--sm" onClick={refresh} aria-label="تحديث الإحصائيات">
            🔄 تحديث
          </button>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 'var(--space-3)' }}>
          <div className="card" style={{ textAlign: 'center', padding: 'var(--space-4)' }}>
            <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 'var(--font-semibold)' }}>
              {stats.total_referrals}
            </div>
            <div className="text-sm text-muted">أصدقاء مدعوون</div>
          </div>
          <div className="card" style={{ textAlign: 'center', padding: 'var(--space-4)' }}>
            <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 'var(--font-semibold)' }}>
              {stats.qualified_referrals}
            </div>
            <div className="text-sm text-muted">مؤهلون (شحنوا رصيداً)</div>
          </div>
          <div className="card" style={{ textAlign: 'center', padding: 'var(--space-4)' }}>
            <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 'var(--font-semibold)' }}>
              {stats.rewarded_referrals}
            </div>
            <div className="text-sm text-muted">مكافآت مدفوعة</div>
          </div>
          <div className="card" style={{ textAlign: 'center', padding: 'var(--space-4)' }}>
            <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 'var(--font-semibold)', color: 'var(--color-accent)' }}>
              ${Number(stats.total_earnings_usd || 0).toFixed(2)}
            </div>
            <div className="text-sm text-muted">إجمالي الأرباح</div>
          </div>
        </div>
        <p className="text-xs text-muted">
          تُطلق المكافأة بعد نجاح دفعة الصديق وفترة حجز قصيرة (حماية من إساءة الاستخدام).
        </p>
      </section>
    </div>
  );
}

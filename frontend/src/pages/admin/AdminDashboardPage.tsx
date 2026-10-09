/**
 * pages/admin/AdminDashboardPage.tsx
 * ──────────────────────────────────
 * Analytics overview (Phase 9, Lesson 9.8): users, messages, revenue,
 * referrals + paid invoice stats + LLM usage by provider (top rows).
 */
import { useQuery } from '@tanstack/react-query';
import { adminApi } from '../../api/admin';

function StatCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <div className="admin-stat-card">
      <div className="admin-stat-card__label">{label}</div>
      <div className="admin-stat-card__value">{value}</div>
      {hint && <div className="admin-stat-card__hint">{hint}</div>}
    </div>
  );
}

export function AdminDashboardPage() {
  const overview = useQuery({
    queryKey: ['admin', 'analytics', 'overview'],
    queryFn: () => adminApi.analyticsOverview(),
    staleTime: 30_000,
  });
  const revenue = useQuery({
    queryKey: ['admin', 'analytics', 'revenue'],
    queryFn: () => adminApi.analyticsRevenue(),
    staleTime: 30_000,
  });
  const llm = useQuery({
    queryKey: ['admin', 'analytics', 'llm'],
    queryFn: () => adminApi.analyticsLlmUsage(30),
    staleTime: 60_000,
  });
  const referrals = useQuery({
    queryKey: ['admin', 'analytics', 'referrals'],
    queryFn: () => adminApi.analyticsReferrals(),
    staleTime: 30_000,
  });

  if (overview.isLoading || overview.isError) {
    return (
      <div className="admin-page">
        <h1 className="admin-page__title">نظرة عامة</h1>
        {overview.isLoading ? (
          <div className="flex items-center justify-center p-8">
            <div className="spinner spinner--lg" />
          </div>
        ) : (
          <div className="admin-error" role="alert">
            <span>تعذر تحميل البيانات.</span>
            <button className="btn btn--secondary btn--sm" onClick={() => overview.refetch()}>
              إعادة المحاولة
            </button>
          </div>
        )}
      </div>
    );
  }

  const o = overview.data!;
  const rev = revenue.data;
  const llmData = llm.data;
  const ref = referrals.data;

  return (
    <div className="admin-page">
      <h1 className="admin-page__title">نظرة عامة</h1>
      <p className="admin-page__desc">صحة المنصة: المستخدمون، الرسائل، الإيرادات، الدعوات.</p>

      <div className="admin-stat-grid">
        <StatCard label="إجمالي المستخدمين" value={o.users.total} hint={`+${o.users.new_last_7d} في 7 أيام`} />
        <StatCard label="إجمالي الرسائل" value={o.messages.total} hint={`${o.messages.assistant_last_7d} مساعد في 7 أيام`} />
        <StatCard
          label="إجمالي الإيرادات"
          value={`$${Number(o.revenue.total_usd).toFixed(2)}`}
          hint={`+$${Number(o.revenue.usd_last_7d).toFixed(2)} في 7 أيام`}
        />
        <StatCard
          label="الدعوات"
          value={o.referrals.total}
          hint={`${o.referrals.qualified} مؤهلة (${(o.referrals.conversion_rate * 100).toFixed(1)}%)`}
        />
      </div>

      {rev && (
        <section className="admin-section" aria-label="الإيرادات حسب الحالة">
          <h2 className="admin-section__title">الإيرادات حسب الحالة</h2>
          <div className="admin-stat-grid admin-stat-grid--sm">
            <StatCard
              label="فواتير مدفوعة"
              value={rev.paid.count}
              hint={`متوسط $${Number(rev.paid.average_usd).toFixed(2)}`}
            />
            {rev.by_status.map((s) => (
              <StatCard key={s.status} label={s.status} value={s.count} hint={`$${Number(s.total_usd).toFixed(2)}`} />
            ))}
          </div>
        </section>
      )}

      {ref && (
        <section className="admin-section" aria-label="مكافآت الدعوات">
          <h2 className="admin-section__title">مكافآت الدعوات</h2>
          <div className="admin-stat-grid admin-stat-grid--sm">
            <StatCard label="قيد الانتظار" value={ref.rewards.pending_count} hint={`$${Number(ref.rewards.pending_amount_usd).toFixed(2)}`} />
            <StatCard label="مدفوعة" value={ref.rewards.paid_count} hint={`$${Number(ref.rewards.paid_amount_usd).toFixed(2)}`} />
          </div>
        </section>
      )}

      {llmData && llmData.by_provider.length > 0 && (
        <section className="admin-section" aria-label="استخدام LLM">
          <h2 className="admin-section__title">استخدام LLM (آخر {llmData.window_days} يوم)</h2>
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>المزود</th>
                  <th>الرسائل</th>
                  <th>إدخال</th>
                  <th>إخراج</th>
                  <th>متوسط الاستجابة</th>
                </tr>
              </thead>
              <tbody>
                {llmData.by_provider.map((row) => (
                  <tr key={row.provider_name}>
                    <td>{row.provider_name}</td>
                    <td>{row.messages}</td>
                    <td>{row.input_tokens.toLocaleString('en')}</td>
                    <td>{row.output_tokens.toLocaleString('en')}</td>
                    <td>{row.avg_latency_ms != null ? `${row.avg_latency_ms}ms` : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {llmData && llmData.by_skill.length > 0 && (
        <section className="admin-section" aria-label="استخدام المهارات">
          <h2 className="admin-section__title">الاستخدام حسب المهارة</h2>
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>المهارة</th>
                  <th>الرسائل</th>
                  <th>إدخال</th>
                  <th>إخراج</th>
                </tr>
              </thead>
              <tbody>
                {llmData.by_skill.map((row) => (
                  <tr key={row.skill_slug}>
                    <td>{row.skill_slug}</td>
                    <td>{row.messages}</td>
                    <td>{row.input_tokens.toLocaleString('en')}</td>
                    <td>{row.output_tokens.toLocaleString('en')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

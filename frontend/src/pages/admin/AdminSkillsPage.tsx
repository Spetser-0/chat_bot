/**
 * pages/admin/AdminSkillsPage.tsx
 * ──────────────────────────────
 * Skill management (Phase 9, Lesson 9.8): list, toggle public/premium,
 * delete, test dry-run. Full prompt editor deferred (no system_prompt
 * exposure in list UI beyond what's needed for edit).
 */
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { adminApi, type AdminSkill } from '../../api/admin';
import { AdminTable, AdminEmptyRow } from '../../components/admin/AdminTable';

export function AdminSkillsPage() {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<AdminSkill | null>(null);
  const [testMessage, setTestMessage] = useState('مرحبا، اختبار المهارة');
  const [testResult, setTestResult] = useState<string | null>(null);

  const listQuery = useQuery({
    queryKey: ['admin', 'skills'],
    queryFn: () => adminApi.listSkills(),
  });
  const countQuery = useQuery({
    queryKey: ['admin', 'skills', 'count'],
    queryFn: () => adminApi.skillCount(),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['admin', 'skills'] });

  const updateMut = useMutation({
    mutationFn: ({ id, body }: { id: string; body: { is_public?: boolean; is_premium?: boolean } }) =>
      adminApi.updateSkill(id, body),
    onSuccess: invalidate,
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => adminApi.deleteSkill(id),
    onSuccess: () => {
      invalidate();
      setSelected(null);
    },
  });

  const testMut = useMutation({
    mutationFn: ({ id, msg }: { id: string; msg: string }) => adminApi.testSkill(id, msg),
    onSuccess: (data) => {
      setTestResult(data.reply_text ?? data.note ?? 'لا يوجد رد.');
    },
    onError: () => setTestResult('فشل اختبار المهارة.'),
  });

  return (
    <div className="admin-page">
      <h1 className="admin-page__title">المهارات</h1>
      <p className="admin-page__desc">
        {countQuery.data
          ? `الإجمالي: ${countQuery.data.total} · عامة: ${countQuery.data.public}`
          : 'مهارات المنصة وحالات النشر.'}
      </p>

      <AdminTable
        columns={['الاسم', 'slug', 'عام', 'مميز', 'الإصدار', 'إجراءات']}
        loading={listQuery.isLoading}
        error={listQuery.isError ? 'تعذر تحميل المهارات.' : null}
        onRetry={() => listQuery.refetch()}
      >
        {listQuery.data?.length === 0 && <AdminEmptyRow colSpan={6} message="لا توجد مهارات." />}
        {listQuery.data?.map((s) => (
          <tr key={s.id}>
            <td>{s.name}</td>
            <td className="admin-table__mono">{s.slug}</td>
            <td>
              <button
                className={`badge ${s.is_public ? 'badge--success' : 'badge--muted'}`}
                onClick={() => updateMut.mutate({ id: s.id, body: { is_public: !s.is_public } })}
                disabled={updateMut.isPending}
                aria-label={`تبديل حالة النشر لـ ${s.name}`}
              >
                {s.is_public ? 'عام' : 'خاص'}
              </button>
            </td>
            <td>
              <span className={`badge ${s.is_premium ? 'badge--warning' : 'badge--muted'}`}>
                {s.is_premium ? '⭐ مميز' : 'عادي'}
              </span>
            </td>
            <td>v{s.version}</td>
            <td className="admin-table__actions">
              <button className="btn btn--secondary btn--sm" onClick={() => { setSelected(s); setTestResult(null); }}>
                تفاصيل
              </button>
              <button
                className="btn btn--danger btn--sm"
                onClick={() => {
                  if (window.confirm(`حذف المهارة "${s.name}"؟ لا يمكن التراجع.`)) {
                    deleteMut.mutate(s.id);
                  }
                }}
                disabled={deleteMut.isPending}
              >
                حذف
              </button>
            </td>
          </tr>
        ))}
      </AdminTable>

      {selected && (
        <div className="admin-detail" role="dialog" aria-label={`تفاصيل ${selected.name}`}>
          <div className="admin-detail__header">
            <h2 className="admin-detail__title">{selected.name}</h2>
            <button className="btn btn--ghost btn--sm" onClick={() => setSelected(null)} aria-label="إغلاق">
              ✕
            </button>
          </div>
          <div className="admin-detail__meta">
            <span>slug: {selected.slug}</span>
            <span>حرارة: {selected.temperature}</span>
            <span>max_tokens: {selected.max_tokens}</span>
            <span>تكلفة ×{selected.cost_multiplier}</span>
            <span>الأدوات: {selected.tools.map((t) => t.tool_name).join(', ') || 'لا شيء'}</span>
          </div>
          <section className="admin-detail__section">
            <h3>System Prompt</h3>
            <pre className="admin-code-block">{selected.system_prompt}</pre>
          </section>
          <section className="admin-detail__section">
            <h3>اختبار سريع</h3>
            <div className="admin-form-row">
              <input
                className="input"
                value={testMessage}
                onChange={(e) => setTestMessage(e.target.value)}
                placeholder="رسالة تجريبية"
                aria-label="رسالة اختبار"
              />
              <button
                className="btn btn--primary btn--sm"
                disabled={testMut.isPending || !testMessage.trim()}
                onClick={() => testMut.mutate({ id: selected.id, msg: testMessage })}
              >
                اختبار
              </button>
            </div>
            {testResult && <pre className="admin-code-block">{testResult}</pre>}
          </section>
        </div>
      )}
    </div>
  );
}

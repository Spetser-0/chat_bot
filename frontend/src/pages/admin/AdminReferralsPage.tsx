/**
 * pages/admin/AdminReferralsPage.tsx
 * ──────────────────────────────────
 * Referral management (Phase 9, Lesson 9.8): list, revoke, release,
 * release-all-due.
 */
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { adminApi, type AdminReferral } from '../../api/admin';
import { AdminTable, AdminEmptyRow } from '../../components/admin/AdminTable';

const STATUS_LABELS: Record<string, string> = {
  pending: 'قيد الانتظار',
  qualified: 'مؤهل',
  rewarded: 'مكافأة مدفوعة',
  revoked: 'ملغاة',
};

function statusBadge(status: string): string {
  if (status === 'rewarded') return 'badge badge--success';
  if (status === 'qualified') return 'badge badge--teal';
  if (status === 'revoked') return 'badge badge--error';
  return 'badge badge--warning';
}

export function AdminReferralsPage() {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState('');
  const [offset, setOffset] = useState(0);
  const [releaseResult, setReleaseResult] = useState<string | null>(null);
  const limit = 50;

  const listQuery = useQuery({
    queryKey: ['admin', 'referrals', status, offset],
    queryFn: () => adminApi.listReferrals({ status: status || undefined, limit, offset }),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['admin', 'referrals'] });

  const revokeMut = useMutation({
    mutationFn: (id: string) => adminApi.revokeReferral(id),
    onSuccess: invalidate,
  });
  const releaseMut = useMutation({
    mutationFn: (id: string) => adminApi.releaseReferral(id),
    onSuccess: invalidate,
  });
  const releaseDueMut = useMutation({
    mutationFn: () => adminApi.releaseDueRewards(),
    onSuccess: (data) => {
      setReleaseResult(`تم تحرير ${data.released_count} مكافأة بقيمة $${Number(data.total_amount).toFixed(2)}`);
      invalidate();
    },
  });

  const count = listQuery.data?.count ?? 0;

  return (
    <div className="admin-page">
      <div className="admin-page__header">
        <div>
          <h1 className="admin-page__title">الدعوات والمكافآت</h1>
          <p className="admin-page__desc">إدارة دعوات الطلاب ومكافآت الاحتفاظ.</p>
        </div>
        <button
          className="btn btn--secondary"
          onClick={() => releaseDueMut.mutate()}
          disabled={releaseDueMut.isPending}
        >
          تحرير المكافآت المستحقة
        </button>
      </div>

      {releaseResult && <p className="admin-success__text">{releaseResult}</p>}

      <div className="admin-filters">
        <select
          className="input"
          value={status}
          onChange={(e) => { setStatus(e.target.value); setOffset(0); }}
          aria-label="تصفية بالحالة"
        >
          <option value="">كل الحالات</option>
          <option value="pending">قيد الانتظار</option>
          <option value="qualified">مؤهل</option>
          <option value="rewarded">مكافأة مدفوعة</option>
          <option value="revoked">ملغاة</option>
        </select>
      </div>

      <AdminTable
        columns={['الدافع', 'المُدعى', 'الحالة', 'المكافأة', 'إجراءات']}
        loading={listQuery.isLoading}
        error={listQuery.isError ? 'تعذر تحميل الدعوات.' : null}
        onRetry={() => listQuery.refetch()}
      >
        {listQuery.data?.items.length === 0 && <AdminEmptyRow colSpan={5} message="لا توجد دعوات." />}
        {listQuery.data?.items.map((r: AdminReferral) => (
          <tr key={r.id}>
            <td className="admin-table__mono">{r.referrer_email ?? r.referrer_user_id.slice(0, 8)}</td>
            <td className="admin-table__mono">{r.referred_email ?? r.referred_user_id.slice(0, 8)}</td>
            <td><span className={statusBadge(r.status)}>{STATUS_LABELS[r.status] ?? r.status}</span></td>
            <td>
              {r.reward_amount
                ? `$${Number(r.reward_amount).toFixed(2)} (${r.reward_status})`
                : '—'}
            </td>
            <td className="admin-table__actions">
              {r.status !== 'revoked' && r.status !== 'rewarded' && (
                <>
                  <button
                    className="btn btn--secondary btn--sm"
                    disabled={releaseMut.isPending}
                    onClick={() => releaseMut.mutate(r.id)}
                  >
                    تحرير
                  </button>
                  <button
                    className="btn btn--danger btn--sm"
                    disabled={revokeMut.isPending}
                    onClick={() => {
                      if (window.confirm('إلغاء هذه الدعوة وتجاهل المكافأة غير المدفوعة؟')) {
                        revokeMut.mutate(r.id);
                      }
                    }}
                  >
                    إلغاء
                  </button>
                </>
              )}
            </td>
          </tr>
        ))}
      </AdminTable>

      <div className="admin-pagination">
        <button
          className="btn btn--secondary btn--sm"
          disabled={offset === 0}
          onClick={() => setOffset(Math.max(0, offset - limit))}
        >
          السابق
        </button>
        <span className="text-sm text-secondary">
          {offset + 1}–{Math.min(offset + limit, count)} من {count}
        </span>
        <button
          className="btn btn--secondary btn--sm"
          disabled={offset + limit >= count}
          onClick={() => setOffset(offset + limit)}
        >
          التالي
        </button>
      </div>
    </div>
  );
}

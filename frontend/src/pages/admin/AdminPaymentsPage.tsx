/**
 * pages/admin/AdminPaymentsPage.tsx
 * ─────────────────────────────────
 * Payment invoices (Phase 9, Lesson 9.8): list, filter by status,
 * detail with webhook history, superadmin manual-confirm.
 */
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { adminApi, type AdminInvoice } from '../../api/admin';
import { useAuth } from '../../contexts/useAuth';
import { AdminTable, AdminEmptyRow } from '../../components/admin/AdminTable';

const STATUS_LABELS: Record<string, string> = {
  pending: 'قيد الانتظار',
  paid: 'مدفوعة',
  expired: 'منتهية',
  failed: 'فاشلة',
};

function statusBadge(status: string): string {
  if (status === 'paid') return 'badge badge--success';
  if (status === 'pending') return 'badge badge--warning';
  return 'badge badge--error';
}

export function AdminPaymentsPage() {
  const { student } = useAuth();
  const queryClient = useQueryClient();
  const [status, setStatus] = useState('');
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<AdminInvoice | null>(null);
  const [confirmReason, setConfirmReason] = useState('');
  const limit = 50;

  const isSuperadmin = student?.role === 'superadmin';

  const listQuery = useQuery({
    queryKey: ['admin', 'payments', status, offset],
    queryFn: () => adminApi.listPayments({ status: status || undefined, limit, offset }),
  });

  const detailQuery = useQuery({
    queryKey: ['admin', 'payments', selected?.id],
    queryFn: () => adminApi.getPayment(selected!.id),
    enabled: !!selected,
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'payments'] });
  };

  const confirmMut = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => adminApi.manualConfirm(id, reason),
    onSuccess: () => {
      invalidate();
      setSelected(null);
      setConfirmReason('');
    },
  });

  const total = listQuery.data?.total ?? 0;
  const detail = detailQuery.data;

  return (
    <div className="admin-page">
      <h1 className="admin-page__title">المدفوعات</h1>
      <p className="admin-page__desc">فواتير الدفع بالعملات الرقمية. التأكيد اليدوي متاح لمدير النظام فقط.</p>

      <div className="admin-filters">
        <select
          className="input"
          value={status}
          onChange={(e) => { setStatus(e.target.value); setOffset(0); }}
          aria-label="تصفية بالحالة"
        >
          <option value="">كل الحالات</option>
          <option value="pending">قيد الانتظار</option>
          <option value="paid">مدفوعة</option>
          <option value="expired">منتهية</option>
          <option value="failed">فاشلة</option>
        </select>
      </div>

      <AdminTable
        columns={['المبلغ', 'العملة', 'الحالة', 'المزود', 'التاريخ', 'إجراءات']}
        loading={listQuery.isLoading}
        error={listQuery.isError ? 'تعذر تحميل الفواتير.' : null}
        onRetry={() => listQuery.refetch()}
      >
        {listQuery.data?.items.length === 0 && <AdminEmptyRow colSpan={6} message="لا توجد فواتير." />}
        {listQuery.data?.items.map((inv) => (
          <tr key={inv.id}>
            <td>${Number(inv.amount_usd).toFixed(2)}</td>
            <td>{inv.currency}</td>
            <td><span className={statusBadge(inv.status)}>{STATUS_LABELS[inv.status] ?? inv.status}</span></td>
            <td>{inv.provider}</td>
            <td className="admin-table__dim">
              {inv.created_at ? new Date(inv.created_at).toLocaleString('ar') : '—'}
            </td>
            <td className="admin-table__actions">
              <button className="btn btn--secondary btn--sm" onClick={() => setSelected(inv)}>
                تفاصيل
              </button>
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
          {offset + 1}–{Math.min(offset + limit, total)} من {total}
        </span>
        <button
          className="btn btn--secondary btn--sm"
          disabled={offset + limit >= total}
          onClick={() => setOffset(offset + limit)}
        >
          التالي
        </button>
      </div>

      {selected && (
        <div className="admin-detail" role="dialog" aria-label="تفاصيل الفاتورة">
          <div className="admin-detail__header">
            <h2 className="admin-detail__title">فاتورة {selected.id.slice(0, 8)}</h2>
            <button className="btn btn--ghost btn--sm" onClick={() => setSelected(null)} aria-label="إغلاق">
              ✕
            </button>
          </div>
          <div className="admin-detail__meta">
            <span>المبلغ: ${Number(selected.amount_usd).toFixed(2)}</span>
            <span>العملة: {selected.currency}</span>
            <span>الحالة: {STATUS_LABELS[selected.status] ?? selected.status}</span>
            <span>المزود: {selected.provider}</span>
            {selected.crypto_address && (
              <span className="admin-table__mono" style={{ wordBreak: 'break-all' }}>
                العنوان: {selected.crypto_address}
              </span>
            )}
          </div>

          {selected.status === 'pending' && (
            <section className="admin-detail__section">
              <h3>تأكيد يدوي (superadmin فقط)</h3>
              {isSuperadmin ? (
                <div className="admin-form-row">
                  <input
                    className="input"
                    placeholder="سبب التأكيد اليدوي (5 أحرف على الأقل)"
                    value={confirmReason}
                    onChange={(e) => setConfirmReason(e.target.value)}
                    aria-label="سبب التأكيد"
                  />
                  <button
                    className="btn btn--primary btn--sm"
                    disabled={confirmReason.length < 5 || confirmMut.isPending}
                    onClick={() => confirmMut.mutate({ id: selected.id, reason: confirmReason })}
                  >
                    تأكيد وشحن الرصيد
                  </button>
                </div>
              ) : (
                <p className="text-sm text-secondary">التأكيد اليدوي متاح لمدير النظام (superadmin) فقط.</p>
              )}
              {confirmMut.isError && <p className="admin-error__text">فشل التأكيد اليدوي.</p>}
            </section>
          )}

          <section className="admin-detail__section">
            <h3>سجل Webhooks</h3>
            {detailQuery.isLoading ? (
              <div className="flex items-center justify-center p-4"><div className="spinner" /></div>
            ) : (
              <div className="admin-table-wrap">
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>النوع</th>
                      <th>معالج</th>
                      <th>خطأ</th>
                      <th>التاريخ</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail?.webhook_events.length === 0 && (
                      <AdminEmptyRow colSpan={4} message="لا توجد أحداث webhook." />
                    )}
                    {detail?.webhook_events.map((ev) => (
                      <tr key={ev.id}>
                        <td>{ev.event_type}</td>
                        <td>
                          <span className={`badge ${ev.processed ? 'badge--success' : 'badge--warning'}`}>
                            {ev.processed ? 'نعم' : 'لا'}
                          </span>
                        </td>
                        <td className="admin-table__dim">{ev.error ?? '—'}</td>
                        <td className="admin-table__dim">
                          {ev.created_at ? new Date(ev.created_at).toLocaleString('ar') : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}

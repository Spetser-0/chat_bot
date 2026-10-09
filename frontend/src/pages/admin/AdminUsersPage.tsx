/**
 * pages/admin/AdminUsersPage.tsx
 * ──────────────────────────────
 * User management (Phase 9, Lesson 9.8): search, filter, ban/unban,
 * adjust credits, view credit ledger.
 */
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { adminApi, type AdminUser } from '../../api/admin';
import { AdminTable, AdminEmptyRow } from '../../components/admin/AdminTable';

export function AdminUsersPage() {
  const queryClient = useQueryClient();
  const [q, setQ] = useState('');
  const [search, setSearch] = useState('');
  const [role, setRole] = useState('');
  const [status, setStatus] = useState('');
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<AdminUser | null>(null);
  const [adjustAmount, setAdjustAmount] = useState('');
  const [adjustReason, setAdjustReason] = useState('');

  const limit = 50;

  const usersQuery = useQuery({
    queryKey: ['admin', 'users', search, role, status, offset],
    queryFn: () =>
      adminApi.listUsers({
        q: search || undefined,
        role: role || undefined,
        status: status || undefined,
        limit,
        offset,
      }),
  });

  const txQuery = useQuery({
    queryKey: ['admin', 'users', selected?.id, 'tx'],
    queryFn: () => adminApi.userTransactions(selected!.id),
    enabled: !!selected,
  });

  const invalidateUsers = () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
  };

  const banMut = useMutation({
    mutationFn: (id: string) => adminApi.banUser(id),
    onSuccess: invalidateUsers,
  });
  const unbanMut = useMutation({
    mutationFn: (id: string) => adminApi.unbanUser(id),
    onSuccess: invalidateUsers,
  });
  const adjustMut = useMutation({
    mutationFn: ({ id, amount, reason }: { id: string; amount: string; reason: string }) =>
      adminApi.adjustCredits(id, { amount, reason }),
    onSuccess: () => {
      invalidateUsers();
      setAdjustAmount('');
      setAdjustReason('');
    },
  });

  const handleSubmitSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setOffset(0);
    setSearch(q);
  };

  const total = usersQuery.data?.total ?? 0;

  return (
    <div className="admin-page">
      <h1 className="admin-page__title">المستخدمون</h1>

      <form className="admin-filters" onSubmit={handleSubmitSearch}>
        <input
          className="input"
          placeholder="بحث بالبريد أو الاسم"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          aria-label="بحث"
        />
        <select className="input" value={role} onChange={(e) => { setRole(e.target.value); setOffset(0); }} aria-label="الدور">
          <option value="">كل الأدوار</option>
          <option value="student">طالب</option>
          <option value="admin">مدير</option>
          <option value="developer">مطور</option>
          <option value="superadmin">مدير أعلى</option>
        </select>
        <select className="input" value={status} onChange={(e) => { setStatus(e.target.value); setOffset(0); }} aria-label="الحالة">
          <option value="">كل الحالات</option>
          <option value="active">نشط</option>
          <option value="banned">محظور</option>
        </select>
        <button type="submit" className="btn btn--primary">بحث</button>
      </form>

      <AdminTable
        columns={['البريد', 'الدور', 'الحالة', 'الرصيد', 'أُنشئ', 'إجراءات']}
        loading={usersQuery.isLoading}
        error={usersQuery.isError ? 'تعذر تحميل المستخدمين.' : null}
        onRetry={() => usersQuery.refetch()}
      >
        {usersQuery.data?.items.length === 0 && <AdminEmptyRow colSpan={6} message="لا يوجد مستخدمون." />}
        {usersQuery.data?.items.map((u) => (
          <tr key={u.id}>
            <td className="admin-table__mono">{u.email}</td>
            <td><span className="badge badge--muted">{u.role}</span></td>
            <td>
              <span className={`badge ${u.status === 'active' ? 'badge--success' : 'badge--error'}`}>
                {u.status === 'active' ? 'نشط' : 'محظور'}
              </span>
            </td>
            <td>{Number(u.credit_balance).toFixed(0)}</td>
            <td className="admin-table__dim">{u.created_at ? new Date(u.created_at).toLocaleDateString('ar') : '—'}</td>
            <td className="admin-table__actions">
              <button className="btn btn--secondary btn--sm" onClick={() => setSelected(u)}>
                تفاصيل
              </button>
              {u.status === 'active' ? (
                <button className="btn btn--danger btn--sm" onClick={() => banMut.mutate(u.id)} disabled={banMut.isPending}>
                  حظر
                </button>
              ) : (
                <button className="btn btn--secondary btn--sm" onClick={() => unbanMut.mutate(u.id)} disabled={unbanMut.isPending}>
                  إلغاء الحظر
                </button>
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
        <div className="admin-detail" role="dialog" aria-label={`تفاصيل ${selected.email}`}>
          <div className="admin-detail__header">
            <h2 className="admin-detail__title">{selected.email}</h2>
            <button className="btn btn--ghost btn--sm" onClick={() => setSelected(null)} aria-label="إغلاق">
              ✕
            </button>
          </div>
          <div className="admin-detail__meta">
            <span>الدور: {selected.role}</span>
            <span>الرصيد: {Number(selected.credit_balance).toFixed(0)}</span>
            <span>مميز: {selected.is_premium ? 'نعم' : 'لا'}</span>
            <span>محاولات دخول فاشلة: {selected.failed_login_attempts}</span>
          </div>

          <section className="admin-detail__section">
            <h3>تعديل الرصيد</h3>
            <div className="admin-form-row">
              <input
                className="input"
                type="number"
                placeholder="المبلغ (+ ائتمان / − خصم)"
                value={adjustAmount}
                onChange={(e) => setAdjustAmount(e.target.value)}
                aria-label="المبلغ"
              />
              <input
                className="input"
                placeholder="السبب (3 أحرف على الأقل)"
                value={adjustReason}
                onChange={(e) => setAdjustReason(e.target.value)}
                aria-label="السبب"
              />
              <button
                className="btn btn--primary btn--sm"
                disabled={!adjustAmount || adjustReason.length < 3 || adjustMut.isPending}
                onClick={() =>
                  adjustMut.mutate({ id: selected.id, amount: adjustAmount, reason: adjustReason })
                }
              >
                تطبيق
              </button>
            </div>
            {adjustMut.isError && <p className="admin-error__text">فشل تعديل الرصيد.</p>}
          </section>

          <section className="admin-detail__section">
            <h3>سجل الرصيد</h3>
            {txQuery.isLoading ? (
              <div className="flex items-center justify-center p-4"><div className="spinner" /></div>
            ) : (
              <div className="admin-table-wrap">
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>النوع</th>
                      <th>الوصف</th>
                      <th>المبلغ</th>
                      <th>التاريخ</th>
                    </tr>
                  </thead>
                  <tbody>
                    {txQuery.data?.items.length === 0 && <AdminEmptyRow colSpan={4} message="لا توجد حركات." />}
                    {txQuery.data?.items.map((row) => (
                      <tr key={row.id}>
                        <td><span className="badge badge--muted">{row.entry_type}</span></td>
                        <td className="admin-table__dim">{row.description ?? '—'}</td>
                        <td>{Number(row.credits_charged).toFixed(0)}</td>
                        <td className="admin-table__dim">
                          {row.created_at ? new Date(row.created_at).toLocaleString('ar') : '—'}
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

/**
 * pages/admin/AdminAuditPage.tsx
 * ─────────────────────────────
 * Audit trail (Phase 9, Lesson 9.8): filter by action / resource type,
 * date range, paginated read-only view.
 */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { adminApi } from '../../api/admin';
import { AdminTable, AdminEmptyRow } from '../../components/admin/AdminTable';

export function AdminAuditPage() {
  const [action, setAction] = useState('');
  const [resourceType, setResourceType] = useState('');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [offset, setOffset] = useState(0);
  const limit = 50;

  const listQuery = useQuery({
    queryKey: ['admin', 'audit', action, resourceType, fromDate, toDate, offset],
    queryFn: () =>
      adminApi.listAuditLogs({
        action: action || undefined,
        resource_type: resourceType || undefined,
        from_date: fromDate ? new Date(fromDate).toISOString() : undefined,
        to_date: toDate ? new Date(toDate).toISOString() : undefined,
        limit,
        offset,
      }),
  });

  const total = listQuery.data?.total ?? 0;

  return (
    <div className="admin-page">
      <h1 className="admin-page__title">سجل التدقيق</h1>
      <p className="admin-page__desc">كل إجراءات الإدارة مسجلة هنا — للقراءة فقط.</p>

      <div className="admin-filters">
        <input
          className="input"
          placeholder="الإجراء (مثال: user.banned)"
          value={action}
          onChange={(e) => { setAction(e.target.value); setOffset(0); }}
          aria-label="تصفية بالإجراء"
        />
        <input
          className="input"
          placeholder="نوع المورد (مثال: skill)"
          value={resourceType}
          onChange={(e) => { setResourceType(e.target.value); setOffset(0); }}
          aria-label="تصفية بنوع المورد"
        />
        <input
          className="input"
          type="date"
          value={fromDate}
          onChange={(e) => { setFromDate(e.target.value); setOffset(0); }}
          aria-label="من تاريخ"
        />
        <input
          className="input"
          type="date"
          value={toDate}
          onChange={(e) => { setToDate(e.target.value); setOffset(0); }}
          aria-label="إلى تاريخ"
        />
      </div>

      <AdminTable
        columns={['الإجراء', 'المورد', 'المعرّف', 'البيانات', 'التاريخ']}
        loading={listQuery.isLoading}
        error={listQuery.isError ? 'تعذر تحميل السجل.' : null}
        onRetry={() => listQuery.refetch()}
      >
        {listQuery.data?.items.length === 0 && <AdminEmptyRow colSpan={5} message="لا توجد سجلات." />}
        {listQuery.data?.items.map((log) => (
          <tr key={log.id}>
            <td><span className="badge badge--teal">{log.action}</span></td>
            <td>{log.resource_type ?? '—'}</td>
            <td className="admin-table__mono admin-table__dim">{log.resource_id?.slice(0, 12) ?? '—'}</td>
            <td className="admin-table__dim" style={{ maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {log.metadata ? JSON.stringify(log.metadata) : '—'}
            </td>
            <td className="admin-table__dim">
              {log.created_at ? new Date(log.created_at).toLocaleString('ar') : '—'}
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
    </div>
  );
}

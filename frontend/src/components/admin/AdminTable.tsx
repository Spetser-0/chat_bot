/**
 * components/admin/AdminTable.tsx
 * ───────────────────────────────
 * Shared table shell for admin pages (Phase 9, Lesson 9.8).
 * RTL-aware via logical properties; empty/loading states included.
 */
import { type ReactNode } from 'react';

interface AdminTableProps {
  columns: string[];
  loading?: boolean;
  error?: string | null;
  emptyMessage?: string;
  onRetry?: () => void;
  children: ReactNode;
}

export function AdminTable({
  columns,
  loading = false,
  error = null,
  onRetry,
  children,
}: AdminTableProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="spinner spinner--lg" />
      </div>
    );
  }
  if (error) {
    return (
      <div className="admin-error" role="alert">
        <span>{error}</span>
        {onRetry && (
          <button className="btn btn--secondary btn--sm" onClick={onRetry}>
            إعادة المحاولة
          </button>
        )}
      </div>
    );
  }
  return (
    <div className="admin-table-wrap">
      <table className="admin-table">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c} scope="col">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

interface AdminEmptyRowProps {
  colSpan: number;
  message?: string;
}

export function AdminEmptyRow({ colSpan, message = 'لا توجد بيانات.' }: AdminEmptyRowProps) {
  return (
    <tr>
      <td colSpan={colSpan} className="admin-table__empty">
        {message}
      </td>
    </tr>
  );
}

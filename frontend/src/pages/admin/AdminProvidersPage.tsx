/**
 * pages/admin/AdminProvidersPage.tsx
 * ──────────────────────────────────
 * AI provider management (Phase 9, Lesson 9.8): list, toggle, test,
 * create. API keys shown only as server-masked previews.
 */
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { adminApi } from '../../api/admin';
import { AdminTable, AdminEmptyRow } from '../../components/admin/AdminTable';

export function AdminProvidersPage() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({
    name: '',
    slug: '',
    model_name: '',
    api_key: '',
    base_url: '',
  });
  const [testResults, setTestResults] = useState<Record<string, { healthy: boolean; error: string | null }>>({});

  const listQuery = useQuery({
    queryKey: ['admin', 'providers'],
    queryFn: () => adminApi.listProviders(),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['admin', 'providers'] });

  const toggleMut = useMutation({
    mutationFn: (slug: string) => adminApi.toggleProvider(slug),
    onSuccess: invalidate,
  });

  const testMut = useMutation({
    mutationFn: (slug: string) => adminApi.testProvider(slug),
    onSuccess: (data, slug) => {
      setTestResults((prev) => ({ ...prev, [slug]: data }));
    },
  });

  const createMut = useMutation({
    mutationFn: () =>
      adminApi.createProvider({
        name: createForm.name,
        slug: createForm.slug,
        model_name: createForm.model_name,
        api_key: createForm.api_key,
        base_url: createForm.base_url || null,
      }),
    onSuccess: () => {
      invalidate();
      setShowCreate(false);
      setCreateForm({ name: '', slug: '', model_name: '', api_key: '', base_url: '' });
    },
  });

  return (
    <div className="admin-page">
      <div className="admin-page__header">
        <div>
          <h1 className="admin-page__title">المزودون</h1>
          <p className="admin-page__desc">
            مزودو الذكاء الاصطناعي. مفاتيح API تُعرض مموّهة فقط ولا تُخزَّن كنص صريح.
          </p>
        </div>
        <button className="btn btn--primary" onClick={() => setShowCreate((v) => !v)}>
          {showCreate ? 'إلغاء' : '+ مزود جديد'}
        </button>
      </div>

      {showCreate && (
        <form
          className="admin-form"
          onSubmit={(e) => {
            e.preventDefault();
            createMut.mutate();
          }}
        >
          <div className="admin-form-row">
            <input className="input" placeholder="الاسم" required value={createForm.name} onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })} aria-label="الاسم" />
            <input className="input" placeholder="slug (a-z0-9-)" required pattern="[a-z0-9-]+" value={createForm.slug} onChange={(e) => setCreateForm({ ...createForm, slug: e.target.value })} aria-label="slug" />
          </div>
          <div className="admin-form-row">
            <input className="input" placeholder="اسم النموذج" required value={createForm.model_name} onChange={(e) => setCreateForm({ ...createForm, model_name: e.target.value })} aria-label="اسم النموذج" />
            <input className="input" type="password" placeholder="مفتاح API" required value={createForm.api_key} onChange={(e) => setCreateForm({ ...createForm, api_key: e.target.value })} aria-label="مفتاح API" autoComplete="off" />
          </div>
          <div className="admin-form-row">
            <input className="input" placeholder="base_url (اختياري)" value={createForm.base_url} onChange={(e) => setCreateForm({ ...createForm, base_url: e.target.value })} aria-label="base_url" />
            <button type="submit" className="btn btn--primary" disabled={createMut.isPending}>
              إنشاء
            </button>
          </div>
          {createMut.isError && <p className="admin-error__text">فشل إنشاء المزود. تحقق من الحقول.</p>}
        </form>
      )}

      <AdminTable
        columns={['الاسم', 'slug', 'النموذج', 'المفتاح', 'الحالة', 'إجراءات']}
        loading={listQuery.isLoading}
        error={listQuery.isError ? 'تعذر تحميل المزودين.' : null}
        onRetry={() => listQuery.refetch()}
      >
        {listQuery.data?.length === 0 && <AdminEmptyRow colSpan={6} message="لا يوجد مزودون." />}
        {listQuery.data?.map((p) => {
          const test = testResults[p.slug];
          return (
            <tr key={p.slug}>
              <td>
                {p.name}
                {p.is_primary && <span className="badge badge--teal" style={{ marginInlineStart: 6 }}>أساسي</span>}
              </td>
              <td className="admin-table__mono">{p.slug}</td>
              <td>{p.model_name}</td>
              <td className="admin-table__mono admin-table__dim">{p.api_key_masked}</td>
              <td>
                <span className={`badge ${p.is_active ? 'badge--success' : 'badge--error'}`}>
                  {p.is_active ? 'نشط' : 'معطّل'}
                </span>
                {test && (
                  <span className={`badge ${test.healthy ? 'badge--success' : 'badge--error'}`} style={{ marginInlineStart: 4 }}>
                    {test.healthy ? 'سليم' : test.error}
                  </span>
                )}
              </td>
              <td className="admin-table__actions">
                <button className="btn btn--secondary btn--sm" onClick={() => toggleMut.mutate(p.slug)} disabled={toggleMut.isPending}>
                  {p.is_active ? 'تعطيل' : 'تفعيل'}
                </button>
                <button className="btn btn--secondary btn--sm" onClick={() => testMut.mutate(p.slug)} disabled={testMut.isPending}>
                  اختبار
                </button>
              </td>
            </tr>
          );
        })}
      </AdminTable>
    </div>
  );
}

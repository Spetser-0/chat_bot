/**
 * components/admin/AdminLayout.tsx
 * ────────────────────────────────
 * Admin area shell (Phase 9, Lesson 9.8): sidebar tabs + content.
 * Nested under RequireDeveloper — no auth check here.
 */
import { type ReactNode } from 'react';
import { NavLink, Link } from 'react-router-dom';
import { SkipLink } from '../ui/SkipLink';

interface AdminLayoutProps {
  children: ReactNode;
}

const ADMIN_TABS = [
  { to: '/admin', end: true, icon: '📊', label: 'نظرة عامة' },
  { to: '/admin/providers', icon: '🔌', label: 'المزودون' },
  { to: '/admin/skills', icon: '🧠', label: 'المهارات' },
  { to: '/admin/users', icon: '👥', label: 'المستخدمون' },
  { to: '/admin/payments', icon: '💳', label: 'المدفوعات' },
  { to: '/admin/referrals', icon: '🎁', label: 'الدعوات' },
  { to: '/admin/audit', icon: '📜', label: 'سجل التدقيق' },
];

export function AdminLayout({ children }: AdminLayoutProps) {
  return (
    <div className="admin-layout" dir="rtl">
      <SkipLink />
      <aside className="admin-layout__sidebar" aria-label="أقسام لوحة التحكم">
        <div className="admin-layout__brand">
          <Link to="/" className="brand-mark">
            <div className="brand-mark__icon" aria-hidden="true">س</div>
            <div>
              <div className="brand-mark__name">لوحة التحكم</div>
              <div className="brand-mark__subtitle">Spetser AI</div>
            </div>
          </Link>
        </div>
        <nav className="admin-layout__nav">
          {ADMIN_TABS.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              end={tab.end}
              className={({ isActive }) =>
                `sidebar__nav-item${isActive ? ' sidebar__nav-item--active' : ''}`
              }
            >
              <span aria-hidden="true">{tab.icon}</span>
              <span>{tab.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="admin-layout__footer">
          <Link to="/" className="btn btn--secondary btn--sm btn--full">
            العودة للتطبيق
          </Link>
        </div>
      </aside>
      <main className="admin-layout__content" id="main-content" tabIndex={-1}>
        {children}
      </main>
    </div>
  );
}

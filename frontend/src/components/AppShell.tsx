/**
 * components/AppShell.tsx
 * ─────────────────────────
 * Main layout shell with right-side sidebar (RTL-first) and top bar.
 */
import { type ReactNode } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/useAuth';

interface AppShellProps {
  children: ReactNode;
}

const NAV_ITEMS = [
  { to: '/', icon: '🏠', label: 'الرئيسية', end: true },
  { to: '/presentations/new', icon: '🖥️', label: 'عرض تقديمي' },
  { to: '/chat', icon: '💬', label: 'محادثة', disabled: false },
  { to: '/research', icon: '📚', label: 'بحث أكاديمي', planned: true },
  { to: '/questions', icon: '🔢', label: 'حل المسائل', planned: true },
  { to: '/history', icon: '🕐', label: 'السجل' },
];

export function AppShell({ children }: AppShellProps) {
  const { student, logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="app-shell" dir="rtl">
      {/* Right sidebar */}
      <aside className="app-shell__sidebar" aria-label="القائمة الرئيسية">
        {/* Brand */}
        <div className="sidebar__brand">
          <Link to="/" className="brand-mark" aria-label="Spetser AI - الصفحة الرئيسية">
            <div className="brand-mark__icon" aria-hidden="true">س</div>
            <div>
              <div className="brand-mark__name">Spetser AI</div>
              <div className="brand-mark__subtitle">مساعدك الأكاديمي</div>
            </div>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="sidebar__nav" aria-label="التنقل">
          {NAV_ITEMS.map((item) => (
            item.planned ? (
              <div
                key={item.to}
                className="sidebar__nav-item"
                style={{ opacity: 0.45, cursor: 'not-allowed' }}
                aria-disabled="true"
                title="قريباً"
              >
                <span aria-hidden="true">{item.icon}</span>
                <span>{item.label}</span>
                <span className="badge badge--muted" style={{ marginInlineStart: 'auto', fontSize: '10px' }}>
                  قريباً
                </span>
              </div>
            ) : (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `sidebar__nav-item${isActive ? ' sidebar__nav-item--active' : ''}`
                }
              >
                <span aria-hidden="true">{item.icon}</span>
                <span>{item.label}</span>
              </NavLink>
            )
          ))}
        </nav>

        {/* Footer */}
        <div className="sidebar__footer">
          {isAuthenticated && student ? (
            <div className="flex flex-col gap-2">
              {/* Credit balance */}
              <div className="credit-badge" aria-label={`رصيدك: ${student.credit_balance} نقطة`}>
                <span aria-hidden="true">⚡</span>
                <span>{student.credit_balance.toFixed(0)} نقطة</span>
              </div>
              {/* Student name */}
              <div className="flex items-center justify-between">
                <span className="text-sm text-secondary" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {student.display_name || student.email}
                </span>
                <button
                  className="btn btn--ghost btn--sm"
                  onClick={handleLogout}
                  aria-label="تسجيل الخروج"
                >
                  خروج
                </button>
              </div>
              {/* Developer badge */}
              {(student.role === 'developer' || student.role === 'admin') && (
                <Link to="/developer" className="btn btn--secondary btn--sm btn--full">
                  لوحة المطور
                </Link>
              )}
            </div>
          ) : (
            <Link to="/login" className="btn btn--primary btn--full">
              تسجيل الدخول
            </Link>
          )}
        </div>
      </aside>

      {/* Main content area */}
      <div className="app-shell__main">
        {/* Top bar */}
        <header className="app-shell__topbar" role="banner">
          <h1 className="sr-only">Spetser AI</h1>
          {/* Breadcrumb / page context will be injected by routes */}
          <div style={{ flex: 1 }} />
          {isAuthenticated && student && (
            <div className="credit-badge">
              <span aria-hidden="true">⚡</span>
              <span>{student.credit_balance.toFixed(0)}</span>
            </div>
          )}
        </header>

        {/* Page content */}
        <main className="app-shell__content" id="main-content">
          {children}
        </main>
      </div>
    </div>
  );
}

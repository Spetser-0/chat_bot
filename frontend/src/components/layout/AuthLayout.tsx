/**
 * components/layout/AuthLayout.tsx
 * ────────────────────────────────
 * Shared shell for auth pages (login/register/referral landing):
 * brand header + theme toggle + centered card area (Phase 9, Lesson 9.3).
 */
import { type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { useTheme } from '../../contexts/useTheme';

interface AuthLayoutProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
}

export function AuthLayout({ title, subtitle, children }: AuthLayoutProps) {
  const { theme, toggleTheme } = useTheme();

  return (
    <div
      style={{ maxWidth: 420, margin: '0 auto', paddingTop: 'var(--space-8)', paddingInline: 'var(--space-4)' }}
    >
      {/* Theme toggle */}
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <button
          className="icon-btn"
          onClick={toggleTheme}
          aria-label={theme === 'light' ? 'الوضع الليلي' : 'الوضع النهاري'}
          title={theme === 'light' ? 'الوضع الليلي' : 'الوضع النهاري'}
        >
          {theme === 'light' ? '🌙' : '☀️'}
        </button>
      </div>

      {/* Brand */}
      <div style={{ textAlign: 'center', marginBottom: 'var(--space-6)' }}>
        <Link to="/" aria-label="Spetser AI">
          <div
            style={{
              width: 48, height: 48,
              background: 'var(--color-accent)',
              borderRadius: 'var(--radius-lg)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: 'white', fontSize: 'var(--text-xl)', fontWeight: 'var(--font-semibold)',
              margin: '0 auto var(--space-4)',
            }}
            aria-hidden="true"
          >
            س
          </div>
        </Link>
        <h1
          style={{
            fontSize: 'var(--text-xl)', fontWeight: 'var(--font-semibold)',
            marginBottom: 'var(--space-1)',
          }}
        >
          {title}
        </h1>
        {subtitle && <p className="text-muted text-sm">{subtitle}</p>}
      </div>

      {children}
    </div>
  );
}

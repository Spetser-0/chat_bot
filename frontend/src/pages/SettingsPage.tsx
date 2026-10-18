/**
 * pages/SettingsPage.tsx
 * ──────────────────────
 * Student settings: profile, appearance, credits and account actions.
 */
import { Link } from 'react-router-dom';
import { useNavigate } from 'react-router-dom';
import { LogOut, Moon, Sun, Zap } from 'lucide-react';
import { useAuth } from '../contexts/useAuth';
import { useTheme } from '../contexts/useTheme';
import { useCredits } from '../hooks/useCredits';

export function SettingsPage() {
  const { student, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { balance, isLow } = useCredits();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="fade-in settings">
      <header className="settings__header">
        <h1 className="settings__title">الإعدادات</h1>
        <p className="settings__desc">إدارة ملفك الشخصي وتفضيلاتك</p>
      </header>

      {/* ── Profile ─────────────────────────────────────────────────── */}
      <section className="card settings__section" aria-labelledby="settings-profile">
        <h2 id="settings-profile" className="settings__section-title">الملف الشخصي</h2>
        <div className="field">
          <span className="field__label">الاسم</span>
          <div className="settings__value">{student?.display_name || '—'}</div>
        </div>
        <div className="field">
          <span className="field__label">البريد الإلكتروني</span>
          <div className="settings__value">{student?.email}</div>
        </div>
      </section>

      {/* ── Appearance ──────────────────────────────────────────────── */}
      <section className="card settings__section" aria-labelledby="settings-appearance">
        <h2 id="settings-appearance" className="settings__section-title">المظهر</h2>
        <button
          type="button"
          className="btn btn--secondary btn--full"
          onClick={toggleTheme}
          aria-label={theme === 'light' ? 'التبديل إلى الوضع الليلي' : 'التبديل إلى الوضع النهاري'}
        >
          {theme === 'light' ? (
            <Moon size={16} aria-hidden="true" />
          ) : (
            <Sun size={16} aria-hidden="true" />
          )}
          <span>{theme === 'light' ? 'الوضع الليلي' : 'الوضع النهاري'}</span>
        </button>
      </section>

      {/* ── Credits ─────────────────────────────────────────────────── */}
      <section className="card settings__section" aria-labelledby="settings-credits">
        <h2 id="settings-credits" className="settings__section-title">الرصيد</h2>
        <div className="settings__credits">
          <Zap size={18} aria-hidden="true" className="text-accent" />
          <span className="settings__credits-value">{balance.toFixed(0)} نقطة</span>
          {isLow && <span className="badge badge--error">رصيد منخفض</span>}
        </div>
        <p className="settings__note">سيتم تفعيل الرصيد اليومي المجاني في التحديث القادم.</p>
      </section>

      {/* ── Account ─────────────────────────────────────────────────── */}
      <section className="card settings__section" aria-labelledby="settings-account">
        <h2 id="settings-account" className="settings__section-title">الحساب</h2>
        <div className="flex flex-col gap-2">
          <button
            type="button"
            className="btn btn--danger btn--full"
            onClick={handleLogout}
          >
            <LogOut size={16} aria-hidden="true" />
            <span>تسجيل الخروج</span>
          </button>
          <Link to="/" className="btn btn--ghost btn--full">العودة إلى الرئيسية</Link>
        </div>
      </section>
    </div>
  );
}

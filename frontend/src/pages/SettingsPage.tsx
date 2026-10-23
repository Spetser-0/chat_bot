/**
 * pages/SettingsPage.tsx
 * ──────────────────────
 * Student settings: profile, appearance, language, credits and account actions.
 */
import { Link, useNavigate } from 'react-router-dom';
import { LogOut, Moon, Sun, Zap } from 'lucide-react';
import { useAuth } from '../contexts/useAuth';
import { useTheme } from '../contexts/useTheme';
import { useCredits } from '../hooks/useCredits';
import { useLanguage } from '../contexts/useLanguage';

export function SettingsPage() {
  const { student, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { balance, isLow } = useCredits();
  const { language, setLanguage, t } = useLanguage();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="fade-in settings">
      <header className="settings__header">
        <h1 className="settings__title">{t('settings.title')}</h1>
        <p className="settings__desc">{t('settings.desc')}</p>
      </header>

      {/* ── Profile ─────────────────────────────────────────────────── */}
      <section className="card settings__section" aria-labelledby="settings-profile">
        <h2 id="settings-profile" className="settings__section-title">
          {t('settings.profile')}
        </h2>
        <div className="field">
          <span className="field__label">{t('settings.name')}</span>
          <div className="settings__value">{student?.display_name || '—'}</div>
        </div>
        <div className="field">
          <span className="field__label">{t('settings.email')}</span>
          <div className="settings__value">{student?.email}</div>
        </div>
      </section>

      {/* ── Appearance ──────────────────────────────────────────────── */}
      <section className="card settings__section" aria-labelledby="settings-appearance">
        <h2 id="settings-appearance" className="settings__section-title">
          {t('settings.appearance')}
        </h2>
        <button
          type="button"
          className="btn btn--secondary btn--full"
          onClick={toggleTheme}
          aria-label={theme === 'light' ? t('settings.darkMode') : t('settings.lightMode')}
        >
          {theme === 'light' ? (
            <Moon size={16} aria-hidden="true" />
          ) : (
            <Sun size={16} aria-hidden="true" />
          )}
          <span>{theme === 'light' ? t('settings.darkMode') : t('settings.lightMode')}</span>
        </button>
      </section>

      {/* ── Language ────────────────────────────────────────────────── */}
      <section className="card settings__section" aria-labelledby="settings-language">
        <h2 id="settings-language" className="settings__section-title">
          {t('settings.language')}
        </h2>
        <select
          className="input input--full"
          value={language}
          onChange={(e) => setLanguage(e.target.value as 'ar' | 'en')}
          aria-label={t('settings.language')}
        >
          <option value="ar">{t('language.arabic')}</option>
          <option value="en">{t('language.english')}</option>
        </select>
      </section>

      {/* ── Credits ─────────────────────────────────────────────────── */}
      <section className="card settings__section" aria-labelledby="settings-credits">
        <h2 id="settings-credits" className="settings__section-title">
          {t('settings.credits')}
        </h2>
        <div className="settings__credits">
          <Zap size={18} aria-hidden="true" className="text-accent" />
          <span className="settings__credits-value">
            {balance.toFixed(0)} {t('settings.creditsUnit')}
          </span>
          {isLow && <span className="badge badge--error">{t('settings.lowCredits')}</span>}
        </div>
        <p className="settings__note">{t('settings.creditsNote')}</p>
      </section>

      {/* ── Account ─────────────────────────────────────────────────── */}
      <section className="card settings__section" aria-labelledby="settings-account">
        <h2 id="settings-account" className="settings__section-title">
          {t('settings.account')}
        </h2>
        <div className="flex flex-col gap-2">
          <button
            type="button"
            className="btn btn--danger btn--full"
            onClick={handleLogout}
          >
            <LogOut size={16} aria-hidden="true" />
            <span>{t('settings.logout')}</span>
          </button>
          <Link to="/" className="btn btn--ghost btn--full">
            {t('settings.backHome')}
          </Link>
        </div>
      </section>
    </div>
  );
}

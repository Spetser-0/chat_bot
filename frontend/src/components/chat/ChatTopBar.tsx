/**
 * components/chat/ChatTopBar.tsx
 * ──────────────────────────────
 * Chat top bar: skill selector, credits, theme toggle, user menu
 * (Phase 9, Lesson 9.1).
 */
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/useAuth';
import { useTheme } from '../../contexts/useTheme';
import { useCredits } from '../../hooks/useCredits';
import { useDismissable } from '../../hooks/useDismissable';
import { BuyCreditsModal } from '../billing/BuyCreditsModal';

interface ChatTopBarProps {
  title?: string;
  skills?: { slug: string; name: string; is_premium?: boolean }[];
  activeSkillSlug?: string;
  onSkillChange?: (slug: string) => void;
  onToggleSidebar?: () => void;
}

export function ChatTopBar({
  title,
  skills = [],
  activeSkillSlug,
  onSkillChange,
  onToggleSidebar,
}: ChatTopBarProps) {
  const { student, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { balance, isLow, isLoading: creditsLoading } = useCredits();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [buyOpen, setBuyOpen] = useState(false);
  const menuRef = useDismissable<HTMLDivElement>({
    open: menuOpen,
    onClose: () => setMenuOpen(false),
    outsideClick: true,
  });

  const activeSkill = skills.find((s) => s.slug === activeSkillSlug);
  const initial = (student?.display_name || student?.email || '?').charAt(0);

  const handleLogout = async () => {
    setMenuOpen(false);
    await logout();
    navigate('/login');
  };

  return (
    <header className="chat-layout__topbar" role="banner">
      {onToggleSidebar && (
        <button
          className="icon-btn"
          onClick={onToggleSidebar}
          aria-label="إظهار/إخفاء قائمة المحادثات"
        >
          ☰
        </button>
      )}

      <span className="chat-topbar__title">{title ?? 'المحادثة'}</span>

      <div style={{ flex: 1 }} />

      {/* Skill selector */}
      {skills.length > 0 && (
        <label className="skill-select" aria-label="اختيار المهارة">
          <span aria-hidden="true">🎓</span>
          <select
            className="skill-select__label"
            value={activeSkillSlug ?? ''}
            onChange={(e) => onSkillChange?.(e.target.value)}
            style={{
              border: 'none', background: 'transparent', color: 'inherit',
              font: 'inherit', cursor: 'pointer', outline: 'none',
            }}
          >
            <option value="">عام</option>
            <option value="auto">تلقائي 🤖</option>
            {skills.map((s) => {
              const locked = s.is_premium && student?.is_premium === false;
              return (
                <option key={s.slug} value={s.slug} disabled={locked}>
                  {s.name}{s.is_premium ? (locked ? ' 🔒' : ' ⭐') : ''}
                </option>
              );
            })}
          </select>
          {activeSkill && null}
        </label>
      )}

      {/* Credits: live balance + low-balance warning + buy button */}
      {student && (
        <div className="flex items-center gap-2">
          <button
            className={`credit-badge${isLow ? ' credit-badge--low' : ''}`}
            onClick={() => setBuyOpen(true)}
            aria-label={
              creditsLoading
                ? 'جاري تحميل الرصيد'
                : isLow
                  ? `رصيدك منخفض: ${balance.toFixed(0)} نقطة — اضغط للشحن`
                  : `رصيدك: ${balance.toFixed(0)} نقطة — اضغط للشحن`
            }
            title="اضغط لشراء رصيد"
          >
            <span aria-hidden="true">{isLow ? '⚠️' : '⚡'}</span>
            <span>{creditsLoading ? '…' : balance.toFixed(0)}</span>
            {isLow && <span className="credit-badge__cta">شحن</span>}
          </button>
        </div>
      )}

      {/* Theme toggle */}
      <button
        className="icon-btn"
        onClick={toggleTheme}
        aria-label={theme === 'light' ? 'الوضع الليلي' : 'الوضع النهاري'}
        title={theme === 'light' ? 'الوضع الليلي' : 'الوضع النهاري'}
      >
        {theme === 'light' ? '🌙' : '☀️'}
      </button>

      {/* User menu */}
      {student && (
        <div className="user-menu" ref={menuRef}>
          <button
            className="user-menu__trigger"
            onClick={() => setMenuOpen((o) => !o)}
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            aria-label="قائمة المستخدم"
          >
            <span className="user-menu__avatar" aria-hidden="true">{initial}</span>
            <span
              style={{
                maxWidth: 120, overflow: 'hidden',
                textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}
            >
              {student.display_name || student.email}
            </span>
          </button>
          {menuOpen && (
            <div className="user-menu__dropdown" role="menu">
              <Link
                to="/"
                className="user-menu__dropdown-item"
                role="menuitem"
                onClick={() => setMenuOpen(false)}
              >
                🏠 الرئيسية
              </Link>
              <Link
                to="/referrals"
                className="user-menu__dropdown-item"
                role="menuitem"
                onClick={() => setMenuOpen(false)}
              >
                🎁 ادعُ أصدقاءك
              </Link>
              {(student.role === 'developer' || student.role === 'admin' ||
                student.role === 'superadmin') && (
                <Link
                  to="/admin"
                  className="user-menu__dropdown-item"
                  role="menuitem"
                  onClick={() => setMenuOpen(false)}
                >
                  🛠️ لوحة التحكم
                </Link>
              )}
              <button
                className="user-menu__dropdown-item"
                role="menuitem"
                onClick={handleLogout}
              >
                🚪 تسجيل الخروج
              </button>
            </div>
          )}
        </div>
      )}

      <BuyCreditsModal open={buyOpen} onClose={() => setBuyOpen(false)} />
    </header>
  );
}

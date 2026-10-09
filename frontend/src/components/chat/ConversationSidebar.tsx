/**
 * components/chat/ConversationSidebar.tsx
 * ────────────────────────────────────────
 * Chat sidebar with conversation history (Phase 9, Lessons 9.1 + 9.4).
 * Includes rename / archive / delete actions per conversation.
 */
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/useAuth';
import { useCredits } from '../../hooks/useCredits';
import { BuyCreditsModal } from '../billing/BuyCreditsModal';

export interface SidebarActions {
  onRename?: (id: string, title: string) => void;
  onArchive?: (id: string) => void;
  onDelete?: (id: string) => void;
}

interface ConversationSidebarProps {
  conversations?: { id: string; title: string }[];
  activeId?: string | null;
  onNewChat?: () => void;
  actions?: SidebarActions;
  onSelect?: (id: string) => void;
}

export function ConversationSidebar({
  conversations = [],
  activeId,
  onNewChat,
  actions,
  onSelect,
}: ConversationSidebarProps) {
  const { student } = useAuth();
  const navigate = useNavigate();
  const { balance, isLow } = useCredits();
  const [menuFor, setMenuFor] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [buyOpen, setBuyOpen] = useState(false);

  // Escape closes the open ⋯ menu (Lesson 9.9).
  useEffect(() => {
    if (!menuFor) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMenuFor(null);
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [menuFor]);

  const startRename = (id: string, currentTitle: string) => {
    setMenuFor(null);
    setRenamingId(id);
    setRenameValue(currentTitle);
  };

  const commitRename = () => {
    if (renamingId && renameValue.trim()) {
      actions?.onRename?.(renamingId, renameValue.trim());
    }
    setRenamingId(null);
  };

  const handleSelect = (id: string) => {
    onSelect?.(id);
    navigate(`/chat/${id}`);
  };

  return (
    <aside className="chat-layout__sidebar" aria-label="المحادثات">
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

      {/* New chat */}
      <div style={{ padding: 'var(--space-3) var(--space-2) 0' }}>
        <button
          className="btn btn--primary btn--full"
          onClick={onNewChat}
          aria-label="بدء محادثة جديدة"
        >
          <span aria-hidden="true">＋</span>
          محادثة جديدة
        </button>
      </div>

      {/* Conversation history */}
      <div className="convo-list" role="list" aria-label="سجل المحادثات">
        <div className="convo-list__section-label">المحادثات</div>
        {conversations.length === 0 ? (
          <p
            className="text-sm text-muted"
            style={{ padding: 'var(--space-3)', textAlign: 'center' }}
          >
            لا توجد محادثات بعد.
          </p>
        ) : (
          conversations.map((c) => (
            <div
              key={c.id}
              role="listitem"
              className={`convo-list__item${c.id === activeId ? ' convo-list__item--active' : ''}`}
            >
              {renamingId === c.id ? (
                <input
                  className="input convo-rename-input"
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  onBlur={commitRename}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') commitRename();
                    if (e.key === 'Escape') setRenamingId(null);
                  }}
                  autoFocus
                  aria-label="عنوان المحادثة"
                />
              ) : (
                <>
                  <button
                    type="button"
                    className="convo-list__link"
                    onClick={() => handleSelect(c.id)}
                    title={c.title}
                    aria-current={c.id === activeId ? 'true' : undefined}
                    style={{
                      all: 'unset', cursor: 'pointer', overflow: 'hidden',
                      textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1,
                    }}
                  >
                    <span aria-hidden="true">💬 </span>
                    {c.title}
                  </button>
                  {actions && (
                    <div className="convo-item-actions">
                      <button
                        className="icon-btn icon-btn--sm"
                        onClick={() => setMenuFor(menuFor === c.id ? null : c.id)}
                        aria-label={`خيارات المحادثة ${c.title}`}
                        aria-haspopup="menu"
                        aria-expanded={menuFor === c.id}
                      >
                        ⋯
                      </button>
                      {menuFor === c.id && (
                        <div className="convo-actions-menu" role="menu">
                          <button
                            role="menuitem"
                            className="convo-actions-menu__item"
                            onClick={() => startRename(c.id, c.title)}
                          >
                            ✏️ إعادة تسمية
                          </button>
                          <button
                            role="menuitem"
                            className="convo-actions-menu__item"
                            onClick={() => { actions.onArchive?.(c.id); setMenuFor(null); }}
                          >
                            📦 أرشفة
                          </button>
                          <button
                            role="menuitem"
                            className="convo-actions-menu__item convo-actions-menu__item--danger"
                            onClick={() => { actions.onDelete?.(c.id); setMenuFor(null); }}
                          >
                            🗑️ حذف
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          ))
        )}
      </div>

      {/* Footer */}
      <div className="sidebar__footer">
        {student && (
          <div className="flex flex-col gap-2">
            <button
              className={`credit-badge credit-badge--full${isLow ? ' credit-badge--low' : ''}`}
              onClick={() => setBuyOpen(true)}
              aria-label={`رصيدك: ${balance.toFixed(0)} نقطة — اضغط للشحن`}
            >
              <span aria-hidden="true">{isLow ? '⚠️' : '⚡'}</span>
              <span>{balance.toFixed(0)} نقطة</span>
              {isLow && <span className="credit-badge__cta">شحن</span>}
            </button>
            <Link to="/" className="btn btn--ghost btn--sm btn--full">
              الرئيسية
            </Link>
          </div>
        )}
        <BuyCreditsModal open={buyOpen} onClose={() => setBuyOpen(false)} />
      </div>
    </aside>
  );
}

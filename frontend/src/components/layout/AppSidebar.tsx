/**
 * components/layout/AppSidebar.tsx
 * ──────────────────────────────────
 * The one sidebar for the whole student app, top → bottom:
 * brand → new chat → projects → chats → recently → footer.
 *
 * Projects and "recently" are client-side only (lib/projects.ts) because the
 * backend has no projects API yet.
 */
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ChevronDown,
  Folder,
  FolderOpen,
  FolderPlus,
  LayoutDashboard,
  LogOut,
  Moon,
  MoreHorizontal,
  Pencil,
  Plus,
  Settings,
  SquarePen,
  Sun,
  Trash2,
  X,
} from 'lucide-react';
import { useAuth } from '../../contexts/useAuth';
import { useTheme } from '../../contexts/useTheme';
import { useCredits } from '../../hooks/useCredits';
import { BuyCreditsModal } from '../billing/BuyCreditsModal';
import {
  addChatToProject,
  chatsOfProject,
  createProject,
  deleteProject,
  projectOfChat,
  removeChatFromProject,
  renameProject,
  useProjects,
  type Project,
} from '../../lib/projects';
import { creditsApi } from '../../api/credits';
import { useQueryClient } from '@tanstack/react-query';
import { Zap } from 'lucide-react';

export interface SidebarActions {
  onRename?: (id: string, title: string) => void;
  onArchive?: (id: string) => void;
  onDelete?: (id: string) => void;
}

interface AppSidebarProps {
  conversations?: { id: string; title: string }[];
  activeId?: string | null;
  onSelect?: (id: string) => void;
  onNewChat?: () => void;
  actions?: SidebarActions;
}

export function AppSidebar({
  conversations = [],
  activeId,
  onSelect,
  onNewChat,
  actions,
}: AppSidebarProps) {
  const navigate = useNavigate();
  const { student, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { balance, isLow } = useCredits();
  const { projects, recent } = useProjects();

  const [buyOpen, setBuyOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState('');
  const [openProject, setOpenProject] = useState<string | null>(null);
  const [projectMenuFor, setProjectMenuFor] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [chatMenuFor, setChatMenuFor] = useState<string | null>(null);
  const [addToFor, setAddToFor] = useState<string | null>(null);
  const [recentOpen, setRecentOpen] = useState(false);
  const [granting, setGranting] = useState(false);
  const queryClient = useQueryClient();

  // Escape closes any open menu.
  useEffect(() => {
    if (!chatMenuFor && !projectMenuFor) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setChatMenuFor(null);
        setProjectMenuFor(null);
        setAddToFor(null);
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [chatMenuFor, projectMenuFor]);

  const titleOf = (id: string) =>
    conversations.find((c) => c.id === id)?.title || 'محادثة بدون عنوان';

  const commitCreate = () => {
    const created = createProject(newName);
    setNewName('');
    setCreating(false);
    if (created) setOpenProject(created.id);
  };

  const commitRename = () => {
    if (renamingId && renameValue.trim()) renameProject(renamingId, renameValue.trim());
    setRenamingId(null);
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleGrant = async () => {
    if (granting) return;
    setGranting(true);
    try {
      await creditsApi.grantTestCredits();
      await queryClient.invalidateQueries({ queryKey: ['credits', 'balance'] });
    } catch {
      /* ignore */
    } finally {
      setGranting(false);
    }
  };

  const avatarInitial = (student?.display_name || student?.email || 'س').trim().charAt(0);

  return (
    <aside className="app-shell__sidebar app-sidebar" aria-label="القائمة الرئيسية">
      {/* ── Brand ─────────────────────────────────────────────────────── */}
      <div className="sidebar__brand">
        <Link to="/" className="brand-mark" aria-label="Spetser AI - الصفحة الرئيسية">
          <div className="brand-mark__icon" aria-hidden="true">س</div>
          <div>
            <div className="brand-mark__name">Spetser AI</div>
            <div className="brand-mark__subtitle">مساعدك الأكاديمي</div>
          </div>
        </Link>
      </div>

      {/* ── New chat ──────────────────────────────────────────────────── */}
      <div className="app-sidebar__new">
        <button
          type="button"
          className="btn btn--primary btn--full"
          onClick={onNewChat ?? (() => navigate('/chat'))}
          aria-label="محادثة جديدة"
        >
          <SquarePen size={16} aria-hidden="true" />
          <span>محادثة جديدة</span>
        </button>

        <button
          type="button"
          className="btn btn--ghost btn--sm btn--full credit-grant-btn"
          onClick={handleGrant}
          disabled={granting}
          aria-label="إضافة 300 نقطة تجريبية"
          title="إضافة 300 نقطة تجريبية"
        >
          <Zap size={14} aria-hidden="true" />
          <span>{granting ? 'جارٍ الإضافة...' : '+300 تجريبي'}</span>
        </button>
      </div>

      <nav className="sidebar__nav" aria-label="التنقل">
        {/* ── Projects ─────────────────────────────────────────────────── */}
        <div className="app-sidebar__section">
          <div className="app-sidebar__section-head">
            <span className="app-sidebar__section-title">المشاريع</span>
            <button
              type="button"
              className="icon-btn icon-btn--sm"
              onClick={() => setCreating(true)}
              aria-label="مشروع جديد"
              title="مشروع جديد"
            >
              <Plus size={15} aria-hidden="true" />
            </button>
          </div>

          {creating && (
            <div className="sidebar-inline-input">
              <input
                className="input"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') commitCreate();
                  if (e.key === 'Escape') {
                    setCreating(false);
                    setNewName('');
                  }
                }}
                placeholder="اسم المشروع"
                aria-label="اسم المشروع"
                autoFocus
              />
              <button
                type="button"
                className="icon-btn icon-btn--sm"
                onClick={commitCreate}
                aria-label="إنشاء المشروع"
              >
                <Plus size={15} aria-hidden="true" />
              </button>
            </div>
          )}

          {projects.length === 0 && !creating && (
            <p className="app-sidebar__empty">لا توجد مشاريع بعد — أنشئ واحداً لتنظيم محادثاتك.</p>
          )}

          {projects.map((project) => (
            <ProjectRow
              key={project.id}
              project={project}
              conversations={conversations}
              expanded={openProject === project.id}
              renaming={renamingId === project.id}
              renameValue={renameValue}
              menuOpen={projectMenuFor === project.id}
              onToggle={() => setOpenProject(openProject === project.id ? null : project.id)}
              onRenameChange={setRenameValue}
              onCommitRename={commitRename}
              onCancelRename={() => setRenamingId(null)}
              onOpenMenu={() => setProjectMenuFor(projectMenuFor === project.id ? null : project.id)}
              onCloseMenu={() => setProjectMenuFor(null)}
              onStartRename={() => {
                setRenamingId(project.id);
                setRenameValue(project.name);
                setProjectMenuFor(null);
              }}
              onDelete={() => {
                deleteProject(project.id);
                if (openProject === project.id) setOpenProject(null);
                setProjectMenuFor(null);
              }}
              onSelectChat={(id) => onSelect?.(id)}
            />
          ))}
        </div>

        {/* ── Chats ────────────────────────────────────────────────────── */}
        <div className="app-sidebar__section">
          <div className="app-sidebar__section-head">
            <span className="app-sidebar__section-title">المحادثات</span>
          </div>
          <div className="convo-list" role="list" aria-label="سجل المحادثات">
            {conversations.length === 0 && (
              <p className="app-sidebar__empty">لا توجد محادثات بعد.</p>
            )}
            {conversations.map((c) => {
              const assigned = projectOfChat(c.id);
              return (
                <div
                  key={c.id}
                  role="listitem"
                  className={`convo-list__item${c.id === activeId ? ' convo-list__item--active' : ''}`}
                >
                  <button
                    type="button"
                    className="convo-list__link"
                    onClick={() => onSelect?.(c.id)}
                    title={c.title}
                    aria-current={c.id === activeId ? 'true' : undefined}
                  >
                    <span aria-hidden="true"><FolderOpen size={14} /></span>
                    <span className="convo-list__title">{c.title}</span>
                    {assigned && (
                      <span className="badge badge--muted" style={{ fontSize: '10px' }}>
                        مشروع
                      </span>
                    )}
                  </button>

                  {actions && (
                    <div className="convo-item-actions">
                      <button
                        type="button"
                        className="icon-btn icon-btn--sm"
                        onClick={() => setChatMenuFor(chatMenuFor === c.id ? null : c.id)}
                        aria-label={`خيارات المحادثة ${c.title}`}
                        aria-haspopup="menu"
                        aria-expanded={chatMenuFor === c.id}
                      >
                        <MoreHorizontal size={15} aria-hidden="true" />
                      </button>

                      {chatMenuFor === c.id && (
                        <div className="convo-actions-menu" role="menu">
                          <button
                            type="button"
                            role="menuitem"
                            className="convo-actions-menu__item"
                            onClick={() => {
                              actions.onRename?.(c.id, c.title);
                              setChatMenuFor(null);
                            }}
                          >
                            <Pencil size={13} aria-hidden="true" /> إعادة تسمية
                          </button>
                          <button
                            type="button"
                            role="menuitem"
                            className="convo-actions-menu__item"
                            onClick={() => {
                              actions.onArchive?.(c.id);
                              setChatMenuFor(null);
                            }}
                          >
                            <Folder size={13} aria-hidden="true" /> أرشفة
                          </button>
                          <button
                            type="button"
                            role="menuitem"
                            className="convo-actions-menu__item convo-actions-menu__item--danger"
                            onClick={() => {
                              actions.onDelete?.(c.id);
                              setChatMenuFor(null);
                            }}
                          >
                            <Trash2 size={13} aria-hidden="true" /> حذف
                          </button>

                          {/* add / remove to project */}
                          {assigned ? (
                            <button
                              type="button"
                              role="menuitem"
                              className="convo-actions-menu__item"
                              onClick={() => {
                                removeChatFromProject(assigned, c.id);
                                setChatMenuFor(null);
                              }}
                            >
                              <X size={13} aria-hidden="true" /> إزالة من المشروع
                            </button>
                          ) : (
                            <div className="convo-actions-menu__item convo-actions-menu__sub">
                              <button
                                type="button"
                                onClick={() => setAddToFor(addToFor === c.id ? null : c.id)}
                                aria-haspopup="menu"
                                aria-expanded={addToFor === c.id}
                                className="convo-actions-menu__item"
                              >
                                <FolderPlus size={13} aria-hidden="true" /> إضافة إلى مشروع
                                <ChevronDown size={12} aria-hidden="true" style={{ marginInlineStart: 'auto' }} />
                              </button>
                              {addToFor === c.id && (
                                <div className="convo-actions-menu convo-actions-menu--nested" role="menu">
                                  {projects.length === 0 && (
                                    <span className="convo-actions-menu__item">لا توجد مشاريع — أنشئ واحداً أولاً.</span>
                                  )}
                                  {projects.map((p) => (
                                    <button
                                      key={p.id}
                                      type="button"
                                      role="menuitem"
                                      className="convo-actions-menu__item"
                                      onClick={() => {
                                        addChatToProject(p.id, c.id);
                                        setAddToFor(null);
                                        setChatMenuFor(null);
                                        setOpenProject(p.id);
                                      }}
                                    >
                                      <Folder size={13} aria-hidden="true" /> {p.name}
                                    </button>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* ── Recently ─────────────────────────────────────────────────── */}
        {recent.length > 0 && (
          <div className="app-sidebar__section">
            <button
              type="button"
              className="app-sidebar__section-head app-sidebar__section-head--btn"
              onClick={() => setRecentOpen((o) => !o)}
              aria-expanded={recentOpen}
            >
              <span className="app-sidebar__section-title">الأخيرة</span>
              <ChevronDown
                size={14}
                aria-hidden="true"
                style={{ transform: recentOpen ? 'rotate(180deg)' : 'none' }}
              />
            </button>
            {recentOpen && (
              <div className="convo-list" role="list" aria-label="المحادثات الأخيرة">
                {recent.map((r) => (
                  <button
                    key={r.conversationId}
                    type="button"
                    className="convo-list__link"
                    onClick={() => onSelect?.(r.conversationId)}
                    title={titleOf(r.conversationId)}
                  >
                    <span aria-hidden="true"><FolderOpen size={14} /></span>
                    <span className="convo-list__title">{titleOf(r.conversationId)}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </nav>

      {/* ── Footer ────────────────────────────────────────────────────── */}
      <div className="sidebar__footer">
        <div className="credit-badge-row">
          <button
            type="button"
            className={`credit-badge credit-badge--full${isLow ? ' credit-badge--low' : ''}`}
            onClick={() => setBuyOpen(true)}
            aria-label={`رصيدك: ${balance.toFixed(0)} نقطة — اضغط للشحن`}
          >
            <span aria-hidden="true">{isLow ? '⚠️' : '⚡'}</span>
            <span>{balance.toFixed(0)} نقطة</span>
            {isLow && <span className="credit-badge__cta">شحن</span>}
          </button>
          <button
            type="button"
            className="icon-btn icon-btn--sm"
            onClick={handleGrant}
            disabled={granting}
            aria-label="إضافة رصيد تجريبي"
            title="إضافة 300 نقطة تجريبية"
          >
            <Zap size={14} aria-hidden="true" />
          </button>
        </div>

        <div className="app-sidebar__footer-row">
          {student && ['developer', 'admin', 'superadmin'].includes(student.role) && (
            <Link to="/admin" className="app-sidebar__footer-link">
              <LayoutDashboard size={16} aria-hidden="true" />
              <span>لوحة التحكم</span>
            </Link>
          )}
          <button
            type="button"
            className="icon-btn icon-btn--sm"
            onClick={toggleTheme}
            aria-label={theme === 'light' ? 'الوضع الليلي' : 'الوضع النهاري'}
            title={theme === 'light' ? 'الوضع الليلي' : 'الوضع النهاري'}
          >
            {theme === 'light' ? <Moon size={16} aria-hidden="true" /> : <Sun size={16} aria-hidden="true" />}
          </button>
          <Link to="/settings" className="app-sidebar__footer-link">
            <Settings size={16} aria-hidden="true" />
            <span>الإعدادات</span>
          </Link>
        </div>

        {student && (
          <div className="user-card">
            <span className="user-card__avatar" aria-hidden="true">{avatarInitial}</span>
            <span className="user-card__name">
              {student.display_name || student.email}
            </span>
            <button
              type="button"
              className="icon-btn icon-btn--sm"
              onClick={handleLogout}
              aria-label="تسجيل الخروج"
              title="تسجيل الخروج"
            >
              <LogOut size={16} aria-hidden="true" />
            </button>
          </div>
        )}
      </div>

      <BuyCreditsModal open={buyOpen} onClose={() => setBuyOpen(false)} />
    </aside>
  );
}

/* ── Project row ─────────────────────────────────────────────────────────── */

interface ProjectRowProps {
  project: Project;
  conversations: { id: string; title: string }[];
  expanded: boolean;
  renaming: boolean;
  renameValue: string;
  menuOpen: boolean;
  onToggle: () => void;
  onRenameChange: (v: string) => void;
  onCommitRename: () => void;
  onCancelRename: () => void;
  onOpenMenu: () => void;
  onCloseMenu: () => void;
  onStartRename: () => void;
  onDelete: () => void;
  onSelectChat: (id: string) => void;
}

function ProjectRow({
  project,
  conversations,
  expanded,
  renaming,
  renameValue,
  menuOpen,
  onToggle,
  onRenameChange,
  onCommitRename,
  onCancelRename,
  onOpenMenu,
  onCloseMenu,
  onStartRename,
  onDelete,
  onSelectChat,
}: ProjectRowProps) {
  const memberIds = chatsOfProject(project.id);
  const members = conversations.filter((c) => memberIds.includes(c.id));

  return (
    <div className="sidebar-project">
      <div className="sidebar-project__head">
        {renaming ? (
          <input
            className="input convo-rename-input"
            value={renameValue}
            onChange={(e) => onRenameChange(e.target.value)}
            onBlur={onCommitRename}
            onKeyDown={(e) => {
              if (e.key === 'Enter') onCommitRename();
              if (e.key === 'Escape') onCancelRename();
            }}
            autoFocus
            aria-label="اسم المشروع"
          />
        ) : (
          <button
            type="button"
            className="sidebar-project__toggle"
            onClick={onToggle}
            aria-expanded={expanded}
          >
            <ChevronDown
              size={14}
              aria-hidden="true"
              style={{ transform: expanded ? 'rotate(180deg)' : 'none' }}
            />
            <Folder size={14} aria-hidden="true" />
            <span className="sidebar-project__name">{project.name}</span>
            <span className="badge badge--muted" style={{ fontSize: '10px' }}>
              {members.length}
            </span>
          </button>
        )}

        <button
          type="button"
          className="icon-btn icon-btn--sm"
          onClick={onOpenMenu}
          aria-label={`خيارات المشروع ${project.name}`}
          aria-haspopup="menu"
          aria-expanded={menuOpen}
        >
          <MoreHorizontal size={15} aria-hidden="true" />
        </button>

        {menuOpen && (
          <div className="convo-actions-menu" role="menu">
            <button
              type="button"
              role="menuitem"
              className="convo-actions-menu__item"
              onClick={onStartRename}
            >
              <Pencil size={13} aria-hidden="true" /> إعادة تسمية
            </button>
            <button
              type="button"
              role="menuitem"
              className="convo-actions-menu__item convo-actions-menu__item--danger"
              onClick={onDelete}
            >
              <Trash2 size={13} aria-hidden="true" /> حذف
            </button>
            <button
              type="button"
              role="menuitem"
              className="convo-actions-menu__item"
              onClick={onCloseMenu}
            >
              <X size={13} aria-hidden="true" /> إغلاق
            </button>
          </div>
        )}
      </div>

      {expanded && (
        <div className="sidebar-project__chats">
          {members.length === 0 ? (
            <p className="app-sidebar__empty">لا توجد محادثات في هذا المشروع.</p>
          ) : (
            members.map((c) => (
              <div key={c.id} className="convo-list__item">
                <button
                  type="button"
                  className="convo-list__link"
                  onClick={() => onSelectChat(c.id)}
                  title={c.title}
                >
                  <span className="convo-list__title">{c.title}</span>
                </button>
                <button
                  type="button"
                  className="icon-btn icon-btn--sm"
                  onClick={() => removeChatFromProject(project.id, c.id)}
                  aria-label={`إزالة ${c.title} من المشروع`}
                  title="إزالة من المشروع"
                >
                  <X size={13} aria-hidden="true" />
                </button>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

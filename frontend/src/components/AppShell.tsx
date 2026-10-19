/**
 * AppShell — authenticated layout wrapper.
 *
 * On the home page ('/'), it renders the exact Stitch Perplexity interface directly.
 * On other pages (e.g. /chat, /settings), it provides the application shell.
 */
import { useEffect, useState, type ReactNode } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { ArrowRight, Menu } from 'lucide-react';
import { useAuth } from '../contexts/useAuth';
import { AppSidebar } from './layout/AppSidebar';
import { useQuery } from '@tanstack/react-query';
import { conversationsApi } from '../api/conversations';

const STORAGE_KEY = 'spetser.sidebarCollapsed';

function readCollapsed(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === '1';
  } catch {
    return false;
  }
}

export function AppShell({ children }: { children?: ReactNode }) {
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(readCollapsed);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [prevPath, setPrevPath] = useState(location.pathname);

  // If on the home page, let HomePage render the exact Stitch layout directly
  const isHome = location.pathname === '/';

  // Derive mobile open reset on route change without effect warning
  if (prevPath !== location.pathname) {
    setPrevPath(location.pathname);
    setMobileOpen(false);
  }

  // Persist the desktop collapse preference.
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, collapsed ? '1' : '0');
    } catch {
      /* storage unavailable — ignore */
    }
  }, [collapsed]);

  // Close the mobile drawer with Escape.
  useEffect(() => {
    if (!mobileOpen) return;
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.key === 'Escape') setMobileOpen(false);
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [mobileOpen]);

  const { data: conversations = [] } = useQuery({
    queryKey: ['conversations'],
    queryFn: () => conversationsApi.list(),
    enabled: isAuthenticated,
    staleTime: 30_000,
  });

  const sidebarConversations: { id: string; title: string }[] = conversations.map((c) => ({
    id: c.id,
    title: c.title ?? 'محادثة بدون عنوان',
  }));

  const location_activeId = location.pathname.startsWith('/chat/')
    ? location.pathname.split('/')[2]
    : null;

  const toggleCollapsed = () => {
    if (window.innerWidth <= 768) {
      setMobileOpen((o) => !o);
    } else {
      setCollapsed((c) => !c);
    }
  };
  const closeMobile = () => setMobileOpen(false);

  if (isHome) {
    return <main className="w-full min-h-screen bg-parchment">{children ?? <Outlet />}</main>;
  }

  return (
    <div
      className={`app-shell${collapsed ? ' app-shell--collapsed' : ''}`}
      data-sidebar-open={mobileOpen ? 'true' : undefined}
    >
      {/* ── Mobile top bar with hamburger ─────────────────────────────── */}
      <header className="app-shell__topbar">
        <button
          type="button"
          className="icon-btn app-shell__menu-btn"
          onClick={toggleCollapsed}
          aria-label={collapsed ? 'إظهار القائمة' : 'إخفاء القائمة'}
          title={collapsed ? 'إظهار القائمة' : 'إخفاء القائمة'}
          aria-expanded={!collapsed && !mobileOpen}
        >
          <Menu size={20} aria-hidden="true" />
        </button>

        <div className="app-shell__topbar-title">
          <span className="brand-mark__name">Perplexity</span>
        </div>

        <button
          type="button"
          className="btn btn--ghost btn--sm app-shell__new-chat-btn"
          onClick={() => navigate('/')}
        >
          <span className="sr-only">محادثة جديدة</span>
          <ArrowRight size={16} aria-hidden="true" />
        </button>
      </header>

      {/* ── Sidebar ───────────────────────────────────────────────────── */}
      <AppSidebar
        conversations={sidebarConversations}
        activeId={location_activeId}
        onSelect={(id) => navigate(`/chat/${id}`)}
        onNewChat={() => navigate('/')}
      />

      {/* ── Mobile overlay ────────────────────────────────────────────── */}
      {mobileOpen && (
        <div
          className="app-shell__overlay"
          onClick={closeMobile}
          aria-hidden="true"
        />
      )}

      {/* ── Main content ──────────────────────────────────────────────── */}
      <main className="app-shell__content">
        {children ?? <Outlet />}
      </main>
    </div>
  );
}
export default AppShell;

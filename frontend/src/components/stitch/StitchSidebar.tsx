import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/useAuth';
import { useQuery } from '@tanstack/react-query';
import { conversationsApi } from '../../api/conversations';

interface StitchSidebarProps {
  onNewThread?: () => void;
}

export function StitchSidebar({ onNewThread }: StitchSidebarProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { student, isAuthenticated, logout } = useAuth();
  const [threadsOpen, setThreadsOpen] = useState(false);
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);

  const { data: conversations = [] } = useQuery({
    queryKey: ['conversations'],
    queryFn: () => conversationsApi.list(),
    enabled: isAuthenticated,
  });

  const isCurrent = (path: string) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  const handleNewThread = () => {
    if (onNewThread) {
      onNewThread();
    } else {
      navigate('/');
    }
  };

  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-surface-container-low border-r border-warm-mist z-50 flex flex-col justify-between p-space-lg select-none">
      <div className="flex flex-col gap-space-lg">
        {/* Brand */}
        <div
          onClick={() => navigate('/')}
          className="flex items-center gap-space-sm px-space-xs py-space-xs cursor-pointer group"
        >
          <span className="material-symbols-outlined text-primary text-[24px] group-hover:rotate-180 transition-transform duration-500">
            all_inclusive
          </span>
          <span className="font-headline-md text-headline-md tracking-tight text-ink font-semibold">
            Perplexity
          </span>
        </div>

        {/* Main Navigation */}
        <nav className="flex flex-col gap-space-xs">
          <button
            type="button"
            onClick={handleNewThread}
            className={`w-full flex items-center gap-space-md px-space-md py-space-sm transition-colors rounded-lg font-medium cursor-pointer ${
              isCurrent('/')
                ? 'bg-primary-container text-on-primary'
                : 'text-graphite hover:bg-surface-container-high hover:text-on-surface'
            }`}
          >
            <span className="material-symbols-outlined text-[20px]">search</span>
            <span>New Thread</span>
          </button>

          <button
            type="button"
            onClick={() => navigate('/')}
            className={`w-full flex items-center gap-space-md px-space-md py-space-sm rounded-lg text-graphite hover:bg-surface-container-high hover:text-on-surface transition-colors font-label-md text-label-md cursor-pointer`}
          >
            <span className="material-symbols-outlined text-[20px]">explore</span>
            <span>Discover</span>
          </button>

          <button
            type="button"
            onClick={() => navigate('/history')}
            className={`w-full flex items-center gap-space-md px-space-md py-space-sm rounded-lg text-graphite hover:bg-surface-container-high hover:text-on-surface transition-colors font-label-md text-label-md cursor-pointer ${
              isCurrent('/history') ? 'bg-surface-container-high text-on-surface font-medium' : ''
            }`}
          >
            <span className="material-symbols-outlined text-[20px]">grid_view</span>
            <span>Spaces</span>
          </button>

          <button
            type="button"
            onClick={() => navigate('/history')}
            className="w-full flex items-center gap-space-md px-space-md py-space-sm rounded-lg text-graphite hover:bg-surface-container-high hover:text-on-surface transition-colors font-label-md text-label-md cursor-pointer"
          >
            <span className="material-symbols-outlined text-[20px]">folder_open</span>
            <span>Library</span>
          </button>
        </nav>

        {/* Workspace Section */}
        <div className="pt-space-md border-t border-warm-mist flex flex-col gap-space-xs">
          <span className="px-space-md font-label-xs text-label-xs text-ash uppercase tracking-wider">
            Workspace
          </span>

          <button
            type="button"
            onClick={() => navigate('/referrals')}
            className="w-full flex items-center gap-space-md px-space-md py-space-sm rounded-lg text-graphite hover:bg-surface-container-high hover:text-on-surface transition-colors font-label-md text-label-md cursor-pointer"
          >
            <span className="material-symbols-outlined text-[20px]">hub</span>
            <span>Connectors</span>
          </button>

          <button
            type="button"
            onClick={() => setThreadsOpen(!threadsOpen)}
            className={`w-full flex items-center justify-between px-space-md py-space-sm rounded-lg text-graphite hover:bg-surface-container-high hover:text-on-surface transition-colors font-label-md text-label-md cursor-pointer ${
              threadsOpen ? 'bg-surface-container-high text-on-surface' : ''
            }`}
          >
            <div className="flex items-center gap-space-md">
              <span className="material-symbols-outlined text-[20px]">forum</span>
              <span>Threads</span>
            </div>
            {conversations.length > 0 && (
              <span className="text-[11px] px-1.5 py-0.5 rounded-full bg-surface-container text-ash font-medium">
                {conversations.length}
              </span>
            )}
          </button>

          {/* Expanded recent threads list */}
          {threadsOpen && (
            <div className="flex flex-col gap-1 pl-6 pr-2 py-1 max-h-48 overflow-y-auto">
              {conversations.length === 0 ? (
                <span className="text-xs text-ash px-2 py-1">No active threads</span>
              ) : (
                conversations.slice(0, 6).map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => navigate(`/chat/${c.id}`)}
                    className="text-left text-xs text-graphite hover:text-ink truncate py-1 px-2 rounded hover:bg-surface-container transition-colors"
                    title={c.title || 'Untitled'}
                  >
                    {c.title || 'Untitled'}
                  </button>
                ))
              )}
            </div>
          )}
        </div>
      </div>

      {/* Bottom: Settings + User profile box */}
      <div className="flex flex-col gap-space-xs pt-space-md border-t border-warm-mist relative">
        <button
          type="button"
          onClick={() => navigate('/settings')}
          className={`w-full flex items-center gap-space-md px-space-md py-space-sm rounded-lg text-graphite hover:bg-surface-container-high hover:text-on-surface transition-colors font-label-md text-label-md cursor-pointer ${
            isCurrent('/settings') ? 'bg-surface-container-high text-on-surface font-medium' : ''
          }`}
        >
          <span className="material-symbols-outlined text-[20px]">settings</span>
          <span>Settings</span>
        </button>

        {/* Profile Card */}
        <div className="flex items-center justify-between px-space-md py-space-sm rounded-lg bg-soft-paper border border-warm-mist mt-space-xs shadow-xs">
          <div
            onClick={() => navigate('/settings')}
            className="flex items-center gap-space-sm cursor-pointer truncate"
          >
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0">
              <span className="material-symbols-outlined text-on-primary text-[18px]">person</span>
            </div>
            <div className="flex flex-col truncate">
              <span className="font-label-sm text-label-sm text-ink truncate font-medium">
                {student?.display_name || 'Scholar Pro'}
              </span>
              <span className="font-label-xs text-label-xs text-ash">
                {student?.role ? `${student.role.toUpperCase()} Plan` : 'Free Plan'}
              </span>
            </div>
          </div>

          <button
            type="button"
            onClick={() => setProfileMenuOpen(!profileMenuOpen)}
            className="text-graphite hover:text-primary transition-colors cursor-pointer p-1"
          >
            <span className="material-symbols-outlined text-[20px]">more_vert</span>
          </button>
        </div>

        {/* Profile Dropdown Menu */}
        {profileMenuOpen && (
          <div className="absolute bottom-16 right-2 bg-soft-paper border border-warm-mist rounded-xl shadow-lg p-1.5 min-w-[160px] z-50 flex flex-col gap-1">
            <button
              type="button"
              onClick={() => {
                navigate('/settings');
                setProfileMenuOpen(false);
              }}
              className="px-3 py-1.5 text-left text-xs rounded-lg text-ink hover:bg-surface-container transition-colors"
            >
              Account Settings
            </button>
            {isAuthenticated ? (
              <button
                type="button"
                onClick={() => {
                  void logout();
                  setProfileMenuOpen(false);
                }}
                className="px-3 py-1.5 text-left text-xs rounded-lg text-error hover:bg-error-container transition-colors"
              >
                Sign Out
              </button>
            ) : (
              <button
                type="button"
                onClick={() => {
                  navigate('/login');
                  setProfileMenuOpen(false);
                }}
                className="px-3 py-1.5 text-left text-xs rounded-lg text-primary font-medium hover:bg-surface-container transition-colors"
              >
                Sign In
              </button>
            )}
          </div>
        )}
      </div>
    </aside>
  );
}

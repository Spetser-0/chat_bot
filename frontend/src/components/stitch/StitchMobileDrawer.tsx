import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/useAuth';
import { useQuery } from '@tanstack/react-query';
import { conversationsApi } from '../../api/conversations';
import { BRAND } from '../../lib/constants';

interface StitchMobileDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onNewThread?: () => void;
}

export function StitchMobileDrawer({ isOpen, onClose, onNewThread }: StitchMobileDrawerProps) {
  const navigate = useNavigate();
  const { student, isAuthenticated, logout } = useAuth();

  const { data: conversations = [] } = useQuery({
    queryKey: ['conversations'],
    queryFn: () => conversationsApi.list(),
    enabled: isAuthenticated,
  });

  if (!isOpen) return null;

  const handleNav = (path: string) => {
    navigate(path);
    onClose();
  };

  const handleNew = () => {
    if (onNewThread) onNewThread();
    else navigate('/');
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex select-none">
      {/* Backdrop */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-ink/30 backdrop-blur-sm transition-opacity"
        aria-hidden="true"
      />

      {/* Drawer content */}
      <div className="relative w-72 max-w-[80vw] h-full bg-surface-container-low border-r border-warm-mist shadow-xl flex flex-col justify-between p-space-lg z-10 animate-in slide-in-from-left duration-200">
        <div className="flex flex-col gap-space-lg">
          {/* Top: Close button & Brand */}
          <div className="flex items-center justify-between">
            <div
              onClick={() => handleNav('/')}
              className="flex items-center gap-space-sm cursor-pointer"
            >
              <img
                src={BRAND.iconSvg}
                alt=""
                className="w-6 h-6 object-contain"
              />
              <span className="font-headline-md text-headline-md tracking-tight text-ink font-semibold">
                {BRAND.nameEn}
              </span>
            </div>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-full flex items-center justify-center text-graphite hover:text-ink hover:bg-surface-container"
              aria-label="Close menu"
            >
              ×
            </button>
          </div>

          {/* Navigation Links */}
          <nav className="flex flex-col gap-space-xs">
            <button
              type="button"
              onClick={handleNew}
              className="flex items-center gap-space-md px-space-md py-space-sm rounded-lg bg-primary-container text-on-primary font-medium text-left"
            >
              <span className="material-symbols-outlined text-[20px]">search</span>
              <span>New Thread</span>
            </button>

            <button
              type="button"
              onClick={() => handleNav('/')}
              className="flex items-center gap-space-md px-space-md py-space-sm rounded-lg text-graphite hover:bg-surface-container-high hover:text-on-surface font-label-md text-label-md text-left"
            >
              <span className="material-symbols-outlined text-[20px]">explore</span>
              <span>Discover</span>
            </button>

            <button
              type="button"
              onClick={() => handleNav('/history')}
              className="flex items-center gap-space-md px-space-md py-space-sm rounded-lg text-graphite hover:bg-surface-container-high hover:text-on-surface font-label-md text-label-md text-left"
            >
              <span className="material-symbols-outlined text-[20px]">grid_view</span>
              <span>Spaces</span>
            </button>

            <button
              type="button"
              onClick={() => handleNav('/history')}
              className="flex items-center gap-space-md px-space-md py-space-sm rounded-lg text-graphite hover:bg-surface-container-high hover:text-on-surface font-label-md text-label-md text-left"
            >
              <span className="material-symbols-outlined text-[20px]">folder_open</span>
              <span>Library</span>
            </button>
          </nav>

          {/* Workspace & Threads */}
          <div className="pt-space-md border-t border-warm-mist flex flex-col gap-space-xs">
            <span className="px-space-md font-label-xs text-label-xs text-ash uppercase tracking-wider">
              Workspace
            </span>

            <button
              type="button"
              onClick={() => handleNav('/referrals')}
              className="flex items-center gap-space-md px-space-md py-space-sm rounded-lg text-graphite hover:bg-surface-container-high hover:text-on-surface font-label-md text-label-md text-left"
            >
              <span className="material-symbols-outlined text-[20px]">hub</span>
              <span>Connectors</span>
            </button>

            <div className="flex items-center justify-between px-space-md py-space-sm font-label-md text-graphite">
              <div className="flex items-center gap-space-md">
                <span className="material-symbols-outlined text-[20px]">forum</span>
                <span>Threads</span>
              </div>
              {conversations.length > 0 && (
                <span className="text-[11px] px-1.5 py-0.5 rounded-full bg-surface-container text-ash font-medium">
                  {conversations.length}
                </span>
              )}
            </div>

            {/* List recent conversations */}
            {conversations.length > 0 && (
              <div className="flex flex-col gap-1 pl-6 pr-2 max-h-36 overflow-y-auto">
                {conversations.slice(0, 5).map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => handleNav(`/chat/${c.id}`)}
                    className="text-left text-xs text-graphite hover:text-ink truncate py-1 px-2 rounded hover:bg-surface-container"
                  >
                    {c.title || 'Untitled'}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Bottom: Settings + Profile */}
        <div className="flex flex-col gap-space-xs pt-space-md border-t border-warm-mist">
          <button
            type="button"
            onClick={() => handleNav('/settings')}
            className="flex items-center gap-space-md px-space-md py-space-sm rounded-lg text-graphite hover:bg-surface-container-high hover:text-on-surface font-label-md text-label-md text-left"
          >
            <span className="material-symbols-outlined text-[20px]">settings</span>
            <span>Settings</span>
          </button>

          <div className="flex items-center justify-between px-space-md py-space-sm rounded-lg bg-soft-paper border border-warm-mist mt-space-xs">
            <div
              onClick={() => handleNav('/settings')}
              className="flex items-center gap-space-sm cursor-pointer truncate"
            >
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0">
                <span className="material-symbols-outlined text-on-primary text-[18px]">person</span>
              </div>
              <div className="flex flex-col truncate">
                <span className="font-label-sm text-label-sm text-ink font-medium truncate">
                  {student?.display_name || 'Scholar Pro'}
                </span>
                <span className="font-label-xs text-label-xs text-ash">Free Plan</span>
              </div>
            </div>

            {isAuthenticated ? (
              <button
                type="button"
                onClick={() => {
                  void logout();
                  onClose();
                }}
                className="text-xs text-error font-medium hover:underline p-1"
              >
                Exit
              </button>
            ) : (
              <button
                type="button"
                onClick={() => handleNav('/login')}
                className="text-xs text-primary font-medium hover:underline p-1"
              >
                Sign In
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

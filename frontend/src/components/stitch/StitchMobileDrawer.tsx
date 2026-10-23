import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/useAuth';
import { useQuery } from '@tanstack/react-query';
import { conversationsApi } from '../../api/conversations';
import { BRAND } from '../../lib/constants';
import { useLanguage } from '../../contexts/useLanguage';
import { mainNavItems, bottomNavItems } from '../../lib/navigation';

interface StitchMobileDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onNewThread?: () => void;
}

export function StitchMobileDrawer({ isOpen, onClose, onNewThread }: StitchMobileDrawerProps) {
  const navigate = useNavigate();
  const { student, isAuthenticated, logout } = useAuth();
  const { t } = useLanguage();

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
      <div className="relative w-72 max-w-[80vw] h-dvh bg-surface-container-low border-r border-warm-mist shadow-xl flex flex-col z-10 animate-in slide-in-from-left duration-200">
        {/* Scrollable content area */}
        <div className="flex-1 overflow-y-auto p-space-lg pb-safe">
          <div className="flex flex-col gap-space-lg">
            {/* Top: Brand & Close */}
            <div className="flex items-center justify-between">
              <div
                onClick={() => handleNav('/')}
                className="flex items-center gap-space-sm px-space-xs py-space-xs cursor-pointer group"
              >
                <img
                  src={BRAND.iconSvg}
                  alt=""
                  className="w-6 h-6 object-contain group-hover:scale-110 transition-transform duration-300"
                />
                <span className="font-headline-md text-headline-md tracking-tight text-ink font-semibold">
                  {BRAND.nameEn}
                </span>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="w-8 h-8 rounded-full flex items-center justify-center text-graphite hover:text-ink hover:bg-surface-container cursor-pointer"
                aria-label="Close menu"
              >
                ×
              </button>
            </div>

            {/* Navigation Items */}
            <nav className="flex flex-col gap-space-xs">
              {mainNavItems.map((item) => (
                <button
                  key={item.path}
                  type="button"
                  onClick={() => {
                    if (item.path === '/') handleNew();
                    else handleNav(item.path);
                  }}
                  className="w-full flex items-center gap-space-md px-space-md py-space-sm rounded-lg text-graphite hover:bg-surface-container-high hover:text-on-surface transition-colors font-label-md text-label-md cursor-pointer text-left"
                >
                  <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
                  <span>{t(item.labelKey)}</span>
                </button>
              ))}
            </nav>

            {/* Recent Conversations */}
            {conversations.length > 0 && (
              <div className="flex flex-col gap-space-xs">
                <span className="px-space-md font-label-xs text-label-xs text-ash uppercase tracking-wider">
                  {t('nav.recent')}
                </span>
                {conversations.slice(0, 10).map((conv) => (
                  <button
                    key={conv.id}
                    type="button"
                    onClick={() => handleNav(`/chat/${conv.id}`)}
                    className="w-full flex items-center gap-space-md px-space-md py-space-sm rounded-lg text-graphite hover:bg-surface-container-high hover:text-on-surface transition-colors font-label-md text-label-md cursor-pointer text-left"
                  >
                    <span className="material-symbols-outlined text-[20px]">chat</span>
                    <span className="truncate">{conv.title || 'Untitled'}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Fixed bottom: Settings + Profile (always visible) */}
        <div className="flex flex-col gap-space-xs p-space-lg border-t border-warm-mist bg-surface-container-low pb-safe">
          {bottomNavItems.map((item) => (
            <button
              key={item.path}
              type="button"
              onClick={() => handleNav(item.path)}
              className="flex items-center gap-space-md px-space-md py-space-sm rounded-lg text-graphite hover:bg-surface-container-high hover:text-on-surface font-label-md text-label-md text-left cursor-pointer"
            >
              <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
              <span>{t(item.labelKey)}</span>
            </button>
          ))}

          <div className="flex items-center justify-between px-space-md py-space-sm rounded-lg bg-soft-paper border border-warm-mist mt-space-xs">
            <div
              onClick={() => handleNav('/settings')}
              className="flex items-center gap-space-sm cursor-pointer truncate flex-1"
            >
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0">
                <span className="material-symbols-outlined text-on-primary text-[18px]">person</span>
              </div>
              <div className="flex flex-col truncate">
                <span className="font-label-sm text-label-sm text-ink font-medium truncate">
                  {student?.display_name || 'Guest'}
                </span>
                <span className="font-label-xs text-label-xs text-ash">
                  {isAuthenticated ? t('nav.freePlan') : t('nav.signIn')}
                </span>
              </div>
            </div>
            {isAuthenticated ? (
              <button
                type="button"
                onClick={() => {
                  void logout();
                  onClose();
                }}
                className="text-xs text-error font-medium hover:underline p-1 shrink-0 cursor-pointer"
              >
                {t('nav.signOut')}
              </button>
            ) : (
              <button
                type="button"
                onClick={() => handleNav('/login')}
                className="text-xs text-primary font-medium hover:underline p-1 shrink-0 cursor-pointer"
              >
                {t('nav.signIn')}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

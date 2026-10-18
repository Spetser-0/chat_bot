/**
 * ChatTopBar — slim header for the chat page: back button, title, actions.
 */
import { ArrowRight, PanelRightClose, PanelRightOpen } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface ChatTopBarProps {
  title?: string;
  onToggleSidebar?: () => void;
  sidebarCollapsed?: boolean;
}

export function ChatTopBar({ title, onToggleSidebar, sidebarCollapsed }: ChatTopBarProps) {
  const navigate = useNavigate();

  return (
    <header className="chat-topbar">
      <button
        type="button"
        className="icon-btn"
        onClick={() => navigate('/')}
        aria-label="العودة للرئيسية"
        title="العودة للرئيسية"
      >
        <ArrowRight size={18} aria-hidden="true" />
      </button>

      <div className="chat-topbar__title">
        {title || 'محادثة جديدة'}
      </div>

      {onToggleSidebar && (
        <button
          type="button"
          className="icon-btn"
          onClick={onToggleSidebar}
          aria-label={sidebarCollapsed ? 'إظهار القائمة' : 'إخفاء القائمة'}
          title={sidebarCollapsed ? 'إظهار القائمة' : 'إخفاء القائمة'}
        >
          {sidebarCollapsed ? (
            <PanelRightOpen size={18} aria-hidden="true" />
          ) : (
            <PanelRightClose size={18} aria-hidden="true" />
          )}
        </button>
      )}
    </header>
  );
}

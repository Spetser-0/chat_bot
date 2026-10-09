/**
 * components/chat/ChatLayout.tsx
 * ──────────────────────────────
 * Full chat layout: conversation sidebar + top bar + messages area +
 * fixed composer (Phase 9, Lessons 9.1 + 9.4).
 */
import { type ReactNode } from 'react';
import { ConversationSidebar, type SidebarActions } from './ConversationSidebar';
import { ChatTopBar } from './ChatTopBar';
import { Composer } from './Composer';
import { SkipLink } from '../ui/SkipLink';

interface ChatLayoutProps {
  children: ReactNode;
  title?: string;
  conversations?: { id: string; title: string }[];
  activeConversationId?: string | null;
  sidebarActions?: SidebarActions;
  skills?: { slug: string; name: string; is_premium?: boolean }[];
  activeSkillSlug?: string;
  onSkillChange?: (slug: string) => void;
  onSend?: (message: string) => void;
  onStop?: () => void;
  composerDisabled?: boolean;
  isStreaming?: boolean;
  onNewChat?: () => void;
  sidebarOpen?: boolean;
  onToggleSidebar?: () => void;
  onConversationSelect?: (id: string) => void;
}

export function ChatLayout({
  children,
  title,
  conversations,
  activeConversationId,
  sidebarActions,
  skills,
  activeSkillSlug,
  onSkillChange,
  onSend,
  onStop,
  composerDisabled,
  isStreaming,
  onNewChat,
  sidebarOpen,
  onToggleSidebar,
  onConversationSelect,
}: ChatLayoutProps) {
  return (
    <div className="chat-layout" dir="rtl" data-sidebar-open={sidebarOpen}>
      <SkipLink />
      <ConversationSidebar
        conversations={conversations}
        activeId={activeConversationId}
        onNewChat={onNewChat}
        actions={sidebarActions}
        onSelect={onConversationSelect}
      />
      <div className="chat-layout__main">
        <ChatTopBar
          title={title}
          skills={skills}
          activeSkillSlug={activeSkillSlug}
          onSkillChange={onSkillChange}
          onToggleSidebar={onToggleSidebar}
        />
        <div
          className="chat-layout__messages"
          id="main-content"
          tabIndex={-1}
          role="log"
          aria-live="polite"
          aria-relevant="additions text"
          aria-label="رسائل المحادثة"
        >
          <div className="chat-layout__messages-inner">{children}</div>
        </div>
        <div className="chat-layout__composer-dock">
          <div className="chat-layout__composer-inner">
            <Composer
              onSend={onSend}
              onStop={onStop}
              disabled={composerDisabled}
              isStreaming={isStreaming}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

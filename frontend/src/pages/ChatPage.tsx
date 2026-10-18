/**
 * pages/ChatPage.tsx
 * ──────────────────
 * Chat page. The sidebar comes from AppShell (AppSidebar) — this page renders
 * only the conversation column: header, messages and the composer with the
 * floating quick-action chips above it.
 */
import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Sparkles } from 'lucide-react';
import { ChatTopBar } from '../components/chat/ChatTopBar';
import { Composer } from '../components/chat/Composer';
import { Markdown } from '../components/chat/Markdown';
import { QuickActions } from '../components/chat/QuickActions';
import { conversationsApi } from '../api/conversations';
import { useChat } from '../hooks/useChat';
import { touchRecent } from '../lib/projects';
import type { QuickActionId } from '../lib/quickActions';

const QUICK_LABELS: Record<QuickActionId, string> = {
  presentation: 'إنشاء عرض تقديمي',
  math: 'حل مسائل رياضية',
  report: 'كتابة بحث / تقرير',
};

export function ChatPage() {
  const { conversationId } = useParams<{ conversationId: string }>();
  const navigate = useNavigate();
  const [quickAction, setQuickAction] = useState<QuickActionId | null>(null);

  const chat = useChat(
    useCallback(
      (id: string) => navigate(`/chat/${id}`, { replace: true }),
      [navigate],
    ),
  );

  const { data: conversations = [] } = useQuery({
    queryKey: ['conversations'],
    queryFn: () => conversationsApi.list(),
  });

  // Hydrate when the route changes to a specific conversation.
  useEffect(() => {
    if (conversationId) {
      touchRecent(conversationId);
      if (chat.conversationId !== conversationId) {
        void chat.loadConversation(conversationId);
      }
    } else if (chat.conversationId) {
      chat.reset();
    }
    // Only react to route changes; chat methods are stable enough here.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId]);

  const activeTitle =
    conversations.find((c) => c.id === conversationId)?.title ?? 'المحادثة الأكاديمية';

  return (
    <div className="chat-page" dir="rtl">
      <ChatTopBar title={activeTitle} />

      <div
        className="chat-page__messages"
        id="main-content"
        tabIndex={-1}
        role="log"
        aria-live="polite"
        aria-relevant="additions text"
        aria-label="رسائل المحادثة"
      >
        <div className="chat-page__messages-inner">
          {chat.messages.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state__icon" aria-hidden="true">
                <Sparkles size={34} />
              </div>
              <div className="empty-state__title">ابدأ محادثة جديدة</div>
              <div className="empty-state__desc">
                اكتب سؤالك الأكاديمي في الأسفل وسأساعدك خطوة بخطوة.
              </div>
            </div>
          ) : (
            <>
              {chat.messages.map((m) => (
                <div key={m.id} className={`chat-msg chat-msg--${m.role}`}>
                  <div className="chat-msg__avatar" aria-hidden="true">
                    {m.role === 'user' ? '👤' : 'س'}
                  </div>
                  <div className="chat-msg__bubble">
                    {m.role === 'assistant' ? (
                      <Markdown content={m.content} />
                    ) : (
                      m.content
                    )}
                    {m.error && (
                      <div role="alert" className="chat-msg__error text-error text-sm">
                        {m.error}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {!chat.isStreaming && chat.messages.some((m) => m.role === 'assistant') && (
                <div style={{ textAlign: 'center', padding: 'var(--space-3)' }}>
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    onClick={chat.regenerate}
                    aria-label="إعادة توليد الرد"
                  >
                    🔄 إعادة توليد الرد
                  </button>
                </div>
              )}
              {chat.error && (
                <div role="alert" className="error-state text-sm" style={{ textAlign: 'center' }}>
                  {chat.error}
                </div>
              )}
            </>
          )}
        </div>
      </div>

      <div className="chat-page__dock">
        <QuickActions active={quickAction} onChange={setQuickAction} />
        <Composer
          onSend={(text) => chat.send(text)}
          onStop={chat.stop}
          isStreaming={chat.isStreaming}
          modeLabel={quickAction ? QUICK_LABELS[quickAction] : null}
          onClearMode={() => setQuickAction(null)}
        />
      </div>
    </div>
  );
}

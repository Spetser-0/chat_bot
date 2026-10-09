/**
 * pages/ChatPage.tsx
 * ──────────────────
 * Chat page (Phase 9, Lessons 9.1 + 9.4).
 * - Conversation list from GET /conversations (react-query)
 * - Streaming replies via SSE (useChat + streamChatCompletion)
 * - Stop generation, regenerate, rename/archive/delete
 * - Loads history from /chat/:conversationId
 */
import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ChatLayout } from '../components/chat/ChatLayout';
import { Markdown } from '../components/chat/Markdown';
import { conversationsApi } from '../api/conversations';
import { skillsApi } from '../api/skills';
import { useChat } from '../hooks/useChat';

export function ChatPage() {
  const { conversationId } = useParams<{ conversationId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [activeSkillSlug, setActiveSkillSlug] = useState<string>('');

  const chat = useChat(
    useCallback((id: string) => {
      navigate(`/chat/${id}`, { replace: true });
    }, [navigate]),
  );

  const { data: conversations = [] } = useQuery({
    queryKey: ['conversations'],
    queryFn: () => conversationsApi.list(),
  });

  const { data: skills = [] } = useQuery({
    queryKey: ['skills'],
    queryFn: () => skillsApi.list(),
    staleTime: 5 * 60_000,
  });

  // Hydrate when the route changes to a specific conversation.
  useEffect(() => {
    if (conversationId) {
      if (chat.conversationId !== conversationId) {
        void chat.loadConversation(conversationId).then((detail) => {
          // Restore the conversation's last active skill (or clear).
          setActiveSkillSlug(detail?.active_skill_slug ?? '');
        });
      }
    } else if (chat.conversationId) {
      chat.reset();
      setActiveSkillSlug('');
    }
    // Only react to route changes; chat methods are stable enough here.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId]);

  const renameMutation = useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) =>
      conversationsApi.update(id, { title }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['conversations'] }),
  });

  const archiveMutation = useMutation({
    mutationFn: (id: string) => conversationsApi.update(id, { is_archived: true }),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      if (id === conversationId) navigate('/chat', { replace: true });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => conversationsApi.remove(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      if (id === conversationId) {
        chat.reset();
        navigate('/chat', { replace: true });
      }
    },
  });

  const handleNewChat = () => {
    chat.reset();
    setActiveSkillSlug('');
    navigate('/chat', { replace: true });
  };

  const activeTitle =
    conversations.find((c) => c.id === conversationId)?.title ?? 'المحادثة الأكاديمية';

  return (
    <ChatLayout
      title={activeTitle}
      conversations={conversations.map((c) => ({
        id: c.id,
        title: c.title || 'محادثة بدون عنوان',
      }))}
      activeConversationId={conversationId ?? null}
      sidebarActions={{
        onRename: (id, title) => renameMutation.mutate({ id, title }),
        onArchive: (id) => archiveMutation.mutate(id),
        onDelete: (id) => deleteMutation.mutate(id),
      }}
      skills={skills.map((s) => ({
        slug: s.slug,
        name: s.name,
        is_premium: s.is_premium,
      }))}
      activeSkillSlug={activeSkillSlug}
      onSkillChange={setActiveSkillSlug}
      onSend={(text) => chat.send(text, activeSkillSlug || null)}
      onStop={chat.stop}
      isStreaming={chat.isStreaming}
      onNewChat={handleNewChat}
    >
      {chat.messages.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state__icon">💬</div>
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
    </ChatLayout>
  );
}

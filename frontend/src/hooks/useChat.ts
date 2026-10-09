/**
 * hooks/useChat.ts
 * ────────────────
 * Chat state for the streaming UI (Phase 9, Lesson 9.4).
 *
 * - send(text): optimistic user turn + streaming assistant placeholder
 * - stop(): abort in-flight stream, keep partial text
 * - regenerate(): drop trailing assistant turn and re-ask the last user turn
 * - loadConversation(id): hydrate from GET /conversations/{id}
 */
import { useCallback, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { conversationsApi, type ChatMessageOut } from '../api/conversations';
import { streamChatCompletion } from '../lib/streaming';

export interface UiMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  streaming?: boolean;
  error?: string;
}

let idCounter = 0;
const nextId = () => `local-${Date.now()}-${idCounter++}`;

function toUiMessages(remote: ChatMessageOut[]): UiMessage[] {
  return remote
    .filter((m) => m.role === 'user' || m.role === 'assistant')
    .map((m) => ({ id: m.id, role: m.role as 'user' | 'assistant', content: m.content }));
}

export function useChat(onConversationCreated?: (id: string) => void) {
  const queryClient = useQueryClient();
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const lastSkillRef = useRef<string | null>(null);

  const invalidateConversations = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: ['conversations'] });
  }, [queryClient]);

  const loadConversation = useCallback(async (id: string) => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsStreaming(false);
    setError(null);
    setConversationId(id);
    try {
      const detail = await conversationsApi.get(id);
      setMessages(toUiMessages(detail.messages));
      return detail;
    } catch {
      setMessages([]);
      setError('تعذر تحميل المحادثة.');
      return null;
    }
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    lastSkillRef.current = null;
    setMessages([]);
    setConversationId(null);
    setIsStreaming(false);
    setError(null);
  }, []);

  const streamTurn = useCallback(
    async (
      history: UiMessage[],
      lastUserText: string,
      activeId: string | null,
      skillSlug: string | null,
      regenerate = false,
    ) => {
      const controller = new AbortController();
      abortRef.current = controller;
      setIsStreaming(true);
      setError(null);
      lastSkillRef.current = skillSlug;

      const assistantId = nextId();
      // Placeholder assistant message we fill as chunks arrive.
      setMessages([
        ...history,
        { id: assistantId, role: 'assistant', content: '', streaming: true },
      ]);

      let acc = '';
      try {
        await streamChatCompletion(
          {
            message: lastUserText,
            conversation_id: activeId,
            skill_slug: skillSlug,
            regenerate,
            signal: controller.signal,
          },
          {
            onConversation: (id) => {
              setConversationId(id);
              onConversationCreated?.(id);
              invalidateConversations();
            },
            onChunk: (text) => {
              acc += text;
              setMessages((prev) =>
                prev.map((m) => (m.id === assistantId ? { ...m, content: acc } : m)),
              );
            },
            onError: (_code, message) => {
              setError(message);
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, streaming: false, error: message, content: acc }
                    : m,
                ),
              );
            },
          },
        );
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === 'AbortError') {
          // User pressed stop — keep whatever streamed so far.
        } else {
          setError('تعذر الاتصال بالخادم. تحقق من اتصالك.');
        }
      } finally {
        abortRef.current = null;
        setIsStreaming(false);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, streaming: false, content: m.content || acc }
              : m,
          ),
        );
        invalidateConversations();
      }
    },
    [invalidateConversations, onConversationCreated],
  );

  const send = useCallback(
    async (text: string, skillSlug: string | null = null) => {
      const trimmed = text.trim();
      if (!trimmed || isStreaming) return;
      const userMsg: UiMessage = { id: nextId(), role: 'user', content: trimmed };
      const history = [...messages, userMsg];
      setMessages(history);
      await streamTurn(history, trimmed, conversationId, skillSlug);
    },
    [conversationId, isStreaming, messages, streamTurn],
  );

  const regenerate = useCallback(async () => {
    if (isStreaming || messages.length === 0) return;
    // Find the last user turn; drop everything after it.
    let lastUserIdx = -1;
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === 'user') { lastUserIdx = i; break; }
    }
    if (lastUserIdx === -1) return;
    if (!conversationId) return;
    const history = messages.slice(0, lastUserIdx + 1);
    const lastUserText = history[lastUserIdx].content;
    // regenerate=true: backend reuses the persisted user turn (no duplicate row).
    await streamTurn(history, lastUserText, conversationId, lastSkillRef.current, true);
  }, [conversationId, isStreaming, messages, streamTurn]);

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return {
    messages,
    conversationId,
    isStreaming,
    error,
    send,
    stop,
    regenerate,
    loadConversation,
    reset,
  };
}

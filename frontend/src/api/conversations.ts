/**
 * api/conversations.ts — Conversation CRUD (Phase 9, Lesson 9.4 backend).
 */
import { apiClient, extractData } from './client';

export interface ConversationSummary {
  id: string;
  title: string | null;
  active_skill_slug: string | null;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface ChatMessageOut {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  skill_slug: string | null;
  provider_name: string | null;
  model_name: string | null;
  created_at: string;
}

export interface ConversationDetail extends ConversationSummary {
  messages: ChatMessageOut[];
}

export const conversationsApi = {
  async list(includeArchived = false): Promise<ConversationSummary[]> {
    const res = await apiClient.get('/conversations', {
      params: includeArchived ? { include_archived: true } : undefined,
    });
    return extractData<ConversationSummary[]>(res);
  },

  async get(id: string): Promise<ConversationDetail> {
    const res = await apiClient.get(`/conversations/${id}`);
    return extractData<ConversationDetail>(res);
  },

  async update(
    id: string,
    body: { title?: string; is_archived?: boolean },
  ): Promise<ConversationSummary> {
    const res = await apiClient.patch(`/conversations/${id}`, body);
    return extractData<ConversationSummary>(res);
  },

  async remove(id: string): Promise<{ deleted: boolean; conversation_id: string }> {
    const res = await apiClient.delete(`/conversations/${id}`);
    return extractData(res);
  },
};

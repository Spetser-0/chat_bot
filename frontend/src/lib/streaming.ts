/**
 * lib/streaming.ts
 * ────────────────
 * SSE stream parser for POST /api/v1/chat/completions (Phase 9, Lesson 9.4).
 *
 * Backend emits named SSE events (`event: <type>\ndata: <json>\n\n`):
 * conversation, chunk, done, error (see backend StreamEvent).
 * We parse with fetch + ReadableStream (axios does not stream reliably).
 */
import { API_BASE_URL } from '../api/client';

export interface StreamHandlers {
  onConversation?: (conversationId: string) => void;
  onChunk: (text: string) => void;
  onDone?: (info: {
    provider_slug?: string;
    model_name?: string;
    input_tokens?: number;
    output_tokens?: number;
    cost_usd?: number | string;
    latency_ms?: number;
  }) => void;
  onError?: (code: string, message: string) => void;
}

interface StreamRequest {
  message?: string;
  conversation_id?: string | null;
  skill_slug?: string | null;
  /** Re-answer last user turn without duplicating it (Lesson 9.10). */
  regenerate?: boolean;
  /** Abort signal for the stop-generation button. */
  signal?: AbortSignal;
}

/** Parse an SSE frame buffer into (eventName, jsonData) pairs. */
export function parseSseFrames(buffer: string): {
  events: { name: string; data: unknown }[];
  rest: string;
} {
  const events: { name: string; data: unknown }[] = [];
  // Normalize CRLF (some proxies/CDNs) to LF before frame splitting.
  let rest = buffer.replace(/\r\n/g, '\n');
  // Frames end with \n\n.
  let idx: number;
  while ((idx = rest.indexOf('\n\n')) !== -1) {
    const frame = rest.slice(0, idx);
    rest = rest.slice(idx + 2);
    let name = 'message';
    let dataLine = '';
    for (const line of frame.split('\n')) {
      if (line.startsWith('event: ')) name = line.slice(7).trim();
      else if (line.startsWith('data: ')) dataLine += line.slice(6);
    }
    if (!dataLine) continue;
    try {
      events.push({ name, data: JSON.parse(dataLine) });
    } catch {
      // Ignore malformed frames rather than crash the UI.
    }
  }
  return { events, rest };
}

/**
 * POST chat/completions with stream=true and dispatch named SSE events
 * to handlers. Resolves when the stream closes (or rejects on abort/network).
 */
export async function streamChatCompletion(
  req: StreamRequest,
  handlers: StreamHandlers,
): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/v1/chat/completions`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify({
      message: req.message,
      conversation_id: req.conversation_id ?? null,
      skill_slug: req.skill_slug ?? null,
      regenerate: req.regenerate ?? false,
      stream: true,
    }),
    signal: req.signal,
  });

  if (!res.ok || !res.body) {
    let code = 'http_error';
    let message = 'تعذر الاتصال بالخادم.';
    try {
      const body = await res.json();
      if (body?.error?.message) {
        message = body.error.message;
        code = body.error.code || code;
      }
    } catch {
      /* keep defaults */
    }
    handlers.onError?.(code, message);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const { events, rest } = parseSseFrames(buffer);
      buffer = rest;
      for (const ev of events) {
        const data = ev.data as Record<string, unknown>;
        switch (ev.name) {
          case 'conversation':
            handlers.onConversation?.(String(data.conversation_id));
            break;
          case 'chunk':
            handlers.onChunk(String(data.text ?? ''));
            break;
          case 'done':
            handlers.onDone?.(data);
            break;
          case 'error':
            handlers.onError?.(
              String(data.code ?? 'internal_error'),
              String(data.message ?? 'حدث خطأ.'),
            );
            break;
          default:
            break; // start / unknown — ignore.
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

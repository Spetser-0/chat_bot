/**
 * lib/streaming.test.ts
 * ─────────────────────
 * Unit tests for the SSE parser + mock-API stream dispatch (Phase 9, Lesson 9.10).
 * No real network — fetch is stubbed.
 */
import { describe, expect, it, vi, afterEach } from 'vitest';
import { parseSseFrames, streamChatCompletion } from './streaming';

describe('parseSseFrames', () => {
  it('parses a single named frame', () => {
    const buffer = 'event: chunk\ndata: {"text":"مرحبا"}\n\n';
    const { events, rest } = parseSseFrames(buffer);
    expect(rest).toBe('');
    expect(events).toHaveLength(1);
    expect(events[0].name).toBe('chunk');
    expect(events[0].data).toEqual({ text: 'مرحبا' });
  });

  it('parses multiple frames and keeps incomplete remainder', () => {
    const buffer =
      'event: conversation\ndata: {"conversation_id":"abc"}\n\n' +
      'event: chunk\ndata: {"text":"أه"}\n\n' +
      'event: chunk\ndata: {"te';
    const { events, rest } = parseSseFrames(buffer);
    expect(events.map((e) => e.name)).toEqual(['conversation', 'chunk']);
    expect(rest).toBe('event: chunk\ndata: {"te');
  });

  it('ignores malformed JSON frames without throwing', () => {
    const buffer = 'event: chunk\ndata: {not-json}\n\n';
    const { events } = parseSseFrames(buffer);
    expect(events).toHaveLength(0);
  });

  it('defaults name to message when event line is missing', () => {
    const buffer = 'data: {"text":"x"}\n\n';
    const { events } = parseSseFrames(buffer);
    expect(events[0].name).toBe('message');
  });

  it('handles \r\n line endings from some proxies', () => {
    const buffer = 'event: done\r\ndata: {"provider_slug":"p"}\r\n\r\n';
    const { events } = parseSseFrames(buffer);
    expect(events).toHaveLength(1);
    expect(events[0].name).toBe('done');
  });
});

describe('streamChatCompletion (mock fetch)', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function sseResponse(chunks: string[]): Response {
    const encoder = new TextEncoder();
    let i = 0;
    const body = new ReadableStream<Uint8Array>({
      pull(controller) {
        if (i < chunks.length) {
          controller.enqueue(encoder.encode(chunks[i++]));
        } else {
          controller.close();
        }
      },
    });
    return new Response(body, {
      status: 200,
      headers: { 'Content-Type': 'text/event-stream' },
    });
  }

  it('dispatches conversation + chunk + done handlers', async () => {
    const frames =
      'event: conversation\ndata: {"conversation_id":"c1"}\n\n' +
      'event: chunk\ndata: {"text":"مر"}\n\n' +
      'event: chunk\ndata: {"text":"حبا"}\n\n' +
      'event: done\ndata: {"provider_slug":"mock","model_name":"m","input_tokens":1,"output_tokens":2,"cost_usd":"0","latency_ms":10}\n\n';

    vi.stubGlobal(
      'fetch',
      vi.fn(async () => sseResponse([frames.slice(0, 40), frames.slice(40)])),
    );

    const onConversation = vi.fn();
    const onChunk = vi.fn();
    const onDone = vi.fn();
    const onError = vi.fn();

    await streamChatCompletion(
      { message: 'hi', conversation_id: null, skill_slug: null },
      { onConversation, onChunk, onDone, onError },
    );

    expect(onConversation).toHaveBeenCalledWith('c1');
    expect(onChunk.mock.calls.map((c) => c[0])).toEqual(['مر', 'حبا']);
    expect(onDone).toHaveBeenCalled();
    expect(onError).not.toHaveBeenCalled();
  });

  it('calls onError on HTTP error envelope', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(
          JSON.stringify({ error: { code: 'insufficient_credits', message: 'الرصيد غير كافٍ' } }),
          { status: 402, headers: { 'Content-Type': 'application/json' } },
        ),
      ),
    );

    const onError = vi.fn();
    const onChunk = vi.fn();
    await streamChatCompletion(
      { message: 'hi' },
      { onChunk, onError },
    );
    expect(onError).toHaveBeenCalledWith('insufficient_credits', 'الرصيد غير كافٍ');
    expect(onChunk).not.toHaveBeenCalled();
  });

  it('sends regenerate flag in the request body', async () => {
    const fetchMock = vi.fn(async () => sseResponse([]));
    vi.stubGlobal('fetch', fetchMock);

    await streamChatCompletion(
      { message: 'hi', conversation_id: 'c1', regenerate: true },
      { onChunk: () => {} },
    );

    const body = JSON.parse((fetchMock.mock.calls[0] as unknown as [RequestInfo, RequestInit])[1]!.body as string);
    expect(body.regenerate).toBe(true);
    expect(body.conversation_id).toBe('c1');
  });
});

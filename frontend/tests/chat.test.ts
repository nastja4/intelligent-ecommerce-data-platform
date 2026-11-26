import assert from 'node:assert/strict';
import { test } from 'node:test';
import { conversationContext, readChatStatus, sendChat } from '../src/chatApi.ts';
import type { ChatMessage } from '../src/chatApi.ts';

test('sends only the last three completed pairs and bounds each message', () => {
  const history: ChatMessage[] = Array.from({ length: 10 }, (_, index) => ({
    role: index % 2 ? 'assistant' : 'user',
    content: String(index).repeat(2001),
  }));
  const context = conversationContext(history);
  assert.equal(context.length, 6);
  assert.deepEqual(context[0], { role: 'user', content: '4'.repeat(2000) });
  assert.equal(history[0].content.length, 2001);
});

test('uses relative chat routes, preserves disabled status, and sanitizes errors', async () => {
  const originalFetch = globalThis.fetch;
  const sent: [string, RequestInit | undefined][] = [];
  globalThis.fetch = async (path, options) => {
    sent.push([String(path), options]);
    if (sent.length === 1) return Response.json({ availability: 'disabled' });
    return Response.json({ detail: 'unexpected private provider detail' }, { status: 502 });
  };
  try {
    assert.equal((await readChatStatus(new AbortController().signal)).availability, 'disabled');
    await assert.rejects(sendChat('Summarize KPIs', []), /^Error: The model provider did not return a usable answer\.$/);
    assert.deepEqual(sent.map(([path]) => path), ['/api/v1/chat/status', '/api/v1/chat']);
    assert.equal(sent[1][1]?.method, 'POST');
    assert.deepEqual(JSON.parse(String(sent[1][1]?.body)), { question: 'Summarize KPIs', history: [] });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

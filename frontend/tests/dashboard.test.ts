import assert from 'node:assert/strict';
import { test } from 'node:test';
import { api, ApiError } from '../src/api.ts';
import { formatAmount, parseBoundedInteger } from '../src/format.ts';

test('formats decimal strings without currency or binary rounding', () => {
  assert.equal(formatAmount('9007199254740993.07'), '9,007,199,254,740,993.07');
  assert.equal(formatAmount('0.00'), '0.00');
  assert.equal(formatAmount(null), '—');
});

test('validates ranking and threshold boundary values', () => {
  assert.equal(parseBoundedInteger('1', 1, 100), 1);
  assert.equal(parseBoundedInteger('100', 1, 100), 100);
  assert.equal(parseBoundedInteger('0', 1, 100), null);
  assert.equal(parseBoundedInteger('101', 1, 100), null);
  assert.equal(parseBoundedInteger('0', 0, 10000), 0);
  assert.equal(parseBoundedInteger('10000', 0, 10000), 10000);
  for (const invalid of ['10001', '', '-1', '2.5', '1e2', 'Infinity']) {
    assert.equal(parseBoundedInteger(invalid, 0, 10000), null);
  }
});

test('uses all six relative GET endpoints and preserves empty results', async context => {
  const paths: string[] = [];
  const signal = new AbortController().signal;
  context.mock.method(globalThis, 'fetch', async (path: string, options: RequestInit) => {
    paths.push(path);
    assert.equal(options.signal, signal);
    assert.equal(options.method ?? 'GET', 'GET');
    return Response.json({ items: [] });
  });
  await api.health(signal);
  await api.kpis(signal);
  await api.categories(signal);
  await api.products(1, signal);
  await api.customers(100, signal);
  assert.deepEqual((await api.inventory(0, signal)).items, []);
  assert.deepEqual(paths, [
    '/health', '/api/v1/kpis', '/api/v1/categories', '/api/v1/products/top?limit=1',
    '/api/v1/customers/top?limit=100', '/api/v1/inventory/low-stock?threshold=0',
  ]);
});

test('distinguishes warehouse errors from proxy and malformed responses', async context => {
  const signal = new AbortController().signal;
  const responses = [
    Response.json({ detail: 'Database path omitted from UI' }, { status: 503 }),
    new Response('Proxy failed', { status: 500 }),
    new Response('<html>Vite fallback</html>', { headers: { 'content-type': 'text/html' } }),
  ];
  context.mock.method(globalThis, 'fetch', async () => responses.shift());
  for (const kind of ['warehouse', 'connection', 'response']) {
    await assert.rejects(api.health(signal), error => error instanceof ApiError && error.kind === kind);
  }
});

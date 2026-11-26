import assert from 'node:assert/strict';
import { test } from 'node:test';
import { dashboardPage, navigation, watchDashboardHash } from '../src/navigation.ts';

test('each supported hash resolves its matching page on direct load', () => {
  assert.equal(navigation.length, 6);
  for (const page of navigation) {
    assert.equal(dashboardPage(`#${page.target}`), page);
  }
  assert.equal(dashboardPage('#assistant').title, 'AI Assistant');
});

test('empty, unknown and malformed fragments fall back to Overview', () => {
  for (const hash of ['', '#', '#wrong', '#main-content', '#%zz', '#Assistant']) {
    assert.equal(dashboardPage(hash).target, 'overview');
  }
});

test('hash changes re-read the browser location and stop on unsubscribe', () => {
  const source = new EventTarget();
  let hash = '#products';
  const pages: string[] = [];
  const unsubscribe = watchDashboardHash(source, () => pages.push(dashboardPage(hash).target));
  for (const next of ['#assistant', '#products', '#assistant']) {
    hash = next;
    source.dispatchEvent(new Event('hashchange'));
  }
  unsubscribe();
  source.dispatchEvent(new Event('hashchange'));
  assert.deepEqual(pages, ['assistant', 'products', 'assistant']);
});

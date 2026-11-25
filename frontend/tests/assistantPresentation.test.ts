import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import Markdown from 'react-markdown';
import { assistantMarkdown, displayBudget, displayCost, displayModel } from '../src/assistantPresentation.ts';

test('renders assistant Markdown while suppressing HTML, links, and external images', () => {
  const text = [
    '## Snapshot', '', '**Gross cart value**', '', '- Sample item', '',
    '| Metric | Value |', '| --- | --- |', '| Carts | 3 |', '',
    '`sample`', '', '```', 'code block', '```', '',
    '<script>alert(1)</script>', '', '<img src="https://example.test/raw.png">', '',
    '[unsafe](javascript:alert%281%29) [external](https://example.test) ![remote](https://example.test/img.png)',
  ].join('\n');
  const html = renderToStaticMarkup(createElement(Markdown, assistantMarkdown, text));
  for (const tag of ['h2', 'strong', 'li', 'table', 'code', 'pre']) {
    assert.ok(html.includes(`<${tag}>`), tag);
  }
  assert.match(html, /unsafe external/);
  assert.doesNotMatch(html, /<a\b|<script\b|<img\b|href=|src=/);
});

test('labels the model and keeps sub-cent estimates visible', () => {
  assert.equal(displayModel('claude-haiku-5-5'), 'Claude Haiku 5.5');
  assert.equal(displayBudget('1.9984801'), 'USD 2.00');
  assert.equal(displayCost('0.001519900'), 'USD 0.0015199');
  assert.equal(displayCost('0.000000001'), 'USD 0.000000001');
});

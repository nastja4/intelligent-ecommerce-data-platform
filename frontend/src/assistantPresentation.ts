import type { Options } from 'react-markdown';
import { createElement } from 'react';
import remarkGfm from 'remark-gfm';

export const assistantMarkdown: Options = {
  remarkPlugins: [remarkGfm],
  skipHtml: true,
  disallowedElements: ['a', 'img'],
  unwrapDisallowed: true,
  components: {
    table: ({ node: _node, ...props }) => createElement(
      'div', { className: 'assistant-table', role: 'region', 'aria-label': 'Analytical table', tabIndex: 0 },
      createElement('table', props),
    ),
  },
};

const budgetFormat = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const costFormat = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 9 });

export const displayBudget = (amount: string) => `USD ${budgetFormat.format(Number(amount))}`;
export const displayCost = (amount: string) => `USD ${costFormat.format(Number(amount))}`;
export const displayModel = (model: string) => model === 'claude-haiku-5-5' ? 'Claude Haiku 5.5' : model;

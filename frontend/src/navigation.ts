export const navigation = [
  { target: 'overview', symbol: '▦', label: 'Overview', title: 'Business overview' },
  { target: 'categories', symbol: '▤', label: 'Categories', title: 'Category analytics' },
  { target: 'products', symbol: '◇', label: 'Products', title: 'Product analytics' },
  { target: 'customers', symbol: '◉', label: 'Customers', title: 'Customer analytics' },
  { target: 'inventory', symbol: '▥', label: 'Inventory', title: 'Inventory alerts' },
  { target: 'assistant', symbol: '✦', label: 'AI Assistant', title: 'AI Assistant' },
] as const;

export function dashboardPage(hash: string): (typeof navigation)[number] {
  return navigation.find(page => `#${page.target}` === hash) ?? navigation[0];
}

export function watchDashboardHash(source: EventTarget, onChange: () => void): () => void {
  source.addEventListener('hashchange', onChange);
  return () => source.removeEventListener('hashchange', onChange);
}

import type { BusinessKpis } from '../contracts';
import { formatAmount, formatCount } from '../format';
import type { Resource } from '../useResource';

export function Metrics({ resource }: { resource: Resource<BusinessKpis> }) {
  const data = resource.status === 'ready' ? resource.data : null;
  const cards = [
    { title: 'Gross cart value', icon: '∑', accent: 'mint', value: data && formatAmount(data.total_gross_cart_value), caption: 'Before discounts' },
    { title: 'Cart count', icon: '▣', accent: 'blue', value: data && formatCount(data.cart_count), caption: 'Includes empty carts' },
    { title: 'Average cart value', icon: '≈', accent: 'violet', value: data && formatAmount(data.average_cart_value),
      caption: data?.average_cart_value === null ? 'No carts in snapshot' : 'Gross value per cart' },
    { title: 'Total item quantity', icon: '▦', accent: 'sand', value: data && formatCount(data.total_quantity), caption: 'Units across all cart lines' },
  ];

  return (
    <>
      <div className="metric-grid" aria-busy={resource.status === 'loading'}>
        {cards.map(card => <article className="metric-card" key={card.title}>
          <span className={`metric-icon ${card.accent}`} aria-hidden="true">{card.icon}</span>
          <h3>{card.title}</h3>
          <div className="metric-value">{card.value ?? '—'}</div>
          <p>{card.caption}</p>
        </article>)}
      </div>
      {resource.status === 'loading' && <p className="sr-only" role="status">Loading business overview…</p>}
      {resource.status === 'error' && <p className="overview-error error-message" role="status">{resource.error.message}</p>}
    </>
  );
}

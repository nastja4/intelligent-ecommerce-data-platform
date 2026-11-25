import type { CategoryPerformance } from '../contracts';
import { categoryLabel, formatAmount, formatCount } from '../format';

const compact = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 2 });

export function CategoryChart({ categories }: { categories: CategoryPerformance[] }) {
  if (!categories.length) return <p className="panel-message">No categories with cart activity in this snapshot.</p>;
  const largest = Math.max(1, ...categories.map(row => Number(row.gross_cart_value)));
  const magnitude = 10 ** Math.floor(Math.log10(largest));
  const scale = Math.ceil(largest / magnitude) * magnitude;

  return (
    <figure className="bar-chart">
      <figcaption><span aria-hidden="true" className="legend-swatch" /> Gross simulated cart value by category</figcaption>
      <div className="chart-body">
        <ul className="chart-bars">
          {categories.map(row => {
            const label = categoryLabel(row.category);
            const description = `${label}: ${formatAmount(row.gross_cart_value)} gross cart value, ${formatCount(row.total_quantity)} items`;
            return <li className="chart-row" key={row.category} title={description}>
              <div className="chart-category">
                <span className="chart-label">{label}</span>
                <small>{formatCount(row.total_quantity)} items</small>
              </div>
              <div className="bar-track" aria-hidden="true">
                <span className="bar" style={{ width: `${100 * Number(row.gross_cart_value) / scale}%` }} />
              </div>
              <span className="chart-value">{formatAmount(row.gross_cart_value)}
                <span className="sr-only"> gross cart value</span>
              </span>
            </li>;
          })}
        </ul>
      </div>
      <div className="chart-axis" aria-hidden="true">
        <span />
        <div>{[0, .25, .5, .75, 1].map(fraction => <span key={fraction}>{compact.format(scale * fraction)}</span>)}</div>
        <span />
      </div>
    </figure>
  );
}

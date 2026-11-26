import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react';
import type { ReactNode } from 'react';
import { api } from './api';
import { rankingBounds, stockBounds, swaggerPath } from './config';
import { categoryLabel, formatAmount, formatCount, formatSnapshot } from './format';
import { useResource } from './useResource';
import { CategoryChart } from './components/CategoryChart';
import { DataTable } from './components/DataTable';
import { Metrics } from './components/Metrics';
import { NumberFilter } from './components/NumberFilter';
import { ResultState } from './components/ResultState';
import { Assistant } from './components/Assistant';
import { dashboardPage, navigation, watchDashboardHash } from './navigation';

const subscribe = (onChange: () => void) => watchDashboardHash(window, onChange);
const readHash = () => window.location.hash;

function Panel({ id, title, description, action, children }: {
  id: string; title: string; description: string; action?: ReactNode; children: ReactNode;
}) {
  return <section id={id} className="panel" aria-labelledby={`${id}-title`}>
    <div className="panel-heading">
      <div>
        <h2 id={`${id}-title`}>{title}</h2>
        <p>{description}</p>
      </div>
      {action}
    </div>
    {children}
  </section>;
}

export function App() {
  const [revision, reload] = useState(0);
  const page = dashboardPage(useSyncExternalStore(subscribe, readHash));
  const active = page.target;
  const [assistantOpened, openAssistant] = useState(false);
  const showingAssistant = active === 'assistant';
  const overview = active === 'overview';
  const content = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (showingAssistant) openAssistant(true);
    if (content.current) content.current.scrollTop = 0;
  }, [active, showingAssistant]);
  const [productLimit, setProductLimit] = useState(rankingBounds.initial);
  const [customerLimit, setCustomerLimit] = useState(rankingBounds.initial);
  const [threshold, setThreshold] = useState(stockBounds.initial);
  const health = useResource(api.health, revision);
  const kpis = useResource(api.kpis, revision);
  const categories = useResource(api.categories, revision);
  const products = useResource(useCallback(signal => api.products(productLimit, signal), [productLimit]), revision);
  const customers = useResource(useCallback(signal => api.customers(customerLimit, signal), [customerLimit]), revision);
  const inventory = useResource(useCallback(signal => api.inventory(threshold, signal), [threshold]), revision);
  const timestamp = kpis.status === 'ready' ? kpis.data.snapshot_at : undefined;
  const snapshotLabel = kpis.status === 'loading' ? 'Loading…'
    : kpis.status === 'error' && kpis.error.kind !== 'warehouse' ? 'Could not load'
    : timestamp && !Number.isFinite(Date.parse(timestamp)) ? 'Invalid timestamp'
    : 'Unavailable';
  const statusText = health.status === 'loading' ? 'Checking connection' :
    health.status === 'ready' ? 'API connected · Warehouse ready' :
    health.error.kind === 'warehouse' ? 'API connected · Warehouse unavailable' :
    health.error.kind === 'connection' ? 'API disconnected' : 'API check failed';

  return <div className="shell">
    <a className="skip-link" href="#main-content" onClick={event => {
      event.preventDefault();
      content.current?.focus();
    }}>Skip to dashboard</a>
    <aside className="sidebar">
      <a className="brand" href="#overview">
        <img className="brand-mark" src="/favicon.svg" alt="" width={35} height={35} />
        <span>Commerce <strong>Intelligence</strong></span>
      </a>
      <nav aria-label="Dashboard sections">
        {navigation.map(item => <a key={item.target} href={`#${item.target}`}
          aria-current={active === item.target ? 'page' : undefined}>
          <span className="nav-symbol" aria-hidden="true">{item.symbol}</span>{item.label}
        </a>)}
      </nav>
      <a className="docs-link" href={swaggerPath} target="_blank" rel="noreferrer">
        <span aria-hidden="true">↗</span> Swagger documentation
      </a>
    </aside>

    <div className="workspace">
      <header className="topbar">
        <span className="workspace-label">Business analytics</span>
        <span className={`connection ${health.status}`} role="status">
          <span aria-hidden="true" />{statusText}
        </span>
      </header>
      <main className="dashboard" aria-labelledby="overview-title">
        <header className="page-header">
          <div className="page-header-inner">
            <div className="overview-heading">
              <h1 id="overview-title">{page.title}</h1>
              <button className="button reload" type="button" onClick={() => reload(value => value + 1)}>
                <span aria-hidden="true">↻</span> Reload dashboard
              </button>
            </div>
            <p className="overview-description">{showingAssistant
              ? 'Ask about simulated cart activity and inventory. Questions and relevant analytical results are sent to Anthropic.'
              : 'Explore simulated cart activity and inventory in the current validated snapshot.'}</p>
            <div className="snapshot" aria-live="polite">
              <span className="snapshot-dot" aria-hidden="true" />
              <span>Snapshot</span>
              {timestamp && Number.isFinite(Date.parse(timestamp))
                ? <time dateTime={timestamp}>{formatSnapshot(timestamp)}</time>
                : <span>{snapshotLabel}</span>}
            </div>
          </div>
        </header>
        <div id="main-content" ref={content} className="dashboard-scroll" role="region"
          aria-label={showingAssistant ? 'AI Assistant' : 'Dashboard analytics'} tabIndex={0}>
          {(showingAssistant || assistantOpened) && <section id="assistant" className="dashboard-content assistant-content" hidden={!showingAssistant}>
            <Assistant />
          </section>}
          {!showingAssistant && <div className="dashboard-content">
            {overview && <section id="overview" className="overview" aria-label="Overview metrics">
              <Metrics resource={kpis} />
            </section>}

            {(overview || active === 'categories' || active === 'inventory') && <div className={overview ? 'analysis-grid' : undefined}>
              {(overview || active === 'categories') && <Panel id="categories" title="Category performance" description="Gross simulated cart value by catalog category">
                <ResultState resource={categories} title="categories">
                  {data => <CategoryChart categories={data.items} />}
                </ResultState>
              </Panel>}
              {(overview || active === 'inventory') && <Panel id="inventory" title="Low-stock inventory" description={`Products with stock below ${formatCount(threshold)}`}
                action={<NumberFilter label="Stock threshold" bounds={stockBounds} onApply={setThreshold} />}>
                <ResultState resource={inventory} title="inventory">
                  {data => <DataTable label="Low-stock inventory" rows={data.items} rowKey={row => row.product_id}
                    empty="No products are below this threshold." columns={[
                      { label: 'Product', render: row => <>{row.title}<small>#{row.product_id}</small></> },
                      { label: 'Stock', numeric: true, render: row => <span className="stock-count">{formatCount(row.stock)}</span> },
                    ]} />}
                </ResultState>
              </Panel>}
            </div>}

            {(overview || active === 'products' || active === 'customers') && <div className={overview ? 'rankings-grid' : undefined}>
              {(overview || active === 'products') && <Panel id="products" title="Top products" description={`Up to ${productLimit} products ranked by gross cart value`}
                action={<NumberFilter label="Product limit" bounds={rankingBounds} onApply={setProductLimit} />}>
                <ResultState resource={products} title="products">
                  {data => <DataTable label="Top products" rows={data.items} rowKey={row => row.product_id}
                    empty="No products with cart activity in this snapshot." columns={[
                      { label: 'Product', render: row => <>{row.title}<small>{categoryLabel(row.category)}</small></> },
                      { label: 'Gross value', numeric: true, render: row => formatAmount(row.gross_cart_value) },
                      { label: 'Items', numeric: true, render: row => formatCount(row.total_quantity) },
                    ]} />}
                </ResultState>
              </Panel>}
              {(overview || active === 'customers') && <Panel id="customers" title="Top customers" description={`Up to ${customerLimit} customer IDs ranked by gross cart value`}
                action={<NumberFilter label="Customer limit" bounds={rankingBounds} onApply={setCustomerLimit} />}>
                <ResultState resource={customers} title="customers">
                  {data => <DataTable label="Top customers" rows={data.items} rowKey={row => row.customer_id}
                    empty="No customers with carts in this snapshot." columns={[
                      { label: 'Customer ID', render: row => <span className="identifier">#{row.customer_id}</span> },
                      { label: 'Gross value', numeric: true, render: row => formatAmount(row.gross_cart_value) },
                      { label: 'Carts', numeric: true, render: row => formatCount(row.cart_count) },
                    ]} />}
                </ResultState>
              </Panel>}
            </div>}
          </div>}
        </div>
      </main>
    </div>
  </div>;
}

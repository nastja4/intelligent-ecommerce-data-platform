# Data model and metric definitions

The warehouse represents one validated DummyJSON snapshot. The fixture counts below come from the synthetic dataset in [tests/fixtures](../tests/fixtures).

| Layer and relation | Grain | Fixture rows |
| --- | --- | ---: |
| `bronze.raw_products` | One raw source record per product ID | 4 |
| `bronze.raw_users` | One raw source record per user ID | 3 |
| `bronze.raw_carts` | One raw source record per cart ID | 3 |
| `silver.stg_products` | One product ID with typed title, category, price, and stock | 4 |
| `silver.stg_users` | One user ID with an ingestion timestamp | 3 |
| `silver.stg_carts` | One cart ID with its owner ID, source totals, and ordered item array | 3 |
| `silver.stg_cart_items` | One cart ID and zero-based source array ordinal, with product ID, unit price, and quantity | 3 |
| `gold.cart_summary` | One cart ID, including empty carts | 3 |
| `gold.product_performance` | One product ID with cart activity | 2 |
| `gold.category_performance` | One catalog category with cart activity | 2 |
| `gold.customer_performance` | One customer ID with carts | 2 |
| `gold.inventory_alerts` | One catalog product ID, regardless of cart activity | 4 |
| `gold.business_kpis` | Exactly one snapshot row | 1 |

## Lineage and validation

Bronze stores a primary key, full JSON payload, and UTC ingestion timestamp. One transaction replaces all three collections. Identical duplicates collapse by source ID, and conflicting payloads fail the load. Raw customer attributes stay in Bronze.

dbt reads Bronze with `source()` and links downstream models with `ref()`. Silver views extract and type required fields. DuckDB's lateral `json_each` uses the JSON array key to preserve source position. A repeated product on two lines remains two rows. Cart-to-user and item-to-cart/product relationships preserve the referenced keys. Invalid required fields become null and fail data tests. Empty carts stay in the cart view and have zero item rows.

Gold tables aggregate cart items before attaching cart or catalog attributes to avoid multiplying values through joins. Category performance rolls up product performance. Customer performance and KPIs roll up cart summaries. The inventory table reads the catalog independently of cart activity. Data tests validate uniqueness, non-null keys and required fields, references, non-negative measures, the item grain, and reconciliation of gross values, applicable quantities, and cart counts.

The validated refresh publishes the candidate only after `dbt build` and all expected relation checks succeed. An extraction, load, test, or replacement failure leaves the previous snapshot in place. Close readers and writers before promotion.

## Metrics

| Metric | Computation or ordering |
| --- | --- |
| Gross simulated cart value | Sum cart-line unit price × quantity before discounts. Source-reported cart totals remain available for inspection in Silver. |
| Cart count | Count carts in the snapshot, including empty carts. |
| Average cart value | Total gross value divided by cart count. Exact decimal division rounds to two places with ties to even. The average is null when there are zero carts. |
| Total item quantity | Sum line quantities. Empty carts contribute zero value and quantity. |
| Product and customer rankings | Descending gross value, then ascending product or customer ID. Customer results contain source ID, cart count, and gross value. |
| Category performance | Gross value and quantity rolled up by catalog category, sorted by descending value then category. |
| Low stock | Stock strictly below the supplied threshold, ordered by stock then product ID. |
| Snapshot time | Latest ingestion instant across source collections. A wholly empty snapshot uses the Gold build time, zero totals, and a null average. |

The fixture totals are `20.00` gross value, 3 carts, `6.67` average, and 3 items. Monetary outputs are decimal strings with two places and no currency label. The values describe synthetic cart activity.

Generate the dbt catalog and lineage against a disposable warehouse after a fixture refresh.

```powershell
$py = (Resolve-Path .\.venv\Scripts\python.exe).Path
$dbt = (Resolve-Path .\.venv\Scripts\dbt.exe).Path
$env:WAREHOUSE_PATH = Join-Path (Get-Location).Path 'data/model-docs.duckdb'
& $py -m ecommerce.refresh --fixture-dir tests/fixtures
if ($LASTEXITCODE) { throw 'Fixture refresh failed' }
& $dbt docs generate --project-dir analytics --profiles-dir analytics
```

The generated catalog and manifest are in `analytics/target`. The [Silver YAML](../analytics/models/staging/_silver.yml) and [Gold YAML](../analytics/models/marts/_gold.yml) document columns and tests.

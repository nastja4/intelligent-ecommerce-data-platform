# Intelligent E-Commerce Data Platform

This portfolio project will load synthetic DummyJSON data into DuckDB, transform and validate it with dbt, and expose cart analytics through FastAPI and MCP. Cart values represent simulated activity.

The current pipeline loads products, users, and carts into DuckDB Bronze, builds the Silver views and Gold tables with dbt, and publishes the warehouse after validation. [PLAN.md](PLAN.md) describes the remaining work, and [SPEC.md](SPEC.md) defines the project requirements.

## Development setup

From the repository root in PowerShell, use Python 3.12. Create the virtual environment only if it is missing.

```powershell
if (-not (Test-Path .\.venv\Scripts\python.exe)) { py -3.12 -m venv .venv }
$python = '.\.venv\Scripts\python.exe'
& $python -m pip install --require-hashes --only-binary=:all: -r requirements.lock
& $python -m pip install --no-deps -e .
& $python -m pip check
& .\.venv\Scripts\dbt.exe --version
```

`pyproject.toml` declares runtime dependencies and a `test` extra for pytest. `requirements.lock` pins the combined development environment, including transitive dependencies and artifact hashes. Regenerate it with uv 0.13.9 using the command in its header, then verify it on Windows and Linux.

The lock has been installed and smoke-tested on Windows x86-64 with Python 3.12. The Linux x86-64 wheel set resolved and installed into an isolated target on Windows. Running the import and dbt checks on a Linux host is still pending.

## Bronze ingestion

Run the fixture refresh twice from the repository root to check repeatability. Use a fresh warehouse under the ignored `data` directory.

```powershell
$py = (Resolve-Path .\.venv\Scripts\python.exe).Path
$runDir = Join-Path (Get-Location).Path ("data/bronze-check-" + [guid]::NewGuid())
$env:WAREHOUSE_PATH = Join-Path $runDir 'warehouse.duckdb'
& $py -m ecommerce.load --fixture-dir tests/fixtures
& $py -m ecommerce.load --fixture-dir tests/fixtures
& $py -m pytest -q tests/test_extract.py tests/test_load.py
```

Each refresh prints `{"products": 4, "users": 3, "carts": 3}`. The CLI creates the parent directory as needed. Verify counts and unique source IDs with a read-only connection.

```powershell
@'
import os
import duckdb

with duckdb.connect(os.environ["WAREHOUSE_PATH"], read_only=True) as connection:
    for table, expected in (("raw_products", 4), ("raw_users", 3), ("raw_carts", 3)):
        counts = connection.execute(
            f"SELECT count(*), count(DISTINCT source_id) FROM bronze.{table}"
        ).fetchone()
        assert counts == (expected, expected), (table, counts)
        print(f"{table}: {counts[0]} rows")
'@ | & $py -
```

For a separate live run, use a different warehouse in the same directory. Live data includes full synthetic source user objects. Keep the warehouse local.

```powershell
$env:WAREHOUSE_PATH = Join-Path $runDir 'live.duckdb'
& $py -m ecommerce.load --live
```

If pytest reports `WinError 5` for its default temporary directory or `.pytest_cache`, use a fresh project-local directory and disable the cache provider for that run.

```powershell
$testTmp = Join-Path (Resolve-Path .\.venv).Path ("pytest-" + [guid]::NewGuid())
& $py -m pytest -q --basetemp $testTmp -p no:cacheprovider
```

| Environment variable | Default | Behavior |
| --- | --- | --- |
| `WAREHOUSE_PATH` | `data/warehouse.duckdb` | Relative paths resolve from the current directory. Use a Phase 1 warehouse and close other DuckDB connections before running the CLI. |
| `DUMMYJSON_TIMEOUT_SECONDS` | `10` | Positive HTTP timeout in seconds. |
| `DUMMYJSON_PAGE_SIZE` | `50` | Live request limit from 1 to 100. |
| `DUMMYJSON_MAX_RETRIES` | `2` | Additional attempts per live page, from 0 to 5, with bounded exponential backoff. |

Fixture files contain arrays of recorded response pages with `total`, `skip`, `limit` and the corresponding collection. Both modes validate page metadata and record IDs. Live requests advance `skip` by the number of rows returned and retry transient transport errors, HTTP 429, and HTTP 5xx. The loader stages all three collections, collapses identical payloads by ID, and rejects conflicting payloads before writing.

Each table stores `source_id`, the complete JSON `payload`, and an `ingested_at` UTC instant. One transaction replaces all three sets of rows, removing IDs absent from the new snapshot. A failed insert rolls the transaction back. A rerun preserves the logical rows and records the new ingestion time. Use the Bronze-only command for disposable warehouses and the validated refresh below for the active warehouse.

## Validated warehouse refresh

Run from the repository root in PowerShell. **Stop all DuckDB readers and writers before replacement**, including interactive DuckDB sessions, application processes, and any containers sharing the warehouse. Run one refresh at a time.

```powershell
$py = (Resolve-Path .\.venv\Scripts\python.exe).Path
$env:WAREHOUSE_PATH = Join-Path (Get-Location).Path 'data/warehouse.duckdb'
& $py -m ecommerce.refresh --fixture-dir tests/fixtures

# Run the live smoke test against its own warehouse.
$env:WAREHOUSE_PATH = Join-Path (Get-Location).Path 'data/live-smoke.duckdb'
& $py -m ecommerce.refresh --live
```

The command loads a sibling candidate file, closes the Bronze writer, and runs `dbt build` in a subprocess using the same Python interpreter. Only the subprocess receives the candidate as `WAREHOUSE_PATH`. When dbt succeeds, the refresh checks the names and types of the expected Bronze, Silver, and Gold relations, closes the verification connection, and replaces the destination file with `os.replace`. An existing WAL blocks replacement so the warehouse can be recovered first.

Exit code `0` means publication succeeded, `1` means the refresh failed, and `2` indicates invalid command arguments. A failed refresh leaves the prior warehouse intact and cleans up its candidate and sidecars. Output includes candidate row counts and, if dbt validation fails, failed dbt node names and counts without source payloads or raw dbt errors. Use the disposable fixture build below to generate dbt documentation.

## Silver staging

Load a fresh fixture warehouse and run dbt against the same absolute `WAREHOUSE_PATH`. Run these commands from the repository root in PowerShell.

```powershell
$py = (Resolve-Path .\.venv\Scripts\python.exe).Path
$dbt = (Resolve-Path .\.venv\Scripts\dbt.exe).Path
$runDir = Join-Path (Get-Location).Path ("data/silver-check-" + [guid]::NewGuid())
$env:WAREHOUSE_PATH = Join-Path $runDir 'warehouse.duckdb'
& $py -m ecommerce.load --fixture-dir tests/fixtures
& $dbt build --project-dir analytics --profiles-dir analytics
```

The dbt profile selects DuckDB, and the project materializes staging models as views in `silver` and marts as tables in `gold`. Source declarations point to the three tables in `bronze`. The schema naming macro preserves the exact layer names.

| Silver view | Grain and fields |
| --- | --- |
| `stg_products` | One row per product. Projects title, category, catalog price, and stock. |
| `stg_users` | One row per user. Projects the ID and ingestion timestamp only. |
| `stg_carts` | One row per cart. Projects the owner ID, source totals, and ordered item array. Keeps empty carts. |
| `stg_cart_items` | One row per cart ID and zero-based source array ordinal. Projects product ID, cart-line unit price, and whole-number quantity. |

`json_each` expands each cart's item array. Its key is the item position, so repeated product IDs in one cart remain separate lines. Missing fields and invalid JSON types become null and fail required-field tests. A malformed item array fails on its parent cart. The dbt tests also check source-key uniqueness, foreign keys, non-negative values, and the composite cart-item grain.

Inspect the catalog and item rows after the dbt process exits.

```powershell
@'
import os
import duckdb

with duckdb.connect(os.environ["WAREHOUSE_PATH"], read_only=True) as con:
    print(con.execute("""
        SELECT table_schema, table_name, table_type
        FROM information_schema.tables
        WHERE table_schema IN ('bronze', 'silver')
        ORDER BY table_schema, table_name
    """).fetchall())
    print(con.execute("""
        SELECT cart_id, item_ordinal, product_id, unit_price, quantity
        FROM silver.stg_cart_items
        ORDER BY cart_id, item_ordinal
    """).fetchall())
'@ | & $py -
```

The fixture has 4 products, 3 users, 3 carts, and 3 cart items. Cart 201 has two lines for product 101 at ordinals 0 and 1. Cart 203 remains in `stg_carts` with zero item rows.

## Gold business analytics

The fixture build above also produces six Gold tables.

| Table | Grain and calculation | Fixture rows |
| --- | --- | ---: |
| `cart_summary` | One row per cart. Sums gross line value and quantity, with zeroes for empty carts. | 3 |
| `product_performance` | One row per product with cart activity. Sums gross line value and quantity and attaches the catalog title and category. | 2 |
| `category_performance` | One row per category with cart activity. Rolls up product value and quantity. | 2 |
| `customer_performance` | One row per customer with carts. Returns only the customer ID, gross cart value, and cart count. | 2 |
| `inventory_alerts` | One row per catalog product, including products without cart activity. Carries stock unchanged for consumer-side threshold filtering. | 4 |
| `business_kpis` | One snapshot row. Aggregates the cart summaries and records the snapshot timestamp. | 1 |

Gross simulated cart value is the sum of the cart-line unit price times quantity before discounts. These amounts describe synthetic cart activity. Money remains decimal with two places, and average cart value uses exact decimal division with ties rounded to even. Fixture KPIs are gross value **20.00**, cart count **3**, average cart value **6.67**, and total item quantity **3**. A snapshot with no carts still returns one KPI row with zero totals and a null average. An empty cart counts and contributes zero. The snapshot timestamp is the latest ingestion instant across the source collections, with Gold build time used when all three are empty.

After running the fixture build above, generate the dbt catalog and lineage and run the full Python suite.

```powershell
& $dbt docs generate --project-dir analytics --profiles-dir analytics
$testTmp = Join-Path (Resolve-Path .\.venv).Path ("pytest-" + [guid]::NewGuid())
& $py -m pytest -q --basetemp $testTmp -p no:cacheprovider
```

dbt writes the documentation and lineage artifacts under `analytics/target`. Its reconciliation test compares gross value across carts, products, categories, customers and KPIs, plus applicable quantity totals and cart counts. The Python integration tests check hand-calculated values, including empty carts and a wholly empty snapshot.

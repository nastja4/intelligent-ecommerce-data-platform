# Intelligent E-Commerce Data Platform

This portfolio project will load synthetic DummyJSON data into DuckDB, transform and validate it with dbt, and expose cart analytics through FastAPI and MCP. Cart values represent simulated activity.

Phase 1 loads products, users, and carts into DuckDB Bronze. The first increment of Phase 2 builds and tests the Silver staging views. [PLAN.md](PLAN.md) describes the remaining work, and [SPEC.md](SPEC.md) defines the project requirements.

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

Each table stores `source_id`, the complete JSON `payload`, and an `ingested_at` UTC instant. One transaction replaces all three sets of rows, removing IDs absent from the new snapshot. A failed insert rolls the transaction back. A rerun preserves the logical rows and records the new ingestion time. The Bronze-only CLI works directly on the selected warehouse. The validated candidate publication workflow belongs to Phase 2.

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

The dbt profile selects DuckDB, and the project materializes staging models as views in `silver`. Source declarations point to the three tables in `bronze`. The schema naming macro lets future Gold models use the exact `gold` schema name.

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

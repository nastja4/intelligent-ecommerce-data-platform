# Intelligent E-Commerce Data Platform

This portfolio project will load synthetic DummyJSON data into DuckDB, transform and validate it with dbt, and expose cart analytics through FastAPI and MCP. Cart values represent simulated activity.

Phase 1 loads products, users, and carts into DuckDB Bronze. dbt transformations and serving interfaces are planned in [PLAN.md](PLAN.md). [SPEC.md](SPEC.md) defines the project requirements.

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

| Environment variable | Default | Behavior |
| --- | --- | --- |
| `WAREHOUSE_PATH` | `data/warehouse.duckdb` | Relative paths resolve from the current directory. Use a Phase 1 warehouse and close other DuckDB connections before running the CLI. |
| `DUMMYJSON_TIMEOUT_SECONDS` | `10` | Positive HTTP timeout in seconds. |
| `DUMMYJSON_PAGE_SIZE` | `50` | Live request limit from 1 to 100. |
| `DUMMYJSON_MAX_RETRIES` | `2` | Additional attempts per live page, from 0 to 5, with bounded exponential backoff. |

Fixture files contain arrays of recorded response pages with `total`, `skip`, `limit` and the corresponding collection. Both modes validate page metadata and record IDs. Live requests advance `skip` by the number of rows returned and retry transient transport errors, HTTP 429, and HTTP 5xx. The loader stages all three collections, collapses identical payloads by ID, and rejects conflicting payloads before writing.

Each table stores `source_id`, the complete JSON `payload`, and an `ingested_at` UTC instant. One transaction replaces all three sets of rows, removing IDs absent from the new snapshot. A failed insert rolls the transaction back. A rerun preserves the logical rows and records the new ingestion time. The Bronze-only CLI works directly on the selected warehouse. The validated candidate publication workflow belongs to Phase 2.

# Implementation progress

**25 November 2026 · Phases 0–3 implemented on Windows**

[SPEC.md](SPEC.md) defines acceptance criteria. [PLAN.md](PLAN.md) defines the implementation sequence.

| Phase | Status and evidence |
| --- | --- |
| 0 · Baseline | Python 3.12 package, existing `.venv`, and hash-pinned dependency lock are in place. Windows installation and dbt connectivity passed. Linux wheel resolution passed, and Linux runtime verification remains open. |
| 1 · Extract and load | Paginated DummyJSON and fixture ingestion, transactional Bronze full refresh, deduplication, and rollback verified. |
| 2 · Transform, validate, and publish | Four Silver views and six Gold tables verified. dbt reported 93 passes, including 83 data tests, with zero warnings, errors, or skips. Fixture and live ELT refreshes published successfully. Failure preservation and Windows reader locking were verified. |
| 3 · Shared queries, REST, and MCP | All 66 Python tests passed. Loopback HTTP and actual MCP stdio smoke tests passed. REST and MCP returned matching fixture results. |
| 4 · Docker and GitHub Actions | Pending. Docker installation is awaiting a Windows restart. |
| 5 · Claude demo and reproduction | Pending. Claude Code is installed. The authenticated demo, final documentation, and clean-checkout reproduction remain open. |

## Verification evidence

- The live DummyJSON refresh published 194 products, 208 users, and 208 carts. The snapshot at `2026-11-25T13:19:40.839163Z` reported gross simulated cart value `3834278.63`, average cart value `18434.03`, and total item quantity `2417`.
- REST returned 200 from `/health`, `/api/v1/kpis`, `/api/v1/products/top`, `/api/v1/categories`, `/api/v1/customers/top`, and `/api/v1/inventory/low-stock`. Swagger and OpenAPI loaded, and an invalid limit returned 422.
- The official MCP SDK 2.3.0 initialized a stdio session and discovered and called `get_business_kpis`, `get_top_products`, `get_category_performance`, `get_top_customers`, and `get_low_stock_products`. All five returned structured results matching REST. Invalid arguments and the unsupported SQL tool were rejected.

## Acceptance criteria still open

AC-01 through AC-07 have local verification evidence.

| Criterion | Remaining evidence |
| --- | --- |
| AC-08 · Claude Code | Capture an authenticated session showing discovery, actual tool calls, answers grounded in fixture data, and handling of an unsupported metric. |
| AC-09 · Automated tests | Local Windows verification is complete with 66 Python tests and 83 dbt data tests. Repeat the fixture-backed checks in the planned Windows and Linux CI jobs. |
| AC-10 · Docker | Build and run the Linux image, verify HTTP health and fixture KPIs, and recreate the container using the same warehouse volume. |
| AC-11 · GHCR | Obtain explicit owner approval for repository visibility, GHCR namespace, package visibility, and publication. Obtain separate push authorization. Then verify the main-branch workflow, SHA-tagged image, and digest. |
| AC-12 · Reproduction | Finish the English documentation and have another developer follow the README from a clean Windows checkout. |

## Windows test workaround

Use a unique project-local pytest temporary directory and disable the cache provider if the default temp directory or `.pytest_cache` triggers `WinError 5`. Leave Windows system permissions in place.

```powershell
$py = (Resolve-Path .\.venv\Scripts\python.exe).Path
$testTmp = Join-Path (Resolve-Path .\.venv).Path ("pytest-" + [guid]::NewGuid())
& $py -m pytest -q --basetemp $testTmp -p no:cacheprovider
```

## Claude Code registration

Run from the repository root in PowerShell using the existing Claude subscription. Use a dedicated fixture warehouse and local registration scope for this project.

```powershell
$py = (Resolve-Path .\.venv\Scripts\python.exe).Path
$env:WAREHOUSE_PATH = Join-Path (Get-Location).Path 'data/claude-demo.duckdb'
& $py -m ecommerce.refresh --fixture-dir tests/fixtures
if ($LASTEXITCODE) { throw 'Fixture refresh failed' }

claude auth status
claude mcp add --env "WAREHOUSE_PATH=$env:WAREHOUSE_PATH" --transport stdio --scope local ecommerce -- "$py" -m ecommerce.mcp_server
claude mcp list
claude
```

Inside Claude Code, run `/mcp` and confirm `ecommerce` is connected. Ask for current simulated cart KPIs, top products, and low-stock alerts. Compare the answers to the tool results. Ask for last month's completed revenue to check that Claude identifies a metric the snapshot cannot support.

## Next steps

1. Run the Claude Code demo and capture a sanitized transcript with tool calls and answers.
2. Complete the Windows restart, verify the Docker engine, and smoke-test the image and persistent warehouse volume.
3. Implement GitHub Actions validation with deterministic fixtures on Windows and Linux.
4. Publish the validated image to GHCR after owner approval and verify the published digest.
5. Finish the README and supporting English documentation, then verify reproduction from a clean checkout.

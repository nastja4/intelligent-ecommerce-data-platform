# Local AI Assistant

The native React dashboard sends JSON chat requests through the Vite development proxy to FastAPI. FastAPI uses the official Anthropic Messages SDK and discovers the five analytical tools through the official MCP stdio client. The MCP server reads the current validated DuckDB Gold snapshot. Chat treats tool outputs as data and only returns tool execution summaries. Customer data stays limited to IDs and analytical aggregates.

## Start on Windows

Install the hash-locked requirements in the project's Python 3.12 virtual environment and install frontend dependencies with `npm ci` in `frontend`. Follow the root README to initialize the warehouse if needed. Configure the ignored root `.env` locally using `.env.example` as a reference. Supply a provider key privately and set `AI_ENABLED=true` only when ready to use credits. Explicit process environment settings take precedence. Leave AI disabled for ordinary analytics.

Run from the repository root in two PowerShell terminals.

```powershell
$env:WAREHOUSE_PATH = Join-Path (Get-Location) 'data/warehouse.duckdb'
.\.venv\Scripts\python.exe -m ecommerce.api
```

```powershell
Set-Location frontend
npm.cmd run dev
```

Open [Commerce Intelligence](http://127.0.0.1:5173) and select **AI Assistant**. Use one native API process bound to loopback. The chat endpoint checks the peer, host, browser origin and JSON content type. The Vite proxy is for development. There is no application authentication or public serving support. Questions, recent answers and relevant synthetic tool results leave the machine when a live request is sent. Never paste secrets or personal data into chat.

The status endpoint reports local configuration and ledger readiness without contacting Anthropic. Model access is confirmed by the separately approved live smoke test.

## Accounting and limits

The local SQLite ledger at `data/ai-usage.sqlite3` is separate from DuckDB. Preserve it between runs and backups. ACID transactions enforce the shared rolling five-request-per-minute limit and reserve the cost of each Messages call before sending it. Each request can make up to five tool rounds plus one final Messages call, with no SDK retries and up to 1500 output tokens per call. The serialized prompt is capped at 24,000 bytes and each tool result at 8,000 serialized characters. Oversize results are reported as unavailable, so narrow the ranking or stock threshold if needed.

The initial per-call reservation is USD 0.01075 at the maximum configured output size, based on the full 100,000-token standard pricing tier plus output. The ledger replaces the reservation with the estimated cost from reported usage after a successful reply. A timeout, process exit or uncertain provider failure can leave funds reserved indefinitely. Estimated usage includes these outstanding reservations. The app does not automatically release them on restart. Cache control is omitted and reported cache tokens are charged conservatively if they occur. See [Haiku 5.5 pricing](https://platform.claude.com/docs/en/models/haiku-5-5/overview).

At short context, input costs USD 0.10 per million tokens and output costs USD 0.50 per million tokens. The configured application ceiling is at most USD 2.00. The ledger cannot observe other clients, provider price changes, external concurrent spend or provider billing adjustments. Configure provider-side spending controls and prepaid credit protection separately.

## Interpretation and verification

Simulated gross cart value uses cart-line price times quantity before discounts. Currency, historical sales, profit, and customer behavior are unavailable. Stock alerts do not establish lost sales or inventory reservations. Tool-based grounding and prompt guidance reduce errors, but users should verify consequential answers against the source dashboard. A restart or browser reload loses the local conversation. If the warehouse is replaced mid-turn, tools may see different snapshots and the response cannot report a single common snapshot.

Tests use the official SDK with a mocked HTTP transport and a real local MCP subprocess against a fixture warehouse. A separately approved live smoke test should ask only for current KPIs with one tool round and a reduced output cap. Verify the tool result against REST, inspect usage and the remaining budget, and disable AI afterward. Do not repeat automatically on failure.

## Migrate the native usage ledger

Use the [Docker startup instructions](../README.md#docker) to build the image. Stop native FastAPI and all Docker AI containers before migrating. Keep the source database as a backup. If the destination already has an active ledger, the copy refuses to replace it. Retain that ledger and reconcile the two histories before choosing which environment to use.

Run these commands from the repository root before enabling Docker AI. If native development set a custom `AI_USAGE_PATH`, select that file instead.

```powershell
$ledger = (Resolve-Path .\data\ai-usage.sqlite3).Path
@'
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

destination = Path("/usage/ai-usage.sqlite3")
with TemporaryDirectory(dir=destination.parent) as work:
    candidate = Path(work) / "ledger.sqlite3"
    with closing(sqlite3.connect("file:/migration/ledger.sqlite3?mode=ro", uri=True)) as source:
        tables = {row[0] for row in source.execute("select name from sqlite_master where type='table'")}
        if not {"calls", "requests"}.issubset(tables):
            raise ValueError("The source is not an assistant usage ledger.")
        with closing(sqlite3.connect(candidate)) as target:
            source.backup(target)
            if target.execute("pragma quick_check").fetchone() != ("ok",):
                raise ValueError("Ledger integrity check failed.")
    candidate.chmod(0o600)
    os.link(candidate, destination)
'@ | docker compose --env-file .env.example run --rm --no-deps -T --volume "${ledger}:/migration/ledger.sqlite3:ro" app python -
if ($LASTEXITCODE) { throw 'Ledger migration failed' }
```

Use one assistant runtime at a time and preserve the same ledger when changing runtimes. Independent copies cannot account for each other's spending. Keep the native database closed during the backup so the mounted file includes all committed records.

## Docker runtime settings

Compose forwards settings to the `app` backend service only. Start with `--env-file .env.example` for the disabled baseline, or explicitly set runtime shell values before recreating the service. Follow the [masked key prompt](../README.md#optional-ai-at-runtime). A restart retains the container environment. Recreating the app preserves the warehouse and usage volumes under the same Compose project.

| Setting | Default |
| --- | --- |
| `AI_ENABLED` | `false` |
| `ANTHROPIC_API_KEY` | Empty. Required only to enable provider requests. |
| `ANTHROPIC_MODEL` | `claude-haiku-5-5` |
| `AI_BUDGET_USD` | `2.00` application ceiling |
| `AI_MAX_TOOL_ROUNDS` / `AI_MAX_OUTPUT_TOKENS` | `5` / `1500` |
| `AI_MAX_REQUESTS_PER_MINUTE` / `AI_MAX_QUESTION_LENGTH` | `5` / `2000` |

Keep the key out of image build arguments, frontend configuration, and Compose output. Usage estimates and Anthropic billing are separate. [Owner-observed Docker evidence](../PROGRESS.md#phase-10--release-corrections-and-portfolio)

# Implementation progress

**Technical MVP completed on 25 November 2026**

[SPEC.md](SPEC.md) defines acceptance criteria. [PLAN.md](PLAN.md) defines the implementation sequence.

| Phase | Status |
| --- | --- |
| 0 · Baseline | Python 3.12 package and hash-pinned dependencies verified on Windows and Linux x86-64. |
| 1 · Extract and load | Paginated fixture and live input, transactional Bronze refresh, deduplication, and rollback verified. |
| 2 · Transform and validate | Four Silver views and six Gold tables built. Candidate publication and Windows reader-lock failure isolation verified. |
| 3 · REST and MCP | Six REST endpoints and five actual stdio tools verified, including response parity and concurrent reads. |
| 4 · Docker and CI/CD | Local container checks passed. GitHub Actions workflow #1 passed all four jobs in 2 minutes 37 seconds, and the owner independently pulled the published GHCR image and matched its digest. |
| 5 · Demo and handoff | Owner verified three Claude Code scenarios. Portfolio documentation is complete. Independent clean-checkout reproduction remains open. |

## Acceptance criteria

| Criterion | Status | Evidence |
| --- | --- | --- |
| AC-01 · Ingest data | Verified | Fixture and live refreshes loaded products, users, and carts. Live counts were 194, 208, and 208 respectively. |
| AC-02 · Repeat ingestion | Verified | Repeated fixture refresh preserved source IDs and logical payloads without duplicates. |
| AC-03 · dbt build | Verified | 93 passes including 83 dbt data tests, with zero warnings, errors, or skips. |
| AC-04 · Warehouse layers | Verified | Three Bronze tables, four Silver views, and six Gold tables checked under their expected schema names. |
| AC-05 · Accurate metrics | Verified | Independent fixture checks returned `20.00` gross value, 3 carts, `6.67` average, and 3 items. Empty carts, empty snapshots, and failed reconciliation were exercised. |
| AC-06 · REST JSON | Verified | All six endpoints, Swagger, and OpenAPI passed smoke tests. Requests with invalid limits returned 422. |
| AC-07 · MCP tools | Verified | An SDK client initialized a stdio session, discovered and called all five tools, and confirmed structured REST parity. |
| AC-08 · Claude Code | Verified | Owner confirmed KPI retrieval, autonomous execution of four analytical tools, and rejection of unsupported historical completed-sales revenue. [Demo scenarios](docs/demo.md) |
| AC-09 · Automated tests | Verified | 66 Python tests passed on each of Windows and Linux. All 83 dbt data tests passed. Hosted Windows and Linux validation also passed in workflow #1. |
| AC-10 · Docker | Verified | Linux image built, ran as UID/GID 10001, and served fixture KPIs from the same read-only volume after recreation. Docker save/load preserved image identity. |
| AC-11 · GHCR | Verified | Workflow #1 published the SHA-tagged image. The owner independently pulled it and confirmed the matching digest. |
| AC-12 · Reproduction | Partially verified | Isolated Windows source copy and Linux image smoke tests passed. Independent reproduction by another developer following the README remains open. |

The verified live snapshot at `2026-11-25T13:19:40.839163Z` reported gross simulated cart value `3834278.63`, 208 carts, average `18434.03`, and 2417 items. The live smoke test is separate from automated fixture testing.

### Isolated reproduction

Copied 59 reviewed source paths into a separate project-local directory. The copy started without Git metadata, a virtual environment, a warehouse, or dbt artifacts. Windows reused the existing locked interpreter and imported the copied package. Fixture refresh, dbt documentation generation, `pip check`, and all 66 Python tests passed. A Linux image built from the copied source passed `pip check`, served the fixture KPIs and Swagger from a read-only volume, and preserved the snapshot across container recreation. Its installed package ran as UID 10001, and the image contained no prebuilt warehouse or checked local configuration paths.

## Pre-publication review

A local scan reviewed publication-eligible tracked and untracked files, ignored workspace path categories, 9 commits, and 61 locally stored Git blobs. It checked common token and private-key formats, literal credential assignments, customer payload fields, emails in repository content, personal absolute paths, risky filenames, and files of at least 1 MiB. No matches were found in the scanned repository content. The committed user fixture contains synthetic IDs and test metadata. Local generated DuckDB files, virtual environments, and caches remain outside Git and the Docker context. The Docker context allowlist admits the project files, dbt SQL/YAML, tests, and the three named synthetic fixtures.

The owner approved replacing the personal email in author and committer metadata before publication. All 11 commits reachable from the published `main` use the approved GitHub noreply address. The rewrite preserved the project tree, commit messages, names, timestamps, and parent order. The original history remains in an ignored local backup. The content scan was pattern-based and can miss unfamiliar secret formats.

## Windows verification workaround

If default pytest temp or cache access produces `WinError 5`, use a unique project-local path and disable the cache provider.

```powershell
$py = (Resolve-Path .\.venv\Scripts\python.exe).Path
$testTmp = Join-Path (Resolve-Path .\.venv).Path ("pytest-" + [guid]::NewGuid())
& $py -m pytest -q --basetemp $testTmp -p no:cacheprovider
```

## Publication evidence

- GitHub Actions workflow #1 succeeded. All four jobs passed in 2 minutes 37 seconds.
- Published commit: `a3749eaca2b06327d94a8d4b374f70dfda3b5846`.
- Published image: `ghcr.io/nastja4/intelligent-ecommerce-data-platform:a3749eaca2b06327d94a8d4b374f70dfda3b5846`.
- Registry digest: `sha256:5d5f3bd2cc29794e39a8992bb9b29f9170ac38ba849f030122c33848bba751b9`. The owner confirmed the match after an independent pull, and local Docker metadata for the SHA-tagged image reports the same digest.

AC-12 remains open for another developer to reproduce the project from a clean checkout of the published repository.

[Quick start](README.md) · [Data model](docs/data-model.md) · [Claude registration and demo](docs/demo.md) · [Cloud portability](docs/cloud-portability.md)

## Phase 7 · Local AI Assistant

The optional branch adds localhost chat routes, an Anthropic Messages adapter, a real MCP stdio client, a persistent SQLite usage ledger and an accessible React assistant. The published MVP and its acceptance evidence above remain in their original scope.

| Criterion | Evidence |
| --- | --- |
| AC-13 | The official SDK's mocked Messages transport and the real MCP stdio client exercised single-tool and multi-tool requests against deterministic Gold fixtures. Checks covered allowlist enforcement, argument validation, thinking-block replay, linked tool results and iteration bounds. |
| AC-14 | Automated checks covered local-only access, disabled and unconfigured states, budget and rate limits, concurrent reservations, restart persistence, pricing, timeout handling and sanitized errors. Git excludes the local environment and usage ledger. Docker's build-context allowlist excludes both. |
| AC-15 | Edge 158 exercised the assistant at 1920 × 1080, 1440 × 900, 1280 × 800, 1024 × 768, 768 × 1024 and 390 × 844 using intercepted chat responses. Verified safe Markdown, snapshot state transitions, cost display, keyboard focus, collapsed MCP details and real wheel scrolling with aligned pinned headers and an accessible composer. The six analytics endpoints also passed the browser smoke check. |
| AC-16 | Verified by the owner. Claude Haiku 5.5 authenticated successfully and the single-tool KPI question returned all four expected warehouse metrics: total gross simulated cart value, cart count, average cart value, and total item quantity. The multi-tool question successfully executed `get_top_products` (limit 20), `get_low_stock_products` (threshold 10), and `get_business_kpis`. |

The owner reported USD 0.0015199 in total estimated application usage and USD 1.9984801 in remaining estimated application budget. These are local ledger estimates. Actual provider charges are reported by Anthropic.

The complete Windows Python suite passed 75 tests, including fixture dbt refreshes. The frontend typecheck, eight frontend tests and production build passed. The binary dependency lock resolved with hash checks on Windows and Linux Python 3.12. The Windows download verified 84 wheels, and `pip check` found no broken requirements. Production integration and hosted verification of the assistant are deferred.

[Local assistant setup and limitations](docs/ai-assistant.md)

## Phase 8 · Production full-stack Docker

Built `ecommerce-fullstack:local` for Linux amd64. Docker reported 525,419,167 bytes. The pinned Node build ran `npm ci`, TypeScript and Vite production compilation. The Python runtime includes only compiled frontend files and uses UID/GID 10001.

| Criterion | Evidence |
| --- | --- |
| AC-17 | The production image served the React dashboard, compiled JS/CSS, custom SVG favicon, six REST endpoints, Swagger, and OpenAPI. Unknown API routes returned JSON 404. Edge 158 at 1440 × 900 verified hash navigation and observed a single origin, `http://127.0.0.1:8000`, with no Vite traffic. |
| AC-18 | Compose fixture refresh published 4 products, 3 users and 3 carts. A separate network-disabled dbt build passed all 93 nodes, including 83 data tests, with zero warnings, errors or skips. The fixture returned gross value 20.00, 3 carts, average value 6.67 and 3 items. A write-open on the serving DuckDB file failed with a read-only filesystem error. A synthetic SQLite charge and the original snapshot remained after container restart and replacement. |
| AC-19 | The running image reported disabled chat and safely rejected a correctly formed disabled request, a foreign origin, and a sibling container spoofing a forwarded address. The image filesystem and bundle checks found no local environment files, generated databases, credentials, frontend source maps, Node, or node_modules. The network-disabled Linux suite verified enabled chat with a mocked Anthropic transport and genuine fixture MCP. |

All 77 Python tests passed on Windows and Linux. Frontend typecheck, all 8 tests, and production build passed. The documented SQLite backup code preserved a synthetic balance when migrating to a new Docker volume. No real AI requests were made in this phase. Test containers were removed after verification and named volumes were retained. Hosted full-stack CI/CD and publication remain pending.

## Phase 9 · Full-stack CI/CD

- The workflow preserves the Windows/Ubuntu Python matrix, adds a pinned frontend job, and gates one full-stack image build on both. Publication still requires an approved main SHA and reloads the tested archive. The release verifies the archive checksum, image ID and source revision.
- Local actionlint 1.7.12, the locked Windows Python check, all 77 Windows tests, the frontend typecheck, all 8 frontend tests, and the frontend build passed. A fixture dbt build in the production image passed all 93 nodes, including 83 data tests, with zero warnings, errors or skips.
- All 77 tests passed in the production Linux image with networking disabled and temporary files on tmpfs. An earlier run on the container's writable layer encountered a SQLite lock during the concurrent ledger test. The rerun used the workflow's tmpfs settings and the same assertions.
- The production Compose smoke script passed from Windows and Linux PowerShell using alternate loopback ports and separate bridges. It exercised the same image before and after container replacement and left no test containers, networks or volumes. The original app on port 8000 remained running. A deliberate verification of the failed-overlap project confirmed its temporary resources were also removed.
- The local image artifact rehearsal verified checksum, save/load identity and the expected source revision. The real environment file was untouched. Tests used synthetic data and mocked Anthropic responses.

At the end of local Phase 9, **AC-20** awaited hosted verification. See the Phase 10 entry for the owner-confirmed PR run. **AC-21** remains pending owner approval, hosted publication and independent verification of the registry digest. The published backend MVP evidence above is unchanged.

## Phase 10 · Release corrections and portfolio

**Hosted check evidence.** The owner confirmed that all four validation jobs passed on PR #1. These were Python and dbt on Windows, Python and dbt on Ubuntu, frontend checks and build, and the full-stack Docker image build and validation. GHCR publication was correctly skipped on the PR. AC-20 is verified for the Phase 9 PR run. Hosted validation of the Phase 10 corrections remains pending. AC-21 remains pending owner-approved publication and an independent digest comparison.

### Owner-observed Docker verification

| Check | Observed result |
| --- | --- |
| Complete synthetic DummyJSON refresh | Gross simulated cart value **3,834,278.63**, **208** carts, average cart value **18,434.03**, **2,417** total items |
| Native SQLite ledger migration | Estimated usage **USD 0.001519900** and remaining estimated budget **USD 1.998480100** preserved in the Docker volume |
| Live category comparison | `get_category_performance` and `get_business_kpis` executed. The three category values and quantities matched expected results |
| Latest request | **3,889** input tokens, **957** output tokens, **USD 0.0008674** estimated |
| Cumulative estimated usage | **USD 0.0023873** |

The owner performed these live checks separately from automated verification. Ledger estimates do not establish actual Anthropic charges. The existing usage ledger was left untouched during Phase 10 implementation.

### Local Phase 10 verification

- All 77 Python tests passed on Windows and in the network-disabled Linux image. Frontend typecheck, all 11 tests, the production build, and actionlint passed.
- Isolated Compose runs from Windows and Linux PowerShell passed default-disabled and dummy-enabled checks. The refresh service, static assets and status response excluded the dummy credential. Same-origin restrictions held, and replacement preserved the fixture snapshot and synthetic usage record. Only test resources were removed.
- Edge exercised direct loads and reloads of all six pages in Vite and compiled FastAPI, plus sidebar navigation, Back and Forward, invalid fragments, keyboard focus and a wide analytical table at 390 × 844. Browser responses were mocked.

AC-22 is verified locally. The owner also manually verified the corrected dashboard navigation in Docker. For AC-23, the owner captured all 12 authentic screenshots covering analytics, the live assistant, Swagger, and CI. The gallery is complete, with public image review pending for account avatars and visible assistant estimates. Validation of the final PR revision remains outstanding.

[Portfolio screenshot gallery and publication review](docs/screenshots/README.md)

## Phase 11 · Frontend lint integration

The frontend uses ESLint flat config with exact development pins, recommended JavaScript and TypeScript rules, and React Hooks placement and dependency checks. VS Code workspace settings point to the frontend package. CI runs lint before the frontend build and keeps the existing Docker and GHCR release flow.

Local Node 22.16.0 verification passed `npm ci`, lint with zero warnings and errors, TypeScript, all 11 frontend tests, and the Vite production build. Running ESLint from the repository root confirmed the TSX parser and the browser, Hooks, and Node test scopes. The workflow passed actionlint 1.7.12. All 105 runtime package lock entries kept their versions and integrity hashes. Hosted verification of this revision is pending.

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

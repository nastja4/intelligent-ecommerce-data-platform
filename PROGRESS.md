# Implementation progress

**25 November 2026 · Core MVP verified locally, publication pending**

[SPEC.md](SPEC.md) defines acceptance criteria. [PLAN.md](PLAN.md) defines the implementation sequence.

| Phase | Status |
| --- | --- |
| 0 · Baseline | Python 3.12 package and hash-pinned dependencies verified on Windows and Linux x86-64. |
| 1 · Extract and load | Paginated fixture and live input, transactional Bronze refresh, deduplication, and rollback verified. |
| 2 · Transform and validate | Four Silver views and six Gold tables built. Candidate publication and Windows reader-lock failure isolation verified. |
| 3 · REST and MCP | Six REST endpoints and five actual stdio tools verified, including response parity and concurrent reads. |
| 4 · Docker and CI/CD | Local image build, Linux tests, non-root execution, volume persistence, and save/load verified. Hosted CI and GHCR remain pending. |
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
| AC-09 · Automated tests | Verified locally | 66 Python tests passed on each of Windows and Linux. All 83 dbt data tests passed. Hosted workflow execution is tracked separately under AC-11. |
| AC-10 · Docker | Verified | Linux image built, ran as UID/GID 10001, and served fixture KPIs from the same read-only volume after recreation. Docker save/load preserved image identity. |
| AC-11 · GHCR | Pending | The repository exists per the owner. This checkout has no configured remote. Hosted workflow, package publication, and registry digest are unverified. |
| AC-12 · Reproduction | Partially verified | Isolated Windows source copy and Linux image smoke tests passed. Independent reproduction by another developer following the README remains open. |

The verified live snapshot at `2026-11-25T13:19:40.839163Z` reported gross simulated cart value `3834278.63`, 208 carts, average `18434.03`, and 2417 items. The live smoke test is separate from automated fixture testing.

### Isolated reproduction

Copied 59 reviewed source paths into a separate project-local directory. The copy started without Git metadata, a virtual environment, a warehouse, or dbt artifacts. Windows reused the existing locked interpreter and imported the copied package. Fixture refresh, dbt documentation generation, `pip check`, and all 66 Python tests passed. A Linux image built from the copied source passed `pip check`, served the fixture KPIs and Swagger from a read-only volume, and preserved the snapshot across container recreation. Its installed package ran as UID 10001, and the image contained no prebuilt warehouse or checked local configuration paths.

## Pre-publication review

A local scan reviewed publication-eligible tracked and untracked files, ignored workspace path categories, 9 commits, and 61 locally stored Git blobs. It checked common token and private-key formats, literal credential assignments, customer payload fields, emails in repository content, personal absolute paths, risky filenames, and files of at least 1 MiB. No matches were found in the scanned repository content. The committed user fixture contains synthetic IDs and test metadata. Local generated DuckDB files, virtual environments, and caches remain outside Git and the Docker context. The Docker context allowlist admits the project files, dbt SQL/YAML, tests, and the three named synthetic fixtures.

Git author/committer metadata contains one distinct address outside the GitHub noreply domain. The owner should decide whether that identity is acceptable before publication. No address is reproduced here. The scan is a local pattern-based review, and unfamiliar secret formats may escape detection. Git history was preserved.

## Windows verification workaround

If default pytest temp or cache access produces `WinError 5`, use a unique project-local path and disable the cache provider.

```powershell
$py = (Resolve-Path .\.venv\Scripts\python.exe).Path
$testTmp = Join-Path (Resolve-Path .\.venv).Path ("pytest-" + [guid]::NewGuid())
& $py -m pytest -q --basetemp $testTmp -p no:cacheprovider
```

## Publication checklist

1. Confirm the existing repository URL, repository and package visibility, GHCR namespace, and whether to publish the current Git author metadata. Obtain explicit approval for the commit, push, and publication.
2. Review the publication files, then configure the approved remote and set the repository Actions variable `GHCR_APPROVED_SHA` to the exact approved commit before pushing to `main`. GitHub CLI is optional. Set the variable in **Settings → Secrets and variables → Actions → Variables** when using the web UI.
3. Verify the Windows, Ubuntu, and image jobs in **Actions**. Confirm the publish job uploaded `ghcr.io/<lowercase-owner>/<lowercase-repo>:<commit-sha>`. Pull the SHA tag and compare its digest with the workflow output.
4. Record independent clean-checkout reproduction against the published repository.

[Quick start](README.md) · [Data model](docs/data-model.md) · [Claude registration and demo](docs/demo.md) · [Cloud portability](docs/cloud-portability.md)

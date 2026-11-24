# Intelligent E-Commerce Data Platform

This portfolio project will load synthetic DummyJSON data into DuckDB, transform and validate it with dbt, and expose cart analytics through FastAPI and MCP. Cart values represent simulated activity.

The repository is at the scaffolding stage. Ingestion, dbt models, and serving interfaces are planned in [PLAN.md](PLAN.md). [SPEC.md](SPEC.md) defines the project requirements.

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

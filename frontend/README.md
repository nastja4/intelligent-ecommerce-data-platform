# Commerce Intelligence

An optional React dashboard for the existing backend MVP. It reads the validated snapshot over REST and displays simulated cart value, catalog performance, ranked customer IDs, and inventory. Reload re-reads the snapshot without starting ingestion.

## Prerequisites

- Windows PowerShell, Node.js 22.16.0 and npm 10.9.2.
- The repository's Python 3.12 `.venv` with the backend dependencies installed.
- An initialized warehouse. See the [backend quick start](../README.md#native-development-on-windows) for setup.

## Start locally

In a PowerShell terminal at the repository root, start FastAPI against the validated warehouse.

```powershell
$py = (Resolve-Path .\.venv\Scripts\python.exe).Path
$env:WAREHOUSE_PATH = (Resolve-Path .\data\warehouse.duckdb).Path
& $py -m ecommerce.api
```

In a second PowerShell terminal at the repository root:

```powershell
Set-Location .\frontend
npm.cmd ci
npm.cmd run dev
```

Open <http://127.0.0.1:5173>. Set independent product and customer limits (1–100) and the stock threshold (0–10,000), then select **Apply**. Products qualify when stock is strictly below the threshold. **Reload dashboard** fetches all six endpoints using the applied filters. **Swagger documentation** opens FastAPI's API reference through the development proxy.

```powershell
npm.cmd run typecheck
npm.cmd test
npm.cmd run build
```

## Architecture and limits

- `src/contracts.ts` reflects the FastAPI response schemas. `src/api.ts` sends relative read-only requests. The dashboard and its components render loading, empty, and error states.
- The category chart uses CSS. Monetary amounts retain their two-decimal strings for display, and the timestamp is shown in UTC. Customer rows expose IDs and aggregate metrics only.
- `vite.config.ts` binds the dev server to `127.0.0.1:5173` and proxies REST, health, and Swagger paths to `127.0.0.1:8000`. This proxy is a development configuration. Serving the static `dist/` output would require matching same-origin API routes.
- The dashboard supports one validated snapshot of synthetic cart activity. It has no authentication or history. A disconnected API or unavailable warehouse is reported in the page.

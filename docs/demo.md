# Claude Code analytics demo

On 25 November 2026, the project owner verified Claude Code registration and actual tool calls over MCP stdio. The scenarios below summarize the observed outcomes. Prompts are examples for reproduction.

| Scenario | Example prompt | Verified outcome |
| --- | --- | --- |
| Business KPI retrieval | What are the current simulated cart KPIs? | Claude selected `get_business_kpis` and interpreted the current snapshot. |
| Autonomous multi-tool analysis | Summarize the cart KPIs, compare products and customers, and flag low-stock items. | Claude selected and executed four analytical tools without requiring the user to name them. |
| Unsupported historical sales | What was our completed sales revenue last month? | Claude identified that the synthetic cart snapshot cannot answer a historical completed-sales question. |

The owner supplied scenario-level evidence. The multi-tool summary records the observed call count. The fixture's KPI reference values are `20.00` gross simulated value, 3 carts, `6.67` average, and 3 items. Both products and both customers with activity tie on gross value. The query service resolves ties by ascending ID.

## Reproduce the demo

From the repository root in PowerShell, prepare the fixture warehouse, then register the project-local server with the existing Claude subscription.

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

Open `/mcp` to confirm the connection. Run the prompts and inspect the tool calls as well as the answers. The server offers five bounded analytical tools and returns structured data with the snapshot timestamp and metric basis.

## Interpretation limits

Claude chooses tools and writes summaries, so wording and call order can vary. Verify claims against tool outputs, the snapshot time, and the [metric definitions](data-model.md). A current synthetic snapshot supports cart activity and catalog stock questions. It contains no completed sales history, verified currency, or time series. The observed refusal is evidence for that demo scenario, and model behavior can vary on other prompts.

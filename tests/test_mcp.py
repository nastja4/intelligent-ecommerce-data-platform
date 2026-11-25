import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import duckdb
from fastapi.testclient import TestClient
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from ecommerce.api import app


@asynccontextmanager
async def _session(warehouse: Path):
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "ecommerce.mcp_server"],
        env={"WAREHOUSE_PATH": str(warehouse)},
        cwd=warehouse.parent,
    )
    async with asyncio.timeout(60):
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer) as client:
                initialized = await client.initialize()
                assert initialized.server_info.name == "ecommerce"
                assert initialized.protocol_version
                yield client


def test_mcp_discovery_calls_and_rest_parity(configured_warehouse: Path) -> None:
    cases = {
        "get_business_kpis": ({}, "/api/v1/kpis"),
        "get_top_products": ({"limit": 1}, "/api/v1/products/top?limit=1"),
        "get_category_performance": ({}, "/api/v1/categories"),
        "get_top_customers": ({}, "/api/v1/customers/top"),
        "get_low_stock_products": ({"threshold": 0}, "/api/v1/inventory/low-stock?threshold=0"),
    }

    async def verify() -> None:
        async with _session(configured_warehouse) as session:
            tools = {tool.name: tool for tool in (await session.list_tools()).tools}
            assert set(tools) == set(cases)
            assert all(tool.output_schema for tool in tools.values())
            limit = tools["get_top_products"].input_schema["properties"]["limit"]
            threshold = tools["get_low_stock_products"].input_schema["properties"]["threshold"]
            assert (limit["minimum"], limit["maximum"], limit["default"]) == (1, 100, 10)
            assert (threshold["minimum"], threshold["maximum"], threshold["default"]) == (0, 10_000, 10)

            results = await asyncio.gather(
                *(session.call_tool(name, args) for name, (args, _) in cases.items())
            )
            with TestClient(app) as http:
                for result, (_, path) in zip(results, cases.values(), strict=True):
                    assert not result.is_error
                    response = http.get(path)
                    assert response.status_code == 200
                    assert result.structured_content == response.json()
            customers = results[3].structured_content["items"]
            assert all(set(row) == {"customer_id", "cart_count", "gross_cart_value"} for row in customers)

            for name, args in (
                ("get_top_products", {"limit": 0}),
                ("get_top_products", {"limit": True}),
                ("get_top_customers", {"limit": 101}),
                ("get_low_stock_products", {"threshold": 10_001}),
                ("run_sql", {}),
            ):
                rejected = await session.call_tool(name, args)
                assert rejected.is_error, name
                assert rejected.structured_content is None

    # The MCP child and REST both read while the parent holds a read-only handle.
    with duckdb.connect(str(configured_warehouse), read_only=True) as reader:
        assert reader.execute("select cart_count from gold.business_kpis").fetchone() == (3,)
        asyncio.run(verify())


def test_mcp_reports_unavailable_without_leaking_path(tmp_path: Path) -> None:
    missing = tmp_path / "private-name.duckdb"

    async def verify() -> None:
        async with _session(missing) as session:
            result = await session.call_tool("get_business_kpis")
            assert result.is_error
            assert result.structured_content is None
            assert "Warehouse is unavailable" in result.content[0].text
            assert missing.name not in result.content[0].text

    asyncio.run(verify())
    assert not missing.exists()

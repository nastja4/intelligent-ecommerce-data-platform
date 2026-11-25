"""Connect to the local analytical MCP server using stdio."""

import asyncio
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from pydantic import BaseModel, ConfigDict, Strict

from ecommerce.config import warehouse_path_from_env
from ecommerce.contracts import (
    DEFAULT_LIMIT, DEFAULT_THRESHOLD, BusinessKpis, CategoryPerformance, CustomerPerformance,
    InventoryProduct, Limit, ProductPerformance, SnapshotRows, Threshold,
)


class NoArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RankingArguments(NoArguments):
    limit: Annotated[Limit, Strict()] = DEFAULT_LIMIT


class StockArguments(NoArguments):
    threshold: Annotated[Threshold, Strict()] = DEFAULT_THRESHOLD


TOOLS: dict[str, tuple[type[BaseModel], type[BaseModel]]] = {
    "get_business_kpis": (NoArguments, BusinessKpis),
    "get_top_products": (RankingArguments, SnapshotRows[ProductPerformance]),
    "get_category_performance": (NoArguments, SnapshotRows[CategoryPerformance]),
    "get_top_customers": (RankingArguments, SnapshotRows[CustomerPerformance]),
    "get_low_stock_products": (StockArguments, SnapshotRows[InventoryProduct]),
}


@asynccontextmanager
async def analytical_session() -> AsyncIterator[tuple[ClientSession, list[dict[str, Any]]]]:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "ecommerce.mcp_server"],
        cwd=Path(__file__).resolve().parent.parent,
        env={"WAREHOUSE_PATH": str(warehouse_path_from_env())},
    )
    # Suppress child diagnostics on this path. The MCP SDK supplies a minimal default environment.
    failure: Exception | None = None
    with open(os.devnull, "w") as diagnostics:
        async with stdio_client(params, errlog=diagnostics) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                try:
                    async with asyncio.timeout(10):
                        await session.initialize()
                        tools = (await session.list_tools()).tools
                    allowed = [tool for tool in tools if tool.name in TOOLS]
                    if {tool.name for tool in allowed} != TOOLS.keys() or len(allowed) != len(TOOLS):
                        raise ValueError("Unexpected analytical tool discovery")
                    yield session, [
                        {"name": tool.name, "description": tool.description or "", "input_schema": tool.input_schema}
                        for tool in allowed
                    ]
                except Exception as exc:
                    # Exit the SDK task groups normally so request errors keep their original type.
                    failure = exc
    if failure is not None:
        raise failure

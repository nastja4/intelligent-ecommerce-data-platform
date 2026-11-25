"""Expose the approved analytical queries over MCP stdio."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Strict

from ecommerce import queries
from ecommerce.contracts import (
    DEFAULT_LIMIT,
    DEFAULT_THRESHOLD,
    BusinessKpis,
    CategoryPerformance,
    CustomerPerformance,
    InventoryProduct,
    Limit,
    ProductPerformance,
    SnapshotRows,
    Threshold,
)

server = MCPServer(
    "ecommerce",
    instructions=(
        "Report results as synthetic cart activity for the supplied snapshot. "
        "Gross cart value is pre-discount and does not represent completed sales. "
        "Explain when a requested metric, currency, or time period is unavailable."
    ),
)


@contextmanager
def _tool_errors() -> Iterator[None]:
    try:
        yield
    except queries.QueryError as exc:
        raise ToolError(str(exc)) from None


@server.tool()
def get_business_kpis() -> BusinessKpis:
    """Return synthetic cart KPIs for the current snapshot."""
    with _tool_errors():
        return queries.get_business_kpis()


@server.tool()
def get_top_products(
    limit: Annotated[Limit, Strict()] = DEFAULT_LIMIT,
) -> SnapshotRows[ProductPerformance]:
    """Rank products by pre-discount simulated cart value."""
    with _tool_errors():
        return queries.get_top_products(limit)


@server.tool()
def get_category_performance() -> SnapshotRows[CategoryPerformance]:
    """Return synthetic cart value and quantity by catalog category."""
    with _tool_errors():
        return queries.get_category_performance()


@server.tool()
def get_top_customers(
    limit: Annotated[Limit, Strict()] = DEFAULT_LIMIT,
) -> SnapshotRows[CustomerPerformance]:
    """Rank customer IDs by simulated cart value and include their cart counts."""
    with _tool_errors():
        return queries.get_top_customers(limit)


@server.tool()
def get_low_stock_products(
    threshold: Annotated[Threshold, Strict()] = DEFAULT_THRESHOLD,
) -> SnapshotRows[InventoryProduct]:
    """Return catalog products with stock strictly below the threshold."""
    with _tool_errors():
        return queries.get_low_stock_products(threshold)


if __name__ == "__main__":
    server.run(transport="stdio")

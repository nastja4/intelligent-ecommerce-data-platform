"""Read the published Gold snapshot through fixed analytical queries."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import TypeVar

import duckdb
from pydantic import BaseModel, TypeAdapter, ValidationError

from ecommerce.config import warehouse_path_from_env
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

LOGGER = logging.getLogger(__name__)
_LIMIT = TypeAdapter(Limit)
_THRESHOLD = TypeAdapter(Threshold)
_ITEM = TypeVar("_ITEM", bound=BaseModel)

_KPI_SQL = """
    select total_gross_cart_value, cart_count, average_cart_value, total_quantity, snapshot_at
    from gold.business_kpis
"""
_PRODUCT_SQL = """
    select product_id, title, category, gross_cart_value, total_quantity
    from gold.product_performance
    order by gross_cart_value desc, product_id
    limit ?
"""
_CATEGORY_SQL = """
    select category, gross_cart_value, total_quantity
    from gold.category_performance
    order by gross_cart_value desc, category
"""
_CUSTOMER_SQL = """
    select customer_id, gross_cart_value, cart_count
    from gold.customer_performance
    order by gross_cart_value desc, customer_id
    limit ?
"""
_INVENTORY_SQL = """
    select product_id, title, stock
    from gold.inventory_alerts
    where stock < ?
    order by stock, product_id
"""


class QueryError(RuntimeError):
    """An analytical request failed with a client-safe explanation."""


class WarehouseUnavailable(QueryError):
    """The published database could not be opened or is not initialized."""


@contextmanager
def _read_warehouse() -> Iterator[duckdb.DuckDBPyConnection]:
    try:
        path = warehouse_path_from_env()
    except (OSError, ValueError, RuntimeError):
        raise WarehouseUnavailable("Warehouse path is unavailable.") from None

    try:
        with duckdb.connect(str(path), read_only=True) as connection:
            yield connection
    except duckdb.CatalogException:
        raise WarehouseUnavailable("Warehouse is not initialized.") from None
    except (duckdb.IOException, duckdb.ConnectionException):
        raise WarehouseUnavailable("Warehouse is unavailable. Check the file and active writers.") from None
    except (duckdb.Error, ValidationError) as exc:
        LOGGER.error("Analytical query failed (%s).", type(exc).__name__)
        raise QueryError("Analytical query failed.") from None


def _snapshot_at(connection: duckdb.DuckDBPyConnection) -> datetime:
    row = connection.execute("select snapshot_at from gold.business_kpis").fetchone()
    if row is None:
        raise WarehouseUnavailable("Warehouse is not initialized.")
    return row[0]


def _dict_rows(cursor: duckdb.DuckDBPyConnection) -> list[dict[str, object]]:
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def _select_items(
    sql: str, parameters: list[int], item_type: type[_ITEM]
) -> SnapshotRows[_ITEM]:
    with _read_warehouse() as connection:
        timestamp = _snapshot_at(connection)
        rows = _dict_rows(connection.execute(sql, parameters))
        return SnapshotRows[item_type](
            snapshot_at=timestamp, items=[item_type.model_validate(row) for row in rows]
        )


def check_health() -> None:
    with _read_warehouse() as connection:
        if not _dict_rows(connection.execute(_KPI_SQL)):
            raise WarehouseUnavailable("Warehouse is not initialized.")
        connection.execute(_PRODUCT_SQL, [0])
        connection.execute(_CATEGORY_SQL + " limit 0")
        connection.execute(_CUSTOMER_SQL, [0])
        connection.execute(_INVENTORY_SQL + " limit 0", [0])


def get_business_kpis() -> BusinessKpis:
    with _read_warehouse() as connection:
        rows = _dict_rows(connection.execute(_KPI_SQL))
        if not rows:
            raise WarehouseUnavailable("Warehouse is not initialized.")
        return BusinessKpis.model_validate(rows[0])


def get_top_products(limit: Limit = DEFAULT_LIMIT) -> SnapshotRows[ProductPerformance]:
    return _select_items(_PRODUCT_SQL, [_LIMIT.validate_python(limit, strict=True)], ProductPerformance)


def get_category_performance() -> SnapshotRows[CategoryPerformance]:
    return _select_items(_CATEGORY_SQL, [], CategoryPerformance)


def get_top_customers(limit: Limit = DEFAULT_LIMIT) -> SnapshotRows[CustomerPerformance]:
    return _select_items(_CUSTOMER_SQL, [_LIMIT.validate_python(limit, strict=True)], CustomerPerformance)


def get_low_stock_products(threshold: Threshold = DEFAULT_THRESHOLD) -> SnapshotRows[InventoryProduct]:
    return _select_items(
        _INVENTORY_SQL, [_THRESHOLD.validate_python(threshold, strict=True)], InventoryProduct
    )

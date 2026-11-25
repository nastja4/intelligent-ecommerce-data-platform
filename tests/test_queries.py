from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import duckdb
import pytest
from pydantic import ValidationError

from ecommerce import queries


def test_fixture_queries(configured_warehouse: Path) -> None:
    kpis = queries.get_business_kpis()
    assert (kpis.total_gross_cart_value, kpis.cart_count, kpis.average_cart_value, kpis.total_quantity) == (
        "20.00", 3, "6.67", 3,
    )
    products = queries.get_top_products()
    assert products.snapshot_at == kpis.snapshot_at
    assert products.metric_basis == "gross_simulated_cart_line_value_before_discounts"
    assert [(p.product_id, p.gross_cart_value, p.total_quantity) for p in products.items] == [
        (101, "10.00", 2), (102, "10.00", 1),
    ]
    assert [p.product_id for p in queries.get_top_products(1).items] == [101]
    assert len(queries.get_top_products(100).items) == 2
    assert [(c.category, c.gross_cart_value, c.total_quantity) for c in queries.get_category_performance().items] == [
        ("kitchen", "10.00", 1), ("stationery", "10.00", 2),
    ]
    rows = queries.get_top_customers().items
    assert [row.model_dump() for row in rows] == [
        {"customer_id": 301, "gross_cart_value": "10.00", "cart_count": 2},
        {"customer_id": 302, "gross_cart_value": "10.00", "cart_count": 1},
    ]
    assert [c.customer_id for c in queries.get_top_customers(1).items] == [301]


def test_inventory_threshold_boundaries(configured_warehouse: Path) -> None:
    assert queries.get_low_stock_products(0).items == []
    assert [(p.product_id, p.stock) for p in queries.get_low_stock_products().items] == [(104, 0), (101, 9)]
    assert [p.product_id for p in queries.get_low_stock_products(10_000).items] == [104, 101, 102, 103]


@pytest.mark.parametrize(
    ("function", "value"),
    [
        (queries.get_top_products, 0),
        (queries.get_top_customers, 101),
        (queries.get_top_products, "1"),
        (queries.get_top_products, True),
        (queries.get_low_stock_products, -1),
        (queries.get_low_stock_products, 10_001),
    ],
)
def test_services_validate_before_accessing_warehouse(function, value) -> None:
    with pytest.raises(ValidationError):
        function(value)


@pytest.mark.parametrize("create_database", [False, True])
def test_warehouse_unavailable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, create_database: bool) -> None:
    path = tmp_path / "unavailable.duckdb"
    if create_database:
        with duckdb.connect(str(path)):
            pass
    monkeypatch.setenv("WAREHOUSE_PATH", str(path))
    with pytest.raises(queries.WarehouseUnavailable) as error:
        queries.get_business_kpis()
    assert str(path) not in str(error.value)
    assert path.exists() is create_database


def test_invalid_ingestion_settings_do_not_affect_reads(
    configured_warehouse: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DUMMYJSON_PAGE_SIZE", "invalid")
    assert queries.get_business_kpis().cart_count == 3


def test_connection_is_read_only_and_closes(configured_warehouse: Path) -> None:
    with queries._read_warehouse() as connection:
        with pytest.raises(duckdb.Error, match="read.only"):
            connection.execute("create table forbidden (id integer)")
    with pytest.raises(duckdb.ConnectionException, match="closed"):
        connection.execute("select 1")


def test_lock_error_becomes_sanitized_unavailable(
    configured_warehouse: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def locked(_path: str, *, read_only: bool) -> None:
        assert read_only is True
        raise duckdb.IOException("private path and lock owner diagnostics")

    monkeypatch.setattr(duckdb, "connect", locked)
    with pytest.raises(queries.WarehouseUnavailable, match=r"^Warehouse is unavailable\.") as error:
        queries.get_business_kpis()
    assert "private" not in str(error.value)


def test_concurrent_read_only_queries(configured_warehouse: Path) -> None:
    with ThreadPoolExecutor(max_workers=4) as workers:
        snapshots = list(workers.map(lambda _: queries.get_business_kpis(), range(8)))
    assert all(snapshot == snapshots[0] for snapshot in snapshots)

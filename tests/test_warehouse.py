"""Verify warehouse metrics against independent, hand-calculated fixture values."""

import os
import subprocess
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest

from ecommerce.extract import RESOURCES, Snapshot, extract_fixtures
from ecommerce.load import load_bronze

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
INGESTED_AT = datetime(2025, 1, 1, 12, tzinfo=UTC)
EXPECTED_RELATIONS = {
    ("bronze", "raw_products", "BASE TABLE"),
    ("bronze", "raw_users", "BASE TABLE"),
    ("bronze", "raw_carts", "BASE TABLE"),
    ("silver", "stg_products", "VIEW"),
    ("silver", "stg_users", "VIEW"),
    ("silver", "stg_carts", "VIEW"),
    ("silver", "stg_cart_items", "VIEW"),
    ("gold", "cart_summary", "BASE TABLE"),
    ("gold", "product_performance", "BASE TABLE"),
    ("gold", "category_performance", "BASE TABLE"),
    ("gold", "customer_performance", "BASE TABLE"),
    ("gold", "inventory_alerts", "BASE TABLE"),
    ("gold", "business_kpis", "BASE TABLE"),
}


def _build_warehouse(tmp_path: Path, snapshot: Snapshot) -> Path:
    warehouse = tmp_path / "warehouse.duckdb"
    load_bronze(warehouse, snapshot, ingested_at=INGESTED_AT)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from dbt.cli.main import cli; cli()",
            "build",
            "--project-dir",
            str(ROOT / "analytics"),
            "--profiles-dir",
            str(ROOT / "analytics"),
            "--target-path",
            str(tmp_path / "target"),
        ],
        env={
            **os.environ,
            "WAREHOUSE_PATH": str(warehouse),
            "DBT_LOG_PATH": str(tmp_path / "logs"),
            "DBT_SEND_ANONYMOUS_USAGE_STATS": "false",
        },
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return warehouse


def test_gold_fixture_metrics(tmp_path: Path) -> None:
    snapshot = extract_fixtures(FIXTURES)
    # Vary prices and reported totals to prove valuation uses only the cart lines.
    snapshot["products"][0]["price"] = 999.99
    snapshot["carts"][0]["total"] = 350.0
    warehouse = _build_warehouse(tmp_path, snapshot)

    with duckdb.connect(str(warehouse), read_only=True) as con:
        assert set(con.execute("""
            select table_schema, table_name, table_type
            from information_schema.tables
            where table_schema in ('bronze', 'silver', 'gold')
        """).fetchall()) == EXPECTED_RELATIONS

        assert con.execute("select * from gold.cart_summary order by cart_id").fetchall() == [
            (201, 301, Decimal("10.00"), 2),
            (202, 302, Decimal("10.00"), 1),
            (203, 301, Decimal("0.00"), 0),
        ]
        assert con.execute("""
            select product_id, category, gross_cart_value, total_quantity
            from gold.product_performance
            order by product_id
        """).fetchall() == [
            (101, "stationery", Decimal("10.00"), 2),
            (102, "kitchen", Decimal("10.00"), 1),
        ]
        assert con.execute("""
            select * from gold.category_performance order by category
        """).fetchall() == [
            ("kitchen", Decimal("10.00"), 1),
            ("stationery", Decimal("10.00"), 2),
        ]
        assert con.execute("""
            select * from gold.customer_performance order by customer_id
        """).fetchall() == [(301, Decimal("10.00"), 2), (302, Decimal("10.00"), 1)]
        assert [column[0] for column in con.description] == [
            "customer_id", "gross_cart_value", "cart_count",
        ]
        assert con.execute("""
            select product_id, stock from gold.inventory_alerts order by product_id
        """).fetchall() == [(101, 9), (102, 10), (103, 11), (104, 0)]
        assert con.execute("select * from gold.business_kpis").fetchall() == [
            (Decimal("20.00"), 3, Decimal("6.67"), 3, INGESTED_AT),
        ]
        kpi_types = dict(
            (name, value_type)
            for name, value_type, *_ in con.execute("describe gold.business_kpis").fetchall()
        )
        assert kpi_types["total_gross_cart_value"] == "DECIMAL(38,2)"
        assert kpi_types["average_cart_value"] == "DECIMAL(38,2)"


@pytest.mark.parametrize("has_empty_cart", [False, True], ids=["empty-snapshot", "empty-cart-only"])
def test_gold_zero_activity(tmp_path: Path, has_empty_cart: bool) -> None:
    if has_empty_cart:
        snapshot = extract_fixtures(FIXTURES)
        snapshot["carts"] = [snapshot["carts"][-1]]
    else:
        snapshot = {resource: [] for resource in RESOURCES}

    before_build = datetime.now(UTC)
    warehouse = _build_warehouse(tmp_path, snapshot)
    after_build = datetime.now(UTC)

    with duckdb.connect(str(warehouse), read_only=True) as con:
        rows = con.execute("select * from gold.business_kpis").fetchall()
        assert len(rows) == 1
        gross, cart_count, average, quantity, snapshot_at = rows[0]
        assert gross == Decimal("0.00")
        assert quantity == 0
        assert con.execute("select count(*) from gold.product_performance").fetchone() == (0,)
        assert con.execute("select count(*) from gold.category_performance").fetchone() == (0,)

        carts = con.execute("select * from gold.cart_summary").fetchall()
        customers = con.execute("select * from gold.customer_performance").fetchall()
        inventory_count = con.execute("select count(*) from gold.inventory_alerts").fetchone()
        if has_empty_cart:
            assert (cart_count, average) == (1, Decimal("0.00"))
            assert snapshot_at == INGESTED_AT
            assert carts == [(203, 301, Decimal("0.00"), 0)]
            assert customers == [(301, Decimal("0.00"), 1)]
            assert inventory_count == (4,)
        else:
            assert (cart_count, average) == (0, None)
            assert before_build <= snapshot_at <= after_build
            assert carts == customers == []
            assert inventory_count == (0,)

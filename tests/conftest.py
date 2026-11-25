"""Shared fixture warehouse for Phase 3 adapter tests."""

from pathlib import Path

import pytest

from ecommerce.config import Settings
from ecommerce.refresh import refresh_warehouse


@pytest.fixture(scope="session")
def analytics_warehouse(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("analytics") / "warehouse.duckdb"
    fixtures = Path(__file__).parent / "fixtures"
    assert refresh_warehouse(Settings(path), fixture_dir=fixtures) == {
        "products": 4, "users": 3, "carts": 3,
    }
    return path


@pytest.fixture
def configured_warehouse(analytics_warehouse: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("WAREHOUSE_PATH", str(analytics_warehouse))
    return analytics_warehouse

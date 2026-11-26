from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient

from ecommerce import queries
from ecommerce.api import app


def test_rest_responses_and_openapi(configured_warehouse: Path) -> None:
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        response = client.get("/api/v1/kpis")
        assert response.status_code == 200
        kpis = response.json()
        assert kpis == queries.get_business_kpis().model_dump(mode="json")
        assert kpis["snapshot_at"].endswith("Z")
        assert kpis["total_gross_cart_value"] == "20.00"
        assert kpis["average_cart_value"] == "6.67"
        assert client.get("/api/v1/products/top?limit=1").json()["items"][0]["product_id"] == 101
        assert len(client.get("/api/v1/categories").json()["items"]) == 2
        assert client.get("/api/v1/customers/top?limit=1").json()["items"] == [
            {"customer_id": 301, "gross_cart_value": "10.00", "cart_count": 2}
        ]
        assert client.get("/api/v1/inventory/low-stock?threshold=0").json()["items"] == []
        assert client.get("/docs").status_code == 200
        schema = client.get("/openapi.json").json()
        assert set(schema["paths"]) == {
            "/health", "/api/v1/kpis", "/api/v1/products/top", "/api/v1/categories",
            "/api/v1/customers/top", "/api/v1/inventory/low-stock",
            "/api/v1/chat/status", "/api/v1/chat",
        }
        parameter = schema["paths"]["/api/v1/products/top"]["get"]["parameters"][0]["schema"]
        assert (parameter["minimum"], parameter["maximum"], parameter["default"]) == (1, 100, 10)
        assert schema["components"]["schemas"]["BusinessKpis"]["properties"]["total_gross_cart_value"]["type"] == "string"


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/products/top?limit=0",
        "/api/v1/customers/top?limit=101",
        "/api/v1/products/top?limit=private-invalid-input",
        "/api/v1/inventory/low-stock?threshold=-1",
        "/api/v1/inventory/low-stock?threshold=10001",
    ],
)
def test_bad_arguments_return_sanitized_422(path: str) -> None:
    with TestClient(app) as client:
        response = client.get(path)
    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid request parameters."}


@pytest.mark.parametrize("create_database", [False, True])
def test_health_and_kpis_report_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, create_database: bool
) -> None:
    path = tmp_path / "unavailable.duckdb"
    if create_database:
        with duckdb.connect(str(path)):
            pass
    monkeypatch.setenv("WAREHOUSE_PATH", str(path))
    with TestClient(app) as client:
        for route in ("/health", "/api/v1/kpis"):
            response = client.get(route)
            assert response.status_code == 503
            assert str(path) not in response.text


def test_unexpected_duckdb_error_is_sanitized(configured_warehouse: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(_path: str, *, read_only: bool) -> None:
        raise duckdb.InternalException("private database diagnostics")

    monkeypatch.setattr(duckdb, "connect", fail)
    with TestClient(app) as client:
        response = client.get("/api/v1/kpis")
    assert response.status_code == 500
    assert response.json() == {"detail": "Analytical query failed."}

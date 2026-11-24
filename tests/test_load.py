import json
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import duckdb
import pytest

from ecommerce.extract import RESOURCES, extract_fixtures
from ecommerce.load import LoadError, load_bronze, main

FIXTURES = Path(__file__).parent / "fixtures"
FIRST_LOAD = datetime(2025, 1, 1, tzinfo=UTC)


def _read_rows(path: Path) -> dict[str, list[tuple]]:
    with duckdb.connect(str(path), read_only=True) as connection:
        connection.execute("SET TimeZone = 'UTC'")
        return {
            resource: connection.execute(
                f"SELECT source_id, payload, ingested_at FROM bronze.raw_{resource} ORDER BY source_id"
            ).fetchall()
            for resource in RESOURCES
        }


def test_full_refresh_preserves_payloads_and_is_logically_idempotent(tmp_path: Path) -> None:
    warehouse = tmp_path / "nested" / "warehouse.duckdb"
    snapshot = extract_fixtures(FIXTURES)
    expected_counts = {"products": 4, "users": 3, "carts": 3}
    assert load_bronze(warehouse, snapshot, ingested_at=FIRST_LOAD) == expected_counts
    first = _read_rows(warehouse)
    for resource in RESOURCES:
        assert {key: json.loads(payload) for key, payload, _ in first[resource]} == {
            record["id"]: record for record in snapshot[resource]
        }
        assert all(timestamp == FIRST_LOAD for _, _, timestamp in first[resource])

    later_load = FIRST_LOAD + timedelta(hours=1)
    same_instant_with_offset = later_load.astimezone(timezone(timedelta(hours=2)))
    assert load_bronze(warehouse, snapshot, ingested_at=same_instant_with_offset) == expected_counts
    second = _read_rows(warehouse)
    for resource in RESOURCES:
        assert [row[:2] for row in second[resource]] == [row[:2] for row in first[resource]]
        assert all(timestamp == later_load for _, _, timestamp in second[resource])


def test_identical_records_deduplicate_even_if_object_keys_are_reordered(tmp_path: Path) -> None:
    warehouse = tmp_path / "warehouse.duckdb"
    snapshot = extract_fixtures(FIXTURES)
    snapshot["users"].extend(
        [
            {"testMetadata": {"group": "fixture-a"}, "id": 301},
            {"id": 301, "testMetadata": {"group": "fixture-a"}},
        ]
    )

    assert load_bronze(warehouse, snapshot, ingested_at=FIRST_LOAD)["users"] == 3
    assert [key for key, _, _ in _read_rows(warehouse)["users"]] == [301, 302, 303]


def test_conflicting_records_fail_before_writes(tmp_path: Path) -> None:
    warehouse = tmp_path / "warehouse.duckdb"
    snapshot = extract_fixtures(FIXTURES)
    load_bronze(warehouse, snapshot, ingested_at=FIRST_LOAD)
    before = _read_rows(warehouse)
    snapshot["users"].append({"id": 301, "testMetadata": {"group": "conflict"}})

    with pytest.raises(LoadError, match="users contains conflicting records for source ID 301"):
        load_bronze(warehouse, snapshot)
    assert _read_rows(warehouse) == before


def test_refresh_removes_outdated_source_ids(tmp_path: Path) -> None:
    warehouse = tmp_path / "warehouse.duckdb"
    snapshot = extract_fixtures(FIXTURES)
    load_bronze(warehouse, snapshot, ingested_at=FIRST_LOAD)
    replacement = {"products": snapshot["products"][:1], "users": [], "carts": []}

    assert load_bronze(warehouse, replacement) == {"products": 1, "users": 0, "carts": 0}
    rows = _read_rows(warehouse)
    assert [key for key, _, _ in rows["products"]] == [101]
    assert rows["users"] == rows["carts"] == []


def test_failed_insert_rolls_back_prior_deletes_and_inserts(tmp_path: Path) -> None:
    warehouse = tmp_path / "warehouse.duckdb"
    with duckdb.connect(str(warehouse)) as connection:
        connection.execute("CREATE SCHEMA bronze")
        connection.execute(
            """CREATE TABLE bronze.raw_carts (
                source_id BIGINT PRIMARY KEY CHECK (source_id <> 999),
                payload JSON NOT NULL,
                ingested_at TIMESTAMPTZ NOT NULL
            )"""
        )
    initial = extract_fixtures(FIXTURES)
    load_bronze(warehouse, initial, ingested_at=FIRST_LOAD)
    before = _read_rows(warehouse)
    replacement = {
        "products": [{"id": 901}],
        "users": [{"id": 902}],
        "carts": [{"id": 903}, {"id": 999}],
    }

    with pytest.raises(duckdb.ConstraintException):
        load_bronze(warehouse, replacement)
    assert _read_rows(warehouse) == before


def test_cli_fixture_mode_prints_counts_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    warehouse = tmp_path / "warehouse.duckdb"
    monkeypatch.setenv("WAREHOUSE_PATH", str(warehouse))

    assert main(["--fixture-dir", str(FIXTURES)]) == 0
    output = capsys.readouterr()
    assert json.loads(output.out) == {"products": 4, "users": 3, "carts": 3}
    assert output.err == ""


def test_cli_reports_invalid_fixture_without_creating_warehouse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    warehouse = tmp_path / "warehouse.duckdb"
    monkeypatch.setenv("WAREHOUSE_PATH", str(warehouse))
    (tmp_path / "products.json").write_text("private-response-body", encoding="utf-8")

    assert main(["--fixture-dir", str(tmp_path)]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert "Cannot read products.json" in output.err
    assert "private-response-body" not in output.err
    assert not warehouse.exists()

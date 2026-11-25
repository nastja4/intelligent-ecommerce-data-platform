"""Exercise candidate validation, publication, and failure isolation."""

import shutil
import re
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest

from ecommerce import refresh
from ecommerce.extract import RESOURCES, extract_fixtures
from ecommerce.load import load_bronze

FIXTURES = Path(__file__).parent / "fixtures"
COUNTS = {"products": 4, "users": 3, "carts": 3}


def _assert_published(warehouse: Path) -> dict[str, list[tuple]]:
    with duckdb.connect(str(warehouse), read_only=True) as connection:
        relations = set(connection.execute("""
            select table_schema || '.' || table_name, table_type
            from information_schema.tables
            where table_schema in ('bronze', 'silver', 'gold')
        """).fetchall())
        assert relations == refresh.EXPECTED_RELATIONS
        # Reopen the renamed file and query the views as well as the tables.
        assert connection.execute("""
            select cart_id, item_ordinal, product_id
            from silver.stg_cart_items
            order by cart_id, item_ordinal
        """).fetchall() == [(201, 0, 101), (201, 1, 101), (202, 0, 102)]
        assert connection.execute("""
            select total_gross_cart_value, cart_count, average_cart_value, total_quantity
            from gold.business_kpis
        """).fetchall() == [(Decimal("20.00"), 3, Decimal("6.67"), 3)]
        return {
            name: connection.execute(
                f"select source_id, payload from bronze.raw_{name} order by source_id"
            ).fetchall()
            for name in RESOURCES
        }


@pytest.fixture(scope="module")
def baseline(tmp_path_factory: pytest.TempPathFactory) -> Path:
    warehouse = tmp_path_factory.mktemp("refresh-baseline") / "active.duckdb"
    assert refresh.refresh_warehouse(refresh.Settings(warehouse), fixture_dir=FIXTURES) == COUNTS
    _assert_published(warehouse)
    return warehouse


@pytest.fixture
def active(tmp_path: Path, baseline: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    warehouse = tmp_path / "active.duckdb"
    shutil.copyfile(baseline, warehouse)
    monkeypatch.setenv("WAREHOUSE_PATH", str(warehouse))
    return warehouse


def _assert_preserved(active: Path, before: bytes) -> None:
    assert active.read_bytes() == before
    assert list(active.parent.iterdir()) == [active]
    _assert_published(active)


def test_repeated_fixture_refresh(active: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    initial_rows = _assert_published(active)
    monkeypatch.setenv("DBT_EMPTY", "true")
    assert refresh.main(["--fixture-dir", str(FIXTURES)]) == 0
    assert _assert_published(active) == initial_rows
    assert list(active.parent.iterdir()) == [active]


def test_failed_extraction_preserves_active_warehouse(
    active: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = active.read_bytes()
    assert refresh.main(["--fixture-dir", str(active.parent / "missing")]) == 1
    output = capsys.readouterr()
    assert "Cannot read products.json" in output.err
    assert not output.out
    _assert_preserved(active, before)


def test_failed_load_cleans_candidate_artifacts(
    active: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    before = active.read_bytes()

    def fail_load(path: Path, snapshot: dict) -> None:
        assert path.parent == active.parent and path != active
        path.touch()
        path.with_suffix(".duckdb.wal").touch()
        spill = path.with_suffix(".duckdb.tmp")
        spill.mkdir()
        (spill / "spill").touch()
        raise duckdb.IOException("private source data")

    monkeypatch.setattr(refresh, "load_bronze", fail_load)
    assert refresh.main(["--fixture-dir", str(FIXTURES)]) == 1
    output = capsys.readouterr()
    assert "Could not load candidate Bronze tables" in output.err
    assert "private source data" not in output.err
    assert not output.out
    _assert_preserved(active, before)


def test_real_dbt_failure_preserves_active_warehouse(
    active: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    before = active.read_bytes()
    snapshot = extract_fixtures(FIXTURES)
    snapshot["products"][0]["stock"] = -1
    monkeypatch.setattr(refresh, "extract_fixtures", lambda directory: snapshot)

    assert refresh.main(["--fixture-dir", str(FIXTURES)]) == 1
    output = capsys.readouterr()
    assert "dbt build exited with code 1" in output.err
    assert re.search(r"non_negative_stg_products_stock\.[a-f0-9]+ \(1 failing rows\)", output.err)
    assert not output.out
    _assert_preserved(active, before)


def test_successful_dbt_exit_without_expected_relations_prevents_publication(
    active: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    before = active.read_bytes()
    monkeypatch.setattr(refresh, "_build_candidate", lambda candidate, target: None)

    assert refresh.main(["--fixture-dir", str(FIXTURES)]) == 1
    output = capsys.readouterr()
    assert "gold.business_kpis (BASE TABLE)" in output.err
    assert not output.out
    _assert_preserved(active, before)


def test_failed_publication_preserves_active_warehouse(
    active: Path, baseline: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    before = active.read_bytes()

    def use_built_candidate(candidate: Path, target: Path) -> None:
        # Simulate a successful build. The real build is covered by the baseline and rerun.
        shutil.copyfile(baseline, candidate)

    def fail_replace(candidate: Path, final: Path) -> None:
        assert candidate.parent == final.parent and final == active
        _assert_published(candidate)
        raise PermissionError("private OS diagnostic")

    monkeypatch.setattr(refresh, "_build_candidate", use_built_candidate)
    monkeypatch.setattr(refresh.os, "replace", fail_replace)
    assert refresh.main(["--fixture-dir", str(FIXTURES)]) == 1
    output = capsys.readouterr()
    assert "Stop all warehouse readers and writers" in output.err
    assert "private OS diagnostic" not in output.err
    assert not output.out
    _assert_preserved(active, before)


def test_active_wal_is_preserved(
    active: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    before = active.read_bytes()
    wal = active.with_suffix(".duckdb.wal")
    wal.write_bytes(b"existing WAL")
    monkeypatch.setattr(refresh, "_build_candidate", lambda candidate, target: None)
    monkeypatch.setattr(refresh, "_verify_relations", lambda candidate: None)

    assert refresh.main(["--fixture-dir", str(FIXTURES)]) == 1
    output = capsys.readouterr()
    assert "warehouse WAL is present" in output.err
    assert not output.out
    assert wal.read_bytes() == b"existing WAL"
    wal.unlink()
    _assert_preserved(active, before)

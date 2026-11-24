import json
from pathlib import Path

import httpx
import pytest

from ecommerce.config import Settings
from ecommerce.extract import RESOURCES, ExtractionError, extract_fixtures, extract_live

FIXTURES = Path(__file__).parent / "fixtures"


def test_live_paginates_all_resources_using_fixture_pages(tmp_path: Path) -> None:
    pages = {
        resource: json.loads((FIXTURES / f"{resource}.json").read_text(encoding="utf-8"))
        for resource in RESOURCES
    }
    requests = []

    def handle(request: httpx.Request) -> httpx.Response:
        resource = request.url.path.removeprefix("/")
        skip = int(request.url.params["skip"])
        requests.append((resource, skip))
        assert request.url.params["limit"] == "2"
        assert request.extensions["timeout"]["read"] == 4.0
        return httpx.Response(200, json=pages[resource][skip // 2])

    settings = Settings(tmp_path / "test.duckdb", timeout_seconds=4, page_size=2)
    assert extract_live(settings, transport=httpx.MockTransport(handle)) == extract_fixtures(FIXTURES)
    assert requests == [(resource, skip) for resource in RESOURCES for skip in (0, 2)]


def test_live_advances_by_actual_page_length(tmp_path: Path) -> None:
    offsets = []

    def handle(request: httpx.Request) -> httpx.Response:
        skip = int(request.url.params["skip"])
        offsets.append(skip)
        resource = request.url.path.removeprefix("/")
        return httpx.Response(200, json={resource: [{"id": skip + 1}], "total": 2, "skip": skip, "limit": 2})

    settings = Settings(tmp_path / "test.duckdb", page_size=2)
    snapshot = extract_live(settings, transport=httpx.MockTransport(handle))
    assert offsets == [0, 1] * 3
    assert [record["id"] for record in snapshot["products"]] == [1, 2]


def test_transient_failures_retry_and_recover(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    statuses = iter([429, 503, 200, 200, 200])
    delays = []
    monkeypatch.setattr("ecommerce.extract.time.sleep", delays.append)

    def handle(request: httpx.Request) -> httpx.Response:
        status = next(statuses)
        resource = request.url.path.removeprefix("/")
        return httpx.Response(status, json={resource: [], "total": 0, "skip": 0, "limit": 0})

    settings = Settings(tmp_path / "test.duckdb")
    assert extract_live(settings, transport=httpx.MockTransport(handle)) == {key: [] for key in RESOURCES}
    assert delays == [0.25, 0.5]


@pytest.mark.parametrize("status", [400, 404])
def test_permanent_errors_fail_without_retry(tmp_path: Path, status: int) -> None:
    calls = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(status, text="private-response-body")

    with pytest.raises(ExtractionError, match=f"HTTP {status}") as error:
        extract_live(Settings(tmp_path / "test.duckdb"), transport=httpx.MockTransport(handle))
    assert len(calls) == 1
    assert "private-response-body" not in str(error.value)


def test_timeout_exhausts_retries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    delays = []
    monkeypatch.setattr("ecommerce.extract.time.sleep", delays.append)

    def handle(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("transport details", request=request)

    with pytest.raises(ExtractionError, match="ReadTimeout after 3 attempts"):
        extract_live(Settings(tmp_path / "test.duckdb"), transport=httpx.MockTransport(handle))
    assert delays == [0.25, 0.5]


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (b"<html>", "valid JSON"),
        (b"[]", "products.*array"),
        (b'{"products":[],"total":true,"skip":0,"limit":2}', "integer.*metadata"),
        (b'{"products":[{"id":1}],"total":2,"skip":1,"limit":2}', "invalid pagination"),
        (b'{"products":[],"total":2,"skip":0,"limit":2}', "empty before"),
        (b'{"products":[{"id":1}],"total":0,"skip":0,"limit":2}', "too many records"),
        (b'{"products":[{"id":true}],"total":1,"skip":0,"limit":2}', "positive integer ID"),
        (b'{"products":[],"total":0,"skip":0,"limit":3}', "requested limit"),
    ],
)
def test_malformed_live_pages(tmp_path: Path, body: bytes, message: str) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=body))
    with pytest.raises(ExtractionError, match=message):
        extract_live(Settings(tmp_path / "test.duckdb", page_size=2), transport=transport)


def test_reported_total_cannot_change(tmp_path: Path) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        skip = int(request.url.params["skip"])
        return httpx.Response(
            200, json={"products": [{"id": skip + 1}], "total": 2 + skip, "skip": skip, "limit": 1}
        )

    with pytest.raises(ExtractionError, match="changed the reported total"):
        extract_live(Settings(tmp_path / "test.duckdb"), transport=httpx.MockTransport(handle))


@pytest.mark.parametrize(
    ("pages", "message"),
    [
        ([], "missing the page at skip=0"),
        ([{"products": [{"id": 1}], "total": 2, "skip": 0, "limit": 1}], "missing the page at skip=1"),
        ([{"products": [], "total": 0, "skip": 0, "limit": 2}, {}], "extra pages"),
    ],
)
def test_fixture_page_sequence(tmp_path: Path, pages: list[dict], message: str) -> None:
    (tmp_path / "products.json").write_text(json.dumps(pages), encoding="utf-8")
    with pytest.raises(ExtractionError, match=message):
        extract_fixtures(tmp_path)


def test_settings_resolve_relative_path_and_read_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("WAREHOUSE_PATH", "test data/warehouse.duckdb")
    monkeypatch.setenv("DUMMYJSON_TIMEOUT_SECONDS", "2.5")
    monkeypatch.setenv("DUMMYJSON_PAGE_SIZE", "3")
    monkeypatch.setenv("DUMMYJSON_MAX_RETRIES", "0")
    assert Settings.from_env() == Settings(tmp_path / "test data" / "warehouse.duckdb", 2.5, 3, 0)


@pytest.mark.parametrize(
    ("setting", "value"),
    [
        ("WAREHOUSE_PATH", ""),
        ("DUMMYJSON_TIMEOUT_SECONDS", "nan"),
        ("DUMMYJSON_TIMEOUT_SECONDS", "oops"),
        ("DUMMYJSON_PAGE_SIZE", "0"),
        ("DUMMYJSON_MAX_RETRIES", "6"),
    ],
)
def test_settings_reject_invalid_values(
    monkeypatch: pytest.MonkeyPatch, setting: str, value: str
) -> None:
    monkeypatch.setenv(setting, value)
    with pytest.raises(ValueError, match=setting):
        Settings.from_env()

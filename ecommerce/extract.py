"""Fetch complete DummyJSON collections or replay recorded fixture pages."""

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from ecommerce.config import DUMMYJSON_URL, Settings

RESOURCES = ("products", "users", "carts")
Record = dict[str, Any]
Snapshot = dict[str, list[Record]]


class ExtractionError(RuntimeError):
    """Extraction failed before a complete snapshot was available."""


def source_id(record: object) -> int:
    """Validate the source key shared by live, fixture, and Bronze inputs."""
    key = record.get("id") if isinstance(record, dict) else None
    if type(key) is not int or not 1 <= key <= 2**63 - 1:
        raise ValueError("Each record must be a JSON object with a positive integer ID.")
    return key


def _collect_pages(
    resource: str, fetch_page: Callable[[int], object], requested_limit: int | None = None
) -> list[Record]:
    records: list[Record] = []
    expected_total = None
    while True:
        skip = len(records)
        label = f"{resource} page at skip={skip}"
        page = fetch_page(skip)
        if not isinstance(page, dict) or not isinstance(page.get(resource), list):
            raise ExtractionError(f"{label} must contain a '{resource}' array.")

        total, offset, limit = (page.get(key) for key in ("total", "skip", "limit"))
        if any(type(value) is not int for value in (total, offset, limit)):
            raise ExtractionError(f"{label} must have integer total, skip, and limit metadata.")
        if offset != skip or total < skip or limit < 0 or (limit == 0 and total != 0):
            raise ExtractionError(f"{label} has invalid pagination metadata.")
        if requested_limit is not None and limit > requested_limit:
            raise ExtractionError(f"{label} exceeds the requested limit.")
        if expected_total is not None and total != expected_total:
            raise ExtractionError(f"{label} changed the reported total during extraction.")

        batch = page[resource]
        if len(batch) > min(limit, total - skip):
            raise ExtractionError(f"{label} has too many records for its metadata.")
        if not batch and skip < total:
            raise ExtractionError(f"{label} is empty before the reported total was reached.")
        for record in batch:
            try:
                source_id(record)
            except ValueError as exc:
                raise ExtractionError(f"{label}: {exc}") from None

        records.extend(batch)
        if len(records) == total:
            return records
        expected_total = total


def _request_page(
    client: httpx.Client, resource: str, skip: int, settings: Settings
) -> object:
    label = f"{resource} page at skip={skip}"
    for attempt in range(settings.max_retries + 1):
        try:
            response = client.get(
                f"/{resource}",
                params={"limit": settings.page_size, "skip": skip},
                timeout=settings.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            reason = f"HTTP {status}"
            if status != 429 and not 500 <= status < 600:
                raise ExtractionError(f"{label} failed with {reason}.") from None
        except (
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.RemoteProtocolError,
            httpx.ProxyError,
        ) as exc:
            reason = type(exc).__name__
        except httpx.RequestError as exc:
            raise ExtractionError(f"{label} failed with {type(exc).__name__}.") from None
        else:
            try:
                return response.json()
            except ValueError:
                raise ExtractionError(f"{label} did not contain valid JSON.") from None

        if attempt == settings.max_retries:
            raise ExtractionError(f"{label} failed with {reason} after {attempt + 1} attempts.")
        time.sleep(min(0.25 * 2**attempt, 2.0))
    raise AssertionError("Unreachable with a non-negative retry count.")


def extract_live(settings: Settings, *, transport: httpx.BaseTransport | None = None) -> Snapshot:
    """Retrieve all three resources with one HTTP client."""
    snapshot: Snapshot = {}
    with httpx.Client(base_url=DUMMYJSON_URL, transport=transport) as client:
        for resource in RESOURCES:
            snapshot[resource] = _collect_pages(
                resource,
                lambda skip: _request_page(client, resource, skip, settings),
                settings.page_size,
            )
    return snapshot


def extract_fixtures(directory: Path) -> Snapshot:
    """Replay one JSON array of response pages per resource."""
    snapshot: Snapshot = {}
    for resource in RESOURCES:
        filename = f"{resource}.json"
        try:
            data = json.loads((directory / filename).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise ExtractionError(f"Cannot read {filename} as a UTF-8 JSON fixture.") from None
        if not isinstance(data, list):
            raise ExtractionError(f"{filename} must contain an array of response pages.")
        pages = iter(data)

        def next_page(skip: int) -> object:
            try:
                return next(pages)
            except StopIteration:
                raise ExtractionError(f"{filename} is missing the page at skip={skip}.") from None

        snapshot[resource] = _collect_pages(resource, next_page)
        if next(pages, ...) is not ...:
            raise ExtractionError(f"{filename} has extra pages after the reported total.")
    return snapshot

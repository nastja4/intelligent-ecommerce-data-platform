"""Replace the DuckDB Bronze snapshot and provide a Bronze-only CLI."""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import duckdb

from ecommerce.config import Settings
from ecommerce.extract import (
    RESOURCES,
    ExtractionError,
    Snapshot,
    extract_fixtures,
    extract_live,
    source_id,
)


class LoadError(RuntimeError):
    """A complete Bronze snapshot could not be loaded."""


def load_bronze(
    warehouse_path: Path, snapshot: Snapshot, *, ingested_at: datetime | None = None
) -> dict[str, int]:
    """Stage distinct source records, then replace all three tables together."""
    if set(snapshot) != set(RESOURCES):
        raise LoadError("The snapshot must contain products, users, and carts.")
    timestamp = datetime.now(UTC) if ingested_at is None else ingested_at
    if timestamp.utcoffset() is None:
        raise LoadError("The ingestion timestamp must include a timezone.")
    timestamp = timestamp.astimezone(UTC)

    staged: dict[str, dict[int, str]] = {}
    for resource in RESOURCES:
        distinct: dict[int, str] = {}
        for record in snapshot[resource]:
            try:
                key = source_id(record)
                payload = json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False)
            except (TypeError, ValueError):
                raise LoadError(f"{resource} contains an invalid source record.") from None
            if key in distinct and distinct[key] != payload:
                raise LoadError(f"{resource} contains conflicting records for source ID {key}.")
            distinct[key] = payload
        staged[resource] = distinct

    warehouse_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(warehouse_path)) as connection:
        connection.execute("BEGIN TRANSACTION")
        try:
            connection.execute("CREATE SCHEMA IF NOT EXISTS bronze")
            for resource in RESOURCES:
                # Table names come only from the fixed RESOURCES tuple.
                table = f"bronze.raw_{resource}"
                connection.execute(
                    f"""CREATE TABLE IF NOT EXISTS {table} (
                        source_id BIGINT PRIMARY KEY,
                        payload JSON NOT NULL,
                        ingested_at TIMESTAMPTZ NOT NULL
                    )"""
                )
                connection.execute(f"DELETE FROM {table}")
                if staged[resource]:
                    connection.executemany(
                        f"INSERT INTO {table} (source_id, payload, ingested_at) VALUES (?, ?, ?)",
                        [(key, payload, timestamp) for key, payload in staged[resource].items()],
                    )
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise

    return {resource: len(records) for resource, records in staged.items()}


def main(argv: list[str] | None = None) -> int:
    """Run one Bronze refresh from fixtures or DummyJSON."""
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--fixture-dir", type=Path, help="Directory containing fixture pages")
    mode.add_argument("--live", action="store_true", help="Fetch the live DummyJSON snapshot")
    args = parser.parse_args(argv)

    try:
        settings = Settings.from_env()
        snapshot = (
            extract_fixtures(args.fixture_dir)
            if args.fixture_dir is not None
            else extract_live(settings)
        )
        counts = load_bronze(settings.warehouse_path, snapshot)
    except (ValueError, ExtractionError, LoadError) as exc:
        print(f"Ingestion failed: {exc}", file=sys.stderr)
        return 1
    except (duckdb.Error, OSError) as exc:
        # Database and filesystem error details may include raw values or local paths.
        print(
            f"Ingestion failed writing the Bronze warehouse ({type(exc).__name__}). "
            "Check WAREHOUSE_PATH, file permissions, and other warehouse connections.",
            file=sys.stderr,
        )
        return 1

    print(json.dumps(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

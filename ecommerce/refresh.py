"""Build, validate, and publish a complete DuckDB warehouse."""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb

from ecommerce.config import Settings
from ecommerce.extract import RESOURCES, ExtractionError, extract_fixtures, extract_live
from ecommerce.load import LoadError, load_bronze

ANALYTICS = Path(__file__).resolve().parents[1] / "analytics"
EXPECTED_RELATIONS = {
    *((f"bronze.raw_{resource}", "BASE TABLE") for resource in RESOURCES),
    ("silver.stg_products", "VIEW"),
    ("silver.stg_users", "VIEW"),
    ("silver.stg_carts", "VIEW"),
    ("silver.stg_cart_items", "VIEW"),
    ("gold.cart_summary", "BASE TABLE"),
    ("gold.product_performance", "BASE TABLE"),
    ("gold.category_performance", "BASE TABLE"),
    ("gold.customer_performance", "BASE TABLE"),
    ("gold.inventory_alerts", "BASE TABLE"),
    ("gold.business_kpis", "BASE TABLE"),
}


class RefreshError(RuntimeError):
    """A safe, actionable warehouse refresh error."""


def _dbt_summary(target: Path) -> str:
    """Read only identifiers and counts from dbt's result artifact."""
    try:
        results = json.loads((target / "run_results.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""

    if not isinstance(results, dict) or not isinstance(results.get("results"), list):
        return ""

    failures = []
    for result in results["results"]:
        if not isinstance(result, dict) or result.get("status") not in ("fail", "error", "runtime error"):
            continue
        name = result.get("unique_id")
        if not isinstance(name, str) or not re.fullmatch(
            r"(?:test|model)\.ecommerce_analytics\.[a-zA-Z0-9_.]+", name
        ):
            continue
        count = result.get("failures")
        failures.append(f"{name} ({count} failing rows)" if type(count) is int else name)
    return " Failed dbt nodes: " + ", ".join(failures) + "." if failures else ""


def _build_candidate(candidate: Path, target: Path) -> None:
    # Ignore inherited dbt flags that could change the target or skip validation.
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("DBT_")}
    env.update(WAREHOUSE_PATH=str(candidate), DBT_SEND_ANONYMOUS_USAGE_STATS="false")
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from dbt.cli.main import cli; cli()",
                "build",
                "--project-dir", str(ANALYTICS),
                "--profiles-dir", str(ANALYTICS),
                "--target-path", str(target),
                "--log-path", str(target / "logs"),
                "--log-level-file", "none",
            ],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=120,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise RefreshError("dbt build exceeded 120 seconds.") from None
    except OSError as exc:
        raise RefreshError(f"Could not start dbt ({type(exc).__name__}).") from None
    if result.returncode:
        raise RefreshError(f"dbt build exited with code {result.returncode}." + _dbt_summary(target))


def _verify_relations(candidate: Path) -> None:
    try:
        with duckdb.connect(str(candidate), read_only=True) as connection:
            relations = set(connection.execute("""
                select table_schema || '.' || table_name, table_type
                from information_schema.tables
                where table_schema in ('bronze', 'silver', 'gold')
            """).fetchall())
    except duckdb.Error as exc:
        raise RefreshError(f"Could not inspect the candidate warehouse ({type(exc).__name__}).") from None

    missing = EXPECTED_RELATIONS - relations
    if missing:
        names = ", ".join(f"{name} ({kind})" for name, kind in sorted(missing))
        raise RefreshError(f"Expected candidate relations missing or of the wrong type: {names}.")


def _publish(candidate: Path, final: Path) -> None:
    for warehouse in (candidate, final):
        wal = warehouse.with_name(f"{warehouse.name}.wal")
        if wal.exists() or wal.is_symlink():
            raise RefreshError("A warehouse WAL is present. Close connections and recover the warehouse before retrying.")
    try:
        os.replace(candidate, final)
    except OSError as exc:
        raise RefreshError(
            f"Could not publish the candidate ({type(exc).__name__}). "
            "Stop all warehouse readers and writers and check directory permissions."
        ) from None


def _clean_candidate(candidate: Path) -> None:
    wal = candidate.with_name(f"{candidate.name}.wal")
    spill = candidate.with_name(f"{candidate.name}.tmp")
    for path in (candidate, wal, spill):
        try:
            if path == spill and path.is_dir() and path.resolve() == path and not path.is_junction():
                shutil.rmtree(path)
            else:
                path.unlink(missing_ok=True)
        except OSError:
            print("Warning: a candidate artifact could not be removed.", file=sys.stderr)


def refresh_warehouse(settings: Settings, *, fixture_dir: Path | None = None) -> dict[str, int]:
    """Publish a validated snapshot after all candidate connections close."""
    final = settings.warehouse_path.resolve()
    snapshot = extract_live(settings) if fixture_dir is None else extract_fixtures(fixture_dir)
    final.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="refresh-", dir=final.parent, ignore_cleanup_errors=True) as work:
        work_dir = Path(work)
        candidate = work_dir.with_suffix(".duckdb")
        try:
            try:
                counts = load_bronze(candidate, snapshot)
            except duckdb.Error as exc:
                raise RefreshError(f"Could not load candidate Bronze tables ({type(exc).__name__}).") from None
            print("Candidate Bronze counts: " + json.dumps(counts), file=sys.stderr)
            _build_candidate(candidate, work_dir / "target")
            _verify_relations(candidate)
            _publish(candidate, final)
        finally:
            _clean_candidate(candidate)
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--fixture-dir", type=Path, help="Build from deterministic fixtures")
    mode.add_argument("--live", action="store_true", help="Build from live DummyJSON records")
    args = parser.parse_args(argv)

    try:
        counts = refresh_warehouse(Settings.from_env(), fixture_dir=args.fixture_dir)
    except (ValueError, ExtractionError, LoadError, RefreshError) as exc:
        print(f"Refresh failed: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Refresh failed accessing warehouse files ({type(exc).__name__}).", file=sys.stderr)
        return 1

    print("Published validated warehouse: " + json.dumps(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

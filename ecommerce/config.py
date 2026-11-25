"""Resolve warehouse and ingestion settings from the environment."""

import math
import os
from dataclasses import dataclass
from pathlib import Path

DUMMYJSON_URL = "https://dummyjson.com"


def warehouse_path_from_env() -> Path:
    warehouse = os.getenv("WAREHOUSE_PATH", "data/warehouse.duckdb")
    if not warehouse.strip():
        raise ValueError("WAREHOUSE_PATH must be a non-empty file path.")
    return Path(warehouse).expanduser().resolve()


@dataclass(frozen=True)
class Settings:
    warehouse_path: Path
    timeout_seconds: float = 10.0
    page_size: int = 50
    max_retries: int = 2

    @classmethod
    def from_env(cls) -> "Settings":
        try:
            timeout = float(os.getenv("DUMMYJSON_TIMEOUT_SECONDS", "10"))
        except ValueError:
            raise ValueError("DUMMYJSON_TIMEOUT_SECONDS must be a positive number.") from None
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("DUMMYJSON_TIMEOUT_SECONDS must be a positive number.")

        return cls(
            warehouse_path=warehouse_path_from_env(),
            timeout_seconds=timeout,
            page_size=_read_int("DUMMYJSON_PAGE_SIZE", 50, 1, 100),
            max_retries=_read_int("DUMMYJSON_MAX_RETRIES", 2, 0, 5),
        )


def _read_int(name: str, default: int, minimum: int, maximum: int) -> int:
    message = f"{name} must be an integer from {minimum} to {maximum}."
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        raise ValueError(message) from None
    if not minimum <= value <= maximum:
        raise ValueError(message)
    return value

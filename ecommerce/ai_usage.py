"""Persist an atomic reservation before each Messages API call."""

import sqlite3
import time
from contextlib import closing, contextmanager
from decimal import Decimal
from pathlib import Path
from typing import Iterator

from pydantic import BaseModel, Field


class Usage(BaseModel):
    input_tokens: int = Field(ge=0, strict=True)
    output_tokens: int = Field(ge=0, strict=True)
    cache_creation_input_tokens: int = Field(default=0, ge=0, strict=True)
    cache_read_input_tokens: int = Field(default=0, ge=0, strict=True)

    def cost_units(self, five_minute_cache_tokens: int = 0) -> int:
        """Integer billionths of a dollar, using the higher cache-write rate if present."""
        total_input = self.input_tokens + self.cache_creation_input_tokens + self.cache_read_input_tokens
        tier = 5 if total_input > 100_000 else 1
        five_minute = max(0, min(five_minute_cache_tokens, self.cache_creation_input_tokens))
        price_per_million = (
            Decimal("0.10") * self.input_tokens + Decimal("0.50") * self.output_tokens
            + Decimal("0.125") * five_minute
            + Decimal("0.20") * (self.cache_creation_input_tokens - five_minute)
            + Decimal("0.01") * self.cache_read_input_tokens
        )
        return int((tier * price_per_million).scaleb(3))


def usd(units: int) -> str:
    return format(Decimal(units).scaleb(-9), ".9f")


class BudgetExceeded(Exception):
    pass


class RateExceeded(Exception):
    pass


class Ledger:
    def __init__(self, path: Path, budget: Decimal) -> None:
        self.path = path
        self.budget = int(budget.scaleb(9))

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=3)) as db, db:
            db.execute("begin immediate")
            db.execute("""
                create table if not exists calls (
                    id integer primary key, request_id text not null, model text not null,
                    timestamp real not null, units integer not null, input_tokens integer,
                    output_tokens integer, cache_creation_input_tokens integer,
                    cache_read_input_tokens integer
                )
            """)
            db.execute("create table if not exists requests (timestamp real not null)")
            yield db

    @staticmethod
    def _spent(db: sqlite3.Connection) -> int:
        return db.execute("select coalesce(sum(units), 0) from calls").fetchone()[0]

    def balances(self) -> tuple[int, int]:
        with self._transaction() as db:
            spent = self._spent(db)
        return spent, max(0, self.budget - spent)

    def admit(self, maximum: int) -> None:
        with self._transaction() as db:
            now = time.time()
            db.execute("delete from requests where timestamp <= ?", (now - 60,))
            if db.execute("select count(*) from requests").fetchone()[0] >= maximum:
                raise RateExceeded
            db.execute("insert into requests values (?)", (now,))

    def reserve(self, request_id: str, model: str, maximum: int) -> int:
        with self._transaction() as db:
            if self._spent(db) + maximum > self.budget:
                raise BudgetExceeded
            row = db.execute(
                "insert into calls (request_id, model, timestamp, units) values (?, ?, ?, ?)",
                (request_id, model, time.time(), maximum),
            )
            assert row.lastrowid is not None
            return row.lastrowid

    def settle(self, call_id: int, usage: Usage, five_minute_cache_tokens: int = 0) -> None:
        with self._transaction() as db:
            db.execute("""
                update calls set units = ?, input_tokens = ?, output_tokens = ?,
                    cache_creation_input_tokens = ?, cache_read_input_tokens = ? where id = ?
            """, (
                usage.cost_units(five_minute_cache_tokens), usage.input_tokens, usage.output_tokens,
                usage.cache_creation_input_tokens, usage.cache_read_input_tokens, call_id,
            ))

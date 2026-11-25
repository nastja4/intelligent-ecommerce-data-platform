"""Shared request constraints and analytical response models."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import AfterValidator, AwareDatetime, BaseModel, BeforeValidator, Field, StringConstraints

DEFAULT_LIMIT = 10
DEFAULT_THRESHOLD = 10
Limit = Annotated[int, Field(ge=1, le=100, description="Maximum number of ranked results.")]
Threshold = Annotated[
    int, Field(ge=0, le=10_000, description="Return products with stock strictly below this value.")
]


def _decimal_string(value: object) -> object:
    if isinstance(value, Decimal):
        return format(value, ".2f")
    return value


def _utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


Money = Annotated[
    str, StringConstraints(pattern=r"^[0-9]+\.[0-9]{2}$"), BeforeValidator(_decimal_string)
]
Count = Annotated[int, Field(ge=0)]
Item = TypeVar("Item", bound=BaseModel)


class Snapshot(BaseModel):
    snapshot_at: Annotated[AwareDatetime, AfterValidator(_utc)]
    metric_basis: Literal["gross_simulated_cart_line_value_before_discounts"] = (
        "gross_simulated_cart_line_value_before_discounts"
    )


class BusinessKpis(Snapshot):
    total_gross_cart_value: Money
    cart_count: Count
    average_cart_value: Money | None
    total_quantity: Count


class ProductPerformance(BaseModel):
    product_id: int
    title: str
    category: str
    gross_cart_value: Money
    total_quantity: Count


class CategoryPerformance(BaseModel):
    category: str
    gross_cart_value: Money
    total_quantity: Count


class CustomerPerformance(BaseModel):
    customer_id: int
    gross_cart_value: Money
    cart_count: Count


class InventoryProduct(BaseModel):
    product_id: int
    title: str
    stock: Count


class SnapshotRows(Snapshot, Generic[Item]):
    items: list[Item]


class Health(BaseModel):
    status: Literal["ok"] = "ok"

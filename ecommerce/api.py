"""Local JSON API for the published analytical snapshot."""

from typing import Annotated

import uvicorn
from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ecommerce import queries
from ecommerce.contracts import (
    DEFAULT_LIMIT,
    DEFAULT_THRESHOLD,
    BusinessKpis,
    CategoryPerformance,
    CustomerPerformance,
    Health,
    InventoryProduct,
    Limit,
    ProductPerformance,
    SnapshotRows,
    Threshold,
)


class ErrorResponse(BaseModel):
    detail: str


app = FastAPI(
    title="E-Commerce Analytics",
    version="1.0.0",
    description="Read-only analytics for the current synthetic cart snapshot.",
    responses={
        422: {"model": ErrorResponse, "description": "Invalid request parameters"},
        503: {"model": ErrorResponse, "description": "Warehouse unavailable"},
        500: {"model": ErrorResponse, "description": "Analytical query failed"},
    },
)


@app.exception_handler(RequestValidationError)
async def invalid_request(_request: Request, _error: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": "Invalid request parameters."})


@app.exception_handler(queries.QueryError)
async def query_error(_request: Request, error: queries.QueryError) -> JSONResponse:
    status = 503 if isinstance(error, queries.WarehouseUnavailable) else 500
    return JSONResponse(status_code=status, content={"detail": str(error)})


@app.exception_handler(Exception)
async def unexpected_error(_request: Request, _error: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "Analytical query failed."})


@app.get("/health")
def health() -> Health:
    queries.check_health()
    return Health()


@app.get("/api/v1/kpis")
def business_kpis() -> BusinessKpis:
    return queries.get_business_kpis()


@app.get("/api/v1/products/top")
def top_products(limit: Annotated[Limit, Query()] = DEFAULT_LIMIT) -> SnapshotRows[ProductPerformance]:
    return queries.get_top_products(limit)


@app.get("/api/v1/categories")
def categories() -> SnapshotRows[CategoryPerformance]:
    return queries.get_category_performance()


@app.get("/api/v1/customers/top")
def top_customers(limit: Annotated[Limit, Query()] = DEFAULT_LIMIT) -> SnapshotRows[CustomerPerformance]:
    return queries.get_top_customers(limit)


@app.get("/api/v1/inventory/low-stock")
def low_stock(
    threshold: Annotated[Threshold, Query()] = DEFAULT_THRESHOLD,
) -> SnapshotRows[InventoryProduct]:
    return queries.get_low_stock_products(threshold)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, access_log=False)

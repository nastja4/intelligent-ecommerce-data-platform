FROM python:3.12-slim-bookworm@sha256:44cf1793efa7c7a476bb0f2cff81443f4a072c90c1cb127e2924933daa3e8c64

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DBT_SEND_ANONYMOUS_USAGE_STATS=false \
    WAREHOUSE_PATH=/data/warehouse.duckdb

WORKDIR /app
COPY requirements.lock ./
RUN python -m pip install --no-cache-dir --require-hashes --only-binary=:all: -r requirements.lock

COPY pyproject.toml README.md ./
COPY ecommerce/ ecommerce/
RUN python -m pip install --no-cache-dir --no-deps . \
    && python -m pip check \
    && groupadd --gid 10001 ecommerce \
    && useradd --uid 10001 --gid 10001 --create-home ecommerce \
    && install -d -o ecommerce -g ecommerce -m 0755 /data \
    && install -o ecommerce -g ecommerce -m 0644 /dev/null /data/.volume-init

COPY analytics/ analytics/
COPY tests/ tests/

USER ecommerce
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "ecommerce.api:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]

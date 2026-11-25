FROM node:22.16.0-bookworm-slim@sha256:048ed02c5fd52e86fda6fbd2f6a76cf0d4492fd6c6fee9e2c463ed5108da0e34 AS frontend-build

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run typecheck && npm run build

FROM python:3.12-slim-bookworm@sha256:44cf1793efa7c7a476bb0f2cff81443f4a072c90c1cb127e2924933daa3e8c64

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DBT_SEND_ANONYMOUS_USAGE_STATS=false \
    WAREHOUSE_PATH=/data/warehouse.duckdb \
    AI_USAGE_PATH=/usage/ai-usage.sqlite3 \
    AI_ENABLED=false

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
    && install -o ecommerce -g ecommerce -m 0644 /dev/null /data/.volume-init \
    && install -d -o ecommerce -g ecommerce -m 0700 /usage \
    && install -o ecommerce -g ecommerce -m 0600 /dev/null /usage/.volume-init

COPY analytics/ analytics/
COPY tests/ tests/
COPY --from=frontend-build /build/dist/ /app/frontend/dist/

USER ecommerce
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "ecommerce.api:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--no-proxy-headers"]

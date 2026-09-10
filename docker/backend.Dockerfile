# Multi-stage Python 3.12 Dockerfile for AstraTrace Backend
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY apps/backend/pyproject.toml .
RUN pip install --no-cache-dir --prefix=/install .

# Final Runner Stage
FROM python:3.12-slim

WORKDIR /app

# Create non-root system user for security
RUN groupadd -g 1000 astragroup && \
    useradd -u 1000 -g astragroup -s /bin/bash -m astrauser

COPY --from=builder /install /usr/local

COPY apps/backend/app ./apps/backend/app
COPY apps/backend/pyproject.toml ./apps/backend/

# Ensure safe permissions
RUN chown -R astrauser:astragroup /app

USER astrauser

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    APP_ENV=production \
    OFFLINE_MODE=true

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

CMD ["uvicorn", "apps.backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

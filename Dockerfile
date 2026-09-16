# ====================================================================
# AstraTrace — Unified Fullstack Production Dockerfile
# SIH 2026 | Problem ID: SIH26227
# ====================================================================

# Stage 1: Build React/Vite Frontend
FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend

COPY apps/frontend/package*.json ./
RUN npm ci --prefer-offline --no-audit

COPY apps/frontend/ ./
RUN npm run build

# Stage 2: Build Python Backend Dependencies
FROM python:3.12-slim AS backend-builder
WORKDIR /app/backend

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY apps/backend/pyproject.toml .
RUN pip install --no-cache-dir --prefix=/install .

# Stage 3: Unified Production Runner
FROM python:3.12-slim AS runner
WORKDIR /app

# Create non-root system user for security
RUN groupadd -g 1000 astragroup && \
    useradd -u 1000 -g astragroup -s /bin/bash -m astrauser

# Copy installed Python packages from backend-builder
COPY --from=backend-builder /install /usr/local

# Copy backend application code
COPY apps/backend/app ./apps/backend/app
COPY apps/backend/pyproject.toml ./apps/backend/

# Copy compiled frontend static bundle
COPY --from=frontend-builder /app/frontend/dist ./apps/frontend/dist

# Copy curated offline Sentinel-2 data, GeoTIFF tiles, and metadata catalog
COPY data ./data

# Ensure safe file permissions
RUN chown -R astrauser:astragroup /app

USER astrauser

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    APP_ENV=production \
    OFFLINE_MODE=true \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request, os; port = os.environ.get('PORT', '8000'); urllib.request.urlopen(f'http://localhost:{port}/api/v1/health')" || exit 1

CMD ["sh", "-c", "uvicorn apps.backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

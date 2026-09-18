# AstraTrace — Cloud Production Deployment Guide
**SIH 2026 | Problem ID: SIH26227**

This document describes the production cloud architecture, configuration, and step-by-step deployment procedure for **AstraTrace** on modern cloud container platforms (Render, Railway, Fly.io, and Hugging Face Spaces).

---

## 1. Production Architecture

AstraTrace is packaged as a **self-contained, unified fullstack container** requiring zero external database instances, zero commercial API keys, and zero external object storage buckets.

```
+-------------------------------------------------------------------------+
|                         PUBLIC HTTPS INTERNET                           |
|                  https://astratrace.onrender.com                         |
+-------------------------------------------------------------------------+
                                    |
                                    v (Port 8000 / $PORT)
+-------------------------------------------------------------------------+
|                  ASTRATRACE PRODUCTION DOCKER CONTAINER                 |
|                                                                         |
|  +-----------------------------+     +-------------------------------+  |
|  |     React / Vite UI         |     |        FastAPI Backend        |  |
|  |   Static Bundle (/dist)     |<--->|       (/api/v1 endpoints)     |  |
|  |  (Mounted at / and /assets) |     | (Uvicorn ASGI Engine, Py3.12) |  |
|  +-----------------------------+     +-------------------------------+  |
|                                                      |                  |
|                                                      v                  |
|  +-------------------------------------------------------------------+  |
|  |                      BUNDLED LOCAL GEOINT STORAGE                 |  |
|  |  - SQLite Catalog (data/catalog.db, 1.88 MB)                      |  |
|  |  - Vector Index (data/processed/vector_index.npz, 130 KB)         |  |
|  |  - Sentinel-2 L2A Bitemporal Pair (T43RGM, 10.24km x 10.24km)     |  |
|  |  - 68 Georeferenced Analysis Tiles & Thumbnails (data/processed/) |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|   Security Profile: Non-root user (astrauser:1000), 100% Offline Mode   |
+-------------------------------------------------------------------------+
```

### Key Architectural Features:
1. **Single Public URL**: Evaluators access a single URL that serves both the UI and backend APIs.
2. **Zero CORS & Cross-Origin Friction**: MapLibre GL raster textures and vector overlays load directly from `/api/v1/catalog/...` on the same origin.
3. **Deterministic Demo Flow**: The real Jewar Corridor Sentinel-2 bitemporal pair (February 2023 vs. November 2024) is bundled inside the container, guaranteeing identical presentation behavior regardless of network availability.
4. **Resilient Port Binding**: Uvicorn automatically binds to `${PORT:-8000}`, adapting seamlessly across Render, Railway, Fly.io, and Cloud Run.

---

## 2. Environment Variables

All settings have safe production defaults. Sensitive secrets are **never** required.

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `APP_ENV` | String | `production` | Operational profile (`production`, `staging`, `development`). |
| `PORT` | Integer | `8000` | HTTP port provided dynamically by cloud PaaS. |
| `API_HOST` | String | `0.0.0.0` | Host interface binding. |
| `OFFLINE_MODE` | Boolean | `true` | Enforces 100% offline, air-gapped processing invariant. |
| `CORS_ORIGINS` | String | `*` | Allowed origins (comma-separated or `*` for single-domain container). |
| `DATABASE_URL` | String | `sqlite:///./data/catalog.db` | Path to local SQLite metadata database. |
| `DATA_DIR` | String | `data` | Path to local raster tiles and thumbnails. |

---

## 3. Platform Deployment Runbooks

### Option A: Render (Recommended — Free Automated HTTPS)

Render provides direct GitHub repository integration with automatic Docker builds and SSL certificates.

#### Method 1: Using `render.yaml` Blueprint (1-Click)
1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **Blueprints** $\to$ **New Blueprint Instance**.
3. Connect the GitHub repository: `https://github.com/arjunverma000005-hue/AstraTrace`.
4. Render detects the root `render.yaml` automatically.
5. Click **Apply**.
6. Render builds the Docker image and provisions a public URL: `https://astratrace.onrender.com`.

#### Method 2: Manual Web Service Setup
1. Click **New +** $\to$ **Web Service**.
2. Select **Build and deploy from a Git repository**.
3. Connect `arjunverma000005-hue/AstraTrace`.
4. Select **Docker** as the Runtime.
5. Leave the Dockerfile path as `./Dockerfile`.
6. Set Plan to **Free**.
7. Under Environment Variables, add:
   - `APP_ENV`: `production`
   - `OFFLINE_MODE`: `true`
   - `DATABASE_URL`: `sqlite:///./data/catalog.db`
   - `CORS_ORIGINS`: `*`
8. Set Health Check Path to `/api/v1/health`.
9. Click **Create Web Service**.

---

### Option B: Railway (Instant Docker Deployment)

1. Log in to [Railway](https://railway.app).
2. Click **New Project** $\to$ **Deploy from GitHub repo**.
3. Select `arjunverma000005-hue/AstraTrace`.
4. Railway automatically detects the root `Dockerfile` and injects `$PORT`.
5. Under service settings, click **Generate Domain** (e.g. `astratrace-production.up.railway.app`).

---

### Option C: Hugging Face Spaces (Permanent Free 16GB Docker Space)

1. Create a new Space on [Hugging Face Spaces](https://huggingface.co/spaces).
2. Choose **Docker** SDK (Blank).
3. Name: `astratrace`, License: `mit`.
4. Push or mirror the repository to the Space remote:
   ```bash
   git remote add space https://huggingface.co/spaces/<username>/astratrace
   git push space main
   ```
5. Hugging Face builds the Dockerfile and hosts it at `https://<username>-astratrace.hf.space`.

---

## 4. Post-Deployment Verification Checklist

Once the container finishes building and status reports **Live**:

1. **Verify Health Endpoint**:
   ```bash
   curl -s https://<your-domain>/api/v1/health
   # Expected: {"status":"healthy","app":"AstraTrace","version":"0.1.0","offline_mode":true,...}
   ```

2. **Verify System Status Endpoint**:
   ```bash
   curl -s https://<your-domain>/api/v1/status
   # Expected: {"catalog":{"scene_count":4,"tile_count":68},...}
   ```

3. **Verify Mission Control UI**:
   - Open `https://<your-domain>/` in Google Chrome or Mozilla Firefox.
   - Confirm dark tactical theme, orbital limb background, SIH 2026 header, and green air-gap pulse badge.

4. **Verify Live Operational Flow**:
   - Query: `"Find newly built structures near roads between January 2023 and January 2025"`.
   - Confirm ranked candidate cards populate the Review Queue.
   - Confirm MapLibre renders the $1024 \times 1024$ Sentinel-2 optical analysis window.
   - Toggle `T1 BEFORE • 2023-02-03` and `T2 AFTER • 2024-11-29` to inspect ground truth.
   - Open Evidence card and verify 8-step cryptographic provenance chain and change mask.

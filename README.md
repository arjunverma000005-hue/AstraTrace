# AstraTrace 🛰️
**Offline Geospatial Intelligence & Satellite Imagery Analysis Platform**

[![Smart India Hackathon 2026](https://img.shields.io/badge/SIH-2026-blue.svg)](https://www.sih.gov.in)
[![Problem ID](https://img.shields.io/badge/Problem%20ID-SIH26227-red.svg)](https://sih2026.vuce.in/ps/SIH26227)
[![Organization](https://img.shields.io/badge/Sponsor-Indian%20Army%2C%20DGIS-darkgreen.svg)](https://mod.gov.in)
[![Milestone](https://img.shields.io/badge/Milestone-1%20Foundation-green.svg)]()
[![Offline Invariant](https://img.shields.io/badge/Network-Air--Gapped%20%28Offline%29-blueviolet.svg)]()

---

## 1. What is AstraTrace?
AstraTrace is an offline, provenance-preserving geospatial intelligence (GeoINT) discovery platform developed for the **Ministry of Defence / Indian Army, Directorate General of Information Systems (DGIS)** under **SIH 2026 (Problem ID: SIH26227)**.

It enables intelligence analysts to:
- Search multi-temporal satellite archives using natural language semantics.
- Discover visually and semantically similar infrastructure across wide geographic regions (*Find Similar Sites*).
- Detect and classify structural changes over time while suppressing false alarms caused by clouds, shadows, registration errors, and seasonality.
- Cross-verify observations using multisensor evidence (fusing Sentinel-2 Optical and Sentinel-1 SAR).
- Maintain forensic chain-of-custody through an immutable, hash-chained provenance graph.
- Execute completely inside air-gapped, sovereign, network-disabled environments.

---

## 2. Current Implementation Status
- **Current Milestone:** **Milestone 1 — Foundation & Repository Setup (COMPLETED)**
- **Implemented in M1:**
  - Standard monorepo layout (`apps/backend`, `apps/frontend`, `data/`, `models/`, `docker/`, `scripts/`, `tests/`).
  - FastAPI backend entrypoint with Pydantic configuration, structured JSON logging, RFC 7807 error handling, and `/api/v1/health` + `/api/v1/status` endpoints.
  - React 18 + TypeScript + Vite frontend dashboard shell with live health indicator, error boundary, and typed API client.
  - Multi-stage Dockerfiles and `docker-compose.yml` / `offline-compose.yml` profiles.
  - Automated unit test suite and end-to-end verification script (`scripts/verify_foundation.py`).
- **Notice on Advanced Features:** Semantic retrieval (RemoteCLIP), change detection (ChangeFormer), PostGIS STAC cataloging, and multisensor fusion belong to subsequent milestones and are **NOT yet implemented in this repository**.

---

## 3. Development Prerequisites
- **Operating System:** Windows 10/11, Linux, or macOS.
- **Python:** `3.11` or `3.12` (Python 3.12.4 verified).
- **Node.js:** `v20.0.0` or later (`v22.14.0` verified).
- **npm:** `10.0.0` or later (`10.9.2` verified).
- **Docker & Docker Compose:** Optional for local development; required for containerized offline deployment.

---

## 4. Local Setup Guide

### 4.1 Clone Repository
```powershell
git clone https://github.com/arjunverma000005-hue/AstraTrace.git
cd AstraTrace
```

### 4.2 Backend Setup
```powershell
cd apps/backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # On Windows PowerShell
# source .venv/bin/activate    # On Linux/macOS

pip install -e ".[dev]"
```

### 4.3 Frontend Setup
```powershell
cd ../frontend
npm install
```

---

## 5. Running the Application

### 5.1 Start Backend Service
```powershell
cd apps/backend
.\.venv\Scripts\uvicorn apps.backend.app.main:app --reload --port 8000
```
- API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Endpoint: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

### 5.2 Start Frontend Dashboard
```powershell
cd apps/frontend
npm run dev
```
- Dashboard UI: [http://localhost:5173](http://localhost:5173)

---

## 6. Running Tests & Verification

### 6.1 Run Backend Unit Tests
```powershell
cd apps/backend
.\.venv\Scripts\pytest ../../tests/backend -v
```

### 6.2 Run Frontend Typecheck & Build
```powershell
cd apps/frontend
npm run typecheck
npm run build
```

### 6.3 Run End-to-End Foundation Verification
From project root:
```powershell
.\apps\backend\.venv\Scripts\python scripts/verify_foundation.py
```

---

## 7. Scene Ingestion & Tiling Pipeline (Milestone 2)

### 7.1 Generate Synthetic Sample Scenes
Generate two authentic bitemporal Sentinel-2 scenes (512x512, 4 bands, 10m UTM EPSG:32643):
```powershell
.\apps\backend\.venv\Scripts\python scripts/generate_sample_scenes.py
```

### 7.2 Ingest Scene via CLI
Ingest, validate CRS, slice into 256x256 tiles with 25px overlap, and generate SHA-256 provenance manifest:
```powershell
.\apps\backend\.venv\Scripts\python scripts/ingest_scene.py --source data/samples/scenes/scene_2023_01_15.tif --sensor SENTINEL-2 --acquired-at 2023-01-15T10:30:00Z
```

### 7.3 Ingest Scene via REST API
```bash
curl -X POST "http://localhost:8000/api/v1/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "source_uri": "data/samples/scenes/scene_2023_01_15.tif",
    "sensor": "SENTINEL-2",
    "collection": "demo_archive",
    "acquired_at": "2023-01-15T10:30:00Z",
    "tile_size": 256,
    "overlap": 25
  }'
```

### 7.4 Retrieve Ingestion Manifest
```bash
curl "http://localhost:8000/api/v1/ingest/manifest/scn_sentinel-2_20230115_96ed9480"
```

---

## 8. Metadata Catalog & STAC Indexing (Milestone 3)

### 8.1 Initialize Database Schema
Initializes PostgreSQL/PostGIS (or offline SQLite fallback) tables and spatial/temporal indexes:
```powershell
.\apps\backend\.venv\Scripts\python scripts/init_db.py
```

### 8.2 Register Ingested Manifest into Catalog via CLI
Consumes Milestone 2 manifests into the database with idempotent duplicate suppression:
```powershell
.\apps\backend\.venv\Scripts\python scripts/catalog_scene.py --manifest data/processed/scn_sentinel-2_20230115_96ed9480/manifest.json
```

### 8.3 Query Catalog Scenes via API
```bash
curl "http://localhost:8000/api/v1/catalog/scenes?sensor=SENTINEL-2"
```

### 8.4 Spatial Bounding Box & Temporal Tile Search
```bash
curl -X POST "http://localhost:8000/api/v1/catalog/tiles/search" \
  -H "Content-Type: application/json" \
  -d '{
    "bbox": [73.57, 18.94, 73.63, 18.99],
    "sensor": "SENTINEL-2",
    "limit": 20
  }'
```

### 8.5 Access STAC-Compatible Metadata
- STAC Root Catalog: `GET http://localhost:8000/api/v1/stac`
- STAC Collections: `GET http://localhost:8000/api/v1/stac/collections`
- STAC Items: `GET http://localhost:8000/api/v1/stac/collections/demo_archive/items`

---

## 9. Baseline Retrieval Pipeline (Milestone 4)

### 9.1 Search via Command-Line Interface (CLI)
Query the offline catalog using natural language, bounding box coordinates, and temporal ranges:
```powershell
# Search for urban structures
.\apps\backend\.venv\Scripts\python scripts/baseline_search.py --query "urban buildings" --top-k 5

# Search with spatial bounding box and temporal filters
.\apps\backend\.venv\Scripts\python scripts/baseline_search.py --query "roads near factories" --bbox 73.57 18.94 73.63 18.99 --top-k 5

# Output raw JSON with execution trace metrics
.\apps\backend\.venv\Scripts\python scripts/baseline_search.py --query "forest vegetation" --json
```

### 9.2 Search via REST API
Execute multi-factor baseline searches combining SQL spatial filtering, EuroSAT synsets, and spectral feature scoring:
```bash
curl -X POST "http://localhost:8000/api/v1/search/baseline" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "industrial warehouse storage",
    "bbox": [73.57, 18.94, 73.63, 18.99],
    "date_from": "2023-01-01T00:00:00Z",
    "date_to": "2025-01-01T00:00:00Z",
    "top_k": 5,
    "min_confidence": 0.2
  }'
```

**Response Format:**
```json
{
  "query_id": "qry_e12d2e23f927",
  "query": "industrial warehouse storage",
  "matched_vocabulary": {"Industrial": 0.85, "Residential": 0.15},
  "is_out_of_vocabulary": false,
  "total_candidates": 18,
  "returned_results": 5,
  "results": [
    {
      "rank": 1,
      "tile_id": "scn_sentinel-2_20241222_7acad713_t0005",
      "baseline_score": 0.5420,
      "score_breakdown": {
        "class_score": 0.245,
        "spatial_score": 1.0,
        "temporal_score": 0.98
      },
      "top_class": "Industrial",
      "top_class_confidence": 0.32,
      "matched_classes": ["Industrial"],
      "bounds_wgs84": [73.57, 18.94, 73.63, 18.99],
      "geometry": {"type": "Polygon", "coordinates": [...]},
      "checksum": "...",
      "acquired_at": "2024-12-22T10:30:00"
    }
  ],
  "execution_trace": {
    "query_parser_ms": 0.2,
    "retrieval_ms": 41.1,
    "scoring_ms": 297.7,
    "total_ms": 339.0
  }
}
```

---

## 10. Offline-First Principles
AstraTrace enforces complete air-gap readiness:
- Zero runtime external cloud API dependencies (no OpenAI, Gemini, or external hosted services).
- Self-contained Docker offline profile (`docker/offline-compose.yml`) configures `internal: true` network mesh dropping outbound traffic.
- Pre-staged datasets and local Safetensors model checkpoints.

---

## 11. License
Apache 2.0 License. Developed for Smart India Hackathon 2026.


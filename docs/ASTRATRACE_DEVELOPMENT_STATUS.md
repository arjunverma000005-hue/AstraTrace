# AstraTrace — Development Status Tracker
**Project:** AstraTrace  
**SIH Problem ID:** SIH26227  
**Sponsor:** Ministry of Defence / Indian Army, Directorate General of Information Systems (DGIS)  
**Last Updated:** 2026-09-11 (Milestone 5 Completion)

---

## 1. Milestone Progress Overview

```
┌──────────┬───────────────────────────────────────────┬─────────────┬────────────────────────────────────┐
│ Milestone│ Description                               │ Status      │ Completion Evidence / Deliverables │
├──────────┼───────────────────────────────────────────┼─────────────┼────────────────────────────────────┤
│ M1       │ Foundation & Repository Setup             │ COMPLETED   │ apps/backend, apps/frontend, tests │
│ M2       │ Data Ingestion & Preprocessing            │ COMPLETED   │ IngestionService, CLI, API, tests  │
│ M3       │ Metadata Catalog & Database Indexing      │ COMPLETED   │ PostGIS DDL, SQLite, STAC, API     │
│ M4       │ Baseline Retrieval Pipeline               │ COMPLETED   │ Vocabulary, Scorer, Search API/CLI │
│ M5       │ Baseline Change Detection Pipeline        │ COMPLETED   │ Detector, Morphology, API, CLI, tests │
│ M6       │ Advanced Embeddings & Semantic Search     │ PLANNED     │ Scheduled for Day 6                │
│ M7       │ Quality Gate & False-Alarm Suppression    │ PLANNED     │ Scheduled for Day 7                │
│ M8       │ Backend Search APIs & MapLibre UI         │ PLANNED     │ Scheduled for Day 8                │
│ M9       │ Provenance Graph & Offline Hardening      │ PLANNED     │ Scheduled for Day 9                │
│ M10      │ Automated Evaluation & SIH Presentation   │ PLANNED     │ Scheduled for Day 10               │
└──────────┴───────────────────────────────────────────┴─────────────┴────────────────────────────────────┘
```

---

## 2. Component Implementation Status

### 2.1 Backend (`apps/backend`)
- [x] **FastAPI Application Factory:** Implemented in `app/main.py` with CORS and request tracing middleware.
- [x] **Configuration Management:** Implemented in `app/config.py` with Pydantic Settings and strict environment validation.
- [x] **Structured Logging:** Implemented in `app/core/logging.py` with JSON formatting, request ID injection, and sensitive token scrubbing.
- [x] **Error Handling:** Implemented in `app/core/errors.py` with RFC 7807 problem details.
- [x] **Health & Status Endpoints:** Implemented in `app/api/v1/router.py` serving `/health` and `/status`.
- [x] **Scene Ingestion Router:** Implemented in `app/api/v1/router.py` serving `POST /api/v1/ingest` and `GET /api/v1/ingest/manifest/{scene_id}`.
- [x] **Ingestion & Tiling Service:** Implemented in `app/services/ingestion.py` (Rasterio GeoTIFF parsing, sliding-window tiling, quality metrics, SHA-256 lineage manifests).
- [x] **Ingestion Schemas:** Implemented in `app/schemas/ingest.py` (Pydantic models with sensor validation and coordinate bounds).
- [x] **Database Session & Engine:** Implemented in `app/db/session.py` (SQLAlchemy 2.0 engine, connection pooling, SQLite WAL + foreign keys, PostgreSQL support).
- [x] **Catalog Models:** Implemented in `app/models/catalog.py` (`SceneRecord` and `TileRecord` with WKT and GeoJSON polygon serialization).
- [x] **Catalog Schemas:** Implemented in `app/schemas/catalog.py` and `app/schemas/stac.py` (STAC Collections and Items).
- [x] **Catalog Service:** Implemented in `app/services/catalog.py` (Idempotent manifest registration, spatial bounding box queries, temporal queries, STAC serialization).
- [x] **Catalog & STAC Endpoints:** Implemented in `app/api/v1/endpoints/catalog.py` and `app/api/v1/endpoints/stac.py`.
- [x] **Baseline Search Router & Service:** Implemented in `app/services/retrieval/` and `app/api/v1/endpoints/search.py` serving `POST /api/v1/search/baseline`.
- [x] **EuroSAT Controlled Vocabulary:** Implemented in `app/services/retrieval/vocabulary.py` with synset resolution.
- [x] **Tile Feature Classifier & Scorer:** Implemented in `app/services/retrieval/baseline_classifier.py` and `baseline_scorer.py` (NDVI, NDWI, Brightness, Texture, IoU, Temporal recency).
- [x] **Baseline Search CLI:** Implemented in `scripts/baseline_search.py`.
- [x] **Change Differencing & Otsu:** Implemented in `app/services/change/differencing.py` (Normalized Euclidean distance $\Delta \mathbf{S} \in [0, 1]$, index deltas $\Delta \text{NDVI}, \Delta \text{NDWI}, \Delta \text{Brightness}$, adaptive Otsu $[0.15, 0.65]$).
- [x] **Pure NumPy Morphology:** Implemented in `app/services/change/morphology.py` (Binary erosion, dilation, opening, closing, 8-connectivity BFS connected component area filter).
- [x] **Baseline Change Detector:** Implemented in `app/services/change/detector.py` (Validation, masking, Otsu thresholding, morphology, physical taxonomy classification, PNG mask export).
- [x] **Change Detection Service & REST Endpoints:** Implemented in `app/services/change/service.py`, `app/schemas/change.py`, and `app/api/v1/endpoints/change.py` (`POST /api/v1/change/detect`, `POST /api/v1/change/scene-pair`, `GET /api/v1/change/mask/{change_id}`).
- [x] **Change Detection CLI:** Implemented in `scripts/detect_change.py` with single tile pair and batch scene pairing.
- [ ] *Analyst Review Router:* PLANNED (Milestone 8).

### 2.2 Frontend (`apps/frontend`)
- [x] **React 18 & TypeScript Shell:** Implemented in `src/App.tsx` with SIH badges and layout.
- [x] **API Client:** Implemented in `src/api/client.ts` with typed `/api/v1/health` invocation.
- [x] **Live Health Card:** Implemented in `src/components/HealthCard.tsx`.
- [x] **Error Boundary:** Implemented in `src/components/ErrorBoundary.tsx`.
- [ ] *MapLibre GL JS Map Viewer:* PLANNED (Milestone 8).
- [ ] *Bitemporal Swipe / Overlay Viewer:* PLANNED (Milestone 8).
- [ ] *Analyst Review Queue:* PLANNED (Milestone 8).

### 2.3 Data & Storage
- [x] **Directory Hierarchy:** Established `data/raw/`, `data/processed/`, `data/samples/`.
- [x] **Sample Fixture:** Created `data/samples/sample_metadata.json`.
- [x] **GeoTIFF Scene Storage:** Implemented in `data/processed/{scene_id}/` storing georeferenced tiles and `manifest.json`.
- [x] **Synthetic Bitemporal Sentinel-2 Scenes:** Generated via `scripts/generate_sample_scenes.py` at `data/samples/scenes/` (512x512, 4 bands B2/B3/B4/B8, 10m UTM EPSG:32643).
- [x] **Database Catalog Storage:** Implemented in `data/catalog.db` (local SQLite catalog) and `sql/init_postgis.sql` (production PostgreSQL/PostGIS DDL).
- [x] **Change Mask Artifact Storage:** Implemented at `data/processed/changes/{change_id}_mask.png`.
- [ ] *MinIO S3 Service:* PLANNED (Milestone 7).

### 2.4 Models & AI/ML
- [x] **Model Weights Directory:** Established `models/` placeholder with `.gitkeep` and gitignore rules.
- [x] **Baseline Feature Extractor:** Multi-spectral physics baseline + pluggable ResNet-50 hook.
- [x] **Baseline Change Detector:** Physics-based multispectral difference engine ($\Delta \mathbf{S}$, Otsu, morphology).
- [ ] *RemoteCLIP ViT-B/32 Weights:* PLANNED (Milestone 6).
- [ ] *ChangeFormer-lite Weights:* PLANNED (Milestone 6).
- [ ] *Quantized SLM GGUF Weights:* PLANNED (Milestone 6).

### 2.5 Infrastructure & Docker
- [x] **Multi-stage Backend Dockerfile:** Implemented in `docker/backend.Dockerfile`.
- [x] **Multi-stage Frontend Dockerfile:** Implemented in `docker/frontend.Dockerfile`.
- [x] **Local Development Compose:** Implemented in `docker/docker-compose.yml`.
- [x] **Air-Gapped Offline Compose:** Implemented in `docker/offline-compose.yml` (`internal: true`).
- [x] **PostgreSQL/PostGIS DDL:** Implemented in `sql/init_postgis.sql` and `sql/migrations/001_initial_catalog.sql`.

### 2.6 Tests & Quality
- [x] **Backend Health Tests:** Implemented in `tests/backend/test_health.py` (4 tests passing).
- [x] **Backend Config Tests:** Implemented in `tests/backend/test_config.py` (3 tests passing).
- [x] **Backend Ingestion Tests:** Implemented in `tests/backend/test_ingestion.py` (10 tests passing).
- [x] **Backend Catalog & STAC Tests:** Implemented in `tests/backend/test_catalog.py` (10 tests passing).
- [x] **Backend Baseline Retrieval Tests:** Implemented in `tests/backend/test_retrieval.py` (14 tests passing).
- [x] **Backend Change Detection Tests:** Implemented in `tests/backend/test_change_detection.py` (17 tests passing).
- [x] **Total Pytest Suite:** 58/58 tests passing in 10.12s.
- [x] **Frontend TypeScript & Build:** `tsc --noEmit` passing with 0 errors.
- [x] **Automated Verification Script:** Implemented in `scripts/verify_foundation.py` covering M1 to M5 (8/8 suites passing).

---

## 3. Blockers & Risks
- **Current Blockers:** ZERO.
- **Active Operational Risk:** Docker CLI is not installed on the Windows host PATH; all host execution and testing utilize native Python 3.12 and Node.js v22. Containerized profiles and PostGIS DDL scripts are packaged and verified syntactically.



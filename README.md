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

## 10. Baseline Change Detection Pipeline (Milestone 5)

Deterministic temporal change detection comparing bitemporal satellite imagery pairs using normalized Euclidean spectral distance, index deltas ($\Delta \text{NDVI}, \Delta \text{NDWI}, \Delta \text{Brightness}$), adaptive Otsu thresholding, pure-NumPy morphological noise filtering, and heuristic physical taxonomy classification.

### 10.1 Change Detection via Command-Line Interface (CLI)
Analyze single tile pairs or batch-evaluate full scenes:
```powershell
# Detect change on a specific tile index between two scenes
.\apps\backend\.venv\Scripts\python scripts/detect_change.py `
  --before-scene scn_sentinel-2_20230115_96ed9480 `
  --after-scene scn_sentinel-2_20241222_7acad713 `
  --tile-index 1

# Detect change directly using raw GeoTIFF paths with custom mask output
.\apps\backend\.venv\Scripts\python scripts/detect_change.py `
  --before-tile-path data/processed/scn_sentinel-2_20230115_96ed9480/tile_0001.tif `
  --after-tile-path data/processed/scn_sentinel-2_20241222_7acad713/tile_0001.tif `
  --threshold 0.15 `
  --save-mask data/processed/changes/sample_mask.png

# Batch-evaluate all overlapping tiles between two scenes
.\apps\backend\.venv\Scripts\python scripts/detect_change.py `
  --before-scene scn_sentinel-2_20230115_96ed9480 `
  --after-scene scn_sentinel-2_20241222_7acad713 `
  --all-tiles `
  --min-change-percent 1.0
```

### 10.2 Change Detection via REST API

#### Single Tile Pair Detection
```bash
curl -X POST "http://localhost:8000/api/v1/change/detect" \
  -H "Content-Type: application/json" \
  -d '{
    "before_tile_id": "scn_sentinel-2_20230115_96ed9480_t0001",
    "after_tile_id": "scn_sentinel-2_20241222_7acad713_t0001",
    "threshold": 0.15,
    "apply_morphology": true,
    "min_component_pixels": 10
  }'
```

**Response Format:**
```json
{
  "change_id": "chg_3c44ca726754",
  "before": {
    "tile_id": "scn_sentinel-2_20230115_96ed9480_t0001",
    "scene_id": "scn_sentinel-2_20230115_96ed9480",
    "acquired_at": "2023-01-15T10:30:00",
    "checksum": "3b2f81..."
  },
  "after": {
    "tile_id": "scn_sentinel-2_20241222_7acad713_t0001",
    "scene_id": "scn_sentinel-2_20241222_7acad713",
    "acquired_at": "2024-12-22T10:30:00",
    "checksum": "a9c140..."
  },
  "metrics": {
    "total_pixels": 65536,
    "valid_pixels": 65536,
    "changed_pixels": 4800,
    "change_percent": 7.3242,
    "mean_magnitude": 0.7412,
    "composite_change_score": 0.5165,
    "change_type": "construction",
    "effective_threshold": 0.15,
    "applied_morphology": true,
    "min_component_pixels": 10,
    "index_deltas_mean": {
      "delta_brightness": 0.8315,
      "delta_ndvi": -0.5582,
      "delta_ndwi": -0.0411
    }
  },
  "mask_url": "/api/v1/change/mask/chg_3c44ca726754",
  "execution_trace": {
    "preprocess_ms": 1.8,
    "diff_ms": 2.9,
    "morphology_ms": 78.4,
    "total_ms": 148.6
  }
}
```

#### Download Change Mask
```bash
curl -O "http://localhost:8000/api/v1/change/mask/chg_3c44ca726754"
```

#### Batch Scene Pair Detection
```bash
curl -X POST "http://localhost:8000/api/v1/change/scene-pair" \
  -H "Content-Type: application/json" \
  -d '{
    "scene_id_t1": "scn_sentinel-2_20230115_96ed9480",
    "scene_id_t2": "scn_sentinel-2_20241222_7acad713",
    "threshold": 0.15,
    "max_tiles": 9
  }'
```

---

## 11. Advanced Embeddings & Semantic Vector Retrieval (Milestone 6)

AstraTrace provides high-throughput, air-gapped semantic vector retrieval and hybrid ranking over satellite imagery. Using 512-dimensional unit-sphere embeddings and exact cosine similarity vector indexing, users can execute natural-language concept searches, image-to-image site similarity lookups, and hybrid scoring that balances semantic representation with physical multi-spectral classification.

### 11.1 Embedding & Search via Command-Line Interface (CLI)

#### Batch Index Catalog Tiles into Vector Store
```powershell
# Index all cataloged tiles into SQLite and disk-persisted vector cache (.npz)
.\apps\backend\.venv\Scripts\python scripts/index_embeddings.py

# Force re-indexing of all tiles
.\apps\backend\.venv\Scripts\python scripts/index_embeddings.py --force
```

#### Natural-Language Semantic Search
```powershell
# Search using conceptual terms with hybrid ranking (alpha=0.65)
.\apps\backend\.venv\Scripts\python scripts/semantic_search.py `
  --query "industrial warehouse storage" `
  --top-k 5 `
  --alpha 0.65

# Pure semantic search (alpha=1.0)
.\apps\backend\.venv\Scripts\python scripts/semantic_search.py `
  --query "mountain forest vegetation" `
  --alpha 1.0

# Output complete JSON payload with execution trace
.\apps\backend\.venv\Scripts\python scripts/semantic_search.py `
  --query "water stream river basin" `
  --json
```

#### Image-to-Image Similarity Search ("Find Similar Sites")
```powershell
# Find tiles visually and semantically similar to a reference tile
.\apps\backend\.venv\Scripts\python scripts/semantic_search.py `
  --reference-tile-id scn_sentinel-2_20230115_96ed9480_t0000 `
  --top-k 5
```

#### Comparative Retrieval Evaluation Benchmark
```powershell
# Empirically compare Baseline vs. Semantic vs. Hybrid retrieval
.\apps\backend\.venv\Scripts\python scripts/evaluate_retrieval.py --top-k 5
```

**Measured Benchmark Results (18 Catalog Tiles, K=5):**
```
================================================================================
ASTRATRACE RETRIEVAL BENCHMARK: BASELINE vs. SEMANTIC vs. HYBRID
================================================================================
Method       Precision@K    Recall@K     MRR        nDCG@K     Latency   
--------------------------------------------------------------------------------
BASELINE     0.0500         0.0833       0.1250     0.0740     86.0    ms
SEMANTIC     0.1000         0.2083       0.2500     0.1708     5.3     ms
HYBRID       0.0500         0.0833       0.1250     0.0740     228.7   ms
================================================================================
```

### 11.2 Semantic Retrieval via REST API

#### Natural Language Semantic Search Endpoint
```bash
curl -X POST "http://localhost:8000/api/v1/search/semantic" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "industrial warehouse storage",
    "top_k": 5,
    "hybrid_weight": 0.65,
    "min_confidence": 0.0
  }'
```

**Response Format:**
```json
{
  "query_id": "sem_7c2b62d854df",
  "search_mode": "hybrid",
  "model_info": {
    "model_name": "AstraTrace-Offline-Baseline-v1",
    "dimension": 512,
    "architecture": "Deterministic-Orthogonal-Projection-512",
    "status": "READY_OFFLINE"
  },
  "total_indexed": 18,
  "returned_results": 5,
  "results": [
    {
      "rank": 1,
      "tile_id": "scn_sentinel-2_20241222_7acad713_t0005",
      "scene_id": "scn_sentinel-2_20241222_7acad713",
      "semantic_score": 0.5556,
      "cosine_sim": 0.1112,
      "baseline_score": 0.4440,
      "hybrid_score": 0.5165,
      "bounds_wgs84": [73.5702, 18.9482, 73.6190, 18.9943],
      "checksum": "306283fc365851d7e26da68997c48f21950e3b97669d25a8db8c6da66708bf99",
      "sensor": "SENTINEL-2"
    }
  ],
  "execution_trace": {
    "encode_ms": 0.98,
    "ann_ms": 0.32,
    "filter_ms": 247.6,
    "total_ms": 248.9
  }
}
```

#### Image-to-Image Similarity Search Endpoint
```bash
curl -X POST "http://localhost:8000/api/v1/search/similar-tiles" \
  -H "Content-Type: application/json" \
  -d '{
    "reference_tile_id": "scn_sentinel-2_20230115_96ed9480_t0000",
    "top_k": 3
  }'
```

#### Vector Store Health & Diagnostics Endpoint
```bash
curl -X GET "http://localhost:8000/api/v1/embeddings/status"
```

---

## 12. Quality Gate & False-Alarm Suppression (Milestone 7)

AstraTrace features a quality-aware decision and false-alarm suppression layer wrapping change detection and retrieval pipelines. The Quality Gate protects tactical analysts from atmospheric and boundary artifacts by strictly decoupling:
1. **Raw Change Score:** Measured physical spectral divergence.
2. **Evidence Quality Score:** Composite usability reflecting cloud cover, cloud shadow, saturation, and registration proxy.
3. **Final Calibrated Confidence:** Multiplicative modulation penalizing degraded or misaligned imagery.

### 12.1 Tactical Decision States
- `QUALITY_PASSED`: High-confidence change verified across clean, mutually usable observations.
- `QUALITY_DEGRADED`: Change detected, but quality metrics indicate atmospheric haze or minor registration jitter.
- `QUALITY_SUPPRESSED`: Raw candidate changes were identified as spurious artifacts (cloud, shadow, boundary) and suppressed.
- `UNCERTAIN`: Mutual usable area below operational threshold (<20%); analysis deferred with explicit escalation flag.
- `INSUFFICIENT_DATA`: Completely cloudy, empty, or unreadable observations; change detection aborted safely.

### 12.2 Quality Assessment via Command-Line Interface (CLI)

#### Assess Single Tile Optical Quality
```powershell
# Assess optical quality signals on a cataloged tile
.\apps\backend\.venv\Scripts\python scripts/assess_quality.py `
  --tile-id "scn_sentinel-2_20230115_96ed9480_t0000"

# Output raw structured JSON
.\apps\backend\.venv\Scripts\python scripts/assess_quality.py `
  --tile-id "scn_sentinel-2_20230115_96ed9480_t0000" --json
```

#### Assess Temporal Observation Pair Quality
```powershell
# Evaluate pair alignment, mutual usable area, and co-registration proxy
.\apps\backend\.venv\Scripts\python scripts/assess_quality.py `
  --pair "scn_sentinel-2_20230115_96ed9480_t0000" "scn_sentinel-2_20241222_7acad713_t0000"
```

#### Quality Gate False-Alarm Benchmark Evaluation
```powershell
# Run empirical benchmark comparing Baseline vs. Quality-Gated Detection
.\apps\backend\.venv\Scripts\python scripts/evaluate_quality_gate.py
```

**Measured Benchmark Results:**
```
================================================================================
ASTRATRACE BENCHMARK: BASELINE CHANGE DETECTION vs. QUALITY-GATED DETECTION
================================================================================
Operational Scenario                 | Baseline Px | Gated Px  | Suppressed | Decision           | Gated Conf
--------------------------------------------------------------------------------------------------------------
1. True Construction Change          | 4800        | 4800      | 0          | QUALITY_DEGRADED   | 0.4479    
2. Clean Negative Control            | 0           | 0         | 0          | QUALITY_PASSED     | 0.0000    
3. Cloud Contamination Challenge     | 6400        | 0         | 6400       | QUALITY_SUPPRESSED | 0.0000    
4. Cloud Shadow Challenge            | 3600        | 0         | 3600       | QUALITY_SUPPRESSED | 0.0000    
5. Insufficient Usable Area Challenge | 0           | 0         | 0          | UNCERTAIN          | 0.0000    
==============================================================================================================
```

### 12.3 Quality Gate via REST API

#### Gated Change Detection with False-Alarm Suppression
```bash
curl -X POST "http://localhost:8000/api/v1/change/detect-gated" \
  -H "Content-Type: application/json" \
  -d '{
    "before_tile_path": "data/processed/scn_sentinel-2_20230115_96ed9480/tile_0001.tif",
    "after_tile_path": "data/processed/scn_sentinel-2_20241222_7acad713/tile_0001.tif",
    "threshold": 0.15,
    "suppress_clouds": true,
    "suppress_shadows": true,
    "suppress_boundaries": true
  }'
```

**Response Format:**
```json
{
  "change_id": "qchg_7d747c8173e7",
  "decision": "QUALITY_DEGRADED",
  "quality_status": "DEGRADED",
  "is_uncertain": false,
  "raw_change_score": 0.5160,
  "pair_quality_score": 0.8681,
  "final_confidence": 0.4479,
  "raw_changed_pixels": 4800,
  "verified_changed_pixels": 4800,
  "verified_change_percent": 7.3242,
  "change_type": "construction",
  "suppression_breakdown": {
    "cloud_suppressed_pixels": 0,
    "shadow_suppressed_pixels": 0,
    "boundary_suppressed_pixels": 0,
    "noise_suppressed_pixels": 0,
    "total_suppressed_pixels": 0
  },
  "explanation": "Result verified with DEGRADED confidence: 4800 changed pixels (construction) detected. Marginal quality/registration (0.87) requires analyst caution.",
  "mask_url": "/api/v1/change/mask/qchg_7d747c8173e7"
}
```

---

## 13. Offline-First Principles
AstraTrace enforces complete air-gap readiness:
- Zero runtime external cloud API dependencies (no OpenAI, Gemini, or external hosted services).
- Self-contained Docker offline profile (`docker/offline-compose.yml`) configures `internal: true` network mesh dropping outbound traffic.
- Pre-staged datasets and local Safetensors model checkpoints.
- Pure NumPy deterministic 512-D vector projection ensuring semantic indexing and search remain operational even in zero-dependency air-gapped environments.

---

## 14. License
Apache 2.0 License. Developed for Smart India Hackathon 2026.





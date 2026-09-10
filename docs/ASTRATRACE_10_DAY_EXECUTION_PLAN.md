# AstraTrace — 10-Day Milestone Execution Plan & Roadmap
**Project:** AstraTrace  
**SIH Problem ID:** SIH26227  
**Document Type:** Daily Engineering Milestone Plan & Risk Contingency Guide  
**Status:** APPROVED (Baseline Execution Schedule)

---

## 1. Engineering Governance & Team Allocation

AstraTrace is structured as a disciplined 10-day sprint executed by a balanced six-person student engineering team. Every day has a singular technical objective, strict acceptance criteria, identified failure risks, and an immediate fallback plan.

### Team Role Allocation:
- **Member 1 (Lead & System Architect):** Architecture integrity, ADR compliance, CI/CD, offline Docker profiling, demo orchestration.
- **Member 2 (Geospatial & Data Engineer):** Scene download manifests, GDAL/Rasterio pipeline, reprojection, tiling, COG generation, MinIO storage.
- **Member 3 (ML Engineer 1 — Retrieval & Embeddings):** RemoteCLIP integration, ResNet-50 baseline, pgvector indexing, FAISS similarity search.
- **Member 4 (ML Engineer 2 — Change Detection & Quality):** ChangeFormer-lite, spectral differencing, quality gate filters, multisensor agreement.
- **Member 5 (Backend & Database Engineer):** FastAPI application, PostgreSQL/PostGIS schema, Pydantic contracts, audit logging, local SLM parser.
- **Member 6 (Frontend & Visualization Engineer):** React, TypeScript, MapLibre GL JS mapping, Deck.gl overlays, review queue UI, evidence dossier display.

---

## 2. Daily Milestone Breakdown (Days 1 to 10)

```
┌───────┬───────────────────────────────┬───────────────────────────────────────────────────────────────┐
│ Day   │ Milestone Name                │ Primary Deliverable                                           │
├───────┼───────────────────────────────┼───────────────────────────────────────────────────────────────┤
│ Day 1 │ Scope, Architecture & Data    │ Frozen schema, repository setup, public scene manifests.      │
│ Day 2 │ Ingestion & Preprocessing     │ GeoTIFF/COG ingestion, validation, and tiling pipeline.       │
│ Day 3 │ Database & Metadata Catalog   │ PostgreSQL + PostGIS + pgvector tables with spatial indexes.  │
│ Day 4 │ Baseline Retrieval            │ Metadata SQL filter + ResNet-50 keyword retrieval working.    │
│ Day 5 │ Baseline Change Detection     │ NDVI/NDWI differencing + morphological change masks working.  │
│ Day 6 │ Advanced Semantic Retrieval   │ RemoteCLIP text-to-tile search & FAISS similarity functional. │
│ Day 7 │ Quality Gate & False Alarms   │ Cloud, shadow, NoData, and misregistration filtering active.  │
│ Day 8 │ Backend APIs & MapLibre UI    │ End-to-end web interface with query input and review queue.   │
│ Day 9 │ Provenance & Offline Docker   │ Append-only audit trail, Docker offline profile verified.     │
│ Day 10│ Evaluation, Benchmark & Demo  │ Automated evaluation report, live demo script, presentation.  │
└───────┴───────────────────────────────┴───────────────────────────────────────────────────────────────┘
```

---

## 3. Daily Detailed Milestone Plans

### Day 1: Scope, Architecture & Data Manifest Freeze
- **Deliverables:** Initialized repository skeleton, committed architecture documentation, pre-staged public Sentinel-1 and Sentinel-2 scene manifests.
- **Dependencies:** Access to git repository and development workstations.
- **Acceptance Criteria:** `docs/` committed; directory structure matching developer guide created; dataset manifest lists at least 4 temporal scene pairs.
- **Major Risk:** Disagreement on model selections or scope.
- **Fallback Plan:** Enforce approved ADR-001 through ADR-010 without deviation.

---

### Day 2: Ingestion & Raster Preprocessing Pipeline
- **Deliverables:** `scripts/ingest_scene.py` capable of reading GeoTIFFs, validating CRS, generating 256x256 tiles with 10% overlap, and storing SHA-256 hashes.
- **Dependencies:** GDAL and Rasterio environment setup.
- **Acceptance Criteria:** Successfully ingest a Sentinel-2 L2A scene, generate 64+ valid GeoTIFF tiles, and output tile manifest JSON.
- **Major Risk:** GDAL C-library installation failures on local development machines.
- **Fallback Plan:** Standardize all GDAL execution inside Docker containers using official `osgeo/gdal` base images.

---

### Day 3: Database & Metadata Catalog
- **Deliverables:** PostgreSQL 16 container running PostGIS and pgvector; Alembic migrations for `scenes`, `tiles`, `embeddings`, `change_events`, `reviews`, `audit_events`.
- **Dependencies:** Day 2 tile manifests.
- **Acceptance Criteria:** Ingested scene and tile metadata inserted into PostgreSQL; spatial query (`ST_Intersects`) returns correct tiles in <10ms.
- **Major Risk:** Database container configuration issues on host OS.
- **Fallback Plan:** Provide local SQLite/SpatiaLite development fallback while debugging Docker PostgreSQL.

---

### Day 4: Baseline Retrieval Pipeline
- **Deliverables:** Structured spatial and temporal SQL retrieval combined with ResNet-50 keyword label matching.
- **Dependencies:** Populated database catalog from Day 3.
- **Acceptance Criteria:** Query for `"urban"` within a bounding box returns matching baseline tiles ranked by keyword score in <500ms.
- **Major Risk:** Semantic gap in simple keyword matching.
- **Fallback Plan:** Controlled vocabulary mapping table linking queries to EuroSAT classes.

---

### Day 5: Baseline Change Detection Pipeline
- **Deliverables:** Deterministic bitemporal change detection script computing spectral difference, NDVI delta, and morphological cleanup.
- **Dependencies:** Co-registered bitemporal tile pairs from Day 2.
- **Acceptance Criteria:** Generates binary change mask PNG highlighting major surface shifts between $T_1$ and $T_2$ observations.
- **Major Risk:** High noise and false positives along agricultural field boundaries.
- **Fallback Plan:** Increase minimum connected component threshold to 20 pixels and apply Otsu adaptive thresholding.

---

### Day 6: Advanced Semantic Retrieval & Vector Indexing
- **Deliverables:** RemoteCLIP (ViT-B/32) integration; feature extraction script populating `embeddings` table; hybrid pgvector HNSW search.
- **Dependencies:** Downloaded RemoteCLIP weights.
- **Acceptance Criteria:** Natural language query `"industrial warehouses"` returns semantically relevant satellite tiles in top 5 results in <1.5s.
- **Major Risk:** Heavy VRAM consumption during batch embedding generation.
- **Fallback Plan:** Batch size set to 1; execute inference with FP16 precision or CPU fallback.

---

### Day 7: Quality Gate & False-Alarm Suppression Engine
- **Deliverables:** Quality filter inspecting cloud masks (Sentinel-2 SCL), shadow projections, NoData bounds, and misregistration residuals.
- **Dependencies:** Change detection outputs from Day 5/6.
- **Acceptance Criteria:** Synthetic cloud and shadow tiles correctly flagged as `likely_artifact` or `insufficient_quality`; false alerts suppressed.
- **Major Risk:** Over-filtering genuine changes.
- **Fallback Plan:** Expose quality threshold parameters in `.env` configuration for rapid calibration.

---

### Day 8: Backend APIs & MapLibre GL JS Analyst UI
- **Deliverables:** FastAPI application serving `/api/v1/search`, `/api/v1/reviews`; React frontend with interactive MapLibre map, bounding-box selector, before/after swipe viewer, and review queue.
- **Dependencies:** Functional backend endpoints and MapLibre components.
- **Acceptance Criteria:** Analyst can enter a text query, view ranked results on the map, inspect bitemporal evidence, and click `Confirm`/`Reject`.
- **Major Risk:** Complex state management delays between map and review queue.
- **Fallback Plan:** Keep UI strictly functional with TanStack Query and standard Tailwind modal dialogs.

---

### Day 9: Provenance, Audit Trail & Offline Docker Hardening
- **Deliverables:** Append-only audit logging with hash chaining; exportable evidence dossier script; `infrastructure/offline-compose.yml` verified with network egress disabled.
- **Dependencies:** Working backend and frontend.
- **Acceptance Criteria:** Analyst adjudication generates immutable audit records; entire system boots and executes search offline with network disabled.
- **Major Risk:** Hidden external CDN links in frontend (e.g. Google Fonts, Mapbox styles).
- **Fallback Plan:** Bundle all font and basemap vector tile assets locally into the frontend container.

---

### Day 10: Benchmark Evaluation, Regression Check & Presentation Polish
- **Deliverables:** `scripts/run_evaluation.py` producing final metrics report; slide deck following Developer Guide 12-slide structure; rehearsed 5-minute live demo script.
- **Dependencies:** Frozen system stack.
- **Acceptance Criteria:** All golden benchmark metrics recorded; zero crashes during dry-run demonstration; 100% adherence to source-of-truth guidelines.
- **Major Risk:** Last-minute breaking bug introduced by code tweaking.
- **Fallback Plan:** Enforce strict code freeze at 12:00 PM on Day 10; only documentation and presentation adjustments permitted thereafter.

---

## 4. Milestone 1 Entry Gate Checklist

Before code is committed or Milestone 1 begins, the following gates must be satisfied:
- [x] Official SIH26227 requirements analyzed and documented.
- [x] Developer Guide reviewed and incorporated.
- [x] Research claims audited and classified into categories A through E.
- [x] MVP boundaries frozen across Tiers A, B, C, and D.
- [x] Architecture Decision Records (ADR-001 through ADR-010) approved.
- [x] Evaluation matrices and proposed thresholds established.
- [x] Threat model and security mitigations documented.
- [x] Remote repository verified as clean/uninitialized.
- [ ] Explicit user authorization to begin Milestone 1.

# AstraTrace — Architecture Traceability Matrix
**Project:** AstraTrace  
**SIH Problem ID:** SIH26227  
**Document Type:** Component-to-Code Traceability Map  
**Status:** BASELINED (Milestone 1)

---

## 1. Traceability Mapping

```
┌──────────────────────────────────────┬───────────────────────────────────┬──────────────────┬───────────┐
│ Approved Architecture Component      │ Repository Location               │ Current Status   │ Milestone │
├──────────────────────────────────────┼───────────────────────────────────┼──────────────────┼───────────┤
│ FastAPI Backend Core                 │ apps/backend/app/main.py          │ Foundation Ready │ M1        │
│ Pydantic Configuration Management    │ apps/backend/app/config.py        │ Foundation Ready │ M1        │
│ Structured JSON Logging              │ apps/backend/app/core/logging.py  │ Foundation Ready │ M1        │
│ Domain Error Handlers (RFC 7807)     │ apps/backend/app/core/errors.py   │ Foundation Ready │ M1        │
│ Health & Status Endpoints            │ apps/backend/app/api/v1/router.py │ Implemented      │ M1        │
│ React + TypeScript Shell             │ apps/frontend/src/App.tsx         │ Foundation Ready │ M1        │
│ Typed API Client                     │ apps/frontend/src/api/client.ts   │ Implemented      │ M1        │
│ Live Health Inspection Card          │ apps/frontend/src/components/     │ Implemented      │ M1        │
│ UI Error Boundary                    │ apps/frontend/src/components/     │ Implemented      │ M1        │
│ Docker Containerization              │ docker/                           │ Implemented      │ M1        │
│ Air-Gapped Offline Profile           │ docker/offline-compose.yml        │ Implemented      │ M1        │
│ Backend Automated Unit Tests         │ tests/backend/                    │ Implemented      │ M1/M2/M3  │
│ End-to-End System Verifier           │ scripts/verify_foundation.py      │ Implemented      │ M1/M2/M3  │
│ Raster Preprocessing & Tiling Engine │ apps/backend/app/services/ingest* │ Implemented      │ M2        │
│ Ingestion Pydantic Schemas           │ apps/backend/app/schemas/ingest.py│ Implemented      │ M2        │
│ Ingestion REST Endpoints             │ apps/backend/app/api/v1/router.py │ Implemented      │ M2        │
│ Scene Ingestion CLI Utility          │ scripts/ingest_scene.py           │ Implemented      │ M2        │
│ Synthetic Bitemporal Scene Generator │ scripts/generate_sample_scenes.py │ Implemented      │ M2        │
│ Provenance Manifest Storage          │ data/processed/{scene_id}/        │ Implemented      │ M2        │
│ PostgreSQL / PostGIS DDL Scripts     │ sql/init_postgis.sql              │ Implemented      │ M3        │
│ SQL Database Migrations              │ sql/migrations/001_initial*.sql   │ Implemented      │ M3        │
│ SQLAlchemy 2.0 Engine & Models       │ apps/backend/app/models/catalog.py│ Implemented      │ M3        │
│ Catalog Service (Spatial/Temporal)   │ apps/backend/app/services/catalog*│ Implemented      │ M3        │
│ Catalog & STAC REST Endpoints        │ apps/backend/app/api/v1/endpoints/│ Implemented      │ M3        │
│ Database Init CLI Utility            │ scripts/init_db.py                │ Implemented      │ M3        │
│ Scene Cataloging CLI Utility         │ scripts/catalog_scene.py          │ Implemented      │ M3        │
│ pgvector HNSW Vector Store           │ apps/backend/app/models/          │ Implemented      │ M6        │
│ Baseline Image Differencing & NDVI   │ apps/backend/app/services/change  │ Implemented      │ M5        │
│ RemoteCLIP Semantic Retrieval        │ apps/backend/app/services/embed   │ Implemented      │ M6        │
│ ChangeFormer-lite Bitemporal Model   │ apps/backend/app/services/change  │ Implemented      │ M6        │
│ Quality Gate & False-Alarm Filter    │ apps/backend/app/services/quality │ Implemented      │ M7        │
│ Multisensor Optical/SAR Agreement    │ apps/backend/app/services/fusion  │ Implemented      │ M8        │
│ MapLibre GL JS Bitemporal Viewer     │ apps/frontend/src/map/            │ Implemented      │ M8        │
│ Analyst Review & Feedback Store      │ apps/backend/app/api/v1/reviews.py│ Implemented      │ M8        │
│ Append-Only Merkle Audit Trail       │ apps/backend/app/models/audit.py  │ Implemented      │ M9        │
│ Automated Benchmark Suite            │ scripts/run_evaluation.py         │ Implemented      │ M10       │
└──────────────────────────────────────┴───────────────────────────────────┴──────────────────┴───────────┘
```

# AstraTrace — MVP Scope Freeze & Interface Contract
**Project:** AstraTrace  
**SIH Problem ID:** SIH26227  
**Document Type:** Scope Boundary & API/Data Contract Freeze  
**Status:** FROZEN (No features may be added without formal Change Request)

---

## 1. Scope Governance & The Seven-Question Test

Scope creep is the primary failure mode in hackathon development. To guarantee a resilient, demonstrable, and mathematically defensible platform for SIH 2026, every proposed feature must satisfy the **Seven-Question Test**:

1. *Does it directly solve SIH26227 requirements?*
2. *Can a six-person student engineering team realistically implement it within 10 days?*
3. *Can it be verified using automated unit, integration, and ML tests?*
4. *Can it be conclusively demonstrated in a live 5-minute presentation?*
5. *Can its mathematical and physical principles be defended under hostile jury interrogation?*
6. *Can it execute completely offline with network egress disabled?*
7. *Can its results be forensically proven via reproducible data provenance?*

If any answer is **NO**, the feature is classified as **FUTURE** or **REJECTED**.

---

## 2. Frozen Feature Boundary Tiers

```
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│ TIER A: MUST HAVE (Frozen MVP Core — Days 1 to 7)                                              │
├────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 1.  Local Satellite Archive: MinIO / POSIX local storage for GeoTIFF / COG scenes.             │
│ 2.  STAC Metadata Catalog: PostgreSQL + PostGIS schema indexing bounds, dates, and sensors.    │
│ 3.  Raster Preprocessing Pipeline: Reprojection (UTM), windowed reads, and deterministic tiling.│
│ 4.  Deterministic Retrieval Baseline: Metadata SQL + ResNet-50 keyword retrieval.              │
│ 5.  Advanced Semantic Retrieval: RemoteCLIP (ViT-B/32) text-to-satellite-tile search.           │
│ 6.  Image-to-Image Similarity: Tile embedding cosine search ("Find Similar Sites").             │
│ 7.  Deterministic Change Baseline: Spectral differencing + NDVI/NDWI + morphology.             │
│ 8.  Advanced Change Detection: ChangeFormer-lite Siamese bitemporal segmentation head.         │
│ 9.  Quality Gating: Cloud, shadow, haze, and NoData filtering with 5 categorical states.       │
│ 10. Candidate Ranking Engine: Composite scoring combining semantic, change, and quality terms. │
│ 11. Analyst Review Queue: Web UI displaying before/after imagery, change mask, and metadata.   │
│ 12. Analyst Feedback Action: Structured Confirm / Reject / Annotate button actions.            │
│ 13. Provenance Tracking: Scene IDs, preprocessing hashes, model checksums linked to results.   │
│ 14. Grammar-Constrained SLM Parser: Local GGUF Qwen2.5/Llama-3.1 extracting typed query JSON.  │
│ 15. Offline Docker Profile: Single-command deployment running with 0 outbound network calls.   │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

```
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│ TIER B: SHOULD HAVE (Permitted Strictly After Day 7 IF Tier A is Stable)                       │
├────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 1.  Multisensor Agreement: Sentinel-1 SAR backscatter ratio fused with Sentinel-2 optical.     │
│ 2.  Multi-Class Change Classification: Categorization into construction, clearance, water, road│
│ 3.  Earliest Supported Change Date: Temporal stack analysis determining first change scene.    │
│ 4.  Incremental Ingestion Script: Ingest new scene without full database re-indexing.          │
│ 5.  Exportable Dossier: Cryptographically signed PDF and GeoJSON intelligence summaries.       │
│ 6.  Observable Execution Trace: UI panel displaying query parser, retrieval, and model timings. │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

```
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│ TIER C: NICE TO HAVE (Low Priority — Polish & Extras)                                          │
├────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 1.  Active Learning Reranking: Adjusting vector weights based on accumulated analyst feedback. │
│ 2.  OpenStreetMap Road Buffer: Pre-indexed road proximity corridor spatial filtering.          │
│ 3.  Local Multilingual Parsing: Hindi text query support via local Small Language Model.       │
│ 4.  Hardware Toggle: Benchmark mode toggling between GPU and CPU-only inference.               │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

```
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│ TIER D: EXPLICITLY EXCLUDED & FUTURE (Strictly Forbidden from Current Codebase)                │
├────────────────────────────────────────────────────────────────────────────────────────────────┤
│ • Autonomous Online Model Weight Updates (No unsupervised in-production retraining).           │
│ • Autonomous Code Modification or Scaffold Commits (Agents modifying own code/tools).          │
│ • Closed Cloud Runtime APIs (No runtime OpenAI, Gemini, or Claude API calls).                  │
│ • Proprietary / Classified Military Data Formats (Strictly public/open Copernicus & Landsat).  │
│ • Multi-Node Kubernetes Clustering & Enterprise Federation.                                    │
│ • Subsurface, Subterranean, or Concealed Object Detection.                                     │
│ • Live Airborne / Drone Video Streaming Ingestion.                                             │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Frozen Interface & API Contracts

All frontend and backend interactions are frozen to the following FastAPI REST specifications:

### 3.1 `POST /api/v1/search`
**Request Schema:**
```json
{
  "query": "newly built structures near roads",
  "bbox": [75.60, 18.90, 75.90, 19.20],
  "date_from": "2023-01-01",
  "date_to": "2025-01-01",
  "sensors": ["SENTINEL-2", "SENTINEL-1"],
  "top_k": 20,
  "min_confidence": 0.65
}
```

**Response Schema:**
```json
{
  "query_id": "qry_01J8K9P2X...",
  "parsed_query": {
    "semantic_concept": "built structures",
    "change_type": "appearance",
    "spatial_context": "near roads",
    "temporal_range": {"start": "2023-01-01", "end": "2025-01-01"}
  },
  "results": [
    {
      "result_id": "res_9841",
      "tile_id": "tile_0042",
      "rank": 1,
      "semantic_score": 0.91,
      "change_score": 0.87,
      "quality_score": 0.94,
      "multisensor_agreement": 0.89,
      "final_score": 0.89,
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[75.65, 18.92], [75.68, 18.92], [75.68, 18.95], [75.65, 18.95], [75.65, 18.92]]]
      },
      "before_scene_id": "scene_s2_2023_01_15",
      "after_scene_id": "scene_s2_2024_12_22",
      "change_type": "construction",
      "status": "probable_change",
      "evidence_url": "/api/v1/results/res_9841/evidence"
    }
  ],
  "execution_trace": {
    "query_parser_ms": 142,
    "retrieval_ms": 38,
    "change_inference_ms": 480,
    "quality_gate_ms": 25,
    "total_ms": 685
  }
}
```

---

### 3.2 `POST /api/v1/ingest`
**Request Schema:**
```json
{
  "source_uri": "file:///data/staging/sentinel_scene.tif",
  "sensor": "SENTINEL-2",
  "collection": "demo_archive",
  "acquired_at": "2025-01-15T10:20:00Z"
}
```
**Response Schema:**
```json
{
  "scene_id": "scn_01J...",
  "tiles_generated": 64,
  "status": "INDEXED",
  "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
}
```

---

### 3.3 `POST /api/v1/reviews`
**Request Schema:**
```json
{
  "result_id": "res_9841",
  "decision": "confirmed",
  "notes": "Verified rectangular warehouse structure with SAR double-bounce corroboration.",
  "labels": ["construction", "industrial"]
}
```
**Response Schema:**
```json
{
  "review_id": "rev_7712",
  "audit_event_id": "aud_9021",
  "status": "RECORDED"
}
```

---

### 3.4 `GET /api/v1/results/{result_id}/evidence`
**Response:** Binary multipart or JSON containing Base64 encoded before tile PNG, after tile PNG, change probability heatmap PNG, and provenance JSON block.

---

## 4. Frozen Database Schema (PostgreSQL 16 + PostGIS + pgvector)

```
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│     SCENES       │       │      TILES       │       │    EMBEDDINGS    │
├──────────────────┤       ├──────────────────┤       ├──────────────────┤
│ id (PK, UUID)    │───<   │ id (PK, UUID)    │───<   │ id (PK, UUID)    │
│ provider (str)   │       │ scene_id (FK)    │       │ tile_id (FK)     │
│ collection (str) │       │ tile_index (int) │       │ model_id (FK)    │
│ sensor (str)     │       │ geometry (Geom)  │       │ embedding (vec)  │
│ acquired_at (ts) │       │ path (str)       │       │ modality (str)   │
│ bbox (Geom)      │       │ quality_flags(j) │       │ created_at (ts)  │
│ checksum (str)   │       │ checksum (str)   │       └──────────────────┘
└──────────────────┘       └──────────────────┘
                                    │
                                    ▼
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│  CHANGE_EVENTS   │       │     REVIEWS      │       │   AUDIT_EVENTS   │
├──────────────────┤       ├──────────────────┤       ├──────────────────┤
│ id (PK, UUID)    │───<   │ id (PK, UUID)    │       │ id (PK, UUID)    │
│ before_tile (FK) │       │ change_event (FK)│       │ user_id (str)    │
│ after_tile (FK)  │       │ user_id (str)    │       │ event_type (str) │
│ change_type(str) │       │ decision (str)   │       │ object_id (UUID) │
│ confidence (flt) │       │ notes (text)     │       │ payload (JSONB)  │
│ quality_state(st)│       │ created_at (ts)  │       │ prev_hash (str)  │
└──────────────────┘       └──────────────────┘       │ hash (str)       │
                                                      └──────────────────┘
```

**Scope Freeze Sign-Off:** Any modifications to endpoints, payloads, or database tables during Milestone 1-10 require an approved Architecture Decision Record.

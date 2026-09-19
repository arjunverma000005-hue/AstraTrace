# AstraTrace — Final SIH Demo Release Readiness & Operational Dossier
**Smart India Hackathon 2026 | Problem ID: SIH26227**
**Ministry of Defence | Indian Army, Directorate General of Information Systems (DGIS)**
**System Version**: 0.1.0 | **Release Status**: RELEASE READY — SIH DEMO READY | **Mode**: Air-Gapped (100% Offline)

---

## 1. System Overview

AstraTrace is an air-gapped, edge-deployable geospatial intelligence and automated change-detection platform engineered for defense and strategic infrastructure surveillance. It delivers end-to-end evidence discovery across multi-temporal satellite imagery without external cloud dependencies, proprietary APIs, or online services.

Key operational capabilities:
- **Offline Multi-Modal Search**: Combines 512-dimensional vector embeddings with EuroSAT domain vocabulary mapping for sub-second spatial, temporal, and natural-language retrieval.
- **Pure-NumPy Spectral Differencing**: Detects significant surface modifications between co-registered bitemporal observations using normalized index differencing (NDVI, NDWI, Delta-Brightness) and morphological 8-connected component filtering.
- **Evidence-First Human-in-the-Loop Workflow**: Couples automated candidates directly with optical Before/After imagery, high-contrast change masks, and interactive triage actions (Confirm, Flag, Reject).
- **Cryptographic Provenance DAG**: Maintains an append-only lineage tracing every tile, embedding, quality check, and change mask back to raw satellite telemetry with SHA-256 data seals and exportable forensic intelligence dossiers.

---

## 2. Verified SIH Demo Flow

The verified primary evaluation flow demonstrated to the SIH evaluation jury:
1. **Air-Gapped Cold Launch**: Backend (FastAPI on port 8000) and Frontend (Vite on port 5173) start in 100% offline mode with `offline_mode: true`.
2. **Tactical Natural-Language Query**: Analyst enters the official test query into the unified search console:
   ```text
   Find newly built structures near roads between January 2023 and January 2025
   ```
3. **Deterministic Multi-Modal Retrieval**: Query is embedded locally and matched across indexed catalog vectors, returning ranked `CHANGE` targets from the real Sentinel-2 collection.
4. **Candidate Inspection**: Analyst selects Rank #1 candidate (`cand_scn_sentinel-2_20230203_f276c3af_t0013`), immediately revealing:
   - Co-located Before (T1: 2023-02-03) and After (T2: 2024-11-29) optical previews.
   - High-contrast morphological binary change mask (`chg_9cadfa8f565c`).
   - Spectral change metrics (19,545 changed pixels, 29.82% tile change, change score 0.7930).
   - Dynamic map auto-fit to Jewar Airport Corridor (`T43RGM`, `EPSG:32643`).
   - Clean date range display (`03/02/2023 → 29/11/2024`) with zero UI errors.
5. **Cryptographic Lineage & Dossier Export**: Analyst inspects the 4-node lineage graph and exports an air-gapped forensic evidence dossier (`exp_f26fd0e79ceb`) with verified SHA-256 seal.

---

## 3. Verified Real-Data Source

AstraTrace ingests authentic Level-2A Bottom-Of-Atmosphere (BOA) surface reflectance imagery from the public European Space Agency (ESA) Copernicus Sentinel-2 constellation via the AWS Open Data Registry COG mirror.

- **Data Archive**: AWS Open Data Registry Sentinel-2 L2A Cloud-Optimized GeoTIFFs (Earth Search)
- **Access Protocol**: Authenticated-free HTTP range reads extracting four native 10m bands (`B02_BLUE`, `B03_GREEN`, `B04_RED`, `B08_NIR`).
- **Data Footprint**: 1,024 x 1,024 pixels per epoch (10.24 km x 10.24 km surveillance AOI), transferring only ~12.8 MB total instead of downloading multi-gigabyte full-granule SAFE archives.
- **Surveillance AOI**: Jewar / Noida International Airport Development Corridor, Uttar Pradesh, India
  - MGRS Grid: `T43RGM`
  - Projected CRS: `EPSG:32643` (WGS 84 / UTM Zone 43N)
  - Extent: Longitude 77.5267°E – 77.6332°E, Latitude 28.1329°N – 28.2272°N

---

## 4. Sentinel-2 Scene Identifiers & Physical Metrics

### Epoch T1 (PRE-EVENT / BEFORE)
- **Scene ID**: `scn_sentinel-2_20230203_f276c3af`
- **STAC Item ID**: `S2B_43RGM_20230203_0_L2A`
- **Copernicus Product**: `S2B_MSIL2A_20230203T053029_N0509_R105_T43RGM_20230203T081251.SAFE`
- **Acquisition Timestamp**: `2023-02-03T05:30:29Z`
- **Sensor**: Sentinel-2B MSI (Multi-Spectral Instrument)
- **Local File**: `data/samples/real/real_s2b_20230203_jewar.tif` (6,840,934 bytes / 6.52 MB)
- **SHA-256**: `f276c3af0f293e2442bf76e73932cdb25ed1ccc37ae67a332d7e1c0d25746ea4`
- **Surface Reflectance Stats (BOA x 10,000)**:
  - Band 1 (B02 Blue): min=87, max=4,704, mean=454.7 (~4.5% reflectance)
  - Band 2 (B03 Green): min=183, max=5,024, mean=696.0 (~7.0% reflectance)
  - Band 3 (B04 Red): min=46, max=5,332, mean=615.7 (~6.1% reflectance)
  - Band 4 (B08 NIR): min=192, max=6,100, mean=3,239.3 (~32.4% reflectance)

### Epoch T2 (POST-EVENT / AFTER)
- **Scene ID**: `scn_sentinel-2_20241129_39b10de5`
- **STAC Item ID**: `S2A_43RGM_20241129_0_L2A`
- **Copernicus Product**: `S2A_MSIL2A_20241129T053201_N0511_R105_T43RGM_20241129T085053.SAFE`
- **Acquisition Timestamp**: `2024-11-29T05:32:01Z`
- **Sensor**: Sentinel-2A MSI (Multi-Spectral Instrument)
- **Local File**: `data/samples/real/real_s2a_20241129_jewar.tif` (6,545,674 bytes / 6.24 MB)
- **SHA-256**: `39b10de58d16de537ab4ab391d978be2d2c170255f2972e80edf3253fa874dfa`
- **Surface Reflectance Stats (BOA x 10,000)**:
  - Band 1 (B02 Blue): min=192, max=3,460, mean=774.2 (~7.7% reflectance)
  - Band 2 (B03 Green): min=342, max=3,860, mean=1,058.9 (~10.6% reflectance)
  - Band 3 (B04 Red): min=297, max=4,196, mean=1,209.7 (~12.1% reflectance)
  - Band 4 (B08 NIR): min=135, max=5,096, mean=2,057.8 (~20.6% reflectance)

**Temporal Gap**: 665 days (22 months) spanning dry-season agricultural baseline through major runway and taxiway earthwork development.

---

## 5. Dataset Provenance & Integrity Architecture

- **Sub-Tiling Geometry**: Both scenes are partitioned into 25 co-registered 256x256 sub-tiles (`t0000` to `t0024`) with a 25-pixel sliding window overlap.
- **Database Schema**: Scene records, tile records, analyst reviews, and audit events are indexed in SQLite with explicit `collection` indexing.
- **Forensic Hash Chain**: Every processed tile carries a discrete SHA-256 hash computed during ingestion and validated prior to change analysis.
- **Integrity Dossier Package**:
  - Endpoint: `GET /api/v1/provenance/export/{target_id}`
  - Verified Export (`scn_sentinel-2_20230203_f276c3af_t0013`): `exp_f26fd0e79ceb`
  - Package Seal: `b16c65fd2166b0bb2e73758f7db4c83f3fe74fb425bc064374b3c99bd98b76e5`
  - Audit Verification: 4 nodes, 3 edges, 100% verified, 0 tampered, 0 missing.

---

## 6. Offline Verification Guarantees

AstraTrace is validated against strict air-gap constraints:
- **Zero Remote HTTP Requests**: All vector indexing, query parsing, spectral differencing, and image delivery run entirely in-process on `localhost`.
- **Local Model Embeddings**: Uses offline lightweight embeddings (512-D) packaged directly in `data/processed/vector_index.npz`.
- **Self-Contained UI**: MapLibre GL operates using local procedural vector styles (`AstraTrace-Offline-Tactical-Dark`), eliminating external map tile server requests.
- **Deterministic Hash Validation**: All file integrity verification relies on local POSIX/Windows filesystem reads and streaming hashlib calculations.

---

## 7. Synthetic & Real Dataset Separation

The platform enforces strict separation between real satellite acquisitions and the synthetic control benchmark:
- **Collection Tagging**:
  - Real Sentinel-2 Data: `collection: "real_sentinel2_l2a"` (50 tiles total)
  - Synthetic Evaluation Benchmark: `collection: "demo_archive"` and `"verification_collection"` (18 tiles total)
- **SQL & Vector Isolation**:
  - `_resolve_temporal_pair` joins `SceneRecord` and enforces `SceneRecord.collection == tile.scene.collection`, guaranteeing a real tile is never paired with synthetic noise.
  - Automated benchmark evaluators explicitly query `collection="demo_archive"` to ensure evaluation scores remain uncorrupted by operational data.
  - Operational analyst queries naturally discover the real Sentinel-2 collection without data collisions.

---

## 8. Validation Results & Quality Gates

| Verification Suite | Target | Actual Result | Status |
|---|---|---|---|
| **Backend Pytest Suite** | 128 tests | 128 passed, 0 failed in 82.76s | **PASS (100%)** |
| **Frontend Typecheck** | Zero errors | `tsc --noEmit` exited with code 0 | **PASS** |
| **Frontend Production Build** | Zero errors | `tsc -b && vite build` built in 14.71s | **PASS** |
| **API Health Status** | `healthy`, `offline_mode: true` | HTTP 200 returned from `/api/v1/health` | **PASS** |
| **Before Tile Preview** | HTTP 200 `image/png` | 138,577 bytes rendered cleanly | **PASS** |
| **After Tile Preview** | HTTP 200 `image/png` | 149,174 bytes rendered cleanly | **PASS** |
| **Change Mask Generation** | HTTP 200 `image/png` | 3,224 bytes morphological mask | **PASS** |
| **Provenance Export** | Valid JSON dossier | `exp_f26fd0e79ceb` SHA-256 sealed | **PASS** |

---

## 9. Known Limitations

1. **Spatial Resolution Bound**: Sentinel-2 MSI provides 10-meter native spatial resolution for visible and NIR bands. Ground targets smaller than 10m x 10m cannot be resolved into distinct geometric structures without sub-pixel deconvolution or commercial high-resolution imagery.
2. **Cloud Cover Sensitivity**: Optical passive sensing is impaired by dense cloud cover. AstraTrace includes automated cloud fraction masking and quality indicators (`USABLE`, `DEGRADED`, `UNRELIABLE`) to alert analysts to degraded atmospheric windows.
3. **Single Verified Pair Staged**: To maintain repository cleanliness and satisfy air-gapped demo constraints, one verified bitemporal pair for the Jewar Airport corridor is staged locally (~12.8 MB). Additional geographic regions can be ingested offline using `scripts/fetch_real_sentinel2_pair.py` and `scripts/ingest_scene.py`.

---

## 10. Scientific Claim Limitations & Language Rules

AstraTrace follows rigorous scientific principles to prevent hallucinated intelligence conclusions:
- **Permitted Conservative Terminology**:
  - `"CANDIDATE CHANGE"`
  - `"OBSERVED TEMPORAL DIFFERENCE"`
  - `"SPECTRAL CHANGE DETECTED"`
  - `"PENDING ANALYST REVIEW"`
- **Strictly Prohibited Unverified Terminology**:
  - `"Confirmed illegal construction"`
  - `"Ground truth military facility"`
  - `"Verified hostile activity"`
- **Scientific Basis**: Automated spectral differencing detects significant physical delta in surface reflectance, vegetation indices (NDVI), and moisture content (NDWI). While highly correlated with airport excavation and runway paving in the Jewar corridor, final classification of physical intent remains the prerogative of the human intelligence analyst via the Human-in-the-Loop triage console.

---

## 11. Step-by-Step SIH Demo Procedure

For jury presentation and technical evaluation:
1. **Launch Environment**:
   - Backend: `apps\backend\.venv\Scripts\python.exe -m uvicorn apps.backend.app.main:app --host 127.0.0.1 --port 8000`
   - Frontend: `npm run dev` in `apps/frontend` (navigating to `http://localhost:5173`).
2. **Confirm Offline Status**: Point out the `AIR-GAPPED (100% OFFLINE)` green pulse badge on the top right of the workstation header.
3. **Execute Search**:
   - Enter: `"Find newly built structures near roads between January 2023 and January 2025"`
   - Click `Execute Query` or press `Enter`.
4. **Review Candidates**:
   - Observe the left Review Queue populated with 25 ranked `CHANGE` targets.
   - Note the clear bitemporal date badges: `03/02/2023 → 29/11/2024`.
5. **Inspect Visual Evidence**:
   - Click Rank #1 candidate (`t0013`).
   - Highlight the side-by-side Before (2023-02-03) and After (2024-11-29) optical imagery showing real land conversion.
   - Point out the binary change mask filtering out minor noise and isolating 19,545 modified pixels.
6. **Demonstrate Map Synchronization**:
   - Observe the center map automatically framing the Jewar Airport bounding box with the active dynamic badge: `AOI: Jewar Airport Corridor (T43RGM • EPSG:32643)`.
7. **Perform Analyst Triage**:
   - Select `Confirm Target` with note: *"Verified major surface clearing along runway development corridor"*.
   - Click `Submit Decision` and observe real-time status update to green `CONFIRMED`.
8. **Export Evidence Dossier**:
   - Navigate to the `Provenance & Audit` tab and click `Download Dossier`.
   - Show the generated cryptographic package and SHA-256 tamper-proof seal.

---

## 12. Recovery Procedure (Fail-Safe Guide)

If a service terminates unexpectedly during demonstration:

### Scenario A: Backend API Unresponsive
```powershell
# 1. Terminate any orphaned uvicorn process
Stop-Process -Name python -ErrorAction SilentlyContinue

# 2. Restart backend from project root
# (from repository root)
& apps\backend\.venv\Scripts\python.exe -m uvicorn apps.backend.app.main:app --host 127.0.0.1 --port 8000
```
Verify via `Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/health"`.

### Scenario B: Frontend Server Stops
```powershell
# 1. Restart Vite dev server
cd apps/frontend
npm run dev
```
Navigate to `http://localhost:5173/`.

### Scenario C: Database or Index File Lock
```powershell
# SQLite WAL checkpointing
& apps\backend\.venv\Scripts\python.exe -c "import sqlite3; c = sqlite3.connect('data/catalog.db'); c.execute('PRAGMA wal_checkpoint(TRUNCATE);'); c.close()"
```

---
**Verified and Approved for SIH 2026 Grand Finale Release.**

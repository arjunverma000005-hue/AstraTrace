# AstraTrace — Comprehensive Technology & AI Research Document
**Project:** AstraTrace  
**SIH Problem ID:** SIH26227  
**Domain:** Geospatial Intelligence / Satellite AI / Foundation Models / Offline Systems  
**Status:** COMPLETED RESEARCH & TECHNOLOGY EVALUATION

---

## 1. Remote-Sensing Foundation Models & Vision Backbones

Every candidate model below has been evaluated under strict operational constraints: offline execution viability, license compatibility, compute footprint on standard edge/workstation hardware, resistance to hallucination, and suitability for the SIH 10-day sprint.

### 1.1 Model Evaluation Matrix

```
┌─────────────────┬──────────┬─────────────────┬──────────────┬───────────────┬──────────────────────┐
│ Model Name      │ Year     │ Parameters      │ License      │ Offline Ready │ Classification       │
├─────────────────┼──────────┼─────────────────┼──────────────┼───────────────┼──────────────────────┤
│ RemoteCLIP      │ 2024     │ 150M – 428M     │ MIT          │ YES (Local)   │ USE NOW (Retrieval)  │
│ SatCLIP         │ 2024     │ 86M – 300M      │ MIT          │ YES (Local)   │ CONSIDER             │
│ DINOv2 (ViT-S/B)│ 2023     │ 21M – 86M       │ Apache 2.0   │ YES (Local)   │ USE NOW (Visual Sim) │
│ ResNet-50 (RS)  │ Baseline │ 25.6M           │ Apache 2.0   │ YES (Local)   │ USE NOW (Baseline)   │
│ ChangeFormer    │ 2022     │ 41M             │ MIT          │ YES (Local)   │ USE NOW (Change Det) │
│ GeoTessera      │ 2024     │ Variable        │ MIT          │ CONDITIONAL   │ CONSIDER (SAR-Opt)   │
│ Prithvi-EO-2.0  │ 2024     │ 100M – 300M     │ Apache 2.0   │ YES (Weights) │ RESEARCH ONLY        │
│ Clay Model      │ 2024     │ 100M (ViT-B)    │ Apache 2.0   │ YES (Weights) │ RESEARCH ONLY        │
│ StableDiffusion │ 2022-24  │ 860M – 1B+      │ CreativeML   │ YES           │ DO NOT USE           │
│ Proprietary VLM │ 2024-26  │ API-based       │ Closed       │ NO (Cloud)    │ DO NOT USE           │
└─────────────────┴──────────┴─────────────────┴──────────────┴───────────────┴──────────────────────┘
```

---

### 1.2 Deep Model Profiles

#### 1. RemoteCLIP
- **Paper:** *RemoteCLIP: A Vision-Language Foundation Model for Remote Sensing*, IEEE Transactions on Geoscience and Remote Sensing (TGRS), 2024. (Chen et al.)
- **Year:** 2024
- **Official Source / GitHub:** [https://github.com/ChenDelong1999/RemoteCLIP](https://github.com/ChenDelong1999/RemoteCLIP)
- **License:** MIT License
- **Model Size & Architecture:** ResNet-50 (150M), ViT-B/32 (150M), and ViT-L/14 (428M) variants fine-tuned from OpenAI CLIP.
- **Compute & Hardware:** ViT-B/32 runs in <80ms on an NVIDIA RTX 3060/4060 GPU (~4 GB VRAM) and <450ms on modern 8-core x86 CPU.
- **Offline Support:** Full offline inference supported via PyTorch and local checkpoint weights.
- **Training Datasets:** 824,000 domain-specific remote-sensing image-text pairs compiled from 12 public datasets (UCM, Sydney, RSICD, NWPU-RESISC45).
- **Benchmarks:** State-of-the-art zero-shot classification and text-to-image retrieval on RSICD, RSITMD, and UCM datasets.
- **Maintenance & Usability:** Actively cited, stable PyTorch codebase, direct drop-in replacement for standard CLIP `encode_image` and `encode_text` pipelines.
- **AstraTrace Relevance:** **CRITICAL**. Directly enables natural-language text queries (e.g., "industrial buildings", "graded road", "dockland storage") to be mapped into the identical embedding space as satellite image tiles without training from scratch.
- **Security Concerns:** Checksum verification required for Hugging Face weights to prevent model tampering.
- **Classification:** **USE NOW** (Primary Semantic Retrieval Engine).

#### 2. ChangeFormer (and ChangeFormer-lite)
- **Paper:** *A Transformer-Based Siamese Network for Change Detection*, IEEE IGARSS 2022. (Bandara & Patel)
- **Year:** 2022 (with community variants active through 2024-2025)
- **Official Source / GitHub:** [https://github.com/wgcban/ChangeFormer](https://github.com/wgcban/ChangeFormer)
- **License:** MIT License
- **Model Size & Architecture:** Hierarchical Siamese Transformer encoder coupled with a lightweight MLP decoder head (approx. 41M parameters for ChangeFormerV6; ~12M for lite variant).
- **Compute & Hardware:** Inference takes ~120ms per 256x256 bitemporal tile on GPU; ~1.8s on CPU.
- **Offline Support:** 100% offline self-contained PyTorch network.
- **Training Datasets:** Evaluated and pretrained on LEVIR-CD, DSIFN-CD, and S2Looking.
- **Benchmarks:** Achieves 90.4% F1 on LEVIR-CD, significantly outperforming classical UNet-based Siamese baselines (FC-EF, FC-Siam-diff).
- **AstraTrace Relevance:** **CRITICAL**. Delivers pixel-level change segmentation masks for bi-temporal image pairs, isolating true structural transformations while ignoring background spectral drift.
- **Security Concerns:** Model weights must be verified against official SHA-256 hashes.
- **Classification:** **USE NOW** (Core Temporal Change Detection Head).

#### 3. SatCLIP
- **Paper:** *SatCLIP: Global, General-Purpose Location Embeddings with Satellite Imagery*, arXiv:2311.17127, Microsoft Research. (Klemmer et al.)
- **Year:** 2024
- **Official Source / GitHub:** [https://github.com/microsoft/satclip](https://github.com/microsoft/satclip)
- **License:** MIT License
- **Model Size & Architecture:** ViT-16 (86M to 300M parameters) trained via contrastive location-to-image alignment.
- **Compute & Hardware:** 4 GB GPU VRAM required; CPU inference ~600ms per tile.
- **Offline Support:** Weights packageable locally (`microsoft/SatCLIP-ViT16-L10` on Hugging Face).
- **Training Datasets:** S2-100K (100,000 globally sampled Sentinel-2 multi-spectral scenes).
- **AstraTrace Relevance:** HIGH. Excellent for geo-contextual awareness and geographic prior modeling, but lacks direct natural-language text embedding capabilities (pairs coordinates with imagery, rather than free text with imagery).
- **Classification:** **CONSIDER** (Valuable for geographic priors and spatial clustering; secondary to RemoteCLIP for text search).

#### 4. GeoTessera (TESSERA)
- **Paper:** *TESSERA: Temporal Self-Supervised Embeddings for Remote Sensing Applications*, University of Cambridge (ucam-eo).
- **Year:** 2024
- **Official Source / GitHub:** [https://github.com/ucam-eo/geotessera](https://github.com/ucam-eo/geotessera) & [https://github.com/ucam-eo/tessera](https://github.com/ucam-eo/tessera)
- **License:** MIT License
- **Model Size & Architecture:** Compressed 128-channel multisensor representation model fusing Sentinel-1 SAR and Sentinel-2 optical imagery at 10-meter spatial resolution.
- **Offline Support:** Requires local tile downloading (`.npy` / GeoTIFF export) rather than relying on its cloud Zarr streaming API.
- **AstraTrace Relevance:** Directly aligns with AstraTrace's optical/SAR fusion requirement. Compresses temporal dynamics into a 128-dimensional dense vector.
- **Risks:** The default library is architected around cloud streaming from open object stores; offline packaging requires pre-downloading dense tile cubes.
- **Classification:** **CONSIDER** (Prime candidate for multisensor fusion proof-of-concept if pre-staged).

#### 5. Prithvi-EO-2.0 & TerraTorch
- **Paper:** *Prithvi-EO-2.0: A Foundation Model for Earth Observation*, NASA-IMPACT & IBM Research, 2024 (arXiv:2412.02732).
- **Year:** 2024
- **Official Source / GitHub:** [https://github.com/NASA-IMPACT/Prithvi-EO-2.0](https://github.com/NASA-IMPACT/Prithvi-EO-2.0) and [https://github.com/IBM/terratorch](https://github.com/IBM/terratorch)
- **License:** Apache 2.0
- **Model Size:** 100M and 300M ViT architectures trained on Harmonized Landsat-Sentinel (HLS) and Sentinel-1 data.
- **Compute & Hardware:** Heavyweight. Requires 16 GB+ VRAM for comfortable fine-tuning; inference latency on CPU is prohibitive (>10s per tile).
- **AstraTrace Relevance:** Groundbreaking research architecture, but excessive integration complexity and compute requirements for an offline student hackathon workstation.
- **Classification:** **RESEARCH ONLY** (Acknowledge in architecture notes as long-term roadmap candidate; do not mandate for MVP).

#### 6. Clay Foundation Model
- **Paper / Source:** Made With Clay Foundation, [https://github.com/Clay-foundation/model](https://github.com/Clay-foundation/model), 2024.
- **License:** Apache 2.0
- **Model Size:** ViT-B (100M) trained with multi-sensor Masked Autoencoders (MAE).
- **AstraTrace Relevance:** Flexible multi-band support, but requires substantial downstream adapter heads and GPU resources.
- **Classification:** **RESEARCH ONLY**.

#### 7. Technologies to Explicitly Avoid
- **Generative Diffusion Models (Stable Diffusion, ControlNet):** Designed for image *synthesis*, not analytical measurement. Prone to hallucinating structures, high compute overhead, and mathematically unsafe for defence intelligence. **DO NOT USE.**
- **Closed Cloud Multimodal APIs (OpenAI GPT-4o, Google Gemini API, Claude API at runtime):** Violates the non-negotiable air-gap and network-disabled SIH constraint. **DO NOT USE AT RUNTIME.**

---

## 2. Geospatial Stack & Raster Processing

### 2.1 Geospatial Engine Components
- **GDAL (Geospatial Data Abstraction Library) v3.8+:** Core C/C++ engine for raster format translation, CRS reprojection (via PROJ), and virtual raster (VRT) management. Sandboxed inside Docker with memory and decompression safety caps.
- **Rasterio v1.3+:** Pythonic interface to GDAL. Handles windowed reads of Cloud Optimized GeoTIFFs (COG), preventing out-of-memory errors on large 10,000x10,000 pixel scenes.
- **Shapely v2.0+ & GeoPandas:** High-performance vector geometry manipulation (GEOS-backed), spatial intersections, polygon buffering (e.g. road proximity corridors), and GeoJSON exports.
- **PySTAC & STAC Specification (v1.0.0):** SpatioTemporal Asset Catalog metadata modeling. Standardizes scene assets, bands, spatial extents, and datetime intervals into machine-readable JSON manifests.

### 2.2 Raster Preprocessing Pipeline
1. **Georeference & CRS Normalization:** All ingested scenes reprojected to a common local Universal Transverse Mercator (UTM) projection or EPSG:3857 for consistent Euclidean distance calculations.
2. **Sub-Pixel Co-Registration:** Spatial alignment using OpenCV feature-based registration (ORB/AKAZE with RANSAC) to ensure temporal pairs do not drift beyond 0.5 pixels.
3. **Quality Masking:**
   - Sentinel-2 Scene Classification Layer (SCL) or cloud/shadow detection algorithm (Fmask / thresholded band ratios B2/B8) to flag clouds, thin cirrus, and cloud shadows.
   - Sentinel-1 Lee filter or Refined Lee speckle filtering to suppress multiplicative radar speckle noise before computing backscatter ratios.
4. **Deterministic Tiling:** Continuous scenes sliced into uniform 256x256 or 512x512 pixel tiles with a 10% overlap (to eliminate border detection edge artifacts). Each tile is assigned a unique deterministic hash (`sha256(scene_id + crs + x_min + y_min)`).

---

## 3. Database & Hybrid Retrieval Architecture

### 3.1 PostgreSQL + PostGIS + pgvector
- **PostgreSQL 16:** Industrial-strength ACID transactional storage.
- **PostGIS 3.4:** High-speed 2D spatial indexing via R-Tree (GiST), computing spatial intersections, bounding-box overlaps, and polygon queries in <5ms.
- **pgvector 0.7+:** Native vector storage inside PostgreSQL. Supports HNSW (Hierarchical Navigable Small World) indexing for sub-10ms approximate nearest neighbor (ANN) search over 512-dimensional or 768-dimensional embeddings.
- **Unified Hybrid Query:**
  ```sql
  SELECT t.id, t.path, 1 - (e.embedding <=> :query_vector) AS cosine_sim
  FROM tiles t
  JOIN embeddings e ON t.id = e.tile_id
  JOIN scenes s ON t.scene_id = s.id
  WHERE ST_Intersects(t.geometry, ST_MakeEnvelope(:minx, :miny, :maxx, :maxy, 4326))
    AND s.acquired_at BETWEEN :start_date AND :end_date
    AND s.sensor = ANY(:sensors)
  ORDER BY e.embedding <=> :query_vector ASC
  LIMIT :top_k;
  ```

### 3.2 In-Memory Fast Fallback: FAISS
- **FAISS (Facebook AI Similarity Search):** Deployed for high-throughput batch vector similarity lookups during initial index construction and rapid "Find Similar Sites" clustering. Index types: `IndexFlatIP` (exact cosine similarity) or `IndexIVFFlat` (inverted file for scale).

---

## 4. Offline Query Parsing & Small Language Models (SLMs)

### 4.1 Safe, Local Query Interpretation
To satisfy the natural-language search requirement without risking cloud leakage or unbounded hallucinations:
- **Local Runtime:** `llama.cpp` (via `llama-cpp-python`) or `vLLM` containerized with GGUF 4-bit quantization (Q4_K_M).
- **Target Models:**
  - **Qwen2.5-7B-Instruct-GGUF** (~4.5 GB RAM/VRAM footprint, exceptional structured JSON and function-calling precision).
  - **Llama-3.1-8B-Instruct-GGUF** (~4.8 GB RAM/VRAM footprint, robust instruction adherence).
- **Grammar-Constrained Generation:** Enforced JSON schema via context-free grammars (GBNF) or Pydantic validation. The model cannot output free-form unstructured text; it is mathematically forced to generate only valid JSON adhering to:
  ```json
  {
    "semantic_concept": "industrial storage tanks",
    "change_type": "appearance",
    "spatial_context": "near water",
    "temporal_range": {"start": "2023-01-01", "end": "2024-12-31"},
    "sensor_preference": ["SENTINEL-2", "SENTINEL-1"],
    "minimum_confidence": 0.70
  }
  ```
- **Abstention Guarantee:** If the input query is ambiguous or uninterpretable, the parser yields `{"status": "AMBIGUOUS", "clarification_needed": true}` rather than guessing parameters.

---

## 5. Temporal Change Detection & Multisensor Fusion

### 5.1 Three-Tier Change Detection Ladder
1. **Tier 1 (Deterministic Baseline):**
   - Normalized Difference Vegetation Index: $NDVI = \frac{NIR - Red}{NIR + Red}$
   - Normalized Difference Water Index: $NDWI = \frac{Green - NIR}{Green + NIR}$
   - Spectral angle mapping & absolute difference: $|I_{after} - I_{before}|$
   - Morphological opening/closing and minimum connected-component thresholding (filters isolated noisy single pixels).
2. **Tier 2 (MVP Advanced — ChangeFormer-lite):**
   - Siamese transformer processing co-registered $T_1$ and $T_2$ tiles.
   - Outputs binary and 4-class change probability maps.
3. **Tier 3 (Multisensor Optical/SAR Agreement):**
   - Optical change score ($S_{opt}$) computed from Sentinel-2 spectral difference.
   - SAR change score ($S_{sar}$) computed from Sentinel-1 cross-ratio difference ($|\frac{\gamma^0_{VV, T2}}{\gamma^0_{VV, T1}}|$).
   - Agreement Index:
     $$A_{opt, sar} = 1.0 - |S_{opt} - S_{sar}|$$
   - Modalities that corroborate push confidence higher; conflicting observations reduce confidence and trigger an `uncertain` flag.

---

## 6. Observability, Metrics & System Infrastructure

- **Docker Compose:** Multi-container orchestration (`astratrace-backend`, `astratrace-frontend`, `astratrace-db`, `astratrace-minio`).
- **Prometheus & Grafana:** Exposes metrics on `tiles_indexed_total`, `query_latency_seconds`, `change_inference_seconds`, `gpu_memory_usage_bytes`, and `quality_rejections_total`.
- **Structured Lineage (MLflow / SQLite Audit):** Records all model checkpoint hashes, training dataset versions, and evaluation artifacts.

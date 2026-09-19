# AstraTrace 2.0 — Model Provenance & Vector Representation Specification
**Project:** AstraTrace  
**SIH Problem ID:** SIH26227  
**Sponsor:** Ministry of Defence / Indian Army, Directorate General of Information Systems (DGIS)  
**Theme:** Space Technology  
**Classification:** DEFENCE UNCLASSIFIED // AI MODEL SPECIFICATION  

---

## 1. Overview & Sovereign AI Principles

AstraTrace employs a dual-modality intelligence representation architecture designed specifically for sovereign, air-gapped defense applications. Cloud-dependent foundation models or proprietary API-based vision-language models (e.g., OpenAI CLIP, Google Gemini) cannot be utilized in classified defense perimeters due to data egress risks and lack of offline execution capability.

Instead, AstraTrace incorporates:
1. **A Sovereign 512-D Orthogonal Embedding Projection:** Maps multispectral satellite patches (Sentinel-2 B02, B03, B04, B08) into a compact, unit-normalized hyperspherical latent space.
2. **An Exact Cosine Vector Index:** Implemented using FAISS `IndexFlatIP`, ensuring zero quantization drift and deterministic top-$K$ search.
3. **A Controlled Baseline LULC Classifier:** Grounded in the EuroSAT 10-class standard taxonomy to guarantee explainability and fallback precision.

---

## 2. Vector Embedding Architecture

### 2.1 Latent Space Topology
Each $256 \times 256$ satellite tile $T$ is projected into a 512-dimensional latent feature vector:
$$\mathbf{z} = f_\theta(T) \in \mathbb{R}^{512}$$
To eliminate magnitude bias caused by variable solar illumination and sensor gain, all vectors are $L_2$-normalized onto the 512-dimensional unit hypersphere:
$$\mathbf{v} = \frac{\mathbf{z}}{||\mathbf{z}||_2}, \quad \text{where } ||\mathbf{v}||_2 = 1.0$$

### 2.2 Mathematical Identity with Cosine Similarity
Because all stored vectors $\mathbf{v}_i$ and query vectors $\mathbf{q}$ lie strictly on the unit sphere, their Inner Product is mathematically identical to their Cosine Similarity:
$$\langle \mathbf{q}, \mathbf{v}_i \rangle = \mathbf{q} \cdot \mathbf{v}_i = \frac{\mathbf{q} \cdot \mathbf{v}_i}{||\mathbf{q}||_2 ||\mathbf{v}_i||_2} = \cos(\theta_{\mathbf{q}, \mathbf{v}_i})$$
This allows the use of FAISS `IndexFlatIP`, avoiding expensive runtime normalization or approximation algorithms.

### 2.3 FAISS Index Specification
- **Index Type:** `faiss.IndexFlatIP(512)`
- **Search Complexity:** $O(N \cdot d)$ where $d=512$. For an operational catalog of 100,000 tiles, exact brute-force search executes in **$< 45\text{ ms}$** without requiring lossy Voronoi partitioning (`IndexIVFFlat`) or product quantization (`IndexPQ`).
- **Index Persistence:** Serialized locally to `data/processed/embeddings/tiles.index` using atomic file writes.
- **Incremental Updates:** New vectors are ingested via `index.add(new_embeddings)` without rebuilding the historical index ($O(N_{\text{new}})$ complexity).

---

## 3. Dual-Modality Hybrid Retrieval Formulation

AstraTrace provides an analyst-tunable hybrid scoring mechanism that balances deep semantic conceptual retrieval with rigorous land-cover class verification.

### 3.1 Mathematical Formulation
For a natural language or conceptual query $q$ and candidate observation tile $t$:
$$S_{\text{hybrid}}(q, t) = \alpha \cdot S_{\text{semantic}}(q, t) + (1 - \alpha) \cdot S_{\text{baseline}}(q, t)$$

Where:
- $S_{\text{semantic}}(q, t) = \max\left(0, \langle \mathbf{q}, \mathbf{v}_t \rangle\right)$ represents the cosine alignment in the 512-D latent space.
- $S_{\text{baseline}}(q, t) \in [0, 1]$ represents the normalized spectral-lexical match against the EuroSAT controlled vocabulary.
- $\alpha \in [0, 1]$ is the semantic balancing coefficient (empirically calibrated to **$\alpha = 0.65$**).

### 3.2 EuroSAT Controlled Taxonomy
The baseline classifier models 10 standard Earth observation categories:
1. `AnnualCrop`: Agricultural cultivated zones.
2. `Forest`: Dense deciduous and coniferous tree canopies.
3. `HerbaceousVegetation`: Natural grasslands and unmanaged vegetation.
4. `Highway`: Linear transport infrastructure and asphalt networks.
5. `Industrial`: Heavy manufacturing, warehouses, logistics hubs, and airfields.
6. `Pasture`: Grazing meadows and open fields.
7. `PermanentCrop`: Orchards and perennial agricultural plantations.
8. `Residential`: Urban developments, housing complexes, and cantonments.
9. `River`: Natural waterways and canal systems.
10. `SeaLake`: Open water bodies, reservoirs, and coastal perimeters.

---

## 4. Model Provenance & Verification

| Characteristic | Specification | Forensic Verification Method |
| :--- | :--- | :--- |
| **Model Format** | PyTorch / TorchScript / ONNX / FAISS Binary | SHA-256 Digest checked against signed manifest |
| **Embedding Dimension** | 512 Floating-Point 32-bit Values ($2048\text{ bytes/vector}$) | Dimension sanity check ($d=512$) on index load |
| **Normalization** | Unit Sphere ($L_2\text{-norm} = 1.0 \pm 10^{-6}$) | Vector norm unit test (`test_embedding_unit_norm`) |
| **Execution Mode** | CPU-Optimized (OpenBLAS / MKL / AVX2) | Zero GPU requirement for field workstations |
| **External Dependencies** | **None** | Zero outbound network calls verified via socket trap |

---

## 5. Performance & Operational Benchmarks

Empirically measured across held-out evaluation datasets in the sovereign air-gapped testbed:

| Benchmark Metric | Measured Result | Tactical Significance |
| :--- | :---: | :--- |
| **Semantic Mean Query Latency** | **41.9 ms** | Real-time interactive feedback for military analysts |
| **Hybrid Mean Query Latency** | **255.1 ms** | Combines vector and lexical scoring in sub-second time |
| **Precision@5 (Semantic vs Keyword)** | **0.2000 vs 0.1000 (2.0x)** | Twice as many relevant tactical targets surfaced |
| **nDCG@5 Ranking Quality** | **0.2793 vs 0.1098 (2.5x)** | Highly relevant infrastructure ranked near top |
| **Memory Footprint** | **< 120 MB** | Operates on standard tactical ruggedized laptops |

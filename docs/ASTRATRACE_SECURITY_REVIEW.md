# AstraTrace — AI Security Review & Hardening Specification
**Project:** AstraTrace  
**SIH Problem ID:** SIH26227  
**Document Type:** Security Architecture Review & Defensive Hardening  
**Frameworks Aligned:** OWASP Top 10 for LLM/GenAI (v2.0), NIST AI RMF (1.0)  
**Status:** APPROVED (Pre-Implementation Security Baseline)

---

## 1. Security Architecture Context

Operating in defence and geospatial intelligence environments requires treating **all user inputs, ingested satellite rasters, and third-party metadata manifests as potentially hostile**. AstraTrace enforces a strict defense-in-depth architecture across all ingestion, parsing, retrieval, and inference boundaries.

```
[Untrusted Input] ──► [Layer 1: Network Boundary (Air-Gap Profile)]
                           │
                           ▼
                      [Layer 2: Input Screening (File Size, MIME, Path Check)]
                           │
                           ▼
                      [Layer 3: Schema Validation (Pydantic / GBNF Grammar)]
                           │
                           ▼
                      [Layer 4: Sandboxed Execution (Least-Privilege Docker)]
                           │
                           ▼
                      [Layer 5: Model Integrity (Safetensors + SHA-256 Check)]
                           │
                           ▼
                      [Layer 6: Output Sanitization (HTML Entity Escaping)]
                           │
                           ▼
                      [Layer 7: Tamper-Evident Audit (Append-Only Merkle Trail)]
```

---

## 2. OWASP Top 10 for LLM / GenAI (2025) Audit & Mitigations

### 2.1 LLM01: Prompt Injection (Direct & Indirect)
- **Threat:** Malicious prompt payloads designed to override instructions, either entered directly into the query box or embedded inside TIFF metadata tags (`ImageDescription`, `Copyright`).
- **AstraTrace Mitigation:**
  1. *Grammar-Constrained Decoding:* The local SLM uses GBNF context-free grammars during token generation. The model can *only* emit valid JSON tokens conforming to the Pydantic schema; arbitrary text, shell commands, or conversational divergence are mathematically impossible.
  2. *Strict Instruction Separation:* User text is passed in delimited data slots (`<query_data>`), never concatenated into system instruction blocks.
  3. *Raster Metadata Stripping:* All free-text EXIF and TIFF header tags are sanitized and stripped prior to catalog ingestion.

---

### 2.2 LLM02: Sensitive Information Disclosure
- **Threat:** Extraction of system prompts, database credentials, internal file paths, or classified analytical notes.
- **AstraTrace Mitigation:**
  1. Database passwords, MinIO keys, and JWT secrets are injected strictly via Docker secrets/environment files (`.env`), never stored in prompts or source code.
  2. System prompts contain zero credentials or sensitive network topology details.
  3. Query responses serialize only typed result objects; internal database stack traces are suppressed.

---

### 2.3 LLM03: Supply Chain Vulnerabilities
- **Threat:** Compromised third-party Python wheels or malicious model checkpoints hosted on public repositories.
- **AstraTrace Mitigation:**
  1. Mandatory dependency pinning in `pyproject.toml` with `pip-tools` hash verification.
  2. Model weights packaged exclusively in **Safetensors** format; legacy Python `.pkl` / `.bin` checkpoints are prohibited.
  3. Pre-staged model manifests declare SHA-256 hashes; backend verifies weights on startup and aborts if hashes mismatch.

---

### 2.4 LLM04: Data & Model Poisoning
- **Threat:** Injecting corrupted scenes, biased labels, or flood of false review confirmations into the feedback store to compromise future rerankers.
- **AstraTrace Mitigation:**
  1. Ingestion allowlisting: Scenes must pass GDAL header validation, CRS sanity checks, and checksum verification.
  2. Multi-analyst quorum required before feedback is admitted to the offline reranker training pool.
  3. Offline evaluation gate: Candidate models must pass the golden benchmark before promotion.

---

### 2.5 LLM05: Improper Output Handling
- **Threat:** Cross-Site Scripting (XSS) or injection payloads reflected in the web dashboard via search query echoes or GeoJSON attribute displays.
- **AstraTrace Mitigation:**
  1. Strict JSON serialization via Pydantic v2.
  2. React DOM automatically escapes rendered string properties.
  3. MapLibre GL JS vector source validation ensures geometry coordinates contain only valid numeric floats.

---

### 2.6 LLM06: Excessive Agency & Tool Abuse
- **Threat:** AI agent gaining access to operating system shells, arbitrary file deletion, or unbounded network requests.
- **AstraTrace Mitigation:**
  1. The LLM has **zero tool execution authority**. It is purely a query parser and summarizer.
  2. Specialized execution engines (retrieval, change detection, quality gating) are invoked deterministically by the FastAPI backend service.
  3. Docker containers execute as non-root users (`uid 1000:1000`).

---

### 2.7 LLM07: System Prompt Leakage
- **Threat:** Prompt extraction techniques designed to steal internal operational guidelines.
- **AstraTrace Mitigation:**
  1. Instructions are hardcoded in the local inference binary configuration.
  2. GBNF grammar forces the output stream to begin with `{"semantic_concept": ...}`. Any attempt to output `"My system prompt is..."` is rejected at the token sampling level.

---

### 2.8 LLM08: Vector & Embedding Weaknesses
- **Threat:** Adversarial pixel perturbations in satellite imagery designed to manipulate cosine distance and evade semantic detection.
- **AstraTrace Mitigation:**
  1. Multisensor cross-verification: Optical pixel perturbations do not transfer to SAR microwave backscatter.
  2. Preprocessing filters (resampling, normalization, blur) attenuate high-frequency adversarial noise.
  3. Spatial and temporal bounding box constraints limit the candidate search space.

---

### 2.9 LLM09: Misinformation & Causal Hallucination
- **Threat:** Generating fabricated operational intelligence, invented military facilities, or false change attribution.
- **AstraTrace Mitigation:**
  1. Evidence-first generation: The LLM receives precomputed change statistics and scene IDs; it cannot generate spatial coordinates.
  2. Strict abstention rule: If evidence is missing, the system outputs `INSUFFICIENT EVIDENCE`.

---

### 2.10 LLM10: Unbounded Consumption / Denial of Service
- **Threat:** Uploading massive GeoTIFF decompression bombs (zip bombs) or submitting queries covering entire continents to exhaust server RAM and GPU memory.
- **AstraTrace Mitigation:**
  1. File size hard limit: 2 GB per scene in prototype.
  2. Raster dimension cap: GDAL header inspection rejects rasters with $W, H > 15,000\text{ pixels}$.
  3. Spatial query bounding box area limit ($Area \le 10,000\text{ km}^2$) and `top_k \le 100`.
  4. Docker container memory ceiling (`mem_limit: 8g`) prevents host kernel lockup.

---

## 3. Geospatial & File Security Hardening

- **GDAL Sandboxing:** Executed inside a dedicated backend container with environment flags:
  `GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR`, `CPL_LOG=/dev/null`, and memory caching caps (`GDAL_CACHEMAX=512`).
- **Path Traversal Defense:** All user-supplied file URIs (`file:///data/...`) are sanitized using Python's `os.path.realpath()`. The backend verifies that the resolved path strictly starts with `/data/staging/`. Requests with `..` or leading slashes outside the sandbox are rejected with HTTP 403.
- **Audit Immutability:** PostgreSQL database user `astratrace_app` is granted strictly `SELECT` and `INSERT` privileges on `audit_events`. `UPDATE` and `DELETE` queries are rejected at the database engine level.

---

## 4. Air-Gap & Network Verification Protocol

The offline deployment profile (`infrastructure/offline-compose.yml`) enforces complete isolation:
```yaml
networks:
  internal_mesh:
    internal: true # Disables default gateway and outbound NAT routing
```
- **Verification Command:**
  ```bash
  docker compose -f infrastructure/offline-compose.yml exec backend ping -c 1 8.8.8.8
  # Expected Output: Network is unreachable (Exit code != 0)
  ```
- **Zero External Calls Invariant:** Running AstraTrace end-to-end under Wireshark or `tcpdump` must yield zero outbound UDP/TCP packets to external IP addresses.

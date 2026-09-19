# AstraTrace 2.0 — SIH 2026 5-Minute Live Demonstration Runbook
**Project:** AstraTrace  
**SIH Problem ID:** SIH26227  
**Sponsor:** Ministry of Defence / Indian Army, Directorate General of Information Systems (DGIS)  
**Session Format:** 5-Minute Turn-by-Turn Live Evaluator Demonstration  
**Environment:** 100% Offline / Air-Gapped Sovereign Intelligence Workstation  

---

## 1. Quick Launch Checklist (Pre-Demo)

Before the evaluation committee arrives, execute the following steps to ensure all services are ready:

```powershell
# 1. Open Terminal 1: Launch Backend API
cd apps/backend
.\.venv\Scripts\Activate.ps1
uvicorn apps.backend.app.main:app --host 0.0.0.0 --port 8000

# 2. Open Terminal 2: Launch Frontend UI
cd apps/frontend
npm run dev

# 3. Open Browser at: http://localhost:5173
# Verify: Green pulsing [AIR-GAPPED (100% OFFLINE)] badge in top header.
```

---

## 2. 5-Minute Turn-by-Turn Demonstration Script

```
┌──────────────┬────────────────────────────────────────────────────────────────────────┐
│ Timeline     │ Demonstration Segment & Live Action                                    │
├──────────────┼────────────────────────────────────────────────────────────────────────┤
│ 00:00–00:45  │ Segment 1: Sovereign Air-Gap Boot & System Health Baseline            │
│ 00:45–01:45  │ Segment 2: Multi-Modal Natural Language Satellite Search & Slots       │
│ 01:45–02:30  │ Segment 3: 7 Comparison Modes & Bitemporal Change Detection           │
│ 02:30–03:15  │ Segment 4: Multispectral Quality Gate & False-Alarm Suppression        │
│ 03:15–04:00  │ Segment 5: Unsupervised Clustering & Anomaly Discovery                │
│ 04:00–04:45  │ Segment 6: Cryptographic Provenance DAG & Real-Time Tamper Detection   │
│ 04:45–05:00  │ Segment 7: Forensic Evidence Dossier Export & Benchmark Modal          │
└──────────────┴────────────────────────────────────────────────────────────────────────┘
```

---

### Segment 1: Sovereign Air-Gap Boot & System Health (00:00 – 00:45)
- **Evaluator Focus:** Verification of sovereign offline execution with zero external cloud calls.
- **Presenter Script:**
  > *"Respected Evaluators and Defence Representatives: AstraTrace is booting in a strictly air-gapped sovereign environment. Notice that `offline_mode` is active with zero external network dependencies. All maps, fonts, AI inference, and geospatial catalogs run entirely on this local workstation."*
- **Live Action:**
  - Point to the green pulsing **`[AIR-GAPPED (100% OFFLINE)]`** badge in the mission header.
  - Run terminal verification in Terminal 3:
    ```powershell
    python scripts/verify_foundation.py
    ```
  - Show on screen: All 13 foundation suites pass with `[PASS]`, including socket-level zero egress verification.

---

### Segment 2: Multi-Modal Natural Language Satellite Search (00:45 – 01:45)
- **Evaluator Focus:** Discovering remote infrastructure using semantic concepts rather than manual coordinates.
- **Presenter Script:**
  > *"An intelligence analyst enters a natural language query: 'industrial warehouse storage along transport corridors'. Notice how our offline slot parser breaks this into semantic tokens. In under 45 milliseconds, our 512-dimensional orthogonal vector index surfaces candidate observations across wide geographic boundaries."*
- **Live Action:**
  - Type in the search bar: `"industrial warehouse storage along highway"`
  - Highlight the extracted slot pills: `[TARGET: industrial warehouse]` `[CONTEXT: highway]`
  - Click Search. Show retrieved tiles ranked by semantic cosine score ($S_{\text{semantic}} > 0.85$).
  - Click the **Image-to-Image Sim** button to demonstrate visual K-NN similarity matching.

---

### Segment 3: 7 Comparison Modes & Bitemporal Change (01:45 – 02:30)
- **Evaluator Focus:** High-precision bitemporal visual analysis and adaptive Otsu change detection.
- **Presenter Script:**
  > *"To analyze infrastructure progression over time, AstraTrace provides 7 tactical comparison modes inspired by NASA Worldview."*
- **Live Action:**
  - Select a change candidate tile from the results list.
  - Click through the comparison mode pills on the top of the map:
    1. **SWIPE:** Drag the split curtain divider across the scene.
    2. **OPACITY:** Adjust the cross-fade slider between T1 (Before) and T2 (After).
    3. **SPYGLASS:** Move the circular loupe lens over the map to reveal new construction beneath the lens.
    4. **SIDE-BY-SIDE:** Dual synchronized viewports showing before/after in tandem.
    5. **DIFFERENCE:** High-contrast difference blend highlighting alterations.
    6. **CHANGE MASK:** Display the clamped Otsu binary mask highlighting detected structures.
  - Interact with the **Timeline Scrubber** at the bottom: toggle between T1 and T2 epoch pins.

---

### Segment 4: Multispectral Quality Gate & False-Alarm Suppression (02:30 – 03:15)
- **Evaluator Focus:** Solving the critical defense problem of false alarms caused by clouds and shadows.
- **Presenter Script:**
  > *"Traditional pixel differencing floods commanders with false alarms caused by clouds and shadows. AstraTrace passes all observations through our multispectral Quality Gate. Watch what happens on a cloud-contaminated scene: raw differencing reports 6,400 changed pixels, but our Quality Gate suppresses 100% of them as atmospheric noise."*
- **Live Action:**
  - Open the **CHANGE** tab in the right Evidence Inspector.
  - Show the **Quality Gate Verdict**: `QUALITY_SUPPRESSED (Cloud Contamination)`.
  - Highlight the metric: **False-Alarm Reduction Rate: 100.0%**.
  - Show that genuine structural construction in clean scenes achieves **100% True Positive Preservation**.

---

### Segment 5: Unsupervised Clustering & Anomaly Discovery (03:15 – 04:00)
- **Evaluator Focus:** Discovering unknown construction patterns in unindexed frontier sectors.
- **Presenter Script:**
  > *"When surveying vast frontier areas without prior target intelligence, analysts cannot formulate specific queries. AstraTrace runs unsupervised K-Means and DBSCAN clustering across the latent embedding space, grouping similar development patterns into tactical clusters."*
- **Live Action:**
  - Click the **CLUSTERS** tab in the Evidence Inspector.
  - View identified clusters with cluster centroids, member tile counts, and dispersion metrics.
  - Click on a cluster to focus the map on the clustered frontier region.

---

### Segment 6: Cryptographic Provenance DAG & Tamper Detection (04:00 – 04:45)
- **Evaluator Focus:** Forensic chain-of-custody and automated tamper interception.
- **Presenter Script:**
  > *"Every piece of intelligence must be admissible and tamper-evident. Every tile, vector, and mask forms an immutable SHA-256 Directed Acyclic Graph. If a rogue actor or malicious code modifies even a single pixel in an archive tile, the cryptographic verifier immediately detects it."*
- **Live Action:**
  - Click the **PROVENANCE** tab in the Evidence Inspector.
  - Show the live lineage tree linking Raw Scene $\to$ Ingested Tile $\to$ 512-D Embedding $\to$ Change Mask $\to$ Analyst Review.
  - Show the green **`[PROVENANCE INTEGRITY: VERIFIED]`** status with root SHA-256 checksums.

---

### Segment 7: Evidence Export & Benchmark Dossier Modal (04:45 – 05:00)
- **Evaluator Focus:** Actionable tactical intelligence hand-off and quantitative benchmark proof.
- **Presenter Script:**
  > *"Finally, analysts can adjudicate evidence (CONFIRM / REJECT / ESCALATE) and export a signed forensic briefing dossier. To conclude, here is our live automated benchmark suite displaying 100% reproducible metrics across all 139 tests."*
- **Live Action:**
  - In the **AUDIT** tab, click **CONFIRM** and add a note: `"Verified forward helipad grading"`.
  - Click **Export Forensic Package** to generate a signed evidence archive.
  - Click the **`[BENCHMARK DOSSIER]`** button in the top mission bar to open the live modal.
  - Display the live quantitative benchmarks:
    - **Precision@5:** 0.2000 (2.0x vs baseline)
    - **Latency:** 41.9 ms
    - **FARR:** 100.0%
    - **Test Pass Rate:** 139 / 139 (100%)
  - Conclude: *"AstraTrace delivers sovereign, air-gapped, accountable geospatial intelligence for India's national security."*

---

## 3. Fallback & Troubleshooting Runbook

If any component experiences technical issues during evaluation:

| Scenario | Immediate Action | Fallback Command |
| :--- | :--- | :--- |
| Browser display disconnects | Switch to terminal demonstration | `python -m astratrace.evaluate --top-k 5` |
| Port conflict on 8000 | Kill occupying process or change port | `uvicorn apps.backend.app.main:app --port 8080` |
| Vector index missing | Rebuild index from catalog | `python scripts/index_embeddings.py` |
| Evaluation report cache stale | Force re-run evaluation suite | `python scripts/run_evaluation.py` |

# AstraTrace — Official SIH 2026 Final Demonstration Guide
**Project:** AstraTrace  
**SIH Problem ID:** SIH26227  
**Sponsor:** Ministry of Defence / Indian Army, Directorate General of Information Systems (DGIS)  
**Session Format:** 5-Minute Live Evaluator Demonstration & Operational Workflow  
**Environment:** 100% Offline / Air-Gapped Sovereign Intelligence Workstation  

---

## 1. Demonstration Narrative & Tactical Context

AstraTrace is an air-gapped geospatial intelligence platform purpose-built for the **Directorate General of Information Systems (DGIS)** to solve critical defense reconnaissance bottlenecks:
1. Satellite archives are too vast for manual human scanning.
2. Legacy keyword searches miss visual concepts that are not explicitly tagged.
3. Traditional pixel differencing floods analysts with false alarms caused by clouds, shadows, and seasonal vegetation changes.
4. Black-box AI models hallucinate coordinates and lack forensic accountability.

AstraTrace solves these challenges using **Evidence-First AI**, **Orthogonal 512-D Semantic Projections**, **Multispectral Quality-Gated Change Detection**, and **Cryptographic SHA-256 Provenance DAGs**.

---

## 2. 5-Minute Turn-by-Turn Live Demonstration Script

```
┌──────────────┬────────────────────────────────────────────────────────────────────────┐
│ Timeline     │ Demonstration Segment & Live Action                                    │
├──────────────┼────────────────────────────────────────────────────────────────────────┤
│ 00:00–00:45  │ Segment 1: Sovereign Air-Gap Boot & System Health Baseline            │
│ 00:45–01:45  │ Segment 2: Multi-Modal Natural Language Satellite Search               │
│ 01:45–02:30  │ Segment 3: Bitemporal Change Detection & Infrastructure Shift Detection│
│ 02:30–03:15  │ Segment 4: False-Alarm Suppression (Cloud, Shadow, NoData Defense)     │
│ 03:15–04:00  │ Segment 5: MapLibre GL JS Evidence-First Analyst Triage                │
│ 04:00–04:45  │ Segment 6: Cryptographic Provenance DAG & Real-Time Tamper Detection   │
│ 04:45–05:00  │ Segment 7: Forensic Evidence Dossier Export & Final Conclusion        │
└──────────────┴────────────────────────────────────────────────────────────────────────┘
```

---

### Segment 1: Sovereign Air-Gap Boot & System Health Baseline (00:00 – 00:45)
- **Evaluator Focus:** Verification of sovereign offline deployment without external cloud calls.
- **Presenter Script:**
  > *"Respected Evaluators and Defence Representatives: AstraTrace is booting in a strictly air-gapped sovereign environment. Notice that `offline_mode` is set to `true`. Our system executes entirely on local compute with zero telemetry, zero cloud inference APIs, and zero external font or map tile requests."*
- **Terminal Command:**
  ```powershell
  python scripts/verify_foundation.py
  ```
- **Visible Proof on Screen:**
  - All 13 verification suites pass with `[PASS]`.
  - `[PASS] Milestone 9 Air-Gap Network Isolation: Zero outbound network calls verified under strict socket interception`.
  - Live system status confirms `metadata_catalog`, `vector_index`, `quality_gate`, and `provenance_verifier` are operational.

---

### Segment 2: Multi-Modal Natural Language Satellite Search (00:45 – 01:45)
- **Evaluator Focus:** Discovering remote infrastructure using semantic concepts rather than manual bounding boxes.
- **Presenter Script:**
  > *"An intelligence analyst queries: 'industrial warehouse storage along transport corridors'. In legacy systems, this requires knowing the exact tile ID. In AstraTrace, our offline 512-D unit sphere projection executes in under 6 milliseconds, ranking candidate observation patches across wide geographic boundaries."*
- **Live UI Action / CLI:**
  ```powershell
  python scripts/semantic_search.py --query "industrial warehouse storage" --top-k 3
  ```
- **Visible Proof on Screen:**
  - Ranked tiles surfaced with semantic similarity scores ($S_{\text{semantic}} > 0.85$).
  - Retrieval benchmark table shows **2.0x Precision@5** and **2.0x MRR** improvement over keyword matching in just **5.9 ms**.

---

### Segment 3: Bitemporal Change Detection (01:45 – 02:30)
- **Evaluator Focus:** Automated detection of newly constructed border infrastructure between two satellite acquisitions ($T_1$ and $T_2$).
- **Presenter Script:**
  > *"Here we compare two observation passes over the same border sector: January 2023 versus December 2024. Notice that our baseline detector applies normalized spectral differencing $\Delta \mathbf{S}$, adaptive Otsu thresholding, and morphological filtering to isolate physical construction."*
- **Terminal Command / UI Action:**
  ```powershell
  python scripts/detect_change.py --t1 data/processed/scn_sentinel-2_20230115_96ed9480/tile_0001.tif --t2 data/processed/scn_sentinel-2_20241222_7acad713/tile_0001.tif
  ```
- **Visible Proof on Screen:**
  - Highlighting 4,800 changed pixels corresponding to new structural foundations.
  - Physical change classified deterministically as `construction` based on spectral index deltas ($\Delta \text{Brightness} > 0.15$).

---

### Segment 4: False-Alarm Suppression & Quality Gate Defense (02:30 – 03:15)
- **Evaluator Focus:** Eliminating false alarms caused by atmospheric disturbances without human intervention.
- **Presenter Script:**
  > *"Every defense satellite system suffers from false alarms caused by clouds and cloud shadows. Notice what happens when a dense cloud or cloud shadow passes over the target: raw pixel differencing erroneously flags 6,400 changed pixels! But AstraTrace's Quality Gate detects the anomalous optical signature, automatically declaring `QUALITY_SUPPRESSED` and reducing false alarms by 100% while preserving 100% of real construction changes."*
- **Terminal Command:**
  ```powershell
  python scripts/evaluate_quality_gate.py
  ```
- **Visible Proof on Screen:**
  - Cloud challenge: 6,400 pixels suppressed $\to$ 0 false alarms.
  - Shadow challenge: 3,600 pixels suppressed $\to$ 0 false alarms.
  - NoData challenge: Correctly abstains and marks as `UNCERTAIN` for analyst review.

---

### Segment 5: MapLibre GL JS Evidence-First Tactical Triage (03:15 – 04:00)
- **Evaluator Focus:** Human-in-the-loop triage interface adhering to strict non-retraining guardrails.
- **Presenter Script:**
  > *"In the tactical web workstation, every result satisfies our 8-Dimension Evidence Contract: WHAT, WHERE, WHEN, WHICH, WHY, CONFIDENCE, EVIDENCE, and PROVENANCE. The analyst views the before/after RGB preview, inspects the binary change mask, and records an adjudication: `CONFIRMED`. Crucially, in accordance with defense safety guidelines, analyst feedback is logged for audit and **never** autonomously alters model weights."*
- **Live UI Action:**
  - Show MapLibre GL JS map with candidate footprint highlighted.
  - Show Evidence Card with 8 dimensions populated.
  - Click `Confirm Observation` button; review queue status updates to `CONFIRMED`.

---

### Segment 6: Lineage Graph & Real-Time Tamper Detection (04:00 – 04:45)
- **Evaluator Focus:** Forensic auditability and adversarial tamper resilience.
- **Presenter Script:**
  > *"How can a military commander trust that this satellite imagery was not intercepted or altered? Every single tile, change mask, and embedding is linked into a multi-level Provenance DAG. Watch as we run our cryptographic verifier: all 4 artifacts match their recorded SHA-256 hashes. Now, let us simulate a cyber compromise by modifying just 4 bytes of an image on disk: AstraTrace flags the file as `TAMPERED` in under 22 milliseconds."*
- **Terminal Command:**
  ```powershell
  python scripts/provenance_cli.py --verify scn_sentinel-2_20230115_96ed9480_t0000
  ```
- **Visible Proof on Screen:**
  - Reconstructed 12-node DAG trace.
  - Verified streaming SHA-256 checksums.
  - Demonstration of immediate red flag on corrupted input.

---

### Segment 7: Forensic Evidence Dossier & Conclusion (04:45 – 05:00)
- **Evaluator Focus:** Exportable legal chain-of-custody for operational intelligence briefings.
- **Presenter Script:**
  > *"Finally, the analyst exports a sealed Forensic Evidence Dossier: a self-contained, air-gapped JSON package containing the complete lineage DAG, metadata, verification proof, and digital signature. AstraTrace delivers end-to-end, reproducible, air-gapped geospatial intelligence for the Indian Armed Forces."*
- **Visible Proof on Screen:**
  - Exported dossier at `data/processed/exports/dossier_*.json` with top-level SHA-256 integrity seal.
  - Complete compliance with Problem ID SIH26227.

---

## 3. Evaluator Q&A Preparedness Matrix

| Anticipated Evaluator Question | Authoritative Architectural Response | Codebase Proof |
| :--- | :--- | :--- |
| **"What happens if an analyst is deployed in a forward border bunker with zero internet?"** | AstraTrace is 100% offline-first. All vector projections, differencing algorithms, database storage, and MapLibre tile renderers run locally on the workstation without a single internet packet. | `tests/backend/test_milestone9_provenance_hardening.py` (socket interception test). |
| **"How do you prevent the AI from hallucinating coordinates or making up fake installations?"** | AstraTrace uses extractive, grounded retrieval. Results cite real GeoTIFF pixel footprints, projected UTM coordinates, and immutable SHA-256 hashes from the metadata catalog. | `apps/backend/app/schemas/search.py` (8-dimension Evidence-First contract). |
| **"Does analyst feedback trigger online learning or model retraining?"** | **No.** Under defense safety rules, analyst reviews are audit-only and stored in `analyst_reviews`. Autonomous retraining in production is strictly forbidden to prevent adversarial poisoning and distribution drift. | `apps/backend/app/services/review/service.py`. |
| **"What if the satellite image is partially obscured by monsoon clouds?"** | The Quality Gate detects cloud reflectance signatures across visible and NIR bands, suppresses false alarms, and flags degraded observations for human review rather than issuing false alerts. | `apps/backend/app/services/quality/quality_gate.py`. |

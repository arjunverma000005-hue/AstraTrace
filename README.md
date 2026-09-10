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
python scripts/verify_foundation.py
```

---

## 7. Offline-First Principles
AstraTrace enforces complete air-gap readiness:
- Zero runtime external cloud API dependencies (no OpenAI, Gemini, or external hosted services).
- Self-contained Docker offline profile (`docker/offline-compose.yml`) configures `internal: true` network mesh dropping outbound traffic.
- Pre-staged datasets and local Safetensors model checkpoints.

---

## 8. License
Apache 2.0 License. Developed for Smart India Hackathon 2026.

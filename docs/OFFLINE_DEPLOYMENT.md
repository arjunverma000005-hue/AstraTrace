# AstraTrace 2.0 — Offline & Air-Gapped Deployment Guide
**Project:** AstraTrace  
**SIH Problem ID:** SIH26227  
**Sponsor:** Ministry of Defence / Indian Army, Directorate General of Information Systems (DGIS)  
**Theme:** Space Technology  
**Classification:** DEFENCE UNCLASSIFIED // DEPLOYMENT RUNBOOK  

---

## 1. Tactical Philosophy: Sovereign Air-Gap Invariant

Modern defense systems deployed in sensitive facilities (Operations Rooms, Tactical Field Posts, Command Bunkers) must operate in complete isolation from the public internet. Software solutions that rely on external API keys (e.g., Google Maps, Mapbox, OpenAI) or remote CDNs for CSS, fonts, and JavaScript libraries represent severe security vulnerabilities and operational points of failure.

AstraTrace is engineered with a **Strict Air-Gap Invariant**:
- **Zero Outbound Sockets:** The system makes no remote HTTP/HTTPS or DNS requests.
- **Zero Remote Assets:** All map rendering, raster tiles, UI icons (Lucide), and typography are bundled locally.
- **Zero Cloud AI Egress:** Vector projections, semantic matching, and change detection execute 100% on local CPU/GPU hardware.

---

## 2. Automated Air-Gap Verification (Socket Interception)

AstraTrace includes an automated test that intercepts network activity at the operating system socket layer to prove air-gap compliance:

### 2.1 Test Architecture (`tests/backend/test_airgap_no_outbound_network.py`)
```python
import socket
import pytest

@pytest.fixture(autouse=True)
def airgap_socket_trap(monkeypatch):
    original_connect = socket.socket.connect

    def forbidden_connect(self, address):
        host, port = address[0], address[1]
        # Allow loopback/local IPC only
        if host in ("127.0.0.1", "localhost", "::1", "0.0.0.0"):
            return original_connect(self, address)
        raise PermissionError(f"AIR-GAP VIOLATION: Attempted outbound connection to {host}:{port}")

    monkeypatch.setattr(socket.socket, "connect", forbidden_connect)
```

### 2.2 Execution Command
```powershell
pytest tests/backend/test_airgap_no_outbound_network.py -v
```
**Output:**
```
tests/backend/test_airgap_no_outbound_network.py::test_airgap_no_outbound_network PASSED [100%]
```

---

## 3. Deployment Topologies

AstraTrace supports four verified deployment options depending on the operational environment.

### Option A: Single Unified Production Container (Recommended for Ruggedized Field Laptops)
Builds the React frontend and Python backend into a single self-contained image where FastAPI directly serves the production SPA and REST API on port 8000:

```powershell
# 1. Build unified image
docker build -t astratrace:latest .

# 2. Run container (mapping port 8000)
docker run -d --name astratrace_app \
  -p 8000:8000 \
  -v ${PWD}/data:/app/data \
  -e OFFLINE_MODE=true \
  astratrace:latest

# 3. Access in local browser
# Web Interface: http://localhost:8000
# API Documentation: http://localhost:8000/docs
```

---

### Option B: Multi-Container Docker Compose (Standard Microservices)
Spins up separate backend and frontend containers connected through an internal Docker bridge with an Nginx reverse proxy:

```powershell
# Launch services
docker compose -f docker/docker-compose.yml up --build -d

# Service Endpoints:
# Frontend Analyst UI: http://localhost:3000
# Backend REST API:    http://localhost:8000
```

---

### Option C: Strict Air-Gapped Compose with Internal Mesh (Classified Operations)
Uses Docker's `internal: true` network flag, which drops the default gateway and guarantees that neither the frontend nor backend container can establish internet connections:

```yaml
# docker/offline-compose.yml snippet
networks:
  airgap_mesh:
    driver: bridge
    internal: true # Disables external gateway routing
```

```powershell
# Launch strict air-gapped stack
docker compose -f docker/offline-compose.yml up --build -d
```

---

### Option D: Bare-Metal / Native Virtual Environment (Development & Offline Field Testing)

#### 1. Backend Service:
```powershell
cd apps/backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1    # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"

# Launch FastAPI
uvicorn apps.backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Frontend Analyst UI:
```powershell
cd apps/frontend
npm install
npm run dev
# Access: http://localhost:5173
```

---

## 4. Configuration Reference

All settings can be configured via environment variables or a `.env` file:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `APP_ENV` | `production` | Deployment mode (`development`, `production`). |
| `OFFLINE_MODE` | `true` | Enforces local execution and disables external telemetry. |
| `API_HOST` | `0.0.0.0` | Network binding interface. |
| `API_PORT` | `8000` | Port for the backend API service. |
| `LOG_LEVEL` | `INFO` | Structured JSON log verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `DATA_ROOT` | `data/` | Path to raw and processed data tiers. |
| `METADATA_DB_URL` | `sqlite:///data/processed/metadata.db` | Path to the relational spatial catalog. |
| `EMBEDDINGS_DIR` | `data/processed/embeddings` | Storage location for FAISS binary indices. |
| `AUDIT_LOG_DIR` | `data/processed/audit` | Storage location for tamper-evident JSON-L logs. |

---

## 5. Health Check & Verification

Once deployed, verify system readiness using the health endpoint:

```powershell
curl http://localhost:8000/api/v1/health
```

**Expected JSON Response:**
```json
{
  "status": "HEALTHY",
  "app_name": "AstraTrace",
  "app_version": "0.1.0",
  "offline_mode": true,
  "timestamp": "2026-09-19T10:50:00.000Z",
  "components": {
    "catalog_db": "ONLINE",
    "vector_index": "ONLINE",
    "quality_gate": "ONLINE",
    "change_detector": "ONLINE",
    "provenance_verifier": "ONLINE"
  }
}
```

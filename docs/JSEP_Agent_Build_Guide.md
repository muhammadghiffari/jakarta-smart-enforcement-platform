# JSEP — AI Agent Build Guide
> **Reference Documents**: JSEP_PRD_v5_REVISED.md (v5.1.3, AGENT-READY) · DESIGN.md  
> **Target**: Jakarta Smart Enforcement Platform — AI Open Innovation Challenge 2026  
> **Agent**: Read this file top-to-bottom before writing a single line of code. Every section links to the PRD section it implements.

---

## ⚠️ Agent Rules — Read First

```
RULE-01  Never hardcode secrets. All API keys via os.environ[]. Use .env + python-dotenv.
RULE-02  USE_MOCK_APIS=true in ALL demo environments. Government APIs are STUB only.
RULE-03  Never auto-submit E-TLE. Every ticket requires human officer approval (FR-ETLE-02).
RULE-04  Confidence < 0.75 → human review queue. Never promote to E-TLE automatically.
RULE-05  Consult DESIGN.md for every UI component: colors, typography, spacing, component names.
RULE-06  H3 Resolution 10 is operator default; Resolution 9 is executive rollup. Never treat Res-9 as 174 m².
RULE-07  YOLO26 is primary. Fallback is YOLOv11. Controlled by DETECTION_MODEL env var.
RULE-08  All video evidence hashed SHA-256 before storage. Hash stored in evidence_packages table.
RULE-09  audit_log table is append-only. Never UPDATE or DELETE from it. PostgreSQL rules enforce this.
RULE-10  Blockchain/SBT removed. Citizen points → citizen_points DB table. No Polygon/Fabric code.
```

## Architecture Refocus

Build JSEP as a closed-loop enforcement system, not a general smart-city platform.

Core v1 path:
`CCTV / DISHUB camera / CRM / JAKI / ATCS`
→ `vehicle detection + tracking + ANPR + duration`
→ `violation event + evidence package + camera readiness`
→ `hotspot analytics + officer placement + E-TLE camera placement`
→ `dispatch + human approval + executive reporting`

Future path:
`cross-camera ReID`, `Ganjil-Genap`, `LLM legal narrative generation`, `live government registry lookups`, and similar stretch items stay out of the core build.

Core legal reference path:
JSEP still needs legal basis, sanction/fine references, evidence checklists, and static report wording in v1. Build this as a deterministic lookup service from reviewed YAML/JSON fixtures and database tables. Do not depend on an LLM for rules, sanctions, fines, or executive summary facts.

Gemini API path:
If a Gemini API key is available, use it only for optional reviewer-assist drafting and executive-summary wording after deterministic facts are assembled. The system must still work with `ENABLE_LLM_DRAFTING=false`.

Swarm/AI Insight path:
Do not add a separate swarm framework in v1. Kafka consumers already act like autonomous processing services. If time permits, add a read-only AI Insight Agent that summarizes deterministic violation clusters for the executive dashboard. It must never create, verify, approve, dismiss, or submit violations.

Docker path:
Docker is useful for reproducible packaging, but Docker Desktop is not required. Docker Build Cloud can build images remotely, while runtime services must run somewhere else: local Docker Engine, a remote VM, or managed cloud services.

---

## Repository Structure

Create this exact layout before writing any code:

```
jsep/
├── .env.example                 ← copy to .env, never commit .env
├── .env                         ← gitignored
├── docker-compose.yml           ← full local stack
├── docker-compose.demo.yml      ← lightweight demo stack
├── Makefile                     ← task runner for agent commands
│
├── services/
│   ├── ingestion/               ← L1: RTSP/HLS capture (FR-VID-01–06)
│   ├── ai_pipeline/             ← L2: YOLO + ANPR + rules (FR-DET, FR-ANPR, FR-VIO)
│   ├── analytics/               ← L4: H3 hotspot + MCLP (FR-ANA-01–07)
│   ├── legal_reference/         ← deterministic legal/sanction lookup (FR-LEGAL-01)
│   ├── insight_agent/           ← optional read-only Gemini insight summaries (FR-INSIGHT-01)
│   ├── api/                     ← L5: FastAPI REST + WebSocket (Section 10)
│   ├── future/                  ← future-only features, not core v1
│   └── jaki_ingest/             ← JAKI/CRM webhook receiver (FR-VIO-08)
│
├── frontend/                    ← React 18 + TypeScript dashboard (FR-DASH-01–10)
│   ├── src/
│   │   ├── components/          ← reference DESIGN.md for every component here
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── stores/              ← Zustand stores
│   │   └── lib/
│   └── public/
│
├── ml/
│   ├── train_jsep.py            ← YOLO26 fine-tuning (PRD Section 11.4)
│   ├── augmentation.py          ← OpenCV pipeline (PRD Section 11.3)
│   ├── anpr_pipeline.py         ← 8-stage ANPR (PRD Section 6.2)
│   └── evaluate.py              ← KPI validation (PRD Section 3.2)
│
├── legal_reference/
│   ├── legal_references.yaml    ← legal basis catalog, reviewed fixture
│   ├── sanction_references.yaml ← sanction/fine catalog, reviewed fixture
│   └── violation_legal_map.yaml ← violation → legal/sanction/evidence mapping
│
├── rag_corpus/                  ← future-only corpus for optional LLM narrative drafting
│   └── (keep out of the v1 critical path)
│
├── migrations/
│   ├── alembic.ini
│   └── versions/                ← One migration file per schema change
│
├── fixtures/
│   └── vehicle_registry_mock.json  ← 500+ synthetic Jakarta plates (PRD Section 7.10)
│
├── templates/
│   └── berita_acara_static.j2   ← deterministic BA template using legal_reference data
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── demo_scenarios/          ← 5 demo scripts (PRD Section 15.3)
│
└── docs/
    ├── JSEP_PRD_v5_REVISED.md   ← PRD reference copy
    └── DESIGN.md                ← UI design system (consult for all frontend work)
```

---

## Environment Variables

**Create `.env.example` with these exact keys.** Agent copies to `.env` and fills values.

```bash
# === DETECTION MODEL (PRD Section 6.1) ===
DETECTION_MODEL=yolo26n.pt          # swap to yolo11n.pt if YOLO26 unavailable
DETECTION_CONFIDENCE_THRESHOLD=0.45

# === DATABASE ===
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=jsep
POSTGRES_USER=jsep_user
POSTGRES_PASSWORD=changeme_local
TIMESCALEDB_ENABLED=true

# === KAFKA ===
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC_VIOLATIONS_RAW=violations.raw
KAFKA_TOPIC_VIOLATIONS_CONFIRMED=violations.confirmed
KAFKA_TOPIC_ALERTS=alerts.verified
KAFKA_TOPIC_DLQ=violations.dlq

# === REDIS ===
REDIS_URL=redis://localhost:6379/0

# === MINIO ===
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_EVIDENCE=jsep-evidence
MINIO_BUCKET_MODELS=jsep-models

# === GOVERNMENT APIs — ALWAYS MOCK IN DEMO (PRD Section 7.10) ===
USE_MOCK_APIS=true                  # NEVER set to false in demo
KORLANTAS_API_URL=https://korlantas.polri.go.id/api-etle   # unused when mock
KORLANTAS_CERT_PATH=certs/korlantas.pem                    # unused when mock

# === FUTURE / OPTIONAL (not core v1) ===
ENABLE_LLM_DRAFTING=false           # true only for optional reviewer-assist drafting
ENABLE_AI_INSIGHTS=false            # true only for read-only executive dashboard insights
GEMINI_API_KEY=                     # optional Gemini API key; never commit real keys
GEMINI_MODEL=                       # set from current Google AI Studio model list
CHROMA_DB_PATH=./chroma_db
RAG_CORPUS_PATH=./rag_corpus

# === JAKI INTEGRATION (PRD FR-VIO-08) ===
JAKI_OAUTH_CLIENT_ID=
JAKI_OAUTH_CLIENT_SECRET=
JAKI_WEBHOOK_SECRET=                # HMAC-SHA256 signing key

# === FRONTEND ===
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws

# === DEMO FLAGS ===
DEMO_MODE=true
DEMO_SEED_DATA=true                 # Load fixtures on startup
DEMO_CAMERA_COUNT=10               # Number of simulated camera feeds
```

---

## Phase 0 — Infrastructure Stack

**PRD Reference**: Section 5.4, Section 9.2  
**Outcome**: One working runtime stack. Verify with `make health`.

### 0.0 Runtime Mode Decision

Choose one mode before implementation:

| Mode | Use When | What Runs Services |
|---|---|---|
| `local-compose` | Developer has Docker Engine or Docker Desktop | `docker compose up` runs Postgres, Kafka, Redis, MinIO |
| `cloud-managed` | Developer has no local Docker runtime | Managed Postgres/Timescale, Kafka/Redpanda/Confluent, Redis, S3-compatible storage |
| `remote-vm` | Team wants one shared demo box | Docker Engine on a cloud VM runs the same `docker-compose.yml` |
| `build-cloud` | Need fast image builds without Docker Desktop | Docker Build Cloud builds/pushes images; runtime still uses `cloud-managed` or `remote-vm` |

Important: Docker Build Cloud is a **builder**, not a replacement for running demo services. If only Docker Build Cloud is available, set up `cloud-managed` or `remote-vm` for runtime.

### 0.1 `docker-compose.yml`

Use this only for `local-compose` or `remote-vm`.

```yaml
# docker-compose.yml
version: "3.9"

services:
  postgres:
    image: timescale/timescaledb-ha:pg16-latest
    environment:
      POSTGRES_DB: jsep
      POSTGRES_USER: jsep_user
      POSTGRES_PASSWORD: changeme_local
    ports: ["5432:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U jsep_user -d jsep"]
      interval: 10s
      retries: 5

  kafka:
    image: confluentinc/cp-kafka:7.6.0
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_CONTROLLER_QUORUM_VOTERS: "1@kafka:9093"
      KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,CONTROLLER:PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_LOG_RETENTION_HOURS: 168       # 7-day retention (PRD Section 5.4)
      CLUSTER_ID: jsep-local-dev-001
    ports: ["9092:9092"]
    healthcheck:
      test: ["CMD", "kafka-broker-api-versions", "--bootstrap-server", "localhost:9092"]
      interval: 15s
      retries: 5

  redis:
    image: redis:7.2-alpine
    ports: ["6379:6379"]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports: ["9000:9000", "9001:9001"]
    volumes: [miniodata:/data]

volumes:
  pgdata:
  miniodata:
```

### 0.2 Makefile Commands

Use these commands only for `local-compose` or `remote-vm`.

```makefile
# Makefile
.PHONY: up down health migrate seed topics

up:
	docker compose up -d
	sleep 5
	$(MAKE) topics
	$(MAKE) migrate
	$(MAKE) seed

down:
	docker compose down -v

health:
	@echo "=== Postgres ===" && docker compose exec postgres pg_isready -U jsep_user
	@echo "=== Kafka ===" && docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list
	@echo "=== Redis ===" && docker compose exec redis redis-cli ping
	@echo "=== MinIO ===" && curl -s http://localhost:9000/minio/health/live && echo " MinIO OK"

topics:
	docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 \
	  --create --if-not-exists --topic violations.raw --partitions 6 --replication-factor 1
	docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 \
	  --create --if-not-exists --topic violations.confirmed --partitions 6 --replication-factor 1
	docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 \
	  --create --if-not-exists --topic alerts.verified --partitions 3 --replication-factor 1
	docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 \
	  --create --if-not-exists --topic violations.dlq --partitions 1 --replication-factor 1

migrate:
	cd services/api && alembic upgrade head

seed:
	python scripts/seed_demo_data.py
```

### 0.3 Validation Checkpoint

```bash
make up && make health
# Expected: all 4 services respond healthy
# If Kafka fails: wait 30s more (KRaft mode needs startup time)
```

### 0.4 Docker Build Cloud Packaging

Use this when Docker Build Cloud is available but Docker Desktop is not.

```bash
# Build and push API image
docker buildx build \
  --builder cloud-ORG-BUILDER_NAME \
  --tag ghcr.io/ORG/jsep-api:demo \
  --push services/api

# Build and push frontend image
docker buildx build \
  --builder cloud-ORG-BUILDER_NAME \
  --tag ghcr.io/ORG/jsep-frontend:demo \
  --push frontend
```

Rules:
- Do not pass API keys as build args.
- Use runtime environment variables for `GEMINI_API_KEY`, database URLs, and webhook secrets.
- Push images to a registry, then deploy them to a remote VM, Cloud Run, Kubernetes, or another runtime.

### 0.5 No-Docker Runtime Mapping

For `cloud-managed`, replace local containers with managed services:

| Local Compose Service | Managed Alternative |
|---|---|
| PostgreSQL + PostGIS + TimescaleDB | Timescale Cloud, managed PostgreSQL with PostGIS, or Supabase/Neon for demo if Timescale is not required |
| Kafka | Confluent Cloud, Redpanda Cloud, or single-process in-memory event bus for early prototype |
| Redis | Upstash Redis or managed Redis |
| MinIO | S3, Cloudflare R2, GCS, or other S3-compatible storage |

The code must read all endpoints from `.env`; never hardcode localhost-only infrastructure.

---

## Phase 1 — Database Schema

**PRD Reference**: Section 12 (complete DDL)  
**Outcome**: All tables created, TimescaleDB hypertables configured, PostGIS enabled.

### 1.1 Alembic Setup

```bash
cd services/api
pip install alembic sqlalchemy psycopg2-binary geoalchemy2
alembic init migrations
```

Edit `alembic.ini`:
```ini
sqlalchemy.url = postgresql://jsep_user:changeme_local@localhost/jsep
```

### 1.2 Initial Migration — `migrations/versions/001_initial_schema.py`

Copy **exact DDL from PRD Section 12.1** into the `upgrade()` function:

```python
def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")

    # violations — copy exact CREATE TABLE from PRD 12.1
    op.execute("""
    CREATE TABLE violations (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        camera_id       VARCHAR(64),
        track_id        VARCHAR(64) NOT NULL,
        violation_type  VARCHAR(32) NOT NULL CHECK (violation_type IN (
                            'ILLEGAL_PARKING','BUSWAY_VIOLATION','BICYCLE_LANE_VIOLATION',
                            'ILLEGAL_DROPOFF','GANJIL_GENAP')),
        zone_id         UUID,
        start_time      TIMESTAMPTZ NOT NULL,
        end_time        TIMESTAMPTZ,
        duration_seconds INTEGER,
        status          VARCHAR(32) DEFAULT 'DETECTED',
        composite_confidence DECIMAL(4,3),
        created_at      TIMESTAMPTZ DEFAULT NOW()
    );
    """)
    op.execute("SELECT create_hypertable('violations', 'start_time');")

    # --- paste remaining tables from PRD Section 12.1 in order ---
    # anpr_results, evidence_packages, cameras, zones,
    # h3_hotspots (hypertable), etle_submissions,
    # legal_references, sanction_references, violation_legal_map,
    # crm_reports, unit_dispatches, citizen_points, audit_log (with append-only RULES)

    # CRITICAL: append-only audit_log rules (PRD Section 12.1)
    op.execute("CREATE RULE no_update_audit AS ON UPDATE TO audit_log DO INSTEAD NOTHING;")
    op.execute("CREATE RULE no_delete_audit AS ON DELETE TO audit_log DO INSTEAD NOTHING;")

def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_log CASCADE;")
    op.execute("DROP TABLE IF EXISTS citizen_points CASCADE;")
    op.execute("DROP TABLE IF EXISTS etle_submissions CASCADE;")
    op.execute("DROP TABLE IF EXISTS h3_hotspots CASCADE;")
    op.execute("DROP TABLE IF EXISTS zones CASCADE;")
    op.execute("DROP TABLE IF EXISTS cameras CASCADE;")
    op.execute("DROP TABLE IF EXISTS evidence_packages CASCADE;")
    op.execute("DROP TABLE IF EXISTS anpr_results CASCADE;")
    op.execute("DROP TABLE IF EXISTS violations CASCADE;")
```

### 1.3 Run & Validate

```bash
alembic upgrade head
# Validate:
psql postgresql://jsep_user:changeme_local@localhost/jsep \
  -c "\dt" | grep -E "violations|cameras|zones|h3_hotspots|audit_log"
# Expected: all PRD Section 12.1 core tables listed
psql postgresql://jsep_user:changeme_local@localhost/jsep \
  -c "SELECT * FROM timescaledb_information.hypertables;"
# Expected: violations, h3_hotspots listed
```

---

## Phase 2 — AI Model Pipeline

**PRD Reference**: Sections 6.1–6.4  
**Outcome**: YOLO26 running on sample Jakarta CCTV frames; ANPR returning plate strings.

### 2.1 Python Dependencies

```bash
# ml/requirements.txt
pip install ultralytics>=8.3      # YOLO26/YOLOv11 — check for yolo26 release
pip install boxmot>=10.0          # BoT-SORT + OSNet ReID
pip install paddlepaddle          # PaddleOCR backend
pip install paddleocr             # OCR engine
pip install "real-esrgan"         # super-resolution
pip install opencv-python>=4.9
pip install torch torchvision
pip install h3>=4.0
pip install pulp                  # MCLP optimizer
pip install scipy numpy pandas
pip install python-dotenv
pip install confluent-kafka        # Kafka producer/consumer
pip install minio                 # object storage
pip install fastapi uvicorn[standard]
pip install sqlalchemy alembic geoalchemy2 psycopg2-binary
pip install redis
pip install google-generativeai   # future-only optional narrative drafting
pip install chromadb              # future-only vector store
pip install pyyaml                # legal/sanction reference fixture loader
pip install jinja2                # deterministic BA template
pip install reportlab             # PDF generation
pip install glpk                  # PuLP solver backend
```

### 2.2 Detection Model Setup — `services/ai_pipeline/detector.py`

```python
# services/ai_pipeline/detector.py
import os
from ultralytics import YOLO
from pathlib import Path

# PRD Section 6.1 — model selection with fallback
DETECTION_MODEL = os.getenv("DETECTION_MODEL", "yolo26n.pt")
PLATE_MODEL = os.getenv("PLATE_MODEL", "yolo26s.pt")     # ANPR stage 1
CONFIDENCE_THRESHOLD = float(os.getenv("DETECTION_CONFIDENCE_THRESHOLD", "0.45"))

# 8 classes from PRD Section 11.2
VEHICLE_CLASSES = ["car", "motorcycle", "truck", "bus", "angkot", "bajaj", "bicycle", "pedestrian"]

class VehicleDetector:
    def __init__(self, model_path: str = DETECTION_MODEL):
        self.model = YOLO(model_path)
        self.class_names = VEHICLE_CLASSES

    def detect(self, frame) -> list[dict]:
        """
        Returns list of detections: [{bbox, class_id, class_name, confidence}]
        Filters detections below CONFIDENCE_THRESHOLD (PRD FR-DET-07).
        """
        results = self.model(frame, conf=CONFIDENCE_THRESHOLD, verbose=False)
        detections = []
        for r in results:
            for box in r.boxes:
                detections.append({
                    "bbox": box.xyxy[0].tolist(),      # [x1, y1, x2, y2]
                    "class_id": int(box.cls),
                    "class_name": self.class_names[int(box.cls)],
                    "confidence": float(box.conf),
                })
        return detections

class PlateDetector:
    """Stage 1 of 8-stage ANPR pipeline (PRD Section 6.2)."""
    def __init__(self, model_path: str = PLATE_MODEL):
        self.model = YOLO(model_path)
        self.min_plate_px = (32, 16)  # minimum plate size (PRD FR-ANPR-01)

    def detect_plates(self, frame) -> list[dict]:
        results = self.model(frame, conf=0.5, verbose=False)
        plates = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                w, h = x2 - x1, y2 - y1
                if w >= self.min_plate_px[0] and h >= self.min_plate_px[1]:
                    plates.append({
                        "bbox": [x1, y1, x2, y2],
                        "confidence": float(box.conf),
                        "crop": frame[y1:y2, x1:x2]
                    })
        return plates
```

### 2.3 BoxMOT Tracker — `services/ai_pipeline/tracker.py`

```python
# services/ai_pipeline/tracker.py
from boxmot import BotSort
from pathlib import Path
import numpy as np

class JSEPTracker:
    """
    PRD Section 6.4 — BoT-SORT with OSNet-x0.25 ReID.
    Maintains persistent Track IDs across minimum 2-second occlusion.
    """
    def __init__(self, reid_weights: str = "osnet_x0_25_msmt17.pt"):
        self.tracker = BotSort(
            reid_weights=Path(reid_weights),
            device="cuda:0" if self._has_gpu() else "cpu",
            half=False,
        )

    def update(self, detections: list[dict], frame: np.ndarray) -> list[dict]:
        """
        Input: raw detections from VehicleDetector
        Output: tracked detections with persistent track_id
        """
        if not detections:
            return []

        # BoxMOT expects: np.array([[x1, y1, x2, y2, conf, cls_id]])
        det_array = np.array([
            [*d["bbox"], d["confidence"], d["class_id"]]
            for d in detections
        ], dtype=np.float32)

        tracks = self.tracker.update(det_array, frame)
        # tracks output: [x1, y1, x2, y2, track_id, conf, cls_id, det_ind]
        results = []
        for t in tracks:
            results.append({
                "bbox": t[:4].tolist(),
                "track_id": int(t[4]),
                "confidence": float(t[5]),
                "class_id": int(t[6]),
                "class_name": ["car","motorcycle","truck","bus","angkot","bajaj","bicycle","pedestrian"][int(t[6])],
            })
        return results

    @staticmethod
    def _has_gpu() -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
```

### 2.4 ANPR Pipeline — `ml/anpr_pipeline.py`

Implement all **8 stages from PRD Section 6.2** in sequence:

```python
# ml/anpr_pipeline.py
import cv2
import re
import numpy as np
from paddleocr import PaddleOCR

# --- Stage 6: Indonesian Plate Regex (PRD Section 6.2, extended) ---
PLATE_STANDARD    = r'^[A-Z]{1,2}\s?\d{1,4}\s?[A-Z]{1,3}$'
PLATE_GOVERNMENT  = r'^(RI\s?\d+|[A-Z]{2}\s?\d{1,4}\s?[A-Z]{0,3})$'
PLATE_MILITARY    = r'^(TNI|POLRI|[A-Z])\s?\d{1,5}$'
PLATE_DIPLOMATIC  = r'^CD\s?\d{1,4}(\s?\d{1,4})?$'
PLATE_PATTERNS    = [PLATE_STANDARD, PLATE_GOVERNMENT, PLATE_MILITARY, PLATE_DIPLOMATIC]

def validate_plate(ocr_text: str) -> tuple[bool, str]:
    cleaned = ocr_text.upper().strip()
    for pattern in PLATE_PATTERNS:
        if re.match(pattern, cleaned):
            return True, cleaned
    return False, cleaned   # log REGEX_REJECTED with raw text

class ANPRPipeline:
    """
    8-stage ANPR pipeline (PRD Section 6.2).
    Stage 1: Plate detection (PlateDetector) — injected
    Stages 2-8: implemented here
    """

    def __init__(self):
        self.ocr = PaddleOCR(lang="en", use_gpu=False, show_log=False)
        self._init_super_resolution()

    def _init_super_resolution(self):
        """Stage 3: Real-ESRGAN (PRD FR-ANPR-02)."""
        try:
            from basicsr.archs.rrdbnet_arch import RRDBNet
            from realesrgan import RealESRGANer
            model = RRDBNet(num_in_ch=3, num_out_ch=3, scale=4, num_feat=64)
            self.upsampler = RealESRGANer(scale=4, model_path="weights/RealESRGAN_x4plus.pth",
                                          model=model, half=False)
            self.sr_available = True
        except Exception:
            self.sr_available = False  # graceful degradation

    def assess_quality(self, crop: np.ndarray) -> float:
        """Stage 2: Quality score 0–1 (resolution + blur + skew)."""
        h, w = crop.shape[:2]
        resolution_score = min(w / 120.0, 1.0) * min(h / 40.0, 1.0)
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        blur_score = min(cv2.Laplacian(gray, cv2.CV_64F).var() / 500.0, 1.0)
        return 0.5 * resolution_score + 0.5 * blur_score

    def super_resolve(self, crop: np.ndarray, quality_score: float) -> np.ndarray:
        """Stage 3: Apply Real-ESRGAN ×4 if quality < 0.6 (PRD Stage 3)."""
        if quality_score < 0.6 and self.sr_available:
            try:
                output, _ = self.upsampler.enhance(crop, outscale=4)
                return output
            except Exception:
                pass
        return crop

    def deskew(self, crop: np.ndarray) -> np.ndarray:
        """Stage 4: Perspective correction via contour detection."""
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return crop
        largest = max(contours, key=cv2.contourArea)
        rect = cv2.minAreaRect(largest)
        angle = rect[2]
        if abs(angle) > 30:
            return crop  # skip extreme angles
        M = cv2.getRotationMatrix2D(rect[0], angle, 1.0)
        return cv2.warpAffine(crop, M, (crop.shape[1], crop.shape[0]))

    def run_ocr(self, crop: np.ndarray) -> tuple[str, float]:
        """Stage 5: PaddleOCR 3.5+ / PP-OCRv5 — returns (text, confidence)."""
        result = self.ocr.ocr(crop, cls=True)
        if not result or not result[0]:
            return "", 0.0
        texts, confidences = [], []
        for line in result[0]:
            texts.append(line[1][0])
            confidences.append(line[1][1])
        return "".join(texts), float(np.mean(confidences)) if confidences else 0.0

    def compute_composite_confidence(self, ocr_conf: float, format_valid: bool,
                                     cross_frame_texts: list[str], ocr_text: str) -> float:
        """Stage 7: composite = 0.6*ocr_conf + 0.3*format_score + 0.1*cross_frame_consistency"""
        format_score = 1.0 if format_valid else 0.0
        if cross_frame_texts:
            consistency = sum(1 for t in cross_frame_texts if t == ocr_text) / len(cross_frame_texts)
        else:
            consistency = 0.5  # unknown
        return round(0.6 * ocr_conf + 0.3 * format_score + 0.1 * consistency, 3)

    def process(self, plate_crop: np.ndarray,
                cross_frame_crops: list[np.ndarray] | None = None) -> dict:
        """
        Full 8-stage pipeline. Returns ANPR result dict.
        Stage 8: composite < 0.75 → human review (RULE-04).
        """
        quality = self.assess_quality(plate_crop)            # Stage 2
        enhanced = self.super_resolve(plate_crop, quality)  # Stage 3
        deskewed = self.deskew(enhanced)                     # Stage 4
        raw_text, ocr_conf = self.run_ocr(deskewed)         # Stage 5
        is_valid, cleaned = validate_plate(raw_text)         # Stage 6

        # Future-only cross-camera consistency is intentionally omitted in v1.
        composite = self.compute_composite_confidence(ocr_conf, is_valid, [], cleaned)

        return {
            "plate_raw": raw_text,
            "plate_cleaned": cleaned,
            "is_valid_format": is_valid,
            "ocr_confidence": round(ocr_conf, 3),
            "quality_score": round(quality, 3),
            "composite_confidence": composite,
            "needs_human_review": composite < 0.75,   # Stage 8 — RULE-04
            "rejection_reason": None if is_valid else "REGEX_REJECTED",
        }
```

### 2.5 Violation Rule Engine — `services/ai_pipeline/violation_rules.py`

Copy **exact pseudocode from PRD Section 6.3** and fully implement:

```python
# services/ai_pipeline/violation_rules.py
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid

class ViolationType(str, Enum):
    ILLEGAL_PARKING        = "ILLEGAL_PARKING"
    BUSWAY_VIOLATION       = "BUSWAY_VIOLATION"
    BICYCLE_LANE_VIOLATION = "BICYCLE_LANE_VIOLATION"
    ILLEGAL_DROPOFF        = "ILLEGAL_DROPOFF"
    GANJIL_GENAP           = "GANJIL_GENAP"

class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"
    LOW      = "LOW"

@dataclass
class VehicleTrack:
    track_id: str
    vehicle_class: str
    bbox: list[float]
    centroid: tuple[float, float]
    is_stationary: bool = False
    stationary_duration_s: float = 0.0
    in_zone_duration_s: float = 0.0
    speed_kmh: float = 0.0
    plate_number: Optional[str] = None
    plate_confidence: float = 0.0

@dataclass
class Zone:
    id: str
    zone_type: str           # NO_PARKING | BUSWAY_LANE | BICYCLE_LANE | DESIGNATED_STOP
    threshold_s: int = 30    # configurable per zone (PRD Section 6.3)
    corridor: str = ""

    def contains(self, point: tuple[float, float]) -> bool:
        """Point-in-polygon using shapely (or pre-computed mask for performance)."""
        # Implementation: use shapely.geometry.Point + Polygon.contains()
        # Zone polygon loaded from zones table (PostGIS) at startup
        raise NotImplementedError

@dataclass
class ViolationEvent:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    violation_type: ViolationType = ViolationType.ILLEGAL_PARKING
    severity: Severity = Severity.HIGH
    track_id: str = ""
    camera_id: str = ""
    zone_id: str = ""
    plate_number: Optional[str] = None
    composite_confidence: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration_s: float = 0.0
    status: str = "DETECTED"

class ViolationRuleEngine:
    """
    Deterministic rule engine — NOT a neural classifier.
    Legally auditable and explainable (PRD Section 6.3).
    """

    def evaluate(self, track: VehicleTrack, zone: Zone) -> Optional[ViolationEvent]:
        """Returns ViolationEvent if rule fires, else None."""

        if zone.zone_type == "NO_PARKING":
            if track.is_stationary and track.stationary_duration_s >= zone.threshold_s:
                return ViolationEvent(
                    violation_type=ViolationType.ILLEGAL_PARKING,
                    severity=Severity.HIGH,
                    track_id=track.track_id,
                    duration_s=track.stationary_duration_s,
                )

        elif zone.zone_type == "BUSWAY_LANE":
            if track.vehicle_class not in ["transjakarta_bus"]:
                return ViolationEvent(
                    violation_type=ViolationType.BUSWAY_VIOLATION,
                    severity=Severity.CRITICAL,    # immediate, no duration threshold
                    track_id=track.track_id,
                    duration_s=0,
                )

        elif zone.zone_type == "BICYCLE_LANE":
            if track.vehicle_class in ["car", "motorcycle", "truck", "bus", "angkot"]:
                if track.in_zone_duration_s >= zone.threshold_s:  # default 10s
                    return ViolationEvent(
                        violation_type=ViolationType.BICYCLE_LANE_VIOLATION,
                        severity=Severity.HIGH,
                        track_id=track.track_id,
                        duration_s=track.in_zone_duration_s,
                    )

        elif zone.zone_type == "DESIGNATED_STOP":
            if track.vehicle_class in ["angkot", "bus"]:
                if track.is_stationary and not zone.contains(track.centroid):
                    if track.stationary_duration_s >= 15:
                        return ViolationEvent(
                            violation_type=ViolationType.ILLEGAL_DROPOFF,
                            severity=Severity.MEDIUM,
                            track_id=track.track_id,
                            duration_s=track.stationary_duration_s,
                        )

        return None

    def check_ganjil_genap(self, plate: str, corridor: str,
                            dt: datetime, holiday_dates: list[str]) -> Optional[ViolationEvent]:
        """
        Future-only extension. Do not wire into the v1 demo flow.
        ANPR confidence must be >= 0.92 before calling this (caller's responsibility).
        """
        import re
        RESTRICTED_CORRIDORS = [
            "SUDIRMAN", "THAMRIN", "GATOT_SUBROTO", "HR_RASUNA_SAID", "SIMATUPANG"
        ]
        RESTRICTED_HOURS = [(6, 10), (16, 21)]   # Pergub DKI 155/2018

        if corridor.upper() not in RESTRICTED_CORRIDORS:
            return None

        date_str = dt.strftime("%Y-%m-%d")
        if dt.weekday() >= 5 or date_str in holiday_dates:  # weekend or holiday
            return None

        hour = dt.hour
        in_window = any(start <= hour < end for start, end in RESTRICTED_HOURS)
        if not in_window:
            return None

        # Extract suffix digit from plate (e.g., "B 1234 XYZ" → last digit of number part)
        match = re.search(r'\d+', plate.replace(" ", ""))
        if not match:
            return None
        last_digit = int(match.group()[-1])

        # Odd day → odd plates allowed; Even day → even plates allowed
        is_even_plate = (last_digit % 2 == 0)
        is_even_day   = (dt.day % 2 == 0)

        if is_even_plate != is_even_day:  # parity conflict
            return ViolationEvent(
                violation_type=ViolationType.GANJIL_GENAP,
                severity=Severity.HIGH,
                plate_number=plate,
                duration_s=0,
            )
        return None
```

### 2.6 Training Data Download — Roboflow

**PRD Reference**: Section 11.1, 11.2

```python
# scripts/download_datasets.py
from roboflow import Roboflow
import os

rf = Roboflow(api_key=os.environ["ROBOFLOW_API_KEY"])

# Download in order: largest first (PRD Section 11.1)
datasets = [
    ("praproject",                  "indonesia-lpr",                   1),  # 5,582 images
    ("rendika-nurhartanto-s",       "indonesia-license-plate-detection", 1), # 2,819 images
    ("ksp-workspace",               "indonesia-license-plate-iqrtj",   1),  # 1,652 images
]

for workspace, project_name, version in datasets:
    proj = rf.workspace(workspace).project(project_name)
    proj.version(version).download("yolov8", location=f"datasets/{project_name}")
    print(f"Downloaded: {project_name}")

print("Now merge with: python scripts/merge_datasets.py")
```

### 2.7 Training — Execute

**PRD Reference**: Section 11.4 (copy exact train_jsep.py)

```bash
# After downloading and merging datasets:
python ml/train_jsep.py
# Trains both vehicle detector (~8-12h on RTX4090) and plate detector (~6-8h)
# Monitor: tensorboard --logdir runs/jsep

# Evaluate against KPIs (PRD Section 3.2):
yolo val model=runs/jsep/vehicle_detector_v1/weights/best.pt \
  data=datasets/merged/dataset.yaml
# Target: mAP50 > 0.90 (KPI-01)
```

---

## Phase 3 — Core Backend API

**PRD Reference**: Section 10 (full API spec)  
**Outcome**: FastAPI server running all endpoints from PRD Section 10.1–10.4.

### 3.1 FastAPI App Structure — `services/api/main.py`

```python
# services/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

from .routers import violations, analytics, etle, jaki, websocket
from .kafka_consumers import start_consumers
from .database import engine, Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: init DB connection pool, start Kafka consumers
    Base.metadata.create_all(bind=engine)
    asyncio.create_task(start_consumers())
    yield
    # Shutdown: cleanup

app = FastAPI(
    title="JSEP API",
    description="Jakarta Smart Enforcement Platform — DISHUB DKI Jakarta",
    version="5.1.2",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

app.include_router(violations.router,  prefix="/api/v1/violations",   tags=["violations"])
app.include_router(analytics.router,   prefix="/api/v1/analytics",    tags=["analytics"])
app.include_router(etle.router,        prefix="/api/v1/etle",         tags=["etle"])
app.include_router(jaki.router,        prefix="/api/v1/jaki",         tags=["jaki"])
app.include_router(websocket.router,   prefix="/ws",                  tags=["websocket"])
```

### 3.2 JAKI Ingest Endpoint — `services/api/routers/jaki.py`

Implements **PRD Section 10.4 webhook schema** and **FR-VIO-08 corroboration flow**:

```python
# services/api/routers/jaki.py
import hmac, hashlib, os
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime
from ..tasks import process_jaki_report   # Celery task

router = APIRouter()
JAKI_WEBHOOK_SECRET = os.environ.get("JAKI_WEBHOOK_SECRET", "")

class JAKIReport(BaseModel):
    jaki_report_id: str
    category: str           # PARKIR_LIAR | BUSWAY | SEPEDA | TURUN_NAIK_PENUMPANG | LAINNYA
    lat: float
    lng: float
    photo_url: str          # signed S3 URL
    description: str
    timestamp: datetime
    user_id_hashed: str     # SHA-256 — not reversible, no real PII

@router.post("/ingest")
async def ingest_jaki_report(
    request: Request,
    report: JAKIReport,
    background_tasks: BackgroundTasks,
):
    # Verify HMAC-SHA256 signature (PRD FR-VIO-08)
    sig_header = request.headers.get("X-JAKI-Signature", "")
    body = await request.body()
    expected = hmac.new(JAKI_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig_header, expected):
        raise HTTPException(status_code=401, detail="Invalid JAKI signature")

    # Queue async corroboration (non-blocking — PRD FR-VIO-08 step 1)
    background_tasks.add_task(process_jaki_report, report.model_dump())
    return {"status": "received", "jaki_report_id": report.jaki_report_id}
```

### 3.3 Kafka Consumers — `services/api/kafka_consumers.py`

```python
# services/api/kafka_consumers.py — bulkhead pattern (PRD Section 7.8)
import asyncio
from confluent_kafka import Consumer
import json
import os

BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

async def start_consumers():
    """Start all 4 alert consumers concurrently — bulkhead: each independent."""
    await asyncio.gather(
        fcm_consumer(),         # dispatch notifications
        websocket_consumer(),   # Dashboard real-time feed
        etle_draft_consumer(),  # E-TLE draft generation
        crm_outbound_consumer(),# CRM + JAKI callback
    )

async def fcm_consumer():
    consumer = Consumer({"bootstrap.servers": BOOTSTRAP, "group.id": "fcm-push-group"})
    consumer.subscribe(["alerts.verified"])
    while True:
        msg = consumer.poll(1.0)
        if msg and not msg.error():
            event = json.loads(msg.value())
            await send_fcm_push(event)       # implement FCM send
        await asyncio.sleep(0)

# Implement websocket_consumer, etle_draft_consumer, crm_outbound_consumer similarly
# Each must have its own consumer group ID and dead-letter-queue error handling
```

---

## Phase 4 — Analytics Engine

**PRD Reference**: Sections 6.5, 6.6, FR-ANA-01–07

### 4.1 H3 Hotspot Engine — `services/analytics/hotspot_engine.py`

Copy **exact algorithm from PRD Section 6.5**:

```python
# Use the exact compute_hotspots() function from PRD Section 6.5
# Key corrections from PRD Appendix 20.1:
#   Resolution 10 = operator default; Resolution 9 = executive rollup
#   KDE bandwidth calibrated in meters after projection, initial 300-600m
#   Refresh every 15 minutes (PRD FR-ANA-01)

# Schedule via APScheduler or Celery beat:
from apscheduler.schedulers.asyncio import AsyncIOScheduler
scheduler = AsyncIOScheduler()

@scheduler.scheduled_job("interval", minutes=15)
async def refresh_hotspots():
    violations = await db.fetch_recent_violations(hours=168)  # 7 days
    risk_scores = compute_hotspots(violations, resolution=10)
    await db.upsert_h3_hotspots(risk_scores)
```

### 4.2 MCLP Optimizer — `services/analytics/optimizer.py`

Copy **exact solve_mclp() function from PRD Section 6.6**.

Key validation:
```python
# After solve_mclp():
assert len(result) <= n_officers, "MCLP returned more positions than officers"
# Test with Jakarta pilot corridors (Sudirman, Thamrin, Gatot Subroto)
```

### 4.3 Legal & Sanction Reference — `services/legal_reference/`

**PRD Reference**: FR-LEGAL-01  
**Outcome**: Every E-TLE draft, CRM callback, dispatch recommendation, and executive summary can cite deterministic legal/sanction references without an LLM.

Create fixtures:

```yaml
# legal_reference/violation_legal_map.yaml
ILLEGAL_PARKING:
  legal_basis_code: "UU_LLAJ_22_2009_PASAL_287"
  sanction_code: "SANCTION_PARKING_DKI_DEFAULT"
  relevant_unit: "parking_enforcement"
  evidence_required:
    - plate_number
    - vehicle_class
    - no_parking_zone_id
    - duration_seconds
    - best_frame_url
    - video_clip_url
  static_report_fragment: "Kendaraan terdeteksi berhenti/parkir pada zona larangan selama {duration_seconds} detik."
```

Build:

```python
# services/legal_reference/reference_service.py
from dataclasses import dataclass
from pathlib import Path
import yaml

@dataclass(frozen=True)
class LegalReferenceBundle:
    violation_type: str
    legal_basis_code: str
    sanction_code: str
    relevant_unit: str
    evidence_required: list[str]
    static_report_fragment: str

class LegalReferenceService:
    def __init__(self, mapping_path: str = "legal_reference/violation_legal_map.yaml"):
        self.mapping = yaml.safe_load(Path(mapping_path).read_text(encoding="utf-8"))

    def get_bundle(self, violation_type: str) -> LegalReferenceBundle:
        data = self.mapping[violation_type]
        return LegalReferenceBundle(
            violation_type=violation_type,
            legal_basis_code=data["legal_basis_code"],
            sanction_code=data["sanction_code"],
            relevant_unit=data["relevant_unit"],
            evidence_required=data["evidence_required"],
            static_report_fragment=data["static_report_fragment"],
        )
```

Validation:

```bash
pytest tests/unit/test_legal_reference.py -v
# Expected: every v1 violation type has legal_basis_code, sanction_code,
# evidence_required, relevant_unit, and static_report_fragment.
```

### 4.4 Future Extension — Optional Narrative Drafting

Do **not** build this in the core v1 path.

If DISHUB explicitly requests legal-language drafting later, add a separate optional service for RAG-assisted berita acara generation. Keep it behind a feature flag, and keep the deterministic Jinja2/ReportLab template as the default path for competition day.

### 4.5 Optional AI Insight Agent — `services/insight_agent/`

**PRD Reference**: FR-INSIGHT-01  
**Outcome**: Executive dashboard can show one concise "AI Insight" per deterministic violation cluster. This is a demo enhancer, not an enforcement dependency.

Do not implement camera agents or a separate swarm framework. The existing Kafka services already provide autonomous processing. Build only a read-only summarizer over analytics output.

Input contract:

```json
{
  "cluster_id": "CLU-20260531-0007",
  "time_window": "2026-05-31T07:00:00+07:00/2026-05-31T07:20:00+07:00",
  "corridor": "Sudirman",
  "top_violation_types": ["ILLEGAL_PARKING", "BUSWAY_VIOLATION"],
  "violation_count": 9,
  "active_count": 6,
  "camera_readiness_mix": {"A": 2, "B": 1, "C": 0},
  "recommended_unit": "parking_enforcement",
  "recommended_action_deterministic": "Deploy 2 officers to H3 cells 8a2... and 8a3..."
}
```

Output contract:

```json
{
  "priority": "HIGH",
  "summary": "Pelanggaran parkir liar meningkat di koridor Sudirman dalam 20 menit terakhir.",
  "recommended_action": "Prioritaskan patroli parkir pada dua titik hotspot dengan kamera readiness A/B.",
  "reasoning": "Cluster berisi 9 pelanggaran, 6 masih aktif, dan terjadi pada jam puncak pagi.",
  "confidence_note": "Berdasarkan cluster CLU-20260531-0007 dan bukan keputusan penindakan otomatis.",
  "source_cluster_id": "CLU-20260531-0007"
}
```

Implementation rules:
- Use Gemini via `GEMINI_API_KEY` and configurable `GEMINI_MODEL`; do not use Anthropic/Claude unless explicitly requested later.
- Keep `ENABLE_AI_INSIGHTS=false` by default.
- Validate output against a JSON schema before showing it.
- If Gemini fails, hide the AI Insight panel or show deterministic template text.
- Never allow the insight agent to call E-TLE, update violation status, or dispatch officers.

---

## Phase 5 — Mock Government APIs

**PRD Reference**: Section 7.10 — CRITICAL: always mock in demo (RULE-02)

### 5.1 Mock Korlantas Client — `services/api/government_apis.py`

```python
# services/api/government_apis.py
import os, json, random
from pathlib import Path
from dataclasses import dataclass

USE_MOCK = os.getenv("USE_MOCK_APIS", "true").lower() == "true"

@dataclass
class VehicleOwner:
    owner_name: str
    nik_masked: str          # format: 3471****0001 — NEVER expose full NIK
    vehicle_brand: str
    vehicle_model: str
    vehicle_color: str
    year: int
    stnk_expiry: str
    pajak_status: str        # LUNAS | MENUNGGAK | BELUM_BAYAR

# Load fixture data (500+ synthetic plates)
_FIXTURE_PATH = Path("fixtures/vehicle_registry_mock.json")
_FIXTURE: dict = json.loads(_FIXTURE_PATH.read_text()) if _FIXTURE_PATH.exists() else {}

def get_vehicle_owner(plate: str) -> VehicleOwner:
    """
    PRD Section 7.10 — MOCK only for demo.
    Production: replace with KorlantasClient using mTLS cert.
    """
    if USE_MOCK:
        # Return fixture data or generate synthetic
        data = _FIXTURE.get(plate, {
            "owner_name": f"Pemilik Kendaraan {plate[-3:]}",
            "nik_masked": f"317{random.randint(1000,9999)}****{random.randint(1000,9999)}",
            "vehicle_brand": random.choice(["Toyota", "Honda", "Suzuki", "Daihatsu", "Mitsubishi"]),
            "vehicle_model": random.choice(["Avanza", "Jazz", "Ertiga", "Xenia", "Pajero"]),
            "vehicle_color": random.choice(["Putih", "Hitam", "Silver", "Merah", "Biru"]),
            "year": random.randint(2015, 2024),
            "stnk_expiry": "2027-12-31",
            "pajak_status": "LUNAS",
        })
        return VehicleOwner(**data)
    else:
        # Production: implement mTLS Korlantas API call here
        raise NotImplementedError("Production Korlantas API requires MoU + PKI cert")
```

### 5.2 Generate Mock Fixture

```bash
python scripts/generate_mock_vehicles.py
# Generates fixtures/vehicle_registry_mock.json with 500 synthetic Jakarta plates
# Use plate format: B XXXX ABC, D XXXX ABC, F XXXX ABC (Jakarta, Bandung, Bogor)
```

---

## Phase 6 — Frontend Dashboard

**PRD Reference**: Section 7.5 (FR-DASH-01–10), Section 9.3  
**⚠️ CONSULT DESIGN.md FOR EVERY COMPONENT** — colors, typography, spacing, component API.

### 6.1 Project Setup

```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install maplibre-gl@4 echarts react-echarts
npm install zustand
npm install @radix-ui/react-dialog @radix-ui/react-tabs   # shadcn/ui base
npm install tailwindcss postcss autoprefixer
npm install socket.io-client                               # WebSocket (PRD FR-DASH-02)
```

### 6.2 Dashboard Pages — Required Routes

| Route | Component | PRD FR |
|---|---|---|
| `/` | `DashboardPage` — live map + violation feed | FR-DASH-01/02/03 |
| `/map` | `ViolationMapPage` — MapLibre + H3 heatmap | FR-DASH-03/04 |
| `/analytics` | `AnalyticsPage` — corridor ranking, temporal | FR-ANA-01/02/03 |
| `/optimizer` | `OptimizerPage` — MCLP officer deployment | FR-ANA-06 |
| `/etle` | `ETLEPage` — bulk review + approval | FR-ETLE-02/05 |
| `/reports` | `ReportsPage` — executive summary PDF download | PRD Section 15.1 / executive summary output |
| `/settings` | `SettingsPage` — zone config, thresholds | Admin only |

### 6.3 H3 Heatmap — MapLibre GL

```typescript
// frontend/src/components/ViolationHeatmap.tsx
// H3 Resolution 10 for operator view; Resolution 9 for executive rollup (PRD Appendix 20.1)
// Consult DESIGN.md for: color scale (low-risk to high-risk), opacity values, legend style

import maplibregl from 'maplibre-gl';
import { cellsToFeatureCollection } from 'h3-js';  // npm install h3-js

export function addH3HeatmapLayer(map: maplibregl.Map, hotspots: Record<string, number>) {
  const features = Object.entries(hotspots).map(([h3Index, riskScore]) => ({
    type: 'Feature' as const,
    geometry: { type: 'Polygon', coordinates: [/* h3 boundary */] },
    properties: { h3Index, riskScore },
  }));

  map.addSource('h3-hotspots', { type: 'geojson', data: { type: 'FeatureCollection', features } });
  map.addLayer({
    id: 'h3-fill',
    type: 'fill',
    source: 'h3-hotspots',
    paint: {
      'fill-color': [
        'interpolate', ['linear'], ['get', 'riskScore'],
        0.0, /* DESIGN.md low-risk color  */  '#00ff88',
        0.5, /* DESIGN.md mid-risk color  */  '#ffaa00',
        1.0, /* DESIGN.md high-risk color */  '#ff2200',
      ],
      'fill-opacity': 0.6,
    },
  });
}
```

### 6.4 WebSocket Live Feed — `frontend/src/hooks/useViolationStream.ts`

```typescript
// Implements PRD FR-DASH-02 + Section 10.3 WebSocket Event Schema
import { useEffect, useRef, useState } from 'react';
import { io, Socket } from 'socket.io-client';

export interface ViolationEvent {
  event_type: string;
  violation_id: string;
  timestamp: string;
  camera_id: string;
  location: { lat: number; lng: number };
  violation_type: string;
  vehicle_class: string;
  plate_number: string;
  plate_confidence: number;
  duration_seconds: number;
  thumbnail_url: string;
  status: string;
  composite_confidence: number;
}

export function useViolationStream(jwt: string) {
  const [events, setEvents] = useState<ViolationEvent[]>([]);
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    const WS_URL = import.meta.env.VITE_WS_URL;
    const socket = io(WS_URL, { auth: { token: jwt }, transports: ['websocket'] });

    socket.on('VIOLATION_DETECTED', (event: ViolationEvent) => {
      setEvents(prev => [event, ...prev].slice(0, 100)); // keep last 100
    });

    socket.on('disconnect', () => {
      // Auto-reconnect handled by Socket.IO (PRD Section 7.8)
    });

    socketRef.current = socket;
    return () => { socket.disconnect(); };
  }, [jwt]);

  return events;
}
```

### 6.5 E-TLE Approval UI — `frontend/src/pages/ETLEPage.tsx`

Key implementation requirements from PRD:
- Show: violation photo, ANPR plate, confidence score, zone, duration, berita acara text
- Actions: `Approve` (1-click) → POST `/api/v1/violations/{id}/confirm`
- Actions: `Dismiss` → POST `/api/v1/violations/{id}/dismiss` + reason dropdown
- Bulk: approve up to 20 at once (FR-ETLE-05)
- **Never allow approval of composite_confidence < 0.75** (RULE-04)
- Show `is_mock: true` banner in demo mode (PRD Section 12.1 `etle_submissions.is_mock`)

---

## Phase 7 — Demo Preparation

**PRD Reference**: Section 15 (Demo Scope), Section 15.3 (5 Scenarios)

### 7.1 Seed Demo Data

```bash
# scripts/seed_demo_data.py
# Seed: 30 days of historical violations for Sudirman, Thamrin, Gatot Subroto
# Seed: 10 camera registrations (Balitower or simulated)
# Seed: 6 zone polygons (2 NO_PARKING, 2 BUSWAY_LANE, 1 BICYCLE_LANE, 1 DESIGNATED_STOP)
# Seed: citizen_points table (100 users with varying points)
python scripts/seed_demo_data.py
```

### 7.2 Demo Video Clips

```bash
# Place pre-recorded Jakarta CCTV clips in demo_clips/
# Minimum clips needed for 5 scenarios:
demo_clips/
├── scenario_a_illegal_parking_sudirman.mp4     # car stops >30s in no-parking zone
├── scenario_b_busway_violation.mp4             # motorcycle enters busway lane
├── scenario_c_illegal_dropoff.mp4             # angkot/bus stops outside designated stop
├── scenario_d_hotspot_overview.json            # pre-computed hotspot data for map demo
└── scenario_e_crm_report.jpg                  # sample citizen photo for CRM/JAKI flow
```

### 7.3 Demo Environment Check

```bash
# Run before every demo
make health                          # all services healthy
python scripts/demo_validation.py   # verify all 5 scenarios work end-to-end
# Expected output:
# ✓ Scenario A: Illegal parking detected in 2.8s
# ✓ Scenario B: Busway violation detected in 1.2s
# ✓ Scenario C: Illegal drop-off detected at designated stop breach
# ✓ Scenario D: H3 heatmap loaded, MCLP returned 5 positions
# ✓ Scenario E: CRM/JAKI report received, AI analysis complete, confidence=0.87
```

### 7.4 Demo Script Notes for Presenter

```markdown
## Scenario A — Illegal Parking (~3 min)
1. Open dashboard → Camera Grid tab
2. Play scenario_a clip on demo camera CAM-DEMO-SUDIRMAN-01
3. Show: 30-second timer counting up in violation feed
4. Alert appears: "ILLEGAL_PARKING | B 1234 XYZ | confidence 0.89"
5. Click alert → evidence panel opens with 10s clip + plate close-up
6. Click "Create E-TLE Draft" → navigate to E-TLE page
7. Show: berita acara generated by deterministic template
8. Click "Approve" → ticket ETL-20260526-JKP-ILP-000001-3 generated

## Scenario D — Analytics (~2 min)
1. Navigate to Analytics → H3 Heatmap
2. Toggle "Resolution 10" for operator view, then switch to "Resolution 9" for executive rollup
3. Show: Sudirman corridor is hottest (red cells)
4. Navigate to Optimizer → set n_officers=5, shift=morning
5. Show: 5 recommended positions as pins on map with coverage circles
6. Explain: MCLP guarantees optimal coverage given violation demand

## CRITICAL: Government API Note
- When demoing vehicle owner lookup → show "MOCK DATA" badge
- Explicitly say: "Production integration requires formal MoU with Korlantas"
- This shows professional awareness of regulatory requirements
```

---

## Phase 8 — Testing & KPI Validation

**PRD Reference**: Section 3.2 (KPI table)

### 8.1 KPI Validation Script

```bash
# tests/validate_kpis.py
# Run against held-out test set (20% of annotated data):

python tests/validate_kpis.py \
  --model runs/jsep/vehicle_detector_v1/weights/best.pt \
  --data datasets/merged_test/
# Expected output (PRD KPIs):
# KPI-01 Vehicle mAP50: 0.923 ✓ (target >0.90)
# KPI-02 ANPR daylight accuracy: 0.871 ✓ (target >0.85)
# KPI-03 ANPR night/rain accuracy: 0.703 ✓ (target >0.68)
# KPI-04 Violation precision: 0.887 ✓ (target >0.85)
# KPI-05 Violation recall: 0.812 ✓ (target >0.78)
# KPI-06 E2E latency (p95): 2.4s ✓ (target <3s)
# KPI-07 Inference FPS: 23 ✓ (target >20 FPS)
# KPI-11 False alarm rate: 6.2% ✓ (target <8%)
```

### 8.2 Integration Tests

```bash
# Run full stack integration tests:
pytest tests/integration/ -v --tb=short

# Key test cases:
# - test_violation_e2e: video clip → kafka → dashboard alert (<3s)
# - test_anpr_pipeline: plate crops → correct regex validation
# - test_illegal_dropoff: stop breach at designated stop → VIOLATION
# - test_jaki_flow: webhook → AI analysis → CCTV corroboration → citizen callback
# - test_etle_human_gate: auto-approve attempt blocked (RULE-03)
# - test_audit_log_immutable: DELETE/UPDATE attempts rejected
```

---

## Agent Decision Tree — Ambiguous Cases

When the PRD is ambiguous, resolve using these rules:

```
Q: YOLO26 not available / AGPL licensing blocked?
A: Use YOLOv11 (yolo11n.pt). Set DETECTION_MODEL=yolo11n.pt. Zero other changes.

Q: Gemini API unavailable or rate-limited?
A: Ignore it in the core build. Use the deterministic Jinja2/ReportLab template. Future narrative drafting stays behind a feature flag.

Q: Do we need legal references, fines/sanctions, and rule citations in v1?
A: YES. Build FR-LEGAL-01 as deterministic YAML/JSON + DB lookup. Do not use Gemini/LLM for authoritative rule or sanction decisions.

Q: Should we build Swarm AI Agents?
A: NO separate swarm framework in v1. Kafka consumers already behave like autonomous processing services. Optional: build FR-INSIGHT-01 as a read-only Gemini summarizer for executive dashboard clusters.

Q: Real Balitower HLS stream unavailable during demo?
A: Use pre-recorded demo_clips/ MP4 files. No apology needed — say "recorded Jakarta footage".

Q: ChromaDB index not built yet?
A: Ignore it for v1. ChromaDB is future-only optional narrative drafting, not the authoritative legal reference source.

Q: Confidence threshold for specific violation unclear?
A: Use PRD defaults (0.45 detection, 0.75 review gate). All thresholds configurable in .env or per-zone in zones table.

Q: DESIGN.md missing a component spec?
A: Use shadcn/ui defaults + Tailwind. Do not invent new design decisions. Flag to human.

Q: Government API returns error in demo?
A: USE_MOCK_APIS=true should prevent this. If reached, return fixture data + log warning.

Q: H3 resolution to use?
A: Use Resolution 10 for operator maps and Resolution 9 for executive rollups. Never use 174 m².

Q: Should blockchain/Polygon/Hyperledger Fabric be implemented?
A: NO. Removed from v1. Citizen points → citizen_points DB table only.
```

---

## Build Sequence Summary

```
Phase 0  →  choose runtime mode: local compose, remote VM, or managed cloud. Use Docker Build Cloud only for image builds.
Phase 1  →  Alembic migrations (all core tables from PRD Section 12.1)
Phase 2  →  YOLO26 setup → BoxMOT → ANPR pipeline → Violation rules → Training
Phase 3  →  FastAPI backend → all endpoints from PRD Section 10 → Kafka consumers
Phase 4  →  H3 hotspot → MCLP optimizer → legal/sanction lookup → unit routing → camera placement suggestions → optional AI Insight
Phase 5  →  Mock government APIs → fixture data → USE_MOCK_APIS=true everywhere
Phase 6  →  React dashboard → CONSULT DESIGN.md → MapLibre heatmap → WebSocket → E-TLE UI
Phase 7  →  Seed demo data → demo clips → 5 scenario validation
Phase 8  →  KPI validation → integration tests → demo environment check
```

---

## References

| Document | Purpose |
|---|---|
| `JSEP_PRD_v5_REVISED.md` | Authoritative specification — resolve all ambiguity here first |
| `DESIGN.md` | UI design system — consult before every React component |
| `fixtures/vehicle_registry_mock.json` | Synthetic vehicle data for demo |
| `legal_reference/` | Core deterministic legal/sanction reference fixtures |
| `services/insight_agent/` | Optional read-only Gemini AI Insight service |
| `rag_corpus/` | Future-only corpus for optional LLM narrative drafting |
| `demo_clips/` | Pre-recorded CCTV footage for 5 demo scenarios |
| `tests/demo_scenarios/` | Automated scenario validation scripts |

---

*JSEP Agent Build Guide — v5.1.3 — DISHUB DKI Jakarta — AI Open Innovation Challenge 2026*  
*AI agent: start at Phase 0 and complete phases in order. Do not skip phases.*

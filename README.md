# JSEP – Jakarta Smart Enforcement Platform

![DeepWiki Badge](https://deepwiki.com/badge-maker?url=https%3A%2F%2Fdeepwiki.com%2Fmuhammadghiffari%2Fjakarta-smart-enforcement-platform)

> End-to-end AI-powered traffic violation detection system using YOLO26, ANPR (PaddleOCR), FastAPI, WebSockets, TimescaleDB, and React.

---

## Project Structure

```
Jsep/
├── docs/                   # PRD, design guides
├── fixtures/               # Zone GeoJSON, mock data, holidays
├── frontend/               # React + Vite + Tailwind v3 UI
├── legal_reference/        # YAML legal basis & sanction maps
├── ml/                     # Training scripts & Kaggle notebooks
├── scripts/                # Utility & pipeline runner scripts
├── services/
│   ├── ai_pipeline/        # YOLO26 + BoT-SORT + ANPR + Rule Engine
│   ├── api/                # FastAPI backend (routers, models, DB)
│   └── narrative_agent/    # RAG agent for report generation
├── tests/                  # KPI validation tests
├── .env.example            # Copy to .env and fill in values
└── README.md
```

---

## Branch Strategy

| Branch | Purpose |
|--------|---------|
| `develop` | Active development – all feature branches merge here |
| `production` | Stable, tested releases only – merge from develop after review |

```
feature/my-feature  →  develop  →  production
```

---

## 🚀 Quick Start for Collaborators

### Prerequisites
- Ubuntu 22.04+ / WSL2
- Python 3.10+
- Node.js 18+
- PostgreSQL 14+ (or TimescaleDB)
- Git

### 1. Clone & branch
```bash
git clone <REPO_URL>
cd Jsep
git checkout develop
git checkout -b feature/your-feature-name
```

### 2. Setup environment
```bash
cp .env.example .env
# Edit .env and fill in DATABASE_URL and other values
```

### 3. Start the database
```bash
# Using Docker (easiest):
docker run -d \
  --name jsep-db \
  -e POSTGRES_USER=jsep_user \
  -e POSTGRES_PASSWORD=your_password \
  -e POSTGRES_DB=jsep_db \
  -p 5432:5432 \
  timescale/timescaledb:latest-pg14
```

### 4. Start the FastAPI backend
```bash
cd /path/to/Jsep
pip install -r services/api/requirements.txt

# Run migrations
cd services/api && alembic upgrade head && cd ../..

# Start the API server (auto-reloads on code changes)
bash scripts/start_api.sh
# → API live at http://localhost:8000
# → Docs at http://localhost:8000/docs
```

### 5. Start the React frontend
```bash
cd frontend
npm install
npm run dev
# → UI live at http://localhost:5173
```

### 6. Run the ML Pipeline (on GPU device)
```bash
# Point to the API server
export API_URL=http://<API_HOST>:8000

# Run on a video file (or RTSP stream)
python scripts/run_pipeline.py demo_clips/scenario_a.mp4

# Or with all options:
python scripts/run_pipeline.py \
  --source demo_clips/scenario_a.mp4 \
  --show \
  --no-anpr          # optional: skip ANPR for speed
```

Once running, violations will appear **live** in the Dashboard at `http://localhost:5173`.

---

## Key API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/v1/violations` | List violations (filter by `?status=DETECTED`) |
| `POST` | `/api/v1/violations/{id}/confirm` | Approve for E-TLE ticketing |
| `POST` | `/api/v1/violations/{id}/dismiss` | Dismiss with reason |
| `POST` | `/api/v1/violations/internal/event` | ML pipeline → save + broadcast |
| `WS` | `/ws/feed` | WebSocket live violation feed |
| `GET` | `/api/v1/analytics/summary` | Dashboard stats |

Interactive docs: `http://localhost:8000/docs`

---

## Business Rules (Critical – Do Not Change Without Review)
- **RULE-04:** Confidence < 0.75 → requires manual human review, auto-approve is BLOCKED.
- **Never auto-submit E-TLE** without officer confirmation.
- **Never call real government APIs** in demo mode (`USE_MOCK_APIS=true`).

---

## Training the ML Models (Kaggle)
See `ml/jsep_vehicle_detector_training.ipynb` for the full Kaggle notebook.  
Pre-trained weights go in `models/` (git-ignored due to size).

---

## Contributing
1. Create your feature branch from `develop`.
2. Open a Pull Request into `develop`.
3. After review & CI passes, it gets merged.
4. Releases to `production` are tagged (e.g. `v1.0.0`).

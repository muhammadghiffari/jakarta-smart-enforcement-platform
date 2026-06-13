#!/bin/bash
# Start JSEP FastAPI backend
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." >/dev/null 2>&1 && pwd)"
cd "$DIR"
source .venv/bin/activate

export DETECTION_MODEL=models/yolov8m.pt
export PLATE_MODEL=models/plate_detector_best.pt

echo "Starting JSEP API on http://localhost:8000 ..."
exec uvicorn services.api.app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level info

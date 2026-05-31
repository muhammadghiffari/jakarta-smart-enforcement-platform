#!/bin/bash
# Start JSEP FastAPI backend
cd /home/mghiffaa/Jsep
source .venv/bin/activate

echo "Starting JSEP API on http://localhost:8000 ..."
exec uvicorn services.api.app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level info

#!/bin/bash
cd /home/mghiffaa/Jsep
source .venv/bin/activate
python -c "from services.api.app.main import app; print('FastAPI app imports OK')"

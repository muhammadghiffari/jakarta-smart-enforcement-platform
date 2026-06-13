#!/usr/bin/env python3
"""Inspect YOLO model class names - run from repo root."""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

models_to_check = [
    "models/jsep_unified_v1.pt",
    "models/best.pt",
    "models/vehicle_detection_best.pt",
    "models/plate_detector_best.pt",
    "models/yolo26n.pt",
    "models/yolo26s.pt",
    "models/osnet_x0_25_msmt17.pt"
]

try:
    from ultralytics import YOLO
except ImportError:
    print("ERROR: ultralytics not installed. Run: pip install ultralytics")
    sys.exit(1)

for model_path in models_to_check:
    p = Path(model_path)
    if not p.exists():
        print(f"[SKIP] {model_path} — file not found")
        continue

    size_mb = p.stat().st_size / 1024 / 1024
    print(f"\n{'='*60}")
    print(f"Model : {model_path}  ({size_mb:.1f} MB)")
    try:
        m = YOLO(model_path)
        names = dict(m.names) if hasattr(m, "names") else {}
        print(f"Task  : {m.task}")
        print(f"Classes ({len(names)}):")
        for k, v in sorted(names.items()):
            print(f"  {k:3d} -> {v}")
    except Exception as e:
        print(f"ERROR loading: {e}")

print(f"\n{'='*60}")
print("Done.")

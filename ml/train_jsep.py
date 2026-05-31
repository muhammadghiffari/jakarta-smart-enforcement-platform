#!/usr/bin/env python3
"""
ml/train_jsep.py
YOLO26 fine-tuning for JSEP vehicle detector (PRD Section 11.4)
8 classes: car, motorcycle, truck, bus, angkot, bajaj, bicycle, pedestrian
"""
import os
import sys
import yaml
import shutil
from pathlib import Path
from ultralytics import YOLO

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------
BASE_DIR       = Path(__file__).resolve().parent.parent
DATASETS_DIR   = BASE_DIR / "datasets"
RUNS_DIR       = BASE_DIR / "runs" / "jsep"
MODEL_WEIGHTS  = os.getenv("DETECTION_MODEL", "yolo26n.pt")

VEHICLE_CLASSES = [
    "car", "motorcycle", "truck", "bus",
    "angkot", "bajaj", "bicycle", "pedestrian",
]

TRAIN_ARGS = dict(
    epochs       = int(os.getenv("TRAIN_EPOCHS", "100")),
    imgsz        = int(os.getenv("TRAIN_IMGSZ",  "640")),
    batch        = int(os.getenv("TRAIN_BATCH",  "16")),
    patience     = 25,
    device       = os.getenv("TRAIN_DEVICE", "0"),  # 0=first GPU, "cpu" fallback
    project      = str(RUNS_DIR),
    name         = "vehicle_detector_v1",
    exist_ok     = True,
    val          = True,
    # PRD Section 11.3 augmentation flags
    hsv_h        = 0.015,
    hsv_s        = 0.7,
    hsv_v        = 0.4,
    degrees      = 5.0,
    translate    = 0.1,
    scale        = 0.5,
    shear        = 0.0,
    perspective  = 0.0001,
    flipud       = 0.0,
    fliplr       = 0.5,
    mosaic       = 1.0,
    mixup        = 0.1,
    copy_paste   = 0.1,
    # Night / rain augmentation (PRD FR-DET-08)
    erasing      = 0.4,
)


def build_merged_dataset_yaml() -> Path:
    """
    Merge all downloaded Roboflow datasets into one dataset.yaml
    Expected structure after download_datasets.py:
      datasets/<project-name>/train/images/, datasets/<project-name>/val/images/
    """
    merged_yaml = DATASETS_DIR / "merged" / "dataset.yaml"
    merged_yaml.parent.mkdir(parents=True, exist_ok=True)

    train_paths, val_paths = [], []
    for d in DATASETS_DIR.iterdir():
        if not d.is_dir() or d.name == "merged":
            continue
        t = d / "train" / "images"
        v = d / "valid" / "images"
        if t.exists():
            train_paths.append(str(t))
        if v.exists():
            val_paths.append(str(v))

    if not train_paths:
        # No Roboflow data downloaded yet — fall back to a small open dataset
        print("WARNING: No Roboflow datasets found in datasets/. "
              "Falling back to COCO subset for smoke-test. "
              "Run scripts/download_datasets.py first for real training.")
        # For smoke-test: use COCO8 bundled with ultralytics
        data_yaml = {
            "path"  : str(DATASETS_DIR / "coco8"),
            "train" : "images/train",
            "val"   : "images/val",
            "nc"    : 8,
            "names" : VEHICLE_CLASSES,
        }
        from ultralytics.utils import downloads
        import subprocess
        subprocess.run(
            ["python", "-c",
             "from ultralytics.utils.downloads import download; "
             "download('https://ultralytics.com/assets/coco8.zip', dir='datasets')"],
            check=False
        )
    else:
        data_yaml = {
            "path"   : str(DATASETS_DIR / "merged"),
            "train"  : train_paths,
            "val"    : val_paths,
            "nc"     : len(VEHICLE_CLASSES),
            "names"  : VEHICLE_CLASSES,
        }

    with open(merged_yaml, "w") as f:
        yaml.dump(data_yaml, f, sort_keys=False)
    print(f"Dataset YAML written: {merged_yaml}")
    return merged_yaml


def train_vehicle_detector(data_yaml: Path):
    print(f"\n{'='*60}")
    print("JSEP Vehicle Detector Training (PRD Section 11.4)")
    print(f"  Model base : {MODEL_WEIGHTS}")
    print(f"  Classes    : {VEHICLE_CLASSES}")
    print(f"  Epochs     : {TRAIN_ARGS['epochs']}")
    print(f"  Device     : {TRAIN_ARGS['device']}")
    print(f"{'='*60}\n")

    model = YOLO(MODEL_WEIGHTS)
    results = model.train(data=str(data_yaml), **TRAIN_ARGS)
    best_pt = RUNS_DIR / "vehicle_detector_v1" / "weights" / "best.pt"
    if best_pt.exists():
        dst = BASE_DIR / "models" / "vehicle_detector_best.pt"
        shutil.copy2(best_pt, dst)
        print(f"\nBest weights saved → {dst}")
    return results


def validate_kpis(data_yaml: Path):
    """PRD Section 3.2 KPI validation after training."""
    best = RUNS_DIR / "vehicle_detector_v1" / "weights" / "best.pt"
    if not best.exists():
        print("No best.pt found — skipping KPI validation.")
        return
    print("\nRunning KPI validation (mAP50 target > 0.90)…")
    model = YOLO(str(best))
    metrics = model.val(data=str(data_yaml), device=TRAIN_ARGS["device"])
    map50 = metrics.box.map50
    print(f"  mAP50 = {map50:.4f}  {'✓ PASS' if map50 > 0.90 else '✗ FAIL (target >0.90)'}")
    return map50


if __name__ == "__main__":
    data_yaml = build_merged_dataset_yaml()
    train_vehicle_detector(data_yaml)
    validate_kpis(data_yaml)

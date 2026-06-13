"""
benchmark_models.py
Evaluasi semua model YOLO di folder models/ terhadap video Traffict_Padat.mp4.
Menghasilkan gambar perbandingan visual dan tabel statistik.
"""
import cv2
import numpy as np
from ultralytics import YOLO
from pathlib import Path

VIDEO   = "data/videos/Traffict_Padat.mp4"
OUT_DIR = Path("artifacts/benchmark")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Ambil 3 frame berbeda untuk evaluasi yang lebih representatif
FRAME_INDICES = [0, 50, 100]

VEHICLE_MODELS = [
    "vehicle_detection_best.pt",
    "best.pt",
    "yolov8m.pt",
    "jsep_unified_v1.pt",
    "yolo26s.pt",
    "yolo26n.pt",
]

PLATE_MODELS = [
    "plate_detector_best.pt",
    "jsep_unified_v1.pt",  # has 'plate' class
]

CONF = 0.15  # low conf to see max capability

# Kelas kendaraan yang valid
VEHICLE_KEYWORDS = {"car", "motorcycle", "truck", "bus", "mobil", "motor", 
                    "angkot", "bajaj", "bicycle", "van", "pickup", "minibus"}
PLATE_KEYWORDS   = {"plate", "license_plate", "numberplate"}

def is_vehicle(name):
    return any(kw in name.lower() for kw in VEHICLE_KEYWORDS)

def is_plate(name):
    return any(kw in name.lower() for kw in PLATE_KEYWORDS)

# Baca frames
cap = cv2.VideoCapture(VIDEO)
frames = {}
for idx in FRAME_INDICES:
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ret, frame = cap.read()
    if ret:
        frames[idx] = frame
cap.release()

print(f"Loaded {len(frames)} frames from {VIDEO}")
print("="*80)

# ─── Benchmark vehicle models ────────────────────────────────────────────────
print("\n📦 VEHICLE DETECTION MODEL BENCHMARK")
print("-"*80)
print(f"{'Model':<30} {'Classes':<40} {'Frame0':>7} {'Frame50':>7} {'Frame100':>7} {'Total':>7}")
print("-"*80)

vehicle_results = {}
for model_name in VEHICLE_MODELS:
    model_path = f"models/{model_name}"
    try:
        model = YOLO(model_path)
        class_names = list(model.names.values())
        vehicle_classes = [c for c in class_names if is_vehicle(c)]
        
        counts = {}
        annotated = {}
        for idx, frame in frames.items():
            results = model(frame, conf=CONF, verbose=False)
            det_count = 0
            out = frame.copy()
            for r in results:
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    name   = model.names[cls_id].lower()
                    conf   = float(box.conf[0])
                    if is_vehicle(name):
                        det_count += 1
                        x1,y1,x2,y2 = map(int, box.xyxy[0].tolist())
                        cv2.rectangle(out, (x1,y1),(x2,y2), (0,200,0), 2)
                        cv2.putText(out, f"{name} {conf:.2f}", (x1, y1-5),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0,255,0), 1)
            counts[idx] = det_count
            annotated[idx] = out
        
        total = sum(counts.values())
        vehicle_results[model_name] = {
            "counts": counts, "classes": vehicle_classes, "annotated": annotated, "total": total
        }
        
        cls_str = ", ".join(vehicle_classes[:5])
        if len(vehicle_classes) > 5: cls_str += f"... (+{len(vehicle_classes)-5})"
        print(f"{model_name:<30} {cls_str:<40} {counts.get(0,0):>7} {counts.get(50,0):>7} {counts.get(100,0):>7} {total:>7}")
        
        # Save annotated frame for best frame (frame 0)
        cv2.imwrite(str(OUT_DIR / f"vehicle_{model_name.replace('.pt','')}_frame0.jpg"), annotated[0])
        
    except Exception as e:
        print(f"{model_name:<30} ERROR: {e}")

# ─── Benchmark plate models ──────────────────────────────────────────────────
print("\n\n🪪  PLATE DETECTION MODEL BENCHMARK")
print("-"*80)
print(f"{'Model':<30} {'Classes':<40} {'Frame0':>7} {'Frame50':>7} {'Frame100':>7} {'Total':>7}")
print("-"*80)

plate_results = {}
for model_name in PLATE_MODELS:
    model_path = f"models/{model_name}"
    try:
        model = YOLO(model_path)
        counts = {}
        annotated = {}
        for idx, frame in frames.items():
            results = model(frame, conf=0.05, verbose=False)  # very low conf for plates
            det_count = 0
            out = frame.copy()
            for r in results:
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    name   = model.names[cls_id].lower()
                    conf_v = float(box.conf[0])
                    if is_plate(name):
                        det_count += 1
                        x1,y1,x2,y2 = map(int, box.xyxy[0].tolist())
                        cv2.rectangle(out, (x1,y1),(x2,y2), (0,0,255), 2)
                        cv2.putText(out, f"{name} {conf_v:.2f}", (x1, y2+12),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0,0,255), 1)
            counts[idx] = det_count
            annotated[idx] = out
        
        total = sum(counts.values())
        plate_results[model_name] = {"counts": counts, "annotated": annotated, "total": total}
        
        print(f"{model_name:<30} {list(model.names.values())!s:<40} {counts.get(0,0):>7} {counts.get(50,0):>7} {counts.get(100,0):>7} {total:>7}")
        cv2.imwrite(str(OUT_DIR / f"plate_{model_name.replace('.pt','')}_frame0.jpg"), annotated[0])
        
    except Exception as e:
        print(f"{model_name:<30} ERROR: {e}")

# ─── Print recommendation ────────────────────────────────────────────────────
print("\n\n🏆 REKOMENDASI")
print("-"*80)
best_vehicle = max(vehicle_results, key=lambda k: vehicle_results[k]["total"])
best_plate   = max(plate_results,   key=lambda k: plate_results[k]["total"])
print(f"✅ Best Vehicle Model : {best_vehicle} ({vehicle_results[best_vehicle]['total']} deteksi total)")
print(f"✅ Best Plate Model   : {best_plate} ({plate_results[best_plate]['total']} deteksi total)")
print(f"\nAnnotated images saved to: {OUT_DIR.resolve()}")

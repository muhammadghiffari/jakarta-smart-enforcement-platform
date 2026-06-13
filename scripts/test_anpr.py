import cv2
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.ai_pipeline.detector import PlateDetector, VehicleDetector
from ml.anpr_pipeline import ANPRPipeline

print("Loading models...")
vd = VehicleDetector("models/yolov8m.pt")
pd = PlateDetector("models/plate_detector_best.pt")
anpr = ANPRPipeline()

print("Extracting frame...")
cap = cv2.VideoCapture("data/videos/Traffict_Padat.mp4")
ret, frame = cap.read()
if not ret:
    print("Failed to read video")
    sys.exit(1)

print("Detecting vehicles...")
vehicles = vd.detect(frame)
print(f"Found {len(vehicles)} vehicles.")

for i, v in enumerate(vehicles[:5]): # Check first 5
    bbox = v["bbox"]
    cls_name = v["class_name"]
    print(f"Vehicle {i}: {cls_name} conf={v['confidence']:.2f}")
    
    plates = pd.detect_in_vehicle_crop(bbox, frame)
    if not plates:
        print("  -> No plates found.")
        continue
    
    for j, p in enumerate(plates):
        print(f"  -> Plate {j}: conf={p['confidence']:.2f}")
        if "crop" in p and p["crop"] is not None:
            crop_path = f"artifacts/plate_crop_{i}_{j}.jpg"
            cv2.imwrite(crop_path, p["crop"])
            print(f"     Saved crop to {crop_path}")
            
            # EasyOCR direct test
            import easyocr
            reader = easyocr.Reader(['en'], gpu=False, verbose=False)
            res_easy = reader.readtext(p["crop"])
            print(f"     EasyOCR direct result: {res_easy}")
            
            # Paddle direct test
            from paddleocr import PaddleOCR
            p_ocr = PaddleOCR(lang="en")
            res_paddle = p_ocr.ocr(p["crop"])
            print(f"     PaddleOCR direct result: {res_paddle}")
            
            res = anpr.process(p["crop"])
            print(f"     ANPR Pipeline Result: {res}")
        else:
            print("     No crop available for ANPR")

print("Done.")

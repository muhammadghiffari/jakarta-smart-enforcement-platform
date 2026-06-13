import cv2
from ultralytics import YOLO
import sys

frame = cv2.imread("temp_frame.jpg")
if frame is None:
    # Extract first frame from video
    cap = cv2.VideoCapture("data/videos/Traffict_Padat.mp4")
    ret, frame = cap.read()
    cv2.imwrite("temp_frame.jpg", frame)

print("--- Testing best.pt ---")
model_best = YOLO("models/best.pt")
res1 = model_best(frame, conf=0.25, verbose=False)[0]
print(f"best.pt found {len(res1.boxes)} objects.")

print("--- Testing yolov8m.pt ---")
model_yolo = YOLO("models/yolov8m.pt")
res2 = model_yolo(frame, conf=0.25, verbose=False)[0]
print(f"yolov8m.pt found {len(res2.boxes)} objects.")

import numpy as np
from boxmot.trackers import BotSort
import sys
from pathlib import Path

# Fix relative path for weights
weights = str(Path(__file__).resolve().parent.parent / "models" / "osnet_x0_25_msmt17.pt")
print(f"Loading weights from {weights}")

tracker = BotSort(reid_model=weights)
dets = np.array([[0,0,10,10,0.9,0], [20,20,30,30,0.9,1]], dtype=np.float32)
img = np.zeros((100,100,3), dtype=np.uint8)

print("Updating tracker...")
tracks = tracker.update(dets, img)

print(f"Tracks type: {type(tracks)}")
print(f"Tracks shape: {tracks.shape}")
print(f"Tracks data:\n{tracks}")

if len(tracks) > 0:
    t = tracks[0]
    print(f"First track len: {len(t)}")
    print(f"First track items: {t}")
    print(f"t[4] (expected track_id): {t[4]}")

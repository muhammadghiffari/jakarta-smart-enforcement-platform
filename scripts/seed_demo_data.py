#!/usr/bin/env python3
"""
scripts/seed_demo_data.py
Seeds 30 days of historical violations, camera registrations, 
zone polygons, and citizen points for the Phase 7 Demo Scenarios.
"""

import sys
import uuid
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.api.app.database import SessionLocal, check_connection
from services.api.app import models

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def seed_cameras(db):
    print("Seeding cameras...")
    corridors = ["Sudirman", "Thamrin", "Gatot_Subroto"]
    for i in range(10):
        cam = models.Camera(
            id=f"CAM-DEMO-{random.choice(corridors).upper()}-{i+1:02d}",
            name=f"Camera Demo {i+1}",
            location_lat=-6.200000 + random.uniform(-0.02, 0.02),
            location_lng=106.816666 + random.uniform(-0.02, 0.02),
            corridor=random.choice(corridors),
            rtsp_url="rtsp://demo-stream.local/live",
            readiness_grade=random.choice(["A", "A", "B", "C"])
        )
        db.merge(cam)
    db.commit()

def seed_zones(db):
    print("Seeding zones...")
    zones_data = [
        ("ZONE-01", "NO_PARKING", "Sudirman", 30),
        ("ZONE-02", "NO_PARKING", "Thamrin", 30),
        ("ZONE-03", "BUSWAY_LANE", "Sudirman", 0),
        ("ZONE-04", "BUSWAY_LANE", "Gatot_Subroto", 0),
        ("ZONE-05", "BICYCLE_LANE", "Thamrin", 0),
        ("ZONE-06", "DESIGNATED_STOP", "Gatot_Subroto", 15)
    ]
    for name, ztype, corridor, thresh in zones_data:
        zone = models.Zone(
            name=name,
            zone_type=ztype,
            corridor=corridor,
            threshold_s=thresh,
            geojson='{"type":"Polygon","coordinates":[[[106.8,-6.2],[106.81,-6.2],[106.81,-6.21],[106.8,-6.21],[106.8,-6.2]]]}'
        )
        db.add(zone)
    db.commit()

def seed_citizen_points(db):
    print("Seeding citizen points...")
    for _ in range(100):
        c = models.CitizenPoints(
            user_id_hashed=uuid.uuid4().hex,
            points_total=random.randint(10, 500),
            reports_count=random.randint(1, 20),
            corroborated=random.randint(0, 15)
        )
        db.add(c)
    db.commit()

def main():
    if not check_connection():
        print("WARNING: PostgreSQL connection failed. Make sure DB is running.")
        print("Skipping database seeding. Please run `docker compose up -d db` and try again.")
        return

    db = next(get_db())
    try:
        seed_cameras(db)
        seed_zones(db)
        seed_citizen_points(db)
        print("Done seeding demo data.")
    except Exception as e:
        print(f"Error seeding data: {e}")
        db.rollback()

if __name__ == "__main__":
    main()

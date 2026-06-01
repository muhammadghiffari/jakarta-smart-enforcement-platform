import sys
import os

# Set pythonpath to include both services/api and the project root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(project_root, 'services/api'))
sys.path.insert(0, project_root)

print("Testing API imports...")
try:
    from app.main import app
    print("✓ App imported successfully!")
except Exception as e:
    print("✗ App import failed:")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("Testing database and models imports...")
try:
    from app import models
    from app.database import SessionLocal
    db = SessionLocal()
    # Query a legal reference or something simple
    ref_count = db.query(models.LegalReference).count()
    print(f"✓ DB connection OK! Found {ref_count} legal references.")
    db.close()
except Exception as e:
    print("✗ DB check failed:")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("All API & DB checks passed successfully!")

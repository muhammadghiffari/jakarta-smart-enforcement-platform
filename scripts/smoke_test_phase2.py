import sys
sys.path.insert(0, '.')

print("Testing detector...")
from services.ai_pipeline.detector import VehicleDetector, PlateDetector, detect_vehicles_and_plates
print("  detector OK")

print("Testing tracker...")
from services.ai_pipeline.tracker import JSEPTracker
print("  tracker OK")

print("Testing violation_rules...")
from services.ai_pipeline.violation_rules import VehicleTrack, Zone, ViolationRuleEngine, LegalReferenceService
print("  violation_rules OK")

print("Testing anpr_pipeline...")
from ml.anpr_pipeline import ANPRPipeline, validate_plate
ok, cleaned = validate_plate("B 1234 XYZ")
print("  anpr_pipeline OK -- validate_plate: valid={}, cleaned={}".format(ok, cleaned))

print("Testing pipeline...")
from services.ai_pipeline.pipeline import JSEPPipeline, ZoneManager
zm = ZoneManager()
print("  pipeline OK -- zones loaded: {}".format(len(zm.zones)))

print("")
print("All Phase 2 imports OK.")

import os
import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'services', 'api')))
from app.models import LegalReference, SanctionReference, ViolationLegalMap, Base

db_user = os.getenv("POSTGRES_USER", "jsep_user")
db_pass = os.getenv("POSTGRES_PASSWORD", "jsep_local_dev")
db_host = os.getenv("POSTGRES_HOST", "localhost")
db_port = os.getenv("POSTGRES_PORT", "5432")
db_name = os.getenv("POSTGRES_DB", "jsep")

DATABASE_URL = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Make sure tables exist
Base.metadata.create_all(bind=engine)

def seed_legal_data():
    db = SessionLocal()
    
    legal_ref_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'legal_reference'))
    
    # 1. Seed Legal References
    try:
        with open(os.path.join(legal_ref_dir, 'legal_references.yaml'), 'r') as f:
            legal_refs = yaml.safe_load(f)
            for code, data in legal_refs.items():
                existing = db.query(LegalReference).filter_by(code=code).first()
                if not existing:
                    lr = LegalReference(
                        code=code,
                        title=data.get('title'),
                        citation_text=data.get('citation_text'),
                        source_doc=data.get('source_doc'),
                        source_article=data.get('source_article')
                    )
                    db.add(lr)
    except FileNotFoundError:
        print("legal_references.yaml not found. Skipping.")

    # 2. Seed Sanction References
    try:
        with open(os.path.join(legal_ref_dir, 'sanction_references.yaml'), 'r') as f:
            sanctions = yaml.safe_load(f)
            for code, data in sanctions.items():
                existing = db.query(SanctionReference).filter_by(code=code).first()
                if not existing:
                    sr = SanctionReference(
                        code=code,
                        title=data.get('title'),
                        fine_min_idr=data.get('fine_min_idr'),
                        fine_max_idr=data.get('fine_max_idr'),
                        action_type=data.get('action_type'),
                        notes=data.get('notes')
                    )
                    db.add(sr)
    except FileNotFoundError:
        print("sanction_references.yaml not found. Skipping.")
        
    db.commit()

    # 3. Seed Violation Legal Map
    try:
        with open(os.path.join(legal_ref_dir, 'violation_legal_map.yaml'), 'r') as f:
            vmap = yaml.safe_load(f)
            for v_type, data in vmap.items():
                existing = db.query(ViolationLegalMap).filter_by(violation_type=v_type).first()
                if not existing:
                    vm = ViolationLegalMap(
                        violation_type=v_type,
                        legal_code=data.get('legal_basis_code'),
                        sanction_code=data.get('sanction_code'),
                        relevant_unit=data.get('relevant_unit'),
                        evidence_required=data.get('evidence_required', []),
                        static_report_fragment=data.get('static_report_fragment')
                    )
                    db.add(vm)
    except FileNotFoundError:
        print("violation_legal_map.yaml not found. Skipping.")

    db.commit()
    db.close()
    print("Seeding completed successfully.")

if __name__ == "__main__":
    seed_legal_data()

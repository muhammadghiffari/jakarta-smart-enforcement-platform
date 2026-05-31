# services/api/government_apis.py
import os
import json
import random
from pathlib import Path
from dataclasses import dataclass

USE_MOCK = os.getenv("USE_MOCK_APIS", "true").lower() == "true"

@dataclass
class VehicleOwner:
    owner_name: str
    nik_masked: str          # format: 3471****0001
    vehicle_brand: str
    vehicle_model: str
    vehicle_color: str
    year: int
    stnk_expiry: str
    pajak_status: str        # LUNAS | MENUNGGAK | BELUM_BAYAR


_FIXTURE_PATH = Path("fixtures/vehicle_registry_mock.json")
_FIXTURE = {}
if _FIXTURE_PATH.exists():
    try:
        _FIXTURE = json.loads(_FIXTURE_PATH.read_text())
    except Exception:
        pass


def get_vehicle_owner(plate: str) -> VehicleOwner:
    """
    PRD Section 7.10 — MOCK only for demo.
    Production: replace with KorlantasClient using mTLS cert.
    """
    if USE_MOCK:
        data = _FIXTURE.get(plate)
        if not data:
            data = {
                "owner_name": f"Pemilik Kendaraan {plate[-3:] if len(plate) > 3 else 'XXX'}",
                "nik_masked": f"317{random.randint(1000,9999)}****{random.randint(1000,9999)}",
                "vehicle_brand": random.choice(["Toyota", "Honda", "Suzuki", "Daihatsu", "Mitsubishi"]),
                "vehicle_model": random.choice(["Avanza", "Jazz", "Ertiga", "Xenia", "Pajero"]),
                "vehicle_color": random.choice(["Putih", "Hitam", "Silver", "Merah", "Biru"]),
                "year": random.randint(2015, 2024),
                "stnk_expiry": "2027-12-31",
                "pajak_status": "LUNAS",
            }
        return VehicleOwner(**data)
    else:
        raise NotImplementedError("Production Korlantas API requires MoU + PKI cert")

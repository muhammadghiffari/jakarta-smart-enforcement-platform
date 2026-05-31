import json
import random
from pathlib import Path

def generate():
    plates = []
    
    # Generate 500 Jakarta (B), Bandung (D), Bogor (F) plates
    for i in range(500):
        prefix = random.choice(["B", "D", "F"])
        num = random.randint(1000, 9999)
        chars = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=random.randint(1, 3)))
        plate = f"{prefix} {num} {chars}"
        
        plates.append(plate)

    data = {}
    for plate in plates:
        data[plate] = {
            "owner_name": f"Pemilik Kendaraan {plate[-3:]}",
            "nik_masked": f"317{random.randint(1000,9999)}****{random.randint(1000,9999)}",
            "vehicle_brand": random.choice(["Toyota", "Honda", "Suzuki", "Daihatsu", "Mitsubishi", "Wuling"]),
            "vehicle_model": random.choice(["Avanza", "Jazz", "Ertiga", "Xenia", "Pajero", "Almaz"]),
            "vehicle_color": random.choice(["Putih", "Hitam", "Silver", "Merah", "Biru"]),
            "year": random.randint(2015, 2024),
            "stnk_expiry": f"{random.randint(2024, 2028)}-12-31",
            "pajak_status": random.choices(["LUNAS", "MENUNGGAK", "BELUM_BAYAR"], weights=[80, 15, 5])[0]
        }
        
    out_dir = Path("fixtures")
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "vehicle_registry_mock.json"
    
    out_file.write_text(json.dumps(data, indent=2))
    print(f"Generated {len(data)} mock vehicles at {out_file}")

if __name__ == "__main__":
    generate()

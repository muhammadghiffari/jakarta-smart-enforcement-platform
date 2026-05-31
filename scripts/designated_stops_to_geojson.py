#!/usr/bin/env python3
"""
Convert the designated stop CSV into a GeoJSON FeatureCollection.

Input:
  fixtures/designated_stops.csv

Output:
  fixtures/designated_stops.geojson
"""

import argparse
import csv
import json
from pathlib import Path


def safe_float(value: str | None):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def row_to_feature(row: dict) -> dict | None:
    lat = safe_float(row.get("lintang"))
    lng = safe_float(row.get("bujur"))
    if lat is None or lng is None:
        return None

    props = {k: v.strip() if isinstance(v, str) else v for k, v in row.items()}
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [lng, lat],
        },
        "properties": props,
    }


def main():
    parser = argparse.ArgumentParser(description="Convert designated stops CSV to GeoJSON")
    parser.add_argument("--input", default="fixtures/designated_stops.csv")
    parser.add_argument("--output", default="fixtures/designated_stops.geojson")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    features = []
    with input_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            feature = row_to_feature(row)
            if feature:
                features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "name": "designated_stops",
        "features": features,
    }
    output_path.write_text(json.dumps(geojson, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output_path} with {len(features)} features")


if __name__ == "__main__":
    main()

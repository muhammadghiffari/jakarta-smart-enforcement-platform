#!/usr/bin/env python3
"""
Load designated stop fixtures for JSEP.

Best-practice layout:
  - fixtures/designated_stops.csv      raw source
  - fixtures/designated_stops.geojson   runtime fixture

This module keeps parsing logic in one place so future backend code can import
the same loader rather than re-implementing file handling.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DesignatedStop:
    no_registrasi: str
    jenis_halte: str
    lokasi_alamat: str
    lintang: float
    bujur: float
    wilayah: str | None = None
    periode_data: str | None = None
    kode_barang: str | None = None
    raw_properties: dict[str, Any] | None = None


def load_designated_stops_geojson(path: str | Path = "fixtures/designated_stops.geojson") -> list[DesignatedStop]:
    geojson_path = Path(path)
    data = json.loads(geojson_path.read_text(encoding="utf-8"))

    stops: list[DesignatedStop] = []
    for feature in data.get("features", []):
        geometry = feature.get("geometry") or {}
        properties = feature.get("properties") or {}
        coords = geometry.get("coordinates") or []

        if geometry.get("type") != "Point" or len(coords) < 2:
            continue

        lng, lat = coords[0], coords[1]
        stop = DesignatedStop(
            no_registrasi=str(properties.get("no_registrasi", "")),
            jenis_halte=str(properties.get("jenis_halte", "")),
            lokasi_alamat=str(properties.get("lokasi_alamat", "")),
            lintang=float(properties.get("lintang", lat)),
            bujur=float(properties.get("bujur", lng)),
            wilayah=properties.get("wilayah"),
            periode_data=properties.get("periode_data"),
            kode_barang=properties.get("kode_barang"),
            raw_properties=properties,
        )
        stops.append(stop)

    return stops


def find_stop_by_registration(
    no_registrasi: str,
    path: str | Path = "fixtures/designated_stops.geojson",
) -> DesignatedStop | None:
    for stop in load_designated_stops_geojson(path):
        if stop.no_registrasi == no_registrasi:
            return stop
    return None


if __name__ == "__main__":
    stops = load_designated_stops_geojson()
    print(f"Loaded {len(stops)} designated stops")
    if stops:
        first = stops[0]
        print(first)

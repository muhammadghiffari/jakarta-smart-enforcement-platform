#!/usr/bin/env python3
"""
scripts/parse_camera_json.py
Convert any Indonesian CCTV JSON (with x,y or lat,lng coordinates)
into JSEP cameras table format and probe which streams are active.

Usage:
  python scripts/parse_camera_json.py --input cameras.json --output fixtures/cameras_jsep.json
  python scripts/parse_camera_json.py --input cameras.json --probe   # also test HLS streams

Handles coordinate formats:
  - WGS84 decimal degrees:  x=106.827, y=-6.208  (lng, lat)
  - Web Mercator EPSG:3857: x=11900000, y=-700000 (will auto-convert)
  - DMS strings:            x="106°49'37\"E", y="6°12'28\"S"
"""

import json
import argparse
import asyncio
import aiohttp
import math
import re
from pathlib import Path


# ─── Coordinate conversion ────────────────────────────────────────────────────

def detect_and_convert(x: float, y: float) -> tuple[float, float]:
    """
    Detect coordinate system and return (lat, lng) in WGS84.
    
    Heuristic:
    - If |x| < 180 and |y| < 90 → already WGS84 (x=lng, y=lat)
    - If |x| > 1_000_000 → Web Mercator EPSG:3857 (x=easting, y=northing)
    - Jakarta range: lng 106.6–107.0, lat -6.4 to -6.0
    """
    if abs(x) > 1_000_000 or abs(y) > 1_000_000:
        # Web Mercator → WGS84
        lng = math.degrees(x / 6_378_137)
        lat = math.degrees(2 * math.atan(math.exp(y / 6_378_137)) - math.pi / 2)
        return round(lat, 6), round(lng, 6)
    elif abs(x) < 180 and abs(y) < 90:
        # Assume x=longitude, y=latitude
        return round(y, 6), round(x, 6)
    else:
        # Unknown — return as-is, flag for review
        return y, x


def parse_dms(dms_str: str) -> float:
    """Parse DMS string like '106°49'37"E' to decimal degrees."""
    pattern = r'(\d+)[°](\d+)[\'"](\d+(?:\.\d+)?)[\"\']\s*([NSEW])'
    m = re.search(pattern, str(dms_str))
    if not m:
        return float(dms_str)  # try direct conversion
    deg, mins, sec, direction = m.groups()
    decimal = float(deg) + float(mins)/60 + float(sec)/3600
    if direction in ('S', 'W'):
        decimal *= -1
    return round(decimal, 6)


# ─── Stream URL builders per known sources ────────────────────────────────────

def build_stream_url(camera: dict, source_hint: str = "auto") -> dict[str, str]:
    """
    Build stream URLs from camera metadata.
    Returns dict of {format: url}.
    """
    urls = {}
    
    # Balitower pattern
    site_name = camera.get("site_name") or camera.get("siteName") or camera.get("name", "")
    if site_name and ("balitower" in str(camera.get("source", "")).lower() or 
                      source_hint == "balitower"):
        site = site_name.replace(" ", "-")
        urls["hls"]   = f"http://cctv.balitower.co.id/{site}/index.m3u8"
        urls["embed"] = f"http://cctv.balitower.co.id/{site}/embed.html?proto=hls"
        urls["rtmp"]  = f"rtmp://cctv.balitower.co.id:1935/static/{site}"

    # LewatMana pattern — inspect network on lewatmana.com/cam/ for actual URL
    cam_id = camera.get("id") or camera.get("camera_id") or camera.get("camId", "")
    if cam_id and ("lewatmana" in str(camera.get("source", "")).lower() or
                   source_hint == "lewatmana"):
        urls["embed"] = f"https://lewatmana.com/cam/{cam_id}"

    # ATCS Jakarta Smart City — URLs vary per location
    atcs_id = camera.get("atcs_id") or camera.get("atcsId", "")
    if atcs_id:
        urls["embed"] = f"http://www.atcsdjka.dishub.dki.jakarta.go.id/camview/{atcs_id}"

    # YouTube live stream (if provided)
    yt = camera.get("youtube_url") or camera.get("youtubeUrl", "")
    if yt:
        urls["youtube"] = yt

    # Direct RTSP/HLS if already in source data
    for key in ["rtsp_url", "hls_url", "stream_url", "url", "rtspUrl", "hlsUrl"]:
        if camera.get(key):
            ext = "hls" if ".m3u8" in str(camera[key]) else "rtsp"
            urls[ext] = camera[key]

    return urls


# ─── Main parser ──────────────────────────────────────────────────────────────

def parse_camera_json(input_data: list | dict) -> list[dict]:
    """
    Parse various Indonesian CCTV JSON formats into standardized JSEP camera records.
    """
    # Normalize to list
    if isinstance(input_data, dict):
        cameras_raw = (input_data.get("cameras") or input_data.get("data") or
                       input_data.get("features") or list(input_data.values()))
        if isinstance(cameras_raw, dict):
            cameras_raw = list(cameras_raw.values())
    else:
        cameras_raw = input_data

    # GeoJSON FeatureCollection
    if isinstance(input_data, dict) and input_data.get("type") == "FeatureCollection":
        cameras_raw = []
        for feat in input_data.get("features", []):
            props = feat.get("properties", {})
            geom  = feat.get("geometry", {})
            if geom.get("type") == "Point":
                coords = geom.get("coordinates", [0, 0])
                props["x"] = coords[0]  # lng
                props["y"] = coords[1]  # lat
            cameras_raw.append(props)

    jsep_cameras = []
    for i, cam in enumerate(cameras_raw):
        if not isinstance(cam, dict):
            continue

        # ── Extract coordinates ──────────────────────────────────────────────
        x = cam.get("x") or cam.get("longitude") or cam.get("lng") or cam.get("lon") or \
            cam.get("Longitude") or cam.get("X") or 0.0
        y = cam.get("y") or cam.get("latitude") or cam.get("lat") or \
            cam.get("Latitude") or cam.get("Y") or 0.0

        try:
            x, y = float(x), float(y)
        except (ValueError, TypeError):
            try:
                x = parse_dms(str(x))
                y = parse_dms(str(y))
            except Exception:
                print(f"  ⚠ Cannot parse coordinates for camera {i}: x={x}, y={y}")
                continue

        lat, lng = detect_and_convert(x, y)

        # ── Extract name/ID ──────────────────────────────────────────────────
        cam_name = (cam.get("name") or cam.get("camera_name") or cam.get("location") or
                    cam.get("nama") or cam.get("lokasi") or cam.get("title") or
                    cam.get("label") or f"CAM-{i:04d}")

        cam_id = (cam.get("id") or cam.get("camera_id") or cam.get("camId") or
                  cam.get("site_name") or cam.get("siteName") or
                  f"CAM-AUTO-{i:04d}")

        # ── Detect corridor from name ────────────────────────────────────────
        name_lower = str(cam_name).lower()
        corridor = "UNKNOWN"
        for corr, keywords in {
            "SUDIRMAN":       ["sudirman", "jend sudirman"],
            "THAMRIN":        ["thamrin", "mh thamrin", "m.h. thamrin"],
            "GATOT_SUBROTO":  ["gatot", "gatsu", "gatot subroto"],
            "HR_RASUNA_SAID": ["rasuna", "hr rasuna"],
            "SIMATUPANG":     ["simatupang", "tb simatupang"],
            "BUNDARAN_HI":    ["bundaran hi", "bundaran hotel indonesia"],
            "SEMANGGI":       ["semanggi"],
            "KUNINGAN":       ["kuningan"],
        }.items():
            if any(kw in name_lower for kw in keywords):
                corridor = corr
                break

        # ── Build stream URLs ────────────────────────────────────────────────
        stream_urls = build_stream_url(cam)
        primary_url = (stream_urls.get("hls") or stream_urls.get("rtsp") or
                       stream_urls.get("embed") or stream_urls.get("youtube") or "")

        jsep_cameras.append({
            "id":           str(cam_id),
            "name":         str(cam_name),
            "lat":          lat,
            "lng":          lng,
            "corridor":     corridor,
            "stream_url":   primary_url,
            "stream_type":  "hls" if ".m3u8" in primary_url else
                            "rtsp" if primary_url.startswith("rtsp") else
                            "embed" if primary_url else "unknown",
            "stream_urls":  stream_urls,
            "status":       "unknown",      # updated by probe_cameras()
            "source":       cam.get("source", "imported"),
            "_raw":         cam,            # keep original for debugging
        })

    print(f"Parsed {len(jsep_cameras)} cameras from {len(cameras_raw)} raw entries")
    return jsep_cameras


# ─── Stream health probe ──────────────────────────────────────────────────────

async def probe_single(session: aiohttp.ClientSession,
                        cam: dict, timeout: int = 4) -> bool:
    """Return True if HLS m3u8 URL responds with valid playlist."""
    url = cam.get("stream_urls", {}).get("hls") or cam["stream_url"]
    if not url or not url.endswith(".m3u8"):
        return False
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as r:
            if r.status == 200:
                content = await r.text()
                return "#EXTM3U" in content
    except Exception:
        pass
    return False


async def probe_cameras(cameras: list[dict], max_concurrent: int = 20) -> list[dict]:
    """Probe all cameras concurrently, update status field."""
    print(f"Probing {len(cameras)} camera streams (max {max_concurrent} concurrent)...")
    sem = asyncio.Semaphore(max_concurrent)

    async def probe_with_sem(session, cam):
        async with sem:
            is_live = await probe_single(session, cam)
            cam["status"] = "online" if is_live else "offline"
            return cam

    async with aiohttp.ClientSession() as session:
        tasks = [probe_with_sem(session, cam) for cam in cameras]
        results = await asyncio.gather(*tasks)

    online = sum(1 for c in results if c["status"] == "online")
    print(f"Results: {online}/{len(results)} cameras online")
    return results


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Convert Indonesian CCTV JSON → JSEP cameras format"
    )
    parser.add_argument("--input",  "-i", required=True, help="Input JSON file")
    parser.add_argument("--output", "-o", default="fixtures/cameras_jsep.json")
    parser.add_argument("--probe",  action="store_true",
                        help="Probe each camera HLS stream for liveness")
    parser.add_argument("--pilot-only", action="store_true",
                        help="Output only Sudirman/Thamrin/Gatot Subroto cameras")
    args = parser.parse_args()

    raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
    cameras = parse_camera_json(raw)

    if args.pilot_only:
        pilot_corridors = {"SUDIRMAN", "THAMRIN", "GATOT_SUBROTO", "BUNDARAN_HI", "SEMANGGI"}
        cameras = [c for c in cameras if c["corridor"] in pilot_corridors]
        print(f"Filtered to {len(cameras)} pilot-corridor cameras")

    if args.probe:
        cameras = asyncio.run(probe_cameras(cameras))

    # Remove _raw to keep output clean
    output = [{k: v for k, v in cam.items() if k != "_raw"} for cam in cameras]

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(output, indent=2, ensure_ascii=False),
                                  encoding="utf-8")

    online  = sum(1 for c in output if c.get("status") == "online")
    unknown = sum(1 for c in output if c.get("status") == "unknown")
    print(f"\nSaved {len(output)} cameras → {args.output}")
    print(f"  Online: {online} | Offline: {len(output)-online-unknown} | Unknown: {unknown}")
    print(f"\nNext: seed into DB with:")
    print(f"  python scripts/seed_cameras.py --input {args.output}")

if __name__ == "__main__":
    main()

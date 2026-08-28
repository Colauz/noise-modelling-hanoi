#!/usr/bin/env python3
"""Index the traffic videos: where each was taken, when, and how long it runs.

WHY THIS IS NOT A NUMBERED PIPELINE STEP. It reads data/raw/videos/, which is
6 GB of footage that is not distributed and is not in the repository. A clone
cannot run it. The index it writes IS committed, because it holds no image
data -- only a coordinate, a timestamp and a duration per file -- and every
downstream use (the site map, the counts of which sites carry video) reads the
index rather than the footage.

The coordinate comes from the QuickTime `location.ISO6709` tag the capture app
writes. Files without one are kept in the index with a null coordinate rather
than dropped: a video that exists but cannot be placed is a fact about the
campaign, and silently losing it would overstate the coverage.

    python scripts/index_videos.py
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIDEOS = ROOT / "data" / "raw" / "videos"
OUT = ROOT / "data" / "processed" / "video_index.csv"

# ISO 6709: "+20.99382+105.86902+8CRSWGS_84" -- signed lat, signed lon, then an
# optional altitude and CRS. The two leading signed decimals are what we want.
ISO6709 = re.compile(r"([+-]\d+\.?\d*)([+-]\d+\.?\d*)")


def probe(path: Path) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", "-show_streams", str(path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return {}
    return json.loads(result.stdout)


def main() -> None:
    rows = []
    for path in sorted(VIDEOS.iterdir()):
        if path.suffix.lower() not in (".mov", ".mp4", ".avi", ".mkv"):
            continue
        meta = probe(path)
        if not meta:
            rows.append({"file": path.name})
            continue
        tags = meta.get("format", {}).get("tags", {})
        video = next(
            (s for s in meta.get("streams", []) if s["codec_type"] == "video"), {}
        )
        location = tags.get("com.apple.quicktime.location.ISO6709", "")
        match = ISO6709.match(location)
        rows.append(
            {
                "file": path.name,
                "latitude": float(match.group(1)) if match else "",
                "longitude": float(match.group(2)) if match else "",
                "creation_time": tags.get("creation_time", ""),
                "duration_s": round(float(meta["format"]["duration"]), 2),
                "width": video.get("width", ""),
                "height": video.get("height", ""),
                "size_mb": round(path.stat().st_size / 1e6, 1),
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fields = ["file", "latitude", "longitude", "creation_time", "duration_s",
              "width", "height", "size_mb"]
    with OUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    placed = sum(1 for r in rows if r.get("latitude") != "" and "latitude" in r)
    total_s = sum(r.get("duration_s", 0) or 0 for r in rows)
    print(f"{OUT.relative_to(ROOT)}: {len(rows)} videos, {placed} with a "
          f"coordinate, {total_s / 60:.0f} min of footage")


if __name__ == "__main__":
    main()

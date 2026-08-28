#!/usr/bin/env python3
"""Fetch the administrative units of Hanoi from OpenStreetMap, once.

WHY THIS IS NOT A NUMBERED PIPELINE STEP. Every `NN_*.py` script in this
directory runs offline against artefacts already in the repository. This one
reaches the network, so it is deliberately outside that numbering: it is run by
hand when the boundaries need refreshing, and its output is committed. Nothing
in `make results` depends on it, and no figure calls it -- figures read the
committed GeoJSON.

WHAT IT FETCHES. Vietnam reorganised its local government in July 2025,
abolishing the district tier. OpenStreetMap carries the new structure, and the
consequence for a query is easy to get wrong: the phuong (wards) and xa
(communes) now sit at `admin_level=6`, directly under the city, where the
districts used to be. Asking for `admin_level=8` -- the level wards were at
before the reform, and the one most tutorials name -- returns nothing at all.

The result is 126 units: 51 phuong, which are the urban wards and the frame the
planned campaign draws from, and 75 xa, which are rural and outside it.

    python scripts/fetch_hanoi_wards.py
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "hanoi_wards.geojson"
OUT_DEV = ROOT / "data" / "processed" / "hanoi_new_developments.geojson"

# Relation 1903516 is Thanh pho Ha Noi at admin_level=4. Overpass addresses a
# relation as an area by adding 3600000000 to its id.
HANOI_AREA = 3_601_903_516

QUERY = f"""
[out:json][timeout:300];
area({HANOI_AREA})->.hanoi;
relation(area.hanoi)["boundary"="administrative"]["admin_level"="6"];
out geom;
"""

# The boundaries are drawn at roughly 1:150 000 in the figure that uses them, and
# the raw geometry is far finer than that. Dropping vertices closer together
# than this leaves the outlines visually identical and the file a fraction of
# the size. Degrees; 1e-4 is about 11 m.
SIMPLIFY_TOL = 2e-4

# The second query. `khu do thi` is the Vietnamese term for a planned new urban
# area, and it is what the developments this campaign has to cover are called
# on the ground and in OSM -- Ocean Park is one. Matching the term plus the
# handful of developer names that do not use it is what lets the sampling frame
# be defined by what is built rather than by which administrative label a
# commune still carries. Hanoi's periphery is full of places that are urban in
# every respect except that the map still calls them a xa.
DEV_QUERY = f"""
[out:json][timeout:300];
area({HANOI_AREA})->.hanoi;
(
  way(area.hanoi)["landuse"="residential"]["name"];
  relation(area.hanoi)["landuse"="residential"]["name"];
  way(area.hanoi)["place"~"^(suburb|neighbourhood|quarter)$"]["name"];
  relation(area.hanoi)["place"~"^(suburb|neighbourhood|quarter)$"]["name"];
);
out tags center;
"""

DEV_PATTERN = re.compile(
    r"khu đô thị|khu do thi|vinhomes|ocean park|ecopark|gamuda|ciputra|"
    r"splendora|smart city|times? city|royal city|new city|garden city|"
    r"starlake|an khánh|thanh hà",
    re.IGNORECASE,
)


def fetch(query: str = QUERY) -> dict:
    request = urllib.request.Request(
        "https://overpass-api.de/api/interpreter",
        data=urllib.parse.urlencode({"data": query}).encode(),
        headers={"User-Agent": "noise-modelling-hanoi (research, contact via repo)"},
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.loads(response.read())


def developments(payload: dict) -> dict:
    """Named new urban areas, as points. Centres are enough: the figure marks
    where a development is, and the frame test is which unit contains it."""
    features = []
    for element in payload["elements"]:
        name = element.get("tags", {}).get("name", "")
        centre = element.get("center")
        if not centre or not DEV_PATTERN.search(name):
            continue
        features.append(
            {
                "type": "Feature",
                "properties": {"name": name, "osm_id": element["id"]},
                "geometry": {"type": "Point",
                             "coordinates": [centre["lon"], centre["lat"]]},
            }
        )
    return {"type": "FeatureCollection", "features": features}


def to_geojson(payload: dict) -> dict:
    """Overpass `out geom` gives each relation's ways; stitch them into rings.

    A boundary relation's outer ways arrive in no particular order and in no
    particular direction, so they are chained end to end rather than simply
    concatenated -- concatenating them produces a polygon that crosses itself
    and fills wrongly.
    """
    from shapely.geometry import LineString, mapping
    from shapely.ops import linemerge, unary_union, polygonize

    features = []
    for element in payload["elements"]:
        tags = element.get("tags", {})
        name = tags.get("name", "")
        lines = [
            LineString([(p["lon"], p["lat"]) for p in member["geometry"]])
            for member in element.get("members", [])
            if member.get("role") in ("outer", "") and member.get("geometry")
        ]
        if not lines:
            continue
        polygons = list(polygonize(unary_union(linemerge(lines))))
        if not polygons:
            continue
        geometry = unary_union(polygons).simplify(SIMPLIFY_TOL, preserve_topology=True)
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "name": name,
                    # The one property the figure actually branches on.
                    "kind": "phuong" if name.startswith("Phường") else "xa",
                    "osm_id": element["id"],
                },
                "geometry": mapping(geometry),
            }
        )
    return {"type": "FeatureCollection", "features": features}


def main() -> None:
    collection = to_geojson(fetch())
    kinds = [f["properties"]["kind"] for f in collection["features"]]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(collection, separators=(",", ":")))
    print(f"{OUT.relative_to(ROOT)}: {len(collection['features'])} units "
          f"({kinds.count('phuong')} phuong, {kinds.count('xa')} xa), "
          f"{OUT.stat().st_size // 1024} KB")

    dev = developments(fetch(DEV_QUERY))
    OUT_DEV.write_text(json.dumps(dev, separators=(",", ":")))
    print(f"{OUT_DEV.relative_to(ROOT)}: {len(dev['features'])} named new "
          f"urban developments, {OUT_DEV.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()

"""Download the OpenStreetMap extract the feature builder reads.

`03_build_features.py` expects `data/interim/hanoi_sites_buildings.gpkg` and
`hanoi_sites_roads.graphml` and stops if they are absent, pointing at
`docs/data-sources.md` -- which describes the extract as regenerable without
saying by what. Notebook 04 did the download for Uganda and nothing did it for
Hanoi, so on a fresh clone the chain could not start. This is that step.

The extract is a dated snapshot of an upstream that moves: two runs a year apart
will not produce identical buildings. That is why it is not versioned, and why
every number derived from it carries the date of the run rather than a checksum.

Usage: python3 scripts/02b_fetch_osm_extract.py   (from the repository root)
"""
import os
import sys

import geopandas as gpd
import osmnx as ox
import pandas as pd

from noise_hanoi import config as cfg

#: About a kilometre beyond the measured envelope, so that a 300 m feature radius
#: at the edge still sees real morphology rather than an empty margin.
MARGIN_DEG = 0.01


def main() -> int:
    if not os.path.exists(cfg.MEASUREMENTS):
        print(f'Missing {cfg.MEASUREMENTS}', file=sys.stderr)
        return 1
    os.makedirs(cfg.INTERIM, exist_ok=True)

    df = pd.read_csv(cfg.MEASUREMENTS)
    bbox = (df.longitude.min() - MARGIN_DEG, df.latitude.min() - MARGIN_DEG,
            df.longitude.max() + MARGIN_DEG, df.latitude.max() + MARGIN_DEG)
    print(f'{len(df)} points -> bbox {bbox}')

    if os.path.exists(cfg.BUILDINGS_GPKG):
        print(f'buildings: already at {cfg.BUILDINGS_GPKG}')
    else:
        print('buildings: downloading (several minutes the first time)...')
        b = ox.features_from_bbox(bbox, tags={'building': True})
        b = b[b.geometry.geom_type.isin(['Polygon', 'MultiPolygon'])]
        gpd.GeoDataFrame(geometry=b.geometry, crs=b.crs).to_file(cfg.BUILDINGS_GPKG, driver='GPKG')
        print(f'  {len(b)} buildings -> {cfg.BUILDINGS_GPKG}')

    if os.path.exists(cfg.ROADS_GRAPHML):
        print(f'roads: already at {cfg.ROADS_GRAPHML}')
    else:
        print('roads: downloading...')
        G = ox.graph_from_bbox(bbox, network_type='drive', simplify=True)
        ox.save_graphml(G, cfg.ROADS_GRAPHML)
        print(f'  {len(G.edges)} edges -> {cfg.ROADS_GRAPHML}')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())

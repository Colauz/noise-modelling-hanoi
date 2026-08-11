#!/usr/bin/env python3
"""Build the OSM morphology features for the field measurement points.

    python3 scripts/03_build_features.py

Reads   data/processed/measurements.csv
        data/interim/hanoi_sites_buildings.gpkg
        data/interim/hanoi_sites_roads.graphml
Writes  data/interim/features.parquet

Why this script exists
----------------------
Until August 2026 this step lived in a cell of `notebooks/08_predict_hanoi.ipynb`,
which imported `morphology()` from `scripts/export_gama_zones.py` through a
`sys.path` hack. Every published number depends on these features, yet the only
way to produce them was to open a notebook -- so the chain could not run headless
and `make all` could not exist. The computation is unchanged; only its home is.

The OSM extract is not downloaded here. It is cached in data/interim/ and, being
a snapshot of a moving database, is treated as an input with a date rather than
something to refetch silently. See docs/data-sources.md.
"""

import os
import sys

from noise_hanoi import config as cfg
from noise_hanoi import features as feat


def main() -> int:
    for path, hint in ((cfg.MEASUREMENTS, 'python3 scripts/01_prepare_field_data.py'),
                       (cfg.BUILDINGS_GPKG, 'see docs/data-sources.md (OSM extract)'),
                       (cfg.ROADS_GRAPHML, 'see docs/data-sources.md (OSM extract)')):
        if not os.path.exists(path):
            print(f'Missing {path}\n  -> {hint}', file=sys.stderr)
            return 1

    os.makedirs(cfg.INTERIM, exist_ok=True)
    df = feat.measurement_features()
    df.to_parquet(cfg.FEATURES, index=False)

    cols = ['built_area_ratio', 'road_density_km_km2', 'intersection_count',
            'dist_road_m', 'dist_highway_m', 'dist_residential_m']
    print(f'OK -> {cfg.FEATURES}')
    print(f'  {len(df)} points, {len(cols)} morphology features, '
          f'radius {cfg.FEATURE_RADIUS_M} m, CRS {cfg.CRS_HANOI}')
    print(df[cols].describe().T[['mean', 'std', 'min', 'max']].round(4).to_string())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

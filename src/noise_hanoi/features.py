"""OpenStreetMap morphology features around a set of points.

Extracted verbatim from `scripts/export_gama_zones.py` (now
`scripts/07_export_gama_inputs.py`), which was the only definition of these
functions. `scripts/04_evaluate_models.py` and notebook 08 reached them by
inserting `scripts/` on `sys.path` and importing the module by filename, which
stopped working once the scripts were numbered -- a module name cannot start
with a digit. They live here instead, so both callers import the same code
through a normal package import and the feature definition has one home.

The numbers this module produces feed every published figure, so the extraction
was verified element by element against the previous code path: see
`tests/test_features_extraction.py` and docs/handover.md.
"""

from __future__ import annotations

import os

import geopandas as gpd
import numpy as np
import osmnx as ox
import pandas as pd

from . import config as cfg

#: Metric CRS. Every distance and area below is computed in it.
CRS_M = cfg.CRS_HANOI
#: Radius over which morphology is aggregated, in metres.
R = cfg.FEATURE_RADIUS_M
AREA_M2 = np.pi * R ** 2

#: Feature set v1, kept for the archived baseline models.
FEATURES = ['built_area_ratio', 'road_density_km_km2', 'intersection_count',
            'dist_road_m', 'hour', 'is_weekend']
#: Feature set v2, used by the residual model of the delivered hybrid.
FEATURES2 = ['built_area_ratio', 'road_density_km_km2', 'intersection_count',
             'dist_highway_m', 'dist_residential_m',
             'hour_sin', 'hour_cos', 'is_weekend']

# Two acoustic road classes (v2, August 2026).
# Rationale: `dist_road_m` lumped a four-lane trunk road together with a
# residential alley, although their acoustic power per linear metre differs by
# an order of magnitude. A distance to "the source" means nothing if the source
# is not identified. `tertiary` sits with the small streets: in dense Hanoi
# fabric it is a local distributor, not a through route. That is a PARAMETER of
# the model, not a truth: moving it into MAJOR_HW redefines both variables.
MAJOR_HW = {'motorway', 'trunk', 'primary', 'secondary',
            'motorway_link', 'trunk_link', 'primary_link', 'secondary_link'}
#: Fallback distance when a road class is absent from the zone, in metres.
FAR_M = 2000.0


def load_osm(proc_dir: str | None = None):
    """Load the cached OSM extract for the three sites.

    Returns (buildings, building_centroids, nodes, edges), all in CRS_M.
    """
    proc = proc_dir or cfg.INTERIM
    bld = gpd.read_file(os.path.join(proc, 'hanoi_sites_buildings.gpkg')).to_crs(CRS_M)
    bld['area_m2'] = bld.geometry.area
    bld_c = bld.set_geometry(bld.geometry.centroid)
    G = ox.load_graphml(os.path.join(proc, 'hanoi_sites_roads.graphml'))
    nodes, edges = ox.graph_to_gdfs(G)
    return (bld, bld_c,
            nodes.to_crs(CRS_M).reset_index(drop=True),
            edges.to_crs(CRS_M).reset_index(drop=True))


def classify_roads(edges):
    """Split the network into (major roads, minor streets) on the OSM `highway` tag."""
    hw = edges['highway'].apply(lambda v: v[0] if isinstance(v, list) else v)
    is_major = hw.isin(MAJOR_HW)
    return edges[is_major], edges[~is_major]


def _dist_to(pts_gdf, lines):
    """Distance from each point to the nearest line of `lines`."""
    if lines is None or len(lines) == 0:
        return np.full(len(pts_gdf), FAR_M)
    near = gpd.sjoin_nearest(pts_gdf[['geometry']], lines[['geometry']], distance_col='d')
    d = near.groupby(near.index)['d'].min().reindex(range(len(pts_gdf))).values
    return np.nan_to_num(d, nan=FAR_M)


def morphology(pts_gdf, bld_c, nodes, edges):
    """Morphology features in a radius of R metres around each point.

    `dist_road_m` is kept alongside the per-class distances: the comparison
    protocols in 04_evaluate_models.py reference it as the historical physical
    baseline.
    """
    buf = gpd.GeoDataFrame({'pt_id': range(len(pts_gdf))},
                           geometry=pts_gdf.geometry.buffer(R), crs=CRS_M)
    jb = gpd.sjoin(bld_c[['geometry', 'area_m2']], buf, predicate='within')
    area_sum = jb.groupby('pt_id')['area_m2'].sum()
    built = np.minimum(np.array([area_sum.get(i, 0) for i in range(len(pts_gdf))]) / AREA_M2, 1.0)

    jr = gpd.sjoin(edges[['geometry']], buf, predicate='intersects')
    rl = jr.groupby('pt_id').apply(lambda g: g.geometry.length.sum())
    road_km = np.array([(rl.get(i, 0) / 1000) / (AREA_M2 / 1e6) for i in range(len(pts_gdf))])

    jn = gpd.sjoin(nodes[['geometry']], buf, predicate='within').groupby('pt_id').size()
    inter = np.array([jn.get(i, 0) for i in range(len(pts_gdf))])

    major, minor = classify_roads(edges)
    dist = _dist_to(pts_gdf, edges)
    dist_hw = _dist_to(pts_gdf, major)
    dist_res = _dist_to(pts_gdf, minor)

    return pd.DataFrame({'built_area_ratio': built, 'road_density_km_km2': road_km,
                         'intersection_count': inter, 'dist_road_m': dist,
                         'dist_highway_m': dist_hw, 'dist_residential_m': dist_res})


def add_time_features(feats, hour, is_weekend=0):
    """Add the hour as CYCLIC variables, plus a weekend flag.

    A raw 0-23 hour forces an artificial discontinuity between 23:00 and 00:00
    and makes a tree split a variable that is in fact circular. sin/cos over 24 h
    restores continuity. `hour` is kept because the site x hour baseline uses it
    as a grouping key.
    """
    feats['hour'] = hour
    feats['hour_sin'] = np.sin(2 * np.pi * np.asarray(hour) / 24.0)
    feats['hour_cos'] = np.cos(2 * np.pi * np.asarray(hour) / 24.0)
    feats['is_weekend'] = is_weekend
    return feats


def measurement_features(measurements_csv: str | None = None, proc_dir: str | None = None):
    """Features for the field measurement points, as consumed by the models.

    Returns the measurement table joined with its morphology features and the
    projected coordinates, which is exactly what 04_evaluate_models.py builds.
    """
    path = measurements_csv or cfg.MEASUREMENTS
    m = pd.read_csv(path, parse_dates=['timestamp'])
    m['hour'] = m.timestamp.dt.hour
    m['hour_sin'] = np.sin(2 * np.pi * m.hour / 24.0)
    m['hour_cos'] = np.cos(2 * np.pi * m.hour / 24.0)
    m['is_weekend'] = m.timestamp.dt.dayofweek.isin([5, 6]).astype(int)
    m = m.dropna(subset=['noise_dB', 'latitude', 'longitude']).reset_index(drop=True)

    _, bld_c, nodes, edges = load_osm(proc_dir)
    pts = gpd.GeoDataFrame(m, geometry=gpd.points_from_xy(m.longitude, m.latitude),
                           crs='EPSG:4326').to_crs(CRS_M)
    feats = morphology(pts, bld_c, nodes, edges)

    df = pd.concat([m, feats], axis=1)
    df['x'] = pts.geometry.x.values
    df['y'] = pts.geometry.y.values
    return df

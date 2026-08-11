"""The morphology features are the input to every published number.

They were moved out of `scripts/export_gama_zones.py` into
`noise_hanoi.features` in August 2026, when numbering the scripts made the old
`sys.path` import impossible. The move was verified element by element at the
time; these tests keep the contract from drifting afterwards.

They are skipped when the OSM extract is absent, since it is not published.
"""

import os

import numpy as np
import pandas as pd
import pytest

from noise_hanoi import config as cfg
from noise_hanoi import features as feat

EXPECTED = ['built_area_ratio', 'road_density_km_km2', 'intersection_count',
            'dist_road_m', 'dist_highway_m', 'dist_residential_m']

needs_osm = pytest.mark.skipif(
    not (os.path.exists(cfg.BUILDINGS_GPKG) and os.path.exists(cfg.ROADS_GRAPHML)),
    reason='OSM extract not present (see docs/data-sources.md)',
)


def test_feature_radius_matches_the_documented_value():
    assert feat.R == cfg.FEATURE_RADIUS_M == 300
    assert np.isclose(feat.AREA_M2, np.pi * 300 ** 2)


def test_road_classes_are_disjoint_and_documented():
    assert 'tertiary' not in feat.MAJOR_HW, (
        'tertiary belongs with the minor streets: in dense Hanoi fabric it is a local '
        'distributor. Moving it redefines dist_highway_m and dist_residential_m.'
    )
    assert 'motorway' in feat.MAJOR_HW and 'primary' in feat.MAJOR_HW


def test_cyclic_hour_makes_23h_and_0h_neighbours():
    """The reason the hour is encoded as sin/cos rather than 0-23."""
    df = pd.DataFrame({'x': [0.0, 0.0]})
    a = feat.add_time_features(df.copy(), np.array([23, 0]))
    d_cyclic = np.hypot(a.hour_sin[0] - a.hour_sin[1], a.hour_cos[0] - a.hour_cos[1])
    d_raw = abs(23 - 0)
    assert d_cyclic < 0.3 < d_raw


@needs_osm
def test_features_match_the_committed_artefact():
    """Recomputing must reproduce data/interim/features.parquet exactly."""
    if not os.path.exists(cfg.FEATURES):
        pytest.skip('features.parquet not built yet (make features)')
    stored = pd.read_parquet(cfg.FEATURES)
    fresh = feat.measurement_features()
    assert list(stored.columns) == list(fresh.columns)
    assert len(stored) == len(fresh)
    for c in EXPECTED:
        np.testing.assert_array_equal(
            stored[c].to_numpy(dtype=float), fresh[c].to_numpy(dtype=float),
            err_msg=f'{c} drifted from the stored features')


@needs_osm
def test_distances_are_ordered_by_construction():
    """dist_road_m is the distance to the nearest road of ANY class, so it can
    never exceed either per-class distance."""
    if not os.path.exists(cfg.FEATURES):
        pytest.skip('features.parquet not built yet (make features)')
    f = pd.read_parquet(cfg.FEATURES)
    assert (f.dist_road_m <= f.dist_highway_m + 1e-9).all()
    assert (f.dist_road_m <= f.dist_residential_m + 1e-9).all()
    assert (f.built_area_ratio.between(0, 1)).all()

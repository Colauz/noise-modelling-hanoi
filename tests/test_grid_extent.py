"""The published map must not extend beyond the sampled envelope.

This file exists because of a specific failure. Notebooks 08 and 09 once
produced a noise grid over Bach Khoa, a district where no measurement was ever
taken, using a model whose leave-one-site-out score is negative on two of the
three sites it *was* trained on. Those artefacts were retracted; see
docs/archive/bach-khoa/README.md.

The invariant: every published cell lies within the measured points plus the
declared margin, and nothing else.
"""

import os

import numpy as np
import pandas as pd
import pytest

from noise_hanoi import config as cfg

pytestmark = pytest.mark.skipif(
    not os.path.exists(cfg.NOISE_MAP_CSV),
    reason='the map has not been built yet (make results)',
)

# The retracted Bach Khoa extent, from docs/archive/bach-khoa/README.md.
BACH_KHOA = dict(lat=(20.992, 21.019), lon=(105.829, 105.858))
# Degrees per metre at Hanoi's latitude, near enough for an envelope check.
DEG_PER_M_LAT = 1.0 / 111_320.0
DEG_PER_M_LON = 1.0 / (111_320.0 * np.cos(np.radians(21.0)))


def _map_and_measurements():
    return pd.read_csv(cfg.NOISE_MAP_CSV), pd.read_csv(cfg.MEASUREMENTS)


def test_every_cell_lies_within_the_sampled_envelope_plus_margin():
    grid, meas = _map_and_measurements()
    margin_lat = cfg.GRID_MARGIN_M * DEG_PER_M_LAT
    margin_lon = cfg.GRID_MARGIN_M * DEG_PER_M_LON

    for site, g in grid.groupby('site'):
        m = meas[meas.site == site]
        assert len(m), f'{site} appears in the map with no measurement behind it'
        assert g.latitude.min() >= m.latitude.min() - margin_lat * 1.05
        assert g.latitude.max() <= m.latitude.max() + margin_lat * 1.05
        assert g.longitude.min() >= m.longitude.min() - margin_lon * 1.05
        assert g.longitude.max() <= m.longitude.max() + margin_lon * 1.05


def test_no_cell_falls_in_the_retracted_bach_khoa_extent():
    grid, _ = _map_and_measurements()
    inside = grid[grid.latitude.between(*BACH_KHOA['lat'])
                  & grid.longitude.between(*BACH_KHOA['lon'])]
    assert inside.empty, (
        f'{len(inside)} cells fall inside the retracted Bach Khoa extent, where no '
        f'measurement was ever taken. See docs/archive/bach-khoa/README.md.'
    )


def test_every_mapped_site_is_a_measured_site():
    grid, meas = _map_and_measurements()
    assert set(grid.site) <= set(meas.site)


def test_predicted_levels_stay_physically_plausible():
    grid, _ = _map_and_measurements()
    hcols = [c for c in grid.columns if c.startswith('h') and c[1:].isdigit()]
    assert hcols, 'no hourly column in the published map'
    v = grid[hcols].to_numpy(dtype=float)
    assert np.isfinite(v).all()
    assert v.min() > 30 and v.max() < 100

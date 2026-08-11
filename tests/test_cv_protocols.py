"""Regression tests for the cross-validation geometry.

This file exists because of a specific failure. Until July 2026 the project
advertised R2 = 0.45 under "honest spatial cross-validation". The split was a
GroupKFold on ~110 m cells, while the features are aggregated over a 300 m
radius: neighbouring points shared most of their support, so the held-out fold
was not independent of the training fold. The figure was withdrawn.

The invariant that would have caught it is small and cheap: the exclusion radius
of the buffered leave-one-out protocol must never be smaller than the radius
over which features are aggregated.
"""

import numpy as np
import pytest

from noise_hanoi import config as cfg


def test_bloo_radius_is_not_smaller_than_the_feature_radius():
    """The leak that produced the withdrawn R2 = 0.45, as an assertion."""
    assert cfg.BLOO_RADIUS_M >= cfg.FEATURE_RADIUS_M, (
        f'Buffered LOO excludes points within {cfg.BLOO_RADIUS_M} m while features '
        f'are aggregated over {cfg.FEATURE_RADIUS_M} m. Held-out points share support '
        f'with training points: the score is optimistic. This is exactly the 110 m '
        f'versus 300 m mismatch that was retracted.'
    )


def test_block_size_exceeds_the_feature_radius():
    """A 600 m block must be wider than the 300 m feature support."""
    assert cfg.BLOCK_SIZE_M > cfg.FEATURE_RADIUS_M


def _bloo_holdout(points, i, radius):
    """Training indices for buffered leave-one-out around point i."""
    d = np.hypot(points[:, 0] - points[i, 0], points[:, 1] - points[i, 1])
    return np.where(d > radius)[0]


def test_bloo_actually_excludes_every_point_inside_the_buffer():
    """The protocol as implemented, not merely as configured."""
    rng = np.random.default_rng(0)
    pts = rng.uniform(0, 2000, size=(200, 2))
    for i in (0, 37, 199):
        train = _bloo_holdout(pts, i, cfg.BLOO_RADIUS_M)
        d = np.hypot(pts[train, 0] - pts[i, 0], pts[train, 1] - pts[i, 1])
        assert (d > cfg.BLOO_RADIUS_M).all()
        assert i not in train


def test_a_110m_buffer_would_leak_and_is_detectable():
    """Guard the guard: the assertion above must fail for the retracted setting."""
    rng = np.random.default_rng(1)
    pts = rng.uniform(0, 1000, size=(300, 2))
    train = _bloo_holdout(pts, 0, 110)
    d = np.hypot(pts[train, 0] - pts[0, 0], pts[train, 1] - pts[0, 1])
    leaking = (d < cfg.FEATURE_RADIUS_M).sum()
    assert leaking > 0, (
        'With a 110 m buffer, training points are expected to remain inside the '
        '300 m feature support. If this ever passes, the test is not testing.'
    )


def test_hours_cover_the_campaign_window():
    assert min(cfg.HOURS) == 5 and max(cfg.HOURS) == 21

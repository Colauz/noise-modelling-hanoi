"""Uganda -> Hanoi transfer: the study's second negative result, made reproducible.

The claim -- a surrogate trained on Sunbird's Kampala/Entebbe data fails on Hanoi
-- was stated in `docs/literature-review.md` and in the header of
`barcelona_transfer.py`, and the number appeared in neither `metrics.json` nor
`model_comparison.md`. It could not be checked from a clone. It can now: the two
Uganda boosters are versioned in `models/`, so the experiment needs no Ugandan
data, only Hanoi's own features.

    python3 scripts/02b_fetch_osm_extract.py    # OSM extract, if absent
    python3 scripts/03_build_features.py        # features.parquet
    python3 scripts/experiments/uganda_transfer.py

What it reports, and why in three parts: a raw R2 says a model failed, and says
nothing about *how*. Removing the mean difference asks whether the failure is a
calibration offset between two cities. Fitting a slope as well asks the kindest
possible question -- whether the model ranks Hanoi's locations correctly even if
its scale is wrong. That last figure is r^2, and it is the ceiling any
recalibration of the transferred model could reach.
"""
import os
import sys

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error

from noise_hanoi import config as cfg

#: The feature names each booster was trained with, read from its own header.
V1_FEATURES = ['building_density_km2', 'road_density_km_km2', 'intersection_count',
               'dist_road_m', 'hour', 'is_weekend']
V2_FEATURES = ['built_area_ratio', 'road_density_km_km2', 'intersection_count',
               'dist_road_m', 'hour', 'is_weekend']


def evaluate(booster_path, features, df, y):
    X = df.copy()
    # v1 was trained on `building_density_km2`; the Hanoi builder produces
    # `built_area_ratio`. The same quantity under two conventions -- which is the
    # artefact v2 exists to remove, and worth carrying rather than hiding.
    if 'building_density_km2' in features and 'building_density_km2' not in X:
        X['building_density_km2'] = X['built_area_ratio']

    p = lgb.Booster(model_file=booster_path).predict(X[features])
    shifted = p + (y.mean() - p.mean())
    slope, intercept = np.polyfit(p, y, 1)
    rescaled = slope * p + intercept
    return {
        'r2_raw': r2_score(y, p),
        'r2_bias_removed': r2_score(y, shifted),
        'r2_bias_and_scale_removed': r2_score(y, rescaled),
        'r': float(np.corrcoef(p, y)[0, 1]),
        'mae': mean_absolute_error(y, p),
        'rmse': root_mean_squared_error(y, p),
        'bias': float(p.mean() - y.mean()),
        'slope': float(slope),
    }


def main() -> int:
    if not os.path.exists(cfg.FEATURES):
        print(f'Missing {cfg.FEATURES}\n  -> run 02b_fetch_osm_extract.py then '
              f'03_build_features.py', file=sys.stderr)
        return 1

    df = pd.read_parquet(cfg.FEATURES)
    y = df['noise_dB'].values
    print(f'{len(df)} Hanoi points, measured {y.min():.0f}-{y.max():.0f} dB '
          f'(mean {y.mean():.1f})\n')

    rows = []
    for path, feats, label in ((cfg.UGANDA_MODEL, V1_FEATURES, 'Uganda 61K (v1)'),
                               (cfg.UGANDA_MODEL_V2, V2_FEATURES, 'Uganda invariant (v2)')):
        r = evaluate(path, feats, df, y)
        rows.append((label, r))
        print(f'{label}')
        print(f'  as delivered          R2 = {r["r2_raw"]:+8.3f}   MAE {r["mae"]:5.2f} dB '
              f'  bias {r["bias"]:+.1f} dB')
        print(f'  mean difference gone  R2 = {r["r2_bias_removed"]:+8.3f}')
        print(f'  and rescaled          R2 = {r["r2_bias_and_scale_removed"]:+8.3f}   '
              f'(= r^2, the ceiling)   r = {r["r"]:+.3f}   slope {r["slope"]:+.2f}\n')

    # The comparison that gives the numbers their meaning: one locally fitted
    # distance term, on the same points.
    d = np.log1p(df['dist_road_m'].values).reshape(-1, 1)
    local = r2_score(y, LinearRegression().fit(d, y).predict(d))
    print(f'For scale, fitted locally on the same points:')
    print(f'  log(distance to road) alone   R2 = {local:+.3f} (in sample)')
    print(f'  physical kernel, buffered LOO R2 = +0.246 (models/metrics.json)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

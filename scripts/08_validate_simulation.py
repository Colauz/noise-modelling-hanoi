"""Validate the simulation: does the map reproduce our field measurements?

At the exact location of each of our 363 measurements, and at the hour it was taken,
this script compares the level predicted by the grid exported to GAMA against the
level actually recorded in the field.

LIMITATION TO KEEP IN MIND - this is an *in-sample* validation: the model that
produces the grid was trained on those same measurements. The figures below therefore
measure the fidelity of the chain (model -> 40 m grid -> GAMA), not the capacity to
generalise. The honest generalisation figure remains the one from the spatial
cross-validation in scripts/04_evaluate_models.py (buffered leave-one-out), where the
model predicts places it has never seen.

Outputs: results/figures/validation_simulation.png
         results/tables/validation_simulation.csv
Usage  : python3 scripts/08_validate_simulation.py
"""
import os
import warnings

warnings.filterwarnings('ignore')

import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from noise_hanoi import config as cfg

ROOT = cfg.ROOT
MEASURES = cfg.MEASUREMENTS
GRID = os.path.join(cfg.GAMA_INPUTS, 'noise_points.shp')
OUT_PNG = os.path.join(cfg.FIGURES, 'validation_simulation.png')
OUT_CSV = os.path.join(cfg.TABLES, 'validation_simulation.csv')
CRS_M = 'EPSG:32648'
HMIN, HMAX = 5, 21


def build():
    m = pd.read_csv(MEASURES, parse_dates=['timestamp'])
    m['hour'] = m.timestamp.dt.hour
    m = m[(m.hour >= HMIN) & (m.hour <= HMAX)].copy()

    mg = gpd.GeoDataFrame(m, geometry=gpd.points_from_xy(m.longitude, m.latitude),
                          crs='EPSG:4326').to_crs(CRS_M)
    grid = gpd.read_file(GRID).to_crs(CRS_M)
    # la grille porte aussi une colonne `site` : on la renomme pour éviter que la
    # jointure ne suffixe les deux et fasse disparaître `site` des mesures.
    grid = grid.drop(columns=[c for c in ['site'] if c in grid.columns])

    j = gpd.sjoin_nearest(mg, grid, distance_col='cell_dist_m')
    j = j[~j.index.duplicated()].copy()
    j['sim_dB'] = [row[f'h{int(row.hour)}'] for _, row in j.iterrows()]
    j['error'] = j.sim_dB - j.noise_dB
    return j


def stats(j):
    e = j.error
    ss_res = float((e ** 2).sum())
    ss_tot = float(((j.noise_dB - j.noise_dB.mean()) ** 2).sum())
    return {
        'n': len(j),
        'bias': e.mean(),
        'mae': e.abs().mean(),
        'rmse': np.sqrt((e ** 2).mean()),
        'r': j.sim_dB.corr(j.noise_dB),
        'r2': 1 - ss_res / ss_tot,
        'within3': (e.abs() <= 3).mean() * 100,
        'within5': (e.abs() <= 5).mean() * 100,
        'cell_dist': j.cell_dist_m.median(),
    }


def figure(j, s):
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))
    colors = {'Ocean Park': '#c0392b', 'Hoan Kiem lake': '#2471a3', 'Vinh Tuy area': '#1e8449'}

    ax = axes[0]
    for site, g in j.groupby('site'):
        ax.scatter(g.noise_dB, g.sim_dB, s=14, alpha=.55,
                   color=colors.get(site, '#888'), label=site.split()[0])
    lo, hi = 45, 90
    ax.plot([lo, hi], [lo, hi], color='#333', lw=1.2)
    ax.plot([lo, hi], [lo + 5, hi + 5], color='#999', lw=.8, ls='--')
    ax.plot([lo, hi], [lo - 5, hi - 5], color='#999', lw=.8, ls='--')
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
    ax.set_xlabel('Field measurement (dB)'); ax.set_ylabel('Simulation (dB)')
    ax.set_title(f'Simulated vs measured  (r {s["r"]:.2f}, bands +/-5 dB)', fontsize=10)
    ax.legend(fontsize=8); ax.grid(alpha=.3)

    ax = axes[1]
    ax.hist(j.error, bins=np.arange(-20, 21, 2), color='#2471a3', edgecolor='white')
    ax.axvline(0, color='#333', lw=1.2)
    ax.axvline(s['bias'], color='#c0392b', lw=1.5, ls='--',
               label=f'biais {s["bias"]:+.1f} dB')
    ax.set_xlabel('Error, simulation - measurement (dB)'); ax.set_ylabel('Number of points')
    ax.set_title('Error distribution', fontsize=10)
    ax.legend(fontsize=8); ax.grid(alpha=.3)

    ax = axes[2]
    per = pd.cut(j.hour, [4, 8, 12, 16, 22], labels=['5-8h', '9-12h', '13-16h', '17-21h'])
    grp = j.groupby(per, observed=True)['error']
    labels = list(grp.groups.keys())
    ax.boxplot([grp.get_group(k) for k in labels], tick_labels=labels)
    ax.axhline(0, color='#333', lw=1.2)
    ax.set_ylabel('Error (dB)')
    ax.set_title('Error by time of day', fontsize=10)
    ax.grid(alpha=.3)

    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=130, bbox_inches='tight')
    plt.close(fig)


def main():
    j = build()
    s = stats(j)
    j[['site', 'hour', 'noise_dB', 'sim_dB', 'error', 'cell_dist_m']].to_csv(OUT_CSV, index=False)
    figure(j, s)

    print(f'{s["n"]} measurements compared against the grid '
          f'(median distance to cell centre: {s["cell_dist"]:.0f} m)')
    print(f'  biais {s["bias"]:+.2f} dB · MAE {s["mae"]:.2f} dB · RMSE {s["rmse"]:.2f} dB')
    print(f'  r {s["r"]:.3f} · R² {s["r2"]:.3f}')
    print(f'  dans ±3 dB : {s["within3"]:.0f} %   dans ±5 dB : {s["within5"]:.0f} %')
    print('\npar site :')
    for site, g in j.groupby('site'):
        print(f'  {site:16} n={len(g):3}  biais {g.error.mean():+5.2f}  '
              f'MAE {g.error.abs().mean():4.2f}  r {g.sim_dB.corr(g.noise_dB):.2f}')
    print(f'\nOK -> {OUT_PNG}')
    ref = cfg.METRICS_JSON
    if os.path.exists(ref):
        import json
        M = json.load(open(ref))
        k = M['meta']['headline_protocol']
        v = M[k]['models']['lgbm_full']
        print(f'Reminder: in-sample validation. Generalisation ({M[k]["label"]}): '
              f'R² {v["r2"]:.2f} [{v["r2_ci95"][0]:.2f}, {v["r2_ci95"][1]:.2f}] / '
              f'MAE {v["mae"]:.2f} dB.')
    else:
        print('Reminder: in-sample validation. Run scripts/04_evaluate_models.py '
              'for the generalisation figure.')
    return s


if __name__ == '__main__':
    main()

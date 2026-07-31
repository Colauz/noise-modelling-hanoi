"""Validation de la simulation : la carte reproduit-elle nos mesures de terrain ?

Phase 4 du projet demande de « calibrer le modèle pour reproduire les mesures observées ».
Ce script confronte, à l'emplacement exact de chacune de nos 363 mesures et à l'heure
où elle a été prise, le niveau prédit par la grille exportée vers GAMA au niveau
réellement relevé sur le terrain.

LIMITE À GARDER EN TÊTE - c'est une validation *en échantillon* : le modèle qui produit
la grille a été entraîné sur ces mêmes mesures. Les chiffres ci-dessous mesurent donc la
fidélité de la chaîne (modèle -> grille 40 m -> GAMA), pas la capacité de généralisation.
Le chiffre honnête de généralisation reste celui de la validation croisée spatiale du
notebook 08 : R² 0.45 / r 0.69 / MAE 4.2 dB, où le modèle prédit des lieux jamais vus.

Sorties : outputs/hanoi/validation_simulation.png + outputs/hanoi/validation_simulation.csv
Usage   : python3 scripts/validate_simulation.py
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEASURES = os.path.join(ROOT, 'data', 'raw', 'hanoi', 'measurements.csv')
GRID = os.path.join(ROOT, 'outputs', 'gama_inputs', 'noise_points.shp')
OUT_PNG = os.path.join(ROOT, 'outputs', 'hanoi', 'validation_simulation.png')
OUT_CSV = os.path.join(ROOT, 'outputs', 'hanoi', 'validation_simulation.csv')
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
    ax.set_xlabel('Mesure terrain (dB)'); ax.set_ylabel('Simulation (dB)')
    ax.set_title(f'Simulé vs mesuré  (r {s["r"]:.2f}, bandes ±5 dB)', fontsize=10)
    ax.legend(fontsize=8); ax.grid(alpha=.3)

    ax = axes[1]
    ax.hist(j.error, bins=np.arange(-20, 21, 2), color='#2471a3', edgecolor='white')
    ax.axvline(0, color='#333', lw=1.2)
    ax.axvline(s['bias'], color='#c0392b', lw=1.5, ls='--',
               label=f'biais {s["bias"]:+.1f} dB')
    ax.set_xlabel('Erreur simulation − mesure (dB)'); ax.set_ylabel('Nombre de points')
    ax.set_title('Distribution des erreurs', fontsize=10)
    ax.legend(fontsize=8); ax.grid(alpha=.3)

    ax = axes[2]
    per = pd.cut(j.hour, [4, 8, 12, 16, 22], labels=['5-8h', '9-12h', '13-16h', '17-21h'])
    grp = j.groupby(per, observed=True)['error']
    labels = list(grp.groups.keys())
    ax.boxplot([grp.get_group(k) for k in labels], tick_labels=labels)
    ax.axhline(0, color='#333', lw=1.2)
    ax.set_ylabel('Erreur (dB)')
    ax.set_title('Erreur par période de la journée', fontsize=10)
    ax.grid(alpha=.3)

    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=130, bbox_inches='tight')
    plt.close(fig)


def main():
    j = build()
    s = stats(j)
    j[['site', 'hour', 'noise_dB', 'sim_dB', 'error', 'cell_dist_m']].to_csv(OUT_CSV, index=False)
    figure(j, s)

    print(f'{s["n"]} mesures confrontées à la grille '
          f'(distance médiane au centre de cellule : {s["cell_dist"]:.0f} m)')
    print(f'  biais {s["bias"]:+.2f} dB · MAE {s["mae"]:.2f} dB · RMSE {s["rmse"]:.2f} dB')
    print(f'  r {s["r"]:.3f} · R² {s["r2"]:.3f}')
    print(f'  dans ±3 dB : {s["within3"]:.0f} %   dans ±5 dB : {s["within5"]:.0f} %')
    print('\npar site :')
    for site, g in j.groupby('site'):
        print(f'  {site:16} n={len(g):3}  biais {g.error.mean():+5.2f}  '
              f'MAE {g.error.abs().mean():4.2f}  r {g.sim_dB.corr(g.noise_dB):.2f}')
    print(f'\nOK -> {OUT_PNG}')
    print('Rappel : validation en échantillon. Généralisation honnête (notebook 08, '
          'CV spatiale) : R² 0.45 / r 0.69 / MAE 4.2 dB.')
    return s


if __name__ == '__main__':
    main()

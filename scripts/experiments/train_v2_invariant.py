"""
v2 - A density feature invariant across cities (built area ratio).

STATUS: not runnable as it stands. It expects data/processed/{uganda,barcelona}/*,
which is not in the repository. See docs/handover.md, debt 3.

v1 diagnosis: the Uganda->Barcelona transfer failed (r about 0) partly because
"buildings per km2" depends on the OSM mapping convention (Kampala = small
individual buildings, Barcelona = whole blocks).

v2:
  - built_area_ratio: built surface / area of the R=300 m disc - invariant
    (fast approximation: sum of the areas of buildings whose centroid falls in R)
  - Uganda v2 retraining (check that the v1 level is preserved: R2 0.639)
  - retest of the transfer to Barcelona - DIAGNOSTIC ONLY, Barcelona is never used
    for training (different instruments and quantities: fixed class 1 sensors /
    4-month LAeq against smartphones / instantaneous levels)

NOTE, August 2026: the plan described below - "pretrained on Uganda plus calibration
on our field measurements" - was tested and abandoned. Cross-city transfer scores
R2 < 0 on Hanoi even with these invariant features, and the delivered model is
trained directly on the Hanoi measurements. See docs/negative-results.md.

Outputs:
  data/processed/uganda/uganda_morphology_v2.parquet
  data/processed/barcelona/barcelona_morphology_v2.parquet
  models/surrogate_lgbm_v2_uganda.txt  (LightGBM booster, portable text format)

Usage: python3 scripts/experiments/train_v2_invariant.py
"""
import time
import warnings

import geopandas as gpd
import joblib
import lightgbm as lgb
import numpy as np
import osmnx as ox
import pandas as pd
from scipy.stats import pearsonr
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupShuffleSplit, train_test_split

warnings.filterwarnings('ignore')
R = 300
AREA_M2 = np.pi * R ** 2
FEATURES = ['built_area_ratio', 'road_density_km_km2', 'intersection_count',
            'dist_road_m', 'hour', 'is_weekend']
t0 = time.time()


def log(msg):
    print(f'[{time.time() - t0:6.0f}s] {msg}', flush=True)


def morphology_v2(points_df, bpath, gpath, crs_utm):
    """Invariant features: built area ratio + road network."""
    buildings = gpd.read_file(bpath).to_crs(crs_utm)
    buildings['area_m2'] = buildings.geometry.area
    buildings = buildings.set_geometry(buildings.geometry.centroid)

    G = ox.load_graphml(gpath)
    nodes, edges = ox.graph_to_gdfs(G)
    edg = edges.to_crs(crs_utm).reset_index(drop=True)
    nod = nodes.to_crs(crs_utm).reset_index(drop=True)

    pts = gpd.GeoDataFrame(
        points_df.reset_index(drop=True).copy(),
        geometry=gpd.points_from_xy(points_df.longitude, points_df.latitude),
        crs='EPSG:4326').to_crs(crs_utm)
    buf = gpd.GeoDataFrame({'pt_id': range(len(pts))},
                           geometry=pts.geometry.buffer(R), crs=crs_utm)

    # Built area ratio (sum of the areas of buildings whose centroid falls in R)
    jb = gpd.sjoin(buildings[['geometry', 'area_m2']], buf, predicate='within')
    area_sum = jb.groupby('pt_id')['area_m2'].sum()
    pts['built_area_ratio'] = [min(area_sum.get(i, 0) / AREA_M2, 1.0)
                               for i in range(len(pts))]

    jr = gpd.sjoin(edg[['geometry']], buf, predicate='intersects')
    rl = jr.groupby('pt_id').apply(lambda g: g.geometry.length.sum())
    pts['road_density_km_km2'] = [(rl.get(i, 0) / 1000) / (AREA_M2 / 1e6)
                                  for i in range(len(pts))]

    jn = gpd.sjoin(nod[['geometry']], buf, predicate='within').groupby('pt_id').size()
    pts['intersection_count'] = [jn.get(i, 0) for i in range(len(pts))]

    near = gpd.sjoin_nearest(pts[['geometry']], edg[['geometry']], distance_col='dist_road_m')
    pts['dist_road_m'] = near.groupby(near.index)['dist_road_m'].min()
    return pd.DataFrame(pts.drop(columns='geometry'))


# ---------- 1. Uganda : morphologie v2 ----------
df_ug = pd.read_csv('data/processed/uganda/sunbird_clean_large.csv')
df_ug['timestamp'] = pd.to_datetime(df_ug['timestamp'], format='ISO8601')
df_ug['hour'] = df_ug['timestamp'].dt.hour
df_ug['is_weekend'] = df_ug['timestamp'].dt.dayofweek.isin([5, 6]).astype(int)

feats = []
for region in df_ug['region'].unique():
    sub = df_ug[df_ug['region'] == region]
    log(f'Uganda/{region} : morphologie v2 sur {len(sub)} points...')
    feats.append(morphology_v2(
        sub, f'data/processed/{region.lower()}_buildings.gpkg',
        f'data/processed/{region.lower()}_roads.graphml', 'EPSG:32636'))
ug = pd.concat(feats, ignore_index=True)
ug.to_parquet('data/processed/uganda/uganda_morphology_v2.parquet', index=False)
log(f'Uganda v2 : {len(ug)} points, built_area_ratio moyen = {ug.built_area_ratio.mean():.3f}')

# ---------- 2. Barcelone : morphologie v2 ----------
bcn_cells = pd.read_parquet('data/processed/barcelona/barcelona_test_set.parquet')
sensors = bcn_cells[['Id_Instal', 'latitude', 'longitude']].drop_duplicates('Id_Instal')
log(f'Barcelone : morphologie v2 sur {len(sensors)} capteurs...')
m2 = morphology_v2(sensors, 'data/processed/barcelona/barcelona_buildings.gpkg',
                   'data/processed/barcelona/barcelona_roads.graphml', 'EPSG:32631')
bcn = bcn_cells.drop(columns=[c for c in ['building_density_km2', 'road_density_km_km2',
                                          'intersection_count', 'dist_road_m']
                              if c in bcn_cells.columns]) \
               .merge(m2[['Id_Instal', 'built_area_ratio', 'road_density_km_km2',
                          'intersection_count', 'dist_road_m']], on='Id_Instal')
bcn.to_parquet('data/processed/barcelona/barcelona_morphology_v2.parquet', index=False)
log(f'Barcelone v2 : {len(bcn)} cellules, built_area_ratio moyen = {bcn.built_area_ratio.mean():.3f}')
log(f'Comparaison domaines — built_area_ratio Uganda [{ug.built_area_ratio.quantile(0.05):.2f}-'
    f'{ug.built_area_ratio.quantile(0.95):.2f}] vs Barcelone [{bcn.built_area_ratio.quantile(0.05):.2f}-'
    f'{bcn.built_area_ratio.quantile(0.95):.2f}]')

# ---------- 3. Uganda v2 model ----------
Xu, yu = ug[FEATURES], ug['noise_measurement']
Xu_tr, Xu_te, yu_tr, yu_te = train_test_split(Xu, yu, test_size=0.2, random_state=42)
mu = lgb.LGBMRegressor(n_estimators=2000, learning_rate=0.05, num_leaves=63,
                       subsample=0.8, random_state=42, verbose=-1)
mu.fit(Xu_tr, yu_tr, eval_set=[(Xu_te, yu_te)],
       callbacks=[lgb.early_stopping(100, verbose=False)])
pu = mu.predict(Xu_te)
log('=== UGANDA v2 (feature invariante) ===')
log(f'MAE = {mean_absolute_error(yu_te, pu):.2f} dB   R² = {r2_score(yu_te, pu):.3f}   '
    f'r = {pearsonr(yu_te, pu)[0]:.3f}')
log('(v1 reference: MAE 5.17, R2 0.639, r 0.800)')
# Booster texte : format portable, independant de la version de LightGBM et de
# sklearn. Le pickle ne se rechargeait qu'avec les versions exactes d'origine.
mu.booster_.save_model('models/surrogate_lgbm_v2_uganda.txt')

# ---------- 4. Transfer diagnostic to Barcelona (never used for training) ----------
Xb, yb = bcn[FEATURES], bcn['LAeq']
pb = mu.predict(Xb)
log('=== DIAGNOSTIC TRANSFERT v2 Uganda -> Barcelone (brut) ===')
log(f'MAE = {mean_absolute_error(yb, pb):.2f} dB   r = {pearsonr(yb, pb)[0]:.3f}   '
    f'biais = {(yb - pb).mean():+.2f} dB')
log('(v1 : MAE 19.55, r -0.001, biais +19.27)')

gss = GroupShuffleSplit(n_splits=1, train_size=0.3, random_state=42)
cal, ev = next(gss.split(Xb, yb, groups=bcn['Id_Instal']))
off = (yb.iloc[cal] - pb[cal]).mean()
log('=== v2 + OFFSET TRANSFER DIAGNOSTIC (the Hanoi protocol) ===')
log(f'offset = {off:+.2f} dB   MAE = {mean_absolute_error(yb.iloc[ev], pb[ev] + off):.2f} dB   '
    f'R² = {r2_score(yb.iloc[ev], pb[ev] + off):.3f}   '
    f'r = {pearsonr(yb.iloc[ev], pb[ev] + off)[0]:.3f}')
log('(v1 : MAE 8.72, R² -2.369, r -0.015)')
log('Done.')

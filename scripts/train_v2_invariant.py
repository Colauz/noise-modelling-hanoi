"""
v2 — Feature de densité invariante entre villes (ratio de surface bâtie).

Diagnostic v1 : le transfert Uganda→Barcelone échouait (r≈0) en partie parce que
le "nombre de bâtiments/km²" dépend de la convention de cartographie OSM
(Kampala = petits bâtiments individuels, Barcelone = îlots entiers).

v2 :
  - built_area_ratio : surface bâtie / surface du disque R=300m — invariant
    (approximation rapide : somme des aires des bâtiments à centroïde dans R)
  - ré-entraînement Uganda v2 (vérifier qu'on garde le niveau v1 : R² 0.639)
  - re-test du transfert vers Barcelone — DIAGNOSTIC SEULEMENT, Barcelone ne sert
    jamais à l'entraînement (instruments et grandeurs différents : capteurs fixes
    classe 1 / LAeq 4 mois vs smartphones / niveaux instantanés)

Le modèle pour Hanoï reste : pré-entraîné Uganda (même instrument, même
échantillonnage que notre collecte) + calibration sur nos mesures terrain.

Sorties :
  data/processed/uganda_morphology_v2.parquet
  data/processed/barcelona_morphology_v2.parquet
  outputs/models/surrogate_lgbm_v2_uganda.pkl

Usage : python3 scripts/train_v2_invariant.py
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
    """Features invariantes : ratio de surface bâtie + réseau routier."""
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

    # Ratio de surface bâtie (somme des aires des bâtiments à centroïde dans R)
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
df_ug = pd.read_csv('data/processed/sunbird_clean_large.csv')
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
ug.to_parquet('data/processed/uganda_morphology_v2.parquet', index=False)
log(f'Uganda v2 : {len(ug)} points, built_area_ratio moyen = {ug.built_area_ratio.mean():.3f}')

# ---------- 2. Barcelone : morphologie v2 ----------
bcn_cells = pd.read_parquet('data/processed/barcelona_test_set.parquet')
sensors = bcn_cells[['Id_Instal', 'latitude', 'longitude']].drop_duplicates('Id_Instal')
log(f'Barcelone : morphologie v2 sur {len(sensors)} capteurs...')
m2 = morphology_v2(sensors, 'data/processed/barcelona_buildings.gpkg',
                   'data/processed/barcelona_roads.graphml', 'EPSG:32631')
bcn = bcn_cells.drop(columns=[c for c in ['building_density_km2', 'road_density_km_km2',
                                          'intersection_count', 'dist_road_m']
                              if c in bcn_cells.columns]) \
               .merge(m2[['Id_Instal', 'built_area_ratio', 'road_density_km_km2',
                          'intersection_count', 'dist_road_m']], on='Id_Instal')
bcn.to_parquet('data/processed/barcelona_morphology_v2.parquet', index=False)
log(f'Barcelone v2 : {len(bcn)} cellules, built_area_ratio moyen = {bcn.built_area_ratio.mean():.3f}')
log(f'Comparaison domaines — built_area_ratio Uganda [{ug.built_area_ratio.quantile(0.05):.2f}-'
    f'{ug.built_area_ratio.quantile(0.95):.2f}] vs Barcelone [{bcn.built_area_ratio.quantile(0.05):.2f}-'
    f'{bcn.built_area_ratio.quantile(0.95):.2f}]')

# ---------- 3. Modèle Uganda v2 ----------
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
log('(référence v1 : MAE 5.17, R² 0.639, r 0.800)')
joblib.dump(mu, 'outputs/models/surrogate_lgbm_v2_uganda.pkl')

# ---------- 4. Diagnostic transfert vers Barcelone (jamais en entraînement) ----------
Xb, yb = bcn[FEATURES], bcn['LAeq']
pb = mu.predict(Xb)
log('=== DIAGNOSTIC TRANSFERT v2 Uganda -> Barcelone (brut) ===')
log(f'MAE = {mean_absolute_error(yb, pb):.2f} dB   r = {pearsonr(yb, pb)[0]:.3f}   '
    f'biais = {(yb - pb).mean():+.2f} dB')
log('(v1 : MAE 19.55, r -0.001, biais +19.27)')

gss = GroupShuffleSplit(n_splits=1, train_size=0.3, random_state=42)
cal, ev = next(gss.split(Xb, yb, groups=bcn['Id_Instal']))
off = (yb.iloc[cal] - pb[cal]).mean()
log('=== DIAGNOSTIC TRANSFERT v2 + OFFSET (protocole Hanoï) ===')
log(f'offset = {off:+.2f} dB   MAE = {mean_absolute_error(yb.iloc[ev], pb[ev] + off):.2f} dB   '
    f'R² = {r2_score(yb.iloc[ev], pb[ev] + off):.3f}   '
    f'r = {pearsonr(yb.iloc[ev], pb[ev] + off)[0]:.3f}')
log('(v1 : MAE 8.72, R² -2.369, r -0.015)')
log('Terminé.')

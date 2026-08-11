"""
Train the surrogate model on Sunbird's `large` config (61K points).

STATUS: not runnable as it stands. It expects data/processed/uganda/*, which is not
in the repository; the Sunbird chain does not run on a fresh machine. See
docs/handover.md, debt 3.

Optimisations over the notebooks (small config):
- downloads only the metadata columns of the parquet files (no audio, ~3 GB saved)
- distance to road via vectorised sjoin_nearest (the loop in notebook 04 would be
  unusable on 61K points)
- reuses the notebooks' OSM caches; extends them if the `large` extent exceeds them

Outputs:
- data/processed/uganda/sunbird_clean_large.csv
- data/processed/uganda/sunbird_morphology_large.parquet
- models/surrogate_lgbm_large.txt  (LightGBM booster, portable text format)

Usage: python3 scripts/experiments/train_uganda_large.py   (from the repository root)
"""
import os
import time
import warnings

import geopandas as gpd
import joblib
import lightgbm as lgb
import numpy as np
import osmnx as ox
import pandas as pd
from dotenv import load_dotenv
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.model_selection import train_test_split

warnings.filterwarnings('ignore')
load_dotenv('.env')

R = 300
AREA_KM2 = np.pi * (R / 1000) ** 2
CRS_UTM = 'EPSG:32636'  # UTM 36N, valable Kampala + Entebbe
META_COLS = ['noise_measurement', 'latitude', 'longitude', 'altitude',
             'accuracy', 'class', 'class_id', 'region', 'timestamp', 'submitter_id']
FEATURES = ['building_density_km2', 'road_density_km_km2', 'intersection_count',
            'dist_road_m', 'hour', 'is_weekend']

t0 = time.time()


def log(msg):
    print(f'[{time.time() - t0:6.0f}s] {msg}', flush=True)


# ---------- 1. Métadonnées large (colonnes sélectionnées, sans audio) ----------
log('Lecture des parquet large (métadonnées seulement)...')
shards = [f'hf://datasets/Sunbird/urban-noise-uganda-61k/large/train-{i:05d}-of-00006.parquet'
          for i in range(6)]
storage = {'token': os.environ['HF_TOKEN']}
df = pd.concat(
    [pd.read_parquet(s, columns=META_COLS, storage_options=storage) for s in shards],
    ignore_index=True)
log(f'{len(df)} lignes chargées')

# ---------- 2. Nettoyage (mêmes règles que le notebook 02) ----------
df = df.dropna(subset=['noise_measurement', 'latitude', 'longitude', 'timestamp'])
df = df.drop_duplicates(subset=['submitter_id', 'timestamp'])
df = df[df['accuracy'] < 50]
df = df[(df['noise_measurement'] >= 20) & (df['noise_measurement'] <= 120)]
df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601')
df['hour'] = df['timestamp'].dt.hour
df['is_weekend'] = df['timestamp'].dt.dayofweek.isin([5, 6]).astype(int)
df = df.reset_index(drop=True)
df.to_csv('data/processed/uganda/sunbird_clean_large.csv', index=False)
log(f'{len(df)} lignes après nettoyage')

# ---------- 3. Caches OSM (étendus si l'emprise large dépasse celle du small) ----------
MARGIN = 0.01
osm = {}
for region, g in df.groupby('region'):
    bbox = (g.longitude.min() - MARGIN, g.latitude.min() - MARGIN,
            g.longitude.max() + MARGIN, g.latitude.max() + MARGIN)
    bpath = f'data/processed/{region.lower()}_buildings.gpkg'
    gpath = f'data/processed/{region.lower()}_roads.graphml'

    def covers(path_graph):
        """Le cache couvre-t-il la bbox large ?"""
        if not (os.path.exists(bpath) and os.path.exists(path_graph)):
            return False
        b = gpd.read_file(bpath, rows=1)  # juste pour les bounds du fichier
        full = gpd.read_file(bpath, columns=['geometry'])
        w, s, e, n = full.total_bounds
        return w <= bbox[0] and s <= bbox[1] and e >= bbox[2] and n >= bbox[3]

    if not covers(gpath):
        log(f'{region} : cache absent ou trop petit, téléchargement OSM (plusieurs minutes)...')
        ox.settings.timeout = 600
        b = ox.features_from_bbox(bbox, tags={'building': True})
        b = b[b.geometry.geom_type.isin(['Polygon', 'MultiPolygon'])]
        b[['geometry']].to_file(bpath, driver='GPKG')
        G = ox.graph_from_bbox(bbox, network_type='drive')
        ox.save_graphml(G, gpath)

    buildings = gpd.read_file(bpath)
    G = ox.load_graphml(gpath)
    nodes, edges = ox.graph_to_gdfs(G)
    osm[region] = (buildings, edges, nodes)
    log(f'{region} : {len(buildings)} bâtiments, {len(edges)} segments')

# ---------- 4. Morphologie (vectorisé, sjoin_nearest pour la distance) ----------
feats = []
for region, (buildings, edges, nodes) in osm.items():
    sub = df[df['region'] == region].reset_index(drop=True)
    log(f'{region} : morphologie sur {len(sub)} points...')

    pts = gpd.GeoDataFrame(
        sub, geometry=gpd.points_from_xy(sub.longitude, sub.latitude),
        crs='EPSG:4326').to_crs(CRS_UTM)
    bld = buildings.to_crs(CRS_UTM)
    bld = bld.set_geometry(bld.geometry.centroid)
    edg = edges.to_crs(CRS_UTM).reset_index(drop=True)
    nod = nodes.to_crs(CRS_UTM).reset_index(drop=True)

    buf = gpd.GeoDataFrame({'pt_id': range(len(pts))},
                           geometry=pts.geometry.buffer(R), crs=CRS_UTM)

    jb = gpd.sjoin(bld[['geometry']], buf, predicate='within').groupby('pt_id').size()
    pts['building_density_km2'] = [jb.get(i, 0) / AREA_KM2 for i in range(len(pts))]

    jr = gpd.sjoin(edg[['geometry']], buf, predicate='intersects')
    rl = jr.groupby('pt_id').apply(lambda g: g.geometry.length.sum())
    pts['road_density_km_km2'] = [(rl.get(i, 0) / 1000) / AREA_KM2 for i in range(len(pts))]

    jn = gpd.sjoin(nod[['geometry']], buf, predicate='within').groupby('pt_id').size()
    pts['intersection_count'] = [jn.get(i, 0) for i in range(len(pts))]

    near = gpd.sjoin_nearest(pts[['geometry']], edg[['geometry']],
                             distance_col='dist_road_m')
    pts['dist_road_m'] = near.groupby(near.index)['dist_road_m'].min()

    feats.append(pd.DataFrame(pts.drop(columns='geometry')))

feat = pd.concat(feats, ignore_index=True)
feat.to_parquet('data/processed/uganda/sunbird_morphology_large.parquet', index=False)
log(f'Morphologie sauvegardée ({len(feat)} points)')

# ---------- 5. Entraînement ----------
X = feat[FEATURES]
y = feat['noise_measurement']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
log(f'Entraînement LightGBM : train={len(X_train)}, test={len(X_test)}')

model = lgb.LGBMRegressor(
    n_estimators=2000, learning_rate=0.05, num_leaves=63,
    min_child_samples=20, subsample=0.8, random_state=42, verbose=-1)
model.fit(X_train, y_train, eval_set=[(X_test, y_test)],
          callbacks=[lgb.early_stopping(100, verbose=False)])

y_pred = model.predict(X_test)
mae = mean_absolute_error(y_test, y_pred)
rmse = root_mean_squared_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

log('=== RÉSULTATS LARGE ===')
log(f'MAE  : {mae:.2f} dB')
log(f'RMSE : {rmse:.2f} dB')
log(f'R²   : {r2:.3f}')

# Booster texte : format portable, independant de la version de LightGBM et de
# sklearn. Le pickle ne se rechargeait qu'avec les versions exactes d'origine.
model.booster_.save_model('models/surrogate_lgbm_large.txt')
log('Modèle sauvegardé : outputs/models/surrogate_lgbm_large.pkl')

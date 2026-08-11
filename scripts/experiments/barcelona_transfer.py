"""Uganda -> Barcelona transfer experiments. CLOSED DEAD END -- NOT RUNNABLE.

STATUS
    Not runnable as it stands. It is kept because the reasoning it encodes is
    reusable, not because it works.

MISSING INPUT
    The Barcelona open data it expects is not in the repository and never was:
        data/raw/barcelona/XarxaSoroll_EquipsMonitor_Instal.csv
        data/raw/barcelona/*_XarxaSoroll_EqMonitor_Dades_1Min.zip   (1+ month)
    Source: Barcelona Open Data, "Xarxa de Soroll" sensor network. Re-downloading
    it is the first step for anyone reviving this script.

WHAT WAS ATTEMPTED
    A dress rehearsal of the Kampala -> Hanoi transfer, on a city where ground
    truth exists (municipal sensor network, 4 months of minute LAeq):
      A. Raw transfer      -- the Uganda model applied as is to Barcelona
      B. Transfer + offset -- calibrate on 30% of sensors, evaluate on the other
                              70%, the protocol then planned for Hanoi
      C. Direct benchmark  -- LightGBM trained on Barcelona, split by sensor

WHY IT WAS ABANDONED
    Cross-city transfer failed on its own terms: a morphology -> noise model
    pretrained on Uganda scores R2 < 0 on Hanoi even with convention-invariant
    features. Barcelona would have measured how far a transfer can be rescued by
    an offset; once the Hanoi answer came back negative, and the project pivoted
    to a methodological study on the data in hand, the question stopped being on
    the critical path. See docs/negative-results.md.

WHAT IT WOULD TAKE TO REVIVE IT
    1. Re-download the two Barcelona datasets into data/raw/barcelona/.
    2. Repoint its paths at noise_hanoi.config like the numbered scripts.
    3. Load the Uganda model from the text booster, not the removed pickle.
    4. Decide what the answer would change. If cross-city transfer stays out of
       scope, this file is documentation, not code.
"""
import glob
import os
import time
import warnings
import zipfile

import geopandas as gpd
import joblib
import lightgbm as lgb
import numpy as np
import osmnx as ox
import pandas as pd
from scipy.stats import pearsonr
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupShuffleSplit

warnings.filterwarnings('ignore')

R = 300
AREA_KM2 = np.pi * (R / 1000) ** 2
CRS_BCN = 'EPSG:32631'  # UTM 31N
FEATURES = ['building_density_km2', 'road_density_km_km2', 'intersection_count',
            'dist_road_m', 'hour', 'is_weekend']
t0 = time.time()


def log(msg):
    print(f'[{time.time() - t0:6.0f}s] {msg}', flush=True)


def energetic_mean(db_series):
    """Energy mean of levels in dB (not arithmetic)."""
    return 10 * np.log10(np.mean(10 ** (db_series / 10)))


# ---------- 1. Measurements: LAeq aggregated by sensor x hour x day type ----------
zips = sorted(glob.glob('data/raw/barcelona/*Dades_1Min.zip'))
log(f'{len(zips)} months of measurements: {[os.path.basename(z) for z in zips]}')

aggs = []
for z in zips:
    with zipfile.ZipFile(z) as zf:
        name = zf.namelist()[0]
        with zf.open(name) as f:
            m = pd.read_csv(f, usecols=['Timestamp_local', 'Id_Instal', 'Nivell_LAeq_1min'])
    # utc=True : les offsets locaux varient (CET/CEST), pandas refuse le .dt sinon
    m['ts'] = pd.to_datetime(m['Timestamp_local'], format='ISO8601', utc=True).dt.tz_convert('Europe/Madrid')
    m['hour'] = m['ts'].dt.hour
    m['is_weekend'] = (m['ts'].dt.dayofweek >= 5).astype(int)
    # mean energy per sensor x hour x weekend for this month
    m['energy'] = 10 ** (m['Nivell_LAeq_1min'] / 10)
    a = (m.groupby(['Id_Instal', 'hour', 'is_weekend'])['energy']
           .agg(['mean', 'count']).reset_index())
    aggs.append(a)
    log(f'{os.path.basename(z)} : {len(m)} lignes 1-min, {m.Id_Instal.nunique()} capteurs')

# combine the months (energy mean weighted by the number of minutes)
allm = pd.concat(aggs)
allm['energy_sum'] = allm['mean'] * allm['count']
agg = (allm.groupby(['Id_Instal', 'hour', 'is_weekend'])
            .agg(energy_sum=('energy_sum', 'sum'), n=('count', 'sum')).reset_index())
agg['LAeq'] = 10 * np.log10(agg['energy_sum'] / agg['n'])
agg = agg[agg['n'] >= 60]  # at least 1 h of data per cell
log(f'Aggregate: {len(agg)} sensor x hour x weekend cells, {agg.Id_Instal.nunique()} sensors')

# ---------- 2. Jointure avec les positions ----------
inst = pd.read_csv('data/raw/barcelona/XarxaSoroll_EquipsMonitor_Instal.csv')
inst = inst.drop_duplicates(subset='Id_Instal')[['Id_Instal', 'Latitud', 'Longitud']]
df = agg.merge(inst, on='Id_Instal', how='inner').rename(
    columns={'Latitud': 'latitude', 'Longitud': 'longitude'})
log(f'After joining positions: {len(df)} cells, {df.Id_Instal.nunique()} located sensors')

# ---------- 3. Morphologie OSM de Barcelone (cache local) ----------
MARGIN = 0.01
bbox = (df.longitude.min() - MARGIN, df.latitude.min() - MARGIN,
        df.longitude.max() + MARGIN, df.latitude.max() + MARGIN)
bpath = 'data/processed/barcelona/barcelona_buildings.gpkg'
gpath = 'data/processed/barcelona/barcelona_roads.graphml'
ox.settings.timeout = 600

if not os.path.exists(bpath):
    log('Downloading Barcelona OSM buildings (several minutes)...')
    b = ox.features_from_bbox(bbox, tags={'building': True})
    b = b[b.geometry.geom_type.isin(['Polygon', 'MultiPolygon'])]
    b[['geometry']].to_file(bpath, driver='GPKG')
if not os.path.exists(gpath):
    log('Downloading Barcelona road network...')
    G = ox.graph_from_bbox(bbox, network_type='drive')
    ox.save_graphml(G, gpath)

buildings = gpd.read_file(bpath)
G = ox.load_graphml(gpath)
nodes, edges = ox.graph_to_gdfs(G)
log(f'Barcelona: {len(buildings)} buildings, {len(edges)} segments')

# features morphologie par CAPTEUR (positions uniques), puis re-jointure
sensors = df[['Id_Instal', 'latitude', 'longitude']].drop_duplicates('Id_Instal').reset_index(drop=True)
pts = gpd.GeoDataFrame(sensors, geometry=gpd.points_from_xy(
    sensors.longitude, sensors.latitude), crs='EPSG:4326').to_crs(CRS_BCN)
bld = buildings.to_crs(CRS_BCN)
bld = bld.set_geometry(bld.geometry.centroid)
edg = edges.to_crs(CRS_BCN).reset_index(drop=True)
nod = nodes.to_crs(CRS_BCN).reset_index(drop=True)

buf = gpd.GeoDataFrame({'pt_id': range(len(pts))},
                       geometry=pts.geometry.buffer(R), crs=CRS_BCN)
jb = gpd.sjoin(bld[['geometry']], buf, predicate='within').groupby('pt_id').size()
pts['building_density_km2'] = [jb.get(i, 0) / AREA_KM2 for i in range(len(pts))]
jr = gpd.sjoin(edg[['geometry']], buf, predicate='intersects')
rl = jr.groupby('pt_id').apply(lambda g: g.geometry.length.sum())
pts['road_density_km_km2'] = [(rl.get(i, 0) / 1000) / AREA_KM2 for i in range(len(pts))]
jn = gpd.sjoin(nod[['geometry']], buf, predicate='within').groupby('pt_id').size()
pts['intersection_count'] = [jn.get(i, 0) for i in range(len(pts))]
near = gpd.sjoin_nearest(pts[['geometry']], edg[['geometry']], distance_col='dist_road_m')
pts['dist_road_m'] = near.groupby(near.index)['dist_road_m'].min()

morph = pd.DataFrame(pts.drop(columns='geometry'))
df = df.merge(morph[['Id_Instal', 'building_density_km2', 'road_density_km_km2',
                     'intersection_count', 'dist_road_m']], on='Id_Instal')
df.to_parquet('data/processed/barcelona/barcelona_test_set.parquet', index=False)
log(f'Test set Barcelone : {len(df)} lignes')

# ---------- 4. Experiments ----------
model = joblib.load('outputs/models/surrogate_lgbm_large.pkl')
X = df[FEATURES]
y = df['LAeq']
pred_raw = model.predict(X)

log('=== A. TRANSFERT BRUT (Uganda -> Barcelone) ===')
log(f'MAE  : {mean_absolute_error(y, pred_raw):.2f} dB')
log(f'R²   : {r2_score(y, pred_raw):.3f}')
log(f'r    : {pearsonr(y, pred_raw)[0]:.3f}')
log(f'Mean bias (measured - predicted): {(y - pred_raw).mean():+.2f} dB')

# B: offset calibrated on 30% of sensors, evaluated on the remaining 70%
gss = GroupShuffleSplit(n_splits=1, train_size=0.3, random_state=42)
cal_idx, eval_idx = next(gss.split(X, y, groups=df['Id_Instal']))
offset = (y.iloc[cal_idx] - pred_raw[cal_idx]).mean()
pred_off = pred_raw[eval_idx] + offset
y_eval = y.iloc[eval_idx]

log('=== B. TRANSFER + OFFSET (the protocol then planned for Hanoi) ===')
log(f'Offset calibrated on {df.iloc[cal_idx].Id_Instal.nunique()} sensors: {offset:+.2f} dB')
log(f'MAE  : {mean_absolute_error(y_eval, pred_off):.2f} dB '
    f'(evaluated on {df.iloc[eval_idx].Id_Instal.nunique()} sensors never seen)')
log(f'R²   : {r2_score(y_eval, pred_off):.3f}')
log(f'r    : {pearsonr(y_eval, pred_off)[0]:.3f}')

# C: direct training on Barcelona, split BY SENSOR (no spatial leakage)
gss2 = GroupShuffleSplit(n_splits=1, train_size=0.7, random_state=42)
tr_idx, te_idx = next(gss2.split(X, y, groups=df['Id_Instal']))
mc = lgb.LGBMRegressor(n_estimators=1000, learning_rate=0.05, num_leaves=31,
                       random_state=42, verbose=-1)
mc.fit(X.iloc[tr_idx], y.iloc[tr_idx])
pc = mc.predict(X.iloc[te_idx])

log('=== C. DIRECT BARCELONA TRAINING (benchmark against the cited R2=0.61, r=0.66) ===')
log(f'MAE  : {mean_absolute_error(y.iloc[te_idx], pc):.2f} dB')
log(f'R²   : {r2_score(y.iloc[te_idx], pc):.3f}')
log(f'r    : {pearsonr(y.iloc[te_idx], pc)[0]:.3f}')
log('Done.')

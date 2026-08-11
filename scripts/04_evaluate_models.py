"""Honest evaluation of the Hanoi model: spatial-block CV + baselines + ablation.

WHY THIS SCRIPT EXISTS
----------------------
Notebook 08 grouped the cross-validation on `lat.round(3)/lon.round(3)`, i.e. cells of
~110 m. But the morphology features are aggregates over a disc of RADIUS 300 m: two
points 110 m apart share more than 85 % of their disc. Their feature vectors are
therefore near-identical and their levels strongly autocorrelated: in training, the
model saw near-twins of its test points. The R2 obtained was not out-of-sample
(Roberts et al. 2017, Ecography).

This script replaces that protocol with two defensible ones:

  1. BLOCK-CV      square blocks of BLOCK_M = 600 m (= 2 x buffer radius) in UTM 48N,
                   GroupKFold on the block identifier.
  2. BLOO          buffered leave-one-out: for each point, train on ALL points more
                   than BUFFER_M = 300 m away from it. This is the reference protocol,
                   stricter and with no split randomness.
  3. LOSO          leave-one-site-out: generalisation to an unseen urban typology.

And it adds what was missing: BASELINES and an ABLATION, evaluated on exactly the same
splits, to answer the question "is urban morphology actually good for anything?".

  global_mean       global mean                             (absolute floor)
  site_mean         mean per site                           (no fine spatial information)
  site_hour_mean    mean per (site, hour)                   <- THE baseline to beat
  dist_road         linear regression on log(dist_road)     (minimal physics)
  idw               inverse distance weighting              (pure interpolation)
  lgbm_time         LightGBM, hour + weekend ONLY           (ablation: no morphology)
  lgbm_morpho       LightGBM, morphology ONLY               (ablation: no time)
  lgbm_full         LightGBM, morphology + time             (the v1 model)

V2 (August 2026) - THREE MORE MODELS
------------------------------------
  lgbm_v2           LightGBM on the v2 features: distances SEPARATED by road class
                    (dist_highway / dist_residential) and a CYCLIC hour (sin/cos).
                    Isolates the contribution of feature engineering, architecture
                    unchanged.
  physical          Physical kernel alone: line source, 1/d decay, three positive
                    parameters. No morphological data at all.
  hybrid            The physical kernel carries the prediction and a LightGBM learns
                    only the RESIDUAL. This is the architecture recommended in the
                    conclusion of docs/negative-results.md.

WHICH MODEL IS DELIVERED IS DECIDED HERE, BY THE CODE. The best R2 under the reference
protocol among candidates fixed in advance is written to `meta.delivered_model`, and
07_export_gama_inputs.py reads the `apply_residual` flag. As of August 2026 the winner
is `physical`, and the residual is written but NOT applied: the elaborate architecture
wins the permissive split and loses both strict ones.

Every score carries a 95 % confidence interval bootstrapped BY BLOCK (not by point:
resampling correlated points would give an interval that is far too narrow).

OUTPUTS
-------
  models/metrics.json          consumed by scripts/10_build_report.py (no metric is
                               copied into the report by hand any more)
  models/model_comparison.md   table ready to paste into the manuscript
  models/surrogate_lgbm_hanoi_direct.txt   final model (all points), consumed by
                               scripts/07_export_gama_inputs.py

USAGE
-----
  python3 scripts/04_evaluate_models.py [--fast]

  --fast  skips the BLOO (the most expensive: one fit per point).

PREREQUISITES: data/processed/measurements.csv (scripts/01_prepare_field_data.py) and the
OSM caches data/interim/hanoi_sites_{buildings.gpkg,roads.graphml}. Feature construction
comes from noise_hanoi.features. The script says what to run if something is missing.
"""
import argparse
import json
import os
import sys
import warnings

warnings.filterwarnings('ignore')

import geopandas as gpd
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from noise_hanoi import config as cfg

ROOT = cfg.ROOT

MEASURES = cfg.MEASUREMENTS
PROC = cfg.INTERIM
OUT_JSON = cfg.METRICS_JSON
OUT_MD = cfg.MODEL_COMPARISON_MD
FINAL_MODEL = cfg.FINAL_MODEL
RESID_MODEL = cfg.RESID_MODEL
PHYS_JSON = cfg.PHYS_JSON

CRS_M = 'EPSG:32648'      # UTM 48N (metres)
R = 300                   # rayon des features de morphologie (m) - fixe le reste
BLOCK_M = 2 * R           # 600 m: a CV block must exceed the range of the predictors
BUFFER_M = R              # rayon d'exclusion du buffered leave-one-out
N_FOLDS = 5
N_BOOT = 2000
SEED = 0

MORPHO = ['built_area_ratio', 'road_density_km_km2', 'intersection_count', 'dist_road_m']
TIME = ['hour', 'is_weekend']
FEATURES = MORPHO + TIME

# --- v2 (August 2026): road classes split + cyclic hour --------------------------------
MORPHO2 = ['built_area_ratio', 'road_density_km_km2', 'intersection_count',
           'dist_highway_m', 'dist_residential_m']
TIME2 = ['hour_sin', 'hour_cos', 'is_weekend']
FEATURES2 = MORPHO2 + TIME2
# Residual features of the conservative variant: NO distance, it is already
# fully consumed by the physical kernel.
RESID_RESTRICTED = ['built_area_ratio', 'road_density_km_km2', 'intersection_count',
                    'hour_sin', 'hour_cos', 'is_weekend']

D0 = 5.0        # distance floor (m): avoids the 1/d singularity at the kerb

LGB_PARAMS = dict(n_estimators=300, learning_rate=0.05, num_leaves=15,
                  min_child_samples=10, random_state=SEED, verbose=-1)
# The residual model learns a bounded correction, not the full level: it needs less
# capacity, otherwise it relearns the noise the physics has already explained.
LGB_RESID = dict(LGB_PARAMS, n_estimators=200, num_leaves=7)


# -------------------------------------------------------------------------------- data
def load_points():
    """measurements.csv + morphology features + metric coordinates + spatial block."""
    if not os.path.exists(MEASURES):
        raise SystemExit(f'Manque {MEASURES}\n  -> python3 scripts/prepare_field_data.py')
    for f in ('hanoi_sites_buildings.gpkg', 'hanoi_sites_roads.graphml'):
        if not os.path.exists(os.path.join(PROC, f)):
            raise SystemExit(f'Manque {os.path.join(PROC, f)}\n'
                             '  -> run notebook 08 once (it downloads and caches the OSM extract)')

    from noise_hanoi import features as feat

    m = pd.read_csv(MEASURES, parse_dates=['timestamp'])
    m['hour'] = m.timestamp.dt.hour
    # CYCLIC hour: 23:00 and 00:00 must be neighbours in feature space
    m['hour_sin'] = np.sin(2 * np.pi * m.hour / 24.0)
    m['hour_cos'] = np.cos(2 * np.pi * m.hour / 24.0)
    m['is_weekend'] = m.timestamp.dt.dayofweek.isin([5, 6]).astype(int)
    m = m.dropna(subset=['noise_dB', 'latitude', 'longitude']).reset_index(drop=True)

    _, bld_c, nodes, edges = feat.load_osm()
    pts = gpd.GeoDataFrame(m, geometry=gpd.points_from_xy(m.longitude, m.latitude),
                           crs='EPSG:4326').to_crs(CRS_M)
    feats = feat.morphology(pts, bld_c, nodes, edges)

    df = pd.concat([m, feats], axis=1)
    df['x'] = pts.geometry.x.values
    df['y'] = pts.geometry.y.values
    # 600 m spatial block: the unit of both the CV split and the bootstrap
    df['block'] = (np.floor(df.x / BLOCK_M).astype(int).astype(str) + '_' +
                   np.floor(df.y / BLOCK_M).astype(int).astype(str))
    return df


# ------------------------------------------------------------------------------ models
# Convention: each model is a function fit_predict(train_df, test_df) -> np.ndarray.
# They receive the full DataFrame, so each one chooses the information it uses.
# None has access to test_df['noise_dB'].

def m_global_mean(tr, te):
    return np.full(len(te), tr.noise_dB.mean())


def m_site_mean(tr, te):
    mu = tr.groupby('site').noise_dB.mean()
    return te.site.map(mu).fillna(tr.noise_dB.mean()).values


def m_site_hour_mean(tr, te):
    """Table de correspondance (site, heure), repli sur la moyenne du site puis globale.
    Aucune variable spatiale fine : c'est le baseline que la morphologie doit battre."""
    g = tr.groupby(['site', 'hour']).noise_dB.mean()
    site_mu = tr.groupby('site').noise_dB.mean()
    idx = pd.MultiIndex.from_arrays([te.site, te.hour])
    p = pd.Series(g.reindex(idx).values, index=te.index)
    return p.fillna(te.site.map(site_mu)).fillna(tr.noise_dB.mean()).values


def m_dist_road(tr, te):
    """Linear regression of level on log10(distance to road). Minimal physics."""
    lx = np.log10(np.maximum(tr.dist_road_m.values, 1.0))
    a, b = np.polyfit(lx, tr.noise_dB.values, 1)
    return a * np.log10(np.maximum(te.dist_road_m.values, 1.0)) + b


def m_idw(tr, te, k=8, power=2.0):
    """Interpolation par distance inverse sur les k plus proches points d'apprentissage.
    Geostatistical baseline: what is gained over "looking at the neighbours"?"""
    tx, ty, tv = tr.x.values, tr.y.values, tr.noise_dB.values
    out = np.empty(len(te))
    for i, (px, py) in enumerate(zip(te.x.values, te.y.values)):
        d = np.hypot(tx - px, ty - py)
        sel = np.argsort(d)[:k]
        dd = np.maximum(d[sel], 1e-6)
        w = 1.0 / dd ** power
        out[i] = float(np.sum(w * tv[sel]) / np.sum(w))
    return out


def _lgbm(cols):
    def f(tr, te):
        mdl = lgb.LGBMRegressor(**LGB_PARAMS).fit(tr[cols], tr.noise_dB)
        return mdl.predict(te[cols])
    return f


# ------------------------------------------------------- physical kernel + hybrid (v2)
# EQUATION. A road is modelled as an incoherent LINE source: intensity
# falls as 1/d (not as 1/d^2, which holds for a point source). The energy received
# is the sum of the contributions of the two road classes and of a residual background:
#
#     E(x) = A_hw / max(d_hw, D0) + A_res / max(d_res, D0) + B
#     L(x) = 10 · log10( E(x) )
#
# Three parameters, all CONSTRAINED NON-NEGATIVE: a source cannot remove energy.
# A_hw and A_res are powers per unit length (major roads / minor streets),
# B the non-road background. This is the same family of equations as the standardised
# emission models, reduced to what our data can identify.
#
# FITTED IN DECIBELS, NOT IN ENERGY. Our levels span 47-88 dB, i.e. four
# orders of magnitude in energy: a least-squares fit in energy would be driven entirely
# by the loudest points. We therefore minimise the discrepancy in dB, which is also the
# metric the model is judged on.
def _phys_design(df):
    d_hw = np.maximum(df.dist_highway_m.values.astype(float), D0)
    d_res = np.maximum(df.dist_residential_m.values.astype(float), D0)
    return np.column_stack([1.0 / d_hw, 1.0 / d_res, np.ones(len(df))])


def fit_physical(tr):
    from scipy.optimize import least_squares
    X = _phys_design(tr)
    y = tr.noise_dB.values.astype(float)
    e_mean = float(np.mean(10 ** (y / 10.0)))
    # initialisation: half the mean level into the background, half shared between the
    # two road classes at their median distance.
    p0 = np.array([0.25 * e_mean * float(np.median(np.maximum(tr.dist_highway_m, D0))),
                   0.25 * e_mean * float(np.median(np.maximum(tr.dist_residential_m, D0))),
                   0.50 * e_mean])
    f = lambda p: 10 * np.log10(np.maximum(X @ p, 1e-9)) - y
    return least_squares(f, p0, bounds=(0, np.inf), max_nfev=2000).x


def predict_physical(p, te):
    return 10 * np.log10(np.maximum(_phys_design(te) @ p, 1e-9))


def m_physical(tr, te):
    """The physical kernel ALONE: three parameters, no morphological data."""
    return predict_physical(fit_physical(tr), te)


def m_hybrid_lowcap(tr, te):
    """Variante conservatrice de l'hybride, sur le compromis interpolation/extrapolation.

    Two differences from `m_hybrid`, both intended to stop the residual from
    relearning what the physics already explains:
      - the residual model does NOT SEE the distances (they are already consumed by the
        noyau physique) : il ne dispose que de la morphologie et du temps ;
      - its capacity is reduced (5 leaves, 120 trees).
    Both variants are published side by side because they do not answer the same
    question: `hybrid` maximises interpolation within the sampled typologies,
    `hybrid_lowcap` better preserves extrapolation to an unseen typology. Choosing
    one or the other on the CV then used to publish it would be selection on the
    test : on les rapporte donc toutes les deux, avec leurs deux profils.
    """
    return m_hybrid(tr, te, cols=RESID_RESTRICTED,
                    params=dict(LGB_RESID, num_leaves=5, n_estimators=120))


def m_hybrid(tr, te, cols=None, params=None):
    """Hybrid architecture: the physics carries the prediction, LightGBM corrects it.

    LightGBM does NOT learn the level, it learns the RESIDUAL of the physical model. The
    transferable part of the prediction (geometric divergence) is thus carried by
    physical parameters, and the non-transferable part is confined to a bounded
    correction term - the architecture recommended in the conclusion of negative-results.md.
    """
    cols = cols or FEATURES2
    p = fit_physical(tr)
    base_tr = predict_physical(p, tr)
    mdl = lgb.LGBMRegressor(**(params or LGB_RESID)).fit(
        tr[cols], tr.noise_dB.values - base_tr)
    return predict_physical(p, te) + mdl.predict(te[cols])


MODELS = {
    'global_mean':    (m_global_mean, 'Moyenne globale'),
    'site_mean':      (m_site_mean, 'Moyenne par site'),
    'site_hour_mean': (m_site_hour_mean, 'Moyenne par (site, heure)'),
    'dist_road':      (m_dist_road, 'Regression on log(distance to road)'),
    'idw':            (m_idw, 'Distance inverse (k=8, p=2)'),
    'lgbm_time':      (_lgbm(TIME), 'LightGBM — temps seul (ablation)'),
    'lgbm_morpho':    (_lgbm(MORPHO), 'LightGBM — morphologie seule (ablation)'),
    'lgbm_full':      (_lgbm(FEATURES), 'LightGBM — morphologie + temps (v1)'),
    # --- v2 ---
    'lgbm_v2':        (_lgbm(FEATURES2), 'LightGBM v2 - road classes split + cyclic hour'),
    'physical':       (m_physical, 'Physical kernel alone (3 parameters)'),
    'hybrid':         (m_hybrid, 'HYBRID - physics + LightGBM on the residual'),
    'hybrid_lowcap':  (m_hybrid_lowcap, 'Conservative HYBRID - constrained residual (morphology+time)'),
}


# --------------------------------------------------------------------------- protocoles
def oof_block_cv(df, fn, n_folds=N_FOLDS):
    """GroupKFold sur les blocs de 600 m."""
    oof = np.full(len(df), np.nan)
    n = min(n_folds, df.block.nunique())
    for tr_i, te_i in GroupKFold(n).split(df, df.noise_dB, df.block):
        oof[te_i] = fn(df.iloc[tr_i], df.iloc[te_i])
    return oof


def oof_bloo(df, fn, buffer_m=BUFFER_M):
    """Buffered leave-one-out: train on the points more than buffer_m from the tested one."""
    xy = df[['x', 'y']].values
    oof = np.full(len(df), np.nan)
    for i in range(len(df)):
        d = np.hypot(xy[:, 0] - xy[i, 0], xy[:, 1] - xy[i, 1])
        tr = df.iloc[np.where(d > buffer_m)[0]]
        if len(tr) < 20:          # isolated block: not cleanly evaluable
            continue
        oof[i] = fn(tr, df.iloc[[i]])[0]
    return oof


def oof_loso(df, fn):
    """Leave-one-site-out: each site predicted by a model that has never seen it."""
    oof = np.full(len(df), np.nan)
    for s in df.site.unique():
        te = df.site == s
        oof[te.values] = fn(df[~te], df[te])
    return oof


# ----------------------------------------------------------------------------- metrics
def scores(y, p):
    ok = ~np.isnan(p)
    y, p = np.asarray(y)[ok], np.asarray(p)[ok]
    ss_res = float(((y - p) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r = float(np.corrcoef(y, p)[0, 1]) if np.std(p) > 1e-9 else float('nan')
    return {'n': int(ok.sum()), 'r': r, 'r2': 1 - ss_res / ss_tot,
            'mae': float(np.abs(y - p).mean()),
            'rmse': float(np.sqrt(((y - p) ** 2).mean()))}


def boot_ci(y, p, blocks, n_boot=N_BOOT, seed=SEED):
    """95 % CI by BLOCK bootstrap: resampling correlated points
    would give an artificially narrow interval."""
    ok = ~np.isnan(p)
    y, p, blocks = np.asarray(y)[ok], np.asarray(p)[ok], np.asarray(blocks)[ok]
    uniq = np.unique(blocks)
    idx_by_block = {b: np.where(blocks == b)[0] for b in uniq}
    rng = np.random.default_rng(seed)
    r2s, maes = [], []
    for _ in range(n_boot):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        idx = np.concatenate([idx_by_block[b] for b in pick])
        yy, pp = y[idx], p[idx]
        sst = ((yy - yy.mean()) ** 2).sum()
        if sst <= 0:
            continue
        r2s.append(1 - ((yy - pp) ** 2).sum() / sst)
        maes.append(np.abs(yy - pp).mean())
    q = lambda a: [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]
    return {'r2_ci95': q(r2s), 'mae_ci95': q(maes)}


# --------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fast', action='store_true', help='saute le buffered leave-one-out')
    args = ap.parse_args()

    df = load_points()
    y = df.noise_dB.values
    print(f'{len(df)} mesures · {df.block.nunique()} blocs de {BLOCK_M} m · '
          f'{df.site.nunique()} sites · dB {y.min():.0f}-{y.max():.0f} (sd {y.std():.1f})')
    print(f'  points per block: median {df.groupby("block").size().median():.0f}, '
          f'max {df.groupby("block").size().max()}')

    protocols = [('block_cv', f'Block-CV {BLOCK_M} m', oof_block_cv),
                 ('loso', 'Leave-one-site-out', oof_loso)]
    if not args.fast:
        protocols.insert(1, ('bloo', f'Buffered LOO {BUFFER_M} m', oof_bloo))
    # Reference protocol: the buffered LOO, whose exclusion radius equals the feature
    # aggregation radius. It is the one that decides between the candidate models.
    REF_PROTO = 'block_cv' if args.fast else 'bloo'

    results = {}
    for pkey, plabel, runner in protocols:
        print(f'\n=== {plabel} ' + '=' * (58 - len(plabel)))
        print(f'{"model":34} {"R2":>7} {"R2 95%CI":>16} {"MAE":>6} {"MAE 95%CI":>14}  {"r":>5}')
        results[pkey] = {'label': plabel, 'models': {}}
        for key, (fn, label) in MODELS.items():
            oof = runner(df, fn)
            s = scores(y, oof)
            s.update(boot_ci(y, oof, df.block.values))
            s['label'] = label
            results[pkey]['models'][key] = s
            print(f'{label:34} {s["r2"]:7.3f} [{s["r2_ci95"][0]:6.2f},{s["r2_ci95"][1]:6.2f}] '
                  f'{s["mae"]:6.2f} [{s["mae_ci95"][0]:5.2f},{s["mae_ci95"][1]:5.2f}]  {s["r"]:5.2f}')

    # --- net contribution of morphology: the question the audit asked ---
    print('\n=== Apport de la morphologie urbaine ' + '=' * 27)
    for pkey in results:
        mm = results[pkey]['models']
        d_r2 = mm['lgbm_full']['r2'] - mm['site_hour_mean']['r2']
        d_mae = mm['site_hour_mean']['mae'] - mm['lgbm_full']['mae']
        results[pkey]['morphology_gain'] = {
            'vs': 'site_hour_mean', 'delta_r2': d_r2, 'delta_mae_dB': d_mae}
        print(f'  {results[pkey]["label"]:24} ΔR² {d_r2:+.3f} · ΔMAE {d_mae:+.2f} dB '
              f'(lgbm_full vs site_hour_mean)')

    # --- v2 : les deux questions que pose l'architecture hybride ---
    # (a) what does ML gain AFTER the physics has done its work?
    # (b) does the hybrid finally beat the one-variable regression, which beat ML v1?
    print('\n=== Contribution of ML on the residual, and hybrid vs physical baseline ' + '=' * 1)
    for pkey in results:
        mm = results[pkey]['models']
        gains = {
            'residual_ml_gain': {
                'vs': 'physical',
                'delta_r2': mm['hybrid']['r2'] - mm['physical']['r2'],
                'delta_mae_dB': mm['physical']['mae'] - mm['hybrid']['mae']},
            'hybrid_vs_dist_road': {
                'vs': 'dist_road',
                'delta_r2': mm['hybrid']['r2'] - mm['dist_road']['r2'],
                'delta_mae_dB': mm['dist_road']['mae'] - mm['hybrid']['mae']},
            'hybrid_vs_lgbm_v1': {
                'vs': 'lgbm_full',
                'delta_r2': mm['hybrid']['r2'] - mm['lgbm_full']['r2'],
                'delta_mae_dB': mm['lgbm_full']['mae'] - mm['hybrid']['mae']},
        }
        results[pkey]['v2_gains'] = gains
        print(f'  {results[pkey]["label"]:24} '
              f'ML/physique ΔR² {gains["residual_ml_gain"]["delta_r2"]:+.3f} · '
              f'hybride/dist_road ΔR² {gains["hybrid_vs_dist_road"]["delta_r2"]:+.3f} · '
              f'hybride/ML v1 ΔR² {gains["hybrid_vs_lgbm_v1"]["delta_r2"]:+.3f}')

    # --- WHICH MODEL DO WE DELIVER? (detailed block further down) --------------------
    DELIVERABLE = ['dist_road', 'lgbm_full', 'lgbm_v2', 'physical', 'hybrid', 'hybrid_lowcap']
    ref = results[REF_PROTO]['models']
    delivered = max((k for k in DELIVERABLE if k in ref), key=lambda k: ref[k]['r2'])

    # --- LOSO broken down by site, for the DELIVERED model and the old LightGBM ------
    results['loso_per_site'] = {}
    for mkey in dict.fromkeys([delivered, 'lgbm_full']):
        oof = oof_loso(df, MODELS[mkey][0])
        per_site = {}
        for s in df.site.unique():
            k = (df.site == s).values
            per_site[s] = scores(y[k], oof[k])
        if mkey == delivered:
            results['loso_per_site'] = per_site       # historical key = delivered model
        results[f'loso_per_site_{mkey}'] = per_site
        print(f'\n=== LOSO par site ({mkey}) ' + '=' * (40 - len(mkey)))
        for s, v in per_site.items():
            print(f'  {s:18} n={v["n"]:3}  R² {v["r2"]:6.2f}  MAE {v["mae"]:5.2f}  r {v["r"]:5.2f}')

    # --- WHICH MODEL DO WE DELIVER? --------------------------------------------------
    # The choice is NOT "the most sophisticated" nor "the one we wanted to build".
    # It is the one that wins under the REFERENCE PROTOCOL, among a candidate list
    # fixed BEFORE seeing the scores. The August 2026 run showed why that guard
    # is necessary: the full hybrid dominates under block-CV 600 m (the most permissive
    # permissif) et perd sous les deux protocoles stricts. Le livrer parce qu'il est le
    # more elaborate one would be exactly the error documented in negative-results.md 5.z.
    print(f'\n=== Delivered model ' + '=' * 47)
    print(f'  choisi sous « {results[REF_PROTO]["label"]} » parmi {len(DELIVERABLE)} candidats')
    for k in DELIVERABLE:
        if k in ref:
            mark = '  <== DELIVERED' if k == delivered else ''
            print(f'    {ref[k]["label"]:52} R² {ref[k]["r2"]:+.3f}{mark}')

    # --- final model: trained on ALL points, saved for the map ---
    # No metric is drawn from it (every published figure comes from the protocols
    # above). It is written here so that the script chain is SELF-CONTAINED:
    # 07_export_gama_inputs.py depends on it, and must not require running a notebook.
    # TWO FILES: the physical coefficients (JSON, readable by eye) and the residual
    # LightGBM (booster). The JSON's `apply_residual` flag says which of the two counts:
    # it is READ by 07_export_gama_inputs.py, which thereby decides whether the published
    # par le LightGBM ou reste purement physique.
    phys = fit_physical(df)
    base = predict_physical(phys, df)
    apply_resid = delivered in ('hybrid', 'hybrid_lowcap')
    if delivered == 'hybrid_lowcap':
        resid_cols, resid_params = RESID_RESTRICTED, dict(LGB_RESID, num_leaves=5,
                                                          n_estimators=120)
    else:
        resid_cols, resid_params = FEATURES2, dict(LGB_RESID, n_estimators=300)
    resid_mdl = lgb.LGBMRegressor(**resid_params).fit(
        df[resid_cols], df.noise_dB.values - base)
    resid_mdl.booster_.save_model(RESID_MODEL)

    phys_json = {'form': 'E = A_hw/max(d_hw,D0) + A_res/max(d_res,D0) + B ; L = 10*log10(E)',
                 'A_highway': float(phys[0]), 'A_residential': float(phys[1]),
                 'B_background': float(phys[2]), 'D0_m': D0,
                 'delivered_model': delivered,
                 'selected_under': results[REF_PROTO]['label'],
                 'apply_residual': apply_resid,
                 'residual_features': resid_cols,
                 'residual_model': os.path.basename(RESID_MODEL)}
    with open(PHYS_JSON, 'w') as f:
        json.dump(phys_json, f, indent=2)
    results['physical_params'] = phys_json
    results['physical_residual_sd_dB'] = float(np.std(df.noise_dB.values - base))
    print(f'\nFitted physical kernel: A_hw={phys[0]:.3g}  A_res={phys[1]:.3g}  B={phys[2]:.3g}')
    print(f'  -> level predicted by physics alone: {base.min():.1f}-{base.max():.1f} dB '
          f'(residual sd {results["physical_residual_sd_dB"]:.2f} dB)')
    print(f'Delivered model -> {PHYS_JSON} + {RESID_MODEL}'
          + ('' if apply_resid else '  (residual written but NOT applied: pure physical delivery)'))
    results['feature_importance_gain'] = dict(zip(
        resid_cols, [float(v) for v in resid_mdl.booster_.feature_importance('gain')]))

    # the old v1 model is still written: archived outputs refer to it
    lgb.LGBMRegressor(**dict(LGB_PARAMS, n_estimators=400)).fit(
        df[FEATURES], df.noise_dB).booster_.save_model(FINAL_MODEL)

    results['meta'] = {
        'n_measurements': int(len(df)), 'n_blocks': int(df.block.nunique()),
        'block_m': BLOCK_M, 'buffer_m': BUFFER_M, 'buffer_features_m': R,
        'n_folds': N_FOLDS, 'n_bootstrap': N_BOOT,
        'sites': {s: int(n) for s, n in df.site.value_counts().items()},
        'db_min': float(y.min()), 'db_max': float(y.max()), 'db_sd': float(y.std()),
        'date_min': str(df.timestamp.min().date()), 'date_max': str(df.timestamp.max().date()),
        'headline_protocol': REF_PROTO,
        'delivered_model': delivered,
        'delivered_label': results[REF_PROTO]['models'][delivered]['label'],
        'note': ('Reference protocol = buffered leave-one-out (300 m exclusion, '
                 'soit le rayon des features). Le block-CV 600 m est la version rapide. '
                 'Les deux remplacent le GroupKFold sur cellules de 110 m du notebook 08, '
                 'qui fuyait (Roberts et al. 2017).'),
    }

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    write_markdown(results)
    print(f'\nOK -> {OUT_JSON}\nOK -> {OUT_MD}')
    print('10_build_report.py now reads this JSON: no metric is copied by hand any more.')


def write_markdown(res):
    L = ['# Model comparison - Hanoi noise map', '',
         f'Generated by `scripts/04_evaluate_models.py`. n = {res["meta"]["n_measurements"]} measurements, '
         f'{res["meta"]["n_blocks"]} blocs spatiaux de {res["meta"]["block_m"]} m.', '',
         'All models are evaluated on **exactly the same splits**. '
         'IC 95 % par bootstrap par bloc.', '']
    for pkey, blk in res.items():
        if not isinstance(blk, dict) or 'models' not in blk:
            continue
        L += [f'## {blk["label"]}', '',
              '| Model | R2 | 95 % CI | MAE (dB) | 95 % CI | r |', '|---|---|---|---|---|---|']
        for m in blk['models'].values():
            L.append(f'| {m["label"]} | {m["r2"]:.3f} | '
                     f'[{m["r2_ci95"][0]:.2f}, {m["r2_ci95"][1]:.2f}] | {m["mae"]:.2f} | '
                     f'[{m["mae_ci95"][0]:.2f}, {m["mae_ci95"][1]:.2f}] | {m["r"]:.2f} |')
        g = blk['morphology_gain']
        v2 = blk['v2_gains']
        L += ['', f'**Apport propre de la morphologie** (LightGBM v1 vs table site × heure) : '
                  f'ΔR² = {g["delta_r2"]:+.3f}, ΔMAE = {g["delta_mae_dB"]:+.2f} dB.',
              '', '**Architecture hybride (v2)** :', '',
              f'- ML on the residual vs physical kernel alone: dR2 = '
              f'{v2["residual_ml_gain"]["delta_r2"]:+.3f}, '
              f'ΔMAE = {v2["residual_ml_gain"]["delta_mae_dB"]:+.2f} dB',
              f'- hybrid vs log(dist_road) regression: dR2 = '
              f'{v2["hybrid_vs_dist_road"]["delta_r2"]:+.3f}, '
              f'ΔMAE = {v2["hybrid_vs_dist_road"]["delta_mae_dB"]:+.2f} dB',
              f'- hybride vs LightGBM v1 : ΔR² = {v2["hybrid_vs_lgbm_v1"]["delta_r2"]:+.3f}, '
              f'ΔMAE = {v2["hybrid_vs_lgbm_v1"]["delta_mae_dB"]:+.2f} dB', '']
    for mkey, title in (('hybrid', 'delivered hybrid model'), ('lgbm_full', 'LightGBM v1')):
        key = f'loso_per_site_{mkey}'
        if key not in res:
            continue
        L += [f'## Leave-one-site-out, par site ({title})', '',
              '| Site | n | R² | MAE (dB) | r |', '|---|---|---|---|---|']
        for s, v in res[key].items():
            L.append(f'| {s} | {v["n"]} | {v["r2"]:.2f} | {v["mae"]:.2f} | {v["r"]:.2f} |')
        L += ['']
    p = res.get('physical_params', {})
    if p:
        L += ['## Fitted physical kernel', '',
              f'`{p["form"]}`', '',
              f'- `A_highway` = {p["A_highway"]:.4g} (power per unit length, major roads)',
              f'- `A_residential` = {p["A_residential"]:.4g} (petites rues)',
              f'- `B_background` = {p["B_background"]:.4g} (fond non routier)',
              f'- `D0` = {p["D0_m"]:.0f} m (plancher de distance)', '']
    L += ['_A negative R2 means: worse than predicting the global mean everywhere._', '']
    with open(OUT_MD, 'w') as f:
        f.write('\n'.join(L))


if __name__ == '__main__':
    main()

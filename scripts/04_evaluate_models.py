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

CRS_M = 'EPSG:32648'      # UTM 48N (mètres)
R = 300                   # rayon des features de morphologie (m) - fixe le reste
BLOCK_M = 2 * R           # 600 m : un bloc de CV doit dépasser la portée des prédicteurs
BUFFER_M = R              # rayon d'exclusion du buffered leave-one-out
N_FOLDS = 5
N_BOOT = 2000
SEED = 0

MORPHO = ['built_area_ratio', 'road_density_km_km2', 'intersection_count', 'dist_road_m']
TIME = ['hour', 'is_weekend']
FEATURES = MORPHO + TIME

# --- v2 (août 2026) : voiries séparées + heure cyclique ---------------------------------
MORPHO2 = ['built_area_ratio', 'road_density_km_km2', 'intersection_count',
           'dist_highway_m', 'dist_residential_m']
TIME2 = ['hour_sin', 'hour_cos', 'is_weekend']
FEATURES2 = MORPHO2 + TIME2
# Features du résidu de la variante conservatrice : PAS de distance, elle est déjà
# entièrement consommée par le noyau physique.
RESID_RESTRICTED = ['built_area_ratio', 'road_density_km_km2', 'intersection_count',
                    'hour_sin', 'hour_cos', 'is_weekend']

D0 = 5.0        # plancher de distance (m) : évite la singularité 1/d au ras de la voie

LGB_PARAMS = dict(n_estimators=300, learning_rate=0.05, num_leaves=15,
                  min_child_samples=10, random_state=SEED, verbose=-1)
# Le modèle de résidu apprend une correction bornée, pas le niveau complet : il lui faut
# moins de capacité, sinon il ré-apprend le bruit que la physique a déjà expliqué.
LGB_RESID = dict(LGB_PARAMS, n_estimators=200, num_leaves=7)


# ----------------------------------------------------------------------------- données
def load_points():
    """measurements.csv + features de morphologie + coordonnées métriques + bloc spatial."""
    if not os.path.exists(MEASURES):
        raise SystemExit(f'Manque {MEASURES}\n  -> python3 scripts/prepare_field_data.py')
    for f in ('hanoi_sites_buildings.gpkg', 'hanoi_sites_roads.graphml'):
        if not os.path.exists(os.path.join(PROC, f)):
            raise SystemExit(f'Manque {os.path.join(PROC, f)}\n'
                             '  -> exécuter le notebook 08 une fois (il télécharge et cache l\'OSM)')

    from noise_hanoi import features as feat

    m = pd.read_csv(MEASURES, parse_dates=['timestamp'])
    m['hour'] = m.timestamp.dt.hour
    # heure CYCLIQUE : 23 h et 0 h doivent être voisines dans l'espace des features
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
    # bloc spatial de 600 m : l'unité de découpage de la CV et du bootstrap
    df['block'] = (np.floor(df.x / BLOCK_M).astype(int).astype(str) + '_' +
                   np.floor(df.y / BLOCK_M).astype(int).astype(str))
    return df


# ---------------------------------------------------------------------------- modèles
# Convention : chaque modèle est une fonction fit_predict(train_df, test_df) -> np.ndarray.
# Elles reçoivent le DataFrame complet, donc chacune choisit l'information qu'elle utilise.
# Aucune n'a accès à test_df['noise_dB'].

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
    """Régression linéaire du niveau sur log10(distance à la route). Physique minimale."""
    lx = np.log10(np.maximum(tr.dist_road_m.values, 1.0))
    a, b = np.polyfit(lx, tr.noise_dB.values, 1)
    return a * np.log10(np.maximum(te.dist_road_m.values, 1.0)) + b


def m_idw(tr, te, k=8, power=2.0):
    """Interpolation par distance inverse sur les k plus proches points d'apprentissage.
    Baseline géostatistique : que gagne-t-on par rapport à « regarder les voisins » ?"""
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


# --------------------------------------------------- noyau physique + modèle hybride (v2)
# ÉQUATION. Une voie est modélisée comme une source LINÉIQUE incohérente : l'intensité
# décroît en 1/d (et non en 1/d², qui vaut pour une source ponctuelle). L'énergie reçue
# est la somme des contributions des deux classes de voirie et d'un fond résiduel :
#
#     E(x) = A_hw / max(d_hw, D0) + A_res / max(d_res, D0) + B
#     L(x) = 10 · log10( E(x) )
#
# Trois paramètres, tous CONTRAINTS POSITIFS : une source ne peut pas retirer d'énergie.
# A_hw et A_res sont des puissances par unité de longueur (grands axes / petites rues),
# B le fond non routier. C'est la même famille d'équations que les modèles d'émission
# normalisés, réduite à ce que nos données peuvent identifier.
#
# AJUSTEMENT EN DÉCIBELS, PAS EN ÉNERGIE. Nos niveaux couvrent 47-88 dB, soit quatre
# ordres de grandeur en énergie : un moindre carré en énergie serait entièrement piloté
# par les points les plus bruyants. On minimise donc l'écart en dB, ce qui est aussi la
# métrique sur laquelle le modèle est jugé.
def _phys_design(df):
    d_hw = np.maximum(df.dist_highway_m.values.astype(float), D0)
    d_res = np.maximum(df.dist_residential_m.values.astype(float), D0)
    return np.column_stack([1.0 / d_hw, 1.0 / d_res, np.ones(len(df))])


def fit_physical(tr):
    from scipy.optimize import least_squares
    X = _phys_design(tr)
    y = tr.noise_dB.values.astype(float)
    e_mean = float(np.mean(10 ** (y / 10.0)))
    # initialisation : moitié du niveau moyen dans le fond, moitié partagée entre les
    # deux classes de voirie à leur distance médiane.
    p0 = np.array([0.25 * e_mean * float(np.median(np.maximum(tr.dist_highway_m, D0))),
                   0.25 * e_mean * float(np.median(np.maximum(tr.dist_residential_m, D0))),
                   0.50 * e_mean])
    f = lambda p: 10 * np.log10(np.maximum(X @ p, 1e-9)) - y
    return least_squares(f, p0, bounds=(0, np.inf), max_nfev=2000).x


def predict_physical(p, te):
    return 10 * np.log10(np.maximum(_phys_design(te) @ p, 1e-9))


def m_physical(tr, te):
    """Le noyau physique SEUL : trois paramètres, aucune donnée morphologique."""
    return predict_physical(fit_physical(tr), te)


def m_hybrid_lowcap(tr, te):
    """Variante conservatrice de l'hybride, sur le compromis interpolation/extrapolation.

    Deux différences avec `m_hybrid`, toutes deux destinées à empêcher le résidu de
    ré-apprendre ce que la physique explique déjà :
      - le modèle de résidu ne VOIT PAS les distances (elles sont déjà consommées par le
        noyau physique) : il ne dispose que de la morphologie et du temps ;
      - sa capacité est réduite (5 feuilles, 120 arbres).
    Les deux variantes sont publiées côte à côte parce qu'elles ne répondent pas à la même
    question : `hybrid` maximise l'interpolation dans les typologies échantillonnées,
    `hybrid_lowcap` préserve mieux l'extrapolation vers une typologie non vue. Choisir
    l'une ou l'autre sur la CV qui sert ensuite à la publier serait une sélection sur le
    test : on les rapporte donc toutes les deux, avec leurs deux profils.
    """
    return m_hybrid(tr, te, cols=RESID_RESTRICTED,
                    params=dict(LGB_RESID, num_leaves=5, n_estimators=120))


def m_hybrid(tr, te, cols=None, params=None):
    """Architecture hybride : la physique porte la prédiction, le LightGBM la corrige.

    Le LightGBM n'apprend PAS le niveau, il apprend le RÉSIDU du modèle physique. La
    part transférable de la prédiction (la divergence géométrique) est ainsi portée par
    des paramètres physiques, et la part non transférable est confinée dans un terme de
    correction borné - l'architecture recommandée en conclusion de negative_results.md.
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
    'dist_road':      (m_dist_road, 'Régression sur log(distance route)'),
    'idw':            (m_idw, 'Distance inverse (k=8, p=2)'),
    'lgbm_time':      (_lgbm(TIME), 'LightGBM — temps seul (ablation)'),
    'lgbm_morpho':    (_lgbm(MORPHO), 'LightGBM — morphologie seule (ablation)'),
    'lgbm_full':      (_lgbm(FEATURES), 'LightGBM — morphologie + temps (v1)'),
    # --- v2 ---
    'lgbm_v2':        (_lgbm(FEATURES2), 'LightGBM v2 — voiries séparées + heure cyclique'),
    'physical':       (m_physical, 'Noyau physique seul (3 paramètres)'),
    'hybrid':         (m_hybrid, 'HYBRIDE — physique + LightGBM sur le résidu'),
    'hybrid_lowcap':  (m_hybrid_lowcap, 'HYBRIDE conservateur — résidu bridé (morpho+temps)'),
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
    """Buffered leave-one-out : apprentissage sur les points à plus de buffer_m du testé."""
    xy = df[['x', 'y']].values
    oof = np.full(len(df), np.nan)
    for i in range(len(df)):
        d = np.hypot(xy[:, 0] - xy[i, 0], xy[:, 1] - xy[i, 1])
        tr = df.iloc[np.where(d > buffer_m)[0]]
        if len(tr) < 20:          # bloc isolé : non évaluable proprement
            continue
        oof[i] = fn(tr, df.iloc[[i]])[0]
    return oof


def oof_loso(df, fn):
    """Leave-one-site-out : chaque site prédit par un modèle qui ne l'a jamais vu."""
    oof = np.full(len(df), np.nan)
    for s in df.site.unique():
        te = df.site == s
        oof[te.values] = fn(df[~te], df[te])
    return oof


# ----------------------------------------------------------------------------- métriques
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
    """IC 95 % par bootstrap PAR BLOC : rééchantillonner des points corrélés
    donnerait un intervalle artificiellement étroit."""
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
    print(f'  points par bloc : médiane {df.groupby("block").size().median():.0f}, '
          f'max {df.groupby("block").size().max()}')

    protocols = [('block_cv', f'Block-CV {BLOCK_M} m', oof_block_cv),
                 ('loso', 'Leave-one-site-out', oof_loso)]
    if not args.fast:
        protocols.insert(1, ('bloo', f'Buffered LOO {BUFFER_M} m', oof_bloo))
    # protocole de référence : le buffered LOO, dont le rayon d'exclusion égale le rayon
    # d'agrégation des features. C'est lui qui départage les modèles candidats.
    REF_PROTO = 'block_cv' if args.fast else 'bloo'

    results = {}
    for pkey, plabel, runner in protocols:
        print(f'\n=== {plabel} ' + '=' * (58 - len(plabel)))
        print(f'{"modèle":34} {"R²":>7} {"IC95 R²":>16} {"MAE":>6} {"IC95 MAE":>14}  {"r":>5}')
        results[pkey] = {'label': plabel, 'models': {}}
        for key, (fn, label) in MODELS.items():
            oof = runner(df, fn)
            s = scores(y, oof)
            s.update(boot_ci(y, oof, df.block.values))
            s['label'] = label
            results[pkey]['models'][key] = s
            print(f'{label:34} {s["r2"]:7.3f} [{s["r2_ci95"][0]:6.2f},{s["r2_ci95"][1]:6.2f}] '
                  f'{s["mae"]:6.2f} [{s["mae_ci95"][0]:5.2f},{s["mae_ci95"][1]:5.2f}]  {s["r"]:5.2f}')

    # --- apport propre de la morphologie : la question posée par l'audit ---
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
    # (a) que gagne le ML APRÈS que la physique a fait son travail ?
    # (b) l'hybride bat-il enfin la régression à une variable, qui battait le ML v1 ?
    print('\n=== Apport du ML sur le résidu, et hybride vs baseline physique ' + '=' * 1)
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

    # --- QUEL MODÈLE LIVRE-T-ON ? (voir le bloc détaillé plus bas) -------------------
    DELIVERABLE = ['dist_road', 'lgbm_full', 'lgbm_v2', 'physical', 'hybrid', 'hybrid_lowcap']
    ref = results[REF_PROTO]['models']
    delivered = max((k for k in DELIVERABLE if k in ref), key=lambda k: ref[k]['r2'])

    # --- LOSO détaillé par site, pour le modèle LIVRÉ et pour l'ancien LightGBM ------
    results['loso_per_site'] = {}
    for mkey in dict.fromkeys([delivered, 'lgbm_full']):
        oof = oof_loso(df, MODELS[mkey][0])
        per_site = {}
        for s in df.site.unique():
            k = (df.site == s).values
            per_site[s] = scores(y[k], oof[k])
        if mkey == delivered:
            results['loso_per_site'] = per_site       # clé historique = modèle livré
        results[f'loso_per_site_{mkey}'] = per_site
        print(f'\n=== LOSO par site ({mkey}) ' + '=' * (40 - len(mkey)))
        for s, v in per_site.items():
            print(f'  {s:18} n={v["n"]:3}  R² {v["r2"]:6.2f}  MAE {v["mae"]:5.2f}  r {v["r"]:5.2f}')

    # --- QUEL MODÈLE LIVRE-T-ON ? ---------------------------------------------------
    # Le choix n'est PAS « le plus sophistiqué » ni « celui qu'on voulait construire ».
    # C'est celui qui gagne sous le PROTOCOLE DE RÉFÉRENCE, parmi une liste de candidats
    # arrêtée AVANT de voir les scores. Le run d'août 2026 a montré pourquoi ce garde-fou
    # est nécessaire : l'hybride complet domine sous block-CV 600 m (le protocole le plus
    # permissif) et perd sous les deux protocoles stricts. Le livrer parce qu'il est le
    # plus élaboré serait exactement l'erreur que documente negative_results.md §5.z.
    print(f'\n=== Modèle livré ' + '=' * 47)
    print(f'  choisi sous « {results[REF_PROTO]["label"]} » parmi {len(DELIVERABLE)} candidats')
    for k in DELIVERABLE:
        if k in ref:
            mark = '  <== LIVRÉ' if k == delivered else ''
            print(f'    {ref[k]["label"]:52} R² {ref[k]["r2"]:+.3f}{mark}')

    # --- modèle final : entraîné sur TOUS les points, sauvegardé pour la carte ---
    # Aucune métrique n'en est tirée (tous les chiffres publiés viennent des protocoles
    # ci-dessus). Il est écrit ici pour que la chaîne de scripts soit AUTONOME :
    # export_gama_zones.py en dépend, et il ne doit pas exiger d'avoir lancé un notebook.
    # DEUX FICHIERS : les coefficients physiques (JSON, lisibles à l'oeil) et le LightGBM
    # de résidu (booster). Le drapeau `apply_residual` du JSON dit lequel des deux compte :
    # il est LU par export_gama_zones.py, qui décide ainsi si la carte publiée est corrigée
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
    print(f'\nNoyau physique ajusté : A_hw={phys[0]:.3g}  A_res={phys[1]:.3g}  B={phys[2]:.3g}')
    print(f'  -> niveau prédit par la physique seule : {base.min():.1f}-{base.max():.1f} dB '
          f'(résidu sd {results["physical_residual_sd_dB"]:.2f} dB)')
    print(f'Modèle livré -> {PHYS_JSON} + {RESID_MODEL}'
          + ('' if apply_resid else '  (résidu écrit mais NON appliqué : livraison physique pure)'))
    results['feature_importance_gain'] = dict(zip(
        resid_cols, [float(v) for v in resid_mdl.booster_.feature_importance('gain')]))

    # l'ancien modèle v1 reste écrit : des sorties archivées y font référence
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
        'note': ('Protocole de référence = buffered leave-one-out (exclusion de 300 m, '
                 'soit le rayon des features). Le block-CV 600 m est la version rapide. '
                 'Les deux remplacent le GroupKFold sur cellules de 110 m du notebook 08, '
                 'qui fuyait (Roberts et al. 2017).'),
    }

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    write_markdown(results)
    print(f'\nOK -> {OUT_JSON}\nOK -> {OUT_MD}')
    print('build_report.py lit désormais ce JSON : plus aucune métrique recopiée à la main.')


def write_markdown(res):
    L = ['# Comparaison des modèles — carte de bruit Hanoï', '',
         f'Généré par `scripts/evaluate_models.py`. n = {res["meta"]["n_measurements"]} mesures, '
         f'{res["meta"]["n_blocks"]} blocs spatiaux de {res["meta"]["block_m"]} m.', '',
         'Tous les modèles sont évalués sur **exactement les mêmes découpages**. '
         'IC 95 % par bootstrap par bloc.', '']
    for pkey, blk in res.items():
        if not isinstance(blk, dict) or 'models' not in blk:
            continue
        L += [f'## {blk["label"]}', '',
              '| Modèle | R² | IC 95 % | MAE (dB) | IC 95 % | r |', '|---|---|---|---|---|---|']
        for m in blk['models'].values():
            L.append(f'| {m["label"]} | {m["r2"]:.3f} | '
                     f'[{m["r2_ci95"][0]:.2f}, {m["r2_ci95"][1]:.2f}] | {m["mae"]:.2f} | '
                     f'[{m["mae_ci95"][0]:.2f}, {m["mae_ci95"][1]:.2f}] | {m["r"]:.2f} |')
        g = blk['morphology_gain']
        v2 = blk['v2_gains']
        L += ['', f'**Apport propre de la morphologie** (LightGBM v1 vs table site × heure) : '
                  f'ΔR² = {g["delta_r2"]:+.3f}, ΔMAE = {g["delta_mae_dB"]:+.2f} dB.',
              '', '**Architecture hybride (v2)** :', '',
              f'- ML sur le résidu vs noyau physique seul : ΔR² = '
              f'{v2["residual_ml_gain"]["delta_r2"]:+.3f}, '
              f'ΔMAE = {v2["residual_ml_gain"]["delta_mae_dB"]:+.2f} dB',
              f'- hybride vs régression log(dist_road) : ΔR² = '
              f'{v2["hybrid_vs_dist_road"]["delta_r2"]:+.3f}, '
              f'ΔMAE = {v2["hybrid_vs_dist_road"]["delta_mae_dB"]:+.2f} dB',
              f'- hybride vs LightGBM v1 : ΔR² = {v2["hybrid_vs_lgbm_v1"]["delta_r2"]:+.3f}, '
              f'ΔMAE = {v2["hybrid_vs_lgbm_v1"]["delta_mae_dB"]:+.2f} dB', '']
    for mkey, title in (('hybrid', 'modèle hybride livré'), ('lgbm_full', 'LightGBM v1')):
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
        L += ['## Noyau physique ajusté', '',
              f'`{p["form"]}`', '',
              f'- `A_highway` = {p["A_highway"]:.4g} (puissance par unité de longueur, grands axes)',
              f'- `A_residential` = {p["A_residential"]:.4g} (petites rues)',
              f'- `B_background` = {p["B_background"]:.4g} (fond non routier)',
              f'- `D0` = {p["D0_m"]:.0f} m (plancher de distance)', '']
    L += ['_Un R² négatif signifie : moins bon que de prédire partout la moyenne globale._', '']
    with open(OUT_MD, 'w') as f:
        f.write('\n'.join(L))


if __name__ == '__main__':
    main()

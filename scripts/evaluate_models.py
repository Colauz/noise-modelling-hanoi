"""Évaluation honnête du modèle Hanoï : CV à blocs spatiaux + baselines + ablation.

POURQUOI CE SCRIPT EXISTE
-------------------------
Le notebook 08 groupait la validation croisée sur `lat.round(3)/lon.round(3)`, soit des
cellules de ~110 m. Or les features de morphologie sont des agrégats sur un disque de
RAYON 300 m : deux points distants de 110 m partagent plus de 85 % de leur disque. Leurs
vecteurs de features sont donc quasi identiques et leurs niveaux fortement autocorrélés :
le modèle voyait, en apprentissage, des quasi-jumeaux de ses points de test. Le R² obtenu
n'était pas hors-échantillon (Roberts et al. 2017, Ecography).

Ce script remplace ce protocole par deux protocoles défendables :

  1. BLOCK-CV      blocs carrés de BLOCK_M = 600 m (= 2 x rayon de buffer) en UTM 48N,
                   GroupKFold sur l'identifiant de bloc.
  2. BLOO          buffered leave-one-out : pour chaque point, on l'apprend sur TOUS les
                   points situés à plus de BUFFER_M = 300 m de lui. C'est le protocole de
                   référence, plus strict et sans hasard de découpage.
  3. LOSO          leave-one-site-out : généralisation à une typologie urbaine non vue.

Et il ajoute ce qui manquait : des BASELINES et une ABLATION, évaluées sur exactement
les mêmes découpages, pour répondre à la question « la morphologie urbaine sert-elle
vraiment à quelque chose ? ».

  global_mean       moyenne globale                        (plancher absolu)
  site_mean         moyenne par site                       (aucune info spatiale fine)
  site_hour_mean    moyenne par (site, heure)              <- LE baseline à battre
  dist_road         régression linéaire sur log(dist_road) (physique minimale)
  idw               pondération inverse de la distance     (interpolation pure)
  lgbm_time         LightGBM, heure + weekend SEULEMENT    (ablation : sans morphologie)
  lgbm_morpho       LightGBM, morphologie SEULEMENT        (ablation : sans temps)
  lgbm_full         LightGBM, morphologie + temps          (le modèle du projet)

Chaque score est assorti d'un intervalle de confiance à 95 % par bootstrap PAR BLOC
(et non par point : rééchantillonner des points corrélés donnerait un IC trop étroit).

SORTIES
-------
  outputs/models/metrics.json          consommé par scripts/build_report.py (plus de
                                       recopie manuelle de chiffres dans le rapport)
  outputs/models/model_comparison.md   tableau prêt à coller dans le manuscrit
  outputs/models/surrogate_lgbm_hanoi_direct.txt   modèle final (tous les points),
                                       consommé par scripts/export_gama_zones.py

USAGE
-----
  python3 scripts/evaluate_models.py [--fast]

  --fast  saute le BLOO (le plus coûteux : un ajustement par point).

PRÉREQUIS : data/raw/hanoi/measurements.csv (scripts/prepare_field_data.py) et les caches
OSM data/processed/hanoi/hanoi_sites_{buildings.gpkg,roads.graphml} (créés par le
notebook 08). Le script dit quoi lancer s'il manque quelque chose.
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

MEASURES = os.path.join(ROOT, 'data', 'raw', 'hanoi', 'measurements.csv')
PROC = os.path.join(ROOT, 'data', 'processed', 'hanoi')
OUT_JSON = os.path.join(ROOT, 'outputs', 'models', 'metrics.json')
OUT_MD = os.path.join(ROOT, 'outputs', 'models', 'model_comparison.md')
FINAL_MODEL = os.path.join(ROOT, 'outputs', 'models', 'surrogate_lgbm_hanoi_direct.txt')

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

LGB_PARAMS = dict(n_estimators=300, learning_rate=0.05, num_leaves=15,
                  min_child_samples=10, random_state=SEED, verbose=-1)


# ----------------------------------------------------------------------------- données
def load_points():
    """measurements.csv + features de morphologie + coordonnées métriques + bloc spatial."""
    if not os.path.exists(MEASURES):
        raise SystemExit(f'Manque {MEASURES}\n  -> python3 scripts/prepare_field_data.py')
    for f in ('hanoi_sites_buildings.gpkg', 'hanoi_sites_roads.graphml'):
        if not os.path.exists(os.path.join(PROC, f)):
            raise SystemExit(f'Manque {os.path.join(PROC, f)}\n'
                             '  -> exécuter le notebook 08 une fois (il télécharge et cache l\'OSM)')

    import export_gama_zones as egz   # réutilise load_osm() et morphology() : pas de duplication

    m = pd.read_csv(MEASURES, parse_dates=['timestamp'])
    m['hour'] = m.timestamp.dt.hour
    m['is_weekend'] = m.timestamp.dt.dayofweek.isin([5, 6]).astype(int)
    m = m.dropna(subset=['noise_dB', 'latitude', 'longitude']).reset_index(drop=True)

    _, bld_c, nodes, edges = egz.load_osm()
    pts = gpd.GeoDataFrame(m, geometry=gpd.points_from_xy(m.longitude, m.latitude),
                           crs='EPSG:4326').to_crs(CRS_M)
    feats = egz.morphology(pts, bld_c, nodes, edges)

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


MODELS = {
    'global_mean':    (m_global_mean, 'Moyenne globale'),
    'site_mean':      (m_site_mean, 'Moyenne par site'),
    'site_hour_mean': (m_site_hour_mean, 'Moyenne par (site, heure)'),
    'dist_road':      (m_dist_road, 'Régression sur log(distance route)'),
    'idw':            (m_idw, 'Distance inverse (k=8, p=2)'),
    'lgbm_time':      (_lgbm(TIME), 'LightGBM — temps seul (ablation)'),
    'lgbm_morpho':    (_lgbm(MORPHO), 'LightGBM — morphologie seule (ablation)'),
    'lgbm_full':      (_lgbm(FEATURES), 'LightGBM — morphologie + temps (modèle du projet)'),
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

    # --- LOSO détaillé par site (le vrai test de généralisation) ---
    oof = oof_loso(df, MODELS['lgbm_full'][0])
    per_site = {}
    for s in df.site.unique():
        k = (df.site == s).values
        per_site[s] = scores(y[k], oof[k])
    results['loso_per_site'] = per_site
    print('\n=== LOSO par site (lgbm_full) ' + '=' * 34)
    for s, v in per_site.items():
        print(f'  {s:18} n={v["n"]:3}  R² {v["r2"]:6.2f}  MAE {v["mae"]:5.2f}  r {v["r"]:5.2f}')

    # --- modèle final : entraîné sur TOUS les points, sauvegardé pour la carte ---
    # Aucune métrique n'en est tirée (tous les chiffres publiés viennent des protocoles
    # ci-dessus). Il est écrit ici pour que la chaîne de scripts soit AUTONOME :
    # export_gama_zones.py en dépend, et il ne doit pas exiger d'avoir lancé un notebook.
    final = lgb.LGBMRegressor(**dict(LGB_PARAMS, n_estimators=400)).fit(
        df[FEATURES], df.noise_dB)
    final.booster_.save_model(FINAL_MODEL)
    print(f'\nModèle final (tous les points) -> {FINAL_MODEL}')
    results['feature_importance_gain'] = dict(zip(
        FEATURES, [float(v) for v in final.booster_.feature_importance('gain')]))

    results['meta'] = {
        'n_measurements': int(len(df)), 'n_blocks': int(df.block.nunique()),
        'block_m': BLOCK_M, 'buffer_m': BUFFER_M, 'buffer_features_m': R,
        'n_folds': N_FOLDS, 'n_bootstrap': N_BOOT,
        'sites': {s: int(n) for s, n in df.site.value_counts().items()},
        'db_min': float(y.min()), 'db_max': float(y.max()), 'db_sd': float(y.std()),
        'date_min': str(df.timestamp.min().date()), 'date_max': str(df.timestamp.max().date()),
        'headline_protocol': 'bloo' if not args.fast else 'block_cv',
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
        if pkey in ('meta', 'loso_per_site', 'feature_importance_gain'):
            continue
        L += [f'## {blk["label"]}', '',
              '| Modèle | R² | IC 95 % | MAE (dB) | IC 95 % | r |', '|---|---|---|---|---|---|']
        for m in blk['models'].values():
            L.append(f'| {m["label"]} | {m["r2"]:.3f} | '
                     f'[{m["r2_ci95"][0]:.2f}, {m["r2_ci95"][1]:.2f}] | {m["mae"]:.2f} | '
                     f'[{m["mae_ci95"][0]:.2f}, {m["mae_ci95"][1]:.2f}] | {m["r"]:.2f} |')
        g = blk['morphology_gain']
        L += ['', f'**Apport propre de la morphologie** (LightGBM complet vs table site × heure) : '
                  f'ΔR² = {g["delta_r2"]:+.3f}, ΔMAE = {g["delta_mae_dB"]:+.2f} dB.', '']
    L += ['## Leave-one-site-out, par site (LightGBM complet)', '',
          '| Site | n | R² | MAE (dB) | r |', '|---|---|---|---|---|']
    for s, v in res['loso_per_site'].items():
        L.append(f'| {s} | {v["n"]} | {v["r2"]:.2f} | {v["mae"]:.2f} | {v["r"]:.2f} |')
    L += ['', '_Un R² négatif signifie : moins bon que de prédire partout la moyenne globale._', '']
    with open(OUT_MD, 'w') as f:
        f.write('\n'.join(L))


if __name__ == '__main__':
    main()

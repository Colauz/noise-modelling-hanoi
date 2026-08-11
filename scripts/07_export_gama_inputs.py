"""Multi-zone, multi-hour GAMA export for the `simulation/gama/hanoi_noise.gaml` model.

Produces in simulation/gama/inputs/:
  - {zone}_noise.shp      predicted noise grid, one column per hour (h5 ... h21),
                          plus d_hw / d_res: distances to the two road classes
  - {zone}_roads.shp      road network of the zone
  - {zone}_buildings.shp  buildings of the zone
  - fleet_by_hour.csv     traffic density, composition AND FLOW by site and by hour
  - physical_params.csv   physical kernel coefficients (A_hw, A_res, B, D0)
  - noise_map.csv         flat format (x, y, noise_dB) at the reference hour REF_HOUR
  - (+ noise_points/roads/buildings.shp: the 3 zones combined, overview)
and in results/maps/:
  - hanoi_noise_map.csv   full grid, 3 zones x 17 hours (the cartographic deliverable)

zones: hoankiem - oceanpark - vinhtuy

EXTENT - AN IMPORTANT METHODOLOGICAL POINT
------------------------------------------
The grid is bounded to the measurement envelope of each site + MARGIN_M (400 m), and to
nothing more. The old outputs of notebooks 08/09 covered a 1500 m disc around Bach Khoa,
a district with NO MEASUREMENT AT ALL: that was extrapolation to an unseen typology, by a
model (the LightGBM of the time) whose leave-one-site-out was negative on 2 sites out of
3. The delivered model extrapolates markedly better since V2, but THE RULE DOES NOT
CHANGE: three sampled typologies remain three, whatever the score. Those artefacts are
archived in docs/archive/bach-khoa/. Do not reintroduce predictions outside the measured
envelope without, at a minimum, an applicability-domain mask. Guarded by
tests/test_grid_extent.py.

Sources and scientific status of each output
--------------------------------------------
  noise grid   : PREDICTED by the model delivered by 04_evaluate_models.py and trained on
                 our 363 field measurements. As of August 2026 that is the PHYSICAL
                 KERNEL ALONE: a line-source law (E = A_hw/d_hw + A_res/d_res + B), with
                 the learned residual written but not applied. Metrics:
                 models/metrics.json. The R2 0.45 of notebook 08 was an artefact of CV
                 grouped on 110 m cells: do not cite it any more.
                 What still holds: the spatial contrasts of this grid are driven by the
                 distance to the two road classes and by nothing else; morphology
                 aggregated over 300 m added no measurable gain (docs/negative-results.md
                 section 5.z).
  traffic/hour : MEASURED - 147 timestamped videos, aggregated by site and by hour.
                 TWO distinct quantities: DENSITY (veh/frame, frame-by-frame detection)
                 which populates the GAMA scene, and FLOW (veh/min, line crossings by
                 ByteTrack tracking) which is the quantity physically linked to emission.
                 Hours with no video are interpolated and flagged with measured=0.

Usage: python3 scripts/07_export_gama_inputs.py
"""
import glob
import os
import warnings

warnings.filterwarnings('ignore')

import geopandas as gpd
import lightgbm as lgb
import numpy as np
import osmnx as ox
import pandas as pd

from noise_hanoi import config as cfg

ROOT = cfg.ROOT
OUT_DIR = cfg.GAMA_INPUTS
MAP_DIR = cfg.MAPS
PROC = cfg.INTERIM
MEASURES = cfg.MEASUREMENTS
MODEL = cfg.FINAL_MODEL
RESID_MODEL = cfg.RESID_MODEL
PHYS_JSON = cfg.PHYS_JSON
COUNTS = os.path.join(PROC, 'vehicle_counts.csv')

# Feature construction now lives in the package, so that 04_evaluate_models.py,
# 03_build_features.py and this script share one definition.
from noise_hanoi.features import (
    CRS_M, R, AREA_M2, FEATURES, FEATURES2, MAJOR_HW, FAR_M,
    load_osm, classify_roads, morphology, add_time_features)
GRID_M = 40                    # pas de la grille de prédiction (mètres)
MARGIN_M = 400                 # marge autour de l'emprise des mesures de chaque site
HOURS = list(range(5, 22))     # 5h-21h : fenêtre de collecte réelle
REF_HOUR = 17                  # heure de référence du format plat (pointe du soir)
SLUGS = {'Hoan Kiem lake': 'hoankiem', 'Ocean Park': 'oceanpark', 'Vinh Tuy area': 'vinhtuy'}


def site_zones():
    """Emprise (en mètres) de chaque site, à partir des mesures terrain."""
    m = pd.read_csv(MEASURES)
    pts = gpd.GeoDataFrame(m, geometry=gpd.points_from_xy(m.longitude, m.latitude),
                           crs='EPSG:4326').to_crs(CRS_M)
    return {site: (g.total_bounds[0] - MARGIN_M, g.total_bounds[1] - MARGIN_M,
                   g.total_bounds[2] + MARGIN_M, g.total_bounds[3] + MARGIN_M)
            for site, g in pts.groupby('site')}


def grid_for(bounds):
    minx, miny, maxx, maxy = bounds
    xx, yy = np.meshgrid(np.arange(minx, maxx, GRID_M), np.arange(miny, maxy, GRID_M))
    return pd.DataFrame({'x': xx.ravel(), 'y': yy.ravel()})


def fleet_by_hour():
    """Densité et composition du trafic par site ET par heure, depuis les vidéos.

    Chaque vidéo est horodatée (nom de fichier) et déjà appariée à sa mesure de bruit.
    On agrège par (site, heure de la journée). Les heures sans vidéo sont interpolées
    linéairement entre les heures voisines mesurées et marquées measured=0 : la
    simulation peut ainsi couvrir toute la journée en distinguant mesure et estimation.
    """
    if not os.path.exists(COUNTS):
        return None
    v = pd.read_csv(COUNTS, parse_dates=['video_start', 'matched_timestamp'])
    m = pd.read_csv(MEASURES, parse_dates=['timestamp'])
    v = v.merge(m[['timestamp', 'site']], left_on='matched_timestamp',
                right_on='timestamp', how='left')
    v['hour'] = v.video_start.dt.hour

    has_flow = 'vehicles_flow' in v.columns
    cls = ['moto', 'car', 'bus', 'truck']
    rows = []
    for site, g in v.groupby('site'):
        agg = {'n_videos': ('video', 'size'), 'dB': ('matched_dB', 'mean')}
        agg.update({c: (f'{c}_mean', 'mean') for c in cls})
        if has_flow:
            agg.update({f'{c}_fl': (f'{c}_flow', 'mean') for c in cls})
        obs = g.groupby('hour').agg(**agg)
        obs['total'] = obs[cls].sum(axis=1)
        if has_flow:
            obs['total_fl'] = obs[[f'{c}_fl' for c in cls]].sum(axis=1)
        full = obs.reindex(HOURS)
        measured = full['n_videos'].notna()
        # interpolation des heures non filmées (bornes = valeur mesurée la plus proche)
        icols = cls + ['total'] + ([f'{c}_fl' for c in cls] + ['total_fl'] if has_flow else [])
        full[icols] = full[icols].interpolate(method='linear', limit_direction='both')
        for h in HOURS:
            tot = float(full.loc[h, 'total'])
            row = {'site_name': site, 'hour': h, 'total': round(tot, 3),
                   'measured': int(bool(measured.loc[h])),
                   'n_videos': int(full.loc[h, 'n_videos']) if measured.loc[h] else 0}
            # `*_share` reste calculé sur la DENSITÉ : c'est la composition visible du
            # parc, utilisée par GAMA pour peupler la scène. Le DÉBIT, lui, pilote
            # l'émission acoustique — les deux ne se déduisent pas l'un de l'autre.
            for c in cls:
                row[f'{c}_share'] = round(float(full.loc[h, c]) / tot, 4) if tot > 0 else 0.0
            if has_flow:
                tf = float(full.loc[h, 'total_fl'])
                row['total_flow_per_min'] = round(tf, 3)
                for c in cls:
                    row[f'{c}_flow_per_min'] = round(float(full.loc[h, f'{c}_fl']), 3)
            rows.append(row)
    return pd.DataFrame(rows)


def construction_sites():
    """Registre des chantiers (formulaire dédié) -> GeoDataFrame.

    `loud` = 1 si le chantier était noté "actif et bruyant" (perçage, marteau).
    Calibration observée sur nos mesures d'Ocean Park : les points signalant un
    chantier à proximité sont +2 dB au-dessus des autres (n=32 vs 152) ; pendant
    la session de 15 h où un chantier était actif et bruyant, l'écart atteint +10 dB.
    """
    files = glob.glob(os.path.join(cfg.KOBO_DIR, '*onstruction*.csv'))
    if not files:
        return None
    raw = pd.read_csv(max(files), sep=';')
    if len(raw.columns) == 1:
        raw = pd.read_csv(max(files))
    loc = [c for c in raw.columns if '_Construction site location' in c]
    if len(loc) < 2:
        return None
    lat = pd.to_numeric(raw[loc[0]], errors='coerce')
    lon = pd.to_numeric(raw[loc[1]], errors='coerce')
    act = next((raw[c] for c in raw.columns if 'Activity level' in c), pd.Series([''] * len(raw)))
    typ = next((raw[c] for c in raw.columns if c.strip() == 'Type'), pd.Series(['Construction'] * len(raw)))
    df = pd.DataFrame({
        'site_type': typ.astype(str),
        'activity': act.astype(str),
        'loud': act.astype(str).str.contains('loud', case=False, na=False).astype(int),
    })
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(lon, lat), crs='EPSG:4326')
    return gdf.dropna(subset=['geometry'])


def measurement_points():
    """Nos mesures terrain, pour les afficher dans GAMA (d'où viennent les données)."""
    m = pd.read_csv(MEASURES, parse_dates=['timestamp'])
    m['hour'] = m.timestamp.dt.hour
    keep = m[['site', 'noise_dB', 'hour', 'latitude', 'longitude']].dropna()
    return gpd.GeoDataFrame(
        keep.rename(columns={'noise_dB': 'dB'}),
        geometry=gpd.points_from_xy(keep.longitude, keep.latitude), crs='EPSG:4326')


def load_hybrid():
    """Charge le modèle livré : noyau physique (JSON) + LightGBM de résidu (booster).

    Retourne une fonction predict(feats) -> niveau en dB. Les paramètres physiques sont
    lisibles à l'oeil dans hybrid_physical.json : c'est un des intérêts de l'architecture.
    """
    import json
    if not (os.path.exists(PHYS_JSON) and os.path.exists(RESID_MODEL)):
        raise SystemExit(f'Manque {PHYS_JSON} ou {RESID_MODEL}\n'
                         '  -> python3 scripts/04_evaluate_models.py')
    with open(PHYS_JSON) as f:
        p = json.load(f)
    d0 = p['D0_m']
    # `apply_residual` est décidé par evaluate_models.py, sur le protocole de référence.
    # Si le noyau physique seul y bat l'hybride, la carte publiée doit être physique pure :
    # appliquer quand même la correction apprise dégraderait la carte hors des typologies
    # échantillonnées, sans qu'aucune métrique publiée ne le montre.
    apply_resid = p.get('apply_residual', True)
    cols = p.get('residual_features', FEATURES2)
    resid = lgb.Booster(model_file=RESID_MODEL) if apply_resid else None

    def predict(feats):
        d_hw = np.maximum(feats['dist_highway_m'].values.astype(float), d0)
        d_res = np.maximum(feats['dist_residential_m'].values.astype(float), d0)
        e = p['A_highway'] / d_hw + p['A_residential'] / d_res + p['B_background']
        base = 10 * np.log10(np.maximum(e, 1e-9))
        return base + (resid.predict(feats[cols]) if resid is not None else 0.0)
    return predict, p


def main():
    print('Chargement OSM (cache)...')
    bld, bld_c, nodes, edges = load_osm()
    predict_hybrid, phys = load_hybrid()
    print(f'Modèle livré : {phys.get("delivered_model", "?")} '
          f'(choisi sous « {phys.get("selected_under", "?")} »)')
    print(f'  noyau physique : A_hw={phys["A_highway"]:.4g} · A_res={phys["A_residential"]:.4g} '
          f'· B={phys["B_background"]:.4g} (D0={phys["D0_m"]:.0f} m)')
    print(f'  correction LightGBM sur le résidu : '
          f'{"APPLIQUÉE" if phys.get("apply_residual", True) else "NON appliquée"}')
    zones = site_zones()

    all_pts, all_roads, all_blds = [], [], []
    for site, bounds in zones.items():
        g = grid_for(bounds)
        gdf = gpd.GeoDataFrame(g, geometry=gpd.points_from_xy(g.x, g.y), crs=CRS_M)
        feats = morphology(gdf, bld_c, nodes, edges)
        # une prédiction par heure de la journée -> colonnes h5 ... h21
        for h in HOURS:
            add_time_features(feats, h, is_weekend=0)
            gdf[f'h{h}'] = predict_hybrid(feats).round(2)
        gdf['site'] = site
        # Distances par classe de voirie exportées AVEC la grille : elles permettent à
        # GAMA de refaire la décomposition énergétique fond/trafic avec la MÊME physique
        # que le modèle (E_trafic = A_hw/d_hw + A_res/d_res, E_fond = B) au lieu de
        # l'approximer par un percentile bas de la zone.
        gdf['d_hw'] = feats['dist_highway_m'].round(1).values
        gdf['d_res'] = feats['dist_residential_m'].round(1).values
        cols = ['site', 'd_hw', 'd_res'] + [f'h{h}' for h in HOURS] + ['geometry']
        all_pts.append(gdf[cols])

        box = gpd.GeoDataFrame(geometry=[gpd.GeoSeries.from_wkt(
            [f'POLYGON(({bounds[0]} {bounds[1]},{bounds[2]} {bounds[1]},'
             f'{bounds[2]} {bounds[3]},{bounds[0]} {bounds[3]},{bounds[0]} {bounds[1]}))'])[0]],
            crs=CRS_M)
        r = gpd.clip(edges[['geometry']], box).copy(); r['site'] = site
        b = gpd.clip(bld[['geometry']], box).copy(); b['site'] = site
        all_roads.append(r); all_blds.append(b)
        rng = f"{gdf[[f'h{h}' for h in HOURS]].min().min():.0f}-{gdf[[f'h{h}' for h in HOURS]].max().max():.0f}"
        print(f'  {site:16} {len(gdf):5} cellules · dB {rng} sur 5h-21h · '
              f'{len(r)} routes · {len(b)} bâtiments')

    pts = gpd.GeoDataFrame(pd.concat(all_pts, ignore_index=True), crs=CRS_M).to_crs('EPSG:4326')
    roads = gpd.GeoDataFrame(pd.concat(all_roads, ignore_index=True), crs=CRS_M).to_crs('EPSG:4326')
    blds = gpd.GeoDataFrame(pd.concat(all_blds, ignore_index=True), crs=CRS_M).to_crs('EPSG:4326')
    blds = blds[blds.geometry.geom_type.isin(['Polygon', 'MultiPolygon'])]

    pts.to_file(os.path.join(OUT_DIR, 'noise_points.shp'))
    roads.to_file(os.path.join(OUT_DIR, 'roads.shp'))
    blds.to_file(os.path.join(OUT_DIR, 'buildings.shp'))

    # --- exports tabulaires, sur la MÊME emprise que les shapefiles ---
    flat = pd.DataFrame({
        'site': pts.site.values,
        'longitude': pts.geometry.x.values.round(7),
        'latitude': pts.geometry.y.values.round(7),
        **{f'h{h}': pts[f'h{h}'].values for h in HOURS},
    })
    os.makedirs(MAP_DIR, exist_ok=True)
    flat.to_csv(os.path.join(MAP_DIR, 'hanoi_noise_map.csv'), index=False)
    (flat.rename(columns={'longitude': 'x', 'latitude': 'y', f'h{REF_HOUR}': 'noise_dB'})
         .assign(hour=REF_HOUR)[['x', 'y', 'noise_dB', 'site', 'hour']]
         .to_csv(os.path.join(OUT_DIR, 'noise_map.csv'), index=False))
    for site, slug in SLUGS.items():
        pts[pts.site == site].to_file(os.path.join(OUT_DIR, f'{slug}_noise.shp'))
        roads[roads.site == site].to_file(os.path.join(OUT_DIR, f'{slug}_roads.shp'))
        blds[blds.site == site].to_file(os.path.join(OUT_DIR, f'{slug}_buildings.shp'))

    # chantiers + points de mesure, découpés par zone
    constr = construction_sites()
    meas = measurement_points()
    for site, slug in SLUGS.items():
        zpts = pts[pts.site == site]
        if len(zpts) == 0:
            continue
        minx, miny, maxx, maxy = zpts.total_bounds
        if constr is not None and len(constr):
            sub = constr.cx[minx:maxx, miny:maxy]
            if len(sub):
                sub.to_file(os.path.join(OUT_DIR, f'{slug}_construction.shp'))
                print(f'  {slug:10} {len(sub)} chantier(s)')
        sm = meas[meas.site == site]
        if len(sm):
            sm.to_file(os.path.join(OUT_DIR, f'{slug}_measurements.shp'))

    # paramètres du noyau physique, lisibles par GAMA (une ligne, en-tête + valeurs)
    pd.DataFrame([{'A_highway': phys['A_highway'], 'A_residential': phys['A_residential'],
                   'B_background': phys['B_background'], 'D0_m': phys['D0_m']}]).to_csv(
        os.path.join(OUT_DIR, 'physical_params.csv'), index=False)

    fleet = fleet_by_hour()
    if fleet is not None:
        fleet.to_csv(os.path.join(OUT_DIR, 'fleet_by_hour.csv'), index=False)
        print('\ntrafic par heure (mesuré sur les vidéos, * = heure filmée) :')
        piv = fleet.pivot(index='hour', columns='site_name', values='total')
        mark = fleet.pivot(index='hour', columns='site_name', values='measured')
        for h in HOURS:
            line = f'  {h:2d}h '
            for s in piv.columns:
                star = '*' if mark.loc[h, s] else ' '
                line += f'{s.split()[0]:>10}={piv.loc[h, s]:5.1f}{star} '
            print(line)

    print(f'\nOK -> {OUT_DIR}')
    print(f'  {len(pts)} cellules · {len(HOURS)} heures prédites · 3 zones')


if __name__ == '__main__':
    main()

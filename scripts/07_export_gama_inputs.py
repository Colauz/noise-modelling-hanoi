"""Export GAMA multi-zones et multi-heures pour la simulation `gama/hanoi_noise.gaml`.

Produit dans outputs/gama_inputs/ :
  - {zone}_noise.shp      grille de bruit prédite, une colonne par heure (h5 ... h21),
                          plus d_hw / d_res : distances aux deux classes de voirie
  - {zone}_roads.shp      réseau routier de la zone
  - {zone}_buildings.shp  bâtiments de la zone
  - fleet_by_hour.csv     densité, composition ET DÉBIT du trafic par site et par heure
  - physical_params.csv   coefficients du noyau physique (A_hw, A_res, B, D0)
  - noise_map.csv         format plat (x, y, noise_dB) à l'heure de référence REF_HOUR
  - (+ noise_points/roads/buildings.shp : les 3 zones réunies, vue d'ensemble)
et dans outputs/hanoi/ :
  - hanoi_noise_map.csv   grille complète, 3 zones x 17 heures (livrable cartographique)

zones : hoankiem · oceanpark · vinhtuy

EMPRISE — POINT MÉTHODOLOGIQUE IMPORTANT
----------------------------------------
La grille est bornée à l'emprise des mesures de chaque site + MARGIN_M (400 m), et à rien
de plus. Les anciennes sorties du notebook 08/09 couvraient un disque de 1500 m autour de
Bach Khoa, quartier SANS AUCUNE MESURE : c'était une extrapolation vers une typologie non
vue, par un modèle (le LightGBM d'alors) dont le leave-one-site-out était négatif sur 2 sites
sur 3. Le modèle livré depuis la V2 extrapole nettement mieux, mais la règle NE CHANGE PAS :
trois typologies échantillonnées restent trois, quel que soit le score. Ces artefacts
sont archivés dans outputs/deprecated/. Ne pas réintroduire de prédiction hors emprise
mesurée sans, au minimum, un masque de domaine d'applicabilité.

Sources et statut scientifique de chaque sortie
----------------------------------------------
  grille de bruit  : PRÉDITE par le modèle HYBRIDE (v2, août 2026) entraîné sur nos 363
                     mesures terrain : un noyau physique de source linéique
                     (E = A_hw/d_hw + A_res/d_res + B) porte la prédiction, un LightGBM
                     apprend seulement le RÉSIDU sur la morphologie OSM dans 300 m et
                     l'heure cyclique. Métriques : outputs/models/metrics.json.
                     Le R² 0.45 du notebook 08 était un artefact de CV groupée sur
                     cellules de 110 m : ne plus le citer.
                     ATTENTION, ce qui vaut toujours : sous leave-one-site-out c'est le
                     NOYAU PHYSIQUE SEUL qui généralise le mieux, l'hybride complet ne
                     bat les baselines que dans les typologies échantillonnées. Les
                     contrastes spatiaux de cette grille sont à lire comme pilotés par la
                     distance aux axes routiers (cf. negative_results.md §5.z).
  trafic par heure : MESURÉ - 147 vidéos horodatées, agrégées par site et par heure.
                     DEUX grandeurs distinctes : la DENSITÉ (véh/image, détection image
                     par image) qui sert à peupler la scène GAMA, et le DÉBIT (véh/min,
                     franchissements de ligne par suivi ByteTrack) qui est la grandeur
                     physiquement liée à l'émission. Les heures sans vidéo sont
                     interpolées et signalées par measured=0.

Usage : python3 scripts/export_gama_zones.py
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, 'outputs', 'gama_inputs')
MAP_DIR = os.path.join(ROOT, 'outputs', 'hanoi')
PROC = os.path.join(ROOT, 'data', 'processed', 'hanoi')
MEASURES = os.path.join(ROOT, 'data', 'raw', 'hanoi', 'measurements.csv')
MODEL = os.path.join(ROOT, 'outputs', 'models', 'surrogate_lgbm_hanoi_direct.txt')
RESID_MODEL = os.path.join(ROOT, 'outputs', 'models', 'hybrid_residual_lgbm.txt')
PHYS_JSON = os.path.join(ROOT, 'outputs', 'models', 'hybrid_physical.json')
COUNTS = os.path.join(PROC, 'vehicle_counts.csv')

CRS_M = 'EPSG:32648'          # UTM 48N (mètres)
R = 300                        # rayon des features de morphologie
AREA_M2 = np.pi * R ** 2
GRID_M = 40                    # pas de la grille de prédiction (mètres)
MARGIN_M = 400                 # marge autour de l'emprise des mesures de chaque site
FEATURES = ['built_area_ratio', 'road_density_km_km2', 'intersection_count',
            'dist_road_m', 'hour', 'is_weekend']                       # v1 (archivé)
FEATURES2 = ['built_area_ratio', 'road_density_km_km2', 'intersection_count',
             'dist_highway_m', 'dist_residential_m',
             'hour_sin', 'hour_cos', 'is_weekend']                     # v2 (résidu hybride)
HOURS = list(range(5, 22))     # 5h-21h : fenêtre de collecte réelle
REF_HOUR = 17                  # heure de référence du format plat (pointe du soir)
SLUGS = {'Hoan Kiem lake': 'hoankiem', 'Ocean Park': 'oceanpark', 'Vinh Tuy area': 'vinhtuy'}


def load_osm():
    bld = gpd.read_file(os.path.join(PROC, 'hanoi_sites_buildings.gpkg')).to_crs(CRS_M)
    bld['area_m2'] = bld.geometry.area
    bld_c = bld.set_geometry(bld.geometry.centroid)
    G = ox.load_graphml(os.path.join(PROC, 'hanoi_sites_roads.graphml'))
    nodes, edges = ox.graph_to_gdfs(G)
    return bld, bld_c, nodes.to_crs(CRS_M).reset_index(drop=True), edges.to_crs(CRS_M).reset_index(drop=True)


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


# Séparation des voiries en deux classes acoustiques (v2, août 2026).
# Motivation : `dist_road_m` mélangeait une nationale à 4 voies et une ruelle résidentielle,
# alors que leur puissance acoustique par mètre linéaire diffère d'un ordre de grandeur.
# La distance à la source ne veut rien dire si on ne sait pas de quelle source il s'agit.
# `tertiary` est rangé avec les petites rues : en zone dense hanoïenne c'est un
# distributeur local, pas un axe traversant. Ce choix est un PARAMÈTRE du modèle, pas une
# vérité : le déplacer dans MAJOR_HW change la définition des deux variables.
MAJOR_HW = {'motorway', 'trunk', 'primary', 'secondary',
            'motorway_link', 'trunk_link', 'primary_link', 'secondary_link'}
FAR_M = 2000.0     # distance de repli quand une classe est absente de la zone


def classify_roads(edges):
    """Sépare le réseau en (grands axes, petites rues) selon le tag OSM `highway`."""
    hw = edges['highway'].apply(lambda v: v[0] if isinstance(v, list) else v)
    is_major = hw.isin(MAJOR_HW)
    return edges[is_major], edges[~is_major]


def _dist_to(pts_gdf, lines):
    """Distance de chaque point à la ligne la plus proche du jeu `lines`."""
    if lines is None or len(lines) == 0:
        return np.full(len(pts_gdf), FAR_M)
    near = gpd.sjoin_nearest(pts_gdf[['geometry']], lines[['geometry']], distance_col='d')
    d = near.groupby(near.index)['d'].min().reindex(range(len(pts_gdf))).values
    return np.nan_to_num(d, nan=FAR_M)


def morphology(pts_gdf, bld_c, nodes, edges):
    """Mêmes features que le notebook 08, plus la séparation des distances par classe
    de voirie (v2). `dist_road_m` est conservée : les protocoles de comparaison de
    scripts/evaluate_models.py la référencent comme baseline physique historique."""
    buf = gpd.GeoDataFrame({'pt_id': range(len(pts_gdf))},
                           geometry=pts_gdf.geometry.buffer(R), crs=CRS_M)
    jb = gpd.sjoin(bld_c[['geometry', 'area_m2']], buf, predicate='within')
    area_sum = jb.groupby('pt_id')['area_m2'].sum()
    built = np.minimum(np.array([area_sum.get(i, 0) for i in range(len(pts_gdf))]) / AREA_M2, 1.0)

    jr = gpd.sjoin(edges[['geometry']], buf, predicate='intersects')
    rl = jr.groupby('pt_id').apply(lambda g: g.geometry.length.sum())
    road_km = np.array([(rl.get(i, 0) / 1000) / (AREA_M2 / 1e6) for i in range(len(pts_gdf))])

    jn = gpd.sjoin(nodes[['geometry']], buf, predicate='within').groupby('pt_id').size()
    inter = np.array([jn.get(i, 0) for i in range(len(pts_gdf))])

    major, minor = classify_roads(edges)
    dist = _dist_to(pts_gdf, edges)
    dist_hw = _dist_to(pts_gdf, major)
    dist_res = _dist_to(pts_gdf, minor)

    return pd.DataFrame({'built_area_ratio': built, 'road_density_km_km2': road_km,
                         'intersection_count': inter, 'dist_road_m': dist,
                         'dist_highway_m': dist_hw, 'dist_residential_m': dist_res})


def add_time_features(feats, hour, is_weekend=0):
    """Heure en variables CYCLIQUES + weekend.

    L'heure brute 0-23 impose au modèle une discontinuité artificielle entre 23 h et 0 h,
    et force un arbre à découper une variable qui est en réalité circulaire. sin/cos sur
    24 h rétablit la continuité : 23 h et 0 h deviennent voisines dans l'espace des
    features. `hour` est conservée pour les baselines (table site x heure) qui s'en servent
    comme clé de groupement.
    """
    feats['hour'] = hour
    feats['hour_sin'] = np.sin(2 * np.pi * np.asarray(hour) / 24.0)
    feats['hour_cos'] = np.cos(2 * np.pi * np.asarray(hour) / 24.0)
    feats['is_weekend'] = is_weekend
    return feats


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
    files = glob.glob(os.path.join(ROOT, 'data', 'raw', 'hanoi', '*onstruction*.csv'))
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
                         '  -> python3 scripts/evaluate_models.py')
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

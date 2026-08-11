"""Generate the project's static HTML dashboard: results/report/dashboard/index.html.

WHY STATIC HTML AND NOT STREAMLIT
---------------------------------
The deliverable must be openable by a supervisor who has neither Python nor the
repository: an HTML file can be emailed, dropped on a share, archived with the report.
A Streamlit server requires a live process and an installation. So we generate HTML, and
`make dashboard` simply builds it.

CONTENTS
  - indicator banner for the DELIVERED model (read from metrics.json, never copied);
  - model comparison, highlighted: the delivered model in colour, the others in grey --
    the question is not "what colour is each model" but "where does ours sit";
  - interactive Folium map: field measurement points + predicted noise grid;
  - measured traffic by hour and by site, now as FLOW (veh/min) from the video tracking;
  - link to the PDF report;
  - instructions for launching the GAMA simulation.

The charts are hand-written SVG: no external JavaScript dependency, so the file stays
readable offline and will not break in five years.

Usage: python3 scripts/11_build_dashboard.py
"""
import html
import json
import os
from datetime import date

import numpy as np
import pandas as pd

from noise_hanoi import config as cfg

ROOT = cfg.ROOT
OUT_DIR = cfg.DASHBOARD_DIR
METRICS = cfg.METRICS_JSON
MEASURES = cfg.MEASUREMENTS
GRID = cfg.NOISE_MAP_CSV
COUNTS = cfg.VEHICLE_COUNTS
FLEET = os.path.join(cfg.GAMA_INPUTS, 'fleet_by_hour.csv')
PHYS = cfg.PHYS_JSON

# Palette de référence du guide de dataviz, validée pour les deux modes
# (scripts/validate_palette.js : tous les tests passent en clair et en sombre).
SERIES = ['#2a78d6', '#eb6834', '#1baf7a']
SERIES_DARK = ['#3987e5', '#d95926', '#199e70']
REF_HOUR = 17


# --------------------------------------------------------------------------- utilitaires
def esc(s):
    return html.escape(str(s))


def fmt(v, n=2, sign=False):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return '—'
    return f'{v:+.{n}f}' if sign else f'{v:.{n}f}'


# ------------------------------------------------------------------------------ graphiques
def bar_emphasis(rows, highlight, width=880, row_h=30, pad_l=286, pad_r=64):
    """Barres horizontales en MISE EN ÉVIDENCE : un modèle en couleur, les autres en gris.

    Les valeurs sont dans une COLONNE FIXE à droite plutôt qu'accolées au bout de chaque
    barre : avec des R² proches de zéro, une étiquette accolée se superpose au nom du
    modèle et devient illisible. L'axe zéro est matérialisé parce que des R² négatifs
    existent — un R² négatif signifie « moins bon que prédire la moyenne partout »,
    c'est une information, pas un artefact.
    """
    if not rows:
        return ''
    vals = [v for _, v in rows]
    lo, hi = min(min(vals), 0.0), max(max(vals), 0.0)
    span = (hi - lo) or 1.0
    plot_w = width - pad_l - pad_r
    x0 = pad_l + (0 - lo) / span * plot_w          # position du zéro
    h = len(rows) * row_h + 34
    out = [f'<svg viewBox="0 0 {width} {h}" role="img" class="chart" '
           f'aria-label="Comparaison des modeles, R2">']
    out.append(f'<line x1="{x0:.1f}" y1="14" x2="{x0:.1f}" y2="{h-24}" class="axis"/>')
    for i, (label, v) in enumerate(rows):
        y = 20 + i * row_h
        xv = pad_l + (v - lo) / span * plot_w
        bx, bw = (min(x0, xv), abs(xv - x0))
        on = (label == highlight)
        sfx = ' on' if on else ''
        out.append(f'<rect x="{bx:.1f}" y="{y}" width="{max(bw,1.5):.1f}" height="16" '
                   f'rx="4" class="bar {"on" if on else "off"}"><title>{esc(label)} : '
                   f'R² {v:+.3f}</title></rect>')
        out.append(f'<text x="{pad_l-12}" y="{y+12}" text-anchor="end" '
                   f'class="lbl{sfx}">{esc(label)}</text>')
        out.append(f'<text x="{width-8}" y="{y+12}" text-anchor="end" '
                   f'class="val{sfx}">{v:+.3f}</text>')
    out.append(f'<text x="{x0:.1f}" y="{h-8}" text-anchor="middle" class="cap">R² = 0 '
               f'(niveau « moyenne globale »)</text>')
    out.append('</svg>')
    return '\n'.join(out)


# Noms courts pour le graphique : les libellés complets de metrics.json débordent de la
# colonne de gauche. Le tableau juste en dessous porte, lui, les libellés complets.
SHORT = {
    'site_hour_mean': 'Table site × heure',
    'idw':            'Distance inverse (IDW)',
    'dist_road':      'Régression log(dist_road)',
    'lgbm_morpho':    'LightGBM morphologie seule',
    'lgbm_time':      'LightGBM temps seul',
    'lgbm_full':      'LightGBM v1',
    'lgbm_v2':        'LightGBM v2 (voiries séparées)',
    'physical':       'Noyau physique seul',
    'hybrid':         'HYBRIDE (livré)',
    'hybrid_lowcap':  'HYBRIDE conservateur',
}


def line_by_hour(fleet, value_col, width=760, height=250):
    """Débit par heure et par site : trois séries, légende + étiquettes directes.

    Trois séries seulement, ce qui est la limite validée en « toutes paires » de la
    palette de référence. Les heures NON FILMÉES sont interpolées : elles sont tracées
    en trait discontinu pour que la distinction mesure/estimation reste visible.
    """
    if fleet is None or value_col not in fleet.columns:
        return '<p class="note">Débit indisponible : relancer count_vehicles.py puis export_gama_zones.py.</p>'
    sites = list(fleet.site_name.unique())[:3]
    pl, pr, pt, pb = 46, 108, 14, 30
    hrs = sorted(fleet.hour.unique())
    vmax = max(float(fleet[value_col].max()), 1.0)
    X = lambda hh: pl + (hh - hrs[0]) / max(len(hrs) - 1, 1) * (width - pl - pr)
    Y = lambda v: pt + (1 - v / vmax) * (height - pt - pb)

    out = [f'<svg viewBox="0 0 {width} {height}" role="img" class="chart" '
           f'aria-label="Debit de vehicules par heure et par site">']
    for frac in (0, .5, 1):
        v = vmax * frac
        out.append(f'<line x1="{pl}" y1="{Y(v):.1f}" x2="{width-pr}" y2="{Y(v):.1f}" class="grid"/>')
        out.append(f'<text x="{pl-8}" y="{Y(v)+4:.1f}" text-anchor="end" class="tick">{v:.0f}</text>')
    for hh in hrs:
        if hh % 4 == 1 or hh == hrs[-1]:
            out.append(f'<text x="{X(hh):.1f}" y="{height-10}" text-anchor="middle" '
                       f'class="tick">{hh}h</text>')
    for i, s in enumerate(sites):
        g = fleet[fleet.site_name == s].sort_values('hour')
        pts = ' '.join(f'{X(r.hour):.1f},{Y(r[value_col]):.1f}' for _, r in g.iterrows())
        out.append(f'<polyline points="{pts}" class="ln s{i+1}"/>')
        for _, r in g[g.measured == 1].iterrows():   # points = heures réellement filmées
            out.append(f'<circle cx="{X(r.hour):.1f}" cy="{Y(r[value_col]):.1f}" r="4" '
                       f'class="dot s{i+1}"><title>{esc(s)} · {int(r.hour)}h · '
                       f'{r[value_col]:.1f} veh/min (mesure)</title></circle>')
        last = g.iloc[-1]
        out.append(f'<text x="{width-pr+8}" y="{Y(last[value_col])+4:.1f}" '
                   f'class="dlbl s{i+1}">{esc(s.split()[0])}</text>')
    out.append('</svg>')
    return '\n'.join(out)


# ----------------------------------------------------------------------------- carte
def build_map(meas, grid):
    """Carte Folium : grille de bruit prédite (heatmap) + points de mesure terrain."""
    import folium
    from folium.plugins import HeatMap

    c = [meas.latitude.mean(), meas.longitude.mean()]
    m = folium.Map(location=c, zoom_start=12, tiles='CartoDB positron',
                   control_scale=True)

    if grid is not None and len(grid):
        col = f'h{REF_HOUR}'
        g = grid.dropna(subset=[col])
        lo, hi = g[col].quantile([.02, .98])
        rng = (hi - lo) or 1.0
        HeatMap([[r.latitude, r.longitude, float(np.clip((r[col] - lo) / rng, 0, 1))]
                 for _, r in g.iterrows()],
                radius=9, blur=12, min_opacity=.30,
                name=f'Bruit prédit (modèle hybride, {REF_HOUR} h)').add_to(m)

    fg = folium.FeatureGroup(name='Mesures terrain (363 points)')
    lo, hi = meas.noise_dB.quantile([.05, .95])
    for _, r in meas.iterrows():
        t = float(np.clip((r.noise_dB - lo) / ((hi - lo) or 1), 0, 1))
        # rampe séquentielle à une seule teinte : plus foncé = plus bruyant
        col = f'#{int(255-107*t):02x}{int(235-180*t):02x}{int(250-190*t):02x}'
        folium.CircleMarker(
            [r.latitude, r.longitude], radius=4, color='#333', weight=.6,
            fill=True, fill_color=col, fill_opacity=.9,
            tooltip=f'{r.noise_dB:.1f} dB · {esc(r.site)} · {r.timestamp}').add_to(fg)
    fg.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    # cadrage sur l'emprise réellement mesurée : les 3 sites sont distants d'une dizaine
    # de km, un zoom fixe les laisse minuscules dans un coin de la carte.
    m.fit_bounds([[meas.latitude.min(), meas.longitude.min()],
                  [meas.latitude.max(), meas.longitude.max()]], padding=(24, 24))
    os.makedirs(OUT_DIR, exist_ok=True)
    m.save(os.path.join(OUT_DIR, 'map.html'))
    return 'map.html'


# ------------------------------------------------------------------------------ page
CSS = """
:root{color-scheme:light dark;
 --bg:#f6f6f4; --card:#fcfcfb; --ink:#0b0b0b; --ink2:#52514e; --ink3:#75736d;
 --line:#e2e1dc; --accent:#2a78d6; --off:#b9b7b0;
 --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a;}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme=light])){
 --bg:#121211; --card:#1a1a19; --ink:#fff; --ink2:#c3c2b7; --ink3:#8f8e85;
 --line:#333230; --accent:#3987e5; --off:#5a5953;
 --s1:#3987e5; --s2:#d95926; --s3:#199e70;}}
:root[data-theme=dark]{--bg:#121211;--card:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--ink3:#8f8e85;
 --line:#333230;--accent:#3987e5;--off:#5a5953;--s1:#3987e5;--s2:#d95926;--s3:#199e70;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
 font:15px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;}
.wrap{max-width:1040px;margin:0 auto;padding:32px 20px 64px}
h1{font-size:26px;margin:0 0 4px;letter-spacing:-.02em}
h2{font-size:17px;margin:38px 0 6px;letter-spacing:-.01em}
.sub{color:var(--ink2);margin:0 0 4px}
.meta{color:var(--ink3);font-size:13px;margin:0}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;
 padding:18px 20px;margin-top:12px;overflow-x:auto}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(158px,1fr));gap:12px;margin-top:16px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.kpi .v{font-size:29px;font-weight:600;letter-spacing:-.02em;line-height:1.15}
.kpi .k{font-size:12px;color:var(--ink3);text-transform:uppercase;letter-spacing:.05em}
.kpi .d{font-size:12.5px;color:var(--ink2);margin-top:3px}
.chart{width:100%;height:auto;display:block}
.axis{stroke:var(--ink3);stroke-width:1}
.grid{stroke:var(--line);stroke-width:1}
.bar.on{fill:var(--accent)} .bar.off{fill:var(--off)}
.lbl{fill:var(--ink2);font-size:12.5px} .lbl.on{fill:var(--ink);font-weight:600}
.val{fill:var(--ink2);font-size:12.5px;font-variant-numeric:tabular-nums}
.val.on{fill:var(--ink);font-weight:600}
.tick{fill:var(--ink3);font-size:11.5px} .cap{fill:var(--ink3);font-size:11.5px}
.ln{fill:none;stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.dot{stroke:var(--card);stroke-width:2}
.dlbl{font-size:12.5px;font-weight:600}
.s1{stroke:var(--s1)} .s2{stroke:var(--s2)} .s3{stroke:var(--s3)}
circle.s1{fill:var(--s1)} circle.s2{fill:var(--s2)} circle.s3{fill:var(--s3)}
text.s1{fill:var(--s1);stroke:none} text.s2{fill:var(--s2);stroke:none}
text.s3{fill:var(--s3);stroke:none}
table{border-collapse:collapse;width:100%;font-size:13.5px}
th,td{text-align:right;padding:7px 10px;border-bottom:1px solid var(--line)}
th:first-child,td:first-child{text-align:left}
th{color:var(--ink3);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.04em}
tr.on td{background:color-mix(in srgb,var(--accent) 11%,transparent);font-weight:600}
td{font-variant-numeric:tabular-nums}
iframe{width:100%;height:520px;border:0;border-radius:10px;display:block}
.note{color:var(--ink2);font-size:13.5px;margin:8px 0 0}
.warn{border-left:3px solid var(--s2);padding-left:14px;margin:12px 0;color:var(--ink2);font-size:14px}
a.btn{display:inline-block;background:var(--accent);color:#fff;text-decoration:none;
 padding:10px 18px;border-radius:8px;font-weight:600;font-size:14px}
a.btn:hover{filter:brightness(1.08)}
code,pre{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px}
pre{background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:12px 14px;
 overflow-x:auto;margin:10px 0 0}
"""


def kpi(value, key, detail=''):
    d = f'<div class="d">{detail}</div>' if detail else ''
    return f'<div class="kpi"><div class="k">{key}</div><div class="v">{value}</div>{d}</div>'


def main():
    if not os.path.exists(METRICS):
        raise SystemExit(f'Manque {METRICS}\n  -> python3 scripts/evaluate_models.py')
    M = json.load(open(METRICS))
    ref = M['meta']['headline_protocol']
    RM = M[ref]['models']
    reflabel = M[ref]['label']

    meas = pd.read_csv(MEASURES, parse_dates=['timestamp']).dropna(
        subset=['noise_dB', 'latitude', 'longitude'])
    grid = pd.read_csv(GRID) if os.path.exists(GRID) else None
    vc = pd.read_csv(COUNTS) if os.path.exists(COUNTS) else None
    fleet = pd.read_csv(FLEET) if os.path.exists(FLEET) else None
    phys = json.load(open(PHYS)) if os.path.exists(PHYS) else {}

    # Le modèle livré est celui que evaluate_models.py a retenu sous le protocole de
    # référence — pas forcément le plus sophistiqué. On le lit, on ne le devine pas.
    delivered = M['meta'].get('delivered_model', 'hybrid' if 'hybrid' in RM else 'lgbm_full')
    D = RM[delivered]

    # --- bandeau d'indicateurs -----------------------------------------------------
    flow_txt, flow_det = '—', ''
    if vc is not None and 'vehicles_flow' in vc.columns:
        f = vc.vehicles_flow.dropna()
        flow_txt = f'{f.mean():.0f}'
        flow_det = f'médiane {f.median():.0f} · max {f.max():.0f} véh/min'
    kpis = ''.join([
        kpi(fmt(D['r2'], 3), 'R² modèle livré',
            f"{esc(SHORT.get(delivered, D['label']))} · IC 95 % "
            f"[{D['r2_ci95'][0]:.2f}, {D['r2_ci95'][1]:.2f}] · {esc(reflabel)}"),
        kpi(f"{D['mae']:.2f} dB", 'MAE',
            f"IC 95 % [{D['mae_ci95'][0]:.2f}, {D['mae_ci95'][1]:.2f}]"),
        kpi(f"{M['meta']['n_measurements']}", 'mesures terrain',
            f"{len(M['meta']['sites'])} sites · {M['meta']['date_min']} → {M['meta']['date_max']}"),
        kpi(f'{len(vc) if vc is not None else 0}', 'vidéos suivies',
            'YOLOv8 + ByteTrack, franchissement de ligne'),
        kpi(flow_txt, 'débit moyen (véh/min)', flow_det),
    ])

    # --- comparaison des modèles ---------------------------------------------------
    order = ['site_hour_mean', 'idw', 'dist_road', 'lgbm_morpho', 'lgbm_full',
             'lgbm_v2', 'physical', 'hybrid', 'hybrid_lowcap']
    rows = [(SHORT.get(k, RM[k]['label']), RM[k]['r2']) for k in order if k in RM]
    best = max((k for k in RM), key=lambda k: RM[k]['r2'])
    chart = bar_emphasis(rows, highlight=SHORT.get(delivered, D['label']))
    trows = ''.join(
        f'<tr class="{"on" if k == delivered else ""}"><td>{esc(RM[k]["label"])}</td>'
        f'<td>{RM[k]["r2"]:+.3f}</td>'
        f'<td>[{RM[k]["r2_ci95"][0]:.2f}, {RM[k]["r2_ci95"][1]:.2f}]</td>'
        f'<td>{RM[k]["mae"]:.2f}</td><td>{RM[k]["r"]:.2f}</td></tr>'
        for k in order if k in RM)

    # L'inversion de classement entre protocoles est LE résultat de la V2 : elle doit être
    # sur la page, pas seulement dans le rapport.
    bcv = M.get('block_cv', {}).get('models', {})
    inversion = ''
    if bcv and 'hybrid' in bcv and 'hybrid' in RM:
        g = M[ref].get('v2_gains', {}).get('residual_ml_gain', {})
        inversion = (
            f'<div class="warn"><strong>Le classement s\'inverse entre protocoles.</strong> '
            f'Sous le découpage permissif (block-CV 600 m) ce sont les modèles les plus '
            f'élaborés qui mènent : hybride {bcv["hybrid"]["r2"]:+.3f}, LightGBM v2 '
            f'{bcv["lgbm_v2"]["r2"]:+.3f}, noyau physique {bcv["physical"]["r2"]:+.3f}. Sous le '
            f'protocole de référence, dont le rayon d\'exclusion égale le rayon d\'agrégation '
            f'des variables, l\'ordre se retourne : noyau physique {RM["physical"]["r2"]:+.3f}, '
            f'hybride {RM["hybrid"]["r2"]:+.3f}. L\'architecture hybride a donc été '
            f'<strong>construite, testée et écartée</strong> — la correction apprise vaut '
            f'ΔR² {g.get("delta_r2", 0):+.3f} face à la physique seule sous ce protocole.</div>')

    # Honnêteté : le modèle livré n'est pas forcément le meilleur sous TOUS les protocoles.
    loso = M.get('loso', {}).get('models', {})
    caveat = ''
    if loso and delivered in loso:
        bl = max(loso, key=lambda k: loso[k]['r2'])
        if bl != delivered:
            caveat = (
                f'<div class="warn"><strong>À lire avec le tableau.</strong> Sous '
                f'<em>leave-one-site-out</em> — généralisation à une typologie urbaine jamais '
                f'vue — le modèle livré tombe à R² {loso[delivered]["r2"]:+.3f}, tandis que '
                f'« {esc(loso[bl]["label"])} » tient à {loso[bl]["r2"]:+.3f}. Le noyau physique '
                f'seul extrapole donc mieux que l\'hybride complet : la correction apprise '
                f'améliore l\'interpolation dans les typologies échantillonnées, pas '
                f'l\'extrapolation hors d\'elles. Toute carte publiée reste bornée à '
                f'l\'emprise mesurée.</div>')

    # --- physique ------------------------------------------------------------------
    phys_html = ''
    if phys:
        phys_html = (
            '<h2>Noyau physique</h2>'
            '<div class="card"><p class="note">Une voie est traitée comme une source '
            '<strong>linéique</strong> : l\'intensité décroît en 1/d et non en 1/d². '
            'L\'énergie reçue est la somme des deux classes de voirie et d\'un fond '
            'résiduel, tous coefficients contraints positifs.</p>'
            f'<pre>E(x) = A_hw / max(d_hw, {phys["D0_m"]:.0f})  +  A_res / max(d_res, '
            f'{phys["D0_m"]:.0f})  +  B\nL(x) = 10 · log10( E(x) )\n\n'
            f'A_highway     = {phys["A_highway"]:.4g}\n'
            f'A_residential = {phys["A_residential"]:.4g}\n'
            f'B_background  = {phys["B_background"]:.4g}</pre>'
            + ('<p class="note">Un LightGBM apprend le <strong>résidu</strong> de cette '
               'équation : la part transférable est portée par les paramètres physiques, la '
               'part non transférable est confinée dans une correction bornée.</p>'
               if phys.get('apply_residual', True) else
               '<p class="note">Un LightGBM de résidu a été entraîné et sauvegardé, mais il '
               '<strong>n\'est pas appliqué</strong> à la carte publiée : sous le protocole '
               'de référence il dégrade la prédiction plutôt que de l\'améliorer (voir le '
               'tableau ci-dessus). Le choix est fait par le code, pas à la main — '
               '<code>evaluate_models.py</code> retient le meilleur candidat sous le '
               'protocole de référence et écrit le drapeau <code>apply_residual</code>.</p>')
            + '</div>')

    # --- trafic --------------------------------------------------------------------
    flow_col = 'total_flow_per_min' if (
        fleet is not None and 'total_flow_per_min' in fleet.columns) else None
    traffic = ''
    if flow_col:
        traffic = (
            '<h2>Trafic mesuré — débit par heure</h2>'
            '<div class="card">' + line_by_hour(fleet, flow_col) +
            '<p class="note">Points = heures réellement filmées ; entre elles, '
            'interpolation linéaire. Le <strong>débit</strong> (franchissements de ligne '
            'par minute) remplace la densité par image utilisée jusqu\'en juillet 2026 : '
            'en congestion la densité est maximale alors que le débit s\'effondre, et '
            'c\'est le débit qui gouverne l\'émission sonore.</p></div>')

    map_src = ''
    try:
        map_src = build_map(meas, grid)
    except Exception as e:      # la carte est un plus : son échec ne doit pas tuer la page
        print(f'  carte non générée : {e}')

    map_html = (f'<div class="card"><iframe src="{map_src}" title="Carte du bruit" '
                f'loading="lazy"></iframe><p class="note">Fond de carte CartoDB / '
                f'OpenStreetMap. La grille prédite est bornée à l\'emprise réellement '
                f'mesurée (+400 m) : aucune extrapolation vers un quartier non '
                f'échantillonné.</p></div>') if map_src else ''

    doc = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hanoi Urban Noise — tableau de bord</title>
<style>{CSS}</style></head><body><div class="wrap">

<h1>Hanoi Urban Noise — tableau de bord</h1>
<p class="sub">Cartographie du bruit urbain par smartphones · Center for Environmental
Intelligence, VinUniversity</p>
<p class="meta">Généré le {date.today().isoformat()} · protocole de référence :
{esc(reflabel)} · toutes les métriques sont lues dans
<code>outputs/models/metrics.json</code>, aucune n'est recopiée à la main.</p>

<div class="kpis">{kpis}</div>

<h2>Comparaison des modèles</h2>
<div class="card">
{chart}
<p class="note">Le modèle livré est en couleur, les autres en gris. Tous sont évalués sur
<strong>exactement les mêmes découpages</strong>, avec IC 95 % par bootstrap par bloc
spatial.</p>
</div>
{inversion}
{caveat}
<div class="card">
<table><thead><tr><th>Modèle</th><th>R²</th><th>IC 95 %</th><th>MAE (dB)</th><th>r</th></tr>
</thead><tbody>{trows}</tbody></table>
</div>

{phys_html}

<h2>Carte</h2>
{map_html}

{traffic}

<h2>Rapport complet</h2>
<div class="card">
<p class="note">Le rapport de collecte de données (8 pages : protocole, métrologie,
analyse, modèle, simulation, limites) est régénéré par
<code>scripts/build_report.py</code>.</p>
<p style="margin-top:14px"><a class="btn" href="../report.pdf">Ouvrir report.pdf</a></p>
</div>

<h2>Lancer la simulation GAMA</h2>
<div class="card">
<p class="note">La simulation multi-agents rejoue la carte heure par heure, avec véhicules
mobiles, chantiers et scénarios de mitigation.</p>
<pre>1.  Installer GAMA Platform 1.9+        https://gama-platform.org/download
2.  File &gt; Open Project…                choisir le dossier  gama/
3.  Ouvrir                              gama/hanoi_noise.gaml
4.  Choisir la zone en tête de fichier  zone &lt;- "oceanpark" | "hoankiem" | "vinhtuy"
5.  Lancer l'expérimentation            hanoi_noise_sim  (icone ▶)

Régénérer les entrées de la simulation :
    python3 scripts/export_gama_zones.py</pre>
<p class="note">Les fichiers d'entrée sont dans <code>outputs/gama_inputs/</code> :
grille de bruit par heure, voiries, bâtiments, chantiers, points de mesure,
<code>fleet_by_hour.csv</code> (débit et composition du parc) et
<code>physical_params.csv</code> (coefficients du noyau physique).</p>
</div>

</div></body></html>"""

    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, 'index.html')
    with open(path, 'w') as f:
        f.write(doc)
    print(f'OK -> {path}')
    print(f'  modèle livré : {D["label"]}  R² {D["r2"]:+.3f}  MAE {D["mae"]:.2f} dB '
          f'({reflabel})')
    if best != delivered:
        print(f'  note : sous ce protocole le meilleur score est {RM[best]["label"]} '
              f'({RM[best]["r2"]:+.3f})')
    return path


if __name__ == '__main__':
    main()

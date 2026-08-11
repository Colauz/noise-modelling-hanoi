"""Carte interactive des points de mesure : outputs/hanoi/hanoi_field_points.html.

SOURCE DE VÉRITÉ UNIQUE de la carte terrain. Utilisable de 2 façons :
  - en script  : `python3 scripts/build_field_map.py`
  - en module  : `import build_field_map as bfm; m = bfm.build_map(df)`
                 (c'est ce que fait le notebook 07)

Contenu :
  - un cercle par mesure, coloré par niveau (vert <60, orange 60-70,
    rouge 70-80, rouge foncé >80 ; la limite QCVN jour est 70 dB)
  - popup au clic : toutes les infos pertinentes du point (les champs vides
    ne sont pas affichés)
  - une couche par site (cochable) + couche chantiers (marqueurs bleus)
  - légende + cadrage automatique sur l'ensemble des points
"""
import glob
import os

import folium
import pandas as pd

from noise_hanoi import config as cfg

ROOT = cfg.ROOT
RAW_DIR = cfg.PROCESSED
OUT = cfg.FIELD_MAP_HTML

BINS = [(60, '#1e8449'), (70, '#e67e22'), (80, '#c0392b'), (999, '#7b241c')]


def color(db):
    for lim, c in BINS:
        if db < lim:
            return c


def fmt(v, suffix=''):
    """Valeur lisible ou None si vide (les None sont omis du popup)."""
    if v is None or (isinstance(v, float) and pd.isna(v)) or str(v) in ('nan', 'NaT', ''):
        return None
    if isinstance(v, float) and v == int(v):
        v = int(v)
    return f'{v}{suffix}'


def popup_html(r):
    head = f"{r.noise_dB:.0f} dB · {r.get('class', '')}"
    rows = []

    def add(label, value):
        if value is not None:
            rows.append(f'<tr><td style="color:#666;padding:1px 8px 1px 0">{label}</td>'
                        f'<td><b>{value}</b></td></tr>')

    ts = r.get('timestamp')
    add('Site', fmt(r.get('site')))
    if pd.notna(ts):
        add('Time', f"{ts:%a %d %b, %H:%M}" + (' (weekend)' if ts.dayofweek >= 5 else ''))
    add('Collector', fmt(r.get('collector')))
    add('Distance to road', fmt(r.get('dist_to_road')))
    add('Distance to source', fmt(r.get('dist_to_source_m'), ' m'))
    add('Construction nearby', fmt(r.get('construction_nearby')))
    counts = [(k, r.get(f'count_{k}')) for k in ('motorbikes', 'cars', 'heavy', 'ev')]
    counts = [f'{fmt(v)} {k}' for k, v in counts if fmt(v) is not None]
    add('Vehicles (20-30 s)', ' · '.join(counts) if counts else None)
    weather = [w for w in (fmt(r.get('temperature_2m'), ' °C'),
                           fmt(r.get('wind_speed_10m'), ' km/h wind'),
                           fmt(r.get('precipitation'), ' mm rain')) if w]
    add('Weather (hourly)', ' · '.join(weather) if weather else None)
    add('GPS accuracy', fmt(r.get('accuracy'), ' m'))
    add('Note', fmt(r.get('note')))

    return (f'<div style="font-family:system-ui,Arial;font-size:12px;min-width:230px">'
            f'<div style="background:{color(r.noise_dB)};color:white;padding:5px 9px;'
            f'font-weight:bold;font-size:14px;border-radius:4px 4px 0 0">{head}</div>'
            f'<table style="margin:6px 2px">{"".join(rows)}</table></div>')


def load_construction():
    files = glob.glob(f'{RAW_DIR}/*onstruction*.csv')
    if not files:
        return None
    raw = pd.read_csv(max(files), sep=';')
    if len(raw.columns) == 1:
        raw = pd.read_csv(max(files), sep=',')

    def col(*keys):
        for k in keys:
            for c in raw.columns:
                if k.lower() in c.lower():
                    return raw[c]
        return None

    return pd.DataFrame({
        'latitude':  pd.to_numeric(col('_latitude')),
        'longitude': pd.to_numeric(col('_longitude')),
        'site_type': col('type of site', 'site_type'),
        'activity':  col('activity'),
        'descr':     col('description'),
    }).dropna(subset=['latitude', 'longitude'])


def build_map(df, out=OUT):
    m = folium.Map(location=[df.latitude.mean(), df.longitude.mean()],
                   zoom_start=15, tiles='OpenStreetMap')

    for site, g in df.groupby('site'):
        fg = folium.FeatureGroup(name=f'{site} (n={len(g)})')
        for _, r in g.iterrows():
            folium.CircleMarker(
                [r.latitude, r.longitude], radius=7,
                color=color(r.noise_dB), fill=True, fill_opacity=0.9, weight=1,
                popup=folium.Popup(popup_html(r), max_width=320),
                tooltip=f"{r.noise_dB:.0f} dB · {r.get('class', '')} · {r.timestamp:%d/%m %H:%M}",
            ).add_to(fg)
        fg.add_to(m)

    constr = load_construction()
    if constr is not None and len(constr):
        fg = folium.FeatureGroup(name=f'Construction sites (n={len(constr)})')
        for _, r in constr.iterrows():
            info = ' · '.join(x for x in (fmt(r.site_type), fmt(r.activity)) if x)
            folium.Marker(
                [r.latitude, r.longitude],
                icon=folium.Icon(color='blue', icon='wrench', prefix='fa'),
                popup=folium.Popup(
                    f'<b>Construction site</b><br>{info}<br>{fmt(r.descr) or ""}', max_width=280),
                tooltip='Construction site',
            ).add_to(fg)
        fg.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    pts = df[['latitude', 'longitude']].values.tolist()
    if constr is not None and len(constr):
        pts += constr[['latitude', 'longitude']].values.tolist()
    m.fit_bounds(pts, padding=(30, 30))

    legend = f'''<div style="position:fixed;bottom:20px;left:20px;z-index:9999;background:white;
    padding:10px 12px;border:1px solid #888;border-radius:6px;font-size:13px;font-family:system-ui,Arial">
    <b>Field measurements (n={len(df)})</b><br>
    <span style="color:{BINS[0][1]}">&#9679;</span> &lt; 60 dB &nbsp;
    <span style="color:{BINS[1][1]}">&#9679;</span> 60-70 &nbsp;
    <span style="color:{BINS[2][1]}">&#9679;</span> 70-80 &nbsp;
    <span style="color:{BINS[3][1]}">&#9679;</span> &gt; 80<br>
    <span style="color:#666">QCVN day limit: 70 dB · click a point for details</span></div>'''
    m.get_root().html.add_child(folium.Element(legend))

    m.save(out)
    return m


def main():
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import prepare_field_data as pfd
    df = pfd.build_dataframe()
    build_map(df)
    print(f'OK -> {OUT}  ({len(df)} points)')


if __name__ == '__main__':
    main()

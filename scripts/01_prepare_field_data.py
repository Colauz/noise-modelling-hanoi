"""
Prepare the Hanoi field data: raw Kobo export -> a clean measurements.csv.

SINGLE SOURCE OF TRUTH for field cleaning. Usable two ways:
  - as a script: `python3 scripts/01_prepare_field_data.py`  (rebuilds measurements.csv)
  - as a module: `import importlib.util` ... `build_dataframe()`
                 (notebook 07 does this, so there is no duplicated logic)

Rerun after every new Kobo export:
    1. drop the CSV into data/raw/kobo/
    2. python3 scripts/01_prepare_field_data.py
    3. then `make features && make models`

What it does:
  - detects the columns whatever the Kobo export mode (names / labels)
  - normalises the distance bands (old d_0_10... codes of form v1)
  - HONEST backfill of the v2 fields on older points:
      * phone_orientation = horizontal, mic_to_source = towards  (the actual protocol)
      * construction_nearby DERIVED from the noise category
      * dist_to_source_m and vehicle counts: left EMPTY when not measured
        (a NaN means "not measured"; a filler value would pollute the analyses)
  - cleaning (same rules as Sunbird notebook 02)
  - per-collector calibration (CALIBRATION_OFFSET, currently all 0.0)
  - Open-Meteo weather enrichment (degrades gracefully if the API is unreachable)
  - writes data/processed/measurements.csv

The raw Kobo file is NEVER modified: it is read, and the clean result is written to
a separate file. Paths come from noise_hanoi.config.
"""
import glob
import os
import time

import numpy as np
import pandas as pd
import requests

# Paths anchored on the repository root (works from the root OR from notebooks/)
from noise_hanoi import config as cfg

ROOT = cfg.ROOT
RAW_DIR = cfg.KOBO_DIR
OUT = cfg.MEASUREMENTS

CALIBRATION_OFFSET = {'laurian': 0.0, 'lucas': 0.0, 'quang': 0.0}
# Centres of the 3 study areas: the site is reassigned to the centre nearest the
# GPS fix (the form label is sometimes left unchanged between areas - 1 case on 30/06).
# The sites are kilometres apart, so the assignment is unambiguous.
SITE_CENTERS = {
    'Hoan Kiem lake': (21.0317, 105.8514),
    'Vinh Tuy area':  (20.9928, 105.8690),
    'Ocean Park':     (20.9922, 105.9441),
}
DIST_NORM = {
    'd_0_10': '0-10 m (v1)', 'd_0_2': '0-2 m', 'd_2_10': '2-10 m',
    'd_10_30': '10-30 m', 'd_30_60': '30-60 m', 'd_60plus': '> 60 m',
}
MODEL_COLS = ['latitude', 'longitude', 'noise_dB', 'timestamp', 'class', 'site', 'hour', 'is_weekend']
EXTRA_COLS = ['temperature_2m', 'wind_speed_10m', 'precipitation', 'dist_to_road',
              'count_motorbikes', 'count_cars', 'count_heavy', 'count_ev',
              'construction_nearby', 'dist_to_source_m']


def latest_export():
    # exclude measurements.csv (our own output) and the construction register (separate form)
    files = [f for f in glob.glob(f'{RAW_DIR}/*.csv')
             if not f.endswith('measurements.csv') and 'construction' not in f.lower()]
    if not files:
        raise SystemExit(f'No Kobo export in {RAW_DIR}/ (measurements.csv aside).')
    return max(files)  # the filename carries the date, so max = most recent


def load_raw(path):
    raw = pd.read_csv(path, sep=';')
    if len(raw.columns) == 1:  # wrong separator
        raw = pd.read_csv(path, sep=',')
    return raw


def col(raw, *keys):
    """First column of raw whose name contains one of the keys (case-insensitive)."""
    for k in keys:
        for c in raw.columns:
            if k.lower() in c.lower():
                return raw[c]
    return None


def standardize(raw):
    df = pd.DataFrame({
        'timestamp':  pd.to_datetime(col(raw, 'start'), format='ISO8601', utc=True)
                        .dt.tz_convert('Asia/Bangkok').dt.tz_localize(None),
        'latitude':   pd.to_numeric(col(raw, '_latitude', 'location_latitude')),
        'longitude':  pd.to_numeric(col(raw, '_longitude', 'location_longitude')),
        'altitude':   pd.to_numeric(col(raw, '_altitude', 'location_altitude')),
        'accuracy':   pd.to_numeric(col(raw, '_precision', 'location_precision')),
        'noise_dB':   pd.to_numeric(col(raw, 'noise level', 'noise_db')),
        'class':      col(raw, 'noise category', 'noise_class'),
        'site':       col(raw, 'study site', 'site'),
        'collector':  col(raw, 'who is collecting', 'collector'),
        'dist_to_road': col(raw, 'distance to nearest road', 'dist_to_road'),
        'note':       col(raw, 'note'),
        'phone_orientation': col(raw, 'phone held', 'phone_orientation'),
        'mic_to_source':     col(raw, 'mic relative', 'mic_to_source'),
        'dist_to_source_m':  pd.to_numeric(col(raw, 'distance to the main source', 'dist_to_source_m'), errors='coerce'),
        'count_motorbikes':  pd.to_numeric(col(raw, 'motorbikes passing', 'count_motorbikes'), errors='coerce'),
        'count_cars':        pd.to_numeric(col(raw, 'cars passing', 'count_cars'), errors='coerce'),
        'count_heavy':       pd.to_numeric(col(raw, 'buses / trucks', 'count_heavy'), errors='coerce'),
        'count_ev':          pd.to_numeric(col(raw, 'electric vehicles', 'count_ev'), errors='coerce'),
        'construction_nearby': col(raw, 'construction/demolition audible', 'construction_nearby'),
    })
    df['collector'] = df['collector'].str.strip().str.lower()
    df['dist_to_road'] = df['dist_to_road'].replace(DIST_NORM)

    # honest backfill (see docstring)
    df['phone_orientation'] = df['phone_orientation'].fillna('horizontal')
    df['mic_to_source'] = df['mic_to_source'].fillna('towards')
    is_constr = df['class'].astype(str).str.contains('construction', case=False, na=False)
    df['construction_nearby'] = df['construction_nearby'].fillna(
        pd.Series(np.where(is_constr, 'yes', 'no'), index=df.index))
    return df


def fix_site_by_gps(df):
    """Reassign `site` to the area centre nearest the GPS fix (corrects the
    site field left unchanged in the form). Reports every correction."""
    names = list(SITE_CENTERS)
    centers = np.array([SITE_CENTERS[n] for n in names])
    d2 = ((df['latitude'].values[:, None] - centers[:, 0]) ** 2 +
          (df['longitude'].values[:, None] - centers[:, 1]) ** 2)
    gps_site = pd.Series([names[i] for i in d2.argmin(axis=1)], index=df.index)
    changed = df['site'].notna() & (df['site'] != gps_site)
    for _, r in df[changed].iterrows():
        print(f"  site corrected from GPS: {r['site']} -> {gps_site[r.name]} "
              f"({r['timestamp']}, {r['noise_dB']:.1f} dB)")
    df['site'] = gps_site
    return df


def clean(df):
    df = df.dropna(subset=['noise_dB', 'latitude', 'longitude'])
    df = df.drop_duplicates(subset=['collector', 'timestamp'])
    df = df[df['accuracy'].isna() | (df['accuracy'] < 50)]
    df = df[(df['noise_dB'] >= 20) & (df['noise_dB'] <= 120)].copy()
    df['noise_dB'] = df['noise_dB'] + df['collector'].map(CALIBRATION_OFFSET).fillna(0)
    df['hour'] = df['timestamp'].dt.hour
    df['is_weekend'] = df['timestamp'].dt.dayofweek.isin([5, 6]).astype(int)
    df['day_of_week'] = df['timestamp'].dt.day_name()
    return df


def add_weather(df):
    def get(lat, lon, date_str, retries=3):
        for _ in range(retries):
            try:
                r = requests.get('https://archive-api.open-meteo.com/v1/archive', params={
                    'latitude': lat, 'longitude': lon,
                    'start_date': date_str, 'end_date': date_str,
                    'hourly': 'temperature_2m,wind_speed_10m,precipitation,relative_humidity_2m',
                    'timezone': 'Asia/Bangkok'}, timeout=30)
                h = r.json()['hourly']
                return pd.DataFrame(h).assign(time=lambda x: pd.to_datetime(x['time']))
            except Exception:
                time.sleep(5)
        return None

    frames = []
    for (date, site), g in df.groupby([df['timestamp'].dt.date, 'site']):
        w = get(g['latitude'].mean(), g['longitude'].mean(), str(date))
        if w is not None:
            w['site'] = site
            frames.append(w)
    if not frames:
        print('  (weather: API unreachable, skipped - rerun later)')
        return df
    weather = pd.concat(frames)
    df['time_h'] = df['timestamp'].dt.floor('h')
    df = df.merge(weather.rename(columns={'time': 'time_h'}), on=['time_h', 'site'], how='left')
    return df.drop(columns='time_h')


def build_dataframe(path=None, weather=True):
    """Full pipeline: raw export -> a clean, enriched DataFrame (in memory).
    This is the entry point used by notebook 07."""
    path = path or latest_export()
    df = fix_site_by_gps(clean(standardize(load_raw(path))))
    if weather:
        df = add_weather(df)
    return df


def save_measurements(df, out=OUT):
    """Write the column subset consumed downstream (plus analysis extras)."""
    cols = MODEL_COLS + [c for c in EXTRA_COLS if c in df.columns]
    df[cols].to_csv(out, index=False)
    return out


def main():
    path = latest_export()
    print(f'Export : {os.path.basename(path)}')
    n0 = len(load_raw(path))
    df = build_dataframe(path)
    save_measurements(df)
    print(f'{n0} raw -> {len(df)} clean measurements -> {OUT}')
    print(f'  sites              : {df["site"].value_counts().to_dict()}')
    print(f'  with vehicle counts: {df["count_motorbikes"].notna().sum()}')
    print(f'  construction (reported/derived): {(df["construction_nearby"].astype(str).str.lower() == "yes").sum()}')
    print(f'  median / min / max dB: {df.noise_dB.median():.0f} / {df.noise_dB.min():.0f} / {df.noise_dB.max():.0f}')


if __name__ == '__main__':
    main()

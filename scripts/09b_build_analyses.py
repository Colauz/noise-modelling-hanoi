#!/usr/bin/env python3
"""Build the five field-analysis figures.

    python3 scripts/09b_build_analyses.py

Reads   data/processed/measurements.csv
Writes  results/figures/analyse_1_horaire.png   hourly cycle by site
        results/figures/analyse_2_jour.png      weekday profile
        results/figures/analyse_3_type.png      transport against construction
        results/figures/analyse_4_depassement.png  QCVN exceedance frequency by hour
        results/figures/analyse_5_meteo.png     weather against level

Why this script exists
----------------------
Until August 2026 these five figures were produced by cells of
`notebooks/07_hanoi_field_data.ipynb`, so they sat in results/ looking like
reproducible output while nothing in the pipeline could rebuild them. Same defect
as the OSM features before 03_build_features.py existed. The computation is
unchanged and was verified figure by figure against the notebook's output; only
the labels are translated.

The numbered suffix is 09b because this is a second figure producer alongside
09_build_field_map.py, and renumbering the whole chain would break every reference
to the existing names.

Thresholds: QCVN 26:2010/BTNMT only. The WHO values (53/45) were removed
deliberately -- they are L_den / L_night, ANNUAL averages with evening and night
penalties, not comparable to our 25 s samples. See docs/metrology.md.
"""

import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from noise_hanoi import config as cfg

QCVN_D, QCVN_N = 70, 55
DAY_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
DAY_SHORT = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


def _out(name):
    return os.path.join(cfg.FIGURES, name)


def hourly_cycle(df):
    fig, ax = plt.subplots(figsize=(11, 5))
    for s in df.site.unique():
        g = df[df.site == s].groupby('hour')['noise_dB'].median()
        ax.plot(g.index, g.values, marker='o', lw=2, label=s)
    ax.axhline(QCVN_D, ls='--', c='red', alpha=.7, label='QCVN day 70')
    ax.axhline(QCVN_N, ls='--', c='darkred', alpha=.7, label='QCVN night 55')
    ax.set_xlabel('Hour'); ax.set_ylabel('$L_{A,25s}$ median (dB)')
    ax.set_xticks(range(0, 24, 2))
    ax.set_title('Hourly noise cycle by site'); ax.legend(fontsize=8, ncol=2); ax.grid(alpha=.3)
    plt.tight_layout(); plt.savefig(_out('analyse_1_horaire.png'), dpi=130); plt.close(fig)


def weekday_profile(df):
    df = df.assign(dayname=df['timestamp'].dt.day_name())
    fig, ax = plt.subplots(figsize=(11, 5))
    for s in df.site.unique():
        g = df[df.site == s].groupby('dayname')['noise_dB'].median().reindex(DAY_ORDER)
        ax.plot(range(7), g.values, marker='s', lw=2, label=s)
    ax.axhline(QCVN_D, ls='--', c='red', alpha=.7, label='QCVN day 70')
    ax.set_xticks(range(7)); ax.set_xticklabels(DAY_SHORT); ax.set_ylabel('median dB')
    ax.set_title('Profile by day of week'); ax.legend(fontsize=8); ax.grid(alpha=.3)
    plt.tight_layout(); plt.savefig(_out('analyse_2_jour.png'), dpi=130); plt.close(fig)


def transport_vs_construction(df):
    df = df.assign(is_constr=df['class'].astype(str).str.contains('construction', case=False))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 5))
    data = [df[~df.is_constr].noise_dB.dropna(), df[df.is_constr].noise_dB.dropna()]
    a1.boxplot(data, tick_labels=['Transport/other', 'Construction'])
    a1.axhline(QCVN_D, ls='--', c='red', alpha=.7, label='QCVN 70'); a1.set_ylabel('dB')
    a1.set_title('Transport vs construction (overall)'); a1.legend(fontsize=8); a1.grid(alpha=.3)
    sites = df.site.unique(); w = .35
    for i, s in enumerate(sites):
        sub = df[df.site == s]
        a2.bar(i - w / 2, sub[~sub.is_constr].noise_dB.median(), w, color='#1f77b4',
               label='Transport' if i == 0 else '')
        cv = sub[sub.is_constr].noise_dB.median()
        a2.bar(i + w / 2, 0 if np.isnan(cv) else cv, w, color='#ff7f0e',
               label='Construction' if i == 0 else '')
    a2.axhline(QCVN_D, ls='--', c='red', alpha=.7); a2.set_xticks(range(len(sites)))
    a2.set_xticklabels([s.replace(' ', chr(10)) for s in sites], fontsize=8)
    a2.set_ylabel('median dB'); a2.set_title('By site'); a2.legend(fontsize=8); a2.grid(alpha=.3)
    plt.tight_layout(); plt.savefig(_out('analyse_3_type.png'), dpi=130); plt.close(fig)


def exceedance_by_hour(df):
    period = np.where((df.hour >= 21) | (df.hour < 6), 'night', 'day')
    limit = np.where(period == 'night', QCVN_N, QCVN_D)
    fig, ax = plt.subplots(figsize=(11, 4.5))
    pe = 100 * df.assign(_ex=df.noise_dB > limit).groupby('hour')['_ex'].mean()
    ax.bar(pe.index, pe.values,
           color=['darkred' if v > 50 else 'orange' if v > 0 else 'green' for v in pe.values])
    ax.set_xlabel('Hour'); ax.set_ylabel('% of measurements > QCVN')
    ax.set_xticks(range(0, 24, 2))
    ax.set_title('QCVN exceedance frequency by hour'); ax.grid(alpha=.3)
    plt.tight_layout(); plt.savefig(_out('analyse_4_depassement.png'), dpi=130); plt.close(fig)

    peak = df.groupby('hour').noise_dB.median()
    print(f'Noisiest hour: {peak.idxmax()}h ({peak.max():.0f} dB) | '
          f'quietest: {peak.idxmin()}h ({peak.min():.0f} dB)')
    print(f'Share of samples above the QCVN threshold: {100 * (df.noise_dB > limit).mean():.1f}%')
    print('  /!\\ a descriptive statistic of our sample, NOT a finding of non-compliance:')
    print('      our quantity (L_A,25s) and our sensors are not those the standard prescribes.')


def weather(df):
    """Weather against level.

    The trap: weather is confounded with the hour (temperature vs hour r about
    0.66) and with the sessions (the "quiet points" campaigns fell on rainy days).
    So we look at the partial correlation with the hour controlled, and at the rain
    effect AT EQUAL SESSION.
    """
    wcols = [c for c in ['temperature_2m', 'wind_speed_10m', 'precipitation'] if c in df.columns]
    dw = df.dropna(subset=wcols).copy()
    dw['rain'] = dw['precipitation'] > 0

    print('correlations with noise_dB (raw / hour controlled):')
    for c in wcols:
        raw = dw[c].corr(dw.noise_dB)
        rh = dw.noise_dB - np.poly1d(np.polyfit(dw.hour, dw.noise_dB, 2))(dw.hour)
        rw = dw[c] - np.poly1d(np.polyfit(dw.hour, dw[c], 2))(dw.hour)
        print(f'  {c:18} raw {raw:+.2f}   partial {rh.corr(rw):+.2f}')

    diffs = []
    for _, g in dw.groupby([dw.timestamp.dt.date, 'site']):
        if g.rain.nunique() == 2 and g.rain.value_counts().min() >= 3:
            m = g.groupby('rain').noise_dB.median()
            diffs.append(m[True] - m[False])
    if diffs:
        print(f'\nrain effect at equal session: {np.mean(diffs):+.1f} dB median '
              f'(over {len(diffs)} mixed sessions)')
    print('=> the raw -10 dB dry/rain gap comes mostly from quiet sessions '
          'that fell on rainy days')

    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    for ax, c in zip(axes, wcols):
        ax.scatter(dw[c], dw.noise_dB, s=12, alpha=.4, c='#2471a3')
        ax.set_xlabel(c); ax.set_ylabel('dB'); ax.grid(alpha=.3)
        ax.set_title(f'raw r {dw[c].corr(dw.noise_dB):+.2f}')
    plt.suptitle('Weather vs noise - raw correlations (see partial correlations above)')
    plt.tight_layout()
    plt.savefig(_out('analyse_5_meteo.png'), dpi=120, bbox_inches='tight')
    plt.close(fig)


def main() -> int:
    if not os.path.exists(cfg.MEASUREMENTS):
        print(f'Missing {cfg.MEASUREMENTS}\n  -> python3 scripts/01_prepare_field_data.py',
              file=sys.stderr)
        return 1
    os.makedirs(cfg.FIGURES, exist_ok=True)
    df = pd.read_csv(cfg.MEASUREMENTS, parse_dates=['timestamp'])
    df['hour'] = df.timestamp.dt.hour

    print('Levels are calibrated in RELATIVE terms (contrasts), not in absolute terms '
          '- uncertified smartphones.')
    hourly_cycle(df)
    weekday_profile(df)
    transport_vs_construction(df)
    exceedance_by_hour(df)
    weather(df)
    print(f'OK -> 5 figures in {cfg.FIGURES}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

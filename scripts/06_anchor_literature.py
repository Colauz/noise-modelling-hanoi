"""Anchor our smartphone measurements on instrumented literature ("virtual calibration").

WHY
---
We have no reference sound level meter and the campaign is closed. Our three phones
are calibrated AGAINST EACH OTHER, never against a standard: a bias common to all three
devices is invisible in our data. We therefore cannot claim certified absolute levels.

What we CAN do, and what this script does: compare the distribution of our levels,
stratified to be comparable, against published Vietnamese campaigns that used
professional instrumentation. This does not calibrate our data -- the quantities and
integration periods differ -- but it BOUNDS the plausible bias and checks that our
orders of magnitude are not aberrant.

PRINCIPLE AND LIMITATION
------------------------
An "anchor point" is only usable if comparable things are compared. We therefore
stratify our measurements to approximate as closely as possible the situation described
by each source (roadside, daytime, major road). Even so, three gaps remain and they are
IRREDUCIBLE:

  1. Quantity : our 25 s against LAeq,1min to 24 h, or even Lden (an annual average
                with evening/night penalties). An Lden is mechanically above the
                daytime LAeq of the same place.
  2. Place    : "major arteries of Hanoi" is not "our 3 districts", two of which are
                not major corridors.
  3. Epoch    : 2005-2019 depending on the source, against 2026 for us (partial
                electrification of the two-wheeler fleet under way in Hanoi).

=> The offset computed here is an ORDER OF PLAUSIBILITY. It is NOT applied to the
   data. No correction is written into measurements.csv.

Output: results/tables/literature_anchoring.md  (+ .csv)
Usage : python3 scripts/06_anchor_literature.py
"""
import os
import warnings

warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd

from noise_hanoi import config as cfg

ROOT = cfg.ROOT
MEASURES = cfg.MEASUREMENTS
OUT_MD = os.path.join(cfg.TABLES, 'literature_anchoring.md')
OUT_CSV = os.path.join(cfg.TABLES, 'literature_anchoring.csv')

# --------------------------------------------------------------------------------------
#  Published anchor points. `comparable` names the stratum of OUR data that best
#  approximates the situation described, and `metric_gap_dB` the systematic gap EXPECTED
#  from the difference in quantity alone (positive = the source should sit above us).
#
#  `status` -- the project's source policy, stated in docs/methodology.md 5.2 and
#  reused by docs/literature-review.md. Do not introduce a fourth level here
#  without changing it there.
#             'verified'  = value read in the source's own abstract or summary
#             'to_check'  = value reported second-hand, to be confirmed against the PDF
#             'grey'      = grey literature (an institute quoted in the press), not
#                           peer-reviewed -- NEVER to be cited as a primary reference
# --------------------------------------------------------------------------------------
ANCHORS = [
    dict(key='gelb2019cyclists',
         source='Gelb & Apparicio 2019, Applied Acoustics 148:332-343',
         city='Ho Chi Minh City', year='2016-2017',
         instrument='personal dosimeters + GPS',
         metric='LAeq,1min', value=78.8, spread='mean over 3300 segments',
         comparable='roadside_day', metric_gap_dB=+2.0,
         status='verified',
         comment="Cyclists INSIDE the flow (~1-2 m from vehicles): more exposed than an "
                 "observer at the kerb. The expected gap is positive."),
    dict(key='phan2010characteristics',
         source='Phan et al. 2010, Applied Acoustics 71(5):479-485',
         city='Hanoi', year='2005-2007',
         instrument='RION NL-21 / NL-22 (sound level meters), 24 h continuous',
         metric='Lden', value=76.5, spread='reported range 70-83 dB over 7 sites',
         comparable='roadside_day', metric_gap_dB=+4.0,
         status='to_check',
         comment="The ONLY published Hanoi campaign with professional instrumentation. "
                 "Lden = annual average with +5 dB evening / +10 dB night penalties: "
                 "mechanically above a daytime level. Value to be confirmed against the PDF."),
    dict(key='phan2010characteristics_night',
         source='Phan et al. 2010, Applied Acoustics 71(5):479-485',
         city='Hanoi', year='2005-2007',
         instrument='RION NL-21 / NL-22, 24 h continuous',
         metric='Lnight (lowest of the 7 sites)', value=66.0, spread='inter-site minimum',
         comparable='night_all', metric_gap_dB=0.0,
         status='to_check',
         comment="Our night-time coverage is too thin (n about 10) for this anchor "
                 "to be informative: it is carried for the record."),
    dict(key='ioh_hanoi_grey',
         source="Institute of Occupational Health and Environment, 12 major Hanoi arteries "
                "(as reported by the Vietnamese press)",
         city='Hanoi', year='2010s',
         instrument='not documented',
         metric='daytime mean dBA', value=77.9, spread='range 77.8-78.1 dBA',
         comparable='roadside_day_major', metric_gap_dB=+1.0,
         status='grey',
         comment="Grey literature: secondary source, undocumented protocol. "
                 "To be used as contextual orientation, never as a primary reference."),
]

# strata of OUR data made comparable to each anchor
ROADSIDE = '0-2|0-10|2-10'          # distance-to-road classes counted as "roadside"


def strata(df):
    day = (df.hour >= 6) & (df.hour < 21)
    road = df.dist_to_road.astype(str).str.contains(ROADSIDE, na=False)
    major = df.site.isin(['Vinh Tuy area', 'Hoan Kiem lake'])   # corridors / vieux quartier dense
    return {
        'all': df,
        'roadside_day': df[day & road],
        'roadside_day_major': df[day & road & major],
        'night_all': df[~day],
    }


def describe(g):
    if len(g) == 0:
        return dict(n=0, median=np.nan, mean=np.nan, p90=np.nan, sd=np.nan)
    return dict(n=len(g), median=float(g.noise_dB.median()), mean=float(g.noise_dB.mean()),
                p90=float(g.noise_dB.quantile(0.9)), sd=float(g.noise_dB.std()))


def main():
    if not os.path.exists(MEASURES):
        raise SystemExit(f'Manque {MEASURES}\n  -> python3 scripts/01_prepare_field_data.py')
    df = pd.read_csv(MEASURES, parse_dates=['timestamp'])
    df['hour'] = df.timestamp.dt.hour
    S = strata(df)

    print('Our strata:')
    for k, g in S.items():
        d = describe(g)
        print(f'  {k:20} n={d["n"]:4}  median {d["median"]:5.1f}  mean {d["mean"]:5.1f}  '
              f'p90 {d["p90"]:5.1f}  sd {d["sd"]:4.1f}')

    rows = []
    for a in ANCHORS:
        d = describe(S[a['comparable']])
        # raw gap, then the gap corrected for the EXPECTED difference in quantity
        raw = np.nan if d['n'] == 0 else a['value'] - d['median']
        resid = np.nan if d['n'] == 0 else raw - a['metric_gap_dB']
        rows.append({**{k: a[k] for k in
                        ('source', 'city', 'year', 'instrument', 'metric', 'value',
                         'comparable', 'metric_gap_dB', 'status', 'comment')},
                     'our_n': d['n'], 'our_median_dB': round(d['median'], 1) if d['n'] else None,
                     'gap_raw_dB': None if d['n'] == 0 else round(raw, 1),
                     'gap_after_metric_correction_dB': None if d['n'] == 0 else round(resid, 1)})
    out = pd.DataFrame(rows)
    out.to_csv(OUT_CSV, index=False)

    usable = out[(out.status != 'grey') & out.gap_after_metric_correction_dB.notna() &
                 (out.comparable != 'night_all')]
    lo = usable.gap_after_metric_correction_dB.min() if len(usable) else np.nan
    hi = usable.gap_after_metric_correction_dB.max() if len(usable) else np.nan

    print('\nResidual gap after correcting for the difference in quantity:')
    for _, r in out.iterrows():
        g = r.gap_after_metric_correction_dB
        print(f'  [{r.status:8}] {r.source[:52]:52} {"n/a" if g is None else f"{g:+5.1f} dB"}')
    print(f'\n=> Plausible bias interval (peer-reviewed sources, night excluded): '
          f'{lo:+.1f} to {hi:+.1f} dB')
    print('   No correction is applied to the data: this interval is there to bound '
          'the\n   absolute uncertainty in the manuscript, not to shift the measurements.')

    write_md(df, S, out, lo, hi)
    print(f'\nOK -> {OUT_MD}\nOK -> {OUT_CSV}')


def write_md(df, S, out, lo, hi):
    L = ['# Anchoring on instrumented literature', '',
         '_Generated by `scripts/06_anchor_literature.py`. No correction is applied '
         'to the measurements: this document bounds the absolute uncertainty, it does not correct it._', '',
         '## Our strata', '',
         '| Stratum | n | Median | Mean | p90 | Std dev |', '|---|---|---|---|---|---|']
    for k, g in S.items():
        d = describe(g)
        if d['n'] == 0:
            L.append(f'| `{k}` | 0 | — | — | — | — |')
        else:
            L.append(f'| `{k}` | {d["n"]} | {d["median"]:.1f} | {d["mean"]:.1f} | '
                     f'{d["p90"]:.1f} | {d["sd"]:.1f} |')
    L += ['', '## Published anchor points', '',
          '| Source | City | Instrument | Quantity | Value | Our stratum | Raw gap | '
          'Corrected gap | Status |', '|---|---|---|---|---|---|---|---|---|']
    for _, r in out.iterrows():
        f = lambda v: '—' if v is None or (isinstance(v, float) and np.isnan(v)) else f'{v:+.1f}'
        L.append(f'| {r.source} | {r.city} | {r.instrument} | {r.metric} | {r.value:.1f} | '
                 f'`{r.comparable}` (n={r.our_n}) | {f(r.gap_raw_dB)} | '
                 f'{f(r.gap_after_metric_correction_dB)} | {r.status} |')
    L += ['', '_"Corrected gap" = raw gap minus the difference expected from the '
              'quantity alone (`metric_gap_dB`). It approximates the residual instrumental bias._', '',
          f'## Conclusion', '',
          f'Plausible absolute bias of our smartphones: **between {lo:+.1f} and {hi:+.1f} dB** '
          '(peer-reviewed sources, night excluded).', '',
          'What this allows and forbids:', '',
          '- **Allowed**: comparing our places with each other, our hours with each other, and '
          'discussing spatial and temporal contrasts. The bias is common to all three devices '
          'and cancels in a difference.',
          '- **Forbidden**: stating a regulatory exceedance rate as a fact. '
          'The QCVN daytime threshold (70 dBA) falls in the middle of our distribution: a bias of '
          'a few dB shifts the exceedance percentage substantially.', '',
          '### Notes by source', '']
    for _, r in out.iterrows():
        L.append(f'- **{r.source}** — {r.comment}')
    with open(OUT_MD, 'w') as f:
        f.write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()

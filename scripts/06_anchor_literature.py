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
#  Points d'ancrage publiés. `comparable` décrit la strate de NOS données qui approche le
#  mieux la situation décrite, et `metric_gap_dB` l'écart systématique ATTENDU du seul fait
#  de la différence de grandeur (positif = la source doit être au-dessus de nous).
#
#  `status` : 'verified'  = valeur lue dans le résumé/abstract de la source
#             'to_check'  = valeur rapportée de seconde main, à confirmer sur le PDF
#             'grey'      = littérature grise (institut cité par la presse), non revue
#                           par les pairs — à ne PAS citer comme référence primaire
# --------------------------------------------------------------------------------------
ANCHORS = [
    dict(key='gelb2019cyclists',
         source='Gelb & Apparicio 2019, Applied Acoustics 148:332-343',
         city='Ho Chi Minh City', year='2016-2017',
         instrument='dosimètres personnels + GPS',
         metric='LAeq,1min', value=78.8, spread='moyenne sur 3300 segments',
         comparable='roadside_day', metric_gap_dB=+2.0,
         status='verified',
         comment="Cyclistes DANS le flux (~1-2 m des véhicules) : plus exposés qu'un "
                 "observateur en bord de trottoir. L'écart attendu est positif."),
    dict(key='phan2010characteristics',
         source='Phan et al. 2010, Applied Acoustics 71(5):479-485',
         city='Hanoï', year='2005-2007',
         instrument='RION NL-21 / NL-22 (sonomètres), 24 h continu',
         metric='Lden', value=76.5, spread='plage rapportée 70-83 dB sur 7 sites',
         comparable='roadside_day', metric_gap_dB=+4.0,
         status='to_check',
         comment="SEULE campagne publiée à Hanoï avec instrumentation professionnelle. "
                 "Lden = moyenne annuelle avec pénalités +5 dB soir / +10 dB nuit : "
                 "mécaniquement au-dessus d'un niveau diurne. Valeur à confirmer sur le PDF."),
    dict(key='phan2010characteristics_night',
         source='Phan et al. 2010, Applied Acoustics 71(5):479-485',
         city='Hanoï', year='2005-2007',
         instrument='RION NL-21 / NL-22, 24 h continu',
         metric='Lnight (le plus bas des 7 sites)', value=66.0, spread='minimum inter-sites',
         comparable='night_all', metric_gap_dB=0.0,
         status='to_check',
         comment="Notre couverture nocturne est trop faible (n≈10) pour que cet ancrage "
                 "soit informatif : il est reporté pour mémoire."),
    dict(key='ioh_hanoi_grey',
         source="Institute of Occupational Health and Environment, 12 grands axes de Hanoï "
                "(rapporté par la presse vietnamienne)",
         city='Hanoï', year='années 2010',
         instrument='non documenté',
         metric='moyenne diurne dBA', value=77.9, spread='plage 77,8-78,1 dBA',
         comparable='roadside_day_major', metric_gap_dB=+1.0,
         status='grey',
         comment="Littérature grise : source secondaire, protocole non documenté. "
                 "À utiliser comme repère contextuel, jamais comme référence primaire."),
]

# strates de NOS données rendues comparables à chaque ancrage
ROADSIDE = '0-2|0-10|2-10'          # classes de distance à la route « bord de voirie »


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
        raise SystemExit(f'Manque {MEASURES}\n  -> python3 scripts/prepare_field_data.py')
    df = pd.read_csv(MEASURES, parse_dates=['timestamp'])
    df['hour'] = df.timestamp.dt.hour
    S = strata(df)

    print('Nos strates :')
    for k, g in S.items():
        d = describe(g)
        print(f'  {k:20} n={d["n"]:4}  médiane {d["median"]:5.1f}  moy {d["mean"]:5.1f}  '
              f'p90 {d["p90"]:5.1f}  sd {d["sd"]:4.1f}')

    rows = []
    for a in ANCHORS:
        d = describe(S[a['comparable']])
        # écart brut, puis écart corrigé de la différence de grandeur ATTENDUE
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

    print('\nÉcart résiduel après correction de la différence de grandeur :')
    for _, r in out.iterrows():
        g = r.gap_after_metric_correction_dB
        print(f'  [{r.status:8}] {r.source[:52]:52} {"n/a" if g is None else f"{g:+5.1f} dB"}')
    print(f'\n=> Fourchette du biais plausible (sources revues, hors nuit) : '
          f'{lo:+.1f} à {hi:+.1f} dB')
    print('   Aucune correction n\'est appliquée aux données : cet intervalle sert à '
          'encadrer\n   l\'incertitude absolue dans le manuscrit, pas à décaler les mesures.')

    write_md(df, S, out, lo, hi)
    print(f'\nOK -> {OUT_MD}\nOK -> {OUT_CSV}')


def write_md(df, S, out, lo, hi):
    L = ['# Ancrage sur la littérature instrumentée', '',
         '_Généré par `scripts/literature_anchoring.py`. Aucune correction n\'est appliquée '
         'aux mesures : ce document borne l\'incertitude absolue, il ne la corrige pas._', '',
         '## Nos strates', '',
         '| Strate | n | Médiane | Moyenne | p90 | Écart-type |', '|---|---|---|---|---|---|']
    for k, g in S.items():
        d = describe(g)
        if d['n'] == 0:
            L.append(f'| `{k}` | 0 | — | — | — | — |')
        else:
            L.append(f'| `{k}` | {d["n"]} | {d["median"]:.1f} | {d["mean"]:.1f} | '
                     f'{d["p90"]:.1f} | {d["sd"]:.1f} |')
    L += ['', '## Points d\'ancrage publiés', '',
          '| Source | Ville | Instrument | Grandeur | Valeur | Notre strate | Écart brut | '
          'Écart corrigé | Statut |', '|---|---|---|---|---|---|---|---|---|']
    for _, r in out.iterrows():
        f = lambda v: '—' if v is None or (isinstance(v, float) and np.isnan(v)) else f'{v:+.1f}'
        L.append(f'| {r.source} | {r.city} | {r.instrument} | {r.metric} | {r.value:.1f} | '
                 f'`{r.comparable}` (n={r.our_n}) | {f(r.gap_raw_dB)} | '
                 f'{f(r.gap_after_metric_correction_dB)} | {r.status} |')
    L += ['', '_« Écart corrigé » = écart brut moins la différence attendue du seul fait de '
              'la grandeur (`metric_gap_dB`). Il approche le biais instrumental résiduel._', '',
          f'## Conclusion', '',
          f'Biais absolu plausible de nos smartphones : **entre {lo:+.1f} et {hi:+.1f} dB** '
          '(sources revues par les pairs, hors nuit).', '',
          'Ce que cela autorise et interdit :', '',
          '- **Autorisé** : comparer nos lieux entre eux, nos heures entre elles, et discuter '
          'des contrastes spatiaux et temporels. Le biais est commun aux trois appareils et '
          's\'annule dans une différence.',
          '- **Interdit** : annoncer un taux de dépassement réglementaire comme un fait. '
          'Le seuil QCVN diurne (70 dBA) tombe au milieu de notre distribution : un biais de '
          'quelques dB déplace fortement le pourcentage de dépassement.', '',
          '### Notes par source', '']
    for _, r in out.iterrows():
        L.append(f'- **{r.source}** — {r.comment}')
    with open(OUT_MD, 'w') as f:
        f.write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()

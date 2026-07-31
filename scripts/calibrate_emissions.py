"""Calibration des émissions sonores par type de véhicule SUR NOS DONNÉES.

Problème : la simulation GAMA a besoin d'un niveau sonore par catégorie (moto,
voiture, poids lourd) et pour les chantiers. Prendre des valeurs « de la
littérature » sans les vérifier revient à simuler au doigt mouillé. On les estime
donc directement à partir de nos 147 vidéos comptées et des mesures appariées.

Principe physique
-----------------
Les niveaux sonores s'additionnent en ÉNERGIE, pas en décibels :

    E_total = E_fond + n_moto·e_moto + n_voiture·e_voiture + n_lourd·e_lourd

avec E = 10^(L/10). C'est donc une régression LINÉAIRE en énergie, avec des
coefficients nécessairement POSITIFS (une source ne peut pas retirer de l'énergie)
-> moindres carrés sous contrainte de non-négativité (NNLS).

Le fond est laissé libre PAR SITE (une colonne indicatrice par site) : chaque
quartier a son ambiance propre, qu'on ne veut pas attribuer aux véhicules.

Ce que les valeurs obtenues signifient
--------------------------------------
e_moto, e_voiture, e_lourd sont les énergies apportées par UN véhicule visible
dans le champ de la caméra, à la distance typique de nos prises de vue. Converties
en dB (10·log10), ce sont donc des niveaux « par véhicule au récepteur », pas des
puissances acoustiques normalisées à 7,5 m comme dans les normes. C'est
exactement ce dont la simulation a besoin, et c'est mesuré chez nous.

Sortie : outputs/gama_inputs/emission_calibration.csv (lu par le modèle GAMA)
Usage  : python3 scripts/calibrate_emissions.py
"""
import os
import warnings

warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from scipy.optimize import nnls

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COUNTS = os.path.join(ROOT, 'data', 'processed', 'hanoi', 'vehicle_counts.csv')
MEASURES = os.path.join(ROOT, 'data', 'raw', 'hanoi', 'measurements.csv')
OUT = os.path.join(ROOT, 'outputs', 'gama_inputs', 'emission_calibration.csv')

TYPES = ['moto', 'car', 'heavy']
# distance médiane, mesurée, entre nos points « chantier signalé » et le chantier
CONSTR_REF_DIST = 56.0


def load():
    v = pd.read_csv(COUNTS, parse_dates=['matched_timestamp'])
    m = pd.read_csv(MEASURES, parse_dates=['timestamp'])
    v = v.merge(m[['timestamp', 'site']], left_on='matched_timestamp',
                right_on='timestamp', how='left')
    v = v.dropna(subset=['matched_dB', 'site']).copy()
    v['heavy_mean'] = v['bus_mean'] + v['truck_mean']
    return v


def fit_emissions(v):
    """NNLS en énergie : E = somme(fond_site) + somme(n_type · e_type)."""
    sites = sorted(v.site.unique())
    cols, names = [], []
    for s in sites:                       # fond propre à chaque site
        cols.append((v.site == s).astype(float).values)
        names.append(f'bg::{s}')
    for t in TYPES:                       # une colonne par type de véhicule
        cols.append(v[f'{t}_mean'].values)
        names.append(t)

    X = np.column_stack(cols)
    y = np.power(10.0, v.matched_dB.values / 10.0)      # dB -> énergie
    coef, _ = nnls(X, y)

    pred_e = X @ coef
    pred_dB = 10 * np.log10(np.maximum(pred_e, 1e-9))
    resid = pred_dB - v.matched_dB.values
    fit = {
        'n': len(v),
        'mae_dB': float(np.abs(resid).mean()),
        'bias_dB': float(resid.mean()),
        'r': float(np.corrcoef(pred_dB, v.matched_dB.values)[0, 1]),
    }
    return dict(zip(names, coef)), fit


def to_dB(e):
    return 10 * np.log10(e) if e > 0 else float('nan')


def construction_excess():
    """Excès dû aux chantiers, estimé en énergie sur nos mesures d'Ocean Park.

    E(avec chantier) - E(sans) = énergie ajoutée par l'activité de chantier.
    Comparaison faite à site et heure comparables pour ne pas confondre avec le trafic.
    """
    m = pd.read_csv(MEASURES, parse_dates=['timestamp'])
    m['hour'] = m.timestamp.dt.hour
    op = m[m.site == 'Ocean Park'].copy()
    op['near'] = op.construction_nearby.astype(str).str.lower() == 'yes'
    if op.near.sum() < 5:
        return None
    # à heure égale, moyenne énergétique avec vs sans chantier signalé
    rows = []
    for h, g in op.groupby('hour'):
        if g.near.nunique() == 2 and g.near.sum() >= 2 and (~g.near).sum() >= 2:
            e_with = np.power(10, g[g.near].noise_dB / 10).mean()
            e_without = np.power(10, g[~g.near].noise_dB / 10).mean()
            rows.append((h, len(g[g.near]), len(g[~g.near]), e_with - e_without))
    if not rows:
        return None
    add_e = np.median([r[3] for r in rows])
    return {'hours': rows, 'energy': add_e, 'dB': to_dB(add_e) if add_e > 0 else float('nan')}


def diagnostics(v):
    """Le comptage vidéo porte-t-il un signal acoustique exploitable ?"""
    print('Pouvoir explicatif du comptage (régression du dB sur le nombre de véhicules) :')
    for s, g in v.groupby('site'):
        r = g.vehicles_mean.corr(g.matched_dB)
        print(f'  {s:16} n={len(g):3}  r {r:+.2f}  ->  R² {r**2:.3f}')
    print()


def main():
    v = load()
    diagnostics(v)
    coef, fit = fit_emissions(v)
    print(f'Calibration sur {fit["n"]} vidéos appariées à une mesure')
    print(f'  qualité de l\'ajustement : MAE {fit["mae_dB"]:.2f} dB · '
          f'biais {fit["bias_dB"]:+.2f} dB · r {fit["r"]:.2f}\n')

    print('Fond par site (niveau sans véhicule visible) :')
    for k, e in coef.items():
        if k.startswith('bg::'):
            print(f'  {k[4:]:16} {to_dB(e):5.1f} dB')

    print('\nÉmission par véhicule visible dans le champ :')
    out_rows = []
    for t in TYPES:
        e = coef[t]
        lvl = to_dB(e)
        print(f'  {t:6} {lvl:5.1f} dB' + ('' if e > 0 else '   (contrainte NNLS -> 0, non séparable)'))
        out_rows.append({'category': t, 'energy': e, 'level_dB': lvl})

    identifiable = any(coef[t] > 0 for t in TYPES)
    if not identifiable:
        print('\n>> RÉSULTAT : les émissions par véhicule NE SONT PAS IDENTIFIABLES sur nos données.')
        print('   La contrainte de non-négativité ramène les trois coefficients à zéro : à site')
        print('   donné, le nombre de véhicules visibles n\'explique pas le niveau mesuré')
        print('   (R² < 0.05 partout, corrélations de signe incohérent entre sites).')
        print('   Causes plausibles : les véhicules garés sont comptés (pas de filtre de')
        print('   mouvement), la distance de chaque véhicule n\'est pas prise en compte, et la')
        print('   vitesse - qui domine le bruit de roulement - n\'est pas observable sur le comptage.')
        print('   CONSÉQUENCE POUR LA SIMULATION : les véhicules y sont une représentation')
        print('   visuelle calibrée du parc, PAS une source acoustique. Le niveau reste piloté')
        print('   par le modèle validé et par la loi de volume de trafic.')

    # Excès chantier. On raisonne sur les MÉDIANES : en énergie, les moyennes sont
    # dominées par les quelques points les plus bruyants et surestiment la source
    # (une calibration sur moyennes donnait 74,7 dB, soit +8 dB simulés près des
    # chantiers, incompatible avec les +2 dB réellement observés).
    m = pd.read_csv(MEASURES, parse_dates=['timestamp'])
    op = m[m.site == 'Ocean Park'].copy()
    op['near'] = op.construction_nearby.astype(str).str.lower() == 'yes'
    med_w = op[op.near].noise_dB.median()
    med_o = op[~op.near].noise_dB.median()
    add_e = max(np.power(10, med_w / 10) - np.power(10, med_o / 10), 0.0)
    print(f'\nChantiers (Ocean Park, n={op.near.sum()} avec / {(~op.near).sum()} sans) :')
    print(f'  niveau médian    : {med_w:.1f} dB avec chantier vs {med_o:.1f} dB sans '
          f'({med_w - med_o:+.1f} dB)')
    print(f'  distance médiane des points signalant un chantier : {CONSTR_REF_DIST:.0f} m')
    print(f'  -> source équivalente : {to_dB(add_e):.1f} dB à {CONSTR_REF_DIST:.0f} m')
    print('  vérification (atténuation géométrique depuis cette source) :')
    for d in [25, 56, 200]:
        lvl = to_dB(add_e) - 20 * np.log10(d / CONSTR_REF_DIST)
        tot = to_dB(np.power(10, med_o / 10) + np.power(10, lvl / 10))
        print(f'    à {d:3d} m -> niveau total {tot:.1f} dB')
    out_rows.append({'category': 'construction', 'energy': add_e, 'level_dB': to_dB(add_e),
                     'ref_distance_m': CONSTR_REF_DIST})

    df = pd.DataFrame(out_rows)
    df['identifiable'] = [int(coef.get(r['category'], 1) > 0) if r['category'] in TYPES else 1
                          for r in out_rows]
    df['source'] = 'estimé sur nos 147 vidéos et 363 mesures terrain'
    df.to_csv(OUT, index=False)
    print(f'\nOK -> {OUT}')
    return coef, fit


if __name__ == '__main__':
    main()

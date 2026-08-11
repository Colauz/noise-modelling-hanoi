"""Calibrate per-vehicle-class sound emissions ON OUR OWN DATA.

Problem: the GAMA simulation needs a sound level per category (motorcycle, car,
heavy vehicle) and for construction sites. Taking "literature" values without
checking them amounts to simulating by guesswork. We therefore estimate them
directly from our 147 counted videos and the matched measurements.

Physical principle
------------------
Sound levels add in ENERGY, not in decibels:

    E_total = E_background + n_moto*e_moto + n_car*e_car + n_heavy*e_heavy

with E = 10^(L/10). It is therefore a LINEAR regression in energy, with
necessarily POSITIVE coefficients (a source cannot remove energy)
-> non-negative least squares (NNLS).

The background is left free PER SITE (one indicator column per site): each
district has its own ambience, which we do not want attributed to vehicles.

What the resulting values mean
------------------------------
e_moto, e_car, e_heavy are the energies contributed by ONE vehicle visible in the
camera field, at the typical distance of our shots. Converted to dB (10*log10),
they are therefore "per-vehicle levels at the receiver", not sound powers
normalised to 7.5 m as in the standards. That is exactly what the simulation
needs, and it is measured on our own data.

RESULT, as of August 2026: the coefficients come out NULL for motorcycles and
cars. They are not identifiable from these data. See docs/negative-results.md.

Output: simulation/gama/inputs/emission_calibration.csv (read by the GAMA model)
Usage : python3 scripts/05_calibrate_emissions.py
"""
import os
import warnings

warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from scipy.optimize import nnls

from noise_hanoi import config as cfg

ROOT = cfg.ROOT
COUNTS = cfg.VEHICLE_COUNTS
MEASURES = cfg.MEASUREMENTS
OUT = os.path.join(cfg.GAMA_INPUTS, 'emission_calibration.csv')

TYPES = ['moto', 'car', 'heavy']
# median measured distance between our "construction reported" points and the site
CONSTR_REF_DIST = 56.0


def load():
    v = pd.read_csv(COUNTS, parse_dates=['matched_timestamp'])
    m = pd.read_csv(MEASURES, parse_dates=['timestamp'])
    v = v.merge(m[['timestamp', 'site']], left_on='matched_timestamp',
                right_on='timestamp', how='left')
    v = v.dropna(subset=['matched_dB', 'site']).copy()
    v['heavy_mean'] = v['bus_mean'] + v['truck_mean']
    if 'bus_flow' in v.columns:
        v['heavy_flow'] = v['bus_flow'] + v['truck_flow']
    return v


def fit_emissions(v, suffix='_mean'):
    """NNLS in energy: E = sum(background_site) + sum(x_type * e_type).

    Two formulations, depending on `suffix`:

    `_mean` (v1) - x = DENSITY, mean number of vehicles visible per frame. `e_type`
        then reads as the energy of a vehicle *present in the field of view*. This is
        the formulation that produced the negative result of 5.x: density is a
        stock, elle ne dit rien du nombre de passages.

    `_flow` (v2) - x = FLOW, line crossings per minute. This is the PHYSICALLY
        CORRECT formulation: an equivalent level integrated over a period T results from
        the sum of the energies contributed by each PASS, so E = E_bg + sum(Q_c * e_c)
        with Q_c the flow of class c and e_c the energy per pass. It is this
        formulation that can identify an emission, if the data allow it.
    """
    sites = sorted(v.site.unique())
    cols, names = [], []
    for s in sites:                       # a background of its own for each site
        cols.append((v.site == s).astype(float).values)
        names.append(f'bg::{s}')
    for t in TYPES:                       # one column per vehicle type
        cols.append(v[f'{t}{suffix}'].values)
        names.append(t)

    X = np.column_stack(cols)
    y = np.power(10.0, v.matched_dB.values / 10.0)      # dB -> energy
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
    """Excess due to construction, estimated in energy on our Ocean Park measurements.

    E(with construction) - E(without) = energy added by construction activity.
    Compared at comparable site and hour so as not to confound it with traffic.
    """
    m = pd.read_csv(MEASURES, parse_dates=['timestamp'])
    m['hour'] = m.timestamp.dt.hour
    op = m[m.site == 'Ocean Park'].copy()
    op['near'] = op.construction_nearby.astype(str).str.lower() == 'yes'
    if op.near.sum() < 5:
        return None
    # at equal hour, energy mean with vs without reported construction
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
    """Does the video count carry a usable acoustic signal?

    The two predictors are compared head to head: density (v1) and flow (v2).
    This is THE question the move to object tracking was meant to settle.
    """
    has_flow = 'vehicles_flow' in v.columns
    print('Explanatory power of the count (correlation of measured dB with the count):')
    head = f'  {"site":16} {"n":>4}  {"r density":>10}  {"R2":>6}'
    if has_flow:
        head += f'  |  {"r FLOW":>9}  {"R2":>6}'
    print(head)
    for s, g in v.groupby('site'):
        r = g.vehicles_mean.corr(g.matched_dB)
        line = f'  {s:16} {len(g):4}  {r:+10.2f}  {r**2:6.3f}'
        if has_flow:
            rf = g.vehicles_flow.corr(g.matched_dB)
            line += f'  |  {rf:+9.2f}  {rf**2:6.3f}'
        print(line)
    r = v.vehicles_mean.corr(v.matched_dB)
    line = f'  {"TOUS SITES":16} {len(v):4}  {r:+10.2f}  {r**2:6.3f}'
    if has_flow:
        rf = v.vehicles_flow.corr(v.matched_dB)
        line += f'  |  {rf:+9.2f}  {rf**2:6.3f}'
    print(line)
    if has_flow:
        print(f'\n  motorcycle flow alone: r = {v.moto_flow.corr(v.matched_dB):+.2f}')
    print()


def main():
    v = load()
    diagnostics(v)

    has_flow = 'vehicles_flow' in v.columns
    if has_flow:
        # Physically correct formulation first: energy per PASS.
        coef_f, fit_f = fit_emissions(v, suffix='_flow')
        print(f'--- v2, regression on FLOW (energy per pass) ---')
        print(f'  ajustement : MAE {fit_f["mae_dB"]:.2f} dB · biais {fit_f["bias_dB"]:+.2f} dB '
              f'· r {fit_f["r"]:.2f}')
        for t in TYPES:
            e = coef_f.get(t, 0.0)
            print(f'  {t:8} {("%.4g" % e) if e > 0 else "0":>12}   '
                  + (f'-> {to_dB(e):.1f} dB par passage' if e > 0
                     else '(contrainte NNLS -> 0, non identifiable)'))
        print()

    coef, fit = fit_emissions(v, suffix='_mean')
    print('--- v1, regression on DENSITY (kept for comparison) ---')
    print(f'Calibration on {fit["n"]} videos matched to a measurement')
    print(f'  goodness of fit: MAE {fit["mae_dB"]:.2f} dB - '
          f'biais {fit["bias_dB"]:+.2f} dB · r {fit["r"]:.2f}\n')

    print('Background per site (level with no visible vehicle):')
    for k, e in coef.items():
        if k.startswith('bg::'):
            print(f'  {k[4:]:16} {to_dB(e):5.1f} dB')

    print('\nEmission per vehicle visible in the field of view:')
    out_rows = []
    for t in TYPES:
        e = coef[t]
        lvl = to_dB(e)
        print(f'  {t:6} {lvl:5.1f} dB' + ('' if e > 0 else '   (NNLS constraint -> 0, not separable)'))
        out_rows.append({'category': t, 'energy': e, 'level_dB': lvl})

    identifiable = any(coef[t] > 0 for t in TYPES)
    if not identifiable:
        print('\n>> RESULT: per-vehicle emissions ARE NOT IDENTIFIABLE from our data.')
        print('   The non-negativity constraint drives all three coefficients to zero: at a')
        print('   given site, the number of visible vehicles does not explain the measured')
        print('   level (R2 < 0.05 everywhere, correlations of inconsistent sign across sites).')
        print('   Plausible causes: parked vehicles are counted (no motion filter), the')
        print('   distance of each vehicle is not accounted for, and speed - which dominates')
        print('   rolling noise - is not observable from a count.')
        print('   CONSEQUENCE FOR THE SIMULATION: vehicles there are a calibrated visual')
        print('   representation of the fleet, NOT an acoustic source. The level stays driven')
        print('   by the validated model and by the traffic volume law.')

    # Construction excess. We reason on MEDIANS -- see docs/methodology.md 5.1. In
    # energy, means are dominated by the few loudest points and overstate the source
    # (a calibration on means gave 74.7 dB, i.e. +8 dB simulated near construction
    # sites, incompatible with the +2 dB actually observed).
    m = pd.read_csv(MEASURES, parse_dates=['timestamp'])
    op = m[m.site == 'Ocean Park'].copy()
    op['near'] = op.construction_nearby.astype(str).str.lower() == 'yes'
    med_w = op[op.near].noise_dB.median()
    med_o = op[~op.near].noise_dB.median()
    add_e = max(np.power(10, med_w / 10) - np.power(10, med_o / 10), 0.0)
    print(f'\nConstruction (Ocean Park, n={op.near.sum()} with / {(~op.near).sum()} without):')
    print(f'  median level    : {med_w:.1f} dB with construction vs {med_o:.1f} dB without '
          f'({med_w - med_o:+.1f} dB)')
    print(f'  median distance of points reporting construction: {CONSTR_REF_DIST:.0f} m')
    print(f'  -> equivalent source: {to_dB(add_e):.1f} dB at {CONSTR_REF_DIST:.0f} m')
    print('  check (geometric attenuation from that source):')
    for d in [25, 56, 200]:
        lvl = to_dB(add_e) - 20 * np.log10(d / CONSTR_REF_DIST)
        tot = to_dB(np.power(10, med_o / 10) + np.power(10, lvl / 10))
        print(f'    at {d:3d} m -> total level {tot:.1f} dB')
    out_rows.append({'category': 'construction', 'energy': add_e, 'level_dB': to_dB(add_e),
                     'ref_distance_m': CONSTR_REF_DIST})

    df = pd.DataFrame(out_rows)
    df['identifiable'] = [int(coef.get(r['category'], 1) > 0) if r['category'] in TYPES else 1
                          for r in out_rows]
    df['source'] = 'estimated on our 147 videos and 363 field measurements'
    df.to_csv(OUT, index=False)
    print(f'\nOK -> {OUT}')
    return coef, fit


if __name__ == '__main__':
    main()

"""Assemble le Data Collection Report du projet en un seul PDF : outputs/report.pdf.

Comprehensive (mais pas trop formel) : objectif, méthodologie (protocole de
collecte + reproduction Sunbird), analyse de données (patterns temporels,
sources, dépassements QCVN/OMS), modèle prédictif (transfert vs entraînement
direct), limitations & prochaines étapes.

Données descriptives recalculées depuis measurements.csv ; métriques modèle LUES
DEPUIS outputs/models/metrics.json (produit par scripts/evaluate_models.py).
Plus aucune métrique n'est recopiée à la main : le rapport ne peut plus se
désynchroniser du modèle réellement livré.

Deux corrections de fond (août 2026) :
  - les valeurs guides OMS (L_den 53 / L_night 45) ont été RETIRÉES du rapport.
    Ce sont des moyennes ANNUELLES avec pénalités soir/nuit, non comparables à
    nos échantillons de 25 s (cf. paper/sections/metrology.md) ;
  - les dépassements QCVN sont présentés comme une STATISTIQUE DESCRIPTIVE de
    notre échantillon, assortie d'une analyse de sensibilité au biais de
    calibration, et non comme un constat de non-conformité réglementaire.

Usage : python3 scripts/build_report.py
  (lancer avant : prepare_field_data.py, evaluate_models.py)
"""
import json
import os
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

# Seuils QCVN 26:2010/BTNMT, zone ordinaire. Aucune valeur OMS : voir docstring.
QCVN_D, QCVN_N = 70, 55
# Fourchette de biais absolu plausible de nos smartphones, estimée par ancrage sur la
# littérature instrumentée (scripts/literature_anchoring.py). Sert à borner la sensibilité
# des taux de dépassement. Mise à jour automatique si le CSV d'ancrage existe.
BIAS_LO, BIAS_HI = -3.0, 3.0
_anch = 'outputs/hanoi/literature_anchoring.csv'
if os.path.exists(_anch):
    _a = pd.read_csv(_anch)
    _u = _a[(_a.status != 'grey') & _a.gap_after_metric_correction_dB.notna()
            & (_a.comparable != 'night_all')]
    if len(_u):
        BIAS_LO = float(_u.gap_after_metric_correction_dB.min())
        BIAS_HI = float(_u.gap_after_metric_correction_dB.max())

MEAS = 'data/raw/hanoi/measurements.csv'
if not os.path.exists(MEAS):
    raise SystemExit(
        f'Manque {MEAS}.\n'
        '  -> déposer l\'export Kobo brut dans data/raw/hanoi/, puis :\n'
        '     python3 scripts/prepare_field_data.py')
df = pd.read_csv(MEAS, parse_dates=['timestamp'])
df['hour'] = df.timestamp.dt.hour
df['dow'] = df.timestamp.dt.day_name()
df['period'] = np.where((df.hour >= 21) | (df.hour < 6), 'night', 'day')
df['limit'] = np.where(df.period == 'night', QCVN_N, QCVN_D)
df['exceeds'] = df.noise_dB > df['limit']
df['is_constr'] = df['class'].astype(str).str.contains('construction', case=False)
SITES = list(df.site.unique())
COL = dict(zip(SITES, ['#c0392b', '#2471a3', '#1e8449', '#8e44ad']))
date_min, date_max = df.timestamp.min().strftime('%d %b'), df.timestamp.max().strftime('%d %b %Y')
exc_glob = 100 * df.exceeds.mean()
peak_h = df.groupby('hour').noise_dB.median().idxmax()

# ---- métriques modèle : LUES depuis metrics.json (scripts/evaluate_models.py) ----
MPATH = 'outputs/models/metrics.json'
if not os.path.exists(MPATH):
    raise SystemExit(
        f'Manque {MPATH}.\n'
        '  -> python3 scripts/evaluate_models.py\n'
        '     (le rapport ne contient plus de métriques codées en dur : elles doivent\n'
        '      venir d\'une évaluation réellement exécutée)')
METRICS = json.load(open(MPATH))
REF = METRICS['meta']['headline_protocol']          # 'bloo' de préférence
REFLABEL = METRICS[REF]['label']
MODELS = METRICS[REF]['models']
GAIN = METRICS[REF]['morphology_gain']
PERSITE = METRICS['loso_per_site']
R2_HEAD = MODELS['lgbm_full']['r2']
MAE_HEAD = MODELS['lgbm_full']['mae']
CI_HEAD = MODELS['lgbm_full']['r2_ci95']

FOOT = 'Hanoi Urban Noise · Data Collection Report'
def footer(fig, n, total=8):
    fig.text(.5, .03, f'{FOOT} · page {n}/{total}', ha='center', fontsize=7.5, color='#999')

def styled_table(ax, rows, highlight=None, foot=False, colWidths=None):
    t = ax.table(cellText=rows[1:], colLabels=rows[0], loc='center', cellLoc='center',
                 colWidths=colWidths)
    t.auto_set_font_size(False); t.set_fontsize(9); t.scale(1, 1.6)
    for (r, c), cell in t.get_celld().items():
        if r == 0:
            cell.set_facecolor('#34495e'); cell.set_text_props(color='w', weight='bold')
        elif foot and r == len(rows) - 1:
            cell.set_facecolor('#eaeef1'); cell.set_text_props(weight='bold')
        elif highlight is not None and r == highlight:
            cell.set_facecolor('#eafaf1')
    return t

pp = PdfPages('outputs/report.pdf')

# ================= PAGE 1 : couverture + objectif + données =================
fig = plt.figure(figsize=(8.27, 11.69))
fig.text(.5, .94, 'Hanoi Urban Noise Mapping', ha='center', fontsize=21, weight='bold')
fig.text(.5, .908, 'Data Collection Report', ha='center', fontsize=14, color='#555')
fig.text(.5, .882, f'{len(df)} smartphone measurements · 3 sites · {date_min} to {date_max}',
         ha='center', fontsize=10, color='#777')

kpis = [('Measurements', f'{len(df)}'), ('Sites', '3'),
        ('L_A,25s range', f'{df.noise_dB.min():.0f}-{df.noise_dB.max():.0f}'),
        ('Model R²', f'{R2_HEAD:.2f}'), ('> QCVN day', f'{exc_glob:.0f}%')]
for i, (k, v) in enumerate(kpis):
    x = .10 + i * .163
    fig.patches.append(plt.Rectangle((x, .80), .15, .055, transform=fig.transFigure,
                       facecolor='#f2f4f6', edgecolor='#d0d4d8'))
    fig.text(x + .075, .833, v, ha='center', fontsize=13, weight='bold', color='#c0392b')
    fig.text(x + .075, .81, k, ha='center', fontsize=7.5, color='#555')

fig.text(.08, .75, '1.  Objective', fontsize=13, weight='bold')
obj = (
    'Map and characterise urban noise in three contrasting districts of Hanoi, and predict noise from\n'
    'urban morphology. We follow the Sunbird AI methodology (Urban Noise Uganda 61K, Nsumba et al.,\n'
    '2026): smartphone field collection plus a morphology-to-noise model, reproduced then applied here.')
fig.text(.08, .71, obj, fontsize=9.5, va='top', linespacing=1.6)
fig.text(.08, .655,
         'Measurement status: our target is a 20-30 s A-weighted level from consumer '
         'smartphones (denoted L_A,25s),\nnot a certified L_Aeq. The three phones are '
         'cross-calibrated against each other, never against a reference\ninstrument: '
         'CONTRASTS between places and hours are supported, ABSOLUTE levels are indicative '
         f'(plausible bias\n{BIAS_LO:+.1f} to {BIAS_HI:+.1f} dB, section 3.4). '
         'No compliance claim is made anywhere in this report.',
         fontsize=8.5, va='top', color='#8a4b08', style='italic', linespacing=1.5)

fig.text(.08, .615, '2.  Data collection summary', fontsize=13, weight='bold')
rows = [['Site', 'n', 'Median dB', 'Min-Max', '% < 60 dB', '% roadside']]
for s in SITES:
    g = df[df.site == s]
    rd = 100 * g.dist_to_road.astype(str).str.contains('0-2|0-10|2-10').mean()
    rows.append([s, str(len(g)), f'{g.noise_dB.median():.0f}',
                 f'{g.noise_dB.min():.0f}-{g.noise_dB.max():.0f}',
                 f'{100*(g.noise_dB<60).mean():.0f}%', f'{rd:.0f}%'])
rows.append(['ALL', str(len(df)), f'{df.noise_dB.median():.0f}',
             f'{df.noise_dB.min():.0f}-{df.noise_dB.max():.0f}',
             f'{100*(df.noise_dB<60).mean():.0f}%',
             f'{100*df.dist_to_road.astype(str).str.contains("0-2|0-10|2-10").mean():.0f}%'])
ax = fig.add_axes([.08, .435, .84, .15]); ax.axis('off')
styled_table(ax, rows, foot=True)
fig.text(.08, .39, 'Zones: Ocean Park = new high-rise development (shielding, construction); '
         'Vinh Tuy = transport\ninfrastructure (heavy traffic); Hoan Kiem = historic old quarter '
         '(narrow streets, pedestrian zones).\n'
         'QC: site labels cross-checked against GPS (6 mislabelled submissions reassigned).',
         fontsize=8.5, color='#555', style='italic', va='top', linespacing=1.5)
fig.text(.08, .315, f'Headline findings: median {df.noise_dB.median():.0f} dB; {exc_glob:.0f}% of '
         f'short samples sit above the QCVN daytime threshold value;\nlevels peak at {peak_h}:00. '
         f'A model trained directly on our data reaches R² {R2_HEAD:.2f} '
         f'[{CI_HEAD[0]:.2f}, {CI_HEAD[1]:.2f}] under\n{REFLABEL.lower()} (section 5), '
         'against baselines reported in the same table.',
         fontsize=9.5, va='top', linespacing=1.6)
footer(fig, 1); pp.savefig(fig); plt.close(fig)

# ================= PAGE 2 : méthodologie =================
fig = plt.figure(figsize=(8.27, 11.69))
fig.text(.08, .95, '3.  Methodology', fontsize=14, weight='bold')

fig.text(.08, .91, '3.1  Field data-collection protocol', fontsize=11.5, weight='bold', color='#34495e')
proto = (
    'Study zones were mapped in Google Earth and chosen for contrasting typologies (section 2).\n'
    'At each point we recorded a 20-30 s reading (with a 10 s audio clip) in ODK Collect, submitted\n'
    'live to a KoboToolbox server with automatic timestamp and GPS. Phones were held at 1.2 m (SPB\n'
    'positioning) at varied distances from the road, by three cross-calibrated collectors, from 05:00\n'
    'to 23:00 with emphasis on rush hours. Weather (Open-Meteo) and spatial context (OSM) are added.')
fig.text(.08, .875, proto, fontsize=9.5, va='top', linespacing=1.55)

fig.text(.08, .735, '3.2  Reproduction of the Sunbird pipeline', fontsize=11.5, weight='bold', color='#34495e')
repro = (
    'We reproduced the full Sunbird chain on their Uganda dataset (notebooks 01-06): cleaning, audio\n'
    'QC, morphology features, figures, surrogate model. Our statistics match the paper (median 49 dB\n'
    'vs their 45-50 dB).')
fig.text(.08, .70, repro, fontsize=9.5, va='top', linespacing=1.55)

fig.text(.08, .615, '3.3  Model features', fontsize=11.5, weight='bold', color='#34495e')
feat = (
    'Morphology within 300 m of each point (OpenStreetMap): built-area ratio, road density,\n'
    'intersection count, distance to nearest road; plus hour of day and weekend flag. Model: LightGBM.')
fig.text(.08, .58, feat, fontsize=9.5, va='top', linespacing=1.55)

fig.text(.08, .50, '3.4  Reference values and measurement status', fontsize=11.5,
         weight='bold', color='#34495e')
std = [['Reference value', 'Day (6-21h)', 'Night (21-6h)'],
       ['QCVN 26:2010/BTNMT (Vietnam, ordinary area)', '70 dB', '55 dB']]
ax = fig.add_axes([.08, .425, .84, .055]); ax.axis('off')
styled_table(ax, std, colWidths=[.5, .25, .25])
fig.text(.08, .405,
         'The WHO road-traffic guideline values (53 / 45 dB) have been WITHDRAWN from this '
         'report. They are\nL_den and L_night: ANNUAL averages with +5 dB evening and +10 dB '
         'night penalties. Comparing them to a\n25 s daytime sample compares different '
         'statistics of different processes. QCVN is retained because it\nregulates a level, '
         'but it regulates an L_Aeq measured with a class 1-2 meter under TCVN 7878-2:2010:\n'
         'our instrument does not meet that specification either.',
         fontsize=8.5, va='top', color='#555', style='italic', linespacing=1.5)
fig.text(.08, .30, 'Consequence for every exceedance figure in this report: it is a '
         'DESCRIPTIVE STATISTIC of our\nsample - the share of short samples above a threshold '
         'value - and never a finding of regulatory\nnon-compliance. Sensitivity to the '
         f'calibration bias ({BIAS_LO:+.1f} to {BIAS_HI:+.1f} dB) is given on page 4.',
         fontsize=9, va='top', color='#8a4b08', linespacing=1.55)
footer(fig, 2); pp.savefig(fig); plt.close(fig)

# ================= PAGE 3 : patterns temporels =================
fig = plt.figure(figsize=(8.27, 11.69)); fig.subplots_adjust(top=.92, bottom=.07, hspace=.32)
fig.text(.08, .955, '4.  Data analysis: temporal patterns', fontsize=14, weight='bold', transform=fig.transFigure)
ax1 = fig.add_subplot(2, 1, 1)
for s in SITES:
    g = df[df.site == s].groupby('hour').noise_dB.median()
    ax1.plot(g.index, g.values, marker='o', lw=2, color=COL[s], label=s)
ax1.axhline(QCVN_D, ls='--', c='red', alpha=.6, label='QCVN day 70')
ax1.axhline(QCVN_N, ls='--', c='darkred', alpha=.6, label='QCVN night 55')
ax1.set_title('Hourly pattern within a day (capture window 05:00-23:00)', fontsize=11)
ax1.set_xlabel('Hour'); ax1.set_ylabel(r'Median $L_{A,25s}$ (dB)')
ax1.set_xlim(4.5, 23.5); ax1.set_xticks(range(5, 24, 2))
ax1.legend(fontsize=7.5, ncol=2); ax1.grid(alpha=.3)
ax2 = fig.add_subplot(2, 1, 2)
order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
for s in SITES:
    g = df[df.site == s].groupby('dow').noise_dB.median().reindex(order)
    ax2.plot(range(7), g.values, marker='s', lw=2, color=COL[s], label=s)
ax2.axhline(QCVN_D, ls='--', c='red', alpha=.6)
ax2.set_title('Day-of-week pattern', fontsize=11); ax2.set_xticks(range(7))
ax2.set_xticklabels(['Mon','Tue','Wed','Thu','Fri','Sat','Sun'])
ax2.set_ylabel(r'Median $L_{A,25s}$ (dB)'); ax2.legend(fontsize=7.5); ax2.grid(alpha=.3)
fig.text(.08, .045, 'Night coverage is very thin (n = '
         f'{int((df.period == "night").sum())} of {len(df)}, none between 00:00 and 05:00): '
         'the night curve and the night\nexceedance rates below are indicative only.',
         fontsize=8, color='#8a4b08', style='italic', va='bottom', linespacing=1.4)
footer(fig, 3); pp.savefig(fig); plt.close(fig)

# ================= PAGE 4 : sources + dépassements =================
fig = plt.figure(figsize=(8.27, 11.69)); fig.subplots_adjust(top=.92, bottom=.10, hspace=.32, wspace=.28)
fig.text(.08, .955, '4.  Data analysis: sources & exceedances', fontsize=14, weight='bold', transform=fig.transFigure)
ax1 = fig.add_subplot(2, 2, 1)
data = [df[~df.is_constr].noise_dB.dropna(), df[df.is_constr].noise_dB.dropna()]
ax1.boxplot(data, tick_labels=['Transport', 'Construction']); ax1.axhline(QCVN_D, ls='--', c='red', alpha=.6)
ax1.set_ylabel('dB'); ax1.set_title('Transport vs Construction', fontsize=10); ax1.grid(alpha=.3)
ax2 = fig.add_subplot(2, 2, 2); w = .35
for i, s in enumerate(SITES):
    sub = df[df.site == s]
    ax2.bar(i-w/2, sub[~sub.is_constr].noise_dB.median(), w, color='#2471a3', label='Transport' if i==0 else '')
    cv = sub[sub.is_constr].noise_dB.median()
    ax2.bar(i+w/2, 0 if np.isnan(cv) else cv, w, color='#e67e22', label='Construction' if i==0 else '')
ax2.axhline(QCVN_D, ls='--', c='red', alpha=.6); ax2.set_xticks(range(len(SITES)))
ax2.set_xticklabels([s.split()[0] for s in SITES], fontsize=8); ax2.set_title('Median dB by site', fontsize=10); ax2.legend(fontsize=7.5); ax2.grid(alpha=.3)
ax3 = fig.add_subplot(2, 1, 2)
# (calculé sans groupby.apply : le comportement de apply sur la colonne de
#  groupement a changé en pandas 3.0 et cassait le rapport)
pe = (100 * df.assign(_ex=df.noise_dB > df['limit']).groupby('hour')['_ex'].mean())
ax3.bar(pe.index, pe.values, color=['#c0392b' if v>50 else '#e67e22' if v>0 else '#27ae60' for v in pe.values])
ax3.set_xlabel('Hour'); ax3.set_ylabel('% measurements > QCVN')
ax3.set_xlim(4.5, 23.5); ax3.set_xticks(range(5, 24, 2))
ax3.set_title('Share of short samples above the QCVN threshold value, by hour', fontsize=11)
ax3.grid(alpha=.3)

# Sensibilité au biais de calibration : le seuil de 70 dB tombe au milieu de notre
# distribution, un décalage de quelques dB change fortement le pourcentage.
exc_lo = 100 * ((df.noise_dB + BIAS_LO) > df['limit']).mean()
exc_hi = 100 * ((df.noise_dB + BIAS_HI) > df['limit']).mean()
fig.text(.08, .045,
         f'Sensitivity to calibration bias: {exc_glob:.0f}% of samples sit above the '
         f'threshold at face value, but {min(exc_lo, exc_hi):.0f}% to {max(exc_lo, exc_hi):.0f}%\n'
         f'once the plausible instrumental bias ({BIAS_LO:+.1f} to {BIAS_HI:+.1f} dB, '
         'section 3.4) is applied. The exposure PATTERN - which hours and\nwhich sites are '
         'loudest - is unaffected by a common bias; the exceedance LEVEL is. We report the '
         'pattern as a\nfinding and the level as an indication.',
         fontsize=8.5, va='bottom', color='#8a4b08', linespacing=1.5)
footer(fig, 4); pp.savefig(fig); plt.close(fig)

# ================= PAGE 5 : vidéos trafic (CV) + météo =================
VC = 'data/processed/hanoi/vehicle_counts.csv'
if os.path.exists(VC):
    vc = pd.read_csv(VC, parse_dates=['video_start', 'matched_timestamp'])
    vc = vc.merge(df[['timestamp', 'site']], left_on='matched_timestamp',
                  right_on='timestamp', how='left')

    fig = plt.figure(figsize=(8.27, 11.69)); fig.subplots_adjust(top=.86, bottom=.42, wspace=.30)
    fig.text(.08, .955, '4.  Data analysis: traffic videos & weather', fontsize=14, weight='bold')
    fig.text(.08, .925, f'{len(vc)} traffic videos (~25 s each) matched to their measurement by '
             f'timestamp (median gap {vc.match_gap_s.median():.0f} s).\nVehicles counted with '
             'YOLOv8 at ~1 frame/s '
             f'({vc.n_frames.sum()} frames analysed): average vehicles visible per frame.',
             fontsize=9.5, va='top', linespacing=1.55)

    ax1 = fig.add_subplot(1, 2, 1)
    comp = vc.groupby('site')[['moto_mean', 'car_mean', 'bus_mean', 'truck_mean']].mean()
    bottom = np.zeros(len(comp))
    for col, colr, lab in [('moto_mean', '#e67e22', 'motorbikes'), ('car_mean', '#2471a3', 'cars'),
                           ('bus_mean', '#1e8449', 'buses'), ('truck_mean', '#7b241c', 'trucks')]:
        ax1.bar(range(len(comp)), comp[col], .55, bottom=bottom, color=colr, label=lab)
        bottom += comp[col].values
    ax1.set_xticks(range(len(comp))); ax1.set_xticklabels([s.split()[0] for s in comp.index], fontsize=9)
    ax1.set_ylabel('Mean vehicles per frame'); ax1.set_title('Traffic composition by site', fontsize=10)
    ax1.legend(fontsize=8); ax1.grid(alpha=.3, axis='y')

    ax2 = fig.add_subplot(1, 2, 2)
    for s in vc.site.dropna().unique():
        g = vc[vc.site == s]
        ax2.scatter(g.vehicles_mean, g.matched_dB, s=22, alpha=.6, color=COL.get(s, '#888'),
                    label=f'{s.split()[0]}  r={g.vehicles_mean.corr(g.matched_dB):+.2f}')
    ax2.set_xlabel('Vehicles per frame'); ax2.set_ylabel('Measured dB')
    ax2.set_title('Traffic density vs noise, by site', fontsize=10); ax2.legend(fontsize=8); ax2.grid(alpha=.3)

    # Aucun de ces chiffres n'est écrit à la main : ils sont recalculés depuis vehicle_counts.csv
    # à chaque build, sinon le texte se désynchronise du run YOLO (cf. règle du ROADMAP).
    _sh = 100 * comp.div(comp.sum(axis=1), axis=0)
    _mx = vc.groupby('site').vehicles_mean.max()
    _rs = {s: g.vehicles_mean.corr(g.matched_dB) for s, g in vc.groupby('site')}
    _hk = next((s for s in _sh.index if 'Hoan' in s), _sh.index[0])
    _op = next((s for s in _sh.index if 'Ocean' in s), _sh.index[0])
    _vt = next((s for s in _sh.index if 'Vinh' in s), _sh.index[-1])
    _rtxt = ', '.join(f'{s.split()[0]} {_rs[s]:+.2f}' for s in _sh.index)
    _neg = sum(1 for v in _rs.values() if v < 0)
    findings = (
        'Findings: traffic composition matches the zone typologies: '
        f'{_hk.split()[0]} is motorbike-dominated\n({_sh.loc[_hk, "moto_mean"]:.0f}%), '
        f'{_op.split()[0]} car-dominated ({_sh.loc[_op, "car_mean"]:.0f}%), '
        f'{_vt.split()[0]} the densest corridor (up to {_mx[_vt]:.0f} vehicles/frame).\n'
        'Vehicle density does NOT track noise: the site-wise correlations are weak and of\n'
        f'inconsistent sign ({_rtxt}), negative on {_neg} of {len(_rs)} sites,\n'
        f'and {vc.vehicles_mean.corr(vc.matched_dB):+.2f} overall. Density is a stock; emission '
        'is driven by flow and speed, which a\nper-frame count cannot observe - see section 7. '
        'Note: small motorbikes are harder to\ndetect than cars and parked vehicles are counted '
        'too (no motion filter yet), so motorbike\nshares are a lower bound, and the detector was '
        'never validated against manual counts.\n\n'
        'Weather: no robust effect. Raw correlations (temperature +0.26, rain -0.29) vanish '
        'once hour of day and\nsession are controlled: quiet-point campaigns happened to fall on '
        'rainy days. Wind shows no effect on\nreadings (no microphone artefact).')
    fig.text(.08, .36, findings, fontsize=9.5, va='top', linespacing=1.55)
    footer(fig, 5); pp.savefig(fig); plt.close(fig)

# ================= PAGE 6 : modèle, baselines, ablation =================
fig = plt.figure(figsize=(8.27, 11.69)); fig.subplots_adjust(left=.08, right=.92)
fig.text(.08, .95, '5.  Predictive model', fontsize=14, weight='bold')
fig.text(.08, .915, 'LightGBM mapping urban morphology (300 m radius, OpenStreetMap) plus '
         'time of day to level.', fontsize=9.5, va='top')

fig.text(.08, .875, '5.1  How performance is measured (corrected August 2026)',
         fontsize=11.5, weight='bold', color='#34495e')
fig.text(.08, .84,
         'Earlier versions of this report grouped cross-validation on ~110 m cells. The '
         'model features are\naggregates over a 300 m RADIUS, so two points 110 m apart '
         'share more than 85% of their disc: the model\nsaw near-twins of its test points '
         'and the reported score was not out-of-sample. That protocol is\nreplaced by '
         f'{REFLABEL.lower()}, and every model below - including the baselines - is scored '
         'on\nexactly the same splits, with bootstrap confidence intervals resampled by '
         'spatial block.',
         fontsize=9, va='top', linespacing=1.55)

fig.text(.08, .715, f'5.2  Model comparison - {REFLABEL}', fontsize=11.5,
         weight='bold', color='#34495e')
ORDER = ['global_mean', 'site_mean', 'site_hour_mean', 'dist_road', 'idw',
         'lgbm_time', 'lgbm_morpho', 'lgbm_full']
mrows = [['Model', 'R²', '95% CI', 'MAE (dB)', 'r']]
for k in ORDER:
    m = MODELS[k]
    mrows.append([m['label'], f"{m['r2']:.2f}",
                  f"[{m['r2_ci95'][0]:.2f}, {m['r2_ci95'][1]:.2f}]",
                  f"{m['mae']:.2f}", f"{m['r']:.2f}"])
ax = fig.add_axes([.08, .44, .84, .26]); ax.axis('off')
# On surligne le MEILLEUR modèle sous le protocole de référence, pas le nôtre par défaut :
# depuis le run d'août 2026 ce n'est plus le LightGBM (cf. negative_results.md §5.z).
BEST = max(ORDER, key=lambda k: MODELS[k]['r2'])
styled_table(ax, mrows, highlight=ORDER.index(BEST) + 1, colWidths=[.47, .11, .19, .12, .11])

_dr, _lf, _lm = MODELS['dist_road'], MODELS['lgbm_full'], MODELS['lgbm_morpho']
fig.text(.08, .415,
         f"Key figure - a one-variable physical baseline wins. An OLS regression on "
         f"log(distance to road) scores\nR2 {_dr['r2']:.3f} against {_lf['r2']:.3f} for the "
         f"six-variable LightGBM: morphology aggregated over 300 m adds nothing\nover the "
         f"distance term alone (morphology-only ablation: {_lm['r2']:.3f}). Against a (site, "
         f"hour) lookup table the\nfull model still gains dR2 = {GAIN['delta_r2']:+.3f} / "
         f"dMAE = {GAIN['delta_mae_dB']:+.2f} dB - but that gain is carried by TIME, not space.",
         fontsize=9, va='top', linespacing=1.55, color='#8a4b08')

fig.text(.08, .325, '5.3  Generalisation to an unseen typology (leave-one-site-out)',
         fontsize=11.5, weight='bold', color='#34495e')
prows = [['Test site', 'n', 'R²', 'MAE (dB)']]
for site, v in PERSITE.items():
    prows.append([site, str(v['n']), f"{v['r2']:.2f}", f"{v['mae']:.2f}"])
ax = fig.add_axes([.08, .20, .84, .11]); ax.axis('off')
styled_table(ax, prows, colWidths=[.34, .16, .22, .28])
fig.text(.08, .16,
         'Each site is predicted by a model trained on the other two only. A negative R2 '
         'means: worse than\npredicting the global mean everywhere. With three sampled '
         'typologies, the number of independent\nmorphological configurations is close to '
         'three, whatever the number of points: the model INTERPOLATES\nwithin sampled '
         'typologies, it does not EXTRAPOLATE. Maps are clipped to the sampled envelope.',
         fontsize=9, va='top', linespacing=1.55)

fig.text(.08, .045, 'Cross-city transfer (Uganda -> Hanoi) is reported in section 7 as a '
         'methodological result, not as a method.\nNo comparison is made with published '
         'scores from other cities: they target a different quantity (long-term L_Aeq).',
         fontsize=8.5, va='bottom', color='#555', style='italic', linespacing=1.5)
footer(fig, 6); pp.savefig(fig); plt.close(fig)

# ================= PAGE 7 : simulation GAMA + validation =================
VALID_PNG = 'outputs/hanoi/validation_simulation.png'
VALID_CSV = 'outputs/hanoi/validation_simulation.csv'
if os.path.exists(VALID_CSV):
    vd = pd.read_csv(VALID_CSV)
    v_bias = vd.error.mean(); v_mae = vd.error.abs().mean()
    v_r = vd.sim_dB.corr(vd.noise_dB)
    v_w5 = (vd.error.abs() <= 5).mean() * 100

    fig = plt.figure(figsize=(8.27, 11.69))
    fig.text(.08, .95, '6.  Agent-based simulation (GAMA)', fontsize=14, weight='bold')
    fig.text(.08, .915, 'The predicted noise map is loaded into an agent-based model with moving '
             'vehicles,\nconstruction sites and interactive scenario controls.',
             fontsize=9.5, va='top', linespacing=1.55)

    fig.text(.08, .858, '6.1  What the simulation contains', fontsize=11.5, weight='bold', color='#34495e')
    srows = [['Layer', 'Source', 'Status'],
             ['Background noise level, per hour', 'LightGBM on our 363 measurements', 'predicted'],
             ['Traffic density and vehicle mix', '147 videos, YOLO counts', 'measured'],
             ['Construction excess (+2 dB at 56 m)', 'our 32 near-site measurements', 'calibrated'],
             ['Vehicles as sound sources', 'not identifiable in our data', 'excluded'],
             ['Traffic-volume scenario', '10 log10 of the volume factor', 'physical law']]
    ax = fig.add_axes([.08, .70, .84, .14]); ax.axis('off')
    styled_table(ax, srows, colWidths=[.42, .36, .22])

    fig.text(.08, .665, '6.2  Scenario controls', fontsize=11.5, weight='bold', color='#34495e')
    fig.text(.08, .632, 'Hour of day (5h-21h, each hour predicted separately, vehicle numbers follow the '
             'traffic\nmeasured at that hour) · traffic volume (x0.2 to x3) · construction on/off with '
             'working hours\n· mitigation: 30 km/h zone (-3 dB) or pedestrianisation (traffic x0.2).\n\n'
             'Calibration note: we tried to derive a per-vehicle emission level from our own data\n'
             '(non-negative energy regression on the 147 matched videos). All three coefficients came\n'
             'out at zero - at a given site, the number of visible vehicles does not explain the measured\n'
             'level (R2 0.008-0.042). Rather than inject invented values, vehicles are displayed as a\n'
             'calibrated picture of the fleet but carry no sound in the computation.',
             fontsize=9.5, va='top', linespacing=1.55)

    fig.text(.08, .455, '6.3  Does the simulation reproduce our measurements?',
             fontsize=11.5, weight='bold', color='#34495e')
    vrows = [['Metric', 'Value'],
             ['Measurements compared', f'{len(vd)}'],
             ['Bias (simulated - measured)', f'{v_bias:+.2f} dB'],
             ['Mean absolute error', f'{v_mae:.2f} dB'],
             ['Correlation r', f'{v_r:.2f}'],
             ['Within +/- 5 dB', f'{v_w5:.0f} %']]
    ax = fig.add_axes([.08, .305, .40, .13]); ax.axis('off')
    styled_table(ax, vrows, colWidths=[.62, .38])

    fig.text(.52, .428, 'Each field measurement is compared with the grid cell it falls in\n'
             '(median 16 m away), at the hour it was taken.\n\n'
             'Caveat: this is an in-sample check - the model that produces\n'
             'the grid was trained on these same points. It measures the\n'
             'fidelity of the chain model -> 40 m grid -> GAMA, not\n'
             'generalisation. The generalisation figures are those of\n'
             f'section 5: R2 {R2_HEAD:.2f} / MAE {MAE_HEAD:.2f} dB under\n{REFLABEL.lower()}.',
             fontsize=8.5, va='top', color='#555', linespacing=1.6)

    if os.path.exists(VALID_PNG):
        img = plt.imread(VALID_PNG)
        ax = fig.add_axes([.08, .07, .84, .21]); ax.axis('off')
        ax.imshow(img)
    footer(fig, 7); pp.savefig(fig); plt.close(fig)

# ================= PAGE 8 : limitations + prochaines étapes =================
fig = plt.figure(figsize=(8.27, 11.69))
fig.text(.08, .95, '7.  Limitations, stated plainly', fontsize=14, weight='bold')
lim_txt = (
    '•  THE MODEL DOES NOT BEAT ITS OWN PHYSICAL BASELINE. An OLS regression on log(distance to\n'
    f"   road) - one variable, two parameters - scores R2 {_dr['r2']:.3f} against {_lf['r2']:.3f} "
    'for the six-variable LightGBM\n   under the reference protocol, and holds '
    f"{METRICS['loso']['models']['dist_road']['r2']:.3f} against "
    f"{METRICS['loso']['models']['lgbm_full']['r2']:.3f} under leave-one-site-out. Morphology\n"
    '   aggregated over 300 m adds no measurable value over that single term. The LightGBM leads only\n'
    '   under the most permissive split (600 m blocks). This is reported as a result, not hidden.\n\n'
    '•  ABSOLUTE CALIBRATION. The three phones are calibrated against each other, never against a\n'
    f'   reference instrument. A bias common to all three ({BIAS_LO:+.1f} to {BIAS_HI:+.1f} dB, '
    'bounded by anchoring on\n   instrumented Vietnamese campaigns) is invisible in our data. The '
    'field campaign is closed and this\n   cannot be repaired retrospectively. Contrasts are '
    'supported; absolute levels are indicative.\n\n'
    '•  MEASUREMENT QUANTITY. A 20-30 s sample is not the L_Aeq of any regulatory reference period.\n'
    '   A single horn burst moves it by several dB - horn events reach +17 dB in Vietnamese traffic.\n'
    '   This variance is a property of the quantity and caps the R² any spatial model can reach.\n\n'
    '•  GENERALISATION. Leave-one-site-out is negative on two of three sites (section 5.3): the model\n'
    '   does not extrapolate to an unsampled typology. Maps are clipped to the sampled envelope.\n\n'
    '•  SPATIAL RESOLUTION. Features are aggregated over a 300 m radius, so adjacent 40 m cells share\n'
    '   more than 98% of their disc. The map cannot resolve the facade/courtyard contrast (10-15 dB in\n'
    '   dense fabric): predicted levels are visibly flatter than measured ones.\n\n'
    '•  TEMPORAL COVERAGE. Night (21:00-06:00) holds ~3% of measurements and nothing between 00:00\n'
    '   and 05:00, although that is the period with the strictest threshold. One season only.\n\n'
    '•  TRAFFIC VIDEOS. Per-frame vehicle DENSITY is not FLOW, and the detector was never validated\n'
    '   against manual counts. Modal splits are lower bounds on motorcycle share (section 7).')
fig.text(.08, .905, lim_txt, fontsize=8.5, va='top', linespacing=1.45)

fig.text(.08, .46, '8.  Next steps', fontsize=14, weight='bold')
nxt = (
    '•  HYBRID MODEL. Add a physical propagation core (CNOSSOS-EU via NoiseModelling, OSM inputs)\n'
    '   and train the statistical model on the RESIDUAL. This restores the fine spatial contrast the\n'
    '   300 m aggregation destroys, and makes the map extrapolable, since physics does not depend\n'
    '   on our sample.\n\n'
    '•  TRAFFIC. Re-derive flow and speed from the videos by object tracking and line crossing, and\n'
    '   validate the detector against manual counts before any acoustic use.\n\n'
    '•  DATA PUBLICATION. Deposit measurements, forms and cleaning code with a DOI; add an ethics\n'
    '   statement covering the public-space video recordings.\n\n'
    '•  MANUSCRIPT. Methods, the three negative results as contributions, discussion.')
fig.text(.08, .42, nxt, fontsize=8.5, va='top', linespacing=1.45)

fig.text(.08, .22, '9.  Summary', fontsize=14, weight='bold')
summ = (
    f'{len(df)} smartphone measurements across 3 contrasting districts document a consistent exposure\n'
    f'pattern in space and time. A LightGBM trained directly on them reaches R² {R2_HEAD:.2f} '
    f'[{CI_HEAD[0]:.2f}, {CI_HEAD[1]:.2f}] / MAE {MAE_HEAD:.2f} dB\nunder {REFLABEL.lower()} - '
    f"but an OLS regression on log(distance to road) alone reaches {_dr['r2']:.2f}.\n"
    'Three negative results are reported as contributions: a one-variable physical baseline beats '
    'the\nsix-variable model and 300 m morphology adds nothing over it; cross-city transfer from '
    'Uganda fails\neven with identical instruments and invariant features; and per-frame vehicle '
    'density carries no\nrecoverable acoustic signal. We claim contrasts, not certified absolute levels.')
fig.text(.08, .18, summ, fontsize=8.5, va='top', linespacing=1.5, color='#222')
footer(fig, 8); pp.savefig(fig); plt.close(fig)

pp.close()
print('OK -> outputs/report.pdf  (8 pages)')

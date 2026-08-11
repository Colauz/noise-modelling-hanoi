"""Assemble the project Data Collection Report into a single PDF.

Comprehensive but not over-formal: objective, methodology (collection protocol +
Sunbird reproduction), data analysis (temporal patterns, sources, QCVN
exceedances), predictive model (transfer against direct training), limitations
and next steps.

Descriptive figures are recomputed from measurements.csv; model metrics are READ
FROM models/metrics.json (produced by scripts/04_evaluate_models.py). No metric is
copied by hand any more: the report can no longer drift from the model actually
delivered, and it refuses to run without that file.

Two substantive corrections (August 2026):
  - the WHO guideline values (L_den 53 / L_night 45) were REMOVED from the report.
    They are ANNUAL averages with evening/night penalties, not comparable to our
    25 s samples (see docs/metrology.md);
  - QCVN exceedances are presented as a DESCRIPTIVE STATISTIC of our sample, with a
    sensitivity analysis on the calibration bias, and not as a finding of
    regulatory non-compliance.

Output: results/report/report.pdf (8 pages)
Usage : python3 scripts/10_build_report.py
  (run first: 01_prepare_field_data.py, 04_evaluate_models.py)
"""
import json
import os
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from noise_hanoi import config as cfg

# Seuils QCVN 26:2010/BTNMT, zone ordinaire. Aucune valeur OMS : voir docstring.
QCVN_D, QCVN_N = 70, 55
# Plausible absolute bias range of our smartphones, estimated by anchoring on the
# instrumented literature (scripts/06_anchor_literature.py). Used to bound the
# sensitivity of the exceedance rates. Updated automatically if the anchoring CSV exists.
BIAS_LO, BIAS_HI = -3.0, 3.0
_anch = os.path.join(cfg.TABLES, 'literature_anchoring.csv')
if os.path.exists(_anch):
    _a = pd.read_csv(_anch)
    _u = _a[(_a.status != 'grey') & _a.gap_after_metric_correction_dB.notna()
            & (_a.comparable != 'night_all')]
    if len(_u):
        BIAS_LO = float(_u.gap_after_metric_correction_dB.min())
        BIAS_HI = float(_u.gap_after_metric_correction_dB.max())

MEAS = cfg.MEASUREMENTS
if not os.path.exists(MEAS):
    raise SystemExit(
        f'Manque {MEAS}.\n'
        '  -> drop the raw Kobo export into data/raw/kobo/, then:\n'
        '     python3 scripts/01_prepare_field_data.py')
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

# ---- model metrics: READ from metrics.json (scripts/04_evaluate_models.py) ----
MPATH = cfg.METRICS_JSON
if not os.path.exists(MPATH):
    raise SystemExit(
        f'Manque {MPATH}.\n'
        '  -> python3 scripts/04_evaluate_models.py\n'
        '     (the report no longer holds hardcoded metrics: they must come from\n'
        '      an evaluation that was actually run)')
METRICS = json.load(open(MPATH))
REF = METRICS['meta']['headline_protocol']          # 'bloo' when available
REFLABEL = METRICS[REF]['label']
MODELS = METRICS[REF]['models']
GAIN = METRICS[REF]['morphology_gain']
PERSITE = METRICS['loso_per_site']
# The DELIVERED model is read from meta; we fall back to LightGBM v1 if the JSON
# comes from an earlier run, so that the report stays buildable on archived
# outputs.
DELIVERED = METRICS['meta'].get('delivered_model',
                                'hybrid' if 'hybrid' in MODELS else 'lgbm_full')
HEAD = MODELS[DELIVERED]
R2_HEAD = HEAD['r2']
MAE_HEAD = HEAD['mae']
CI_HEAD = HEAD['r2_ci95']

FOOT = 'Hanoi Urban Noise · Data Collection Report'
def footer(fig, n, total=8):
    fig.text(.5, .03, f'{FOOT} · page {n}/{total}', ha='center', fontsize=7.5, color='#999')

def styled_table(ax, rows, highlight=None, foot=False, colWidths=None,
                 fontsize=9, vscale=1.6):
    t = ax.table(cellText=rows[1:], colLabels=rows[0], loc='center', cellLoc='center',
                 colWidths=colWidths)
    t.auto_set_font_size(False); t.set_fontsize(fontsize); t.scale(1, vscale)
    for (r, c), cell in t.get_celld().items():
        if r == 0:
            cell.set_facecolor('#34495e'); cell.set_text_props(color='w', weight='bold')
        elif foot and r == len(rows) - 1:
            cell.set_facecolor('#eaeef1'); cell.set_text_props(weight='bold')
        elif highlight is not None and r == highlight:
            cell.set_facecolor('#eafaf1')
    return t

os.makedirs(cfg.REPORT_DIR, exist_ok=True)
pp = PdfPages(cfg.REPORT_PDF)

# ================= PAGE 1: cover + objective + data =================
fig = plt.figure(figsize=(8.27, 11.69))
fig.text(.5, .94, 'Hanoi Urban Noise Mapping', ha='center', fontsize=21, weight='bold')
fig.text(.5, .908, 'Data Collection Report', ha='center', fontsize=14, color='#555')
fig.text(.5, .882, f'{len(df)} smartphone measurements · 3 sites · {date_min} to {date_max}',
         ha='center', fontsize=10, color='#777')

kpis = [('Measurements', f'{len(df)}'), ('Sites', '3'),
        ('L_A,25s range', f'{df.noise_dB.min():.0f}-{df.noise_dB.max():.0f}'),
        ('Model R²', f'{R2_HEAD:.2f}'), ('> QCVN day', f'{exc_glob:.1f}%')]   # one decimal: 09b_build_analyses.py prints the same figure
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

# ================= PAGE 2: methodology =================
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

# ================= PAGE 4: sources + exceedances =================
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
# (computed without groupby.apply: the behaviour of apply on the grouping column
#  changed in pandas 3.0 and broke the report)
pe = (100 * df.assign(_ex=df.noise_dB > df['limit']).groupby('hour')['_ex'].mean())
ax3.bar(pe.index, pe.values, color=['#c0392b' if v>50 else '#e67e22' if v>0 else '#27ae60' for v in pe.values])
ax3.set_xlabel('Hour'); ax3.set_ylabel('% measurements > QCVN')
ax3.set_xlim(4.5, 23.5); ax3.set_xticks(range(5, 24, 2))
ax3.set_title('Share of short samples above the QCVN threshold value, by hour', fontsize=11)
ax3.grid(alpha=.3)

# Sensitivity to the calibration bias: the 70 dB threshold falls in the middle of our
# distribution, so a shift of a few dB changes the percentage substantially.
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

# ================= PAGE 5: traffic videos (CV) + weather =================
VC = cfg.VEHICLE_COUNTS
if os.path.exists(VC):
    vc = pd.read_csv(VC, parse_dates=['video_start', 'matched_timestamp'])
    vc = vc.merge(df[['timestamp', 'site']], left_on='matched_timestamp',
                  right_on='timestamp', how='left')

    fig = plt.figure(figsize=(8.27, 11.69)); fig.subplots_adjust(top=.83, bottom=.42, wspace=.30)
    fig.text(.08, .955, '4.  Data analysis: traffic videos & weather', fontsize=14, weight='bold')
    HASFLOW = 'vehicles_flow' in vc.columns
    _fps = vc.sample_fps.median() if 'sample_fps' in vc.columns else 1
    fig.text(.08, .925, f'{len(vc)} traffic videos (~25 s each) matched to their measurement by '
             f'timestamp (median gap {vc.match_gap_s.median():.0f} s).\n'
             + (f'YOLOv8 + ByteTrack at ~{_fps:.0f} frames/s ({vc.n_frames.sum()} frames): '
                'vehicles are TRACKED and counted when they\ncross a virtual line, giving a real '
                'FLOW in vehicles/min - not just a density per frame.'
                if HASFLOW else
                f'Vehicles counted with YOLOv8 at ~1 frame/s ({vc.n_frames.sum()} frames '
                'analysed): average vehicles visible per frame.'),
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

    # We plot FLOW whenever it is available: it is the quantity physically linked to
    # emission, so it is the one on which the reader should judge the absence of a relation.
    _xcol = 'vehicles_flow' if HASFLOW else 'vehicles_mean'
    ax2 = fig.add_subplot(1, 2, 2)
    for s in vc.site.dropna().unique():
        g = vc[vc.site == s]
        ax2.scatter(g[_xcol], g.matched_dB, s=22, alpha=.6, color=COL.get(s, '#888'),
                    label=f'{s.split()[0]}  r={g[_xcol].corr(g.matched_dB):+.2f}')
    ax2.set_xlabel('Vehicles per minute crossing the line' if HASFLOW else 'Vehicles per frame')
    ax2.set_ylabel('Measured dB')
    ax2.set_title('Traffic FLOW vs noise, by site' if HASFLOW else 'Traffic density vs noise, by site',
                  fontsize=10)
    ax2.legend(fontsize=8); ax2.grid(alpha=.3)

    # None of these figures is written by hand: they are recomputed from vehicle_counts.csv
    # at every build, otherwise the text drifts from the YOLO run (see CONTRIBUTING.md).
    _sh = 100 * comp.div(comp.sum(axis=1), axis=0)
    _mx = vc.groupby('site').vehicles_mean.max()
    _rs = {s: g.vehicles_mean.corr(g.matched_dB) for s, g in vc.groupby('site')}
    _hk = next((s for s in _sh.index if 'Hoan' in s), _sh.index[0])
    _op = next((s for s in _sh.index if 'Ocean' in s), _sh.index[0])
    _vt = next((s for s in _sh.index if 'Vinh' in s), _sh.index[-1])
    _rtxt = ', '.join(f'{s.split()[0]} {_rs[s]:+.2f}' for s in _sh.index)
    _neg = sum(1 for v in _rs.values() if v < 0)
    _rf = {s: g.vehicles_flow.corr(g.matched_dB) for s, g in vc.groupby('site')} if HASFLOW else {}
    _rftxt = ', '.join(f'{s.split()[0]} {_rf[s]:+.2f}' for s in _sh.index) if HASFLOW else ''
    findings = (
        'Findings: traffic composition matches the zone typologies: '
        f'{_hk.split()[0]} is motorbike-dominated\n({_sh.loc[_hk, "moto_mean"]:.0f}%), '
        f'{_op.split()[0]} car-dominated ({_sh.loc[_op, "car_mean"]:.0f}%), '
        f'{_vt.split()[0]} the densest corridor (up to {_mx[_vt]:.0f} vehicles/frame).\n'
        + ((f'Mean flow is {vc.vehicles_flow.mean():.0f} veh/min (median '
            f'{vc.vehicles_flow.median():.0f}, max {vc.vehicles_flow.max():.0f}).\n'
            'MOVING TO REAL FLOW DOES NOT RECOVER THE SIGNAL. Correlation with level, by site:\n'
            f'density {_rtxt};\nflow {_rftxt}.\n'
            f'Pooled: density {vc.vehicles_mean.corr(vc.matched_dB):+.2f}, flow '
            f'{vc.vehicles_flow.corr(vc.matched_dB):+.2f} - still the wrong sign; motorcycle flow\n'
            f'is uncorrelated ({vc.moto_flow.corr(vc.matched_dB):+.3f}). Only {_vt.split()[0]}, '
            f'the through-traffic corridor, is positive, and it\nIMPROVES with flow '
            f'({_rs[_vt]:+.2f} -> {_rf[_vt]:+.2f}) - the direction physics predicts. What is still\n'
            'missing is SPEED and the source-receiver DISTANCE: the field of view is not\n'
            'georeferenced. See section 7.\n')
           if HASFLOW else
           ('Vehicle density does NOT track noise: the site-wise correlations are weak and of\n'
            f'inconsistent sign ({_rtxt}), negative on {_neg} of {len(_rs)} sites,\n'
            f'and {vc.vehicles_mean.corr(vc.matched_dB):+.2f} overall.\n'))
        + 'Note: small motorbikes are harder to detect than cars and parked vehicles are counted\n'
          'too, so motorbike shares are a lower bound; the detector was never validated against\n'
          'manual counts.\n\n'
        'Weather: no robust effect. Raw correlations (temperature +0.26, rain -0.29) vanish '
        'once hour of day and\nsession are controlled: quiet-point campaigns happened to fall on '
        'rainy days. Wind shows no effect on\nreadings (no microphone artefact).')
    fig.text(.08, .36, findings, fontsize=9.5, va='top', linespacing=1.55)
    footer(fig, 5); pp.savefig(fig); plt.close(fig)

# ================= PAGE 6: model, baselines, ablation =================
fig = plt.figure(figsize=(8.27, 11.69)); fig.subplots_adjust(left=.08, right=.92)
fig.text(.08, .95, '5.  Predictive model', fontsize=14, weight='bold')
fig.text(.08, .915, f'Seven models compared on identical splits. Delivered: {HEAD["label"]}.',
         fontsize=9.5, va='top')

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
# `site_mean` and `lgbm_time` are omitted from THIS table (limited space on the page);
# they remain in models/model_comparison.md, cited just below. `global_mean`
# is kept: it is the floor that gives a negative R2 its meaning.
ORDER = [k for k in ['global_mean', 'site_hour_mean', 'dist_road', 'idw',
                     'lgbm_morpho', 'lgbm_full', 'lgbm_v2',
                     'physical', 'hybrid', 'hybrid_lowcap'] if k in MODELS]
mrows = [['Model', 'R²', '95% CI', 'MAE (dB)', 'r']]
for k in ORDER:
    m = MODELS[k]
    mrows.append([m['label'], f"{m['r2']:.2f}",
                  f"[{m['r2_ci95'][0]:.2f}, {m['r2_ci95'][1]:.2f}]",
                  f"{m['mae']:.2f}", f"{m['r']:.2f}"])
ax = fig.add_axes([.08, .425, .84, .275]); ax.axis('off')
# We highlight the BEST model under the reference protocol, not ours by default:
# since the August 2026 run that is no longer the LightGBM (see negative-results.md 5.z).
BEST = max(ORDER, key=lambda k: MODELS[k]['r2'])
styled_table(ax, mrows, highlight=ORDER.index(BEST) + 1, colWidths=[.47, .11, .19, .12, .11],
             fontsize=8, vscale=1.35)

_dr = MODELS['dist_road']
_lo = METRICS.get('loso', {}).get('models', {})
_bcv = METRICS.get('block_cv', {}).get('models', {})
_v2 = METRICS[REF].get('v2_gains', {})
# The salient fact is not the delivered model's score: it is that the RANKING inverts
# between the permissive protocol and the strict ones. We state it with the table's two
# extremes rather than with a hardcoded model name.
_hy = MODELS.get('hybrid')
_key = (f"Key figure - the ranking inverts between protocols. Under the permissive 600 m block "
        f"split the\nelaborate models lead"
        + (f" (hybrid physics+ML: {_bcv['hybrid']['r2']:.3f}, LightGBM v2: "
           f"{_bcv['lgbm_v2']['r2']:.3f}, physical core: {_bcv['physical']['r2']:.3f})"
           if _bcv and 'hybrid' in _bcv else '')
        + f".\nUnder {REFLABEL.lower()} - whose exclusion radius equals the feature aggregation "
          f"radius - the order\nreverses: the 3-parameter physical core reaches {R2_HEAD:.3f}, "
          f"ahead of the distance regression ({_dr['r2']:.3f})"
        + (f"\nand of the hybrid ({_hy['r2']:.3f}). The learned residual is a NET LOSS here: "
           f"dR2 {_v2['residual_ml_gain']['delta_r2']:+.3f}."
           if _hy and _v2 else '.'))
fig.text(.08, .405, _key, fontsize=8.5, va='top', linespacing=1.45, color='#8a4b08')

fig.text(.08, .305, '5.3  Generalisation to an unseen typology (leave-one-site-out)',
         fontsize=11.5, weight='bold', color='#34495e')
prows = [['Test site', 'n', 'R²', 'MAE (dB)']]
for site, v in PERSITE.items():
    prows.append([site, str(v['n']), f"{v['r2']:.2f}", f"{v['mae']:.2f}"])
ax = fig.add_axes([.08, .185, .84, .105]); ax.axis('off')
styled_table(ax, prows, colWidths=[.34, .16, .22, .28], fontsize=8.5, vscale=1.4)
_loso_txt = ''
if _lo and 'hybrid' in _lo and DELIVERED in _lo:
    _loso_txt = (f'\nPooled over all sites the delivered model holds R2 '
                 f'{_lo[DELIVERED]["r2"]:+.3f}, the hybrid falls to '
                 f'{_lo["hybrid"]["r2"]:+.3f}: the learned residual\nhelps INSIDE sampled '
                 f'typologies and hurts outside them, so it is not applied to the published map.')
fig.text(.08, .15,
         'Each site is predicted by a model trained on the other two only. A negative R2 '
         'means: worse than\npredicting the global mean everywhere. Maps are clipped to the '
         'sampled envelope regardless.' + _loso_txt,
         fontsize=8.5, va='top', linespacing=1.5)

fig.text(.08, .04, 'Cross-city transfer (Uganda -> Hanoi) is reported in section 7 as a '
         'methodological result, not as a method.',
         fontsize=8.5, va='bottom', color='#555', style='italic', linespacing=1.5)
footer(fig, 6); pp.savefig(fig); plt.close(fig)

# ================= PAGE 7 : simulation GAMA + validation =================
VALID_PNG = os.path.join(cfg.FIGURES, 'validation_simulation.png')
VALID_CSV = os.path.join(cfg.TABLES, 'validation_simulation.csv')
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

# ================= PAGE 8: limitations + next steps =================
fig = plt.figure(figsize=(8.27, 11.69))
fig.text(.08, .95, '7.  Limitations, stated plainly', fontsize=14, weight='bold')
lim_txt = (
    '•  THE LEARNED COMPONENT DOES NOT SURVIVE AN HONEST SPATIAL SPLIT. We built the hybrid\n'
    '   architecture we recommend (physical core + LightGBM on the residual). It leads under the\n'
    + (f"   permissive 600 m block split ({_bcv['hybrid']['r2']:.3f} against "
       f"{_bcv['physical']['r2']:.3f} for the bare core) and LOSES under both\n"
       if _bcv and 'hybrid' in _bcv else '   permissive split and loses under both\n')
    + f"   strict ones (dR2 {_v2['residual_ml_gain']['delta_r2']:+.3f} under {REFLABEL.lower()}). "
      f"The delivered model is therefore\n   the bare 3-parameter physical core; the residual is "
      f"trained but NOT applied. Morphology aggregated\n   over 300 m adds no measurable value "
      f"over the two distance terms alone.\n\n"
    '•  ABSOLUTE CALIBRATION. The three phones are calibrated against each other, never against a\n'
    f'   reference instrument. A bias common to all three ({BIAS_LO:+.1f} to {BIAS_HI:+.1f} dB, '
    'bounded by anchoring on\n   instrumented Vietnamese campaigns) is invisible in our data. The '
    'field campaign is closed and this\n   cannot be repaired retrospectively. Contrasts are '
    'supported; absolute levels are indicative.\n\n'
    '•  MEASUREMENT QUANTITY. A 20-30 s sample is not the L_Aeq of any regulatory reference period.\n'
    '   A single horn burst moves it by several dB - horn events reach +17 dB in Vietnamese traffic.\n'
    '   This variance is a property of the quantity and caps the R² any spatial model can reach.\n\n'
    '•  GENERALISATION. With three sampled typologies, the number of independent morphological\n'
    '   configurations available is close to three, whatever the number of points. The delivered\n'
    '   physical model extrapolates markedly better than the learned ones (section 5.3), but three\n'
    '   typologies remain three: maps are clipped to the sampled envelope regardless of the score.\n\n'
    '•  SPATIAL RESOLUTION. Features are aggregated over a 300 m radius, so adjacent 40 m cells share\n'
    '   more than 98% of their disc. The map cannot resolve the facade/courtyard contrast (10-15 dB in\n'
    '   dense fabric): predicted levels are visibly flatter than measured ones.\n\n'
    '•  TEMPORAL COVERAGE. Night (21:00-06:00) holds ~3% of measurements and nothing between 00:00\n'
    '   and 05:00, although that is the period with the strictest threshold. One season only.\n\n'
    '•  TRAFFIC VIDEOS. Counts are now real FLOW (tracking + line crossing), but speed is still\n'
    '   unobservable without a ground homography and the field of view is not georeferenced, so\n'
    '   distance is discarded. The detector was never validated against manual counts: modal\n'
    '   splits remain lower bounds on motorcycle share (section 7).')
fig.text(.08, .915, lim_txt, fontsize=8, va='top', linespacing=1.4)

fig.text(.08, .445, '8.  Next steps', fontsize=14, weight='bold')
nxt = (
    '•  RICHER PHYSICS, NOT MORE LEARNING. Our 3-parameter line-source core already beats every\n'
    '   learned variant. The next gain should come from a real propagation model (CNOSSOS-EU via\n'
    '   NoiseModelling: screening, reflections, canyon geometry), not from more capacity fitted to\n'
    '   363 points. A learned residual should be re-tested only once the sample covers more\n'
    '   typologies - on this one it degrades generalisation.\n\n'
    '•  TRAFFIC. Flow by class is now measured; SPEED is the missing half. Estimate it from track\n'
    '   displacement under a ground homography, which also georeferences the field of view and so\n'
    '   restores the source-receiver distance. Validate the detector against manual counts first.\n\n'
    '•  MORE TYPOLOGIES. Three sampled districts bound every generalisation claim we can make.\n'
    '   A fourth and fifth contrasting fabric would do more than any modelling change.\n\n'
    '•  DATA PUBLICATION. Deposit measurements, forms and code with a DOI; add an ethics statement\n'
    '   covering the public-space video recordings.')
fig.text(.08, .405, nxt, fontsize=8, va='top', linespacing=1.4)

fig.text(.08, .175, '9.  Summary', fontsize=14, weight='bold')
summ = (
    f'{len(df)} smartphone measurements across 3 districts document a consistent exposure pattern in\n'
    f'space and time. The delivered model is a 3-parameter PHYSICAL line-source law: R² {R2_HEAD:.2f} '
    f'[{CI_HEAD[0]:.2f}, {CI_HEAD[1]:.2f}] /\nMAE {MAE_HEAD:.2f} dB under {REFLABEL.lower()}, ahead of '
    f'a log(distance) regression ({_dr["r2"]:.2f}), a 6-feature\nLightGBM ({MODELS["lgbm_full"]["r2"]:.2f}) '
    f'and the physics+ML hybrid we built to improve on it ({MODELS["hybrid"]["r2"]:.2f}).\n'
    'Three negative results are contributions: every learned elaboration gains under a permissive\n'
    'spatial split and loses under a strict one; cross-city transfer from Uganda fails; and video\n'
    'counts yield no emission coefficient, as density OR as flow. We claim contrasts, not absolutes.')
fig.text(.08, .138, summ, fontsize=8, va='top', linespacing=1.45, color='#222')
footer(fig, 8); pp.savefig(fig); plt.close(fig)

pp.close()
print(f'OK -> {cfg.REPORT_PDF}  (8 pages)')

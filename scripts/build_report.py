"""Assemble le Data Collection Report du projet en un seul PDF : outputs/report.pdf.

Comprehensive (mais pas trop formel) : objectif, méthodologie (protocole de
collecte + reproduction Sunbird), analyse de données (patterns temporels,
sources, dépassements QCVN/OMS), modèle prédictif (transfert vs entraînement
direct), limitations & prochaines étapes.

Données descriptives recalculées depuis measurements.csv ; métriques modèle
recopiées du notebook 08 (dicts MODEL et PERSITE ci-dessous — à mettre à jour
si les scores du notebook changent).
Usage : python3 scripts/build_report.py
"""
import os
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

QCVN_D, QCVN_N, WHO_D, WHO_N = 70, 55, 53, 45
df = pd.read_csv('data/raw/hanoi/measurements.csv', parse_dates=['timestamp'])
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

# métriques modèle — recopiées de la sortie du notebook 08 (CV spatiale honnête)
MODEL = {
    'Direct training, spatial CV (honest)': ('0.68', '0.45', '4.4'),
    'Direct training, random split (optimistic)': ('0.71', '0.49', '4.1'),
    'Uganda to Hanoi transfer (comparison)': ('0.06', '−1.48', '8.4'),
}
PERSITE = {'Ocean Park': '0.28', 'Vinh Tuy area': '−0.71', 'Hoan Kiem lake': '−0.28'}

FOOT = 'Hanoi Urban Noise · Data Collection Report'
def footer(fig, n, total=7):
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
        ('dB range', f'{df.noise_dB.min():.0f}-{df.noise_dB.max():.0f}'),
        ('Model R²', '0.45'), ('Exceed QCVN', f'{exc_glob:.0f}%')]
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
fig.text(.08, .315, f'Headline findings: median {df.noise_dB.median():.0f} dB, {exc_glob:.0f}% of '
         f'measurements exceed the QCVN limit, noise peaks at {peak_h}:00.\nA model trained directly '
         'on our data reaches R² 0.45 (honest cross-validation, section 5).',
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

fig.text(.08, .50, '3.4  Standards used', fontsize=11.5, weight='bold', color='#34495e')
std = [['Standard', 'Day (6-21h)', 'Night (21-6h)'],
       ['QCVN 26:2010/BTNMT (Vietnam, ordinary area)', '70 dB', '55 dB'],
       ['WHO (road-traffic guideline)', '53 dB', '45 dB']]
ax = fig.add_axes([.08, .39, .84, .08]); ax.axis('off')
styled_table(ax, std, colWidths=[.5, .25, .25])
footer(fig, 2); pp.savefig(fig); plt.close(fig)

# ================= PAGE 3 : patterns temporels =================
fig = plt.figure(figsize=(8.27, 11.69)); fig.subplots_adjust(top=.92, bottom=.07, hspace=.32)
fig.text(.08, .955, '4.  Data analysis: temporal patterns', fontsize=14, weight='bold', transform=fig.transFigure)
ax1 = fig.add_subplot(2, 1, 1)
for s in SITES:
    g = df[df.site == s].groupby('hour').noise_dB.median()
    ax1.plot(g.index, g.values, marker='o', lw=2, color=COL[s], label=s)
ax1.axhline(QCVN_D, ls='--', c='red', alpha=.6, label='QCVN day 70'); ax1.axhline(QCVN_N, ls='--', c='darkred', alpha=.6, label='QCVN night 55')
ax1.axhline(WHO_D, ls=':', c='gray', alpha=.6, label='WHO day 53')
ax1.set_title('Hourly pattern within a day (capture window 05:00-23:00)', fontsize=11)
ax1.set_xlabel('Hour'); ax1.set_ylabel('Median dB')
ax1.set_xlim(4.5, 23.5); ax1.set_xticks(range(5, 24, 2))
ax1.legend(fontsize=7.5, ncol=2); ax1.grid(alpha=.3)
ax2 = fig.add_subplot(2, 1, 2)
order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
for s in SITES:
    g = df[df.site == s].groupby('dow').noise_dB.median().reindex(order)
    ax2.plot(range(7), g.values, marker='s', lw=2, color=COL[s], label=s)
ax2.axhline(QCVN_D, ls='--', c='red', alpha=.6)
ax2.set_title('Day-of-week pattern', fontsize=11); ax2.set_xticks(range(7))
ax2.set_xticklabels(['Mon','Tue','Wed','Thu','Fri','Sat','Sun']); ax2.set_ylabel('Median dB'); ax2.legend(fontsize=7.5); ax2.grid(alpha=.3)
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
pe = df.groupby('hour').apply(lambda g: (g.noise_dB > np.where((g.hour>=21)|(g.hour<6), QCVN_N, QCVN_D)).mean()*100)
ax3.bar(pe.index, pe.values, color=['#c0392b' if v>50 else '#e67e22' if v>0 else '#27ae60' for v in pe.values])
ax3.set_xlabel('Hour'); ax3.set_ylabel('% measurements > QCVN')
ax3.set_xlim(4.5, 23.5); ax3.set_xticks(range(5, 24, 2))
ax3.set_title('Frequency of QCVN exceedance by hour (peak periods)', fontsize=11); ax3.grid(alpha=.3)
footer(fig, 4); pp.savefig(fig); plt.close(fig)

# ================= PAGE 5 : vidéos trafic (CV) + météo =================
VC = 'data/processed/hanoi/vehicle_counts.csv'
if os.path.exists(VC):
    vc = pd.read_csv(VC, parse_dates=['video_start', 'matched_timestamp'])
    vc = vc.merge(df[['timestamp', 'site']], left_on='matched_timestamp',
                  right_on='timestamp', how='left')
    vc['rush'] = vc.video_start.dt.strftime('%m%d').isin(['0708', '0713', '0714'])

    fig = plt.figure(figsize=(8.27, 11.69)); fig.subplots_adjust(top=.86, bottom=.42, wspace=.30)
    fig.text(.08, .955, '4.  Data analysis: traffic videos & weather', fontsize=14, weight='bold')
    fig.text(.08, .925, f'{len(vc)} traffic videos (~25 s each) matched to their measurement by '
             'timestamp (median gap 15 s).\nVehicles counted with YOLOv8 at ~1 frame/s '
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
    for rush, colr, lab in [(False, '#2471a3', 'moderate traffic (June)'), (True, '#c0392b', 'rush hours (July)')]:
        g = vc[vc.rush == rush]
        ax2.scatter(g.vehicles_mean, g.matched_dB, s=22, alpha=.6, color=colr,
                    label=f'{lab}  r={g.vehicles_mean.corr(g.matched_dB):+.2f}')
    ax2.set_xlabel('Vehicles per frame'); ax2.set_ylabel('Measured dB')
    ax2.set_title('Traffic density vs noise', fontsize=10); ax2.legend(fontsize=8); ax2.grid(alpha=.3)

    findings = (
        'Findings: traffic composition matches the zone typologies: Hoan Kiem is motorbike-'
        'dominated, Ocean Park\ncar-dominated, Vinh Tuy densest (up to 14 vehicles/frame). In '
        'moderate traffic, more vehicles = more noise\n(r +0.37); at rush hours the correlation '
        'reverses (r −0.32): congestion slows traffic down, and slow dense\ntraffic is quieter '
        'than free-flowing traffic. Note: small motorbikes are harder to detect than cars, so\n'
        'motorbike shares are likely underestimated.\n\n'
        'Weather: no robust effect. Raw correlations (temperature +0.26, rain −0.29) vanish '
        'once hour of day and\nsession are controlled: quiet-point campaigns happened to fall on '
        'rainy days. Wind shows no effect on\nreadings (no microphone artefact).')
    fig.text(.08, .36, findings, fontsize=9.5, va='top', linespacing=1.55)
    footer(fig, 5); pp.savefig(fig); plt.close(fig)

# ================= PAGE 6 : modèle (transfert vs direct) =================
fig = plt.figure(figsize=(8.27, 11.69)); fig.subplots_adjust(left=.08, right=.92)
fig.text(.08, .95, '5.  Predictive model', fontsize=14, weight='bold')
fig.text(.08, .915, 'LightGBM mapping urban morphology + time of day to noise level (dB).',
         fontsize=9.5, va='top')

fig.text(.08, .87, '5.1  Key finding: transfer fails, direct training works', fontsize=11.5, weight='bold', color='#34495e')
finding = (
    'The Uganda-pretrained model transfers poorly to Hanoi even after offset calibration (R² < 0):\n'
    'the noise-morphology relationship learned in Kampala does not hold here, as in the Barcelona\n'
    'cross-city experiment. Training directly on our own measurements works, and is our method.')
fig.text(.08, .835, finding, fontsize=9.5, va='top', linespacing=1.55)

mrows = [['Method', 'r', 'R²', 'MAE (dB)']] + [[k, v[0], v[1], v[2]] for k, v in MODEL.items()]
mrows.append(['Barcelona reference (for context)', '0.66', '0.61', 'n/a'])
ax = fig.add_axes([.08, .59, .84, .14]); ax.axis('off')
styled_table(ax, mrows, highlight=1, colWidths=[.48, .14, .14, .18])
fig.text(.08, .565, 'Spatial CV: tested on locations the model never saw in training (the honest number). '
         'Random split: test points can\nsit metres from training points, which inflates scores; kept '
         'as an optimistic upper bound.', fontsize=8.5, color='#555', style='italic', va='top', linespacing=1.5)

fig.text(.08, .51, '5.2  Per-site generalization (leave-one-site-out)', fontsize=11.5, weight='bold', color='#34495e')
prows = [['Test site', 'R²', 'Comment'],
         ['Ocean Park', PERSITE['Ocean Park'], 'best case (largest, most varied sample)'],
         ['Vinh Tuy', PERSITE['Vinh Tuy area'], 'distinct transport-corridor typology'],
         ['Hoan Kiem', PERSITE['Hoan Kiem lake'], 'distinct old-quarter morphology']]
ax = fig.add_axes([.08, .39, .84, .11]); ax.axis('off')
styled_table(ax, prows, colWidths=[.24, .14, .52])
fig.text(.08, .35, 'A stress test: each site is predicted by a model trained on the other two only. '
         'Per-site R² on such\nsmall samples is noisy; the spatial CV above is the reliable number.',
         fontsize=9.5, va='top', linespacing=1.55)
fig.text(.08, .285, 'Reading the metrics: r = does the model rank places correctly; R² = are predicted '
         'dB values accurate.\nDirect training delivers both: r 0.68, R² 0.45.',
         fontsize=9.5, va='top', linespacing=1.55)
footer(fig, 6); pp.savefig(fig); plt.close(fig)

# ================= PAGE 7 : limitations + prochaines étapes =================
fig = plt.figure(figsize=(8.27, 11.69))
fig.text(.08, .95, '6.  Limitations', fontsize=14, weight='bold')
lim_txt = (
    '•  The model interpolates well within the sampled areas but extrapolates poorly to a district\n'
    '   it has never seen: city-wide prediction would need more urban typologies covered.\n\n'
    '•  Instantaneous readings carry ±5 dB of irreducible noise (a passing bus), capping the\n'
    '   achievable R² near 0.6; repeated measurements at fixed points would raise it.\n\n'
    '•  Consumer sound meters: a constant calibration bias is correctable, clipping above 90 dB and\n'
    '   wind noise are not. Weekend coverage is still light compared to weekdays.')
fig.text(.08, .905, lim_txt, fontsize=9.5, va='top', linespacing=1.55)

fig.text(.08, .71, '7.  Next steps', fontsize=14, weight='bold')
nxt = (
    '•  Add weekend sessions and repeated measurements at fixed locations to average out\n'
    '   instantaneous variation.\n\n'
    '•  Vehicle counting from the 83 traffic videos via computer vision, each matched to its\n'
    '   measurement point (transport composition as a model feature).\n\n'
    '•  GAMA simulation: import the noise map, add a traffic-volume slider and what-if scenarios\n'
    '   (pedestrianisation, peak-hour traffic).\n\n'
    '•  Manuscript: methods (Sunbird reproduction + transferability study), results, discussion.')
fig.text(.08, .665, nxt, fontsize=9.5, va='top', linespacing=1.55)

fig.text(.08, .45, '8.  Summary', fontsize=14, weight='bold')
summ = (
    f'{len(df)} calibrated measurements across 3 districts confirm high exposure ({exc_glob:.0f}% exceed\n'
    'QCVN). A model trained on our data reaches R² 0.45 / r 0.68 / MAE 4.4 dB (spatial CV), solid\n'
    'for instantaneous smartphone data. Cross-city transfer from Uganda fails: a documented,\n'
    'useful methodological result.')
fig.text(.08, .405, summ, fontsize=9.5, va='top', linespacing=1.6, color='#222')
footer(fig, 7); pp.savefig(fig); plt.close(fig)

pp.close()
print('OK -> outputs/report.pdf  (7 pages)')

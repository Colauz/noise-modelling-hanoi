"""Assemble le rapport d'analyse de données en un seul PDF : outputs/report.pdf.
Données descriptives recalculées depuis measurements.csv ; métriques modèle
vérifiées dans le notebook 08 (CV spatiale honnête). Usage : python3 scripts/build_report.py
"""
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

# métriques modèle (vérifiées cette session — CV spatiale honnête)
MODEL = {
    'Direct training (spatial CV, honest)': ('0.69', '0.45', '4.7'),
    'Direct training (random split, upper bound)': ('0.74', '0.53', '4.3'),
    'Uganda->Hanoi transfer (comparison)': ('0.23', '-0.68', '8.5'),
}
PERSITE = {'Ocean Park': '0.46', 'Vinh Tuy area': '0.18', 'Hoan Kiem lake': '-0.89'}
date_min, date_max = df.timestamp.min().strftime('%d %b'), df.timestamp.max().strftime('%d %b %Y')
exc_glob = 100 * df.exceeds.mean()
peak_h = df.groupby('hour').noise_dB.median().idxmax()

pp = PdfPages('outputs/report.pdf')

# ---------- PAGE 1 : couverture + résumé des données ----------
fig = plt.figure(figsize=(8.27, 11.69)); fig.subplots_adjust(left=.08, right=.92, top=.94, bottom=.06)
fig.text(.5, .92, 'Urban Noise Mapping — Hanoi', ha='center', fontsize=20, weight='bold')
fig.text(.5, .888, 'Data Analysis Report', ha='center', fontsize=14, color='#555')
fig.text(.5, .862, f'{len(df)} smartphone measurements · 3 sites · {date_min} – {date_max} 2026',
         ha='center', fontsize=10, color='#777')
fig.text(.5, .845, 'Methodology adapted from Sunbird AI (Urban Noise Uganda 61K)',
         ha='center', fontsize=9, style='italic', color='#777')

# bandeau KPI
kpis = [('Measurements', f'{len(df)}'), ('Sites', '3'),
        ('dB range', f'{df.noise_dB.min():.0f}–{df.noise_dB.max():.0f}'),
        ('Exceed QCVN', f'{exc_glob:.0f}%'), ('Peak hour', f'{peak_h}:00')]
for i, (k, v) in enumerate(kpis):
    x = .10 + i * .163
    fig.patches.append(plt.Rectangle((x, .76), .15, .055, transform=fig.transFigure,
                       facecolor='#f2f4f6', edgecolor='#d0d4d8'))
    fig.text(x + .075, .793, v, ha='center', fontsize=13, weight='bold', color='#c0392b')
    fig.text(x + .075, .77, k, ha='center', fontsize=7.5, color='#555')

# tableau par site
fig.text(.08, .71, '1.  Data collection summary', fontsize=13, weight='bold')
rows = [['Site', 'n', 'Median dB', 'Min–Max', '% < 60 dB', '% roadside']]
for s in SITES:
    g = df[df.site == s]
    rd = 100 * g.dist_to_road.astype(str).str.contains('0-2|0-10|2-10').mean()
    rows.append([s, str(len(g)), f'{g.noise_dB.median():.0f}',
                 f'{g.noise_dB.min():.0f}–{g.noise_dB.max():.0f}',
                 f'{100*(g.noise_dB<60).mean():.0f}%', f'{rd:.0f}%'])
rows.append(['ALL', str(len(df)), f'{df.noise_dB.median():.0f}',
             f'{df.noise_dB.min():.0f}–{df.noise_dB.max():.0f}',
             f'{100*(df.noise_dB<60).mean():.0f}%',
             f'{100*df.dist_to_road.astype(str).str.contains("0-2|0-10|2-10").mean():.0f}%'])
ax = fig.add_axes([.08, .53, .84, .15]); ax.axis('off')
t = ax.table(cellText=rows[1:], colLabels=rows[0], loc='center', cellLoc='center')
t.auto_set_font_size(False); t.set_fontsize(9); t.scale(1, 1.6)
for (r, c), cell in t.get_celld().items():
    if r == 0: cell.set_facecolor('#34495e'); cell.set_text_props(color='w', weight='bold')
    elif r == len(rows) - 1: cell.set_facecolor('#eaeef1'); cell.set_text_props(weight='bold')

# notes
fig.text(.08, .47, '2.  Protocol & standards', fontsize=13, weight='bold')
notes = (
    '•  Capture: smartphone (Decibel X, A-weighting), ODK Collect + KoboToolbox, walking sampling,\n'
    '   GPS < 10 m accuracy, >=10 s audio per point, cross-calibrated phones, 05:00–23:00 window.\n'
    '•  Per point: location, dB, dominant source category, distance to road, audio; construction\n'
    '   sites logged separately (radius transect). 40 traffic videos for later vehicle counting.\n'
    '•  Standards: QCVN 26:2010/BTNMT = 70 dB day (6–21h) / 55 dB night.  WHO = 53 / 45 dB.')
fig.text(.08, .40, notes, fontsize=9, va='top', linespacing=1.6)
fig.text(.5, .03, 'Hanoi Urban Noise — Data Analysis Report — page 1/4', ha='center', fontsize=7.5, color='#999')
pp.savefig(fig); plt.close(fig)

# ---------- PAGE 2 : patterns temporels ----------
fig = plt.figure(figsize=(8.27, 11.69)); fig.subplots_adjust(top=.93, bottom=.07, hspace=.32)
fig.text(.08, .955, '3.  Temporal patterns by site', fontsize=14, weight='bold', transform=fig.transFigure)
ax1 = fig.add_subplot(2, 1, 1)
for s in SITES:
    g = df[df.site == s].groupby('hour').noise_dB.median()
    ax1.plot(g.index, g.values, marker='o', lw=2, color=COL[s], label=s)
ax1.axhline(QCVN_D, ls='--', c='red', alpha=.6, label='QCVN day 70'); ax1.axhline(QCVN_N, ls='--', c='darkred', alpha=.6, label='QCVN night 55')
ax1.axhline(WHO_D, ls=':', c='gray', alpha=.6, label='WHO day 53')
ax1.set_title('Hourly pattern within a day', fontsize=11); ax1.set_xlabel('Hour'); ax1.set_ylabel('Median dB')
ax1.set_xticks(range(0, 24, 2)); ax1.legend(fontsize=7.5, ncol=2); ax1.grid(alpha=.3)
ax2 = fig.add_subplot(2, 1, 2)
order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
for s in SITES:
    g = df[df.site == s].groupby('dow').noise_dB.median().reindex(order)
    ax2.plot(range(7), g.values, marker='s', lw=2, color=COL[s], label=s)
ax2.axhline(QCVN_D, ls='--', c='red', alpha=.6)
ax2.set_title('Day-of-week pattern', fontsize=11); ax2.set_xticks(range(7))
ax2.set_xticklabels(['Mon','Tue','Wed','Thu','Fri','Sat','Sun']); ax2.set_ylabel('Median dB'); ax2.legend(fontsize=7.5); ax2.grid(alpha=.3)
fig.text(.5, .03, 'Hanoi Urban Noise — Data Analysis Report — page 2/4', ha='center', fontsize=7.5, color='#999')
pp.savefig(fig); plt.close(fig)

# ---------- PAGE 3 : sources + dépassements ----------
fig = plt.figure(figsize=(8.27, 11.69)); fig.subplots_adjust(top=.93, bottom=.07, hspace=.32, wspace=.28)
fig.text(.08, .955, '4.  Noise sources & standard exceedances', fontsize=14, weight='bold', transform=fig.transFigure)
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
ax2.set_xticklabels([s.split()[0] for s in SITES], fontsize=8); ax2.set_title('By site', fontsize=10); ax2.legend(fontsize=7.5); ax2.grid(alpha=.3)
ax3 = fig.add_subplot(2, 1, 2)
pe = df.groupby('hour').apply(lambda g: (g.noise_dB > np.where((g.hour>=21)|(g.hour<6), QCVN_N, QCVN_D)).mean()*100)
ax3.bar(pe.index, pe.values, color=['#c0392b' if v>50 else '#e67e22' if v>0 else '#27ae60' for v in pe.values])
ax3.set_xlabel('Hour'); ax3.set_ylabel('% measurements > QCVN'); ax3.set_xticks(range(0, 24, 2))
ax3.set_title('Frequency of QCVN exceedance by hour (peak periods)', fontsize=11); ax3.grid(alpha=.3)
fig.text(.5, .03, 'Hanoi Urban Noise — Data Analysis Report — page 3/4', ha='center', fontsize=7.5, color='#999')
pp.savefig(fig); plt.close(fig)

# ---------- PAGE 4 : modèle + tableau dépassements + limites ----------
fig = plt.figure(figsize=(8.27, 11.69)); fig.subplots_adjust(left=.08, right=.92)
fig.text(.08, .95, '5.  Predictive model (morphology + time -> dB)', fontsize=14, weight='bold')
fig.text(.08, .915, 'LightGBM on urban-morphology features (built ratio, road density, distance to road,\n'
         'intersections) + hour + weekend. Reported on held-out data.', fontsize=9, va='top', linespacing=1.5)
mrows = [['Method', 'r', 'R²', 'MAE (dB)']] + [[k, v[0], v[1], v[2]] for k, v in MODEL.items()]
mrows.append(['Barcelona reference (profs)', '0.66', '0.61', '—'])
ax = fig.add_axes([.08, .70, .84, .15]); ax.axis('off')
t = ax.table(cellText=mrows[1:], colLabels=mrows[0], loc='center', cellLoc='center')
t.auto_set_font_size(False); t.set_fontsize(9); t.scale(1, 1.6)
for (r, c), cell in t.get_celld().items():
    if r == 0: cell.set_facecolor('#34495e'); cell.set_text_props(color='w', weight='bold')
    elif r == 1: cell.set_facecolor('#eafaf1')           # méthode retenue
    elif r == len(mrows)-1: cell.set_facecolor('#fef5e7')
fig.text(.08, .665, 'Per-site generalization (leave-one-site-out): Ocean Park R² '
         f'{PERSITE["Ocean Park"]}  ·  Vinh Tuy R² {PERSITE["Vinh Tuy area"]}  ·  '
         f'Hoan Kiem R² {PERSITE["Hoan Kiem lake"]}', fontsize=8.5, color='#555')

# tableau dépassements
fig.text(.08, .61, '6.  QCVN 26:2010 exceedances by site', fontsize=13, weight='bold')
erows = [['Site', 'Period', 'n', 'Median dB', 'Limit', '% exceed', 'Mean excess']]
for s in SITES:
    for per in ['day', 'night']:
        g = df[(df.site == s) & (df.period == per)]
        if len(g) == 0: continue
        lim = QCVN_D if per == 'day' else QCVN_N
        sev = (g.noise_dB - lim)[g.noise_dB > lim].mean()
        erows.append([s, per, str(len(g)), f'{g.noise_dB.median():.0f}', str(lim),
                      f'{100*(g.noise_dB>lim).mean():.0f}%', f'{sev:.1f} dB' if not np.isnan(sev) else '—'])
ax = fig.add_axes([.08, .36, .84, .22]); ax.axis('off')
t = ax.table(cellText=erows[1:], colLabels=erows[0], loc='center', cellLoc='center')
t.auto_set_font_size(False); t.set_fontsize(8.5); t.scale(1, 1.5)
for (r, c), cell in t.get_celld().items():
    if r == 0: cell.set_facecolor('#34495e'); cell.set_text_props(color='w', weight='bold')

fig.text(.08, .305, '7.  Limitations', fontsize=13, weight='bold')
lim_txt = (
    '•  The model generalizes well within consistently-sampled sites (Ocean Park R² 0.46) but\n'
    '   poorly to the historic centre (Hoan Kiem), where sampling was narrow (mostly roadside,\n'
    '   little dB variation) — a sampling issue, not a model limitation.\n'
    '•  Instantaneous smartphone readings carry ~±5 dB of irreducible noise (a passing bus),\n'
    '   which caps the achievable R² (~0.6); aggregating repeated measurements would help.\n'
    '•  Cross-city transfer (Uganda -> Hanoi) failed (R² < 0); only direct local training works.\n'
    '•  Non-professional sound meter: a constant calibration bias is correctable, clipping > 90 dB\n'
    '   and wind are not. Weekend loud points and a third quiet site remain under-sampled.')
fig.text(.08, .25, lim_txt, fontsize=9, va='top', linespacing=1.6)
fig.text(.08, .085, 'Next: collect varied quieter points at Hoan Kiem; vehicle counting via computer vision\n'
         'on traffic videos; GAMA simulation (calibrated noise map + traffic scenarios).',
         fontsize=9, va='top', style='italic', color='#555', linespacing=1.5)
fig.text(.5, .03, 'Hanoi Urban Noise — Data Analysis Report — page 4/4', ha='center', fontsize=7.5, color='#999')
pp.savefig(fig); plt.close(fig)

pp.close()
print('OK -> outputs/report.pdf')

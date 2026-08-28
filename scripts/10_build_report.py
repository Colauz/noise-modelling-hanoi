"""Assemble the project Data Collection Report as a typeset LaTeX document.

WHY THIS SCRIPT CHANGED (August 2026)
-------------------------------------
The report used to be drawn with matplotlib: every heading, paragraph and table
was a `fig.text()` call positioned by hand in figure coordinates, saved through
`PdfPages`. That produced a PDF, but not a document -- no reflow, no hyphenation,
no real tables, no cross-references, and a layout that broke whenever a number
grew a digit.

The prose now lives in `results/report/report.tex`. This script does the part a
document cannot do for itself: it computes every figure the report quotes and
writes them out as LaTeX macros and table bodies, then calls latexmk.

THE RULE THIS PRESERVES
-----------------------
No metric is typed by hand, in the report or anywhere else. Descriptive figures
are recomputed from measurements.csv; model metrics are READ from
models/metrics.json (produced by scripts/04_evaluate_models.py). The report
cannot drift from the model actually delivered, and it refuses to run without
that file.

TWO SUBSTANTIVE POSITIONS, CARRIED OVER UNCHANGED
-------------------------------------------------
  - the WHO guideline values (L_den 53 / L_night 45) are NOT in this report.
    They are ANNUAL averages with evening/night penalties, not comparable to our
    25 s samples (docs/metrology.md);
  - QCVN exceedances are presented as a DESCRIPTIVE STATISTIC of our sample,
    with a sensitivity analysis on the calibration bias, and never as a finding
    of regulatory non-compliance.

OUTPUTS
-------
  results/report/numbers.tex    scalar macros  (\\nMeas, \\Rtwohead, ...)
  results/report/tab_*.tex      table bodies   (sites, models, exceedances, anchors)
  results/report/report.pdf     the typeset report

USAGE
-----
  python3 scripts/10_build_report.py [--no-compile]

  --no-compile   write the .tex inputs and stop (useful when latexmk is absent)

PREREQUISITES: scripts/01_prepare_field_data.py, scripts/04_evaluate_models.py,
scripts/09b_build_analyses.py (for the figures the report includes).
Requires latexmk and a TeX Live with booktabs, geometry and hyperref.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import warnings

warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd

from noise_hanoi import config as cfg

# QCVN 26:2010/BTNMT thresholds, ordinary zone. No WHO value: see the docstring.
QCVN_D, QCVN_N = 70, 55

# Plausible absolute bias range of our smartphones, estimated by anchoring on the
# instrumented literature (scripts/06_anchor_literature.py). Used to bound the
# sensitivity of the exceedance rates, never to correct a level.
BIAS_LO, BIAS_HI = -3.0, 3.0


def tex_escape(s):
    """Escape the five characters that would otherwise be LaTeX syntax."""
    for a, b in (('\\', r'\textbackslash{}'), ('&', r'\&'), ('%', r'\%'),
                 ('_', r'\_'), ('#', r'\#')):
        s = s.replace(a, b)
    return s


def read_bias_interval():
    """Widen the default bias interval to whatever the anchoring actually found.

    Night is excluded: n is about 10, which is too thin for the anchor to be
    informative, and it is carried in the CSV for the record only.
    """
    path = os.path.join(cfg.TABLES, 'literature_anchoring.csv')
    if not os.path.exists(path):
        return BIAS_LO, BIAS_HI
    a = pd.read_csv(path)
    u = a[(a.status != 'grey') & a.gap_after_metric_correction_dB.notna()
          & (a.comparable != 'night_all')]
    if not len(u):
        return BIAS_LO, BIAS_HI
    return (float(u.gap_after_metric_correction_dB.min()),
            float(u.gap_after_metric_correction_dB.max()))


def mobile_facts():
    r"""Read the field application's own constants out of its source.

    The report describes the Android app, so it quotes figures about it: the
    integration window, the traffic-multiplier range, the question counts, the
    accuracy gate, how many unit tests there are. None of those live in
    metrics.json, and typing them here would give each one a second home --
    which is the failure the first audit found and the reason this script exists.

    So they are read from the files that define them. If someone changes
    WINDOW_SECONDS in SplMeter.kt, the report changes with it; if someone deletes
    the constant, this raises rather than quietly reporting yesterday's value.

    Anything the app reports that is a MEASURED result rather than a constant --
    the GAMA agreement figures, for instance -- is not extracted here. Those
    belong to mobile/README.md and the report points at it instead of restating
    a number it cannot check.
    """
    root = os.path.join(cfg.ROOT, 'mobile')
    src = os.path.join(root, 'app', 'src')
    if not os.path.isdir(src):
        return None

    def read(*parts):
        with open(os.path.join(src, *parts)) as f:
            return f.read()

    def grab(text, pattern, what):
        m = re.search(pattern, text)
        if not m:
            sys.exit(f'10_build_report.py: could not read {what} from the mobile '
                     f'source. The constant moved or was renamed; fix the pattern '
                     f'rather than typing the number into the report.')
        return m

    kt = [os.path.join(d, f)
          for d, _, fs in os.walk(src) for f in fs if f.endswith('.kt')]
    main_kt = [f for f in kt if os.sep + 'main' + os.sep in f]
    tests = sum(open(f).read().count('@Test') for f in kt if os.sep + 'test' + os.sep in f)
    lines = sum(sum(1 for _ in open(f)) for f in kt)

    meter = read('main', 'java', 'org', 'noisehanoi', 'mobile', 'measure', 'SplMeter.kt')
    scen = read('main', 'java', 'org', 'noisehanoi', 'mobile', 'study', 'Scenario.kt')
    gps = read('main', 'java', 'org', 'noisehanoi', 'mobile', 'location', 'GpsFixes.kt')
    spec = read('main', 'java', 'org', 'noisehanoi', 'mobile', 'form', 'FormSpec.kt')
    with open(os.path.join(root, 'app', 'build.gradle.kts')) as f:
        gradle = f.read()

    window = float(grab(meter, r'WINDOW_SECONDS\s*=\s*([\d.]+)', 'WINDOW_SECONDS').group(1))
    mult = grab(scen, r'MULTIPLIER_RANGE\s*=\s*([\d.]+)f\.\.([\d.]+)f', 'MULTIPLIER_RANGE')
    gate = float(grab(gps, r'REQUIRED_ACCURACY_M\s*=\s*([\d.]+)', 'REQUIRED_ACCURACY_M').group(1))
    minsdk = grab(gradle, r'minSdk\s*=\s*(\d+)', 'minSdk').group(1)

    # Each FormSpec's questions run from `questions = listOf(` to the closing
    # `),` at the same indentation. Counting the constructor calls one level in
    # is what the file's own shape gives us without parsing Kotlin.
    def questions(name):
        block = spec.split(f'val {name} = FormSpec(', 1)[1].split('questions = listOf(', 1)[1]
        depth, out, count = 1, [], 0
        for ch in block:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    break
            out.append(ch)
        return len(re.findall(r'^\s{8}[A-Z]\w*Q\(', ''.join(out), re.M))

    return {
        'appKtFiles':   f'{len(main_kt)}',
        'appKtLines':   f'{lines:,}'.replace(',', r'\,'),
        'appTests':     f'{tests}',
        'appWindowS':   f'{window:g}',
        'appMultLo':    f'{float(mult.group(1)):g}',
        'appMultHi':    f'{float(mult.group(2)):g}',
        'appGateM':     f'{gate:g}',
        'appMinSdk':    minsdk,
        'appQnoise':    f'{questions("NOISE_FORM_V2")}',
        'appQconstr':   f'{questions("CONSTRUCTION_FORM_V1")}',
    }


def load():
    if not os.path.exists(cfg.METRICS_JSON):
        sys.exit('models/metrics.json is missing. Run scripts/04_evaluate_models.py first.\n'
                 'This report reads every model metric from that file and will not '
                 'invent one.')
    df = pd.read_csv(cfg.MEASUREMENTS, parse_dates=['timestamp'])
    metrics = json.load(open(cfg.METRICS_JSON))
    return df, metrics


def roadside_share(g):
    """Share of points the collector placed within 10 m of a road.

    Three bin labels mean 'within 10 m' because the survey form changed mid
    campaign: v1 offered a single 0-10 m bin, v2 split it into 0-2 m and 2-10 m.
    They are pooled here rather than silently treated as different strata.
    """
    return 100 * g.dist_to_road.astype(str).str.contains('0-2|0-10|2-10').mean()


def write_numbers(df, metrics, bias_lo, bias_hi, out, app=None):
    ref = metrics['meta']['headline_protocol']          # 'bloo'
    models = metrics[ref]['models']
    delivered = metrics['meta']['delivered_model']      # 'physical'
    d = models[delivered]
    ci = d.get('r2_ci95', [float('nan')] * 2)
    phys = metrics['physical_params']

    exc_day = 100 * (df[df.hour.between(6, 20)].noise_dB > QCVN_D).mean()
    hourly = df.groupby('hour').noise_dB.median()

    m = {
        # --- campaign ---
        'nMeas':       f'{len(df)}',
        'nSites':      f'{df.site.nunique()}',
        'dateMin':     str(df.timestamp.min().date()),
        'dateMax':     str(df.timestamp.max().date()),
        'dbMin':       f'{df.noise_dB.min():.0f}',
        'dbMax':       f'{df.noise_dB.max():.0f}',
        'dbMedian':    f'{df.noise_dB.median():.0f}',
        'dbMean':      f'{df.noise_dB.mean():.1f}',
        'dbSd':        f'{df.noise_dB.std():.2f}',
        'peakHour':    f'{int(hourly.idxmax())}',
        'excDay':      f'{exc_day:.1f}',
        'roadsideAll': f'{roadside_share(df):.0f}',
        'nNight':      f'{int(((df.hour >= 21) | (df.hour < 6)).sum())}',
        # --- reference protocol ---
        'refLabel':    tex_escape(metrics[ref].get('label', 'buffered leave-one-out')),
        'bufferM':     f"{metrics['meta']['buffer_m']}",
        'blockM':      f"{metrics['meta']['block_m']}",
        'nBlocks':     f"{metrics['meta']['n_blocks']}",
        'nBootstrap':  f"{metrics['meta']['n_bootstrap']}",
        # --- delivered model ---
        'deliveredKey':  tex_escape(delivered),
        'deliveredName': tex_escape(d.get('label', delivered)),
        'Rtwohead':    f"{d['r2']:.3f}",
        'CIheadLo':    f'{ci[0]:.3f}',
        'CIheadHi':    f'{ci[1]:.3f}',
        'MAEhead':     f"{d['mae']:.2f}",
        'RMSEhead':    f"{d['rmse']:.2f}",
        'residSd':     f"{metrics['physical_residual_sd_dB']:.2f}",
        'Ahw':         f"{phys['A_highway']:.3e}".replace('e+0', r'\times 10^{') + '}',
        'Ares':        f"{phys['A_residential']:.3e}".replace('e+0', r'\times 10^{') + '}',
        'Bbg':         f"{10 * np.log10(phys['B_background']):.1f}",
        'Dzero':       f"{phys['D0_m']:.0f}",
        'applyResid':  'true' if phys['apply_residual'] else 'false',
        # --- comparators, under the reference protocol ---
        'RtwoDistRoad': f"{models['dist_road']['r2']:.3f}",
        'RtwoLgbmFull': f"{models['lgbm_full']['r2']:.3f}",
        'RtwoHybrid':   f"{models['hybrid']['r2']:.3f}",
        'RtwoSiteHour': f"{models['site_hour_mean']['r2']:.3f}",
        # --- block-CV, for the inversion argument ---
        'BcvPhysical':  f"{metrics['block_cv']['models']['physical']['r2']:.3f}",
        'BcvHybrid':    f"{metrics['block_cv']['models']['hybrid']['r2']:.3f}",
        # --- thresholds and bias ---
        'qcvnDay':     f'{QCVN_D}',
        'qcvnNight':   f'{QCVN_N}',
        'biasLo':      f'{bias_lo:+.1f}',
        'biasHi':      f'{bias_hi:+.1f}',
    }
    # --- the field application, read from mobile/ (see mobile_facts) ---
    if app:
        m.update(app)
    with open(out, 'w') as f:
        f.write('% Generated by scripts/10_build_report.py -- do not edit.\n'
                '% Every number the report quotes is defined here, and nowhere else.\n')
        for k, v in m.items():
            f.write(f'\\newcommand{{\\{k}}}{{{v}}}\n')
    return m


def write_site_table(df, out):
    r"""Emit the complete tabular.

    The whole environment is generated, not just the rows: LaTeX's \input is not
    expandable, and reading a file from inside an alignment makes TeX misread the
    \noalign that \midrule and \bottomrule expand to.
    """
    rows = [r'\begin{tabular}{@{}lrrrrr@{}}', r'\toprule',
            r'\textbf{Site} & \textbf{n} & \textbf{Median dB} & \textbf{Min--Max} & '
            r'\textbf{\% $<$ 60 dB} & \textbf{\% roadside} \\', r'\midrule']
    for s in sorted(df.site.unique()):
        g = df[df.site == s]
        rows.append(f'{tex_escape(s)} & {len(g)} & {g.noise_dB.median():.0f} & '
                    f'{g.noise_dB.min():.0f}--{g.noise_dB.max():.0f} & '
                    f'{100 * (g.noise_dB < 60).mean():.0f}\\% & '
                    f'{roadside_share(g):.0f}\\% \\\\')
    rows.append(r'\midrule')
    rows.append(f'\\textbf{{All}} & \\textbf{{{len(df)}}} & {df.noise_dB.median():.0f} & '
                f'{df.noise_dB.min():.0f}--{df.noise_dB.max():.0f} & '
                f'{100 * (df.noise_dB < 60).mean():.0f}\\% & '
                f'{roadside_share(df):.0f}\\% \\\\')
    rows += [r'\bottomrule', r'\end{tabular}']
    open(out, 'w').write('% Generated by scripts/10_build_report.py\n' + '\n'.join(rows) + '\n')


def write_model_table(metrics, out):
    """One row per model, the three protocols side by side, CI on the reference."""
    order = ['global_mean', 'site_mean', 'site_hour_mean', 'dist_road', 'idw',
             'lgbm_time', 'lgbm_morpho', 'lgbm_full', 'lgbm_v2',
             'physical', 'hybrid', 'hybrid_lowcap']
    delivered = metrics['meta']['delivered_model']
    lines = [r'\begin{tabular}{@{}lccccr@{}}', r'\toprule',
             r'& \textbf{Block-CV} & \textbf{Buffered LOO} & & \textbf{LOSO} & \textbf{MAE} \\',
             r'\textbf{Model} & $R^2$ & $R^2$ \emph{(reference)} & \textbf{95\,\% CI} & '
             r'$R^2$ & \textbf{dB} \\', r'\midrule']
    for k in order:
        if k not in metrics['bloo']['models']:
            continue
        def r2(p):
            v = metrics[p]['models'].get(k)
            return f"{v['r2']:+.3f}" if v and v.get('r2') is not None else '---'
        b = metrics['bloo']['models'][k]
        ci = b.get('r2_ci95')
        cis = f'$[{ci[0]:+.3f},\\, {ci[1]:+.3f}]$' if ci else '---'
        name = r'\texttt{' + tex_escape(k) + '}'
        if k == delivered:
            name = r'\textbf{' + name + '}'
        lines.append(f"{name} & ${r2('block_cv')}$ & $\\mathbf{{{r2('bloo')}}}$ & {cis} & "
                     f"${r2('loso')}$ & {b['mae']:.2f} \\\\")
    lines += [r'\bottomrule', r'\end{tabular}']
    open(out, 'w').write('% Generated by scripts/10_build_report.py\n' + '\n'.join(lines) + '\n')


def write_exceedance_table(out):
    path = os.path.join(cfg.TABLES, 'hanoi_exceedances.csv')
    head = [r'\begin{tabular}{@{}llrrrr@{}}', r'\toprule',
            r'\textbf{Site} & \textbf{Period} & \textbf{n} & \textbf{Median dB} & '
            r'\textbf{\% above threshold} & \textbf{Mean excess dB} \\', r'\midrule']
    foot = [r'\bottomrule', r'\end{tabular}']
    if not os.path.exists(path):
        open(out, 'w').write('\n'.join(head + [r'\multicolumn{6}{c}{\emph{run '
                             r'scripts/09b\_build\_analyses.py}} \\'] + foot) + '\n')
        return
    e = pd.read_csv(path)
    lines = [f"{tex_escape(str(r.site))} & {r.period} & {int(r.n)} & {r.dB_median:.1f} & "
             f"{r.pct_depassement:.1f}\\% & {r.severite_moy_dB:.1f} \\\\"
             for r in e.itertuples()]
    open(out, 'w').write('% Generated by scripts/10_build_report.py\n'
                         + '\n'.join(head + lines + foot) + '\n')


def write_anchor_table(out):
    path = os.path.join(cfg.TABLES, 'literature_anchoring.csv')
    # raggedright in the wide columns: justified text in a 5 cm box hyphenates
    # journal names into unreadable fragments.
    head = [r'\begin{tabular}{@{}>{\raggedright\arraybackslash}p{5.4cm}'
            r'>{\raggedright\arraybackslash}p{2.9cm}'
            r'>{\raggedright\arraybackslash}p{1.9cm}rr@{}}', r'\toprule',
            r'\textbf{Source} & \textbf{Instrument} & \textbf{Quantity} & '
            r'\textbf{Raw gap} & \textbf{Corrected} \\', r'\midrule']
    foot = [r'\bottomrule', r'\end{tabular}']
    if not os.path.exists(path):
        open(out, 'w').write('\n'.join(head + [r'\multicolumn{5}{c}{\emph{run '
                             r'scripts/06\_anchor\_literature.py}} \\'] + foot) + '\n')
        return
    a = pd.read_csv(path)
    lines = []
    for r in a.itertuples():
        grey = str(r.status) == 'grey'
        # No truncation: the p{} columns wrap. Slicing here used to cut source
        # strings mid-page-number ("148:332-34") and mid-parenthesis.
        cells = [tex_escape(str(r.source)), tex_escape(str(r.instrument)),
                 tex_escape(str(r.metric)),
                 f'{r.gap_raw_dB:+.1f}' if pd.notna(r.gap_raw_dB) else '---',
                 f'{r.gap_after_metric_correction_dB:+.1f}'
                 if pd.notna(r.gap_after_metric_correction_dB) else '---']
        if grey:
            cells = [r'\textcolor{gray}{' + c + '}' for c in cells]
        lines.append(' & '.join(cells) + r' \\')
    open(out, 'w').write('% Generated by scripts/10_build_report.py\n'
                         + '\n'.join(head + lines + foot) + '\n')


def compile_report(report_dir):
    if shutil.which('latexmk') is None:
        print('  latexmk not found: the .tex inputs are written, the PDF is not built.')
        return False
    print('  latexmk report.tex')
    r = subprocess.run(['latexmk', '-pdf', '-interaction=nonstopmode', '-halt-on-error',
                        'report.tex'], cwd=report_dir,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if r.returncode != 0:
        tail = '\n'.join(r.stdout.splitlines()[-25:])
        print(tail)
        sys.exit(f'latexmk failed (exit {r.returncode}). '
                 f'See {os.path.join(report_dir, "report.log")}.')
    subprocess.run(['latexmk', '-c'], cwd=report_dir,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--no-compile', action='store_true',
                    help='write the .tex inputs and stop')
    args = ap.parse_args()

    df, metrics = load()
    bias_lo, bias_hi = read_bias_interval()
    rd = cfg.REPORT_DIR
    os.makedirs(rd, exist_ok=True)

    print(f'Report inputs -> {rd}')
    app = mobile_facts()
    if app is None:
        print('  note: mobile/ is absent, the application section will not resolve.')
    write_numbers(df, metrics, bias_lo, bias_hi, os.path.join(rd, 'numbers.tex'), app)
    write_site_table(df, os.path.join(rd, 'tab_sites.tex'))
    write_model_table(metrics, os.path.join(rd, 'tab_models.tex'))
    write_exceedance_table(os.path.join(rd, 'tab_exceedances.tex'))
    write_anchor_table(os.path.join(rd, 'tab_anchors.tex'))
    for f in ('numbers', 'tab_sites', 'tab_models', 'tab_exceedances', 'tab_anchors'):
        print(f'  {f}.tex')

    missing = [f for f in ('analyse_1_horaire.png', 'analyse_2_jour.png',
                           'analyse_3_type.png', 'analyse_4_depassement.png',
                           'analyse_5_meteo.png')
               if not os.path.exists(os.path.join(cfg.FIGURES, f))]
    if missing:
        print(f'  note: {len(missing)} figure(s) absent, run scripts/09b_build_analyses.py: '
              + ', '.join(missing))

    if args.no_compile:
        print('  --no-compile: stopping before latexmk.')
        return
    if compile_report(rd):
        print(f'OK -> {cfg.REPORT_PDF}')


if __name__ == '__main__':
    main()

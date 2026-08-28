#!/usr/bin/env python3
"""Figures drawn for the end-of-internship deck.

The deck was almost entirely typeset text. These are the figures that carry the
arguments the text was making in prose, so a slide can show the result instead
of describing it.

Everything here reads `models/metrics.json`, `data/processed/measurements.csv`
and `results/maps/hanoi_noise_map.csv`. **No number is typed in this file.**
That is the same rule the deck, the report and the app already follow: every
published figure has exactly one home, and this script is a renderer, not a
source.

Output goes to `presentation/figures/*.pdf` — vector, because the deck is
projected. Labels are English: the existing `results/figures/` set is French
(see `results/figures/sunbird/NOT-REGENERABLE.md`) and could not be reused.

    python scripts/12_presentation_figures.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "presentation" / "figures"

# The deck's palette, verbatim from main.tex. Keeping the figures on the same
# five colours is what stops them reading as imported from another document.
INK = "#1A1A1A"
ACCENT = "#1F5C8B"
GOOD = "#2E7D32"
# Green is a LINE colour here, never a font colour. Set as type it reads as a
# highlighter even at this darkness -- against black body text on white paper
# it looks like something the reader is meant to click. Every label that used
# to be green is INK; the line beside it still carries the meaning.
BAD = "#C62828"
WARN = "#EF6C00"
MUTED = "#6E6E6E"
RULE = "#D8D8D4"

# QCVN 26:2010 reading bands. Descriptive only — the same use the published map
# and the app make of them, and never a compliance statement. See
# docs/metrology.md: our quantity is not the quantity the standard regulates.
#
# The ramp is ordered by lightness, not by hue. The previous one ran
# green -> yellow-green -> lime -> yellow (#7CB342, #C0CA33, #F9A825) and its
# three middle bands sat within a few points of the same lightness: printed,
# and on a projector, 55-60 / 60-65 / 65-70 were one washed-out band. Since
# those three cover most of the mapped area, the map read as noise. Each band
# below is now clearly darker than the one under it, so the order survives
# greyscale printing and the two common red-green deficiencies; the hue break
# at 60 dB is deliberate and marks where the bands stop being quiet.
BANDS = [
    (-np.inf, 55, "#14654A", "< 55"),
    (55, 60, "#4FA07C", "55 – 60"),
    (60, 65, "#F5D06B", "60 – 65"),
    (65, 70, "#EE9422", "65 – 70"),
    (70, 75, "#D6541E", "70 – 75"),
    (75, 80, "#A31E1E", "75 – 80"),
    (80, np.inf, "#5E0F14", "> 80"),
]


def style() -> None:
    """Deck typography. Lato if the system has it, matplotlib's default if not."""
    installed = {f.name for f in matplotlib.font_manager.fontManager.ttflist}
    family = "Lato" if "Lato" in installed else "DejaVu Sans"
    plt.rcParams.update(
        {
            "font.family": family,
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "axes.edgecolor": MUTED,
            "axes.labelcolor": INK,
            "axes.linewidth": 0.6,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "text.color": INK,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.frameon": False,
            "legend.fontsize": 8,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.02,
            "pdf.fonttype": 42,
        }
    )


def save(fig: plt.Figure, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.pdf"
    fig.savefig(path)
    plt.close(fig)
    print(f"  {path.relative_to(ROOT)}")


def metrics() -> dict:
    return json.loads((ROOT / "models" / "metrics.json").read_text())


def measurements() -> pd.DataFrame:
    df = pd.read_csv(ROOT / "data" / "processed" / "measurements.csv")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["date"] = df["timestamp"].dt.date
    return df


# ---------------------------------------------------------------------------
# 1. The ranking inversion
# ---------------------------------------------------------------------------
def fig_ranking_inversion(m: dict) -> None:
    """The result of the whole study, as one picture.

    A slope chart across the three splits. The elaborate models start at the top
    of the permissive split and fall through the floor on the strict ones; the
    three-parameter kernel is the only line that stays flat. The table version of
    this lives on the same slide — the chart is what makes the crossing visible
    from the back of the room.
    """
    protocols = ["block_cv", "bloo", "loso"]
    headers = [
        ("Block-CV 600 m", "permissive"),
        ("Buffered LOO 300 m", "reference"),
        ("Leave-one-site-out", "strictest"),
    ]
    shown = {
        "dist_road": (r"$\log(d_\mathrm{road})$, 2 param.", MUTED, 1.1, "-"),
        "physical": ("Physical kernel, 3 param.", GOOD, 2.6, "-"),
        "lgbm_full": ("LightGBM v1", BAD, 1.3, "--"),
        "lgbm_v2": ("LightGBM v2", BAD, 1.3, ":"),
        "hybrid": ("Hybrid (physics + ML)", BAD, 2.0, "-"),
    }

    fig, ax = plt.subplots(figsize=(7.6, 3.4))
    xs = np.arange(3.0)

    for key, (label, colour, lw, ls) in shown.items():
        ys = [m[p]["models"][key]["r2"] for p in protocols]
        ax.plot(xs, ys, ls, color=colour, lw=lw, marker="o", ms=4.5,
                markeredgecolor="white", markeredgewidth=0.7, zorder=3)

    # The two losing lines finish within a hundredth of each other, so the end
    # labels have to be pushed apart by hand or they overprint.
    ends = {k: m["loso"]["models"][k]["r2"] for k in shown}
    placed: list[float] = []
    for key in sorted(ends, key=ends.get, reverse=True):
        label, colour, _, _ = shown[key]
        y = ends[key]
        while any(abs(y - p) < 0.035 for p in placed):
            y -= 0.012
        placed.append(y)
        ax.annotate(
            f"{label}   {ends[key]:+.3f}",
            xy=(2.05, y), xytext=(0, 0), textcoords="offset points",
            va="center", ha="left", fontsize=8, color=INK,
            fontweight="bold" if key == "physical" else "normal",
        )

    ax.axhline(0, color=RULE, lw=0.8, zorder=1)
    ax.annotate("no better than predicting the mean", xy=(0.03, 0),
                xytext=(0, -10), textcoords="offset points", fontsize=7.5,
                color=MUTED)

    ax.set_xticks(xs)
    ax.set_xticklabels([h[0] for h in headers], fontsize=8.5, color=INK)
    for x, (_, sub) in zip(xs, headers):
        weight = "bold" if sub == "reference" else "normal"
        ax.annotate(sub, xy=(x, 0), xycoords=("data", "axes fraction"),
                    xytext=(0, -26), textcoords="offset points",
                    ha="center", fontsize=7.5, color=MUTED, fontweight=weight)

    ax.set_ylabel("$R^2$")
    # The right third of the axes is label gutter: nothing is plotted past x = 2.
    ax.set_xlim(-0.06, 3.35)
    ax.set_ylim(-0.09, 0.44)
    ax.spines["bottom"].set_visible(False)
    ax.tick_params(axis="x", length=0)
    ax.grid(axis="y", color=RULE, lw=0.5, alpha=0.6)
    ax.set_axisbelow(True)
    save(fig, "ranking-inversion")


# ---------------------------------------------------------------------------
# 2. The confidence intervals
# ---------------------------------------------------------------------------
def fig_forest_bloo(m: dict) -> None:
    """Every model under the reference protocol, with the interval that qualifies it.

    Audit finding 3 says the headline ranking is not statistically separated.
    That is a claim about overlap, and overlap is a thing you see, not a thing
    you read off a table of point estimates.
    """
    models = m["bloo"]["models"]
    order = sorted(models, key=lambda k: models[k]["r2"])
    labels = {
        "global_mean": "Global mean",
        "site_mean": "Mean per site",
        "site_hour_mean": "Mean per (site, hour)",
        "dist_road": r"$\log(d_\mathrm{road})$ regression",
        "idw": "Inverse distance weighting",
        "lgbm_time": "LightGBM — time only",
        "lgbm_morpho": "LightGBM — morphology only",
        "lgbm_full": "LightGBM v1",
        "lgbm_v2": "LightGBM v2",
        "physical": "Physical kernel  (delivered)",
        "hybrid": "Hybrid — physics + residual",
        "hybrid_lowcap": "Hybrid — constrained residual",
    }

    fig, ax = plt.subplots(figsize=(7.0, 3.9))
    for i, key in enumerate(order):
        e = models[key]
        lo, hi = e["r2_ci95"]
        delivered = key == m["meta"]["delivered_model"]
        colour = GOOD if delivered else (MUTED if e["r2"] < 0 else ACCENT)
        ax.plot([lo, hi], [i, i], color=colour, lw=2.4 if delivered else 1.4,
                alpha=1.0 if delivered else 0.55, solid_capstyle="round")
        ax.plot([e["r2"]], [i], "o", ms=6 if delivered else 4.5, color=colour,
                markeredgecolor="white", markeredgewidth=0.8, zorder=3)
        ax.annotate(f"{e['r2']:+.3f}", xy=(hi, i), xytext=(5, 0),
                    textcoords="offset points", va="center", fontsize=7.5,
                    color=INK)

    ax.axvline(0, color=RULE, lw=0.8)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(
        [labels[k] for k in order], fontsize=8,
        color=INK,
    )
    for tick, key in zip(ax.get_yticklabels(), order):
        if key == m["meta"]["delivered_model"]:
            tick.set_fontweight("bold")
            tick.set_color(INK)
    ax.set_xlabel("$R^2$ under buffered leave-one-out, 95 % interval bootstrapped by block")
    ax.set_xlim(-0.85, 0.62)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color=RULE, lw=0.5, alpha=0.6)
    ax.set_axisbelow(True)
    save(fig, "forest-bloo")


# ---------------------------------------------------------------------------
# 3. The campaign
# ---------------------------------------------------------------------------
def fig_campaign(df: pd.DataFrame, m: dict) -> None:
    """What 363 points over three sites actually look like.

    Left: the level distribution per site, which is the contrast the protocol
    supports. Right: the hourly profile, which is the other one. Both are shown
    as spread, not as a mean, because the spread is the argument.
    """
    sites = list(m["meta"]["sites"].keys())
    colours = {sites[0]: ACCENT, sites[1]: WARN, sites[2]: GOOD}

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.2, 3.1),
                                   gridspec_kw={"width_ratios": [1, 1.3]})

    # --- per site
    for i, site in enumerate(sites):
        v = df.loc[df["site"] == site, "noise_dB"].to_numpy()
        parts = ax1.violinplot([v], positions=[i], widths=0.75,
                               showextrema=False, showmedians=False)
        for body in parts["bodies"]:
            body.set_facecolor(colours[site])
            body.set_alpha(0.22)
            body.set_edgecolor(colours[site])
        q1, med, q3 = np.percentile(v, [25, 50, 75])
        ax1.plot([i, i], [q1, q3], color=colours[site], lw=3.2,
                 solid_capstyle="round")
        ax1.plot([i], [med], "o", ms=5, color="white",
                 markeredgecolor=colours[site], markeredgewidth=1.6, zorder=3)
        ax1.annotate(f"n = {len(v)}", xy=(i, 44.5), ha="center", fontsize=7.5,
                     color=MUTED)

    ax1.set_xticks(range(len(sites)))
    ax1.set_xticklabels(
        ["Ocean Park\nnew\nperi-urban", "Hoan Kiem\ndense\nhistoric",
         "Vinh Tuy\ntransport\ncorridor"],
        fontsize=7.5, color=INK, linespacing=1.35,
    )
    ax1.set_ylabel(r"$L_{A,25\mathrm{s}}$  (dB)")
    ax1.set_ylim(42, 92)
    ax1.tick_params(axis="x", length=0)
    ax1.grid(axis="y", color=RULE, lw=0.5, alpha=0.6)
    ax1.set_axisbelow(True)
    ax1.set_title("The contrast between sites", fontsize=9, color=INK,
                  loc="left", pad=8)

    # --- per hour
    for site in sites:
        g = df[df["site"] == site].groupby("hour")["noise_dB"]
        h = g.mean()
        keep = g.size() >= 3          # an hour sampled twice is not a profile
        h = h[keep]
        ax2.plot(h.index, h.to_numpy(), "-o", ms=3.5, lw=1.4,
                 color=colours[site], label=site, alpha=0.9)

    ax2.set_xlabel("Hour of day")
    ax2.set_ylabel(r"mean $L_{A,25\mathrm{s}}$  (dB)")
    ax2.set_xlim(5.5, 21.5)
    ax2.set_xticks(range(6, 22, 2))
    ax2.grid(color=RULE, lw=0.5, alpha=0.6)
    ax2.set_axisbelow(True)
    ax2.legend(loc="lower left", fontsize=7.5, ncol=1, handlelength=1.4)
    ax2.set_title("The contrast between hours  (hours with n ≥ 3)",
                  fontsize=9, color=INK, loc="left", pad=8)

    fig.subplots_adjust(wspace=0.32)
    save(fig, "campaign")


# ---------------------------------------------------------------------------
# 4. The 27 June discontinuity
# ---------------------------------------------------------------------------
def fig_discontinuity(df: pd.DataFrame) -> None:
    """Audit finding 1, drawn.

    The break date is not chosen here: it is the date the form version changed,
    documented in docs/audit/. The figure only shows what the level distribution
    does around it.
    """
    break_date = pd.Timestamp("2026-06-27")
    df = df.sort_values("timestamp")
    before = df[df["timestamp"] < break_date]
    after = df[df["timestamp"] >= break_date]

    fig, ax = plt.subplots(figsize=(7.4, 3.0))

    for part, colour in ((before, BAD), (after, ACCENT)):
        ax.plot(part["timestamp"], part["noise_dB"], "o", ms=3.2, alpha=0.35,
                color=colour, markeredgewidth=0)
        daily = part.groupby(part["timestamp"].dt.floor("D"))["noise_dB"].mean()
        ax.plot(daily.index, daily.to_numpy(), "-", lw=1.6, color=colour)
        ax.hlines(part["noise_dB"].mean(), part["timestamp"].min(),
                  part["timestamp"].max(), color=colour, lw=1.2, ls="--",
                  alpha=0.9)
        ax.annotate(
            f"mean {part['noise_dB'].mean():.1f} dB",
            xy=(part["timestamp"].median(), part["noise_dB"].mean()),
            xytext=(0, 6), textcoords="offset points", ha="center",
            fontsize=8, color=colour, fontweight="bold",
        )

    ax.axvline(break_date, color=INK, lw=1.0)
    ax.annotate("27 June — the form version changes",
                xy=(break_date, 90), xytext=(6, 0), textcoords="offset points",
                fontsize=8, color=INK, va="top")

    ax.set_ylabel(r"$L_{A,25\mathrm{s}}$  (dB)")
    ax.set_ylim(44, 92)
    ax.grid(axis="y", color=RULE, lw=0.5, alpha=0.6)
    ax.set_axisbelow(True)
    ax.legend(
        handles=[
            Line2D([], [], color=BAD, lw=2, label=f"before  (n = {len(before)})"),
            Line2D([], [], color=ACCENT, lw=2, label=f"after  (n = {len(after)})"),
        ],
        loc="lower left", fontsize=8,
    )
    fig.autofmt_xdate(rotation=0, ha="center")
    save(fig, "discontinuity")


# ---------------------------------------------------------------------------
# 5. Feature importance, in English
# ---------------------------------------------------------------------------
def fig_feature_importance(m: dict) -> None:
    """What the learned model leaned on — kept because it explains the ablation.

    `results/figures/sunbird/feature_importance.png` is the Uganda reproduction
    with French labels and cannot be regenerated. This is the Hanoi model's own
    gain, read from metrics.json.
    """
    gain = m["feature_importance_gain"]
    pretty = {
        "built_area_ratio": "Built area ratio",
        "road_density_km_km2": "Road density",
        "dist_highway_m": "Distance to highway",
        "is_weekend": "Weekend",
        "hour_sin": "Hour (sin)",
        "dist_residential_m": "Distance to residential road",
        "hour_cos": "Hour (cos)",
        "intersection_count": "Intersection count",
    }
    keys = sorted(gain, key=gain.get)
    total = sum(gain.values())

    fig, ax = plt.subplots(figsize=(5.4, 3.0))
    ys = np.arange(len(keys))
    vals = [100 * gain[k] / total for k in keys]
    morpho = {"built_area_ratio", "road_density_km_km2", "dist_highway_m",
              "dist_residential_m", "intersection_count"}
    colours = [ACCENT if k in morpho else WARN for k in keys]
    ax.barh(ys, vals, height=0.62, color=colours, alpha=0.85)
    for y, v in zip(ys, vals):
        ax.annotate(f"{v:.0f} %", xy=(v, y), xytext=(4, 0),
                    textcoords="offset points", va="center", fontsize=7.5,
                    color=MUTED)

    ax.set_yticks(ys)
    ax.set_yticklabels([pretty.get(k, k) for k in keys], fontsize=8, color=INK)
    ax.set_xlabel("share of total split gain")
    ax.set_xlim(0, max(vals) * 1.18)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color=RULE, lw=0.5, alpha=0.6)
    ax.set_axisbelow(True)
    ax.legend(
        handles=[Patch(color=ACCENT, alpha=0.85, label="morphology"),
                 Patch(color=WARN, alpha=0.85, label="time")],
        loc="lower right", fontsize=8,
    )
    save(fig, "feature-importance")


# ---------------------------------------------------------------------------
# 6. The ceiling on R^2
# ---------------------------------------------------------------------------
def fig_ceiling(df: pd.DataFrame, m: dict) -> None:
    """The answer to "R2 = 0.25 --- isn't that very low?", drawn.

    Two measurements a few metres apart at the same hour must be predicted
    identically by any spatial model, so whatever they disagree by is variance no
    spatial model can explain. That disagreement bounds the achievable R2, and
    the bound is far below 1.

    The conversion: for two readings of a common value with error sd sigma, the
    difference is N(0, 2 sigma^2), so E|difference| = 2 sigma / sqrt(pi) and
    sigma = mean|difference| * sqrt(pi) / 2.

    docs/presentation-brief.md sec. 3 states the caveat that belongs on the same
    slide: pairs at the same hour may fall on different days, so this sigma
    carries day-to-day variation too and overestimates pure measurement noise.
    It is an order of magnitude, not a bound.
    """
    R = 6_371_000.0
    lat = np.radians(df["latitude"].to_numpy())
    lon = np.radians(df["longitude"].to_numpy())
    x = R * lon * np.cos(lat.mean())
    y = R * lat
    sep = np.hypot(x[:, None] - x[None, :], y[:, None] - y[None, :])
    hour = df["hour"].to_numpy()
    same_hour = hour[:, None] == hour[None, :]
    level = df["noise_dB"].to_numpy()
    iu = np.triu_indices(len(df), 1)

    total_var = float(np.var(level, ddof=1))
    bands = [20, 40, 60]
    rows = []
    for b in bands:
        keep = (sep[iu] < b) & same_hour[iu]
        diff = np.abs(level[iu[0]][keep] - level[iu[1]][keep])
        sigma = diff.mean() * np.sqrt(np.pi) / 2
        rows.append((b, int(keep.sum()), diff.mean(), sigma,
                     1 - sigma**2 / total_var))

    delivered = m["bloo"]["models"][m["meta"]["delivered_model"]]["r2"]

    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    xs = np.arange(len(rows))
    ceilings = [r[4] for r in rows]
    ax.bar(xs, ceilings, width=0.5, color=ACCENT, alpha=0.20,
           edgecolor=ACCENT, linewidth=0.8)
    ax.bar(xs, [delivered] * len(rows), width=0.5, color=GOOD, alpha=0.85)

    for i, (b, n, md, sd, ceil) in enumerate(rows):
        ax.annotate(f"{ceil:.2f}", xy=(i, ceil), xytext=(0, 4),
                    textcoords="offset points", ha="center", fontsize=8.5,
                    color=ACCENT, fontweight="bold")

    ax.annotate(f"delivered model  {delivered:.3f}", xy=(len(rows) - 0.7, delivered),
                xytext=(6, 0), textcoords="offset points", va="center",
                fontsize=8.5, color=INK, fontweight="bold")

    ax.set_xticks(xs)
    ax.set_xticklabels(
        [f"pairs < {b} m apart, same hour\n"
         f"{n} pairs, {md:.2f} dB apart\n"
         f"$\\Rightarrow\\ \\sigma \\approx$ {sd:.1f} dB"
         for b, n, md, sd, _ in rows],
        fontsize=7.8, color=INK, linespacing=1.7)
    ax.set_ylabel("$R^2$")
    ax.set_ylim(0, 0.78)
    ax.set_xlim(-0.55, len(rows) - 0.05)
    ax.tick_params(axis="x", length=0, pad=8)
    ax.spines["bottom"].set_visible(False)
    ax.grid(axis="y", color=RULE, lw=0.5, alpha=0.6)
    ax.set_axisbelow(True)
    ax.set_title("What any spatial model could reach, given how much two "
                 "neighbouring points disagree",
                 fontsize=9, color=INK, loc="left", pad=8)
    save(fig, "ceiling")


# ---------------------------------------------------------------------------
# 7. The map, in English
# ---------------------------------------------------------------------------
def fig_map(m: dict) -> None:
    """The published grid, redrawn from the CSV rather than screenshotted.

    `results/figures/noise-map-oceanpark-17h.png` is a GAMA capture with a French
    overlay — the deck's one non-English element. This draws the same quantity
    from `results/maps/hanoi_noise_map.csv`, which is the file the map, the report
    and the app all read.
    """
    grid = pd.read_csv(ROOT / "results" / "maps" / "hanoi_noise_map.csv")
    hour = "h17"
    sites = list(m["meta"]["sites"].keys())

    # The CSV is one row per cell, not a raster: the grid is regular in UTM 48 N
    # and the export carries it back as lat/lon, so no two cells share a
    # coordinate. Binning onto a lattice at the grid step rebuilds the raster.
    cmap = matplotlib.colors.ListedColormap([c for _, _, c, _ in BANDS])
    norm = matplotlib.colors.BoundaryNorm(
        [40] + [hi for _, hi, _, _ in BANDS[:-1]] + [110], cmap.N
    )

    step_m = 40.0            # the export's own grid step, docs/methodology.md

    def rasterise(g: pd.DataFrame) -> np.ndarray:
        """Bin the cells of one site onto a 40 m lattice, averaging collisions.

        Local equirectangular is accurate to well under a cell over a 2 km site,
        and the alternative — snapping to the unique coordinates — aliases,
        because the UTM grid is rotated a little against the meridian.
        """
        lat0 = float(g["latitude"].mean())
        x = (g["longitude"] - g["longitude"].min()) * 111_320 * np.cos(np.radians(lat0))
        y = (g["latitude"] - g["latitude"].min()) * 110_540
        ix = np.rint(x / step_m).astype(int)
        iy = np.rint(y / step_m).astype(int)
        flat = iy * (ix.max() + 1) + ix
        size = (iy.max() + 1) * (ix.max() + 1)
        total = np.bincount(flat, weights=g[hour].to_numpy(), minlength=size)
        count = np.bincount(flat, minlength=size)
        with np.errstate(invalid="ignore"):
            out = np.where(count > 0, total / np.maximum(count, 1), np.nan)
        return out.reshape(iy.max() + 1, ix.max() + 1)

    fig, axes = plt.subplots(1, 3, figsize=(7.8, 2.8))
    for ax, site in zip(axes, sites):
        g = grid[grid["site"] == site]
        ax.imshow(rasterise(g), origin="lower", cmap=cmap, norm=norm,
                  interpolation="nearest", aspect="equal")
        ax.set_title(f"{site}\n{len(g):,} cells".replace(",", " "),
                     fontsize=8, color=INK, pad=6)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_color(RULE)

    fig.legend(
        handles=[Patch(color=c, label=lab) for _, _, c, lab in BANDS],
        loc="lower center", ncol=7, fontsize=7.5, handlelength=1.1,
        columnspacing=1.0, bbox_to_anchor=(0.5, -0.06),
        title=r"predicted $L_{A,25\mathrm{s}}$ at 17:00  (dB) — QCVN 26:2010 reading bands, descriptive",
        title_fontsize=7.5,
    )
    fig.legends[0].get_title().set_color(MUTED)
    save(fig, "map-grid")


# ---------------------------------------------------------------------------
# 8. Where the 363 measurements actually are
# ---------------------------------------------------------------------------
def frame_units(wards, developments):
    """The sampling frame: every phuong, plus every xa holding a new town.

    The administrative label is not the question the campaign is asking. Hanoi
    keeps calling a commune a xa long after it has been built over -- Ocean
    Park sits in Xa Gia Lam, and half this project's measurements were taken
    there. A frame of "the 51 urban phuong" would exclude it, and with it every
    other new town on the periphery, which is precisely the typology a noise
    study of a growing city cannot leave out.

    So the test is what is built, not what it is called: a unit is in the frame
    if it is a phuong, or if it contains a named new urban development
    (`khu do thi` and the developer names that do not use the term). Computed
    from the data, not listed by hand -- add a development to OSM and the frame
    picks it up.
    """
    import geopandas as gpd

    located = gpd.sjoin(developments, wards, predicate="within", how="left")
    with_dev = set(located["name_right"].dropna())
    keep = (wards["kind"] == "phuong") | (wards["name"].isin(with_dev))
    return wards[keep], wards[~keep]


def video_coverage(df: pd.DataFrame) -> pd.Series:
    """True where a measurement has a traffic video matched to it.

    The match is the pipeline's own, from data/processed/vehicle_counts.csv --
    not recomputed here, because a second definition of "matched" is a second
    home for the number.
    """
    counts = pd.read_csv(ROOT / "data" / "processed" / "vehicle_counts.csv",
                         parse_dates=["matched_timestamp"])
    return df["timestamp"].isin(set(counts["matched_timestamp"].dropna()))


def fig_sites_map(df: pd.DataFrame) -> None:
    """All of Hanoi, the frame, and which measurements carry video.

    Two things are drawn that the earlier version of this figure did not have.
    The whole city rather than a bounding box around three sites, so the frame
    and the gap in it can both be seen; and the audio/video split, because the
    campaign records two instruments and only one of them ran everywhere. Of
    the 363 measurements, 142 have a matched traffic video and 221 do not, and
    the difference is not evenly spread: Ocean Park, the largest site, is the
    thinnest covered.

    Detail panels are cut to the SAME box in kilometres so their densities can
    be compared by eye.
    """
    import geopandas as gpd

    wards = gpd.read_file(ROOT / "data" / "processed" / "hanoi_wards.geojson")
    devs = gpd.read_file(ROOT / "data" / "processed"
                         / "hanoi_new_developments.geojson")
    inside, outside = frame_units(wards, devs)

    df = df.copy()
    df["has_video"] = video_coverage(df)
    n_video = int(df["has_video"].sum())

    lat0 = float(df["latitude"].mean())
    kx = 111.320 * np.cos(np.radians(lat0))
    aspect = 1 / np.cos(np.radians(lat0))

    sites = ["Ocean Park", "Hoan Kiem lake", "Vinh Tuy area"]
    stems = {"Ocean Park": "oceanpark_roads", "Hoan Kiem lake": "hoankiem_roads",
             "Vinh Tuy area": "vinhtuy_roads"}
    roads = {}
    for site, stem in stems.items():
        path = ROOT / "simulation" / "gama" / "inputs" / f"{stem}.shp"
        roads[site] = gpd.read_file(path) if path.exists() else None

    def draw_roads(ax, gdf, lw):
        if gdf is None:
            return
        for geom in gdf.geometry:
            parts = geom.geoms if geom.geom_type == "MultiLineString" else [geom]
            for part in parts:
                x, y = part.xy
                ax.plot(np.asarray(x), np.asarray(y), color=RULE, lw=lw,
                        zorder=1, solid_capstyle="round")

    def scalebar(ax, km, label, fx, fy):
        x0, x1 = ax.get_xlim()
        y0, y1 = ax.get_ylim()
        dx = km / kx
        bx, by = x0 + (x1 - x0) * fx, y0 + (y1 - y0) * fy
        ax.plot([bx, bx + dx], [by, by], color=INK, lw=1.6,
                solid_capstyle="butt", zorder=7)
        ax.text(bx + dx / 2, by + (y1 - y0) * 0.022, label, ha="center",
                va="bottom", fontsize=6.5, color=INK, zorder=7)

    def frame_off(ax):
        ax.set_xticks([])
        ax.set_yticks([])
        # The stylesheet hides the top and right spines, which is right for a
        # chart and wrong for a map: a map wants a closed neat line.
        for sp in ax.spines.values():
            sp.set_visible(True)
            sp.set_color(RULE)

    # Hanoi province is taller than it is wide, so a full-width overview
    # leaves half the panel empty and puts the three measured areas -- which
    # are 11 km apart in a city 70 km across -- inside one blob with three
    # labels fighting over it. The overview keeps its own proportions on the
    # left; a zoom on the urban core takes the space that would have been
    # white, and carries the labels.
    fig = plt.figure(figsize=(7.8, 6.9))
    gs = fig.add_gridspec(2, 3, height_ratios=[4.3, 2.4], hspace=0.22,
                          wspace=0.10)
    gs_top = gs[0, :].subgridspec(1, 2, width_ratios=[1, 1.45], wspace=0.06)

    # ---- all of Hanoi ----------------------------------------------------
    ax = fig.add_subplot(gs_top[0, 0])
    outside.plot(ax=ax, facecolor="#F6F6F4", edgecolor="white", linewidth=0.3,
                 zorder=1)
    inside.plot(ax=ax, facecolor=ACCENT, alpha=0.14, edgecolor=ACCENT,
                linewidth=0.4, zorder=2)
    ax.scatter(devs.geometry.x, devs.geometry.y, s=9, marker="^",
               facecolor="white", edgecolor=WARN, linewidths=0.7, zorder=4)

    # At province scale the three areas are one dot; the box marks where the
    # zoom beside it comes from.
    zx0, zx1 = df["longitude"].min() - 0.075, df["longitude"].max() + 0.075
    zy0, zy1 = df["latitude"].min() - 0.055, df["latitude"].max() + 0.055
    ax.plot([zx0, zx1, zx1, zx0, zx0], [zy0, zy0, zy1, zy1, zy0],
            color=BAD, lw=1.0, zorder=7)

    ax.set_aspect(aspect)
    frame_off(ax)
    scalebar(ax, 20, "20 km", 0.05, 0.04)
    ax.set_title("Hanoi, whole", fontsize=8.5, color=INK, loc="left", pad=6)

    # ---- the urban core, where everything is -----------------------------
    axc = fig.add_subplot(gs_top[0, 1])
    outside.plot(ax=axc, facecolor="#F6F6F4", edgecolor="white",
                 linewidth=0.3, zorder=1)
    inside.plot(ax=axc, facecolor=ACCENT, alpha=0.14, edgecolor=ACCENT,
                linewidth=0.4, zorder=2)
    axc.scatter(devs.geometry.x, devs.geometry.y, s=14, marker="^",
                facecolor="white", edgecolor=WARN, linewidths=0.8, zorder=4)

    for site, dy in zip(sites, (1, -1, -1)):
        g = df[df["site"] == site]
        got = int(g["has_video"].sum())
        axc.plot(g["longitude"].mean(), g["latitude"].mean(), "o", ms=7,
                 color=BAD, markeredgecolor="white", markeredgewidth=1.1,
                 zorder=6)
        axc.annotate(
            f"{site}\n{len(g)} pts · {got} with video",
            xy=(g["longitude"].mean(), g["latitude"].mean()),
            xytext=(0, 13 * dy), textcoords="offset points", ha="center",
            va="bottom" if dy > 0 else "top", fontsize=7.5, color=INK,
            fontweight="bold", linespacing=1.3, zorder=7,
        )

    axc.plot([], [], "o", ms=7, color=BAD, markeredgecolor="white",
             markeredgewidth=1.1, label="measured — 3 areas, 363 points")
    axc.plot([], [], "^", ms=6, color="white", markeredgecolor=WARN,
             markeredgewidth=0.9,
             label=f"{len(devs)} named new urban developments")
    axc.plot([], [], "s", ms=8, color=ACCENT, alpha=0.4,
             label=f"the frame — {len(inside)} units: "
                   f"{int((inside['kind'] == 'phuong').sum())} phuong + "
                   f"{int((inside['kind'] == 'xa').sum())} xa with a new town")
    axc.plot([], [], "s", ms=8, color="#EDEDEA",
             label=f"{len(outside)} rural units — outside the frame")
    axc.legend(loc="upper right", fontsize=6.8, labelspacing=0.45,
               borderpad=0.45, frameon=True, framealpha=0.95,
               facecolor="white", edgecolor=RULE)

    axc.set_xlim(zx0, zx1)
    axc.set_ylim(zy0, zy1)
    axc.set_aspect(aspect)
    frame_off(axc)
    for sp in axc.spines.values():
        sp.set_color(BAD)
    scalebar(axc, 5, "5 km", 0.04, 0.05)
    axc.set_title(
        "The urban core. The frame follows what is built, not what it is "
        "called — Ocean Park is inside it.",
        fontsize=8.5, color=INK, loc="left", pad=6,
    )

    # ---- three detail panels, one box ------------------------------------
    half_km = 0.90
    ky = 110.540
    for col, site in enumerate(sites):
        axd = fig.add_subplot(gs[1, col])
        g = df[df["site"] == site]
        cx, cy = g["longitude"].mean(), g["latitude"].mean()
        draw_roads(axd, roads[site], 0.5)

        no_vid = g[~g["has_video"]]
        vid = g[g["has_video"]]
        axd.scatter(no_vid["longitude"], no_vid["latitude"], s=15,
                    facecolor="white", edgecolor=MUTED, linewidths=0.7,
                    zorder=3)
        axd.scatter(vid["longitude"], vid["latitude"], s=17, marker="o",
                    facecolor=ACCENT, edgecolor="white", linewidths=0.5,
                    zorder=4)

        axd.set_xlim(cx - half_km / kx, cx + half_km / kx)
        axd.set_ylim(cy - half_km / ky, cy + half_km / ky)
        axd.set_aspect(aspect)
        frame_off(axd)
        share = 100 * len(vid) / len(g)
        axd.set_title(f"{site}\n{len(vid)} of {len(g)} with video "
                      f"({share:.0f} %)",
                      fontsize=8, color=INK, pad=5, linespacing=1.45)
        scalebar(axd, 0.5, "500 m", 0.06, 0.06)

    handles = [
        Line2D([], [], marker="o", ls="none", markerfacecolor=ACCENT,
               markeredgecolor="white", ms=6,
               label=f"audio + traffic video — {n_video} points"),
        Line2D([], [], marker="o", ls="none", markerfacecolor="white",
               markeredgecolor=MUTED, ms=6,
               label=f"audio only — {len(df) - n_video} points"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=2, fontsize=8,
               bbox_to_anchor=(0.5, -0.012),
               title="Detail panels: 1.8 × 1.8 km, the same box and scale in "
                     "all three",
               title_fontsize=7.5)
    fig.legends[0].get_title().set_color(MUTED)
    save(fig, "hanoi-sites")

# ---------------------------------------------------------------------------
# 9. Exceedance of the national limit, and how thin the night is
# ---------------------------------------------------------------------------
def fig_exceedance() -> None:
    """QCVN 26:2010 exceedance by site and period, read from the results table.

    The night bars are drawn at the same weight as the day bars and then
    contradicted by their own sample size, printed on each bar. Ten night
    measurements out of 363 is the whole night evidence of this campaign; a
    reader who takes "100 % of nights exceed" away from this figure without
    taking "n = 6" with it has read it wrong, so both are on the bar.
    """
    t = pd.read_csv(ROOT / "results" / "tables" / "hanoi_exceedances.csv")
    sites = list(t["site"].unique())
    periods = ["day", "night"]
    colours = {"day": ACCENT, "night": INK}

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.8, 2.9), width_ratios=[1.25, 1])
    width = 0.36
    xs = np.arange(len(sites))

    for k, period in enumerate(periods):
        vals, ns = [], []
        for site in sites:
            row = t[(t["site"] == site) & (t["period"] == period)]
            vals.append(float(row["pct_depassement"].iloc[0]) if len(row) else np.nan)
            ns.append(int(row["n"].iloc[0]) if len(row) else 0)
        pos = xs + (k - 0.5) * width
        ax1.bar(pos, vals, width=width, color=colours[period], alpha=0.9,
                label=period)
        for x, v, n in zip(pos, vals, ns):
            ax1.text(x, v + 2.5, f"{v:.0f} %", ha="center", va="bottom",
                     fontsize=7.5, color=INK, fontweight="bold")
            ax1.text(x, 2.5, f"n = {n}", ha="center", va="bottom", fontsize=6.8,
                     color="white" if v > 14 else MUTED)

    ax1.set_xticks(xs)
    ax1.set_xticklabels(sites, fontsize=8, color=INK)
    ax1.set_ylabel("measurements over the limit  (%)")
    ax1.set_ylim(0, 118)
    ax1.set_yticks([0, 25, 50, 75, 100])
    ax1.grid(axis="y", color=RULE, lw=0.5, alpha=0.6)
    ax1.set_axisbelow(True)
    ax1.legend(loc="upper left", ncol=2, bbox_to_anchor=(0, 1.14))
    ax1.set_title("Share over QCVN 26:2010 — 70 dB(A) by day, 55 by night",
                  fontsize=9, color=INK, loc="left", pad=20)

    # -- the severity beside the share -------------------------------------
    for k, period in enumerate(periods):
        vals, ns = [], []
        for site in sites:
            row = t[(t["site"] == site) & (t["period"] == period)]
            vals.append(float(row["severite_moy_dB"].iloc[0]) if len(row) else np.nan)
            ns.append(int(row["n"].iloc[0]) if len(row) else 0)
        pos = xs + (k - 0.5) * width
        ax2.bar(pos, vals, width=width, color=colours[period], alpha=0.9)
        for x, v in zip(pos, vals):
            ax2.text(x, v + 0.35, f"+{v:.1f}", ha="center", va="bottom",
                     fontsize=7.5, color=INK, fontweight="bold")

    ax2.set_xticks(xs)
    ax2.set_xticklabels(sites, fontsize=8, color=INK)
    ax2.set_ylabel("mean overshoot  (dB)")
    ax2.set_ylim(0, max(t["severite_moy_dB"]) * 1.30)
    ax2.grid(axis="y", color=RULE, lw=0.5, alpha=0.6)
    ax2.set_axisbelow(True)
    ax2.set_title("By how much, when it is over", fontsize=9, color=INK,
                  loc="left", pad=20)

    fig.text(
        0.5, -0.10,
        "Descriptive only. QCVN 26:2010 regulates a 1 h $L_{Aeq}$; this campaign "
        "measured 25 s $L_{A,25\\mathrm{s}}$, so these bars are placed beside the "
        "limit, not compared to it (docs/metrology.md).",
        ha="center", fontsize=7, color=MUTED,
    )
    save(fig, "exceedance")


# ---------------------------------------------------------------------------
# 10. What the operator said the noise was
# ---------------------------------------------------------------------------
def fig_class_levels(df: pd.DataFrame) -> None:
    """Level by the source class the operator recorded on the form.

    This is the one variable in the dataset that is a human judgement rather
    than a sensor reading, and it is worth a figure because it behaves: the
    ordering it produces is the ordering the physics predicts. It is also the
    clearest picture of how unbalanced the campaign is — two classes carry
    three quarters of it and eight classes have single digits.
    """
    counts = df["class"].value_counts()
    keep = counts[counts >= 5].index.tolist()
    order = (df[df["class"].isin(keep)].groupby("class")["noise_dB"].median()
             .sort_values().index.tolist())

    fig, ax = plt.subplots(figsize=(7.8, 3.2))
    for i, cls in enumerate(order):
        v = df[df["class"] == cls]["noise_dB"]
        q1, med, q3 = v.quantile([0.25, 0.5, 0.75])
        ax.plot([q1, q3], [i, i], color=ACCENT, lw=3.0, solid_capstyle="round",
                alpha=0.55, zorder=2)
        ax.plot([v.min(), v.max()], [i, i], color=ACCENT, lw=0.7, alpha=0.5,
                zorder=1)
        ax.plot([med], [i], "o", ms=5.5, color="white", markeredgecolor=ACCENT,
                markeredgewidth=1.6, zorder=3)
        ax.text(v.max() + 1.2, i, f"$n$ = {len(v)}", va="center", ha="left",
                fontsize=7.5, color=MUTED)

    dropped = int(counts[counts < 5].sum())
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(order, fontsize=8, color=INK)
    ax.set_xlabel(r"$L_{A,25\mathrm{s}}$  (dB)")
    ax.set_xlim(df["noise_dB"].min() - 2, df["noise_dB"].max() + 9)
    ax.grid(axis="x", color=RULE, lw=0.5, alpha=0.6)
    ax.set_axisbelow(True)
    ax.set_title(
        "Level by the source class the operator recorded — median, "
        "interquartile range and full range",
        fontsize=9, color=INK, loc="left", pad=8,
    )
    ax.text(
        0, -0.30,
        f"Classes with fewer than 5 measurements are not drawn "
        f"({dropped} measurements across "
        f"{int((counts < 5).sum())} classes). The class is the operator's "
        "judgement on the form, not a measured quantity.",
        transform=ax.transAxes, fontsize=7, color=MUTED,
    )
    save(fig, "class-levels")

# ---------------------------------------------------------------------------
# 11. The frame the planned campaign draws from
# ---------------------------------------------------------------------------
def fig_campaign_frame(df: pd.DataFrame) -> None:
    """Hanoi's 51 urban wards, the three areas measured so far, and the gap.

    NOTHING ON THIS MAP IS A SITE. The 160 sites of the planned campaign have
    not been drawn, and inventing 160 coordinates to fill a map would commit
    the team to a sample nobody selected. What can be drawn honestly is the
    FRAME -- the 51 phuong the draw will be made across -- and what has
    actually been measured inside it, which is the comparison the plan turns
    on.

    Boundaries: data/processed/hanoi_wards.geojson, from OpenStreetMap under
    the July 2025 reform (scripts/fetch_hanoi_wards.py). Areas are computed in
    UTM 48 N, not from degrees.
    """
    import geopandas as gpd

    wards = gpd.read_file(ROOT / "data" / "processed" / "hanoi_wards.geojson")
    devs = gpd.read_file(ROOT / "data" / "processed"
                         / "hanoi_new_developments.geojson")
    phuong, xa = frame_units(wards, devs)   # in-frame, out-of-frame

    pts = gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
        crs="EPSG:4326",
    )
    hulls = pts.dissolve("site").convex_hull
    measured_km2 = float(hulls.to_crs(32648).area.sum()) / 1e6
    frame_km2 = float(phuong.to_crs(32648).area.sum()) / 1e6

    # Which of the three areas falls inside the frame? Asked rather than
    # assumed. Under the FIRST frame -- the 51 urban phuong -- Ocean Park did
    # not, and half the campaign fell outside it. Under the frame as widened
    # (frame_units: what is built, not what it is called) all three are in, and
    # the assertion below is what keeps that true if the boundaries move.
    in_frame_names = set(phuong["name"])
    located = gpd.sjoin(pts, wards, predicate="within", how="left")
    inside = {
        site: bool(sub["name"].isin(in_frame_names).all())
        for site, sub in located.groupby("site")
    }
    outside_n = int(sum(len(df[df["site"] == s]) for s, ok in inside.items()
                        if not ok))

    # Stacked, not side by side: the frame is 1.7 times wider than it is tall
    # and the scale-up rows carry long labels, so putting them in a column
    # beside the map either squashes the map or runs the labels over it.
    map_h = 7.8 / 1.71
    fig = plt.figure(figsize=(7.8, map_h + 2.5))
    gs = fig.add_gridspec(2, 1, height_ratios=[map_h, 2.0], hspace=0.30)

    # -- the frame ----------------------------------------------------------
    ax = fig.add_subplot(gs[0, 0])
    xa.plot(ax=ax, facecolor="#F7F7F5", edgecolor="white", linewidth=0.3,
            zorder=1)
    phuong.plot(ax=ax, facecolor=ACCENT, alpha=0.15, edgecolor=ACCENT,
                linewidth=0.4, zorder=2)

    for site in hulls.index:
        g = df[df["site"] == site]
        ok = inside[site]
        ax.plot(g["longitude"].mean(), g["latitude"].mean(),
                "o" if ok else "D", ms=7 if ok else 6.5,
                color=BAD, markerfacecolor=BAD if ok else "white",
                markeredgecolor=BAD if not ok else "white",
                markeredgewidth=1.4 if not ok else 1.0, zorder=5)

    for site, ok in inside.items():
        if ok:
            continue
        g = df[df["site"] == site]
        unit = sorted(set(located[located["site"] == site]["name"].dropna()))[0]
        ax.annotate(
            f"{site} sits in {unit},\na rural commune — "
            f"{len(g)} of the {len(df)} measurements\n"
            "are OUTSIDE the frame drawn from",
            xy=(g["longitude"].mean(), g["latitude"].mean()),
            xytext=(-12, -46), textcoords="offset points",
            ha="right", va="top", fontsize=7, color=BAD, zorder=6,
            linespacing=1.4,
            arrowprops=dict(arrowstyle="-", color=BAD, lw=0.7,
                            shrinkA=0, shrinkB=5),
        )

    ax.plot([], [], "o", ms=6, color=BAD, markeredgecolor="white",
            markeredgewidth=1.0,
            label=f"measured — {len(df) - outside_n} points, all inside the frame"
            if not outside_n else
            f"measured, inside the frame — {len(df) - outside_n} points")
    if outside_n:
        ax.plot([], [], "D", ms=6, color="white", markeredgecolor=BAD,
                markeredgewidth=1.4,
                label=f"measured, OUTSIDE the frame — {outside_n} points")
    ax.plot([], [], "s", ms=8, color=ACCENT, alpha=0.4,
            label=f"the frame — {len(phuong)} units, {frame_km2:.0f} km$^2$")
    ax.plot([], [], "s", ms=8, color="#EDEDEA",
            label=f"{len(xa)} rural units — outside the frame")

    x0, y0, x1, y1 = phuong.total_bounds
    px, py = (x1 - x0) * 0.03, (y1 - y0) * 0.05
    ax.set_xlim(x0 - px, x1 + px)
    ax.set_ylim(y0 - py, y1 + py)
    ax.legend(loc="lower left", fontsize=7, labelspacing=0.5, borderpad=0.5,
              frameon=True, framealpha=0.95, facecolor="white",
              edgecolor=RULE)
    ax.set_aspect(1 / np.cos(np.radians(float(df["latitude"].mean()))))
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_color(RULE)
    ax.set_title(
        "Where the 160 sites will be drawn from — not where they are. "
        "No site has been selected.",
        fontsize=9, color=INK, loc="left", pad=8,
    )
    assert not outside_n, (
        "a measured area falls outside the sampling frame; the figure's "
        "annotation branch was removed when the frame was widened"
    )

    # -- the scale-up, on the numbers --------------------------------------
    ax2 = fig.add_subplot(gs[1, 0])
    night_now = int(((df["hour"] >= 21) | (df["hour"] < 6)).sum())
    rows = [
        ("Area covered  (km$^2$)", measured_km2, frame_km2),
        ("Measurement sessions", len(df), 160 * 4 * 3),
        ("Night sessions", night_now, 160 * 1 * 3),
        ("Distinct sites", 3, 160),
    ]
    ys = np.arange(len(rows))[::-1]
    h = 0.34
    for y, (label, now, plan) in zip(ys, rows):
        ax2.barh(y + h / 2, now, height=h, color=MUTED, alpha=0.85)
        ax2.barh(y - h / 2, plan, height=h, color=ACCENT, alpha=0.85)
        for value, offset in ((now, h / 2), (plan, -h / 2)):
            text = (f"{value:.1f}" if 0 < value < 10 and value % 1
                    else f"{value:,.0f}".replace(",", " "))
            ax2.text(value * 1.18, y + offset, text, va="center", ha="left",
                     fontsize=7.5, color=INK)

    ax2.set_xscale("log")
    ax2.set_yticks(ys)
    ax2.set_yticklabels([r[0] for r in rows], fontsize=8, color=INK)
    ax2.set_xlim(0.9, 2.2e4)
    ax2.set_ylim(-0.6, len(rows) - 0.4)
    ax2.set_xticks([1, 10, 100, 1000, 10000])
    ax2.set_xticklabels(["1", "10", "100", "1 000", "10 000"])
    ax2.grid(axis="x", color=RULE, lw=0.5, alpha=0.6)
    ax2.set_axisbelow(True)
    ax2.spines["left"].set_visible(False)
    ax2.tick_params(axis="y", length=0)
    ax2.legend(
        handles=[Patch(color=MUTED, alpha=0.85, label="this campaign"),
                 Patch(color=ACCENT, alpha=0.85, label="planned campaign")],
        loc="lower right", fontsize=7.5, ncol=2,
    )
    ax2.set_title(
        f"Log scale. On area alone the step up is a factor of "
        f"{frame_km2 / measured_km2:.0f}; on night measurements, "
        f"{160 * 3 / night_now:.0f}.",
        fontsize=9, color=INK, loc="left", pad=8,
    )

    save(fig, "campaign-frame")

def main() -> None:
    style()
    m = metrics()
    df = measurements()
    print("presentation figures:")
    fig_ranking_inversion(m)
    fig_forest_bloo(m)
    fig_campaign(df, m)
    fig_discontinuity(df)
    fig_feature_importance(m)
    fig_ceiling(df, m)
    fig_map(m)
    fig_sites_map(df)
    fig_exceedance()
    fig_class_levels(df)
    fig_campaign_frame(df)


if __name__ == "__main__":
    main()

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
BAD = "#C62828"
WARN = "#EF6C00"
MUTED = "#6E6E6E"
RULE = "#D8D8D4"

# QCVN 26:2010 reading bands. Descriptive only — the same use the published map
# and the app make of them, and never a compliance statement. See
# docs/metrology.md: our quantity is not the quantity the standard regulates.
BANDS = [
    (-np.inf, 55, "#2E7D32", "< 55"),
    (55, 60, "#7CB342", "55 – 60"),
    (60, 65, "#C0CA33", "60 – 65"),
    (65, 70, "#F9A825", "65 – 70"),
    (70, 75, "#EF6C00", "70 – 75"),
    (75, 80, "#D84315", "75 – 80"),
    (80, np.inf, "#B71C1C", "> 80"),
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
            va="center", ha="left", fontsize=8, color=colour,
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
                    color=colour)

    ax.axvline(0, color=RULE, lw=0.8)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(
        [labels[k] for k in order], fontsize=8,
        color=INK,
    )
    for tick, key in zip(ax.get_yticklabels(), order):
        if key == m["meta"]["delivered_model"]:
            tick.set_fontweight("bold")
            tick.set_color(GOOD)
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
# 6. The map, in English
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
    fig_map(m)


if __name__ == "__main__":
    main()

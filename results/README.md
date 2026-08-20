# results/

Everything a human looks at. All of it is regenerable with `make results`, and
all of it derives from `models/metrics.json` and the published datasets.

| Folder | What |
|---|---|
| `figures/` | The five field analyses, the simulation validation, and `sunbird/` for the Uganda reproduction |

> **Not everything here is reproducible.** `figures/sunbird/` holds eight frozen images
> that **never had a scripted producer** — they come from notebook cells — and whose
> input data is absent from the repository. Two causes, and the first would outlive
> the second being fixed. See
> [`figures/sunbird/NOT-REGENERABLE.md`](figures/sunbird/NOT-REGENERABLE.md). One of them,
> `pred_vs_real.png`, carries "R² = 0.250" for the **Uganda** reproduction, which is easily
> mistaken for the Hanoi delivered model's 0.246. The two are unrelated.
| `maps/` | `hanoi_noise_map.csv` (5 587 cells × 17 hours) and the interactive field-point map |
| `tables/` | Exceedances, simulation validation, literature anchoring |
| `report/` | `report.tex` + `report.pdf` (typeset LaTeX) and the static `dashboard/` |

**The map covers the sampled envelope only** — the three measured sites plus a
400 m margin, at 40 m resolution. It must never be extended to a district where
nothing was measured; that mistake was made once and retracted, see
[`../docs/archive/bach-khoa/README.md`](../docs/archive/bach-khoa/README.md).
`tests/test_grid_extent.py` enforces it.

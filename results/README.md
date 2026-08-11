# results/

Everything a human looks at. All of it is regenerable with `make results`, and
all of it derives from `models/metrics.json` and the published datasets.

| Folder | What |
|---|---|
| `figures/` | The five field analyses, the simulation validation, and `sunbird/` for the Uganda reproduction |
| `maps/` | `hanoi_noise_map.csv` (5 587 cells × 17 hours) and the interactive field-point map |
| `tables/` | Exceedances, simulation validation, literature anchoring |
| `report/` | `report.pdf` (8 pages) and the static `dashboard/` |

**The map covers the sampled envelope only** — the three measured sites plus a
400 m margin, at 40 m resolution. It must never be extended to a district where
nothing was measured; that mistake was made once and retracted, see
[`../docs/archive/bach-khoa/README.md`](../docs/archive/bach-khoa/README.md).
`tests/test_grid_extent.py` enforces it.

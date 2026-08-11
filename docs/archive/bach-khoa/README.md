# Retracted artefacts — the "Bach Khoa" grid

These files were produced by the old cells of notebook 08 and by notebook 09.
**They must not be redistributed.** The payload itself was removed from `HEAD` in
August 2026; this note is kept, because what was withdrawn and why is worth more
than the files it describes. Everything remains reachable in git history.

## Why they were retracted

They cover a disc of 1 500 m around **Bach Khoa** (lat 20.992–21.019,
lon 105.829–105.858) — a district where **no field measurement was ever taken**.
The model that produced them is trained on Ocean Park, Hoan Kiem and Vinh Tuy, and
its leave-one-site-out score is negative on two of those three sites: it does not
generalise to an urban typology it has not seen. Publishing a noise map over Bach
Khoa was therefore extrapolation outside the model's domain of applicability.

| File | Replaced by |
|---|---|
| `hanoi_heatmap.html` | to be regenerated over the sampled envelope (below) |
| `hanoi_noise_map.geojson` | `results/maps/hanoi_noise_map.csv` (3 zones × 17 hours) |
| `hanoi_osm.png` | — (a figure of the Bach Khoa area, now moot) |

## What replaces them

`scripts/07_export_gama_inputs.py` produces the map **over the envelope actually
sampled**: the three measurement sites plus a 400 m margin, a 40 m grid, one
column per hour (`h5`…`h21`).

```bash
python3 scripts/07_export_gama_inputs.py     # or: make results
```

Outputs: `results/maps/hanoi_noise_map.csv` (5 587 cells × 17 hours),
`simulation/gama/inputs/noise_map.csv` (flat format for GAMA, reference hour
17:00), and `simulation/gama/inputs/{zone}_noise.shp`.

## What prevents a recurrence

`tests/test_grid_extent.py` fails if any published cell falls outside the sampled
envelope plus its margin, or inside the Bach Khoa extent above. The export script
is now the **single** producer of the GAMA inputs; having two producers is how
this grid survived as long as it did.

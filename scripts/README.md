# scripts/

Command-line entry points, numbered in execution order. The numbering is the
pipeline documentation: `ls` tells you what runs when.

| Script | Reads | Writes |
|---|---|---|
| `01_prepare_field_data.py` | raw Kobo export | `data/processed/measurements.csv` |
| `02_count_vehicles.py` | the 147 videos | `data/processed/vehicle_counts.csv` |
| `03_build_features.py` | measurements + OSM extract | `data/interim/features.parquet` |
| `04_evaluate_models.py` | features | `models/metrics.json`, `model_comparison.md`, the delivered model |
| `05_calibrate_emissions.py` | counts + measurements | `simulation/gama/inputs/emission_calibration.csv` |
| `06_anchor_literature.py` | measurements | `results/tables/literature_anchoring.*` |
| `07_export_gama_inputs.py` | features + delivered model | `simulation/gama/inputs/`, `results/maps/` |
| `08_validate_simulation.py` | grid + measurements | `results/tables/validation_simulation.*` |
| `09_build_field_map.py` | measurements | `results/maps/hanoi_field_points.html` |
| `10_build_report.py` | `models/metrics.json` | `results/report/{numbers,tab_*}.tex` -> `report.pdf` |
| `11_build_dashboard.py` | metrics + map + counts | `results/report/dashboard/` |
| `12_presentation_figures.py` | metrics + measurements + map | `presentation/figures/*.pdf` |

`01` and `02` need inputs that are not published; the chain from `03` onwards runs
from the versioned datasets alone. Use `make` rather than calling these by hand.

`12` renders the slide deck's figures. It is a renderer, not a source: it types no
number of its own, and its labels are English because `results/figures/` is French
and partly not regenerable. `make slides` runs it and then builds the deck.

`experiments/` holds one-shot studies that are **not** part of `make all`.
`barcelona_transfer.py` is a closed dead end and says so in its own header.

Shared logic lives in `src/noise_hanoi/`, not here. A script should read its
inputs, call the package, and write its outputs.

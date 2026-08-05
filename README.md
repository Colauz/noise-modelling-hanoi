# Noise Modelling Hanoi

Smartphone-based urban noise mapping for Hanoi. We reproduce the methodology of
[Nsumba et al. 2026 (Scientific Data)](https://doi.org/10.1038/s41597-026-06658-w) - the
[Sunbird Urban Noise Uganda 61K dataset](https://huggingface.co/datasets/Sunbird/urban-noise-uganda-61k) -
then apply it to Hanoi with our own field campaign (363 measurements, 3 districts),
a LightGBM model trained directly on our data, and a GAMA agent-based simulation.

**Key results.** Three of them are negative, and they are the most transferable:
1. **A three-parameter physical model beats every learned model we built.** The delivered
   model is a line-source attenuation law (`E = A_hw/d_hw + A_res/d_res + B`), R² = **0.246**
   under buffered leave-one-out and **0.222** under leave-one-site-out — ahead of a
   six-variable LightGBM (0.137 / 0.029) and of the physics+ML **hybrid** we built to improve
   on it (0.123 / 0.035). The learned residual gains ΔR² +0.140 under the permissive 600 m
   block split and loses −0.123 / −0.187 under the two strict ones: the ranking of the seven
   models inverts almost exactly between protocols. Morphology aggregated over 300 m adds no
   measurable value. See `paper/sections/negative_results.md` §5.z.
2. **Cross-city transfer fails.** A morphology→noise model pretrained on Uganda gives R² < 0
   on Hanoi even with convention-invariant features. Local measurement is a prerequisite,
   not a refinement.
3. **Per-frame vehicle density carries no acoustic signal.** Non-negative energy regression
   on 147 matched videos returns three zero coefficients: density is not flow, and speed is
   not observable in a frame count. V2 replaces density with **real flow** (YOLOv8 +
   ByteTrack line-crossing counts, veh/min) and re-tests the emission fit on the physically
   correct formulation, energy per *pass*.

Full table with baselines, ablation and bootstrap CIs under all three protocols:
`outputs/models/model_comparison.md`.

**Interactive dashboard**: `./run_dashboard.sh` builds `outputs/dashboard/index.html` (map,
model comparison, traffic flow, link to the report, GAMA instructions) and opens it.

> ⚠️ **Measurement status.** Our target is a 20–30 s A-weighted level from consumer
> smartphones (`L_A,25s`), not a certified `L_Aeq`. The three phones are cross-calibrated
> **against each other, never against a reference instrument**: contrasts between places and
> hours are supported, absolute levels are indicative. No compliance claim is made anywhere.
> See `paper/sections/metrology.md`.

> ⚠️ **Superseded figure.** The "R² 0.45 under honest spatial cross-validation" advertised
> until July 2026 came from a `GroupKFold` grouped on ~110 m cells, smaller than the 300 m
> radius over which the features are aggregated. It leaked. See `audit_noise_modeling.md`
> and `scripts/evaluate_models.py`.

## Repository layout

| Folder | Content |
|---|---|
| `notebooks/` | The project spine, numbered in execution order (see below) |
| `scripts/` | Reusable pipeline: `prepare_field_data.py`, `evaluate_models.py`, `export_gama_zones.py`, `literature_anchoring.py`, `build_field_map.py`, `build_report.py` |
| `scripts/experiments/` | One-shot studies: `train_large.py` (Uganda 59K), `train_v2_invariant.py` (v2 features), `barcelona_transfer.py` (Barcelona diagnostics) |
| `field/` | Field protocol (README) + Kobo/ODK forms (noise survey v2, construction-sites log) |
| `paper/` | Q1 paper material: `bibliography.bib`, `sections/` (metrology, negative results), `figures/`, `references/` |
| `gama/` | Simulation plan (`PLAN.md`) and GAMA model |
| `data/` | **Not in git.** `raw/{barcelona,hanoi}` + `processed/{uganda,barcelona,hanoi}`; field videos in `raw/hanoi/videos/` (Sunbird data is auto-downloaded from HuggingFace into `cache/`) |
| `outputs/` | `report.pdf`, `models/metrics.json` + `model_comparison.md`, `sunbird/`, `hanoi/` (maps + analyses), `gama_inputs/` (shapefiles), `deprecated/` (withdrawn Bach Khoa artefacts) |

## Notebooks

| Notebook | What it does |
|---|---|
| `01_explore_sunbird` | Load the Uganda dataset, distributions |
| `02_clean_sunbird` | Dedup, GPS accuracy filter, dB sanity → `sunbird_clean.csv` |
| `03_audio_qc` | Audio quality control (silence, band energy, MD5 dedup) |
| `04_morphology_features` | Morphology features in a 300 m radius (OSM) |
| `05_reproduce_figures` | Reproduce the paper's figures 8-10 |
| `06_train_surrogate_model` | LightGBM morphology → dB on Uganda |
| `07_hanoi_field_data` | **Hanoi**: clean field data (via `scripts/prepare_field_data.py`), 5 analyses (hourly, day-of-week, sources, QCVN, weather), interactive map |
| `08_predict_hanoi` | **Hanoi**: OSM features, evaluation via `scripts/evaluate_models.py`, transfer comparison, final model |
| `09_export_gama` | ⚠️ neutralised — superseded by `scripts/export_gama_zones.py` |

## Pipeline after each Kobo export

```bash
# 1. drop the new CSV in data/raw/hanoi/ (archive the old one in data/raw/hanoi/old/)
python3 scripts/prepare_field_data.py        # clean -> measurements.csv
# 2. notebooks 07 (EDA + map) then 08 (OSM features, once, to build the caches)
python3 -m nbconvert --to notebook --execute --inplace notebooks/07_hanoi_field_data.ipynb
python3 -m nbconvert --to notebook --execute --inplace notebooks/08_predict_hanoi.ipynb
# 3. evaluation, anchoring, map, simulation inputs, report
python3 scripts/evaluate_models.py           # -> outputs/models/metrics.json (+ .md)
python3 scripts/literature_anchoring.py      # -> outputs/hanoi/literature_anchoring.md
python3 scripts/export_gama_zones.py         # -> outputs/gama_inputs/ + hanoi_noise_map.csv
python3 scripts/validate_simulation.py       # -> in-sample check of the chain
python3 scripts/build_report.py              # -> outputs/report.pdf (reads metrics.json)
```

No metric is ever copied by hand: `build_report.py` reads `outputs/models/metrics.json` and
refuses to run without it.

Interactive map of field points: `outputs/hanoi/hanoi_field_points.html`.

## Setup

```bash
pip install -r requirements.txt
```

Sunbird is gated: accept the terms on its HuggingFace page, create a Read token at
https://huggingface.co/settings/tokens, and paste it in the first cell of notebooks 01-05
(never commit a real token).

## Field protocol (summary)

ODK Collect → KoboToolbox; 20-30 s spot measurements with ≥10 s audio; phones at ≈1.2 m,
varied distances from the road; 3 collectors cross-calibrated **against each other only**;
05:00-23:00 with rush-hour emphasis; traffic videos timestamped to match measurements.
Details in `field/`. **The campaign is closed** — the project has pivoted to a methodological
study on the data in hand (see `audit_noise_modeling.md`).

## Paper draft

https://www.overleaf.com/project/6a1d529010bdbac6b41da01e

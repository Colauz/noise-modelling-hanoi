# Noise Modelling Hanoi

Smartphone-based urban noise mapping for Hanoi. We reproduce the methodology of
[Nsumba et al. 2026 (Scientific Data)](https://doi.org/10.1038/s41597-026-06658-w) — the
[Sunbird Urban Noise Uganda 61K dataset](https://huggingface.co/datasets/Sunbird/urban-noise-uganda-61k) —
then apply it to Hanoi with our own field campaign (323 measurements, 3 districts),
a LightGBM model trained directly on our data, and (later) a GAMA simulation.

**Key result so far**: cross-city transfer (Uganda → Hanoi) fails (R² < 0); training
directly on our measurements works — **R² 0.45 · r 0.68 · MAE 4.4 dB** under honest
spatial cross-validation. See `outputs/report.pdf` and `ROADMAP.md`.

## Repository layout

| Folder | Content |
|---|---|
| `notebooks/` | The project spine, numbered in execution order (see below) |
| `scripts/` | Reusable pipeline: `prepare_field_data.py`, `build_field_map.py`, `build_report.py` |
| `scripts/experiments/` | One-shot studies: `train_large.py` (Uganda 59K), `train_v2_invariant.py` (v2 features), `barcelona_transfer.py` (Barcelona diagnostics) |
| `field/` | Field protocol (README) + Kobo/ODK forms (noise survey v2, construction-sites log) |
| `paper/` | Q1 paper material: `figures/`, `references/` (incl. the Sunbird paper PDF) |
| `gama/` | Simulation plan (`PLAN.md`) and GAMA model |
| `data/` | **Not in git.** `raw/{barcelona,hanoi}` + `processed/{uganda,barcelona,hanoi}`; field videos in `raw/hanoi/videos/` (Sunbird data is auto-downloaded from HuggingFace into `cache/`) |
| `outputs/` | `report.pdf`, `sunbird/` (reproduction figures), `hanoi/` (maps + analyses), `gama_inputs/` (shapefiles), `models/` |

## Notebooks

| Notebook | What it does |
|---|---|
| `01_explore_sunbird` | Load the Uganda dataset, distributions |
| `02_clean_sunbird` | Dedup, GPS accuracy filter, dB sanity → `sunbird_clean.csv` |
| `03_audio_qc` | Audio quality control (silence, band energy, MD5 dedup) |
| `04_morphology_features` | Morphology features in a 300 m radius (OSM) |
| `05_reproduce_figures` | Reproduce the paper's figures 8-10 |
| `06_train_surrogate_model` | LightGBM morphology → dB on Uganda |
| `07_hanoi_field_data` | **Hanoi**: clean field data (via `scripts/prepare_field_data.py`), 4 analyses (hourly, day-of-week, sources, QCVN exceedances), interactive map |
| `08_predict_hanoi` | **Hanoi**: direct training + honest spatial CV, transfer comparison, predicted noise grid |
| `09_export_gama` | Shapefiles + noise grid CSV for GAMA |

## Pipeline after each Kobo export

```bash
# 1. drop the new CSV in data/raw/hanoi/ (archive the old one in data/raw/hanoi/old/)
python3 scripts/prepare_field_data.py        # clean -> measurements.csv
# 2. run notebooks 07 then 08 (Run All, or:)
python3 -m nbconvert --to notebook --execute --inplace notebooks/07_hanoi_field_data.ipynb
python3 -m nbconvert --to notebook --execute --inplace notebooks/08_predict_hanoi.ipynb
# 3. copy the notebook-08 scores into MODEL/PERSITE at the top of scripts/build_report.py, then:
python3 scripts/build_report.py              # -> outputs/report.pdf
```

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
varied distances from the road; 3 cross-calibrated collectors; 05:00-23:00 with rush-hour
emphasis; traffic videos timestamped to match measurements. Details in `field/`.

## Paper draft

https://www.overleaf.com/project/6a1d529010bdbac6b41da01e

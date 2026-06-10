# Noise Modelling Hanoi

Smartphone-based urban noise mapping for Hanoi, reproducing the methodology of
[Nsumba et al. 2026 (Scientific Data)](https://doi.org/10.1038/s41597-026-06658-w) — the
[Sunbird Urban Noise Uganda 61K dataset](https://huggingface.co/datasets/Sunbird/urban-noise-uganda-61k) —
then transferring it to Hanoi with our own field measurements, a LightGBM surrogate model,
and a GAMA simulation.

## Pipeline (mirrors the paper)

| Notebook | Paper section reproduced | What it does |
|---|---|---|
| `01_explore_sunbird` | Data Records | Load dataset, distribution of noise_measurement |
| `02_clean_sunbird` | Post-processing & privacy | Dedup, GPS accuracy filter, dB sanity → `sunbird_clean.csv` |
| `03_audio_qc` | Technical Validation | Decode audio, RMS silence check, band energy (0-250 Hz / 250-2k / 2-8k), MD5 dedup |
| `04_morphology_features` | Urban morphology metrics | Building density (R=300 m, /πR²), road density, intersection count, dist-to-road |
| `05_reproduce_figures` | Usage Notes (Figs. 8-10) | Mean SPL map, hourly median+IQR cycle, day vs night |
| `06_train_surrogate_model` | (our extension) | LightGBM: morphology features → dB |
| `07_predict_hanoi` | (our extension) | OSMnx Hanoi grid, fine-tune with field data, city-wide prediction |
| `08_export_gama` | (our extension) | Shapefiles + CSV for GAMA |
| `gama/hanoi_noise.gaml` | (our extension) | Scenario simulation |
| `00_hanoi_map_preview` | — | Quick OSMnx/folium demo of study area |

## Field protocol (Hanoi — same as the paper)

- **App**: ODK Collect (the exact tool used in the paper) + audio recorder, Android
- **Calibration**: cross-calibrate phones against each other; cite paper Table 1 (smartphone vs Casella CEL-633A1, error < 2 dB over 35-120 dB)
- **Per sample**: ≥10 s audio + dB + GPS + manual noise category + timestamp
- **Strategy**: walk the site, one sample every ~30 s at varying distances from the road

### Study sites

| Site | Noise type |
|---|---|
| Hoan Kiem lake | Transportation |
| Vinh Tuy area | Transportation |
| Ocean Park | Construction |

## Setup

```bash
pip install -r requirements.txt
```

Sunbird is gated: accept the terms on its HuggingFace page, create a Read token at
https://huggingface.co/settings/tokens, and paste it in the first cell of each notebook
(never commit a real token).

## Paper limitations we address / inherit

- Their limitations: night-time coverage (phone theft risk), rain disruptions, duplicate submissions
- Our additions: ML surrogate model + transfer to a new city (their suggested downstream use)
- Omitted from their method: DEM slope (Hanoi is flat), Class 1 reference meter (we cross-calibrate phones instead)

## Survey
https://www.overleaf.com/project/6a1d529010bdbac6b41da01e

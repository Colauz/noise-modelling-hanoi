# Superseded validation — 5 August 2026

**These two files validate a grid that no longer exists in this repository.**
Kept as the record; do not cite them.

## What happened

`validation_simulation.{csv,png}` were last regenerated in commit `b8521f3`. The
grid they validate, `noise_points.dbf`, was regenerated **afterwards**, in
`687e387`, when the three-parameter physical kernel replaced the hybrid as the
delivered model. The derived artefact never followed its input, and nothing in the
repository expressed that dependency. It was found on 2026-08-11 by re-running the
script during an unrelated label translation.

## The two sets of figures

| | Superseded (V1 hybrid grid) | Current (delivered physical kernel) |
|---|---:|---:|
| bias | −0.58 dB | −1.24 dB |
| MAE | 3.79 dB | 5.30 dB |
| RMSE | 5.03 dB | 6.49 dB |
| r | 0.715 | 0.444 |
| R² in-sample | 0.499 | 0.166 |
| within ±5 dB | 72.8 % | 53.1 % |
| σ simulated | 5.57 dB | 3.14 dB |

## Why the current numbers are worse, and still the right ones

The degradation is the **bias-variance trade-off, not a regression**. The
three-parameter physical kernel fits the training points less closely than a
LightGBM did (R² 0.166 against 0.499) and **generalises better** under buffered
leave-one-out (0.246 against 0.137). The map is flatter (σ 3.14 against 5.57)
because the model is less flexible.

The superseded numbers were more flattering and described a model that is not
delivered. See [`../../methodology.md`](../../methodology.md) section 5.3.

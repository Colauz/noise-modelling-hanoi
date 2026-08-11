# models/

Fitted artefacts and the metrics that qualify them, kept together because the
project's rule is that no published number is ever copied by hand.

| File | What |
|---|---|
| `metrics.json` | **Single source of truth for every published number.** `10_build_report.py` refuses to run without it |
| `model_comparison.md` | 7 models × 3 CV protocols, with bootstrap confidence intervals |
| `hybrid_physical.json` | **The delivered model**: the three-parameter kernel `E = A_hw/d_hw + A_res/d_res + B` |
| `hybrid_residual_lgbm.txt` | Learned residual booster. Written always, applied only if `apply_residual` is true |
| `surrogate_lgbm_hanoi_direct.txt` | LightGBM trained directly on the Hanoi points |
| `surrogate_lgbm_large.txt` | Uganda 59K surrogate, used for the transfer experiment |
| `surrogate_lgbm_v2_uganda.txt` | Convention-invariant v2 of the above |

**The delivered model is chosen by code, not by hand.** `04_evaluate_models.py`
takes the best R² under the reference protocol (buffered LOO 300 m) among six
candidates fixed in advance, writes `meta.delivered_model` into `metrics.json`,
and `07_export_gama_inputs.py` reads the `apply_residual` flag. The published map
cannot silently inherit a model that only wins a permissive split.

As of August 2026 the winner is the **three-parameter physical kernel**, ahead of
every learned model including the physics+ML hybrid the team had itself
recommended. The residual is written but **not** applied.

All boosters are in LightGBM's portable text format. Do not reintroduce pickles:
a joblib pickle only reloads under the exact scikit-learn and LightGBM versions
it was written with.

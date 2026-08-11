# src/

`noise_hanoi`, the importable core. Install with `pip install -e .` (or `make setup`).

| Module | What |
|---|---|
| `config.py` | Every path and every model parameter, stated once |
| `features.py` | OSM morphology in a 300 m radius, and the feature sets |

Before this package existed, thirteen scripts each recomputed the project root
and spelled out their own path literals, and `04_evaluate_models.py` reached
`morphology()` by putting `scripts/` on `sys.path` and importing a sibling file by
name. Numbering the scripts broke that outright — a Python module name cannot
start with a digit — which is the short version of why this package exists.

Modules still to extract, in the order they would pay off: `validation.py` (the
three CV protocols and the block bootstrap, currently inside
`04_evaluate_models.py`), `physics.py` (the delivered kernel), `grid.py`,
`vision.py`, `field.py`.

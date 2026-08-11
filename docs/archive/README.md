# Archive — superseded and withdrawn work

Nothing here should be republished. Each item is kept because a research record
that shows what it withdrew, and why, is worth more than one that shows only its
wins. All of it remains reachable in git history.

## `noise-map-2026-07-31-superseded.png`

GAMA screenshot taken on 2026-07-31, **before** the methodological pivot of
2026-08-05.

**What is invalid.** Its legend reads *"Fond : modele ML R2 0.45"*. That R² came
from a `GroupKFold` grouped on ~110 m cells, smaller than the 300 m radius over
which the features are aggregated: held-out points shared their support with
training points, so the score is optimistic. It was withdrawn. The legend also
carries a WHO threshold (*"OMS 53 dB"*), whereas WHO `L_den`/`L_night` values were
removed from the whole project on 2026-08-05 — they describe a long-term
indicator this campaign never measured.

**What replaces it.** `results/figures/noise-map-oceanpark-17h.png`, produced by
the corrected model. Its legend cites `metrics.json` rather than a hardcoded
figure, and it references QCVN day/night bands only. The honest score under the
reference protocol is **R² = 0.246**, in `models/model_comparison.md`.

## `slides-2026-07-31.html`

Project-update deck of 2026-07-31, **also pre-pivot**.

**What is invalid.** It presents the same withdrawn **R² = 0.45** as a headline
result, and predates all three negative results that are now the contribution:
the three-parameter physical kernel beating every learned model, the failure of
cross-city transfer, and the absence of an acoustic signal in vehicle density.

**What replaces it.** The deck in `presentation/`, and
[`../negative-results.md`](../negative-results.md).

## `bach-khoa/`

Noise grid published over Bach Khoa, a district where **no measurement was ever
taken**, by a model whose leave-one-site-out score is negative on two of the
three sites it was trained on. The payload was removed; its README, which records
the extent and the reason for the retraction, is kept. `tests/test_grid_extent.py`
now fails if any published cell falls in that extent again.

## `09_export_gama.ipynb`

Neutralised notebook, superseded by `scripts/07_export_gama_inputs.py`. It was the
second producer of the GAMA inputs, and having two producers is how the Bach Khoa
grid survived as long as it did.

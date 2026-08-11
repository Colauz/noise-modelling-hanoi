# These eight figures cannot be regenerated

**Status: frozen artefacts. Do not treat them as reproducible output.**

They were produced by `notebooks/01`–`06`, the Uganda / Sunbird reproduction chain.
That chain expects `data/processed/uganda/*`, which is **not in this repository and
does not exist on a fresh machine**. Nobody can rebuild these images today, including
the people who made them. See `docs/handover.md`, debt 3.

They are kept because the Uganda reproduction is what the cross-city transfer result
(one of the study's three negative results) rests on, and deleting the only visual
record of it would leave that result unillustrated.

| File | Produced by | Language |
|---|---|---|
| `audio_qc.png` | notebook 03 | French labels |
| `feature_importance.png` | notebook 06 | French labels |
| `fig9_hourly_cycle.png`, `fig10_day_night.png` | notebook 05 | French labels |
| `morphology_vs_spl.png` | notebook 04 | French labels |
| `pred_vs_real.png` | notebook 06 | French labels |
| `reproduce_sunbird.png` | notebook 02 | French labels |
| `sunbird_distribution.png` | notebook 01 | French labels |

## Read `pred_vs_real.png` with care

Its title reads **"Surrogate model — R² = 0.250"**. That figure is the **Uganda**
reproduction, on the Sunbird `small` config (1 000 rows, **random split**) — not our
Hanoi result and not our reference protocol.

It sits three thousandths away from **R² = 0.246**, the score of the model actually
delivered for Hanoi under buffered leave-one-out. **The two are unrelated.** Anyone
citing a figure of ~0.25 must say which one they mean; see
`models/model_comparison.md` for the Hanoi numbers.

## To make them regenerable

Restore the Uganda chain: re-download the Sunbird dataset (gated, see
`docs/data-sources.md`), rebuild `data/processed/uganda/`, and re-run notebooks 01–06
after translating their labels. That is a project in itself, not a cleanup task.

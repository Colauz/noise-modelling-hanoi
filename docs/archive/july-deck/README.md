# The July deck

`Hanoi_Urban_Noise_Modelling.pptx` — the project update presented in July 2026,
before the August audit. Eleven slides, each a full-page image.

It is kept here for the same reason everything else in `docs/archive/` is kept:
**retracted work is archived with its reason, never silently deleted.** It is also
the source of one thing still in use — see below.

## What is still current: the research question

Slide 2 states it, and the end-of-internship deck
([`presentation/main.tex`](../../../presentation/main.tex)) quotes it **verbatim**:

> **Research question:** can urban noise be attributed to the form of the city and
> to the type of vehicle passing through it? Models validated on car-centric
> European cities are unproven on motorcycle-heavy soundscapes.

It was not rewritten after the answer came back, and that is deliberate. The
answer is **no on both halves** — morphology adds nothing the strict protocols can
see, and the video chain that was meant to measure vehicle type does not work. A
question kept after it defeats you is worth more than one adjusted to fit the
result.

## What was withdrawn, and must not be quoted from it

| In the July deck | Status |
|---|---|
| Slide 1: *"363 field measurements · **model validated**"* | **Withdrawn.** No model was validated. The R² of 0.45 came from a cross-validation grouped on 110 m cells while the features aggregate over 300 m — it leaked. See [`../../negative-results.md`](../../negative-results.md). |
| Slide 2: *"**53 dB** — WHO ceiling for road-traffic noise"* | **Withdrawn in full.** The WHO `L_den` 53 / `L_night` 45 values are annual averages with evening and night penalties. Our quantity is a 25 s sample. The comparison is a category error, not a rounding one — [`../../metrology.md`](../../metrology.md). |
| Slide 4: *"**39 %** exceed the QCVN daytime limit (70 dB)"* | **Withdrawn as phrased.** QCVN 26:2010 regulates a quantity we do not measure, with an instrument class we did not have. Exceedance is now reported as a descriptive statistic of the sample, with a sensitivity analysis on the calibration bias, and never as non-compliance. |
| Slide 1: affiliation *"Center for Environmental Intelligence · VinUniversity"* | **Unresolved**, not withdrawn. The current deck says "COSMOS Lab, VinUniversity". Someone should settle which is correct — `docs/handover.md` §6 lists it as an open item. |

The map on slide 4 also carries a QCVN day-limit legend and predates the envelope
rule; the current map is drawn from `results/maps/hanoi_noise_map.csv` by
`scripts/12_presentation_figures.py`.

## Why the numbers changed

Nothing here was a mistake of arithmetic. The July deck reported what the pipeline
said at the time; the pipeline was wrong about how it was validating itself. The
August audit is written up in [`../../audit/`](../../audit/), and the corrections
it forced are in [`../../project-timeline.md`](../../project-timeline.md).

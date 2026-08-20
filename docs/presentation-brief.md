# Brief for the final presentation

Written 21 August 2026, for whoever finishes the slides. Everything below is a
figure that has been checked against the repository or produced by running
something in it. **Nothing here should be rounded, reworded upward, or filled in
from memory** — the whole argument of this work is that it reports what it
measured, and a slide that overstates by half a decibel undoes that in front of
the one person in the room who checks.

Where a number is not in this brief, it is in `models/metrics.json`, which is the
single source of truth. `scripts/12_presentation_figures.py` reads from there;
keep it that way.

---

## 1. The story that holds

Not "we built an app". The app is the instrument, not the finding.

> **What a smartphone protocol can and cannot establish about urban noise.**
> Three months, 363 measurements, three consumer phones — and three negative
> results that hold up better than the positive one.

The negative results are the original contribution. Lead with them.

---

## 2. The three findings, with their exact figures

### 2.1 A three-parameter physical law beats every learned model

The delivered model is a line-source attenuation kernel:

    E = A_hw/d_hw + A_res/d_res + B      L = 10·log10(E)

R², under the reference protocol (buffered leave-one-out, 300 m exclusion):

| Model | Block-CV 600 m | **Buffered LOO** | Leave-one-site-out |
|---|---|---|---|
| Physical kernel (delivered) | 0.255 | **0.246** | 0.222 |
| Regression on log(dist_road) | 0.221 | 0.200 | 0.189 |
| LightGBM v1 (6 features) | 0.304 | 0.137 | 0.029 |
| LightGBM v2 (8 features) | 0.332 | 0.099 | −0.035 |
| Physics + ML hybrid | 0.395 | 0.123 | 0.035 |
| Mean per (site, hour) | −0.008 | −0.419 | −0.058 |

**The point of the table is the inversion.** Read the first column and the
hybrid wins. Read the third and it is nearly worthless. The ranking reverses
between a permissive split and one that tests generalisation — and the team built
the hybrid it had itself recommended, then published that it loses.

The delivered model is chosen by code, not by hand: `04_evaluate_models.py` takes
the best R² under the reference protocol among six candidates fixed in advance.

### 2.2 Morphology from OpenStreetMap adds nothing measurable

Built area, road density and intersection counts aggregated over 300 m. Their
incremental contribution over a single distance-to-road term is **negative under
all three protocols**. Spatial contrast comes from distance to the two road
classes and from nothing else.

### 2.3 Cross-city transfer fails, and in three distinct ways

Reproducible since 21 August: `make transfer`, or
`scripts/experiments/uganda_transfer.py`. The Uganda boosters are versioned, so
it needs no Ugandan data.

| | as delivered | mean difference removed | and rescaled (= r²) | r |
|---|---|---|---|---|
| Uganda 61K (v1) | R² = −15.8 | −2.17 | +0.151 | **−0.388** |
| Uganda invariant (v2) | R² = −8.1 | −0.96 | +0.004 | +0.066 |

Three readings, and the third is the one worth a slide:

- **Not a calibration offset.** The Kampala model predicts 26 dB below Hanoi, and
  removing that difference still leaves R² negative.
- **v1 transfers anti-information**: its correlation with Hanoi is *negative*. It
  ranks quiet and loud the wrong way round.
- **v2 removes the convention artefact and leaves nothing**: r = +0.066. Not
  wrong — empty.

Against which, on the same 363 points, `log(distance to road)` alone reaches
R² = 0.240. **One locally fitted distance term carries more than a 61 000-point
model trained in another city carries at all.**

---

## 3. The question that will be asked, and the answer

> *"R² = 0.25 — isn't that very low?"*

It will come. Answer it before it is asked, with the ceiling.

Two measurements taken within 20 m of each other **at the same hour** differ by
4.23 dB on average (29 such pairs in the dataset). A spatial model must predict
the same value for both, so that disagreement is variance no spatial model can
ever explain.

| Separation | Pairs | Mean absolute difference | Implied σ |
|---|---|---|---|
| < 20 m | 29 | 4.23 dB | ≈ 3.8 dB |
| < 40 m | 87 | 5.44 dB | ≈ 4.8 dB |
| < 60 m | 229 | 6.09 dB | ≈ 5.4 dB |

Total variance of the 363 measurements is 51 dB². At the 40 m scale the map works
at, the ceiling is around **R² ≈ 0.54**. The delivered model reaches 0.246 —
about half of what is attainable, not a tenth of it.

State the caveat on the same slide: pairs at the same hour may be on different
days, so this σ includes day-to-day variation and overestimates pure measurement
noise; and 29 pairs is few. It is an order of magnitude, not a bound.

The underlying reason is the quantity itself: a 25 s A-weighted sample in
motorcycle traffic, where a single horn event reaches +17 dB
(`nguyen2025horn`). `docs/metrology.md` makes the argument and concludes that
0.25 "is reported without apology".

---

## 4. The withdrawn R² = 0.45 — put it on a slide

An earlier version reported 0.45 from a cross-validation grouped on 110 m cells,
smaller than the 300 m feature aggregation radius. It leaked between folds. The
protocol was replaced and the number withdrawn.

This is the single most credibility-building thing in the work: a team that
retracts its own best figure after finding the leak. `docs/negative-results.md`
frames it as a confirmation of Roberts et al. 2017 rather than a discovery —
which is what makes it defensible rather than embarrassing.

---

## 5. The demo: thirty seconds, three gestures

Better than any slide of the app. Rehearse it; the phone must already be on the
home screen.

1. **One measurement.** Open the noise survey, press *Measure 25 s*. It shows the
   level and attaches the clip from the same microphone session.
2. **The map.** Open it — the predicted level where you are standing appears at
   the top; the 40 m grid and the 363 points below. Zoom in once.
3. **The simulation.** GAMA screen → *Run scenario* → drag traffic to ×3. The map
   goes orange and the mean level moves.

For step 3 a `gama-server` must be running and reachable:

```sh
/Applications/Gama.app/Contents/headless/gama-headless.sh -socket 6868 -ping_interval -1
```

Set the app's server field to the machine's **wifi address**, not localhost, and
the model path to the absolute path of `simulation/gama/hanoi_noise.gaml` on that
machine. Details in `mobile/ARCHITECTURE.md` §5.2.1. **If the wifi is uncertain,
rehearse a fallback: steps 1 and 2 need no network at all.**

---

## 6. What the app must not be claimed to do

- It is **not calibrated**. No reading from it has ever been compared to a sound
  level meter. Say "relative", never "measured in dB SPL".
- It makes **no compliance claim**. The QCVN colour bands are descriptive. The
  WHO `L_den`/`L_night` comparison was withdrawn in full and must not reappear.
- It **does not predict outside the three measured areas**, and refuses to.
- GAMA **does not run on the phone**. The app draws the model's own display and
  drives it over a server; that is not the same thing as embedding it.

---

## 7. Future work — two directions, and they are not the same

Keep them apart. Detail in `docs/handover.md`.

**A real propagation kernel (CNOSSOS-EU / NoiseModelling).** The continuation.
Figure 2 of `bocher2019noisemodelling` — direct path, diffraction, first- and
second-order reflections — is exactly what a distance law does not model, and the
project's own result is the argument for adopting one. Already cited in
`references.bib`.

**Acoustic event localisation.** A different project, not a continuation. Time
difference of arrival needs clocks agreeing to about 35 ms for a ±12 m fix —
sound travels 343 m/s — plus continuous listening and four sensors at known fixed
positions. This campaign has 363 spot measurements from three unsynchronised
handsets. Strong as future work, wrong as a promise attached to this result.

---

## 8. The limits to state plainly

They will be asked about, and saying them first is stronger than conceding them.

- **No absolute reference.** Three handsets cross-calibrated against each other
  and against no standard.
- **Three sites are three typologies.** The effective number of independent
  morphological configurations is close to three whatever the number of points,
  which bounds generalisation further than the R² does.
- **Night-time is out of scope** — 10 measurements after 21:00.

# Methodology

The processing chain end to end, with every assumption stated where it is made.
Numbers here come from `models/metrics.json` and `models/model_comparison.md`,
which are produced by `scripts/04_evaluate_models.py`. None is typed by hand.

```
acquisition ──▶ preparation ──▶ features ──▶ model selection ──▶ map ──▶ simulation
  Kobo/ODK       cleaning        OSM 300 m    3 CV protocols     40 m grid   GAMA
  363 points     + weather       morphology   8 models           17 hours    agents
```

---

## 1. Acquisition

**Instrument.** Three consumer smartphones running Decibel X, A-weighting, SLOW
response, trim 0.0. **No professional sound level meter was ever available.**

**Quantity measured.** A 20–30 s A-weighted level, written `L_A,25s`. This is
**not** a certified `L_Aeq`, and not `L_den` or `L_night`. The distinction is not
pedantic: it governs which comparisons are legitimate. See
[`metrology.md`](metrology.md).

**Calibration.** The three phones were cross-calibrated **against each other**,
never against a reference instrument. The middle phone was taken as reference and
the two others trimmed to match within ~1 dB.

> **Assumption 1 — relative, not absolute.** Cross-calibration makes the three
> phones mutually consistent; it fixes no absolute scale. Consequence: contrasts
> between places and hours are supported by the data; absolute levels are
> indicative. No compliance statement is made anywhere in this repository. The
> plausible absolute bias is *bounded*, not corrected — see §5.2.

**Sampling.** 363 measurements across three deliberately contrasted urban
typologies: Ocean Park (184, new development), Hoan Kiem (99, old quarter),
Vinh Tuy (80, transport corridor). 2026-06-10 to 2026-07-22, 05:00–23:00 with
emphasis on 08–10 h and 16–18 h, varying distance to the road at each site.

> **Limitation 1 — the night is not sampled.** Ten measurements fall between
> 21:00 and 06:00, none between 00:00 and 05:00. Nothing in this study supports
> any statement about night-time noise.

**Traffic videos.** 147 timestamped videos, filmed from the pavement facing the
roadway, matched to measurements by capture time. Not published; see
[`data-sources.md`](data-sources.md).

---

## 2. Preparation — `01_prepare_field_data.py`

Kobo export → `data/processed/measurements.csv`:

1. drop submissions with GPS accuracy worse than the field threshold;
2. sanity-bound the levels and drop non-numeric readings;
3. apply per-collector calibration offsets — **currently 0.0 / 0.0 / 0.0**, since
   the trims were applied on the phones in the field;
4. join hourly weather from Open-Meteo on time and place;
5. derive `hour` and `is_weekend`;
6. **drop every identifying column**: collector name, device id, audio URL, notes.

> **Assumption 2 — the declared distance bands are informative but coarse.**
> `dist_to_road` is a band chosen by the collector (`0-2 m`, `2-10 m`, `10-30 m`,
> `30-60 m`, `> 60 m / behind building`), not a measurement. It is used for
> description and cross-checking, never as a model input; the model uses the
> distance computed from OSM geometry.

---

## 3. Features — `03_build_features.py`

For each measurement point, from the cached OSM extract, within a radius of
**300 m**:

| Feature | Definition |
|---|---|
| `built_area_ratio` | building footprint area / disc area, capped at 1 |
| `road_density_km_km2` | road length in the disc / disc area |
| `intersection_count` | OSM graph nodes in the disc |
| `dist_road_m` | distance to the nearest road of any class |
| `dist_highway_m` | distance to the nearest **major** road |
| `dist_residential_m` | distance to the nearest **minor** street |

**Road classes.** `motorway, trunk, primary, secondary` and their `_link` variants
are major; everything else, including `tertiary`, is minor.

> **Assumption 3 — `tertiary` is a local distributor, not a through route.** In
> dense Hanoi fabric that is the right reading, but it is a *parameter* of the
> model and not a truth. Moving `tertiary` into the major class redefines both
> `dist_highway_m` and `dist_residential_m` and would change every result below.

> **Assumption 4 — the hour is circular.** Encoded as `sin`/`cos` over 24 h so
> that 23:00 and 00:00 are neighbours. Raw 0–23 forces a tree to split a variable
> that has no endpoint.

> **Limitation 2 — 300 m averages away the canyon.** A disc of 300 m smooths the
> street-canyon geometry that actually governs propagation, and stays
> autocorrelated between neighbouring points. This is why the morphology
> aggregates turn out to contribute *negatively* (§4.3).

---

## 4. Model selection — `04_evaluate_models.py`

### 4.1 Three cross-validation protocols, one set of splits

Every model is evaluated on **exactly the same splits**, with 95 % confidence
intervals from a **block bootstrap** (2000 resamples over the 17 spatial blocks).

| Protocol | Geometry | What it answers |
|---|---|---|
| Block-CV | 600 m spatial blocks, 5 folds | Fast, permissive. Neighbouring blocks still share context |
| **Buffered LOO** (reference) | hold out one point, exclude everything within **300 m** | Can the model predict an unmeasured *location*? |
| Leave-one-site-out | hold out an entire site | Can it predict an unmeasured *typology*? |

> **Assumption 5 — the exclusion radius must equal the feature radius.** Features
> are aggregated over 300 m, so a buffer smaller than 300 m leaves training points
> sharing support with the held-out point. This is not a refinement: a
> `GroupKFold` on ~110 m cells is what produced the **R² = 0.45 advertised until
> July 2026 and since withdrawn**. `tests/test_cv_protocols.py` asserts the
> invariant.

### 4.2 The delivered model is chosen by code

Among six candidates fixed in advance, the script takes the best R² under the
reference protocol, writes `meta.delivered_model` into `metrics.json`, and
`07_export_gama_inputs.py` reads the `apply_residual` flag. The published map
cannot silently inherit a model that only wins a permissive split.

**Selected: the three-parameter physical kernel.**

```
E = A_hw / max(d_hw, D0) + A_res / max(d_res, D0) + B
L = 10 · log10(E)

A_highway = 4.774e7    A_residential = 3.800e7    B = 1.106e-10    D0 = 5 m
```

A line-source attenuation law: acoustic energy falls as 1/d from two source
classes, plus a background term. Three parameters, fitted on 363 points.

**The learned residual is written but not applied** (`apply_residual: false`).
`hybrid_residual_lgbm.txt` is produced at every run so the decision stays
auditable, and deliberately not used: under the reference protocol the residual
*degrades* the prediction. Delivering it would have improved the number a
permissive split reports and worsened the map where it matters.

### 4.3 Results, and why they are stated as negative

R² by protocol, n = 363 (`models/model_comparison.md`):

| Model | Block-CV 600 m | **Buffered LOO** | Leave-one-site-out |
|---|---|---|---|
| Site × hour table | −0.008 | −0.419 | −0.058 |
| log(dist_road), 2 parameters | 0.221 | 0.200 | 0.189 |
| **Physical kernel, 3 parameters — DELIVERED** | 0.255 | **0.246** | **0.222** |
| LightGBM v1 (6 features) | 0.304 | 0.137 | 0.029 |
| LightGBM v2 (8 features) | 0.332 | 0.099 | −0.035 |
| Hybrid (physics + ML residual) | **0.395** | 0.123 | 0.035 |
| Conservative hybrid (constrained residual) | 0.378 | 0.144 | 0.106 |

**The ranking inverts, almost exactly, between the first column and the other
two.** The models that win the permissive split are the ones that lose the strict
splits, monotonically. That is the signature of a model learning the sample's
spatial autocorrelation rather than physics.

Three consequences, all negative, all reported rather than buried:

1. **A three-parameter physical law beats every learned model here**, including
   the hybrid this team had itself recommended in an earlier draft. The residual
   gains ΔR² +0.140 under block-CV and loses −0.123 and −0.187 under the two
   strict protocols. The recommendation is therefore *tested and rejected at this
   sample size*, not deferred to future work.
2. **Morphology aggregated over 300 m has a negative marginal contribution.**
   Adding built ratio, road density and intersections to `dist_road` costs R²
   under every protocol (§3, Limitation 2).
3. **What survives of the ML is time, not space.** The gap between the full model
   and morphology-only under block-CV is carried by the hour — a real effect, but
   not a spatial one. It does not help predict an unmeasured place, which is
   precisely what a map is for.

R² ≈ 0.25 is a modest result. It is reported as the honest one: the alternative
figures are larger and do not survive a split that excludes the feature support.

---

## 5. Calibration and validation

### 5.1 Emission calibration — `05_calibrate_emissions.py`

Non-negative least squares of energy per vehicle *pass* against the flow counts
returns **zero coefficients for motorcycles and cars**. They are not identifiable
from these data. A non-zero heavy-vehicle coefficient exists but is fitted on 4
videos out of 147 (0.4 % of total flow, r = +0.02): an artefact of the
non-negativity constraint, **not an identified emission, and it must not be
cited**.

> **Limitation 3 — flow is not the whole story.** Speed is not observable without
> a ground homography, and source–receiver distance is not observable from a
> non-georeferenced camera field. Moving from density to flow was necessary — it
> is the difference between a structurally wrong quantity and an incomplete one —
> but it was not sufficient. One structured exception: Vinh Tuy, the only transit
> corridor, is the only site where the correlation is positive and improves with
> flow (r +0.22 → +0.30), which is the direction physics predicts.

### 5.2 Literature anchoring — `06_anchor_literature.py`

With no reference instrument, the absolute bias is **bounded rather than
corrected**, by stratified comparison against instrumented studies of Hanoi and
Ho Chi Minh City. The result is an interval on the plausible bias, propagated into
the exceedance statistics as a sensitivity band — never as a correction applied to
the levels.

### 5.3 Simulation validation — `08_validate_simulation.py`

Checks that the published grid reproduces the field measurements at the points
where they were taken. **This is an in-sample check** and is labelled as such: it
verifies chain integrity, not generalisation. Generalisation is what §4.3
measures, and the answer there is R² 0.246.

---

## 6. Map and simulation

**Grid** — `07_export_gama_inputs.py`. 40 m cells over the three measured sites
plus a 400 m margin: 5 587 cells × 17 hours (05:00–21:00).

> **Assumption 6 — never predict beyond the sampled envelope.** The margin is
> 400 m and no more. A grid once published over Bach Khoa, a district with zero
> measurements, was retracted; `tests/test_grid_extent.py` now fails if it
> recurs. See [`archive/bach-khoa/README.md`](archive/bach-khoa/README.md).

**Simulation** — `simulation/gama/hanoi_noise.gaml`. Receiver agents, not emitter
agents: the map is the input, and the simulation adds what a map alone cannot
give, namely people's exposure. Scenario physics applies `10·log10(k)` and any
mitigation **only to the traffic share of the energy**, decomposed with the same
kernel as the model.

> **Assumption 7 — measured flow applies only to the observed corridor.** Flow is
> injected on streets within 150 m of a measurement point, not uniformly over the
> exported zone. Spreading one point's measurement over 673 streets diluted it to
> 0.076 vehicles per street and left the lake loop empty 92 % of the time, though
> every video was filmed there.

Correcting the scenario physics halved the claimed benefit of pedestrianisation,
from −7.0 dB to **−3.5 dB** of zone mean. Invariant checked: at k = 1 with no
mitigation, the simulated map is identical to the predicted map.

---

## 7. What this methodology does not support

- Any absolute compliance statement against QCVN, TCVN, the EU END directive or
  the WHO guidelines. Exceedance rates are reported as descriptive statistics of
  `L_A,25s` with a bias sensitivity band.
- Any statement about night-time noise (Limitation 1).
- Any prediction outside the three measured sites plus 400 m (Assumption 6).
- Any modal share from the video counts, until the detector is validated against
  manual counts — see [`handover.md`](handover.md), debt 2.

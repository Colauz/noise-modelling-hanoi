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

## 2b. Traffic counting from video — `02_count_vehicles.py`

147 timestamped videos, matched to the measurements by capture time. This step
sets the **input uncertainty of everything downstream**, so its parameters and its
weaknesses are stated here rather than left in the code.

**Chain.** YOLOv8**n** detection at `imgsz=640`, `conf=0.3`, on COCO classes mapped
to motorcycle / car / bus / truck; bicycles are excluded as non-motorised. Object
tracking with **ByteTrack**, sampled at **10 fps** — tracking needs consecutive
frames, and at 1 fps no tracker can associate detections. Crossings of a virtual
line are then counted **in post-processing** over the stored trajectories, which is
what allows the line orientation to be chosen once the video has been seen in full,
and makes the counting rule testable without rerunning YOLO.

**Three guards, each established by calibrating on our own videos, each fixing a
failure that had produced silent nonsense:**

| Guard | The failure it fixes |
|---|---|
| Dead band at **5 % of image height**, not a fixed pixel count | Our videos have two resolutions. An absolute dead band was 4 % of the height in one case and 13 % in the other — passing all jitter on one side, blocking every crossing on the other |
| **At most one crossing per direction per trajectory** | ByteTrack reuses identifiers on sparsely populated scenes; counting every side change gave 109 veh/min on a video showing 0.6 vehicles per frame |
| **Line orientation chosen per video**, perpendicular to the dominant motion, on amplitudes normalised by the image dimension | A forced horizontal line returned **zero flow on 14 of the 19 `VID_*` videos**, which are filmed across the street. A whole site read as empty for a purely geometric reason |

> **The only independent check on the counting is Little's law.** For a stationary
> flow, `L = lambda x W`: the mean number of vehicles present equals the flow times
> the residence time. Density and flow are measured separately here, so their ratio
> yields an *implied* residence time that can be compared against the residence time
> *observed* directly on the trajectories. The first counting rule implied 0.3 s,
> i.e. vehicles crossing the field at 60–90 m/s — physically absurd, and that is how
> the identifier-reuse bug was found. After correction the implied time is 4.7 s
> against 7.6 s observed: the same order, which is what this check can establish.
>
> This is a **consistency** check, not an accuracy check. It can detect a counting
> rule that is impossible; it cannot tell us how many motorcycles were missed.

> **Assumption 2b — the flow measured over ~24 s stands for the hour.** Videos have
> a median duration of **24 s** (p10 20 s, p90 30 s), and their crossing counts are
> converted to vehicles per minute and then attributed to the (site, hour) pair.
> That assumes the flow is stationary over the window and representative of the hour.
>
> The size of that assumption is measurable from the data we have. Across the 11
> (site, hour) pairs holding three or more videos, the flow varies between videos of
> the *same* site and hour with a coefficient of variation of **31 % at the median**
> (interquartile range 26–47 %). So a single 24 s window estimates its hour's flow to
> roughly ±30 % (1σ) from sampling alone, before any detector error. That is an
> order of magnitude, not a calibrated uncertainty: 11 groups is a thin basis, and it
> conflates genuine within-hour variation with counting noise.

> **Limitation 2b — the detector is not validated.** No manual reference count has
> been made, on any video. **Precision, recall and MAPE per class are unknown.**
> Under-detection of two-wheelers by `yolov8n` at 640 px is expected — they are
> small, densely packed and heavily occluded in Hanoi traffic — but it is **not
> quantified**. Consequently **the modal shares are not publishable**, and the
> per-class flows must be read as lower bounds on the two-wheeler share.
>
> Closing this is the highest value-per-effort task left in the project: a manual
> count on ten videos, about one day, turns an open-ended limitation into a
> quantified uncertainty. See [`handover.md`](handover.md), debt 2.

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

> **Assumption 5a — the bootstrap resamples blocks, never points.** Noise levels at
> nearby points are strongly autocorrelated, and their features are computed over
> overlapping 300 m discs. Resampling individual points would treat correlated
> observations as independent draws, understate the variance of the estimator and
> return a confidence interval that is too narrow. The interval would then say the
> score is more certain than the data can support — which is the same failure mode
> as a leaking split, arriving by a different route: **an artificially narrow
> interval makes R² = 0.246 as attackable as a protocol that leaks.** Resampling
> the 17 spatial blocks keeps the correlated observations together, so the
> uncertainty reported is the uncertainty across independent portions of the
> sample. Implemented in `04_evaluate_models.py`.

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

`D0 = 5 m` is a distance floor. Without it the 1/d term diverges for a receiver at
the kerb, and a handful of points measured within a metre or two of the carriageway
would dominate the fit through a singularity that has no physical meaning: a real
road is not a mathematical line, and at that range the line-source approximation
has already stopped holding.

> **Assumption 5b — the kernel is fitted in decibels, not in energy.** This is a
> choice of loss function, and it determines the published coefficients.
>
> Our levels span **47 to 88 dB**. Because a decibel is logarithmic, that range is
> roughly **four orders of magnitude in energy**: the loudest point carries about
> ten thousand times the acoustic energy of the quietest. A least-squares fit
> performed in energy would therefore be driven almost entirely by the few loudest
> measurements — the residual of a single 88 dB point would outweigh the combined
> residuals of a hundred points near 50 dB — and the fitted coefficients would
> describe the noisiest kerbside situations rather than the distribution as a whole.
>
> We minimise the discrepancy **in dB** instead. That weights every measurement
> comparably, and it is also the metric the model is judged on: R² and MAE are
> reported in dB, so fitting and scoring use the same scale. The consequence to be
> aware of is that the kernel is not the maximum-likelihood solution under an
> energy-additive noise model; it is the best fit to the quantity we actually
> report.

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

**Two hybrid variants are published side by side**, not one. `hybrid` lets the
residual model see everything; `hybrid_lowcap` withholds the distances from it —
they are already consumed by the physical kernel — and caps its capacity at 5
leaves and 120 trees. They answer different questions: the first maximises
interpolation within the sampled typologies, the second better preserves
extrapolation to an unseen one. **Picking between them on the cross-validation
that then publishes the winner would be selection on the test set**, so both are
reported and neither is quietly dropped.

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

> **Assumption 5c — the construction source is calibrated on medians, not means.**
> The equivalent construction source is derived from the gap between points that
> reported nearby construction and those that did not, at Ocean Park. Sound levels
> add in energy, so the natural move is to compare energy means — and that is what
> was done first. It gave an equivalent source of **74.7 dB**, which propagates to
> about **+8 dB** in the simulation near a construction site, against the **+2 dB**
> actually observed in the field. The mean is dominated by a handful of loud points
> and overstates the source by a factor of four in level terms.
>
> The calibration therefore compares **medians**, which reproduces the observed
> +2 dB. This is a choice that changes a published parameter, and it is made the way
> a calibration should be: not by preferring the statistic that behaves better, but
> by rejecting the one whose output contradicts a field observation.

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

**Every anchor carries a reliability status, and the status governs its use.** This
is the project's source policy; it applies here and in
[`literature-review.md`](literature-review.md), which uses the same three levels
rather than inventing a parallel scheme.

| Status | Meaning | Permitted use |
|---|---|---|
| `verified` | The value is read in the source's own abstract or summary | Citable as a primary reference |
| `to_check` | The value is reported second-hand and not yet confirmed against the source PDF | Usable, but flagged as unverified wherever it appears |
| `grey` | Grey literature — an institute quoted in the press, undocumented protocol, not peer-reviewed | **Never cited as a primary reference.** Contextual orientation only |

The distinction is load-bearing rather than decorative. The figures circulating for
twelve Hanoi arteries come from an institute via the Vietnamese press with no
documented protocol; they are the most convenient numbers available and the least
defensible, so they are marked `grey` and excluded from the bias interval. The
Phan et al. (2010) `L_den` values, the only professionally instrumented campaign
published for Hanoi, are `to_check` until confirmed against the PDF — which is
still open; see [`handover.md`](handover.md).

Alongside the status, each anchor declares `metric_gap_dB`, the systematic gap
**expected from the difference in quantity alone** — an `L_den` carries evening and
night penalties and sits mechanically above a daytime level; dosimeters worn by
cyclists sit inside the traffic stream rather than at the kerb. That expected gap is
subtracted before the residual is read as instrumental bias. Comparing our numbers
to a published number without that subtraction would attribute to our smartphones a
difference that is a property of the indicator.

### 5.3 Simulation validation — `08_validate_simulation.py`

Checks that the published grid reproduces the field measurements at the points
where they were taken. **This is an in-sample check** and is labelled as such: it
verifies chain integrity, not generalisation. Generalisation is what §4.3
measures, and the answer there is R² 0.246.

Current figures, against the delivered physical kernel: bias −1.24 dB, MAE 5.30 dB,
RMSE 6.49 dB, r 0.444, R² 0.166, 53.1 % of points within ±5 dB.

> **Read those numbers as a trade-off, not as a failure.** The three-parameter
> physical kernel fits the training points less closely than the LightGBM did
> (R² 0.166 against 0.499) and generalises better under buffered leave-one-out
> (0.246 against 0.137). The map is flatter — σ 3.14 dB simulated against 5.57 dB
> for the earlier grid — because the model is less flexible. The earlier, more
> flattering validation described a model that is not delivered; it is archived in
> [`archive/validation-2026-08-05/`](archive/validation-2026-08-05/).

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
  manual counts — see section 2b and [`handover.md`](handover.md), debt 2.

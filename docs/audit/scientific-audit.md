# Scientific audit — *Noise Modelling Hanoi*

> # ⛔ FROZEN DOCUMENT — 5 August 2026
>
> **This is a dated record, not current documentation. It is never updated.**
>
> Every figure below — including **R² = 0.45**, which appears eleven times — is a
> value of the **old protocol**, measured before the corrections this audit
> triggered. **None of them matches `models/metrics.json`, and none should.** File
> paths likewise refer to the repository layout as it stood at commit `c5108d6`.
>
> The validation metrics quoted here (bias −0.52, MAE 3.68, r 0.719, 74 % within
> ±5 dB) are those of 5 August 2026, **before the grid was regenerated**. Current
> values are in `docs/methodology.md` section 5.3.
>
> **For current results, read [`../methodology.md`](../methodology.md) and
> [`../../models/model_comparison.md`](../../models/model_comparison.md).**
> The delivered model scores **R² = 0.246** under the reference protocol.
>
> An audit whose figures are corrected after the fact documents nothing. This one
> is kept exactly as written so that the diagnosis remains verifiable against what
> was actually claimed at the time. It is excluded from the repository's
> number-consistency check for that reason — see `CONTRIBUTING.md`.

> ## ⚙️ Status of the follow-up actions (5 August 2026)
>
> The project has **pivoted to a methodological study**: no professional sound
> level meter available, field campaign closed. Recommendations that assumed extra
> equipment or extra fieldwork are therefore moot; those bearing on analysis and
> writing have been applied. Details in `ROADMAP.md`.
>
> | Recommendation | Status |
> |---|---|
> | **P0-1** Honest CV + baselines + ablation + CI | ✅ `scripts/evaluate_models.py` (600 m blocks, 300 m BLOO, LOSO, 8 models, block bootstrap) |
> | **P0-2** Metric and standards reframing | ✅ target `L_A,25s`, WHO `L_den`/`L_night` removed everywhere, QCVN as a descriptive statistic + sensitivity — `paper/sections/metrology.md` |
> | **P0-3** Absolute anchoring | ⚠️ **adapted**: no sound level meter → bias bounded by anchoring on instrumented literature (`scripts/literature_anchoring.py`). The bias is bracketed, not corrected. |
> | **P0-4** Repository cleanup | ✅ Bach Khoa artefacts archived in `outputs/deprecated/`, notebook 09 neutralised, `metrics.json` replaces manual copying |
> | **P0-5** Data publication | ⏳ to do (Zenodo + DOI + ethics statement) |
> | **P1-1** Additional campaign | ❌ **moot** — fieldwork closed |
> | **P1-2** Measured R² ceiling | ❌ moot (requires repeated fixed points) |
> | **P1-3** CNOSSOS physical layer | ⏸️ deferred to *future work* |
> | **P1-4** Video counting as flow | ⏸️ argued as a negative result — `paper/sections/negative_results.md` |
> | **P1-6** GAMA physics | ✅ background/traffic energy decomposition, zone 30 bounded to 150 m — corrected and verified numerically |
>
> The audit text below is **kept exactly as written**: it documents the state at
> the time of the diagnosis, and the figures it cites (R² 0.45, etc.) are those of
> the old protocol.

**Audit date:** 5 August 2026
**Scope:** repository `noise-modelling-hanoi` @ `c5108d6` (README, ROADMAP, `field/`, `scripts/`, `notebooks/01→09`, `gama/`, `outputs/`)
**Angle:** data science + environmental acoustic modelling. A referee's eye.

> **Method note and limitation of this audit.** The `data/` folder is absent from the machine (it is
> `gitignore`d). I therefore **could not recompute** the model scores from the raw measurements.
> Everything stated below is either **[V]** verified by computation on the artefacts present in
> `outputs/`, **[C]** read directly in the code, or **[I]** inferred and flagged as such.
> This inability to replay the chain is itself an audit finding (§4.8).

---

## 1. Summary of the current state

### 1.1 What the project does today

| Block | Actual content |
|---|---|
| **Collection** | 363 spot smartphone measurements, 3 districts of Hanoi (Ocean Park 184, Hoan Kiem 99, Vinh Tuy 80) **[V]**, via ODK Collect → KoboToolbox, sound meter application *Decibel X* (A-weighting, SLOW response), 3 cross-calibrated collectors, ~20–30 s per point + audio clip ≥ 10 s **[C]** |
| **Ancillary data** | 147 timestamped traffic videos counted by YOLOv8n, construction site register (dedicated form), hourly Open-Meteo weather (reanalysis) **[C]** |
| **Cleaning** | `scripts/prepare_field_data.py`: single source of truth, dedup, GPS filter `accuracy < 50 m`, dB filter ∈ [20,120], site reassignment by nearest GPS centre, explicit backfill of v2 fields, calibration offsets (all 0.0) **[C]** |
| **Model** | LightGBM, 6 features: `built_area_ratio`, `road_density_km_km2`, `intersection_count`, `dist_road_m` (all within a **300 m** radius from OSM) + `hour` + `is_weekend`. Trained **directly** on the 363 measurements **[C]** |
| **Advertised score** | r 0.69 / R² 0.45 / MAE 4.2 dB under "honest spatial CV"; Uganda→Hanoi transfer R² −1.26 **[C, notebook 08 outputs]** |
| **Map** | predicted grid, two coexisting versions: ① 8 640 cells at ~30 m around **Bach Khoa** (notebooks 08/09); ② 5 587 cells at 40 m over the **3 measured sites**, one column per hour `h5…h21` (`scripts/export_gama_zones.py`) **[V]** |
| **Simulation** | GAMA `hanoi_noise.gaml` (446 lines): predicted hourly background + mobile vehicles (visual), construction sites calibrated in energy, sliders for hour / traffic volume / mitigation **[C]** |
| **Validation** | `scripts/validate_simulation.py`: grid ↔ measurements comparison, **explicitly announced as *in-sample*** — bias −0.52 dB, MAE 3.68 dB, RMSE 4.98 dB, r 0.719, 74 % within ±5 dB **[V, recomputed]** |
| **Deliverables** | `outputs/report.pdf` (8 pages), HTML slide deck, Folium maps, figures |

### 1.2 Overall verdict

**The project is very good engineering work and still-incomplete research work.**

The engineering is solid: a working end-to-end chain, a single source of truth for cleaning, a clean
separation of "measured / predicted / calibrated / excluded", a documented refusal to invent
parameters. That is rare and it is to the project's credit.

But **three obstacles currently prevent calling the study "reliable and generalisable"** in the sense
a Q1 journal would mean:

1. **The headline figure "R² 0.45 under honest spatial cross-validation" is not honest**: the CV
   blocks are ~110 m while the features are computed over a 300 m disc. There is structural spatial
   leakage. The only genuinely out-of-sample protocol in the record — *leave-one-site-out* — gives
   **R² from −0.68 to +0.21**, i.e. *worse than the mean*. (§4.3)
2. **The morphology → noise link is not demonstrated to be useful.** A simple "site × hour" lookup
   table, with no morphology at all, reaches **R² 0.27 / MAE 4.79 dB under leave-one-out** on the same
   points **[V, computed by me]** — against 0.45 / 4.2 advertised for the model under a more permissive
   CV. The net contribution of the 4 OSM features is therefore modest at best, and has never been
   isolated.
3. **The metrology is not anchored.** The 3 phones are calibrated *against each other*, never against
   an absolute reference (class 1/2 sound level meter or acoustic calibrator). The whole level
   distribution — and therefore the 39 % QCVN exceedance rate — could be shifted by several dB
   without anyone being able to tell. (§4.1)

None of these three is fatal. All are repairable, and two of them in a few days of work with no new
collection. §5 gives the plan.

---

## 2. Dissecting the data collection

### 2.1 Instrumentation

- **Sensor:** the *Decibel X* application on consumer smartphones. Uniform settings: **A**-weighting,
  **SLOW** response, trim 0.0 **[C, `field/README.md`]**.
- **Quantity recorded:** a single number, the "AVG" value read on screen. The form says
  *"Read LAeq / average value from the dB app"* **[V, XLSForm]**. No integration duration recorded,
  no L_Amax, no L10/L90, no third-octave bands.
- **Calibration:** a **relative** 5-step procedure — the 3 phones side by side, the middle phone taken
  as an arbitrary reference, offsets entered in the app's trim **[C]**.
  In the code, `CALIBRATION_OFFSET = {'laurian': 0.0, 'lucas': 0.0, 'quang': 0.0}` **[C]**.
- **Height:** ~1.2 m, hand-held **[C]**. Not recorded per point.
- **Phone model:** **not recorded**. The `collector` field is an imperfect proxy for it.

### 2.2 Spatial sampling design

- 3 zones chosen for their contrasting typologies: Ocean Park (new vertical fabric),
  Vinh Tuy (transport corridor), Hoan Kiem (old quarter). A sound choice in principle.
- **Selection of points within a zone: unspecified.** No grid, no random draw, no documented
  stratification. The protocol only says *"vary the distances to the road"* **[C]**.
  This is convenience sampling along accessible streets.
- `dist_to_road` is entered in **classes** (0-2 / 2-10 / 10-30 / 30-60 / >60 m), not in metres **[V]**.
- GPS filter used: `accuracy < 50 m` **[C]**, whereas the form asks the collector to wait for
  `< 10 m` **[V]**. Inconsistent: 50 m of positional uncertainty on a 40 m grid is more than one cell
  of error.

### 2.3 Temporal sampling design

Actual hourly distribution, recomputed **[V]**:

```
 5h:  6   6h: 27   7h: 53   8h: 37   9h:  0 ←  complete gap
10h: 17  11h: 31  12h: 22  13h: 18  14h:  9
15h: 48  16h: 10  17h: 54  18h: 16  19h:  9
20h:  2  21h:  1  (+3 points at 22-23h)
```

- **Night almost absent.** The regulated "night" period of QCVN 26:2010 runs from 21:00 to 06:00.
  The dataset holds **10 points out of 363, i.e. 2.8 %** **[V, via `hanoi_exceedances.csv`]**,
  and **zero measurements between 00:00 and 05:00**. Yet that is the period with the strictest
  threshold (55 dB) and the one that weighs most on health (WHO: L_night).
- **Gap at 09:00**, marked troughs at 14:00, 16:00, 19:00–21:00.
- **Weekend**: reported as "light" in the report, not quantifiable here (data absent).
- **Seasonality: none.** Campaign concentrated in June–July 2026 **[I, git history]** —
  a single season, in the monsoon. No coverage of Tết, the dry season, or school holidays.

### 2.4 Metadata collected

The v2 form is well designed **[V, XLSForm]**: site, collector, GPS, audio, dB, source category,
distance-to-road class, phone orientation, microphone direction, distance to the dominant source,
motorcycle/car/HGV/EV counts, traffic video, audible construction. Good granularity.

Missing, and these are the fields most expensive to recover *after the fact*: **integration
duration**, **phone model**, **measurement height**, **perceived wind / presence of a windscreen**,
**road surface state (dry/wet)**, **fixed-point identifier** allowing repetition, **street width and
façade height** (the H/W ratio of the urban canyon).

---

## 3. Dissecting the workflow

```
Kobo CSV ──► prepare_field_data.py ──► measurements.csv
                                            │
   videos ──► count_vehicles.py (YOLOv8n) ──┼──► vehicle_counts.csv
                                            │
                       Open-Meteo (reanalysis)┘
                                            │
                          nb 07: EDA, standards, Folium map
                                            │
                          nb 08: OSM features 300 m + LightGBM + CV
                                            │
                    ┌───────────────────────┴───────────────────────┐
        nb 09 (Bach Khoa)                             export_gama_zones.py (3 sites × 17 h)
                    │                                               │
                    └──────────► outputs/gama_inputs/ ◄──────────────┘   ⚠ two producers
                                            │
                            calibrate_emissions.py (NNLS in energy)
                                            │
                          GAMA hanoi_noise.gaml ──► validate_simulation.py (in-sample)
                                            │
                                     build_report.py ──► report.pdf
```

**Mapping algorithm.** There is **no spatial interpolation** (neither kriging nor IDW) and
**no physical propagation model**. The map is pure **land use regression (LUR)**: for each cell, 4
OSM descriptors are computed within a 300 m disc, plus the hour, and LightGBM is asked for its
prediction. That is a legitimate and published approach, but it is a methodological choice that is
**never justified nor compared** against an alternative in the record.

**Current validation protocol.**
- "Spatial" CV: `GroupKFold(5)` on groups = `(lat.round(3), lon.round(3))`, i.e. cells of
  **~111 m × 104 m** at Hanoi's latitude **[C, notebook 08]**.
- Random CV, kept as an optimistic upper bound. Good practice.
- Leave-one-site-out, reported on page 6 of the PDF: R² = 0.21 / −0.68 / −0.37 **[C]**.
- Simulation validation: *in-sample*, honestly labelled as such **[C]**.

---

## 4. Critical evaluation — gap analysis

### 4.0 Strengths (to keep and to foreground in the manuscript)

They are real and they should be defended:

1. **Documented methodological honesty.** Refusing to inject invented vehicle emissions when the NNLS
   returns null coefficients (`calibrate_emissions.py`) is exactly the right scientific reflex. The
   "in-sample validation" note in `validate_simulation.py` and in the PDF, likewise. The "honest"
   backfill that leaves NaN rather than inventing, likewise. **This is the record's greatest asset** —
   many published studies do not do it.
2. **The negative result on cross-city transfer is publishable.** Uganda → Hanoi R² −1.26, with the
   Barcelona control as a dress rehearsal. That is a genuine methodological contribution, and the
   survey paper explicitly calls for it.
3. **Explicit separation of each layer's status** (predicted / measured / calibrated / excluded) in the
   `.gaml` header and in `export_gama_zones.py`. Exemplary.
4. **Single source of truth** for field cleaning, reused as a module by the notebook.
   No duplicated logic. Good software architecture.
5. **Invariant `built_area_ratio` feature** introduced after diagnosing the OSM mapping-convention bias
   (Kampala = individual buildings, Barcelona = blocks). A fine, well-conducted diagnosis.
6. **Traceability of corrections**: site reassignment by GPS, with a log of the 6 corrections.
7. **Written and reproducible field protocol**, with versioned XLSForm files.

---

### 4.1 🔴 CRITICAL — Metrology: no absolute anchor

**The problem.** Cross-calibration aligns the 3 phones **with each other**, on an arbitrary fourth
("the middle phone"). There is **no point of attachment to an acoustic reference**. The consequence is
direct: a systematic bias common to all 3 devices is strictly invisible and propagates in full through
every result.

**Why it matters here.** The report's headline deliverable is *"39 % of measurements exceed QCVN"*.
A bias of +3 dB would collapse that figure; a bias of −3 dB would push it beyond 55 %.
The literature on smartphone sound level meters gives discrepancies commonly of ±3 to ±8 dB(A)
depending on device and OS, non-linear in level. **No normative conclusion is currently defensible.**

**Aggravating factors.**
- The phone model is not recorded → impossible to correct *after the fact*.
- No windscreen mentioned. The "no wind effect" analysis **[C, notebook 07]** relies on
  **Open-Meteo reanalysis** wind (grid ~10–25 km) — an instrument incapable of detecting a microphone
  artefact that depends on *local* wind at 1.2 m. That is an absence of evidence, not evidence of
  absence.
- Floor and saturation not characterised. The maximum measured is **88.0 dB** **[V]**, in the range
  where smartphone AGC chains begin to compress. High levels are probably flattened, which
  **artificially reduces the variance of the target** (σ = 7.1 dB **[V]**) and therefore mechanically
  caps the achievable R².

### 4.2 🔴 CRITICAL — The measured quantity is comparable to none of the standards cited

**The problem.** The project's quantity is an "AVG" over ~20–30 s. Yet:

| Standard cited in the report | Actual quantity of the standard | Comparable to the "AVG 20-30 s"? |
|---|---|---|
| QCVN 26:2010/BTNMT, 70 / 55 dB | L_Aeq over the reference period, class 1 or 2 instrument, TCVN 7878-2 method | **No** — neither duration nor instrument compliant |
| WHO 2018, 53 / 45 dB | **L_den** and **L_night**, **annual** averages, with +5 dB evening / +10 dB night penalties | **No, very far from it** |

The PDF (§3.4) presents "WHO (road-traffic guideline) — Day 53 / Night 45" in a day/night table.
That is an **error of kind**: L_den is not a "daytime" indicator, it is an indicator aggregated over
24 h and over the year. A Q1 reviewer will raise this point first.

The ROADMAP itself notes the problem ("position our dB metric against Leq/L_dn/L_max, cf. survey
paper §V") — but the report was circulated without addressing it.

**Second problem, quantitative.** A 25 s sample on a Hanoi street does not converge to the L_Aeq of
the period: a passing bus or a horn blast displaces the value by 5–10 dB.
The report claims *"±5 dB of irreducible noise, capping R² near 0.6"* — a statement
**made with no derivation and no measurement**. It is probably right, but it is currently
unverifiable, whereas it is easy to establish experimentally (§5, P0-3).

### 4.3 🔴 CRITICAL — Model validation overstates performance

This is the most serious point on the data science side.

**(a) Spatial leakage in the "spatial CV".**
The `GroupKFold` groups are cells of ~110 m. The features are aggregates over a disc of
**300 m radius**. Two points 110 m apart therefore have discs whose intersection exceeds
**85 % of the area**: their feature vectors are near-identical and their noise levels are strongly
autocorrelated. In training, the model therefore sees near-twins of its test points.
**The R² 0.45 is not out-of-sample.**

The accepted rule in spatial modelling (Roberts et al. 2017, *Ecography*; Meyer & Pebesma 2021,
*Nat. Commun.*) is that the CV block must exceed the autocorrelation range of the predictors —
here **at least 600 m** (2 × buffer radius), ideally with an excluded buffer zone (*buffered
leave-one-out*).

**(b) The only genuinely out-of-sample validation gives a negative result.**
The PDF's *leave-one-site-out*: **R² = +0.21 (Ocean Park), −0.68 (Vinh Tuy), −0.37 (Hoan Kiem)**.
A negative R² means: *the model does worse than predicting the global mean everywhere*.
The report calls it a "stress test", "noisy on small samples", and points back to the
0.45 as the "reliable figure". **It is the other way round.** Leave-one-site-out is the clean
protocol; it is the 0.45 that is contaminated. The correct conclusion is: *at this stage, the model
does not extrapolate to an unseen urban typology* — which the PDF's Limitations section states in so
many words, contradicting the figure put on the cover.

**(c) The effective number of degrees of freedom is of the order of 3, not 363.**
The 4 morphology features are aggregates over 300 m. Within a site, whose extent is a few hundred
metres, those 4 values vary very little. The model therefore has in practice
**3 distinct morphological configurations**, repeated 363 times. Any inference about the
morphology → noise relationship rests on n ≈ 3. No confidence interval is reported anywhere.

**(d) No comparison model has been tested.** The only point of comparison in notebook 08 is the
mean (MAE 5.9 dB). I built the missing comparator from
`outputs/hanoi/validation_simulation.csv` **[V, audit computation]**:

| Predictor | Protocol | R² | MAE |
|---|---|---|---|
| Global mean | — | 0.00 | 5.9 dB |
| **Mean per site** (no morphology) | leave-one-out | 0.03 | 5.79 dB |
| **Mean per (site × hour)** (no morphology) | leave-one-out | **0.27** | **4.79 dB** |
| LightGBM morphology + hour | "spatial CV" 110 m (optimistic) | 0.45 | 4.2 dB |
| GAMA grid vs measurements | *in-sample* | 0.51 | 3.68 dB |

*Reading:* a 29-entry lookup table, without a single spatial variable, already captures
**more than half** the model's advertised performance — and it does so under strict leave-one-out.
The protocols are not rigorously identical (LOO on 360 points vs GroupKFold on 363),
so this table is **strong evidence, not proof**; but it makes measuring the net contribution of
morphology indispensable (§5, P0-1). As it stands, the question *"are your 4 OSM features good for
anything?"* has no answer in the record.

**(e) No uncertainty quantification.** No bootstrap confidence interval on R²/MAE, no prediction
interval on the map, no analysis of the spatial autocorrelation of residuals (Moran's I), no
applicability-domain mask on extrapolated cells.

**(f) The Barcelona comparison (R² 0.61) is misleading.** It appears in the same table as the Hanoi
scores on page 6 of the PDF. But Barcelona = fixed class 1 sensors, L_Aeq integrated over 4 months.
That is not the same statistical target: a long-term L_Aeq is intrinsically far more predictable
than a 25 s snapshot. The docstring of `train_v2_invariant.py` states this correctly —
the PDF does not. To be removed from the table or isolated with an explicit warning.

### 4.4 🟠 MAJOR — Map resolution and physics

- **The 300 m smoothing destroys exactly the information a noise map should carry.** Two neighbouring
  cells of the 40 m grid share > 98 % of their feature disc: their predictions are near-identical.
  The model is structurally incapable of representing the façade / inner courtyard contrast
  (10–15 dB in dense fabric), the screening effect of buildings, or the transverse gradient of a
  street. It shows in the figures: σ(simulated) = 5.52 dB against
  σ(measured) = 7.10 dB **[V]** — the map is significantly flatter than reality.
- **No physics.** No geometric divergence, no ground effect, no diffraction / screening by buildings,
  no façade reflection, no atmospheric absorption. Yet the building footprints are already downloaded
  and exported as shapefiles — the raw material is there, unused.
- **The circulated map does not cover the studied area.** `outputs/hanoi/hanoi_noise_map.csv`,
  `hanoi_heatmap.html` and `outputs/gama_inputs/noise_map.csv` cover a 1 500 m disc around
  **Bach Khoa** — a district where **no measurement was taken** **[V: lat 20.992-21.019,
  lon 105.829-105.858, 8 640 cells]**. That is extrapolation to an unseen typology, by a model whose
  leave-one-site-out is negative. These three files must not be circulated as they stand.

### 4.5 🟠 MAJOR — Video counting: no detector validation, wrong quantity

- **The quantity counted is the wrong one.** `count_vehicles.py` measures a *density of vehicles
  visible per frame* **[C]**. Traffic acoustics depends on **flow** (veh/h) and **speed**,
  not on the number of objects present in a non-georeferenced camera field. That is the root cause
  of the failure of `calibrate_emissions.py` — a cause the script itself identifies correctly.
- **No assessment of detector accuracy.** YOLOv8**n** (the smallest model), `imgsz=640`,
  `conf=0.3`, COCO classes **[C]**. On a Hanoi motorcycle stream, under-detection is massive and
  well known. Yet the report publishes a "traffic composition by site" figure
  (Hoan Kiem 65 % motorcycles, Ocean Park 84 % cars **[V, `fleet_mix.csv`]**) **without a single line
  of validation** — no reference manual count, no precision/recall, no MAPE. Those modal shares are
  not publishable at this stage.
- **Parked vehicles counted**, no motion filter — already identified in the ROADMAP.
- **Video ↔ measurement matching at ±5 min** **[C, `MATCH_MAX_S = 300`]** although the measurement
  lasts 25 s. A 5 min gap between the filmed traffic and the recorded level is enough to decorrelate
  the two. The PDF reports a median gap of 15 s — good; but the tail of the distribution is not
  controlled.

### 4.6 🟠 MAJOR — Construction site calibration: fragile extrapolation

The equivalent construction source (64.7 dB at 56 m, propagated as 20·log₁₀) derives from a
**median difference of +2.0 dB** between 32 "construction reported" points and 152 "without", at
Ocean Park **[C]**.

- **No significance test, no confidence interval.** +2.0 dB on n=32 vs n=152, with
  σ ≈ 8 dB at Ocean Park **[V]**: the standard error of the difference is of the order of ±1.5 dB. The
  difference is probably indistinguishable from zero.
- **No confounder control.** The "construction" points are not matched to the others on distance to
  the road, hour or sub-zone. A construction site is typically at the kerbside;
  the difference could be entirely due to traffic.
- **`construction_nearby` is partly derived from the target.** The backfill infers it from the
  declared noise category (`class` contains "construction") **[C]**. But `class` is filled in
  by the collector *on the basis of what they hear*. We are therefore partly selecting on the variable
  we are trying to explain → circular bias toward a positive difference.
- **Strong extrapolation**: from +2 dB observed at 56 m, a source is inferred which, at 25 m, adds
  ~+7 dB **[C]**. The extrapolation factor is 3.5× the observed effect, using geometric divergence
  alone and with no error bar.

### 4.7 🟡 MODERATE — GAMA simulation: two physically wrong approximations

The `.gaml` is well written and well commented. Two substantive corrections:

1. **The 10·log₁₀(k) law is applied uniformly to every cell** **[C, `reflex scenario`]**,
   including inner courtyards and cells far from any road. Physically,
   `10·log₁₀(k)` applies only to **the share of energy attributable to traffic**. Tripling traffic
   cannot add +4.8 dB in a courtyard where traffic contributes only marginally.
   *Fix:* decompose `E_cell = E_traffic(d_road) + E_residual` and apply the factor only to
   `E_traffic`.
2. **The "zone 30" mitigation applies −3 dB to the whole zone** **[C]**, including streets that are
   not in the zone 30 and cells far from the streets concerned. Same fix: apply it on the selected
   roads, with decay in distance.

PLAN.md also provides for **receiver pedestrian agents** (tier 2) — that is the right idea,
and it is what would make GAMA a contribution rather than a viewer. It is not implemented.

### 4.8 🟠 MAJOR — Reproducibility

- **The data cannot be replayed.** `data/` is outside git and absent from the machine. Neither I, nor
  a referee, nor your future self in January can recompute a single figure. For a project claiming
  descent from a *Scientific Data* article, that is blocking.
- **Two producers write the same files.** `notebooks/09_export_gama.ipynb` and
  `scripts/export_gama_zones.py` both write into `outputs/gama_inputs/`. The current state of that
  folder is **hybrid**: `noise_points.shp` is the 3-zone version (5 587 cells, columns
  `h5…h21`) **[V]**, but `noise_map.csv` is still the stale **Bach Khoa** version (8 640 rows)
  **[V]**. Replaying notebook 09 would silently overwrite the simulation inputs.
- **Manual copying of scores.** The README instructs one to *"copy the notebook 08 scores into
  MODEL/PERSITE at the top of build_report.py"* **[C]**. The PDF can therefore display metrics
  desynchronised from the model actually delivered. The values there are moreover hardcoded
  strings.
- **The PDF contains stale sections.** Page 8 "Next steps" still announces *"vehicle counting on the
  83 videos"* and *"GAMA: import the map"* **[C]** — two tasks done since, with 147 videos.
- No environment pinning (`>=` everywhere), no `data/processed/` created by the code
  (notebook 08 writes into a folder it never creates), notebooks executed on another
  machine under Python 3.9.

### 4.9 🟡 MODERATE — Regulatory compliance and ethics

- **No ethics / IRB statement.** 147 videos filmed in public space in Hanoi: faces and
  registration plates. A Q1 journal will require a statement (approval or exemption from the
  VinUniversity ethics committee) and, if the videos are shared, blurring.
- **No data licence**, no deposit plan (Zenodo/DOI), no pseudonymisation of the collectors (first
  names in clear text in the pipeline).
- **No explicit reference to measurement standards**: ISO 1996-1/2 (weather conditions, height,
  distance to reflecting surfaces, duration), TCVN 7878-2:2010, nor to the CNOSSOS-EU framework.

---

## 5. Action plan for a "perfect study"

Prioritisation: **P0** = without it the manuscript does not survive review; **P1** = takes it from
"correct" to "good"; **P2** = comfort and ambition.

### P0 — To do before any further circulation (≈ 1 to 2 weeks, with no new collection)

**P0-1. Redo the validation with honest spatial blocks, and publish the ablation table.**
*Why:* this is the point on which the study is currently attackable in one sentence.
*How:*
- Replace the `round(3)` groups by **spatial blocking ≥ 600 m** (2 × buffer radius) or, better,
  a *buffered leave-one-out* (exclude from training every point within 300 m of the tested point).
  `sklearn.model_selection.GroupKFold` on a block identifier computed in UTM, or `spacv`.
- Publish **four baseline rows** in the same table, under the exact same protocol:
  ① global mean · ② mean per site · ③ mean per (site × hour) · ④ `dist_road_m` alone
  (linear regression) · ⑤ IDW / ordinary kriging on the measurements · ⑥ full LightGBM.
- Add a **feature ablation**: LightGBM without morphology, without hour, etc.
- Add **95 % bootstrap CIs** on R² and MAE, resampling **by spatial block**.
*Success criterion:* one can write a sentence of the form *"morphology contributes ΔR² = X
[95 % CI] beyond a site × hour model"*, whatever the value of X.
*Accepted risk:* ΔR² may be small. That is not a failure — it is a result, and
exactly the kind of result the cited survey paper calls for.

**P0-2. Reformulate the metric and the comparisons to standards.**
- Rename the target everywhere to **`L_Aeq,25s` (instantaneous proxy, uncertified smartphone)**, never
  bare "dB", never "LAeq" without a duration subscript.
- **Remove L_den / L_night from the thresholds table** or move them into a box marked "for public
  health context only, not comparable to our quantity".
- Reformulate QCVN exceedances as **"rate of instantaneous samples above the threshold"**,
  never as "regulatory exceedance", and attach the calibration uncertainty to it.
- Remove the Barcelona row from the performance table, or isolate it with the warning of §4.3(f).

**P0-3. Anchor the absolute calibration.** *(1 day, low cost)*
- Borrow a **class 1 or class 2 sound level meter** (VinUniversity civil/environmental engineering
  lab, or rental) or a **94 dB / 1 kHz acoustic calibrator**.
- Protocol: 3 phones + reference side by side, **≥ 20 minutes of simultaneous L_Aeq,1min**, in
  **3 environments of contrasting levels** (~50, ~65, ~80 dB) — not a single point, so as to capture
  **non-linearity** in level.
- Fit a per-phone correction: `L_ref = a·L_phone + b`, publish `a`, `b`, R² and the residual standard
  deviation. Carry it into `CALIBRATION_OFFSET` (to be generalised into an affine correction).
- **Characterise floor and saturation**: the quietest achievable point and a point > 90 dB to locate
  the onset of compression.
*Success criterion:* a sentence of the form *"after correction, the residual discrepancy against the
reference sound level meter is ±X dB (1σ) over the 50–85 dB range"*.

**P0-4. Clean up the state of the repository.**
- **Delete** `outputs/hanoi/hanoi_noise_map.*`, `hanoi_heatmap.html` and
  `outputs/gama_inputs/noise_map.csv` (unvalidated Bach Khoa artefacts), or move them into an
  `outputs/deprecated/` with a README explaining why.
- **Remove cells 1-7 of notebook 08** (Bach Khoa grid) and **archive notebook 09**:
  `export_gama_zones.py` is henceforth the only legitimate producer of `outputs/gama_inputs/`.
- Have notebook 08 write an `outputs/models/metrics.json`, and have `build_report.py` **read** that
  JSON. No more hardcoded metrics.
- Update page 8 "Next steps" of the PDF.
- Align the GPS filter with the protocol: `accuracy < 15 m` (and publish the distribution plus the
  number of points discarded).

**P0-5. Publish the dataset.**
- Commit `measurements.csv` (363 rows, collectors pseudonymised as C1/C2/C3) **into the repository** —
  it is a few tens of KiB, there is no reason to exclude it.
- Deposit on **Zenodo** (dataset + DOI): measurements, `vehicle_counts.csv`, construction register,
  XLSForm files, cleaning script. The raw videos stay outside the repository (GDPR/privacy).
- Add an **ethics statement** (VinUniversity IRB status) and a licence (CC-BY-4.0 for the data,
  MIT/Apache for the code).

### P1 — To reach a solid academic level (≈ 4 to 8 weeks, collection included)

**P1-1. Targeted additional campaign — priority to the gaps, not to volume.**
The problem is not "363 is few": it is *where* and *when* they are. Priority order:

| Target | Indicative volume | Why |
|---|---|---|
| **Night 22:00–05:00** | ≥ 60 points, ≥ 3 nights, all 3 sites | currently 2.8 %, zero between 00:00 and 05:00; it is the period with the strictest threshold |
| **Repeated fixed points** | **15-20 points**, each measured **≥ 6 times** at different hours/days | Enables variance decomposition (§P1-2) — the highest scientific gain per hour of fieldwork |
| **A 4th and a 5th typology** | ~60 points each | Industrial / peri-urban / quiet residential. Without a new typology, leave-one-site-out will stay at n=3 and stay negative |
| **Weekend** | ~50 points | Current coverage "light", unquantified |
| **Hourly gaps** 09:00, 14:00, 16:00, 19:00–21:00 | ~40 points | The hourly profile is a central deliverable of the report |

**Metadata that must be added to the v3 form:**
`point_id` (for repeated fixed points) · `duration_s` (actual integration duration) ·
`phone_model` · `height_m` · `windscreen` (yes/no) · `road_surface` (dry/wet) ·
`wind_local` (pocket anemometer, ~€15) · `street_width_m` and `facade_height_m` (canyon ratio) ·
`dist_to_road_m` **in metres** (keep the class as a fallback) · `L_Amax` and `L90` if the app shows
them (Decibel X offers them: two free and highly informative features).

**What must also be removed from the protocol:** forbid measuring in rain and in wind
> 5 m/s (ISO 1996-2), and document the minimum distance to façades (≥ 3.5 m) to avoid
reflections.

**P1-2. Quantify the R² ceiling instead of asserting it.**
With the repeated fixed points of P1-1: variance decomposition
`σ²_total = σ²_between-points + σ²_within-point`. The maximum R² achievable by *any* spatial model
equals `σ²_between / σ²_total`. This turns the report's soft sentence ("±5 dB
irreducible, ceiling ~0.6") into a measured result, and it **adds value to** the R² obtained instead of
suffering it. A high-yield addition for a manuscript.

**P1-3. Move from blind LUR to a hybrid physics + ML model.**
This is the most structuring recommendation, and the repository's name invites it: use
**NoiseModelling** (UMRAE/Cerema, open source, GPL, **CNOSSOS-EU** engine, native OSM inputs,
GIS output). Target architecture:

```
OSM (roads + buildings + heights)
        │
        ├─► NoiseModelling / CNOSSOS-EU ──► physical L_Aeq per receiver
        │      (emission Q,v by class · divergence · ground effect ·
        │       diffraction/building screening · façade reflections)
        │                                          │
        └─► morphological features ────────────────┤
                                                   ▼
                       LightGBM on the RESIDUAL (measurement − physics)
                                                   │
                                                   ▼
                                    final map = physics + corrected residual
```

Benefits:
- The map regains the **fine resolution** (façade vs courtyard, screening effect) that the 300 m buffer
  destroys.
- The model becomes **extrapolable** to an unmeasured district, since physics does not depend on the
  sample — which directly answers the negative leave-one-site-out R².
- The comparison **physics only / ML only / hybrid** becomes a results section in its own right,
  and that is exactly the kind of contribution the survey paper calls for.
- Building heights missing from OSM can be filled with `building:levels` × 3.2 m, or with
  a free DSM (Copernicus DEM 30 m as a fallback).

*If NoiseModelling is judged too heavy for the time available:* implement at minimum a simplified
physical layer (line source per road weighted by the OSM `highway` class, divergence
`−10·log₁₀(d)` for a line source, and a building visibility mask). Even crude, it will provide
a spatial contrast that the current 4 features cannot produce.

**P1-4. Redo the video counting on the right quantity.**
- Move to **tracking** (`ultralytics` + ByteTrack/BoT-SORT) and count **line crossings**
  → **flow Q in veh/h per class**, the quantity CNOSSOS requires.
- Estimate **speed** via a simple homography (2 ground markers of known separation per site).
- Move to **YOLOv8m/l or YOLO11**, `imgsz` 960–1280, `conf` ~0.25 — the nano model at 640 px
  massively under-detects motorcycles.
- **Validate the detector**: reference manual count on **10 videos** (one per site and per
  time slot), publish precision / recall / MAPE per class. **Without this validation, do not publish
  the modal shares.**
- Motion filter to exclude parked vehicles (already in the ROADMAP).
- Tighten video↔measurement matching from 300 s to **60 s**, and publish the distribution of gaps.
- *Once flow and speed are available*, `calibrate_emissions.py` can become identifiable again —
  or, better, calibration is no longer needed: CNOSSOS provides emission laws
  per vehicle class and per speed, and we **verify** them against our measurements instead of inventing them.

**P1-5. Make the construction calibration reliable.**
- *Matching* of "construction" and "no construction" points on `dist_to_road`, hour and
  sub-zone, before computing the difference. Or a linear model with those covariates.
- **Permutation test** + bootstrap CI on the difference, and publication of the effective n.
- **Remove the circular backfill**: compare only on points where `construction_nearby` was
  *actually entered*, and treat the value derived from `class` as a distinct variable.
- Explicit dB-distance transect: the protocol already provides for "2-3 measurements while walking
  away" — use them to **fit** the observed attenuation law instead of imposing 20·log₁₀.
- Attach an error bar to the +2 dB in the `.gaml` and run a **sensitivity analysis**
  (low / central / high scenario).

**P1-6. Correct the GAMA physics.** The two points of §4.7 (traffic/residual decomposition for
the `10·log₁₀(k)` factor, local application of the zone 30). Then implement **tier 2 of
PLAN.md** — the pedestrian agents and the **exposure dose**: that is what distinguishes an
agent-based simulation from an animated map, and it is what produces an indicator (population
exposure) that the map alone does not give.

### P2 — Ambition and bonus

- **Model benchmark** (task already in the ROADMAP, status to clarify with the supervisor):
  LightGBM vs Random Forest vs regularised linear regression vs the Barcelona LSTM/ST-GNN. Note:
  temporal models (LSTM, ST-GNN) **require continuous series** — so the
  "phone left in place for a day" task in the technical backlog is their **prerequisite**, not a bonus.
- **Long time series**: 3–5 points with a phone recording continuously over 24 h
  → a true hourly L_Aeq, computable L_den/L_night, and the means to **quantify the bias** of the
  25 s sample relative to the hourly L_Aeq. High yield, near-zero cost.
- **Audio as a feature.** 363 clips of ≥ 10 s are already collected and serve only for QC.
  Embeddings (YAMNet / PANNs / VGGish) would give an objective classification of sources, replacing
  the declarative category — and could become model features.
- **Meyer & Pebesma style spatial cross-validation** with an **area of applicability** (AOA) map:
  mask on the final map the cells where the model extrapolates outside its feature space.
  Visually compelling and methodologically unimpeachable.
- **Uncertainty map** published beside the level map (quantile LightGBM, or ensemble variance).
  A noise map without an uncertainty map is hard to publish today.

---

## 6. What to write (and no longer write) in the manuscript

**To reformulate:**

| Current wording | Defensible wording |
|---|---|
| "R² 0.45 under honest spatial cross-validation" | "R² 0.45 with 110 m blocks; that protocol remains contaminated by the overlap of the 300 m buffers. Under 600 m blocking: R² = … ; under leave-one-site-out: −0.68 to +0.21" |
| "39 % of measurements exceed QCVN" | "39 % of instantaneous samples exceed the QCVN daytime threshold. Our quantity is not the standard's reference L_Aeq and our instrumentation is not certified: this rate is indicative, not regulatory" |
| "WHO day 53 / night 45" | to be removed from the thresholds table; mention L_den/L_night only in a public health discussion |
| "better than the Barcelona reference R² 0.61" | to be removed: non-comparable targets (4-month L_Aeq, class 1 sensors) |
| "±5 dB irreducible, R² ceiling ≈ 0.6" | replace with the **measured** ceiling from the variance decomposition (P1-2) |
| "Transfer fails, direct training works" | "Cross-city transfer fails (R² −1.26). Direct training works **within the sampled typologies** and does not yet generalise to an unseen typology" |

**To foreground — these are your real contributions:**
1. The documented negative result on cross-city transfer, with Barcelona as a control.
2. The non-identifiability of vehicle emissions from a video density count — a
   useful negative result, and a lesson in experimental design.
3. A reproducible smartphone field protocol, with open forms and deposited data.
4. The complete chain measurement → model → hourly map → ABM simulation with an explicit status for
   each layer.

---

## 7. Summary of figures verified during the audit

| Quantity | Value | Source |
|---|---|---|
| Total measurements / sites | 363 — OP 184, HK 99, VT 80 | `hanoi_exceedances.csv`, `*_measurements.dbf` |
| Night measurements (21:00–06:00) | **10 (2.8 %)**, of which 0 between 00:00 and 05:00 | `hanoi_exceedances.csv`, hourly histogram |
| Hours with no measurement at all | **09:00** (and near-empty 20:00–23:00) | `validation_simulation.csv` |
| Measured range / dispersion | 47.0 – 88.0 dB · σ = 7.10 dB | `validation_simulation.csv` |
| Simulated dispersion | σ = 5.52 dB (map flatter than reality) | idem |
| GAMA validation *in-sample* | n=360 · bias −0.52 · MAE 3.68 · RMSE 4.98 · r 0.719 · 74 % within ±5 dB | audit recomputation |
| Baseline "mean per site" (LOO) | R² 0.03 · MAE 5.79 dB | audit computation |
| **Baseline "site × hour" (LOO)** | **R² 0.27 · MAE 4.79 dB** | audit computation |
| LightGBM model, CV 110 m | R² 0.45 · MAE 4.2 dB | notebook 08 outputs |
| Model, leave-one-site-out | R² **+0.21 / −0.68 / −0.37** | `build_report.py` (PERSITE) |
| Size of the "spatial" CV blocks | ~111 m × 104 m, vs feature buffer **300 m** | notebook 08 |
| Bach Khoa grid (unmeasured) | 8 640 cells, lat 20.992-21.019 / lon 105.829-105.858 | `hanoi_noise_map.csv` |
| 3-site grid (GAMA) | 5 587 cells at 40 m × 17 hours | `noise_points.dbf` |
| Vehicle emissions (NNLS) | motorcycle / car / HGV = **0.0** — not identifiable | `emission_calibration.csv` |
| Calibrated construction source | 64.7 dB at 56 m, from a median difference of **+2.0 dB** (n=32 vs 152) | `emission_calibration.csv`, `.gaml` |
| Sunbird reproduction (notebook 06) | R² 0.25 · MAE 8.17 dB, on the `small` config = **1 000 rows**, random split | notebook 06 |
| Calibration offsets applied | 0.0 / 0.0 / 0.0 — no absolute reference | `prepare_field_data.py` |

---

## 8. Conclusion

The study **stands up as engineering work**: the chain is complete, the code is clean, and
the intellectual honesty displayed in the scripts (refusing to invent emissions, explicitly
noting the in-sample character of a validation) is above what one reads in many
published articles.

It **does not yet stand up as generalisable scientific work**, for three cumulative reasons:
metrology not anchored to an absolute reference, a cross-validation that leaks and masks a negative
leave-one-site-out, and a map whose effective resolution (300 m) is incompatible with
the object it claims to represent.

The shortest path to a defensible study does not run through "more measurements": it runs through
**P0-1** (honest validation + ablation), **P0-3** (one day with a reference sound level meter) and
**P0-2** (reformulating the metric and the standards). Those three actions, achievable in one to two
weeks without returning to the field, turn an attackable figure into a solid
contribution — including if the result becomes less flattering. Only then do **P1-3** (CNOSSOS/
NoiseModelling physical layer) and **P1-1** (night + repeated fixed points + a 4th typology) take
the work to publication level.

The negative result on cross-city transfer and the non-identifiability of emissions from
video counting are, as things stand, the two most original contributions in the record. They should be
owned and put at the centre, not treated as accidents along the way.

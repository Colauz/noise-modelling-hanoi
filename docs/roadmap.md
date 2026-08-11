# Roadmap

*Updated 5 August 2026 — pivot to a methodological study*

## The pivot (5 August 2026)

No professional sound level meter available, **field campaign definitively
closed**. The project therefore no longer seeks to produce a reference noise map
for Hanoi — it cannot, and claiming otherwise would be indefensible. It becomes a
**methodological study** on the data in hand: what a low-cost smartphone protocol
allows one to establish, what it does not, and why. The two negative results
obtained become the core of the contribution.

Basis: `docs/audit/scientific-audit.md` (audit of 5 August 2026).

**State**: 363 measurements / 3 sites · 147 videos counted by YOLO · no robust
weather effect · noise grid over the 3 measured zones × 17 hours · GAMA simulation
corrected · 8-page report wired to `metrics.json`.

## V2 (5 August 2026) — what improving the algorithms produced

V2 was meant to improve two things: the video counting (object tracking instead of
density) and the model (hybrid physics + ML architecture). Both were built. **The
outcome is that algorithmic elaboration improves nothing under honest validation,
and that the simplest of the three models — three physical parameters — is the one
delivered.**

R² by protocol (n = 363, 95 % block-bootstrap CI, `models/model_comparison.md`):

| Model | Block-CV 600 m | **Buffered LOO (reference)** | Leave-one-site-out |
|---|---|---|---|
| Site × hour table | −0.008 | −0.419 | −0.058 |
| log(dist_road) regression, 2 param. | 0.221 | 0.200 | 0.189 |
| **Physical kernel, 3 param. — DELIVERED** | 0.255 | **0.246** | **0.222** |
| LightGBM v1 (6 features) | 0.304 | 0.137 | 0.029 |
| LightGBM v2 (8 features, road classes separated + cyclic hour) | 0.332 | 0.099 | −0.035 |
| Hybrid (physics + ML on the residual) | **0.395** | 0.123 | 0.035 |
| Conservative hybrid (constrained residual) | 0.378 | 0.144 | 0.106 |

**The ranking inverts almost exactly between the first column and the other two.**
The models that win the permissive split are the ones that lose the strict split,
monotonically. That is the signature of a capacity learning the sample's spatial
autocorrelation, not physics.

- The **contribution of ML on the residual** is worth ΔR² +0.140 under block-CV,
  but **−0.123** under BLOO and **−0.187** under leave-one-site-out. The hybrid
  architecture we recommended ourselves in the conclusion of `negative-results.md`
  is therefore **tested and rejected at this sample size**, not deferred to future
  work.
- The **better feature engineering degraded** pure ML: separating road classes and
  encoding the hour as sin/cos gains 0.03 under block-CV and loses 0.04 under BLOO.
- Constraining the residual (5 leaves, 120 trees, deprived of the distances)
  recovers part of the loss (0.144 / 0.106). The MEANING of that trade-off is the
  diagnosis: what the free residual was learning was not missing physics.

**The delivered model is chosen by the code**, not by hand:
`04_evaluate_models.py` keeps the best R² under the reference protocol among six
candidates fixed in advance, writes `meta.delivered_model` into `metrics.json`, and
`07_export_gama_inputs.py` reads the `apply_residual` flag. The published map
therefore cannot silently inherit a model that only wins on a permissive split.

### Traffic: flow does not rescue the correlation either

The 147 videos were reprocessed with **object tracking** (ByteTrack, 10 fps) and
**line-crossing counts** — the recommendation we made ourselves in §5.x.

- Counts are now physically coherent: the residence time implied by Little's law
  (4.7 s) is of the same order as the one observed on the trajectories (7.6 s). The
  first counting rule written implied 0.3 s, i.e. 60–90 m/s — absurd.
- **The correlation remains negative**: r = −0.11 for flow against −0.15 for
  density. Motorcycle flow is uncorrelated (r = −0.004). NNLS regression on energy
  per *pass* still brings motorcycle and car back to zero.
- A heavy-vehicle coefficient comes out non-zero (46.8 dB/pass) but it is fitted on
  **4 videos out of 147**, i.e. 0.4 % of total flow, with r = +0.02: it is an
  artefact of the non-negativity constraint, not an identified emission. **Do not
  cite it.**
- **One structured exception**: Vinh Tuy, the only transit-corridor site, is the
  only positive one — and it improves with flow (r = +0.22 → +0.30). That is the
  direction physics predicts: where traffic really flows, throughput tracks level.

What is missing remains what we listed: **speed** (no ground homography) and
**source–receiver distance** (non-georeferenced camera field). Moving to flow was
necessary — it is the difference between a structurally wrong quantity and an
incomplete one — but it is **not sufficient**.

### Three bugs found while calibrating the counting (for the record)

1. Dead band in **absolute pixels** although the videos have two resolutions
   (1080×1920 and 1280×720): it was 4 % of the height in one case, 13 % in the
   other.
2. ByteTrack **reuses its identifiers** on our sparsely populated scenes → 109
   veh/min on a video showing 0.6 vehicles per frame. Capped at one crossing per
   direction per trajectory, checked against Little's law.
3. **Horizontal crossing line imposed** although vehicles cross the field
   laterally: 14 of the 19 `VID_*` videos came out at zero flow. Orientation is now
   chosen per video, perpendicular to the dominant motion, on amplitudes
   **normalised by the image dimension** (comparing raw pixels favours the longer
   side). Zeros fell from 27/145 to 3/147.

## The V1 result (5 August 2026) — retained, but BROADENED by V2 above

> **Read the V2 section first.** What follows remains exact: a one-variable
> regression beats the 6-variable LightGBM. But V2 showed that this is not the
> strongest formulation — the 3-parameter physical kernel beats the one-variable
> regression *as well*, and beats every learned model, including the hybrid. That
> is the version the paper defends (§5.z).

The scripts ran on the real data. The V1 ablation verdict was:

> **A simple physical regression on `log(dist_road)` — two parameters, one
> variable — generalises better than our 6-variable LightGBM model. Urban
> morphology aggregated within a 300 m radius adds no measurable gain beyond that
> single distance term.**

R² by protocol (n = 363, 17 blocks, 95 % bootstrap CI, `models/model_comparison.md`):

| Model | inputs | Block-CV 600 m | **Buffered LOO 300 m** | Leave-one-site-out |
|---|---|---|---|---|
| Site × hour table | 0 spatial | −0.008 | −0.419 | −0.058 |
| **Regression on log(dist_road)** | **1** | 0.221 | **0.200** | **0.189** |
| LightGBM morphology only | 4 | 0.153 | 0.041 | 0.007 |
| LightGBM morphology + time | 6 | **0.304** | 0.137 | 0.029 |

Three readings:

1. **The ML lead is an artefact of the permissive protocol.** LightGBM only leads
   under block-CV 600 m. Under buffered LOO (reference protocol, exclusion radius =
   feature radius) the order inverts; under leave-one-site-out the ML collapses by
   a factor of 6 (0.029) while the regression moves by 0.03 across all three
   protocols. It is the only model whose CI excludes zero everywhere.
2. **The 300 m morphological aggregates have a NEGATIVE marginal contribution.**
   Adding built ratio, road density and intersections to `dist_road` loses 0.07 /
   0.16 / 0.18 of R² depending on the protocol. The 300 m disc averages away the
   canyon geometry that governs propagation and stays autocorrelated between
   neighbouring points: it contributes variance, not information.
3. **What remains of the ML is time, not space.** The gap between the full model
   and morphology-only under block-CV (0.304 vs 0.153) is carried by the hour. A
   real effect, but not a spatial one: it does not help predict an unmeasured
   place, which is precisely what a map is for. Under leave-one-site-out the
   "time only" ablation is itself negative (−0.139).

Written up in §5.z of `docs/negative-results.md`. **The R² 0.45 displayed until
July 2026 is an artefact of the CV grouped on 110 m cells** (smaller than the 300 m
feature radius): it must no longer appear anywhere.

## Corrections applied (5 August 2026)

| # | Correction | Deliverable |
|---|---|---|
| 1 | **Honest CV**: 600 m spatial blocks + buffered leave-one-out 300 m + leave-one-site-out, replacing the `GroupKFold` on 110 m cells that leaked | `scripts/04_evaluate_models.py` |
| 2 | **Baselines + ablation**: 8 models on the same splits, including the `site × hour` table with no spatial variable; 95 % block-bootstrap CI | `models/model_comparison.md` |
| 3 | **End of hand-copied metrics**: the report reads `metrics.json` and refuses to run without it | `scripts/10_build_report.py` |
| 4 | **Metrological reframing**: target renamed `L_A,25s`, "relative, not absolute" status accepted, WHO `L_den`/`L_night` values removed everywhere, QCVN exceedances presented as a descriptive statistic + bias sensitivity | `docs/metrology.md`, `10_build_report.py`, `hanoi_noise.gaml` |
| 5 | **Anchoring on instrumented literature**: bounding of the plausible absolute bias by stratified comparison against Phan et al. 2010 (Hanoi, RION NL-21/22) and Gelb & Apparicio 2019 (HCMC, dosimeters) | `scripts/06_anchor_literature.py`, `docs/references.bib` |
| 6 | **GAMA physics corrected**: `10·log10(k)` and the −3 dB "zone 30" now apply only to the share of energy attributable to traffic, and the zone 30 is bounded to 150 m from a road | `simulation/gama/hanoi_noise.gaml` |
| 7 | **Map refocused on the studied area**: the "Bach Khoa" artefacts (a district with no measurement at all) are archived; a single producer for the GAMA inputs | `docs/archive/bach-khoa/`, notebook 09 neutralised |
| 8 | **Negative results given value**: three Discussion subsections written, including §5.z (`dist_road` > ML) which becomes the central argument | `docs/negative-results.md` |
| 9 | **Traffic recounted**: the 147 videos reprocessed under YOLOv8, `vehicle_counts.csv` regenerated, `fleet_by_hour.csv` rebuilt, page 5 of the report restored | `scripts/02_count_vehicles.py`, `results/report/report.pdf` |

### Verification of the GAMA correction (Ocean Park, 17:00)

| Cell | Base | Traffic ×3, old | Traffic ×3, corrected |
|---|---|---|---|
| quietest | 53.3 dB | 58.1 dB | **53.3 dB** |
| median | 65.4 dB | 70.2 dB | 69.4 dB |
| loudest | 78.6 dB | 83.4 dB | 83.3 dB |

The old formula announced −7.0 dB of zone mean for pedestrianisation; the corrected
formula gives **−3.5 dB**. The benefit of the scenarios was overstated by a factor
of two. Invariant checked: at k = 1 with no mitigation, the map is identical to the
predicted map.

## What remains

### 🔴 Blocking before any release

- [x] **Run the scripts on the real data.** Done 5 August 2026:
      `02_count_vehicles.py` (147 videos) → `04_evaluate_models.py` →
      `06_anchor_literature.py` → `07_export_gama_inputs.py` →
      `10_build_report.py`. Every published metric now comes from a real run.
- [x] **Report the real figures** in `docs/negative-results.md`: done, §5.z
      contains the full three-protocol table.
- [ ] **Check Phan et al. 2010 against the PDF** (VinUniversity library): the
      `L_den` 70–83 dB values come from secondary sources, status `to_check` in
      `scripts/06_anchor_literature.py`. Switch to `verified` once confirmed.

### 🟡 For the manuscript

- [ ] **Writing**: Methods (protocol + metrology), Results (model comparison),
      Discussion (the two negative results), Limitations.
- [ ] **Ethics statement**: VinUniversity IRB status for the 147 videos filmed in
      public space (faces, plates). Required by a Q1 journal.
- [ ] **Data deposit**: `measurements.csv` (pseudonymised collectors) in the
      repository + Zenodo with a DOI. CC-BY-4.0 for data, MIT for code.
- [ ] **YOLO detector validation**: reference manual count on ~10 videos,
      precision/recall/MAPE per class. **Without it, do not publish the modal
      shares.**

### ⏸️ Deferred or abandoned

- **LSTM / ST-GNN benchmark (Barcelona)** — missing prerequisite: those models
  require continuous time series, which we do not have. To be reclarified with the
  supervisor.
- **Demolition audio (10 h)** — outside the scope of the pivot.
- **CNOSSOS / NoiseModelling physical layer** — still outside the time budget, but
  **the central result above makes it the logical continuation of the project
  rather than a mere option**: if a two-parameter distance term already beats the
  ML, then a real physical propagation kernel corrected by a locally learned
  residual is the indicated architecture. To be carried into *future work* at the
  top of the list, not at the end of the section.
- **GAMA pedestrian agents (tier 2 of the plan)** — not implemented.

## Rules

- Videos and raw data outside git (`data/raw/` ignored).
- No commit or push without an explicit request.
- No metric hardcoded in a deliverable: everything goes through `metrics.json`.
- No prediction published outside the envelope actually sampled.

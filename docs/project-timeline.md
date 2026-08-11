# Project timeline

*How this project got to where it is: what was decided, when, and why. Chronology
and reasoning only — no results.*

**Results, figures and open tasks live elsewhere, and only there:**

| You want | Read |
|---|---|
| The R² tables and the model comparison | [`../models/model_comparison.md`](../models/model_comparison.md) |
| The chain, its assumptions and its limits | [`methodology.md`](methodology.md) |
| The three negative results, written up | [`negative-results.md`](negative-results.md) |
| What is left to do, ranked | [`handover.md`](handover.md) |
| The audit that triggered the pivot | [`audit/scientific-audit.md`](audit/scientific-audit.md) |

This separation is deliberate. Until August 2026 the same R² figures appeared in
three documents at once, which is three chances for them to diverge. Every number
now has exactly one home.

---

## June 2026 — reproduce, then transplant

The project started from the [Sunbird Urban Noise Uganda 61K
dataset](https://doi.org/10.1038/s41597-026-06658-w) and its *Scientific Data*
descriptor. The plan was straightforward: reproduce the paper's figures, train a
morphology→level surrogate on Uganda, and transfer it to Hanoi, using a local field
campaign only to calibrate an offset.

A parallel review of the field, *Environmental Noise Modelling in Hanoi: A
Comparative Review of Old and New Urban Fabrics*, was written in June to situate
the work.

## June–July 2026 — the field campaign

Three collectors, three consumer smartphones running a sound meter application,
ODK Collect against a KoboToolbox server. Three deliberately contrasted urban
typologies: Ocean Park (new development), Hoan Kiem (old quarter), Vinh Tuy
(transport corridor). 363 measurements between 10 June and 22 July, plus 147
timestamped traffic videos.

**Decision: cross-calibrate the phones against each other.** No reference
instrument was available and none could be borrowed. The consequence — levels are
relative, not absolute — was accepted at the time and became the constraint the
whole methodology is built around. See [`metrology.md`](metrology.md).

## July 2026 — the first architecture, and the figure that was later withdrawn

A LightGBM model trained on the Hanoi points scored R² = 0.45 under what was then
described as honest spatial cross-validation. A GAMA simulation was built on top of
it, and a project-update deck presented that figure.

**That score was later found to leak** and was withdrawn. The grouping was on
~110 m cells while the features aggregate over 300 m. The deck and the map that
carried it are in [`archive/`](archive/).

## 5 August 2026 — the audit and the pivot

An internal scientific audit went through the whole chain as a reviewer would. It
found three cumulative problems: metrology with no absolute anchor, a
cross-validation that leaked and masked a negative leave-one-site-out, and a map
whose effective resolution was incompatible with what it claimed to represent.

**Decision: pivot to a methodological study.** No professional sound level meter
would become available, so the field campaign was closed for good. The project
stopped trying to produce a reference noise map for Hanoi — it could not, and
claiming otherwise would have been indefensible — and became a study of what a
low-cost smartphone protocol can and cannot establish. The negative results became
the contribution rather than an embarrassment.

Nine corrections were applied the same day: honest cross-validation with three
protocols, baselines and ablation with bootstrap intervals, metrics read from
`metrics.json` instead of copied by hand, the metrological reframing to `L_A,25s`,
literature anchoring in place of the impossible calibration, corrected GAMA scenario
physics, the map refocused on the sampled envelope, and the traffic recount.

## 5 August 2026 — V2, and the result that reversed the design

V2 was meant to improve two things: video counting (object tracking instead of
density) and the model (a hybrid physics + ML architecture that the team had itself
recommended in an earlier draft).

**Both were built, and both were rejected by the evidence.** The elaborate
architecture wins the permissive split and loses the strict ones; the simplest of
the models — three physical parameters — is the one delivered. The hybrid is
therefore reported as *tested and rejected at this sample size*, not deferred to
future work.

**Decision: let the code choose the delivered model.** `04_evaluate_models.py`
takes the best score under the reference protocol among candidates fixed in
advance and writes the choice into `metrics.json`; the export reads a flag. This
was a direct response to the audit: the published map must not be able to inherit,
silently, a model that only wins on a permissive split.

Three counting bugs were found while calibrating the tracker — a dead band in
absolute pixels across two video resolutions, track-ID reuse producing impossible
flows, and an imposed horizontal crossing line on videos where vehicles cross
laterally. They are recorded in [`handover.md`](handover.md), because each cost
real time and each is easy to reintroduce.

## 6 August 2026 — the simulation corridor

Measured flow was being spread uniformly over every street of the exported zone,
which extends 400 m beyond the survey envelope, leaving the Hoan Kiem lake loop
empty although every video had been filmed there. Flow is now injected only within
150 m of a measurement point — also the more honest choice, since nothing was
measured 400 m from the lake.

## 11 August 2026 — restructuring for handover

The repository was reorganised for publication and handover: a documented layout,
an importable package, numbered pipeline scripts, a reproducible environment,
tests aimed at the failures the project actually had, and licensing. The retracted
artefacts were archived with their reasons rather than deleted.

## What was tried and abandoned

| Abandoned | Why |
|---|---|
| **Cross-city transfer as the method** | It failed: R² < 0 on Hanoi even with convention-invariant features. It survives as a negative result, not as a technique |
| **Barcelona benchmark (LSTM / ST-GNN)** | Those models need continuous time series, which this campaign does not produce. `scripts/experiments/barcelona_transfer.py` is kept as a documented dead end |
| **Emitter agents in GAMA** | No per-street flows, modal shares, speeds or signal cycles to calibrate them with, and nothing to validate them against |
| **Demolition audio** | Out of scope after the pivot |
| **Vehicle emission coefficients** | Non-negative regression returns zero for motorcycles and cars: they are not identifiable from these data |
| **GAMA pedestrian agents (tier 2)** | Never implemented; still the most valuable extension of the simulation |

## Working rules that came out of all this

- Raw data and videos stay outside git.
- No metric is hardcoded in a deliverable: everything passes through
  `models/metrics.json`.
- No prediction is published outside the envelope actually sampled.
- The delivered model is selected by code, under the reference protocol.
- Retracted work is archived with its reason, never silently deleted.

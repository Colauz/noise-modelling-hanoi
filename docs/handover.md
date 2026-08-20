# Handover

*Written August 2026, at the end of a three-month research internship at
[AFFILIATION TO CONFIRM — CEI or COSMOS Lab], VinUniversity, Hanoi.*

**You are taking this project over tomorrow and want to know where to start.**
Read §1, run §2, then pick from §6.

---

## 0. The working principle: verify by executing, not by reading

**Every defect this project shipped was one that reading could not catch.**

The R² = 0.45 was withdrawn because a cross-validation split *looked* spatial. The
Bach Khoa map was published because a grid *looked* like it covered the study area.
The validation figures drifted for six days because an artefact *looked* current.
A renamed import broke the pipeline three times, and two of those survived review
because the reviewer was reading module headers. None of these is a careless
mistake; each is what happens when a check is a person looking at code instead of
a machine running it.

So the guards here execute. Each one exists because something got past a reading.

| Guard | What it runs | What it catches |
|---|---|---|
| `tests/test_cv_protocols.py` | asserts `BLOO_RADIUS_M >= FEATURE_RADIUS_M`, and that a 110 m buffer would still leak | the leak behind the withdrawn R² = 0.45 |
| `tests/test_grid_extent.py` | reads the published grid, checks every cell against the sampled envelope and against the retracted Bach Khoa extent | a map extended to unmeasured ground |
| `tests/test_features_extraction.py` | recomputes the morphology features and compares them element by element to the stored artefact | silent drift in the input to every published number |
| `tests/test_gama_fingerprint.py` | compares extracted **values**, never strings, between two dated fingerprints | a model edit that changes what the simulation loads |
| `tests/test_pipeline_end_to_end.py` | loads every numbered script for real; `-m slow` runs `make results` | a broken import, including one hidden inside a function |
| `Makefile` dependency rules | rebuilds a derived artefact when its input is newer | the validation that drifted from its grid |
| `make` environment check | fails legibly when the package is not importable | an obscure `ModuleNotFoundError` halfway through a target |

Two habits go with them, and they cost minutes:

- **Fingerprint before you change anything.** Before the restructuring, before the
  feature extraction, before translating the simulation's strings, a reference was
  captured and diffed afterwards. Every one of those diffs came back identical,
  which is the only reason those changes can be trusted. `tests/fixtures/` holds
  the two GAMA fingerprints, including the French one kept as the continuity trace.
- **Compare dates across the whole tree, not the file you are thinking about.**
  Comparing each artefact's last commit against its inputs' found **four** stale
  artefacts where one had been noticed by hand — and `report.pdf` and the dashboard
  were stale a level above, because `make results` did not build them.

If you add a step to the pipeline, add its dependency to the Makefile and a check
that runs. A rule nobody executes is a rule that will be broken without anyone
noticing, and this repository has the receipts.

---

## 0b. Open items — answers we never got

Every one of these is a **visible placeholder** in the repository rather than a
guess. A field marked "to confirm" is honest; a field filled in by judgement is
not. Tracked as GitHub issue *Complete author and affiliation metadata*.

| Item | Placeholder | Who holds the answer | If it never arrives |
|---|---|---|---|
| Affiliation: CEI or COSMOS Lab | `[AFFILIATION TO CONFIRM]` | Supervisor / VinUniversity | `CITATION.cff` and every paper byline stay unresolved. The June 2026 survey says *Center for Environmental Intelligence*; the team was told *COSMOS Lab*. They may nest rather than conflict |
| Lucas Zborowski's ORCID | `[ORCID]` | Lucas Zborowski | The citation record is not FAIR-complete; a Zenodo DOI would credit an unidentified author |
| Doanh Nguyen-Ngoc's title | `[TITLE TO CONFIRM]` | Doanh Nguyen-Ngoc | Acknowledgements and the title slide carry an unqualified name |
| Nguyen Thanh Quang: co-author or acknowledgement? | `contributor` + acknowledgement | Nguyen Thanh Quang | The default stands. It credits the contribution without claiming authorship nobody agreed to — the choice that wrongs no one |
| Video retention: custodian, location, deletion deadline | `[SUPERVISOR DECISION]` | Supervisor | 6 GB of unanonymised video with faces and plates sits with no owner and no expiry. **The most consequential gap on this list** |
| Publication status of the June 2026 survey | `[À VÉRIFIER]` | The two authors | It stays out of `HEAD` and is cited as an internal working document |


---

## 1. Where the project actually stands

The field campaign is **closed**. There was never a professional sound level
meter, so the project stopped trying to produce a reference noise map for Hanoi —
it cannot, and claiming otherwise would be indefensible — and became a
**methodological study on the data in hand**: what a low-cost smartphone protocol
can establish, what it cannot, and why.

Three results, all negative, all transferable:

1. **A three-parameter physical model beats every learned model built here**,
   including the physics+ML hybrid the team had itself recommended. R² = 0.246
   under buffered leave-one-out against 0.137 for a six-variable LightGBM. The
   ranking of seven models *inverts* between a permissive spatial split and two
   strict ones — the signature of learning spatial autocorrelation rather than
   physics.
2. **Cross-city transfer fails.** A morphology→noise model pretrained on Uganda
   scores R² < 0 on Hanoi even with convention-invariant features.
3. **Per-frame vehicle density carries no acoustic signal**, and switching to real
   flow (line-crossing counts) does not rescue the correlation either.

Everything else in the repository exists to support or to qualify those three.

**What is solid:** the evaluation framework (three CV protocols, baselines,
ablation, bootstrap CIs, code-driven model selection), the field protocol and its
metrological framing, the GAMA simulation with corrected physics, and the
retraction trail.

**What is fragile:** absolute levels (no reference instrument), the vehicle
detector (never validated), and anything that depends on the Uganda chain, which
is not reproducible on a fresh machine (§5).

---

## 2. Get it running in five commands

```bash
git clone https://github.com/Colauz/noise-modelling-hanoi && cd noise-modelling-hanoi
make setup
make features
make models
make results
```

`make features` needs the OSM extract in `data/interim/`, which is **not
published** because it is a dated snapshot of a moving database — see
[`data-sources.md`](data-sources.md). Ask the team for it, or re-download it and
accept that `built_area_ratio` will shift slightly.

Everything from `03` onwards runs from the two datasets versioned in
`data/processed/`. You do **not** need the raw Kobo export or the 6 GB of video.

For the simulation: open `simulation/gama/hanoi_noise.gaml` in GAMA and run
`hanoi_noise_sim`. It was last verified with gama-headless 2025.6.4 — three zones
load, 5 587 cells total.

---

## 3. Why the repository is shaped the way it is

Three constraints explain most of the layout, and breaking any of them will
quietly break the science.

**No metric is ever copied by hand.** `04_evaluate_models.py` writes
`models/metrics.json`; the report, the dashboard and the manuscript read it.
`10_build_report.py` refuses to run without it. If you find a number in a
deliverable that is not traceable to that file, it is wrong.

**The map never leaves the sampled envelope.** Three sites plus 400 m, 40 m grid.
A noise map was once published over Bach Khoa, a district with zero measurements,
using a model with a negative leave-one-site-out on two of three sites. It was
retracted — `docs/archive/bach-khoa/README.md`. `tests/test_grid_extent.py` now
fails if it happens again.

**The cross-validation buffer must not be smaller than the feature radius.**
Features are aggregated over 300 m. A `GroupKFold` on ~110 m cells leaked and
produced the R² = 0.45 that was advertised until July 2026 and then withdrawn.
`tests/test_cv_protocols.py` asserts `BLOO_RADIUS_M >= FEATURE_RADIUS_M`.

**Why `src/noise_hanoi/` exists**, in one sentence: `04_evaluate_models.py` used
to reach `morphology()` by putting `scripts/` on `sys.path` and importing a
sibling script by filename, and numbering the scripts broke that outright —
**a Python module name cannot start with a digit**. Shared code lives in the
package now; scripts read inputs, call the package, write outputs.

---

## 4. Technical debt, honestly

| # | Debt | Cost to fix | Consequence of leaving it |
|---|---|---|---|
| 1 | `04_evaluate_models.py` is 598 lines and still holds the three CV protocols, the bootstrap and six model definitions | 1–2 days to extract `validation.py` and `physics.py` | The most valuable code in the project is the least testable |
| 2 | The YOLO detector has **no** validation against manual counts | ~1 day for 10 videos, double-counted | **The modal shares cannot be published.** Precision, recall and MAPE per class are unknown, and two-wheeler under-detection is expected but unquantified. **This is the highest value-per-effort task left in the project**: one day of manual counting turns an open-ended limitation into a quantified uncertainty, and it is the input uncertainty of every downstream number. See `docs/methodology.md` section 2b |
| 3 | The Uganda chain (notebooks 01–06) is not reproducible: it expects `data/processed/uganda/*` which exists nowhere | Unknown; needs the HF download rerun | One of the three negative results rests on a chain nobody can replay |
| 4 | Two tests still to write: field cleaning, report guard | Half a day | Schema drift in `measurements.csv` would pass unnoticed |
| 5 | `run_dashboard.sh` duplicates `make dashboard` | 10 minutes | Two entry points that can disagree |
| 6 | `07_export_gama_inputs.py` is 414 lines doing grid, export, fleet, construction and measurement layers | 1 day | Hard to change one output without touching the others |
| 7 | Notebook 08 still computes as well as reports | Half a day | It should only read artefacts now that `03_build_features.py` exists |
| 8 | The Eclipse/GAMA `.project` at the repository root still filters a resource named `cache`, which became `data/interim/` | 1 minute, **for whoever next has GAMA open** | A stale filter in the IDE project. Left alone deliberately: editing Eclipse metadata blind, without being able to reopen the IDE and check, risks more than it fixes |

---

## 5. Traps that cost us time

- **The `.gitignore` negations did not work.** `measurements.csv` and
  `vehicle_counts.csv` were tracked from inside excluded directories and survived
  only through `git add -f`. Git cannot re-include a file whose parent directory
  is excluded. Fixed by re-including directories first. **Never `git add -f`.**
- **`#` only starts a comment at the start of a line in `.gitignore`.** A trailing
  comment becomes part of the pattern. This bit us while fixing the point above.
- **GAMA resolves relative paths against the model file**, so moving the model
  broke every input path. Inputs now sit in `simulation/gama/inputs/`, beside it.
- **ByteTrack reuses track IDs** on sparsely populated scenes, which produced
  109 veh/min on a video showing 0.6 vehicles per frame. Capped at one crossing
  per direction per trajectory, checked against Little's law.
- **A dead band in absolute pixels** across two video resolutions was 4 % of the
  height in one and 13 % in the other.
- **A joblib pickle only reloads under the exact scikit-learn and LightGBM
  versions it was written with**, and nothing recorded them. The two 11 MB
  `.pkl` Uganda models were therefore a time bomb for anyone cloning later. They
  were re-exported as LightGBM text boosters, verified identical to machine
  precision on 5000 rows before removal. Worth knowing: **the swap bought
  portability, not weight** — the text boosters are 10.3 MB against 10.4 MB of
  pickle, and the pickles remain in history, which was not rewritten. Anyone
  hoping to slim the repository by dropping large files from `HEAD` should expect
  the same result.
- **A derived artefact silently stopped matching its input.** The published
  validation validated a grid that had been regenerated after it. Found on
  2026-08-11 by re-running the script during an unrelated label translation, not
  by any check. The figures moved a long way -- MAE 3.79 -> 5.30 dB -- and the old
  ones were the flattering ones. Archived in `docs/archive/validation-2026-08-05/`.
  **The lesson is in the Makefile now, not in anyone's memory**: a derived artefact
  must declare its inputs as prerequisites so `make` rebuilds it.
- **An import inside a function escapes every static check.** Numbering the scripts
  broke `import prepare_field_data` three times over. Two of those escaped review
  because the checks only inspected module-level imports; the third was inside
  `main()`. A Python module name cannot start with a digit, so numbered scripts that
  need each other load by file path. The guard is now executable --
  `tests/test_pipeline_end_to_end.py` runs the chain -- rather than a habit of
  looking harder.
- **A forced horizontal crossing line** returned zero flow on 14 of 19 `VID_*`
  videos, because vehicles crossed the frame laterally.

---

## 6. What to do next, by priority

### Blocking before any public release

- [ ] **Confirm the affiliation**: CEI or COSMOS Lab. The June 2026 survey says
      *Center for Environmental Intelligence*; the team was told *COSMOS Lab*.
      Placeholders `[AFFILIATION TO CONFIRM]` are in `CITATION.cff`, this file and
      `data-sources.md`.
- [ ] **Missing identity fields**: Lucas Zborowski's ORCID, Doanh Nguyen-Ngoc's
      title, and whether Nguyen Thanh Quang is a co-author or an acknowledgement
      (currently `contributor` plus acknowledgement, the default that wrongs
      nobody).
- [ ] **Video retention decision**: custodian, location, deletion or anonymisation
      deadline — `[SUPERVISOR DECISION]` in `data-sources.md`.
- [ ] **Who holds the data of a public campaign.** The mobile app submits to a
      KoboToolbox account, and whoever owns that account holds the measurements —
      GPS positions and timestamps of strangers — and answers for them. It should
      be an institutional account, not a student's: a personal one leaves with its
      owner, which is the failure this handover exists to prevent. The account is
      not compiled into the app (`-Pnoisehanoi.koboUser`), so this is a decision to
      take rather than a change to make.
- [ ] **Consent and ethics for collection from the public.** The app shows a
      consent screen naming what is collected and who holds it, but a public
      campaign is a new collection campaign, and §7 lists the VinUniversity ethics
      committee as a prerequisite for one. The video collection went without a
      review and the repository says so; do not repeat that at a larger scale.
- [ ] **Where the GAMA server lives, if the simulation screen is to be used away
      from a laptop.** The app drives a `gama-server` over the network; today that
      is whichever machine is running `gama-headless.sh -socket 6868`. A
      demonstration needs it switched on and reachable; anything beyond that needs
      it hosted, with TLS — a release build will only accept `wss://`. The map
      screen needs none of this, which is the argument for keeping it.
- [x] **The 26 measurement points inside OSM building footprints — resolved.**
      13 sit inside footprints tagged residential, but none lies deeper inside one
      than the worst GPS accuracy of the campaign (max depth 7.1 m against 9.0 m),
      the ten `apartments` are 26–35 storey towers whose multipath explains the
      offset, and the field metadata records outdoor distances to the road.
      Full-precision coordinates published on that basis; see `data-sources.md`.
- [ ] **Recompile the June 2026 survey** from its LaTeX source with institutional
      addresses; the compiled PDF was removed from `HEAD` because it carries
      personal e-mail addresses.

### High value, low effort

- [ ] **Read the twelve journal quartiles off Scimago** and record each with its
      ranking year and subject category in `docs/literature-review.md`. About fifteen
      minutes in a browser. It cannot be automated: scimagojr.com returns HTTP 403 to
      automated requests, and a search engine's summary of a quartile is second-hand
      evidence, which this project classifies `grey` everywhere else.

- [x] **The Uganda transfer is now reproducible.** It was asserted in
      `literature-review.md` and in the header of `barcelona_transfer.py` and
      appeared in neither `metrics.json` nor `model_comparison.md`; a reader could
      not check it. `scripts/experiments/uganda_transfer.py` runs it from the two
      versioned boosters and Hanoi's own features, so it needs no Ugandan data.
      `02b_fetch_osm_extract.py` supplies the OSM extract that `03` requires and
      that nothing in the repository produced. What it finds is stronger than the
      R² < 0 that was claimed: see below.

- [ ] Validate the YOLO detector on ~10 videos (debt #2). Without it, no modal shares.
- [ ] Extract `validation.py` and `physics.py` from `04_evaluate_models.py` (debt #1).
- [ ] Write the two remaining tests (debt #4).

### What the transfer experiment actually shows

Worth carrying into the manuscript, because it is sharper than "transfer fails".

| | as delivered | mean difference removed | and rescaled (= r²) | r |
|---|---|---|---|---|
| Uganda 61K (v1) | R² = −15.8 | −2.17 | +0.151 | **−0.388** |
| Uganda invariant (v2) | R² = −8.1 | −0.96 | +0.004 | +0.066 |

Three readings, and the third is the one that matters.

**It is not a calibration offset.** The Kampala model predicts 26 dB below Hanoi,
but removing that difference still leaves R² negative. A recalibrated transfer
would not work either.

**v1 transfers anti-information.** Its correlation with Hanoi is *negative*: it
ranks quiet and loud the wrong way round, and the only way to extract anything
from it is to flip it. That is consistent with the convention artefact v2 was
built to remove.

**v2 removes the artefact and leaves nothing.** r = +0.066, Spearman +0.077. Not
wrong — empty. Even granted a free bias and a free slope, its ceiling is R² =
0.004.

Against which: `log(distance to road)` alone, fitted on those same 363 points,
reaches R² = 0.240, and the delivered physical kernel 0.246 under buffered
leave-one-out. **One locally fitted distance term carries more than a
61 000-point model trained in another city carries at all.**

### The two limits the manuscript should state plainly

Neither is fixable by code, and both will be asked about.

- [ ] **No absolute reference.** Three handsets were cross-calibrated against each
      other and against no standard, so every level in this project is relative.
      `metrology.md` argues this well, but a reviewer in acoustics will ask whether
      one afternoon beside a class 1 or class 2 meter was truly out of reach. It
      would convert "calibrated in relative terms" into "calibrated", and it would
      open the comparisons the paper currently forbids itself. The mobile app's
      calibration screen exists for exactly this and has never been used against a
      reference.
- [ ] **Three sites are three typologies.** §5.x already says it: the effective
      number of independent morphological configurations is close to three whatever
      the number of points, and three is not a basis for claiming coverage of a
      city. This bounds generalisation far more than the R² does, and it is the
      reason every published map stops at the sampled envelope.

### The scientifically indicated next step

- [ ] **A real propagation kernel: CNOSSOS-EU, via NoiseModelling.** This is no
      longer an optional extra. If a two-parameter distance term already beats a
      six-variable LightGBM, then a physical propagation model corrected by a
      locally learned residual is the architecture the data points at. It was out
      of time budget for a three-month internship; it should be first on the list
      now, not in a "future work" paragraph.

### Two directions the supervisor has pointed at, and what separates them

**A real propagation kernel — the continuation.** The figure circulated in August
2026 is Figure 2 of `bocher2019noisemodelling`, already in `references.bib`: the
direct path, first-order horizontal diffraction, and first- and second-order
specular reflections between a source and a receiver. It is precisely what a
three-parameter distance law does not model — it knows a distance, not the
buildings that block, reflect and bend around. This is the same next step already
named above, arriving from outside, and it belongs in the manuscript as future
work with that figure and a paragraph. Implementing CNOSSOS is months; citing
what is missing is a page.

**Acoustic event localisation — a different project, not a continuation.** The
sketched output — *vehicle collision 0.94, estimated location intersection X,
localization uncertainty ±12 m, detected independently by 5 sensors* — is the
"gunshot paper" and the sensor-placement problem from the original plan. It
cannot be done with this campaign's data, for a reason of physics rather than of
effort: localisation by time difference of arrival needs synchronised clocks, and
sound travels 343 m/s, so ±12 m demands agreement to about 35 ms across sensors.
It also needs continuous listening rather than 25 s samples, and at least four
sensors at known fixed positions for a 2D fix when the emission time is unknown.
This project has 363 spot measurements from three unsynchronised handsets.

Keep them apart in the writing. The manuscript's contribution is three negative
results about low-cost spatial prediction; a promise of localisation grafted onto
it invites the question of where the synchronised sensors are. As future work it
is strong, and the mobile app is already half of the instrument — it records
position, timestamp and level. What is missing is synchronisation and continuity,
which is hardware.

### Deliberately abandoned

- **LSTM / ST-GNN benchmark on Barcelona** — those models need continuous time
  series, which this campaign does not have. `barcelona_transfer.py` is kept as a
  documented dead end.
- **Demolition audio** — out of scope after the pivot.
- **GAMA pedestrian agents (tier 2 of the simulation plan)** — never implemented.

---

## 7. Accounts and access to request

| What | From whom | For |
|---|---|---|
| KoboToolbox project | The outgoing team | Re-running or extending the survey |
| HuggingFace read token | Yourself, after accepting the Sunbird terms | Notebooks 01–05 |
| Overleaf manuscript | The outgoing team | The paper |
| The 147 videos (6 GB) | The outgoing team | Only if re-counting vehicles |
| GAMA Platform ≥ 2025.6 | <https://gama-platform.org> | The simulation |
| VinUniversity ethics committee | Supervisor | **Before any new collection campaign** |

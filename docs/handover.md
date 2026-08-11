# Handover

*Written August 2026, at the end of a three-month research internship at
[AFFILIATION TO CONFIRM — CEI or COSMOS Lab], VinUniversity, Hanoi.*

**You are taking this project over tomorrow and want to know where to start.**
Read §1, run §2, then pick from §6.

---

## 0. Open items — answers we never got

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
| 2 | The YOLO detector has **no** validation against manual counts | ~1 day for 10 videos, double-counted | **The modal shares cannot be published.** Currently unquantified precision/recall |
| 3 | The Uganda chain (notebooks 01–06) is not reproducible: it expects `data/processed/uganda/*` which exists nowhere | Unknown; needs the HF download rerun | One of the three negative results rests on a chain nobody can replay |
| 4 | Two tests still to write: field cleaning, report guard | Half a day | Schema drift in `measurements.csv` would pass unnoticed |
| 5 | `run_dashboard.sh` duplicates `make dashboard` | 10 minutes | Two entry points that can disagree |
| 6 | `07_export_gama_inputs.py` is 414 lines doing grid, export, fleet, construction and measurement layers | 1 day | Hard to change one output without touching the others |
| 7 | Notebook 08 still computes as well as reports | Half a day | It should only read artefacts now that `03_build_features.py` exists |

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

- [ ] Validate the YOLO detector on ~10 videos (debt #2). Without it, no modal shares.
- [ ] Extract `validation.py` and `physics.py` from `04_evaluate_models.py` (debt #1).
- [ ] Write the two remaining tests (debt #4).

### The scientifically indicated next step

- [ ] **A real propagation kernel: CNOSSOS-EU, via NoiseModelling.** This is no
      longer an optional extra. If a two-parameter distance term already beats a
      six-variable LightGBM, then a physical propagation model corrected by a
      locally learned residual is the architecture the data points at. It was out
      of time budget for a three-month internship; it should be first on the list
      now, not in a "future work" paragraph.

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

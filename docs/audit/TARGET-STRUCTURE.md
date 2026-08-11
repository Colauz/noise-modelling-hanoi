# Target repository structure — Phase 1 proposal

**Date:** 2026-08-11
**Status:** proposal, awaiting approval. **No file has been moved.**
**Inputs:** [`INVENTORY.md`](INVENTORY.md) (Phase 0 findings) + the team's Phase 0 arbitration
of 2026-08-11.

References used as a starting point, adapted rather than copied: Cookiecutter Data Science
v2, The Turing Way (reproducible research chapter), FAIR principles (F1–F4, A1, I1, R1.1).

---

## 1. Design principles

Five rules drive every decision below. Where the template in the mission brief conflicts with
one of them, the rule wins and the deviation is justified in §5.

**P1 — One directory, one versioning policy.**
The Phase 0 audit found the repository's most dangerous defect: `measurements.csv` and
`vehicle_counts.csv` are tracked *inside* gitignored directories, surviving only through
`git add -f`, with `.gitignore` negations that cannot work. A newcomer moving those files
loses the empirical basis of the project silently. In the target structure, whether a path is
tracked is readable from the path itself and enforced by verified ignore rules (§4.1).

**P2 — Reproducibility is a property of `scripts/` + `Makefile`, never of a notebook.**
Today the OSM morphology features — an input to every published number — are computed in
`notebooks/08_predict_hanoi.ipynb`, which imports `morphology()` from
`scripts/export_gama_zones.py` through a `sys.path` hack. The chain cannot run headless.
Notebooks become exploration and narrative; every artefact-producing step becomes a numbered
CLI script over an importable package.

**P3 — Shared logic lives in one importable package.**
No script imports another today (verified). Site definitions, CRS, cleaning rules, the
physical kernel and the CV protocols are therefore restated across 13 files. `src/noise_hanoi/`
ends that.

**P4 — Separate what is *fitted* from what is *simulated* from what is *shown*.**
This project has three distinct kinds of "model" that the brief's single `models/` folder
would conflate: fitted statistical artefacts, a GAMA agent-based simulation (which is source
code plus its GIS inputs), and human-facing results. Each gets its own home.

**P5 — Retracted work is archived with its reason, never deleted.**
The withdrawn R² = 0.45, the Bach Khoa extrapolation and the pre-pivot deck are part of the
scientific record. They move to `docs/archive/` behind an explicit warning, they do not
disappear from `HEAD` without a trace.

---

## 2. Target tree

```
noise-modelling-hanoi/
│
├── README.md                     # showcase: what, why, how to reproduce in 5 commands
├── LICENSE                       # MIT — code
├── LICENSE-DATA                  # CC-BY-4.0 — data, docs, figures
├── CITATION.cff                  # machine-readable citation
├── CONTRIBUTING.md               # incl. the FR→EN commit-language switch
├── Makefile                      # the whole chain, one target per stage
├── pyproject.toml                # package metadata + pinned dependencies
├── requirements.txt              # generated lock file, for pip-only users
├── .gitignore                    # rewritten, verified (§4.1)
├── .gitattributes                # LF normalisation, linguist hints, diff drivers
├── .project  .settings/          # GAMA/Eclipse project metadata — kept, documented (§5.4)
│
├── config/                       # every tunable parameter, versioned, no magic numbers in code
│   ├── sites.yaml                #   3 sites: bbox, CRS EPSG:32648, 400 m margin, grid 40 m
│   ├── model.yaml                #   CV protocols (600 m blocks, 300 m BLOO, LOSO), hours 5–21
│   └── figures.yaml              #   plot style, colour scales, dB class breaks
│
├── data/                         # local by default; only the two published files are tracked
│   ├── README.md                 #   provenance, licence, access date, schema of each source
│   ├── raw/                      #   IMMUTABLE, gitignored: Kobo exports, 147 videos
│   │   └── .gitkeep
│   ├── interim/                  #   gitignored: OSM caches (.gpkg, .graphml), HF cache
│   │   └── .gitkeep
│   └── processed/
│       ├── measurements.csv      #   ● TRACKED — 363 rows, pseudonymised, the primary dataset
│       └── vehicle_counts.csv    #   ● TRACKED — 147 videos, ~26 min GPU to regenerate
│
├── src/noise_hanoi/              # importable package — the reusable core
│   ├── __init__.py
│   ├── config.py                 #   loads config/*.yaml, resolves project paths (no CWD hacks)
│   ├── io.py                     #   readers/writers, schema validation
│   ├── field.py                  #   Kobo cleaning, calibration offsets, QC rules
│   ├── features.py               #   OSM morphology in a 300 m radius  ← extracted from notebook 08
│   ├── physics.py                #   the delivered kernel E = A_hw/d_hw + A_res/d_res + B
│   ├── validation.py             #   the three CV protocols + block bootstrap  ← the core asset
│   ├── vision.py                 #   YOLOv8 + ByteTrack line-crossing counting
│   ├── grid.py                   #   sampled-envelope grid, exports for GAMA
│   └── plotting.py               #   shared figure style
│
├── scripts/                      # CLI entry points, numbered in execution order
│   ├── 01_prepare_field_data.py      # Kobo export      → data/processed/measurements.csv
│   ├── 02_count_vehicles.py          # 147 videos       → data/processed/vehicle_counts.csv  [needs raw videos]
│   ├── 03_build_features.py          # OSM + measures   → data/interim/features.parquet      [NEW, from notebook 08]
│   ├── 04_evaluate_models.py         # 8 models × 3 CV  → models/metrics.json, model_comparison.md
│   ├── 05_calibrate_emissions.py     # NNLS per class   → results/tables/emission_calibration.csv
│   ├── 06_anchor_literature.py       # bias bounding    → results/tables/literature_anchoring.*
│   ├── 07_export_gama_inputs.py      # grid + shapefiles→ simulation/gama/inputs/, results/maps/
│   ├── 08_validate_simulation.py     # in-sample check  → results/tables/validation_simulation.*
│   ├── 09_build_figures.py           # 5 analyses + map → results/figures/, results/maps/
│   ├── 10_build_report.py            # reads metrics.json → results/report/report.pdf
│   ├── 11_build_dashboard.py         # → results/report/dashboard/
│   └── experiments/                  # one-shot studies, not part of `make all`
│       ├── train_uganda_large.py
│       ├── train_v2_invariant.py
│       └── barcelona_transfer.py     # ← pending decision (§7, Q15)
│
├── notebooks/                    # exploration & narrative only, outputs stripped
│   ├── 01_explore_sunbird.ipynb
│   ├── 02_clean_sunbird.ipynb
│   ├── 03_audio_qc.ipynb
│   ├── 04_morphology_features.ipynb
│   ├── 05_reproduce_sunbird_figures.ipynb
│   ├── 06_train_surrogate_model.ipynb
│   ├── 07_hanoi_field_data.ipynb
│   └── 08_hanoi_results.ipynb     # reads artefacts, computes nothing  (09 → docs/archive/)
│
├── models/                       # FITTED artefacts + the metrics that qualify them
│   ├── README.md                 #   which model is delivered, and why (code-selected)
│   ├── hybrid_physical.json      #   ● the delivered 3-parameter kernel
│   ├── hybrid_residual_lgbm.txt  #   ● residual booster, portable text format
│   ├── surrogate_hanoi_direct.txt
│   ├── metrics.json              #   ● single source of truth for every published number
│   └── model_comparison.md       #   ● 7 models × 3 protocols + bootstrap CIs
│
├── simulation/gama/              # the agent-based model: source + its GIS inputs
│   ├── hanoi_noise.gaml
│   ├── README.md                 #   how to open it in GAMA without a Python environment
│   ├── inputs/                   #   ● tracked: 85 shapefile/CSV files (§5.3)
│   └── snapshots/                #   renamed, ASCII, no spaces
│
├── results/                      # human-facing outputs
│   ├── figures/                  #   hourly, weekday, source, exceedance, weather, Sunbird
│   ├── maps/                     #   hanoi_noise_map.csv, field points, heatmaps
│   ├── tables/                   #   exceedances, validation, literature anchoring
│   └── report/                   #   report.pdf + dashboard/
│
├── docs/
│   ├── methodology.md            #   acquisition → preparation → modelling → validation
│   ├── data-sources.md           #   incl. the 147 unpublished videos: protocol + why withheld
│   ├── metrology.md              #   ← paper/sections/metrology.md, translated
│   ├── negative-results.md       #   ← paper/sections/negative_results.md, translated
│   ├── literature-review.md      #   Phase 4
│   ├── references.bib            #   ← paper/bibliography.bib, every entry verified
│   ├── handover.md               #   ← THE handover document
│   ├── roadmap.md                #   ← ROADMAP.md, translated, results split out
│   ├── audit/
│   │   ├── scientific-audit.md   #   ← audit_noise_modeling.md, translated
│   │   ├── INVENTORY.md          #   this audit's Phase 0
│   │   └── TARGET-STRUCTURE.md   #   this document
│   └── archive/                  #   superseded work, kept with its reason (P5)
│       ├── README.md             #   what was withdrawn, when, and why
│       ├── bach-khoa/            #   ← outputs/deprecated/
│       ├── slides-2026-07-31.html#   ← pre-pivot deck, contains the withdrawn R² = 0.45
│       └── 09_export_gama.ipynb  #   ← neutralised notebook
│
├── presentation/                 # Phase 5
│   ├── main.tex                  #   Beamer, metropolis theme
│   ├── sections/
│   ├── figures/
│   ├── Makefile
│   └── hanoi-noise-2026-08.pdf   #   compiled, versioned
│
└── tests/                        # small, and aimed at the failures that actually happened
    ├── test_cv_protocols.py      #   buffered LOO really excludes points within 300 m
    ├── test_grid_extent.py       #   no cell outside the sampled envelope + 400 m
    ├── test_physics.py           #   kernel monotonicity, energy summation
    ├── test_field_cleaning.py    #   calibration offsets, QC rules, schema
    └── test_report_guard.py      #   the report refuses to build without metrics.json
```

Legend: **●** = deliberately tracked in git despite being derived or large-ish.

---

## 3. Why each directory exists

| Directory | Why it exists | What it replaces |
|---|---|---|
| `config/` | Every number that a reviewer might challenge (300 m radius, 600 m blocks, 40 m grid, 400 m margin, hours 5–21, CRS) currently lives as a literal in several files at once. A reviewer must be able to read the parameters without reading the code, and a successor must be able to change one in one place. | scattered constants in 13 scripts |
| `data/` | Three-stage immutability: `raw/` is never written to, `interim/` is machine-regenerable, `processed/` holds the two curated datasets we publish. Enables the FAIR "R1.1" (clear provenance + licence per source) via `data/README.md`. | `data/raw`, `data/processed` with broken ignore rules |
| `src/noise_hanoi/` | The reusable, importable, testable core. Makes `pip install -e .` meaningful, kills the `sys.path.insert('../scripts')` hack, and gives `tests/` something to import. | logic duplicated across `scripts/*.py` and notebook 08 |
| `scripts/` | Numbered CLI entry points = the executable table of contents of the method. The numbering *is* the pipeline documentation. | unnumbered `scripts/*.py` whose order lives only in the README |
| `notebooks/` | Exploration and narrative. Stripped of outputs so diffs are readable and no collaborator's machine path leaks. Notebook 08 is demoted to *reading* artefacts rather than producing them. | notebooks that both explore and produce published artefacts |
| `models/` | Fitted artefacts *and* the metrics that qualify them, together. `metrics.json` sits next to the model it describes, because the project's rule is that no number is ever copied by hand. | `outputs/models/` |
| `simulation/gama/` | The GAMA model is source code with GIS dependencies, not an output. Keeping `inputs/` beside the `.gaml` lets a GAMA-only user (no Python) clone and run. | `gama/` + `outputs/gama_inputs/`, 2 directories apart |
| `results/` | What a human looks at: figures, maps, tables, report. Cleanly separable from `models/` (what a machine reloads). | `outputs/hanoi/`, `outputs/sunbird/`, `outputs/dashboard/`, `outputs/report.pdf` |
| `docs/` | The handover surface. Currently the two best documents in the repository (the audit and the negative-results section) are buried at the root and under `paper/`. | root `*.md` + `paper/sections/` |
| `docs/archive/` | Retraction trail (P5). A public repository that shows *what it withdrew and why* is more trustworthy than one that shows only its wins. | `outputs/deprecated/`, orphan deck |
| `presentation/` | Phase 5 Beamer sources + compiled PDF. | `outputs/slides_presentation.html` (superseded) |
| `tests/` | Five tests, each aimed at a failure this project actually suffered. `test_cv_protocols.py` is the regression test for the leak that produced the withdrawn R² = 0.45. | nothing — there are no tests today |

---

## 4. What changes concretely

### 4.1 `.gitignore` — rewritten and empirically verified

The current negations are inert. The replacement re-includes directories first, which is what
makes downstream negations legal in git. **Tested in a scratch repository before proposing it:**

```gitignore
# --- data: local by default -------------------------------------------------
data/**
!data/**/                                  # re-include dirs, else no negation below applies
!data/**/README.md
!data/**/.gitkeep
!data/processed/measurements.csv           # the 363 field measurements
!data/processed/vehicle_counts.csv         # the 147 video counts
```

Verified result: `measurements.csv`, `vehicle_counts.csv`, `data/README.md` and the `.gitkeep`
files are staged; `data/raw/hanoi/video.mp4`, the Kobo export and `data/interim/roads.graphml`
are ignored. No `git add -f` anywhere in the project any more.

Also added: `.venv/` (currently ignored only by its own internal file), `.claude/`,
`*.pyc`/`__pycache__`, `.ipynb_checkpoints/`, `.workspace*/`, the space-named Eclipse
directory, `yolov8n.pt`, `presentation/*.aux|log|nav|out|snm|toc`.

### 4.2 `.gitattributes` — new

```
* text=auto eol=lf
*.gaml   text
*.csv    text
*.ipynb  text
*.shp binary
*.dbf binary
*.shx binary
*.gpkg binary
*.pdf binary
*.png binary
notebooks/*.ipynb linguist-documentation
```

Guarantees LF endings for the next team regardless of platform, and stops GitHub from
reporting the project as majority-Jupyter.

### 4.3 Path rewrites — the real migration cost

**24 tracked files** contain project-relative paths that the move invalidates: 13 scripts, 10
notebooks, `run_dashboard.sh`, plus `gama/hanoi_noise.gaml`. `scripts/export_gama_zones.py`
alone references project paths 13 times. This is mechanical but must be done in a commit
separate from the `git mv` commits, per the mission's rule (§Phase 6).

Introducing `src/noise_hanoi/config.py` with resolved project-root paths means most of these
become one import instead of a literal, so the rewrite also removes the class of bug rather
than relocating it.

### 4.4 Entry points and the 5-command README promise

```makefile
make setup      # pip install -e . ; pre-commit install
make data       # 01 (+ 02 only if raw videos are present)
make features   # 03
make models     # 04            -> models/metrics.json
make results    # 05 06 07 08 09 10 11
make all        # everything above, in order
make test       # pytest
make slides     # presentation/
make clean      # interim + regenerable results, never data/raw
```

README reproduction section, five commands:

```bash
git clone https://github.com/Colauz/noise-modelling-hanoi && cd noise-modelling-hanoi
make setup
make features        # data/processed/measurements.csv ships with the repo
make models
make results         # -> results/maps/, results/report/report.pdf
```

`make data` is deliberately *not* in the critical path: `measurements.csv` and
`vehicle_counts.csv` are versioned, so an external researcher reproduces the maps and the
model comparison without the raw Kobo export and without the 6 GB of video. This is what makes
acceptance criterion #1 achievable given the ethics decision on the videos.

### 4.5 File and directory naming

- `kebab-case` for documents and directories, `snake_case` for Python modules and data files.
- ASCII only, no spaces, no accents. Two current offenders, both renamed:
  `gama/snapshots/hanoi_noise_model_display_Carte de bruit_cycle_83174_time_1785474057481.png`
  → `simulation/gama/snapshots/noise-map-cycle-83174.png`;
  `paper/references/Survey_Paper_Noise_Modelling (1).pdf` → pending decision (§7, Q14).
- Google-Drive-generated directory names (`drive-download-20260805T101542Z-1-00{1..4}`) are
  replaced by a documented scheme in the local/external video archive.
- UTF-8, LF everywhere, enforced by `.gitattributes`.

### 4.6 Migration map

| Current | Target | Method |
|---|---|---|
| `README.md` | `README.md` | rewritten (Phase 3) |
| `ROADMAP.md` | `docs/roadmap.md` + results → `docs/methodology.md` | `git mv` + split + translate |
| `audit_noise_modeling.md` | `docs/audit/scientific-audit.md` | `git mv` + translate |
| `paper/sections/metrology.md` | `docs/metrology.md` | `git mv` + translate |
| `paper/sections/negative_results.md` | `docs/negative-results.md` | `git mv` + translate |
| `paper/bibliography.bib` | `docs/references.bib` | `git mv` + verify every entry (Phase 4) |
| `paper/references/*.pdf` | — | pending (§7, Q14) |
| `field/README.md` | `docs/field-protocol.md` | `git mv` + translate |
| `field/*.xlsx` | `data/forms/*.xlsx` (tracked) | `git mv` |
| `data/raw/hanoi/measurements.csv` | `data/processed/measurements.csv` | `git mv` — **ends the ignored-but-tracked trap** |
| `data/processed/hanoi/vehicle_counts.csv` | `data/processed/vehicle_counts.csv` | `git mv` — idem |
| `data/processed/hanoi/*.gpkg,*.graphml` | `data/interim/` | move, stays untracked |
| `data/raw/hanoi/drive-download-*` | external archive | not in git; documented in `docs/data-sources.md` |
| `scripts/*.py` | `scripts/NN_*.py` + `src/noise_hanoi/*` | `git mv` then refactor (2 commits) |
| `scripts/experiments/*` | `scripts/experiments/*` | unchanged |
| `notebooks/09_export_gama.ipynb` | `docs/archive/` | `git mv` |
| `notebooks/*` (others) | same names, outputs stripped | in place |
| `gama/hanoi_noise.gaml` | `simulation/gama/hanoi_noise.gaml` | `git mv` (+ **commit the pending `FLOW_RADIUS` fix first**) |
| `gama/PLAN.md` | `simulation/gama/README.md` | `git mv` + translate + refresh |
| `outputs/gama_inputs/*` (85) | `simulation/gama/inputs/` | `git mv` |
| `outputs/models/*` | `models/` | `git mv` |
| `outputs/models/*.pkl` (2 × 11 MB) | pending (§7, Q17) | — |
| `outputs/hanoi/*.png` | `results/figures/` | `git mv` |
| `outputs/hanoi/*.csv,*.html` | `results/tables/`, `results/maps/` | `git mv` |
| `outputs/sunbird/*` | `results/figures/sunbird/` | `git mv` |
| `outputs/report.pdf`, `outputs/dashboard/` | `results/report/` | `git mv` |
| `outputs/deprecated/*` | `docs/archive/bach-khoa/` | `git mv` |
| `outputs/slides_presentation.html` | `docs/archive/slides-2026-07-31.html` | `git mv` |
| `run_dashboard.sh` | `make dashboard` | replaced by the Makefile target |
| `.workspace0/`, `" "/` , `scripts/__pycache__/` | — | delete (untracked junk) |

Commit sequencing (Phase 6 rule: never mix a move with a content change):
`chore: commit pending GAMA corridor fix` → `refactor: move files to target layout` (pure
`git mv`) → `fix: update paths after restructure` → `feat: add src package` → `docs: …` →
`chore: add licence, citation, contributing`.

---

## 5. Deliberate deviations from the brief's template

| Deviation | Reason |
|---|---|
| **`simulation/gama/` instead of putting GAMA under `models/`** | The brief's `models/` is described as "NoiseModelling configurations, calibrations". This project has no NoiseModelling. It has (a) fitted statistical artefacts and (b) an agent-based simulation that is source code with GIS inputs. Merging them would put an 85-file shapefile tree next to a 564-byte JSON kernel. |
| **GAMA inputs tracked, beside the model, not under `data/`** | A GAMA user with no Python environment must be able to clone and run. Keeping `inputs/` beside the `.gaml` also shortens every path inside the model. Cost: 14 MB of regenerable files in git — accepted deliberately, documented in `simulation/gama/README.md`. |
| **No `paper/` directory** | The manuscript lives on Overleaf. Its two written sections are the best documentation in the repository and serve the handover better as first-class `docs/` pages than as manuscript fragments. (Reopens Q20 — see §7.) |
| **`data/processed/` holds two curated files, not a stage dump** | Follows P1: the directory that is tracked is small and curated; everything machine-regenerable goes to `interim/`. |
| **`environment.yml` not proposed** | The project is pip-installable and has no conda-only dependency. `pyproject.toml` + a generated `requirements.txt` lock is enough, and one fewer file to keep in sync. Reversible if you want conda. |
| **`docs/archive/` added** | Not in the template. Required by P5 and by this project's history of one retraction and one withdrawn figure. |
| **`config/` split into 3 files, not 1** | `sites.yaml` changes when a site is added, `model.yaml` when a protocol changes; different people, different review cadence. |

---

## 6. What will break, and how it is handled

| Risk | Handling |
|---|---|
| The GAMA model stops finding its shapefiles | Paths inside `hanoi_noise.gaml` are rewritten in the same commit as the input move, and the model is opened in GAMA to confirm before the next commit. **This needs you to run GAMA — I cannot verify it here.** |
| The Eclipse/GAMA `.project` filters reference `data`, `.venv`, `cache` by name | All three names survive the restructure. `cache/` becomes `data/interim/`, so one filter entry needs updating. |
| Notebooks break on `sys.path.insert('../scripts')` | Replaced by `from noise_hanoi import …` after `pip install -e .`. |
| The Sunbird chain references `data/processed/uganda/*` which does not exist locally | Confirmed absent (Phase 0). Notebooks 01–06 are not currently reproducible on this machine; documented as a known gap in `docs/handover.md` rather than silently "fixed". |
| Stripping notebook outputs loses displayed results | Those results exist in `results/` and `models/metrics.json`. Notebook 08 is rewritten to *read* them, so the narrative survives without stored outputs. |
| History rewriting | Not performed. Per your arbitration, the 12 commits stay as they are, French messages included. |

---

## 7. Decisions still open

Answered in the Phase 0 arbitration: identity (partially), remote, language, ethics/data.
Still open, and each blocks a specific later step:

| # | Question | Blocks | My recommendation |
|---|---|---|---|
| Q12 | Pre-pivot deck (`slides_presentation.html`, contains the withdrawn R² = 0.45) | Phase 2 | `docs/archive/` with a warning banner in `docs/archive/README.md` |
| Q13 | `outputs/deprecated/` payload (6.7 MB) | Phase 2 | Keep `README.md` (it documents the retraction), drop the 6.7 MB from `HEAD` |
| Q14 | The two third-party PDFs in `paper/references/` | Phase 2 | Remove both from the public repo, replace with DOIs. The *Scientific Data* one is very likely CC-BY, but I will not assert that without verifying the licence page in Phase 4 |
| Q15 | `barcelona_transfer.py` with no Barcelona data | Phase 2 | Keep, under `experiments/`, with a header stating the data source and that it is a closed dead end |
| Q17 | Two 11 MB `.pkl` models | Phase 2 | Re-export as LightGBM `.txt` (portable, version-independent, ~1 MB); keep the `.pkl` only if you still need `joblib.load` in notebook 08 |
| Q18 | Phase 4 reference count 15–25, and treat `bibliography.bib` as unverified | Phase 4 | Confirm |
| Q19 | Presentation date, audience, 20 min / 18–22 slides | Phase 5 | Confirm |
| Q20 | Is the Overleaf manuscript in scope? | Phase 3 | Out of scope; `docs/` carries the sections, README links to Overleaf |

### Identity gaps to fill (placeholders will be used meanwhile)

| Placeholder | Needed for |
|---|---|
| `[SUPERVISOR NAME]`, title, affiliation | `CITATION.cff`, `README` acknowledgements, title slide |
| Author order in `CITATION.cff` | `CITATION.cff`, Zenodo record |
| ORCIDs (Jamin, Zborowski, Nguyen, supervisor) | `CITATION.cff` FAIR compliance |
| Role of Nguyen Thanh Quang — co-author or acknowledgement? | `CITATION.cff`, `README` |
| VinUni IRB status for the 147 videos | `docs/data-sources.md`, push gate |
| `measurements.csv`: full-precision or rounded GPS | Two variants prepared, neither pushed |

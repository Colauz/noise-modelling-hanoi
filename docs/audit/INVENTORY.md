# Repository inventory — Phase 0 audit

**Date:** 2026-08-11
**Scope:** full recursive walk of the local working directory
`/home/enedis/Documents/Scolaire/quitus/vin_uni_stage/noise-modelling-hanoi`, at commit
`b86e252` (+ 1 uncommitted change).
**Purpose:** decide what belongs in a public, citable research repository before restructuring.

**Evidence codes used below**
`[V]` verified by direct inspection (file read, command output) ·
`[I]` inferred from context, flagged as such ·
`[?]` unknown, requires a decision from the team.

> **Nothing has been moved, renamed or deleted.** This document only proposes verdicts.

---

## 1. Headline numbers

| Metric | Value | Source |
|---|---|---|
| Working directory size | **8.7 GB** | `du -sh .` [V] |
| Of which `data/raw/` (147 field videos) | **6.0 GB** | `du -sh data/raw` [V] |
| Of which `.venv/` | 2.6 GB | [V] |
| Git object store | 39 MB | `du -sh .git` [V] |
| Tracked files | **167** | `git ls-files` [V] |
| Largest tracked file | 11 MB (`surrogate_lgbm_v2_uganda.pkl`) | [V] |
| Commits | 12, first on 2026-06-01 | `git log` [V] |
| Files > 50 MB in git | **none** | [V] |
| Secrets in tracked files or history | **none found** | pattern scan over `git ls-files` + `git log -S` [V] |

**Verdict on size:** the repository itself is publishable as-is size-wise. The 6 GB of raw
video is correctly kept out of git and needs an external home (Phase 6 decision).

---

## 2. Inventory by area

Files are listed individually where they carry meaning, and grouped where a directory is
homogeneous (e.g. 85 shapefile sidecar files). Sizes are on-disk; `git` column says whether
the path is tracked.

### 2.1 Root

| Path | Type | Size | Modified | Git | Presumed role | Verdict |
|---|---|---|---|---|---|---|
| `README.md` | md | 6.9 KB | 2026-08-05 | tracked | Project front page, English, already reflects the methodological pivot | **KEEP** — rewrite in Phase 3 |
| `ROADMAP.md` | md | 14 KB | 2026-08-05 | tracked | French. Mixes three things: results narrative (V1/V2 model tables), applied corrections, remaining tasks | **KEEP, SPLIT** → results to `docs/methodology.md`, open items to `docs/handover.md` |
| `audit_noise_modeling.md` | md | 48 KB | 2026-08-05 | tracked | French. Internal scientific audit of 2026-08-05 that triggered the pivot. Highest-value document in the repo for a newcomer | **KEEP, MOVE** → `docs/audit/` |
| `requirements.txt` | txt | 275 B | 2026-07-04 | tracked | 16 deps, all `>=`, **no pins**; misses `scipy`, `requests`, `ultralytics`, `opencv`, `reportlab`/PDF lib actually imported by scripts `[V]` | **KEEP, FIX** — pin + complete in Phase 2 |
| `run_dashboard.sh` | sh | 2.8 KB | 2026-08-05 | tracked | Builds and opens `outputs/dashboard/index.html` | **KEEP** — becomes a `make dashboard` target |
| `yolov8n.pt` | binary | 6.3 MB | 2026-08-05 | ignored | Ultralytics pretrained weights, auto-downloaded | **KEEP local, stays ignored** — document the download in setup |
| `.gitignore` | — | 1.3 KB | 2026-08-05 | tracked | Well commented, but has a **broken negation pattern** (§4.2) | **KEEP, FIX** |
| `.project`, `.settings/` | Eclipse XML | 1.4 KB | 2026-08-05 | **tracked** | GAMA/Eclipse workspace metadata, committed in `b86e252`. Inconsistent: `gama/.project` and `gama/.settings/` are explicitly *ignored* `[V]` | **CLARIFY** — is the root `.project` required to open the model in GAMA, or leftover? |
| `.workspace0/` | dir | empty | 2026-08-06 | untracked | Eclipse/GAMA scratch workspace | **DELETE** |
| `" "/.workspace1/` | dir | 32 KB | 2026-08-06 | untracked | **Directory literally named with a single space**, containing empty Eclipse `.metadata`. Created by GAMA on launch | **DELETE** |
| `.claude/settings.local.json` | json | 500 B | 2026-08-06 | untracked | Local tool permissions, contains an absolute personal path | **KEEP local, add to `.gitignore`** |
| `.venv/` | dir | 2.6 GB | — | self-ignored | Python 3.14.4 virtualenv. Ignored only via its own internal `.venv/.gitignore` — **not** by the project `.gitignore` `[V]` | **KEEP local, add explicit ignore rule** |
| `cache/` | dir | 26 MB | 2026-08-05 | ignored | 2 HuggingFace/OSMnx response caches | **KEEP local** — regenerable |

### 2.2 `notebooks/` — 4.5 MB, 9 files, all tracked

| Path | Cells / with output | Size | Role | Verdict |
|---|---|---|---|---|
| `01_explore_sunbird.ipynb` | 8 / 4 | 812 KB | Load Uganda Sunbird 61K, distributions | **KEEP, STRIP OUTPUTS** |
| `02_clean_sunbird.ipynb` | 12 / 6 | 1.6 MB | Dedup, GPS filter, dB sanity | **KEEP, STRIP OUTPUTS** |
| `03_audio_qc.ipynb` | 6 / 4 | 56 KB | Audio QC (silence, band energy, MD5) | **KEEP, STRIP OUTPUTS** |
| `04_morphology_features.ipynb` | 9 / 4 | 192 KB | 300 m OSM morphology features | **KEEP, STRIP OUTPUTS** |
| `05_reproduce_figures.ipynb` | 9 / 4 | 164 KB | Reproduce Nsumba et al. figures 8–10 | **KEEP, STRIP OUTPUTS** |
| `06_train_surrogate_model.ipynb` | 6 / 5 | 84 KB | LightGBM morphology→dB on Uganda | **KEEP, STRIP OUTPUTS** |
| `07_hanoi_field_data.ipynb` | 11 / 8 | 1.6 MB | Hanoi field data cleaning + 5 analyses + map | **KEEP, STRIP OUTPUTS** |
| `08_predict_hanoi.ipynb` | 13 / 0 | 12 KB | Hanoi OSM features + evaluation entry point | **KEEP** |
| `09_export_gama.ipynb` | 3 / 0 | 4 KB | **Neutralised** — superseded by `scripts/export_gama_zones.py` | **ARCHIVE** — dead notebook, keep in history only |

**Two problems, both in stored outputs `[V]`:**
1. Notebooks 01–05 and 07 embed execution outputs from a **second, non-anonymised machine
   path**: `/Users/phocidae/Library/...` and
   `/Users/phocidae/Desktop/VinUni/noise-modelling-hanoi/data/raw/hanoi/measurements.csv`.
   This discloses a collaborator's OS username in a public repo.
2. Those outputs account for ~4.3 MB of the 4.5 MB. Stripping them makes diffs readable.

### 2.3 `scripts/` — 420 KB, 13 Python files, all tracked

| Path | Lines | Role (from docstring) | Verdict |
|---|---|---|---|
| `prepare_field_data.py` | 211 | Kobo export → cleaned `measurements.csv` | **KEEP** |
| `evaluate_models.py` | 598 | Honest evaluation: 3 CV protocols, 8 models, bootstrap CIs; **selects the delivered model and writes `meta.delivered_model`** | **KEEP — core contribution** |
| `export_gama_zones.py` | 414 | Multi-zone × multi-hour grid export, reads `apply_residual` flag | **KEEP** |
| `literature_anchoring.py` | 209 | Bounds the absolute bias against instrumented literature | **KEEP** |
| `calibrate_emissions.py` | 246 | NNLS per-vehicle emission fit (returns zeros — a result, not a bug) | **KEEP** |
| `validate_simulation.py` | 147 | In-sample check: does the map reproduce the measurements | **KEEP** |
| `build_report.py` | 582 | 8-page PDF, reads `metrics.json`, refuses to run without it | **KEEP** |
| `build_dashboard.py` | 478 | Static HTML dashboard | **KEEP** |
| `build_field_map.py` | 161 | Interactive folium map of field points | **KEEP** |
| `experiments/count_vehicles.py` | 320 | YOLOv8 + ByteTrack line-crossing counts on 147 videos | **KEEP** |
| `experiments/train_large.py` | 164 | LightGBM on Uganda 59K | **KEEP** |
| `experiments/train_v2_invariant.py` | 152 | Convention-invariant v2 features | **KEEP** |
| `experiments/barcelona_transfer.py` | 181 | Barcelona transfer diagnostics — **no Barcelona data exists** in `data/` `[V]`, and `README` still advertises `data/raw/barcelona` | **CLARIFY** — dead branch or reproducible from an external source? |
| `__pycache__/` | 8 `.pyc` | Build artefact | **DELETE** (already ignored) |

**Structural note `[V]`:** no script imports another (`grep` on imports shows zero
cross-imports). There is no importable package. Shared logic (paths, site definitions,
CRS, cleaning rules) is therefore duplicated across 13 files — the main refactor candidate
for Phase 2's `src/` layer.

### 2.4 `data/` — 6.0 GB

| Path | Size | Git | Role | Verdict |
|---|---|---|---|---|
| `raw/hanoi/drive-download-*-00{1..4}/` | **6.0 GB**, 147 videos (`.mov`/`.mp4`) | ignored | Traffic videos, source of `vehicle_counts.csv`. Directory names are Google Drive export artefacts, not meaningful | **ARCHIVE EXTERNALLY** — rename to a documented scheme; contains faces and licence plates (ethics, §5.3) |
| `raw/hanoi/measurements.csv` | 48 KB, 363 rows | **tracked, inside an ignored directory** | **The primary dataset.** Columns are already pseudonymised: no collector name `[V]` | **KEEP — but MOVE** out of `data/raw/` (§4.2) |
| `raw/hanoi/Hanoi_Urban_Noise_Survey_*.csv` | 228 KB | ignored | Raw Kobo export. Contains `Who is collecting?`, `_submitted_by`, audio URLs → **personal data** `[V]` | **KEEP local, NEVER commit** |
| `raw/hanoi/Hanoi_Construction_Sites_Log_*.csv` | 4 KB | ignored | Raw Kobo construction log | **KEEP local** |
| `processed/hanoi/vehicle_counts.csv` | 23 KB | **tracked, inside an ignored directory** | 147 videos × flow counts, ~26 min of GPU to regenerate | **KEEP — but MOVE** (§4.2) |
| `processed/hanoi/hanoi_sites_buildings.gpkg` | 12 MB | ignored | OSM buildings for the 3 sites | **KEEP local** — regenerable, but OSM drifts: record the extraction date |
| `processed/hanoi/hanoi_sites_roads.graphml` | 6.4 MB | ignored | OSMnx road graph | idem |

### 2.5 `outputs/` — 49 MB

| Path | Size | Git | Role | Verdict |
|---|---|---|---|---|
| `models/metrics.json` | 21 KB | tracked | **Single source of truth for every published number** | **KEEP — critical** |
| `models/model_comparison.md` | 5.6 KB | tracked | 7-model × 3-protocol table with bootstrap CIs | **KEEP — critical** |
| `models/hybrid_physical.json` | 564 B | tracked | 3-parameter delivered kernel | **KEEP** |
| `models/hybrid_residual_lgbm.txt` | 239 KB | tracked | Residual booster (text format, portable) | **KEEP** |
| `models/surrogate_lgbm_hanoi_direct.txt` | 627 KB | untracked | Direct Hanoi LightGBM | **CLARIFY** — track or regenerate? |
| `models/surrogate_lgbm_large.pkl` | **11 MB** | tracked | Uganda 59K model, pickled | **CLARIFY** — pickle is Python/lib-version fragile; prefer `.txt` booster or Zenodo |
| `models/surrogate_lgbm_v2_uganda.pkl` | **11 MB** | tracked | v2 invariant model, pickled | idem |
| `hanoi/` (12 files) | 2.1 MB | tracked | 5 analysis figures, exceedances, field map, `hanoi_noise_map.csv` (5 587 cells × 17 h), validation, literature anchoring | **KEEP** → becomes `results/` |
| `gama_inputs/` (85 files) | 14 MB | tracked | Shapefiles + CSVs consumed by the GAMA model, fully regenerable by `export_gama_zones.py` | **KEEP but RECONSIDER** — 85 tracked files that one command reproduces |
| `sunbird/` (11 files) | 2.3 MB | tracked | Uganda reproduction figures + maps | **KEEP** → `results/figures/` |
| `dashboard/index.html` + `map.html` | 552 KB | tracked | Generated dashboard | **KEEP** (generated, but useful as a browsable artefact) |
| `report.pdf` | 184 KB | tracked | 8-page data-collection report, generated from `metrics.json` | **KEEP** |
| `slides_presentation.html` | **1.9 MB** | tracked | Deck dated **2026-07-31**, i.e. **before** the 2026-08-05 pivot. Contains the withdrawn **R² = 0.45** figure (2 occurrences) `[V]`. No script produces it — orphan | **ARCHIVE** — must not be published as-is; superseded by the Phase 5 Beamer deck |
| `deprecated/` (4 files) | 6.8 MB | tracked | Withdrawn "Bach Khoa" artefacts + a README explaining why. `hanoi_heatmap.html` alone is 4.7 MB | **ARCHIVE** — keep the README (it documents a retraction), drop the 6.7 MB of payload from `HEAD` |

### 2.6 `gama/`, `paper/`, `field/`

| Path | Size | Git | Role | Verdict |
|---|---|---|---|---|
| `gama/hanoi_noise.gaml` | 46 KB | tracked, **modified** | The simulation model. Uncommitted change dated 2026-08-06 introduces `FLOW_RADIUS` / `spawn_roads`: measured flow is now injected only on streets within 150 m of a measurement point, instead of being diluted over 673 streets `[V]` | **KEEP — COMMIT the pending fix** (real content, currently unversioned) |
| `gama/PLAN.md` | 4 KB | tracked | Simulation design rationale (receiver-agents, not emitter-agents). Written before tier 1 was implemented — the "Reste à faire" list is now partly stale `[I]` | **KEEP, UPDATE** |
| `gama/snapshots/hanoi_noise_model_display_Carte de bruit_cycle_83174_time_1785474057481.png` | 558 KB | tracked | GAMA screen capture. **Filename contains spaces and a French label** | **KEEP, RENAME** |
| `paper/bibliography.bib` | 11 KB | tracked | Existing BibTeX — the starting point for Phase 4 | **KEEP, VERIFY EVERY ENTRY** |
| `paper/sections/negative_results.md` | 29 KB | tracked | §5.x/§5.z — the central scientific argument. French | **KEEP — core contribution** |
| `paper/sections/metrology.md` | 8.8 KB | tracked | `L_A,25s` framing, why no compliance claim is made. French | **KEEP — core contribution** |
| `paper/references/s41597-026-06658-w.pdf` | 3.0 MB | tracked | Nsumba et al., *Scientific Data* — likely CC-BY, redistributable **if verified** `[?]` | **CLARIFY** |
| `paper/references/Survey_Paper_Noise_Modelling (1).pdf` | 956 KB | tracked | Unidentified survey PDF, filename with space + `(1)`. **Provenance and licence unknown** | **CLARIFY / likely REMOVE** — replace with a DOI link |
| `paper/figures/.gitkeep` | 0 B | tracked | Empty — figures live in `outputs/` | **KEEP** (folder placeholder) |
| `field/README.md` | 3 KB | tracked | Field protocol: cross-calibration, per-point routine, capture window | **KEEP — core contribution** |
| `field/hanoi_noise_form_v2.xlsx` | ~14 KB | tracked | XLSForm, main survey | **KEEP** |
| `field/hanoi_construction_form.xlsx` | ~14 KB | tracked | XLSForm, construction log | **KEEP** |

---

## 3. Duplicates, temporary files, regenerable outputs, orphans

| Category | Items | Note |
|---|---|---|
| **Temporary / IDE junk** | `" "/.workspace1/`, `.workspace0/`, `scripts/__pycache__/` | Safe to delete, none tracked |
| **Regenerable in one command** | `outputs/gama_inputs/` (85 files, 14 MB), `outputs/hanoi/hanoi_noise_map.csv`, `outputs/dashboard/`, `outputs/report.pdf`, `data/processed/hanoi/*.gpkg|graphml` | Tracking them is a choice, not a necessity — worth an explicit policy |
| **Expensive to regenerate (keep tracked)** | `data/processed/hanoi/vehicle_counts.csv` (~26 min GPU), `outputs/models/metrics.json` | Already handled correctly |
| **Duplicated derived data** | `outputs/hanoi/hanoi_noise_map.csv` (full grid × 17 h) vs `outputs/gama_inputs/noise_map.csv` (flat, 17 h reference) | Same producer, two views — documented, not a defect |
| **Dead / orphan artefacts** | `notebooks/09_export_gama.ipynb` (neutralised), `outputs/slides_presentation.html` (pre-pivot, no producer), `outputs/deprecated/*` (retracted), `scripts/experiments/barcelona_transfer.py` (no data) | Each needs a keep/archive decision |
| **Stale documentation claims** | `README.md` advertises `data/raw/{barcelona,hanoi}` and `processed/{uganda,barcelona,hanoi}`; only `hanoi` exists `[V]`. `gama/PLAN.md` lists tier-1 tasks that are done | Fix in Phase 3 |
| **No duplicates found** | — | No byte-identical file pairs of consequence outside `.venv` |

---

## 4. Defects found (nothing fixed yet)

### 4.1 Git remote points nowhere near the target `[V]`

```
origin  git@gitlab.com:jaminfollietlaurian/noise-modelling-hanoi.git (fetch)
origin  ssh://git@codeberg.org/Laurian/noise-modelling-hanoi.git     (push)
origin  git@gitlab.com:jaminfollietlaurian/noise-modelling-hanoi.git (push)
```

`origin` has **two push URLs** (Codeberg *and* GitLab) and neither is the stated target
`https://github.com/Colauz/noise-modelling-hanoi`. Any `git push` today writes to two
forges at once. This must be resolved before Phase 6.

### 4.2 Two critical data files are tracked *inside* ignored directories `[V]`

```
IGNORED but TRACKED: data/raw/hanoi/measurements.csv          <- the 363 measurements
IGNORED but TRACKED: data/processed/hanoi/vehicle_counts.csv  <- the 147 video counts
```

The `.gitignore` negations meant to re-include them (`!data/processed/hanoi/…`) **cannot
work**: git does not re-include files inside an excluded directory. They only survive
because someone ran `git add -f`. Consequence: a fresh clone reproduces the chain, but
anyone re-adding them after a move will silently lose them, and `git status` will never
warn. These two files are the empirical basis of the entire project.

### 4.3 Environment is not reproducible `[V]`

- `requirements.txt` has 16 unpinned `>=` deps and omits at least `scipy`, `requests`,
  `ultralytics`, `opencv-python` and the PDF library used by `build_report.py`.
- The venv runs **Python 3.14.4**, a version for which several pinned scientific wheels
  may not exist on other machines `[I]`.
- Two 11 MB `.pkl` models are tracked; unpickling requires a matching
  scikit-learn/LightGBM version, which is nowhere recorded.

An external researcher cannot currently satisfy acceptance criterion #1 (clone → reproduce
a noise map from the README alone).

### 4.4 Personal data exposure risk `[V]`

- Raw Kobo exports contain collector identities (`Who is collecting?`, `_submitted_by`)
  and audio recording URLs. **Correctly ignored today** — the risk is a future careless
  `git add -A` combined with the confusing rules in §4.2.
- The 147 videos were shot in public space and contain faces and licence plates.
  `ROADMAP.md` already flags the missing VinUni IRB statement as a Q1-journal blocker.
- Notebook stored outputs leak a collaborator's machine path (`/Users/phocidae/…`).

### 4.5 Missing repository infrastructure `[V]`

Absent: `LICENSE`, `LICENSE-DATA`, `CITATION.cff`, `CONTRIBUTING.md`, `.gitattributes`,
`Makefile`, `pyproject.toml`, `tests/`, `config/`, `src/`, `docs/`.
Without a licence, the repository is **all-rights-reserved by default** and legally
unusable by the team taking over.

### 4.6 The stack described in the mission brief does not match the code `[V]`

The brief lists *NoiseModelling v4.x, PostGIS*. Neither appears anywhere in the code:
`grep` finds them only in `audit_noise_modeling.md` and `ROADMAP.md`, as **recommended
future work**. The actual stack is: Python 3.14 · pandas/GeoPandas/Shapely/OSMnx ·
LightGBM/scikit-learn · Ultralytics YOLOv8 + ByteTrack · folium/matplotlib · GAMA Platform
(GAML) · KoboToolbox/ODK · HuggingFace `datasets`. Documentation must state this, not the
brief's placeholder.

---

## 5. What is the actual scientific contribution?

### 5.1 The contribution (this is what the repository exists to carry)

1. **A field campaign and its protocol.** 363 smartphone measurements across 3 Hanoi sites
   (Ocean Park 184, Hoan Kiem 99, Vinh Tuy 80), with the XLSForms, the cross-calibration
   procedure, and an explicit metrological framing (`L_A,25s`, relative not absolute).
   `field/`, `data/…/measurements.csv`, `paper/sections/metrology.md`.
2. **An honest-evaluation framework, and the negative results it produced.** Three CV
   protocols (600 m spatial blocks, 300 m buffered LOO, leave-one-site-out), 7–8 models,
   bootstrap CIs, and code-driven model selection. It shows the model ranking **inverts**
   between permissive and strict protocols — the signature of learning spatial
   autocorrelation. `scripts/evaluate_models.py`, `outputs/models/model_comparison.md`,
   `paper/sections/negative_results.md`.
3. **The delivered model is a 3-parameter physical kernel**, `E = A_hw/d_hw + A_res/d_res + B`,
   which beats every learned model including the physics+ML hybrid the team itself had
   recommended. A team publishing the result that refutes its own recommendation is the
   most transferable thing here.
4. **Traffic flow from video, and its negative result.** YOLOv8 + ByteTrack line-crossing
   counts on 147 videos, with three counting bugs found and documented; flow still does not
   correlate with level, except at the one true transit corridor (Vinh Tuy). Density → flow
   was necessary but not sufficient. `scripts/experiments/count_vehicles.py`.
5. **A GAMA agent-based simulation with corrected physics**, where the `10·log10(k)` factor
   and the "zone 30" bonus apply only to the traffic share of energy — which halved the
   claimed benefit of pedestrianisation (−7.0 dB → −3.5 dB).
6. **The self-audit** (`audit_noise_modeling.md`) and the **retraction trail**
   (`outputs/deprecated/README.md`, the withdrawn R² = 0.45). Documented retraction is rare
   and is itself a reusable asset.
7. **Literature anchoring** as a substitute for the sound-level meter the team never had.

### 5.2 The noise (no scientific content)

`.venv/` · `cache/` · `scripts/__pycache__/` · `" "/.workspace1/` · `.workspace0/` ·
Eclipse `.project`/`.settings` · Google-Drive-named download folders · notebook stored
outputs · the 6.7 MB of retracted Bach Khoa payload · the pre-pivot HTML deck.

### 5.3 In between — decisions required, not defects

The 6 GB of video, the two 11 MB pickles, the 85 regenerable shapefiles, and the two
third-party PDFs. Each is defensible; none should be settled silently.

---

## 6. Open questions

Grouped so they can be answered in one pass. Nothing in Phase 1 is blocked by them except
where noted.

**A — Identity and authorship (blocks `CITATION.cff`, `README`, the title slide)**
1. Exact institution and lab: is it VinUniversity, Hanoi? Which college/lab? Any partner
   institution?
2. Team composition: how many people, full names, roles, ORCIDs if any, and who is the
   corresponding author?
3. Supervisor(s) to credit, and internship start/end dates (git says first commit
   2026-06-01; today is 2026-08-11 — is the end date the same as the presentation date?)
4. Preferred citation form, and do you want a Zenodo DOI (§F)?

**B — Remote and history (blocks Phase 6, and only Phase 6)**
5. `origin` currently pushes to GitLab **and** Codeberg. Do we replace it with the GitHub
   target, or add GitHub as a second remote and keep the others as mirrors?
6. Does `github.com/Colauz/noise-modelling-hanoi` already exist, and is it empty? Is
   `Colauz` your account or a shared one?
7. Push the full 12-commit history (French commit messages, includes retracted artefacts),
   or start the public repo from a clean squashed baseline? *My recommendation: keep the
   history — the retraction trail is an asset, and rewriting it loses provenance.*

**C — Language (affects the size of Phase 2/3)**
8. The rule is "everything published in English". Today, French: `ROADMAP.md` (14 KB),
   `audit_noise_modeling.md` (48 KB), `paper/sections/*.md` (38 KB), all script docstrings
   and comments, all `.gaml` comments, all 12 commit messages. Full translation is roughly
   100 KB of technical prose. Options: (a) translate everything, (b) translate the
   front-facing docs and keep the internal audit/sections French with an English abstract,
   (c) English README/docs + bilingual note. Which?

**D — Data publication and ethics**
9. The 147 videos (6 GB) contain faces and licence plates. What is the VinUni IRB status?
   Until it is settled, my default is: **do not publish the videos**, publish only the
   derived `vehicle_counts.csv`. Confirm?
10. Can `measurements.csv` (363 rows, GPS + dB, collectors already pseudonymised) be
    published openly under CC-BY-4.0? Any restriction on precise GPS coordinates?
11. Where should the videos live: Zenodo (restricted access), Google Drive, an institutional
    server, or nowhere public with only a request procedure documented?

**E — Content decisions**
12. `outputs/slides_presentation.html` (2026-07-31, contains the withdrawn R² = 0.45): move
    to an `archive/` folder with a warning banner, or delete from `HEAD` (keeping it in
    history)?
13. `outputs/deprecated/` payload (6.7 MB of Bach Khoa artefacts): same question — I propose
    keeping only its `README.md`, which documents the retraction.
14. `paper/references/*.pdf`: may I remove both PDFs from the public repo and replace them
    with DOI links? If you want to keep the *Scientific Data* one, I need to verify its
    CC-BY licence first. And what is the provenance of `Survey_Paper_Noise_Modelling (1).pdf`?
15. `scripts/experiments/barcelona_transfer.py`: is the Barcelona work abandoned (README
    still references `data/raw/barcelona`)? Keep the script as a documented dead end, or
    remove it?
16. Do you want `outputs/gama_inputs/` (85 files, 14 MB, one command regenerates it) to stay
    tracked so GAMA users can run the model without a Python environment? *My
    recommendation: yes, keep it — it is the only way a GAMA-only user can open the model.*
17. The two 11 MB `.pkl` models: re-export as portable LightGBM `.txt`, keep as Git LFS, or
    move to Zenodo?

**F — Scope of the remaining phases**
18. Phase 4 asks for 15–25 verified references. Confirm the count, and confirm I should
    treat `paper/bibliography.bib` as a candidate list to **verify entry by entry** rather
    than trust it (I will mark anything unverifiable `[À VÉRIFIER]`).
19. Phase 5: presentation date, audience (defence jury? lab seminar? handover meeting?),
    and does 20 min / 18–22 slides still hold?
20. Is the Overleaf manuscript (linked in the README) in scope for this restructuring, or
    strictly out of scope?

---

## 7. Proposed disposition summary

| Verdict | Count (approx.) | Volume |
|---|---|---|
| **KEEP** (moves into the new structure) | ~120 tracked files | ~25 MB |
| **ARCHIVE** (out of `HEAD`, kept in history or an `archive/` folder) | 6 items | ~8.6 MB |
| **DELETE** (untracked junk only) | 3 directories | ~32 KB |
| **CLARIFY** (needs a decision above) | 8 items | ~28 MB + 6 GB of video |

No deletion, move or push will happen without explicit approval.

# Reproduce the study. `make help` lists the targets.
#
# The critical path -- setup, features, models, results -- runs from the two
# datasets versioned in data/processed/. It needs neither the raw Kobo export
# nor the 147 traffic videos, which are not published. That is what makes the
# results reproducible by someone outside the team.

PYTHON ?= python3
SCRIPTS = scripts

.DEFAULT_GOAL := help
.PHONY: help setup data features models results report dashboard simulate all test clean clean-all

help:  ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
	 | awk 'BEGIN{FS=":.*?## "}{printf "  \033[1m%-12s\033[0m %s\n", $$1, $$2}'

setup:  ## Install the package and its dependencies (editable)
	$(PYTHON) -m pip install -e .

# --- data -------------------------------------------------------------------
# Both targets need inputs that are NOT published. They are here for the team
# that holds them; an external user starts at `features`.
data:  ## Rebuild measurements.csv from the raw Kobo export (needs data/raw/kobo/)
	$(PYTHON) $(SCRIPTS)/01_prepare_field_data.py

counts:  ## Recount vehicles from the 147 videos (needs data/raw/videos/ + a GPU, ~26 min)
	$(PYTHON) $(SCRIPTS)/02_count_vehicles.py

# --- the reproducible chain -------------------------------------------------
features:  ## OSM morphology features for the measurement points
	$(PYTHON) $(SCRIPTS)/03_build_features.py

models: features  ## Evaluate 8 models under 3 CV protocols, select and write the delivered one
	$(PYTHON) $(SCRIPTS)/04_evaluate_models.py

results: models  ## Emission calibration, literature anchoring, GAMA inputs, validation, figures
	$(PYTHON) $(SCRIPTS)/05_calibrate_emissions.py
	$(PYTHON) $(SCRIPTS)/06_anchor_literature.py
	$(PYTHON) $(SCRIPTS)/07_export_gama_inputs.py
	$(PYTHON) $(SCRIPTS)/08_validate_simulation.py
	$(PYTHON) $(SCRIPTS)/09_build_field_map.py

report: results  ## Build the 8-page PDF report (reads models/metrics.json)
	$(PYTHON) $(SCRIPTS)/10_build_report.py

dashboard: results  ## Build the static HTML dashboard
	$(PYTHON) $(SCRIPTS)/11_build_dashboard.py

all: report dashboard  ## Everything above, in order

simulate:  ## Print how to run the GAMA model (needs the GAMA Platform GUI)
	@echo "Open simulation/gama/hanoi_noise.gaml in GAMA, run experiment hanoi_noise_sim."
	@echo "Headless, 3 cycles:  see simulation/gama/README.md"

test:  ## Run the test suite
	$(PYTHON) -m pytest -q

# --- housekeeping -----------------------------------------------------------
clean:  ## Remove regenerable results and interim data (never data/raw)
	rm -rf results/report/report.pdf results/report/dashboard
	rm -f data/interim/features.parquet
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +

clean-all: clean  ## Also drop the OSM caches (they will be re-downloaded)
	rm -f data/interim/hanoi_sites_buildings.gpkg data/interim/hanoi_sites_roads.graphml

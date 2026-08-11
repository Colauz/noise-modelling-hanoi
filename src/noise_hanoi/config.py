"""Project paths and parameters, resolved once.

Every script in `scripts/` imports its paths from here. Before this module
existed, each of the thirteen scripts recomputed the project root with its own
`os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` and then spelled
out its own literals, so a directory rename meant thirteen edits and any one of
them could be missed silently.

Paths are plain strings, not `Path` objects, because the calling code passes
them to `os.path.join`, to string concatenation and to pandas/geopandas
readers interchangeably.
"""

from __future__ import annotations

import os
from pathlib import Path

# src/noise_hanoi/config.py -> src/noise_hanoi -> src -> project root
ROOT: str = str(Path(__file__).resolve().parents[2])

# --- data -------------------------------------------------------------------
DATA = os.path.join(ROOT, 'data')
RAW = os.path.join(DATA, 'raw')
INTERIM = os.path.join(DATA, 'interim')
PROCESSED = os.path.join(DATA, 'processed')

#: Raw Kobo/ODK exports. Carry collector identities -- never published.
KOBO_DIR = os.path.join(RAW, 'kobo')
#: The 147 traffic videos. Carry faces and plates -- never published.
VIDEO_DIR = os.path.join(RAW, 'videos')
#: XLSForms: the survey instrument itself, published.
FORMS = os.path.join(DATA, 'forms')

#: The 363 field measurements, pseudonymised. The primary dataset.
MEASUREMENTS = os.path.join(PROCESSED, 'measurements.csv')
#: Line-crossing counts for the 147 videos, ~26 min of GPU to regenerate.
VEHICLE_COUNTS = os.path.join(PROCESSED, 'vehicle_counts.csv')

# OSM extracts, regenerable but slow and subject to upstream drift.
BUILDINGS_GPKG = os.path.join(INTERIM, 'hanoi_sites_buildings.gpkg')
ROADS_GRAPHML = os.path.join(INTERIM, 'hanoi_sites_roads.graphml')
#: Morphology features for the measurement points, built by 03_build_features.
FEATURES = os.path.join(INTERIM, 'features.parquet')

# --- fitted models ----------------------------------------------------------
MODELS = os.path.join(ROOT, 'models')
#: Single source of truth for every published number. Never copy a metric by hand.
METRICS_JSON = os.path.join(MODELS, 'metrics.json')
MODEL_COMPARISON_MD = os.path.join(MODELS, 'model_comparison.md')
FINAL_MODEL = os.path.join(MODELS, 'surrogate_lgbm_hanoi_direct.txt')
RESID_MODEL = os.path.join(MODELS, 'hybrid_residual_lgbm.txt')
PHYS_JSON = os.path.join(MODELS, 'hybrid_physical.json')
UGANDA_MODEL = os.path.join(MODELS, 'surrogate_lgbm_large.txt')
UGANDA_MODEL_V2 = os.path.join(MODELS, 'surrogate_lgbm_v2_uganda.txt')

# --- results ----------------------------------------------------------------
RESULTS = os.path.join(ROOT, 'results')
FIGURES = os.path.join(RESULTS, 'figures')
MAPS = os.path.join(RESULTS, 'maps')
TABLES = os.path.join(RESULTS, 'tables')
REPORT_DIR = os.path.join(RESULTS, 'report')
REPORT_PDF = os.path.join(REPORT_DIR, 'report.pdf')
DASHBOARD_DIR = os.path.join(REPORT_DIR, 'dashboard')
NOISE_MAP_CSV = os.path.join(MAPS, 'hanoi_noise_map.csv')
FIELD_MAP_HTML = os.path.join(MAPS, 'hanoi_field_points.html')

# --- simulation -------------------------------------------------------------
SIMULATION = os.path.join(ROOT, 'simulation', 'gama')
#: GIS inputs read by hanoi_noise.gaml, tracked so a GAMA-only user can run.
GAMA_INPUTS = os.path.join(SIMULATION, 'inputs')

# --- parameters -------------------------------------------------------------
#: UTM 48N. Metric CRS used for every distance and area computation.
CRS_HANOI = 'EPSG:32648'
#: Radius over which morphology is aggregated around a point, in metres.
FEATURE_RADIUS_M = 300
#: Exclusion radius of the buffered leave-one-out protocol. Must equal
#: FEATURE_RADIUS_M: a smaller value leaks, which is what produced the
#: withdrawn R2 = 0.45. See docs/audit/scientific-audit.md section 4.3.
BLOO_RADIUS_M = 300
#: Side of the spatial blocks of the block cross-validation, in metres.
BLOCK_SIZE_M = 600
#: Grid resolution of the published noise map, in metres.
GRID_STEP_M = 40
#: Margin added around the sampled envelope. Never predict beyond it.
GRID_MARGIN_M = 400
#: Hours covered by the map. The campaign ran 05:00-23:00.
HOURS = tuple(range(5, 22))

#: The three measured sites, and the shapefile slug each one exports under.
SITES = {
    'Ocean Park': 'oceanpark',
    'Hoan Kiem': 'hoankiem',
    'Vinh Tuy': 'vinhtuy',
}


def ensure_output_dirs() -> None:
    """Create the output directories a script writes into, if missing."""
    for d in (INTERIM, PROCESSED, MODELS, FIGURES, MAPS, TABLES,
              REPORT_DIR, DASHBOARD_DIR, GAMA_INPUTS):
        os.makedirs(d, exist_ok=True)

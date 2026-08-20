# tests/

Small, and aimed at the failures this project actually had rather than at coverage.

| File | The failure it guards against |
|---|---|
| `test_cv_protocols.py` | The 110 m vs 300 m leak that produced the withdrawn R² = 0.45 |
| `test_grid_extent.py` | The Bach Khoa map, published over a district where nothing was measured |
| `test_features_extraction.py` | Drift in the features that feed every published number |
| `test_field_cleaning.py` | Public submissions sharing one `collector` value, and de-duplicating each other away |

Run with `make test`. Tests needing the unpublished OSM extract skip themselves.

Still to write: `test_report_guard.py` (the report refuses to build without
`metrics.json`).

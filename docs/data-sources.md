# Data sources

Every dataset the study touches: where it comes from, what licence it carries,
when it was accessed, what it contains, and whether this repository publishes it.

Affiliation of the collecting team: [AFFILIATION TO CONFIRM — CEI or COSMOS Lab],
VinUniversity, Hanoi, Vietnam.

---

## Summary

| Dataset | Origin | Published here | Licence |
|---|---|---|---|
| Field measurements (363) | Our campaign, Jun–Jul 2026 | **Yes** — `data/processed/measurements.csv` | CC-BY-4.0 |
| Vehicle counts (147 videos) | Derived from our videos | **Yes** — `data/processed/vehicle_counts.csv` | CC-BY-4.0 |
| Survey forms | Our XLSForms | **Yes** — `data/forms/` | CC-BY-4.0 |
| Traffic videos (147, 6.0 GB) | Our campaign | **No** — see Ethics below | not distributed |
| Raw Kobo exports | KoboToolbox | **No** — contain collector identities | not distributed |
| OpenStreetMap extract | OSM contributors | **No** — regenerable | ODbL |
| Weather | Open-Meteo | **No** — regenerable | CC-BY-4.0 |
| Sunbird Urban Noise Uganda 61K | Nsumba et al. 2026 | **No** — gated upstream | see below |

---

## 1. Field measurements — `data/processed/measurements.csv`

**Origin.** Our own campaign, three sites in Hanoi, June–July 2026. Collected with
ODK Collect against a KoboToolbox server; sound levels read from Decibel X on
consumer smartphones. Protocol in [`field-protocol.md`](field-protocol.md).

**Size.** 363 rows. Ocean Park 184, Hoan Kiem 99, Vinh Tuy 80.

**Schema.**

| Column | Type | Meaning |
|---|---|---|
| `latitude`, `longitude` | float, WGS 84 | Receiver position, full precision (see §1.1) |
| `noise_dB` | float | A-weighted level over 20–30 s, `L_A,25s` — **not** a certified `L_Aeq` |
| `timestamp` | datetime | Local time (UTC+7) |
| `class` | str | Dominant source category declared in the field |
| `site` | str | One of the three sites |
| `hour`, `is_weekend` | int | Derived from `timestamp` |
| `temperature_2m`, `wind_speed_10m`, `precipitation` | float | Open-Meteo, joined on time and place |
| `dist_to_road` | str | Declared distance band to the nearest road |
| `count_motorbikes`, `count_cars`, `count_heavy`, `count_ev` | int | Manual counts, sparse |
| `construction_nearby` | str | Audible construction, yes/no |
| `dist_to_source_m` | float | Declared distance to the dominant source |

**What it does not contain.** No collector name, no device identifier, no audio,
no free-text note. Those columns exist in the raw Kobo export and are removed by
`scripts/01_prepare_field_data.py`. The raw export is not published.

**Measurement status.** The three phones were cross-calibrated **against each
other and never against a reference instrument**. Contrasts between places and
hours are supported; absolute levels are indicative. No compliance claim is made
anywhere in this repository. See [`metrology.md`](metrology.md).

### 1.1 Why the coordinates are published at full precision

The coordinates locate a **measuring instrument on a public street**, not a
dwelling. Rounding them would break the model–field validation, which compares a
predicted 40 m grid cell against the point where the level was actually read: an
uncertainty added on top of the existing GPS uncertainty would make the residuals
uninterpretable. Reproducibility of the validation requires the receiver position.

**Verification performed** (2026-08-11). All 363 points were tested against the
OSM building footprints of the three sites, and the 26 containing footprints were
looked up by way ID against the live OpenStreetMap API to read their `building`
tag.

| Footprint class | Footprints | Points |
|---|---|---|
| `apartments` (named towers, 26–35 storeys) | 10 | 10 |
| `house`, `terrace` | 3 | 3 |
| `commercial`, `office`, `construction` | 4 | 4 |
| `building=yes`, no further specification | 9 | 9 |
| **Total** | **26** | **26** |

So 13 of the 363 points (3.6 %) fall inside a footprint tagged residential.

**How far inside they fall is the decisive figure.** Distance from each point to
the boundary of the polygon containing it:

- median **2.7 m**, maximum **7.1 m**;
- GPS accuracy declared by ODK: median 4.9 m, p90 5.0 m, **maximum 9.0 m**;
- **no point lies deeper inside a residential footprint than the worst GPS
  accuracy recorded during the campaign**, and only 5 exceed the p90.

Three further facts point the same way. The ten `apartments` footprints are named
high-rise towers of 26 to 35 storeys with footprints roughly 40–50 m on a side —
precisely the geometry that degrades smartphone GNSS through multipath, and
always toward the tower. The field metadata of these 13 points records distances
to the road of `2-10 m`, `10-30 m`, `30-60 m` and, for two of them,
`> 60 m / behind building`: outdoor positions by the collector's own note. And
their levels, 55.0 to 72.1 dB, are consistent with outdoor readings.

**Conclusion.** The containment is a positional artefact of urban-canyon GNSS
error, not evidence of measurement inside private property. The protocol
(outdoors, phone at ~1.2 m, recorded distance to the road) is incompatible with
an indoor reading. Full-precision coordinates are published on that basis. No
blanket rounding has been applied, and no individual point has been moved.

The 26 footprint IDs and per-point depths are reproducible from
`data/processed/measurements.csv` and the OSM extract; the analysis is described
here rather than shipped as a script because it is a one-off provenance check.

---

## 2. Vehicle counts — `data/processed/vehicle_counts.csv`

**Origin.** Derived from the 147 traffic videos by `scripts/02_count_vehicles.py`
(YOLOv8 + ByteTrack, 10 fps, line-crossing counts). Roughly 26 minutes of GPU to
regenerate, which is why the result is versioned and the input is not.

**Content.** One row per video: per-class flow in vehicles per minute, per-class
mean density, the matched measurement and its level. Non-identifying aggregates.

**Known limitation.** The detector has never been validated against a manual
reference count. Precision, recall and MAPE per class are unknown. **The modal
shares must not be published until that validation exists** — see
[`handover.md`](handover.md).

---

## 3. Traffic videos — not published

**What was collected.** 147 videos, 6.0 GB, filmed June–July 2026 from the public
street, camera pointed at the roadway, for the sole purpose of counting vehicles.
Filenames carry the capture timestamp, which is how each video is matched to its
measurement.

**Where they are.** Held locally by the team, outside the repository and outside
git history. They are consolidated in `data/raw/videos/` on the working machine.

**Why they are not published.** Volume, and the fact that the originals contain
identifiable faces and vehicle registration plates. See Ethics below.

---

## 4. OpenStreetMap extract — not published, regenerable

**Origin.** OpenStreetMap via OSMnx, downloaded around the three sites with a
margin large enough that the 300 m feature disc of every edge point is complete.

**Files.** `data/interim/hanoi_sites_buildings.gpkg` (49 146 building footprints)
and `data/interim/hanoi_sites_roads.graphml`.

**Access date.** 2026-08-05. **This matters**: OSM is a moving database, so a
re-download on another date will not reproduce these files exactly, and small
changes in the building layer shift `built_area_ratio`. Treat the extract as an
input with a date, not as something to refetch silently.

**Licence.** ODbL 1.0, © OpenStreetMap contributors. Derived works must attribute.

---

## 5. Weather — not published, regenerable

Hourly temperature, wind speed and precipitation from the **Open-Meteo** historical
API, joined to each measurement on time and place by
`scripts/01_prepare_field_data.py`. Licence CC-BY-4.0. No robust weather effect was
found in the data.

---

## 6. Sunbird Urban Noise Uganda 61K — not published, gated upstream

**Origin.** Nsumba, S., Muhanguzi, T., Ouma, E. N., Sekalala, I., Bainomugisha, E.,
Mwebaze, E. & Quinn, J. *Noise mapping and ambient sound recordings of the urban
environment in Uganda.* Scientific Data (2026).
<https://doi.org/10.1038/s41597-026-06658-w>

Dataset: <https://huggingface.co/datasets/Sunbird/urban-noise-uganda-61k>

**Use here.** Notebooks 01–06 reproduce the descriptor's figures 8–10 and train a
morphology→level surrogate, which is then transferred to Hanoi. The transfer fails
(R² < 0), which is one of the study's three negative results.

**Access.** Gated: accept the terms on the dataset page, create a read token, and
export it as `HF_TOKEN` before running notebooks 01–05. Never commit a token.
Nothing from this dataset is redistributed here.

---

## Ethics and data handling

This section is descriptive. It records what was done and what was not.

**What was collected.** 147 videos, filmed from the public street, pointed at the
roadway, for the purpose of counting vehicles. Alongside them, 363 spot sound
measurements with GPS positions, and short audio clips submitted through the Kobo
form for quality control.

**What is published.** Only `data/processed/vehicle_counts.csv`, which contains
non-identifying aggregates (per-class flow and density per video), and
`data/processed/measurements.csv`, which contains no personal data. **No video, no
image and no individual frame is distributed, and none will be.**

**What was not done.** **No institutional ethics review was requested for the video
collection.** No approval, no exemption and no finding of compliance was sought or
obtained, and none is claimed anywhere in this repository or in any output derived
from it. The videos were not anonymised at source: faces and registration plates
are present in the originals, which is one reason they are not distributed.

**Retention.** Originals are held by the project team at VinUniversity, outside the
repository. Custodian, storage location and the deletion or anonymisation deadline:
**[SUPERVISOR DECISION]**.

**Recommendation to the team taking over.** Submit the protocol to the VinUniversity
ethics committee before any further collection campaign, and before any publication
that relies on the video material beyond the aggregate counts already released. A
documented limitation is acceptable in a research record; a compliance claim that
was never granted is not.

---

## Licences of this repository's own outputs

| What | Licence |
|---|---|
| Code (`src/`, `scripts/`, `simulation/`, `tests/`) | MIT — see `LICENSE` |
| Data, documentation, figures, maps | CC-BY-4.0 — see `LICENSE-DATA` |

Attribution for the derived OSM layers in `simulation/gama/inputs/` remains due to
OpenStreetMap contributors under ODbL.

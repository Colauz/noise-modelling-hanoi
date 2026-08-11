# data/

Local by default. Only two curated datasets and the survey forms are versioned;
everything else stays on the collecting team's machines. Provenance, licence and
schema of every source: [`../docs/data-sources.md`](../docs/data-sources.md).

| Path | Versioned | What |
|---|---|---|
| `forms/` | yes | The two XLSForms: the survey instrument itself |
| `processed/measurements.csv` | yes | 363 field measurements, pseudonymised. **The primary dataset** |
| `processed/vehicle_counts.csv` | yes | Line-crossing counts for 147 videos, ~26 min of GPU to rebuild |
| `raw/kobo/` | no | Raw Kobo exports. Contain collector identities |
| `raw/videos/` | no | 147 traffic videos, 6.0 GB. Faces and plates — never published |
| `interim/` | no | OSM extract and computed features. Regenerable |

`raw/` is immutable: nothing in this repository ever writes to it.

The two versioned CSVs are re-includable through explicit `.gitignore` negations.
Do not re-add data files with `git add -f` — if a file belongs in git, give it a
rule. The previous layout relied on force-adds and nearly lost both of them.

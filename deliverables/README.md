# deliverables/

End-of-internship package by Laurian Jamin and Lucas Zborowski, drafted
24 August 2026, revised 28 August 2026. Nothing here has been sent or submitted.

| File | What |
|---|---|
| `internship_report.pdf` | The full progress report, 24 pages, 12 figures. Source: `internship_report.tex` |
| `overleaf/` | Self-contained 4-page short paper. Zip it and upload |
| `email_draft.md` | Transmittal e-mail, with the addresses left as placeholders. **Not versioned** — it names real people and is git-ignored; it exists only in a local working copy |
| `figures/` | The figures the report uses, copied from the repository's own generators |
| `appscreens.tex` | The application's five screens, drawn in TikZ from the Compose source. Shared verbatim with `presentation/appscreens.tex` |
| `refs.bib` | `docs/references.bib` with the internal `note = {...}` status annotations stripped |

## Rebuilding

```bash
cd deliverables
pdflatex internship_report && bibtex internship_report && \
  pdflatex internship_report && pdflatex internship_report

cd overleaf
pdflatex main && bibtex main && pdflatex main && pdflatex main
```

`overleaf/` was verified to compile from a clean copy of `main.tex`, `refs.bib`
and `figures/` alone, with `pdflatex` and no exotic packages. To hand it over:

```bash
cd overleaf && zip -r ../hanoi-short-paper.zip main.tex refs.bib figures main.pdf
```

## Where the figures come from

No figure was drawn for these documents. `campaign.pdf`, `ranking-inversion.pdf`,
`forest-bloo.pdf`, `ceiling.pdf`, `map-grid.pdf`, `discontinuity.pdf`,
`feature-importance.pdf`, `hanoi-sites.pdf`, `exceedance.pdf`,
`class-levels.pdf` and `campaign-frame.pdf` are produced by
`scripts/12_presentation_figures.py`, which reads `models/metrics.json`,
`data/processed/measurements.csv`, `results/maps/hanoi_noise_map.csv`,
`results/tables/hanoi_exceedances.csv`, `data/processed/hanoi_wards.geojson`
and the road shapefiles under `simulation/gama/inputs/` — and types no number of
its own. `validation_simulation.png` comes from `scripts/08_validate_simulation.py`.

Three figures are new. `hanoi-sites.pdf` is the map of the whole campaign: all
363 measurements on the street network they were taken in, at city scale and
then in three same-scale detail panels. There is no basemap and no tile server
behind it — the roads are the OSMnx extracts the GAMA simulation already runs
on, which is why the space between the three areas is blank: it was never
extracted, because it was never measured. `exceedance.pdf` draws the QCVN
exceedance table with the sample size inside every bar, because the night bars
are the ones a reader will quote and the ones the campaign cannot support.
`class-levels.pdf` puts level against the source class the operator recorded.

`campaign-frame.pdf` (§6.2) maps the frame the *planned* campaign draws from —
Hanoi's 51 urban *phường* under the July 2025 reform — against the 1.7 km² this
campaign actually covered. **Nothing on it is a site.** The 160 sites have not
been drawn, and 160 invented coordinates would commit the team to a sample
nobody selected, so the map shows the frame and the step, not a fake draw.

Drawing it turned up something. **Ocean Park is not in a *phường*** — all 184
of its measurements, half this campaign, fall inside *Xã Gia Lâm*, a rural
commune the frame as specified excludes. Nothing in the results changes; the
plan does. Either the frame widens to admit the peri-urban *xã*, or the one
area the project knows best contributes nothing to the design of the next
campaign. The report states it as a decision for whoever fixes the protocol.

The ward boundaries are committed as `data/processed/hanoi_wards.geojson`.
`scripts/fetch_hanoi_wards.py` regenerates them from OpenStreetMap and is the
only script in the project that touches the network — which is why it is
unnumbered and outside the pipeline, and why no figure calls it.

The script was re-run on 28 August 2026. The one change against the previously
committed figures is the noise map's colour ramp. The old one ran
green → yellow-green → lime → yellow (`#7CB342`, `#C0CA33`, `#F9A825`) and its
three middle bands sat at nearly the same lightness, so `55–60`, `60–65` and
`65–70` — most of the mapped area — printed as a single washed-out band. The
ramp is now ordered by lightness and survives greyscale. **Green is also no
longer used as a font colour anywhere in the figures** — set as type it read as
a highlighter; every label that was green is now ink, and the line beside it
still carries the meaning. The same ramp was
carried into the app's `levelColour()` (`mobile/.../ui/Theme.kt`) and into the
screen mock-ups, so the three stay in step. **No number moved.**

The application's screens in the report are the vector mock-ups of
`appscreens.tex`, not device captures: nobody has yet run the app on a handset
in front of a calibrated source, and a screenshot would imply otherwise.

## Rule followed throughout

Every number is quoted from a repository artefact and the artefact is named where
the number appears.

Earlier drafts carried `[TO CONFIRM: ...]` marks for anything the repository did
not establish, collected in an appendix. Those are gone: the affiliation is
**COSMOS Lab**, the report is submitted jointly by both authors, and the one
genuine gap behind a mark — the author list of `anh2024motorcycle`, which was
literally `{[AUTHORS TO CONFIRM]}` in the `.bib` — was resolved from the DOI
rather than deleted.

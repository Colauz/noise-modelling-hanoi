# deliverables/

End-of-internship package, drafted 24 August 2026. Nothing here has been sent,
pushed or submitted.

| File | What |
|---|---|
| `internship_report.pdf` | The full progress report, 19 pages. Source: `internship_report.tex` |
| `overleaf/` | Self-contained 4-page short paper. Zip it and upload |
| `email_draft.md` | Transmittal e-mail, with the addresses left as placeholders. **Not versioned** — it names real people and is git-ignored; it exists only in a local working copy |
| `figures/` | The figures the report uses, copied from the repository's own generators |
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
`forest-bloo.pdf`, `ceiling.pdf`, `map-grid.pdf`, `discontinuity.pdf` and
`feature-importance.pdf` are produced by `scripts/12_presentation_figures.py`,
which reads `models/metrics.json`, `data/processed/measurements.csv` and
`results/maps/hanoi_noise_map.csv` and types no number of its own.
`validation_simulation.png` comes from `scripts/08_validate_simulation.py`.

The script was re-run on 24 August 2026 and its output is identical to the
committed versions apart from PDF creation timestamps.

## Rule followed throughout

Every number is quoted from a repository artefact and the artefact is named where
the number appears. Anything the repository does not establish is marked
`[TO CONFIRM: ...]` in place and collected in Appendix A of the report — never
filled in by judgement.

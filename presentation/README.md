# presentation/

End-of-internship presentation. LaTeX Beamer, *metropolis* theme, 16:9.

```bash
make -C .. slides    # figures from the pipeline, then the deck   <- start here
make                 # -> main.pdf   (47 slides incl. 4 backup)
make notes           # -> main-notes.pdf, presenter notes beside each slide
make logos           # report which institutional marks are present
make ENGINE=lualatex # better typography if your TeX Live can load system Lato
```

## What is in it

| Section | Slides | |
|---|---|---|
| Context and research questions | 3 | The gap, the four questions, related work by function |
| Data and protocol | 2 | The campaign **with its two distributions drawn**, and the metrology |
| Method and evaluation protocol | 3 | The chain, the three CV splits, the model roster |
| Results | 6 | **The inversion as a slope chart**, the kernel, **the ceiling on $R^2$**, **the map redrawn in English**, what the learned model leaned on, the three negative results |
| **Auditing our own data** | 5 | The retracted R² = 0.45, then a second audit **of the measurements**, with the 27 June break drawn |
| **From a pipeline to an instrument** | 8 | The three-month arc, **the four application screens**, architecture, engineering results, **the three blockers before a public release** |
| **Next: Clermont-Ferrand** | 3 | Three upgrades, the two-city comparison, staged programme |
| Conclusion | 3 | **The two things a reviewer will press on**, then what the work established |
| Backup | 4 | **Every formula the talk rests on**, the forest plot of every interval, the bias interval, what is published |

Every slide carries a `\note{}`.

## Rules the deck follows

- **No number is typed by hand.** Everything traceable comes from
  `models/metrics.json`, `models/model_comparison.md` and `results/tables/` —
  including every figure, which `scripts/12_presentation_figures.py` renders
  from those files rather than from a saved image.
- **R² = 0.45 and the WHO 53/45 values appear only as retractions.**
- **Nothing claims regulatory compliance.** QCVN thresholds are shown
  descriptively and said to be descriptive.
- **Confidence intervals travel with the point estimates** — the summary slide
  gives the ranking, the backup forest plot gives the intervals that qualify it.

## Typography

Three sizes, and no fourth. Set once in the preamble, never inline:

| | | |
|---|---|---|
| body | `\footnotesize` | every sentence on every slide |
| `\src{}` | `\scriptsize`, typewriter | a **file path** |
| `\aside{}` | `\scriptsize`, roman | a caption, a citation, an aside |

Figures go through `\fig[<height>]{<file>}{<path>}`. The optional argument is a
fraction of the **frame's text height**, not of the column width: height is the
dimension that overflows a slide. A build with zero `Overfull \vbox` warnings is
the check that nothing runs off the bottom edge —

```bash
make clean && make && grep -c 'Overfull .vbox' main.log   # must print 0
```

## Figures

`figures/*.pdf` — vector, English, built by `scripts/12_presentation_figures.py`:

| File | What | From |
|---|---|---|
| `ranking-inversion.pdf` | the slope chart across the three splits | `models/metrics.json` |
| `forest-bloo.pdf` | every model's R² with its 95 % interval | `models/metrics.json` |
| `campaign.pdf` | levels by site and by hour | `data/processed/measurements.csv` |
| `discontinuity.pdf` | the 27 June break | `data/processed/measurements.csv` |
| `feature-importance.pdf` | LightGBM's split gain, in English | `models/metrics.json` |
| `ceiling.pdf` | how much of $R^2$ is reachable at all | `data/processed/measurements.csv` |
| `map-grid.pdf` | the 40 m grid over all three sites at 17:00 | `results/maps/hanoi_noise_map.csv` |

`map-grid.pdf` replaces the GAMA screenshot the deck used to carry. That capture
had a **French legend** and showed one site; this is drawn from the CSV the map,
the report and the app all read, covers all three sites, and regenerates with the
pipeline. Nothing in the deck reads `results/figures/` any more — that set is
French-labelled and partly not regenerable
([`sunbird/NOT-REGENERABLE.md`](../results/figures/sunbird/NOT-REGENERABLE.md)).

## The application screens

[`appscreens.tex`](appscreens.tex) draws four phones — Home, Measure, Map,
Results — in TikZ, from the Compose source in `mobile/.../ui/`. Every string and
colour on them is the app's own, **so they go stale when the app changes**: the
Home screen gained its GAMA card when #9 added one, and the next change to
`HomeScreen.kt` should be followed here too.

**They are mock-ups, not device captures**, and the deck says so on the slide.
Nobody has run the app on a handset in front of a sound source; that is the
limitation the last slide of the app section is about, and presenting a drawing
as a screenshot would contradict the rest of the talk. When real captures exist,
put the PNGs in `screens/` and swap the `\phone...` call for `\includegraphics`.

## Logos

The real marks are in `logos/`, built from `logos/source/` by
[`logos/prepare.py`](logos/prepare.py) — it trims, flattens and optically
balances them, which is what stops a row of logos looking like an accident. See
[`logos/README.md`](logos/README.md). `uca` has no real file yet and still falls
back to a placeholder.

Both the title slide and the closing slide draw the band with one `\logoband`,
so the two cannot drift apart.

## Mathematics

Formulas sit on the slide that uses them — the measured quantity on *Metrology*,
the line-source kernel on *The delivered model*, the traffic decomposition on
*Three engineering results*, the ceiling conversion on the $R^2$ slide. The
backup slide **Every formula this talk rests on** collects all of them, including
the IEC 61672 A-weighting expression, for jumping to under questions.

## Slides to adapt to the audience

| Slide | With the supervisor | With the incoming team |
|---|---|---|
| Title | Go early to the pivot and the negative results | Spend the time on the last third |
| The chain | Compress if short on time | Keep in full |
| *We found one of our own results was wrong* | **Lead with it** | Keep, but after the results |
| *A second audit, on the data itself* | The three findings are open items, not conclusions | Hand over with `docs/audit/` |
| *The application* | One sentence per screen | **The slide they should photograph** |
| *The programme, staged* | The gates are the discussion | Read the S2 row as the to-do list |

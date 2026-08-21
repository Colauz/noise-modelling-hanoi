# presentation/

End-of-internship presentation. LaTeX Beamer, *metropolis* theme, 16:9.

```bash
make -C .. slides    # figures from the pipeline, then the deck   <- start here
make                 # -> main.pdf and script.pdf   (48 slides incl. 4 backup)
make notes           # -> main-notes.pdf, presenter notes beside each slide
make script          # -> script.pdf, what to say on each slide, EN beside FR
make script-short    # -> script-short.pdf, the same talk at 30 s a slide
make formulas        # -> formulas.pdf, every equation explained, EN beside FR
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
| **From a pipeline to an instrument** | 9 | The three-month arc, **the four application screens**, architecture, engineering results, **how GAMA is driven from the phone**, the three blockers before a public release |
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

## The speaker scripts

Two lengths of the same talk. Both are EN | FR: the English is what you say, the
French is the same thing so nobody recites a sentence they do not own. Both share
[`scriptstyle.tex`](scriptstyle.tex), so they cannot drift apart in layout, and
both are held to the deck's slide titles by `check_script.py`.

| | | |
|---|---|---|
| [`script.tex`](script.tex) | **~30 min**, 15 pages | The full version: every slide, the reasoning behind each line, the questions to expect with their answers. |
| [`script-short.tex`](script-short.tex) | **~19 min**, 11 pages | 36 content slides at **30 seconds each**, plus 8 one-sentence section signposts. |

The short one is written to a word budget: about **60 English words a slide**, none
over 75. That is ~25 seconds read aloud, leaving five a slide for the pause, the
pointing and the breath — a cell written to the full 30 seconds is a cell read at
a rush.

**What was cut, and what was not.** Every caveat survived. What went is
elaboration: the second example, the reason behind the reason. A talk can be short
or long; it cannot be short and overclaiming, because the sentence dropped under
time pressure is always the qualifying one.

### The full script

[`script.tex`](script.tex) → `script.pdf`, 15 pages. Every spoken slide, in
order, with **English on the left and French on the right**: the English is what
you say, written to be spoken; the French is the same thing, so nobody recites a
sentence they do not own. It carries the cumulative minute marks, the questions to
expect with their answers, and the three phrases that must never be said in
English (`"we measured 68 dB"`, `"it exceeds the limit"`, `"the app runs GAMA"`).

It is prose. Every number in it is also on a slide, and the slide gets it from
`metrics.json` — if the two disagree, the slide is right.

**Its slide numbers and titles are not its own to invent.**
[`check_script.py`](check_script.py) walks `main.tex` in document order, works out
what lands on which slide, and compares. `make script` runs it and **refuses to
build on drift** — a script that names slide 9 differently from slide 9 is worse
than no script, because the presenter stops trusting it mid-talk.

```bash
make check                        # report drift
python3 check_script.py --fix     # take the deck's titles
```

This caught fifteen paraphrased titles the first time it ran, including *"Metrology
— the spine of the talk"* against the deck's *"Metrology — the constraint everything
else is built around"*.

## The equations

[`formulas.tex`](formulas.tex) → `formulas.pdf`, 10 pages. The eleven equations in
the deck. Each one carries, in this order:

1. the equation;
2. **what it is for** — one line, plain language: what it predicts, what it
   decides, what it draws. *"Predicting a level where nobody measured. This is the
   model that draws all 5 587 cells of the map."*
3. the symbols named;
4. why that form and not another, and **what it refuses to claim** — the half an
   acoustics audience actually tests.

Same EN | FR layout as the script. Step 2 exists because an explanation that only
says what a formula *means* leaves you unable to answer the first thing anyone
asks, which is what it is *for*.

Every number in it was **recomputed from the repository**, not copied off a slide.
One recomputation disagreed with the deck and is flagged in the document rather
than quietly reconciled: slide 12 said two points 110 m apart share *"more than
85 %"* of a 300 m disc; the lens formula gives **76.8 %** (85 % is reached at
71 m). The slide has been corrected — the argument never needed the bigger number,
because the real leak is two points either side of a cell boundary sharing
essentially all of it.

## The application screens

[`appscreens.tex`](appscreens.tex) draws five phones — Home, Measure, Map, GAMA,
Results — in TikZ, from the Compose source in `mobile/.../ui/`. Every string and
colour on them is the app's own, **so they go stale when the app changes**. They
have already been redrawn twice: the Home screen gained its GAMA card, and the Map
screen lost its hour slider and gained the here-and-now reading. When
`mobile/.../ui/` moves, this file moves with it.

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

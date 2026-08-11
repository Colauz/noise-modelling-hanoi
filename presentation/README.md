# presentation/

Handover presentation, LaTeX Beamer, metropolis theme.

```bash
make          # -> main.pdf   (23 slides, 16:9)
make notes    # -> main-notes.pdf, presenter notes beside each slide
```

Every slide carries a `\note{}`. Every figure is traceable to a file named on the
slide itself; no number is typed by hand.

**Slides to adapt to the audience** — flagged in their notes:

| Slide | With the supervisor | With the incoming team |
|---|---|---|
| Title | Go early to the pivot and the negative results | Spend the time on the last third |
| The chain | Compress if short on time | Keep in full |
| The stale validation | **Lead with it** | Keep, but after the results |
| Verify by executing | Summarise | **The slide they should photograph** |
| Handover priorities | Confirm the open items | Hand over `docs/handover.md` and stop |

**Rules the deck follows.** R² = 0.45 and the WHO 53/45 values appear only as
retractions. Sunbird figures are not used. The affiliation is
`[AFFILIATION TO CONFIRM]` on the title slide, matching the rest of the repository.

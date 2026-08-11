# docs/

| Document | What it is |
|---|---|
| [`methodology.md`](methodology.md) | The processing chain end to end, with its assumptions |
| [`data-sources.md`](data-sources.md) | Every dataset: origin, licence, access date, ethics |
| [`field-protocol.md`](field-protocol.md) | How the 363 measurements were taken |
| [`metrology.md`](metrology.md) | Why the target is `L_A,25s` and not a certified `L_Aeq` |
| [`negative-results.md`](negative-results.md) | The three negative results. **The scientific core** |
| [`literature-review.md`](literature-review.md) | Verified references and what each one informed |
| [`references.bib`](references.bib) | BibTeX for the above |
| [`handover.md`](handover.md) | **Start here if you are taking the project over** |
| [`project-timeline.md`](project-timeline.md) | What was done, in what order, and what changed course |
| [`audit/`](audit/) | The August 2026 scientific audit and the repository restructuring |
| [`archive/`](archive/) | Withdrawn work, kept with the reason it was withdrawn |

## Manuscript

The manuscript is written in Overleaf, **which is the source of truth for it**:
<https://www.overleaf.com/project/6a1d529010bdbac6b41da01e>

This repository is the source of truth for everything else — data, code, figures,
numbers. The two are synchronised in one direction only:

- **Numbers and figures flow repository → Overleaf.** No metric is ever typed into
  the manuscript by hand; it comes from `models/metrics.json` or from a figure in
  `results/`. If a number in the manuscript cannot be traced to one of those, it
  is wrong by construction.
- **Prose flows Overleaf → repository at milestones only.** `metrology.md` and
  `negative-results.md` are the two sections drafted here first; when they are
  edited in Overleaf, the updated text is copied back at each milestone (draft
  complete, submission, revision) rather than continuously.
- The compiled PDF is **not** versioned here. Overleaf keeps its own history.

Our June 2026 internal survey, *Environmental Noise Modelling in Hanoi: A
Comparative Review of Old and New Urban Fabrics*, is **not distributed**: the
compiled PDF carries personal e-mail addresses. It returns once recompiled from
source with institutional addresses. Publication status: [À VÉRIFIER].

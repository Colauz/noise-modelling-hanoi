# presentation/logos/

Institutional marks for the title slide and the frame footer.

> **What is in here right now are PLACEHOLDERS, not the institutions' logos.**
> They are neutral typographic slugs — the acronym in the deck's accent colour
> over a rule, with the expansion under it — drawn by
> [`placeholders.tex`](placeholders.tex) so the logo band on the title and
> closing slides is composed and evenly weighted while the real files are being
> obtained. They do not imitate any institution's actual mark and must not be
> presented as one.
>
> **Replace them.** Drop the real files in under the same names and the deck
> picks them up with no edit to `main.tex`. `make -C .. logos-placeholder`
> regenerates the placeholders if you still need them.

**Drop the files here under these exact names.** The deck compiles with or
without them: `main.tex` wraps every logo in `\IfFileExists`, so a missing file
falls back to the institution's name set in type, and nothing breaks.

| Expected file | Institution | Where it appears |
|---|---|---|
| `cosmos.pdf` | COSMOS Lab, VinUniversity | Title slide, closing slide |
| `vinuni.pdf` | VinUniversity | Title slide |
| `isima.pdf` | ISIMA, Clermont-Ferrand | Title slide |
| `uca.pdf` | Université Clermont Auvergne | Future-work section only |

`.pdf` is preferred — it is vector, so it stays sharp when the deck is
projected or printed. `.png` also works with no edit at all: `\logoslot` tries
`.pdf` first, then `.png`, then the text fallback. Supply at least 600 px on the
long edge for a PNG.

Trim the whitespace around the mark before dropping it in; the deck sizes
logos by height (`\logoheight`, 8.5 mm) and a generous
bounding box will make one logo look smaller than its neighbours.

Nothing in this directory is redistributed by the repository's licences: the
LICENSE covers the code and LICENSE-DATA the datasets, and institutional
marks belong to their institutions. Keep them out of any public release of
the deck unless you have permission to reproduce them.

# presentation/logos/

Institutional marks for the title slide and the frame footer.

The marks supplied by the team live in [`source/`](source/) as delivered, and
[`prepare.py`](prepare.py) turns them into the `*.png` files the deck loads:

```sh
python3 presentation/logos/prepare.py
make -C presentation logos          # what the deck will actually find
```

It trims the border, flattens onto white, pads an equal margin back, and applies
a per-mark optical correction. **Trimming is the part that matters**: `main.tex`
sizes logos by *height*, so a mark delivered with a generous margin renders
smaller than its neighbours by exactly that margin's share of the box — the
VinUniversity file arrives 500x500 with the wordmark in a 90 px band, and dropped
in untouched it would come out about a fifth the size of the others.

`placeholders.tex` still generates the neutral typographic slugs the deck used
before the real marks arrived (`make -C presentation logos-placeholder`). They
are **not** the institutions' logos and must never be presented as such; keep
them for a slot that has no real file yet — `uca.pdf` is currently one.

**Drop the files here under these exact names.** The deck compiles with or
without them: `main.tex` wraps every logo in `\IfFileExists`, so a missing file
falls back to the institution's name set in type, and nothing breaks.

| Expected file | Institution | Where it appears |
|---|---|---|
| `cosmos.png` | COSMOS Lab, VinUniversity | Title slide, closing slide |
| `vinuni.png` | VinUniversity | Title slide |
| `isima.png` | ISIMA, Clermont-Ferrand (the mark carries UCA) | Title slide |
| `uca.pdf` | Université Clermont Auvergne | Unused — still a placeholder |

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

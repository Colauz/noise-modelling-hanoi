# Contributing

This repository is a research record as much as a codebase. Most of the rules
below exist because something went wrong once and was fixed; each says which.

## Getting set up

```bash
make setup      # pip install -e .
make test       # 14 tests, all should pass
make features && make models && make results
```

## The two rules that govern where numbers live

They are a pair. Written apart, the first cancels the second on the first
careless reading, so they are written together.

### Rule 1 — one fact, one place of authority

Every published number has exactly one home, and everything else links to it.

| Fact | Authority |
|---|---|
| Model scores, CIs, the delivered model | `models/metrics.json`, `models/model_comparison.md` |
| The chain, its assumptions and limits | `docs/methodology.md` |
| Dataset provenance, licences, ethics | `docs/data-sources.md` |
| What is left to do | `docs/handover.md` |
| Project chronology and decisions | `docs/project-timeline.md` |

**No metric is ever copied by hand into a deliverable.** `10_build_report.py`
reads `metrics.json` and refuses to run without it. If you find a figure in a
document that cannot be traced to its authority, it is wrong by construction.

*Why:* until August 2026 the same R² tables lived in three documents at once, and
the report carried hardcoded strings that had drifted from the model actually
delivered.

### Rule 2 — frozen documents keep their period figures, and are never updated

Rule 1 has one named exception. Some documents are **dated records**, not current
documentation. They keep the figures that were true when they were written, even
when those figures have since been retracted.

**Frozen documents:**

| Document | Frozen at | Contains |
|---|---|---|
| `docs/audit/scientific-audit.md` | 5 August 2026 | The withdrawn R² = 0.45, and every other old-protocol value |
| `docs/audit/INVENTORY.md`, `TARGET-STRUCTURE.md` | 11 August 2026 | The repository as it stood before restructuring |
| `docs/archive/**` | various | Retracted artefacts, with the reason for each |

Each carries a banner saying so. **Do not "correct" them.** An audit whose
figures are updated after the fact documents nothing: its value is that it can be
checked against what was actually claimed at the time. The same holds for a
retraction note — the point is the record of the error.

These documents are **excluded from the number-consistency check** against
`metrics.json`, and that exclusion is deliberate, not an oversight.

## Language

**Everything published is in English**: code, comments, docstrings, documentation,
commit messages, figure labels, log and error messages.

**Sweeping for leftover French: search accents AND keywords.** An accent-only
filter has a blind spot — short French sentences in common vocabulary carry none.
`MAX_CROSS_PER_DIR = 1  # au plus un franchissement par sens` survived several
accent-based passes and was caught by eye. Combine the two, and run the combined
filter over the **whole repository**, not only over the files touched in the
current change.

The project ran in French until 11 August 2026. Commits before that date have
French messages and are left as they are — history is not rewritten here. From
that date on, every new commit is in English.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/), in English:
`feat:` `fix:` `docs:` `refactor:` `chore:` `test:` `data:`.

- **The body explains why, not what.** The diff already says what.
- **Never mix a move with a content change.** `git mv` in one commit, edits in
  the next. A rename buried inside a rewrite is unreviewable.
- **State verifications in the commit.** If you changed something that could alter
  a published number, say what you compared and what the tolerance was.

## Rules that must not be broken

Each has a test or a documented reason behind it.

1. **The buffered leave-one-out radius must never be smaller than the feature
   radius.** Features aggregate over 300 m; a smaller exclusion radius leaks.
   Guarded by `tests/test_cv_protocols.py`.
   *Why:* a `GroupKFold` on ~110 m cells produced the R² = 0.45 that was
   advertised until July 2026 and then withdrawn.
2. **Never publish a prediction outside the sampled envelope** — the three
   measured sites plus 400 m. Guarded by `tests/test_grid_extent.py`.
   *Why:* a noise map was once published over Bach Khoa, a district with zero
   measurements. See `docs/archive/bach-khoa/README.md`.
3. **The delivered model is chosen by code**, under the reference protocol, and
   written into `meta.delivered_model`. Do not override it by hand.
   *Why:* so the published map cannot silently inherit a model that only wins on
   a permissive split.
4. **Never `git add -f`.** If a file belongs in git, give it a `.gitignore` rule.
   *Why:* `measurements.csv` and `vehicle_counts.csv` were tracked from inside
   ignored directories, surviving only on force-adds, with nothing recording the
   fact. In `.gitignore`, note that `#` only starts a comment at the start of a
   line — a trailing comment becomes part of the pattern.
5. **No raw data in git.** No videos, no raw Kobo exports. They carry faces,
   plates and collector identities. See `docs/data-sources.md`.
6. **Call the instrument what it is.** The measurements come from a smartphone
   application, not from a class 1 or class 2 sound level meter. Do not write
   "sound level meter" for our own data, and do not claim regulatory compliance
   anywhere. See `docs/metrology.md`.
7. **Every derived artefact declares its inputs in the Makefile.** If a file in
   `results/`, `models/` or `simulation/gama/inputs/` is produced from another
   tracked file, that dependency belongs in a `make` rule, not in someone's memory.
   *Why:* the published validation validated a grid that had been regenerated after
   it, and nothing anywhere expressed the link. It went unnoticed for six days and
   was found by accident. See `docs/archive/validation-2026-08-05/`.
8. **A date comparison names a suspect; only regeneration convicts it.** An
   artefact whose input has a more recent commit is *stale by date*. It is only
   *stale by content* if its inputs actually changed what it says. Both cases
   occurred here within a week: the published validation had drifted by up to
   15 dB because the grid beneath it was rebuilt, while `hanoi_exceedances.csv`
   was older than its stated inputs and came back **identical**, because its only
   real input, `measurements.csv`, had not moved. Regenerate and diff before
   announcing a problem — and before republishing.
9. **Retracted work is archived with its reason, never silently deleted.**

## Adding a model

Add it to the candidate list in `04_evaluate_models.py`, fixed **in advance** of
seeing the results, and let the selection logic do its work. Report it under all
three protocols. If it wins the permissive split and loses the strict ones, that
is a finding — write it up rather than tuning until it wins.

## Data

Two datasets are versioned: `data/processed/measurements.csv` (363 field
measurements, pseudonymised) and `data/processed/vehicle_counts.csv` (147 video
counts). Everything else under `data/` is local.

Changing either means changing the empirical basis of every published figure.
Regenerate the whole chain (`make all`) and say in the commit what moved.

## Open items

Some metadata is deliberately unfilled and marked `[TO CONFIRM]` rather than
guessed. See the Open items table at the top of `docs/handover.md`. A field
marked to confirm is honest; a field filled in by judgement is not.

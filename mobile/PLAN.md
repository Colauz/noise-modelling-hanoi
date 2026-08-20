# Mobile app — scope, feasibility, plan

*Working document. Written 2026-08-19 after reading the repository; the app itself
is a scaffold at this point. English, like the rest of `docs/`.*

## What is being asked

1. **An ODK Collect replica** — fill the survey form and submit it to a
   KoboToolbox server, the way the campaign already did.
2. **A public APK** — open the collection beyond the two people currently doing
   it, at a scale the draft plan puts at 50 k participants.
3. **Reproduce the pipeline in the app** — from a submitted point to a prediction.
4. **Present the results**, with a GAMA integration.

## What the repository already gives us

| Asset | Where | Use in the app |
|---|---|---|
| The survey instrument | `data/forms/hanoi_noise_form_v2.xlsx` — 18 questions, 5 choice lists | The collection screens, one to one |
| Construction register | `data/forms/hanoi_construction_form.xlsx` — 6 questions | A second, shorter form |
| **The delivered model** | `models/hybrid_physical.json` — 3 parameters | On-device prediction, ~10 lines of Kotlin |
| Predicted map | `results/maps/hanoi_noise_map.csv` — 5 587 cells × 17 hours, 744 KB | Ships inside the APK as-is |
| Site figures | `results/figures/*.png` | The results screens |
| Validation numbers | `models/metrics.json` | Never retyped; parsed and displayed |
| Simulation tier 1 | `simulation/gama/hanoi_noise.gaml` | The behaviour to reproduce interactively |

The delivered model is the whole reason on-device prediction is cheap here:

```
E(x) = A_hw / max(d_hw, D0) + A_res / max(d_res, D0) + B
L(x) = 10 · log10(E(x))
```

`A_hw = 4.774e7`, `A_res = 3.800e7`, `B = 1.106e-10`, `D0 = 5 m`. Three constants
and two distances. No LightGBM runtime, no Python, no server. `apply_residual` is
`false`, so the residual booster does not need to ship.

## Four constraints that shape the design

### 1. GAMA cannot run on the phone

GAMA is an Eclipse RCP desktop application: SWT, AWT, a full JVM. Android has
none of that, and there is no Android port. "GAMA embedded in the phone" as
literally stated is not available. Three things that *are*:

- **Reimplement tier 1 natively.** Tier 1 is the coloured grid plus a traffic
  multiplier applied to the traffic share of the energy — arithmetic over the
  5 587 cells we already export. The GAML file states the invariant to check
  against: at `k = 1` with no mitigation, the simulated map equals the predicted
  map. This gives the same interaction on the phone, offline, at 60 fps.
- **`gama-server` behind an HTTP endpoint.** GAMA ≥ 2025.6 runs headless and
  exposes a websocket protocol. The app sends scenario parameters, the server
  runs the model and returns indicators. This is the honest route for anything
  the phone cannot recompute — tier 2 pedestrian agents, if they ever get built.
- **Ship recorded GAMA output** — a scenario video or figure sequence — for the
  presentation use case, clearly labelled as a recording.

Recommended: native tier 1 for interaction, recorded output for the rest, and
`gama-server` only if a scenario genuinely needs the platform.

### 2. A public app cannot claim absolute levels — and *these* readings are not
   comparable to the 363

`docs/metrology.md` is unambiguous: the campaign is calibrated **relative**, by
cross-trimming three phones against each other, with no link to any acoustic
standard. Open that to 50 000 arbitrary handsets and even that consistency is
gone — device-to-reference departures of several decibels, handset- and
level-dependent, not a constant offset.

Two consequences the app has to encode, not paper over:

- A level measured by *this app's own microphone* is a **different quantity**
  from the `noise_dB` column of `measurements.csv`, which is a trimmed Decibel X
  reading. It must go in its own field, carry the device model and OS version,
  and never be silently merged into the published dataset.
- Every screen showing a level shows what it is: `L_A,25s`, a 25-second
  A-weighted sample, uncalibrated in absolute terms. No compliance claim, no WHO
  comparison — that comparison was withdrawn in full and must not reappear in a
  new interface.

### 3. Prediction stops at the edge of the sampled envelope

`config.GRID_MARGIN_M = 400`, and the repository rule is explicit: never predict
beyond the envelope of the measured points. Three sites — Ocean Park, Hoan Kiem,
Vinh Tuy. A public app installed across Hanoi will be opened where we have no
data, and the correct behaviour there is **to say so**, not to extrapolate a
kernel fitted 12 km away.

### 4. KoboToolbox will not absorb a public campaign as-is

The Global server's free plan caps submissions per month and storage, and every
record here can carry an audio clip and sometimes a video. Fifty thousand
participants is a different order of magnitude from 363 points. Either a paid
plan sized in advance, or a backend of our own in front of Kobo.

## Protocol notes for the collection screens

Kobo speaks **OpenRosa**, and it is a small protocol:

- `GET https://kc.kobotoolbox.org/formList` — the forms available to the account.
- `GET <downloadUrl>` — the XForm XML of a deployed form.
- `POST https://kc.kobotoolbox.org/submission` — `multipart/form-data`, part
  `xml_submission_file` holding the instance XML, one extra part per attachment
  (the audio clip, the photo). `X-OpenRosa-Version: 1.0`. Expect `201`.
- Auth: Basic, or a Kobo API token. Anonymous submission is possible only if the
  receiving account has `require_auth` turned off — which is exactly what a
  public APK needs, and also what makes the endpoint spammable.

Rendering *any* XForm dynamically is what JavaRosa does for ODK Collect, and it
is a large dependency and a large surface. Our two forms are frozen — the
campaign is closed and v2 is final. Building the screens natively and emitting
the matching instance XML is a fraction of the work, gives a far better public
UX, and costs one app release if a form ever changes. That is the recommendation.

## Phases

**Phase 1 — collect. Built.** The two forms as native Compose screens, GPS with
an accuracy gate at 10 m, audio capture, an offline outbox that survives losing
signal in the field, OpenRosa submission to Kobo. See `README.md`.

**Phase 2 — measure. Built with phase 1**, because separating them would have
been wrong: Android does not usually grant `AudioRecord` and `MediaRecorder` the
microphone at once, so measuring and recording as two steps would have measured
one stretch of street and submitted another. One session now does both —
`AudioRecord` at 48 kHz, A-weighting, SLOW, a 25 s window, the same PCM encoded
to AAC for the clip. The level is reported as its own quantity, with the device
model and the audio source the platform actually granted.

**Phase 3 — results. Built.** The predicted map for the three sites over the
bundled grid, the 363 measured points, the analysis figures, and the metrics read
from `metrics.json` rather than retyped — including the negative results, which
are the honest part of this work and belong in the app as much as the map does.

**Phase 4 — predict. Built, and simplified.** The plan was to compute `d_hw` and
`d_res` on device against bundled road geometry. That turned out to be work for
nothing: the published grid is already the kernel's output at 40 m, so reading
the nearest cell *is* the prediction, exactly and by construction. Road geometry
would have re-derived a number we ship. The kernel itself is in
`study/Scenario.kt` and under test, for the day a prediction is wanted somewhere
the grid does not cover — which, per the envelope rule, is nowhere yet.

**Phase 5 — simulate. Built, both ways.** Tier 1 recomputed locally over the
grid, and the real model driven over `gama-server` from a screen of its own. The
first is offline and covers the traffic volume; the second needs a server and
covers the scenarios the grid cannot hold. Driving the real model is also what
exposed the local scenario as wrong — see `README.md`.

**Phase 6 — backend.** Whatever Phase 1 submits to at scale: quota, moderation,
deduplication, and the path back into `scripts/01_prepare_field_data.py` so a
public submission can reach the pipeline.

## Decisions taken, 2026-08-19

1. **Android only.** Native Kotlin and Compose. iOS is a rewrite when it comes,
   not a constraint on this build.
2. **Straight to Kobo, anonymously.** OpenRosa `POST` to `kc.kobotoolbox.org`
   with no credentials, which needs `require_auth` off on the receiving account.
   The consequences — an open endpoint, and the free plan's submission and
   storage caps against a campaign meant to be public — are phase 6's problem and
   are not solved here.
3. **The app measures sound itself, into a separate field.** Nobody outside the
   team will install Decibel X, so without a microphone the public app collects
   nothing. Manual entry stays available for the calibrated handsets. The two
   never share a column.

## What the first real submission taught

Kobo replaces the XLSForm's `id_string` at deployment with the asset's own
identifier. Everything else about the instance was right — the fields, the
version, the anonymous route, the account — and the server still answered 404,
because the root element named a form it had never heard of. The app now reads
`/formList` and submits under what the server calls the form. Nothing about this
is visible from the phone when it goes wrong, which is the argument for having
tested it against the real server rather than reasoning about it.

## Still open

1. **Which Kobo account and project.** The campaign's is with the outgoing team
   (`docs/handover.md` §7). A public deployment needs its own, sized for the
   load rather than for 363 points.
2. **Video.** The v2 form has an optional `video_traffic` question; in-app video
   capture is not built. Traffic videos also carry faces and plates, which is why
   the campaign's 147 are not published — collecting them from the public raises
   the consent question the campaign never had to answer for strangers.
3. **Abuse and quota**, before an APK is distributed at all. An open OpenRosa
   endpoint accepts whatever is posted to it.

# How the app works

A companion to [`README.md`](README.md), which says what the app is and how to
build it. This one says how it works inside, and — where it matters more — why it
works that way. Most of the decisions below were forced by something that went
wrong; those are recorded with the failure, because a rule without its reason is
the first thing a later change discards.

---

## 1. What the app is made of

```
app/src/main/java/org/noisehanoi/mobile/
  form/       the two XLSForms as data, and the answers with their constraints
  odk/        the instance XML, and the OpenRosa client
  outbox/     the on-disk queue and the WorkManager job that drains it
  measure/    A-weighting, the level meter, the PCM writer, the AAC encoder,
              the calibration arithmetic
  location/   GPS fixes and the three campaign sites
  study/      the published grid, the delivered kernel, the tier 1 scenario
  gama/       the client that drives a running gama-server
  settings/   server configuration, the microphone offset, consent
  ui/         Compose screens
```

`form/`, `odk/`, `study/`, `measure/AWeighting.kt`, `measure/PcmWriter.kt` and
`measure/Calibration.kt` are pure Kotlin with no Android dependency. That is why
the constraint logic, the instance format, the weighting curve, the sample byte
order, the scenario decomposition and the calibration arithmetic are all covered
by JVM unit tests that need no emulator.

---

## 2. Collecting a measurement

### 2.1 The forms are data, not an engine

`form/FormSpec.kt` holds the two XLSForms transcribed as Kotlin values:
questions, choice lists, constraints, in the order the spreadsheet declares them.

This is deliberately **not** a general XForm engine. Rendering an arbitrary
XForm is what JavaRosa does for ODK Collect, and it is a large dependency and a
large surface. Both forms are frozen — the campaign is closed and v2 is final —
so the questions live as data, the screens render them natively, and
`odk/InstanceXml.kt` emits an instance the deployed form accepts. A form change
costs one app release. That is the trade.

Question names, choice names and constraints must stay identical to the
spreadsheet. Kobo validates each instance against the deployed form: a renamed
field is a rejected submission, not a warning.

### 2.2 One microphone session does two jobs

`measure/SplMeter.kt` opens `AudioRecord` once and, from that single stream,
computes the level *and* writes the raw PCM that becomes the audio clip.

Doing both from one capture is a correctness requirement, not an optimisation.
Android will not usually grant `AudioRecord` and `MediaRecorder` the microphone
at the same time, so measuring and recording as two steps would measure one
stretch of street and submit a different one.

Three things stand between the microphone and a number worth having:

- **The signal must not be pre-processed.** Automatic gain control rescales the
  signal to keep speech intelligible, which is exactly the information a level
  measurement is made of; noise suppression removes the steady background, which
  on a Hanoi street *is* the measurement. The capture asks for `UNPROCESSED`
  where the device declares it and `VOICE_RECOGNITION` otherwise, then explicitly
  disables AGC, noise suppression and echo cancellation on the session — an audio
  source is a request, not a guarantee. What was actually obtained travels with
  the submission in `measure_method`.
- **The first second is discarded.** The weighting filter starts from rest and
  the microphone hardware settles over the first buffers. One second is run
  through the filter to settle it and then thrown away — excluded from the
  energy, from the clipping count and from the written clip, so the clip really
  is the stretch that was measured.
- **The rate has to exist.** 48 kHz is asked for first, because the A-weighting
  design is accurate there; a handset that will not give it falls back to
  44.1 kHz rather than failing to measure at all.

### 2.3 The weighting curve

`measure/AWeighting.kt` implements IEC 61672-1 A-weighting as four zeros at the
origin and six poles, mapped by the bilinear substitution: four differences, two
sums and six one-pole sections in cascade.

The two sums are not optional. Six poles against four zeros leaves two surplus
poles, and the transform puts a zero at z = -1 for each. Without them the curve
rises about 1.9 dB too high at 8 kHz and keeps climbing. Pole frequencies are
prewarped so the 12.2 kHz pair lands where the standard puts it instead of at
10.3 kHz.

Measured against the IEC table at 48 kHz, the design is within 0.7 dB from
31.5 Hz to 12.5 kHz. A unit test pins it there, and a second test pins the
deviation at 16 kHz, so that a later change cannot quietly make it worse.

### 2.4 The byte order, and why it has its own file

`measure/PcmWriter.kt` exists because getting this wrong is silent. The first
version used `DataOutputStream.writeShort`, which is big-endian by
specification, while `AudioRecord` produces native-endian samples and
`MediaCodec` reads little-endian. Every sample went out byte-swapped and the clip
that reached the server was noise. The measurement was unaffected — it is
computed from the shorts, never from the file — so nothing on screen looked
wrong. And an emulator records silence, which is a run of zeros, and zeros
survive a byte swap unharmed. Neither the app nor the test device could show it;
only a written-down expectation about the bytes can.

### 2.5 The clip never blocks a submission

The clip is corroboration; the app measures the level itself. It was required of
the team at first, on the reasoning that it lets a doubtful measurement be
revisited — true, and not worth what it costs when it fails. On the first real
handset the encoder threw from `MediaMuxer.release()` *after* writing a complete
file; the exception replaced the success, the attachment was never made, and the
form could not be sent, with a perfectly good 206 kB clip sitting next to it on
disk. Every cleanup call is wrapped now, and the clip is optional in both modes.

In public contributor mode no clip is made at all. Across a public campaign that
would be 209 kB a submission — some 10 GB for fifty thousand — of recordings
nobody will play back, each of which may have caught a passing conversation.

### 2.6 The GPS gate

`location/GpsFixes.kt` uses `LocationManager` rather than the fused provider, so
that the APK does not require Google Play services.

The 10 m accuracy gate is the field protocol's. The campaign reported a median
declared accuracy of 4.9 m and a maximum of 9.0 m, and that bound is what let the
26 points falling inside OSM building footprints be explained rather than
discarded. A submission that silently relaxes it costs the next analysis that
argument.

Cached fixes older than two minutes are ignored. `getLastKnownLocation` will hand
back a position from hours ago without comment, and a stale fix with a good
accuracy figure beats a fresh one on any test that looks only at accuracy — right
up to the point where it is submitted as the place a measurement was taken.

`LocationListener` is written out rather than passed as a lambda: it only gained
default implementations for its other three methods in API 30, so on API 26–29 a
lambda leaves them abstract and the process dies with an `AbstractMethodError`
the first time the system reports a provider change. That is to say: in the
field, on the older phones, and never on a current emulator.

### 2.7 The outbox

`outbox/Outbox.kt` keeps one directory per pending instance under
`filesDir/outbox/`, holding the instance XML, its attachments and a small state
file. The same shape ODK Collect uses, for the same reason: a field session loses
signal, the app is killed, and nothing may be lost. There is no database on
purpose — a directory that survives a crash is easier to reason about, and to
recover by hand, than a half-migrated schema.

Three rules earned by things going wrong:

- **A file goes up only if the instance names it.** The directory is also the
  measurement's workspace, and a session stopped by hand leaves the raw PCM
  behind. Uploading whatever lies next to the instance would send 2.4 MB of raw
  audio per stranded file.
- **Drafts are spared, abandoned directories are not.** A directory with no state
  file and no draft is a form that was opened and backed out of, holding a clip
  no instance will reference; it is discarded at startup, which is the only
  moment none of them can be the form currently open.
- **A torn state file surfaces as failed rather than vanishing.** An entry that
  cannot be listed cannot be retried or deleted, and its attachments stay on the
  phone for good.

### 2.8 Drafts

The answers are written to `draft.json` beside the instance on every change and
restored at launch. Android kills backgrounded apps as a matter of routine — a
phone call, a notification, memory pressure — and everything typed lived only in
the ViewModel. A field worker who answered a call halfway through lost the lot,
while the recorded clip stayed on disk as an orphan.

It is a flat JSON map rewritten on every change. Not a database, not a state
machine: the file is small, and a draft that survives is worth more than a clever
way of storing it.

---

## 3. Sending it

### 3.1 OpenRosa

`odk/OpenRosaClient.kt` implements the submitting half of ODK Collect:
`GET /formList`, and `POST /submission` as `multipart/form-data` with the
instance in a part named `xml_submission_file` and one part per attachment.

### 3.2 The form identifier is the server's, not the spreadsheet's

**This is the thing that took the longest to find.** Kobo does not keep the
`id_string` from the XLSForm. On deployment it gives the form its own
identifier — `aA8FaTuUVSkRjbUW7rCBz7` rather than `hanoi_noise_v1` — and the
instance's root element and `id` attribute have to be **that**, or the server
answers 404 for a form it has never heard of. From the phone that is
indistinguishable from a wrong URL.

So the app reads `/formList` and submits under the name the server gives the
form. Settings has a *Fetch the deployed forms* button; until it has been used
once the home screen says so in red, because every submission would otherwise
fail. The version changes on each redeployment, which is the second reason this
is read rather than compiled in.

### 3.3 Where a submission goes

In anonymous mode the account name is the only thing routing a submission to a
project, so a distributed APK has to carry one. It is deliberately not a constant
in the source: hard-coding it would put one person's account into every installed
copy and require a new release to move it. It is a build property:

```sh
./gradlew assembleRelease -Pnoisehanoi.koboUser=the-account
```

Empty is the default, and empty means the app asks.

### 3.4 Who the contributor is

`collector` was the right key while the collectors were three named people. It is
the wrong list for a public campaign — it asks a stranger to file their
measurement under someone else's name — so v3 adds `public`, and the app offers
only that choice in public contributor mode.

The field could not simply be dropped: `01_prepare_field_data.py` maps its
per-collector calibration offset through it and de-duplicates on it.
`contributor_id` is what replaces it for those two jobs — a random UUID the app
mints on first launch and keeps. Not a hardware identifier, not an advertising
id, not a name. It lets a per-phone calibration offset exist at all, and it makes
a flood of identical submissions visible. Neither field reaches the published
dataset.

---

## 4. Carrying the study

### 4.1 Nothing is transcribed

`syncStudyData` in `app/build.gradle.kts` copies `hanoi_noise_map.csv`,
`measurements.csv`, `metrics.json`, `hybrid_physical.json` and the figures out of
the repository at build time. The repository's rule is that no published number
is ever written out by hand; an app that displays the headline R² is bound by the
same rule, so it reads the same file. Re-run the pipeline, rebuild the APK, and
the app moves with it.

### 4.2 The delivered model is three constants

```
E(x) = A_hw / max(d_hw, D0) + A_res / max(d_res, D0) + B
L(x) = 10 · log10( E(x) )
```

Chosen by `04_evaluate_models.py` over six candidates under buffered
leave-one-out, ahead of every learned model. Two things follow: the app needs no
ML runtime, and — since the published grid is already this kernel's output at
40 m — reading the nearest cell *is* the prediction, exactly and by construction.
There is no need to recompute distances to roads on the phone.

### 4.3 The app refuses to predict where nothing was measured

`GRID_MARGIN_M` puts the map's edge 400 m beyond the sampled envelope, and the
repository's rule is to predict no further. An app installed across Hanoi will be
opened where the campaign never went, and a kernel fitted 12 km away has nothing
to say there. Beyond two cells from the nearest one, the app says so.

---

## 5. The simulation, twice

The app reaches GAMA two ways, and they are not interchangeable.

### 5.1 Tier 1, recomputed locally

The map screen applies a traffic multiplier to the grid it carries: no network,
instant, and correct — checked against the model itself, the two agree within
0.2 dB from ×0.2 to ×3.

That check was worth making. **The first version of this decomposition was
wrong.** It subtracted the kernel's additive constant `B_background`, 1.1e-10,
from a cell energy near 1e6 — a subtraction of nothing — so it scaled the total
after all and returned exactly 10·log10(k). At a fifth of the traffic it gave
−7.0 dB where the model gives −3.7: precisely the error the study had already
found and corrected, rebuilt here, and certified by a unit test asserting it.

What must be held back is the zone's **residual ambience**, the fifth percentile
of its own levels — the quietest cells, where traffic contributes least. For
Ocean Park at 17:00 both the model and the app compute 56.08 dB from that rule.

### 5.2 The real model, driven over gama-server

GAMA is an Eclipse desktop platform and does not run on Android. `gama/` speaks
its websocket protocol to a process started elsewhere with
`gama-headless.sh -socket 6868`. That needs a network and a server that is on,
which the map does not; what it buys is everything the grid cannot hold — the
mitigation scenarios, the construction sites, the fleet by hour.

Four things had to be learned by driving it rather than by reading about it:

- **The experiment must have no display.** `hanoi_noise_sim` is `type: gui` with
  three, one of them OpenGL; loading it makes the server create a render surface,
  take the main thread on macOS, and stop answering the socket entirely. The
  model's own display-free `check` experiment loads in about two seconds.
- **`step` needs `sync`.** Without it the command returns, the cycle does not
  advance, and every indicator reads zero — which looks exactly like a model that
  does not work.
- **`expression` evaluates, it cannot assign.** `traffic_multiplier <- 2.0` is
  refused outright. Parameters are applied by `load` and by nothing else, which
  is why moving a slider reloads. That costs about 0.2 s once the model is
  compiled, which is what makes the sliders usable.
- **An abandoned experiment is not free.** Each holds 2544 cells, 1075 buildings
  and 766 roads — about 15 MB, measured. Sixty slider moves without stopping the
  previous one would be a gigabyte of simulations nobody is watching, so the
  screen stops the one it replaces.

### 5.2.1 Running the server

The app is a client. Something has to be listening, and it is not the phone.

```sh
# on the machine that holds the repository and a GAMA installation
/Applications/Gama.app/Contents/headless/gama-headless.sh -socket 6868 -ping_interval -1
```

Roughly forty seconds to start; it is ready when the log says `Server started at
port 6868`. GAMA ≥ 2025.6 is required — `-socket` is the server mode.

`-ping_interval -1` turns off the server's keep-alive pings. GAMA does not answer
them while it compiles a model, and a client that enforces a ping timeout drops
the connection mid-load, which looks exactly like a server that has crashed. The
app's own client disables read and ping timeouts for the same reason.

What the app needs to be told, in its GAMA screen:

| Field | Value | Notes |
|---|---|---|
| Server | `ws://192.168.1.66:6868` | The machine's address on the network the phone is on. `10.0.2.2` is the host as an emulator sees it and means nothing on a handset — so it is offered only on an emulator, and a real device starts blank |
| Model path | `/…/simulation/gama/hanoi_noise.gaml` | Absolute, and **on the server**. GAMA opens it; the phone never sees the file |

Both must be reachable from the phone: the same wifi, and a router that does not
isolate its clients from one another. A phone's own hotspot will not see the
machine.

Cleartext is the other constraint. `gama-server` offers no TLS, so the address is
`ws://`, which Android has blocked by default since API 28 — rightly. It is
permitted in **debug builds only**, through `app/src/debug/AndroidManifest.xml`. A
release build keeps the platform default and will only reach a server behind
`wss://`. That is deliberate: driving a simulation server across the room is a
development and demonstration feature, not something a publicly distributed APK
should relax its network policy for.

Two costs worth knowing before a demonstration. A GAMA server with the model
loaded sits at about 1.4 GB resident, and each abandoned experiment adds roughly
15 MB — 2544 cells, 1075 buildings and 766 roads apiece. The app stops the
experiment it replaces, so sliders do not accumulate them, but a long session
still grows: the JVM does not return memory to the operating system eagerly.
Restarting the server between sessions costs forty seconds and avoids the
question entirely.

### 5.3 The picture is the model's own

`ui/GamaCanvas.kt` redraws the model's "Noise map" display. The layers, their
stacking order and every colour and size are read from the `aspect` blocks of
`hanoi_noise.gaml` and reproduced: the 40 m grid in its eight bands, buildings,
roads, construction sites as diamonds, vehicles sized and coloured by type, and
the measured points on top. The declaration order is the stacking order in GAMA,
and getting it wrong buries the measurements under the buildings.

Static layers are pulled once per scenario; only the grid's levels and the
vehicles are re-pulled. Ocean Park comes across as about 430 kB. During play only
the vehicles move — the noise field is a function of hour, traffic and mitigation,
and none of those change on their own.

### 5.4 What the audit found

Driven against the running model, cell by cell:

| Check | Result |
|---|---|
| GAMA's predicted field against `hanoi_noise_map.csv` | 2544 cells, **max difference 0.000 dB** |
| GAMA's measured points against `measurements.csv` | 184 points, **max difference 0.000 dB** |
| The model's own invariant, `background_dB == base_dB` at k=1 | **0.000000 dB** |
| Reported mean, peak and exceedance against `effective_dB` | **0.0000** |

The indicators sit slightly above the map screen's grid — 62.97 against 62.77 dB
— and that is not a disagreement. The app's map shows `base_dB`, the predicted
field; the model reports `effective_dB`, which adds the construction sites'
energy on 333 of the 2544 cells. Two different quantities, both correct.

---

## 5.5 The audit of the data itself

Not only that the app agrees with the model, but that the chain the app rests on
holds together. Checked against the published files:

| Check | Result |
|---|---|
| `measurements.csv` against `metrics.json` | 363 rows, 47.0–88.0 dB, sd 7.138892896461 — identical to 12 decimals |
| Site counts | Ocean Park 184, Hoan Kiem 99, Vinh Tuy 80 — as `metrics.json` states |
| Campaign dates | 2026-06-10 to 2026-07-22, as stated |
| The grid's 17 hourly columns | **identical for all 5 587 cells** |

That last row is not a defect: the delivered kernel has no hour term, so a map
that varied by hour would be the thing worth worrying about. It does mean an
hour control on the map screen would be inert, which is why there is not one. In
the GAMA screen the hour does something real — it selects the measured traffic,
about 24 vehicles a minute at 21:00 against 76 at 17:00 — and whether the
construction sites are working, which moves the mean by 0.2 dB. It does not move
the predicted field.

### Why the map fits the measurements less well than the metrics say

Read at the 363 measurement locations, the published grid gives R² 0.159 and
MAE 5.35 dB, where `metrics.json` reports 0.246 and 5.01 under buffered
leave-one-out. An in-sample lookup scoring *worse* than a cross-validated figure
deserved an explanation rather than a shrug.

It is the grid resolution. Cells are 40 m, so a measurement sits up to 27 m from
the centre it is read at — and on a 1/d kernel near a road, that distance moves
the answer. Splitting the points by how far they fall from a cell centre:

| Half | R² | MAE |
|---|---|---|
| Nearest a centre (median 15.7 m) | 0.211 | 4.84 dB |
| Furthest | 0.118 | 5.86 dB |

Monotone, and the near half lands close to the cross-validated figures. The map
is coherent with the model; reading a 40 m raster at a point costs precision, and
that cost is what the gap measures.

## 6. What the app does not claim

`docs/metrology.md` is the authority and the app is bound by it.

A level measured by this app's microphone is **not** the same quantity as the
`noise_dB` column of `measurements.csv`, which is a trimmed Decibel X reading
from one of three cross-calibrated handsets. Consumer microphones depart from a
reference by several decibels in a way that depends on handset, OS and level, and
that is not a constant offset. So the app-measured level travels in its own
field, with the device model and the audio source attached, and never merges into
the published column.

The microphone offset in Settings is the whole of a handset's absolute
calibration in one number, and its default is a plausible constant, not a
measurement. Until someone calibrates against a reference, the app's decibels are
comparable to each other and to nothing else — which is also the status of the
campaign's own 363 points. The calibration screen exists to fix that: measure
beside a reference, type what it read, repeat. A single pair is refused as a
calibration, because traffic noise moves several decibels between one 25 s window
and the next and a single agreement can be luck.

Nothing in the app states compliance with QCVN 26:2010, and nothing compares a
reading to the WHO `L_den`/`L_night` values. That comparison was withdrawn in
full from this project — it set a 25 s sample against an annual indicator — and a
new interface is not a place to reintroduce it.

---

## 7. What has not been established

The level itself. The weighting curve is pinned to the IEC table by unit test and
the sample byte order likewise, and the app has been run on a real handset — but
**no reading from this app has ever been compared to a sound level meter**, and an
emulator records silence. Everything above is scaffolding around a number nobody
has checked. That is the first thing to do, and until it is done the absolute
figure means nothing at all.

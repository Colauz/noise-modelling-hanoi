# mobile/

Android app for the Hanoi urban noise campaign. Kotlin + Jetpack Compose, single
`:app` module.

It does two things. It replaces the ODK Collect + Decibel X pairing the campaign
ran on — the two survey forms, a sound level measurement, the audio clip, the GPS
fix and the submission to KoboToolbox, in one application that works with no
signal and uploads when there is one. And it carries the study: the predicted
map over the three measured areas, the 363 points, the simulation's traffic
scenario, and the results with the negative ones stated as plainly as the
positive one.

Scope, feasibility and the phases after this one: [`PLAN.md`](PLAN.md).

## What is built

**Collecting** — the two forms, the measurement, the submission.

| | |
|---|---|
| Forms | `hanoi_noise_form_v2` (16 questions) and `hanoi_construction_form` (6), transcribed in `form/FormSpec.kt` |
| Level | 25 s A-weighted, SLOW, from `AudioRecord`, after a discarded warm-up and with AGC, noise suppression and echo cancellation switched off |
| Calibration | Measure beside a reference, type what it read, repeat — `measure/Calibration.kt` |
| Audio clip | The same microphone session, encoded to AAC — required of the team, not collected at all in public mode |
| GPS | `LocationManager`, the protocol's 10 m accuracy gate, site suggested from the fix |
| Photo | Camera via `FileProvider`, for the construction form |
| Outbox | One directory per pending instance in `filesDir/outbox/`, drained by `WorkManager` |
| Submission | OpenRosa `POST /submission`, multipart, with or without credentials |
| Consent | Shown before the first form; declining leaves the map and the results usable |

**Showing** — the map, the model, the results.

| | |
|---|---|
| Map | The published 40 m grid over the three areas, by hour, drawn on a Canvas with no basemap and no network |
| Points | The 363 measurements overlaid, coloured on the same scale |
| Simulation | Tier 1 of the GAMA model recomputed on the phone: a traffic multiplier from x0.2 to x3 |
| Prediction | The delivered three-parameter kernel, in `study/Scenario.kt` — and a refusal outside the mapped areas |
| Results | The campaign, the three negative results, and every metric read from `metrics.json` |

The study's data is not transcribed into the app. `syncStudyData` in
`app/build.gradle.kts` copies `hanoi_noise_map.csv`, `measurements.csv`,
`metrics.json`, `hybrid_physical.json` and the figures out of the repository at
build time. Re-run the pipeline, rebuild the APK, and the app moves with it.

GAMA itself does not run on Android — it is an Eclipse desktop platform — but
tier 1 is not an agent simulation: it is a traffic multiplier over a grid the app
already carries. The multiplier scales the traffic share of the energy and never
the background, which is the correction that took the claimed benefit of
pedestrianisation from 7.0 dB down to 3.5. A unit test asserts the invariant the
GAML file states in its own header: at a multiplier of 1, the simulated map
equals the published one.

## Build and install

```sh
cd mobile
./gradlew :app:assembleDebug      # -> app/build/outputs/apk/debug/app-debug.apk
./gradlew :app:installDebug       # onto a connected device or emulator
./gradlew :app:testDebugUnitTest  # 26 tests, no emulator needed
./gradlew :app:lintDebug          # clean: the remaining warnings are the SDK pinning below
```

Or open `mobile/` as a project in Android Studio.

`local.properties` (which points at the Android SDK) is generated locally and
git-ignored; Android Studio writes it for you, or:

```sh
echo "sdk.dir=$HOME/Library/Android/sdk" > mobile/local.properties
```

## Sending to KoboToolbox: what has to happen

The app is finished on its side. What it needs is an account that will accept the
submissions. Reaching the server already works — a connection test against
`kc.kobotoolbox.org` answers **401**, which is a server saying "who are you",
not a broken client.

Pick one of two routes.

**First, whichever route: fetch the deployed forms.** Settings → *Fetch the
deployed forms*.

Kobo does not keep the `id_string` from the XLSForm. On deployment it gives the
form its own identifier — `aA8FaTuUVSkRjbUW7rCBz7` rather than `hanoi_noise_v1` —
and a submission has to name **that**, in the instance's root element and its
`id` attribute, or the server answers **404 for a form it has never heard of**.
From the phone that is indistinguishable from a wrong URL, and it is what made
the first real submission fail. The identifier is read from `/formList` and kept;
do it once per account, and again after each redeployment, because the version
changes every time.

**A. Named collectors** — the team, or anyone you hand credentials to.

1. Log in at kobotoolbox.org (Global server) with the account that owns the
   project. `docs/handover.md` §7 says whose that is.
2. Check the form is deployed: the project's *Form* tab, **Deploy**. The app
   submits against `hanoi_noise_v1`.
3. In the app, Settings: fill **Kobo username** and **Password**, or paste an
   **API token** from Kobo's *Account Settings > Security*.
4. Press **Test connection**. It should read "Reachable, form list returned 200".
5. Fill a form and press *Save to outbox and send*. The outbox shows SENT.

**B. Anonymous, which is what a public APK needs.**

0. Decide **which account owns it**, and build the APK against that account:

   ```sh
   ./gradlew assembleRelease -Pnoisehanoi.koboUser=the-account
   ```

   In anonymous mode the account name is the only thing routing a submission to a
   project, so a distributed APK has to carry one — nobody is going to type it.
   It is deliberately not a constant in the source: hard-coding it would put one
   person's account into every installed copy and require a new release to move
   it. Prefer an institutional account over an individual's; whoever owns it
   holds the data, and answers for it.

1. Same account and deployed form.
2. Turn off authentication for submissions: Kobo *Account Settings >* the option
   that requires authentication to submit (`require_auth` in the API). Off means
   anyone holding the APK can post to that project.
3. Leave username, password and token **blank** in the app.
4. `/formList` is readable anonymously on an account with per-form anonymous
   submission enabled, so *Fetch the deployed forms* works with no credentials.
   The outbox is the real test: a submission reaches SENT only on a 201.

**Whichever route, if the app is going to strangers**, turn on *Public
contributor* in Settings. The collector question stops offering the three
campaign first names and files submissions under `public`, with a random
per-install identifier alongside so the pipeline can still tell one contributor's
points from another's. It needs the v3 form deployed — see
[`forms/README.md`](forms/README.md), which also names the one de-duplication
change this owes `01_prepare_field_data.py`.

Route B is what "publish an APK so people do it" means, and it comes with the
consequences named in `PLAN.md`: an open endpoint anyone can post to, and the
free plan's monthly submission and storage caps against a campaign meant to
scale. Decide those before distributing anything.

## Configuring a server

Settings, in the app:

- **Server URL** — `https://kc.kobotoolbox.org` for the Kobo Global server.
- **Username** — the Kobo account that owns the project, and in anonymous mode an
  address rather than a credential: KoBoCAT routes on the path. Set, the app posts
  to `/<user>/submission`; blank, to `/submission`, which needs authentication to
  resolve. Pre-filled from `-Pnoisehanoi.koboUser` if the APK was built with it.
- **Password** or **API token** — leave both blank for anonymous submission,
  which works only if the receiving account has `require_auth` turned off. That
  is what a publicly distributed APK needs, and it is also what leaves the
  endpoint open to anyone who finds it. Sizing and abuse are the subject of phase
  6 in `PLAN.md`; this app does not solve them.
- **Test connection** fetches `/formList`, which separates "wrong URL" from
  "wrong password".

The campaign's own Kobo project is with the outgoing team (`docs/handover.md`
§7). A public deployment needs its own.

## Consent

The first launch shows what a submission contains, what the random contributor
identifier is and is not, that a position with a timestamp identifies a person
without needing a name, where the data lands and who therefore holds it, and that
the levels are calibrated against nothing unless someone calibrates them.
Declining is a real choice: the map and the results send nothing, so they stay
available.

`Settings.CONSENT_VERSION` is a version rather than a flag. Raise it when what is
collected changes, so that consent is asked again rather than inherited from an
agreement given to different facts.

## What the app records, and what it does not claim

The app measures with the phone's own microphone. That number is **not** the same
quantity as the `noise_dB` column of `data/processed/measurements.csv`, which is
a trimmed Decibel X reading from one of three handsets cross-calibrated against
each other. Consumer microphones depart from a reference instrument by several
decibels, handset- and level-dependent, and not by a constant offset
(`docs/metrology.md`).

So:

- The app-measured level goes in its own field, with the device model, the OS
  version and which audio source the platform granted. It reaches Kobo only once
  the v3 form is deployed — see [`forms/README.md`](forms/README.md).
- Settings carries a **microphone offset**, which is the whole of this handset's
  absolute calibration in one number. The default is a plausible constant for a
  consumer phone, not a measurement.
- Nothing in the app states compliance with QCVN 26:2010, and nothing compares a
  reading to the WHO `L_den`/`L_night` values. That comparison was withdrawn in
  full from this project — it set a 25 s sample against an annual indicator — and
  a new interface is not a place to reintroduce it.

The app asks for the microphone before it can record, and for location before it
can fix a point. It sends what a submission contains and nothing else: no
analytics, no identifiers beyond the device model that goes into the form.

## Versions, and why they are pinned where they are

| | |
|---|---|
| AGP | 9.3.1 — Kotlin support is built into AGP from 9.0, so there is no `org.jetbrains.kotlin.android` plugin here |
| Gradle | 9.5.1 (wrapper) |
| Kotlin | 2.4.10, JVM target 17 |
| compileSdk / targetSdk | 36 |
| minSdk | 26 — `AudioRecord` and runtime permissions behave consistently from Oreo on |

AndroidX and OkHttp are held one release behind current: Compose BOM 2026.06.01,
`core-ktx` 1.18.0, `activity-compose` 1.12.4, `lifecycle` 2.10.0,
`navigation-compose` 2.9.8, `work-runtime-ktx` 2.11.2, OkHttp 5.4.0. The newest
releases declare `minCompileSdk=37`, and only platforms 35, 36 and 36.1 are
installed here. Install `platforms;android-37` and these can all move up
together.

## Layout

```
app/src/main/java/org/noisehanoi/mobile/
  form/       the two XLSForms as data, and the answers with their constraints
  odk/        instance XML, and the OpenRosa client
  outbox/     the on-disk queue and the WorkManager job that drains it
  measure/    A-weighting, the level meter, the PCM writer, the AAC encoder
  location/   GPS fixes and the three campaign sites
  settings/   server configuration and the microphone offset
  study/      the published grid, the delivered kernel, the tier 1 scenario
  ui/         Compose screens
forms/        the v3 XLSForm the app submits against, and its generator
```

`form/`, `odk/`, `measure/AWeighting.kt` and `measure/PcmWriter.kt` are pure
Kotlin with no Android dependency, which is why the constraint logic, the
instance format, the weighting curve and the sample byte order are covered by JVM
unit tests rather than by an emulator.

## What has been checked, and what has not

Verified on an emulator, end to end, against the live server: a fix inside the
accuracy gate, a 25 s measurement, the instance written, and a **submission
accepted by `kc.kobotoolbox.org`** under the deployed form's own identifier. The map draws all three areas, the hour
and traffic sliders move it, tapping a cell reads it, and a position outside the
three areas is refused rather than answered.

**The level itself has never been checked against a sound source.** An emulator
records silence. The weighting curve is pinned to the IEC table by unit test, and
the byte order of the samples likewise, but no reading from this app has been
compared to a meter. That is the first thing to do on a real handset, ideally
alongside Decibel X on the three campaign phones, and until it is done the
absolute figure means nothing at all — which, per `docs/metrology.md`, is also
true of the campaign's own numbers.

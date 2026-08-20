# mobile/forms/

`hanoi_noise_app_v3.xlsx` — the form the Android app submits against, derived
from `data/forms/hanoi_noise_form_v2.xlsx` by `build_app_form.py`.

It is v2 plus six fields the app fills — `app_noise_db`, `measure_method`,
`device_model`, `os_version`, `app_version`, `contributor_id` — and one added
choice, `public` on the `collector` list.

The measurement fields exist because a level measured by the app's own microphone
is **not** the same quantity as `noise_db`, which is a trimmed Decibel X reading
from one of three cross-calibrated handsets. Consumer microphones depart from a
reference by several decibels in a way that depends on handset, OS and level, and
is not a constant offset (`docs/metrology.md`). One column for both would silently
mix them, and nothing downstream could separate them again.

## Opening the form to people who are not on the team

The v2 `collector` list is `lucas`, `laurian`, `quang`. That is the right list for
the team that ran the campaign and the wrong one for a public campaign: it asks a
stranger to file their measurement under someone else's name. v3 adds `public`,
and the app offers only that choice when its public-contributor mode is on.

The field could not simply be dropped. `01_prepare_field_data.py` uses it twice —
it maps `CALIBRATION_OFFSET` through it, and it de-duplicates on
`['collector', 'timestamp']`. Emptying it would merge every public submission
into one collector for both purposes.

`contributor_id` is what replaces it for those two jobs: a random UUID the app
mints on first launch and keeps. Not a hardware identifier, not an advertising
id, not a name, and nothing that resolves to a person. It lets a per-phone
calibration offset exist at all, and it makes a flood of identical submissions
visible.

**One pipeline change is owed here, and it is not made yet.** Once public
submissions arrive, `['collector', 'timestamp']` stops being a good de-duplication
key, because every public row shares one collector value. The key should become
`['contributor_id', 'timestamp']`, falling back to `collector` for the campaign's
own 363 rows, which have no contributor id. Millisecond timestamps make an actual
collision very unlikely, so this is a latent weakness rather than a live bug —
but it is a real one, and it belongs in `01_prepare_field_data.py`, not here.

Neither field reaches the published dataset. `measurements.csv` carries no
collector name and no device identifier today (`docs/data-sources.md`), and this
does not change that: `contributor_id` lives in the raw Kobo export, which is
never distributed.

The `id_string` stays `hanoi_noise_v1`: Kobo reads this as a **new version of the
same form**, so the project keeps its existing submissions rather than splitting
into two datasets. Only the version string changes.

## Deploying it

1. `python3 mobile/forms/build_app_form.py` — regenerates the file. Never edit the
   output by hand; edit v2 or edit the script.
2. Kobo → the existing project → **Replace form** → upload `hanoi_noise_app_v3.xlsx`
   → Deploy.
3. In the app: Settings → *Submit app-measured level and device metadata* → on.

Until step 3 the app submits a strictly v2-conformant instance and keeps the
app-measured level on the phone. Turning it on before the form is deployed makes
every submission fail: Kobo validates each instance against the deployed form,
and an unknown element is a refusal, not a warning.

The version string is in two places and they must agree — `VERSION` in
`build_app_form.py`, and `NOISE_FORM_V3_VERSION` in
`app/src/main/java/org/noisehanoi/mobile/form/FormSpec.kt`. A unit test asserts
that an instance carrying the app fields declares the v3 version; nothing checks
that the two constants match, so change them together.

`hanoi_construction_form.xlsx` needs no app variant: the app records nothing the
construction form does not already have.

# Field protocol and forms

## Forms

- `data/forms/hanoi_noise_form_v2.xlsx` — the main form (Kobo XLSForm): dB, GPS,
  source category, distance to road and to the dominant source, phone
  orientation, vehicle counts, traffic video, audible construction.
- `data/forms/hanoi_construction_form.xlsx` — construction site register, one
  record per site: GPS position, type (construction / demolition / renovation),
  activity level, photograph.

## Setup (once)

1. **Kobo** — create an account on kobotoolbox.org (Global server), then
   New → Upload XLSForm → Deploy.
2. **Phones** — install ODK Collect, set the server to `https://kc.kobotoolbox.org`
   with the Kobo credentials, then Get Blank Form.
3. **Sound meter app** — Decibel X, identical settings on every phone:
   **A**-weighting, **SLOW** response, trim 0.0.

## Cross-calibration (10 min, at the start of the first session, all three phones together)

1. Place the phones side by side facing the street, measure for 1 min, and read
   the AVG values at the same moment.
2. Repeat for 30 s to confirm stability (to within about 1 dB).
3. Take the middle phone as the reference; offset = reference − phone reading.
4. Enter each offset in Decibel X > Settings > Trim, so that the three phones
   display the same value.
5. Record the values and the date. If a trim was **not** applied in the field,
   carry the offset into `CALIBRATION_OFFSET` in
   `scripts/01_prepare_field_data.py` instead.

> This procedure makes the three phones **mutually consistent**. It does not
> anchor them to any absolute scale: there was never a reference instrument. See
> [`metrology.md`](metrology.md).

## Per-point routine (about 45 s)

1. ODK Collect → Fill Blank Form → Hanoi Urban Noise Survey.
2. Enter site and collector. For GPS, wait until the reported accuracy is
   better than 10 m.
3. Record at least 10 s of audio in the form, standing still and silent, and read
   the dB (AVG) on Decibel X during that time.
4. Enter the distances to the road and to the dominant source, and vehicle counts
   where feasible. Film the traffic during rush hours — the timestamped filename
   is what matches a video to its measurement automatically.
5. Capture window 05:00–23:00, with emphasis on 08:00–10:00 and 16:00–18:00.
   Vary the distance to the road between points.

## Construction sites

One record per site in the construction form, plus two or three ordinary
measurements taken while walking away from it. The dB-against-distance
relationship is computed later by matching the GPS positions.

---

*The campaign is closed. This document records how the 363 measurements were
taken, so that a future campaign can extend the dataset rather than start over.*

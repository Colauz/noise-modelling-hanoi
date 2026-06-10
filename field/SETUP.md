# Field data collection — setup (one-time, ~30 min)

## 1. Server (KoboToolbox, free)
1. Create an account at https://www.kobotoolbox.org (choose the **Global** server)
2. In Kobo: **New** → **Upload an XLSForm** → upload `hanoi_noise_form.xlsx`
3. Open the form draft → **Deploy**

## 2. Phones (both of them)
1. Install **ODK Collect** from the Play Store
2. In Kobo: click your avatar → **Account Settings** → there's a QR/config for data collection,
   or configure ODK Collect manually:
   - Server URL: `https://kc.kobotoolbox.org`
   - Username / password: your Kobo account
3. In ODK Collect: **Get Blank Form** → select *Hanoi Urban Noise Survey* → download
4. Install ONE sound meter app, the SAME on both phones (e.g. "Sound Meter" by Abc Apps,
   or NIOSH SLM if iPhone backup needed)

## 3. Cross-calibration (once, 30 min, both phones together)
1. Put both phones side by side, mics uncovered, same height
2. Play a constant sound source (white noise video) at 3 volumes: quiet / medium / loud
3. Note both readings at each level → if phone B reads systematically +3 dB vs phone A,
   subtract 3 dB from B's readings (column in the analysis, not on the field)
4. Save the readings in `calibration.csv`: phone, level, db_reading, date

## Per-sample routine on the field (~45 s once practiced)
1. ODK Collect → Fill Blank Form → Hanoi Urban Noise Survey
2. Pick site + collector
3. GPS: wait until accuracy < 10 m
4. Start audio recording in the form (>= 10 s), keep still and silent
5. During recording, read the dB value on the sound meter app
6. Enter dB, pick category + distance-to-road bracket
7. Save & send → walk 30-60 s to next spot at a DIFFERENT distance from the road

## Session plan (per the paper, scaled down)
- 3 sites x 4 time slots (08h, 12h, 17h, ~22h) x >= 2 days (1 weekday + 1 weekend)
- 20-30 samples per session, varying distance to road (0-10 m up to > 60 m)
- Target: 300-700 samples total
- Night sessions: go in pairs (paper's limitation #1 was night-time safety)

## Export
Kobo → your project → **Data** → **Downloads** → CSV (+ media for audio)
→ drop into `data/raw/hanoi/`

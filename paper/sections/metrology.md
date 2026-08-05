# Metrology: what our measurements are, and what they are not

> **Langue.** Les fichiers de `paper/sections/` sont rédigés en anglais : ils sont destinés à
> être collés dans le manuscrit Overleaf et utilisent les clés de `paper/bibliography.bib`.
> Le reste du dépôt reste en français.
>
> **À placer** dans *Methods*, immédiatement après la description du protocole de terrain,
> et à répercuter dans *Limitations*. Remplace toute mention de conformité normative et
> toute comparaison aux valeurs guides annuelles de l'OMS.

---

## 2.x Measurement quantity and instrumental status

### 2.x.1 The quantity we record

Each field record is a single A-weighted sound pressure level, read with SLOW time
weighting from a consumer smartphone application over a stationary observation of 20–30 s.
Throughout this paper we denote it **`L_A,25s`** and never simply "dB". It is a short-sample
estimate of an equivalent continuous level, and it is deliberately *not* labelled `L_Aeq`
without a duration subscript, because the reference periods that give `L_Aeq` its regulatory
meaning are one to twenty-four hours, not twenty-five seconds.

Two consequences follow, and both are load-bearing for the rest of the paper.

**(i) The quantity is intrinsically noisy at the sample level.** In a motorcycle-dominated
traffic stream, a single horn burst or the passage of one bus displaces a 25 s average by
several decibels; horn events alone have been measured at up to +17 dB above ordinary horn
use in Vietnamese urban traffic \citep{nguyen2025horn}. This variance is a property of the
quantity, not a defect of the sensor, and it places a ceiling on the coefficient of
determination that *any* spatial model can reach against these targets.

**(ii) The quantity is not the quantity that regulations and health guidelines address.**
QCVN 26:2010/BTNMT \citep{qcvn26} regulates an `L_Aeq` determined under TCVN 7878-2:2010
with a class 1 or class 2 sound level meter. The WHO road-traffic guideline values of 53 and
45 dB are `L_den` and `L_night`: **annual** averages incorporating +5 dB evening and +10 dB
night penalties. A 25 s daytime sample and an annual `L_den` are not the same statistic of
the same process, and the numerical proximity of their values is a coincidence of scale, not
a basis for comparison.

> **Change from earlier versions of this work.** Our internal data-collection report compared
> measurement-level exceedance rates against both QCVN thresholds and the WHO
> `L_den`/`L_night` values, and presented the latter in a day/night threshold table. **The WHO
> comparison has been withdrawn in full.** It compared a short-sample instantaneous level to
> an annual long-term indicator, and no defensible correction bridges the two from our data.
> QCVN comparisons are retained but reframed (§2.x.4).

### 2.x.2 Relative, not absolute: the calibration status of the sensors

Three smartphones were cross-calibrated against one another at the start of the campaign:
placed side by side, read simultaneously, and trimmed so that all three agreed to within
approximately 1 dB. The middle device was taken as the reference.

This procedure establishes **inter-device consistency and nothing else.** It contains no link
to an acoustic standard — no class 1 or class 2 meter, no acoustic calibrator. A bias common
to all three devices is, by construction, invisible in our data. Consumer smartphone sound
measurement is known to depart from reference instruments by several decibels, in a manner
that depends on handset, operating system and level, and that is not a simple constant offset
\citep{kardous2014smartphone, murphy2016smartphone}.

We therefore state the instrumental status of this dataset explicitly:

> **Our measurements are calibrated in the relative sense and uncalibrated in the absolute
> sense.** Differences — between locations, between hours of the day, between site
> typologies — are supported by the data, because a bias common to the three devices cancels
> in a difference. Absolute levels are *not* certified, and no claim in this paper depends on
> a single absolute value being correct.

This is a limitation of materials, and the field campaign is closed; it cannot be repaired
retrospectively. It can, however, be *bounded*, and it constrains which claims we make.

### 2.x.3 Bounding the absolute bias against instrumented literature

Because we cannot calibrate against a reference instrument, we anchor our distribution
against published Vietnamese campaigns that used professional equipment
(`scripts/literature_anchoring.py`; full table in `outputs/hanoi/literature_anchoring.md`).
Our measurements are stratified to approximate each published situation as closely as
possible — roadside classes only, daytime only, and for major-corridor anchors the two sites
whose typology matches.

| Anchor | City | Instrument | Quantity |
|---|---|---|---|
| \citet{gelb2019cyclists} | Ho Chi Minh City | personal dosimeters + GPS, 3300 segments | `L_Aeq,1min`, mean 78.8 dB(A) |
| \citet{phan2010characteristics} | **Hanoi** | RION NL-21 / NL-22, 24 h continuous, 7 sites | `L_den` 70–83 dB |

Three irreducible gaps separate these anchors from our data, and we correct for the first
explicitly and declare the other two:

1. **Quantity.** `L_den` carries evening and night penalties and exceeds the daytime `L_Aeq`
   of the same location by several decibels; dosimeters worn by cyclists sit within the
   traffic stream, 1–2 m from vehicles, rather than at the kerb. An expected offset is
   subtracted for each anchor before the residual is interpreted.
2. **Place.** "Major arteries of Hanoi" is not "our three districts", two of which are not
   major corridors.
3. **Epoch.** The Hanoi reference campaign dates from 2005–2007
   \citep{phan2010characteristics}; ours is 2026, during a partial electrification of the
   two-wheeler fleet.

The residual after the quantity correction is our estimate of the plausible absolute bias.
**This estimate is reported; it is never applied.** No offset is written into
`measurements.csv`, because an anchor separated from us by place and epoch cannot support a
point correction — only an interval.

*(Note for the authors: the `L_den` figures attributed to \citet{phan2010characteristics} are
currently taken from secondary sources and are flagged `to_check` in
`scripts/literature_anchoring.py`. They must be confirmed against the PDF — available through
the VinUniversity library — before submission. The figures circulating from the Institute of
Occupational Health and Environment for twelve Hanoi arteries are press-reported grey
literature and are retained only as contextual orientation, never as a primary reference.)*

### 2.x.4 What we claim, and how exceedances are reported

| Claim type | Status | Wording used in this paper |
|---|---|---|
| Contrast between sites, hours, typologies | **Supported** | reported directly |
| Rank ordering of locations by exposure | **Supported** | reported directly |
| Absolute level at a given point | Indicative | reported with the bias interval of §2.x.3 |
| Regulatory compliance / non-compliance | **Not claimed** | see below |

Exceedance statistics are reported as *"the proportion of short-sample measurements
exceeding the QCVN daytime threshold value"* — a descriptive statistic of our sample — and
never as a rate of regulatory non-compliance. The distinction is not cosmetic: the 70 dBA
threshold falls near the middle of our distribution, so a bias of a few decibels moves the
exceedance proportion substantially. Every exceedance figure is accompanied by a sensitivity
statement giving the proportion under the bias interval of §2.x.3.

Vietnam has no national strategic noise mapping programme and no statutory noise action plan
\citep{nguyen2025law}. This is precisely the context in which a low-cost, reproducible,
smartphone-based method has value — provided it is honest about the difference between
*mapping relative exposure patterns*, which it can do, and *certifying compliance*, which it
cannot.

---

## Checklist for the manuscript

- [ ] Replace every bare "dB" denoting our target with `L_A,25s`.
- [ ] Remove the WHO `L_den` / `L_night` row from the thresholds table (done in
      `gama/hanoi_noise.gaml` and `scripts/build_report.py`).
- [ ] Reword every exceedance figure per §2.x.4, with the sensitivity statement.
- [ ] Confirm the \citet{phan2010characteristics} values against the PDF; update
      `scripts/literature_anchoring.py` and switch the status flag to `verified`.
- [ ] State in *Limitations* that the campaign is closed and that absolute calibration cannot
      be retrofitted — then state what the design nonetheless supports (§2.x.2).

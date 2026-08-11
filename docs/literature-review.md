# Literature review

**Short on purpose.** The selection criterion is *actual use*: a reference is here
because it informed a decision, a parameter or a stated limitation of this project.
Coverage was not a goal. An honest bibliography beats a long one.

**Source reliability follows the project policy** defined in
[`methodology.md`](methodology.md) §5.2 — `verified` / `to_check` / `grey`, no fourth
level, and grey literature is never cited as a primary reference.

> **Status: DOIs verified. Quartiles could not be read off their source.**
>
> Every DOI below was resolved against the Crossref API on 2026-08-12 and its
> journal, year and title confirmed.
>
> **Quartiles are recorded as `relevé impossible` rather than filled in.**
> The rule of this project is that a quartile is read off its ranking source with
> the year of that ranking, never from memory and never from a summary.
> [scimagojr.com](https://www.scimagojr.com) returns **HTTP 403 to automated
> requests**, and a search engine's summary of a quartile is second-hand — the same
> category of evidence this project classifies `grey` everywhere else. Quoting one
> would break the source policy in the very document that states it.
>
> **This is a fifteen-minute manual task**, listed in
> [`handover.md`](handover.md): open Scimago in a browser, search each journal
> below, and record the quartile *with its ranking year and subject category*.
> Until then, **no quartile from this file may be quoted**, and the journals are
> characterised by publisher and by the credibility evidence that could be
> verified: method, independence, and citation counts where Crossref reports them.

---

## 1. The standard we apply

### QCVN 26:2010/BTNMT

**Reference.** Ministry of Natural Resources and Environment of Viet Nam (2010).
*QCVN 26:2010/BTNMT — National technical regulation on noise.* Hanoi.
**Status.** `verified` — national regulation, cited from its official designation.
No DOI (regulatory text).
**Why credible.** It is the binding instrument in the jurisdiction studied.
**Concrete contribution.** **This is the only threshold this project displays.** Its
70 dB day / 55 dB night values are the colour breaks of every published map, of the
GAMA legend, and of the exceedance statistic (38.6 % of samples). It also sets the
day/night boundary at 06:00–21:00 used to split our sample. And it is the source of
the project's central metrological limitation: the regulation specifies an `L_Aeq`
measured with a class 1 or 2 instrument under TCVN 7878-2, which is **not** our
quantity and **not** our instrument — hence exceedances reported as a descriptive
statistic and never as non-compliance. See [`metrology.md`](metrology.md).

### ISO 1996-2:2017

**Reference.** International Organization for Standardization (2017). *ISO 1996-2:
Acoustics — Description, measurement and assessment of environmental noise — Part 2.*
**Status.** `verified` — international standard. No DOI.
**Concrete contribution.** Read, and **used mainly as a list of what we did not do**:
it prescribes limits on wind speed, measurement height, distance to reflecting
surfaces and integration duration, none of which our protocol controls. It is cited
in the audit as a conformity gap and it informs the v3 form recommendations in
[`handover.md`](handover.md). No parameter of this project comes from it.

---

## 2. Instrumented measurements in Vietnam — bounding our absolute bias

### Phan et al. 2010, *Applied Acoustics*

**Reference.** Phan, H. Y. T., Yano, T., Sato, T. & Nishimura, T. (2010).
Characteristics of road traffic noise in Hanoi and Ho Chi Minh City, Vietnam.
*Applied Acoustics* 71(5), 479–485. DOI
[10.1016/j.apacoust.2009.11.008](https://doi.org/10.1016/j.apacoust.2009.11.008)
**Status.** **`to_check`** — DOI and metadata verified against Crossref, **but the
`L_den` values 70–83 dB used as our anchor come from secondary sources and have not
been confirmed against the article PDF.** Flagged `to_check` in
`06_anchor_literature.py` and still open in `handover.md`.
**Quartile.** *Relevé impossible* (Scimago 403). Applied Acoustics, Elsevier, an established journal in environmental and applied acoustics.
**Why credible.** The only professionally instrumented noise campaign published for
Hanoi: RION NL-21/22 sound level meters, 24 h continuous, 7 urban sites.
**Concrete contribution.** **The primary anchor of our absolute-bias interval.** With
no reference instrument of our own, this is what our stratified roadside daytime
distribution is compared against, after subtracting the expected `L_den` offset. It
is the single reason we can state a plausible bias range at all rather than declaring
absolute levels unknowable. Its 2005–2007 epoch is also one of the three irreducible
gaps we declare (§5.2 of the methodology).

### Gelb & Apparicio 2019, *Applied Acoustics*

**Reference.** Gelb, J. & Apparicio, P. (2019). Noise exposure of cyclists in Ho Chi
Minh City. *Applied Acoustics* 148, 332–343. DOI
[10.1016/j.apacoust.2018.12.031](https://doi.org/10.1016/j.apacoust.2018.12.031)
**Status.** `verified` — DOI resolved, value read in the abstract.
**Quartile.** *Relevé impossible* (Scimago 403 — see the note at the top)
**Why credible.** Personal dosimeters plus GPS over 3 300 segments; independent team;
method fully described.
**Concrete contribution.** **The second anchor**, and the one that forced the
`metric_gap_dB` mechanism: cyclists carry dosimeters *inside* the traffic stream,
1–2 m from vehicles, so their mean of 78.8 dB(A) is expected to sit above a kerbside
observer's. Subtracting that expected offset before reading the residual as
instrumental bias is a direct consequence of this source.

### Nguyen et al. 2025, horn use, *Acoustics*

**Reference.** Nguyen, T. L., Nishimura, Y. & Nishimura, S. (2025). Horn use patterns
and acoustic characteristics in congested urban traffic. *Acoustics* 7(2). DOI
[10.3390/acoustics7020036](https://doi.org/10.3390/acoustics7020036)
**Status.** `verified`
**Quartile.** *Relevé impossible* (Scimago 403). *Acoustics*, MDPI.
**Concrete contribution.** Supplies the **+17 dB horn-event figure** used in
`metrology.md` to argue that our 25 s target is *intrinsically* noisy at sample level
— a property of the quantity, not a sensor defect. That argument is what places a
ceiling on the R² any spatial model can reach against these targets, and it is
therefore part of why R² ≈ 0.25 is reported without apology.

### Nguyen et al. 2025, noise law, *City and Environment Interactions*

**Reference.** Nguyen, Q. C., Chu, A. T. T., Truong, B. G. et al. (2025). Noise
pollution in developing countries: loopholes and recommendations for Vietnam law.
*City and Environment Interactions*. DOI
[10.1016/j.cacint.2025.100187](https://doi.org/10.1016/j.cacint.2025.100187)
**Status.** `verified`
**Quartile.** *Relevé impossible* (Scimago 403 — see the note at the top)
**Concrete contribution.** Establishes that **Vietnam has no national strategic noise
mapping programme and no statutory noise action plan**. That single fact is the
justification for the project's positioning in `metrology.md`: a low-cost reproducible
smartphone method has value precisely in that vacuum, provided it does not overclaim.

---

## 3. Smartphone measurement — why our levels are relative

### Kardous & Shaw 2014, *JASA*

**Reference.** Kardous, C. A. & Shaw, P. B. (2014). Evaluation of smartphone sound
measurement applications. *The Journal of the Acoustical Society of America* 135(4).
DOI [10.1121/1.4865269](https://doi.org/10.1121/1.4865269)
**Status.** `verified`
**Quartile.** *Relevé impossible* (Scimago 403 — see the note at the top)
**Why credible.** NIOSH authors, reference-laboratory comparison, heavily cited.
**Concrete contribution.** **The evidential basis of Assumption 1.** It is why we
state that consumer smartphone measurement departs from reference instruments by
several decibels in a way that is not a constant offset — and therefore why a bias
common to our three phones is invisible by construction, why absolute levels are
"indicative", and why no compliance claim appears anywhere in the repository.

### Murphy & King 2016, *Applied Acoustics*

**Reference.** Murphy, E. & King, E. A. (2016). Testing the accuracy of smartphones
and sound level meter applications for measuring environmental noise. *Applied
Acoustics* 106, 16–22. DOI
[10.1016/j.apacoust.2016.01.007](https://doi.org/10.1016/j.apacoust.2016.01.007)
**Status.** `verified`
**Quartile.** *Relevé impossible* (Scimago 403 — see the note at the top)
**Concrete contribution.** Corroborates the above on **environmental** noise
specifically, and on a device/OS spread. Cited beside Kardous & Shaw in
`metrology.md`; it is the reason the phone **model** is named as a missing metadata
field in the v3 form recommendations — without it, no retrospective correction is
possible.

---

## 4. Spatial validation — target 2

### Roberts et al. 2017, *Ecography*

**Reference.** Roberts, D. R., Bahn, V., Ciuti, S. et al. (2017). Cross-validation
strategies for data with temporal, spatial, hierarchical, or phylogenetic structure.
*Ecography* 40(8), 913–929. DOI
[10.1111/ecog.02881](https://doi.org/10.1111/ecog.02881)
**Status.** `verified`
**Quartile.** *Relevé impossible* (Scimago 403 — see the note at the top)
**Why credible.** The reference synthesis on the question; very heavily cited across
ecology, remote sensing and geostatistics; independent of any noise-modelling agenda.
**Concrete contribution.** **This is the source that makes our reference protocol
defensible by literature rather than by internal argument.** The rule it states — the
cross-validation block must exceed the autocorrelation range of the predictors — is
what condemned the `GroupKFold` on ~110 m cells against a 300 m feature radius, and
what fixes our block size at 600 m and our buffered-LOO exclusion at 300 m. It is
cited in the audit, in `methodology.md` Assumption 5, and in the docstring of
`04_evaluate_models.py`. **Without it, the withdrawal of R² = 0.45 rests on our own
judgement; with it, it rests on an accepted standard.**

### Meyer & Pebesma 2021, *Methods in Ecology and Evolution*

**Reference.** Meyer, H. & Pebesma, E. (2021). Predicting into unknown space?
Estimating the area of applicability of spatial prediction models. *Methods in Ecology
and Evolution* 12(9). DOI
[10.1111/2041-210X.13650](https://doi.org/10.1111/2041-210X.13650)
**Status.** `verified`
**Quartile.** *Relevé impossible* (Scimago 403 — see the note at the top)
**Concrete contribution.** Two uses, one applied and one deferred. Applied: it
underpins the rule that **no prediction is published outside the sampled envelope**,
now enforced by `tests/test_grid_extent.py` and the reason the Bach Khoa grid was
retracted. Deferred: its area-of-applicability mask is the recommended next step for
the map, listed in `handover.md` rather than implemented.

---

## 5. Vehicle counting in motorcycle-dominated traffic — target 1

### Anh et al. 2024, *International Journal of Intelligent Transportation Systems Research*

**Reference.** *Counting Mixed Traffic Volumes at Motorcycle-Dominated Intersections
by Using Computer Vision.* (2024) *International Journal of Intelligent Transportation
Systems Research.* DOI
[10.1007/s13177-024-00442-z](https://doi.org/10.1007/s13177-024-00442-z)
**Status.** **`to_check`** — DOI, title, journal and year verified against Crossref;
**the author list and the reported accuracy figures have not been read in the article
itself.** Do not quote a number from it until they are.
**Quartile.** *Relevé impossible* (Scimago 403 — see the note at the top)
**Concrete contribution (pending confirmation).** This is the closest published
counterpart to our §2b limitation: automated counting at **motorcycle-dominated**
intersections, the traffic composition that makes our own detector's under-detection
expected but unquantified. If its per-class accuracy figures hold on reading, they
give an **order of magnitude for our input uncertainty in the absence of our own
manual count** — which is exactly what `handover.md` debt 2 exists to replace with a
measured value.

---

## 6. Reproduced work and modelling tools

### Nsumba et al. 2026, *Scientific Data*

**Reference.** Nsumba, S., Muhanguzi, T., Ouma, E. N., Sekalala, I., Bainomugisha, E.,
Mwebaze, E. & Quinn, J. (2026). Noise mapping and ambient sound recordings of the urban
environment in Uganda. *Scientific Data*. DOI
[10.1038/s41597-026-06658-w](https://doi.org/10.1038/s41597-026-06658-w)
**Status.** `verified`
**Quartile.** *Relevé impossible* (Scimago 403). *Scientific Data*, Nature Portfolio.
**Concrete contribution.** **The project's point of departure and the subject of its
second negative result.** Its protocol shaped ours (ODK collection, smartphone target,
morphology within a radius); notebooks 01–06 reproduce its figures; and its surrogate
model is what we transferred to Hanoi and watched fail at R² < 0. The failure is
reported as a finding about transferability, not as a criticism of the dataset.

### Kephalopoulos et al. 2014, CNOSSOS-EU, *Science of The Total Environment*

**Reference.** Kephalopoulos, S., Paviotti, M., Anfosso-Lédée, F. et al. (2014).
Advances in the development of common noise assessment methods in Europe. *Science of
The Total Environment* 482–483, 400–410. DOI
[10.1016/j.scitotenv.2014.02.031](https://doi.org/10.1016/j.scitotenv.2014.02.031)
**Status.** `verified`
**Quartile.** *Relevé impossible* (Scimago 403 — see the note at the top)
**Concrete contribution.** **Read, not used — and that is itself a documented
decision.** CNOSSOS-EU is the physical propagation framework this project does *not*
implement. It is cited to name precisely what is missing, and it is the top entry in
future work: our own result — a three-parameter distance law beating a six-variable
learned model — is the argument for adopting a real propagation kernel rather than
more machine learning.

### Bocher et al. 2019, NoiseModelling, *IJGI*

**Reference.** Bocher, E., Guillaume, G., Picaut, J. et al. (2019). NoiseModelling: an
open source GIS-based tool to produce environmental noise maps. *ISPRS International
Journal of Geo-Information* 8(3), 130. DOI
[10.3390/ijgi8030130](https://doi.org/10.3390/ijgi8030130)
**Status.** `verified`
**Quartile.** *Relevé impossible* (Scimago 403 — see the note at the top)
**Concrete contribution.** **Read, not used.** It is the concrete implementation route
for the CNOSSOS layer above — open source, OSM-native inputs — and it is named as such
in the audit's P1-3 and in `handover.md`. No parameter of the present work comes from
it. Cited so that the successor does not have to rediscover which tool to use.

---

## 7. Read, not used

Kept in `references.bib` because they were consulted and may serve the manuscript,
but they informed no decision in the current work.

| Reference | DOI status | Why not used |
|---|---|---|
| Phan et al. 2010, *community responses* | `verified` | Social survey of annoyance. Our study measures levels, not response; no parameter derives from it |
| Nguyen et al. 2021, HCMC road traffic noise | `verified` | Ho Chi Minh City, not Hanoi, and its levels were not used as an anchor because the anchoring stratification could not be matched |
| Nguyen et al. 2020, Noi Bai airport | `verified` | Aircraft noise. Out of scope: our sources are road traffic and construction |
| Institute of Occupational Health and Environment, 12 Hanoi arteries | **`grey`** | Reported by the Vietnamese press, protocol undocumented, not peer-reviewed. **Excluded from the bias interval and never cited as a primary reference** — see `methodology.md` §5.2 |

---

## 8. Gaps in the literature, and what they imply

**There is one instrumented noise campaign published for Hanoi, and it is twenty
years old.** Phan et al. 2010 measured in 2005–2007. Nothing comparable has been
published since, over a period in which the city's two-wheeler fleet began
electrifying. Our absolute-bias interval therefore rests on a single ageing anchor,
and it is wide for that reason rather than through lack of care.

**Southeast Asian motorcycle-dominated traffic is under-represented in noise
modelling.** The propagation and emission frameworks we would adopt — CNOSSOS-EU and
its national variants — were calibrated on European fleets dominated by four-wheeled
vehicles. Applying them to a stream where motorcycles are the majority is not a
solved problem, and we found no source that resolves it. **This bounds the value of
the CNOSSOS route we recommend**: it is the right next step, but it will need local
emission validation rather than direct application.

**Detector accuracy on dense two-wheeler traffic is reported unevenly.** Published
figures exist, but with differing camera geometries, classes and definitions of
accuracy. **None of them substitutes for a manual count on our own videos**, which is
why `handover.md` debt 2 remains the highest value-per-effort task rather than being
closed by citation.

**Consequence for the scope of our results.** Our contrasts between sites and hours
are supported. Our absolute levels are bounded by one twenty-year-old anchor. Our
modal shares are not publishable. And our generalisation claim stops at three sampled
typologies — the literature offers nothing that would let us extend it by analogy.

---

## 9. Negative results against the state of the art

A failure predicted by the literature is a result; an isolated failure is an anecdote.

| Our negative result | What the literature says |
|---|---|
| **R² = 0.45 withdrawn**; the model ranking inverts between permissive and strict splits | Predicted, and precisely. Roberts et al. 2017 states the rule we broke; the inversion of ranking under stricter splits is the documented signature of models learning spatial autocorrelation. **Our finding is a confirmation, not a discovery** — which is what makes it defensible rather than embarrassing |
| **Cross-city transfer fails** (Uganda → Hanoi, R² < 0) | `[À VÉRIFIER]` — we have not yet found a published counterpart on land-use-regression transfer between cities of different fabric. Target 3 of the search remains open |
| **Vehicle counts carry no recoverable emission** | Partially anticipated: emission frameworks require flow **and speed**, and our camera field yields neither speed nor source distance. CNOSSOS-EU's own formulation is the demonstration that a count alone is insufficient |
| **Morphology aggregated over 300 m adds nothing beyond distance** | `[À VÉRIFIER]` — the land-use-regression literature reports gains from morphology at various radii; we have not yet located work reporting a negative marginal contribution at comparable radius and sample size. Target 3 |

---

## What remains to complete this review

1. **Quartiles.** Every `[À VÉRIFIER]` above must be read off Scimago (SJR) or JCR with
   its ranking year. No quartile is quoted from memory.
2. **Phan et al. 2010.** Confirm the `L_den` 70–83 dB values against the PDF, then
   switch the status to `verified` in `06_anchor_literature.py` and here.
3. **The 2024 counting reference.** Read the author list and the per-class accuracy in
   the article itself before quoting any figure.
4. **Targets 2 and 3, still open.** No source yet located for (a) LUR transfer failure
   between cities, (b) a reported negative marginal contribution of morphology at
   comparable radius and n. If none exists, that absence is itself worth stating.

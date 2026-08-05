# Negative results as contributions

> **Langue.** Rédigé en anglais pour insertion directe dans le manuscrit Overleaf ; clés de
> citation dans `paper/bibliography.bib`.
>
> **À placer** en *Discussion*, en trois sous-sections. Ces trois résultats sont, en l'état, les
> apports les plus originaux du travail : ils doivent être présentés comme des résultats
> obtenus, pas comme des difficultés rencontrées. §5.z est l'argument central du papier.

---

Three of our experiments returned negative results. All three were designed to succeed, all
three failed for identifiable reasons, and all three constrain how urban noise should be
modelled in motorcycle-dominated cities. We report them as findings rather than as
limitations, because each answers a question that the positive results do not.

---

## 5.x Visual vehicle density does not carry acoustic information: a measurement-design result

### The experiment

We recorded 147 timestamped traffic videos alongside our noise measurements (median offset
15 s between video and measurement), counted motorcycles, cars, buses and trucks with a
YOLOv8 detector sampled at approximately 1 frame per second, and attempted to recover a
per-vehicle-class sound emission by regressing measured acoustic energy on vehicle counts.

The regression was formulated in **energy**, not decibels, since acoustic contributions add
linearly in energy:

$$E_{\text{total}} = E_{\text{background}(s)} + \sum_{c} n_c \, e_c$$

with a free background term per site $s$, and with the physical constraint $e_c \ge 0$ — a
source cannot subtract energy. This is a non-negative least squares problem.

### The result

**All three vehicle coefficients returned exactly zero.** The non-negativity constraint drove
$e_{\text{moto}}$, $e_{\text{car}}$ and $e_{\text{heavy}}$ to the boundary. Within a site, the
number of visible vehicles explains between 0.8 % and 4.4 % of the variance in the measured
level, and the sign of the site-wise correlation is inconsistent — it is *negative* at two of
our three sites (Hoan Kiem $r = -0.09$, Ocean Park $r = -0.19$, Vinh Tuy $r = +0.21$; pooled
$r = -0.15$ over all 147 matched videos). Ocean Park, where the densest sessions approach
gridlock at 7–9 vehicles per frame, is one of the two negative sites: where congestion is
highest, more visible vehicles go with *less* measured sound.

Rather than substitute literature emission values that our data cannot support, we left the
result standing: in the accompanying agent-based simulation, vehicles are a calibrated visual
representation of the measured fleet and carry no acoustic weight.

### Why this happened, and why it generalises

The failure is not a failure of the detector. It is a **mismatch between the quantity measured
and the quantity that governs the physics**, and it decomposes into four distinct causes:

1. **Density is not flow.** Mean vehicles visible per frame is a *stock*; road traffic noise
   emission is driven by a *flow*, $Q$ in vehicles per hour. The two decouple exactly when it
   matters most: in congestion, density is maximal while flow collapses. This is the
   mechanism behind our negative correlation in the gridlocked sessions, and it is why the
   result is structural rather than incidental.

2. **Speed is unobservable in a frame count, and speed dominates.** Above roughly 30–40 km/h
   rolling noise dominates propulsion noise and rises steeply with speed; all standard
   emission models are parameterised on $(Q, v)$ jointly \citep{kephalopoulos2014cnossos}.
   A per-frame count observes neither term.

3. **Parked vehicles are counted.** Without a motion filter, stationary vehicles inflate the
   count with zero acoustic contribution — a pure additive noise term on the predictor, which
   attenuates any regression coefficient toward zero.

4. **Distance is discarded.** The camera field of view is not georeferenced. A motorcycle 5 m
   away and one 40 m away increment the same counter while differing by roughly 18 dB in
   contribution at the receiver.

To these we add an unquantified fifth: **the detector itself was never validated.** We used
the smallest YOLOv8 variant at 640 px input, with COCO classes, on dense two-wheeler streams
for which small-object recall is known to be poor. We therefore report our modal split figures
as *lower bounds on motorcycle share* and we do not treat them as measurements. Establishing
detector accuracy against manual reference counts is a prerequisite for any acoustic use of
these data, and we recommend it be treated as such.

### Implication for practice

Video is a legitimate traffic-noise input, but only if it is instrumented for the right
quantity. The transferable recommendation is:

> Count **line-crossing events with object tracking** to obtain flow $Q$ by vehicle class,
> estimate **speed** from track displacement under a simple ground homography, and validate
> the detector against manual counts before use. With $(Q, v)$ in hand, established emission
> laws \citep{kephalopoulos2014cnossos} apply directly, and the calibration problem changes
> character: one *verifies* published emission curves against local measurements instead of
> attempting to *estimate* emissions from a proxy that does not contain the information.

We state this as a design lesson because the failure mode is invisible before the fact.
Per-frame density is the natural output of an off-the-shelf detector, it is cheap, it looks
like traffic intensity, and it correlates with it well enough to be plausible — and it is
acoustically inert. We expect this trap to be common in low-cost urban sensing.

---

## 5.y Cross-city transfer fails while local training succeeds: evidence for the locality of the morphology–noise relation

### The experiment

Following the methodology we reproduce \citep{nsumba2026sunbird}, we trained a
morphology-to-noise model on the Uganda smartphone dataset (Kampala and Entebbe) and
transferred it to Hanoi, with an offset calibrated on Hanoi training folds. As a rehearsal on
ground truth, we ran the same transfer to Barcelona, where a municipal fixed-sensor network
provides months of `L_Aeq`.

Both transfers were designed to work: the source and target instruments are identical
(smartphones), the sampling protocol is the same, and the feature set — built-area ratio,
road density, intersection count, distance to the nearest road, all within a 300 m radius —
was deliberately reformulated to be invariant to OSM mapping conventions after a first version
proved sensitive to them (Kampala is mapped as individual buildings, Barcelona as whole
blocks).

### The result

**Transfer fails, and fails hard.** The Uganda-pretrained model applied to Hanoi yields a
negative coefficient of determination even after offset calibration — worse than predicting
the global mean everywhere — with a near-zero correlation. Training the same model
architecture, on the same features, directly on our Hanoi measurements works.

The result is therefore not "the features are bad" and not "the model is bad". The features
and the model are held fixed; only the origin of the training data changes.

### Interpretation

The transferable content of a morphology-to-noise model is smaller than the apparent
generality of its inputs suggests. Built-area ratio and road density are physically
meaningful, city-agnostic descriptors — and yet the *function* mapping them to sound
pressure level does not survive relocation. We attribute this to three coupled factors, in
decreasing order of confidence:

1. **Fleet composition and emission behaviour differ.** Hanoi traffic is dominated by
   two-wheelers, whose emission spectrum, speed profile and horn usage differ fundamentally
   from a car-dominated fleet, and whose horn behaviour is itself a first-order noise source
   in Vietnamese cities \citep{nguyen2025horn, phan2010characteristics}. A given road density
   therefore implies a different acoustic source strength in Kampala and in Hanoi.

2. **The same morphological descriptor denotes different urban forms.** A built-area ratio of
   0.4 describes a low-rise sprawl in one city and a narrow-canyon old quarter in another. The
   descriptors are invariant; their acoustic meaning is not, because canyon geometry governs
   reverberant build-up and screening, and the 300 m aggregation radius does not resolve it.

3. **Target quantities are not exchangeable across studies.** Our Barcelona rehearsal
   compares smartphone short samples to class 1 fixed-sensor `L_Aeq` integrated over months.
   These are different statistics of different processes; a large part of the apparent transfer
   failure to Barcelona is attributable to this alone, which is why Barcelona is used strictly
   as a diagnostic and never for training, and why its reported performance figures are not
   comparable to ours.

### Two caveats we impose on our own claim

Honesty about the negative result requires equal honesty about the positive one.

**First, "local training succeeds" is bounded by typology, not by geography.** Under
leave-one-site-out validation — each of our three districts predicted by a model trained only
on the other two — performance degrades sharply and is negative for two sites out of three.
With three sampled typologies, the effective number of independent morphological
configurations available to the model is close to three, whatever the number of measurement
points. Our model interpolates within sampled typologies; it does not extrapolate to unseen
ones. Consequently, and in line with area-of-applicability reasoning \citep{meyer2021aoa}, we
restrict every published map to the sampled envelope and we withdrew an earlier map covering
a district in which no measurement was taken.

**Second, the contribution of morphology must be measured, not assumed.** We report a full
ablation against baselines evaluated on identical splits — including a lookup table of mean
level by (site, hour), which uses no spatial variable whatsoever — under 600 m spatial block
cross-validation, buffered leave-one-out and leave-one-site-out, with bootstrap confidence
intervals (`scripts/evaluate_models.py`, results in `outputs/models/model_comparison.md`).
That ablation is what produced §5.z below: measured rather than assumed, the incremental
contribution of the 300 m morphological aggregates over a single distance-to-road term is
**negative under all three protocols**. An earlier version of this work reported
cross-validation grouped on ~110 m cells, smaller than the 300 m feature aggregation radius,
which leaked information between folds and overstated performance
\citep{roberts2017crossvalidation}; that protocol has been replaced, and the R² = 0.45
reported before July 2026 is an artefact of it.

### Implication for practice

Together, these results define a boundary condition for smartphone-based noise mapping:

> **Cross-city transfer of a purely data-driven morphology-to-noise model should not be
> assumed to work, even with identical instruments, identical protocols and
> convention-invariant features. Local measurement is not a refinement of transfer; it is a
> prerequisite.**

This is a constraint on the ambition of low-cost noise mapping, but it is also an argument
for the hybrid architecture we recommend for future work: a physical propagation core, whose
parameters are transferable because they are physical \citep{kephalopoulos2014cnossos,
bocher2019noisemodelling}, corrected by a locally trained statistical residual model, whose
non-transferability is then confined to a bounded correction term rather than carried by the
whole prediction.

---

## 5.z A one-variable physical baseline outperforms the machine-learning model: the 300 m morphological aggregates carry no usable signal

### The experiment

Our predictive model is a LightGBM regressor on six inputs: four morphological descriptors
aggregated within a 300 m radius (built-area ratio, road density, intersection count,
distance to the nearest road) and two temporal ones (hour, weekend flag). To establish what
that model actually buys, we evaluated it against seven baselines *on identical splits*,
under three protocols of increasing severity — 600 m spatial block cross-validation, buffered
leave-one-out with a 300 m exclusion radius, and leave-one-site-out — with 95 % confidence
intervals from a block bootstrap (n = 363 measurements, 17 spatial blocks,
`scripts/evaluate_models.py`).

One of those baselines is deliberately minimal: an ordinary least-squares regression of the
measured level on $\log_{10} d_{\text{road}}$, the distance to the nearest road. It is a
single free slope and intercept, it encodes nothing but geometric divergence from a line
source, and it uses one of the six variables already available to the full model.

### The result

**The one-variable physical baseline wins under the two protocols that test generalisation,
and it is the only model whose confidence interval excludes zero under all three.**

| Model | inputs | Block-CV 600 m | Buffered LOO 300 m | Leave-one-site-out |
|---|---|---|---|---|
| Mean level by (site, hour) | 0 spatial | −0.008 [−0.18, 0.29] | −0.419 [−0.77, 0.03] | −0.058 [−0.15, −0.03] |
| **Regression on $\log d_{\text{road}}$** | **1** | 0.221 [0.10, 0.29] | **0.200 [0.08, 0.27]** | **0.189 [0.06, 0.27]** |
| LightGBM, morphology only | 4 | 0.153 [−0.09, 0.29] | 0.041 [−0.24, 0.23] | 0.007 [−0.36, 0.18] |
| LightGBM, morphology + time | 6 | **0.304 [0.10, 0.46]** | 0.137 [−0.10, 0.33] | 0.029 [−0.35, 0.21] |

*R², with 95 % bootstrap confidence intervals. Best per column in bold.*

Three readings of this table matter.

**First, the ML model's advantage is an artefact of the permissive protocol.** Under 600 m
block cross-validation the full LightGBM leads (R² = 0.304 against 0.221). Tighten the
protocol and the lead inverts: under buffered leave-one-out it drops to 0.137 against 0.200,
and under leave-one-site-out it collapses to 0.029 against 0.189 — a factor of six. The
distance regression, by contrast, moves by 0.03 across the three protocols. It is the only
model in the comparison that does not care how the folds are drawn, which is the operational
definition of a model that has learned something transferable.

**Second, the 300 m morphological aggregates have negative marginal value.** The comparison
that isolates them is *LightGBM on the four morphological features* against *the regression
on one of those four*. Adding built-area ratio, road density and intersection count to
distance-to-road does not improve prediction; it degrades it, by 0.07 R² under block-CV, 0.16
under buffered LOO and 0.18 under leave-one-site-out. Feature importance tells the same story
from the inside: distance to road is the single largest contributor to gain-based importance
in the fitted model (40 %), matching the three area-aggregated descriptors *combined* (39 %,
split 19 / 11 / 9). The 300 m disk is large enough
to average away the canyon geometry that governs propagation and small enough to be strongly
autocorrelated between neighbouring points — it therefore supplies variance without supplying
information, and a gradient-boosted model with 363 points fits that variance.

**Third, what remains of the ML model is time, not morphology.** The gap between the full
model and the morphology-only ablation under block-CV (0.304 against 0.153) is carried by the
hour-of-day features, which encode the diurnal traffic cycle. That is a real and reproducible
effect, but it is not a spatial one: it does not help the model predict an unmeasured
location, which is what a noise map is for. Consistently, under leave-one-site-out the
time-only ablation is itself negative (R² = −0.139).

### Interpretation

We had assumed the burden of proof ran the other way — that a physical baseline was a sanity
check the learned model would clear. It does not clear it. The honest statement of our
positive result is therefore not "a machine-learning model predicts urban noise from urban
form"; it is:

> **At our sampling density and typological coverage, the predictable part of the spatial
> variation in urban noise is the distance to the nearest road, and a two-parameter physical
> regression captures it more robustly than a six-variable gradient-boosted model. Urban
> morphology aggregated over a 300 m radius adds no measurable predictive value over that
> single term, under any of our three validation protocols.**

This is not an argument that morphology is acoustically irrelevant — canyon geometry,
building height and street width demonstrably govern propagation. It is an argument that
*these descriptors, at this radius, on this sample* do not recover it, and that the
literature's habit of reporting a single R² under a spatially permissive split makes such a
result invisible.

### Implication for practice

The recommendation is a reordering of the modelling pipeline, not an abandonment of learning:

> Report a distance-to-source physical baseline as a mandatory reference in every
> morphology-based noise mapping study, evaluated under a spatial split whose block size
> exceeds the feature aggregation radius. A learned model that does not beat it has not
> demonstrated that morphology carries information — it has demonstrated that its validation
> was optimistic. Where morphology is expected to matter, resolve it at the scale of the
> street canyon rather than aggregating it over a disk that spans several urban blocks.

This result also converges with §5.y from a second direction. There we found that the learned
morphology-to-noise function does not survive relocation; here we find that within a single
city it does not outperform geometry. Both point to the same architecture: a physical
propagation core \citep{kephalopoulos2014cnossos, bocher2019noisemodelling}, whose parameters
are transferable because they are physical, plus a locally fitted residual correction — with
the distance term promoted from one feature among six to the backbone of the prediction.

---

## Notes for the authors *(not for the manuscript)*

- **Les chiffres sont désormais réels** (run du 5 août 2026 sur les 363 mesures) et proviennent
  tous de `outputs/models/metrics.json` / `outputs/models/model_comparison.md`. Ne pas les
  recopier à la main ailleurs : si `evaluate_models.py` est relancé, régénérer le tableau de
  §5.z depuis le JSON.
- **Protocole de référence = buffered leave-one-out 300 m** (`meta.headline_protocol`), parce
  que son rayon d'exclusion égale le rayon d'agrégation des features. C'est le chiffre à citer
  dans l'abstract : `log(dist_road)` R² = 0,200 contre 0,137 pour le LightGBM complet.
- **Nuance à ne pas escamoter** : sous block-CV 600 m — le protocole le plus permissif des
  trois — le LightGBM complet est nominalement devant (0,304 contre 0,221), et son IC recouvre
  celui de la régression. La formulation défendable n'est donc pas « le ML perd partout » mais
  « l'avantage du ML disparaît dès que le découpage teste la généralisation, et s'inverse ».
  §5.z est rédigé ainsi. Un relecteur qui vérifiera le tableau trouvera cette ligne : mieux
  vaut l'avoir écrite nous-mêmes.
- Le ΔR² « apport de la morphologie » affiché dans `model_comparison.md` (+0,312 / +0,556 /
  +0,087) est calculé **contre la table site × heure**, pas contre `dist_road`. C'est le second
  chiffre qui porte l'argument de §5.z ; ne pas confondre les deux dans le manuscrit.
- La "0.8 % to 4.2 % of variance" et "median offset 15 s" de §5.x viennent de
  `calibrate_emissions.py` et `build_report.py` ; re-vérifier après tout nouveau run de
  `count_vehicles.py`.

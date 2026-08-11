# Negative results as contributions

> **Manuscript placement.** Goes in *Discussion*, as three subsections. These three
> results are the most original contribution of the work and must be presented as
> findings obtained, not as difficulties encountered. Section 5.z is the paper's
> central argument. Citation keys refer to [`references.bib`](references.bib).

---

Three of our experiments returned negative results. All three were designed to succeed, all
three failed for identifiable reasons, and all three constrain how urban noise should be
modelled in motorcycle-dominated cities. We report them as findings rather than as
limitations, because each answers a question that the positive results do not.

---

## 5.x Video vehicle counts do not carry recoverable emission coefficients, whether counted as density or as flow

### The experiment

We recorded 147 timestamped traffic videos alongside our noise measurements (median offset
15 s between video and measurement), counted motorcycles, cars, buses and trucks with a
YOLOv8 detector sampled at approximately 1 frame per second, and attempted to recover a
per-vehicle-class sound emission by regressing measured acoustic energy on vehicle counts.
When that failed for reasons we traced to the *choice of quantity*, we implemented the
correction we ourselves recommended — object tracking and line-crossing flow — and re-ran the
whole analysis. Both passes are reported below, because the second is what makes the first
interpretable.

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

### We took our own advice, and it was not enough

Because the recommendation above is ours, we implemented it rather than leaving it as future
work. All 147 videos were re-processed with multi-object tracking (ByteTrack over the same
detector), sampling at 10 frames per second, counting **line-crossing events** at a virtual
line placed across the dominant direction of travel, and converting them to a flow in
vehicles per minute per class. The resulting counts are internally coherent: the dwell time
implied by Little's law, $L = \lambda W$, agrees with the observed track duration to within a
factor 0.6 (4.7 s against 7.6 s median), whereas the naive crossing rule we first wrote
implied 0.3 s — an implicit vehicle speed of 60–90 m s⁻¹.

**Flow does not recover the acoustic signal either.** Pooled over the 147 matched videos the
correlation between total flow and measured level is $r = -0.11$, against $-0.15$ for density:
marginally less negative, still the wrong sign. Motorcycle flow — the dominant class in this
fleet — is uncorrelated at $r = -0.004$. Re-fitting the non-negative emission model in the
physically correct form, energy per *passage* rather than per visible vehicle
($E = E_{\text{bg}(s)} + \sum_c Q_c e_c$), still drives the motorcycle and car coefficients to
the boundary at zero. A non-zero coefficient does appear for heavy vehicles (46.8 dB per
passage), but it is fitted on **4 videos out of 147**, carrying 0.4 % of total counted flow,
with $r = +0.02$ against level; we report it as an artefact of the non-negativity constraint
latching onto a handful of points, not as an identified emission.

One structured exception is worth recording. Vinh Tuy — the transport-corridor site, the only
one of the three with substantial through-traffic rather than dense local circulation — is
the only site with a positive association, and it *strengthens* when density is replaced by
flow ($r = +0.22 \rightarrow +0.30$, $R^2 = 0.09$). This is the direction the physics
predicts, and it suggests the quantity is not meaningless so much as swamped: where traffic
genuinely flows past a receiver, flow tracks level; where it is congested, or where the
receiver's exposure is dominated by a canyon it does not sit in, it does not.

The residual obstacles are the two we listed and did not remove: **speed is still
unobservable** without a ground homography, and **distance is still discarded** because the
field of view is not georeferenced. Our conclusion therefore sharpens rather than reverses.
Replacing density by flow is necessary — it is the difference between a quantity that is
structurally wrong and one that is merely incomplete — but on its own it is *not sufficient*.
The recommendation for practitioners becomes: instrument for $(Q, v)$ **and** georeference the
field of view; obtaining $Q$ alone buys a coherent traffic statistic and no acoustic
calibration.

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
on the other two — the *learned* models degrade sharply and are negative for two sites out of
three (LightGBM: −0.42 at Hoan Kiem, −0.58 at Vinh Tuy). This is one of the places where the
physical model of §5.z behaves qualitatively differently: it reaches +0.42 at Vinh Tuy and
−0.08 at Hoan Kiem, because geometric divergence from a road is the same law in an old
quarter and in a transport corridor, whereas the mapping from morphological aggregates to
level is not. The caveat nevertheless stands for both. With three sampled typologies, the
effective number of independent morphological configurations is close to three, whatever the
number of measurement points, and three is not a basis for claiming coverage of a city.
Consequently, and in line with area-of-applicability reasoning \citep{meyer2021aoa}, we
restrict every published map to the sampled envelope — irrespective of the score — and we
withdrew an earlier map covering a district in which no measurement was taken.

**Second, the contribution of morphology must be measured, not assumed.** We report a full
ablation against baselines evaluated on identical splits — including a lookup table of mean
level by (site, hour), which uses no spatial variable whatsoever — under 600 m spatial block
cross-validation, buffered leave-one-out and leave-one-site-out, with bootstrap confidence
intervals (`scripts/04_evaluate_models.py`, results in `models/model_comparison.md`).
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

## 5.z A three-parameter physical model outperforms every learned model we built, including the hybrid designed to fix it

### The experiment

Our predictive model is a LightGBM regressor on six inputs: four morphological descriptors
aggregated within a 300 m radius (built-area ratio, road density, intersection count,
distance to the nearest road) and two temporal ones (hour, weekend flag). To establish what
that model actually buys, we evaluated it against seven baselines *on identical splits*,
under three protocols of increasing severity — 600 m spatial block cross-validation, buffered
leave-one-out with a 300 m exclusion radius, and leave-one-site-out — with 95 % confidence
intervals from a block bootstrap (n = 363 measurements, 17 spatial blocks,
`scripts/04_evaluate_models.py`).

One of those baselines is deliberately minimal: an ordinary least-squares regression of the
measured level on $\log_{10} d_{\text{road}}$, the distance to the nearest road. It is a
single free slope and intercept, it encodes nothing but geometric divergence from a line
source, and it uses one of the six variables already available to the full model.

We then did the obvious next thing: we *built* the hybrid architecture that our own
discussion recommends. A physical core carries the prediction and a LightGBM learns only its
residual. The core treats each road class as an incoherent **line source**, whose intensity
falls as $1/d$ rather than $1/d^2$:

$$E(x) = \frac{A_{\text{hw}}}{\max(d_{\text{hw}}, d_0)} + \frac{A_{\text{res}}}{\max(d_{\text{res}}, d_0)} + B, \qquad L(x) = 10\log_{10} E(x)$$

with $d_{\text{hw}}$ and $d_{\text{res}}$ the distances to the nearest major axis and to the
nearest local street — separated by OSM `highway` tag, because a four-lane trunk road and a
residential lane differ by an order of magnitude in acoustic power per unit length. The three
coefficients are constrained non-negative and fitted in decibels. We also rebuilt the pure
LightGBM on the same improved features (separated distances, hour encoded cyclically as
$\sin/\cos$).

### The result

**Every elaboration we added improves the permissive protocol and degrades the strict ones.
The three-parameter physical core is the best model under both protocols that test
generalisation, and it is the only model whose confidence interval excludes zero under all
three.**

| Model | Block-CV 600 m | **Buffered LOO 300 m** | Leave-one-site-out |
|---|---|---|---|
| Mean level by (site, hour) | −0.008 | −0.419 | −0.058 |
| Regression on $\log d_{\text{road}}$ (2 param.) | 0.221 [0.09, 0.29] | 0.200 [0.08, 0.27] | 0.189 [0.06, 0.27] |
| **Physical core (3 param.)** | 0.255 [0.09, 0.36] | **0.246 [0.10, 0.34]** | **0.222 [0.05, 0.33]** |
| LightGBM v1 (6 features) | 0.304 [0.10, 0.46] | 0.137 [−0.10, 0.33] | 0.029 [−0.35, 0.21] |
| LightGBM v2 (8 features) | 0.332 [0.11, 0.49] | 0.099 [−0.13, 0.25] | −0.035 [−0.40, 0.16] |
| Hybrid, physics + ML residual | **0.395 [0.18, 0.53]** | 0.123 [−0.22, 0.29] | 0.035 [−0.41, 0.23] |
| Hybrid, capacity-restricted residual | 0.378 [0.20, 0.51] | 0.144 [−0.15, 0.35] | 0.106 [−0.27, 0.27] |

*R², with 95 % bootstrap confidence intervals. Reference protocol in bold; buffered
leave-one-out is the reference because its exclusion radius equals the feature aggregation
radius. Best per column in bold.*

**Read the table by column and the ranking almost exactly reverses.** Under block-CV the
order is hybrid > hybrid-restricted > LightGBM v2 > LightGBM v1 > physical core > distance
regression. Under the reference protocol it is physical core > distance regression >
hybrid-restricted > LightGBM v1 > hybrid > LightGBM v2. The models that win the permissive
split are the ones that lose the strict one, and vice versa, monotonically. That is the
signature of capacity fitting spatial autocorrelation rather than physics.

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

### The hybrid architecture does not rescue the learned component

The result that surprised us most is the one we least wanted. We proposed the hybrid
architecture ourselves, in the concluding paragraph of §5.y, as the constructive answer to
both negative results. Built and evaluated on identical splits, **the learned residual is a
net loss under both strict protocols**: relative to the bare physical core it gains
ΔR² = +0.140 under block-CV, and loses −0.123 under buffered leave-one-out and −0.187 under
leave-one-site-out.

Two subsidiary observations sharpen this.

*Better features made the pure ML model worse.* Separating the road classes and encoding the
hour cyclically are textbook improvements, and they behave as advertised under block-CV
(0.332 against 0.304). Under the reference protocol the same change costs 0.038 R²
(0.099 against 0.137), and under leave-one-site-out it turns a marginally positive model
negative. Giving a gradient-boosted model finer spatial descriptors, at this sample size,
buys it a finer ability to memorise where the training points are.

*Constraining the residual recovers part of the loss, and that is the tell.* A
capacity-restricted variant — five leaves, 120 trees, and denied the distance features the
physics has already consumed — is worse under block-CV (0.378) and better under both strict
protocols (0.144 and 0.106) than the unconstrained hybrid. The direction of that trade is
the diagnosis: what the unconstrained residual learns is not physics the core is missing, it
is the spatial arrangement of our 363 points.

Because of this, **the model we deliver is the bare physical core**, not the hybrid we set
out to build. That choice is made in code, by selecting the best candidate under the
reference protocol from a list fixed in advance (`scripts/04_evaluate_models.py`), so that the
published map cannot silently inherit a model that only wins on a permissive split.

### Interpretation

We had assumed the burden of proof ran the other way — that a physical baseline was a sanity
check the learned model would clear. It does not clear it, and neither does the hybrid built
to give it a second chance. The honest statement of our positive result is therefore not "a
machine-learning model predicts urban noise from urban form"; it is:

> **At our sampling density and typological coverage, the predictable part of the spatial
> variation in urban noise is the geometric divergence of sound from the road network. A
> three-parameter line-source model captures it more robustly than any learned model we
> built, including a hybrid that uses that same physical model as its base. Urban morphology
> aggregated over a 300 m radius adds no measurable predictive value, under any of our three
> validation protocols.**

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
city it does not outperform geometry, and that grafting it onto a physical core as a residual
does not repair it either.

We therefore state the hybrid recommendation more carefully than we first did. A physical
propagation core \citep{kephalopoulos2014cnossos, bocher2019noisemodelling} is clearly the
right backbone: ours, with three parameters, is the best model we have under every protocol
that tests generalisation. But the "plus a locally trained residual" half of the
recommendation is **not** free. A residual model is still a statistical model fitted to the
same spatially autocorrelated sample, and it inherits the same failure mode; whether it helps
must be demonstrated under a spatial split, not assumed from the elegance of the
decomposition. On our data it does not, and we report the architecture as tested and
rejected at this sample size rather than as future work that would obviously have worked.
The open question we hand on is whether the residual becomes worth its risk with a denser
sample and more typologies — not whether hybridisation is a good idea in the abstract.

---

## Notes for the authors *(not for the manuscript)*

- **Les chiffres sont désormais réels** (run du 5 août 2026 sur les 363 mesures) et proviennent
  tous de `models/metrics.json` / `models/model_comparison.md`. Ne pas les
  recopier à la main ailleurs : si `evaluate_models.py` est relancé, régénérer le tableau de
  §5.z depuis le JSON.
- **Protocole de référence = buffered leave-one-out 300 m** (`meta.headline_protocol`), parce
  que son rayon d'exclusion égale le rayon d'agrégation des features. Chiffre à citer dans
  l'abstract : **noyau physique R² = 0,246**, devant `log(dist_road)` 0,200, l'hybride 0,123
  et le LightGBM v1 0,137.
- **Nuance à ne pas escamoter** : sous block-CV 600 m — le protocole le plus permissif des
  trois — l'ordre est presque exactement INVERSE (hybride 0,395 en tête, noyau physique
  0,255 en avant-dernier), et les IC se recouvrent largement. La formulation défendable n'est
  donc pas « le ML perd partout » mais « le classement s'inverse dès que le découpage teste la
  généralisation ». §5.z est rédigé ainsi, et affiche les trois colonnes. Un relecteur qui
  vérifiera le tableau trouvera cette inversion : mieux vaut l'avoir écrite nous-mêmes.
- **Le modèle livré est choisi PAR LE CODE**, pas par nous : `evaluate_models.py` prend le
  meilleur R² sous le protocole de référence parmi six candidats arrêtés à l'avance, écrit le
  choix dans `meta.delivered_model`, et `export_gama_zones.py` lit le drapeau
  `apply_residual`. C'est ce qui garantit que la carte publiée n'hérite pas silencieusement
  d'un modèle qui ne gagne que sur un découpage permissif. Si un run futur fait gagner
  l'hybride sous BLOO, la livraison basculera d'elle-même — et il faudra mettre §5.z à jour.
- **Ne pas présenter l'hybride comme un échec d'implémentation.** Il est correctement
  construit et il gagne largement sous block-CV. Le résultat est que cet avantage ne survit
  pas à un découpage spatial honnête, ce qui est une information sur la méthode, pas sur le
  code.
- Le ΔR² « apport de la morphologie » affiché dans `model_comparison.md` (+0,312 / +0,556 /
  +0,087) est calculé **contre la table site × heure**, pas contre `dist_road`. C'est le second
  chiffre qui porte l'argument de §5.z ; ne pas confondre les deux dans le manuscrit.
- La "0.8 % to 4.2 % of variance" et "median offset 15 s" de §5.x viennent de
  `calibrate_emissions.py` et `build_report.py` ; re-vérifier après tout nouveau run de
  `count_vehicles.py`.

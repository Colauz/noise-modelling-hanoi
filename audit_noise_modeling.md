# Audit scientifique — *Noise Modelling Hanoi*

> ## ⚙️ État des suites données (5 août 2026)
>
> Le projet a **pivoté vers une étude méthodologique** : pas de sonomètre professionnel
> disponible, campagne de terrain close. Les recommandations qui supposaient du matériel ou
> du terrain supplémentaire sont donc caduques ; celles qui portent sur l'analyse et la
> rédaction ont été appliquées. Détail dans `ROADMAP.md`.
>
> | Recommandation | Statut |
> |---|---|
> | **P0-1** CV honnête + baselines + ablation + IC | ✅ `scripts/evaluate_models.py` (blocs 600 m, BLOO 300 m, LOSO, 8 modèles, bootstrap par bloc) |
> | **P0-2** Recadrage métrique et normes | ✅ cible `L_A,25s`, OMS `L_den`/`L_night` retirées partout, QCVN en statistique descriptive + sensibilité — `paper/sections/metrology.md` |
> | **P0-3** Ancrage absolu | ⚠️ **adapté** : pas de sonomètre → bornage du biais par ancrage sur la littérature instrumentée (`scripts/literature_anchoring.py`). Le biais est encadré, pas corrigé. |
> | **P0-4** Nettoyage du dépôt | ✅ artefacts Bach Khoa archivés dans `outputs/deprecated/`, notebook 09 neutralisé, `metrics.json` remplace la recopie manuelle |
> | **P0-5** Publication des données | ⏳ à faire (Zenodo + DOI + déclaration éthique) |
> | **P1-1** Campagne complémentaire | ❌ **sans objet** — terrain clos |
> | **P1-2** Plafond de R² mesuré | ❌ sans objet (exige des points fixes répétés) |
> | **P1-3** Couche physique CNOSSOS | ⏸️ reporté en *future work* |
> | **P1-4** Comptage vidéo en débit | ⏸️ argumenté comme résultat négatif — `paper/sections/negative_results.md` |
> | **P1-6** Physique GAMA | ✅ décomposition énergie fond/trafic, zone 30 bornée à 150 m — corrigé et vérifié numériquement |
>
> Le texte d'audit ci-dessous est **conservé tel quel** : il documente l'état au moment du
> diagnostic et les chiffres qu'il cite (R² 0.45, etc.) sont ceux de l'ancien protocole.

**Date de l'audit :** 5 août 2026
**Périmètre :** dépôt `noise-modelling-hanoi` @ `c5108d6` (README, ROADMAP, `field/`, `scripts/`, `notebooks/01→09`, `gama/`, `outputs/`)
**Angle :** data science + modélisation acoustique environnementale. Regard de rapporteur.

> **Note de méthode et de limite de cet audit.** Le dossier `data/` est absent de la machine (il est
> `gitignore`). Je n'ai donc **pas pu recalculer** les scores du modèle à partir des mesures brutes.
> Tout ce que j'annonce ci-dessous est soit **[V]** vérifié par calcul sur les artefacts présents dans
> `outputs/`, soit **[C]** lu directement dans le code, soit **[I]** inféré/déduit et signalé comme tel.
> Cette impossibilité de rejouer la chaîne est elle-même un constat d'audit (§4.8).

---

## 1. Résumé de l'état actuel

### 1.1 Ce que fait le projet aujourd'hui

| Bloc | Contenu réel |
|---|---|
| **Collecte** | 363 mesures ponctuelles au smartphone, 3 quartiers de Hanoï (Ocean Park 184, Hoan Kiem 99, Vinh Tuy 80) **[V]**, via ODK Collect → KoboToolbox, application sonomètre *Decibel X* (pondération A, réponse SLOW), 3 collecteurs inter-calibrés, ~20-30 s par point + clip audio ≥ 10 s **[C]** |
| **Données annexes** | 147 vidéos trafic horodatées comptées par YOLOv8n, registre de chantiers (formulaire dédié), météo horaire Open-Meteo (réanalyse) **[C]** |
| **Nettoyage** | `scripts/prepare_field_data.py` : source unique, dédup, filtre GPS `accuracy < 50 m`, filtre dB ∈ [20,120], réassignation du site par plus proche centre GPS, backfill explicite des champs v2, offsets de calibration (tous à 0.0) **[C]** |
| **Modèle** | LightGBM, 6 features : `built_area_ratio`, `road_density_km_km2`, `intersection_count`, `dist_road_m` (tous dans un rayon **300 m** issu d'OSM) + `hour` + `is_weekend`. Entraîné **directement** sur les 363 mesures **[C]** |
| **Score annoncé** | r 0.69 / R² 0.45 / MAE 4.2 dB en « CV spatiale honnête » ; transfert Ouganda→Hanoï R² −1.26 **[C, sorties du notebook 08]** |
| **Carte** | grille prédite, deux versions coexistantes : ①  8 640 cellules ~30 m autour de **Bach Khoa** (notebooks 08/09) ; ②  5 587 cellules 40 m sur les **3 sites mesurés**, une colonne par heure `h5…h21` (`scripts/export_gama_zones.py`) **[V]** |
| **Simulation** | GAMA `hanoi_noise.gaml` (446 lignes) : fond horaire prédit + véhicules mobiles (visuels), chantiers calibrés en énergie, sliders heure / volume de trafic / mitigation **[C]** |
| **Validation** | `scripts/validate_simulation.py` : confrontation grille ↔ mesures, **explicitement annoncée comme *in-sample*** — biais −0.52 dB, MAE 3.68 dB, RMSE 4.98 dB, r 0.719, 74 % dans ±5 dB **[V, recalculé]** |
| **Livrables** | `outputs/report.pdf` (8 pages), diaporama HTML, cartes Folium, figures |

### 1.2 Verdict global

**Le projet est un très bon travail d'ingénieur et un travail de recherche encore incomplet.**

L'ingénierie est solide : chaîne bout-en-bout fonctionnelle, source de vérité unique pour le
nettoyage, séparation nette « mesuré / prédit / calibré / exclu », refus documenté d'inventer des
paramètres. C'est rare et c'est à porter au crédit du projet.

Mais **trois verrous empêchent aujourd'hui de qualifier l'étude de « fiable et généralisable »**
au sens où une revue Q1 l'entendrait :

1. **Le chiffre-phare « R² 0.45 en validation croisée spatiale honnête » n'est pas honnête** : les
   blocs de CV font ~110 m alors que les features sont calculées sur un disque de 300 m. Il y a
   fuite spatiale structurelle. Le seul protocole réellement hors-échantillon présent au dossier —
   le *leave-one-site-out* — donne **R² de −0.68 à +0.21**, c'est-à-dire *pire que la moyenne*. (§4.3)
2. **Le lien morphologie → bruit n'est pas démontré comme utile.** Un simple tableau de correspondance
   « site × heure », sans aucune morphologie, atteint **R² 0.27 / MAE 4.79 dB en leave-one-out**
   sur les mêmes points **[V, calculé par moi]** — contre 0.45 / 4.2 annoncés pour le modèle avec une
   CV plus permissive. L'apport propre des 4 features OSM n'est donc, au mieux, que modeste, et
   n'a jamais été isolé.
3. **La métrologie n'est pas ancrée.** Les 3 téléphones sont calibrés *entre eux*, jamais contre une
   référence absolue (sonomètre classe 1/2 ou calibreur acoustique). Toute la distribution des
   niveaux — et donc les 39 % de dépassement QCVN — peut être décalée en bloc de plusieurs dB
   sans qu'on puisse le savoir. (§4.1)

Aucun de ces trois points n'est rédhibitoire. Tous sont réparables, et deux d'entre eux le sont
en quelques jours de travail sans nouvelle collecte. Le §5 donne le plan.

---

## 2. Décorticage de la Data Collection

### 2.1 Instrumentation

- **Capteur :** application *Decibel X* sur smartphone grand public. Réglages homogènes : pondération
  **A**, réponse **SLOW**, trim 0.0 **[C, `field/README.md`]**.
- **Grandeur relevée :** un seul nombre, la valeur « AVG » lue à l'écran. Le formulaire dit
  *« Read LAeq / average value from the dB app »* **[V, XLSForm]**. Ni durée d'intégration
  enregistrée, ni L_Amax, ni L10/L90, ni tiers d'octave.
- **Calibration :** procédure **relative** en 5 étapes — les 3 téléphones côte à côte, le téléphone du
  milieu pris comme référence arbitraire, offsets saisis dans le trim de l'app **[C]**.
  Dans le code, `CALIBRATION_OFFSET = {'laurian': 0.0, 'lucas': 0.0, 'quang': 0.0}` **[C]**.
- **Hauteur :** ~1,2 m, tenu à la main **[C]**. Non enregistré par point.
- **Modèle de téléphone :** **non enregistré**. Le champ `collector` en est un proxy imparfait.

### 2.2 Plan d'échantillonnage spatial

- 3 zones choisies pour leurs typologies contrastées : Ocean Park (nouveau tissu vertical),
  Vinh Tuy (corridor de transport), Hoan Kiem (vieux quartier). Choix pertinent sur le principe.
- **Sélection des points à l'intérieur d'une zone : non spécifiée.** Ni grille, ni tirage aléatoire,
  ni stratification documentée. Le protocole dit seulement *« varier les distances à la route »* **[C]**.
  C'est de l'échantillonnage de convenance le long des rues accessibles.
- `dist_to_road` est saisi en **classes** (0-2 / 2-10 / 10-30 / 30-60 / >60 m), pas en mètres **[V]**.
- Filtre GPS retenu : `accuracy < 50 m` **[C]**, alors que le formulaire demande au collecteur
  d'attendre `< 10 m` **[V]**. Incohérence : 50 m d'incertitude de position sur une grille de 40 m,
  c'est plus d'une cellule d'erreur.

### 2.3 Plan d'échantillonnage temporel

Distribution horaire réelle, recalculée **[V]** :

```
 5h:  6   6h: 27   7h: 53   8h: 37   9h:  0 ←  trou complet
10h: 17  11h: 31  12h: 22  13h: 18  14h:  9
15h: 48  16h: 10  17h: 54  18h: 16  19h:  9
20h:  2  21h:  1  (+3 points à 22-23h)
```

- **Nuit quasi absente.** La période réglementée « nuit » du QCVN 26:2010 court de 21 h à 6 h.
  Le jeu de données y compte **10 points sur 363, soit 2,8 %** **[V, via `hanoi_exceedances.csv`]**,
  et **zéro mesure entre 00 h et 05 h**. Or c'est la période au seuil le plus sévère (55 dB) et celle
  qui pèse le plus lourd sur la santé (OMS : L_night).
- **Trou à 9 h**, creux marqué à 14 h, 16 h, 19-21 h.
- **Week-end** : signalé comme « léger » dans le rapport, non quantifiable ici (données absentes).
- **Saisonnalité : nulle.** Campagne concentrée sur juin-juillet 2026 **[I, historique git]** —
  une seule saison, en mousson. Aucune couverture du Têt, de la saison sèche, des vacances scolaires.

### 2.4 Métadonnées collectées

Le formulaire v2 est bien conçu **[V, XLSForm]** : site, collecteur, GPS, audio, dB, catégorie de
source, classe de distance à la route, orientation du téléphone, direction du micro, distance à la
source dominante, comptages moto/voiture/PL/VE, vidéo trafic, chantier audible. Bonne granularité.

Manquent, et ce sont les champs qui coûtent le plus cher à rattraper *a posteriori* : **durée
d'intégration**, **modèle de téléphone**, **hauteur de mesure**, **vent ressenti / présence de
bonnette**, **état de la chaussée (sèche/humide)**, **identifiant de point fixe** permettant la
répétition, **largeur de rue et hauteur de front bâti** (ratio H/L du canyon urbain).

---

## 3. Décorticage du Workflow

```
Kobo CSV ──► prepare_field_data.py ──► measurements.csv
                                            │
   vidéos ──► count_vehicles.py (YOLOv8n) ──┼──► vehicle_counts.csv
                                            │
                       Open-Meteo (réanalyse)┘
                                            │
                          nb 07 : EDA, normes, carte Folium
                                            │
                          nb 08 : features OSM 300 m + LightGBM + CV
                                            │
                    ┌───────────────────────┴───────────────────────┐
        nb 09 (Bach Khoa)                             export_gama_zones.py (3 sites × 17 h)
                    │                                               │
                    └──────────► outputs/gama_inputs/ ◄──────────────┘   ⚠ deux producteurs
                                            │
                            calibrate_emissions.py (NNLS en énergie)
                                            │
                          GAMA hanoi_noise.gaml ──► validate_simulation.py (in-sample)
                                            │
                                     build_report.py ──► report.pdf
```

**Algorithme de cartographie.** Il n'y a **aucune interpolation spatiale** (ni krigeage, ni IDW) et
**aucun modèle physique de propagation**. La carte est une pure **régression d'usage des sols
(LUR — Land Use Regression)** : pour chaque cellule, on calcule 4 descripteurs OSM dans un disque de
300 m + l'heure, et on demande sa prédiction à LightGBM. C'est une approche légitime et publiée,
mais c'est un choix méthodologique qui n'est **jamais justifié ni comparé** à une alternative dans
le dossier.

**Protocole de validation actuel.**
- CV « spatiale » : `GroupKFold(5)` sur des groupes = `(lat.round(3), lon.round(3))`, soit des
  cellules de **~111 m × 104 m** à la latitude de Hanoï **[C, notebook 08]**.
- CV aléatoire, gardée comme borne haute optimiste. Bonne pratique.
- Leave-one-site-out, reporté en page 6 du PDF : R² = 0.21 / −0.68 / −0.37 **[C]**.
- Validation de la simulation : *in-sample*, honnêtement étiquetée comme telle **[C]**.

---

## 4. Évaluation critique — Gap Analysis

### 4.0 Points forts (à conserver et à mettre en avant dans le manuscrit)

Ils sont réels et il faut les défendre :

1. **Honnêteté méthodologique documentée.** Le refus d'injecter des émissions véhicule inventées
   quand la NNLS renvoie des coefficients nuls (`calibrate_emissions.py`) est exactement le bon
   réflexe scientifique. La note « validation in-sample » dans `validate_simulation.py` et dans le
   PDF idem. Le backfill « honnête » qui laisse des NaN plutôt que d'inventer idem. **C'est le
   meilleur atout du dossier** — beaucoup d'études publiées ne le font pas.
2. **Le résultat négatif sur le transfert inter-villes est publiable.** Ouganda → Hanoï R² −1.26,
   avec le contrôle Barcelone en répétition générale. C'est une contribution méthodologique
   authentique, et le survey paper la réclame explicitement.
3. **Séparation explicite du statut de chaque couche** (prédit / mesuré / calibré / exclu) dans
   l'en-tête du `.gaml` et dans `export_gama_zones.py`. Exemplaire.
4. **Source de vérité unique** pour le nettoyage terrain, réutilisée comme module par le notebook.
   Pas de logique dupliquée. Bonne architecture logicielle.
5. **Feature `built_area_ratio` invariante** introduite après diagnostic du biais de convention
   cartographique OSM (Kampala = bâtiments individuels, Barcelone = îlots). Diagnostic fin et bien mené.
6. **Traçabilité des corrections** : réassignation des sites par GPS, avec log des 6 corrections.
7. **Protocole terrain écrit et reproductible**, formulaires XLSForm versionnés.

---

### 4.1 🔴 CRITIQUE — Métrologie : aucun ancrage absolu

**Le problème.** La calibration croisée aligne les 3 téléphones **entre eux**, sur un quatrième
arbitraire (« le téléphone du milieu »). Il n'existe **aucun point de rattachement à une référence
acoustique**. La conséquence est directe : un biais systématique commun aux 3 appareils est
strictement invisible et se propage intégralement dans tous les résultats.

**Pourquoi c'est grave ici.** Le livrable principal du rapport est *« 39 % des mesures dépassent le
QCVN »*. Un biais de +3 dB ferait chuter ce chiffre ; un biais de −3 dB l'enverrait au-delà de 55 %.
La littérature sur les sonomètres smartphone donne des écarts couramment de ±3 à ±8 dB(A) selon
l'appareil et l'OS, non linéaires en niveau. **Aucune conclusion normative n'est actuellement
défendable.**

**Aggravants.**
- Le modèle de téléphone n'est pas enregistré → impossible de corriger *a posteriori*.
- Pas de bonnette anti-vent mentionnée. L'analyse « pas d'effet du vent » **[C, notebook 07]** s'appuie
  sur le vent de **réanalyse Open-Meteo** (maille ~10-25 km) — un instrument incapable de détecter
  un artefact de micro qui dépend du vent *local à 1,2 m*. C'est une absence de preuve, pas une
  preuve d'absence.
- Plancher et saturation non caractérisés. Le max mesuré est **88,0 dB** **[V]**, dans la zone où les
  chaînes AGC des smartphones commencent à comprimer. Les niveaux hauts sont probablement écrasés,
  ce qui **réduit artificiellement la variance de la cible** (σ = 7,1 dB **[V]**) et donc plafonne
  mécaniquement le R² atteignable.

### 4.2 🔴 CRITIQUE — La grandeur mesurée n'est comparable à aucune norme citée

**Le problème.** La grandeur du projet est un « AVG » de ~20-30 s. Or :

| Norme citée dans le rapport | Grandeur réelle de la norme | Comparable au « AVG 20-30 s » ? |
|---|---|---|
| QCVN 26:2010/BTNMT, 70 / 55 dB | L_Aeq sur la période de référence, appareil classe 1 ou 2, méthode TCVN 7878-2 | **Non** — durée et instrument non conformes |
| OMS 2018, 53 / 45 dB | **L_den** et **L_night**, moyennes **annuelles**, avec pénalités +5 dB soirée / +10 dB nuit | **Non, très loin** |

Le PDF (§3.4) présente « WHO (road-traffic guideline) — Day 53 / Night 45 » dans un tableau
jour/nuit. C'est une **erreur de nature** : L_den n'est pas un indicateur « de jour », c'est un
indicateur agrégé sur 24 h et sur l'année. Un rapporteur de revue Q1 relèvera ce point en premier.

La ROADMAP note d'ailleurs elle-même le problème (« positionner notre métrique dB face à
Leq/L_dn/L_max, cf. survey paper §V ») — mais le rapport a été diffusé sans l'avoir traité.

**Second problème, quantitatif.** Un échantillon de 25 s sur une voirie hanoïenne ne converge pas
vers le L_Aeq de la période : le passage d'un bus ou un coup de klaxon déplace la valeur de 5-10 dB.
Le rapport affirme *« ±5 dB de bruit irréductible, plafonnant le R² vers 0,6 »* — affirmation
**posée sans aucune dérivation ni mesure**. Elle est probablement juste, mais elle est
actuellement invérifiable, alors qu'elle est facile à établir expérimentalement (§5, P0-3).

### 4.3 🔴 CRITIQUE — La validation du modèle surestime la performance

C'est le point le plus grave sur le plan de la data science.

**(a) Fuite spatiale dans la « CV spatiale ».**
Les groupes de `GroupKFold` sont des cellules de ~110 m. Les features sont des agrégats sur un
disque de **rayon 300 m**. Deux points distants de 110 m ont donc des disques dont l'intersection
dépasse **85 % de la surface** : leurs vecteurs de features sont quasi identiques, et leurs niveaux
de bruit sont fortement autocorrélés. Le modèle voit donc, en apprentissage, des quasi-jumeaux de
ses points de test. **Le R² 0.45 n'est pas hors-échantillon.**

La règle admise en modélisation spatiale (Roberts et al. 2017, *Ecography* ; Meyer & Pebesma 2021,
*Nat. Commun.*) est que le bloc de CV doit dépasser la portée d'autocorrélation des prédicteurs —
ici **au minimum 600 m** (2 × rayon du buffer), idéalement avec zone tampon exclue (*buffered
leave-one-out*).

**(b) La seule validation réellement hors-échantillon donne un résultat négatif.**
Le *leave-one-site-out* du PDF : **R² = +0.21 (Ocean Park), −0.68 (Vinh Tuy), −0.37 (Hoan Kiem)**.
Un R² négatif signifie : *le modèle fait moins bien que de prédire partout la moyenne globale*.
Le rapport le qualifie de « stress test » « bruité sur de petits échantillons » et renvoie vers le
0.45 comme « chiffre fiable ». **C'est l'inverse.** Le leave-one-site-out est le protocole propre,
c'est le 0.45 qui est contaminé. La conclusion correcte est : *à ce stade, le modèle n'extrapole pas
à une typologie urbaine non vue* — ce que la section Limitations du PDF dit d'ailleurs en toutes
lettres, en contradiction avec le chiffre mis en avant en couverture.

**(c) Le nombre effectif de degrés de liberté est de l'ordre de 3, pas de 363.**
Les 4 features de morphologie sont des agrégats sur 300 m. À l'intérieur d'un site, dont l'emprise
fait quelques centaines de mètres, ces 4 valeurs varient très peu. Le modèle dispose donc en pratique
de **3 configurations morphologiques distinctes**, répétées 363 fois. Toute inférence sur la relation
morphologie → bruit repose sur n ≈ 3. Aucun intervalle de confiance n'est reporté nulle part.

**(d) Aucun modèle de comparaison n'a été testé.** Le seul point de comparaison du notebook 08 est
la moyenne (MAE 5,9 dB). J'ai construit le comparateur manquant à partir de
`outputs/hanoi/validation_simulation.csv` **[V, calcul de l'audit]** :

| Prédicteur | Protocole | R² | MAE |
|---|---|---|---|
| Moyenne globale | — | 0.00 | 5.9 dB |
| **Moyenne par site** (aucune morphologie) | leave-one-out | 0.03 | 5.79 dB |
| **Moyenne par (site × heure)** (aucune morphologie) | leave-one-out | **0.27** | **4.79 dB** |
| LightGBM morphologie + heure | « CV spatiale » 110 m (optimiste) | 0.45 | 4.2 dB |
| Grille GAMA vs mesures | *in-sample* | 0.51 | 3.68 dB |

*Lecture :* une table de correspondance à 29 entrées, sans une seule variable spatiale, capte déjà
**plus de la moitié** de la performance annoncée du modèle — et elle, en leave-one-out strict.
Les protocoles ne sont pas rigoureusement identiques (LOO sur 360 points vs GroupKFold sur 363),
donc ce tableau est un **indice fort, pas une preuve** ; mais il rend indispensable de mesurer
l'apport propre de la morphologie (§5, P0-1). En l'état, la question *« vos 4 features OSM
servent-elles à quelque chose ? »* n'a pas de réponse au dossier.

**(e) Aucune quantification d'incertitude.** Pas d'intervalle de confiance bootstrap sur R²/MAE, pas
d'intervalle de prédiction sur la carte, pas d'analyse de l'autocorrélation spatiale des résidus
(Moran's I), pas de masque de domaine d'applicabilité sur les cellules extrapolées.

**(f) La comparaison à Barcelone (R² 0.61) est trompeuse.** Elle figure dans le même tableau que les
scores Hanoï en page 6 du PDF. Or Barcelone = capteurs fixes classe 1, L_Aeq intégré sur 4 mois.
Ce n'est pas la même cible statistique : un L_Aeq long terme est intrinsèquement beaucoup plus
prévisible qu'un instantané de 25 s. Le docstring de `train_v2_invariant.py` le dit correctement —
le PDF, non. À retirer du tableau ou à isoler avec un avertissement explicite.

### 4.4 🟠 MAJEUR — Résolution et physique de la carte

- **Le lissage à 300 m détruit exactement l'information qu'une carte de bruit doit porter.** Deux
  cellules voisines de la grille 40 m partagent > 98 % de leur disque de features : leurs prédictions
  sont quasi identiques. Le modèle est structurellement incapable de représenter le contraste
  façade / cour intérieure (10-15 dB en tissu dense), l'effet d'écran des bâtiments, ou le gradient
  transversal d'une rue. On le voit dans les chiffres : σ(simulé) = 5,52 dB contre
  σ(mesuré) = 7,10 dB **[V]** — la carte est significativement plus plate que la réalité.
- **Aucune physique.** Pas de divergence géométrique, pas d'effet de sol, pas de diffraction /
  masquage par le bâti, pas de réflexion de façade, pas d'absorption atmosphérique. Les empreintes
  bâties sont pourtant déjà téléchargées et exportées en shapefile — la matière première est là,
  inutilisée.
- **La carte diffusée ne couvre pas la zone étudiée.** `outputs/hanoi/hanoi_noise_map.csv`,
  `hanoi_heatmap.html` et `outputs/gama_inputs/noise_map.csv` couvrent un disque de 1 500 m autour de
  **Bach Khoa** — un quartier où **aucune mesure n'a été prise** **[V : lat 20.992-21.019,
  lon 105.829-105.858, 8 640 cellules]**. C'est de l'extrapolation vers une typologie non vue, par un
  modèle dont le leave-one-site-out est négatif. Ces trois fichiers ne doivent pas être diffusés en
  l'état.

### 4.5 🟠 MAJEUR — Comptage vidéo : aucune validation du détecteur, mauvaise grandeur

- **La grandeur comptée est la mauvaise.** `count_vehicles.py` mesure une *densité de véhicules
  visibles par image* **[C]**. L'acoustique du trafic dépend du **débit** (véh/h) et de la **vitesse**,
  pas du nombre d'objets présents dans un champ de caméra non géoréférencé. C'est la cause racine
  de l'échec de `calibrate_emissions.py` — cause que le script lui-même identifie correctement.
- **Aucune évaluation de l'exactitude du détecteur.** YOLOv8**n** (le plus petit modèle), `imgsz=640`,
  `conf=0.3`, classes COCO **[C]**. Sur un flux de motos hanoïen, la sous-détection est massive et
  connue. Le rapport publie pourtant une figure « composition du trafic par site »
  (Hoan Kiem 65 % motos, Ocean Park 84 % voitures **[V, `fleet_mix.csv`]`**) **sans une seule ligne
  de validation** — ni comptage manuel de référence, ni précision/rappel, ni MAPE. Ces parts modales
  ne sont, à ce stade, pas publiables.
- **Véhicules garés comptés**, absence de filtre de mouvement — déjà identifié dans la ROADMAP.
- **Appariement vidéo ↔ mesure à ±5 min** **[C, `MATCH_MAX_S = 300`]** alors que la mesure dure 25 s.
  Un écart de 5 min entre le trafic filmé et le niveau relevé suffit à décorréler les deux. Le PDF
  annonce un écart médian de 15 s — bien ; mais la queue de distribution n'est pas contrôlée.

### 4.6 🟠 MAJEUR — Calibration des chantiers : extrapolation fragile

La source équivalente chantier (64,7 dB à 56 m, propagée en 20·log₁₀) dérive d'un **écart de médianes
de +2,0 dB** entre 32 points « chantier signalé » et 152 points « sans », à Ocean Park **[C]**.

- **Aucun test de significativité, aucun intervalle de confiance.** +2,0 dB sur n=32 vs n=152, avec
  σ ≈ 8 dB à Ocean Park **[V]** : l'erreur-type de la différence est de l'ordre de ±1,5 dB. L'écart
  n'est probablement pas distinguable de zéro.
- **Aucun contrôle de confusion.** Les points « chantier » ne sont pas appariés aux autres sur la
  distance à la route, l'heure ou la sous-zone. Un chantier est typiquement en bord de voirie ;
  l'écart peut être entièrement dû au trafic.
- **`construction_nearby` est partiellement dérivé de la cible.** Le backfill le déduit de la
  catégorie de bruit déclarée (`class` contient « construction ») **[C]**. Or `class` est renseigné
  par le collecteur *au vu de ce qu'il entend*. On sélectionne donc partiellement sur la variable
  qu'on cherche à expliquer → biais circulaire vers un écart positif.
- **Extrapolation forte** : de +2 dB observés à 56 m, on remonte une source qui, à 25 m, ajoute
  ~+7 dB **[C]**. Le facteur d'extrapolation est de 3,5× l'effet observé, avec la seule divergence
  géométrique et sans barre d'erreur.

### 4.7 🟡 MODÉRÉ — Simulation GAMA : deux approximations physiquement fausses

Le `.gaml` est bien écrit et bien commenté. Deux corrections de fond :

1. **La loi 10·log₁₀(k) est appliquée uniformément à toutes les cellules** **[C, `reflex scenario`]**,
   y compris aux cours intérieures et aux cellules éloignées de toute voirie. Physiquement,
   `10·log₁₀(k)` ne s'applique qu'à **la part d'énergie attribuable au trafic**. Tripler le trafic ne
   peut pas ajouter +4,8 dB dans une cour où le trafic ne contribue que marginalement.
   *Correctif :* décomposer `E_cellule = E_trafic(d_route) + E_résiduel` et n'appliquer le facteur
   qu'à `E_trafic`.
2. **La mitigation « zone 30 » applique −3 dB à toute la zone** **[C]**, y compris aux rues qui ne
   sont pas en zone 30 et aux cellules loin des rues concernées. Même correctif : appliquer sur les
   routes sélectionnées, avec décroissance en distance.

Le PLAN.md prévoit par ailleurs des **agents piétons récepteurs** (palier 2) — c'est la bonne idée,
et c'est ce qui ferait de GAMA une contribution plutôt qu'un visualiseur. Elle n'est pas implémentée.

### 4.8 🟠 MAJEUR — Reproductibilité

- **Les données ne sont pas rejouables.** `data/` est hors git et absent de la machine. Ni moi, ni un
  rapporteur, ni le futur toi de janvier ne peut recalculer le moindre chiffre. Pour un projet qui
  se réclame de la lignée d'un article *Scientific Data*, c'est bloquant.
- **Deux producteurs écrivent les mêmes fichiers.** `notebooks/09_export_gama.ipynb` et
  `scripts/export_gama_zones.py` écrivent tous deux dans `outputs/gama_inputs/`. L'état actuel du
  dossier est **hybride** : `noise_points.shp` est la version 3-zones (5 587 cellules, colonnes
  `h5…h21`) **[V]**, mais `noise_map.csv` est encore la version **Bach Khoa** périmée (8 640 lignes)
  **[V]**. Rejouer le notebook 09 écraserait silencieusement les entrées de la simulation.
- **Recopie manuelle des scores.** Le README instruit de *« recopier les scores du notebook 08 dans
  MODEL/PERSITE en haut de build_report.py »* **[C]**. Le PDF peut donc afficher des métriques
  désynchronisées du modèle réellement livré. Les valeurs y sont d'ailleurs des chaînes de
  caractères en dur.
- **Le PDF contient des sections périmées.** La page 8 « Next steps » annonce encore *« comptage
  véhicules sur les 83 vidéos »* et *« GAMA : importer la carte »* **[C]** — deux tâches faites depuis,
  avec 147 vidéos.
- Pas de pinning d'environnement (`>=` partout), pas de `data/processed/` créé par le code
  (le notebook 08 écrit dans un dossier qu'il ne crée jamais), notebooks exécutés sur une autre
  machine en Python 3.9.

### 4.9 🟡 MODÉRÉ — Conformité normative et éthique

- **Pas de déclaration éthique / IRB.** 147 vidéos filmées dans l'espace public à Hanoï : visages et
  plaques d'immatriculation. Une revue Q1 exigera une déclaration (approbation ou exemption du
  comité d'éthique de VinUni) et, si les vidéos sont partagées, un floutage.
- **Pas de licence de données**, pas de plan de dépôt (Zenodo/DOI), pas de pseudonymisation des
  collecteurs (prénoms en clair dans le pipeline).
- **Pas de référence explicite aux normes de mesure** : ISO 1996-1/2 (conditions météo, hauteur,
  distance aux surfaces réfléchissantes, durée), TCVN 7878-2:2010, ni au cadre CNOSSOS-EU.

---

## 5. Plan d'action pour une « étude parfaite »

Priorisation : **P0** = sans cela le manuscrit ne passe pas la relecture ; **P1** = fait passer de
« correct » à « bon » ; **P2** = confort et ambition.

### P0 — À faire avant toute nouvelle diffusion (≈ 1 à 2 semaines, sans nouvelle collecte)

**P0-1. Refaire la validation avec des blocs spatiaux honnêtes, et publier le tableau d'ablation.**
*Pourquoi :* c'est le point sur lequel l'étude est aujourd'hui attaquable en une phrase.
*Comment :*
- Remplacer les groupes `round(3)` par un **blocage spatial ≥ 600 m** (2 × rayon de buffer) ou, mieux,
  un *buffered leave-one-out* (exclure de l'apprentissage tout point à moins de 300 m du point testé).
  `sklearn.model_selection.GroupKFold` sur un identifiant de bloc calculé en UTM, ou `spacv`.
- Publier **quatre lignes de baseline** dans le même tableau, sous le même protocole exact :
  ① moyenne globale · ② moyenne par site · ③ moyenne par (site × heure) · ④ `dist_road_m` seul
  (régression linéaire) · ⑤ IDW / krigeage ordinaire sur les mesures · ⑥ LightGBM complet.
- Ajouter une **ablation de features** : LightGBM sans morphologie, sans heure, etc.
- Ajouter des **IC bootstrap 95 %** sur R² et MAE, avec ré-échantillonnage **par bloc spatial**.
*Critère de succès :* on peut écrire une phrase de la forme *« la morphologie apporte ΔR² = X
[IC 95 %] au-delà d'un modèle site × heure »*, quelle que soit la valeur de X.
*Risque assumé :* il est possible que ΔR² soit petit. Ce n'est pas un échec — c'est un résultat, et
c'est exactement le genre de résultat que le survey paper cité appelle.

**P0-2. Reformuler la métrique et les comparaisons aux normes.**
- Renommer partout la cible en **`L_Aeq,25s` (proxy instantané, smartphone non certifié)**, jamais
  « dB » nu, jamais « LAeq » sans indice de durée.
- **Retirer L_den / L_night du tableau des seuils** ou les déplacer dans un encadré « pour contexte
  santé publique uniquement, non comparable à notre grandeur ».
- Reformuler les dépassements QCVN en **« taux d'échantillons instantanés supérieurs au seuil »**,
  jamais en « dépassement réglementaire », et l'assortir de l'incertitude de calibration.
- Retirer la ligne Barcelone du tableau de performance, ou l'isoler avec l'avertissement du §4.3(f).

**P0-3. Ancrer la calibration absolue.** *(1 journée, coût faible)*
- Emprunter un **sonomètre classe 1 ou classe 2** (labo génie civil / environnement de VinUni, ou
  location) ou un **calibreur acoustique 94 dB / 1 kHz**.
- Protocole : 3 téléphones + référence côte à côte, **≥ 20 minutes en L_Aeq,1min simultané**, sur
  **3 environnements de niveaux contrastés** (~50, ~65, ~80 dB) — pas un seul point, pour capter la
  **non-linéarité** en niveau.
- Ajuster une correction par téléphone : `L_ref = a·L_phone + b`, publier `a`, `b`, R² et l'écart-type
  résiduel. Reporter dans `CALIBRATION_OFFSET` (à généraliser en correction affine).
- **Caractériser plancher et saturation** : point le plus calme atteignable et point > 90 dB pour
  situer le début de compression.
*Critère de succès :* une phrase du type *« après correction, l'écart résiduel au sonomètre de
référence est de ±X dB (1σ) sur la plage 50-85 dB »*.

**P0-4. Nettoyer l'état du dépôt.**
- **Supprimer** `outputs/hanoi/hanoi_noise_map.*`, `hanoi_heatmap.html` et
  `outputs/gama_inputs/noise_map.csv` (artefacts Bach Khoa non validés), ou les déplacer dans un
  `outputs/deprecated/` avec un README expliquant pourquoi.
- **Retirer les cellules 1-7 du notebook 08** (grille Bach Khoa) et **archiver le notebook 09** :
  `export_gama_zones.py` est désormais le seul producteur légitime de `outputs/gama_inputs/`.
- Faire écrire au notebook 08 un `outputs/models/metrics.json`, et faire **lire** ce JSON par
  `build_report.py`. Plus aucune métrique en dur.
- Mettre à jour la page 8 « Next steps » du PDF.
- Aligner le filtre GPS sur le protocole : `accuracy < 15 m` (et publier la distribution + le nombre
  de points écartés).

**P0-5. Publier le jeu de données.**
- Committer `measurements.csv` (363 lignes, collecteurs pseudonymisés en C1/C2/C3) **dans le dépôt** —
  il fait quelques dizaines de kio, il n'y a aucune raison de l'exclure.
- Déposer sur **Zenodo** (dataset + DOI) : mesures, `vehicle_counts.csv`, registre chantiers,
  formulaires XLSForm, script de nettoyage. Les vidéos brutes restent hors dépôt (RGPD/vie privée).
- Ajouter une **déclaration éthique** (statut IRB VinUni) et une licence (CC-BY-4.0 pour les données,
  MIT/Apache pour le code).

### P1 — Pour atteindre un niveau académique solide (≈ 4 à 8 semaines, collecte incluse)

**P1-1. Campagne complémentaire ciblée — priorité aux trous, pas au volume.**
Le problème n'est pas « 363 c'est peu » : c'est *où* et *quand* ils sont. Ordre de priorité :

| Cible | Volume indicatif | Pourquoi |
|---|---|---|
| **Nuit 22 h - 05 h** | ≥ 60 points, ≥ 3 nuits, les 3 sites | 2,8 % actuellement, zéro entre 0 h et 5 h ; c'est la période au seuil le plus sévère |
| **Points fixes répétés** | **15-20 points**, chacun mesuré **≥ 6 fois** à des heures/jours différents | Permet la décomposition de variance (§P1-2) — le gain scientifique le plus élevé par heure de terrain |
| **Une 4ᵉ et une 5ᵉ typologie** | ~60 points chacune | Zone industrielle / périurbaine / résidentielle calme. Sans nouvelle typologie, le leave-one-site-out restera sur n=3 et restera négatif |
| **Week-end** | ~50 points | Couverture actuelle « légère », non quantifiée |
| **Trous horaires** 9 h, 14 h, 16 h, 19-21 h | ~40 points | Le profil horaire est un livrable central du rapport |

**Métadonnées à ajouter impérativement au formulaire v3 :**
`point_id` (pour les points fixes répétés) · `duration_s` (durée réelle d'intégration) ·
`phone_model` · `height_m` · `windscreen` (oui/non) · `road_surface` (sec/humide) ·
`wind_local` (anémomètre de poche, ~15 €) · `street_width_m` et `facade_height_m` (ratio de canyon) ·
`dist_to_road_m` **en mètres** (garder la classe en secours) · `L_Amax` et `L90` si l'app les affiche
(Decibel X les propose : ce sont deux features gratuites et très informatives).

**Ce qu'il faut aussi supprimer du protocole :** interdire la mesure sous la pluie et par vent
> 5 m/s (ISO 1996-2), et documenter la distance minimale aux façades (≥ 3,5 m) pour éviter les
réflexions.

**P1-2. Quantifier le plafond de R² au lieu de l'affirmer.**
Avec les points fixes répétés de P1-1 : décomposition de variance
`σ²_total = σ²_entre-points + σ²_intra-point`. Le R² maximal atteignable par *tout* modèle
spatial vaut `σ²_entre / σ²_total`. Cela transforme la phrase molle du rapport (« ±5 dB
irréductibles, plafond ~0,6 ») en un résultat mesuré, et cela **valorise** le R² obtenu au lieu de
le subir. C'est un ajout à fort rendement pour un manuscrit.

**P1-3. Passer d'une LUR aveugle à un modèle hybride physique + ML.**
C'est la recommandation la plus structurante, et le nom du dépôt y invite : utiliser
**NoiseModelling** (UMRAE/Cerema, open source, GPL, moteur **CNOSSOS-EU**, entrées OSM natives,
sortie SIG). Architecture cible :

```
OSM (routes + bâtiments + hauteurs)
        │
        ├─► NoiseModelling / CNOSSOS-EU ──► L_Aeq physique par récepteur
        │      (émission Q,v par classe · divergence · effet de sol ·
        │       diffraction/masquage bâti · réflexions de façade)
        │                                          │
        └─► features morphologiques ───────────────┤
                                                   ▼
                       LightGBM sur le RÉSIDU (mesure − physique)
                                                   │
                                                   ▼
                                    carte finale = physique + résidu corrigé
```

Bénéfices :
- La carte retrouve la **résolution fine** (façade vs cour, effet d'écran) que le buffer 300 m détruit.
- Le modèle devient **extrapolable** à un quartier non mesuré, puisque la physique ne dépend pas de
  l'échantillon — ce qui répond directement au R² négatif du leave-one-site-out.
- La comparaison **physique seule / ML seul / hybride** devient une section de résultats à part
  entière, et c'est exactement le type de contribution que le survey paper appelle.
- Les hauteurs de bâtiment manquantes dans OSM se comblent avec `building:levels` × 3,2 m, ou avec
  un MNS libre (Copernicus DEM 30 m en secours).

*Si NoiseModelling est jugé trop lourd dans le temps imparti :* implémenter a minima une couche
physique simplifiée (source linéique par route pondérée par la classe OSM `highway`, divergence
`−10·log₁₀(d)` en source linéique, et un masque de visibilité bâti). Même grossière, elle apportera
un contraste spatial que les 4 features actuelles ne peuvent pas produire.

**P1-4. Refaire le comptage vidéo sur la bonne grandeur.**
- Passer au **tracking** (`ultralytics` + ByteTrack/BoT-SORT) et compter des **franchissements de
  ligne** → **débit Q en véh/h par classe**, la grandeur qu'exige CNOSSOS.
- Estimer la **vitesse** via une homographie simple (2 repères au sol de distance connue par site).
- Passer à **YOLOv8m/l ou YOLO11**, `imgsz` 960-1280, `conf` ~0.25 — la nano à 640 px sous-détecte
  massivement les motos.
- **Valider le détecteur** : comptage manuel de référence sur **10 vidéos** (une par site et par
  créneau), publier précision / rappel / MAPE par classe. **Sans cette validation, ne pas publier
  les parts modales.**
- Filtre de mouvement pour exclure les véhicules garés (déjà dans la ROADMAP).
- Resserrer l'appariement vidéo↔mesure de 300 s à **60 s**, et publier la distribution des écarts.
- *Une fois le débit et la vitesse disponibles*, `calibrate_emissions.py` peut redevenir
  identifiable — ou, mieux, on n'a plus besoin de calibrer : CNOSSOS fournit les lois d'émission
  par classe de véhicule et par vitesse, et on les **vérifie** sur nos mesures au lieu de les inventer.

**P1-5. Fiabiliser la calibration chantier.**
- Appariement (*matching*) des points « chantier » et « sans chantier » sur `dist_to_road`, heure et
  sous-zone, avant de calculer l'écart. Ou modèle linéaire avec ces covariables.
- **Test de permutation** + IC bootstrap sur l'écart, et publication du n effectif.
- **Retirer le backfill circulaire** : ne comparer que sur les points où `construction_nearby` a été
  *effectivement saisi*, et traiter la valeur dérivée de `class` comme une variable distincte.
- Transect dB-distance explicite : le protocole prévoit déjà « 2-3 mesures en s'éloignant » — les
  exploiter pour **ajuster** la loi d'atténuation observée au lieu d'imposer 20·log₁₀.
- Assortir le +2 dB d'une barre d'erreur dans le `.gaml` et faire une **analyse de sensibilité**
  (scénario bas / central / haut).

**P1-6. Corriger la physique de GAMA.** Les deux points du §4.7 (décomposition trafic/résiduel pour
le facteur `10·log₁₀(k)`, application locale de la zone 30). Puis implémenter le **palier 2 du
PLAN.md** — les agents piétons et la **dose d'exposition** : c'est ce qui distingue une simulation
agent-based d'une carte animée, et c'est ce qui produit un indicateur (exposition de population)
que la carte seule ne donne pas.

### P2 — Ambition et bonus

- **Benchmark de modèles** (tâche déjà dans la ROADMAP, statut à clarifier avec l'encadrant) :
  LightGBM vs Random Forest vs régression linéaire régularisée vs LSTM/ST-GNN de Barcelone. Note :
  les modèles temporels (LSTM, ST-GNN) **exigent des séries continues** — donc la tâche
  « téléphone posé une journée » du reliquat technique en est le **prérequis**, pas un bonus.
- **Séries temporelles longues** : 3-5 points avec un téléphone en enregistrement continu sur 24 h
  → vrai L_Aeq horaire, L_den/L_night calculables, et de quoi **quantifier le biais** de l'échantillon
  25 s par rapport au L_Aeq horaire. Fort rendement, coût quasi nul.
- **Audio comme feature.** 363 clips ≥ 10 s sont déjà collectés et ne servent qu'au QC. Des
  embeddings (YAMNet / PANNs / VGGish) donneraient une classification objective des sources, en
  remplacement de la catégorie déclarative — et pourraient devenir des features du modèle.
- **Cross-validation spatiale à la Meyer & Pebesma** avec carte du **domaine d'applicabilité** (AOA) :
  masquer sur la carte finale les cellules où le modèle extrapole hors de son espace de features.
  Visuellement parlant et méthodologiquement irréprochable.
- **Carte d'incertitude** publiée à côté de la carte de niveaux (LightGBM quantile, ou variance
  d'ensemble). Une carte de bruit sans carte d'incertitude est aujourd'hui difficilement publiable.

---

## 6. Ce qu'il faut écrire (et ne plus écrire) dans le manuscrit

**À reformuler :**

| Formulation actuelle | Formulation défendable |
|---|---|
| « R² 0.45 sous validation croisée spatiale honnête » | « R² 0.45 avec blocs de 110 m ; ce protocole reste contaminé par le recouvrement des buffers de 300 m. Sous blocage à 600 m : R² = … ; en leave-one-site-out : −0.68 à +0.21 » |
| « 39 % des mesures dépassent le QCVN » | « 39 % des échantillons instantanés dépassent le seuil QCVN diurne. Notre grandeur n'est pas le L_Aeq de référence de la norme et notre instrumentation n'est pas certifiée : ce taux est indicatif, non réglementaire » |
| « WHO day 53 / night 45 » | à retirer du tableau des seuils ; mentionner L_den/L_night uniquement en discussion santé publique |
| « supérieur à la référence Barcelone R² 0.61 » | à retirer : cibles non comparables (L_Aeq 4 mois, capteurs classe 1) |
| « ±5 dB irréductibles, plafond R² ≈ 0.6 » | remplacer par le plafond **mesuré** issu de la décomposition de variance (P1-2) |
| « Le transfert échoue, l'entraînement direct fonctionne » | « Le transfert inter-villes échoue (R² −1.26). L'entraînement direct fonctionne **à l'intérieur des typologies échantillonnées** et ne généralise pas encore à une typologie non vue » |

**À mettre en avant, ce sont vos vraies contributions :**
1. Le résultat négatif documenté sur le transfert inter-villes, avec Barcelone en contrôle.
2. La non-identifiabilité des émissions véhicule à partir d'un comptage de densité vidéo — un
   résultat négatif utile, et une leçon de conception d'expérience.
3. Un protocole terrain smartphone reproductible, avec formulaires ouverts et données déposées.
4. La chaîne complète mesure → modèle → carte horaire → simulation ABM avec statut explicite de
   chaque couche.

---

## 7. Récapitulatif des chiffres vérifiés pendant l'audit

| Grandeur | Valeur | Source |
|---|---|---|
| Mesures totales / sites | 363 — OP 184, HK 99, VT 80 | `hanoi_exceedances.csv`, `*_measurements.dbf` |
| Mesures nocturnes (21 h-6 h) | **10 (2,8 %)**, dont 0 entre 0 h et 5 h | `hanoi_exceedances.csv`, histogramme horaire |
| Heures sans aucune mesure | **9 h** (et quasi-vide 20-23 h) | `validation_simulation.csv` |
| Plage / dispersion mesurée | 47,0 - 88,0 dB · σ = 7,10 dB | `validation_simulation.csv` |
| Dispersion simulée | σ = 5,52 dB (carte plus plate que le réel) | idem |
| Validation GAMA *in-sample* | n=360 · biais −0,52 · MAE 3,68 · RMSE 4,98 · r 0,719 · 74 % dans ±5 dB | recalcul de l'audit |
| Baseline « moyenne par site » (LOO) | R² 0,03 · MAE 5,79 dB | calcul de l'audit |
| **Baseline « site × heure » (LOO)** | **R² 0,27 · MAE 4,79 dB** | calcul de l'audit |
| Modèle LightGBM, CV 110 m | R² 0,45 · MAE 4,2 dB | sorties notebook 08 |
| Modèle, leave-one-site-out | R² **+0,21 / −0,68 / −0,37** | `build_report.py` (PERSITE) |
| Taille des blocs de CV « spatiale » | ~111 m × 104 m, vs buffer de features **300 m** | notebook 08 |
| Grille Bach Khoa (non mesurée) | 8 640 cellules, lat 20,992-21,019 / lon 105,829-105,858 | `hanoi_noise_map.csv` |
| Grille 3 sites (GAMA) | 5 587 cellules 40 m × 17 heures | `noise_points.dbf` |
| Émissions véhicule (NNLS) | moto / voiture / PL = **0,0** — non identifiables | `emission_calibration.csv` |
| Source chantier calibrée | 64,7 dB à 56 m, depuis un écart de médianes de **+2,0 dB** (n=32 vs 152) | `emission_calibration.csv`, `.gaml` |
| Reproduction Sunbird (notebook 06) | R² 0,25 · MAE 8,17 dB, sur le config `small` = **1 000 lignes**, split aléatoire | notebook 06 |
| Offsets de calibration appliqués | 0,0 / 0,0 / 0,0 — aucune référence absolue | `prepare_field_data.py` |

---

## 8. Conclusion

L'étude **tient debout comme travail d'ingénieur** : la chaîne est complète, le code est propre, et
l'honnêteté intellectuelle affichée dans les scripts (refus d'inventer des émissions, mention
explicite du caractère in-sample d'une validation) est au-dessus de ce qu'on lit dans beaucoup
d'articles publiés.

Elle **ne tient pas encore comme étude scientifique généralisable**, pour trois raisons cumulatives :
une métrologie non ancrée à une référence absolue, une validation croisée qui fuit et masque un
leave-one-site-out négatif, et une carte dont la résolution effective (300 m) est incompatible avec
l'objet qu'elle prétend représenter.

Le chemin le plus court vers une étude défendable ne passe pas par « plus de mesures » : il passe par
**P0-1** (validation honnête + ablation), **P0-3** (une journée avec un sonomètre de référence) et
**P0-2** (reformulation de la métrique et des normes). Ces trois actions, réalisables en une à deux
semaines sans retourner sur le terrain, transforment un chiffre attaquable en une contribution
solide — y compris si le résultat devient moins flatteur. Ensuite seulement, **P1-3** (couche
physique CNOSSOS/NoiseModelling) et **P1-1** (nuit + points fixes répétés + 4ᵉ typologie) font
passer le travail au niveau d'une publication.

Le résultat négatif sur le transfert inter-villes et la non-identifiabilité des émissions par
comptage vidéo sont, en l'état, les deux contributions les plus originales du dossier. Il faut les
assumer et les mettre au centre, pas les traiter comme des accidents de parcours.

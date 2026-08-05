# Roadmap

*Mise à jour : 5 août 2026 — pivot vers une étude méthodologique*

## Le pivot (5 août 2026)

Pas de sonomètre professionnel disponible, **campagne de terrain définitivement close**.
Le projet ne cherche donc plus à produire une carte de bruit de référence pour Hanoï — il ne
peut pas, et le prétendre serait indéfendable. Il devient une **étude méthodologique** sur les
données en main : ce qu'un protocole smartphone à bas coût permet d'établir, ce qu'il ne
permet pas, et pourquoi. Les deux résultats négatifs obtenus deviennent le cœur de la
contribution.

Base : `audit_noise_modeling.md` (audit du 5 août 2026).

**État** : 363 mesures / 3 sites · 147 vidéos comptées par YOLO · pas d'effet météo robuste ·
grille de bruit sur les 3 zones mesurées × 17 heures · simulation GAMA corrigée · rapport
8 pages branché sur `metrics.json`.

## Le résultat central (5 août 2026)

Les scripts ont tourné sur les vraies données. Le verdict de l'ablation est le suivant, et
c'est lui que défend le papier :

> **Une simple régression physique sur `log(dist_road)` — deux paramètres, une variable —
> généralise mieux que notre modèle LightGBM à 6 variables. La morphologie urbaine agrégée
> dans un rayon de 300 m n'apporte aucun gain mesurable au-delà de ce seul terme de distance.**

R² par protocole (n = 363, 17 blocs, IC 95 % bootstrap, `outputs/models/model_comparison.md`) :

| Modèle | entrées | Block-CV 600 m | **Buffered LOO 300 m** | Leave-one-site-out |
|---|---|---|---|---|
| Table site × heure | 0 spatiale | −0,008 | −0,419 | −0,058 |
| **Régression sur log(dist_road)** | **1** | 0,221 | **0,200** | **0,189** |
| LightGBM morphologie seule | 4 | 0,153 | 0,041 | 0,007 |
| LightGBM morphologie + temps | 6 | **0,304** | 0,137 | 0,029 |

Trois lectures :

1. **L'avance du ML est un artefact du protocole permissif.** Le LightGBM ne mène que sous
   block-CV 600 m. Sous buffered LOO (protocole de référence, rayon d'exclusion = rayon des
   features) l'ordre s'inverse ; sous leave-one-site-out le ML s'effondre d'un facteur 6
   (0,029) quand la régression bouge de 0,03 sur les trois protocoles. C'est le seul modèle
   dont l'IC exclut zéro partout.
2. **Les agrégats morphologiques à 300 m ont un apport marginal NÉGATIF.** Ajouter ratio bâti,
   densité de voirie et intersections à `dist_road` fait perdre 0,07 / 0,16 / 0,18 de R² selon
   le protocole. Le disque de 300 m moyenne la géométrie de canyon qui gouverne la propagation
   et reste autocorrélé entre points voisins : il apporte de la variance, pas de l'information.
3. **Ce qui reste du ML, c'est le temps, pas l'espace.** L'écart modèle complet / morphologie
   seule sous block-CV (0,304 vs 0,153) est porté par l'heure. Effet réel, mais non spatial :
   il n'aide pas à prédire un lieu non mesuré, ce qui est précisément l'objet d'une carte.
   Sous leave-one-site-out l'ablation « temps seul » est elle-même négative (−0,139).

Rédigé en §5.z de `paper/sections/negative_results.md`. **Le R² 0,45 affiché jusqu'en juillet
2026 est un artefact de la CV groupée sur cellules de 110 m** (plus petites que le rayon de
300 m des features) : il ne doit plus apparaître nulle part.

## Corrections appliquées (5 août 2026)

| # | Correction | Livrable |
|---|---|---|
| 1 | **CV honnête** : blocs spatiaux 600 m + buffered leave-one-out 300 m + leave-one-site-out, en remplacement du `GroupKFold` sur cellules de 110 m qui fuyait | `scripts/evaluate_models.py` |
| 2 | **Baselines + ablation** : 8 modèles sur les mêmes découpages, dont la table `site × heure` sans aucune variable spatiale ; IC 95 % bootstrap par bloc | `outputs/models/model_comparison.md` |
| 3 | **Fin des métriques recopiées à la main** : le rapport lit `metrics.json` et refuse de tourner sans | `scripts/build_report.py` |
| 4 | **Recadrage métrologique** : cible renommée `L_A,25s`, statut « relatif, pas absolu » assumé, valeurs OMS `L_den`/`L_night` retirées partout, dépassements QCVN présentés comme statistique descriptive + sensibilité au biais | `paper/sections/metrology.md`, `build_report.py`, `hanoi_noise.gaml` |
| 5 | **Ancrage sur la littérature instrumentée** : bornage du biais absolu plausible par comparaison stratifiée à Phan et al. 2010 (Hanoï, RION NL-21/22) et Gelb & Apparicio 2019 (HCMV, dosimètres) | `scripts/literature_anchoring.py`, `paper/bibliography.bib` |
| 6 | **Physique GAMA corrigée** : `10·log10(k)` et le −3 dB « zone 30 » ne s'appliquent plus qu'à la part d'énergie attribuable au trafic, et la zone 30 est bornée à 150 m d'une route | `gama/hanoi_noise.gaml` |
| 7 | **Carte recadrée sur la zone étudiée** : les artefacts « Bach Khoa » (quartier sans aucune mesure) sont archivés ; un seul producteur pour `outputs/gama_inputs/` | `outputs/deprecated/`, notebook 09 neutralisé |
| 8 | **Résultats négatifs valorisés** : trois sous-sections de Discussion rédigées, dont §5.z (`dist_road` > ML) qui devient l'argument central | `paper/sections/negative_results.md` |
| 9 | **Trafic recompté** : les 147 vidéos repassées sous YOLOv8, `vehicle_counts.csv` régénéré, `fleet_by_hour.csv` reconstruit, page 5 du rapport rétablie | `scripts/experiments/count_vehicles.py`, `outputs/report.pdf` |

### Vérification de la correction GAMA (Ocean Park, 17 h)

| Cellule | Base | Trafic ×3, ancien | Trafic ×3, corrigé |
|---|---|---|---|
| la plus calme | 53,3 dB | 58,1 dB | **53,3 dB** |
| médiane | 65,4 dB | 70,2 dB | 69,4 dB |
| la plus bruyante | 78,6 dB | 83,4 dB | 83,3 dB |

L'ancienne formule annonçait −7,0 dB en moyenne de zone pour la piétonnisation ; la formule
corrigée donne **−3,5 dB**. Le bénéfice des scénarios était surestimé d'un facteur 2.
Invariant vérifié : à k = 1 sans mitigation, la carte est identique à la carte prédite.

## Ce qu'il reste

### 🔴 Bloquant avant toute diffusion

- [x] **Lancer les scripts sur les vraies données.** Fait le 5 août 2026 :
      `count_vehicles.py` (147 vidéos) → `evaluate_models.py` → `literature_anchoring.py` →
      `export_gama_zones.py` → `build_report.py`. Toutes les métriques publiées viennent
      maintenant d'un run réel.
- [x] **Reporter les vrais chiffres** dans `paper/sections/negative_results.md` : fait, §5.z
      contient le tableau complet des trois protocoles.
- [ ] **Vérifier Phan et al. 2010 sur le PDF** (bibliothèque VinUni) : les valeurs `L_den`
      70-83 dB viennent de sources secondaires, statut `to_check` dans
      `literature_anchoring.py`. Basculer en `verified` une fois confirmé.

### 🟡 Pour le manuscrit

- [ ] **Rédaction** : Methods (protocole + métrologie), Results (comparaison de modèles),
      Discussion (les deux résultats négatifs), Limitations.
- [ ] **Déclaration éthique** : statut IRB VinUni pour les 147 vidéos filmées dans l'espace
      public (visages, plaques). Exigé par une revue Q1.
- [ ] **Dépôt des données** : `measurements.csv` (collecteurs pseudonymisés) dans le dépôt +
      Zenodo avec DOI. Licence CC-BY-4.0 données / MIT code.
- [ ] **Validation du détecteur YOLO** : comptage manuel de référence sur ~10 vidéos,
      précision/rappel/MAPE par classe. **Sans cela, ne pas publier les parts modales.**

### ⏸️ Reporté ou abandonné

- **Benchmark LSTM / ST-GNN (Barcelone)** — prérequis manquant : ces modèles exigent des
  séries temporelles continues, que nous n'avons pas. À reclarifier avec l'encadrant.
- **Audio démolition (10 h)** — hors périmètre du pivot.
- **Couche physique CNOSSOS / NoiseModelling** — reste hors budget temps, mais **le résultat
  central ci-dessus en fait la suite logique du projet, plus une simple option** : si un terme
  de distance à deux paramètres bat déjà le ML, un vrai noyau de propagation physique corrigé
  par un résidu appris localement est l'architecture indiquée. À porter en *future work* en
  tête de liste, pas en fin de section.
- **Agents piétons GAMA (palier 2 du PLAN)** — non implémenté.

## Règles

- Vidéos et données brutes hors git (`data/raw/` ignoré).
- Aucun commit / push sans demande explicite.
- Aucune métrique codée en dur dans un livrable : tout passe par `metrics.json`.
- Aucune prédiction publiée hors de l'emprise réellement échantillonnée.

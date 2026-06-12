# Roadmap — état du projet et prochaines étapes

*Mis à jour : 12 juin 2026*

**Ordre d'exécution des notebooks Hanoï : 07 (terrain) → 08 (prédiction) → 09 (export GAMA)**,
à relancer dans cet ordre après chaque export Kobo placé dans `data/raw/hanoi/`.

## Où on en est

| Bloc | État |
|---|---|
| Reproduction pipeline Sunbird (notebooks 01-05) | **Terminé** — tout tourne, stats conformes au papier |
| Modèle surrogate v1, config `small` (notebook 06) | **Terminé** — MAE 8.2 dB, R² 0.25 sur 955 points |
| Modèle surrogate v2, config `large` (59K points) | **Terminé** — MAE 5.17 dB, RMSE 7.12, **R² 0.639** — checkpoint 1 validé |
| Protocole terrain (ODK Collect + KoboToolbox) | **Prêt** — formulaire déployé, 3 collecteurs (Laurian/Lucas/Quang) |
| Calibration des téléphones | **Terminé** — cross-calibration Decibel X sur S24+ |
| Session pilote (21 pts, Ocean Park, 10-11 juin) | **Terminé** — chaîne Kobo → 07 → 08 → 09 validée de bout en bout |
| Collecte terrain complète | En cours — objectif 300-500 samples, multi-sites, AVEC points calmes |
| Transfer learning Hanoï (notebook 08) | **Premier résultat (21 pts)** : MAE 6.6 dB après offset (+21.0 dB) — checkpoint 2 provisoirement validé |
| GAMA | Squelette seulement (`gama/hanoi_noise.gaml`) |
| Manuscrit | Pas commencé |

## Pourquoi le passage en `large`

Courbe d'apprentissage mesurée sur le config `small` — le R² monte régulièrement
et ne plafonne pas, le modèle est limité par les données, pas par les features :

```
train= 100   R² = -0.09   MAE = 10.1 dB
train= 200   R² = -0.05   MAE =  9.8 dB
train= 400   R² = +0.10   MAE =  8.8 dB
train= 600   R² = +0.16   MAE =  8.4 dB
train= 764   R² = +0.20   MAE =  8.2 dB
```

Extrapolation pour 48K points d'entraînement : R² ~0.40-0.55, MAE ~5.5-6.5 dB.

**Résultat réel du run `large` (11 juin 2026, 59 366 points, train 47 492 / test 11 874) :**

```
MAE  : 5.17 dB
RMSE : 7.12 dB
R²   : 0.639
```

→ Au-dessus des critères (R² > 0.4, MAE < 6) : **le surrogate model est solide,
checkpoint 1 validé.** Modèle : `outputs/models/surrogate_lgbm_large.pkl`.
Reproduction : `python3 scripts/train_large.py` (~5 min, caches OSM inclus).

## Validation croisée sur Barcelone (Xarxa de Soroll, 197 capteurs, 4 mois)

Barcelone = **banc d'essai diagnostique uniquement** (jamais en entraînement :
capteurs fixes classe 1 / LAeq 4 mois ≠ smartphones / niveaux instantanés).
Comparable au pipeline de référence des profs validé sur Barcelone (R²=0.61, r=0.66).

| Expérience | MAE | R² | r |
|---|---|---|---|
| C. Pipeline entraîné directement sur Barcelone | 3.95 dB | 0.29 | 0.59 |
| A/B. Transfert zéro-shot Uganda→Barcelone (v1 comptage) | 8.7 dB après offset | <0 | ~0 |
| A/B. Transfert zéro-shot v2 (ratio surface bâtie) | 7.5 dB après offset | <0 | ~0 |

**Enseignements :**
1. La feature v1 "nombre de bâtiments/km²" n'est pas comparable entre villes
   (OSM Kampala = petits bâtiments individuels, Barcelone = îlots entiers).
   → **v2 : `built_area_ratio`** (surface bâtie / surface du disque, invariant).
   Le biais de transfert passe de +19.3 à +8.6 dB, sans rien perdre côté Uganda
   (v2 : MAE 5.11, R² 0.645, r 0.803 — légèrement meilleur que v1).
2. Le **classement spatial ne se transfère pas zéro-shot** entre villes (r≈0),
   en partie pour des raisons de fond (mismatch instruments/grandeurs/échantillonnage
   spécifique à Barcelone), en partie domain shift. Limitation documentée pour le papier.
3. **Conséquence pour Hanoï** : le transfert a structurellement de meilleures chances
   (OSM Hanoï = petits bâtiments comme Kampala ; collecte smartphone en marche comme
   Sunbird = même instrument et même grandeur), mais il n'est plus présumé acquis.
   Le protocole du notebook 08 garde un double filet : calibration offset ET
   fine-tuning sur nos mesures (la meilleure méthode gagne, mesurée sur un test set
   tenu) — et en dernier recours, entraînement direct sur nos ~500 points.
   **La session pilote (checkpoint 2) est décisive.**

Modèle courant pour Hanoï : `outputs/models/surrogate_lgbm_v2_uganda.pkl`
(features v2, utilisé par le notebook 08). Reproduction : `python3 scripts/train_v2_invariant.py`.

## Après le run `large` — la séquence

### 1. Figer le modèle (5 min)
Le run sauvegarde `outputs/models/surrogate_lgbm_large.pkl`. C'est le modèle
définitif côté Uganda — on n'y retouche plus. La colonne "reproduction Sunbird"
est terminée : pipeline reproduit + modèle entraîné (leur future work).

### 2. Terrain — LE chemin critique
Plus rien côté code ne bloque. Tout dépend des mesures :
- **Session pilote** : 30-50 samples, 1 site, calibration des 3 téléphones au début
- Export Kobo → notebook 07 → notebook 08 → **checkpoint 2** : le MAE du modèle
  sur nos points Hanoï après calibration. < 7 dB = on continue ; > 10 dB = on
  diagnostique avant d'investir 3 semaines
- Si OK → campagne complète 2-3 semaines (~500 samples, protocole `field/PROTOCOL.md`)

### 3. En parallèle de la campagne (celui qui ne collecte pas)
- **GAMA** : installer, tuto officiel "load GIS data", puis étoffer
  `gama/hanoi_noise.gaml` avec les exports du notebook 09. Dernière brique
  technique inconnue — commencer tôt. Viser le palier 1 : carte de bruit
  importée + slider trafic (+10·log10 du facteur), pas la simulation d'agents complète
- **Manuscrit** : squelette Overleaf + sections indépendantes du terrain
  (intro, related work, methods Sunbird)

### 4. Fin de campagne
Notebook 07 complet (analyses QCVN 26:2010, figures Phase 3)
→ notebook 08 final (carte de bruit Hanoï calibrée)
→ notebook 09 (export GAMA)
→ scénarios GAMA
→ résultats + discussion du papier

## Les 3 checkpoints de validation

| # | Question | Statut |
|---|---|---|
| 1 | Le modèle apprend-il sur Sunbird ? | **Validé** — R² 0.639, MAE 5.17 dB sur le config `large` |
| 2 | La chaîne Hanoï tient-elle ? (session pilote → MAE) | À faire — première sortie terrain |
| 3 | L'offset Kampala→Hanoï est-il stable entre sites ? | À faire — en cours de campagne |

Filet de sécurité : même si le modèle spatial décevait, 500 mesures + analyse des
dépassements QCVN + simulation GAMA = un projet complet. Le ML est la cerise, pas le gâteau.

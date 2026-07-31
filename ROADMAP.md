# Roadmap

*Mis à jour : 29 juillet 2026 - intègre la feuille de route officielle du projet*

**État** : 363 mesures / 3 sites · modèle direct **R² 0.45 / r 0.69 / MAE 4.2 dB** (CV spatiale) ·
le transfert inter-villes échoue, l'entraînement direct fonctionne · 147 vidéos comptées par YOLO
(caveat : véhicules garés inclus, motos sous-détectées) · pas d'effet météo robuste ·
survey paper Q1 dans `paper/references/` · rapport 7 pages, carte et analyses à jour ·
repo restructuré, commité et pushé.

**Pipeline après chaque export Kobo** : CSV dans `data/raw/hanoi/` (ancien dans `old/`)
→ `python3 scripts/prepare_field_data.py` → notebooks 07 → 08 → `python3 scripts/build_report.py`
(recopier les scores du notebook 08 dans `MODEL`/`PERSITE` avant).

## Feuille de route officielle

### 1. Gestion de projet & infrastructure
- [x] **Restructuration du git** : architecture claire, commitée et pushée (juillet 2026)

### 2. État de l'art & R&D
- [x] **Ancrage scientifique Q1** : survey paper (`paper/references/Survey_Paper_Noise_Modelling.pdf`)
  + papier Sunbird - pose explicitement la question du benchmark ci-dessous
- [ ] **Benchmark de modèles** : tester nos données sur plusieurs modèles de l'état de l'art,
  **dont les modèles de l'équipe de Barcelone** (LSTM baseline, ST-GNN) - en plus de LightGBM

### 3. Collecte & analyse de données
- [ ] **Audio démolition : minimum 10 h** d'enregistrements de sons de démolition
- [x] **100-200 séquences vidéo+audio horizontales** : 147 vidéos acquises, dans la fourchette
- [x] **Cartographie/EDA** : 5 analyses (heures, jours, sources, QCVN, météo+trafic) + carte
  interactive complète + composition du trafic par site (147 vidéos, cohérent avec le survey paper)

### 4. Rédaction scientifique
- [ ] **Papier de recherche complet** (→ `paper/`) : méthodologie + illustrations, architecture
  du modèle, protocole d'entraînement, tests, résultats
  (note : positionner notre métrique dB face à Leq/L_dn/L_max, cf. survey paper §V)

## Ce qu'il reste concrètement (5 chantiers) - priorisé 31 juillet 2026

1. 🔴 **PRIORITÉ - Diaporama de présentation** (deadline proche)
2. 🟡 **GAMA** (en cours) - Phase 4 couverte : 3 zones importées, données terrain injectées, trafic et
   chantiers calibrés sur les mesures, scénarios (heure, volume de trafic, horaires de chantier,
   zone 30, piétonnisation), validation simulé vs mesuré (`scripts/validate_simulation.py`,
   page 7 du rapport). Émissions calibrées sur nos données (`scripts/calibrate_emissions.py`) :
   les chantiers le sont (+2 dB à 56 m), les véhicules NON - non identifiables, ils sont donc
   visuels et n'ajoutent pas de bruit. Reste possible : agents piétons (exposition individuelle),
   filtre de mouvement sur le comptage vidéo.
3. ⏸️ **Manuscrit** - repoussé à la fin
4. ⏸️ **Benchmark de modèles** (LightGBM vs autres, dont LSTM/ST-GNN Barcelone) - mis de côté,
   statut à reclarifier avec le prof (à qui revient cette tâche ?)
5. ⏸️ **Audio démolition** (10 h à enregistrer) - skip pour l'instant

## Reliquat technique (à caser dans les chantiers ci-dessus)

- Filtre de mouvement dans `count_vehicles.py` (exclure véhicules garés) → benchmark (1) + papier (4)
- Propagation dB vs distance + lecture santé/OMS → candidat pour approfondir l'EDA (3) ou le papier (4)
- Téléphone posé 1 journée → séries temporelles Hanoï, utile au benchmark LSTM (1) et à l'audio (2)

## Règles

- Vidéos et données brutes hors git (`data/raw/` ignoré).
- Aucun commit / push sans demande explicite.

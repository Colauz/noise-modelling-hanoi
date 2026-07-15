# Roadmap

*Mis à jour : 15 juillet 2026 — intègre la feuille de route officielle du projet*

**État** : 323 mesures / 3 sites · modèle direct **R² 0.45 / r 0.68 / MAE 4.4 dB** (CV spatiale) ·
le transfert inter-villes échoue, l'entraînement direct fonctionne · 107 vidéos comptées par YOLO
(caveat : véhicules garés inclus, motos sous-détectées) · pas d'effet météo robuste ·
rapport 7 pages, carte et analyses à jour.

**Pipeline après chaque export Kobo** : CSV dans `data/raw/hanoi/` (ancien dans `old/`)
→ `python3 scripts/prepare_field_data.py` → notebooks 07 → 08 → `python3 scripts/build_report.py`
(recopier les scores du notebook 08 dans `MODEL`/`PERSITE` avant).

## Feuille de route officielle

### 1. Gestion de projet & infrastructure
- [x] **Restructuration du git** : architecture claire (fait juillet 2026 — en attente de commit)

### 2. État de l'art & R&D
- [ ] **Ancrage scientifique Q1** : biblio de papiers Q1 pour justifier démarche et choix
  techniques (→ `paper/references/`)
- [ ] **Benchmark de modèles** : tester nos données sur plusieurs modèles de l'état de l'art,
  **dont les modèles de l'équipe de Barcelone** (LSTM baseline, ST-GNN) — en plus de LightGBM

### 3. Collecte & analyse de données
- [ ] **Audio démolition : minimum 10 h** d'enregistrements de sons de démolition
- [ ] **100-200 séquences vidéo+audio** pour la computer vision —
  ⚠️ **format HORIZONTAL obligatoire** (vertical inexploitable : champ trop restreint).
  Acquis : ~78 séquences horizontales valides (les TC_*) ; ~29 verticales à refaire
- [ ] **Cartographie/EDA complète** : analyse exploratoire et mapping beaucoup plus détaillés
  des jeux de données actuels

### 4. Rédaction scientifique
- [ ] **Papier de recherche complet** (→ `paper/`) :
  - méthodologie précise + illustrations (schémas, diagrammes de flux)
  - architecture du modèle, protocole d'entraînement, tests, résultats

## Reliquat technique (à caser dans les items ci-dessus)

- Filtre de mouvement dans `count_vehicles.py` (exclure véhicules garés) + feature trafic
  dans le notebook 08 → alimente le benchmark (2) et le papier (4)
- GAMA palier 1 (`gama/PLAN.md`) — si toujours au scope
- Propagation dB vs distance + lecture santé/OMS → candidat pour l'EDA détaillée (3)
- Téléphone posé 1 journée → séries temporelles pour le benchmark LSTM (2)

## Règles

- Vidéos et données brutes hors git (`data/raw/` ignoré).
- Aucun commit / push sans demande explicite.

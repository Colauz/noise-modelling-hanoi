# Field - protocole & formulaires

## Fichiers

- `hanoi_noise_form_v2.xlsx` - formulaire principal (XLSForm Kobo) : dB, GPS, catégorie,
  distance route/source, orientation téléphone, comptages véhicules, vidéo, chantier audible
- `hanoi_construction_form.xlsx` - registre des chantiers (1 fiche par site : position GPS,
  type construction/démolition/rénovation, niveau d'activité, photo)

## Setup (une fois)

1. **Kobo** : compte sur kobotoolbox.org (serveur Global) → New → Upload XLSForm → Deploy
2. **Téléphones** : ODK Collect (Play Store), serveur `https://kc.kobotoolbox.org` +
   identifiants Kobo → Get Blank Form
3. **Sonomètre** : Decibel X, mêmes réglages partout - pondération **A**, réponse **SLOW**, trim 0.0

## Calibration croisée (10 min, début de première session, les 3 téléphones ensemble)

1. Téléphones côte à côte face à la rue, mesurer 1 min, relever les AVG au même moment
2. Refaire 30 s pour vérifier la stabilité (~1 dB près)
3. Téléphone du milieu = référence ; offset = référence − valeur du téléphone
4. Entrer chaque offset dans Decibel X > settings > Trim → les 3 téléphones affichent pareil
5. Noter les valeurs + date (et reporter dans `CALIBRATION_OFFSET` de
   `scripts/prepare_field_data.py` si un trim n'a pas été appliqué sur le terrain)

## Routine par point (~45 s)

1. ODK Collect → Fill Blank Form → Hanoi Urban Noise Survey
2. Site + collecteur ; GPS : attendre précision < 10 m
3. Audio ≥ 10 s dans le form, immobile et silencieux ; lire le dB (AVG) sur Decibel X pendant
4. Distances route/source, comptages si possible ; vidéo trafic pendant les rush hours
   (nom horodaté = appariement automatique à la mesure)
5. Fenêtre de capture : 05h-23h, accent sur 08-10h et 16-18h ; varier les distances à la route

## Chantiers

Une fiche par site dans le form chantiers + 2-3 mesures normales en s'éloignant
(le rayon dB-distance est calculé au traitement par croisement GPS).

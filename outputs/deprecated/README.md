# Artefacts périmés — grille « Bach Khoa »

Ces fichiers ont été produits par les anciennes cellules du notebook 08 et par le
notebook 09. **Ils ne doivent pas être diffusés.**

## Pourquoi ils ont été retirés

Ils couvrent un disque de 1 500 m autour de **Bach Khoa** (lat 20.992-21.019,
lon 105.829-105.858) — un quartier où **aucune mesure de terrain n'a été prise**. Le modèle
qui les a produits est entraîné sur Ocean Park, Hoan Kiem et Vinh Tuy, et son
leave-one-site-out est négatif sur deux sites sur trois : il ne généralise pas à une
typologie urbaine qu'il n'a pas vue. Publier une carte de bruit sur Bach Khoa revenait donc
à extrapoler hors du domaine d'applicabilité du modèle.

| Fichier | Remplacé par |
|---|---|
| `hanoi_heatmap.html` | à régénérer sur l'emprise mesurée (voir ci-dessous) |
| `hanoi_noise_map.geojson` | `outputs/hanoi/hanoi_noise_map.csv` (3 zones × 17 heures) |
| `hanoi_osm.png` | — (figure de la zone Bach Khoa, sans objet) |

## Ce qui les remplace

`scripts/export_gama_zones.py` produit la carte **sur l'emprise réellement échantillonnée** :
les 3 sites de mesure + 400 m de marge, grille de 40 m, une colonne par heure (`h5`…`h21`).

```bash
python3 scripts/export_gama_zones.py
```

Sorties : `outputs/hanoi/hanoi_noise_map.csv` (5 587 cellules × 17 heures),
`outputs/gama_inputs/noise_map.csv` (format plat pour GAMA, heure de référence 17 h),
`outputs/gama_inputs/{zone}_noise.shp`.

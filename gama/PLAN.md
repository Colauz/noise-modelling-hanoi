# Plan GAMA — simulation de scénarios de bruit

*Entrées : `outputs/maps/gama_inputs/` (roads.shp, buildings.shp, noise_map.csv),
produits par le notebook 09 après chaque mise à jour de la carte.*

## Les 3 paliers

### Palier 1 — carte interactive + slider trafic (NOTRE OBJECTIF)
1. Charger routes + bâtiments (tutoriel officiel GAMA "load GIS data")
2. Afficher la grille de bruit colorée depuis `noise_map.csv`
3. Paramètre interactif `facteur_trafic` (×0.2 à ×3) :
   `dB' = dB + 10·log10(facteur)` — doubler le trafic = +3 dB
4. Indicateur live : % de la zone au-dessus de 70 dB (QCVN 26:2010 jour)

### Palier 2 — scénarios pour le papier
- Piétonnisation : facteur ×0.2 sur des rues sélectionnées → quelle zone repasse au vert
- Heure de pointe : ×1.5 partout → surface exposée au-dessus de la norme
- 2-3 scénarios suffisent pour la section résultats de la simulation

### Palier 3 — agents véhicules individuels (HORS SCOPE, voir ci-dessous)

## Pourquoi on ne fait PAS la simulation complète avec motos/véhicules individuels

1. **Pas de données pour la calibrer.** Une simulation à agents demande les flux
   réels par rue (véhicules/heure), la composition du parc (motos vs voitures vs
   camions), les vitesses, les cycles de feux. On n'a rien de tout ça pour Hanoï.
   Chaque moto simulée aurait une puissance acoustique inventée — la simulation
   aurait l'air précise mais serait construite sur des paramètres devinés.

2. **Pas de données pour la valider.** Nos ~500 mesures valident une carte de
   bruit statique (niveau moyen par endroit). Elles ne peuvent pas valider une
   dynamique microscopique (le passage d'une moto donnée à un instant donné).
   Une simulation invérifiable n'apporte rien de scientifique.

3. **Le premier ordre est déjà capturé.** Le bruit routier agrégé suit
   ~10·log10(flux) : l'effet dominant d'un changement de trafic est ce facteur
   logarithmique, que le palier 1 applique exactement. Les agents individuels
   ajoutent de la variance, pas de la justesse — sauf à vouloir étudier des
   événements isolés (klaxons, accélérations), ce qui n'est pas notre question.

4. **Coût/bénéfice.** Le palier 1, c'est quelques jours avec le tutoriel GAMA.
   Une simulation à agents calibrée, c'est plusieurs semaines plus une campagne
   de comptage de trafic — pour une question de recherche qu'on ne pose pas.

5. **Notre crédibilité vient des mesures.** La force du projet, c'est la chaîne
   données réelles → modèle ML validé → carte calibrée. Y greffer une couche
   d'agents non calibrés affaiblirait l'ensemble au lieu de l'enrichir.

→ À mentionner dans le papier comme **future work** : couplage avec des données
de comptage de trafic (capteurs, vidéo) pour passer à une simulation à agents
calibrée.

## Reste à faire
- [ ] Installer GAMA Platform (https://gama-platform.org)
- [ ] Tutoriel "load GIS data" avec nos shapefiles
- [ ] Étoffer `hanoi_noise.gaml` : grille colorée + slider (palier 1)
- [ ] Scénarios palier 2 + captures pour le papier

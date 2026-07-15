# Plan GAMA — simulation de scénarios de bruit

*Entrées : `outputs/gama_inputs/` (roads.shp, buildings.shp, noise_map.csv),
produits par le notebook 09 après chaque mise à jour de la carte.*

## L'idée directrice : agents récepteurs, pas agents émetteurs

GAMA est une plateforme agent-based — mais il y a deux façons d'y mettre des
agents, et elles n'ont pas du tout le même coût en données :

- **Agents émetteurs (motos, voitures)** : il faut les flux réels par rue, la
  composition du parc, les vitesses, les feux. On n'a rien de tout ça pour
  Hanoï → simulation non calibrable et non vérifiable. **Écarté** (détails plus bas).
- **Agents récepteurs (habitants, piétons)** : des agents qui se déplacent dans
  la zone (domicile → école → marché) et accumulent leur **dose de bruit**
  en traversant notre carte. L'entrée de la simulation est notre carte ML
  validée par nos mesures — rien d'inventé. **C'est notre couche agent.**

Résultat : une vraie simulation agent-based (agents mobiles, comportements,
indicateur émergent au niveau population), calibrée par nos données, qui produit
ce que la carte seule ne donne pas : l'**exposition des gens**.

## Les paliers

### Palier 1 — carte interactive + slider trafic
1. Charger routes + bâtiments (tutoriel officiel GAMA "load GIS data")
2. Afficher la grille de bruit colorée depuis `noise_map.csv`
3. Paramètre interactif `facteur_trafic` (×0.2 à ×3) :
   `dB' = dB + 10·log10(facteur)` — doubler le trafic = +3 dB
4. Indicateur live : % de la zone au-dessus de 70 dB (QCVN 26:2010 jour)

### Palier 2 — agents piétons exposés (la couche agent-based)
- N agents avec des trajets quotidiens simples sur le réseau routier
  (domicile → destination → retour, horaires variés)
- Chaque agent accumule sa dose : niveau de la cellule traversée × temps passé
- Indicateurs : distribution des doses quotidiennes, % d'agents au-dessus des
  recommandations OMS, exposition moyenne par type de trajet

### Palier 3 — scénarios pour le papier (croise 1 et 2)
- Piétonnisation : facteur ×0.2 sur des rues sélectionnées → quelle zone
  repasse au vert ET de combien baisse l'exposition des agents
- Heure de pointe ×1.5 → surface au-dessus de la norme + dose des piétons
- 2-3 scénarios suffisent pour la section résultats de la simulation

## Pourquoi on ne simule PAS les véhicules individuels (agents émetteurs)

1. **Pas de données pour calibrer.** Flux par rue, parts motos/voitures/camions,
   vitesses, cycles de feux : on n'a rien. Chaque moto simulée aurait une
   puissance acoustique inventée — précision apparente, paramètres devinés.

2. **Pas de données pour valider.** Nos ~500 mesures valident une carte de
   niveaux moyens, pas une dynamique microscopique du trafic. Une simulation
   invérifiable n'apporte rien de scientifique.

3. **Le premier ordre est déjà capturé.** Le bruit agrégé d'un flux suit
   ~10·log10(flux) : l'effet dominant d'un changement de trafic est ce facteur,
   que le palier 1 applique exactement. Les agents émetteurs ajoutent de la
   variance instantanée (passages, klaxons) dont notre question n'a pas besoin.

4. **Coût/bénéfice.** Palier 1+2 : quelques jours avec les tutoriels GAMA.
   Trafic à agents calibré : plusieurs semaines + une campagne de comptage.

5. **Notre crédibilité vient des mesures.** La chaîne données réelles → modèle
   ML validé → carte calibrée → exposition simulée reste vérifiable de bout en
   bout. Une couche trafic non calibrée casserait ce fil.

→ À mentionner dans le papier comme **future work** : couplage avec des données
de comptage de trafic (capteurs, vidéo) pour ajouter les agents émetteurs.

## Reste à faire
- [ ] Installer GAMA Platform (https://gama-platform.org)
- [ ] Tutoriel "load GIS data" avec nos shapefiles
- [ ] Étoffer `hanoi_noise.gaml` : grille colorée + slider (palier 1)
- [ ] Agents piétons + dose d'exposition (palier 2)
- [ ] Scénarios palier 3 + captures pour le papier

# Ancrage sur la littérature instrumentée

_Généré par `scripts/literature_anchoring.py`. Aucune correction n'est appliquée aux mesures : ce document borne l'incertitude absolue, il ne la corrige pas._

## Nos strates

| Strate | n | Médiane | Moyenne | p90 | Écart-type |
|---|---|---|---|---|---|
| `all` | 363 | 68.0 | 66.7 | 75.0 | 7.1 |
| `roadside_day` | 273 | 69.5 | 68.7 | 76.0 | 6.0 |
| `roadside_day_major` | 141 | 69.3 | 69.0 | 75.1 | 4.8 |
| `night_all` | 10 | 69.0 | 66.0 | 72.2 | 7.2 |

## Points d'ancrage publiés

| Source | Ville | Instrument | Grandeur | Valeur | Notre strate | Écart brut | Écart corrigé | Statut |
|---|---|---|---|---|---|---|---|---|
| Gelb & Apparicio 2019, Applied Acoustics 148:332-343 | Ho Chi Minh City | dosimètres personnels + GPS | LAeq,1min | 78.8 | `roadside_day` (n=273) | +9.3 | +7.3 | verified |
| Phan et al. 2010, Applied Acoustics 71(5):479-485 | Hanoï | RION NL-21 / NL-22 (sonomètres), 24 h continu | Lden | 76.5 | `roadside_day` (n=273) | +7.0 | +3.0 | to_check |
| Phan et al. 2010, Applied Acoustics 71(5):479-485 | Hanoï | RION NL-21 / NL-22, 24 h continu | Lnight (le plus bas des 7 sites) | 66.0 | `night_all` (n=10) | -3.0 | -3.0 | to_check |
| Institute of Occupational Health and Environment, 12 grands axes de Hanoï (rapporté par la presse vietnamienne) | Hanoï | non documenté | moyenne diurne dBA | 77.9 | `roadside_day_major` (n=141) | +8.6 | +7.6 | grey |

_« Écart corrigé » = écart brut moins la différence attendue du seul fait de la grandeur (`metric_gap_dB`). Il approche le biais instrumental résiduel._

## Conclusion

Biais absolu plausible de nos smartphones : **entre +3.0 et +7.3 dB** (sources revues par les pairs, hors nuit).

Ce que cela autorise et interdit :

- **Autorisé** : comparer nos lieux entre eux, nos heures entre elles, et discuter des contrastes spatiaux et temporels. Le biais est commun aux trois appareils et s'annule dans une différence.
- **Interdit** : annoncer un taux de dépassement réglementaire comme un fait. Le seuil QCVN diurne (70 dBA) tombe au milieu de notre distribution : un biais de quelques dB déplace fortement le pourcentage de dépassement.

### Notes par source

- **Gelb & Apparicio 2019, Applied Acoustics 148:332-343** — Cyclistes DANS le flux (~1-2 m des véhicules) : plus exposés qu'un observateur en bord de trottoir. L'écart attendu est positif.
- **Phan et al. 2010, Applied Acoustics 71(5):479-485** — SEULE campagne publiée à Hanoï avec instrumentation professionnelle. Lden = moyenne annuelle avec pénalités +5 dB soir / +10 dB nuit : mécaniquement au-dessus d'un niveau diurne. Valeur à confirmer sur le PDF.
- **Phan et al. 2010, Applied Acoustics 71(5):479-485** — Notre couverture nocturne est trop faible (n≈10) pour que cet ancrage soit informatif : il est reporté pour mémoire.
- **Institute of Occupational Health and Environment, 12 grands axes de Hanoï (rapporté par la presse vietnamienne)** — Littérature grise : source secondaire, protocole non documenté. À utiliser comme repère contextuel, jamais comme référence primaire.

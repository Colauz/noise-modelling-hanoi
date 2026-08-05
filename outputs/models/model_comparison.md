# Comparaison des modèles — carte de bruit Hanoï

Généré par `scripts/evaluate_models.py`. n = 363 mesures, 17 blocs spatiaux de 600 m.

Tous les modèles sont évalués sur **exactement les mêmes découpages**. IC 95 % par bootstrap par bloc.

## Block-CV 600 m

| Modèle | R² | IC 95 % | MAE (dB) | IC 95 % | r |
|---|---|---|---|---|---|
| Moyenne globale | -0.019 | [-0.10, -0.00] | 5.99 | [5.20, 6.66] | -0.18 |
| Moyenne par site | -0.027 | [-0.21, 0.06] | 6.05 | [5.27, 6.76] | 0.07 |
| Moyenne par (site, heure) | -0.008 | [-0.18, 0.29] | 5.50 | [4.21, 6.48] | 0.38 |
| Régression sur log(distance route) | 0.221 | [0.09, 0.29] | 5.17 | [4.39, 5.81] | 0.47 |
| Distance inverse (k=8, p=2) | 0.117 | [-0.14, 0.31] | 5.25 | [4.34, 6.17] | 0.44 |
| LightGBM — temps seul (ablation) | 0.230 | [0.02, 0.45] | 4.87 | [3.75, 5.80] | 0.51 |
| LightGBM — morphologie seule (ablation) | 0.153 | [-0.09, 0.29] | 5.15 | [4.76, 5.57] | 0.48 |
| LightGBM — morphologie + temps (modèle du projet) | 0.304 | [0.10, 0.46] | 4.70 | [4.16, 5.14] | 0.58 |

**Apport propre de la morphologie** (LightGBM complet vs table site × heure) : ΔR² = +0.312, ΔMAE = +0.80 dB.

## Buffered LOO 300 m

| Modèle | R² | IC 95 % | MAE (dB) | IC 95 % | r |
|---|---|---|---|---|---|
| Moyenne globale | -0.039 | [-0.12, -0.03] | 6.06 | [5.28, 6.76] | -0.44 |
| Moyenne par site | -0.198 | [-0.55, -0.03] | 6.62 | [5.86, 7.30] | -0.06 |
| Moyenne par (site, heure) | -0.419 | [-0.77, 0.03] | 6.58 | [4.89, 7.94] | 0.06 |
| Régression sur log(distance route) | 0.200 | [0.08, 0.27] | 5.28 | [4.49, 5.91] | 0.45 |
| Distance inverse (k=8, p=2) | -0.203 | [-0.37, 0.02] | 6.44 | [5.28, 7.34] | 0.02 |
| LightGBM — temps seul (ablation) | 0.075 | [-0.13, 0.46] | 5.19 | [3.67, 6.28] | 0.39 |
| LightGBM — morphologie seule (ablation) | 0.041 | [-0.24, 0.23] | 5.63 | [4.99, 6.21] | 0.41 |
| LightGBM — morphologie + temps (modèle du projet) | 0.137 | [-0.10, 0.33] | 5.26 | [4.56, 5.89] | 0.47 |

**Apport propre de la morphologie** (LightGBM complet vs table site × heure) : ΔR² = +0.556, ΔMAE = +1.32 dB.

## Leave-one-site-out

| Modèle | R² | IC 95 % | MAE (dB) | IC 95 % | r |
|---|---|---|---|---|---|
| Moyenne globale | -0.058 | [-0.15, -0.03] | 6.05 | [5.29, 6.72] | -0.21 |
| Moyenne par site | -0.058 | [-0.15, -0.03] | 6.05 | [5.29, 6.72] | -0.21 |
| Moyenne par (site, heure) | -0.058 | [-0.15, -0.03] | 6.05 | [5.29, 6.72] | -0.21 |
| Régression sur log(distance route) | 0.189 | [0.06, 0.27] | 5.26 | [4.47, 5.92] | 0.44 |
| Distance inverse (k=8, p=2) | -0.140 | [-0.34, 0.05] | 6.25 | [5.00, 7.30] | 0.18 |
| LightGBM — temps seul (ablation) | -0.139 | [-0.29, 0.08] | 5.82 | [4.54, 6.75] | 0.21 |
| LightGBM — morphologie seule (ablation) | 0.007 | [-0.36, 0.17] | 5.75 | [5.45, 6.20] | 0.35 |
| LightGBM — morphologie + temps (modèle du projet) | 0.029 | [-0.35, 0.21] | 5.68 | [5.18, 6.36] | 0.33 |

**Apport propre de la morphologie** (LightGBM complet vs table site × heure) : ΔR² = +0.087, ΔMAE = +0.37 dB.

## Leave-one-site-out, par site (LightGBM complet)

| Site | n | R² | MAE (dB) | r |
|---|---|---|---|---|
| Ocean Park | 184 | 0.19 | 5.80 | 0.51 |
| Hoan Kiem lake | 99 | -0.42 | 5.30 | 0.41 |
| Vinh Tuy area | 80 | -0.58 | 5.85 | 0.14 |

_Un R² négatif signifie : moins bon que de prédire partout la moyenne globale._

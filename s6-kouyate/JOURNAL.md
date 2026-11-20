# JOURNAL - Séance 6

Écrit le 20/11/2026 15:05, avant le premier entraînement.

## Tableau de décisions

| Décision | Ma valeur |
|---|---|
| Métrique d'arbitrage | PR-AUC sur le test (découpage par patient) |
| Écart minimal pour déclarer une approche meilleure | supérieur à la plus grande variation d'une même approche entre ses deux graines (42 et 7) |
| Critère de départage si l'écart est sous le bruit | duree_entrainement_s (le plus court gagne), sinon l'approche de référence |
| Nom du validateur au registre | Issa Kouyaté |

## Question 0.1

Un écart est réel s'il dépasse ce que change une même approche quand on change seulement la graine, et s'il se retrouve avec les deux graines.
Sinon c'est du bruit : on ne déclare pas de gagnant sur la qualité et on tranche sur le coût.

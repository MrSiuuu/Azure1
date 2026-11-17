# SURVEILLANCE — TP5 « Optimiser et surveiller » (YNOV)

Issa Kouyaté — séance du 17/11/2026 — dossier `s5-kouyate/`

Réglages décidés avant toute mesure de dérive (voir `JOURNAL.md`) : statistique **PSI**, seuil d'alerte **0,25**, seuil de surveillance **0,10**, fenêtre glissante de **200 inférences**, covariable prioritaire `tbp_tile_type`, levier `eclairage`. Ils n'ont pas été modifiés.

## Mesure 7 — La référence

Fichier : `reference_covariables.json` (jeu d'entraînement du manifeste). Nombre de vignettes de la référence : **16 158**.

| Covariable | Modalités et proportions | Taux d'absence |
|---|---|---|
| `tbp_tile_type` | `3D: white` 53,4 % ; `3D: XP` 46,6 % | 0 % |
| `age_tranche` (les trois plus fréquentes) | 60-69 : 31,4 % ; 50-59 : 24,8 % ; 70-79 : 17,9 % | 0,67 % |
| `anatom_site_general` (les deux plus fréquentes) | posterior torso : 30,9 % ; lower extremity : 26,6 % | 1,83 % |
| `sex` | male 71,0 % ; female 29,0 % | 1,37 % |

La tranche 10-19 ans ne pèse que 0,025 % (≈ 4 vignettes) : elle est très instable dans un PSI calculé sur 200 appels.

**Question 5.1 — Pourquoi la part de `3D: white` de la référence (53,4 %) n'est pas celle de la mesure 20 pour le manifeste (52,80 %) ?**
La référence est le **jeu d'entraînement** du manifeste (16 158 vignettes sur 20 294), pas le manifeste entier : le manifeste contient aussi les jeux de validation et de test, découpés par patient, donc avec des proportions un peu différentes. Le jeu d'entraînement est la bonne référence parce que c'est ce que le modèle a **appris** : la dérive cherchée est l'écart entre le flux servi et ce que le modèle a vu à l'entraînement. Le manifeste entier mélangerait des vignettes que le modèle n'a pas apprises, et l'archive entière (52,73 % de white, 217 477 lésions) contient surtout des négatifs jamais vus à l'entraînement.

**Question 5.2 — PSI à la main sur un flux composé comme le `train-metadata.csv` complet de S2.**
Le `train-metadata.csv` complet (401 059 lésions) contient 28,713 % de `3D: white` et 71,287 % de `3D: XP` (mesure 20 : 28,71 % / 71,29 %). Avec p la proportion de référence et q la proportion observée :

| Modalité | p | q | (q − p) · ln(q / p) |
|---|---|---|---|
| `3D: white` | 0,533853 | 0,28713 | 0,153014 |
| `3D: XP` | 0,466147 | 0,71287 | 0,104808 |
| **PSI** | | | **0,257822** |

0,2578 est **au-dessus** de mon seuil d'alerte de 0,25 (de 3 %) et très au-dessus du seuil de surveillance de 0,10. Ce que cela apprend sur le choix du seuil : un flux qui est simplement la composition réelle de l'archive déclenche déjà l'alerte, donc ma référence (un échantillon : tous les positifs plus 20 000 négatifs) n'est pas représentative de la population servie. Le seuil de 0,25 est conventionnel mais marginal ici : il faut une référence représentative de la population cible, mesurer d'abord le PSI « normal » d'un flux conforme, et fixer le seuil avant, en connaissant cet écart d'échantillonnage.

## Mesure 8 — La dérive provoquée, en local (levier `eclairage`)

800 appels journalisés (400 conformes puis 400 dérivés, tous en `200`), fenêtre 200, alerte à PSI ≥ 0,25. Journal brut : `journal_local.jsonl` ; PSI par fenêtre : `sorties/psi_fenetres_eclairage.csv`.

| Covariable | PSI max en flux conforme | PSI de la dernière fenêtre | Délai d'alerte (inférences après le début de la dérive) |
|---|---|---|---|
| `tbp_tile_type` | 0,0152 | 4,9885 | **86** |
| `age_tranche` | 0,0646 | 0,0731 | aucune alerte |
| `anatom_site_general` | 0,0444 | 0,0174 | aucune alerte |
| `sex` | 0,0134 | 0,0149 | aucune alerte |
| Taux de `a_examiner` : flux conforme / flux dérivé | 40,75 % (163/400) | 41,0 % (164/400) | |

## Mesure 9 — Second levier (`age`)

Mêmes réglages. Journal brut : `journal_local_age.jsonl` ; PSI par fenêtre : `sorties/psi_fenetres_age.csv`.

| Relevé | Valeur |
|---|---|
| Levier | `age` |
| Covariable qui alerte, et délai | `age_tranche` : PSI de la dernière fenêtre 7,0481, alerte **53 appels** après le début de la dérive |
| Autre covariable qui bouge sans alerter, et son PSI | `sex` : PSI 0,1857 (au-dessus du seuil de surveillance 0,10, sous l'alerte 0,25) ; max en flux conforme 0,0134. Les autres : `tbp_tile_type` 0,0666, `anatom_site_general` 0,0392 |
| Taux de `a_examiner` : flux conforme / flux dérivé | 40,75 % / 40,75 % (163/400 dans les deux) |

**Question 5.3 — Un tableau de bord qui ne suivrait que la sortie du modèle aurait-il vu la dérive ?**
Pour l'éclairage, le taux de `a_examiner` passe de 40,75 % à 41,0 % (+0,25 point) : un tableau de bord qui ne suit que la sortie n'aurait **rien vu**, alors que le PSI sur l'entrée a alerté après 86 appels. Pour le second levier (l'âge), le taux est strictement identique (40,75 % dans les deux phases) : la sortie est totalement aveugle, alors que le PSI de `age_tranche` alerte après 53 appels. Le service répond toujours `200` avec des probabilités d'apparence normale. Conclusion : on surveille les **entrées** parce qu'une dérive d'entrée précède et n'est pas toujours visible en sortie, et la **sortie** parce que c'est elle qui touche le patient et qu'une dérive de sortie signale ce que les entrées surveillées ne couvrent pas.

**Question 5.4 — Une covariable a-t-elle dépassé le seuil de surveillance en flux conforme ?**
En local, aucune (la plus haute est `age_tranche`, 0,0646). Sur Azure (mesure 10), **`anatom_site_general`** atteint 0,1072 en flux conforme, au-dessus du seuil de surveillance de 0,10 mais loin de l'alerte, avant de retomber à 0,0259. C'est du **bruit**, pas une dérive : aucune dérive n'était provoquée à ce moment. Le lien avec le nombre de modalités et la taille de fenêtre : le PSI d'un échantillon purement aléatoire a une valeur attendue de l'ordre de (k − 1)/n, qui croît avec le nombre de modalités k et décroît avec la taille de la fenêtre n. `anatom_site_general` a 5 modalités, dont une rare (`head/neck`, ≈ 3 %, soit environ 6 appels attendus sur 200, très variable) ; `age_tranche` en a 8. Sur 200 inférences, le bruit des modalités rares suffit à franchir un seuil de 0,10.

**Question 5.5 — Avec une fenêtre deux fois plus petite ?**
Le délai d'alerte serait environ **divisé par deux**, et les fausses alertes **augmenteraient**. Compromis : une petite fenêtre détecte plus vite mais crie plus souvent à tort, parce que le bruit d'échantillonnage du PSI croît quand la fenêtre diminue ; une grande fenêtre est plus stable mais plus lente. Délai théorique pour l'éclairage : si une fraction f de la fenêtre est 100 % `3D: XP` et le reste suit la référence, le PSI vaut ≈ 0,243 pour f = 0,45 et ≈ 0,255 pour f = 0,46 ; le seuil de 0,25 est donc franchi vers **f ≈ 0,455**, soit ≈ 91 appels pour une fenêtre de 200 (≈ 46 pour une fenêtre de 100). Observé : 86 appels en local et 94 sur Azure, cohérent à l'écart d'échantillonnage près.

## Mesure 10 — La surveillance en ligne (Azure)

Groupe `rg-dermascan-s5-ik42` (germanywestcentral), Web App en B1 avec l'`IMAGE_DIGEST` renseigné (`sha256:ac1755a5…f7cc`), espace Log Analytics `law-dermascan-s5-ik42` (rétention 30 jours, paramètre de diagnostic `diag-dermascan-s5` sur `AppServiceConsoleLogs`). Rejeu à 1 appel par seconde : 600 appels conformes (début 14:32:11 UTC) puis 600 appels dérivés (début **14:42:34 UTC**, fin 14:52:56 UTC). Journal brut : `journal_azure.jsonl`.

| Relevé | Valeur |
|---|---|
| Délai entre un appel et son apparition dans Log Analytics | ≈ **3 min** (appel de test à 14:28:14 UTC, 195 s mesurés) |
| Nombre de lignes exportées / nombre d'appels envoyés | **1 201 / 1 201** (1 200 appels de rejeu + 1 appel de test) ; `derive.py` en journalise 1 200 |
| PSI de l'éclairage par fenêtre de 5 min, phase conforme (min – max) | **0,0003 – 0,0368** (fenêtres 14:30 et 14:35 UTC). La fenêtre 14:25, qui ne contient que l'appel de test, donne PSI ≈ 4,2 : artefact, exclue |
| Première fenêtre de 5 min au-dessus du seuil d'alerte, et heure de début de dérive | fenêtre **14:40–14:45 UTC** (PSI 0,3479, 279 appels) ; dérive commencée à **14:42:34 UTC** (fenêtre mixte). Les suivantes : 14:45 → 4,9885 ; 14:50 → 4,9885 |
| Délai d'alerte de `derive.py` sur le journal Azure | **94 inférences** (86 en local) |
| Capture du tableau de bord (requêtes 2, 3 et 4) | `captures/10_tableau_de_bord.png` |

Autres résultats de `derive.py` sur `journal_azure.jsonl` (fenêtre 200, alerte 0,25) : taux de `a_examiner` 40,0 % (conforme) / 40,83 % (dérivé) ; `age_tranche` max conforme 0,0646, dernière fenêtre 0,1638 ; `anatom_site_general` max conforme 0,1072, dernière fenêtre 0,0259 ; `sex` max conforme 0,0134, dernière fenêtre 0,0036 ; aucune alerte hors `tbp_tile_type`.

Requête 3 de `requetes.kql` complétée avec mes valeurs : référence `3D: white` = 0,533853 et `3D: XP` = 0,466147 (mesure 7), seuil d'alerte 0,25. Elle est épinglée au tableau de bord partagé avec les requêtes 2 et 4.

**Question 5.6 — Délai entre le premier patient « dérivé » et le moment où un humain voit l'alerte.**
Au moins quatre termes, pour un début de dérive à 14:42:34 UTC :
1. **Accumulation de patients dérivés dans la fenêtre** : le PSI ne franchit 0,25 qu'à ≈ 45 % de la fenêtre, soit 94 inférences mesurées (≈ 94 s à 1 appel/s).
2. **Pas de 5 minutes du tableau de bord** : le calcul se fait par fenêtre de temps ; celle de 14:40–14:45 ne se ferme qu'à 14:45:00, soit jusqu'à 5 min d'attente selon le moment du début de la dérive (ici 2 min 26 s après le début).
3. **Ingestion dans Log Analytics** : ≈ 3 min mesurées entre l'appel et sa visibilité.
4. **Rafraîchissement et lecture par un humain** : il faut que la personne actualise (ou que l'actualisation automatique soit réglée), puis regarde.

Estimation : alerte visible vers 14:48 UTC au plus tôt, soit environ **5 à 6 minutes** après le début de la dérive, contre ≈ 1 min 30 s pour `derive.py` en continu (estimation, je n'ai pas chronométré le moment de lecture sur le tableau de bord). Sans toucher au seuil, je peux réduire le **pas de la fenêtre** (de 5 min à 1 min) et le **rafraîchissement** (actualisation automatique, ou règle d'alerte planifiée). L'ingestion n'est pas réglable.

## Mesure 12 — Fin de séance

| Contrôle | Mon observation |
|---|---|
| Nombre et types de ressources du groupe avant destruction | **4** : plan App Service B1 (`Microsoft.Web/serverFarms`), Web App (`Microsoft.Web/sites`), espace Log Analytics (`Microsoft.OperationalInsights/workspaces`), tableau de bord partagé (`Microsoft.Portal/dashboards`) |
| `az group exists` sur le groupe de séance | **false** (suppression terminée en ≈ 1 min) |
| Le groupe du registre est-il toujours là ? Tags du dépôt de l'image | **oui** (`true`) ; tags : `1.0.0`, `2.0.0` |
| Le tableau de bord partagé survit-il à la destruction du groupe ? Ses graphiques affichent-ils encore quelque chose ? | Mon tableau de bord partagé, créé **par erreur dans le groupe de séance**, a disparu avec lui. J'ai observé un **clone** (`dermascan-s5-hors-groupe`, privé, placé hors du groupe de séance) : il **survit**, mais après « Actualiser » chaque tuile affiche **« Introuvable »** (espace de travail supprimé, ID de ressource non disponible) : graphiques vides, il ne reste que les requêtes. Capture : `captures/15_tableau_de_bord_apres_destruction.png` |
| Crédit restant, et écart avec la séance 4 | **83 € sur 90 €** (coûts de novembre : 2,61 €, partiels : les coûts du jour peuvent ne pas être remontés), expiration 06/10/2027 ; en S4 : 86 € sur 88 € . Écart sur le restant : −3 € ; le total est passé de 88 à 90 €, à interpréter avec prudence |

Détails de la destruction : attribution `AcrPull` supprimée, espace Log Analytics supprimé avec `--force`, groupe `rg-dermascan-s5-ik42` supprimé ; conteneur local de la séance supprimé. Fichiers bruts conservés : `journal_azure.jsonl` (1 201 lignes), `journal_local.jsonl` (804 lignes).

**Question 6.1 — Que montre le tableau de bord après la destruction de l'espace Log Analytics, et que garder pour que la surveillance survive aux séances ?**
Il montre des tuiles vides (« Introuvable ») : le tableau de bord ne stocke que des requêtes, pas de données ; quand l'espace est supprimé, ces requêtes n'ont plus rien à interroger. Pour que la surveillance survive aux séances, il faut garder : (1) les **requêtes** dans le dépôt (`requetes.kql`) et la définition du tableau de bord exportée (JSON ou modèle déployable) ; (2) un **espace Log Analytics durable**, hors du groupe de séance, avec une rétention choisie, ou un export régulier du journal ; (3) la **référence** (`reference_covariables.json`) versionnée avec le modèle ; (4) idéalement une **règle d'alerte Azure Monitor** sur la requête 3 (extension de l'annexe C), pour que l'alerte n'attende pas qu'un humain ouvre le tableau de bord.

### Contrôle d'extinction

| Contrôle | Fait |
|---|---|
| `az group exists` sur le groupe de la séance renvoie `false` | oui |
| Aucun conteneur de la séance dans `docker ps -a` | oui |
| Docker Desktop quitté | à faire à la fin du rendu |
| Machine éteinte | à faire à la fin du rendu |

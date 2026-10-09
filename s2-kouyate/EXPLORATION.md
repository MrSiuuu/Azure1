# EXPLORATION — Séance 2 · Du modèle à l'API d'inférence

**Issa KOUYATÉ** — M2 Data Engineering · Ynov Campus Montpellier
Module : Industrialisation de l'IA dans le Cloud · 2026-2027
Séance du 9 octobre 2026 · Poste : Windows · PowerShell

Tous les chiffres de ce document sortent de `python explorer.py`, lancé sur mon poste.

---

## Tableau de décisions

| Décision | Ma valeur |
|---|---|
| Suffixe personnel, identique à la séance 1 | `ik42` |
| Groupe portant le registre, créé en séance 1 | `rg-dermascan-registre-ik42` |
| Registre ACR de la séance 1 | `acrdermascanik42` |
| Rappel visé, décidé avant de voir le moindre résultat | **90 %** |
| Date portée par l'étiquette `a_detruire` | `2027-09-30` |

### Question 0.1 — Pourquoi fixer le rappel visé avant la première mesure ?

Si je le choisissais après avoir vu la courbe, je prendrais le point où les chiffres sont
flatteurs, par exemple juste avant que la précision s'effondre. L'objectif serait alors
dicté par ce que le modèle sait faire, et non par le besoin médical. En le fixant avant,
c'est le besoin (ne pas rater plus d'une maligne sur dix) qui commande, et le modèle est
jugé sur ce qu'il coûte pour y arriver. J'ai fixé 90 % après l'exploration des données
mais avant tout entraînement : je n'avais vu aucun score.

---

## Mesure 1 — Versions et volumétrie du fichier

| Relevé | Commande | Ma valeur |
|---|---|---|
| Version de Python | `python --version` | 3.14.0 |
| Version de scikit-learn | `python -c "import sklearn; print(sklearn.__version__)"` | 1.9.1 |
| Version de pandas | `python -c "import pandas; print(pandas.__version__)"` | 3.0.6 |
| Poids du fichier d'annotation | `Get-Item data\train-metadata.csv` | 257 543 161 octets, soit environ 246 Mo |

Note : l'outil `kaggle` s'est authentifié (`You are now logged in`) mais la commande de
téléchargement a continué de répondre `Authentication required`. Le fichier a donc été
téléchargé depuis la page Data de la compétition, après acceptation des règles. C'est le
même fichier : 55 colonnes, colonne `target` présente.

---

## Mesure 2 — Volumétrie et structure

| Relevé | Ma valeur |
|---|---|
| Nombre de lignes | 401 059 |
| Nombre de colonnes | 55 |
| Nombre de patients distincts | 1 042 |
| Lésions par patient : minimum / médiane / maximum | 1 / 241 / 9 184 |

Types des colonnes : 35 en `float64`, 2 en `int64`, 18 en texte (`str`).

### Question 1.1 — Une ligne est-elle une observation indépendante ?

Non. Il y a 401 059 lignes pour 1 042 patients, soit 241 lésions par patient en médiane
et jusqu'à 9 184 pour un seul. Les lésions d'un même patient partagent la même peau, le
même âge, le même sexe et le même appareil : elles se ressemblent. La taille réelle de
mon échantillon est donc donnée par le **nombre de patients (1 042)**, pas par le nombre
de lignes. Conséquence pour la partie 2.1 : le découpage se fait par patient, sinon le
modèle serait évalué sur des personnes qu'il a déjà vues.

---

## Mesure 3 — Colonnes à écarter pour cause de fuite

Total de lésions malignes dans le jeu : 393.

| Colonne | Valeurs renseignées | Dont malignes | Écartée ? |
|---|---|---|---|
| `iddx_1` | 401 059 | 393 | Oui |
| `iddx_full` | 401 059 | 393 | Oui |
| `mel_thick_mm` | 63 | 63 | Oui |
| `mel_mitotic_index` | 53 | 53 | Oui |
| `lesion_id` | 22 058 | 393 | Oui |
| `iddx_2` | 1 068 | 393 | Oui |
| `iddx_3` | 1 065 | 393 | Oui |
| `iddx_4` | 551 | 242 | Oui |
| `iddx_5` | 1 | 0 | Oui |

Cela fait neuf colonnes écartées, les cinq du tableau de l'énoncé plus `iddx_2` à
`iddx_5`, qui sont les niveaux de détail du même diagnostic.

`iddx_1` est remplie partout : ce n'est pas sa présence qui trahit, c'est sa valeur.
Croisée avec la cible :

| `iddx_1` | target = 0 | target = 1 |
|---|---|---|
| Benign | 400 552 | 0 |
| Indeterminate | 114 | 0 |
| Malignant | 0 | 393 |

### Question 1.2 — Pourquoi écarter `lesion_id`, qui n'est qu'un identifiant ?

Il n'est renseigné que pour 22 058 lésions sur 401 059 (5,5 %), et les 393 malignes en
font toutes partie. Parmi les lésions qui ont un `lesion_id`, 1,78 % sont malignes,
contre 0,098 % dans l'ensemble du jeu, soit 18 fois plus ; parmi celles qui n'en ont pas,
aucune ne l'est. Sa seule présence révèle donc qu'un médecin a jugé la lésion assez
intéressante pour la suivre ou la prélever. Cet identifiant est attribué après la
photographie, au moment de l'examen clinique. Au moment où la cabine envoie une nouvelle
lésion, il est vide pour tout le monde : le modèle aurait appris « pas d'identifiant,
donc bénin » et répondrait bénin à chaque fois.

### Question 1.3 — « `iddx_1` donne 100 % de bonnes réponses, je le garde. »

Le modèle n'apprend pas à reconnaître une lésion maligne, il apprend à recopier le
diagnostic déjà posé par le médecin, puisque `iddx_1` vaut « Malignant » exactement pour
les 393 malignes. Le jour où une nouvelle lésion arrive, ce diagnostic n'existe pas
encore, la colonne est vide, et le modèle ne sait rien faire.

---

## Mesure 4 — Valeurs manquantes et colonnes constantes

| Relevé | Ma valeur |
|---|---|
| Colonnes avec au moins une valeur manquante, hors fuites | `sex`, `anatom_site_general`, `age_approx` |
| Taux de valeurs manquantes | `sex` 2,87 % (11 517) · `anatom_site_general` 1,44 % (5 756) · `age_approx` 0,70 % (2 798) |
| Colonnes constantes | `image_type` (toujours « TBP tile: close-up ») ; `iddx_5` aussi, mais déjà écartée comme fuite |
| Variables restantes après retrait des fuites, identifiants et constantes | 42 |

**Décision supplémentaire.** Parmi ces 42, je retire aussi `attribution` (l'institution
d'origine) et `copyright_license` (la licence de l'image). Elles ne décrivent pas la
lésion, une cabine en pharmacie ne les enverra jamais, et le modèle pourrait apprendre
« telle institution a plus de cancers » au lieu de regarder la lésion. Il reste
**40 variables pour le modèle** : 35 numériques et 5 catégorielles (`sex`,
`anatom_site_general`, `tbp_tile_type`, `tbp_lv_location`, `tbp_lv_location_simple`).
`attribution` reste utile pour l'analyse des angles morts de la model card, pas comme
entrée du modèle.

### Question 1.4 — Pourquoi retirer une colonne constante, et pourquoi la consigner ?

La retirer : toute colonne gardée devient un champ que le client de l'API doit envoyer à
chaque appel. `image_type` serait un champ obligatoire qui n'apporte aucune information,
et qui ferait échouer l'appel s'il manquait.

La consigner : sa valeur unique dit sur quoi le modèle a été entraîné. Il n'a vu que des
images de type « TBP tile: close-up ». Si un autre type d'image arrive un jour, le modèle
est hors de son domaine de validité, et c'est cette trace écrite qui permettra de le
savoir.

---

## Mesure 5 — Déséquilibre de la cible

| Relevé | Ma valeur |
|---|---|
| Nombre de lésions `target = 1` | 393 |
| Nombre de lésions `target = 0` | 400 666 |
| Taux de positifs | 0,098 % |
| Rapport « une maligne pour N bénignes » | 1 pour 1 020 |

### Question 1.5 — Exactitude d'un classifieur qui répond toujours « bénin »

Il a raison sur les 400 666 bénignes et tort sur les 393 malignes :
400 666 / 401 059 = **99,902 %**. Ce score presque parfait est obtenu en ne détectant
aucun cancer. L'exactitude compte toutes les bonnes réponses de la même façon, et comme
il y a 1 020 bénignes pour une maligne, elle ne mesure presque que la capacité à dire
« bénin ». Elle ne peut pas servir de critère de choix sur ce jeu.

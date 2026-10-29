# JOURNAL — Séance 4 · Modèle lourd : deep learning

**Issa KOUYATÉ** — M2 Data Engineering · Ynov Campus Montpellier
Module : Industrialisation de l'IA dans le Cloud · 2026-2027
Séance du 29 octobre 2026 · Entraînement : Google Colab (GPU Tesla T4) · Poste : Windows + WSL2 Ubuntu 22.04

---

## Environnement réellement utilisé

| Élément | Valeur |
|---|---|
| Entraînement | Colab navigateur, GPU **Tesla T4**, torch 2.11.0+cu130 |
| Poste | Windows, tout le travail local dans **WSL2 Ubuntu 22.04** |
| Python local | **3.12.16** installé avec `uv` (Ubuntu 22.04 n'a que 3.10) |
| torch local | 2.14.1+cpu et torchvision 0.29.1+cpu, depuis l'index CPU de PyTorch (mêmes versions que `requirements-entrainement.txt`, sans les 3 Go de CUDA inutiles sans GPU) |
| Docker | Moteur Docker **propre à WSL** (distinct de Docker Desktop) : build, scan et tests faits dans WSL |
| Azure CLI | Installée dans WSL (2.91.0) pour exécuter les commandes bash de l'énoncé telles quelles |

## Incidents et adaptations

| Incident | Adaptation |
|---|---|
| L'URL `isic-challenge-data.s3.amazonaws.com/2024/` renvoie une page « Moved » de 428 octets, enregistrée à la place du zip (cellule « 0 s ») | Contrôle des tailles, puis téléchargement depuis la nouvelle adresse `isic-archive.s3.amazonaws.com/challenges/2024/`. Zip vérifié : **653 107 434 octets**, la taille attendue en annexe A |
| Cellule Kaggle : `No module named kaggle.__main__` | Appel par la commande `kaggle` directe, jeton au nouveau format `KGAT_…` passé par `KAGGLE_API_TOKEN` (lu depuis les Secrets Colab, jamais écrit en clair) |
| L'entraînement GPU a fini en 3 min sans laisser le temps de couper | Relance complète pour provoquer la coupure de la partie 3.3. Le modèle livré est celui du second lancement |
| `unzip` absent dans WSL | `python -m zipfile -e` |
| `docker scout` non connecté dans WSL | `docker login` dans WSL |

---

## Tableau de décisions

| Décision | Contrainte | Ma valeur |
|---|---|---|
| `N_NEGATIFS` | Avec GPU : la valeur de la progression | **20 000** (GPU T4 attribué) |
| Graine | Celle du code distribué | **42** |
| Taille d'entrée | Lue dans `donnees.py` | **128 px** |
| Architecture | Lue dans `entrainer.py` | **ResNet18** pré-entraîné ImageNet, tête `fc` à 1 logit |
| Époques gelé / dégelé | Lues dans `entrainer.py` | **4 / 4** (dégel de `layer4`) |
| Taux d'apprentissage | Lus dans `entrainer.py` | **1e-3** (tête) / **1e-4** (dégel), AdamW, weight decay 1e-4 |
| Taille de lot | Lue dans `entrainer.py` | **64** |
| Part de validation | Exprimée en plis | **1 pli sur 5** (pli 0 de `StratifiedGroupKFold(5)`), soit ~20 % |
| Rappel visé | À justifier par rapport à S2 | **90 %**, le même qu'en S2 : on ne change qu'une pièce de la chaîne, le compromis clinique reste celui décidé avec le médecin, et les deux modèles se comparent au même point de fonctionnement |
| Métrique de sélection | Lue dans `entrainer.py` | **PR-AUC de validation** |
| Tag de l'image | Version sémantique | **2.0.0** (S2 : 1.0.0). Version majeure : l'entrée de `/predict` change (une image au lieu de 40 variables), un client de la 1.0.0 ne peut pas appeler la 2.0.0 sans modification |
| Groupe de la séance | Préfixé `rg-dermascan-s4-` | `rg-dermascan-s4-ik42` |
| Registre ACR | Celui de S1, jamais détruit | `acrdermascanik42` (groupe `rg-dermascan-registre-ik42`) |

### Question 0.1 — Ce que la graine garantit

Elle fixe le tirage des négatifs (`pandas.sample`), le découpage (`StratifiedGroupKFold(shuffle=True)`), l'ordre des lots et les augmentations (`torch.Generator`) — **à versions de bibliothèques identiques**. Vérifié : avec le même code et la graine 42, mon poste (scikit-learn 1.9.1) tire **les mêmes 20 294 vignettes** que Colab, mais seulement **70,3 %** tombent dans le même jeu, et le manifeste a une autre empreinte (`b0e0dbe0…` contre `72f3ed14…`).
Elle ne garantit pas les poids finaux : le GPU et le CPU n'enchaînent pas les calculs flottants dans le même ordre, et certains noyaux cuDNN ne sont pas déterministes. Vérifié aussi : sur deux lancements Colab, les époques 1 à 4 sont identiques au dix-millième, l'époque 5 diverge (PR-AUC 0,1982 puis 0,1870).
Deux apprenants, l'un sur CPU, l'autre sur GPU, ont donc le même échantillon s'ils ont les mêmes versions, mais jamais les mêmes poids : c'est le manifeste et `sha256_poids` qui tracent, pas la graine.

### Question 0.2 — Pourquoi la PR-AUC plutôt que l'exactitude ?

Avec 1,26 % de positifs en validation, un modèle qui répond toujours « bénin » obtient déjà 98,74 % d'exactitude : l'exactitude récompenserait l'époque qui détecte le moins de malignes, alors que la PR-AUC mesure si les malignes passent devant les bénignes. Vérifié en partie 1.3 (mesure 3).

---

# Partie 1 — Données

## Mesure 1 — L'archive et l'échantillon

| Relevé | Ma valeur |
|---|---|
| Vignettes dans l'archive Permissive | **217 477** |
| Positifs dans l'archive, et prévalence | **294**, soit **0,135 %** |
| Patients distincts dans l'archive | **634** |
| Vignettes de l'échantillon | **20 294** = 294 positifs + 20 000 négatifs |
| Prévalence de l'échantillon | **1,45 %** |
| Découpage (manifeste Colab) | entraînement 16 158 vignettes (242 positifs, 497 patients) · validation 4 136 (52 positifs, 122 patients) |
| Taille du tableau en mémoire | (20294, 128, 128, 3), uint8, **997 Mo** |
| Taille d'origine des vignettes (500 premières) | médiane **127 px**, min **91**, max **211** |
| Durée de `python donnees.py` | **60,9 s** au premier lancement · **28,4 s** au second (cache `.npy`) |

## Mesure 2 — Ligne d'échantillonnage

| Effectif | Graine | Méthode | Prévalence d'entraînement | Empreinte du manifeste |
|---|---|---|---|---|
| 20 294 | 42 | Tous les positifs + 20 000 négatifs tirés uniformément sans remise (`pandas.sample`) | 1,45 % | `72f3ed140ec96fb9` |

Le manifeste livré est celui produit sur Colab, avec lequel le modèle a été entraîné. Relancer `donnees.py` sur le poste le réécrit avec un autre découpage (question 0.1) : je l'ai restauré depuis le paquet, empreinte vérifiée.

### Question 1.1 — Un effectif fixe de négatifs, pas une fraction

1. **Recalibration.** La correction de la partie 4 vaut ln β, avec β = négatifs tirés / négatifs disponibles. Avec un effectif fixe, le numérateur est une constante écrite dans le code et dans le meta (`n_negatifs`, `n_negatifs_disponibles`), et la prévalence d'entraînement est décidée, pas subie. La correction se recalcule exactement à partir de deux nombres tracés.
2. **Reproductibilité.** Si l'archive est mise à jour, une fraction de 20 % changerait la taille même de l'échantillon (donc le coût d'entraînement, la durée d'époque, la mémoire). L'effectif fixe garde un échantillon de même taille, et le manifeste avec son empreinte dit exactement quelles vignettes ont servi : toute différence se détecte.

### Question 1.2 — Pourquoi l'archive Permissive

Près de la moitié des images de `train-image.hdf5` sont sous licence non commerciale (CC-BY-NC) ; la partie Permissive est en CC-BY 4.0, utilisable commercialement à condition de citer la source. DermaScan veut servir ce modèle dans un produit payant : un modèle entraîné sur des images NC ne pourrait pas être exploité.

## Mesure 3 — Exactitude du modèle constant « bénin »

| Population | Calcul | Exactitude |
|---|---|---|
| Flux réel (archive entière) | 1 − 294 / 217 477 | **99,865 %** |
| Échantillon d'entraînement | 1 − 294 / 20 294 | **98,551 %** |
| Jeu de validation | 1 − 52 / 4 136 | **98,743 %** |

### Question 1.3 — Le plancher bouge

Le plancher vaut 1 − prévalence, et la prévalence change parce qu'on a gardé tous les positifs mais seulement 9,2 % des négatifs. Toute métrique qui dépend du nombre de négatifs (exactitude, précision, PR-AUC) n'a donc pas la même valeur sur l'échantillon et sur le flux réel : la comparer telle quelle mélange la qualité du modèle et la composition de la population. Il faut ramener les deux à la même prévalence, ce que fait la partie 4.

---

# Partie 2 — Découpage et prétraitement

## Mesure 4 — L'expérience de fuite

Code écrit (interpréteur, depuis le dossier) :

```python
tr2, va2 = train_test_split(m, test_size=0.2, stratify=m.cible, random_state=42)
communs = set(tr2.patient_id) & set(va2.patient_id)
print(len(va2), va2.cible.sum(), va2.patient_id.nunique(), len(communs))
```

Stratifié sur `cible`, `test_size` 0,2 (un pli sur cinq), graine 42.

| Découpage | Vignettes en validation | Positifs en validation | Patients en validation | Patients communs |
|---|---|---|---|---|
| `decouper()` (par patient) | 4 136 | 52 | 122 | **0** |
| `train_test_split` ligne à ligne | 4 059 | 59 | 561 | **555** |

### Question 2.1 — Ce que le découpage ligne à ligne ferait apprendre

555 des 561 patients de validation seraient aussi à l'entraînement. Leurs lésions partagent la même peau, le même éclairage, le même appareil, le même grain d'image : le réseau apprendrait à reconnaître le patient et ses conditions de prise de vue, pas la lésion. La PR-AUC de validation serait gonflée, puisqu'on mesurerait sur des patients déjà vus ; le score s'effondrerait sur un nouveau patient.

### Question 2.2 — Pourquoi `StratifiedGroupKFold`

`GroupShuffleSplit` tire des patients sans regarder les positifs. Avec 294 malignes concentrées chez quelques patients, la validation pourrait en recevoir 20 comme 100 : en S2, 20 % des patients portaient 28 % des malignes. `StratifiedGroupKFold` garde les patients groupés tout en équilibrant les positifs : ici 52 / 294 = 17,7 % des malignes pour un pli de 20 %.

## Mesure 5 — Le lot d'entrée

| Relevé | Ma valeur |
|---|---|
| Forme | (64, 3, 128, 128) |
| Type | torch.float32 |
| Minimum et maximum | −2,118 et 2,249 |
| Moyenne et écart-type | **0,435** et 0,678 |

### Question 2.3 — Normalisation ImageNet

Les poids du ResNet18 ont été appris sur des images normalisées avec la moyenne et l'écart-type d'ImageNet : ses filtres attendent cette échelle. Changer la normalisation décalerait toutes les entrées par rapport à ce que le réseau pré-entraîné sait traiter. Ma moyenne relevée, 0,435, est loin de 0 : les vignettes de peau sont nettement plus claires et plus homogènes en couleur que les photographies d'ImageNet.

### Question 2.4 — Passer à 224 px

Le coût d'une convolution suit le nombre de pixels : (224 / 128)² = **3,06 fois** plus de calcul. Pour une information nulle : les vignettes font ~127 px à l'origine, les agrandir à 224 ne ferait qu'interpoler des pixels qui n'existent pas. Le seul gain serait de retrouver l'échelle des motifs vue par le réseau pendant son pré-entraînement.

### Question 2.5 — Rotations oui, couleur non

Une lésion photographiée sur la peau n'a ni haut ni bas : la tourner ou la retourner ne change pas sa malignité. Un chiffre manuscrit a une orientation (un 6 retourné devient un 9). La couleur, elle, est un critère diagnostique : un `ColorJitter` détruirait le **C** de la règle ABCDE (Couleur : une lésion polychrome est suspecte).

### Question 2.6 — Pas d'augmentation en validation

La validation doit mesurer le modèle sur les images telles qu'il les recevra en service, et donner le même score à chaque passage.

---

# Partie 3 — Entraînement

### Question 3.1 — Paramètres entraînables

| Phase | Couches qui apprennent | Paramètres entraînables | Part du total |
|---|---|---|---|
| Tête seule | `fc` | **513** | 0,005 % |
| Dégel | `layer4` + `fc` | **8 394 241** | 75,1 % |
| Total du réseau | — | 11 177 025 | 100 % |

### Question 3.2 — Pourquoi `requires_grad = False` ne suffit pas

`requires_grad = False` empêche l'optimiseur de modifier les poids, mais les couches **BatchNorm** ont aussi des statistiques (`running_mean`, `running_var`) qui ne sont pas des paramètres : en mode `train()`, elles se mettent à jour à chaque lot, gradient ou pas. `mode_entrainement()` passe tout le réseau en `eval()`, puis seulement les couches actives en `train()`. Sans cela, les statistiques ImageNet du backbone « gelé » dériveraient vers celles des vignettes, sans aucun message d'erreur. Le vérificateur compare précisément ces tenseurs aux poids ImageNet d'origine (122 tenseurs comparés, OK).

## Mesure 6 — Conditions de l'entraînement

| Relevé | Ma valeur |
|---|---|
| Où | Colab navigateur, GPU **Tesla T4** |
| `N_NEGATIFS` | **20 000** |
| Vignettes d'entraînement / validation (positifs) | 16 158 (242) / 4 136 (52) |
| Durée de chargement des données | **26,0 s** au premier lancement (lecture du zip) · 5,2 s puis 4,9 s ensuite (cache `.npy`) |

## Mesure 7 — Courbe d'entraînement (identique à `sorties/historique.csv`)

| Époque | Phase | Durée (s) | Perte d'entraînement | PR-AUC | ROC-AUC | pAUC (rappel > 80 %) |
|---|---|---|---|---|---|---|
| 1 | tête | 20,6 | 0,1015 | 0,0519 | 0,6521 | 0,0384 |
| 2 | tête | 22,8 | 0,0694 | 0,1048 | 0,7965 | 0,0583 |
| 3 | tête | 22,2 | 0,0646 | 0,1198 | 0,8043 | 0,0639 |
| 4 | tête | 16,2 | 0,0629 | 0,1133 | 0,7911 | 0,0642 |
| 5 | dégel | 18,9 | 0,0681 | 0,1870 | 0,8509 | 0,0910 |
| 6 | dégel | 21,9 | 0,0476 | 0,1608 | 0,8644 | 0,0998 |
| 7 | dégel | 21,3 | 0,0414 | 0,1007 | 0,8248 | 0,0862 |
| 8 | dégel | 21,5 | 0,0383 | **0,2101** | 0,8779 | 0,1165 |

Époque retenue : **8**. Durée totale 153 s, RAM max 4 004 Mo.

### Question 3.3 — La perte baisse, la PR-AUC recule

Oui : à l'époque 7, la perte passe de 0,0476 à 0,0414 pendant que la PR-AUC tombe de 0,1608 à 0,1007 (même chose, plus faiblement, aux époques 4 et 6).
1. **Sur-apprentissage** : le réseau, maintenant que `layer4` est dégelé, colle davantage aux lésions d'entraînement sans mieux classer celles des patients nouveaux.
2. **Bruit de mesure** : la validation ne compte que **52 malignes**. Que deux ou trois d'entre elles passent derrière quelques centaines de bénignes suffit à faire bouger la PR-AUC de plusieurs centièmes ; une partie du recul est du hasard.
La sélection sur la meilleure époque protège le modèle livré : on ne livre pas la dernière époque, mais celle dont la PR-AUC était la plus haute, quelle que soit la forme de la courbe.

## Mesure 8 — Reprise après coupure

| Relevé | Ma valeur |
|---|---|
| Époque interrompue | **2** (pendant le calcul, `KeyboardInterrupt`) |
| Ligne affichée au redémarrage | `reprise a l'epoque 2` |
| Époques recalculées en double | **1** : l'époque 2, interrompue en cours, refaite entièrement |
| Taille du point de reprise (`reprise.pt`) | **89 582 089 octets** (≈ 89,6 Mo, deux fois le modèle : il contient aussi l'optimiseur et le meilleur état) |

Preuves : `captures/01_coupure_epoque2.png` et `captures/02_reprise_entrainement.png`.

### Question 3.4 — Meilleur état et générateur

- **Le meilleur état** : c'est lui qui est livré. Sans lui, après une coupure, une meilleure époque déjà passée serait perdue et on livrerait la dernière.
- **L'état du générateur** : il fixe l'ordre des lots et les tirages d'augmentation des époques suivantes. Sans lui, le générateur repartirait de la graine au redémarrage : l'époque 2 rejouerait l'ordre et les augmentations de l'époque 1, et l'entraînement repris ne serait plus celui qu'on aurait obtenu sans coupure.

## Mesure 9 — Latence du réseau seul, lot de 1

| Dispositif | p50 (ms) | p95 (ms) |
|---|---|---|
| CPU (Colab) | 29,3 | 34,2 |
| GPU (Tesla T4) | 6,0 | 6,2 |

### Question 3.5 — Le GPU accélère-t-il autant une prédiction unitaire ?

Non. L'entraînement traite des lots de 64 images : le GPU y est massivement parallèle, c'est ce qui permet 8 époques en 3 minutes. Pour une image seule, le gain n'est que de ×5, et 29 ms sur CPU restent faibles devant le reste de la chaîne : en local, `/predict` complet répond en 19,6 ms au p50, et sur Azure, la latence est dominée par le réseau et la file d'attente (mesure 19). Servir ce modèle n'exige pas de GPU : le plan B1 de S3, sans GPU, suffit en latence unitaire ; c'est le débit sous charge qui le limite.

## Mesure 10 — Vérification du paquet rapatrié

| Relevé | Ma valeur |
|---|---|
| Contrôles OK / total, verdict | **13 / 13, RENDU RECEVABLE** |
| Contrôles « SAUTE » | Aucun |
| sha256 de `modele.pt` (16 car.) et égalité | `3f334db3a2a143f1` — identique à `sha256_poids` |
| Taille de `modele.pt` | 44,8 Mo |
| Bloc `controle` | `ISIC_0699524`, probabilité 0,352668 (recalculée par le vérificateur : 0,352667) |

Preuve : `captures/03_verifier_s4.png`.

### Question 3.6 — Pourquoi publier depuis le poste

1. **Un notebook se partage** (avec le professeur, les camarades, sur GitHub) : un secret Azure écrit dedans, ou laissé dans ses sorties, partirait avec lui.
2. **Le paquet rend Colab inutile pour la suite** : il contient les poids, le meta et les empreintes. On le vérifie sur le poste, déjà authentifié auprès d'Azure, et seul un paquet vérifié est emballé et publié. Colab n'a jamais besoin de parler à Azure.

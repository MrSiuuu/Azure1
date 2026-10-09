# MODEL CARD — DermaScan · modèle de tri des lésions cutanées

**Version du modèle : 1.0.0** · entraîné le 9 octobre 2026
**Auteur :** Issa KOUYATÉ — M2 Data Engineering · Ynov Campus Montpellier
Module : Industrialisation de l'IA dans le Cloud · 2026-2027 · Séance 2

Cette fiche permet à quelqu'un d'autre de décider s'il peut utiliser ce modèle, et pour
quoi. Tous les chiffres viennent de `explorer.py` et `entrainer.py`, lancés sur mon poste.

---

## 1. Usage prévu

Le tri, et rien d'autre. Le modèle reçoit les mesures d'une lésion photographiée en
cabine et répond si elle doit être montrée en priorité à un dermatologue
(`a_examiner`) ou non (`non_prioritaire`). Il sert à ordonner le travail d'un médecin
qui ne peut pas relire les centaines de lésions d'un même patient.

## 2. Usage explicitement exclu

- **Le diagnostic.** Le modèle ne dit pas si une lésion est un cancer.
- **Rassurer un patient.** `non_prioritaire` ne veut pas dire « bénin » : une maligne sur
  dix n'est pas signalée.
- **Un usage sans médecin.** Aucune décision de soin ne doit être prise sur la seule
  réponse de l'API.
- **Une autre population que celle de l'entraînement**, par exemple une consultation
  spécialisée où les lésions ont déjà été sélectionnées par un médecin (voir rubrique 7).
- **Un autre type d'image** que « TBP tile: close-up », le seul vu à l'entraînement.

## 3. Données d'entraînement

| Élément | Valeur |
|---|---|
| Origine | Jeu ISIC 2024 (International Skin Imaging Collaboration), fichier `train-metadata.csv`, licence CC BY-NC 4.0 |
| Nature | Données de santé réelles, issues d'institutions hospitalières |
| Volumétrie totale | 401 059 lésions, 1 042 patients, 55 colonnes |
| Lésions par patient | 1 au minimum, 241 en médiane, 9 184 au maximum |
| Lésions malignes | 393, soit 0,098 % (une pour 1 020 bénignes) |
| Ensemble d'entraînement | 319 514 lésions, 833 patients, 283 malignes (0,0886 %) |
| Ensemble de test | 81 545 lésions, 209 patients, 110 malignes (0,1349 %) |
| Découpage | Par patient (`GroupShuffleSplit`, 20 % de test, graine 42), aucun patient des deux côtés |

**La prévalence d'entraînement n'est pas la prévalence réelle.** Les patients de ce jeu
sont suivis dans des centres de dermatologie spécialisés. Les clients d'une pharmacie ne
sont pas la même population : la part de lésions malignes y sera différente, et personne
ne l'a encore mesurée. Les chiffres de précision de cette fiche ne valent que pour une
prévalence proche de 0,1 %.

## 4. Variables utilisées

40 variables : 35 numériques et 5 catégorielles.

| Famille | Nombre | Variables |
|---|---|---|
| Patient | 2 | `age_approx`, `sex` |
| Position anatomique | 6 | `anatom_site_general`, `tbp_lv_location`, `tbp_lv_location_simple`, `tbp_lv_x`, `tbp_lv_y`, `tbp_lv_z` |
| Taille et forme | 9 | `clin_size_long_diam_mm`, `tbp_lv_areaMM2`, `tbp_lv_perimeterMM`, `tbp_lv_minorAxisMM`, `tbp_lv_area_perim_ratio`, `tbp_lv_eccentricity`, `tbp_lv_symm_2axis`, `tbp_lv_symm_2axis_angle`, `tbp_lv_norm_border` |
| Couleur et contraste | 20 | `tbp_lv_A`, `Aext`, `B`, `Bext`, `C`, `Cext`, `H`, `Hext`, `L`, `Lext`, `deltaA`, `deltaB`, `deltaL`, `deltaLB`, `deltaLBnorm`, `stdL`, `stdLExt`, `color_std_mean`, `radial_color_std_max`, `norm_color` |
| Acquisition | 1 | `tbp_tile_type` |
| Scores calculés par l'appareil | 2 | `tbp_lv_nevi_confidence`, `tbp_lv_dnn_lesion_confidence` |

Les deux scores de la dernière ligne sont produits par le logiciel de l'appareil de
photographie. Si ce logiciel change de version, ces deux entrées changent de sens.

Prétraitement : valeurs manquantes remplacées par la médiane (numériques) ou par la
valeur la plus fréquente (catégorielles), mise à l'échelle, encodage one-hot avec
`handle_unknown="ignore"`. Modèle : régression logistique, `class_weight="balanced"`.

## 5. Variables écartées, avec le motif

| Variable | Motif |
|---|---|
| `iddx_full`, `iddx_1`, `iddx_2`, `iddx_3`, `iddx_4`, `iddx_5` | **Fuite.** C'est le diagnostic lui-même : `iddx_1` vaut « Malignant » pour les 393 malignes et pour elles seules |
| `mel_thick_mm`, `mel_mitotic_index` | **Fuite.** Mesures faites au microscope après biopsie : remplies 63 et 53 fois, toujours pour une maligne |
| `lesion_id` | **Fuite.** Attribué seulement aux lésions examinées par un médecin : 22 058 lésions, dont les 393 malignes |
| `isic_id`, `patient_id` | Identifiants. `patient_id` sert au découpage, pas au modèle |
| `image_type` | Constante (« TBP tile: close-up ») : aucune information |
| `attribution`, `copyright_license` | Origine administrative de l'image, pas une mesure de la lésion ; absente en production |
| `target` | La cible |

## 6. Performance

Mesurée sur l'ensemble de test : 209 patients jamais vus, 81 545 lésions, 110 malignes.

| Métrique | Modèle | Valeur du hasard |
|---|---|---|
| **PR-AUC** | **0,0542** | 0,0013 (le taux de positifs du test) |
| ROC-AUC | 0,9097 | 0,5000 |

Le modèle fait environ 40 fois mieux que le hasard, mais sa précision reste très faible
en valeur absolue. L'exactitude (84,92 %) n'est pas retenue comme critère : un modèle qui
répond toujours « bénin » obtient 99,87 % en ne trouvant aucun cancer.

Ces chiffres viennent d'un seul découpage. Avec 110 malignes au test, ils changeraient
avec une autre graine.

## 7. Seuil et compromis

Rappel visé : **90 %**, fixé avant tout entraînement.

| Relevé | Valeur |
|---|---|
| Seuil retenu | 0,347616 |
| Rappel obtenu | 90,00 % (99 malignes signalées sur 110) |
| Précision | 0,5062 % |
| **Lésions examinées par maligne trouvée** | **198** |
| Faux négatifs | 11 sur 110 |
| Alertes pour 1 000 lésions | 239,8 |

En clair : sur 1 000 lésions, le service en écarte 760 et en signale 240 ; parmi les
lésions signalées, une sur 198 est maligne ; une maligne sur dix n'est pas signalée.
Sans le service, la proportion est d'une maligne pour 741 lésions.

Le seuil a été réglé sur l'ensemble de test lui-même : le rappel de 90 % y est atteint
par construction. Il doit être revérifié sur de nouveaux patients.

Le seuil est un arbitrage clinique. Il se change par la variable d'environnement `SEUIL`,
sur décision d'un médecin, pas d'un ingénieur.

## 8. Populations et angles morts

La colonne `attribution` ne contient que sept institutions :

| Institution | Pays | Lésions | Malignes |
|---|---|---|---|
| Memorial Sloan Kettering Cancer Center | États-Unis | 129 068 | 174 |
| Hospital Clínic de Barcelona | Espagne | 105 724 | 72 |
| University Hospital of Basel | Suisse | 65 218 | 13 |
| Frazer Institute, University of Queensland | Australie | 51 768 | 81 |
| ACEMID MIA | Australie | 28 665 | 33 |
| Medical University of Vienna | Autriche | 12 640 | 14 |
| University of Athens, Andreas Syggros Hospital | Grèce | 7 976 | 6 |

L'énoncé parle de neuf institutions ; le fichier d'annotation en distingue sept.

- **Peaux foncées.** Aucune institution en Afrique, en Asie ou en Amérique latine, et
  aucune colonne ne décrit le phototype. Les peaux foncées sont très probablement
  sous-représentées, et le jeu ne permet même pas de mesurer la performance sur elles.
- **Femmes.** Parmi les lésions dont le sexe est connu, 68 % viennent d'hommes
  (265 546 contre 123 996).
- **Jeunes.** L'âge médian est de 60 ans, la moitié des lésions vient de patients de 50 à
  70 ans. Les moins de 20 ans représentent 645 lésions, soit 0,16 %.
- **Poids d'un seul centre.** Memorial Sloan Kettering fournit 32 % des lésions et 44 %
  des malignes. Le modèle a surtout appris ce à quoi ressemble une maligne dans ce centre.
- **Patients à risque.** Tous sont suivis en dermatologie spécialisée, ce qui n'est pas
  le public d'une pharmacie.

## 9. Versions

| Élément | Valeur |
|---|---|
| Modèle | 1.0.0, entraîné le 9 octobre 2026 |
| Python | 3.14.0 |
| scikit-learn | 1.9.1 |
| pandas | 3.0.6 |
| numpy | 2.5.3 |
| joblib | 1.6.0 |
| Image | `acrdermascanik42.azurecr.io/dermascan-api:1.0.0` |
| Digest | `sha256:35654575fabaf125bc5a169a45c03dd9fbc43db0bca7cbf9a24e822d1f4f76aa` |

Le modèle ne se recharge que dans ces versions : elles sont épinglées dans
`requirements.txt` et l'image de base est `python:3.14.0-slim-bookworm`.

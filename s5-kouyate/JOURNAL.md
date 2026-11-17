# JOURNAL — TP5 « Optimiser et surveiller » (YNOV)

Issa Kouyaté — séance du 17/11/2026 — dossier `s5-kouyate/`

## Tableau de décisions

Date de remplissage : **17/11/2026**.

| Décision | Contrainte | Valeur | Rempli |
|---|---|---|---|
| Suffixe personnel | identique à S1 | `ik42` | après la mesure 3 |
| Écart max. de probabilité, « même modèle » | ONNX contre PyTorch | `1e-4` | après la mesure 3 |
| Rappel minimal d'une variante | au seuil servi | `0,88` | après la mesure 3 |
| Décisions changées max., même version | entier | `0` | après la mesure 3 |
| Covariable surveillée en priorité | reçue par l'API | `tbp_tile_type` | avant toute mesure de dérive |
| Statistique de dérive | calculée par derive.py | PSI | avant toute mesure de dérive |
| Seuil d'alerte du PSI | avant la mesure | `0,25` | avant toute mesure de dérive |
| Seuil de surveillance du PSI | sous l'alerte | `0,10` | avant toute mesure de dérive |
| Fenêtre glissante | en inférences | `200` | avant toute mesure de dérive |
| Levier de dérive provoquée | eclairage, age, site | `eclairage` | avant toute mesure de dérive |

Le **second levier** demandé par la mesure 9 est `age` ; aucune autre ligne du tableau n'a été touchée.

### Déclaration sur la date de remplissage

- **J'ai oublié ce tableau au début de la séance.** Il devait être rempli avant la partie 1. Les **4 premières lignes** ont été remplies **après la mesure 3** (la comparaison des trois variantes) : je ne les ai pas antidatées. Conséquence : ces trois seuils (`1e-4`, `0,88`, `0`) ont été posés en connaissant déjà les résultats des variantes. Le seuil de rappel de 0,88 se trouve juste sous le rappel de PyTorch mesuré (0,8846) ; il n'est pas ce qui écarte l'int8, dont le rappel (0,9038) passe ce critère. L'int8 est écartée par les deux autres critères (écart de probabilité et décisions changées), qui sont des valeurs de principe : `1e-4` est de l'ordre de la précision du float32 et « 0 décision changée » est la définition de « même modèle ».
- Les **6 dernières lignes** (dérive) ont été remplies **avant toute mesure de dérive** (avant la mesure 7).
- **Aucune valeur de ce tableau n'a été modifiée** après la lecture d'une mesure de dérive : le seuil d'alerte de 0,25, le seuil de surveillance de 0,10 et la fenêtre de 200 sont les mêmes en local (mesures 8 et 9) et sur Azure (mesure 10).

### Décision de la partie 3.3 (rappel)

ONNX float32 (`modele.onnx`), version **2.0.0**. La variante int8 est refusée comme « même modèle » (écart max de probabilité 0,28 ; 178 décisions changées). Détail dans `MESURES.md`.

## Question 0.1 — Pourquoi fixer le seuil d'alerte avant de regarder la dérive ?

Un analyste qui choisirait son seuil après avoir vu ses courbes le calerait, sans le vouloir, sur ce qu'il vient de voir : la barre juste sous le pic à détecter et juste au-dessus du bruit à ignorer. Le seuil serait alors ajusté aux données de l'essai, le délai d'alerte et le taux de fausses alertes mesurés seraient flatteurs, et on ne saurait plus si la détection marcherait sur une dérive future.

## Question 0.2 — Pourquoi sacrifier la quantization avant la surveillance ?

La quantization est une optimisation de coût (taille, latence) : sans elle, le service tient encore en ONNX float32. La surveillance protège les patients : le service continue de répondre `200` avec des probabilités d'apparence normale quand les données changent, et sans surveillance rien ne signale que le modèle ne voit plus le monde sur lequel il a été entraîné.

## Incidents et écarts déclarés

| Date | Écart | Traitement |
|---|---|---|
| 17/11/2026 | Tableau de décisions oublié au début ; lignes 1 à 4 remplies après la mesure 3 | Déclaré ci-dessus, non antidaté |
| 17/11/2026 | Énoncé : « 1 058 vignettes de validation » ; mon `modele_meta.json` indique **4 136** (dont 52 malignes) | Je garde les chiffres de mon jeu (4 136) |
| 17/11/2026 | `.dockerignore` distribué sans la ligne `**/*.pt` | Ligne ajoutée avant la construction |
| 17/11/2026 | `unzip` absent de WSL | Image de contrôle extraite avec le module Python `zipfile` |
| 17/11/2026 | Tableau de bord partagé `dermascan-s5` créé **dans** le groupe de séance (au lieu du groupe par défaut `dashboards`) ; premiers essais d'épinglage faits en privé par erreur | Observation de la mesure 12 faite sur un clone `dermascan-s5-hors-groupe` placé hors du groupe de séance ; les tableaux de bord privés des premiers essais restent (gratuits, hors groupe) |
| 17/11/2026 | Premier lancement de Locust en échec (`KeyError: IMAGE_CONTROLE_S4`) : variable d'environnement absente, aucune requête envoyée | Variable définie, mesure relancée |
| 17/11/2026 | Fenêtre de 5 min à 14:25 UTC ne contenant qu'un seul appel (appel de test) : PSI ≈ 4, taux de a_examiner 100 % | Exclue de la lecture, signalée dans `SURVEILLANCE.md` |

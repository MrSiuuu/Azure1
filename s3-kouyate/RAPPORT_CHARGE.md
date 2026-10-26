# Séance 3 — Rapport de test de charge

**Industrialisation de l'IA dans le Cloud · Ynov Montpellier · M2**
Auteur : Issa KOUYATÉ — 26/10/2026

Cible : `https://dermascan-api-ik42.azurewebsites.net` — App Service, plan **B1 Linux (1 vCPU)**, `germanywestcentral`, **une instance**, Gunicorn **1 worker sync** (image S2).
Outil : Locust 2.47.0 (Python 3.11.1), sans interface, depuis mon poste. Pièces jointes : `palier[1-4]_stats.csv` et `palier[1-4].html`, non retouchés.

---

## Scénario (`locustfile.py`)

| Décision | Valeur |
|---|---|
| Temps de réflexion | `between(1, 5)` secondes |
| Poids | `/predict` **10**, `/health` **1**, `/model/info` **1** |
| Variables perturbées | `age_approx` ±10 ans par pas de 5, borné 20–85 (format ISIC) ; `clin_size_long_diam_mm` et `tbp_lv_areaMM2` ±20 % |
| Contrôle préalable | 5 appels avec la charge perturbée → **5 × 200** |

### Question 5.1 — Justification des poids

- **`/predict` = 10** : c'est le geste métier. Chaque patient vu en consultation donne une soumission de lésion.
- **`/health` = 1** : vérification occasionnelle de disponibilité par le poste, pas un geste du praticien.
- **`/model/info` = 1** : consulté à l'ouverture de l'outil ou pour vérifier la version, pas à chaque patient.

---

## Critère de rupture — posé avant toute mesure

| Élément | Choix | Justification |
|---|---|---|
| Taux d'échec inacceptable | **> 1 %** | En dépistage, une prédiction sur cent perdue, c'est un patient sans réponse en consultation |
| p95 inacceptable | **> 3 × le p95 du palier 1** | Au-delà, l'attente devient perceptible pour le praticien (repère du cours) |
| Rupture atteinte quand | **l'un des deux** | Une seule dégradation suffit à rompre l'engagement de service |

Paliers retenus (10 à 150 utilisateurs, plus d'un ordre de grandeur), 3 minutes chacun :

| Palier | `--users` | `--spawn-rate` |
|---|---|---|
| 1 | 10 | 2 |
| 2 | 30 | 5 |
| 3 | 75 | 10 |
| 4 | 150 | 15 |

---

## Mesure 13 — Résultats (ligne `Aggregated` des CSV)

| Palier | Utilisateurs | Débit (req/s) | p50 (ms) | p95 (ms) | p99 (ms) | Échecs (%) | Échecs les plus fréquents |
|---|---|---|---|---|---|---|---|
| 1 | 10 | 3,17 | 92 | 430 | 940 | 0 | aucun |
| 2 | 30 | 8,80 | 120 | **1 500** | 4 400 | 0 | aucun |
| 3 | 75 | 15,55 | 1 200 | 5 200 | 10 000 | 0 | aucun |
| 4 | 150 | 16,32 | 5 700 | 9 100 | 11 000 | 0 | aucun (`palier4_failures.csv` vide) |

Détail `POST /predict` : palier 1 p50 96 / p95 470 / p99 950 ms ; palier 2 130 / 1 500 / 4 600 ms ; palier 3 1 200 / 5 200 / 10 000 ms ; palier 4 5 700 / 9 100 / 11 000 ms.

Seuil de rupture en latence : 3 × 430 = **1 290 ms**.

## Mesure 14 — Ligne de base réseau

| Ligne de base | Valeur |
|---|---|
| Établissement de connexion (`time_connect`), médiane sur 20 | **59,8 ms** |
| Part dans le p50 du palier 1 (92 ms) | ~65 % |

**Honnêteté de la mesure.** Une part importante de la latence des paliers bas n'appartient pas au service : c'est le trajet Montpellier → Allemagne. Les 65 % sont une **borne haute** : Locust réutilise ses connexions (keep-alive) et ne repaie pas l'établissement à chaque requête. Aux paliers hauts, cette part devient négligeable devant les secondes d'attente.

## Mesure 15 — Point de rupture

CPU et mémoire du plan (`az monitor metrics`, `PT1M`) :

| Palier | CPU | Mémoire |
|---|---|---|
| 1 | max 39 % | 77 % |
| 2 | max 66 % | 77-78 % |
| 3 | 77 → **100 → 100 %** | 78 % |
| 4 | 63 → **100 %** | 76 % |

| Conclusion | Réponse |
|---|---|
| Palier où le critère est franchi | **Palier 2** (p95 1 500 ms > 1 290 ms), par la latence, pas par les erreurs |
| Utilisateurs simultanés supportés | **Entre 10 et 30** |
| Débit maximal avant dégradation | **3,17 req/s** (palier 1, dernier palier conforme) ; plafond absolu observé ~16 req/s |
| Ressource qui sature en premier | **Le CPU** (1 vCPU, 100 % aux paliers 3 et 4) ; mémoire stable 74-78 % |
| `Http5xx` au palier le plus chargé | **0** (aucun échec Locust) |

**Lecture.** Le service ne plante jamais : il **fait la queue**. Un seul worker synchrone traite une requête à la fois sur un seul vCPU. Au-delà de la capacité, le débit plafonne (15,6 → 16,3 req/s pour deux fois plus d'utilisateurs) et toute la charge supplémentaire se transforme en attente. Avec 75 utilisateurs réfléchissant 3 s en moyenne, la demande approche 25 req/s ; le service en sert 16.

---

## Question 5.2 — p50 contre p99 au palier le plus chargé

Au palier 4, p50 = 5,7 s et p99 = 11 s : un écart **faible en proportion** (×2). Ce n'est pas une queue isolée, c'est une **saturation générale** : tout le monde attend. Le cas contraire s'observe au palier 2 (p50 120 ms, p99 4 400 ms, ×37) : la plupart des requêtes vont bien, quelques-unes souffrent. Pour un praticien au palier 4, le p99 (11 s) tombe dans 1 % des soumissions, mais la soumission **typique** prend déjà près de 6 s : l'outil est inutilisable en consultation, pas seulement « parfois lent ».

## Question 5.3 — Engagement de service

« **Jusqu'à 10 utilisateurs simultanés, 95 % des prédictions sont rendues en moins de 470 ms, avec moins de 1 % d'échecs.** »

Adossé au palier 1 (`POST /predict` : p95 470 ms, 0 % d'échec sur 452 prédictions). Je ne m'engage pas sur 30 utilisateurs : ce palier franchit déjà mon critère.

## Question 5.4 — Deux centres de plus, charge doublée

1. **Mise à l'échelle verticale (scale up)** : passer à un SKU plus gros (B2, B3, P1v3), donc plus de vCPU et de mémoire par instance.
2. **Mise à l'échelle horizontale (scale out)** : ajouter des instances au plan (`az appservice plan update --number-of-workers 2`), le répartiteur d'App Service distribuant le trafic.

Je testerais **le scale out en premier** : le CPU est la ressource saturée, ajouter une instance double le CPU disponible **et** apporte de la redondance (une instance qui tombe n'arrête plus le service). Mais avant de payer l'un ou l'autre, je corrigerais l'image : un seul worker Gunicorn synchrone n'exploite même pas correctement le vCPU dont il dispose. `--workers 2 --threads 4` est une piste gratuite à mesurer d'abord.

## Question 5.5 — Si le modèle était rechargé à chaque requête

Chaque requête paierait la lecture et la désérialisation du paquet `joblib`. L'effet serait le plus visible sur la **latence, dès le p50**, à tous les paliers : chaque appel s'allonge du temps de chargement, et sous charge ce temps augmente encore la file d'attente. Le débit aux paliers non saturés ne bougerait pas, car il est fixé par le nombre d'utilisateurs et leur temps de réflexion (10 utilisateurs qui attendent 1 à 5 s produisent ~3 req/s quoi qu'il arrive), pas par la vitesse du service. Le rechargement n'apparaîtrait sur le débit qu'au moment où il ferait saturer le service plus tôt.

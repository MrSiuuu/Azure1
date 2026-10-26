# Séance 3 — Observabilité et compte rendu d'incident

**Industrialisation de l'IA dans le Cloud · Ynov Montpellier · M2**
Auteur : Issa KOUYATÉ — 26/10/2026

---

## 4.1 — Ce que les logs laissent voir

Journalisation activée (`az webapp log config --docker-container-logging filesystem --application-logging filesystem --level information`), puis flux ouvert avec `az webapp log tail`. Trafic envoyé :

- 15:00:04 — `GET /health` → 200
- 15:00:05 — `GET /model/info` → 200
- 15:00:06 — `POST /predict` incomplet `{"age_approx": 55}` → **400**, « variables manquantes », 39 manquantes

### Mesure 9

| Observation | Relevé |
|---|---|
| Nom du conteneur en préfixe de chaque ligne ? | **Non.** Les lignes applicatives sont préfixées `ContainerStream:` (ou `[Previous Container]`). Le nom `…_dermascan-api-ik42` n'apparaît que dans les lignes de la plateforme |
| Ligne d'accès Gunicorn par requête ? | **Non, aucune.** Gunicorn n'écrit son journal d'accès qu'avec `--access-logfile`, absent du `CMD` de l'image S2 |
| Que journalise l'API sur un `/predict` incomplet ? | **Rien.** `app.py` ne contient aucun appel de journalisation ; le refus n'existe que dans la réponse HTTP |
| Liste des variables manquantes dans les logs ? | Non, seulement dans la réponse au client |
| Délai requête → apparition de la ligne | Sans objet : aucune ligne n'est apparue (« No new trace in the past 4 min(s) ») |
| Charge utile complète du POST dans les logs ? | **Non** — mais pas par choix de conformité : parce que rien n'est journalisé |

**Ce que le flux montre quand même** (journaux de démarrage) : `Using worker: sync` et un seul `Booting worker` → Gunicorn tourne avec **un seul worker synchrone** ; `Site startup probe succeeded after 44.98 seconds` ; l'activation des logs a **recyclé** le conteneur (arrêt à 13:56:39 UTC, grâce de 5 s, terminé en 6,7 s).

**Conséquence.** Un dermatologue pourrait soumettre mille lésions sans qu'il en reste une seule trace côté service. C'est le point de départ de la partie 6.

Archive complète : `logs_s3.zip` (33 781 octets).

---

## Compte rendu d'incident — démarrage impossible, port sondé vide

| Rubrique | Contenu |
|---|---|
| **Date** | 26/10/2026 |
| **Service** | `dermascan-api-ik42` (App Service, plan B1, `germanywestcentral`) |
| **Déclencheur** | Exercice : `WEBSITES_PORT=9999` puis `az webapp restart` à **15:03:39** |
| **Symptôme vu du client** | Plusieurs minutes **sans aucune réponse** (`000`, délai client de 60 s dépassé), puis **503** |
| **Ligne de log fautive** | voir ci-dessous |
| **Cause** | La plateforme sonde le port 9999 ; Gunicorn écoute sur 8000. L'application est saine, la porte est fausse |
| **Correction** | `WEBSITES_PORT=8000` par `appsettings set` à **15:17:03**, sans restart |
| **Retour au service** | Premier 200 à **15:20:08**, soit **3 min 05** |

### Mesure 10 — Diagnostic

Relevés côté client (`curl` toutes les 30 s, délai max 60 s) :

| Heure | Résultat |
|---|---|
| 15:03:54 | `000` (60 s) |
| 15:05:24 | `000` (60 s) |
| 15:06:54 | `000` (60 s) |
| 15:08:24 | `503` (19,9 s) |
| 15:09:14 | `000` (60 s) |
| 15:10:44 | `000` (60 s) |
| 15:12:14 | `000` (60 s) |
| 15:13:44 | `503` (0,31 s) |

| Élément | Relevé |
|---|---|
| Code HTTP vu par le client | D'abord des délais dépassés (`000`), puis **503** une fois la plateforme ayant abandonné |
| Délai avant la réponse d'erreur | 503 définitif à 15:13:44, ~10 min après le restart ; ensuite immédiat (0,31 s) |
| Ligne de log exacte | voir ci-dessous |
| Tentatives de la plateforme | **Une** sonde de démarrage de **230 s**, puis abandon (`Retry count = 0`) |
| Le processus applicatif a-t-il démarré ? | **Oui** : `Starting gunicorn 26.2.0` / `Listening at: http://0.0.0.0:8000` à 14:09:31 UTC |
| Restart → ligne fautive | 15:03:39 → 15:13:22, ~9 min 43 (conteneur démarré à 15:09:31, puis 230 s de sonde) |

**Ligne fautive, recopiée intégralement :**

```
2026-10-26T14:13:22.6104200Z State: Stopping, Action: CancellingStartup, LastError: ContainerTimeout, LastErrorTimestamp: 10/26/2026 14:13:20, LastErrorDetails: Container did not respond to startup probe on port 9999 within the expected time limit of 230s. Port mismatch detected: the container is listening on port 8000 but the platform is probing port 9999. Set the WEBSITES_PORT app setting to match the port your application listens on. If your application needs more time to start, increase WEBSITES_CONTAINER_START_TIME_LIMIT. Please inspect your container logs for more details as this could indicate an issue with your application., Details: Site container: dermascan-api-ik42 terminated during site startup. Cancelling site startup., DetailsLevel: ERR
```

Capture : `captures/incident_port.png`.

### Mesure 11 — Retour au service

| Élément | Relevé |
|---|---|
| Correction → premier 200 | **3 min 05** (15:17:03 → 15:20:08 ; `000` à 15:17:34, 15:18:14, 15:18:54, 15:19:34) |
| Redémarrage explicite nécessaire ? | **Non** : l'`appsettings set` recycle le conteneur, la plateforme a repris seule |

---

## Question 4.1 — Même 503, deux causes

Rappel de la panne 1 (partie 2.2, avant l'octroi d'AcrPull), retrouvée dans `logs_s3.zip` :

```
2026-10-26T13:26:13.9861812Z State: Stopping, Action: CancellingStartup, LastError: ImagePullUnauthorizedFailure, LastErrorTimestamp: 10/26/2026 13:26:13, LastErrorDetails: Failed to pull image: acrdermascanik42.azurecr.io/dermascan-api:1.0.0. Image pull failed with forbidden or unauthorized. Check registry credentials., Details: Site container: dermascan-api-ik42 terminated during site startup. Cancelling site startup., DetailsLevel: ERR
```

1. **Vu du client** : rien de fiable ne les distingue. Les deux finissent en 503 avec la même page générique. Seul indice, l'attente : la panne 1 a répondu 503 en 0,3 s (le pull échoue en 2 s), la panne 2 a laissé le client sans réponse plusieurs minutes. Mais cet indice dépend du moment où l'on interroge.
2. **Dans les logs**, tout les distingue :
   - panne 1 : `LastError: ImagePullUnauthorizedFailure … Image pull failed with forbidden or unauthorized` — le conteneur **n'a jamais démarré**, l'image n'a pas été téléchargée ;
   - panne 2 : `LastError: ContainerTimeout … Port mismatch detected: the container is listening on port 8000 but the platform is probing port 9999` — le conteneur **a démarré**, Gunicorn tournait.
3. **Conclusion** : un code HTTP décrit un **symptôme**, pas une cause. Un 503 dit « je ne peux pas servir », jamais pourquoi. Diagnostiquer à partir du code mène à corriger la mauvaise chose (ici, toucher aux droits du registre alors que le problème est un port). Seule la ligne de log discriminante permet de conclure.

---

## 4.3 — Métriques de plateforme

### Mesure 12 — Agrégat sur l'heure écoulée (`--interval PT1H`)

| Métrique | Relevé |
|---|---|
| Nombre total de requêtes | 71 |
| Nombre de réponses 5xx | 15 |
| Temps de réponse moyen | **41,9 s** |

Une prédiction normale prend ~0,2 s. Ces 41,9 s sont tirés vers le haut par les requêtes restées bloquées pendant la panne et les démarrages à froid. Cette moyenne ne décrit l'expérience d'**aucun** utilisateur réel.

## Question 4.2 — Ces métriques suffisent-elles ?

Non : il faut des **percentiles**. Une moyenne agrège des requêtes de 0,1 s et de 60 s en un chiffre que personne n'a vécu ; la partie 5 le montre, avec un p50 à 92 ms et un p99 à 940 ms au même palier, ou un p95 qui franchit le seuil alors que la médiane reste correcte.

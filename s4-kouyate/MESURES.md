# MESURES — Séance 4 · Évaluation, substitution, service

**Issa KOUYATÉ** — M2 Data Engineering · Ynov Campus Montpellier
Module : Industrialisation de l'IA dans le Cloud · 2026-2027 · Séance du 29 octobre 2026

Tous les chiffres viennent de `sorties/predictions_validation.csv`, `model/modele_meta.json`, et des commandes lancées sur mon poste (WSL2 Ubuntu 22.04) et sur Azure.

---

# Partie 4 — Évaluation et recalibration

## Mesure 11 — Matrice au seuil

Seuil choisi par `seuil_pour_rappel`, sur la validation, pour un rappel d'au moins **90 %**. Décision recalculée avec `p >= meta["seuil"]` sur le CSV.

| | Prédit `a_examiner` | Prédit `surveillance` |
|---|---|---|
| **Malin** | VP = **46** | FN = **6** |
| **Bénin** | FP = **1 670** | VN = **2 414** |

| Contrôle | Ma valeur |
|---|---|
| Somme des quatre cases | 4 136 = nombre de vignettes de validation ✅ |
| Identique au meta ? | **Non, à une lésion près** : le meta donne VP 47 / FN 5 |

### Question 4.1 — La lésion d'écart

La lésion dont le score est le plus proche du seuil est une **maligne** : son score relu dans le CSV vaut `0.0001582277713871`, le seuil vaut `0.00015822777138716095`, soit un écart de **−6 × 10⁻¹⁷**. Elle passe juste sous le seuil et devient un faux négatif.
`precision_recall_curve` prend comme seuils candidats les scores des lésions eux-mêmes : le seuil retenu est donc **exactement** le score d'une lésion, ici la dernière maligne nécessaire pour atteindre 90 % de rappel. Le CSV écrit ce flottant en décimal avec un nombre fini de chiffres ; relu, il est arrondi au dernier bit, et la comparaison `>=` bascule. Une lésion « pile sur le seuil » ne survit pas à un aller-retour par un fichier texte.

## Mesure 12 — Métriques au seuil

| Métrique | Formule | Ma valeur |
|---|---|---|
| Rappel | VP / (VP + FN) = 46 / 52 | **88,5 %** (90,4 % dans le meta, avec VP = 47) |
| Précision en validation | VP / (VP + FP) = 46 / 1 716 | **2,68 %** |
| Taux de faux positifs | FP / (FP + VN) = 1 670 / 4 084 | **40,9 %** |
| Part des lésions envoyées en examen | (VP + FP) / N = 1 716 / 4 136 | **41,5 %** |

Tableau de seuils, sur `proba_brute` :

| Seuil sur `proba_brute` | VP | FP | Rappel | Précision |
|---|---|---|---|---|
| 0,5 | 7 | 19 | 13,5 % | 26,9 % |
| 0,1 | 24 | 148 | 46,2 % | 14,0 % |
| 0,05 | 27 | 260 | 51,9 % | 9,4 % |
| `seuil_brut` du meta (0,001716) | 46 | 1 670 | 88,5 % | 2,7 % |
| 0,01 | 39 | 737 | 75,0 % | 5,0 % |

### Question 4.2 — Le seuil de 0,5

Non : il laisse partir **45 malignes sur 52** en surveillance (rappel 13,5 %). 0,5 n'a de sens que pour un modèle calibré sur une population à classes équilibrées ; ici le réseau a appris sur 1,45 % de positifs, ses probabilités brutes sont presque toutes très basses, et 0,5 n'est qu'une convention. Le seuil se choisit sur le rappel visé, pas par habitude.

## Mesure 13 — Recalibration

β = 20 000 / 217 183 (négatifs tirés / négatifs de l'archive).

| Grandeur | Mon calcul | Valeur du meta |
|---|---|---|
| β | 0,092088 | `taux_negatifs` : 0,092088 |
| ln β | −2,3850 | `correction_logit` : −2,3850 |
| Seuil brut | — | `seuil_brut` : 0,0017155 |
| Seuil recalibré σ(logit(seuil brut) + ln β) | 0,00015823 | `seuil` : 0,00015823 |
| Décisions de validation changées par la recalibration | **0** | — |
| Précision projetée sur le flux réel | 0,00292 (avec mon rappel de 88,5 %) | 0,00298 |
| Lésions examinées par maligne trouvée | 342 | **335** |
| Même grandeur, modèle tabulaire de S2 | **198** | — |

π = 0,135 % (`prevalence_reelle`), TFP = 40,9 %. L'écart avec le meta vient de la lésion de la question 4.1.

### Question 4.3 — À quoi sert une recalibration qui ne change aucune décision

Elle ne change ni l'ordre des lésions, ni les décisions, ni la PR-AUC : elle change **le sens du nombre** renvoyé.
- **Pour le dermatologue** : `probabilite_maligne` doit pouvoir se lire comme un risque réel. Sans correction, le réseau surestime les cotes d'un facteur 1/β ≈ 11, puisqu'il a vu 11 fois plus de malignes que la réalité. L'image de contrôle vaut 0,35 une fois recalibrée ; la valeur brute serait bien plus haute et ferait croire à une quasi-certitude.
- **Pour l'analyste de S5** : il comparera la distribution des probabilités servies à celle de la validation. Il faut que les deux soient sur la même échelle (recalibrée), et il saura que la correction dépend de la prévalence : si celle du flux change, c'est `correction_logit` qu'il faut revoir.

### Question 4.4 — Deux erreurs de déploiement

| Erreur | Part envoyée en examen | Rappel |
|---|---|---|
| 1. L'API sert `proba_brute` mais applique le seuil recalibré | 73,2 % | 100 % |
| 2. L'API sert la probabilité recalibrée mais applique le seuil brut | 13,3 % | **73,1 %** |

La plus dangereuse pour un patient est la **seconde** : elle laisse partir 14 malignes sur 52 en surveillance (au lieu de 5), en silence, avec une charge de travail réduite qui a l'air d'un progrès. La première surcharge les dermatologues (trois lésions sur quatre à examiner) mais ne rate aucun cancer : coûteuse, visible, pas dangereuse.

### Question 4.5 — Si l'on avait pondéré les positifs

Pondérer les positifs d'un facteur w multiplie aussi les cotes apprises par w : il faudrait ajouter **−ln w** au logit, soit `σ(logit + ln β − ln w)`.

## Mesure 14 — PR-AUC ramenées à une même prévalence

| PR-AUC | Valeur | Hasard (prévalence) |
|---|---|---|
| S4, validation sous-échantillonnée (meta) | 0,210 | 0,0126 |
| S4, négatifs repondérés par 1/β | **0,094** | 0,0012 |
| S2, flux réel (mon `MESURES.md`) | 0,054 | 0,0013 |

ROC-AUC S4 : 0,8779 avant repondération, 0,8779 après.

### Question 4.6 — Deux PR-AUC qui ne se comparent pas

La PR-AUC repose sur la précision, VP / (VP + FP) : multiplier le nombre de négatifs multiplie les FP, donc elle baisse quand la prévalence baisse. La ROC-AUC repose sur deux taux calculés **dans** chaque classe (rappel et taux de faux positifs) : changer la proportion des classes ne les change pas. Vérifié : 0,8779 avant et après repondération.

Conclusion honnête : à prévalence égale, le CNN passe de 0,054 à 0,094, soit environ 75 fois le hasard contre 40. Mais les deux validations ne portent ni sur les mêmes lésions (archive Permissive contre jeu complet), ni sur les mêmes patients, ni sur le même nombre de malignes (52 contre 110) : avec 52 positifs, l'incertitude sur 0,094 est large. Et au point de fonctionnement qui compte (rappel 90 %), le CNN demande **335 lésions examinées par maligne trouvée, contre 198** pour le modèle tabulaire. Je ne peux pas conclure que le CNN fait mieux : il classe un peu mieux en moyenne, mais il est plus coûteux au seuil clinique retenu.

---

# Partie 5 — Une seule pièce changée

## 5.1 — Copie de l'API

`api-s4/` contient le `Dockerfile`, le `.dockerignore` de S2, `app.py` et `requirements.txt` distribués, et `model/modele.pt` + `model/modele_meta.json`. Le manifeste ne va pas dans l'image.

**Écart avec l'énoncé.** Mon Dockerfile de S2 n'est pas celui que l'énoncé suppose : il part de `python:3.14.0-slim-bookworm` et copie le modèle par son nom (`COPY model/modele.joblib`).
1. La substitution a d'abord touché **deux lignes** : `MODEL_PATH=model/modele.pt` et ce `COPY`, qui doit aussi embarquer `modele_meta.json` (l'API lit le meta à côté du modèle). `diff` : uniquement ces deux lignes.
2. Cette image a échoué à la porte de sécurité (mesure 15 : 150 CVE, toutes dans la base Debian). Je suis donc passé à la base **Wolfi** (`cgr.dev/chainguard/wolfi-base` + `python-3.12`), avec `pip` désinstallé dans le même `RUN` que l'installation. L'ordre des couches, l'utilisateur non root (uid 10001) et le `CMD` gunicorn restent ceux de S2.

### Question 5.1 — Le diff de `app.py`

1. **Chargement du modèle** : au lieu de `joblib.load` d'un pipeline, on construit un ResNet18 vide, on y charge `modele.pt`, et on lit `modele_meta.json` à côté (seuil, normalisation, correction).
2. **Entrée de `/predict`** : un fichier image en multipart (champ `image`) au lieu d'un JSON de 40 variables ; l'API la redimensionne à 128 px et la normalise comme à l'entraînement.
3. **Correction de prior** : `ln β` est ajouté au logit avant la sigmoïde, pour renvoyer une probabilité à la prévalence réelle.
4. **`/model/info`** : renvoie l'architecture, la taille d'entrée, l'échantillonnage, les deux prévalences et `sha256_poids` au lieu des colonnes attendues.

Ce qui ne change pas : les trois routes (`/health`, `/model/info`, `/predict`), les codes (200, 400 pour une requête invalide, 503 sans modèle) et les clés de la réponse (`probabilite_maligne`, `seuil`, `decision`, `rappel_cible`, `version_modele`). Un poste de consultation qui appelle déjà l'API garde son code de lecture de la réponse ; seul l'envoi change.

Une différence à signaler : la valeur négative de `decision` passe de `non_prioritaire` (S2) à `surveillance` (S4). Un client qui teste cette chaîne casserait : c'est une raison de plus pour le tag majeur 2.0.0.

### Question 5.2 — `weights=None` et `weights_only=True`

- `resnet18(weights=None)` construit le réseau **sans télécharger** les poids ImageNet au démarrage : ils seraient immédiatement écrasés par `modele.pt`, et le conteneur dépendrait d'un serveur extérieur pour démarrer. Prouvé par la mesure 16 : démarrage sous `--network none`.
- `torch.load(..., weights_only=True)` : un fichier `.pt` est un pickle, et un pickle peut exécuter du code au chargement. `weights_only` n'accepte que des tenseurs et des structures simples : un fichier de poids piégé ne peut pas exécuter de code dans le conteneur.

### Question 5.3 — Multipart plutôt que base64 dans du JSON

1. **Taille et coût** : base64 grossit l'image d'un tiers, et il faut encoder côté client puis décoder côté serveur, en gardant toute la chaîne en mémoire. Le multipart transporte les octets tels quels.
2. **Standard** : c'est le format natif de l'envoi de fichiers (`curl -F`, formulaires, bibliothèques HTTP), lu en flux par Flask (`request.files`).

## Mesure 15 — Construction et scan

| Relevé | Ma valeur |
|---|---|
| Durée de construction à froid | 72,9 s (base Debian de S2) · **72,5 s** (base Wolfi, image livrée) |
| Taille de l'image S4 (`docker images`) | 1,2 Go (Debian) · **1,13 Go** (Wolfi, 432 Mo compressée selon scout) |
| Taille de l'image S2 | 653 Mo (relevée en S2 ; image supprimée du poste en fin de S2) |
| `docker scout cves`, base Debian de S2 | **8 C / 51 H / 38 M / 53 L**, 150 CVE dans 24 paquets, code retour **2** → **non poussée** |
| `docker scout cves`, base Wolfi | **0 C / 0 H / 0 M / 0 L**, code retour **0** |
| Exceptions écrites | Aucune |

Les 150 CVE venaient toutes de la base Debian (perl, openssl, gnutls, glibc, util-linux…) sauf 6 dans `pip`, et une partie est marquée « not fixed » : aucune mise à jour de la base Debian n'aurait permis d'atteindre zéro. Preuves : `captures/04_docker_scout_s2base.png`, `captures/05_docker_scout_wolfi.png`.

## Mesure 16 — Démarrage hors ligne et concordance

| Relevé | Ma valeur |
|---|---|
| Délai jusqu'au premier `/health` à 200, sous `--network none` | **≈ 5 s** (12:29:30 → 12:29:35) |
| Corps de `/health` | `{"hostname":"a27440692cd0","model_loaded":true,"service":"isic-vignettes-api","status":"ok","uptime_seconds":0.4}` |
| Servi pour l'image de contrôle `ISIC_0699524` | `probabilite_maligne` **0,352667**, `decision` **a_examiner** |
| `controle.probabilite_maligne` du meta, écart absolu | 0,352668 · écart **1 × 10⁻⁶** < 10⁻⁵ ✅ |
| Codes HTTP : sans champ image / fichier qui n'est pas une image | **400** / **400** |

Preuve : `captures/06_predict_local.png`.

### Question 5.4 — Un autre filtre de redimensionnement

L'API redimensionnerait les pixels un peu autrement que ce que le réseau a vu à l'entraînement : chaque probabilité serait légèrement fausse, aucune erreur ne serait levée, les codes HTTP resteraient à 200. C'est un écart entraînement / service silencieux. Seule une comparaison de bout en bout, une image connue, une probabilité attendue et une tolérance (la mesure 16), le révèle.

## Mesure 17 — Comparatif S2 / S4

| Grandeur | S2 (mon `MESURES.md`) | S4 |
|---|---|---|
| Taille de l'image | 653 Mo | 1,13 Go |
| Taille du fichier de modèle | 9,5 Ko | 44,8 Mo |
| Durée de construction à froid | 118,5 s | 72,5 s |
| Démarrage jusqu'au premier `/health` à 200 | non relevé en S2 | ≈ 5 s (local, hors ligne) · 2 min 02 s sur Azure B1 |
| Mémoire du conteneur au repos | non relevée en S2 | 297 Mio |
| Latence `/predict` p50 / p95, local | 42,2 ms médiane (10 appels, Docker Desktop Windows, p95 non relevé) | **19,6 / 24,9 ms** (50 appels, WSL2) |
| Latence du réseau seul, lot de 1 (mesure 9) | — | 29,3 / 34,2 ms (CPU Colab) |
| Architecture du poste | amd64 natif | amd64 natif |

Les latences locales S2 et S4 ne sont pas mesurées dans les mêmes conditions (moteur Docker, nombre d'appels) : je ne les compare pas directement. Ce qui ressort : le modèle pèse 4 700 fois plus lourd, mais l'image seulement 1,7 fois ; comme en S2, ce sont les bibliothèques (torch) qui font la taille de l'image.

### Question 5.5 — Lésions par heure pour un worker

Un worker synchrone traite une requête à la fois : à 19,6 ms au p50, il sert au mieux 1 000 / 19,6 ≈ **51 lésions par seconde**, soit environ **184 000 par heure**, en local. C'est un plafond optimiste pour le B1 : sa vCPU est plus lente que mon poste, chaque requête traverse le réseau, et sous charge les requêtes font la queue derrière le même worker. Sur Azure, j'ai mesuré 120 ms au p50 dès 10 utilisateurs.

## 5.5 — Azure

**Incident.** `az appservice plan create` en `germanywestcentral` (la région du registre) a été refusé quatre fois (12:36, 12:43, 12:45, 12:50) :

> App Service Plan Create operation is throttled for subscription fec0c6a0-752a-453e-95fc-4c30318138e4.

Essai en `francecentral` : `RequestDisallowedByAzure`. La policy de l'abonnement Azure for Students n'autorise que cinq régions : germanywestcentral, switzerlandnorth, italynorth, spaincentral, polandcentral. Plan créé avec succès en **`switzerlandnorth`** ; le groupe et le registre restent en Allemagne, l'app tire l'image d'une autre région. Le reste de la routine de S3 est inchangé.

Valeurs décidées :
- `a_detruire` = `2026-10-29` (groupe détruit en fin de séance)
- SKU = **B1** (celui de S3, pour comparer)
- `WEBSITES_PORT` = 8000
- `WEBSITES_CONTAINER_START_TIME_LIMIT` = **600 s** : torch se charge lentement sur un vCPU, 600 s laissent une large marge sans approcher la limite de 1 800 s
- Rôle = **AcrPull** (lecture seule sur le registre, rien de plus)

## Mesure 18 — Le service S4 en ligne

| Relevé | Ma valeur |
|---|---|
| Durée du `docker push`, taille | **48,8 s** (S2 : 121,6 s) · image de 432 Mo compressée · digest `sha256:b4885c210f64f5e2655877a0b1fc54b5e38ffcedf1a6c4eab171d91fc1ae6e94` |
| Tags dans `dermascan-api` | 1.0.0, 2.0.0 |
| Restart → premier 200 sur `/health` | **2 min 02 s** (12:56:11 → 12:58:13) |
| Servi sur Azure pour l'image de contrôle | `probabilite_maligne` **0,352668**, `decision` **a_examiner** (identique au meta) |
| `/model/info` | `version` 2.0.0 · `version_deployee` 2.0.0 |

Preuve : `captures/07_predict_azure.png` (URL `https://dermascan-api-s4-ik42.azurewebsites.net`).

## Mesure 19 — Charge sur le service S4

`locustfile_s4.py` : `wait_time = between(1, 5)` comme en S3 ; poids `/predict` 10, `/health` 1, `/model/info` 1 ; paliers 10 et 30 utilisateurs (mes paliers 1 et 2 de S3), 3 minutes chacun, montée 5/s.

| Palier | Utilisateurs | Débit (req/s) | p50 (ms) | p95 (ms) | p99 (ms) | Échecs (%) |
|---|---|---|---|---|---|---|
| 1 (Azure) | 10 | 3,13 | 120 | 590 | 1 400 | 0 |
| 2 (Azure) | 30 | 8,57 | 220 | 1 500 | 5 200 | 0 |
| S3, palier à 10 utilisateurs | 10 | 3,17 | 92 | — | — | 0 |

Détail `POST /predict` :

| Palier | p50 | p95 | p99 |
|---|---|---|---|
| S4, 10 utilisateurs | 120 | 610 | 1 400 |
| S3, 10 utilisateurs | 96 | 470 | 950 |
| S4, 30 utilisateurs | 230 | 1 500 | 5 500 |
| S3, 30 utilisateurs | 130 | 1 500 | 4 600 |

Complément, avant de trouver la région : un palier à 10 utilisateurs contre le conteneur local (`palier_s4_local_1`, réseau non traversé) donne 3,35 req/s, p50 23 ms, p95 40 ms, p99 56 ms, 0 % d'échec.

### Question 5.6 — S4 contre S3 à usage égal

À 10 utilisateurs, le p50 de `/predict` passe de 96 ms (S3) à 120 ms (S4), et le p95 de 470 à 610 ms. Le relevé qui l'explique : la **latence `/predict`** et celle du **réseau seul** (mesures 9 et 17) : un passage de ResNet18 coûte ~20 à 30 ms de CPU, contre une fraction de milliseconde pour la régression logistique, et chaque requête transporte une image. S'y ajoute ici un trajet vers la Suisse au lieu de l'Allemagne.
Mon engagement de S3 (« jusqu'à 10 utilisateurs, 95 % des prédictions en moins de 470 ms ») **ne tient plus** sur le même plan B1 : 610 ms. Il faut soit l'abaisser, soit un plan plus gros, soit un modèle optimisé (séance 5).

---

# Partie 7 — Nettoyage et extinction

## Mesure 21 — Contrôles de fin de séance

| Contrôle | Mon observation |
|---|---|
| Ressources dans `$RG` avant destruction | `plan-dermascan-s4-ik42` (serverFarms) et `dermascan-api-s4-ik42` (sites), en switzerlandnorth |
| `az group exists --name rg-dermascan-s4-ik42` | **false** |
| `az group exists --name rg-dermascan-registre-ik42` | **true** |
| Tags dans le registre après nettoyage | 1.0.0, 2.0.0 |
| Point de reprise supprimé du Drive, session Colab terminée | Oui : `reprise.pt` supprimé par `entrainer.py` en fin d'entraînement, seul `paquet_modele_s4.zip` reste sur le Drive ; environnement d'exécution déconnecté et supprimé |
| Local | `docker ps -a` : aucun conteneur de la séance · alias du registre supprimé · `dermascan-api:2.0.0` conservée pour S5 |
| Crédit restant (Cost Management) | **86 € sur 88 €** · coûts d'octobre **3,37 €** · expiration 06/10/2027 |
| Écart avec S3 | En S2 : 88 € et 0,40 € de coûts. Les ~3 € couvrent le registre Basic depuis trois semaines et les plans B1 de S3 et S4, détruits le jour même |

L'attribution AcrPull a été supprimée avant le groupe, tant que l'identité de l'app existait.

### Question 7.1 — Pourquoi la garde `case`

En S3, un seul groupe était détruit et l'erreur de cible était peu probable. Aujourd'hui, l'abonnement porte plusieurs groupes dont un, `rg-dermascan-registre-ik42`, ne doit jamais être détruit : il contient les images 1.0.0 et 2.0.0 que S5 et le projet réutilisent. Si `$RG` avait été écrasé par une valeur restée dans un vieux terminal (par exemple celle du registre), `az group delete --yes --no-wait` le détruirait sans demander. La garde refuse tout groupe qui ne commence pas par `rg-dermascan-s4-`.

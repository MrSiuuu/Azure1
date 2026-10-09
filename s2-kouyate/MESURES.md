# MESURES — Séance 2 · Du modèle à l'API d'inférence

**Issa KOUYATÉ** — M2 Data Engineering · Ynov Campus Montpellier
Module : Industrialisation de l'IA dans le Cloud · 2026-2027
Séance du 9 octobre 2026 · Poste : Windows · PowerShell

Tous les chiffres sortent de `python entrainer.py`, lancé sur mon poste
(Python 3.14.0, scikit-learn 1.9.1, pandas 3.0.6, graine 42).

---

## Tableau de décisions

| Décision | Ma valeur |
|---|---|
| Suffixe personnel, identique à la séance 1 | `ik42` |
| Groupe portant le registre, créé en séance 1 | `rg-dermascan-registre-ik42` |
| Registre ACR de la séance 1 | `acrdermascanik42` |
| Rappel visé, décidé avant de voir le moindre résultat | **90 %** |
| Date portée par l'étiquette `a_detruire` | `2027-09-30` |

---

# Partie 2 — Pipeline scikit-learn

## Mesure 6 — Découpage

Découpage par patient avec `GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=42)`.
Contrôle par comptage : aucun patient en commun entre les deux ensembles.

| Relevé | Entraînement | Test |
|---|---|---|
| Nombre de lignes | 319 514 | 81 545 |
| Nombre de patients | 833 | 209 |
| Nombre de positifs | 283 | 110 |
| Taux de positifs | 0,0886 % | 0,1349 % |

### Question 2.1 — Les deux taux de positifs sont-ils identiques ?

Non : 0,0886 % à l'entraînement contre 0,1349 % au test. `GroupShuffleSplit` tire des
patients au hasard sans chercher à équilibrer les malignes. Le test contient 20 % des
patients mais 110 des 393 malignes, soit 28 %. Avec si peu de positifs, quelques patients
qui portent plusieurs malignes suffisent à déplacer le taux. Conséquence : mes scores
reposent sur 110 cas, chaque maligne trouvée ou ratée pèse 0,9 point de rappel, et une
autre graine donnerait d'autres patients au test, donc d'autres scores. Un seul découpage
donne un ordre de grandeur, pas une valeur stable ; il faudrait répéter sur plusieurs
graines pour connaître la marge.

## Pipeline retenu

| Colonnes | Étapes |
|---|---|
| 35 numériques | imputation par la médiane, puis `StandardScaler` |
| 5 catégorielles | imputation par la valeur la plus fréquente, puis `OneHotEncoder(handle_unknown="ignore")` |
| Modèle | `LogisticRegression(max_iter=1000, class_weight="balanced")` |

### Question 2.2 — `handle_unknown` : une position anatomique jamais vue arrive

Avec `"error"`, l'encodeur lève une `ValueError` : l'API répond une erreur et la lésion
n'est pas triée du tout. Avec `"ignore"`, la variable est codée par des zéros et la
prédiction se fait avec les 39 autres variables. Je retiens `"ignore"` : pour un service
de tri, une lésion sans réponse est pire qu'une réponse calculée sans une variable. La
contrepartie est que ce cas passe en silence ; il faudrait le journaliser pour savoir
qu'une nouvelle valeur circule.

### Question 2.3 — Pourquoi l'imputation est-elle une étape du pipeline ?

Calculée sur le tableau complet avant le découpage, la médiane serait calculée aussi avec
les lignes du test : de l'information des patients de test entrerait dans le modèle, et
l'évaluation ne se ferait plus sur des données jamais vues.

## Mesure 7 — Comparaison des deux modèles, sur le test

| Modèle | Exactitude | ROC-AUC | PR-AUC |
|---|---|---|---|
| DummyClassifier | 99,8651 % | 0,5000 | 0,0013 |
| Régression logistique | 84,9175 % | 0,9097 | 0,0542 |
| Valeur du hasard pour la PR-AUC | — | — | 0,0013 |

### Question 2.4 — Lequel est le meilleur ?

Selon l'exactitude seule, c'est le DummyClassifier : 99,87 % contre 84,92 %. En réalité
c'est la régression logistique : au seuil 0,50 elle trouve 90 des 110 malignes, alors que
le Dummy n'en trouve aucune. L'exactitude compte les bonnes réponses sans regarder
lesquelles. Les 110 cancers ratés par le Dummy ne lui coûtent que 0,13 point, tandis que
les 12 279 fausses alertes de la régression lui coûtent 15 points. Elle compte les
bénignes bien classées, qui sont 1 000 fois plus nombreuses ; elle ne compte pas le fait
qu'une maligne ratée est l'erreur grave.

### Question 2.5 — PR-AUC du hasard et intérêt face à la ROC-AUC

Vérification : le taux de positifs du test est 110 / 81 545 = 0,1349 %, soit 0,0013, et
la PR-AUC du Dummy vaut bien 0,0013. Mon modèle obtient 0,0542, soit environ 40 fois le
hasard.

La ROC-AUC utilise le taux de faux positifs, c'est-à-dire les fausses alertes divisées
par toutes les bénignes. Avec 81 435 bénignes, des milliers de fausses alertes restent un
petit pourcentage, et le score paraît excellent (0,91). La PR-AUC utilise la précision,
c'est-à-dire la part de vraies malignes parmi les alertes : elle montre directement que
presque toutes les alertes sont fausses (0,054). C'est la question que se pose le
dermatologue.

## Mesure 8 — Compromis rappel / précision

| Seuil | Rappel | Précision | Vrais positifs | Faux positifs | Faux négatifs | Alertes pour 1000 lésions |
|---|---|---|---|---|---|---|
| 0,50 | 81,82 % | 0,73 % | 90 | 12 279 | 20 | 151,7 |
| 0,80 | 61,82 % | 1,55 % | 68 | 4 308 | 42 | 53,7 |
| 0,90 | 47,27 % | 2,17 % | 52 | 2 339 | 58 | 29,3 |
| 0,99 | 18,18 % | 4,94 % | 20 | 385 | 90 | 5,0 |

## Mesure 9 — Seuil retenu et son coût

| Relevé | Ma valeur |
|---|---|
| Rappel visé, décidé en début de séance | 90 % |
| Seuil correspondant | 0,347616 |
| Précision à ce seuil | 0,5062 % |
| Nombre de lésions examinées par maligne trouvée | 198 |
| Faux négatifs restants | 11 sur 110 |

À ce seuil : 99 vrais positifs, 19 457 faux positifs, 239,8 alertes pour 1 000 lésions.

Limite de méthode : le seuil est réglé sur le même ensemble de test que celui qui sert à
mesurer. Le rappel de 90 % y est donc atteint par construction ; sur de nouveaux patients
il sera un peu différent. Un troisième ensemble (validation) aurait permis de le vérifier.

### Question 2.6 — Présentation au médecin-chef

« Sur 1 000 lésions photographiées, le service en écarte 760 et vous en signale 240.
Parmi celles qu'il signale, une sur 198 est maligne. Il retrouve 9 malignes sur 10 ; la
dixième n'est pas signalée. Sans le service, il faut relire toutes les lésions, soit une
maligne pour 741 : la charge par cancer trouvé est divisée par un peu moins de quatre. »

S'il juge 198 inacceptable, je lui réponds qu'il y a deux leviers et que le premier est
sa décision, pas la mienne. Soit on baisse le rappel visé : au seuil 0,50, c'est une
maligne pour 137 lésions examinées et 152 alertes pour 1 000, mais on rate 18 malignes
sur 100 au lieu de 10. Soit on améliore le modèle pour gagner en précision à rappel égal,
par exemple avec les images en séance 4. Je ne déplace pas le seuil de moi-même.

### Question 2.7 — Ce que le service promet

Le service signale 9 lésions malignes sur 10 ; il ne garantit pas qu'une lésion non
signalée soit bénigne.

## Mesure 10 — Paquet produit

| Relevé | Ma valeur |
|---|---|
| Taille du fichier `model/modele.joblib` | 9,5 Ko |
| Nombre de colonnes attendues déclarées | 40 |
| Durée de l'entraînement | 13,6 s |

Contenu du paquet : pipeline, version `1.0.0`, colonnes attendues, seuil, rappel cible,
métriques, prévalence d'entraînement (0,0886 %), date d'entraînement, versions des
bibliothèques.

### Question 2.8 — À quoi sert `prevalence_entrainement` ?

Elle sert de point de référence. En séance 5, on comparera le flux reçu en production à
ce que le modèle a connu : s'il a appris sur 0,0886 % de malignes et que le taux d'alertes
ou de malignes confirmées s'en écarte nettement, la population a changé, et le seuil
comme la précision annoncés ne tiennent plus. Sans cette valeur dans le paquet, il n'y
aurait rien à quoi comparer.

### Question 2.9 — Deux conséquences de l'absence de `colonnes_attendues`

1. L'API ne peut pas valider la charge reçue : un champ manquant ferait planter le
   pipeline et produirait une erreur 500, au lieu d'un 400 qui nomme ce qui manque.
2. L'API ne sait pas quelles colonnes présenter au pipeline, ni dans quel ordre, et
   `/model/info` ne peut pas dire au client ce qu'il doit envoyer.

---

# Partie 3 — API d'inférence

### Question 3.1 — Latence ajoutée si le modèle était rechargé à chaque requête

J'ai chronométré `joblib.load` sur mon paquet de 9,5 Ko (mesure 10) : **2,3 ms**. Ma
latence médiane étant de 20 ms, recharger le modèle à chaque appel ajouterait environ
11 % à chaque requête, pour relire un fichier qui n'a pas changé. Le coût est faible ici
parce que le modèle est minuscule ; il est proportionnel à la taille du paquet, et se
compterait en secondes pour un modèle de plusieurs centaines de Mo.

## Mesure 11 — Réponses de l'API

Relevées avec `tester_api.py`, d'abord sur `python app.py`, puis sur le conteneur :
mêmes réponses dans les deux cas.

| Appel | Code HTTP | Élément relevé |
|---|---|---|
| `GET /health` | 200 | `model_loaded` = `true` |
| `GET /model/info` | 200 | 40 colonnes attendues |
| `POST /predict`, charge valide | 200 | `probabilite_maligne` = 0,750193 · `decision` = `a_examiner` |
| `POST /predict`, charge incomplète | 400 | 3 variables manquantes signalées (`age_approx`, `sex`, `anatom_site_general`) |
| `POST /predict`, corps vide | 400 | `corps JSON vide ou invalide` |

La charge valide (`charge.json`) est une lésion maligne réelle de mon jeu de test : elle
est bien signalée.

## Mesure 12 — Latence de dix appels successifs sur charge valide

| Contexte | Minimum | Médiane | Maximum |
|---|---|---|---|
| `python app.py` sur le poste | 14,9 ms | 20,0 ms | 25,0 ms |
| Conteneur (gunicorn, Docker Desktop) | 39,3 ms | 42,2 ms | 47,3 ms |

Piège rencontré : ma première mesure donnait 2 060 ms de médiane. Même `/health`
mettait 2 secondes, donc le modèle n'y était pour rien. Sous Windows, `localhost` est
d'abord résolu en IPv6, l'API n'écoute qu'en IPv4, et chaque appel perdait 2 secondes
avant de basculer. En appelant `127.0.0.1`, la latence réelle apparaît.

### Question 3.2 — Pourquoi renvoyer `decision`, `seuil` et `rappel_cible` ?

Une décision seule ne dit pas selon quelle règle elle a été prise. Dans six mois, le
seuil aura peut-être changé : une réponse archivée « a_examiner » ne voudra plus dire la
même chose qu'une réponse du jour. Avec le seuil et le rappel visé dans la réponse, le
dermatologue sait à quel niveau d'exigence la lésion a été triée, et la probabilité
permet de rejouer la décision avec un autre seuil sans rappeler le modèle.

### Question 3.3 — `/health` sans le fichier du modèle

Après avoir retiré `model/modele.joblib` et relancé l'API, `/health` renvoie
**503 SERVICE UNAVAILABLE**, avec `"model_loaded": false` et
`"error": "FileNotFoundError: [Errno 2] No such file or directory: 'model/modele.joblib'"`.

C'est préférable à un plantage : une plateforme qui voit un conteneur planter le
redémarre en boucle, sans savoir pourquoi. Ici le processus reste vivant, la sonde dit
« pas prêt », la plateforme ne lui envoie pas de trafic, et la cause est lisible dans la
réponse. Un processus vivant et un service en état de servir sont deux choses distinctes.

---

# Partie 4 — Conteneurisation et publication

Dockerfile de la séance 1 étendu sur quatre points : image de base
`python:3.14.0-slim-bookworm` (la version qui a entraîné le modèle), variables `PORT` et
`MODEL_PATH`, une ligne `COPY` pour le modèle, et `gunicorn` qui écoute sur le port lu
dans `PORT`.

### Question 4.1 — Écart de taille attendu, puis vérifié

En séance 1, l'image pesait 192 Mo dont 188 pour la base : Flask ne coûtait que 4 Mo.
Pour estimer la séance 2, j'ai additionné les paquets téléchargés par `pip` :
scipy 37,4 Mo, numpy 12,7 Mo, pandas 9,8 Mo, scikit-learn 8,4 Mo, soit environ 68 Mo
compressés, donc de l'ordre de 250 à 300 Mo une fois installés.
Vérification : l'image pèse **653 Mo**, soit **+461 Mo**. J'avais sous-estimé : les
bibliothèques de calcul prennent bien plus de place installées que compressées.

## Mesure 13 — Image de la séance 2, comparée à celle de la séance 1

| Relevé | Séance 1 | Séance 2 |
|---|---|---|
| Taille de l'image | 192 Mo | 653 Mo (150 Mo compressée) |
| Nombre de couches (`docker history`) | 19 | 18 |
| Durée de construction à froid | 12,59 s | 118,5 s |
| Nombre de paquets dans `pip freeze` | 7 | 18 |

La couche `pip install` passe de 3,4 s à 57,2 s : c'est elle que l'ordre des
instructions protège.

### Question 4.2 — Ce qui coûte cher dans un artefact d'inférence

Le modèle pèse 9,5 Ko, l'image 653 Mo : ce qui coûte, ce sont les bibliothèques, pas le
modèle. Si la taille devenait un problème, il faudrait d'abord réduire les dépendances,
par exemple retirer pandas de l'API (il ne sert qu'à construire une ligne) ou exporter
le modèle vers un moteur d'exécution plus léger. Compresser le modèle ne changerait rien.

## Mesure 15 — Cohérence des versions entre l'entraînement et l'image

| Relevé | Ma valeur |
|---|---|
| Version de scikit-learn ayant entraîné le modèle (champ `versions` du paquet) | 1.9.1 |
| Version de scikit-learn épinglée dans `requirements.txt` | 1.9.1 |
| Sont-elles identiques ? | Oui |
| Message d'erreur exact | Aucun |

Je n'ai pas eu l'erreur annoncée par l'énoncé, parce que j'ai épinglé les versions de la
mesure 1 dans `requirements.txt` et aligné l'image de base sur Python 3.14.0 **avant**
le premier lancement du conteneur. Preuve que les deux environnements sont identiques :
le conteneur renvoie exactement la même probabilité (0,750193) que l'API lancée hors
conteneur. `pip freeze` dans l'image confirme scikit-learn 1.9.1, pandas 3.0.6,
numpy 2.5.3, joblib 1.6.0.

La seule erreur de build rencontrée était autre : `"/requirements.txt": not found`, le
fichier n'étant pas encore dans le dossier lors de ma première tentative.

### Question 4.3 — Si je n'avais pas épinglé

L'image aurait cessé de fonctionner à deux moments. Le premier, tout de suite, si la
dernière version publiée diffère de celle de mon environnement d'entraînement : l'erreur
apparaît au premier lancement. Le second, plus tard, lors d'une reconstruction anodine
(un correctif dans `app.py`, une mise à jour de sécurité) après la sortie d'une nouvelle
version de scikit-learn : même Dockerfile, même modèle, mais une image différente.

Le second est le plus dangereux : le service tourne déjà en production, rien n'a changé
dans le dépôt, et personne ne fera le lien entre une reconstruction banale et un modèle
qui ne se charge plus, ou qui se charge et répond autrement.

## Mesure 16 — Publication

| Relevé | Ma valeur |
|---|---|
| Durée du push | 121,6 s (20,34 s en séance 1) |
| Digest obtenu | `sha256:35654575fabaf125bc5a169a45c03dd9fbc43db0bca7cbf9a24e822d1f4f76aa` |
| Tags présents dans le dépôt `dermascan-api` | `1.0.0` |
| Image complète | `acrdermascanik42.azurecr.io/dermascan-api:1.0.0` |

Le digest renvoyé par le push et celui lu ensuite dans le registre sont identiques.

---

# Partie 5 — Gouvernance

La model card est dans `MODEL_CARD.md`.

### Question 5.1 — Le seuil reste-t-il valable si une lésion sur vingt est maligne ?

Non. Mon seuil a été choisi pour une prévalence de 0,1 % ; là, elle serait de 5 %, soit
50 fois plus.

- La précision annoncée ne tient plus. À mon seuil, le modèle signale 90 % des malignes
  et 23,9 % des bénignes (19 457 sur 81 435). Avec 5 % de malignes, cela donnerait
  environ une maligne pour 6 lésions signalées, au lieu d'une pour 198.
- Le compromis change de poids. Rater une maligne sur dix, c'est une lésion ratée pour
  10 000 photographiées à 0,1 %, et 50 à 5 %.
- Le rappel lui-même n'est plus garanti : dans une consultation spécialisée, les lésions
  ont déjà été sélectionnées par un médecin et ne ressemblent pas à celles de
  l'entraînement.

Il faudrait mesurer le modèle sur des lésions de cette consultation, refaire le tableau
du compromis, rechoisir le seuil avec le médecin, et sans doute réentraîner.

### Question 5.2 — Une population pour laquelle je ne garantis rien

Les personnes à peau foncée. Je m'appuie sur la colonne `attribution` : les sept
institutions du jeu sont aux États-Unis, en Espagne, en Suisse, en Autriche, en Grèce et
en Australie, aucune en Afrique, en Asie ou en Amérique latine. Aucune colonne ne décrit
le phototype, donc je ne peux même pas mesurer la performance sur ces patients.

Deuxième cas, d'après `age_approx` : les moins de 20 ans, 645 lésions sur 401 059
(0,16 %).

---

# Nettoyage

Comme en séance 1, je n'ai pas lancé `docker system prune` : le poste héberge cinq
conteneurs d'autres projets (`rag-api`, `rag-db`, `mongodb`, `mariadb-container`,
`mysql-container`) qu'il aurait détruits. J'ai supprimé nominativement le conteneur et
les deux images de la séance, puis vidé le cache de build avec `docker builder prune`.

## Mesure 17 — Contrôles de nettoyage

| Contrôle de fin de séance | Mon observation |
|---|---|
| Espace disque libéré | 838,6 Mo de cache de build, plus les deux images locales de la séance |
| Espace libéré en séance 1, pour comparaison | plusieurs Go de cache |
| Nombre de ressources laissées actives | 1 : le registre `acrdermascanik42` |
| Coût journalier estimé du SKU Basic | environ 0,17 $US par jour |
| Date portée par l'étiquette `a_detruire` | 2027-09-30 |
| Crédit restant, relevé dans le portail (offre étudiant) le 09/10/2026 | 88 € sur 88 € · coûts d'octobre : 0,40 € · expiration le 06/10/2027 (362 jours) |
| Écart avec le relevé de la séance précédente (88 sur 88 et 0,00 de coûts le 06/10/2026) | Crédit affiché : inchangé · coûts du mois : +0,40 € |

Lecture de l'écart : le crédit affiché n'a pas bougé, mais le compteur de coûts est passé
de 0,00 à 0,40 € en trois jours, soit environ 0,13 € par jour. C'est cohérent avec le
registre Basic, seule ressource active, estimé à 0,17 $US par jour. Aucune dépense
inattendue : rien ne tourne à mon insu. Comme en séance 1, c'est le compteur de coûts
qui renseigne, pas le solde, qui est arrondi et n'a pas encore reflété la consommation.
Le portail affiche désormais les montants en euros, alors que j'avais relevé des dollars
en séance 1.

### Question 6.1 — La phrase de ticket de la séance 1 est-elle encore exacte ?

Elle ne l'est plus tout à fait. Le registre ne contient plus seulement le dépôt
`dermascan-health` de la séance 1 : il porte maintenant un second dépôt,
`dermascan-api`, avec le tag `1.0.0`, l'artefact que la séance 3 va déployer. Et la date du 30/09/2027 était une borne de sécurité, écrite avant de savoir
combien de séances en dépendraient ; laissé jusque-là, le registre consommerait une
soixantaine de dollars.

Phrase corrigée : « Le registre `acrdermascanik42` (groupe `rg-dermascan-registre-ik42`)
reste actif parce qu'il contient l'image `dermascan-api:1.0.0` que la séance 3 déploie
et que les séances 4, 5 et le projet fil rouge y publient encore ; il est à détruire dès
la soutenance du projet, et au plus tard le 30/09/2027. »

Ce qui m'a fait la corriger : le contenu du registre a changé, et « jusqu'à quand » doit
désigner la fin du module, pas seulement la date limite de l'étiquette.

## Contrôle d'extinction

| Contrôle | Fait |
|---|---|
| `az group list` ne montre qu'un groupe, celui du registre | Oui : `rg-dermascan-registre-ik42`, `germanywestcentral` |
| Aucun conteneur de la séance dans `docker ps -a` | Oui : il ne reste que les cinq conteneurs d'autres projets |
| Docker Desktop quitté | À faire en fin de séance |
| Machine éteinte | À faire en fin de séance |
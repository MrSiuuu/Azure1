# Mesures et réponses - Séance 1

**Issa KOUYATÉ** - M2 Data Engineering · Ynov Campus Montpellier
Industrialisation de l'IA dans le Cloud · 2026-2027 · séance du **6 octobre 2026**

**Poste :** Windows · PowerShell · Docker Desktop 29.5.3 · architecture **amd64**
**Abonnement :** Azure for Students · `fec0c6a0-752a-453e-95fc-4c30318138e4` · tenant `Ynov`

> **Note de transposition.** L'énoncé est écrit en syntaxe bash. Le poste étant sous Windows,
> toutes les commandes ont été transposées en PowerShell. Les équivalences utilisées sont
> listées en annexe de ce document.

---

# Partie 2 - Mise en place de l'environnement

## Mesure 2 - identité du compte Azure

| Élément | Valeur |
|---|---|
| ID d'abonnement | `fec0c6a0-752a-453e-95fc-4c30318138e4` |
| Nom de l'abonnement | `Azure for Students` |
| Nom du locataire (tenant) | `Ynov` (`ynov.com`) |
| ID du tenant | `38e72bba-3c22-4382-9323-ac1612931297` |
| `IsDefault` | `True` |
| `State` | `Enabled` |
| Rôle | Propriétaire |

> `az account set --subscription` n'affiche rien en cas de succès. L'exécuter reste
> indispensable : sur un compte multi-abonnements, l'absence de sélection explicite crée des
> ressources sur le mauvais abonnement **sans aucun message d'erreur**.

## Question 2.1 - Nombre de régions, et critères de choix

`az account list-locations` renvoie **109 régions**.

> **Précision importante, découverte en partie 4.** Ces 109 régions sont celles que
> l'abonnement **voit**, pas celles où il est **autorisé à déployer**. Une stratégie Azure
> nommée *« Allowed resource deployment regions »*, appliquée à l'abonnement Azure for
> Students, restreint le déploiement à cinq régions seulement : `germanywestcentral`,
> `switzerlandnorth`, `italynorth`, `spaincentral`, `polandcentral`. Les tentatives de
> création du registre en `francecentral` puis en `westeurope` ont été refusées avec le code
> `RequestDisallowedByAzure`. La stratégie a été identifiée avec
> `az policy assignment list --query "[].{nom:displayName, params:parameters}"`.
> **« Région visible » et « région autorisée » sont donc deux ensembles différents**, et seule
> l'inspection des stratégies permet de connaître la seconde.

**Deux critères qui imposent le choix d'une région en entreprise**, pour une plateforme
traitant des données industrielles européennes :

1. **Résidence des données.** Le RGPD encadre les transferts hors UE. Pour des données de
   santé (article 9), héberger dans l'Union évite d'avoir à justifier un transfert vers un
   pays tiers, et simplifie l'analyse d'impact.
2. **Latence.** La distance physique entre le datacenter et les utilisateurs se paie en
   millisecondes sur chaque requête. Pour une prédiction synchrone dans un parcours
   interactif, le seuil d'acceptabilité est de l'ordre de 200 ms au p95 : la latence réseau
   en consomme une part non négligeable.

*(Un troisième critère existe : la disponibilité des services et les tarifs varient d'une
région à l'autre - toutes n'offrent pas tous les SKU.)*

## Mesure 3 - état d'approvisionnement du groupe de ressources

| Élément | Valeur |
|---|---|
| Nom | `rg-dermascan-registre-ik42` |
| `provisioningState` | **`Succeeded`** |
| Région finale | `germanywestcentral` |
| Étiquettes | `projet=dermascan`, `role=registre`, `proprietaire=issa.kouyate`, `a_detruire=2027-09-30` |

> L'étiquette `a_detruire` porte une date **postérieure à la soutenance**, et non celle du
> jour : ce groupe porte le registre que les séances 2, 3 et 4 consomment, ainsi que le projet
> fil rouge. C'est la seule ressource Azure du module qui survit d'une séance à l'autre.

## Question 2.2 - La création du groupe a-t-elle consommé du crédit ?

**Non.** Un groupe de ressources est un **objet de métadonnées** dans Azure Resource Manager :
il n'y a derrière lui ni CPU, ni stockage, ni réseau. Azure ne facture que les ressources
*contenues* dans le groupe. Vérification dans Cost Management : le compteur `Coûts de Octobre`
est resté à `0,00 $US` après la création.

## Mesure 4 - environnement Docker du poste

| Élément relevé | Commande source | Valeur |
|---|---|---|
| Version du client Docker | `docker version` | `29.5.3` |
| Version du démon (server) | `docker version` | `29.5.3` |
| Architecture | `docker info` | `x86_64` → **amd64** |
| Nombre d'images déjà présentes | `docker info` | `10` |
| Mémoire allouée au démon | `docker info` | `7,635 GiB` |
| Noyau | `docker info` | `6.18.40.1-microsoft-standard-WSL2` |

> **Point d'attention architecture - sans objet sur ce poste.** L'architecture relevée est
> `amd64`, identique à celle des hôtes Linux utilisés par Azure en séance 3. La reconstruction
> avec `--platform linux/amd64 --provenance=false` prévue par l'énoncé ne concerne que les
> postes Apple Silicon (`arm64`) et n'a donc pas été nécessaire. L'absence d'`exec format
> error` au test de bout en bout (mesure 11) le confirme.

> **Remarque sur l'état initial du poste :** 10 images et 5 conteneurs arrêtés
> (`rag-api`, `rag-db`, `mongodb`, `mariadb-container`, `mysql-container`) préexistaient à la
> séance, issus d'autres projets. Ce point conditionne le nettoyage final (mesure 12).

---

# Partie 3 - Conteneurisation

## Question 3.1 - Pourquoi `0.0.0.0` et non `127.0.0.1`

Un conteneur dispose de sa **propre pile réseau**. Une écoute sur `127.0.0.1` ne serait
joignable que depuis l'intérieur du conteneur lui-même : la redirection de port `-p` de l'hôte
n'aboutirait jamais, et `curl` depuis Windows recevrait un refus de connexion.
`0.0.0.0` fait écouter le processus sur **toutes** les interfaces du conteneur, dont celle que
Docker relie à l'hôte.

C'est le dernier symptôme listé en annexe A de l'énoncé : *« curl ne répond pas mais
`docker ps` affiche Up »*.

## Question 3.2 - Si `EXPOSE` avait été oublié

**Le conteneur aurait quand même fonctionné avec `-p`.** `EXPOSE` ne publie aucun port : c'est
une déclaration documentaire, lisible par `docker inspect` et par les collègues qui reprennent
l'image. Seul `-p` au lancement crée la redirection entre un port de l'hôte et un port du
conteneur.

## Question 3.3 - Oubli du `.dockerignore` avec un `.venv/` de 400 Mo

Deux conséquences distinctes :

1. **Sur la durée du build.** Le `.` final de `docker build` désigne le **contexte**, envoyé
   intégralement au démon Docker **avant** l'exécution de la première instruction. 400 Mo
   seraient transférés à chaque build, même si aucune instruction ne les utilise.
2. **Sur l'image.** Si une instruction `COPY . ./` les embarque, les 400 Mo se retrouvent dans
   une couche de l'image finale - qui sera poussée, stockée et tirée à chaque déploiement. S'y
   ajoute un risque de **fuite de secrets** si un fichier `.env` ou une clé traîne dans le
   dossier.

## Mesure 5 - coût du premier build et composition de l'image

| Mesure | Valeur |
|---|---|
| Durée du premier build (cache vide) | **12,59 s** |
| Taille de l'image | **192 Mo** (disk usage) - 46,8 Mo (content size) |
| Nombre de couches listées par `docker history` | **19** |
| Couche la plus lourde, et son instruction | **85,2 Mo** - `# debian.sh --arch 'amd64' out/ 'bookworm'`, le système de fichiers Debian de l'image de base |
| Taille de l'image de base seule | **188 Mo** (disk usage) - 47,7 Mo (content size) |

**Pourquoi la sortie affiche `[1/6]` et non `[1/10]` :** toutes les instructions ne créent pas
une couche de système de fichiers. `ENV`, `USER`, `EXPOSE` et `CMD` ne posent que des
**métadonnées** - zéro octet ajouté, visible dans `docker history`. Seules `FROM`, `WORKDIR`,
les deux `COPY` et les deux `RUN` produisent du contenu.

**Décomposition de la taille :**

| Mes instructions | Taille | | Image de base | Taille |
|---|---|---|---|---|
| `WORKDIR /app` | 8,19 ko | | `debian.sh … bookworm` | 85,2 Mo |
| `COPY requirements.txt` | 12,3 ko | | `RUN apt-get …` | 9,59 Mo |
| `RUN pip install` | **5,64 Mo** | | `RUN … CPython` | 45,0 Mo |
| `COPY app.py` | 12,3 ko | | `RUN … idle3` | 16,4 ko |
| `RUN useradd` | 81,9 ko | | | |
| `ENV` / `USER` / `EXPOSE` / `CMD` | 0 B | | | |
| **Total ajouté** | **≈ 5,75 Mo** | | **Total base** | **≈ 139,8 Mo** |

## Question 3.4 - Pourcentage imputable à l'image de base

**188 / 192 ≈ 98 %.**

Mes dix instructions n'ajoutent que ~4 Mo à une image qui en pèse 192. L'enseignement est
net : **le code applicatif ne pèse rien, tout le poids vient du socle choisi en une ligne**
(`FROM`). C'est ce qui fait du choix `slim` - plutôt que l'image Python complète, d'environ
1 Go - la décision la plus rentable du Dockerfile.

## Mesure 6 - réponse de la sonde `/health` du conteneur local

| Mesure | Valeur |
|---|---|
| Code HTTP retourné | **`200 OK`** |
| Champ `hostname` | `ca1d364df4f6` |
| Champ `version` | `0.1.0` |
| Champ `status` | `ok` |
| En-tête `Server` | `Werkzeug/3.1.9 Python/3.12.7` |

## Question 3.5 - D'où vient la valeur du champ `hostname`

Elle vient de **l'identifiant du conteneur**, dont Docker fait le nom de machine du conteneur.
Python la lit avec `socket.gethostname()`. La correspondance est directe :

```
docker run → ca1d364df4f6a7ca308e3b8cc2e51b39e89886fd19943c1959094e8ce2811f6d
hostname   → ca1d364df4f6          (les 12 premiers caractères)
```

Après destruction et relance, la valeur change : le second conteneur a répondu
`c9f1efa4246e`, et celui lancé depuis le registre `810f639d1583` - alors que **l'image n'a pas
bougé d'un octet**, digest identique.

**Ce que j'en déduis :** un conteneur n'a **pas d'identité stable**, il est jetable. On ne
s'attache pas à une instance, on la remplace. C'est le modèle même du cloud : si un conteneur
meurt, l'orchestrateur en relance un autre, avec un nouvel identifiant, et le service continue.
Toute logique applicative qui dépendrait du `hostname` pour identifier une instance de façon
durable serait fausse par construction.

## Question 3.6 - Surcharge de `APP_VERSION` sans reconstruction

Deux conteneurs lancés depuis **la même image**, sans aucun rebuild :

```
port 8080 → {"hostname":"ca1d364df4f6", … "version":"0.1.0"}
port 8081 → {"hostname":"c9f1efa4246e", … "version":"0.2.0-test"}   (-e APP_VERSION)
```

**Oui, la réponse JSON change sans qu'aucune reconstruction n'ait eu lieu.**

Ce que cela dit de la séparation image / configuration : l'**image** est l'artefact -
immuable, identifiée par un digest, strictement la même partout. La **configuration** est
externe, injectée au lancement par variables d'environnement. C'est ce qui permet de promouvoir
exactement le même binaire de développement vers la recette puis vers la production en ne
changeant que des variables.

Si la configuration était figée dans l'image, chaque environnement exigerait son propre build -
et l'on ne déploierait jamais l'artefact que l'on a validé, seulement une recompilation de
celui-ci.

## Mesure 7 - effet de l'ordre des instructions sur le cache de build

| Scénario | Durée du build | Étapes `CACHED` | `pip install` rejoué ? |
|---|---|---|---|
| **A - bon ordre**, après modification d'`app.py` | **3,97 s** | **3** | **Non** - `CACHED`, 0,0 s |
| **B - mauvais ordre**, après modification d'`app.py` | **5,13 s** | **1** | **Oui** - 3,4 s |
| **Écart A/B** | **+1,16 s (+29 %)** | **−2 couches** | |

**Sortie du scénario A** - seules les deux dernières étapes sont rejouées :
```
=> CACHED [2/6] WORKDIR /app                                        0.0s
=> CACHED [3/6] COPY requirements.txt ./                            0.0s
=> CACHED [4/6] RUN pip install --no-cache-dir -r requirements.txt  0.0s
=> [5/6] COPY app.py ./                                             0.1s
=> [6/6] RUN useradd --create-home --uid 10001 appuser ...          0.9s
```

**Sortie du scénario B** - une seule couche sauvée, l'installation est relancée :
```
=> CACHED [2/5] WORKDIR /app                                        0.0s
=> [3/5] COPY . ./                                                  0.0s
=> [4/5] RUN pip install --no-cache-dir -r requirements.txt         3.4s
=> [5/5] RUN useradd --create-home --uid 10001 appuser ...          0.4s
```

Le `Dockerfile.naif` ne compte que 5 étapes au lieu de 6, les deux `COPY` ayant été fusionnés.

## Question 3.7 - Le mécanisme d'invalidation du cache

Docker construit l'image en couches empilées, une par instruction. Pour chaque instruction, il
calcule une empreinte à partir de l'instruction elle-même et du contenu des fichiers qu'elle
copie. Si cette empreinte correspond à celle d'un build précédent, la couche est réutilisée
telle quelle et affichée `CACHED`.

Dès qu'une couche est invalidée, **toutes les couches suivantes le sont également**, même si
leurs propres instructions n'ont pas changé : chaque couche est construite au-dessus de l'état
du système de fichiers produit par la précédente, et cet état n'est plus le même.

D'où la règle d'ordre : **du moins volatil au plus volatil**. L'image de base et les
dépendances en haut, le code applicatif en bas.

## Question 3.8 - Coût du mauvais ordre sur vingt itérations en séance 2

L'écart mesuré aujourd'hui (**1,16 s**) correspond à la durée du `pip install` rejoué
inutilement (**3,4 s**), atténuée par les variations de build. Le point important n'est pas
cette valeur, mais ce qu'elle représente : **le mauvais ordre coûte, à chaque itération, le
temps d'installation complet des dépendances.**

L'écart n'est donc pas une constante - c'est la durée de la couche que l'on invalide à tort.

| Contexte | Durée de `pip install` | Coût sur 20 itérations / jour |
|---|---|---|
| Séance 1 - `Flask` seul | ~3,4 s | ~68 s par jour - négligeable |
| Séance 2 - `scikit-learn` + `pandas` + `numpy` | ~90 s estimées | **~1 800 s, soit 30 minutes par développeur et par jour** |

Trente minutes de temps mort quotidien, par développeur, **pour une modification d'une seule
ligne de code**. Sur une équipe de quatre personnes, deux heures par jour passées à attendre un
build. Et ce temps n'apparaît dans aucun indicateur : il se dilue en attente, en changements de
contexte, et en itérations qu'on finit par ne plus faire.

## Mesure 8 - contrôles de l'utilisateur non privilégié

| Contrôle | Résultat attendu | Observation |
|---|---|---|
| `id` dans le conteneur | uid non nul | `uid=10001(appuser) gid=10001(appuser) groups=10001(appuser)` ✅ |
| `.Config.User` de l'image | non vide | `appuser` ✅ |
| Écriture dans `/etc` | refusée | `touch: cannot touch '/etc/preuve_root': Permission denied` ✅ |

## Question 3.9 - Ce que gagne un attaquant si le processus tourne en root

En `root`, un attaquant qui obtient l'exécution de code arbitraire dans le conteneur peut
écrire partout dans son système de fichiers : installer des outils, remplacer des binaires,
désactiver des protections, modifier la configuration du service. Surtout, **l'uid 0 du
conteneur est l'uid 0 de l'hôte** - le noyau est partagé : tout volume monté devient
modifiable en root, et la moindre faille d'évasion ou capacité mal configurée se traduit
directement en privilèges root sur la machine hôte.

En `appuser` (uid 10001), il hérite d'un compte sans droit d'écriture hors de `/app`, incapable
d'installer quoi que ce soit, et sans correspondance privilégiée côté hôte.

---

# Partie 4 - Azure Container Registry

## Mesure 9 - caractéristiques du registre ACR créé

| Élément | Valeur |
|---|---|
| `loginServer` | **`acrdermascanik42.azurecr.io`** |
| SKU retenu | **Basic** |
| État d'approvisionnement | **`Succeeded`** |
| Région | `germanywestcentral` |
| Date de création | 06/10/2026 12:30 UTC |
| `adminUserEnabled` | `false` (valeur par défaut) |
| Coût mensuel annoncé pour ce SKU | **≈ 5 $US / mois**, soit **≈ 0,17 $US / jour** |

> **Sur le mode de facturation d'ACR.** Le prix est une **redevance journalière fixe par
> tier**, et non une facturation à l'usage : le registre coûte le même montant qu'il reçoive
> mille tirages ou aucun. Chaque tier inclut un quota de stockage et un débit ; on ne paie en
> supplément qu'au-delà de ces quotas. C'est l'illustration directe de la règle énoncée en
> question 1.2 : **on paie la réservation, pas l'usage.**
>
> Ordre de grandeur relevé : Basic ≈ 5 $/mois, Standard ≈ 20 $/mois, Premium ≈ 50 $/mois. Le
> tarif exact dépend de la région et de la devise de facturation - à confirmer sur la page
> tarifaire officielle pour Germany West Central.
>
> **Projection sur le module :** à ~0,17 $/jour, le registre laissé actif de la séance 1 à la
> soutenance (environ 12 mois) consommerait de l'ordre de **60 $ sur un crédit de 100 $**.
> C'est considérable, et c'est précisément pourquoi l'étiquette `a_detruire` n'est pas
> décorative.

### Obstacles rencontrés avant la création

Deux refus successifs, non documentés dans l'énoncé :

1. **`RequestDisallowedByAzure`** en `francecentral` puis en `westeurope` - stratégie
   *« Allowed resource deployment regions »* limitant le déploiement à cinq régions
   (voir question 2.1).
2. **`MissingSubscriptionRegistration`** - l'abonnement, créé le matin même, n'avait jamais
   utilisé de conteneurs : le fournisseur de ressources `Microsoft.ContainerRegistry` n'y était
   pas enregistré. Corrigé par `az provider register --namespace Microsoft.ContainerRegistry`,
   suivi d'une attente jusqu'au passage de `Registering` à `Registered`.
   `Microsoft.ContainerInstance` a été enregistré dans la foulée, en prévision de la séance 3.

> Ce second point éclaire concrètement l'avertissement de l'énoncé sur le crédit épuisé : ce
> sont exactement ces deux namespaces que l'offre Starter interdit.

## Question 4.1 - Comparaison des trois SKU

| Critère | Basic | Standard | Premium |
|---|---|---|---|
| Quota de stockage inclus | ~10 Go | ~100 Go | ~500 Go |
| Débit et connexions simultanées | faible | moyen | élevé |
| Géo-réplication | non | non | **oui** |
| Private Link / isolation réseau | non | non | **oui** |
| Verrouillage de contenu, tokens à portée limitée | non | non | **oui** |

**À partir de quel besoin concret passer au Premium chez DermaScan ?** Deux déclencheurs,
tous deux liés au métier :

1. **La géo-réplication**, dès que des centres de dépistage répartis sur plusieurs pays
   tirent la même image : sans elle, chaque site télécharge depuis une région unique, avec la
   latence et le coût de sortie réseau correspondants.
2. **Private Link**, dès qu'une exigence de conformité impose que le registre ne soit pas
   joignable depuis l'Internet public. Sur un produit manipulant de la donnée de santé, c'est
   une demande d'audit courante.

Pour le périmètre du module - quelques images, un seul utilisateur, un seul site - **Basic est
le choix correct**. Prendre Premium serait consommer du crédit pour des fonctions inutilisées.

## Question 4.2 - Contenu de `~/.docker/config.json` après `az acr login`

Le fichier gagne une entrée `auths` pour `acrdermascanik42.azurecr.io`.

**Sur une configuration par défaut** (Linux, ou Docker sans credential helper), cette entrée
contient un champ `auth` portant le jeton d'identification **encodé en base64**. Base64 est un
encodage, pas un chiffrement : il est réversible par quiconque lit le fichier. Le jeton peut
alors être rejoué pour pousser ou tirer des images en se faisant passer pour moi, pendant toute
sa durée de validité - quelques heures. C'est pourquoi ce fichier ne doit jamais être committé
ni partagé.

**Sur mon poste**, le contenu observé est différent :

```json
"auths": { "acrdermascanik42.azurecr.io": {} },
"credsStore": "desktop"
```

L'entrée est **vide**. La ligne `"credsStore": "desktop"` indique que Docker Desktop délègue le
stockage du secret au **Gestionnaire d'identifiants Windows**, où il est chiffré par DPAPI et
lié à ma session utilisateur. `config.json` ne joue plus que le rôle d'**index des registres
authentifiés**.

Le risque de fuite par copie de ce fichier est donc écarté - mais le jeton reste extractible
par tout processus s'exécutant sous mon compte utilisateur. Le credential helper protège contre
la fuite documentaire, pas contre un code malveillant local.

## Question 4.3 - Pourquoi l'utilisateur administrateur du registre est déconseillé

**1. Identité partagée, donc traçabilité nulle.** L'utilisateur admin est un couple
login/mot de passe **unique pour tout le registre**, utilisé par toute l'équipe et par la CI.
Les journaux d'audit enregistrent alors « admin a poussé une image », jamais *qui*. En cas
d'incident - une image compromise publiée sous un tag de production - il devient impossible de
remonter à l'origine.

**2. Secret de longue durée, aux droits maximaux.** Le mot de passe admin ne tourne pas
automatiquement, donne un accès complet en lecture **et écriture** sur l'ensemble du registre,
et finit systématiquement en clair dans une variable de CI ou un fichier `.env`. L'approche
recommandée - jetons Entra ID via `az acr login`, ou identité managée pour un service - produit
des jetons **courts, nominatifs et à portée réduite**, révocables individuellement.

Azure applique d'ailleurs le bon réglage par défaut : le registre créé porte
`"adminUserEnabled": false`.

## Mesure 10 - coût du premier push vers ACR et identité de l'image poussée

| Mesure | Valeur |
|---|---|
| Durée du push | **20,34 s** |
| Nombre de couches poussées | **10** |
| IMAGE ID local et IMAGE ID taggé : identiques ? | **Oui** - `43633dd710cc` pour les deux |
| Digest retourné en fin de push | `sha256:43633dd710cc44bd76599e9301d4991b690f087ae7f8266b114f79787a2e61f7` |

**Sur `docker tag` :** la commande ne copie ni ne reconstruit rien. Après exécution,
`docker images` liste deux entrées pour **un seul IMAGE ID** - deux noms pointant vers la même
image sur disque :

```
acrdermascanik42.azurecr.io/dermascan-health:0.1.0   43633dd710cc   192MB
dermascan-health:0.1.0                               43633dd710cc   192MB
dermascan-health:naif                                6def86379a5d   192MB   ← autre image
```

**Sur le digest :** ses douze premiers caractères sont exactement l'IMAGE ID. Le digest est
calculé **à partir du contenu** de l'image. Il est donc impossible de modifier l'image sans
changer le digest - ce qui en fait un identifiant **immuable**, contrairement à un tag qui peut
être réassigné à un autre contenu. C'est ce digest, et non le tag, qui est inscrit en rubrique 2
de la fiche d'identité.

## Question 4.4 - Second push de la même image

**Non, la durée n'est pas la même : 20,34 s au premier push, 0,64 s au second** - trente-deux
fois plus rapide. Docker affiche `Layer already exists` pour chacune des 10 couches, et le
digest retourné est identique.

**Mécanisme révélé : le stockage adressé par le contenu** (*content-addressable storage*). Une
couche n'est identifiée ni par son nom, ni par son rang dans l'image, mais par l'empreinte
SHA-256 de son contenu. Avant tout transfert, le client interroge le registre pour chaque digest
de couche ; si le blob correspondant y est déjà présent, rien ne transite sur le réseau. Seul le
manifeste, qui référence les couches, est réécrit.

Conséquence à l'échelle d'une organisation : dix images applicatives bâties sur la même base
`python:3.12.7-slim-bookworm` ne stockent cette base **qu'une seule fois** dans le registre, et
ne la transfèrent qu'une seule fois. C'est ce qui rend viable de pousser une image à chaque
commit en CI - seules les couches réellement modifiées, en général les quelques mégaoctets de
code applicatif, transitent.

## Vérification dans le registre

```
az acr repository list      → dermascan-health
az acr repository show-tags → 0.1.0
```

`az acr manifest list-metadata` retourne **trois manifestes** :

| Digest | Architecture / OS | Taille | Rôle |
|---|---|---|---|
| `sha256:43633dd7…` | - | 0 | l'**index** (manifest list) - c'est lui qui porte le tag `0.1.0` |
| `sha256:9619ecfb…` | **amd64 / linux** | 46 786 519 o | l'**image réelle**, celle qui s'exécute |
| `sha256:b76e64cd…` | unknown / unknown | 1 112 o | le **manifeste d'attestation** (provenance), ajouté par BuildKit |

Le portail confirme : dépôt `dermascan-health`, 1 étiquette, 3 manifestes *(capture
`01-portail-acr-depot.png`)*.

> La troisième ligne `unknown/unknown` est précisément ce que l'option `--provenance=false` de
> l'énoncé sert à supprimer : BuildKit joint à chaque build un manifeste décrivant comment
> l'image a été construite. Inoffensif, mais il encombre la lecture du relevé.

## Mesure 11 - exécution de l'image retéléchargée depuis ACR

Image et conteneurs locaux supprimés au préalable, pour forcer un téléchargement réel.

| Mesure | Valeur |
|---|---|
| Durée du `docker run` avec téléchargement | **2,03 s** |
| Le JSON de santé est-il identique à celui de la partie 3.4 ? | **Oui** - mêmes champs et mêmes valeurs, hormis `hostname` et `uptime_seconds` |
| Le `hostname` a-t-il changé ? | **Oui** - `810f639d1583` au lieu de `ca1d364df4f6` |

```
Unable to find image 'acrdermascanik42.azurecr.io/dermascan-health:0.1.0' locally
0.1.0: Pulling from dermascan-health
Digest: sha256:43633dd710cc44bd76599e9301d4991b690f087ae7f8266b114f79787a2e61f7
```

**Le digest récupéré est identique à celui du push.** C'est la démonstration recherchée :
l'artefact exécuté est bit pour bit celui qui a été construit et validé - ni une
reconstruction, ni une approximation. Cinq couches sur dix affichent `Pull complete`, les
autres étant encore présentes localement (couches de l'image de base, partagées avec
`dermascan-health:naif`) : sur une machine vierge, le téléchargement serait plus long.

---

# Partie 5 - Gouvernance

## Question 5.1 - `pip freeze` comparé au `requirements.txt`

`requirements.txt` déclare **1 paquet** (`Flask==3.0.3`). `pip freeze` en liste **7** :

```
blinker==1.9.0      click==8.5.0        Flask==3.0.3        itsdangerous==2.2.0
Jinja2==3.1.6       MarkupSafe==3.0.4   Werkzeug==3.1.9
```

**Six paquets supplémentaires.** Ce sont les **dépendances transitives** : le résolveur de pip
installe l'arbre complet des dépendances nécessaires au fonctionnement de Flask. Werkzeug est
son serveur WSGI, Jinja2 son moteur de templates, MarkupSafe une dépendance de Jinja2,
itsdangerous gère la signature des sessions, click la ligne de commande, blinker les signaux.

**Pourquoi un audit de licences doit porter sur le `pip freeze` :** ce qui est redistribué,
c'est l'image - donc **tout le code réellement embarqué**, pas la liste de ce qui a été
demandé. Une dépendance transitive sous licence copyleft oblige exactement au même titre
qu'une dépendance directe, et personne ne l'a choisie explicitement. Le `requirements.txt` est
une déclaration d'intention ; le `pip freeze` est l'inventaire de ce qui est là. Seul le second
fait foi.

## Question 5.2 - Les trois licences, et la plus contraignante

| Composant | Licence | Nature |
|---|---|---|
| Flask 3.0.3 (et `click`, `itsdangerous`, `Jinja2`, `MarkupSafe`, `Werkzeug`) | **BSD-3-Clause** | permissive |
| CPython 3.12.7 | **PSF License Agreement** | permissive |
| Paquets système de Debian bookworm (image de base) | **mélange GPL-2, GPL-3, LGPL-2.1+** - `glibc` est LGPL, de nombreux utilitaires sont GPL | **copyleft** |

*(`blinker` est sous licence MIT, également permissive.)*

**La plus contraignante si DermaScan redistribue cette image à un centre de dépistage client :
les paquets système de Debian.**

BSD, MIT et PSF n'exigent que la conservation des mentions de copyright et du texte de licence -
une formalité documentaire. Les composants **GPL et LGPL** de la distribution de base imposent
en revanche la **mise à disposition du code source correspondant**, ou une offre écrite valable
trois ans, y compris pour des composants que personne n'a choisi d'ajouter : ils arrivent avec
la seule ligne `FROM`.

Point souvent négligé : **distribuer une image Docker constitue une distribution de binaires**
au sens de ces licences. Pousser l'image dans un registre accessible au client déclenche les
mêmes obligations qu'expédier un support physique.

# Nettoyage

## Mesure 12 - nettoyage local, et coût de ce qui reste actif

| Contrôle de fin de séance | Observation |
|---|---|
| Espace disque libéré par le nettoyage du cache de build | **plusieurs Go** - une soixantaine d'entrées supprimées, dont quatre de 0,9 à 1,3 Go. Après nettoyage, le cache de build ne présente plus que **42,68 Mo récupérables** |
| Nombre de ressources laissées actives dans `$RG` | **1** - `acrdermascanik42` (`Microsoft.ContainerRegistry/registries`, état `Succeeded`) |
| SKU du registre, et son coût journalier estimé | **Basic** - ≈ **0,17 $US / jour** (≈ 5 $US / mois) |
| Date portée par l'étiquette `a_detruire` | **2027-09-30** |
| Nombre de groupes de ressources m'appartenant au total | **1** - `rg-dermascan-registre-ik42` |
| Crédit restant, relevé dans Cost Management | **88 $US sur 88 $US** - relevé le 06/10/2026 à 15h44 · `Coûts de Octobre` : **0,00 $US** |

### Observation sur le relevé de crédit - écart non imputable à une consommation

| Relevé | Crédits disponibles | Coûts du mois |
|---|---|---|
| 06/10/2026, avant toute création | `100 $US sur 100 $US` | `0,00 $US` |
| 06/10/2026, 15h44, en fin de séance | `88 $US sur 88 $US` | `0,00 $US` |

L'écart apparent est de 12 $US, mais **il ne correspond à aucune consommation** : le compteur
`Coûts de Octobre` est resté à `0,00 $US`, et le **montant total de l'offre** a lui aussi varié
(100 → 88), pas seulement le solde disponible. Une dépense aurait fait baisser le disponible
tout en laissant le total inchangé.

L'hypothèse la plus plausible est une **réévaluation du montant de la subvention** côté
Microsoft - conversion de devise ou ajustement de l'offre étudiante - et non une facturation.
Le point sera signalé au formateur et vérifié au relevé suivant.

**Ce que cet épisode illustre :** l'énoncé demande de suivre *l'écart entre deux relevés* parce
qu'il révèle une ressource oubliée. Encore faut-il distinguer un écart dû à la consommation
d'un écart dû à autre chose. Le croisement avec le compteur `Coûts du mois` permet de trancher :
ici, dépense réelle nulle, cohérente avec un registre créé depuis environ trois heures à
~0,17 $/jour, soit de l'ordre de **0,02 $US** - un montant sous le seuil d'affichage.

État du poste après nettoyage (`docker system df`) :

```
TYPE            TOTAL   ACTIVE   SIZE      RECLAIMABLE
Images          11      5        9.347GB   3.283GB (35%)
Containers      5       0        1.786MB   1.786MB (100%)
Local Volumes   9       5        1.086GB   429.4MB (39%)
Build Cache     37      0        2.439GB   42.68MB
```

> **Décision assumée sur le périmètre du nettoyage local.** Le poste hébergeait, avant la
> séance, cinq conteneurs arrêtés issus d'autres projets (`rag-api`, `rag-db`, `mongodb`,
> `mariadb-container`, `mysql-container`) et dix images. `docker system prune` agit sur
> **l'ensemble du poste** et non sur les seuls artefacts du TP : il aurait détruit ces cinq
> conteneurs.
>
> J'ai donc écarté le prune global au profit de `docker builder prune`, qui ne supprime que
> le **cache de build** - là où se trouvait l'essentiel de l'espace récupérable du TP, cinq
> builds ayant été réalisés dans la journée. Les conteneurs et volumes des autres projets
> sont restés intacts.
>
> Les artefacts du TP, eux, ont été supprimés nominativement : `docker rm -f` sur les trois
> conteneurs, `docker rmi -f` sur les trois tags d'image. `docker ps -a` confirme qu'aucun
> conteneur de la séance ne subsiste.
>
> **Ce choix illustre le principe même de la section :** le nettoyage n'est pas une
> destruction aveugle, c'est une décision de périmètre, prise après inventaire et tracée.

## Décision de fin de séance

**Ce qui disparaît :** tous les conteneurs de la séance (`dermascan-health`,
`dermascan-health-bis`, `dermascan-from-acr`), les images locales (`dermascan-health:0.1.0`,
`dermascan-health:naif`, l'image taguée au nom du registre), ainsi que les couches et caches de
build orphelins.

**Ce qui survit :** le registre `acrdermascanik42` et son groupe
`rg-dermascan-registre-ik42`. Ce n'est pas un oubli, c'est une décision : les séances 2, 3 et 4
consomment ce registre, puis le projet fil rouge. Le détruire ce soir obligerait à tout
reconstruire au début de la séance 2.

**La trace de cette décision** est portée par les étiquettes du groupe : `proprietaire` dit qui
appeler, `a_detruire=2027-09-30` dit jusqu'à quand, `projet` et `role` disent pourquoi.

## Question 6.1 - Phrase pour un ticket d'équipe

> Le registre `acrdermascanik42` (SKU Basic, groupe `rg-dermascan-registre-ik42`, région
> Germany West Central) héberge les images du projet DermaScan consommées par les séances 2 à 5
> et par le projet fil rouge ; il peut être supprimé sans me consulter après le **30 septembre
> 2027**, date portée par son étiquette `a_detruire`.

Elle contient les trois informations exigées : **quoi** (le registre nommé, avec son SKU et son
groupe), **pourquoi** (ce qui en dépend), **jusqu'à quand** (une date explicite, cohérente avec
l'étiquette portée par la ressource elle-même).

## Question 6.2 - Le risque de `--no-wait`

`--no-wait` rend la main **avant** que la suppression n'aboutisse : la commande retourne
immédiatement, mais le groupe peut rester visible plusieurs minutes dans `az group list`. Plus
grave, la suppression peut **échouer silencieusement** - verrou de ressource, dépendance non
résolue, ressource en cours de provisionnement - sans qu'aucun message ne revienne, puisque
personne n'attend le résultat.

Considérer la suppression comme acquise à cet instant, c'est risquer de laisser tourner - et
facturer - des ressources que l'on croit détruites. Précisément le scénario que le nettoyage
cherche à éviter.

**La seule vérification fiable** est `az group exists --name "$RG"`, qui doit **finir par
renvoyer `false`**, relancée jusqu'à confirmation. Un contrôle complémentaire consiste à
relever le crédit dans Cost Management le lendemain : un écart non nul sur une ressource
supposée détruite est le signal qu'elle ne l'est pas.

Cette vérification sera appliquée en fin de séance 3, sur un groupe nettement plus coûteux que
celui-ci.

# Annexe - transposition bash → PowerShell

Le poste étant sous Windows, les commandes de l'énoncé ont dû être transposées. Les
équivalences utilisées :

| Syntaxe de l'énoncé (bash) | Équivalent PowerShell |
|---|---|
| `export VAR="x"` | `$env:VAR = "x"` |
| `$VAR` dans une chaîne | `$($env:VAR)` |
| `time docker build …` | `Measure-Command { docker build … \| Out-Default }` |
| `curl -s -i …` | **`curl.exe`** `-s -i …` |
| `--query "length(@)"` | `(… \| Measure-Object).Count` |
| `\` en fin de ligne | backtick `` ` `` |
| `grep dermascan` | `Select-String dermascan` |

Trois points méritent explication :

- **`curl`** est, sous PowerShell, un alias vers `Invoke-WebRequest`, qui ne comprend pas les
  options `-s` et `-i`. Il faut invoquer le binaire réel, `curl.exe`.
- **`--query "length(@)"`** échoue : les parenthèses sont interprétées par PowerShell avant
  d'atteindre `az`, produisant l'erreur `--output était inattendu`.
- **`Measure-Command`** capture la sortie de ce qu'il chronomètre ; sans `| Out-Default`, le
  déroulé du build n'est pas affiché.

**Autres points d'attention rencontrés :**

- Après installation de l'Azure CLI, il faut **fermer et rouvrir le terminal** : le PATH n'est
  lu qu'au démarrage du shell.
- Le fichier doit s'appeler exactement `Dockerfile`, **sans extension** - le Bloc-notes ajoute
  un `.txt` invisible.
- `docker info` affiche la section `Client:` même lorsque le démon est arrêté ; c'est la
  présence de la section `Server:` qui atteste que Docker Desktop tourne.
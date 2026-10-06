# Fiche d'identité du conteneur

**Projet DermaScan** - sonde de santé (health probe)
Séance 1 · Industrialisation de l'IA dans le Cloud · Ynov Montpellier · 2026-2027

> Toutes les valeurs de cette fiche ont été **mesurées sur l'artefact**, par interrogation
> directe de l'image (`docker image inspect`, `python --version`, `pip freeze`), et non
> recopiées depuis les fichiers sources.

| # | Rubrique | Valeur |
|---|---|---|
| 1 | **Nom de l'artefact et tag** | `dermascan-health:0.1.0` - nom complet dans le registre : `acrdermascanik42.azurecr.io/dermascan-health:0.1.0` |
| 2 | **Digest sha256** | `sha256:43633dd710cc44bd76599e9301d4991b690f087ae7f8266b114f79787a2e61f7` |
| 3 | **Image de base, tag exact** | `python:3.12.7-slim-bookworm` (digest de base : `sha256:60d9996b6a8a3689d36db740b49f4327be3be09a21122bd02fb8895abb38b50d`) |
| 4 | **Version de Python embarquée** | `Python 3.12.7` - relevée par `docker run --rm <image> python --version` |
| 5 | **Dépendances directes** | `Flask==3.0.3` (unique ligne de `requirements.txt`) |
| 6 | **Dépendances transitives** | 6 paquets ajoutés par le résolveur pip : `blinker==1.9.0`, `click==8.5.0`, `itsdangerous==2.2.0`, `Jinja2==3.1.6`, `MarkupSafe==3.0.4`, `Werkzeug==3.1.9` |
| 7 | **Licences et obligations** | voir le détail ci-dessous |
| 8 | **Architecture et OS cibles** | `amd64` / `linux` |
| 9 | **Utilisateur d'exécution** | `appuser`, uid `10001`, gid `10001` - vérifié par `docker exec … id` et par `.Config.User` |
| 10 | **Port exposé et endpoint de santé** | `EXPOSE 8000` (TCP) ; sonde : `GET /health` → JSON `{status, service, version, hostname, uptime_seconds}` ; endpoint secondaire : `GET /` |
| 11 | **Producteur** | Issa Kouyaté - M2 Data Engineering, Ynov Campus Montpellier - image construite le **06/10/2026 à 10:58:32 UTC** (12:58 heure de Paris), publiée le même jour à 12:40 UTC |
| 12 | **Registre de publication** | `loginServer` : `acrdermascanik42.azurecr.io` - dépôt : `dermascan-health` - SKU Basic, région `germanywestcentral`, groupe `rg-dermascan-registre-ik42` |
| 13 | **Destination connue** | Séance 2 : cette image sert de base à l'API d'inférence DermaScan. `requirements.txt` y sera enrichi de `scikit-learn`, `pandas` et `numpy`. Séance 3 : déploiement sur service managé Azure. |
| 14 | **Limites connues et risques résiduels** | voir le détail ci-dessous |

---

## Rubrique 7 - détail des licences

| Composant | Licence | Nature | Obligations en cas de redistribution |
|---|---|---|---|
| **Flask 3.0.3** et ses 5 dépendances BSD (`click`, `itsdangerous`, `Jinja2`, `MarkupSafe`, `Werkzeug`) | **BSD-3-Clause** | permissive | conserver la mention de copyright et le texte de licence ; ne pas utiliser le nom des auteurs pour promouvoir le produit |
| **blinker 1.9.0** | **MIT** | permissive | conserver la mention de copyright et le texte de licence |
| **CPython 3.12.7** | **PSF License Agreement** | permissive | conserver la notice PSF ; signaler les modifications si l'interpréteur est modifié |
| **Paquets système de Debian bookworm** (image de base) | **mélange GPL-2, GPL-3, LGPL-2.1+ et autres** - `glibc` est LGPL-2.1+, de nombreux utilitaires sont GPL | **copyleft** | **mettre à disposition le code source correspondant** des composants concernés, ou fournir une offre écrite valable trois ans ; transmettre le texte des licences |

### La plus contraignante - réponse à la question 5.2

Si DermaScan redistribue cette image à un centre de dépistage client, **ce sont les paquets
système Debian de l'image de base qui portent les obligations les plus lourdes.**

BSD, MIT et PSF n'exigent que la conservation des mentions de copyright et du texte de
licence - une formalité documentaire. Les composants **GPL et LGPL** de la distribution de
base imposent en revanche la **mise à disposition du code source correspondant** (ou une
offre écrite valable trois ans), y compris pour des composants que personne n'a choisi
d'ajouter : ils arrivent avec la ligne `FROM`.

Point souvent négligé : **distribuer une image Docker est une distribution de binaires** au
sens de ces licences. Pousser l'image dans un registre accessible au client déclenche les
mêmes obligations qu'expédier un CD de logiciel.

C'est aussi ce qui justifie la question 5.1 : l'audit doit porter sur l'inventaire réel
(`pip freeze` + paquets système), pas sur le `requirements.txt`.

---

## Rubrique 14 - limites connues et risques résiduels

### 1. Serveur de développement utilisé comme serveur applicatif

L'application est servie par **Werkzeug 3.1.9**, le serveur de développement intégré de
Flask. Le conteneur l'annonce lui-même à chaque démarrage, dans ses propres logs :

```
WARNING: This is a development server. Do not use it in a production deployment.
Use a production WSGI server instead.
```

Conséquences : pas de gestion de la concurrence au-delà du mono-thread par défaut, pas de
limitation du nombre de connexions, pas de durcissement contre les requêtes malformées, et
des performances sans rapport avec un serveur de production.

**Correctif attendu :** passer à Gunicorn (ou Uvicorn pour une bascule ASGI en séance 2),
avec un nombre de workers calibré.

### 2. Aucune analyse de vulnérabilités, aucun SBOM

L'image n'a été soumise à **aucun scanner** - ni Trivy, ni Grype, ni `docker scout`. Aucun
SBOM (*Software Bill of Materials*) n'a été produit ni joint à l'artefact.

Le risque est documenté par la fiche elle-même : `docker history` montre que les couches de
l'image de base datent de **23 mois**. Elles embarquent donc, avec quasi-certitude, des CVE
publiées et corrigées depuis dans `python:3.12-slim` ou dans les paquets Debian sous-jacents.

**Correctif attendu :** intégrer un scan bloquant dans la CI, et définir une politique de
rafraîchissement de l'image de base.

### 3. Aucune signature, aucune attestation vérifiée

Le registre a `trustPolicy: disabled` et `quarantinePolicy: disabled`. Rien ne permet, côté
consommateur, de vérifier **que l'image tirée est bien celle construite ici** et qu'elle n'a
pas été remplacée dans le registre. Le digest garantit l'intégrité du contenu, pas son
origine.

En séance 3, un hôte Azure tirera cette image en faisant confiance au seul tag. Un tag est
réassignable : rien n'empêche techniquement qu'un autre contenu porte `0.1.0` demain.

**Correctif attendu :** signature avec Cosign et vérification à l'admission. Note : le
verrouillage de contenu et les tokens à portée limitée exigent le SKU Premium.

### 4. Aucune limite de ressources, aucune sonde d'orchestration câblée

Le conteneur est lancé sans `--memory` ni `--cpus` : il peut consommer toute la mémoire de
l'hôte, et entraîner l'éviction d'autres charges sur la même machine.

L'endpoint `/health` existe et répond correctement, mais il n'est **câblé à aucun mécanisme**
- ni `HEALTHCHECK` dans le Dockerfile, ni sonde *liveness* / *readiness* côté orchestrateur.
Un processus vivant mais bloqué ne serait détecté par personne.

**Correctif attendu :** limites de ressources explicites, et déclaration des sondes dans le
manifeste de déploiement en séance 3.

### 5. Secrets et configuration - risque non couvert à ce stade

L'application ne manipule aujourd'hui aucun secret, ce qui rend la question théorique. Mais
le mécanisme de configuration retenu (variables d'environnement, vérifié en question 3.6)
**n'est pas adapté aux secrets** : une variable d'environnement est lisible par
`docker inspect`, apparaît dans les journaux d'orchestrateur, et se retrouve dans les
exports de configuration.

Dès la séance 2, si l'API d'inférence doit accéder à un stockage ou à une base, il faudra un
magasin dédié (Azure Key Vault) plutôt qu'un `-e`.

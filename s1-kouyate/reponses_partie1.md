# Partie 1 - Fondamentaux du cloud

**Séance 1 · Industrialisation de l'IA dans le Cloud · Ynov Campus Montpellier**
Auteur : Issa KOUYATÉ - M2 Data Engineering - 6 octobre 2026

---

## Tableau de décisions

| Décision | Contrainte | Valeur retenue |
|---|---|---|
| Suffixe personnel | 4 à 6 car., minuscules et chiffres | `ik42` |
| Région Azure | une seule, la même partout | `germanywestcentral` |
| Nom du groupe de ressources | préfixé `rg-dermascan-registre-` | `rg-dermascan-registre-ik42` |
| Nom du registre ACR | minuscules et chiffres, unique sur Azure | `acrdermascanik42` |
| Nom de l'image | ce que l'image contient, pas mon nom | `dermascan-health` |
| Tag de version initial | versionnage sémantique | `0.1.0` |
| Image de base Python | variante légère, version fixée, jamais `latest` | `python:3.12.7-slim-bookworm` |
| Répertoire de travail dans l'image | chemin absolu, le même dans Dockerfile et CMD | `/app` |
| Port d'écoute de l'application | cohérent entre `EXPOSE`, `PORT` et les `-p` | `8000` |
| `uid` de l'utilisateur d'exécution | non nul, au-delà de 10000 | `10001` |

### Région - décision initiale, et pourquoi elle a dû changer

Le choix initial était `francecentral` : DermaScan traite des images de lésions cutanées,
donc de la donnée de santé au sens de l'article 9 du RGPD. Maintenir l'hébergement sur le
territoire national simplifie la démonstration de conformité et réduit la latence depuis des
centres de dépistage français.

Ce choix s'est révélé **impossible à appliquer**. La création du registre a été refusée en
`francecentral`, puis en `westeurope`, avec le code `RequestDisallowedByAzure`. L'inspection
des stratégies (`az policy assignment list`) a révélé une assignation nommée
**« Allowed resource deployment regions »**, appliquée à l'abonnement Azure for Students,
qui n'autorise le déploiement que dans cinq régions :

```
germanywestcentral · switzerlandnorth · italynorth · spaincentral · polandcentral
```

**Région finalement retenue : `germanywestcentral`** (Francfort). Elle reste dans l'Union
européenne, ce qui préserve l'argument de résidence des données pour un traitement relevant
de l'article 9 ; on y perd seulement la résidence strictement française.

`switzerlandnorth` a été écartée volontairement : la Suisse est un **pays tiers** au sens du
RGPD, couverte par une décision d'adéquation mais exigeant une justification supplémentaire
dans un dossier de conformité portant sur de la donnée de santé.

---

### Question 0.1 - Unicité globale du nom de registre ACR

Le nom du registre devient un **nom DNS public** (`<nom>.azurecr.io`) : Azure expose chaque
registre comme un point de terminaison HTTPS joignable depuis Internet, et deux registres ne
peuvent pas partager le même FQDN. L'unicité du nom n'est donc pas une contrainte
d'organisation interne, mais la conséquence directe d'un espace de noms DNS partagé par tous
les clients d'Azure.

**Vérification empirique :** `az acr check-name --name acrdermascanik42` a renvoyé
`NameAvailable: True` et, dans la même réponse, le futur `AvailableLoginServerName` :
`acrdermascanik42.azurecr.io`. Azure confirme ainsi explicitement que le nom et l'adresse
DNS sont une seule et même chose.

---

## 1.1 - Les trois modèles de service

| Modèle | Ce que le fournisseur gère à ma place | Ce qui reste à ma charge | Exemple de service Azure |
|---|---|---|---|
| **IaaS** | Le matériel, le réseau physique, la couche de virtualisation | Le système d'exploitation, ses mises à jour, le runtime, l'application, les données | Machine virtuelle (Azure Virtual Machines) |
| **PaaS** | Tout l'IaaS, plus le système d'exploitation et ses correctifs, le runtime d'exécution, la mise à l'échelle et la haute disponibilité de la plateforme | Le code de l'application, sa configuration, ses dépendances applicatives, les données, et le dimensionnement demandé | Azure App Service |
| **SaaS** | La totalité de la pile, application comprise : infrastructure, OS, runtime, code applicatif, mises à jour fonctionnelles | Les données saisies, les comptes et les droits d'accès, le paramétrage fonctionnel offert par l'éditeur | Microsoft 365 |

## 1.2 - Où s'arrête ma responsabilité

| Couche | Dernier modèle où c'est à moi |
|---|---|
| Correctifs de sécurité du système d'exploitation | **IaaS** |
| Version du runtime Python | **PaaS** |
| Code de l'application | **PaaS** |
| Dimensionnement du nombre d'instances | **PaaS** |
| Mes données métier | **SaaS** |

> Lecture de la ligne « version du runtime Python » : en PaaS, c'est encore moi qui déclare
> la version que la plateforme doit servir ; en SaaS, la question ne se pose plus, il n'y a
> plus de runtime à moi.

### Question 1.1 - L'élément à ma charge dans les trois modèles

C'est **la donnée métier** : elle reste sous ma responsabilité en IaaS, en PaaS comme en
SaaS.

Conséquence RGPD directe : externaliser l'infrastructure n'externalise pas la responsabilité
du traitement. DermaScan reste **responsable de traitement** au sens de l'article 4, le
fournisseur cloud n'étant que **sous-traitant** (article 28). Il en découle des obligations
qu'aucun contrat de service ne transfère : base légale du traitement, information des
patients, minimisation, durée de conservation. Et pour des images de lésions cutanées -
donnée de santé, article 9 - s'y ajoutent une analyse d'impact (AIPD) et un choix de région
qui tienne compte du lieu d'hébergement.

## 1.3 - Les cinq caractéristiques NIST (SP 800-145)

| Caractéristique NIST | Traduction opérationnelle |
|---|---|
| Libre-service à la demande | Je crée une ressource sans ouvrir de ticket ni attendre l'accord d'un humain. |
| Accès réseau large | J'atteins la ressource depuis n'importe quel poste connecté, via des protocoles standards, sans matériel ni client propriétaire. |
| Mise en commun des ressources | Mon conteneur tourne sur du matériel partagé avec d'autres clients, dont j'ignore - et n'ai pas à connaître - l'emplacement physique exact. |
| Élasticité rapide | Je passe d'une instance à vingt puis je reviens à une en quelques minutes, en suivant la charge au lieu de provisionner pour le pic. |
| Service mesuré | Chaque heure de registre et chaque Go stocké sont comptés et facturés, et je lis cette consommation dans Cost Management. |

**Trois de ces caractéristiques ont été observées directement pendant la séance :** le
libre-service (compte créé et registre provisionné sans aucune intervention humaine), l'accès
réseau large (pilotage du même abonnement depuis le portail web et depuis PowerShell avec
`az`), et le service mesuré (compteur `Coûts de Octobre` visible dès la première minute,
à `0,00 $US`).

### Question 1.2 - Celle qui rend le nettoyage obligatoire

**Le service mesuré.** La facturation porte sur la **réservation** de la ressource, pas sur
son usage : un registre que personne n'interroge est compté exactement comme un registre
sollicité, et le compteur tourne la nuit et le week-end. Une ressource oubliée consomme donc
du crédit sans produire aucune valeur - d'où une suppression qui doit être **décidée**, pas
espérée.

Dans ce module, la sanction n'est d'ailleurs pas financière mais pédagogique : un crédit
épuisé fait basculer l'abonnement sur l'offre Starter, qui interdit les fournisseurs
`Microsoft.ContainerRegistry` et `Microsoft.ContainerInstance`. On ne perd pas la possibilité
de payer, on perd le registre - donc l'artefact que les séances suivantes consomment.

## 1.4 - Exploration du portail Azure

### Mesure 1 - relevé d'exploration

| # | Observation | Valeur relevée |
|---|---|---|
| # | Observation | Valeur relevée |
|---|---|---|
| 1 | Champs obligatoires de l'écran de création d'un Container Registry | **5** : abonnement, groupe de ressources, nom du registre, emplacement, référence SKU |
| 2 | Identifiant de l'abonnement, et son état | `fec0c6a0-752a-453e-95fc-4c30318138e4` - état **Actif** |
| 3 | Nombre de groupes de ressources existants | **0** au début de la séance (page vide) ; **1** après création de `rg-dermascan-registre-ik42` |
| 4 | Crédit restant, à la date d'aujourd'hui | **100,00 $US** sur 100,00 - relevé le **06/10/2026**, expiration le 06/10/2027 |
| 5 | Un quota qui limiterait la création de dix VM | **Total Regional vCPUs** - le quota de vCPU par région |
| 6 | À quoi sert l'onglet Étiquettes (Tags) | Attacher à une ressource ou à un groupe des paires clé-valeur librement définies, qui servent à imputer analytiquement les coûts dans Cost Management, à filtrer l'inventaire, et à porter des décisions d'exploitation lisibles par un tiers. |

**Observation 1 - corroboration.** Ces cinq champs sont exactement les paramètres exigés par
la commande équivalente en ligne de commande :
`az acr create --resource-group --name --sku --location`, l'abonnement étant fixé en amont par
`az account set`. Le portail et le CLI demandent la même chose, présentée différemment.

**Observation 5 - pourquoi le quota de vCPU et non un quota de VM.** Azure ne limite pas le
*nombre* de machines virtuelles, mais la somme de leurs processeurs virtuels dans une région.
Dix VM de taille modeste consomment dix fois leur nombre de vCPU : c'est ce total qui atteint
le plafond en premier. Un quota exprimé en nombre de VM n'aurait d'ailleurs aucun sens, une
VM pouvant aller de 1 à plus de 100 vCPU.

**Observation 6 - vérification pendant la séance.** Les quatre étiquettes posées sur le groupe
de ressources en partie 2 illustrent chacun de ces usages : `projet=dermascan` pour
l'imputation des coûts, `role=registre` pour le filtrage, `proprietaire=issa.kouyate` pour
savoir qui contacter, et `a_detruire=2027-09-30` pour porter la décision de fin de vie. Sans
cette dernière, la ressource survivrait par inertie plutôt que par décision.

### Classement des services

| Service Azure | Modèle |
|---|---|
| Azure Virtual Machines | IaaS |
| Azure App Service | PaaS |
| Azure Container Registry | PaaS |
| Azure Machine Learning (espace de travail managé) | PaaS |
| Microsoft 365 | SaaS |

> ACR est un PaaS et non un SaaS : Azure gère le stockage, la réplication et l'API du
> registre, mais le contenu - mes images, leurs tags, leur cycle de vie - reste entièrement
> mon affaire. Un SaaS me livrerait une application finie, pas un conteneur à remplir.

### Question 1.3 - Le groupe de ressources

**Une ressource peut-elle appartenir à deux groupes simultanément ?**
Non. L'appartenance est exclusive : une ressource vit dans exactement un groupe à un instant
donné. Elle peut être *déplacée* d'un groupe à un autre - le portail propose d'ailleurs un
lien « déplacer » sur la page du registre - mais jamais partagée entre les deux.

**Que se passe-t-il pour les ressources contenues lorsqu'on supprime le groupe ?**
Elles sont supprimées avec lui, toutes, de façon irréversible et sans corbeille. C'est ce qui
fait du groupe de ressources le bouton d'arrêt d'urgence du module : une seule commande
suffit à garantir qu'il ne reste rien qui facture.

**La région du groupe contraint-elle la région des ressources qu'il contient ?**
Non. La région du groupe détermine uniquement l'emplacement où sont stockées ses
**métadonnées** - l'enregistrement de son contenu dans Azure Resource Manager. Elle compte
malgré tout : si cette région subit une panne, les opérations de **gestion** sur le groupe
(créer, modifier, supprimer une ressource) peuvent devenir indisponibles, même si les
ressources elles-mêmes, hébergées ailleurs, continuent de tourner.

**Vérification pendant la séance :** lorsque la création du registre a été refusée en
`francecentral`, le groupe de ressources, lui, avait été créé sans difficulté dans cette même
région. La stratégie de régions autorisées s'applique donc aux ressources déployées, pas au
conteneur logique qui les regroupe. Le groupe a malgré tout été recréé en
`germanywestcentral`, par cohérence avec la décision « une seule région, la même partout » -
par choix de lisibilité, non par nécessité technique.
# Séance 3 — Faisabilité et choix de la cible

**Industrialisation de l'IA dans le Cloud · Ynov Montpellier · M2**
Auteur : Issa KOUYATÉ — 26/10/2026

---

## Tableau de décisions

| Décision | Valeur |
|---|---|
| Suffixe personnel (identique à S1) | `ik42` |
| Région Azure | `germanywestcentral` |
| Groupe de ressources | `rg-dermascan-s3-ik42` |
| Registre ACR existant (S1) | `acrdermascanik42` |
| Dépôt et tag de l'image S2 | `dermascan-api:1.0.0` |
| Plan de service | `plan-dermascan-ik42` |
| Application web | `dermascan-api-ik42` |

**Pourquoi `germanywestcentral`.** C'est la région de mon registre (S1), et elle figure dans la liste des régions autorisées par la politique de l'abonnement (voir mesure 1). La France n'y figure pas. Garder la même région que le registre évite un transfert inter-régions à chaque pull.

## Prérequis vérifiés

| Contrôle | Résultat |
|---|---|
| `az account show` | Azure for Students, état `Enabled`, tenant Ynov |
| Azure CLI | 2.91.0 (≥ 2.60) |
| Docker | 29.5.3, démon actif |
| Python pour Locust | 3.11 (3.14 écarté : dépendances compilées de Locust) |
| Dépôts du registre | `dermascan-api` et `dermascan-health` |
| `charge.json` de S2 | 40 colonnes, égal au nombre annoncé par `/model/info` |

---

## Question 0.1 — Unicité du nom et point de vue de l'attaquant

Le nom devient un sous-domaine public `dermascan-api-ik42.azurewebsites.net`, résolu par n'importe qui. Contrairement au registre, qui exige une authentification pour toute lecture, l'application web est **ouverte par défaut** : un attaquant qui devine ou énumère des noms prévisibles (`<produit>-api-<suffixe>`) tombe sur une API sans authentification, et `/model/info` lui livre même la liste des 40 variables et les métriques du modèle.

---

## Mesure 1 — Sondes de faisabilité de l'abonnement

| Sonde | Commande source | Relevé |
|---|---|---|
| Régions autorisées par la politique | `az policy assignment list` | `germanywestcentral`, `switzerlandnorth`, `italynorth`, `spaincentral`, `polandcentral` |
| `Microsoft.Web` | `az provider show` | **NotRegistered** au départ → `az provider register --wait` (80 s) → Registered |
| `Microsoft.ContainerInstance` | `az provider show` | Registered |
| `Microsoft.ContainerRegistry` | `az provider show` | Registered |
| Création du plan App Service Linux | `az appservice plan create --sku B1` | **Succès**, état `Ready`, en 6,8 s |
| Code d'erreur exact | sortie de la commande | Aucun |
| Durée totale de la sonde | chronomètre | 14h13 → 14h22, soit ~9 min (dont 80 s d'enregistrement du fournisseur) |

**Ce qu'apprend la sonde 2.** Sur un abonnement neuf, `Microsoft.Web` n'était pas activé. Sans la sonde, la création du plan aurait échoué avec `MissingSubscriptionRegistration`, un message qu'on interprète facilement à tort comme un manque de droits.

## Mesure 2 — Cible retenue

| Élément | Réponse |
|---|---|
| Cible retenue | **A — App Service for Containers** |
| Fait déclencheur | Plan Linux B1 créé, statut `Ready`, aucune erreur |
| Heure de la décision | 14h22 (9 min après le début, sous la limite de 20 min) |
| Ce que la cible A ne permettra pas de montrer | La mise à l'échelle horizontale mesurée (plusieurs répliques derrière un répartiteur, comme en cible C) : un second worker sur le plan est facturé en plus, le test de charge reste donc sur une seule instance |

---

## Question 1.1 — Niveau d'abstraction des trois cibles

| Cible | Modèle | Ce que je ne gère pas | Ce qui reste à ma charge |
|---|---|---|---|
| App Service for Containers | **PaaS** | Matériel, OS, moteur de conteneur, répartiteur, TLS/HTTPS, redémarrage, mise à l'échelle | L'image, la configuration (réglages), le port, la sonde de santé |
| Azure Container Instances | **CaaS** | Matériel, OS, moteur de conteneur | Le conteneur, ses ressources déclarées, l'accès au registre (principal de service), le TLS, la mise à l'échelle (manuelle) |
| Docker sur mon poste | **IaaS** (sur mon propre matériel) | Rien | Tout : machine, OS, moteur, réseau, disponibilité, correctifs |

## Question 1.2 — Coût du SKU et autonomie du crédit

| Relevé | Valeur |
|---|---|
| Prix B1 Linux, `germanywestcentral` | 0,0159 €/h (API publique `prices.azure.com`, 26/10/2026) |
| Soit | 0,38 €/jour, **11,61 €/mois** (730 h) |
| Crédit restant (Education › Vue d'ensemble) | **86 € sur 88 €**, expiration le 06/10/2027 |
| Jours de B1 continu finançables | 86 / 0,0159 ≈ 5 400 h ≈ **225 jours** (hors registre ACR, ~0,16 €/jour) |

Un seul B1 semble anodin. Mais un plan est facturé à l'heure, trafic ou non : un plan plus gros oublié, ou plusieurs plans un week-end, et le crédit fond. Un crédit épuisé bascule l'abonnement sur l'offre Starter, qui interdit `Microsoft.ContainerRegistry` : je perdrais mon registre, donc les séances 4 et 5. C'est ce qui justifie le nettoyage systématique de fin de séance.

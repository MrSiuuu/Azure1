# Séance 3 — Déploiement, configuration, nettoyage

**Industrialisation de l'IA dans le Cloud · Ynov Montpellier · M2**
Auteur : Issa KOUYATÉ — 26/10/2026

URL publique : `https://dermascan-api-ik42.azurewebsites.net` (détruite en fin de séance)

> **Seuil de décision appliqué en production : `0.347616`** — seuil de la séance 2 (MESURES.md de S2, mesure 9), choisi pour un rappel visé de 90 %.
> Valeur abaissée testée en 3.3 : `0.0347616` (dixième). Valeur relevée testée en complément : `0.8` (voir mesure 8).

---

## Partie 2 — Déploiement depuis ACR

### Mesure 3 — Image exacte déployée

| Relevé | Valeur |
|---|---|
| `loginServer` | `acrdermascanik42.azurecr.io` |
| Nom complet (`IMAGE_FULL`) | `acrdermascanik42.azurecr.io/dermascan-api:1.0.0` |
| Digest du tag déployé | `sha256:35654575fabaf125bc5a169a45c03dd9fbc43db0bca7cbf9a24e822d1f4f76aa` |
| Architecture | `amd64` (OS `linux`) |
| Date de publication | 2026-10-09T12:09:26Z |

Un seul manifeste dans le dépôt : l'image a été construite en S2 avec `--provenance=false`, donc ni index ni attestation. Taille : 149 795 556 octets. Le digest est identique à celui relevé au push de S2.

### Question 2.1 — Tag déployé, digest relevé

Un tag est une étiquette **réassignable**. Si un camarade poussait demain une autre image sous `dermascan-api:1.0.0`, le prochain redémarrage de mon service tirerait silencieusement ce nouveau contenu : même URL, même tag, autre code. Le digest relevé aujourd'hui sert alors deux fois : il **prouve** ce qui tournait le 26/10 (audit), et il permet de redéployer exactement cette image avec `dermascan-api@sha256:3565…`. La bonne pratique est de déployer directement par digest.

### Mesure 4 — Avant tout octroi de droit sur le registre

| Relevé | Valeur |
|---|---|
| Code HTTP | **503** |
| Durée de la réponse | 0,30 s |
| Contenu de la page | Page HTML générique d'Azure « 503 Service Unavailable — The server is unable to handle your request right now », avec un lien Troubleshoot. Aucune mention de la cause |

À ce moment, Azure affichait l'application en état `Running` : l'application existait, mais son conteneur n'avait jamais pu démarrer. `WEBSITES_PORT=8000` a été posé dès la création.

### Mesure 5 — Identité managée et rôle

| Relevé | Valeur |
|---|---|
| `principalId` de l'identité managée | `c4b95042-5a51-40a1-be05-1e890cc9d870` |
| Rôle accordé | **AcrPull** |
| Portée exacte | `/subscriptions/fec0c6a0-752a-453e-95fc-4c30318138e4/resourceGroups/rg-dermascan-registre-ik42/providers/Microsoft.ContainerRegistry/registries/acrdermascanik42` |
| Délai attribution → premier pull réussi | ~2 min 30 (rôle vers 14h28, restart 14h29:54, premier 200 à 14h30:53) |

`acrUseManagedIdentityCreds` = `true`. Dans `az role assignment list`, la colonne Principal affiche `920be48f-9a75-4e39-8b1b-4d8cb5f27146` : c'est l'identifiant d'application de la même identité, pas un autre principal.

### Question 2.2 — Les rôles plus larges

- **AcrPush** aurait fonctionné : l'application pourrait en plus **pousser** des images, donc écraser un tag que tout le parc tire.
- **Contributor** (sur le registre, ou pire sur l'abonnement, recommandé par facilité dans certains tutoriels) : l'application pourrait **supprimer le registre**, changer son SKU, ou **activer le compte administrateur** et lire son mot de passe.
- La portée compte autant que le rôle : AcrPull limité au seul registre, c'est le moindre privilège à la lettre.

### Question 2.3 — Propagation du rôle

Aucune attente supplémentaire : le premier restart, lancé ~1 min 30 après l'attribution, a réussi. Pour un script automatisé, je ne compterais pas sur cette chance : boucle de sonde sur `/health` avec plusieurs minutes de marge et un second restart si le pull échoue encore.

### Mesure 6 — Premier démarrage

| Mesure | Valeur |
|---|---|
| Restart → premier 200 sur `/health` | **59 s** (14:29:54 → 14:30:53) |
| Codes observés pendant l'attente | `000` (délai client de 30 s dépassé), puis `200` |
| `model_loaded` | `true` |
| Version retournée par `/model/info` | `1.0.0` (entraîné le 2026-10-09, Python 3.14.0, scikit-learn 1.9.1) |
| `probabilite_maligne` et `decision` | `0.750193` → `a_examiner` |
| Seuil appliqué = seuil du paquet S2 ? | **Oui** : `0.3476161828081349` |
| Durée de la 1re requête `/predict` | 0,202 s |
| Durée de la 5e requête identique | 0,458 s |

Série complète : 0,202 / 0,163 / 0,296 / 0,178 / 0,458 s.

### Question 2.4 — Écart entre la 1re et la 5e requête

L'écart est **faible et non monotone** : la 5e est la plus lente, la 2e la plus rapide. Pas de « première requête lente », car un `/predict` avait déjà été servi juste avant : le modèle était en mémoire.

| Hypothèse | Comment la confirmer ou l'écarter aujourd'hui |
|---|---|
| **Variabilité réseau** : chaque `curl` rouvre une connexion TLS vers l'Allemagne | Décomposer chaque appel avec `-w "%{time_connect} %{time_appconnect} %{time_starttransfer}"`. Si l'écart est dans la connexion et pas dans le temps serveur, c'est le réseau. La mesure 14 (connexion médiane 59,8 ms) va dans ce sens |
| **Worker Gunicorn unique occupé** par une autre requête (sonde de la plateforme, autre appel) au même moment | Rejouer 30 appels espacés et regarder si les valeurs hautes coïncident avec les sondes visibles dans `az webapp log tail` ; ou comparer avec un appel `/health` simultané |

---

## Partie 3 — Configuration d'exécution

### 3.1 — Réglages posés

`PORT=8000`, `MODEL_VERSION=1.0.0`, `LOG_LEVEL=info`, `ENVIRONMENT=recette`, `SEUIL=0.347616`.
Liste effective après 3.1 : 7 réglages, dont `WEBSITES_ENABLE_APP_SERVICE_STORAGE=false`, ajouté automatiquement par Azure.

### Question 3.1 — `WEBSITES_PORT` et `PORT`

- `WEBSITES_PORT` est lu par **la plateforme** : il lui dit sur quel port du conteneur sonder et router le trafic.
- `PORT` est lu par **mon code** : le `CMD` de l'image lance Gunicorn sur `0.0.0.0:${PORT:-8000}`.
- Ils doivent désigner le **même port réel**. S'ils diffèrent, l'application est saine mais le service est mort : la plateforme frappe à une porte où personne n'écoute. Vérifié en partie 4 : avec `WEBSITES_PORT=9999` et Gunicorn sur 8000, la plateforme le dit textuellement (`Port mismatch detected`).

### Mesure 7 — Visibilité du secret `INFERENCE_LOG_SALT`

Le sel a été engendré localement (16 octets du générateur cryptographique de Windows, équivalent de `openssl rand -hex 16`) et poussé en réglage, sans jamais être écrit dans un fichier.

| Contrôle | Observation |
|---|---|
| Masqué dans la sortie du CLI ? | **Non** : `az webapp config appsettings list` l'affiche en clair |
| Visible dans le portail (Variables d'environnement) ? | Masqué par défaut, mais **un clic sur « Afficher une valeur »** le révèle en clair à toute personne ayant accès à l'application |
| Lisible par un processus du conteneur ? | **Oui** : c'est une variable d'environnement, lisible via `os.environ`, exactement comme `SEUIL` est lu par `app.py` |

**Incident pendant la mesure.** La première valeur, affichée en clair par le CLI, a été recopiée hors du terminal. Je l'ai considérée comme compromise et j'ai régénéré le sel immédiatement. Le second n'a jamais été affiché : contrôle par sa seule longueur (32 caractères).

### Question 3.2 — Le coffre-fort

Le service est **Azure Key Vault**. Avec l'identité managée créée en 2.3 et le rôle « Key Vault Secrets User » sur le coffre, le réglage contiendrait seulement une **référence** (`@Microsoft.KeyVault(SecretUri=…)`) au lieu de la valeur : le sel disparaîtrait complètement de la configuration, du CLI et du portail, et sa rotation se ferait dans le coffre sans toucher à l'application.

### Mesure 8 — Configuration complète, sonde et épreuve du seuil

| Relevé | Valeur |
|---|---|
| Chemin de sonde enregistré | `/health` |
| Restart explicite → premier 200 | **≤ 1 min 43** (restart 14:40:27, 200 à 14:42:10 ; borne haute, la boucle ayant été lancée après le restart). Codes : `000` puis `200` |
| `appsettings set` du seuil abaissé → nouveau seuil visible | **49 s** (14:48:57 → 14:49:46), sans coupure |
| Nombre total de réglages | **8** (`WEBSITES_ENABLE_APP_SERVICE_STORAGE`, `WEBSITES_PORT`, `PORT`, `MODEL_VERSION`, `LOG_LEVEL`, `ENVIRONMENT`, `SEUIL`, `INFERENCE_LOG_SALT`) |
| `MODEL_VERSION` apparaît dans `/model/info` ? | La valeur affichée est `1.0.0`, mais elle vient du **paquet sérialisé** : `app.py` ne lit pas `MODEL_VERSION`. Ce réglage est sans effet dans cette image |
| `probabilite_maligne`, seuil S2 | `0.750193` |
| `seuil` et `decision`, seuil S2 | `0.347616` → `a_examiner` |
| `probabilite_maligne`, seuil abaissé | `0.750193` |
| `seuil` et `decision`, seuil abaissé | `0.0347616` → `a_examiner` |

**Pourquoi un essai supplémentaire.** Ma lésion de `charge.json` a une probabilité de 0,75 : elle est au-dessus des deux seuils, donc l'abaissement ne pouvait pas faire basculer sa décision. Pour observer la bascule à entrée identique, j'ai aussi relevé le seuil au-dessus de la probabilité :

| Seuil | `probabilite_maligne` | `decision` | Délai d'apparition |
|---|---|---|---|
| `0.8` | `0.750193` | **`non_prioritaire`** | 54 s, sans coupure |
| Retour à `0.347616` | `0.750193` | `a_examiner` | 57 s, sans coupure |

**Comparaison.** Un `appsettings set` recycle le conteneur **sans coupure observée** (~50 s, l'ancien conteneur répond jusqu'au basculement). Un `restart` explicite coupe le service (`000` observé).

### Question 3.3 — Quelle sonde de santé ?

Je déploie la **version 2** (modèle chargé + inférence de test sur une entrée figée), dans une forme légère. La version 1 introduit le risque central : une instance dont le modèle n'a pas pu être chargé répond 200 sur `/health`, reste dans le routage, et renvoie une erreur sur chaque `/predict` à de vrais praticiens. Mon `/health` actuel est déjà entre les deux : il renvoie 503 si le modèle n'est pas chargé. Le risque de la version 2 est son coût : une inférence par sonde, et une sonde lente sous charge pourrait faire retirer une instance saine ; d'où une entrée minimale et un délai d'expiration généreux.

### Question 3.4 — Le modèle estime, le service décide

1. **Le service** a changé de comportement, pas le modèle : même image, même modèle, même entrée, même probabilité au millionième. Seule la règle de décision (le seuil) a bougé.
2. Non. Le service ne rend pas « les mêmes décisions ». Un rapport qui dirait « le modèle a changé d'avis » serait faux : le modèle a rendu exactement la même estimation, c'est la politique de décision du service qui a changé.
3. Il faut que chaque ligne de journal porte le **`seuil_applique`** (et sa source), voir la grille de la partie 6. Côté plateforme, le **journal d'activité Azure** trace l'opération `appsettings` : qui, quand. Aujourd'hui, mon API ne journalise rien : ce changement serait indétectable a posteriori dans les traces applicatives.
4. Ma position : **un progrès, à condition d'être tracé**. On ajuste le compromis rappel/charge médicale en une commande, sans reconstruire. L'argument adverse : une décision médicale qui change sans revue, sans redéploiement et sans trace, c'est un changement de dispositif hors de tout contrôle qualité. Le seuil devrait passer par la même revue qu'une nouvelle version d'image.

---

## Nettoyage

### Mesure 16 — Inventaire avant destruction

| Relevé | Valeur |
|---|---|
| Nombre de ressources dans le groupe | 2 |
| Types | `plan-dermascan-ik42` (`Microsoft.Web/serverfarms`) ; `dermascan-api-ik42` (`Microsoft.Web/sites`) |
| Registre ACR dans ce groupe ? | Non : il est dans `rg-dermascan-registre-ik42` (S1) |

### Mesure 17 — Contrôles de destruction

L'attribution AcrPull a été supprimée **avant** le groupe, tant que l'identité existait encore.

| Contrôle | Observation |
|---|---|
| Le groupe `rg-dermascan-s3-ik42` apparaît-il encore ? | Non |
| Reste-t-il une attribution de rôle sur le registre ? | Non (`az role assignment list --scope` vide) |
| Le groupe du registre est-il toujours debout ? | Oui, seul groupe restant |
| `az group exists` renvoie | `false` (~1 min après `az group delete --no-wait`) |
| Crédit restant | 86 € sur 88 € (coûts d'octobre : 3,06 €) |
| Écart avec la séance précédente | 09/10 : 88 €, coûts 0,40 € → −2 € de crédit, +2,66 € de coûts |

Côté poste : aucun conteneur de la séance (tout tournait sur Azure), environnement `.venv-locust` supprimé, Docker Desktop quitté.

### Question 7.1 — Pourquoi la destruction est sûre en une commande

Le registre vit dans son **propre groupe** (`rg-dermascan-registre-ik42`), séparé du groupe de séance. Le cycle de vie suit le groupe : `az group delete` sur le groupe de séance ne peut pas toucher le registre. S'il avait été dans le même groupe, il aurait fallu supprimer l'application et le plan **un par un** (`az webapp delete`, `az appservice plan delete`), et poser un **verrou** `CanNotDelete` sur le registre pour se protéger d'une suppression du groupe par erreur.

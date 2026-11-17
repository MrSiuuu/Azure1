# MESURES — TP5 « Optimiser et surveiller » (YNOV)

Issa Kouyaté — séance du 17/11/2026 — dossier `s5-kouyate/`

**Environnement.** Poste Windows avec WSL2 (x86_64, amd64 natif), disque C: presque plein (7,6 Go libres) : torch installé en version CPU. Python 3.12.16 (`~/venv-s5`), torch 2.14.1+cpu, onnx 1.23.2, onnxruntime 1.31.0, Azure CLI 2.91.0, Docker 28.2.2. Registre `acrdermascanik42` avec les tags 1.0.0 et 2.0.0 avant la séance.

## Mesure 1 — Le point de départ (recopié de mon `MESURES.md` de S4)

| Grandeur (S4) | Valeur |
|---|---|
| Empreinte de `modele.pt`, identique à `sha256_poids` | **oui** (`3f334db3a2a143f1…`, la même qu'en S4) |
| Taille de l'image | 1,13 Go |
| Taille du fichier de modèle | 44,8 Mo |
| Démarrage jusqu'au premier `/health` à 200 | ≈ 5 s (local, hors ligne) ; 2 min 02 s sur Azure B1 |
| Mémoire du conteneur au repos | 297 Mio |
| Latence `/predict` p50 / p95, local | 19,6 / 24,9 ms (50 appels, WSL2) |
| Mesure 19 : p50 et p95 au palier le plus chargé sur B1, CPU du plan | palier 30 utilisateurs : p50 220 ms, p95 1 500 ms (8,57 req/s, p99 5 200 ms) ; CPU du plan **non relevé en S4** (en S3 : 100 % aux paliers 75 et 150 utilisateurs) |
| Mesure 20 : part de `3D: white` | **52,80 %** dans mon manifeste (20 294 lésions) ; **52,73 %** dans l'archive Permissive entière (217 477 lésions) |

À titre de contexte (même mesure 20) : 66,33 % chez les 294 positifs de l'archive, et 28,71 % (71,29 % en XP) dans le `train-metadata.csv` complet de S2 (401 059 lésions).

**Question 1.1 — Pourquoi comparer avec tous les cœurs du portable pourrait conclure à l'inverse de B1.**
Sur un portable à huit cœurs, un moteur qui parallélise son calcul sur plusieurs fils paraît plus rapide qu'un moteur limité à un fil. Sur B1, qui n'a qu'un vCPU, ce parallélisme disparaît (les fils se disputent un seul cœur) et le classement peut s'inverser. D'où le protocole de `comparer.py` : un seul fil, pour PyTorch comme pour ONNX Runtime.

**Question 1.2 — Pourquoi jeter les 20 premiers appels ?**
Le premier appel paie des coûts qui n'existent plus ensuite : l'initialisation paresseuse du moteur (allocation des tampons mémoire, préparation du graphe et choix des noyaux de calcul, création du pool de fils) et le chargement à froid des poids et des caches du processeur (pages du fichier lues sur disque une seule fois). Les mesurer fausserait p50 et p95 vers le haut.

## Mesure 2 — L'export

| Relevé | Valeur |
|---|---|
| Taille de `modele.onnx`, comparée à `modele.pt` | 44 775 708 octets (44,8 Mo) ; même taille que `modele.pt` (44,8 Mo en S4) : l'export fige les mêmes poids, sans les réduire |
| Empreinte de `modele.onnx` (16 premiers caractères) | `2c03ed7ef392b627` |
| Écart maximal de logit sur le lot de contrôle | 5,2e-06 |
| L'export relancé une seconde fois donne-t-il la même empreinte ? | oui : l'export refait à l'étape 3.1 donne la même empreinte (`2c03ed7ef392b627`) |

Blancs de l'appel d'export : `input_names=["entree"]` (nom attendu par `comparer.py` et `app.py`) et `external_data=False` (un seul fichier à copier dans l'image).

**Question 2.1 — `reseau.eval()` avant l'export.**
Sans cette ligne, l'export figerait le réseau en mode entraînement : les couches de normalisation par lot (BatchNorm) calculeraient leurs statistiques sur le lot courant au lieu d'utiliser leurs statistiques apprises (et un éventuel Dropout resterait actif). L'écart de logit entre PyTorch (en `eval`) et ONNX l'aurait révélé : il serait grand au lieu d'être de l'ordre de 5e-06.

**Question 2.2 — Pourquoi `onnx.checker.check_model` ne suffit pas.**
Le contrôleur vérifie que le fichier est un graphe ONNX **valide** (structure, types, opset, nœuds bien formés), pas qu'il **calcule la même chose** que le réseau. L'assertion qui le suit compare les logits d'ONNX Runtime à ceux de PyTorch sur un lot de contrôle, dans une tolérance : c'est elle qui prouve l'équivalence numérique.

**Question 2.3 — Axe 0 dynamique, les trois autres fixes.**
On fixe 3 × 128 × 128 parce que le modèle a été entraîné sur des vignettes de cette taille : une autre forme ne correspondrait pas à ce qu'il a appris, et des formes fixes laissent le moteur optimiser le graphe. Une image de 300 pixels envoyée telle quelle serait rejetée par ONNX Runtime (forme d'entrée invalide) : le service doit la redimensionner à 128 × 128 avant l'appel.

## Mesure 3 — Les trois variantes

Seuil servi : 0,000158. Jeu de validation : **4 136 vignettes dont 52 malignes** (l'énoncé annonce 1 058, mon `modele_meta.json` indique 4 136).

| Variante | Taille (Mo) | p50 (ms) | p95 (ms) | Proba de contrôle | Rappel au seuil | Alertes | ROC-AUC | Écart max de proba | Décisions changées |
|---|---|---|---|---|---|---|---|---|---|
| PyTorch | 44,8 | 65,52 | 83,99 | 0,352667 | 0,8846 | 1 716 | 0,8779 | 0 | 0 |
| ONNX | 44,8 | 49,49 | 71,73 | 0,352667 | 0,8846 | 1 716 | 0,8779 | 0,000002 | 0 |
| ONNX int8 | 11,3 | 42,37 | 61,82 | 0,407556 | 0,9038 | 1 772 | 0,8798 | 0,28 | 178 |

Écart maximal de logit d'ONNX float32 : 5,2e-06. Empreintes : float32 `2c03ed7ef392b627`, int8 `ab2f66dbd38effbf`.

## Mesure 4 — Ce que l'int8 change

| Relevé | Valeur |
|---|---|
| Décisions passées en `a_examiner` / passées en `surveillance` | 117 / 61 (soit 56 alertes de plus : 1 772 contre 1 716) |
| Malignes parmi les décisions changées | 1 |
| Rapport des probabilités int8 / PyTorch : médiane, minimum, maximum | 1,098 ; 0,162 ; 9,42 |

Le gain de rappel de l'int8 (+1 maligne) vient de fausses alertes en plus.

**Question 3.1 — Rappel de `comparer.py` contre celui du meta.**
Le meta donne un rappel au seuil de 0,9038 (47 malignes sur 52), `comparer.py` mesure 0,8846 (46 sur 52). L'écart est une seule maligne : **ISIC_6730784**, de probabilité 0,000158, pile sur le seuil de 0,00015823 et passée à `a_examiner = False`. Un rappel posé sur 52 lésions est fragile : une lésion vaut 1,9 point, et une valeur à l'épaisseur du seuil bascule avec l'arrondi (c'est le point de ma question 4.1 de S4). Conclusion : on juge une variante sur les **décisions changées** plutôt que sur le rappel.

**Question 3.2 — ONNX float32 plus rapide que PyTorch ?**
Oui sur mon poste (p50 49,49 ms contre 65,52 ms ; p95 71,73 contre 83,99 ms). Cela ne prouve rien pour B1 : le processeur est différent (un vCPU partagé, plus lent, au jeu d'instructions éventuellement différent) et, sur une machine qui émulerait une autre architecture, les durées changeraient encore. Mon poste est x86_64 natif ; B1 est un seul cœur. Le gain qui reste acquis même si la latence n'avait pas bougé concerne ce qu'il faut **installer** : `onnxruntime` à la place de PyTorch. L'image perd la plus grosse bibliothèque, passe de 1,13 Go à 280 Mo, et compte beaucoup moins de paquets à scanner.

**Question 3.3 — Mes critères du tableau de décisions, sans les modifier.**

| Critère | Seuil | ONNX float32 | ONNX int8 |
|---|---|---|---|
| Écart max de probabilité | ≤ 1e-4 | 0,000002 : ✓ | 0,28 : ✗ |
| Rappel au seuil servi | ≥ 0,88 | 0,8846 : ✓ | 0,9038 : ✓ |
| Décisions changées | 0 | 0 : ✓ | 178 : ✗ |

La variante int8 n'est **pas acceptée** : elle viole deux critères sur trois. Elle n'est **plus le modèle 2.0.0** : changer 178 décisions, c'est se comporter autrement, donc c'est un nouveau modèle, qui devrait porter une nouvelle version (par exemple 2.1.0) et être revalidé. ONNX float32 respecte les trois critères : c'est le même modèle que PyTorch, donc toujours la version 2.0.0.

| Décision de déploiement | Valeur |
|---|---|
| Variante déployée | **ONNX float32** (`modele.onnx`, 44 775 708 octets) |
| Version du modèle servi | **2.0.0** (variante `onnx`) |

**Question 3.4 — Ce qu'il faudrait refaire avant de servir une variante qui change des décisions à des patients réels.**
(1) La **revalider** : rappel au seuil, ROC-AUC et PR-AUC sur un jeu **indépendant**, et par sous-groupe (âge, site, éclairage). (2) **Re-décider le seuil** (le rappel cible de 0,9) et mettre à jour la fiche du modèle et son numéro de version, avec l'accord de l'équipe clinique. Aujourd'hui j'ai fait la première **partiellement** : la comparaison des décisions sur les 4 136 vignettes de validation, mais c'est le jeu qui a servi à fixer le seuil, pas un jeu indépendant, et sans découpage par sous-groupe.

## Questions de la partie 4

**Question 4.1 — Ce qui change dans `app.py` (S5 contre S4).**
- **Moteur d'inférence** : `torch` et `torchvision` sont remplacés par `onnxruntime` (`InferenceSession`, un fil par défaut, réglable par `ORT_THREADS`) ; le modèle devient `modele.onnx`, dont le sha256 est calculé au démarrage.
- **Covariables** : champs de formulaire facultatifs (`age_approx`, `sex`, `anatom_site_general`, `tbp_tile_type`), validés contre un domaine : hors domaine donne un 400, absent est accepté. L'âge est converti en tranche de 10 ans, jamais journalisé brut.
- **Ligne de journal** : une ligne JSON par appel sur la sortie standard, au format S3 (schéma 2.0) ; le patient est pseudonymisé par sha256(sel:id) tronqué à 16 caractères, et rien n'est journalisé sans sel. La décision est calculée une fois (`proba >= seuil`) et réutilisée dans la réponse et dans le journal ; toute erreur 400 est journalisée.
- **`/model/info`** : ajoute `format` (`onnx`), `fichier_servi`, `sha256_fichier_servi` (empreinte du fichier réellement chargé) et `covariables_acceptees`.

**Question 4.2 — Défendre le choix « covariables facultatives à côté de l'image ».**
- Contre l'option 1 (surveiller l'API tabulaire de S2) : cette API reçoit ces colonnes, mais ce n'est pas le trafic de l'API DermaScan ; elle surveillerait une autre population que celle qui est servie.
- Contre l'option 2 (statistique de l'image côté serveur, comme la luminance) : c'est un proxy difficile à interpréter, sans lien direct avec la covariable qui fait varier le modèle (`tbp_tile_type`), et il demanderait sa propre référence.
- Faiblesse du choix : c'est le **client** (le poste de consultation) qui fournit ces valeurs. S'il ment, la surveillance mesure une population fausse sans que personne ne le voie ; s'il les omet, le taux d'absence monte et le PSI se calcule sur moins de données. D'où la validation du domaine à l'entrée et la surveillance du taux d'absence.

**Question 4.3 — Pourquoi 400 pour une modalité inconnue (`UV`) et acceptation pour une modalité absente.**
Une modalité inconnue est une erreur du client (ou du domaine) : si on l'acceptait, elle créerait dans le tableau de bord une modalité absente de la référence (un terme de PSI aberrant) et polluerait le journal. Une modalité absente est légitime (le champ est facultatif) : elle se compte comme « absent », et son taux est un signal à part, surveillé sans fausser la distribution des modalités.

**Question 4.4 — Pourquoi ne pas ajouter le SDK Application Insights aujourd'hui.**
Deux arguments. (1) De la partie 4.3 : l'image démarre hors ligne (`--network none`, premier `/health` en 0,87 s) ; un SDK de télémétrie dépend d'une connexion sortante et d'une chaîne de connexion, alors qu'un `print` sur la sortie standard n'a aucune dépendance et est collecté par le paramètre de diagnostic de la Web App. (2) De la règle zéro CVE : chaque dépendance ajoutée apporte des paquets à scanner (l'image en compte 84, avec 0 CVE) et risque de casser la porte `docker scout --exit-code`.

**Question 4.5 — `chown -R /app` après `COPY model/`.**
Dans `docker history`, la couche du modèle fait 44,8 Mo. Un `chown -R` placé après ce `COPY` recopierait tous les fichiers dans une nouvelle couche : environ 44,8 Mo de plus pour rien. Son absence ne casse rien : l'application ne fait que lire ses fichiers (lisibles par tous) et n'écrit que sur la sortie standard, donc l'utilisateur `appuser` n'a pas besoin d'en être propriétaire.

**Question 4.6 — Pourquoi `**/*.pt` et pas `*.pt`.**
Dans un `.dockerignore`, `*.pt` ne vaut que pour la **racine** du contexte : `model/modele.pt` (un sous-dossier) entrerait dans le contexte. `**/*.pt` vaut à toute profondeur. De même, `*.csv` seul laisserait entrer les CSV des sous-dossiers (`donnees/train-metadata.csv`, `sorties/`…) et `*.zip` les archives de vignettes, énormes, dans le contexte de construction.

## Mesure 5 — L'image S5

| Relevé | Valeur |
|---|---|
| Code retour de `docker scout cves --exit-code`, et décompte C / H / M / L | **0** ; 0 C / 0 H / 0 M / 0 L (84 paquets, aucun paquet vulnérable) |
| Durée de construction | 36,9 s (`real`) ; 35,8 s dans Docker ; contexte transféré 44,80 Mo (le modèle ONNX seul) |
| `probabilite_maligne` de l'image de contrôle servie par le conteneur | 0,352667 |
| Probabilité de contrôle de la même variante dans la mesure 3, et écart | 0,352667 ; écart **0** |
| `sha256_fichier_servi` de `/model/info`, égal à l'empreinte de la variante | **oui** (`2c03ed7ef392b627185a0cdfac17b7bed49b981ce0d1598bfe6cdfbc16c67332`) ; version et `version_deployee` : 2.0.0 ; format : `onnx` |
| Le `patient_ref` journalisé contient-il `IP_0000001` en clair ? | **non** (`f53754c498f76075`) |

Ligne de journal complète d'un appel avec covariables :

```json
{"ts": "2026-11-17T14:04:09.799Z", "request_id": "dd65407e-5903-4a64-861f-a528ec3ddc78", "model_version": "2.0.0", "image_digest": null, "patient_ref": "f53754c498f76075", "probabilite_maligne": 0.352667, "seuil_applique": 0.00015822777138716095, "rappel_cible": 0.9, "decision": "a_examiner", "covariables": {"age_tranche": "60-69", "sex": "male", "anatom_site_general": null, "tbp_tile_type": "3D: white"}, "inference_ms": 14.9, "http_status": 200, "input_schema_version": "2.0", "env": "local"}
```

Un appel avec `tbp_tile_type=UV` renvoie 400 « covariable invalide », journalisé avec `http_status` 400 et sans probabilité ni décision. `image_digest` vaut `null` en local (renseigné sur Azure).

Contrôles de l'image : démarrage avec `--network none` : `/health` répond, donc l'image n'a besoin d'aucun téléchargement au démarrage. `docker history` : couche des dépendances 168 Mo, python 49,1 Mo, modèle 44,8 Mo (couche séparée), `app.py` 7,58 ko, `adduser` 3,53 ko. `.dockerignore` : ligne `**/*.pt` ajoutée (absente de la version distribuée) ; aucun `.pt` dans le contexte de construction.

Preuve en ligne : `/model/info` sur la Web App Azure renvoie le même `sha256_fichier_servi` que le `sha256sum` local de `api-s5/model/modele.onnx`. Les captures du scan et de `/model/info` sont dans `captures/`.

## Mesure 6 — S4 contre S5, sur mon poste

| Grandeur | S4 | S5 |
|---|---|---|
| Taille de l'image | 1,13 Go | 280 Mo (`docker images`) ; 135 Mo (`docker scout`) |
| Taille du fichier de modèle | 44,8 Mo | 44,8 Mo (44 775 708 octets) |
| Démarrage jusqu'au premier `/health` à 200 (hors ligne) | ≈ 5 s | 0,87 s |
| Mémoire au repos | 297 Mio | 155,4 MiB (156,1 MiB après 2 appels) |
| Latence `/predict` p50 / p95, 50 appels | 19,6 / 24,9 ms | 19,9 / 24,7 ms |
| Latence p50 / p95 sous `--cpus 1`, `ORT_THREADS` par défaut (1) | — | 18,2 / 20,2 ms |
| Latence p50 / p95 sous `--cpus 1`, `ORT_THREADS=8` | — | 190,8 / 287,5 ms |
| Architecture du poste | amd64 natif | amd64 natif (WSL2) |

Lecture : la latence locale n'a pas bougé (19,9 contre 19,6 ms) ; ce que l'image a gagné, c'est du **poids** (taille ÷ 4 et mémoire presque ÷ 2) et du **démarrage** (0,87 s au lieu de ≈ 5 s).

**Question 4.7 — L'écart entre les deux dernières lignes de latence.**
Avec `--cpus 1` et 8 fils, huit fils se disputent un seul processeur : le système les ordonnance à tour de rôle (le quota CPU étrangle le conteneur) et les fils perdent leur temps à s'attendre et à changer de contexte. Résultat : environ **10 fois plus lent** (p50 190,8 ms contre 18,2 ms). `app.py` fixe **un fil par défaut** parce qu'ONNX Runtime lit le nombre de cœurs de la machine et non le quota du conteneur. Ce réglage compte partout où un conteneur est limité en CPU sur une machine qui paraît plus grande : le plan B1 (un vCPU), les conteneurs Azure à quota de CPU, et les pods Kubernetes à limites du projet fil rouge.

## Mesure 11 — S4 contre S5 sur B1, mêmes paliers

Locust : `locustfile_s4.py` inchangé (variable `IMAGE_CONTROLE_S4` = `ISIC_0699524.jpg`), 3 min par palier, montée 5/s, hôte = Web App Azure. 0 échec aux deux paliers.

| Palier | S4 : débit, p50, p95 (mesure 19) | S5 : débit, p50, p95 | S5 : CPU max du plan |
|---|---|---|---|
| 1 (10 utilisateurs) | 3,13 req/s ; 120 ms ; 590 ms | 3,29 req/s ; 76 ms ; 190 ms | 19 % |
| 2 (30 utilisateurs) | 8,57 req/s ; 220 ms ; 1 500 ms | 9,10 req/s ; 94 ms ; 780 ms | 55 % |

Détails S5 : palier 1 — `POST /predict` p50 77 ms / p95 210 ms / p99 450 ms, max 589 ms. Palier 2 — `POST /predict` p50 100 ms / p95 810 ms, p99 agrégé 3 400 ms, max 4 142 ms. Le CPU du plan est passé d'environ 100 % en S4 à 55 % au palier 2.

Lecture : p50 ÷ 1,6 au palier 1 et ÷ 2,3 au palier 2 ; p95 ÷ 3,1 et ÷ 1,9. Le débit varie peu parce qu'il est limité par le `wait_time between(1, 5)` du script, pas par le serveur ; le gain se lit sur la latence et le CPU. Une queue lente subsiste (p99 3,4 s au palier 2). Rapports : `captures/13_locust_palier1.html`, `captures/14_locust_palier2.html`.

**Question 5.7 — Mon engagement de S3 tient-il avec S5 ?**
Mon engagement de S3 : « jusqu'à 10 utilisateurs simultanés, 95 % des prédictions en moins de **470 ms**, avec moins de 1 % d'échecs. » Avec S5 il **tient** avec de la marge : à 10 utilisateurs, p95 de 190 ms (210 ms sur `/predict`) et 0 % d'échec. À 30 utilisateurs il **ne tiendrait pas** (p95 780 ms, 810 ms sur `/predict`) : l'engagement reste à 10 utilisateurs. Part du gain : **0 % pour l'int8**, que j'ai refusée (écart de probabilité 0,28, 178 décisions changées). Tout le gain revient donc au **moteur et à l'image allégée** (ONNX Runtime sans PyTorch : image ÷ 4, mémoire presque ÷ 2, démarrage ≈ 5 s → 0,87 s, p50 ÷ 1,6 à ÷ 2,3 sur B1). À titre indicatif, l'int8 aurait réduit la latence d'environ 14 % de plus sur mon poste (p50 42,37 ms contre 49,49 ms pour le float32), mais au prix de 178 décisions changées.

## Décision de déploiement

**ONNX float32 (`modele.onnx`), version 2.0.0**, image 2.0.0 (digest du registre `sha256:ac1755a54776fb4c2942efdab29d1ef133cf3880f7570a5012f9226b2490f7cc`). Variante int8 refusée : elle changerait 178 décisions (écart de probabilité 0,28), donc ce serait un nouveau modèle à revalider.

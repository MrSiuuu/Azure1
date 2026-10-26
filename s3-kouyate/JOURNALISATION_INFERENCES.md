# Séance 3 — Journalisation des inférences

**Industrialisation de l'IA dans le Cloud · Ynov Montpellier · M2**
Auteur : Issa KOUYATÉ — 26/10/2026

**Point de départ (mesure 9).** L'image S2 ne journalise **rien** : ni ligne d'accès Gunicorn, ni trace applicative. Aujourd'hui, une réclamation sur une inférence ne pourrait être instruite avec aucune donnée. Ce document décrit ce que le service **devrait** écrire ; l'implémentation viendra dans l'image suivante.

---

## 6.1 — Grille : que journaliser, que ne jamais journaliser

| Donnée | Journaliser ? | Forme | Justification |
|---|---|---|---|
| Horodatage de la requête, UTC | Toujours | Brut | Sans ordre temporel, aucune reconstitution d'incident |
| Identifiant de corrélation | Toujours | Brut, généré si absent | Seul moyen de relier une ligne de log à une réclamation |
| Version du modèle et digest de l'image | Toujours | Brut | Répond à « quel modèle a produit cette réponse », question n° 1 d'un audit |
| `patient_id` | Toujours | **Pseudonymisé** (`patient_ref`) | Relier les lésions d'un même patient sans l'identifier |
| `isic_id` (lésion) | Jamais | — | Identifiant direct de l'image source ; `request_id` suffit pour retrouver l'appel |
| `age_approx`, `sex` | Toujours | **Généralisé** : tranche de 10 ans, sexe | Covariables de dérive (séance 5) ; la tranche limite la réidentification |
| `anatom_site_general` | Toujours | Brut (6 modalités) | Covariable de dérive, déjà peu précise |
| Valeurs brutes `tbp_lv_*` | Jamais en brut | Sous-ensemble arrondi (voir 6.2) | 30 mesures fines croisées forment une empreinte ; un sous-ensemble arrondi suffit à la dérive |
| Probabilité maligne prédite | Toujours | Brut, 6 décimales | Indispensable à l'audit et à la dérive de score |
| Seuil appliqué et rappel visé | Toujours | Brut, avec la source du seuil | Une décision sans son seuil est inauditable (partie 3) |
| Décision rendue | Toujours | Brut | C'est ce qui a été communiqué au praticien |
| Latence d'inférence | Toujours | Brut, ms | Performance et SLO |
| Code HTTP et message d'erreur | Toujours | Code brut ; message sans charge utile | Diagnostic, sans recopier les valeurs reçues |
| Adresse IP source | Toujours | **Tronquée** (dernier octet masqué), journal d'accès seulement | Sécurité (détection d'abus) ; l'IP complète est une donnée personnelle |
| Identité du praticien | Toujours | Pseudonymisée (identifiant interne) | Responsabilité : qui a déclenché la décision |
| Jeton d'authentification, clé d'API | Jamais | — | Un journal qui fuite ne doit pas donner d'accès |
| Sel `INFERENCE_LOG_SALT` | Jamais | — | Le sel rend la pseudonymisation réversible |

### Question 6.1 — Qualification RGPD des quatre cas

1. **`tbp_lv_*` seules, sans identifiant** : ni article 4 ni article 9 *en principe* — des mesures morphologiques non rattachées à une personne. Réserve : leur précision peut en faire une empreinte (voir 6.2).
2. **Les mêmes avec `patient_id`** : **article 9**. La personne est identifiée, et des mesures d'une lésion cutanée dépistée sont des données concernant sa santé. Le volume (jusqu'à 9 184 lésions pour un patient) aggrave le profilage.
3. **Les mêmes avec `age_approx`, `sex`, `anatom_site_general`, sans `patient_id`** : **article 4 au minimum**, et **article 9** dès que la combinaison rend la personne identifiable. Dans un centre donné, quelques variables croisées suffisent souvent (piège de la quasi-identification).
4. **Probabilité maligne associée à un patient identifiable** : **article 9**. Qu'elle soit **produite** par DermaScan et non collectée ne change rien : le RGPD qualifie la donnée par ce qu'elle révèle, pas par son origine. Une inférence sur la santé d'une personne est une donnée de santé, et DermaScan en est responsable de traitement.

### Question 6.2 — À partir de combien de variables croisées ?

Avec une tranche d'âge, un sexe, un site anatomique et une taille de lésion, un patient d'un centre donné peut redevenir unique dès **3 à 4 variables**. Je ne peux pas le calculer aujourd'hui. La mesure à produire est la **k-anonymat** : pour chaque combinaison de quasi-identifiants, compter combien de patients la partagent (k). Si k = 1 pour une combinaison, ce patient est réidentifiable. On complète par la l-diversité pour vérifier que les k patients ne partagent pas tous le même diagnostic.

### Question 6.3 — Le journal fuite

| Ligne « Toujours » | Ce que l'attaquant en tire |
|---|---|
| Horodatage UTC | Rythme d'activité des centres |
| `request_id` | Rien d'exploitable seul |
| Version et digest | Version exacte à cibler |
| `patient_ref` | Lésions regroupées par patient |
| Tranche d'âge, sexe, site | Quasi-identifiants à croiser |
| Probabilité maligne | Risque de cancer estimé |
| Seuil et rappel | Politique de décision exposée |
| Décision | Patients orientés vers examen |
| Latence | Capacité du service |
| Code HTTP | Erreurs à exploiter |
| IP tronquée | Réseau approximatif du centre |
| Praticien pseudonymisé | Activité par praticien |

**Le cas de `patient_ref` + probabilité.** Tant que le sel ne fuite pas, l'attaquant ne peut pas remonter au patient ; c'est ce qui justifie le « Toujours ». Si le sel fuite aussi, ces deux lignes deviennent sérieuses, d'où l'interdiction absolue du sel dans le journal.

**Une fuite de prédiction est-elle moins grave qu'une fuite de diagnostic ?** Non, pas pour la personne concernée. Une probabilité de 0,75 « maligne » associée à un patient identifiable est **perçue** comme un diagnostic, peut l'inquiéter, l'exposer à une discrimination (assurance, employeur), et elle peut être **fausse** : une fausse alarme qui fuite cause un tort réel. Juridiquement, les deux relèvent de l'article 9.

---

## 6.2 — Format d'une ligne de journal d'inférence

Une ligne JSON par inférence, écrite sur la sortie standard (collectée par la plateforme) :

```json
{"ts": "2026-10-26T14:33:12.481Z", "request_id": "6f1c2b7e-0d4a-4c1e-9a3b-2f8e5d7c1a90",
 "model_version": "1.0.0", "image_digest": "sha256:35654575fabaf125bc5a169a45c03dd9fbc43db0bca7cbf9a24e822d1f4f76aa",
 "patient_ref": "3fa1c09b7e2d4c55", "probabilite_maligne": 0.750193,
 "seuil_applique": 0.347616, "seuil_source": "env", "rappel_cible": 0.9, "decision": "a_examiner",
 "covariables": {"age_tranche": "70-79", "sex": "male", "anatom_site_general": "head/neck",
                 "tbp_tile_type": "3D: white", "clin_size_long_diam_mm": 4.0, "tbp_lv_areaMM2": 6.2},
 "inference_ms": 18.4, "http_status": 200, "input_schema_version": "1.0"}
```

| Champ | Décision |
|---|---|
| `ts` | UTC ISO 8601 à la milliseconde, imposé |
| `request_id` | Repris de l'en-tête `X-Request-ID` s'il est fourni par le poste ; sinon **uuid4 généré par le service** et renvoyé dans la réponse |
| `model_version` | Lue dans le **paquet sérialisé** : mesure 8, `app.py` ignore `MODEL_VERSION`, la variable pourrait mentir |
| `image_digest` | **Le digest**, pas le tag : un tag est réassignable (question 2.1). Injecté au déploiement dans une variable d'environnement |
| `patient_ref` | Pseudonymisation ci-dessous, jamais l'identifiant en clair |
| `probabilite_maligne` | **6 décimales**, comme la réponse de l'API. Arrondir à 2 décimales écraserait les écarts près du seuil (0,347 contre 0,348) et aplatirait la distribution des scores : une dérive de score deviendrait invisible en séance 5 |
| `seuil_applique` | La valeur **effective** au moment de l'appel. Source : variable d'environnement si définie, sinon paquet ; les deux ne disent pas la même chose (la seconde est le seuil validé à l'entraînement, la première une décision d'exploitation), d'où `seuil_source` |
| `decision` | Vocabulaire de S2 : `a_examiner` / `non_prioritaire`. Le service trie, il ne dit jamais « bénin » |
| `inference_ms` | Durée de `predict_proba` seule, entre la fin de la validation et l'obtention de la probabilité ; la latence totale est déjà dans le journal d'accès |
| `http_status` | Code renvoyé à l'appelant |
| `input_schema_version` | À incrémenter dès que le contrat d'entrée change : colonne ajoutée, retirée ou renommée, type modifié, nouvelle modalité acceptée |

**Les covariables (réclamées par la séance 5).** Je **conserve un sous-ensemble** : `age_tranche` (10 ans), `sex`, `anatom_site_general`, `tbp_tile_type`, et deux mesures arrondies, `clin_size_long_diam_mm` (0,5 mm) et `tbp_lv_areaMM2` (0,1 mm²). Ce sont les variables dont la dérive de population se mesure (pic saisonnier, nouveau centre, nouvel appareil d'acquisition). Je n'en garde pas plus, pour limiter la quasi-identification de 6.1. Ne rien garder rendrait la séance 5 impossible sans un second dispositif, par exemple un échantillonnage séparé des entrées vers un stockage dédié à durée courte.

### Pseudonymisation de `patient_id`

`patient_id` n'est pas une variable du modèle : il arriverait hors de la charge utile, dans un en-tête `X-Patient-Ref` émis par le poste de consultation.

```python
import hashlib
import os

def pseudonymiser(patient_id: str) -> str:
    """patient_ref stable dans le temps, mais non réversible sans le sel."""
    SEL = os.environ["INFERENCE_LOG_SALT"]      # jamais en dur dans le code
    return hashlib.sha256(f"{SEL}:{patient_id}".encode("utf-8")).hexdigest()[:16]
```

Concaténation du sel lu dans l'environnement et de l'identifiant, SHA-256, 16 premiers caractères hexadécimaux.

### Question 6.4

1. **Pourquoi le sel.** Sans sel, `sha256(patient_id)` est réversible par force brute : 1 042 patients aux identifiants réguliers, on hache toutes les valeurs possibles et on compare, en quelques millisecondes. Le sel, inconnu de l'attaquant, rend ce dictionnaire impossible à construire.
2. **Stabilité.** Nécessaire : un patient porte jusqu'à 9 184 lésions ; pour l'audit (« toutes les décisions de ce patient ») et le suivi, ses lignes doivent être reliables. Faiblesse : c'est un identifiant persistant ; ses lignes forment un profil complet, et un seul rattachement (une lésion reconnue) dévoile toutes les autres.
3. **Qui remonte au patient.** Seul le **centre de dépistage**, qui détient déjà le `patient_id`, peut recalculer le `patient_ref` et retrouver ses lignes. Chez DermaScan, uniquement une fonction habilitée (DPO ou référent médical), sur demande tracée, via un service qui détient le sel dans Key Vault ; jamais par un accès direct au sel.
4. **Rotation du sel.** Toutes les lignes historiques deviennent **impossibles à relier** aux nouvelles : le même patient obtient un autre `patient_ref`. C'est une **propriété recherchée** si l'on veut une désassociation volontaire (fin de conservation, pseudonymes par période), un **défaut** pour l'audit d'une réclamation ancienne. Une rotation se décide donc avec la politique de conservation : on fait tourner le sel quand les anciennes lignes doivent de toute façon devenir non reliables.

---

## 6.3 — Durées de conservation

| Catégorie | Durée | Besoin qui la justifie | À l'échéance |
|---|---|---|---|
| Journal d'inférence complet (pseudonymisé) | **12 mois** | Instruire une réclamation : l'exemple du TP est un patient qui revient **6 mois** après ; 12 mois couvrent ce délai avec marge, et servent de référence de dérive (séance 5) | Purge des lignes ; seuls les agrégats survivent |
| Journal d'erreurs applicatives | **90 jours** | Diagnostiquer et corriger un défaut, comparer avant et après correctif | Purge |
| Métriques agrégées, sans identifiant | **3 ans** | Suivi de capacité, tendances de dérive et de performance par version de modèle | Conservation ou archivage, aucune donnée personnelle |
| Journal d'accès de la plateforme (IP) | **30 jours** | Détection d'abus et d'incident de sécurité | Purge (rétention de l'espace de logs) |

À valider avec le DPO : la responsabilité médicale peut justifier une conservation plus longue de certaines décisions. Ce serait alors un besoin nommé, avec une durée propre, pas un « au cas où ».

### Question 6.5 — Deux exigences opposées

- **Minimisation des données** (RGPD art. 5.1.c, et limitation de la conservation, art. 5.1.e) : garder le moins possible, le moins longtemps possible.
- **Capacité d'audit a posteriori** (principe de responsabilité, art. 5.2) : pouvoir expliquer une décision contestée des mois plus tard.

Le mécanisme qui satisfait les deux : **l'agrégation** (troisième ligne de la grille). Les lignes individuelles pseudonymisées vivent le temps du besoin d'audit, puis sont réduites en **métriques agrégées sans identifiant** conservées longtemps. On garde le signal (distributions, taux de décision par version et par seuil), on perd la personne.

### Question 6.6 — Où configurer la purge

Dans la **plateforme**, là où les journaux sont réellement stockés : la rétention de l'**espace Log Analytics** ou d'**Application Insights** (et `--docker-container-logging filesystem` avec une durée de rétention pour les fichiers d'App Service, ainsi que tout export vers un compte de stockage, avec sa règle de cycle de vie). Si la purge n'est faite que dans le code applicatif, les **copies de la plateforme survivent** : les lignes envoyées sur la sortie standard ont déjà été collectées et dupliquées ailleurs. Le code croit avoir purgé, la donnée de santé est toujours là, au-delà de la durée annoncée.

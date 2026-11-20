# GOUVERNANCE - Séance 6

## 2.1 Classement AI Act

| Sujet | Usage du service | Niveau proposé | Article ou annexe | Ce qui ferait changer de niveau |
|---|---|---|---|---|
| ISIC approfondi | Aide au diagnostic : estimer la probabilité qu'une lésion de peau soit maligne, pour un clinicien | Haut risque | Art. 6(1) + annexe I (règlement sur les dispositifs médicaux) | Un usage purement recherche ou enseignement, sans usage clinique, sortirait du haut risque |
| DEEP-VOICE | Détecter si une voix est réelle ou convertie, sans dire qui parle | Minimal | Art. 50 (transparence) : vise surtout ceux qui génèrent des voix synthétiques | Dès que la voix sert à identifier une personne, elle devient biométrique : haut risque, annexe III point 1 |
| Eedi | Retrouver l'idée fausse la plus probable derrière une mauvaise réponse d'un élève | Selon l'usage : minimal si c'est une aide à l'enseignant, haut risque si ça évalue les élèves | Annexe III point 3 (éducation) | Si le résultat sert à évaluer les acquis ou à orienter le parcours de l'élève : haut risque |

## Q2.1
Sujet retenu : ISIC approfondi (aide au diagnostic des lésions de peau).
Niveau : haut risque.
Raison : le service estime la probabilité qu'une lésion soit maligne pour aider un clinicien ; un logiciel d'aide au diagnostic est un dispositif médical, donc il relève de l'art. 6(1) et de l'annexe I (règlement sur les dispositifs médicaux).
Conséquence : gestion des risques, qualité des données, traçabilité et supervision humaine, c'est-à-dire ce que construisent les séances 3 à 6.
Ce qui ferait changer de niveau : un usage limité à la recherche ou à l'enseignement, sans usage clinique, le ferait sortir du haut risque.

## 2.2 Ce que je journalise

| Champ | Conservé ? | Transformation | Durée | Besoin nommé |
|---|---|---|---|---|
| ts | oui | aucune | 12 mois | situer l'appel dans une fenêtre de dérive, audit |
| request_id | oui | aucune (identifiant aléatoire) | 12 mois | retrouver une inférence précise en cas d'incident |
| model_version | oui | aucune | durée de vie du modèle + 12 mois | relier l'appel à la version du registre |
| image_digest | oui | aucune (digest de l'image Docker, pas de la photo) | durée de vie du modèle + 12 mois | relier l'appel au scan zéro CVE et au commit |
| patient_ref | oui, pseudonymisé | hachage avec sel gardé hors du journal, jamais l'identifiant en clair | 6 mois | relier plusieurs appels d'un même patient sans l'identifier |
| probabilite_maligne | oui | arrondie à 3 décimales | 12 mois | suivre la distribution des sorties (dérive de sortie) |
| decision | oui | aucune | 12 mois | suivre le taux de « à examiner », audit |
| covariables | oui, réduites | généralisées (âge en tranches, pas de date de naissance) | 12 mois | mesurer la dérive des entrées (PSI) |

## Q2.2
Non : une photo de peau ne se pseudonymise pas par hachage. L'image reste l'image (elle peut identifier la personne, et c'est une donnée de santé, article 9), et un hachage identique pour une même image permet de la retrouver.
Cela interdit de journaliser la vignette elle-même ou toute copie, ainsi que l'identifiant patient en clair.

## Q2.3
Avec de vrais patients, mon journal devient un fichier de données de santé : même pseudonymisé, patient_ref reste une donnée personnelle.
Il faudrait alors une base légale, une durée de conservation justifiée par champ, un hébergement maîtrisé et la possibilité d'effacer les lignes d'un patient.
Je réduirais aussi les champs au strict nécessaire (minimiser), pour ne garder que ce que l'audit exige.

## 2.3 Une ligne de journal mène au commit

| Maillon | Identifiant qui mène au suivant | Où il est écrit | Présent aujourd'hui ? |
|---|---|---|---|
| Ligne de journal | image_digest | ligne JSON sur la sortie standard, lue dans Log Analytics | Oui pour le format (S3/S5), mais model_version (1.0.0) ne correspond pas au registre (voir Q2.5) |
| Image | sha256 du fichier de modèle servi | /model/info (sha256_fichier_servi) et digest de l'image dans le registre ACR | Oui pour DermaScan (S5), pas encore pour le modèle tabulaire |
| Version de modèle au registre | run_id (et tag sha256_modele) | registre MLflow (poste/suivi/mlflow.db) | Oui (v2 promue, repli v1) |
| Run | tag sha256_manifeste | tags du run MLflow | Oui |
| Manifeste de données | champ commit (et sha256 des données) | donnees/manifeste.json | Oui, mais le commit (842f613) est antérieur aux scripts de S6 |
| Commit du code | (fin de chaîne) | historique git | Partiel : les scripts de S6 ne sont pas encore commités |

## Q2.4
Le dernier maillon est rompu : le manifeste ne pointe vers aucun commit (« hors-git »), donc on ne sait pas quel code a produit les données.
Le geste de la partie 3 qui le répare : créer le dépôt git et faire un premier commit avant tout code, puis commiter avant de produire les données, pour que le manifeste enregistre un vrai commit. (Chez moi, il affiche 842f613 parce que le dossier est dans le dépôt Azure1, mais ce commit date d'avant les scripts de S6 : le maillon existe sans pointer vers le bon code.)

## Q2.5
Le journal de S3 écrit un numéro libre (1.0.0) alors que le registre numérote ses versions (dermascan-tabulaire v2).
On fait écrire par promouvoir.py la version du registre dans le modele_meta.json qui part dans l'image, et l'API journalise cette valeur : la ligne de journal et le registre portent alors le même identifiant, et verifier_chaine.py peut les comparer automatiquement.

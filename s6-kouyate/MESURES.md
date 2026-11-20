# MESURES - Séance 6

## Mesure 1
- Graine 42 : 100 054 lignes de test, 130 positifs
- Graine 7 : 101 995 lignes de test, 108 positifs
- Empreinte de manifeste.json (12 premiers caractères) : 5f0d20607679

## Q1.1
Le découpage se fait par patient : on tire 25 % des patients, pas 25 % des lignes. Chaque patient a un nombre de lésions différent et les cas positifs se concentrent sur certains patients, donc lignes et positifs de test changent selon les patients tirés.

## Mesure 2 (reference-g42)
- PR-AUC : 0.0501
- Précision au rappel cible (90 %) : 0.0041
- Seuil : 0.2864
- Durée : 38 s
- Run : fcad9f897124444eb86f9eae63e96b58

## Q1.2
Seuil de reference-g42 : 0.2864. Le seuil du modèle de S2 est dans son paquet de modèle (pas dans un fichier texte) : comparaison à compléter.
S'il est identique, la chaîne est reproductible (mêmes données, même découpage, même graine, même code). S'il diffère, l'un de ces éléments (découpage, graine, versions de librairies, prétraitement) a changé et le résultat n'est pas rejouable à l'identique.

## Mesure 3
- Métriques et paramètres lisibles : oui (5 métriques, 7 paramètres)
- Artefacts (model/modele.joblib) lisibles : non, l'onglet affiche « No Artifacts Recorded »
- Chemin indiqué : file:C:/Users/ISSA/Downloads/azure1/s6-kouyate/session/suivi/artefacts/fcad9f897124444eb86f9eae63e96b58/artifacts

## Q1.3
(a) Les métriques et paramètres sont des valeurs stockées dans la base, donc ils voyagent avec elle. Les artefacts sont des fichiers à part : la base n'en garde que l'adresse, en chemin absolu, qui pointait vers un dossier de session disparu.
(b) importer_suivi.py retrouve l'ancien chemin dans la base et le remplace par celui de suivi/artefacts du poste, dans les colonnes qui contiennent des adresses d'artefacts.
(c) Entre deux postes du groupe, le même problème se poserait : chaque machine a un chemin absolu différent (nom d'utilisateur, disque), donc il faudrait réécrire les adresses à chaque import.

## Mesure 4
| Run | PR-AUC | Précision au rappel cible | Durée |
|---|---|---|---|
| reference-g42 | 0.0501 | 0.0041 | 38 s |
| reference-g7 | 0.0654 | 0.0060 | 14 s |
| variante-g42 | 0.0834 | 0.0051 | 4 s |
| variante-g7 | 0.0469 | 0.0052 | 3 s |

## Mesure 5
| Grandeur | Valeur |
|---|---|
| Écart variante - référence, graine 42 | +0.0333 |
| Écart variante - référence, graine 7 | -0.0185 |
| Variation de la référence entre ses deux graines | 0.0153 |
| Variation de la variante entre ses deux graines | 0.0365 |

## Q1.4
L'écart entre approches (+0.033 à la graine 42, -0.019 à la graine 7) ne dépasse pas la plus grande variation d'une même approche (0.037) et change de signe : selon mon tableau de décisions, ce n'est pas un écart réel.
Je ne déclare donc pas de meilleure approche sur la PR-AUC et je tranche sur le coût : la variante s'entraîne en 3-4 s contre 14-38 s pour la référence, je promeus la variante.
(À compléter : ce que j'attendais, et si ce résultat le contredit.)

## Mesure 6
- Version promue : dermascan-tabulaire v2 (run variante-g42), validée par Issa Kouyaté
- Version de repli : v1 (run reference-g42)
- Maillons de verifier_chaine.py, tous OK :
  1. fichier servi = version promue (empreinte 4a5a25f662ce61de)
  2. artefact du run = fichier servi (4a5a25f662ce61de)
  3. manifeste du run = manifeste local (5f0d206076798960)
  4. données du manifeste = données locales (536e8208cfb3502b)
- Commit du code qui a produit les données : 842f613

## Q1.5
Le premier maillon casse : « fichier servi = version promue ». L'empreinte du fichier de la référence (27608e47...) ne correspond pas à celle enregistrée au registre pour la v2 (4a5a25f6...). Code de sortie : 1.
Le script s'arrête avec un code non nul dès qu'un maillon est rompu, donc un pipeline peut l'utiliser comme test automatique (exigence H2), sans relecture humaine. Je le lancerais juste avant la construction de l'image (le fichier copié dans l'image doit être celui de la version « production » du registre), puis dans la CI avant le push de l'image.

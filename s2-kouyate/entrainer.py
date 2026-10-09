# entrainer.py - Seance 2, partie 2
# Decoupage par patient, pipeline scikit-learn, evaluation, choix du seuil,
# serialisation du modele avec ses metadonnees.
# Lancement : python entrainer.py
# Produit : model/modele.joblib et charge.json

import json
import os
import platform
import time
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score,
                             precision_recall_curve, roc_auc_score)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# ------------------------------------------------------------- Decisions
RAPPEL_CIBLE = 0.90      # decide AVANT tout resultat (tableau de decisions)
VERSION = "1.0.0"        # impose par le contrat d'interface
GRAINE = 42              # fixe le hasard : deux lancements = meme decoupage
PART_TEST = 0.20         # 20 % des patients mis de cote pour l'evaluation

# Colonnes ecartees, d'apres EXPLORATION.md
FUITES = ["iddx_full", "iddx_1", "iddx_2", "iddx_3", "iddx_4", "iddx_5",
          "mel_thick_mm", "mel_mitotic_index", "lesion_id"]
IDENTIFIANTS = ["isic_id", "patient_id"]
CONSTANTES = ["image_type"]
ADMINISTRATIVES = ["attribution", "copyright_license"]


def titre(texte):
    print("\n" + "=" * 70)
    print(texte)
    print("=" * 70)


# ------------------------------------------------------------- Chargement
d = pd.read_csv("data/train-metadata.csv", low_memory=False)

y = d["target"].to_numpy()             # la reponse a deviner : 0 ou 1
groupes = d["patient_id"].to_numpy()   # a quel patient appartient chaque ligne
X = d.drop(columns=FUITES + IDENTIFIANTS + CONSTANTES + ADMINISTRATIVES + ["target"])

colonnes_numeriques = X.select_dtypes(include="number").columns.tolist()
colonnes_categorielles = [c for c in X.columns if c not in colonnes_numeriques]
# Les colonnes texte sont passees en type "object" : les cases vides y sont
# des NaN, ce que les etapes d'imputation savent reconnaitre.
X[colonnes_categorielles] = X[colonnes_categorielles].astype(object)

print("variables :", X.shape[1], "dont", len(colonnes_numeriques), "numeriques et",
      len(colonnes_categorielles), "categorielles")


# ------------------------------------------------------------- 2.1 Decoupage
titre("MESURE 6 - Decoupage par patient")

# GroupShuffleSplit tire au hasard des PATIENTS, pas des lignes : toutes les
# lesions d'un patient vont du meme cote.
decoupe = GroupShuffleSplit(n_splits=1, test_size=PART_TEST, random_state=GRAINE)
train, test = next(decoupe.split(X, y, groups=groupes))

# La preuve par comptage : aucun patient des deux cotes.
assert not (set(groupes[train]) & set(groupes[test])), "fuite de patients"
print("aucun patient en commun entre entrainement et test : verifie")

for nom, idx in [("entrainement", train), ("test", test)]:
    print(f"{nom:<13} lignes {len(idx):>7} | patients {len(set(groupes[idx])):>4} | "
          f"positifs {int(y[idx].sum()):>3} | taux de positifs {y[idx].mean():.4%}")


# ------------------------------------------------------------- 2.2 Pipeline
# Chaque etape apprend ses statistiques (mediane, moyenne, liste des
# categories) pendant fit(), donc sur l'entrainement seul.
pre = ColumnTransformer([
    # Colonnes numeriques : case vide -> mediane, puis mise a la meme echelle.
    ("num", Pipeline([("imputation", SimpleImputer(strategy="median")),
                      ("echelle", StandardScaler())]), colonnes_numeriques),
    # Colonnes texte : case vide -> valeur la plus frequente, puis une colonne
    # de 0/1 par categorie. "ignore" : une categorie jamais vue ne fait pas
    # planter, elle est codee par des 0 partout.
    ("cat", Pipeline([("imputation", SimpleImputer(strategy="most_frequent")),
                      ("encodage", OneHotEncoder(handle_unknown="ignore"))]),
     colonnes_categorielles),
])

# class_weight="balanced" : une erreur sur une maligne pese autant que
# ~1000 erreurs sur des benignes. Sans cela le modele ignorerait les malignes.
modele = Pipeline([("pre", pre),
                   ("clf", LogisticRegression(max_iter=1000, class_weight="balanced"))])


# ------------------------------------------------------------- 2.3 Entrainement
titre("MESURE 7 - Comparaison des deux modeles sur le test")

# Reference qui n'apprend rien : repond toujours la classe la plus frequente.
reference = DummyClassifier(strategy="most_frequent").fit(X.iloc[train], y[train])

debut = time.perf_counter()
modele.fit(X.iloc[train], y[train])
duree_entrainement = time.perf_counter() - debut

# predict_proba renvoie deux colonnes : [proba benin, proba malin].
# La colonne 1 est la probabilite d'etre maligne.
proba = modele.predict_proba(X.iloc[test])[:, 1]
proba_reference = reference.predict_proba(X.iloc[test])[:, 1]
y_test = y[test]

metriques = {}
for nom, m, p in [("DummyClassifier", reference, proba_reference),
                  ("Regression logistique", modele, proba)]:
    exactitude = accuracy_score(y_test, m.predict(X.iloc[test]))
    roc = roc_auc_score(y_test, p)
    pr = average_precision_score(y_test, p)
    print(f"{nom:<22} exactitude {exactitude:.4%} | ROC-AUC {roc:.4f} | PR-AUC {pr:.4f}")
    if m is modele:
        metriques = {"exactitude": float(exactitude), "roc_auc": float(roc),
                     "pr_auc": float(pr)}

hasard = y_test.mean()
print(f"valeur du hasard pour la PR-AUC (taux de positifs du test) : {hasard:.4f}")
print(f"duree de l'entrainement : {duree_entrainement:.1f} s")


# ------------------------------------------------------------- 2.4 Seuil
titre("MESURE 8 - Compromis rappel / precision")


def bilan(seuil):
    """Compte les 3 cas utiles quand on alerte au-dessus de `seuil`."""
    alerte = proba >= seuil
    vp = int((alerte & (y_test == 1)).sum())     # malignes trouvees
    fp = int((alerte & (y_test == 0)).sum())     # alertes pour rien
    fn = int((~alerte & (y_test == 1)).sum())    # malignes ratees
    rappel = vp / (vp + fn) if (vp + fn) else 0.0
    precision = vp / (vp + fp) if (vp + fp) else 0.0
    alertes_pour_1000 = 1000 * (vp + fp) / len(y_test)
    return rappel, precision, vp, fp, fn, alertes_pour_1000


print(f"{'seuil':>6} {'rappel':>8} {'precision':>10} {'VP':>4} {'FP':>7} {'FN':>4} "
      f"{'alertes/1000':>13}")
for s in [0.50, 0.80, 0.90, 0.99]:
    r, p, vp, fp, fn, a = bilan(s)
    print(f"{s:>6.2f} {r:>8.2%} {p:>10.4%} {vp:>4} {fp:>7} {fn:>4} {a:>13.1f}")

titre("MESURE 9 - Seuil retenu et son cout")

precision_c, rappel_c, seuils = precision_recall_curve(y_test, proba)
# Le long de la courbe, le seuil monte et le rappel descend. On prend le
# DERNIER point ou le rappel vaut encore au moins la cible : c'est le seuil
# le plus haut possible, donc le moins de fausses alertes, sans passer sous
# le rappel vise.
i = np.where(rappel_c >= RAPPEL_CIBLE)[0][-1]
seuil_retenu = float(seuils[min(i, len(seuils) - 1)])

r, p, vp, fp, fn, a = bilan(seuil_retenu)
print(f"rappel vise                  : {RAPPEL_CIBLE:.0%}")
print(f"seuil correspondant          : {seuil_retenu:.6f}")
print(f"rappel obtenu a ce seuil     : {r:.2%}")
print(f"precision a ce seuil         : {p:.4%}")
print("lesions examinees par maligne trouvee :", round(1 / precision_c[i]))
print(f"vrais positifs {vp} | faux positifs {fp} | faux negatifs restants {fn}")
print(f"alertes pour 1000 lesions    : {a:.1f}")


# ------------------------------------------------------------- 2.5 Serialisation
titre("MESURE 10 - Paquet produit")

metriques.update({"pr_auc_hasard": float(hasard), "rappel_au_seuil": float(r),
                  "precision_au_seuil": float(p), "faux_negatifs_test": fn,
                  "positifs_test": int(y_test.sum()), "lignes_test": int(len(y_test))})

# Le paquet contient tout ce qu'il faut pour servir le modele sans moi.
paquet = {
    "pipeline": modele,
    "version": VERSION,
    "colonnes_attendues": X.columns.tolist(),
    "colonnes_numeriques": colonnes_numeriques,
    "colonnes_categorielles": colonnes_categorielles,
    "seuil": seuil_retenu,
    "rappel_cible": RAPPEL_CIBLE,
    "metriques": metriques,
    "prevalence_entrainement": float(y[train].mean()),
    "entraine_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "versions": {"python": platform.python_version(), "scikit-learn": sklearn.__version__,
                 "pandas": pd.__version__, "numpy": np.__version__,
                 "joblib": joblib.__version__},
}
os.makedirs("model", exist_ok=True)
joblib.dump(paquet, "model/modele.joblib")

print(f"taille du fichier model/modele.joblib : {os.path.getsize('model/modele.joblib') / 1024:.1f} Ko")
print("colonnes attendues declarees :", len(paquet["colonnes_attendues"]))
print(f"duree de l'entrainement      : {duree_entrainement:.1f} s")
print("prevalence a l'entrainement  :", f"{paquet['prevalence_entrainement']:.4%}")
print("versions :", paquet["versions"])

# Une ligne reelle du jeu de test, pour tester l'API en partie 3 :
# la premiere lesion maligne du test. Les cases vides deviennent null.
ligne = X.iloc[[test[y_test == 1][0]]]
charge = json.loads(ligne.to_json(orient="records"))[0]
with open("charge.json", "w", encoding="utf-8") as f:
    json.dump(charge, f, indent=2)
print("charge.json ecrit : 1 lesion maligne du jeu de test,", len(charge), "champs")

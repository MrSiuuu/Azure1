# explorer.py - Seance 2, partie 1 : exploration du jeu ISIC 2024
# Ce script ne produit aucun modele. Il affiche les chiffres a recopier
# dans EXPLORATION.md (mesures 2 a 5).
# Lancement : python explorer.py

import pandas as pd

# low_memory=False : pandas lit tout le fichier avant de deviner le type de
# chaque colonne. Sinon il devine bloc par bloc et affiche des avertissements
# de "type mixte" sur les colonnes partiellement vides.
d = pd.read_csv("data/train-metadata.csv", low_memory=False)


def titre(texte):
    print("\n" + "=" * 70)
    print(texte)
    print("=" * 70)


# ---------------------------------------------------------------- Mesure 2
titre("MESURE 2 - Volumetrie et structure")

print("lignes, colonnes   :", d.shape)
print("patients distincts :", d["patient_id"].nunique())

# groupby("patient_id").size() : pour chaque patient, son nombre de lignes,
# donc son nombre de lesions.
tailles = d.groupby("patient_id").size()
print("lesions par patient (min / mediane / max) :",
      tailles.min(), "/", int(tailles.median()), "/", tailles.max())

print("\nType de chaque colonne :")
print(d.dtypes.to_string())


# ---------------------------------------------------------------- Mesure 3
titre("MESURE 3 - Colonnes qui trahissent la reponse (fuites)")

total_malignes = int(d["target"].sum())
print("total de lesions malignes dans le jeu :", total_malignes, "\n")

# Les 5 colonnes du tableau de l'enonce, puis les autres colonnes de
# diagnostic du fichier (l'annexe C parle de neuf colonnes de fuite).
SUSPECTES = ["iddx_full", "iddx_1", "mel_thick_mm", "mel_mitotic_index", "lesion_id",
             "iddx_2", "iddx_3", "iddx_4", "iddx_5"]
SUSPECTES = [c for c in SUSPECTES if c in d.columns]

for c in SUSPECTES:
    rempli = d[c].notna().sum()                         # cases non vides
    malignes = d.loc[d[c].notna(), "target"].sum()      # malignes parmi elles
    print(f"{c:<22} rempli {rempli:>7} dont malignes {int(malignes):>4}"
          f"  ({malignes / total_malignes:.0%} de toutes les malignes)")

# iddx_1 est remplie partout : ce n'est pas sa presence qui trahit, c'est
# sa valeur. Ce tableau croise sa valeur avec la cible.
print("\nValeurs de iddx_1 croisees avec la cible (0 = benin, 1 = malin) :")
print(pd.crosstab(d["iddx_1"].fillna("(vide)"), d["target"]).to_string())


# ---------------------------------------------------------------- Mesure 4
titre("MESURE 4 - Valeurs manquantes et colonnes constantes")

FUITES = SUSPECTES
IDENTIFIANTS = ["isic_id", "patient_id"]

na = d.isna().sum()
na = na[na > 0].sort_values(ascending=False)            # les plus vides d'abord
print("Colonnes avec au moins une valeur manquante, hors fuites :")
for c, n in na.items():
    if c not in FUITES:
        print(f"  {c:<30} {n:>7} manquantes  ({n / len(d):.2%})")

# Une colonne constante n'a qu'une seule valeur differente (ou aucune).
constantes = [c for c in d.columns if d[c].nunique(dropna=True) <= 1]
print("\nconstantes :", constantes)
for c in constantes:
    print(f"  {c} vaut toujours : {d[c].dropna().unique().tolist()}")

a_retirer = set(FUITES) | set(IDENTIFIANTS) | set(constantes) | {"target"}
restantes = [c for c in d.columns if c not in a_retirer]
print("\nvariables restantes apres retrait des fuites, identifiants,")
print("constantes et de la cible :", len(restantes))
print(restantes)

# Decision supplementaire : ces deux colonnes decrivent l'origine de l'image
# (hopital, licence), pas la lesion. Une cabine en pharmacie ne les enverra
# jamais. On les garde pour l'analyse (model card), pas pour le modele.
ADMINISTRATIVES = ["attribution", "copyright_license"]
retenues = [c for c in restantes if c not in ADMINISTRATIVES]
print("\nvariables retenues pour le modele, sans les colonnes administratives :",
      len(retenues))
print("lesions par institution (attribution) :")
print(d["attribution"].value_counts().to_string())


# ---------------------------------------------------------------- Mesure 5
titre("MESURE 5 - Distribution de la cible")

positifs = int((d["target"] == 1).sum())
negatifs = int((d["target"] == 0).sum())
print("lesions target = 1 (malignes) :", positifs)
print("lesions target = 0 (benignes) :", negatifs)
print(f"taux de positifs              : {positifs / len(d):.4%}")
print("une maligne pour N benignes   : N =", round(negatifs / positifs))

# Question 1.5 : un modele qui repond toujours "benin" a bon sur toutes
# les benignes et faux sur toutes les malignes.
print(f"exactitude du 'toujours benin' : {negatifs / len(d):.4%}")

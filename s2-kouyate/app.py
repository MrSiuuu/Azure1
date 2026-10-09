"""API d'inference DermaScan - seance 2.

Etend la sonde de sante de la seance 1 : meme lecture de la configuration
dans l'environnement, meme ecoute sur 0.0.0.0, plus un modele.

Endpoints : GET /health, GET /model/info, POST /predict
Variables d'environnement lues : PORT, MODEL_PATH, SEUIL
"""

import os
import socket
import time

import joblib
import numpy as np
import pandas as pd
from flask import Flask, jsonify, request

STARTED_AT = time.time()

SERVICE_NAME = os.environ.get("SERVICE_NAME", "dermascan-api")
PORT = int(os.environ.get("PORT", "8000"))
MODEL_PATH = os.environ.get("MODEL_PATH", "model/modele.joblib")

# Chargement au demarrage, PAS dans la fonction de vue : le fichier est lu
# une seule fois, puis le modele reste en memoire pour toutes les requetes.
# Un modele absent n'empeche pas le processus de demarrer : c'est /health
# qui signalera l'indisponibilite par un 503.
PAQUET = None
PIPELINE = None
ERREUR = None
try:
    PAQUET = joblib.load(MODEL_PATH)
    PIPELINE = PAQUET["pipeline"]
    # Le seuil du paquet est la valeur par defaut ; SEUIL permet de le
    # changer au lancement, sans reconstruire l'image.
    SEUIL = float(os.environ.get("SEUIL", PAQUET["seuil"]))
    COLONNES = PAQUET["colonnes_attendues"]
    NUMERIQUES = PAQUET["colonnes_numeriques"]
    CATEGORIELLES = PAQUET["colonnes_categorielles"]
except Exception as exc:
    PIPELINE = None
    ERREUR = f"{type(exc).__name__}: {exc}"

app = Flask(__name__)


def modele_indisponible():
    return jsonify({"error": "modele non charge", "detail": ERREUR}), 503


@app.get("/")
def accueil():
    return jsonify({"message": "DermaScan inference API", "service": SERVICE_NAME,
                    "endpoints": ["/health", "/model/info", "/predict"]})


@app.get("/health")
def health():
    # 200 si et seulement si le modele est charge. Un processus vivant qui
    # ne peut pas predire n'est pas en etat de servir : 503.
    charge = PIPELINE is not None
    corps = {"status": "ok" if charge else "unavailable",
             "model_loaded": charge,
             "service": SERVICE_NAME,
             "version": PAQUET["version"] if charge else None,
             "hostname": socket.gethostname(),
             "uptime_seconds": round(time.time() - STARTED_AT, 1)}
    if not charge:
        corps["error"] = ERREUR
    return jsonify(corps), 200 if charge else 503


@app.get("/model/info")
def model_info():
    if PIPELINE is None:
        return modele_indisponible()
    return jsonify({"version": PAQUET["version"],
                    "seuil": SEUIL,
                    "rappel_cible": PAQUET["rappel_cible"],
                    "metriques": PAQUET["metriques"],
                    "prevalence_entrainement": PAQUET["prevalence_entrainement"],
                    "entraine_le": PAQUET["entraine_le"],
                    "versions": PAQUET["versions"],
                    "nombre_colonnes_attendues": len(COLONNES),
                    "colonnes_attendues": COLONNES})


@app.post("/predict")
def predict():
    if PIPELINE is None:
        return modele_indisponible()

    # --- Validation AVANT prediction : une charge incorrecte donne un 400
    # qui nomme le probleme, jamais un 500.
    charge = request.get_json(silent=True)
    if not isinstance(charge, dict) or not charge:
        return jsonify({"error": "corps JSON vide ou invalide",
                        "attendu": "un objet JSON avec les colonnes de /model/info"}), 400

    manquantes = [c for c in COLONNES if c not in charge]
    if manquantes:
        return jsonify({"error": "variables manquantes",
                        "nombre_manquantes": len(manquantes),
                        "manquantes": manquantes[:10]}), 400

    # Une valeur null est acceptee (le pipeline sait boucher les trous),
    # mais pas un texte la ou un nombre est attendu, ni l'inverse.
    mal_typees = [c for c in NUMERIQUES
                  if charge[c] is not None
                  and (isinstance(charge[c], bool) or not isinstance(charge[c], (int, float)))]
    mal_typees += [c for c in CATEGORIELLES
                   if charge[c] is not None and not isinstance(charge[c], str)]
    if mal_typees:
        return jsonify({"error": "types invalides",
                        "nombre_invalides": len(mal_typees),
                        "invalides": mal_typees[:10]}), 400

    # --- Prediction : une ligne, avec exactement les colonnes de l'entrainement.
    ligne = pd.DataFrame([{c: charge[c] for c in COLONNES}], columns=COLONNES)
    ligne[NUMERIQUES] = ligne[NUMERIQUES].astype(float)          # null -> NaN
    cat = ligne[CATEGORIELLES].astype(object)
    ligne[CATEGORIELLES] = cat.where(cat.notna(), np.nan)        # null -> NaN

    proba = float(PIPELINE.predict_proba(ligne)[0, 1])

    return jsonify({
        "probabilite_maligne": round(proba, 6),
        "seuil": SEUIL,
        # Le service trie, il ne diagnostique pas : il ne dit jamais "benin".
        "decision": "a_examiner" if proba >= SEUIL else "non_prioritaire",
        "version_modele": PAQUET["version"],
        "rappel_cible": PAQUET["rappel_cible"],
    })


if __name__ == "__main__":
    # host="0.0.0.0" : indispensable en conteneur (seance 1, question 3.1).
    app.run(host="0.0.0.0", port=PORT)

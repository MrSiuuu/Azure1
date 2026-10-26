"""Scénario Locust - DermaScan séance 3.

Un utilisateur = un dermatologue derrière son poste de consultation.
"""
import copy
import json
import random
from pathlib import Path

from locust import HttpUser, between, task

# Chargé UNE fois au démarrage : on ne recopie pas 40 champs dans le code.
CHARGE_DE_BASE = json.loads(Path(__file__).with_name("charge.json").read_text(encoding="utf-8"))


def charge_utile_perturbee():
    """Une lésion différente à chaque appel, sans sortir des plages réelles.

    - age_approx : +/- 10 ans, multiple de 5, borné entre 20 et 85 (format ISIC)
    - clin_size_long_diam_mm et tbp_lv_areaMM2 : +/- 20 %
    """
    charge = copy.deepcopy(CHARGE_DE_BASE)
    age = charge["age_approx"] + random.choice([-10, -5, 0, 5, 10])
    charge["age_approx"] = float(min(85, max(20, age)))
    for col in ("clin_size_long_diam_mm", "tbp_lv_areaMM2"):
        charge[col] = round(charge[col] * random.uniform(0.8, 1.2), 4)
    return charge


class Dermatologue(HttpUser):
    # Temps de réflexion entre deux gestes : 1 à 5 secondes.
    wait_time = between(1, 5)

    @task(10)
    def predire(self):
        with self.client.post("/predict", json=charge_utile_perturbee(),
                              name="POST /predict", catch_response=True) as reponse:
            if reponse.status_code == 200:
                reponse.success()
            else:
                reponse.failure(f"statut {reponse.status_code}")

    @task(1)
    def sante(self):
        self.client.get("/health", name="GET /health")

    @task(1)
    def info_modele(self):
        self.client.get("/model/info", name="GET /model/info")
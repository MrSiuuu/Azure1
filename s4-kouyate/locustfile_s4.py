"""Scenario Locust - DermaScan seance 4.

Un utilisateur = un dermatologue derriere son poste de consultation.
Seule la tache de prediction change : elle envoie l'image de controle en multipart.
"""
import os
from pathlib import Path

from locust import HttpUser, between, task

# Lue UNE fois au chargement du module.
IMAGE = Path(os.environ["IMAGE_CONTROLE_S4"]).read_bytes()


class Dermatologue(HttpUser):
    # Meme temps de reflexion qu'en S3, pour comparer a usage egal.
    wait_time = between(1, 5)

    @task(10)
    def predire(self):
        with self.client.post(
            "/predict",
            files={"image": ("controle.jpg", IMAGE, "image/jpeg")},
            name="POST /predict",
            catch_response=True,
        ) as reponse:
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

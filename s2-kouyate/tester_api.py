# tester_api.py - Seance 2, partie 3.3 : mesures 11 et 12
# L'API doit tourner dans un autre terminal (python app.py).
# Lancement : python tester_api.py

import json
import statistics
import time

import requests

# 127.0.0.1 et non "localhost" : sous Windows, "localhost" est d'abord
# resolu en IPv6 (::1). L'API n'ecoute qu'en IPv4, donc chaque appel perd
# environ 2 secondes avant de basculer, ce qui fausse la mesure de latence.
URL = "http://127.0.0.1:8000"

with open("charge.json", encoding="utf-8") as f:
    charge = json.load(f)

print("=" * 70)
print("MESURE 11 - Reponses de l'API")
print("=" * 70)

r = requests.get(f"{URL}/health")
print("GET /health                      ->", r.status_code,
      "| model_loaded =", r.json().get("model_loaded"))

r = requests.get(f"{URL}/model/info")
print("GET /model/info                  ->", r.status_code,
      "| colonnes attendues =", r.json().get("nombre_colonnes_attendues"))

r = requests.post(f"{URL}/predict", json=charge)
print("POST /predict, charge valide     ->", r.status_code)
print(json.dumps(r.json(), indent=2))

# Charge incomplete : on retire 3 variables de la charge valide.
incomplete = dict(charge)
for c in list(incomplete)[:3]:
    del incomplete[c]
r = requests.post(f"{URL}/predict", json=incomplete)
print("POST /predict, charge incomplete ->", r.status_code,
      "| variables manquantes signalees =", r.json().get("nombre_manquantes"),
      r.json().get("manquantes"))

r = requests.post(f"{URL}/predict", data="", headers={"Content-Type": "application/json"})
print("POST /predict, corps vide        ->", r.status_code, "|", r.json().get("error"))

print()
print("=" * 70)
print("MESURE 12 - Latence de dix appels successifs sur charge valide")
print("=" * 70)

session = requests.Session()
durees = []
for _ in range(10):
    debut = time.perf_counter()
    session.post(f"{URL}/predict", json=charge)
    durees.append((time.perf_counter() - debut) * 1000)

print(f"minimum {min(durees):.1f} ms | mediane {statistics.median(durees):.1f} ms | "
      f"maximum {max(durees):.1f} ms")
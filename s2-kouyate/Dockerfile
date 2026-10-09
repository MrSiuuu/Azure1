# DermaScan - API d'inference - Seance 2
# Dockerfile de la seance 1, etendu. Ce qui change est marque [S2].

# 1 - Image de base. [S2] Python 3.14.0 au lieu de 3.12.7 : c'est la version
#     qui a entraine le modele. Un pipeline scikit-learn serialise se recharge
#     dans le meme environnement que celui qui l'a produit.
FROM python:3.14.0-slim-bookworm

# 2 - Repertoire de travail.
WORKDIR /app

# 3 - Reglages Python, inchanges. [S2] PORT et MODEL_PATH : valeurs par defaut
#     du contrat d'interface, surchargeables au lancement.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    MODEL_PATH=model/modele.joblib

# 4 - Les dependances d'abord : l'ordre de la seance 1 tient toujours.
COPY requirements.txt ./

# 5 - Installation. [S2] 5 dependances directes au lieu de 1 : c'est la couche
#     qu'il ne faut pas rejouer a chaque modification du code.
RUN pip install --no-cache-dir -r requirements.txt

# 6 - [S2] Le modele est un artefact, pas du code : il a sa propre ligne.
COPY model/modele.joblib ./model/

# 7 - Code applicatif, en dernier.
COPY app.py ./

# 8 - Utilisateur non privilegie, comme en seance 1.
RUN useradd --create-home --uid 10001 appuser \
 && chown -R appuser:appuser /app

# 9 - Le processus final ne s'execute pas en root.
USER appuser

# 10 - Documente le port d'ecoute.
EXPOSE 8000

# 11 - [S2] gunicorn remplace le serveur de developpement de Flask. Le port est
#      lu dans la variable PORT (defaut 8000). "exec" laisse le pid 1 a gunicorn.
CMD ["sh", "-c", "exec gunicorn -b 0.0.0.0:${PORT:-8000} app:app"]

# =============================================================================
# DermaScan — sonde de sante (health probe)
# Seance 1 · Industrialisation de l'IA dans le Cloud · Ynov Montpellier
#
# Ordre des instructions : de ce qui change le moins souvent vers ce qui change
# le plus souvent. Docker reutilise une couche tant que ni son instruction ni
# les fichiers qu'elle copie n'ont change ; des qu'une couche est invalidee,
# toutes celles qui la suivent sont rejouees. Le code applicatif arrive donc en
# dernier, et le durcissement (utilisateur non privilegie) apres l'installation,
# qui a besoin des droits.
# =============================================================================

# 1 · Image de base : variante slim (et non alpine, pour rester compatible avec
#     les wheels precompiles), version explicitement figee. latest est exclu :
#     il rendrait la construction non reproductible d'un jour a l'autre.
FROM python:3.12.7-slim-bookworm

# 2 · Repertoire de travail : chemin absolu, cree s'il n'existe pas. Toutes les
#     instructions suivantes lui sont relatives.
WORKDIR /app

# 3 · Reglages d'environnement Python.
#     PYTHONDONTWRITEBYTECODE : pas de .pyc dans une image jetable.
#     PYTHONUNBUFFERED        : sans lui, la sortie est tamponnee et
#                               `docker logs` reste muet au demarrage.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 4 · Le fichier qui change le moins souvent : la liste des dependances.
#     Copie SEUL, avant le code — c'est la decision centrale pour le cache.
COPY requirements.txt ./

# 5 · Installation des dependances. --no-cache-dir evite d'embarquer le cache
#     de pip dans la couche (quelques Mo inutiles dans l'image finale).
RUN pip install --no-cache-dir -r requirements.txt

# 6 · Code applicatif : change a chaque modification, donc copie le plus tard
#     possible. Une edition d'app.py n'invalide que cette couche et les
#     suivantes — jamais la couche pip.
COPY app.py ./

# 7 · Utilisateur non privilegie, uid explicite au-dela de 10000, et
#     appropriation du repertoire de travail.
RUN useradd --create-home --uid 10001 appuser \
 && chown -R appuser:appuser /app

# 8 · Bascule : le processus final ne s'executera pas en root.
USER appuser

# 9 · Documente le port d'ecoute. Purement declaratif : seul -p au lancement
#     publie reellement un port vers l'hote.
EXPOSE 8000

# 10 · Processus principal, en forme « exec » (tableau JSON). En forme
#      « shell », le processus serait lance sous un /bin/sh qui garderait le
#      pid 1 et n'attend pas correctement SIGTERM.
CMD ["python", "app.py"]
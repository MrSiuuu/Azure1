# DermaScan - API d'inference - Seance 4
# Base Wolfi (zero CVE) a la place de python-slim Debian (150 CVE).
FROM cgr.dev/chainguard/wolfi-base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    MODEL_PATH=model/modele.pt \
    PATH=/opt/venv/bin:$PATH

# Python 3.12 + dependances, puis retrait de pip dans le MEME RUN
RUN apk add --no-cache python-3.12 libstdc++
COPY requirements.txt ./
RUN python3.12 -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt \
 && /opt/venv/bin/pip uninstall -y pip

COPY model/modele.pt model/modele_meta.json ./model/
COPY app.py ./

RUN adduser -D -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["sh", "-c", "exec gunicorn -b 0.0.0.0:${PORT:-8000} app:app"]

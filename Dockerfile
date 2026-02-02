FROM python:3.12-slim

## Image QAIA CPU (production légère)
## - Python 3.12
## - Dépendances système audio minimales
## - Exécution via launcher.py

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    QAIA_ROOT=/app \
    QAIA_DATA_DIR=/app/data \
    QAIA_MODELS_DIR=/app/models \
    QAIA_LOGS_DIR=/app/logs \
    QAIA_CONFIG_DIR=/app/config

WORKDIR /app

# Dépendances système de base (audio + build minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    libasound2 \
    libasound2-dev \
    portaudio19-dev \
    alsa-utils \
    espeak-ng \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copie des fichiers de dépendances uniquement pour optimiser le cache
COPY requirements.txt ./requirements.txt

RUN python -m venv /opt/venv && \
    . /opt/venv/bin/activate && \
    pip install --upgrade pip && \
    pip install -r requirements.txt

ENV PATH="/opt/venv/bin:$PATH"

# Copie du code de l’application (sans gros artefacts, gérés via .dockerignore)
COPY . /app

# Création des répertoires de travail
RUN mkdir -p /app/data /app/logs /app/models

# Point d’entrée par défaut : launcher QAIA
CMD ["python", "launcher.py"]


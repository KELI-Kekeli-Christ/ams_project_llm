# Dockerfile Robot Hotel - Flask API + Pepper client
# Build: docker build -t robot-hotel .
# Run: voir docker-compose.yml

FROM python:3.10-slim

WORKDIR /app

# Dépendances système pour Whisper, OpenCV, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copier les requirements
COPY requirement.txt .

# Installer les dépendances Python (sans les extras CUDA si déploiement CPU)
RUN pip install --no-cache-dir -r requirement.txt \
    && pip install --no-cache-dir qi redis

# Copier l'application
COPY . .

# Variables d'environnement
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:/app/pepper_test

# Port Flask
EXPOSE 5000

# Point d'entrée par défaut: Flask
CMD ["python", "main.py"]

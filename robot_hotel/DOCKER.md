# Déploiement Docker - Robot Hotel

## Prérequis

- Docker et Docker Compose installés
- Robot Pepper sur le même réseau (pour le service Pepper)

## Démarrage rapide

### 1. Flask + Redis uniquement

```bash
cd robot_hotel
docker-compose up -d redis flask
```

- **Flask API** : http://localhost:5000
- **Redis** : localhost:6379

### 2. Avec le client Pepper

```bash
# Créer .env avec l'IP du robot
echo "PEPPER_IP=192.168.13.213" > .env

# Lancer tout (Flask, Redis, Pepper)
docker-compose --profile pepper up -d
```

Le service Pepper utilise `network_mode: host` pour atteindre le robot sur le LAN.

### 3. Build manuel

```bash
docker build -t robot-hotel .
docker run -p 5000:5000 -e REDIS_HOST=host.docker.internal robot-hotel
```

## Variables d'environnement

| Variable | Description | Défaut |
|----------|-------------|--------|
| `PEPPER_IP` | IP du robot Pepper | 192.168.13.213 |
| `PEPPER_PORT` | Port NAOqi | 9559 |
| `FLASK_API_URL` | URL de l'API Flask | http://localhost:5000 |
| `REDIS_HOST` | Hôte Redis | redis (ou localhost) |
| `REDIS_PORT` | Port Redis | 6379 |

## Structure

- **flask** : API REST (chat, transcription, réservation, etc.)
- **redis** : Mémoire conversationnelle du chatbot
- **pepper** : Client qui connecte au robot et pilote la conversation

## Tablette Pepper

L'URL affichée sur la tablette doit pointer vers la machine qui héberge Flask. Si Docker tourne sur une machine avec IP `10.126.9.22`, l'API sera à `http://10.126.9.22:5000`.

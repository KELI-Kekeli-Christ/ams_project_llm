# -*- coding: utf-8 -*-
"""
Configuration du robot Pepper et de l'API Flask
"""
import os

ROBOT_CONFIG = {
    "ip": os.environ.get("PEPPER_IP", "192.168.13.216"),
    "port": int(os.environ.get("PEPPER_PORT", "9559")),
    "language": os.environ.get("PEPPER_LANGUAGE", "French"),
}

API_CONFIG = {
    "base_url": os.environ.get("FLASK_API_URL", "http://localhost:5000"),
    "timeout": 60,
    "record_timeout": 120,
}

# Utiliser le micro de Pepper au lieu du PC quand disponible
USE_PEPPER_MIC = False

# Afficher le bouton « Appel » sur la tablette (appel vocal temps réel continu)
SHOW_TABLET_CALL_BUTTON = os.environ.get("SHOW_TABLET_CALL_BUTTON", "true").lower() in ("1", "true", "yes")

CHOREGRAPHE_PATH = "/opt/Softbank Robotics/Choregraphe Suite 2.5"

TEST_MESSAGE = "Bonjour, je suis connecté et prêt à vous aider. Ceci est un test de connexion."

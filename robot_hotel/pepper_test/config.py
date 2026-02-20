# -*- coding: utf-8 -*-
"""
Configuration du robot Pepper et de l'API Flask
"""
ROBOT_CONFIG = {
    "ip": "192.168.13.213",
    "port": 9559,
    "language": "French",
}

API_CONFIG = {
    "base_url": "http://localhost:5000",
    "timeout": 60,
    "record_timeout": 120,
}

# Utiliser le micro de Pepper au lieu du PC quand disponible
USE_PEPPER_MIC = True

CHOREGRAPHE_PATH = "/opt/Softbank Robotics/Choregraphe Suite 2.5"

TEST_MESSAGE = "Bonjour, je suis connecté et prêt à vous aider. Ceci est un test de connexion."

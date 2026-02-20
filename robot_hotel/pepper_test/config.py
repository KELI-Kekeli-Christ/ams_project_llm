#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Configuration for pepper_test module.
Contains robot and API configuration settings.
"""

# ============================================================================
# CONFIGURATION - Modifiez ces valeurs pour changer de robot
# ============================================================================
ROBOT_CONFIG = {
    "ip": "192.168.13.213",           # Adresse IP du robot (127.0.0.1 pour robot virtuel)
    "port": 9559,                # Port du robot (9559 par défaut, 40937 pour Choregraphe)
    "language": "French",         # Langue pour la synthèse vocale (French, English, etc.)
}

# Configuration de l'API Flask (pour enregistrement, transcription et chat)
API_CONFIG = {
    "base_url": "http://localhost:5000",  # URL de base de l'API Flask
    "timeout": 60,                        # Timeout pour les requêtes (secondes)
    "record_timeout": 120,                # Timeout spécifique pour l'enregistrement
}

# Message de test à faire dire au robot
TEST_MESSAGE = "Bonjour, je suis connecté et prêt à vous aider. Ceci est un test de connexion."

# Configuration Choregraphe (généralement pas besoin de modifier)
CHOREGRAPHE_PATH = "/opt/Softbank Robotics/Choregraphe Suite 2.5"


# -*- coding: utf-8 -*-
"""
Configuration centralisée pour le script Pepper
"""

# ============================================================================
# CONFIGURATION - Modifiez ces valeurs pour changer de robot
# ============================================================================
ROBOT_CONFIG = {
    "ip": "10.120.19.96",           # Adresse IP du robot (127.0.0.1 pour robot virtuel)
    "port": 9559,                # Port du robot (9559 par défaut, 40937 pour Choregraphe)
    "language": "French",         # Langue pour la synthèse vocale (French, English, etc.)
}

# Configuration de l'API Flask (pour enregistrement, transcription et chat)
API_CONFIG = {
    "base_url": "http://localhost:5000",  # URL de base de l'API Flask (pour les requêtes depuis Python)
    "timeout": 60,                        # Timeout pour les requêtes (secondes) - augmenté pour l'enregistrement
    "record_timeout": 120,                # Timeout spécifique pour l'enregistrement (plus long car il attend la fin de la parole)
}

# ============================================================================
# Configuration Choregraphe (généralement pas besoin de modifier)
# ============================================================================
CHOREGRAPHE_PATH = "/opt/Softbank Robotics/Choregraphe Suite 2.5"

# Message de test à faire dire au robot
TEST_MESSAGE = "Bonjour, je suis connecté et prêt à vous aider. Ceci est un test de connexion."
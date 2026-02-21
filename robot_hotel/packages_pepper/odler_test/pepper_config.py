#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Configuration centrale pour le robot Pepper.

Ce module regroupe les constantes de configuration (robot, API Flask,
Choregraphe, message de test) et prépare l'environnement Choregraphe.
"""

import os
import sys


# ============================================================================
# CONFIGURATION - Modifiez ces valeurs pour changer de robot
# ============================================================================
ROBOT_CONFIG = {
    "ip": "10.120.19.96",          # Adresse IP du robot (127.0.0.1 pour robot virtuel)
    "port": 9559,                   # Port du robot (9559 par défaut, 40937 pour Choregraphe)
    "language": "French",           # Langue pour la synthèse vocale (French, English, etc.)
}


# Configuration de l'API Flask (pour enregistrement, transcription et chat)
API_CONFIG = {
    "base_url": "http://localhost:5000",  # URL de base de l'API Flask (pour les requêtes depuis Python)
    "timeout": 60,                        # Timeout pour les requêtes (secondes) - augmenté pour l'enregistrement
    "record_timeout": 120,                # Timeout spécifique pour l'enregistrement (plus long car il attend la fin de la parole)
}


# Message de test à faire dire au robot
TEST_MESSAGE = (
    "Bonjour, je suis connecté et prêt à vous aider. "
    "Ceci est un test de connexion."
)


# ============================================================================
# Configuration Choregraphe
# ============================================================================
CHOREGRAPHE_PATH = "/opt/Softbank Robotics/Choregraphe Suite 2.5"


def setup_choreographe_environment():
    """Configure l'environnement pour utiliser Choregraphe."""
    choregraph_lib_path = os.path.join(CHOREGRAPHE_PATH, "lib")

    # Add Choregraphe lib directory to LD_LIBRARY_PATH
    if os.path.exists(choregraph_lib_path):
        current_ld_path = os.environ.get("LD_LIBRARY_PATH", "")
        if choregraph_lib_path not in current_ld_path:
            os.environ["LD_LIBRARY_PATH"] = "{}:{}".format(
                choregraph_lib_path,
                current_ld_path,
            ) if current_ld_path else choregraph_lib_path

    # Add Choregraphe Python path to sys.path so we can import qi
    choregraph_python_paths = [
        os.path.join(CHOREGRAPHE_PATH, "lib", "python2.7", "site-packages"),
        os.path.join(CHOREGRAPHE_PATH, "lib", "python", "site-packages"),
        os.path.join(CHOREGRAPHE_PATH, "pynaoqi"),
    ]

    for python_path in choregraph_python_paths:
        if os.path.exists(python_path) and python_path not in sys.path:
            sys.path.insert(0, python_path)


# Configurer l'environnement Choregraphe dès l'import du module
setup_choreographe_environment()


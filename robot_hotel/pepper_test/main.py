#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Point d'entrée principal pour la communication avec le robot Pepper.

L'application est décomposée en modules pour une maintenance évolutive :
- config.py        : Configuration robot et API
- choreographe.py  : Environnement Choregraphe (sys.path, LD_LIBRARY_PATH)
- robot_manager.py : Connexion et services NAOqi (TTS, tablette, vidéo)
- flask_utils.py   : Vérification et démarrage du serveur Flask
- api_client.py    : Client API (enregistrement, transcription, chat, réservation, QR)
- utils/           : Utilitaires (safe_print, encodage, réseau)
- ui/tablet_html.py: Génération HTML pour la tablette
- conversation.py  : Boucle de conversation interactive

Lancement : python main.py
(Depuis robot_hotel/pepper_test/)
"""
# IMPORTANT: choreographe doit être importé en premier pour configurer
# l'environnement (sys.path, LD_LIBRARY_PATH) avant l'import du module qi
import atexit
import choreographe  # noqa: F401

from api_client import release_micro
from conversation import run_conversation

# À la sortie du processus (Ctrl+C, fin normale, crash), libérer le micro
atexit.register(release_micro)

if __name__ == "__main__":
    run_conversation()

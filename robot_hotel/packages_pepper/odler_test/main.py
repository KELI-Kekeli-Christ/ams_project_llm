#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script principal pour communiquer avec le robot Pepper
Point d'entrée unique qui orchestre tous les modules
"""

import os
import sys
import time

# Import des modules personnalisés
from config import ROBOT_CONFIG, API_CONFIG
from robot_manager import RobotManager
from flask_integration import check_flask_server, start_flask_server_background
from tablet_interface import create_tablet_html
from conversation import run_conversation
from utils import safe_print


def main():
    """Fonction principale avec conversation interactive"""
    print("=" * 60)
    print("Robot Pepper - Mode Conversation Interactive")
    print("=" * 60)
    print("Configuration:")
    print("  IP: {}".format(ROBOT_CONFIG["ip"]))
    print("  Port: {}".format(ROBOT_CONFIG["port"]))
    print("  Langue: {}".format(ROBOT_CONFIG["language"]))
    print("=" * 60)
    
    # Vérifier que le serveur Flask est en cours d'exécution
    print("\nVerification du serveur Flask...")
    if not check_flask_server():
        print("Le serveur Flask n'est pas accessible sur {}".format(API_CONFIG["base_url"]))
        print("   Tentative de demarrage automatique...")
        
        if not start_flask_server_background():
            print("\n❌ Impossible de démarrer Flask automatiquement.")
            print("   Veuillez démarrer Flask manuellement avec:")
            print("   cd robot_hotel && python main.py")
            print("   ou utilisez le script: ./start_all.sh")
            print("\n   Le serveur Flask doit tourner indépendamment du robot.")
            return
    else:
        print("Serveur Flask accessible")
    
    # Créer le gestionnaire de robot
    robot = RobotManager(
        ip=ROBOT_CONFIG["ip"],
        port=ROBOT_CONFIG["port"]
    )
    
    # Connecter au robot
    if not robot.connect():
        print("\nÉchec de la connexion. Arrêt du programme.")
        return
    
    # Initialiser les services
    robot.initialize_services()
    
    # Attendre un peu après l'initialisation pour laisser les services se stabiliser
    print("Attente de stabilisation des services...")
    time.sleep(2.0)
    
    try:
        # Activer la tablette AVANT toute autre opération si elle est disponible
        # show_blank=True uniquement au premier démarrage pour initialiser
        if robot.tablet:
            print("Activation de la tablette au demarrage...")
            robot.wake_tablet(show_blank=True)
            time.sleep(0.5)  # Délai court après activation
        
        # Démarrer le flux vidéo continu pour la détection faciale
        recognized_name = None
        if robot.video and robot.camera_url:
            print("Demarrage du flux video continu pour la detection faciale...")
            if robot.start_continuous_video_stream():
                print("Reconnaissance faciale en cours depuis le flux video continu...")
                recognized_name = robot.recognize_face_from_stream(max_attempts=15, delay=0.3)
            else:
                print("Impossible de demarrer le flux video, utilisation de la capture unique...")
                recognized_name = robot.recognize_face_from_camera()
        elif robot.video:
            print("Reconnaissance faciale en cours (capture unique)...")
            recognized_name = robot.recognize_face_from_camera()
        
        # Message d'accueil personnalisé si une personne est reconnue
        if recognized_name:
            # Si reconnu, dire seulement "Ah bonjour [nom]"
            welcome_message = "Ah bonjour {} !".format(recognized_name)
            print("Personne reconnue: {}".format(recognized_name))
            if robot.tts:
                ok = robot.safe_say(welcome_message, language=ROBOT_CONFIG["language"])
                if not ok:
                    print("TTS failed to speak welcome message for {}".format(recognized_name))
        else:
            # Si non reconnu, ne rien dire
            print("👤 Aucune personne reconnue - pas de message d'accueil")
        
        # Afficher l'interface initiale avec bouton micro (recharge le site à chaque démarrage)
        if robot.tablet:
            # Charger directement le contenu sans réactiver (évite les pages blanches)
            print("🖥️ Chargement de l'interface sur la tablette...")
            
            greeting_text = "Ah bonjour {} !".format(recognized_name) if recognized_name else "Prêt à vous aider"
            html_content = create_tablet_html(
                title="Pepper",
                message=greeting_text,
                subtitle="",
                status="En attente",
                show_mic_button=True,
                mic_active=False,
                robot_ip=robot.ip
            )
            robot.display_text(html_content)
            time.sleep(1.0)  # Délai pour laisser le contenu se charger
            print("✅ Site chargé sur la tablette")
        else:
            print("💡 Astuce: La tablette n'est pas disponible sur le robot virtuel")
            print("   Les interactions se feront via la console")
        
        # Lancer la conversation interactive
        run_conversation(robot)
        
    except KeyboardInterrupt:
        print("\n\nConversation interrompue par l'utilisateur")
        if robot.tts:
            robot.safe_say("Au revoir !", language=ROBOT_CONFIG["language"])
        # Arrêter le flux vidéo si actif
        if robot.video_stream_active:
            print("Arret du flux video continu...")
            robot.stop_continuous_video_stream()
        # Ne plus cacher la vue web - la laisser affichée
    except Exception as e:
        print("\n❌ Erreur lors de l'exécution: {}".format(e))
        import traceback
        traceback.print_exc()
        if robot.tts:
            robot.safe_say("Je suis désolé, une erreur s'est produite.", language=ROBOT_CONFIG["language"])
        # Arrêter le flux vidéo si actif
        if robot.video_stream_active:
            print("Arret du flux video continu...")
            robot.stop_continuous_video_stream()
        # Ne plus cacher la vue web - la laisser affichée
    finally:
        # Arrêter le flux vidéo si toujours actif
        if robot.video_stream_active:
            print("Arret du flux video continu...")
            robot.stop_continuous_video_stream()
        # Déconnecter proprement (cela réinitialisera aussi la tablette)
        robot.disconnect()


if __name__ == "__main__":
    main()
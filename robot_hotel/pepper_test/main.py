#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script to communicate with Pepper robot
Entry point - imports from modular components
"""

# Import configuration
from config import ROBOT_CONFIG, API_CONFIG

# Import utilities
from utils.helpers import safe_print
from utils.language import map_language_code_to_ald_label

# Import API functions
from api.flask_check import check_flask_server, start_flask_server_background
from api.client import record_audio_manual, transcribe_audio, chat_with_api, make_reservation_with_api

# Import UI
from ui.tablet_html import create_tablet_html

# Import conversation
from conversation.flow import run_conversation

# Import robot manager
from pepper.robot_manager import RobotManager


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
    
    # Attendre un peu après l'initialisation
    print("Attente de stabilisation des services...")
    import time
    time.sleep(2.0)
    
    try:
        # Activer la tablette au démarrage
        if robot.tablet:
            print("Activation de la tablette au demarrage...")
            robot.wake_tablet(show_blank=True)
            time.sleep(0.5)
        
        # Démarrer le flux vidéo continu pour la détection faciale
        recognized_name = None
        if robot.video and robot.camera_url:
            print("Demarrage du flux video continu pour la detection faciale...")
            if robot.start_continuous_video_stream():
                print("Reconnaissance faciale en cours depuis le flux video continu...")
                recognized_name = robot.recognize_face_from_stream(max_attempts=5, delay=0.3)
            else:
                print("Impossible de demarrer le flux video, utilisation de la capture unique...")
                recognized_name = robot.recognize_face_from_camera()
        elif robot.video:
            print("Reconnaissance faciale en cours (capture unique)...")
            recognized_name = robot.recognize_face_from_camera()
        
        # Message d'accueil personnalisé
        if recognized_name:
            welcome_message = "Ah bonjour {} !".format(recognized_name)
            print("Personne reconnue: {}".format(recognized_name))
            if robot.tts:
                robot.say(welcome_message, language=ROBOT_CONFIG["language"])
        else:
            print("👤 Aucune personne reconnue - pas de message d'accueil")
        
        # Afficher l'interface initiale
        if robot.tablet:
            print("🖥️ Chargement de l'interface sur la tablette...")
            greeting_text = "Ah bonjour {} !".format(recognized_name) if recognized_name else "Prêt à vous aider"
            html_content = create_tablet_html(
                title="Pepper",
                message=greeting_text,
                subtitle="",
                status="En attente",
                show_mic_button=True,
                mic_active=False,
                robot_ip=robot.ip,
                show_qr_button=True
            )
            robot.display_text(html_content)
            time.sleep(1.0)
            print("✅ Site chargé sur la tablette")
        else:
            print("💡 Astuce: La tablette n'est pas disponible sur le robot virtuel")
            print("   Les interactions se feront via la console")
        
        # Lancer la conversation interactive
        run_conversation(robot)
        
    except KeyboardInterrupt:
        print("\n\nConversation interrompue par l'utilisateur")
        if robot.tts:
            robot.say("Au revoir !", language=ROBOT_CONFIG["language"])
        if robot.video_stream_active:
            print("Arret du flux video continu...")
            robot.stop_continuous_video_stream()
    except Exception as e:
        print("\n❌ Erreur lors de l'exécution: {}".format(e))
        import traceback
        traceback.print_exc()
        if robot.tts:
            robot.say("Je suis désolé, une erreur s'est produite.", language=ROBOT_CONFIG["language"])
        if robot.video_stream_active:
            print("Arret du flux video continu...")
            robot.stop_continuous_video_stream()
    finally:
        if robot.video_stream_active:
            print("Arret du flux video continu...")
            robot.stop_continuous_video_stream()
        robot.disconnect()


if __name__ == "__main__":
    main()


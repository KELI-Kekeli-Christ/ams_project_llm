#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script to communicate with Pepper robot
"""

import os
import sys
import time
import json
import requests





# ============================================================================
# CONFIGURATION - Modifiez ces valeurs pour changer de robot
# ============================================================================
ROBOT_CONFIG = {
    "ip": "127.0.0.1",           # Adresse IP du robot (127.0.0.1 pour robot virtuel)
    "port": 40937,                # Port du robot (9559 par défaut, 40937 pour Choregraphe)
    "language": "French",         # Langue pour la synthèse vocale (French, English, etc.)
}

# Configuration de l'API Flask (pour enregistrement, transcription et chat)
API_CONFIG = {
    "base_url": "http://localhost:5000",  # URL de base de l'API Flask
    "timeout": 60,                        # Timeout pour les requêtes (secondes) - augmenté pour l'enregistrement
    "record_timeout": 120,                # Timeout spécifique pour l'enregistrement (plus long car il attend la fin de la parole)
}

# Message de test à faire dire au robot
TEST_MESSAGE = "Bonjour, je suis connecté et prêt à vous aider. Ceci est un test de connexion."

# ============================================================================
# Configuration Choregraphe (généralement pas besoin de modifier)
# ============================================================================
CHOREGRAPHE_PATH = "/opt/Softbank Robotics/Choregraphe Suite 2.5"

# ============================================================================
# Initialisation de l'environnement Choregraphe
# ============================================================================
def setup_choreographe_environment():
    """Configure l'environnement pour utiliser Choregraphe"""
    choregraph_lib_path = os.path.join(CHOREGRAPHE_PATH, "lib")
    
    # Add Choregraphe lib directory to LD_LIBRARY_PATH
    if os.path.exists(choregraph_lib_path):
        current_ld_path = os.environ.get("LD_LIBRARY_PATH", "")
        if choregraph_lib_path not in current_ld_path:
            os.environ["LD_LIBRARY_PATH"] = "{}:{}".format(
                choregraph_lib_path, 
                current_ld_path
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

# Configuration de l'environnement
setup_choreographe_environment()

# Import qi module (NOT naoqi!)
try:
    import qi
except ImportError as e:
    print("ERROR: Cannot import 'qi' module")
    print("Make sure Choregraphe is installed at: {}".format(CHOREGRAPHE_PATH))
    print("Error: {}".format(e))
    sys.exit(1)


# ============================================================================
# Classe pour gérer la connexion au robot
# ============================================================================
class RobotManager:
    """Gère la connexion et les services du robot Pepper"""
    
    def __init__(self, ip, port):
        """
        Initialise le gestionnaire de robot
        
        Args:
            ip: Adresse IP du robot
            port: Port du robot
        """
        self.ip = ip
        self.port = port
        self.session = None
        self.tts = None
        self.tablet = None
        self.audio_recorder = None
        self.connection_string = "tcp://{}:{}".format(ip, port)
    
    def connect(self):
        """
        Connecte au robot
        
        Returns:
            bool: True si la connexion réussit, False sinon
        """
        try:
            print("Connexion au robot à {}:{}...".format(self.ip, self.port))
            self.session = qi.Session()
            self.session.connect(self.connection_string)
            print("Robot connecté avec succès!")
            return True
        except RuntimeError as e:
            print("Erreur de connexion au robot: {}".format(e))
            print("\nVérifiez que:")
            print("1. Le robot est allumé et connecté au réseau")
            print("2. L'adresse IP est correcte (actuellement: {}:{})".format(self.ip, self.port))
            print("3. Le robot écoute sur le bon port")
            return False
        except Exception as e:
            print("Erreur inattendue lors de la connexion: {}".format(e))
            return False
    
    def initialize_services(self):
        """Initialise les services du robot (TTS, Tablet, etc.)"""
        if not self.session:
            print("Erreur: Pas de session active. Connectez-vous d'abord au robot.")
            return False
        
        # Initialiser le service TextToSpeech
        try:
            self.tts = self.session.service("ALTextToSpeech")
            print("Service TextToSpeech initialisé")
        except Exception as e:
            print("Erreur avec le service TextToSpeech: {}".format(e))
            self.tts = None
        
        # Initialiser le service Tablet (peut ne pas être disponible sur robot virtuel)
        try:
            self.tablet = self.session.service("ALTabletService")
            print("Service Tablet initialisé")
        except Exception as e:
            print("Service Tablet non disponible (normal pour robot virtuel): {}".format(e))
            self.tablet = None
        
        # Initialiser le service AudioRecorder (pour enregistrer depuis le robot)
        try:
            self.audio_recorder = self.session.service("ALAudioRecorder")
            print("Service AudioRecorder initialisé")
        except Exception as e:
            print("Service AudioRecorder non disponible: {}".format(e))
            self.audio_recorder = None
        
        return True
    
    def say(self, text, language=None):
        """
        Fait parler le robot
        
        Args:
            text: Texte à dire
            language: Langue (optionnel, utilise la langue configurée si non spécifiée)
        """
        if not self.tts:
            print("Erreur: Service TextToSpeech non disponible")
            return False
        
        try:
            if language:
                self.tts.setLanguage(language)
            print("Le robot dit: '{}'".format(text))
            self.tts.say(text)
            return True
        except Exception as e:
            print("Erreur lors de la synthèse vocale: {}".format(e))
            return False
    
    def display_text(self, html_content):
        """
        Affiche du contenu HTML sur la tablette du robot
        
        Args:
            html_content: Contenu HTML à afficher
        """
        if not self.tablet:
            print("Service Tablet non disponible")
            return False
        
        try:
            self.tablet.showWebview(html_content)
            print("Texte affiché sur la tablette!")
            return True
        except Exception as e:
            print("Erreur lors de l'affichage sur la tablette: {}".format(e))
            return False
    
    def disconnect(self):
        """Déconnecte du robot"""
        if self.session:
            print("Déconnexion du robot...")
            self.session.close()
            print("Déconnecté")
            self.session = None
    
 


# ============================================================================
# Fonctions pour l'API Flask (enregistrement, transcription, chat)
# ============================================================================
def record_audio():
    """
    Démarre l'enregistrement audio via l'API Flask
    
    Returns:
        str: Chemin du fichier audio enregistré, ou None en cas d'erreur
    """
    try:
        print("Démarrage de l'enregistrement...")
        response = requests.get(
            "{}/record".format(API_CONFIG["base_url"]),
            timeout=API_CONFIG["record_timeout"]
        )
        response.raise_for_status()
        result = response.json()
        audio_file = result.get("file")
        print("Fichier audio enregistré: {}".format(audio_file))
        return audio_file
    except Exception as e:
        print("Erreur lors de l'enregistrement: {}".format(e))
        return None

def transcribe_audio(audio_file):
    """
    Transcrit le fichier audio via l'API Flask
    
    Args:
        audio_file: Chemin du fichier audio à transcrire (relatif ou absolu)
    
    Returns:
        str: Texte transcrit, ou None en cas d'erreur
    """
    try:
        print("Transcription de l'audio...")
        
        # Construire le chemin absolu si c'est un chemin relatif
        # Le fichier est créé dans le répertoire robot_hotel/recordings/
        if not os.path.isabs(audio_file):
            # Obtenir le répertoire du script actuel (pepper_test/)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # Remonter d'un niveau pour aller à robot_hotel/
            robot_hotel_dir = os.path.dirname(script_dir)
            # Construire le chemin absolu
            audio_file = os.path.join(robot_hotel_dir, audio_file)
        
        print("Ouverture du fichier: {}".format(audio_file))
        
        if not os.path.exists(audio_file):
            print("Erreur: Le fichier n'existe pas: {}".format(audio_file))
            return None
        
        with open(audio_file, "rb") as f:
            response = requests.post(
                "{}/transcribe".format(API_CONFIG["base_url"]),
                files={"file": f},
                timeout=API_CONFIG["timeout"]
            )
            response.raise_for_status()
            result = response.json()
            text = result.get("text")
            print("Texte transcrit: {}".format(text))
            return text
    except Exception as e:
        print("Erreur lors de la transcription: {}".format(e))
        return None

def chat_with_api(message):
    """
    Envoie un message au service de chat via l'API Flask
    
    Args:
        message: Message à envoyer
    
    Returns:
        str: Réponse du chat, ou None en cas d'erreur
    """
    try:
        print("Envoi du message au service de chat...")
        response = requests.post(
            "{}/chat".format(API_CONFIG["base_url"]),
            json={"message": message},
            timeout=API_CONFIG["timeout"]
        )
        response.raise_for_status()
        result = response.json()
        chat_response = result.get("response")
        print("Réponse reçue: {}".format(chat_response))
        return chat_response
    except Exception as e:
        print("Erreur lors de la communication avec le chat: {}".format(e))
        return None









# ============================================================================
# Fonctions utilitaires
# ============================================================================
def create_tablet_html(title, message, subtitle="", status=""):
    """
    Crée un contenu HTML pour la tablette
    
    Args:
        title: Titre principal
        message: Message principal
        subtitle: Sous-titre (optionnel)
        status: Statut/étape actuelle (optionnel)
    
    Returns:
        str: Contenu HTML
    """
    status_html = "<div style='background-color: rgba(255,255,255,0.2); padding: 10px; border-radius: 5px; margin-bottom: 20px;'>{}</div>".format(status) if status else ""
    
    html = """
    <html>
    <head>
        <meta charset="UTF-8">
    </head>
    <body style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; font-family: 'Arial', sans-serif; padding: 30px; text-align: center; min-height: 100vh; margin: 0;">
        <div style="background-color: rgba(255,255,255,0.1); border-radius: 15px; padding: 30px; box-shadow: 0 8px 32px rgba(0,0,0,0.1);">
            {}
            <h1 style="font-size: 42px; margin: 20px 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);">{}</h1>
            <div style="background-color: rgba(255,255,255,0.15); border-radius: 10px; padding: 20px; margin: 20px 0;">
                <p style="font-size: 28px; line-height: 1.6; margin: 0;">{}</p>
            </div>
            {}
        </div>
    </body>
    </html>
    """.format(
        status_html,
        title,
        message,
        "<div style='margin-top: 20px; padding: 15px; background-color: rgba(255,255,255,0.1); border-radius: 8px;'><p style='font-size: 20px; margin: 0;'><strong>Question:</strong> {}</p></div>".format(subtitle) if subtitle else ""
    )
    return html


# ============================================================================
# Fonction principale
# ============================================================================
def main():
    """Fonction principale"""
    print("=" * 60)
    print("Test de connexion au robot Pepper")
    print("=" * 60)
    print("Configuration:")
    print("  IP: {}".format(ROBOT_CONFIG["ip"]))
    print("  Port: {}".format(ROBOT_CONFIG["port"]))
    print("  Langue: {}".format(ROBOT_CONFIG["language"]))
    print("=" * 60)
    
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
    
    try:
        # Test de base: Faire parler le robot
        if robot.tts:
            robot.say("Je suis prêt. Dites quelque chose et je vais vous répondre.", 
                      language=ROBOT_CONFIG["language"])
        
        # Afficher du texte sur la tablette
        if robot.tablet:
            html_content = create_tablet_html(
                title="🤖 Robot Connecté!",
                message="Prêt à écouter",
                subtitle="Parlez et je répondrai",
                status="🟢 En attente..."
            )
            robot.display_text(html_content)
        else:
            print("💡 Astuce: La tablette n'est pas disponible sur le robot virtuel")
            print("   Les résultats seront affichés dans la console et le robot parlera la réponse")
        
        # ====================================================================
        # Workflow complet: Enregistrement -> Transcription -> Chat -> Réponse
        # ====================================================================
        
        # 1. Enregistrer l'audio
        print("\n" + "=" * 60)
        print("ÉTAPE 1: Enregistrement audio")
        print("=" * 60)
        if robot.tablet:
            html_content = create_tablet_html(
                title="🎤 Enregistrement...",
                message="Parlez maintenant",
                status="🟡 Enregistrement en cours..."
            )
            robot.display_text(html_content)
        
        audio_file = record_audio()
        if not audio_file:
            print("❌ Échec de l'enregistrement. Arrêt du workflow.")
            if robot.tablet:
                html_content = create_tablet_html(
                    title="❌ Erreur",
                    message="Échec de l'enregistrement",
                    status="🔴 Erreur"
                )
                robot.display_text(html_content)
            return
        
        # 2. Transcrire l'audio
        print("\n" + "=" * 60)
        print("ÉTAPE 2: Transcription audio")
        print("=" * 60)
        if robot.tablet:
            html_content = create_tablet_html(
                title="📝 Transcription...",
                message="Analyse de votre message",
                status="🟡 Transcription en cours..."
            )
            robot.display_text(html_content)
        
        transcribed_text = transcribe_audio(audio_file)
        if not transcribed_text:
            print("❌ Échec de la transcription. Arrêt du workflow.")
            if robot.tablet:
                html_content = create_tablet_html(
                    title="❌ Erreur",
                    message="Échec de la transcription",
                    status="🔴 Erreur"
                )
                robot.display_text(html_content)
            return
        
        print("✅ Texte transcrit: '{}'".format(transcribed_text))
        
        # Afficher la transcription sur la tablette
        if robot.tablet:
            html_content = create_tablet_html(
                title="✅ Transcription réussie",
                message=transcribed_text,
                subtitle="",
                status="🟢 Texte transcrit"
            )
            robot.display_text(html_content)
            time.sleep(2)  # Laisser le temps de voir la transcription
        
        # 3. Envoyer le message au service de chat
        print("\n" + "=" * 60)
        print("ÉTAPE 3: Traitement par le chatbot")
        print("=" * 60)
        if robot.tablet:
            html_content = create_tablet_html(
                title="🤔 Traitement...",
                message="Analyse de votre question",
                subtitle=transcribed_text,
                status="🟡 Génération de la réponse..."
            )
            robot.display_text(html_content)
        
        chat_response = chat_with_api(transcribed_text)
        if not chat_response:
            print("❌ Échec de la communication avec le chat. Arrêt du workflow.")
            if robot.tablet:
                html_content = create_tablet_html(
                    title="❌ Erreur",
                    message="Échec de la communication",
                    status="🔴 Erreur"
                )
                robot.display_text(html_content)
            return
        
        print("✅ Réponse générée: '{}'".format(chat_response))
        
        # 4. Faire dire la réponse au robot
        print("\n" + "=" * 60)
        print("ÉTAPE 4: Réponse vocale du robot")
        print("=" * 60)
        if robot.tts:
            robot.say(chat_response, language=ROBOT_CONFIG["language"])
        
        # 5. Afficher la réponse complète sur la tablette
        if robot.tablet:
            html_content = create_tablet_html(
                title="✅ Réponse",
                message=chat_response,
                subtitle=transcribed_text,
                status="🟢 Réponse générée"
            )
            robot.display_text(html_content)
        
        print("\n" + "=" * 60)
        print("✅ Workflow terminé avec succès!")
        print("=" * 60)
        print("📝 Question: {}".format(transcribed_text))
        print("💬 Réponse: {}".format(chat_response))
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\nInterrompu par l'utilisateur")
    except Exception as e:
        print("\nErreur lors de l'exécution: {}".format(e))
    finally:
        # Déconnecter proprement
        robot.disconnect()


if __name__ == "__main__":
    main()
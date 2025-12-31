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

# Import optionnel pour le scan QR code via caméra
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("⚠️ OpenCV (cv2) non disponible. Le scan QR code depuis la caméra ne fonctionnera pas.")





# ============================================================================
# CONFIGURATION - Modifiez ces valeurs pour changer de robot
# ============================================================================
ROBOT_CONFIG = {
    "ip": "127.0.0.1",           # Adresse IP du robot (127.0.0.1 pour robot virtuel)
    "port": 35693,                # Port du robot (9559 par défaut, 40937 pour Choregraphe)
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
        
        # Initialiser le service Video (pour accéder à la caméra du robot)
        try:
            self.video = self.session.service("ALVideoDevice")
            print("Service Video initialisé")
            # Construire l'URL de la caméra si possible
            # Note: L'URL exacte dépend de la configuration du robot
            self.camera_url = "http://{}:8080/video".format(self.ip)
            print("URL caméra configurée: {}".format(self.camera_url))
        except Exception as e:
            print("Service Video non disponible (normal pour robot virtuel): {}".format(e))
            self.video = None
            # Pour le robot virtuel ou si le service n'est pas disponible,
            # on peut utiliser l'URL par défaut si accessible
            self.camera_url = "http://{}:8080/video".format(self.ip)
        
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

def make_reservation_with_api(audio_file):
    """
    Crée une réservation depuis un fichier audio via l'API Flask
    
    Args:
        audio_file: Chemin du fichier audio contenant la demande de réservation
    
    Returns:
        dict: Résultat de la création de réservation ou None en cas d'erreur
    """
    try:
        print("Création de réservation depuis l'audio...")
        
        # Construire le chemin absolu si nécessaire
        if not os.path.isabs(audio_file):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            robot_hotel_dir = os.path.dirname(script_dir)
            audio_file = os.path.join(robot_hotel_dir, audio_file)
        
        if not os.path.exists(audio_file):
            print("Erreur: Le fichier n'existe pas: {}".format(audio_file))
            return None
        
        with open(audio_file, "rb") as f:
            response = requests.post(
                "{}/make_reservation".format(API_CONFIG["base_url"]),
                files={"file": f},
                timeout=API_CONFIG["timeout"]
            )
            response.raise_for_status()
            result = response.json()
            print("Résultat de la réservation: {}".format(result))
            return result
    except Exception as e:
        print("Erreur lors de la création de réservation: {}".format(e))
        return None

def is_reservation_request(text):
    """
    Détermine si le texte contient une demande de réservation
    
    Args:
        text: Texte à analyser
    
    Returns:
        bool: True si c'est une demande de réservation
    """
    if not text:
        return False
    
    text_lower = text.lower()
    reservation_keywords = [
        "réserver", "réservation", "chambre", "reserver", "reservation",
        "réserver une chambre", "je veux réserver", "je voudrais réserver",
        "book", "booking", "reserve"
    ]
    
    return any(keyword in text_lower for keyword in reservation_keywords)

def scan_qr_code_with_api(image_file_path=None, camera_url=None):
    """
    Scanne un QR code depuis une image ou via l'URL de la caméra du robot
    
    Args:
        image_file_path: Chemin vers une image (optionnel)
        camera_url: URL de la caméra du robot (optionnel)
    
    Returns:
        dict: Résultat du scan QR code ou None en cas d'erreur
    """
    try:
        url = "{}/scan_qr".format(API_CONFIG["base_url"])
        
        # Si une image est fournie, l'envoyer
        if image_file_path and os.path.exists(image_file_path):
            with open(image_file_path, "rb") as f:
                response = requests.post(
                    url,
                    files={"file": f},
                    timeout=API_CONFIG["timeout"]
                )
        elif camera_url:
            # Capturer depuis la caméra du robot
            if not CV2_AVAILABLE:
                print("❌ OpenCV non disponible pour capturer depuis la caméra")
                return None
            
            cap = cv2.VideoCapture(camera_url)
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                print("❌ Impossible de capturer une image depuis la caméra: {}".format(camera_url))
                return None
            
            # Sauvegarder temporairement l'image
            temp_file = "/tmp/pepper_qr_scan.png"
            cv2.imwrite(temp_file, frame)
            
            if not os.path.exists(temp_file):
                print("❌ Impossible de sauvegarder l'image capturée")
                return None
            
            with open(temp_file, "rb") as f:
                response = requests.post(
                    url,
                    files={"file": f},
                    timeout=API_CONFIG["timeout"]
                )
            
            # Nettoyer le fichier temporaire
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
        else:
            return None
        
        response.raise_for_status()
        result = response.json()
        
        if result.get("success"):
            print("✅ QR code scanné avec succès!")
            return result
        else:
            print("❌ Erreur lors du scan: {}".format(result.get("error", "Erreur inconnue")))
            return result
            
    except Exception as e:
        print("❌ Erreur lors du scan QR code: {}".format(e))
        return None

def is_qr_scan_request(text):
    """
    Détermine si le texte contient une demande de scan QR code
    
    Args:
        text: Texte à analyser
    
    Returns:
        bool: True si c'est une demande de scan QR code
    """
    if not text:
        return False
    
    text_lower = text.lower()
    qr_keywords = [
        "scanner", "scanne", "qr code", "code qr", "vérifier", "verifier",
        "vérifie", "verifie", "mon qr", "mon code", "ma réservation",
        "ma reservation", "check", "scan"
    ]
    
    return any(keyword in text_lower for keyword in qr_keywords)









# ============================================================================
# Fonctions utilitaires
# ============================================================================
def create_tablet_html(title, message, subtitle="", status="", show_mic_button=False, mic_active=False):
    """
    Crée un contenu HTML pour la tablette avec un bouton micro interactif
    
    Args:
        title: Titre principal
        message: Message principal
        subtitle: Sous-titre (optionnel)
        status: Statut/étape actuelle (optionnel)
        show_mic_button: Afficher le bouton micro (optionnel)
        mic_active: État du bouton micro (True = actif/enregistrement)
    
    Returns:
        str: Contenu HTML
    """
    status_html = "<div style='background-color: rgba(255,255,255,0.2); padding: 10px; border-radius: 5px; margin-bottom: 20px; font-size: 18px;'>{}</div>".format(status) if status else ""
    
    # Bouton micro avec animation
    mic_button_html = ""
    if show_mic_button:
        mic_color = "#ff4444" if mic_active else "#4CAF50"
        mic_size = "120px" if mic_active else "100px"
        mic_animation = "pulse 1.5s infinite" if mic_active else "none"
        
        mic_button_html = """
        <div style="margin-top: 30px;">
            <button id="micButton" onclick="startRecording()" style="
                background: radial-gradient(circle, {} 0%, {} 100%);
                border: none;
                border-radius: 50%;
                width: {};
                height: {};
                cursor: pointer;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                transition: all 0.3s ease;
                animation: {};
            " onmouseover="this.style.transform='scale(1.1)'" onmouseout="this.style.transform='scale(1)'">
                <span style="font-size: 60px;">🎤</span>
            </button>
            <p style="margin-top: 15px; font-size: 20px; opacity: 0.9;">
                {}
            </p>
        </div>
        <style>
            @keyframes pulse {{
                0% {{ transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 68, 68, 0.7); }}
                50% {{ transform: scale(1.1); box-shadow: 0 0 0 20px rgba(255, 68, 68, 0); }}
                100% {{ transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 68, 68, 0); }}
            }}
        </style>
        <script>
            function startRecording() {{
                var btn = document.getElementById('micButton');
                btn.style.background = 'radial-gradient(circle, #ff4444 0%, #cc0000 100%)';
                btn.innerHTML = '<span style="font-size: 60px;">🔴</span>';
                // Dans un vrai scénario, ceci déclencherait l'enregistrement via une API
                // Pour l'instant, on simule juste l'action
            }}
        </script>
        """.format(
            mic_color, 
            mic_color.replace("4", "8") if not mic_active else mic_color.replace("ff4444", "cc0000"),
            mic_size,
            mic_size,
            mic_animation,
            "🟢 Parlez maintenant" if mic_active else "Appuyez pour parler"
        )
    
    html = """
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; font-family: 'Arial', sans-serif; padding: 20px; text-align: center; min-height: 100vh; margin: 0; display: flex; flex-direction: column; justify-content: center;">
        <div style="background-color: rgba(255,255,255,0.1); border-radius: 15px; padding: 30px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); max-width: 100%;">
            {}
            <h1 style="font-size: 36px; margin: 15px 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);">{}</h1>
            <div style="background-color: rgba(255,255,255,0.15); border-radius: 10px; padding: 20px; margin: 20px 0;">
                <p style="font-size: 24px; line-height: 1.6; margin: 0;">{}</p>
            </div>
            {}
            {}
        </div>
    </body>
    </html>
    """.format(
        status_html,
        title,
        message,
        "<div style='margin-top: 20px; padding: 15px; background-color: rgba(255,255,255,0.1); border-radius: 8px;'><p style='font-size: 18px; margin: 0;'><strong>💬 Vous:</strong> {}</p></div>".format(subtitle) if subtitle else "",
        mic_button_html
    )
    return html


# ============================================================================
# Fonction principale - Conversation interactive
# ============================================================================
def main():
    """Fonction principale avec conversation interactive"""
    print("=" * 60)
    print("🤖 Robot Pepper - Mode Conversation Interactive")
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
        # Message d'accueil avec présentation des fonctionnalités
        welcome_message = "Bonjour ! Je suis Pepper, votre assistant hôtelier. Je peux vous aider à réserver une chambre, répondre à vos questions, ou vérifier votre réservation en scannant votre QR code. Appuyez sur le micro pour commencer à me parler."
        if robot.tts:
            robot.say(welcome_message, language=ROBOT_CONFIG["language"])
        
        # Afficher l'interface initiale avec bouton micro
        if robot.tablet:
            html_content = create_tablet_html(
                title="🤖 Pepper",
                message="Prêt à vous aider",
                subtitle="",
                status="🟢 En attente",
                show_mic_button=True,
                mic_active=False
            )
            robot.display_text(html_content)
        else:
            print("💡 Astuce: La tablette n'est pas disponible sur le robot virtuel")
            print("   Les interactions se feront via la console")
        
        # État de la conversation pour les réservations
        conversation_context = {
            "in_reservation_mode": False,
            "collected_info": {},
            "missing_fields": []
        }
        
        # ====================================================================
        # BOUCLE DE CONVERSATION
        # ====================================================================
        conversation_count = 0
        max_conversations = 50  # Limite de sécurité
        
        while conversation_count < max_conversations:
            conversation_count += 1
            print("\n" + "=" * 60)
            print("💬 Tour de conversation #{}".format(conversation_count))
            print("=" * 60)
            
            # Afficher le bouton micro en attente
            if robot.tablet:
                html_content = create_tablet_html(
                    title="🤖 Pepper",
                    message="Appuyez sur le micro pour parler",
                    subtitle="",
                    status="🟢 En attente",
                    show_mic_button=True,
                    mic_active=False
                )
                robot.display_text(html_content)
            
            # Demander à l'utilisateur de parler
            if robot.tts and conversation_count == 1:
                # Déjà dit au début
                pass
            elif not conversation_context["in_reservation_mode"]:
                if robot.tts:
                    robot.say("Comment puis-je vous aider ?", language=ROBOT_CONFIG["language"])
            
            # Attendre que l'utilisateur déclenche l'enregistrement (via micro de la tablette)
            # Dans un vrai scénario, ce serait déclenché par l'appui tactile sur le bouton micro
            print("\n⏳ Appuyez sur ENTRÉE ou sur le micro de la tablette pour commencer l'enregistrement...")
            print("   (En production, cela serait déclenché automatiquement par l'appui sur le bouton)")
            
            # Simuler l'attente de l'appui (en production, utiliserait les événements tactiles de Pepper)
            # Pour l'instant, on attend juste un court délai ou une entrée clavier
            try:
                import select
                import sys
                if select.select([sys.stdin], [], [], 2)[0]:
                    input()  # Attendre une entrée si disponible
            except:
                time.sleep(2)  # Sinon attendre 2 secondes
            
            # 1. Enregistrer l'audio
            if robot.tablet:
                html_content = create_tablet_html(
                    title="🎤 Enregistrement...",
                    message="Je vous écoute",
                    status="🟡 Enregistrement en cours...",
                    show_mic_button=True,
                    mic_active=True
                )
                robot.display_text(html_content)
            
            print("📹 Démarrage de l'enregistrement...")
            audio_file = record_audio()
            
            if not audio_file:
                error_msg = "Je n'ai pas réussi à enregistrer votre message. Pouvez-vous réessayer ?"
                print("❌ Échec de l'enregistrement")
                if robot.tts:
                    robot.say(error_msg, language=ROBOT_CONFIG["language"])
                if robot.tablet:
                    html_content = create_tablet_html(
                        title="❌ Erreur",
                        message="Échec de l'enregistrement",
                        status="🔴 Veuillez réessayer",
                        show_mic_button=True,
                        mic_active=False
                    )
                    robot.display_text(html_content)
                continue
            
            # 2. Transcrire l'audio
            if robot.tablet:
                html_content = create_tablet_html(
                    title="📝 Transcription...",
                    message="Je comprends votre message",
                    status="🟡 Analyse en cours...",
                    show_mic_button=False
                )
                robot.display_text(html_content)
            
            print("📝 Transcription de l'audio...")
            transcribed_text = transcribe_audio(audio_file)
            
            # Vérifier si la transcription a réussi
            if not transcribed_text or len(transcribed_text.strip()) < 3:
                error_msg = "Je n'ai pas bien compris ce que vous avez dit. Pouvez-vous répéter, s'il vous plaît ?"
                print("❌ Transcription vide ou trop courte")
                if robot.tts:
                    robot.say(error_msg, language=ROBOT_CONFIG["language"])
                if robot.tablet:
                    html_content = create_tablet_html(
                        title="❓",
                        message="Je n'ai pas compris",
                        subtitle="Veuillez répéter",
                        status="🟡 Transcription échouée",
                        show_mic_button=True,
                        mic_active=False
                    )
                    robot.display_text(html_content)
                continue
            
            print("✅ Texte transcrit: '{}'".format(transcribed_text))
            
            # Afficher la transcription sur la tablette
            if robot.tablet:
                html_content = create_tablet_html(
                    title="✅ Compris",
                    message="J'ai bien entendu",
                    subtitle=transcribed_text,
                    status="🟢 Transcription réussie",
                    show_mic_button=False
                )
                robot.display_text(html_content)
            
            time.sleep(1)
            
            # 3. Détecter si c'est une demande de réservation
            if is_reservation_request(transcribed_text) or conversation_context["in_reservation_mode"]:
                # Mode réservation
                print("📅 Détection d'une demande de réservation")
                conversation_context["in_reservation_mode"] = True
                
                if robot.tablet:
                    html_content = create_tablet_html(
                        title="📅 Réservation",
                        message="Traitement de votre demande",
                        subtitle=transcribed_text,
                        status="🟡 Création en cours...",
                        show_mic_button=False
                    )
                    robot.display_text(html_content)
                
                # Créer la réservation
                reservation_result = make_reservation_with_api(audio_file)
                
                if reservation_result and reservation_result.get("status") == "success":
                    # Réservation créée avec succès
                    # Extraire l'ID de réservation depuis la réponse
                    reservation_info = reservation_result.get("reservation", {})
                    reservation_id = reservation_info.get("id_reservation") or reservation_info.get("id_res") or reservation_info.get("reservation_id") or "N/A"
                    success_msg = "Parfait ! Votre réservation a été créée avec succès. Votre numéro de réservation est {}. Merci et à bientôt !".format(reservation_id)
                    
                    if robot.tts:
                        robot.say(success_msg, language=ROBOT_CONFIG["language"])
                    
                    if robot.tablet:
                        html_content = create_tablet_html(
                            title="✅ Réservation créée !",
                            message="Numéro: {}".format(reservation_id),
                            subtitle=transcribed_text,
                            status="🟢 Succès",
                            show_mic_button=True,
                            mic_active=False
                        )
                        robot.display_text(html_content)
                    
                    # Réinitialiser le contexte
                    conversation_context["in_reservation_mode"] = False
                    conversation_context["collected_info"] = {}
                    
                    print("✅ Réservation créée avec succès: {}".format(reservation_id))
                    time.sleep(3)
                    
                else:
                    # Vérifier si des informations manquent (analyse de l'erreur ou des données)
                    reservation_data = reservation_result.get("reservation_data", {}) if reservation_result else {}
                    error_msg = reservation_result.get("error", "").lower() if reservation_result else ""
                    
                    # Vérifier ce qui manque dans les données extraites
                    nom = reservation_data.get("nom", "").strip() if reservation_data else ""
                    prenom = reservation_data.get("prenom", "").strip() if reservation_data else ""
                    
                    # Utiliser les infos collectées précédemment si disponibles
                    if not nom or nom.lower() in ["inconnu", ""]:
                        nom = conversation_context["collected_info"].get("nom", "")
                    if not prenom or prenom.lower() in ["inconnu", ""]:
                        prenom = conversation_context["collected_info"].get("prenom", "")
                    
                    # Déterminer ce qui manque
                    missing_nom = not nom or nom.lower() in ["inconnu", ""]
                    missing_prenom = not prenom or prenom.lower() in ["inconnu", ""]
                    
                    if missing_nom or missing_prenom or "nom" in error_msg or "prenom" in error_msg:
                        # Informations manquantes (nom/prénom) - continuer la conversation
                        if missing_nom and not conversation_context["collected_info"].get("nom"):
                            missing_msg = "Pour créer votre réservation, j'ai besoin de connaître votre nom. Quel est votre nom de famille, s'il vous plaît ?"
                            conversation_context["missing_fields"] = ["nom"]
                        elif missing_prenom and not conversation_context["collected_info"].get("prenom"):
                            missing_msg = "Merci. Et quel est votre prénom, s'il vous plaît ?"
                            conversation_context["missing_fields"] = ["prenom"]
                            # Sauvegarder le nom si on vient de le collecter
                            if nom and nom.lower() not in ["inconnu", ""]:
                                conversation_context["collected_info"]["nom"] = nom
                        else:
                            missing_msg = "Il me manque quelques informations pour finaliser votre réservation. Pouvez-vous me donner votre nom complet, s'il vous plaît ?"
                            conversation_context["missing_fields"] = ["nom", "prenom"]
                        
                        if robot.tts:
                            robot.say(missing_msg, language=ROBOT_CONFIG["language"])
                        
                        if robot.tablet:
                            html_content = create_tablet_html(
                                title="❓ Information manquante",
                                message=missing_msg,
                                subtitle=transcribed_text,
                                status="🟡 En attente d'informations",
                                show_mic_button=True,
                                mic_active=False
                            )
                            robot.display_text(html_content)
                        
                        # Stocker les nouvelles informations collectées
                        if nom and nom.lower() not in ["inconnu", ""]:
                            conversation_context["collected_info"]["nom"] = nom
                        if prenom and prenom.lower() not in ["inconnu", ""]:
                            conversation_context["collected_info"]["prenom"] = prenom
                        
                        print("⚠️ Information manquante. Message: {}".format(missing_msg))
                        print("   Informations collectées: {}".format(conversation_context["collected_info"]))
                        continue
                    else:
                        # Autre erreur
                        error_msg_full = reservation_result.get("error", "Erreur inconnue lors de la création de la réservation") if reservation_result else "Erreur inconnue"
                        error_display = "Je suis désolé, il y a eu un problème lors de la création de votre réservation. Pouvez-vous réessayer en donnant plus de détails, notamment votre nom, prénom, le type de chambre et les dates ?"
                        
                        if robot.tts:
                            robot.say(error_display, language=ROBOT_CONFIG["language"])
                        
                        if robot.tablet:
                            html_content = create_tablet_html(
                                title="❌ Erreur",
                                message="Problème lors de la création",
                                subtitle=error_msg_full[:150] if len(error_msg_full) > 0 else "Erreur inconnue",
                                status="🔴 Erreur",
                                show_mic_button=True,
                                mic_active=False
                            )
                            robot.display_text(html_content)
                        
                        print("❌ Erreur lors de la création de réservation: {}".format(error_msg_full))
                        # Réinitialiser le contexte pour permettre une nouvelle tentative
                        conversation_context["in_reservation_mode"] = False
                        conversation_context["collected_info"] = {}
                        continue
                
            elif is_qr_scan_request(transcribed_text):
                # Mode scan QR code
                print("📷 Détection d'une demande de scan QR code")
                
                if robot.tablet:
                    html_content = create_tablet_html(
                        title="📷 Scan QR Code",
                        message="Préparez votre QR code",
                        subtitle=transcribed_text,
                        status="🟡 Scan en cours...",
                        show_mic_button=False
                    )
                    robot.display_text(html_content)
                
                # Demander au client de présenter le QR code
                if robot.tts:
                    robot.say("Présentez votre QR code devant ma caméra, s'il vous plaît.", language=ROBOT_CONFIG["language"])
                
                time.sleep(2)  # Donner le temps au client de positionner le QR code
                
                # Scanner le QR code
                print("📷 Scan du QR code en cours...")
                qr_result = scan_qr_code_with_api(camera_url=robot.camera_url)
                
                if qr_result and qr_result.get("success"):
                    # QR code valide scanné
                    reservation = qr_result.get("reservation", {})
                    client = qr_result.get("client", {})
                    qr_id = qr_result.get("qr_id", "N/A")
                    
                    # Construire le message de confirmation
                    client_name = "{} {}".format(client.get("prenom", ""), client.get("nom", "")).strip()
                    if not client_name:
                        client_name = "Client"
                    
                    confirmation_msg = "Parfait ! J'ai vérifié votre QR code. Bonjour {}, votre réservation {} est confirmée. Type de chambre: {}, arrivée le {}, départ le {}. Au plaisir de vous accueillir !".format(
                        client_name,
                        qr_id,
                        reservation.get("type_chambre", "N/A"),
                        reservation.get("date_arrivee", "N/A"),
                        reservation.get("date_depart", "N/A")
                    )
                    
                    if robot.tts:
                        robot.say(confirmation_msg, language=ROBOT_CONFIG["language"])
                    
                    if robot.tablet:
                        html_content = create_tablet_html(
                            title="✅ QR Code Validé",
                            message="Réservation confirmée",
                            subtitle="ID: {}".format(qr_id),
                            status="🟢 Validé",
                            show_mic_button=True,
                            mic_active=False
                        )
                        robot.display_text(html_content)
                    
                    print("✅ QR code validé avec succès!")
                    print("   Client: {}".format(client_name))
                    print("   Réservation: {}".format(qr_id))
                    time.sleep(3)
                else:
                    # Erreur lors du scan
                    error_msg = "Je suis désolé, je n'ai pas pu scanner votre QR code. Pouvez-vous le repositionner devant ma caméra, s'il vous plaît ?"
                    
                    if robot.tts:
                        robot.say(error_msg, language=ROBOT_CONFIG["language"])
                    
                    if robot.tablet:
                        error_detail = qr_result.get("error", "QR code non détecté") if qr_result else "QR code non détecté"
                        html_content = create_tablet_html(
                            title="❌ Erreur",
                            message="QR code non détecté",
                            subtitle=error_detail[:100],
                            status="🔴 Erreur",
                            show_mic_button=True,
                            mic_active=False
                        )
                        robot.display_text(html_content)
                    
                    print("❌ Échec du scan QR code")
                    time.sleep(2)
            
            else:
                # Mode conversation normale (questions/réponses)
                print("💬 Mode conversation normale")
                conversation_context["in_reservation_mode"] = False
                
                if robot.tablet:
                    html_content = create_tablet_html(
                        title="🤔 Traitement...",
                        message="Je réfléchis à votre question",
                        subtitle=transcribed_text,
                        status="🟡 Génération de la réponse...",
                        show_mic_button=False
                    )
                    robot.display_text(html_content)
                
                # Obtenir la réponse du chatbot
                chat_response = chat_with_api(transcribed_text)
                
                if not chat_response:
                    error_msg = "Je suis désolé, je n'ai pas pu traiter votre demande. Pouvez-vous répéter, s'il vous plaît ?"
                    print("❌ Échec de la communication avec le chat")
                    if robot.tts:
                        robot.say(error_msg, language=ROBOT_CONFIG["language"])
                    if robot.tablet:
                        html_content = create_tablet_html(
                            title="❌ Erreur",
                            message="Je n'ai pas pu répondre",
                            subtitle=transcribed_text,
                            status="🔴 Erreur",
                            show_mic_button=True,
                            mic_active=False
                        )
                        robot.display_text(html_content)
                    continue
                
                print("✅ Réponse générée: '{}'".format(chat_response))
                
                # Faire dire la réponse au robot
                if robot.tts:
                    robot.say(chat_response, language=ROBOT_CONFIG["language"])
                
                # Afficher la réponse sur la tablette
                if robot.tablet:
                    html_content = create_tablet_html(
                        title="✅ Réponse",
                        message=chat_response,
                        subtitle=transcribed_text,
                        status="🟢 Réponse générée",
                        show_mic_button=True,
                        mic_active=False
                    )
                    robot.display_text(html_content)
            
            # Pause avant la prochaine interaction
            time.sleep(2)
        
        # Fin de la boucle
        farewell_msg = "Merci d'avoir utilisé mes services. Au revoir !"
        if robot.tts:
            robot.say(farewell_msg, language=ROBOT_CONFIG["language"])
        
        if robot.tablet:
            html_content = create_tablet_html(
                title="👋 Au revoir",
                message="Merci pour votre visite",
                status="🟢 Conversation terminée",
                show_mic_button=False
            )
            robot.display_text(html_content)
        
        print("\n" + "=" * 60)
        print("✅ Conversation terminée")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Conversation interrompue par l'utilisateur")
        if robot.tts:
            robot.say("Au revoir !", language=ROBOT_CONFIG["language"])
    except Exception as e:
        print("\n❌ Erreur lors de l'exécution: {}".format(e))
        import traceback
        traceback.print_exc()
        if robot.tts:
            robot.say("Je suis désolé, une erreur s'est produite.", language=ROBOT_CONFIG["language"])
    finally:
        # Déconnecter proprement
        robot.disconnect()


if __name__ == "__main__":
    main()
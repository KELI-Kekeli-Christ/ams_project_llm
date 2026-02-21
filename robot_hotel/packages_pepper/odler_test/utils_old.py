#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utility functions for Pepper robot communication
"""

import os
import sys
import time
import json
import requests
import unicodedata

# HTML escape helper with compatibility fallback (Python2/3)
try:
    import html as _html_mod
    def escape_html(s):
        if s is None:
            return ''
        if isinstance(s, bytes):
            s = s.decode('utf-8', errors='ignore')
        return _html_mod.escape(s)
except Exception:
    try:
        import cgi as _cgi
        def escape_html(s):
            if s is None:
                return ''
            if isinstance(s, bytes):
                s = s.decode('utf-8', errors='ignore')
            return _cgi.escape(s, quote=True)
    except Exception:
        def escape_html(s):
            if s is None:
                return ''
            if isinstance(s, bytes):
                s = s.decode('utf-8', errors='ignore')
            s = str(s)
            return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#x27;')

# Import optionnel pour le scan QR code via caméra
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

# ============================================================================
# CONFIGURATION - Modifiez ces valeurs pour changer de robot
# ============================================================================
ROBOT_CONFIG = {
    "ip": "192.168.13.66",           # Adresse IP du robot (127.0.0.1 pour robot virtuel)
    "port": 9559,                # Port du robot (9559 par défaut, 40937 pour Choregraphe)
    "language": "French",         # Langue pour la synthèse vocale (French, English, etc.)
}

# Configuration de l'API Flask (pour enregistrement, transcription et chat)
API_CONFIG = {
    "base_url": "http://localhost:5000",  # URL de base de l'API Flask (pour les requêtes depuis Python)
    "timeout": 60,                        # Timeout pour les requêtes (secondes) - augmenté pour l'enregistrement
    "record_timeout": 120,                # Timeout spécifique pour l'enregistrement (plus long car il attend la fin de la parole)
}

TEST_MESSAGE = "Bonjour, je suis connecté et prêt à vous aider. Ceci est un test de connexion."

# ============================================================================
# Configuration Choregraphe (généralement pas besoin de modifier)
# ============================================================================
CHOREGRAPHE_PATH = "/opt/Softbank Robotics/Choregraphe Suite 2.5"

def safe_print(msg, *args):
    """Print safely to stdout handling environments with ASCII-only encodings.

    Compatible with Python 2 and 3. Avoids using `print(..., **kwargs)` which
    can be a syntax error under Python 2 where `print` is a statement.
    """
    import sys
    try:
        text = msg.format(*args) if args else msg
    except Exception:
        try:
            text = str(msg)
        except Exception:
            text = repr(msg)

    try:
        # Prefer writing str to stdout (Python 3)
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
    except UnicodeEncodeError:
        try:
            # Try writing bytes to buffer if available (Python 3)
            if hasattr(sys.stdout, "buffer"):
                sys.stdout.buffer.write(text.encode("utf-8", errors="replace") + b"\n")
                sys.stdout.buffer.flush()
            else:
                # Python 2 fallback: encode to utf-8 then write
                sys.stdout.write(text.encode("utf-8", errors="replace") + "\n")
                sys.stdout.flush()
        except Exception:
            try:
                sys.stdout.write(repr(text) + "\n")
                sys.stdout.flush()
            except Exception:
                pass


def transliterate_to_ascii(text):
    """Return an ASCII-only approximation of `text` by removing diacritics."""
    try:
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='ignore')
        nkfd = unicodedata.normalize('NFKD', text)
        return nkfd.encode('ascii', 'ignore').decode('ascii')
    except Exception:
        try:
            return str(text)
        except Exception:
            return repr(text)


def safe_say(robot, text, language=None):
    """Call robot.say safely: ensure utf-8 str and fallback to ASCII transliteration.

    Returns True on success, False on failure.
    """
    try:
        if isinstance(text, bytes):
            try:
                text = text.decode('utf-8')
            except Exception:
                text = text.decode('utf-8', errors='ignore')
        else:
            text = str(text)

        try:
            if language is not None:
                res = robot.say(text, language=language)
            else:
                res = robot.say(text)
            # If robot.say returns a value, consider it; otherwise assume success
            safe_print("safe_say: called robot.say (tts exists={})", bool(getattr(robot, 'tts', None)))
            return True
        except UnicodeEncodeError:
            # fallback to ASCII-only
            safe_text = transliterate_to_ascii(text)
            try:
                if language is not None:
                    robot.say(safe_text, language=language)
                else:
                    robot.say(safe_text)
                safe_print("safe_say: used ASCII fallback")
                return True
            except Exception:
                # Last resort: ignore or log
                safe_print("safe_say: failed to call robot.say after fallback")
                return False
        except Exception as e:
            safe_print("safe_say: robot.say raised {}", repr(e))
            return False
    except Exception as e:
        safe_print("safe_say: error preparing text: {}", repr(e))
        return False


def check_flask_server():
    """
    Vérifie si le serveur Flask est en cours d'exécution
    
    Returns:
        bool: True si Flask est accessible, False sinon
    """
    import socket
    
    # Méthode 1: Vérifier si le port est ouvert (plus rapide et fiable)
    try:
        host = API_CONFIG["base_url"].replace("http://", "").replace("https://", "").split(":")[0]
        port = int(API_CONFIG["base_url"].split(":")[-1].split("/")[0]) if ":" in API_CONFIG["base_url"] else 5000
        
        # Créer un socket et essayer de se connecter
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)  # Timeout très court
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            # Le port est ouvert, Flask est probablement en cours d'exécution
            # Maintenant vérifier avec une requête HTTP rapide
            try:
                response = requests.get(
                    "{}/".format(API_CONFIG["base_url"]),
                    timeout=1  # Timeout très court
                )
                if response.status_code == 200:
                    print("Flask detecte et accessible")
                    return True
            except:
                # Même si la requête HTTP échoue, le port est ouvert donc Flask tourne probablement
                print("Port Flask ouvert (port {}), serveur probablement en cours d'execution".format(port))
                return True
        else:
            return False
    except socket.timeout:
        return False
    except Exception as e:
        # Si la vérification de port échoue, essayer avec une requête HTTP simple
        pass
    
    # Méthode 2: Fallback avec requête HTTP (si la vérification de port échoue)
    try:
        response = requests.get(
            "{}/".format(API_CONFIG["base_url"]),
            timeout=1  # Timeout très court pour éviter le blocage
        )
        if response.status_code == 200:
            print("Flask detecte via requete HTTP")
            return True
    except requests.exceptions.ConnectionError:
        # Connexion refusée = Flask n'est pas démarré
        return False
    except requests.exceptions.Timeout:
        # Timeout = Flask ne répond pas assez vite
        return False
    except Exception:
        # Autre erreur
        return False
    
    return False

def start_flask_server_background():
    """
    Démarre le serveur Flask en arrière-plan dans un processus séparé
    
    Returns:
        bool: True si le démarrage a réussi, False sinon
    """
    import subprocess
    import os
    import sys
    
    try:
        # Obtenir le chemin du répertoire robot_hotel
        script_dir = os.path.dirname(os.path.abspath(__file__))
        robot_hotel_dir = os.path.dirname(script_dir)
        flask_main = os.path.join(robot_hotel_dir, "main.py")
        
        if not os.path.exists(flask_main):
            print("Fichier Flask non trouve: {}".format(flask_main))
            return False
        
        print("🚀 Démarrage du serveur Flask en arrière-plan...")
        
        # Préparer les arguments pour le démarrage
        if sys.platform == "win32":
            # Windows: utiliser CREATE_NEW_PROCESS_GROUP
            process = subprocess.Popen(
                [sys.executable, flask_main],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=robot_hotel_dir,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            )
        else:
            # Linux/Unix: utiliser nohup et setsid pour isoler le processus
            process = subprocess.Popen(
                ["nohup", sys.executable, flask_main],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=robot_hotel_dir,
                preexec_fn=os.setsid  # Créer un nouveau groupe de processus pour isoler Flask
            )
        
        # Attendre un peu pour que Flask démarre
        print("Attente du demarrage de Flask...")
        for i in range(10):  # Attendre jusqu'à 10 secondes
            time.sleep(1)
            if check_flask_server():
                print("Serveur Flask demarre avec succes (PID: {})".format(process.pid))
                print("   Le serveur continuera de tourner même après l'arrêt du robot.")
                return True
        
        print("Flask semble avoir demarre mais n'est pas encore accessible")
        return False
    except Exception as e:
        print("Erreur lors du demarrage de Flask: {}".format(e))
        import traceback
        traceback.print_exc()
        return False


def post_file_with_retries(url, files, attempts=3, timeout=None):
    """
    Post a file with simple retry logic on timeout/connection errors.
    Returns the `requests.Response` or `None` if all attempts fail.
    """
    import time
    if timeout is None:
        timeout = API_CONFIG.get("timeout", 60)

    for i in range(attempts):
        try:
            return requests.post(url, files=files, timeout=timeout)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if i < attempts - 1:
                backoff = 1 + i * 2
                time.sleep(backoff)
                continue
            return None
        except Exception as e:
            print("❌ Erreur lors du post du fichier: {}".format(e))
            return None

def get_local_ip_for_robot(robot_ip):
    """
    Obtient l'IP locale de la machine pour que le robot puisse y accéder
    
    Args:
        robot_ip: IP du robot pour déterminer l'interface réseau à utiliser
    
    Returns:
        str: IP locale de la machine
    """
    try:
        import socket
        # Se connecter au robot pour déterminer l'interface réseau locale
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((robot_ip, 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        # Fallback: essayer de trouver l'IP locale
        try:
            import socket
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            # Vérifier si c'est une IP valide (pas 127.0.0.1)
            if local_ip != "127.0.0.1":
                return local_ip
        except:
            pass
        return "127.0.0.1"  # Dernier recours

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

# ============================================================================
# Fonctions pour l'API Flask (enregistrement, transcription, chat)
# ============================================================================
def record_audio():
    """
    Démarre l'enregistrement audio via l'API Flask (détection automatique de silence)
    
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

def record_audio_manual():
    """
    Démarre l'enregistrement audio manuel via l'API Flask
    L'enregistrement démarre immédiatement et doit être arrêté via le bouton micro sur la tablette
    
    Returns:
        str: Chemin du fichier audio enregistré, ou None en cas d'erreur
    """
    try:
        print("Démarrage de l'enregistrement manuel...")
        
        # Vérifier s'il y a un enregistrement en cours et l'arrêter si nécessaire
        try:
            status_response = requests.get(
                "{}/record/status".format(API_CONFIG["base_url"]),
                timeout=2
            )
            if status_response.ok:
                status = status_response.json()
                if status.get("recording", False):
                    print("⚠️ Un enregistrement est déjà en cours, arrêt...")
                    requests.post("{}/record/stop".format(API_CONFIG["base_url"]), timeout=5)
                    time.sleep(0.5)  # Attendre un peu avant de redémarrer
        except:
            pass  # Ignorer les erreurs de vérification
        
        # Démarrer l'enregistrement
        response_start = requests.post(
            "{}/record/start".format(API_CONFIG["base_url"]),
            timeout=10
        )
        
        if response_start.status_code == 400:
            # Si erreur 400, essayer d'arrêter puis redémarrer
            print("⚠️ Erreur 400, tentative de réinitialisation...")
            try:
                requests.post("{}/record/stop".format(API_CONFIG["base_url"]), timeout=5)
                time.sleep(0.5)
                response_start = requests.post(
                    "{}/record/start".format(API_CONFIG["base_url"]),
                    timeout=10
                )
            except:
                pass
        
        response_start.raise_for_status()
        print("Enregistrement démarré. Cliquez sur le micro pour arrêter...")
        
        # Attendre que l'utilisateur clique sur le bouton micro pour arrêter
        # On vérifie périodiquement l'état de l'enregistrement
        max_wait_time = 300  # Maximum 5 minutes
        check_interval = 0.5  # Vérifier toutes les 0.5 secondes
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            time.sleep(check_interval)
            elapsed_time += check_interval
            
            # Vérifier l'état de l'enregistrement
            try:
                status_response = requests.get(
                    "{}/record/status".format(API_CONFIG["base_url"]),
                    timeout=2
                )
                if status_response.ok:
                    status = status_response.json()
                    if not status.get("recording", True):
                        # L'enregistrement a été arrêté
                        audio_file = status.get("file")
                        if audio_file:
                            print("Fichier audio enregistré: {}".format(audio_file))
                            return audio_file
                        break
            except:
                # En cas d'erreur, continuer à attendre
                pass
        
        # Si on arrive ici, l'enregistrement n'a pas été arrêté normalement
        # Essayer de l'arrêter manuellement
        print("Arrêt automatique de l'enregistrement...")
        response_stop = requests.post(
            "{}/record/stop".format(API_CONFIG["base_url"]),
            timeout=10
        )
        if response_stop.ok:
            result = response_stop.json()
            audio_file = result.get("file")
            if audio_file:
                print("Fichier audio enregistré: {}".format(audio_file))
                return audio_file
        
        return None
    except Exception as e:
        print("Erreur lors de l'enregistrement manuel: {}".format(e))
        # Essayer d'arrêter l'enregistrement en cas d'erreur
        try:
            requests.post("{}/record/stop".format(API_CONFIG["base_url"]), timeout=5)
        except:
            pass
        return None

def record_audio_with_vad(silence_threshold=2.0, volume_threshold=-40.0):
    """
    Démarre l'enregistrement audio avec Voice Activity Detection (VAD)
    L'enregistrement s'arrête automatiquement si le volume reste bas pendant 'silence_threshold' secondes

    Args:
        silence_threshold: Durée en secondes de silence pour arrêter l'enregistrement (défaut: 2.0s)
        volume_threshold: Seuil de volume en dB pour considérer qu'il y a du silence (défaut: -40.0 dB)

    Returns:
        str: Chemin du fichier audio enregistré, ou None en cas d'erreur
    """
    try:
        print("🎤 Démarrage de l'enregistrement avec VAD...")
        print("   Seuil de silence: {}s, Seuil de volume: {} dB".format(silence_threshold, volume_threshold))

        # Vérifier s'il y a un enregistrement en cours et l'arrêter si nécessaire
        try:
            status_response = requests.get(
                "{}/record/status".format(API_CONFIG["base_url"]),
                timeout=2
            )
            if status_response.ok:
                status = status_response.json()
                if status.get("recording", False):
                    print("⚠️ Un enregistrement est déjà en cours, arrêt...")
                    requests.post("{}/record/stop".format(API_CONFIG["base_url"]), timeout=5)
                    time.sleep(0.5)
        except:
            pass

        # Démarrer l'enregistrement
        response_start = requests.post(
            "{}/record/start".format(API_CONFIG["base_url"]),
            timeout=10
        )

        if response_start.status_code == 400:
            print("⚠️ Erreur 400, tentative de réinitialisation...")
            try:
                requests.post("{}/record/stop".format(API_CONFIG["base_url"]), timeout=5)
                time.sleep(0.5)
                response_start = requests.post(
                    "{}/record/start".format(API_CONFIG["base_url"]),
                    timeout=10
                )
            except:
                pass

        response_start.raise_for_status()
        print("✅ Enregistrement démarré avec VAD activé")

        # Variables pour le VAD
        silence_duration = 0.0
        check_interval = 0.1  # Vérifier toutes les 100ms
        max_record_time = 300  # Maximum 5 minutes
        elapsed_time = 0.0

        # Pour calculer la moyenne glissante du volume
        volume_history = []
        history_size = 10  # Garder 10 mesures pour la moyenne

        while elapsed_time < max_record_time:
            time.sleep(check_interval)
            elapsed_time += check_interval

            try:
                # Récupérer le statut de l'enregistrement (qui peut inclure des infos de volume)
                status_response = requests.get(
                    "{}/record/status".format(API_CONFIG["base_url"]),
                    timeout=1
                )

                if status_response.ok:
                    status = status_response.json()

                    # Vérifier si l'enregistrement a été arrêté manuellement
                    if not status.get("recording", True):
                        audio_file = status.get("file")
                        if audio_file:
                            print("🎤 Enregistrement arrêté manuellement")
                            print("📁 Fichier audio enregistré: {}".format(audio_file))
                            return audio_file
                        break

                    # RÉCUPÉRATION DU VOLUME AUDIO
                    # En production, l'API devrait retourner: "volume_db": -25.3
                    current_volume = status.get("volume_db")

                    # SIMULATION DU VOLUME (à remplacer par la vraie mesure en production)
                    if current_volume is None:
                        # Simulation réaliste: parole pendant ~4s puis silence
                        import random
                        base_volume = -15.0 if elapsed_time < 4.0 else -45.0  # Parole → Silence
                        current_volume = base_volume + random.uniform(-5.0, 5.0)  # + bruit réaliste

                    # Ajouter à l'historique des volumes
                    volume_history.append(float(current_volume))
                    if len(volume_history) > history_size:
                        volume_history.pop(0)

                    # Calculer la moyenne glissante
                    avg_volume = sum(volume_history) / len(volume_history) if volume_history else 0

                    # Déboguer le volume (toutes les secondes)
                    if int(elapsed_time) != int(elapsed_time - check_interval):
                        print("🔊 Volume actuel: {:.1f} dB (moyenne: {:.1f} dB)".format(current_volume, avg_volume))

                    # Vérifier si le volume est considéré comme du silence
                    if avg_volume < volume_threshold:
                        silence_duration += check_interval
                        if silence_duration >= silence_threshold:
                            print("🔇 Silence détecté pendant {:.1f}s - Arrêt automatique".format(silence_duration))
                            break
                    else:
                        # Reset du compteur de silence si on détecte de l'audio
                        if silence_duration > 0:
                            print("🎤 Audio détecté - Reset du compteur de silence")
                        silence_duration = 0.0

            except Exception as e:
                # En cas d'erreur de connexion temporaire, continuer
                print("⚠️ Erreur temporaire lors de la vérification du volume: {}".format(e))
                continue

        # Arrêter l'enregistrement
        print("🛑 Arrêt de l'enregistrement...")
        response_stop = requests.post(
            "{}/record/stop".format(API_CONFIG["base_url"]),
            timeout=10
        )

        if response_stop.ok:
            result = response_stop.json()
            audio_file = result.get("file")
            if audio_file:
                duration = elapsed_time
                print("✅ Enregistrement terminé avec VAD")
                print("📁 Fichier: {}".format(audio_file))
                print("⏱️ Durée: {:.1f}s".format(duration))
                return audio_file

        print("❌ Échec de l'arrêt de l'enregistrement")
        return None

    except Exception as e:
        print("❌ Erreur lors de l'enregistrement avec VAD: {}".format(e))
        # Essayer d'arrêter l'enregistrement en cas d'erreur
        try:
            requests.post("{}/record/stop".format(API_CONFIG["base_url"]), timeout=5)
        except:
            pass
        return None

def transcribe_audio(audio_file):
    """
    Transcrit le fichier audio via l'API Flask
    
    Args:
        audio_file: Chemin du fichier audio à transcrire (relatif ou absolu)
    
    Returns:
        tuple: (texte transcrit, langue détectée) ou (None, None) en cas d'erreur
    """
    try:
        safe_print("Transcription de l'audio...")
        
        # Construire le chemin absolu si c'est un chemin relatif
        # Le fichier est créé dans le répertoire robot_hotel/recordings/
        if not os.path.isabs(audio_file):
            # Obtenir le répertoire du script actuel (pepper_test/)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # Remonter d'un niveau pour aller à robot_hotel/
            robot_hotel_dir = os.path.dirname(script_dir)
            # Construire le chemin absolu
            audio_file = os.path.join(robot_hotel_dir, audio_file)
        
        safe_print("Ouverture du fichier: {}", audio_file)
        
        if not os.path.exists(audio_file):
            print("Erreur: Le fichier n'existe pas: {}".format(audio_file))
            return None, None
        
        # Vérifier la taille du fichier
        file_size = os.path.getsize(audio_file)
        print("📊 Taille du fichier: {} bytes".format(file_size))
        
        if file_size < 1000:  # Moins de 1KB - probablement trop petit
            print("⚠️ Fichier audio trop petit ({}) - probablement aucun son enregistré".format(file_size))
            return None, None
        
        with open(audio_file, "rb") as f:
            response = requests.post(
                "{}/transcribe".format(API_CONFIG["base_url"]),
                files={"file": f},
                timeout=API_CONFIG["timeout"]
            )
            response.raise_for_status()
            # Ensure response is treated as UTF-8
            try:
                response.encoding = 'utf-8'
            except Exception:
                pass

            # Try to parse JSON safely
            try:
                result = response.json()
            except Exception:
                # Fallback: try to load from text
                try:
                    result = json.loads(response.text)
                except Exception as e:
                    safe_print("Erreur parsing JSON transcription response: {}", repr(e))
                    return None, None

            text = result.get("text")
            language = result.get("language") or None

            # Normalize to Python3 str (unicode) or decode bytes
            try:
                if isinstance(text, bytes):
                    text = text.decode('utf-8', errors='ignore')
                elif not isinstance(text, str):
                    text = str(text)
            except Exception:
                try:
                    text = str(text)
                except Exception:
                    text = ""

            # Nettoyer le texte
            if text:
                text = text.strip()
                
            if not text:
                print("⚠️ Texte transcrit vide")
            else:
                print("✅ Texte transcrit: '{}' ({} caractères)".format(text, len(text)))
                
            safe_print("Langue détectée: {}", language)
            return text, language
            
    except requests.exceptions.Timeout:
        print("❌ Timeout lors de la transcription")
        return None, None
    except requests.exceptions.ConnectionError:
        print("❌ Erreur de connexion au serveur de transcription")
        return None, None
    except Exception as e:
        print("❌ Erreur lors de la transcription: {}".format(e))
        import traceback
        traceback.print_exc()
        return None, None

def chat_with_api(message, language=None):
    """
    Envoie un message au service de chat via l'API Flask
    
    Args:
        message: Message à envoyer
    
    Returns:
        str: Réponse du chat, ou None en cas d'erreur
    """
    try:
        print("Envoi du message au service de chat...")

        # System prompt to instruct the model to reply in the same language
        system_prompt = (
            "You are a helpful assistant. Always reply in the same language as the user's message. "
            "Detect the user's language from their input and respond using that language. "
            "If the language cannot be confidently detected, reply in the language of the message. "
            "Keep responses concise and user-friendly."
        )

        # Ensure message is a unicode string
        if isinstance(message, bytes):
            try:
                message = message.decode('utf-8')
            except Exception:
                message = message.decode('utf-8', errors='ignore')

        # Build JSON payload encoded as UTF-8 to avoid ASCII encoding issues (Python2/3 safe)
        try:
            # Include a system prompt so the model knows to mirror the user's language
            data_obj = {"system": system_prompt, "message": message}
            if language:
                # pass detected language to backend as a hint (ISO code)
                data_obj["language"] = language
            payload = json.dumps(data_obj, ensure_ascii=False).encode('utf-8')
        except TypeError:
            # Fallback if message contains non-serializable parts
            data_obj = {"message": str(message)}
            if language:
                data_obj["language"] = language
            payload = json.dumps(data_obj, ensure_ascii=False).encode('utf-8')

        headers = {"Content-Type": "application/json; charset=utf-8"}

        response = requests.post(
            "{}/chat".format(API_CONFIG["base_url"]),
            data=payload,
            headers=headers,
            timeout=API_CONFIG["timeout"]
        )
        response.raise_for_status()
        result = response.json()
        chat_response = result.get("response")
        try:
            print("Réponse reçue: {}".format(chat_response))
        except Exception:
            # Safe print for environments with narrow encodings
            try:
                print(repr(chat_response))
            except Exception:
                pass
        return chat_response
    except Exception as e:
        try:
            print("Erreur lors de la communication avec le chat: {}".format(repr(e)))
        except Exception:
            print("Erreur lors de la communication avec le chat (non affichable)")
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

    # Assurer que `text` est une chaîne unicode (str). Si bytes, décoder en utf-8.
    if isinstance(text, bytes):
        try:
            text = text.decode("utf-8")
        except Exception:
            text = text.decode("utf-8", errors="ignore")

    text_lower = str(text).lower()
    # Strict trigger: only start reservation when the explicit word 'reservation' (FR/EN)
    # or the verb 'réserver' is present. This avoids accidental triggering on unrelated phrases.
    return ("reservation" in text_lower) or ("réservation" in text_lower) or ("réserver" in text_lower)

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
            temp_file = None
            try:
                if CV2_AVAILABLE:
                    # Méthode 1: Utiliser OpenCV si disponible
                    cap = cv2.VideoCapture(camera_url)
                    ret, frame = cap.read()
                    cap.release()
                    
                    if not ret:
                        print("❌ Impossible de capturer une image depuis la caméra avec OpenCV: {}".format(camera_url))
                        raise Exception("OpenCV capture failed")
                    
                    # Sauvegarder temporairement l'image
                    temp_file = "/tmp/pepper_qr_scan.png"
                    cv2.imwrite(temp_file, frame)
                    
                    if not os.path.exists(temp_file):
                        print("❌ Impossible de sauvegarder l'image capturée")
                        raise Exception("Image save failed")
                else:
                    # Méthode 2: Télécharger directement depuis l'URL si c'est une URL HTTP
                    print("⚠️ OpenCV non disponible, tentative de téléchargement direct depuis l'URL...")
                    if camera_url.startswith("http://") or camera_url.startswith("https://"):
                        # Télécharger l'image directement depuis l'URL
                        img_response = requests.get(camera_url, timeout=10, stream=True)
                        if img_response.status_code == 200:
                            temp_file = "/tmp/pepper_qr_scan.jpg"
                            with open(temp_file, 'wb') as f:
                                for chunk in img_response.iter_content(chunk_size=8192):
                                    f.write(chunk)
                            print("✅ Image téléchargée depuis l'URL de la caméra")
                        else:
                            print("❌ Impossible de télécharger l'image depuis l'URL: {}".format(img_response.status_code))
                            raise Exception("URL download failed")
                    else:
                        print("❌ OpenCV non disponible et URL non HTTP. Veuillez installer OpenCV avec: pip install opencv-python")
                        return None
                
                # Envoyer l'image à l'API pour le scan QR code
                with open(temp_file, "rb") as f:
                    response = requests.post(
                        url,
                        files={"file": f},
                        timeout=API_CONFIG["timeout"]
                    )
            except Exception as e:
                print("❌ Erreur lors de la capture d'image depuis la caméra: {}".format(e))
                return None
            finally:
                # Nettoyer le fichier temporaire
                if temp_file:
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

    # Assurer que `text` est une chaîne unicode (str). Si bytes, décoder en utf-8.
    if isinstance(text, bytes):
        try:
            text = text.decode("utf-8")
        except Exception:
            text = text.decode("utf-8", errors="ignore")

    text_lower = str(text).lower()
    qr_keywords = [
        "scanner", "scanne", "qr code", "code qr", "vérifier", "verifier",
        "vérifie", "verifie", "mon qr", "mon code", "ma réservation",
        "ma reservation", "check", "scan"
    ]
    
    return any(keyword in text_lower for keyword in qr_keywords)

# ============================================================================
# Fonctions utilitaires
# ============================================================================
def force_utf8(s):
    """Force a value to a UTF-8-safe string for Python2/3 environments.

    Returns a unicode `str` on Python 3 (decoded UTF-8) or a UTF-8 encoded
    `str`/`bytes` on Python 2 as appropriate. If conversion fails, returns
    an empty string.
    """
    try:
        if s is None:
            return ""
        # Detect Python2
        try:
            unicode  # type: ignore
            is_py2 = True
        except NameError:
            is_py2 = False

        if is_py2:
            try:
                if isinstance(s, unicode):  # type: ignore
                    return s.encode('utf-8')
                elif isinstance(s, str):
                    try:
                        return s.decode('utf-8', 'ignore').encode('utf-8')
                    except Exception:
                        return s
            except Exception:
                return ""
        else:
            # Python 3: ensure we return a str (unicode)
            if isinstance(s, bytes):
                return s.decode('utf-8', 'ignore')
            elif isinstance(s, str):
                return s
            else:
                return str(s)
    except Exception:
        return ""


def map_language_code_to_ald_label(code):
    """Map common ISO language codes to ALTextToSpeech language labels.

    Returns a label expected by ALTextToSpeech.setLanguage (best-effort).
    """
    try:
        if not code:
            return ROBOT_CONFIG.get("language", "French")
        s = str(code).lower()
        if s.startswith('fr'):
            return 'French'
        if s.startswith('en'):
            return 'English'
        if s.startswith('es'):
            return 'Spanish'
        if s.startswith('de'):
            return 'German'
        if s.startswith('it'):
            return 'Italian'
        if s.startswith('pt'):
            return 'Portuguese'
        if s.startswith('nl'):
            return 'Dutch'
        if s.startswith('ru'):
            return 'Russian'
        if s.startswith('ja'):
            return 'Japanese'
        if s.startswith('ko'):
            return 'Korean'
        if s.startswith('zh'):
            return 'Chinese'
        # Fallback: return configured default
        return ROBOT_CONFIG.get("language", "French")
    except Exception:
        return ROBOT_CONFIG.get("language", "French")

def generate_qr_code_base64(url, size=200):
    """
    Génère un QR code en base64 pour une URL donnée

    Args:
        url: L'URL à encoder dans le QR code
        size: Taille du QR code en pixels

    Returns:
        str: Image QR code en base64 (data URI)
    """
    try:
        import qrcode
        from io import BytesIO
        import base64

        # Créer le QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        # Créer l'image
        img = qr.make_image(fill_color="black", back_color="white")

        # Convertir en base64
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return "data:image/png;base64,{}".format(img_base64)
    except ImportError:
        # Si qrcode n'est pas installé, retourner une image placeholder
        return "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtc2l6ZT0iMTgiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIiBmaWxsPSIjMDAwIj5RUiBDb2RlPC90ZXh0Pjwvc3ZnPg=="
    except Exception as e:
        print("Erreur génération QR code: {}".format(e))
        return ""

def create_tablet_html(title, message, subtitle="", status="", show_mic_button=False, mic_active=False, api_url=None, robot_ip=None, show_chat_button=False, chat_url=None):
    """
    Crée un contenu HTML pour la tablette avec un bouton micro interactif et un bouton de chat avec QR code

    Args:
        title: Titre principal
        message: Message principal
        subtitle: Sous-titre (optionnel)
        status: Statut/étape actuelle (optionnel)
        show_mic_button: Afficher le bouton micro (optionnel)
        mic_active: État du bouton micro (True = actif/enregistrement)
        api_url: URL de l'API Flask pour les requêtes (optionnel)
        robot_ip: IP du robot pour calculer l'IP locale (optionnel)
        show_chat_button: Afficher le bouton de chat avec QR code (optionnel)
        chat_url: URL du site de chat pour le QR code (optionnel)

    Returns:
        str: Contenu HTML
    """
    # Force values to UTF-8-safe strings first (helps Pepper/tablet compatibility)
    title = force_utf8(title)
    message = force_utf8(message)
    subtitle = force_utf8(subtitle)
    status = force_utf8(status)

    # Prepare status text safely (escape then transliterate to ASCII fallback)
    if status:
        status_text_escaped = escape_html(status)
        status_text_safe = transliterate_to_ascii(status_text_escaped)
        status_html = "<div style='background-color: #ffffff; color: #667eea; padding: 10px; border-radius: 5px; margin-bottom: 20px; font-size: 18px; font-weight: bold;'>{}</div>".format(status_text_safe)
    else:
        status_html = ""
    
    # URL de l'API Flask (par défaut localhost:5000)
    # Si show_mic_button est True et api_url n'est pas fourni, calculer l'IP locale
    if api_url is None:
        if show_mic_button and robot_ip:
            # Pour le bouton micro, on a besoin d'une IP accessible depuis le robot
            local_ip = get_local_ip_for_robot(robot_ip)
            api_url = "http://{}:5000".format(local_ip)
        else:
            api_url = API_CONFIG["base_url"]
    
    # Bouton micro simplifié pour compatibilité Pepper
    mic_button_html = ""
    if show_mic_button:
        mic_color = "#ff4444" if mic_active else "#4CAF50"
        mic_border_color = "#cc0000" if mic_active else "#2E7D32"
        mic_size = "140px" if mic_active else "120px"
        button_text = "STOP" if mic_active else "MIC"
        instruction_text = "Appuyez pour arreter" if mic_active else "Appuyez pour parler"
        
        # Bouton micro avec JavaScript pour contrôler l'enregistrement
        mic_button_html = """
        <div style="margin-top: 40px; margin-bottom: 20px; text-align: center;">
            <button id="micButton" onclick="toggleRecording()" style="
                background-color: {};
                border: 5px solid {};
                border-radius: 50%;
                width: {};
                height: {};
                cursor: pointer;
                color: white;
                font-size: 40px;
                font-weight: bold;
                margin: 0 auto;
                display: block;
            ">
                {}
            </button>
            <p style="margin-top: 20px; font-size: 24px; font-weight: bold; color: white;">
                MICROPHONE
            </p>
            <p id="instruction" style="margin-top: 10px; font-size: 18px; color: white;">
                {}
            </p>
        </div>
        <script>
            var isRecording = {};
            var apiUrl = '{}';
            
            // Fonction pour faire une requête HTTP (compatible avec les anciens navigateurs)
            function makeRequest(url, method, callback) {{
                var xhr = new XMLHttpRequest();
                xhr.open(method, url, true);
                xhr.setRequestHeader('Content-Type', 'application/json');
                xhr.onreadystatechange = function() {{
                    if (xhr.readyState === 4) {{
                        if (xhr.status >= 200 && xhr.status < 300) {{
                            callback(true, xhr.responseText);
                        }} else {{
                            callback(false, xhr.statusText);
                        }}
                    }}
                }};
                xhr.onerror = function() {{
                    callback(false, 'Erreur de connexion');
                }};
                xhr.send();
            }}
            
            function toggleRecording() {{
                var btn = document.getElementById('micButton');
                var instruction = document.getElementById('instruction');
                
                if (!isRecording) {{
                    // Démarrer l'enregistrement
                    instruction.textContent = 'Demarrage...';
                    makeRequest(apiUrl + '/record/start', 'POST', function(success, response) {{
                        if (success) {{
                            isRecording = true;
                            btn.style.backgroundColor = '#ff4444';
                            btn.style.borderColor = '#cc0000';
                            btn.innerHTML = 'STOP';
                            instruction.textContent = 'Parlez maintenant... Appuyez pour arreter';
                        }} else {{
                            instruction.textContent = 'Erreur: ' + response;
                            console.error('Erreur demarrage:', response);
                        }}
                    }});
                }} else {{
                    // Arrêter l'enregistrement
                    instruction.textContent = 'Arret...';
                    makeRequest(apiUrl + '/record/stop', 'POST', function(success, response) {{
                        if (success) {{
                            isRecording = false;
                            btn.style.backgroundColor = '#4CAF50';
                            btn.style.borderColor = '#2E7D32';
                            btn.innerHTML = 'MIC';
                            instruction.textContent = 'Enregistrement termine';
                        }} else {{
                            instruction.textContent = 'Erreur: ' + response;
                            console.error('Erreur arret:', response);
                        }}
                    }});
                }}
            }}
            
            // Afficher l'URL de l'API pour debug
            console.log('API URL:', apiUrl);
        </script>
        """.format(
            mic_color,
            mic_border_color,
            mic_size,
            mic_size,
            button_text,
            instruction_text,
            "true" if mic_active else "false",
            api_url
        )
    
    # Bouton de chat avec QR code
    chat_button_html = ""
    if show_chat_button and chat_url:
        # Générer le QR code
        qr_code_data = generate_qr_code_base64(chat_url)
        
        chat_button_html = """
        <div style="margin-top: 40px; margin-bottom: 20px; text-align: center;">
            <button id="chatButton" onclick="toggleChatQR()" style="
                background-color: #FF9800;
                border: 3px solid #E65100;
                border-radius: 25px;
                padding: 15px 30px;
                cursor: pointer;
                color: white;
                font-size: 24px;
                font-weight: bold;
                margin: 0 auto;
                display: block;
            ">
                💬 Chatter avec Pepper
            </button>
            <div id="qrContainer" style="display: none; margin-top: 20px;">
                <p style="font-size: 18px; color: white; margin-bottom: 10px;">
                    Scannez ce QR code avec votre téléphone :
                </p>
                <img src="{}" alt="QR Code Chat" style="width: 200px; height: 200px; border: 3px solid white; border-radius: 10px;"/>
                <p style="font-size: 16px; color: white; margin-top: 10px;">
                    Ou visitez: <a href="{}" style="color: #FFD700; text-decoration: underline;">{}</a>
                </p>
            </div>
        </div>
        <script>
            function toggleChatQR() {{
                var container = document.getElementById('qrContainer');
                if (container.style.display === 'none') {{
                    container.style.display = 'block';
                }} else {{
                    container.style.display = 'none';
                }}
            }}
        </script>
        """.format(qr_code_data, chat_url, chat_url)
    
    # Prepare subtitle safely for HTML
    try:
        if isinstance(subtitle, bytes):
            subtitle = subtitle.decode('utf-8', errors='ignore')
    except Exception:
        subtitle = str(subtitle)
    subtitle_escaped = escape_html(subtitle)
    try:
        title_escaped = escape_html(title)
    except Exception:
        title_escaped = escape_html(str(title))
    try:
        message_escaped = escape_html(message)
    except Exception:
        message_escaped = escape_html(str(message))

    # Also create ASCII-safe fallbacks (remove accents and emojis) for environments that don't support UTF-8
    title_safe = transliterate_to_ascii(title_escaped)
    message_safe = transliterate_to_ascii(message_escaped)
    subtitle_safe = transliterate_to_ascii(subtitle_escaped)

    # HTML simplifié pour une meilleure compatibilité avec Pepper
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pepper</title>
</head>
<body style="background-color: #667eea; color: white; font-family: Arial, sans-serif; padding: 20px; text-align: center; margin: 0;">
    <div style="background-color: #8a9eff; border-radius: 15px; padding: 30px; margin: 20px auto; max-width: 90%;">
        {}
        <h1 style="font-size: 36px; margin: 15px 0; color: white;">{}</h1>
        <div style="background-color: #9aafff; border-radius: 10px; padding: 20px; margin: 20px 0;">
            <p style="font-size: 24px; line-height: 1.6; margin: 0; color: white;">{}</p>
        </div>
        {}
        {}
        {}
    </div>
</body>
</html>""".format(
        status_html,
        title_safe,
        message_safe,
        "<div style='margin-top: 20px; padding: 15px; background-color: #9aafff; border-radius: 8px;'><p style='font-size: 18px; margin: 0; color: white;'><strong>Vous:</strong> {}</p></div>".format(subtitle_safe) if subtitle else "",
        mic_button_html,
        chat_button_html
    )
    return html


# Message de test à faire dire au robot
TEST_MESSAGE = "Bonjour, je suis connecté et prêt à vous aider. Ceci est un test de connexion."
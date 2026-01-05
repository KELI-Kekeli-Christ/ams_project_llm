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
    safe_print("OpenCV (cv2) non disponible. Le scan QR code utilisera le téléchargement direct depuis l'URL si disponible.")
    safe_print("Pour installer OpenCV: pip install opencv-python")





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
        sock.settimeout(1)  # Timeout très court pour éviter le blocage
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
            print("❌ Erreur lors du démarrage de Flask: {}".format(e))
            import traceback
            traceback.print_exc()
            return False

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
        self.video = None
        self.camera_url = None
        self.video_stream_active = False
        self.latest_qr_result = None
        import threading
        self.qr_lock = threading.Lock()
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
            # Essayer plusieurs URLs possibles pour la caméra Pepper
            # Pepper peut avoir différentes URLs selon la version et la configuration
            possible_urls = [
                "http://{}:8080/cameras/front".format(self.ip),  # URL standard Pepper
                "http://{}:8080/video".format(self.ip),  # URL alternative
                "http://{}:8080/cameras/head".format(self.ip),  # Caméra de la tête
                "http://{}:9559/video".format(self.ip),  # Port NAOqi
            ]
            self.camera_url = possible_urls[0]  # Par défaut, utiliser la première
            print("URL caméra configurée: {}".format(self.camera_url))
            print("   URLs alternatives disponibles si nécessaire: {}".format(possible_urls[1:]))
        except Exception as e:
            print("Service Video non disponible (normal pour robot virtuel): {}".format(e))
            self.video = None
            # Pour le robot virtuel ou si le service n'est pas disponible,
            # essayer plusieurs URLs possibles
            possible_urls = [
                "http://{}:8080/cameras/front".format(self.ip),
                "http://{}:8080/video".format(self.ip),
                "http://{}:8080/cameras/head".format(self.ip),
            ]
            self.camera_url = possible_urls[0]
        
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

        # Python2/3 safe handling of unicode/str
        try:
            try:
                unicode  # type: ignore
                is_py2 = True
            except NameError:
                is_py2 = False

            if is_py2:
                if isinstance(text, unicode):  # type: ignore
                    text = text.encode("utf-8")
                elif isinstance(text, str):
                    try:
                        text = text.decode("utf-8").encode("utf-8")
                    except Exception:
                        pass
            else:
                # Python 3: ensure str -> utf-8 encoded bytes if required by SDK
                if isinstance(text, bytes):
                    try:
                        text = text.decode('utf-8')
                    except Exception:
                        text = text.decode('utf-8', errors='ignore')

            if language:
                try:
                    self.tts.setLanguage(language)
                except Exception:
                    pass

            # Log intent and call TTS
            print("Le robot dit: '{}'".format(text))
            try:
                self.tts.say(text)
            except Exception:
                # Some SDKs expect utf-8 bytes on Python2; try fallback
                try:
                    if not is_py2:
                        self.tts.say(text)
                    else:
                        self.tts.say(text)
                except Exception as e:
                    print("Erreur TTS:", e)
                    return False

            return True
        except Exception as e:
            print("Erreur lors de la synthèse vocale: {}".format(e))
            return False
    
    def wake_tablet(self, show_blank=False):
        """
        S'assure que la tablette est allumée et active
        
        Args:
            show_blank: Si True, affiche une page blanche (uniquement au premier démarrage)
        """
        if not self.tablet:
            print("Service Tablet non disponible")
            return False
        
        try:
            # Méthode 1: wakeUp (si disponible) - sans afficher de page blanche
            try:
                self.tablet.wakeUp()
                print("Tablette activee via wakeUp()")
                time.sleep(0.3)  # Délai court
            except Exception as e:
                    print("wakeUp() non disponible: {}".format(e))
            
            # Ne pas afficher de page blanche sauf si explicitement demandé (premier démarrage)
            if show_blank:
                try:
                    # Afficher un HTML minimal pour activer la tablette (uniquement au premier démarrage)
                    minimal_html = "<html><head><meta charset='UTF-8'></head><body style='background-color: #667eea; margin: 0; padding: 0;'></body></html>"
                    self.tablet.showWebview(minimal_html)
                    print("Tablette initialisee")
                    time.sleep(0.5)
                except Exception as e:
                    print("showWebview() a echoue: {}".format(e))
            
            return True
            
        except Exception as e:
            print("Erreur lors de l'activation de la tablette: {}".format(e))
            import traceback
            traceback.print_exc()
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
        
        # Ne pas appeler wake_tablet() à chaque fois pour éviter les pages blanches
        # La tablette reste active une fois initialisée
        
        try:
            import sys
            
            # Normaliser le contenu HTML pour Python 2/3
            html_normalized = html_content
            if sys.version_info[0] < 3:
                # Python 2: s'assurer que c'est une chaîne Unicode
                if isinstance(html_normalized, str):
                    try:
                        html_normalized = html_normalized.decode('utf-8')
                    except UnicodeDecodeError:
                        html_normalized = html_normalized.decode('utf-8', 'ignore')
            
            # Méthode 1: Essayer avec URL data: (base64) via loadUrl
            try:
                import base64
                # Encoder le HTML en base64
                if sys.version_info[0] < 3:
                    html_bytes = html_normalized.encode('utf-8', 'ignore')
                else:
                    html_bytes = html_normalized.encode('utf-8')
                
                html_encoded = base64.b64encode(html_bytes)
                # En Python 2, b64encode retourne une str, en Python 3 c'est bytes
                if sys.version_info[0] >= 3:
                    html_encoded = html_encoded.decode('ascii')
                
                data_url = "data:text/html;charset=utf-8;base64,{}".format(html_encoded)
                print("Tentative avec URL data: (taille: {} caractères)...".format(len(data_url)))
                
                self.tablet.loadUrl(data_url)
                print("Texte affiché sur la tablette via loadUrl (data URL)!")
                time.sleep(1)
                return True
            except Exception as e_data:
                print("loadUrl avec data URL a échoué: {}".format(e_data))
                
                # Méthode 2: Essayer showWebview avec HTML direct
            try:
                    # Pour Python 2, convertir en bytes (str)
                    if sys.version_info[0] < 3:
                        html_for_tablet = html_normalized.encode('utf-8', 'ignore')
                    else:
                        html_for_tablet = html_normalized
                    
                    print("Tentative avec showWebview HTML direct (taille: {} caractères)...".format(len(html_for_tablet)))
                    self.tablet.showWebview(html_for_tablet)
                    print("Texte affiché sur la tablette via showWebview (HTML direct)!")
                    time.sleep(1)
                    return True
            except Exception as e1:
                print("showWebview avec HTML direct a échoué: {}".format(e1))
                
                # Méthode 2: Essayer avec loadUrl et un serveur HTTP local
                try:
                    import codecs
                    import tempfile
                    import threading
                    import socket
                    
                    # Obtenir l'IP locale
                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        s.connect((self.ip, 80))
                        local_ip = s.getsockname()[0]
                        s.close()
                    except:
                        local_ip = "127.0.0.1"
                    
                    # Créer un répertoire temporaire
                    temp_dir = tempfile.mkdtemp()
                    html_file = os.path.join(temp_dir, "index.html")
                    
                    # Écrire le fichier HTML
                    with codecs.open(html_file, 'w', encoding='utf-8') as f:
                        f.write(html_normalized)
                    
                    # Créer un serveur HTTP simple
                    if sys.version_info[0] < 3:
                        import SocketServer
                        import SimpleHTTPServer
                        Handler = SimpleHTTPServer.SimpleHTTPRequestHandler
                        Server = SocketServer.TCPServer
                    else:
                        import http.server
                        import socketserver
                        Handler = http.server.SimpleHTTPRequestHandler
                        Server = socketserver.TCPServer
                    
                    port = 8080
                    old_dir = os.getcwd()
                    os.chdir(temp_dir)
                    
                    try:
                        httpd = Server(("", port), Handler)
                        server_thread = threading.Thread(target=httpd.serve_forever)
                        server_thread.daemon = True
                        server_thread.start()
                        
                        http_url = "http://{}:{}/index.html".format(local_ip, port)
                        print("Tentative avec serveur HTTP: {}".format(http_url))
                        
                        # Essayer loadUrl
                        self.tablet.loadUrl(http_url)
                        print("Texte affiché sur la tablette via loadUrl (HTTP)!")
                        time.sleep(2)
                        return True
                    finally:
                        os.chdir(old_dir)
                       
                            
                except Exception as e2:
                    print("Toutes les méthodes ont échoué: {}".format(e2))
                    import traceback
                    traceback.print_exc()
                    return False
                    
        except Exception as e:
            print("Erreur lors de l'affichage sur la tablette: {}".format(e))
            import traceback
            traceback.print_exc()
            return False
    
    def capture_image_from_camera(self):
        """
        Capture une image depuis la caméra du robot Pepper

        Returns:
            tuple: (image_bytes, width, height) where image_bytes is raw RGB bytes,
                   or (None, None, None) on error
        """
        if not self.video:
            print("Service Video non disponible")
            return None, None, None
        
        try:
            # Capturer une image depuis la caméra
            # ALVideoDevice utilise un système de subscription
            video_client = self.video.subscribeCamera("python_client", 0, 2, 11, 5)  # 0 = caméra frontale, 2 = VGA, 11 = RGB
            
            # Attendre un peu pour que l'image soit capturée
            time.sleep(0.5)
            
            # Obtenir l'image
            image_container = self.video.getImageRemote(video_client)
            
            if image_container:
                # Extraire les données de l'image
                image_data = image_container[6]  # Les données de l'image sont à l'index 6
                image_width = image_container[0]
                image_height = image_container[1]

                # Se désabonner de la caméra
                self.video.unsubscribe(video_client)

                print("Image capturée: {}x{}".format(image_width, image_height))
                return image_data, image_width, image_height
            
            # Se désabonner en cas d'erreur
            try:
                self.video.unsubscribe(video_client)
            except Exception:
                pass
            return None, None, None
            
        except Exception as e:
            print("Erreur lors de la capture d'image: {}".format(e))
            try:
                self.video.unsubscribe(video_client)
            except:
                pass
            return None, None, None
    
    def start_continuous_video_stream(self):
        """
        Démarre un flux vidéo continu pour la détection faciale
        Utilise directement ALVideoDevice selon la documentation Aldebaran
        
        Returns:
            bool: True si le flux a démarré avec succès, False sinon
        """
        if not self.video:
            print("Service ALVideoDevice non disponible")
            return False
        
        try:
            print("Demarrage du flux video continu via ALVideoDevice...")
            
            # Utiliser ALVideoDevice directement (selon doc.aldebaran.com)
            # Créer un thread qui capture les images et les envoie au service Flask
            import threading
            
            def video_capture_worker():
                """Worker qui capture les images via ALVideoDevice et les envoie au service Flask"""
                try:
                    # S'abonner à la caméra selon la documentation Aldebaran
                    # resolution: 2 = VGA (640x480), colorSpace: 11 = RGB, fps: 5
                    video_client = self.video.subscribeCamera("python_face_detection", 0, 2, 11, 5)
                    print("Abonnement a la camera reussi")
                    
                    frame_count = 0
                    while self.video_stream_active:
                        try:
                            # Capturer une image selon la documentation
                            image_container = self.video.getImageRemote(video_client)
                            
                            if image_container:
                                # Extraire les données de l'image
                                image_width = image_container[0]
                                image_height = image_container[1]
                                image_data = image_container[6]  # Données de l'image
                                
                                # Envoyer l'image au service Flask pour détection faciale
                                # Créer un fichier temporaire avec l'image
                                import tempfile
                                temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                                
                                # Convertir les données en image PIL puis sauvegarder
                                try:
                                    from PIL import Image
                                    # Les données sont en RGB
                                    image_bytes = bytes(bytearray(image_data))
                                    im = Image.frombytes("RGB", (image_width, image_height), image_bytes)
                                    im.save(temp_file.name, "JPEG")
                                    temp_file.close()
                                    
                                    # Envoyer au service Flask (avec retries)
                                    with open(temp_file.name, 'rb') as f:
                                        response = post_file_with_retries(
                                            "{}/face/detect".format(API_CONFIG["base_url"]),
                                            files={"file": f},
                                        )

                                    # Every few frames, also try QR detection to detect presented QR codes
                                    try:
                                        if frame_count % 5 == 0:
                                            with open(temp_file.name, 'rb') as qf:
                                                qr_resp = requests.post(
                                                    "{}/scan_qr".format(API_CONFIG["base_url"]),
                                                    files={"file": qf},
                                                    timeout=API_CONFIG["timeout"]
                                                )
                                            if qr_resp.ok:
                                                try:
                                                    qr_json = qr_resp.json()
                                                except Exception:
                                                    qr_json = json.loads(qr_resp.text)
                                                if qr_json and qr_json.get('success'):
                                                    # Store latest QR result thread-safely
                                                    try:
                                                        with self.qr_lock:
                                                            self.latest_qr_result = qr_json
                                                        print("✅ QR code detecte en flux video: {}".format(qr_json.get('qr_id', 'N/A')))
                                                    except Exception:
                                                        pass
                                    except Exception:
                                        pass
                                    
                                    # Nettoyer le fichier temporaire
                                    try:
                                        os.unlink(temp_file.name)
                                    except:
                                        pass
                                    
                                    frame_count += 1
                                    if frame_count % 10 == 0:  # Log tous les 10 frames
                                        print("{} frames capturees et traitees".format(frame_count))
                                    
                                except Exception as e:
                                    print("Erreur lors du traitement de l'image: {}".format(e))
                                    try:
                                        os.unlink(temp_file.name)
                                    except:
                                        pass
                            
                            time.sleep(0.2)  # Capturer environ 5 images par seconde
                            
                        except Exception as e:
                            print("Erreur lors de la capture: {}".format(e))
                            time.sleep(1.0)
                    
                    # Se désabonner quand on arrête
                    self.video.unsubscribe(video_client)
                    print("Flux video arrete, desabonnement effectue")
                    
                except Exception as e:
                    print("Erreur dans le worker de capture video: {}".format(e))
                    import traceback
                    traceback.print_exc()
                    self.video_stream_active = False
            
            # Démarrer le thread de capture
            self.video_stream_active = True
            capture_thread = threading.Thread(target=video_capture_worker)
            # Python 2.7: utiliser setDaemon() au lieu du paramètre daemon
            capture_thread.setDaemon(True)
            capture_thread.start()
            
            print("✅ Flux vidéo continu démarré via ALVideoDevice")
            time.sleep(1.0)  # Attendre un peu pour que le thread démarre
            return True
            
        except Exception as e:
            print("❌ Erreur lors du démarrage du flux vidéo: {}".format(e))
            import traceback
            traceback.print_exc()
            self.video_stream_active = False
            return False
    
    def stop_continuous_video_stream(self):
        """
        Arrête le flux vidéo continu
        
        Returns:
            bool: True si le flux a été arrêté avec succès, False sinon
        """
        if not self.video_stream_active:
            return True
        
        try:
            print("Arret du flux video continu...")
            response = requests.post(
                "{}/face/stream/stop".format(API_CONFIG["base_url"]),
                timeout=10
            )
            
            if response.ok:
                result = response.json()
                if result.get("success"):
                    self.video_stream_active = False
                    print("✅ Flux vidéo arrêté")
                    return True
            return False
        except Exception as e:
            print("⚠️ Erreur lors de l'arrêt du flux vidéo: {}".format(e))
            self.video_stream_active = False
            return False
    
    def recognize_face_from_stream(self, max_attempts=15, delay=0.3):
        """
        Reconnaît une personne depuis le flux vidéo continu
        Utilise directement ALVideoDevice selon la documentation Aldebaran
        
        Args:
            max_attempts: Nombre maximum de tentatives
            delay: Délai entre chaque tentative (secondes)
        
        Returns:
            str: Nom de la personne reconnue, ou None si non reconnue
        """
        if not self.video:
            print("⚠️ Service ALVideoDevice non disponible")
            return None
        
        try:
            print("👤 Recherche de visage via ALVideoDevice...")
            
            # S'abonner à la caméra selon la documentation Aldebaran
            # 0 = caméra frontale, 2 = VGA (640x480), 11 = RGB, 5 = fps
            video_client = self.video.subscribeCamera("python_face_recognition", 0, 2, 11, 5)
            
            try:
                for attempt in range(max_attempts):
                    # Capturer une image selon la documentation
                    image_container = self.video.getImageRemote(video_client)
                    
                    if image_container:
                        # Extraire les données de l'image
                        image_width = image_container[0]
                        image_height = image_container[1]
                        image_data = image_container[6]  # Données de l'image
                        
                        # Créer un fichier temporaire avec l'image
                        import tempfile
                        temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                        
                        try:
                            # Convertir en image PIL et sauvegarder selon la documentation
                            from PIL import Image
                            image_bytes = bytes(bytearray(image_data))
                            im = Image.frombytes("RGB", (image_width, image_height), image_bytes)
                            im.save(temp_file.name, "JPEG")
                            temp_file.close()
                            
                            # Envoyer au service Flask pour détection (avec retries)
                            with open(temp_file.name, 'rb') as f:
                                response = post_file_with_retries(
                                    "{}/face/detect".format(API_CONFIG["base_url"]),
                                    files={"file": f},
                                )
                            
                            # Nettoyer le fichier temporaire
                            try:
                                os.unlink(temp_file.name)
                            except:
                                pass
                            
                            if response.ok:
                                result = response.json()
                                recognized_persons = result.get("recognized_persons", [])
                                
                                if recognized_persons and len(recognized_persons) > 0:
                                    name = recognized_persons[0]
                                    print("✅ Personne reconnue: {}".format(name))
                                    return name
                            
                            # Attendre avant la prochaine tentative
                            if attempt < max_attempts - 1:
                                time.sleep(delay)
                                
                        except Exception as e:
                            print("⚠️ Erreur lors du traitement de l'image: {}".format(e))
                            try:
                                os.unlink(temp_file.name)
                            except:
                                pass
                            if attempt < max_attempts - 1:
                                time.sleep(delay)
                                continue
                    
                    else:
                        if attempt < max_attempts - 1:
                            time.sleep(delay)
                            continue
                
                print("ℹ️ Aucune personne reconnue après {} tentatives".format(max_attempts))
                return None
                
            finally:
                # Se désabonner selon la documentation
                self.video.unsubscribe(video_client)
                
        except Exception as e:
            print("❌ Erreur lors de la reconnaissance faciale: {}".format(e))
            import traceback
            traceback.print_exc()
            return None
    
    def recognize_face_from_camera(self):
        """
        Capture une image depuis la caméra et essaie de reconnaître la personne
        (Méthode de fallback si le flux vidéo n'est pas disponible)
        
        Returns:
            str: Nom de la personne reconnue, ou None si non reconnue
        """
        try:
            # Essayer d'abord avec le flux vidéo continu si disponible
            if self.video_stream_active:
                return self.recognize_face_from_stream()
            
            # Sinon, utiliser la méthode de capture d'image unique
            image_data, image_width, image_height = self.capture_image_from_camera()

            if not image_data:
                print("Impossible de capturer l'image")
                return None

            # Convert raw RGB bytes to JPEG using PIL then send to API
            import tempfile
            import os
            try:
                from PIL import Image
                image_bytes = bytes(bytearray(image_data))
                im = Image.frombytes("RGB", (image_width, image_height), image_bytes)
                temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                im.save(temp_file.name, "JPEG")
                temp_file.close()
            except Exception:
                # Fallback: write raw bytes (may not work but attempt)
                temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                temp_file.write(image_data)
                temp_file.close()
            
            try:
                # Envoyer à l'API Flask
                with open(temp_file.name, 'rb') as f:
                    response = post_file_with_retries(
                        "{}/face/detect".format(API_CONFIG["base_url"]),
                        files={"file": f},
                    )
                
                if response.ok:
                    result = response.json()
                    recognized_persons = result.get("recognized_persons", [])
                    
                    if recognized_persons and len(recognized_persons) > 0:
                        # Retourner le premier nom reconnu
                        name = recognized_persons[0]
                        print("Personne reconnue: {}".format(name))
                        return name
                    else:
                        print("Aucune personne reconnue")
                        return None
                else:
                    print("Erreur API: {}".format(response.status_code))
                    return None
            finally:
                # Nettoyer le fichier temporaire
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
                    
        except Exception as e:
            print("Erreur lors de la reconnaissance faciale: {}".format(e))
            return None
    
    def hide_tablet_webview(self):
        """
        Cache simplement la vue web de la tablette sans réinitialiser complètement
        """
        if not self.tablet:
            return False
        
        try:
            # Méthode 1: hideWebview (cache la vue web)
            try:
                self.tablet.hideWebview()
                print("Vue web de la tablette cachée")
                return True
            except:
                pass
            
            # Méthode 2: Charger une page blanche (fallback)
            try:
                self.tablet.loadUrl("about:blank")
                print("Vue web de la tablette cachée (page blanche)")
                return True
            except:
                pass
            
            print("Impossible de cacher la vue web de la tablette")
            return False
        except Exception as e:
            print("Erreur lors du masquage de la vue web: {}".format(e))
            return False
    
    def check_for_new_face(self, last_recognized_name=None):
        """
        Vérifie s'il y a un nouveau visage détecté dans le flux vidéo
        
        Args:
            last_recognized_name: Nom de la dernière personne reconnue (pour éviter les répétitions)
        
        Returns:
            str: Nom de la personne reconnue si différente de last_recognized_name, None sinon
        """
        if not self.video_stream_active:
            return None
        
        try:
            response = requests.get(
                "{}/face/stream/detections".format(API_CONFIG["base_url"]),
                timeout=2
            )
            
            if response.ok:
                result = response.json()
                if result.get("success") and result.get("streaming"):
                    recognized_persons = result.get("recognized_persons", [])
                    
                    if recognized_persons and len(recognized_persons) > 0:
                        current_name = recognized_persons[0]
                        # Si c'est une nouvelle personne ou une personne différente
                        if current_name != last_recognized_name:
                            return current_name
            return None
        except:
            return None
    
    def disconnect(self):
        """Déconnecte du robot"""
        # Ne plus cacher la vue web - la laisser affichée
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

def transcribe_audio(audio_file):
    """
    Transcrit le fichier audio via l'API Flask
    
    Args:
        audio_file: Chemin du fichier audio à transcrire (relatif ou absolu)
    
    Returns:
        str: Texte transcrit, ou None en cas d'erreur
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
            return None
        
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
                    return None

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

            safe_print("Texte transcrit: {} (lang={})", text, language)
            return text, language
    except Exception as e:
                print("Erreur lors de la transcription: {}".format(e))
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
def create_tablet_html(title, message, subtitle="", status="", show_mic_button=False, mic_active=False, api_url=None, robot_ip=None):
    """
    Crée un contenu HTML pour la tablette avec un bouton micro interactif
    
    Args:
        title: Titre principal
        message: Message principal
        subtitle: Sous-titre (optionnel)
        status: Statut/étape actuelle (optionnel)
        show_mic_button: Afficher le bouton micro (optionnel)
        mic_active: État du bouton micro (True = actif/enregistrement)
        api_url: URL de l'API Flask pour les requêtes (optionnel)
        robot_ip: IP du robot pour calculer l'IP locale (optionnel)
    
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
    </div>
</body>
</html>""".format(
        status_html,
        title_safe,
        message_safe,
        "<div style='margin-top: 20px; padding: 15px; background-color: #9aafff; border-radius: 8px;'><p style='font-size: 18px; margin: 0; color: white;'><strong>Vous:</strong> {}</p></div>".format(subtitle_safe) if subtitle else "",
        mic_button_html
    )
    return html


# ============================================================================
# Fonction principale - Conversation interactive
# ============================================================================
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
                ok = safe_say(robot, welcome_message, language=ROBOT_CONFIG["language"])
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
        
        # État de la conversation pour les réservations
        conversation_context = {
            "in_reservation_mode": False,
            "collected_info": {},
            "missing_fields": []
        }
        
        # Variable pour suivre la dernière personne reconnue (pour éviter les répétitions)
        last_recognized_name = recognized_name
        
        # ====================================================================
        # BOUCLE DE CONVERSATION
        # ====================================================================
        conversation_count = 0
        max_conversations = 50  # Limite de sécurité
        
        while conversation_count < max_conversations:
            conversation_count += 1
            print("\n" + "=" * 60)
            print("Tour de conversation #{}".format(conversation_count))
            print("=" * 60)
            
            # Vérifier s'il y a un nouveau visage détecté pendant la session
            # Vérifier si un QR a été détecté en arrière-plan via le flux vidéo
            try:
                qr_scan = None
                if robot.latest_qr_result:
                    with robot.qr_lock:
                        qr_scan = robot.latest_qr_result
                        robot.latest_qr_result = None
                if qr_scan:
                    print("📷 QR détecté en arrière-plan")
                    qr_result = qr_scan
                    if qr_result and qr_result.get("success"):
                        reservation = qr_result.get("reservation", {})
                        client = qr_result.get("client", {})
                        qr_id = qr_result.get("qr_id", "N/A")
                        client_name = "{} {}".format(client.get("prenom", ""), client.get("nom", "")).strip()
                        if not client_name:
                            client_name = "Client"
                        confirmation_msg = "Parfait ! QR détecté. Bonjour {}, votre réservation {} est confirmée.".format(client_name, qr_id)
                        if robot.tts:
                            safe_say(robot, confirmation_msg, language=tts_lang)
                        if robot.tablet:
                            html_content = create_tablet_html(
                                title="✅ QR Code détecté",
                                message="Réservation confirmée",
                                subtitle="ID: {}".format(qr_id),
                                status="🟢 Validé",
                                show_mic_button=True,
                                mic_active=False
                            )
                            robot.display_text(html_content)
                        print("✅ QR code validé en arrière-plan: {}".format(qr_id))
                        time.sleep(3)
                        continue
            except Exception as e:
                print("Erreur lors du traitement du QR détecté en arrière-plan: {}".format(e))

            if robot.video_stream_active:
                new_face = robot.check_for_new_face(last_recognized_name)
                if new_face:
                    print("Nouveau visage detecte: {}".format(new_face))
                    greeting_msg = "Ah bonjour {} !".format(new_face)
                    if robot.tts:
                        ok = safe_say(robot, greeting_msg, language=ROBOT_CONFIG["language"])
                        if not ok:
                            print("TTS failed to speak greeting for {}".format(new_face))
                    last_recognized_name = new_face
                    
                    # Mettre à jour l'affichage sur la tablette
                    if robot.tablet:
                        html_content = create_tablet_html(
                            title="Bonjour",
                            message="Ah bonjour {} !".format(new_face),
                            subtitle="",
                            status="Personne detectee",
                            show_mic_button=True,
                            mic_active=False,
                            robot_ip=robot.ip
                        )
                        robot.display_text(html_content)
                    time.sleep(1.0)  # Petite pause après la salutation
            
            # Afficher le bouton micro en attente
            if robot.tablet:
                html_content = create_tablet_html(
                    title="Pepper",
                    message="Appuyez sur le micro pour parler",
                    subtitle="",
                    status="En attente",
                    show_mic_button=True,
                    mic_active=False,
                    robot_ip=robot.ip
                )
                robot.display_text(html_content)
            
            # Demander à l'utilisateur de parler
            if robot.tts and conversation_count == 1:
                # Déjà dit au début
                pass
            elif not conversation_context["in_reservation_mode"]:
                if robot.tts:
                    safe_say(robot, "Comment puis-je vous aider ?", language=ROBOT_CONFIG["language"])
            
            # Afficher le bouton micro et attendre que l'utilisateur clique dessus
            print("\nCliquez sur le micro pour demarrer l'enregistrement...")
            print("   (Ensuite, cliquez à nouveau pour arrêter)")
            
            # Afficher le bouton micro en attente
            if robot.tablet:
                html_content = create_tablet_html(
                    title="Pret",
                    message="Cliquez sur le micro pour parler",
                    status="En attente...",
                    show_mic_button=True,
                    mic_active=False,
                    robot_ip=robot.ip
                )
                robot.display_text(html_content)
                # Afficher l'URL de l'API utilisée
                local_ip = get_local_ip_for_robot(robot.ip)
                api_url_for_tablet = "http://{}:5000".format(local_ip)
                print("URL de l'API pour la tablette: {}".format(api_url_for_tablet))
            
            # Attendre que l'utilisateur clique sur le micro pour démarrer (ou timeout)
            print("⏳ En attente du démarrage de l'enregistrement...")
            print("   (Si le bouton ne fonctionne pas, l'enregistrement démarrera automatiquement dans 10 secondes)")
            max_wait_start = 10  # Maximum 10 secondes pour démarrer (timeout plus court)
            check_interval = 0.5
            elapsed_time = 0
            recording_started = False
            
            while elapsed_time < max_wait_start and not recording_started:
                time.sleep(check_interval)
                elapsed_time += check_interval
                
                # Vérifier si l'enregistrement a démarré
                try:
                    status_response = requests.get(
                        "{}/record/status".format(API_CONFIG["base_url"]),
                        timeout=2
                    )
                    if status_response.ok:
                        status = status_response.json()
                        if status.get("recording", False):
                            recording_started = True
                            print("Enregistrement demarre via le bouton micro. Parlez maintenant...")
                            # Mettre à jour l'affichage
                            if robot.tablet:
                                html_content = create_tablet_html(
                                    title="Enregistrement...",
                                    message="Je vous ecoute",
                                    status="Enregistrement en cours... Cliquez sur le micro pour arreter",
                                    show_mic_button=True,
                                    mic_active=True,
                                    robot_ip=robot.ip
                                )
                                robot.display_text(html_content)
                except Exception as e:
                    # Ignorer les erreurs de connexion temporaires
                    pass
            
            if not recording_started:
                print("⏱️ Timeout: démarrage automatique de l'enregistrement...")
                # Fallback: démarrer automatiquement après le timeout
                try:
                    response = requests.post("{}/record/start".format(API_CONFIG["base_url"]), timeout=5)
                    if response.ok:
                        recording_started = True
                        print("Enregistrement demarre automatiquement. Parlez maintenant...")
                        if robot.tablet:
                            html_content = create_tablet_html(
                                title="Enregistrement...",
                                message="Je vous ecoute",
                                status="Enregistrement en cours... Cliquez sur le micro pour arreter",
                                show_mic_button=True,
                                mic_active=True,
                                robot_ip=robot.ip
                            )
                            robot.display_text(html_content)
                except Exception as e:
                    print("❌ Erreur lors du démarrage automatique: {}".format(e))
            
            # 1. Attendre que l'enregistrement soit arrêté via le bouton micro
            audio_file = record_audio_manual()
            
            if not audio_file:
                error_msg = "Je n'ai pas réussi à enregistrer votre message. Pouvez-vous réessayer ?"
                print("❌ Échec de l'enregistrement")
                if robot.tts:
                    safe_say(robot, error_msg, language=ROBOT_CONFIG["language"])
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
            transcribed_text, detected_lang = transcribe_audio(audio_file)

            # Determine TTS language: prefer detected language from Whisper, else default
            tts_lang = detected_lang if detected_lang else ROBOT_CONFIG["language"]
            # Map detected language code to ALTextToSpeech label (e.g., 'fr' -> 'French')
            try:
                tts_lang_mapped = map_language_code_to_ald_label(tts_lang)
                safe_print("Detected language: {} -> using TTS label: {}", tts_lang, tts_lang_mapped)
                tts_lang = tts_lang_mapped
            except Exception:
                pass

            # Vérifier si la transcription a réussi
            if not transcribed_text or len(transcribed_text.strip()) < 3:
                error_msg = "Je n'ai pas bien compris ce que vous avez dit. Pouvez-vous répéter, s'il vous plaît ?"
                print("❌ Transcription vide ou trop courte")
                if robot.tts:
                    safe_say(robot, error_msg, language=tts_lang)
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
                        safe_say(robot, success_msg, language=tts_lang)
                    
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
                            safe_say(robot, missing_msg, language=tts_lang)
                        
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
                            # Keep the missing-info message visible for at least 10 seconds
                            try:
                                time.sleep(10)
                            except Exception:
                                pass
                        
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
                            safe_say(robot, error_display, language=tts_lang)
                        
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
                    safe_say(robot, "Présentez votre QR code devant ma caméra, s'il vous plaît.", language=tts_lang)
                
                time.sleep(2)  # Donner le temps au client de positionner le QR code
                
                # Scanner le QR code
                print("📷 Scan du QR code en cours...")
                # Prefer using the robot's ALVideoDevice capture when available
                qr_result = None
                try:
                    if robot.video:
                        import tempfile
                        # Capture image from Pepper's camera via ALVideoDevice
                        image_data, image_width, image_height = robot.capture_image_from_camera()
                        if image_data:
                            try:
                                from PIL import Image
                                tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                                try:
                                    image_bytes = bytes(bytearray(image_data))
                                    im = Image.frombytes("RGB", (image_width, image_height), image_bytes)
                                    im.save(tmp.name, "JPEG")
                                    tmp.close()
                                    with open(tmp.name, 'rb') as f:
                                        resp = requests.post(
                                            "{}/scan_qr".format(API_CONFIG["base_url"]),
                                            files={"file": f},
                                            timeout=API_CONFIG["timeout"]
                                        )
                                    resp.raise_for_status()
                                    try:
                                        qr_result = resp.json()
                                    except Exception:
                                        qr_result = json.loads(resp.text)
                                finally:
                                    try:
                                        if os.path.exists(tmp.name):
                                            os.remove(tmp.name)
                                    except Exception:
                                        pass
                            except Exception:
                                # Fallback: write raw bytes if PIL isn't available
                                tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                                tmp.write(image_data)
                                tmp.close()
                                try:
                                    with open(tmp.name, 'rb') as f:
                                        resp = requests.post(
                                            "{}/scan_qr".format(API_CONFIG["base_url"]),
                                            files={"file": f},
                                            timeout=API_CONFIG["timeout"]
                                        )
                                    resp.raise_for_status()
                                    try:
                                        qr_result = resp.json()
                                    except Exception:
                                        qr_result = json.loads(resp.text)
                                finally:
                                    try:
                                        if os.path.exists(tmp.name):
                                            os.remove(tmp.name)
                                    except Exception:
                                        pass
                        else:
                            print("❌ Impossible de capturer l'image depuis la caméra pour le scan QR")
                    # Fallback to existing method (OpenCV/URL) if robot capture not available or failed
                    if not qr_result:
                        qr_result = scan_qr_code_with_api(camera_url=robot.camera_url)
                except Exception as e:
                    print("❌ Erreur lors du scan QR via la caméra du robot: {}".format(e))
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
                        safe_say(robot, confirmation_msg, language=tts_lang)
                    
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
                        safe_say(robot, error_msg, language=tts_lang)
                    
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
                
                # Obtenir la réponse du chatbot (passer la langue détectée comme indice)
                chat_response = chat_with_api(transcribed_text, language=detected_lang)

                # Normalize chat response encoding for Python2/3
                try:
                    try:
                        unicode  # type: ignore
                        is_py2 = True
                    except NameError:
                        is_py2 = False

                    if is_py2:
                        if isinstance(chat_response, unicode):  # type: ignore
                            chat_response = chat_response.encode('utf-8')
                    else:
                        if isinstance(chat_response, bytes):
                            chat_response = chat_response.decode('utf-8', 'ignore')
                except Exception:
                    # Best-effort normalization; continue even if it fails
                    pass
                
                if not chat_response:
                    error_msg = "Je suis désolé, je n'ai pas pu traiter votre demande. Pouvez-vous répéter, s'il vous plaît ?"
                    print("❌ Échec de la communication avec le chat")
                    if robot.tts:
                        safe_say(robot, error_msg, language=tts_lang)
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
                        # Keep chat response visible for at least 10 seconds
                        try:
                            time.sleep(10)
                        except Exception:
                            pass
                    continue
                
                safe_print("✅ Réponse générée: '{}'", chat_response)
                
                # Faire dire la réponse au robot (avec fallback ASCII si nécessaire)
                if robot.tts:
                        safe_say(robot, chat_response, language=tts_lang)

                # Afficher la réponse sur la tablette (gérer problèmes d'encodage)
                if robot.tablet:
                    try:
                        html_content = create_tablet_html(
                            title="Reponse",
                            message=chat_response,
                            subtitle=transcribed_text,
                            status="Reponse generee",
                            show_mic_button=True,
                            mic_active=False
                        )
                        robot.display_text(html_content)
                    except UnicodeEncodeError:
                        safe_print("UnicodeEncodeError in display_text, using ASCII fallback for subtitle")
                        html_content = create_tablet_html(
                            title="Reponse",
                            message=transliterate_to_ascii(chat_response),
                            subtitle=transliterate_to_ascii(transcribed_text),
                            status="Reponse generee",
                            show_mic_button=True,
                            mic_active=False
                        )
                        try:
                            robot.display_text(html_content)
                        except Exception as e:
                            safe_print("Failed to display on tablet: {}", repr(e))
                    except Exception as e:
                        safe_print("Failed to display on tablet: {}", repr(e))
            
            # Pause avant la prochaine interaction
            time.sleep(2)
        
        # Fin de la boucle
        farewell_msg = "Merci d'avoir utilisé mes services. Au revoir !"
        if robot.tts:
            safe_say(robot, farewell_msg, language=ROBOT_CONFIG["language"])
        
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
        print("\n\nConversation interrompue par l'utilisateur")
        if robot.tts:
            safe_say(robot, "Au revoir !", language=ROBOT_CONFIG["language"])
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
            safe_say(robot, "Je suis désolé, une erreur s'est produite.", language=ROBOT_CONFIG["language"])
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
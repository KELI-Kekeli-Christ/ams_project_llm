# -*- coding: utf-8 -*-
"""
Gestionnaire de connexion et services pour le robot Pepper
"""

import os
import sys
import time
import json
import threading
import tempfile
from utils import safe_print, transliterate_to_ascii, post_file_with_retries
from config import CHOREGRAPHE_PATH, API_CONFIG


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
    
    def safe_say(self, text, language=None):
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
                    res = self.say(text, language=language)
                else:
                    res = self.say(text)
                # If robot.say returns a value, consider it; otherwise assume success
                safe_print("safe_say: called robot.say (tts exists={})", bool(self.tts))
                return True
            except UnicodeEncodeError:
                # fallback to ASCII-only
                safe_text = transliterate_to_ascii(text)
                try:
                    if language is not None:
                        self.say(safe_text, language=language)
                    else:
                        self.say(safe_text)
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
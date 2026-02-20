#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Robot Manager class for pepper_test module.
Handles connection and services for the Pepper robot.
"""

import os
import sys
import time
import threading

CHOREGRAPHE_PATH = "/opt/Softbank Robotics/Choregraphe Suite 2.5"


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


TEST_MESSAGE = "Bonjour, je suis connecté et prêt à vous aider. Ceci est un test de connexion."


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
            possible_urls = [
                "http://{}:8080/cameras/front".format(self.ip),
                "http://{}:8080/video".format(self.ip),
                "http://{}:8080/cameras/head".format(self.ip),
                "http://{}:9559/video".format(self.ip),
            ]
            self.camera_url = possible_urls[0]
            print("URL caméra configurée: {}".format(self.camera_url))
        except Exception as e:
            print("Service Video non disponible (normal pour robot virtuel): {}".format(e))
            self.video = None
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

        from utils.helpers import force_utf8
        text = force_utf8(text)

        try:
            if language:
                try:
                    self.tts.setLanguage(language)
                except Exception:
                    pass

            print("Le robot dit: '{}'".format(text))
            try:
                self.tts.say(text)
            except Exception:
                try:
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
            # Méthode 1: wakeUp (si disponible)
            try:
                self.tablet.wakeUp()
                print("Tablette activee via wakeUp()")
                time.sleep(0.3)
            except Exception as e:
                print("wakeUp() non disponible: {}".format(e))
            
            if show_blank:
                try:
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
        
        try:
            import sys
            
            # Normaliser le contenu HTML pour Python 2/3
            html_normalized = html_content
            if sys.version_info[0] < 3:
                if isinstance(html_normalized, str):
                    try:
                        html_normalized = html_normalized.decode('utf-8')
                    except UnicodeDecodeError:
                        html_normalized = html_normalized.decode('utf-8', 'ignore')
            
            # La tablette reçoit le contenu via ALTabletService (module intégré).
            # Ordre: data URL (pas de réseau) -> URL Flask (si tablette et PC sur même réseau) -> showWebview -> HTTP local.

            # Méthode 1: loadUrl avec data: (base64) - souvent le mieux rendu sur la tablette Pepper
            try:
                import base64
                if sys.version_info[0] < 3:
                    html_bytes = html_normalized.encode('utf-8', 'ignore')
                else:
                    html_bytes = html_normalized.encode('utf-8')
                html_encoded = base64.b64encode(html_bytes)
                if sys.version_info[0] >= 3:
                    html_encoded = html_encoded.decode('ascii')
                data_url = "data:text/html;charset=utf-8;base64,{}".format(html_encoded)
                print("Affichage tablette: loadUrl (data URL, {} octets)...".format(len(html_bytes)))
                self.tablet.loadUrl(data_url)
                print("Tablette affichee via loadUrl (data URL)")
                time.sleep(1.5)
                return True
            except Exception as e_data:
                print("loadUrl data a echoue: {}".format(e_data))

            # Méthode 2: loadUrl vers la page Flask (tablette et PC sur le même réseau)
            try:
                from utils.helpers import get_local_ip_for_robot
                local_ip = get_local_ip_for_robot(self.ip)
                http_url = "http://{}:5000/tablet".format(local_ip)
                print("Affichage tablette: loadUrl ({})...".format(http_url))
                self.tablet.loadUrl(http_url)
                print("Tablette affichee via URL Flask")
                time.sleep(1.5)
                return True
            except Exception as e_http:
                print("loadUrl Flask a echoue: {}".format(e_http))

            # Méthode 3: showWebview (HTML direct - peut rester blanc sur certains Pepper)
            try:
                if sys.version_info[0] < 3:
                    html_for_tablet = html_normalized.encode('utf-8', 'ignore')
                else:
                    html_for_tablet = html_normalized
                print("Affichage tablette: showWebview...")
                self.tablet.showWebview(html_for_tablet)
                print("Tablette affichee via showWebview")
                time.sleep(1)
                return True
            except Exception as e1:
                print("showWebview a echoue: {}".format(e1))

            # Méthode 4: serveur HTTP local (dernier recours)
            try:
                import codecs
                import tempfile
                import threading
                from utils.helpers import get_local_ip_for_robot
                local_ip = get_local_ip_for_robot(self.ip)
                temp_dir = tempfile.mkdtemp()
                html_file = os.path.join(temp_dir, "index.html")
                with codecs.open(html_file, 'w', encoding='utf-8') as f:
                    f.write(html_normalized)
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
                    print("Tentative loadUrl HTTP local: {}".format(http_url))
                    self.tablet.loadUrl(http_url)
                    print("Texte affiche sur la tablette via HTTP local!")
                    time.sleep(2)
                    return True
                finally:
                    os.chdir(old_dir)
            except Exception as e2:
                print("Toutes les methodes ont echoue: {}".format(e2))
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
            tuple: (image_bytes, width, height) or (None, None, None) on error
        """
        if not self.video:
            print("Service Video non disponible")
            return None, None, None
        
        try:
            video_client = self.video.subscribeCamera("python_client", 0, 2, 11, 5)
            time.sleep(0.5)
            image_container = self.video.getImageRemote(video_client)
            
            if image_container:
                image_data = image_container[6]
                image_width = image_container[0]
                image_height = image_container[1]
                self.video.unsubscribe(video_client)
                print("Image capturée: {}x{}".format(image_width, image_height))
                return image_data, image_width, image_height
            
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
        
        Returns:
            bool: True si le flux a démarré avec succès, False sinon
        """
        if not self.video:
            print("Service ALVideoDevice non disponible")
            return False
        
        try:
            print("Demarrage du flux video continu via ALVideoDevice...")
            
            def video_capture_worker():
                """Worker qui capture les images via ALVideoDevice et les envoie au service Flask"""
                try:
                    video_client = self.video.subscribeCamera("python_face_detection", 0, 2, 11, 5)
                    print("Abonnement a la camera reussi")
                    
                    frame_count = 0
                    while self.video_stream_active:
                        try:
                            image_container = self.video.getImageRemote(video_client)
                            
                            if image_container:
                                image_width = image_container[0]
                                image_height = image_container[1]
                                image_data = image_container[6]
                                
                                import tempfile
                                temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                                
                                try:
                                    from PIL import Image
                                    image_bytes = bytes(bytearray(image_data))
                                    im = Image.frombytes("RGB", (image_width, image_height), image_bytes)
                                    im.save(temp_file.name, "JPEG")
                                    temp_file.close()
                                    
                                    from api.flask_check import post_file_with_retries
                                    with open(temp_file.name, 'rb') as f:
                                        response = post_file_with_retries(
                                            "{}/face/detect".format(self._get_api_base_url()),
                                            files={"file": f},
                                        )

                                    # Every few frames, also try QR detection
                                    try:
                                        if frame_count % 5 == 0:
                                            with open(temp_file.name, 'rb') as qf:
                                                import requests
                                                qr_resp = requests.post(
                                                    "{}/scan_qr".format(self._get_api_base_url()),
                                                    files={"file": qf},
                                                    timeout=30
                                                )
                                            if qr_resp.ok:
                                                import json
                                                try:
                                                    qr_json = qr_resp.json()
                                                except Exception:
                                                    qr_json = json.loads(qr_resp.text)
                                                if qr_json and qr_json.get('success'):
                                                    with self.qr_lock:
                                                        self.latest_qr_result = qr_json
                                                    print("✅ QR code detecte en flux video: {}".format(qr_json.get('qr_id', 'N/A')))
                                    except Exception:
                                        pass
                                    
                                    try:
                                        os.unlink(temp_file.name)
                                    except:
                                        pass
                                    
                                    frame_count += 1
                                    if frame_count % 10 == 0:
                                        print("{} frames capturees et traitees".format(frame_count))
                                    
                                except Exception as e:
                                    print("Erreur lors du traitement de l'image: {}".format(e))
                                    try:
                                        os.unlink(temp_file.name)
                                    except:
                                        pass
                            
                            time.sleep(0.2)
                            
                        except Exception as e:
                            print("Erreur lors de la capture: {}".format(e))
                            time.sleep(1.0)
                    
                    self.video.unsubscribe(video_client)
                    print("Flux video arrete, desabonnement effectue")
                    
                except Exception as e:
                    print("Erreur dans le worker de capture video: {}".format(e))
                    import traceback
                    traceback.print_exc()
                    self.video_stream_active = False
            
            self.video_stream_active = True
            capture_thread = threading.Thread(target=video_capture_worker)
            capture_thread.setDaemon(True)
            capture_thread.start()
            
            print("✅ Flux vidéo continu démarré via ALVideoDevice")
            time.sleep(1.0)
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
            import requests
            response = requests.post(
                "{}/face/stream/stop".format(self._get_api_base_url()),
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
            
            video_client = self.video.subscribeCamera("python_face_recognition", 0, 2, 11, 5)
            
            try:
                for attempt in range(max_attempts):
                    image_container = self.video.getImageRemote(video_client)
                    
                    if image_container:
                        image_width = image_container[0]
                        image_height = image_container[1]
                        image_data = image_container[6]
                        
                        import tempfile
                        temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                        
                        try:
                            from PIL import Image
                            image_bytes = bytes(bytearray(image_data))
                            im = Image.frombytes("RGB", (image_width, image_height), image_bytes)
                            im.save(temp_file.name, "JPEG")
                            temp_file.close()
                            
                            from api.flask_check import post_file_with_retries
                            with open(temp_file.name, 'rb') as f:
                                response = post_file_with_retries(
                                    "{}/face/detect".format(self._get_api_base_url()),
                                    files={"file": f},
                                )
                            
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
                self.video.unsubscribe(video_client)
                
        except Exception as e:
            print("❌ Erreur lors de la reconnaissance faciale: {}".format(e))
            import traceback
            traceback.print_exc()
            return None
    
    def recognize_face_from_camera(self):
        """
        Capture une image depuis la caméra et essaie de reconnaître la personne
        
        Returns:
            str: Nom de la personne reconnue, ou None si non reconnue
        """
        try:
            if self.video_stream_active:
                return self.recognize_face_from_stream()
            
            image_data, image_width, image_height = self.capture_image_from_camera()

            if not image_data:
                print("Impossible de capturer l'image")
                return None

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
                temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                temp_file.write(image_data)
                temp_file.close()
            
            try:
                from api.flask_check import post_file_with_retries
                with open(temp_file.name, 'rb') as f:
                    response = post_file_with_retries(
                        "{}/face/detect".format(self._get_api_base_url()),
                        files={"file": f},
                    )
                
                if response.ok:
                    result = response.json()
                    recognized_persons = result.get("recognized_persons", [])
                    
                    if recognized_persons and len(recognized_persons) > 0:
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
            try:
                self.tablet.hideWebview()
                print("Vue web de la tablette cachée")
                return True
            except:
                pass
            
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
            last_recognized_name: Nom de la dernière personne reconnue
        
        Returns:
            str: Nom de la personne reconnue si différente, None sinon
        """
        if not self.video_stream_active:
            return None
        
        try:
            import requests
            response = requests.get(
                "{}/face/stream/detections".format(self._get_api_base_url()),
                timeout=2
            )
            
            if response.ok:
                result = response.json()
                if result.get("success") and result.get("streaming"):
                    recognized_persons = result.get("recognized_persons", [])
                    
                    if recognized_persons and len(recognized_persons) > 0:
                        current_name = recognized_persons[0]
                        if current_name != last_recognized_name:
                            return current_name
            return None
        except:
            return None
    
    def disconnect(self):
        """Déconnecte du robot"""
        if self.session:
            print("Déconnexion du robot...")
            self.session.close()
            print("Déconnecté")
            self.session = None
    
    def _get_api_base_url(self):
        """Get the API base URL from config"""
        from api.flask_check import API_CONFIG
        return API_CONFIG.get("base_url", "http://localhost:5000")


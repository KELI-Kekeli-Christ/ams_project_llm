# -*- coding: utf-8 -*-
"""
Gestionnaire de connexion au robot Pepper (NAOqi)
"""
import os
import sys
import time
import json
import threading
import requests
import tempfile
from config import API_CONFIG
from flask_utils import post_file_with_retries
from utils.helpers import get_local_ip_for_robot

# Import qi après setup_choreographe_environment (appelé depuis main)
from datetime import datetime
try:
    import qi
except ImportError as e:
    from config import CHOREGRAPHE_PATH
    print("ERROR: Cannot import 'qi' module")
    print("Make sure Choregraphe is installed at: {}".format(CHOREGRAPHE_PATH))
    print("Error: {}".format(e))
    sys.exit(1)


class RobotManager:
    """Gère la connexion et les services du robot Pepper"""

    def __init__(self, ip, port):
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
        try:
            self.tts = self.session.service("ALTextToSpeech")
            print("Service TextToSpeech initialisé")
        except Exception as e:
            print("Erreur avec le service TextToSpeech: {}".format(e))
            self.tts = None
        try:
            self.tablet = self.session.service("ALTabletService")
            print("Service Tablet initialisé")
        except Exception as e:
            print("Service Tablet non disponible (normal pour robot virtuel): {}".format(e))
            self.tablet = None
        try:
            self.audio_recorder = self.session.service("ALAudioRecorder")
            print("Service AudioRecorder initialisé")
        except Exception as e:
            print("Service AudioRecorder non disponible: {}".format(e))
            self.audio_recorder = None
        try:
            self.video = self.session.service("ALVideoDevice")
            print("Service Video initialisé")
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
            self.camera_url = "http://{}:8080/cameras/front".format(self.ip)
        return True

    def say(self, text, language=None):
        """Fait parler le robot"""
        if not self.tts:
            print("Erreur: Service TextToSpeech non disponible")
            return False
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
                if isinstance(text, bytes):
                    text = text.decode('utf-8', errors='ignore')
            if language:
                try:
                    self.tts.setLanguage(language)
                except Exception:
                    pass
            print("Le robot dit: '{}'".format(text))
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
        """S'assure que la tablette est allumée et active"""
        if not self.tablet:
            print("Service Tablet non disponible")
            return False
        try:
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
        """Affiche du contenu HTML sur la tablette"""
        if not self.tablet:
            print("Service Tablet non disponible")
            return False
        try:
            html_normalized = html_content
            if sys.version_info[0] < 3:
                if isinstance(html_normalized, str):
                    try:
                        html_normalized = html_normalized.decode('utf-8')
                    except UnicodeDecodeError:
                        html_normalized = html_normalized.decode('utf-8', 'ignore')
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
                self.tablet.loadUrl(data_url)
                print("Texte affiché sur la tablette via loadUrl (data URL)!")
                time.sleep(1)
                return True
            except Exception as e_data:
                print("loadUrl avec data URL a échoué: {}".format(e_data))
            try:
                if sys.version_info[0] < 3:
                    html_for_tablet = html_normalized.encode('utf-8', 'ignore')
                else:
                    html_for_tablet = html_normalized
                self.tablet.showWebview(html_for_tablet)
                print("Texte affiché sur la tablette via showWebview!")
                time.sleep(1)
                return True
            except Exception as e1:
                print("showWebview a échoué: {}".format(e1))
                try:
                    import codecs
                    import socket
                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        s.connect((self.ip, 80))
                        local_ip = s.getsockname()[0]
                        s.close()
                    except Exception:
                        local_ip = "127.0.0.1"
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
                        self.tablet.loadUrl(http_url)
                        print("Texte affiché via loadUrl (HTTP)!")
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
        """Capture une image depuis la caméra. Retourne (image_data, width, height) ou (None, None, None)"""
        if not self.video:
            print("Service Video non disponible")
            return None, None, None
        video_client = None
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
            if video_client is not None:
                try:
                    self.video.unsubscribe(video_client)
                except Exception:
                    pass
            return None, None, None

    def record_audio_from_pepper(self, max_duration=30, silence_timeout=3.0, should_stop_callback=None):
        """
        Enregistre l'audio depuis les micros de Pepper.
        Arrêt après silence_timeout secondes de silence ou quand should_stop_callback() retourne True.

        Args:
            max_duration: Durée max en secondes
            silence_timeout: Secondes de silence avant arrêt auto
            should_stop_callback: Fonction appelée régulièrement, si True -> arrêt

        Returns:
            str: Chemin du fichier local ou None
        """
        if not self.audio_recorder:
            print("Service AudioRecorder non disponible")
            return None
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            robot_hotel_dir = os.path.dirname(script_dir)
            recordings_dir = os.path.join(robot_hotel_dir, "recordings")
            if not os.path.exists(recordings_dir):
                os.makedirs(recordings_dir)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            local_file = os.path.join(recordings_dir, "pepper_{}.wav".format(timestamp))
            pepper_filename = "/home/nao/recordings/audio_{}.wav".format(timestamp)
            try:
                filesystem = self.session.service("ALFilesystem")
                filesystem.makeFolder("/home/nao/recordings/")
            except Exception:
                pass
            print("Enregistrement depuis le micro de Pepper... (clic STOP ou {}s max)".format(max_duration))
            self.audio_recorder.startMicrophonesRecording(
                pepper_filename, "wav", 16000, [0, 0, 1, 0]
            )
            start_time = time.time()
            check_interval = 0.3
            while True:
                time.sleep(check_interval)
                elapsed = time.time() - start_time
                if elapsed >= max_duration:
                    print("Arret apres {}s (duree max).".format(int(max_duration)))
                    break
                if should_stop_callback and should_stop_callback():
                    print("Arret demande (clic stop).")
                    break
            self.audio_recorder.stopMicrophonesRecording()
            time.sleep(0.5)
            downloaded = False
            try:
                filesystem = self.session.service("ALFilesystem")
                if filesystem.exists(pepper_filename):
                    file_content = filesystem.readFile(pepper_filename)
                    with open(local_file, "wb") as f:
                        f.write(file_content)
                    downloaded = True
                    try:
                        filesystem.remove(pepper_filename)
                    except Exception:
                        pass
            except Exception:
                pass
            if not downloaded:
                try:
                    import ftplib
                    ftp = ftplib.FTP()
                    ftp.connect(self.ip, 21, timeout=10)
                    ftp.login("nao", "nao")
                    ftp.cwd("recordings")
                    remote_name = "audio_{}.wav".format(timestamp)
                    with open(local_file, "wb") as f:
                        ftp.retrbinary("RETR " + remote_name, f.write)
                    try:
                        ftp.delete(remote_name)
                    except Exception:
                        pass
                    ftp.quit()
                    downloaded = True
                except Exception as e_ftp:
                    print("FTP fallback echoue: {}".format(e_ftp))
            if not downloaded:
                try:
                    import paramiko
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(self.ip, 22, username="nao", password="nao", timeout=10)
                    sftp = ssh.open_sftp()
                    sftp.get(pepper_filename, local_file)
                    sftp.close()
                    ssh.close()
                    downloaded = True
                except ImportError:
                    print("paramiko non installe: pip install paramiko")
                except Exception as e_ssh:
                    print("SSH fallback echoue: {}".format(e_ssh))
            if not downloaded:
                print("Fichier non cree sur Pepper")
                return None
            if os.path.getsize(local_file) < 5000:
                print("Fichier trop petit")
                return None
            print("Fichier telecharge: {}".format(local_file))
            return local_file
        except Exception as e:
            print("Erreur enregistrement Pepper: {}".format(e))
            import traceback
            traceback.print_exc()
            return None

    def _video_capture_worker(self):
        """Worker pour le flux vidéo continu"""
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
                        temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                        try:
                            from PIL import Image
                            image_bytes = bytes(bytearray(image_data))
                            im = Image.frombytes("RGB", (image_width, image_height), image_bytes)
                            im.save(temp_file.name, "JPEG")
                            temp_file.close()
                            with open(temp_file.name, 'rb') as f:
                                response = post_file_with_retries(
                                    "{}/face/detect".format(API_CONFIG["base_url"]),
                                    files={"file": f},
                                )
                            if frame_count % 5 == 0:
                                try:
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
                                            with self.qr_lock:
                                                self.latest_qr_result = qr_json
                                            print("✅ QR code detecte en flux video: {}".format(qr_json.get('qr_id', 'N/A')))
                                except Exception:
                                    pass
                            try:
                                os.unlink(temp_file.name)
                            except Exception:
                                pass
                            frame_count += 1
                            if frame_count % 10 == 0:
                                print("{} frames capturees et traitees".format(frame_count))
                        except Exception as e:
                            print("Erreur traitement image: {}".format(e))
                            try:
                                os.unlink(temp_file.name)
                            except Exception:
                                pass
                    time.sleep(0.2)
                except Exception as e:
                    print("Erreur capture: {}".format(e))
                    time.sleep(1.0)
            self.video.unsubscribe(video_client)
            print("Flux video arrete, desabonnement effectue")
        except Exception as e:
            print("Erreur worker video: {}".format(e))
            import traceback
            traceback.print_exc()
            self.video_stream_active = False

    def start_continuous_video_stream(self):
        """Démarre le flux vidéo continu pour détection faciale"""
        if not self.video:
            print("Service ALVideoDevice non disponible")
            return False
        try:
            print("Demarrage du flux video continu via ALVideoDevice...")
            self.video_stream_active = True
            capture_thread = threading.Thread(target=self._video_capture_worker)
            capture_thread.setDaemon(True)
            capture_thread.start()
            print("✅ Flux vidéo continu démarré")
            time.sleep(1.0)
            return True
        except Exception as e:
            print("❌ Erreur démarrage flux vidéo: {}".format(e))
            import traceback
            traceback.print_exc()
            self.video_stream_active = False
            return False

    def stop_continuous_video_stream(self):
        """Arrête le flux vidéo continu"""
        if not self.video_stream_active:
            return True
        try:
            print("Arret du flux video continu...")
            response = requests.post("{}/face/stream/stop".format(API_CONFIG["base_url"]), timeout=10)
            if response.ok and response.json().get("success"):
                self.video_stream_active = False
                print("✅ Flux vidéo arrêté")
                return True
            return False
        except Exception as e:
            print("⚠️ Erreur arrêt flux vidéo: {}".format(e))
            self.video_stream_active = False
            return False

    def recognize_face_from_stream(self, max_attempts=15, delay=0.3):
        """Reconnaît une personne depuis le flux vidéo"""
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
                        image_width, image_height = image_container[0], image_container[1]
                        image_data = image_container[6]
                        temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                        try:
                            from PIL import Image
                            image_bytes = bytes(bytearray(image_data))
                            im = Image.frombytes("RGB", (image_width, image_height), image_bytes)
                            im.save(temp_file.name, "JPEG")
                            temp_file.close()
                            with open(temp_file.name, 'rb') as f:
                                response = post_file_with_retries(
                                    "{}/face/detect".format(API_CONFIG["base_url"]),
                                    files={"file": f},
                                )
                            try:
                                os.unlink(temp_file.name)
                            except Exception:
                                pass
                            if response and response.ok:
                                result = response.json()
                                recognized_persons = result.get("recognized_persons", [])
                                if recognized_persons:
                                    print("✅ Personne reconnue: {}".format(recognized_persons[0]))
                                    return recognized_persons[0]
                            if attempt < max_attempts - 1:
                                time.sleep(delay)
                        except Exception as e:
                            print("⚠️ Erreur traitement: {}".format(e))
                            try:
                                os.unlink(temp_file.name)
                            except Exception:
                                pass
                            if attempt < max_attempts - 1:
                                time.sleep(delay)
                    else:
                        if attempt < max_attempts - 1:
                            time.sleep(delay)
                print("ℹ️ Aucune personne reconnue après {} tentatives".format(max_attempts))
                return None
            finally:
                self.video.unsubscribe(video_client)
        except Exception as e:
            print("❌ Erreur reconnaissance faciale: {}".format(e))
            import traceback
            traceback.print_exc()
            return None

    def recognize_face_from_camera(self):
        """Capture une image et reconnaît une personne (fallback)"""
        try:
            if self.video_stream_active:
                return self.recognize_face_from_stream()
            image_data, image_width, image_height = self.capture_image_from_camera()
            if not image_data:
                print("Impossible de capturer l'image")
                return None
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
                with open(temp_file.name, 'rb') as f:
                    response = post_file_with_retries(
                        "{}/face/detect".format(API_CONFIG["base_url"]),
                        files={"file": f},
                    )
                if response and response.ok:
                    result = response.json()
                    recognized_persons = result.get("recognized_persons", [])
                    if recognized_persons:
                        return recognized_persons[0]
                return None
            finally:
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
        except Exception as e:
            print("Erreur reconnaissance faciale: {}".format(e))
            return None

    def hide_tablet_webview(self):
        """Cache la vue web de la tablette"""
        if not self.tablet:
            return False
        try:
            try:
                self.tablet.hideWebview()
                print("Vue web de la tablette cachée")
                return True
            except Exception:
                pass
            try:
                self.tablet.loadUrl("about:blank")
                print("Vue web de la tablette cachée (page blanche)")
                return True
            except Exception:
                pass
            return False
        except Exception as e:
            print("Erreur masquage vue web: {}".format(e))
            return False

    def check_for_new_face(self, last_recognized_name=None):
        """Vérifie s'il y a un nouveau visage détecté"""
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
                    if recognized_persons:
                        current_name = recognized_persons[0]
                        if current_name != last_recognized_name:
                            return current_name
            return None
        except Exception:
            return None

    def disconnect(self):
        """Déconnecte du robot"""
        if self.session:
            print("Déconnexion du robot...")
            self.session.close()
            print("Déconnecté")
            self.session = None

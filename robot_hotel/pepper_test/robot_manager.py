# -*- coding: utf-8 -*-
"""
Gestionnaire de connexion au robot Pepper (NAOqi)
"""
import os
import sys
import time
import json
import logging
import threading
import requests
import tempfile
from config import API_CONFIG
from flask_utils import post_file_with_retries
from utils.helpers import get_local_ip_for_robot

# Supprimer le warning "No handlers could be found for logger 'paramiko.transport'" (Python 2)
logging.getLogger("paramiko").addHandler(logging.NullHandler())
logging.getLogger("paramiko.transport").addHandler(logging.NullHandler())

# Import qi après setup_choreographe_environment (appelé depuis main)
from datetime import datetime
import wave
try:
    import numpy as np
except ImportError:
    np = None
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
        self._asr_vocabulary_loaded = False  # True après le 1er setVocabulary réussi

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
        # ALSpeechRecognition pour le wake word (micros Pepper)
        try:
            self.speech_reco = self.session.service("ALSpeechRecognition")
            self.memory = self.session.service("ALMemory")
            print("Service SpeechRecognition initialise")
        except Exception as e:
            print("Service SpeechRecognition non disponible: {}".format(e))
            self.speech_reco = None
            self.memory = None
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
            for attempt in range(2):
                try:
                    self.tts.say(text)
                    return True
                except Exception as e:
                    print("Erreur TTS (tentative {}): {}".format(attempt + 1, e))
                    if self._is_socket_error(e) and attempt == 0:
                        if self.reconnect():
                            continue
                    return False
            return False
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

    def load_tablet_url(self, url):
        """Charge une URL sur la tablette (ex: page « Appel en cours »)."""
        if not self.tablet:
            return False
        try:
            self.tablet.loadUrl(url)
            time.sleep(0.5)
            return True
        except Exception as e:
            print("Erreur loadUrl: {}".format(e))
            return False

    def _is_socket_error(self, exc):
        """Retourne True si l'exception indique une déconnexion qi."""
        msg = str(exc).lower()
        return "socket is not connected" in msg or "connection" in msg

    def reconnect(self):
        """Tente de se reconnecter à Pepper et réinitialise les services."""
        print("[Reconnexion] Tentative de reconnexion au robot {}...".format(self.ip))
        try:
            if self.session:
                try:
                    self.session.close()
                except Exception:
                    pass
            self.session = None
            self.tts = None
            self.tablet = None
            self.audio_recorder = None
            self.speech_reco = None
            self.memory = None
            time.sleep(1.0)
            if self.connect():
                self.initialize_services()
                print("[Reconnexion] Reconnecte avec succes.")
                return True
        except Exception as e:
            print("[Reconnexion] Echec: {}".format(e))
        return False

    def display_text(self, html_content):
        """Affiche du contenu HTML sur la tablette via data URL (base64).
        Si le socket est déconnecté, tente une reconnexion unique.
        Le fallback serveur HTTP a été supprimé (causait [Errno 98] Address already in use).
        """
        if not self.tablet:
            print("Service Tablet non disponible")
            return False
        try:
            # Normaliser en unicode
            html_normalized = html_content
            if sys.version_info[0] < 3:
                if isinstance(html_normalized, str):
                    try:
                        html_normalized = html_normalized.decode('utf-8')
                    except UnicodeDecodeError:
                        html_normalized = html_normalized.decode('utf-8', 'ignore')

            import base64
            if sys.version_info[0] < 3:
                html_bytes = html_normalized.encode('utf-8', 'ignore')
            else:
                html_bytes = html_normalized.encode('utf-8')
            html_encoded = base64.b64encode(html_bytes)
            if sys.version_info[0] >= 3:
                html_encoded = html_encoded.decode('ascii')
            data_url = "data:text/html;charset=utf-8;base64,{}".format(html_encoded)

            # ── Méthode 1 : loadUrl avec data URL ────────────────────────────
            for attempt in range(2):
                try:
                    self.tablet.loadUrl(data_url)
                    time.sleep(0.8)
                    return True
                except Exception as e:
                    print("loadUrl data URL echoue (tentative {}): {}".format(attempt + 1, e))
                    if self._is_socket_error(e) and attempt == 0:
                        if self.reconnect():
                            continue  # réessayer après reconnexion
                    break

            # ── Méthode 2 : showWebview ───────────────────────────────────────
            try:
                if sys.version_info[0] < 3:
                    self.tablet.showWebview(html_normalized.encode('utf-8', 'ignore'))
                else:
                    self.tablet.showWebview(html_normalized)
                time.sleep(0.8)
                return True
            except Exception as e2:
                print("showWebview echoue: {}".format(e2))

            print("Affichage tablette impossible (socket deconnecte?).")
            return False

        except Exception as e:
            print("Erreur display_text: {}".format(e))
            return False
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

    def _rms_from_wav(self, path):
        """Retourne le niveau RMS du fichier WAV (silence si bas)."""
        if not os.path.exists(path) or os.path.getsize(path) < 100:
            return 0.0
        try:
            w = wave.open(path, "rb")
            try:
                n = w.getnframes()
                if n == 0:
                    return 0.0
                buf = w.readframes(n)
            finally:
                w.close()
            if np is not None:
                samples = np.frombuffer(buf, dtype=np.int16)
                return float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))
            total = 0
            n = len(buf) // 2
            for i in range(n):
                s = int.from_bytes(buf[i*2:(i*2)+2], "little", signed=True)
                total += s * s
            return (total / n) ** 0.5 if n else 0.0
        except Exception:
            return 0.0

    def _download_pepper_file(self, pepper_filename, local_path):
        """Télécharge un fichier enregistré depuis Pepper vers un chemin local. Retourne True si ok.
        Cache la méthode qui fonctionne pour éviter les timeouts des méthodes lentes à chaque chunk."""

        # 1. ALFilesystem (le plus rapide, pas de timeout réseau)
        if getattr(self, '_dl_method', None) != 'sftp':
            try:
                filesystem = self.session.service("ALFilesystem")
                if filesystem.exists(pepper_filename):
                    file_content = filesystem.readFile(pepper_filename)
                    with open(local_path, "wb") as f:
                        f.write(file_content)
                    try:
                        filesystem.remove(pepper_filename)
                    except Exception:
                        pass
                    self._dl_method = 'alfs'
                    return True
            except Exception:
                pass

        # 2. FTP (timeout réduit à 3s)
        if getattr(self, '_dl_method', None) in (None, 'ftp'):
            try:
                import ftplib
                ftp = ftplib.FTP()
                ftp.connect(self.ip, 21, timeout=3)
                ftp.login("nao", "nao")
                ftp.cwd("recordings")
                remote_name = os.path.basename(pepper_filename)
                with open(local_path, "wb") as f:
                    ftp.retrbinary("RETR " + remote_name, f.write)
                try:
                    ftp.delete(remote_name)
                except Exception:
                    pass
                ftp.quit()
                self._dl_method = 'ftp'
                return True
            except Exception:
                pass

        # 3. SFTP via paramiko (timeout réduit à 3s)
        try:
            import warnings
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            import paramiko
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.ip, 22, username="nao", password="nao", timeout=3)
            sftp = ssh.open_sftp()
            sftp.get(pepper_filename, local_path)
            sftp.close()
            ssh.close()
            self._dl_method = 'sftp'
            return True
        except Exception:
            return False

    def record_audio_from_pepper(self, max_duration=10, silence_timeout=2.0, should_stop_callback=None):
        """
        Enregistre l'audio depuis les micros de Pepper.
        Même principe que le PC : arrêt après silence_timeout secondes de silence (détection sur le micro Pepper),
        ou quand should_stop_callback() retourne True.

        Args:
            max_duration: Durée max en secondes
            silence_timeout: Secondes de silence avant arrêt auto (ex. 2.0)
            should_stop_callback: Fonction appelée régulièrement, si True -> arrêt

        Returns:
            str: Chemin du fichier local ou None
        """
        if not self.audio_recorder:
            print("Service AudioRecorder non disponible")
            return None
        CHUNK_DURATION = 1.0
        SILENCE_RMS_THRESHOLD = 100  # Abaissé : 600 coupait trop tôt (parole douce < 600)
        silence_chunks_needed = max(1, int(round(silence_timeout / CHUNK_DURATION)))
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            robot_hotel_dir = os.path.dirname(script_dir)
            recordings_dir = os.path.join(robot_hotel_dir, "recordings")
            if not os.path.exists(recordings_dir):
                os.makedirs(recordings_dir)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            local_file = os.path.join(recordings_dir, "pepper_{}.wav".format(timestamp))
            try:
                filesystem = self.session.service("ALFilesystem")
                filesystem.makeFolder("/home/nao/recordings/")
            except Exception:
                pass
            try:
                self.audio_recorder.stopMicrophonesRecording()
                time.sleep(0.3)
            except Exception:
                pass
            print("Enregistrement depuis le micro de Pepper... 2 s de silence = envoi (ou {}s max)".format(max_duration))
            chunk_paths = []
            silence_count = 0
            start_time = time.time()
            chunk_index = 0
            while time.time() - start_time < max_duration:
                if should_stop_callback and should_stop_callback():
                    print("Arret demande (clic stop).")
                    break
                pepper_filename = "/home/nao/recordings/audio_{}_{}.wav".format(timestamp, chunk_index)
                try:
                    self.audio_recorder.startMicrophonesRecording(
                        pepper_filename, "wav", 16000, [0, 0, 1, 0]
                    )
                except Exception as e:
                    if "Already recording" in str(e):
                        try:
                            self.audio_recorder.stopMicrophonesRecording()
                            time.sleep(0.2)
                        except Exception:
                            pass
                        continue
                    raise
                time.sleep(CHUNK_DURATION)
                try:
                    self.audio_recorder.stopMicrophonesRecording()
                except Exception:
                    pass
                time.sleep(0.3)
                chunk_local = os.path.join(recordings_dir, "pepper_chunk_{}_{}.wav".format(timestamp, chunk_index))
                if not self._download_pepper_file(pepper_filename, chunk_local):
                    chunk_index += 1
                    continue
                if os.path.getsize(chunk_local) < 1000:
                    chunk_index += 1
                    try:
                        os.remove(chunk_local)
                    except Exception:
                        pass
                    continue
                rms = self._rms_from_wav(chunk_local)
                if rms < SILENCE_RMS_THRESHOLD:
                    silence_count += 1
                    if silence_count >= silence_chunks_needed:
                        try:
                            os.remove(chunk_local)
                        except Exception:
                            pass
                        break
                else:
                    silence_count = 0
                chunk_paths.append(chunk_local)
                chunk_index += 1
            if not chunk_paths:
                return None
            ref = wave.open(chunk_paths[0], "rb")
            try:
                nchannels, sampwidth, framerate = ref.getnchannels(), ref.getsampwidth(), ref.getframerate()
            finally:
                ref.close()
            out = wave.open(local_file, "wb")
            try:
                out.setnchannels(nchannels)
                out.setsampwidth(sampwidth)
                out.setframerate(framerate)
                for p in chunk_paths:
                    try:
                        w = wave.open(p, "rb")
                        try:
                            out.writeframes(w.readframes(w.getnframes()))
                        finally:
                            w.close()
                    except Exception:
                        pass
                    try:
                        os.remove(p)
                    except Exception:
                        pass
            finally:
                out.close()
            if os.path.getsize(local_file) < 5000:
                return None
            print("Fichier telecharge: {}".format(local_file))
            return local_file
        except Exception as e:
            print("Erreur enregistrement Pepper: {}".format(e))
            import traceback
            traceback.print_exc()
            self.stop_pepper_microphones()
            return None

    def stop_pepper_microphones(self):
        """Arrête l'enregistrement micro sur Pepper (évite « Already recording » au prochain démarrage)."""
        if not self.audio_recorder:
            return
        try:
            self.audio_recorder.stopMicrophonesRecording()
        except Exception:
            pass

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
                                            files={"file": ("frame.jpg", qf)},
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

    # ─── Wake word via ALSpeechRecognition (micros Pepper) ───────────────────

    def setup_wake_word_recognition(self, vocabulary=None, language="French"):
        """Configure ALSpeechRecognition pour écouter les wake words via les micros de Pepper.
        vocabulary : liste de mots/phrases à reconnaître (défaut: wake words standards)
        language   : langue NAOqi (ex. "French", "English")

        Stratégie robuste contre l'erreur Nuance "modifiable_grammar already exists" :
        - 1er appel  : setup complet (langue + vocabulaire + subscribe)
        - Rappels    : pause → éventuellement setVocabulary → unpause → subscribe
          Si setVocabulary échoue avec "modifiable_grammar" (grammaire Nuance déjà chargée),
          on saute setVocabulary : la grammaire du 1er appel est encore valide.
        """
        if not self.speech_reco or not self.memory:
            print("ALSpeechRecognition non disponible, wake word PC utilise en fallback")
            return False
        if vocabulary is None:
            vocabulary = [
                "bonjour", "hey pepper", "ok pepper", "pepper",
                "hello", "excuse moi", "s il vous plait",
            ]
        try:
            # 1. Mettre en pause (toujours en premier)
            try:
                self.speech_reco.pause(True)
            except Exception:
                pass

            # 2. Désabonner pour libérer l'abonnement actif (erreur ignorée si pas abonné)
            try:
                self.speech_reco.unsubscribe("wake_word_listener")
            except Exception:
                pass

            # 3. Langue (une seule fois suffit, mais ne coûte rien de le refaire)
            try:
                self.speech_reco.setLanguage(language)
            except Exception as e:
                print("Langue '{}' non dispo: {}".format(language, e))

            # 4. Charger le vocabulaire
            #    La grammaire Nuance "modifiable_grammar" persiste sur le robot même entre
            #    deux redémarrages du script. On tente setVocabulary dans tous les cas,
            #    mais on accepte l'erreur "already exists" : le vocabulaire est déjà là.
            try:
                self.speech_reco.setVocabulary(vocabulary, False)
                self._asr_vocabulary_loaded = True
                print("Vocabulaire ASR charge: {}".format(vocabulary))
            except Exception as vocab_err:
                err_str = str(vocab_err)
                if "modifiable_grammar" in err_str or "already exists" in err_str:
                    # Grammaire déjà présente (session précédente ou appel précédent) — c'est OK
                    self._asr_vocabulary_loaded = True
                    print("Vocabulaire ASR deja charge (grammaire Nuance persistante) — OK")
                else:
                    raise  # autre erreur inattendue, on laisse remonter

            # 5. Reprendre le moteur
            try:
                self.speech_reco.pause(False)
            except Exception:
                pass

            # 6. S'abonner
            self.speech_reco.subscribe("wake_word_listener")

            # 7. Remettre la clé mémoire à zéro
            try:
                self.memory.insertData("WordRecognized", [])
            except Exception:
                pass

            print("ALSpeechRecognition active (vocab: {})".format(vocabulary))
            return True
        except Exception as e:
            try:
                self.speech_reco.pause(False)
            except Exception:
                pass
            print("Erreur setup ALSpeechRecognition: {}".format(e))
            import traceback
            traceback.print_exc()
            return False

    def check_pepper_wake_word(self, confidence_threshold=0.25):
        """Lit ALMemory 'WordRecognized'. Retourne True si un wake word a été reconnu
        avec une confiance >= confidence_threshold, False sinon."""
        if not self.memory:
            return False
        try:
            val = self.memory.getData("WordRecognized")
            # val est de la forme [word, confidence, ...]
            if not val or len(val) < 2:
                return False
            word = val[0] if val[0] else ""
            confidence = float(val[1]) if val[1] else 0.0
            if word and confidence >= confidence_threshold:
                print("[WakeWord Pepper] '{}' confidence={:.2f}".format(word, confidence))
                # Remettre à zéro pour ne pas re-détecter
                try:
                    self.memory.insertData("WordRecognized", [])
                except Exception:
                    pass
                return True
        except Exception:
            pass
        return False

    def stop_wake_word_recognition(self):
        """Désabonne ALSpeechRecognition."""
        if not self.speech_reco:
            return
        try:
            self.speech_reco.unsubscribe("wake_word_listener")
            print("ALSpeechRecognition désabonné")
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────

    def disconnect(self):
        """Déconnecte du robot"""
        self._asr_vocabulary_loaded = False  # reset pour la prochaine connexion
        if self.session:
            print("Déconnexion du robot...")
            self.session.close()
            print("Déconnecté")
            self.session = None

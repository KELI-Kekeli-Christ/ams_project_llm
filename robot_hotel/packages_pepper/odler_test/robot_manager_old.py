#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Gestionnaire de robot Pepper (connexion, services, vidéo, tablette, etc.).
"""

import os
import time
import json
import requests
import threading
from datetime import datetime

from pepper_config import API_CONFIG, CHOREGRAPHE_PATH
from robot_hotel.pepper_test.utils_old import post_file_with_retries

# Import qi module (NOT naoqi!)
try:
    import qi
except ImportError as e:
    print("ERROR: Cannot import 'qi' module")
    print("Make sure Choregraphe is installed at: {}".format(CHOREGRAPHE_PATH))
    print("Error: {}".format(e))
    import sys
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
        self.audio_device = None
        self.speech_recognition = None
        self.video = None
        self.camera_url = None
        self.video_stream_active = False
        self.latest_qr_result = None
        self.wake_word_active = False
        self.wake_word_detected = False
        self.qr_lock = threading.Lock()
        self.connection_string = "tcp://{}:{}".format(ip, port)
        
        # Variables pour l'enregistrement audio
        self.is_recording = False
        self.audio_buffer = []
        self.recording_start_time = None
        self.silence_detected = False
        self.silence_start_time = None
        
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
            
        # Initialiser le service ALAudioDevice (pour le streaming audio)
        try:
            self.audio_device = self.session.service("ALAudioDevice")
            print("Service ALAudioDevice initialisé")
        except Exception as e:
            print("Service ALAudioDevice non disponible: {}".format(e))
            self.audio_device = None
        
        # Initialiser le service SpeechRecognition (pour le wake word)
        try:
            self.speech_recognition = self.session.service("ALSpeechRecognition")
            print("Service SpeechRecognition initialisé")
        except Exception as e:
            print("Service SpeechRecognition non disponible: {}".format(e))
            self.speech_recognition = None
        
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
            print("Service Video non disponible: {}".format(e))
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
            language: Langue (optionnel)
        """
        if not self.tts:
            print("Erreur: Service TextToSpeech non disponible")
            return False

        try:
            try:
                unicode
                is_py2 = True
            except NameError:
                is_py2 = False

            if is_py2:
                if isinstance(text, unicode):
                    text = text.encode("utf-8")
                elif isinstance(text, str):
                    try:
                        text = text.decode("utf-8").encode("utf-8")
                    except Exception:
                        pass
            else:
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

            print("Le robot dit: '{}'".format(text))
            try:
                self.tts.say(text)
            except Exception:
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
            show_blank: Si True, affiche une page blanche
        """
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
            import base64
            
            html_normalized = html_content
            if sys.version_info[0] < 3:
                if isinstance(html_normalized, str):
                    try:
                        html_normalized = html_normalized.decode('utf-8')
                    except UnicodeDecodeError:
                        html_normalized = html_normalized.decode('utf-8', 'ignore')
            
            try:
                if sys.version_info[0] < 3:
                    html_bytes = html_normalized.encode('utf-8', 'ignore')
                else:
                    html_bytes = html_normalized.encode('utf-8')
                
                html_encoded = base64.b64encode(html_bytes)
                if sys.version_info[0] >= 3:
                    html_encoded = html_encoded.decode('ascii')
                
                data_url = "data:text/html;charset=utf-8;base64,{}".format(html_encoded)
                self.tablet.loadUrl(data_url)
                print("Texte affiché sur la tablette via loadUrl!")
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
                    return False
                    
        except Exception as e:
            print("Erreur lors de l'affichage sur la tablette: {}".format(e))
            return False
    
    def record_audio_from_pepper(self, duration=10):
        """
        Enregistre l'audio directement depuis les micros de Pepper
        
        Args:
            duration: Durée d'enregistrement en secondes
        
        Returns:
            str: Chemin du fichier audio enregistré, ou None en cas d'erreur
        """
        if not self.audio_recorder:
            print("❌ Service AudioRecorder non disponible")
            return None
        
        try:
            print("🎤 Enregistrement audio depuis les micros de Pepper...")
            
            # Créer le dossier recordings s'il n'existe pas
            script_dir = os.path.dirname(os.path.abspath(__file__))
            robot_hotel_dir = os.path.dirname(script_dir)
            recordings_dir = os.path.join(robot_hotel_dir, "recordings")
            if not os.path.exists(recordings_dir):
                os.makedirs(recordings_dir)
            
            # Nom du fichier avec timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            local_file = os.path.join(recordings_dir, f"pepper_{timestamp}.wav")
            
            # Configuration de l'enregistrement sur Pepper
            pepper_filename = f"/home/nao/recordings/audio_{timestamp}.wav"
            
            # S'assurer que le dossier existe sur Pepper
            try:
                filesystem = self.session.service("ALFilesystem")
                filesystem.makeFolder("/home/nao/recordings/")
            except Exception as e:
                print("⚠️ Impossible de créer le dossier sur Pepper: {}".format(e))
            
            print(f"📝 Enregistrement sur Pepper: {pepper_filename}")
            print(f"⏱️ Durée: {duration} secondes")
            
            # Démarrer l'enregistrement
            # canaux: [gauche, droit, avant, arrière] - 1 = activé, 0 = désactivé
            # On active seulement le micro avant pour une meilleure qualité
            self.audio_recorder.startMicrophonesRecording(
                pepper_filename,  # Nom du fichier
                "wav",            # Format
                16000,            # Fréquence d'échantillonnage (16kHz)
                [0, 0, 1, 0]      # Canaux [gauche, droit, avant, arrière]
            )
            
            print("✅ Enregistrement démarré sur Pepper")
            
            # Attendre la durée spécifiée
            for i in range(duration):
                time.sleep(1)
                if i % 2 == 0:
                    print(f"⏳ Enregistrement... {duration - i - 1}s restantes")
            
            # Arrêter l'enregistrement
            self.audio_recorder.stopMicrophonesRecording()
            print("✅ Enregistrement terminé sur Pepper")
            
            # Télécharger le fichier depuis Pepper vers le PC
            print("📥 Téléchargement du fichier audio...")
            filesystem = self.session.service("ALFilesystem")
            
            # Vérifier que le fichier existe
            if not filesystem.exists(pepper_filename):
                print("❌ Le fichier n'a pas été créé sur Pepper")
                return None
            
            # Lire le fichier depuis Pepper
            file_content = filesystem.readFile(pepper_filename)
            
            # Écrire le fichier localement
            with open(local_file, "wb") as f:
                f.write(file_content)
            
            # Supprimer le fichier temporaire sur Pepper
            try:
                filesystem.remove(pepper_filename)
                print("🧹 Fichier temporaire supprimé sur Pepper")
            except Exception as e:
                print("⚠️ Impossible de supprimer le fichier sur Pepper: {}".format(e))
            
            # Vérifier la taille du fichier
            file_size = os.path.getsize(local_file)
            print(f"📊 Taille du fichier: {file_size} bytes")
            
            if file_size < 5000:
                print("⚠️ Fichier trop petit - probablement aucun son détecté")
                return None
            
            print(f"✅ Fichier audio téléchargé: {local_file}")
            return local_file
            
        except Exception as e:
            print(f"❌ Erreur lors de l'enregistrement audio depuis Pepper: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def record_audio_from_pepper_with_vad(self, max_duration=30, silence_timeout=2.0, min_duration=1.0):
        """
        Enregistre l'audio depuis Pepper avec détection de silence (VAD)
        
        Args:
            max_duration: Durée maximale d'enregistrement en secondes
            silence_timeout: Temps de silence avant arrêt en secondes
            min_duration: Durée minimale d'enregistrement en secondes
        
        Returns:
            str: Chemin du fichier audio enregistré, ou None en cas d'erreur
        """
        if not self.audio_recorder:
            print("❌ Service AudioRecorder non disponible")
            return None
        
        if not self.audio_device:
            print("❌ Service ALAudioDevice non disponible pour la détection VAD")
            return self.record_audio_from_pepper(duration=10)  # Fallback
        
        try:
            print("🎤 Enregistrement avec VAD depuis les micros de Pepper...")
            print(f"   Paramètres: max={max_duration}s, silence={silence_timeout}s, min={min_duration}s")
            
            # Créer le dossier recordings
            script_dir = os.path.dirname(os.path.abspath(__file__))
            robot_hotel_dir = os.path.dirname(script_dir)
            recordings_dir = os.path.join(robot_hotel_dir, "recordings")
            if not os.path.exists(recordings_dir):
                os.makedirs(recordings_dir)
            
            # Nom du fichier avec timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            local_file = os.path.join(recordings_dir, f"pepper_vad_{timestamp}.wav")
            
            # Fichier temporaire sur Pepper
            pepper_filename = f"/home/nao/recordings/audio_vad_{timestamp}.wav"
            
            # S'assurer que le dossier existe
            try:
                filesystem = self.session.service("ALFilesystem")
                filesystem.makeFolder("/home/nao/recordings/")
            except:
                pass
            
            # Variable pour le callback de niveau audio
            self.is_recording = False
            self.audio_buffer = []
            self.recording_start_time = None
            self.silence_detected = False
            self.silence_start_time = None
            
            # Configuration du callback pour la détection de niveau audio
            def audio_callback(data, channels, rate):
                """Callback appelé pour chaque échantillon audio"""
                if not self.is_recording:
                    return
                
                # Calculer le niveau audio approximatif (RMS simplifié)
                import numpy as np
                audio_array = np.frombuffer(data, dtype=np.int16)
                if len(audio_array) > 0:
                    rms = np.sqrt(np.mean(audio_array**2))
                    # Convertir en dB (approximatif)
                    if rms > 0:
                        db = 20 * np.log10(rms / 32768)  # Normalisé pour 16-bit
                    else:
                        db = -100
                    
                    current_time = time.time()
                    
                    # Détection de début de parole
                    if not self.silence_detected:
                        if db > -40:  # Seuil de détection de parole
                            self.silence_detected = True
                            self.silence_start_time = None
                            print(f"🔊 Parole détectée (niveau: {db:.1f} dB)")
                    
                    # Détection de silence
                    elif self.silence_detected:
                        if db < -45:  # Seuil de silence
                            if self.silence_start_time is None:
                                self.silence_start_time = current_time
                            elif current_time - self.silence_start_time > silence_timeout:
                                print(f"🔇 Silence détecté pendant {silence_timeout}s")
                                self.is_recording = False
                        else:
                            self.silence_start_time = None
            
            # S'abonner au flux audio
            print("🔄 Configuration du callback audio...")
            self.audio_device.setClientPreferences("PythonVAD", 16000, 3, 0)
            self.audio_device.subscribe("PythonVAD")
            
            # Démarrer l'enregistrement sur Pepper
            print("▶️ Démarrage de l'enregistrement sur Pepper...")
            self.audio_recorder.startMicrophonesRecording(
                pepper_filename,
                "wav",
                16000,
                [0, 0, 1, 0]  # Seulement micro avant
            )
            
            self.is_recording = True
            self.recording_start_time = time.time()
            self.silence_detected = False
            
            print("✅ Enregistrement démarré avec VAD - Parlez maintenant...")
            
            # Attendre la fin de l'enregistrement
            while self.is_recording:
                elapsed = time.time() - self.recording_start_time
                if elapsed > max_duration:
                    print(f"⏱️ Durée maximale atteinte ({max_duration}s)")
                    self.is_recording = False
                    break
                
                # Afficher le statut toutes les secondes
                if int(elapsed) % 2 == 0 and int(elapsed) > 0:
                    print(f"⏳ Enregistrement en cours... {elapsed:.1f}s")
                
                time.sleep(0.1)
            
            # Arrêter l'enregistrement
            print("🛑 Arrêt de l'enregistrement...")
            self.audio_recorder.stopMicrophonesRecording()
            
            # Se désabonner du flux audio
            self.audio_device.unsubscribe("PythonVAD")
            
            # Vérifier la durée
            elapsed = time.time() - self.recording_start_time
            if elapsed < min_duration:
                print(f"⚠️ Enregistrement trop court ({elapsed:.1f}s < {min_duration}s)")
                return None
            
            # Télécharger le fichier
            print("📥 Téléchargement du fichier audio...")
            filesystem = self.session.service("ALFilesystem")
            
            if not filesystem.exists(pepper_filename):
                print("❌ Le fichier n'existe pas sur Pepper")
                return None
            
            file_content = filesystem.readFile(pepper_filename)
            
            with open(local_file, "wb") as f:
                f.write(file_content)
            
            # Nettoyer
            try:
                filesystem.remove(pepper_filename)
            except:
                pass
            
            file_size = os.path.getsize(local_file)
            print(f"📊 Taille du fichier: {file_size} bytes")
            
            if file_size < 5000:
                print("⚠️ Fichier trop petit")
                return None
            
            print(f"✅ Enregistrement VAD terminé: {local_file}")
            print(f"⏱️ Durée totale: {elapsed:.1f}s")
            
            return local_file
            
        except Exception as e:
            print(f"❌ Erreur lors de l'enregistrement VAD: {e}")
            import traceback
            traceback.print_exc()
            
            # Nettoyer
            try:
                self.audio_recorder.stopMicrophonesRecording()
            except:
                pass
            try:
                self.audio_device.unsubscribe("PythonVAD")
            except:
                pass
            
            return None
    
    def capture_image_from_camera(self):
        """
        Capture une image depuis la caméra du robot Pepper

        Returns:
            tuple: (image_bytes, width, height) or (None, None, None)
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
            
            self.video.unsubscribe(video_client)
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
        """
        if not self.video:
            print("Service ALVideoDevice non disponible")
            return False
        
        try:
            print("Demarrage du flux video continu...")
            
            def video_capture_worker():
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
                                    
                                    with open(temp_file.name, 'rb') as f:
                                        post_file_with_retries(
                                            "{}/face/detect".format(API_CONFIG["base_url"]),
                                            files={"file": f},
                                        )

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
                                                except:
                                                    qr_json = json.loads(qr_resp.text)
                                                if qr_json and qr_json.get('success'):
                                                    with self.qr_lock:
                                                        self.latest_qr_result = qr_json
                                                    print("✅ QR code detecte: {}".format(qr_json.get('qr_id', 'N/A')))
                                    except:
                                        pass
                                    
                                    try:
                                        os.unlink(temp_file.name)
                                    except:
                                        pass
                                    
                                    frame_count += 1
                                    if frame_count % 10 == 0:
                                        print("{} frames capturees".format(frame_count))
                                    
                                except Exception as e:
                                    print("Erreur traitement image: {}".format(e))
                                    try:
                                        os.unlink(temp_file.name)
                                    except:
                                        pass
                            
                            time.sleep(0.2)
                            
                        except Exception as e:
                            print("Erreur capture: {}".format(e))
                            time.sleep(1.0)
                    
                    self.video.unsubscribe(video_client)
                    print("Flux video arrete")
                    
                except Exception as e:
                    print("Erreur worker video: {}".format(e))
                    self.video_stream_active = False
            
            self.video_stream_active = True
            capture_thread = threading.Thread(target=video_capture_worker)
            capture_thread.setDaemon(True)
            capture_thread.start()
            
            print("✅ Flux vidéo continu démarré")
            time.sleep(1.0)
            return True
            
        except Exception as e:
            print("❌ Erreur démarrage flux vidéo: {}".format(e))
            self.video_stream_active = False
            return False
    
    def stop_continuous_video_stream(self):
        """
        Arrête le flux vidéo continu
        """
        if not self.video_stream_active:
            return True
        
        try:
            print("Arret du flux video continu...")
            self.video_stream_active = False
            print("✅ Flux vidéo arrêté")
            return True
        except Exception as e:
            print("⚠️ Erreur arrêt flux vidéo: {}".format(e))
            self.video_stream_active = False
            return False
    
    def recognize_face_from_stream(self, max_attempts=5, delay=0.3):
        """
        Reconnaît une personne depuis le flux vidéo continu
        """
        if not self.video:
            print("⚠️ Service ALVideoDevice non disponible")
            return None
        
        try:
            print("👤 Recherche de visage ({} tentatives)...".format(max_attempts))
            
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
                            
                            with open(temp_file.name, 'rb') as f:
                                response = post_file_with_retries(
                                    "{}/face/detect".format(API_CONFIG["base_url"]),
                                    files={"file": f},
                                )
                            
                            try:
                                os.unlink(temp_file.name)
                            except:
                                pass
                            
                            if response and response.ok:
                                result = response.json()
                                recognized_persons = result.get("recognized_persons", [])
                                
                                if recognized_persons and len(recognized_persons) > 0:
                                    name = recognized_persons[0]
                                    print("✅ Personne reconnue: {}".format(name))
                                    return name
                            
                            if attempt < max_attempts - 1:
                                time.sleep(delay)
                                
                        except Exception as e:
                            print("⚠️ Erreur traitement: {}".format(e))
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
                
                print("ℹ️ Aucune personne reconnue")
                return None
                
            finally:
                self.video.unsubscribe(video_client)
                
        except Exception as e:
            print("❌ Erreur reconnaissance faciale: {}".format(e))
            return None
    
    def recognize_face_from_camera(self):
        """
        Capture une image depuis la caméra pour la reconnaissance faciale
        """
        try:
            if self.video_stream_active:
                return self.recognize_face_from_stream()
            
            image_data, image_width, image_height = self.capture_image_from_camera()

            if not image_data:
                print("Impossible de capturer l'image")
                return None

            import tempfile
            try:
                from PIL import Image
                image_bytes = bytes(bytearray(image_data))
                im = Image.frombytes("RGB", (image_width, image_height), image_bytes)
                temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                im.save(temp_file.name, "JPEG")
                temp_file.close()
            except:
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
                        name = recognized_persons[0]
                        print("Personne reconnue: {}".format(name))
                        return name
                    else:
                        print("Aucune personne reconnue")
                        return None
                else:
                    return None
            finally:
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
                    
        except Exception as e:
            print("Erreur reconnaissance faciale: {}".format(e))
            return None
    
    def check_for_new_face(self, last_recognized_name=None):
        """
        Vérifie s'il y a un nouveau visage détecté
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
                    
                    if recognized_persons:
                        current_name = recognized_persons[0]
                        if current_name != last_recognized_name:
                            return current_name
            return None
        except:
            return None
    
    def start_wake_word_detection(self, wake_words=None):
        """
        Démarre la détection du wake word
        """
        if not self.speech_recognition:
            print("Erreur: Service SpeechRecognition non disponible")
            return False
        
        if self.wake_word_active:
            print("Wake word detection déjà active")
            return True
        
        if wake_words is None:
            wake_words = ["bonjour pepper", "hello pepper", "pepper", "hey pepper"]
        
        try:
            # Nettoyer toute reconnaissance en cours
            try:
                self.speech_recognition.unsubscribe("WakeWordDetection")
            except:
                pass
            try:
                self.speech_recognition.pause(True)
            except:
                pass
            
            time.sleep(0.5)
            
            self.speech_recognition.setLanguage("French")
            self.speech_recognition.setVocabulary(wake_words, False)
            
            self.wake_word_detected = False
            self.wake_word_active = True
            
            self.wake_word_subscriber = self.speech_recognition.subscriber("WordRecognized")
            self.wake_word_subscriber.signal.connect(self._on_wake_word_detected)
            
            self.speech_recognition.subscribe("WakeWordDetection")
            self.speech_recognition.pause(False)
            
            print("✅ Détection du wake word démarrée")
            print("   Mots-clés: {}".format(", ".join(wake_words)))
            return True
            
        except Exception as e:
            print("Erreur démarrage wake word: {}".format(e))
            self.wake_word_active = False
            return False
    
    def stop_wake_word_detection(self):
        """
        Arrête la détection du wake word
        """
        if not self.wake_word_active:
            return True
        
        try:
            if hasattr(self, 'wake_word_subscriber'):
                self.wake_word_subscriber.signal.disconnect(self._on_wake_word_detected)
                delattr(self, 'wake_word_subscriber')
            
            self.speech_recognition.unsubscribe("WakeWordDetection")
            self.wake_word_active = False
            print("✅ Détection du wake word arrêtée")
            return True
            
        except Exception as e:
            print("Erreur arrêt wake word: {}".format(e))
            return False
    
    def _on_wake_word_detected(self, value):
        """
        Callback pour le wake word
        """
        try:
            if len(value) >= 2:
                recognized_word = value[0]
                confidence = value[1]
                
                if confidence > 0.3:
                    print("🎤 Wake word détecté: '{}' (confiance: {:.2f})".format(recognized_word, confidence))
                    self.wake_word_detected = True
                else:
                    print("🎤 Mot détecté (confiance faible): '{}' ({:.2f})".format(recognized_word, confidence))
        except Exception as e:
            print("Erreur callback wake word: {}".format(e))
    
    def wait_for_wake_word_and_stream(self, timeout=30):
        """
        Attend le wake word puis active le streaming
        """
        if not self.wake_word_active:
            print("Erreur: Wake word detection n'est pas active")
            return False
        
        print("⏳ En attente du wake word... (timeout: {}s)".format(timeout))
        
        start_time = time.time()
        while not self.wake_word_detected and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        
        if not self.wake_word_detected:
            print("⏰ Timeout: Aucun wake word détecté")
            return False
        
        print("🎯 Wake word détecté! Arrêt de la reconnaissance...")
        self.stop_wake_word_detection()
        
        print("✅ Prêt pour l'enregistrement")
        return True

    def disconnect(self):
        """Déconnecte du robot"""
        if self.session:
            print("Déconnexion du robot...")
            self.session.close()
            print("Déconnecté")
            self.session = None
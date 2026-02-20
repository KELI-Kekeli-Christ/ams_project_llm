#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API client functions for pepper_test module.
Contains record_audio, transcribe_audio, chat_with_api, etc.
"""

import os
import time
import json
import requests
from api.flask_check import API_CONFIG, post_file_with_retries
from utils.helpers import force_utf8, safe_print


# Message de test à faire dire au robot
TEST_MESSAGE = "Bonjour, je suis connecté et prêt à vous aider. Ceci est un test de connexion."


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
                pass
        
        # Si on arrive ici, l'enregistrement n'a pas été arrêté normalement
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
        tuple: (text, language) or (None, None) on error
    """
    try:
        safe_print("Transcription de l'audio...")
        
        # Construire le chemin absolu si c'est un chemin relatif
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
        language: Optional language hint (ISO code)
    
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

        # Build JSON payload encoded as UTF-8
        try:
            data_obj = {"system": system_prompt, "message": message}
            if language:
                data_obj["language"] = language
            payload = json.dumps(data_obj, ensure_ascii=False).encode('utf-8')
        except TypeError:
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
    # or the verb 'réserver' is present.
    return ("reservation" in text_lower) or ("réservation" in text_lower) or ("réserver" in text_lower)


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
        from utils.helpers import CV2_AVAILABLE
        
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
                    import cv2
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


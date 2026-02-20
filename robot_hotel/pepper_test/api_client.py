# -*- coding: utf-8 -*-
"""
Client API Flask : enregistrement, transcription, chat, réservation, scan QR
"""
import os
import json
import time
import requests
from config import API_CONFIG
from utils.helpers import safe_print

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("OpenCV (cv2) non disponible. Le scan QR utilisera le téléchargement direct si possible.")
    print("Pour installer: pip install opencv-python")


def record_audio():
    """Enregistrement audio via API (détection silence). Retourne chemin fichier ou None."""
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
    """Enregistrement manuel (démarré/arrêté via bouton micro). Retourne chemin ou None."""
    try:
        print("Démarrage de l'enregistrement manuel...")
        already_recording = False
        try:
            status_response = requests.get("{}/record/status".format(API_CONFIG["base_url"]), timeout=2)
            if status_response.ok and status_response.json().get("recording", False):
                already_recording = True
                print("Enregistrement deja en cours (clic micro), attente de la fin...")
        except Exception:
            pass
        if not already_recording:
            response_start = requests.post("{}/record/start".format(API_CONFIG["base_url"]), timeout=10)
            if response_start.status_code == 400:
                try:
                    requests.post("{}/record/stop".format(API_CONFIG["base_url"]), timeout=5)
                    time.sleep(0.5)
                    response_start = requests.post("{}/record/start".format(API_CONFIG["base_url"]), timeout=10)
                except Exception:
                    pass
            response_start.raise_for_status()
            print("Enregistrement demarre. Parlez... arret auto apres 3 sec de silence (ou cliquez STOP).")
        max_wait_time = 300
        check_interval = 0.5
        elapsed_time = 0
        while elapsed_time < max_wait_time:
            time.sleep(check_interval)
            elapsed_time += check_interval
            try:
                status_response = requests.get("{}/record/status".format(API_CONFIG["base_url"]), timeout=2)
                if status_response.ok:
                    status = status_response.json()
                    if not status.get("recording", True):
                        audio_file = status.get("file")
                        if audio_file:
                            print("Fichier audio enregistré: {}".format(audio_file))
                            return audio_file
                        break
            except Exception:
                pass
        print("Arrêt automatique de l'enregistrement...")
        response_stop = requests.post("{}/record/stop".format(API_CONFIG["base_url"]), timeout=10)
        if response_stop.ok:
            audio_file = response_stop.json().get("file")
            if audio_file:
                return audio_file
        return None
    except Exception as e:
        print("Erreur lors de l'enregistrement manuel: {}".format(e))
        try:
            requests.post("{}/record/stop".format(API_CONFIG["base_url"]), timeout=5)
        except Exception:
            pass
        return None


def transcribe_audio(audio_file):
    """Transcrit l'audio via l'API. Retourne (text, language) ou (None, None)."""
    try:
        safe_print("Transcription de l'audio...")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        robot_hotel_dir = os.path.dirname(script_dir)
        if not os.path.isabs(audio_file):
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
            try:
                response.encoding = 'utf-8'
            except Exception:
                pass
            try:
                result = response.json()
            except Exception:
                try:
                    result = json.loads(response.text)
                except Exception as e:
                    safe_print("Erreur parsing JSON: {}", repr(e))
                    return None, None
            text = result.get("text")
            language = result.get("language") or None
            if isinstance(text, bytes):
                text = text.decode('utf-8', errors='ignore')
            # Ne pas faire str(text) sur unicode en Python 2 -> UnicodeEncodeError
            # Translitterer avant tout print (evite UnicodeEncodeError Python 2)
            from utils.helpers import transliterate_to_ascii
            text_safe = transliterate_to_ascii(text) if text else ""
            safe_print("Texte transcrit: {} (lang={})", text_safe, language)
            return text, language
    except Exception as e:
        safe_print("Erreur lors de la transcription: {}", repr(e))
        return None, None


def chat_with_api(message, language=None):
    """Envoie un message au chat. Retourne la réponse ou None."""
    try:
        print("Envoi du message au service de chat...")
        system_prompt = (
            "You are a helpful assistant. Always reply in the same language as the user's message. "
            "Detect the user's language from their input and respond using that language. "
            "Keep responses concise and user-friendly."
        )
        if isinstance(message, bytes):
            message = message.decode('utf-8', errors='ignore')
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
        return result.get("response")
    except Exception as e:
        try:
            print("Erreur chat: {}".format(repr(e)))
        except Exception:
            pass
        return None


def make_reservation_with_api(audio_file):
    """Crée une réservation depuis l'audio. Retourne dict ou None."""
    try:
        print("Création de réservation depuis l'audio...")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        robot_hotel_dir = os.path.dirname(script_dir)
        if not os.path.isabs(audio_file):
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
            return response.json()
    except Exception as e:
        print("Erreur lors de la création de réservation: {}".format(e))
        return None


def is_reservation_request(text):
    """True si le texte contient une demande de réservation."""
    if not text:
        return False
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="ignore")
    # Normaliser en ASCII pour eviter UnicodeDecodeError (Python 2 bytes vs unicode)
    from utils.helpers import transliterate_to_ascii
    text_lower = transliterate_to_ascii(text).lower()
    return ("reservation" in text_lower) or ("reserver" in text_lower)


def scan_qr_code_with_api(image_file_path=None, camera_url=None):
    """Scanne un QR code depuis image ou caméra. Retourne dict ou None."""
    try:
        url = "{}/scan_qr".format(API_CONFIG["base_url"])
        if image_file_path and os.path.exists(image_file_path):
            with open(image_file_path, "rb") as f:
                response = requests.post(url, files={"file": f}, timeout=API_CONFIG["timeout"])
        elif camera_url:
            temp_file = None
            try:
                if CV2_AVAILABLE:
                    cap = cv2.VideoCapture(camera_url)
                    ret, frame = cap.read()
                    cap.release()
                    if not ret:
                        raise Exception("OpenCV capture failed")
                    temp_file = "/tmp/pepper_qr_scan.png"
                    cv2.imwrite(temp_file, frame)
                    if not os.path.exists(temp_file):
                        raise Exception("Image save failed")
                elif camera_url.startswith("http://") or camera_url.startswith("https://"):
                    img_response = requests.get(camera_url, timeout=10, stream=True)
                    if img_response.status_code == 200:
                        temp_file = "/tmp/pepper_qr_scan.jpg"
                        with open(temp_file, 'wb') as f:
                            for chunk in img_response.iter_content(chunk_size=8192):
                                f.write(chunk)
                    else:
                        raise Exception("URL download failed")
                else:
                    print("❌ OpenCV non disponible. pip install opencv-python")
                    return None
                with open(temp_file, "rb") as f:
                    response = requests.post(url, files={"file": f}, timeout=API_CONFIG["timeout"])
            except Exception as e:
                print("❌ Erreur capture caméra: {}".format(e))
                return None
            finally:
                if temp_file and os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception:
                        pass
        else:
            return None
        response.raise_for_status()
        result = response.json()
        if result.get("success"):
            print("✅ QR code scanné avec succès!")
        return result
    except Exception as e:
        print("❌ Erreur scan QR: {}".format(e))
        return None


def is_qr_scan_request(text):
    """True si le texte contient une demande de scan QR."""
    if not text:
        return False
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="ignore")
    from utils.helpers import transliterate_to_ascii
    text_lower = transliterate_to_ascii(text).lower()
    keywords = [
        "scanner", "scanne", "qr code", "code qr", "verifier", "verifie",
        "mon qr", "mon code", "ma reservation", "check", "scan"
    ]
    return any(kw in text_lower for kw in keywords)

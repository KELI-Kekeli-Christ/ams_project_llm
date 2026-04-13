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


def release_micro():
    """Libère le micro (POST /record/stop). À appeler au démarrage et à la sortie pour éviter
    qu'un ancien lancement ait laissé l'enregistrement actif (micro indisponible)."""
    try:
        requests.post("{}/record/stop".format(API_CONFIG["base_url"]), timeout=3)
    except Exception:
        pass


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
            print("Enregistrement demarre. Parlez... arret auto apres 2 sec de silence (ou cliquez STOP).")
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


def chat_voice(audio_file, session_id=None):
    """Envoie un fichier audio à POST /chat/voice (transcription + chat). Retourne (response, session_id, transcript) ou (None, None, None)."""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        robot_hotel_dir = os.path.dirname(script_dir)
        if not os.path.isabs(audio_file):
            audio_file = os.path.join(robot_hotel_dir, audio_file)
        if not os.path.exists(audio_file):
            print("Erreur: Fichier audio inexistant: {}".format(audio_file))
            return None, None, None
        with open(audio_file, "rb") as f:
            response = requests.post(
                "{}/chat/voice".format(API_CONFIG["base_url"]),
                files={"file": f},
                data={"session_id": session_id} if session_id else {},
                timeout=API_CONFIG["timeout"]
            )
        response.raise_for_status()
        result = response.json()
        resp = result.get("response")
        sid = result.get("session_id") or session_id
        transcript = result.get("transcript") or ""
        return (resp, sid, transcript)
    except Exception as e:
        safe_print("Erreur chat/voice: {}", repr(e))
        return (None, None, None)


def chat_with_api(message, language=None, session_id=None):
    """Envoie un message au chat. Retourne (reponse, session_id) ou (None, None).
    session_id permet la memoire conversationnelle (rappel du contexte)."""
    try:
        print("Envoi du message au service de chat...")
        if isinstance(message, bytes):
            message = message.decode('utf-8', errors='ignore')
        # Ne pas utiliser str(message) ici : en Python 2, str(unicode avec accents) => UnicodeEncodeError.
        # Garder le texte tel quel pour json.dumps(ensure_ascii=False).encode('utf-8').
        data_obj = {"message": message}
        if language:
            data_obj["language"] = language
        if session_id:
            data_obj["session_id"] = session_id
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
        resp = result.get("response")
        sid = result.get("session_id")
        return (resp, sid)
    except Exception as e:
        try:
            print("Erreur chat: {}".format(repr(e)))
        except Exception:
            pass
        return (None, None)


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
    from utils.helpers import transliterate_to_ascii
    text_lower = transliterate_to_ascii(text).lower()
    # Mots-clés étendus : variantes françaises, anglaises, et erreurs de transcription courantes
    keywords = [
        "reservation", "reserver", "reserv",
        "chambre", "nuit", "sejour", "hotel",
        "dormir", "loger", "logement", "heberger", "hebergement",
        "check in", "checkin", "check-in",
        "booking", "book", "room",
        "arrivee", "depart", "date",
        "je veux rester", "je voudrais rester",
        "je veux une chambre", "je voudrais une chambre",
    ]
    matched = next((kw for kw in keywords if kw in text_lower), None)
    if matched:
        print("[Intent] Reservation detectee via mot-cle: '{}'".format(matched))
    return matched is not None


def scan_qr_code_with_api(image_file_path=None, camera_url=None):
    """Scanne un QR code depuis image ou caméra. Retourne dict ou None."""
    try:
        url = "{}/scan_qr".format(API_CONFIG["base_url"])
        if image_file_path and os.path.exists(image_file_path):
            name = os.path.basename(image_file_path) or "image.png"
            with open(image_file_path, "rb") as f:
                response = requests.post(url, files={"file": (name, f)}, timeout=API_CONFIG["timeout"])
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
                name = os.path.basename(temp_file) or "scan.png"
                with open(temp_file, "rb") as f:
                    response = requests.post(url, files={"file": (name, f)}, timeout=API_CONFIG["timeout"])
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


# ─── Wake word ────────────────────────────────────────────────────────────────

def start_wake_word_detection():
    """Démarre l'écoute des wake words côté serveur Flask."""
    try:
        requests.post("{}/record/wake_word/start".format(API_CONFIG["base_url"]), timeout=5)
    except Exception as e:
        print("Erreur démarrage wake word: {}".format(e))


def check_wake_word_status():
    """Retourne True si un wake word a été détecté."""
    try:
        r = requests.get("{}/record/wake_word/status".format(API_CONFIG["base_url"]), timeout=2)
        if r.ok:
            return r.json().get("wake_word_detected", False)
    except Exception:
        pass
    return False


def reset_wake_word():
    """Réinitialise l'état du wake word."""
    try:
        requests.post("{}/record/wake_word/reset".format(API_CONFIG["base_url"]), timeout=3)
    except Exception:
        pass


# ─── Réservation conversationnelle pas à pas ─────────────────────────────────

def conversation_start():
    """Démarre une conversation de réservation pas à pas. Retourne dict ou None."""
    try:
        r = requests.post(
            "{}/conversation/start".format(API_CONFIG["base_url"]),
            timeout=API_CONFIG["timeout"]
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("Erreur conversation/start: {}".format(e))
        return None


def conversation_answer(session_id, audio_file=None):
    """
    Envoie la réponse (dernier enregistrement) à l'étape courante.
    audio_file : chemin vers le fichier WAV (obligatoire pour micro Pepper).
    Retourne dict ou None.
    """
    try:
        if audio_file and os.path.exists(audio_file):
            # Envoyer directement le fichier (micro Pepper ou PC)
            with open(audio_file, "rb") as f:
                r = requests.post(
                    "{}/conversation/answer".format(API_CONFIG["base_url"]),
                    files={"file": ("audio.wav", f, "audio/wav")},
                    data={"session_id": session_id},
                    timeout=API_CONFIG["timeout"]
                )
        else:
            # Fallback : le serveur utilise get_last_recorded_file_path()
            r = requests.post(
                "{}/conversation/answer".format(API_CONFIG["base_url"]),
                json={"session_id": session_id},
                timeout=API_CONFIG["timeout"]
            )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("Erreur conversation/answer: {}".format(e))
        return None


def conversation_state(session_id):
    """
    Retourne l'état courant d'une conversation ou None si terminée/expirée.
    Un retour None signifie que la réservation a été finalisée.
    """
    try:
        r = requests.get(
            "{}/conversation/state".format(API_CONFIG["base_url"]),
            params={"session_id": session_id},
            timeout=5
        )
        if r.status_code == 404:
            return None  # conversation terminée / confirmée
        if r.ok:
            return r.json()
    except Exception:
        pass
    return None

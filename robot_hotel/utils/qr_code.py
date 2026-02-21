"""
Utilitaires pour la détection, vérification et génération des QR codes
"""
import io
import os
import base64
import threading
import time
import cv2
import numpy as np
import requests


def detect_qr_in_image(img):
    """
    Détecte un QR code dans une image

    Args:
        img: Image numpy array (BGR format from cv2)

    Returns:
        tuple: (success, qr_id) ou (False, None)
    """
    detector = cv2.QRCodeDetector()
    retval, decoded_info, points, straight_qrcode = detector.detectAndDecodeMulti(img)

    if retval and decoded_info and len(decoded_info) > 0 and decoded_info[0]:
        qr_id = decoded_info[0].strip()
        if qr_id:
            return True, qr_id

    return False, None


def generate_chat_qrcode(chat_url, as_base64=False):
    """
    Génère un QR code pointant vers l'URL du chatbot.

    Args:
        chat_url: URL complète du chat (ex: http://192.168.1.10:5000/chat)
        as_base64: Si True, retourne l'image en base64; sinon bytes PNG

    Returns:
        bytes ou str: Image PNG en bytes ou chaîne base64
    """
    import qrcode

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(chat_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    if as_base64:
        return base64.b64encode(img_bytes.getvalue()).decode()
    return img_bytes.getvalue()


def verify_qr_with_api(qr_id):
    """
    Vérifie un QR code via l'API FastAPI

    Args:
        qr_id: ID du QR code à vérifier

    Returns:
        dict: Résultat de la vérification
    """
    try:
        reservation_api_url = os.getenv("RESERVATION_API_URL", "http://localhost:8000")
        verify_url = f"{reservation_api_url}/verify_qr"

        response = requests.post(
            verify_url,
            json={"qr_id": qr_id},
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "qr_id": qr_id,
                "reservation": result.get("reservation", {}),
                "client": result.get("client", {})
            }
        elif response.status_code == 404:
            return {
                "success": False,
                "error": "QR code invalide ou réservation non trouvée",
                "qr_id": qr_id
            }
        else:
            error_detail = response.json().get("detail", "Erreur inconnue")
            return {
                "success": False,
                "error": f"Erreur lors de la vérification: {error_detail}",
                "qr_id": qr_id
            }

    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": "Impossible de se connecter à l'API de réservation. Vérifiez que le serveur FastAPI est démarré.",
            "qr_id": qr_id
        }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Timeout lors de la vérification du QR code",
            "qr_id": qr_id
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Erreur lors de la vérification: {str(e)}",
            "qr_id": qr_id
        }


# Variables globales pour le streaming QR code
qr_stream_capture = None
qr_stream_thread = None
qr_stream_active = False
qr_stream_lock = threading.Lock()
latest_qr_result = None


def qr_stream_worker(video_url=None, camera_index=0):
    """Thread worker pour capturer et analyser le flux vidéo QR code"""
    global qr_stream_capture, qr_stream_active, latest_qr_result

    try:
        if video_url:
            qr_stream_capture = cv2.VideoCapture(video_url)
        else:
            qr_stream_capture = cv2.VideoCapture(camera_index)

        if not qr_stream_capture.isOpened():
            error_msg = f"Impossible d'ouvrir la caméra {camera_index} ou l'URL {video_url}"
            print(f"❌ {error_msg}")
            with qr_stream_lock:
                qr_stream_active = False
                latest_qr_result = {"error": error_msg, "success": False}
            return

        print(f"✅ Stream QR code démarré - Camera: {camera_index}, URL: {video_url or 'None'}")

        frame_skip = 3

        while qr_stream_active:
            ret, frame = qr_stream_capture.read()

            if not ret:
                time.sleep(0.1)
                continue

            if frame_skip > 0:
                frame_skip -= 1
                continue
            frame_skip = 3

            success, qr_id = detect_qr_in_image(frame)

            if success and qr_id:
                result = verify_qr_with_api(qr_id)
                with qr_stream_lock:
                    latest_qr_result = result
                    if result.get("success"):
                        qr_stream_active = False

            time.sleep(0.2)

    except Exception as e:
        with qr_stream_lock:
            qr_stream_active = False
            latest_qr_result = {"error": str(e)}
    finally:
        if qr_stream_capture is not None:
            qr_stream_capture.release()
            qr_stream_capture = None

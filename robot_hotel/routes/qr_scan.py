"""
Routes Scan QR Code : scan d'images et streaming vidéo
"""
import threading
import numpy as np
import cv2
from flask import Blueprint, request, jsonify
from utils import qr_code as qr_code_module
from utils.qr_code import detect_qr_in_image, verify_qr_with_api, qr_stream_worker

bp = Blueprint('qr_scan', __name__)


@bp.route("/scan_qr", methods=["POST"])
def handle_scan_qr():
    """Scanne un QR code depuis une image"""
    if "file" not in request.files:
        return jsonify({"error": "No file provided", "success": False}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected", "success": False}), 400

    try:
        file_bytes = file.read()
        nparr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return jsonify({"error": "Invalid image file", "success": False}), 400

        success, qr_id = detect_qr_in_image(img)
        if not success:
            return jsonify({"error": "QR code not detected in image", "success": False}), 400

        result = verify_qr_with_api(qr_id)
        if result["success"]:
            return jsonify(result)
        status_code = 404 if "invalide" in result.get("error", "").lower() else 500
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({"error": f"Erreur lors du traitement: {str(e)}", "success": False}), 500


@bp.route("/scan_qr/stream/start", methods=["POST"])
def handle_scan_qr_stream_start():
    """Démarre le streaming vidéo pour la détection de QR code"""
    data = request.get_json() or {}
    video_url = data.get("video_url")
    camera_index = data.get("camera_index", 0)

    if qr_code_module.qr_stream_active:
        return jsonify({"error": "Stream déjà actif", "success": False}), 400

    qr_code_module.qr_stream_active = False
    if qr_code_module.qr_stream_thread:
        qr_code_module.qr_stream_thread.join(timeout=2.0)

    qr_code_module.qr_stream_active = True
    qr_code_module.qr_stream_thread = threading.Thread(
        target=qr_stream_worker,
        args=(video_url, camera_index),
        daemon=True
    )
    qr_code.qr_stream_thread.start()

    return jsonify({
        "success": True,
        "message": f"Stream QR code démarré (camera: {camera_index}, URL: {video_url or 'None'})"
    })


@bp.route("/scan_qr/stream/stop", methods=["POST"])
def handle_scan_qr_stream_stop():
    """Arrête le streaming vidéo QR code"""
    qr_code_module.qr_stream_active = False
    if qr_code_module.qr_stream_thread:
        qr_code_module.qr_stream_thread.join(timeout=2.0)
        qr_code_module.qr_stream_thread = None

    return jsonify({"success": True, "message": "Stream QR code arrêté"})


@bp.route("/scan_qr/stream/status", methods=["GET"])
def handle_scan_qr_stream_status():
    """Récupère le statut du stream QR code"""
    with qr_code_module.qr_stream_lock:
        result = qr_code_module.latest_qr_result.copy() if qr_code_module.latest_qr_result else None

    return jsonify({"active": qr_code_module.qr_stream_active, "result": result})


@bp.route("/scan_qr/stream", methods=["POST"])
def handle_scan_qr_stream():
    """Scanne un QR code depuis une frame vidéo"""
    if "file" not in request.files:
        return jsonify({"detected": False, "success": False}), 200

    file = request.files["file"]
    try:
        file_bytes = file.read()
        if len(file_bytes) == 0:
            return jsonify({"detected": False, "success": False}), 200

        nparr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return jsonify({"detected": False, "success": False}), 200

        success, qr_id = detect_qr_in_image(img)
        if not success:
            return jsonify({"detected": False, "success": False}), 200

        result = verify_qr_with_api(qr_id)
        result["detected"] = True
        return jsonify(result)

    except Exception as e:
        return jsonify({"detected": False, "success": False, "error": str(e)}), 200

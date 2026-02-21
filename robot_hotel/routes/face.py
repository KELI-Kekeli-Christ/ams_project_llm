"""
Routes Face Detection : détection, enregistrement, streaming
"""
from flask import Blueprint, request, jsonify
from services.face_detection import (
    detect_faces_in_image,
    register_person_from_image,
    get_registered_persons,
    delete_person,
    start_video_stream,
    stop_video_stream,
    get_latest_detections,
)

bp = Blueprint('face', __name__)


@bp.route("/face/detect", methods=["POST"])
def handle_face_detect():
    """Détecte et identifie les visages dans une image"""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    return detect_faces_in_image(request.files["file"])


@bp.route("/face/register", methods=["POST"])
def handle_face_register():
    """Enregistre une nouvelle personne dans la base de reconnaissance faciale"""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    if "name" not in request.form:
        return jsonify({"error": "Name parameter is required"}), 400
    return register_person_from_image(request.files["file"], request.form["name"])


@bp.route("/face/persons", methods=["GET"])
def handle_get_persons():
    """Récupère la liste des personnes enregistrées"""
    return get_registered_persons()


@bp.route("/face/persons/<name>", methods=["DELETE"])
def handle_delete_person(name):
    """Supprime une personne de la base"""
    return delete_person(name)


@bp.route("/face/stream/start", methods=["POST"])
def handle_start_stream():
    """Démarre le streaming vidéo pour la détection faciale"""
    data = request.get_json() or {}
    camera_index = data.get("camera_index", 0)
    video_url = data.get("video_url", None)
    return start_video_stream(camera_index, video_url)


@bp.route("/face/stream/stop", methods=["POST"])
def handle_stop_stream():
    """Arrête le streaming vidéo"""
    return stop_video_stream()


@bp.route("/face/stream/detections", methods=["GET"])
def handle_get_detections():
    """Récupère les dernières détections du flux vidéo"""
    return get_latest_detections()

"""
Routes Audio : transcription, enregistrement, wake word
"""
from flask import Blueprint, request, jsonify
from services.whisper import transcribe_audio
from services.record import (
    record_until_silence,
    start_manual_recording,
    stop_manual_recording,
    get_recording_status,
    get_last_recorded_file_path,
    start_wake_word_detection,
    get_wake_word_status,
    reset_wake_word_status,
    set_pepper_mic_mode,
    get_pepper_mic_mode,
)

bp = Blueprint('audio', __name__)


def get_whisper_model():
    """Récupère le modèle Whisper chargé (injecté par l'app)"""
    from flask import current_app
    return current_app.config.get('whisper_model')


@bp.route("/transcribe", methods=["POST"])
def handle_transcribe():
    """Transcrit un fichier audio en texte avec Whisper"""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    model = get_whisper_model()
    result = transcribe_audio(model, file=request.files["file"])
    return jsonify(result)


@bp.route("/record", methods=["GET"])
def handle_record():
    """Enregistre l'audio jusqu'à détection d'un silence"""
    return record_until_silence()


@bp.route("/record/start", methods=["POST"])
def handle_record_start():
    """Démarre un enregistrement audio manuel"""
    return start_manual_recording()


@bp.route("/record/stop", methods=["POST"])
def handle_record_stop():
    """Arrête l'enregistrement audio manuel"""
    return stop_manual_recording()


@bp.route("/record/status", methods=["GET"])
def handle_record_status():
    """Retourne l'état actuel de l'enregistrement"""
    return get_recording_status()


@bp.route("/record/pepper_mode", methods=["POST", "GET"])
def handle_pepper_mode():
    """Active/désactive le mode micro Pepper (POST) ou retourne l'état (GET)"""
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        enabled = data.get("enabled", True)
        set_pepper_mic_mode(enabled)
        return jsonify({"pepper_mic_mode": enabled, "message": "Mode micro Pepper activé" if enabled else "Mode micro PC"})
    return jsonify({"pepper_mic_mode": get_pepper_mic_mode()})


@bp.route("/record/wake_word/start", methods=["POST"])
def handle_wake_word_start():
    """Démarre l'écoute des mots déclencheurs"""
    result = start_wake_word_detection()
    return jsonify(result)


@bp.route("/record/wake_word/status", methods=["GET"])
def handle_wake_word_status():
    """Retourne l'état de la détection des mots déclencheurs"""
    result = get_wake_word_status()
    return jsonify(result)


@bp.route("/record/wake_word/reset", methods=["POST"])
def handle_wake_word_reset():
    """Réinitialise le statut du mot déclencheur"""
    result = reset_wake_word_status()
    return jsonify(result)

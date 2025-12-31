from flask import Flask, request, jsonify
from flasgger import Swagger
from services.chat import chat
from services.location import get_heure_date
from services.rag import init_rag
from services.whisper import charge_model_whisper, transcribe_audio
from services.record import record_until_silence
from services.make_reservation import make_reservation
from services.face_detection import (
    init_face_detection,
    detect_faces_in_image,
    register_person_from_image,
    get_registered_persons,
    delete_person,
    start_video_stream,
    stop_video_stream,
    get_latest_detections
)
from flask_cors import CORS 
from werkzeug.datastructures import FileStorage
import os
import requests
import cv2
import numpy as np
import threading
import time as time_module

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration Swagger
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/api-docs"
}

swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "Pepper-Llama Hotel API",
        "description": "API pour le robot hôtel Pepper avec intégration Llama 3, Whisper, et gestion de réservations",
        "version": "1.0.0",
        "contact": {
            "name": "API Support"
        }
    },
    "basePath": "/",
    "schemes": ["http", "https"],
    "tags": [
        {
            "name": "Chat",
            "description": "Endpoints pour la conversation avec le modèle Llama 3"
        },
        {
            "name": "Audio",
            "description": "Endpoints pour la transcription et l'enregistrement audio"
        },
        {
            "name": "Reservation",
            "description": "Endpoints pour la gestion des réservations"
        },
        {
            "name": "Face Detection",
            "description": "Endpoints pour la détection et reconnaissance faciale"
        },
        {
            "name": "System",
            "description": "Endpoints système"
        },
        {
            "name": "QR Code",
            "description": "Endpoints pour le scan et vérification de QR codes"
        },
        {
            "name": "QR Code",
            "description": "Endpoints pour le scan et vérification de QR codes"
        }
    ]
}

swagger = Swagger(app, config=swagger_config, template=swagger_template)

init_rag()
model=charge_model_whisper() #charger le model whisper au demarrage
init_face_detection() # Initialiser la détection faciale au démarrage

@app.route("/chat", methods=["POST"])
def handle_chat():
    """
    Envoie un message au chatbot et reçoit une réponse du modèle Llama 3
    ---
    tags:
      - Chat
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        description: Message de l'utilisateur
        required: true
        schema:
          type: object
          required:
            - message
          properties:
            message:
              type: string
              description: Le message de l'utilisateur
              example: "Quels sont les services de l'hôtel ?"
    responses:
      200:
        description: Réponse du chatbot avec contexte RAG
        schema:
          type: object
          properties:
            response:
              type: string
              description: La réponse du modèle Llama 3
            context_used:
              type: string
              description: Le contexte RAG utilisé pour la réponse
        example:
          response: "L'hôtel propose plusieurs services..."
          context_used: "Informations sur les services..."
      400:
        description: Erreur - Aucun message fourni
        schema:
          type: object
          properties:
            error:
              type: string
        example:
          error: "Aucun message fourni."
      500:
        description: Erreur serveur
        schema:
          type: object
          properties:
            error:
              type: string
    """
    data = request.get_json()
    return chat(user_message = data.get("message", ""))


@app.route("/location", methods=["GET"])
def handle_location():
    """
    Retourne l'heure et la date actuelles
    ---
    tags:
      - System
    produces:
      - text/plain
    responses:
      200:
        description: Heure et date actuelles
        schema:
          type: string
        example: "Il est 14:30 le 23 décembre 2025."
    """
    return get_heure_date()


@app.route("/transcribe", methods=["POST"])
def handle_transcribe():
    """
    Transcrit un fichier audio en texte en utilisant Whisper
    La langue est détectée automatiquement
    ---
    tags:
      - Audio
    consumes:
      - multipart/form-data
    produces:
      - application/json
    parameters:
      - in: formData
        name: file
        type: file
        required: true
        description: Fichier audio à transcrire (format MP3, WAV, etc.)
    responses:
      200:
        description: Transcription réussie
        schema:
          type: object
          properties:
            text:
              type: string
              description: Le texte transcrit
            language:
              type: string
              description: La langue détectée (code ISO 639-1)
        example:
          text: "Bonjour, je voudrais réserver une chambre"
          language: "fr"
      400:
        description: Erreur - Fichier non fourni ou invalide
        schema:
          type: object
          properties:
            error:
              type: string
      500:
        description: Erreur serveur
        schema:
          type: object
          properties:
            error:
              type: string
    """
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    result = transcribe_audio(model, file=request.files["file"])
    return jsonify(result)


@app.route("/record", methods=["GET"])
def handle_record():
    """
    Enregistre l'audio depuis le microphone jusqu'à détection d'un silence
    ---
    tags:
      - Audio
    produces:
      - application/json
    responses:
      200:
        description: Enregistrement terminé avec succès
        schema:
          type: object
          properties:
            message:
              type: string
              description: Message de confirmation
            file:
              type: string
              description: Chemin vers le fichier audio enregistré
        example:
          message: "Enregistrement terminé"
          file: "recordings/20251223_143000_voice.wav"
      500:
        description: Erreur lors de l'enregistrement
        schema:
          type: object
          properties:
            error:
              type: string
    """
    return record_until_silence()


@app.route("/make_reservation", methods=["POST"])
def handle_make_reservation():
    """
    Crée une réservation à partir d'un fichier audio
    Le fichier audio est transcrit, puis les informations sont extraites et envoyées à l'API de réservation
    ---
    tags:
      - Reservation
    consumes:
      - multipart/form-data
    produces:
      - application/json
    parameters:
      - in: formData
        name: file
        type: file
        required: true
        description: Fichier audio contenant la demande de réservation
    responses:
      200:
        description: Réservation créée avec succès
        schema:
          type: object
          properties:
            status:
              type: string
              description: Statut de l'opération (success ou error)
            reservation_data:
              type: object
              description: Données de réservation extraites
              properties:
                id_client:
                  type: string
                nom:
                  type: string
                prenom:
                  type: string
                type_chambre:
                  type: string
                  enum: [simple, double, suite]
                date_arrivee:
                  type: string
                  format: date
                date_depart:
                  type: string
                  format: date
            api_response:
              type: object
              description: Réponse de l'API de réservation
        example:
          status: "success"
          reservation_data:
            id_client: "C-001"
            nom: "Dupont"
            prenom: "Jean"
            type_chambre: "double"
            date_arrivee: "2025-12-25"
            date_depart: "2025-12-30"
          api_response:
            reservation_id: "R-12345"
      400:
        description: Erreur - Fichier non fourni ou transcript vide
        schema:
          type: object
          properties:
            error:
              type: string
            status:
              type: string
        example:
          error: "Le transcript est vide"
          status: "error"
      500:
        description: Erreur serveur
        schema:
          type: object
          properties:
            error:
              type: string
            status:
              type: string
    """
    try:
        # Vérifier si un fichier est fourni
        if "file" not in request.files:
            return jsonify({"error": "No file provided", "status": "error"}), 400
        
        uploaded_file = request.files["file"]
        if uploaded_file.filename == "":
            return jsonify({"error": "No file selected", "status": "error"}), 400
        
        print(f"📁 Fichier reçu : {uploaded_file.filename}")
        
        # Étape 1 : Transcrire l'audio directement depuis le fichier uploadé
        print("📝 Transcription de l'audio...")
        transcribe_result = transcribe_audio(model, uploaded_file)
        
        transcript = transcribe_result.get("text", "")
        language = transcribe_result.get("language", "")
        
        print(f"✅ Transcription : {transcript}")
        print(f"🌐 Langue détectée : {language}")
        
        if not transcript or not transcript.strip():
            return jsonify({
                "error": "Le transcript est vide. Le fichier audio ne contient peut-être pas de parole.",
                "status": "error"
            }), 400
        
        # Étape 2 : Créer la réservation
        print("📅 Création de la réservation...")
        result = make_reservation(transcript)
        
        # Ajouter les informations de transcription dans la réponse
        result["transcript"] = transcript
        result["language"] = language
        result["audio_filename"] = uploaded_file.filename
        
        return jsonify(result), 200
    
    except Exception as e:
        print(f"❌ Erreur : {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": f"Erreur serveur : {str(e)}",
            "status": "error"
        }), 500

@app.route("/face/detect", methods=["POST"])
def handle_face_detect():
    """
    Détecte et identifie les visages dans une image
    ---
    tags:
      - Face Detection
    consumes:
      - multipart/form-data
    produces:
      - application/json
    parameters:
      - in: formData
        name: file
        type: file
        required: true
        description: Image à analyser (format JPG, PNG, etc.)
    responses:
      200:
        description: Détection réussie
        schema:
          type: object
          properties:
            success:
              type: boolean
            detections:
              type: array
              description: Liste des détections
            total_detected:
              type: integer
            recognized_persons:
              type: array
            total_recognized:
              type: integer
      400:
        description: Erreur - Fichier non fourni ou invalide
      500:
        description: Erreur serveur
    """
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    return detect_faces_in_image(request.files["file"])

@app.route("/face/register", methods=["POST"])
def handle_face_register():
    """
    Enregistre une nouvelle personne dans la base de données de reconnaissance faciale
    ---
    tags:
      - Face Detection
    consumes:
      - multipart/form-data
    produces:
      - application/json
    parameters:
      - in: formData
        name: file
        type: file
        required: true
        description: Image contenant un seul visage à enregistrer
      - in: formData
        name: name
        type: string
        required: true
        description: Nom de la personne à enregistrer
    responses:
      200:
        description: Personne enregistrée avec succès
        schema:
          type: object
          properties:
            success:
              type: boolean
            message:
              type: string
            total_registered:
              type: integer
      400:
        description: Erreur - Fichier non fourni, aucun visage trouvé, ou nom déjà existant
      500:
        description: Erreur serveur
    """
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    if "name" not in request.form:
        return jsonify({"error": "Name parameter is required"}), 400
    return register_person_from_image(request.files["file"], request.form["name"])

@app.route("/face/persons", methods=["GET"])
def handle_get_persons():
    """
    Récupère la liste de toutes les personnes enregistrées
    ---
    tags:
      - Face Detection
    produces:
      - application/json
    responses:
      200:
        description: Liste des personnes enregistrées
        schema:
          type: object
          properties:
            success:
              type: boolean
            persons:
              type: array
              items:
                type: string
            total:
              type: integer
    """
    return get_registered_persons()

@app.route("/face/persons/<name>", methods=["DELETE"])
def handle_delete_person(name):
    """
    Supprime une personne de la base de données de reconnaissance faciale
    ---
    tags:
      - Face Detection
    produces:
      - application/json
    parameters:
      - in: path
        name: name
        type: string
        required: true
        description: Nom de la personne à supprimer
    responses:
      200:
        description: Personne supprimée avec succès
        schema:
          type: object
          properties:
            success:
              type: boolean
            message:
              type: string
            total_registered:
              type: integer
      404:
        description: Personne non trouvée dans la base de données
      500:
        description: Erreur serveur
    """
    return delete_person(name)

@app.route("/face/stream/start", methods=["POST"])
def handle_start_stream():
    """
    Démarre le streaming vidéo en temps réel pour la détection faciale
    ---
    tags:
      - Face Detection
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        description: Paramètres du stream vidéo
        schema:
          type: object
          properties:
            camera_index:
              type: integer
              description: Index de la caméra (par défaut 0)
              example: 0
            video_url:
              type: string
              description: URL du flux vidéo (optionnel, pour Pepper par exemple)
              example: "http://pepper.local:8080/video"
    responses:
      200:
        description: Stream vidéo démarré avec succès
        schema:
          type: object
          properties:
            success:
              type: boolean
            message:
              type: string
      400:
        description: Erreur - Stream déjà en cours
      500:
        description: Erreur serveur
    """
    data = request.get_json() or {}
    camera_index = data.get("camera_index", 0)
    video_url = data.get("video_url", None)
    return start_video_stream(camera_index, video_url)

@app.route("/face/stream/stop", methods=["POST"])
def handle_stop_stream():
    """
    Arrête le streaming vidéo en temps réel
    ---
    tags:
      - Face Detection
    produces:
      - application/json
    responses:
      200:
        description: Stream vidéo arrêté avec succès
        schema:
          type: object
          properties:
            success:
              type: boolean
            message:
              type: string
      400:
        description: Erreur - Aucun stream en cours
    """
    return stop_video_stream()

@app.route("/face/stream/detections", methods=["GET"])
def handle_get_detections():
    """
    Récupère les dernières détections du flux vidéo en temps réel
    ---
    tags:
      - Face Detection
    produces:
      - application/json
    responses:
      200:
        description: Dernières détections
        schema:
          type: object
          properties:
            success:
              type: boolean
            streaming:
              type: boolean
            detections:
              type: array
              description: Liste des détections actuelles
            recognized_persons:
              type: array
              description: Liste des personnes reconnues
            total_detected:
              type: integer
            total_recognized:
              type: integer
            timestamp:
              type: number
      400:
        description: Erreur - Aucun stream en cours
    """
    return get_latest_detections()

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

@app.route("/scan_qr", methods=["POST"])
def handle_scan_qr():
    """
    Scanne un QR code depuis une image et retourne les informations de réservation
    ---
    tags:
      - QR Code
    consumes:
      - multipart/form-data
    produces:
      - application/json
    parameters:
      - in: formData
        name: file
        type: file
        required: true
        description: Image contenant le QR code à scanner
    responses:
      200:
        description: QR code scanné et vérifié avec succès
        schema:
          type: object
          properties:
            success:
              type: boolean
            qr_id:
              type: string
              description: ID du QR code détecté
            reservation:
              type: object
              description: Informations de la réservation
            client:
              type: object
              description: Informations du client
      400:
        description: Erreur - Fichier non fourni, image invalide ou QR code non détecté
      404:
        description: QR code invalide ou réservation non trouvée
      500:
        description: Erreur serveur
    """
    if "file" not in request.files:
        return jsonify({"error": "No file provided", "success": False}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected", "success": False}), 400
    
    try:
        # Lire l'image
        file_bytes = file.read()
        nparr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return jsonify({"error": "Invalid image file", "success": False}), 400
        
        # Détecter le QR code
        success, qr_id = detect_qr_in_image(img)
        
        if not success:
            return jsonify({"error": "QR code not detected in image", "success": False}), 400
        
        # Vérifier le QR code via l'API
        result = verify_qr_with_api(qr_id)
        
        if result["success"]:
            return jsonify(result)
        else:
            status_code = 404 if "invalide" in result.get("error", "").lower() else 500
            return jsonify(result), status_code
            
    except Exception as e:
        return jsonify({"error": f"Erreur lors du traitement de l'image: {str(e)}", "success": False}), 500

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
        # Ouvrir le flux vidéo
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
        
        frame_skip = 3  # Analyser une frame sur 3 pour améliorer les performances
        
        while qr_stream_active:
            ret, frame = qr_stream_capture.read()
            
            if not ret:
                time_module.sleep(0.1)
                continue
            
            # Analyser une frame sur frame_skip
            if frame_skip > 0:
                frame_skip -= 1
                continue
            frame_skip = 3
            
            # Détecter le QR code dans la frame
            success, qr_id = detect_qr_in_image(frame)
            
            if success and qr_id:
                # Vérifier le QR code
                result = verify_qr_with_api(qr_id)
                with qr_stream_lock:
                    latest_qr_result = result
                    if result.get("success"):
                        # Arrêter le stream si un QR code valide est trouvé
                        qr_stream_active = False
            
            time_module.sleep(0.2)  # Pause entre les analyses
    
    except Exception as e:
        with qr_stream_lock:
            qr_stream_active = False
            latest_qr_result = {"error": str(e)}
    finally:
        if qr_stream_capture is not None:
            qr_stream_capture.release()
            qr_stream_capture = None

@app.route("/scan_qr/stream/start", methods=["POST"])
def handle_scan_qr_stream_start():
    """
    Démarre le streaming vidéo pour la détection automatique de QR code
    ---
    tags:
      - QR Code
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        schema:
          type: object
          properties:
            video_url:
              type: string
              description: URL du flux vidéo (optionnel)
            camera_index:
              type: integer
              description: Index de la caméra (par défaut 0)
    responses:
      200:
        description: Stream démarré avec succès
    """
    global qr_stream_thread, qr_stream_active
    
    data = request.get_json() or {}
    video_url = data.get("video_url")
    camera_index = data.get("camera_index", 0)
    
    if qr_stream_active:
        return jsonify({"error": "Stream déjà actif", "success": False}), 400
    
    # Arrêter le stream précédent s'il existe
    qr_stream_active = False
    if qr_stream_thread:
        qr_stream_thread.join(timeout=2.0)
    
    qr_stream_active = True
    qr_stream_thread = threading.Thread(
        target=qr_stream_worker,
        args=(video_url, camera_index),
        daemon=True
    )
    qr_stream_thread.start()
    
    return jsonify({
        "success": True,
        "message": f"Stream QR code démarré (camera: {camera_index}, URL: {video_url or 'None'})"
    })

@app.route("/scan_qr/stream/stop", methods=["POST"])
def handle_scan_qr_stream_stop():
    """
    Arrête le streaming vidéo QR code
    ---
    tags:
      - QR Code
    produces:
      - application/json
    responses:
      200:
        description: Stream arrêté avec succès
    """
    global qr_stream_active, qr_stream_thread
    
    qr_stream_active = False
    if qr_stream_thread:
        qr_stream_thread.join(timeout=2.0)
        qr_stream_thread = None
    
    return jsonify({
        "success": True,
        "message": "Stream QR code arrêté"
    })

@app.route("/scan_qr/stream/status", methods=["GET"])
def handle_scan_qr_stream_status():
    """
    Récupère le statut et les derniers résultats du stream QR code
    ---
    tags:
      - QR Code
    produces:
      - application/json
    responses:
      200:
        description: Statut du stream
    """
    global qr_stream_active, latest_qr_result
    
    with qr_stream_lock:
        result = latest_qr_result.copy() if latest_qr_result else None
    
    return jsonify({
        "active": qr_stream_active,
        "result": result
    })

@app.route("/scan_qr/stream", methods=["POST"])
def handle_scan_qr_stream():
    """
    Scanne un QR code depuis un flux vidéo (capture d'une frame)
    ---
    tags:
      - QR Code
    consumes:
      - multipart/form-data
    produces:
      - application/json
    parameters:
      - in: formData
        name: file
        type: file
        required: true
        description: Image/frame du flux vidéo contenant le QR code à scanner
      - in: formData
        name: video_url
        type: string
        required: false
        description: URL du flux vidéo (optionnel)
    responses:
      200:
        description: Résultat du scan (peut être vide si aucun QR code détecté)
        schema:
          type: object
          properties:
            detected:
              type: boolean
            qr_id:
              type: string
            success:
              type: boolean
            reservation:
              type: object
            client:
              type: object
    """
    if "file" not in request.files:
        return jsonify({"detected": False, "success": False}), 200
    
    file = request.files["file"]
    
    try:
        # Lire l'image
        file_bytes = file.read()
        if len(file_bytes) == 0:
            return jsonify({"detected": False, "success": False}), 200
            
        nparr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return jsonify({"detected": False, "success": False}), 200
        
        # Détecter le QR code
        success, qr_id = detect_qr_in_image(img)
        
        if not success:
            return jsonify({"detected": False, "success": False}), 200
        
        # Vérifier le QR code via l'API
        result = verify_qr_with_api(qr_id)
        result["detected"] = True
        return jsonify(result)
            
    except Exception as e:
        return jsonify({"detected": False, "success": False, "error": str(e)}), 200

@app.route("/")
def home():
    """
    Page d'accueil de l'API
    ---
    tags:
      - System
    produces:
      - text/plain
    responses:
      200:
        description: Message de bienvenue
        schema:
          type: string
        example: "Serveur Pepper-Llama en ligne 🚀"
    """
    return "Serveur Pepper-Llama en ligne 🚀"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

import cv2
import face_recognition
import numpy as np
import pickle
import os
import tempfile
import threading
import time
from flask import jsonify
from ultralytics import YOLO

# --- CONFIGURATION ---
DATABASE_FILE = "friends.pkl"
CONFIDENCE_THRESHOLD = 0.5

# Load YOLOv8 Model (Standard model detects 'person')
yolo_model = None
known_face_encodings = []
known_face_names = []

# Variables pour le streaming vidéo en temps réel
video_stream = None
video_thread = None
is_streaming = False
latest_detections = {
    "detections": [],
    "recognized_persons": [],
    "timestamp": None
}
stream_lock = threading.Lock()

def init_face_detection():
    """Initialise le modèle YOLO et charge la base de données des visages."""
    global yolo_model, known_face_encodings, known_face_names
    
    print("Loading YOLO model...")
    yolo_model = YOLO('yolov8n.pt')
    
    # Load known faces from database
    if os.path.exists(DATABASE_FILE):
        try:
            with open(DATABASE_FILE, 'rb') as f:
                data = pickle.load(f)
                known_face_encodings = data['encodings']
                known_face_names = data['names']
                print(f"Loaded {len(known_face_names)} people from database.")
        except Exception as e:
            print(f"Error loading database: {e}")
            known_face_encodings = []
            known_face_names = []

def save_database():
    """Saves the current list of known faces to disk."""
    try:
        with open(DATABASE_FILE, 'wb') as f:
            pickle.dump({'encodings': known_face_encodings, 'names': known_face_names}, f)
        return True
    except Exception as e:
        print(f"Error saving database: {e}")
        return False

def detect_faces_in_image(file):
    """
    Détecte et identifie les visages dans une image.
    
    Args:
        file: Fichier image uploadé via Flask
        
    Returns:
        JSON avec les détections et identifications
    """
    global yolo_model
    
    if yolo_model is None:
        return jsonify({"error": "YOLO model not initialized. Call init_face_detection() first."}), 500
    
    # Sauvegarder le fichier temporairement
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name
    
    try:
        # Charger l'image
        frame = cv2.imread(tmp_path)
        if frame is None:
            return jsonify({"error": "Could not load image"}), 400
        
        # Utiliser la fonction de traitement de frame
        result = process_frame_for_detection(frame)
        
        return jsonify({
            "success": True,
            "detections": result["detections"],
            "total_detected": len(result["detections"]),
            "recognized_persons": result["recognized_persons"],
            "total_recognized": len(result["recognized_persons"])
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    finally:
        # Nettoyer le fichier temporaire
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

def register_person_from_image(file, name):
    """
    Enregistre une nouvelle personne depuis une image.
    
    Args:
        file: Fichier image uploadé via Flask
        name: Nom de la personne
        
    Returns:
        JSON avec le résultat de l'enregistrement
    """
    global known_face_encodings, known_face_names
    
    if not name or name.strip() == "":
        return jsonify({"error": "Name cannot be empty"}), 400
    
    name = name.strip()
    
    # Sauvegarder le fichier temporairement
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name
    
    try:
        # Charger l'image
        image = cv2.imread(tmp_path)
        if image is None:
            return jsonify({"error": "Could not load image"}), 400
        
        # Convertir en RGB pour face_recognition
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Trouver les emplacements des visages
        face_locations = face_recognition.face_locations(rgb_image, model="hog")
        
        if len(face_locations) == 0:
            return jsonify({"error": "No face found in image"}), 400
        
        if len(face_locations) > 1:
            return jsonify({"error": "Multiple faces found. Please provide an image with only one face."}), 400
        
        # Obtenir l'encodage du visage
        face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
        
        if len(face_encodings) == 0:
            return jsonify({"error": "Could not generate face encoding"}), 400
        
        # Vérifier si le nom existe déjà
        if name in known_face_names:
            return jsonify({"error": f"Person '{name}' already exists in database"}), 400
        
        # Ajouter à la base de données
        known_face_encodings.append(face_encodings[0])
        known_face_names.append(name)
        
        # Sauvegarder la base de données
        if save_database():
            return jsonify({
                "success": True,
                "message": f"Successfully registered '{name}'",
                "total_registered": len(known_face_names)
            })
        else:
            return jsonify({"error": "Failed to save database"}), 500
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    finally:
        # Nettoyer le fichier temporaire
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

def get_registered_persons():
    """
    Retourne la liste des personnes enregistrées.
    
    Returns:
        JSON avec la liste des personnes
    """
    return jsonify({
        "success": True,
        "persons": known_face_names.copy(),
        "total": len(known_face_names)
    })

def delete_person(name):
    """
    Supprime une personne de la base de données.
    
    Args:
        name: Nom de la personne à supprimer
        
    Returns:
        JSON avec le résultat de la suppression
    """
    global known_face_encodings, known_face_names
    
    if name not in known_face_names:
        return jsonify({"error": f"Person '{name}' not found in database"}), 404
    
    # Trouver l'index et supprimer
    index = known_face_names.index(name)
    known_face_names.pop(index)
    known_face_encodings.pop(index)
    
    # Sauvegarder la base de données
    if save_database():
        return jsonify({
            "success": True,
            "message": f"Successfully deleted '{name}'",
            "total_registered": len(known_face_names)
        })
    else:
        return jsonify({"error": "Failed to save database"}), 500

def process_frame_for_detection(frame):
    """
    Traite une frame pour détecter et identifier les personnes.
    
    Args:
        frame: Image numpy array (BGR format)
        
    Returns:
        dict avec les détections
    """
    global yolo_model, known_face_encodings, known_face_names
    
    if yolo_model is None:
        return {"detections": [], "recognized_persons": []}
    
    # Détecter les personnes avec YOLO
    results = yolo_model(frame, classes=[0], verbose=False)
    
    detections = []
    
    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            
            if conf < CONFIDENCE_THRESHOLD:
                continue
            
            person_crop = frame[y1:y2, x1:x2]
            if person_crop.shape[0] < 20 or person_crop.shape[1] < 20:
                continue
            
            rgb_crop = cv2.cvtColor(person_crop, cv2.COLOR_BGR2RGB)
            face_locations_in_crop = face_recognition.face_locations(rgb_crop, model="hog")
            
            detection = {
                "bbox": {"x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2)},
                "confidence": float(conf),
                "name": "Unknown Person",
                "recognized": False
            }
            
            # Si un visage est trouvé, essayer de l'identifier
            if face_locations_in_crop:
                face_encs = face_recognition.face_encodings(rgb_crop, face_locations_in_crop)
                
                if face_encs:
                    matches = face_recognition.compare_faces(known_face_encodings, face_encs[0], tolerance=0.5)
                    face_distances = face_recognition.face_distance(known_face_encodings, face_encs[0])
                    
                    if len(face_distances) > 0:
                        best_match_index = np.argmin(face_distances)
                        if matches[best_match_index]:
                            detection["name"] = known_face_names[best_match_index]
                            detection["recognized"] = True
            
            detections.append(detection)
    
    # Extraire la liste des noms des personnes reconnues
    recognized_names = [det["name"] for det in detections if det["recognized"]]
    recognized_names = list(dict.fromkeys(recognized_names))
    
    return {
        "detections": detections,
        "recognized_persons": recognized_names
    }

def video_stream_worker(camera_index=0, video_url=None):
    """
    Thread worker qui traite le flux vidéo en continu.
    
    Args:
        camera_index: Index de la caméra (par défaut 0)
        video_url: URL du flux vidéo (optionnel, pour Pepper par exemple)
    """
    global video_stream, is_streaming, latest_detections, yolo_model
    
    try:
        # Ouvrir le flux vidéo
        if video_url:
            video_stream = cv2.VideoCapture(video_url)
        else:
            video_stream = cv2.VideoCapture(camera_index)
        
        if not video_stream.isOpened():
            with stream_lock:
                is_streaming = False
                latest_detections = {
                    "error": f"Could not open camera {camera_index} or video URL",
                    "detections": [],
                    "recognized_persons": [],
                    "timestamp": time.time()
                }
            return
        
        print(f"Video stream started (camera: {camera_index}, URL: {video_url})")
        
        frame_skip = 2  # Traiter une frame sur 2 pour améliorer les performances
        
        while is_streaming:
            ret, frame = video_stream.read()
            
            if not ret:
                print("Failed to read frame from video stream")
                break
            
            # Traiter une frame sur frame_skip pour améliorer les performances
            if frame_skip > 0:
                frame_skip -= 1
                continue
            frame_skip = 2
            
            # Traiter la frame
            result = process_frame_for_detection(frame)
            
            # Mettre à jour les dernières détections
            with stream_lock:
                latest_detections = {
                    "detections": result["detections"],
                    "recognized_persons": result["recognized_persons"],
                    "total_detected": len(result["detections"]),
                    "total_recognized": len(result["recognized_persons"]),
                    "timestamp": time.time()
                }
            
            # Petite pause pour ne pas surcharger le CPU
            time.sleep(0.1)
    
    except Exception as e:
        print(f"Error in video stream worker: {e}")
        with stream_lock:
            is_streaming = False
            latest_detections = {
                "error": str(e),
                "detections": [],
                "recognized_persons": [],
                "timestamp": time.time()
            }
    
    finally:
        if video_stream is not None:
            video_stream.release()
        video_stream = None

def start_video_stream(camera_index=0, video_url=None):
    """
    Démarre le streaming vidéo en temps réel.
    
    Args:
        camera_index: Index de la caméra (par défaut 0)
        video_url: URL du flux vidéo (optionnel)
        
    Returns:
        JSON avec le résultat
    """
    global video_thread, is_streaming, video_stream
    
    if is_streaming:
        return jsonify({"error": "Video stream is already running"}), 400
    
    # Arrêter le stream précédent s'il existe
    stop_video_stream()
    
    is_streaming = True
    video_thread = threading.Thread(
        target=video_stream_worker,
        args=(camera_index, video_url),
        daemon=True
    )
    video_thread.start()
    
    return jsonify({
        "success": True,
        "message": f"Video stream started (camera: {camera_index}, URL: {video_url or 'None'})"
    })

def stop_video_stream():
    """
    Arrête le streaming vidéo.
    
    Returns:
        JSON avec le résultat
    """
    global video_thread, is_streaming, video_stream
    
    if not is_streaming:
        return jsonify({"error": "No video stream is running"}), 400
    
    is_streaming = False
    
    if video_stream is not None:
        video_stream.release()
        video_stream = None
    
    if video_thread is not None:
        video_thread.join(timeout=2.0)
        video_thread = None
    
    return jsonify({
        "success": True,
        "message": "Video stream stopped"
    })

def get_latest_detections():
    """
    Récupère les dernières détections du flux vidéo en temps réel.
    
    Returns:
        JSON avec les dernières détections
    """
    global latest_detections, is_streaming
    
    if not is_streaming:
        return jsonify({
            "error": "No video stream is running",
            "success": False
        }), 400
    
    with stream_lock:
        result = latest_detections.copy()
    
    return jsonify({
        "success": True,
        "streaming": True,
        **result
    })


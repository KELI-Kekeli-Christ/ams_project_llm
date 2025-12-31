"""
Module utilitaire pour les appels API
"""
import requests
import os
from typing import Optional, Dict, Any

# Configuration de l'API
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5000")

def make_api_request(
    method: str,
    endpoint: str,
    data: Optional[Dict] = None,
    files: Optional[Dict] = None,
    json_data: Optional[Dict] = None,
    return_text: bool = False
) -> Dict[str, Any]:
    """
    Fait une requête à l'API Flask
    
    Args:
        method: Méthode HTTP (GET, POST, DELETE, etc.)
        endpoint: Endpoint de l'API (sans le base URL)
        data: Données form-data (pour multipart)
        files: Fichiers à envoyer
        json_data: Données JSON
        return_text: Si True, retourne aussi le texte de la réponse si JSON échoue
        
    Returns:
        Réponse de l'API sous forme de dictionnaire
    """
    url = f"{API_BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=30)
        elif method == "POST":
            if files:
                response = requests.post(url, data=data, files=files, timeout=60)
            elif json_data:
                response = requests.post(url, json=json_data, timeout=30)
            else:
                response = requests.post(url, data=data, timeout=30)
        elif method == "DELETE":
            response = requests.delete(url, timeout=30)
        else:
            return {"error": f"Method {method} not supported"}
        
        response.raise_for_status()
        
        # Essayer de parser en JSON, sinon retourner le texte si return_text=True
        try:
            return response.json()
        except ValueError:
            if return_text:
                return {"text": response.text, "status": "success"}
            else:
                return {"error": f"La réponse n'est pas du JSON: {response.text[:100]}"}
    
    except requests.exceptions.ConnectionError:
        return {"error": f"Impossible de se connecter à l'API à {url}. Vérifiez que le serveur Flask est démarré."}
    except requests.exceptions.Timeout:
        return {"error": "La requête a expiré. Le serveur met trop de temps à répondre."}
    except requests.exceptions.HTTPError as e:
        try:
            return response.json()
        except:
            return {"error": f"Erreur HTTP {e.response.status_code}: {str(e)}"}
    except Exception as e:
        return {"error": f"Erreur inattendue: {str(e)}"}

# Fonctions spécifiques pour chaque endpoint

def test_api_connection() -> bool:
    """Teste la connexion à l'API"""
    try:
        url = f"{API_BASE_URL}/"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        # L'endpoint "/" retourne du texte, pas du JSON
        # Si on reçoit une réponse (même du texte), la connexion fonctionne
        return True
    except requests.exceptions.ConnectionError:
        return False
    except requests.exceptions.Timeout:
        return False
    except Exception:
        return False

def chat_api(message: str) -> Dict:
    """Envoie un message au chatbot"""
    return make_api_request("POST", "/chat", json_data={"message": message})

def get_location() -> Dict:
    """Récupère l'heure et la date"""
    result = make_api_request("GET", "/location", return_text=True)
    # L'endpoint /location retourne du texte, pas du JSON
    if "text" in result:
        return {"text": result["text"], "success": True}
    return result

def transcribe_audio(file) -> Dict:
    """Transcrit un fichier audio"""
    return make_api_request("POST", "/transcribe", files={"file": file})

def record_audio() -> Dict:
    """Démarre l'enregistrement audio"""
    return make_api_request("GET", "/record")

def make_reservation(file) -> Dict:
    """Crée une réservation depuis un fichier audio"""
    return make_api_request("POST", "/make_reservation", files={"file": file})

# Face Detection APIs
def detect_faces(file) -> Dict:
    """Détecte les visages dans une image"""
    return make_api_request("POST", "/face/detect", files={"file": file})

def register_person(file, name: str) -> Dict:
    """Enregistre une nouvelle personne"""
    data = {"name": name}
    return make_api_request("POST", "/face/register", data=data, files={"file": file})

def get_registered_persons() -> Dict:
    """Récupère la liste des personnes enregistrées"""
    return make_api_request("GET", "/face/persons")

def delete_person(name: str) -> Dict:
    """Supprime une personne"""
    return make_api_request("DELETE", f"/face/persons/{name}")

def start_video_stream(camera_index: int = 0, video_url: Optional[str] = None) -> Dict:
    """Démarre le streaming vidéo"""
    json_data = {"camera_index": camera_index}
    if video_url:
        json_data["video_url"] = video_url
    return make_api_request("POST", "/face/stream/start", json_data=json_data)

def stop_video_stream() -> Dict:
    """Arrête le streaming vidéo"""
    return make_api_request("POST", "/face/stream/stop")

def get_latest_detections() -> Dict:
    """Récupère les dernières détections"""
    return make_api_request("GET", "/face/stream/detections")

def scan_qr_code(file) -> Dict:
    """Scanne un QR code depuis une image"""
    return make_api_request("POST", "/scan_qr", files={"file": file})

def scan_qr_code_stream(file, video_url: Optional[str] = None) -> Dict:
    """Scanne un QR code depuis un flux vidéo (frame)"""
    data = {}
    if video_url:
        data["video_url"] = video_url
    return make_api_request("POST", "/scan_qr/stream", files={"file": file}, data=data)

def start_qr_stream(video_url: Optional[str] = None, camera_index: int = 0) -> Dict:
    """Démarre le streaming vidéo pour la détection automatique de QR code"""
    json_data = {"camera_index": camera_index}
    if video_url:
        json_data["video_url"] = video_url
    return make_api_request("POST", "/scan_qr/stream/start", json_data=json_data)

def stop_qr_stream() -> Dict:
    """Arrête le streaming vidéo QR code"""
    return make_api_request("POST", "/scan_qr/stream/stop")

def get_qr_stream_status() -> Dict:
    """Récupère le statut et les résultats du stream QR code"""
    return make_api_request("GET", "/scan_qr/stream/status")


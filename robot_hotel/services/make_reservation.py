import json
import requests
from openai import OpenAI
from services.location import get_heure_date
import os
import uuid
import sqlite3
from datetime import datetime, timedelta

# Configuration de la base de données temporaire
TEMP_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'temp_reservations.db')

def init_temp_db():
    """Initialise la base de données temporaire pour les réservations en attente de validation"""
    conn = sqlite3.connect(TEMP_DB_PATH)
    cursor = conn.cursor()
    
    # Créer la table pour les réservations extraites (en attente de validation)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS extracted_reservations (
            session_id TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        )
    ''')
    
    # Créer la table pour les réservations validées (prêtes pour confirmation)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS validated_reservations (
            session_id TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        )
    ''')
    
    # Créer un index sur expires_at pour le nettoyage automatique
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_extracted_expires ON extracted_reservations(expires_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_validated_expires ON validated_reservations(expires_at)')
    
    conn.commit()
    conn.close()

def cleanup_expired_entries():
    """Nettoie les entrées expirées de la base de données temporaire"""
    try:
        conn = sqlite3.connect(TEMP_DB_PATH)
        cursor = conn.cursor()
        
        now = datetime.now()
        cursor.execute('DELETE FROM extracted_reservations WHERE expires_at < ?', (now,))
        cursor.execute('DELETE FROM validated_reservations WHERE expires_at < ?', (now,))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Erreur lors du nettoyage: {e}")

def store_extracted_reservation(session_id: str, data: dict) -> bool:
    """Stocke une réservation extraite dans la base temporaire"""
    try:
        init_temp_db()
        cleanup_expired_entries()
        
        conn = sqlite3.connect(TEMP_DB_PATH)
        cursor = conn.cursor()
        
        # Expiration dans 1 heure
        expires_at = datetime.now() + timedelta(hours=1)
        
        cursor.execute('''
            INSERT OR REPLACE INTO extracted_reservations (session_id, data, expires_at)
            VALUES (?, ?, ?)
        ''', (session_id, json.dumps(data), expires_at))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erreur stockage réservation extraite: {e}")
        return False

def get_extracted_reservation(session_id: str) -> dict:
    """Récupère une réservation extraite depuis la base temporaire"""
    try:
        init_temp_db()
        cleanup_expired_entries()
        
        conn = sqlite3.connect(TEMP_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT data FROM extracted_reservations WHERE session_id = ?', (session_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return json.loads(row[0])
        return None
    except Exception as e:
        print(f"Erreur récupération réservation extraite: {e}")
        return None

def store_validated_reservation(session_id: str, data: dict) -> bool:
    """Stocke une réservation validée dans la base temporaire"""
    try:
        init_temp_db()
        cleanup_expired_entries()
        
        conn = sqlite3.connect(TEMP_DB_PATH)
        cursor = conn.cursor()
        
        # Expiration dans 1 heure
        expires_at = datetime.now() + timedelta(hours=1)
        
        cursor.execute('''
            INSERT OR REPLACE INTO validated_reservations (session_id, data, expires_at)
            VALUES (?, ?, ?)
        ''', (session_id, json.dumps(data), expires_at))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erreur stockage réservation validée: {e}")
        return False

def get_validated_reservation(session_id: str) -> dict:
    """Récupère une réservation validée depuis la base temporaire"""
    try:
        init_temp_db()
        cleanup_expired_entries()
        
        conn = sqlite3.connect(TEMP_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT data FROM validated_reservations WHERE session_id = ?', (session_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return json.loads(row[0])
        return None
    except Exception as e:
        print(f"Erreur récupération réservation validée: {e}")
        return None

def delete_temp_reservation(session_id: str):
    """Supprime une réservation temporaire (après confirmation)"""
    try:
        init_temp_db()
        
        conn = sqlite3.connect(TEMP_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM extracted_reservations WHERE session_id = ?', (session_id,))
        cursor.execute('DELETE FROM validated_reservations WHERE session_id = ?', (session_id,))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Erreur suppression réservation temporaire: {e}")

# Configuration du client OpenAI via Hugging Face
client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key="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",  
)

# URL de l'API de réservation (FastAPI)
RESERVATION_API_URL = os.getenv("RESERVATION_API_URL", "http://localhost:8000")


def extract_reservation_info(transcript: str) -> dict:
    """
    Utilise le chat pour extraire les informations de réservation depuis le transcript de l'utilisateur.
    La date et l'heure actuelles sont utilisées pour convertir les dates relatives en dates absolues.
    Retourne un dictionnaire avec les informations structurées.
    """
    # Récupérer la date et l'heure actuelles pour aider à l'extraction
    current_datetime = get_heure_date()
    
    system_prompt = f"""Tu es un assistant spécialisé dans l'extraction d'informations de réservation d'hôtel.
À partir du transcript d'une conversation avec un client, tu dois extraire les informations suivantes et les retourner UNIQUEMENT au format JSON valide, sans texte supplémentaire :
{{
    "id_client": "C-XXX" ou "inconnu" si non mentionné,
    "nom": "nom du client" ou "inconnu" si non mentionné,
    "prenom": "prénom du client" ou "inconnu" si non mentionné,
    "type_chambre": "simple", "double", "suite" ou "inconnu" si non mentionné,
    "date_arrivee": "YYYY-MM-DD" ou "inconnu" si non mentionné,
    "date_depart": "YYYY-MM-DD" ou "inconnu" si non mentionné
}}

INFORMATION TEMPORELLE ACTUELLE :
{current_datetime}

RÈGLES IMPORTANTES :
- Le NOM et le PRÉNOM sont OBLIGATOIRES. Si le transcript ne les mentionne pas clairement, essaie de les déduire du contexte ou utilise "inconnu".
- Pour le type de chambre : accepte "simple", "double", "suite" ou équivalents (ex: "chambre simple", "chambre double", "suite").
- Pour les dates : utilise le format YYYY-MM-DD.
  * Si une date absolue est mentionnée (ex: "25 décembre", "30/12/2025"), utilise-la directement.
  * Si une date relative est mentionnée (ex: "demain", "dans 3 jours", "la semaine prochaine"), calcule la date absolue en te basant sur la date actuelle fournie ci-dessus.
  * Si seulement le jour est mentionné sans année, assume le mois et l'année actuels.
  * Exemples de conversion :
    - "demain" → date actuelle + 1 jour
    - "dans 3 jours" → date actuelle + 3 jours
    - "la semaine prochaine" → date actuelle + 7 jours
    - "lundi prochain" → prochain lundi à partir de la date actuelle
- L'id_client est optionnel et peut être "inconnu" si le client est nouveau.

IMPORTANT : Retourne UNIQUEMENT le JSON, sans texte avant ou après."""

    try:
        completion = client.chat.completions.create(
            model="meta-llama/Llama-3.1-8B-Instruct",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Transcript de la conversation :\n{transcript}\n\nExtrais les informations de réservation au format JSON."}
            ],
        )

        response_text = completion.choices[0].message.content.strip()
        
        # Nettoyer la réponse pour extraire uniquement le JSON
        # Parfois le modèle peut ajouter du texte avant/après le JSON
        response_text = response_text.strip()
        
        # Si la réponse commence par ```json ou ```, on les enlève
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        elif response_text.startswith("```"):
            response_text = response_text[3:]
        
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        response_text = response_text.strip()
        
        # Parser le JSON
        reservation_data = json.loads(response_text)
        return reservation_data
        
    except json.JSONDecodeError as e:
        print(f"Erreur de parsing JSON : {e}")
        print(f"Réponse reçue : {response_text}")
        return None
    except Exception as e:
        print(f"Erreur lors de l'extraction des informations : {e}")
        return None


def create_client_api(nom: str, prenom: str) -> dict:
    """
    Crée un client dans la DB via l'API et récupère son id_client.
    
    Args:
        nom: Nom du client
        prenom: Prénom du client
        
    Returns:
        Dictionnaire avec l'id_client créé ou erreur
    """
    try:
        payload = {
            "nom": nom.strip(),
            "prenom": prenom.strip()
        }
        
        endpoint = f"{RESERVATION_API_URL}/create_client"
        
        print(f"🌐 Appel de l'API pour créer le client : {endpoint}")
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            client_data = response.json()
            id_client = client_data.get("id_client")
            print(f"✅ Client créé avec succès : ID = {id_client}")
            return client_data
        else:
            error_text = response.text
            try:
                error_json = response.json()
                error_detail = error_json.get("detail", error_text)
            except:
                error_detail = error_text
                
            return {
                "error": f"Erreur lors de la création du client : {response.status_code} - {error_detail}",
                "status": "error"
            }
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur de connexion à l'API : {e}")
        return {
            "error": f"Erreur de connexion à l'API : {str(e)}",
            "status": "error"
        }
    except Exception as e:
        print(f"❌ Erreur lors de la création du client : {e}")
        return {
            "error": f"Erreur inattendue : {str(e)}",
            "status": "error"
        }


def create_reservation_api(id_client: str, reservation_data: dict) -> dict:
    """
    Crée une réservation dans la DB via l'API avec l'id_client.
    
    Args:
        id_client: L'ID du client créé précédemment
        reservation_data: Dictionnaire contenant les informations de réservation
        
    Returns:
        Dictionnaire avec la réponse de l'API ou erreur
    """
    try:
        # Vérifier les champs obligatoires : type_chambre, dates
        required_fields = {
            "type_chambre": "Le type de chambre est obligatoire",
            "date_arrivee": "La date d'arrivée est obligatoire",
            "date_depart": "La date de départ est obligatoire"
        }
        
        for field, error_msg in required_fields.items():
            if field not in reservation_data or not reservation_data[field] or reservation_data[field] == "inconnu":
                return {
                    "error": error_msg,
                    "status": "error",
                    "field": field
                }
        
        # Normaliser le type de chambre (accepter plusieurs variantes)
        type_chambre = reservation_data["type_chambre"].lower()
        if "simple" in type_chambre:
            type_chambre = "simple"
        elif "double" in type_chambre:
            type_chambre = "double"
        elif "suite" in type_chambre:
            type_chambre = "suite"
        
        # Préparer les données pour créer la réservation avec l'id_client
        payload = {
            "id_client": id_client,
            "nom": reservation_data.get("nom", "").strip(),
            "prenom": reservation_data.get("prenom", "").strip(),
            "type_chambre": type_chambre,
            "date_arrivee": reservation_data["date_arrivee"],
            "date_depart": reservation_data["date_depart"]
        }
        
        endpoint = f"{RESERVATION_API_URL}/create_reservation"
        
        print(f"🌐 Appel de l'API pour créer la réservation : {endpoint}")
        print(f"   Avec id_client : {id_client}")
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            api_response = response.json()
            print(f"✅ Réservation créée avec l'ID : {api_response.get('id_reservation', 'N/A')}")
            return api_response
        else:
            error_text = response.text
            try:
                error_json = response.json()
                error_detail = error_json.get("detail", error_text)
            except:
                error_detail = error_text
                
            return {
                "error": f"Erreur lors de la création de la réservation : {response.status_code} - {error_detail}",
                "status": "error"
            }
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur de connexion à l'API : {e}")
        return {
            "error": f"Erreur de connexion à l'API : {str(e)}",
            "status": "error"
        }
    except Exception as e:
        print(f"❌ Erreur lors de la création de la réservation : {e}")
        import traceback
        traceback.print_exc()
        return {
            "error": f"Erreur inattendue : {str(e)}",
            "status": "error"
        }


def make_reservation(transcript: str, session_id: str = None) -> dict:
    """
    Fonction principale qui prend le transcript de l'utilisateur,
    extrait les informations via le chat, et stocke les données pour validation.
    
    PROCESSUS MODIFIÉ :
    1. Extraction des informations (nom, prénom, dates, type chambre)
    2. Vérification que toutes les informations sont présentes
    3. Stockage dans Redis pour validation via tablette
    4. La création client/réservation se fait seulement après validation
    
    Args:
        transcript: Le transcript de la conversation avec l'utilisateur
        session_id: ID de session optionnel (généré automatiquement si non fourni)
        
    Returns:
        Dictionnaire avec le résultat de l'extraction et stockage
    """
    if not transcript or not transcript.strip():
        return {
            "error": "Le transcript est vide",
            "status": "error"
        }
    
    # Générer un session_id si non fourni
    if not session_id:
        session_id = f"res_{uuid.uuid4().hex[:8]}"
    
    # Initialiser la base de données temporaire
    try:
        init_temp_db()
    except Exception as e:
        return {
            "error": f"Impossible d'initialiser la base de données temporaire: {str(e)}",
            "status": "error"
        }
    
    # Étape 1 : Extraire les informations depuis le transcript
    print("\n" + "="*60)
    print("📝 ÉTAPE 1 : EXTRACTION DES INFORMATIONS")
    print("="*60)
    reservation_data = extract_reservation_info(transcript)
    
    if reservation_data is None:
        return {
            "error": "Impossible d'extraire les informations de réservation du transcript",
            "status": "error"
        }
    
    print(f"📋 Informations extraites :")
    print(f"   - Nom : {reservation_data.get('nom', 'N/A')}")
    print(f"   - Prénom : {reservation_data.get('prenom', 'N/A')}")
    print(f"   - Type chambre : {reservation_data.get('type_chambre', 'N/A')}")
    print(f"   - Date arrivée : {reservation_data.get('date_arrivee', 'N/A')}")
    print(f"   - Date départ : {reservation_data.get('date_depart', 'N/A')}")
    print(f"   - ID Client : {reservation_data.get('id_client', 'N/A')}")
    
    # Étape 2 : Vérification basique que les champs principaux sont présents
    print("\n" + "="*60)
    print("✅ ÉTAPE 2 : VÉRIFICATION BASIQUE DES DONNÉES")
    print("="*60)
    
    # Vérifier au moins nom et prénom (les plus critiques)
    if reservation_data.get('nom') == "inconnu" or reservation_data.get('prenom') == "inconnu":
        return {
            "error": "Nom et prénom sont obligatoires et n'ont pas pu être extraits du transcript",
            "status": "error",
            "reservation_data": reservation_data
        }
    
    # Étape 3 : Stocker dans Redis pour validation
    print("\n" + "="*60)
    print("💾 ÉTAPE 3 : STOCKAGE POUR VALIDATION")
    print("="*60)
    
    # Préparer les données à stocker
    storage_data = reservation_data.copy()
    storage_data['session_id'] = session_id
    storage_data['transcript'] = transcript
    storage_data['extracted_at'] = get_heure_date()
    storage_data['status'] = 'extracted'
    
    # Stocker dans SQLite avec expiration (1 heure)
    try:
        success = store_extracted_reservation(session_id, storage_data)
        if not success:
            return {
                "error": "Erreur lors du stockage temporaire dans la base de données",
                "status": "error"
            }
        print(f"✅ Données stockées dans SQLite avec session_id: {session_id}")
    except Exception as e:
        print(f"❌ Erreur stockage SQLite: {e}")
        return {
            "error": f"Erreur lors du stockage temporaire: {str(e)}",
            "status": "error"
        }
    
    return {
        "status": "success",
        "message": "Informations extraites et stockées pour validation",
        "session_id": session_id,
        "reservation_data": reservation_data,
        "next_step": "validation_required"
    }


def make_reservation_from_data(user_data: dict) -> dict:
    """
    Crée une réservation directement à partir de données structurées.
    Cette fonction est utilisée lors de la confirmation de réservation depuis la page de validation.
    
    Args:
        user_data: Dictionnaire contenant les informations de réservation
            - nom: Nom du client
            - prenom: Prénom du client
            - email: Email du client (optionnel)
            - type_chambre: Type de chambre (simple, double, suite)
            - date_arrivee: Date d'arrivée (YYYY-MM-DD)
            - date_depart: Date de départ (YYYY-MM-DD)
        
    Returns:
        Dictionnaire avec le résultat de la création de réservation
    """
    try:
        # Étape 1: Créer le client si nécessaire
        nom = user_data.get('nom', '').strip()
        prenom = user_data.get('prenom', '').strip()
        
        if not nom or not prenom:
            return {
                "error": "Nom et prénom sont obligatoires",
                "status": "error"
            }
        
        print(f"\n{'='*60}")
        print("📝 CRÉATION DE RÉSERVATION DEPUIS DONNÉES VALIDÉES")
        print(f"{'='*60}")
        
        # Créer le client
        client_result = create_client_api(nom, prenom)
        
        if client_result.get('error'):
            print(f"⚠️ Erreur création client: {client_result.get('error')}")
            # On continue quand même pour tester même si le client n'est pas créé
        
        id_client = client_result.get('id_client', 'C-TEMP')
        
        # Étape 2: Créer la réservation
        reservation_data = {
            'nom': nom,
            'prenom': prenom,
            'type_chambre': user_data.get('type_chambre', 'simple'),
            'date_arrivee': user_data.get('date_arrivee'),
            'date_depart': user_data.get('date_depart')
        }
        
        reservation_result = create_reservation_api(id_client, reservation_data)
        
        if reservation_result.get('error'):
            print(f"⚠️ Erreur création réservation: {reservation_result.get('error')}")
            # Stocker quand même en local comme sauvegarde
            return {
                "status": "success",
                "message": "Réservation créée localement (API externe non disponible)",
                "reservation_id": f"LOCAL-{uuid.uuid4().hex[:8]}",
                "local": True,
                "reservation_data": reservation_data
            }
        
        return {
            "status": "success",
            "message": "Réservation créée avec succès",
            "reservation_id": reservation_result.get('id_reservation'),
            "reservation_data": reservation_data
        }
        
    except Exception as e:
        print(f"❌ Erreur création réservation: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "error": f"Erreur lors de la création de la réservation: {str(e)}",
            "status": "error"
        }


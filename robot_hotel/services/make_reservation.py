import json
import requests
from openai import OpenAI
import os

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
    Retourne un dictionnaire avec les informations structurées.
    """
    system_prompt = """Tu es un assistant spécialisé dans l'extraction d'informations de réservation d'hôtel.
À partir du transcript d'une conversation avec un client, tu dois extraire les informations suivantes et les retourner UNIQUEMENT au format JSON valide, sans texte supplémentaire :
{
    "id_client": "C-XXX" ou "inconnu" si non mentionné,
    "nom": "nom du client" ou "inconnu" si non mentionné,
    "prenom": "prénom du client" ou "inconnu" si non mentionné,
    "type_chambre": "simple", "double", "suite" ou "inconnu" si non mentionné,
    "date_arrivee": "YYYY-MM-DD" ou "inconnu" si non mentionné,
    "date_depart": "YYYY-MM-DD" ou "inconnu" si non mentionné
}

RÈGLES IMPORTANTES :
- Le NOM et le PRÉNOM sont OBLIGATOIRES. Si le transcript ne les mentionne pas clairement, essaie de les déduire du contexte ou utilise "inconnu".
- Pour le type de chambre : accepte "simple", "double", "suite" ou équivalents (ex: "chambre simple", "chambre double", "suite").
- Pour les dates : utilise le format YYYY-MM-DD. Si seulement le jour est mentionné, assume le mois et l'année actuels.
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


def make_reservation(transcript: str) -> dict:
    """
    Fonction principale qui prend le transcript de l'utilisateur,
    extrait les informations via le chat, et crée la réservation via l'API.
    
    PROCESSUS :
    1. Extraction des informations (nom, prénom, dates, type chambre)
    2. Vérification que toutes les informations sont présentes
    3. Création du client dans la DB (nom, prénom)
    4. Création de la réservation dans la DB liée au client
    
    Args:
        transcript: Le transcript de la conversation avec l'utilisateur
        
    Returns:
        Dictionnaire avec le résultat de la création de réservation
    """
    if not transcript or not transcript.strip():
        return {
            "error": "Le transcript est vide",
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
    
    # Étape 2 : Vérifier que toutes les informations nécessaires sont présentes
    print("\n" + "="*60)
    print("✅ ÉTAPE 2 : VÉRIFICATION DES DONNÉES")
    print("="*60)
    
    # Étape 3 : Créer le client dans la DB
    print("\n" + "="*60)
    print("💾 ÉTAPE 3 : CRÉATION DU CLIENT DANS LA DB")
    print("="*60)
    print(f"👤 Insertion du client : {reservation_data['nom']} {reservation_data['prenom']}")
    
    client_result = create_client_api(
        nom=reservation_data["nom"],
        prenom=reservation_data["prenom"]
    )
    
    if client_result.get("status") == "error":
        return client_result
    
    id_client = client_result.get("id_client")
    if not id_client:
        return {
            "error": "Impossible de récupérer l'ID du client créé",
            "status": "error"
        }
    
    print(f"✅ Client inséré dans la DB avec l'ID : {id_client}")
    
    # Étape 4 : Récupérer l'id_client et créer la réservation
    print("\n" + "="*60)
    print("📅 ÉTAPE 4 : CRÉATION DE LA RÉSERVATION AVEC L'ID CLIENT")
    print("="*60)
    print(f"🆔 Utilisation de l'id_client : {id_client}")
    print(f"📅 Création de la réservation : {reservation_data.get('type_chambre')} du {reservation_data.get('date_arrivee')} au {reservation_data.get('date_depart')}")
    
    reservation_result = create_reservation_api(id_client, reservation_data)
    
    if reservation_result.get("status") == "error":
        return reservation_result
    
    print("\n" + "="*60)
    print("🎉 RÉSERVATION CRÉÉE AVEC SUCCÈS")
    print("="*60)
    
    return {
        "status": "success",
        "client": client_result,
        "reservation": reservation_result,
        "reservation_data": reservation_data,
        "message": f"Client {reservation_data.get('nom')} {reservation_data.get('prenom')} (ID: {id_client}) créé dans la DB. Réservation créée avec succès."
    }


from pydantic import BaseModel, Field
from typing import Optional, Dict

# --------- Requêtes ---------

class CreateReservation(BaseModel):
    """Modèle pour créer une nouvelle réservation"""
    id_client: str = Field(..., description="Identifiant unique du client", example="C-002")
    nom: Optional[str] = Field("", description="Nom du client", example="Dupont")
    prenom: Optional[str] = Field("", description="Prénom du client", example="Jean")
    type_chambre: str = Field(..., description="Type de chambre souhaité", example="simple")
    date_arrivee: str = Field(..., description="Date d'arrivée au format ISO (YYYY-MM-DD)", example="2025-11-10")
    date_depart: str = Field(..., description="Date de départ au format ISO (YYYY-MM-DD)", example="2025-11-15")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id_client": "C-002",
                "nom": "Dupont",
                "prenom": "Jean",
                "type_chambre": "simple",
                "date_arrivee": "2025-11-10",
                "date_depart": "2025-11-15"
            }
        }

class CheckReservation(BaseModel):
    """Modèle pour vérifier une réservation existante"""
    id_res: str = Field(..., description="Identifiant de la réservation", example="R-C-002-2025-11-10")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id_res": "R-C-002-2025-11-10"
            }
        }

class UpdatePreferences(BaseModel):
    """Modèle pour mettre à jour les préférences d'un client"""
    id_client: str = Field(..., description="Identifiant du client", example="C-002")
    preferences: Dict = Field(..., description="Dictionnaire des préférences du client", example={"lit": "double", "vue": "mer", "etage": "haut"})
    
    class Config:
        json_schema_extra = {
            "example": {
                "id_client": "C-002",
                "preferences": {
                    "lit": "double",
                    "vue": "mer",
                    "etage": "haut"
                }
            }
        }

class VerifyQR(BaseModel):
    """Modèle pour vérifier un QR code"""
    qr_id: str = Field(..., description="Identifiant du QR code à vérifier", example="R-C-002-2025-11-10")
    
    class Config:
        json_schema_extra = {
            "example": {
                "qr_id": "R-C-002-2025-11-10"
            }
        }

class CreateClient(BaseModel):
    """Modèle pour créer un nouveau client"""
    nom: str = Field(..., description="Nom du client", example="Martin")
    prenom: str = Field(..., description="Prénom du client", example="Sophie")
    
    class Config:
        json_schema_extra = {
            "example": {
                "nom": "Martin",
                "prenom": "Sophie"
            }
        }

class CreateReservationOnSite(BaseModel):
    """Modèle pour créer une réservation sur place (sans id_client préexistant)"""
    nom: str = Field(..., description="Nom du client", example="Martin")
    prenom: str = Field(..., description="Prénom du client", example="Sophie")
    type_chambre: str = Field(..., description="Type de chambre souhaité", example="double")
    date_arrivee: str = Field(..., description="Date d'arrivée au format ISO (YYYY-MM-DD)", example="2025-11-20")
    date_depart: str = Field(..., description="Date de départ au format ISO (YYYY-MM-DD)", example="2025-11-25")
    
    class Config:
        json_schema_extra = {
            "example": {
                "nom": "Martin",
                "prenom": "Sophie",
                "type_chambre": "double",
                "date_arrivee": "2025-11-20",
                "date_depart": "2025-11-25"
            }
        }

# --------- Réponses ---------

class ReservationResponse(BaseModel):
    """Modèle de réponse pour une réservation"""
    status: str = Field(..., description="Statut de la réponse", example="created")
    id_reservation: str = Field(..., description="Identifiant de la réservation", example="R-C-002-2025-11-10")
    id_client: str = Field(..., description="Identifiant du client", example="C-002")
    qr_code_path: str = Field(..., description="Chemin vers le fichier QR code généré", example="app/static/qr/R-C-002-2025-11-10.png")

class ReservationDetailResponse(BaseModel):
    """Modèle de réponse détaillée pour une réservation"""
    status: str = Field(..., description="Statut de la réponse", example="ok")
    client: Dict = Field(..., description="Informations du client")
    reservation: Dict = Field(..., description="Informations de la réservation")

class PreferencesResponse(BaseModel):
    """Modèle de réponse pour la mise à jour des préférences"""
    status: str = Field(..., description="Statut de la réponse", example="updated")
    preferences: Dict = Field(..., description="Préférences mises à jour")
from fastapi import FastAPI
from app import db
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date, datetime
from fastapi import HTTPException
from app import schemas

from app.db import get_session
from app import crud
from app.schemas import CreateReservation, CheckReservation, UpdatePreferences, CreateClient

import qrcode
import os
import time


app = FastAPI(
    title="CERIBot Server",
    description="""
    API de gestion des réservations pour CERIBot.
    
    Cette API permet de :
    * Créer et gérer des réservations
    * Vérifier les réservations existantes
    * Gérer les préférences des clients
    * Générer et vérifier des QR codes
    * Confirmer les arrivées
    
    ## Endpoints principaux
    
    * **Réservations** : Création et consultation des réservations
    * **QR Codes** : Génération et vérification des QR codes
    * **Clients** : Gestion des préférences clients
    """,
    version="1.0.0",
    contact={
        "name": "CERIBot Support",
    },
    tags_metadata=[
        {
            "name": "Health",
            "description": "Endpoints de vérification de santé de l'API",
        },
        {
            "name": "Réservations",
            "description": "Gestion des réservations (création, consultation)",
        },
        {
            "name": "QR Codes",
            "description": "Génération et vérification des QR codes",
        },
        {
            "name": "Clients",
            "description": "Gestion des préférences clients",
        },
    ],
)
def get_db():
    SessionLocal = get_session()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def generate_qr(text: str, filename: str):
    # Création du QR
    img = qrcode.make(text)

    # Chemin final
    folder = "app/static/qr"
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)

    # Enregistrement
    img.save(path)

    return path


@app.on_event("startup")
def startup():
    db.init_db()

@app.post(
    "/create_client",
    tags=["Clients"],
    summary="Créer un nouveau client",
    description="""
    Crée un nouveau client dans la base de données.
    
    * Un id_client unique sera généré automatiquement
    * Retourne l'id_client créé pour pouvoir créer une réservation ensuite
    """,
    response_description="Détails du client créé avec son id_client",
    responses={
        200: {
            "description": "Client créé avec succès",
            "content": {
                "application/json": {
                    "example": {
                        "status": "created",
                        "id_client": "C-1734987600",
                        "nom": "Martin",
                        "prenom": "Sophie"
                    }
                }
            }
        },
        422: {"description": "Erreur de validation des données"}
    }
)
def create_client_route(payload: CreateClient, db: Session = Depends(get_db)):
    """
    Crée un nouveau client.
    
    Args:
        payload: Données du client (nom, prénom)
        db: Session de base de données
    
    Returns:
        Dictionnaire contenant le statut, l'ID client, le nom et le prénom
    """
    client = crud.create_client(db, nom=payload.nom, prenom=payload.prenom)
    
    return {
        "status": "created",
        "id_client": client.id_client,
        "nom": client.nom,
        "prenom": client.prenom
    }


@app.get(
    "/health",
    tags=["Health"],
    summary="Vérification de santé",
    description="Endpoint pour vérifier que l'API est opérationnelle",
    response_description="Statut de l'API"
)
def health():
    """
    Vérifie que l'API est opérationnelle.
    
    Retourne un statut "ok" si l'API fonctionne correctement.
    """
    return {"status": "ok"}

@app.post(
    "/create_reservation",
    tags=["Réservations"],
    summary="Créer une réservation",
    description="""
    Crée une nouvelle réservation pour un client existant.
    
    * Si le client n'existe pas, il sera créé automatiquement
    * Un QR code sera généré pour la réservation
    * Le statut initial de la réservation est "prévue"
    """,
    response_description="Détails de la réservation créée avec le chemin du QR code",
    responses={
        200: {
            "description": "Réservation créée avec succès",
            "content": {
                "application/json": {
                    "example": {
                        "status": "created",
                        "id_reservation": "R-C-002-2025-11-10",
                        "id_client": "C-002",
                        "qr_code_path": "app/static/qr/R-C-002-2025-11-10.png"
                    }
                }
            }
        },
        422: {"description": "Erreur de validation des données"}
    }
)
def create_res(payload: CreateReservation, db: Session = Depends(get_db)):
    """
    Crée une nouvelle réservation.
    
    Args:
        payload: Données de la réservation (client, dates, type de chambre)
        db: Session de base de données
    
    Returns:
        Dictionnaire contenant le statut, l'ID de réservation, l'ID client et le chemin du QR code
    """
    # Convertir les dates string en date
    date_arrivee = date.fromisoformat(payload.date_arrivee)
    date_depart = date.fromisoformat(payload.date_depart)

    # Vérifier ou créer le client
    client = crud.ensure_client(
        db,
        id_client=payload.id_client,
        nom=payload.nom,
        prenom=payload.prenom
    )

    # Générer un id_res unique (avec timestamp pour éviter les doublons)
    base_id = f"R-{payload.id_client}-{payload.date_arrivee}"
    id_res = base_id
    
    # Vérifier si une réservation avec cet ID existe déjà
    counter = 1
    while crud.get_reservation(db, id_res) is not None:
        # Si l'ID existe déjà, ajouter un suffixe numérique
        id_res = f"{base_id}-{counter}"
        counter += 1
        # Sécurité : éviter une boucle infinie (max 1000 tentatives)
        if counter > 1000:
            # En dernier recours, utiliser un timestamp
            id_res = f"{base_id}-{int(time.time())}"
            break

    # Données SQLAlchemy
    data = {
        "id_res": id_res,
        "id_client": payload.id_client,
        "type_chambre": payload.type_chambre,
        "date_arrivee": date_arrivee,
        "date_depart": date_depart,
        "statut": "prévue",
    }

    # Créer réservation
    try:
        reservation = crud.create_reservation(db, data)
    except Exception as e:
        # Si malgré tout il y a une erreur d'unicité, utiliser un timestamp
        if "UNIQUE constraint" in str(e) or "IntegrityError" in str(type(e).__name__):
            id_res = f"{base_id}-{int(time.time())}"
            data["id_res"] = id_res
            reservation = crud.create_reservation(db, data)
        else:
            raise

    # Générer QR code
    qr_filename = f"{id_res}.png"
    qr_path = generate_qr(id_res, qr_filename)

    return {
        "status": "created",
        "id_reservation": reservation.id_res,
        "id_client": reservation.id_client,
        "qr_code_path": qr_path
    }
    


@app.post(
    "/check_reservation",
    tags=["Réservations"],
    summary="Vérifier une réservation",
    description="Récupère les détails d'une réservation existante avec les informations du client associé",
    response_description="Détails complets de la réservation et du client",
    responses={
        200: {
            "description": "Réservation trouvée",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "client": {
                            "id_client": "C-002",
                            "nom": "Dupont",
                            "prenom": "Jean",
                            "preferences": {"lit": "double"}
                        },
                        "reservation": {
                            "id_res": "R-C-002-2025-11-10",
                            "type_chambre": "simple",
                            "date_arrivee": "2025-11-10",
                            "date_depart": "2025-11-15",
                            "statut": "prévue"
                        }
                    }
                }
            }
        },
        404: {"description": "Réservation non trouvée"}
    }
)
def check_res(payload: CheckReservation, db: Session = Depends(get_db)):
    """
    Vérifie et récupère les détails d'une réservation.
    
    Args:
        payload: Contient l'ID de la réservation à vérifier
        db: Session de base de données
    
    Returns:
        Dictionnaire contenant les informations du client et de la réservation
    
    Raises:
        HTTPException: Si la réservation n'est pas trouvée (404)
    """
    # 1. Chercher la réservation
    reservation = crud.get_reservation(db, payload.id_res)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    
    # 2. Récupérer le client associé
    client = crud.ensure_client(db, reservation.id_client)

    return {
        "status": "ok",
        "client": {
            "id_client": client.id_client,
            "nom": client.nom,
            "prenom": client.prenom,
            "preferences": client.preferences
        },
        "reservation": {
            "id_res": reservation.id_res,
            "type_chambre": reservation.type_chambre,
            "date_arrivee": str(reservation.date_arrivee),
            "date_depart": str(reservation.date_depart),
            "statut": reservation.statut
        }
    }


@app.post(
    "/update_preferences",
    tags=["Clients"],
    summary="Mettre à jour les préférences d'un client",
    description="Met à jour les préférences d'un client existant (ex: type de lit, vue, étage, etc.)",
    response_description="Préférences mises à jour",
    responses={
        200: {
            "description": "Préférences mises à jour avec succès",
            "content": {
                "application/json": {
                    "example": {
                        "status": "updated",
                        "preferences": {
                            "lit": "double",
                            "vue": "mer",
                            "etage": "haut"
                        }
                    }
                }
            }
        },
        404: {"description": "Client non trouvé"}
    }
)
def update_prefs(payload: UpdatePreferences, db: Session = Depends(get_db)):
    """
    Met à jour les préférences d'un client.
    
    Args:
        payload: Contient l'ID du client et les nouvelles préférences
        db: Session de base de données
    
    Returns:
        Dictionnaire contenant le statut et les préférences mises à jour
    
    Raises:
        HTTPException: Si le client n'est pas trouvé (404)
    """
    client = crud.update_client_preferences(
        db,
        id_client=payload.id_client,
        new_prefs=payload.preferences
    )

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    return {"status": "updated", "preferences": client.preferences}


@app.post(
    "/verify_qr",
    tags=["QR Codes"],
    summary="Vérifier un QR code",
    description="Vérifie un QR code et retourne les informations de la réservation et du client associé",
    response_description="Informations de la réservation et du client",
    responses={
        200: {
            "description": "QR code valide",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "reservation": {
                            "id_res": "R-C-002-2025-11-10",
                            "type_chambre": "simple",
                            "date_arrivee": "2025-11-10",
                            "date_depart": "2025-11-15",
                            "statut": "prévue"
                        },
                        "client": {
                            "id_client": "C-002",
                            "nom": "Dupont",
                            "prenom": "Jean",
                            "nb_visites": 3,
                            "derniere_visite": "2025-10-15"
                        }
                    }
                }
            }
        },
        400: {"description": "qr_id manquant dans la requête"},
        404: {"description": "QR code invalide ou réservation non trouvée"}
    }
)
def verify_qr(data: dict, db: Session = Depends(get_db)):
    """
    Vérifie un QR code et retourne les informations associées.
    
    Args:
        data: Dictionnaire contenant le qr_id à vérifier
        db: Session de base de données
    
    Returns:
        Dictionnaire contenant les informations de la réservation et du client
    
    Raises:
        HTTPException: Si qr_id est manquant (400) ou si le QR code est invalide (404)
    """
    if "qr_id" not in data:
        raise HTTPException(status_code=400, detail="qr_id manquant")

    qr_id = data["qr_id"]

    reservation = crud.get_reservation_by_id(db, qr_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="QR code invalide")

    # Récupérer aussi les infos du client
    client = crud.get_client(db, reservation.id_client)

    return {
        "status": "ok",
        "reservation": {
            "id_res": reservation.id_res,
            "type_chambre": reservation.type_chambre,
            "date_arrivee": str(reservation.date_arrivee),
            "date_depart": str(reservation.date_depart),
            "statut": reservation.statut
        },
        "client": {
            "id_client": client.id_client,
            "nom": client.nom,
            "prenom": client.prenom,
            "nb_visites": client.nb_visites,
            "derniere_visite": str(client.derniere_visite)
        }
    }


@app.post(
    "/confirm_arrival",
    tags=["Réservations"],
    summary="Confirmer l'arrivée d'un client",
    description="Confirme l'arrivée d'un client en utilisant son QR code. Met à jour le statut de la réservation.",
    response_description="Confirmation de l'arrivée",
    responses={
        200: {
            "description": "Arrivée confirmée avec succès",
            "content": {
                "application/json": {
                    "example": {
                        "status": "arrival_confirmed",
                        "id_reservation": "R-C-002-2025-11-10",
                        "message": "Arrivée enregistrée. Vous pouvez aller récupérer vos clés."
                    }
                }
            }
        },
        404: {"description": "Réservation non trouvée"}
    }
)
def confirm_arrival_route(payload: schemas.VerifyQR, db: Session = Depends(get_db)):
    """
    Confirme l'arrivée d'un client.
    
    Args:
        payload: Contient le qr_id de la réservation
        db: Session de base de données
    
    Returns:
        Dictionnaire de confirmation avec l'ID de réservation et un message
    
    Raises:
        HTTPException: Si la réservation n'est pas trouvée (404)
    """
    reservation = crud.confirm_arrival(db, payload.qr_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Réservation inconnue")

    return {
        "status": "arrival_confirmed",
        "id_reservation": reservation.id_res,
        "message": "Arrivée enregistrée. Vous pouvez aller récupérer vos clés."
    }




@app.post(
    "/create_reservation_on_site",
    tags=["Réservations"],
    summary="Créer une réservation sur place",
    description="""
    Crée une réservation directement sur place (sans id_client préexistant).
    
    * Un nouveau client sera créé automatiquement
    * Un QR code sera généré pour la réservation
    * Utile pour les réservations faites directement à la réception
    """,
    response_description="Détails de la réservation créée sur place",
    responses={
        200: {
            "description": "Réservation créée avec succès",
            "content": {
                "application/json": {
                    "example": {
                        "status": "created_on_site",
                        "client_id": "C-17640829",
                        "reservation_id": "R-C-17640829-2025-11-20",
                        "qr_code_path": "app/static/qr/R-C-17640829-2025-11-20.png",
                        "message": "Réservation créée. Présentez ce QR code à votre arrivée."
                    }
                }
            }
        },
        422: {"description": "Erreur de validation des données"}
    }
)
def create_reservation_on_site(payload: schemas.CreateReservationOnSite, db: Session = Depends(get_db)):
    """
    Crée une réservation directement sur place.
    
    Args:
        payload: Données de la réservation (nom, prénom, dates, type de chambre)
        db: Session de base de données
    
    Returns:
        Dictionnaire contenant le statut, l'ID client, l'ID réservation, le chemin du QR code et un message
    """
    client, reservation = crud.create_reservation_on_site(db, payload)

    # Facultatif : on génère un QR code aussi pour les réservations sur place
    qr_id = reservation.id_res
    qr_bytes = qrcode.make(qr_id)
    qr_path = f"app/static/qr/{qr_id}.png"
    qr_bytes.save(qr_path)

    return {
        "status": "created_on_site",
        "client_id": client.id_client,
        "reservation_id": reservation.id_res,
        "qr_code_path": qr_path,
        "message": "Réservation créée. Présentez ce QR code à votre arrivée."
    }

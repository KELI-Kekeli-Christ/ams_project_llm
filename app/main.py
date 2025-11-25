from fastapi import FastAPI
from app import db
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from fastapi import HTTPException

from app.db import get_session
from app import crud
from app.schemas import CreateReservation, CheckReservation, UpdatePreferences

import qrcode
import os


app = FastAPI(title="CERIBot Server")
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

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/create_reservation")
def create_res(payload: CreateReservation, db: Session = Depends(get_db)):
    
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

    # Générer un id_res lisible
    id_res = f"R-{payload.id_client}-{payload.date_arrivee}"

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
    reservation = crud.create_reservation(db, data)

    # Générer QR code
    qr_filename = f"{id_res}.png"
    qr_path = generate_qr(id_res, qr_filename)

    return {
        "status": "created",
        "id_reservation": reservation.id_res,
        "id_client": reservation.id_client,
        "qr_code_path": qr_path
    }
    


@app.post("/check_reservation")
def check_res(payload: CheckReservation, db: Session = Depends(get_db)):
    
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


@app.post("/update_preferences")
def update_prefs(payload: UpdatePreferences, db: Session = Depends(get_db)):
    
    client = crud.update_client_preferences(
        db,
        id_client=payload.id_client,
        new_prefs=payload.preferences
    )

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    return {"status": "updated", "preferences": client.preferences}


@app.post("/verify_qr")
def verify_qr(data: dict, db: Session = Depends(get_db)):
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
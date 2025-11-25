from sqlalchemy.orm import Session
from app import models
from datetime import datetime


# -----------------------------
# 1. Vérifier ou créer un client
# -----------------------------
def ensure_client(db: Session, id_client: str, nom: str = "", prenom: str = ""):
    """
    Si le client existe, on le retourne.
    Sinon, on le crée dans la base.
    """
    c = db.get(models.Client, id_client)

    if not c:
        c = models.Client(
            id_client=id_client,
            nom=nom,
            prenom=prenom,
            nb_visites=1,
            derniere_visite=datetime.utcnow()
        )
        db.add(c)
        db.commit()
        db.refresh(c)
    else:
        # Si le client existe déjà, on met juste à jour sa dernière visite
        c.nb_visites += 1
        c.derniere_visite = datetime.utcnow()
        db.commit()
        db.refresh(c)

    return c


# -----------------------------
# 2. Créer une réservation
# -----------------------------
def create_reservation(db: Session, data: dict):
    """
    data doit contenir :
    - id_res
    - id_client
    - type_chambre
    - date_arrivee
    - date_depart
    """
    r = models.Reservation(**data)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


# -----------------------------
# 3. Lire une réservation
# -----------------------------
def get_reservation(db: Session, id_res: str):
    return db.get(models.Reservation, id_res)


# -----------------------------
# 4. Mise à jour des préférences client
# -----------------------------
def update_client_preferences(db: Session, id_client: str, new_prefs: dict):
    """
    Fusionne les nouvelles préférences avec celles existantes.
    """
    c = db.get(models.Client, id_client)
    if not c:
        return None
    
    # Merge des préférences sans effacer l’ancien contenu
    merged = dict(c.preferences or {})
    merged.update(new_prefs or {})

    c.preferences = merged
    db.commit()
    db.refresh(c)
    return c


def get_reservation_by_id(db: Session, id_res: str):
    return db.query(models.Reservation).filter(models.Reservation.id_res == id_res).first()

def get_client(db: Session, id_client: str):
    return db.query(models.Client).filter(models.Client.id_client == id_client).first()



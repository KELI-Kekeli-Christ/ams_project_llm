from sqlalchemy.orm import Session
from app import models
from datetime import date, datetime
import time

from app.models import Client, Reservation

# -----------------------------
# 1. Créer un nouveau client
# -----------------------------
def create_client(db: Session, nom: str, prenom: str):
    """
    Crée un nouveau client dans la base de données.
    Génère automatiquement un id_client unique.
    
    Returns:
        Client: Le client créé avec son id_client
    """
    # Générer un nouvel ID client unique
    new_id_client = f"C-{int(datetime.utcnow().timestamp())}"
    
    # Vérifier que l'ID n'existe pas déjà
    counter = 1
    while db.get(models.Client, new_id_client) is not None:
        new_id_client = f"C-{int(datetime.utcnow().timestamp())}-{counter}"
        counter += 1
        if counter > 1000:
            # En dernier recours, utiliser un timestamp plus précis
            new_id_client = f"C-{int(time.time() * 1000)}"
            break
    
    client = models.Client(
        id_client=new_id_client,
        nom=nom,
        prenom=prenom,
        nb_visites=0,
        derniere_visite=None
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    
    return client


# -----------------------------
# 2. Vérifier ou créer un client
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
    try:
        db.commit()
        db.refresh(r)
    except Exception as e:
        db.rollback()
        raise
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


def confirm_arrival(db: Session, id_res: str):
    reservation = db.query(Reservation).filter(Reservation.id_res == id_res).first()
    if not reservation:
        return None

    # Mise à jour du statut
    reservation.statut = "arrivé"

    # Mise à jour de l'heure d'arrivée (tu peux ajouter ce champ dans modèle)
    # reservation.arrivee_effective = datetime.utcnow()  # si tu l'ajoutes

    # Mise à jour du client (fidélisation)
    client = db.query(Client).filter(Client.id_client == reservation.id_client).first()
    if client:
        client.nb_visites += 1
        client.derniere_visite = datetime.utcnow()

    db.commit()
    db.refresh(reservation)
    return reservation


def create_reservation_on_site(db: Session, data):
    # Générer un nouvel ID client
    new_id_client = f"C-{datetime.utcnow().timestamp()}"[:10].replace('.', '')

    # 1. Créer le client
    client = Client(
        id_client=new_id_client,
        nom=data.nom,
        prenom=data.prenom,
        nb_visites=0,
        derniere_visite=None
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    # 2. Générer ID réservation unique
    base_id = f"R-{client.id_client}-{data.date_arrivee}"
    id_res = base_id
    
    # Vérifier si une réservation avec cet ID existe déjà
    counter = 1
    existing = db.query(Reservation).filter(Reservation.id_res == id_res).first()
    while existing is not None:
        id_res = f"{base_id}-{counter}"
        counter += 1
        existing = db.query(Reservation).filter(Reservation.id_res == id_res).first()
        if counter > 1000:
            # En dernier recours, utiliser un timestamp
            id_res = f"{base_id}-{int(time.time())}"
            break

    # 3. Créer la réservation
    reservation = Reservation(
        id_res=id_res,
        id_client=client.id_client,
        type_chambre=data.type_chambre,
        date_arrivee=date.fromisoformat(data.date_arrivee),
        date_depart=date.fromisoformat(data.date_depart),
        statut="en attente"
    )
    db.add(reservation)
    try:
        db.commit()
        db.refresh(reservation)
    except Exception as e:
        db.rollback()
        raise

    return client, reservation

from sqlalchemy import Column, String, Integer, Date, DateTime, JSON, ForeignKey
from datetime import datetime
from app.db import Base

class Client(Base):
    __tablename__ = "clients"

    id_client = Column(String, primary_key=True)  # ex: "C-001"
    nom = Column(String)
    prenom = Column(String)
    langue_pref = Column(String, default="fr")
    # Mémoire “goûts” du client, simple et flexible
    preferences = Column(JSON, default={})        # ex: {"activites":["spa","rando"], "repas":["veg"]}
    nb_visites = Column(Integer, default=0)
    derniere_visite = Column(DateTime, default=datetime.utcnow)

class Reservation(Base):
    __tablename__ = "reservations"

    id_res = Column(String, primary_key=True)      # ex: "R-C-001-2025-11-10"
    id_client = Column(String, ForeignKey("clients.id_client"))
    type_chambre = Column(String)                  # "Simple" / "Double" / "Suite"
    date_arrivee = Column(Date)
    date_depart = Column(Date)
    statut = Column(String, default="prévue")      # "prévue" | "arrivée" | "conflit"

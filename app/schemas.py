from pydantic import BaseModel
from typing import Optional, Dict

# --------- Requêtes ---------

class CreateReservation(BaseModel):
    id_client: str
    nom: Optional[str] = ""
    prenom: Optional[str] = ""
    type_chambre: str
    date_arrivee: str   # tu pourrais plus tard les typer en date
    date_depart: str

class CheckReservation(BaseModel):
    id_res: str

class UpdatePreferences(BaseModel):
    id_client: str
    preferences: Dict

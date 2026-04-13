"""
Service de réservation conversationnelle pas à pas.
Le robot pose une question à la fois et collecte les réponses vocales.
"""
import json
import sqlite3
import uuid
import os
from datetime import datetime, timedelta
from openai import OpenAI
from services.location import get_heure_date

CONV_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'conversation_reservations.db')

_client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=os.getenv("HF_API_KEY", "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"),
)

# Définition des étapes de la conversation
STEPS = [
    {
        "step": "nom",
        "question": "Quel est votre nom de famille ?",
        "field": "nom",
        "prompt": (
            "Extrait le nom de famille (nom) depuis ce texte : '{text}'. "
            "Retourne UNIQUEMENT le nom, sans ponctuation ni explication."
        ),
        "valid": lambda v: bool(v and v.lower() not in ("inconnu", "") and len(v) > 1),
    },
    {
        "step": "prenom",
        "question": "Quel est votre prénom ?",
        "field": "prenom",
        "prompt": (
            "Extrait le prénom depuis ce texte : '{text}'. "
            "Retourne UNIQUEMENT le prénom, sans ponctuation ni explication."
        ),
        "valid": lambda v: bool(v and v.lower() not in ("inconnu", "") and len(v) > 1),
    },
    {
        "step": "type_chambre",
        "question": "Quel type de chambre souhaitez-vous ? Simple, double ou suite ?",
        "field": "type_chambre",
        "prompt": (
            "Depuis ce texte : '{text}', détermine le type de chambre demandé. "
            "Retourne UNIQUEMENT l'un de ces mots exacts : simple, double, suite."
        ),
        "valid": lambda v: v in ("simple", "double", "suite"),
    },
    {
        "step": "date_arrivee",
        "question": "Quelle est votre date d'arrivée ?",
        "field": "date_arrivee",
        "prompt": (
            "Depuis ce texte : '{text}', extrais la date mentionnée. "
            "La date d'aujourd'hui est {date}. "
            "Convertis les dates relatives (demain, dans 3 jours, lundi prochain…) en date absolue. "
            "Retourne UNIQUEMENT la date au format YYYY-MM-DD, rien d'autre."
        ),
        "valid": lambda v: bool(v and len(v) == 10 and v[4] == '-' and v[7] == '-'),
    },
    {
        "step": "date_depart",
        "question": "Quelle est votre date de départ ?",
        "field": "date_depart",
        "prompt": (
            "Depuis ce texte : '{text}', extrais la date de départ mentionnée. "
            "La date d'aujourd'hui est {date}. "
            "Convertis les dates relatives en date absolue. "
            "Retourne UNIQUEMENT la date au format YYYY-MM-DD, rien d'autre."
        ),
        "valid": lambda v: bool(v and len(v) == 10 and v[4] == '-' and v[7] == '-'),
    },
]

STEP_LABELS = {
    "nom": "Étape 1/5 : Nom",
    "prenom": "Étape 2/5 : Prénom",
    "type_chambre": "Étape 3/5 : Type de chambre",
    "date_arrivee": "Étape 4/5 : Date d'arrivée",
    "date_depart": "Étape 5/5 : Date de départ",
    "email": "Étape finale : Email de confirmation",
}


# ─── DB helpers ───────────────────────────────────────────────────────────────

def _init_db():
    conn = sqlite3.connect(CONV_DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            session_id TEXT PRIMARY KEY,
            step       TEXT NOT NULL,
            data       TEXT NOT NULL,
            expires_at TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


def _get(session_id):
    _init_db()
    conn = sqlite3.connect(CONV_DB_PATH)
    row = conn.execute(
        'SELECT step, data FROM conversations WHERE session_id=? AND expires_at>?',
        (session_id, datetime.now())
    ).fetchone()
    conn.close()
    if row:
        return row[0], json.loads(row[1])
    return None, None


def _save(session_id, step, data):
    _init_db()
    exp = datetime.now() + timedelta(hours=1)
    conn = sqlite3.connect(CONV_DB_PATH)
    conn.execute(
        'INSERT OR REPLACE INTO conversations (session_id, step, data, expires_at) VALUES (?,?,?,?)',
        (session_id, step, json.dumps(data), exp)
    )
    conn.commit()
    conn.close()


def _delete(session_id):
    _init_db()
    conn = sqlite3.connect(CONV_DB_PATH)
    conn.execute('DELETE FROM conversations WHERE session_id=?', (session_id,))
    conn.commit()
    conn.close()


# ─── LLM extraction ───────────────────────────────────────────────────────────

def _extract_field(step_info, transcript):
    """Extrait une valeur unique depuis le transcript via le LLM."""
    current_date = get_heure_date()
    prompt = step_info["prompt"].format(text=transcript, date=current_date)
    try:
        completion = _client.chat.completions.create(
            model="meta-llama/Llama-3.1-8B-Instruct",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu es un extracteur d'informations précis. "
                        "Retourne UNIQUEMENT la valeur demandée, sans aucune explication."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=30,
        )
        value = completion.choices[0].message.content.strip().strip('"\'.,;:!? ')
        if step_info["field"] == "type_chambre":
            value = value.lower()
        return value
    except Exception as e:
        print(f"[conv] Erreur extraction LLM: {e}")
        return None


# ─── Public API ───────────────────────────────────────────────────────────────

def start_conversation():
    """Démarre une nouvelle conversation et retourne la première question."""
    session_id = f"conv_{uuid.uuid4().hex[:8]}"
    _save(session_id, "nom", {})
    return {
        "session_id": session_id,
        "step": "nom",
        "label": STEP_LABELS["nom"],
        "question": STEPS[0]["question"],
    }


def get_conversation_state(session_id):
    """Retourne l'état courant d'une conversation."""
    step, data = _get(session_id)
    if not step:
        return None
    return {"step": step, "data": data, "label": STEP_LABELS.get(step, "")}


def process_answer(session_id, transcript):
    """
    Traite une réponse vocale transcrite, avance à l'étape suivante et
    retourne la prochaine question ou indique que la saisie email est requise.
    """
    step_name, data = _get(session_id)
    if step_name is None:
        return {"status": "error", "error": "Session expirée ou introuvable"}

    step_info = next((s for s in STEPS if s["step"] == step_name), None)
    if not step_info:
        return {"status": "error", "error": f"Étape inconnue : {step_name}"}

    value = _extract_field(step_info, transcript)

    if not value or not step_info["valid"](value):
        # Demander à nouveau
        return {
            "status": "retry",
            "step": step_name,
            "label": STEP_LABELS.get(step_name, ""),
            "question": f"Je n'ai pas bien compris. {step_info['question']}",
            "transcript": transcript,
        }

    data[step_info["field"]] = value
    current_idx = next(i for i, s in enumerate(STEPS) if s["step"] == step_name)
    next_idx = current_idx + 1

    if next_idx < len(STEPS):
        next_step = STEPS[next_idx]
        _save(session_id, next_step["step"], data)
        return {
            "status": "continue",
            "step": next_step["step"],
            "label": STEP_LABELS[next_step["step"]],
            "question": next_step["question"],
            "transcript": transcript,
            "collected": data,
        }

    # Toutes les étapes vocales terminées → besoin de l'email
    _save(session_id, "email", data)
    return {
        "status": "need_email",
        "step": "email",
        "label": STEP_LABELS["email"],
        "question": (
            "Parfait ! Veuillez entrer votre adresse email sur la tablette "
            "pour recevoir votre confirmation de réservation."
        ),
        "transcript": transcript,
        "collected": data,
    }


def finalize_reservation(session_id, email):
    """
    Finalise la réservation : sauvegarde en DB et envoie le mail de confirmation.
    L'email est celui saisi par l'utilisateur sur la tablette.
    """
    step_name, data = _get(session_id)
    if data is None:
        return {"status": "error", "error": "Session expirée ou introuvable"}

    data["email"] = email

    # Vérification des champs obligatoires avant de sauvegarder
    required = ["nom", "prenom", "type_chambre", "date_arrivee", "date_depart"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return {
            "status": "error",
            "error": f"Champs manquants : {', '.join(missing)}",
        }

    # Validation date_depart > date_arrivee
    try:
        d_arr = datetime.strptime(data["date_arrivee"], "%Y-%m-%d")
        d_dep = datetime.strptime(data["date_depart"], "%Y-%m-%d")
        if d_dep <= d_arr:
            return {
                "status": "error",
                "error": "La date de départ doit être postérieure à la date d'arrivée",
            }
    except ValueError as e:
        return {"status": "error", "error": f"Format de date invalide : {e}"}

    # Création de la réservation via le service existant
    from services.make_reservation import make_reservation_from_data
    result = make_reservation_from_data(data)

    if result.get("status") == "success" or result.get("local"):
        reservation_id = result.get("reservation_id", "N/A")

        # Envoi de l'email de confirmation au client (et gestionnaire)
        try:
            from services.email import send_reservation_confirmation
            email_result = send_reservation_confirmation(data)
            email_sent = email_result.get("success", False)
        except Exception as e:
            print(f"[conv] Erreur envoi email: {e}")
            email_sent = False

        _delete(session_id)
        return {
            "status": "success",
            "message": "Réservation confirmée avec succès !",
            "reservation_id": reservation_id,
            "email_sent": email_sent,
            "data": data,
        }

    return {
        "status": "error",
        "error": result.get("error", "Erreur lors de la création de la réservation"),
    }

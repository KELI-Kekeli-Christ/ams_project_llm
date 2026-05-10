"""
Service de réservation conversationnelle pas à pas.
Le robot pose une question à la fois et collecte les réponses vocales.
"""
import json
import sqlite3
import uuid
import os
import re
import threading
from datetime import datetime, timedelta
from openai import OpenAI
from services.location import get_heure_date


def _normalize_room_type(text):
    """Normalise les variations de transcription vers simple/double/suite."""
    if not text:
        return None

    t = text.lower().strip()
    # Nettoyage léger des ponctuations fréquentes de transcription
    for ch in ("!", "?", ".", ",", ";", ":", "'", '"'):
        t = t.replace(ch, " ")
    t = " ".join(t.split())

    simple_tokens = (
        "simple", "single", "solo", "une place", "1 place", "standard"
    )
    double_tokens = (
        "double", "deux", "2 places", "2 place", "deux places", "matrimoniale"
    )
    suite_tokens = (
        "suite", "deluxe", "lux", "luxe", "premium", "executive"
    )

    if any(tok in t for tok in simple_tokens):
        return "simple"
    if any(tok in t for tok in double_tokens):
        return "double"
    if any(tok in t for tok in suite_tokens):
        return "suite"

    return None


def _normalize_date_value(text, base_date=None):
    """Normalise une date transcrite en format YYYY-MM-DD si possible."""
    if not text:
        return None

    base = base_date or datetime.now()
    t = text.lower().strip()
    t = t.replace("’", "'")

    weekday_map = {
        "lundi": 0,
        "mardi": 1,
        "mercredi": 2,
        "jeudi": 3,
        "vendredi": 4,
        "samedi": 5,
        "dimanche": 6,
    }

    month_map = {
        "janvier": 1,
        "fevrier": 2,
        "février": 2,
        "mars": 3,
        "avril": 4,
        "mai": 5,
        "juin": 6,
        "juillet": 7,
        "aout": 8,
        "août": 8,
        "septembre": 9,
        "octobre": 10,
        "novembre": 11,
        "decembre": 12,
        "décembre": 12,
    }

    # Déjà au bon format
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", t)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    # Formats classiques FR: 12/06/2026, 12-06-2026, 12/06
    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", t)
    if m:
        day = int(m.group(1))
        month = int(m.group(2))
        year_raw = m.group(3)
        year = base.year
        if year_raw:
            year = int(year_raw)
            if year < 100:
                year += 2000
        try:
            return datetime(year, month, day).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Formats FR avec mois en toutes lettres: "le 5 juin", "5 juin 2026"
    m = re.search(
        r"\b(?:le\s+)?(\d{1,2})(?:er)?\s+(janvier|fevrier|février|mars|avril|mai|juin|juillet|aout|août|septembre|octobre|novembre|decembre|décembre)(?:\s+(\d{4}))?\b",
        t,
    )
    if m:
        day = int(m.group(1))
        month = month_map.get(m.group(2))
        year = int(m.group(3)) if m.group(3) else base.year
        if month:
            try:
                parsed = datetime(year, month, day)
                if not m.group(3) and parsed.date() < base.date():
                    parsed = datetime(year + 1, month, day)
                return parsed.strftime("%Y-%m-%d")
            except ValueError:
                pass

    # Expressions relatives avec jour de semaine : "jeudi prochain", "lundi prochain"
    m = re.search(r"\b(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\s+prochain(?:e|es|s)?\b", t)
    if m:
        target_weekday = weekday_map[m.group(1)]
        days_ahead = (target_weekday - base.weekday() + 7) % 7
        if days_ahead == 0:
            days_ahead = 7
        return (base + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    # "semaine prochaine" : on prend le même jour de semaine à J+7
    if "semaine prochaine" in t:
        return (base + timedelta(days=7)).strftime("%Y-%m-%d")

    # Expressions relatives simples
    if "aujourd" in t:
        return base.strftime("%Y-%m-%d")
    if "apres-demain" in t or "après-demain" in t:
        return (base + timedelta(days=2)).strftime("%Y-%m-%d")
    if "demain" in t:
        return (base + timedelta(days=1)).strftime("%Y-%m-%d")

    m = re.search(r"dans\s+(\d{1,3})\s+jour", t)
    if m:
        return (base + timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d")

    return None

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
            "Depuis ce texte : '{text}', extrais TOUT MOT ou PHRASE que la personne a dit. "
            "Retourne juste le texte transcrit, sans filtrer, sans jugement. "
            "C'est un identifiant brut."
        ),
        "valid": lambda v: bool(v and v.strip()),  # Accept anything that's not empty
    },
    {
        "step": "prenom",
        "question": "Quel est votre prénom ?",
        "field": "prenom",
        "prompt": (
            "Depuis ce texte : '{text}', extrais TOUT MOT ou PHRASE que la personne a dit. "
            "Retourne juste le texte transcrit, sans filtrer, sans jugement. "
            "C'est un identifiant brut supplémentaire."
        ),
        "valid": lambda v: bool(v and v.strip()),  # Accept anything that's not empty
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
    # Cas spécial type de chambre: normalisation locale avant appel LLM
    if step_info["field"] == "type_chambre":
        direct = _normalize_room_type(transcript)
        if direct:
            return direct

    # Cas spécial dates: parser local avant appel LLM
    if step_info["field"] in ("date_arrivee", "date_depart"):
        direct_date = _normalize_date_value(transcript)
        if direct_date:
            return direct_date

    current_date = get_heure_date()
    prompt = step_info["prompt"].format(text=transcript, date=current_date)
    try:
        if step_info["field"] == "type_chambre":
            system_content = (
                "Tu es un classificateur. "
                "Retourne UNIQUEMENT un mot parmi: simple, double, suite. "
                "Aucune autre sortie."
            )
            max_tokens = 10
        elif step_info["field"] in ("date_arrivee", "date_depart"):
            system_content = (
                "Tu es un extracteur de dates. "
                "Retourne UNIQUEMENT une date au format YYYY-MM-DD. "
                "Si la date est relative (demain, dans X jours), convertis-la. "
                "Aucune autre sortie."
            )
            max_tokens = 20
        else:
            system_content = (
                "Tu es un extracteur d'informations. "
                "Retourne UNIQUEMENT le texte ou phrase, sans aucune explication ou filtrage."
            )
            max_tokens = 50

        completion = _client.chat.completions.create(
            model="meta-llama/Llama-3.1-8B-Instruct",
            messages=[
                {
                    "role": "system",
                    "content": system_content,
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
        )
        value = completion.choices[0].message.content.strip().strip('"\'.,;:!? ')
        if step_info["field"] == "type_chambre":
            normalized = _normalize_room_type(value)
            if normalized:
                return normalized
            return None
        if step_info["field"] in ("date_arrivee", "date_depart"):
            normalized_date = _normalize_date_value(value)
            if normalized_date:
                return normalized_date
            return None
        # Pour nom/prenom, accepter tout ce qui reste (même juste le transcript brut)
        if not value and transcript:
            value = transcript.strip()
        return value
    except Exception as e:
        print(f"[conv] Erreur extraction LLM: {e}")
        if step_info["field"] == "type_chambre":
            return _normalize_room_type(transcript)
        if step_info["field"] in ("date_arrivee", "date_depart"):
            return _normalize_date_value(transcript)
        # Fallback: retourner le transcript lui-même
        return transcript.strip() if transcript else None


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


def update_conversation_data(session_id, updates):
    """
    Met à jour les champs collectés pour une session en cours.
    `updates` doit être un dict contenant les clés à modifier (nom, prenom, date_arrivee, ...).
    Retourne un dict avec le nouvel état ou une erreur.
    """
    step, data = _get(session_id)
    if data is None:
        return {"status": "error", "error": "Session introuvable ou expirée"}
    if not isinstance(updates, dict):
        return {"status": "error", "error": "Données d'update invalides"}
    # Fusionner et sauvegarder sous l'étape email (on reste à l'étape finale)
    data.update(updates)
    _save(session_id, "email", data)
    return {"status": "success", "data": data}


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
    print(f"[process] Étape '{step_name}' | transcript='{transcript}' | extracted='{value}' | valid={step_info['valid'](value) if value else False}")

    if not value or not step_info["valid"](value):
        # Demander à nouveau
        print(f"[process] ❌ Réponse rejetée pour '{step_name}' - valeur='{value}'")
        return {
            "status": "retry",
            "step": step_name,
            "label": STEP_LABELS.get(step_name, ""),
            "question": f"Je n'ai pas bien compris. {step_info['question']}",
            "transcript": transcript,
            "collected": data,
        }

    data[step_info["field"]] = value
    current_idx = next(i for i, s in enumerate(STEPS) if s["step"] == step_name)
    next_idx = current_idx + 1
    print(f"[process] ✅ Réponse acceptée pour '{step_name}' | valeur='{value}' | progression {current_idx+1}/5 → {next_idx+1}/5")

    if next_idx < len(STEPS):
        next_step = STEPS[next_idx]
        _save(session_id, next_step["step"], data)
        print(f"[process] Passage à l'étape: {next_step['step']}")
        return {
            "status": "continue",
            "step": next_step["step"],
            "label": STEP_LABELS[next_step["step"]],
            "question": next_step["question"],
            "transcript": transcript,
            "collected": data,
        }

    # Toutes les étapes vocales terminées → besoin de l'email
    print(f"[process] ✅ TOUTES LES ÉTAPES COMPLÉTÉES! Données finales: {data}")
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

        # Envoi de l'email en arrière-plan (asynchrone) pour ne pas bloquer la réponse
        def _send_email_async(payload):
            try:
                from services.email import send_reservation_confirmation
                email_result = send_reservation_confirmation(payload)
                print(f"[conv] ✅ Email result: {email_result}")
            except Exception as e:
                print(f"[conv] ❌ Erreur envoi email: {e}")
                import traceback
                traceback.print_exc()

        print(f"[conv] Lancement envoi email en arrière-plan pour {email}...")
        threading.Thread(target=_send_email_async, args=(data.copy(),), daemon=True).start()

        _delete(session_id)
        return {
            "status": "success",
            "message": "Réservation confirmée avec succès !",
            "reservation_id": reservation_id,
            "email_sent": False,
            "email_pending": True,
            "data": data,
        }

    return {
        "status": "error",
        "error": result.get("error", "Erreur lors de la création de la réservation"),
    }

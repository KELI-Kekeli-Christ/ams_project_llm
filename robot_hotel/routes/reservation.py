"""
Routes Réservation : création, validation, confirmation
"""
import re
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template
from services.whisper import transcribe_audio
from services.record import get_last_recorded_file_path
from services.make_reservation import (
    make_reservation,
    make_reservation_from_data,
    get_extracted_reservation,
    store_validated_reservation,
)
from services.chat import get_reservation_session, delete_reservation_session, save_reservation_session
from services.email import send_validation_email, send_reservation_confirmation

bp = Blueprint('reservation', __name__)


def get_whisper_model():
    from flask import current_app
    return current_app.config.get('whisper_model')


@bp.route("/make_reservation", methods=["POST"])
def handle_make_reservation():
    """Crée une réservation à partir d'un fichier audio"""
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file provided", "status": "error"}), 400

        uploaded_file = request.files["file"]
        if uploaded_file.filename == "":
            return jsonify({"error": "No file selected", "status": "error"}), 400

        model = get_whisper_model()
        transcribe_result = transcribe_audio(model, uploaded_file)
        transcript = transcribe_result.get("text", "")
        language = transcribe_result.get("language", "")

        if not transcript or not transcript.strip():
            return jsonify({
                "error": "Le transcript est vide. Le fichier audio ne contient peut-être pas de parole.",
                "status": "error"
            }), 400

        result = make_reservation(transcript)
        result["transcript"] = transcript
        result["language"] = language
        result["audio_filename"] = uploaded_file.filename

        return jsonify(result), 200

    except Exception as e:
        print(f"❌ Erreur : {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": f"Erreur serveur : {str(e)}",
            "status": "error"
        }), 500


@bp.route("/make_reservation_from_last", methods=["POST"])
def handle_make_reservation_from_last():
    """Crée une réservation à partir du dernier fichier audio enregistré"""
    try:
        path = get_last_recorded_file_path()
        if not path:
            return jsonify({
                "error": "Aucun enregistrement récent. Enregistrez d'abord avec le micro.",
                "status": "error"
            }), 400

        model = get_whisper_model()
        transcribe_result = transcribe_audio(model, path)
        transcript = transcribe_result.get("text", "").strip()
        if not transcript:
            return jsonify({
                "error": "Le dernier enregistrement est vide ou sans parole.",
                "status": "error"
            }), 400

        result = make_reservation(transcript)
        result["transcript"] = transcript
        result["audio_file"] = path
        return jsonify(result), 200
    except Exception as e:
        print(f"Erreur make_reservation_from_last: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e), "status": "error"}), 500


@bp.route("/validate_reservation_form", methods=["POST"])
def validate_reservation_form():
    """Valide les informations de réservation envoyées depuis la tablette"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided", "status": "error"}), 400

        session_id = data.get('session_id')
        if not session_id:
            return jsonify({"error": "Session ID requis", "status": "error"}), 400

        audio_data = get_extracted_reservation(session_id)
        if not audio_data:
            return jsonify({"error": "Aucune donnée audio trouvée pour cette session", "status": "error"}), 400

        validated_data = audio_data.copy()
        corrections = data.get('corrections', {})

        for field, value in corrections.items():
            if value and value != "inconnu":
                validated_data[field] = value

        client_email = data.get('email', '').strip()
        if client_email:
            validated_data['email'] = client_email

        required_fields = ['nom', 'prenom', 'type_chambre', 'date_arrivee', 'date_depart']
        missing_fields = [f for f in required_fields if not validated_data.get(f) or validated_data.get(f) == "inconnu"]

        if missing_fields:
            return jsonify({
                "error": f"Champs obligatoires manquants: {', '.join(missing_fields)}",
                "status": "error",
                "missing_fields": missing_fields
            }), 400

        valid_room_types = ['simple', 'double', 'suite']
        if validated_data.get('type_chambre') not in valid_room_types:
            return jsonify({
                "error": f"Type de chambre invalide. Valeurs acceptées: {', '.join(valid_room_types)}",
                "status": "error"
            }), 400

        date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        for date_field in ['date_arrivee', 'date_depart']:
            date_value = validated_data.get(date_field)
            if not date_pattern.match(date_value):
                return jsonify({
                    "error": f"Format de date invalide pour {date_field}. Utilisez YYYY-MM-DD",
                    "status": "error"
                }), 400

        try:
            date_arrivee = datetime.strptime(validated_data['date_arrivee'], '%Y-%m-%d')
            date_depart = datetime.strptime(validated_data['date_depart'], '%Y-%m-%d')
            if date_depart <= date_arrivee:
                return jsonify({
                    "error": "La date de départ doit être postérieure à la date d'arrivée",
                    "status": "error"
                }), 400
        except ValueError as e:
            return jsonify({"error": f"Erreur dans le format des dates: {str(e)}", "status": "error"}), 400

        send_by_email = data.get('send_by_email', False)

        if send_by_email:
            if not client_email:
                return jsonify({"error": "Email requis pour l'envoi par email", "status": "error"}), 400
            email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
            if not email_pattern.match(client_email):
                return jsonify({"error": "Format d'email invalide", "status": "error"}), 400

            email_result = send_validation_email(
                client_email=client_email,
                client_name=validated_data.get('nom', ''),
                client_prenom=validated_data.get('prenom', ''),
                reservation_data=validated_data,
                session_id=session_id
            )

            if email_result.get('status') == 'success':
                return jsonify({
                    "status": "email_sent",
                    "message": "Données de réservation envoyées par email avec succès",
                    "email_result": email_result,
                    "session_id": session_id
                }), 200
            else:
                return jsonify({
                    "error": f"Erreur lors de l'envoi par email: {email_result.get('message')}",
                    "status": "error",
                    "email_result": email_result
                }), 500
        else:
            validated_data['validated_at'] = datetime.now().isoformat()
            validated_data['status'] = 'validated'
            success = store_validated_reservation(session_id, validated_data)
            if not success:
                return jsonify({"error": "Erreur lors de la sauvegarde des données validées", "status": "error"}), 500

            return jsonify({
                "status": "success",
                "message": "Données de réservation validées avec succès",
                "validated_data": validated_data,
                "session_id": session_id
            }), 200

    except Exception as e:
        print(f"❌ Erreur validation formulaire: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Erreur serveur: {str(e)}", "status": "error"}), 500


@bp.route('/validate')
def validate_reservation():
    """Page de validation de réservation"""
    session_id = request.args.get('session_id')
    if not session_id:
        return render_template('error.html', message="Session ID manquant"), 400

    user_data, current_step = get_reservation_session(session_id)
    if not user_data or current_step != 'complete':
        user_data = get_extracted_reservation(session_id)
        if user_data:
            current_step = 'complete'

    if not user_data or current_step != 'complete':
        return render_template('error.html', message="Session de réservation invalide ou expirée"), 400

    return render_template('validation.html', session_id=session_id, user_data=user_data)


@bp.route('/get_reservation_session')
def get_reservation_session_endpoint():
    """Récupère les données de session de réservation"""
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({"error": "Session ID manquant"}), 400

    user_data, current_step = get_reservation_session(session_id)
    if not user_data:
        user_data = get_extracted_reservation(session_id)
        current_step = 'complete' if user_data else None

    if not user_data:
        return jsonify({"error": "Session non trouvée"}), 404

    return jsonify({
        "session_id": session_id,
        "user_data": user_data,
        "current_step": current_step or 'complete'
    })


@bp.route('/confirm_reservation', methods=['POST'])
def confirm_reservation():
    """Confirme et finalise la réservation"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Aucune donnée fournie"}), 400

        session_id = data.get('session_id')
        send_email = data.get('send_email', False)
        form_data = data.get('user_data', {})

        if not session_id:
            return jsonify({"error": "Session ID manquant"}), 400

        user_data, current_step = get_reservation_session(session_id)
        if not user_data or not user_data.get('nom') or not user_data.get('prenom'):
            extracted_data = get_extracted_reservation(session_id)
            if extracted_data:
                user_data = extracted_data
                current_step = "complete"

        # Fusionner les donnees du formulaire (email, corrections) si fournies
        if form_data:
            user_data = (user_data or {}).copy()
            for k, v in form_data.items():
                if v is not None and str(v).strip():
                    user_data[k] = str(v).strip()

        if not user_data:
            return jsonify({"error": "Session de réservation invalide - aucune donnée trouvée"}), 400

        if not user_data.get('nom') or user_data.get('nom') == 'inconnu':
            return jsonify({"error": "Nom manquant ou invalide dans les données de réservation"}), 400
        if not user_data.get('prenom') or user_data.get('prenom') == 'inconnu':
            return jsonify({"error": "Prénom manquant ou invalide dans les données de réservation"}), 400

        reservation_result = make_reservation_from_data(user_data)

        if reservation_result.get('success') or reservation_result.get('status') == 'success' or reservation_result.get('local'):
            if send_email:
                try:
                    email_result = send_reservation_confirmation(user_data)
                    if email_result.get('success'):
                        print("📧 Emails de confirmation envoyés (client + gestionnaire)")
                    else:
                        print("⚠️ Email non envoyé:", email_result.get('error', 'inconnu'))
                except Exception as e:
                    print("⚠️ Erreur envoi email:", e)
            delete_reservation_session(session_id)
            return jsonify({
                "success": True,
                "message": "Réservation confirmée avec succès !",
                "reservation_id": reservation_result.get('reservation_id', 'N/A')
            })
        else:
            error_msg = reservation_result.get('error', 'Échec de la création de la réservation')
            return jsonify({"error": error_msg}), 500

    except Exception as e:
        print(f"❌ Erreur confirmation réservation: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Erreur interne du serveur: {str(e)}"}), 500


@bp.route('/reservation_success')
def reservation_success():
    """Page de succès après confirmation"""
    reservation_id = request.args.get('reservation_id')
    return render_template('success.html', reservation_id=reservation_id)


@bp.route('/update_reservation_session', methods=['POST'])
def update_reservation_session():
    """Met à jour les données de session de réservation"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        new_data = data.get('data', {})

        if not session_id:
            return jsonify({"error": "Session ID manquant"}), 400

        existing_data, current_step = get_reservation_session(session_id)
        if existing_data:
            existing_data.update(new_data)
        else:
            existing_data = new_data

        save_reservation_session(session_id, existing_data, current_step or "complete")

        return jsonify({
            "success": True,
            "message": "Données mises à jour",
            "data": existing_data
        })
    except Exception as e:
        print(f"Erreur mise à jour session: {e}")
        return jsonify({"error": str(e)}), 500

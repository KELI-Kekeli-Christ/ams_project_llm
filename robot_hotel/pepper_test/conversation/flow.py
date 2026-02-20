#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Main conversation flow for pepper_test module.
Handles the interactive conversation loop with the Pepper robot.
"""

import time
import requests
from api.client import (
    record_audio_manual,
    transcribe_audio,
    chat_with_api,
    make_reservation_with_api,
    is_reservation_request,
    is_qr_scan_request,
    scan_qr_code_with_api
)
from api.flask_check import API_CONFIG
from utils.helpers import safe_print
from utils.language import map_language_code_to_ald_label
from ui.tablet_html import create_tablet_html
from conversation.context import ConversationContext


# Configuration du robot
ROBOT_CONFIG = {
    "ip": "127.0.0.1",
    "port": 43817,
    "language": "French",
}


def run_conversation(robot):
    """
    Fonction principale de la conversation interactive
    
    Args:
        robot: Instance de RobotManager
    """
    from pepper.robot_manager import TEST_MESSAGE as _TEST_MSG
    
    print("=" * 60)
    print("Robot Pepper - Mode Conversation Interactive")
    print("=" * 60)
    print("Configuration:")
    print("  IP: {}".format(ROBOT_CONFIG["ip"]))
    print("  Port: {}".format(ROBOT_CONFIG["port"]))
    print("  Langue: {}".format(ROBOT_CONFIG["language"]))
    print("=" * 60)
    
    # Initialiser le contexte de conversation
    conversation_context = ConversationContext()
    
    # Variable pour suivre la dernière personne reconnue
    last_recognized_name = None
    
    # Démarrer la reconnaissance faciale
    recognized_name = None
    if robot.video and robot.camera_url:
        print("Demarrage du flux video continu pour la detection faciale...")
        if robot.start_continuous_video_stream():
            print("Reconnaissance faciale en cours depuis le flux video continu...")
            recognized_name = robot.recognize_face_from_stream(max_attempts=15, delay=0.3)
        else:
            print("Impossible de demarrer le flux video, utilisation de la capture unique...")
            recognized_name = robot.recognize_face_from_camera()
    elif robot.video:
        print("Reconnaissance faciale en cours (capture unique)...")
        recognized_name = robot.recognize_face_from_camera()
    
    # Message d'accueil personnalisé
    if recognized_name:
        welcome_message = "Ah bonjour {} !".format(recognized_name)
        print("Personne reconnue: {}".format(recognized_name))
        if robot.tts:
            robot.say(welcome_message, language=ROBOT_CONFIG["language"])
    else:
        print("👤 Aucune personne reconnue - pas de message d'accueil")
    
    # Afficher l'interface initiale
    if robot.tablet:
        print("🖥️ Chargement de l'interface sur la tablette...")
        greeting_text = "Ah bonjour {} !".format(recognized_name) if recognized_name else "Prêt à vous aider"
        html_content = create_tablet_html(
            title="Pepper",
            message=greeting_text,
            subtitle="",
            status="En attente",
            show_mic_button=True,
            mic_active=False,
            show_chat_button=True,
            robot_ip=robot.ip
        )
        robot.display_text(html_content)
        time.sleep(1.0)
        print("✅ Site chargé sur la tablette")
    
    last_recognized_name = recognized_name
    
    # ====================================================================
    # BOUCLE DE CONVERSATION
    # ====================================================================
    conversation_count = 0
    max_conversations = 50
    
    while conversation_count < max_conversations:
        conversation_count += 1
        print("\n" + "=" * 60)
        print("Tour de conversation #{}".format(conversation_count))
        print("=" * 60)
        
        # Vérifier les détections en arrière-plan (QR code)
        _check_background_qr(robot)
        
        # Vérifier les nouveaux visages
        if robot.video_stream_active:
            new_face = robot.check_for_new_face(last_recognized_name)
            if new_face:
                _handle_new_face(robot, new_face, last_recognized_name)
                last_recognized_name = new_face
        
        # Afficher le bouton micro en attente
        if robot.tablet:
            _show_waiting_interface(robot)
        
        # Demander à l'utilisateur de parler
        if not conversation_context.in_reservation_mode and robot.tts:
            robot.say("Comment puis-je vous aider ?", language=ROBOT_CONFIG["language"])
        
        # Attendre l'enregistrement
        audio_file = _wait_for_recording(robot)
        
        if not audio_file:
            _show_error(robot, "Échec de l'enregistrement")
            continue
        
        # Transcrire l'audio
        if robot.tablet:
            _show_processing_interface(robot)
        
        print("📝 Transcription de l'audio...")
        transcribed_text, detected_lang = transcribe_audio(audio_file)
        
        # Déterminer la langue pour TTS
        tts_lang = detected_lang if detected_lang else ROBOT_CONFIG["language"]
        try:
            tts_lang = map_language_code_to_ald_label(tts_lang)
        except Exception:
            pass
        
        if not transcribed_text or len(transcribed_text.strip()) < 3:
            _show_error(robot, "Je n'ai pas bien compris")
            continue
        
        print("✅ Texte transcrit: '{}'".format(transcribed_text))
        
        # Afficher la transcription
        if robot.tablet:
            _show_transcription(robot, transcribed_text)
        
        time.sleep(1)
        
        # Détecter le type de requête et traiter
        if is_reservation_request(transcribed_text) or conversation_context.in_reservation_mode:
            _handle_reservation(robot, transcribed_text, audio_file, conversation_context, tts_lang)
        elif is_qr_scan_request(transcribed_text):
            _handle_qr_scan(robot, transcribed_text, conversation_context, tts_lang)
        else:
            _handle_normal_chat(robot, transcribed_text, detected_lang, tts_lang)
        
        time.sleep(2)
    
    # Fin de la conversation
    _handle_conversation_end(robot)


def _check_background_qr(robot):
    """Vérifie les QR codes détectés en arrière-plan"""
    try:
        qr_scan = None
        if robot.latest_qr_result:
            with robot.qr_lock:
                qr_scan = robot.latest_qr_result
                robot.latest_qr_result = None
        
        if qr_scan:
            print("📷 QR détecté en arrière-plan")
            qr_result = qr_scan
            if qr_result and qr_result.get("success"):
                reservation = qr_result.get("reservation", {})
                client = qr_result.get("client", {})
                qr_id = qr_result.get("qr_id", "N/A")
                client_name = "{} {}".format(client.get("prenom", ""), client.get("nom", "")).strip()
                if not client_name:
                    client_name = "Client"
                
                confirmation_msg = "Parfait ! QR détecté. Bonjour {}, votre réservation {} est confirmée.".format(
                    client_name, qr_id
                )
                
                if robot.tts:
                    robot.say(confirmation_msg, language="French")
                
                if robot.tablet:
                    html_content = create_tablet_html(
                        title="✅ QR Code détecté",
                        message="Réservation confirmée",
                        subtitle="ID: {}".format(qr_id),
                        status="🟢 Validé",
                        show_mic_button=True,
                        mic_active=False
                    )
                    robot.display_text(html_content)
                
                print("✅ QR code validé en arrière-plan: {}".format(qr_id))
                time.sleep(3)
    except Exception as e:
        print("Erreur lors du traitement du QR détecté en arrière-plan: {}".format(e))


def _handle_new_face(robot, new_face, last_recognized_name):
    """Gère la détection d'un nouveau visage"""
    print("Nouveau visage detecte: {}".format(new_face))
    greeting_msg = "Ah bonjour {} !".format(new_face)
    if robot.tts:
        robot.say(greeting_msg, language=ROBOT_CONFIG["language"])
    
    if robot.tablet:
        html_content = create_tablet_html(
            title="Bonjour",
            message="Ah bonjour {} !".format(new_face),
            subtitle="",
            status="Personne detectee",
            show_mic_button=True,
            mic_active=False,
            robot_ip=robot.ip
        )
        robot.display_text(html_content)
    time.sleep(1.0)


def _show_waiting_interface(robot):
    """Affiche l'interface d'attente"""
    html_content = create_tablet_html(
        title="Pret",
        message="Cliquez sur le micro pour parler",
        status="En attente...",
        show_mic_button=True,
        mic_active=False,
        show_chat_button=True,
        robot_ip=robot.ip
    )
    robot.display_text(html_content)


def _wait_for_recording(robot):
    """Attend que l'utilisateur enregistre un message"""
    print("⏳ En attente du démarrage de l'enregistrement...")
    print("   (Si le bouton ne fonctionne pas, l'enregistrement démarrera automatiquement dans 10 secondes)")
    
    max_wait_start = 10
    check_interval = 0.5
    elapsed_time = 0
    recording_started = False
    
    while elapsed_time < max_wait_start and not recording_started:
        time.sleep(check_interval)
        elapsed_time += check_interval
        
        try:
            status_response = requests.get(
                "{}/record/status".format(API_CONFIG["base_url"]),
                timeout=2
            )
            if status_response.ok:
                status = status_response.json()
                if status.get("recording", False):
                    recording_started = True
                    print("Enregistrement demarre via le bouton micro. Parlez maintenant...")
                    if robot.tablet:
                        _show_recording_interface(robot)
        except Exception:
            pass
    
    if not recording_started:
        print("⏱️ Timeout: démarrage automatique de l'enregistrement...")
        try:
            response = requests.post("{}/record/start".format(API_CONFIG["base_url"]), timeout=5)
            if response.ok:
                recording_started = True
                print("Enregistrement demarre automatiquement. Parlez maintenant...")
                if robot.tablet:
                    _show_recording_interface(robot)
        except Exception as e:
            print("❌ Erreur lors du démarrage automatique: {}".format(e))
    
    return record_audio_manual()


def _show_recording_interface(robot):
    """Affiche l'interface d'enregistrement"""
    html_content = create_tablet_html(
        title="Enregistrement...",
        message="Je vous ecoute",
        status="Enregistrement en cours... Cliquez sur le micro pour arreter",
        show_mic_button=True,
        mic_active=True,
        robot_ip=robot.ip
    )
    robot.display_text(html_content)


def _show_processing_interface(robot):
    """Affiche l'interface de traitement"""
    html_content = create_tablet_html(
        title="📝 Transcription...",
        message="Je comprends votre message",
        status="🟡 Analyse en cours...",
        show_mic_button=False
    )
    robot.display_text(html_content)


def _show_transcription(robot, transcribed_text):
    """Affiche la transcription"""
    html_content = create_tablet_html(
        title="✅ Compris",
        message="J'ai bien entendu",
        subtitle=transcribed_text,
        status="🟢 Transcription réussie",
        show_mic_button=False
    )
    robot.display_text(html_content)


def _show_error(robot, message):
    """Affiche un message d'erreur"""
    error_msg = message or "Je n'ai pas bien compris. Pouvez-vous répéter ?"
    print("❌ {}".format(error_msg))
    
    if robot.tts:
        robot.say(error_msg, language="French")
    
    if robot.tablet:
        html_content = create_tablet_html(
            title="❓",
            message=message,
            subtitle="Veuillez répéter",
            status="🟡 Réessayez",
            show_mic_button=True,
            mic_active=False
        )
        robot.display_text(html_content)


def _handle_reservation(robot, transcribed_text, audio_file, conversation_context, tts_lang):
    """Gère une demande de réservation"""
    print("📅 Détection d'une demande de réservation")
    conversation_context.start_reservation()
    
    if robot.tablet:
        html_content = create_tablet_html(
            title="📅 Réservation",
            message="Traitement de votre demande",
            subtitle=transcribed_text,
            status="🟡 Création en cours...",
            show_mic_button=False
        )
        robot.display_text(html_content)
    
    # Créer la réservation
    reservation_result = make_reservation_with_api(audio_file)
    
    if reservation_result and reservation_result.get("status") == "success":
        # Réservation créée avec succès
        reservation_info = reservation_result.get("reservation", {})
        reservation_id = reservation_info.get("id_reservation") or reservation_info.get("id_res") or reservation_info.get("reservation_id") or "N/A"
        success_msg = "Parfait ! Votre réservation a été créée avec succès. Votre numéro de réservation est {}. Merci et à bientôt !".format(reservation_id)
        
        if robot.tts:
            robot.say(success_msg, language=tts_lang)
        
        if robot.tablet:
            html_content = create_tablet_html(
                title="✅ Réservation créée !",
                message="Numéro: {}".format(reservation_id),
                subtitle=transcribed_text,
                status="🟢 Succès",
                show_mic_button=True,
                mic_active=False
            )
            robot.display_text(html_content)
        
        conversation_context.reset()
        print("✅ Réservation créée avec succès: {}".format(reservation_id))
        time.sleep(3)
    else:
        # Vérifier les informations manquantes
        _handle_reservation_error(robot, reservation_result, transcribed_text, conversation_context, tts_lang)


def _handle_reservation_error(robot, reservation_result, transcribed_text, conversation_context, tts_lang):
    """Gère les erreurs de réservation"""
    reservation_data = reservation_result.get("reservation_data", {}) if reservation_result else {}
    error_msg = reservation_result.get("error", "").lower() if reservation_result else ""
    
    nom = reservation_data.get("nom", "").strip() if reservation_data else ""
    prenom = reservation_data.get("prenom", "").strip() if reservation_data else ""
    
    if not nom or nom.lower() in ["inconnu", ""]:
        nom = conversation_context.get_info("nom", "")
    if not prenom or prenom.lower() in ["inconnu", ""]:
        prenom = conversation_context.get_info("prenom", "")
    
    missing_nom = not nom or nom.lower() in ["inconnu", ""]
    missing_prenom = not prenom or prenom.lower() in ["inconnu", ""]
    
    if missing_nom or missing_prenom or "nom" in error_msg or "prenom" in error_msg:
        _ask_for_missing_info(robot, transcribed_text, missing_nom, missing_prenom, nom, prenom, conversation_context, tts_lang)
    else:
        # Autre erreur
        error_display = "Je suis désolé, il y a eu un problème lors de la création de votre réservation."
        
        if robot.tts:
            robot.say(error_display, language=tts_lang)
        
        if robot.tablet:
            html_content = create_tablet_html(
                title="❌ Erreur",
                message="Problème lors de la création",
                subtitle=error_msg[:150] if error_msg else "Erreur inconnue",
                status="🔴 Erreur",
                show_mic_button=True,
                mic_active=False
            )
            robot.display_text(html_content)
        
        print("❌ Erreur lors de la création de réservation: {}".format(error_msg))
        conversation_context.reset()


def _ask_for_missing_info(robot, transcribed_text, missing_nom, missing_prenom, nom, prenom, conversation_context, tts_lang):
    """Demande les informations manquantes"""
    if missing_nom and not conversation_context.get_info("nom"):
        missing_msg = "Pour créer votre réservation, j'ai besoin de connaître votre nom. Quel est votre nom de famille, s'il vous plaît ?"
        conversation_context.set_missing_fields(["nom"])
    elif missing_prenom and not conversation_context.get_info("prenom"):
        missing_msg = "Merci. Et quel est votre prénom, s'il vous plaît ?"
        conversation_context.set_missing_fields(["prenom"])
        if nom and nom.lower() not in ["inconnu", ""]:
            conversation_context.update_info("nom", nom)
    else:
        missing_msg = "Il me manque quelques informations pour finaliser votre réservation. Pouvez-vous me donner votre nom complet ?"
        conversation_context.set_missing_fields(["nom", "prenom"])
    
    if robot.tts:
        robot.say(missing_msg, language=tts_lang)
    
    if robot.tablet:
        html_content = create_tablet_html(
            title="❓ Information manquante",
            message=missing_msg,
            subtitle=transcribed_text,
            status="🟡 En attente d'informations",
            show_mic_button=True,
            mic_active=False
        )
        robot.display_text(html_content)
        try:
            time.sleep(10)
        except Exception:
            pass
    
    if nom and nom.lower() not in ["inconnu", ""]:
        conversation_context.update_info("nom", nom)
    if prenom and prenom.lower() not in ["inconnu", ""]:
        conversation_context.update_info("prenom", prenom)
    
    print("⚠️ Information manquante. Message: {}".format(missing_msg))


def _handle_qr_scan(robot, transcribed_text, conversation_context, tts_lang):
    """Gère une demande de scan QR code"""
    print("📷 Détection d'une demande de scan QR code")
    
    if robot.tablet:
        html_content = create_tablet_html(
            title="📷 Scan QR Code",
            message="Préparez votre QR code",
            subtitle=transcribed_text,
            status="🟡 Scan en cours...",
            show_mic_button=False
        )
        robot.display_text(html_content)
    
    if robot.tts:
        robot.say("Présentez votre QR code devant ma caméra, s'il vous plaît.", language=tts_lang)
    
    time.sleep(2)
    
    # Scanner le QR code
    print("📷 Scan du QR code en cours...")
    qr_result = None
    
    try:
        if robot.video:
            import tempfile
            image_data, image_width, image_height = robot.capture_image_from_camera()
            if image_data:
                try:
                    from PIL import Image
                    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                    try:
                        image_bytes = bytes(bytearray(image_data))
                        im = Image.frombytes("RGB", (image_width, image_height), image_bytes)
                        im.save(tmp.name, "JPEG")
                        tmp.close()
                        with open(tmp.name, 'rb') as f:
                            resp = requests.post(
                                "{}/scan_qr".format(API_CONFIG["base_url"]),
                                files={"file": f},
                                timeout=30
                            )
                        resp.raise_for_status()
                        qr_result = resp.json()
                    finally:
                        try:
                            import os
                            if os.path.exists(tmp.name):
                                os.remove(tmp.name)
                        except Exception:
                            pass
                except Exception:
                    pass
        
        if not qr_result:
            qr_result = scan_qr_code_with_api(camera_url=robot.camera_url)
    except Exception as e:
        print("❌ Erreur lors du scan QR: {}".format(e))
        qr_result = scan_qr_code_with_api(camera_url=robot.camera_url)
    
    _process_qr_result(robot, qr_result, tts_lang)


def _process_qr_result(robot, qr_result, tts_lang):
    """Traite le résultat du scan QR"""
    if qr_result and qr_result.get("success"):
        reservation = qr_result.get("reservation", {})
        client = qr_result.get("client", {})
        qr_id = qr_result.get("qr_id", "N/A")
        
        client_name = "{} {}".format(client.get("prenom", ""), client.get("nom", "")).strip()
        if not client_name:
            client_name = "Client"
        
        confirmation_msg = "Parfait ! J'ai vérifié votre QR code. Bonjour {}, votre réservation {} est confirmée.".format(
            client_name, qr_id
        )
        
        if robot.tts:
            robot.say(confirmation_msg, language=tts_lang)
        
        if robot.tablet:
            html_content = create_tablet_html(
                title="✅ QR Code Validé",
                message="Réservation confirmée",
                subtitle="ID: {}".format(qr_id),
                status="🟢 Validé",
                show_mic_button=True,
                mic_active=False
            )
            robot.display_text(html_content)
        
        print("✅ QR code validé avec succès!")
        time.sleep(3)
    else:
        error_msg = "Je suis désolé, je n'ai pas pu scanner votre QR code. Pouvez-vous le repositionner ?"
        
        if robot.tts:
            robot.say(error_msg, language=tts_lang)
        
        if robot.tablet:
            error_detail = qr_result.get("error", "QR code non détecté") if qr_result else "QR code non détecté"
            html_content = create_tablet_html(
                title="❌ Erreur",
                message="QR code non détecté",
                subtitle=error_detail[:100],
                status="🔴 Erreur",
                show_mic_button=True,
                mic_active=False
            )
            robot.display_text(html_content)
        
        print("❌ Échec du scan QR code")
        time.sleep(2)


def _handle_normal_chat(robot, transcribed_text, detected_lang, tts_lang):
    """Gère une conversation normale"""
    print("💬 Mode conversation normale")
    
    if robot.tablet:
        html_content = create_tablet_html(
            title="🤔 Traitement...",
            message="Je réfléchis à votre question",
            subtitle=transcribed_text,
            status="🟡 Génération de la réponse...",
            show_mic_button=False
        )
        robot.display_text(html_content)
    
    # Obtenir la réponse du chatbot
    chat_response = chat_with_api(transcribed_text, language=detected_lang)
    
    if not chat_response:
        _show_error(robot, "Je n'ai pas pu traiter votre demande")
        return
    
    print("✅ Réponse générée: '{}'".format(chat_response))
    
    # Faire dire la réponse au robot
    if robot.tts:
        robot.say(chat_response, language=tts_lang)
    
    # Afficher la réponse sur la tablette
    if robot.tablet:
        try:
            html_content = create_tablet_html(
                title="Reponse",
                message=chat_response,
                subtitle=transcribed_text,
                status="Reponse generee",
                show_mic_button=True,
                mic_active=False
            )
            robot.display_text(html_content)
        except UnicodeEncodeError:
            from utils.helpers import transliterate_to_ascii
            html_content = create_tablet_html(
                title="Reponse",
                message=transliterate_to_ascii(chat_response),
                subtitle=transliterate_to_ascii(transcribed_text),
                status="Reponse generee",
                show_mic_button=True,
                mic_active=False
            )
            try:
                robot.display_text(html_content)
            except Exception as e:
                print("Failed to display on tablet: {}".format(e))


def _handle_conversation_end(robot):
    """Gère la fin de la conversation"""
    farewell_msg = "Merci d'avoir utilisé mes services. Au revoir !"
    
    if robot.tts:
        robot.say(farewell_msg, language=ROBOT_CONFIG["language"])
    
    if robot.tablet:
        html_content = create_tablet_html(
            title="👋 Au revoir",
            message="Merci pour votre visite",
            status="🟢 Conversation terminée",
            show_mic_button=False
        )
        robot.display_text(html_content)
    
    print("\n" + "=" * 60)
    print("✅ Conversation terminée")
    print("=" * 60)


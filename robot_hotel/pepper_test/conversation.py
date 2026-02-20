# -*- coding: utf-8 -*-
"""
Boucle de conversation interactive avec le robot Pepper
"""
import os
import time
import json
import tempfile
import requests
from config import ROBOT_CONFIG, API_CONFIG, USE_PEPPER_MIC
from utils import safe_print, safe_say, get_local_ip_for_robot, map_language_code_to_ald_label
from utils.helpers import transliterate_to_ascii
from flask_utils import check_flask_server, start_flask_server_background
from api_client import (
    record_audio_manual,
    transcribe_audio,
    chat_with_api,
    make_reservation_with_api,
    is_reservation_request,
    is_qr_scan_request,
    scan_qr_code_with_api,
)
from ui.tablet_html import create_tablet_html
from robot_manager import RobotManager


def _record_audio(robot):
    """Enregistrement via micro Pepper ou PC selon config et disponibilite."""
    if robot and robot.audio_recorder and USE_PEPPER_MIC:
        def should_stop():
            try:
                r = requests.get("{}/record/status".format(API_CONFIG["base_url"]), timeout=2)
                if r.ok and not r.json().get("recording", True):
                    return True
            except Exception:
                pass
            return False
        return robot.record_audio_from_pepper(max_duration=30, should_stop_callback=should_stop)
    return record_audio_manual()


def _scan_qr_from_robot_camera(robot):
    """Scanne un QR code via la caméra du robot (ALVideoDevice)."""
    qr_result = None
    if robot.video:
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
                            timeout=API_CONFIG["timeout"]
                        )
                    resp.raise_for_status()
                    try:
                        qr_result = resp.json()
                    except Exception:
                        qr_result = json.loads(resp.text)
                finally:
                    try:
                        if os.path.exists(tmp.name):
                            os.remove(tmp.name)
                    except Exception:
                        pass
            except Exception:
                tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                tmp.write(image_data)
                tmp.close()
                try:
                    with open(tmp.name, 'rb') as f:
                        resp = requests.post(
                            "{}/scan_qr".format(API_CONFIG["base_url"]),
                            files={"file": f},
                            timeout=API_CONFIG["timeout"]
                        )
                    resp.raise_for_status()
                    try:
                        qr_result = resp.json()
                    except Exception:
                        qr_result = json.loads(resp.text)
                finally:
                    try:
                        if os.path.exists(tmp.name):
                            os.remove(tmp.name)
                    except Exception:
                        pass
        else:
            print("❌ Impossible de capturer l'image depuis la caméra pour le scan QR")
    if not qr_result:
        qr_result = scan_qr_code_with_api(camera_url=robot.camera_url)
    return qr_result


def run_conversation():
    """Fonction principale - boucle de conversation interactive"""
    print("=" * 60)
    print("Robot Pepper - Mode Conversation Interactive")
    print("=" * 60)
    print("Configuration:")
    print("  IP: {}".format(ROBOT_CONFIG["ip"]))
    print("  Port: {}".format(ROBOT_CONFIG["port"]))
    print("  Langue: {}".format(ROBOT_CONFIG["language"]))
    print("=" * 60)

    print("\nVerification du serveur Flask...")
    if not check_flask_server():
        print("Le serveur Flask n'est pas accessible sur {}".format(API_CONFIG["base_url"]))
        print("   Tentative de demarrage automatique...")
        if not start_flask_server_background():
            print("\n❌ Impossible de démarrer Flask automatiquement.")
            print("   Veuillez démarrer Flask manuellement avec:")
            print("   cd robot_hotel && python main.py")
            print("   ou utilisez le script: ./start_all.sh")
            return
    else:
        print("Serveur Flask accessible")

    robot = RobotManager(ip=ROBOT_CONFIG["ip"], port=ROBOT_CONFIG["port"])
    if not robot.connect():
        print("\nÉchec de la connexion. Arrêt du programme.")
        return

    robot.initialize_services()
    print("Attente de stabilisation des services...")
    time.sleep(2.0)

    try:
        if robot.audio_recorder and USE_PEPPER_MIC:
            requests.post("{}/record/pepper_mode".format(API_CONFIG["base_url"]),
                          json={"enabled": True}, timeout=5)
            print("Micro Pepper active (enregistrement sur le robot)")
        else:
            requests.post("{}/record/pepper_mode".format(API_CONFIG["base_url"]),
                          json={"enabled": False}, timeout=5)
    except Exception as e:
        print("Config mode enregistrement: {}".format(e))

    tts_lang = map_language_code_to_ald_label(ROBOT_CONFIG["language"])

    try:
        if robot.tablet:
            print("Activation de la tablette au demarrage...")
            robot.wake_tablet(show_blank=True)
            time.sleep(0.5)

        recognized_name = None
        if robot.video and robot.camera_url:
            print("Demarrage du flux video continu pour la detection faciale...")
            if robot.start_continuous_video_stream():
                recognized_name = robot.recognize_face_from_stream(max_attempts=15, delay=0.3)
            else:
                recognized_name = robot.recognize_face_from_camera()
        elif robot.video:
            recognized_name = robot.recognize_face_from_camera()

        if recognized_name:
            welcome_message = "Ah bonjour {} !".format(recognized_name)
            print("Personne reconnue: {}".format(recognized_name))
            if robot.tts:
                safe_say(robot, welcome_message, language=tts_lang)
        else:
            print("👤 Aucune personne reconnue - pas de message d'accueil")

        if robot.tablet:
            greeting_text = "Ah bonjour {} !".format(recognized_name) if recognized_name else "Prêt à vous aider"
            html_content = create_tablet_html(
                title="Pepper",
                message=greeting_text,
                subtitle="",
                status="En attente",
                show_mic_button=True,
                mic_active=False,
                robot_ip=robot.ip
            )
            robot.display_text(html_content)
            time.sleep(1.0)
        else:
            print("💡 Astuce: La tablette n'est pas disponible sur le robot virtuel")

        conversation_context = {
            "in_reservation_mode": False,
            "collected_info": {},
            "missing_fields": []
        }
        last_recognized_name = recognized_name
        conversation_count = 0
        max_conversations = 50

        while conversation_count < max_conversations:
            conversation_count += 1
            print("\n" + "=" * 60)
            print("Tour de conversation #{}".format(conversation_count))
            print("=" * 60)

            # QR détecté en arrière-plan
            try:
                qr_scan = None
                if robot.latest_qr_result:
                    with robot.qr_lock:
                        qr_scan = robot.latest_qr_result
                        robot.latest_qr_result = None
                if qr_scan and qr_scan.get("success"):
                    print("📷 QR détecté en arrière-plan")
                    client = qr_scan.get("client", {})
                    qr_id = qr_scan.get("qr_id", "N/A")
                    client_name = "{} {}".format(client.get("prenom", ""), client.get("nom", "")).strip() or "Client"
                    confirmation_msg = "Parfait ! QR détecté. Bonjour {}, votre réservation {} est confirmée.".format(client_name, qr_id)
                    if robot.tts:
                        safe_say(robot, confirmation_msg, language=tts_lang)
                    if robot.tablet:
                        robot.display_text(create_tablet_html(
                            title="✅ QR Code détecté",
                            message="Réservation confirmée",
                            subtitle="ID: {}".format(qr_id),
                            status="🟢 Validé",
                            show_mic_button=True,
                            mic_active=False
                        ))
                    print("✅ QR code validé en arrière-plan: {}".format(qr_id))
                    time.sleep(3)
                    continue
            except Exception as e:
                print("Erreur traitement QR arrière-plan: {}".format(e))

            # Nouveau visage
            if robot.video_stream_active:
                new_face = robot.check_for_new_face(last_recognized_name)
                if new_face:
                    print("Nouveau visage detecte: {}".format(new_face))
                    if robot.tts:
                        safe_say(robot, "Ah bonjour {} !".format(new_face), language=tts_lang)
                    last_recognized_name = new_face
                    if robot.tablet:
                        robot.display_text(create_tablet_html(
                            title="Bonjour",
                            message="Ah bonjour {} !".format(new_face),
                            subtitle="",
                            status="Personne detectee",
                            show_mic_button=True,
                            mic_active=False,
                            robot_ip=robot.ip
                        ))
                    time.sleep(1.0)

            if robot.tablet:
                robot.display_text(create_tablet_html(
                    title="Pepper",
                    message="Appuyez sur le micro pour parler",
                    subtitle="",
                    status="En attente",
                    show_mic_button=True,
                    mic_active=False,
                    robot_ip=robot.ip
                ))

            if robot.tts and conversation_count > 1 and not conversation_context["in_reservation_mode"]:
                safe_say(robot, "Comment puis-je vous aider ?", language=tts_lang)

            print("\nCliquez sur le micro pour demarrer l'enregistrement...")
            if robot.tablet:
                robot.display_text(create_tablet_html(
                    title="Pret",
                    message="Cliquez sur le micro pour parler",
                    status="En attente...",
                    show_mic_button=True,
                    mic_active=False,
                    robot_ip=robot.ip
                ))
                local_ip = get_local_ip_for_robot(robot.ip)
                print("URL de l'API pour la tablette: http://{}:5000".format(local_ip))

            print("⏳ En attente du démarrage de l'enregistrement...")
            max_wait_start = 10
            recording_started = False
            for _ in range(int(max_wait_start / 0.5)):
                time.sleep(0.5)
                try:
                    status_response = requests.get("{}/record/status".format(API_CONFIG["base_url"]), timeout=2)
                    if status_response.ok and status_response.json().get("recording", False):
                        recording_started = True
                        print("Enregistrement demarré via le bouton micro.")
                        if robot.tablet:
                            robot.display_text(create_tablet_html(
                                title="Enregistrement...",
                                message="Je vous ecoute",
                                status="Enregistrement en cours... Cliquez sur le micro pour arreter",
                                show_mic_button=True,
                                mic_active=True,
                                robot_ip=robot.ip
                            ))
                        break
                except Exception:
                    pass

            if not recording_started:
                try:
                    response = requests.post("{}/record/start".format(API_CONFIG["base_url"]), timeout=5)
                    if response.ok:
                        recording_started = True
                        print("Enregistrement demarre automatiquement.")
                        if robot.tablet:
                            robot.display_text(create_tablet_html(
                                title="Enregistrement...",
                                message="Je vous ecoute",
                                status="Enregistrement en cours...",
                                show_mic_button=True,
                                mic_active=True,
                                robot_ip=robot.ip
                            ))
                except Exception as e:
                    print("❌ Erreur démarrage automatique: {}".format(e))

            audio_file = _record_audio(robot)
            if not audio_file and robot.audio_recorder and USE_PEPPER_MIC:
                try:
                    requests.post("{}/record/pepper_mode".format(API_CONFIG["base_url"]),
                                  json={"enabled": False}, timeout=5)
                    if robot.tts:
                        safe_say(robot, "Micro Pepper indisponible. Utilisation du micro du PC. Cliquez pour demarrer.", language=tts_lang)
                    if robot.tablet:
                        robot.display_text(create_tablet_html(
                            title="Micro PC",
                            message="Cliquez sur le micro pour parler",
                            status="Utilisation du micro du PC",
                            show_mic_button=True,
                            mic_active=False,
                            robot_ip=robot.ip
                        ))
                    for _ in range(20):
                        time.sleep(0.5)
                        try:
                            r = requests.get("{}/record/status".format(API_CONFIG["base_url"]), timeout=2)
                            if r.ok and r.json().get("recording", False):
                                break
                        except Exception:
                            pass
                    audio_file = record_audio_manual()
                except Exception:
                    pass
            if not audio_file:
                if robot.tts:
                    safe_say(robot, "Je n'ai pas réussi à enregistrer votre message. Pouvez-vous réessayer ?", language=tts_lang)
                if robot.tablet:
                    robot.display_text(create_tablet_html(
                        title="❌ Erreur",
                        message="Échec de l'enregistrement",
                        status="🔴 Veuillez réessayer",
                        show_mic_button=True,
                        mic_active=False
                    ))
                continue

            if robot.tablet:
                robot.display_text(create_tablet_html(
                    title="📝 Transcription...",
                    message="Je comprends votre message",
                    status="🟡 Analyse en cours...",
                    show_mic_button=False
                ))

            transcribed_text, detected_lang = transcribe_audio(audio_file)
            tts_lang = map_language_code_to_ald_label(detected_lang or ROBOT_CONFIG["language"])
            safe_print("Detected language: {} -> TTS label: {}", detected_lang, tts_lang)

            if not transcribed_text or not transcribed_text.strip() or len(transcribed_text.strip()) < 3:
                if robot.tts:
                    safe_say(robot, "Je n'ai pas bien compris. Pouvez-vous répéter ?", language=tts_lang)
                if robot.tablet:
                    robot.display_text(create_tablet_html(
                        title="❓",
                        message="Je n'ai pas compris",
                        subtitle="Veuillez répéter",
                        status="🟡 Transcription échouée",
                        show_mic_button=True,
                        mic_active=False
                    ))
                continue

            txt_safe = transliterate_to_ascii(transcribed_text) if transcribed_text else "(vide)"
            safe_print("Texte transcrit: {}", txt_safe)
            if robot.tablet:
                robot.display_text(create_tablet_html(
                    title="✅ Compris",
                    message="J'ai bien entendu",
                    subtitle=transcribed_text,
                    status="🟢 Transcription réussie",
                    show_mic_button=False
                ))
            time.sleep(1)

            # Mode réservation
            if is_reservation_request(transcribed_text) or conversation_context["in_reservation_mode"]:
                conversation_context["in_reservation_mode"] = True
                if robot.tablet:
                    robot.display_text(create_tablet_html(
                        title="📅 Réservation",
                        message="Traitement de votre demande",
                        subtitle=transcribed_text,
                        status="🟡 Création en cours...",
                        show_mic_button=False
                    ))
                reservation_result = make_reservation_with_api(audio_file)

                if reservation_result and reservation_result.get("status") == "success":
                    reservation_info = reservation_result.get("reservation", {})
                    reservation_id = reservation_info.get("id_reservation") or reservation_info.get("id_res") or reservation_info.get("reservation_id") or "N/A"
                    success_msg = "Parfait ! Votre réservation a été créée. Numéro: {}. Merci et à bientôt !".format(reservation_id)
                    if robot.tts:
                        safe_say(robot, success_msg, language=tts_lang)
                    if robot.tablet:
                        robot.display_text(create_tablet_html(
                            title="✅ Réservation créée !",
                            message="Numéro: {}".format(reservation_id),
                            subtitle=transcribed_text,
                            status="🟢 Succès",
                            show_mic_button=True,
                            mic_active=False
                        ))
                    conversation_context["in_reservation_mode"] = False
                    conversation_context["collected_info"] = {}
                    time.sleep(3)
                else:
                    reservation_data = reservation_result.get("reservation_data", {}) if reservation_result else {}
                    error_msg = reservation_result.get("error", "").lower() if reservation_result else ""
                    nom = reservation_data.get("nom", "").strip() or conversation_context["collected_info"].get("nom", "")
                    prenom = reservation_data.get("prenom", "").strip() or conversation_context["collected_info"].get("prenom", "")
                    missing_nom = not nom or nom.lower() in ["inconnu", ""]
                    missing_prenom = not prenom or prenom.lower() in ["inconnu", ""]

                    if missing_nom or missing_prenom or "nom" in error_msg or "prenom" in error_msg:
                        if missing_nom and not conversation_context["collected_info"].get("nom"):
                            missing_msg = "Pour créer votre réservation, j'ai besoin de votre nom. Quel est votre nom de famille ?"
                        elif missing_prenom and not conversation_context["collected_info"].get("prenom"):
                            missing_msg = "Merci. Et quel est votre prénom ?"
                            if nom:
                                conversation_context["collected_info"]["nom"] = nom
                        else:
                            missing_msg = "Il me manque des informations. Pouvez-vous me donner votre nom complet ?"
                        if robot.tts:
                            safe_say(robot, missing_msg, language=tts_lang)
                        if robot.tablet:
                            robot.display_text(create_tablet_html(
                                title="❓ Information manquante",
                                message=missing_msg,
                                subtitle=transcribed_text,
                                status="🟡 En attente",
                                show_mic_button=True,
                                mic_active=False
                            ))
                            time.sleep(10)
                        if nom:
                            conversation_context["collected_info"]["nom"] = nom
                        if prenom:
                            conversation_context["collected_info"]["prenom"] = prenom
                        continue
                    else:
                        error_display = "Je suis désolé, il y a eu un problème. Pouvez-vous réessayer avec plus de détails ?"
                        if robot.tts:
                            safe_say(robot, error_display, language=tts_lang)
                        if robot.tablet:
                            robot.display_text(create_tablet_html(
                                title="❌ Erreur",
                                message="Problème lors de la création",
                                subtitle=(reservation_result or {}).get("error", "Erreur")[:150],
                                status="🔴 Erreur",
                                show_mic_button=True,
                                mic_active=False
                            ))
                        conversation_context["in_reservation_mode"] = False
                        conversation_context["collected_info"] = {}
                        continue

            # Mode scan QR
            elif is_qr_scan_request(transcribed_text):
                if robot.tablet:
                    robot.display_text(create_tablet_html(
                        title="📷 Scan QR Code",
                        message="Préparez votre QR code",
                        subtitle=transcribed_text,
                        status="🟡 Scan en cours...",
                        show_mic_button=False
                    ))
                if robot.tts:
                    safe_say(robot, "Présentez votre QR code devant ma caméra, s'il vous plaît.", language=tts_lang)
                time.sleep(2)
                try:
                    qr_result = _scan_qr_from_robot_camera(robot)
                except Exception as e:
                    print("❌ Erreur scan QR: {}".format(e))
                    qr_result = scan_qr_code_with_api(camera_url=robot.camera_url)

                if qr_result and qr_result.get("success"):
                    reservation = qr_result.get("reservation", {})
                    client = qr_result.get("client", {})
                    qr_id = qr_result.get("qr_id", "N/A")
                    client_name = "{} {}".format(client.get("prenom", ""), client.get("nom", "")).strip() or "Client"
                    confirmation_msg = "Parfait ! Bonjour {}, votre réservation {} est confirmée. Type: {}, arrivée {}, départ {}. Au plaisir !".format(
                        client_name, qr_id,
                        reservation.get("type_chambre", "N/A"),
                        reservation.get("date_arrivee", "N/A"),
                        reservation.get("date_depart", "N/A")
                    )
                    if robot.tts:
                        safe_say(robot, confirmation_msg, language=tts_lang)
                    if robot.tablet:
                        robot.display_text(create_tablet_html(
                            title="✅ QR Code Validé",
                            message="Réservation confirmée",
                            subtitle="ID: {}".format(qr_id),
                            status="🟢 Validé",
                            show_mic_button=True,
                            mic_active=False
                        ))
                    time.sleep(3)
                else:
                    if robot.tts:
                        safe_say(robot, "Je n'ai pas pu scanner votre QR code. Repositionnez-le, s'il vous plaît.", language=tts_lang)
                    if robot.tablet:
                        robot.display_text(create_tablet_html(
                            title="❌ Erreur",
                            message="QR code non détecté",
                            subtitle=(qr_result or {}).get("error", "Non détecté")[:100],
                            status="🔴 Erreur",
                            show_mic_button=True,
                            mic_active=False
                        ))
                    time.sleep(2)

            # Mode conversation normale
            else:
                conversation_context["in_reservation_mode"] = False
                if robot.tablet:
                    robot.display_text(create_tablet_html(
                        title="🤔 Traitement...",
                        message="Je réfléchis à votre question",
                        subtitle=transcribed_text,
                        status="🟡 Génération...",
                        show_mic_button=False
                    ))
                chat_response = chat_with_api(transcribed_text, language=detected_lang)
                if isinstance(chat_response, bytes):
                    chat_response = chat_response.decode('utf-8', 'ignore')

                if not chat_response:
                    if robot.tts:
                        safe_say(robot, "Je n'ai pas pu traiter votre demande. Pouvez-vous répéter ?", language=tts_lang)
                    if robot.tablet:
                        robot.display_text(create_tablet_html(
                            title="❌ Erreur",
                            message="Je n'ai pas pu répondre",
                            subtitle=transcribed_text,
                            status="🔴 Erreur",
                            show_mic_button=True,
                            mic_active=False
                        ))
                        time.sleep(10)
                    continue

                resp_safe = transliterate_to_ascii(chat_response) if chat_response else "(vide)"
                safe_print("Reponse generee: {}", resp_safe)
                if robot.tts:
                    safe_say(robot, chat_response, language=tts_lang)
                if robot.tablet:
                    try:
                        robot.display_text(create_tablet_html(
                            title="Reponse",
                            message=chat_response,
                            subtitle=transcribed_text,
                            status="Reponse generee",
                            show_mic_button=True,
                            mic_active=False
                        ))
                    except UnicodeEncodeError:
                        robot.display_text(create_tablet_html(
                            title="Reponse",
                            message=transliterate_to_ascii(chat_response),
                            subtitle=transliterate_to_ascii(transcribed_text),
                            status="Reponse generee",
                            show_mic_button=True,
                            mic_active=False
                        ))

            time.sleep(2)

        farewell_msg = "Merci d'avoir utilisé mes services. Au revoir !"
        if robot.tts:
            safe_say(robot, farewell_msg, language=tts_lang)
        if robot.tablet:
            robot.display_text(create_tablet_html(
                title="👋 Au revoir",
                message="Merci pour votre visite",
                status="🟢 Conversation terminée",
                show_mic_button=False
            ))
        print("\n" + "=" * 60)
        print("✅ Conversation terminée")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\nConversation interrompue par l'utilisateur")
        if robot.tts:
            safe_say(robot, "Au revoir !", language=tts_lang)
        if robot.video_stream_active:
            robot.stop_continuous_video_stream()
    except Exception as e:
        safe_print("Erreur: {}", e)
        import traceback
        traceback.print_exc()
        if robot.tts:
            safe_say(robot, "Je suis désolé, une erreur s'est produite.", language=tts_lang)
        if robot.video_stream_active:
            robot.stop_continuous_video_stream()
    finally:
        if robot.video_stream_active:
            robot.stop_continuous_video_stream()
        robot.disconnect()

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
    release_micro,
    transcribe_audio,
    chat_with_api,
    chat_voice,
    make_reservation_with_api,
    is_reservation_request,
    is_qr_scan_request,
    scan_qr_code_with_api,
    start_wake_word_detection,
    check_wake_word_status,
    reset_wake_word,
    conversation_start,
    conversation_answer,
    conversation_state,
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
                            files={"file": ("scan.jpg", f)},
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
                            files={"file": ("scan.jpg", f)},
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


def _tablet_call_status():
    """Retourne { call_requested, call_stop } depuis le serveur."""
    try:
        r = requests.get("{}/tablet/call/status".format(API_CONFIG["base_url"]), timeout=2)
        if r.ok:
            return r.json()
    except Exception:
        pass
    return {"call_requested": False, "call_stop": False}


def _tablet_scan_qr_requested():
    """Retourne True si l'utilisateur a demandé un scan QR depuis la tablette (bouton SCAN QR)."""
    try:
        r = requests.get("{}/tablet/scan_qr/status".format(API_CONFIG["base_url"]), timeout=2)
        if r.ok:
            return r.json().get("scan_qr_requested", False)
    except Exception:
        pass
    return False


def _clear_tablet_scan_qr_requested():
    """Efface la demande de scan QR côté serveur après prise en charge."""
    try:
        requests.post("{}/tablet/scan_qr/cleared".format(API_CONFIG["base_url"]), timeout=2)
    except Exception:
        pass


def _wait_for_wake_word(robot, tts_lang):
    """
    Affiche la page d'attente sur la tablette et attend un wake word.
    Retourne True dès qu'un mot déclencheur est détecté.
    Quitte aussi si un appel vocal ou un scan QR est demandé (retourne False).
    """
    base_url = API_CONFIG["base_url"].rstrip("/")

    # Démarrer l'écoute côté serveur
    reset_wake_word()
    start_wake_word_detection()

    # Afficher la page d'attente sur la tablette
    if robot and robot.tablet:
        robot.display_text(create_tablet_html(
            title="Pepper",
            message="Je vous écoute...",
            subtitle="",
            status="Dites « Bonjour » ou « Hey Pepper » pour commencer",
            show_mic_button=False,
            mic_active=False,
            robot_ip=getattr(robot, 'ip', None)
        ))

    print("En attente d'un wake word (bonjour, hey pepper, ok pepper…)")

    while True:
        time.sleep(1.0)

        # Vérifier si un appel ou scan QR est demandé depuis la tablette
        try:
            if _tablet_call_status().get("call_requested"):
                return False
            if _tablet_scan_qr_requested():
                return False
        except Exception:
            pass

        if check_wake_word_status():
            reset_wake_word()
            print("Wake word détecté !")
            if robot and robot.tts:
                safe_say(robot, "Oui, je vous écoute. Comment puis-je vous aider ?", language=tts_lang)
            return True


def _build_email_form_html(session_id, api_url, collected):
    """Génère la page HTML pour la saisie de l'email sur la tablette."""
    nom = collected.get("nom", "")
    prenom = collected.get("prenom", "")
    type_ch = collected.get("type_chambre", "")
    arr = collected.get("date_arrivee", "")
    dep = collected.get("date_depart", "")
    confirm_url = api_url.rstrip("/") + "/conversation/confirm"
    state_url = api_url.rstrip("/") + "/conversation/state?session_id=" + session_id

    return """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Confirmation - Pepper</title>
  <style>
    body {{ background:#667eea; color:white; font-family:Arial,sans-serif;
            display:flex; align-items:center; justify-content:center;
            min-height:100vh; margin:0; padding:16px; }}
    .card {{ background:#8a9eff; border-radius:18px; padding:28px 24px;
             width:100%; max-width:480px; text-align:center; }}
    h2 {{ font-size:26px; margin:0 0 14px; }}
    .recap {{ background:#9aafff; border-radius:10px; padding:14px;
              font-size:17px; text-align:left; margin-bottom:18px; line-height:1.8; }}
    input {{ width:100%; font-size:20px; padding:12px; border-radius:10px;
             border:none; color:#333; margin-bottom:14px; }}
    button {{ background:#43a047; border:none; border-radius:24px;
              padding:14px 40px; font-size:22px; color:white; cursor:pointer; width:100%; }}
    button:disabled {{ opacity:.6; }}
    .ok {{ font-size:24px; color:#b9f6ca; margin-top:10px; }}
  </style>
</head>
<body>
<div class="card">
  <h2>📧 Confirmation de réservation</h2>
  <div class="recap">
    <strong>Nom :</strong> {prenom} {nom}<br>
    <strong>Chambre :</strong> {type_ch}<br>
    <strong>Arrivée :</strong> {arr}<br>
    <strong>Départ :</strong> {dep}
  </div>
  <input type="email" id="em" placeholder="votre@email.com" />
  <button id="btn" onclick="send()">✅ Confirmer</button>
  <div id="msg"></div>
</div>
<script>
function send() {{
  var em = document.getElementById('em').value.trim();
  if (!em || !em.includes('@')) {{ alert('Email invalide'); return; }}
  var btn = document.getElementById('btn');
  btn.disabled = true; btn.textContent = 'Envoi…';
  var r = new XMLHttpRequest();
  r.open('POST', '{confirm_url}', true);
  r.setRequestHeader('Content-Type', 'application/json');
  r.onreadystatechange = function() {{
    if (r.readyState !== 4) return;
    var d; try {{ d = JSON.parse(r.responseText); }} catch(e) {{ d = {{}}; }}
    if (d.status === 'success') {{
      btn.style.display = 'none';
      document.getElementById('em').style.display = 'none';
      document.getElementById('msg').innerHTML =
        '<p class="ok">✅ Réservation confirmée !<br>N° ' + (d.reservation_id||'N/A') + '<br>' +
        (d.email_sent ? '📧 Email envoyé !' : '') + '</p>';
    }} else {{
      btn.disabled = false; btn.textContent = '✅ Confirmer';
      alert('Erreur : ' + (d.error || 'réessayez'));
    }}
  }};
  r.send(JSON.stringify({{session_id: '{session_id}', email: em}}));
}}
</script>
</body>
</html>""".format(
        nom=nom, prenom=prenom, type_ch=type_ch, arr=arr, dep=dep,
        confirm_url=confirm_url, session_id=session_id
    )


def run_reservation_conversation(robot, tts_lang):
    """
    Flux de réservation conversationnel pas à pas via l'API /conversation/*.
    Le robot pose chaque question à voix haute, enregistre la réponse, passe à l'étape suivante.
    Quand toutes les infos vocales sont collectées, affiche le formulaire email sur la tablette.
    """
    base_url = API_CONFIG["base_url"].rstrip("/")

    # Démarrer la conversation
    conv = conversation_start()
    if not conv or not conv.get("session_id"):
        if robot and robot.tts:
            safe_say(robot, "Désolé, je ne peux pas démarrer la réservation maintenant.", language=tts_lang)
        return

    session_id = conv["session_id"]
    question = conv.get("question", "")
    label = conv.get("label", "")

    print("Conversation réservation démarrée : session={}".format(session_id))

    while True:
        # Dire la question
        if robot and robot.tts:
            safe_say(robot, question, language=tts_lang)

        if robot and robot.tablet:
            robot.display_text(create_tablet_html(
                title="Réservation",
                message=question,
                subtitle="",
                status=label,
                show_mic_button=True,
                mic_active=False,
                robot_ip=getattr(robot, 'ip', None)
            ))

        # Enregistrer la réponse
        audio_file = _record_audio(robot)
        try:
            requests.post("{}/record/stop".format(base_url), timeout=3)
        except Exception:
            pass

        if not audio_file:
            if robot and robot.tts:
                safe_say(robot, "Je n'ai pas entendu. " + question, language=tts_lang)
            continue

        # Afficher "traitement"
        if robot and robot.tablet:
            robot.display_text(create_tablet_html(
                title="Traitement…",
                message="Un instant…",
                status=label,
                show_mic_button=False,
                robot_ip=getattr(robot, 'ip', None)
            ))

        # Envoyer au serveur
        result = conversation_answer(session_id)
        if not result:
            if robot and robot.tts:
                safe_say(robot, "Erreur serveur. " + question, language=tts_lang)
            continue

        status = result.get("status")
        transcript = result.get("transcript", "")
        print("Réponse : status={} transcript={}".format(status, transcript))

        if status == "continue":
            question = result.get("question", "")
            label = result.get("label", "")

        elif status == "need_email":
            # Toutes les infos vocales collectées — afficher le formulaire email sur la tablette
            collected = result.get("collected", {})
            if robot and robot.tts:
                safe_say(robot, result.get("question", "Veuillez entrer votre email sur la tablette."), language=tts_lang)
            if robot and robot.tablet:
                email_html = _build_email_form_html(session_id, base_url, collected)
                robot.display_text(email_html)

            # Attendre que l'utilisateur confirme (la session disparaît quand confirmée)
            print("En attente de la saisie email sur la tablette...")
            max_wait = 300  # 5 minutes max
            waited = 0
            confirmed = False
            while waited < max_wait:
                time.sleep(2)
                waited += 2
                state = conversation_state(session_id)
                if state is None:
                    # session supprimée = réservation confirmée
                    confirmed = True
                    break

            if confirmed:
                if robot and robot.tts:
                    safe_say(robot, "Parfait, votre réservation est confirmée ! Un email de confirmation vous a été envoyé. Au plaisir !", language=tts_lang)
                if robot and robot.tablet:
                    robot.display_text(create_tablet_html(
                        title="✅ Réservé !",
                        message="Votre réservation est confirmée.",
                        status="Email de confirmation envoyé",
                        show_mic_button=True,
                        mic_active=False,
                        robot_ip=getattr(robot, 'ip', None)
                    ))
                    time.sleep(3)
            else:
                if robot and robot.tts:
                    safe_say(robot, "Le temps imparti est écoulé. Veuillez réessayer.", language=tts_lang)
            return

        elif status == "retry":
            # La réponse n'a pas été comprise, on repose la même question
            question = result.get("question", question)
            if robot and robot.tts:
                safe_say(robot, question, language=tts_lang)

        elif status == "error":
            err = result.get("error", "erreur inconnue")
            print("Erreur conversation: {}".format(err))
            if robot and robot.tts:
                safe_say(robot, "Désolé, une erreur s'est produite. Réessayons plus tard.", language=tts_lang)
            return

        else:
            print("Statut inattendu: {}".format(status))
            return


def run_robot_call_flow(robot, tts_lang, conversation_context):
    """
    Appel vocal temps réel continu déclenché par le bouton Appel sur la tablette.
    Boucle : enregistrement (2 s silence = envoi) -> POST /chat/voice -> TTS robot.
    Sortie quand l'utilisateur clique sur Raccrocher (call_stop).
    """
    base_url = API_CONFIG["base_url"].rstrip("/")
    try:
        requests.post("{}/tablet/call/cleared".format(base_url), timeout=3)
    except Exception:
        pass
    if robot.tablet:
        robot.load_tablet_url("{}/tablet/call".format(base_url))
    if robot.tts:
        safe_say(robot, "Appel vocal activé. Parlez, deux secondes de silence envoient votre message. Dites raccrocher ou appuyez sur le bouton pour terminer.", language=tts_lang)
    session_id = conversation_context.get("chat_session_id")

    def check_stop():
        return _tablet_call_status().get("call_stop", False)

    while True:
        if check_stop():
            print("Appel termine (Raccrocher).")
            break
        if USE_PEPPER_MIC and robot.audio_recorder:
            audio_file = robot.record_audio_from_pepper(
                max_duration=60,
                silence_timeout=2.0,
                should_stop_callback=check_stop
            )
        else:
            try:
                requests.post("{}/record/start".format(base_url), timeout=5)
            except Exception:
                pass
            audio_file = None
            for _ in range(240):
                if check_stop():
                    break
                time.sleep(0.5)
                try:
                    r = requests.get("{}/record/status".format(base_url), timeout=2)
                    if r.ok:
                        data = r.json()
                        if not data.get("recording", True):
                            audio_file = data.get("file")
                            break
                except Exception:
                    pass
            if not audio_file:
                try:
                    requests.post("{}/record/stop".format(base_url), timeout=5)
                    r = requests.get("{}/record/status".format(base_url), timeout=2)
                    if r.ok:
                        audio_file = r.json().get("file")
                except Exception:
                    pass
        if not audio_file:
            continue
        response, new_sid, transcript = chat_voice(audio_file, session_id=session_id)
        if new_sid:
            session_id = new_sid
            conversation_context["chat_session_id"] = session_id
        if response and robot.tts:
            safe_say(robot, response, language=tts_lang)
        elif robot.tts and (transcript or audio_file):
            safe_say(robot, "Je n'ai pas bien compris. Pouvez-vous répéter ?", language=tts_lang)
        if check_stop():
            break

    try:
        requests.post("{}/tablet/call/reset".format(base_url), timeout=3)
    except Exception:
        pass
    if robot.tablet:
        robot.display_text(create_tablet_html(
            title="Pepper",
            message="Appel termine. Comment puis-je vous aider ?",
            subtitle="",
            status="En attente",
            show_mic_button=True,
            mic_active=False,
            robot_ip=robot.ip
        ))


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

    # Libérer le micro si un ancien lancement l'a laissé actif (évite "micro indisponible")
    release_micro()

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
    robot.stop_pepper_microphones()

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
            "missing_fields": [],
            "chat_session_id": None,
        }
        last_recognized_name = recognized_name
        conversation_count = 0
        max_conversations = 50

        while conversation_count < max_conversations:
            conversation_count += 1
            print("\n" + "=" * 60)
            print("Tour de conversation #{}".format(conversation_count))
            print("=" * 60)

            # Appel vocal temps réel (bouton Appel sur la tablette)
            try:
                call_status = _tablet_call_status()
                if call_status.get("call_requested"):
                    print("Demande d'appel vocal detectee (bouton Appel).")
                    run_robot_call_flow(robot, tts_lang, conversation_context)
                    continue
            except Exception as e:
                print("Erreur check appel tablette: {}".format(e))

            # Scan QR demandé depuis la tablette (bouton SCAN QR)
            try:
                if _tablet_scan_qr_requested():
                    _clear_tablet_scan_qr_requested()
                    print("Demande de scan QR detectee (bouton tablette).")
                    if robot.tablet:
                        robot.display_text(create_tablet_html(
                            title="📷 Scan QR Code",
                            message="Préparez votre QR code",
                            subtitle="",
                            status="🟡 Scan en cours...",
                            show_mic_button=False,
                            robot_ip=robot.ip
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
                        client = qr_result.get("client", {})
                        reservation = qr_result.get("reservation", {})
                        qr_id = qr_result.get("qr_id", "N/A")
                        client_name = "{} {}".format(client.get("prenom", ""), client.get("nom", "")).strip() or "Client"
                        type_ch = reservation.get("type_chambre", "N/A")
                        date_in = reservation.get("date_arrivee", "N/A")
                        date_out = reservation.get("date_depart", "N/A")
                        confirmation_msg = "Parfait ! Bonjour {}, votre réservation {} est confirmée. Type: {}, arrivée {}, départ {}. Au plaisir !".format(
                            client_name, qr_id, type_ch, date_in, date_out
                        )
                        if robot.tts:
                            safe_say(robot, confirmation_msg, language=tts_lang)
                        if robot.tablet:
                            result_message = "Bonjour {} — Réservation {} validée. Chambre: {} — Arrivée: {} — Départ: {}.".format(
                                client_name, qr_id, type_ch, date_in, date_out
                            )
                            robot.display_text(create_tablet_html(
                                title="✅ QR Code Validé",
                                message=result_message,
                                subtitle="ID réservation: {}".format(qr_id),
                                status="🟢 Réservation confirmée",
                                show_mic_button=True,
                                mic_active=False,
                                robot_ip=robot.ip
                            ))
                        time.sleep(3)
                    else:
                        err_msg = (qr_result or {}).get("error", "Non détecté") if qr_result else "Non détecté"
                        if robot.tts:
                            safe_say(robot, "Je n'ai pas pu scanner votre QR code. Repositionnez-le, s'il vous plaît.", language=tts_lang)
                        if robot.tablet:
                            robot.display_text(create_tablet_html(
                                title="❌ Scan échoué",
                                message="QR code non détecté ou invalide.",
                                subtitle=str(err_msg)[:120],
                                status="🔴 Erreur",
                                show_mic_button=True,
                                mic_active=False,
                                robot_ip=robot.ip
                            ))
                        time.sleep(2)
                    continue
            except Exception as e:
                print("Erreur traitement demande scan QR: {}".format(e))

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

            # ── Attente par wake word (remplace le bouton micro) ──────────────────
            wake_detected = _wait_for_wake_word(robot, tts_lang)
            if not wake_detected:
                # call ou scan QR demandé depuis la tablette → géré par les blocs suivants
                continue

            audio_file = _record_audio(robot)
            try:
                requests.post("{}/record/stop".format(API_CONFIG["base_url"]), timeout=3)
            except Exception:
                pass
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

            # Mode réservation conversationnel pas à pas
            if is_reservation_request(transcribed_text) or conversation_context["in_reservation_mode"]:
                conversation_context["in_reservation_mode"] = False
                conversation_context["collected_info"] = {}
                run_reservation_conversation(robot, tts_lang)
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
                chat_response, new_session_id = chat_with_api(
                    transcribed_text,
                    language=detected_lang,
                    session_id=conversation_context.get("chat_session_id")
                )
                if new_session_id:
                    conversation_context["chat_session_id"] = new_session_id
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
        robot.stop_pepper_microphones()
        release_micro()
        robot.disconnect()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script to communicate with Pepper robot
"""

import os
import sys
import time
import json
import requests
import unicodedata

from pepper_config import (
    ROBOT_CONFIG,
    API_CONFIG,
    TEST_MESSAGE,
    CHOREGRAPHE_PATH,
)
from pepper_utils import safe_print, transliterate_to_ascii, safe_say
from robot_hotel.pepper_test.robot_manager_old import RobotManager
from robot_hotel.pepper_test.utils_old import (
    check_flask_server,
    start_flask_server_background,
    post_file_with_retries,
    get_local_ip_for_robot,
    record_audio,
    record_audio_manual,
    record_audio_with_vad,
    transcribe_audio,
    chat_with_api,
    make_reservation_with_api,
    is_reservation_request,
    is_qr_scan_request,
    force_utf8,
    map_language_code_to_ald_label,
    create_tablet_html,
    scan_qr_code_with_api,
)

# HTML escape helper with compatibility fallback (Python2/3)
try:
    import html as _html_mod
    def escape_html(s):
        if s is None:
            return ''
        if isinstance(s, bytes):
            s = s.decode('utf-8', errors='ignore')
        return _html_mod.escape(s)
except Exception:
    try:
        import cgi as _cgi
        def escape_html(s):
            if s is None:
                return ''
            if isinstance(s, bytes):
                s = s.decode('utf-8', errors='ignore')
            return _cgi.escape(s, quote=True)
    except Exception:
        def escape_html(s):
            if s is None:
                return ''
            if isinstance(s, bytes):
                s = s.decode('utf-8', errors='ignore')
            s = str(s)
            return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#x27;')

# Import optionnel pour le scan QR code via caméra
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    safe_print("OpenCV (cv2) non disponible. Le scan QR code utilisera le téléchargement direct depuis l'URL si disponible.")
    safe_print("Pour installer OpenCV: pip install opencv-python")


# ============================================================================
# Fonction principale - Conversation interactive
# ============================================================================
def main():
    """Fonction principale avec conversation interactive"""
    print("=" * 60)
    print("Robot Pepper - Mode Conversation Interactive")
    print("=" * 60)
    print("Configuration:")
    print("  IP: {}".format(ROBOT_CONFIG["ip"]))
    print("  Port: {}".format(ROBOT_CONFIG["port"]))
    print("  Langue: {}".format(ROBOT_CONFIG["language"]))
    print("=" * 60)
    
    # Vérifier que le serveur Flask est en cours d'exécution
    print("\nVerification du serveur Flask...")
    if not check_flask_server():
        print("Le serveur Flask n'est pas accessible sur {}".format(API_CONFIG["base_url"]))
        print("   Tentative de demarrage automatique...")
        
        if not start_flask_server_background():
            print("\n❌ Impossible de démarrer Flask automatiquement.")
            print("   Veuillez démarrer Flask manuellement avec:")
            print("   cd robot_hotel && python main.py")
            print("   ou utilisez le script: ./start_all.sh")
            print("\n   Le serveur Flask doit tourner indépendamment du robot.")
            return
    else:
        print("Serveur Flask accessible")
    
    # Créer le gestionnaire de robot
    robot = RobotManager(
        ip=ROBOT_CONFIG["ip"],
        port=ROBOT_CONFIG["port"]
    )
    
    # Connecter au robot
    if not robot.connect():
        print("\nÉchec de la connexion. Arrêt du programme.")
        return
    
    # Initialiser les services
    robot.initialize_services()
    
    # Vérifier si le micro de Pepper est disponible
    if robot.audio_recorder:
        print("✅ Micro de Pepper disponible - Utilisation des micros intégrés pour une meilleure qualité audio")
    else:
        print("⚠️ Micro de Pepper non disponible - Utilisation du micro du PC comme fallback")
    
    # Attendre un peu après l'initialisation pour laisser les services se stabiliser
    print("Attente de stabilisation des services...")
    time.sleep(2.0)
    
    try:
        # Activer la tablette AVANT toute autre opération si elle est disponible
        # show_blank=True uniquement au premier démarrage pour initialiser
        if robot.tablet:
            print("Activation de la tablette au demarrage...")
            robot.wake_tablet(show_blank=True)
            time.sleep(0.5)  # Délai court après activation
        
        # Démarrer le flux vidéo continu pour la détection faciale
        recognized_name = None
        if robot.video and robot.camera_url:
            print("Demarrage du flux video continu pour la detection faciale...")
            if robot.start_continuous_video_stream():
                print("Reconnaissance faciale en cours depuis le flux video continu...")
                recognized_name = robot.recognize_face_from_stream(max_attempts=5, delay=0.3)
            else:
                print("Impossible de demarrer le flux video, utilisation de la capture unique...")
                recognized_name = robot.recognize_face_from_camera()
        elif robot.video:
            print("Reconnaissance faciale en cours (capture unique)...")
            recognized_name = robot.recognize_face_from_camera()
        
        # Message d'accueil personnalisé si une personne est reconnue
        if recognized_name:
            # Si reconnu, dire seulement "Ah bonjour [nom]"
            welcome_message = "Ah bonjour {} !".format(recognized_name)
            print("Personne reconnue: {}".format(recognized_name))
            if robot.tts:
                ok = safe_say(robot, welcome_message, language=ROBOT_CONFIG["language"])
                if not ok:
                    print("TTS failed to speak welcome message for {}".format(recognized_name))
        else:
            # Si non reconnu, ne rien dire
            print("👤 Aucune personne reconnue - pas de message d'accueil")
        
        # Afficher l'interface initiale avec bouton micro (recharge le site à chaque démarrage)
        if robot.tablet:
            # Charger directement le contenu sans réactiver (évite les pages blanches)
            print("🖥️ Chargement de l'interface sur la tablette...")
            
            greeting_text = "Ah bonjour {} !".format(recognized_name) if recognized_name else "Prêt à vous aider"
            html_content = create_tablet_html(
                title="Pepper",
                message=greeting_text,
                subtitle="",
                status="En attente",
                show_mic_button=True,
                mic_active=False,
                robot_ip=robot.ip,
                show_chat_button=True,
                chat_url="http://{}:5000/chat".format(get_local_ip_for_robot(robot.ip) if robot.ip else "localhost")
            )
            robot.display_text(html_content)
            time.sleep(1.0)  # Délai pour laisser le contenu se charger
            print("✅ Site chargé sur la tablette")
        else:
            print("💡 Astuce: La tablette n'est pas disponible sur le robot virtuel")
            print("   Les interactions se feront via la console")
        
        # État de la conversation pour les réservations
        conversation_context = {
            "in_reservation_mode": False,
            "collected_info": {},
            "missing_fields": []
        }
        
        # Variable pour suivre la dernière personne reconnue (pour éviter les répétitions)
        last_recognized_name = recognized_name
        
        # ====================================================================
        # BOUCLE DE CONVERSATION
        # ====================================================================
        conversation_count = 0
        max_conversations = 50  # Limite de sécurité
        
        while conversation_count < max_conversations:
            conversation_count += 1
            print("\n" + "=" * 60)
            print("Tour de conversation #{}".format(conversation_count))
            print("=" * 60)
            
            # Initialiser la langue TTS pour ce tour de conversation
            tts_lang = ROBOT_CONFIG["language"]
            
            # Vérifier s'il y a un nouveau visage détecté pendant la session
            # Vérifier si un QR a été détecté en arrière-plan via le flux vidéo
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
                        confirmation_msg = "Parfait ! QR détecté. Bonjour {}, votre réservation {} est confirmée.".format(client_name, qr_id)
                        if robot.tts:
                            safe_say(robot, confirmation_msg, language=tts_lang)
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
                        continue
            except Exception as e:
                print("Erreur lors du traitement du QR détecté en arrière-plan: {}".format(e))

            if robot.video_stream_active:
                new_face = robot.check_for_new_face(last_recognized_name)
                if new_face:
                    print("Nouveau visage detecte: {}".format(new_face))
                    greeting_msg = "Ah bonjour {} !".format(new_face)
                    if robot.tts:
                        ok = safe_say(robot, greeting_msg, language=ROBOT_CONFIG["language"])
                        if not ok:
                            print("TTS failed to speak greeting for {}".format(new_face))
                    last_recognized_name = new_face
                    
                    # Mettre à jour l'affichage sur la tablette
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
                    time.sleep(1.0)  # Petite pause après la salutation
            
            # Phase d'attente (Wake Word) - Utilisation d'ALSpeechRecognition
            print("\n🎤 Phase d'attente - Wake Word activé")
            print("   Dites 'Bonjour Pepper' ou 'Hello Pepper' pour commencer")
            
            # Afficher l'instruction sur la tablette
            if robot.tablet:
                html_content = create_tablet_html(
                    title="Pepper en attente",
                    message="Dites 'Bonjour Pepper' pour commencer",
                    subtitle="",
                    status="En attente du wake word...",
                    show_mic_button=False,
                    show_chat_button=True,
                    chat_url="http://{}:5000/chat".format(get_local_ip_for_robot(robot.ip) if robot.ip else "localhost")
                )
                robot.display_text(html_content)
            
            # Démarrer la détection du wake word avec gestion d'erreur améliorée
            wake_word_started = False
            max_retries = 3
            for retry in range(max_retries):
                if robot.start_wake_word_detection():
                    wake_word_started = True
                    break
                else:
                    print("Tentative {}/{} échouée, nouvelle tentative dans 1 seconde...".format(retry + 1, max_retries))
                    time.sleep(1)
                    # Réinitialiser le service si nécessaire
                    try:
                        if robot.speech_recognition:
                            robot.speech_recognition.unsubscribe("WakeWordDetection")
                    except:
                        pass

            if not wake_word_started:
                print("❌ Impossible de démarrer la détection du wake word après {} tentatives".format(max_retries))
                print("   Passage en mode manuel...")
                # Fallback vers l'ancienne méthode
                if robot.tablet:
                    html_content = create_tablet_html(
                        title="Pepper",
                        message="Appuyez sur le micro pour parler",
                        subtitle="",
                        status="Mode manuel",
                        show_mic_button=True,
                        mic_active=False,
                        robot_ip=robot.ip
                    )
                    robot.display_text(html_content)
                
                # Attendre que l'utilisateur clique sur le micro (ancienne logique)
                print("⏳ En attente du clic sur le micro...")
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
                                print("Enregistrement démarré via le bouton micro")
                    except Exception:
                        pass
                
                if not recording_started:
                    print("⏱️ Timeout: démarrage automatique...")
                    try:
                        response = requests.post("{}/record/start".format(API_CONFIG["base_url"]), timeout=5)
                        recording_started = response.ok
                    except Exception as e:
                        print("❌ Erreur démarrage automatique: {}".format(e))
                
                if not recording_started:
                    continue
            else:
                # Attendre la détection du wake word et passer au streaming
                if robot.wait_for_wake_word_and_stream(timeout=30):
                    print("✅ Wake word détecté - Passage à l'enregistrement")
                    
                    # Mettre à jour l'affichage sur la tablette
                    if robot.tablet:
                        html_content = create_tablet_html(
                            title="Wake word détecté !",
                            message="Je vous écoute",
                            status="Enregistrement en cours...",
                            show_mic_button=False
                        )
                        robot.display_text(html_content)
                else:
                    print("⏰ Timeout wake word - Nouvelle tentative")
                    continue
            
            # ================================================================
            # 1. ENREGISTREMENT AUDIO - Utilisation du micro de Pepper
            # ================================================================
            print("\n🎤 Démarrage de l'enregistrement audio...")
            
            if robot.audio_recorder:
                # Utiliser le micro de Pepper avec VAD si disponible
                if hasattr(robot, 'record_audio_from_pepper_with_vad'):
                    print("📢 Utilisation du micro de Pepper avec VAD (détection de silence)...")
                    audio_file = robot.record_audio_from_pepper_with_vad(
                        max_duration=30,
                        silence_timeout=2.0,
                        min_duration=1.0
                    )
                else:
                    # Fallback: enregistrement simple sans VAD
                    print("📢 Utilisation du micro de Pepper (mode simple, 10 secondes)...")
                    audio_file = robot.record_audio_from_pepper(duration=10)
            else:
                # Fallback: micro du PC
                print("💻 Utilisation du micro du PC (fallback)...")
                audio_file = record_audio_with_vad()
            
            if not audio_file:
                error_msg = "Je n'ai pas réussi à enregistrer votre message. Pouvez-vous réessayer ?"
                print("❌ Échec de l'enregistrement")
                if robot.tts:
                    safe_say(robot, error_msg, language=tts_lang)
                if robot.tablet:
                    html_content = create_tablet_html(
                        title="❌ Erreur",
                        message="Échec de l'enregistrement",
                        status="🔴 Veuillez réessayer",
                        show_mic_button=True,
                        mic_active=False
                    )
                    robot.display_text(html_content)
                continue
            
            # ================================================================
            # 2. TRANSCRIPTION
            # ================================================================
            if robot.tablet:
                html_content = create_tablet_html(
                    title="📝 Transcription...",
                    message="Je comprends votre message",
                    status="🟡 Analyse en cours...",
                    show_mic_button=False
                )
                robot.display_text(html_content)
            
            print("📝 Transcription de l'audio...")
            transcribed_text, detected_lang = transcribe_audio(audio_file)

            # Déterminer la langue TTS
            tts_lang = detected_lang if detected_lang else ROBOT_CONFIG["language"]
            try:
                tts_lang_mapped = map_language_code_to_ald_label(tts_lang)
                safe_print("Langue détectée: {} -> TTS: {}", tts_lang, tts_lang_mapped)
                tts_lang = tts_lang_mapped
            except Exception:
                pass

            # Vérifier si la transcription a réussi
            if not transcribed_text or len(transcribed_text.strip()) < 3:
                error_msg = "Je n'ai pas bien compris ce que vous avez dit. Pouvez-vous répéter, s'il vous plaît ?"
                print("❌ Transcription vide ou trop courte")
                if robot.tts:
                    safe_say(robot, error_msg, language=tts_lang)
                if robot.tablet:
                    html_content = create_tablet_html(
                        title="❓",
                        message="Je n'ai pas compris",
                        subtitle="Veuillez répéter",
                        status="🟡 Transcription échouée",
                        show_mic_button=True,
                        mic_active=False
                    )
                    robot.display_text(html_content)
                continue
            
            print("✅ Texte transcrit: '{}'".format(transcribed_text))
            
            # Afficher la transcription sur la tablette
            if robot.tablet:
                html_content = create_tablet_html(
                    title="✅ Compris",
                    message="J'ai bien entendu",
                    subtitle=transcribed_text,
                    status="🟢 Transcription réussie",
                    show_mic_button=False
                )
                robot.display_text(html_content)
            
            time.sleep(1)
            
            # ================================================================
            # 3. TRAITEMENT DE LA DEMANDE
            # ================================================================
            
            # Détecter si c'est une demande de réservation
            if is_reservation_request(transcribed_text) or conversation_context["in_reservation_mode"]:
                # Mode réservation
                print("📅 Détection d'une demande de réservation")
                conversation_context["in_reservation_mode"] = True
                
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
                        safe_say(robot, success_msg, language=tts_lang)
                    
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
                    
                    # Réinitialiser le contexte
                    conversation_context["in_reservation_mode"] = False
                    conversation_context["collected_info"] = {}
                    
                    print("✅ Réservation créée avec succès: {}".format(reservation_id))
                    time.sleep(3)
                    
                else:
                    # Vérifier si des informations manquent
                    reservation_data = reservation_result.get("reservation_data", {}) if reservation_result else {}
                    error_msg = reservation_result.get("error", "").lower() if reservation_result else ""
                    
                    # Vérifier ce qui manque dans les données extraites
                    nom = reservation_data.get("nom", "").strip() if reservation_data else ""
                    prenom = reservation_data.get("prenom", "").strip() if reservation_data else ""
                    
                    # Utiliser les infos collectées précédemment
                    if not nom or nom.lower() in ["inconnu", ""]:
                        nom = conversation_context["collected_info"].get("nom", "")
                    if not prenom or prenom.lower() in ["inconnu", ""]:
                        prenom = conversation_context["collected_info"].get("prenom", "")
                    
                    # Déterminer ce qui manque
                    missing_nom = not nom or nom.lower() in ["inconnu", ""]
                    missing_prenom = not prenom or prenom.lower() in ["inconnu", ""]
                    
                    if missing_nom or missing_prenom or "nom" in error_msg or "prenom" in error_msg:
                        # Informations manquantes
                        if missing_nom and not conversation_context["collected_info"].get("nom"):
                            missing_msg = "Pour créer votre réservation, j'ai besoin de connaître votre nom. Quel est votre nom de famille, s'il vous plaît ?"
                            conversation_context["missing_fields"] = ["nom"]
                        elif missing_prenom and not conversation_context["collected_info"].get("prenom"):
                            missing_msg = "Merci. Et quel est votre prénom, s'il vous plaît ?"
                            conversation_context["missing_fields"] = ["prenom"]
                            if nom and nom.lower() not in ["inconnu", ""]:
                                conversation_context["collected_info"]["nom"] = nom
                        else:
                            missing_msg = "Il me manque quelques informations pour finaliser votre réservation. Pouvez-vous me donner votre nom complet, s'il vous plaît ?"
                            conversation_context["missing_fields"] = ["nom", "prenom"]
                        
                        if robot.tts:
                            safe_say(robot, missing_msg, language=tts_lang)
                        
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
                            conversation_context["collected_info"]["nom"] = nom
                        if prenom and prenom.lower() not in ["inconnu", ""]:
                            conversation_context["collected_info"]["prenom"] = prenom
                        
                        print("⚠️ Information manquante. Message: {}".format(missing_msg))
                        print("   Informations collectées: {}".format(conversation_context["collected_info"]))
                        continue
                    else:
                        # Autre erreur
                        error_msg_full = reservation_result.get("error", "Erreur inconnue") if reservation_result else "Erreur inconnue"
                        error_display = "Je suis désolé, il y a eu un problème lors de la création de votre réservation. Pouvez-vous réessayer en donnant plus de détails ?"
                        
                        if robot.tts:
                            safe_say(robot, error_display, language=tts_lang)
                        
                        if robot.tablet:
                            html_content = create_tablet_html(
                                title="❌ Erreur",
                                message="Problème lors de la création",
                                subtitle=error_msg_full[:150],
                                status="🔴 Erreur",
                                show_mic_button=True,
                                mic_active=False
                            )
                            robot.display_text(html_content)
                        
                        print("❌ Erreur réservation: {}".format(error_msg_full))
                        conversation_context["in_reservation_mode"] = False
                        conversation_context["collected_info"] = {}
                        continue
                
            elif is_qr_scan_request(transcribed_text):
                # Mode scan QR code
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
                
                # Demander au client de présenter le QR code
                if robot.tts:
                    safe_say(robot, "Présentez votre QR code devant ma caméra, s'il vous plaît.", language=tts_lang)
                
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
                            print("❌ Impossible de capturer l'image")
                    if not qr_result:
                        qr_result = scan_qr_code_with_api(camera_url=robot.camera_url)
                except Exception as e:
                    print("❌ Erreur scan QR: {}".format(e))
                    qr_result = scan_qr_code_with_api(camera_url=robot.camera_url)
                
                if qr_result and qr_result.get("success"):
                    # QR code valide scanné
                    reservation = qr_result.get("reservation", {})
                    client = qr_result.get("client", {})
                    qr_id = qr_result.get("qr_id", "N/A")
                    
                    client_name = "{} {}".format(client.get("prenom", ""), client.get("nom", "")).strip()
                    if not client_name:
                        client_name = "Client"
                    
                    confirmation_msg = "Parfait ! J'ai vérifié votre QR code. Bonjour {}, votre réservation {} est confirmée. Type de chambre: {}, arrivée le {}, départ le {}. Au plaisir de vous accueillir !".format(
                        client_name,
                        qr_id,
                        reservation.get("type_chambre", "N/A"),
                        reservation.get("date_arrivee", "N/A"),
                        reservation.get("date_depart", "N/A")
                    )
                    
                    if robot.tts:
                        safe_say(robot, confirmation_msg, language=tts_lang)
                    
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
                    print("   Client: {}".format(client_name))
                    print("   Réservation: {}".format(qr_id))
                    time.sleep(3)
                else:
                    # Erreur lors du scan
                    error_msg = "Je suis désolé, je n'ai pas pu scanner votre QR code. Pouvez-vous le repositionner devant ma caméra, s'il vous plaît ?"
                    
                    if robot.tts:
                        safe_say(robot, error_msg, language=tts_lang)
                    
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
            
            else:
                # Mode conversation normale
                print("💬 Mode conversation normale")
                conversation_context["in_reservation_mode"] = False
                
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

                # Normaliser la réponse
                try:
                    try:
                        unicode
                        is_py2 = True
                    except NameError:
                        is_py2 = False

                    if is_py2:
                        if isinstance(chat_response, unicode):
                            chat_response = chat_response.encode('utf-8')
                    else:
                        if isinstance(chat_response, bytes):
                            chat_response = chat_response.decode('utf-8', 'ignore')
                except Exception:
                    pass
                
                if not chat_response:
                    error_msg = "Je suis désolé, je n'ai pas pu traiter votre demande. Pouvez-vous répéter ?"
                    print("❌ Échec du chat")
                    if robot.tts:
                        safe_say(robot, error_msg, language=tts_lang)
                    if robot.tablet:
                        html_content = create_tablet_html(
                            title="❌ Erreur",
                            message="Je n'ai pas pu répondre",
                            subtitle=transcribed_text,
                            status="🔴 Erreur",
                            show_mic_button=True,
                            mic_active=False
                        )
                        robot.display_text(html_content)
                    continue
                
                safe_print("✅ Réponse générée: '{}'", chat_response)
                
                # Faire dire la réponse au robot
                if robot.tts:
                    safe_say(robot, chat_response, language=tts_lang)

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
                        safe_print("UnicodeEncodeError, using ASCII fallback")
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
                            safe_print("Erreur affichage tablette: {}", repr(e))
                    except Exception as e:
                        safe_print("Erreur affichage tablette: {}", repr(e))
            
            # Pause avant la prochaine interaction
            time.sleep(2)
        
        # Fin de la boucle
        farewell_msg = "Merci d'avoir utilisé mes services. Au revoir !"
        if robot.tts:
            safe_say(robot, farewell_msg, language=ROBOT_CONFIG["language"])
        
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
        
    except KeyboardInterrupt:
        print("\n\nConversation interrompue par l'utilisateur")
        if robot.tts:
            safe_say(robot, "Au revoir !", language=ROBOT_CONFIG["language"])
        if robot.video_stream_active:
            print("Arret du flux video continu...")
            robot.stop_continuous_video_stream()
        if robot.wake_word_active:
            print("Arret de la detection du wake word...")
            robot.stop_wake_word_detection()
    except Exception as e:
        print("\n❌ Erreur lors de l'exécution: {}".format(e))
        import traceback
        traceback.print_exc()
        if robot.tts:
            safe_say(robot, "Je suis désolé, une erreur s'est produite.", language=ROBOT_CONFIG["language"])
        if robot.video_stream_active:
            print("Arret du flux video continu...")
            robot.stop_continuous_video_stream()
        if robot.wake_word_active:
            print("Arret de la detection du wake word...")
            robot.stop_wake_word_detection()
    finally:
        # Nettoyage final
        if robot.video_stream_active:
            print("Arret du flux video continu...")
            robot.stop_continuous_video_stream()
        if robot.wake_word_active:
            print("Arret de la detection du wake word...")
            robot.stop_wake_word_detection()
        robot.disconnect()


if __name__ == "__main__":
    main()
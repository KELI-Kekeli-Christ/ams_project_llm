import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import time
import os
import threading
from flask import jsonify
SAMPLE_RATE = 16000
THRESHOLD = 0.01     # Seuil de détection de silence (plus bas = moins sensible aux bruits de fond)
SPEECH_THRESHOLD = 0.08  # Tres sensible pour detecter la parole
SILENCE_LEVEL = 0.03   # En dessous = silence (parole typique > 0.05, bruit ambiant < 0.05)
SILENCE_RATIO = 0.7      # Silence = niveau < 70% du pic
SILENCE_ABSOLUTE = 0.06  # Fallback : si niveau < ceci pendant 3s -> arret (sans avoir parle)
SILENCE_DURATION = 1.5  # Pour record_until_silence (GET /record)
SILENCE_DURATION_MANUAL = 1.5  # Secondes de silence pour arret auto (bouton micro)
MIN_RECORDING_BEFORE_SILENCE = 0.3  # Minimum avant de compter le silence
MAX_RECORDING_DURATION = 60.0
BLOCK_SIZE = 1024
# ~64ms par bloc -> N blocs = 2 secondes
SILENCE_BLOCKS_NEEDED = int(SILENCE_DURATION_MANUAL * SAMPLE_RATE / BLOCK_SIZE)
RECORDINGS_DIR = "recordings"
os.makedirs(RECORDINGS_DIR, exist_ok=True)

# Mots déclencheurs pour démarrer l'enregistrement automatiquement
WAKE_WORDS = ["bonjour", "hello", "hola", "hey pepper", "ok pepper", "pepper"]
WAKE_WORD_DETECTION_ENABLED = True
# Seuil de parole pour le wake word (adapte pour capter une voix plus faible)
WAKE_WORD_SPEECH_THRESHOLD = 0.015

# Générer le chemin du fichier
OUTPUT_FILE = f"{RECORDINGS_DIR}/{time.strftime('%Y%m%d_%H%M%S')}_voice.wav"

# Variables globales pour l'enregistrement manuel
recording_thread = None
recording_data = []
recording_active = False
recording_stream = None
wake_word_detected = False

# Mode micro Pepper : quand True, /record/start ne lance pas le PC, le script utilise le micro de Pepper
pepper_mic_mode = False

# Wake word : thread unique + modèle Whisper partagé (injecté depuis app.py)
_wake_word_thread = None
_wake_word_stop = threading.Event()
_shared_whisper_model = None


def set_shared_whisper_model(model):
    """Injecte le modèle Whisper déjà chargé par Flask pour éviter un double chargement."""
    global _shared_whisper_model
    _shared_whisper_model = model


def set_pepper_mic_mode(enabled):
    global pepper_mic_mode
    pepper_mic_mode = bool(enabled)

def get_pepper_mic_mode():
    return pepper_mic_mode


def is_silent(data, threshold):
    return _audio_level(data) < threshold


def _audio_level(data):
    """Mesure simple de l'énergie audio, plus stable qu'une moyenne brute."""
    return float(np.sqrt(np.mean(np.square(data.astype(np.float32)))))

def record_until_silence():
    print("🎤 Parle... j'arrêterai quand tu te tais.")

    sd.default.samplerate = SAMPLE_RATE
    sd.default.channels = 1

    recording = []
    silence_start = None

    with sd.InputStream() as stream:
        while True:
            data, _ = stream.read(1024)
            recording.append(data)

            # Detect silence
            if is_silent(data, THRESHOLD):
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start > SILENCE_DURATION:
                    print("⏹ Silence détecté. Arrêt.")
                    break
            else:
                silence_start = None  # reset

    audio = np.concatenate(recording, axis=0)
    write(OUTPUT_FILE, SAMPLE_RATE, audio)
    print("💾 Enregistré sous :", OUTPUT_FILE)
    file=os.listdir("recordings")
    return jsonify({"message": "Enregistrement terminé", "file": f"{RECORDINGS_DIR}/{file[-1]}"})

def _record_audio_thread():
    """Thread pour enregistrer l'audio. Arret auto apres 2 s de silence (temps reel)."""
    global recording_data, recording_active, recording_stream, OUTPUT_FILE

    sd.default.samplerate = SAMPLE_RATE
    sd.default.channels = 1

    peak_level = 0.0
    silence_start_time = None  # debut du silence en temps reel
    recording_start_time = time.time()
    last_debug_print = time.time()

    with sd.InputStream() as stream:
        recording_stream = stream
        while recording_active:
            data, _ = stream.read(1024)
            recording_data.append(data)

            level = _audio_level(data)
            elapsed = time.time() - recording_start_time

            # Parole : niveau > SILENCE_LEVEL -> reset (bruit ambiant < 0.035, parole > 0.05)
            if level > SILENCE_LEVEL:
                silence_start_time = None
                peak_level = max(peak_level, level)
            # Silence : niveau <= SILENCE_LEVEL
            elif elapsed >= MIN_RECORDING_BEFORE_SILENCE:
                if silence_start_time is None:
                    silence_start_time = time.time()
                elif time.time() - silence_start_time >= SILENCE_DURATION_MANUAL:
                    print("Silence detecte pendant 2 s. Arret automatique.")
                    recording_active = False
                    break

            if elapsed >= MAX_RECORDING_DURATION:
                print("Arret apres {} s (duree max).".format(int(MAX_RECORDING_DURATION)))
                recording_active = False
                break

            if time.time() - last_debug_print > 1.0:
                sil_dur = (time.time() - silence_start_time) if silence_start_time else 0
                print("[Record] niv={:.3f} peak={:.3f} silence={:.1f}s | {}s".format(
                    level, peak_level, sil_dur, int(elapsed)))
                last_debug_print = time.time()

        # Sauvegarder le fichier si arret par silence
        if recording_data and len(recording_data) > 0 and not recording_active:
            try:
                audio = np.concatenate(recording_data, axis=0)
                write(OUTPUT_FILE, SAMPLE_RATE, audio)
                print("Enregistrement sauvegarde (arret auto silence):", OUTPUT_FILE)
            except Exception as e:
                print("Erreur sauvegarde auto:", e)

def start_manual_recording():
    """Démarre l'enregistrement manuel (ou signale le début en mode micro Pepper)"""
    global recording_thread, recording_active, recording_data, OUTPUT_FILE, recording_stream

    if pepper_mic_mode:
        recording_active = True
        print("Mode micro Pepper : signal start (enregistrement sur le robot)")
        return jsonify({"message": "Enregistrement démarré (micro Pepper)", "status": "recording"})

    # Si un enregistrement est déjà en cours, l'arrêter proprement d'abord
    if recording_active:
        print("⚠️ Un enregistrement est déjà en cours, arrêt avant de redémarrer...")
        recording_active = False

        # Attendre que le thread se termine
        if recording_thread:
            recording_thread.join(timeout=1)

        # Arrêter le stream si nécessaire
        if recording_stream:
            try:
                recording_stream.stop()
            except Exception:
                pass
            recording_stream = None

        # Réinitialiser les données
        recording_data = []
        time.sleep(0.3)  # Petite pause pour s'assurer que tout est arrêté

    # Générer un nouveau nom de fichier
    OUTPUT_FILE = f"{RECORDINGS_DIR}/{time.strftime('%Y%m%d_%H%M%S')}_voice.wav"

    recording_active = True
    recording_data = []
    recording_thread = threading.Thread(target=_record_audio_thread)
    recording_thread.daemon = True
    recording_thread.start()

    print("🎤 Enregistrement manuel démarré")
    return jsonify({"message": "Enregistrement démarré", "status": "recording"})

def stop_manual_recording():
    """Arrête l'enregistrement manuel et sauvegarde le fichier"""
    global recording_thread, recording_active, recording_data, OUTPUT_FILE, recording_stream

    print(f"🛑 Tentative d'arrêt de l'enregistrement... (actif: {recording_active})")

    if pepper_mic_mode:
        recording_active = False
        print("Mode micro Pepper : signal stop")
        return jsonify({"message": "Enregistrement arrêté (micro Pepper)", "status": "stopped"})

    if not recording_active:
        print("⚠️ Aucun enregistrement en cours")
        return jsonify({
            "message": "Aucun enregistrement en cours",
            "status": "already_stopped"
        })

    recording_active = False

    # Attendre que le thread se termine
    if recording_thread:
        print("⏳ Attente de la fin du thread d'enregistrement...")
        recording_thread.join(timeout=3)
        if recording_thread.is_alive():
            print("⚠️ Thread toujours actif après timeout")

    # Arrêter le stream si nécessaire
    if recording_stream:
        try:
            recording_stream.stop()
            print("✅ Stream audio arrêté")
        except Exception as e:
            print(f"⚠️ Erreur lors de l'arrêt du stream: {e}")
        recording_stream = None

    # Sauvegarder les données si présentes
    if recording_data and len(recording_data) > 0:
        try:
            audio = np.concatenate(recording_data, axis=0)
            write(OUTPUT_FILE, SAMPLE_RATE, audio)
            print(f"💾 Enregistré sous : {OUTPUT_FILE}")
            file_list = os.listdir(RECORDINGS_DIR)
            return jsonify({
                "message": "Enregistrement terminé",
                "file": f"{RECORDINGS_DIR}/{file_list[-1]}" if file_list else OUTPUT_FILE,
                "status": "saved"
            })
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde: {e}")
            return jsonify({
                "error": f"Erreur lors de la sauvegarde: {str(e)}",
                "status": "error"
            }), 500
    else:
        print("⚠️ Aucune donnée audio à sauvegarder")
        # Retourner un succès quand même pour ne pas bloquer l'interface
        return jsonify({
            "message": "Enregistrement arrêté (pas de données)",
            "status": "stopped_no_data"
        })

def get_recording_status():
    """Retourne l'état actuel de l'enregistrement"""
    global recording_active, OUTPUT_FILE
    return jsonify({
        "recording": recording_active,
        "file": OUTPUT_FILE if not recording_active and OUTPUT_FILE else None
    })


def get_last_recorded_file_path():
    """
    Retourne le chemin du dernier fichier enregistré (pour réservation depuis la tablette).
    Retourne None si aucun enregistrement ou si un enregistrement est en cours.
    """
    global recording_active, OUTPUT_FILE
    if recording_active or not OUTPUT_FILE:
        return None
    if os.path.isfile(OUTPUT_FILE):
        return OUTPUT_FILE
    return None


# ============ WAKE WORD DETECTION ============

def check_wake_word(text):
    """Vérifie si le texte contient un mot déclencheur."""
    if not text:
        return False
    text_lower = text.lower().strip()
    for wake_word in WAKE_WORDS:
        if wake_word in text_lower:
            return True
    return False


def start_wake_word_listening(stop_event):
    """
    Démarre un thread d'écoute wake word avec calibration automatique du bruit de fond.
    stop_event : threading.Event — mis à True pour arrêter proprement le thread.
    """
    global wake_word_detected

    def _wake_word_listener():
        global wake_word_detected
        import queue
        import tempfile
        import scipy.io.wavfile as wav_io

        print("[WakeWord] Demarrage thread d'ecoute...")
        print("[WakeWord] Mots surveilles: {}".format(WAKE_WORDS))

        # Réutiliser le modèle Whisper déjà chargé par Flask
        whisper_model = _shared_whisper_model
        if whisper_model is None:
            try:
                from services.whisper import charge_model_whisper
                print("[WakeWord] Chargement du modele Whisper (fallback)...")
                whisper_model = charge_model_whisper()
            except Exception as e:
                print("[WakeWord] Erreur chargement Whisper: {}".format(e))
                return

        from services.whisper import transcribe_audio

        q = queue.Queue()

        def _audio_callback(indata, frames, time_info, status):
            if status:
                print("[WakeWord] Status audio: {}".format(status))
            q.put(indata.copy())

        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                callback=_audio_callback,
                blocksize=2048
            ):
                # ── Calibration du bruit ambiant (2 secondes) ──────────────────
                calib_levels = []
                calib_end = time.time() + 2.0
                while time.time() < calib_end:
                    try:
                        data = q.get(timeout=0.3)
                        calib_levels.append(_audio_level(data))
                    except queue.Empty:
                        pass
                if calib_levels:
                    noise_floor = sum(calib_levels) / len(calib_levels)
                else:
                    noise_floor = 0.06
                # Seuil parole = bruit_ambiant * 2.0 avec un plancher plus bas
                # pour mieux capter les voix faibles.
                speech_threshold = max(noise_floor * 2.0, WAKE_WORD_SPEECH_THRESHOLD)
                silence_threshold = max(noise_floor * 1.3, 0.02)
                print("[WakeWord] Bruit ambiant={:.4f} | Seuil parole={:.4f} | Seuil silence={:.4f}".format(
                    noise_floor, speech_threshold, silence_threshold))

                audio_buffer = []
                silence_counter = 0
                speaking = False
                # 1.2s de silence à blocksize=2048 @ 16000Hz
                silence_blocks_needed = int(1.2 * SAMPLE_RATE / 2048)
                # Max 6s de buffer pour éviter l'accumulation infinie
                max_buffer_blocks = int(6.0 * SAMPLE_RATE / 2048)

                while not stop_event.is_set():
                    try:
                        data = q.get(timeout=0.5)
                    except queue.Empty:
                        continue

                    level = _audio_level(data)

                    if level > speech_threshold:
                        speaking = True
                        silence_counter = 0
                        audio_buffer.append(data)
                    elif speaking:
                        # En période de silence après parole : on garde quand même l'audio
                        audio_buffer.append(data)
                        silence_counter += 1
                    # else: silence sans avoir parlé → on n'accumule pas

                    # Buffer trop grand → vider sans transcrire (évite accumulation)
                    if len(audio_buffer) > max_buffer_blocks:
                        audio_buffer = []
                        speaking = False
                        silence_counter = 0
                        continue

                    # 1.2s de silence après parole → transcrire
                    if speaking and silence_counter >= silence_blocks_needed:
                        full_audio = np.concatenate(audio_buffer)
                        audio_buffer = []
                        speaking = False
                        silence_counter = 0

                        tmp_path = None
                        try:
                            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                                wav_io.write(tmp.name, SAMPLE_RATE, full_audio)
                                tmp_path = tmp.name

                            result = transcribe_audio(whisper_model, file=tmp_path)
                            text = result.get('text', '')
                            print("[WakeWord] Transcription: '{}'".format(text))

                            if check_wake_word(text):
                                print("[WakeWord] Wake word detecte!")
                                wake_word_detected = True
                        except Exception as e:
                            print("[WakeWord] Erreur transcription: {}".format(e))
                        finally:
                            if tmp_path and os.path.exists(tmp_path):
                                try:
                                    os.remove(tmp_path)
                                except Exception:
                                    pass

        except Exception as e:
            print("[WakeWord] Erreur ouverture micro: {}".format(e))

        print("[WakeWord] Thread termine.")

    listener_thread = threading.Thread(target=_wake_word_listener, daemon=True)
    listener_thread.start()
    return listener_thread


def get_wake_word_status():
    """Retourne l'état de la détection des mots déclencheurs."""
    global wake_word_detected
    return {
        "wake_word_detected": wake_word_detected,
        "wake_words": WAKE_WORDS,
        "enabled": WAKE_WORD_DETECTION_ENABLED
    }


def reset_wake_word_status():
    """Réinitialise le statut du mot déclencheur."""
    global wake_word_detected
    wake_word_detected = False
    return {
        "wake_word_detected": False,
        "message": "Statut réinitialisé"
    }


def start_wake_word_detection():
    """
    Démarre l'écoute des mots déclencheurs en arrière-plan.
    Si le thread est déjà actif, réinitialise juste le flag (évite l'accumulation de threads).
    """
    global wake_word_detected, _wake_word_thread, _wake_word_stop
    wake_word_detected = False

    # Ne démarrer un nouveau thread que si l'ancien est mort
    if _wake_word_thread is not None and _wake_word_thread.is_alive():
        print("[WakeWord] Thread deja actif, flag reset seulement.")
        return {
            "status": "already_running",
            "wake_words": WAKE_WORDS,
            "message": "Thread wake word déjà actif"
        }

    # Signaler l'arrêt de l'ancien stop_event et en créer un neuf
    _wake_word_stop.set()
    _wake_word_stop = threading.Event()

    _wake_word_thread = start_wake_word_listening(_wake_word_stop)

    return {
        "status": "started",
        "wake_words": WAKE_WORDS,
        "message": "Écoute des mots déclencheurs démarrée"
    }


def stop_wake_word_detection():
    """Arrête proprement le thread de détection wake word."""
    global _wake_word_stop
    _wake_word_stop.set()
    print("[WakeWord] Arret demande.")

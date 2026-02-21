import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import time
import os
import threading
from flask import jsonify
SAMPLE_RATE = 16000
THRESHOLD = 0.05     # Seuil de détection de silence (plus bas = moins sensible aux bruits de fond)
SPEECH_THRESHOLD = 0.008  # Tres sensible pour detecter la parole
SILENCE_LEVEL = 0.05   # En dessous = silence (parole typique > 0.05, bruit ambiant < 0.05)
SILENCE_RATIO = 0.7      # Silence = niveau < 70% du pic
SILENCE_ABSOLUTE = 0.06  # Fallback : si niveau < ceci pendant 3s -> arret (sans avoir parle)
SILENCE_DURATION = 2.0  # Pour record_until_silence (GET /record)
SILENCE_DURATION_MANUAL = 2.0  # Secondes de silence pour arret auto (bouton micro)
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

def set_pepper_mic_mode(enabled):
    global pepper_mic_mode
    pepper_mic_mode = bool(enabled)

def get_pepper_mic_mode():
    return pepper_mic_mode


def is_silent(data, threshold):
    return np.abs(data).mean() < threshold

def record_until_silence():
    print("🎤 Parle... j'arrêterai quand tu te tais.")
    
    sd.default.samplerate = SAMPLE_RATE
    sd.default.channels = 1

    recording = []
    silence_start = None

    with sd.InputStream() as stream:
        while True:
            data, overflow = stream.read(1024)
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
            data, overflow = stream.read(1024)
            recording_data.append(data)
            
            level = float(np.abs(data).mean())
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
            except:
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
    """
    Vérifie si le texte contient un mot déclencheur
    
    Args:
        text: Texte à vérifier
    
    Returns:
        bool: True si un mot déclencheur est détecté
    """
    if not text:
        return False
    
    text_lower = text.lower().strip()
    
    for wake_word in WAKE_WORDS:
        if wake_word in text_lower:
            return True
    
    return False


def start_wake_word_listening():
    """
    Démarre l'écoute en arrière-plan pour détecter les mots déclencheurs
    Returns un thread qui écoute en continu
    """
    global wake_word_detected
    
    def _wake_word_listener():
        """Thread qui écoute en arrière-plan pour les mots déclencheurs"""
        global wake_word_detected
        import queue
        
        print("🎤 Démarrage de l'écoute des mots déclencheurs...")
        print(f"   Mots surveillés: {WAKE_WORDS}")
        
        try:
            # Import ici pour éviter les problèmes si whisper n'est pas chargé
            from services.whisper import transcribe_audio
            from services.whisper import charge_model_whisper
            
            # Charger le modèle whisper
            whisper_model = charge_model_whisper()
            
        except Exception as e:
            print(f"❌ Erreur lors du chargement de Whisper: {e}")
            return None
        
        q = queue.Queue()
        
        def _audio_callback(indata, frames, time_info, status):
            """Callback pour traiter l'audio en continu"""
            if status:
                print(f"⚠️ Status audio: {status}")
            q.put(indata.copy())
        
        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                callback=_audio_callback,
                blocksize=4096
            ) as stream:
                print("🎤 Écoute active pour les mots déclencheurs...")
                
                # Buffer pour accumuler l'audio
                audio_buffer = []
                silence_counter = 0
                speaking = False
                min_audio_length = 1.0  # Minimum 1 seconde pour traiter
                
                while True:
                    try:
                        data = q.get(timeout=1)
                        audio_buffer.append(data)
                        
                        # Vérifier si y a du son
                        if np.abs(data).mean() > THRESHOLD:
                            speaking = True
                            silence_counter = 0
                        elif speaking:
                            silence_counter += 1
                        
                        # Si 2 secondes de silence après avoir parlé, traiter l'audio
                        if speaking and silence_counter > (2.0 * SAMPLE_RATE / 4096):
                            # Combiner l'audio
                            full_audio = np.concatenate(audio_buffer)
                            
                            # Sauvegarder temporairement
                            import tempfile
                            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                                import scipy.io.wavfile as wav
                                wav.write(tmp.name, SAMPLE_RATE, full_audio)
                                tmp_path = tmp.name
                            
                            # Transcrire
                            try:
                                result = transcribe_audio(whisper_model, file=open(tmp_path, 'rb'))
                                text = result.get('text', '')
                                
                                print(f"🔍 Texte détecté: {text}")
                                
                                if check_wake_word(text):
                                    print(f"✅ Mot déclencheur détecté: {text}")
                                    wake_word_detected = True
                                    
                            except Exception as e:
                                print(f"❌ Erreur transcription: {e}")
                            
                            # Nettoyer
                            try:
                                os.remove(tmp_path)
                            except:
                                pass
                            
                            # Réinitialiser
                            audio_buffer = []
                            speaking = False
                            silence_counter = 0
                            
                    except queue.Empty:
                        continue
                    except Exception as e:
                        print(f"❌ Erreur dans l'écoute: {e}")
                        continue
        
        except Exception as e:
            print(f"❌ Erreur démarrage écoute wake word: {e}")
        
        return None
    
    # Démarrer le thread d'écoute
    listener_thread = threading.Thread(target=_wake_word_listener, daemon=True)
    listener_thread.start()
    
    return listener_thread


def get_wake_word_status():
    """
    Retourne l'état de la détection des mots déclencheurs
    
    Returns:
        dict: Statut du wake word
    """
    global wake_word_detected
    return {
        "wake_word_detected": wake_word_detected,
        "wake_words": WAKE_WORDS,
        "enabled": WAKE_WORD_DETECTION_ENABLED
    }


def reset_wake_word_status():
    """
    Réinitialise le statut du mot déclencheur
    
    Returns:
        dict: Statut réinitialisé
    """
    global wake_word_detected
    wake_word_detected = False
    return {
        "wake_word_detected": False,
        "message": "Statut réinitialisé"
    }


def start_wake_word_detection():
    """
    Démarre l'écoute des mots déclencheurs en arrière-plan
    
    Returns:
        dict: Message de confirmation
    """
    global wake_word_detected
    wake_word_detected = False
    
    thread = start_wake_word_listening()
    
    return {
        "status": "started",
        "wake_words": WAKE_WORDS,
        "message": "Écoute des mots déclencheurs démarrée"
    }

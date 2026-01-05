import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import time
import os
import threading
from flask import jsonify
SAMPLE_RATE = 16000
THRESHOLD = 0.05     # Seuil de détection de silence (plus bas = moins sensible aux bruits de fond)
SILENCE_DURATION = 2.0  # Durée de silence nécessaire avant arrêt (en secondes) - augmenté pour permettre des pauses naturelles
RECORDINGS_DIR = "recordings"
os.makedirs(RECORDINGS_DIR, exist_ok=True)

# Générer le chemin du fichier
OUTPUT_FILE = f"{RECORDINGS_DIR}/{time.strftime('%Y%m%d_%H%M%S')}_voice.wav"

# Variables globales pour l'enregistrement manuel
recording_thread = None
recording_data = []
recording_active = False
recording_stream = None


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
    """Thread pour enregistrer l'audio en continu"""
    global recording_data, recording_active, recording_stream
    
    sd.default.samplerate = SAMPLE_RATE
    sd.default.channels = 1
    
    with sd.InputStream() as stream:
        recording_stream = stream
        while recording_active:
            data, overflow = stream.read(1024)
            recording_data.append(data)
            time.sleep(0.01)  # Petite pause pour éviter de surcharger le CPU

def start_manual_recording():
    """Démarre l'enregistrement manuel"""
    global recording_thread, recording_active, recording_data, OUTPUT_FILE, recording_stream
    
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
    
    if not recording_active:
        return jsonify({"error": "Aucun enregistrement en cours"}), 400
    
    recording_active = False
    
    # Attendre que le thread se termine
    if recording_thread:
        recording_thread.join(timeout=2)
    
    if recording_stream:
        try:
            recording_stream.stop()
        except:
            pass
    
    if recording_data:
        audio = np.concatenate(recording_data, axis=0)
        write(OUTPUT_FILE, SAMPLE_RATE, audio)
        print("💾 Enregistré sous :", OUTPUT_FILE)
        file = os.listdir(RECORDINGS_DIR)
        return jsonify({"message": "Enregistrement terminé", "file": f"{RECORDINGS_DIR}/{file[-1]}"})
    else:
        return jsonify({"error": "Aucune donnée enregistrée"}), 400

def get_recording_status():
    """Retourne l'état actuel de l'enregistrement"""
    global recording_active, OUTPUT_FILE
    return jsonify({
        "recording": recording_active,
        "file": OUTPUT_FILE if not recording_active and OUTPUT_FILE else None
    })
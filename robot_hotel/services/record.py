import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import time
import os
from flask import jsonify
SAMPLE_RATE = 16000
THRESHOLD = 0.085    # seuil augmenté → meilleure détection
SILENCE_DURATION = 1.2
RECORDINGS_DIR = "recordings"
os.makedirs(RECORDINGS_DIR, exist_ok=True)

# Générer le chemin du fichier
OUTPUT_FILE = f"{RECORDINGS_DIR}/{time.strftime('%Y%m%d_%H%M%S')}_voice.wav"


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
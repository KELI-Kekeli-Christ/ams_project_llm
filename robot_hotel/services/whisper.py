import os
import subprocess
import torch
import tempfile
from faster_whisper import WhisperModel

# Extensions souvent problématiques (WebM/Opus) : on convertit en WAV avant Whisper
CONVERT_TO_WAV_EXTENSIONS = (".webm", ".ogg", ".mp4", ".m4a", ".opus")

def charge_model_whisper(model_size="medium", force_cpu=False):
    """
    Charge le modèle Faster-Whisper pour une inférence rapide.
    
    Args:
        model_size (str): "tiny", "base", "small", "medium". 
                         "small" est le meilleur compromis vitesse/précision pour Pepper.
        force_cpu (bool): Si True, utilise le CPU.
    """
    # Détection automatique du device et de la quantification
    if torch.cuda.is_available() and not force_cpu:
        device = "cuda"
        compute_type = "float16" # Très rapide sur GPU
    else:
        device = "cpu"
        compute_type = "int8"    # Quantification pour accélérer le CPU sans perdre trop de précision
    
    try:
        print(f"📥 Chargement de Faster-Whisper '{model_size}' sur {device.upper()} ({compute_type})...")
        # Utilisation de WhisperModel de faster-whisper
        model = WhisperModel(model_size, device=device, compute_type=compute_type)
        print(f"✅ Modèle chargé avec succès sur {device}.")
        return model
    except Exception as e:
        print(f"❌ Erreur : {e}")
        # Secours sur le modèle 'base' en cas d'erreur
        return WhisperModel("base", device="cpu", compute_type="int8")

def _convert_to_wav(path: str) -> str:
    """Convertit un fichier audio (webm, mp4, etc.) en WAV via ffmpeg pour éviter 'Error parsing Opus packet header'."""
    wav_path = path + ".wav"
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", path,
                "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                wav_path
            ],
            check=True,
            capture_output=True,
        )
        return wav_path
    except (subprocess.CalledProcessError, FileNotFoundError):
        return path


def transcribe_audio(model, file): 
    """
    Transcrit l'audio de manière optimisée.
    file: chemin (str) ou objet avec .save(destination) (ex: FileStorage).
    Les fichiers WebM/Opus sont convertis en WAV avant transcription pour éviter les erreurs de parsing.
    """
    if isinstance(file, str) and os.path.isfile(file):
        tmp_path = file
        own_tmp = False
    else:
        ext = ".wav"
        if hasattr(file, "filename") and file.filename:
            ext = os.path.splitext(file.filename)[1].lower() or ext
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        own_tmp = True

    wav_path = tmp_path
    own_wav = False
    if tmp_path.lower().endswith(CONVERT_TO_WAV_EXTENSIONS):
        wav_path = _convert_to_wav(tmp_path)
        if wav_path != tmp_path:
            own_wav = True
    
    try:
        # beam_size=1 est beaucoup plus rapide pour du temps réel (greedy decoding)
        # vad_filter=True retire automatiquement les silences pour gagner du temps
        # language="fr" évite les dérives de détection automatique sur des phrases courtes.
        segments, info = model.transcribe(
            wav_path,
            beam_size=1,
            vad_filter=True,
            language="fr",
            condition_on_previous_text=False,
        )
        
        # On concatène les segments (faster-whisper renvoie un générateur)
        text = " ".join([segment.text for segment in segments]).strip()
        
        return {
            "text": text, 
            "language": info.language
        }
    finally:
        if own_wav and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except OSError:
                pass
        if own_tmp and os.path.exists(tmp_path):
            os.remove(tmp_path)
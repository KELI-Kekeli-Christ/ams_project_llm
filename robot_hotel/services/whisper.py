import os
import torch
import tempfile
from faster_whisper import WhisperModel

def charge_model_whisper(model_size="small", force_cpu=False):
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
        print(f"✅ Modèle chargé avec succès.")
        return model
    except Exception as e:
        print(f"❌ Erreur : {e}")
        # Secours sur le modèle 'base' en cas d'erreur
        return WhisperModel("base", device="cpu", compute_type="int8")

def transcribe_audio(model, file): 
    """
    Transcrit l'audio de manière optimisée.
    """
    # Sauvegarde temporaire efficace
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name
    
    try:
        # beam_size=1 est beaucoup plus rapide pour du temps réel (greedy decoding)
        # vad_filter=True retire automatiquement les silences pour gagner du temps
        segments, info = model.transcribe(tmp_path, beam_size=1, vad_filter=True)
        
        # On concatène les segments (faster-whisper renvoie un générateur)
        text = " ".join([segment.text for segment in segments]).strip()
        
        return {
            "text": text, 
            "language": info.language
        }
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
import whisper
import tempfile
import os
import torch


def charge_model_whisper(model_size="medium", force_cpu=True):
    """
    Charge le modèle Whisper.
    
    Args:
        model_size (str): Taille du modèle ("tiny", "base", "small", "medium", "large")
                         Par défaut "medium". Utiliser "small" ou "base" si problème de mémoire.
        force_cpu (bool): Forcer l'utilisation du CPU (par défaut True pour éviter les problèmes GPU)
    
    Returns:
        whisper.Whisper: Le modèle Whisper chargé.
    """
    # Déterminer le device à utiliser
    if force_cpu:
        device = "cpu"
        print(f"⚠️  Mode CPU forcé pour éviter les problèmes de mémoire GPU")
    else:
        device = "cpu"  # Par défaut CPU pour être sûr
        # Optionnel: essayer GPU si disponible et assez de mémoire
        # if torch.cuda.is_available():
        #     try:
        #         free_memory = torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_allocated(0)
        #         if free_memory > 2 * 1024 * 1024 * 1024:  # Plus de 2GB libre
        #             device = "cuda"
        #     except:
        #         pass
    
    try:
        print(f"📥 Chargement du modèle Whisper '{model_size}' sur {device.upper()}...")
        model = whisper.load_model(model_size, device=device)
        print(f"✅ Modèle Whisper '{model_size}' chargé avec succès sur {device.upper()}")
        return model
    except Exception as e:
        print(f"❌ Erreur lors du chargement du modèle '{model_size}': {e}")
        if model_size != "base":
            print(f"⚠️  Tentative avec un modèle plus petit ('base')...")
            try:
                model = whisper.load_model("base", device="cpu")
                print(f"✅ Modèle Whisper 'base' chargé avec succès sur CPU (modèle de secours)")
                return model
            except Exception as e2:
                print(f"❌ Impossible de charger même le modèle 'base': {e2}")
                raise
        else:
            raise

def transcribe_audio(model, file): 
    """
    Transcrit un fichier audio en texte en utilisant le modèle Whisper.
    La langue est détectée automatiquement.
    
    Args:
        model (whisper.Whisper): Le modèle Whisper chargé.
        file: Le fichier audio à transcrire.
    
    Returns:
        dict: Un dictionnaire contenant le texte transcrit et la langue détectée.
    """

    # Utiliser delete=False pour que le fichier existe pendant la transcription
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name
    
    try:
        # Détection automatique de la langue (pas de paramètre language)
        result = model.transcribe(tmp_path)
        text = result.get("text", "")
        language = result.get("language", "")
    finally:
        # Nettoyer le fichier temporaire
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return {"text": text, "language": language}

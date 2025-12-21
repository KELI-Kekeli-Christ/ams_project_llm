import whisper, tempfile
from flask import jsonify


def charge_model_whisper():
    """
    Charge le modèle Whisper.
    
    Returns:
        whisper.Whisper: Le modèle Whisper chargé.
    """
    model = whisper.load_model("medium")
    return model

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
        import os
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return jsonify({"text": text, "language": language})

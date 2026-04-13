"""
Application Flask - Factory et configuration
"""
import os

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request
from flasgger import Swagger
from flask_cors import CORS

from config.swagger import SWAGGER_CONFIG, SWAGGER_TEMPLATE
from services.rag import init_rag
from services.whisper import charge_model_whisper
from services.face_detection import init_face_detection
from routes import (
    chat_bp,
    audio_bp,
    reservation_bp,
    face_bp,
    qr_scan_bp,
    email_bp,
    pages_bp,
    tablet_bp,
    conversation_bp,
)

# Message vocal (mic) : envoi d'un message audio, réponse en texte
ENABLE_VOICE_CALL = os.environ.get("ENABLE_VOICE_CALL", "false").lower() in ("1", "true", "yes")
# Appel vocal (icône téléphone) : vous parlez, la réponse de Pepper est lue en audio sur votre appareil
ENABLE_REALTIME_VOICE_CALL = os.environ.get("ENABLE_REALTIME_VOICE_CALL", "false").lower() in ("1", "true", "yes")
# Mode "vrai appel" : un appui pour parler, 3 s de silence = envoi auto, interrompre Pepper en parlant (true/false)
REALTIME_CALL_VOICE_MODE = os.environ.get("REALTIME_CALL_VOICE_MODE", "false").lower() in ("1", "true", "yes")
# Afficher le bouton « Appel » sur la tablette du robot (true/false)
SHOW_TABLET_CALL_BUTTON = os.environ.get("SHOW_TABLET_CALL_BUTTON", "true").lower() in ("1", "true", "yes")


def create_app():
    """Crée et configure l'application Flask"""
    app = Flask(__name__)
    CORS(app)
    app.config["ENABLE_VOICE_CALL"] = ENABLE_VOICE_CALL
    app.config["ENABLE_REALTIME_VOICE_CALL"] = ENABLE_REALTIME_VOICE_CALL
    app.config["REALTIME_CALL_VOICE_MODE"] = REALTIME_CALL_VOICE_MODE
    app.config["SHOW_TABLET_CALL_BUTTON"] = SHOW_TABLET_CALL_BUTTON

    # Configuration Swagger
    Swagger(app, config=SWAGGER_CONFIG, template=SWAGGER_TEMPLATE)

    # Initialisation des services au démarrage
    init_rag()
    whisper_model = charge_model_whisper()
    init_face_detection()

    app.config['whisper_model'] = whisper_model

    # Partager le modèle Whisper avec le service d'enregistrement (évite double chargement pour wake word)
    from services.record import set_shared_whisper_model
    set_shared_whisper_model(whisper_model)

    # Enregistrement des blueprints
    app.register_blueprint(chat_bp)
    if ENABLE_REALTIME_VOICE_CALL:
        from routes.realtime_voice_ws import init_realtime_voice_ws
        init_realtime_voice_ws(app)
    app.register_blueprint(audio_bp)
    app.register_blueprint(reservation_bp)
    app.register_blueprint(face_bp)
    app.register_blueprint(qr_scan_bp)
    app.register_blueprint(email_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(tablet_bp)
    app.register_blueprint(conversation_bp)

    # Gestionnaire d'erreur 404
    @app.errorhandler(404)
    def page_not_found(e):
        base = request.host_url.rstrip('/')
        html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Page non trouvee</title></head>
<body style="font-family:sans-serif;padding:2em;text-align:center;">
    <h1>Page non trouvee</h1>
    <p>L'URL demandee n'existe pas.</p>
    <p><strong>Pour la tablette Pepper :</strong> ouvrez <a href="{base}/tablet">{base}/tablet</a></p>
    <p><a href="{base}">Retour accueil</a></p>
</body></html>"""
        return html, 404, {'Content-Type': 'text/html; charset=utf-8'}

    return app


app = create_app()

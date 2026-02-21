"""
Routes Chat et QR Code pour accéder au chatbot
"""
from flask import Blueprint, request, render_template, jsonify, current_app
from services.chat import chat
from services.whisper import transcribe_audio
from utils.qr_code import generate_chat_qrcode

bp = Blueprint('chat', __name__)


def get_whisper_model():
    return current_app.config.get('whisper_model')


@bp.route("/chat", methods=["POST"])
def handle_chat():
    """
    Envoie un message au chatbot et reçoit une réponse du modèle Llama 3
    """
    data = request.get_json()
    return chat(user_message=data.get("message", ""), session_id=data.get("session_id"))


@bp.route("/chat", methods=["GET"])
def chat_interface():
    """Interface web pour discuter avec Pepper"""
    enable_voice_call = current_app.config.get("ENABLE_VOICE_CALL", False)
    enable_realtime_voice_call = current_app.config.get("ENABLE_REALTIME_VOICE_CALL", False)
    realtime_call_voice_mode = current_app.config.get("REALTIME_CALL_VOICE_MODE", False)
    return render_template('chat.html',
        enable_voice_call=enable_voice_call,
        enable_realtime_voice_call=enable_realtime_voice_call,
        realtime_call_voice_mode=realtime_call_voice_mode)


@bp.route("/chat/voice", methods=["POST"])
def chat_voice():
    """
    Appel vocal : reçoit un fichier audio, transcrit, envoie au chat, retourne la réponse.
    Utilise la même session que le chat pour mémoire et réservation.
    """
    if not current_app.config.get("ENABLE_VOICE_CALL", False):
        return jsonify({"error": "Voice call disabled"}), 403
    if "file" not in request.files:
        return jsonify({"error": "No audio file"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No audio file"}), 400
    session_id = request.form.get("session_id")
    try:
        model = get_whisper_model()
        result = transcribe_audio(model, file=file)
        text = (result.get("text") or "").strip()
        if not text or len(text) < 2:
            # Audio trop faible ou vide : pas de message (évite de dire "je n'ai pas compris" à chaque fois)
            return jsonify({
                "response": "",
                "session_id": session_id,
                "transcript": ""
            })
        resp = chat(user_message=text, session_id=session_id)
        data = resp.get_json() if hasattr(resp, "get_json") and resp else None
        if data and "response" in data:
            return jsonify({
                "response": data["response"],
                "session_id": data.get("session_id", session_id),
                "transcript": text
            })
        return jsonify({"error": data.get("error", "Chat error") if data else "Chat error", "session_id": session_id}), 500
    except Exception as e:
        return jsonify({"error": str(e), "session_id": session_id}), 500


@bp.route("/chat/qrcode", methods=["GET"])
def chat_qrcode():
    """Génère une image QR code pour l'interface de chat"""
    server_url = request.host_url.rstrip('/')
    chat_url = f"{server_url}/chat"
    img_bytes = generate_chat_qrcode(chat_url, as_base64=False)
    return img_bytes, 200, {'Content-Type': 'image/png'}


@bp.route("/chat/qrcode/html", methods=["GET"])
def chat_qrcode_html():
    """Retourne une page HTML avec le QR code pour accéder au chatbot"""
    server_url = request.host_url.rstrip('/')
    chat_url = f"{server_url}/chat"
    img_base64 = generate_chat_qrcode(chat_url, as_base64=True)

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chat Pepper - QR Code</title>
    <style>
        body {{
            font-family: 'Inter', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #8b5cf6 100%);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            background: white;
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 400px;
            width: 100%;
        }}
        h1 {{ color: #333; margin-bottom: 10px; font-size: 28px; }}
        p {{ color: #666; margin-bottom: 30px; font-size: 16px; }}
        .qr-container {{ margin: 20px 0; }}
        .qr-container img {{
            max-width: 250px;
            border-radius: 10px;
            border: 3px solid #667eea;
        }}
        .url {{
            background: #f5f5f5;
            padding: 10px 15px;
            border-radius: 8px;
            font-family: monospace;
            font-size: 14px;
            color: #555;
            word-break: break-all;
            margin-top: 20px;
        }}
        .buttons {{ margin-top: 30px; display: flex; flex-direction: column; gap: 15px; }}
        .btn {{
            display: inline-block;
            padding: 15px 30px;
            border-radius: 30px;
            text-decoration: none;
            font-weight: bold;
            font-size: 16px;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .btn-primary {{
            background: linear-gradient(135deg, #667eea 0%, #8b5cf6 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
        }}
        .btn-primary:hover {{ transform: translateY(-2px); box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5); }}
        .btn-secondary {{ background: #f0f0f0; color: #333; }}
        .btn-secondary:hover {{ background: #e0e0e0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>💬 Chat avec Pepper</h1>
        <p>Scannez ce QR code avec votre téléphone pour discuter avec le robot</p>
        <div class="qr-container">
            <img src="data:image/png;base64,{img_base64}" alt="QR Code">
        </div>
        <div class="url">{chat_url}</div>
        <div class="buttons">
            <a href="{chat_url}" class="btn btn-primary">Ouvrir le chat</a>
            <a href="/" class="btn btn-secondary">Retour à l'accueil</a>
        </div>
    </div>
</body>
</html>"""

    return html, 200, {'Content-Type': 'text/html'}

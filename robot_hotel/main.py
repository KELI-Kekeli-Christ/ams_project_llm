from flask import Flask, request, jsonify
from services.chat import chat
from services.location import get_heure_date
from services.rag import init_rag
from services.whisper import charge_model_whisper, transcribe_audio
from services.record import record_until_silence
from flask_cors import CORS 
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
init_rag()
model=charge_model_whisper() #charger le model whisper au demarrage

@app.route("/chat", methods=["POST"])
def handle_chat():
    data = request.get_json()
    return chat(user_message = data.get("message", ""))


@app.route("/location", methods=["GET"])
def handle_location():
    return get_heure_date()


@app.route("/transcribe", methods=["POST"])
def handle_transcribe():
    return transcribe_audio(model, file=request.files["file"])


@app.route("/record", methods=["GET"])
def handle_record():
    return record_until_silence()


@app.route("/")
def home():
    return "Serveur Pepper-Llama en ligne 🚀"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

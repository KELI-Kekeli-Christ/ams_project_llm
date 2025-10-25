from flask import Flask, request, jsonify
from openai import OpenAI
import os

app = Flask(__name__)

# Configuration du client OpenAI via Hugging Face
client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key="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",  
)

@app.route("/chat", methods=["POST"])
def chat():
    """
    Endpoint pour recevoir un message et retourner la réponse du modèle Llama 3
    """
    data = request.get_json()
    user_message = data.get("message", "")

    if not user_message:
        return jsonify({"error": "Aucun message fourni."}), 400

    try:
        # Appel au modèle Llama 3 sur Hugging Face
        completion = client.chat.completions.create(
            model="meta-llama/Llama-3.1-8B-Instruct",
            messages=[
                {"role": "system", "content": "Tu es un robot Pepper amical et poli."},
                {"role": "user", "content": user_message}
            ],
        )

        response = completion.choices[0].message.content
        return jsonify({"response": response})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/")
def home():
    return "Serveur Pepper-Llama en ligne 🚀"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

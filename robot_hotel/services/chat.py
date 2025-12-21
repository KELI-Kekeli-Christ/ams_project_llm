from flask import request, jsonify
from openai import OpenAI
from services.rag import get_rag_context
import os


# Configuration du client OpenAI via Hugging Face
client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key="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",  
)

def chat(user_message=None):
    """
    Endpoint pour recevoir un message et retourner la réponse du modèle Llama 3
    """    

    if not user_message:
        return jsonify({"error": "Aucun message fourni."}), 400

    try:
        # Appel au modèle Llama 3 sur Hugging Face
        rag_context = get_rag_context(user_message,top_k=3)
        context_prompt = f"Contexte de l'hôtel :\n{rag_context}\n\n" if rag_context else ""
        completion = client.chat.completions.create(
            model="meta-llama/Llama-3.1-8B-Instruct",
            messages=[
                {"role": "system", "content": "Tu es un assistant amical et poli . Dans tes reponses soit bref précis et concis."},
                {"role": "user", "content": f"{context_prompt} Question : {user_message}"}
            ],
        )

        response = completion.choices[0].message.content
        return jsonify({"response": response, "context_used": rag_context})

    except Exception as e:
        return jsonify({"error": str(e)}), 500







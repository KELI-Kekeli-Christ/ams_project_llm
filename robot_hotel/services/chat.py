from flask import request, jsonify
from openai import OpenAI
from services.rag import get_rag_context
from services.location import get_heure_date
import os


# Configuration du client OpenAI via Hugging Face
client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key="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",  
)

def chat(user_message=None):
    """
    Endpoint pour recevoir un message et retourner la réponse du modèle Llama 3
    La date et l'heure actuelles sont automatiquement intégrées dans le contexte
    """    

    if not user_message:
        return jsonify({"error": "Aucun message fourni."}), 400

    try:
        # Récupérer la date et l'heure actuelles
        current_datetime = get_heure_date()
        
        # Appel au modèle Llama 3 sur Hugging Face
        rag_context = get_rag_context(user_message, top_k=3)
        
        # Construire le prompt avec le contexte RAG et la date/heure
        context_prompt = ""
        if rag_context:
            context_prompt = f"Contexte de l'hôtel :\n{rag_context}\n\n"
        
        # Prompt système incluant la date/heure actuelle
        system_content = f"""Tu es un assistant amical et poli pour un hôtel. Dans tes réponses, sois bref, précis et concis.

INFORMATION TEMPORELLE IMPORTANTE :
{current_datetime}

Cette information te permet de :
- Répondre correctement aux questions sur la date et l'heure actuelles
- Interpréter les références temporelles relatives (ex: "demain", "dans 3 jours", "la semaine prochaine")
- Contextualiser tes réponses en fonction du moment actuel
- Aider à convertir les dates relatives en dates absolues si nécessaire"""
        
        user_content = f"{context_prompt}Question : {user_message}"
        
        completion = client.chat.completions.create(
            model="meta-llama/Llama-3.1-8B-Instruct",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content}
            ],
        )

        response = completion.choices[0].message.content
        return jsonify({
            "response": response, 
            "context_used": rag_context,
            "current_datetime": current_datetime
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500







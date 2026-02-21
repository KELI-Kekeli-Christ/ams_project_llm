"""
Configuration Swagger pour la documentation API
"""

SWAGGER_CONFIG = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/api-docs"
}

SWAGGER_TEMPLATE = {
    "swagger": "2.0",
    "info": {
        "title": "Pepper-Llama Hotel API",
        "description": "API pour le robot hôtel Pepper avec intégration Llama 3, Whisper, et gestion de réservations",
        "version": "1.0.0",
        "contact": {"name": "API Support"}
    },
    "basePath": "/",
    "schemes": ["http", "https"],
    "tags": [
        {"name": "Chat", "description": "Endpoints pour la conversation avec le modèle Llama 3"},
        {"name": "Audio", "description": "Endpoints pour la transcription et l'enregistrement audio"},
        {"name": "Reservation", "description": "Endpoints pour la gestion des réservations"},
        {"name": "Face Detection", "description": "Endpoints pour la détection et reconnaissance faciale"},
        {"name": "System", "description": "Endpoints système"},
        {"name": "QR Code", "description": "Endpoints pour le scan et vérification de QR codes"},
    ]
}

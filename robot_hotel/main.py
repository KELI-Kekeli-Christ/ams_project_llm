#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Point d'entrée principal du serveur Pepper Hotel.

L'application est décomposée en modules pour une maintenance évolutive :
- app.py          : Factory Flask et configuration
- config/         : Configuration (Swagger, etc.)
- routes/         : Blueprints par domaine (chat, audio, reservation, face, qr_scan, email, pages, tablet)
- utils/          : Utilitaires (qr_code, etc.)
- ui/             : Interfaces HTML (tablette)
- services/       : Logique métier (chat, whisper, record, make_reservation, etc.)

Lancement : python main.py
"""
from app import app

if __name__ == "__main__":
    import os
    debug = os.environ.get("FLASK_DEBUG", "true").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=5000, debug=debug)

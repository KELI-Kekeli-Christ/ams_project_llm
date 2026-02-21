# Structure du projet Robot Hotel

Ce document décrit l'organisation du code pour une maintenance évolutive.

## Point d'entrée

- **`main.py`** : Lance le serveur Flask (port 5000)

## Architecture

```
robot_hotel/
├── app.py                 # Factory Flask, configuration, enregistrement des blueprints
├── main.py                # Point d'entrée

├── config/
│   └── swagger.py         # Configuration Swagger/OpenAPI

├── routes/                # Blueprints par domaine
│   ├── chat.py            # Chat + endpoints QR code chatbot
│   ├── audio.py           # Transcription, enregistrement, wake word
│   ├── reservation.py     # Réservations, validation, confirmation
│   ├── face.py            # Détection et reconnaissance faciale
│   ├── qr_scan.py         # Scan QR codes (réservations)
│   ├── email_routes.py    # Configuration email
│   ├── pages.py           # Accueil, test, location
│   └── tablet.py          # Interface tablette Pepper

├── utils/
│   └── qr_code.py         # Génération QR code, détection, vérification

├── ui/
│   └── tablet_html.py     # HTML pour la tablette Pepper

├── services/              # Logique métier (inchangé)
│   ├── chat.py
│   ├── whisper.py
│   ├── record.py
│   ├── make_reservation.py
│   ├── email.py
│   ├── face_detection.py
│   └── ...

└── templates/             # Templates Jinja2
    ├── chat.html          # Interface chat (avec bouton QR Code)
    ├── robot_test.html
    ├── validation.html
    └── ...
```

## Accès au QR Code du chatbot

- **URL** : `/chat/qrcode/html` — page avec QR code généré
- **Image** : `/chat/qrcode` — image PNG du QR code
- **Bouton** : dans l'interface chat (header) et sur la page d'accueil

Le QR code est généré avec la bibliothèque Python `qrcode` et pointe vers l'URL du chatbot.

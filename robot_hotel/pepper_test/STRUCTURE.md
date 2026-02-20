# Structure du projet Pepper Test

Décomposition du script monolithique (2700+ lignes) en modules pour une maintenance évolutive.

## Point d'entrée

- **`main.py`** : Importe choreographe (setup env), puis lance la conversation

## Architecture

```
pepper_test/
├── main.py              # Point d'entrée (20 lignes)

├── config.py            # ROBOT_CONFIG, API_CONFIG, CHOREGRAPHE_PATH

├── choreographe.py      # Setup environnement Choregraphe (sys.path, LD_LIBRARY_PATH)

├── robot_manager.py     # RobotManager : connexion NAOqi, TTS, tablette, vidéo, reconnaissance faciale

├── flask_utils.py       # check_flask_server, start_flask_server_background, post_file_with_retries

├── api_client.py        # record_audio, record_audio_manual, transcribe_audio, chat_with_api,
│                        # make_reservation_with_api, scan_qr_code_with_api, is_reservation_request, is_qr_scan_request

├── conversation.py      # Boucle de conversation interactive (run_conversation)

├── utils/
│   ├── helpers.py       # safe_print, transliterate_to_ascii, escape_html, force_utf8,
│   │                    # get_local_ip_for_robot, map_language_code_to_ald_label
│   └── tts.py           # safe_say (synthèse vocale sécurisée)

└── ui/
    └── tablet_html.py   # create_tablet_html (HTML pour la tablette Pepper)
```

## Lancement

```bash
cd robot_hotel/pepper_test
python main.py
```

**Note :** Le SDK NAOqi (Choregraphe) utilise Python 2.7. Pour une compatibilité complète avec le robot Pepper, exécutez avec Python 2.7. Le serveur Flask (robot_hotel/main.py) doit être démarré au préalable, ou sera lancé automatiquement si possible.

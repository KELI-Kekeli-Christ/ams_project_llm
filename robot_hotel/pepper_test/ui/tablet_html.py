#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tablet HTML generation for pepper_test module.
"""

from utils.helpers import force_utf8, escape_html, transliterate_to_ascii, get_local_ip_for_robot


def create_tablet_html(title, message, subtitle="", status="", show_mic_button=False, mic_active=False, api_url=None, robot_ip=None, show_chat_button=False, show_qr_button=False):
    """
    Crée un contenu HTML pour la tablette avec un bouton micro interactif et/ou un bouton chat
    
    Args:
        title: Titre principal
        message: Message principal
        subtitle: Sous-titre (optionnel)
        status: Statut/étape actuelle (optionnel)
        show_mic_button: Afficher le bouton micro (optionnel)
        mic_active: État du bouton micro (True = actif/enregistrement)
        api_url: URL de l'API Flask pour les requêtes (optionnel)
        robot_ip: IP du robot pour calculer l'IP locale (optionnel)
        show_chat_button: Afficher le bouton chat (optionnel)
    
    Returns:
        str: Contenu HTML
    """
    # Force values to UTF-8-safe strings first (helps Pepper/tablet compatibility)
    title = force_utf8(title)
    message = force_utf8(message)
    subtitle = force_utf8(subtitle)
    status = force_utf8(status)

    # Prepare status text safely (escape then transliterate to ASCII fallback)
    if status:
        status_text_escaped = escape_html(status)
        status_text_safe = transliterate_to_ascii(status_text_escaped)
        status_html = "<div style='background-color: #ffffff; color: #667eea; padding: 10px; border-radius: 5px; margin-bottom: 20px; font-size: 18px; font-weight: bold;'>{}</div>".format(status_text_safe)
    else:
        status_html = ""
    
    # URL de l'API Flask (par défaut localhost:5000)
    # Si show_mic_button est True et api_url n'est pas fourni, calculer l'IP locale
    if api_url is None:
        if show_mic_button and robot_ip:
            # Pour le bouton micro, on a besoin d'une IP accessible depuis le robot
            local_ip = get_local_ip_for_robot(robot_ip)
            api_url = "http://{}:5000".format(local_ip)
        else:
            from api.flask_check import API_CONFIG
            api_url = API_CONFIG["base_url"]
    
    # URL de l'API injectée côté serveur pour que la tablette (et le WebView du robot) appelle le bon serveur
    if api_url:
        api_url_js = 'var apiUrl = "' + api_url.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ') + '";'
    else:
        api_url_js = "var apiUrl = (window.location.protocol + '//' + window.location.host);"
    # Variables JavaScript globales et fonction makeRequest
    global_js = """
        {}
        console.log('API URL:', apiUrl);
        
        // Fonction pour faire une requête HTTP (compatible avec les anciens navigateurs)
        function makeRequest(url, method, callback) {{
            var xhr = new XMLHttpRequest();
            xhr.open(method, url, true);
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.onreadystatechange = function() {{
                if (xhr.readyState === 4) {{
                    if (xhr.status >= 200 && xhr.status < 300) {{
                        callback(true, xhr.responseText);
                    }} else {{
                        callback(false, xhr.statusText);
                    }}
                }}
            }};
            xhr.onerror = function() {{
                callback(false, 'Erreur de connexion');
            }};
            xhr.send();
        }}
    """.format(api_url_js)
    
    # Bouton micro simplifié pour compatibilité Pepper
    mic_button_html = ""
    if show_mic_button:
        mic_color = "#ff4444" if mic_active else "#4CAF50"
        mic_border_color = "#cc0000" if mic_active else "#2E7D32"
        mic_size = "140px" if mic_active else "120px"
        button_text = "STOP" if mic_active else "MIC"
        instruction_text = "Appuyez pour arreter" if mic_active else "Appuyez pour parler"
        
        # Bouton micro avec JavaScript pour contrôler l'enregistrement et détecter les mots déclencheurs
        mic_button_html = """
        <div style="margin-top: 40px; margin-bottom: 20px; text-align: center;">
            <button id="micButton" onclick="toggleRecording()" style="
                background-color: {};
                border: 5px solid {};
                border-radius: 50%;
                width: {};
                height: {};
                cursor: pointer;
                color: white;
                font-size: 40px;
                font-weight: bold;
                margin: 0 auto;
                display: block;
            ">
                {}
            </button>
            <p style="margin-top: 20px; font-size: 24px; font-weight: bold; color: white;">
                MICROPHONE
            </p>
            <p id="instruction" style="margin-top: 10px; font-size: 18px; color: white;">
                {}
            </p>
            <p style="margin-top: 10px; font-size: 14px; color: #ddd;">
                Dites "bonjour", "hello" ou "hola" pour activer automatiquement
            </p>
        </div>
        <script>
            var isRecording = {};
            var wakeWordCheckInterval = null;
            
            function toggleRecording() {{
                var btn = document.getElementById('micButton');
                var instruction = document.getElementById('instruction');
                
                if (!isRecording) {{
                    // Démarrer l'enregistrement
                    instruction.textContent = 'Demarrage...';
                    makeRequest(apiUrl + '/record/start', 'POST', function(success, response) {{
                        if (success) {{
                            isRecording = true;
                            btn.style.backgroundColor = '#ff4444';
                            btn.style.borderColor = '#cc0000';
                            btn.innerHTML = 'STOP';
                            instruction.textContent = 'Parlez maintenant... Appuyez pour arreter';
                            // Démarrer la vérification du wake word
                            startWakeWordCheck();
                        }} else {{
                            instruction.textContent = 'Erreur: ' + response;
                            console.error('Erreur demarrage:', response);
                        }}
                    }});
                }} else {{
                    // Arrêter l'enregistrement puis lancer la réservation depuis le dernier fichier
                    instruction.textContent = 'Arret...';
                    makeRequest(apiUrl + '/record/stop', 'POST', function(success, response) {{
                        if (success) {{
                            isRecording = false;
                            btn.style.backgroundColor = '#4CAF50';
                            btn.style.borderColor = '#2E7D32';
                            btn.innerHTML = 'MIC';
                            instruction.textContent = 'Traitement en cours...';
                            stopWakeWordCheck();
                            // Réservation par audio : utiliser le dernier enregistrement
                            makeRequest(apiUrl + '/make_reservation_from_last', 'POST', function(resSuccess, resResponse) {{
                                if (resSuccess) {{
                                    try {{
                                        var data = JSON.parse(resResponse);
                                        if (data.session_id) {{
                                            instruction.textContent = 'Redirection vers validation...';
                                            window.location.href = apiUrl + '/validate?session_id=' + encodeURIComponent(data.session_id);
                                            return;
                                        }}
                                    }} catch(e) {{}}
                                }}
                                instruction.textContent = 'Enregistrement termine. Parlez pour reserver.';
                            }});
                        }} else {{
                            instruction.textContent = 'Erreur: ' + response;
                            console.error('Erreur arret:', response);
                        }}
                    }});
                }}
            }}
            
            // Vérifier automatiquement si un mot déclencheur a été détecté
            function checkWakeWord() {{
                makeRequest(apiUrl + '/record/wake_word/status', 'GET', function(success, response) {{
                    if (success) {{
                        try {{
                            var data = JSON.parse(response);
                            if (data.wake_word_detected) {{
                                console.log('Mot déclencheur détecté!');
                                var btn = document.getElementById('micButton');
                                var instruction = document.getElementById('instruction');
                                
                                // Démarrer l'enregistrement automatiquement
                                if (!isRecording) {{
                                    isRecording = true;
                                    btn.style.backgroundColor = '#ff4444';
                                    btn.style.borderColor = '#cc0000';
                                    btn.innerHTML = 'STOP';
                                    instruction.textContent = 'Mot détecté! Parlez...';
                                    
                                    // Faire une requête pour démarrer l'enregistrement côté serveur
                                    makeRequest(apiUrl + '/record/start', 'POST', function(s, r) {{}});
                                }}
                                
                                // Réinitialiser le flag wake word
                                makeRequest(apiUrl + '/record/wake_word/reset', 'POST', function(s, r) {{}});
                            }}
                        }} catch(e) {{
                            console.error('Erreur parsing wake word status:', e);
                        }}
                    }}
                }});
            }}
            
            function startWakeWordCheck() {{
                // Vérifier toutes les 2 secondes si un mot déclencheur a été détecté
                wakeWordCheckInterval = setInterval(checkWakeWord, 2000);
            }}
            
            function stopWakeWordCheck() {{
                if (wakeWordCheckInterval) {{
                    clearInterval(wakeWordCheckInterval);
                    wakeWordCheckInterval = null;
                }}
            }}
            
            // Démarrer automatiquement l'écoute des mots déclencheurs au chargement
            window.onload = function() {{
                console.log('Démarrage de l\'écoute des mots déclencheurs...');
                makeRequest(apiUrl + '/record/wake_word/start', 'POST', function(success, response) {{
                    if (success) {{
                        console.log('Écoute wake word démarrée');
                        startWakeWordCheck();
                    }} else {{
                        console.error('Erreur démarrage wake word');
                    }}
                }});
            }};
        </script>
        """.format(
            mic_color,
            mic_border_color,
            mic_size,
            mic_size,
            button_text,
            instruction_text,
            "true" if mic_active else "false"
        )
    
    # Bouton Chat pour ouvrir l'interface de chat
    chat_button_html = ""
    if show_chat_button:
        chat_button_html = """
        <div style="margin-top: 20px; text-align: center;">
            <a href="/chat/qrcode/html" target="_self" style="
                display: inline-block;
                background-color: #8b5cf6;
                color: white;
                padding: 15px 40px;
                border-radius: 30px;
                font-size: 22px;
                font-weight: bold;
                text-decoration: none;
                box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4);
                margin: 10px;
            ">
                💬 Chat
            </a>
        </div>
        """
    
    # Bouton QR Code pour scanner les réservations
    qr_button_html = ""
    if show_qr_button:
        qr_button_html = """
        <div style="margin-top: 20px; text-align: center;">
            <button onclick="startQRScanner()" style="
                background-color: #f59e0b;
                color: white;
                padding: 15px 40px;
                border-radius: 30px;
                font-size: 22px;
                font-weight: bold;
                border: none;
                cursor: pointer;
                box-shadow: 0 4px 15px rgba(245, 158, 11, 0.4);
                margin: 10px;
            ">
                📱 Scanner QR Code
            </button>
            <div id="qrResult" style="margin-top: 15px; padding: 15px; background-color: rgba(255,255,255,0.9); border-radius: 10px; display: none;">
                <p id="qrResultText" style="color: #333; font-size: 16px; margin: 0;"></p>
            </div>
        </div>
        <script>
            function startQRScanner() {
                // Essayer d'accéder à la caméra pour scanner QR
                navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
                    .then(function(stream) {
                        // Créer un élément vidéo pour le scanner
                        var video = document.createElement('video');
                        video.setAttribute('style', 'width: 100%; max-width: 400px; border-radius: 10px;');
                        video.srcObject = stream;
                        video.play();
                        
                        // Demander au serveur de démarrer le scan
                        makeRequest(apiUrl + '/scan_qr/stream/start', 'POST', function(success, response) {
                            if (success) {
                                document.getElementById('qrResult').style.display = 'block';
                                document.getElementById('qrResultText').textContent = 'Scanner actif! Présentez votre QR code...';
                                
                                // Arrêter après 30 secondes
                                setTimeout(function() {
                                    stream.getTracks().forEach(track => track.stop());
                                    makeRequest(apiUrl + '/scan_qr/stream/stop', 'POST', function() {});
                                }, 30000);
                            } else {
                                document.getElementById('qrResult').style.display = 'block';
                                document.getElementById('qrResultText').textContent = 'Erreur: ' + response;
                            }
                        });
                    })
                    .catch(function(err) {
                        // Si pas de caméra, proposer l'interface de scan
                        document.getElementById('qrResult').style.display = 'block';
                        document.getElementById('qrResultText').innerHTML = 'Camera non disponible.<br><a href="/chat/qrcode/html" style="color: #667eea;">Cliquez ici pour ouvrir le scanner</a>';
                    });
            }
            
            // Vérifier le résultat du scan QR périodiquement
            setInterval(function() {
                makeRequest(apiUrl + '/scan_qr/stream/status', 'GET', function(success, response) {
                    if (success) {
                        try {
                            var data = JSON.parse(response);
                            if (data.result && data.result.success) {
                                document.getElementById('qrResult').style.display = 'block';
                                document.getElementById('qrResultText').innerHTML = '<strong style="color: #10b981;">✓ Réservation trouvée!</strong><br>' + 
                                    'Client: ' + (data.result.client ? data.result.client.nom : 'N/A');
                            }
                        } catch(e) {}
                    }
                });
            }, 2000);
        </script>
        """
    
    # Prepare subtitle safely for HTML
    try:
        if isinstance(subtitle, bytes):
            subtitle = subtitle.decode('utf-8', errors='ignore')
    except Exception:
        subtitle = str(subtitle)
    subtitle_escaped = escape_html(subtitle)
    try:
        title_escaped = escape_html(title)
    except Exception:
        title_escaped = escape_html(str(title))
    try:
        message_escaped = escape_html(message)
    except Exception:
        message_escaped = escape_html(str(message))

    # Also create ASCII-safe fallbacks (remove accents and emojis) for environments that don't support UTF-8
    title_safe = transliterate_to_ascii(title_escaped)
    message_safe = transliterate_to_ascii(message_escaped)
    subtitle_safe = transliterate_to_ascii(subtitle_escaped)

    # HTML simplifié pour une meilleure compatibilité avec Pepper
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pepper</title>
    <script>
        {}
    </script>
</head>
<body style="background-color: #667eea; color: white; font-family: Arial, sans-serif; padding: 20px; text-align: center; margin: 0;">
    <div style="background-color: #8a9eff; border-radius: 15px; padding: 30px; margin: 20px auto; max-width: 90%;">
        {}
        <h1 style="font-size: 36px; margin: 15px 0; color: white;">{}</h1>
        <div style="background-color: #9aafff; border-radius: 10px; padding: 20px; margin: 20px 0;">
            <p style="font-size: 24px; line-height: 1.6; margin: 0; color: white;">{}</p>
        </div>
        {}
        {}
        {}
        {}
    </div>
</body>
</html>""".format(
        global_js,
        status_html,
        title_safe,
        message_safe,
        "<div style='margin-top: 20px; padding: 15px; background-color: #9aafff; border-radius: 8px;'><p style='font-size: 18px; margin: 0; color: white;'><strong>Vous:</strong> {}</p></div>".format(subtitle_safe) if subtitle else "",
        mic_button_html,
        chat_button_html,
        qr_button_html
    )
    return html


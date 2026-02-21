# -*- coding: utf-8 -*-
"""
Interface HTML pour la tablette du robot Pepper
"""

from utils import force_utf8, escape_html, transliterate_to_ascii, get_local_ip_for_robot
from config import API_CONFIG


def create_tablet_html(title, message, subtitle="", status="", show_mic_button=False, mic_active=False, api_url=None, robot_ip=None):
    """
    Crée un contenu HTML pour la tablette avec un bouton micro interactif
    
    Args:
        title: Titre principal
        message: Message principal
        subtitle: Sous-titre (optionnel)
        status: Statut/étape actuelle (optionnel)
        show_mic_button: Afficher le bouton micro (optionnel)
        mic_active: État du bouton micro (True = actif/enregistrement)
        api_url: URL de l'API Flask pour les requêtes (optionnel)
        robot_ip: IP du robot pour calculer l'IP locale (optionnel)
    
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
            api_url = API_CONFIG["base_url"]
    
    # Bouton micro simplifié pour compatibilité Pepper
    mic_button_html = ""
    if show_mic_button:
        mic_color = "#ff4444" if mic_active else "#4CAF50"
        mic_border_color = "#cc0000" if mic_active else "#2E7D32"
        mic_size = "140px" if mic_active else "120px"
        button_text = "STOP" if mic_active else "MIC"
        instruction_text = "Appuyez pour arreter" if mic_active else "Appuyez pour parler"
        
        # Bouton micro avec JavaScript pour contrôler l'enregistrement
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
        </div>
        <script>
            var isRecording = {};
            var apiUrl = '{}';
            
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
                        }} else {{
                            instruction.textContent = 'Erreur: ' + response;
                            console.error('Erreur demarrage:', response);
                        }}
                    }});
                }} else {{
                    // Arrêter l'enregistrement
                    instruction.textContent = 'Arret...';
                    makeRequest(apiUrl + '/record/stop', 'POST', function(success, response) {{
                        if (success) {{
                            isRecording = false;
                            btn.style.backgroundColor = '#4CAF50';
                            btn.style.borderColor = '#2E7D32';
                            btn.innerHTML = 'MIC';
                            instruction.textContent = 'Enregistrement termine';
                        }} else {{
                            instruction.textContent = 'Erreur: ' + response;
                            console.error('Erreur arret:', response);
                        }}
                    }});
                }}
            }}
            
            // Afficher l'URL de l'API pour debug
            console.log('API URL:', apiUrl);
        </script>
        """.format(
            mic_color,
            mic_border_color,
            mic_size,
            mic_size,
            button_text,
            instruction_text,
            "true" if mic_active else "false",
            api_url
        )
    
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
    </div>
</body>
</html>""".format(
        status_html,
        title_safe,
        message_safe,
        "<div style='margin-top: 20px; padding: 15px; background-color: #9aafff; border-radius: 8px;'><p style='font-size: 18px; margin: 0; color: white;'><strong>Vous:</strong> {}</p></div>".format(subtitle_safe) if subtitle else "",
        mic_button_html
    )
    return html
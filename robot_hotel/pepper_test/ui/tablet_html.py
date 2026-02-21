# -*- coding: utf-8 -*-
"""
Génération HTML pour la tablette Pepper
"""
from config import API_CONFIG, SHOW_TABLET_CALL_BUTTON
from utils.helpers import (
    force_utf8,
    escape_html,
    transliterate_to_ascii,
    get_local_ip_for_robot,
)


def create_tablet_html(
    title,
    message,
    subtitle="",
    status="",
    show_mic_button=False,
    mic_active=False,
    api_url=None,
    show_call_button=None,
    robot_ip=None,
):
    """Crée le HTML pour la tablette avec bouton micro et optionnellement bouton Appel.
    show_call_button: True/False pour forcer, None = utiliser SHOW_TABLET_CALL_BUTTON (config/env).
    """
    if show_call_button is None:
        show_call_button = SHOW_TABLET_CALL_BUTTON
    title = force_utf8(title)
    message = force_utf8(message)
    subtitle = force_utf8(subtitle)
    status = force_utf8(status)

    status_html = ""
    if status:
        status_text_escaped = escape_html(status)
        status_text_safe = transliterate_to_ascii(status_text_escaped)
        status_html = "<div style='background-color: #ffffff; color: #667eea; padding: 10px; border-radius: 5px; margin-bottom: 20px; font-size: 18px; font-weight: bold;'>{}</div>".format(status_text_safe)

    if api_url is None:
        if show_mic_button and robot_ip:
            local_ip = get_local_ip_for_robot(robot_ip)
            api_url = "http://{}:5000".format(local_ip)
        else:
            api_url = API_CONFIG["base_url"]

    mic_button_html = ""
    if show_mic_button:
        mic_color = "#ff4444" if mic_active else "#4CAF50"
        mic_border_color = "#cc0000" if mic_active else "#2E7D32"
        mic_size = "140px" if mic_active else "120px"
        button_text = "STOP" if mic_active else "MIC"
        instruction_text = "Parlez... arret auto (2 sec silence) ou STOP" if mic_active else "Cliquez pour parler"
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
            ">{}</button>
            <p style="margin-top: 20px; font-size: 24px; font-weight: bold; color: white;">MICROPHONE</p>
            <p id="instruction" style="margin-top: 10px; font-size: 18px; color: white;">{}</p>
        </div>
        <script>
            var isRecording = {};
            var apiUrl = '{}';
            function makeRequest(url, method, callback) {{
                var xhr = new XMLHttpRequest();
                xhr.open(method, url, true);
                xhr.setRequestHeader('Content-Type', 'application/json');
                xhr.onreadystatechange = function() {{
                    if (xhr.readyState === 4) {{
                        callback(xhr.status >= 200 && xhr.status < 300, xhr.status >= 200 ? xhr.responseText : xhr.statusText);
                    }}
                }};
                xhr.onerror = function() {{ callback(false, 'Erreur de connexion'); }};
                xhr.send();
            }}
            function toggleRecording() {{
                var btn = document.getElementById('micButton');
                var instruction = document.getElementById('instruction');
                if (!isRecording) {{
                    instruction.textContent = 'Demarrage...';
                    makeRequest(apiUrl + '/record/start', 'POST', function(success, response) {{
                        if (success) {{
                            isRecording = true;
                            btn.style.backgroundColor = '#ff4444';
                            btn.style.borderColor = '#cc0000';
                            btn.innerHTML = 'STOP';
                            instruction.textContent = 'Parlez... arret auto apres 2 sec de silence';
                        }} else {{ instruction.textContent = 'Erreur: ' + response; }}
                    }});
                }} else {{
                    instruction.textContent = 'Arret...';
                    makeRequest(apiUrl + '/record/stop', 'POST', function(success, response) {{
                        if (success) {{
                            isRecording = false;
                            btn.style.backgroundColor = '#4CAF50';
                            btn.style.borderColor = '#2E7D32';
                            btn.innerHTML = 'MIC';
                            instruction.textContent = 'Enregistrement termine';
                        }} else {{ instruction.textContent = 'Erreur: ' + response; }}
                    }});
                }}
            }}
        </script>
        """.format(
            mic_color, mic_border_color, mic_size, mic_size,
            button_text, instruction_text,
            "true" if mic_active else "false",
            api_url
        )

    # Bouton Appel : déclenche l'appel vocal temps réel continu (même logique que web)
    call_button_html = ""
    if show_call_button and api_url:
        call_start_url = api_url.rstrip("/") + "/tablet/call/start"
        call_button_html = """
        <div style="margin-top: 25px; text-align: center;">
            <button type="button" onclick="startCall()" style="
                display: inline-block;
                background-color: #2196F3;
                border: 3px solid #1565C0;
                border-radius: 25px;
                padding: 15px 30px;
                color: white;
                font-size: 22px;
                font-weight: bold;
                cursor: pointer;
            ">APPEL</button>
            <p style="font-size: 14px; color: white; margin-top: 8px;">Appel continu (2 s silence = envoi)</p>
        </div>
        <script>
            function startCall() {
                var btn = document.querySelector('button[onclick=\"startCall()\"]');
                if (btn) { btn.disabled = true; btn.textContent = 'Demande...'; }
                var xhr = new XMLHttpRequest();
                xhr.open('POST', '{}', true);
                xhr.setRequestHeader('Content-Type', 'application/json');
                xhr.onreadystatechange = function() {
                    if (xhr.readyState === 4) {
                        if (btn) { btn.disabled = false; btn.textContent = 'Appel demande'; }
                    }
                };
                xhr.send();
            }
        </script>
        """.format(call_start_url)
    else:
        call_button_html = ""

    # Bouton Chat : affiche le QR code au clic (redirige vers la page chat)
    chat_button_html = ""
    if api_url:
        qr_image_url = "{}/chat/qrcode".format(api_url.rstrip('/'))
        chat_button_html = """
        <div style="margin-top: 20px; text-align: center;">
            <button id="chatBtn" onclick="toggleQrCode()" style="
                background-color: #FF9800;
                border: 3px solid #E65100;
                border-radius: 25px;
                padding: 15px 35px;
                color: white;
                font-size: 22px;
                font-weight: bold;
                cursor: pointer;
            ">CHAT</button>
            <p style="font-size: 14px; color: white; margin-top: 8px;">Scannez le QR code pour discuter</p>
        </div>
        <div id="qrCodeContainer" style="display: none; margin-top: 25px; padding: 20px; background-color: #fff; border-radius: 15px; text-align: center;">
            <p style="color: #333; font-size: 18px; margin-bottom: 15px;">Scannez pour acceder au chat</p>
            <img id="qrImage" src="{}" alt="QR Code Chat" style="max-width: 220px; height: auto; border-radius: 8px;">
            <br>
            <button onclick="toggleQrCode()" style="
                margin-top: 15px;
                background-color: #667eea;
                border: 2px solid #5a6fd6;
                border-radius: 15px;
                padding: 10px 25px;
                color: white;
                font-size: 16px;
                cursor: pointer;
            ">Retour</button>
        </div>
        <script>
            function toggleQrCode() {{
                var container = document.getElementById('qrCodeContainer');
                var chatBtn = document.getElementById('chatBtn');
                if (container.style.display === 'none') {{
                    container.style.display = 'block';
                    if (chatBtn) chatBtn.style.display = 'none';
                }} else {{
                    container.style.display = 'none';
                    if (chatBtn) chatBtn.style.display = 'inline-block';
                }}
            }}
        </script>
        """.format(qr_image_url)

    try:
        if isinstance(subtitle, bytes):
            subtitle = subtitle.decode('utf-8', errors='ignore')
    except Exception:
        subtitle = str(subtitle)
    subtitle_escaped = escape_html(subtitle)
    title_escaped = escape_html(title) if title else ""
    message_escaped = escape_html(message) if message else ""
    title_safe = transliterate_to_ascii(title_escaped)
    message_safe = transliterate_to_ascii(message_escaped)
    subtitle_safe = transliterate_to_ascii(subtitle_escaped)

    subtitle_block = ""
    if subtitle:
        subtitle_block = "<div style='margin-top: 20px; padding: 15px; background-color: #9aafff; border-radius: 8px;'><p style='font-size: 18px; margin: 0; color: white;'><strong>Vous:</strong> {}</p></div>".format(subtitle_safe)

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
        {}
        {}
    </div>
</body>
</html>""".format(status_html, title_safe, message_safe, subtitle_block, mic_button_html, call_button_html, chat_button_html)
    return html

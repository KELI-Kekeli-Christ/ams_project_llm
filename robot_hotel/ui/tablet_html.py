"""
Interface HTML pour la tablette du robot Pepper
Compatible avec l'API Flask du robot hôtel
"""
import html


def _safe_str(s):
    """Convertit en chaîne UTF-8 sûre"""
    if s is None:
        return ""
    if isinstance(s, bytes):
        return s.decode('utf-8', errors='ignore')
    return str(s)


def create_tablet_html(
    title,
    message,
    subtitle="",
    status="",
    show_mic_button=False,
    mic_active=False,
    api_url=None,
    show_qr_button=False,
    show_call_button=False,
    robot_ip=None,
):
    """
    Crée un contenu HTML pour la tablette Pepper.

    Args:
        title: Titre principal
        message: Message principal
        subtitle: Sous-titre (optionnel)
        status: Statut/étape actuelle (optionnel)
        show_mic_button: Afficher le bouton micro
        mic_active: État du bouton micro (True = enregistrement)
        api_url: URL de l'API Flask (ex: http://192.168.1.10:5000)
        show_qr_button: Afficher le bouton pour accéder au QR code du chatbot
        show_call_button: Afficher le bouton Appel (appel vocal temps réel continu)
        robot_ip: IP du robot (optionnel, pour calcul d'URL)

    Returns:
        str: Contenu HTML
    """
    title = _safe_str(title)
    message = _safe_str(message)
    subtitle = _safe_str(subtitle)
    status = _safe_str(status)

    status_html = ""
    if status:
        status_escaped = html.escape(status)
        status_html = f"<div style='background-color: #ffffff; color: #667eea; padding: 10px; border-radius: 5px; margin-bottom: 20px; font-size: 18px; font-weight: bold;'>{status_escaped}</div>"

    if api_url is None:
        api_url = "http://localhost:5000"

    mic_button_html = ""
    if show_mic_button:
        mic_color = "#ff4444" if mic_active else "#4CAF50"
        mic_border_color = "#cc0000" if mic_active else "#2E7D32"
        mic_size = "140px" if mic_active else "120px"
        button_text = "STOP" if mic_active else "MIC"
        instruction_text = "Appuyez pour arreter" if mic_active else "Appuyez pour parler"

        mic_button_html = f"""
        <div style="margin-top: 40px; margin-bottom: 20px; text-align: center;">
            <button id="micButton" onclick="toggleRecording()" style="
                background-color: {mic_color};
                border: 5px solid {mic_border_color};
                border-radius: 50%;
                width: {mic_size};
                height: {mic_size};
                cursor: pointer;
                color: white;
                font-size: 40px;
                font-weight: bold;
                margin: 0 auto;
                display: block;
            ">
                {button_text}
            </button>
            <p style="margin-top: 20px; font-size: 24px; font-weight: bold; color: white;">MICROPHONE</p>
            <p id="instruction" style="margin-top: 10px; font-size: 18px; color: white;">{instruction_text}</p>
        </div>
        <script>
            var isRecording = {"true" if mic_active else "false"};
            var apiUrl = '{api_url}';
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
                            instruction.textContent = 'Parlez maintenant... Appuyez pour arreter';
                        }} else {{
                            instruction.textContent = 'Erreur: ' + response;
                        }}
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
                        }} else {{
                            instruction.textContent = 'Erreur: ' + response;
                        }}
                    }});
                }}
            }}
        </script>
        """

    call_button_html = ""
    if show_call_button and api_url:
        call_start_url = api_url.rstrip("/") + "/tablet/call/start"
        call_button_html = f"""
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
            ">📞 Appel</button>
            <p style="font-size: 14px; color: white; margin-top: 8px;">Appel vocal continu (2 s silence = envoi)</p>
        </div>
        <script>
            function startCall() {{
                var btn = document.querySelector('button[onclick="startCall()"]');
                if (btn) {{ btn.disabled = true; btn.textContent = 'Demande...'; }}
                var xhr = new XMLHttpRequest();
                xhr.open('POST', '{call_start_url}'.replace(/^http:/, window.location.protocol === 'https:' ? 'https:' : 'http:'), true);
                xhr.setRequestHeader('Content-Type', 'application/json');
                xhr.onreadystatechange = function() {{
                    if (xhr.readyState === 4) {{
                        if (btn) {{ btn.disabled = false; btn.textContent = 'Appel demandé'; }}
                    }}
                }};
                xhr.send();
            }}
        </script>
        """

    chat_qr_html = ""
    if show_qr_button and api_url:
        chat_url = f"{api_url.rstrip('/')}/chat"
        qr_page_url = f"{api_url.rstrip('/')}/chat/qrcode/html"
        chat_qr_html = f"""
        <div style="margin-top: 30px; text-align: center;">
            <a href="{qr_page_url}" style="
                display: inline-block;
                background-color: #FF9800;
                border: 3px solid #E65100;
                border-radius: 25px;
                padding: 15px 30px;
                color: white;
                font-size: 22px;
                font-weight: bold;
                text-decoration: none;
                cursor: pointer;
            ">📱 QR Code Chatbot</a>
            <p style="font-size: 16px; color: white; margin-top: 10px;">Scannez pour discuter avec Pepper</p>
        </div>
        """

    title_escaped = html.escape(title)
    message_escaped = html.escape(message)
    subtitle_html = ""
    if subtitle:
        subtitle_escaped = html.escape(subtitle)
        subtitle_html = f"<div style='margin-top: 20px; padding: 15px; background-color: #9aafff; border-radius: 8px;'><p style='font-size: 18px; margin: 0; color: white;'><strong>Vous:</strong> {subtitle_escaped}</p></div>"

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pepper</title>
</head>
<body style="background-color: #667eea; color: white; font-family: Arial, sans-serif; padding: 20px; text-align: center; margin: 0;">
    <div style="background-color: #8a9eff; border-radius: 15px; padding: 30px; margin: 20px auto; max-width: 90%;">
        {status_html}
        <h1 style="font-size: 36px; margin: 15px 0; color: white;">{title_escaped}</h1>
        <div style="background-color: #9aafff; border-radius: 10px; padding: 20px; margin: 20px 0;">
            <p style="font-size: 24px; line-height: 1.6; margin: 0; color: white;">{message_escaped}</p>
        </div>
        {subtitle_html}
        {mic_button_html}
        {call_button_html}
        {chat_qr_html}
    </div>
</body>
</html>"""
    return html_content

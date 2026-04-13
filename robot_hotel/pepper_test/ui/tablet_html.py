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
        status_html = "<div class='tablet-status-pill'>{}</div>".format(status_text_safe)

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
        mic_size = "80px" if mic_active else "70px"
        button_text = "STOP" if mic_active else "MIC"
        instruction_text = "Parlez..." if mic_active else "Parler"
        mic_button_html = """
        <div class="tablet-btn-cell tablet-mic-cell">
            <button id="micButton" onclick="toggleRecording()" class="tablet-btn tablet-btn-mic tablet-btn-mic-round" style="background-color:{};border-color:{};width:{};height:{};">🎤 {}</button>
            <p class="tablet-btn-label">Micro</p>
            <p id="instruction" class="tablet-btn-hint">{}</p>
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
                            btn.style.backgroundColor = '#dc2626';
                            btn.style.backgroundImage = 'linear-gradient(145deg, #ef4444, #b91c1c)';
                            btn.style.borderColor = 'rgba(255,255,255,0.3)';
                            btn.innerHTML = '&#9209; STOP';
                            instruction.textContent = 'Parlez... arret auto apres 2 sec de silence';
                        }} else {{ instruction.textContent = 'Erreur: ' + response; }}
                    }});
                }} else {{
                    instruction.textContent = 'Arret...';
                    makeRequest(apiUrl + '/record/stop', 'POST', function(success, response) {{
                        if (success) {{
                            isRecording = false;
                            btn.style.backgroundColor = '';
                            btn.style.backgroundImage = '';
                            btn.style.borderColor = '';
                            btn.innerHTML = '&#127908; MIC';
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

    # Bouton Appel
    call_button_html = ""
    if show_call_button and api_url:
        call_start_url = api_url.rstrip("/") + "/tablet/call/start"
        call_button_html = """
        <div class="tablet-btn-cell">
            <button type="button" onclick="startCall()" class="tablet-btn tablet-btn-call">📞 Appel</button>
            <p class="tablet-btn-label">2 s silence = envoi</p>
        </div>
        <script>
            function startCall() {{
                var btn = document.querySelector('button[onclick="startCall()"]');
                if (btn) {{ btn.disabled = true; btn.textContent = '...'; }}
                var xhr = new XMLHttpRequest();
                xhr.open('POST', '{}', true);
                xhr.setRequestHeader('Content-Type', 'application/json');
                xhr.onreadystatechange = function() {{
                    if (xhr.readyState === 4) {{ if (btn) {{ btn.disabled = false; btn.textContent = 'APPEL'; }} }}
                }};
                xhr.send();
            }}
        </script>
        """.format(call_start_url)
    else:
        call_button_html = ""

    # Bouton Chat
    chat_button_html = ""
    if api_url:
        qr_image_url = "{}/chat/qrcode".format(api_url.rstrip('/'))
        chat_button_html = """
        <div class="tablet-btn-cell">
            <button id="chatBtn" onclick="toggleQrCode()" class="tablet-btn tablet-btn-chat">💬 Chat</button>
            <p class="tablet-btn-label">QR code chat</p>
        </div>
        <div id="qrCodeContainer" class="tablet-overlay" style="display:none;">
            <div class="tablet-overlay-inner">
                <p class="tablet-overlay-title">Scannez pour accéder au chat</p>
                <div class="tablet-overlay-qr"><img id="qrImage" src="{}" alt="QR Code"></div>
                <button onclick="toggleQrCode()" class="tablet-btn tablet-btn-back">← Retour</button>
            </div>
        </div>
        <script>
            function toggleQrCode() {{
                var c = document.getElementById('qrCodeContainer');
                var b = document.getElementById('chatBtn');
                if (c.style.display === 'none' || !c.style.display) {{ c.style.display = 'flex'; if (b) b.style.display = 'none'; }}
                else {{ c.style.display = 'none'; if (b) b.style.display = 'block'; }}
            }}
        </script>
        """.format(qr_image_url)

    # Bouton Scan QR
    scan_qr_button_html = ""
    if api_url:
        scan_qr_start_url = api_url.rstrip("/") + "/tablet/scan_qr/start"
        scan_qr_button_html = """
        <div class="tablet-btn-cell">
            <button type="button" onclick="startScanQr()" class="tablet-btn tablet-btn-scanqr">📷 Scan QR</button>
            <p class="tablet-btn-label">Réservation</p>
        </div>
        <script>
            function startScanQr() {{
                var btn = document.querySelector('button[onclick="startScanQr()"]');
                if (btn) {{ btn.disabled = true; btn.textContent = '...'; }}
                var xhr = new XMLHttpRequest();
                xhr.open('POST', '{}', true);
                xhr.setRequestHeader('Content-Type', 'application/json');
                xhr.onreadystatechange = function() {{
                    if (xhr.readyState === 4) {{ if (btn) {{ btn.disabled = false; btn.textContent = 'SCAN QR'; }} }}
                }};
                xhr.send();
            }}
        </script>
        """.format(scan_qr_start_url)

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
        subtitle_block = "<div class='tablet-subtitle'>Vous : {}</div>".format(subtitle_safe)

    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Pepper — Hôtel</title>
    <style>
        * {{ box-sizing: border-box; }}
        html, body {{ margin: 0; padding: 0; height: 100%; overflow: hidden; font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; }}
        body {{ background: linear-gradient(165deg, #1a1a2e 0%, #16213e 35%, #0f3460 70%, #1a1a2e 100%); color: #fff; -webkit-tap-highlight-color: transparent; }}
        .tablet-wrap {{ display: flex; flex-direction: column; height: 100%; padding: 14px; max-height: 100vh; }}
        .tablet-header {{ flex-shrink: 0; }}
        .tablet-status-pill {{ display: inline-block; background: rgba(255,255,255,0.95); color: #0f3460; padding: 6px 14px; border-radius: 20px; margin-bottom: 10px; font-size: 13px; font-weight: 600; letter-spacing: 0.3px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); }}
        .tablet-title {{ font-size: 22px; margin: 0 0 8px; font-weight: 700; color: #fff; letter-spacing: -0.3px; text-shadow: 0 1px 2px rgba(0,0,0,0.2); }}
        .tablet-message {{ background: rgba(255,255,255,0.12); backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,0.2); border-radius: 14px; padding: 14px 16px; margin: 0 0 8px; font-size: 16px; line-height: 1.45; color: #fff; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
        .tablet-subtitle {{ margin: 6px 0 0; padding: 10px 14px; background: rgba(255,255,255,0.08); border-radius: 10px; font-size: 14px; color: rgba(255,255,255,0.95); border-left: 4px solid rgba(255,255,255,0.4); }}
        .tablet-btn-grid {{ display: flex; flex-direction: column; flex: 1; min-height: 0; margin-top: 12px; }}
        .tablet-btn-row-mic {{ flex-shrink: 0; text-align: center; margin-bottom: 14px; }}
        .tablet-mic-cell .tablet-btn-label {{ font-size: 14px; margin-top: 6px; }}
        .tablet-btn-row-three {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; flex: 1; min-height: 0; align-content: start; }}
        .tablet-btn-cell {{ text-align: center; }}
        .tablet-btn {{ border: none; border-radius: 14px; padding: 14px 16px; color: #fff; font-size: 17px; font-weight: 600; cursor: pointer; width: 100%; min-height: 54px; transition: transform 0.12s ease, box-shadow 0.12s ease; box-shadow: 0 4px 14px rgba(0,0,0,0.25); letter-spacing: 0.2px; }}
        .tablet-btn:active {{ transform: scale(0.97); }}
        .tablet-btn:disabled {{ opacity: 0.8; cursor: not-allowed; }}
        .tablet-btn-row-three .tablet-btn {{ max-width: none; }}
        .tablet-btn-mic-round {{ border-radius: 50%; min-height: 0; box-shadow: 0 6px 20px rgba(0,0,0,0.3); }}
        .tablet-btn-mic {{ background: linear-gradient(145deg, #22c55e, #16a34a); border: 3px solid rgba(255,255,255,0.3); }}
        .tablet-btn-mic:active {{ background: linear-gradient(145deg, #16a34a, #15803d); }}
        .tablet-btn-call {{ background: linear-gradient(145deg, #3b82f6, #2563eb); box-shadow: 0 4px 14px rgba(37,99,235,0.4); }}
        .tablet-btn-call:active {{ background: linear-gradient(145deg, #2563eb, #1d4ed8); }}
        .tablet-btn-chat {{ background: linear-gradient(145deg, #f59e0b, #d97706); box-shadow: 0 4px 14px rgba(217,119,6,0.35); }}
        .tablet-btn-chat:active {{ background: linear-gradient(145deg, #d97706, #b45309); }}
        .tablet-btn-scanqr {{ background: linear-gradient(145deg, #a855f7, #7c3aed); box-shadow: 0 4px 14px rgba(124,58,237,0.4); }}
        .tablet-btn-scanqr:active {{ background: linear-gradient(145deg, #7c3aed, #6d28d9); }}
        .tablet-btn-label {{ font-size: 12px; margin: 5px 0 0; color: rgba(255,255,255,0.85); font-weight: 500; }}
        .tablet-btn-hint {{ font-size: 11px; margin: 3px 0 0; color: rgba(255,255,255,0.7); }}
        .tablet-overlay {{ display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: linear-gradient(165deg, #1a1a2e, #16213e); z-index: 20; padding: 20px; text-align: center; overflow: auto; flex-direction: column; align-items: center; justify-content: center; }}
        .tablet-overlay-inner {{ max-width: 320px; margin: auto; }}
        .tablet-overlay-title {{ color: #fff; font-size: 18px; font-weight: 600; margin: 0 0 20px; }}
        .tablet-overlay-qr {{ background: #fff; padding: 20px; border-radius: 16px; display: inline-block; box-shadow: 0 8px 24px rgba(0,0,0,0.3); margin-bottom: 20px; }}
        .tablet-overlay-qr img {{ max-width: 220px; height: auto; border-radius: 8px; display: block; }}
        .tablet-btn-back {{ background: rgba(255,255,255,0.2); font-size: 16px; }}
        .tablet-btn-back:active {{ background: rgba(255,255,255,0.3); }}
    </style>
</head>
<body>
    <div class="tablet-wrap">
        <div class="tablet-header">
            {}
            <h1 class="tablet-title">{}</h1>
            <div class="tablet-message">{}</div>
            {}
        </div>
        <div class="tablet-btn-grid">
            <div class="tablet-btn-row-mic">{}</div>
            <div class="tablet-btn-row-three">
                {} {}
                {}
            </div>
        </div>
    </div>
</body>
</html>""".format(status_html, title_safe, message_safe, subtitle_block, mic_button_html, call_button_html, chat_button_html, scan_qr_button_html)
    return html

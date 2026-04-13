"""
Routes Tablette Pepper
"""
from flask import Blueprint, request, jsonify, current_app

from ui.tablet_html import create_tablet_html

bp = Blueprint('tablet', __name__)

# État pour l'appel vocal temps réel déclenché depuis la tablette du robot
_tablet_call_requested = False
_tablet_call_stop = False

# Demande de scan QR depuis la tablette (bouton "Scan QR")
_tablet_scan_qr_requested = False


def get_tablet_call_status():
    return {"call_requested": _tablet_call_requested, "call_stop": _tablet_call_stop}


def set_tablet_call_requested(value):
    global _tablet_call_requested
    _tablet_call_requested = bool(value)


def set_tablet_call_stop(value):
    global _tablet_call_stop
    _tablet_call_stop = bool(value)


def reset_tablet_call():
    global _tablet_call_requested, _tablet_call_stop
    _tablet_call_requested = False
    _tablet_call_stop = False


def get_tablet_scan_qr_requested():
    return _tablet_scan_qr_requested


def set_tablet_scan_qr_requested(value):
    global _tablet_scan_qr_requested
    _tablet_scan_qr_requested = bool(value)


def _tablet_html_content(recording_mode=False):
    """Génère le HTML de la tablette"""
    api_url = request.host_url.rstrip('/')
    if recording_mode:
        return create_tablet_html(
            title="Enregistrement",
            message="Je vous ecoute",
            status="Enregistrement en cours...",
            show_mic_button=True,
            mic_active=True,
            api_url=api_url,
            show_qr_button=True,
            show_call_button=False,
        )
    show_call = current_app.config.get("SHOW_TABLET_CALL_BUTTON", True)
    return create_tablet_html(
        title="Pepper",
        message="Pret a vous aider",
        subtitle="",
        status="En attente",
        show_mic_button=True,
        mic_active=False,
        api_url=api_url,
        show_qr_button=True,
        show_call_button=show_call,
    )


@bp.route('/tablet')
@bp.route('/tablet/')
def tablet_interface():
    """Interface HTML pour la tablette Pepper"""
    try:
        html_content = _tablet_html_content(recording_mode=False)
        return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
    except Exception as e:
        print("Erreur route /tablet:", e)
        import traceback
        traceback.print_exc()
        return "<h1>Erreur</h1><p>Impossible de charger la page tablette.</p><p>Verifiez que le serveur tourne depuis le dossier robot_hotel.</p>", 500, {'Content-Type': 'text/html; charset=utf-8'}


@bp.route('/tablet/recording')
def tablet_recording_interface():
    """Interface de la tablette en mode enregistrement"""
    try:
        html_content = _tablet_html_content(recording_mode=True)
        return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
    except Exception as e:
        print("Erreur route /tablet/recording:", e)
        import traceback
        traceback.print_exc()
        return "<h1>Erreur</h1><p>Impossible de charger la page.</p>", 500, {'Content-Type': 'text/html; charset=utf-8'}


# --- Appel vocal temps réel depuis la tablette du robot ---

@bp.route('/tablet/call/status', methods=['GET'])
def tablet_call_status():
    """Statut de l'appel (poll par pepper_test)."""
    s = get_tablet_call_status()
    return jsonify(s)


@bp.route('/tablet/scan_qr/status', methods=['GET'])
def tablet_scan_qr_status():
    """Statut demande de scan QR (poll par pepper_test)."""
    return jsonify({"scan_qr_requested": get_tablet_scan_qr_requested()})


@bp.route('/tablet/scan_qr/start', methods=['GET', 'POST'])
def tablet_scan_qr_start():
    """Déclenche une demande de scan QR (bouton sur la tablette)."""
    set_tablet_scan_qr_requested(True)
    if request.method == 'POST' or request.headers.get('Accept', '').find('json') >= 0:
        return jsonify({"ok": True, "message": "Scan QR demandé"})
    return "<html><head><meta charset='UTF-8'></head><body style='font-family:sans-serif;text-align:center;padding:2em;'><p>Scan QR demandé. Présentez votre QR code devant la caméra.</p></body></html>", 200, {'Content-Type': 'text/html; charset=utf-8'}


@bp.route('/tablet/scan_qr/cleared', methods=['POST'])
def tablet_scan_qr_cleared():
    """Le script a pris en charge la demande de scan QR."""
    set_tablet_scan_qr_requested(False)
    return jsonify({"ok": True})


@bp.route('/tablet/call/start', methods=['GET', 'POST'])
def tablet_call_start():
    """Déclenche une demande d'appel (bouton Appel sur la tablette)."""
    set_tablet_call_requested(True)
    if request.method == 'POST' or request.headers.get('Accept', '').find('json') >= 0:
        return jsonify({"ok": True, "message": "Appel demandé"})
    return "<html><head><meta charset='UTF-8'></head><body style='font-family:sans-serif;text-align:center;padding:2em;'><p>Appel demandé. Le robot va lancer l'appel.</p></body></html>", 200, {'Content-Type': 'text/html; charset=utf-8'}


@bp.route('/tablet/call/cleared', methods=['POST'])
def tablet_call_cleared():
    """Le script a pris en charge l'appel (efface call_requested)."""
    set_tablet_call_requested(False)
    return jsonify({"ok": True})


@bp.route('/tablet/call/stop', methods=['GET', 'POST'])
def tablet_call_stop():
    """Raccrocher : met call_stop à True (bouton sur la tablette)."""
    set_tablet_call_stop(True)
    base = request.host_url.rstrip('/')
    html = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="background:#667eea;color:white;font-family:sans-serif;text-align:center;padding:2em;">
    <h1>Appel terminé</h1>
    <p>Vous pouvez revenir à l'écran d'accueil.</p>
</body></html>"""
    return html, 200, {'Content-Type': 'text/html; charset=utf-8'}


@bp.route('/tablet/call/reset', methods=['POST'])
def tablet_call_reset():
    """Réinitialise l'état appel (après fin d'appel par le script)."""
    reset_tablet_call()
    return jsonify({"ok": True})


@bp.route('/tablet/call')
def tablet_call_page():
    """Page tablette pendant l'appel : UI animée avec logo, ondes audio et bouton Raccrocher."""
    base = request.host_url.rstrip('/')
    stop_url = base + '/tablet/call/stop'
    html = u"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Appel en cours – Pepper</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      font-family: 'Segoe UI', Arial, sans-serif;
      color: white;
      overflow: hidden;
    }}

    /* Cercles de pulse autour du logo */
    .pulse-ring {{
      position: relative;
      width: 180px;
      height: 180px;
      margin-bottom: 32px;
    }}
    .pulse-ring::before,
    .pulse-ring::after {{
      content: '';
      position: absolute;
      top: 50%; left: 50%;
      transform: translate(-50%, -50%);
      border-radius: 50%;
      border: 3px solid rgba(102, 126, 234, 0.6);
      animation: pulse 2s ease-out infinite;
    }}
    .pulse-ring::after {{ animation-delay: 1s; }}
    @keyframes pulse {{
      0%   {{ width: 160px; height: 160px; opacity: 1; }}
      100% {{ width: 260px; height: 260px; opacity: 0; }}
    }}

    /* Logo robot (SVG inline) */
    .robot-circle {{
      position: relative;
      width: 140px;
      height: 140px;
      background: linear-gradient(135deg, #667eea, #764ba2);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 20px auto 0;
      box-shadow: 0 0 40px rgba(102,126,234,0.5);
      z-index: 1;
      animation: glow 2s ease-in-out infinite alternate;
    }}
    @keyframes glow {{
      from {{ box-shadow: 0 0 20px rgba(102,126,234,0.4); }}
      to   {{ box-shadow: 0 0 60px rgba(118,75,162,0.8); }}
    }}
    .robot-icon {{
      font-size: 72px;
      line-height: 1;
      user-select: none;
    }}

    /* Titre */
    .title {{
      font-size: 30px;
      font-weight: 700;
      letter-spacing: 1px;
      margin-bottom: 10px;
    }}
    .subtitle {{
      font-size: 16px;
      color: rgba(255,255,255,0.7);
      margin-bottom: 36px;
    }}

    /* Barres d'ondes audio */
    .waves {{
      display: flex;
      align-items: flex-end;
      gap: 5px;
      height: 48px;
      margin-bottom: 44px;
    }}
    .wave-bar {{
      width: 8px;
      border-radius: 4px;
      background: linear-gradient(to top, #667eea, #a78bfa);
      animation: wave 1.2s ease-in-out infinite;
    }}
    .wave-bar:nth-child(1)  {{ height: 20px; animation-delay: 0.0s; }}
    .wave-bar:nth-child(2)  {{ height: 36px; animation-delay: 0.1s; }}
    .wave-bar:nth-child(3)  {{ height: 28px; animation-delay: 0.2s; }}
    .wave-bar:nth-child(4)  {{ height: 44px; animation-delay: 0.3s; }}
    .wave-bar:nth-child(5)  {{ height: 32px; animation-delay: 0.4s; }}
    .wave-bar:nth-child(6)  {{ height: 48px; animation-delay: 0.5s; }}
    .wave-bar:nth-child(7)  {{ height: 36px; animation-delay: 0.4s; }}
    .wave-bar:nth-child(8)  {{ height: 44px; animation-delay: 0.3s; }}
    .wave-bar:nth-child(9)  {{ height: 24px; animation-delay: 0.2s; }}
    .wave-bar:nth-child(10) {{ height: 36px; animation-delay: 0.1s; }}
    .wave-bar:nth-child(11) {{ height: 16px; animation-delay: 0.0s; }}
    @keyframes wave {{
      0%, 100% {{ transform: scaleY(0.4); opacity: 0.6; }}
      50%       {{ transform: scaleY(1.0); opacity: 1.0; }}
    }}

    /* Indicateur statut */
    .status-badge {{
      display: flex;
      align-items: center;
      gap: 8px;
      background: rgba(255,255,255,0.1);
      border: 1px solid rgba(255,255,255,0.2);
      border-radius: 20px;
      padding: 8px 20px;
      font-size: 14px;
      margin-bottom: 44px;
      backdrop-filter: blur(4px);
    }}
    .status-dot {{
      width: 10px;
      height: 10px;
      background: #4ade80;
      border-radius: 50%;
      animation: blink 1.5s ease-in-out infinite;
    }}
    @keyframes blink {{
      0%, 100% {{ opacity: 1; }}
      50%       {{ opacity: 0.2; }}
    }}

    /* Bouton raccrocher */
    .btn-hangup {{
      display: flex;
      align-items: center;
      gap: 12px;
      background: linear-gradient(135deg, #ef4444, #dc2626);
      color: white;
      border: none;
      border-radius: 50px;
      padding: 18px 48px;
      font-size: 20px;
      font-weight: 600;
      cursor: pointer;
      text-decoration: none;
      box-shadow: 0 8px 24px rgba(239,68,68,0.4);
      transition: transform 0.15s, box-shadow 0.15s;
    }}
    .btn-hangup:hover  {{ transform: scale(1.05); box-shadow: 0 12px 32px rgba(239,68,68,0.6); }}
    .btn-hangup:active {{ transform: scale(0.97); }}
    .hangup-icon {{ font-size: 24px; }}

    /* Hint en bas */
    .hint {{
      position: fixed;
      bottom: 24px;
      font-size: 13px;
      color: rgba(255,255,255,0.4);
      text-align: center;
    }}
  </style>
</head>
<body>

  <div class="pulse-ring">
    <div class="robot-circle">
      <span class="robot-icon">🤖</span>
    </div>
  </div>

  <h1 class="title">Appel en cours</h1>
  <p class="subtitle">Pepper vous écoute</p>

  <div class="waves">
    <div class="wave-bar"></div><div class="wave-bar"></div>
    <div class="wave-bar"></div><div class="wave-bar"></div>
    <div class="wave-bar"></div><div class="wave-bar"></div>
    <div class="wave-bar"></div><div class="wave-bar"></div>
    <div class="wave-bar"></div><div class="wave-bar"></div>
    <div class="wave-bar"></div>
  </div>

  <div class="status-badge">
    <div class="status-dot"></div>
    <span>Parlez — 2 s de silence = envoi</span>
  </div>

  <a href="{stop_url}" class="btn-hangup">
    <span class="hangup-icon">📵</span>
    Raccrocher
  </a>

  <p class="hint">Appuyez sur Raccrocher pour terminer la conversation</p>

</body>
</html>""".format(stop_url=stop_url)
    return html, 200, {'Content-Type': 'text/html; charset=utf-8'}

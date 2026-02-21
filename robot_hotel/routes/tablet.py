"""
Routes Tablette Pepper
"""
from flask import Blueprint, request, jsonify, current_app

from ui.tablet_html import create_tablet_html

bp = Blueprint('tablet', __name__)

# État pour l'appel vocal temps réel déclenché depuis la tablette du robot
_tablet_call_requested = False
_tablet_call_stop = False


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
    """Page tablette pendant l'appel : « Appel en cours » + bouton Raccrocher."""
    base = request.host_url.rstrip('/')
    stop_url = base + '/tablet/call/stop'
    html = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="background:#667eea;color:white;font-family:sans-serif;text-align:center;padding:2em;">
    <h1 style="font-size:28px;">Appel en cours</h1>
    <p style="font-size:18px;">Parlez, j'écoute. 2 secondes de silence envoient votre message.</p>
    <p style="margin-top:30px;"><a href="{stop_url}" style="display:inline-block;background:#e53935;color:white;padding:15px 30px;border-radius:25px;font-size:20px;text-decoration:none;">Raccrocher</a></p>
</body></html>""".format(stop_url=stop_url)
    return html, 200, {'Content-Type': 'text/html; charset=utf-8'}

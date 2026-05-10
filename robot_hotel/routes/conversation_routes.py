"""
Routes pour la réservation conversationnelle pas à pas.
Le robot pose une question à la fois via la tablette.
"""
import html as html_module
from flask import Blueprint, request, jsonify, current_app
from services.reservation_conversation import (
    start_conversation,
    get_conversation_state,
    process_answer,
    finalize_reservation,
)
from services.whisper import transcribe_audio
from services.record import get_last_recorded_file_path

bp = Blueprint('conversation', __name__)


@bp.route('/conversation/start', methods=['POST'])
def conv_start():
    """Démarre une nouvelle conversation de réservation."""
    result = start_conversation()
    return jsonify(result)


@bp.route('/conversation/answer', methods=['POST'])
def conv_answer():
    """
    Transcrit le dernier enregistrement et traite la réponse pour l'étape courante.
    Accepte :
      - multipart/form-data : {"session_id": "...", "file": <wav>}  (micro Pepper)
      - application/json    : {"session_id": "..."}                  (micro PC)
    """
    import tempfile, os as _os

    # ── Récupérer session_id et fichier audio ────────────────────────────────
    tmp_path = None
    if request.files.get('file'):
        # Le script Pepper a envoyé le fichier directement
        session_id = request.form.get('session_id')
        uploaded = request.files['file']
        tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        uploaded.save(tmp.name)
        tmp.close()
        tmp_path = tmp.name
        file_path = tmp_path
    else:
        data = request.get_json(silent=True) or {}
        session_id = data.get('session_id')
        file_path = get_last_recorded_file_path()

    if not session_id:
        return jsonify({"error": "session_id requis", "status": "error"}), 400

    if not file_path:
        return jsonify({
            "status": "retry",
            "question": "Je n'ai pas recu d'enregistrement. Appuyez sur le micro et parlez.",
        }), 200

    model = current_app.config.get('whisper_model')
    try:
        tr = transcribe_audio(model, file_path)
        transcript = tr.get('text', '').strip()
    except Exception as e:
        return jsonify({"error": "Erreur de transcription : {}".format(e), "status": "error"}), 500
    finally:
        # Supprimer le fichier temporaire uploadé
        if tmp_path and _os.path.exists(tmp_path):
            try:
                _os.remove(tmp_path)
            except Exception:
                pass

    if not transcript:
        return jsonify({
            "status": "retry",
            "question": "Je n'ai rien entendu. Pouvez-vous repeter ?",
        }), 200

    result = process_answer(session_id, transcript)
    return jsonify(result)


@bp.route('/conversation/confirm', methods=['POST'])
def conv_confirm():
    """
    Finalise la réservation avec l'email saisi sur la tablette.
    Body JSON : {"session_id": "...", "email": "..."}
    """
    data = request.get_json(silent=True) or {}
    session_id = data.get('session_id')
    email = (data.get('email') or '').strip()

    if not session_id:
        return jsonify({"error": "session_id requis", "status": "error"}), 400
    if not email or '@' not in email:
        return jsonify({"error": "Email invalide", "status": "error"}), 400

    result = finalize_reservation(session_id, email)
    return jsonify(result)


@bp.route('/conversation/edit', methods=['POST'])
def conv_edit():
    """
    Met à jour les champs collectés d'une conversation (appelé depuis la tablette).
    Body JSON: {"session_id": "...", "updates": {"nom": "...", "prenom": "...", ...}}
    """
    data = request.get_json(silent=True) or {}
    session_id = data.get('session_id')
    updates = data.get('updates') or {}

    if not session_id:
        return jsonify({"error": "session_id requis", "status": "error"}), 400

    from services.reservation_conversation import update_conversation_data
    res = update_conversation_data(session_id, updates)
    return jsonify(res)


@bp.route('/conversation/state')
def conv_state():
    """Retourne l'état courant d'une conversation (pour debug)."""
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({"error": "session_id requis"}), 400
    state = get_conversation_state(session_id)
    if not state:
        return jsonify({"error": "Session introuvable ou expirée"}), 404
    return jsonify(state)


# ─── Page tablette ────────────────────────────────────────────────────────────

@bp.route('/tablet/reservation')
def tablet_reservation():
    """
    Interface tablette pour la réservation conversationnelle.
    Page SPA : le robot pose les questions une par une, l'utilisateur répond
    au micro, puis saisit son email pour confirmer.
    """
    api_url = request.host_url.rstrip('/')
    return _build_reservation_html(api_url), 200, {'Content-Type': 'text/html; charset=utf-8'}


def _build_reservation_html(api_url):
    api = html_module.escape(api_url)
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Réservation - Pepper</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #667eea;
      color: white;
      font-family: Arial, sans-serif;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 16px;
    }}
    .card {{
      background: #8a9eff;
      border-radius: 18px;
      padding: 28px 24px;
      width: 100%;
      max-width: 500px;
      text-align: center;
    }}
    h1 {{ font-size: 30px; margin-bottom: 6px; }}
    .label {{
      font-size: 14px;
      color: rgba(255,255,255,0.75);
      margin-bottom: 16px;
      min-height: 18px;
    }}
    .bubble {{
      background: #9aafff;
      border-radius: 12px;
      padding: 18px;
      font-size: 22px;
      line-height: 1.5;
      margin-bottom: 14px;
      min-height: 70px;
    }}
    .heard {{
      background: rgba(255,255,255,0.18);
      border-radius: 8px;
      padding: 10px 14px;
      font-size: 16px;
      font-style: italic;
      margin-bottom: 14px;
      display: none;
    }}
    .mic-wrap {{ margin: 18px 0 8px; }}
    .mic-btn {{
      background: #4CAF50;
      border: 5px solid #2E7D32;
      border-radius: 50%;
      width: 120px;
      height: 120px;
      cursor: pointer;
      color: white;
      font-size: 42px;
      font-weight: bold;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      transition: all .2s;
    }}
    .mic-btn.rec {{
      background: #e53935;
      border-color: #b71c1c;
      width: 136px;
      height: 136px;
    }}
    .mic-hint {{
      font-size: 17px;
      margin-top: 10px;
      min-height: 22px;
    }}
    /* Email step */
    .email-section {{ display: none; margin-top: 10px; }}
    .email-input {{
      width: 100%;
      font-size: 20px;
      padding: 12px 16px;
      border-radius: 10px;
      border: none;
      color: #333;
      margin-bottom: 14px;
    }}
    .ok-btn {{
      background: #43a047;
      border: none;
      border-radius: 24px;
      padding: 14px 40px;
      font-size: 22px;
      color: white;
      cursor: pointer;
      width: 100%;
    }}
    .ok-btn:disabled {{ opacity: .6; cursor: default; }}
    /* Summary */
    .summary {{
      background: rgba(255,255,255,0.15);
      border-radius: 10px;
      padding: 12px 16px;
      font-size: 16px;
      text-align: left;
      margin-bottom: 14px;
      display: none;
    }}
    .summary p {{ margin: 4px 0; }}
    /* Back */
    .back {{
      margin-top: 20px;
      background: rgba(255,255,255,0.15);
      border: 2px solid white;
      border-radius: 20px;
      padding: 9px 24px;
      color: white;
      font-size: 15px;
      cursor: pointer;
    }}
    .success-msg {{ font-size: 26px; color: #b9f6ca; line-height: 1.6; }}
  </style>
</head>
<body>
<div class="card">
  <h1>🏨 Réservation</h1>
  <div id="label" class="label"></div>
  <div id="bubble" class="bubble">Chargement…</div>
  <div id="heard" class="heard"></div>

  <div class="mic-wrap" id="micWrap">
    <button id="micBtn" class="mic-btn" onclick="toggleMic()">🎤</button>
    <div id="micHint" class="mic-hint">Appuyez pour parler</div>
  </div>

  <div class="email-section" id="emailSection">
    <div class="summary" id="summary"></div>
    <input type="email" id="emailInput" class="email-input" placeholder="votre@email.com" />
    <button class="ok-btn" id="okBtn" onclick="confirmRes()">✅ Confirmer la réservation</button>
    <div style="margin-top:8px; display:flex; gap:8px;">
      <button style="flex:1; background:#1976d2; border:none; border-radius:12px; padding:10px; color:white; cursor:pointer;" id="editBtn" onclick="editInfo()">✏️ Modifier</button>
    </div>
    <div id="editSection" style="display:none; margin-top:10px; text-align:left;">
      <input id="edit_nom" placeholder="Nom" style="width:100%; padding:10px; margin-bottom:6px; border-radius:8px; border:none; font-size:16px;" />
      <input id="edit_prenom" placeholder="Prénom" style="width:100%; padding:10px; margin-bottom:6px; border-radius:8px; border:none; font-size:16px;" />
      <input id="edit_date_arrivee" placeholder="Date arrivée (YYYY-MM-DD)" style="width:100%; padding:10px; margin-bottom:6px; border-radius:8px; border:none; font-size:16px;" />
      <input id="edit_date_depart" placeholder="Date départ (YYYY-MM-DD)" style="width:100%; padding:10px; margin-bottom:6px; border-radius:8px; border:none; font-size:16px;" />
      <div style="display:flex; gap:8px;">
        <button style="flex:1; background:#43a047; border:none; border-radius:12px; padding:10px; color:white; cursor:pointer;" onclick="saveEditInfo()">💾 Enregistrer</button>
        <button style="flex:1; background:#9e9e9e; border:none; border-radius:12px; padding:10px; color:white; cursor:pointer;" onclick="cancelEdit()">✖ Annuler</button>
      </div>
    </div>
  </div>

  <button class="back" onclick="goBack()">← Retour accueil</button>
</div>

<script>
(function() {{
  var API = '{api}';
  var sessionId = null;
  var isRec = false;

  function xhr(method, url, body, cb) {{
    var r = new XMLHttpRequest();
    r.open(method, url, true);
    r.setRequestHeader('Content-Type', 'application/json');
    r.onreadystatechange = function() {{
      if (r.readyState !== 4) return;
      var ok = r.status >= 200 && r.status < 300;
      var data;
      try {{ data = JSON.parse(r.responseText); }} catch(e) {{ data = {{}}; }}
      cb(ok, data);
    }};
    r.onerror = function() {{ cb(false, {{error:'Connexion perdue'}}); }};
    r.send(body ? JSON.stringify(body) : null);
  }}
    window.editInfo = function() {{
      var s = document.getElementById('summary');
      // Pré-remplir les champs d'édition à partir du résumé affiché si possible
      var collected = {{nom: '', prenom: '', date_arrivee: '', date_depart: ''}};
      try {{
        // tenter d'extraire depuis le summary innerText
        var lines = s.innerText.split('\\n');
        lines.forEach(function(l) {{
          if (l.indexOf('Nom :') !== -1) {{
            var m = l.replace('Nom :','').trim().split(' ');
            collected.prenom = m[0] || '';
            collected.nom = m.slice(1).join(' ') || collected.nom;
          }}
          if (l.indexOf('Arrivée :') !== -1) {{ collected.date_arrivee = l.replace('Arrivée :','').trim(); }}
          if (l.indexOf('Départ :') !== -1) {{ collected.date_depart = l.replace('Départ :','').trim(); }}
        }});
      }} catch(e) {{}}
      document.getElementById('edit_nom').value = collected.nom || '';
      document.getElementById('edit_prenom').value = collected.prenom || '';
      document.getElementById('edit_date_arrivee').value = collected.date_arrivee || '';
      document.getElementById('edit_date_depart').value = collected.date_depart || '';
      document.getElementById('editSection').style.display = 'block';
      document.getElementById('editBtn').disabled = true;
    }};

    window.cancelEdit = function() {{
      document.getElementById('editSection').style.display = 'none';
      document.getElementById('editBtn').disabled = false;
    }};

    window.saveEditInfo = function() {{
      var updates = {{}};
      var nom = document.getElementById('edit_nom').value.trim();
      var prenom = document.getElementById('edit_prenom').value.trim();
      var da = document.getElementById('edit_date_arrivee').value.trim();
      var dd = document.getElementById('edit_date_depart').value.trim();
      if (nom) updates.nom = nom;
      if (prenom) updates.prenom = prenom;
      if (da) updates.date_arrivee = da;
      if (dd) updates.date_depart = dd;
      var btn = document.getElementById('editBtn');
      btn.disabled = true;
      xhr('POST', API + '/conversation/edit', {{session_id: sessionId, updates: updates}}, function(ok, res) {{
        btn.disabled = false;
        if (ok && res.status === 'success') {{
          // Mettre à jour l'affichage résumé
          var collected = res.data || {{}};
          showEmail(collected);
          document.getElementById('editSection').style.display = 'none';
          document.getElementById('editBtn').disabled = false;
        }} else {{
          alert('Erreur en enregistrant les modifications: ' + (res.error || 'réessayez'));
        }}
      }});
    }};


  function setLabel(txt) {{ document.getElementById('label').textContent = txt || ''; }}
  function setBubble(txt) {{ document.getElementById('bubble').textContent = txt; }}
  function setHeard(txt) {{
    var el = document.getElementById('heard');
    if (txt) {{ el.textContent = 'Compris : "' + txt + '"'; el.style.display = 'block'; }}
    else {{ el.style.display = 'none'; }}
  }}

  function showMic() {{
    document.getElementById('micWrap').style.display = 'block';
    document.getElementById('emailSection').style.display = 'none';
  }}
  function showEmail(collected) {{
    document.getElementById('micWrap').style.display = 'none';
    document.getElementById('emailSection').style.display = 'block';
    var s = document.getElementById('summary');
    if (collected) {{
      s.innerHTML =
        '<p><strong>Nom :</strong> ' + (collected.nom||'') + ' ' + (collected.prenom||'') + '</p>' +
        '<p><strong>Chambre :</strong> ' + (collected.type_chambre||'') + '</p>' +
        '<p><strong>Arrivée :</strong> ' + (collected.date_arrivee||'') + '</p>' +
        '<p><strong>Départ :</strong> ' + (collected.date_depart||'') + '</p>';
      s.style.display = 'block';
    }}
    document.getElementById('emailInput').value = '';
    var btn = document.getElementById('okBtn');
    btn.disabled = false;
    btn.textContent = '✅ Confirmer la réservation';
  }}

  function micIdle() {{
    isRec = false;
    var btn = document.getElementById('micBtn');
    btn.classList.remove('rec');
    btn.style.width = btn.style.height = '120px';
    btn.textContent = '🎤';
    document.getElementById('micHint').textContent = 'Appuyez pour parler';
  }}
  function micActive() {{
    isRec = true;
    var btn = document.getElementById('micBtn');
    btn.classList.add('rec');
    btn.style.width = btn.style.height = '136px';
    btn.textContent = 'STOP';
    document.getElementById('micHint').textContent = 'Parlez… appuyez pour arrêter';
  }}

  function handleServerResponse(res) {{
    if (res.status === 'continue') {{
      setHeard(res.transcript);
      setTimeout(function() {{
        setLabel(res.label);
        setBubble(res.question);
        setHeard(null);
        micIdle();
      }}, 1600);
    }} else if (res.status === 'need_email') {{
      setHeard(res.transcript);
      setTimeout(function() {{
        setLabel(res.label);
        setBubble(res.question);
        setHeard(null);
        showEmail(res.collected);
      }}, 1600);
    }} else if (res.status === 'retry') {{
      setHeard(res.transcript || null);
      setBubble(res.question);
      setTimeout(function() {{ setHeard(null); micIdle(); }}, 2000);
    }} else if (res.status === 'error') {{
      setBubble('Erreur : ' + (res.error || 'réessayez'));
      micIdle();
    }} else {{
      micIdle();
    }}
  }}

  window.toggleMic = function() {{
    if (!isRec) {{
      micActive();
      document.getElementById('micHint').textContent = 'Démarrage…';
      xhr('POST', API + '/record/start', null, function(ok) {{
        if (!ok) {{
          micIdle();
          document.getElementById('micHint').textContent = 'Erreur micro';
        }} else {{
          document.getElementById('micHint').textContent = 'Parlez maintenant…';
        }}
      }});
    }} else {{
      document.getElementById('micHint').textContent = 'Arrêt en cours…';
      xhr('POST', API + '/record/stop', null, function() {{
        micIdle();
        document.getElementById('micHint').textContent = 'Traitement…';
        setBubble('Un instant…');
        xhr('POST', API + '/conversation/answer', {{session_id: sessionId}}, function(ok, res) {{
          handleServerResponse(res);
        }});
      }});
    }}
  }};

  window.confirmRes = function() {{
    var email = document.getElementById('emailInput').value.trim();
    if (!email || !email.includes('@')) {{
      alert('Veuillez entrer un email valide');
      return;
    }}
    var btn = document.getElementById('okBtn');
    btn.disabled = true;
    btn.textContent = 'Envoi en cours…';
    xhr('POST', API + '/conversation/confirm', {{session_id: sessionId, email: email}}, function(ok, res) {{
      if (ok && res.status === 'success') {{
        setLabel('');
        setBubble('');
        document.getElementById('bubble').innerHTML =
          '<span class="success-msg">✅ Réservation confirmée !<br>' +
          'N° ' + (res.reservation_id || 'N/A') + '<br><br>' +
          (res.email_sent ? '📧 Email de confirmation envoyé !' : '⚠️ Email non envoyé (SMTP non configuré)') +
          '</span>';
        document.getElementById('emailSection').style.display = 'none';
        document.getElementById('heard').style.display = 'none';
        setHeard(null);
      }} else {{
        btn.disabled = false;
        btn.textContent = '✅ Confirmer la réservation';
        alert('Erreur : ' + (res.error || 'Veuillez réessayer'));
      }}
    }});
  }};

  window.goBack = function() {{
    window.location.href = API + '/tablet';
  }};

  // Démarrage automatique de la conversation au chargement
  xhr('POST', API + '/conversation/start', null, function(ok, res) {{
    if (ok && res.session_id) {{
      sessionId = res.session_id;
      setLabel(res.label);
      setBubble(res.question);
    }} else {{
      setBubble('Erreur de démarrage. Revenez à l\\'accueil.');
    }}
  }});
}})();
</script>
</body>
</html>"""
